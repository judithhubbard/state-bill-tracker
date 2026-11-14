#!/usr/bin/env python3
"""Download Colorado's bills from the General Assembly's website, https://leg.colorado.gov/ (the new site, a Rails app
that replaced the old Drupal pages in 2026; the old ones live on at content.leg.colorado.gov for documents). Plain HTML:
there is no API or JSON, and pages answer 406 unless the request asks for text/html. robots.txt disallows the file
downloads (bill texts, fiscal notes, amendments, committee reports, session laws: "/bill_files/*/download" and the
like), the calendars and journals, and admin paths; none are read here, and `allowed()` checks every path against it.
It sets no crawl delay. One request at a time, three seconds apart: at one every 1.5 seconds the site answered
429 (too many requests) after about 230 requests; a 429 makes it wait and go slower.

For each regular session (2024, 2025, 2026; one a year, January to May):
- The bill list (/bills/bill-search?sessions[]=2025 Regular Session&measures[]=Bill, 25 to a page): every House and
  Senate bill with its short title, long title, subjects, sponsors and last action, into data/co/<year>/list.json.
- Each bill's page (/bills/HB25-1001) parsed into data/co/<year>/bills/<HB25-1001>.json: the short title, long title,
  subjects, the summary (paragraphs as [kind, text]), prime sponsors, sponsors and co-sponsors in each house, the
  committees in each house, the history (date, chamber, action), the committee hearings (each motion, its result and
  vote link), the floor votes (date, calendar, motion, tallies, vote link), amendments, versions and fiscal notes (dates
  and names only) and session laws (chapter and effective date).
  A finished session (after June 20, past the governor's 30 days) is read once, after it finishes. The current
  session's bills are read again when the list shows a new last action, and otherwise in turn, the seventh read
  longest ago each run, so every bill is read at least weekly.
- Each vote the bill pages link to, member by member, into votes/<id>.json, once: floor votes (/bill_votes/22375, id
  "f22375") and committee votes (/committee_meeting_hearing_items/1425/votes/1774, id "c1425-1774").
- The members (/legislators?sess=2025a: name, title, district, party; the current session's list also has Capitol
  phones and emails) and each member's page (leadership position, counties, email, phone, Capitol address, committee
  assignments) into members.json; the House and Senate committees of reference and the year-round committees
  (/committees?sess=2025a, then each committee's page: members with "Chair"/"Vice Chair", meeting days) into
  committees.json. A finished session's once; the current one's once a week.
data/co/incomplete lists what was never downloaded (votes not yet read don't count; a failed refresh keeps the last
copy); it is removed when nothing is missing.
Usage: python3 states/co/fetch.py [year]   (default: 2024, 2025 and 2026, i.e. this year and the two before)
"""
import html, json, math, os, re, sys, time, urllib.error, urllib.parse, urllib.request
from datetime import date, datetime, timedelta

SITE = "https://leg.colorado.gov"
DATA = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "co"))
AGENT = "statebilltracker.org (a nonprofit bill tracker; contact via github.com/judithhubbard)"
TODAY = date.today()
YEARS = [int(sys.argv[1])] if len(sys.argv) > 1 else [TODAY.year - 2, TODAY.year - 1, TODAY.year]
REFRESH_DAYS = 7
INCOMPLETE = set()
WHOLE = [True]  # the last run left nothing missing (set in main)
PENDING_VOTES = []  # (year, folder, votes to read, vote -> bill), read after every year's bills
# The run's own time limit (FETCH_MINUTES, set by the workflow): stop a few minutes early with everything saved, rather
# than be cut off before writing the incomplete marker.
START = time.time()
BUDGET = max(0.0, float(os.environ.get("FETCH_MINUTES") or 0) - 5) * 60


def out_of_time():
    return BUDGET and time.time() - START > BUDGET
MISSING = object()  # a page that answers 404
DELAY = 3.0  # seconds between requests: at 1.5 the site answered 429 (too many requests) after about 230
THROTTLED = 0  # 429 answers in a row
RULES = []  # (allow?, regex) from robots.txt


def finished(year):
    """A session is final once the governor's 30 days after adjournment (early to mid May) have passed."""
    return TODAY > date(year, 6, 20)


# ---------------------------------------------------------------- fetching

