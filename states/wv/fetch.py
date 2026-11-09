#!/usr/bin/env python3
"""Download West Virginia's bills from the Legislature's bill status pages on www.wvlegislature.gov (server-built HTML
from ColdFusion: there is no API, bulk file or export; the one JSON file, billsearch_data.cfm, is only numbers and short
titles). www.wvlegislature.gov's robots.txt (checked 2026-11-09) bars, for all user agents, /mobile/, /apps/, /js/,
/media/, /daily_sum/, /FiscalNotes/, /WVCODE/, /Staff/, /Wrapup/ and a few other folders, none of which are read, and
sets no crawl delay (the bare wvlegislature.gov has no robots.txt and serves nothing; code.wvlegislature.gov bars only
/wp-admin/ and isn't read). /Bill_Status/, /legisdocs/ (the roll-call PDFs), /House/, /Senate1/ and /committees/ are
allowed. One request at a time, at most one a second (a bill page takes the server about half a second).

West Virginia's Legislature meets once a year for 60 days: from the second Wednesday of January, or of February in the
year a governor is inaugurated (2025, 2029). Special (extraordinary) sessions are left out. The lower house is the House
of Delegates. For each year from two years back through this one (and next year's in November and December, once its
bill list has bills), into data/wv/<year>/:
- lists/<name>.html (each page's <main>, scripts removed, blank lines squeezed) and list.json, what this script reads
  from them: {"read", "bills": {"HB2001": {"href", "cells"}}, "laws": {"SB8": cells}, "governor": {"SIGNED": {"SB1":
  cells}, ...}, "votes": [{"bill", "date", "motion", "pdf"}]}. The lists, all for the regular session (sessiontype=RS):
  all_bills (Bills_all_bills.cfm: every House and Senate bill with its short title, status ("Pending", "Signed",
  "Vetoed", "Became Law (Without Signature)"), where it is (committee, "Concurrence", "Governor") and the date of its
  last step, or its effective date); resolutions (res_list.cfm: only the joint resolutions, HJR and SJR, are kept:
  West Virginia's constitutional amendments are joint resolutions, which pass each house by two-thirds and go to the
  voters, not the governor; concurrent and one house's resolutions are left out); completed (Bills_all_pass.cfm:
  every bill that completed legislative action, with its Acts chapter, "Chapter 46, Acts, Regular Session, 2025", once
  assigned, and its effective date); gov_signed, gov_vetoed, gov_awaiting, gov_nosig (ActionsbyGov.cfm, one per
  actype: SIGNED, VETOED, AWAITING GOVERNOR ACTION, BECAME LAW (NO SIGNATURE)); votes (votes.cfm: every floor roll call
  of the session, bills' and resolutions', with its bill, date, motion ("Passed House (Roll No. 93)", "Amendment
  rejected", "Constitutional Rule Suspended") and PDF).
- bills/<HB2001>.html, <SJR3>.html: each bill's and joint resolution's history page (Bills_history.cfm?input=2001&year=
  2025&sessiontype=RS&btype=bill; Resolution_History.cfm?...&billtype=jr&houseorig=h), from its heading on, scripts
  removed: last action, the short title ("SUMMARY:"), lead sponsor and sponsors in order (surnames: "Thorne"; House
  sponsors linked by hsemem=, Senate by senmem=), the bill text versions (Introduced Version, Committee Substitute,
  Engrossed, Enrolled ...), the Code sections affected, committee amendments, the roll calls with their links, subjects,
  then the actions, newest first, each with its house letter, its committee code when it's a referral (data-com="HHR":
  "To Health and Human Resources"), its date and journal page ("Introduced in Senate", "To Health and Human Resources",
  "Committee substitute reported", "Passed House (Roll No. 93)", "Senate concurred in House amendments and passed bill",
  "To Governor 3/20/2025", "Approved by Governor 3/26/2025", "Vetoed by Governor", "Chapter 46, Acts, Regular
  Session, 2025"). Overrides and line-item vetoes (budget bills) are in the actions as written. Floor votes are tallies
  there; members' votes are in the roll-call PDFs (below).
- texts/<HB2001>.json: "What it does". The bill pages' "summary" is only the short title, but each bill's text carries
  the drafter's note ("NOTE: The purpose of this bill is to ..."), and its title ("A BILL to amend and reenact ...
  relating to ..."). From each HTML text version (bills_text.cfm) except engrossed and enrolled ones (which drop the
  note), read once: {"docs": {"sb8 intr.htm": {"version": "Introduced Version", "head": [...], "title", "note"}}}.
- votes/house/<00093>.txt and votes/senate/<02-24-0019>.txt: every floor roll call as text (pdftotext -layout), read
  once: the House's lists every name under YEAS / NAYS / NOT VOTING / EXCUSED ("Smith, B", "Speaker Hanshaw"), the
  Senate's has a Y/N/A/E letter before each surname in capitals ("MR PRESIDENT"). From the votes list and the bill
  pages' links (about 1,300 a year: in 2025, 683 House and 609 Senate). Committee votes aren't published by member
  (the minutes are PDFs, not read).
- state.json: each bill's signal (its list row, Acts chapter and governor's action) when it was read ("signals"), the
  day it was read ("read"), its text documents ("docs") and roll-call links ("rolls") from its page, roll calls that
  failed to convert ("bad_rolls"), bills that answer 404 ("absent") and when the lists were read ("listed").
And into data/wv/members/: house.html and senate.html (/House/roster.cfm, /Senate1/roster.cfm: the current members with
party, district (the House's 100 single-member districts since 2022; the Senate's 17 two-member districts, with the
member's home county and the district's counties), Capitol office, email and phone), <Delegate Adkins>.html (each
member's page, lawmaker.cfm?member=...: name with party, county and district "(R - Nicholas, 049)", the leadership post,
Capitol and district addresses, committee assignments, district counties), committees/<house>_<code>.html (each
standing committee's page, HouseCommittee.cfm?Chart=jud: members with "Chair", "Vice-Chair", "Minority Chair"; phone
and email); members.json and committees.json are what this script reads from them. Read when older than a week. Only
current members are listed: past years' members are names in the bill pages and roll calls.

What's read again: the lists every run for this year and next (about 9 requests a year, under a minute), weekly for
past years; a bill's page when its signal changes, and, for this year's bills, when its copy is over REFRESH_DAYS old
(through June; at most REFRESH_MAX a run, oldest first: the signal misses new sponsors and some steps). Roll calls and text versions
are read once. A first copy of three sessions (about 7,500 bills and joint resolutions, about 9,000 text versions and
about 4,000 roll calls, at a request a second: about 2 hours of bill pages, then about 2½ hours of texts and an hour
of roll calls) builds up over several runs: the bill pages first, then the roll calls, then the texts. A quiet run
takes about a minute; one during the session a few minutes more.

Not downloaded: bill texts in full, fiscal notes (/FiscalNotes/, barred), committee amendments, agendas and minutes,
journals, the governor's veto messages (in the journals), members' biographies.

data/wv/incomplete says "running" during the first copy, then lists what was never downloaded (a year's bill or
resolution list, a listed bill's page, the rosters, a member's or committee's page); it is removed when nothing is
missing. Roll calls and texts fill in on later runs and don't hold the state back. A request that fails where a last
copy exists keeps that copy and doesn't count; a bill page that answers 404 is noted and doesn't count. Roll calls need
pdftotext (poppler-utils); without it they are skipped, with a note.
Usage: python3 states/wv/fetch.py [year]   (default: every year above; a single year leaves the marker alone)
"""
import gzip, hashlib, html, json, os, re, shutil, subprocess, sys, tempfile, time, urllib.error, urllib.parse
import urllib.request
from collections import Counter
from datetime import date, datetime, timedelta

