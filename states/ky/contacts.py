#!/usr/bin/env python3
"""Kentucky's legislators and committees, written as data/ky/contacts_<session>.json in the shape build_data.py reads.

From what states/ky/fetch.py downloads, no other web pages:
- data/ky/members/members.json: the current members (house, district, counties, party, leadership post, committees with
  their roles, addresses, phones, email, profile number).
- data/ky/committees.json: the House and Senate standing committees with their members by profile number, "Chair" and
  "Vice Chair". The budget review subcommittees and the Enrollment committees are left out.
Each district elects one member: seats "S:12", "H:45". Most members list only "LRC: 502-564-8100", the Legislative
Research Commission's message line, which takes messages for every member: it's shown as "Capitol (LRC message line)";
home and work numbers follow when a member lists them (faxes are left out).
Only current members are published (no past member lists): the latest year lists them all, with their posts and
committees; a past year lists the current members who sponsored a bill in their house that year, without posts.
Usage: python3 states/ky/contacts.py [session]   (default: every year downloaded)
"""
import json, os, re, sys
from datetime import datetime
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
from fetch_contacts import committee_key, name_key
from states.ky import convert as C
from states.ky import profile as P

PARTY = {"R": "Republican", "D": "Democratic", "I": "Independent"}
PROFILE = "https://legislature.ky.gov/Legislators/Pages/Legislator-Profile.aspx?DistrictNumber={}"
LABEL = {"LRC": "Capitol (LRC message line)", "Home": "Home", "Work": "Work"}


def phone(p):
    d = re.sub(r"\D", "", p or "")
    if len(d) == 11 and d[0] == "1":
        d = d[1:]
    return f"({d[:3]}) {d[3:6]}-{d[6:]}" if len(d) == 10 else None


def person(m, latest):
    phones = []
    for raw in m.get("phones") or []:
        label, _, num = raw.partition(":")
        if "fax" in num.lower():
            continue
        ph = phone(num)
        if ph and ph not in [x[1] for x in phones]:
            phones.append([LABEL.get(label.strip(), label.strip()), ph])
    # A member's own number first; the shared message line last.
    phones.sort(key=lambda x: x[0].startswith("Capitol"))
    office = ", ".join(m.get("legislative") or m.get("capitol") or []) or None
    return {
        "name": m["name"], "key": name_key(m["name"]), "id": m.get("sponsor_id"), "party": PARTY.get(m.get("party"), m.get("party") or ""),
        "email": (m.get("email") or "").strip() or None, "form": None,
        "phone": phones[0][1] if phones else None, "phones": phones, "url": PROFILE.format(m["number"]),
        "image": None, "office": office, "position": (m.get("post") or None) if latest else None,
        "places": ", ".join(re.sub(r"^(.+?)(?: \(Part\))?$", lambda x: f"{x.group(1)} County" + (" (part)" if "(Part)" in c else ""), c)
                           for c in m.get("counties") or []) if latest else "", "dataName": C.surname(m["name"]),
    }


def build(session):
    latest = session == max(C.sessions())
    people = {}
    sponsors = set()
    if not latest:
        for r in C.load_session(session)[0]:
            for v in r["vers"]:
                for n in [v["sponsor"]] + v["cosponsors"]:
                    sponsors.add((v["p"][0], n))
    for m in C.members():
        h = m["house"]
        if not latest and (h, m["name"]) not in sponsors:
            continue
        people[f"{h}:{m['district']}"] = person(m, latest)
    comms = {"S": {}, "H": {}}
    if latest:
        try:
            raw = json.load(open(os.path.join(P.DATA, "committees.json"), encoding="utf-8")).get("committees") or []
        except (OSError, ValueError):
            raw = []
        by_number = {m["number"]: m for m in C.members()}
        for c in raw:
            hm = re.search(r"\((H|S)\)$", c.get("name") or "")
            if not hm or not re.search(r"Standing Committee", c.get("kind") or "") or re.match(r"BR Sub", c["name"]):
                continue
            name = C.comm_name(c["name"])
            if name == "Enrollment":
                continue
            h = hm.group(1)
            e = comms[h].setdefault(committee_key(name), {"name": name, "chair": None, "coChairs": [], "viceChair": None,
                                                          "meets": None, "members": []})
            for x in c.get("members") or []:
                m = by_number.get(x.get("number"))
                who = m["name"] if m else (x.get("name") or "").strip()
                if not who:
                    continue
                if who not in e["members"]:
                    e["members"].append(who)
                role = x.get("role") or ""
                if role == "Chair":
                    if e["chair"]:
                        e["coChairs"].append(who)
                    else:
                        e["chair"] = who
                elif role == "Vice Chair" and not e["viceChair"]:
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
