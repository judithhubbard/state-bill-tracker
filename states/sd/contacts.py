#!/usr/bin/env python3
"""South Dakota's legislators and committees, written as data/sd/contacts_<year>.json in the shape build_data.py reads,
from data/sd/<year>/members.json and committees.json (states/sd/fetch.py: the Legislature's JSON API).

Each of the 35 districts elects a senator and two representatives; districts 26 and 28 elect their representatives from
subdistricts ("26A", "26B"). As in New Jersey, a district's senator and both representatives are its legislators: seat
ids "S:12", and "H:12a", "H:12b" for the representatives (by last name; "H:26a" is 26A's). Phones are the House's and
Senate's Capitol switchboards; emails the state's. Members' ids are their SessionMemberId, which the roll calls use. A
member with an InactiveDate has left and is skipped (unless no one else holds the seat in a past year).
Usage: python3 states/sd/contacts.py [year]
"""
import json, os, re, sys
from datetime import datetime
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
from fetch_contacts import committee_key, name_key
from states.sd import profile as P

PARTY = {"D": "Democratic", "R": "Republican"}


def seats(members):
    """SessionMemberId -> seat id, for everyone in the list (those who left too, sharing their successor's seat)."""
    out, by_district = {}, {}
    for m in members:
        d = m.get("District") or ""
        if m.get("MemberType") == "S":
            out[m["SessionMemberId"]] = f"S:{int(re.sub(r'\D', '', d))}"
        elif re.fullmatch(r"\d+[AB]", d):
            out[m["SessionMemberId"]] = f"H:{int(d[:-1])}{d[-1].lower()}"
        else:
            by_district.setdefault(int(d), []).append(m)
    for d, ms in by_district.items():
        current = sorted((m for m in ms if not m.get("InactiveDate")), key=lambda m: (m["LastName"], m["FirstName"]))
        for i, m in enumerate(current[:2]):
            out[m["SessionMemberId"]] = f"H:{d}{'ab'[i]}"
        for m in ms:  # someone who left: the seat of the one who took it, else the first free letter
            if m["SessionMemberId"] not in out:
                taken = {out[x["SessionMemberId"]] for x in current[:2]}
                out[m["SessionMemberId"]] = next((f"H:{d}{c}" for c in "ab" if f"H:{d}{c}" not in taken), f"H:{d}a")
    return out


def name_of(m):
    return re.sub(r"\s+", " ", f"{m.get('FirstName') or ''} {m.get('LastName') or ''}").strip()


def build(year):
    folder = os.path.join(P.DATA, str(year))
    members = json.load(open(os.path.join(folder, "members.json")))
    seat = seats(members)
    people = {}
    for m in sorted(members, key=lambda m: bool(m.get("InactiveDate"))):
        sid = seat[m["SessionMemberId"]]
        if sid in people:
            continue
        # The House's and the Senate's Capitol switchboards (one member's is typed "605-733-": Pierre's exchange is 773).
        ph = re.sub(r"^605-733-", "605-773-", m.get("CapitolPhone") or "")
        people[sid] = {
            "name": name_of(m), "key": name_key(name_of(m)), "id": str(m["SessionMemberId"]),
            "party": PARTY.get(m.get("Politics"), m.get("PartyName") or ""), "email": m.get("EmailState") or None,
            "form": None, "phone": ph or None, "phones": [[f"{'Senate' if sid[0] == 'S' else 'House'} switchboard", ph]] if ph else [],
            "url": f"https://sdlegislature.gov/Legislators/Profile/{m['SessionMemberId']}/Detail", "image": None,
            "office": "", "position": m.get("Position") or None, "places": f"District {m.get('District')}",
            "dataName": m.get("UniqueName") or m.get("LastName"),
        }
    comms = {"S": {}, "H": {}}
    try:
        committees = json.load(open(os.path.join(folder, "committees.json")))
    except (OSError, ValueError):
        committees = []
    for c in committees:
        d, l = c.get("detail") or {}, c.get("listing") or {}
        h = d.get("Body") or (l.get("Committee") or {}).get("Body")
        if d.get("FullBody") or h not in comms:
            continue  # the whole House or Senate, and joint committees ("A")
        full = l.get("FullName") or ""
        name = re.sub(r"^(?:House|Senate) (?:Committee on )?", "", full)
        ms = d.get("CommitteeMembers") or []
        chair = next((m for m in ms if m.get("CommitteeMemberType") == "Chair"), None)
        comms[h][committee_key(name)] = {"name": name, "chair": name_of(chair["Member"]) if chair else None, "meets": None,
                                         "members": sorted(name_of(m["Member"]) for m in ms)}
    leaders = {}
    for h, (name, role, _) in P.LEADERS.items():
        hit = next((p for sid, p in people.items() if sid[0] == h and p["position"] and role.startswith(p["position"])), None)
        if hit:
            leaders[h] = {"name": hit["name"], "role": role}
    return {"session": year, "fetched": datetime.now(ZoneInfo(P.TIMEZONE)).strftime("%Y-%m-%d %H:%M"),
            "people": people, "since": {}, "senateCommittees": comms["S"], "assemblyCommittees": comms["H"],
            "leaders": leaders, "assemblyMembers": {}, "kept": []}


def main(year):
    out = build(year)
    if len(out["people"]) < 100:
        raise SystemExit(f"only {len(out['people'])} legislators; kept the last contacts")
    path = os.path.join(P.DATA, f"contacts_{year}.json")
    json.dump(out, open(path, "w"), indent=1, ensure_ascii=False)
    ppl = out["people"].values()
    comms = list(out["senateCommittees"].values()) + list(out["assemblyCommittees"].values())
    print(f"{path}: {len(out['people'])} legislators ({sum(1 for p in ppl if p['email'])} with email, "
          f"{sum(1 for p in ppl if p['phone'])} with a phone), {len(comms)} committees ({sum(1 for c in comms if c['chair'])} "
          f"with a chair), leaders {sorted(out['leaders'])}")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else P.session_of(datetime.now(ZoneInfo(P.TIMEZONE)).year))
