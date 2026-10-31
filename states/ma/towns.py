#!/usr/bin/env python3
"""Each Massachusetts city and town and the Senate and House districts that cover it, for "Where you live", and the
districts' names (Massachusetts names its districts: "8th Middlesex", "Hampden and Hampshire").

data/ma/district_towns.json: [["Amherst town", "", [[7, 100]], [[24, 60], ...]], ...]: town, (unused), Senate and House
districts, each [seat number, percent of the town's land in it]. Seat numbers are the Census codes' last digits
(Senate "25D07" -> 7, House "25024" -> 24). data/ma/district_names.json: {"S": {"7": "Hampshire, Franklin and
Worcester"}, "H": {"24": "3rd Hampshire"}}, the Census names without " District".

From the Census Bureau's relationship files between the 2024 state legislative districts and 2020 county subdivisions
(www2.census.gov/geo/docs/maps-data/data/rel2020/cd-sld/, no key needed). Fixed until the 2031 redistricting, so this
is run once and both files kept in git. Usage: python3 states/ma/towns.py
"""
import json, os, re, subprocess, sys
from collections import defaultdict

DATA = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "ma"))
BASE = "https://www2.census.gov/geo/docs/maps-data/data/rel2020/cd-sld/tab20_{h}202420_cousub20_st25.txt"


def rows(h):
    text = subprocess.run(["curl", "-sSf", "--max-time", "120", BASE.format(h=h)], capture_output=True, check=True).stdout.decode("utf-8-sig")
    lines = [l.split("|") for l in text.splitlines() if l.strip()]
    return [dict(zip(lines[0], l)) for l in lines[1:]]


def main():
    places = defaultdict(lambda: {"S": defaultdict(int), "H": defaultdict(int), "area": 1})
    names = {"S": {}, "H": {}}
    for h, letter in (("sldu", "S"), ("sldl", "H")):
        for r in rows(h):
            code = re.sub(r"\D", "", r[f"GEOID_{h.upper()}2024_20"][2:])
            name = r.get("NAMELSAD_COUSUB_20")
            if not code or not name or r.get("MTFCC_COUSUB_20") != "G4040" or name.startswith("County subdivisions not defined"):
                continue
            d = int(code)
            names[letter][str(d)] = re.sub(r"\s+District$", "", r[f"NAMELSAD_{h.upper()}2024_20"])
            p = places[name]
            p["area"] = max(1, int(r["AREALAND_COUSUB_20"] or 0))
            p[letter][d] += int(r["AREALAND_PART"] or 0)
    out = []
    for name, p in places.items():
        share = {h: sorted(([d, round(100 * a / p["area"])] for d, a in p[h].items() if a / p["area"] >= 0.005), key=lambda x: -x[1]) for h in "SH"}
        if share["S"] and share["H"]:
            out.append([name, "", share["S"], share["H"]])
    out.sort(key=lambda r: r[0].lower())
    os.makedirs(DATA, exist_ok=True)
    json.dump(out, open(os.path.join(DATA, "district_towns.json"), "w"), indent=0)
    json.dump(names, open(os.path.join(DATA, "district_names.json"), "w"), indent=0)
    print(f"{len(out)} towns; {len(names['S'])} Senate and {len(names['H'])} House district names")


if __name__ == "__main__":
    main()
