#!/usr/bin/env python3
"""Every New York download, in download.yml's "New York" job (since 2026-11-22; before, publish.yml copied what
albanybilltracker.org's repository committed and downloaded only the current bills). Run on GitHub, never on the owner's
computer: three of the steps read nyassembly.gov a page at a time.

In order (each step's failure is noted and the next still runs):
1. states/ny/memos.py: the Assembly sponsors' memos (data/ny/assembly_memos_<session>.json), for the current session
   and, in November and December of even years, the next one's prefiled bills. At most about 12 minutes a run; a new
   session's first copy fills in over several runs.
2. fetch_bills.py --if-changed: the current session's bills (data/bills_<session>.json, senate_memos_<session>.json,
   texts_<session>.json), downloaded again only when the Senate's API lists an update. Also the next session's prefiled
   bills (November and December of even years: its page is <year>.html, "upcoming"), and the session just ended through
   February 15 of odd years (the governor's late actions), or whenever its file is missing.
3. fetch_assembly_votes.py: Assembly floor votes for bills that passed since last checked (data/assembly_votes_<session>.json).
4. fetch_agendas.py: Senate and Assembly committee agendas (data/agendas_<session>.json).
5. fetch_contacts.py: committees, chairs, members and links (data/contacts_<session>.json), once a day.

The files live in this job's Actions cache (.github/states.json's "paths"); the copies kept in git (contacts, Assembly
votes, past sessions' bills_<year>.json.gz) are the starting point when the cache is empty. A file whose contents didn't
change gets its old modification time back, so download.yml saves the cache only when something really changed.
Problems for check_fresh.py (run by check_site.py once a day) go to data/ny/problems.txt.

Exits 1 only when the current session's bills didn't download (then download.yml doesn't mark the copy as checked).
Usage: python3 states/ny/fetch.py
"""
import glob, hashlib, json, os, subprocess, sys
from datetime import datetime
from zoneinfo import ZoneInfo

HERE = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
DATA = os.path.join(HERE, "data")
OWN = os.path.join(DATA, "ny")
PROBLEMS = os.path.join(OWN, "problems.txt")
NOW = datetime.now(ZoneInfo("America/New_York"))
CURRENT = NOW.year if NOW.year % 2 else NOW.year - 1
PREV = CURRENT - 2
# Prefiled bills for the next session: November and December of even years.
NEXT = CURRENT + 2 if NOW.year % 2 == 0 and NOW.month >= 11 else None


def files():
    return sorted(glob.glob(os.path.join(DATA, "*.json")) + glob.glob(os.path.join(OWN, "*")))


def digest(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def step(name, args, minutes, env=None):
    """Runs one script; True if it finished without error."""
    print(f"\n== {name}", flush=True)
    try:
        r = subprocess.run([sys.executable] + args, cwd=HERE, timeout=minutes * 60, env={**os.environ, **(env or {})})
    except subprocess.TimeoutExpired:
        print(f"{name}: stopped after {minutes} minutes", flush=True)
        return False
    if r.returncode:
        print(f"{name}: failed (exit {r.returncode})", flush=True)
    return r.returncode == 0


def main():
    os.makedirs(OWN, exist_ok=True)
    before = {p: (digest(p), os.stat(p)) for p in files() if os.path.isfile(p)}
    problems = []
    # fetch_agendas.py adds its own lines here (an Assembly agenda page with meetings but no bills).
    open(PROBLEMS, "w").close()
    env = {"PROBLEMS_FILE": PROBLEMS}

    # 1. The Assembly memos first, so "What it does" (written by fetch_bills.py) has the newest.
    for s in [CURRENT] + ([NEXT] if NEXT else []):
        step(f"Assembly memos {s}", ["states/ny/memos.py", str(s)], 15, {"FETCH_MINUTES": "17"})

    # 2. Bills from the Senate's Open Legislation API.
    ok = step(f"Bills {CURRENT}", ["fetch_bills.py", str(CURRENT), "--if-changed"], 10)
    if not ok:
        problems.append(f"The {CURRENT} bills didn't download from the Senate's API (fetch_bills.py).")
    if NEXT:
        step(f"Prefiled bills {NEXT}", ["fetch_bills.py", str(NEXT), "--if-changed"], 10) or print("Prefiled bills didn't download")
    have_prev = any(os.path.exists(os.path.join(DATA, f"bills_{PREV}.json{x}")) for x in ("", ".gz"))
    if not have_prev or (NOW.year % 2 and (NOW.month, NOW.day) <= (2, 15)):
        step(f"Bills {PREV} (the session just ended)", ["fetch_bills.py", str(PREV), "--if-changed"], 10)

    # 3. Assembly floor votes (nyassembly.gov), for bills that passed the Assembly since last checked.
    if os.path.exists(os.path.join(DATA, f"bills_{CURRENT}.json")):
        step(f"Assembly votes {CURRENT}", ["fetch_assembly_votes.py", str(CURRENT)], 12)

    # 4. Committee agendas; they matter only while committees meet (January to June).
    if not step(f"Committee agendas {CURRENT}", ["fetch_agendas.py", str(CURRENT)], 6, env) and NOW.month <= 6:
        problems.append("Committee agendas didn't download.")

    # 5. Contacts, once a day.
    cpath = os.path.join(DATA, f"contacts_{CURRENT}.json")
    try:
        fresh = json.load(open(cpath)).get("fetched") == NOW.strftime("%Y-%m-%d")
    except (OSError, ValueError):
        fresh = False
    if fresh:
        print("\n== Contacts: already refreshed today")
    elif not step(f"Contacts {CURRENT}", ["fetch_contacts.py", str(CURRENT)], 10):
        print("Contacts refresh failed; the last copy is kept")

    with open(PROBLEMS, "a") as f:
        f.writelines(p + "\n" for p in problems)
    # Files rewritten with the same contents keep their old time.
    same = 0
    for p, (h, st) in before.items():
        if os.path.isfile(p) and digest(p) == h:
            os.utime(p, ns=(st.st_atime_ns, st.st_mtime_ns))
            same += 1
    changed = [os.path.relpath(p, DATA) for p in files() if os.path.isfile(p) and (p not in before or digest(p) != before[p][0])]
    print(f"\n{len(changed)} files changed{': ' + ', '.join(changed) if changed else ''}; {same} unchanged")
    if problems:
        print("Problems:\n" + "\n".join(f"- {p}" for p in problems))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
