#!/usr/bin/env python3
"""Download Missouri's bills from its two houses, which publish separately:
- The House's XML exports (https://documents.house.mo.gov/, instructions at its home page): a bill list for the current
  session with a link to one XML file per bill and when each was last written ("LastTimeRun"), a member list with one
  XML file per representative, the House and joint committees, and the House's actions on Senate bills. Past sessions
  are one zip each (/xml/251.zip, listed on /XMLPastExports.html), "no longer updated". Its robots.txt (checked
  2026-11-08) sets Crawl-delay: 20 for all user agents and bars nothing; its instructions ask scripts not to poll the
  exports more often than every half hour and to pull only files updated since the last run. So: one request at a time
  to that host, 20 seconds after the last answer, and a file is read again only when the list's LastTimeRun for it
  changes. (house.mo.gov, the House's own pages, sets Crawl-delay: 120 and bars every address with "?" in it: not read.)
- The Senate's website (https://www.senate.mo.gov/, server-built HTML; no export). Its robots.txt (checked 2026-11-08)
  bars only /Trade/ and /DistrictWebApps/, none of which are read, and sets no crawl delay: one request at a time, a
  second after the last answer.
The two hosts are read side by side (one thread each), each at its own pace.

Missouri's General Assembly meets once a year, from early January to mid-May; the governor acts by mid-July and the
veto session is in September (bills don't carry over). Extraordinary sessions are left out. For each year from two
years back through this one (and next year's prefiled bills from December 1), into data/mo/<year>/:
- house/: the House's exports for the regular session (session code <yy>1: 261 for 2026). BillList.xml, MemberList.xml,
  CommitteeList.xml (each House and joint committee with its members, chair, vice-chair and ranking minority member),
  SenateActList.xml (Senate bills' actions in the House, with sponsor and handler); bills/<HB2>.xml, one per House
  bill (HB) and joint resolution (HJR: constitutional amendments, which go to the voters, not the governor; concurrent
  and simple resolutions are left out). A bill's XML has the current version ("CCS SS SCS HCS HB 2"), short and long
  titles, sponsor and co-sponsors (FullName, District), every action in both houses (Description such as "Third Read
  and Passed (H)", "Truly Agreed To and Finally Passed", "Approved by Governor (G)", "Vetoed in Part by Governor (G)",
  with date, sequence and the journal page; floor and committee votes as totals only), the governor's last action and
  veto letter link, the versions' and summaries' PDF links (with each version's roll-call PDFs), hearings, and subject
  index. members/<001>.xml, one per representative by district: name, party, committees with positions, Capitol
  phone, email, address, counties. A past year comes from its zip (read once; then the year is finished on the House
  side). Until the zip is listed, the current year's files are read from the live exports.
- senate/: list.json, the Senate's bill list for the year (from /BillTracking/Bills/BillList?year=2026&session=R, which
  carries its rows as JSON: bill id, prefix, number, sponsor and district, House handler, brief description);
  bills/<SB1>.html, each Senate bill (SB) and joint resolution (SJR)'s page (trimmed to its content: sponsor, LR
  number, current version ("SS SB 1"), House handler, effective date, committee, current status ("Signed by
  Governor"), amendments, and the Senate's current bill summary, a plain account of what it does); actions/<SB1>.html,
  its "All Actions" list (date, action, journal pages; both houses' steps: "S Third Read and Passed", "Truly Agreed To
  and Finally Passed", "Signed by Governor"). committees/<id>.html and committees.json: each Senate committee that year
  (from the /Committees/CommitteeGroup pages) with its members and their roles ("Chair", "Vice-Chair").
- journals/house/<jrn043>.txt.gz and journals/senate/<DAY08>.txt.gz: each day's House and Senate Journal (PDFs, turned
  into text with pdftotext -layout) that a bill's actions point to. They hold every floor roll call member by member
  ("AYES: 086" then the names, "Brown 149"; "YEAS—Senators" ... "Williams—31"), which the exports and pages have only
  as totals. House journals come from documents.house.mo.gov (/BillTracking/bills251/jrnpdf/jrn043.pdf), Senate ones
  from /25info/pdf-jrnl/DAY08.pdf. While a year is live, a journal is read once more a few days after it was first
  read (journals are corrected).
- house/summaries/<HB2>.txt: the House's summary of each House bill's latest version (the bill XML's last BillSummary
  PDF, /billtracking/bills251/sumpdf/HB0002T.pdf, as text). Read again when that link changes.
- state/: what was read and when, one file per thread's part so the two never write the same file: house.json (the zip,
  or each bill's and member's LastTimeRun when read; each summary's link; "finished" once the year's zip is in),
  senate.json (each bill's read day and SenateActList hash, the committees' read day; "finished" once every Senate bill
  has been read after the year's session and veto session, from October 1), journals-house.json and
  journals-senate.json (each journal's read day).
And into data/mo/members/: senators.html (the current senators' list, /Senators) and senate/<id>.html (each senator's
page, trimmed), and senate.json read from them: name, district, party (with any leadership post: "Majority Caucus
Secretary - Republican"), Capitol address and phone, the "Email the Senator" contact form (the pages give no email
address), staff, committees with "Chair"/"Vice-Chair". Read when older than a week. The representatives are the
current year's house/members/.

The Senate's bill pages give no change dates: until a year's Senate side is finished, its bills are read again when older than
a day during the session (January to May) and a week otherwise (at most REFRESH_MAX a run, oldest first), and at once
when the House's SenateActList entry for the bill changes.

Order of work: what was never downloaded first (lists, members, bills, Senate bill pages), then changes, then the
extras that fill in on later runs: journals (votes by member) and the House's summaries. Time: the House host's
20-second pace sets it. A first copy of three years is two zips plus, for the current year until its zip appears, about
2,200 files at 20 seconds (about 12 hours: several runs), then about 75 House journals a year (25 minutes each) and the
House summaries (about 1,700 a year, 9 hours each: these fill in over a few days of runs). The Senate side (about 900
bills a year, two pages each, plus journals and members) takes about 1½ hours in all, alongside. After the first copy a
run reads the House lists and whatever changed, and the Senate list: a few minutes out of session.

Not downloaded: the bill texts, fiscal notes, amendments, witness forms and committee minutes (PDFs); the House's
roll-call PDFs (the same votes as the journals, one file per vote: 362 in 2025 at 20 seconds each); the House's member
pages (house.mo.gov, barred). Committee votes by member are only in minutes. PDF work needs pdftotext (poppler-utils);
without it the journals and summaries are skipped, with a note.

data/mo/incomplete says "running" during a first copy, then lists what was never downloaded (a year's House bill list
or zip, a listed House bill, the Senate list, a listed Senate bill's page or actions, the members of either house); it
is removed when nothing is missing. Journals and summaries are extras and never hold it. A request that fails where a
last copy exists keeps that copy and doesn't count; a year whose lists don't exist yet doesn't count.
Usage: python3 states/mo/fetch.py [year]   (default: every year above; a single year leaves the marker alone)
"""
import gzip, hashlib, html, io, json, os, re, shutil, subprocess, sys, tempfile, threading, time, urllib.error
import urllib.request, zipfile
from collections import Counter
from datetime import date, timedelta