SITE = "https://www.wvlegislature.gov"
STATUS = SITE + "/Bill_Status/"
DATA = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "wv"))
AGENT = "statebilltracker.org (a nonprofit bill tracker; contact via github.com/judithhubbard)"
TODAY = date.today()
YEAR = TODAY.year
ONLY = int(sys.argv[1]) if len(sys.argv) > 1 else None
DELAY = 1.0  # seconds between the starts of two requests
REFRESH_DAYS = 30
REFRESH_MAX = 200
LIST_DAYS = 7  # past years' lists
MEMBER_DAYS = 7
MARKER = os.path.join(DATA, "incomplete")
PDFTOTEXT = shutil.which("pdftotext")
GOV = {"SIGNED": "gov_signed", "VETOED": "gov_vetoed", "AWAITING GOVERNOR ACTION": "gov_awaiting",
       "BECAME LAW (NO SIGNATURE)": "gov_nosig"}
HISTORY = re.compile(r'href="((?:Bills_history|Resolution_History)\.cfm\?[^"]*)"[^>]*>\s*([HS](?:B|JR|CR|R)) (\d+)\s*<',
                     re.I)
ROLL = re.compile(r'href="(/legisdocs/(\d{4})/RS/votes/(house|senate)/([\w-]+)\.pdf)"', re.I)

