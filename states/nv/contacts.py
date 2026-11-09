#!/usr/bin/env python3
"""Nevada's legislators and committees, written as data/nv/contacts_<session>.json in the shape build_data.py reads.

From what states/nv/fetch.py downloads:
- data/nv/<session>/members/members.json: each district's member (party, district, county, Carson City room and phone,
  Las Vegas office room, leadership post, page). A member who resigned (Toby Yurek, Assembly 19, October 2025) is left
  out, and the seat shows as vacant. For the next session (members-elect, listed from November of the even year) the
  posts are still the last session's, so no posts are taken from it.
- committees.json: each house's standing committees with chair, vice chair and members, tied to the members by house
  and district. The Committees of the Whole are left out. The next session's committees are listed only once it
  organizes.
- Emails: Open States' public-domain file (data.openstates.org/people/current/nv.csv, saved as
  data/nv/openstates_people.csv), since the Legislature's pages hide members' addresses behind Cloudflare's script (as
  for North Carolina); matched by house and district when the last name agrees, so a seat Open States hasn't updated
  after an election gets none.
Leaders (P.LEADERS) are named for the current session only.
Usage: python3 states/nv/contacts.py [session]   (default: every session downloaded)
"""
import csv, json, os, re, sys, time, urllib.request
from datetime import datetime
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
from fetch_contacts import committee_key, name_key
from states.nv import convert as C
from states.nv import profile as P

PEOPLE = "https://data.openstates.org/people/current/nv.csv"
AGENT = "statebilltracker.org (a nonprofit bill tracker; contact via github.com/judithhubbard)"
SITE = "https://www.leg.state.nv.us"
GONE = re.compile(r"\b(?:Resigned|Died|Deceased|Expelled|Removed)\b", re.I)


def get(url):
    for attempt in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": AGENT}), timeout=120) as r:
                return r.read()
        except Exception:
            time.sleep(10 * (attempt + 1))
    return None


_OS = []


def open_states():
    """Open States' current members, (house, district) -> row; the last copy when the download fails."""
    if _OS:
        return _OS[0]
    path = os.path.join(P.DATA, "openstates_people.csv")
    body = get(PEOPLE)
    if body and body.startswith(b"id,"):
        with open(path, "wb") as f:
            f.write(body)
    try:
        rows = list(csv.DictReader(open(path, encoding="utf-8")))
    except OSError:
        rows = []
    _OS.append({("S" if r["current_chamber"] == "upper" else "A", int(r["current_district"])): r
                for r in rows if (r.get("current_district") or "").isdigit()})
    return _OS[0]


def phone(x):
    d = re.sub(r"\D", "", x or "")
    return f"({d[:3]}) {d[3:6]}-{d[6:]}" if len(d) == 10 else None


def build(session):
    now = session == P.session_of(datetime.now(ZoneInfo(P.TIMEZONE)).year)
    newest = session == max(C.sessions())
    os_by = open_states() if newest or now else {}
    people, by_seat = {}, {}
    for m in C.load(session, "members"):
        h = C.CHAMBER.get(m.get("house"))
        if not h or not m.get("district") or GONE.search(m.get("status") or ""):
            continue
        sid = f"{h}:{int(m['district'])}"
        name = C.full_name(m)
        o = os_by.get((h, int(m["district"])))
        if o and name_key(o["name"]).split()[-1:] != name_key(name).split()[-1:]:
            o = None  # Open States still has the seat's last holder
        ph = phone(m.get("carson_phone"))
        office = "; ".join(x for x in (f"Legislative Building, Room {m['carson_office']}, Carson City" if m.get("carson_office") else "",
                                       f"Las Vegas office, Room {m['las_vegas_office']}" if m.get("las_vegas_office") else "") if x)
        people[sid] = {
            "name": name, "key": name_key(name), "id": sid, "party": m.get("party") or "",
            "email": (o or {}).get("email") or None, "form": None,
            "phone": ph, "phones": [["Carson City", ph]] if ph else [],
            "url": SITE + m["page"] if m.get("page") else None,
            "image": None, "office": office or None,
            "position": (C.text(m.get("post")) or None) if now else None,
            "places": C.text(m.get("county")), "dataName": C.text(m.get("name")),
        }
        by_seat[sid] = name
    comms = {"S": {}, "A": {}}
    for c in C.load(session, "committees"):
        h = C.CHAMBER.get(c.get("house"))
        name = re.sub(r"^(?:Assembly|Senate)\s+", "", C.text(c.get("name")))
        if not h or name == "Committee of the Whole":
            continue

        def who(x):
            sid = f"{C.CHAMBER.get(x.get('house'), h)}:{x.get('district')}"
            return by_seat.get(sid) or C.text(x.get("name"))
        ms = c.get("members") or []
        chair = [who(x) for x in ms if x.get("role") == "Chair"]
        vice = [who(x) for x in ms if x.get("role") == "Vice Chair"]
        comms[h][committee_key(name)] = {"name": name, "chair": chair[0] if chair else None, "coChairs": chair[1:],
                                         "viceChair": vice[0] if vice else None, "meets": C.text(c.get("meets")) or None,
                                         "members": sorted({who(x) for x in ms})}
    leaders = {}
    if now:
        for h, (name, role, _) in P.LEADERS.items():
            hit = next((p for sid, p in people.items() if sid[0] == h and p["key"] == name_key(name)), None)
            if hit:
                leaders[h] = {"name": hit["name"], "role": role}
    return {"session": session, "fetched": datetime.now(ZoneInfo(P.TIMEZONE)).strftime("%Y-%m-%d %H:%M"),
            "people": people, "since": {}, "senateCommittees": comms["S"], "assemblyCommittees": comms["A"],
            "leaders": leaders, "assemblyMembers": {}, "kept": []}


def main(session):
    out = build(session)
    if len(out["people"]) < 55:
        raise SystemExit(f"{session}: only {len(out['people'])} legislators; kept the last contacts")
    path = os.path.join(P.DATA, f"contacts_{session}.json")
    json.dump(out, open(path, "w"), indent=1, ensure_ascii=False)
    ppl = list(out["people"].values())
    comms = list(out["senateCommittees"].values()) + list(out["assemblyCommittees"].values())
    phones = [p["phone"] for p in ppl if p["phone"]]
    dup = sorted({x for x in phones if phones.count(x) > 1})
    print(f"{path}: {len(ppl)} legislators ({sum(1 for p in ppl if p['email'])} with email, {len(phones)} with a phone"
          f"{f'; shared phones {dup}' if dup else ''}), {len(out['senateCommittees'])} Senate and "
          f"{len(out['assemblyCommittees'])} Assembly committees ({sum(1 for c in comms if c['chair'])} with a chair), "
          f"leaders {sorted(out['leaders'])}")


if __name__ == "__main__":
    for s in ([int(sys.argv[1])] if len(sys.argv) > 1 else C.sessions()):
        main(s)
