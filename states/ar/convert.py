"""Arkansas's bills (downloaded by states/ar/fetch.py from the Bureau of Legislative Research's files and, for sessions
with no kept copy, arkleg.state.ar.us's bill pages) in the shape build_data.py reads. A page a year: the regular session
in odd years ("2025R"), the fiscal session in even years ("2026F"); extraordinary sessions are left out. House and Senate
bills, plus the joint resolutions that propose constitutional amendments; other resolutions are left out.

Each history line has a time, the house that acted, and the action as written, in each house's own stamp wording: "Read
the first time, rules suspended, read the second time and referred to the Committee on JUDICIARY COMMITTEE- HOUSE"
(House) or "Read first time, rules suspended, read second time, referred to JUDICIARY COMMITTEE - SENATE" (Senate);
"Returned by the Committee Do Pass" / "..., with the recommendation that it Do Pass" (approved), "... that it do not
pass" (voted down), "Recommended for study in the Interim ..." (set aside); "Read the third time and passed" (the
passage; joint resolutions are "adopted" or "concurred in"); "The vote by which HB1001 Passed was expunged" (undone);
"Senate amendment No. 1 read and concurred in" (the first house agreeing to the other's changes); "TO BE ENROLLED" /
"ORDERED ENROLLED" (passed both houses); "Correctly enrolled and ordered transmitted to the Governor's Office" /
"DELIVERED TO GOVERNOR." (sent); "Notification that HB1001 is now Act 2" (a law: signed, or law without signature, or
over a veto); "Returned to House from Governor Having Been Vetoed"; "... Line-Item Vetoed" (a law, an item vetoed);
"Returned from the Governor as requested" (the house took it back). Joint resolutions go through the same enrolling and
are "Approved by the Governor", a formality: they go to the voters, and stop at "passed both houses" here.
Members' votes come from the roll-call pages fetch.py saves (votes/), when they've been read; the files carry only the
roll call's number, so a vote not yet read isn't shown. There are no summaries beyond the subtitle, which is the title
here, so there's no "What it does".
"""
import functools, glob, json, os, re
from datetime import datetime
from zoneinfo import ZoneInfo

from fetch_contacts import name_key
from states.ar import profile as P

HOUSE = {"S": "Senate", "H": "House"}
CURRENT = P.session_of(datetime.now(ZoneInfo(P.TIMEZONE)).year)
_PARTIES = {}


def biennium(session):
    """The General Assembly's odd first year, which names the folder: 2026 -> 2025."""
    return session - (session + 1) % 2


def folder(session):
    return os.path.join(P.DATA, str(biennium(session)))


def text(x):
    return re.sub(r"\s+", " ", (x or "").replace("\x00", "")).strip()


@functools.lru_cache(maxsize=None)
def rows(b, name):
    """A pipe file's records (data/ar/<biennium>/<name>), fields stripped; empty fields hold a NUL in the files."""
    try:
        with open(os.path.join(P.DATA, str(b), name), encoding="utf-8") as f:
            return tuple([text(x) for x in line.rstrip("\n").split("|")] for line in f if line.strip())
    except OSError:
        return ()


def page_bills(session):
    """Bills read from arkleg's pages for a session with no kept copy of the files (2024F)."""
    return glob.glob(os.path.join(folder(session), P.session_id(session), "bills", "*.json"))


@functools.lru_cache(maxsize=None)
def sessions():
    out = []
    for f in glob.glob(os.path.join(P.DATA, "[0-9]" * 4)):
        b = int(os.path.basename(f))
        for s in (b, b + 1):
            sid = P.session_id(s)
            n = sum(1 for r in rows(b, "LegislativeMeasures.txt") if len(r) >= 18 and r[17] == sid and r[1] == "B")
            if n + len(page_bills(s)) > 100:
                out.append(s)
    return tuple(sorted(out))


def is_amendment(kind, subtitle):
    """A joint resolution proposing an amendment to the Arkansas Constitution (not an application to Congress for an
    Article V convention): "A CONSTITUTIONAL AMENDMENT TO ...", "AN AMENDMENT TO THE ARKANSAS CONSTITUTION ...", "THE
    CITIZENS ONLY VOTING AMENDMENT."."""
    return kind == "JR" and bool(re.search(r"\bCONSTITUTION(?:AL)? AMENDMENT\b|\bAMENDMENT TO (?:THE )?ARKANSAS CONSTITUTION\b|AMENDMENT\.?$", subtitle, re.I)) \
        and not re.search(r"UNITED STATES CONGRESS|ARTICLE V CONVENTION", subtitle, re.I)


