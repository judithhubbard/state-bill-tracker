#!/usr/bin/env python3
"""Each Vermont town and city (and the unorganized gores and grants), with the Senate and House districts that cover it,
for "Where you live": data/vt/district_towns.json: [["Barre City", "Washington", [[13, 100]], [[94, 100]]], ...]:
place, county, Senate districts and House districts, each [district, percent of the place's land in it]. Also
data/vt/district_names.json: {"S": {"4": "Chittenden Central", ...}, "H": {"37": "Chittenden-17", ...}}.

Vermont's districts have names, not numbers: the Senate's 16 are counties or parts of them ("Chittenden Central"), with
one to three senators each (30 in all); the House's 109 are towns or groups of towns ("Chittenden-17",
"Orange-Washington-Addison"), with one or two representatives each (150). Seat ids number them in alphabetical order
(the number that follows a hyphen read as a number: Chittenden-2 before Chittenden-10), and the page shows the names.

From the Census Bureau's relationship files between the 2024 state legislative districts and 2020 county subdivisions
(Vermont's towns and cities; www2.census.gov/geo/docs/maps-data/data/rel2020/cd-sld/, no key needed), which give each
overlap's land area. Slivers along boundaries (under 0.5% of the place) are left out. A city and a town with one name
(Barre, Rutland, St. Albans, Newport) are "Barre City" and "Barre Town". Villages are inside their towns. The districts
are fixed until the next reapportionment (2032), so this is run once and the files kept in git.
Usage: python3 states/vt/towns.py
"""
import json, os, re, subprocess, sys
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
from states.vt import profile as P

BASE = "https://www2.census.gov/geo/docs/maps-data/data/rel2020/cd-sld/tab20_{h}202420_cousub20_st50.txt"
COUNTIES = {"001": "Addison", "003": "Bennington", "005": "Caledonia", "007": "Chittenden", "009": "Essex", "011": "Franklin",
            "013": "Grand Isle", "015": "Lamoille", "017": "Orange", "019": "Orleans", "021": "Rutland", "023": "Washington",
            "025": "Windham", "027": "Windsor"}


def rows(h):
    text = subprocess.run(["curl", "-sSf", "--max-time", "120", BASE.format(h=h)], capture_output=True, check=True).stdout.decode("utf-8-sig")
    lines = [l.split("|") for l in text.splitlines() if l.strip()]
    return [dict(zip(lines[0], l)) for l in lines[1:]]


def district_name(full):
    """"Chittenden-17 State House District" -> "Chittenden-17"; "Chittenden South East Senatorial District" -> "Chittenden
    Southeast" (the Legislature's spelling)."""
    n = re.sub(r"\s+(?:State House|Senatorial) District$", "", full).strip()
    return n.replace("South East", "Southeast")


def natural(name):
    return [int(x) if x.isdigit() else x.lower() for x in re.split(r"(\d+)", name)]


def place_name(name, others):
    """"Burlington city" -> "Burlington"; "Barre city" -> "Barre City" when there's also a Barre town."""
    m = re.match(r"(.+?) (city|town|gore|grant|unorganized territory|location)$", name)
    if not m:
        return name
    base, kind = m.group(1), m.group(2)
    if kind in ("city", "town"):
        return f"{base} {kind.title()}" if sum(1 for o in others if re.match(re.escape(base) + r" (?:city|town)$", o)) > 1 else base
    return f"{base} {kind.title()}" if kind in ("gore", "grant") else name


def main():
    data = {h: rows(h) for h in ("sldu", "sldl")}
    names = {}
    for h, letter in (("sldu", "S"), ("sldl", "H")):
        ds = sorted({district_name(r[f"NAMELSAD_{h.upper()}2024_20"]) for r in data[h]
                     if not r[f"GEOID_{h.upper()}2024_20"].endswith("ZZZ")}, key=natural)
        names[letter] = {str(i + 1): d for i, d in enumerate(ds)}
    number = {h: {d: int(i) for i, d in names[h].items()} for h in names}
    all_names = {r["NAMELSAD_COUSUB_20"] for rs in data.values() for r in rs}
    places = defaultdict(lambda: {"S": defaultdict(int), "H": defaultdict(int), "area": 1, "county": ""})
    for h, letter in (("sldu", "S"), ("sldl", "H")):
        for r in data[h]:
            full = district_name(r[f"NAMELSAD_{h.upper()}2024_20"])
            if full not in number[letter]:
                continue  # land in no district
            p = places[r["GEOID_COUSUB_20"]]
            p["name"] = place_name(r["NAMELSAD_COUSUB_20"], all_names)
            p["county"] = COUNTIES.get(r["GEOID_COUSUB_20"][2:5], "")
            p["area"] = max(1, int(r["AREALAND_COUSUB_20"] or 0))
            p[letter][number[letter][full]] += int(r["AREALAND_PART"] or 0)
    out = []
    for p in places.values():
        share = {h: sorted(([d, round(100 * a / p["area"])] for d, a in p[h].items() if a / p["area"] >= 0.005), key=lambda x: -x[1]) for h in "SH"}
        if share["S"] and share["H"]:
            out.append([p["name"], p["county"], share["S"], share["H"]])
    out.sort(key=lambda r: (r[0].lower(), r[1]))
    os.makedirs(P.DATA, exist_ok=True)
    json.dump(out, open(P.TOWNS_PATH, "w"), indent=0)
    json.dump(names, open(P.DISTRICT_NAMES_PATH, "w"), indent=0)
    print(f"{P.TOWNS_PATH}: {len(out)} towns and cities; {sum(1 for r in out if len(r[2]) == 1 and len(r[3]) == 1)} in one district "
          f"of each; {len(names['S'])} Senate and {len(names['H'])} House districts")


if __name__ == "__main__":
    main()
