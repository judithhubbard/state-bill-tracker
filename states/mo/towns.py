#!/usr/bin/env python3
"""Each Missouri city, town, village, community and county and the Senate and House districts that cover it, for "Where you
live": data/mo/district_towns.json: [["Columbia city", "", [[19, 100]], [[45, 30], ...]], ...]: place, (unused), Senate
and House districts, each [district, percent of the place's land in it].

From the Census Bureau's relationship files between the 2024 state legislative districts and 2020 places and counties
(www2.census.gov/geo/docs/maps-data/data/rel2020/cd-sld/, no key needed), which give each overlap's land area. Missouri
has 34 Senate and 163 House districts, drawn separately. Cities, towns, villages and Census-designated places are listed,
and the counties; St. Louis city is a county of its own and a place, listed once. Slivers along boundaries (under 0.5% of
the place) are left out, unless the place holds most of the district (the urban districts inside St. Louis and Kansas
City). The districts are fixed until the next redistricting (after the 2030 census), so this is run once and the file
kept in git. Usage: python3 states/mo/towns.py
"""
import json, os, subprocess, sys
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
from states.mo import profile as P

BASE = "https://www2.census.gov/geo/docs/maps-data/data/rel2020/cd-sld/tab20_{h}202420_{geo}20_st29.txt"


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
                name = r.get(f"NAMELSAD_{geo.upper()}_20")
                mtfcc = r.get(f"MTFCC_{geo.upper()}_20")
                code = r[f"GEOID_{h.upper()}2024_20"][-3:]
                if not code.isdigit():
                    continue  # "ZZZ": land in no district (water)
                d = int(code)
                if geo == "county":
                    district_area[letter][d] += int(r["AREALAND_PART"] or 0)  # counties cover the state
                if not name or (geo == "place" and mtfcc not in ("G4110", "G4210")):  # cities, towns and communities
                    continue
                if geo == "county" and name == "St. Louis city":
                    continue  # the independent city: listed once, as a place
                p = places[name[:-4] if name.endswith(" CDP") else name]
                p["area"] = max(1, int(r[f"AREALAND_{geo.upper()}_20"] or 0))
                p[letter][d] += int(r["AREALAND_PART"] or 0)
    out = []
    for name, p in places.items():
        share = {h: sorted(([d, round(100 * a / p["area"])] for d, a in p[h].items()
                            if a / p["area"] >= 0.005 or a / max(1, district_area[h][d]) >= 0.5), key=lambda x: -x[1])
                 for h in "SH"}
        if share["S"] and share["H"]:
            out.append([name, "", share["S"], share["H"]])
    out.sort(key=lambda r: r[0].lower())
    path = os.path.join(P.DATA, "district_towns.json")
    os.makedirs(P.DATA, exist_ok=True)
    json.dump(out, open(path, "w"), indent=0)
    print(f"{path}: {len(out)} places and counties; districts listed: Senate {len({d for r in out for d, _ in r[2]})} of 34, "
          f"House {len({d for r in out for d, _ in r[3]})} of 163")


if __name__ == "__main__":
    main()
