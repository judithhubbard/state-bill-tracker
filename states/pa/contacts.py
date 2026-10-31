#!/usr/bin/env python3
"""Pennsylvania's legislators and committees, written as data/pa/contacts_<session>.json in the shape build_data.py reads.

- Members, parties, districts, offices and phones: the General Assembly's member feeds
  (https://www.palegis.us/{house,senate}/rss/session/members); committees and chairs: its committee assignment feeds
  (.../rss/committee/assignments). Seat ids "S:12", "H:19"; "id" is the member id the roll calls use.
- Emails and links to each member's own site: Open States' public-domain file (data.openstates.org), since the feeds
  have no emails and the Senate's pages build them with a script meant to stop collection (decided 2026-10-31, as for
  Ohio); matched by house and district.
Each committee has a majority and a minority chair; "chair" is the majority party's. Usage: python3 states/pa/contacts.py
"""
import csv, html, io, json, os, re, sys, time, urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
from fetch_contacts import committee_key, name_key
from states.pa import profile as P

SITE = "https://www.palegis.us"
PEOPLE = "https://data.openstates.org/people/current/pa.csv"
AGENT = "statebilltracker.org (a nonprofit bill tracker; contact via github.com/judithhubbard)"
NS = "{https://www.legis.state.pa.us/RSS}"
PARTY = {"D": "Democratic", "R": "Republican", "I": "Independent"}


def get(url):
    for attempt in range(3):
        time.sleep(1)
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": AGENT}), timeout=120) as r:
                return r.read()
        except Exception:
            time.sleep(10 * (attempt + 1))
    return None


def feed(path):
    body = get(SITE + path)
    return ET.fromstring(body).iter("item") if body else []


def proper(name):
    """"PATRICK J. HARKINS" -> "Patrick J. Harkins"; "MCCLINTON" -> "McClinton"."""
    n = re.sub(r"\b([A-Za-z])([A-Za-z']*)", lambda m: m.group(1).upper() + m.group(2).lower(), " ".join(name.split()))
    n = re.sub(r"\b(Ii|Iii|Iv)$", lambda m: m.group(1).upper(), n)
    return re.sub(r"\b(Mc|Mac(?=[a-z]{4}))([a-z])", lambda m: m.group(1) + m.group(2).upper(), re.sub(r"\bO'([a-z])", lambda m: "O'" + m.group(1).upper(), n))


def phone(p):
    d = re.sub(r"\D", "", p or "")
    return f"({d[:3]}) {d[3:6]}-{d[6:10]}" if len(d) == 10 else ""


def build(session):
    body = get(PEOPLE)
    if body:
        open(os.path.join(P.DATA, "openstates_people.csv"), "wb").write(body)
    try:
        rows = list(csv.DictReader(open(os.path.join(P.DATA, "openstates_people.csv"))))
    except OSError:
        rows = []
    os_by = {("S" if r["current_chamber"] == "upper" else "H", int(r["current_district"] or 0)): r for r in rows if r["current_district"].isdigit()}
    people, majority = {}, {}
    for h, house in (("S", "senate"), ("H", "house")):
        parties = []
        for it in feed(f"/{house}/rss/session/members"):
            f = lambda k: (it.findtext(NS + k) or "").strip()
            if f("Vacant") == "true" or not f("District").isdigit():
                continue
            d, name = int(f("District")), proper(it.findtext("title") or "")
            mid = re.search(r"memberId=(\d+)", it.findtext("link") or "")
            o = os_by.get((h, d))
            if o and name_key(o["name"]).split()[-1:] != name_key(name).split()[-1:]:
                o = None  # Open States still has the seat's last holder
            offices = [("Harrisburg", phone(f("CapitolAddress_Phone")))] + [
                (re.sub(r",.*", "", f(f"District_{i}_CityStateZip")), phone(f(f"District_{i}_Phone"))) for i in (1, 2, 3)]
            offices = [o_ for o_ in offices if o_[1]]
            links = [u for u in ((o or {}).get("links") or "").split(";") if u and "palegis" not in u]
            parties.append(f("Party"))
            people[f"{h}:{d}"] = {
                "name": name, "key": name_key(name), "id": int(mid.group(1)) if mid else None,
                "party": PARTY.get(f("Party"), f("Party")), "email": (o or {}).get("email") or None, "form": None,
                "phone": offices[0][1] if offices else None, "phones": [list(x) for x in dict.fromkeys(offices)],
                "url": it.findtext("link"), "image": f("ImageSrc") or None,
                "office": f"{f('CapitolAddress_Street1')}, Harrisburg".strip(", "), "position": None,
                "places": f("County"), "dataName": name,
            }
        majority[h] = max(set(parties), key=parties.count) if parties else ""
    by_id = {p["id"]: (sid, p) for sid, p in people.items()}
    comms = {"S": {}, "H": {}}
    for h, house in (("S", "senate"), ("H", "house")):
        for it in feed(f"/{house}/rss/committee/assignments"):
            mid = re.search(r"memberId=(\d+)", it.findtext("link") or "")
            hit = by_id.get(int(mid.group(1))) if mid else None
            if not hit:
                continue
            sid, p = hit
            for c in it.iter(NS + "Committee"):
                name = html.unescape(c.text or "").strip()
                entry = comms[h].setdefault(committee_key(name), {"name": name, "chair": None, "meets": None, "members": []})
                entry["members"].append(p["name"])
                if c.get("position") == "Chair" and p["party"][:1] == majority[h]:
                    entry["chair"] = p["name"]
    for c in comms["S"].values():
        c["members"].sort()
    for c in comms["H"].values():
        c["members"].sort()
    leaders = {}
    for h, (name, role, _) in P.LEADERS.items():
        hit = next((p for sid, p in people.items() if sid[0] == h and p["key"] == name_key(name)), None)
        if hit:
            hit["position"] = role
            leaders[h] = {"name": hit["name"], "role": role}
    return {"session": session, "fetched": datetime.now(ZoneInfo(P.TIMEZONE)).strftime("%Y-%m-%d %H:%M ET"),
            "people": people, "since": {}, "senateCommittees": comms["S"], "assemblyCommittees": comms["H"],
            "leaders": leaders, "assemblyMembers": {}, "kept": []}


def main(session):
    out = build(session)
    if len(out["people"]) < 240:
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