HOUSE = "https://documents.house.mo.gov"
SENATE = "https://www.senate.mo.gov"
DATA = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "mo"))
AGENT = "statebilltracker.org (a nonprofit bill tracker; contact via github.com/judithhubbard)"
TODAY = date.today()
YEAR = TODAY.year
ONLY = int(sys.argv[1]) if len(sys.argv) > 1 else None
DELAYS = {HOUSE: 20.0, SENATE: 1.0}  # seconds from the end of one answer to the next request (House: its Crawl-delay)
HOUSE_KIND = re.compile(r"^(HB|HJR)\d+$")
SENATE_KIND = re.compile(r"^(SB|SJR)\d+$")
LISTS = ("BillList", "MemberList", "CommitteeList", "SenateActList")
REFRESH_MAX = 400  # Senate bills read again per run for being old
MEMBER_DAYS = 7
JOURNAL_RECHECK = (3, 14)  # a live year's journal is read once more when its copy is 3 to 14 days old
PDFTOTEXT = shutil.which("pdftotext")
MARKER = os.path.join(DATA, "incomplete")

# The run's own time limit (FETCH_MINUTES, set by the workflow): stop a few minutes early, with everything read so far
# saved and a summary printed, rather than be cut off silently mid-request.
START = time.time()
BUDGET = max(0.0, float(os.environ.get("FETCH_MINUTES") or 0) - 5) * 60
LOCK = threading.Lock()
FAILS = Counter()  # why requests failed, for the summary
STATS = Counter()  # requests per host, and what was read
LAST = {HOUSE: 0.0, SENATE: 0.0}  # when each host's last answer ended
REFUSED = {}
CRASHED = []  # threads that stopped on an error (the run then exits 1)


class Refused(Exception):
    """The server turned us away (401/403/429): stop reading that host this run."""


def out_of_time():
    return BUDGET and time.time() - START > BUDGET


def log(msg):
    with LOCK:
        print(msg, flush=True)


