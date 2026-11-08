#!/usr/bin/env python3
"""Each Idaho city, community and county and the legislative districts that cover it, for "Where you live" (each
district elects one senator and two representatives, House seats A and B, so one list serves both houses):
data/id/district_towns.json: [["Boise city", "", [[16, 12], ...]], ...]: place, (unused), districts, each [district,
percent of the place's land in it].

From the Census Bureau's relationship files between the 2024 state legislative districts and 2020 places and counties
(www2.census.gov/geo/docs/maps-data/data/rel2020/cd-sld/, no key needed), which give each overlap's land area. Slivers
along boundaries (under 0.5% of the place) are left out, unless the place holds most of the district (Ada County's
small urban districts in Boise). Census-designated places (unincorporated communities) are listed too. The districts
are fixed until the next redistricting (after the 2030 census), so this is run once and the file kept in git.
Usage: python3 states/id/towns.py
"""
import json, os, subprocess, sys
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
from states.id import profile as P

BASE = "https://www2.census.gov/geo/docs/maps-data/data/rel2020/cd-sld/tab20_{h}202420_{geo}20_st16.txt"


def rows(h, geo):
    url = BASE.format(h=h, geo=geo)
    text = subprocess.run(["curl", "-sSf", "--max-time", "120", url], capture_output=True, check=True).stdout.decode("utf-8-sig")
    lines = [l.split("|") for l in text.splitlines() if l.strip()]
    head = lines[0]
    return [dict(zip(head, l)) for l in lines[1:]]


def main():
    places = defaultdict(lambda: {"S": defaultdict(int), "area": 1})
    district_area = defaultdict(int)
    h = "sldu"
    for geo in ("place", "county"):
        for r in rows(h, geo):
            name = r.get(f"NAMELSAD_{geo.upper()}_20")
            mtfcc = r.get(f"MTFCC_{geo.upper()}_20")
            code = r[f"GEOID_{h.upper()}2024_20"][-3:]
            if not code.isdigit():
                continue  # "ZZZ": land in no district (water)
            d = int(code)
            if geo == "county":
                district_area[d] += int(r["AREALAND_PART"] or 0)  # counties cover the state: each district's land
            if not name or (geo == "place" and mtfcc not in ("G4110", "G4210")):  # cities and communities
                continue
            name = "Boise city" if name == "Boise City city" else name  # the Census Bureau's name for Boise
            p = places[name[:-4] if name.endswith(" CDP") else name]  # "Garden City city"; "Hayden Lake"
            p["area"] = max(1, int(r[f"AREALAND_{geo.upper()}_20"] or 0))
            p["S"][d] += int(r["AREALAND_PART"] or 0)
    out = []
    for name, p in places.items():
        share = sorted(([d, round(100 * a / p["area"])] for d, a in p["S"].items()
                        if a / p["area"] >= 0.005 or a / max(1, district_area[d]) >= 0.5), key=lambda x: -x[1])
        if share:
            out.append([name, "", share])
    out.sort(key=lambda r: r[0].lower())
    path = os.path.join(P.DATA, "district_towns.json")
    os.makedirs(P.DATA, exist_ok=True)
    json.dump(out, open(path, "w"), indent=0)
    print(f"{path}: {len(out)} places and counties; {sum(1 for r in out if len(r[2]) == 1)} in one district; "
          f"districts listed: {len({d for r in out for d, _ in r[2]})} of 35")


if __name__ == "__main__":
    main()
