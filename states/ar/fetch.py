#!/usr/bin/env python3
"""Download Arkansas's bills from the Bureau of Legislative Research's file server (https://webftp.blr.arkansas.gov/;
the "Arkansas General Assembly Data" pages that arkleg.state.ar.us links its downloads to). The server has no
robots.txt (it answers 404), so nothing is barred; one request at a time, a second apart.

The server is a web page per folder ("/?folder=Assembly%2F2025"), listing each file's size ("6558386 B") and time
("11/8/2026 6:30:02 AM", the server's local clock: see listing_dates.py), with files at
"/Home/FTPDocument?path=<folder>%2F<name>". The data are pipe-delimited text files, UTF-16 with a byte-order mark and
CRLF line ends, one record a line, no header row (the columns are in ReadMeTextFileFields.txt, saved with them):
- LegislativeMeasures.txt: every bill and resolution: originating chamber (H/S), bill type (B, R, JR, CR, MR, CMR),
  number, subtitle (and the same cut into lines, Bill Subtitle 1-6), Bill ID (the database's own key, "ADF002"),
  sponsor, act number, introduction date, act date, original sponsor, measure number ("HB1001") and session ("2025R").
- ChamberActions.txt: the history: id, chamber, bill type, number, action stamp code ("V1" third reading and passed,
  "I1" referral, "E2" sent to the governor, "Z2" act number), date and time, the action as written ("Read the third
  time and passed and ordered transmitted to the Senate."), the house that acted (a column the read-me leaves out: it
  says H or S where the bill is, so a House bill's Senate passage is "S"), the roll call's number (RCS; floor votes
  only), measure number and session. The ids are not in date order (HB1001's act line has a lower id than its
  enrolling): sort by the time.
- BillSponsors.txt: id, chamber, bill type, number, sponsor ("L. Johnson", the members' Sponsor Name, or a committee),
  Bill ID (joins LegislativeMeasures; it has no session column, and numbers repeat across a biennium's sessions) and
  sponsor type. BillCodeCrossReference.txt: Bill ID and measure type ("HR").
- Amendments.txt (sponsor, chamber, introduced, PDF location, session), Engrossing.txt (measure number and date: no
  session), FloorCalendars.txt, CommitteeAgendas.txt (each meeting's bills), ScheduledMeetings.txt, AgendaWebLinks.txt,
  BillsInCommitteesWithFiscalImpacts.txt.
- LegislativeMembers.txt: member id, names, address, type (Senator/Representative), phone, district, seniority, fax,
  email, occupation, church, public service, veteran, state, party, Sponsor Name (the name the bill files and roll
  calls use: "J. Dismang"), status, web email, counties served. Committees.txt (name, code, type H/S/J..., parent, active,
  staff), CommitteeInformationChair.txt (committee, member id, designation: Chair, Co-Chair, Vice-Chair, Regular,
  Ex-Officio, Non-Voting, Alternate), CommitteeNonMembers.txt, CommitteesTypes.txt, House/SenateActionStamps.txt (the
  stamp codes' wording).
Some empty fields hold a NUL character ("\\x00") rather than nothing; they're saved as they are.

Where the files are. The top folder, SessionInformation/, is the live copy, rewritten every morning (every file's time
changes daily, whether or not anything did): during a session it holds that General Assembly's sessions so far; between
sessions its bill files are empty (two bytes, the byte-order mark; so on 2026-11-08), while its members, committees and
meetings stay filled. When a session is over a copy is kept under Assembly/<biennium>/<session>/SessionInformation/,
and each copy holds the whole biennium up to then (the Session ID column tells the sessions apart): the 2026 fiscal
session's (Assembly/2025/2026F, 2026-05-14) has 2025R, 2026F and 2026S1; the 2023 regular session's (Assembly/2023/
2023R, 2024-01-05) has 2023R and 2023S1. Not every session has a copy: 2025R, 2024F and 2024S2 don't, so the 2024
fiscal session (and 2024S2) isn't in these files at all: those are read from arkleg.state.ar.us's bill pages (below).

What's saved, in data/ar/<biennium>/ (the odd first year: 2025 is the 95th General Assembly, 2025-2026), converted to
UTF-8 with plain line ends, under the server's file names: each file from the newest place that has it filled in: the
live folder when its bills are this biennium's (or, between sessions, for this biennium's members and committees),
else the newest kept copy. seen.json records where each came from and its listing entry; a file is
downloaded again only when that changes. The bienniums read are the current one and the one before, and the next once
the live folder holds its bills (prefiling starts in November of even years).

Sessions with no kept copy, from arkleg.state.ar.us (the Legislature's site; its robots.txt allows everything to all
agents but ChatGPT's, with no crawl delay; read one request at a time, a second apart, with the same User-Agent). For a
finished biennium (before the current one), each session in the site's session list (the "ddBienniumSession" options:
"2023/2024F") that has no rows in the saved LegislativeMeasures.txt: for 2023-24, the 2024 fiscal session and the
second extraordinary session (2024S2). /Bills/SearchByRange?ddBienniumSession=2023%2F2024F lists the session's
measure types; for bills (HB, SB) and joint resolutions (HJR, SJR), /Bills/ViewBills?type=HB&... says the range ("begins
with HB1001 and goes through HB1097"), and each number's /Bills/Detail?id=HB1001&ddBienniumSession=2023%2F2024F is read
(a number that was never filed answers a page whose heading has no title: recorded as absent). Each bill goes into
data/ar/<biennium>/<session>/bills/<HB1001>.json, named like the files' columns so one converter reads both:
  Session ID, Measure Number, Originating Chamber (H/S), Bill Type (B, JR), Bill Number, Bill Subtitle (the page's
  heading; the same text as the file's subtitle), Bill Sponsor (the lead sponsor), Act Number, Introduction Date and Act
  Date (as "2024-04-03 08:49:17", the files' form without fractions of a second), Status (the page's status line), Bill
  ID (empty: the page doesn't show the database's key);
  sponsors: [{Sponsor, Sponsor Type}], Sponsor in the members' Sponsor Name form ("L. Johnson") or a committee's name
  ("Joint Budget Committee"); Sponsor Type is the page's label ("Lead Sponsor", "Other Primary Sponsor", "CoSponsors"),
  not the file's number;
  actions: ChamberActions-like rows, oldest first: {ID (empty), Chamber (the originating chamber, as in the file), Bill
  Type, Bill Number, Action Stamp (empty: the page has no codes), Action Datetime, Action, Action Chamber (H/S, the
  house that acted: the page's Chamber column, which matches the file's undocumented column), RCS Number (from the
  row's vote link), Measure Number, Session ID};
  amendments: [{Chamber, Amendment Number, Amendment Sponsor, Introduction Date}].
The page's history matches ChamberActions row for row (checked on HB1001 of 2025R), less the stamp codes and ids. A
finished session is read once: saved bills and absent numbers are skipped (state.json in the session folder), and the
session is marked finished when every number is read.

Members' votes (only with --votes): the files and pages carry only roll-call numbers. Each roll call is a page,
/Bills/Votes?id=HB1001&rcs=29&chamber=House&ddBienniumSession=2025%2F2025R (the RCS number and acting house from
ChamberActions, or from the bill JSON above), listing Yeas, Nays, Non Voting, Present and Excused by Sponsor Name
("F. Allen"), each with its count. One JSON per roll call in data/ar/<biennium>/votes/<2025R>-<H29>-<HB1001>.json
({session, chamber, rcs, bill, when (the page's heading: "Wednesday, January 22, 2025 1:48:07 PM"), counts: {Yeas: 99,
...}, names: {Yeas: [...], ...}}); a roll call number can appear on two bills, so the bill is part of the name. Each is
read once. About 2,900 roll calls in 2025-26 and 2,450 in 2023-24 (370 of them 2024F's and 2024S2's), at about 1.5
seconds each: about 2¼ hours for all. Missing votes don't mark the download incomplete.
Not anywhere: committee votes (Arkansas's committees mostly vote by voice; nothing is published) and any summary beyond
the subtitle.

data/ar/incomplete says "running" during a run and, after it, lists the files that were never downloaded and still
couldn't be (or the arkleg sessions' bills never read); a file whose download fails when a last copy exists keeps that
copy and doesn't count. It is removed when nothing is missing.
Usage: python3 states/ar/fetch.py [biennium] [--votes]   (default: the bienniums above; a single one leaves the marker
alone; --votes also reads members' votes, at most --votes=N roll calls when a number is given)
"""
import html, json, os, re, sys, time, urllib.error, urllib.parse, urllib.request
from collections import Counter
from datetime import date, datetime

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
from listing_dates import same  # noqa: E402

