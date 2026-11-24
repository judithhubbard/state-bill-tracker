"""Ohio's light history (states/light.py, states/LIGHT.md): the General Assemblies before the site's first full one
(the 134th, 2021-22), from the Legislative Service Commission's API with fetch.py's own session(): the Assembly's
legislation list (one call), each House and Senate bill's (and amendment resolution's) versions and actions (two calls
a bill, three at a time: about 2,800 calls an Assembly, 20-40 minutes), its legislators and committees. The 131st's
answers have the same shape as the 136th's (checked 2026-11-24: HB 64's list entry and actions). The LSC's analyses
("What it does") and the members' pages are left out: the light records keep the long titles."""
import os, sys

SOURCE = "search-prod.lis.state.oh.us/api/v2 (Ohio Legislative Service Commission)"
# The 131st (2015-16), 132nd (2017-18) and 133rd (2019-20); the site keeps the 134th on.
SESSIONS = [2015, 2017, 2019]


def fetch(session, data):
    saved = sys.argv
    sys.argv = [saved[0], str(session)]  # (fetch.py reads its first year from the command line when loaded)
    try:
        from states.oh import fetch as F
        from states.oh import profile as P
    finally:
        sys.argv = saved
    P.DATA = data  # (fetch.py writes under P.DATA: the scratch folder; states/light.py puts the real one back after)
    F.INCOMPLETE.discard(session)
    F.session(session)
    folder = os.path.join(data, str(session))
    ok = session not in F.INCOMPLETE and all(os.path.exists(os.path.join(folder, n))
                                             for n in ("legislation.json", "legislators.json"))
    if not ok:
        print(f"oh {session}: not downloaded completely", flush=True)
    return ok
