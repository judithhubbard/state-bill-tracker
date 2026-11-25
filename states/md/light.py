"""Light history for MD (states/light.py, states/LIGHT.md): the 2017 to 2022 regular sessions. The General Assembly's legislation.json reaches only 2019, without the governor's actions (the converter reads each passed bill's page for them: about 900 a session). From Open States' bulk session files
(states/openstates_records.py; public domain), one download a session, named by the owner in states/md/light_bulk.json."""
from states import openstates_records as O

SOURCE = O.SOURCE
SESSIONS = [2017, 2018, 2019, 2020, 2021, 2022]


def fetch(session, data):
    return O.fetch("md", session, data)


def records(session, data, P):
    return O.records("md", session, data, P)