SERVER = "https://webftp.blr.arkansas.gov/"
LIVE = "SessionInformation"
DATA = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "ar"))
AGENT = "statebilltracker.org (a nonprofit bill tracker; contact via github.com/judithhubbard)"
TODAY = date.today()
CURRENT = TODAY.year - (TODAY.year + 1) % 2  # the biennium's odd first year
ARGS = [a for a in sys.argv[1:] if not a.startswith("--")]
ONLY = int(ARGS[0]) if ARGS else None
VOTES = next((a for a in sys.argv[1:] if a.startswith("--votes")), None)
VOTES_MAX = int(VOTES.split("=", 1)[1]) if VOTES and "=" in VOTES else None  # for trying it out on a few
SITE = "https://arkleg.state.ar.us"
TYPES = ("HB", "SB", "HJR", "SJR")  # bills, and joint resolutions (constitutional amendments, in regular sessions)
MARKER = os.path.join(DATA, "incomplete")
EMPTY = 8  # bytes: an empty file is the byte-order mark alone (2), perhaps with a line end
# The files of the sessions' bills and meetings. Between sessions the live folder's bill files are empty and its
# meeting files hold the interim committees' (CommitteeAgendas.txt: 1 MB, against the 2026 fiscal session's copy's 8
# MB), so these come from the kept copy then. The rest (members, committees, chairs, the stamp codes) are taken from
# the live folder for the current biennium even between sessions.
SESSION_FILES = {"LegislativeMeasures.txt", "ChamberActions.txt", "BillSponsors.txt", "BillCodeCrossReference.txt",
                 "Amendments.txt", "Engrossing.txt", "FloorCalendars.txt", "BillsInCommitteesWithFiscalImpacts.txt",
                 "CommitteeAgendas.txt", "AgendaWebLinks.txt", "ScheduledMeetings.txt"}

