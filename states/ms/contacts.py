#!/usr/bin/env python3
"""Mississippi's legislators and committees, written as data/ms/contacts_<year>.json in the shape build_data.py reads.

All from the member files states/ms/fetch.py saves in data/ms/members/ (the Legislature's bill status system; no web
pages): each member's name, district, party, email (the user name, with the domain the Legislature's own stylesheets add:
@house.ms.gov or @senate.ms.gov), Capitol, business and home phones, Capitol room and committees, with "C" for the chair
and "V" the vice chair. Seat ids "S:12", "H:110": one senator or representative a district (52 and 122). The member files
are the current members only, so the file is written for the current year. "dataName" is the member's author link
("anderson_(110th)"), which the bills' authors use.
Leaders: the Speaker (a member) and the Lieutenant Governor, who presides over the Senate, names its committees and refers
its bills, but isn't a senator: his phone and email are from his website (checked 2026-11-08).
Usage: python3 states/ms/contacts.py [year]   (default: the current year)
"""
import json, os, re, sys
from datetime import datetime
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
from fetch_contacts import committee_key, name_key
from states.ms import convert as C
from states.ms import profile as P

# Committees that aren't standing committees bills go to.
NOT_STANDING = re.compile(r"committee of the whole|joint|legislative budget|PEER|subcommittee", re.I)


def build(year):
    people, members = {}, {}
    for (h, sl), m in C.current_members().items():
        sid = f"{h}:{m['district']}"
        page = "house" if h == "H" else "senate"
        p = {
            "name": m["name"], "key": name_key(m["name"]), "id": sl,
            "party": {"R": "Republican", "D": "Democratic", "I": "Independent"}.get(m["party"], m["party"] or None),
            "email": m["email"], "form": None,
            "phone": m["phones"][0][1] if m["phones"] else None, "phones": m["phones"],
            "url": f"https://billstatus.ls.state.ms.us/members/{page}/{sl}.xml",
            "image": None, "office": f"Room {m['room']}, New Capitol, Jackson" if m["room"] else "New Capitol, Jackson",
            "position": None, "places": ", ".join(m["counties"]), "dataName": sl,
        }
        if sid in people:  # two files claiming one seat (see C.DISTRICT_FIX): keep the first, and say so
            print(f"{sid} is claimed by {people[sid]['name']} and {p['name']}; kept {people[sid]['name']}", file=sys.stderr)
            continue
        people[sid] = p
        members[sid] = m
    comms = {"S": {}, "H": {}}
    for sid, m in members.items():
        h = sid[0]
        for name, officer in m["committees"]:
            if NOT_STANDING.search(name):
                continue
            c = comms[h].setdefault(committee_key(name), {"name": name, "chair": None, "viceChair": None,
                                                          "rankingMinority": None, "meets": None, "members": []})
            c["members"].append(people[sid]["name"])
            if officer == "C":
                c["chair"] = people[sid]["name"]
            elif officer == "V":
                c["viceChair"] = people[sid]["name"]
    for h in comms:
        for c in comms[h].values():
            c["members"] = sorted(set(c["members"]))
    now = year >= P.session_of(datetime.now(ZoneInfo(P.TIMEZONE)).year)
    leaders = {}
    if now:
        name, role, _ = P.LEADERS["H"]
        hit = next((p for sid, p in people.items() if sid[0] == "H" and p["key"] == name_key(name)), None)
        if hit:
            hit["position"] = role
            leaders["H"] = {"name": hit["name"], "role": role}
        # The Lieutenant Governor: phone and email from his website's page footer, ltgovhosemann.ms.gov (checked 2026-11-08).
        name, role, _ = P.LEADERS["S"]
        leaders["S"] = {"name": name, "role": role, "title": "Lt. Gov.", "url": "https://ltgovhosemann.ms.gov/",
                        "email": "ltgov@senate.ms.gov", "phone": "(601) 359-3200", "phones": [["Capitol", "(601) 359-3200"]],
                        "form": "https://ltgovhosemann.ms.gov/contact/"}
        pro = next((p for sid, p in people.items() if sid[0] == "S" and p["key"] == name_key("Dean Kirby")), None)
        if pro:
            pro["position"] = "President Pro Tempore"
        spt = next((p for sid, p in people.items() if sid[0] == "H" and p["key"] == name_key("Manly Barton")), None)
        if spt:
            spt["position"] = "Speaker Pro Tempore"
    return {"session": year, "fetched": datetime.now(ZoneInfo(P.TIMEZONE)).strftime("%Y-%m-%d %H:%M"),
            "people": people, "since": {}, "senateCommittees": comms["S"], "assemblyCommittees": comms["H"],
            "leaders": leaders, "assemblyMembers": {}, "kept": []}


def main(year):
    out = build(year)
    if len(out["people"]) < 160:
        raise SystemExit(f"only {len(out['people'])} legislators; kept the last contacts")
    path = os.path.join(P.DATA, f"contacts_{year}.json")
    json.dump(out, open(path, "w"), indent=1, ensure_ascii=False)
    ppl = out["people"].values()
    comms = list(out["senateCommittees"].values()) + list(out["assemblyCommittees"].values())
    print(f"{path}: {len(out['people'])} legislators ({sum(1 for p in ppl if p['email'])} with email, "
          f"{sum(1 for p in ppl if p['phone'])} with a phone), {len(out['senateCommittees'])} Senate and "
          f"{len(out['assemblyCommittees'])} House committees ({sum(1 for c in comms if c['chair'])} with a chair), "
          f"leaders {sorted(out['leaders'])}")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else P.session_of(datetime.now(ZoneInfo(P.TIMEZONE)).year))
