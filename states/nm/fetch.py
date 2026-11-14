#!/usr/bin/env python3
"""Download New Mexico's bills from the Legislature's website, www.nmlegis.gov: the session's legislation list and
each bill's page (ASP.NET pages, server-built HTML), the Legislature's own database as a download, and the session
folders the site serves its documents from (plain IIS folder listings: /Sessions/25%20Regular/votes/). There is no
API. robots.txt (checked 2026-11-09; nmlegis.gov only redirects to www.) bars, for all user agents, only /*.axd (and,
for Googlebot, /signalr/), none of which are read, and sets no crawl delay (AhrefsBot alone is asked for 2 seconds).
One request at a time, a second apart (counted from the end of the last answer).

New Mexico's Legislature meets every year from the third Tuesday of January: 60 days in odd years, 30 in even years
(budget, and only what the governor puts on the call, plus vetoed bills); the governor has 3 days during the session
and 20 days after it, and a bill not signed by then is pocket vetoed. Line-item vetoes are allowed on appropriations.
Constitutional amendments are joint resolutions (HJR, SJR): they pass both houses and go to the voters, not the
governor. Special sessions are left out. For each regular session from two years back through this one (and next
year's once the site lists it, for bills prefiled in December), into data/nm/<year>/:
- list.json: {"session": 69 (the site's session id), "stamp" ("4/29/2026 12:27:26 PM": the site's "Last legislative
  database update", one stamp for the whole database), "read", "bills": {"HB5": {"chamber": "H", "type": "B", "number":
  5, "title": "OFFICE OF CHILD ADVOCATE ACT", "sponsors": [["HABMI", "Michelle Paulene Abeyta"], ...] (up to five, in
  order), "actions": "[5] HHHC/HJC-HHHC [8] DP-HJC [11] DP/a [12] fl/a- PASSED/H (64-0) ... SGND BY GOV (Mar. 21) Ch.
  13."}}}, from /Legislation/Legislation_List?Session=<id> (every bill, memorial and resolution of the session on one
  page, about 3 MB). The actions are in the Legislature's abbreviated code (/Legislation/Action_Abbreviations; saved
  as data/nm/abbreviations.html): "[n]" is the legislative day, "DP" do pass, "DNP-CS/DP" a committee substitute,
  "PASSED/H (64-0)", "h/cncrd", "SGND BY GOV (Mar. 21) Ch. 13.", "VETO.", "POCKET VETO.", "VETO OVERRIDE PASSED/H".
- bills/<HB5>.html: each House and Senate bill and joint resolution's page (/Legislation/Legislation?chamber=H&
  legType=B&legNo=5&year=25; trimmed to its content, scripts and styles removed): title, sponsors (all of them, in
  order, by sponsor code), current location, text versions, links to the floor votes, fiscal impact report, committee
  reports and substitutes, floor amendments, the governor's veto messages, and the actions by legislative and
  calendar day in plain English ("HAFC: Reported by committee with Do Pass recommendation", "Passed in the House of
  Representatives - Y:65 N:1", "Signed by Governor - Chapter 1 - Jan. 23"). Memorials and resolutions other than joint
  resolutions are left out (joint memorials too). Read when new, and again when its row in the list changes.
- LegInfo<yy>.zip: the Legislature's own database (/Sessions/25%20Regular/other/LegInfo25.zip, a Microsoft Access
  file, LegInfo25.accdb, 3-5 MB zipped). Its tables include Legislation (every bill: sponsors' codes, referrals,
  ActionText, chapter number, date signed, passed flags, "Floor Votes" and "CommitteeVotes" tallies, subject codes),
  Actions (coded steps by day), tblSponsors (codes, names, party, district), TblLocations (committees with chairs),
  TblActions (the action codes), BillSubs (substitutes), FloorActions (the order of business, with tallies and absent
  and excused names) and LegStats (the session's totals by party: passed, chapters, vetoes, pocket vetoes). It has no
  member-by-member votes. The site's own database: it's posted now and then (LegInfo26.zip on 4/29/2026, the day of
  the site's last database update); read when its listing changes. The converter doesn't read it (the pages carry
  everything shown); it was used once, by hand, to check the session totals.
- members.txt: the session's legislators (/Sessions/25%20Regular/Legislator%20Information/
  LegislatorsCommaDelimitedforMerging.txt: last name, first name, party, counties, district, mailing address, Capitol
  room, phone, email, "R"/"S"), read when its listing changes.
- votes/<HB0005HVOTE.PDF>.txt: the floor roll calls (/Sessions/25%20Regular/votes/, PDFs, as text by pdftotext
  -layout): one per bill and house for final passage ("HB0005HVOTE", "HB0005SVOTE"), named by day and roll call for
  others ("018.351": legislative day 18, roll call 351; the text names the bill). Every member by name, with YEA, NAY,
  PNV (present not voting), EXC(used) and ABSENT columns (House), or YES, NO, ABS, EXC, REC(used) (Senate). These are
  the only member-by-member floor votes: neither the pages nor the database have them. A file the listing shows as
  changed is read again (a later vote can replace one).
- reports/<HB0005JC1.HTML>.txt: committee reports as text (/Sessions/25%20Regular/bills/house/HB0005JC1.HTML: the
  committee's two-letter code and the report's number), with the recommendation, the amendments and the roll call:
  "The roll call vote was 9 For 0 Against / Yes: 9 / No: 0 / Excused: Hochman-Vigil, McQueen / Absent: None" (House
  reports name only the no, excused and absent members; Senate reports name the yes votes too). Floor amendments
  ("SB0005FS5") are named the same way and come along. Reports that tabled a bill (/Tabled_Reports/HB0028AA1T.pdf,
  PDFs) go in as text too.
- firs/<HB0005.PDF>.txt: the Legislative Finance Committee's fiscal impact report (/Sessions/25%20Regular/firs/),
  only its first part: the header (sponsor, "LAST UPDATED", bill number with amendments) and the SUMMARY (the
  "Synopsis of ..." paragraphs: "What it does"), up to FISCAL IMPLICATIONS. Read again when the listing changes.
- messages/<HB0012GovMsg.pdf>.txt: the governor's veto and line-item veto messages (/ExecMessages/house/ and
  /senate/). Pocket vetoes have no message.
- state.json: each folder listing's entries when the files were read ("listing": {"votes": {"HB0005HVOTE.PDF":
  "3/4/2025 12:22 PM 72448"}}), the day each folder was listed ("listed"), each bill's list row fingerprint when its
  page was read ("rows"), and bills whose page answered 404 ("absent").
And into data/nm/: sessions.json (the site's session ids: {"2025 Regular": 69}), members/house.html and senate.html
(the current members, /Members/Legislator_List?T=R and T=S), members/<HSZCZ>.html (each member's page by sponsor
code: name, party, leadership post ("Majority Floor Leader"), district, county, Capitol phone and room, email, phone,
district office, standing committees), members.json (what this script reads from them), committees/<HAFC>.html (each
standing committee's page: meeting days and room, members with district, party and role: Chair, Vice Chair, Ranking
Member, Member), committees.json, and leadership.html (/Members/Leadership). Members' and committees' pages are read
weekly for current members (and once for others who sponsored a bill: their pages keep their last details).

What changes and when: during a session (and until July 1, for the governor's actions and pocket vetoes), each run
reads the session's list, the bills whose row changed, and the folder listings, then the files new or changed in
them. Otherwise the lists and listings are read weekly. A first copy of three sessions (about 2,600 bills and joint
resolutions) is about 2,700 requests for the core (about an hour at a request a second plus the server's time), then
about 1,300 vote PDFs, 3,500 committee reports, 2,500 fiscal impact reports and the messages: several hours, built up
over several runs. A quiet run is a handful of requests.

data/nm/incomplete says "running" during the first copy, then lists what was never downloaded (the session ids, a
session's list, a listed bill's page, its database or members file once listed, the current members' lists); it is
removed when nothing is missing. Votes, committee reports, fiscal impact reports, messages, members' and committees'
pages fill in on later runs and don't hold the state back. A request that fails where a last copy exists keeps that
copy and doesn't count; a bill page that answers 404 is noted and doesn't count. PDFs need pdftotext (poppler-utils);
without it they are skipped (and say so). A file that isn't a readable PDF is saved empty and asked for again only when
its listing changes.
Usage: python3 states/nm/fetch.py [year]   (default: every session above; a single year leaves the marker alone)
"""
import hashlib, html, json, os, re, shutil, subprocess, sys, tempfile, time, urllib.error, urllib.parse, urllib.request
from collections import Counter
from datetime import date, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
from listing_dates import same  # noqa: E402