# The run's own time limit (FETCH_MINUTES, set by the workflow): stop a few minutes early, with everything read so far
# saved and a summary printed, rather than be cut off silently mid-request.
START = time.time()
BUDGET = max(0.0, float(os.environ.get("FETCH_MINUTES") or 0) - 5) * 60
FAILS = Counter()  # why requests failed, for the summary
STATS = {"requests": 0, "bytes": 0}
MISSING = set()  # files never downloaded that still couldn't be
FETCHED = {}  # the live LegislativeMeasures.txt, read once to see whose bills it holds


class Refused(Exception):
    """The server turned us away (401/403/429): stop the run."""


def out_of_time():
    return BUDGET and time.time() - START > BUDGET


def request(url, label):
    """GET url; the body, or None after three tries (or at once for a 404). Refused on 401/403/429."""
    for attempt in range(3):
        if out_of_time():
            return None
        time.sleep(1)
        STATS["requests"] += 1
        try:
            req = urllib.request.Request(url, headers={"User-Agent": AGENT})
            with urllib.request.urlopen(req, timeout=180) as r:
                body = r.read()
            STATS["bytes"] += len(body)
            return body
        except urllib.error.HTTPError as e:
            FAILS[f"HTTP {e.code}"] += 1
            if e.code in (401, 403, 429):
                raise Refused(f"{label}: HTTP {e.code}")
            if e.code == 404:
                return None
        except Exception as e:
            FAILS[type(e).__name__] += 1
        time.sleep(10 * (attempt + 1))
    print(f"{label}: failed three times", flush=True)
    return None


def save(obj, path):
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(obj, f, ensure_ascii=False, indent=0)
    os.replace(tmp, path)


def load(path, default):
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


