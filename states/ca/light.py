"""California's light history (states/light.py, states/LIGHT.md): the two-year sessions before the shared window (2015,
2017, 2019), each from its own pubinfo_<year>.zip with fetch.py's save(): only the tables are read out of the zip (HTTP
range requests, states/ca/pubinfo.py), plus the veto messages and each bill's latest digest (texts.update), which the
converter reads as the summary. The zips are 0.8-1.2 GB; the tables and digests come to a few hundred MB of ranges."""
import sys
from email.utils import parsedate_to_datetime

SOURCE = "downloads.leginfo.legislature.ca.gov pubinfo_<year>.zip (California Legislative Counsel)"
# Two-year sessions, named by their first (odd) year; the window keeps CA from 2021.
SESSIONS = [2015, 2017, 2019]


def fetch(session, data):
    saved = sys.argv
    sys.argv = [saved[0]]  # (fetch.py reads its first session from the command line when loaded)
    try:
        from states.ca import fetch as F
        from states.ca import profile as P
    finally:
        sys.argv = saved
    # save() and texts.update() write under P.DATA: the scratch folder (states/light.py puts the real one back after).
    P.DATA = data
    url = f"{F.BASE}/pubinfo_{session}.zip"
    h = F.head(url)
    if not h:
        print(f"ca {session}: {url} not found", flush=True)
        return False
    # (save() writes into the folder of the session its bill table names.)
    return F.save(url, parsedate_to_datetime(h[1]).isoformat()) == session
