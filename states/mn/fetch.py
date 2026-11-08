#!/usr/bin/env python3
"""Download Minnesota's bills from the Revisor of Statutes' Bill Status API v1 (documented at
https://www.revisor.mn.gov/bills/service.php), with House floor votes member by member from house.mn.gov, the Senate's
journals (PDFs, where its members' votes are), summaries from House Research and Senate Counsel, and the members and
committees of both houses.

robots.txt, read at the start of every run for each host and obeyed (`allowed()`; none sets a crawl delay):
- www.revisor.mn.gov disallows /alpha/, /beta/, /search/doc_result.php, /bills/status_results.php (plural) and
  /rules/status/result. The searches used here are /bills/status_result.php (singular), the address the API's
  documentation gives, with &format=xml. api.revisor.mn.gov, www.mnsenate.gov (www.senate.mn redirects there) and
  assets.mnsenate.gov have no robots.txt (404). www.house.mn.gov disallows only /Fiscal2/; www.lrl.mn.gov disallows
  its member pages, search and RSS, none of which are read.
One request at a time, a second apart (from the end of the last answer).

Minnesota's Legislatures run two years (the 94th is 2025-2026); a session is coded "0942025" (special session number,
Legislature, first year; "1942025" is the 2025 First Special Session). Each regular session goes in data/mn/<first
year>/, each special session in data/mn/<year>-s<n>/, from FIRST_LS on (the next Legislature once it has bills):
- list.json: {"HF10": {"uri", "title"}}, from the basic search (/bills/status_result.php?...&bill=1-500&format=xml),
  500 bill numbers a request (a search returns at most 500), House files and Senate files; bills only (Minnesota's
  constitutional amendments are bills), not resolutions.
- bills/<HF10>.json: each bill's status record (api.revisor.mn.gov/bills/v1/94/2025/0/HF/10/; the year is the one the
  bill was introduced in, so the list's address is used), turned from XML into JSON with empty elements left out:
  companion and substitution, description, law (chapter) number, text versions with dates, authors in order for each
  house (LEGISLATOR_KEY is the member's id on house.mn.gov for House members), and each house's actions (number,
  text, date, description, committee id and name, engrossment, journal page, and ROLL_CALL, a tally like "70-63"; no
  member votes). Committee ids are each house's own (House "94024", Senate "3127").
- house_votes.json (the House's list of bills with recorded floor votes, POST /Votes/GetVoteSummary, each with its
  latest vote date) and house_votes/<HF3023>.json (/Votes/Details?SessionKey=302&BillNumber=HF3023): every House roll
  call on the bill: the motion, amendment, tallies, journal page, date, and the members voting yes and no by last name
  as printed ("Anderson, P. E."). Read again when the bill's latest vote date changes.
- summaries/house/<hf0010>.txt: House Research's bill summaries (billsum.aspx?ls=94&filter=AllHF and AllSF list the
  PDFs, /hrd/bs/94/hf0010.pdf), as text (pdftotext); hrd.json maps each to its bill. Read again when the bill has a
  newer text version. summaries/senate/<id>.txt: Senate Counsel, Research and Fiscal Analysis's bill summaries (the
  list from www.mnsenate.gov/api/billsummary/year/bill/<year>, the PDFs from assets.mnsenate.gov/summ/...), once per
  summary id (a new version is a new id); senate_summaries.json lists them.
In the regular session's folder, for the whole Legislature:
- members_house.json (www.house.mn.gov/members/list: profile id, name, district, party, office, phone, email) and
  members_senate.json (www.mnsenate.gov/api/members: id, name, district, party, leader title, office, phone, email):
  the current Legislature only (neither site lists past members this way). Read again weekly.
- committees_house.json (/Committees/members/<id>: name, meeting time, members with roles "Chair", "Co-Chair",
  "Vice Chair" ...) and committees_senate.json (www.mnsenate.gov/committees/committee_bio.php?cmte_id=<id>&ls=94: the
  same, with "Ranking Minority Member"): the committees on the current committee lists and every committee the bills'
  actions name, weekly. A past Legislature's House committees once (their pages keep the name and meeting time but no
  longer list members); the Senate's pages show only the current Legislature (a past one's address shows today's
  committee), so a past Legislature has no committees_senate.json.
- journals/<2025051900>.txt.gz: the Senate Journal, each day's PDF (journal_list.php?display_ls_year=94) as text
  (pdftotext -layout), once. The Senate publishes its roll calls only there ("Those who voted in the affirmative
  were:"). Some days' PDFs are large (8 MB).
- state.json: what has been read (each bill's last read day, the change feed's last day, House vote dates, summaries).
data/mn/vetoes.html.gz: the Legislative Reference Library's list of every veto (www.lrl.mn.gov/vetoes/vetodetails),
weekly, to check totals against.

Changes: a live Legislature (the current one) is followed through the advanced search's action dates (search=advanced,
action[] empty, fromDate/toDate), which returns every bill with an action in those days, in each house's records; up
to a week a request, split when a search reaches 500, and by action kind for a single day that does. A bill with an
action on day D is read again once a day until D + LAG days (actions are entered when the journal is, often a few
days later), and every bill again after REREAD_DAYS (ROLLING a run). The list is read again weekly. A finished
Legislature (not live, everything read) is marked "finished" and not asked again.

PDF summaries and journals need pdftotext (poppler-utils); without it they are skipped, with a note.
At a second a request (about 1.2 seconds each with the answer), a first copy of two Legislatures (about 21,000 bills,
3,300 House Research and 1,900 Senate summaries, 500 House vote pages, 240 journal days) takes about 9 hours, so GitHub's runs build it up over several
runs, each resuming where the last stopped. data/mn/incomplete lists what was never downloaded (a session's list, its
bills, the current members and committees); votes, summaries and journals fill in on later runs and don't hold the
state off the site. A failed refresh keeps the last copy; a bill the server fails on in three runs is left out of
the count.
Usage: python3 states/mn/fetch.py [session]   (e.g. 2025 or 2025-s1; default: every session; one leaves the marker alone)
"""
import gzip, html, json, os, re, shutil, subprocess, sys, tempfile, time, urllib.error, urllib.parse, \
    urllib.request, urllib.robotparser
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import date, datetime, timedelta

