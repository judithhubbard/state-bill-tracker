"""Arizona's bills (downloaded by states/az/fetch.py from Open States, the owner's decision 2026-10-31) in the shape
build_data.py reads. House and Senate bills of each regular session (one a year), and the concurrent resolutions (HCR, SCR) that propose
constitutional amendments, which go to the voters, not the governor; other resolutions and memorials are left out.
Which resolutions propose amendments comes from their official titles, read from azleg.gov by states/az/azleg.py into
data/az/azleg/resolutions.json (Open States has only the short titles); one not read yet is left out.

Open States classifies each action: "reading-1" (read and sent to committee), "committee-passage" and
"amendment-passage" (a committee's DP, DPA or DPA/SE, naming the committee), "passage" (a house passing it; the first
house passes it again, "final read", after agreeing to the other's amendments), "failure", "executive-receipt"
("Transmit to Governor"), "executive-signature", "executive-veto". Votes are member by member with Open States person
ids, which the contacts file also uses. There are no summaries.
"""
import glob, json, os, re, unicodedata
from collections import defaultdict
from datetime import datetime
from zoneinfo import ZoneInfo

from states.az import profile as P
from states.undated import settle

HOUSE = {"S": "Senate", "H": "House"}
ORG = {"upper": "S", "lower": "H", "executive": "G"}
CURRENT = P.session_of(datetime.now(ZoneInfo(P.TIMEZONE)).year)
_PARTIES = {}


def folder(session):
    return os.path.join(P.DATA, str(session))


def sessions():
    # (A first copy still downloading is built too; build_site.sh skips the state while data/az/incomplete exists.)
    # This year's and next year's sessions show from their first bill (prefiled from mid-November); older ones once
    # they're mostly there.
    return sorted(int(os.path.basename(f)) for f in glob.glob(os.path.join(P.DATA, "[0-9]" * 4))
                  if len(glob.glob(os.path.join(f, "bills", "*.json"))) > (0 if int(os.path.basename(f)) >= CURRENT else 500))


def text(x):
    return re.sub(r"\s+", " ", x or "").strip()


def decode(a):
    """One Open States action -> (house, shared wording)."""
    h = ORG.get((a.get("organization") or {}).get("classification"), "")
    kinds, desc = a.get("classification") or [], text(a.get("description"))
    comm = next((e.get("name") for e in a.get("related_entities") or [] if e.get("entity_type") == "organization"), None)
    if "executive-signature" in kinds or "became-law" in kinds:
        return "G", "SIGNED"
    if "executive-veto" in kinds:
        return "G", "VETOED"
    if desc.startswith("Transmit to Secretary of State"):
        return "G", "Transmitted to the Secretary of State, for the next general election ballot"
    if "executive-receipt" in kinds:
        return "G", "DELIVERED TO GOVERNOR"
    if "passage" in kinds and desc == "DP":
        return h, "Committee of the Whole: do pass"  # the step before the third-reading vote, not a passage
    if "passage" in kinds:
        return h, f"PASSED {HOUSE.get(h, 'HOUSE').upper()}"
    if "failure" in kinds:
        return h, "FAILED"
    if "committee-passage" in kinds or "amendment-passage" in kinds or "informal-passage" in kinds:
        return h, f"REPORTED|{comm or ''}|{desc}"  # some reports don't name their committee
    if "reading-1" in kinds:
        return h, "REFERRED"
    if "withdrawal" in kinds:
        return h, "Withdrawn"
    return h or "G", desc


def resolution_titles(session):
    """Resolution number -> {"title": official title, "kind": "amendment" | "measure" | "other"} (states/az/azleg.py)."""
    try:
        return json.load(open(os.path.join(P.DATA, "azleg", "resolutions.json"))).get(str(session), {})
    except (OSError, ValueError):
        return {}


