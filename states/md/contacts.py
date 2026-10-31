#!/usr/bin/env python3
"""Maryland's legislators and committees, written as data/md/contacts_<session>.json in the shape build_data.py reads,
from data/md/members.json (states/md/fetch.py: each member's page on mgaleg.maryland.gov).

Maryland has 47 legislative districts, each with one senator and three delegates; some districts elect their delegates
from subdistricts ("44A", "44B"). As in New Jersey, a district's senator and all its delegates are its legislators: seat
ids "S:44", and "H:44a", "H:44b", "H:44c" for the delegates (the subdistrict is in "places"). "dataName" is how the bill
list names a member: "Ebersole", or "Lewis, R." where two members of a house share a last name.
Usage: python3 states/md/contacts.py
"""
import json, os, re, sys
from collections import Counter, defaultdict
from datetime import datetime
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
from fetch_contacts import committee_key, name_key
from states.md import profile as P

PARTY = {"Democrat": "Democratic", "Republican": "Republican"}


def last_name(name):
    words = [w for w in re.sub(r",.*$", "", name).split() if not re.fullmatch(r"(Jr|Sr|II|III|IV)\.?", w)]
    return words[-1] if words else name


def build(session):
    members = json.load(open(os.path.join(P.DATA, "members.json")))
    lasts = Counter((m["house"], last_name(m["name"])) for m in members)
    people, comms = {}, {"S": {}, "H": {}}
    by_district = defaultdict(list)
    for m in sorted(members, key=lambda m: (m["house"], m["district"], m["name"])):
        d = re.match(r"(\d+)", m["district"] or "")
        if not d:
            continue
        by_district[(m["house"], int(d.group(1)))].append(m)
    for (h, d), ms in by_district.items():
        for i, m in enumerate(ms):
            sid = f"S:{d}" if h == "S" else f"H:{d}{'abcdef'[i]}"
            last = last_name(m["name"])
            data_name = last if lasts[(h, last)] == 1 else f"{last}, {m['name'][0]}."
            phone = re.sub(r"(\d{3})-(\d{3})-(\d{4})", r"(\1) \2-\3", m.get("phone") or "")
            people[sid] = {
                "name": m["name"], "key": name_key(m["name"]), "id": m["code"], "party": PARTY.get(m["party"], m["party"]),
                "email": m.get("email"), "form": None, "phone": phone or None, "phones": [["Annapolis", phone]] if phone else [],
                "url": m["url"], "image": None, "office": "", "position": None,
                "places": f"District {m['district']} ({m['county']})" if h == "H" else m["county"], "dataName": data_name,
            }
            for c in m.get("committees") or []:
                name = re.sub(r"\s*\((?:Chair|Vice Chair|Co-Chair)\)$", "", c).replace(" Committee", "").strip()
                entry = comms[h].setdefault(committee_key(name), {"name": name, "chair": None, "meets": None, "members": []})
                entry["members"].append(m["name"])
                if c.endswith("(Chair)"):
                    entry["chair"] = m["name"]
    leaders = {}
    for h, (name, role, _) in P.LEADERS.items():
        hit = next((p for sid, p in people.items() if sid[0] == h and p["key"] == name_key(name)), None)
        if hit:
            hit["position"] = role
            leaders[h] = {"name": hit["name"], "role": role}
    return {"session": session, "fetched": datetime.now(ZoneInfo(P.TIMEZONE)).strftime("%Y-%m-%d %H:%M ET"),
            "people": people, "since": {}, "senateCommittees": comms["S"], "assemblyCommittees": comms["H"],
            "leaders": leaders, "assemblyMembers": {}, "kept": []}


def main(session):
    out = build(session)
    if len(out["people"]) < 180:
        raise SystemExit(f"only {len(out['people'])} legislators; kept the last contacts")
    path = os.path.join(P.DATA, f"contacts_{session}.json")
    json.dump(out, open(path, "w"), indent=1, ensure_ascii=False)
    ppl = out["people"].values()
    comms = list(out["senateCommittees"].values()) + list(out["assemblyCommittees"].values())
    print(f"{path}: {len(out['people'])} legislators ({sum(1 for p in ppl if p['email'])} with email, "
          f"{sum(1 for p in ppl if p['phone'])} with a phone), {len(out['senateCommittees'])} Senate and "
          f"{len(out['assemblyCommittees'])} House committees ({sum(1 for c in comms if c['chair'])} with a chair), "
          f"leaders {sorted(out['leaders'])}")


if __name__ == "__main__":
    main(P.session_of(datetime.now(ZoneInfo(P.TIMEZONE)).year))
