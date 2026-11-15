#!/usr/bin/env python3
"""Florida's legislators and committees, written as data/fl/contacts_<session>.json in the shape build_data.py reads.

From what states/fl/fetch.py downloads, no other web pages:
- data/fl/members/<term>.json: each two-year term's Senate and House lists (name, district, party, counties; the
  Senate's posts; House members' dates of service), and for the current term each member's page once fetch.py has read
  it (offices with phones; the Senate's committee assignments).
- data/fl/committees/: the Senate's committees (senate.json: members with "Chair"/"Vice Chair") and the House's for a term
  (house_<term id>.json: leadership with roles, members by member id), when they've been read.
Neither house publishes members' email addresses: senators are written through the form on their page, representatives
through the House's contact form; those are the contact links, and no email is made up. Missing phones, committees or
posts are left out, not guessed.
A session's contacts are the members of its term who held each seat at the session's end (a member who left mid-term
gives way to the one who followed); the next session's page (prefiled bills) has the newly elected term's members.
Each district elects one member: seats "S:12", "H:45".
Usage: python3 states/fl/contacts.py [session]   (default: every session downloaded)
"""
import glob, json, os, re, sys
from datetime import datetime
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
from fetch_contacts import committee_key, name_key
from states.fl import convert as C
from states.fl import profile as P

PARTY = {"Republican": "Republican", "Democrat": "Democratic", "Democratic": "Democratic",
         "No Party Affiliation": "No party affiliation"}
HOUSE_TERM_ID = lambda term: 92 + (term - 2026) // 2


def phone(p):
    d = re.sub(r"\D", "", p or "")
    if len(d) == 11 and d[0] == "1":
        d = d[1:]
    return f"({d[:3]}) {d[3:6]}-{d[6:]}" if len(d) == 10 else None


def end_of(session):
    return P.SESSION_ENDS.get(session) or f"{session}-05-01"


def holder(ms, day):
    """Of a seat's members in a term, the one serving on that day (else the last to start)."""
    on = [m for m in ms if (not m["start"] or m["start"] <= day) and (not m["end"] or day <= m["end"])]
    pick = on or ms
    return max(pick, key=lambda m: m["start"] or "")


def offices(m):
    """[[label, phone], ...] and a Capitol address, from the member's page fields when fetch.py has read them."""
    phones, office = [], None
    for label, lines in (m.get("offices") or {}).items():
        lab = "Tallahassee" if re.search(r"Tallahassee|Capitol", label + " " + " ".join(lines), re.I) else "District"
        for x in lines:
            ph = phone(x) if re.search(r"\(\d{3}\)\s*\d{3}-\d{4}", x) and not re.search(r"fax", x, re.I) else None
            if ph and ph not in [p for _, p in phones]:
                phones.append([lab, ph])
        if lab == "Tallahassee" and not office:
            addr = [x for x in lines if not re.search(r"\(\d{3}\)|fax|phone", x, re.I)]
            office = ", ".join(addr) or None
    if not phones:
        for x in m.get("phones") or []:
            ph = phone(x)
            if ph and ph not in [p for _, p in phones]:
                phones.append(["", ph])
    phones.sort(key=lambda x: x[0] != "Tallahassee")
    return phones, office


def person(m, term, current):
    phones, office = offices(m) if current else ([], None)
    if m["house"] == "S":
        url = f"https://www.flsenate.gov{m['page']}" if m.get("page") else None
        form = f"https://www.flsenate.gov/Senators/S{m['district']}" if current else None
    else:
        url = (f"https://www.flhouse.gov/Sections/Representatives/details.aspx?MemberId={m['member_id']}"
               f"&LegislativeTermId={HOUSE_TERM_ID(term)}") if m.get("member_id") else None
        form = f"https://www.flhouse.gov/Sections/Representatives/contactmember.aspx?MemberId={m['member_id']}" \
            if current and m.get("member_id") else None
    return {
        "name": m["display"], "key": name_key(m["display"]), "id": m.get("member_id"),
        "party": PARTY.get(m.get("party"), m.get("party") or ""), "email": None, "form": form,
        "phone": phones[0][1] if phones else None, "phones": phones, "url": url, "image": None, "office": office,
        "position": re.sub(r"\s+\d+/\d+/\d+-\d+/\d+/\d+$", "", m.get("post") or "") or None,
        "places": re.sub(r"^Consist(?:s|ed) of ", "", (m.get("counties") or "").split('">')[-1].strip()), "dataName": m["lastRaw"],
    }


