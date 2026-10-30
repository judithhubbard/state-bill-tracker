#!/usr/bin/env python3
"""Texas's legislators, committees and leaders, from the two houses' own websites and the Legislative Reference
Library, written as data/tx/contacts_<session>.json in the shape build_data.py reads (as states/va/contacts.py writes).

- House: the member list (house.texas.gov/members: name, member code, district, as JSON in the page), each member's
  page (Capitol and district phones, the email form, counties), and each committee's page (members as JSON, with
  "Chair").
- Senate: each senator's page (senate.texas.gov/member.php?d=N: name, party, Capitol and district phones, the email
  form, committees with "Chair"), and the committee list.
- Parties: the Legislative Reference Library's list for the Legislature (the House's site doesn't give them).
Each member carries `dataName`, the name the bill histories use: the last name, or "Bell, Keith" where two members of
a house share it. Seat ids are "S:14" and "H:137". Usage: python3 states/tx/contacts.py [session]
"""
import html, json, os, re, subprocess, sys, time
from datetime import datetime
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
from fetch_contacts import committee_key, name_key
from states.tx import profile as P

HOUSE = "https://house.texas.gov"
SENATE = "https://senate.texas.gov"
LRL = "https://lrl.texas.gov/legeLeaders/members/partyListSession.cfm?leg={}"


# A town in an address: "6500 Rookin, Building C Houston, TX 77074" -> "Houston"; "Corpus Christi, Texas 78401".
TOWN = re.compile(r"([A-Z][a-z.]+(?: [A-Z][a-z.]+)?),?\s+(?:TX|Texas)\s+\d{5}")


def get(url):
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
    parts = [p.strip() for p in name.split(",") if p.strip()]
    return " ".join([parts[1], parts[0]] + parts[2:]) if len(parts) > 1 else name.strip()


def phones_in(block):
    out = []
    # "(512) 463-0492" or "512-463-0586"; not fax numbers.
    for a, b, c in re.findall(r"\(?(\d{3})\)?[\s-]?(\d{3})-(\d{4})(?!\s*Fax)", block):
        n = f"({a}) {b}-{c}"
        if n not in [x[1] for x in out]:
            out.append(n)
    return out


def parties(session):
    """(house letter, name key) -> party, from the Library's list."""
    t = text(get(LRL.format(P.code_of(session)[:-1])))
    out = {}
    for party, house, names in re.findall(r"(Democrats|Republicans|Independents) in the (House of Representatives|Senate) \[[^\]]*\]\s*(.+?)(?=(?:Democrats|Republicans|Independents) in the|Legislative Reference Library|$)", t):
        h = "H" if house.startswith("House") else "S"
        # The names run together ("Gene Wu Erin Zwiener"); they're matched later by searching for each member.
        # Each party is named twice (a summary at the top, then the full list): keep the longer.
        key = (h, party[:-1].replace("Democrat", "Democratic"))
        out[key] = max(out.get(key, ""), " " + plain(names) + " ", key=len)
    return out


def plain(s):
    """Lowercase letters and spaces only, without accents: "Rafael Anchía" -> "rafael anchia"."""
    import unicodedata
    s = unicodedata.normalize("NFD", s).encode("ascii", "ignore").decode().lower()
    return re.sub(r"\s+", " ", re.sub(r"[^a-z\s]", " ", s)).strip()


def party_of(h, name, lists):
    key = [w for w in plain(name).split() if w not in ("jr", "sr", "ii", "iii", "lll", "iv")]
    first, last = key[0], key[-1]
    for (hh, party), names in lists.items():
        if hh == h and re.search(rf"\b{re.escape(first)}\b[^ ]*(?: \S+){{0,3}}? {re.escape(last)}\b", names):
            return party
    for (hh, party), names in lists.items():
        if hh == h and f" {last} " in names:
            return party
    return ""


