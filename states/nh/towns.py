#!/usr/bin/env python3
"""Each New Hampshire town, city ward and unincorporated place, with its Senate and House districts, for "Where you live":
data/nh/district_towns.json: [["Laconia Ward 2", "Belknap", [[2, 100]], [[106, 100]]], ...]: place, county, Senate
district, House districts. Also data/nh/district_names.json: {"H": {"106": "Belknap 6", ...}}, the House districts'
names (their ids are the county's code times 100 plus the number, as in convert.seat_ids()).

From the law that sets the districts, on gc.nh.gov (robots.txt allowing; at its crawl delay): RSA 662:3 (State Senate
Districts, 2022), whose districts are lists of towns and of city wards ("wards 1, 2, and 5 in Nashua"), and RSA 662:5
(State Representative Districts, 2022), a table per county of each district's towns and wards and how many
representatives it elects. A place can be in two House districts at once: its own and a "floterial" district that
covers it and its neighbors (Belknap 8 is Belmont, Sanbornton and Tilton, which also have Belknap 3 and 4), and its
residents vote in both, so a place's House list is every district it's in, not a choice. (The General Court's
HouseDistricts.txt data file still has the 2012 map: Belknap has 9 districts there, 8 in the law and in the member
list. So it isn't used.) The table has a few slips: "Laconia Ward | 1" (the ward number in the count column) and
"Ossipee 1" (the count in the name column). The districts are fixed until the next redistricting (2032), so this is run
once and the files kept in git. Usage: python3 states/nh/towns.py
"""
import html, json, os, re, subprocess, sys, time
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
from states.nh import profile as P

AGENT = "statebilltracker.org (a nonprofit bill tracker; contact via github.com/judithhubbard)"
SENATE = "https://gc.nh.gov/rsa/html/LXIII/662/662-3.htm"
HOUSE = "https://gc.nh.gov/rsa/html/LXIII/662/662-5.htm"
COUNTIES = {"Belknap": 1, "Carroll": 2, "Cheshire": 3, "Coos": 4, "Grafton": 5, "Hillsborough": 6, "Merrimack": 7,
            "Rockingham": 8, "Strafford": 9, "Sullivan": 10}


def get(url):
    out = subprocess.run(["curl", "-sSf", "--max-time", "120", "-A", AGENT, url], capture_output=True, check=True).stdout
    time.sleep(11)  # gc.nh.gov's crawl delay
    return out.decode("utf-8", "replace")


def plain(x):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", x))).strip()


def house_districts(page):
    """[(county, district number, place)] from RSA 662:5's tables, one per county ("I. Belknap County")."""
    out = []
    for m in re.finditer(r"([A-Za-z]+) County\s*(?:<[^>]*>\s*)*<table>(.*?)</table>", page, re.S):
        county = m.group(1)
        if county not in COUNTIES:
            continue
        d, held = None, ""
        for row in re.findall(r"<tr[^>]*>(.*?)</tr>", m.group(2), re.S):
            cells = [plain(c) for c in re.findall(r"<td[^>]*>(.*?)</td>", row, re.S)]
            if len(cells) < 2:
                continue
            n = re.match(r"District No\.\s*(\d+)", cells[0])
            if n:
                d = int(n.group(1))
            name, count = held + cells[1], cells[2] if len(cells) > 2 else ""
            held = ""
            if name.endswith(" and"):  # "Thompson and" | "Meserve's Purchase": one name on two rows
                held = name + " "
                continue
            if re.search(r"\bWard$", name) and count.isdigit():
                name = f"{name} {count}"  # "Laconia Ward | 1": the ward's number in the count column
            name = re.sub(r"(?<!Ward)\s+\d+$", "", name)  # "Ossipee 1": the count in the name column
            name = re.sub(r"^([NSEW])\. ", lambda x: {"N": "North ", "S": "South ", "E": "East ", "W": "West "}[x.group(1)], name)
            if name and d:
                out.append((county, d, name))
    return out


def senate_districts(page):
    """Place -> Senate district, from RSA 662:3 ("Senatorial district number 12 is constituted of wards 1, 2, and 5 in
    Nashua, and Brookline, ..."); wards as "Nashua Ward 1"."""
    out = {}
    for m in re.finditer(r"Senatorial district number (\d+) is constituted of (.+?)\.\s*(?=[IVXL]+\.|Source|$)", plain(page)):
        d, rest = int(m.group(1)), m.group(2)
        for w in re.finditer(r"wards? ([\d, and]+?) in ([A-Z][A-Za-z' ]+?)(?=,|$)", rest):
            for k in re.findall(r"\d+", w.group(1)):
                out[f"{w.group(2).strip()} Ward {k}"] = d
        rest = re.sub(r"wards? [\d, and]+? in [A-Z][A-Za-z' ]+?(?=,|$)", "", rest)
        for name in re.split(r",\s*", rest):  # not on " and ": "Low and Burbank's Grant"
            name = re.sub(r"^and\s+", "", name.strip())
            if name:
                out[name] = d
    return out


def main():
    house_page, senate_page = get(HOUSE), get(SENATE)
    rows = house_districts(house_page)
    senate = senate_districts(senate_page)
    names = {}
    places = defaultdict(lambda: {"county": "", "H": []})
    for county, d, name in rows:
        did = COUNTIES[county] * 100 + d
        names[str(did)] = f"{county} {d}"
        p = places[name]
        p["county"] = county
        if did not in p["H"]:
            p["H"].append(did)
    out, missing = [], []
    for name, p in places.items():
        town = re.sub(r" Ward \d+$", "", name)
        s = senate.get(name) or senate.get(town)
        if not s:
            missing.append(name)
            continue
        out.append([name, p["county"], [[s, 100]], [[d, 100] for d in sorted(p["H"])]])
    # Towns the House table names only by ward share a Senate district per ward; check each place was found.
    if missing:
        print(f"no Senate district for: {', '.join(missing)}")
    out.sort(key=lambda r: [int(x) if x.isdigit() else x.lower() for x in re.split(r"(\d+)", r[0])])
    os.makedirs(P.DATA, exist_ok=True)
    json.dump(out, open(P.TOWNS_PATH, "w"), indent=0, ensure_ascii=False)
    json.dump({"H": names}, open(P.DISTRICT_NAMES_PATH, "w"), indent=0)
    print(f"{P.TOWNS_PATH}: {len(out)} places; {len(names)} House districts; "
          f"{sum(1 for r in out if len(r[3]) > 1)} places in a floterial district too; "
          f"{len(set(r[2][0][0] for r in out))} Senate districts")


if __name__ == "__main__":
    main()
