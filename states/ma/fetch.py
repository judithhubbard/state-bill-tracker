#!/usr/bin/env python3
"""Download Massachusetts's bills from the Legislature's API (https://malegislature.gov/api/; swagger at /api/swagger;
robots.txt allows everything; see the state-survey-2026-10-31 memory).

- Each General Court's document list (every bill with its sponsor, co-sponsors and title); House and Senate bills
  only (not docket filings that never got a bill number).
- Each bill's history (DocumentHistoryActions) into data/ma/<court>/bills/<H1234>.json. A finished General Court's are
  read once; the current one's bills are read again when the list shows a change, or every run for bills with
  recent activity.
- The members (with emails and phones), committees, leadership and session laws.
- The Senate's roll calls (API) and the House's (the House Journal's yearly PDF of them: states/ma/house_votes.py).
- Committee hearings and the bills on their agendas (hearings(): data/ma/hearings.json, <session>/agendas.json).
Three requests at a time. Usage: python3 states/ma/fetch.py [first_year]   (default: the shared window's first session, states/window.py: from 2023-24 until 2029)
"""
import json, os, re, sys, time, urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import date
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
from states import window as W

API = "https://malegislature.gov/api"
DATA = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "ma"))
AGENT = "statebilltracker.org (a nonprofit bill tracker; contact via github.com/judithhubbard)"
YEAR = date.today().year
CURRENT = YEAR if YEAR % 2 else YEAR - 1
FIRST = int(sys.argv[1]) if len(sys.argv) > 1 else W.first_session()
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
            # A General Court with nothing public yet (January) answers 400 "Could not locate any public Documents in
            # General Court "195"." (its members and roll calls likewise): not there, like a 404, not worth retrying.
            if e.code == 404 or e.code == 400 and b"Could not locate" in e.read()[:500]:
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
    docs = get(f"{API}/GeneralCourts/{gc}/Documents")
    if not docs:
        print(f"{session}: no document list; kept the last copy")
        # Only a list never read holds the state off; not a new General Court's, which lists nothing until its first
        # bills are numbered (most in February), while the last court stays on the site.
        new = session == CURRENT and os.path.exists(os.path.join(DATA, str(session - 2), "documents.json"))
        if not os.path.exists(os.path.join(folder, "documents.json")) and not new:
            INCOMPLETE.add(session)
        return
    os.makedirs(os.path.join(folder, "bills"), exist_ok=True)
    bills = {d["BillNumber"]: d for d in docs if (d.get("BillNumber") or "")[:1] in ("H", "S") and d["BillNumber"][1:].isdigit()}
    save(os.path.join(folder, "documents.json"), list(bills.values()))
    # The last court too until March 1: its final informal sessions run into the new court's first week of January,
    # and the governor acts on what they passed in the ten days after.
    live = session >= CURRENT or session == CURRENT - 2 and date.today() < date(CURRENT, 3, 1)

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


FIRST_HEARINGS = 150  # with no cache yet, read only this many of the newest hearings (ids rise as hearings are posted)
NEW_HEARINGS_MAX = 300  # new hearings read in one run at most


def committee_label(name):
    """ "Joint Committee on Environment and Natural Resources" -> "Joint Environment and Natural Resources";
    "House Committee on Ways and Means" -> "House Ways and Means"."""
    name = " ".join((name or "").split())
    m = re.match(r"(Joint|House|Senate) Committee on (?:the )?(.+)$", name)
    return f"{m.group(1)} {m.group(2)}" if m else name


