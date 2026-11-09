#!/usr/bin/env python3
"""Minnesota's legislators and committees, written as data/mn/contacts_<session>.json in the shape build_data.py reads.

From what states/mn/fetch.py downloads, no other web pages:
- members_house.json and members_senate.json (the current Legislature's folder): each member's district, party ("DFL",
  the Democratic-Farmer-Labor Party, Minnesota's Democrats; "R"), St. Paul office, phone and email, and the Senate's
  leadership titles.
- committees_house.json and committees_senate.json: each committee's members with their roles. In 2025-26 the House is
  tied 67-67 and every House committee has two co-chairs, a Republican and a DFL member (the power-sharing agreement):
  the first listed is shown as chair, the other as co-chair.
Seats: Senate "S:12"; House districts are Senate districts' halves, 12A and 12B, numbered 1 to 134 ("H:23" is 12A:
profile.house_seat()). Only current members are published (no past member lists): the latest Legislature lists them all,
with posts and committees; a past one lists the current members who sponsored a bill in their house then.
Usage: python3 states/mn/contacts.py [session]   (default: every Legislature downloaded)
"""
import json, os, re, sys
from datetime import datetime
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
from fetch_contacts import committee_key, name_key
from states.mn import convert as C
from states.mn import profile as P

PARTY = {"DFL": "Democratic-Farmer-Labor", "R": "Republican"}
HOUSE_PAGE = "https://www.house.mn.gov/members/Profile/{}"
SENATE_PAGE = "https://www.mnsenate.gov/members/member_bio.html?mem_id={}"


def phone(p):
    d = re.sub(r"\D", "", p or "")
    if len(d) == 11 and d[0] == "1":
        d = d[1:]
    return f"({d[:3]}) {d[3:6]}-{d[6:]}" if len(d) == 10 else None


def person(m, house, latest):
    name = C.full_name(m, house)
    ph = phone(m.get("phone") if house == "H" else m.get("full_phone_number"))
    office = ", ".join(x for x in (m.get("office") or []) if x) if house == "H" else \
        ", ".join(x for x in (m.get("office_address_first_line"), m.get("office_address_second_line")) if x)
    title = (m.get("leader_title") or "") if house == "S" else ""
    return {
        "name": name, "key": name_key(name), "id": m.get("id") if house == "H" else m.get("mem_id"),
        "party": PARTY.get((m.get("party") or "").upper(), m.get("party") or ""),
        "email": (m.get("email") or "").strip() or None, "form": None,
        "phone": ph, "phones": [["St. Paul office", ph]] if ph else [],
        "url": (HOUSE_PAGE if house == "H" else SENATE_PAGE).format(m.get("id") if house == "H" else m.get("mem_id")),
        "image": None, "office": office or None,
        "position": (title if title and not re.match(r"(Majority|Minority) Member$", title) else None) if latest else None,
        "places": "", "dataName": name,
    }


def clean(n):
    return re.sub(r"^(Rep|Sen)\.\s+", "", (n or "").strip())


def committees(session, house):
    path = os.path.join(C.folder(session), "committees_house.json" if house == "H" else "committees_senate.json")
    raw = C.jload(path, {}) or {}
    out = {}
    for c in raw.values():
        name = C.committee(c.get("name"))
        if not name or not c.get("members"):
            continue
        e = {"name": name, "chair": None, "coChairs": [], "viceChair": None, "meets": (c.get("meets") or "").replace("\n", "; ") or None,
             "members": []}
        for x in c.get("members") or []:
            who = clean(x.get("name"))
            if not who:
                continue
            if who not in e["members"]:
                e["members"].append(who)
            role = x.get("role") or ""
            if role in ("Chair", "Co-Chair", "Committee Chair"):
                if e["chair"]:
                    e["coChairs"].append(who)
                else:
                    e["chair"] = who
            elif role in ("Vice Chair", "Co-Vice Chair") and not e["viceChair"]:
                e["viceChair"] = who
        e["members"].sort()
        out[committee_key(name)] = e
    return out


def build(session):
    latest = session == max(C.sessions())
    people = {}
    sponsors = set()
    if not latest:
        for r in C.load_session(session)[0]:
            for v in r["vers"]:
                for n in [v["sponsor"]] + v["cosponsors"]:
                    sponsors.add((v["p"][0], n))
    for house in ("S", "H"):
        for m in C.members(house):
            sid = C.seat_of(m, house)
            if not sid or (not latest and (house, C.full_name(m, house)) not in sponsors):
                continue
            people[sid] = person(m, house, latest)
    leaders = {}
    if latest:
        for h, (name, role, _) in P.LEADERS.items():
            hit = next((x for sid, x in people.items() if sid[0] == h and x["key"] == name_key(name)), None)
            if hit:
                leaders[h] = {"name": hit["name"], "role": role}
    return {"session": session, "fetched": datetime.now(ZoneInfo(P.TIMEZONE)).strftime("%Y-%m-%d %H:%M"),
            "people": people, "since": {},
            "senateCommittees": committees(session, "S") if latest else {},
            "assemblyCommittees": committees(session, "H") if latest else {},
            "leaders": leaders, "assemblyMembers": {}, "kept": []}


def main(session):
    out = build(session)
    latest = session == max(C.sessions())
    if latest and len(out["people"]) < 190:
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
