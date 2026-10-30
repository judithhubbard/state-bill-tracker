#!/usr/bin/env python3
"""California's legislators, committees and leaders, from the two houses' own websites, written as
data/ca/contacts_<session>.json in the shape build_data.py reads (as states/va/contacts.py writes).

- Senate: the senator list (www.senate.ca.gov/senators: district, party, Capitol and district offices with phones,
  contact form, website), each standing committee's members page (marked "(Chair)"), and the leadership page.
- Assembly: the member list (the Assembly's member-data API: name, district, party), each member's page (phones,
  website, contact form) and committees (the same API), and the leadership page.
Each member is tied to the name the Legislature's database uses for them (LEGISLATOR_TBL, by district), so bills
and votes find their seat. Seat ids are "S:21" and "A:30". Usage: python3 states/ca/contacts.py [session]
"""
import html, json, os, re, subprocess, sys, time
from datetime import datetime
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
from fetch_contacts import committee_key, name_key
from states.ca import profile as P
from states.ca.convert import committees, rows

SENATE = "https://www.senate.ca.gov"
ASSEMBLY = "https://www.assembly.ca.gov"
API = "https://webapi.assembly.ca.gov/member-data/api/v1/members"
FORM = "https://lcmspubcontact.lc.ca.gov/PublicLCMS/ContactPopup.php?district={}&inframe=N"
PARTY = {"D": "Democratic", "R": "Republican", "I": "Independent"}


def get(url):
    # curl: the Legislature's servers turn away Python's default client.
    for attempt in range(3):
        r = subprocess.run(["curl", "-sSfL", "--max-time", "60", url], capture_output=True)
        if r.returncode == 0:
            time.sleep(0.3)
            return r.stdout.decode("utf-8", "replace")
        time.sleep(3 * (attempt + 1))
    raise RuntimeError(f"{url}: {r.stderr.decode(errors='replace').strip()}")


def text(h):
    h = re.sub(r"(?is)<(script|style).*?</\1>", "", h)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", h))).strip()


def flip(name):
    """"Aguiar-Curry, Cecilia M." -> "Cecilia M. Aguiar-Curry"."""
    parts = [p.strip() for p in name.split(",")]
    return " ".join([parts[1], parts[0]] + parts[2:]) if len(parts) > 1 else name


def phone_of(s):
    m = re.search(r"\(\d{3}\) ?\d{3}-\d{4}", s or "")
    return m.group(0).replace(") ", ")").replace(")", ") ") if m else None


def data_names(session):
    """Seat -> the name the database uses ("A:30" -> "Addis"), for the current members."""
    out = {}
    for r in rows(session, "LEGISLATOR"):
        if r[3] in ("A", "S") and r[4] and r[13] != "N" and r[15] != "N":
            out[f"{r[3]}:{int(r[0][2:])}"] = r[4]
    return out


