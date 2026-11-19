"""Party control in past years, for the front page map's "Party control" view of 2023, 2024 and 2025 (today's comes from
each state's member list, balance.py; next year's from the 2026 election, front_page.next_data()). Writes
states/party_history.json: {"2023": {"_asOf": "2023-05-22", st: {dots, title}, ...}, ...}, in front_page.map_data()'s
shape, which build_site.sh puts on the front page for the states built in that run. Past years don't change, so this
rarely needs a re-run.

Each year is one day mid-session (`NCSL`'s dates: March 1, 2024; May 22, 2023 and April 30, 2025, the nearest to March 1
that NCSL published). Sources:
- State legislatures: the National Conference of State Legislatures' "State & Legislative Partisan Composition" tables
  for those days (each chamber's Democrats, Republicans, others and vacancies; PDFs read with pdftotext).
- Congress: the congress-legislators data (public domain; data/us/members/legislators-{current,historical}.json,
  downloaded by states/us/fetch.py): each member's terms with dates and party; independents count with the party they
  caucus with.
- Governors and the President: each profile's GOVERNORS (who held office that day) and the party below for those who
  have since left (states/legislatures.json has today's); checked against NCSL's governor column.
The Open States people archive (https://github.com/openstates/people, public domain) was the first choice for the
legislatures, but its roles have too many slips for seat counts (members who moved from the House to the Senate shown
in the Senate for their House years, placeholder end dates, missing members: Montana's Senate came to 58 of 50 seats,
Maine's 34 of 35 with the wrong split, New Hampshire's 26 of 24). With a path to a copy of it, this compares each chamber
on the same day and prints where the two differ (`--check`).

Usage: python3 party_history.py [--check PATH_TO_OPENSTATES_PEOPLE]
"""
import glob, importlib, json, math, os, re, subprocess, sys, tempfile
from datetime import date, timedelta
from collections import Counter
from fractions import Fraction

from balance import party_letter, table
from front_page import ADJ, WORD

HERE = os.path.dirname(os.path.abspath(__file__))
# NCSL's partisan composition tables: the day each counts, and where it is.
NCSL = {
    2023: ("2023-05-22", "https://documents.ncsl.org/wwwncsl/About-State-Legislatures/2023%20May%20State%20&%20Legislative%20Partisan%20Composi_Adam%20Kuckuk.pdf"),
    2024: ("2024-03-01", "https://documents.ncsl.org/wwwncsl/About-State-Legislatures/Legis-Control-2024-3-1-24.pdf"),
    2025: ("2025-04-30", "https://documents.ncsl.org/wwwncsl/Elections/Legis_Control_2025_4.30.25.pdf"),
}
YEARS = sorted(NCSL)

# Governors (and Presidents) who held office on a March 1 of 2023-2025 and have since left: their parties.
# legislatures.json gives the party of the one serving now.
PAST_PARTY = {
    "de": {"Carney": "D"}, "in": {"Holcomb": "R"}, "la": {"Edwards": "D"}, "mo": {"Parson": "R"}, "nc": {"Cooper": "D"},
    "nd": {"Burgum": "R"}, "nh": {"Sununu": "R"}, "nj": {"Murphy": "D"}, "sd": {"Noem": "R"}, "va": {"Youngkin": "R"},
    "wa": {"Inslee": "D"}, "wv": {"Justice": "R"}, "us": {"Biden": "D", "Trump": "R"},
    # Governors whose terms end in December 2026 or January 2027 (governors.py switches on the successor's first day).
    "ak": {"Dunleavy": "R"}, "al": {"Ivey": "R"}, "ca": {"Newsom": "D"}, "co": {"Polis": "D"}, "fl": {"DeSantis": "R"}, "ga": {"Kemp": "R"},
    "ia": {"Reynolds": "R"}, "ks": {"Kelly": "D"}, "me": {"Mills": "D"}, "mi": {"Whitmer": "D"}, "mn": {"Walz": "D"}, "nm": {"Lujan Grisham": "D"},
    "nv": {"Lombardo": "R"}, "oh": {"DeWine": "R"}, "ok": {"Stitt": "R"}, "ri": {"McKee": "D"}, "sc": {"McMaster": "R"}, "tn": {"Lee": "R"},
    "tx": {"Abbott": "R"}, "wi": {"Evers": "D"}, "wy": {"Gordon": "R"},
}

