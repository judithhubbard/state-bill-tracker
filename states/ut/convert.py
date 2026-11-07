"""Utah's bills (downloaded by states/ut/fetch.py from the Legislature's developer API) in the shape build_data.py reads.
House and Senate bills of each year's general session, plus the joint resolutions that propose constitutional
amendments ("Proposal to Amend Utah Constitution"); other resolutions are left out.

Since 2025 each action carries a code ("HPASS3" House passed 3rd reading), its time, who has the bill next (owner: "House
Transportation Committee") and its vote (id and "71-0-4": yes, no, absent). 2024's records are older and thinner (a date,
the wording and a location), so its actions get their codes from the same wording in 2025-26 and their votes from each
bill's status page (status/<HB0001>.json). A new bill goes first to its house's Rules Committee, which sends it to a
standing committee (HTOSTAND) or, later, decides which bills reach the floor (a reported bill often goes back to Rules,
and in the Senate the 2nd Reading Calendar goes "to Rules"). A committee's favorable, substitute, amendment or consent
calendar recommendation reports it; "Held", "Tabled" and "Motion to Recommend Failed" don't. "Signed by Speaker/President,
sent for enrolling" means both houses passed the same text; "to Governor"; "Governor Signed", "Became Law w/o Governor
Signature", "Governor Vetoed", "Governor Line Item Veto". Joint resolutions go to the Lieutenant Governor for the ballot.
"Filed" (bills not passed) and "strike enacting clause" end a bill. Members' votes are in votes.json (states/ut/fetch.py
reads le.utah.gov's vote pages, so recent ones may still be missing; the tallies are always there).
"""
import glob, html, json, os, re
from datetime import datetime
from zoneinfo import ZoneInfo

from states.ut import profile as P

HOUSE = {"S": "Senate", "H": "House"}
CURRENT = P.session_of(datetime.now(ZoneInfo(P.TIMEZONE)).year)
_PARTIES = {}

REFER = {"HTOSTAND", "STOSTAND", "HLIFTCAL", "HCAMOVE"}
TO_RULES = {"HREAD1", "SREAD1", "S2NDTORUL", "H3RDTORUL", "S3RDTORUL", "HCARUL", "SCARUL", "HRETRULFIS", "HCRRUL", "SCRRUL",
            "SRETRUL", "HCRRULSUB", "SCRRULSUB", "SCRRULAMD", "HCRRULAMD", "HCRRULSUBA", "SCRRULSUBA", "H2NDTORUL"}
REPORTED = {"HCAFAV", "HCASUB", "HCAAMD", "HCACONCAL", "SCAFAV", "SCASUB", "SCAAMD", "SCACONCAL"}
COMMITTEE_NO = {"HCAFAVFAIL", "SCAFAVFAIL"}
HELD = {"HCAHELD", "SCAHELD", "HCATBL", "SCATBL", "HCANOCNSDR", "SCANOCNSDR"}
FLOOR = {"SON2ND", "SREAD2", "SREAD3", "HREAD2", "HREAD3", "SREAD23SP", "SRUL2ND", "HRUL3RD", "HLIFTRUL", "SLIFTRUL",
         "SON3TBL", "HMOVE3RD", "SMOVE2ND", "SMOVE3RD", "HPLACETC", "SPLACETC", "HCC", "HREAD2SP"}
PASSED = {"HPASS3": "H", "SPASS3": "S", "SPASS23SP": "S"}
FINAL = {"HCOMFINALP": "H", "SCOMFINALP": "S"}  # passing the conference committee's version
VOTED = REPORTED | COMMITTEE_NO | HELD | set(PASSED) | set(FINAL) | {"HFAIL", "SFAIL", "HCONCUR", "SCONCUR", "HCOMREPADP",
                                                                     "SCOMREPADP", "SPASS2", "HRECONCUR", "SRECONCUR"}


def folder(session):
    return os.path.join(P.DATA, str(session))


