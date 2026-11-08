#!/usr/bin/env python3
"""Each Maine city, town, plantation and unorganized territory, and each county, with the Senate and House districts that
cover it, for "Where you live": data/me/district_towns.json: [["Allagash town", "", [[1, 100]], [[1, 100]]], ...]:
place, (unused), Senate and House districts, each [district, percent of the place's land in it].

From the Census Bureau's relationship files between the 2024 state legislative districts and 2020 county subdivisions and
counties (www2.census.gov/geo/docs/maps-data/data/rel2020/cd-sld/, no key needed). Maine's local governments are its
county subdivisions: cities, towns and plantations, plus the unorganized territories ("Northwest Aroostook UT"), where
the state and county govern the townships no town covers. Slivers along boundaries (under 0.5% of the place's land) are
left out, unless the place holds most of a district. A name used in two counties carries its county. The districts are
fixed until the next redistricting (2031), so this is run once and the file kept in git. Usage: python3 states/me/towns.py
"""
import json, os, subprocess, sys
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
import importlib
P = importlib.import_module("states.me.profile")

BASE = "https://www2.census.gov/geo/docs/maps-data/data/rel2020/cd-sld/tab20_{h}202420_{geo}20_st23.txt"
COUNTIES = {"001": "Androscoggin", "003": "Aroostook", "005": "Cumberland", "007": "Franklin", "009": "Hancock",
            "011": "Kennebec", "013": "Knox", "015": "Lincoln", "017": "Oxford", "019": "Penobscot", "021": "Piscataquis",
            "023": "Sagadahoc", "025": "Somerset", "027": "Waldo", "029": "Washington", "031": "York"}


def rows(h, geo):
    url = BASE.format(h=h, geo=geo)
    text = subprocess.run(["curl", "-sSf", "--max-time", "120", url], capture_output=True, check=True).stdout.decode("utf-8-sig")
    lines = [l.split("|") for l in text.splitlines() if l.strip()]
    head = lines[0]
    return [dict(zip(head, l)) for l in lines[1:]]


def main():
    places = defaultdict(lambda: {"S": defaultdict(int), "H": defaultdict(int), "area": 1, "county": ""})
    district_area = defaultdict(int)
    for h, letter in (("sldu", "S"), ("sldl", "H")):
        for geo in ("cousub", "county"):
            for r in rows(h, geo):
                G = geo.upper()
                name = r.get(f"NAMELSAD_{G}_20") or ""
                if not name or name.startswith("County subdivisions not defined"):
                    continue
                code = r[f"GEOID_{h.upper()}2024_20"][-3:]
                if not code.isdigit():
                    continue  # "ZZZ": land in no district (open water)
                d = int(code)
                geoid = r[f"GEOID_{G}_20"]
                key = (geo, geoid)
                p = places[key]
                p["name"], p["county"] = name, COUNTIES.get(geoid[2:5], "")
                p["area"] = max(1, int(r[f"AREALAND_{G}_20"] or 0))
                p[letter][d] += int(r["AREALAND_PART"] or 0)
                if geo == "cousub":
                    district_area[(letter, d)] += int(r["AREALAND_PART"] or 0)
    names = defaultdict(int)
    for (geo, _), p in places.items():
        names[p["name"]] += 1
    out = []
    for (geo, _), p in places.items():
        share = {h: sorted(([d, round(100 * a / p["area"])] for d, a in p[h].items()
                            if a / p["area"] >= 0.005 or (geo == "cousub" and a / max(1, district_area[(h, d)]) >= 0.5)),
                           key=lambda x: -x[1]) for h in "SH"}
        if share["S"] and share["H"]:
            name = p["name"] if names[p["name"]] == 1 or geo == "county" else f"{p['name']} ({p['county']} County)"
            out.append([name, "", share["S"], share["H"]])
    out.sort(key=lambda r: r[0].lower())
    path = os.path.join(P.DATA, "district_towns.json")
    os.makedirs(P.DATA, exist_ok=True)
    json.dump(out, open(path, "w"), indent=0)
    print(f"{path}: {len(out)} places and counties; {sum(1 for r in out if len(r[2]) == 1 and len(r[3]) == 1)} in one district of each")


if __name__ == "__main__":
    main()
