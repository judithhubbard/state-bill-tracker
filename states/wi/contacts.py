#!/usr/bin/env python3
"""Wisconsin's legislators and committees, written as data/wi/contacts_<session>.json in the shape build_data.py reads,
from data/wi/<session>/members.json and committees.json (states/wi/fetch.py: the Legislature's member pages, with
emails, phones and member ids, and each committee's page, with "(Chair)").

Seat ids "S:12", "A:82"; "id" is the member id the bills' author links use. A finished session's member list includes
members who left (two senators for one district): the later one keeps the seat. Usage: python3 states/wi/contacts.py
"""
import json, os, re, sys
from datetime import datetime
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
from fetch_contacts import committee_key, name_key
from states.wi import profile as P

PARTY = {"D": "Democratic", "R": "Republican", "I": "Independent"}


def build(session):
    folder = os.path.join(P.DATA, str(session))
    members = json.load(open(os.path.join(folder, "members.json")))
    people, by_id = {}, {}
    for m in members:
        h = "S" if m.get("house") == "senate" else "A"
        if not str(m.get("district") or "").isdigit():
            continue
        name = m.get("fullName") or m.get("name")
        phones = [p for p in m.get("telephone") or [] if p]
        sid = f"{h}:{int(m['district'])}"
        if sid in people and not (m.get("email") or m.get("telephone")):
            continue  # a member who left: the seat's current holder has contact details
        people[sid] = {
            "name": name, "key": name_key(name), "id": m.get("id"), "party": PARTY.get(m.get("party"), m.get("party") or ""),
            "email": (m.get("email") or [None])[0], "form": None, "phone": phones[0] if phones else None,
            "phones": [["Madison", p] for p in phones[:2]], "url": m.get("website") or None, "image": None,
            "office": ", ".join((m.get("office") or [])[:2]), "position": ", ".join(m.get("titles") or []) or None,
            "places": m.get("town") or "", "dataName": name,
        }
    for sid, p in people.items():
        by_id[str(p["id"])] = p["name"]
    comms = {"S": {}, "A": {}}
    try:
        committees = json.load(open(os.path.join(folder, "committees.json")))
    except (OSError, ValueError):
        committees = []
    for c in committees:
        h = {"senate": "S", "assembly": "A"}.get(c.get("kind"))
        if not h:
            continue  # joint committees: listed under neither house here
        name = re.sub(r"^(?:Assembly|Senate) Committee on\s+", "", c.get("name") or "")
        ms = c.get("members") or []
        names = sorted({by_id[str(x.get("id"))] for x in ms if str(x.get("id")) in by_id})
        chair = next((by_id.get(str(x.get("id"))) for x in ms if x.get("role") == "Chair"), None)
        comms[h][committee_key(name)] = {"name": name, "chair": chair, "meets": None, "members": names}
    leaders = {}
    for h, (name, role, _) in P.LEADERS.items():
        hit = next((p for sid, p in people.items() if sid[0] == h and p["key"] == name_key(name)), None)
        if hit:
            hit["position"] = role
            leaders[h] = {"name": hit["name"], "role": role}
    return {"session": session, "fetched": datetime.now(ZoneInfo(P.TIMEZONE)).strftime("%Y-%m-%d %H:%M"),
            "people": people, "since": {}, "senateCommittees": comms["S"], "assemblyCommittees": comms["A"],
            "leaders": leaders, "assemblyMembers": {}, "kept": []}


def main(session):
    out = build(session)
    if len(out["people"]) < 125:
        raise SystemExit(f"only {len(out['people'])} legislators; kept the last contacts")
    path = os.path.join(P.DATA, f"contacts_{session}.json")
    json.dump(out, open(path, "w"), indent=1, ensure_ascii=False)
    ppl = out["people"].values()
    comms = list(out["senateCommittees"].values()) + list(out["assemblyCommittees"].values())
    print(f"{path}: {len(out['people'])} legislators ({sum(1 for p in ppl if p['email'])} with email, "
          f"{sum(1 for p in ppl if p['phone'])} with a phone), {len(out['senateCommittees'])} Senate and "
          f"{len(out['assemblyCommittees'])} Assembly committees ({sum(1 for c in comms if c['chair'])} with a chair), "
          f"leaders {sorted(out['leaders'])}")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else P.session_of(datetime.now(ZoneInfo(P.TIMEZONE)).year))
