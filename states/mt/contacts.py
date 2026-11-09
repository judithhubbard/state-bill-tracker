#!/usr/bin/env python3
"""Montana's legislators and committees, written as data/mt/contacts_<session>.json in the shape build_data.py reads.

- Members, parties, districts, emails, leadership positions and committees (chairs and vice chairs): what
  states/mt/fetch.py downloads from the Legislature's API (data/mt/<session>/legislators.json and committees.json). The
  member list keeps one record per member, overwritten with their latest house and district (legislators elected to the
  Senate in 2026 show as senators already): convert.members() takes the house from the roll calls and P.SEAT_FIX. Seat
  ids "S:41", "H:82"; a seat held by two members in the session goes to the one serving now. 2023's archive has names,
  parties, districts and committees, but no emails.
- Phones: the API's are empty. The members' own numbers come from Open States' public-domain file
  (data.openstates.org/people/current/mt.csv; about a third list one), matched by the API's member id in its links (the
  last copy when the download fails), and every member gets the Legislature's session message line, (406) 444-4800
  (staff take messages for legislators while the Legislature meets; from the Legislature's and advocacy groups' guides,
  not checked by the owner).
- Leaders: the member list's positions, for the current Legislature only.
Usage: python3 states/mt/contacts.py [session]   (default: every session downloaded)
"""
import csv, json, os, re, sys, time, urllib.request
from datetime import date, datetime
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
from fetch_contacts import committee_key, name_key
from states.mt import convert as C
from states.mt import profile as P

PEOPLE = "https://data.openstates.org/people/current/mt.csv"
AGENT = "statebilltracker.org (a nonprofit bill tracker; contact via github.com/judithhubbard)"
MESSAGES = ["Capitol (session message line)", "(406) 444-4800"]
PARTY = {"R": "Republican", "D": "Democratic", "I": "Independent", "L": "Libertarian"}
POSITIONS = {"SPEAKER": "Speaker of the House", "PRESIDENT": "President of the Senate", "SPEAKER_PRO_TEMPOR": "Speaker Pro Tempore",
             "PRESIDENT_PRO_TEMPOR": "President Pro Tempore", "MAJORITY_LEADER": "Majority Leader",
             "MINORITY_LEADER": "Minority Leader", "MAJORITY_WHIP": "Majority Whip", "MINORITY_WHIP": "Minority Whip"}
# Committees bills aren't referred to.
NOT_STANDING = re.compile(r"Committee on Committees|Committee of the Whole|Ethics|Legislative Administration|Executive Branch Review|Rules")


def get(url):
    for attempt in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": AGENT}), timeout=120) as r:
                return r.read()
        except Exception:
            time.sleep(10 * (attempt + 1))
    return None


def open_states():
    """Open States' current members by the Legislature's member id (from their links); the last copy when the download fails."""
    path = os.path.join(P.DATA, "openstates_people.csv")
    body = get(PEOPLE)
    if body and body.startswith(b"id,"):
        with open(path, "wb") as f:
            f.write(body)
    try:
        rows = list(csv.DictReader(open(path, encoding="utf-8")))
    except OSError:
        rows = []
    out = {}
    for r in rows:
        m = re.search(r"legislators\.legmt\.gov/#/legislator/(\d+)", f"{r.get('links')};{r.get('sources')}")
        if m:
            out[int(m.group(1))] = r
    return out


def phone(x):
    d = re.sub(r"\D", "", x or "")
    if len(d) == 11 and d[0] == "1":
        d = d[1:]
    return f"({d[:3]}) {d[3:6]}-{d[6:]}" if len(d) == 10 else None