SITE = "https://www.nmlegis.gov"
DATA = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "nm"))
AGENT = "statebilltracker.org (a nonprofit bill tracker; contact via github.com/judithhubbard)"
TODAY = date.today()
ONLY = int(sys.argv[1]) if len(sys.argv) > 1 else None
DELAY = 1.0  # seconds from the end of one answer to the next request
WEEKLY = 7
TYPES = ("B", "JR")  # bills and joint resolutions (constitutional amendments); not memorials or other resolutions
PDFTOTEXT = shutil.which("pdftotext")
MEMBERS = os.path.join(DATA, "members")
COMMITTEES = os.path.join(DATA, "committees")
MARKER = os.path.join(DATA, "incomplete")
# The session folders' extras: (kind, folder under /Sessions/<yy> Regular/, file name pattern, how to read it).
EXTRAS = (
    ("votes", "votes/", r"(?i).+\.pdf$", "pdf"),
    ("messages", "ExecMessages/house/", r"(?i).+\.pdf$", "pdf"),
    ("messages", "ExecMessages/senate/", r"(?i).+\.pdf$", "pdf"),
    ("reports", "bills/house/", r"(?i)^(HB|HJR)\d{4}[A-Z]{2}\d+\.html?$", "html"),
    ("reports", "bills/senate/", r"(?i)^(SB|SJR)\d{4}[A-Z]{2}\d+\.html?$", "html"),
    ("reports", "Tabled_Reports/", r"(?i)^(HB|SB|HJR|SJR)\d+.*\.pdf$", "pdf"),
    ("firs", "firs/", r"(?i)^(HB|SB|HJR|SJR)\d+.*\.pdf$", "fir"),
)