def senate(session):
    page = get(f"{SENATE}/senators")
    people = {}
    for card in re.split(r'<div class="page-members__member"', page)[1:]:
        d = re.search(r'data-district="(\d+)"', card)
        name = re.search(r'<h3 class="member__name"[^>]*>([^<]+)</h3>', card)
        if not (d and name) or "Vacant" in name.group(1):
            continue
        d = int(d.group(1))
        party = re.search(r'data-party="([DRI])"', card)
        home = re.search(r'href="([^"]+)"[^>]*>Homepage<', card)
        img = re.search(r'data-src="([^"]+)"', card)
        offices = re.findall(r'<h4 class="member__office-title">([^<]+)</h4>\s*<p class="member__address">([^<]+)</p>', card)
        phones = []
        for title, addr in offices:
            n = phone_of(addr)
            if n:
                town = "Capitol" if "Capitol" in title else (re.search(r",\s*([A-Za-z .]+), CA \d{5}", addr) or [None, "District"])[1].strip()
                phones.append([town, n])
        people[f"S:{d}"] = {
            "name": html.unescape(name.group(1)).strip(), "id": f"SD{d:02d}",
            "party": PARTY.get(party.group(1) if party else "", ""), "email": None, "form": FORM.format(f"SD{d:02d}"),
            "phone": phones[0][1] if phones else None, "phones": phones,
            "url": home.group(1) if home else None,
            "image": (SENATE + img.group(1)) if img and img.group(1).startswith("/") else None,
            "office": html.unescape(offices[0][1]).split(";")[0].strip() if offices else "", "position": None, "places": "",
        }
    # Each standing committee's members page.
    comm_page = get(f"{SENATE}/committees")
    i = comm_page.find('id="Standing-Committees-header"')
    j = comm_page.find("<h2", i + 10)
    by_district = {int(k[2:]): p["name"] for k, p in people.items()}
    comms = {}
    for url, cname in re.findall(r'<a\s+href="(https?://[a-z0-9]+\.senate\.ca\.gov/?)">([^<]+)</a>', comm_page[i:j]):
        cname = html.unescape(cname).strip()
        try:
            members = text(get(url.rstrip("/") + "/members"))
        except RuntimeError as e:
            print(f"  {cname}: {e}", file=sys.stderr)
            continue
        on, chair = [], None
        for who, role, d in re.findall(r"([A-Z][\w.'’ -]+?) (?:\((Chair|Vice Chair)\) )?(?:Dem|Rep|Ind) - (\d+)", members):
            n = by_district.get(int(d))
            if n and n not in on:
                on.append(n)
                if role == "Chair":
                    chair = n
        comms[committee_key(cname)] = {"name": cname, "chair": chair, "meets": None, "members": sorted(on)}
    lead = text(get(f"{SENATE}/leadership"))
    leaders = {}
    m = re.search(r"President pro Tempore District (\d+)", lead)
    if m and f"S:{int(m.group(1))}" in people:
        people[f"S:{int(m.group(1))}"]["position"] = "Senate President pro Tempore"
        leaders["S"] = {"name": people[f"S:{int(m.group(1))}"]["name"], "role": "Senate President pro Tempore"}
    m = re.search(r"Majority Floor Leader District (\d+)", lead)
    if m and f"S:{int(m.group(1))}" in people:
        people[f"S:{int(m.group(1))}"]["position"] = "Senate Majority Leader"
    m = re.search(r"Minority Leader District (\d+)", lead)
    if m and f"S:{int(m.group(1))}" in people:
        people[f"S:{int(m.group(1))}"]["position"] = "Senate Minority Leader"
    return people, comms, leaders


