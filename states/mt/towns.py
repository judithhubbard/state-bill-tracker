#!/usr/bin/env python3
"""Each Montana city, town, Census-designated community and county and the Senate and House districts that cover it, for
"Where you live": data/mt/district_towns.json: [["Billings city", "", [[26, 41], ...], [[52, 23], ...]], ...]: place,
(unused), Senate and House districts, each [district, percent of the place's land in it]. (Each Senate district is two House
districts: Senate District n is House Districts 2n-1 and 2n.)

From the Census Bureau's relationship files between the 2024 state legislative districts (the map the Districting and
Apportionment Commission drew after the 2020 census, first used in the 2024 elections) and 2020 places and counties
(www2.census.gov/geo/docs/maps-data/data/rel2020/cd-sld/, no key needed), which give each overlap's land area. Slivers
along boundaries (under 0.5% of the place) are left out, unless the place holds most of the district. Census-designated
places are listed too (many on the reservations: Browning, Lame Deer, Crow Agency). The districts are fixed until the
next redistricting (after the 2030 census), so this is run once and the file kept in git. Usage: python3 states/mt/towns.py
"""
import json, os, subprocess, sys
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
from states.mt import profile as P

BASE = "https://www2.census.gov/geo/docs/maps-data/data/rel2020/cd-sld/tab20_{h}202420_{geo}20_st30.txt"


def rows(h, geo):
    url = BASE.format(h=h, geo=geo)
    text = subprocess.run(["curl", "-sSf", "--max-time", "120", url], capture_output=True, check=True).stdout.decode("utf-8-sig")
    lines = [l.split("|") for l in text.splitlines() if l.strip()]
    head = lines[0]
    return [dict(zip(head, l)) for l in lines[1:]]


def main():
    places = defaultdict(lambda: {"S": defaultdict(int), "H": defaultdict(int), "area": 1})
    district_area = defaultdict(int)  # (house, district) -> land area, from the county file (counties cover the state)
    for h, letter in (("sldu", "S"), ("sldl", "H")):
        for geo in ("place", "county"):
            for r in rows(h, geo):
                name = r.get(f"NAMELSAD_{geo.upper()}_20")
                mtfcc = r.get(f"MTFCC_{geo.upper()}_20")
                if not name or (geo == "place" and mtfcc not in ("G4110", "G4210")):  # cities, towns and communities
                    continue
                code = r[f"GEOID_{h.upper()}2024_20"][-3:]
                if not code.isdigit():
                    continue  # "ZZZ": land in no district (water)
                d = int(code)
                part = int(r["AREALAND_PART"] or 0)
                if geo == "county":
                    district_area[(letter, d)] += part
                name = name.replace(" (balance)", "")  # "Butte-Silver Bow (balance)", the consolidated city-county
                p = places[name[:-4] if name.endswith(" CDP") else name]  # "Lame Deer CDP" -> "Lame Deer"
                p["area"] = max(1, int(r[f"AREALAND_{geo.upper()}_20"] or 0))
                p[letter][d] += part
    out = []
    for name, p in places.items():
        share = {h: sorted(([d, round(100 * a / p["area"])] for d, a in p[h].items()
                            if a / p["area"] >= 0.005 or a / max(1, district_area[(h, d)]) >= 0.5), key=lambda x: -x[1]) for h in "SH"}
        if share["S"] and share["H"]:
            out.append([name, "", share["S"], share["H"]])
    out.sort(key=lambda r: r[0].lower())
    path = os.path.join(P.DATA, "district_towns.json")
    os.makedirs(P.DATA, exist_ok=True)
    json.dump(out, open(path, "w"), indent=0)
    have = {h: {d[0] for r in out for d in r[2 if h == "S" else 3]} for h in "SH"}
    print(f"{path}: {len(out)} places and counties; {sum(1 for r in out if len(r[2]) == 1 and len(r[3]) == 1)} in one district "
          f"of each; Senate districts covered {len(have['S'])} of 50, House {len(have['H'])} of 100")


if __name__ == "__main__":
    main()
