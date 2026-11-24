"""Georgia's light history (states/light.py, states/LIGHT.md): the regular sessions (two years each) before the shared
window, from the General Assembly's SOAP web services with fetch.py's own session(): the session's legislation list,
each House and Senate bill's (and amendment resolution's) detail (status history with dates, sponsors, committees, act
or veto number: about 1,600-2,400 calls a session, three at a time), and the members and committees with their
details (about 300 calls). The services list every session back to 2001-02 (GetSessions; checked 2026-11-24 with 2015's
list and HB 170's detail: the same shape and status codes as now). Members' votes (GetVote, one call each) are left out:
the light records keep each floor vote's tally from the detail. The governor's veto messages aren't read."""
import os, sys
from states import window as W

SOURCE = "webservices.legis.ga.gov GGAServices (Georgia General Assembly)"
# 2015-16, 2017-18, 2019-20, 2021-22: two-year sessions, by their first year, up to the window's first.
SESSIONS = list(range(2015, W.first_session(), 2))


def fetch(session, data):
    saved = sys.argv
    sys.argv = [saved[0]]
    try:
        from states.ga import fetch as F
    finally:
        sys.argv = saved
    F.DATA = data
    ids = F.session_ids()
    if session not in ids:
        print(f"ga {session}: no regular session listed", flush=True)
        return False
    real = F.call
    # (Members' votes aren't kept in a light file: the GetVote calls are skipped.)
    F.call = lambda service, op, *a, **k: None if service == "Votes" else real(service, op, *a, **k)
    try:
        F.session(session, ids[session])
    finally:
        F.call = real
    missing = sorted(m for m in F.INCOMPLETE if m.startswith(f"{session}:"))
    if missing:
        print(f"ga {session}: not downloaded: {' '.join(missing)}", flush=True)
    return not missing
