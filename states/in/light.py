"""Indiana's light history (states/light.py, states/LIGHT.md): the sessions before the shared window, from the General
Assembly's API (api.iga.in.gov, which lists every regular session from 2009), with fetch.py's own bills() and people():
the session's bill list, all its actions and roll-call tallies (three answers), each House and Senate bill and joint
resolution's detail (about 1,300-1,600 a long session, 800-1,000 a short one), then the legislators and standing
committees (about 200). 0.6 seconds apart, as fetch.py: about 20-25 minutes a session. Needs INDIANA_API_KEY. Agendas
are left out."""
import importlib, sys
from states import window as W

SOURCE = "api.iga.in.gov (Indiana General Assembly, MyIGA API 2.0)"
# One regular session a year (long in odd years, short in even), 2015 up to the window's first year.
SESSIONS = list(range(2015, W.first_year()))


def fetch(session, data):
    saved = sys.argv
    sys.argv = [saved[0]]  # (fetch.py reads its first year from the command line when loaded)
    try:
        F = importlib.import_module("states.in.fetch")  # ("in" is a Python keyword: no plain import)
    finally:
        sys.argv = saved
    if not F.key():
        print("in: no Indiana API key (INDIANA_API_KEY)", flush=True)
        return False
    F.DATA = data
    F.LIST_FALLBACK = True
    done = F.bills(session)
    F.people(session)
    return bool(done)
