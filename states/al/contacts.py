#!/usr/bin/env python3
"""Alabama's legislators and committees, written as data/al/contacts_<session>.json in the shape build_data.py reads.

From what states/al/fetch.py downloads, no other web pages:
- data/al/members/members.json: every member record (the current ones with house, district, the counties it covers,
  party, leadership title, Montgomery office phone and address, district phone, email; past members with their name,
  district and party).
- data/al/members/committees.json: the current standing committees with their members ("Chairperson"/"Chair", "Vice
  Chairperson", "Ranking Minority Member", "Pro Tempore" ...).
Each district elects one member: seats "S:12", "H:45". The latest year lists the current members (with leadership posts
and committees); a past year lists everyone on its roll calls, from their records (a member who moved house, Matt
Woods, is in the House seat he held then: P.MOVED). The Lieutenant Governor presides over the Senate but isn't a senator,
and isn't listed.
Usage: python3 states/al/contacts.py [session]   (default: every year downloaded)
"""
import json, os, re, sys
from datetime import datetime
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
from fetch_contacts import committee_key, name_key
from states.al import convert as C
from states.al import profile as P

PARTY = {"R": "Republican", "D": "Democratic", "I": "Independent"}
LIST_URL = {"S": "https://alison.legislature.state.al.us/senate-leaders-members",
            "H": "https://alison.legislature.state.al.us/house-leaders-members"}


def phone(p):
    """"334-261-0530" / "(334) 261-0530 " -> "(334) 261-0530"."""
    d = re.sub(r"\D", "", p or "")
    if len(d) == 11 and d[0] == "1":
        d = d[1:]
    return f"({d[:3]}) {d[3:6]}-{d[6:]}" if len(d) == 10 else None


def person(m, h, district, latest):
    phones = []
    for label, ph in (("Montgomery office", phone(m.get("phone"))), ("District office", phone(m.get("districtPhone")))):
        if ph and ph not in [x[1] for x in phones]:
            phones.append([label, ph])
    office = re.sub(r"\s*\n\s*", ", ", (m.get("fullAddress") or "").strip()) or None
    if office and "No Address" in office:
        office = None
    title = (m.get("leadershipTitle") or "").strip()
    if title == "President Pro Tempore" and name_key(m["name"]) != name_key(P.LEADERS["S"][0]):
        title = ""  # the members list also gives Matt Woods this title (see P.LEADERS)
    return {
        "name": m["name"], "key": name_key(m["name"]), "id": m.get("id"), "party": PARTY.get(m.get("party"), m.get("party") or ""),
        "email": (m.get("email") or m.get("districtEmail") or "").strip() or None, "form": None,
        "phone": phones[0][1] if phones else None, "phones": phones, "url": LIST_URL[h],
        "image": None, "office": office, "position": (title or None) if latest else None,
        "places": (m.get("counties") or "") if latest else "", "dataName": m.get("last") or m["name"].split()[-1],
    }


def build(session):
    latest = session == max(C.sessions())
    people = {}
    voted = C.voters(session)
    for m in C.members():
        h = m["house"]
        if latest and not m.get("active"):
            continue
        if not latest and voted.get((h, m["name"]), 0) < 5:
            continue
        sid = f"{h}:{m['district']}"
        if sid in people:
            continue
        people[sid] = person(m, h, m["district"], latest)
    if not latest:
        for (h, name), d in P.MOVED.items():
            sid = f"{h}:{d}"
            m = next((x for x in C.members() if x["name"] == name), None)
            if m and voted.get((h, name), 0) >= 5:
                people[sid] = person({**m, "leadershipTitle": ""}, h, d, False)
    comms = {"S": {}, "H": {}}
    if latest:
        try:
            raw = json.load(open(os.path.join(P.DATA, "members", "committees.json"), encoding="utf-8")).get("committees") or []
        except (OSError, ValueError):
            raw = []
        for c in raw:
            if c.get("type") != "Standing" or c.get("body") not in ("House", "Senate"):
                continue
            h = c["body"][0]
            name = C.comm_name(c["name"])
            if name.endswith("County"):
                name += " Legislation"
            e = comms[h].setdefault(committee_key(name), {"name": name, "chair": None, "coChairs": [], "viceChair": None,
                                                          "meets": None, "members": []})
            for m in c.get("members") or []:
                who = (m.get("fullName") or "").strip()
                if not who:
                    continue
                if who not in e["members"]:
                    e["members"].append(who)
                pos = m.get("position") or ""
                if re.fullmatch(r"Chair(?:person|man)?", pos):
                    if e["chair"]:
                        e["coChairs"].append(who)
                    else:
                        e["chair"] = who
                elif re.match(r"Vice Chair", pos) and not e["viceChair"]:
                    e["viceChair"] = who
            e["members"].sort()
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
    if len(out["people"]) < 120:
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