def sessions():
    return sorted(int(os.path.basename(f)) for f in glob.glob(os.path.join(P.DATA, "[0-9]" * 4))
                  if len(glob.glob(os.path.join(f, "bills", "*.json"))) > 500)


def text(x):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", x or ""))).strip()


def comm_name(full):
    """"House Transportation Committee" -> "Transportation"; "Senate Rules Committee" -> "Rules"."""
    return re.sub(r"^(?:House|Senate) | Committee$", "", full or "").strip()


_CODES = {}


def codes():
    """Each action's wording -> its code, learned from the years whose records carry codes."""
    if not _CODES:
        for f in glob.glob(os.path.join(P.DATA, "[0-9]" * 4, "bills", "*.json")):
            for a in json.load(open(f)).get("actionHistoryList") or []:
                if a.get("actionCode"):
                    _CODES.setdefault(wording(a.get("description")), a["actionCode"])
    return _CODES


def wording(d):
    """"House Comm - Substitute Recommendation from # 0 to # 3" -> "House Comm - Substitute Recommendation"."""
    return re.sub(r"\s*(?:from )?#.*$", "", text(d))


def stamp(d):
    """"2026-01-19 11:07:38.010" or "2/18/2025 3:38 PM" (both appear) -> "YYYY-MM-DD HH:MM"."""
    d = (d or "").strip()
    m = re.match(r"(\d+)/(\d+)/(\d{4})(?:\s+(\d+):(\d+)(?::\d+)?\s*([AP]M)?)?", d)
    if m:
        hh = int(m.group(4) or 0)
        if m.group(6):
            hh = hh % 12 + (12 if m.group(6) == "PM" else 0)
        return f"{m.group(3)}-{int(m.group(1)):02d}-{int(m.group(2)):02d} {hh:02d}:{m.group(5) or '00'}"
    return d[:16]


def actions(b, session):
    """[(time "YYYY-MM-DD HH:MM", code, wording, owner, vote key, (yes, no, absent) or None)] in order."""
    out = []
    if b.get("actionHistoryList") is not None:
        for a in b["actionHistoryList"]:
            code, vid = a.get("actionCode") or "", a.get("voteID") or ""
            committee = code[1:3] == "CA"
            key = (("C" if committee else (a.get("voteHouse") or code[:1])) + vid) if vid else ""
            m = re.match(r"(\d+)-(\d+)-(\d+)$", a.get("voteStr") or "")
            out.append((stamp(a.get("actionDate")), code, text(a.get("description")), text(a.get("owner")), key,
                        tuple(map(int, m.groups())) if m else None))
        return out
    try:  # 2024: the status page's table (times and votes), else the API's dated actions
        rows = json.load(open(os.path.join(folder(session), "status", f"{b.get('bill')}.json")))
    except (OSError, ValueError):
        rows = [{"date": a.get("date"), "action": a.get("action"), "location": a.get("location")} for a in b.get("actionhistory") or []]
    for r in rows:
        d = r.get("date") or ""
        m = re.match(r"(\d+)/(\d+)/(\d{4})(?:\s*\((\d+):(\d+):\d+ ([AP]M)\))?", d)
        if m:
            hh = (int(m.group(4)) % 12 + (12 if m.group(6) == "PM" else 0)) if m.group(4) else 0
            ts = f"{m.group(3)}-{int(m.group(1)):02d}-{int(m.group(2)):02d} {hh:02d}:{m.group(5) or '00'}"
        else:
            ts = d[:10]
        link = r.get("voteLink") or ""
        v = re.search(r"voteid=(\d+)", link)
        key = ("C" + v.group(1) if "mtgvotes" in link else (re.search(r"house=([HS])", link).group(1) + v.group(1))) if v and re.search(r"mtgvotes|house=[HS]", link) else ""
        t = re.match(r"(\d+) (\d+) (\d+)$", r.get("vote") or "")
        out.append((ts, codes().get(wording(r.get("action")), ""), text(r.get("action")), text(r.get("location")), key,
                    tuple(map(int, t.groups())) if t else None))
    return out