# Chambers a coalition ran (legislatures.json's `coalition` is today's): both of Alaska's houses since 2023 (in 2023-24
# a bipartisan Senate majority of 9 Democrats and 8 Republicans, and a Republican-led House majority with rural
# Democrats and independents; from memory, unchecked); Minnesota's House, tied 67-67 in 2025 under a power-sharing
# agreement.
COALITION = {2023: {"ak": ["S", "H"]}, 2024: {"ak": ["S", "H"]}, 2025: {"ak": ["S", "H"], "mn": ["H"]}}

# Chambers whose seat counts don't show who ran them: Michigan's House in March 2024, 54-54 with two seats vacant after
# two Democrats resigned in November 2023 (both won city offices), which the Democrats kept running (the Speaker,
# committees) until special elections in April 2024 filled the seats.
CONTROL = {2024: {"mi": {"H": "D"}}}

# The House's non-voting delegates and Resident Commissioner (not counted, as balance.py leaves them out today).
TERRITORIES = {"DC", "PR", "GU", "VI", "AS", "MP"}


def unquote(s):
    """A YAML scalar: double-quoted ones may hold escapes like \\xE1 (á)."""
    s = s.strip()
    if s.startswith('"'):
        return s[1:-1].encode("latin-1", "backslashreplace").decode("unicode_escape")
    return s.strip("'")


def parse(text):
    """The party and roles lists of an Open States person file (plain YAML, no library needed): each list item's
    keys, whatever order they come in."""
    person, section, item = {"party": [], "roles": []}, None, None
    for line in text.splitlines():
        m = re.match(r"^(\w+):\s*(.*)$", line)
        if m:
            section, item = m.group(1), None
            if section == "name":
                person["name"] = unquote(m.group(2))
            continue
        m = re.match(r"^(- |  )(\w+):\s*(.*)$", line)
        if m and section in ("party", "roles"):
            if m.group(1) == "- ":
                item = {}
                person[section].append(item)
            if item is not None:
                item[m.group(2)] = unquote(m.group(3))
    return person


def held(start, end, day):
    """Whether a role or term with these dates (YYYY-MM-DD, either may be missing) was held on a day."""
    return (not start or start[:10] <= day) and (not end or end[:10] >= day)


def days(a, b):
    """Days from date a to date b (YYYY-MM-DD)."""
    return (date.fromisoformat(b[:10]) - date.fromisoformat(a[:10])).days


# Party switches the archive records without dates (it gives only the party held now): before the day given, the
# member was of the other party. From news reports, as remembered (the NC pair from NC's own 2023 member list,
# data/nc/2023/members.json and NCSL's April 2025 table count them as Democrats; the 2025-26 list says unaffiliated).
SWITCHED = {
    "nc": {"Tricia Cotham": ("2023-04-05", "Democratic"), "Carla Cunningham": ("2025-05-01", "Democratic"),
           "Nasif Majeed": ("2025-05-01", "Democratic")},
    "ga": {"Mesha Mainor": ("2023-07-11", "Democratic")},
    "ca": {"Marie Alvarado-Gil": ("2024-08-07", "Democratic")},
}


def party_on(person, day, state=""):
    """A person's party on a day: the entry whose dates cover it, else the last one listed."""
    switched = SWITCHED.get(state, {}).get(person.get("name"))
    if switched and day < switched[0]:
        return switched[1]
    parties = person["party"]
    return next((p["name"] for p in parties if held(p.get("start_date"), p.get("end_date"), day)),
                parties[-1]["name"] if parties else "")


