#!/usr/bin/env python3
"""Arkansas's legislators and committees, written as data/ar/contacts_<year>.json in the shape build_data.py reads.

All from the Bureau of Legislative Research's files that states/ar/fetch.py saves in data/ar/<biennium>/ (no web pages):
- LegislativeMembers.txt: each member's names, house (Senator/Representative), district, party, phone and email, and the
  Sponsor Name the bill files and roll calls use ("S. Flowers"), kept as "dataName" and "id". Seat ids "S:8", "H:12".
  One senator or representative a district (35 and 100). A finished General Assembly's copy is the members when it was
  kept (2023-24's: January 2024).
- Committees.txt and CommitteeInformationChair.txt: each house's standing committees (types H and S) and the joint
  committees bills are referred to (Joint Budget, Public Retirement and Social Security Programs, Energy, Military and
  Veterans Affairs), with their members and Chair (or Co-Chair, for a joint committee's house) and Vice-Chair. A joint
  committee is listed for both houses, each with its own house's members.
- Leaders: P.LEADERS and P.POSITIONS, for the current year only.
Usage: python3 states/ar/contacts.py [year]   (default: the current year; run for each year shown)
"""
import json, os, re, sys, urllib.parse
from datetime import datetime
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
from fetch_contacts import committee_key, name_key
from states.ar import convert as C
from states.ar import profile as P

# Joint committees that bills are referred to (as C.committee() names them).
JOINT = {"Joint Budget", "Public Retirement and Social Security Programs", "Energy", "Military and Veterans Affairs"}
# Each house's committees that aren't standing committees on a subject.
NOT_STANDING = re.compile(r"business meeting|committee of the whole|orientation|biennial institute|legislative council|"
                          r"subcommittee|joint performance review|ethics|committee on committees|enrolled bills|efficiency", re.I)


def phone(x):
    d = re.sub(r"\D", "", x or "")
    return f"({d[:3]}) {d[3:6]}-{d[6:10]}" if len(d) == 10 else None


def build(year):
    b = C.biennium(year)
    now = year >= P.session_of(datetime.now(ZoneInfo(P.TIMEZONE)).year)  # leaders are named for the current year only
    people, by_id = {}, {}
    for r in C.rows(b, "LegislativeMembers.txt"):
        if len(r) < 19 or r[6] not in ("Senator", "Representative") or not r[8].isdigit() or (len(r) > 19 and r[19] not in ("A", "")):
            continue
        h = "S" if r[6] == "Senator" else "H"
        sid, name = f"{h}:{int(r[8])}", C.text(f"{r[1]} {r[2]}")
        ph = phone(r[7])
        people[sid] = {
            "name": name, "key": name_key(name), "id": r[18], "party": {"R": "Republican", "D": "Democratic"}.get(r[17], r[17]),
            "email": r[11] if "@" in r[11] else None, "form": None,
            "phone": ph, "phones": [["Phone", ph]] if ph else [],
            "url": f"https://arkleg.state.ar.us/Legislators/Detail?member={urllib.parse.quote_plus(r[18])}"
                   f"&ddBienniumSession={b}%2F{P.session_id(b)}",
            "image": None, "office": "State Capitol, Little Rock", "position": P.POSITIONS.get((h, name)) if now else None,
            "places": r[21] if len(r) > 21 else "", "dataName": r[18],
        }
        by_id[r[0]] = sid
    kinds = {r[1]: (r[2], r[0]) for r in C.rows(b, "Committees.txt") if len(r) > 2}
    roles = {}
    for r in C.rows(b, "CommitteeInformationChair.txt"):
        if len(r) >= 5 and r[2] in by_id:
            roles.setdefault(r[0], []).append((by_id[r[2]], r[4].lower()))
    comms = {"S": {}, "H": {}}
    for code, (kind, raw) in kinds.items():
        name = C.committee(raw)
        if kind in ("S", "H") and not NOT_STANDING.search(raw):
            houses = [kind]
        elif kind == "J" and name in JOINT:
            houses = ["S", "H"]
        else:
            continue
        for h in houses:
            mine = [(sid, role) for sid, role in roles.get(code, []) if sid[0] == h and role not in ("alternate", "ex officio", "ex-officio", "non-voting")]
            if not mine:
                continue
            pick = lambda *want: next((people[sid]["name"] for sid, role in mine if role in want), None)
            comms[h][committee_key(name)] = {"name": name, "chair": pick("chair", "co-chair"), "viceChair": pick("vice-chair"),
                                             "rankingMinority": None, "meets": None,
                                             "members": sorted({people[sid]["name"] for sid, _ in mine})}
    leaders = {}
    for h, (name, role, _) in (P.LEADERS.items() if now else ()):
        hit = next((p for sid, p in people.items() if sid[0] == h and p["key"] == name_key(name)), None)
        if hit:
            hit["position"] = role
            leaders[h] = {"name": hit["name"], "role": role}
    return {"session": year, "fetched": datetime.now(ZoneInfo(P.TIMEZONE)).strftime("%Y-%m-%d %H:%M"),
            "people": people, "since": {}, "senateCommittees": comms["S"], "assemblyCommittees": comms["H"],
            "leaders": leaders, "assemblyMembers": {}, "kept": []}


def main(year):
    out = build(year)
    if len(out["people"]) < 120:
        raise SystemExit(f"only {len(out['people'])} legislators; kept the last contacts")
    path = os.path.join(P.DATA, f"contacts_{year}.json")
    json.dump(out, open(path, "w"), indent=1, ensure_ascii=False)
    ppl = out["people"].values()
    comms = list(out["senateCommittees"].values()) + list(out["assemblyCommittees"].values())
    print(f"{path}: {len(out['people'])} legislators ({sum(1 for p in ppl if p['email'])} with email, "
          f"{sum(1 for p in ppl if p['phone'])} with a phone), {len(out['senateCommittees'])} Senate and "
          f"{len(out['assemblyCommittees'])} House committees ({sum(1 for c in comms if c['chair'])} with a chair), "
          f"leaders {sorted(out['leaders'])}")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else P.session_of(datetime.now(ZoneInfo(P.TIMEZONE)).year))
