"""Connecticut's light history (states/light.py, states/LIGHT.md): the yearly sessions before the window's first (2022),
from the FTP archive's flat files with fetch.py's own flat_year() (bill_info, bill_history, introducer, subject and the
legislator spreadsheet: five files, a few MB) and texts() (the statements of purpose, the converter's summaries). The
old years have no comm_ref, committee or actions files, as for 2023. Journals (floor votes) and veto messages are left
out. A minute a session."""
import os, sys, time

SOURCE = "ftp.cga.ct.gov/pub/data/archive flat files (Connecticut General Assembly)"
# One session a year (long in odd years, short in even), 2015 up to the first year the site keeps (2022).
SESSIONS = list(range(2015, 2022))


def fetch(session, data):
    saved = sys.argv
    sys.argv = [saved[0]]  # (fetch.py reads its first year from the command line when loaded)
    try:
        from states.ct import fetch as F
        from states.ct import profile as P
    finally:
        sys.argv = saved
    # flat_year() and texts() write under P.DATA: the scratch folder (states/light.py puts the real one back after).
    P.DATA = data
    folder = os.path.join(data, str(session))
    os.makedirs(folder, exist_ok=True)
    # The FTP server often times out from GitHub's runners (2026-11-24: the archive's listing failed for 2016-2018, and
    # 2015 and 2019-2021 each lost a file or two, so nothing was written). The files are named by year, so the listing
    # isn't needed: flat_year() asks for each file, and only the missing ones again, a few rounds a minute apart.
    marker = os.path.join(data, f"incomplete_{session}")
    for attempt in range(5):
        if attempt:
            time.sleep(60)
        F.flat_year(session, folder)
        if not os.path.exists(marker):
            break
    missing = open(marker).read().split() if os.path.exists(marker) else []
    if missing and all(m.endswith(":LegislatorData") for m in missing):
        # (The legislator spreadsheet only gives sponsors' parties: without it the session is written with none.)
        print(f"ct {session}: no legislator spreadsheet after 5 tries; written without sponsors' parties", flush=True)
        os.remove(marker)
    elif missing:
        print(f"ct {session}: still missing {' '.join(missing)} after 5 tries", flush=True)
        return False
    F.texts()
    return True
