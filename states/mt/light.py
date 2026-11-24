"""Montana's light history (states/light.py, states/LIGHT.md): the regular sessions before the shared window, from the
api.legmt.gov archive (archive/v1: the format convert.py's steps_archive() reads, as for 2023), with fetch.py's own
functions: the session's members and committees, then each bill type's list pages (every bill with its actions,
sponsors and subjects). Ten seconds between requests (api.legmt.gov's robots.txt: Crawl-delay 10); about 20-40 requests
a session. Bill texts and veto letters (docs.legmt.gov) are left out."""
import os, sys
from states import window as W

SOURCE = "api.legmt.gov archive/v1 (Montana Legislature)"
# Regular sessions meet in odd years.
SESSIONS = [y for y in range(2015, W.first_year()) if y % 2]


def fetch(session, data):
    saved = sys.argv
    sys.argv = [saved[0]]  # (fetch.py reads its year from the command line when loaded)
    try:
        from states.mt import fetch as F
    finally:
        sys.argv = saved
    F.DATA, F.MARKER, F.FIRST_YEAR, F.ONLY = data, os.path.join(data, "incomplete"), session, session
    found = [s for s in F.sessions() if s["year"] == session]
    if not found or not found[0]["archive"]:
        print(f"mt {session}: not in the archive's session list", flush=True)
        return False
    F.session_lists(found[0])
    folder = os.path.join(data, str(session))
    state = F.load(os.path.join(folder, "state.json"), {})
    return bool(state.get("listed")) and os.path.isdir(os.path.join(folder, "bills"))
