"""Wisconsin's bills (downloaded by states/wi/fetch.py from docs.legis.wisconsin.gov) in the shape build_data.py reads.
Assembly and Senate bills of each two-year regular session, and the joint resolutions proposing constitutional amendments
(AJR/SJR whose relating clause ends "(first consideration)" or "(second consideration)"); other resolutions and special
sessions are left out. An amendment must pass two successive Legislatures by a majority of each house, then go to the
voters (Wisconsin Constitution, Art. XII, Sec. 1); it never goes to the governor. A joint resolution is "adopted" in the
first house ("Read a third time and adopted, Ayes 54, Noes 44") and "concurred in" by the second.

Each bill's history line has its date, house and action: "Read first time and referred to committee on X", "Report
passage recommended by committee on X, Ayes 4, Noes 2", "Placed on calendar 2-13-2024", "Read a third time and passed,
Ayes 53, Noes 45" (the first house), "Read a third time and concurred in" (the second), "Assembly Amendment 1 concurred
in" (the first house agreeing to the second's change), "Report correctly enrolled", "Presented to the Governor on
3-21-2024", "Report approved by the Governor on 3-29-2024. 2023 Wisconsin Act 123" or "... with partial veto", "Report
vetoed by the Governor". Bills still pending in the spring of the second year "Failed to pass pursuant to Senate Joint
Resolution 1". "What it does" is the Legislative Reference Bureau's analysis. Floor votes are member by member.
"""
import glob, json, os, re
from datetime import datetime
from zoneinfo import ZoneInfo

from states.wi import profile as P

HOUSE = {"S": "Senate", "A": "Assembly"}
CURRENT = P.session_of(datetime.now(ZoneInfo(P.TIMEZONE)).year)
_PARTIES = {}


def folder(session):
    return os.path.join(P.DATA, str(session))


def sessions():
    return sorted(int(os.path.basename(f)) for f in glob.glob(os.path.join(P.DATA, "[0-9]" * 4))
                  if len(glob.glob(os.path.join(f, "bills", "*.json"))) > 1000)


def text(x):
    return re.sub(r"\s+", " ", x or "").strip()


def load(session, name, default):
    try:
        return json.load(open(os.path.join(folder(session), name)))
    except (OSError, ValueError):
        return default


def committee(a):
    m = re.search(r"\b(?:joint )?(?:survey )?committee on (.+?)(?:,\s*Ayes.*|\s+pursuant.*)?$", a, re.I)
    return re.sub(r"^(?:Assembly|Senate)\s+", "", m.group(1)).strip() if m else None


def decode(h):
    """One history line -> (house, shared wording)."""
    a, house = text(h.get("action")), {"Assembly": "A", "Senate": "S"}.get(h.get("house"), "")
    low = a.lower()
    if re.search(r"referred to (?:joint )?committee on", low) and not low.startswith("report"):
        return house, f"REFERRED TO {committee(a).upper()}" if committee(a) else a
    if re.match(r"report (?:passage|concurrence|introduction)(?: as amended)? recommended", low):
        return house, "REPORTED"
    if re.match(r"report (?:rejection|nonconcurrence|indefinite postponement) recommended", low):
        return house, "Committee recommended it fail"
    if re.match(r"placed on calendar|available for scheduling|read a second time", low):
        return house, "PLACED ON FLOOR"
    if re.match(r"read a third time and (?:passed|concurred in|adopted)|(?:concurred in as amended|adopted|passed), ayes", low):
        return house, f"PASSED {HOUSE.get(house, 'ASSEMBLY').upper()}"
    if re.match(r"(?:assembly|senate) (?:substitute )?amendment .*concurred in", low):
        return house, "CONCURRED"
    if re.match(r"report correctly enrolled", low):
        return house, "ENROLLED"
    if re.match(r"presented to the governor", low):
        return "G", "DELIVERED TO GOVERNOR"
    if re.match(r"report approved by the governor", low):
        return "G", "SIGNED"
    if re.match(r"report vetoed by the governor", low):
        return "G", "VETOED"
    if re.search(r"failed to (?:pass|adopt|concur in) pursuant to", low):
        return house, "Died at the end of the session"
    if re.match(r"(?:failed|refused) to (?:pass|adopt|concur)|indefinitely postponed", low):
        return house, "FAILED" if "ayes" in low else a
    return house or "G", a


def tally(a):
    m = re.search(r"Ayes (\d+), Noes (\d+)", a)
    return (int(m.group(1)), int(m.group(2))) if m else None


