"""Connecticut's light history (states/light.py, states/LIGHT.md): the yearly sessions before the window's first (2022),
from the FTP archive's flat files with fetch.py's own flat_year() (bill_info, bill_history, introducer, subject and the
legislator spreadsheet: five files, a few MB) and texts() (the statements of purpose, the converter's summaries). The
old years have no comm_ref, committee or actions files, as for 2023. Journals (floor votes) and veto messages are left
out. A minute a session."""
import os, sys

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
    if f"{session}bill_info.csv" not in F.archive():
        print(f"ct {session}: no flat files in the archive", flush=True)
        return False
    folder = os.path.join(data, str(session))
    os.makedirs(folder, exist_ok=True)
    F.flat_year(session, folder)
    if os.path.exists(os.path.join(data, f"incomplete_{session}")):
        return False  # (window.mark() names what's still missing)
    F.texts()
    return True
