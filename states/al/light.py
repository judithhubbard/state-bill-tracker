"""Alabama's light history (states/light.py, states/LIGHT.md): the regular sessions before the shared window, from ALISON's
GraphQL endpoint (no robots.txt; fetch.py's pace, a second apart) with fetch.py's own read_bills() and read_history():
the session's bills (one request) and its whole history (a few pages), so about a minute a session. Left out: the
Budget Isolation Resolutions' and passages' roll calls (the converter reads stages from the history lines), texts and
introduced versions. The older years' wording goes through convert.py's old_wording() (written for 2023's)."""
import os, sys
from states import window as W

SOURCE = "alison.legislature.state.al.us GraphQL (Alabama Legislature)"
# One regular session a year ("<year>RS"), 2015 up to the window's first year.
SESSIONS = list(range(2015, W.first_year()))


def fetch(session, data):
    saved = sys.argv
    sys.argv = [saved[0]]  # (fetch.py reads its arguments when loaded)
    try:
        from states.al import fetch as F
    finally:
        sys.argv = saved
    F.DATA = data
    folder = os.path.join(data, str(session))
    os.makedirs(folder, exist_ok=True)
    state = {}
    s = f"{session}RS"
    bills = F.read_bills(s, folder, state)
    if not bills:
        print(f"al {session}: no bills", flush=True)
        return False
    F.read_history(s, folder, state)
    F.save(state, os.path.join(folder, "state.json"))
    return bool(state.get("bills") and state.get("history"))
