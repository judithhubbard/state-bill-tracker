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
(2025 and 2026 both go in data/nh/2025/); a year no longer in the files keeps its last copy for good. What 2025 lost
before the first run (2026-11-08): the titles, sponsors and roll calls of the bills finished in 2025 (their Docket
history is kept), and everything of 2023-24. The Legislature's public SQL Server (described in
https://gc.nh.gov/downloads/ODBC%20and%20Data%20Table%20Structure.pdf, with published read-only credentials) or the
bill status pages could fill those in; neither is read here (the owner's decision).

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
data/nh/incomplete says "running" during a run, and after it lists files never downloaded; it is removed when every
file has a copy. A run is about 15 requests at the crawl delay: about 3 minutes, the same every day.
Usage: python3 states/nh/fetch.py
"""
import gzip, json, os, time, urllib.error, urllib.request, urllib.robotparser
from collections import Counter
from datetime import date

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


def missing(term):
    """Files never downloaded: the current biennium's per-term files, and this session year's (or, before a new
    session's files appear in January, the last year's)."""
    folder = os.path.join(DATA, str(term))
    out = [n for n in list(PER_TERM) + ["Members"] if not os.path.exists(os.path.join(folder, f"{n}.txt"))]
    for name in BY_YEAR:
        if not any(os.path.exists(os.path.join(DATA, str(first_year(y)), f"{name}_{y}.txt"))
                   for y in (TODAY.year, TODAY.year - 1)):
            out.append(f"{name}_{TODAY.year}")
    return out


def main():
    os.makedirs(DATA, exist_ok=True)
    # A run cut off by its time limit leaves this, so a partial copy isn't published (cleared once every file has a copy).
    if not os.path.exists(MARKER):
        open(MARKER, "w").write("running\n")
    term = term_now()
    folder = os.path.join(DATA, str(term))
    os.makedirs(folder, exist_ok=True)
    try:
        rp = robots()
        if rp is None:
            print("robots.txt couldn't be read; nothing downloaded", flush=True)
        else:
            for name, (columns, col) in BY_YEAR.items():
                if out_of_time():
                    break
                by_year(rp, name, columns, col)
            for name, columns in PER_TERM.items():
                if out_of_time():
                    break
                per_term(rp, name, columns, folder)
            if not out_of_time():
                members(rp, folder)
    except Refused as e:
        print(f"Stopped: the server refused a request ({e})", flush=True)
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
