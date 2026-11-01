#!/usr/bin/env python3
"""Arizona's legislators, written as data/az/contacts_<session>.json in the shape build_data.py reads, from Open States'
public-domain people file (data/az/openstates_people.csv, saved by states/az/fetch.py; the owner's decision 2026-10-31)
and committees from data/az/committees.json when azleg.gov's committee pages have been read (one request every two
minutes, its robots.txt crawl delay).

Arizona has 30 districts, each electing one senator and two representatives. As in New Jersey, a district's senator and
both representatives are its legislators: seat ids "S:12", "H:12a", "H:12b". "id" is the Open States person id the
votes use. Usage: python3 states/az/contacts.py [session]
"""
import csv, json, os, re, sys
from collections import defaultdict
from datetime import datetime
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
from fetch_contacts import committee_key, name_key
from states.az import profile as P


def phone(p):
    d = re.sub(r"\D", "", p or "")
    return f"({d[:3]}) {d[3:6]}-{d[6:10]}" if len(d) == 10 else ""


def roster():
    """Name key -> (room, phone) from azleg.gov's member rosters (data/az/azleg/roster_H.html, roster_S.html)."""
    out = {}
    for h in "HS":
        try:
            page = open(os.path.join(P.DATA, "azleg", f"roster_{h}.html"), encoding="utf-8").read()
        except OSError:
            continue
        for name, room, ph in re.findall(r'class="roster-tooltip">([^<]+)<strong>.*?</td>.*?</td>.*?</td>.*?</td><td>([^<]*)</td><td>([^<]*)</td>', page, re.S):
            out[(h, name_key(name))] = (room.strip(), phone(ph))
            out.setdefault((h, "last:" + name_key(name).split()[-1]), []).append((room.strip(), phone(ph)))
    return out


def build(session):
    rows = list(csv.DictReader(open(os.path.join(P.DATA, "openstates_people.csv"))))
    by_district = defaultdict(list)
    for r in rows:
        if not r["current_district"].isdigit():
            continue
        h = "S" if r["current_chamber"] == "upper" else "H"
        by_district[(h, int(r["current_district"]))].append(r)
    rooms = roster()
    people = {}
    for (h, d), rs in sorted(by_district.items()):
        for i, r in enumerate(sorted(rs, key=lambda r: r["name"])):
            sid = f"S:{d}" if h == "S" else f"H:{d}{'abc'[i]}"
            by_last = rooms.get((h, "last:" + name_key(r["name"]).split()[-1]), [])
            room, ph = rooms.get((h, name_key(r["name"]))) or (by_last[0] if len(by_last) == 1 else ("", phone(r.get("capitol_voice"))))
            links = [u for u in (r.get("links") or "").split(";") if u]
            people[sid] = {
                "name": r["name"], "key": name_key(r["name"]), "id": r["id"],
                "party": {"Democratic": "Democratic", "Republican": "Republican"}.get(r["current_party"], r["current_party"]),
                "email": r.get("email") or None, "form": None, "phone": ph or None, "phones": [["Phoenix", ph]] if ph else [],
                "url": links[0] if links else None, "image": r.get("image") or None, "office": room, "position": None,
                "places": f"District {d}", "dataName": r["name"],
            }
    by_name = {p["key"]: p["name"] for p in people.values()}
    comms = {"S": {}, "H": {}}
    try:
        for c in json.load(open(os.path.join(P.DATA, "committees.json"))):
            h = "S" if c.get("house") == "S" else "H"
            names = sorted({by_name.get(name_key(m), m) for m in c.get("members") or []})
            chair = by_name.get(name_key(c.get("chair") or ""), c.get("chair"))
            comms[h][committee_key(c["name"])] = {"name": c["name"], "chair": chair, "meets": c.get("meets"), "members": names}
    except (OSError, ValueError):
        pass
    leaders = {}
    for h, (name, role, _) in P.LEADERS.items():
        hit = next((p for sid, p in people.items() if sid[0] == h and p["key"] == name_key(name)), None)
        if hit:
            hit["position"] = role
            leaders[h] = {"name": hit["name"], "role": role}
    return {"session": session, "fetched": datetime.now(ZoneInfo(P.TIMEZONE)).strftime("%Y-%m-%d %H:%M"),
            "people": people, "since": {}, "senateCommittees": comms["S"], "assemblyCommittees": comms["H"],
            "leaders": leaders, "assemblyMembers": {}, "kept": []}


def main(session):
    out = build(session)
    if len(out["people"]) < 80:
        raise SystemExit(f"only {len(out['people'])} legislators; kept the last contacts")
    path = os.path.join(P.DATA, f"contacts_{session}.json")
    json.dump(out, open(path, "w"), indent=1, ensure_ascii=False)
    ppl = out["people"].values()
    print(f"{path}: {len(out['people'])} legislators ({sum(1 for p in ppl if p['email'])} with email, "
          f"{sum(1 for p in ppl if p['phone'])} with a phone), {len(out['senateCommittees'])} Senate and "
          f"{len(out['assemblyCommittees'])} House committees, leaders {sorted(out['leaders'])}")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else P.session_of(datetime.now(ZoneInfo(P.TIMEZONE)).year))
