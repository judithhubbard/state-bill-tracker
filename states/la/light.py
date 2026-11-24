"""Louisiana's light history (states/light.py, states/LIGHT.md): the regular sessions before the shared window, from
legis.la.gov (no robots.txt; fetch.py's pace, one request a second) with fetch.py's own session(): the bill lists (a page
per 100 numbers), the vetoed list and the constitutional amendments' list (about 15-30 pages), then each bill's page
(BillInfo.aspx: authors, status, the history with tallies and the governor's actions), about 1,000-2,300 a session, so
about 20-40 minutes. Left out: the documents (floor-vote, digest and veto-message PDFs: the converter's stages come from
the history lines), members, committees, agendas. Regular sessions only ("15RS"), as now."""
import os, sys
from states import window as W

SOURCE = "legis.la.gov bill lists and BillInfo pages (Louisiana State Legislature)"
# One regular session a year (general in even years, fiscal in odd), 2015 up to the window's first year.
SESSIONS = list(range(2015, W.first_year()))


def fetch(session, data):
    saved = sys.argv
    sys.argv = [saved[0]]  # (fetch.py reads its arguments when loaded)
    try:
        from states.la import fetch as F
    finally:
        sys.argv = saved
    F.DATA = data
    F.BUDGET = 0  # (no time limit inside a session: the workflow's own limit applies)
    F.session(session)
    folder = os.path.join(data, str(session))
    listing = F.load(os.path.join(folder, "list.json")) or {}
    rows = listing.get("bills") or {}
    state = F.load(os.path.join(folder, "state.json"), {}) or {}
    absent = state.get("absent") or {}
    return bool(rows) and all(os.path.exists(os.path.join(folder, "bills", f"{k}.json")) or k in absent for k in rows)
