#!/usr/bin/env python3
"""Download Wisconsin's bills from the Legislature's document site, https://docs.legis.wisconsin.gov/ (plain HTML;
robots.txt disallows only /feed/, /search, /frame/ and a few other features, none used here, and sets no crawl
delay). One request at a time, a second apart.

For each two-year session (2023 = 2023-2024, 2025 = 2025-2026; regular session only, not special sessions):
- The Assembly and Senate bill lists (/<year>/proposals/reg/asm/bill, .../sen/bill: every bill with its status line
  and relating clause) into data/wi/<year>/list.json, with the joint resolutions that propose constitutional
  amendments (/<year>/proposals/reg/asm/joint_resolution, .../sen/...: those whose relating clause says "(first
  consideration)" or "(second consideration)"; AJR5, SJR12). Other resolutions are left out. Below, "bill" includes them.
- Each bill's history page (/<year>/proposals/reg/asm/bill/ab1) parsed into data/wi/<year>/bills/<AB1>.json: the
  title, status, authors (first-house members, in order) and cosponsors (the other house's), each history line with
  its date, house, plain text and the vote, committee, amendment and act it links to, and the page's document links
  (acts, committee records, memos, companion bills under "See Also"). The Legislative Reference Bureau's analysis
  of the bill as introduced comes from its text page (/<year>/related/proposals/ab1), read once per bill.
  A finished session's bills are read once. The current session's are read again when the list shows a new status or
  relating clause, when a journal published since the last run names the bill, and otherwise in turn, the seventh of
  them read longest ago each run, so every bill is read at least weekly (committee hearings and executive sessions
  aren't in the journals or the status line).
- Each floor roll call the histories link to (/<year>/related/votes/assembly/av0006, .../senate/sv0086), member by
  member, into votes/<av0006>.json, once.
- Each Record of Committee Proceedings the bill pages link to (/<year>/related/records/<house>/<committee>/<id>: the
  committee's hearings and executive sessions on that bill, with each motion's ayes and noes by name) into
  rocp/<id>.json, once.
- The members (/<year>/legislators/assembly and /senate: name, district, party, home town, leadership title, Madison
  office, phones, email, website, member id) into members.json, every run; the committees (/<year>/committees/assembly,
  /senate, /joint, then each committee's page: members with "(Chair)" and the like, by member id) into
  committees.json, once a week for the current session.
data/wi/incomplete lists what was never downloaded (a failed refresh keeps the last copy; roll calls, committee records
and journals still to read count only until a run leaves nothing missing); it is removed when nothing is missing.
Usage: python3 states/wi/fetch.py [first_year]   (default: the session before this one, and this one)
"""
import html, json, math, os, re, sys, time, urllib.error, urllib.request
from collections import Counter
from datetime import date, datetime, timedelta

SITE = "https://docs.legis.wisconsin.gov"
DATA = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "wi"))
AGENT = "statebilltracker.org (a nonprofit bill tracker; contact via github.com/judithhubbard)"
YEAR = date.today().year
CURRENT = YEAR if YEAR % 2 else YEAR - 1
FIRST = int(sys.argv[1]) if len(sys.argv) > 1 else CURRENT - 2
HOUSES = {"asm": ("AB", "assembly"), "sen": ("SB", "senate")}
# The lists read: (house, kind, number prefix). Joint resolutions are kept only for constitutional amendments.
KINDS = [("asm", "bill", "AB"), ("sen", "bill", "SB"), ("asm", "joint_resolution", "AJR"), ("sen", "joint_resolution", "SJR")]
AMENDMENT = re.compile(r"\((?:first|second) consideration\)", re.I)


def split_num(num):
    """"AJR12" -> ("AJR", 12)."""
    m = re.match(r"([A-Z]+)(\d+)$", num)
    return m.group(1), int(m.group(2))


def page_path(year, num):
    """A bill's or joint resolution's page: /2025/proposals/reg/asm/bill/ab1, .../sen/joint_resolution/sjr3."""
    prefix, _ = split_num(num)
    house = "asm" if prefix[0] == "A" else "sen"
    kind = "joint_resolution" if prefix.endswith("JR") else "bill"
    return f"/{year}/proposals/reg/{house}/{kind}/{num.lower()}"
REFRESH_DAYS = 7  # every current-session bill is read again at least this often
INCOMPLETE = set()
WHOLE = [True]  # the last run left nothing missing (set in main): the first copy is whole


