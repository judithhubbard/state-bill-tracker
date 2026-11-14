#!/usr/bin/env python3
"""Download New Hampshire's bills from the General Court's "Dynamic Data Files" (https://gc.nh.gov/dynamicdatadump/,
linked from https://gc.nh.gov/downloads/ as "Current Data Tables - data refreshes on file access") and its member file
(https://gc.nh.gov/downloads/Members.txt). gc.nh.gov's robots.txt bars only AhrefsBot and asks every agent for
"Crawl-delay: 11": it is read at the start of each run and obeyed (nothing is fetched that it disallows, and requests
are at least its crawl delay apart, never less than a second). One request at a time.

The data files are pipe-delimited, UTF-8 with a byte-order mark, CRLF line ends, no header row, generated when they're
asked for (Last-Modified is always "now", so there's nothing to check before downloading). They hold the CURRENT
SESSION YEAR only (in 2026: session year 2026, whose bills include the 225 bills of 2025 retained in committee and
carried over), except the Docket, which holds both years of the biennium. There is no archive: a year that leaves the
files is gone from this source. So each file is split by session year and kept as data/nh/<first year>/<Name>_<year>.txt
(2025 and 2026 both go in data/nh/2025/); a year no longer in the files keeps its last copy for good.

The years the files had already dropped (2023, 2024, and 2025's bills finished in 2025) come from the Legislature's
public read-only SQL Server, chosen by the owner 2026-11-08. Its address, database and published login are in the
Legislature's own document, https://gc.nh.gov/downloads/ODBC%20and%20Data%20Table%20Structure.pdf, which is downloaded
(robots.txt allowing, at the crawl delay) and read with pypdf only on runs that need the server, so the login is never
written into this repository, saved or printed. Needs `pip install pymssql pypdf` (pymssql has no wheel for Python 3.14
on an Intel Mac: 3.12 with pymssql 2.3.10 works); without them the daily files are still read. The server's tables are
views (dbo.*): Legislation and Docket (the current biennium, 2025-26), PastLegislation and PastDocket (2024 and before),
Sponsors (with PersonID) and PastSponsors (employee numbers only), RollCallSummary and RollCallHistory (every year; the
vote as a code: 1 Yea, 2 Nay, 3 Not Voting/Excused, 4 Not Voting/Not Excused, 6 Presiding), Legislators (every member
since about 2015, Active or not, with both PersonID and employee number) and CommitteeMembers (current committees: each
member's employee number and "Chairman", "V Chairman" or "Clerk"). For each session year from two years before this
biennium through last year whose files are missing, it writes LSRs, Docket, LsrSponsors, RollCallSummary and
RollCallHistory in the daily files' shapes (each file once: a finished year is never read again), with small queries a
second apart (one per table and year; members' votes a hundred roll calls a query): about 75 queries, a few minutes.
Built from the server for 2026, the five files matched the daily ones row for row except: LSRs column 24 (the Senate
status code: the server says 05 where the daily file says 12 or 13 for 29 bills), the Docket's last column (its edit
time isn't on the server; PastDocket's OrderDate is used, and for the current Docket view it's empty), and LSRs
columns 20 and 28 (the server's House and Senate "amended" flags; the daily file always writes 0, so 0 is written).
LsrSponsors keeps only signed-off sponsors who didn't withdraw, as the daily file does. There is no LsrsOnly file for
those years (LsrSponsors and legislators.txt hold the same). The server's LSRs include requests that never became
bills (no bill number, no Docket: 116 in 2023, 84 in 2024; the daily file lists only numbered ones), and kinds the
2026 file doesn't have (7, 14, 16). Three employee numbers (376628, 377080, 409060) vote in every 2023-24 House roll call
and have no Legislators row, so those votes have no PersonID (about 0.7%). Also from the server: legislators.txt for a past biennium
(everyone in its sponsor and roll-call files, from Legislators: their latest details, not necessarily those of then),
and, weekly, the current biennium's former_legislators.txt (members in its files who are no longer sitting) and
CommitteeMembers.txt (committee code, order, employee number, PersonID, active 1/0, role: the only source of chairs).

Files kept (columns by position; the PDF above names most of them):
- LSRs_<year>.txt (39 columns): every LSR (legislative service request: a bill or resolution, with or without a number
  yet) of the session year. 0 session year, 1 LSR number ("0010"; with 0 the key the Docket and sponsor files use),
  2 title ("(New Title) ..." when amended; one has a non-breaking space), 3 house of origin (H/S), 4 kind (1 HB, 2 SB,
  3 or 13 CACR, 4 HR, 5 HCR; CACRs, proposed constitutional amendments, are the only joint resolutions), 5-7 flags (not
  documented), 8 LSR as "25-0010" (its first year), 9 bill number padded ("HB  0054"), 10 the same condensed ("HB54"),
  11 chapter number ("0157", padded; a law), 12 subject code (SubjectCodes), 13/14 House committee (first and
  current), 15 House referral date, 16 House status code (BodyStatusCodes), 17 empty, 18 House status date, 19 a later
  date (not documented), 20 0, 21-27 the same for the Senate (25 a date as "04/09/2026", 26 empty), 28 0, 29 general
  status code (GeneralCodes: 05 signed, 06 law without signature, 07 vetoed, 09 veto overridden ...), 30-32 the next
  hearing's committee, date and time, and room, 33-38 empty or 0. Dates are "1/7/2026 12:00:00 AM".
- Docket_<year>.txt (7): each bill's history. 0 session year, 1 LSR number, 2 the entry's time, 3 bill number
  (condensed), 4 house (H/S), 5 the history line as written ("Ought to Pass: MA RC 358-14 03/06/2025  HJ 7  P. 40",
  "Committee Report: Ought to Pass  02/12/2025 (Vote 18-0; RC)", "Retained in Committee"; with leading spaces and
  double spaces), 6 when it was last edited. A retained bill's 2025 lines are under session year 2026.
- LsrSponsors_<year>.txt (5): 0 session year, 1 LSR number, 2 order (1 first), 3 PersonID (legislators' column 0; a
  few are former members), 4 prime sponsor (1/0). The retained bills' LSR numbers are written unpadded here ("10",
  not "0010" as in LSRs and the Docket): join on the number as an integer.
- LsrsOnly_<year>.txt (8): sponsors again, with names joined in: 0 LSR as "26-2001", 1 PersonID, 2 legislation id,
  3 session year, 4 "Prime" or "Sponsor", 5 bill number, 6 the sponsor's house, 7 title. Only the session year's own
  LSRs ("26-"): the retained bills' sponsors are only in LsrSponsors. A few titles have line breaks, and blank lines,
  inside them (CACR 14's second sentence): records are rejoined by their column count, the break made a space.
- RollCallSummary_<year>.txt (15): floor roll calls only. 0 session year, 1 house, 2 the house's vote number (the key,
  with 0-1), 3 time, 4 bill number (empty for procedural votes), 5 yeas, 6 nays, 7 present (House) or not voting,
  8 absent, 9-10 short titles (empty), 11 question ("OTPA", "ITL", "Concur", "Veto Override", "Adopt CofC Report"),
  12-13 title, 14 (Senate) a time. Every yea and nay count matched RollCallHistory (2026-11-08).
- RollCallHistory_<year>.txt (8): each member's vote. 0 session year, 1 house, 2 vote number, 3 employee number (not in
  legislators.txt), 4 PersonID (about 3% are former members not in legislators.txt), 5 bill number (mostly empty),
  6 "Yea", "Nay", "Not Voting/Excused", "Not Voting/Not Excused" or "Presiding", 7 (Senate) the vote's time.
There are no committee roll calls (a committee's tally is in its Docket report line, "Vote 18-0") and no summaries of
what a bill does (only titles).
Kept per biennium, in the current biennium's folder (a new General Court is organized in December of an even year, so
from December 1 these go to the next biennium's folder and the last one keeps its copy):
- legislators.txt (15): 0 PersonID, 1-3 last, first, middle name, 4 house, 5 seat number, 6 county code, 7 district,
  8 party ("R", "D", "I"; one "r"), 9-13 address, 14 email. No phones. About 400 rows: all current members.
  Senators have no seat number (join them by district).
- Members.txt (from /downloads/, tab-delimited with a header row, Windows-1252, re-saved as UTF-8; updated now and then,
  so read only when its Last-Modified changes): names, house, seat, county, district, electedStatus ("Former" for a
  few), address (ZIP codes lose their leading zero: "3301"), phone, email, party, gender, title and up to five
  committees by name with each one's phone (142 of 408 members have no phone of their own). No PersonID: it joins
  legislators.txt by house and seat number (House) or district (Senate).
- Committees.txt (code "H05", name, abbreviation), BodyStatusCodes.txt, GeneralCodes.txt (their codes overlap: "03" is
  IN APPROPRIATION/FINANCE in one and SENATE in the other), SubjectCodes.txt, Counties.txt (code, name, abbreviation),
  HouseDistricts.txt (county code, district, ward, town; the House's districts by town; there is no Senate file).
Codes written two ways: bill numbers "HB  0054" and "HB54"; LSRs "25-0010" and year 2026 + "0010"; chapters padded.
A download that fails, is refused, isn't text, or has fewer than half the rows of the last copy keeps the last copy.
data/nh/incomplete says "running" during a run, and after it lists files never downloaded (the daily files' and the
SQL Server's); it is removed when every file has a copy. A run is about 15 requests at the crawl delay: about 3
minutes, the same every day, plus the SQL Server once a week (and on a run that has a past year to fill in).
Also each bill's "What it does" (the Office of Legislative Services' analysis in its text: see analyses() below), into
data/nh/texts_<year>.json; never part of "incomplete".
Usage: python3 states/nh/fetch.py [--texts-only] [--max-requests=N]  (the options are for testing)
"""
import functools, gzip, json, os, re, sys, time, urllib.error, urllib.request, urllib.robotparser
from collections import Counter
from datetime import date, datetime, timedelta

