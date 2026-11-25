"""Light history for UT (states/light.py, states/LIGHT.md): the 2017 to 2022 General Sessions. The Legislature's API keys only recent sessions, and its floor roll calls are barred since 2026-11-23. From Open States' bulk session files
(states/openstates_records.py; public domain), one download a session, named by the owner in states/ut/light_bulk.json."""
from states import openstates_records as O

SOURCE = O.SOURCE
SESSIONS = [2017, 2018, 2019, 2020, 2021, 2022]


def fetch(session, data):
    return O.fetch("ut", session, data)


def records(session, data, P):
    return O.records("ut", session, data, P)