ROW = re.compile(r'<a href="([^"]+)"[^>]*>\s*(.*?)\s*</a>\s*</td>\s*<td[^>]*>\s*(.*?)\s*</td>\s*<td>\s*(.*?)\s*</td>', re.S)


def listing(folder):
    """A folder's listing: ({file name: "<date> <time> <size>"}, [subfolder names]), or None if it can't be read."""
    body = request(SERVER + "?folder=" + urllib.parse.quote_plus(folder), f"listing {folder}")
    if body is None:
        return None
    text = body.decode("utf-8", "replace")
    if "Arkansas General Assembly Data" not in text:
        FAILS["not a listing"] += 1
        return None
    files, folders = {}, []
    for href, name, size, when in ROW.findall(text):
        href, name = html.unescape(href), html.unescape(name).strip()
        if "FTPDocument?path=" in href:
            files[name] = f"{' '.join(when.split())} {size.replace(' B', '').strip()}"
        elif href.startswith("?folder=") and name != "../":
            folders.append(name.rstrip("/"))
    return files, folders


def size(entry):
    return int(entry.rsplit(None, 1)[1]) if entry else 0


def when(entry):
    """A listing entry's time, for picking the newest copy."""
    try:
        return datetime.strptime(entry.rsplit(None, 1)[0], "%m/%d/%Y %I:%M:%S %p")
    except (ValueError, AttributeError):
        return datetime.min


def unchanged(old, new):
    """Whether two listing entries are the same file. listing_dates.same() reads times without seconds: the seconds
    must match, and the rest may be an hour apart (the server's clock across a daylight saving change)."""
    if old == new:
        return True
    if not old or not new:
        return False
    secs = re.compile(r"(\d+:\d+):(\d\d) ")
    so, sn = secs.search(old), secs.search(new)
    if not so or not sn or so.group(2) != sn.group(2):
        return False
    return same(secs.sub(r"\1 ", old, count=1), secs.sub(r"\1 ", new, count=1))


def decode(body):
    """A file's text: UTF-16 when it starts with the byte-order mark (all the data files), else UTF-8 (the read-mes)."""
    if body[:2] == b"\xff\xfe":
        text = body[2:].decode("utf-16-le")
    else:
        try:
            text = body.decode("utf-8-sig")
        except UnicodeDecodeError:
            text = body.decode("cp1252", "replace")
    return text.replace("\r\n", "\n")


def biennium_of(session):
    """"2026F" -> 2025; "2027R" -> 2027."""
    m = re.match(r"(\d{4})", session or "")
    if not m:
        return None
    year = int(m.group(1))
    return year - (year + 1) % 2


def sessions_in(text):
    """The Session IDs in a LegislativeMeasures file (its last column)."""
    return Counter(line.rsplit("|", 1)[-1].strip() for line in text.splitlines() if line.strip())


def kept_copies(biennium):
    """{file name: (folder, entry)} from the copies kept under Assembly/<biennium>/<session>/SessionInformation/, the
    newest of each; None if the biennium's folder can't be listed."""
    top = f"Assembly/{biennium}"
    got = listing(top)
    if got is None:
        return None
    best = {}
    for session in got[1]:
        if not re.fullmatch(r"\d{4}[A-Za-z]\d*", session):
            continue  # Documents, Member Pictures, ...
        sub = listing(f"{top}/{session}")
        if sub is None:
            return None
        if LIVE not in sub[1]:
            continue  # no copy kept for this session (2025R, 2024F)
        folder = f"{top}/{session}/{LIVE}"
        files = listing(folder)
        if files is None:
            return None
        for name, entry in files[0].items():
            if name not in best or when(entry) > when(best[name][1]):
                best[name] = (folder, entry)
    return best


