#!/usr/bin/env python3
"""Kansas's legislators and committees, written as data/ks/contacts_<session>.json in the shape build_data.py reads.

From what states/ks/fetch.py downloads from the Legislature's API, no other web pages:
- data/ks/<session>/legislators.json: every member the API lists for the biennium (it lists past members too, marked
  "Inactive"): name, party, district, email. Each seat goes to its active member (convert.seats(); a seat whose member
  left and wasn't replaced goes to that member, if they voted in the biennium's roll calls).
- data/ks/members/<kpid>.json: the active biennium's active members' details: Capitol office and phone, home phone,
  leadership roles. A past biennium's contacts have the email alone.
- data/ks/<session>/committees.json: each house's committees, with chairs, vice chairs and members by kpid, and the
  meeting time and room. The Senate Ways and Means subcommittees and the joint, special and select committees that bills
  aren't sent to are left out.
- data/ks/<session>/leadership.json: the Speaker, the President of the Senate and the other leaders.
Usage: python3 states/ks/contacts.py [session]   (default: every biennium downloaded)
"""
import json, os, re, sys
from datetime import datetime
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
from fetch_contacts import committee_key, name_key
from states.ks import convert as C
from states.ks import profile as P

PARTY = {"D": "Democratic", "R": "Republican"}
LEAD = re.compile(r"^(Speaker of the House|Speaker Pro Tem|President of the Senate|Vice President of the Senate|"
                  r"(House|Senate) (Majority|Minority) Leader)$")


def phone(x):
    d = re.sub(r"\D", "", x or "")
    if len(d) == 11 and d[0] == "1":
        d = d[1:]
    return f"({d[:3]}) {d[3:6]}-{d[6:]}" if len(d) == 10 else None


def meets(c):
    t, room = C.text(c.get("mtg_time")), C.text(c.get("mtg_room"))
    if not t or re.search(r"on call", t, re.I):
        return None
    t = re.sub(r"\b(am|pm)\b", lambda m: m.group(1)[0] + ".m.", t, flags=re.I)
    return f"at {t}" + (f" in Room {room}" if room and not re.search(r"on call", room, re.I) else "")


def build(session):
    now = session == max(C.sessions())
    bien = f"b{session}_{str(session + 1)[2:]}"
    seats = C.seats(session)
    ms = C.members(session)
    people, by_kpid = {}, {}
    roles = {}
    for x in (C.load(session, "leadership", {}) or {}).get("leadership") or []:
        if x.get("status") == "Active" and x.get("mem_kpid"):
            roles.setdefault(x["mem_kpid"], C.text(x.get("title")))
    for k, sid in seats.items():
        m = ms[k]
        pg = C.member_page(k) if now else None
        if pg and pg.get("biennium") != bien:
            pg = None
        raw = next((x for x in (C.load(session, "legislators", {}) or {}).get("legislators") or [] if x.get("kpid") == k), {})
        phones = []
        for label, num in (("Topeka office", (pg or {}).get("office_phone")), ("Home", (pg or {}).get("home_phone"))):
            ph = phone(num)
            if ph and ph not in [p[1] for p in phones]:
                phones.append([label, ph])
        pos = roles.get(k) if now else None
        people[sid] = {
            "name": m["name"], "key": name_key(m["name"]), "id": k, "party": PARTY.get(m["party"], ""),
            "email": C.text((pg or {}).get("email") or raw.get("email")) or None, "form": None,
            "phone": phones[0][1] if phones else None, "phones": phones,
            "url": f"https://kslegislature.gov/{bien}/legislators/{k}/", "image": None,
            "office": f"Room {C.text(pg['office_number'])}, State Capitol, 300 SW 10th Ave., Topeka, KS 66612" if pg and C.text(pg.get("office_number")) else None,
            "position": pos if pos and LEAD.match(pos) else None,
            "places": C.text(raw.get("county")), "dataName": m["name"],
        }
        by_kpid[k] = m["name"]
    comms = {"S": {}, "H": {}}
    for c in (C.load(session, "committees", {}) or {}).get("committees") or []:
        h = {"Senate": "S", "House": "H"}.get(c.get("chamber"))
        title = C.text(c.get("title"))
        if not h or c.get("status") != "Active" or re.search(r"Subcommittee|Investigating|Government Oversight|Confirmation", title):
            continue
        name = C.committee_name(re.sub(r"\s*\((House|Senate)\)$", "", title))
        name = re.sub(r"^(Senate|House) Select Committee on ", "Select Committee on ", name)
        who = lambda k: by_kpid.get(k) or (ms.get(k) or {}).get("name")
        chair = next((who(k) for k in c.get("chair") or [] if who(k)), None)
        vice = next((who(k) for k in c.get("vice_chair") or [] if who(k)), None)
        members = sorted({who(k) for k in (c.get("members") or []) + (c.get("chair") or []) + (c.get("vice_chair") or []) if who(k)})
        comms[h][committee_key(name)] = {"name": name, "chair": chair, "coChairs": [], "viceChair": vice,
                                        "meets": meets(c), "members": members}
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
    if len(out["people"]) < 150:
        raise SystemExit(f"{session}: only {len(out['people'])} legislators; kept the last contacts")
    path = os.path.join(P.DATA, f"contacts_{session}.json")
    json.dump(out, open(path, "w"), indent=1, ensure_ascii=False)
    ppl = out["people"].values()
    comms = list(out["senateCommittees"].values()) + list(out["assemblyCommittees"].values())
    print(f"{path}: {len(out['people'])} legislators ({sum(1 for p in ppl if p['email'])} with an email, "
          f"{sum(1 for p in ppl if p['phone'])} with a phone), {len(out['senateCommittees'])} Senate and "
          f"{len(out['assemblyCommittees'])} House committees ({sum(1 for c in comms if c['chair'])} with a chair), "
          f"leaders {sorted(out['leaders'])}")


if __name__ == "__main__":
    for s in ([int(sys.argv[1])] if len(sys.argv) > 1 else C.sessions()):
        main(s)