def request(url, label, must=None, binary=False):
    """The answer at url (bytes when binary, else text), or None after three tries; None at once for a 404. must is
    text the answer has to contain (else it counts as a failure: both hosts serve error pages as 200)."""
    host = HOUSE if url.startswith(HOUSE) else SENATE if url.startswith(SENATE) else None
    if host is None:
        raise ValueError(f"not a host this script reads: {url}")
    for attempt in range(3):
        if out_of_time():
            return None
        wait = LAST[host] + DELAYS[host] - time.time()
        if wait > 0:
            time.sleep(wait)
        with LOCK:
            STATS[host] += 1
            n = STATS[host]
        if n % (25 if host == HOUSE else 200) == 0:
            log(f"  {'House' if host == HOUSE else 'Senate'}: {n} requests, {round((time.time() - START) / 60)} min"
                + (f"; failures {dict(FAILS)}" if FAILS else ""))
        try:
            req = urllib.request.Request(url, headers={"User-Agent": AGENT, "Accept-Encoding": "gzip"})
            with urllib.request.urlopen(req, timeout=120) as r:
                body = r.read()
                if r.headers.get("Content-Encoding") == "gzip":
                    body = gzip.decompress(body)
            LAST[host] = time.time()
            if must is not None and must not in body:
                with LOCK:
                    FAILS["unexpected answer"] += 1
            else:
                return body if binary else body.decode("utf-8-sig", "replace")
        except urllib.error.HTTPError as e:
            LAST[host] = time.time()
            with LOCK:
                FAILS[f"HTTP {e.code}"] += 1
            if e.code in (401, 403, 429):
                raise Refused(f"{label}: HTTP {e.code}")
            if e.code == 404:
                return None
        except Exception as e:
            LAST[host] = time.time()
            with LOCK:
                FAILS[type(e).__name__] += 1
        time.sleep(10 * (attempt + 1))
    log(f"{label}: failed three times")
    return None


def save_bytes(body, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "wb") as f:
        f.write(body)
    os.replace(tmp, path)


def save_text(body, path):
    save_bytes(body.encode("utf-8"), path)


def save(obj, path):
    save_bytes(json.dumps(obj, ensure_ascii=False, indent=0).encode("utf-8"), path)


def load(path, default=None):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def read_text(path):
    try:
        with open(path, encoding="utf-8-sig") as f:
            return f.read()
    except OSError:
        return ""


def text(fragment):
    t = re.sub(r"<br\s*/?>", "\n", fragment)
    t = html.unescape(re.sub(r"<[^>]+>", " ", t)).replace("\xa0", " ").replace("\r", "")
    return "\n".join(x for x in (re.sub(r"[ \t]+", " ", line).strip() for line in t.split("\n")) if x)


def trim(page):
    """A Senate page's content (its <main>), without scripts and styles."""
    a = page.find("<main")
    b = page.find("</main>", max(a, 0))
    body = page[max(a, 0):b + 7 if b > 0 else len(page)]
    return re.sub(r"<script\b.*?</script>|<style\b.*?</style>", "", body, flags=re.S)


def pdf_text(body):
    """A PDF's text (pdftotext -layout), or None."""
    if not body or not body.startswith(b"%PDF"):
        return None
    with tempfile.TemporaryDirectory() as tmp:
        src = os.path.join(tmp, "in.pdf")
        with open(src, "wb") as f:
            f.write(body)
        try:
            out = subprocess.run([PDFTOTEXT, "-layout", "-enc", "UTF-8", src, "-"], capture_output=True, timeout=300)
        except Exception:
            return None
        return out.stdout.decode("utf-8", "replace") if out.returncode == 0 else None


def code_of(year):
    """The House's code for a year's regular session: 2026 -> "261"."""
    return f"{year % 100:02d}1"


def finished_by(year):
    """From this day a year's bills no longer change: the governor's deadline and the veto session are past."""
    return f"{year}-10-01"


def live(year):
    return TODAY.isoformat() < finished_by(year)


def in_session():
    return 1 <= TODAY.month <= 5


def exists_once(year):
    """Whether a year's lists should exist by now (next year's only from December 1)."""
    return year <= YEAR


def folder(year, *parts):
    return os.path.join(DATA, str(year), *parts)


def state_path(year, part):
    """Each part's state in its own file, so the two threads never write the same one: "house" (the House thread's
    bills, members and summaries), "senate", and each house's journals ("journals-house", "journals-senate")."""
    return folder(year, "state", part + ".json")


def load_state(year, part):
    return load(state_path(year, part), {})


def save_state(year, part, state):
    save(state, state_path(year, part))


# ---------------------------------------------------------------- the House's exports

def xml_rows(page, tag):
    """[{child: text}] for each <tag> element of a flat export list."""
    out = []
    for m in re.finditer(rf"<{tag}>(.*?)</{tag}>", page, re.S):
        out.append({k: html.unescape(v).strip() for k, v in re.findall(r"<(\w+)>([^<]*)</\1>", m.group(1))})
    return out


def past_zips():
    """{year: zip url} for the regular sessions on the House's past-exports page; None when unreadable."""
    page = request(f"{HOUSE}/XMLPastExports.html", "House past exports", must=b"Regular Session")
    if not page:
        return None
    out = {}
    for m in re.finditer(r'href="(https://documents\.house\.mo\.gov/xml/\d{3}\.zip)"[^>]*>\s*(\d{4}) Regular Session', page):
        out[int(m.group(2))] = m.group(1)
    return out


ZIP_NAME = re.compile(r"^(\d{3})-(.+)\.xml$", re.I)


