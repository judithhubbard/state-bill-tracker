#!/usr/bin/env python3
"""North Carolina's legislators and committees, written as data/nc/contacts_<session>.json in the shape build_data.py reads,
from data/nc/<session>/members.json and committees.json (states/nc/fetch.py: the General Assembly's member lists and
biographies, and each committee's page with its chairs). Emails: the General Assembly's pages hide them behind
Cloudflare's anti-collection script, so they come from Open States' public-domain file (data/nc/openstates_people.csv,
as for Pennsylvania), matched by chamber and district.

Seat ids "S:12", "H:96"; "id" is the member id the bills' sponsors use. A committee can have several co-chairs; the first
listed is "chair". Usage: python3 states/nc/contacts.py [session]
"""
import csv, json, os, re, sys, urllib.request
from datetime import datetime
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
from fetch_contacts import committee_key, name_key
from states.nc import profile as P

PEOPLE = "https://data.openstates.org/people/current/nc.csv"
AGENT = "statebilltracker.org (a nonprofit bill tracker; contact via github.com/judithhubbard)"
PARTY = {"D": "Democratic", "R": "Republican", "U": "Unaffiliated"}


def phone(p):
    d = re.sub(r"\D", "", p or "")
    return f"({d[:3]}) {d[3:6]}-{d[6:10]}" if len(d) == 10 else ""


def build(session):
    folder = os.path.join(P.DATA, str(session))
    try:
        body = urllib.request.urlopen(urllib.request.Request(PEOPLE, headers={"User-Agent": AGENT}), timeout=60).read()
        open(os.path.join(P.DATA, "openstates_people.csv"), "wb").write(body)
    except Exception:
        pass
    try:
        rows = list(csv.DictReader(open(os.path.join(P.DATA, "openstates_people.csv"))))
    except OSError:
        rows = []
    os_by = {("S" if r["current_chamber"] == "upper" else "H", int(r["current_district"])): r for r in rows if r["current_district"].isdigit()}
    people, by_id = {}, {}
    for m in json.load(open(os.path.join(folder, "members.json"))):
        # Members who left ("Resigned 10/31/25", "Died 3/2/26") stay on the list; the seat is their successor's.
        if not m.get("district") or re.search(r"Resigned|Died|Deceased|Expelled|Left", m.get("note") or ""):
            continue
        h = m["chamber"]
        sid = f"{h}:{int(m['district'])}"
        o = os_by.get((h, int(m["district"])))
        if o and name_key(o["name"]).split()[-1:] != name_key(m["name"]).split()[-1:]:
            o = None
        bio = m.get("bio") or {}
        ph = phone(m.get("phone") or bio.get("mainPhone"))
        people[sid] = {
            "name": m["name"], "key": name_key(m["name"]), "id": m["id"], "party": PARTY.get(m.get("party"), m.get("party") or ""),
            "email": (o or {}).get("email") or None, "form": None, "phone": ph or None, "phones": [["Raleigh", ph]] if ph else [],
            "url": f"https://www.ncleg.gov/Members/Biography/{h}/{m['id']}", "image": None, "office": m.get("office") or "",
            "position": None, "places": ", ".join(m.get("counties") or []), "dataName": m["name"],
        }
        by_id[str(m["id"])] = m["name"]
    comms = {"S": {}, "H": {}}
    try:
        pages = json.load(open(os.path.join(folder, "committees.json"))).get("pages") or []
    except (OSError, ValueError):
        pages = []
    for c in pages:
        h = "S" if (c.get("kind") or "").startswith("Senate") else "H" if (c.get("kind") or "").startswith("House") else None
        if not h:
            continue
        name = re.sub(r"^(?:House|Senate)\s+(?:Select\s+)?(?:Standing\s+)?(?:Committee on\s+)?", "", c.get("name") or "").strip()
        name = re.sub(r"^Rules(?:, Calendar,)? and Operations of the (?:Senate|House)$", "Rules", name, flags=re.I)
        ms = c.get("members") or []
        names = sorted({by_id[str(x.get("id"))] for x in ms if str(x.get("id")) in by_id})
        chairs = [by_id.get(str(x.get("id"))) for x in ms if re.match(r"(Senior )?Chairs?$", x.get("role") or "")]
        comms[h][committee_key(name)] = {"name": name, "chair": next((c_ for c_ in chairs if c_), None),
                                         "meets": re.sub(r"\s*DASHBOARD\b", "", c.get("schedule") or "").strip() or None,
                                         "members": names}
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
    if len(out["people"]) < 160:
        raise SystemExit(f"only {len(out['people'])} legislators; kept the last contacts")
    path = os.path.join(P.DATA, f"contacts_{session}.json")
    json.dump(out, open(path, "w"), indent=1, ensure_ascii=False)
    ppl = out["people"].values()
    comms = list(out["senateCommittees"].values()) + list(out["assemblyCommittees"].values())
    print(f"{path}: {len(out['people'])} legislators ({sum(1 for p in ppl if p['email'])} with email, "
          f"{sum(1 for p in ppl if p['phone'])} with a phone), {len(out['senateCommittees'])} Senate and "
          f"{len(out['assemblyCommittees'])} House committees ({sum(1 for c in comms if c['chair'])} with a chair), "
          f"leaders {sorted(out['leaders'])}")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else P.session_of(datetime.now(ZoneInfo(P.TIMEZONE)).year))