def extra(item):
    """Roll calls, committee records and journals still to read (and a refusal) hold only a first copy; once it is
    whole, they fill in on later runs."""
    if not WHOLE[0]:
        INCOMPLETE.add(item)
MISSING = object()  # a page that answers 404
# The run's own time limit (FETCH_MINUTES, set by the workflow): stop a few minutes early, with everything read so far
# saved and a summary printed, rather than be cut off silently mid-request.
START = time.time()
BUDGET = max(0.0, float(os.environ.get("FETCH_MINUTES") or 0) - 5) * 60
FAILS = Counter()  # why requests failed, for the summary


def out_of_time():
    return BUDGET and time.time() - START > BUDGET


def progress(label, i, total, got):
    if i and i % 25 == 0:
        print(f"{label}: {i} of {total} tried, {got} read, {round((time.time() - START) / 60)} min"
              + (f"; failures {dict(FAILS)}" if FAILS else ""), flush=True)


def get(path, timeout=30):
    """The page's text; MISSING for a 404, None when it can't be read. Stops the run if the site refuses us. The large
    pages (bill lists, journal indexes, member and committee lists: hundreds of KB, slow from GitHub's machines) are
    given up to three minutes; the thousands of small ones 30 seconds."""
    for attempt in range(3):
        if out_of_time():
            return None
        time.sleep(1)
        try:
            req = urllib.request.Request(SITE + path, headers={"User-Agent": AGENT})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return MISSING
            FAILS[f"HTTP {e.code}"] += 1
            if e.code in (401, 403, 429):
                print(f"{path}: refused ({e.code}); stopping")
                extra(f"refused:{e.code}")
                finish()
                sys.exit(1)
            time.sleep(10 * (attempt + 1))
        except Exception as e:
            FAILS[type(e).__name__] += 1
            time.sleep(10 * (attempt + 1))
    return None


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


def text(fragment):
    """Plain text of an HTML fragment, whitespace collapsed."""
    fragment = re.sub(r"<br\s*/?>", " ", fragment)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", fragment))).strip()


def main_part(page):
    i = page.find('id="main_content"')
    return page[i:] if i >= 0 else page


# ---------------------------------------------------------------- bill lists

def bill_list(year, house, kind="bill"):
    """{"AB1": {"status": "A - Veto Sustained", "relating": "Relating to: ..."}} from a house's bill (or joint
    resolution) list, or None."""
    page = get(f"/{year}/proposals/reg/{house}/{kind}", timeout=180)
    if not isinstance(page, str):
        return None
    out = {}
    for m in re.finditer(rf'<a href="/\d+/proposals/reg/\w+/{kind}/([a-z]+)(\d+)">[^<]*</a></div>\s*'
                         r'<div class="span3">(.*?)</div>\s*<div class="span6">(.*?)</div>', page, re.S):
        out[f"{m.group(1).upper()}{m.group(2)}"] = {"status": text(m.group(3)), "relating": text(m.group(4))}
    if kind == "joint_resolution":
        out = {k: v for k, v in out.items() if AMENDMENT.search(v["relating"])}
    return out


# ---------------------------------------------------------------- journals (the change signal)

def journal_bills(year, folder):
    """Bills named in each house's journals published since the last run (and the newest one again, since a day's
    journal can be corrected). Returns (set of "AB12", journals newly read, all journal paths read now)."""
    first = load(os.path.join(folder, "journals.json")) is None  # the first run reads every bill anyway
    seen = set(load(os.path.join(folder, "journals.json"), []))
    named, read = set(), []
    for house in ("assembly", "senate"):
        index = get(f"/{year}/related/journals/{house}", timeout=180)
        if not isinstance(index, str):
            extra(f"{year}:journals")
            continue
        days = sorted(set(re.findall(rf'href="(/{year}/related/journals/{house}/\d{{8}})"', index)))
        if first:
            read += days
            continue
        todo = [d for d in days if d not in seen] + days[-1:]
        for d in dict.fromkeys(todo):
            page = get(d)
            if not isinstance(page, str):
                extra(f"{year}:journals")
                continue
            body = text(main_part(page))
            for kind, jr, num in re.findall(r"\b(Assembly|Senate) (Joint Resolutions?|Bills?) (\d+)", body):
                named.add(kind[0] + ("JR" if jr.startswith("Joint") else "B") + num)
            # "Senate Bills 12, 15 and 20" lists
            for kind, jr, nums in re.findall(r"\b(Assembly|Senate) (Joint Resolutions|Bills) ((?:\d+, )*\d+,? and \d+)", body):
                for num in re.findall(r"\d+", nums):
                    named.add(kind[0] + ("JR" if jr.startswith("Joint") else "B") + num)
            read.append(d)
    return named, read, seen


