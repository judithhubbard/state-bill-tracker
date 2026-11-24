"""South Dakota's light history (states/light.py, states/LIGHT.md): the sessions before the shared window, from the
Legislature's JSON API (sdlegislature.gov/api, no key), with fetch.py's own session(): the bill list and every action
log (two answers), each House and Senate bill and joint resolution's detail and versions (two requests a bill, about
900-1,100 a session), the members, committees and the BillLogs lists. Members' votes (Votes/<id>, two to three thousand
a session) are left out: the converter reads the action logs' results and tallies without them. Then the LRC's Title
Summaries where the session list names one. A second apart, as fetch.py: about 20 minutes a session."""
import os, sys
from states import window as W

SOURCE = "sdlegislature.gov/api (South Dakota Legislative Research Council)"
# One regular session a year, 2015 up to the window's first year.
SESSIONS = list(range(2015, W.first_year()))


def fetch(session, data):
    saved = sys.argv
    sys.argv = [saved[0]]  # (fetch.py reads its first year from the command line when loaded)
    try:
        from states.sd import fetch as F
        from states.sd import summaries as S
    finally:
        sys.argv = saved
    F.DATA = S.DATA = data
    ids = F.session_ids()
    if session not in ids:
        print(f"sd {session}: no regular session listed", flush=True)
        return False
    real_get = F.get
    # (Member votes aren't kept in a light file: their requests are skipped, and the converter reads none.)
    F.get = lambda path, *a, **k: None if path.startswith("Votes/") else real_get(path, *a, **k)
    try:
        F.session(session, ids[session])
        S.run(real_get, [session])
    finally:
        F.get = real_get
    folder = os.path.join(data, str(session))
    return all(os.path.exists(os.path.join(folder, n)) for n in ("bills.json", "status.json", "members.json")) \
        and not any(g.startswith(f"{session}:bills") or g.startswith(f"{session}:list") for g in F.INCOMPLETE)
