#!/usr/bin/env python3
"""The District's neighborhoods and the ward each is in, for "Find your Councilmember": data/dc/district_towns.json:
[["Adams Morgan", "", [[1, 100]]], ...]: neighborhood, (unused), and [[ward, 100]]. One list, as New Jersey's towns:
everyone has their ward's Councilmember and the five at-large members (STATE.atLarge).

From the District's open data (opendata.dc.gov, public, no key): "Wards from 2022" (the map drawn in 2022, used since the
2022 elections) and "Neighborhood Labels" (a point for each of 132 neighborhood names, where the city's maps print it),
from DC GIS's map service (maps2.dcgis.dc.gov). Each neighborhood is put in the ward that holds its label's point; a
neighborhood split between wards (Columbia Heights, Navy Yard) shows the ward around its label, so the page also offers
the address lookup (the Census geocoder files the wards as "State Legislative Districts - Upper": "Ward 2").
data/dc/district_names.json names the districts: wards 1-8 and "At-large" (9). The wards are fixed until the next
redistricting (after the 2030 census), so this is run once and both files kept in git. Usage: python3 states/dc/towns.py
"""
import json, os, sys, urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
from states.dc import profile as P

BASE = "https://maps2.dcgis.dc.gov/dcgis/rest/services/DCGIS_DATA/Administrative_Other_Boundaries_WebMercator/MapServer"
WARDS, LABELS = 53, 35
AGENT = "statebilltracker.org (a nonprofit bill tracker; contact via github.com/judithhubbard)"


def layer(n):
    url = f"{BASE}/{n}/query?where=1%3D1&outFields=*&outSR=4326&f=geojson"
    req = urllib.request.Request(url, headers={"User-Agent": AGENT})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.load(r)["features"]


def inside(pt, ring):
    """Ray casting: whether (x, y) is inside a ring of [x, y] points."""
    x, y = pt
    hit = False
    for (x1, y1), (x2, y2) in zip(ring, ring[1:] + ring[:1]):
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / ((y2 - y1) or 1e-12) + x1:
            hit = not hit
    return hit


def in_polygon(pt, geom):
    polys = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
    for poly in polys:
        if inside(pt, poly[0]) and not any(inside(pt, hole) for hole in poly[1:]):
            return True
    return False


def main():
    wards = [(int(f["properties"]["WARD"]), f["geometry"]) for f in layer(WARDS)]
    out, missing = [], []
    for f in layer(LABELS):
        name = (f["properties"].get("NAME") or "").strip()
        pt = f["geometry"]["coordinates"][:2]
        ward = next((w for w, g in wards if in_polygon(pt, g)), None)
        if not name:
            continue
        if ward is None:
            missing.append(name)
            continue
        out.append([name, "", [[ward, 100]]])
    seen, rows = set(), []
    for r in sorted(out, key=lambda r: r[0].lower()):
        if r[0] not in seen:
            seen.add(r[0])
            rows.append(r)
    os.makedirs(P.DATA, exist_ok=True)
    json.dump(rows, open(os.path.join(P.DATA, "district_towns.json"), "w"), indent=0)
    names = {"B": {**{str(w): f"Ward {w}" for w in range(1, 9)}, "9": "At-large"}}
    json.dump(names, open(os.path.join(P.DATA, "district_names.json"), "w"), indent=1)
    by = {}
    for r in rows:
        by.setdefault(r[2][0][0], 0)
        by[r[2][0][0]] += 1
    print(f"{len(rows)} neighborhoods; by ward {dict(sorted(by.items()))}; outside every ward: {missing}")


if __name__ == "__main__":
    main()