SITE = "https://gc.nh.gov"
DATA = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "nh"))
AGENT = "statebilltracker.org (a nonprofit bill tracker; contact via github.com/judithhubbard)"
TODAY = date.today()
# Files with a session year in each row: {name: (columns, the session year's column)}.
BY_YEAR = {"LSRs": (39, 0), "Docket": (7, 0), "LsrSponsors": (5, 0), "LsrsOnly": (8, 3),
           "RollCallSummary": (15, 0), "RollCallHistory": (8, 0)}
# Files kept per biennium: {name: columns}.
PER_TERM = {"legislators": 15, "Committees": 3, "BodyStatusCodes": 2, "GeneralCodes": 2, "SubjectCodes": 3,
            "Counties": 3, "HouseDistricts": 4}
MARKER = os.path.join(DATA, "incomplete")

# The run's own time limit (FETCH_MINUTES, set by the workflow): stop a few minutes early, with everything read so far
# saved and a summary printed, rather than be cut off silently mid-request.
START = time.time()
BUDGET = max(0.0, float(os.environ.get("FETCH_MINUTES") or 0) - 5) * 60
FAILS = Counter()  # why requests failed, for the summary
STATS = {"requests": 0, "pause": 11.0, "last": 0.0}


class Refused(Exception):
    """The server turned us away (401/403/429): stop the run."""


def out_of_time():
    return BUDGET and time.time() - START > BUDGET


def first_year(year):
    """The biennium a session year belongs to: 2025 and 2026 -> 2025."""
    return year if year % 2 else year - 1


def term_now():
    """The current biennium's first year; from December 1 of an even year, the new General Court's."""
    if TODAY.year % 2 == 0 and TODAY.month == 12:
        return TODAY.year + 1
    return first_year(TODAY.year)


def request(url, label, headers=None):
    """GET url, at least the crawl delay after the last request; (body, response headers), or (None, None) after three
    tries. Refused on 401/403/429; a 404 is None at once; a 304 is (b"", headers)."""
    for attempt in range(3):
        if out_of_time():
            return None, None
        wait = STATS["last"] + STATS["pause"] - time.time()
        if wait > 0:
            time.sleep(wait)
        STATS["requests"] += 1
        try:
            req = urllib.request.Request(url, headers={"User-Agent": AGENT, "Accept-Encoding": "gzip", **(headers or {})})
            with urllib.request.urlopen(req, timeout=180) as r:
                body = r.read()
                if r.headers.get("Content-Encoding") == "gzip":
                    body = gzip.decompress(body)
                return body, r.headers
        except urllib.error.HTTPError as e:
            if e.code == 304:
                return b"", e.headers
            FAILS[f"HTTP {e.code}"] += 1
            if e.code in (401, 403, 429):
                raise Refused(f"{label}: HTTP {e.code}")
            if e.code == 404:
                print(f"{label}: not found", flush=True)
                return None, None
        except Exception as e:
            FAILS[type(e).__name__] += 1
        finally:
            STATS["last"] = time.time()
        time.sleep(10 * (attempt + 1))
    print(f"{label}: failed three times", flush=True)
    return None, None