def is_appropriation(subtitle):
    """An appropriation bill: "AN ACT FOR THE DEPARTMENT OF EDUCATION APPROPRIATION FOR THE 2026-2027 FISCAL YEAR.", "AN
    ACT TO MAKE AN APPROPRIATION FOR ...", "... REAPPROPRIATION ..."; most of a fiscal session's bills."""
    return bool(re.search(r"\b(?:RE)?APPROPRIATIONS?\b", subtitle, re.I)) and not re.match(r"TO\b", subtitle, re.I)


SMALL = {"a", "an", "and", "as", "at", "by", "for", "from", "in", "into", "of", "on", "or", "the", "to", "with"}
# Words kept capitalized in a sentence-cased subtitle.
PROPER = re.compile(r"\b(arkansas|united states|u\.s\.|america\w*|little rock|fort smith|fayetteville|jonesboro|springdale|"
                    r"rogers|conway|bentonville|pine bluff|texarkana|hot springs|benton|medicaid|medicare|internet|"
                    r"national guard|god|english|native american|ozarks?|mississippi|missouri|delta|razorback\w*|"
                    r"january|february|march|april|may(?= \d)|june|july|august|september|october|november|december)\b", re.I)
# The state's departments, then other bodies named "X of Y": "DEPARTMENT OF HUMAN SERVICES", "UNIVERSITY OF ARKANSAS".
DEPARTMENTS = re.compile(r"\b(department of (?:agriculture|commerce|corrections|education|energy and environment|finance and "
                         r"administration|health|human services|inspector general|labor and licensing|the military|parks, "
                         r"heritage,? and tourism|public safety|transformation and shared services|veterans affairs))\b", re.I)
BODY = re.compile(r"\b((?:department|division|office|university|college|bureau) "
                  r"(?:of|for) (?:the )?(?!(?:the|a|an)\b)[a-z]+)\b", re.I)
ACRONYMS = re.compile(r"\b(uams|aetn|ualr|uapb|uafs|asu|atu|saumag|sau|ua|adfa|adeq|ahtd|ardot|dfa|dhs|ade|k-12|ii|iii|iv)\b", re.I)


def caps(words):
    """Each word capitalized but the small ones (after the first): "department of human services" -> "Department of
    Human Services"."""
    return " ".join(w if i and w in SMALL else w[:1].upper() + w[1:] for i, w in enumerate(words.split(" ")))


def titled(subtitle):
    """A subtitle in capitals -> a sentence: "TO AMEND THE LAW CONCERNING THE ARKANSAS STATE POLICE." -> "To amend the law
    concerning the Arkansas State Police"; an appropriation's agency is a name: "AN ACT FOR THE DEPARTMENT OF EDUCATION -
    MARTIN LUTHER KING, JR. COMMISSION APPROPRIATION FOR THE 2024-2025 FISCAL YEAR." -> "Department of Education - Martin
    Luther King, Jr. Commission appropriation for the 2024-2025 fiscal year"."""
    t = text(subtitle).rstrip(".;, ")
    if re.search(r"[a-z]", t):
        return t[:1].upper() + t[1:]
    t = t.lower()
    m = re.match(r"(?:an act (?:for|to make an appropriation for) (?:the )?|the )?(.+?) ((?:re)?appropriations?\b.*)$", t)
    if m and not re.match(r"to |an act\b", m.group(1)):
        t = f"{caps(m.group(1))} {m.group(2)}"
    t = DEPARTMENTS.sub(lambda m: caps(m.group(1)), t)
    t = BODY.sub(lambda m: caps(m.group(1)), t)
    t = PROPER.sub(lambda m: m.group(1).upper() if m.group(1).lower() == "u.s." else m.group(1).title(), t)
    # "arkansas state police", "arkansas lottery": what follows "Arkansas" and ends in a body's word is a name.
    t = re.sub(r"\bArkansas ((?:[a-z]+ ){0,3}(?:police|commission|board|agency|lottery|program|fund|code|constitution|"
               r"department|university|college|corporation|authority|council|system|association))\b",
               lambda m: "Arkansas " + caps(m.group(1)), t)
    # Named acts: "to create the brighter start act of 2025" -> "the Brighter Start Act of 2025".
    t = re.sub(r"\b((?:create|establish|known as|cited as|enact|amend) the )((?:[a-z0-9'’-]+,? ){1,8}act)\b",
               lambda m: m.group(1) + caps(m.group(2)), t, flags=re.I)
    t = re.sub(r"\b(act|amendment|article) (\d+)\b", lambda m: f"{m.group(1).title()} {m.group(2)}", t)
    t = ACRONYMS.sub(lambda m: m.group(1).upper(), t)
    return t[:1].upper() + t[1:]


