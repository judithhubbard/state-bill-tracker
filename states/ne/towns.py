#!/usr/bin/env python3
"""Each Nebraska city, village, Census-designated community and county and the legislative districts that cover it, for
"Where you live": data/ne/district_towns.json: [["Lincoln city", "", [[46, 9], [26, 8], ...]], ...]: place, (unused), and
the districts, each [district, percent of the place's land in it]. Nebraska has one house, so one list (as New Jersey's
towns, whose district gives all its legislators): a district elects one senator.

From the Census Bureau's relationship files between the 2024 state legislative districts (the "upper" districts: Nebraska
files its 49 districts there; the map drawn in 2021, first used in the 2022 elections) and 2020 places and counties
(www2.census.gov/geo/docs/maps-data/data/rel2020/cd-sld/, no key needed), which give each overlap's land area. Slivers
along boundaries (under 0.5% of the place) are left out, unless the place holds most of the district (Omaha's and
Lincoln's districts). The districts are fixed until the next redistricting (after the 2030 census), so this is run once
and the file kept in git. Usage: python3 states/ne/towns.py
"""
import json, os, subprocess, sys
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
from states.ne import profile as P

BASE = "https://www2.census.gov/geo/docs/maps-data/data/rel2020/cd-sld/tab20_sldu202420_{geo}20_st31.txt"


def rows(geo):
    url = BASE.format(geo=geo)
    text = subprocess.run(["curl", "-sSf", "--max-time", "120", url], capture_output=True, check=True).stdout.decode("utf-8-sig")
    lines = [l.split("|") for l in text.splitlines() if l.strip()]
    head = lines[0]
    return [dict(zip(head, l)) for l in lines[1:]]


def main():
    places = defaultdict(lambda: {"d": defaultdict(int), "area": 1})
    district_area = defaultdict(int)  # district -> land area, from the county file (counties cover the state)
    for geo in ("place", "county"):
        for r in rows(geo):
            name = r.get(f"NAMELSAD_{geo.upper()}_20")
            mtfcc = r.get(f"MTFCC_{geo.upper()}_20")
            if not name or (geo == "place" and mtfcc not in ("G4110", "G4210")):  # cities, villages and communities
                continue
            code = r["GEOID_SLDU2024_20"][-3:]
            if not code.isdigit():
                continue  # "ZZZ": land in no district (water)
            d = int(code)
            part = int(r["AREALAND_PART"] or 0)
            if geo == "county":
                district_area[d] += part
            p = places[name[:-4] if name.endswith(" CDP") else name]  # "Offutt AFB CDP" -> "Offutt AFB"
            p["area"] = max(1, int(r[f"AREALAND_{geo.upper()}_20"] or 0))
            p["d"][d] += part
    out = []
    for name, p in places.items():
        share = sorted(([d, round(100 * a / p["area"])] for d, a in p["d"].items()
                        if a / p["area"] >= 0.005 or a / max(1, district_area[d]) >= 0.5), key=lambda x: -x[1])
        if share:
            out.append([name, "", share])
    out.sort(key=lambda r: r[0].lower())
    path = os.path.join(P.DATA, "district_towns.json")
    os.makedirs(P.DATA, exist_ok=True)
    json.dump(out, open(path, "w"), indent=0)
    have = {d[0] for r in out for d in r[2]}
    print(f"{path}: {len(out)} places and counties; {sum(1 for r in out if len(r[2]) == 1)} in one district; "
          f"districts covered {len(have)} of 49")


if __name__ == "__main__":
    main()