def download(folder, name, entry, target, seen, label):
    """Download one file into target/<name> unless seen.json says this copy is already there. True when the file is
    there afterwards (new or kept)."""
    path = os.path.join(target, name)
    had = seen.get(name) or {}
    if os.path.exists(path) and had.get("from") == folder and unchanged(had.get("entry"), entry):
        return True
    if out_of_time():
        return os.path.exists(path)
    body = FETCHED.get(f"{folder}/{name}") or request(
        SERVER + "Home/FTPDocument?path=" + urllib.parse.quote_plus(f"{folder}/{name}"), f"{label} {name}")
    if body is not None and body.lstrip()[:15].lower().startswith((b"<!doctype", b"<html")):
        FAILS["a page, not a file"] += 1
        body = None
    if body is None:
        print(f"{label} {name}: not read" + ("; kept the last copy" if os.path.exists(path) else ""), flush=True)
        return os.path.exists(path)
    with open(path + ".tmp", "w", encoding="utf-8") as f:
        f.write(decode(body))
    os.replace(path + ".tmp", path)
    seen[name] = {"from": folder, "entry": entry, "read": datetime.now().isoformat(timespec="seconds")}
    print(f"{label} {name}: {len(body):,} bytes from {folder}", flush=True)
    return True


def biennium_run(biennium, live, live_biennium):
    """One biennium's files, each from the newest place that has it filled in. live is the live folder's listing."""
    label = str(biennium)
    target = os.path.join(DATA, str(biennium))
    os.makedirs(target, exist_ok=True)
    seen_path = os.path.join(target, "seen.json")
    seen = load(seen_path, {})
    kept = kept_copies(biennium)
    if kept is None:
        print(f"{label}: the kept copies couldn't be listed; kept the last copies", flush=True)
        kept = {}
        if not seen:
            MISSING.add(f"{biennium}:listing")
    # The live folder serves this biennium for every file when its bills are this biennium's; between sessions (its
    # bills empty), for the current biennium's members and committees.
    use_live = {}
    if live:
        if live_biennium == biennium:
            use_live = dict(live)
        elif live_biennium is None and biennium == CURRENT:
            use_live = {n: e for n, e in live.items() if n not in SESSION_FILES}
    names = sorted(set(kept) | set(use_live))
    for name in names:
        if not name.lower().endswith(".txt"):
            continue
        source = None
        if size(use_live.get(name)) > EMPTY or (name.startswith("ReadMe") and name in use_live):
            source = (LIVE, use_live[name])
        elif name in kept and (size(kept[name][1]) > EMPTY or name.startswith("ReadMe")):
            source = kept[name]
        if source is None:
            continue  # empty everywhere (no amendments yet in a new session)
        if not download(source[0], name, source[1], target, seen, label):
            MISSING.add(f"{biennium}:{name}")
        save(seen, seen_path)
    measures = os.path.join(target, "LegislativeMeasures.txt")
    if os.path.exists(measures):
        with open(measures, encoding="utf-8") as f:
            print(f"{label}: measures by session {dict(sorted(sessions_in(f.read()).items()))}", flush=True)
    else:
        print(f"{label}: no bills yet", flush=True)


def page(path, label):
    """An arkleg.state.ar.us page's text, or None."""
    body = request(SITE + path, label)
    return None if body is None else body.decode("utf-8", "replace")


def text_of(fragment):
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", fragment)).split())


def stamp(text):
    """"4/3/2024 8:49:17 AM" or "5/3/2024" -> "2024-04-03 08:49:17" or "2024-05-03" (the files' form)."""
    text = " ".join(text.replace("\xa0", " ").split())
    for f, out in (("%m/%d/%Y %I:%M:%S %p", "%Y-%m-%d %H:%M:%S"), ("%m/%d/%Y %I:%M %p", "%Y-%m-%d %H:%M:00"),
                   ("%m/%d/%Y", "%Y-%m-%d")):
        try:
            return datetime.strptime(text, f).strftime(out)
        except ValueError:
            pass
    return text


HOUSE = {"House": "H", "Senate": "S"}
FIELD = re.compile(r'aria-colindex="1" role="gridcell">([^<]*):</div>\s*<div class="col-md-8"[^>]*>(.*?)</div>\s*</div>',
                   re.S)


