"""Light history for MA (states/light.py, states/LIGHT.md): the 190th to 192nd General Courts (2017-18 to 2021-22); Open States has no 189th (2015-16). The Legislature's API needs each bill's history for "passed one house". From Open States' bulk session files
(states/openstates_records.py; public domain), one download a session, named by the owner in states/ma/light_bulk.json."""
from states import openstates_records as O

SOURCE = O.SOURCE
SESSIONS = [2017, 2019, 2021]


def fetch(session, data):
    return O.fetch("ma", session, data)


def records(session, data, P):
    return O.records("ma", session, data, P)