REVISOR = "https://www.revisor.mn.gov"
HOUSE = "https://www.house.mn.gov"
SENATE = "https://www.mnsenate.gov"
ASSETS = "https://assets.mnsenate.gov"
LRL = "https://www.lrl.mn.gov"
DATA = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "mn"))
AGENT = "statebilltracker.org (a nonprofit bill tracker; contact via github.com/judithhubbard)"
TODAY = date.today()
ONLY = sys.argv[1] if len(sys.argv) > 1 else None
FIRST_LS = 93
CURRENT_LS = 94 + (TODAY.year - 2025) // 2
DELAY = 1.0
RANGE = 500  # bill numbers a list search asks for (a search returns at most 500)
CAP = 500
WEEK = 7
LAG = 4  # days after an action that its bill is read again (once a day)
OVERLAP = 7  # days the change feed looks back each run, one day a request
REREAD_DAYS = 28
ROLLING = 150
FAILED_RUNS = 3
MARKER = os.path.join(DATA, "incomplete")
PDFTOTEXT = shutil.which("pdftotext")
ORDINALS = {1: "First", 2: "Second", 3: "Third", 4: "Fourth", 5: "Fifth", 6: "Sixth", 7: "Seventh"}

# The run's own time limit (FETCH_MINUTES, set by the workflow): stop a few minutes early, with everything read so far
# saved and a summary printed, rather than be cut off silently mid-request.
START = time.time()
BUDGET = max(0.0, float(os.environ.get("FETCH_MINUTES") or 0) - 5) * 60
FAILS = Counter()  # why requests failed, for the summary
STATS = Counter()  # requests, and what was read
LAST = [0.0]  # when the last answer ended
ROBOTS = {}  # host -> RobotFileParser, or None when its robots.txt couldn't be read (the host is skipped)


class Refused(Exception):
    """The server turned us away (401/403/429): stop the run."""


def out_of_time():
    return BUDGET and time.time() - START > BUDGET


def fetch(url, data=None, headers=None, timeout=120):
    """One request, paced: (status, body bytes, content type). HTTP errors are raised."""
    wait = LAST[0] + DELAY - time.time()
    if wait > 0:
        time.sleep(wait)
    STATS["requests"] += 1
    if STATS["requests"] % 200 == 0:
        print(f"  {STATS['requests']} requests, {round((time.time() - START) / 60)} min"
              + (f"; failures {dict(FAILS)}" if FAILS else ""), flush=True)
    h = {"User-Agent": AGENT, "Accept-Encoding": "gzip", **(headers or {})}
    try:
        req = urllib.request.Request(url, data=data, headers=h, method="POST" if data is not None else "GET")
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = r.read()
            if r.headers.get("Content-Encoding") == "gzip":
                body = gzip.decompress(body)
            return r.status, body, r.headers.get("Content-Type") or ""
    finally:
        LAST[0] = time.time()


def allowed(url):
    """Whether robots.txt lets us read url (each host's robots.txt is read once a run)."""
    parts = urllib.parse.urlsplit(url)
    host = parts.netloc
    if host not in ROBOTS:
        rp = urllib.robotparser.RobotFileParser()
        try:
            status, body, _ = fetch(f"{parts.scheme}://{host}/robots.txt", timeout=60)
            rp.parse(body.decode("utf-8", "replace").splitlines())
        except urllib.error.HTTPError as e:
            if e.code in (404, 410):
                rp.allow_all = True
            else:
                print(f"robots.txt of {host}: HTTP {e.code}; not reading {host} this run", flush=True)
                rp = None
        except Exception as e:
            print(f"robots.txt of {host}: {type(e).__name__}; not reading {host} this run", flush=True)
            rp = None
        if rp is not None and not rp.allow_all:
            delay = rp.crawl_delay(AGENT) or rp.crawl_delay("*")
            if delay and float(delay) > DELAY:
                print(f"robots.txt of {host} asks for {delay} seconds between requests; this script waits {DELAY}: "
                      "not reading it", flush=True)
                rp = None
        ROBOTS[host] = rp
    rp = ROBOTS[host]
    if rp is None:
        return False
    path = parts.path + ("?" + parts.query if parts.query else "")
    return rp.allow_all or rp.can_fetch(AGENT, f"{parts.scheme}://{host}{path}")


def request(url, label, data=None, headers=None, timeout=120):
    """The body at url (bytes), or None after three tries; None at once for a 404, or when robots.txt disallows it.
    Raises Refused on 401/403/429."""
    if not allowed(url):
        FAILS["robots.txt"] += 1
        print(f"{label}: robots.txt disallows {url}; not read", flush=True)
        return None
    for attempt in range(3):
        if out_of_time():
            return None
        try:
            status, body, kind = fetch(url, data, headers, timeout)
            return body
        except urllib.error.HTTPError as e:
            FAILS[f"HTTP {e.code}"] += 1
            if e.code in (401, 403, 429):
                raise Refused(f"{label}: HTTP {e.code}")
            if e.code in (404, 410):
                return None
        except Exception as e:
            FAILS[type(e).__name__] += 1
        time.sleep(5 * (attempt + 1))
    print(f"{label}: failed three times", flush=True)
    return None


def text_of(body):
    return body.decode("utf-8", "replace") if body is not None else None


def save(obj, path):
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(obj, f, ensure_ascii=False)
    os.replace(tmp, path)


def load(path, default=None):
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def clean(s):
    """Text from a bit of HTML: tags dropped, entities decoded, spaces collapsed."""
    s = re.sub(r"<br\s*/?>", "\n", s or "", flags=re.I)
    s = html.unescape(re.sub(r"<[^>]+>", " ", s))
    return "\n".join(" ".join(line.split()) for line in s.split("\n") if line.strip())


def stale_after(iso, days):
    return not iso or iso[:10] <= (TODAY - timedelta(days=days)).isoformat()