# The run's own time limit (FETCH_MINUTES, set by the workflow): stop a few minutes early, with everything read so far
# saved and a summary printed, rather than be cut off silently mid-request.
START = time.time()
BUDGET = max(0.0, float(os.environ.get("FETCH_MINUTES") or 0) - 5) * 60
FAILS = Counter()  # why requests failed, for the summary
STATS = Counter()  # requests, bills, rolls, texts
LAST = [0.0]  # when the last request started
CODE = [0]  # the last request's HTTP status (404: not there)


class Refused(Exception):
    """The server turned us away (401/403/429): stop the run."""


def out_of_time():
    return BUDGET and time.time() - START > BUDGET


def request(url, label, must=None, binary=False):
    """The page as text (bytes when binary), or None after three tries; None at once for a 404 (CODE[0] is then 404).
    must is a piece of text the page has to contain (else it's counted as a failure: an error page served as 200)."""
    CODE[0] = 0
    url = urllib.parse.quote(url, safe=":/?&=%#+,;'()")
    for attempt in range(3):
        if out_of_time():
            return None
        wait = LAST[0] + DELAY - time.time()
        if wait > 0:
            time.sleep(wait)
        LAST[0] = time.time()
        STATS["requests"] += 1
        if STATS["requests"] % 100 == 0:
            print(f"  {STATS['requests']} requests, {round((time.time() - START) / 60)} min"
                  + (f"; failures {dict(FAILS)}" if FAILS else ""), flush=True)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": AGENT, "Accept-Encoding": "gzip"})
            with urllib.request.urlopen(req, timeout=90) as r:
                body = r.read()
                if r.headers.get("Content-Encoding") == "gzip":
                    body = gzip.decompress(body)
            if binary:
                if must and not body.startswith(must):
                    FAILS["unexpected file"] += 1
                else:
                    return body
            else:
                text = body.decode("utf-8", "replace")
                if must and must not in text:
                    FAILS["unexpected page"] += 1
                else:
                    return text
        except urllib.error.HTTPError as e:
            FAILS[f"HTTP {e.code}"] += 1
            if e.code in (401, 403, 429):
                raise Refused(f"{label}: HTTP {e.code}")
            if e.code == 404:
                CODE[0] = 404
                return None
        except Exception as e:
            FAILS[type(e).__name__] += 1
        time.sleep(5 * (attempt + 1))
    print(f"{label}: failed three times", flush=True)
    return None


def strip(body):
    body = re.sub(r"<script\b.*?</script>|<style\b.*?</style>|<input\b[^>]*>|<link\b[^>]*>", "", body, flags=re.S | re.I)
    return re.sub(r"[ \t]*\n\s*", "\n", body)


def trim_main(page):
    """A page's <main> element, scripts removed."""
    a = page.find("<main")
    b = page.find("</main>", max(a, 0))
    return strip(page[max(a, 0):b + 7 if b > 0 else len(page)])


def trim_bill(page):
    """A bill or resolution page from its heading (the menus above it are the same everywhere) to the end of <main>."""
    a = page.find('id="bhistcontent"')
    a = page.rfind("<div", 0, a) if a > 0 else page.find("<main")
    b = page.find("</main>", max(a, 0))
    return strip(page[max(a, 0):b + 7 if b > 0 else len(page)])


def text(fragment):
    t = re.sub(r"<br\s*/?>", "\n", fragment, flags=re.I)
    t = html.unescape(re.sub(r"<[^>]+>", " ", t)).replace("\xa0", " ")
    return "\n".join(re.sub(r"[ \t]+", " ", line).strip() for line in t.split("\n")).strip()


def one_line(fragment):
    return re.sub(r"\s+", " ", text(fragment)).strip()


def save_text(body, path):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(body)
    os.replace(tmp, path)


def save(obj, path):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=0)
    os.replace(tmp, path)


def load(path, default=None):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def rows(page):
    """A list page's table rows that link to a bill or resolution: (key "HB2001", href, kind "jr"/"cr"/"r"/"", cells)."""
    out = []
    for r in re.findall(r"<tr\b[^>]*>(.*?)</tr>", page or "", re.S | re.I):
        m = HISTORY.search(r)
        if not m:
            continue
        kind = re.search(r"billtype=(\w+)", m.group(1))
        cells = [one_line(c) for c in re.findall(r"<td\b[^>]*>(.*?)</td>", r, re.S | re.I)]
        out.append((m.group(2).upper() + m.group(3), html.unescape(m.group(1)), kind.group(1).lower() if kind else "",
                    cells))
    return out


