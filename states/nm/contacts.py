#!/usr/bin/env python3
"""New Mexico's legislators and committees, written as data/nm/contacts_<session>.json in the shape build_data.py reads.

From what states/nm/fetch.py downloads, no other web pages:
- data/nm/<year>/members.txt: the year's legislators (the Legislature's merge file: name, party, counties, district,
  mailing address, Capitol room and phone, email).
- data/nm/members.json: each current member's page (sponsor code, full name, leadership post, counties, committees), and
  data/nm/members/<code>.html for members who have left (district and years of service).
- data/nm/committees.json: the standing committees with each member's role (Chair, Vice Chair, Ranking Member, Member).
Each district elects one member: seats "S:12", "H:45" (42 Senate and 70 House districts, drawn separately). Capitol
phones are the Capitol's (505) 986 lines; several members share one office line. A past year lists that year's members.
Usage: python3 states/nm/contacts.py [session]   (default: every year downloaded)
"""
import json, os, re, sys
from datetime import datetime
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
from fetch_contacts import committee_key, name_key
from states.nm import convert as C
from states.nm import profile as P

PARTY = {"R": "Republican", "D": "Democratic", "I": "Independent", "DTS": "Independent"}
PAGE = "https://www.nmlegis.gov/Members/Legislator?SponCode={}"


def phone(p):
    d = re.sub(r"\D", "", p or "")
    if len(d) == 7:
        d = "505" + d  # the Capitol's numbers are written without the area code: "986-4254"
    if len(d) == 11 and d[0] == "1":
        d = d[1:]
    return f"({d[:3]}) {d[3:6]}-{d[6:]}" if len(d) == 10 else None


def code_for(h, district, last):
    """The member's sponsor code: a current member in that seat with that last name, else a former one."""
    for code, m in C.members_json().items():
        if m.get("house") == h and m.get("district") and int(m["district"]) == district and \
                C.norm(C.bare(m.get("name"))).endswith(C.norm(C.bare(last))):
            return code, m
    for code, m in C.former().items():
        if m["house"] == h and m["district"] == district and C.norm(C.bare(m["name"])).endswith(C.norm(C.bare(last))):
            return code, None
    return None, None


def person(session, r, latest):
    h = r["house"]
    code, m = code_for(h, r["district"], r["last"])
    if m and m.get("name"):
        name = m["name"]
    elif code:
        name = C.former()[code]["name"]
    else:
        name = f"{r['first']} {r['last']}".strip()
    phones = []
    for label, raw in (("Capitol", r.get("capitol")), ("Office", r.get("phone")), ("Office", (m or {}).get("phone")),
                       ("Office", (m or {}).get("phone2"))):
        ph = phone(raw)
        if ph and ph not in [x[1] for x in phones]:
            phones.append([label, ph])
    room = r.get("room")
    county = ((m or {}).get("county") if latest else "") or ""
    return {
        "name": name, "key": name_key(name), "id": code, "party": PARTY.get(r.get("party"), r.get("party") or ""),
        "email": (r.get("email") or (m or {}).get("email") or "").strip() or None, "form": None,
        "phone": phones[0][1] if phones else None, "phones": phones, "url": PAGE.format(code) if code else None,
        "image": None, "office": f"State Capitol, Room {room}" if room else None,
        "position": ((m or {}).get("post") or "").replace("Of The", "of the") or None if latest else None,
        "places": re.sub(r"\s*&\s*", " and ", county) + (" County" if county and "," not in county and "&" not in county else
                                                           " Counties" if county else ""),
        "dataName": C.bare(r["last"]),
    }


def build(session):
    latest = session == max(C.sessions())
    people = {}
    for r in sorted(C.roster(session), key=lambda r: bool(r.get("former"))):
        sid = f"{r['house']}:{r['district']}"
        if sid in people or (latest and not C.is_current(r)):
            continue  # (this year's page lists today's members: a seat left vacant stays empty)  # the member on the list holds the seat; one who left shows in that year's votes by seat
        people[sid] = person(session, r, latest)
    comms = {"S": {}, "H": {}}
    if latest:
        try:
            raw = json.load(open(os.path.join(P.DATA, "committees.json"), encoding="utf-8"))
        except (OSError, ValueError):
            raw = []
        names = {p["id"]: p["name"] for p in people.values() if p["id"]}
        for c in raw:
            h = c["code"][0]
            name = C.comm_name(c["code"])
            e = comms[h].setdefault(committee_key(name), {"name": name, "chair": None, "coChairs": [], "viceChair": None,
                                                          "meets": c.get("meets") or None, "members": [],
                                                          "url": f"https://www.nmlegis.gov/Committee/Standing_Committee?CommitteeCode={c['code']}"})
            for x in c.get("members") or []:
                who = names.get(x.get("code")) or (x.get("name") or "").strip()
                if not who:
                    continue
                if who not in e["members"]:
                    e["members"].append(who)
                if x.get("role") == "Chair":
                    if e["chair"]:
                        e["coChairs"].append(who)
                    else:
                        e["chair"] = who
                elif x.get("role") == "Vice Chair" and not e["viceChair"]:
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
    if latest and len(out["people"]) < 100:
        raise SystemExit(f"{session}: only {len(out['people'])} legislators; kept the last contacts")
    path = os.path.join(P.DATA, f"contacts_{session}.json")
    json.dump(out, open(path, "w"), indent=1, ensure_ascii=False)
    ppl = out["people"].values()
    comms = list(out["senateCommittees"].values()) + list(out["assemblyCommittees"].values())
    print(f"{path}: {len(out['people'])} legislators ({sum(1 for p in ppl if p['email'])} with email, "
          f"{sum(1 for p in ppl if p['phone'])} with a phone, {sum(1 for p in ppl if p['id'])} with a page), "
          f"{len(out['senateCommittees'])} Senate and {len(out['assemblyCommittees'])} House committees "
          f"({sum(1 for c in comms if c['chair'])} with a chair), leaders {sorted(out['leaders'])}")


if __name__ == "__main__":
    for s in ([int(sys.argv[1])] if len(sys.argv) > 1 else C.sessions()):
        main(s)