def pdf_text(body, layout=False):
    """A PDF's text (pdftotext), or None."""
    if not PDFTOTEXT or not body or not body.startswith(b"%PDF"):
        return None
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "in.pdf")
        with open(path, "wb") as f:
            f.write(body)
        r = subprocess.run([PDFTOTEXT] + (["-layout"] if layout else []) + ["-enc", "UTF-8", path, "-"],
                           capture_output=True)
    return r.stdout.decode("utf-8", "replace") if r.returncode == 0 else None


# ---- sessions --------------------------------------------------------------------------------------------------

def sessions():
    """The sessions from FIRST_LS on, newest first: [{"code", "ls", "year", "special", "key", "first", "live"}]."""
    path = os.path.join(DATA, "sessions.json")
    page = text_of(request(f"{REVISOR}/bills/status_search.php?body=House", "session list"))
    m = re.search(r'<select[^>]*name="session"[^>]*>(.*?)</select>', page or "", re.S)
    codes = re.findall(r'<option value="(\d{7})"', m.group(1)) if m else []
    if codes:
        save(codes, path)
    else:
        print("session list: unreadable; kept the last copy", flush=True)
        codes = load(path, [])
    out = []
    for code in codes:
        special, ls, year = int(code[0]), int(code[1:3]), int(code[3:])
        if not FIRST_LS <= ls <= CURRENT_LS + 1:
            continue
        first = 2025 + 2 * (ls - 94)
        out.append({"code": code, "ls": ls, "year": year, "special": special, "first": first,
                    "key": f"{year}-s{special}" if special else str(year), "live": ls >= CURRENT_LS})
    return sorted(out, key=lambda s: (s["ls"], s["year"], s["special"]), reverse=True)


def session_end(s):
    return date(s["first"] + 1, 12, 31)


def folder_of(s):
    return os.path.join(DATA, s["key"])


def regular_folder(ls):
    return os.path.join(DATA, str(2025 + 2 * (ls - 94)))


# ---- the bill list and the change feed -----------------------------------------------------------------------------

def results(body):
    """[(key, uri, title)] from a search answer (HF and SF only), or None when it isn't one."""
    t = text_of(body)
    if not t or "<SEARCH_RESULTS" not in t:
        return None
    out = []
    for block in re.findall(r"<BILL_RESULT>(.*?)</BILL_RESULT>", t, re.S):
        f = {tag: html.unescape(m.group(1)).strip() for tag in ("FILE_TYPE", "FILE_NUMBER", "STATUS_XML_URI", "DESCRIPTION")
             for m in [re.search(rf"<{tag}>(.*?)</{tag}>", block, re.S)] if m}
        if f.get("FILE_TYPE") in ("HF", "SF") and (f.get("FILE_NUMBER") or "").isdigit():
            out.append((f"{f['FILE_TYPE']}{int(f['FILE_NUMBER'])}", f.get("STATUS_XML_URI") or "", f.get("DESCRIPTION") or ""))
    return out


def search_range(s, ftype, lo, hi):
    body = "House" if ftype == "HF" else "Senate"
    q = urllib.parse.urlencode({"body": body, "search": "basic", "session": s["code"], "location": body,
                                "bill": f"{lo}-{hi}", "bill_type": "bill", "submit_bill": "GO", "format": "xml"})
    return results(request(f"{REVISOR}/bills/status_result.php?{q}", f"{s['key']} {ftype} {lo}-{hi}", timeout=300))


def add(lst, found):
    for k, uri, title in found:
        lst[k] = {"uri": uri, "title": title}


def read_list(s, folder, state, lst):
    """Every bill's number, address and title, RANGE numbers a request, resuming where the last run stopped. Read
    once, and again weekly while the session is live. True when the list is whole."""
    if state.get("listed") and not (s["live"] and stale_after(state["listed"], WEEK)) and "pages" not in state:
        return True
    if "feed" not in state:
        state["feed"] = (TODAY - timedelta(days=2)).isoformat()  # the feed covers changes from here on
    pages = state.setdefault("pages", {})
    for ftype in ("HF", "SF"):
        lo = pages.get(ftype, 1)
        while lo > 0:
            if out_of_time():
                return False
            found = search_range(s, ftype, lo, lo + RANGE - 1)
            if found is None:
                print(f"{s['key']} {ftype} {lo}-{lo + RANGE - 1}: unreadable", flush=True)
                return False
            add(lst, found)
            highest = max([int(k[2:]) for k in lst if k.startswith(ftype)] or [0])
            lo = lo + RANGE if found or highest >= lo else 0
            pages[ftype] = lo
            save(lst, os.path.join(folder, "list.json"))
            save(state, os.path.join(folder, "state.json"))
    state["listed"] = TODAY.isoformat()
    state.pop("pages", None)
    print(f"{s['key']}: {sum(k.startswith('HF') for k in lst)} House files, {sum(k.startswith('SF') for k in lst)} "
          "Senate files listed", flush=True)
    return True


ACTION_IDS = {}


def action_ids(s, body):
    """The action kinds the advanced search offers for this session and house (for splitting a capped day)."""
    k = (s["code"], body)
    if k not in ACTION_IDS:
        q = urllib.parse.urlencode({"search": "advanced", "body": body, "session": s["code"]})
        page = text_of(request(f"{REVISOR}/bills/status_search.php?{q}", f"{s['key']} {body} action kinds")) or ""
        m = re.search(r'<select[^>]*name="action\[\]"[^>]*>(.*?)</select>', page, re.S)
        ACTION_IDS[k] = [a for a in re.findall(r'<option value="(\d+)"', m.group(1))] if m else None
    return ACTION_IDS[k]


def window(s, body, d1, d2, action=""):
    """[(key, uri, title)] of the bills with an action from d1 to d2 in this house's records, or None."""
    q = urllib.parse.urlencode({"body": body, "search": "advanced", "session": s["code"], "action[]": action,
                                "fromDate": d1.strftime("%m/%d/%Y"), "toDate": d2.strftime("%m/%d/%Y"),
                                "submit_advanced": "GO", "format": "xml"})
    return results(request(f"{REVISOR}/bills/status_result.php?{q}", f"{s['key']} {body} actions {d1}..{d2}", timeout=300))


