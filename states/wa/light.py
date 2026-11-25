"""Light history for WA (states/light.py, states/LIGHT.md): 2017-18 and 2019-20 (Open States has no 2015-16; the site keeps 2021-22 on). The Legislature's web services are one request a bill. From Open States' bulk session files
(states/openstates_records.py; public domain), one download a session, named by the owner in states/wa/light_bulk.json."""
from states import openstates_records as O

SOURCE = O.SOURCE
SESSIONS = [2017, 2019]


def fetch(session, data):
    return O.fetch("wa", session, data)


def records(session, data, P):
    return O.records("wa", session, data, P)
