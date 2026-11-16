#!/usr/bin/env python3
"""Every city, town, community and county in the country and the congressional districts that cover it, for "Where you
live": data/us/district_towns.json: [["Abbeville city", "Alabama", [[1, 100]], [[102, 100]]], ...]: place, its state,
the state's Senate seat number (its FIPS code: both senators) and the House districts (seat numbers, 100 times the FIPS
code plus the district, as in profile.house_seat()), each [number, percent of the place's land in it]. The page asks
for the state first, then the place (STATE.townRegions).

From the Census Bureau's relationship files between the 119th Congress's districts and 2020 places and counties
(www2.census.gov/geo/docs/maps-data/data/rel2020/cd-sld/tab20_cd11920_place20_natl.txt and ..._county20_natl.txt; no
key; the site's robots.txt names only some search engines' crawlers), which give each overlap's land area.
Census-designated places (unincorporated communities) are listed too. Slivers along boundaries (under 0.5% of the
place) are left out, unless the place holds most of the district. At-large districts are "00" (the delegates' "98").
The 119th Congress's districts are those elected in 2024; several states drew new maps for 2026 (Texas, California,
Missouri, North Carolina, Ohio, Utah ...): run this again with the 120th Congress's files when the Census Bureau
publishes them. Also writes data/us/district_names.json (every seat's name, from profile.district_names()).
Usage: python3 states/us/towns.py
"""
import json, os, subprocess, sys
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
from states.us import profile as P

BASE = "https://www2.census.gov/geo/docs/maps-data/data/rel2020/cd-sld/tab20_cd11920_{geo}20_natl.txt"


def rows(geo):
    url = BASE.format(geo=geo)
    text = subprocess.run(["curl", "-sSf", "--max-time", "300", url], capture_output=True, check=True).stdout.decode("utf-8-sig")
    lines = [l.split("|") for l in text.splitlines() if l.strip()]
    head = lines[0]
    return [dict(zip(head, l)) for l in lines[1:]]


def main():
    places = defaultdict(lambda: {"H": defaultdict(int), "area": 1})
    district_area = defaultdict(int)
    for geo in ("place", "county"):
        for r in rows(geo):
            cd = r["GEOID_CD119_20"]
            fips, d = int(cd[:2]), cd[2:]
            if fips not in P.BY_FIPS or not d.isdigit() or d == "ZZ":
                continue
            seat = fips * 100 + (0 if d in ("00", "98") else int(d))
            name = r.get(f"NAMELSAD_{geo.upper()}_20")
            mtfcc = r.get(f"MTFCC_{geo.upper()}_20")
            if geo == "county":
                district_area[seat] += int(r["AREALAND_PART"] or 0)  # counties cover each state
            if not name or (geo == "place" and mtfcc not in ("G4110", "G4210")):  # cities, towns and communities
                continue
            key = (name[:-4] if name.endswith(" CDP") else name, fips)
            p = places[key]
            p["area"] = max(1, int(r[f"AREALAND_{geo.upper()}_20"] or 0))
            p["H"][seat] += int(r["AREALAND_PART"] or 0)
    out = []
    for (name, fips), p in places.items():
        share = sorted(([d, round(100 * a / p["area"])] for d, a in p["H"].items()
                        if a / p["area"] >= 0.005 or a / max(1, district_area[d]) >= 0.5), key=lambda x: -x[1])
        if not share:
            continue
        code, state = P.BY_FIPS[fips]
        out.append([name, state, [[fips, 100]] if code not in P.NONVOTING else [], share])
    out.sort(key=lambda r: (r[1], r[0].lower()))
    path = os.path.join(P.DATA, "district_towns.json")
    os.makedirs(P.DATA, exist_ok=True)
    json.dump(out, open(path, "w"), separators=(",", ":"), ensure_ascii=False)
    print(f"{path}: {len(out)} places and counties in {len({r[1] for r in out})} states and territories; "
          f"{len({d for r in out for d, _ in r[3]})} House seats listed; {os.path.getsize(path):,} bytes")
    from states.us import convert as C
    seats = {d for r in out for d, _ in r[3]}
    for c in C.CONGRESSES:
        seats |= {int(m["seats"]["H"][2:]) for m in C.members(c).values() if "H" in m["seats"]}
    json.dump(P.district_names(seats), open(P.DISTRICT_NAMES_PATH, "w"), separators=(",", ":"), ensure_ascii=False)
    print(f"{P.DISTRICT_NAMES_PATH}: {len(seats)} House seats named")


if __name__ == "__main__":
    main()