def changed(s, body, d1, d2):
    """The bills with actions from d1 to d2 (splitting a search that reaches CAP), or None."""
    found = window(s, body, d1, d2)
    if found is None or len(found) < CAP:
        return found
    if d1 < d2:
        mid = d1 + (d2 - d1) // 2
        a, b = changed(s, body, d1, mid), changed(s, body, mid + timedelta(days=1), d2)
        return None if a is None or b is None else a + b
    ids = action_ids(s, body)
    if not ids:
        return None
    out = []
    for a in ids:
        part = window(s, body, d1, d2, a)
        if part is None:
            return None
        if len(part) >= CAP:
            print(f"{s['key']} {body} {d1} action {a}: {len(part)} bills, the search's limit", flush=True)
        out += part
    return out


def feed(s, folder, state, lst):
    """Mark the bills with recent actions to be read again (see the docstring). The feed's day advances only over
    days read in both houses."""
    if "feed" not in state:
        return True
    end = min(TODAY, session_end(s))
    last = date.fromisoformat(state["feed"])
    if last >= end and not s["live"]:
        return True
    d = min(last + timedelta(days=1), end - timedelta(days=OVERLAP))
    d = max(d, date(s["year"], 1, 1))
    stale = set(state.get("stale") or [])
    read = state.setdefault("read", {})
    while d <= end:
        if out_of_time():
            break
        recent = d > end - timedelta(days=OVERLAP)
        d2 = d if recent else min(d + timedelta(days=WEEK - 1), end - timedelta(days=OVERLAP))
        hits = []
        for body in ("House", "Senate"):
            part = changed(s, body, d, d2)
            if part is None:
                hits = None
                break
            hits += part
        if hits is None:
            print(f"{s['key']}: change feed unreadable from {d}; asked again next run", flush=True)
            break
        for k, uri, title in hits:
            if k not in lst:
                lst[k] = {"uri": uri, "title": title}
            r = read.get(k)
            if r and r < TODAY.isoformat() and r <= (d2 + timedelta(days=LAG)).isoformat():
                stale.add(k)
        if d2.isoformat() > state["feed"]:
            state["feed"] = d2.isoformat()
        d = d2 + timedelta(days=1)
    state["stale"] = sorted(stale)
    save(lst, os.path.join(folder, "list.json"))
    save(state, os.path.join(folder, "state.json"))
    return state["feed"] >= end.isoformat()


# ---- bills -----------------------------------------------------------------------------------------------------

LISTS = {"AUTHOR", "ACTION", "DOCUMENT"}


def node(e):
    """An XML element as JSON: text for a leaf, a list of its children when they're authors, actions or documents,
    else an object; empty elements are left out."""
    kids = list(e)
    if not kids:
        return (e.text or "").strip()
    if all(k.tag in LISTS for k in kids):
        return [node(k) for k in kids]
    out = {}
    for k in kids:
        v = node(k)
        if v not in ("", [], {}):
            out[k.tag] = v
    return out


def read_bill(s, folder, k, uri, state):
    url = uri if uri.startswith("http") else "https://" + uri.lstrip("/")
    body = request(url, f"{s['key']} {k}")
    bill = None
    if body:
        try:
            bill = node(ET.fromstring(body))
        except ET.ParseError:
            FAILS["unreadable XML"] += 1
    if not isinstance(bill, dict) or not bill.get("FILE_TYPE"):
        state.setdefault("failed", {})[k] = state.get("failed", {}).get(k, 0) + 1
        return False
    save(bill, os.path.join(folder, "bills", f"{k}.json"))
    state.setdefault("read", {})[k] = TODAY.isoformat()
    state.get("failed", {}).pop(k, None)
    STATS["bills"] += 1
    return True


def never_read(folder, state, lst):
    failed = state.get("failed") or {}
    return [k for k in lst if not os.path.exists(os.path.join(folder, "bills", f"{k}.json"))
            and failed.get(k, 0) < FAILED_RUNS]


def order(keys):
    return sorted(keys, key=lambda k: (k[:2], int(k[2:])))


def read_bills(found, ctx):
    """Bills to read: those marked by the feed first, then those never read (newest session first), then a live
    session's bills read longest ago. A bill that fails is tried once a run."""
    tried = set()
    for phase in ("stale", "new", "rolling"):
        budget = ROLLING
        for s in found:
            folder, state, lst = ctx[s["key"]]
            os.makedirs(os.path.join(folder, "bills"), exist_ok=True)
            if phase == "stale":
                keys = [k for k in state.get("stale") or [] if k in lst]
            elif phase == "new":
                keys = order(never_read(folder, state, lst))
            else:
                if not s["live"]:
                    continue
                read = state.get("read") or {}
                keys = sorted((k for k in lst if stale_after(read.get(k), REREAD_DAYS) and k in read),
                              key=lambda k: read[k])[:budget]
                budget -= len(keys)
            n = 0
            for k in keys:
                if out_of_time():
                    save(state, os.path.join(folder, "state.json"))
                    return
                if (s["key"], k) in tried:
                    continue
                tried.add((s["key"], k))
                if read_bill(s, folder, k, lst[k]["uri"], state) and phase == "stale":
                    state["stale"] = [x for x in state.get("stale") or [] if x != k]
                n += 1
                if n % 50 == 0:
                    save(state, os.path.join(folder, "state.json"))
            save(state, os.path.join(folder, "state.json"))
            if keys:
                print(f"{s['key']} bills ({phase}): {n} of {len(keys)} read", flush=True)


# ---- House floor votes -----------------------------------------------------------------------------------------

HOUSE_KEYS = {}


