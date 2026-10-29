#!/usr/bin/env python3
"""Virginia's legislators, committees and leaders, from the two houses' own websites, written as
data/va/contacts_<session>.json in the shape build_data.py reads (as states/nj/contacts.py writes).

- House of Delegates: the member list (house.vga.virginia.gov/members: district, party, phones, email,
  the localities in the district, photo) and each committee's page (chair and members, by member id).
- Senate: the Senate's member spreadsheet (VAsen.xlsx: district, party, phones, address), its email list,
  and each senator's page (committees, marked "(Chair)", first year in the Senate, district localities).
Seat ids are "S:34" and "H:71". Usage: python3 states/va/contacts.py [session]
"""
import html, io, json, os, re, sys, time, urllib.request, zipfile
from datetime import datetime
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
from fetch_contacts import committee_key, name_key
from states.va import profile as P
from states.va.convert import rows

HOUSE_SITE = "https://house.vga.virginia.gov"
SENATE_SITE = "https://apps.senate.virginia.gov"
PARTY = {"D": "Democratic", "R": "Republican", "I": "Independent"}


def get(url, binary=False):
    req = urllib.request.Request(url, headers={"User-Agent": "statebilltracker.org data fetch"})
    with urllib.request.urlopen(req, timeout=60) as r:
        body = r.read()
    time.sleep(0.3)
    return body if binary else body.decode("utf-8", "replace")


def text(h):
    h = re.sub(r"(?is)<(script|style).*?</\1>", "", h)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", h))).strip()


def flip(name):
    """"Anderson, Jessica L." -> "Jessica L. Anderson"; "Sullivan, Richard C. (Rip), Jr." keeps the suffix."""
    parts = [p.strip() for p in name.split(",")]
    return " ".join([parts[1], parts[0]] + parts[2:]) if len(parts) > 1 else name


def house(session, lis_names):
    page = get(f"{HOUSE_SITE}/members")
    people, committees = {}, {}
    for card in re.split(r'<div\s+class="delegate-card', page)[1:]:
        mid = re.search(r'href="/members/(H\d+)"', card)
        search = re.search(r'data-search="([^"]*)"', card)
        district = re.search(r"District:</span>\s*(\d+)", card)
        if not (mid and search and district):
            continue
        mid, d = mid.group(1), int(district.group(1))
        name = lis_names.get(mid) or flip(re.search(r'alt="([^"]+)"', card).group(1))
        party = (re.search(r"^.*?\b\d+ ([dri]) \(", search.group(1)) or re.search(r"\s([dri])\s", search.group(1)))
        email = re.search(r"mailto:([^\"]+)", card)
        phones = [[label, num] for label, num in re.findall(r"(District|Capitol) Phone:</span>\s*(\(\d{3}\) \d{3}-\d{4})", card)]
        desc = re.search(r"Description:</span>\s*([^<]+)", card)
        people[f"H:{d}"] = {
            "name": name, "key": name_key(name), "id": mid,
            "party": PARTY.get(party.group(1).upper(), "") if party else "",
            "email": email.group(1).strip() if email else None,
            "phone": phones[0][1] if phones else None, "phones": phones,
            "url": f"{HOUSE_SITE}/members/{mid}", "image": f"{HOUSE_SITE}/delegate_photos/thumbs/{mid}.jpg",
            "office": "", "position": None, "places": desc.group(1).strip() if desc else "",
        }
    by_id = {p["id"]: p["name"] for p in people.values()}
    for code, (chamber, cname) in {r["COM_COMNO"]: (r["CHAMBER"], r["COM_NAME"]) for r in rows(session, "Committees.csv")}.items():
        if chamber != "H":
            continue
        cpage = get(f"{HOUSE_SITE}/committees/{code}")
        chair = re.search(r"Chair:</span>\s*([^<]+)</p>", cpage)
        members = list(dict.fromkeys(by_id[m] for m in re.findall(r'href="/members/(H\d+)"', cpage) if m in by_id))
        chair_name = flip(chair.group(1).strip()) if chair else None
        # The chair as the member list names them (it may spell a middle initial differently).
        chair_name = next((m for m in members if chair_name and name_key(m).split()[-1] == name_key(chair_name).split()[-1]), chair_name)
        committees[committee_key(cname)] = {"name": cname, "chair": chair_name, "meets": None, "members": members}
    return people, committees