# ---------------------------------------------------------------- bill pages

def people(fragment):
    """[{"name": "Kitchens", "id": "2744"}, ...] for the legislator links in a fragment; committees as names."""
    out = []
    for m in re.finditer(r'<a rel="(legislator|committee)/\d+/(\d+)"[^>]*>(.*?)</a>', fragment, re.S):
        out.append({"name": text(m.group(3)), "id": m.group(2), "kind": m.group(1)})
    return out


def history_row(row):
    m = re.search(r'<td class="date">\s*([\d/]+)\s*<abbr class="house" title="(\w+)"', row)
    entry = re.search(r'<td class="entry">(.*?)</td>', row, re.S)
    journal = re.search(r'<td class="journal[^"]*"><a href="([^"]+)"[^>]*>([^<]*)</a>', row)
    if not m or not entry:
        return None
    e = entry.group(1)
    d = datetime.strptime(m.group(1), "%m/%d/%Y").date().isoformat()
    line = {"date": d, "house": m.group(2), "action": text(e)}
    refs = re.findall(r'rel="([^"]+)"', e)
    for kind, key in (("votes", "votes"), ("committee", "committees"), ("amends", "amendments"), ("acts", "acts"),
                      ("legislator", "legislators")):
        got = [r.split("/")[-1] for r in refs if r.startswith(kind + "/")]
        if got:
            line[key] = got
    if journal:
        line["journal"] = {"url": journal.group(1), "page": journal.group(2).strip()}
    return line


def sponsors(intro_html):
    """Authors (the first house's members, in order) and cosponsors (the other house's), each with member ids;
    `by` is the introduction as written (committees and "by request of" included)."""
    parts = re.split(r";\s*(?:<br\s*/?>)?\s*cosponsored by", intro_html, maxsplit=1)
    authors = [p for p in people(parts[0])]
    cos = people(parts[1]) if len(parts) > 1 else []
    return {"by": text(intro_html), "authors": authors, "cosponsors": cos}


def parse_bill(page, num, year):
    body = main_part(page)
    out = {"number": num, "session": year}
    m = re.search(r'<div class="proposalTitle">\s*<h1>(.*?)</h1>', body, re.S)
    out["heading"] = text(m.group(1)) if m else ""
    m = re.search(r'</h1>\s*</div>\s*<div>\s*<p>(.*?)</p>', body, re.S)
    out["title"] = text(m.group(1)) if m else ""
    r = re.search(r"Relating to:\s*(.*)", out["title"])
    out["relating"] = r.group(1).strip() if r else ""
    m = re.search(r'<div class="propStatus">\s*<h2>Status:\s*(.*?)</h2>', body, re.S)
    out["status"] = text(m.group(1)) if m else ""
    links = re.search(r'<div class="propLinks[^"]*">(.*?)<h2>See Also</h2>(.*?)</ul>', body, re.S)
    docs, see = [], []
    if links:
        for li in re.findall(r"<li><p>(.*?)</p></li>", links.group(1), re.S):
            a = re.search(r'<a href="([^"]+)"[^>]*>(.*?)</a>', li, re.S)
            if a:
                docs.append({"text": text(a.group(2)), "href": html.unescape(a.group(1))})
        for li in re.findall(r"<li><p>(.*?)</p></li>", links.group(2), re.S):
            a = re.search(r'<a href="([^"]+)"[^>]*>(.*?)</a>(.*)', li, re.S)
            if a:
                see.append({"text": text(a.group(2)), "href": a.group(1),
                            "status": text(a.group(3)).lstrip("- ").strip()})
    out["links"], out["seeAlso"] = docs, see
    hist = body[body.find('<div class="propHistory">'):] if '<div class="propHistory">' in body else ""
    rows = re.findall(r'<tr class="historyRow">(.*?)</tr>', hist, re.S)
    out["history"] = [h for h in (history_row(r) for r in rows) if h]
    intro = next((re.search(r'<td class="entry">(.*?)</td>', r, re.S).group(1) for r in rows
                  if re.search(r'<td class="entry">\s*Introduced\b', r)), "")
    out.update(sponsors(intro))
    out["votes"] = list(dict.fromkeys(v for h in out["history"] for v in h.get("votes", [])))
    out["rocps"] = list(dict.fromkeys(re.sub(r"\.(pdf|html)$", "", d["href"]) for d in docs
                                      if "/related/records/" in d["href"]))
    return out