def house_key(s):
    """The House vote pages' session key ("2025 - 2026 Regular Session" is 302), from /Votes/."""
    if not HOUSE_KEYS:
        page = text_of(request(f"{HOUSE}/Votes/", "House vote sessions")) or ""
        for key, label in re.findall(r'href="/Votes/Summary/(\d+)"[^>]*>\s*([^<]+?)\s*<', page):
            HOUSE_KEYS[" ".join(label.split())] = int(key)
        if not HOUSE_KEYS:
            HOUSE_KEYS["?"] = None
    for label, key in HOUSE_KEYS.items():
        if not s["special"] and label == f"{s['first']} - {s['first'] + 1} Regular Session":
            return key
        if s["special"] and label.startswith(str(s["year"])) and (
                f"{ORDINALS.get(s['special'], '?')} Special Session" in label
                or (s["special"] == 1 and label == f"{s['year']} Special Session")):
            return key
    return None


def parse_votes(page):
    """Each roll call on a /Votes/Details page."""
    out = []
    for panel in page.split('class="collapsible-panel"')[1:]:
        row = re.search(r"<tbody>(.*?)</tbody>", panel, re.S)
        cells = [clean(c) for c in re.findall(r"<td[^>]*>(.*?)</td>", row.group(1), re.S)] if row else []
        if len(cells) < 7:
            continue
        v = {"bill": cells[0], "description": cells[1].split("\n"), "amendment": cells[2], "yeas": cells[3],
             "nays": cells[4], "journal_page": cells[5], "date": cells[6]}
        content = panel.split('class="panel-content"', 1)[-1]
        yes = re.search(r"voted in the affirmative were:(.*?)(?:voted in the negative were:|$)", content, re.S)
        no = re.search(r"voted in the negative were:(.*)", content, re.S)
        v["yes"] = [n for n in (clean(x) for x in re.findall(r"<td>([^<]*)", yes.group(1))) if n] if yes else []
        v["no"] = [n for n in (clean(x) for x in re.findall(r"<td>([^<]*)", no.group(1))) if n] if no else []
        if (v["yeas"].isdigit() and int(v["yeas"]) != len(v["yes"])) or (v["nays"].isdigit() and int(v["nays"]) != len(v["no"])):
            STATS["House roll calls whose names don't match their tally"] += 1
        out.append(v)
    return out


def house_votes(s, folder, state):
    """True when every bill on the House's list of recorded votes has been read."""
    done = state.get("hv_done")
    if done and not s["live"]:
        return True
    key = house_key(s)
    if key is None:
        print(f"{s['key']}: no House vote list for this session", flush=True)
        return True
    raw = request(f"{HOUSE}/Votes/GetVoteSummary", f"{s['key']} House vote list",
                  data=json.dumps({"SessionKey": key, "sortOption": "Date"}).encode(),
                  headers={"Content-Type": "application/json; charset=utf-8", "Accept": "application/json"})
    try:
        summary = json.loads(raw)
    except (TypeError, ValueError):
        summary = None
    path = os.path.join(folder, "house_votes.json")
    if not isinstance(summary, list):
        print(f"{s['key']}: House vote list unreadable; kept the last copy", flush=True)
        summary = load(path, [])
        whole = False
    else:
        save(summary, path)
        whole = True
    latest = {}
    for v in summary:
        n = re.sub(r"[^A-Z0-9]", "", (v.get("Number") or "").upper())
        if n:
            latest[n] = max(latest.get(n, ""), v.get("Date") or "")
    hv = state.setdefault("hv", {})
    os.makedirs(os.path.join(folder, "house_votes"), exist_ok=True)
    n = 0
    for num, when in sorted(latest.items()):
        k = re.sub(r"^([HS]F)0*", r"\1", num)
        out = os.path.join(folder, "house_votes", f"{k}.json")
        if hv.get(num) == when and os.path.exists(out):
            continue
        if out_of_time():
            whole = False
            break
        q = urllib.parse.urlencode({"SessionKey": key, "BillNumber": num})
        page = text_of(request(f"{HOUSE}/Votes/Details?{q}", f"{s['key']} {num} House votes"))
        votes = parse_votes(page) if page else None
        if not votes:
            whole = False
            continue
        save(votes, out)
        hv[num] = when
        n += 1
        STATS["House vote pages"] += 1
    state["hv_done"] = whole
    save(state, os.path.join(folder, "state.json"))
    print(f"{s['key']}: House votes on {len(latest)} bills; {n} read this run", flush=True)
    return whole


# ---- members and committees ------------------------------------------------------------------------------------

def house_members(folder, state):
    path = os.path.join(folder, "members_house.json")
    if os.path.exists(path) and not stale_after(state.get("members_house"), WEEK):
        return
    page = text_of(request(f"{HOUSE}/members/list", "House members")) or ""
    part = page.split('id="Alpha"', 1)[-1].split('id="District"', 1)[0]
    out = []
    for block in part.split('<div class="media my-3">')[1:]:
        m = re.search(r'/members/profile/(\d+)"><b>([^<]+?)\s*\(([^,]+),\s*([^)]+)\)</b>', block)
        if not m:
            continue
        lines = clean(block.split("</h5>", 1)[-1]).split("\n")
        email = re.search(r"mailto:([^\"]+)", block)
        phone = next((l for l in lines if re.fullmatch(r"\d{3}-\d{3}-\d{4}", l)), "")
        office = [l for l in lines if l != phone and not l.startswith("E-mail") and "@" not in l and "<" not in l]
        out.append({"id": int(m.group(1)), "name": html.unescape(m.group(2)), "district": m.group(3).strip(),
                    "party": m.group(4).strip(), "office": office, "phone": phone,
                    "email": email.group(1).strip() if email else ""})
    if len(out) < 120:
        print(f"House members: only {len(out)} read; kept the last copy", flush=True)
        return
    save(out, path)
    state["members_house"] = TODAY.isoformat()
    print(f"House members: {len(out)}", flush=True)


def senate_members(folder, state):
    path = os.path.join(folder, "members_senate.json")
    if os.path.exists(path) and not stale_after(state.get("members_senate"), WEEK):
        return
    try:
        d = json.loads(request(f"{SENATE}/api/members", "Senate members") or b"")
    except ValueError:
        d = None
    rows = d.get("members") if isinstance(d, dict) else None
    if not isinstance(rows, list) or len(rows) < 60:
        print("Senate members: unreadable; kept the last copy", flush=True)
        return
    save(rows, path)
    state["members_senate"] = TODAY.isoformat()
    print(f"Senate members: {len(rows)}", flush=True)


