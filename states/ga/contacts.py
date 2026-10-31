#!/usr/bin/env python3
"""Georgia's legislators and committees, written as data/ga/contacts_<session>.json in the shape build_data.py reads,
from the members and committees states/ga/fetch.py saved (data/ga/<session>/members.json, committees.json: the web
services' member listing and detail, committee detail with members and roles).

Seat ids "S:37", "H:50"; "id" is the member id the bills' authors and the roll calls use. Members who left mid-session
(DateVacated) are skipped. The Senate's presiding officer, the Lieutenant Governor, isn't a senator.
Usage: python3 states/ga/contacts.py [session]
"""
import json, os, re, sys
from datetime import datetime
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
from fetch_contacts import committee_key, name_key
from states.ga import profile as P

PARTY = {"Democrat": "Democratic", "Republican": "Republican"}


def phone(p):
    d = re.sub(r"\D", "", p or "")
    return f"({d[:3]}) {d[3:6]}-{d[6:10]}" if len(d) == 10 else ""


def build(session):
    folder = os.path.join(P.DATA, str(session))
    members = json.load(open(os.path.join(folder, "members.json")))
    people, by_id = {}, {}
    for m in members:
        L, D = m.get("listing") or {}, m.get("detail") or {}
        if L.get("DateVacated"):
            continue
        dist = L.get("District") or {}
        if not str(dist.get("Number") or "").isdigit():
            continue
        h = "S" if dist.get("Type") == "Senate" else "H"
        n = L.get("Name") or {}
        first = n.get("Nickname") or n.get("First") or ""
        name = " ".join(x for x in (first, n.get("Last"), n.get("Suffix")) if x)
        addr = D.get("Address") or {}
        ph = phone(addr.get("Phone"))
        sid = f"{h}:{int(dist['Number'])}"
        people[sid] = {
            "name": name, "key": name_key(name), "id": L.get("Id"), "party": PARTY.get(L.get("Party"), L.get("Party") or ""),
            "email": addr.get("Email") or (D.get("DistrictAddress") or {}).get("Email") or None, "form": None,
            "phone": ph or None, "phones": [["Atlanta", ph]] if ph else [], "url": f"https://www.legis.ga.gov/members/{'senate' if h == 'S' else 'house'}/{L.get('Id')}",
            "image": None, "office": addr.get("Address1") or "", "position": None, "places": L.get("Residence") or "",
            "dataName": n.get("Last") or name,
        }
        by_id[str(L.get("Id"))] = name
    comms = {"S": {}, "H": {}}
    for c in json.load(open(os.path.join(folder, "committees.json"))):
        d = c.get("detail") or c.get("listing") or {}
        h = "S" if d.get("Type") == "Senate" else "H"
        ms = [x for x in d.get("Members") or [] if not x.get("DateVacated")]
        names = sorted({by_id[str((x.get("Member") or {}).get("Id"))] for x in ms if str((x.get("Member") or {}).get("Id")) in by_id})
        chair = next((by_id.get(str((x.get("Member") or {}).get("Id"))) for x in ms if re.fullmatch(r"Chair(man|person|woman)?", x.get("Role") or "", re.I)), None)
        comms[h][committee_key(d.get("Name"))] = {"name": d.get("Name"), "chair": chair, "meets": None, "members": names}
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
    if len(out["people"]) < 220:
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
    main(int(sys.argv[1]) if len(sys.argv) > 1 else P.session_of(datetime.now(ZoneInfo(P.TIMEZONE)).year))
