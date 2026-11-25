"""Virginia's light history (states/light.py, states/LIGHT.md): the 2017 to 2022 sessions. 2022 from the legacy LIS's CSVs
(legacylis.virginia.gov/SiteInformation/csv/221/, robots.txt allows everything; the same files and converter as 2023's
first copy: fetch.py's one()); the legacy site has no older years (2015-2021 answer 404, checked 2026-11-25), so 2017-2021
come from Open States' bulk session files (states/openstates_records.py; public domain), named by the owner in
states/va/light_bulk.json. Open States has no 2015 or 2016 regular session listed for Virginia."""
import importlib, sys

from states import openstates_records as O

SOURCE = "the legacy LIS's CSVs (2022); Open States bulk session files (2017-2021, public domain)"
SESSIONS = [2017, 2018, 2019, 2020, 2021, 2022]
OFFICIAL = {2022}


def _fetch_module():
    saved = sys.argv
    sys.argv = [saved[0]]  # (fetch.py reads its first year from the command line when loaded)
    try:
        return importlib.import_module("states.va.fetch")
    finally:
        sys.argv = saved


def fetch(session, data):
    if session not in OFFICIAL:
        return O.fetch("va", session, data)
    F = _fetch_module()
    real = F.P.DATA
    F.P.DATA = data
    try:
        F.one(session)
    finally:
        F.P.DATA = real
    import os
    return os.path.exists(os.path.join(data, f"{session}1", "BILLS.CSV"))


def records(session, data, P):
    if session not in OFFICIAL:
        return O.records("va", session, data, P)
    C = importlib.import_module("states.va.convert")
    recs = C.load_session(session)[0]
    return recs, (C.parties(session, recs) if hasattr(C, "parties") else {})