def committee_ids(ls):
    """The committee ids the bills' actions name in each house, across the Legislature's sessions."""
    ids = {"HOUSE": set(), "SENATE": set()}
    for name in os.listdir(DATA):
        s_folder = os.path.join(DATA, name, "bills")
        if not (name == str(2025 + 2 * (ls - 94)) or name.startswith(f"{2025 + 2 * (ls - 94)}-s")
                or name.startswith(f"{2026 + 2 * (ls - 94)}-s")) or not os.path.isdir(s_folder):
            continue
        for f in os.listdir(s_folder):
            b = load(os.path.join(s_folder, f), {})
            for house in ids:
                for a in ((b.get("ACTIONS") or {}).get(house) or []) if isinstance(b, dict) else []:
                    if isinstance(a, dict) and (a.get("COMMITTEE_ID") or "").isdigit():
                        ids[house].add(a["COMMITTEE_ID"])
    return ids


def house_committee(cid):
    page = text_of(request(f"{HOUSE}/Committees/members/{cid}", f"House committee {cid}"))
    if not page or "CommitteeMembers" not in page:
        return None
    name = re.search(r'<h2><a href="/Committees/home/\d+">([^<]+)</a></h2>', page, re.I)
    meets = re.search(r"<b>Meets: </b>\s*([^<]*)", page)
    members = []
    for block in page.split('<div class="media pl-2 py-4">')[1:]:
        m = re.search(r'/members/profile/(\d+)">([^<]+)</a></b>\s*\(([^)]*)\)\s*District:\s*([0-9A-Z]+)', block)
        if not m:
            continue
        role = re.search(r"<u>([^<]+)</u>", block)
        members.append({"id": int(m.group(1)), "name": clean(m.group(2)), "party": m.group(3).strip(),
                        "district": m.group(4), "role": clean(role.group(1)) if role else "Member"})
    return {"id": cid, "name": clean(name.group(1)) if name else "", "meets": clean(meets.group(1)) if meets else "",
            "members": members}


def senate_committee(cid, ls):
    page = text_of(request(f"{SENATE}/committees/committee_bio.php?cmte_id={cid}&ls={ls}", f"Senate committee {cid}"))
    first = 2025 + 2 * (ls - 94)
    if not page or "member_bio.php" not in page or f"{first} - {first + 1} Biennium" not in page:
        return None  # (a past Legislature's address shows the current committee)
    name = re.search(r"<h1[^>]*>(.*?)</h1>", page, re.S)
    meets = re.search(r"Regular Meeting Schedule:\s*</span>(.*?)</p>", page, re.S)
    members = []
    for block in re.split(r"<div class='media my-3'>", page)[1:]:
        m = re.search(r"member_bio\.php\?member_id=(\d+)'><b>([^<]+)</b>", block)
        if not m:
            continue
        role = re.search(r"<b>([^<]+)</b>\s*<h5", block)
        parts = [p.strip() for p in html.unescape(m.group(2)).split(",")]
        members.append({"id": int(m.group(1)), "name": ", ".join(parts[:-2]) if len(parts) > 2 else parts[0],
                        "district": parts[-2] if len(parts) > 2 else "", "party": parts[-1] if len(parts) > 2 else "",
                        "role": clean(role.group(1)) if role else "Member"})
    return {"id": cid, "name": clean(name.group(1)) if name else "", "meets": clean(meets.group(1)) if meets else "",
            "members": members}


def committees(ls, folder, state, live):
    """Both houses' committees: those on the current lists and those the bills name. True when none is missing."""
    whole = True
    named = committee_ids(ls)
    failed = state.setdefault("committees_failed", {})
    for house, fname in (("HOUSE", "committees_house.json"), ("SENATE", "committees_senate.json")):
        if house == "SENATE" and not live:
            continue  # the Senate's pages show only the current Legislature's committees
        path = os.path.join(folder, fname)
        have = load(path, {})
        ids = named[house]
        if live:
            if house == "HOUSE":
                page = text_of(request(f"{HOUSE}/committees", "House committee list")) or ""
                ids |= {c for c in re.findall(r'/Committees/Home/(\d+)"', page, re.I) if c.startswith(str(ls))}
            else:
                page = text_of(request(f"{SENATE}/committees/", "Senate committee list")) or ""
                ids |= {c for c, l in re.findall(r"committee_bio\.php\?cmte_id=(\d+)&(?:amp;)?ls=(\d+)", page) if l == str(ls)}
        read = state.setdefault(f"committees_{house.lower()}", {})
        n = 0
        for cid in sorted(ids):
            if cid in have and not (live and stale_after(read.get(cid), WEEK)):
                continue
            if cid not in have and failed.get(cid, 0) >= FAILED_RUNS:
                continue  # an id the site doesn't know (asked in three runs)
            if out_of_time():
                whole = False
                break
            c = house_committee(cid) if house == "HOUSE" else senate_committee(cid, ls)
            if c is None:
                whole = whole and cid in have
                failed[cid] = failed.get(cid, 0) + 1
                continue
            have[cid] = c
            read[cid] = TODAY.isoformat()
            n += 1
        save(have, path)
        if n:
            print(f"Legislature {ls}: {house.title()} committees: {len(have)} ({n} read)", flush=True)
    save(state, os.path.join(folder, "state.json"))
    return whole


# ---- summaries and journals ------------------------------------------------------------------------------------