def is_amendment(title, num):
    return num[:3] in ("HJR", "SJR") and bool(re.search(r"amend (?:the )?Utah Constitution|Constitutional Amendment", title, re.I))


def what_it_does(b):
    """The General Description, then the Highlighted Provisions' bullets ("This bill:<hr><ltbullet>defines terms; ...")."""
    general = text(b.get("generalProvisions") or b.get("generalprovisions"))
    hi = b.get("highlightedProvisions") or b.get("hilightedprovisions") or ""
    bullets = [re.sub(r"[;,]?\s*(?:\band|\bor)?\s*[;,.]?\s*$", "", text(x)) for x in re.split(r"<ltbullet>", hi)[1:]]
    bullets = [x[:1].upper() + x[1:] + ("" if x.endswith(".") else ".") for x in bullets if x]
    return "\n".join([general] + bullets[:8]) if general else ""


def load_session(session):
    """Read one year's bills and return (records, bill number -> record index, fetched time, delegation)."""
    path = os.path.join(P.DATA, f"contacts_{session}.json")
    if not os.path.exists(path):
        paths = sorted(glob.glob(os.path.join(P.DATA, "contacts_*.json")))
        path = paths[-1] if paths else ""
    contacts = json.load(open(path)) if path else {}
    people = contacts.get("people", {})
    by_id = {p["id"]: (sid, p) for sid, p in people.items()}
    # Committee vote pages give "Peterson, K." (no district): (house, last name, first initial) -> seat.
    initials = {}
    for sid, p in people.items():
        last, _, first = (p.get("dataName") or "").partition(", ")
        for given in dict.fromkeys(w[:1] for w in first.split() if w[:1].isalpha()):  # "R. Neil" is "Walter, N." too
            initials.setdefault((sid[0], last, given), []).append(sid)
    names = sponsor_names()
    try:
        votes_seen = json.load(open(os.path.join(folder(session), "votes.json")))
    except (OSError, ValueError):
        votes_seen = {}
    parties = _PARTIES.setdefault(session, {})
    files = glob.glob(os.path.join(folder(session), "bills", "*.json"))
    fetched = datetime.fromtimestamp(max(os.path.getmtime(f) for f in files), ZoneInfo(P.TIMEZONE)).strftime("%Y-%m-%d %H:%M")
    texts, recs, index = {}, [], {}
    for f in sorted(files, key=lambda f: (os.path.basename(f)[0], int(re.sub(r"\D", "", os.path.basename(f)) or 0))):
        b = json.load(open(f))
        num = b.get("billNumber") or b.get("bill") or os.path.basename(f)[:-5]
        kind = re.match(r"[A-Z]+", num).group(0)
        title = text(b.get("shortTitle") or b.get("shorttitle"))
        amendment = is_amendment(title, num)
        if kind not in ("HB", "SB") and not amendment:
            continue
        p = f"{kind}{int(re.sub(r'\D', '', num))}"
        origin = p[0]
        other = "S" if origin == "H" else "H"
        acts = actions(b, session)
        steps = []  # (date, house, shared wording, as written, code)
        for ts, code, desc, owner, key, tally in acts:
            h = code[:1] if code[:1] in HOUSE else ("H" if desc.startswith("House") else "S" if desc.startswith("Senate") else "G")
            if code in REFER:
                t = f"REFERRED TO {comm_name(owner).upper()}"
            elif code in TO_RULES and "Rules" in owner:
                t = "REFERRED TO RULES"
            elif code in REPORTED:
                t = "REPORTED"
            elif code in COMMITTEE_NO:
                t = "Committee voted it down"
            elif code in HELD:
                t = "HELD"
            elif code in FLOOR:
                t = "PLACED ON FLOOR"
            elif code in PASSED:
                t, h = f"PASSED {HOUSE[PASSED[code]].upper()}", PASSED[code]
            elif code in FINAL:
                t, h = "CONFERENCE PASSED", FINAL[code]
            elif code in ("HFAIL", "SFAIL"):
                t = "FAILED"
            elif code in ("HMOTREC", "SMOTREC", "HMOTRECP") and (code == "HMOTRECP" or not tally or tally[0] > tally[1]
                                                                   or tally[:2] == (0, 0)):  # 0-0: a voice vote
                t = "RECONSIDERED"
            elif code in ("HRECALL", "SRECALL"):
                t = "RECALLED"  # taken back after the presiding officers signed it (SB 254 of 2025)
            elif code in ("HCONCUR", "SCONCUR"):
                t = "CONCURRED"
            elif code in ("HSIGN", "SSIGN"):
                t = "ENROLLED"
            elif code in ("HTOGOV", "STOGOV"):
                t, h = "DELIVERED TO GOVERNOR", "G"
            elif code in ("HTOLTGOV", "STOLTGOV"):
                t, h = "To the Lieutenant Governor", "G"
            elif code in ("GSIGN", "GNOSIGN"):
                t, h = "SIGNED", "G"
            elif code == "GOVLVETO":
                t, h = "Signed with item vetoes", "G"
            elif code == "GVETO":
                t, h = "VETOED", "G"
            elif code in ("HFILED", "SFILED", "HECS", "SECS"):
                t = "DIED"
            else:
                t = desc
            steps.append((ts[:10], h, t, desc, code, key, tally, owner))
        passed = set()
        for _, h, t, _, _, _, _, _ in steps:  # in order: a reconsidered passage no longer counts
            if t.startswith("PASSED") or t == "CONFERENCE PASSED":
                passed.add(h)
            elif t == "RECONSIDERED":
                passed.discard(h)
        texts_ = [s[2] for s in steps]
        if "RECALLED" in texts_:  # signatures before a recall don't count
            last = len(texts_) - 1 - texts_[::-1].index("RECALLED")
            texts_ = [t for i, t in enumerate(texts_) if not (i < last and t == "ENROLLED")]
        line_veto = "Signed with item vetoes" in texts_
        if amendment:
            stage = 3 if len(passed) == 2 and ("ENROLLED" in texts_ or "To the Lieutenant Governor" in texts_) else None
        elif "SIGNED" in texts_ or line_veto:
            stage = 5
        elif "VETOED" in texts_:
            stage = 6
        elif "DELIVERED TO GOVERNOR" in texts_:
            stage = 4
        elif "ENROLLED" in texts_:
            stage = 3
        elif passed:
            stage = 2
        else:
            stage = None
        if stage is not None and stage >= 3:
            passed = {"S", "H"}
        where_h, place, comm = origin, "desk", None
        for _, h, t, _, _, _, _, _ in steps:
            if t.startswith("REFERRED TO"):
                where_h, place, comm = (h if h in HOUSE else where_h), "committee", t[len("REFERRED TO "):]
            elif t in ("REPORTED", "PLACED ON FLOOR"):
                where_h, place, comm = (h if h in HOUSE else where_h), "floor", None
            elif t.startswith("PASSED"):
                place, comm = "desk", None
                where_h = other if h == origin else origin
        if stage is None:
            stage = 1 if place == "floor" else 0
        proper = lambda c: re.sub(r"\b(And|Of|The|On|For|To|In)\b", lambda m: m.group(1).lower(), c.title())
        comm = proper(comm) if comm else None
        refs = [(s[1] if s[1] in HOUSE else origin, proper(s[2][len("REFERRED TO "):])) for s in steps if s[2].startswith("REFERRED TO")]
        comm_list = sorted({f"{h} · {c}" for h, c in refs})
        ver = (b.get("billVersionList") or [{}])[-1]
        subjects = [s.get("description") for s in ver.get("subjectList") or []] or list(b.get("subjects") or [])
        long_title = what_it_does(b)
        topics = list(dict.fromkeys((["const"] if amendment else []) +
                                    [P.SUBJECT_TOPICS[s] for s in subjects if s in P.SUBJECT_TOPICS] +
                                    [v for k, v in P.COMMITTEE_TOPICS.items() if any(c.startswith(k) for _, c in refs)] +
                                    [k for k in P.TOPIC_WORDS if P.TOPIC_WORDS[k].search(title)]))
        # A bill's first real committee (Rules only routes bills): approved, held, voted down or never acted on.
        first = next((r for r in refs if r[1] != "Rules"), None)
        after = texts_[texts_.index(f"REFERRED TO {first[1].upper()}"):] if first and f"REFERRED TO {first[1].upper()}" in texts_ else []
        left = "REPORTED" in after or any(t.startswith("PASSED") for t in texts_)
        fate = ("passed" if left else "defeated" if "Committee voted it down" in after else "held" if "HELD" in after else "none")
        sponsors = [b.get("primeSponsor") or b.get("sponsor"), b.get("floorSponsor") or b.get("floorsponsor")]
        sponsors += [c.get("id") if isinstance(c, dict) else c for c in ver.get("coSponsorList") or []]
        names_ = []
        for i in dict.fromkeys(x for x in sponsors if x):
            sid, person = by_id.get(i, (None, None))
            name = person["name"] if person else names.get(i, i)
            if person and person.get("party"):
                parties[(sid[0], name)] = person["party"][:1]
            if name not in names_:
                names_.append(name)
        sponsor, cos = (names_[0] if names_ else "—"), names_[1:]
        what = long_title
        if what:
            texts[p] = {"statement": what, "label": "From the bill's General Description and Highlighted Provisions, written by the Office of Legislative Research and General Counsel."}
        if stage == 0:
            desc = f"In {HOUSE[where_h]} committee"
        elif stage == 1:
            desc = f"On the {HOUSE[where_h]} floor"
        else:
            desc = {2: f"Passed the {HOUSE[origin] if origin in passed else HOUSE[other]}", 3: "Passed both houses",
                    4: "On the governor's desk", 5: "Became law", 6: "Vetoed"}[stage]

        def dates(test, mode="last"):
            ds = sorted({s[0] for s in steps if test(s[1], s[2]) and s[0]})
            return {"first": ds[0], "last": ds[-1], "all": ";".join(ds)}[mode] if ds else ""

        votes = []
        for d, h, t, desc_, code, key, tally, owner in steps:
            if code not in VOTED or not tally:
                continue
            committee = code[1:3] == "CA"
            vh = code[:1] if code[:1] in HOUSE else h
            roll = votes_seen.get(key) or {}
            names_v = []
            for kind_, mark in (("nays", "N"), ("absent", "A")):
                for name, district in roll.get(kind_) or []:
                    sid = f"{vh}:{int(district)}" if str(district).isdigit() else None
                    if not sid:
                        last, _, first = name.partition(", ")
                        hits = initials.get((vh, last, first[:1]), [])
                        sid = hits[0] if len(hits) == 1 else f"{vh}?{name}"
                    names_v.append([sid, mark])
            yes, no = tally[0], tally[1]
            if roll.get("ok") and (roll.get("yeas") or roll.get("nays")):  # the vote page's own list wins (SB 141 of 2026: 6-0 vs 5-1)
                yes, no = len(roll.get("yeas") or []), len(roll.get("nays") or [])
            votes.append([vh, "C" if committee else "F", proper(comm_name(owner_of_vote(steps, code, owner))) if committee else None,
                          d, yes, no, names_v])
        # A committee voting on a substitute, then amendments, then the bill, the same day: only the last vote shows.
        last_of = {(v[0], v[2], v[3]): i for i, v in enumerate(votes) if v[1] == "C"}
        votes = [v for i, v in enumerate(votes) if v[1] != "C" or last_of[(v[0], v[2], v[3])] == i]
        action_dates = [s[0] for s in steps if s[0]]
        num_padded = f"{kind}{int(re.sub(r'\D', '', num)):04d}"
        rec = {
            "nums": [p], "base": [p], "prev": earlier(session, title, sponsors[0] if sponsors else ""),
            "title": title, "summary": text(b.get("generalProvisions") or b.get("generalprovisions")), "act": "", "lawCode": "",
            "law": None, "laws": [], "comms": comm_list, "topics": topics, "places": [], "narrow": P.narrow_kind(title),
            "commFate": fate, "mainTopic": topics[0] if topics else "", "local": "local" in topics,
            "senDeleg": False, "asmDeleg": False, "budget": bool(re.search(r"\bbudget\b|appropriations? act", title, re.I)),
            "passedS": "S" in passed, "passedA": "H" in passed, "program": None,
            "stage": stage, "passedIn": (HOUSE[origin] if origin in passed else HOUSE[other]) if stage == 2 else None,
            "chapter": None, "veto": None, "memo": "", "vetoMemo": None,
            "simText": f"{title} {' '.join(subjects)}",
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
                dates(lambda h, t: t in ("SIGNED", "Signed with item vetoes")),
                dates(lambda h, t: t == "VETOED"),
            ],
            "votes": votes, "firstComms": [(first[0], first[1], left)] if first else [],
            "vers": [{"p": p, "sponsor": sponsor, "district": 0, "cosponsors": cos, "primes": 1, "cosp": len(cos),
                      "statusDesc": desc, "committee": comm if place == "committee" and stage in (0, 2) else None,
                      "actions": [[s[0], s[2] if s[2].isupper() or s[2].startswith("Committee") else s[3]] for s in steps],
                      "link": f"https://le.utah.gov/~{session}/bills/static/{num_padded}.html"}],
        }
        index[p] = len(recs)
        recs.append(rec)
    json.dump(texts, open(os.path.join(P.DATA, f"texts_{session}.json"), "w"), ensure_ascii=False)
    return recs, index, fetched, {"SENATE": [], "ASSEMBLY": []}