def official_summary(title):
    """"A CONCURRENT RESOLUTION Proposing an amendment ...; Amending article IV ..." -> "Proposing an amendment ...; amending
    article IV ..."."""
    t = re.sub(r"^A concurrent resolution\s*", "", text(title), flags=re.I)
    t = re.sub(r"; ([A-Z])(?=[a-z])", lambda m: "; " + m.group(1).lower(), t)
    # The texts' small capitals come through as "CONSTITUTION", "RELATING", even "CONSTituTION"; roman numerals stay.
    t = re.sub(r"\b[A-Za-z]\w*[A-Z]\w*\b", lambda m: m.group(0) if re.fullmatch(r"[IVXLC]+", m.group(0)) else m.group(0).lower(), t)
    t = re.sub(r"\bconstitution of arizona\b", "Constitution of Arizona", t, flags=re.I)
    t = re.sub(r"\barizona\b", "Arizona", t)
    return t[:1].upper() + t[1:]


_TITLES = {}


def _titles(session):
    """Short title -> [(bill, first sponsor)] for one session's bills."""
    if session not in _TITLES:
        out = {}
        for f in glob.glob(os.path.join(folder(session), "bills", "[HS]B*.json")):
            b = json.load(open(f))
            sp = next((x.get("name") for x in b.get("sponsorships") or [] if x.get("primary")), "")
            out.setdefault(text(b.get("title")).lower(), []).append((b["identifier"].replace(" ", ""), sp))
        _TITLES[session] = out
    return _TITLES[session]


def earlier(session, b):
    """The same bill in the two sessions before: the same short title, and the same prime sponsor or a title only one
    bill has in each session (Arizona's short titles are specific: "groundwater; replenishment; reporting")."""
    out = set()
    k = text(b.get("title")).lower()
    who = next((x.get("name") for x in b.get("sponsorships") or [] if x.get("primary")), "")
    if len(k.split()) < 3 or re.match(r"appropriations?\b|general appropriations|technical correction", k):
        return out
    for y in (session - 1, session - 2):
        if y not in sessions():
            continue
        old = _titles(y).get(k, [])
        same = [n for n, sp in old if sp and sp == who]
        if same:
            out.add((y, same[0]))
        elif len(old) == 1 and len(_titles(session).get(k, [])) == 1:
            out.add((y, old[0][0]))
    return out


def _key(name):
    """"Denise “Mitzi” Epstein", "David Marshall, Sr.", "Andrés Cano" -> "denise mitzi epstein", "david marshall",
    "andres cano"."""
    n = unicodedata.normalize("NFKD", name or "").encode("ascii", "ignore").decode().lower()
    words = [w for w in re.sub(r"[^a-z\s-]", " ", n.replace(".", "")).split() if w not in ("jr", "sr", "ii", "iii", "iv")]
    return " ".join(words)


# Roles missing from Open States' people data, checked against the 2023 roll calls: Flavio Bravo was a representative
# for District 26 until he was appointed to the Senate on May 8, 2023 (his file has only the Senate role).
ROLE_FIX = {"ocd-person/36cc8d88-e944-4889-b8ab-cf5610f3f03e": [{"house": "H", "district": 26, "start": "2023-01-09", "end": "2023-05-08"}]}


