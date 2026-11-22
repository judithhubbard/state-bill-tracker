#!/usr/bin/env python3
"""The Council's 13 members and its committees, written as data/dc/contacts_<session>.json in the shape build_data.py reads.

From dccouncil.gov (the Council's own site; its robots.txt allows everything): the members' list
(https://dccouncil.gov/councilmembers/), each member's page (seat: "Ward 3" or "At-Large", the Chairman's "Chairman";
email, telephone, office, political affiliation, committees, photo) and each committee's page (its chairperson and
members). About 25 pages, a second apart, once a day (kept in data/dc/members/). LegiScan's people records (legiscan.py)
give each member's id, which the roll calls use.

One house: seats "B:1" to "B:8" (the wards) and "B:9a" to "B:9e" (the five members elected at large, the Chairman first;
district 9 is named "At-large" in data/dc/district_names.json), in the shared files' "assemblyCommittees" slot (the
lower house's: P.LOWER). The Committee of the Whole is every member, chaired by the Chairman. A past Council Period lists
the current members who introduced a bill in it, without posts.
Usage: python3 states/dc/contacts.py [session]   (default: every Council Period downloaded)
"""
import html, json, os, re, sys, time, urllib.request
from datetime import datetime
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
from fetch_contacts import committee_key, name_key
from states import legiscan_convert as L
from states.dc import convert as C
from states.dc import profile as P

SITE = "https://dccouncil.gov"
AGENT = "Mozilla/5.0 (compatible; statebilltracker.org; a nonprofit bill tracker)"
FOLDER = os.path.join(P.DATA, "members")
EVERY = 20 * 3600


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": AGENT})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode("utf-8", "replace")


def lines(page):
    s = re.sub(r"(?s)<script.*?</script>|<style.*?</style>", "", page)
    t = html.unescape(re.sub(r"<[^>]+>", "\n", s))
    return [re.sub(r"\s+", " ", l).strip() for l in t.split("\n") if l.strip()]


def saved(name):
    return os.path.join(FOLDER, re.sub(r"[^a-z0-9-]", "_", name.lower()) + ".html")


def download():
    """The members' list, each member's page and each committee page they name, into data/dc/members/ (at most once in 20
    hours; a page that fails keeps its last copy)."""
    os.makedirs(FOLDER, exist_ok=True)
    stamp = os.path.join(FOLDER, "last_read")
    if os.path.exists(stamp) and time.time() - os.path.getmtime(stamp) < EVERY:
        # Within the day: only pages that failed last time.
        listed = json.load(open(os.path.join(FOLDER, "pages.json")))
        for kind, urls in (("cm-", listed["members"]), ("co-", listed["committees"])):
            for url in urls:
                path = saved(kind + url.rstrip("/").rsplit("/", 1)[1])
                if not os.path.exists(path):
                    time.sleep(1)
                    try:
                        open(path, "w").write(get(url))
                    except OSError as e:
                        print(f"  {url}: {e.__class__.__name__}", flush=True)
        return
    index = get(f"{SITE}/councilmembers/")
    open(saved("index"), "w").write(index)
    pages = sorted(set(re.findall(r'href="(https://dccouncil\.gov/council/[a-z0-9-]+/)"', index)))
    comms = set()
    for url in pages:
        time.sleep(1)
        try:
            page = get(url)
        except OSError as e:
            print(f"  {url}: {e.__class__.__name__}; kept the last copy", flush=True)
            continue
        open(saved("cm-" + url.rstrip("/").rsplit("/", 1)[1]), "w").write(page)
        comms |= set(re.findall(r'href="(https://dccouncil\.gov/committees/[a-z0-9-]+/)"', page))
    for url in sorted(comms):
        time.sleep(1)
        try:
            page = get(url)
        except OSError as e:
            print(f"  {url}: {e.__class__.__name__}; kept the last copy", flush=True)
            continue
        open(saved("co-" + url.rstrip("/").rsplit("/", 1)[1]), "w").write(page)
    json.dump({"members": pages, "committees": sorted(comms)}, open(os.path.join(FOLDER, "pages.json"), "w"), indent=1)
    open(stamp, "w").write(datetime.now().isoformat() + "\n")