def analysis(page):
    """The Legislative Reference Bureau's analysis paragraphs from a bill's text page: [["text", "..."], ["head",
    "..."], ...] by the page's own div classes (qsanal_text, qsanal_head ...); [] if the bill has none."""
    out = []
    # 2025's pages write the classes "qsanal_text"; 2023's "qs_anal_text_".
    for cls, inner in re.findall(r'<div class="qs_?anal_(\w+?)_?(?:\s[^"]*)?"[^>]*>(.*?)</div>', page, re.S):
        if cls in ("line", "space", "title_bylrb"):
            continue
        t = text(inner)
        if t:
            out.append([cls, t])
    return out


# ---------------------------------------------------------------- roll calls

def parse_vote(page, vid):
    body = main_part(page)
    doc = body[body.find('id="document"'):]
    out = {"id": vid, "house": "Assembly" if vid.startswith("av") else "Senate"}
    head = re.search(r'<b style="font-size: 1.2em">(.*?)</b>(.*?)</p>', doc, re.S)
    if head:
        out["item"] = text(head.group(1))
        lines = [text(x) for x in re.split(r"<br\s*/?>", head.group(2)) if text(x)]
        out["heading"] = lines  # ["BY KITCHENS", "CELL PHONE USAGE POLICIES IN SCHOOLS", "PASSAGE"]
    members = []
    if out["house"] == "Assembly":
        m = re.search(r"AYES - (\d+)\s+NAYS - (\d+)\s+NOT VOTING - (\d+)(?:\s+PAIRED - (\d+))?", text(doc))
        if m:
            out["totals"] = {"yes": int(m.group(1)), "no": int(m.group(2)), "nv": int(m.group(3)),
                             "paired": int(m.group(4) or 0)}
        for t in re.findall(r'<table class="assembly-names">(.*?)</table>', doc, re.S):
            for row in re.findall(r"<tr>(.*?)</tr>", t, re.S):
                cells = [text(c) for c in re.findall(r"<td[^>]*>(.*?)</td>", row, re.S)]
                if len(cells) >= 4 and cells[3]:
                    vote = "Y" if cells[0] else "N" if cells[1] else "NV" if cells[2] else ""
                    members.append({"name": cells[3], "party": cells[4] if len(cells) > 4 else "", "vote": vote})
    else:
        totals = {}
        for label, n, names in re.findall(r'<td class="vote-count">\s*([A-Z ]+?) - (\d+)\s*</td>\s*<td>(.*?)</table>',
                                          doc, re.S):
            key = {"AYES": "Y", "NAYS": "N", "NOT VOTING": "NV", "PAIRED": "P"}.get(label.strip(), label.strip())
            totals[key] = int(n)
            for c in re.findall(r"<td[^>]*>(.*?)</td>", names, re.S):
                if text(c):
                    members.append({"name": text(c), "vote": key})
        out["totals"] = totals
    out["members"] = members
    # The footer: vacancies, pairs, presiding officer, sequence number, date and time.
    out["notes"] = [text(p) for p in re.findall(r'<p style="font-family: sans-serif"[^>]*>(.*?)</p>', doc, re.S)
                    if text(p)]
    m = re.search(r"SEQUENCE NO\. (\d+)\s*<br>\s*\w+, (\w+ \d+, \d{4})\s*<br>\s*([\d:]+ [AP]M)", doc)
    if m:
        out["sequence"] = int(m.group(1))
        out["date"] = datetime.strptime(m.group(2), "%B %d, %Y").date().isoformat()
        out["time"] = m.group(3)
    return out


# ---------------------------------------------------------------- committee records

TITLES = r"(?:Senators?|Representatives?)"


def names(s):
    """'Representative Gustafson; Representatives VanderMeer, Spiros and Tusler.' ->
    [{"title": "Representative", "name": "Gustafson"}, ...]; "None." -> []."""
    out = []
    for part in s.rstrip(". ").split(";"):
        part = part.strip()
        m = re.match(rf"({TITLES})\s+(.*)", part)
        if not m:
            continue
        title = re.sub(r"s$", "", m.group(1))
        for n in re.split(r",\s*|\s+and\s+", m.group(2)):
            if n.strip():
                out.append({"title": title, "name": n.strip()})
    return out


