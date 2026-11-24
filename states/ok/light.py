"""Oklahoma's light history (states/light.py, states/LIGHT.md): the Legislatures before the shared window (2015-2022,
named by their first, odd year), from LegiScan's datasets (states/legiscan_light.py, CC BY 4.0). LegiScan has a session a
year; both years' datasets are read, and the converter keeps the even year's, which holds the whole Legislature, once it
is as large (convert.py's session_folders()). The staff summaries (supplements), the governor's veto pages and contacts
are left out."""
from states import legiscan_light as LL
from states import window as W

SOURCE = "LegiScan datasets (api.legiscan.com, CC BY 4.0)"
SESSIONS = LL.sessions_from(2015, W.first_year(), 2)


def fetch(session, data):
    return LL.fetch("ok", session, data, years=[session, session + 1])