def robots():
    """Read robots.txt; a parser that says what we may fetch, or None if it can't be read (then nothing is fetched)."""
    body, _ = request(f"{SITE}/robots.txt", "robots.txt")
    if body is None:
        return None
    rp = urllib.robotparser.RobotFileParser()
    rp.parse(body.decode("utf-8-sig", "replace").splitlines())
    delay = rp.crawl_delay(AGENT)
    if delay is not None:  # without one, keep the 11 seconds last asked for
        STATS["pause"] = max(1.0, float(delay))
    print(f"robots.txt: crawl delay {STATS['pause']:g} s", flush=True)
    return rp


def records(text, columns, name):
    """The rows of a pipe-delimited file, a record cut by a line break inside a field joined back up (the break made a
    space). Returns (rows, how many rows still have the wrong column count)."""
    rows, bad, cur = [], 0, None
    for line in text.split("\r\n") if "\r\n" in text else text.split("\n"):
        if cur is None and not line.strip():
            continue  # a blank line (inside a title, or the file's end)
        if cur is None and rows and "|" not in line and columns > 1:
            rows[-1] += " " + line  # a break inside the last field (LsrsOnly's titles)
            continue
        cur = line if cur is None else cur + " " + line
        if cur.count("|") + 1 < columns:
            continue
        if cur.count("|") + 1 != columns:
            bad += 1
        rows.append(cur)
        cur = None
    if cur and cur.strip():
        rows.append(cur)
        bad += 1
    if bad:
        print(f"{name}: {bad} rows without {columns} columns", flush=True)
    return rows, bad


def lines_in(path):
    try:
        with open(path, encoding="utf-8") as f:
            return sum(1 for _ in f)
    except OSError:
        return 0


def write(path, rows):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        f.write("".join(r + "\n" for r in rows))
    os.replace(tmp, path)


def text_of(body, label):
    """The file's text, or None when the answer isn't one of these files (an error page)."""
    text = body.decode("utf-8-sig", "replace")
    if text.lstrip().startswith("<"):
        FAILS["not a data file"] += 1
        print(f"{label}: answered a web page, not the file; kept the last copy", flush=True)
        return None
    return text


def enough(path, rows, label):
    """False (keep the last copy) when rows is fewer than half the last copy's."""
    before = lines_in(path)
    if before > 20 and len(rows) < before / 2:
        FAILS["shrank"] += 1
        print(f"{label}: {len(rows)} rows, the last copy {before}; kept the last copy", flush=True)
        return False
    return True


def by_year(rp, name, columns, col):
    """A file with a session year in each row, split by year into each year's biennium folder."""
    url = f"{SITE}/dynamicdatadump/{name}.txt"
    if not rp.can_fetch(AGENT, url):
        print(f"{name}: robots.txt disallows it; not read", flush=True)
        return
    body, _ = request(url, name)
    if body is None:
        return
    text = text_of(body, name)
    if text is None:
        return
    rows, bad = records(text, columns, name)
    years = {}
    for r in rows:
        y = r.split("|")[col] if r.count("|") >= col else ""
        if y.isdigit():
            years.setdefault(int(y), []).append(r)
    for year, part in sorted(years.items()):
        folder = os.path.join(DATA, str(first_year(year)))
        os.makedirs(folder, exist_ok=True)
        path = os.path.join(folder, f"{name}_{year}.txt")
        if enough(path, part, f"{name} {year}"):
            write(path, part)
    print(f"{name}: " + ", ".join(f"{y} {len(p)} rows" for y, p in sorted(years.items())), flush=True)


def per_term(rp, name, columns, folder):
    url = f"{SITE}/dynamicdatadump/{name}.txt"
    if not rp.can_fetch(AGENT, url):
        print(f"{name}: robots.txt disallows it; not read", flush=True)
        return
    body, _ = request(url, name)
    if body is None:
        return
    text = text_of(body, name)
    if text is None:
        return
    rows, bad = records(text, columns, name)
    path = os.path.join(folder, f"{name}.txt")
    if rows and enough(path, rows, name):
        write(path, rows)
        print(f"{name}: {len(rows)} rows", flush=True)


def members(rp, folder):
    """/downloads/Members.txt (phones and committees), only when its Last-Modified has changed."""
    url = f"{SITE}/downloads/Members.txt"
    if not rp.can_fetch(AGENT, url):
        print("Members.txt: robots.txt disallows it; not read", flush=True)
        return
    path = os.path.join(folder, "Members.txt")
    seen_path = os.path.join(folder, "members_modified.json")
    try:
        seen = json.load(open(seen_path))
    except (OSError, ValueError):
        seen = {}
    headers = {"If-Modified-Since": seen["modified"]} if seen.get("modified") and os.path.exists(path) else {}
    body, got = request(url, "Members.txt", headers)
    if body is None:
        return
    if body == b"" and headers:
        print("Members.txt: unchanged", flush=True)
        return
    try:
        text = body.decode("utf-8-sig")  # UTF-8 first; in 2026 it was Windows-1252 ("Riché", an en dash)
    except UnicodeDecodeError:
        text = body.decode("cp1252", "replace")
    if text.lstrip().startswith("<") or not text.startswith("LastName\t"):
        FAILS["not a data file"] += 1
        print("Members.txt: not the member file; kept the last copy", flush=True)
        return
    rows = [r for r in text.replace("\r\n", "\n").split("\n") if r.strip()]
    if enough(path, rows, "Members.txt"):
        write(path, rows)
        with open(seen_path, "w") as f:
            json.dump({"modified": got.get("Last-Modified") or ""}, f)
        print(f"Members.txt: {len(rows) - 1} members", flush=True)