def parse_rocp(page, path):
    """A committee's record on one bill: its paragraphs as written, and each meeting's attendance and motions."""
    doc = page[page.find('id="document"'):]
    doc = doc[:doc.find('id="nodePath"')]
    paras = [text(p) for p in re.findall(r"<p\b[^>]*>(.*?)</p>", doc, re.S)]
    paras = [p for p in paras if p]
    out = {"path": path, "paragraphs": paras, "meetings": []}
    meeting = motion = None
    for p in paras:
        m = re.match(r"([A-Z][a-z]+ \d{1,2}, \d{4})\s+(.*)", p)
        if m:
            try:
                d = datetime.strptime(m.group(1), "%B %d, %Y").date().isoformat()
            except ValueError:
                d = m.group(1)
            meeting = {"date": d, "event": m.group(2), "motions": []}
            out["meetings"].append(meeting)
            motion = None
            continue
        if meeting is None:
            continue
        m = re.match(r"(Present|Absent|Excused):\s*\((\d+)\)\s*(.*)", p)
        if m and motion is None:
            meeting[m.group(1).lower()] = names(m.group(3))
            continue
        if p.startswith("Moved by"):
            motion = {"motion": p}
            meeting["motions"].append(motion)
            continue
        m = re.match(r"(Ayes|Noes|Absent|Excused|Not Voting):\s*\((\d+)\)\s*(.*)", p)
        if m and motion is not None:
            motion[m.group(1).lower()] = names(m.group(3))
            motion[m.group(1).lower() + "Count"] = int(m.group(2))
            continue
        if motion is not None and re.match(r"[A-Z][A-Z0-9 ,.'()-]{3,}.*\bAyes \d+", p):
            motion["result"] = p  # "PASSAGE AS AMENDED RECOMMENDED, Ayes 4, Noes 2"
            motion = None
    return out


# ---------------------------------------------------------------- members and committees

def parse_members(page, house):
    out = []
    for block in re.split(r'<div class="rounded', page)[1:]:
        m = re.search(r'id="district(\d+)"', block)
        if not m:
            continue
        p = {"house": house, "district": int(m.group(1))}
        a = re.search(r'alt="Picture of (?:Senator|Representative) ([^"]*)"', block)
        p["fullName"] = html.unescape(a.group(1)) if a else ""
        a = re.search(r"<strong>\s*(?:<a[^>]*>)?([^<]+?)(?:</a>)?\s*</strong>\s*<small>\(([^)]*)\)</small>", block)
        if a:
            p["name"] = html.unescape(a.group(1)).strip()
            party, _, town = a.group(2).partition(" - ")
            p["party"], p["town"] = party.strip(), town.strip()
        head = block[:block.find("<small>District")]
        p["titles"] = [text(t) for t in re.findall(r"<strong>([^<]*)</strong>", head) if text(t)]  # leadership
        d = re.search(r'href="/\d+/legislators/\w+/(\d+)">Details', block)
        p["id"] = d.group(1) if d else ""
        w = re.search(r'<a href="([^"]+)">\s*Website</a>', block)
        p["website"] = w.group(1) if w else ""
        for cls in ("office", "telephone", "fax", "email", "voting_address"):
            s = re.search(rf"<span class='info {cls}'>(.*?)</span>\s*(?:<span class='info|<br />|$)", block, re.S)
            if not s:
                continue
            inner = re.sub(r"<span class='title'>.*?</span>", "", s.group(1), flags=re.S)
            vals = [text(x) for x in re.split(r"<br\s*/?>", inner) if text(x)]
            p[cls] = vals
        out.append(p)
    return out


def committee_links(year):
    out = []
    for kind in ("assembly", "senate", "joint"):
        page = get(f"/{year}/committees/{kind}", timeout=180)
        if not isinstance(page, str):
            if not os.path.exists(os.path.join(DATA, str(year), "committees.json")):  # else the last copy stays
                INCOMPLETE.add(f"{year}:committees")
            continue
        for cid, name in re.findall(r'<a href="/document/committee/\d+/(\d+)">([^<]+)</a>', main_part(page)):
            out.append({"id": cid, "kind": kind, "name": html.unescape(name).strip()})
    return out