# The run's own time limit (FETCH_MINUTES, set by the workflow): stop a few minutes early, with everything read so far
# saved and a summary printed, rather than be cut off silently mid-request.
START = time.time()
BUDGET = max(0.0, float(os.environ.get("FETCH_MINUTES") or 0) - 5) * 60
FAILS = Counter()  # why requests failed, for the summary
STATS = Counter()
LAST = [0.0]  # when the last answer ended
GONE = object()  # a 404


class Refused(Exception):
    """The server turned us away (401/403/429): stop the run."""


def out_of_time():
    return BUDGET and time.time() - START > BUDGET


def request(path, label, must=None, binary=False, timeout=120):
    """SITE + path: text (or bytes when binary), GONE for a 404, None after three tries. must is a piece of text the
    page has to contain (else it counts as a failure: an error page served as 200)."""
    url = path if path.startswith("http") else SITE + path
    for attempt in range(3):
        if out_of_time():
            return None
        wait = LAST[0] + DELAY - time.time()
        if wait > 0:
            time.sleep(wait)
        STATS["requests"] += 1
        if STATS["requests"] % 100 == 0:
            print(f"  {STATS['requests']} requests, {round((time.time() - START) / 60)} min"
                  + (f"; failures {dict(FAILS)}" if FAILS else ""), flush=True)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": AGENT})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                body = r.read()
                length = r.headers.get("Content-Length")
            LAST[0] = time.time()
            if length and int(length) != len(body):
                FAILS["cut off"] += 1
            elif binary:
                return body
            else:
                try:
                    page = body.decode("utf-8")
                except UnicodeDecodeError:
                    page = body.decode("cp1252", "replace")
                if must is None or must in page:
                    return page
                FAILS["unexpected page"] += 1
        except urllib.error.HTTPError as e:
            LAST[0] = time.time()
            FAILS[f"HTTP {e.code}"] += 1
            if e.code in (401, 403, 429):
                raise Refused(f"{label}: HTTP {e.code}")
            if e.code == 404:
                return GONE
        except Exception as e:
            LAST[0] = time.time()
            FAILS[type(e).__name__] += 1
        time.sleep(10 * (attempt + 1))
    print(f"{label}: failed three times", flush=True)
    return None


def save(obj, path):
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(obj, f, ensure_ascii=False)
    os.replace(tmp, path)


def save_text(body, path):
    with open(path + ".tmp", "w", encoding="utf-8") as f:
        f.write(body)
    os.replace(path + ".tmp", path)


def save_bytes(body, path):
    with open(path + ".tmp", "wb") as f:
        f.write(body)
    os.replace(path + ".tmp", path)


def load(path, default=None):
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def text(fragment):
    """Plain text of an HTML fragment, whitespace collapsed."""
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", fragment))).strip()


def page_text(page):
    """A whole HTML document as text, line breaks kept (committee reports)."""
    page = re.sub(r"(?is)<(script|style|head)\b.*?</\1>", "", page)
    page = re.sub(r"(?i)<br\s*/?>|</p>|</div>|</tr>|</h\d>", "\n", page)
    out = html.unescape(re.sub(r"<[^>]+>", " ", page)).replace("\xa0", " ")
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in out.splitlines()]
    return "\n".join(line for line in lines if line) + "\n"


