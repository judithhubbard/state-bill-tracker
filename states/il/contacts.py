#!/usr/bin/env python3
"""Illinois's legislators and committees, from the General Assembly's own member and committee files (downloaded
by states/il/fetch.py into data/il/<GA>/), written as data/il/contacts_<session>.json in the shape build_data.py
reads. The files have each member's name, party, district and Capitol and district phones (no email), and each
committee's members with the chairperson. Seat ids are "S:5" and "H:103". Usage: python3 states/il/contacts.py [session]
"""
import html, json, os, re, sys
from datetime import datetime
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
from fetch_contacts import committee_key, name_key
from states.il import profile as P

PARTY = {"D": "Democratic", "R": "Republican", "I": "Independent"}
FIND = "https://www.elections.il.gov/ElectionOperations/DistrictLocator.aspx"


def field(block, tag):
    m = re.search(rf"<{tag}>([^<]*)</{tag}>", block)
    return re.sub(r"\s+", " ", html.unescape(m.group(1))).strip() if m else ""


def people_of(path, h):
    out = {}
    for m in re.findall(r"<Member>(.*?)</Member>", open(path, encoding="utf-8-sig").read(), re.S):
        name, d = field(m, "Name"), field(m, "District")
        if not (name and d.isdigit()):
            continue
        phones = []
        for part, label in (("CapitolAddress", "Capitol"), ("DistrictAddress", None)):
            block = re.search(rf"<{part}>(.*?)</{part}>", m, re.S)
            n = field(block.group(1), "PhoneNumber") if block else ""
            n = re.match(r"\(?\d{3}\)?[\s-]?\d{3}-\d{4}", n)
            if n:
                num = re.sub(r"\(?(\d{3})\)?[\s-]?(\d{3})-(\d{4})", r"(\1) \2-\3", n.group(0))
                if num not in [x[1] for x in phones]:
                    phones.append([label or field(block.group(1), "City") or "District", num])
        sid = f"{h}:{int(d)}"
        out[sid] = {
            "name": name, "key": name_key(name), "id": sid, "party": PARTY.get(field(m, "Party")[:1], ""),
            "email": None, "form": None, "phone": phones[0][1] if phones else None, "phones": phones,
            "url": None, "image": None, "office": "", "position": None, "places": "", "dataName": name,
        }
    return out


def committees_of(path):
    out = {}
    for c in re.findall(r"<Committee>(.*?)</Committee>", open(path, encoding="utf-8-sig").read(), re.S):
        cname = field(c, "Name")
        members = [(field(m, "Name"), field(m, "Title")) for m in re.findall(r"<Member>(.*?)</Member>", c, re.S)]
        out[committee_key(cname)] = {"name": cname, "chair": next((n for n, t in members if t in ("Chairperson", "Chair")), None),
                                     "meets": None, "members": sorted(n for n, _ in members)}
    return out


def build(session):
    ga = P.assembly_of(session)
    base = os.path.join(P.DATA, str(ga))
    people = {**people_of(os.path.join(base, f"{ga}SenateMembers.xml"), "S"),
              **people_of(os.path.join(base, f"{ga}HouseMembers.xml"), "H")}
    s_comms = committees_of(os.path.join(base, f"{ga}SenateCommitteeMembers.xml"))
    h_comms = committees_of(os.path.join(base, f"{ga}HouseCommitteeMembers.xml"))
    leaders = {}
    for h, (name, role, _) in P.LEADERS.items():
        hit = next((p for sid, p in people.items() if sid[0] == h and p["key"] == name_key(name)), None)
        if hit:
            hit["position"] = role
            leaders[h] = {"name": hit["name"], "role": role}
    return {"session": session, "fetched": datetime.now(ZoneInfo(P.TIMEZONE)).strftime("%Y-%m-%d %H:%M CT"),
            "people": people, "since": {}, "senateCommittees": s_comms, "assemblyCommittees": h_comms,
            "leaders": leaders, "assemblyMembers": {}, "kept": []}


def main(session):
    out = build(session)
    path = os.path.join(P.DATA, f"contacts_{session}.json")
    json.dump(out, open(path, "w"), indent=1, ensure_ascii=False)
    ppl = out["people"].values()
    print(f"{path}: {len(out['people'])} legislators ({sum(1 for p in ppl if p['phone'])} with a phone, "
          f"{sum(1 for p in ppl if p['party'])} with party), {len(out['senateCommittees'])} Senate and "
          f"{len(out['assemblyCommittees'])} House committees, leaders {sorted(out['leaders'])}")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else P.session_of(datetime.now(ZoneInfo(P.TIMEZONE)).year))
