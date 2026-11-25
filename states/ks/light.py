"""Light history for KS (states/light.py, states/LIGHT.md): 2017-18 to 2021-22. The Legislature's API holds only 2023-24 on; older years are HTML archives (a page a bill). From Open States' bulk session files
(states/openstates_records.py; public domain), one download a session, named by the owner in states/ks/light_bulk.json."""
from states import openstates_records as O

SOURCE = O.SOURCE
SESSIONS = [2017, 2019, 2021]


def fetch(session, data):
    return O.fetch("ks", session, data)


def records(session, data, P):
    return O.records("ks", session, data, P)
