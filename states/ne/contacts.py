#!/usr/bin/env python3
"""Nebraska's senators and committees, written as data/ne/contacts_<session>.json in the shape build_data.py reads.

From what states/ne/fetch.py downloads, no other web pages:
- data/ne/members/members.json: the 49 current senators (district, name, the id bill pages use, Capitol room, phone,
  email, committees, photo, and which one is Speaker).
- data/ne/members/committees.json: the 14 standing committees with their members by id, "Chairperson" and "Vice
  Chairperson", and when and where they meet; and the select and special committees (Executive Board, Rules, Committee on
  Committees and others), kept only where they hear bills (the Executive Board).
One house: seats "L:12" (District 12), in the shared files' "assemblyCommittees" slot (the lower house's, which is the only
one: P.LOWER). Senators are elected without party labels and no official page lists a party, so no party is given.
Only current senators are known (former senators' pages are empty): a past Legislature lists the current senators who
introduced a bill in it, without posts.
Usage: python3 states/ne/contacts.py [session]   (default: every Legislature downloaded)
"""
import json, os, re, sys
from datetime import datetime
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
from fetch_contacts import committee_key, name_key
from states.ne import convert as C
from states.ne import profile as P

PAGE = "https://nebraskalegislature.gov/senators/landing-pages/index.php?District={}"
COMMITTEE_PAGE = "https://nebraskalegislature.gov/committees/landing_pages/index.php?cid={}"


def person(m, latest):
    return {
        "name": m["name"], "key": name_key(m["name"]), "id": m.get("senator_id"), "party": "",
        "email": (m.get("email") or "").strip() or None, "form": None,
        "phone": m.get("phone") or None, "phones": [["Capitol", m["phone"]]] if m.get("phone") else [],
        "url": PAGE.format(m["district"]), "image": m.get("photo") or None,
        "office": ", ".join(m.get("address") or []) or m.get("room") or None,
        "position": ("Speaker of the Legislature" if m.get("speaker") else None) if latest else None,
        "places": "", "dataName": C.surname(m["name"]),
    }


def meets(text):
    """"During session, the Agriculture Committee meets on Tuesdays in Room 1023 on the 1st Floor of the Capitol." -> "on
    Tuesdays in Room 1023" (the page adds "during session")."""
    m = re.search(r"\bmeets\s+(.+?)(?:,? on the \w+ floor\b.*)?\.?$", text or "", re.I)
    return m.group(1).strip() if m else None


def committees():
    try:
        raw = json.load(open(os.path.join(P.DATA, "members", "committees.json"), encoding="utf-8")).get("committees") or []
    except (OSError, ValueError):
        raw = []
    by_id = C.by_id()
    by_district = {m["district"]: m for m in C.members()}
    out = {}
    for c in raw:
        name = C.comm_name(c.get("name"))
        # The standing committees hear bills; of the others, only the Executive Board (the Reference Committee's members,
        # which also hears bills about the Legislature itself).
        if c.get("kind") != "standing" and name != "Executive Board":
            continue
        e = {"name": name, "chair": None, "coChairs": [], "viceChair": None, "meets": meets(c.get("meets")),
             "url": COMMITTEE_PAGE.format(c["cid"]) if c.get("cid") else None, "members": []}
        for x in c.get("members") or []:
            m = by_id.get(x.get("senator_id")) or by_district.get(x.get("district"))
            who = m["name"] if m else (x.get("name") or "").strip()
            if not who:
                continue
            if who not in e["members"]:
                e["members"].append(who)
            role = x.get("role") or ""
            if re.match(r"Chair(?:person|man)?$", role) and not e["chair"]:
                e["chair"] = who
            elif re.match(r"Vice Chair", role) and not e["viceChair"]:
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
                sponsors |= {v["sponsor"], *v["cosponsors"]}
    for m in C.members():
        if not latest and m["name"] not in sponsors:
            continue
        people[f"{C.H}:{m['district']}"] = person(m, latest)
    comms = committees() if latest else {}
    leaders = {}
    if latest:
        for h, (name, role, _) in P.LEADERS.items():
            hit = next((x for x in people.values() if x["key"] == name_key(name)), None)
            if hit:
                leaders[h] = {"name": hit["name"], "role": role}
    return {"session": session, "fetched": datetime.now(ZoneInfo(P.TIMEZONE)).strftime("%Y-%m-%d %H:%M"),
            "people": people, "since": {}, "senateCommittees": {}, "assemblyCommittees": comms,
            "leaders": leaders, "assemblyMembers": {}, "kept": []}


def main(session):
    out = build(session)
    latest = session == max(C.sessions())
    if latest and len(out["people"]) < 45:
        raise SystemExit(f"{session}: only {len(out['people'])} senators; kept the last contacts")
    path = os.path.join(P.DATA, f"contacts_{session}.json")
    json.dump(out, open(path, "w"), indent=1, ensure_ascii=False)
    ppl = out["people"].values()
    comms = list(out["assemblyCommittees"].values())
    print(f"{path}: {len(out['people'])} senators ({sum(1 for p in ppl if p['email'])} with email, "
          f"{sum(1 for p in ppl if p['phone'])} with a phone), {len(comms)} committees "
          f"({sum(1 for c in comms if c['chair'])} with a chair), leaders {sorted(out['leaders'])}")


if __name__ == "__main__":
    for s in ([int(sys.argv[1])] if len(sys.argv) > 1 else C.sessions()):
        main(s)