def senate(session, lis_names):
    # The spreadsheet: district, party, phones, address.
    z = zipfile.ZipFile(io.BytesIO(get(f"{SENATE_SITE}/Portal/Resources/VAsen.xlsx", binary=True)))
    strings = [html.unescape(re.sub(r"<[^>]+>", "", s)) for s in re.findall(r"<si>(.*?)</si>", z.read("xl/sharedStrings.xml").decode(), re.S)]
    sheet = z.read("xl/worksheets/sheet1.xml").decode()
    table = []
    for row in re.findall(r"<row[^>]*>(.*?)</row>", sheet, re.S):
        cells = {}
        for ref, attrs, val in re.findall(r'<c r="([A-Z]+)\d+"([^>]*)>(?:<v>([^<]*)</v>)?', row):
            cells[ref] = strings[int(val)] if 't="s"' in attrs and val else (val or "")
        table.append(cells)
    head = {v: k for k, v in table[0].items()}
    col = lambda r, name: (r.get(head.get(name, ""), "") or "").strip()
    emails = {}
    for name, addr in re.findall(r"([A-Z][^<>@]{2,60}?)\s+(senator\w+@senate\.virginia\.gov)", text(get(f"{SENATE_SITE}/Senator/EmailListing.php"))):
        emails[name_key(name.strip()).split()[-1]] = addr
    # Each senator's page: committees, first year, the localities in the district.
    index = get(f"{SENATE_SITE}/Senator/index.php")
    pages = {}
    for sid in dict.fromkeys(re.findall(r"memberpage\.php\?id=(S\d+)", index)):
        t = text(get(f"{SENATE_SITE}/Senator/memberpage.php?id={sid}"))
        m = re.search(r"(?:Democrat|Republican|Independent), District (\d+)", t)
        if m:
            pages[int(m.group(1))] = (sid, t)
    people, members = {}, {}
    lis_by_last = {name_key(n).split()[-1]: n for i, n in lis_names.items() if i.startswith("S")}
    for r in table[1:]:
        if not col(r, "DISTRICT").isdigit():
            continue
        d, last = int(col(r, "DISTRICT")), col(r, "LASTNAME")
        name = lis_by_last.get(name_key(last).split()[-1]) or f'{col(r, "FIRSTNAME")} {last}'
        sid, page = pages.get(d, ("", ""))
        # The senator's own list ("Committees Local Government (Chair) Education and Health ... Biography"),
        # not the site's menu, which also says "Committees".
        comms = re.search(r"Committees ((?:(?!Committees ).)+?) Biography", page)
        since = re.search(r"Member of the Senate: (\d{4})", page)
        places = re.search(rf"District {d} Description (.+?) Studies and Commissions", page)
        phones = [["Capitol", col(r, "GABPHONE")]] if col(r, "GABPHONE") else []
        if col(r, "DISTRICTPHONE"):
            phones.append([col(r, "CITY") or "District", col(r, "DISTRICTPHONE")])
        people[f"S:{d}"] = {
            "name": name, "key": name_key(name), "id": sid,
            "party": PARTY.get(col(r, "PARTY")[:1], ""),
            "email": emails.get(name_key(name).split()[-1]),
            "phone": phones[0][1] if phones else None, "phones": phones,
            "url": f"{SENATE_SITE}/Senator/memberpage.php?id={sid}" if sid else None, "image": None,
            "office": " ".join(filter(None, [col(r, "ADDRESS1"), col(r, "ADDRESS2"), col(r, "CITY"), col(r, "ZIP")])),
            "position": None, "places": places.group(1).strip() if places else "",
            "_since": int(since.group(1)) if since else None,
            "_comms": comms.group(1) if comms else "",
        }
    committees = {}
    for code, (chamber, cname) in {r["COM_COMNO"]: (r["CHAMBER"], r["COM_NAME"]) for r in rows(session, "Committees.csv")}.items():
        if chamber != "S":
            continue
        on = [p["name"] for p in people.values() if cname in p["_comms"]]
        chair = next((p["name"] for p in people.values() if f"{cname} (Chair)" in p["_comms"]), None)
        committees[committee_key(cname)] = {"name": cname, "chair": chair, "meets": None, "members": sorted(on)}
    return people, committees


def build(session):
    lis_names = {r["MBR_MBRNO"]: re.sub(r"\s+", " ", r["MBR_NAME"]).strip() for r in rows(session, "Members.csv")}
    h_people, h_comms = house(session, lis_names)
    s_people, s_comms = senate(session, lis_names)
    since = {k: p.pop("_since") for k, p in s_people.items() if p.get("_since")}
    for p in s_people.values():
        p.pop("_comms", None)
        p.pop("_since", None)
    return {
        "session": session,
        "fetched": datetime.now(ZoneInfo(P.TIMEZONE)).strftime("%Y-%m-%d %H:%M ET"),
        "people": {**s_people, **h_people}, "since": since,
        "senateCommittees": s_comms, "assemblyCommittees": h_comms,
        "assemblyMembers": {}, "kept": [],
    }


def main(session):
    out = build(session)
    path = os.path.join(P.DATA, f"contacts_{session}.json")
    with open(path, "w") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
    print(f"{path}: {len(out['people'])} legislators ({sum(1 for p in out['people'].values() if p['email'])} with email, "
          f"{sum(1 for p in out['people'].values() if p['party'])} with party), {len(out['senateCommittees'])} Senate and "
          f"{len(out['assemblyCommittees'])} House committees "
          f"({sum(1 for c in list(out['senateCommittees'].values()) + list(out['assemblyCommittees'].values()) if c['chair'])} with a chair)")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else P.session_of(datetime.now(ZoneInfo(P.TIMEZONE)).year))