def trim(page):
    """A site page cut to its content: from the first MainContent element after the menus to the footer, without
    scripts and styles."""
    nav = page.find("Visit the Capitol")
    a = page.find('id="MainContent_', max(nav, 0))
    a = page.rfind("<", 0, a) if a > 0 else 0
    b = page.find("Visit the Capitol", a)
    body = page[a:b if b > a else len(page)]
    body = re.sub(r"(?is)<script\b.*?</script>|<style\b.*?</style>|<!--.*?-->", "", body)
    return re.sub(r"\n\s*\n+", "\n", body)


def stale(day, days=WEEKLY):
    return not day or day < (TODAY - timedelta(days=days)).isoformat()


def live(year):
    """A session still changing: from prefiling until July 1 of its year (the governor's 20 days, pocket vetoes)."""
    return year > TODAY.year or (year == TODAY.year and TODAY < date(year, 7, 1))


def folder_of(year):
    return f"/Sessions/{year % 100:02d}%20Regular/"


def pdf_text(body, layout=True):
    """A PDF's text (pdftotext), or None."""
    if not PDFTOTEXT or not body or not body.startswith(b"%PDF"):
        return None
    with tempfile.TemporaryDirectory() as tmp:
        src = os.path.join(tmp, "in.pdf")
        with open(src, "wb") as f:
            f.write(body)
        try:
            out = subprocess.run([PDFTOTEXT] + (["-layout"] if layout else []) + ["-enc", "UTF-8", src, "-"],
                                 capture_output=True, timeout=300)
        except Exception:
            return None
        return out.stdout.decode("utf-8", "replace") if out.returncode == 0 else None


def fir_part(body):
    """A fiscal impact report's header and SUMMARY section (to FISCAL IMPLICATIONS), as text."""
    full = pdf_text(body)
    if full is None:
        return None
    end = re.search(r"(?m)^\s*(FISCAL IMPLICATIONS|SIGNIFICANT ISSUES)\s*$", full)
    return full[:end.start()] if end else full


# ----------------------------------------------------------------------------------------------- sessions and lists

def sessions():
    """{"2025 Regular": 69, ...} from the legislation list's session menu; the last copy when it can't be read."""
    path = os.path.join(DATA, "sessions.json")
    page = request("/Legislation/Legislation_List", "sessions", must="Legislation_List")
    found = {}
    if isinstance(page, str):
        for value, name in re.findall(r'<option[^>]*value="(\d+)"[^>]*>([^<]+)</option>', page):
            found.setdefault(text(name), int(value))
        codes = sorted(set(re.findall(r"Standing_Committee\?CommitteeCode=([A-Z]+)", page)))
        if codes:
            save(codes, os.path.join(DATA, "committee_codes.json"))
    if any(n.endswith(" Regular") for n in found):
        save(found, path)
        return found
    print("sessions: unreadable; kept the last copy", flush=True)
    return load(path, {})


def years(found):
    """The regular sessions to read, newest first: two years back through this one, and next year's once listed."""
    out = [y for y in range(TODAY.year - 2, TODAY.year + 2) if f"{y} Regular" in found]
    if ONLY:
        out = [y for y in out if y == ONLY]
    return sorted(out, reverse=True)


def parse_list(page):
    """The legislation list's rows: {"HB5": {...}} (every type)."""
    out = {}
    for row in re.findall(r"<tr[^>]*>(.*?)</tr>", page, re.S):
        link = re.search(r'linkBillID_\d+" href="Legislation\?chamber=(\w)&amp;legType=(\w+)&amp;legNo=(\d+)&amp;year=(\d+)"',
                         row)
        if not link:
            continue
        chamber, kind, number = link.group(1), link.group(2), int(link.group(3))
        title = re.search(r'lblTitle_\d+">(.*?)</span>', row, re.S)
        actions = re.search(r'lblActions_\d+">(.*?)</span>', row, re.S)
        sponsors = [[code, text(name)] for code, name in
                    re.findall(r'linkSponsor\w+_\d+" href="[^"]*SponCode=(\w+)">(.*?)</a>', row, re.S)]
        out[f"{chamber}{kind}{number}"] = {
            "chamber": chamber, "type": kind, "number": number, "title": text(title.group(1)) if title else "",
            "sponsors": sponsors, "actions": text(actions.group(1)) if actions else ""}
    return out


