"""Delaware's light history (states/light.py, states/LIGHT.md): the General Assemblies before the shared window (the
148th, 2015-16, to the 151st, 2021-22), from legis.delaware.gov's own JSON and pages (no robots.txt) with fetch.py's
own assembly_lists(), people() and assembly(): the Assembly's bill and substitute list (about 40 pages), its members and
committees, each member's page (about 65: the old member lists have no party), and each bill's page, actions and committee reports (three requests a bill, a second apart: about 750-1,000
bills, roughly an hour an Assembly). The roll-call lists and roll calls are left out: the actions carry each floor
vote's tally ("Passed By House. Votes: 39 YES 1 NO 1 ABSENT"). The 148th's answers have today's shape (checked
2026-11-24: its list, 736 bills, and HB 450's actions); their passage lines are worded the old way ("Passed in House",
"Passed by Senate. Votes: Passed 21 YES ..."), which convert.py's old_wording() reads as today's."""
import os, sys
from states import window as W

SOURCE = "legis.delaware.gov (Delaware General Assembly: bill list, pages and actions)"
# 2015, 2017, 2019, 2021: each Assembly by its first year, up to the window's first.
SESSIONS = list(range(2015, W.first_session(), 2))


def fetch(session, data):
    saved = sys.argv
    sys.argv = [saved[0]]
    try:
        from states.de import fetch as F
    finally:
        sys.argv = saved
    F.DATA, F.MARKER = data, os.path.join(data, "incomplete")
    ga = 153 + (session - 2025) // 2
    real_grid = F.grid
    # (No roll calls in a light file: the roll-call list isn't asked for, so none are read.)
    F.grid = lambda path, *a, **k: [] if "GetVotingReportsByLegislationId" in path else real_grid(path, *a, **k)
    try:
        F.assembly_lists(ga)
        # (The old member lists have no party: the converter takes it from each member's page heading, "(D)".)
        F.people([ga])
        F.assembly(ga)
    finally:
        F.grid = real_grid
    missing = F.missing(ga)
    if missing:
        print(f"de {session}: not downloaded: {' '.join(missing)}", flush=True)
    return not missing
