"""Missouri's light history (states/light.py, states/LIGHT.md): the regular sessions before the shared window, with
fetch.py's own functions. The House side is the session's past-exports zip (documents.house.mo.gov/xml/<yy>1.zip, listed
on XMLPastExports.html back to 2013): every House bill's XML with both houses' actions, the members and the lists, two
requests at the House's 20-second Crawl-delay. The Senate side is senate.mo.gov: the year's bill list, then each Senate
bill's page and its actions (two requests a bill, about 1,000-1,400 a session, a second apart), and the year's
committees. Journals (member votes), the House's summary PDFs and the Senate's committee vote reports are left out, so
House bills have no summary. About 30-45 minutes a session. The current senators' list (members/senate.json) isn't read:
past senators' parties come from what the Senate's pages say."""
import os, sys
from states import window as W

SOURCE = "documents.house.mo.gov past exports (Missouri House) and senate.mo.gov bill pages (Missouri Senate)"
# One regular session a year, 2015 up to the window's first year.
SESSIONS = list(range(2015, W.first_year()))


def fetch(session, data):
    saved = sys.argv
    sys.argv = [saved[0], str(session)]  # (fetch.py reads ONLY, a single year, from the command line when loaded)
    try:
        from states.mo import fetch as F
    finally:
        sys.argv = saved
    F.DATA, F.MARKER, F.ONLY = data, os.path.join(data, "incomplete"), session
    zips = F.past_zips()
    if not (zips or {}).get(session):
        print(f"mo {session}: no House zip listed", flush=True)
        return False
    F.house_zip(session, zips)
    F.senate_year(session)
    missing = [m for m in F.never_downloaded([session]) if m != "senators"]
    if missing:
        print(f"mo {session}: not downloaded: {' '.join(missing)}", flush=True)
    return not missing
