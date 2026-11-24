"""Alaska's light history (states/light.py, states/LIGHT.md): the Legislatures before the shared window (the 29th, 2015-16,
to the 32nd, 2021-22), from the BASIS public service (akleg.gov/publicservice/, which robots.txt allows) with fetch.py's
own legislature_run(): the sessions, the roster, the bill list and each House and Senate bill's and constitutional
amendment's record (sponsors, actions, committee actions, subjects, referrals, floor votes: one request each, about 900-
1,200 a Legislature), a second apart, so about 30-45 minutes a Legislature. Left out: sponsor statements (PDFs on
get_documents.asp), bill texts and fiscal notes (/PDF/, barred). A session is the Legislature's first year (2015 is the
29th)."""
import os, sys
from states import window as W

SOURCE = "akleg.gov/publicservice/basis (Alaska Legislature's BASIS public service)"
# Two-year Legislatures, named by their first year.
SESSIONS = [y for y in range(2015, W.first_session()) if y % 2]


def fetch(session, data):
    saved = sys.argv
    sys.argv = [saved[0]]  # (fetch.py reads its Legislature from the command line when loaded)
    try:
        from states.ak import fetch as F
    finally:
        sys.argv = saved
    F.DATA = data
    F.BUDGET = 0  # (no time limit inside a Legislature: the workflow's own limit applies)
    legislature = 29 + (session - 2015) // 2
    problems = F.legislature_run(legislature)
    if problems:
        print(f"ak {session}: {problems}", flush=True)
    return not any(p.endswith((":list", ":bills")) for p in problems)
