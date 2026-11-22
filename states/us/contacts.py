#!/usr/bin/env python3
"""Congress's members and committees, written as data/us/contacts_<session>.json in the shape build_data.py reads.

From the public-domain congress-legislators data that states/us/fetch.py downloads (data/us/members/), no web pages:
- legislators-current.json and legislators-historical.json: every member with their terms (state, district or Senate
  class, party, office address, Washington phone, contact form, website). A Congress's seats go to the members who held
  them at its end (or now, for the current one); the House's seats are "H:612" (California's 12th: 100 times the
  state's FIPS code plus the district), the Senate's "S:6a"/"S:6b" (convert.members()). Members of Congress publish no
  email addresses: each has a contact form (`form`), which the page offers instead. The data gives senators' forms;
  for representatives it gives only the website, whose contact page is the form, so `form` is the website.
- The six delegates and the Resident Commissioner (DC, Puerto Rico, Guam, the Virgin Islands, American Samoa, the
  Northern Mariana Islands) are House members who can't vote on a bill's passage: they're listed (marked "nonvoting")
  and balance.py leaves them out of the House's party count.
- committees-current.json and committee-membership-current.json: the current Congress's standing and select
  committees with their members, chairs ("Chairman"/"Chair") and ranking members; subcommittees and joint committees
  are left out. Past Congresses' committees aren't in the data.
Usage: python3 states/us/contacts.py [session]   (default: every Congress downloaded)
"""
import json, os, re, sys
from datetime import datetime
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
from fetch_contacts import committee_key, name_key
from states.us import convert as C
from states.us import profile as P

POSITIONS = re.compile(r"^(?:House|Senate) (?:Majority|Minority) (?:Leader|Whip)$|^President Pro Tempore")


def phone(x):
    d = re.sub(r"\D", "", x or "")
    return f"({d[:3]}) {d[3:6]}-{d[6:]}" if len(d) == 10 else None


def election_day(iso):
    """Whether a day is a November general election day (the Tuesday after the first Monday)."""
    d = datetime.strptime(iso, "%Y-%m-%d").date()
    return d.month == 11 and d.weekday() == 1 and 2 <= d.day <= 8


def holders(congress):
    """Seat -> (member, term) holding it at the Congress's end (or today, for the current one: members who left, with
    their term's end set to the day they left, are dropped), and seat -> the year the member first took a seat in
    that house."""
    start, end = C.congress_dates(congress)
    today = datetime.now(ZoneInfo(P.TIMEZONE)).date().isoformat()
    when = min(end, today)
    now = congress == max(C.CONGRESSES)
    seats = {}
    for bid, m in C.members(congress).items():
        for t in m["terms"]:
            h = "S" if t["type"] == "sen" else "H"
            sid = m["seats"].get(h)
            # An appointed senator's term ends on the special election's day; they serve until the winner is sworn in,
            # so they keep the seat until someone else's term starts (Ohio's and Florida's in November 2026).
            if not sid or t["start"] > when or (now and t["end"] < today and not election_day(t["end"])):
                continue
            if sid not in seats or t["start"] > seats[sid][1]["start"]:
                seats[sid] = (bid, t)
    since = {}
    for sid, (bid, t) in seats.items():
        firsts = [x["start"] for x in C.members(congress)[bid]["bio"]["terms"] if (x["type"] == "sen") == (sid[0] == "S")]
        since[sid] = int(min(firsts)[:4]) if firsts else None
    return seats, since