def state_counts(root, state, seats, day):
    """{chamber letter: Counter of party letters} for the legislators holding a seat on a day, and who they were
    ({chamber: [(district, name, party, start, end)]}, for checking).

    The archive has slips this works around: a member who moved from one house to the other often has their years in
    the old house typed as the new house, ending a day or two before the new role starts (SD's Sue Peterson, WA's Mike
    Chapman), or copied into the new house beside the real role (WA's Marcus Riccelli, NH's David Rochefort). Such roles
    are suspects: a district holding more members than it has seats that day keeps the others, and a suspect who has no
    other place there goes to the other house (district unknown). Montana splits real Senate terms the same way, which
    is why a suspect moves only when its district is over-full."""
    lower = next((c for c in seats if c != "S"), "L")
    other = {"S": lower, lower: "S"}
    folder = os.path.join(root, "data", state)
    files = [parse(open(path, encoding="utf-8").read()) for path in
             glob.glob(os.path.join(folder, "legislature", "*.yml")) + glob.glob(os.path.join(folder, "retired", "*.yml"))]
    # An end date of January 1 is often a placeholder for "left sometime" (NC's Ashton Clemmons, "2024-01-01", served
    # until her successor took the seat in August 2024): such a role runs until the next member in its seat starts,
    # when that's one to twelve months later (a successor starting days later, at a new term, means the date was real).
    starts = {}
    for p in files:
        for r in p["roles"]:
            if r.get("start_date"):
                starts.setdefault((r.get("type"), r.get("district")), []).append(r["start_date"][:10])
    for p in files:
        for r in p["roles"]:
            end = (r.get("end_date") or "")[:10]
            if end.endswith("-01-01"):
                later = [d for d in starts.get((r.get("type"), r.get("district")), []) if d > end]
                if later and 30 < days(end, min(later)) <= 366:
                    r["end_date"] = (date.fromisoformat(min(later)) - timedelta(days=1)).isoformat()
    people = []  # [person, {(chamber, district): suspect}]
    for p in files:
        roles = [({"upper": "S", "lower": lower, "legislature": lower}.get(r.get("type")), r) for r in p["roles"]]
        roles = [(c, r) for c, r in roles if c]
        now = [(c, r) for c, r in roles if held(r.get("start_date"), r.get("end_date"), day)]
        if not now:
            continue
        options = {}
        for c, r in now:
            suspect = lower != "L" and (len(now) > 1 or bool(r.get("end_date")) and any(
                c2 == c and r2 is not r and r2.get("start_date") and 0 <= days(r["end_date"], r2["start_date"]) <= 2
                for c2, r2 in roles))
            key = (c, r.get("district"))
            options[key] = options.get(key, True) and suspect
        people.append([p, options])
    # The most members a district has in each house (New Hampshire's House districts have up to 10): seats over
    # districts, rounded up.
    districts = {c: {d for _, opts in people for c2, d in opts if c2 == c} for c in seats}
    cap = {c: math.ceil(n / max(1, len(districts[c]))) for c, n in seats.items()}
    holders, chosen = Counter(), {}
    for i, (p, opts) in sorted(enumerate(people), key=lambda x: len(x[1][1])):
        if len(opts) == 1:
            chosen[i] = next(iter(opts))
        else:
            chosen[i] = min(opts, key=lambda k: (holders[k] >= cap[k[0]], opts[k], holders[k] / cap[k[0]], k[0] == "S"))
        holders[chosen[i]] += 1
    # Over-full districts: their suspects (latest first) go to the other house until the district fits.
    for place in [k for k, n in holders.items() if n > cap[k[0]]]:
        for i in sorted((i for i, k in chosen.items() if k == place and people[i][1][k]), key=lambda i: people[i][0].get("name", "")):
            if holders[place] <= cap[place[0]]:
                break
            holders[place] -= 1
            chosen[i] = (other[place[0]], "?")
    counts, who = {}, {}
    for i, (c, d) in chosen.items():
        p = people[i][0]
        letter = party_letter(party_on(p, day, state))
        counts.setdefault(c, Counter())[letter] += 1
        who.setdefault(c, []).append((d or "", p.get("name", ""), letter))
    return counts, who