def owner_of_vote(steps, code, owner):
    """A committee vote's committee: the step's owner is the committee for the recommendation codes."""
    return owner


_NAMES = {}


def sponsor_names():
    """Legislator id -> name, from every year's bills ("Rep. Whyte, Stephen L." -> "Stephen L. Whyte") and the member list,
    for members no longer serving."""
    if not _NAMES:
        for f in glob.glob(os.path.join(P.DATA, "[0-9]" * 4, "bills", "*.json")):
            b = json.load(open(f))
            for k in ("primeSponsor", "floorSponsor"):
                i, n = b.get(k), b.get(k + "Name") or ""
                m = re.match(r"(?:Rep|Sen)\. ([^,]+), (.+)$", n)
                if i and m:
                    _NAMES.setdefault(i, f"{m.group(2)} {m.group(1)}")
    return _NAMES


_TITLES = {}


def _titles(session):
    if session not in _TITLES:
        out = {}
        for f in glob.glob(os.path.join(folder(session), "bills", "*.json")):
            b = json.load(open(f))
            if (b.get("lastAction") or b.get("lastaction") or "").startswith(("Governor Signed", "Became Law", "Governor Line")):
                continue  # a law isn't tried again
            num = b.get("billNumber") or b.get("bill") or ""
            out.setdefault(text(b.get("shortTitle") or b.get("shorttitle")).lower(), []).append(
                (f"{re.match(r'[A-Z]+', num).group(0)}{int(re.sub(r'D', '', re.sub(r'[^0-9]', '', num)))}", b.get("primeSponsor") or b.get("sponsor")))
        _TITLES[session] = out
    return _TITLES[session]


def earlier(session, title, who):
    """The same bill in the two years before: the same short title with the same sponsor, or a title only one bill had."""
    out = set()
    k = title.lower()
    if len(k.split()) < 3:
        return out
    for y in (session - 1, session - 2):
        if y not in sessions():
            continue
        old = _titles(y).get(k, [])
        same = [n for n, sp in old if sp and sp == who]
        if same:
            out.add((y, same[0]))
        elif len(old) == 1:
            out.add((y, old[0][0]))
    return out


def agendas(session):
    return {}


def parties(session, recs):
    return {k: v for k, v in _PARTIES.get(session, {}).items() if v in ("D", "R")}
