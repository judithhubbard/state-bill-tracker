#!/usr/bin/env python3
"""West Virginia's legislators and committees, written as data/wv/contacts_<session>.json in the shape build_data.py reads.

From what states/wv/fetch.py downloads, no other web pages:
- data/wv/members/members.json: today's members (from the House and Senate rosters and each member's page): name, party,
  district (and a senator's counties), Capitol office, phone, email, leadership post, committees.
- data/wv/members/committees.json: each house's standing committees and, in the House since 2025, its subcommittees,
  with "Chair", "Vice-Chair" and "Minority Chair". The Senate's Confirmations, Enrolled Bills and Interstate Cooperation
  committees (which don't take bills) are left out.
Seats: "H:62" (the House of Delegates' 100 single-member districts since 2022); "S:5a"/"S:5b" (each of the 17 Senate
districts elects two senators, in alternate even years; the two are lettered by surname, as in convert.members()).
Only today's members are listed (no past member lists): the latest year lists them all, with their posts and committees;
an earlier year lists those of today's members who voted (convert.seat_of(): continuing members only before 2025) or
sponsored a bill in their house that year, without posts.
Usage: python3 states/wv/contacts.py [session]   (default: every year downloaded)
"""
import json, os, re, sys
from datetime import datetime
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
from fetch_contacts import committee_key, name_key
from states.wv import convert as C
from states.wv import profile as P

PARTY = {"Republican": "Republican", "Democrat": "Democratic", "Democratic": "Democratic", "Independent": "Independent"}
PAGE = "https://www.wvlegislature.gov/{sub}/lawmaker.cfm?member={member}"
NO_BILLS = {"Confirmations", "Enrolled Bills", "Interstate Cooperation"}


def phone(p):
    d = re.sub(r"\D", "", p or "")
    if len(d) == 11 and d[0] == "1":
        d = d[1:]
    return f"({d[:3]}) {d[3:6]}-{d[6:]}" if len(d) == 10 else None


def person(m, latest):
    ph = phone(m.get("capitol_phone") or m.get("phone"))
    office = ", ".join(x for x in (m.get("capitol") or []) if x) or (m.get("office") or "").replace("\n", ", ") or None
    places = m.get("counties") or m.get("district_counties") or ""
    places = ", ".join(re.sub(r"^(.+?)(?: \(part\))?$", lambda x: f"{x.group(1)} County" + (" (part)" if "(part)" in c.lower() else ""), c.strip())
                       for c in places.split(",") if c.strip())
    sub = "House" if m["house"] == "H" else "Senate1"
    return {
        "name": m["name"], "key": name_key(m["name"]), "id": m["member"], "party": PARTY.get(m.get("party"), m.get("party") or ""),
        "email": (m.get("email") or "").strip() or None, "form": None,
        "phone": ph, "phones": [["Capitol", ph]] if ph else [], "url": PAGE.format(sub=sub, member=m["member"].replace(" ", "%20")),
        "image": None, "office": office, "position": (m.get("post") or None) if latest else None,
        "places": places if latest else "",
        # The name the roll calls and sponsor lists use ("Smith, D", "MAYNARD, M"): the pages' own key.
        "dataName": re.sub(r"^(?:Delegate|Senator|Speaker|President)\s+", "", m["member"]).rstrip("."),
    }


def served(session):
    """(house, seat) of today's members who voted or sponsored a bill in their house that year."""
    out = set()
    for h, names in C.roll_names(session).items():
        for last, init in names:
            sid = C.seat_of(session, h, f"{last}, {init}" if init else last)
            if "?" not in sid:
                out.add(sid)
    for r in C.load_session(session)[0]:
        for v in r["vers"]:
            for n in [v["sponsor"]] + v["cosponsors"]:
                m = next((x for x in C.members() if x["house"] == v["p"][0] and x["name"] == n), None)
                if m:
                    out.add(m["seat"])
    return out


def build(session):
    latest = session == max(C.sessions())
    keep = None if latest else served(session)
    people = {}
    for m in C.members():
        if keep is not None and m["seat"] not in keep:
            continue
        people[m["seat"]] = person(m, latest)
    comms = {"S": {}, "H": {}}
    if latest:
        try:
            raw = json.load(open(os.path.join(P.DATA, "members", "committees.json"), encoding="utf-8")).get("committees") or []
        except (OSError, ValueError):
            raw = []
        by_member = {m["member"].rstrip("."): m for m in C.members()}
        for c in raw:
            h = c.get("house")
            name = C.comm_name(c.get("name") or "")
            if h not in comms or not name or name in NO_BILLS:
                continue
            e = comms[h].setdefault(committee_key(name), {"name": name, "chair": None, "coChairs": [], "viceChair": None,
                                                          "meets": None, "members": []})
            for x in c.get("members") or []:
                m = by_member.get((x.get("member") or "").rstrip("."))
                if not m:
                    continue
                who = m["name"]
                if who not in e["members"]:
                    e["members"].append(who)
                role = x.get("role") or ""
                if role == "Chair":
                    if e["chair"]:
                        e["coChairs"].append(who)
                    else:
                        e["chair"] = who
                elif role == "Vice-Chair" and not e["viceChair"]:
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
    if latest and len(out["people"]) < 125:
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
