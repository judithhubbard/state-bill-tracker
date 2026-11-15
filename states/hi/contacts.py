#!/usr/bin/env python3
"""Hawaii's legislators, written as data/hi/contacts_<session>.json in the shape build_data.py reads, from Open States'
public-domain people file (data/hi/openstates_people.csv, saved by states/hi/fetch.py; the Legislature's own site turns
automated requests away). The file has each member's party, district, email and photo, but no phone numbers, so none
are shown (none is invented).

Hawaii has 25 Senate and 51 House districts, one member each: seat ids "S:12", "H:12". Committees come from the bills'
histories: each standing committee of each house with the members who voted in it in the Legislature's latest year
(every committee vote is recorded member by member). The histories don't say who chairs a committee, so no chairs are
shown. A past Legislature's contacts are today's members. Usage: python3 states/hi/contacts.py [session]
"""
import json, os, re, sys
from collections import defaultdict
from datetime import datetime
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
from fetch_contacts import committee_key, name_key
from states.hi import convert as C
from states.hi import profile as P


def committees(session):
    """(house, committee) -> member seats, from the committee votes of the Legislature's latest year that has any."""
    by_year = defaultdict(lambda: defaultdict(set))
    for key, y in C.keys(session):
        b = C.bill(y, key) or {}
        for a in b.get("actions") or []:
            t = C.text(a.get("description"))
            h = C.ORG.get((a.get("organization") or {}).get("classification"))
            m = re.match(r"The committee\(?s?\)? on\s+([A-Z]{2,4})\s+recommends?(?:\(s\))? that the measure be PASSED", t)
            if not h or not m:
                continue
            cv = C.committee_vote(t, h)
            if not cv:
                continue
            year = int(a["date"][:4])
            names = cv[3] + [n for n, _ in cv[2]]
            for n in names:
                by_year[year][(h, P.committee_name(m.group(1), year, h))].add(C.seat_of(session, h, n))
    if not by_year:
        return {}
    return by_year[max(by_year)]


def build(session):
    people = {}
    for h, seat, full, fam, given, party in C.people():
        people[seat] = {"name": full, "key": name_key(full), "id": None, "party": {"D": "Democratic", "R": "Republican"}.get(party, party),
                        "email": None, "form": None, "phone": None, "phones": [], "url": None, "image": None, "office": "",
                        "position": None, "places": f"District {seat.split(':')[1]}", "dataName": fam}
    import csv
    for r in csv.DictReader(open(os.path.join(P.DATA, "openstates_people.csv"), encoding="utf-8")):
        h = C.ORG.get(r.get("current_chamber"))
        if not h or not (r.get("current_district") or "").isdigit():
            continue
        p = people.get(f"{h}:{int(r['current_district'])}")
        if not p:
            continue
        links = [u for u in (r.get("links") or "").split(";") if u]
        p["email"] = r.get("email") or None
        p["url"] = next((u for u in links if "memberpage" in u and "year=" not in u), links[0] if links else None)
        # Photos hosted on the Legislature's own site are left out: test pages loading them would be automated requests
        # to a site that turns them away.
        img = r.get("image") or ""
        p["image"] = img.replace("http://", "https://") if img and "capitol.hawaii.gov" not in img else None
    comms = {"S": {}, "H": {}}
    for (h, name), seats in sorted(committees(session).items()):
        members = sorted(people[s]["name"] for s in seats if s in people)
        comms[h][committee_key(name)] = {"name": name, "chair": None, "meets": None, "members": members}
    leaders = {}
    for h, (name, role, _) in P.LEADERS.items():
        hit = next((p for sid, p in people.items() if sid[0] == h and p["key"] == name_key(name)), None)
        if hit:
            hit["position"] = role
            leaders[h] = {"name": hit["name"], "role": role}
    return {"session": session, "fetched": datetime.now(ZoneInfo(P.TIMEZONE)).strftime("%Y-%m-%d %H:%M"),
            "people": people, "since": {}, "senateCommittees": comms["S"], "assemblyCommittees": comms["H"],
            "leaders": leaders, "assemblyMembers": {}, "kept": []}


def main(sessions):
    for session in sessions:
        out = build(session)
        if len(out["people"]) < 70:
            raise SystemExit(f"only {len(out['people'])} legislators; kept the last contacts")
        path = os.path.join(P.DATA, f"contacts_{session}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(out, f, indent=1, ensure_ascii=False)
        ppl = out["people"].values()
        print(f"{path}: {len(out['people'])} legislators ({sum(1 for p in ppl if p['email'])} with email), "
              f"{len(out['senateCommittees'])} Senate and {len(out['assemblyCommittees'])} House committees, leaders {sorted(out['leaders'])}")


if __name__ == "__main__":
    main([int(sys.argv[1])] if len(sys.argv) > 1 else C.sessions())
