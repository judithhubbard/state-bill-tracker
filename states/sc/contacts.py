#!/usr/bin/env python3
"""South Carolina's legislators and committees, written as data/sc/contacts_<session>.json in the shape build_data.py
reads.

From what states/sc/fetch.py downloads, no other web pages:
- data/sc/<session>/members_H.json, members_S.json: every member of the General Assembly (code, district, party). Each
  seat goes to the member who held it last (convert.seats(), by the last roll call each was named on); members who left
  mid-term aren't listed.
- data/sc/members/<code>.json: each member's page: Columbia (State House complex) office and phone, home or business
  address and phones, leadership position, and the page's message form. The Legislature publishes no email addresses:
  each member's contact is that form (shown as "Contact form"), never an invented address.
- data/sc/committees_H.json, committees_S.json: each house's standing committees today, with chairs and members by
  code. Past General Assemblies' committees aren't published, so a past session's contacts have none. The Ethics
  committees are left out (bills aren't sent there).
Leadership positions are named for the current General Assembly only.
Usage: python3 states/sc/contacts.py [session]   (default: every General Assembly downloaded)
"""
import json, os, re, sys
from datetime import datetime
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
from fetch_contacts import committee_key, name_key
from states.sc import convert as C
from states.sc import profile as P

PARTY = {"D": "Democratic", "R": "Republican", "I": "Independent", "Democrat": "Democratic", "Republican": "Republican"}
LEAD = re.compile(r"^(Speaker|Speaker Pro Tempore|President|President Pro Tempore|Majority Leader|Minority Leader)$")
SKIP = re.compile(r"^Ethics\b", re.I)


def phone(x):
    d = re.sub(r"\D", "", x or "")
    if len(d) == 11 and d[0] == "1":
        d = d[1:]
    return f"({d[:3]}) {d[3:6]}-{d[6:]}" if len(d) == 10 else None


def address(block):
    return ", ".join(C.text(x) for x in (block or {}).get("address", "").split("\n") if C.text(x)) or None


def unlisted(name):
    """A committee list's "Jordan, Wallace H. \"Jay\", Jr." -> "Wallace H. \"Jay\" Jordan, Jr.", for C.display()."""
    ps = [x.strip() for x in C.text(name).split(",")]
    return f"{ps[1]} {ps[0]}" + (f", {ps[2]}" if len(ps) > 2 else "") if len(ps) > 1 else C.text(name)


def build(session):
    now = session == max(C.sessions())
    seats = C.seats(session)
    people, by_code = {}, {}
    for (h, code), m in C.members(session).items():
        sid = seats.get((h, code))
        if not sid or "?" in sid:
            continue
        pg = C.member_page(code) or {}
        if pg.get("chamber") and pg["chamber"] != h and now:
            pg = {k: v for k, v in pg.items() if k in ("code", "name")}  # the page is for the member's newer house
        phones, seen = [], set()
        for label, block in (("Columbia office", pg.get("columbia")), ("", pg.get("home"))):
            for kind, num in ((block or {}).get("phones") or {}).items():
                ph = phone(num)
                if ph and ph not in seen:
                    seen.add(ph)
                    phones.append([label or {"Home Phone": "Home", "Business Phone": "Business", "Cell Phone": "Cell"}.get(kind, kind), ph])
                    if label:
                        label = "Columbia office"
        pos = C.text(pg.get("position"))
        people[sid] = {
            "name": m["name"], "key": name_key(m["name"]), "id": code, "party": PARTY.get(m["party"], PARTY.get(pg.get("party"), m["party"])),
            "email": None, "form": pg.get("contact"),
            "phone": phones[0][1] if phones else None, "phones": phones,
            "url": f"https://www.scstatehouse.gov/member.php?code={code}", "image": None,
            "office": address(pg.get("columbia")), "position": pos if now and LEAD.match(pos) else None,
            "places": C.text(pg.get("district_counties")), "dataName": m["name"],
        }
        by_code[code] = m["name"]
    comms = {"S": {}, "H": {}}
    if now:
        for h in "SH":
            try:
                rows = json.load(open(os.path.join(P.DATA, f"committees_{h}.json"), encoding="utf-8"))
            except (OSError, ValueError):
                rows = []
            for c in rows:
                name = re.sub(r"\s+Com\.$", "", C.committee_name(c.get("name")))
                if SKIP.search(name):
                    continue
                who = lambda x: by_code.get(x.get("code")) or C.display(unlisted(x.get("name")))
                chair = (c.get("chair") or {})
                chair_name = by_code.get(chair.get("code")) or (C.display(chair["name"]) if chair.get("name") else None)
                vice = next((who(x) for x in c.get("members") or [] if re.match(r"(1st )?V\.C\.", x.get("role") or "")), None)
                members = sorted({who(x) for x in c.get("members") or []} | ({chair_name} if chair_name else set()))
                comms[h][committee_key(name)] = {"name": name, "chair": chair_name, "coChairs": [], "viceChair": vice,
                                                 "meets": None, "members": members}
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
    if len(out["people"]) < 150:
        raise SystemExit(f"{session}: only {len(out['people'])} legislators; kept the last contacts")
    path = os.path.join(P.DATA, f"contacts_{session}.json")
    json.dump(out, open(path, "w"), indent=1, ensure_ascii=False)
    ppl = out["people"].values()
    comms = list(out["senateCommittees"].values()) + list(out["assemblyCommittees"].values())
    print(f"{path}: {len(out['people'])} legislators ({sum(1 for p in ppl if p['form'])} with a contact form, "
          f"{sum(1 for p in ppl if p['phone'])} with a phone), {len(out['senateCommittees'])} Senate and "
          f"{len(out['assemblyCommittees'])} House committees ({sum(1 for c in comms if c['chair'])} with a chair), "
          f"leaders {sorted(out['leaders'])}")


if __name__ == "__main__":
    for s in ([int(sys.argv[1])] if len(sys.argv) > 1 else C.sessions()):
        main(s)