def house(session, lists):
    page = get(f"{HOUSE}/members")
    m = re.search(r'="(\[\{&quot;member_name[^"]*)"', page)
    members = json.loads(html.unescape(m.group(1)))
    people = {}
    for mem in members:
        if not mem.get("active"):
            continue
        d, code = int(mem["id"]), mem["member_bill_code"]
        name = re.sub(r" lll$", " III", flip(html.unescape(mem["member_name"])))  # the list writes "lll"
        p = get(f"{HOUSE}/members/{code}")
        t = text(p)
        cap = re.search(r"Capitol Address:(.+?)(?:District Address:|Bills Authored)", t)
        dist = re.search(r"District Address:(.+?)Bills Authored", t)
        phones = [["Capitol", n] for n in phones_in(cap.group(1) if cap else "")[:1]]
        town = TOWN.findall(dist.group(1)) if dist else []
        phones += [[town[0] if town else "District", n] for n in phones_in(dist.group(1) if dist else "")[:1]]
        counties = re.search(r"Counties Represented:(.+?)(?:Return to top|$)", t)
        people[f"H:{d}"] = {
            "name": name, "id": str(code), "party": party_of("H", name, lists), "email": None,
            "form": f"{HOUSE}/members/{code}/email", "phone": phones[0][1] if phones else None, "phones": phones,
            "url": f"{HOUSE}/members/{code}", "image": f"{HOUSE}/{mem['image']}" if mem.get("image") else None,
            "office": "", "position": None, "places": counties.group(1).strip() if counties else "",
            "_bill": html.unescape(mem["member_name"]),
        }
    # Standing committees (not subcommittees) and their members.
    listing = get(f"{HOUSE}/committees")
    by_code = {v["id"]: k for k, v in people.items()}
    comms = {}
    for code, cname in dict(re.findall(r'committees/committee/(\d+)"[^>]*>\s*([^<]+?)\s*</a>', listing)).items():
        cname = html.unescape(cname).strip()
        if "S/C" in cname or "Subcommittee" in cname:
            continue
        try:
            cp = get(f"{HOUSE}/committees/committee/{code}")
        except RuntimeError as e:
            print(f"  {cname}: {e}", file=sys.stderr)
            continue
        m = re.search(r'committeemembers="([^"]*)"', cp)
        on, chair = [], None
        for x in json.loads(html.unescape(m.group(1))) if m else []:
            sid = by_code.get(str(x.get("member_bill_code")))
            if sid:
                on.append(people[sid]["name"])
                if x.get("position") == "Chair":
                    chair = people[sid]["name"]
        comms[committee_key(cname)] = {"name": cname, "chair": chair, "meets": None, "members": sorted(on)}
    return people, comms


