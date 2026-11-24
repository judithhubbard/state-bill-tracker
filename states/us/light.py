"""Congress's light history (states/light.py, states/LIGHT.md): the 114th to 116th Congresses (2015-2020), before the
window's 117th, from GovInfo's BILLSTATUS bulk data with fetch.py's own bills() (each Congress's four zips: House and
Senate bills and joint resolutions, about 100 MB together; a finished Congress has no updates to read) and members()
(the congress-legislators files, whose historical list names every member). Roll calls and veto messages are left out.
Six requests a Congress, a couple of seconds apart: a few minutes each."""
import os, sys

SOURCE = "govinfo.gov/bulkdata/BILLSTATUS (Government Publishing Office) and congress-legislators"
# Sessions are named by a Congress's first year, as convert.py's sessions(): the 114th is 2015.
SESSIONS = [2015, 2017, 2019]


def fetch(session, data):
    saved = sys.argv
    sys.argv = [saved[0]]  # (fetch.py reads the Congresses from the command line when loaded)
    try:
        from states.us import fetch as F
        from states.us import profile as P
    finally:
        sys.argv = saved
    F.DATA = data
    congress = P.congress_of(session)
    del F.missing[:]
    F.bills(congress)
    F.members()
    if F.missing:
        print(f"us {session}: not downloaded: {', '.join(F.missing)}", flush=True)
        return False
    return all(os.path.exists(os.path.join(data, str(congress), f"BILLSTATUS-{congress}-{t}.zip")) for t in F.TYPES)