def build(session):
    congress = P.congress_of(session)
    now = congress == max(C.CONGRESSES)
    ms = C.members(congress)
    seats, since = holders(congress)
    people = {}
    for sid, (bid, t) in sorted(seats.items()):
        m = ms[bid]
        code = t["state"]
        phones = [["Washington office", phone(t.get("phone"))]] if phone(t.get("phone")) else []
        roles = [r["title"] for r in m["bio"].get("leadership_roles") or [] if not r.get("end") or r["end"] >= C.congress_dates(congress)[1]]
        pos = next((r for r in roles if POSITIONS.match(r)), None)
        for h, (name, role, _) in P.LEADERS.items():
            if now and h == sid[0] and name_key(name) == name_key(m["name"]):
                pos = role
        people[sid] = {
            "name": m["name"], "key": name_key(m["name"]), "id": bid, "party": m["party"],
            "email": None, "form": t.get("contact_form") or (t.get("url") if sid[0] == "H" else None) or None,
            "phone": phones[0][1] if phones else None, "phones": phones,
            "url": t.get("url") or None, "image": None,
            "office": (t.get("address") or "").replace(" WASHINGTON DC ", ", Washington, DC ") or None,
            "position": pos, "places": P.seat_name(sid[0], re.sub(r"\D", "", sid[2:])), "dataName": m["name"],
            **({"nonvoting": True} if code in P.NONVOTING else {}),
        }
    comms = {"S": {}, "H": {}}
    if now:
        info = json.load(open(os.path.join(P.DATA, "members", "committees-current.json")))
        roster = json.load(open(os.path.join(P.DATA, "members", "committee-membership-current.json")))
        names = {bid: ms[bid]["name"] for bid in ms}
        for c in info:
            h = {"house": "H", "senate": "S"}.get(c.get("type"))
            if not h:
                continue
            name = C.committee_name(re.sub(r"^(?:House|Senate) (?:Select |Permanent Select |Special )?Committee on (?:the )?", "", c["name"]))
            if re.search(r"Caucus|Subcommittee", name):
                continue
            who = roster.get(c.get("thomas_id"), [])
            members = sorted({names.get(x.get("bioguide"), x.get("name")) for x in who})
            chair = next((names.get(x.get("bioguide"), x.get("name")) for x in who if (x.get("title") or "") in ("Chairman", "Chair", "Chairwoman")), None)
            comms[h][committee_key(name)] = {"name": name, "chair": chair, "coChairs": [], "viceChair": None,
                                            "meets": None, "members": members}
    leaders = {}
    if now:
        for h, (name, role, _) in P.LEADERS.items():
            hit = next((p for sid, p in people.items() if sid[0] == h and p["key"] == name_key(name)), None)
            if hit:
                leaders[h] = {"name": hit["name"], "role": role}
    return {"session": session, "fetched": datetime.now(ZoneInfo(P.TIMEZONE)).strftime("%Y-%m-%d %H:%M"),
            "people": people, "since": since, "senateCommittees": comms["S"], "assemblyCommittees": comms["H"],
            "leaders": leaders, "assemblyMembers": {}, "kept": []}


def main(session):
    out = build(session)
    n = len(out["people"])
    if n < 500:
        raise SystemExit(f"{session}: only {n} members; kept the last contacts")
    path = os.path.join(P.DATA, f"contacts_{session}.json")
    # Written when something changed, or daily (check_site.py wants it fresh): Congress's saved copy is large, and
    # download.yml saves it only when a file changed.
    try:
        last = json.load(open(path))
    except (OSError, ValueError):
        last = {}
    same = {k: v for k, v in last.items() if k != "fetched"} == {k: v for k, v in out.items() if k != "fetched"}
    if same and last.get("fetched", "")[:10] == out["fetched"][:10]:
        print(f"{path}: unchanged")
        return
    json.dump(out, open(path, "w"), indent=1, ensure_ascii=False)
    ppl = out["people"].values()
    print(f"{path}: {n} members ({sum(1 for s in out['people'] if s[0] == 'S')} senators, "
          f"{sum(1 for s, p in out['people'].items() if s[0] == 'H' and not p.get('nonvoting'))} representatives, "
          f"{sum(1 for p in ppl if p.get('nonvoting'))} delegates; {sum(1 for p in ppl if p['form'])} with a contact form, "
          f"{sum(1 for p in ppl if p['phone'])} with a phone), {len(out['senateCommittees'])} Senate and "
          f"{len(out['assemblyCommittees'])} House committees, leaders {sorted(out['leaders'])}")


if __name__ == "__main__":
    for s in ([int(sys.argv[1])] if len(sys.argv) > 1 else C.sessions()):
        try:
            main(s)
        except SystemExit:
            # A new Congress's members may not be in congress-legislators yet when its first bills are: until
            # March, too few members leaves its contacts unwritten without failing the run.
            if s != max(C.sessions()) or datetime.now(ZoneInfo(P.TIMEZONE)).date().isoformat() >= f"{s}-03-01":
                raise
            print(f"{s}: too few members of the new Congress listed yet; no contacts written")