CONSIDERATION = re.compile(r"\s*\((first|second) consideration\)", re.I)


def is_amendment(b):
    return bool(re.match(r"[AS]JR\d+$", b.get("number") or "")) and bool(CONSIDERATION.search(text(b.get("relating"))))


_RELATING = {}


def _amendments(session):
    """Relating clause without "(first consideration)" -> [(number, stage reached)] for a session's amendments."""
    if session not in _RELATING:
        out = {}
        for f in glob.glob(os.path.join(folder(session), "bills", "?JR*.json")):
            b = json.load(open(f))
            if is_amendment(b):
                out.setdefault(CONSIDERATION.sub("", text(b.get("relating"))).lower().rstrip(". "), []).append(b["number"])
        _RELATING[session] = out
    return _RELATING[session]


_BILLS = {}


def _bills(session):
    """Relating clause -> [(bill, first author's name)] for a session's bills."""
    if session not in _BILLS:
        out = {}
        for f in glob.glob(os.path.join(folder(session), "bills", "[AS]B*.json")):
            b = json.load(open(f))
            a = (b.get("authors") or [{}])[0]
            out.setdefault(text(b.get("relating")).lower().rstrip(". "), []).append((b["number"], text(a.get("name")).lower()))
        _BILLS[session] = out
    return _BILLS[session]


def earlier(session, b):
    """The same measure in the Legislature before. A second-consideration amendment: the joint resolution with the same
    relating clause. A bill: the same relating clause and the same first author, or a clause of six words or more that only
    one bill has in each session."""
    if is_amendment(b):
        old = _amendments(session - 2).get(CONSIDERATION.sub("", text(b.get("relating"))).lower().rstrip(". "), [])
        return {(session - 2, old[0])} if len(old) == 1 else set()
    if not os.path.isdir(os.path.join(folder(session - 2), "bills")):
        return set()
    k = text(b.get("relating")).lower().rstrip(". ")
    who = text((b.get("authors") or [{}])[0].get("name")).lower()  # by name: member ids change each session
    old = _bills(session - 2).get(k, [])
    same = [n for n, a in old if a and a == who]
    if same:
        return {(session - 2, same[0])}
    if len(old) == 1 and len(_bills(session).get(k, [])) == 1 and len(k.split()) >= 6:
        return {(session - 2, old[0][0])}
    return set()


def members_index(session):
    """Roll-call names -> seat ids: Assembly "ALLEN" / "JACOBSON, B"; Senate names in capitals cut to 14 characters."""
    path = os.path.join(P.DATA, f"contacts_{session}.json")
    people = json.load(open(path))["people"] if os.path.exists(path) else {}
    out = {}
    for sid, p in people.items():
        h = sid[0]
        last = p["name"].split()[-1].upper() if not re.search(r"\b(Jr|Sr|II|III)\.?$", p["name"]) else p["name"].split()[-2].rstrip(",").upper()
        first = p["name"][:1].upper()
        two = " ".join(re.sub(r",?\s+(?:Jr|Sr|II|III)\.?$", "", p["name"]).split()[-2:]).upper()  # "MOORE OMOKUNDE"
        for k in {(h, last), (h, last[:14]), (h, two), (h, two[:14])}:  # (the same key when the name is short)
            out.setdefault(k, set()).add(sid)
        out[(h, f"{last}, {first}")] = {sid}
    return {k: next(iter(v)) for k, v in out.items() if len(v) == 1}


