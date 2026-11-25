"""Light history for TX (states/light.py, states/LIGHT.md): the 86th Legislature's regular session (2019) only: Open States lists no 85th regular session (2017), and the Legislature's FTP is one file a bill (10,000-12,000 a session). From Open States' bulk session files
(states/openstates_records.py; public domain), one download a session, named by the owner in states/tx/light_bulk.json."""
from states import openstates_records as O

SOURCE = O.SOURCE
SESSIONS = [2019]


def fetch(session, data):
    return O.fetch("tx", session, data)


def records(session, data, P):
    return O.records("tx", session, data, P)