def hrd_summaries(s, folder, state):
    """House Research's bill summaries (PDF -> text). True when every listed one has been read."""
    if not PDFTOTEXT:
        return True
    index_path = os.path.join(folder, "hrd.json")
    index = load(index_path, {})
    if not state.get("hrd_listed") or (s["live"] and stale_after(state["hrd_listed"], WEEK)):
        ls = str(s["ls"]) if not s["special"] else f"{s['ls']}-{s['year']}-{s['special']}"
        fresh, whole = {}, True
        for which in ("AllHF", "AllSF"):
            page = text_of(request(f"{HOUSE}/hrd/billsum.aspx?ls={ls}&filter={which}", f"{s['key']} House Research {which}"))
            if page is None:
                whole = False
                continue
            for href in re.findall(r'href="([^"]*/hrd/bs/[^"]+\.pdf)"', page, re.I):
                name = os.path.splitext(href.rsplit("/", 1)[-1])[0].lower()
                m = re.match(r"(hf|sf)0*(\d+)", name)
                if m:
                    fresh[name] = {"bill": f"{m.group(1).upper()}{m.group(2)}", "url": urllib.parse.urljoin(HOUSE, href)}
        if whole:
            index = fresh
            save(index, index_path)
            state["hrd_listed"] = TODAY.isoformat()
    os.makedirs(os.path.join(folder, "summaries", "house"), exist_ok=True)
    read = state.setdefault("hrd_read", {})
    whole, n = True, 0
    for name, e in sorted(index.items()):
        out = os.path.join(folder, "summaries", "house", f"{name}.txt")
        newest = ""
        if os.path.exists(out) and s["live"]:
            bill = load(os.path.join(folder, "bills", f"{e['bill']}.json"), {})
            dates = [d.get("DATE_INSERT", "") for d in (bill.get("TEXT_VERSION_LIST") or []) if isinstance(d, dict)]
            newest = max(dates or [""])[:10]
        if os.path.exists(out) and not (newest and newest > read.get(name, "")):
            continue
        if out_of_time():
            whole = False
            break
        text = pdf_text(request(e["url"], f"{s['key']} House Research {name}"))
        if text is None:
            whole = whole and os.path.exists(out)
            continue
        with open(out, "w") as f:
            f.write(text)
        read[name] = TODAY.isoformat()
        n += 1
        STATS["House Research summaries"] += 1
        if n % 50 == 0:
            save(state, os.path.join(folder, "state.json"))
    save(state, os.path.join(folder, "state.json"))
    if n:
        print(f"{s['key']}: House Research summaries: {len(index)} listed, {n} read", flush=True)
    return whole


SENATE_SUMMARIES = {}


def senate_summaries(s, folder, state):
    """Senate Counsel, Research and Fiscal Analysis's bill summaries (PDF -> text), once per summary id."""
    if not PDFTOTEXT:
        return True
    index_path = os.path.join(folder, "senate_summaries.json")
    index = load(index_path, {})
    if not state.get("senate_listed") or (s["live"] and stale_after(state["senate_listed"], WEEK)):
        whole = True
        for year in (s["first"], s["first"] + 1):
            if year not in SENATE_SUMMARIES:
                try:
                    d = json.loads(request(f"{SENATE}/api/billsummary/year/bill/{year}", f"Senate summaries {year}") or b"")
                    SENATE_SUMMARIES[year] = d["summaries"] if isinstance(d.get("summaries"), list) else None
                except (ValueError, KeyError, AttributeError, TypeError):
                    SENATE_SUMMARIES[year] = None
            if SENATE_SUMMARIES[year] is None:
                whole = False
        if whole:
            index = {}
            for year in (s["first"], s["first"] + 1):
                for e in SENATE_SUMMARIES[year]:
                    if e.get("make_public") != "Y" or e.get("ls_year") != s["ls"] or (e.get("ss_number") or 0) != s["special"]:
                        continue
                    if s["special"] and e.get("ss_year") != s["year"]:
                        continue
                    index[str(e["id"])] = e
            save(index, index_path)
            state["senate_listed"] = TODAY.isoformat()
    os.makedirs(os.path.join(folder, "summaries", "senate"), exist_ok=True)
    whole, n = True, 0
    for sid, e in sorted(index.items()):
        out = os.path.join(folder, "summaries", "senate", f"{sid}.txt")
        if os.path.exists(out):
            continue
        if out_of_time():
            whole = False
            break
        bill = (e.get("bill_type") or "").replace(".", "").upper() + str(e.get("bill_number") or "")
        if e.get("is_act") == "Y":
            path = f"chapter/{e['ss_year']}/{e['ss_number']}"
        else:
            path = f"bill/{e['ss_year']}/{e['ss_number']}/{bill}"
        url = f"{ASSETS}/summ/{path}/{urllib.parse.quote(e.get('upload_name') or '')}"
        text = pdf_text(request(url, f"{s['key']} Senate summary {sid} ({bill})"))
        if text is None:
            whole = False
            continue
        with open(out, "w") as f:
            f.write(text)
        n += 1
        STATS["Senate summaries"] += 1
    if n:
        print(f"{s['key']}: Senate summaries: {len(index)} listed, {n} read", flush=True)
    return whole


def journals(ls, folder, state, live):
    """The Senate Journal's days as text, once each. True when every listed day has been read."""
    if not PDFTOTEXT:
        return True
    index_path = os.path.join(folder, "journals.json")
    index = load(index_path, [])
    if not state.get("journals_listed") or live:
        page = text_of(request(f"{SENATE}/journals/journal_list.php?display_ls_year={ls}", f"Legislature {ls} Senate journals"))
        if page:
            found = sorted(set(re.findall(r"""href=['"](/journals/+[^'"]+\.pdf)""", page)))
            first = 2025 + 2 * (ls - 94)
            found = [p for p in found if f"/{first}-{first + 1}/" in p]
            if found:
                index = found
                save(index, index_path)
                state["journals_listed"] = TODAY.isoformat()
    os.makedirs(os.path.join(folder, "journals"), exist_ok=True)
    whole, n = True, 0
    for p in index:
        name = os.path.splitext(p.rsplit("/", 1)[-1])[0]
        out = os.path.join(folder, "journals", f"{name}.txt.gz")
        if os.path.exists(out):
            continue
        if out_of_time():
            whole = False
            break
        text = pdf_text(request(SENATE + re.sub(r"/+", "/", p), f"Legislature {ls} Senate journal {name}", timeout=300), layout=True)
        if text is None:
            whole = False
            continue
        with gzip.open(out, "wt") as f:
            f.write(text)
        n += 1
        STATS["Senate journal days"] += 1
    save(state, os.path.join(folder, "state.json"))
    if n or index:
        print(f"Legislature {ls}: Senate journal days: {len(index)} listed, {n} read", flush=True)
    return whole and bool(index)


