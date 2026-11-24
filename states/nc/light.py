"""North Carolina's light history (states/light.py, states/LIGHT.md): the two-year sessions before the shared window, from
ncleg.gov with fetch.py's own session(): the session's All Bills feed (one request) and each bill's page
(/BillLookup/<year>/<num>, about 2,000-2,300 a session), at robots.txt's 2-second crawl delay, so about 70-80 minutes a
session. Left out: the roll-call transcripts (the converter reads stages from each bill's history; its votes only list
names), so a past session's members.json (made from the roll calls' names) isn't written and sponsors carry no party;
member biographies, summaries, veto letters and agendas. Checked 2026-11-24: 2015's feed (2,053 entries) and bill pages
(H97, S2) read with today's parse_bill()."""
import os, sys
from states import window as W

SOURCE = "ncleg.gov All Bills feed and bill pages (North Carolina General Assembly)"
# Two-year sessions, named by their first year.
SESSIONS = [y for y in range(2015, W.first_session()) if y % 2]


def fetch(session, data):
    saved = sys.argv
    sys.argv = [saved[0]]  # (fetch.py reads its first year from the command line when loaded)
    try:
        from states.nc import fetch as F
    finally:
        sys.argv = saved
    F.DATA = data
    F.INCOMPLETE.clear()
    real_get = F.get
    # (No roll-call transcripts or biographies: a light file keeps no votes, and these would double the requests.)
    F.get = lambda url, *a, **k: None if ("/RollCallVoteTranscript/" in url or "/Members/Biography/" in url) \
        else real_get(url, *a, **k)
    try:
        F.session(session)
    finally:
        F.get = real_get
    folder = os.path.join(data, str(session))
    return os.path.exists(os.path.join(folder, "list.json")) and \
        not any(g in (f"{session}:list", f"{session}:bills") for g in F.INCOMPLETE)
