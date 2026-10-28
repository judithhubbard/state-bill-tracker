#!/usr/bin/env python3
"""Which legislative district each New Jersey town is in, for "Where you live": writes
data/nj/district_towns.json as [[town, county, [[district, share of its people], ...]], ...].

The districts are the Apportionment Commission's map for 2022-2031 (its municipalities table, which
lists a split town under each of its districts); full town names ("Washington township") come from the
Census Bureau's list, matched by the same codes. Run again only when the districts are redrawn.
"""
import io, json, os, re, sys, urllib.request, zipfile
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
from states.nj import profile as P

TABLE = "https://www.apportionmentcommission.org/documents/2022/NJ_LDS22_30_DEMOGR_MCDS_AND_SPLITS.xlsx"
NAMES = "https://www2.census.gov/geo/docs/maps-data/data/gazetteer/2020_Gazetteer/2020_gaz_cousubs_34.txt"
COUNTY = {f"{2 * i + 1:03d}": c for i, c in enumerate(P.COUNTIES)}  # FIPS 001 Atlantic ... 041 Warren


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "statebilltracker.org data fetch"})
    return urllib.request.urlopen(req, timeout=120).read()


def table_rows(xlsx):
    """The spreadsheet's rows as lists of cell values (no spreadsheet library needed)."""
    z = zipfile.ZipFile(io.BytesIO(xlsx))
    strings = [re.sub(r"<[^>]+>", "", s) for s in re.findall(r"<si>(.*?)</si>", z.read("xl/sharedStrings.xml").decode(), re.S)]
    for row in re.findall(r"<row[^>]*>(.*?)</row>", z.read("xl/worksheets/sheet1.xml").decode(), re.S):
        cells = []
        for attrs, v in re.findall(r'<c r="[A-Z]+\d+"([^>]*)>(?:<f>.*?</f>)?(?:<v>([^<]*)</v>)?', row):
            cells.append(strings[int(v)] if 't="s"' in attrs and v else v)
        yield cells


def main():
    names = {}
    for line in get(NAMES).decode("utf-8").splitlines()[1:]:
        f = line.split("\t")
        names[f[1]] = f[3].strip()  # GEOID -> "Washington township"
    people = defaultdict(lambda: defaultdict(int))
    for cells in list(table_rows(get(TABLE)))[1:]:
        geoid, name, district, pop = cells[:4]
        if not geoid or int(pop or 0) == 0:
            continue
        people[geoid][int(district)] += int(pop)
    out = []
    for geoid, by_district in people.items():
        total = sum(by_district.values())
        # "Washington township" -> "Washington Township"; cities by their plain names ("Newark city" -> "Newark").
        town = re.sub(r" city$", "", names[geoid])
        town = re.sub(r"\b(borough|township|town|village)$", lambda m: m.group(1).title(), town)
        out.append([town, COUNTY[geoid[2:5]],
                    sorted(([d, round(100 * n / total)] for d, n in by_district.items()), key=lambda x: -x[1])])
    out.sort(key=lambda t: (t[0].lower(), t[1]))
    path = os.path.join(P.DATA, "district_towns.json")
    with open(path, "w") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
    split = [t for t in out if len(t[2]) > 1]
    print(f"{path}: {len(out)} towns, {len(split)} split between districts: " + ", ".join(f"{t[0]} {[d for d, _ in t[2]]}" for t in split))


if __name__ == "__main__":
    main()
