#!/usr/bin/env python3
"""Hawaii's legislators, written as data/hi/contacts_<session>.json in the shape build_data.py reads, from Open States'
public-domain people file (data/hi/openstates_people.csv, saved by states/hi/fetch.py; the Legislature's own site turns
automated requests away). The file has each member's party, district, email and photo, but no phone numbers. Phones
(and an email the people file lacks) come from the Public Access Room's "Email, Room & Phone Directory", a text PDF the
Legislative Reference Bureau posts for each Legislature (lrb.hawaii.gov, a different host from capitol.hawaii.gov;
robots.txt bars only /wp-admin/): `directory()`. Its address changes with each edition, so it's read from the link on
the PAR's "Current Legislature" page (once a day; the PDF again only when the link changes). The directory names
members "Awa, Brenton" with no district; each is matched to a people-file member of the same house by email or by
surname and first name, so a member who sits in the same house in both Legislatures gets the phone while the people
file still lists the Legislature now sitting (the November 2026 edition is the 2027-28 Legislature's: a representative
elected to the Senate, Jackson Sayama, gets none until the people file moves him in January). The source's typos are
fixed ("@capitol.hawaii,gov").

Hawaii has 25 Senate and 51 House districts, one member each: seat ids "S:12", "H:12". Committees come from the bills'
histories: each standing committee of each house with the members who voted in it in the Legislature's latest year
(every committee vote is recorded member by member). The histories don't say who chairs a committee, so no chairs are
shown. A past Legislature's contacts are today's members. Usage: python3 states/hi/contacts.py [session]
"""
import json, os, re, subprocess, sys, time, unicodedata, urllib.request
from collections import defaultdict
from datetime import datetime
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
from fetch_contacts import committee_key, name_key
from states.hi import convert as C
from states.hi import profile as P


def committees(session):
    """(house, committee) -> member seats, from the committee votes of the Legislature's latest year that has any."""
    by_year = defaultdict(lambda: defaultdict(set))
    for key, y in C.keys(session):
        b = C.bill(y, key) or {}
        for a in b.get("actions") or []:
            t = C.text(a.get("description"))
            h = C.ORG.get((a.get("organization") or {}).get("classification"))
            m = re.match(r"The committee\(?s?\)? on\s+([A-Z]{2,4})\s+recommends?(?:\(s\))? that the measure be PASSED", t)
            if not h or not m:
                continue
            cv = C.committee_vote(t, h)
            if not cv:
                continue
            year = int(a["date"][:4])
            names = cv[3] + [n for n, _ in cv[2]]
            for n in names:
                by_year[year][(h, P.committee_name(m.group(1), year, h))].add(C.seat_of(session, h, n))
    if not by_year:
        return {}
    return by_year[max(by_year)]


PAR = "https://lrb.hawaii.gov/par/current-legislature/"
AGENT = "statebilltracker.org (a nonprofit bill tracker; contact via github.com/judithhubbard)"
DIRECTORY = os.path.join(P.DATA, "par_directory.json")


def _get(url):
    req = urllib.request.Request(url, headers={"User-Agent": AGENT})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def parse_directory(text):
    """The directory's text (pdftotext -layout) as [(house, "Last, First", email, phone digits)], from its "Senator" and
    "Representative" tables (the staff tables are skipped)."""
    out, house = [], None
    for line in text.splitlines():
        head = re.split(r"\s{2,}", line.strip())[0]
        if head in ("Senator", "Representative"):
            house = "S" if head == "Senator" else "H"
            continue
        if re.match(r"(?:Senate|House|Legislative) Staff\b", head):
            house = None
            continue
        m = re.match(r"\s*(.+?)\s{2,}(\S+@\S+)\s.*?(\(?808\)?[-. ]?\d{3}-\d{4})\s*$", line)
        if not house or not m:
            continue
        name, email, phone = m.groups()
        email = re.sub(r"@capitol\.hawaii[,;]gov$", "@capitol.hawaii.gov", email.strip().lower().rstrip(".,;"))
        name = re.sub(r"-\s+", "-", re.sub(r"\s+", " ", name)).strip()
        out.append((house, name, email, re.sub(r"\D", "", phone)[-10:]))
    return out


