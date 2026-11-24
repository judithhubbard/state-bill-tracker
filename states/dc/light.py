"""The District of Columbia's light history (states/light.py, states/LIGHT.md): the Council Periods before the shared
window (the 21st to 24th, 2015-2022, named by their first year), each from its LegiScan dataset (states/legiscan_light.py:
one getDataset each, CC BY 4.0), plus the period's acts and laws from the Council's law library on GitHub (laws.py's
refresh() and table(): two listings, then each act's and law's file, a quarter of a second apart; about 600-1,000 files
a period), which give laws their numbers and effective dates. Contacts are left out."""
import json, os
from states import legiscan_light as LL
from states import window as W

SOURCE = "LegiScan datasets (api.legiscan.com, CC BY 4.0) and the DC Council's law library (github.com/DCCouncil/law-xml)"
SESSIONS = LL.sessions_from(2015, W.first_year(), 2)


def fetch(session, data):
    if not LL.fetch("dc", session, data):
        return False
    from states.dc import laws as LW
    from states.dc import profile as P
    LW.FOLDER = os.path.join(data, "lawxml")
    period = P.period_of(session)
    n = LW.refresh(period)
    t = LW.table(period)
    if t:
        json.dump(t, open(os.path.join(data, f"laws_{session}.json"), "w"), indent=0, ensure_ascii=False, sort_keys=True)
    print(f"dc {session}: Council Period {period}: {n if n is not None else 'no'} law-library files read; "
          f"{sum(1 for e in t.values() if e.get('law'))} laws, {sum(1 for e in t.values() if e.get('act'))} acts", flush=True)
    return n is not None