def read_lists(year, folder):
    """The session's lists; None unless the bill and resolution lists were read."""
    os.makedirs(os.path.join(folder, "lists"), exist_ok=True)
    last = load(os.path.join(folder, "list.json")) or {}
    q = f"year={year}&sessiontype=RS"
    out = {"read": datetime.now().isoformat(timespec="minutes"), "bills": {}, "laws": {}, "governor": {}, "votes": []}
    pages = [("all_bills", f"Bills_all_bills.cfm?{q}&btype=bill"), ("resolutions", f"res_list.cfm?{q}&btype=res"),
             ("completed", f"Bills_all_pass.cfm?{q}&btype=bill"), ("votes", f"votes.cfm?{q}&btype=bill")]
    pages += [(name, f"ActionsbyGov.cfm?{q}&actype={urllib.parse.quote_plus(kind)}") for kind, name in GOV.items()]
    for name, path in pages:
        if out_of_time():
            return None
        page = request(STATUS + path, f"{year} {name}", "</main>")
        if page is None:
            if name in ("all_bills", "resolutions"):
                return None
            print(f"{year} {name}: unreadable; kept the last copy", flush=True)
            if name == "completed":
                out["laws"] = last.get("laws", {})
            elif name == "votes":
                out["votes"] = last.get("votes", [])
            else:
                kind = next(k for k, n in GOV.items() if n == name)
                out["governor"][kind] = last.get("governor", {}).get(kind, {})
            continue
        save_text(trim_main(page), os.path.join(folder, "lists", f"{name}.html"))
        if name == "all_bills":
            for key, href, kind, cells in rows(page):
                if re.match(r"[HS]B\d", key):
                    out["bills"][key] = {"href": href, "cells": cells}
        elif name == "resolutions":
            for key, href, kind, cells in rows(page):
                if kind == "jr" and re.match(r"[HS]JR\d", key):
                    out["bills"][key] = {"href": href, "cells": cells}
        elif name == "completed":
            out["laws"] = {key: cells for key, href, kind, cells in rows(page)}
        elif name == "votes":
            for r in re.findall(r"<tr\b[^>]*>(.*?)</tr>", page, re.S | re.I):
                m, pdf = HISTORY.search(r), ROLL.search(r)
                if not (m and pdf):
                    continue
                cells = [one_line(c) for c in re.findall(r"<td\b[^>]*>(.*?)</td>", r, re.S | re.I)]
                out["votes"].append({"bill": m.group(2).upper() + m.group(3), "date": cells[2] if len(cells) > 2 else "",
                                     "motion": cells[-1] if cells else "", "pdf": pdf.group(1)})
        else:
            kind = next(k for k, n in GOV.items() if n == name)
            out["governor"][kind] = {key: cells for key, href, k, cells in rows(page)}
    return out


def signal(listing, key):
    """What the lists say about a bill: when it changes, the bill's page is read again."""
    gov = sorted(kind for kind, keys in listing.get("governor", {}).items() if key in keys)
    raw = json.dumps([listing["bills"][key]["cells"], listing.get("laws", {}).get(key), gov], ensure_ascii=False)
    return hashlib.sha1(raw.encode()).hexdigest()[:16]


def page_links(page):
    """A bill page's text versions (except engrossed and enrolled) and roll-call PDFs."""
    docs = []
    for m in re.finditer(r'href="(bills_text\.cfm\?[^"]*)"\s+title="HTML - ([^"]*?) - [^"]*"', page):
        href, version = html.unescape(m.group(1)), html.unescape(m.group(2))
        doc = re.search(r"billdoc=([^&]*)", href)
        if doc and not re.search(r"engross|enroll", version, re.I):
            docs.append([urllib.parse.unquote(doc.group(1)), version, href])
    rolls = sorted(set(m.group(1) for m in ROLL.finditer(page)))
    return docs, rolls