def bill_page(t, session, measure):
    """A bill's detail page as a record in the files' terms; None when the number was never filed."""
    m = re.search(r"<h1[^>]*>\s*([^<]*?)\s*</h1>", t)
    if not m or " - " not in m.group(1):
        return None
    kind, number = re.match(r"([A-Z]+)(\d+)", measure).groups()
    fields = {k.strip(): v for k, v in FIELD.findall(t)}
    origin = HOUSE.get(text_of(fields.get("Originating Chamber", "")), kind[0])
    rec = {"Session ID": session, "Measure Number": measure, "Originating Chamber": origin, "Bill Type": kind[1:],
           "Bill Number": number, "Bill Subtitle": html.unescape(m.group(1).split(" - ", 1)[1]).strip(), "Bill ID": "",
           "Bill Sponsor": text_of(fields.get("Lead Sponsor", "")),
           "Act Number": (re.findall(r"(\d+)\s*$", text_of(fields.get("Act Number", ""))) or [""])[0],
           "Introduction Date": stamp(text_of(fields.get("Introduction Date", ""))),
           "Act Date": stamp(text_of(fields.get("Act Date", ""))), "Status": text_of(fields.get("Status", ""))}
    rec["sponsors"] = [{"Sponsor": text_of(a), "Sponsor Type": label}
                       for label in ("Lead Sponsor", "Other Primary Sponsor", "CoSponsors")
                       for a in re.findall(r"<a [^>]*>(.*?)</a>", fields.get(label, ""), re.S)]
    # The history and amendments: each a grid of rows after its heading.
    sections = re.split(r"<h3>([^<]*)</h3>", t)
    part = {sections[i].strip(): sections[i + 1] for i in range(1, len(sections) - 1, 2)}
    rows = lambda chunk: re.split(r'<div class="row tableRow(?:Alt)?"[^>]*role="row">', chunk)[1:]
    actions = []
    for r in rows(part.get("Bill Status History", "")):
        cells = [text_of(c) for c in re.findall(r'role="gridcell">(.*?)</div>', r, re.S)]
        if len(cells) < 3:
            continue
        vote = re.search(r"rcs=(\d+)", r)
        actions.append({"ID": "", "Chamber": origin, "Bill Type": kind[1:], "Bill Number": number, "Action Stamp": "",
                        "Action Datetime": stamp(cells[1]), "Action": cells[2], "Action Chamber": HOUSE.get(cells[0], cells[0]),
                        "RCS Number": vote.group(1) if vote else "", "Measure Number": measure, "Session ID": session})
    rec["actions"] = actions[::-1]  # the page lists the newest first
    amendments = []
    for r in rows(part.get("Amendments", "")):
        cells = [text_of(c) for c in re.findall(r'role="gridcell">(.*?)</div>', r, re.S)]
        if len(cells) >= 4 and cells[0].startswith("Chamber:"):
            amendments.append({"Chamber": HOUSE.get(cells[0].split(":", 1)[1].strip(), cells[0]),
                               "Amendment Number": cells[1].split(":", 1)[-1].strip(), "Amendment Sponsor": cells[2],
                               "Introduction Date": stamp(cells[3])})
    rec["amendments"] = amendments
    return rec


def site_sessions(biennium):
    """The site's sessions of a biennium ("2024F"), from its session list; None if it can't be read."""
    t = page(f"/Bills/SearchByRange?ddBienniumSession={biennium}%2F{biennium}R", f"{biennium} sessions")
    if t is None:
        return None
    return sorted(set(re.findall(rf'<option value="{biennium}/(\d{{4}}[A-Z]\d*)"', t)))


