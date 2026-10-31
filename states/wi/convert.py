"""Wisconsin's bills (downloaded by states/wi/fetch.py from docs.legis.wisconsin.gov) in the shape build_data.py reads.
Assembly and Senate bills of each two-year regular session; joint resolutions and special sessions are left out.

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
    if re.match(r"read a third time and (?:passed|concurred in)|concurred in as amended, ayes", low):
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
    if re.search(r"failed to pass pursuant to|failed to concur in pursuant to", low):
        return house, "Died at the end of the session"
    if re.match(r"(?:failed|refused) to pass|indefinitely postponed", low):
        return house, "FAILED" if "ayes" in low else a
    return house or "G", a


def tally(a):
    m = re.search(r"Ayes (\d+), Noes (\d+)", a)
    return (int(m.group(1)), int(m.group(2))) if m else None


def members_index(session):
    """Roll-call names -> seat ids: Assembly "ALLEN" / "JACOBSON, B"; Senate names in capitals cut to 14 characters."""
    path = os.path.join(P.DATA, f"contacts_{session}.json")
    people = json.load(open(path))["people"] if os.path.exists(path) else {}
    out = {}
    for sid, p in people.items():
        h = sid[0]
        last = p["name"].split()[-1].upper() if not re.search(r"\b(Jr|Sr|II|III)\.?$", p["name"]) else p["name"].split()[-2].rstrip(",").upper()
        first = p["name"][:1].upper()
        out.setdefault((h, last), []).append(sid)
        out[(h, f"{last}, {first}")] = [sid]
        out.setdefault((h, last[:14]), []).append(sid)
    return {k: v[0] for k, v in out.items() if len(v) == 1}


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
        if p[:2] not in ("AB", "SB"):
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
        if "VETOED" in texts_:
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
        topics = list(dict.fromkeys([v for k, v in P.COMMITTEE_TOPICS.items() if any(k.lower() in c.lower() for _, c in refs)] +
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
            names_ = []
            for vid in raw.get("votes") or []:
                v = load(session, os.path.join("votes", f"{vid}.json"), {})
                for m in v.get("members") or []:
                    if m.get("vote") == "Y":
                        continue
                    n = text(m.get("name")).upper()
                    names_.append([seat.get((h, n)) or seat.get((h, n[:14])) or f"{h}?{n.title()}", "N" if m.get("vote") == "N" else "A"])
            votes.append([h, "F", None, d] + list(tally(a)) + [names_])
        action_dates = [s[0] for s in steps if s[0]]
        rec = {
            "nums": [p], "base": [p], "prev": set(),
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