def take_zip(year, url, state):
    """A past session's zip: its bill, member and list files into house/. True when taken."""
    body = request(url, f"{year} House zip", binary=True)
    if not body or not body.startswith(b"PK"):
        log(f"{year} House zip: unreadable")
        return False
    base = folder(year, "house")
    got = Counter()
    try:
        with zipfile.ZipFile(io.BytesIO(body)) as z:
            for info in z.infolist():
                m = ZIP_NAME.match(os.path.basename(info.filename))
                if not m or m.group(1) != code_of(year) or info.file_size > 50_000_000:
                    continue
                name = m.group(2)
                if HOUSE_KIND.match(name.upper()):
                    path, kind = os.path.join(base, "bills", name.upper() + ".xml"), "bills"
                elif re.fullmatch(r"\d{3}", name):
                    path, kind = os.path.join(base, "members", name + ".xml"), "members"
                elif name in LISTS:
                    path, kind = os.path.join(base, name + ".xml"), "lists"
                else:
                    continue
                save_bytes(z.read(info), path)
                got[kind] += 1
    except zipfile.BadZipFile:
        log(f"{year} House zip: not a zip")
        return False
    if not got["bills"]:
        log(f"{year} House zip: no bills in it")
        return False
    state["zip"] = {"url": url, "read": TODAY.isoformat()}
    state["finished"] = True
    log(f"{year} House zip: {got['bills']} bills and joint resolutions, {got['members']} members, {got['lists']} lists")
    return True


def house_lists(year, state):
    """The current exports' lists for a year not yet in a zip. Returns {"bills": {key: (url, stamp)}, "members": ...}."""
    code, base = code_of(year), folder(year, "house")
    out = {"bills": {}, "members": {}}
    for name in LISTS:
        page = request(f"{HOUSE}/xml/{code}-{name}.XML", f"{year} House {name}", must=b"<ROOT")
        path = os.path.join(base, name + ".xml")
        if page:
            save_text(page, path)
        elif exists_once(year) and os.path.exists(path):
            log(f"{year} House {name}: unreadable; kept the last copy")
    for row in xml_rows(read_text(os.path.join(base, "BillList.xml")), "BillXML"):
        key = (row.get("BillType", "") + row.get("BillNumber", "")).upper()
        url = row.get("BillXMLLink", "")
        if HOUSE_KIND.match(key) and url.startswith(HOUSE + "/"):
            out["bills"][key] = (url, row.get("LastTimeRun", ""))
    for row in xml_rows(read_text(os.path.join(base, "MemberList.xml")), "RepresentativeXML"):
        d, url = row.get("RepresentativeDistrict", ""), row.get("RepresentativeXMLLink", "")
        if re.fullmatch(r"\d{3}", d) and url.startswith(HOUSE + "/"):
            out["members"][d] = (url, row.get("LastTimeRun", ""))
    return out


def house_files(year, state, wanted, kind, label):
    """Reads each file in wanted ({key: (url, stamp)}) never read or whose stamp changed, missing ones first."""
    stamps = state.setdefault(kind, {})
    base = folder(year, "house", kind)
    missing = [k for k in wanted if not os.path.exists(os.path.join(base, k + ".xml"))]
    changed = [k for k in wanted if k not in missing and stamps.get(k) != wanted[k][1]]
    todo = missing + changed
    if todo:
        log(f"{year} House {label}: {len(wanted)} listed; {len(missing)} never read, {len(changed)} changed")
    got = 0
    for k in todo:
        if out_of_time():
            break
        page = request(wanted[k][0], f"{year} House {k}", must=b"<ROOT")
        if not page:
            continue  # the last copy stays, and it's asked again next run
        save_text(page, os.path.join(base, k + ".xml"))
        stamps[k] = wanted[k][1]
        got += 1
        STATS[f"house {kind}"] += 1
        if got % 10 == 0:
            save_state(year, "house", state)
    save_state(year, "house", state)
    if todo:
        log(f"{year} House {label}: {got} of {len(todo)} read")


def house_zip(year, zips):
    """A year's zip, when listed and not yet taken (a request or two: before any year's file-by-file reading)."""
    state = load_state(year, "house")
    if state.get("finished"):
        return
    url = (zips or {}).get(year)
    if url and take_zip(year, url, state):
        save_state(year, "house", state)
    elif year < YEAR - 1 and zips is not None:
        log(f"{year}: no House zip listed")


def house_year(year):
    state = load_state(year, "house")
    if state.get("finished"):
        return
    lists = house_lists(year, state)
    if year == YEAR:
        house_files(year, state, lists["members"], "members", "members")
    house_files(year, state, lists["bills"], "bills", "bills and joint resolutions")


def house_journal_names(year):
    """The House Journal files a year's actions point to ("jrn043"), from the House bill XMLs and SenateActList."""
    code, names = code_of(year), set()
    paths = [os.path.join(folder(year, "house", "bills"), f) for f in os.listdir(folder(year, "house", "bills"))] \
        if os.path.isdir(folder(year, "house", "bills")) else []
    paths.append(folder(year, "house", "SenateActList.xml"))
    for p in paths:
        for c, name in re.findall(r"/BillTracking/bills(\d{3})/jrnpdf/(jrn\d+)\.pdf", read_text(p), re.I):
            if c == code:
                names.add(name.lower())
    return names


