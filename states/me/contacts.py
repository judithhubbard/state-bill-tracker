#!/usr/bin/env python3
"""Maine's legislators, written as data/me/contacts_<session>.json in the shape build_data.py reads.

- Who holds each seat now, with party and email: Open States' public-domain list of current legislators
  (data.openstates.org/people/current/me.csv; the last copy when the download fails). LegiScan's people for the session
  (data/me/legiscan/<id>/people/, CC BY 4.0) include members who left; Open States says who serves now.
- Ids, phones and offices: LegiScan's person record for the same seat and last name ("id" is LegiScan's people_id, which
  the roll calls use; phones are the numbers the Legislature lists for each member, often a home or cell phone, since
  Maine's legislators have no Capitol office lines). A member LegiScan doesn't list yet keeps Open States' email with no
  phone.
- Seat ids "S:18" (35 Senate districts), "H:75" (151 House districts; the two kinds differ). The tribal representatives
  (the Passamaquoddy Tribe's and the Houlton Band of Maliseet Indians') speak and sponsor bills but have no floor vote and
  no district, so they aren't seats here: "Where you live" can't name them, and their bills show their names.
- Committees: none. Neither LegiScan nor Open States has committee members or chairs, and the General Assembly's site
  (legislature.maine.gov) asks automated readers not to read it.
- Leaders: P.LEADERS (the Speakers), for the current session only.
Usage: python3 states/me/contacts.py [session]
"""
import csv, json, os, re, sys, time, urllib.request
from datetime import datetime
from zoneinfo import ZoneInfo

HERE = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
sys.path.insert(0, HERE)
from fetch_contacts import name_key
from states import legiscan_convert as L
from states.me import profile as P

PEOPLE = "https://data.openstates.org/people/current/me.csv"
AGENT = "statebilltracker.org (a nonprofit bill tracker; contact via github.com/judithhubbard)"
OFFICE = "State House, Augusta"
# Senators listed with their caucus office's shared line (Democrats 287-1515, Republicans 287-1505).
CAUCUS = {"(207) 287-1515", "(207) 287-1505"}


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
        cands = by_seat.get(sid, [])
        # The same last name, or the same first name (Tiffany Roberts is "Tiffany Roberts-Lovell" in LegiScan's list); never
        # a member who left (Kathy Javner's seat, H:29, is Nancy Theriault's now).
        p = next((x for x in cands if last(x["name"]) == last(o["name"]) or last(o["name"]) in name_key(x["name"]).split()
                  or last(o["name"]) in name_key(x["name"]).replace("-", " ").split()), None) or next((x for x in cands if name_key(x["name"]).split()[:1] == name_key(o["name"]).split()[:1]), None) or {}
        social = (p.get("bio") or {}).get("social") or {}
        tel = phone(social.get("capitol_phone"))
        party = o.get("current_party") or {"D": "Democratic", "R": "Republican"}.get(p.get("party"), "")
        people[sid] = {
            "name": L.text(o["name"]), "key": name_key(o["name"]), "id": str(p.get("people_id") or ""), "party": party,
            "email": o.get("email") or social.get("email") or None, "form": None,
            "phone": tel, "phones": [["Senate caucus office" if tel in CAUCUS else "Phone", tel]] if tel else [],
            "url": next((u for u in (o.get("links") or "").split(";") if "legislature.maine.gov" in u), None)
                   or social.get("biography") or None,
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
    if len(out["people"]) < 170:
        raise SystemExit(f"only {len(out['people'])} legislators; kept the last contacts")
    path = os.path.join(P.DATA, f"contacts_{session}.json")
    json.dump(out, open(path, "w"), indent=1, ensure_ascii=False)
    ppl = out["people"].values()
    print(f"{path}: {len(out['people'])} legislators ({sum(1 for p in ppl if p['email'])} with email, "
          f"{sum(1 for p in ppl if p['phone'])} with a phone, {sum(1 for p in ppl if p['id'])} matched to LegiScan), "
          f"leaders {sorted(out['leaders'])}")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else max(L.folders(P.DATA)))
