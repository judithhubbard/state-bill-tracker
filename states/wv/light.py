"""West Virginia's light history (states/light.py, states/LIGHT.md): the regular sessions before the shared window
(2015-2022), from www.wvlegislature.gov's bill status pages (robots.txt allows /Bill_Status/) with fetch.py's own
session() and members(): the session's lists (all bills, joint resolutions, completed legislation with its Acts
chapters, the governor's actions, the roll-call list: about 9 pages) and each bill's history page (about 1,800-2,300 a
year, a second apart: 30-45 minutes), and today's members (the converter reads sponsors' parties from them, as it does
for the window's past years; a name no longer sitting has none). The roll-call PDFs and the drafters' notes ("What it
does", one request per text version) are left out: the history lines carry each floor vote's tally, and the light
records keep the short titles. Not tried from the owner's computer (the server didn't answer it on 2026-11-24, while
GitHub's runners read it daily): the first run is the check that 2015's pages have today's shape."""
import os, sys
from states import window as W

SOURCE = "www.wvlegislature.gov/Bill_Status (West Virginia Legislature: lists and bill histories)"
# One regular session a year, 2015 up to the window's first year.
SESSIONS = list(range(2015, W.first_year()))


def fetch(session, data):
    saved = sys.argv
    sys.argv = [saved[0], str(session)]  # (fetch.py reads ONLY, a single year, from the command line when loaded)
    try:
        from states.wv import fetch as F
    finally:
        sys.argv = saved
    F.DATA, F.MARKER = data, os.path.join(data, "incomplete")
    try:
        F.members()
        if not F.session(session):
            print(f"wv {session}: no bills listed", flush=True)
            return False
    except F.Refused as e:
        print(f"wv {session}: the server refused a request ({e})", flush=True)
        return False
    missing = [m for m in F.never_downloaded([session]) if m not in ("members", "committees")]
    if missing:
        print(f"wv {session}: not downloaded: {' '.join(missing)}", flush=True)
    return not missing
