#!/usr/bin/env python3
"""Rhode Island's legislators, written as data/ri/contacts_<session>.json in the shape build_data.py reads.

- Who holds each seat now, with party and email: Open States' public-domain list of current legislators
  (data.openstates.org/people/current/ri.csv; the last copy when the download fails). LegiScan's people for the session
  (data/ri/legiscan/<id>/people/, CC BY 4.0) include members who left; Open States says who serves now.
- Ids, phones and offices: LegiScan's person record for the same seat and last name ("id" is LegiScan's people_id, which
  the roll calls use; phones are each member's State House line, and the State House address). A member LegiScan
  doesn't list yet keeps Open States' email with no phone.
- Seat ids "S:18" (38 Senate districts), "H:75" (75 House districts); one member a district, the two houses' districts
  drawn separately.
- Committees: none. Neither LegiScan nor Open States has committee members or chairs, and the General Assembly's site
  (rilegislature.gov) asks automated readers not to read it.
- Leaders: P.LEADERS (the Speakers), for the current session only.
Usage: python3 states/ri/contacts.py [session]
"""
import csv, json, os, re, sys, time, urllib.request
from datetime import datetime
from zoneinfo import ZoneInfo

HERE = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
sys.path.insert(0, HERE)
from fetch_contacts import name_key
from states import legiscan_convert as L
from states.ri import profile as P

PEOPLE = "https://data.openstates.org/people/current/ri.csv"
AGENT = "statebilltracker.org (a nonprofit bill tracker; contact via github.com/judithhubbard)"
OFFICE = "State House, 82 Smith Street, Providence"


def get(url):
    for attempt in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": AGENT}), timeout=120) as r:
                return r.read()
        except Exception:
            time.sleep(10 * (attempt + 1))
    return None


def open_states():
    path = os.path.join(P.DATA, "openstates_people.csv")
    body = get(PEOPLE)
    if body and body.startswith(b"id,"):
        os.makedirs(P.DATA, exist_ok=True)
        with open(path, "wb") as f:
            f.write(body)
    try:
        return list(csv.DictReader(open(path, encoding="utf-8")))
    except OSError:
        return []


def last(name):
    parts = [w for w in name_key(name).split() if w not in ("jr", "sr", "ii", "iii", "iv")]
    return parts[-1] if parts else ""


def phone(x):
    d = re.sub(r"\D", "", x or "")
    return f"({d[:3]}) {d[3:6]}-{d[6:10]}" if len(d) == 10 else None


def build(session):
    folder = L.folders(P.DATA)[session]
    ls = L.people(folder)
    by_seat = {}
    for p in ls.values():
        h, d = L.person_house(p), L.district_of(p)
        if h and d:
            by_seat.setdefault(f"{h}:{d}", []).append(p)
    now = session >= P.session_of(datetime.now(ZoneInfo(P.TIMEZONE)).year)
    people = {}
    for o in open_states():
        if not (o.get("current_district") or "").isdigit():
            continue
        h = "S" if o["current_chamber"] == "upper" else "H"
        sid = f"{h}:{int(o['current_district'])}"
        p = next((x for x in by_seat.get(sid, []) if last(x["name"]) == last(o["name"])), None) or {}
        social = (p.get("bio") or {}).get("social") or {}
        tel = phone(social.get("capitol_phone"))
        party = o.get("current_party") or {"D": "Democratic", "R": "Republican"}.get(p.get("party"), "")
        people[sid] = {
            "name": L.text(o["name"]), "key": name_key(o["name"]), "id": str(p.get("people_id") or ""), "party": party,
            "email": o.get("email") or social.get("email") or None, "form": None,
            "phone": tel, "phones": [["Capitol", tel]] if tel else [],
            # (Open States' links can include another member's page: LegiScan's biography link first.)
            "url": social.get("biography") or next((u for u in (o.get("links") or "").split(";")
                                                    if "rilegislature.gov" in u and last(o["name"]) in u.lower()), None),
            "image": None, "office": OFFICE if tel else None, "position": None, "places": "",
            "dataName": L.text(p.get("name") or o["name"]),
        }
    leaders = {}
    for h, (name, role, _) in (P.LEADERS.items() if now else ()):
        hit = next((x for sid, x in people.items() if sid[0] == h and x["key"] == name_key(name)), None)
        if hit:
            hit["position"] = role
            leaders[h] = {"name": hit["name"], "role": role}
    return {"session": session, "fetched": datetime.now(ZoneInfo(P.TIMEZONE)).strftime("%Y-%m-%d %H:%M"),
            "people": people, "since": {}, "senateCommittees": {}, "assemblyCommittees": {},
            "leaders": leaders, "assemblyMembers": {}, "kept": []}


def main(session):
    out = build(session)
    if len(out["people"]) < 100:
        raise SystemExit(f"only {len(out['people'])} legislators; kept the last contacts")
    path = os.path.join(P.DATA, f"contacts_{session}.json")
    json.dump(out, open(path, "w"), indent=1, ensure_ascii=False)
    ppl = out["people"].values()
    print(f"{path}: {len(out['people'])} legislators ({sum(1 for p in ppl if p['email'])} with email, "
          f"{sum(1 for p in ppl if p['phone'])} with a phone, {sum(1 for p in ppl if p['id'])} matched to LegiScan), "
          f"leaders {sorted(out['leaders'])}")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else max(L.folders(P.DATA)))