def senate_journal_names(year):
    """The Senate Journal files a year's Senate bill actions point to ("DAY08")."""
    names, d = set(), folder(year, "senate", "actions")
    for f in (os.listdir(d) if os.path.isdir(d) else []):
        for yy, name in re.findall(r"senate\.mo\.gov/(\d\d)info/pdf-jrnl/([A-Za-z0-9_-]+)\.pdf", read_text(os.path.join(d, f)), re.I):
            if yy == f"{year % 100:02d}":
                names.add(name)
    return names


def journals(year, house):
    """The year's journals of one house (house True: the House's), as text: missing ones, then a live year's rechecks."""
    if not PDFTOTEXT:
        return
    which = "house" if house else "senate"
    got_at = load_state(year, "journals-" + which)
    names = house_journal_names(year) if house else senate_journal_names(year)
    base = folder(year, "journals", which)
    missing = sorted(n for n in names if not os.path.exists(os.path.join(base, n + ".txt.gz")))
    recheck = []
    if live(year):
        for n in sorted(names):
            first = got_at.get(n) or {}
            if first and not first.get("rechecked"):
                age = (TODAY - date.fromisoformat(first["read"])).days
                if JOURNAL_RECHECK[0] <= age <= JOURNAL_RECHECK[1]:
                    recheck.append(n)
    todo = missing + recheck
    if not todo:
        return
    log(f"{year} {which} journals: {len(names)} referred to; {len(missing)} never read, {len(recheck)} to read again")
    got = 0
    for n in todo:
        if out_of_time() or REFUSED.get(HOUSE if house else SENATE):
            break
        url = (f"{HOUSE}/BillTracking/bills{code_of(year)}/jrnpdf/{n}.pdf" if house
               else f"{SENATE}/{year % 100:02d}info/pdf-jrnl/{n}.pdf")
        body = request(url, f"{year} {which} journal {n}", must=b"%PDF", binary=True)
        t = pdf_text(body)
        if not t:
            continue
        save_bytes(gzip.compress(t.encode("utf-8"), mtime=0), os.path.join(base, n + ".txt.gz"))
        got_at[n] = {"read": TODAY.isoformat(), "rechecked": n in recheck or not live(year)}
        got += 1
        STATS[f"{which} journals"] += 1
        if got % 5 == 0:
            save_state(year, "journals-" + which, got_at)
    save_state(year, "journals-" + which, got_at)
    log(f"{year} {which} journals: {got} of {len(todo)} read")


def summaries(year):
    """The House's summary of each House bill's latest version, as text."""
    if not PDFTOTEXT:
        return
    base = folder(year, "house", "bills")
    if not os.path.isdir(base):
        return
    state = load_state(year, "house")
    done = state.setdefault("summaries", {})
    wanted = {}
    for f in sorted(os.listdir(base)):
        links = re.findall(r"<SummaryTextLink>\s*([^<]+?)\s*</SummaryTextLink>", read_text(os.path.join(base, f)))
        links = [html.unescape(x) for x in links if x.strip().lower().startswith(HOUSE.lower() + "/")]
        if links:
            wanted[f[:-4]] = HOUSE + links[-1][len(HOUSE):]
    todo = [k for k, u in wanted.items() if done.get(k) != u or not os.path.exists(folder(year, "house", "summaries", k + ".txt"))]
    if not todo:
        return
    log(f"{year} House summaries: {len(wanted)} bills with one; {len(todo)} to read")
    got = 0
    for k in todo:
        if out_of_time():
            break
        body = request(wanted[k], f"{year} House summary {k}", must=b"%PDF", binary=True)
        t = pdf_text(body)
        if t is None:
            continue
        save_text(t, folder(year, "house", "summaries", k + ".txt"))
        done[k] = wanted[k]
        got += 1
        STATS["house summaries"] += 1
        if got % 10 == 0:
            save_state(year, "house", state)
    save_state(year, "house", state)
    log(f"{year} House summaries: {got} of {len(todo)} read")


def house_main(years):
    try:
        need_zip = [y for y in years if not load_state(y, "house").get("finished") and exists_once(y)]
        zips = past_zips() if need_zip else {}
        for year in years:
            if out_of_time():
                break
            house_zip(year, zips)
        for year in years:
            if out_of_time():
                break
            house_year(year)
        for year in years:  # the extras, after everything core
            if out_of_time():
                break
            journals(year, house=True)
        for year in years:
            if out_of_time():
                break
            summaries(year)
        if not PDFTOTEXT:
            log("House: pdftotext isn't installed; journals and summaries not read")
    except Refused as e:
        REFUSED[HOUSE] = str(e)
        log(f"House: stopped, the server refused a request ({e})")
    except Exception:
        CRASHED.append("House")
        raise