def robots():
    """Reads robots.txt's rules for every user agent ("*" wildcards and "$" ends) and any crawl delay."""
    global DELAY
    req = urllib.request.Request(SITE + "/robots.txt", headers={"User-Agent": AGENT, "Accept": "text/plain, text/html"})
    with urllib.request.urlopen(req, timeout=60) as r:
        body = r.read().decode("utf-8", "replace")
    applies = False
    for line in body.splitlines():
        line = line.split("#", 1)[0].strip()
        if ":" not in line:
            continue
        key, value = (x.strip() for x in line.split(":", 1))
        key = key.lower()
        if key == "user-agent":
            applies = value == "*" or value.lower().startswith("statebilltracker")
        elif applies and key in ("allow", "disallow") and value:
            pattern = re.escape(value).replace(r"\*", ".*")
            if pattern.endswith(r"\$"):
                pattern = pattern[:-2] + "$"
            RULES.append((key == "allow", re.compile(pattern), len(value)))
        elif applies and key == "crawl-delay":
            try:
                DELAY = max(DELAY, float(value))
            except ValueError:
                pass


def allowed(path):
    """The longest matching rule wins (Google's reading); no rule means allowed."""
    best = None
    for allow, pattern, length in RULES:
        if pattern.match(path) and (best is None or length > best[1]):
            best = (allow, length)
    return best is None or best[0]


def get(path):
    """The page's text; MISSING for a 404, None when it can't be read. Stops the run if the site refuses us (401, 403,
    406, a bot challenge). A 429 (too many requests) means slow down: wait as long as Retry-After says (at least five
    minutes), go slower from then on, and stop after three in a row."""
    global DELAY, THROTTLED
    if not allowed(urllib.parse.urlsplit(path).path):
        print(f"{path}: disallowed by robots.txt; skipped")
        return None
    for attempt in range(4):
        if out_of_time():
            return None
        time.sleep(DELAY)
        try:
            req = urllib.request.Request(SITE + path, headers={"User-Agent": AGENT, "Accept": "text/html"})
            with urllib.request.urlopen(req, timeout=30) as r:
                body = r.read().decode("utf-8", "replace")
            THROTTLED = 0
            if "cf-challenge" in body or "Just a moment..." in body[:2000]:
                refused(path, "a bot challenge")
            return body
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return MISSING
            if e.code == 429:
                THROTTLED += 1
                if THROTTLED >= 3:
                    refused(path, 429)
                try:
                    wait = max(300, int(e.headers.get("Retry-After") or 0))
                except ValueError:
                    wait = 300
                DELAY = min(DELAY * 1.5, 15)
                print(f"{path}: too many requests (429); waiting {wait} s, then one request every {DELAY:.1f} s", flush=True)
                time.sleep(wait)
                continue
            if e.code in (401, 403, 406):
                refused(path, e.code)
            time.sleep(10 * 2 ** attempt)
        except Exception:
            time.sleep(10 * 2 ** attempt)
    return None


def refused(path, why):
    print(f"{path}: refused ({why}); stopping")
    if not WHOLE[0]:  # a refusal stops a first copy; once whole, the last copies stay
        INCOMPLETE.add(f"refused:{why}")
    finish()
    sys.exit(1)


