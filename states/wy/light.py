"""Wyoming's light history (states/light.py, states/LIGHT.md): the sessions before the shared window, read with fetch.py's
own functions (the year's bill list, each bill in full, the members and committees) into a scratch folder, one request at
a time, a second apart. Veto letters, agendas and contacts are left out."""
import os, sys
from states import window as W

SOURCE = "lsoservice.wyoleg.gov /api/BillInformation (LSO)"
# One session a year (general in odd years, budget in even), 2015 up to the window's first year.
SESSIONS = list(range(2015, W.first_year()))


def fetch(session, data):
    saved = sys.argv
    sys.argv = [saved[0]]  # (fetch.py reads its year from the command line when loaded)
    try:
        from states.wy import fetch as F
    finally:
        sys.argv = saved
    F.DATA, F.MARKER = data, os.path.join(data, "incomplete")
    folder = os.path.join(data, str(session))
    os.makedirs(folder, exist_ok=True)
    F.members(session, folder, False)
    F.committees(session, folder, False)
    n = F.bills(session, folder, False)
    return bool(n) and os.path.isdir(os.path.join(folder, "bills"))