def parse_committee(page):
    body = main_part(page)
    sec = re.search(r'<div id="members"><h2>Members</h2>(.*?)</div>', body, re.S)
    members = []
    for lid, label in re.findall(r'<a href="[^"]*/legislator(?:s/\w+)?/\d+/(\d+)">([^<]*)</a>', sec.group(1) if sec else ""):
        label = html.unescape(label).strip()
        role = re.search(r"\(([^)]*)\)\s*$", label)
        members.append({"id": lid, "name": re.sub(r"\s*\([^)]*\)\s*$", "", label),
                        "role": role.group(1) if role else ""})
    clerk = re.search(r'<div id="Committee Clerk">.*?<p>(.*?)</p>', body, re.S)
    return {"members": members, "clerk": text(clerk.group(1)) if clerk else ""}


# ---------------------------------------------------------------- one session

def session(year):
    folder = os.path.join(DATA, str(year))
    for sub in ("bills", "votes", "rocp"):
        os.makedirs(os.path.join(folder, sub), exist_ok=True)
    live = year >= CURRENT

    listing = {}
    for house, kind, prefix in KINDS:
        got = bill_list(year, house, kind)
        if got is None:
            print(f"{year} {house} {kind}: no list; kept the last copy")
            if kind == "bill" and not os.path.exists(os.path.join(folder, "list.json")):
                INCOMPLETE.add(f"{year}:list")  # a missing amendment list, or a failed refresh, doesn't hold back the bills
            got = {k: v for k, v in (load(os.path.join(folder, "list.json"), {}) or {}).items()
                   if split_num(k)[0] == prefix}
        listing.update(got)
    if listing:
        save(os.path.join(folder, "list.json"), listing)

    named, journals_read, journals_seen = (journal_bills(year, folder) if live else (set(), [], set()))

    def path_of(num):
        return os.path.join(folder, "bills", f"{num}.json")

    todo, stale = [], []
    for num, entry in listing.items():
        old = load(path_of(num)) if live or not os.path.exists(path_of(num)) else True
        if not old:
            todo.append(num)
        elif live and (old.get("listStatus") != entry["status"] or old.get("listRelating") != entry["relating"]
                       or num in named or "analysis" not in old):
            todo.append(num)
        elif live:
            stale.append((old.get("fetched", ""), num))
    if live:
        # Each bill read again once it's REFRESH_DAYS old, at most a seventh of the list a run (runs are two hours apart).
        week = (datetime.now() - timedelta(days=REFRESH_DAYS)).isoformat(timespec="seconds")
        stale.sort()
        todo += [n for f, n in stale[:math.ceil(len(listing) / REFRESH_DAYS)] if f < week]
    todo = sorted(dict.fromkeys(todo), key=split_num)
    print(f"{year}: {len(listing)} bills listed, {len(todo)} to read", flush=True)

    got = failed = 0
    for i, num in enumerate(todo):
        progress(f"{year} bills", i, len(todo), got)
        if out_of_time():
            break
        page = get(page_path(year, num))
        if not isinstance(page, str):
            failed += 1
            continue
        try:
            bill = parse_bill(page, num, year)
        except Exception as e:
            print(f"{num}: couldn't read the page ({e})")
            failed += 1
            continue
        if not bill["history"]:
            failed += 1
            continue
        old = load(path_of(num), {}) or {}
        if "analysis" in old:
            bill["analysis"] = old["analysis"]
        else:
            t = get(f"/{year}/related/proposals/{num.lower()}")
            if isinstance(t, str):
                bill["analysis"] = analysis(t)
            elif t is MISSING:
                bill["analysis"] = []
        entry = listing.get(num, {})
        bill["listStatus"], bill["listRelating"] = entry.get("status"), entry.get("relating")
        bill["fetched"] = datetime.now().isoformat(timespec="seconds")
        save(path_of(num), bill)
        got += 1
        if got % 250 == 0:
            print(f"{year}: {got} of {len(todo)} bills read", flush=True)
    # A bill whose refresh failed keeps its last copy; only bills never read make the copy incomplete.
    if any(not os.path.exists(path_of(n)) for n in listing):
        INCOMPLETE.add(f"{year}:bills")
    print(f"{year}: {got} of {len(todo)} bills read ({failed} failed)", flush=True)
    if live and not failed and not out_of_time():  # the journals' changes are only "seen" once their bills are read
        save(os.path.join(folder, "journals.json"), sorted(journals_seen | set(journals_read)))

    votes, rocps = set(), set()
    for num in listing:
        b = load(path_of(num))
        if b:
            votes.update(b.get("votes", []))
            rocps.update(b.get("rocps", []))
    vtodo = sorted(v for v in votes if not os.path.exists(os.path.join(folder, "votes", f"{v}.json")))
    vgot = 0
    for i, vid in enumerate(vtodo):
        progress(f"{year} roll calls", i, len(vtodo), vgot)
        if out_of_time():
            break
        kind = "assembly" if vid.startswith("av") else "senate"
        page = get(f"/{year}/related/votes/{kind}/{vid}")
        if isinstance(page, str):
            v = parse_vote(page, vid)
            if v["members"]:
                save(os.path.join(folder, "votes", f"{vid}.json"), v)
                vgot += 1
    if vgot < len(vtodo):
        extra(f"{year}:votes")
    print(f"{year}: {len(votes)} roll calls ({vgot} of {len(vtodo)} read now)", flush=True)

    rtodo = sorted(r for r in rocps if not os.path.exists(os.path.join(folder, "rocp", r.rsplit("/", 1)[-1] + ".json")))
    rgot = 0
    for i, path in enumerate(rtodo):
        progress(f"{year} committee records", i, len(rtodo), rgot)
        if out_of_time():
            break
        page = get(path)
        if isinstance(page, str) and 'id="document"' in page:
            save(os.path.join(folder, "rocp", path.rsplit("/", 1)[-1] + ".json"), parse_rocp(page, path))
            rgot += 1
    if rgot < len(rtodo):
        extra(f"{year}:rocp")
    print(f"{year}: {len(rocps)} committee records ({rgot} of {len(rtodo)} read now)", flush=True)

    members_and_committees(year, folder, live)


