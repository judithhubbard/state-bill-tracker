#!/usr/bin/env python3
"""Oklahoma's legislators, written as data/ok/contacts_<session>.json in the shape build_data.py reads.

- Who holds each seat now, with party and email: Open States' public-domain list of current legislators
  (data.openstates.org/people/current/ok.csv; the last copy when the download fails). LegiScan's people for the session
  (data/ok/legiscan/<id>/people/, CC BY 4.0) include members who left; Open States says who serves now.
- Ids, phones and offices: LegiScan's person record for the same seat and last name ("id" is LegiScan's people_id, which
  the roll calls use; phones are each member's Capitol line, offices their State Capitol room). A member LegiScan
  doesn't list yet keeps Open States' email with no phone.
- Seat ids "S:18", "H:75" (one member a district in each house: 48 Senate and 101 House districts, which differ).
- Committees: none. Neither LegiScan nor Open States has committee members or chairs, and the Legislature's site
  (oklegislature.gov) asks automated readers not to read it.
- Leaders: P.LEADERS (the Speaker and the Senate's President Pro Tempore), for the current session only.
Usage: python3 states/ok/contacts.py [session]
"""
import csv, json, os, re, sys, time, urllib.request
from datetime import datetime
from zoneinfo import ZoneInfo

HERE = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
sys.path.insert(0, HERE)
from fetch_contacts import name_key
from states import legiscan_convert as L
from states.ok import profile as P

PEOPLE = "https://data.openstates.org/people/current/ok.csv"
AGENT = "statebilltracker.org (a nonprofit bill tracker; contact via github.com/judithhubbard)"
OFFICE = "State Capitol, 2300 N. Lincoln Blvd., Oklahoma City"


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


def room(p):
    """"2300 N. Lincoln Blvd., Room 406" -> "State Capitol, Room 406, Oklahoma City"."""
    a = L.text(((p.get("bio") or {}).get("capitol_address") or {}).get("address1"))
    m = re.search(r"\b(?:Room|Rm\.?)\s*(\w+)", a)
    return f"State Capitol, Room {m.group(1)}, Oklahoma City" if m else OFFICE


def build(session):
    from states.ok.convert import RULES
    folder = RULES.session_folders()[session]
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
        # The same last name, else a shared name word ("Arturo Alonso" is LegiScan's "Arturo Alonso-Sandoval").
        words = lambda n: set(name_key(n).replace("-", " ").split()) - {"jr", "sr", "ii", "iii", "iv"}
        p = next((x for x in by_seat.get(sid, []) if last(x["name"]) == last(o["name"])), None) or \
            next((x for x in by_seat.get(sid, []) if len(words(x["name"]) & words(o["name"])) >= 2), None) or {}
        social = (p.get("bio") or {}).get("social") or {}
        tel = phone(social.get("capitol_phone"))
        party = o.get("current_party") or {"D": "Democratic", "R": "Republican"}.get(p.get("party"), "")
        people[sid] = {
            "name": L.text(o["name"]), "key": name_key(o["name"]), "id": str(p.get("people_id") or ""), "party": party,
            "email": o.get("email") or social.get("email") or None, "form": None,
            "phone": tel, "phones": [["Capitol", tel]] if tel else [],
            "url": next((u for u in (o.get("links") or "").split(";") if re.search(r"okhouse\.gov|oksenate\.gov", u)), None)
                   or social.get("biography") or None,
            "image": None, "office": room(p) if tel else None, "position": None, "places": "",
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
    if len(out["people"]) < 140:
        raise SystemExit(f"only {len(out['people'])} legislators; kept the last contacts")
    path = os.path.join(P.DATA, f"contacts_{session}.json")
    json.dump(out, open(path, "w"), indent=1, ensure_ascii=False)
    ppl = out["people"].values()
    print(f"{path}: {len(out['people'])} legislators ({sum(1 for p in ppl if p['email'])} with email, "
          f"{sum(1 for p in ppl if p['phone'])} with a phone, {sum(1 for p in ppl if p['id'])} matched to LegiScan), "
          f"leaders {sorted(out['leaders'])}")


if __name__ == "__main__":
    from states.ok.convert import RULES
    main(int(sys.argv[1]) if len(sys.argv) > 1 else max(RULES.session_folders()))