def assembly(session):
    listing = get(API)
    people, roles = {}, {}
    for card in re.split(r'<li class="members-list__member"', listing)[1:]:
        name = re.search(r'data-name="([^"]+)"', card)
        d = re.search(r'data-district="(\d+)"', card)
        if not (name and d) or "Vacant" in name.group(1):
            continue
        d = int(d.group(1))
        party = re.search(r'data-party="(\w+)"', card)
        img = re.search(r'<img src="([^"]+)"', card)
        page = get(f"{ASSEMBLY}/assemblymembers/{d:02d}")
        site = re.search(r'href="(https?://(?:a|ad)\d+\.asm[dr]c\.org/?)"', page)
        # Office cards: a heading (the town), the address, and a phone.
        phones = []
        for sec, body in re.findall(r"<h2[^>]*>(Capitol Offices|District Offices)</h2>(.*?)</section>", page, re.S):
            for town, n in re.findall(r'card-header">([^<]+)</h3>.*?card-phone">\s*([^<]+?)\s*</p>', body, re.S):
                ph = ["Capitol" if sec.startswith("Capitol") else html.unescape(town).strip(), phone_of(n) or n]
                if ph not in phones:
                    phones.append(ph)
        try:
            roles[d] = get(f"{API}/{d}/committees")
        except RuntimeError:
            roles[d] = ""
        people[f"A:{d}"] = {
            "name": flip(html.unescape(name.group(1))), "id": f"AD{d:02d}",
            "party": {"Democrat": "Democratic", "Republican": "Republican"}.get(party.group(1) if party else "", "Independent" if party else ""),
            "email": None, "form": FORM.format(f"AD{d:02d}"),
            "phone": phones[0][1] if phones else None, "phones": phones,
            "url": site.group(1) if site else f"{ASSEMBLY}/assemblymembers/{d:02d}",
            "image": img.group(1) if img else None, "office": "", "position": None, "places": "",
        }
    # Standing committees and each member's role on them.
    comms = {}
    for d, frag in roles.items():
        std = re.search(r"Standing Committees</h3>(.*?)</section>", frag, re.S)
        for role, cname in re.findall(r"<p>\s*([^<]+?)\s*</p>\s*<a [^>]*>([^<]+)</a>", std.group(1) if std else ""):
            cname = html.unescape(cname).strip()
            c = comms.setdefault(committee_key(cname), {"name": cname, "chair": None, "meets": None, "members": []})
            c["members"].append(people[f"A:{d}"]["name"])
            if role == "Chair":
                c["chair"] = people[f"A:{d}"]["name"]
    for c in comms.values():
        c["members"].sort()
    lead = text(get(f"{ASSEMBLY}/assemblymembers/leadership"))
    leaders = {}
    m = re.search(r"Speaker: Honorable ([^:]+?) Speaker pro Tempore", lead)
    if m:
        who = next((k for k, p in people.items() if name_key(p["name"]).split()[-1] == name_key(m.group(1)).split()[-1]
                    and name_key(p["name"]).split()[0] == name_key(m.group(1)).split()[0]), None)
        if who:
            people[who]["position"] = "Assembly Speaker"
            leaders["A"] = {"name": people[who]["name"], "role": "Assembly Speaker"}
    return people, comms, leaders


def build(session):
    names = data_names(session)
    s_people, s_comms, s_lead = senate(session)
    a_people, a_comms, a_lead = assembly(session)
    people = {**s_people, **a_people}
    for sid, p in people.items():
        # Degrees aren't part of the name ("Dr. Darshana R. Patel", "Akilah Weber Pierson, M.D.").
        p["name"] = re.sub(r"^Dr\.\s+|,?\s+(?:M\.D\.|Ph\.D\.|Ed\.D\.|J\.D\.)$", "", p["name"]).strip()
        p["key"] = name_key(p["name"])
        p["dataName"] = names.get(sid)
    # The committees the bills name (LOCATION_CODE_TBL) should match the sites' names.
    known = {committee_key(n) for h, n in committees(session).values()}
    for c in list(s_comms) + list(a_comms):
        if c not in known:
            print(f"  committee not in the bill data: {(s_comms.get(c) or a_comms.get(c))['name']}", file=sys.stderr)
    return {
        "session": session,
        "fetched": datetime.now(ZoneInfo(P.TIMEZONE)).strftime("%Y-%m-%d %H:%M PT"),
        "people": people, "since": {},
        "senateCommittees": s_comms, "assemblyCommittees": a_comms, "leaders": {**s_lead, **a_lead},
        "assemblyMembers": {}, "kept": [],
    }


def main(session):
    out = build(session)
    path = os.path.join(P.DATA, f"contacts_{session}.json")
    with open(path, "w") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
    ppl = out["people"].values()
    print(f"{path}: {len(out['people'])} legislators ({sum(1 for p in ppl if p['phone'])} with a phone, "
          f"{sum(1 for p in ppl if p['party'])} with party, {sum(1 for p in ppl if p['dataName'])} tied to the bill data), "
          f"{len(out['senateCommittees'])} Senate and {len(out['assemblyCommittees'])} Assembly committees "
          f"({sum(1 for c in list(out['senateCommittees'].values()) + list(out['assemblyCommittees'].values()) if c['chair'])} with a chair)")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else P.session_of(datetime.now(ZoneInfo(P.TIMEZONE)).year))
