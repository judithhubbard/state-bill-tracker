"""Rhode Island's light history (states/light.py, states/LIGHT.md): the yearly sessions before the shared window
(2015-2022), each from its LegiScan dataset (states/legiscan_light.py: one getDataset each, CC BY 4.0). Contacts are left
out."""
from states import legiscan_light as LL
from states import window as W

SOURCE = "LegiScan datasets (api.legiscan.com, CC BY 4.0)"
SESSIONS = LL.sessions_from(2015, W.first_year())


def fetch(session, data):
    return LL.fetch("ri", session, data)
