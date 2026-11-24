"""Light history from Open States' bulk session files (states/light.py, states/LIGHT.md), for the states whose current
sessions already come from Open States in the API's shape (Arizona's older years, Hawaii): each old year's file, named
by the owner in states/<st>/light_bulk.json ({"2015": "AZ_52nd-1st-regular_json_<id>.zip"}; the names carry an id that
changes with each rebuild and are listed only at open.pluralpolicy.com/data/session-json/, which needs the owner's
login), is read (the owner's Bulk_files_OpenStates/ copy when it's there, else data.openstates.org's public link: one
download, a few MB) and its bills are written into <data>/<year>/bills/ with states/openstates_bulk.py's own api_shape()
and bill types, as the site's own bulk imports are. Open States' data is public domain. A separate list from bulk.json:
names there are imported into the site's own data by every download run."""
import io, json, os, re, zipfile

from states import openstates_bulk as B


def names(st):
    return B.load(os.path.join(B.ROOT, "states", st, "light_bulk.json"), {}) or {}


def missing_names(st, years):
    have = names(st)
    return [y for y in years if not have.get(str(y))]


def fetch_years(st, years, data):
    """Each year's bulk file into <data>/<year>/bills/; False (and why, printed) when one isn't named or can't be read."""
    have = names(st)
    keep = re.compile(B.KEEP[st] + r" ?\d+$")
    for year in years:
        name = have.get(str(year))
        if not name:
            print(f"{st} {year}: no Open States bulk file named in states/{st}/light_bulk.json", flush=True)
            return False
        try:
            z = zipfile.ZipFile(io.BytesIO(B.fetch(name)))
            bills = json.loads(z.read(next(n for n in z.namelist() if n.endswith("_bills.json"))))
        except Exception as e:
            print(f"{st} {year}: {name} unreadable ({type(e).__name__}: {e})", flush=True)
            return False
        folder = os.path.join(data, str(year))
        out = os.path.join(folder, "bills")
        os.makedirs(out, exist_ok=True)
        n = 0
        for b in bills:
            if keep.match(b.get("identifier") or ""):
                B.save(B.api_shape(b), os.path.join(out, b["identifier"].replace(" ", "") + ".json"))
                n += 1
        B.save({"complete": True, "bulk": name}, os.path.join(folder, "openstates.json"))
        B.save({"complete": True}, os.path.join(folder, "state.json"))
        print(f"{st} {year}: {n} bills from {name} (of {len(bills)} records)", flush=True)
    return True