def congress_counts(day):
    """Congress's seats by party on a day, from congress-legislators' terms; independents count with their caucus."""
    counts = {"S": Counter(), "H": Counter()}
    for name in ("legislators-current.json", "legislators-historical.json"):
        path = os.path.join(HERE, "data", "us", "members", name)
        for person in json.load(open(path)):
            for t in person.get("terms", []):
                if t["type"] == "rep" and t["state"] in TERRITORIES:
                    continue
                if held(t.get("start"), t.get("end"), day):
                    counts["S" if t["type"] == "sen" else "H"][party_letter(t.get("caucus") or t.get("party"))] += 1
                    break
    return counts, {}


def governor_party(state, facts, day):
    """The party of whoever was governor (or President) on a day, from the profile's GOVERNORS."""
    P = importlib.import_module(f"states.{state}.profile")
    who = None
    for name, start in P.GOVERNORS:
        if day >= start:
            who = name
    import governors
    if who == governors.in_office(P, day)[0] and who == governors.in_office(P)[0]:
        return governors.facts_governor(facts)[1]
    return PAST_PARTY[state][who]  # a KeyError here: add the governor's party above


def ncsl(year, facts_all):
    """{state: ({chamber: Counter of party letters}, governor's party)} from NCSL's table for a year. Its "other" columns
    hold others ("1") and vacancies ("2v", "2, 4v"); a vacancy isn't counted."""
    path = os.path.join(tempfile.gettempdir(), f"ncsl_partisan_{year}.pdf")
    if not os.path.exists(path):
        subprocess.run(["curl", "-sSfL", "-o", path, NCSL[year][1]], check=True)
    text = subprocess.run(["pdftotext", "-layout", path, "-"], capture_output=True, text=True, check=True).stdout
    names = {importlib.import_module(f"states.{st}.profile").STATE_NAME: st for st in facts_all if st != "us"}
    out = {}
    for line in text.splitlines():
        name = next((n for n in names if line.startswith(n + " ")), None)
        if not name:
            continue
        st = names[name]
        facts = facts_all[st]
        lower = next(c for c in facts["seats"] if c != "S")
        gov = re.search(r"\b(Rep|Dem|Ind)\s+(?:Rep|Dem|Divided|N/A)\s*$", line)
        party = {"Rep": "R", "Dem": "D", "Ind": "I"}[gov.group(1)]
        if facts.get("nonpartisan"):
            out[st] = ({lower: Counter({"N": facts["seats"][lower]})}, party)
            continue
        S, H = facts["seats"]["S"], facts["seats"][lower]
        m = re.search(rf"\s{S}\s+(\d+)\s+(\d+)\s+(.*?)\s+{H}\s+(\d+)\s+(\d+)\s*(.*?)\s+(?:Rep|Dem|Divided)\s", line)
        if not m:
            raise ValueError(f"NCSL {year}: can't read {name}: {line}")

        def chamber(d, r, other, seats):
            others = sum(int(x) for x in re.findall(r"\b(\d+)(?!v)\b", other))
            count = Counter({"D": int(d), "R": int(r), "I": others})
            vacant = sum(int(x) for x in re.findall(r"(\d+)v", other))
            if sum(count.values()) + vacant != seats:
                raise ValueError(f"NCSL {year}: {name} doesn't add up: {line}")
            return +count
        out[st] = ({"S": chamber(m.group(1), m.group(2), m.group(3), S), lower: chamber(m.group(4), m.group(5), m.group(6), H)}, party)
    missing = set(names.values()) - set(out)
    if missing:
        raise ValueError(f"NCSL {year}: no row for {sorted(missing)}")
    return out


