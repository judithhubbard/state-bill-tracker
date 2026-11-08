#!/usr/bin/env python3
"""New Hampshire's legislators and committees, written as data/nh/contacts_<year>.json in the shape build_data.py reads.

- Members, parties, districts and emails: the General Court's legislators file for the biennium
  (data/nh/<first year>/legislators.txt, from states/nh/fetch.py). Seat ids "S:12" for senators; a House district's
  members are "H:612a", "H:612b" ... (Hillsborough 12: the county's code times 100 plus the district number), lettered in
  the order of their seat numbers (convert.seat_ids(), which the roll calls use too). "id" is the PersonID.
- Phones and offices: the General Court's member list (Members.txt), joined by House seat number or Senate district.
  It lists 142 representatives without a phone of their own; they're left without one (no shared line is invented).
  Its electedStatus "Former" is on 18 members still sitting and voting in 2026 (not those who left), so it's ignored.
- Committees: Committees.txt (names) and CommitteeMembers.txt (each current member, with "Chairman", "V Chairman" or
  "Clerk"), joined by PersonID.
- Pages: gc.nh.gov's member page (House, by PersonID) or the senator's district page.
- Leaders: P.LEADERS and P.POSITIONS (the files name none), for the current General Court only.
Usage: python3 states/nh/contacts.py [year]
"""
import json, os, re, sys
from datetime import datetime
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
from fetch_contacts import committee_key, name_key
from states.nh import convert as C
from states.nh import profile as P

PARTY = {"R": "Republican", "D": "Democratic", "I": "Independent", "L": "Libertarian"}


def members_file(folder):
    """Members.txt's rows (tab-delimited, a header row): ("H", seat number) or ("S", district) -> row."""
    path = os.path.join(folder, "Members.txt")
    if not os.path.exists(path):
        return {}
    lines = [l.rstrip("\r\n").split("\t") for l in open(path, encoding="utf-8-sig") if l.strip()]
    head, out = lines[0], {}
    for l in lines[1:]:
        r = dict(zip(head, l))
        h = r.get("LegislativeBody", "").strip()
        key = (h, (r.get("seatno") or "").strip()) if h == "H" else (h, (r.get("District") or "").strip())
        out[key] = r
    return out


def build(year):
    first = P.first_year(year)
    folder = os.path.join(P.DATA, str(first))
    now = first == P.first_year(datetime.now(ZoneInfo(P.TIMEZONE)).year)  # leaders are named for the current court only
    seats = C.seat_ids(first)
    who = C.people(first)
    listed = members_file(folder)
    people, by_pid = {}, {}
    for pid, sid in seats.items():
        m = who[pid]
        h = m["house"]
        row = listed.get((h, m["seat"]) if h == "H" else (h, str(m["district"]))) or {}
        if row and name_key(f"{row.get('FirstName', '')} {row.get('LastName', '')}").split()[-1:] != name_key(m["name"]).split()[-1:]:
            row = {}  # the member list's seat has someone else
        phone = (row.get("Phone") or "").strip() or None
        office = ", ".join(x.strip().strip('"') for x in (row.get("Address"), row.get("address2"), row.get("city")) if x and x.strip()) if h == "S" else None
        people[sid] = {
            "name": m["name"], "key": name_key(m["name"]), "id": str(pid), "party": PARTY.get(m["party"], ""),
            "email": (row.get("WorkEmail") or "").strip() or None, "form": None,
            "phone": phone, "phones": [["Phone", phone]] if phone else [],
            "url": f"https://gc.nh.gov/senate/members/webpages/district{m['district']:02d}.aspx" if h == "S"
                   else f"https://gc.nh.gov/house/members/member.aspx?pid={pid}",
            "image": None, "office": office, "position": P.POSITIONS.get((h, m["name"])) if now else None,
            "places": "", "dataName": m["name"],
        }
        by_pid[pid] = sid
    # Emails the member list lacks, from the legislators file.
    for r in C.rows(os.path.join(folder, "legislators.txt")):
        if len(r) >= 15 and r[0].strip().isdigit() and int(r[0]) in by_pid and not people[by_pid[int(r[0])]]["email"]:
            people[by_pid[int(r[0])]]["email"] = r[14].strip() or None
    names = C.committee_names(first)
    comms = {"S": {}, "H": {}}
    for r in C.rows(os.path.join(folder, "CommitteeMembers.txt")):
        if len(r) < 6 or r[4].strip() != "1" or not r[3].strip().isdigit():
            continue
        code = r[0].strip().upper()
        h, name = code[:1], names.get(code)
        pid = int(r[3])
        if h not in comms or not name or pid not in by_pid or re.match(r"(?:No Committee|Committee of Conference)", name):
            continue
        c = comms[h].setdefault(committee_key(name), {"name": name, "chair": None, "viceChair": None, "meets": None, "members": []})
        n = people[by_pid[pid]]["name"]
        if n not in c["members"]:
            c["members"].append(n)
        role = r[5].strip()
        if role == "Chairman":
            c["chair"] = n
        elif role == "V Chairman":
            c["viceChair"] = n
    for h in comms:
        # Committees no longer meeting keep a member or two marked active (the Senate's "Rules, Enrolled Bills and
        # Internal Affairs" of an earlier court): left out.
        comms[h] = {k: c for k, c in comms[h].items() if len(c["members"]) >= 3}
        for c in comms[h].values():
            c["members"].sort()
    leaders = {}
    for h, (name, role, _) in (P.LEADERS.items() if now else ()):
        hit = next((p for sid, p in people.items() if sid[0] == h and p["key"] == name_key(name)), None)
        if hit:
            hit["position"] = role
            leaders[h] = {"name": hit["name"], "role": role}
    return {"session": year, "fetched": datetime.now(ZoneInfo(P.TIMEZONE)).strftime("%Y-%m-%d %H:%M"),
            "people": people, "since": {}, "senateCommittees": comms["S"], "assemblyCommittees": comms["H"],
            "leaders": leaders, "assemblyMembers": {}, "kept": []}


def main(year):
    out = build(year)
    if len(out["people"]) < 350:
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
