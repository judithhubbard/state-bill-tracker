#!/usr/bin/env python3
"""Each Wisconsin city, village and town and the Senate and Assembly districts that cover it, for "Where you live":
data/wi/district_towns.json: [["Madison city", "", [[26, 40], ...], [[76, 20], ...]], ...]: place, (unused), Senate and Assembly
districts, each [district, percent of the place's land in it]. Names that repeat in several counties (many towns share a name) carry their county: "Lincoln town (Adams County)".

From the Census Bureau's relationship files between the 2024 state legislative districts and 2020 county subdivisions
(www2.census.gov/geo/docs/maps-data/data/rel2020/cd-sld/, no key needed). Wisconsin's county subdivisions are its cities,
villages and towns. Fixed until the 2031 redistricting, so this is run once and the file kept
in git. Usage: python3 states/wi/towns.py
"""
import json, os, re, subprocess
from collections import Counter, defaultdict

DATA = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "wi"))
BASE = "https://www2.census.gov/geo/docs/maps-data/data/rel2020/cd-sld/tab20_{h}202420_{geo}20_st55.txt"


def rows(h, geo):
    text = subprocess.run(["curl", "-sSf", "--max-time", "120", BASE.format(h=h, geo=geo)], capture_output=True, check=True).stdout.decode("utf-8-sig")
    lines = [l.split("|") for l in text.splitlines() if l.strip()]
    return [dict(zip(lines[0], l)) for l in lines[1:]]


def main():
    county = {r["GEOID_COUNTY_20"]: r["NAMELSAD_COUNTY_20"] for r in rows("sldu", "county")}
    places = defaultdict(lambda: {"S": defaultdict(int), "H": defaultdict(int), "area": 1, "name": ""})
    for h, letter in (("sldu", "S"), ("sldl", "H")):
        for r in rows(h, "cousub"):
            code = re.sub(r"\D", "", r[f"GEOID_{h.upper()}2024_20"][2:])
            geoid, name = r.get("GEOID_COUSUB_20") or "", r.get("NAMELSAD_COUSUB_20")
            if not code or not name or name.startswith("County subdivisions not defined"):
                continue
            # Cities and villages have unique names and can cross county lines (Milwaukee): one entry each.
            p = places[name if re.search(r" (?:city|village)$", name) else geoid]
            p["name"], p["county"] = name, county.get(geoid[:5], "")
            p.setdefault("areas", {})[geoid] = int(r["AREALAND_COUSUB_20"] or 0)
            p["area"] = max(1, sum(p["areas"].values()))
            p[letter][int(code)] += int(r["AREALAND_PART"] or 0)
    seen = Counter(p["name"] for p in places.values())
    out = []
    for p in places.values():
        share = {h: sorted(([d, round(100 * a / p["area"])] for d, a in p[h].items() if a / p["area"] >= 0.005), key=lambda x: -x[1]) for h in "SH"}
        if share["S"] and share["H"]:
            out.append([p["name"] + (f" ({p['county']})" if seen[p["name"]] > 1 else ""), "", share["S"], share["H"]])
    out.sort(key=lambda r: r[0].lower())
    os.makedirs(DATA, exist_ok=True)
    json.dump(out, open(os.path.join(DATA, "district_towns.json"), "w"), indent=0)
    print(f"{len(out)} municipalities; {sum(1 for r in out if len(r[2]) == 1 and len(r[3]) == 1)} in one district of each")


if __name__ == "__main__":
    main()
