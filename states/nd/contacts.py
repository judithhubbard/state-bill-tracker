#!/usr/bin/env python3
"""North Dakota's legislators and committees, written as data/nd/contacts_<session>.json in the shape build_data.py reads.

From what states/nd/fetch.py downloads, no other web pages:
- data/nd/<session>/members.json: each member's id (the roll calls use it), name ("Pyle, Brandy L."), house, party,
  district and biography page; only active members get a seat (convert.seats(): "S:12"; a district's two
  representatives "H:12a" and "H:12b", the subdistricts 4A/4B and 9A/9B each one).
- data/nd/members/<slug>.json: the biography page's phones (Home, Work, Cell; listed as the member gives them, each
  number once: a few give one number twice) and email. The slug is the members.json url's; the same person can have a
  page per spelling of their name ("jeff-a-hoverson" in 2023, "jeff-hoverson" in 2025), each read for its own assembly.
- committees.json: each house's standing committees and the joint committees of the special sessions, with their
  members (is_chair, is_vice_chair). Procedural committees (Rules, Delayed Bills, Employment ...) and the
  Appropriations divisions are left out (bills aren't referred to them).
- leaders.json: the leadership page's positions, for the current assembly only ("Majority Leader"; a position with an
  end date that has passed, "Effective 1/7/25 - 4/29/25", is dropped; "Effective 6/2/26" is kept).
Usage: python3 states/nd/contacts.py [session]   (default: every assembly downloaded)
"""
import json, os, re, sys
from datetime import date, datetime
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
from fetch_contacts import committee_key, name_key
from states.nd import convert as C
from states.nd import profile as P

PARTY = {"Republican": "Republican", "Democrat": "Democratic", "Democratic": "Democratic", "Democratic-NPL": "Democratic"}
PROCEDURAL = re.compile(r"^(?:Rules|Delayed Bills|Committees|Employment|Arrangements for|Correction and Revision)|Division$")


def phone(x):
    d = re.sub(r"\D", "", x or "")
    if len(d) == 11 and d[0] == "1":
        d = d[1:]
    return f"({d[:3]}) {d[3:6]}-{d[6:]}" if len(d) == 10 else None


def bio(url):
    slug = (url or "").rstrip("/").rsplit("/", 1)[-1]
    try:
        return json.load(open(os.path.join(P.DATA, "members", f"{slug}.json")))
    except (OSError, ValueError):
        return {}


def current_position(pos, today):
    """"Majority Leader" -> itself; "Minority Leader Effective 1/3/23 - 4/30/23" -> None once it's past; "... Effective
    after 4/30/23" / "Effective 6/2/26" -> the position, once started; "Effective through 4/9/25" -> None after it."""
    pos = C.text(pos)
    m = re.match(r"(.+?)\s+Effective\s+(.*)$", pos)
    if not m:
        return pos or None
    role, when = m.group(1), m.group(2)
    ds = [datetime.strptime(x, "%m/%d/%y").date() for x in re.findall(r"\d{1,2}/\d{1,2}/\d{2}", when)]
    if re.match(r"through", when) and ds and today > ds[0]:
        return None
    if " - " in when and len(ds) == 2 and today > ds[1]:
        return None
    if ds and today < ds[0] and not re.match(r"through", when):
        return None
    return role


def build(session):
    today = datetime.now(ZoneInfo(P.TIMEZONE)).date()
    now = session >= P.session_of(today.year)  # positions are named for the current assembly only
    seats = C.seats(session)
    people = {}
    for m in C.load(session, "members"):
        sid = seats.get(m.get("id"))
        if not sid:
            continue
        name = C.person(m["name"])
        b = bio(m.get("url"))
        phones, seen = [], set()
        for label in ("Cell", "Home", "Work"):
            ph = phone((b.get("phones") or {}).get(label))
            if ph and ph not in seen:
                seen.add(ph)
                phones.append([label, ph])
        people[sid] = {
            "name": name, "key": name_key(name), "id": m.get("id"), "party": PARTY.get(m.get("party"), m.get("party") or ""),
            "email": C.text(b.get("email")) or None, "form": None,
            "phone": phones[0][1] if phones else None, "phones": phones,
            "url": m.get("url"), "image": b.get("photo") or None, "office": None,
            "position": None, "places": "", "dataName": name,
        }
    comms = {"S": {}, "H": {}}
    for c in C.load(session, "committees"):
        h = C.CHAMBER.get(c.get("chamber"))
        name = C.text(c.get("name"))
        if h not in comms or c.get("type") not in ("Standing", "Procedural") or PROCEDURAL.search(name):
            continue
        ms = [x for x in c.get("members") or [] if C.CHAMBER.get(x.get("chamber")) == h]
        chairs = [C.person(x["name"]) for x in ms if x.get("is_chair")]
        vice = [C.person(x["name"]) for x in ms if x.get("is_vice_chair")]
        comms[h][committee_key(name)] = {"name": name, "chair": chairs[0] if chairs else None, "coChairs": chairs[1:],
                                         "viceChair": vice[0] if vice else None, "meets": None,
                                         "members": sorted({C.person(x["name"]) for x in ms})}
    leaders = {}
    if now:
        for l in C.load(session, "leaders"):
            pos = current_position(l.get("position"), today)
            h = C.CHAMBER.get(l.get("chamber"))
            if not pos or not h:
                continue
            hit = next((p for sid, p in people.items() if sid[0] == h and p["key"] == name_key(l.get("name"))), None)
            if hit:
                hit["position"] = pos if not hit["position"] else f"{hit['position']}; {pos}"
        for h, (name, role, _) in P.LEADERS.items():
            hit = next((p for sid, p in people.items() if sid[0] == h and p["key"] == name_key(name)), None)
            if hit:
                leaders[h] = {"name": hit["name"], "role": role}
    return {"session": session, "fetched": datetime.now(ZoneInfo(P.TIMEZONE)).strftime("%Y-%m-%d %H:%M"),
            "people": people, "since": {}, "senateCommittees": comms["S"], "assemblyCommittees": comms["H"],
            "leaders": leaders, "assemblyMembers": {}, "kept": []}


def main(session):
    out = build(session)
    if len(out["people"]) < 120:
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
