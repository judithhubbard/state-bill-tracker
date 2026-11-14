#!/usr/bin/env python3
"""Missouri's legislators and committees, written as data/mo/contacts_<session>.json in the shape build_data.py reads.

From what states/mo/fetch.py downloads, no other web pages:
- data/mo/<year>/house/members/<001>.xml: each representative that year (party, Capitol office and phone, email,
  committees with positions, leadership post, counties); <year>/house/CommitteeList.xml: the House's committees with
  chair and vice-chair (joint committees are left out).
- data/mo/members/senate.json: the current senators (party and leadership post, Capitol office and phone, the "Email the
  Senator" contact form: the Senate publishes no email addresses, so senators get the form and no email), and
  <year>/senate/committees.json: that year's Senate committees with "Chair"/"Vice-Chair".
Each district elects one member: seats "S:12", "H:45". A past year's senators who have since left (their names and
districts come from the Senate's bill list and the House's conferee entries) are listed by name only, without party or
contacts. Usage: python3 states/mo/contacts.py [session]   (default: every year downloaded)
"""
import json, os, re, sys
import xml.etree.ElementTree as ET
from datetime import datetime
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
from fetch_contacts import committee_key, name_key
from states.mo import convert as C
from states.mo import profile as P

HOUSE_URL = "https://house.mo.gov/MemberDetails.aspx?district={:03d}"
SENATE_URL = "https://www.senate.mo.gov/Senators/Member/{}"


def phone(p):
    d = re.sub(r"\D", "", p or "")
    if len(d) == 11 and d[0] == "1":
        d = d[1:]
    return f"({d[:3]}) {d[3:6]}-{d[6:]}" if len(d) == 10 else None


def party_of(p):
    p = p or ""
    return "Republican" if "Republican" in p else "Democratic" if "Democrat" in p else ("Independent" if p else "")


def post_of(p):
    """"Majority Floor Leader - Republican" -> "Majority Floor Leader"; "Republican" -> None."""
    m = re.match(r"(.+?) - (?:Republican|Democrat)", p or "")
    return m.group(1) if m else None


def build(session):
    latest = session == max(C.sessions())
    people = {}
    for d, m in C.house_members(session).items():
        ph = phone(m["phone"])
        people[f"H:{d}"] = {
            "name": m["name"], "key": name_key(m["name"]), "id": d, "party": party_of(m["party"]),
            "email": m["email"] or None, "form": None, "phone": ph, "phones": [["Capitol", ph]] if ph else [],
            "url": HOUSE_URL.format(d), "image": m["photo"] or None, "office": m["office"] or None,
            "position": (m["post"] or None) if latest else None,
            "places": ", ".join(f"{c} County" if not c.endswith("City") else c for c in m["counties"]) if latest else "",
            "dataName": C.last_name(m["name"])}
    now = {int(x["district"]): x for x in C.senators_now() if x.get("district")}
    for d, name in sorted(C.senate_roster(session).items()):
        x = now.get(d)
        if x and C.norm(C.last_name(x["name"])) != C.norm(C.last_name(name)):
            x = None
        if x is None and latest:
            continue  # a seat vacant now
        ph = phone(x.get("phone")) if x else None
        people[f"S:{d}"] = {
            "name": x["name"] if x else name, "key": name_key(x["name"] if x else name), "id": d,
            "party": party_of(x.get("party")) if x else "", "email": None,
            "form": x.get("contact_form") if x else None, "phone": ph, "phones": [["Capitol", ph]] if ph else [],
            "url": SENATE_URL.format(d) if x else None, "image": None, "office": (x.get("address") if x else None),
            "position": post_of(x.get("party")) if x and latest else None, "places": "",
            "dataName": C.last_name(x["name"] if x else name)}

    comms = {"S": {}, "H": {}}
    try:
        root = ET.parse(os.path.join(C.folder(session), "house", "CommitteeList.xml")).getroot()
    except (OSError, ET.ParseError):
        root = None
    for c in root.findall("Committee") if root is not None else []:
        name = (c.findtext("Name") or "").strip()
        if not name or re.match(r"(?:Joint Committee|Subcommittee|Conference Committee|Special Interim)", name) or (c.findtext("Type") or "") in ("Task Force", "Interim"):
            continue
        e = comms["H"].setdefault(committee_key(name), {"name": C.comm_name(name), "chair": None, "coChairs": [], "viceChair": None,
                                                         "meets": None, "members": []})
        for mm in c.iter("CommitteeMember"):
            if (mm.findtext("Chamber") or "H").strip() != "H":
                continue
            who = (mm.findtext("MemberName") or "").strip()
            if not who:
                continue
            if who not in e["members"]:
                e["members"].append(who)
            role = (mm.findtext("PositionName") or "").strip()
            if role == "Chair" and not e["chair"]:
                e["chair"] = who
            elif role == "Vice-Chair" and not e["viceChair"]:
                e["viceChair"] = who
        e["members"].sort()
    try:
        raw = json.load(open(os.path.join(C.folder(session), "senate", "committees.json"), encoding="utf-8"))
    except (OSError, ValueError):
        raw = []
    for c in raw if isinstance(raw, list) else raw.get("committees") or []:
        name = C.comm_name(c.get("name") or "")
        if not name or not re.search(r"Standing|Select|Statutory", c.get("group") or "Standing"):
            continue
        e = comms["S"].setdefault(committee_key(name), {"name": name, "chair": None, "coChairs": [], "viceChair": None,
                                                         "meets": None, "members": []})
        for x in c.get("members") or []:
            if x.get("house", "S") != "S" or not x.get("name"):
                continue
            who = x["name"]
            if who not in e["members"]:
                e["members"].append(who)
            if x.get("role") == "Chair" and not e["chair"]:
                e["chair"] = who
            elif x.get("role") == "Vice-Chair" and not e["viceChair"]:
                e["viceChair"] = who
        e["members"].sort()
    leaders = {}
    if latest:
        for h, (name, role, _) in P.LEADERS.items():
            hit = next((x for sid, x in people.items() if sid[0] == h and x["key"] == name_key(name)), None)
            if hit:
                leaders[h] = {"name": hit["name"], "role": role}
    return {"session": session, "fetched": datetime.now(ZoneInfo(P.TIMEZONE)).strftime("%Y-%m-%d %H:%M"),
            "people": people, "since": {}, "senateCommittees": comms["S"], "assemblyCommittees": comms["H"],
            "leaders": leaders, "assemblyMembers": {}, "kept": []}


def main(session):
    out = build(session)
    latest = session == max(C.sessions())
    if latest and len(out["people"]) < 180:
        raise SystemExit(f"{session}: only {len(out['people'])} legislators; kept the last contacts")
    path = os.path.join(P.DATA, f"contacts_{session}.json")
    json.dump(out, open(path, "w"), indent=1, ensure_ascii=False)
    ppl = out["people"].values()
    comms = list(out["senateCommittees"].values()) + list(out["assemblyCommittees"].values())
    print(f"{path}: {len(out['people'])} legislators ({sum(1 for p in ppl if p['email'])} with email, "
          f"{sum(1 for p in ppl if p['form'])} with a contact form, {sum(1 for p in ppl if p['phone'])} with a phone, "
          f"{sum(1 for p in ppl if not p['party'])} without a party), {len(out['senateCommittees'])} Senate and "
          f"{len(out['assemblyCommittees'])} House committees ({sum(1 for c in comms if c['chair'])} with a chair), "
          f"leaders {sorted(out['leaders'])}")


if __name__ == "__main__":
    for s in ([int(sys.argv[1])] if len(sys.argv) > 1 else C.sessions()):
        main(s)