def committee(c):
    """A referral's committee as written -> its name: "the Committee on JUDICIARY COMMITTEE- HOUSE" -> "Judiciary";
    "STATE AGENCIES & GOVT'L AFFAIRS-SENATE" -> "State Agencies and Governmental Affairs"; "JOINT BUDGET COMMITTEE" ->
    "Joint Budget"; "HOUSE RULES" -> "Rules"; "HOUSE JOURNAL; ENGROSSED AND ENROLLED BILLS" -> "Journal, Engrossed and
    Enrolled Bills"."""
    c = text(c).upper().rstrip(". ")
    c = re.sub(r"^(?:RE-?REFERRED TO |REASSIGN TO TRANSFER TO )?(?:THE )?(?:COMMITTEE ON )?", "", c)
    c = re.sub(r"\s*-\s*(?:HOUSE|SENATE|JOINT|S)$", "", c)
    c = re.sub(r"\s+COMMITTEE$", "", c)
    c = re.sub(r"^(?:HOUSE|SENATE) (?=RULES|MANAGEMENT|EFFICIENCY|JOURNAL)|^JOINT COMMITTEE ON ", "", c)
    c = c.replace("GOVT'L", "GOVERNMENTAL").replace(";", ",").replace(", &", ", AND").replace("&", "AND")
    c = re.sub(r"\s+", " ", c).strip()
    return " ".join(w.lower() if i and w.lower() in SMALL else w.capitalize() for i, w in enumerate(c.split(" ")))


def decode(a, h):
    """One history line, as written, in house h -> the shared wording the rules use, or the line itself."""
    if re.search(r"\b(?:expunge|reconsider)", a, re.I):
        # "The vote by which HB1001 Passed was expunged", "Motion to Expunge the Vote by which SB5 passed. Motion carried."
        if re.search(r"(?:vote by which \S+ ?\d* passed|batch vote|expunge passage)", a, re.I) and \
                re.search(r"was expunged|motion carried|carried\.?$|passed\.?$", a, re.I) and not re.search(r"motion failed|failed of adoption|objected", a, re.I):
            return "PASSAGE EXPUNGED"
        return a
    if re.search(r"\bmotion\b", a, re.I) and re.search(r"\b(?:fail|failed|objected)\b", a, re.I):
        return a  # a motion to refer, extract or recall that failed
    m = re.search(r"(?:referred to|Re-referred to|transfer(?:s)? to|Transfer to)(?: reassign to transfer to)? (?:the )?(?:Committee on )?(.+)$", a, re.I)
    if m and not re.search(r"\bCALENDAR\b", m.group(1)):
        if re.match(r"Recommended for study", a, re.I):
            return "INTERIM STUDY"
        return f"REFERRED TO {committee(m.group(1)).upper()}"
    if re.match(r"Recommended for study in the Interim", a, re.I):
        return "INTERIM STUDY"
    if re.search(r"placed on (?:the )?calendar|transfers to CALENDAR|recommended do pass", a, re.I) and not re.search(r"failed", a, re.I):
        return "PLACED ON FLOOR"
    if re.match(r"Returned by the Committee", a, re.I):
        if re.search(r"do not pass", a, re.I):
            return "REPORTED DO NOT PASS"
        return "REPORTED"
    if re.match(r"Read (?:the )?third time,? and passed|Read (?:the )?third time, concurred in", a, re.I):
        return f"PASSED {HOUSE[h].upper()}"
    if re.match(r"Read (?:the )?third time and failed|Read third time and failed to pass|Upon Sounding of the Ballot \S+ failed", a, re.I):
        return "FAILED"
    if re.search(r"(?:amendments? (?:No\.? ?)?#?[\d ,&]+ )?read(?: first time, rule suspended, read second time)? and concurred in", a, re.I) \
            and re.search(r"amendment", a, re.I) and not re.search(r"fail", a, re.I):
        return "CONCURRED"
    if re.match(r"(?:TO BE|ORDERED) ENROLLED", a, re.I):
        return "ENROLLED"
    if re.search(r"ordered (?:transmitted|delivered) to the Governor|^DELIVERED TO GOVERNOR", a, re.I):
        return "DELIVERED TO GOVERNOR"
    if re.search(r"returned from the Governor as requested|Return from Governor's office as requested", a, re.I):
        return "RECALLED FROM GOVERNOR"
    if re.search(r"line[- ]item vetoed", a, re.I):
        return a
    if re.search(r"Governor Vetoed|from (?:the )?Governor having been vetoed", a, re.I):
        return "VETOED"
    if re.search(r"veto overridden", a, re.I):
        return "VETO OVERRIDDEN"
    if re.match(r"Withdrawn by author|WITHDRAWN BY AUTHOR", a, re.I):
        return "Withdrawn by the author"
    return a


