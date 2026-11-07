#!/usr/bin/env python3
"""Colorado's legislators and committees, written as data/co/contacts_<year>.json in the shape build_data.py reads, from
data/co/<year>/members.json and committees.json (states/co/fetch.py: leg.colorado.gov's member and committee pages).
Seat ids "S:18", "H:12"; each member's id is the site's slug ("judy-amabile"), which the bill pages use for sponsors.
Committees are each house's committees of reference, with their chairs.
Usage: python3 states/co/contacts.py [year]
"""
import json, os, re, sys
from datetime import datetime
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
from fetch_contacts import committee_key, name_key
from states.co import profile as P

PARTY = {"Democrat": "Democratic", "Republican": "Republican"}


def build(year):
    folder = os.path.join(P.DATA, str(year))
    people = {}
    for m in json.load(open(os.path.join(folder, "members.json")))["members"]:
        page = m.get("page") or {}
        h = {"Senator": "S", "Representative": "H"}.get(m.get("title"))
        district = str(m.get("district") or page.get("district") or "")
        if not h or not district.isdigit():
            continue  # a vacancy ("District 21")
        last, _, first = (m.get("name") or "").partition(", ")
        name = page.get("fullName") or f"{first} {last}".strip()
        phone = page.get("phone") or m.get("phone") or ""
        people[f"{h}:{int(district)}"] = {
            "name": name, "key": name_key(name), "id": m["slug"],
            "party": PARTY.get(page.get("party") or m.get("party"), page.get("party") or m.get("party") or ""),
            "email": page.get("email") or m.get("email") or None, "form": None,
            "phone": phone or None, "phones": [["Capitol", phone]] if phone else [],
            "url": f"https://leg.colorado.gov/legislators/{m['slug']}", "image": None, "office": page.get("address") or "",
            "position": page.get("leadership") or None, "places": ", ".join(page.get("counties") or []),
            "dataName": last,
        }
    comms = {"S": {}, "H": {}}
    for c in json.load(open(os.path.join(folder, "committees.json")))["committees"]:
        m = re.search(r"/committees/\w+/(house|senate)/", c.get("href") or "")
        if not m:
            continue  # year-round and interim committees see no bills during the session
        h = "H" if m.group(1) == "house" else "S"
        members = c.get("members") or []
        chair = next((x["name"] for x in members if x.get("role") == "Chair"), None)
        comms[h][committee_key(c["name"])] = {"name": c["name"], "chair": chair, "meets": None,
                                               "members": sorted(x["name"] for x in members)}
    leaders = {}
    if year < datetime.now(ZoneInfo(P.TIMEZONE)).year:
        # A past year's member pages show positions held today (James Coleman wasn't Senate President in 2024), so a
        # past year's positions and leaders are left out rather than shown wrong.
        for p in people.values():
            p["position"] = None
        return {"session": year, "fetched": datetime.now(ZoneInfo(P.TIMEZONE)).strftime("%Y-%m-%d %H:%M"),
                "people": people, "since": {}, "senateCommittees": comms["S"], "assemblyCommittees": comms["H"],
                "leaders": {}, "assemblyMembers": {}, "kept": []}
    for h, (name, role, _) in P.LEADERS.items():
        hit = (next((p for sid, p in people.items() if sid[0] == h and p["position"] == role), None)
               or next((p for sid, p in people.items() if sid[0] == h and p["key"] == name_key(name)), None))
        if hit:
            hit["position"] = role
            leaders[h] = {"name": hit["name"], "role": role}
    return {"session": year, "fetched": datetime.now(ZoneInfo(P.TIMEZONE)).strftime("%Y-%m-%d %H:%M"),
            "people": people, "since": {}, "senateCommittees": comms["S"], "assemblyCommittees": comms["H"],
            "leaders": leaders, "assemblyMembers": {}, "kept": []}


def main(year):
    out = build(year)
    if len(out["people"]) < 90:
        raise SystemExit(f"only {len(out['people'])} legislators; kept the last contacts")
    path = os.path.join(P.DATA, f"contacts_{year}.json")
    json.dump(out, open(path, "w"), indent=1, ensure_ascii=False)
    ppl = out["people"].values()
    comms = list(out["senateCommittees"].values()) + list(out["assemblyCommittees"].values())
    print(f"{path}: {len(out['people'])} legislators ({sum(1 for p in ppl if p['email'])} with email, "
          f"{sum(1 for p in ppl if p['phone'])} with a phone), {len(comms)} committees ({sum(1 for c in comms if c['chair'])} "
          f"with a chair), leaders {sorted(out['leaders'])}")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else P.session_of(datetime.now(ZoneInfo(P.TIMEZONE)).year))
