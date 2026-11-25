"""Light history for NE (states/light.py, states/LIGHT.md): the 105th to 107th Legislatures (2017-18 to 2021-22). Unicameral: passing the Legislature is "passed both". The Legislature's pages are one a bill at a 3-second crawl delay. From Open States' bulk session files
(states/openstates_records.py; public domain), one download a session, named by the owner in states/ne/light_bulk.json."""
from states import openstates_records as O

SOURCE = O.SOURCE
SESSIONS = [2017, 2019, 2021]


def fetch(session, data):
    return O.fetch("ne", session, data)


def records(session, data, P):
    return O.records("ne", session, data, P)
