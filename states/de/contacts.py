#!/usr/bin/env python3
"""Delaware's legislators and committees, written as data/de/contacts_<session>.json in the shape build_data.py reads.

From what states/de/fetch.py downloads, no other web pages:
- data/de/<session>/members.json: every member who served in the General Assembly (person id, house, district, party,
  short name, leadership role). Each seat goes to the member who held it last (convert.seats(), by the last roll call
  each voted on); members who left mid-term (Sarah McBride, Senate 1, in January 2025) aren't listed.
- data/de/people.json: each member's page: Legislative Hall phone, email, office address.
- committees.json: each house's standing committees with chair, vice chair and members (full names, matched to the
  members by name). The Rules, Ethics and Rules & Ethics committees and disbanded ones are left out (bills aren't sent
  there); joint committees too (the Joint Finance and Joint Capital Improvement committees write the budget and the bond
  bill, which are filed as House bills).
Leadership positions are named for the current General Assembly only.
Usage: python3 states/de/contacts.py [session]   (default: every General Assembly downloaded)
"""
import json, os, re, sys
from datetime import datetime
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
from fetch_contacts import committee_key, name_key
from states.de import convert as C
from states.de import profile as P

PARTY = {"D": "Democratic", "R": "Republican", "I": "Independent"}
SKIP = re.compile(r"^(?:Rules|Ethics|Rules & Ethics)$|DISBANDED", re.I)


def phone(x):
    d = re.sub(r"\D", "", x or "")
    if len(d) == 11 and d[0] == "1":
        d = d[1:]
    return f"({d[:3]}) {d[3:6]}-{d[6:]}" if len(d) == 10 else None


def build(session):
    today = datetime.now(ZoneInfo(P.TIMEZONE)).date()
    now = session == max(C.sessions())
    try:
        pages = json.load(open(os.path.join(P.DATA, "people.json")))
    except (OSError, ValueError):
        pages = {}
    seats = C.seats(session)
    people, by_key = {}, {}
    for m in C.load(session, "members"):
        h = C.CHAMBER.get(m.get("ChamberId"))
        sid = seats.get((h, C.text(m.get("ShortName"))))
        if not sid or "?" in sid:
            continue
        name = C.full_name(m)
        pg = pages.get(str(m.get("PersonId"))) or {}
        phones, seen = [], set()
        for x in pg.get("phones") or []:
            ph = phone(x.get("number"))
            if ph and ph not in seen:
                seen.add(ph)
                phones.append([re.sub(r"^Leghall Phone$", "Legislative Hall", C.text(x.get("label"))) or "Office", ph])
        email = next((C.text(e) for e in pg.get("emails") or [] if "@" in e), None)
        role = C.text(m.get("MemberTypeName")) if m.get("IsLeadershipRole") else ""
        people[sid] = {
            "name": name, "key": name_key(name), "id": m.get("PersonId"), "party": PARTY.get(C.party_of(m), C.party_of(m)),
            "email": email, "form": None, "phone": phones[0][1] if phones else None, "phones": phones,
            "url": f"https://legis.delaware.gov/LegislatorDetail?personId={m['PersonId']}" if m.get("PersonId") else None,
            "image": None, "office": ", ".join(x for x in (C.text(pg.get("office")), C.text(pg.get("address"))) if x) or None,
            "position": role if now and role else None, "places": "", "dataName": name,
        }
        by_key[(h, name_key(name))] = name
        by_key[(h, name_key(f"{C.text(m.get('FirstName'))} {C.text(m.get('LastName'))}"))] = name
    # A number several members list is their caucus's shared office line (the House Democrats' (302) 744-4351).
    count = {}
    for p in people.values():
        for _, ph in p["phones"]:
            count[ph] = count.get(ph, 0) + 1
    for p in people.values():
        p["phones"] = [[("Caucus office" if count[ph] > 2 else label), ph] for label, ph in p["phones"]]
    comms = {"S": {}, "H": {}}
    for c in C.load(session, "committees"):
        h = {"Senate": "S", "House": "H"}.get(c.get("CommitteeTypeName"))
        name = C.committee_name(c.get("CommitteeName"))
        if not h or SKIP.search(name):
            continue
        groups = c.get("members") or {}

        def who(label):
            out = []
            for x in groups.get(label) or []:
                n = C.text(x.get("name"))
                k = name_key(n)
                hit = by_key.get((h, k)) or next((v for (hh, kk), v in by_key.items() if hh == h and kk.split(" ")[-1] == k.split(" ")[-1] and kk[:1] == k[:1]), None)
                out.append(hit or n)
            return out
        chair, vice, rest = who("Chair"), who("Vice-Chair(s)"), who("Members")
        if not (chair or rest) and c.get("ChairName"):
            chair = [C.text(c.get("ChairName"))]
        comms[h][committee_key(name)] = {"name": name, "chair": chair[0] if chair else None, "coChairs": chair[1:],
                                         "viceChair": vice[0] if vice else None, "meets": None,
                                         "members": sorted(set(chair + vice + rest))}
    leaders = {}
    if now:
        for h, (name, role, _) in P.LEADERS.items():
            hit = next((p for sid, p in people.items() if sid[0] == h and p["key"] == name_key(name)), None)
            if hit:
                leaders[h] = {"name": hit["name"], "role": role}
    return {"session": session, "fetched": datetime.now(ZoneInfo(P.TIMEZONE)).strftime("%Y-%m-%d %H:%M"),
            "people": people, "since": {}, "senateCommittees": comms["S"], "assemblyCommittees": comms["H"],
            "leaders": leaders, "assemblyMembers": {}, "kept": []}


def main(session):
    out = build(session)
    if len(out["people"]) < 55:
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