def committees(term, current):
    """{"S": {key: committee}, "H": {...}} from data/fl/committees/, for the current term only."""
    out = {"S": {}, "H": {}}
    if not current:
        return out
    by_id = {m.get("member_id"): m for m in C.members(term) if m["house"] == "H"}

    def entry(h, name):
        return out[h].setdefault(committee_key(name), {"name": name, "chair": None, "coChairs": [], "viceChair": None,
                                                       "meets": None, "members": []})
    sen = C.load(os.path.join(P.DATA, "committees", "senate.json"), {}) or {}
    for c in sen.get("committees") or []:
        if not c.get("members") or re.search(r"TBA", " ".join(x.get("text", "") for x in c["members"])):
            continue
        e = entry("S", C.comm_name(c.get("name")))
        for x in c["members"]:
            t = x.get("text") or ""
            who = re.sub(r"^Senator\s+|,?\s*\(?(?:Vice Chair|Chair|Co-Chair|Alternating Chair)\)?.*$", "", t).strip()
            hits = C.holders(term, "S", C.fold(who.split(",")[0].split()[-1] if who else ""))
            name = hits[0]["display"] if len(hits) == 1 else who
            if not name:
                continue
            if name not in e["members"]:
                e["members"].append(name)
            if re.search(r"Vice Chair", t):
                e["viceChair"] = e["viceChair"] or name
            elif re.search(r"\bChair\b", t):
                if e["chair"]:
                    e["coChairs"].append(name)
                else:
                    e["chair"] = name
    for f in glob.glob(os.path.join(P.DATA, "committees", f"house_{HOUSE_TERM_ID(term)}.json")):
        for c in (C.load(f, {}) or {}).get("committees") or []:
            e = entry("H", C.comm_name(c.get("name")))
            for x in (c.get("leaders") or []) + (c.get("members") or []):
                if x.get("active") is False:
                    continue
                m = by_id.get(x.get("member_id"))
                name = m["display"] if m else C.display(x.get("name") or "")
                if name and name not in e["members"]:
                    e["members"].append(name)
                role = x.get("role") or ""
                if role == "Chair" and not e["chair"]:
                    e["chair"] = name
                elif role == "Vice Chair" and not e["viceChair"]:
                    e["viceChair"] = name
    for h in out:
        for e in out[h].values():
            e["members"].sort()
    return out


def build(session):
    term = P.term_of(session)
    today = datetime.now(ZoneInfo(P.TIMEZONE)).date().isoformat()
    current_term = max(int(os.path.basename(f)[:-5]) for f in glob.glob(os.path.join(P.DATA, "members", "*.json")))
    current = term == current_term
    day = today if current else end_of(session)
    seats = {}
    for m in C.members(term):
        seats.setdefault(f"{m['house']}:{m['district']}", []).append(m)
    people = {sid: person(holder(ms, day), term, current) for sid, ms in seats.items()}
    if not current:
        # A past session's member who still holds the seat is reached through today's contact form and offices.
        now = {f"{m['house']}:{m['district']}": m for m in C.members(current_term)}
        for sid, p in people.items():
            m = now.get(sid)
            if m and m["display"] == p["name"]:
                q = person(m, current_term, True)
                p.update({k: q[k] for k in ("form", "phone", "phones", "office")})
    comms = committees(term, current)
    leaders = {}
    for h, (last, role) in (P.OFFICERS.get(term) or {}).items():
        hit = [p for sid, p in people.items() if sid[0] == h and C.fold(p["dataName"]) == C.fold(last)]
        if len(hit) == 1:
            leaders[h] = {"name": hit[0]["name"], "role": role}
    return {"session": session, "fetched": datetime.now(ZoneInfo(P.TIMEZONE)).strftime("%Y-%m-%d %H:%M"),
            "people": people, "since": {}, "senateCommittees": comms["S"], "assemblyCommittees": comms["H"],
            "leaders": leaders, "assemblyMembers": {}, "kept": []}


def main(session):
    out = build(session)
    if len(out["people"]) < 150:
        raise SystemExit(f"{session}: only {len(out['people'])} legislators; kept the last contacts")
    path = os.path.join(P.DATA, f"contacts_{session}.json")
    with open(path, "w") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
    ppl = out["people"].values()
    print(f"{path}: {len(out['people'])} legislators ({sum(1 for p in ppl if p['form'])} with a contact form, "
          f"{sum(1 for p in ppl if p['phone'])} with a phone), {len(out['senateCommittees'])} Senate and "
          f"{len(out['assemblyCommittees'])} House committees, leaders {sorted(out['leaders'])}")


if __name__ == "__main__":
    for s in ([int(sys.argv[1])] if len(sys.argv) > 1 else C.sessions()):
        main(s)