def dots_of(state, facts, counts, gov, year, lower_name):
    """front_page.map_data()'s {dots, title} from seat counts: a majority is more than half the seats, a ring a
    supermajority that can override a veto on its own (not where a simple majority overrides, as in Indiana)."""
    lower = re.sub(r" of Delegates$", "", lower_name)
    dots, words = [], []
    for c, seats in sorted(facts["seats"].items(), key=lambda x: x[0] != "S"):
        name = "Senate" if c == "S" else lower
        if facts.get("nonpartisan"):
            dots.append(["N", False])
            words.append(f"{name}: nonpartisan, one house")
            continue
        parties = sorted(counts.get(c, Counter()).items(), key=lambda x: -x[1])
        top, n = parties[0] if parties else (None, 0)
        coalition = c in COALITION.get(year, {}).get(state, [])
        ruled = CONTROL.get(year, {}).get(state, {}).get(c)
        # A majority of the members seated that day (Pennsylvania's House in March 2024: 102-100 with one seat vacant,
        # Michigan's Senate in April 2025: 19-18 with one); a plurality isn't one. Today's balance.py counts all the
        # seats, where vacancies are fewer.
        filled = sum(v for _, v in parties)
        majority = "C" if coalition else ruled or (top if n > filled / 2 else None)
        need = seats // 2 + 1 if facts["override"] == "majority" else math.ceil(Fraction(facts["override"]) * seats)
        sm = not coalition and bool(top) and majority == top and n >= need and facts["override"] != "majority"
        dots.append([majority or "S", sm])
        tally = "–".join(str(v) for _, v in parties[:2]) if majority != "C" else ""
        words.append(f"{name}: {WORD.get(majority, 'split') if majority else 'split'}{' ' + tally if tally else ''}"
                     + (" (supermajority)" if sm else "") + (f" ({seats - filled} seats vacant)" if ruled and seats > filled else ""))
    dots.append([gov, False])
    exe = facts.get("executive", "Governor")
    words.append(f"{exe}: {ADJ.get(gov, gov)}")
    if exe != "Governor":
        words.insert(0, words.pop())  # Congress's names the President first, as front_page.map_data()
    return {"dots": dots, "title": "; ".join(words)}


def main():
    args = sys.argv[1:]
    root = args[args.index("--check") + 1] if "--check" in args else None
    facts_all = table()
    out, checks = {}, []
    for year in YEARS:
        day = NCSL[year][0]
        out[str(year)] = {"_asOf": day}
        table_ = ncsl(year, facts_all)
        for state, facts in sorted(facts_all.items()):
            P = importlib.import_module(f"states.{state}.profile")
            if state == "us":
                counts = congress_counts(day)[0]
            else:
                counts, ncsl_gov = table_[state]
                if root and not facts.get("nonpartisan"):
                    archive = state_counts(root, state, facts["seats"], day)[0]
                    for c in facts["seats"]:
                        a, b = +archive.get(c, Counter()), +counts.get(c, Counter())
                        if a != b:
                            checks.append((sum(((a - b) + (b - a)).values()), year, state, c, dict(a), dict(b)))
            gov = governor_party(state, facts, day)
            if state != "us" and gov != ncsl_gov:
                print(f"{year} {state}: governor {gov} here, {ncsl_gov} in NCSL's table")
            out[str(year)][state] = dots_of(state, facts, counts, gov, year, getattr(P, "LOWER_NAME", "Assembly"))
    for diff, year, state, c, a, b in sorted(checks, reverse=True):
        print(f"{year} {state} {c}: Open States {a}, NCSL {b}")
    if root:
        print(f"{len(checks)} chambers differ between the Open States archive and NCSL")
    path = os.path.join(HERE, "states", "party_history.json")
    with open(path, "w") as f:
        f.write("{\n" + ",\n".join(f' "{y}": {{\n' + ",\n".join(f'  "{s}": {json.dumps(d, ensure_ascii=False)}' for s, d in v.items()) + "\n }"
                                  for y, v in out.items()) + "\n}\n")
    print(f"wrote {path}")


if __name__ == "__main__":
    main()