def vetoes():
    path = os.path.join(DATA, "vetoes.html.gz")
    if os.path.exists(path) and not stale_after(time.strftime("%Y-%m-%d", time.localtime(os.path.getmtime(path))), WEEK):
        return
    body = request(f"{LRL}/vetoes/vetodetails.aspx", "vetoes")
    if body and b"veto" in body.lower():
        with gzip.open(path + ".tmp", "wb") as f:
            f.write(body)
        os.replace(path + ".tmp", path)
        print("vetoes: read", flush=True)


# ---- the run ---------------------------------------------------------------------------------------------------

def missing(s):
    """What of this session was never downloaded (a failed re-read with a last copy doesn't count; votes, summaries
    and journals fill in on later runs)."""
    folder = folder_of(s)
    state = load(os.path.join(folder, "state.json"), {})
    if state.get("finished"):
        return []
    out = []
    lst = load(os.path.join(folder, "list.json"), {})
    if not state.get("listed"):
        out.append(f"{s['key']}:list")
    if never_read(folder, state, lst):
        out.append(f"{s['key']}:bills")
    if s["ls"] == CURRENT_LS and not s["special"]:
        for name in ("members_house", "members_senate", "committees_house", "committees_senate"):
            if not os.path.exists(os.path.join(folder, f"{name}.json")):
                out.append(f"{s['key']}:{name}")
    return out


def has_bills(s):
    """Whether a session not yet downloaded has numbered bills."""
    for ftype in ("HF", "SF"):
        found = search_range(s, ftype, 1, RANGE)
        if found is None or found:
            return True  # (unreadable: try)
    return False


def main():
    os.makedirs(DATA, exist_ok=True)
    first_copy = not any(re.fullmatch(r"\d{4}(-s\d)?", n) for n in os.listdir(DATA))
    if not ONLY and first_copy:
        with open(MARKER, "w") as f:
            f.write("running\n")
    if not PDFTOTEXT:
        print("pdftotext isn't installed (poppler-utils): summaries and Senate journals are skipped this run", flush=True)
    refused = False
    seen, found, ctx, done = [], [], {}, {}
    try:
        seen = [s for s in sessions() if not ONLY or s["key"] == ONLY]
        # Lists and the change feed first, newest session first.
        for s in seen:
            folder = folder_of(s)
            state = load(os.path.join(folder, "state.json"), {})
            if state.get("finished"):
                print(f"{s['key']}: finished and fully read; nothing to do", flush=True)
                continue
            if out_of_time():
                break
            if not os.path.isdir(folder) and not has_bills(s):
                print(f"{s['key']}: no bills numbered yet", flush=True)
                continue
            os.makedirs(folder, exist_ok=True)
            lst = load(os.path.join(folder, "list.json"), {})
            listed = read_list(s, folder, state, lst)
            fed = feed(s, folder, state, lst) if listed else False
            save(state, os.path.join(folder, "state.json"))
            ctx[s["key"]] = (folder, state, lst)
            done[s["key"]] = listed and fed
            found.append(s)
        # The current Legislature's members and committees, and the House's votes (small), before the bills.
        for ls in sorted({s["ls"] for s in found if not s["special"]}, reverse=True):
            folder = regular_folder(ls)
            if os.path.basename(folder) not in ctx:
                continue
            state = ctx[os.path.basename(folder)][1]
            if ls == CURRENT_LS:
                house_members(folder, state)
                senate_members(folder, state)
                committees(ls, folder, state, True)
            save(state, os.path.join(folder, "state.json"))
        for s in found:
            folder, state, lst = ctx[s["key"]]
            done[s["key"]] &= house_votes(s, folder, state)
        read_bills(found, ctx)
        for s in found:
            folder, state, lst = ctx[s["key"]]
            if s["special"]:
                continue
            done[s["key"]] &= committees(s["ls"], folder, state, s["ls"] == CURRENT_LS)
        for s in found:
            folder, state, lst = ctx[s["key"]]
            done[s["key"]] &= hrd_summaries(s, folder, state)
            done[s["key"]] &= senate_summaries(s, folder, state)
        for s in found:
            folder, state, lst = ctx[s["key"]]
            if not s["special"]:
                done[s["key"]] &= journals(s["ls"], folder, state, s["live"])
        vetoes()
        for s in found:
            folder, state, lst = ctx[s["key"]]
            if done[s["key"]] and not s["live"] and PDFTOTEXT and not missing(s) and not state.get("stale") \
                    and not out_of_time():
                state["finished"] = True
                print(f"{s['key']}: finished", flush=True)
            save(state, os.path.join(folder, "state.json"))
    except Refused as e:
        print(f"Stopped: the server refused a request ({e})", flush=True)
        refused = True
        for folder, state, lst in ctx.values():
            save(state, os.path.join(folder, "state.json"))
            save(lst, os.path.join(folder, "list.json"))
    gaps = [g for s in seen for g in missing(s) if os.path.isdir(folder_of(s))]
    if not seen:
        gaps.append("sessions")
    counts = {k: v for k, v in STATS.items() if k != "requests"}
    print(f"run: {STATS['requests']} requests, {round((time.time() - START) / 60)} min"
          + (f"; read {counts}" if counts else "")
          + ("; stopped at the time limit" if out_of_time() else "")
          + ("; refused" if refused else "")
          + (f"; request failures {dict(FAILS)}" if FAILS else "; no request failures")
          + (f"; still missing: {' '.join(gaps)}" if gaps else "; nothing missing"), flush=True)
    if ONLY:
        return
    # Left while data that was never downloaded is missing, so a partial first copy isn't published.
    if gaps:
        with open(MARKER, "w") as f:
            f.write(" ".join(gaps) + "\n")
    elif os.path.exists(MARKER):
        os.remove(MARKER)


if __name__ == "__main__":
    main()
