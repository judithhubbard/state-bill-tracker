"""North Dakota's light history (states/light.py, states/LIGHT.md): the Legislative Assemblies before the shared window,
from the Legislative Council's API with fetch.py's own functions: the assembly's five files (bills, roll calls, members,
committees, sessions; one request each, a second apart) and the Session Laws' bill index (chapters). Minutes, member
pages, texts and fiscal notes are left out. A session is the assembly's first year (2015 is the 64th)."""
import os, sys
from states import window as W

SOURCE = "ndlegis.gov /api/assembly/<n-year>/data (Legislative Council)"
# Assemblies start in odd years.
SESSIONS = [y for y in range(2015, W.first_year()) if y % 2]


def fetch(session, data):
    saved = sys.argv
    sys.argv = [saved[0]]  # (fetch.py reads its year from the command line when loaded)
    try:
        from states.nd import fetch as F
    finally:
        sys.argv = saved
    F.DATA, F.MARKER, F.FIRST_YEAR, F.ONLY = data, os.path.join(data, "incomplete"), session, session
    F.MEMBERS, F.BIOS = os.path.join(data, "members"), os.path.join(data, "bios.json")
    found = F.assemblies()
    if not found:
        print(f"nd {session}: no such assembly", flush=True)
        return False
    a = found[0]
    folder = os.path.join(data, str(a["year"]))
    state = {}
    if not F.data_files(a, folder, state):
        return False
    F.chapters(a, folder, state)
    return os.path.exists(os.path.join(folder, "bills.json"))