def load_session(session):
    """Read one session's bills and return (records, bill number -> record index, fetched time, delegation)."""
    path = os.path.join(P.DATA, f"contacts_{session}.json")
    people = json.load(open(path))["people"] if os.path.exists(path) else {}
    by_id = {str(p.get("id")): (sid, p) for sid, p in people.items() if p.get("id")}
    seat = members_index(session)
    members = {str(m.get("id")): m for m in load(session, "members.json", [])}
    parties = _PARTIES.setdefault(session, {})

    def person(a, h):
        hit = by_id.get(str(a.get("id")))
        m = members.get(str(a.get("id"))) or {}
        name = hit[1]["name"] if hit else m.get("fullName") or text(a.get("name"))
        party = (m.get("party") or (hit[1].get("party") if hit else "") or "")[:1]
        if party:
            parties[(h, name)] = party
        return name

    files = glob.glob(os.path.join(folder(session), "bills", "*.json"))
    fetched = datetime.fromtimestamp(max(os.path.getmtime(f) for f in files), ZoneInfo(P.TIMEZONE)).strftime("%Y-%m-%d %H:%M")
    texts, recs, index = {}, [], {}
    for f in sorted(files, key=lambda f: (os.path.basename(f)[0], int(re.sub(r"\D", "", os.path.basename(f)) or 0))):
        b = json.load(open(f))
        p = b["number"]
        amend = is_amendment(b)
        if p[:2] not in ("AB", "SB") and not amend:
            continue
        origin = p[0]
        steps = [(h.get("date") or "",) + decode(h) + (text(h.get("action")), h) for h in b.get("history") or []]
        # "Report approved by the Governor with partial veto": a law with parts vetoed (the page's partlyVetoed()).
        if any(re.search(r"partial veto", s[3], re.I) for s in steps):
            steps.append(("", "G", "Signed with item vetoes", "", {}))
        passed = set()
        for s in steps:
            if s[2].startswith("PASSED"):
                passed.add(s[1])
        texts_ = [s[2] for s in steps]
        act = next((re.search(r"Wisconsin Act (\d+)", s[3]).group(1) for s in steps if re.search(r"Wisconsin Act \d+", s[3])), None)
        if amend:
            # Passed both houses: the second house concurred in the same text, or the first agreed to its changes.
            last = max((i for i, s in enumerate(steps) if s[2].startswith("PASSED") and s[1] != origin), default=None)
            agreed = last is not None and (not re.search(r"as amended", steps[last][3], re.I)
                                           or any(s[2] == "CONCURRED" and s[1] == origin for s in steps[last + 1:]))
            stage = 3 if "ENROLLED" in texts_ or (len(passed) == 2 and agreed) else 2 if passed else None
        elif "VETOED" in texts_:
            stage = 6
        elif "SIGNED" in texts_:
            stage = 5
        elif "DELIVERED TO GOVERNOR" in texts_:
            stage = 4
        elif "ENROLLED" in texts_:
            stage = 3
        elif passed:
            stage = 2
        else:
            stage = None
        if stage is not None and stage >= 3:
            passed = {"S", "A"}
        where_h, place, comm = origin, "desk", None
        for d, h, t, a, _ in steps:
            if t.startswith("REFERRED TO"):
                where_h, place, comm = (h if h in HOUSE else where_h), "committee", t[len("REFERRED TO "):]
            elif t in ("REPORTED", "PLACED ON FLOOR"):
                where_h, place, comm = (h if h in HOUSE else where_h), "floor", None
            elif t.startswith("PASSED"):
                place, comm = "desk", None
                where_h = "S" if h == "A" else "A"
        if stage is None:
            stage = 1 if place == "floor" else 0
        proper = lambda c: re.sub(r"\b(And|Of|The|On|For|To|In)\b", lambda m: m.group(1).lower(), c.title()).replace("Ai", "AI")
        comm = proper(comm) if comm else None
        refs = [(s[1] if s[1] in HOUSE else origin, proper(s[2][len("REFERRED TO "):])) for s in steps if s[2].startswith("REFERRED TO")]
        comm_list = sorted({f"{h} · {c}" for h, c in refs})
        relating = re.sub(r"\s*\((?:FE|FE\))\)?$", "", text(b.get("relating"))).rstrip(". ")  # "(FE)": has a fiscal estimate
        title = relating[:1].upper() + relating[1:] if relating else text(b.get("title"))
        if amend:
            title = "Constitutional amendment: " + relating  # keeps "(first consideration)": page's amendmentFinal reads it
        topics = list(dict.fromkeys((["const"] if amend else []) + [v for k, v in P.COMMITTEE_TOPICS.items() if any(k.lower() in c.lower() for _, c in refs)] +
                                    [k for k in P.TOPIC_WORDS if P.TOPIC_WORDS[k].search(title)]))
        first = next((i for i, s in enumerate(steps) if s[2].startswith("REFERRED TO")), None)
        left = first is not None and any(t in ("REPORTED",) or t.startswith("PASSED") for _, _, t, _, _ in steps[first + 1:])
        fate = "passed" if left else "defeated" if "Committee recommended it fail" in texts_ else "none"
        names = [person(a, origin) for a in b.get("authors") or []]
        other = "S" if origin == "A" else "A"
        cos = names[1:] + [person(a, other) for a in b.get("cosponsors") or []]
        sponsor = names[0] if names else (re.sub(r"^Introduced by\s+", "", text(b.get("by"))).split(",")[0] or "—")
        analysis = [t for kind, t in b.get("analysis") or [] if kind == "text" and text(t)]
        if analysis:
            texts[p] = {"statement": "\n".join(text(t) for t in analysis[:6]), "label": "The Legislative Reference Bureau's analysis"}
        if stage == 0 and comm:
            desc = f"In {HOUSE[where_h]} committee"
        elif stage <= 1 and place == "floor":
            desc = f"On the {HOUSE[where_h]} floor"
        elif stage >= 2:
            desc = {2: f"Passed the {HOUSE[origin] if origin in passed else HOUSE[other]}", 3: "Passed both houses",
                    4: "On the governor's desk", 5: "Signed into law", 6: "Vetoed"}[stage]
        else:
            desc = steps[-1][3] if steps else "Introduced"

        def dates(test, mode="last"):
            ds = sorted({s[0] for s in steps if test(s[1], s[2]) and s[0]})
            return {"first": ds[0], "last": ds[-1], "all": ";".join(ds)}[mode] if ds else ""

        votes = []
        for d, h, t, a, raw in steps:
            if h not in HOUSE or not (t.startswith("PASSED") or t in ("CONCURRED", "FAILED")) or not tally(a):
                continue
            names_, totals = [], None
            for vid in raw.get("votes") or []:
                v = load(session, os.path.join("votes", f"{vid}.json"), {})
                if v.get("totals"):
                    t = v["totals"]
                    totals = (t.get("Y", t.get("yes", 0)), t.get("N", t.get("no", 0)))
                for m in v.get("members") or []:
                    if m.get("vote") == "Y":
                        continue
                    n = text(m.get("name")).upper()
                    names_.append([seat.get((h, n)) or seat.get((h, n[:14])) or f"{h}?{n.title()}", "N" if m.get("vote") == "N" else "A"])
            # The roll call's own totals over the history line's (SB 541 of 2023: "Noes 8", nine noes by name).
            votes.append([h, "F", None, d] + list(totals or tally(a)) + [names_])
        action_dates = [s[0] for s in steps if s[0]]
        rec = {
            "nums": [p], "base": [p], "prev": earlier(session, b),
            "title": title, "summary": "", "act": "", "lawCode": "", "law": None, "laws": [],
            "comms": comm_list, "topics": topics, "places": [], "narrow": P.narrow_kind(title),
            "commFate": fate, "mainTopic": topics[0] if topics else "", "local": "local" in topics,
            "senDeleg": False, "asmDeleg": False, "budget": bool(re.search(r"state finances and appropriations", title, re.I)),
            "passedS": "S" in passed, "passedA": "A" in passed, "program": None,
            "stage": stage, "passedIn": HOUSE[origin] if stage == 2 and origin in passed else HOUSE[other] if stage == 2 else None,
            "chapter": int(act) if act and stage == 5 else None,
            "veto": None, "memo": "", "vetoMemo": None,
            "simText": f"{title} {' '.join(analysis[:2])}",
            "comm": comm if stage == 0 and place == "committee" else None,
            "first": min(action_dates, default=f"{session}-01-01"),
            "last": max(action_dates, default=f"{session}-01-01"),
            "cosp": len(cos),
            "keyDates": [
                dates(lambda h, t: t == "REPORTED", "first"),
                dates(lambda h, t: t == "PASSED SENATE", "all"),
                dates(lambda h, t: t == "PASSED ASSEMBLY", "all"),
                "",
                dates(lambda h, t: t == "DELIVERED TO GOVERNOR"),
                dates(lambda h, t: t == "SIGNED"),
                dates(lambda h, t: t == "VETOED"),
            ],
            "votes": votes, "firstComms": [(refs[0][0], refs[0][1], left)] if refs else [],
            "vers": [{"p": p, "sponsor": sponsor, "district": 0, "cosponsors": cos, "primes": 1, "cosp": len(cos),
                      "statusDesc": desc, "committee": comm if place == "committee" and stage in (0, 2) else None,
                      "actions": [[s[0], s[2]] for s in steps]}],
        }
        index[p] = len(recs)
        recs.append(rec)
    json.dump(texts, open(os.path.join(P.DATA, f"texts_{session}.json"), "w"), ensure_ascii=False)
    return recs, index, fetched, {"SENATE": [], "ASSEMBLY": []}


def agendas(session):
    return {}


def parties(session, recs):
    return {k: v for k, v in _PARTIES.get(session, {}).items() if v in ("D", "R")}
