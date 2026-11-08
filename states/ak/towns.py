#!/usr/bin/env python3
"""Each Alaska city, community, borough and census area and the Senate and House districts that cover it, for "Where you
live": data/ak/district_towns.json: [["Bethel city", "", [[19, 100]], [[38, 100]]], ...]: place, (unused), Senate and House
districts, each [district, percent of the place's land in it]. Senate districts are letters (A to T), numbered 1 to 20
here and in the seat ids; data/ak/district_names.json gives the page their letters ({"S": {"1": "A", ...}}).

From the Census Bureau's relationship files between the 2024 state legislative districts and 2020 places and counties
(www2.census.gov/geo/docs/maps-data/data/rel2020/cd-sld/, no key needed), which give each overlap's land area. Alaska has
no counties: the county files hold its boroughs and census areas (the Unorganized Borough's parts). Most Alaska
communities aren't incorporated, so Census-designated places are listed too, unlike Indiana's list. Slivers along
boundaries (under 0.5% of the place, unless the place holds most of the district) are left out. The districts are fixed until the next redistricting (2031), so this is
run once and the files kept in git. Usage: python3 states/ak/towns.py
"""
import json, os, subprocess, sys
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
from states.ak import profile as P

BASE = "https://www2.census.gov/geo/docs/maps-data/data/rel2020/cd-sld/tab20_{h}202420_{geo}20_st02.txt"


def rows(h, geo):
    url = BASE.format(h=h, geo=geo)
    text = subprocess.run(["curl", "-sSf", "--max-time", "120", url], capture_output=True, check=True).stdout.decode("utf-8-sig")
    lines = [l.split("|") for l in text.splitlines() if l.strip()]
    head = lines[0]
    return [dict(zip(head, l)) for l in lines[1:]]


def main():
    places = defaultdict(lambda: {"S": defaultdict(int), "H": defaultdict(int), "area": 1, "name": "", "whole": {}})
    for h, letter in (("sldu", "S"), ("sldl", "H")):
        for geo in ("place", "county"):
            for r in rows(h, geo):
                name = r.get(f"NAMELSAD_{geo.upper()}_20") or ""
                mtfcc = r.get(f"MTFCC_{geo.upper()}_20")
                if not name or (geo == "place" and mtfcc not in ("G4110", "G4210")):  # cities and Census-designated places
                    continue
                code = r[f"GEOID_{h.upper()}2024_20"][-3:]
                if letter == "S" and code[:2] == "00" and code[2:].isalpha():
                    d = P.senate_number(code[2])  # "00A" -> 1
                elif letter == "H" and code.isdigit():
                    d = int(code)
                else:
                    continue  # "ZZZ": land in no district
                # Anchorage and Juneau are both a city and a borough ("Anchorage municipality" in the places file,
                # "Anchorage Municipality" in the county file): one entry, with the borough's spelling.
                p = places[(name.lower(), geo)]
                p["name"] = name
                p["area"] = max(1, int(r[f"AREALAND_{geo.upper()}_20"] or 0))
                p[letter][d] += int(r["AREALAND_PART"] or 0)
                p["whole"].setdefault(letter, {})[d] = max(1, int(r[f"AREALAND_{h.upper()}2024_20"] or 0))
    out = []
    for (key, geo), p in places.items():
        if geo == "place" and (key, "county") in places:
            continue
        name = p["name"]
        # A district counts when it's at least 0.5% of the place, or the place holds most of it (Anchorage's small urban
        # districts are each under 0.5% of the municipality's land).
        share = {h: sorted(([d, round(100 * a / p["area"])] for d, a in p[h].items()
                            if a / p["area"] >= 0.005 or a / p["whole"].get(h, {}).get(d, 1e18) >= 0.5), key=lambda x: -x[1]) for h in "SH"}
        if share["S"] and share["H"]:
            out.append([name, "", share["S"], share["H"]])
    out.sort(key=lambda r: r[0].lower())
    os.makedirs(P.DATA, exist_ok=True)
    json.dump(out, open(P.TOWNS_PATH, "w"), indent=0)
    json.dump({"S": {str(i): chr(64 + i) for i in range(1, 21)}}, open(P.DISTRICT_NAMES_PATH, "w"))
    print(f"{P.TOWNS_PATH}: {len(out)} places, boroughs and census areas; "
          f"{sum(1 for r in out if len(r[2]) == 1 and len(r[3]) == 1)} in one district of each")


if __name__ == "__main__":
    main()
