"""Tennessee's light history (states/light.py, states/LIGHT.md): the General Assemblies before the shared window (the
109th to 112th, 2015-2022, named by their first year), each from its LegiScan dataset (states/legiscan_light.py: one
getDataset each, CC BY 4.0). Contacts are left out."""
from states import legiscan_light as LL
from states import window as W

SOURCE = "LegiScan datasets (api.legiscan.com, CC BY 4.0)"
SESSIONS = LL.sessions_from(2015, W.first_year(), 2)


def fetch(session, data):
    return LL.fetch("tn", session, data)
