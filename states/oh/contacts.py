#!/usr/bin/env python3
"""Ohio's legislators and committees, written as data/oh/contacts_<session>.json in the shape build_data.py reads.

- Members, parties, districts and committee roles: the Legislative Service Commission's API (data/oh/<session>/
  legislators.json, committees.json, committee_members.json, from states/oh/fetch.py). Seat ids "S:5", "H:63".
- Emails and links to each member's page: Open States' public-domain file (data/oh/openstates_people.csv; decided
  2026-10-31, when the House's and Senate's sites turned automated requests away); matched by house, district and last
  name. It has no phone numbers.
- Office phones and addresses: each member's own page on ohiohouse.gov or ohiosenate.gov (data/oh/member_pages.json,
  read by fetch.py's member_pages(); approved by the owner 2026-11-22). Usage: python3 states/oh/contacts.py [session]
"""
import csv, json, os, re, sys
from datetime import datetime
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
from fetch_contacts import committee_key, name_key
from states.oh import profile as P

PARTY = {"party_republican_1": "Republican", "party_democrat_1": "Democratic"}


def page_of(row):
    """A current member's page on their own house's site, from Open States' links (a senator's can name their old
    House page first): "https://www.ohiosenate.gov/members/rob-mccolley"."""
    site = "ohiosenate.gov" if row["current_chamber"] == "upper" else "ohiohouse.gov"
    for u in row["links"].split(";"):
        m = re.match(rf"https?://(?:www\.)?{re.escape(site)}/members/([a-z0-9-]+)/?$", u.strip())
        if m:
            return f"https://www.{site}/members/{m.group(1)}"
    return None


def build(session):
    folder = os.path.join(P.DATA, str(session))
    legs = json.load(open(os.path.join(folder, "legislators.json")))
    try:
        rows = list(csv.DictReader(open(os.path.join(P.DATA, "openstates_people.csv"))))
    except OSError:
        rows = []
    try:
        pages = json.load(open(os.path.join(P.DATA, "member_pages.json")))
    except (OSError, ValueError):
        pages = {}
    os_by = {("S" if r["current_chamber"] == "upper" else "H", int(r["current_district"] or 0)): r for r in rows}
    people, by_lpid = {}, {}
    for m in legs:
        if not m.get("active") or not str(m.get("district", "")).isdigit() or (m.get("lastname") or "") == "Vacant":
            continue
        # "Hall, D.": the API tells members with the same last name apart after a comma.
        last = (m.get("lastname") or "").split(",")[0].strip()
        h = "S" if m.get("chamber") == "Senate" else "H"
        sid = f"{h}:{int(m['district'])}"
        name = m.get("displayname") or f"{m.get('firstname', '')} {m.get('lastname', '')}".strip()
        o = os_by.get((h, int(m["district"])))
        # Open States' member for the seat, when it's the same person (a vacancy filled since would differ).
        same = lambda x: name_key(x.replace("\u2010", "-").replace("\u2011", "-")).split()[-1:]
        if o and same(o["family_name"]) != same(last or name):
            o = None
        page = page_of(o) if o else None
        info = pages.get(page) or {}
        phones = [["Columbus", n] for n in info.get("phones", [])]
        people[sid] = {
            "name": name, "key": name_key(name), "id": m.get("lpid"), "party": PARTY.get(m.get("party"), ""),
            "email": (o or {}).get("email") or None, "form": None,
            "phone": phones[0][1] if phones else None, "phones": phones,
            "url": page, "image": (o or {}).get("image") or None, "office": info.get("office", ""),
            "position": None, "places": "", "dataName": last or name,
        }
        by_lpid[m.get("lpid")] = name
    s_comms, h_comms = {}, {}
    try:
        members = json.load(open(os.path.join(folder, "committee_members.json")))
    except (OSError, ValueError):
        members = {}
    for c in json.load(open(os.path.join(folder, "committees.json"))):
        if not c.get("active") or c.get("chamber") not in ("House", "Senate"):
            continue
        ms = members.get(c["lpid"], [])
        names = sorted({by_lpid.get(x.get("lpid")) or x.get("display_name") for x in ms if x.get("lpid")} - {None})
        chair = next((by_lpid.get(x.get("lpid")) or x.get("display_name") for x in ms if (x.get("role") or "").lower() in ("chair", "chairman", "chairperson")), None)
        (s_comms if c["chamber"] == "Senate" else h_comms)[committee_key(c["name"])] = {
            "name": c["name"], "chair": chair, "meets": None, "members": names}
    leaders = {}
    for h, (name, role, _) in P.LEADERS.items():
        hit = next((p for sid, p in people.items() if sid[0] == h and p["key"] == name_key(name)), None)
        if hit:
            hit["position"] = role
            leaders[h] = {"name": hit["name"], "role": role}
    return {"session": session, "fetched": datetime.now(ZoneInfo(P.TIMEZONE)).strftime("%Y-%m-%d %H:%M ET"),
            "people": people, "since": {}, "senateCommittees": s_comms, "assemblyCommittees": h_comms,
            "leaders": leaders, "assemblyMembers": {}, "kept": []}


def main(session):
    out = build(session)
    path = os.path.join(P.DATA, f"contacts_{session}.json")
    json.dump(out, open(path, "w"), indent=1, ensure_ascii=False)
    ppl = out["people"].values()
    comms = list(out["senateCommittees"].values()) + list(out["assemblyCommittees"].values())
    print(f"{path}: {len(out['people'])} legislators ({sum(1 for p in ppl if p['email'])} with email, "
          f"{sum(1 for p in ppl if p['phone'])} with a phone, {sum(1 for p in ppl if p['url'])} with a page, "
          f"{sum(1 for p in ppl if p['party'])} with party), {len(out['senateCommittees'])} Senate and "
          f"{len(out['assemblyCommittees'])} House committees ({sum(1 for c in comms if c['chair'])} with a chair), "
          f"leaders {sorted(out['leaders'])}")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else P.session_of(datetime.now(ZoneInfo(P.TIMEZONE)).year))
