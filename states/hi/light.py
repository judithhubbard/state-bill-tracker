"""Hawaii's light history (states/light.py, states/LIGHT.md): the two-year Legislatures before the shared window
(2015-16 to 2021-22), from Open States' bulk session files (states/openstates_light.py; public domain), one download a
year: a Legislature's page needs both years (a bill's second-year record holds its whole history), read as the site's
own 2023-26 bulk imports are. The owner names each year's file in states/hi/light_bulk.json ("HI_2015_json_<id>.zip"
... "HI_2022_json_<id>.zip"; 2023's was named "HI_2023 Regular Session_json_<id>.zip"). capitol.hawaii.gov turns
automated readers away (a request to the Legislature is open, 2026-11-24), so nothing is read there."""
from states import openstates_light as O
from states import window as W

SOURCE = "Open States bulk session files (open.pluralpolicy.com/data/session-json/, public domain)"
SESSIONS = list(range(2015, W.first_session(), 2))


def fetch(session, data):
    return O.fetch_years("hi", [session, session + 1], data)