def roster(session):
    """For records without person ids (the 2023 bulk file): (houses, name, day) -> {"id", "name", "party", "district",
    "house"} or None, from Open States' people data (states/az/people.json, made by states/az/people.py). Candidates are
    the people who held a seat in one of the houses ("H", or "HS": the bill's house first) during the session. A name
    matches by its full form or one of the person's other names, else by first and last name, else by last name and first
    initial, else by last name alone when only one candidate has it; each looser test is tried only when no stricter one
    matched in any of the houses (Sen. Anna Hernandez co-sponsoring a House bill isn't Rep. Alma Hernández). Those seated
    on the day come first, then anyone seated that session (roll calls keep listing a member for a few days after a
    resignation or expulsion: Liz Harris, expelled April 12, 2023); so a seat that changed hands mid-session is told apart
    by the day."""
    try:
        everyone = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "people.json"), encoding="utf-8"))
    except (OSError, ValueError):
        none = lambda houses, name, day=None: None
        none.by_id = lambda pid, day=None: None
        return none
    # A role ending in a session's first two weeks is the term before it (the old terms end on the opening day: Mitzi
    # Epstein's House seat, Alma Hernández's old district).
    first, last = f"{session}-01-15", f"{session + P.YEARS - 1}-12-31"
    cands = defaultdict(list)  # house -> [(person, role, keys)]
    ids = defaultdict(list)  # person id -> [(person, role)]
    # Roles that ended in the three months before: a member named on that session's bills though Open States ends the
    # term on January 1 (Amish Shah, Jennifer Longdon, Leezah Sun on 2024's prefiled bills). Used only for full names.
    recent = defaultdict(list)
    for p in everyone:
        keys = [n.split() for n in {_key(n) for n in [p["name"]] + p.get("other_names", []) if "," not in n}]
        for r in p["roles"] + ROLE_FIX.get(p["id"], []):
            if (not r["start"] or r["start"] <= last) and (not r["end"] or r["end"] > first):
                cands[r["house"]].append((p, r, keys))
                ids[p["id"]].append((p, r))
            elif r["end"] and f"{session - 1}-10-01" <= r["end"] <= f"{session}-01-01":
                recent[r["house"]].append((p, r, keys))
    cache = {}

    def party_of(p, day):
        hit = [x for x in p.get("party") or [] if (not x["start"] or x["start"] <= day) and (not x["end"] or x["end"] > day)]
        return (hit or p.get("party") or [{"name": ""}])[-1]["name"]

    def resolve(houses, name, day=None):
        day = day or f"{session}-03-01"
        k = (houses, name, day)
        if k in cache:
            return cache[k]
        words = _key(name).split()
        tests = (lambda w: w == words,
                 lambda w: w[:1] == words[:1] and w[-1:] == words[-1:],
                 lambda w: w[-1:] == words[-1:] and w[0][:1] == words[0][:1],
                 lambda w: w[-1:] == words[-1:])
        hits = []
        for test in tests if words else ():
            # Each house's members seated that day, then that session; only then (full names only) recent ones.
            pools = [p_ for h in houses for p_ in (
                [c for c in cands.get(h, []) if (not c[1]["start"] or c[1]["start"] <= day) and (not c[1]["end"] or c[1]["end"] > day)],
                cands.get(h, []))]
            pools += [recent.get(h, []) for h in houses] if test in tests[:2] else []
            for pool in pools:
                hits = list({p["id"]: (p, r) for p, r, keys in pool if any(test(w) for w in keys)}.values())
                if hits:
                    break
            if hits:
                break
        out = None
        if len(hits) == 1:
            p, r = hits[0]
            out = {"id": p["id"], "name": p["name"], "party": party_of(p, day), "district": r["district"], "house": r["house"]}
        cache[k] = out
        return out

    def by_id(pid, day=None):
        """The same answer for a person id (the API's years): their seat that day, else their last one that session."""
        day = day or f"{session}-03-01"
        rs = sorted(ids.get(pid, []),
                    key=lambda x: ((not x[1]["start"] or x[1]["start"] <= day) and (not x[1]["end"] or x[1]["end"] > day), x[1]["end"] or "9999"))
        if not rs:
            return None
        p, r = rs[-1]
        return {"id": p["id"], "name": p["name"], "party": party_of(p, day), "district": r["district"], "house": r["house"]}
    resolve.by_id = by_id
    return resolve