def read_list(year, folder, found, state):
    """list.json for a session: each run while it's live, weekly otherwise. The rows read, or None."""
    path = os.path.join(folder, "list.json")
    old = load(path)
    if old and not live(year) and not stale(state.get("list_read")):
        return old
    sid = found[f"{year} Regular"]
    page = request(f"/Legislation/Legislation_List?Session={sid}", f"{year} list", must="Last legislative database update",
                   timeout=300)
    if not isinstance(page, str):
        print(f"{year} list: not read" + ("; kept the last copy" if old else ""), flush=True)
        return old
    stamp = re.search(r"Last legislative database update:\s*([^<]+)", page)
    bills = parse_list(page)
    if not bills and old and old.get("bills"):
        print(f"{year} list: no rows; kept the last copy", flush=True)
        return old
    out = {"session": sid, "stamp": text(stamp.group(1)) if stamp else None, "read": TODAY.isoformat(), "bills": bills}
    os.makedirs(folder, exist_ok=True)
    save(out, path)
    state["list_read"] = TODAY.isoformat()
    kinds = Counter(f"{b['chamber']}{b['type']}" for b in bills.values())
    print(f"{year} list: {len(bills)} ({', '.join(f'{k} {n}' for k, n in sorted(kinds.items()))}); "
          f"database updated {out['stamp']}", flush=True)
    return out


def wanted(listing):
    return {k: b for k, b in (listing or {}).get("bills", {}).items() if b["type"] in TYPES}


def row_sig(b):
    return hashlib.sha1(json.dumps([b["title"], b["sponsors"], b["actions"]]).encode()).hexdigest()[:16]


def bill_pages(year, folder, state, listing):
    """Each bill and joint resolution's page: when new, and when its list row changed."""
    bills = wanted(listing)
    os.makedirs(os.path.join(folder, "bills"), exist_ok=True)
    rows, absent = state.setdefault("rows", {}), state.setdefault("absent", {})
    new = [k for k in bills if not os.path.exists(os.path.join(folder, "bills", f"{k}.html")) and k not in absent]
    changed = [k for k in bills if k not in new and rows.get(k) != row_sig(bills[k])
               and (k not in absent or absent[k] != row_sig(bills[k]))]
    got = 0
    for k in new + changed:
        if out_of_time():
            break
        b = bills[k]
        page = request(f"/Legislation/Legislation?chamber={b['chamber']}&legType={b['type']}&legNo={b['number']}"
                       f"&year={year % 100:02d}", f"{year} {k}", must="formViewLegislationTitle")
        if page is GONE:
            absent[k] = row_sig(b)
            continue
        if not isinstance(page, str):
            continue
        save_text(trim(page), os.path.join(folder, "bills", f"{k}.html"))
        rows[k] = row_sig(b)
        absent.pop(k, None)
        got += 1
        if got % 50 == 0:
            save(state, os.path.join(folder, "state.json"))
    print(f"{year} bills: {got} read ({len(new)} new, {len(changed)} changed; {len(bills)} listed)", flush=True)


# ---------------------------------------------------------------------------------------------------- folder files

def listing(path, label):
    """A folder listing: {name: "date time size"}, GONE when the folder doesn't exist, None when it can't be read."""
    page = request(path, label, must="[To Parent Directory]")
    if page is GONE or page is None:
        return page
    out = {}
    for when, size, name in re.findall(r"(\d{1,2}/\d{1,2}/\d{4}\s+\d{1,2}:\d{2} [AP]M)\s+(\d+)\s+<A HREF=\"[^\"]+\">([^<]+)</A>",
                                       page):
        out[html.unescape(name)] = f"{' '.join(when.split())} {size}"
    return out


def changed_files(kind_key, entries, state, pattern, have):
    """Names in a listing that match pattern and are new or changed since they were read (have(name): saved?)."""
    seen = state.setdefault("listing", {}).setdefault(kind_key, {})
    return [n for n, e in sorted(entries.items()) if re.match(pattern, n) and not (have(n) and same(seen.get(n), e))]