# ---------------------------------------------------------------- the Senate's website

def senate_list(year):
    """The Senate's bill list for a year: [{billId, billPrefix, billSuffix, ...}], saved as list.json; None if unread."""
    page = request(f"{SENATE}/BillTracking/Bills/BillList?year={year}&session=R", f"{year} Senate list",
                   must=b"const bills = ")
    path = folder(year, "senate", "list.json")
    rows = None
    if page:
        i = page.find("const bills = ")
        try:
            rows, _ = json.JSONDecoder().raw_decode(page, i + len("const bills = "))
        except ValueError:
            rows = None
    if rows:
        save(rows, path)
        return rows
    last = load(path)
    if last:
        log(f"{year} Senate list: unreadable; kept the last copy")
    return last


def senate_act_hashes(year):
    """{key: hash} of each Senate bill's entry in the House's SenateActList, to notice House steps on it."""
    out = {}
    for m in re.finditer(r"<BillInformation>(.*?)</BillInformation>", read_text(folder(year, "house", "SenateActList.xml")), re.S):
        k = re.search(r"<BillNumber>([^<]+)</BillNumber>", m.group(1))
        if k:
            out[k.group(1).strip().upper()] = hashlib.sha1(m.group(1).encode()).hexdigest()[:12]
    return out


def senate_year(year):
    sen = load_state(year, "senate")
    if sen.get("finished"):
        return
    rows = senate_list(year)
    if not rows:
        if exists_once(year):
            log(f"{year}: no Senate list")
        return
    bills = {}
    for r in rows:
        key = f"{r.get('billPrefix', '')}{r.get('billSuffix', '')}".upper()
        if SENATE_KIND.match(key) and str(r.get("billId", "")).isdigit():
            bills[key] = r
    read, acts = sen.setdefault("read", {}), sen.setdefault("house_acts", {})
    hashes = senate_act_hashes(year)
    base = folder(year, "senate")
    missing = [k for k in bills if not (os.path.exists(os.path.join(base, "bills", k + ".html"))
                                        and os.path.exists(os.path.join(base, "actions", k + ".html")))]
    todo = list(missing)
    if live(year):
        todo += [k for k in bills if k not in todo and k in hashes and acts.get(k) != hashes[k]]
        stale = (TODAY - timedelta(days=1 if in_session() else 7)).isoformat()
        old = sorted((read.get(k, ""), k) for k in bills if k not in todo and read.get(k, "") < stale)
        todo += [k for _, k in old[:REFRESH_MAX]]
    else:
        # After the session, every bill is read once more (so the year can be finished).
        todo += [k for k in bills if k not in todo and read.get(k, "") < finished_by(year)]
    log(f"{year} Senate: {len(bills)} bills and joint resolutions listed; {len(missing)} never read, {len(todo)} to read")
    got = 0
    for k in todo:
        if out_of_time():
            break
        r = bills[k]
        bid, prefix, num = r["billId"], r["billPrefix"], r["billSuffix"]
        page = request(f"{SENATE}/BillTracking/Bills/BillInformation?year={year}&billid={bid}", f"{year} Senate {k}",
                       must=b"Bill Details")
        if not page:
            continue
        acts_page = request(f"{SENATE}/BillTracking/Bills/BillInformation?year={year}&billId={bid}&billPrefix={prefix}"
                            f"&billSuffix={num}&handler=Actions", f"{year} Senate {k} actions", must=b'id="actionsTable"')
        if not acts_page:
            continue
        save_text(trim(page), os.path.join(base, "bills", k + ".html"))
        save_text(re.sub(r"<script\b.*?</script>|<style\b.*?</style>", "", acts_page, flags=re.S),
                  os.path.join(base, "actions", k + ".html"))
        read[k] = TODAY.isoformat()
        if k in hashes:
            acts[k] = hashes[k]
        got += 1
        STATS["senate bills"] += 1
        if got % 25 == 0:
            save_state(year, "senate", sen)
    log(f"{year} Senate bills: {got} of {len(todo)} read")
    committees(year, sen)
    if not live(year) and bills and all(read.get(k, "") >= finished_by(year) for k in bills) \
            and sen.get("committees") and not out_of_time():
        sen["finished"] = True
        log(f"{year} Senate: finished")
    save_state(year, "senate", sen)