def jr_passage(a):
    """A joint resolution's passage: "Read the third time and adopted.", "Read and adopted and ordered transmitted to the
    Senate.", "Resolution read and concurred in." (its roll call is on the next line, "Returned To the House as concurred
    in.")."""
    return bool(re.match(r"(?:Resolution )?Read (?:the third time )?and (?:adopted|concurred in)|Read and adopted", a, re.I))


def members(b):
    """A biennium's members file: (house, Sponsor Name) -> {name, district, party}."""
    out = {}
    for r in rows(b, "LegislativeMembers.txt"):
        if len(r) < 19 or r[6] not in ("Senator", "Representative") or not r[8].isdigit():
            continue
        h = "S" if r[6] == "Senator" else "H"
        out[(h, r[18])] = {"name": text(f"{r[1]} {r[2]}"), "district": int(r[8]), "party": r[17][:1]}
    return out


def file_bills(session):
    """A session's bills from the files: measure -> {fields, sponsors, actions}, in the bill pages' shape."""
    b, sid = biennium(session), P.session_id(session)
    heads = ["Originating Chamber", "Bill Type", "Bill Number", "Bill Subtitle", "S1", "S2", "S3", "S4", "S5", "S6", "Bill ID",
             "Bill Sponsor", "Act Number", "Introduction Date", "Act Date", "Original Sponsor", "Measure Number", "Session ID"]
    bills = {}
    for r in rows(b, "LegislativeMeasures.txt"):
        if len(r) >= 18 and r[17] == sid and r[1] in ("B", "JR"):
            x = dict(zip(heads, r))
            x["sponsors"], x["actions"] = [], []
            bills[x["Measure Number"]] = x
    if not bills:
        return {}
    by_id = {x["Bill ID"]: x for x in bills.values() if x["Bill ID"]}
    for r in sorted(rows(b, "BillSponsors.txt"), key=lambda r: (int(r[6]) if r[6].isdigit() else 99, int(r[0]) if r[0].isdigit() else 0)):
        if len(r) >= 7 and r[5] in by_id:
            by_id[r[5]]["sponsors"].append({"Sponsor": r[4], "Sponsor Type": "Primary" if r[6] == "1" else "CoSponsors"})
    for r in rows(b, "ChamberActions.txt"):
        if len(r) >= 11 and r[10] == sid and r[9] in bills:
            bills[r[9]]["actions"].append({"ID": r[0], "Action Datetime": r[5], "Action": r[6], "Action Chamber": r[7],
                                           "RCS Number": r[8], "Action Stamp": r[4]})
    return bills


@functools.lru_cache(maxsize=None)
def all_bills(session):
    bills = file_bills(session)
    if not bills:
        for f in page_bills(session):
            x = json.load(open(f))
            bills[x["Measure Number"]] = x
    return bills


def vote_file(session, house, rcs, measure):
    path = os.path.join(folder(session), "votes", f"{P.session_id(session)}-{house}{rcs}-{measure}.json")
    try:
        return json.load(open(path))
    except (OSError, ValueError):
        return None


VOTE_CODE = {"Nays": "N", "Non Voting": "A", "Present": "B", "Excused": "E"}


