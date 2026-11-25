"""Light history for MI (states/light.py, states/LIGHT.md): 2017-18 to 2021-22 (Open States has no 2015-16). The Legislature's own status files are one a bill (about 4,500 a session). From Open States' bulk session files
(states/openstates_records.py; public domain), one download a session, named by the owner in states/mi/light_bulk.json."""
from states import openstates_records as O

SOURCE = O.SOURCE
SESSIONS = [2017, 2019, 2021]


def fetch(session, data):
    return O.fetch("mi", session, data)


def records(session, data, P):
    return O.records("mi", session, data, P)