def committees(year, sen):
    """The year's Senate committees and their members: read once for a past year, weekly for a live one."""
    last = sen.get("committees") or ""
    if last and (not live(year) or last >= (TODAY - timedelta(days=MEMBER_DAYS)).isoformat()):
        return
    if out_of_time():
        return
    home = request(f"{SENATE}/Committees", "Senate committees", must=b"CommitteeGroup")
    types = sorted(set(re.findall(r"CommitteeGroup\?type=(\d+)", home or "")), key=int) or ["1", "2", "5", "8"]
    found = {}
    for t in types:
        page = request(f"{SENATE}/Committees/CommitteeGroup?type={t}&year={year}", f"{year} Senate committee group {t}",
                       must=b"Committee")
        if page is None:
            return
        heading = re.search(r'card__header card__header--bold"><span[^>]*>(.*?)</span>', page, re.S)
        group = text(heading.group(1)) if heading else t
        for cid in re.findall(r"CommitteeDetail\?id=(\d+)&amp;year=\d+", page):
            found.setdefault(cid, {"id": int(cid), "type": t, "group": group})
    if not found:
        log(f"{year} Senate committees: none listed")
        return
    out, ok = [], True
    for cid, c in found.items():
        if out_of_time():
            return
        page = request(f"{SENATE}/Committees/CommitteeDetail?id={cid}&year={year}", f"{year} Senate committee {cid}",
                       must=b"card__header")
        if page is None:
            ok = False  # its last copy, if any, stays; all are asked again next run
            continue
        body = trim(page)
        save_text(body, folder(year, "senate", "committees", f"{cid}.html"))
        name = re.search(r'card__header card__header--bold">\s*<span[^>]*>(.*?)</span>', body, re.S)
        members = []
        # Joint committees list representatives too ("Representative Taylor").
        for full, house, short, role in re.findall(r'alt="(?:Senator|Representative|Rep) ([^"]+)">.*?card__footer[^>]*>\s*'
                                                   r'(Senator|Representative) ([^<]+?)\s*<br\s*/?>\s*([^<]*?)\s*</div>',
                                                   body, re.S):
            members.append({"name": html.unescape(full).strip(), "house": "S" if house == "Senator" else "H",
                            "short": html.unescape(short).strip(), "role": html.unescape(role).strip()})
        out.append(dict(c, name=text(name.group(1)) if name else "", members=members))
    if not ok and os.path.exists(folder(year, "senate", "committees.json")):
        log(f"{year} Senate committees: {len(out)} of {len(found)} read; kept the last list")
        return
    save(out, folder(year, "senate", "committees.json"))
    if ok:
        sen["committees"] = TODAY.isoformat()
    log(f"{year} Senate committees: {len(out)} ({sum(1 for c in out for m in c['members'] if m['role'] == 'Chair')} chairs)")


def senator(sid, page):
    """One senator's fields from the page."""
    body = trim(page)
    def field(label):
        m = re.search(rf'detail-grid__label[^>]*>\s*{label}\s*</span>\s*<span[^>]*>(.*?)</span>', body, re.S)
        return text(m.group(1)) if m else ""
    contact = re.search(r"Contact Information</span>.*?<div[^>]*aria-live=\"polite\">(.*?)</div>", body, re.S)
    lines = text(contact.group(1)).split("\n") if contact else []
    phones = re.findall(r"\(?\d{3}\)?[-. ]\d{3}-\d{4}", "\n".join(lines))
    form = re.search(r'href="(https://www\.senate\.mo\.gov/Senators/WebApplications/Disclaimer\?DistrictNumber=\d+)"', body)
    comms = [{"id": int(i), "name": re.sub(r",\s*(Chair|Vice-Chair)$", "", text(n)),
              "role": (re.search(r",\s*(Chair|Vice-Chair)$", text(n)) or [None, ""])[1]}
             for i, n in re.findall(r'CommitteeDetail\?year=\d+&amp;id=(\d+)"[^>]*>(.*?)</a>', body, re.S)]
    name = re.search(r"<h1[^>]*>(.*?)</h1>", body, re.S)
    return {"id": sid, "name": text(name.group(1)) if name else "", "party": field("Party"),
            "district": int(re.sub(r"\D", "", field("District")) or 0) or None,
            "address": ", ".join(x for x in lines if not re.fullmatch(r"\(?\d{3}\)?[-. ]\d{3}-\d{4}", x)),
            "phone": phones[0] if phones else "", "contact_form": html.unescape(form.group(1)) if form else "",
            "staff": "; ".join(re.sub(r"\s+", " ", x) for x in field("Legislative Staff").split("\n")), "committees": comms}


def senators():
    """The current senators, weekly."""
    base = os.path.join(DATA, "members")
    path = os.path.join(base, "senate.json")
    last = load(path)
    if last and last.get("read", "") >= (TODAY - timedelta(days=MEMBER_DAYS)).isoformat():
        return
    page = request(f"{SENATE}/Senators", "senators", must=b"Senators/Member?id=")
    cards = re.findall(r'Senators/Member\?id=(\d+)" aria-label="View Senator ([^"]+?) details page".*?District (\d+)',
                       page or "", re.S)
    if not cards:
        log("senators: unreadable; kept the last copy")
        return
    save_text(trim(page), os.path.join(base, "senators.html"))
    out, ok = [], True
    for sid, name, district in cards:
        p = request(f"{SENATE}/Senators/Member?id={sid}", f"senator {sid}", must=b"detail-grid")
        if not p:
            ok = False
            continue
        save_text(trim(p), os.path.join(base, "senate", f"{sid}.html"))
        s = senator(int(sid), p)
        s["name"] = s["name"] or html.unescape(name)
        s["list_name"], s["district"] = html.unescape(name), int(district)
        out.append(s)
    if ok:
        save({"read": TODAY.isoformat(), "members": out}, path)
        log(f"senators: {len(out)} ({sum(1 for s in out if s['phone'])} with phones)")
    else:
        log(f"senators: {len(out)} of {len(cards)} pages read; kept the last list")


