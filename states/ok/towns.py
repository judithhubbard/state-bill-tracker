#!/usr/bin/env python3
"""Each Oklahoma city, town and county and the Senate and House districts that cover it, for "Where you live":
data/ok/district_towns.json: [["Norman city", "", [[16, 60], ...], [[60, 30], ...]], ...]: place, (unused), Senate and House
districts, each [district, percent of the place's land in it].

From the Census Bureau's relationship files between the 2024 state legislative districts and 2020 places and
counties (www2.census.gov/geo/docs/maps-data/data/rel2020/cd-sld/, no key needed), which give each overlap's land
area. Slivers along boundaries (under 0.5% of the place) are left out. Census-designated places (unincorporated
communities) aren't listed; their residents can pick their county or look up their address. The districts are
fixed until the next redistricting (2032), so this is run once and the file kept in git. Usage: python3 states/ok/towns.py
"""
import json, os, subprocess, sys
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
import importlib
P = importlib.import_module("states.ok.profile")

BASE = "https://www2.census.gov/geo/docs/maps-data/data/rel2020/cd-sld/tab20_{h}202420_{geo}20_st40.txt"


def rows(h, geo):
    url = BASE.format(h=h, geo=geo)
    text = subprocess.run(["curl", "-sSf", "--max-time", "120", url], capture_output=True, check=True).stdout.decode("utf-8-sig")
    lines = [l.split("|") for l in text.splitlines() if l.strip()]
    head = lines[0]
    return [dict(zip(head, l)) for l in lines[1:]]


def main():
    places = defaultdict(lambda: {"S": defaultdict(int), "H": defaultdict(int), "area": 1})
    for h, letter in (("sldu", "S"), ("sldl", "H")):
        for geo in ("place", "county"):
            for r in rows(h, geo):
                name = (r.get(f"NAMELSAD_{geo.upper()}_20") or "").replace(" (balance)", "")
                mtfcc = r.get(f"MTFCC_{geo.upper()}_20")
                if not name or (geo == "place" and mtfcc != "G4110"):  # incorporated places only
                    continue
                code = r[f"GEOID_{h.upper()}2024_20"][-3:]
                if not code.isdigit():
                    continue  # "ZZZ": land in no district
                d = int(code)
                p = places[name]
                p["area"] = max(1, int(r[f"AREALAND_{geo.upper()}_20"] or 0))
                p[letter][d] += int(r["AREALAND_PART"] or 0)
    out = []
    for name, p in places.items():
        share = {h: sorted(([d, round(100 * a / p["area"])] for d, a in p[h].items() if a / p["area"] >= 0.005), key=lambda x: -x[1]) for h in "SH"}
        if share["S"] and share["H"]:
            out.append([name, "", share["S"], share["H"]])
    out.sort(key=lambda r: r[0].lower())
    path = os.path.join(P.DATA, "district_towns.json")
    os.makedirs(P.DATA, exist_ok=True)
    json.dump(out, open(path, "w"), indent=0)
    print(f"{path}: {len(out)} places and counties; {sum(1 for r in out if len(r[2]) == 1 and len(r[3]) == 1)} in one district of each")


if __name__ == "__main__":
    main()