def session(year):
    """One session's lists and bill pages. True when the session exists (its lists have bills)."""
    folder = os.path.join(DATA, str(year))
    state_path = os.path.join(folder, "state.json")
    state = load(state_path, {})
    listing = load(os.path.join(folder, "list.json"))
    fresh = year >= YEAR or not listing or not state.get("listed") or \
        state["listed"] < (TODAY - timedelta(days=LIST_DAYS)).isoformat()
    if fresh:
        got = read_lists(year, folder)
        if got and got["bills"]:
            listing = got
            os.makedirs(folder, exist_ok=True)
            save(listing, os.path.join(folder, "list.json"))
            state["listed"] = TODAY.isoformat()
        elif got is not None:
            if not listing:
                print(f"{year}: no bills listed yet", flush=True)
                return False
        elif not out_of_time():
            print(f"{year}: lists unreadable; kept the last copy", flush=True)
    if not listing:
        return False
    os.makedirs(os.path.join(folder, "bills"), exist_ok=True)
    read, signals = state.setdefault("read", {}), state.setdefault("signals", {})
    docs, rolls, absent = state.setdefault("docs", {}), state.setdefault("rolls", {}), state.setdefault("absent", {})
    wanted = {k: signal(listing, k) for k in listing["bills"]}
    have = lambda k: os.path.exists(os.path.join(folder, "bills", f"{k}.html"))
    urgent = [k for k in wanted if (not have(k) and absent.get(k) != wanted[k]) or (have(k) and signals.get(k) != wanted[k])]
    old = (TODAY - timedelta(days=REFRESH_DAYS)).isoformat()
    live = year > YEAR or (year == YEAR and TODAY.month <= 6)  # the session and its signing period
    rest = [k for k in wanted if k not in urgent and have(k) and live and read.get(k, "") < old]
    rest.sort(key=lambda k: read.get(k, ""))  # oldest copies first
    todo = urgent + rest[:REFRESH_MAX]
    print(f"{year}: {len(wanted)} bills and joint resolutions listed; {len(urgent)} new or changed, {len(rest)} copies"
          f" over {REFRESH_DAYS} days old; {len(todo)} to read", flush=True)
    got = 0
    for k in todo:
        if out_of_time():
            break
        page = request(STATUS + listing["bills"][k]["href"], f"{year} {k}", "bhistcontent")
        if not page:
            if CODE[0] == 404:
                absent[k] = wanted[k]
            continue  # the last copy stays, and it's asked again next run
        save_text(trim_bill(page), os.path.join(folder, "bills", f"{k}.html"))
        read[k], signals[k] = TODAY.isoformat(), wanted[k]
        docs[k], rolls[k] = page_links(page)
        absent.pop(k, None)
        got += 1
        STATS["bills"] += 1
        if got % 50 == 0:
            save(state, state_path)
    save(state, state_path)
    print(f"{year} bills: {got} of {len(todo)} read", flush=True)
    return True


def pdf_text(body):
    """A PDF's text (pdftotext -layout), or None."""
    with tempfile.TemporaryDirectory() as tmp:
        src = os.path.join(tmp, "in.pdf")
        with open(src, "wb") as f:
            f.write(body)
        try:
            out = subprocess.run([PDFTOTEXT, "-layout", "-enc", "UTF-8", src, "-"], capture_output=True, timeout=300)
        except Exception:
            return None
        return out.stdout.decode("utf-8", "replace") if out.returncode == 0 else None


def roll_calls(year):
    """Every roll call of the session not read yet, as text. A PDF that fails three runs in a row is left."""
    folder = os.path.join(DATA, str(year))
    listing = load(os.path.join(folder, "list.json"))
    state_path = os.path.join(folder, "state.json")
    state = load(state_path, {})
    if not listing:
        return
    pdfs = {v["pdf"] for v in listing.get("votes", [])}
    for links in state.get("rolls", {}).values():
        pdfs.update(links)
    bad = state.setdefault("bad_rolls", {})
    todo = []
    for pdf in sorted(pdfs):
        m = ROLL.match(f'href="{pdf}"')
        if not m or int(m.group(2)) != year:
            continue
        path = os.path.join(folder, "votes", m.group(3).lower(), m.group(4) + ".txt")
        if not os.path.exists(path) and bad.get(pdf, 0) < 3:
            todo.append((pdf, path))
    if not todo:
        return
    print(f"{year} roll calls: {len(pdfs)} known, {len(todo)} to read", flush=True)
    got = 0
    for pdf, path in todo:
        if out_of_time():
            break
        body = request(SITE + pdf, f"{year} roll call {pdf}", b"%PDF", binary=True)
        out = pdf_text(body) if body else None
        if not out or not out.strip():
            if body is not None or CODE[0] == 404:
                bad[pdf] = bad.get(pdf, 0) + 1
            continue
        os.makedirs(os.path.dirname(path), exist_ok=True)
        save_text(out, path)
        bad.pop(pdf, None)
        got += 1
        STATS["rolls"] += 1
    save(state, state_path)
    print(f"{year} roll calls: {got} of {len(todo)} read", flush=True)


