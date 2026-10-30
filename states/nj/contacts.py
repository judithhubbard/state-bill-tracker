#!/usr/bin/env python3
"""New Jersey's legislators, committees and leaders, from the session's roster files, written as
data/nj/contacts_<session>.json in the shape build_data.py reads (as New York's fetch_contacts.py writes).

Usage: python3 states/nj/contacts.py [session]   (default: the current session; fetch.py runs it)
The roster file has phone numbers and offices; each legislator's email address and contact form come from
the Legislature's website (one small request each), and are kept from the last copy when a request fails.
"""
import json, os, re, sys, time, urllib.request, zipfile
from datetime import datetime
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
from fetch_contacts import committee_key, name_key
from states.nj import profile as P
from states.nj.convert import _rows, person, seat_ids
from states.nj.convert import name_key as roster_key

PARTY = {"D": "Democratic", "R": "Republican"}
BIO_API = "https://www.njleg.gov/api/legislatorData/legislatorBio/{}"


def reach(roster_key):
    """A legislator's email address and contact form, from the Legislature's website (None, None on failure)."""
    try:
        with urllib.request.urlopen(BIO_API.format(roster_key), timeout=20) as r:
            bio = json.load(r)[0][0]
    except Exception:
        return None, None
    email = (bio.get("ccMailName") or "").strip()
    form = (bio.get("ContactLink") or "").strip()
    return (email if re.fullmatch(r"[\w.+-]+@[\w-]+(\.[\w-]+)+", email) else None,
            form if form.startswith("https://") else None)


def build(session):
    z = zipfile.ZipFile(os.path.join(P.DATA, f"DB{session}_TEXT.zip"))
    path = os.path.join(P.DATA, f"contacts_{session}.json")
    old = {v["url"]: v for v in json.load(open(path))["people"].values()} if os.path.exists(path) else {}
    seats = seat_ids(z)
    bios = {r["Roster Key"]: r for r in _rows(z, "LEGBIO.TXT")}
    people, since, names = {}, {}, {}
    for r in _rows(z, "ROSTER.TXT"):
        sid = seats[(r["House"],) + roster_key(r["LastName"], r["Firstname"])]
        # Titles and degrees ("Esq.", "M.D.") aren't part of the name (they'd end up in their page's address).
        suffix = re.sub(r"\s*\b(Esq\.|M\.D\.|Ph\.D\.|Ed\.D\.)", "", r["Suffix"] or "").strip()
        name = " ".join(filter(None, [r["Firstname"], r["MidName"], r["LastName"], suffix]))
        title = "senator" if r["House"] == "S" else "assemblywoman" if r["Sex"] == "F" else "assemblyman"
        office = f'{r["City"]} office' if r["City"] else "District office"
        bio = bios.get(r["Roster Key"], {})
        url = f'https://www.njleg.gov/legislative-roster/{r["Roster Key"]}/{title}-{re.sub(r"[^a-z]+", "-", r["LastName"].lower()).strip("-")}'
        email, form = reach(r["Roster Key"])
        time.sleep(0.2)
        if not (email or form):
            email, form = old.get(url, {}).get("email"), old.get(url, {}).get("form")
        people[sid] = {
            "name": name, "key": name_key(name), "party": PARTY.get(r["Party"], r["Party"]),
            "email": email, "form": form,
            "phone": r["Phone"] or None, "phones": [[r["City"] or "Office", r["Phone"]]] if r["Phone"] else [],
            "url": url,
            "image": (bio.get("URLPicture") or "").replace("http://", "https://") or None,
            "office": " ".join(filter(None, [r["Address"], r["City"], r["State"], r["Zipcode"]])),
            "position": r["LegPos"] or None,
        }
        # When they began serving in their current house ("General Assembly 2010-2021, Senate 2022-present").
        m = re.search((r"Senate" if r["House"] == "S" else r"General Assembly") + r" (\d{4})-present", bio.get("LegService") or "")
        if m:
            since[sid] = int(m.group(1))
        names[(r["House"],) + roster_key(r["LastName"], r["Firstname"])] = name
    houses = {}
    for r in _rows(z, "COMMITTEE.TXT"):
        if r["House"] in ("S", "A") and r["Type"].startswith("Standing"):
            houses[r["Code"]] = (r["House"], r["Description"])
    committees = {"S": {}, "A": {}}
    for r in _rows(z, "COMEMBER.TXT"):
        if r["Code"] not in houses:
            continue
        house, desc = houses[r["Code"]]
        last, _, first = r["Member"].partition(",")
        who = names.get((house,) + roster_key(last, first.strip())) or person(r["Member"])
        c = committees[house].setdefault(committee_key(desc), {"name": desc, "chair": None, "meets": None, "members": []})
        c["members"].append(who)
        if r["Position_on_Committee"] == "C":
            c["chair"] = who
    return {
        "session": session,
        "fetched": datetime.now(ZoneInfo(P.TIMEZONE)).strftime("%Y-%m-%d %H:%M ET"),
        "people": people, "since": since,
        "senateCommittees": committees["S"], "assemblyCommittees": committees["A"],
        "assemblyMembers": {}, "kept": [],
    }


def main(session):
    out = build(session)
    path = os.path.join(P.DATA, f"contacts_{session}.json")
    with open(path, "w") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
    print(f"{path}: {len(out['people'])} legislators ({sum(1 for p in out['people'].values() if p['email'])} with email), {len(out['senateCommittees'])} Senate and "
          f"{len(out['assemblyCommittees'])} Assembly committees")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else P.session_of(datetime.now(ZoneInfo(P.TIMEZONE)).year))
