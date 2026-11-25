"""Wisconsin's light history (states/light.py, states/LIGHT.md): the two-year sessions before the shared window (2015-16
to 2021-22), from docs.legis.wisconsin.gov (robots.txt bars only /feed/, /search, /frame/ and the like) with fetch.py's
own session() and members_and_committees(): the Assembly and Senate bill lists (and the joint resolutions proposing
constitutional amendments), each bill's history page and its Legislative Reference Bureau analysis ("What it does"):
two requests a bill, a second apart, about 1,700-2,000 bills a session (about an hour), then the members (with party)
and committees. The roll calls member by member, the committee records and the veto messages are left out: the
history lines carry each floor vote's tally ("Ayes 53, Noes 45") and the acts. The 2015 session's pages have today's
shape (checked 2026-11-24: the Assembly's bill list, 1,026 bills, and AB 21's history)."""
import os, sys
from states import window as W

SOURCE = "docs.legis.wisconsin.gov (Wisconsin Legislature: bill histories, LRB analyses, members)"
# 2015, 2017, 2019, 2021: each session by its first year, up to the window's first.
SESSIONS = list(range(2015, W.first_session(), 2))
# (The LRB analysis, /related/proposals/, left out too since 2026-11-25: from GitHub's machines each page took about 8
# seconds, so a session needed more than a run's 340 minutes; the light records keep the titles, "lacks" says summary.)
SKIP = ("/related/votes/", "/related/records/", "/vetomessages/", "/related/proposals/")


def fetch(session, data):
    saved = sys.argv
    sys.argv = [saved[0], str(session)]  # (fetch.py reads its first year from the command line when loaded)
    try:
        from states.wi import fetch as F
    finally:
        sys.argv = saved
    F.DATA = data
    real = F.get
    # (No roll calls, committee records or veto messages in a light file: their pages aren't asked for.)
    F.get = lambda path, *a, **k: None if any(s in path for s in SKIP) else real(path, *a, **k)
    try:
        F.session(session)
    finally:
        F.get = real
    missing = sorted(m for m in F.INCOMPLETE if m.startswith(f"{session}:"))
    if missing:
        print(f"wi {session}: not downloaded: {' '.join(missing)}", flush=True)
    return not missing