# The Legislature's public SQL Server: the years the daily files no longer hold. Its address and its published
# read-only login are read from the Legislature's own document at run time (never stored or printed).
SQL_DOC = f"{SITE}/downloads/ODBC%20and%20Data%20Table%20Structure.pdf"
SQL_NAMES = ("LSRs", "Docket", "LsrSponsors", "RollCallSummary", "RollCallHistory")  # not LsrsOnly
VOTES = {1: "Yea", 2: "Nay", 3: "Not Voting/Excused", 4: "Not Voting/Not Excused", 6: "Presiding", 0: ""}
WEEKLY_DAYS = 7


def history_years():
    """The session years the SQL Server fills in: the previous biennium's and this biennium's past years."""
    return list(range(first_year(TODAY.year) - 2, TODAY.year))


def sql_login(rp):
    """{server, user, password, database} from the Legislature's document, or None."""
    if not rp.can_fetch(AGENT, SQL_DOC):
        print("SQL Server document: robots.txt disallows it; not read", flush=True)
        return None
    body, _ = request(SQL_DOC, "SQL Server document")
    if not body or not body.startswith(b"%PDF"):
        print("SQL Server document: not read", flush=True)
        return None
    import io, pypdf
    text = " ".join(page.extract_text() or "" for page in pypdf.PdfReader(io.BytesIO(body)).pages)
    found = {k: re.search(pattern, text) for k, pattern in (
        ("server", r"SQL Server:\s*([\w.-]+)"), ("user", r"Username:\s*(\S+)"), ("password", r"Password:\s*(\S+)"),
        ("database", r"default database is\s*(\w+)"))}
    if not all(found.values()):
        print("SQL Server document: no " + ", ".join(k for k, m in found.items() if not m) + " in it", flush=True)
        return None
    return {k: m.group(1) for k, m in found.items()}


class Sql:
    """One connection; small queries a second apart, rows as dicts with lower-case keys."""

    def __init__(self, login):
        import pymssql
        self.secret = login["password"]
        self.conn = pymssql.connect(server=login["server"], user=login["user"], password=login["password"],
                                    database=login["database"], login_timeout=30, timeout=600)
        self.queries = 0

    def rows(self, query, params=()):
        time.sleep(1)
        self.queries += 1
        cur = self.conn.cursor(as_dict=True)
        cur.execute(query, params)
        return [{k.strip().lower(): v for k, v in r.items()} for r in cur.fetchall()]

    def scrub(self, e):
        return str(e).replace(self.secret, "***")


def fmt(v):
    """A value as the daily files write it: "1/7/2026 10:15:33 AM", 1/0 for flags, "" for none; line breaks inside
    text dropped, as the daily LSRs file drops them ("municipal" CRLF "board" -> "municipalboard"), and "|" (the files'
    delimiter) made "/"."""
    if v is None:
        return ""
    if isinstance(v, bool):
        return "1" if v else "0"
    if isinstance(v, datetime):
        return f"{v.month}/{v.day}/{v.year} {v.hour % 12 or 12}:{v.minute:02d}:{v.second:02d} {'AM' if v.hour < 12 else 'PM'}"
    return str(v).replace("\r", "").replace("\n", "").replace("|", "/")


def pad4(v):
    v = fmt(v).strip()
    return v.zfill(4) if v.isdigit() else v


def unpad(v):
    v = fmt(v).strip()
    return (v.lstrip("0") or "0") if v.isdigit() else v


def legislator_row(r):
    """A Legislators row as legislators.txt has it."""
    return "|".join([fmt(r["personid"]), fmt(r["lastname"]), fmt(r["firstname"]), fmt(r["middlename"]),
                     fmt(r["legislativebody"]), fmt(r["seatno"]), unpad(r["countycode"]), unpad(r["district"]),
                     fmt(r["party"]), fmt(r["address"]), fmt(r["address2"]), fmt(r["city"]), fmt(r["expr2"]),
                     fmt(r["zipcode"]), fmt(r["emailaddress"])])


def lsr_row(r):
    """A Legislation or PastLegislation row as LSRs.txt has it (the columns the daily file leaves empty or 0 too)."""
    senate_date = r["senatestatusdate"]
    if isinstance(senate_date, datetime):  # text in Legislation ("04/09/2026"), a date in PastLegislation
        senate_date = senate_date.strftime("%m/%d/%Y")
    return "|".join([fmt(r["sessionyear"]), pad4(r["lsr"]), fmt(r["lsrtitle"]), fmt(r["legislativebody"]),
                     fmt(r["billtype"]), fmt(r["appropriationcode"]), fmt(r["fiscalimpactcode"]), fmt(r["localcode"]),
                     fmt(r["fulllsr"]), fmt(r["expandedbillno"]), fmt(r["condensedbillno"]), pad4(r["chapterno"]),
                     fmt(r["subjectcode"]), fmt(r["housecommitteereferralcode"]), fmt(r["housecurrentcommitteecode"]),
                     fmt(r["housedateintroduced"]), fmt(r["housestatuscode"]), "", fmt(r["houseduedate"]),
                     fmt(r["housefloordate"]), "0",fmt(r["senatecommitteereferralcode"]),
                     fmt(r["senatecurrentcommitteecode"]), fmt(r["senatedateintroduced"]), fmt(r["senatestatuscode"]),
                     fmt(senate_date), "", fmt(r["senatefloordate"]), "0",
                     fmt(r["generalstatuscode"]), fmt(r["latestcommitteehearingcode"]),
                     fmt(r["latestcommitteehearingdate"]), fmt(r["latestcommitteehearingplace"]), "", "", "", "0", "0", ""])


