"""Idaho's light history (states/light.py, states/LIGHT.md): the regular sessions before the shared window, from
legislature.idaho.gov (robots.txt bars only /wp-admin/ and the committee calendar's views) with fetch.py's own session():
the year's legislation page (every bill's status, the Enacted Legislation table with chapters and signing dates, the
vetoed bills) and each House and Senate bill's and joint resolution's page (about 550-700 a year), plus the year's
standing committees' pages (about 25), one a second, so about 12-15 minutes a session. Left out: statements of purpose
(PDFs), member pages, agendas."""
import os, sys
from states import window as W

SOURCE = "legislature.idaho.gov /sessioninfo/<year>/ (Idaho Legislature)"
# One regular session a year, 2015 up to the window's first year.
SESSIONS = list(range(2015, W.first_year()))


def fetch(session, data):
    saved = sys.argv
    sys.argv = [saved[0]]  # (fetch.py reads its arguments when loaded)
    try:
        from states.id import fetch as F
    finally:
        sys.argv = saved
    F.DATA = data
    F.BUDGET = 0  # (no time limit inside a session: the workflow's own limit applies)
    F.session(session)
    folder = os.path.join(data, str(session))
    listing = F.load(os.path.join(folder, "list.json")) or {}
    want = [k for k in listing.get("bills") or {} if F.KIND.match(k)]
    return bool(want) and all(os.path.exists(os.path.join(folder, "bills", f"{k}.html")) for k in want)
