#!/usr/bin/env python3
"""Michigan's legislators, written as data/mi/contacts_<session>.json in the shape build_data.py reads, from the
Legislature's web service (https://legislature.mi.gov/litwebservices/litwebservices.asmx): GetLegislatorInformation
(names, districts, emails, Capitol phones) and GetLegislatorInformationBySession (each member's website). Party comes
from the website: the caucuses host Democrats' pages (housedems.com, senatedems.com) and Republicans' (gophouse.org, or
"rep..."/"senator..." sites); a member whose site says neither gets the party from Open States' public-domain file.
Committees aren't in the web service, so the file has none yet. Seat ids "S:15", "H:47".
Usage: python3 states/mi/contacts.py [session]
"""
import csv, html, io, json, os, re, sys, time, urllib.request
from datetime import datetime
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
from fetch_contacts import name_key
from states.mi import profile as P

SERVICE = "https://legislature.mi.gov/litwebservices/litwebservices.asmx"
NS = "http://www.legislature.mi.gov/LITWebServices/"
PEOPLE = "https://data.openstates.org/people/current/mi.csv"
AGENT = "statebilltracker.org (a nonprofit bill tracker; contact via github.com/judithhubbard)"


def call(op, body=""):
    env = (f'<?xml version="1.0" encoding="utf-8"?><soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">'
           f'<soap:Body><{op} xmlns="{NS}">{body}</{op}></soap:Body></soap:Envelope>').encode()
    for attempt in range(3):
        try:
            req = urllib.request.Request(SERVICE, data=env, headers={"User-Agent": AGENT, "Content-Type": "text/xml; charset=utf-8",
                                                                      "SOAPAction": f'"{NS}{op}"'})
            with urllib.request.urlopen(req, timeout=120) as r:
                t = html.unescape(r.read().decode("utf-8", "replace"))
            m = re.search(rf"<{op}Result>(.*)</{op}Result>", t, re.S)
            return json.loads(m.group(1), strict=False) if m else []
        except Exception:
            time.sleep(10 * (attempt + 1))
    return []


def phone(p):
    d = re.sub(r"\D", "", p or "")
    return f"({d[:3]}) {d[3:6]}-{d[6:10]}" if len(d) == 10 else ""


def build(session):
    info = call("GetLegislatorInformation")
    sites = {(x["Chamber"][:1], int(x["District"])): text(x.get("Website")) for x in call("GetLegislatorInformationBySession", f"<Session>{session}-{session + 1}</Session>")}
    try:
        body = urllib.request.urlopen(urllib.request.Request(PEOPLE, headers={"User-Agent": AGENT}), timeout=60).read()
        open(os.path.join(P.DATA, "openstates_people.csv"), "wb").write(body)
    except Exception:
        pass
    try:
        rows = list(csv.DictReader(open(os.path.join(P.DATA, "openstates_people.csv"))))
    except OSError:
        rows = []
    os_party = {("S" if r["current_chamber"] == "upper" else "H", int(r["current_district"])): r["current_party"] for r in rows if r["current_district"].isdigit()}
    people = {}
    for x in info:
        h = "S" if x.get("Chamber") == "Senate" else "H"
        if not str(x.get("District") or "").isdigit():
            continue
        d = int(x["District"])
        name = text(f"{x.get('FirstName', '')} {x.get('LastName', '')}")
        site = sites.get((h, d), "")
        party = ("Democratic" if re.search(r"dems\.com", site) else "Republican" if re.search(r"gophouse|//(?:www\.)?(?:rep|senator)\w+\.com", site)
                 else {"Democratic": "Democratic", "Republican": "Republican"}.get(os_party.get((h, d)), ""))
        ph = phone(x.get("Phone"))
        people[f"{h}:{d}"] = {
            "name": name, "key": name_key(name), "id": None, "party": party, "email": x.get("Email") or None, "form": None,
            "phone": ph or None, "phones": [["Lansing", ph]] if ph else [], "url": site.strip() or None, "image": None,
            "office": "", "position": None, "places": "", "dataName": name,
        }
    leaders = {}
    for h, (name, role, _) in P.LEADERS.items():
        hit = next((p for sid, p in people.items() if sid[0] == h and p["key"] == name_key(name)), None)
        if hit:
            hit["position"] = role
            leaders[h] = {"name": hit["name"], "role": role}
    return {"session": session, "fetched": datetime.now(ZoneInfo(P.TIMEZONE)).strftime("%Y-%m-%d %H:%M ET"),
            "people": people, "since": {}, "senateCommittees": {}, "assemblyCommittees": {},
            "leaders": leaders, "assemblyMembers": {}, "kept": []}


def text(x):
    return re.sub(r"\s+", " ", x or "").strip()


def main(session):
    out = build(session)
    if len(out["people"]) < 140:
        raise SystemExit(f"only {len(out['people'])} legislators; kept the last contacts")
    path = os.path.join(P.DATA, f"contacts_{session}.json")
    json.dump(out, open(path, "w"), indent=1, ensure_ascii=False)
    ppl = out["people"].values()
    print(f"{path}: {len(out['people'])} legislators ({sum(1 for p in ppl if p['email'])} with email, "
          f"{sum(1 for p in ppl if p['phone'])} with a phone, {sum(1 for p in ppl if p['party'])} with party), leaders {sorted(out['leaders'])}")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else P.session_of(datetime.now(ZoneInfo(P.TIMEZONE)).year))