def fill_missing(groups, counts, house):
    """Put back a member the roll-call page counts but doesn't list. The 2023-24 pages never list Sen. Alan Clark ("A.
    Clark"): each Senate roll call's groups add up to 35 but name 34 (HB1024's Senate vote: "Nays: 2", one name). When the
    names a page leaves out are exactly the house's members missing from every group, and only one group is short, they
    belong to that group; otherwise the page's names are kept as they are."""
    short = {g: int(counts.get(g) or 0) - len(groups[g]) for g in groups}
    if not any(n > 0 for n in short.values()) or any(n < 0 for n in short.values()):
        return
    listed = {n for ns in groups.values() for n in ns}
    missing = sorted(house - listed)
    lacking = [g for g, n in short.items() if n > 0]
    if len(lacking) == 1 and short[lacking[0]] == len(missing):
        groups[lacking[0]] += missing


def load_session(session):
    """Read one year's bills and return (records, bill number -> record index, fetched time, delegation)."""
    b = biennium(session)
    who = members(b)
    # Sponsors' names: this General Assembly's members, then the one before's and after's (members who left).
    named = {**members(b + 2), **members(b - 2), **who}
    by_short = {}  # sponsor name in either house -> [(house, member)]
    for (h, short), m in named.items():
        by_short.setdefault(short, []).append((h, m))
    parties = _PARTIES.setdefault(session, {})
    bills = all_bills(session)
    paths = [os.path.join(P.DATA, str(b), "LegislativeMeasures.txt")] + page_bills(session)
    fetched = datetime.fromtimestamp(max(os.path.getmtime(f) for f in paths if os.path.exists(f)), ZoneInfo(P.TIMEZONE)).strftime("%Y-%m-%d %H:%M")
    recs, index = [], {}
    order = lambda m: (m[0], m[1:].rstrip("0123456789"), int(re.sub(r"\D", "", m) or 0))
    for measure in sorted(bills, key=order):
        x = bills[measure]
        kind = x.get("Bill Type")
        subtitle = text(x.get("Bill Subtitle"))
        amendment = is_amendment(kind, subtitle)
        if kind != "B" and not amendment:
            continue
        origin = x.get("Originating Chamber") or measure[0]
        other = "S" if origin == "H" else "H"
        p = f"{origin}{'J' if kind == 'JR' else 'B'}{int(x['Bill Number'])}"
        acts = sorted(x.get("actions") or [], key=lambda a: (a.get("Action Datetime") or "", int(a.get("ID") or 0)))
        steps = []  # (date, house, shared wording, as written, roll call number)
        for a in acts:
            desc = text(a.get("Action"))
            h = a.get("Action Chamber") if a.get("Action Chamber") in HOUSE else origin
            t = decode(desc, h)
            if amendment and jr_passage(desc):
                t = f"PASSED {HOUSE[h].upper()}"
            steps.append(((a.get("Action Datetime") or "")[:10], h, t, desc, a.get("RCS Number") or ""))
        texts_ = [s[2] for s in steps]
        passed, sent = set(), False
        for _, h, t, _, _ in steps:
            if t.startswith("PASSED"):
                passed.add(h)
            elif t == "PASSAGE EXPUNGED":
                passed.discard(h)
            elif t == "DELIVERED TO GOVERNOR":
                sent = True
            elif t == "RECALLED FROM GOVERNOR":
                sent = False
        act_no = text(x.get("Act Number")) or next((m.group(1) for s in steps for m in [re.search(r"is now Act (\d+)", s[3])] if m), "")
        vetoed = "VETOED" in texts_ and "VETO OVERRIDDEN" not in texts_
        enrolled = "ENROLLED" in texts_
        if amendment:
            stage = 3 if enrolled or sent else (2 if passed else None)
        elif act_no and not vetoed:
            stage = 5  # signed, law without the governor's signature, or over a veto
        elif vetoed:
            stage = 6
        elif sent:
            stage = 4
        elif enrolled:
            stage = 3
        elif passed:
            stage = 2
        else:
            stage = None
        if stage is not None and stage >= 3:
            passed = {"S", "H"}
        where_h, place, comm = origin, "desk", None
        for d, h, t, a, _ in steps:
            if t.startswith("REFERRED TO"):
                where_h, place, comm = h, "committee", t[len("REFERRED TO "):]
            elif t in ("REPORTED", "PLACED ON FLOOR"):
                where_h, place, comm = h, "floor", None
            elif t.startswith("PASSED"):
                place, comm = "desk", None
                where_h = other if h == origin else origin
        if stage is None:
            stage = 1 if place == "floor" else 0
        proper = lambda c: " ".join(w.lower() if i and w.lower() in SMALL else w.capitalize() for i, w in enumerate(c.split(" ")))
        comm = proper(comm) if comm else None
        refs = [(s[1], proper(s[2][len("REFERRED TO "):])) for s in steps if s[2].startswith("REFERRED TO")]
        comm_list = sorted({f"{h} · {c}" for h, c in refs})
        title = titled(subtitle)
        if amendment:
            title = re.sub(r"^(?:A |An )?(?:constitutional amendment|constitution amendment|amendment to the Arkansas Constitution)\s*", "", title, flags=re.I)
            title = "Constitutional amendment" + (f": {title[:1].lower() + title[1:]}" if title else "")
        appropriation = is_appropriation(subtitle)
        topics = list(dict.fromkeys((["const"] if amendment else []) +
                                    [P.COMMITTEE_TOPICS[c] for _, c in refs if c in P.COMMITTEE_TOPICS] +
                                    [k for k in P.TOPIC_WORDS if P.TOPIC_WORDS[k].search(title)]))
        # A bill's first committee: approved, voted down ("do not pass"), set aside for interim study, or no action.
        first_ref = next((i for i, s in enumerate(steps) if s[2].startswith("REFERRED TO")), None)
        after = texts_[first_ref + 1:] if first_ref is not None else []
        fate = ("passed" if "REPORTED" in after or passed or "PLACED ON FLOOR" in after else
                "defeated" if "REPORTED DO NOT PASS" in after else "held" if "INTERIM STUDY" in after else "none")
        # Sponsors: the lead sponsor (the measure's Bill Sponsor), the other primary sponsors, then co-sponsors, each
        # named as the members file has them ("L. Johnson" -> "Lee Johnson"); committees ("Joint Budget Committee") as written.
        names = []
        raw = [x.get("Bill Sponsor") or ""] + [s.get("Sponsor") or "" for s in x.get("sponsors") or []]
        for short in raw:
            short = text(short)
            hits = by_short.get(short, [])  # a name both houses use: the bill's own house's member
            h, m = next((hm for hm in hits if hm[0] == origin), hits[0]) if hits else (origin, None)
            full = m["name"] if m else short
            if m and m["party"] in ("D", "R"):
                parties[(h, full)] = m["party"]
            if full and full not in names:
                names.append(full)
        sponsor = names[0] if names else "—"
        cos = names[1:]
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

        # Members' votes, from the roll-call pages read so far: the bill's passages, failures and concurrences.
        votes = []
        for i, (d, h, t, a, rcs) in enumerate(steps):
            if not rcs or not (t.startswith("PASSED") or t in ("FAILED", "CONCURRED") or re.search(r"concurred in\.?$", a, re.I)):
                continue
            v = vote_file(session, h, rcs, measure)
            if not v:
                continue
            seat = lambda n: (lambda m: f"{h}:{m['district']}" if m else f"{h}?{n}")(who.get((h, n)))
            counts = v.get("counts") or {}
            groups = {g: list((v.get("names") or {}).get(g) or []) for g in ("Yeas",) + tuple(VOTE_CODE)}
            fill_missing(groups, counts, {n for (hh, n) in who if hh == h})
            names_ = [[seat(n), VOTE_CODE[g]] for g in VOTE_CODE for n in groups[g]]
            votes.append([h, "F", None, d, int(counts.get("Yeas") or 0), int(counts.get("Nays") or 0), names_])
        action_dates = [s[0] for s in steps if s[0]]
        act_date = text(x.get("Act Date"))[:10]
        rec = {
            "nums": [p], "base": [p], "prev": earlier(session, x, p),
            "title": title, "summary": "", "act": "", "lawCode": "", "law": None, "laws": [],
            "comms": comm_list, "topics": topics, "places": [], "narrow": P.narrow_kind(title),
            "commFate": fate, "mainTopic": topics[0] if topics else "", "local": "local" in topics,
            "senDeleg": False, "asmDeleg": False, "budget": appropriation,
            "passedS": "S" in passed, "passedA": "H" in passed, "program": None,
            "stage": stage, "passedIn": (HOUSE[origin] if origin in passed else HOUSE[other]) if stage == 2 else None,
            "chapter": int(act_no) if act_no.isdigit() and stage == 5 else None,
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
                dates(lambda h, t: t == "DELIVERED TO GOVERNOR") if stage >= 4 and not amendment else "",
                (act_date or dates(lambda h, t: False) or next((s[0] for s in steps if re.search(r"is now Act", s[3])), "")
                 or max(action_dates, default="")) if stage == 5 else "",
                dates(lambda h, t: t == "VETOED", "first") if stage == 6 else "",
            ],
            "votes": votes, "firstComms": [(refs[0][0], refs[0][1], fate == "passed")] if refs else [],
            "vers": [{"p": p, "sponsor": sponsor, "district": 0, "cosponsors": cos, "primes": 1, "cosp": len(cos),
                      "statusDesc": desc, "committee": comm if place == "committee" and stage in (0, 2) else None,
                      "actions": [[s[0], s[2] if KEEP.match(s[2]) and not re.match(r"Returned", s[3], re.I) else s[3]] for s in steps],
                      "link": bill_link(p, session)}],
        }
        index[p] = len(recs)
        recs.append(rec)
    return recs, index, fetched, {"SENATE": [], "ASSEMBLY": []}


