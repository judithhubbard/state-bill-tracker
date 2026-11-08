#!/usr/bin/env python3
"""Indiana's legislators and committees, written as data/in/contacts_<year>.json in the shape build_data.py reads.

- Members, parties, districts and committees: data/in/<year>/legislators.json and committees.json (states/in/fetch.py:
  the General Assembly's API; each standing committee's chair, vice chair, ranking minority member and members). Seat
  ids "S:26", "H:18"; "id" is the API's member slug ("david_abbott_1").
- Emails and links to each member's caucus page: Open States' public-domain file (data.openstates.org), since the API has
  no emails, phones or offices (as for Ohio and Pennsylvania); matched by house and district, when the last name agrees.
- Phones: the caucuses' shared lines (House Republicans 800-382-9841, House Democrats 800-382-9842; the Senate's
  317-232-9400 and 800-382-9467), from the caucuses' own sites (checked 2026-11-08); members have no direct lines there.
- Leaders: P.LEADERS and P.POSITIONS (the API has none), for the current year only.
Usage: python3 states/in/contacts.py [year]
"""
import csv, importlib, json, os, re, sys, time, urllib.request
from datetime import datetime
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
from fetch_contacts import committee_key, name_key

P = importlib.import_module("states.in.profile")  # "in" is a Python keyword
C = importlib.import_module("states.in.convert")

PEOPLE = "https://data.openstates.org/people/current/in.csv"
AGENT = "statebilltracker.org (a nonprofit bill tracker; contact via github.com/judithhubbard)"
PHONES = {("H", "R"): [["Caucus office", "(800) 382-9841"]], ("H", "D"): [["Caucus office", "(800) 382-9842"]],
          ("S", "R"): [["Senate", "(317) 232-9400"], ["Toll-free", "(800) 382-9467"]],
          ("S", "D"): [["Senate", "(317) 232-9400"], ["Toll-free", "(800) 382-9467"]]}


def get(url):
    for attempt in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": AGENT}), timeout=120) as r:
                return r.read()
        except Exception:
            time.sleep(10 * (attempt + 1))
    return None


def open_states():
    """Open States' current members, (house, district) -> row; the last copy when the download fails."""
    path = os.path.join(P.DATA, "openstates_people.csv")
    body = get(PEOPLE)
    if body and body.startswith(b"id,"):
        with open(path, "wb") as f:
            f.write(body)
    try:
        rows = list(csv.DictReader(open(path, encoding="utf-8")))
    except OSError:
        rows = []
    return {("S" if r["current_chamber"] == "upper" else "H", int(r["current_district"])): r
            for r in rows if (r.get("current_district") or "").isdigit()}


def name_of(m):
    return C.text(f"{m.get('firstName') or m.get('firstname') or ''} {m.get('lastName') or m.get('lastname') or ''}")


def build(year):
    folder = os.path.join(P.DATA, str(year))
    now = year >= P.session_of(datetime.now(ZoneInfo(P.TIMEZONE)).year)  # leaders are named for the current year only
    os_by = open_states()
    people, by_link = {}, {}
    for m in json.load(open(os.path.join(folder, "legislators.json"))):
        h = {"House": "H", "Senate": "S"}.get((m.get("chamber") or {}).get("name")) or \
            ("S" if (m.get("position_title") or "").startswith("Senator") else "H")
        d = re.search(r"(\d+)$", m.get("district") or "")
        if not d:
            continue
        sid, name = f"{h}:{int(d.group(1))}", name_of(m)
        party = m.get("party") or m.get("partyid") or ""
        o = os_by.get((h, int(d.group(1))))
        if o and name_key(o["name"]).split()[-1:] != name_key(name).split()[-1:]:
            o = None  # Open States still has the seat's last holder
        links = [u for u in ((o or {}).get("links") or "").split(";") if u and "iga.in.gov" not in u]
        slug = (m.get("link") or "").rstrip("/").split("/")[-1]
        people[sid] = {
            "name": name, "key": name_key(name), "id": slug, "party": party,
            "email": (o or {}).get("email") or None, "form": None,
            "phone": (PHONES.get((h, party[:1])) or [[None, None]])[0][1], "phones": PHONES.get((h, party[:1]), []),
            "url": links[-1] if links else f"https://iga.in.gov/legislative/{year}/legislators/legislator_{slug}",
            "image": None, "office": "200 W. Washington St., Indianapolis", "position": P.POSITIONS.get((h, name)) if now else None,
            "places": "", "dataName": name,
        }
        by_link[m.get("link")] = sid
    comms = {"S": {}, "H": {}}
    for c in json.load(open(os.path.join(folder, "committees.json"))):
        h = {"House": "H", "Senate": "S"}.get(((c.get("chamber") or [{}])[0] or {}).get("name"))
        if not h or not c.get("name"):
            continue
        name = C.committee(c["name"])
        who = lambda k: next((people[by_link[x["link"]]]["name"] for x in c.get(k) or [] if x.get("link") in by_link), None)
        members = sorted({people[by_link[x["link"]]]["name"] for x in c.get("members") or [] if x.get("link") in by_link})
        comms[h][committee_key(name)] = {"name": name, "chair": who("chair"), "viceChair": who("viceChair"),
                                         "rankingMinority": who("rankingMinMember"), "meets": None, "members": members}
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
    if len(out["people"]) < 140:
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
