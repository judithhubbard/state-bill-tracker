#!/usr/bin/env python3
"""Utah's legislators and committees, written as data/ut/contacts_<year>.json in the shape build_data.py reads, from
data/ut/<year>/legislators.json and committees.json (states/ut/fetch.py: the Legislature's developer API, which has the
current members only). Seat ids "S:3", "H:12"; each member's id is the Legislature's ("PETERT"), which bills use for
sponsors. Committees are each house's standing committees ("House Transportation Committee" -> "Transportation"), with
their chairs.
Usage: python3 states/ut/contacts.py [year]
"""
import json, os, re, sys
from datetime import datetime
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
from fetch_contacts import committee_key, name_key
from states.ut import profile as P

PARTY = {"D": "Democratic", "R": "Republican", "F": "Forward"}


def items(path, key):
    d = json.load(open(path))
    return d.get(key, d) if isinstance(d, dict) else d


def comm_name(full):
    """"House Business, Labor, and Commerce Committee" -> "Business, Labor, and Commerce"."""
    return re.sub(r"^(?:House|Senate) | Committee$", "", full or "").strip()


def build(year):
    folder = os.path.join(P.DATA, str(year))
    people = {}
    for m in items(os.path.join(folder, "legislators.json"), "legislators"):
        if m.get("house") not in ("H", "S") or not str(m.get("district") or "").isdigit():
            continue
        sid = f"{m['house']}:{int(m['district'])}"
        phones = [[label, m[k]] for k, label in (("workPhone", "Work"), ("cell", "Cell"), ("homePhone", "Home")) if m.get(k)]
        phones = [p for i, p in enumerate(phones) if p[1] not in [q[1] for q in phones[:i]]]  # the same number once
        people[sid] = {
            "name": m["formatName"], "key": name_key(m["formatName"]), "id": m["id"],
            "party": PARTY.get(m.get("party"), m.get("party") or ""), "email": m.get("email") or None, "form": None,
            "phone": phones[0][1] if phones else None, "phones": phones,
            "url": f"https://le.utah.gov/legislator/{m['id']}", "image": None, "office": m.get("address") or "",
            "position": m.get("leadership") or None, "places": m.get("counties") or "",
            "dataName": m.get("fullName") or m["formatName"],
        }
    by_id = {p["id"]: p["name"] for p in people.values()}
    comms = {"S": {}, "H": {}}
    for c in items(os.path.join(folder, "committees.json"), "committees"):
        full = c.get("description") or ""
        h = {"House": "H", "Senate": "S"}.get(full.split(" ")[0])
        # Each house's standing committees (not interim, appropriations subcommittees or commissions).
        # (Confirmation committees review appointments; Ethics and Legislative Expense Oversight see no bills.)
        if (not h or not full.endswith(" Committee") or re.search(r"Interim|Appropriations Subcommittee|Confirmation|Ethics|Expense", full)):
            continue
        name = comm_name(full)
        members = c.get("members") or []
        chair = next((m for m in members if m.get("position") == "chair"), None)
        comms[h][committee_key(name)] = {"name": name, "chair": by_id.get(chair["id"]) if chair else None, "meets": None,
                                         "members": sorted(by_id.get(m["id"], m.get("name")) for m in members)}
    leaders = {}
    for h, (name, role, _) in P.LEADERS.items():
        hit = next((p for sid, p in people.items() if sid[0] == h and p["key"] == name_key(name)), None)
        if hit:
            hit["position"] = role
            leaders[h] = {"name": hit["name"], "role": role}
    return {"session": year, "fetched": datetime.now(ZoneInfo(P.TIMEZONE)).strftime("%Y-%m-%d %H:%M"),
            "people": people, "since": {}, "senateCommittees": comms["S"], "assemblyCommittees": comms["H"],
            "leaders": leaders, "assemblyMembers": {}, "kept": []}


def main(year):
    out = build(year)
    if len(out["people"]) < 95:
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
