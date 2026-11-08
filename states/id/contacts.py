#!/usr/bin/env python3
"""Idaho's legislators and committees, written as data/id/contacts_<session>.json in the shape build_data.py reads.

From what states/id/fetch.py downloads, no other web pages:
- data/id/members/members.json (the current members: name, party, district, House seat A or B, leadership post, home and
  Statehouse phones, email, address, committees with "Chair"/"Vice Chair"), for the latest year.
- data/id/<session>/committees/*.html: each standing committee's members that year (chair and vice chair marked,
  district, Statehouse phone, email; Republicans and Democrats in two columns), for the committees and, in past years,
  the members (a member who left during the year may be missing; one marked "Resigned" has no district).
Each district elects a senator and two representatives (House seats A and B): seats "S:12", "H:12a", "H:12b"
(convert.roster()). The Joint Finance-Appropriations Committee isn't listed: bills aren't referred to it.
Usage: python3 states/id/contacts.py [session]   (default: every year downloaded)
"""
import json, os, re, sys
from datetime import datetime
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
from fetch_contacts import committee_key, name_key
from states.id import convert as C
from states.id import profile as P

PARTY = {"R": "Republican", "D": "Democratic", "I": "Independent"}


def build(session):
    latest = session == max(C.sessions())
    roster = C.roster(session)
    names = C.committee_names(session)
    people = {}
    for p in roster.values():
        sid = p.get("sid")
        if not sid:
            continue
        phones = []
        for label, ph in (("Statehouse (session only)", p.get("phone")), ("Home", p.get("home"))):
            if ph and ph not in [x[1] for x in phones]:
                phones.append([label, ph])
        people[sid] = {
            "name": p["name"], "key": name_key(p["name"]), "id": p.get("id"), "party": PARTY.get(p["party"], p["party"] or ""),
            "email": p.get("email") or None, "form": None,
            "phone": phones[0][1] if phones else None, "phones": phones,
            "url": f"https://legislature.idaho.gov/legislators/membership/{session}/id{p['id']}" if p.get("id") else
                   "https://legislature.idaho.gov/" + ("senate" if p["house"] == "S" else "house") + "/membership/",
            "image": None, "office": p.get("address") or None,
            "position": (p.get("post") or None) if latest else None, "places": "", "dataName": C.surname(p["name"]),
        }
    # Members the year's committee pages leave out (the Speaker serves on none) whose votes that year were tied to a
    # current member's seat (convert.resolver()): their entry from the current list, without its leadership post.
    if not latest:
        voted = {m for r in C.load_session(session)[0] for v in r["votes"] for m, _ in v[6] if ":" in m}
        for c in C.current_members():
            sid = f"S:{c['district']}" if c["house"] == "S" else f"H:{c['district']}{(c.get('seat') or '').lower()}"
            if sid in voted and sid not in people:
                name = C.plain_name(c["name"])
                people[sid] = {"name": name, "key": name_key(name), "id": None, "party": PARTY.get(c["party"], ""),
                               "email": c.get("email") or None, "form": None, "phone": c.get("statehouse") or None,
                               "phones": [["Statehouse (session only)", c["statehouse"]]] if c.get("statehouse") else [],
                               "url": "https://legislature.idaho.gov/" + ("senate" if c["house"] == "S" else "house") + "/membership/",
                               "image": None, "office": c.get("address") or None, "position": None, "places": "",
                               "dataName": C.surname(name)}
    comms = {"S": {}, "H": {}}
    for p in roster.values():
        for code, role in p["committees"]:
            h = code[0]
            if h not in comms or code not in names:
                continue
            name = names[code]
            c = comms[h].setdefault(committee_key(name), {"name": name, "chair": None, "coChairs": [], "viceChair": None,
                                                          "meets": None, "members": []})
            if p["name"] not in c["members"]:
                c["members"].append(p["name"])
            if re.fullmatch(r"Chair(?:man)?", role or ""):
                if c["chair"]:
                    c["coChairs"].append(p["name"])
                else:
                    c["chair"] = p["name"]
            elif re.fullmatch(r"Vice Chair(?:man)?", role or ""):
                c["viceChair"] = p["name"]
    for h in comms:
        for c in comms[h].values():
            c["members"].sort()
    leaders = {}
    if latest:
        for h, (name, role, _) in P.LEADERS.items():
            hit = next((x for sid, x in people.items() if sid[0] == h and x["key"] == name_key(name)), None)
            if hit:
                leaders[h] = {"name": hit["name"], "role": role}
    return {"session": session, "fetched": datetime.now(ZoneInfo(P.TIMEZONE)).strftime("%Y-%m-%d %H:%M"),
            "people": people, "since": {}, "senateCommittees": comms["S"], "assemblyCommittees": comms["H"],
            "leaders": leaders, "assemblyMembers": {}, "kept": []}


def main(session):
    out = build(session)
    if len(out["people"]) < 90:
        raise SystemExit(f"{session}: only {len(out['people'])} legislators; kept the last contacts")
    path = os.path.join(P.DATA, f"contacts_{session}.json")
    json.dump(out, open(path, "w"), indent=1, ensure_ascii=False)
    ppl = out["people"].values()
    comms = list(out["senateCommittees"].values()) + list(out["assemblyCommittees"].values())
    print(f"{path}: {len(out['people'])} legislators ({sum(1 for p in ppl if p['email'])} with email, "
          f"{sum(1 for p in ppl if p['phone'])} with a phone), {len(out['senateCommittees'])} Senate and "
          f"{len(out['assemblyCommittees'])} House committees ({sum(1 for c in comms if c['chair'])} with a chair), "
          f"leaders {sorted(out['leaders'])}")


if __name__ == "__main__":
    for s in ([int(sys.argv[1])] if len(sys.argv) > 1 else C.sessions()):
        main(s)
