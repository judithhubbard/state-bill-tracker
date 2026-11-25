"""Light history for MN (states/light.py, states/LIGHT.md): the 90th to 92nd Legislatures (2017-18 to 2021-22). The Revisor's API is one request a bill (about 8,000 a Legislature). From Open States' bulk session files
(states/openstates_records.py; public domain), one download a session, named by the owner in states/mn/light_bulk.json."""
from states import openstates_records as O

SOURCE = O.SOURCE
SESSIONS = [2017, 2019, 2021]


def fetch(session, data):
    return O.fetch("mn", session, data)


def records(session, data, P):
    return O.records("mn", session, data, P)
