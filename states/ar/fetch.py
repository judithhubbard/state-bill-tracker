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
fiscal session (and 2024S2) isn't in these files at all. It's on arkleg.state.ar.us's bill pages only (not read).

What's saved, in data/ar/<biennium>/ (the odd first year: 2025 is the 95th General Assembly, 2025-2026), converted to
UTF-8 with plain line ends, under the server's file names: each file from the newest place that has it filled in: the
live folder when its bills are this biennium's (or, between sessions, for this biennium's members and committees),
else the newest kept copy. seen.json records where each came from and its listing entry; a file is
downloaded again only when that changes. The bienniums read are the current one and the one before, and the next once
the live folder holds its bills (prefiling starts in November of even years).

Not in the files: members' votes (only roll-call numbers), committee votes (Arkansas's committees mostly vote by voice;
nothing is published), and any summary beyond the subtitle. Members' votes are on arkleg.state.ar.us, whose robots.txt
allows everything to all agents but ChatGPT's: a page per roll call, /Bills/Votes?id=HB1001&rcs=29&chamber=House&
ddBienniumSession=2025%2F2025R (the RCS number and house from ChamberActions), listing Yeas, Nays, Non Voting, Present
and Excused by Sponsor Name ("L. Johnson"); about 2,900 in 2025-26. Not read yet.

data/ar/incomplete says "running" during a run and, after it, lists the files that were never downloaded and still
couldn't be; a file whose download fails when a last copy exists keeps that copy and doesn't count. It is removed when
nothing is missing.
Usage: python3 states/ar/fetch.py [biennium]   (default: the bienniums above; a single one leaves the marker alone)
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
ONLY = int(sys.argv[1]) if len(sys.argv) > 1 else None
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


def main():
    os.makedirs(DATA, exist_ok=True)
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
    except Refused as e:
        print(f"Stopped: the server refused a request ({e})", flush=True)
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
