"""Mississippi's light history (states/light.py, states/LIGHT.md): the regular sessions before the shared window, from
billstatus.ls.state.ms.us with fetch.py's own session(): the year's lists (all measures, committees, author lists) and
each House and Senate bill and concurrent resolution's history file (about 3,500-4,000 a year, a second apart: about 80
minutes a session), then the current members (fetch.py's members(), about 180 files; the converter takes parties from
them, as it does for the window's past years). Roll-call PDFs and veto messages are left out."""
import os, sys
from states import window as W

SOURCE = "billstatus.ls.state.ms.us (Mississippi Legislature bill status XML)"
# One regular session a year, 2015 up to the window's first year.
SESSIONS = list(range(2015, W.first_year()))


def fetch(session, data):
    saved = sys.argv
    sys.argv = [saved[0], str(session)]  # (fetch.py reads ONLY, a single year, from the command line when loaded)
    try:
        from states.ms import fetch as F
    finally:
        sys.argv = saved
    F.DATA, F.ONLY = data, session
    F.MARKER, F.CA = os.path.join(data, "incomplete"), os.path.join(data, "ca.pem")
    F.CONTEXT = F.ca_bundle()
    F.members()
    F.session(session)
    missing = [m for m in F.never_downloaded([session]) if not m.startswith("members:")]
    if missing:
        print(f"ms {session}: not downloaded: {' '.join(missing)}", flush=True)
    return not missing