def senate_main(years):
    try:
        if not ONLY:
            senators()
        for year in years:
            if out_of_time():
                break
            senate_year(year)
        for year in years:
            if out_of_time():
                break
            journals(year, house=False)
    except Refused as e:
        REFUSED[SENATE] = str(e)
        log(f"Senate: stopped, the server refused a request ({e})")
    except Exception:
        CRASHED.append("Senate")
        raise


# ---------------------------------------------------------------- the run

def years_wanted():
    if ONLY:
        return [ONLY]
    ys = [YEAR, YEAR - 1, YEAR - 2]
    if TODAY.month == 12:
        ys.insert(0, YEAR + 1)  # prefiled bills
    return ys


def begun(year):
    """Whether a year's session has convened (the Wednesday after the first Monday of January)."""
    return TODAY >= date(year, 1, 3 + (0 - date(year, 1, 1).weekday()) % 7)


def never_downloaded(years):
    """What was never downloaded: a year's House bill list (or zip), a listed House bill, the Senate list, a listed
    Senate bill's page or actions, either house's members. (A failed refresh with a last copy doesn't count; nor does a
    year whose lists don't exist yet.)"""
    out = []
    if not os.path.exists(os.path.join(DATA, "members", "senate.json")):
        out.append("senators")
    years = [y for y in years if begun(y)]  # prefiled bills are read, but don't hold Missouri back before the session
    current = max(y for y in years if y <= YEAR) if any(y <= YEAR for y in years) else None
    for year in years:
        if not exists_once(year):
            continue
        hb = folder(year, "house")
        listed = [(r.get("BillType", "") + r.get("BillNumber", "")).upper()
                  for r in xml_rows(read_text(os.path.join(hb, "BillList.xml")), "BillXML")]
        if not listed and not load_state(year, "house").get("finished"):
            out.append(f"{year}:house-list")
        elif any(HOUSE_KIND.match(k) and not os.path.exists(os.path.join(hb, "bills", k + ".xml")) for k in listed):
            out.append(f"{year}:house-bills")
        if year == current:
            reps = [r.get("RepresentativeDistrict", "") for r in xml_rows(read_text(os.path.join(hb, "MemberList.xml")),
                                                                          "RepresentativeXML")]
            if not reps or any(not os.path.exists(os.path.join(hb, "members", d + ".xml")) for d in reps):
                out.append(f"{year}:representatives")
        rows = load(folder(year, "senate", "list.json"))
        if not rows:
            out.append(f"{year}:senate-list")
            continue
        keys = [f"{r.get('billPrefix', '')}{r.get('billSuffix', '')}".upper() for r in rows]
        sb = folder(year, "senate")
        if any(SENATE_KIND.match(k) and not (os.path.exists(os.path.join(sb, "bills", k + ".html"))
                                             and os.path.exists(os.path.join(sb, "actions", k + ".html"))) for k in keys):
            out.append(f"{year}:senate-bills")
    return out


def main():
    os.makedirs(DATA, exist_ok=True)
    # Before the first copy, a run cut off without its summary leaves this, so a partial copy isn't published.
    if not ONLY and not any(name.isdigit() for name in os.listdir(DATA)):
        with open(MARKER, "w") as f:
            f.write("running\n")
    years = years_wanted()
    threads = [threading.Thread(target=house_main, args=(years,)), threading.Thread(target=senate_main, args=(years,))]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    missing = never_downloaded(years)
    read = ", ".join(f"{v} {k}" for k, v in sorted(STATS.items()) if not k.startswith("http"))
    log(f"run: {STATS[HOUSE]} House and {STATS[SENATE]} Senate requests"
        + (f" ({read})" if read else "") + f", {round((time.time() - START) / 60)} min"
        + ("; stopped at the time limit" if out_of_time() else "")
        + ("; refused: " + "; ".join(REFUSED.values()) if REFUSED else "")
        + (f"; request failures {dict(FAILS)}" if FAILS else "; no request failures")
        + ("" if PDFTOTEXT else "; no pdftotext (journals and summaries skipped)")
        + (f"; never downloaded: {' '.join(missing)}" if missing else "; nothing missing"))
    if CRASHED:
        sys.exit(1)
    if ONLY:
        return
    # Left while data that was never downloaded is missing, so a partial first copy isn't published.
    if missing:
        with open(MARKER, "w") as f:
            f.write(" ".join(missing) + "\n")
    elif os.path.exists(MARKER):
        os.remove(MARKER)


if __name__ == "__main__":
    main()