def sql_year(db, year, people):
    """One session year's five files from the SQL Server, each written only if missing (a finished year is read
    once). people: {employee number: Legislators row}. Returns the files written."""
    folder = os.path.join(DATA, str(first_year(year)))
    os.makedirs(folder, exist_ok=True)
    path = lambda name: os.path.join(folder, f"{name}_{year}.txt")
    current = db.rows("SELECT COUNT(*) AS n FROM dbo.Legislation WHERE sessionyear = %s", (year,))[0]["n"] > 0
    written = []
    if not os.path.exists(path("LSRs")):
        view = "dbo.Legislation WHERE sessionyear = %s" if current else "dbo.PastLegislation WHERE SessionYear = %s"
        rows = db.rows(f"SELECT * FROM {view} ORDER BY CondensedBillNo", (year,))
        if rows:
            write(path("LSRs"), [lsr_row(r) for r in rows])
            written.append(f"LSRs {len(rows)}")
    if not os.path.exists(path("Docket")):
        view = "dbo.Docket" if current else "dbo.PastDocket"
        rows = db.rows(f"SELECT SessionYear, LSR, StatusDate, CondensedBillNo, LegislativeBody, Description, OrderDate "
                       f"FROM {view} WHERE SessionYear = %s ORDER BY LSR, StatusDate, statusorder", (year,))
        if rows:  # OrderDate stands in for the daily file's last column (its Docket's is 1900 or 2200: left empty)
            write(path("Docket"), ["|".join([fmt(r["sessionyear"]), pad4(r["lsr"]), fmt(r["statusdate"]),
                                             fmt(r["condensedbillno"]), fmt(r["legislativebody"]), fmt(r["description"]),
                                             fmt(r["orderdate"]) if 1950 < (r["orderdate"] or datetime.min).year < 2100
                                             else ""]) for r in rows])
            written.append(f"Docket {len(rows)}")
    if not os.path.exists(path("LsrSponsors")):
        view = "dbo.Sponsors" if current else "dbo.PastSponsors"
        rows = db.rows(f"SELECT * FROM {view} WHERE SessionYear = %s AND SignedOff = 1 "
                       f"AND (SponsorWithdrawn = 0 OR SponsorWithdrawn IS NULL) ORDER BY lsr, LSRSequenceNo", (year,))
        if rows:
            out = []
            for r in rows:
                person = r.get("personid") or (people.get(fmt(r["employeeno"]).strip()) or {}).get("personid")
                out.append("|".join([fmt(r["sessionyear"]), fmt(r["lsr"]), fmt(r["lsrsequenceno"]), fmt(person),
                                     fmt(r["primesponsor"])]))
            write(path("LsrSponsors"), out)
            written.append(f"LsrSponsors {len(rows)}")
    summary = db.rows("SELECT * FROM dbo.RollCallSummary WHERE SessionYear = %s "
                      "ORDER BY LegislativeBody, VoteSequenceNumber", (year,))
    if summary and not os.path.exists(path("RollCallHistory")):
        out, unknown = [], Counter()
        for house in ("H", "S"):
            last = max((r["votesequencenumber"] for r in summary if r["legislativebody"] == house), default=0)
            for low in range(1, last + 1, 100):  # a hundred roll calls a query
                for r in db.rows("SELECT EmployeeNumber, SessionYear, LegislativeBody, VoteSequenceNumber, "
                                 "CondensedBillNo, Vote, DateModified FROM dbo.RollCallHistory WHERE SessionYear = %s "
                                 "AND LegislativeBody = %s AND VoteSequenceNumber BETWEEN %s AND %s "
                                 "ORDER BY VoteSequenceNumber, EmployeeNumber", (year, house, low, low + 99)):
                    emp = fmt(r["employeenumber"]).strip()
                    if r["vote"] not in VOTES:
                        unknown[r["vote"]] += 1
                    out.append("|".join([fmt(r["sessionyear"]), fmt(r["legislativebody"]), fmt(r["votesequencenumber"]),
                                         emp, fmt((people.get(emp) or {}).get("personid")), fmt(r["condensedbillno"]),
                                         VOTES.get(r["vote"], fmt(r["vote"])), fmt(r["datemodified"])]))
        if unknown:
            print(f"{year}: vote codes not known: {dict(unknown)}", flush=True)
        write(path("RollCallHistory"), out)
        written.append(f"RollCallHistory {len(out)}")
    if summary and not os.path.exists(path("RollCallSummary")):  # after the members' votes, so it marks them done
        write(path("RollCallSummary"), ["|".join([fmt(r["sessionyear"]), fmt(r["legislativebody"]),
                                                  fmt(r["votesequencenumber"]), fmt(r["votedate"]),
                                                  fmt(r["condensedbillno"]), fmt(r["yeas"]), fmt(r["nays"]),
                                                  fmt(r["present"]), fmt(r["absent"]), fmt(r["abbreviatedtitle1"]),
                                                  fmt(r["abbreviatedtitle2"]), fmt(r["question_motion"]),
                                                  fmt(r["title1"]), fmt(r["title2"]), fmt(r["datemodified"])])
                                        for r in summary])
        written.append(f"RollCallSummary {len(summary)}")
    return written


def who_appears(first):
    """PersonIDs and employee numbers in a biennium's sponsor and roll-call files."""
    ids, emps = set(), set()
    for year in (first, first + 1):
        for name, col, into in (("LsrSponsors", 3, ids), ("RollCallHistory", 4, ids), ("RollCallHistory", 3, emps)):
            try:
                with open(os.path.join(DATA, str(first), f"{name}_{year}.txt"), encoding="utf-8") as f:
                    into.update(x for x in (line.split("|")[col] for line in f) if x)
            except (OSError, IndexError):
                pass
    return ids, emps


def members_of(first, people, skip=()):
    """Legislators rows for everyone in a biennium's sponsor and roll-call files (but skip's PersonIDs)."""
    ids, emps = who_appears(first)
    rows = [r for r in people.values()
            if (fmt(r["personid"]) in ids or fmt(r["employeeno"]).strip() in emps) and fmt(r["personid"]) not in skip]
    return [legislator_row(r) for r in sorted(rows, key=lambda r: (fmt(r["lastname"]), fmt(r["firstname"])))]