def hearings():
    """Bills on upcoming committee hearings' agendas, into data/ma/<session>/agendas.json: {"H892": [["Joint
    Environment and Natural Resources", "2025-10-21T13:00:00"], ...]}. /api/Hearings lists every hearing's id (about
    4,300 in November 2026, no dates); /api/Hearings/<id> gives its committee (HearingHost), status ("Confirmed",
    "Completed", "Canceled", "Rescheduled"), date and the bills on its agenda (HearingAgendas' DocumentsInAgenda,
    with BillNumber). Each hearing read is kept in data/ma/hearings.json ({"floor", "hearings": {id: {d, s, n, c, gc,
    b}}}); a run reads the hearings not yet kept from the floor up (the first run's newest FIRST_HEARINGS: ids rise as
    hearings are posted, so older ones are past; at most NEW_HEARINGS_MAX a run) and again those dated from yesterday on
    (agendas are filled in and hearings canceled or moved up to the day). Only today to three weeks ahead goes into
    agendas.json; a failure keeps the last files and never marks the state incomplete."""
    import datetime as dt
    path = os.path.join(DATA, "hearings.json")
    try:
        kept = json.load(open(path))
    except (OSError, ValueError):
        kept = {}
    have = kept.get("hearings") or {}
    listing = get(f"{API}/Hearings")
    if not listing:
        print("hearings: no list; kept the last files", flush=True)
        return
    ids = sorted({int(h["EventId"]) for h in listing if h.get("EventId")})
    # Hearings below the floor (older than the first run's newest FIRST_HEARINGS) are never read.
    floor = kept.get("floor") or (ids[-FIRST_HEARINGS] if len(ids) >= FIRST_HEARINGS else (ids or [0])[0])
    new = [i for i in ids if i >= floor and str(i) not in have][:NEW_HEARINGS_MAX]
    yesterday = (date.today() - dt.timedelta(days=1)).isoformat()
    again = [int(k) for k, v in have.items() if (v.get("d") or "") >= yesterday and int(k) not in new]
    failed = 0

    def one(i):
        return i, get(f"{API}/Hearings/{i}")

    with ThreadPoolExecutor(3) as pool:
        for i, h in pool.map(one, again + new):
            if h is None:  # gone (404)
                have.pop(str(i), None)
                continue
            if h is False:
                failed += 1
                continue
            host = h.get("HearingHost") or {}
            bills = []
            for a in h.get("HearingAgendas") or []:
                for d in a.get("DocumentsInAgenda") or []:
                    b = d.get("BillNumber") or ""
                    if re.fullmatch(r"[HS]\d+", b) and b not in bills:
                        bills.append(b)
            have[str(i)] = {"d": h.get("StartTime") or h.get("EventDate") or "", "s": h.get("Status") or "",
                            "n": committee_label(h.get("Name")), "c": host.get("CommitteeCode"),
                            "gc": host.get("GeneralCourtNumber"), "b": bills}
    save(path, {"floor": floor, "hearings": have})
    today, last = date.today().isoformat(), (date.today() + dt.timedelta(days=21)).isoformat()
    by_session = {}
    for i, v in have.items():
        when = v.get("d") or ""
        if not (today <= when[:10] <= last) or re.match(r"cancel|resched|postpon", v.get("s") or "", re.I) or not v.get("gc"):
            continue
        out = by_session.setdefault(1637 + 2 * int(v["gc"]), {})
        entry = [v["n"], when if "T" in when else when[:10] + "T00:00:00"]
        for b in v["b"]:
            if entry not in out.setdefault(b, []):
                out[b].append(entry)
    for s in sorted(set(by_session) | {CURRENT}):
        if os.path.isdir(os.path.join(DATA, str(s))):
            save(os.path.join(DATA, str(s), "agendas.json"), by_session.get(s, {}))
    print(f"hearings: {len(new)} new and {len(again)} upcoming read ({failed} failed); "
          f"{sum(len(o) for o in by_session.values())} bills on upcoming agendas", flush=True)


def main():
    os.makedirs(DATA, exist_ok=True)
    sys.path.insert(0, os.path.normpath(os.path.join(DATA, "..", "..")))
    from states.ma import contacts, house_votes
    for s in range(FIRST, CURRENT + 1, 2):
        session(s)
        if os.path.exists(os.path.join(DATA, str(s), "documents.json")):  # (not a new court with nothing listed yet)
            rollcalls(s)
            try:  # the House's roll calls by member (states/ma/house_votes.py): never hold the run back
                house_votes.fetch(s, os.path.join(DATA, str(s)))
            except Exception as e:
                print(f"{s}: House roll calls: stopped ({type(e).__name__}: {e}); kept the last copy", flush=True)
        if s < CURRENT and not os.path.exists(os.path.join(DATA, str(s), "member_details.json")):
            contacts.details(s)
    try:
        contacts.main(CURRENT)
    except SystemExit as e:
        print(e)
    try:  # committee hearings' agendas: never hold the run back
        hearings()
    except Exception as e:
        print(f"hearings: stopped ({type(e).__name__}: {e}); kept the last files", flush=True)
    marker = os.path.join(DATA, "incomplete")
    # A General Court not yet begun (no documents filed yet) is read when it's there but never holds Massachusetts back.
    undone = {s for s in INCOMPLETE if begun(s)}
    if undone:
        open(marker, "w").write(" ".join(map(str, sorted(undone))) + "\n")
    elif os.path.exists(marker):
        os.remove(marker)


if __name__ == "__main__":
    main()