def load_session(session):
    """Read one session's bills and return (records, bill number -> record index, fetched time, delegation)."""
    path = os.path.join(P.DATA, f"contacts_{session}.json")
    if not os.path.exists(path):
        paths = sorted(glob.glob(os.path.join(P.DATA, "contacts_*.json")))
        path = paths[-1] if paths else ""
    people = json.load(open(path))["people"] if path else {}
    seat_of = {p["id"]: sid for sid, p in people.items() if p.get("id")}
    parties = _PARTIES.setdefault(session, {})
    resolve = roster(session)

    def voter(h, x, day):
        """A roll-call name as a seat ("H:12a") when the voter holds one now, as the API's years do; else "H?Name"."""
        pid = (x.get("voter") or {}).get("id")
        name = text(x.get("voter_name"))
        if not pid:
            hit = resolve(h, name, day)
            if hit:
                pid, name = hit["id"], hit["name"]
        return seat_of.get(pid) or f"{h}?{name}"
    files = glob.glob(os.path.join(folder(session), "bills", "*.json"))
    fetched = datetime.fromtimestamp(max(os.path.getmtime(f) for f in files), ZoneInfo(P.TIMEZONE)).strftime("%Y-%m-%d %H:%M")
    recs, index = [], {}
    official = resolution_titles(session)
    for f in sorted(files, key=lambda f: (os.path.basename(f)[0], int(re.sub(r"\D", "", os.path.basename(f)) or 0))):
        b = json.load(open(f))
        p = b["identifier"].replace(" ", "")
        amendment = p[:3] in ("HCR", "SCR") and (official.get(p) or {}).get("kind") == "amendment"
        if not amendment and (p[:2] not in ("HB", "SB") or "bill" not in (b.get("classification") or [])):
            continue
        origin = p[0]
        other = "S" if origin == "H" else "H"
        acts = sorted(b.get("actions") or [], key=lambda a: (a.get("date") or "", a.get("order") or 0))
        steps = [((a.get("date") or "")[:10],) + decode(a) + (text(a.get("description")),) for a in acts]
        # A referral names no committee: it's the committee that later reports it in that house, if any.
        reports = {}
        for d, h, t, a in steps:
            if t.startswith("REPORTED|") and t.split("|")[1]:
                reports.setdefault(h, t.split("|")[1])
        steps = [(d, h, f"REFERRED TO {reports[h].upper()}" if t == "REFERRED" and h in reports else "Referred to committee" if t == "REFERRED" else
                  "REPORTED" if t.startswith("REPORTED|") else t, a) for d, h, t, a in steps]
        # A third-reading vote that failed outranks a "PASSED" the same day in the same house: Open States also lists the
        # Committee of the Whole's earlier voice vote as a passage (HB 2044 of 2024: "FAILED" 18-40, then "PASSED" with no
        # tally); about a hundred failed bills a year showed as passed that house.
        failed_days = {(d, h) for d, h, t, a in steps if t == "FAILED"}
        steps = [(d, h, "Committee of the Whole: passed" if t.startswith("PASSED") and (d, h) in failed_days else t, a)
                 for d, h, t, a in steps]
        passed, last, result = set(), {}, {}
        for i, (d, h, t, a) in enumerate(steps):
            if t.startswith("PASSED"):
                passed.add(h)
                last[h] = i
            if t.startswith("PASSED") or t == "FAILED":
                result[h] = t
        # Each house's last floor vote has to be a passage: a first house that fails the final vote on the other's
        # amendments (HB 2022 of 2024, 29-28 short of the 31 it needs) hasn't agreed, whatever it passed before.
        agreed = len(passed) == 2 and all(result.get(h, "").startswith("PASSED") for h in HOUSE)
        texts_ = [s[2] for s in steps]
        amended_by_other = any(s[1] == other and re.match(r"DPA", s[3]) for s in steps)
        if amendment:
            # Never goes to the governor: passing both houses (and going to the Secretary of State) is as far as it gets.
            stage = 3 if agreed and (not amended_by_other or last[origin] > last[other]) else 2 if passed else None
        elif "VETOED" in texts_:
            stage = 6
        elif "SIGNED" in texts_:
            stage = 5
        elif "DELIVERED TO GOVERNOR" in texts_:
            stage = 4
        elif agreed and (not amended_by_other or last[origin] > last[other]):
            stage = 3
        elif passed:
            stage = 2
        else:
            stage = None
        if stage is not None and stage >= 3:
            passed = {"S", "H"}
        where_h, place, comm = origin, "desk", None
        for d, h, t, a in steps:
            if t.startswith("REFERRED TO") or t == "Referred to committee":
                where_h, place, comm = (h if h in HOUSE else where_h), "committee", t[len("REFERRED TO "):] if t.startswith("REFERRED TO") else None
            elif t == "REPORTED":
                where_h, place, comm = (h if h in HOUSE else where_h), "floor", None
            elif t.startswith("PASSED"):
                place, comm = "desk", None
                where_h = other if h == origin else origin
        if stage is None:
            stage = 1 if place == "floor" else 0
        proper = lambda c: re.sub(r"\b(And|Of|The|On|For|To|In)\b", lambda m: m.group(1).lower(), c.title())
        comm = proper(comm) if comm else None
        refs = [(h, c) for h, c in reports.items() if h in HOUSE]
        refs.sort(key=lambda r: r[0] != origin)
        comm_list = sorted({f"{h} · {c}" for h, c in refs})
        title = text(b.get("title"))
        title = title[:1].upper() + title[1:]
        if amendment and not re.search(r"constitution", title, re.I):
            title = f"Constitutional amendment: {title}"
        topics = list(dict.fromkeys((["const"] if amendment else []) +[v for k, v in P.COMMITTEE_TOPICS.items() if any(k.lower() in c.lower() for _, c in refs)] +
                                    [k for k in P.TOPIC_WORDS if P.TOPIC_WORDS[k].search(title)]))
        left = any(s[1] == origin and s[2] == "REPORTED" for s in steps) or origin in passed
        fate = "passed" if left else "none"
        spons = sorted(b.get("sponsorships") or [], key=lambda s: (not s.get("primary"), s.get("name") or ""))
        names, district = [], 0
        day0 = min((s[0] for s in steps if s[0]), default=None)
        for s in spons:
            person = s.get("person") or {}
            # The bulk file (2023), and some of the API's sponsorships (239 in 2024: members who had left), name sponsors
            # without ids: tie the name to who held a seat that session, in the bill's house first. With an id, the same
            # people data gives the session's district (and the party of a member the API no longer describes).
            hit = resolve.by_id(person.get("id"), day0) if person.get("id") else resolve(origin + other, text(s.get("name")), day0)
            if hit:
                role = {"org_classification": "upper" if hit["house"] == "S" else "lower"}
                person = dict(person, id=hit["id"], party=person.get("party") or hit["party"], current_role=role)
                district = district or (hit["district"] if not names else 0)
                if not seat_of.get(hit["id"]):
                    s = dict(s, name=hit["name"])
            sid = seat_of.get(person.get("id"))
            name = people[sid]["name"] if sid else text(s.get("name"))
            party = (person.get("party") or "")[:1]
            role = ((person.get("current_role") or {}).get("org_classification") or "")
            if party:
                parties[("S" if role == "upper" else "H", name)] = party
            if name not in names:
                names.append(name)
        sponsor = names[0] if names else "—"
        cos = names[1:]
        if stage == 0:
            desc = f"In {HOUSE[where_h]} committee"
        elif stage == 1:
            desc = f"On the {HOUSE[where_h]} floor"
        else:
            desc = {2: f"Passed the {HOUSE[origin] if origin in passed else HOUSE[other]}", 3: "Passed both houses",
                    4: "On the governor's desk", 5: "Signed into law", 6: "Vetoed"}[stage]

        def dates(test, mode="last"):
            ds = sorted({s[0] for s in steps if test(s[1], s[2]) and s[0]})
            return {"first": ds[0], "last": ds[-1], "all": ";".join(ds)}[mode] if ds else ""

        votes = []
        for v in b.get("votes") or []:
            h = ORG.get((v.get("organization") or {}).get("classification"))
            if h not in HOUSE or "passage" not in (v.get("motion_classification") or []):
                continue
            counts = {c["option"]: c["value"] for c in v.get("counts") or []}
            if not any(counts.values()) or text(v.get("motion_text")).lower() == "do pass":
                continue  # the Committee of the Whole's unrecorded "do pass"
            day = (v.get("start_date") or "")[:10]
            names_ = [[voter(h, x, day), "N" if x.get("option") == "no" else "A"] for x in v.get("votes") or [] if x.get("option") != "yes"]
            votes.append([h, "F", None, (v.get("start_date") or "")[:10], counts.get("yes", 0), counts.get("no", 0), names_])
        votes.sort(key=lambda v: v[3])
        chapter = next((re.search(r"Chapter (\d+)", s[3]).group(1) for s in steps if re.search(r"Chapter \d+", s[3])), None)
        action_dates = [s[0] for s in steps if s[0]]
        src = next((s.get("url") for s in b.get("sources") or [] if "azleg.gov" in (s.get("url") or "")), None)
        rec = {
            "nums": [p], "base": [p], "prev": earlier(session, b),
            "title": title, "summary": official_summary((official.get(p) or {}).get("title", "")) if amendment else "", "act": "", "lawCode": "", "law": None, "laws": [],
            "comms": comm_list, "topics": topics, "places": [], "narrow": P.narrow_kind(title),
            "commFate": fate, "mainTopic": topics[0] if topics else "", "local": "local" in topics,
            "senDeleg": False, "asmDeleg": False, "budget": bool(re.search(r"general appropriations|\bbudget\b", title, re.I)),
            "passedS": "S" in passed, "passedA": "H" in passed, "program": None,
            "stage": stage, "passedIn": (HOUSE[origin] if origin in passed else HOUSE[other]) if stage == 2 else None,
            "chapter": int(chapter) if chapter and stage == 5 else None,
            "veto": None, "memo": "", "vetoMemo": None,
            "simText": title,
            "comm": comm if stage == 0 and place == "committee" else None,
            "first": min(action_dates, default=f"{session}-01-01"),
            "last": max(action_dates, default=f"{session}-01-01"),
            "cosp": len(cos),
            "keyDates": [
                dates(lambda h, t: t == "REPORTED", "first"),
                dates(lambda h, t: t == "PASSED SENATE", "all"),
                dates(lambda h, t: t == "PASSED HOUSE", "all"),
                "",
                dates(lambda h, t: t == "DELIVERED TO GOVERNOR"),
                dates(lambda h, t: t == "SIGNED"),
                dates(lambda h, t: t == "VETOED"),
            ],
            "votes": votes, "firstComms": [(refs[0][0], refs[0][1], left)] if refs else [],
            "vers": [{"p": p, "sponsor": sponsor, "district": district, "cosponsors": cos, "primes": 1, "cosp": len(cos),
                      "statusDesc": desc, "committee": comm if place == "committee" and stage in (0, 2) else None,
                      "actions": [[s[0], s[2]] for s in steps], "link": src or b.get("openstates_url")}],
        }
        index[p] = len(recs)
        recs.append(rec)
    settle(recs, folder(session))  # bills with no history yet: never dated in the future (states/undated.py)
    return recs, index, fetched, {"SENATE": [], "ASSEMBLY": []}


def agendas(session):
    """Bills on upcoming standing committee agendas (states/az/azleg.py's agendas(), from www.azleg.gov's agenda PDFs):
    bill -> [["House Education", "2026-02-17T14:00:00"], ...], meetings from today on."""
    try:
        got = json.load(open(os.path.join(folder(session), "agendas.json")))
    except (OSError, ValueError):
        return {}
    today = datetime.now(ZoneInfo(P.TIMEZONE)).date().isoformat()
    out = {k: [e for e in v if e[1][:10] >= today] for k, v in got.items()}
    return {k: v for k, v in out.items() if v}


def parties(session, recs):
    return {k: v for k, v in _PARTIES.get(session, {}).items() if v in ("D", "R")}