def paragraphs(page):
    a = page.find("<main")
    b = page.find("</main>", max(a, 0))
    body = re.sub(r"<script\b.*?</script>|<style\b.*?</style>", "", page[max(a, 0):b if b > 0 else len(page)], flags=re.S)
    return [p for p in (one_line(x) for x in re.findall(r"<(?:p|h\d)\b[^>]*>(.*?)</(?:p|h\d)>", body, re.S | re.I)) if p]


def bill_text(page):
    """A text version's heading lines, title ("A BILL to ...") and drafter's note ("NOTE: The purpose of this bill ...")."""
    ps = paragraphs(page)
    head, title, note = [], "", []
    for i, p in enumerate(ps):
        if re.match(r"(A BILL|AN ACT|A JOINT RESOLUTION|JOINT RESOLUTION|A RESOLUTION)\b", p, re.I):
            title, head = p, ps[max(0, i - 6):i]
            break
    starts = [i for i, p in enumerate(ps) if p.startswith("NOTE:")]
    if starts:
        for p in ps[starts[-1]:starts[-1] + 4]:
            if note and re.match(r"Strike-throughs|§|ARTICLE|\(?This (section|article|bill) (is|was|has)", p):
                break
            note.append(p)
    return {"head": head, "title": title, "note": " ".join(note)}


def texts(year):
    """Each bill's text versions not read yet: heading, title and note."""
    folder = os.path.join(DATA, str(year))
    state = load(os.path.join(folder, "state.json"), {})
    todo = []
    for k, ds in state.get("docs", {}).items():
        have = (load(os.path.join(folder, "texts", f"{k}.json")) or {}).get("docs", {})
        todo += [(k, d) for d in ds if d[0] not in have]
    if not todo:
        return
    print(f"{year} texts: {len(todo)} to read", flush=True)
    os.makedirs(os.path.join(folder, "texts"), exist_ok=True)
    got = 0
    for k, (doc, version, href) in todo:
        if out_of_time():
            break
        page = request(STATUS + href, f"{year} {k} {doc}", "</main>")
        if page is None and CODE[0] != 404:
            continue
        path = os.path.join(folder, "texts", f"{k}.json")
        record = load(path) or {"docs": {}}
        record["docs"][doc] = dict(version=version, **(bill_text(page) if page else {"missing": True}))
        save(record, path)
        got += 1
        STATS["texts"] += 1
    print(f"{year} texts: {got} of {len(todo)} read", flush=True)


def roster(page, house):
    """The House's or Senate's roster: [{house, member (the page's key), name, party, district, ...}]."""
    out = []
    for r in re.findall(r"<tr\b[^>]*>(.*?)</tr>", page, re.S | re.I):
        m = re.search(r'href="lawmaker\.cfm\?member=([^"]+)"[^>]*style="vertical-align:top">(.*?)</a>', r, re.S)
        if not m:
            continue
        cells = [text(c) for c in re.findall(r"<td\b[^>]*>(.*?)</td>", r, re.S | re.I)]
        email = re.search(r"mailto:\s*([^\"'>\s]+)", r)
        rec = {"house": house, "member": html.unescape(m.group(1)).strip(), "name": one_line(m.group(2)),
               "party": cells[1] if len(cells) > 1 else "", "email": email.group(1) if email else ""}
        if house == "H":  # name, party, district, office, email, phone
            rec.update(district=cells[2] if len(cells) > 2 else "", office=cells[3] if len(cells) > 3 else "",
                       phone=cells[5] if len(cells) > 5 else "")
        else:  # name, party, district and home county, counties, office, phone and email
            d = (cells[2] if len(cells) > 2 else "").split("\n")
            phone = re.search(r"\(\d{3}\)\s*\d{3}-\d{4}", cells[5] if len(cells) > 5 else "")
            rec.update(district=d[0].strip(), home_county=" ".join(d[1:]).strip(),
                       counties=cells[3] if len(cells) > 3 else "", office=cells[4] if len(cells) > 4 else "",
                       phone=phone.group(0) if phone else "")
        out.append(rec)
    return out