def save(path, data):
    with open(path + ".tmp", "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=0)
    os.replace(path + ".tmp", path)


def load(path, default=None):
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


# ---------------------------------------------------------------- HTML helpers

def text(fragment):
    """Plain text of an HTML fragment, whitespace collapsed."""
    fragment = re.sub(r"<br\s*/?>", " ", fragment)
    fragment = re.sub(r"<!--.*?-->", "", fragment, flags=re.S)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", fragment))).strip()


def section(page, start, end=None):
    """The part of the page from the first `start` to the next `end` (or the end)."""
    i = page.find(start)
    if i < 0:
        return ""
    j = page.find(end, i + len(start)) if end else -1
    return page[i:j] if j > 0 else page[i:]


def table_rows(fragment):
    """[{label: text, label + "_href": first link}] for each row of the site's tables (cells carry data-label)."""
    out = []
    for row in re.findall(r"<tr[^>]*role=\"row\"[^>]*>(.*?)</tr>", fragment, re.S):
        cells = re.findall(r'<t[dh][^>]*data-label="([^"]*)"[^>]*>(.*?)</t[dh]>', row, re.S)
        if not cells:
            continue
        r = {}
        for label, cell in cells:
            r[label] = text(cell)
            link = re.search(r'href="([^"]+)"', cell)
            if link:
                r[label + "_href"] = html.unescape(link.group(1)).replace(SITE, "")
        out.append(r)
    return out


def accordions(fragment):
    """[(heading, body)] for each collapsible block in a tab."""
    parts = re.split(r'<div class="gen-accordion">', fragment)[1:]
    out = []
    for p in parts:
        head = re.search(r"<h4[^>]*>(.*?)</h4>", p, re.S)
        out.append((text(head.group(1)) if head else "", p))
    return out


def mdy(s):
    """'05/22/2025' -> '2025-05-22'; other text unchanged."""
    m = re.match(r"(\d\d)/(\d\d)/(\d{4})", s or "")
    return f"{m.group(3)}-{m.group(1)}-{m.group(2)}" if m else s


def slug(href):
    m = re.search(r"/legislators/([^/?#\"]+)", href or "")
    return m.group(1) if m else None


def tallies(fragment):
    """{"Yes": 41, "No": 22, ...} from a vote page's count tags or a bill page's tally boxes."""
    out = {k: int(v) for k, v in re.findall(r'class="count-tag (\w+)">\s*(\d+)', fragment)}
    if not out:
        for v, k in re.findall(r"bill-votes-count[^>]*>(\d+)</div>\s*<div class='text-center'>(\w+)</div>", fragment):
            out[k] = int(v)
    return out


# ---------------------------------------------------------------- bill list

def bill_list(year):
    """{"HB25-1001": {"short": ..., "title": ..., "subjects": [...], "sponsors": [...], "lastDate": ..., "lastAction":
    ...}} for every bill of the year's regular session, or None if a page can't be read."""
    out, page_no, pages = {}, 1, 1
    while page_no <= pages:
        q = urllib.parse.urlencode([("sessions[]", f"{year} Regular Session"), ("measures[]", "Bill"),
                                    ("sort", "Bill # Ascending"), ("page", page_no)])
        page = get(f"/bills/bill-search?{q}")
        if not isinstance(page, str):
            return None
        total = re.search(r"Showing \d+ - \d+ of (\d+) bills", page)
        if not total:
            if "results found" in page and page_no == 1 and "bill-result" not in page:
                return {}  # a session not begun yet
            return None
        pages = math.ceil(int(total.group(1)) / 25)
        for block in page.split('<div class="bill-result">')[1:]:
            num = re.search(r"sponsor-bill-or-resolution-tag[^>]*>\s*([A-Z]+\d\d-\d+)\s*<", block)
            if not num:
                continue
            short = re.search(r'class="all-bills-data-heading"[^>]*>(.*?)</a>', block, re.S)
            long_ = re.search(r'LONG TITLE: </span>(.*?)</p>', block, re.S)
            last = re.search(r'LAST ACTION: </span>(.*?)</div>', block, re.S)
            last = text(last.group(1)) if last else ""
            ld, _, la = last.partition(" | ")
            subj = re.search(r"SUBJECTS: </span>(.*?)</ul>", block, re.S)
            out[num.group(1)] = {
                "short": text(short.group(1)) if short else "",
                "title": text(long_.group(1)) if long_ else "",
                "subjects": [text(x) for x in re.findall(r"<li[^>]*>(.*?)</li>", subj.group(1), re.S)] if subj else [],
                "sponsors": [[text(n), slug(h)] for h, n in re.findall(r'href="(/legislators/[^"]+)">(.*?)</a>', block)],
                "lastDate": mdy(ld.strip()), "lastAction": la.strip()}
        page_no += 1
    if len(out) < int(total.group(1)):
        print(f"{year}: the list showed {len(out)} of {total.group(1)} bills")
    return out


# ---------------------------------------------------------------- bill pages

def sponsor_groups(fragment):
    """{"prime": {"house": [...], "senate": [...]}, "sponsor": {...}, "cosponsor": {...}} from the Sponsors tab; each
    member as [shown name, page slug]."""
    out = {}
    for block in re.split(r'<div class="bill-detail-', fragment)[1:]:
        head = re.match(r'[\w-]+[^>]*>\s*<p>(.*?)</p>', block, re.S)
        if not head:
            continue
        name = text(head.group(1)).lower().replace("-", "")
        key = {"prime sponsor": "prime", "sponsor": "sponsor", "cosponsor": "cosponsor"}.get(name, name)
        group = {}
        for label, sec in re.findall(r"<section[^>]*aria-label='(House|Senate) Bill Sponsors'[^>]*>(.*?)</section>", block, re.S):
            group[label.lower()] = [[text(n), slug(h)] for h, n in re.findall(r'href="(/legislators/[^"]+)">(.*?)</a>', sec)]
        out[key] = group
    return out


def summary(page):
    """The bill summary as [["p" or "li", text], ...]."""
    body = section(page, "class='bill-summary-content'", "read-more-less-btn")
    body = re.sub(r"<!--.*?-->", "", body, flags=re.S)
    out = []
    for kind, piece in re.findall(r"<(p|li|h\d)\b[^>]*>(.*?)(?=<(?:/?p|/?li|/?ul|/?ol|h\d|/h\d|/div)\b)", body, re.S):
        t = text(piece)
        if t and t != "Read more":
            out.append(["li" if kind == "li" else "head" if kind.startswith("h") else "p", t])
    return out


def parse_bill(page, num):
    head = section(page, "bill-detail-bill-number-tag", "Related Documents")
    short = re.search(r"<h1>(.*?)</h1>", head, re.S)
    long_ = re.search(r"class='bill-long-title[^']*'>(.*?)</p>", head, re.S)
    bill = {
        "number": num,
        "short": text(short.group(1)) if short else "",
        "title": text(long_.group(1)) if long_ else "",
        "type": text((re.search(r"<th>Type</th>\s*<td>(.*?)</td>", head, re.S) or [None, ""])[1]),
        "session": text((re.search(r"<th>Session</th>\s*<td>(.*?)</td>", head, re.S) or [None, ""])[1]),
        "subjects": [text(x) for x in re.findall(r'class="subject-tag">(.*?)</span>', head, re.S)],
        "summary": summary(page),
        "url": f"{SITE}/bills/{num}",
    }
    note = [p for p in bill["summary"] if p[1].startswith("(Note:")]
    bill["summaryNote"] = note[-1][1] if note else None
    badge = re.search(r"class='final-status-badge[^']*'>(.*?)</div>", page, re.S)
    bill["status"] = text(badge.group(1)) if badge else None
    # the committees each house sent it to, in order
    comm = section(page, "class='d-flex flex-column committee-block'", "</section>")
    bill["committees"] = {}
    for house, body in re.findall(r'<h3 class="chamber-title[^"]*">(\w+)</h3>(.*?)(?=<h3 class="chamber-title|$)', comm, re.S):
        bill["committees"][house.lower()] = [
            {"name": text(n), "href": h} for h, n in
            re.findall(r'class="committee-link" href="([^"]+)">.*?bill-detail-committee-title">.*?<p>(?:<i[^>]*></i>)?</p>\s*<p>(.*?)</p>', body, re.S)]
    bill["sponsors"] = sponsor_groups(section(page, 'id="bill-activity-sponsors"', 'id="bill-activity-session-laws"'))
    # tabs
    tab = lambda name, nxt: section(page, f'id="bill-activity-{name}"', f'id="bill-activity-{nxt}"' if nxt else None)
    versions = []
    for heading, body in accordions(tab("bill-text", "fiscal") + tab("fiscal", "committees")):
        for r in table_rows(body):
            versions.append({"group": re.sub(r"\s*\(\d+\)$", "", heading), "date": mdy(r.get("Date")),
                             "version": r.get("Version")})
    bill["documents"] = versions  # names and dates only: robots.txt bars the downloads
    hearings = []
    for heading, body in accordions(tab("committees", "votes")):
        d, _, c = heading.partition(" | ")
        h = {"date": mdy(d.strip()), "committee": re.sub(r"\s*\(\d+\)$", "", c).strip(), "actions": []}
        for r in table_rows(body):
            m = re.search(r"/committee_meeting_hearing_items/(\d+)/votes/(\d+)", r.get("Documents_href", ""))
            h["actions"].append({"motion": r.get("Activity"), "result": r.get("Vote"),
                                 "vote": f"c{m.group(1)}-{m.group(2)}" if m else None})
        summ = re.search(r'href="[^"]*/committee_meeting_hearing_summary/(\d+)"', body)
        h["hearingSummary"] = f"/committee_meeting_hearing_summary/{summ.group(1)}" if summ else None
        h["report"] = bool(re.search(r"Committee Report", body))
        hearings.append(h)
    bill["hearings"] = hearings
    floor = []
    for heading, body in accordions(tab("votes", "amendments")):
        house = "house" if heading.lower().startswith("house") else "senate" if heading.lower().startswith("senate") else heading
        for row in re.findall(r"<tr[^>]*role=\"row\"[^>]*>(.*?)</tr>", body, re.S):
            cells = dict((lab, cell) for lab, cell in re.findall(r'<td[^>]*data-label="([^"]*)"[^>]*>(.*?)</td>', row, re.S))
            if not cells:
                continue
            m = re.search(r"/bill_votes/(\d+)", cells.get("Vote Document", ""))
            floor.append({"house": house, "date": mdy(text(cells.get("Date", ""))), "calendar": text(cells.get("Calendar", "")),
                          "motion": text(cells.get("Motion", "")), "counts": tallies(cells.get("Vote", "")),
                          "vote": f"f{m.group(1)}" if m else None})
    bill["floorVotes"] = floor
    bill["amendments"] = [{"date": mdy(r.get("Date")), "number": r.get("Amendment Number"),
                           "where": r.get("Committee/ Floor Hearing") or r.get("Committee/Floor Hearing"),
                           "status": r.get("Status")} for r in table_rows(tab("amendments", "bill-history"))]
    bill["history"] = [{"date": mdy(r.get("Date")), "chamber": r.get("Location"), "action": r.get("Action")}
                       for r in table_rows(tab("bill-history", "sponsors"))]
    bill["sessionLaws"] = [{"effective": mdy(r.get("Effective Date")), "chapter": r.get("Chapter #"), "title": r.get("Title")}
                           for r in table_rows(tab("session-laws", None).split("Quick Links")[0])]
    acts = [h["action"] for h in bill["history"]]
    outcome = None
    for a in acts:  # newest first
        low = (a or "").lower()
        if "governor signed" in low:
            outcome = "signed"
        elif "vetoed" in low and "governor" in low:
            outcome = "vetoed"
        elif "became law without" in low:
            outcome = "law without signature"
        if outcome:
            break
    bill["outcome"] = outcome
    bill["votes"] = sorted({a["vote"] for h in hearings for a in h["actions"] if a["vote"]} |
                           {v["vote"] for v in floor if v["vote"]})
    return bill


# ---------------------------------------------------------------- votes

def vote_members(fragment):
    out = []
    for name, how in re.findall(r'<tr role="row">\s*<td>(.*?)</td>.*?class="vote-tag (\w+)"', fragment, re.S):
        out.append([text(name), how])
    return out


def parse_floor_vote(page, vid):
    main = section(page, "<main", "Quick Links")
    house = re.search(r"Votes by (House|Senate) member", main)
    info = table_rows(main)
    first = info[0] if info else {}
    bill = re.search(r"\b([A-Z]+\d\d-\d+)\b", text(main[:5000]))
    return {"id": vid, "kind": "floor", "bill": bill.group(1) if bill else None,
            "house": house.group(1).lower() if house else None, "calendar": first.get("Calendar"),
            "motion": first.get("Motion"), "time": first.get("Voted on"), "counts": tallies(main),
            "members": vote_members(section(main, "Votes by"))}


def parse_committee_vote(page, vid):
    main = section(page, "<main", "Quick Links")
    heads = [text(x) for x in re.findall(r"<h[1-3][^>]*>(.*?)</h[1-3]>", main, re.S)]
    when = re.search(r"\b((?:January|February|March|April|May|June|July|August|September|October|November|December) \d{1,2}, \d{4})\b",
                     text(main[:5000]))
    info = table_rows(main)
    first = info[0] if info else {}
    result = re.search(r'class="tag-final[^"]*">(.*?)</span>', main, re.S)
    bill = re.search(r"\b([A-Z]+\d\d-\d+)\b", text(main[:3000]))
    return {"id": vid, "kind": "committee", "bill": bill.group(1) if bill else None, "committee": heads[2] if len(heads) > 2 else None,
            "date": datetime.strptime(when.group(1), "%B %d, %Y").date().isoformat() if when else None, "motion": first.get("Motion"), "moved": first.get("Moved"),
            "seconded": first.get("Seconded"), "time": first.get("Time"),
            "result": text(result.group(1)) if result else None, "counts": tallies(main),
            "members": vote_members(section(main, "Votes by Committee Member"))}


# ---------------------------------------------------------------- members and committees

def parse_member_list(page):
    out = []
    table = section(page, "leg-data", "</table>")
    for row in re.findall(r"<tr class='mb-0'>(.*?)</tr>", table, re.S):
        cells = dict(re.findall(r'<t[dh][^>]*data-label="([^"]*)"[^>]*>(.*?)</t[dh]>', row, re.S))
        name = cells.get("Name", "")
        link = re.search(r'href="(/legislators/[^"]+)">(.*?)</a>', name, re.S)
        note = re.search(r"<div class='mb-0'>(.*?)</div>", name, re.S)
        email = re.search(r'mailto:([^"]+)"', cells.get("Email", ""))
        out.append({"slug": slug(link.group(1)) if link else None, "name": text(link.group(2)) if link else text(name),
                    "title": text(cells.get("Title", "")), "district": text(cells.get("District", "")),
                    "party": text(cells.get("Party", "")), "phone": text(cells.get("Capitol Phone #", "")) or None,
                    "email": email.group(1) if email else None, "note": text(note.group(1)) if note and text(note.group(1)) else None})
    return out


def parse_member_page(page):
    main = section(page, "<main", "Sponsored Bills")
    info = dict((text(k), text(v)) for k, v in re.findall(r"<dt>(.*?)</dt>\s*<dd>(.*?)</dd>", main, re.S))
    email = re.search(r'mailto:([^"]+)"', main)
    phone = re.search(r'href="tel:([^"]+)"', main)
    addr = re.search(r"<address>(.*?)</address>", main, re.S)
    site = re.search(r'Website:</div>\s*<a[^>]*href="([^"]+)"', main)
    return {"fullName": text((re.search(r"<h1[^>]*>(.*?)</h1>", main, re.S) or [None, ""])[1]),
            "party": info.get("PARTY"), "leadership": info.get("LEADERSHIP POSITION"),
            "counties": [text(x) for x in re.findall(r"<li>(.*?)</li>", section(main, 'class="county-list"', "</ul>"), re.S)],
            "district": text((re.search(r'class="district-number">(.*?)</div>', main, re.S) or [None, ""])[1]),
            "email": email.group(1) if email else None, "phone": phone.group(1) if phone else None,
            "address": ", ".join(t for t in (text(x) for x in re.split(r"<br\s*/?>", addr.group(1))) if t) if addr else None, "website": site.group(1) if site else None,
            "committees": [{"name": text(n), "href": h} for h, n in
                           re.findall(r'class="committee-link d-block"[^>]*href="([^"]+)">.*?<span>([^<]*)</span>\s*</div>',
                                      section(main, "committee-assignments-block", "legislator-address-block"), re.S)]}


def parse_committee(page):
    main = section(page, "<main", "Committee Activity")
    members = []
    for label, h, body in re.findall(r'<a class="cm-link" aria-label="([^"]*)" href="([^"]+)">(.*?)</a>', main, re.S):
        role = re.search(r"class='comm-mem-role'>(.*?)</div>", body, re.S)
        name = re.search(r"class='comm-member-name'>(.*?)</p>", body, re.S)
        title = re.search(r"comm-member-tile-content'>\s*<p>(.*?)</p>", body, re.S)
        members.append({"slug": slug(h), "name": text(name.group(1)) if name else "",
                        "title": text(title.group(1)) if title else "", "role": text(role.group(1)) if role else None})
    days = [[text(a), text(b), text(c)] for a, b, c in re.findall(
        r'meeting-day-title[^>]*>(.*?)</p>\s*<p[^>]*>(.*?)</p>.*?meeting-chamber-title[^>]*>(.*?)</p>', main, re.S)]
    return {"members": members, "meetings": days,
            "heading": text((re.search(r"class='[^']*committee-type[^']*'[^>]*>(.*?)<", main, re.S) or [None, ""])[1]) or None}


def members_and_committees(year, folder):
    live = not finished(year)
    sess = f"{year}a"
    mpath = os.path.join(folder, "members.json")
    age = (time.time() - os.path.getmtime(mpath)) / 86400 if os.path.exists(mpath) else None
    if age is None or (live and age >= REFRESH_DAYS) or (not live and load(mpath, {}).get("asOf", "") < f"{year}-06-20"):
        page = get(f"/legislators?sess={sess}")
        members = parse_member_list(page) if isinstance(page, str) else []
        bad = not members
        for m in members:
            if not m["slug"]:
                continue
            p = get(f"/legislators/{m['slug']}")
            if isinstance(p, str):
                m["page"] = parse_member_page(p)
            else:
                bad = True
        if members and not bad:
            save(mpath, {"asOf": TODAY.isoformat(), "session": sess, "members": members})
            print(f"{year}: {len(members)} members", flush=True)
        else:
            if not os.path.exists(mpath):  # only a list never read holds the state off the site
                INCOMPLETE.add(f"{year}:members")
            print(f"{year}: member list incomplete; kept the last copy", flush=True)
    cpath = os.path.join(folder, "committees.json")
    age = (time.time() - os.path.getmtime(cpath)) / 86400 if os.path.exists(cpath) else None
    if age is None or (live and age >= REFRESH_DAYS) or (not live and load(cpath, {}).get("asOf", "") < f"{year}-06-20"):
        page = get(f"/committees?sess={sess}")
        links = []
        if isinstance(page, str):
            for h in re.findall(rf'href="(/committees/{year}A/(?:house|senate|year-round)/[^"]+)"', page, re.I):
                if h not in links:
                    links.append(h)
        out, bad = [], not links
        for h in links:
            p = get(h)
            if not isinstance(p, str):
                bad = True
                continue
            c = parse_committee(p)
            name = re.search(r"<h1[^>]*>(.*?)</h1>", section(p, "<main"), re.S)
            c.update({"href": h, "kind": h.split("/")[3], "name": text(name.group(1)) if name else h.rsplit("/", 1)[-1]})
            out.append(c)
        if out and not bad:
            save(cpath, {"asOf": TODAY.isoformat(), "session": sess, "committees": out})
            print(f"{year}: {len(out)} committees", flush=True)
        elif not os.path.exists(cpath):  # a failed refresh keeps the last copy
            INCOMPLETE.add(f"{year}:committees")


# ---------------------------------------------------------------- one session

def session(year):
    folder = os.path.join(DATA, str(year))
    for sub in ("bills", "votes"):
        os.makedirs(os.path.join(folder, sub), exist_ok=True)
    final = finished(year)
    cutoff = f"{year}-06-20"
    lpath = os.path.join(folder, "list.json")
    old_list = load(lpath)
    if final and old_list and old_list.get("asOf", "") > cutoff:
        listing = old_list["bills"]
    else:
        listing = bill_list(year)
        if listing is None:
            print(f"{year}: no bill list; kept the last copy", flush=True)
            if not old_list:
                INCOMPLETE.add(f"{year}:list")
            listing = (old_list or {}).get("bills", {})
        elif listing:
            save(lpath, {"asOf": TODAY.isoformat(), "bills": listing})
    if not listing:
        print(f"{year}: no bills yet", flush=True)
        return

    def path_of(num):
        return os.path.join(folder, "bills", f"{num}.json")

    todo, stale = [], []
    for num, entry in listing.items():
        old = load(path_of(num))
        if not old:
            todo.append(num)
        elif final:
            if old.get("fetched", "") < cutoff:
                todo.append(num)
        elif (old.get("listDate"), old.get("listAction")) != (entry["lastDate"], entry["lastAction"]):
            todo.append(num)
        else:
            stale.append((old.get("fetched", ""), num))
    if not final:
        # Each bill read again once it's REFRESH_DAYS old, at most a seventh of the list a run (runs are two hours apart).
        week = (datetime.now() - timedelta(days=REFRESH_DAYS)).isoformat(timespec="seconds")
        stale.sort()
        todo += [n for f, n in stale[:math.ceil(len(listing) / REFRESH_DAYS)] if f < week]
    key = lambda n: (n[:2], int(re.sub(r"\D", "", n.split("-", 1)[1]) or 0))
    todo = sorted(dict.fromkeys(todo), key=key)
    print(f"{year}: {len(listing)} bills listed, {len(todo)} to read", flush=True)

    got = failed = 0
    for num in todo:
        if out_of_time():
            break
        page = get(f"/bills/{num}")
        if not isinstance(page, str):
            failed += 1
            continue
        try:
            bill = parse_bill(page, num)
        except Exception as e:
            print(f"{num}: couldn't read the page ({e})")
            failed += 1
            continue
        if not bill["history"]:
            print(f"{num}: no history on the page")
            failed += 1
            continue
        entry = listing.get(num, {})
        bill["listDate"], bill["listAction"] = entry.get("lastDate"), entry.get("lastAction")
        bill["fetched"] = datetime.now().isoformat(timespec="seconds")
        save(path_of(num), bill)
        got += 1
        if got % 100 == 0:
            print(f"{year}: {got} of {len(todo)} bills read", flush=True)
    # A bill whose refresh failed keeps its last copy; only bills never read make the copy incomplete.
    if any(not os.path.exists(path_of(n)) for n in listing):
        INCOMPLETE.add(f"{year}:bills")
    print(f"{year}: {got} of {len(todo)} bills read ({failed} failed)", flush=True)

    votes, linked = set(), {}
    for num in listing:
        b = load(path_of(num))
        if b:
            votes.update(b.get("votes", []))
            for v in b.get("votes", []):
                linked.setdefault(v, num)
    vtodo = sorted(v for v in votes if not os.path.exists(os.path.join(folder, "votes", f"{v}.json")))
    print(f"{year}: {len(votes)} votes, {len(vtodo)} to read (after every year's bills)", flush=True)
    PENDING_VOTES.append((year, folder, vtodo, linked))

    members_and_committees(year, folder)


def read_votes():
    """Members' votes, after every year's bills (so a run spent on votes never skips a year's bill updates), until the
    time limit. Votes still to read don't hold the state off the site: its bills are whole, and members' votes fill in
    run by run (each vote is read once)."""
    for year, folder, vtodo, linked in PENDING_VOTES:
        vgot = 0
        for vid in vtodo:
            if out_of_time():
                break
            if vid.startswith("f"):
                page = get(f"/bill_votes/{vid[1:]}")
                parse = parse_floor_vote
            else:
                item, vote = vid[1:].split("-")
                page = get(f"/committee_meeting_hearing_items/{item}/votes/{vote}")
                parse = parse_committee_vote
            if isinstance(page, str):
                v = parse(page, vid)
                v["bill"] = v["bill"] or linked.get(vid)
                if v["members"] or v["counts"]:
                    save(os.path.join(folder, "votes", f"{vid}.json"), v)
                    vgot += 1
            if vgot and vgot % 500 == 0:
                print(f"{year}: {vgot} of {len(vtodo)} votes read", flush=True)
        print(f"{year}: {vgot} of {len(vtodo)} votes read now" + (f"; {len(vtodo) - vgot} left for later runs" if vgot < len(vtodo) else ""), flush=True)


def begun(year):
    """Whether a year's session has convened (the second Wednesday of January)."""
    return TODAY >= date(year, 1, 1 + (2 - date(year, 1, 1).weekday()) % 7 + 7)


def finish():
    marker = os.path.join(DATA, "incomplete")
    # A session not yet begun (prefiled bills, no members yet) is read when it's there but never holds Colorado back.
    undone = {g for g in INCOMPLETE if not g[:4].isdigit() or begun(int(g[:4]))}
    if undone:
        with open(marker, "w") as f:
            f.write(" ".join(sorted(undone)) + "\n")
    elif os.path.exists(marker):
        os.remove(marker)


def main():
    os.makedirs(DATA, exist_ok=True)
    marker = os.path.join(DATA, "incomplete")
    WHOLE[0] = not os.path.exists(marker)
    if not os.path.exists(marker):  # until this run finishes, the copy may be partial
        with open(marker, "w") as f:
            f.write("running\n")
    robots()
    started = time.time()
    for y in YEARS:
        session(y)
    read_votes()
    print(f"done in {(time.time() - started) / 60:.0f} minutes", flush=True)
    finish()


if __name__ == "__main__":
    main()
