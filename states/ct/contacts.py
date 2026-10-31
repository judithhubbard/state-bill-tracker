#!/usr/bin/env python3
"""Connecticut's legislators and committees, from the General Assembly's legislator database (data/ct/<year>/
LegislatorDatabase.csv and committee.csv, downloaded by states/ct/fetch.py), written as data/ct/contacts_<year>.json in
the shape build_data.py reads. The database has each member's district, party, leadership title, Capitol phone, email,
website and committees (chaired, vice-chaired, ranking, member). Committees are joint, so each is listed for both
houses. Seat ids "S:5", "H:63". Usage: python3 states/ct/contacts.py [year]
"""
import csv, json, os, re, sys
from datetime import datetime
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
from fetch_contacts import committee_key, name_key
from states.ct import profile as P

PARTY = {"D": "Democratic", "R": "Republican"}


def rows(year, name):
    from states.ct.convert import rows as read
    return read(year, name)


def build(year):
    people, member_of, chairs = {}, {}, {}
    comm_names = {r["comm_code"]: re.sub(r"\s+Committee$", "", re.sub(r"^(?:Joint )?Committee on\s+", "", r["comm_name"]))
                  for r in rows(year, "committee")}
    for r in rows(year, "LegislatorDatabase"):
        h, d = r.get("office code"), r.get("dist", "")
        if h not in ("H", "S") or not d.isdigit():
            continue
        name = " ".join(x for x in (r.get("commonly used name") or r.get("first name"), r.get("last name"), r.get("suffix")) if x)
        phone = r.get("capitol phone") or None
        sid = f"{h}:{int(d)}"
        title = r.get("title") or None
        people[sid] = {
            "name": name, "key": name_key(name), "id": sid, "party": PARTY.get((r.get("party") or "")[:1], ""),
            "email": r.get("email") or None, "form": None, "phone": phone, "phones": [["Hartford", phone]] if phone else [],
            "url": r.get("URL") or None, "image": None, "office": "", "position": title if title and title.lower() not in ("representative", "senator") else None,
            "places": "", "dataName": r.get("last name") or name,
        }
        for c in (r.get("committees chaired") or "").split(";"):
            c = re.sub(r"\s*\(.*?\)", "", c).strip()
            if c:
                chairs.setdefault(c, []).append(name)
        for field in ("committees chaired", "committees vice chaired", "ranking member", "committee member1"):
            for c in (r.get(field) or "").split(";"):
                c = re.sub(r"\s*\(.*?\)", "", c).strip()
                if c:
                    member_of.setdefault(c, set()).add(name)
    comms = {}
    for code, cname in comm_names.items():
        # The database names committees without "Committee" ("Energy and Technology"); co-chairs are one per house.
        key_names = [n for n in member_of if committee_key(re.sub(r"^Committee on\s+", "", n)) == committee_key(cname)]
        members = sorted(set().union(*(member_of[n] for n in key_names))) if key_names else []
        cs = [x for n in key_names for x in chairs.get(n, [])]
        if members:  # the committee list also has a student council's code
            comms[committee_key(cname)] = {"name": cname, "chair": " and ".join(cs) or None, "meets": None, "members": members}
    leaders = {}
    for h, (name, role, _) in P.LEADERS.items():
        hit = next((p for sid, p in people.items() if sid[0] == h and p["key"] == name_key(name)), None)
        if hit:
            hit["position"] = role
            leaders[h] = {"name": hit["name"], "role": role}
    return {"session": year, "fetched": datetime.now(ZoneInfo(P.TIMEZONE)).strftime("%Y-%m-%d %H:%M ET"),
            "people": people, "since": {}, "senateCommittees": comms, "assemblyCommittees": comms,
            "leaders": leaders, "assemblyMembers": {}, "kept": []}


def main(year):
    out = build(year)
    path = os.path.join(P.DATA, f"contacts_{year}.json")
    json.dump(out, open(path, "w"), indent=1, ensure_ascii=False)
    ppl = out["people"].values()
    print(f"{path}: {len(out['people'])} legislators ({sum(1 for p in ppl if p['phone'])} with a phone, "
          f"{sum(1 for p in ppl if p['email'])} with email, {sum(1 for p in ppl if p['party'])} with party), "
          f"{len(out['senateCommittees'])} committees ({sum(1 for c in out['senateCommittees'].values() if c['chair'])} with chairs), "
          f"leaders {sorted(out['leaders'])}")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else datetime.now(ZoneInfo(P.TIMEZONE)).year)
