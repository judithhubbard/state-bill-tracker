"""Kentucky's light history (states/light.py, states/LIGHT.md): the regular sessions before the shared window, from the
LRC's static bill record (apps.legislature.ky.gov/record/<yy>rs/, no robots.txt) with fetch.py's own session(): the
record page, the index and status lists (about 15 pages) and each bill's and joint resolution's page (about 800-1,300 a
session), one a second, so about 15-25 minutes a session. Left out: members and committees (the site lists only today's,
so old sponsors are matched to today's members where they still serve, as the converter does), vote-history and veto
PDFs, agendas. Checked 2026-11-24: 15rs's record (last regenerated 2019-01-16) and HB 1's page have today's layout. The
record goes back to 2012 (06rs answers 404)."""
import os, sys
from states import window as W

SOURCE = "apps.legislature.ky.gov/record/<yy>rs/ (Kentucky Legislative Research Commission)"
# One regular session a year, 2015 up to the window's first year.
SESSIONS = list(range(2015, W.first_year()))


def fetch(session, data):
    saved = sys.argv
    sys.argv = [saved[0]]  # (fetch.py reads its arguments when loaded)
    try:
        from states.ky import fetch as F
    finally:
        sys.argv = saved
    F.DATA = data
    F.REFRESH_MAX = 10 ** 6
    F.BUDGET = 0  # (no time limit inside a session: the workflow's own limit applies)
    F.session(session)
    state = F.load(os.path.join(data, str(session), "state.json"), {}) or {}
    return bool(state.get("complete"))