def site_session(biennium, session):
    """Every bill of a session with no kept copy, from its bill pages; a finished session is read once."""
    folder = os.path.join(DATA, str(biennium), session)
    os.makedirs(os.path.join(folder, "bills"), exist_ok=True)
    state_path = os.path.join(folder, "state.json")
    state = load(state_path, {})
    if state.get("finished"):
        print(f"{session}: finished and fully read; nothing to do", flush=True)
        return
    ranges = state.setdefault("ranges", {})
    absent = set(state.get("absent") or [])
    q = f"ddBienniumSession={biennium}%2F{session}"
    t = page(f"/Bills/SearchByRange?{q}", f"{session} types")
    if t is None:
        MISSING.add(f"{session}:list")
        return
    types = [k for k in TYPES if f"type={k}&" in t]
    for kind in types:
        if kind in ranges:
            continue
        v = page(f"/Bills/ViewBills?type={kind}&{q}", f"{session} {kind} range")
        m = v and re.search(rf"begins with <b>{kind}(\d+)</b> and goes through <b>{kind}(\d+)</b>", v)
        if not m:
            MISSING.add(f"{session}:list")
            continue
        ranges[kind] = [int(m.group(1)), int(m.group(2))]
    save(state, state_path)
    todo = [f"{k}{n}" for k in types if k in ranges for n in range(ranges[k][0], ranges[k][1] + 1)]
    todo = [b for b in todo if b not in absent and not os.path.exists(os.path.join(folder, "bills", f"{b}.json"))]
    got = 0
    for measure in todo:
        if out_of_time():
            break
        t = page(f"/Bills/Detail?id={measure}&{q}", f"{session} {measure}")
        if t is None:
            continue
        rec = bill_page(t, session, measure)
        if rec is None:
            absent.add(measure)
        else:
            rec["read"] = datetime.now().isoformat(timespec="seconds")
            save(rec, os.path.join(folder, "bills", f"{measure}.json"))
        got += 1
        if got % 25 == 0:
            state["absent"] = sorted(absent)
            save(state, state_path)
    state["absent"] = sorted(absent)
    saved = len(os.listdir(os.path.join(folder, "bills")))
    if got == len(todo) and not MISSING & {f"{session}:list"}:
        state["finished"] = True
    else:
        MISSING.add(f"{session}:bills")
    save(state, state_path)
    print(f"{session}: {got} of {len(todo)} bill pages read; {saved} bills saved, {len(absent)} numbers never filed "
          f"(ranges {ranges})", flush=True)


def site_run(biennium):
    """A finished biennium's sessions that have no kept copy (no rows in the saved LegislativeMeasures.txt)."""
    if biennium >= CURRENT:
        return
    path = os.path.join(DATA, str(biennium), "LegislativeMeasures.txt")
    try:
        with open(path, encoding="utf-8") as f:
            have = set(sessions_in(f.read()))
    except OSError:
        return  # the files come first
    listed = site_sessions(biennium)
    if listed is None:
        if not any(os.path.isdir(os.path.join(DATA, str(biennium), s)) for s in os.listdir(os.path.join(DATA, str(biennium)))
                   if re.fullmatch(r"\d{4}[A-Z]\d*", s)):
            MISSING.add(f"{biennium}:sessions")
        return
    for session in listed:
        if session not in have:
            site_session(biennium, session)


def roll_calls(biennium):
    """(session, house, rcs, bill) of every roll call in a biennium's files and arkleg bill records."""
    out = set()
    path = os.path.join(DATA, str(biennium), "ChamberActions.txt")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            for line in f:
                r = [x.strip() for x in line.split("|")]
                if len(r) >= 11 and r[8].isdigit():
                    out.add((r[10], r[7], r[8], r[9]))
    for session in os.listdir(os.path.join(DATA, str(biennium))):
        bills = os.path.join(DATA, str(biennium), session, "bills")
        if os.path.isdir(bills):
            for name in os.listdir(bills):
                for a in load(os.path.join(bills, name), {}).get("actions") or []:
                    if a.get("RCS Number"):
                        out.add((a["Session ID"], a["Action Chamber"], a["RCS Number"], a["Measure Number"]))
    return sorted(out)