def build(session):
    today = datetime.now(ZoneInfo(P.TIMEZONE)).date()
    now = session >= P.session_of(today.year)  # positions are named for the current Legislature only
    ms = C.members(session)
    os_by = open_states() if not C.archive(session) else {}
    people, sid_of = {}, {}
    for mid, m in ms.items():
        if not m["seat"] or not m["current"]:
            continue
        o = os_by.get(mid) or {}
        if o and name_key(o.get("name", "")).split()[-1:] != name_key(m["name"]).split()[-1:]:
            o = {}
        if o and (o.get("current_district") or "").isdigit() and \
                ("S" if o.get("current_chamber") == "upper" else "H", int(o["current_district"])) != (m["house"], m["district"]):
            print(f"  {m['name']}: seat {m['seat']} here, {o.get('current_chamber')} {o.get('current_district')} at Open States", flush=True)
        phones = []
        for label, key in (("Phone", "district_voice"), ("Capitol", "capitol_voice")):
            ph = phone(o.get(key))
            if ph and ph not in [x[1] for x in phones]:
                phones.append([label, ph])
        if now:
            phones.append(MESSAGES)
        url = next((u for u in (o.get("links") or "").split(";") if "legmt.gov/legislators/" in u), None) or \
            (f"https://legislators.legmt.gov/#/legislator/{mid}" if not C.archive(session) else None)
        people[m["seat"]] = {
            "name": m["name"], "key": name_key(m["name"]), "id": mid, "party": PARTY.get(m["party"], m["party"] or None),
            "email": m["email"] or (o.get("email") or None), "form": None,
            "phone": phones[0][1] if phones else None, "phones": phones,
            "url": url, "image": o.get("image") or None, "office": "State Capitol, Helena" if now else None,
            "position": (POSITIONS.get(m["position"], m["position"]) if now and m["position"] else None),
            "places": "", "dataName": m["name"],
        }
        sid_of[mid] = m["seat"]
    comms = {"S": {}, "H": {}}
    if C.archive(session):
        for mid, raw in ((x["lawEntity"]["entityIdSequence"], x) for x in C.load(session, "legislators", []) or []):
            if mid not in sid_of:
                continue
            for a in raw.get("committeeAssignments") or []:
                c = a.get("committee") or {}
                h = c.get("houseCode")
                name = C.comm_name(c.get("committeeName"))
                if h not in comms or c.get("committeeTypeName") != "ST" or NOT_STANDING.search(name):
                    continue
                e = comms[h].setdefault(committee_key(name), {"name": name, "chair": None, "coChairs": [], "viceChair": None,
                                                             "meets": None, "members": []})
                who = people[sid_of[mid]]["name"]
                code = (a.get("committeeAssignmentType") or {}).get("assignmentCode")
                if code == "CH":
                    e["chair"] = who
                elif code == "VC" and not e["viceChair"]:
                    e["viceChair"] = who
                e["members"] = sorted(set(e["members"]) | {who})
    else:
        for c in C.load(session, "committees", []) or []:
            code = (c.get("committeeDetails") or {}).get("committeeCode") or {}
            h = {"HOUSE": "H", "SENATE": "S"}.get(c.get("chamber"))
            name = C.comm_name(code.get("name"))
            if not h or (code.get("committeeType") or {}).get("code") != "ST" or NOT_STANDING.search(name):
                continue
            ship = [x for x in c.get("memberships") or [] if x.get("legislatorId") in sid_of and (x.get("endDate") or "9999") >= today.isoformat()]
            ship = ship or [x for x in c.get("memberships") or [] if x.get("legislatorId") in sid_of]
            names = lambda t: [people[sid_of[x["legislatorId"]]]["name"] for x in ship if (x.get("type") or {}).get("code") == t]
            chairs, vice = names("CH"), names("VC")
            comms[h][committee_key(name)] = {
                "name": name, "chair": chairs[0] if chairs else None, "coChairs": chairs[1:], "viceChair": vice[0] if vice else None,
                "meets": None, "members": sorted({people[sid_of[x["legislatorId"]]]["name"] for x in ship})}
    leaders = {}
    if now:
        for h, (name, role, _) in P.LEADERS.items():
            hit = next((p for sid, p in people.items() if sid[0] == h and p["key"] == name_key(name)), None)
            if hit:
                leaders[h] = {"name": hit["name"], "role": role}
    return {"session": session, "fetched": datetime.now(ZoneInfo(P.TIMEZONE)).strftime("%Y-%m-%d %H:%M"),
            "people": people, "since": {}, "senateCommittees": comms["S"], "assemblyCommittees": comms["H"],
            "leaders": leaders, "assemblyMembers": {}, "kept": []}


def main(session):
    out = build(session)
    if len(out["people"]) < 140:
        raise SystemExit(f"{session}: only {len(out['people'])} legislators; kept the last contacts")
    path = os.path.join(P.DATA, f"contacts_{session}.json")
    json.dump(out, open(path, "w"), indent=1, ensure_ascii=False)
    ppl = out["people"].values()
    comms = list(out["senateCommittees"].values()) + list(out["assemblyCommittees"].values())
    print(f"{path}: {len(out['people'])} legislators ({sum(1 for p in ppl if p['email'])} with email, "
          f"{sum(1 for p in ppl if len(p['phones']) > (1 if p['phones'] and p['phones'][-1] == MESSAGES else 0))} with their own phone), "
          f"{len(out['senateCommittees'])} Senate and {len(out['assemblyCommittees'])} House committees "
          f"({sum(1 for c in comms if c['chair'])} with a chair), leaders {sorted(out['leaders'])}")


if __name__ == "__main__":
    for s in ([int(sys.argv[1])] if len(sys.argv) > 1 else C.sessions()):
        main(s)