def senate(session, lists):
    people, roles = {}, {}
    for d in range(1, 32):
        p = get(f"{SENATE}/member.php?d={d}")
        name = re.search(r"<title>Senator (.+?): District \d+", p)
        if not name:
            continue
        name = re.sub(r"\s+", " ", html.unescape(name.group(1))).strip()
        party = re.search(r"Party:\s*</?[^>]*>?\s*(Republican|Democrat|Democratic|Independent)", p) or re.search(r"Party: (Republican|Democrat|Independent)", text(p))
        form = re.search(r'href="(memberform\.php\?[^"]+)"', p)
        cap = re.search(r'headers="d\d+CAP">(.*?)</td>', p, re.S)
        dist = re.search(r'headers="d\d+DA1">(.*?)</td>', p, re.S)
        phones = [["Capitol", n] for n in phones_in(cap.group(1) if cap else "")[:1]]
        town = TOWN.findall(text(dist.group(1))) if dist else []
        phones += [[town[0] if town else "District", n] for n in phones_in(dist.group(1) if dist else "")[:1]]
        roles[d] = re.findall(r'<li><a href="cmte\.php\?c=\d+">([^<]+?)\s*\**</a>\s*&mdash;\s*([A-Za-z-]+)', p) + \
            [(c, "Member") for c in re.findall(r'<li><a href="cmte\.php\?c=\d+">([^<]+?)\s*\**</a></li>', p)]
        pt = party.group(1) if party else ""
        people[f"S:{d}"] = {
            "name": name, "id": str(d), "party": {"Democrat": "Democratic"}.get(pt, pt) or party_of("S", name, lists),
            "email": None, "form": f"{SENATE}/{html.unescape(form.group(1))}" if form else f"{SENATE}/member.php?d={d}",
            "phone": phones[0][1] if phones else None, "phones": phones, "url": f"{SENATE}/member.php?d={d}",
            "image": None, "office": "", "position": None, "places": "",
        }
    comms = {}
    for d, rs in roles.items():
        for cname, role in rs:
            cname = html.unescape(cname).strip().rstrip("*").strip()
            # Standing committees only (not "..., Select", "..., Special", "..., General Investigating").
            if cname.startswith("Senate ") or re.search(r", (Select|Special|General Investigating)$", cname):
                continue  # select and special committees
            c = comms.setdefault(committee_key(cname), {"name": cname, "chair": None, "meets": None, "members": []})
            c["members"].append(people[f"S:{d}"]["name"])
            if role == "Chair":
                c["chair"] = people[f"S:{d}"]["name"]
    for c in comms.values():
        c["members"].sort()
    return people, comms


def build(session):
    lists = parties(session)
    h_people, h_comms = house(session, lists)
    s_people, s_comms = senate(session, lists)
    # The name the bill histories use: the last name, or "Last, First" where two members of a house share it.
    for people, h in ((h_people, "H"), (s_people, "S")):
        lasts = [name_key(p["name"]).split()[-1] for p in people.values()]
        for p in people.values():
            raw = p.pop("_bill", None) or ", ".join(reversed(p["name"].rsplit(" ", 1)))
            last = raw.split(",")[0].strip()
            p["dataName"] = raw.strip() if lasts.count(name_key(p["name"]).split()[-1]) > 1 else last
    people = {**s_people, **h_people}
    for p in people.values():
        p["key"] = name_key(p["name"])
    # The Lieutenant Governor presides over the Senate and decides which bills come up, but isn't a senator.
    leaders = {"S": {"name": P.LEADERS["S"][0], "role": P.LEADERS["S"][1], "title": "Lt. Gov.",
                     "url": "https://www.ltgov.texas.gov/", "phone": "(512) 463-0001", "phones": [["Capitol", "(512) 463-0001"]],
                     "form": "https://www.ltgov.texas.gov/contact/"}}
    speaker = next((p for p in h_people.values() if name_key(p["name"]) == name_key(P.LEADERS["H"][0])), None)
    if speaker:
        speaker["position"] = "Speaker of the House"
        leaders["H"] = {"name": speaker["name"], "role": "Speaker of the House"}
    return {
        "session": session,
        "fetched": datetime.now(ZoneInfo(P.TIMEZONE)).strftime("%Y-%m-%d %H:%M CT"),
        "people": people, "since": {},
        "senateCommittees": s_comms, "assemblyCommittees": h_comms, "leaders": leaders,
        "assemblyMembers": {}, "kept": [],
    }


def main(session):
    out = build(session)
    path = os.path.join(P.DATA, f"contacts_{session}.json")
    os.makedirs(P.DATA, exist_ok=True)
    with open(path, "w") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
    ppl = out["people"].values()
    print(f"{path}: {len(out['people'])} legislators ({sum(1 for p in ppl if p['phone'])} with a phone, "
          f"{sum(1 for p in ppl if p['party'])} with party), {len(out['senateCommittees'])} Senate and "
          f"{len(out['assemblyCommittees'])} House committees "
          f"({sum(1 for c in list(out['senateCommittees'].values()) + list(out['assemblyCommittees'].values()) if c['chair'])} with a chair)")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else P.session_of(datetime.now(ZoneInfo(P.TIMEZONE)).year))
