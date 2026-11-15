#!/usr/bin/env python3
"""Iowa's legislators, written as data/ia/contacts_<session>.json in the shape build_data.py reads.

From what states/ia/fetch.py saves (it reads legis.iowa.gov; this script reads only the saved files): each General
Assembly's member lists (data/ia/members/<first year>/members.json, else the saved house.html and senate.html: name,
district, party, county, email; members who left show their dates of service) and each member's page where it's been
read (pages/<person>.html: "Capitol Phone"); Open States' public-domain people file (data/ia/openstates_people.csv) when
neither list is there. Nearly every member's Capitol phone is the House's (515) 281-3221 or the Senate's (515) 281-3371
switchboard, so it's shown as that ("Capitol (House switchboard)"), the same for every member of the house; a member's own
number is shown as their own. Photos are left out (they're served by legis.iowa.gov, which isn't to be read automatically).

Committees come from data/ia/committees.json (fetch.py: the current General Assembly's standing committees with "Chair",
"Vice Chair" and "Ranking Member") when it exists; until then none are shown (the member pages list committees, but only
some pages have been read). Iowa has 50 Senate and 100 House districts, one member each: seats "S:12", "H:12". A past
General Assembly's contacts are today's members. Usage: python3 states/ia/contacts.py [session]
"""
import json, os, re, sys
from datetime import datetime
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
from fetch_contacts import committee_key, name_key
from states.ia import convert as C
from states.ia import profile as P

SWITCHBOARD = {"H": ("Capitol (House switchboard)", "(515) 281-3221"), "S": ("Capitol (Senate switchboard)", "(515) 281-3371")}


def phone(s):
    d = re.sub(r"\D", "", s or "")
    d = d[1:] if len(d) == 11 and d[0] == "1" else d
    return f"({d[:3]}) {d[3:6]}-{d[6:]}" if len(d) == 10 else ""


def page_info(session, person):
    try:
        page = open(os.path.join(P.DATA, "members", str(session), "pages", f"{person}.html"), encoding="utf-8").read()
    except (OSError, TypeError):
        return {}
    info = {C.text(k).rstrip(":"): C.text(v) for k, v in re.findall(r"<label>(.*?):?</label></td><td>(.*?)</td>", page, re.S)}
    if not info:  # an older saved layout: "Capitol Phone: 515.281.3221" in the text
        t = C.text(page)
        for k in ("Capitol Phone", "Home Phone", "Cell Phone", "Business Phone", "Legislative Email"):
            m = re.search(rf"{k}:\s*([\w.@\-() ]+?)(?=\s+[A-Z][a-z]+ (?:Phone|Email|Address)|\s+Subscribe|$)", t)
            if m:
                info[k] = m.group(1).strip()
    return info


def build(session):
    cur = C.current_session()
    mems = [m for m in C.members(cur) if not m["served"]]  # sitting members (members who left show dates of service)
    people = {}
    for m in mems:
        seat = f"{m['house']}:{m['district']}"
        info = page_info(cur, m["person"])
        phones = []
        own = phone(info.get("Capitol Phone"))
        board = SWITCHBOARD[m["house"]]
        if own and own != board[1]:
            phones.append(["Capitol", own])
        for k in ("Home Phone", "Cell Phone", "Business Phone"):
            p = phone(info.get(k))
            if p and p not in [x[1] for x in phones]:
                phones.append([k.replace(" Phone", ""), p])
        phones.append(list(board))
        email = (info.get("Legislative Email") or m["email"] or "").lower() or None
        url = f"https://www.legis.iowa.gov/legislators/legislator?ga={P.ga_of(cur)}&personID={m['person']}" if m["person"] else None
        people[seat] = {"name": m["name"], "key": name_key(m["name"]), "id": m["person"],
                        "party": {"D": "Democratic", "R": "Republican"}.get(m["party"], m["party"]),
                        "email": email, "form": None, "phone": phones[0][1], "phones": phones, "url": url, "image": None,
                        "office": "Iowa State Capitol, 1007 E Grand Ave, Des Moines, IA 50319", "position": None,
                        "places": f"District {m['district']}",
                        "dataName": C.display(m["name"].split()[-1] if not m["raw"].get("surname") else m["raw"]["surname"])}
    comms = {"S": {}, "H": {}}
    cj = C.load(os.path.join(P.DATA, "committees.json"), {}) or {}
    if cj.get("ga") == P.ga_of(cur):
        for c in cj.get("committees") or []:
            for h, word in (("S", "Senate"), ("H", "House")):
                mem = [x for x in c.get("members") or [] if x.get("house") == word]
                if not mem:
                    continue
                name = C.comm_name(re.sub(rf"^{word}\s+", "", c.get("name") or ""))
                full = lambda x: next((p["name"] for s, p in people.items() if s == f"{h}:{x.get('district')}"), x.get("name"))
                chair = next((full(x) for x in mem if x.get("role") == "Chair"), None)
                vice = next((full(x) for x in mem if x.get("role") == "Vice Chair"), None)
                comms[h][committee_key(name)] = {"name": name, "chair": chair, "coChairs": [], "viceChair": vice, "meets": None,
                                                 "members": sorted({full(x) for x in mem})}
    leaders = {}
    for h, (name, role, _) in P.LEADERS.items():
        hit = next((p for sid, p in people.items() if sid[0] == h and p["key"] == name_key(name)), None)
        if hit:
            hit["position"] = role
            leaders[h] = {"name": hit["name"], "role": role}
    return {"session": session, "fetched": datetime.now(ZoneInfo(P.TIMEZONE)).strftime("%Y-%m-%d %H:%M"),
            "people": people, "since": {}, "senateCommittees": comms["S"], "assemblyCommittees": comms["H"],
            "leaders": leaders, "assemblyMembers": {}, "kept": []}


def main(sessions):
    for session in sessions:
        out = build(session)
        if len(out["people"]) < 140:
            raise SystemExit(f"only {len(out['people'])} legislators; kept the last contacts")
        path = os.path.join(P.DATA, f"contacts_{session}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(out, f, indent=1, ensure_ascii=False)
        ppl = out["people"].values()
        print(f"{path}: {len(out['people'])} legislators ({sum(1 for p in ppl if p['email'])} with email, "
              f"{sum(1 for p in ppl if len(p['phones']) > 1)} with a number of their own), {len(out['senateCommittees'])} Senate "
              f"and {len(out['assemblyCommittees'])} House committees, leaders {sorted(out['leaders'])}")


if __name__ == "__main__":
    main([int(sys.argv[1])] if len(sys.argv) > 1 else C.sessions())