# The shared wording shown in place of the line as written (the rest is kept as written; a vetoed bill's return to its
# house, "Returned to House from Governor Having Been Vetoed", too, after the "Governor Vetoed" line).
KEEP = re.compile(r"^(?:REFERRED TO |REPORTED$|PASSED (?:HOUSE|SENATE)$|DELIVERED TO GOVERNOR$|VETOED$)")


def bill_link(p, session):
    kind = "B" if p[1] == "B" else "JR"
    return f"https://arkleg.state.ar.us/Bills/Detail?id={p[0]}{kind}{p[2:]}&ddBienniumSession={biennium(session)}%2F{P.session_id(session)}"


_TITLES = {}


def _titles(session):
    if session not in _TITLES:
        out = {}
        for m, x in all_bills(session).items():
            act = text(x.get("Act Number")) or any(re.search(r"is now Act", a.get("Action") or "") for a in x.get("actions") or [])
            if act or x.get("Bill Type") != "B" and not is_amendment(x.get("Bill Type"), text(x.get("Bill Subtitle"))):
                continue  # laws aren't tried again (yearly bills share titles); other resolutions aren't shown
            p = f"{x['Originating Chamber']}{'J' if x['Bill Type'] == 'JR' else 'B'}{int(x['Bill Number'])}"
            out.setdefault(text(x.get("Bill Subtitle")).lower(), []).append((p, text(x.get("Bill Sponsor"))))
        _TITLES[session] = out
    return _TITLES[session]


