"""Light history for AR (states/light.py, states/LIGHT.md): the 2019 to 2022 regular and fiscal sessions (Open States has no 2017 regular session). Whether the Bureau of Legislative Research's files reach back is unverified. From Open States' bulk session files
(states/openstates_records.py; public domain), one download a session, named by the owner in states/ar/light_bulk.json."""
from states import openstates_records as O

SOURCE = O.SOURCE
SESSIONS = [2019, 2020, 2021, 2022]


def fetch(session, data):
    return O.fetch("ar", session, data)


def records(session, data, P):
    return O.records("ar", session, data, P)
