"""New Mexico's light history (states/light.py, states/LIGHT.md): the regular sessions before the shared window, from
www.nmlegis.gov with fetch.py's own functions: the session's legislation list (one page), each House and Senate bill and
joint resolution's page (about 1,000-1,700 a session), the session's database and members file (core_files()), and the
Legislative Finance Committee's fiscal impact reports (the converter's "What it does": one PDF a bill, read with
pdftotext). A second apart: about an hour a session. Floor-vote PDFs, committee reports and the governor's messages are
left out; so are the current members' and committees' pages."""
import os, sys
from states import window as W

SOURCE = "www.nmlegis.gov legislation pages and session folders (New Mexico Legislature)"
# One regular session a year (60 days in odd years, 30 in even), 2015 up to the window's first year.
SESSIONS = list(range(2015, W.first_year()))


def fetch(session, data):
    saved = sys.argv
    sys.argv = [saved[0], str(session)]  # (fetch.py reads ONLY, a single year, from the command line when loaded)
    try:
        from states.nm import fetch as F
    finally:
        sys.argv = saved
    F.DATA, F.ONLY = data, session
    F.MARKER, F.MEMBERS = os.path.join(data, "incomplete"), os.path.join(data, "members")
    F.COMMITTEES = os.path.join(data, "committees")
    F.EXTRAS = tuple(e for e in F.EXTRAS if e[0] == "firs")  # (only the fiscal impact reports: the summaries)
    found = F.sessions()
    if f"{session} Regular" not in found:
        print(f"nm {session}: not in the site's session list", flush=True)
        return False
    folder = os.path.join(data, str(session))
    os.makedirs(folder, exist_ok=True)
    state = F.load(os.path.join(folder, "state.json"), {})
    listing = F.read_list(session, folder, found, state)
    if not listing:
        return False
    F.bill_pages(session, folder, state, listing)
    F.core_files(session, folder, state)
    F.save(state, os.path.join(folder, "state.json"))
    F.extras(session, folder, state)
    F.save(state, os.path.join(folder, "state.json"))
    missing = [g for g in F.never_downloaded([session], found) if not g.startswith("members:")]
    if missing:
        print(f"nm {session}: not downloaded: {' '.join(missing)}", flush=True)
    return not any(":list" in g or ":bills" in g for g in missing)
