#!/usr/bin/env python3
"""Each Minnesota city and county and the Senate and House districts that cover it, for "Where you live":
data/mn/district_towns.json: [["Duluth city", "", [[7, 52], ...], [[13, 30], ...]], ...]: place, (unused), Senate and
House districts, each [district, percent of the place's land in it]; and data/mn/district_names.json, the House
districts' names by seat number ({"H": {"23": "12A", ...}}).

Minnesota has 67 Senate districts, each split into two House districts, A and B (12A and 12B make up Senate District
12). The page numbers House seats 1 to 134 (1A = 1, 1B = 2, ... 12A = 23, 67B = 134: profile.house_seat()), and the
names file shows them as "12A".

From the Census Bureau's relationship files between the 2024 state legislative districts and 2020 places and counties
(www2.census.gov/geo/docs/maps-data/data/rel2020/cd-sld/, no key needed), which give each overlap's land area. Only
cities are listed (not Census-designated places or townships: residents of a township pick their county, or look up
their address on the Legislature's district finder). Slivers along boundaries (under 0.5% of the place) are left out,
unless the place holds most of the district (Minneapolis's and St. Paul's small districts). The districts are fixed until
the next redistricting (after the 2030 census), so this is run once and the files kept in git. Usage: python3 states/mn/towns.py
"""
import json, os, subprocess, sys
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
from states.mn import profile as P

BASE = "https://www2.census.gov/geo/docs/maps-data/data/rel2020/cd-sld/tab20_{h}202420_{geo}20_st27.txt"


def rows(h, geo):
    url = BASE.format(h=h, geo=geo)
    text = subprocess.run(["curl", "-sSf", "--max-time", "120", url], capture_output=True, check=True).stdout.decode("utf-8-sig")
    lines = [l.split("|") for l in text.splitlines() if l.strip()]
    head = lines[0]
    return [dict(zip(head, l)) for l in lines[1:]]


def district(h, code):
    """The file's district code ("2712A" for House District 12A, "27012" for Senate District 12) -> seat number."""
    tail = code[2:]
    if h == "sldl":
        return P.house_seat(tail)
    return int(tail) if tail.isdigit() else None


def main():
    places = defaultdict(lambda: {"S": defaultdict(int), "H": defaultdict(int), "area": 1})
    size = {"S": defaultdict(int), "H": defaultdict(int)}  # each district's land area
    for h, letter in (("sldu", "S"), ("sldl", "H")):
        for geo in ("place", "county"):
            for r in rows(h, geo):
                d = district(h, r[f"GEOID_{h.upper()}2024_20"])
                if not d:
                    continue  # "ZZZ": land in no district
                size[letter][d] = max(size[letter][d], int(r[f"AREALAND_{h.upper()}2024_20"] or 0))
                name = (r.get(f"NAMELSAD_{geo.upper()}_20") or "").replace(" (balance)", "")
                mtfcc = r.get(f"MTFCC_{geo.upper()}_20")
                if not name or (geo == "place" and mtfcc != "G4110"):  # incorporated places only
                    continue
                p = places[name]
                p["area"] = max(1, int(r[f"AREALAND_{geo.upper()}_20"] or 0))
                p[letter][d] += int(r["AREALAND_PART"] or 0)
    out = []
    for name, p in places.items():
        share = {}
        for h in "SH":
            keep = [[d, round(100 * a / p["area"])] for d, a in p[h].items()
                    if a / p["area"] >= 0.005 or (size[h][d] and a / size[h][d] > 0.5)]
            share[h] = sorted(keep, key=lambda x: -x[1])
        if share["S"] and share["H"]:
            out.append([name, "", share["S"], share["H"]])
    out.sort(key=lambda r: r[0].lower())
    os.makedirs(P.DATA, exist_ok=True)
    path = os.path.join(P.DATA, "district_towns.json")
    json.dump(out, open(path, "w"), indent=0)
    names = {"H": {str(n): P.house_district(n) for n in range(1, 135)}}
    json.dump(names, open(P.DISTRICT_NAMES_PATH, "w"), indent=0)
    covered = {h: {d for r in out for d, _ in r[2 if h == "S" else 3]} for h in "SH"}
    print(f"{path}: {len(out)} cities and counties; {sum(1 for r in out if len(r[2]) == 1 and len(r[3]) == 1)} in one district "
          f"of each; districts covered: Senate {len(covered['S'])} of 67, House {len(covered['H'])} of 134")


if __name__ == "__main__":
    main()