def core_files(year, folder, state):
    """The session's database (LegInfo<yy>.zip) and members file, when their listing changed."""
    for key, sub, name, dest in (("database", "other/", f"LegInfo{year % 100:02d}.zip", f"LegInfo{year % 100:02d}.zip"),
                                 ("members", "Legislator%20Information/", "LegislatorsCommaDelimitedforMerging.txt",
                                  "members.txt")):
        if out_of_time():
            return
        if not (live(year) or stale(state.get("listed", {}).get(key)) or not os.path.exists(os.path.join(folder, dest))):
            continue
        entries = listing(folder_of(year) + sub, f"{year} {sub}")
        if entries is None:
            continue
        state.setdefault("listed", {})[key] = TODAY.isoformat()
        state.setdefault("present", {})[key] = entries is not GONE and name in entries
        if entries is GONE or name not in entries:
            continue
        seen = state.setdefault("listing", {}).setdefault(key, {})
        path = os.path.join(folder, dest)
        if os.path.exists(path) and same(seen.get(name), entries[name]):
            continue
        body = request(folder_of(year) + sub + urllib.parse.quote(name), f"{year} {name}", binary=True, timeout=300)
        if not isinstance(body, bytes) or (dest.endswith(".zip") and not body.startswith(b"PK")):
            print(f"{year} {name}: not read" + ("; kept the last copy" if os.path.exists(path) else ""), flush=True)
            continue
        save_bytes(body, path)
        seen[name] = entries[name]
        print(f"{year} {dest}: {len(body)} bytes", flush=True)


def extras(year, folder, state):
    """Votes, messages, committee reports and fiscal impact reports: files new or changed in their folders' listings."""
    counts = Counter()
    for kind, sub, pattern, how in EXTRAS:
        if out_of_time():
            break
        if how in ("pdf", "fir") and not PDFTOTEXT:
            counts[f"{kind} skipped (no pdftotext)"] += 1
            continue
        key = f"{kind}:{sub}"
        dest = os.path.join(folder, kind)
        listed = state.setdefault("listed", {})
        cached = state.setdefault("listings", {})
        if live(year) or stale(listed.get(key)) or key not in cached:
            entries = listing(folder_of(year) + sub, f"{year} {sub}")
            if entries is None:
                continue
            listed[key] = TODAY.isoformat()
            cached[key] = {} if entries is GONE else {n: e for n, e in entries.items() if re.match(pattern, n)}
        entries = cached[key]
        todo = changed_files(key, entries, state, pattern, lambda n: os.path.exists(os.path.join(dest, f"{n}.txt")))
        os.makedirs(dest, exist_ok=True)
        seen = state["listing"][key]
        done = 0
        for i, name in enumerate(todo):
            if out_of_time():
                break
            body = request(folder_of(year) + sub + urllib.parse.quote(name), f"{year} {name}", binary=True)
            if body is GONE:
                counts[f"{kind} gone"] += 1
                done += 1
                continue
            if not isinstance(body, bytes):
                continue
            done += 1
            if how == "html":
                try:
                    page = body.decode("utf-8")
                except UnicodeDecodeError:
                    page = body.decode("cp1252", "replace")
                out = page_text(page)
            elif how == "fir":
                out = fir_part(body)
            else:
                out = pdf_text(body)
            if out is None:  # not a readable PDF: saved empty, and not asked for again until its listing changes
                counts[f"{kind} unreadable"] += 1
                out = ""
            save_text(out, os.path.join(dest, f"{name}.txt"))
            seen[name] = entries[name]
            counts[kind] += 1
            if i % 50 == 49:
                save(state, os.path.join(folder, "state.json"))
        if len(todo) - done:
            counts[f"{kind} left"] += len(todo) - done
    if counts:
        print(f"{year} files: {', '.join(f'{k} {n}' for k, n in sorted(counts.items()))}", flush=True)


# ---------------------------------------------------------------------------------------- members and committees

def parse_member(page):
    def label(name):
        m = re.search(rf'id="MainContent_formViewLegislator_{name}"[^>]*>(.*?)</(?:span|a)>', page, re.S)
        return text(m.group(1)) if m else ""
    head = re.search(r'lblLegislatorName">(.*?)</span>(.*?)</td>', page, re.S)
    name = text(head.group(1)) if head else ""
    party = re.search(r"- \((\w+)\)\s*$", name)
    post = text(head.group(2)).strip(" -") if head else ""
    committees = [[c, text(n)] for c, n in re.findall(
        r'gridViewStandingCommittees_linkCommittee_\d+" href="[^"]*CommitteeCode=(\w+)">(.*?)</a>', page, re.S)]
    name = re.sub(r"\s*- \(\w+\)\s*$", "", name)
    title = re.match(r"(Representative|Senator)\s+", name)
    return {"title": title.group(1) if title else "", "name": name[title.end():] if title else name,
            "party": party.group(1) if party else None, "post": post,
            "district": label("linkDistrict"), "county": label("lblCounty"), "since": label("lblStartYear"),
            "capitol_phone": label("Label2"), "room": label("Label3"), "address": label("lblAddress"),
            "email": label("linkEmail"), "phone": label("lblPhone1"), "phone2": label("lblPhone2"),
            "committees": committees}