def votes_run(biennium, budget):
    """Members' votes, one page per roll call, each read once. Returns how many were read."""
    folder = os.path.join(DATA, str(biennium), "votes")
    os.makedirs(folder, exist_ok=True)
    calls = roll_calls(biennium)
    todo = [c for c in calls if not os.path.exists(os.path.join(folder, f"{c[0]}-{c[1]}{c[2]}-{c[3]}.json"))]
    if budget is not None:
        todo = todo[:budget]
    got = 0
    for session, house, rcs, bill in todo:
        if out_of_time():
            break
        chamber = {"H": "House", "S": "Senate"}.get(house, house)
        t = page(f"/Bills/Votes?id={bill}&rcs={rcs}&chamber={chamber}&ddBienniumSession={biennium}%2F{session}",
                 f"{session} {bill} {house}{rcs}")
        heading = t and re.search(r"<h1>\s*(?:House|Senate) Vote - ([^<]*?)\s*</h1>", t)
        if not heading:
            FAILS["vote page without a vote"] += 1
            continue
        counts, names = {}, {}
        parts = re.split(r'<b style="font-size:23px;">\s*([A-Za-z ]+):\s*(\d+)\s*</b>', t)
        for i in range(1, len(parts) - 2, 3):
            group = parts[i].strip()
            counts[group] = int(parts[i + 1])
            chunk = re.split(r"<div class=\"row\">|<b style=", parts[i + 2])[0] if counts[group] else ""
            names[group] = [text_of(c) for c in re.findall(r'role="gridcell">(.*?)</div>', chunk, re.S)]
        save({"session": session, "chamber": house, "rcs": rcs, "bill": bill, "when": heading.group(1),
              "counts": counts, "names": names}, os.path.join(folder, f"{session}-{house}{rcs}-{bill}.json"))
        got += 1
        if got % 100 == 0:
            print(f"{biennium} votes: {got} of {len(todo)}, {round((time.time() - START) / 60)} min", flush=True)
    print(f"{biennium} votes: {got} of {len(todo)} read ({len(calls)} roll calls)", flush=True)
    return got


def main():
    os.makedirs(DATA, exist_ok=True)
    whole = not os.path.exists(MARKER)  # the last run left nothing missing
    # A run cut off by its time limit leaves this, so a partial copy isn't published (cleared after a clean run).
    if not ONLY and not os.path.exists(MARKER):
        with open(MARKER, "w") as f:
            f.write("running\n")
    try:
        # The live folder: whose bills it holds decides which biennium it serves.
        got = listing(LIVE)
        live, live_biennium = (got[0] if got else None), None
        if got is None:
            print("live folder: couldn't be listed; using the kept copies", flush=True)
        elif size(live.get("LegislativeMeasures.txt")) > EMPTY:
            body = request(SERVER + "Home/FTPDocument?path=" + urllib.parse.quote_plus(f"{LIVE}/LegislativeMeasures.txt"),
                           "live LegislativeMeasures.txt")
            if body is None:
                live = None  # can't tell whose it is: use the kept copies this time
            else:
                FETCHED[f"{LIVE}/LegislativeMeasures.txt"] = body
                sessions = sessions_in(decode(body))
                live_biennium = max((biennium_of(s) for s in sessions if biennium_of(s)), default=None)
                print(f"live folder: measures by session {dict(sessions)}", flush=True)
        else:
            print("live folder: no bills (between sessions)", flush=True)
        bienniums = [CURRENT, CURRENT - 2]
        if live_biennium and live_biennium not in bienniums:
            bienniums.insert(0, live_biennium)  # next biennium's prefiled bills
        for biennium in bienniums:
            if ONLY and biennium != ONLY:
                continue
            biennium_run(biennium, live, live_biennium)
            site_run(biennium)
        if VOTES:
            budget = VOTES_MAX
            for biennium in bienniums:
                if ONLY and biennium != ONLY:
                    continue
                got = votes_run(biennium, budget)
                if budget is not None:
                    budget -= got
    except Refused as e:
        print(f"Stopped: the server refused a request ({e})", flush=True)
        if not whole:  # a refusal stops a first copy; once whole, the last copies stay
            MISSING.add("refused")
    if out_of_time():
        print("stopped at the time limit", flush=True)
    print(f"run: {STATS['requests']} requests, {STATS['bytes'] / 1e6:.1f} MB, {round((time.time() - START) / 60)} min"
          + ("; stopped at the time limit" if out_of_time() else "")
          + (f"; request failures {dict(FAILS)}" if FAILS else "; no request failures")
          + (f"; never downloaded: {' '.join(sorted(MISSING))}" if MISSING else ""), flush=True)
    if ONLY:
        return
    if MISSING:
        with open(MARKER, "w") as f:
            f.write(" ".join(sorted(MISSING)) + "\n")
    elif os.path.exists(MARKER):
        os.remove(MARKER)


if __name__ == "__main__":
    main()
