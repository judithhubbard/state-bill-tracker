"""Arizona's light history (states/light.py, states/LIGHT.md): the regular sessions before the shared window (2015,
the 52nd Legislature's first, to 2022, the 55th's second), from Open States' bulk session files (states/
openstates_light.py; public domain), one download a session, read as the site's own 2023 bulk import is (the
converter's Open States path). The owner names each file in states/az/light_bulk.json: "AZ_52nd-1st-regular_json_<id>
.zip" for 2015 ... "AZ_55th-2nd-regular_json_<id>.zip" for 2022. Not from apps.azleg.gov: the webmaster's permission
(2026-11-24) covers the current sessions' bills, not a back catalogue. Sponsors before 2023 aren't in states/az/
people.json's roles, so the light records name them without parties; no chapter numbers (Open States has none)."""
from states import openstates_light as O
from states import window as W

SOURCE = "Open States bulk session files (open.pluralpolicy.com/data/session-json/, public domain)"
SESSIONS = list(range(2015, W.first_year()))


def fetch(session, data):
    return O.fetch_years("az", [session], data)
