#!/usr/bin/env python3
"""Each Virginia locality (county or independent city) and the Senate and House districts that cover it,
from the district descriptions on the two houses' websites (in data/va/contacts_<session>.json, from
states/va/contacts.py), written as data/va/district_towns.json for "Where you live":
[["Fairfax County", "", [[34, 0], [35, 0], ...], [[5, 0], ...]], ...]: locality, (unused), Senate districts,
House districts. A district's share of the locality isn't published, so it's 0.

House descriptions: "Counties of James City (part) and New Kent (part); City of Williamsburg".
Senate descriptions: "All of Roanoke City and Salem City. Parts of Montgomery County and Roanoke County."
Usage: python3 states/va/towns.py [session]   (fetch.py runs it after contacts)
"""
import json, os, re, sys
from collections import defaultdict
from datetime import datetime
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
from states.va import profile as P


def names(listing):
    """"A (part), B (part), and C" -> ["A", "B", "C"] ("King and Queen" is one county)."""
    listing = re.sub(r"\s*\(part\)", "", listing).replace("King and Queen", "King&Queen")
    return [n.strip().replace("King&Queen", "King and Queen") for n in re.split(r",\s*(?:and\s+)?|\s+and\s+", listing) if n.strip()]


def house_places(desc):
    out = []
    for part in re.split(r";\s*", desc):
        m = re.match(r"(Count(?:y|ies)|Cit(?:y|ies)) of (.+)$", part.strip())
        if m:
            kind = "County" if m.group(1).startswith("Count") else "City"
            out += [f"{n} {kind}" for n in names(m.group(2))]
        else:
            # A plain list ("Alleghany County, Botetourt County, Buena Vista, Covington"): a bare name is a city.
            out += [n if re.search(r" (County|City)$", n) else f"{n} City" for n in names(part)]
    return out


def senate_places(desc):
    out = []
    for m in re.finditer(r"(?:All|Parts?) of ([^.]+)\.", desc):
        out += [re.sub(r"\s+", " ", n) for n in names(m.group(1))]
    return [n if re.search(r" (County|City)$", n) else n for n in out]


def main(session):
    people = json.load(open(os.path.join(P.DATA, f"contacts_{session}.json")))["people"]
    places = defaultdict(lambda: ([], []))
    for seat, p in people.items():
        house, district = seat.split(":")
        for place in (senate_places if house == "S" else house_places)(p.get("places") or ""):
            places[place][0 if house == "S" else 1].append([int(district), 0])
    # A slip in a description ("Counties of Chesapeake (part)") names a city as a county: Virginia has no county
    # that shares a name with a city only the House lists that way, so fold it into the city.
    for name in [n for n in places if n.endswith(" County")]:
        city = name[:-len("County")] + "City"
        if city in places and not places[name][0]:
            places[city][1].extend(places.pop(name)[1])
    # Every locality is in some Senate district; a name only a House list mentions is a town inside one
    # (Herndon, in Fairfax County), not a locality.
    out = sorted([[name, "", sorted(map(list, {tuple(x) for x in s})), sorted(map(list, {tuple(x) for x in h}))]
                  for name, (s, h) in places.items() if s], key=lambda t: t[0])
    path = os.path.join(P.DATA, "district_towns.json")
    json.dump(out, open(path, "w"))
    print(f"{path}: {len(out)} localities ({sum(1 for t in out if t[2] and t[3])} with both a Senate and a House district)")
    return out


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else P.session_of(datetime.now(ZoneInfo(P.TIMEZONE)).year))
