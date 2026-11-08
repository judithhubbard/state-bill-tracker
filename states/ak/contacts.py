#!/usr/bin/env python3
"""Alaska's legislators and committees, written as data/ak/contacts_<session>.json in the shape build_data.py reads.

From data/ak/<session>/members.json and committees.json (states/ak/fetch.py: the BASIS public service), no web pages:
- Members: party (D, R, or N: nonpartisan or undeclared, shown as "Independent"), district, Juneau office phone (465-xxxx;
  a few are cut to "465", left out), email, Capitol room, and leadership in the Comment field ("Speaker", "Majority
  Leader"; also "Resigned ...", "Oath Taken ...", "Name Changed ...", which aren't positions). Only active members.
  Seat ids "S:1" for Senate District A ... "S:20" for T (P.senate_number), "H:1" ... "H:40"; "id" is the member's code
  ("FIE"), which the roll calls use.
- Committees: each house's standing and special committees with their members; positions C0/CH chair, C1/C2/C3/CC
  co-chairs (the first is shown as chair), V1/VC vice chair. Finance subcommittees, joint and conference committees are
  left out (bills aren't referred to them).
Usage: python3 states/ak/contacts.py [session]
"""
import json, os, re, sys
from datetime import datetime
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
from fetch_contacts import committee_key, name_key
from states.ak import convert as C
from states.ak import profile as P

PARTY = {"D": "Democratic", "R": "Republican", "N": "Independent"}
NOT_POSITIONS = re.compile(r"Resigned|Oath Taken|Name Changed|Appointed|Deceased|Sworn", re.I)


def phone(x):
    d = re.sub(r"\D", "", x or "")
    if len(d) == 7:
        d = "907" + d
    return f"({d[:3]}) {d[3:6]}-{d[6:]}" if len(d) == 10 else None


def build(session):
    folder = os.path.join(P.DATA, str(session))
    now = session >= P.session_of(datetime.now(ZoneInfo(P.TIMEZONE)).year)  # leaders are named for the current Legislature
    leg = P.legislature_of(session)
    people, by_code = {}, {}
    for m in json.load(open(os.path.join(folder, "members.json"))):
        if not m.get("IsActive") or re.search(r"Name Changed", m.get("Comment") or "", re.I):
            continue  # left, or the record under an old name (Burke, now Frier: both active)
        h, d = m.get("Chamber"), (m.get("District") or "").strip()
        sid = f"S:{P.senate_number(d)}" if h == "S" and re.fullmatch(r"[A-T]", d) else f"H:{int(d)}" if h == "H" and d.isdigit() else None
        if not sid:
            continue
        name = C.person(m)
        ph = phone(m.get("Phone"))
        comment = C.text(m.get("Comment"))
        room = C.text(m.get("Room"))
        people[sid] = {
            "name": name, "key": name_key(name), "id": m.get("Code"), "party": PARTY.get(m.get("Party"), m.get("Party") or ""),
            "email": C.text(m.get("EMail")) or None, "form": None,
            "phone": ph, "phones": [["Juneau office", ph]] if ph else [],
            "url": f"https://www.akleg.gov/basis/Member/Detail/{leg}?code={m.get('Code')}",
            "image": None, "office": f"State Capitol, Room {room}, Juneau" if room else "State Capitol, Juneau",
            "position": comment if now and comment and not NOT_POSITIONS.search(comment) else None,
            "places": "", "dataName": name, "majority": bool(m.get("IsMajority")),
        }
        by_code[(h, m.get("Code"))] = sid
    comms = {"S": {}, "H": {}}
    for c in json.load(open(os.path.join(folder, "committees.json"))):
        h = c.get("Chamber")
        if h not in comms or c.get("Catagory") not in ("Standing Committee", "Special Committee"):
            continue
        name = re.sub(r"^Special Committee on ", "", C.committee_name(c.get("Name")))
        ms = c.get("Membership") or []
        who = lambda codes: [people[by_code[(x.get("MemberChamber"), x.get("MemberCode"))]]["name"] for x in ms
                             if x.get("Position") in codes and (x.get("MemberChamber"), x.get("MemberCode")) in by_code]
        chairs = who({"C0", "CH", "C1", "CC"}) + who({"C2", "C3"})
        vice = who({"V1", "VC"})
        members = sorted({people[by_code[k]]["name"] for x in ms for k in [(x.get("MemberChamber"), x.get("MemberCode"))] if k in by_code})
        comms[h][committee_key(name)] = {"name": name, "chair": chairs[0] if chairs else None,
                                         "coChairs": chairs[1:], "viceChair": vice[0] if vice else None,
                                         "meets": " ".join(x for x in (C.text(c.get("MeetingDays")), C.text(c.get("StartTime"))) if x) or None,
                                         "members": members}
    leaders = {}
    for h, (name, role, _) in (P.LEADERS.items() if now else ()):
        hit = next((p for sid, p in people.items() if sid[0] == h and p["key"] == name_key(name)), None)
        if hit:
            hit["position"] = role
            leaders[h] = {"name": hit["name"], "role": role}
    return {"session": session, "fetched": datetime.now(ZoneInfo(P.TIMEZONE)).strftime("%Y-%m-%d %H:%M"),
            "people": people, "since": {}, "senateCommittees": comms["S"], "assemblyCommittees": comms["H"],
            "leaders": leaders, "assemblyMembers": {}, "kept": []}


def main(session):
    out = build(session)
    if len(out["people"]) < 55:
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