def sql_run(rp, term):
    """Fill in from the SQL Server: each missing past year's files, a past biennium's legislators.txt; weekly, this
    biennium's former_legislators.txt and CommitteeMembers.txt. Returns problems."""
    todo = [y for y in history_years() if not all(os.path.exists(os.path.join(DATA, str(first_year(y)), f"{n}_{y}.txt"))
                                                   for n in SQL_NAMES)]
    past = sorted({first_year(y) for y in history_years()} - {term})
    todo_members = [f for f in past if not os.path.exists(os.path.join(DATA, str(f), "legislators.txt"))]
    state_path = os.path.join(DATA, "sql.json")
    try:
        state = json.load(open(state_path))
    except (OSError, ValueError):
        state = {}
    weekly = (state.get("weekly") or "") <= (TODAY - timedelta(days=WEEKLY_DAYS)).isoformat()
    if not (todo or todo_members or weekly) or out_of_time():
        return []
    try:
        import pymssql, pypdf  # noqa: F401 (pip install pymssql pypdf)
    except ImportError:
        print("SQL Server: pymssql or pypdf isn't installed; past years not read", flush=True)
        return ["sql:not installed"]
    login = sql_login(rp)
    if not login:
        return ["sql:login"]
    db = None
    try:
        db = Sql(login)
        people = {fmt(r["employeeno"]).strip(): r for r in db.rows(
            "SELECT PersonID, Employeeno, LastName, FirstName, MiddleName, LegislativeBody, seatno, countycode, "
            "District, party, Address, address2, city, Expr2, Zipcode, EMailAddress FROM dbo.Legislators")}
        for year in todo:
            if out_of_time():
                return ["time"]
            written = sql_year(db, year, people)
            print(f"SQL Server {year}: " + (", ".join(written) or "nothing new"), flush=True)
        for first in todo_members:
            rows = members_of(first, people)
            if rows:
                write(os.path.join(DATA, str(first), "legislators.txt"), rows)
            print(f"SQL Server {first}-{first + 1}: {len(rows)} legislators", flush=True)
        if weekly:
            folder = os.path.join(DATA, str(term))
            try:
                with open(os.path.join(folder, "legislators.txt"), encoding="utf-8") as f:
                    sitting = {line.split("|")[0] for line in f}
            except OSError:
                sitting = set()
            former = members_of(term, people, sitting)
            write(os.path.join(folder, "former_legislators.txt"), former)
            committee = db.rows("SELECT CommitteeCode, SequenceNumber, EmployeeNumber, ActiveMember, comments "
                                "FROM dbo.CommitteeMembers ORDER BY CommitteeCode, SequenceNumber")
            write(os.path.join(folder, "CommitteeMembers.txt"), ["|".join([
                fmt(r["committeecode"]), fmt(r["sequencenumber"]), fmt(r["employeenumber"]).strip(),
                fmt((people.get(fmt(r["employeenumber"]).strip()) or {}).get("personid")), fmt(r["activemember"]),
                fmt(r["comments"])]) for r in committee])
            print(f"SQL Server: {len(former)} former legislators, {len(committee)} committee members", flush=True)
            state["weekly"] = TODAY.isoformat()
            with open(state_path, "w") as f:
                json.dump(state, f)
        return []
    except Exception as e:  # a connection or query that fails: the files written so far stay
        print(f"SQL Server: {type(e).__name__}: {db.scrub(e) if db else str(e).replace(login['password'], '***')}",
              flush=True)
        return ["sql:failed"]
    finally:
        if db:
            print(f"SQL Server: {db.queries} queries", flush=True)
            db.conn.close()


# ---- "What it does": the Office of Legislative Services' analysis at the top of each bill's text ("ANALYSIS" or, once
# amended, "AMENDED ANALYSIS": "This bill ..."). The bill status page's "Bill Text" link is the latest version:
# billText.aspx?id=<legislation id>&sy=<session year>&txtFormat=html, whose <title> names it ("HB10 — CHAPTERED FINAL
# VERSION", "SB416 — As Amended by the House", "HB54 — Introduced"). The id: the current year's own bills' from LsrsOnly
# (column 2); before this biennium it's the LSR number and the year run together (HB 119 of 2023, LSR 111: 1112023),
# checked against the page's title; otherwise (2025's bills, bills kept over) read once from the bill's status page.
# Kept in data/nh/<first year>/analyses_<session year>.json, one entry per bill, read again only when the Docket shows a
# new adopted amendment ("Amendment # 2025-0695h: AA", "Ought to Pass with Amendment 2025-0695h: MA", a conference
# report "Adopted") or a chapter number. The text lists the amendments it includes near the top ("20Mar2025... 0695h",
# "29Jun2023... 2224CofC"); when the site hasn't caught up with the Docket yet, it's read again after two days, up to
# four times. These are extras: they never mark the state incomplete, and a first copy (about 5,000 requests at the
# crawl delay, 16 hours; about a week of 20-minute runs every two hours) fills in run by run, the current year's new and
# changed bills first, then laws.
TEXT_PAGE = f"{SITE}/bill_status/legacy/bs2016/billText.aspx?id={{id}}&sy={{sy}}&txtFormat=html"
STATUS_PAGE = f"{SITE}/bill_status/legacy/bs2016/bill_status.aspx?lsr={{lsr}}&sy={{sy}}&txtsessionyear={{sy}}&txtbillnumber={{bill}}"
TEXT_KINDS = {"1", "2", "3", "13"}  # HB, SB, CACR (as convert.py's KINDS)
RETRY_DAYS, RETRIES = 2, 4
ADOPTED = re.compile(r"\b(?:AA|MA|Adopted)\b")
NOT_ADOPTED = re.compile(r"\b(?:AF|MF)\b|Filed")


def text_rows(year):
    """(LSR number, bill number "HB10", chapter, LSR as "25-0010", house) for each bill and CACR of a session year's
    LSRs file."""
    return [(r[1].strip(), r[10].replace(" ", "").upper(), r[11].strip(), r[8].strip(), r[3].strip() or "H")
            for r in _lsr_rows(year)
            if len(r) > 11 and r[4] in TEXT_KINDS and r[10].strip() and r[1].strip().isdigit()]


@functools.lru_cache(maxsize=None)
def _lsr_rows(year):
    try:
        with open(os.path.join(DATA, str(first_year(year)), f"LSRs_{year}.txt"), encoding="utf-8-sig") as f:
            return tuple(tuple(l.rstrip("\n").split("|")) for l in f if l.strip())
    except OSError:
        return ()


def wanted(year):
    """Bill number -> the amendments adopted so far, from the Docket ("0695h", "2224c")."""
    out = {}
    try:
        with open(os.path.join(DATA, str(first_year(year)), f"Docket_{year}.txt"), encoding="utf-8-sig") as f:
            for line in f:
                r = line.rstrip("\n").split("|")
                if len(r) < 6 or not ADOPTED.search(r[5]) or NOT_ADOPTED.search(r[5]):
                    continue
                codes = {a + b.lower() for a, b in re.findall(r"\b20\d\d-(\d{4})([hsc])\b", r[5], re.I)}
                if codes:
                    out.setdefault(r[3].replace(" ", "").upper(), set()).update(codes)
    except OSError:
        pass
    return out