def members_and_committees(year, folder, live):
    mpath = os.path.join(folder, "members.json")
    if live or not os.path.exists(mpath):
        members = []
        for house in ("assembly", "senate"):
            page = get(f"/{year}/legislators/{house}", timeout=180)
            got = parse_members(main_part(page), house) if isinstance(page, str) else []
            if not got:
                if not os.path.exists(mpath):  # a failed refresh keeps the last copy
                    INCOMPLETE.add(f"{year}:members")
                members = None
                break
            members += got
        if members:
            save(mpath, members)
            print(f"{year}: {len(members)} members", flush=True)
        else:
            print(f"{year}: no member list; kept the last copy")
    cpath = os.path.join(folder, "committees.json")
    age = (time.time() - os.path.getmtime(cpath)) / 86400 if os.path.exists(cpath) else None
    if age is None or (live and age >= REFRESH_DAYS):
        out, bad = [], False
        for c in committee_links(year):
            page = get(f"/document/committee/{year}/{c['id']}")
            if not isinstance(page, str):
                bad = True
                continue
            c.update(parse_committee(page))
            out.append(c)
        if out and not bad:
            save(cpath, out)
            print(f"{year}: {len(out)} committees", flush=True)
        elif not os.path.exists(cpath):  # a failed refresh keeps the last copy
            INCOMPLETE.add(f"{year}:committees")


def begun(year):
    """Whether a session has convened (the first Monday of January of its first year)."""
    return date.today() >= date(year, 1, 1 + (0 - date(year, 1, 1).weekday()) % 7)


def finish():
    print(f"run: {round((time.time() - START) / 60)} min" + (f"; stopped at the time limit" if out_of_time() else "")
          + (f"; request failures {dict(FAILS)}" if FAILS else "; no request failures")
          + (f"; still to do: {' '.join(sorted(INCOMPLETE))}" if INCOMPLETE else ""), flush=True)
    marker = os.path.join(DATA, "incomplete")
    # A session not yet begun (no bills or members listed yet) is read when it's there but never holds Wisconsin back.
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
    for y in range(FIRST, CURRENT + 1, 2):
        session(y)
    sys.path.insert(0, os.path.normpath(os.path.join(DATA, "..", "..")))
    from states.wi import contacts
    for y in range(FIRST, CURRENT + 1, 2):
        try:
            contacts.main(y)
        except (SystemExit, OSError) as e:
            print(e)
    finish()


if __name__ == "__main__":
    main()