def after(ls, label, n=1):
    try:
        i = ls.index(label)
    except ValueError:
        return ""
    return ls[i + n] if i + n < len(ls) else ""


def member(url):
    page = open(saved("cm-" + url.rstrip("/").rsplit("/", 1)[1])).read()
    ls = lines(page)
    title = ls[0] if ls else ""
    # "At-Large Councilmember Elissa Silverman • Council of the District of Columbia", "Ward 3 Councilmember Matthew Frumin",
    # "Chairman Phil Mendelson"
    name = after(ls, "Connect")
    m = re.search(r"\bcouncilmember\s+•\s+(.+)$", " • ".join(ls[ls.index("Connect"):ls.index("Connect") + 3]) if "Connect" in ls else "", re.I)
    head = re.sub(r"\s+•.*$", "", title)
    ward = re.search(r"\bWard (\d)\b", head)
    seat_word = "Chairman" if re.match(r"Chair", head) else f"Ward {ward.group(1)}" if ward else "At-Large" if re.search(r"At-Large", head, re.I) else ""
    # The name is the line after the seat line ("councilmember • At-Large" then "Elissa Silverman").
    for i, l in enumerate(ls):
        if re.match(r"(?:councilmember|chairman)\s*•", l, re.I) and i + 1 < len(ls):
            name = ls[i + 1]
            break
    else:
        name = re.sub(r"^(?:At-Large |Ward \d )?(?:Councilmember |Chairman )", "", head).strip()
    email = next((x for x in re.findall(r"mailto:([a-z0-9._-]+@dccouncil\.gov)", page)), None)
    phone = after(ls, "Telephone:") or None
    office = after(ls, "Office") or None
    party = after(ls, "Political Affiliation")
    photo = (re.findall(r'<meta property="og:image" content="([^"]+)"', page) or [None])[0]
    if photo and re.search(r"Seal|cropped-DC", photo):
        photo = None
    comms = []
    if "Committees" in ls:
        for l in ls[ls.index("Committees") + 1:]:
            if not l.startswith("Committee"):
                break
            comms.append(l)
    return {"name": name, "seat": seat_word, "email": email, "phone": phone, "office": office, "party": party,
            "image": photo, "url": url, "committees": comms}


def committee(url):
    path = saved("co-" + url.rstrip("/").rsplit("/", 1)[1])
    if not os.path.exists(path) or "/sub-committee" in url:
        return {"name": "", "chair": None, "members": []}  # (a page not read yet; subcommittees' bills stay with the committee)
    ls = lines(open(path).read())
    name = ls[0].split(" • ")[0] if ls else ""
    chair, members = None, []
    if "Chairperson" in ls:
        i = ls.index("Chairperson") + 1
        chair = ls[i] if i < len(ls) else None
        for l in ls[i:]:
            if l in ("Key Staff", "Agencies Under This Committee", "Related materials"):
                break
            if re.match(r"(?:Ward \d |At-Large )?(?:Councilmember|Chairman) ", l):
                members.append(l)
    strip = lambda x: re.sub(r"^(?:Ward \d |At-Large )?(?:Councilmember|Chairman) ", "", x or "").strip()
    return {"name": C.comm_name(name), "chair": strip(chair) if chair else None, "members": [strip(m) for m in members]}


WORDS = {"D": "Democratic", "R": "Republican", "I": "Independent"}


def party_word(p):
    """The page's "Political Affiliation" as the contacts files write parties: "Democratic", "Republican", "Independent",
    or the page's own words (the D.C. Statehood Green Party's members count as another party: balance.py)."""
    p = (p or "").strip()
    low = p.lower()
    return "Democratic" if low.startswith("democrat") else "Republican" if low.startswith("republican") else \
        "Independent" if low.startswith(("independent", "no party", "nonpartisan")) else p