def legislation_ids(year):
    """LSR number (int) -> legislation id, from LsrsOnly (the session year's own LSRs only)."""
    out = {}
    try:
        with open(os.path.join(DATA, str(first_year(year)), f"LsrsOnly_{year}.txt"), encoding="utf-8-sig") as f:
            for line in f:
                r = line.split("|")
                m = re.match(rf"{year % 100:02d}-(\d+)$", r[0].strip()) if len(r) > 3 else None
                if m and r[2].strip().isdigit():
                    out[int(m.group(1))] = r[2].strip()
    except OSError:
        pass
    return out


def page_lines(body):
    """A bill text page's text, a line per paragraph."""
    try:
        t = body.decode("utf-8")
    except UnicodeDecodeError:
        t = body.decode("cp1252", "replace")
    t = re.sub(r"(?is)<(script|style)\b.*?</\1>", "", t)
    title = re.search(r"(?is)<title>(.*?)</title>", t)
    t = re.sub(r"(?i)</(?:p|div|tr|h\d|li|pre)>|<br\s*/?>", "\n", t)
    import html
    t = html.unescape(re.sub(r"<[^>]+>", "", t))
    lines = [re.sub(r"\s+", " ", l.replace(" ", " ")).strip() for l in t.split("\n")]
    return html.unescape(title.group(1)).strip() if title else "", lines


def analysis_of(body, bill):
    """(version, amendments the text includes, amended analysis?, analysis paragraphs) of a bill text page, or None when
    it isn't that bill's text."""
    title, lines = page_lines(body)
    m = re.match(r"(\S+)\s+[—–-]+\s+(.*)$", title)
    if not m or m.group(1).upper() != bill:
        return None
    version = re.sub(r"\s+-\s+NH General Court$", "", m.group(2).strip())
    head = next((i for i, l in enumerate(lines) if re.fullmatch(r"(?:AMENDED )?ANALYSIS", l)), None)
    top = lines[:head] if head is not None else lines[:40]
    got = sorted({a + ("c" if b.lower() == "cofc" else b.lower())
                  for a, b in re.findall(r"\b(\d{4})(h|s|CofC)\b", " ".join(top), re.I)})
    paras = []
    if head is not None:
        for l in lines[head + 1:]:
            if re.match(r"(?:- ){3}|─{3}|Explanation:|STATE OF NEW HAMPSHIRE", l):
                break
            if not l:
                continue
            # A line cut inside a sentence (the next starts in lower case) belongs to the paragraph before.
            if paras and not re.search(r"[.:;?!)\"”]$", paras[-1]) and re.match(r"[a-z(]", l):
                paras[-1] += " " + l
            else:
                paras.append(l)
    if paras and re.fullmatch(r"No analysis (?:needed|required)\.?", paras[0], re.I):
        paras = []
    return version, got, head is not None and lines[head].startswith("AMENDED"), paras


def fetch_text(rp, sy, lsr, bill, entry, ids):
    """Read the bill's latest text into entry (a request, two when the id has to come from the status page). False when
    nothing could be read."""
    def text_at(i, y):
        url = TEXT_PAGE.format(id=i, sy=y)
        if not rp.can_fetch(AGENT, url):
            FAILS["robots.txt"] += 1
            return None
        body, _ = request(url, f"{bill} of {sy} text")
        return analysis_of(body, bill) if body else None

    got = None
    if entry.get("id"):
        got = text_at(entry["id"], entry["sy"])
    elif int(lsr) in ids:
        entry.update(id=ids[int(lsr)], sy=sy)
        got = text_at(entry["id"], sy)
    elif first_year(sy) < term_now():
        got = text_at(f"{int(lsr)}{sy}", sy)
        if got:
            entry.update(id=f"{int(lsr)}{sy}", sy=sy)
    if not got and not out_of_time():
        url = STATUS_PAGE.format(lsr=int(lsr), sy=sy, bill=bill)
        if rp.can_fetch(AGENT, url):
            body, _ = request(url, f"{bill} of {sy} status")
            m = re.search(r"billText\.aspx\?id=(\d+)&(?:amp;)?sy=(\d{4})", (body or b"").decode("utf-8", "replace"))
            if m and m.group(1) != str(entry.get("id")):
                entry.update(id=m.group(1), sy=int(m.group(2)))
                got = text_at(entry["id"], entry["sy"])
            elif body is not None and not m:
                entry["id"] = ""  # no text yet
    if not got:
        return False
    entry["version"], entry["got"], entry["amended"], entry["text"] = got
    return True


def text_years():
    """The session years with a bills file (as convert.py's sessions())."""
    out = []
    for name in os.listdir(DATA):
        if re.fullmatch(r"\d{4}", name):
            for f in os.listdir(os.path.join(DATA, name)):
                m = re.fullmatch(r"LSRs_(\d{4})\.txt", f)
                if m and len(_lsr_rows(int(m.group(1)))) > 100:
                    out.append(int(m.group(1)))
    return sorted(out)


def analyses(rp, years, limit=None):
    """Read new and changed bills' analyses, as time allows; the cache files written as it goes."""
    caches, todo = {}, []
    today = TODAY.isoformat()
    soon = (TODAY - timedelta(days=RETRY_DAYS)).isoformat()
    week = (TODAY - timedelta(days=7)).isoformat()
    for year in years:
        path = os.path.join(DATA, str(first_year(year)), f"analyses_{year}.json")
        try:
            cache = json.load(open(path))
        except (OSError, ValueError):
            cache = {}
        caches[year] = (path, cache)
        want, ids = wanted(year), legislation_ids(year)
        for lsr, bill, chapter, _, _ in text_rows(year):
            w = sorted(want.get(bill, ())) + (["chapter"] if chapter else [])
            e = cache.get(bill)
            if e and e.get("fails", 0) >= 3 and e.get("failed", "") > week:
                continue  # failed three runs in a row: tried again a week later
            if e is None or e.get("want") != w:
                why = 0 if e is None else 1  # never read; a new version
            elif not set(w) <= set(e.get("got", [])) | ({"chapter"} if "CHAPTERED" in e.get("version", "").upper() else set()) \
                    and e.get("tries", 0) < RETRIES and e.get("read", "") <= soon:
                why = 2  # the site behind the Docket
            elif e.get("id") == "" and e.get("read", "") <= soon and e.get("tries", 0) < RETRIES:
                why = 2  # no text yet
            else:
                continue
            # The current year first; then laws; then the newest years.
            rank = (0 if year == max(years) else 1, why == 2, not chapter, -year)
            todo.append((rank, year, lsr, bill, w, ids))
    todo.sort(key=lambda x: x[0])
    done = failed = 0
    try:
        for _, year, lsr, bill, w, ids in todo:
            if out_of_time() or (limit is not None and STATS["requests"] >= limit):
                break
            path, cache = caches[year]
            old = cache.get(bill) or {}
            e = {k: old[k] for k in ("id", "sy") if k in old and old[k]}
            if fetch_text(rp, year, lsr, bill, e, ids):
                tries = old.get("tries", 0) + 1 if old.get("want") == w else 1
                cache[bill] = {**e, "want": w, "read": today, "tries": tries}
                done += 1
            elif out_of_time():
                break
            else:
                failed += 1
                if e.get("id") == "":  # the status page links no text yet
                    cache[bill] = {**old, **e, "want": w, "read": today,
                                   "tries": old.get("tries", 0) + 1 if old.get("want") == w else 1}
                else:  # kept as it was (the last text, if any), with the failure counted
                    cache[bill] = {**old, **{k: v for k, v in e.items() if v}, "want": old.get("want"),
                                   "failed": today, "fails": old.get("fails", 0) + 1}
            if (done + failed) % 20 == 0:
                save_json(path, cache)
    finally:
        for path, cache in caches.values():
            save_json(path, cache)
    left = len(todo) - done - failed
    print(f"analyses: {done} read, {failed} not read, {left} still to read", flush=True)


