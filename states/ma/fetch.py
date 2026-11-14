#!/usr/bin/env python3
"""Download Massachusetts's bills from the Legislature's API (https://malegislature.gov/api/; swagger at /api/swagger;
robots.txt allows everything; see the state-survey-2026-10-31 memory).

- Each General Court's document list (every bill with its sponsor, co-sponsors and title); House and Senate bills
  only (not docket filings that never got a bill number).
- Each bill's history (DocumentHistoryActions) into data/ma/<court>/bills/<H1234>.json. A finished General Court's are
  read once; the current one's bills are read again when the list shows a change, or every run for bills with
  recent activity.
- The members (with emails and phones), committees, leadership and session laws.
Three requests at a time. Usage: python3 states/ma/fetch.py [first_year]   (default: the General Court before this one)
"""
import json, os, sys, time, urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import date

API = "https://malegislature.gov/api"
DATA = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "ma"))
AGENT = "statebilltracker.org (a nonprofit bill tracker; contact via github.com/judithhubbard)"
YEAR = date.today().year
CURRENT = YEAR if YEAR % 2 else YEAR - 1
FIRST = int(sys.argv[1]) if len(sys.argv) > 1 else CURRENT - 2
INCOMPLETE = set()


def begun(session):
    """Whether a General Court has convened (the first Wednesday of January of its first year)."""
    return date.today() >= date(session, 1, 1 + (2 - date(session, 1, 1).weekday()) % 7)


def court_of(session):
    """2025 -> 194."""
    return (session - 1637) // 2


def get(url):
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": AGENT, "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=180) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            time.sleep(5 * (attempt + 1))
        except Exception:
            time.sleep(5 * (attempt + 1))
    return False


def save(path, data):
    json.dump(data, open(path + ".tmp", "w"), ensure_ascii=False)
    os.replace(path + ".tmp", path)


def session(session):
    gc = court_of(session)
    folder = os.path.join(DATA, str(session))
    os.makedirs(os.path.join(folder, "bills"), exist_ok=True)
    docs = get(f"{API}/GeneralCourts/{gc}/Documents")
    if not docs:
        print(f"{session}: no document list; kept the last copy")
        if not os.path.exists(os.path.join(folder, "documents.json")):  # only a list never read holds the state off
            INCOMPLETE.add(session)
        return
    bills = {d["BillNumber"]: d for d in docs if (d.get("BillNumber") or "")[:1] in ("H", "S") and d["BillNumber"][1:].isdigit()}
    save(os.path.join(folder, "documents.json"), list(bills.values()))
    live = session >= CURRENT

    def one(b):
        path = os.path.join(folder, "bills", f"{b}.json")
        if os.path.exists(path) and not live:
            return True
        if os.path.exists(path) and live:
            old = json.load(open(path))
            # Bills with nothing for 60 days are read again once a week (Mondays); others every run.
            last = max((a.get("Date") or "" for a in old), default="")
            if last < (date.fromordinal(date.today().toordinal() - 60)).isoformat() and date.today().weekday() != 0:
                return True
        h = get(f"{API}/GeneralCourts/{gc}/Documents/{b}/DocumentHistoryActions")
        if h is False:
            return False
        save(path, h or [])
        return True

    got = 0
    with ThreadPoolExecutor(3) as pool:
        for ok in pool.map(one, sorted(bills)):
            got += ok
    # A few bills whose history the API fails on every time mustn't hold back the whole state (Ohio's HB 178 trap):
    # incomplete only when more than 1% were never read (a bill whose refresh failed keeps its last copy).
    have = sum(os.path.exists(os.path.join(folder, "bills", f"{b}.json")) for b in bills)
    if have < 0.99 * len(bills):
        INCOMPLETE.add(session)
    print(f"{session}: {got} of {len(bills)} bills read", flush=True)
    for name, url in (("members", f"{API}/GeneralCourts/{gc}/LegislativeMembers"),
                      ("committees", f"{API}/GeneralCourts/{gc}/Committees"),
                      ("leadership_house", f"{API}/GeneralCourts/{gc}/Branches/House/Leadership"),
                      ("leadership_senate", f"{API}/GeneralCourts/{gc}/Branches/Senate/Leadership")):
        d = get(url)
        if d:
            save(os.path.join(folder, f"{name}.json"), d)
    for y in (session, session + 1):
        d = get(f"{API}/SessionLaws/{y}") if y <= YEAR else None
        if d:
            save(os.path.join(folder, f"laws_{y}.json"), [{k: v for k, v in x.items() if k != "ChapterText"} for x in d])


def rollcalls(session):
    """The Senate's roll calls (each member's vote), into data/ma/<session>/senate_rollcalls.json: number -> record.
    The histories cite them ("see Roll Call #215"); the House's aren't in the API (its histories give the tallies)."""
    gc = court_of(session)
    path = os.path.join(DATA, str(session), "senate_rollcalls.json")
    try:
        have = json.load(open(path))
    except (OSError, ValueError):
        have = {}
    listing = get(f"{API}/GeneralCourts/{gc}/Branches/Senate/RollCalls") or []
    todo = [r["RollCallNumber"] for r in listing if str(r["RollCallNumber"]) not in have or session >= CURRENT and r["RollCallNumber"] > max(map(int, have or [0])) - 5]
    with ThreadPoolExecutor(3) as pool:
        for num, rc in zip(todo, pool.map(lambda n: get(f"{API}/GeneralCourts/{gc}/Branches/Senate/RollCalls/{n}"), todo)):
            if rc:
                have[str(num)] = {k: ([x.get("MemberCode") for x in v] if isinstance(v, list) else v) for k, v in rc.items()}
    os.makedirs(os.path.dirname(path), exist_ok=True)
    save(path, have)
    print(f"{session}: {len(have)} Senate roll calls ({len(todo)} read now)")


def main():
    os.makedirs(DATA, exist_ok=True)
    sys.path.insert(0, os.path.normpath(os.path.join(DATA, "..", "..")))
    from states.ma import contacts
    for s in range(FIRST, CURRENT + 1, 2):
        session(s)
        rollcalls(s)
        if s < CURRENT and not os.path.exists(os.path.join(DATA, str(s), "member_details.json")):
            contacts.details(s)
    try:
        contacts.main(CURRENT)
    except SystemExit as e:
        print(e)
    marker = os.path.join(DATA, "incomplete")
    # A General Court not yet begun (no documents filed yet) is read when it's there but never holds Massachusetts back.
    undone = {s for s in INCOMPLETE if begun(s)}
    if undone:
        open(marker, "w").write(" ".join(map(str, sorted(undone))) + "\n")
    elif os.path.exists(marker):
        os.remove(marker)


if __name__ == "__main__":
    main()
