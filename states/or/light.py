"""Oregon's light history (states/light.py, states/LIGHT.md): the regular sessions before the earliest full one (2022),
from the Legislature's OData API with fetch.py's own table reader: the seven tables convert.py reads (measures, history
actions, sponsors, floor and committee votes, committees, legislators), one paged request after another. Documents,
agendas, meetings and veto letters are left out. Oregon meets every year (long sessions in odd years, short in even)."""
import importlib, json, os, sys
from states import window as W

SOURCE = "api.oregonlegislature.gov OData (Oregon Legislature)"
TABLES = ["Measures", "MeasureHistoryActions", "MeasureSponsors", "MeasureVotes", "CommitteeVotes", "Committees", "Legislators"]
# Before 2022, the first full session kept (states/window.py keeps earlier ones a state already had).
SESSIONS = list(range(2015, min(2022, W.first_year())))


def fetch(session, data):
    saved = sys.argv
    sys.argv = [saved[0]]  # (fetch.py reads its first year from the command line when loaded)
    try:
        F = importlib.import_module("states.or.fetch")  # ("or" is a keyword: imported by name)
    finally:
        sys.argv = saved
    P = importlib.import_module("states.or.profile")
    folder = os.path.join(data, P.session_key(session))
    os.makedirs(folder, exist_ok=True)
    for name in TABLES:
        rows = F.table(name, P.session_key(session))
        if rows is None:
            print(f"or {session} {name}: failed", flush=True)
            return False
        with open(os.path.join(folder, f"{name}.json"), "w") as f:
            json.dump(rows, f)
        print(f"or {session} {name}: {len(rows)} rows", flush=True)
    return True
