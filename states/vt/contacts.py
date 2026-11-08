#!/usr/bin/env python3
"""Vermont's legislators, written as data/vt/contacts_<session>.json in the shape build_data.py reads.

- Who holds each seat now, with party and email: Open States' public-domain list of current legislators
  (data.openstates.org/people/current/vt.csv; the last copy when the download fails). Its party for the Progressives is
  "Democratic/Progressive" (they run on both lines), shown as written; the balance of power counts them with the
  Democrats.
- Ids, phones: LegiScan's person record for the same house and name (CC BY 4.0; "id" is LegiScan's people_id, which the
  roll calls use). Many members list the Sergeant at Arms' shared State House line, (802) 828-2228, as their capitol
  phone: it's shown, since it's how the State House takes messages for members.
- Seats: Vermont's districts have names, numbered alphabetically in data/vt/district_names.json (states/vt/towns.py).
  Most districts elect more than one member (Senate districts one to three, House districts one or two), so each member
  is "S:4a", "S:4b", "S:4c" or "H:37a", "H:37b" (New Jersey's scheme), in the order of their names.
- Committees: none. Neither LegiScan nor Open States has committee members or chairs, and the Legislature's site
  asks automated readers not to read it.
- Leaders: P.LEADERS (the Speaker and the President pro tempore), for the current session only.
Usage: python3 states/vt/contacts.py [session]
"""
import csv, json, os, re, sys, time, urllib.request
from datetime import datetime
from zoneinfo import ZoneInfo

HERE = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
sys.path.insert(0, HERE)
from fetch_contacts import name_key
from states import legiscan_convert as L
from states.vt import profile as P

PEOPLE = "https://data.openstates.org/people/current/vt.csv"
AGENT = "statebilltracker.org (a nonprofit bill tracker; contact via github.com/judithhubbard)"
OFFICE = "State House, 115 State Street, Montpelier"


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


def norm(d):
    """District names alike: "Chittenden South East", "Chittenden-Southeast" -> "chittendensoutheast"."""
    return re.sub(r"[^a-z0-9]", "", (d or "").lower().replace("south east", "southeast"))


def build(session):
    folder = L.folders(P.DATA)[session]
    ls = [p for p in L.people(folder).values() if L.person_house(p)]
    names = json.load(open(P.DISTRICT_NAMES_PATH))
    number = {h: {norm(n): int(i) for i, n in names[h].items()} for h in names}
    now = session >= P.session_of(datetime.now(ZoneInfo(P.TIMEZONE)).year)
    rows = []
    for o in open_states():
        h = "S" if o["current_chamber"] == "upper" else "H"
        d = number[h].get(norm(o.get("current_district")))
        if not d:
            print("unknown district:", h, o.get("current_district"), o.get("name"))
            continue
        rows.append((h, d, o))
    rows.sort(key=lambda x: (x[0], x[1], name_key(x[2]["name"]).split()[-1]))
    people, seen = {}, {}
    for h, d, o in rows:
        k = seen[(h, d)] = seen.get((h, d), -1) + 1
        sid = f"{h}:{d}{'abcdefgh'[k]}"
        same = [x for x in ls if L.person_house(x) == h and last(x["name"]) == last(o["name"])]
        if len(same) > 1:
            same = [x for x in same if name_key(x["name"]).split()[0] == name_key(o["name"]).split()[0]] or same[:1]
        p = same[0] if same else {}
        social = (p.get("bio") or {}).get("social") or {}
        tel = phone(o.get("capitol_voice")) or phone(social.get("capitol_phone"))
        party = o.get("current_party") or {"D": "Democratic", "R": "Republican", "I": "Independent"}.get(p.get("party"), "")
        people[sid] = {
            "name": L.text(o["name"]), "key": name_key(o["name"]), "id": str(p.get("people_id") or ""), "party": party,
            "email": o.get("email") or social.get("email") or None, "form": None,
            "phone": tel, "phones": [["State House", tel]] if tel else [],
            "url": next((u for u in reversed((o.get("links") or "").split(";")) if "legislature.vermont.gov/people/single" in u), None)
                   or social.get("biography") or None,
            "image": None, "office": OFFICE if tel else None, "position": None, "places": names[h][str(d)],
            "dataName": L.text(p.get("name") or o["name"]),
        }
    # A line many members share is the State House's message line (the House's Sergeant at Arms, the Senate's office).
    shared = {t for t in (x["phone"] for x in people.values()) if t and sum(1 for y in people.values() if y["phone"] == t) > 5}
    for x in people.values():
        if x["phone"] in shared:
            x["phones"] = [["State House (messages)", x["phone"]]]
    leaders = {}
    for h, (name, role, _) in (P.LEADERS.items() if now else ()):
        hit = next((x for sid, x in people.items() if sid[0] == h and last(x["name"]) == last(name)), None)
        if hit:
            hit["position"] = role
            leaders[h] = {"name": hit["name"], "role": role}
    return {"session": session, "fetched": datetime.now(ZoneInfo(P.TIMEZONE)).strftime("%Y-%m-%d %H:%M"),
            "people": people, "since": {}, "senateCommittees": {}, "assemblyCommittees": {},
            "leaders": leaders, "assemblyMembers": {}, "kept": []}


def main(session):
    out = build(session)
    if len(out["people"]) < 150:
        raise SystemExit(f"only {len(out['people'])} legislators; kept the last contacts")
    path = os.path.join(P.DATA, f"contacts_{session}.json")
    json.dump(out, open(path, "w"), indent=1, ensure_ascii=False)
    ppl = out["people"].values()
    print(f"{path}: {len(out['people'])} legislators ({sum(1 for p in ppl if p['email'])} with email, "
          f"{sum(1 for p in ppl if p['phone'])} with a phone, {sum(1 for p in ppl if p['id'])} matched to LegiScan), "
          f"leaders {sorted(out['leaders'])}")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else max(L.folders(P.DATA)))
