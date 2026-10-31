#!/usr/bin/env python3
"""Oregon's legislators and committees, from the Legislature's API tables downloaded by states/or/fetch.py (Legislators,
Committees, CommitteeMembers), written as data/or/contacts_<year>.json in the shape build_data.py reads. Each member has
party, district, Capitol phone, email and website; committee members have titles (Chair, Co-Chair, Vice-Chair). Joint
committees (Ways and Means) are listed for both houses. Seat ids "S:5", "H:19"; a member's id is the API's code ("Rep
Andersen"), which the votes use. Usage: python3 states/or/contacts.py [year]
"""
import importlib, json, os, sys
from datetime import datetime
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
from fetch_contacts import committee_key, name_key

P = importlib.import_module("states.or.profile")
C = importlib.import_module("states.or.convert")
PARTY = {"Democrat": "Democratic", "Republican": "Republican", "Independent": "Independent"}


def build(year):
    people, names = {}, {}
    for l in C.table(year, "Legislators"):
        h, d = l.get("Chamber"), str(l.get("DistrictNumber") or "")
        if h not in ("H", "S") or not d.isdigit():
            continue
        name = f"{l['FirstName']} {l['LastName']}"
        names[l["LegislatorCode"]] = name
        phone = l.get("CapitolPhone") or None
        people[f"{h}:{int(d)}"] = {
            "name": name, "key": name_key(name), "id": l["LegislatorCode"], "party": PARTY.get(l.get("Party"), l.get("Party") or ""),
            "email": l.get("EmailAddress") or None, "form": None, "phone": phone, "phones": [["Salem", phone]] if phone else [],
            "url": l.get("WebSiteUrl") or None, "image": None, "office": "", "position": None, "places": "",
            "dataName": l["LastName"],
        }
    members = {}
    for m in C.table(year, "CommitteeMembers"):
        members.setdefault(m["CommitteeCode"], []).append(m)
    s_comms, h_comms = {}, {}
    for c in C.table(year, "Committees"):
        ms = members.get(c["CommitteeCode"], [])
        if not ms or c.get("ParentCommitteeCode"):
            continue  # subcommittees (Ways and Means' are listed under it) and empty committees
        chairs = [names.get(m["LegislatorCode"]) for m in ms if m.get("Title") in ("Chair", "Co-Chair") and m["LegislatorCode"] in names]
        entry = {"name": c["CommitteeName"], "chair": " and ".join(chairs) or None, "meets": None,
                 "members": sorted({names[m["LegislatorCode"]] for m in ms if m["LegislatorCode"] in names and m.get("Title") != "Alternate"})}
        for h, out in (("S", s_comms), ("H", h_comms)):
            if c.get("HouseOfAction") in (h, "J"):
                out[committee_key(c["CommitteeName"])] = entry
    leaders = {}
    for h, (name, role, _) in P.LEADERS.items():
        hit = next((p for sid, p in people.items() if sid[0] == h and p["key"] == name_key(name)), None)
        if hit:
            hit["position"] = role
            leaders[h] = {"name": hit["name"], "role": role}
    return {"session": year, "fetched": datetime.now(ZoneInfo(P.TIMEZONE)).strftime("%Y-%m-%d %H:%M PT"),
            "people": people, "since": {}, "senateCommittees": s_comms, "assemblyCommittees": h_comms,
            "leaders": leaders, "assemblyMembers": {}, "kept": []}


def main(year):
    out = build(year)
    path = os.path.join(P.DATA, f"contacts_{year}.json")
    json.dump(out, open(path, "w"), indent=1, ensure_ascii=False)
    ppl = out["people"].values()
    comms = list(out["senateCommittees"].values()) + list(out["assemblyCommittees"].values())
    print(f"{path}: {len(out['people'])} legislators ({sum(1 for p in ppl if p['phone'])} with a phone, "
          f"{sum(1 for p in ppl if p['email'])} with email, {sum(1 for p in ppl if p['party'])} with party), "
          f"{len(out['senateCommittees'])} Senate and {len(out['assemblyCommittees'])} House committees "
          f"({sum(1 for c in comms if c['chair'])} with chairs), leaders {sorted(out['leaders'])}")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else datetime.now(ZoneInfo(P.TIMEZONE)).year)
