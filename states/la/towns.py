#!/usr/bin/env python3
"""Each Louisiana city, town, village, Census-designated place and parish, with the Senate and House districts that
cover it, for "Where you live": data/la/district_towns.json: [["Baton Rouge city", "", [[15, 40], [14, 30]], [[29, 12],
...]], ...]: place, (unused), Senate and House districts, each [district, percent of the place's land in it].

From the Census Bureau's relationship files between the 2024 state legislative districts and 2020 places and counties
(www2.census.gov/geo/docs/maps-data/data/rel2020/cd-sld/, no key needed; Louisiana's counties are parishes, "Orleans
Parish"), which give each overlap's land area. Slivers along boundaries (under 0.5% of the place) are left out, unless
the place holds most of that district. Census-designated places (unincorporated communities, "Metairie CDP") are listed
too. The Senate has 39 and the House 105 single-member districts, drawn in 2022 and fixed until the next redistricting
(after the 2030 census), so this is run once and the file kept in git. Usage: python3 states/la/towns.py
"""
import json, os, subprocess, sys
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
from states.la import profile as P

BASE = "https://www2.census.gov/geo/docs/maps-data/data/rel2020/cd-sld/tab20_{h}202420_{geo}20_st22.txt"


def rows(h, geo):
    url = BASE.format(h=h, geo=geo)
    text = subprocess.run(["curl", "-sSf", "--max-time", "120", url], capture_output=True, check=True).stdout.decode("utf-8-sig")
    lines = [l.split("|") for l in text.splitlines() if l.strip()]
    head = lines[0]
    return [dict(zip(head, l)) for l in lines[1:]]


def main():
    places = defaultdict(lambda: {"S": defaultdict(int), "H": defaultdict(int), "area": 1})
    district_area = {"S": defaultdict(int), "H": defaultdict(int)}
    for h, letter in (("sldu", "S"), ("sldl", "H")):
        for geo in ("place", "county"):
            for r in rows(h, geo):
                name = (r.get(f"NAMELSAD_{geo.upper()}_20") or "").replace(" (balance)", "")
                mtfcc = r.get(f"MTFCC_{geo.upper()}_20")
                if not name or (geo == "place" and mtfcc not in ("G4110", "G4210")):  # incorporated places and CDPs
                    continue
                code = r[f"GEOID_{h.upper()}2024_20"][-3:]
                if not code.isdigit():
                    continue  # "ZZZ": land in no district
                d = int(code)
                p = places[name]
                p["area"] = max(1, int(r[f"AREALAND_{geo.upper()}_20"] or 0))
                part = int(r["AREALAND_PART"] or 0)
                p[letter][d] += part
                if geo == "county":
                    district_area[letter][d] += part
    out = []
    for name, p in places.items():
        def keep(h, d, a):
            return a / p["area"] >= 0.005 or a >= 0.5 * max(1, district_area[h][d])
        share = {h: sorted(([d, max(1, round(100 * a / p["area"]))] for d, a in p[h].items() if a and keep(h, d, a)), key=lambda x: -x[1])
                 for h in "SH"}
        if share["S"] and share["H"]:
            out.append([name, "", share["S"], share["H"]])
    out.sort(key=lambda r: r[0].lower())
    path = os.path.join(P.DATA, "district_towns.json")
    os.makedirs(P.DATA, exist_ok=True)
    json.dump(out, open(path, "w"), indent=0)
    have = {h: {d for r in out for d, _ in r[2 if h == "S" else 3]} for h in "SH"}
    print(f"{path}: {len(out)} places and parishes; {sum(1 for r in out if len(r[2]) == 1 and len(r[3]) == 1)} in one "
          f"district of each; Senate districts {len(have['S'])}, House districts {len(have['H'])}")


if __name__ == "__main__":
    main()