def build(session):
    latest = session == max(C.sessions())
    pages = json.load(open(os.path.join(FOLDER, "pages.json")))
    ms = [member(u) for u in pages["members"]]
    # LegiScan's ids (the roll calls'), by name.
    folder = L.folders(P.DATA)[max(C.sessions())]
    ids = {name_key(L.text(p.get("name"))): p["people_id"] for p in L.people(folder).values() if p.get("state_id") == 51}
    # (A member whose page names no affiliation yet, Jamal Holtz's in November 2026: LegiScan's party.)
    lparty = {p["people_id"]: p.get("party") or "" for p in L.people(folder).values() if p.get("state_id") == 51}
    sponsors = set()
    if not latest:
        for r in C.load_session(session)[0]:
            for v in r["vers"]:
                sponsors |= {v["sponsor"], *v["cosponsors"]}
    people = {}
    at_large = sorted((m for m in ms if m["seat"] in ("Chairman", "At-Large")), key=lambda m: (m["seat"] != "Chairman", m["name"].split()[-1]))
    for i, m in enumerate(at_large):
        m["sid"] = f"{C.H}:9{'abcde'[i]}" if i < 5 else f"{C.H}:9{chr(97 + i)}"
    for m in ms:
        w = re.match(r"Ward (\d)", m["seat"])
        if w:
            m["sid"] = f"{C.H}:{w.group(1)}"
    for m in ms:
        if not m.get("sid") or (not latest and m["name"] not in sponsors):
            continue
        key = name_key(m["name"])
        pid = ids.get(key) or next((v for k, v in ids.items() if k.split()[-1] == key.split()[-1] and k[0] == key[0]), None)
        people[m["sid"]] = {
            "name": m["name"], "key": key, "id": pid, "party": party_word(m["party"]) or WORDS.get(lparty.get(pid), ""),
            "email": m["email"], "form": None, "phone": m["phone"], "phones": [["Wilson Building", m["phone"]]] if m["phone"] else [],
            "url": m["url"], "image": m["image"], "office": m["office"],
            "position": ("Chairman of the Council" if m["seat"] == "Chairman" else None) if latest else None,
            "places": "", "dataName": m["name"],
        }
    comms = {}
    if latest:
        for url in pages["committees"]:
            c = committee(url)
            if c["name"]:
                comms[committee_key(c["name"])] = {"name": c["name"], "chair": c["chair"], "coChairs": [], "viceChair": None,
                                                   "meets": None, "url": url, "members": sorted(set(c["members"] + ([c["chair"]] if c["chair"] else [])))}
        whole = [m["name"] for m in ms]
        chair = next((m["name"] for m in ms if m["seat"] == "Chairman"), None)
        comms.setdefault(committee_key("Committee of the Whole"), {"name": "Committee of the Whole", "chair": chair, "coChairs": [],
                         "viceChair": None, "meets": None, "url": f"{SITE}/committees/committee-of-the-whole/", "members": sorted(whole)})
    leaders = {}
    if latest:
        for h, (name, role, _) in P.LEADERS.items():
            hit = next((x for x in people.values() if x["key"] == name_key(name)), None)
            if hit:
                leaders[h] = {"name": hit["name"], "role": role}
    return {"session": session, "fetched": datetime.now(ZoneInfo(P.TIMEZONE)).strftime("%Y-%m-%d %H:%M"),
            "people": people, "since": {}, "senateCommittees": {}, "assemblyCommittees": comms,
            "leaders": leaders, "assemblyMembers": {}, "kept": []}


def main(session):
    out = build(session)
    latest = session == max(C.sessions())
    if latest and len(out["people"]) < 12:
        raise SystemExit(f"{session}: only {len(out['people'])} Councilmembers; kept the last contacts")
    path = os.path.join(P.DATA, f"contacts_{session}.json")
    json.dump(out, open(path, "w"), indent=1, ensure_ascii=False)
    ppl = out["people"].values()
    comms = list(out["assemblyCommittees"].values())
    print(f"{path}: {len(out['people'])} Councilmembers ({sum(1 for p in ppl if p['email'])} with email, "
          f"{sum(1 for p in ppl if p['phone'])} with a phone, {sum(1 for p in ppl if p['id'])} matched to LegiScan), "
          f"{len(comms)} committees ({sum(1 for c in comms if c['chair'])} with a chair), leaders {sorted(out['leaders'])}")


if __name__ == "__main__":
    try:
        download()
    except OSError as e:
        print(f"dccouncil.gov: {e.__class__.__name__}; kept the last copies", flush=True)
    for s in ([int(sys.argv[1])] if len(sys.argv) > 1 else C.sessions()):
        main(s)