def member_page(page):
    """One member's page: heading, post, Capitol and district addresses, phone, committees, district counties."""
    out = {}
    h = re.search(r'<div id="wrapleftcolr">\s*<h2>(.*?)</h2>\s*<b>(.*?)</b>', page, re.S)
    if h:
        out["heading"] = one_line(h.group(1))  # "Stanley Adkins (R - Nicholas, 049)"
        out["post"] = one_line(h.group(2))
    cap = re.search(r"<b>Capitol Office:</b>(.*?)<i>", page, re.S)
    out["capitol"] = [x for x in text(cap.group(1)).split("\n") if x] if cap else []
    ph = re.search(r"Capitol Phone:</i>\s*([^<]*)", page)
    out["capitol_phone"] = ph.group(1).strip() if ph else ""
    dist = re.search(r"<b>District:</b>(.*?)(?:<h2|</div>)", page, re.S)
    out["district_address"] = [x for x in text(dist.group(1)).split("\n") if x] if dist else []
    right = re.search(r'<div id="wraprightcolr">(.*?)INTERIM COMMITTEES', page, re.S)
    out["committees"] = [{"code": c.group(1).lower(), "name": one_line(c.group(2))}
                         for c in re.finditer(r'chart=(\w+)">(.*?)</a>', right.group(1) if right else "", re.I)]
    counties = re.search(r"District Counties:</strong>(.*?)<br", page, re.S)
    out["district_counties"] = one_line(counties.group(1)) if counties else ""
    return out


def members():
    """The current members of both houses and their pages, weekly. A page that fails keeps its last copy."""
    folder = os.path.join(DATA, "members")
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, "members.json")
    last = load(path) or {}
    if last.get("read", "") >= (TODAY - timedelta(days=MEMBER_DAYS)).isoformat() and not last.get("missing"):
        return
    listed = []
    for house, sub, name in (("H", "House", "house"), ("S", "Senate1", "senate")):
        page = request(f"{SITE}/{sub}/roster.cfm", f"{name} roster", "lawmaker.cfm")
        got = roster(page or "", house)
        if len(got) < (90 if house == "H" else 30):
            print(f"{name} roster: unreadable; kept the last copy", flush=True)
            return
        save_text(trim_main(page), os.path.join(folder, f"{name}.html"))
        listed += got
    before = {m["member"]: m for m in last.get("members", [])}
    out, missing = [], []
    for m in listed:
        if out_of_time():
            return
        sub = "House" if m["house"] == "H" else "Senate1"
        page = request(f"{SITE}/{sub}/lawmaker.cfm?member={m['member']}", m["member"], "wrapleftcolr")
        if page:
            save_text(trim_main(page), os.path.join(folder, re.sub(r"[^\w ,.-]", "", m["member"]) + ".html"))
            out.append(dict(m, **member_page(page)))
        elif m["member"] in before:
            out.append(dict(before[m["member"]], **m))
        else:
            out.append(m)
            missing.append(m["member"])
    save({"read": TODAY.isoformat(), "members": out, "missing": missing}, path)
    print(f"members: {sum(m['house'] == 'H' for m in out)} delegates, {sum(m['house'] == 'S' for m in out)} senators,"
          f" {sum(bool(m['email']) for m in out)} with emails, {sum(bool(m.get('phone')) for m in out)} with phones"
          + (f"; {len(missing)} pages never read" if missing else ""), flush=True)


def committee(page, house, code):
    title = re.search(r"<h1>(.*?)</h1>", page, re.S)
    left = re.search(r'<div id="wrapleftcol">(.*?)</div>', page, re.S)
    mems = []
    for m in re.finditer(r'lawmaker\.cfm\?member=([^"]+)">[^<]*</a>(\s*-\s*<strong>(.*?)</strong>)?',
                         left.group(1) if left else "", re.S):
        mems.append({"member": html.unescape(m.group(1)).strip(), "role": one_line(m.group(3) or "")})
    right = page[page.find("wraprightcol"):page.find("<footer")] if "wraprightcol" in page else ""
    phone = re.search(r"(\d{3}-\d{3}-\d{4})", right)
    email = re.search(r"mailto:([^\"'>\s]+)", right)
    return {"house": house, "code": code, "name": one_line(title.group(1)) if title else "", "members": mems,
            "phone": phone.group(1) if phone else "", "email": email.group(1) if email else ""}