def directory():
    """The latest directory's members, as [[house, name, email, phone]] (data/hi/par_directory.json keeps them with the
    PDF's address and the day the page was last read). Any failure keeps the last copy."""
    try:
        saved = json.load(open(DIRECTORY))
    except (OSError, ValueError):
        saved = {}
    if saved.get("read") == time.strftime("%Y-%m-%d") and saved.get("entries"):
        return saved["entries"]
    try:
        page = _get(PAR).decode("utf-8", "replace")
        links = re.findall(r'href="(https://lrb\.hawaii\.gov/[^"]*Room-Phone-Email[^"]*\.pdf)"', page)
        if not links:
            raise ValueError("no directory link on the page")
        link = sorted(set(links))[-1]
        if link != saved.get("pdf") or not saved.get("entries"):
            r = subprocess.run(["pdftotext", "-layout", "-", "-"], input=_get(link), capture_output=True)
            text = r.stdout.decode("utf-8", "replace")
            entries = parse_directory(text)
            if len(entries) < 70:
                raise ValueError(f"only {len(entries)} members read from {link}")
            title = re.search(r"\S+ Hawaii State Legislature, \d{4}-\d{4}", text)
            saved = {"pdf": link, "title": title.group(0) if title else "", "entries": [list(e) for e in entries]}
            print(f"directory: {len(entries)} members from {link}")
        saved["read"] = time.strftime("%Y-%m-%d")
        with open(DIRECTORY + ".tmp", "w") as f:
            json.dump(saved, f, indent=1, ensure_ascii=False)
        os.replace(DIRECTORY + ".tmp", DIRECTORY)
    except (OSError, ValueError, subprocess.SubprocessError) as e:
        print(f"directory: {type(e).__name__}: {e}; kept the last copy")
    return saved.get("entries") or []


def _plain(s):
    s = unicodedata.normalize("NFKD", s or "")
    return re.sub(r"[^a-z ]", "", "".join(c for c in s if not unicodedata.combining(c)).lower().replace("-", " ")).strip()


def directory_match(p, h, entries, used):
    """The index of the directory entry for people-file member p of house h, or None: the same email, else the same
    surname (the directory's may be longer: "Keohokapu-Lee Loy" for Sue Lee Loy) and first name."""
    email = (p.get("email") or "").lower()
    for i, (eh, name, em, phone) in enumerate(entries):
        if eh == h and i not in used and email and em == email:
            return i
    fam, given = _plain(p.get("dataName")), _plain(p["name"]).split()
    for i, (eh, name, em, phone) in enumerate(entries):
        if eh != h or i in used or "," not in name:
            continue
        last, first = (_plain(x) for x in name.split(",", 1))
        last, first = re.sub(r"\b(?:jr|sr|ii|iii|iv)\b", "", last).strip(), first.split()
        if fam and given and first and (last == fam or last.endswith(" " + fam)) and (
                given[0] in first or first[0] in given):
            return i
    return None


def build(session):
    people = {}
    for h, seat, full, fam, given, party in C.people():
        people[seat] = {"name": full, "key": name_key(full), "id": None, "party": {"D": "Democratic", "R": "Republican"}.get(party, party),
                        "email": None, "form": None, "phone": None, "phones": [], "url": None, "image": None, "office": "",
                        "position": None, "places": f"District {seat.split(':')[1]}", "dataName": fam}
    import csv
    for r in csv.DictReader(open(os.path.join(P.DATA, "openstates_people.csv"), encoding="utf-8")):
        h = C.ORG.get(r.get("current_chamber"))
        if not h or not (r.get("current_district") or "").isdigit():
            continue
        p = people.get(f"{h}:{int(r['current_district'])}")
        if not p:
            continue
        links = [u for u in (r.get("links") or "").split(";") if u]
        p["email"] = r.get("email") or None
        p["url"] = next((u for u in links if "memberpage" in u and "year=" not in u), links[0] if links else None)
        # Photos hosted on the Legislature's own site are left out: test pages loading them would be automated requests
        # to a site that turns them away.
        img = r.get("image") or ""
        p["image"] = img.replace("http://", "https://") if img and "capitol.hawaii.gov" not in img else None
    entries, used = directory(), set()
    for sid, p in sorted(people.items()):
        i = directory_match(p, sid[0], entries, used)
        if i is None:
            continue
        used.add(i)
        d = entries[i][3]
        p["phone"] = f"{d[:3]}-{d[3:6]}-{d[6:]}"
        p["phones"] = [["Capitol", p["phone"]]]
        p["email"] = p["email"] or entries[i][2]
    comms = {"S": {}, "H": {}}
    for (h, name), seats in sorted(committees(session).items()):
        members = sorted(people[s]["name"] for s in seats if s in people)
        comms[h][committee_key(name)] = {"name": name, "chair": None, "meets": None, "members": members}
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
        if len(out["people"]) < 70:
            raise SystemExit(f"only {len(out['people'])} legislators; kept the last contacts")
        path = os.path.join(P.DATA, f"contacts_{session}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(out, f, indent=1, ensure_ascii=False)
        ppl = out["people"].values()
        print(f"{path}: {len(out['people'])} legislators ({sum(1 for p in ppl if p['email'])} with email, "
              f"{sum(1 for p in ppl if p['phone'])} with a phone), "
              f"{len(out['senateCommittees'])} Senate and {len(out['assemblyCommittees'])} House committees, leaders {sorted(out['leaders'])}")


if __name__ == "__main__":
    main([int(sys.argv[1])] if len(sys.argv) > 1 else C.sessions())
