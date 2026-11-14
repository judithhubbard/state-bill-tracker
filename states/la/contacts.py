#!/usr/bin/env python3
"""Louisiana's legislators and committees, written as data/la/contacts_<session>.json in the shape build_data.py reads.

From what states/la/fetch.py downloads, no other web pages:
- data/la/members.json: today's members (the Legislature's member lists and each member's page on the House's or Senate's
  site): name, party, district and parishes, district office address and phones, email, and the Senate's posts ("Senate
  President", "President Pro Tempore"). Vacant seats are left out.
- data/la/committees.json: each house's standing committees with "Chair", "Vice Chair", "Member", "Interim Member" and
  "Ex Officio" members. The Speaker sits ex officio on every House committee and isn't listed as a member of any.
Seats: "S:12" and "H:71" (the Senate's 39 and the House's 105 single-member districts). The members serving now were
elected in 2023 for 2024-2028, or since in special elections, so an earlier year lists today's members first elected by
then, without their posts and committees.
Usage: python3 states/la/contacts.py [session]   (default: every year downloaded)
"""
import json, os, re, sys
from datetime import datetime
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
from fetch_contacts import committee_key, name_key
from states.la import convert as C
from states.la import profile as P

PARTY = {"Republican": "Republican", "Democrat": "Democratic", "Democratic": "Democratic", "Independent": "Independent"}


def phone(p):
    d = re.sub(r"\D", "", p or "")
    if len(d) == 11 and d[0] == "1":
        d = d[1:]
    return f"({d[:3]}) {d[3:6]}-{d[6:]}" if len(d) == 10 else None


def speaker():
    """The House member who sits ex officio on every House standing committee: the Speaker."""
    raw = (C.load(os.path.join(P.DATA, "committees.json"), {}) or {}).get("committees") or []
    house = [c for c in raw if c.get("house") == "H"]
    counts = {}
    for c in house:
        for m in c.get("members") or []:
            if m.get("role") == "Ex Officio":
                counts[m.get("name")] = counts.get(m.get("name"), 0) + 1
    hits = [n for n, k in counts.items() if house and k == len(house)]
    return hits[0] if len(hits) == 1 else None


def person(m, latest, posts):
    phones = []
    for p in m.get("phones") or []:
        ph = phone(p)
        if ph and ph not in [x[1] for x in phones]:
            phones.append(["District office", ph])
    office = ", ".join(x for x in (m.get("address") or []) if x and not re.search(r"\bFAX\b|^F:|^\(?\d{3}\)?\s*\d{3}-\d{4}$", x, re.I)) or None
    places = m.get("parishes") or ""
    if places:
        parts = [x.strip() for x in re.split(r",| and ", places) if x.strip()]
        places = ", ".join(f"{x} Parish" if not re.search(r"Parish", x) else x for x in parts)
    return {
        "name": C.display(m), "key": name_key(C.display(m)), "id": m["seat"],
        "party": PARTY.get(m.get("party"), m.get("party") or ""),
        "email": (m.get("email") or "").strip() or None, "form": None,
        "phone": phones[0][1] if phones else None, "phones": phones, "url": m.get("page"),
        "image": None, "office": office, "position": posts.get(m["seat"]) if latest else None,
        "places": places if latest else "",
        # The roll calls' form: the surname ("Carter, R." where two share it).
        "dataName": m["name"].split(",")[0].strip(),
    }


def canonical(h, name, known):
    """A committee list's name -> the bill histories' ("Senate Agriculture Committee" -> "Agriculture, Forestry,
    Aquaculture, and Rural Development"; "Senate & Governmental Affairs Committee" -> "Senate and Governmental Affairs")."""
    c = re.sub(r"\s+Committee$", "", (name or "").strip())
    c = re.sub(r"^(?:House |Senate )?Committee on ", "", c).replace(" & ", " and ")
    flat = lambda s: re.sub(r"[^a-z ]", "", s.lower().replace(",", "")).split()
    if c in known:
        return c
    for cand in ([c] + ([c[len("Senate "):]] if c.startswith("Senate ") else [])):
        w = flat(cand)
        hits = [k for k in known if flat(k)[:len(w)] == w]
        if len(hits) == 1:
            return hits[0]
    return c


def build(session):
    latest = session == max(C.sessions())
    posts = {}
    for m in C.members():
        if m.get("post") in ("Senate President", "President Pro Tempore"):
            posts[m["seat"]] = {"Senate President": "President of the Senate", "President Pro Tempore": "President Pro Tempore"}[m["post"]]
    spk = speaker()
    if spk:
        last, inits = C.split_name(spk)
        for m in C.members():
            if m["house"] == "H" and m["last"] == last and m["inits"] & inits:
                posts[m["seat"]] = "Speaker of the House"
    people = {}
    for m in C.members():
        if m["since"] and m["since"] > session:
            continue
        people[m["seat"]] = person(m, latest, posts)
    comms = {"S": {}, "H": {}}
    if latest:
        known = {"S": set(), "H": set()}
        for s in C.sessions():
            for r in C.load_session(s)[0]:
                for x in r["comms"]:
                    h, _, c = x.partition(" · ")
                    known[h].add(c)
        raw = (C.load(os.path.join(P.DATA, "committees.json"), {}) or {}).get("committees") or []
        seat_name = {m["seat"]: people[m["seat"]]["name"] for m in C.members() if m["seat"] in people}
        for c in raw:
            h = c.get("house")
            if h not in comms:
                continue
            name = canonical(h, c.get("name"), known[h])
            e = comms[h].setdefault(committee_key(name), {"name": name, "chair": None, "coChairs": [], "viceChair": None,
                                                          "meets": None, "members": []})
            for x in c.get("members") or []:
                if x.get("role") == "Ex Officio":
                    continue
                who = seat_name.get(f"{h}:{x.get('district')}")
                if not who:
                    continue
                if who not in e["members"]:
                    e["members"].append(who)
                if x.get("role") == "Chair" and not e["chair"]:
                    e["chair"] = who
                elif x.get("role") == "Vice Chair" and not e["viceChair"]:
                    e["viceChair"] = who
            e["members"].sort()
    leaders = {}
    if latest:
        for h, (name, role, _) in P.LEADERS.items():
            hit = next((x for sid, x in people.items() if sid[0] == h and x["key"].split()[-1:] == name_key(name).split()[-1:]
                        and x.get("position") == role), None)
            if hit:
                leaders[h] = {"name": hit["name"], "role": role}
    return {"session": session, "fetched": datetime.now(ZoneInfo(P.TIMEZONE)).strftime("%Y-%m-%d %H:%M"),
            "people": people, "since": {}, "senateCommittees": comms["S"], "assemblyCommittees": comms["H"],
            "leaders": leaders, "assemblyMembers": {}, "kept": []}


def main(session):
    out = build(session)
    latest = session == max(C.sessions())
    if latest and len(out["people"]) < 130:
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
