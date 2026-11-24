"""Nevada's light history (states/light.py, states/LIGHT.md): the regular sessions (odd years) before the shared window
(the 78th, 2015, to the 81st, 2021), from NELIS with fetch.py's own lists(), overviews(), members() and committees():
the session's bill lists (one page a kind), the laws and vetoed lists, each bill's Overview tab (history, sponsors,
digest: about 1,100-1,300 a session, a second apart, the server taking about 1.7 seconds each: 35-60 minutes), the
members (with party) and the standing committees. Votes member by member (four or five requests a bill), the committee
minutes and the veto messages (under /Reports/, which robots.txt bars) are left out: the history lines carry each floor
vote's tally and result. NELIS serves 2015 in today's shape (checked 2026-11-24: the 78th's AB list, 498 bills, and AB
1's Overview). Special sessions are left out, as now."""
import os, sys
from states import window as W

SOURCE = "NELIS, www.leg.state.nv.us/App/NELIS/REL/<session>/ (Nevada Legislature)"
# The 78th (2015), 79th (2017), 80th (2019) and 81st (2021), up to the window's first.
SESSIONS = list(range(2015, W.first_session(), 2))


def fetch(session, data):
    saved = sys.argv
    sys.argv = [saved[0], str(session)]  # (fetch.py reads ONLY, a single year, from the command line when loaded)
    try:
        from states.nv import fetch as F
    finally:
        sys.argv = saved
    F.DATA, F.MARKER = data, os.path.join(data, "incomplete")
    folder = os.path.join(data, str(session))
    os.makedirs(folder, exist_ok=True)
    state = {}
    try:
        listing = F.lists(session, folder, state)
        if not listing:
            print(f"nv {session}: no bill list", flush=True)
            return False
        F.overviews(session, folder, state, listing)
        F.members(session, folder, state, False)
        F.committees(session, folder, state)
    except F.Refused as e:
        print(f"nv {session}: the server refused a request ({e})", flush=True)
        return False
    F.save(state, os.path.join(folder, "state.json"))
    missing = F.never_downloaded([session])
    if missing:
        print(f"nv {session}: not downloaded: {' '.join(missing)}", flush=True)
    return not missing