def committees():
    """Each house's standing committees, weekly. A committee that fails keeps its last copy."""
    folder = os.path.join(DATA, "members", "committees")
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(DATA, "members", "committees.json")
    last = load(path) or {}
    if last.get("read", "") >= (TODAY - timedelta(days=MEMBER_DAYS)).isoformat() and not last.get("missing"):
        return
    found = []
    for house, sub, page_name in (("H", "house", "HouseCommittee"), ("S", "senate", "SenateCommittee")):
        page = request(f"{SITE}/committees/{sub}/main.cfm", f"{sub} committees", page_name)
        codes = sorted(set(c.lower() for c in re.findall(page_name + r"\.cfm\?Chart=(\w+)", page or "", re.I)))
        if not codes:
            print(f"{sub} committees: list unreadable; kept the last copy", flush=True)
            return
        found += [(house, sub, page_name, c) for c in codes]
    before = {(c["house"], c["code"]): c for c in last.get("committees", [])}
    out, missing = [], []
    for house, sub, page_name, code in found:
        if out_of_time():
            return
        page = request(f"{SITE}/committees/{sub}/{page_name}.cfm?Chart={code}", f"committee {house} {code}",
                       "wrapleftcol")
        if page:
            save_text(trim_main(page), os.path.join(folder, f"{house}_{code}.html"))
            out.append(committee(page, house, code))
        elif (house, code) in before:
            out.append(before[(house, code)])
        else:
            missing.append(f"{house}_{code}")
    save({"read": TODAY.isoformat(), "committees": out, "missing": missing}, path)
    print(f"committees: {len(out)} ({sum(any(m['role'] == 'Chair' for m in c['members']) for c in out)} with a chair)"
          + (f"; {len(missing)} never read" if missing else ""), flush=True)


def never_downloaded(years):
    """What was never downloaded: a year's lists, a listed bill's page, the rosters or a member's or committee's page.
    (A failed refresh with a last copy doesn't count; nor does a year with no bills listed yet, a bill page that answers
    404, or a roll call or text version.)"""
    out = []
    m = load(os.path.join(DATA, "members", "members.json"))
    if not m or m.get("missing"):
        out.append("members")
    c = load(os.path.join(DATA, "members", "committees.json"))
    if not c or c.get("missing"):
        out.append("committees")
    for year in years:
        folder = os.path.join(DATA, str(year))
        listing = load(os.path.join(folder, "list.json"))
        if not listing:
            if year < YEAR or (year == YEAR and TODAY.month > 2):
                out.append(f"{year}:lists")
            continue
        absent = (load(os.path.join(folder, "state.json")) or {}).get("absent", {})
        if any(not os.path.exists(os.path.join(folder, "bills", f"{k}.html")) and k not in absent
               for k in listing["bills"]):
            out.append(f"{year}:bills")
    return out


def main():
    os.makedirs(DATA, exist_ok=True)
    # Before the first copy, a run cut off without its summary leaves this, so a partial copy isn't published.
    if not ONLY and not any(name.isdigit() for name in os.listdir(DATA)):
        with open(MARKER, "w") as f:
            f.write("running\n")
    years = [ONLY] if ONLY else [YEAR, YEAR - 1, YEAR - 2]
    nxt = [YEAR + 1] if not ONLY and TODAY.month >= 11 else []  # next session's bills, once listed
    refused = False
    live = []
    try:
        if not ONLY:
            members()
        if not ONLY and not out_of_time():
            committees()
        for year in nxt + years:  # the newest first: lists and bill pages
            if out_of_time():
                break
            if session(year):
                live.append(year)
        if PDFTOTEXT:
            for year in live:
                if out_of_time():
                    break
                roll_calls(year)
        else:
            print("roll calls: pdftotext isn't installed (poppler-utils); not read", flush=True)
        for year in live:
            if out_of_time():
                break
            texts(year)
    except Refused as e:
        print(f"Stopped: the server refused a request ({e})", flush=True)
        refused = True
    missing = never_downloaded(years)
    print(f"run: {STATS['requests']} requests ({STATS['bills']} bills, {STATS['rolls']} roll calls, {STATS['texts']}"
          f" texts), {round((time.time() - START) / 60)} min"
          + ("; stopped at the time limit" if out_of_time() else "")
          + ("; refused" if refused else "")
          + (f"; request failures {dict(FAILS)}" if FAILS else "; no request failures")
          + (f"; never downloaded: {' '.join(missing)}" if missing else "; nothing missing"), flush=True)
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
