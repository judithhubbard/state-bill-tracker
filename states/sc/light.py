"""Light history for SC (states/light.py, states/LIGHT.md): the 122nd to 124th General Assemblies (2017-18 to 2021-22). scstatehouse.gov's search sits behind Cloudflare's bot check. From Open States' bulk session files
(states/openstates_records.py; public domain), one download a session, named by the owner in states/sc/light_bulk.json."""
from states import openstates_records as O

SOURCE = O.SOURCE
SESSIONS = [2017, 2019, 2021]


def fetch(session, data):
    return O.fetch("sc", session, data)


def records(session, data, P):
    return O.records("sc", session, data, P)