def members(lists):
    """The current members' lists, then each member's page: current members weekly, other sponsors once."""
    os.makedirs(MEMBERS, exist_ok=True)
    seen = load(os.path.join(MEMBERS, "read.json"), {})
    current = {}
    for house, t in (("house", "R"), ("senate", "S")):
        path = os.path.join(MEMBERS, f"{house}.html")
        if os.path.exists(path) and not stale(seen.get(house), 1):
            page = open(path, encoding="utf-8").read()
        else:
            got = request(f"/Members/Legislator_List?T={t}", f"{house} members", must="listViewLegislators")
            if isinstance(got, str):
                page = trim(got)
                save_text(page, path)
                seen[house] = TODAY.isoformat()
            elif os.path.exists(path):
                page = open(path, encoding="utf-8").read()
            else:
                continue
        for code in re.findall(r"Legislator\?SponCode=(\w+)", page):
            current[code] = house
    others = {code for listing in lists for b in listing.get("bills", {}).values() for code, _ in b["sponsors"]}
    todo = [c for c in sorted(set(current) | others)
            if not (seen.get(c, {}) or {}).get("gone")
            and (not os.path.exists(os.path.join(MEMBERS, f"{c}.html"))
                 or (c in current and stale((seen.get(c) or {}).get("read"))))]
    got = 0
    for code in todo:
        if out_of_time():
            break
        page = request(f"/Members/Legislator?SponCode={code}", f"member {code}", must="formViewLegislator")
        if page is GONE:
            seen[code] = {"gone": TODAY.isoformat()}
            continue
        if not isinstance(page, str):
            continue
        save_text(trim(page), os.path.join(MEMBERS, f"{code}.html"))
        seen[code] = {"read": TODAY.isoformat()}
        got += 1
    save(seen, os.path.join(MEMBERS, "read.json"))
    out = []
    for name in sorted(os.listdir(MEMBERS)):
        code = name[:-5]
        if name.endswith(".html") and code not in ("house", "senate"):
            m = parse_member(open(os.path.join(MEMBERS, name), encoding="utf-8").read())
            out.append({"code": code, "house": "S" if code.startswith("S") else "H", "current": code in current, **m})
    save(out, os.path.join(DATA, "members.json"))
    print(f"members: {len(current)} current; {got} of {len(todo)} pages read ({len(out)} saved)", flush=True)


def parse_committee(page):
    name = re.search(r'lblCommitteeName">(.*?)</span>', page, re.S)
    when = re.search(r'lblMeetingDate">(.*?)</span>', page, re.S)
    people = []
    for row in re.findall(r"<tr[^>]*>(.*?)</tr>", page, re.S):
        link = re.search(r'gridViewCommitteeMembers_linkLegislator_\d+" href="[^"]*SponCode=(\w+)">(.*?)</a>', row, re.S)
        if link:
            cells = [text(c) for c in re.findall(r"<td[^>]*>(.*?)</td>", row, re.S)]
            people.append({"code": link.group(1), "name": text(link.group(2)), "district": cells[2] if len(cells) > 2 else "",
                           "party": cells[3] if len(cells) > 3 else "", "role": cells[4] if len(cells) > 4 else ""})
    return {"name": text(name.group(1)) if name else "", "meets": text(when.group(1)) if when else "", "members": people}


def committees():
    """Each standing committee's page (codes from the site's menu), weekly; the leadership and abbreviations pages."""
    os.makedirs(COMMITTEES, exist_ok=True)
    seen = load(os.path.join(COMMITTEES, "read.json"), {})
    for name, path, must in (("leadership", "/Members/Leadership", "MainContent"),
                             ("abbreviations", "/Legislation/Action_Abbreviations", "MainContent")):
        dest = os.path.join(DATA, f"{name}.html")
        if os.path.exists(dest) and not stale(seen.get(name)) or out_of_time():
            continue
        page = request(path, name, must=must)
        if isinstance(page, str):
            save_text(trim(page), dest)
            seen[name] = TODAY.isoformat()
    codes = load(os.path.join(DATA, "committee_codes.json"), [])
    got = 0
    for code in codes:
        dest = os.path.join(COMMITTEES, f"{code}.html")
        if out_of_time() or (os.path.exists(dest) and not stale(seen.get(code))):
            continue
        page = request(f"/Committee/Standing_Committee?CommitteeCode={code}", f"committee {code}",
                       must="formViewCommitteeInformation")
        if isinstance(page, str):
            save_text(trim(page), dest)
            seen[code] = TODAY.isoformat()
            got += 1
    save(seen, os.path.join(COMMITTEES, "read.json"))
    out = []
    for code in codes:
        dest = os.path.join(COMMITTEES, f"{code}.html")
        if os.path.exists(dest):
            out.append({"code": code, "house": code[0], **parse_committee(open(dest, encoding="utf-8").read())})
    save(out, os.path.join(DATA, "committees.json"))
    print(f"committees: {got} read, {len(out)} saved", flush=True)


