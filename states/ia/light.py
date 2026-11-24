"""Iowa's light history (states/light.py, states/LIGHT.md): the General Assemblies before the shared window (the 86th,
2015-16, to the 89th, 2021-22), from Open States' bulk JSON files (public domain), the same files and reader
(states/openstates_bulk.py's fetch() and api_shape()) that made 2023-24's first copy, into <year>/openstates/, which
convert.py reads when a General Assembly has no history pages. Never legis.iowa.gov: its bot check ends a run after
about 45 requests, and its history pages are one request a bill.

A file's name carries an id listed only on open.pluralpolicy.com/data/session-json/ (the owner's login), so each session
needs its name in states/ia/light_bulk.json, {"2015": "IA_2015-2016_json_<id>.zip"}, before it's read: a separate file
from bulk.json, whose every entry the daily download imports into the live data. One request a session."""
import io, json, os, re, sys, zipfile
from datetime import date
from states import window as W

SOURCE = "Open States bulk JSON (data.openstates.org/json/latest/, public domain), as Iowa's 2023-24"
HERE = os.path.dirname(os.path.abspath(__file__))
# Two-year General Assemblies, named by their first year.
SESSIONS = [y for y in range(2015, W.first_session()) if y % 2]


def fetch(session, data):
    from states import openstates_bulk as OB
    try:
        names = json.load(open(os.path.join(HERE, "light_bulk.json"), encoding="utf-8"))
    except (OSError, ValueError):
        names = {}
    name = names.get(str(session))
    if not name:
        print(f"ia {session}: no bulk file named in states/ia/light_bulk.json (the owner looks it up on "
              f"open.pluralpolicy.com/data/session-json/)", flush=True)
        return False
    try:
        z = zipfile.ZipFile(io.BytesIO(OB.fetch(name)))
        bills = json.loads(z.read(next(n for n in z.namelist() if n.endswith("_bills.json"))))
    except Exception as e:
        print(f"ia {session}: {name} unreadable ({type(e).__name__}: {e})", flush=True)
        return False
    folder = os.path.join(data, str(session))
    out = os.path.join(folder, "openstates")
    os.makedirs(out, exist_ok=True)
    keep = re.compile(OB.KEEP["ia"] + r" ?\d+$")
    n = 0
    for b in bills:
        if keep.match(b.get("identifier") or ""):
            OB.save(OB.api_shape(b), os.path.join(out, b["identifier"].replace(" ", "") + ".json"))
            n += 1
    OB.save({"complete": True, "bulk": name, "done": date.today().isoformat()}, os.path.join(folder, "openstates.json"))
    print(f"ia {session}: {n} bills from {name}", flush=True)
    return n > 0