def save_json(path, data):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=0, sort_keys=True)
    os.replace(tmp, path)


def write_texts(years):
    """data/nh/texts_<page year>.json from the cached analyses: a page's bills are its year's, and for a first year the
    bills kept over to the second (in the second year's files, "25-0010")."""
    for page in years:
        rows = [(page, r) for r in text_rows(page)]
        if page % 2:
            rows += [(page + 1, r) for r in text_rows(page + 1) if r[3].startswith(f"{page % 100:02d}-")]
        caches, out = {}, {}
        for sy, (lsr, bill, _, _, house) in rows:
            if sy not in caches:
                try:
                    caches[sy] = json.load(open(os.path.join(DATA, str(first_year(sy)), f"analyses_{sy}.json")))
                except (OSError, ValueError):
                    caches[sy] = {}
            e = caches[sy].get(bill)
            if e and e.get("text"):
                # The page's number: a CACR with its house in front ("HCACR1"), as convert.py has it.
                out[house + bill if bill.startswith("CACR") else bill] = {"statement": "\n".join(e["text"]),
                                                                          "label": text_label(e, bill)}
        save_json(os.path.join(DATA, f"texts_{page}.json"), out)
        print(f"texts_{page}.json: {len(out)} of {len(rows)} bills", flush=True)


def text_label(e, bill=""):
    """"From the Office of Legislative Services' analysis of the bill as amended by the House." and the like. An analysis
    not marked "AMENDED" is the one written for the bill as introduced, though the text may since have been amended."""
    v = e.get("version", "").lower()
    what = "resolution" if "CACR" in bill else "bill"
    if not e.get("amended"):
        which = f"the {what} as introduced" if e.get("got") or "introduced" in v else f"the {what}"
    elif "chaptered" in v or "final" in v or "enrolled" in v:
        which = "the final version"
    elif "amended by" in v:
        which = f"the {what} " + re.sub(r"^.*?(as amended by.*)$", r"\1", v).replace("house", "House").replace("senate", "Senate")
    else:
        which = f"the {what} as amended"
    return f"From the Office of Legislative Services' analysis of {which}."


def missing(term):
    """Files never downloaded: the current biennium's per-term files, and this session year's (or, before a new
    session's files appear in January, the last year's)."""
    folder = os.path.join(DATA, str(term))
    out = [n for n in list(PER_TERM) + ["Members"] if not os.path.exists(os.path.join(folder, f"{n}.txt"))]
    for name in BY_YEAR:
        if not any(os.path.exists(os.path.join(DATA, str(first_year(y)), f"{name}_{y}.txt"))
                   for y in (TODAY.year, TODAY.year - 1)):
            out.append(f"{name}_{TODAY.year}")
    for year in history_years():  # from the SQL Server
        out += [f"{n}_{year}" for n in SQL_NAMES
                if not os.path.exists(os.path.join(DATA, str(first_year(year)), f"{n}_{year}.txt"))]
    for first in sorted({first_year(y) for y in history_years()} - {term}):
        if not os.path.exists(os.path.join(DATA, str(first), "legislators.txt")):
            out.append(f"legislators_{first}")
    return out


def main():
    os.makedirs(DATA, exist_ok=True)
    # A run cut off by its time limit leaves this, so a partial copy isn't published (cleared once every file has a copy).
    if not os.path.exists(MARKER):
        open(MARKER, "w").write("running\n")
    term = term_now()
    folder = os.path.join(DATA, str(term))
    os.makedirs(folder, exist_ok=True)
    texts_only = "--texts-only" in sys.argv  # for testing: only the analyses
    limit = next((int(a.split("=", 1)[1]) for a in sys.argv if a.startswith("--max-requests=")), None)
    try:
        rp = robots()
        if rp is None:
            print("robots.txt couldn't be read; nothing downloaded", flush=True)
        else:
            for name, (columns, col) in ({} if texts_only else BY_YEAR).items():
                if out_of_time():
                    break
                by_year(rp, name, columns, col)
            for name, columns in ({} if texts_only else PER_TERM).items():
                if out_of_time():
                    break
                per_term(rp, name, columns, folder)
            if not texts_only:
                if not out_of_time():
                    members(rp, folder)
                sql_run(rp, term)
            if not out_of_time():
                analyses(rp, text_years(), limit)
    except Refused as e:
        print(f"Stopped: the server refused a request ({e})", flush=True)
    write_texts(text_years())
    print(f"run: {STATS['requests']} requests, {round((time.time() - START) / 60, 1)} min"
          + ("; stopped at the time limit" if out_of_time() else "")
          + (f"; request failures {dict(FAILS)}" if FAILS else "; no request failures"), flush=True)
    gaps = missing(term)
    if gaps:
        open(MARKER, "w").write(" ".join(gaps) + "\n")
        print(f"never downloaded: {' '.join(gaps)}", flush=True)
    elif os.path.exists(MARKER):
        os.remove(MARKER)


if __name__ == "__main__":
    main()
