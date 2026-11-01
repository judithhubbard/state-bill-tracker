#!/usr/bin/env python3
"""Wyoming's legislators and committees, written as data/wy/contacts_<year>.json in the shape build_data.py reads, from
data/wy/<year>/members_H.json, members_S.json and committees.json (states/wy/fetch.py: the Legislative Service Office's
API). Phones are the members' own (the API lists no Capitol offices). Committees are joint (J09 is the House's H09 and the
Senate's S09), each with a House and a Senate chair. Seat ids "S:8", "H:12"; members who left (legStatus "F") are skipped.
Usage: python3 states/wy/contacts.py [year]
"""
import json, os, re, sys
from datetime import datetime
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
from fetch_contacts import committee_key, name_key
from states.wy import profile as P

PARTY = {"D": "Democratic", "R": "Republican", "Democratic": "Democratic", "Republican": "Republican"}


def build(year):
    folder = os.path.join(P.DATA, str(year))
    people = {}
    past = year < datetime.now(ZoneInfo(P.TIMEZONE)).year
    for h in "HS":
        # Members serving now first; in a past year, then those who left, for seats no one else holds (the API lists
        # a past year's members as they stand today).
        for m in sorted(json.load(open(os.path.join(folder, f"members_{h}.json"))), key=lambda m: (m.get("legStatus") or "C") == "F"):
            if ((m.get("legStatus") or "C") == "F" and not past) or not re.match(r"[HS]\d+", m.get("district") or ""):
                continue
            sid = f"{h}:{int(m['district'][1:])}"
            if sid in people:
                continue
            ph = m.get("phone") or ""
            people[sid] = {
                "name": m["name"], "key": name_key(m["name"]), "id": m.get("voteName") or m["name"].split()[-1],
                "party": PARTY.get(m.get("party"), m.get("party") or ""), "email": m.get("eMail") or None, "form": None,
                "phone": ph or None, "phones": [["Phone", ph]] if ph else [], "url": None, "image": None, "office": "",
                "position": m.get("leadershipPosition") or None, "places": m.get("county") or "",
                "dataName": m.get("voteName") or m["name"],
            }
    by_last = {}
    for sid, p in people.items():
        by_last.setdefault((sid[0], p["name"].split()[-1]), []).append(p["name"])
    comms = {"S": {}, "H": {}}
    try:
        committees = json.load(open(os.path.join(folder, "committees.json")))
    except (OSError, ValueError):
        committees = []
    for c in committees:
        d = c.get("detail") or {}
        if (d.get("type") or c.get("listing", {}).get("type")) != "J":
            continue
        name = d.get("jointCommName") or d.get("description") or d.get("commName")
        for h in "HS":
            ms = [m for m in d.get("commMembers") or [] if m.get("chamber") == h and m.get("active", True) and not m.get("alternate")]
            names = sorted({m["name"] for m in ms})
            chair = next((m["name"] for m in ms if m.get("isChair")), None)
            comms[h][committee_key(name)] = {"name": name, "chair": chair, "meets": None, "members": names}
    leaders = {}
    for h, (name, role, _) in P.LEADERS.items():
        # The member list's own positions decide (a past year's list shows today's leaders only among those still serving).
        hit = (next((p for sid, p in people.items() if sid[0] == h and p["position"] == role), None)
               or (None if past else next((p for sid, p in people.items() if sid[0] == h and p["key"] == name_key(name)), None)))
        if hit:
            hit["position"] = role
            leaders[h] = {"name": hit["name"], "role": role}
    return {"session": year, "fetched": datetime.now(ZoneInfo(P.TIMEZONE)).strftime("%Y-%m-%d %H:%M"),
            "people": people, "since": {}, "senateCommittees": comms["S"], "assemblyCommittees": comms["H"],
            "leaders": leaders, "assemblyMembers": {}, "kept": []}


def main(year):
    out = build(year)
    if len(out["people"]) < 85:
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
