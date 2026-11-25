"""Light history for IL (states/light.py, states/LIGHT.md): the 99th to 101st General Assemblies (2015-16 to 2019-20). Not ftp.ilga.gov: the General Assembly asked automated users to read it once a day, 10 seconds a request (states/il/NOTES.md), and an old Assembly is 6,000-10,000 files. From Open States' bulk session files
(states/openstates_records.py; public domain), one download a session, named by the owner in states/il/light_bulk.json."""
from states import openstates_records as O

SOURCE = O.SOURCE
SESSIONS = [2015, 2017, 2019]


def fetch(session, data):
    return O.fetch("il", session, data)


def records(session, data, P):
    return O.records("il", session, data, P)
