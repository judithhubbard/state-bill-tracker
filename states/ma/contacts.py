#!/usr/bin/env python3
"""Massachusetts's legislators and committees, from the Legislature's API (each member's record: district, party,
email, phone, room, committees; each committee's chairs), written as data/ma/contacts_<session>.json in the shape
build_data.py reads. Members' districts are names ("8th Middlesex"); each is given the Census seat number from
data/ma/district_names.json (states/ma/towns.py), matched with "&"/"and", hyphens and commas made alike. Seat ids
"S:7", "H:24". Usage: python3 states/ma/contacts.py [session]
"""
import json, os, re, sys, time, urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
from fetch_contacts import committee_key, name_key

API = "https://malegislature.gov/api"
DATA = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "ma"))
AGENT = "statebilltracker.org (a nonprofit bill tracker; contact via github.com/judithhubbard)"
PARTY = {"Democrat": "Democratic", "Republican": "Republican", "Unenrolled": "Independent"}
ORDINAL = {"first": "1st", "second": "2nd", "third": "3rd", "fourth": "4th", "fifth": "5th", "sixth": "6th",
           "seventh": "7th", "eighth": "8th", "ninth": "9th", "tenth": "10th"}


def get(url):
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": AGENT, "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.loads(r.read())
        except Exception:
            time.sleep(5 * (attempt + 1))
    return None


def norm(name):
    """ "Berkshire, Hampden, Franklin & Hampshire" and "Berkshire-Hampden-Franklin-Hampshire" -> the same words."""
    words = re.findall(r"[a-z0-9]+", name.lower().replace("&", " and "))
    return " ".join(ORDINAL.get(w, w) for w in words if w not in ("and", "district"))


def details(session):
    """Each member's record (without the long lists of bills they sponsored) into data/ma/<session>/member_details.json.
    convert.py names past General Courts' senators in roll calls from it."""
    gc = (session - 1637) // 2
    folder = os.path.join(DATA, str(session))
    os.makedirs(folder, exist_ok=True)
    codes = [m["MemberCode"] for m in (get(f"{API}/GeneralCourts/{gc}/LegislativeMembers") or [])]
    with ThreadPoolExecutor(3) as pool:
        members = [{k: v for k, v in m.items() if k not in ("SponsoredBills", "CoSponsoredBills")}
                   for m in pool.map(lambda c: get(f"{API}/GeneralCourts/{gc}/LegislativeMembers/{c}"), codes) if m]
    if len(members) >= 190:
        json.dump(members, open(os.path.join(folder, "member_details.json"), "w"), ensure_ascii=False)
    return members


def main(session):
    gc = (session - 1637) // 2
    folder = os.path.join(DATA, str(session))
    os.makedirs(folder, exist_ok=True)
    members = details(session)
    if len(members) < 190:
        raise SystemExit(f"only {len(members)} member records; kept the last contacts")
    names = json.load(open(os.path.join(DATA, "district_names.json")))
    seat_no = {h: {norm(v): int(k) for k, v in names[h].items()} for h in "SH"}
    people, by_code, unmatched = {}, {}, []
    for m in members:
        h = "S" if m.get("Branch") == "Senate" else "H"
        n = seat_no[h].get(norm(m.get("District") or ""))
        if not n:
            unmatched.append((h, m.get("District"), m.get("Name")))
            continue
        phone = m.get("PhoneNumber") or ""
        phone = re.sub(r"^(\d{3})(\d{3})(\d{4})$", r"(\1) \2-\3", phone) or None
        people[f"{h}:{n}"] = {
            "name": m["Name"], "key": name_key(m["Name"]), "id": m["MemberCode"], "party": PARTY.get(m.get("Party"), m.get("Party") or ""),
            "email": m.get("EmailAddress") or None, "form": None, "phone": phone, "phones": [["Boston", phone]] if phone else [],
            "url": f"https://malegislature.gov/Legislators/Profile/{m['MemberCode']}", "image": None, "office": "",
            "position": m.get("LeadershipPosition") or None, "places": "", "dataName": m["Name"],
        }
        by_code[m["MemberCode"]] = m["Name"]
    comms = get(f"{API}/GeneralCourts/{gc}/Committees") or []
    s_comms, h_comms = {}, {}
    for c in comms:
        d = get(f"{API}/GeneralCourts/{gc}/Committees/{c['CommitteeCode']}") or {}
        name = re.sub(r"^(?:Joint |House |Senate )?Committee on\s+", "", d.get("FullName") or d.get("Name") or c["CommitteeCode"])
        chairs = [by_code.get((d.get(k) or {}).get("MemberCode")) for k in ("HouseChairperson", "SenateChairperson")]
        members_ = sorted({by_code[x.get("MemberCode")] for k in ("HouseMembers", "SenateMembers") for x in (d.get(k) or []) if x.get("MemberCode") in by_code})
        entry = {"name": name, "chair": " and ".join(x for x in chairs if x) or None, "meets": None, "members": members_}
        code = c["CommitteeCode"]
        for h, out in (("S", s_comms), ("H", h_comms)):
            if code[0] in (h, "J"):
                out[committee_key(name)] = entry
    leaders = {}
    for h, role in (("H", "Speaker of the House"), ("S", "Senate President")):
        hit = next((p for sid, p in people.items() if sid[0] == h and (p.get("position") or "") in ("Speaker of the House", "President of the Senate")), None)
        if hit:
            leaders[h] = {"name": hit["name"], "role": role}
    out = {"session": session, "fetched": time.strftime("%Y-%m-%d %H:%M"), "people": people, "since": {},
           "senateCommittees": s_comms, "assemblyCommittees": h_comms, "leaders": leaders, "assemblyMembers": {}, "kept": []}
    path = os.path.join(DATA, f"contacts_{session}.json")
    json.dump(out, open(path, "w"), indent=1, ensure_ascii=False)
    ppl = people.values()
    print(f"{path}: {len(people)} legislators ({sum(1 for p in ppl if p['phone'])} with a phone, {sum(1 for p in ppl if p['email'])} "
          f"with email), {len(s_comms)} Senate and {len(h_comms)} House committees, leaders {leaders}; unmatched districts: {unmatched[:6]}")


if __name__ == "__main__":
    y = date.today().year
    main(int(sys.argv[1]) if len(sys.argv) > 1 else (y if y % 2 else y - 1))