def earlier(session, x, p):
    """The same bill in the two years before: the same subtitle with the same lead sponsor, or a subtitle only one bill
    has in each year. Appropriations aren't linked (each year's are new bills for that year)."""
    out = set()
    k = text(x.get("Bill Subtitle")).lower()
    who = text(x.get("Bill Sponsor"))
    if len(k.split()) < 4 or is_appropriation(k):
        return out
    for y in (session - 1, session - 2):
        if y not in sessions():
            continue
        old = _titles(y).get(k, [])
        same = [n for n, sp in old if sp and sp == who]
        if same:
            out.add((y, same[0]))
        elif len(old) == 1 and len(_titles(session).get(k, [])) <= 1:
            out.add((y, old[0][0]))
    return out


def agendas(session):
    """Bills on committee agendas (CommitteeAgendas.txt): bill -> [["House Judiciary", "2027-02-03T10:00:00"], ...], for
    meetings in the session's year. Times of 12:37 stand for "upon adjournment" (ScheduledMeetings.txt says when), so
    those show the day only."""
    b = biennium(session)
    kinds = {r[1]: r[2] for r in rows(b, "Committees.txt") if len(r) > 2}
    out = {}
    for r in rows(b, "CommitteeAgendas.txt"):
        if len(r) < 15 or not re.match(r"[HS]J?B\d+$", r[8].replace("JR", "J")) or not r[3].startswith(str(session)):
            continue
        m = re.match(r"([HS])(B|JR)(\d+)$", r[8])
        if not m:
            continue
        house = {"H": "House", "S": "Senate"}.get(kinds.get(r[1]), "")
        name = committee(r[2])
        if not name:
            continue
        when = r[3][:10] + ("T00:00:00" if r[3][11:16] == "12:37" else f"T{r[3][11:19]}")
        entry = [f"{house} {name}".strip(), when]
        bill = f"{m.group(1)}{'J' if m.group(2) == 'JR' else 'B'}{m.group(3)}"
        if entry not in out.setdefault(bill, []):
            out[bill].append(entry)
    return out


def parties(session, recs):
    return {k: v for k, v in _PARTIES.get(session, {}).items() if v in ("D", "R")}