# ---------------------------------------------------------------------------------------------------------- main

def begun(year):
    """Whether a year's session has convened (the third Tuesday of January)."""
    return TODAY >= date(year, 1, 1 + (1 - date(year, 1, 1).weekday()) % 7 + 14)


def never_downloaded(yrs, found):
    """What was never downloaded (a failed re-read with a last copy, or a 404, doesn't count)."""
    gaps = [] if found else ["sessions"]
    for year in yrs:
        if not begun(year):
            continue  # next year's prefiled bills are read when listed, but don't hold New Mexico back
        folder = os.path.join(DATA, str(year))
        listing = load(os.path.join(folder, "list.json"))
        if not listing:
            gaps.append(f"{year}:list")
            continue
        state = load(os.path.join(folder, "state.json"), {})
        absent = state.get("absent") or {}
        missing = [k for k in wanted(listing) if k not in absent
                   and not os.path.exists(os.path.join(folder, "bills", f"{k}.html"))]
        if missing:
            gaps.append(f"{year}:bills({len(missing)})")
        present = state.get("present") or {}
        if present.get("database", True) and not os.path.exists(os.path.join(folder, f"LegInfo{year % 100:02d}.zip")):
            gaps.append(f"{year}:database")
        if present.get("members", True) and not os.path.exists(os.path.join(folder, "members.txt")):
            gaps.append(f"{year}:members")
    for house in ("house", "senate"):
        if not os.path.exists(os.path.join(MEMBERS, f"{house}.html")):
            gaps.append(f"members:{house}")
    return gaps


def main():
    os.makedirs(DATA, exist_ok=True)
    # Before the first copy, a run cut off without its summary leaves this, so a partial copy isn't published.
    if not ONLY and not any(name.isdigit() for name in os.listdir(DATA)):
        with open(MARKER, "w") as f:
            f.write("running\n")
    refused = False
    found, yrs, lists = {}, [], []
    try:
        found = sessions()
        yrs = years(found)
        # The core first, newest session first: lists, bill pages, database and members files.
        for year in yrs:
            if out_of_time():
                break
            folder = os.path.join(DATA, str(year))
            os.makedirs(folder, exist_ok=True)
            state = load(os.path.join(folder, "state.json"), {})
            listing = read_list(year, folder, found, state)
            if listing:
                lists.append(listing)
                bill_pages(year, folder, state, listing)
            core_files(year, folder, state)
            save(state, os.path.join(folder, "state.json"))
        if not out_of_time():
            members(lists)
            committees()
        # Then what fills in over later runs: votes, messages, committee and fiscal impact reports.
        for year in yrs:
            if out_of_time():
                break
            folder = os.path.join(DATA, str(year))
            state = load(os.path.join(folder, "state.json"), {})
            extras(year, folder, state)
            save(state, os.path.join(folder, "state.json"))
    except Refused as e:
        print(f"Stopped: the server refused a request ({e})", flush=True)
        refused = True
    gaps = never_downloaded(yrs, found)
    sizes = []
    for year in yrs:
        folder = os.path.join(DATA, str(year))
        n = len(wanted(load(os.path.join(folder, "list.json"), {})))
        files = {k: len(os.listdir(os.path.join(folder, k))) for k in ("bills", "votes", "reports", "firs", "messages")
                 if os.path.isdir(os.path.join(folder, k))}
        sizes.append(f"{year} {n} listed, " + ", ".join(f"{k} {v}" for k, v in files.items()))
    print(f"run: {STATS['requests']} requests, {round((time.time() - START) / 60, 1)} min"
          + (f"; {'; '.join(sizes)}" if sizes else "")
          + ("; stopped at the time limit" if out_of_time() else "")
          + ("; refused" if refused else "")
          + ("" if PDFTOTEXT else "; no pdftotext (PDFs skipped)")
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
