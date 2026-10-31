"""Washington's bills (downloaded by states/wa/fetch.py from the Legislature's web services) in the shape build_data.py
reads. Each bill is one record under its number ("HB1003"); substitutes ("SHB 1003", "E2SSB 5001") are versions of it.

The history lines are plain English and kept as written, except the steps the site's rules use, which are put in the
shared wording ("REFERRED TO HOUSING", "REPORTED", "PASSED HOUSE", "SIGNED"...). The lines don't say which house acted:
committee steps carry the committee's acronym ("HSG - Majority; do pass."), floor votes match a roll call (which names
its house), and otherwise the bill is in its house of origin until it passes, then in the other one. A bill a committee
approves goes to that house's Rules Committee, which decides which bills reach the floor (shown as in the Rules
Committee, like Texas's Calendars); "X file" is Rules' list of bills it won't move.
"""
import glob, html, json, os, re
from collections import defaultdict
from datetime import datetime
from zoneinfo import ZoneInfo

from states.wa import profile as P

HOUSE = {"S": "Senate", "H": "House"}
CURRENT = P.session_of(datetime.now(ZoneInfo(P.TIMEZONE)).year)
VOTE_CODE = {"Nay": "N", "Absent": "A", "Excused": "E"}


def folder(session):
    return os.path.join(P.DATA, str(session))


def sessions():
    return sorted(int(os.path.basename(f)) for f in glob.glob(os.path.join(P.DATA, "[0-9]" * 4))
                  if glob.glob(os.path.join(f, "bills", "*.json")))


def text(x):
    return re.sub(r"\s+", " ", html.unescape(x or "")).strip()


def committees(session):
    """Committee name and acronym -> (house, name), from that biennium's committee list."""
    try:
        rows = json.load(open(os.path.join(folder(session), "committees.json")))
    except (OSError, ValueError):
        rows = []
    out = {}
    for c in rows:
        h = "S" if c.get("Agency") == "Senate" else "H"
        name = text(c.get("Name"))
        out[name.lower()] = (h, name)
        if c.get("Acronym"):
            out[c["Acronym"].upper()] = (h, name)
    return out


def members(session):
    """Member id -> {name, last, house, district, party}, from that biennium's member list."""
    try:
        rows = json.load(open(os.path.join(folder(session), "sponsors.json")))
    except (OSError, ValueError):
        rows = []
    return {m["Id"]: {"name": text(f"{m.get('FirstName', '')} {m.get('LastName', '')}"), "last": text(m.get("LastName")),
                      "house": "S" if m.get("Agency") == "Senate" else "H", "district": int(m.get("District") or 0),
                      "party": (m.get("Party") or "")[:1]} for m in rows}


PASS = re.compile(r"^(?:Third reading, passed|Passed final passage)(?: as recommended by conference committee)?; yeas, (\d+); nays, (\d+)", re.I)
FAILED = re.compile(r"^(?:Third reading, failed|Failed to pass)", re.I)
REFER = re.compile(r"^(?:First reading, )?(?:referred|And refer|Referred) to (.+?)\.?$", re.I)
REPORT = re.compile(r"^(?:([A-Z&]{2,6}) - )?Majority;.*\bdo pass\b", re.I)


def where_to(name, comms):
    """A committee name in a history line -> (house, name), or None. Subcommittees count as their committee."""
    name = re.sub(r"^(?:the )?", "", re.sub(r"\s*\(Not Officially read.*$", "", name.strip()))
    name = re.sub(r"^.* Subcommittee to ", "", name)
    return comms.get(name.lower())


def steps_of(bill, d, comms):
    origin = "H" if bill.startswith("H") else "S"
    other = {"H": "S", "S": "H"}
    rolls = [{"date": (r.get("VoteDate") or "")[:10], "house": "S" if r.get("Agency") == "Senate" else "H",
              "yeas": int((r.get("YeaVotes") or {}).get("Count") or 0)} for r in d.get("rollCalls", [])]
    vote_house = {(r["date"], r["yeas"]): r["house"] for r in rolls}
    house, out = origin, []
    # The history repeats lines (once per version) and isn't in date order: by date, each line once, in the file's order
    # within a day.
    seen, hist = set(), []
    for h in d["history"]:
        k = ((h.get("ActionDate") or "")[:10], text(h.get("HistoryLine")))
        if k not in seen:
            seen.add(k)
            hist.append(h)
    hist.sort(key=lambda h: (h.get("ActionDate") or "")[:10])
    # A few histories stop early (HB 2134 of 2023-24, the transportation budget, ends in committee though ESHB 2134
    # became law): a version's current status that's newer than the history is added, and a status "C 310 L 24"
    # (chapter 310, 2024 Laws) means it became law.
    last = max(((h.get("ActionDate") or "")[:10] for h in hist), default="")
    for v in d.get("versions") or []:
        cs = v.get("CurrentStatus") or {}
        if isinstance(cs, dict) and (cs.get("ActionDate") or "")[:10] > last:
            m = re.match(r"C (\d+) L (\d\d)$", cs.get("Status") or "")
            if m:
                hist.append({"ActionDate": cs["ActionDate"], "HistoryLine": f"Chapter {m.group(1)}, 20{m.group(2)} Laws."})
            elif cs.get("HistoryLine"):
                hist.append({"ActionDate": cs["ActionDate"], "HistoryLine": cs["HistoryLine"]})
            last = (cs.get("ActionDate") or "")[:10]
    for h in hist:
        day, line = (h.get("ActionDate") or "")[:10], text(h.get("HistoryLine"))
        if not line:
            continue
        t = line
        m = PASS.match(line)
        if m:
            house = vote_house.get((day, int(m.group(1))), house)
            t = f"PASSED {HOUSE[house].upper()}"
            out.append((day, house, t, line))
            # After passing its first house a bill goes to the other one; a later passage (concurrence, conference)
            # leaves it with the house that voted.
            if house == origin and not any(x[2] == f"PASSED {HOUSE[other[origin]].upper()}" for x in out):
                house = other[origin]
            continue
        conc = re.match(r"^(House|Senate) (concurred|receded|refuses|adopted|insists|grants|appoints)", line)
        if conc:
            house = "H" if conc.group(1) == "House" else "S"
        r = REFER.match(line)
        if r:
            hit = where_to(r.group(1), comms)
            if re.match(r"Rules\b", r.group(1)):
                t = "REFERRED TO RULES"
            elif hit:
                house = hit[0]
                t = f"REFERRED TO {hit[1].upper()}"
        # Not the end-of-session "Returned to House Rules 3.": bookkeeping for every bill left on the floor calendar.
        elif re.match(r"^Passed to Rules Committee for second reading|^(?:By resolution, )?[Rr]eturned to (?:(?:House|Senate) )?Rules Committee|"
                      r'^(?:House|Senate) Rules "X" file', line):
            t = "REFERRED TO RULES"
        elif REPORT.match(line):
            acr = REPORT.match(line).group(1)
            if acr and acr.upper() in comms:
                house = comms[acr.upper()][0]
            t = "REPORTED"
        elif re.match(r"^(?:Rules Committee relieved of further consideration\.\s+)?Placed on (?:second|third) reading", line, re.I) or \
                re.match(r"^Rules Committee relieved of further consideration", line):
            t = "PLACED ON FLOOR"
        elif FAILED.match(line):
            t = "FAILED"
        elif line.startswith("Delivered to Governor"):
            t = "DELIVERED TO GOVERNOR"
        elif re.match(r"^Governor (?:signed|partially vetoed)|^Chapter \d+, \d+ Laws|^Without Governor's signature|^Became law", line):
            t = "SIGNED"
        elif re.match(r"^Governor vetoed", line):
            t = "VETOED"
        elif re.match(r"^(?:Speaker|President) signed", line):
            t = "ENROLLED"
        out.append((day, house, t, line))
    return out


def both_agreed(origin, rolls):
    """Whether the two houses passed the same text, from the passage roll calls: the second house's passage without
    amendments, the first house's final passage after agreeing to the other's amendments, or a conference report
    both houses passed. "Final Passage as Amended by the House" alone leaves the Senate's agreement to come."""
    passes = sorted((r for r in rolls if re.search(r"final passage", r["motion"], re.I)), key=lambda r: r["date"])
    if len({r["house"] for r in passes}) < 2:
        return False
    last = passes[-1]
    # The first house passing it again on third reading (a bill restarted in the second year) is starting over.
    if last["house"] == origin and re.search(r"reading", last["motion"], re.I):
        return False
    if re.search(r"conference", last["motion"], re.I):
        return len({r["house"] for r in passes if re.search(r"conference", r["motion"], re.I)}) == 2
    if re.search(r"as amended by the", last["motion"], re.I):
        return False
    return True


def stage_of(steps, live, agreed=False):
    texts = [t for _, _, t, _ in steps]
    if "SIGNED" in texts:
        return 5
    if "VETOED" in texts:
        return 6
    if "DELIVERED TO GOVERNOR" in texts:
        return 4
    passed = {h for _, h, t, _ in steps if t.startswith("PASSED")}
    # Passed both houses: the Speaker and President signed it, or the roll calls show both passed the same text.
    if "ENROLLED" in texts or (len(passed) == 2 and agreed):
        return 3
    if passed:
        return 2
    return 1 if where(steps)[1] == "floor" else 0


def where(steps):
    """(house, "committee"/"floor"/"desk", committee) the bill is in now."""
    house, place, comm = None, "desk", None
    for _, h, t, _ in steps:
        house = house or h
        if t.startswith("REFERRED TO"):
            house, place, comm = h, "committee", "Rules" if t == "REFERRED TO RULES" else None
            if comm is None:
                comm = t[len("REFERRED TO "):]
        elif t == "PLACED ON FLOOR":
            house, place, comm = h, "floor", None
        elif t.startswith("PASSED"):
            place, comm = "desk", None
    return house, place, comm


# ---- The same bill in earlier bienniums. Bills come back under new numbers and the data doesn't link them, so: an
# earlier bill with the same short description ("Mail-in ballot watermarks") whose description and title share at least
# 60% of their words (40% with the same prime sponsor). Up to two bienniums back.
_EARLIER = {}
_SKIP = {"the", "and", "act", "relating", "concerning", "that", "with", "for", "under", "section", "this", "providing"}


def _session(session):
    if session not in _EARLIER:
        out = {}
        for f in glob.glob(os.path.join(folder(session), "bills", "*.json")):
            d = json.load(open(f))
            top = (d.get("versions") or [{}])[-1]
            short = text(top.get("ShortDescription")).upper()
            if not short:
                continue
            words = set(re.findall(r"[a-z0-9]{3,}", f"{text(top.get('LongDescription'))} {text(top.get('LegalTitle'))}".lower())) - _SKIP
            prime = next((x.get("Id") for x in d.get("sponsors") or [] if x.get("Type") == "Primary"), top.get("PrimeSponsorID"))
            out[os.path.basename(f)[:-5]] = (short, words, prime)
        _EARLIER[session] = out
    return _EARLIER[session]


def earlier(session, bill):
    out = set()
    me = _session(session).get(bill)
    if not me or len(me[1]) < 5:
        return out
    for y in (session - 2, session - 4):
        if not os.path.isdir(folder(y)):
            continue
        best = None
        for other, (short, words, prime) in _session(y).items():
            if short != me[0]:
                continue
            j = len(me[1] & words) / max(1, len(me[1] | words))
            if j >= 0.6 or (j >= 0.4 and prime and prime == me[2]):
                if not best or j > best[0]:
                    best = (j, other)
        if best:
            out.add((y, best[1]))
    return out


def load_session(session):
    """Read one session's bills and return (records, bill number -> record index, fetched time, delegation)."""
    live = session >= CURRENT
    comms = committees(session)
    # Committee names as written ("REFERRED TO HOUSING" -> "Housing").
    proper = {n.upper(): n for _, n in comms.values()}
    who = members(session)
    files = sorted(glob.glob(os.path.join(folder(session), "bills", "*.json")))
    stamp = max((os.path.getmtime(f) for f in files), default=0)
    fetched = datetime.fromtimestamp(stamp, ZoneInfo(P.TIMEZONE)).strftime("%Y-%m-%d %H:%M")
    seat_of = seats(session)

    def member(mid, name):
        return seat_of.get(mid) or f"{who.get(mid, {}).get('house', '?')}?{name}"

    recs, index = [], {}
    for f in sorted(files, key=lambda f: (os.path.basename(f)[:2], int(re.sub(r"\D", "", os.path.basename(f)) or 0))):
        p = os.path.basename(f)[:-5]
        d = json.load(open(f))
        vers = d.get("versions") or []
        if not vers:
            continue
        top = vers[-1]
        origin, other = p[0], ("S" if p[0] == "H" else "H")
        steps = steps_of(p, d, comms)
        rolls = [{"house": "S" if r.get("Agency") == "Senate" else "H", "date": (r.get("VoteDate") or "")[:10],
                  "motion": r.get("Motion") or ""} for r in d.get("rollCalls", [])]
        stage = stage_of(steps, live, both_agreed(origin, rolls))
        texts = [t for _, _, t, _ in steps]
        passed = {h for _, h, t, _ in steps if t.startswith("PASSED")}
        if stage >= 3:
            passed = {"S", "H"}
        last_pass = max(((dd, h) for dd, h, t, _ in steps if t.startswith("PASSED")), default=None)
        passed_in = HOUSE[last_pass[1]] if stage == 2 and last_pass else None
        now_house, place, committee = where(steps)
        now_house = now_house or origin
        committee = proper.get(committee, committee.title() if committee and committee != "Rules" else committee)
        refs = [(h, proper.get(t[len("REFERRED TO "):], t[len("REFERRED TO "):].title())) for _, h, t, _ in steps
                if t.startswith("REFERRED TO") and t != "REFERRED TO RULES"]
        comm_names = {c for _, c in refs}
        comm_list = sorted({f"{h} · {c}" for h, c in refs})
        title = text(top.get("ShortDescription")) or text(top.get("LongDescription"))
        about = text(top.get("LongDescription"))
        topics = [k for k, (label, cset, _, _) in P.TOPICS.items()
                  if comm_names & cset or (k in P.TOPIC_WORDS and P.TOPIC_WORDS[k].search(title + " " + about))]
        own = [c for h, c in refs if h == origin]
        first_comms = []
        if own:
            i0 = next(i for i, (_, h, t, _) in enumerate(steps) if h == origin and t.startswith("REFERRED TO") and t != "REFERRED TO RULES")
            left = any(h == origin and (t == "REPORTED" or t.startswith("PASSED")) for _, h, t, _ in steps[i0 + 1:])
            first_comms.append((origin, own[0], left))
        raw = [a for _, _, _, a in steps]
        fate = ("passed" if "REPORTED" in texts else
                "held" if own and any(re.search(r'Rules "X" file', a) for a in raw) else "none")
        spons = d.get("sponsors") or []
        prime = next((s for s in spons if s.get("Type") == "Primary"), spons[0] if spons else None)
        names = [(s.get("Agency"), who.get(s.get("Id"), {}).get("name") or text(f"{s.get('FirstName', '')} {s.get('LastName', '')}"))
                 for s in spons]
        sponsor = names[spons.index(prime)][1] if prime else (text(top.get("Sponsor")).strip("()") or "—")
        cos = [n for s, (_, n) in zip(spons, names) if s is not prime]
        for s in spons:
            m = who.get(s.get("Id"))
            if m and m["party"] in ("D", "R"):
                _PARTIES.setdefault(session, {})[("S" if s.get("Agency") == "Senate" else "H", m["name"])] = m["party"]
        if stage == 0 and committee:
            desc = f"In {HOUSE[now_house]} committee"
        elif stage <= 1 and place == "floor":
            desc = f"On the {HOUSE[now_house]} floor"
        elif stage >= 2:
            desc = {2: f"Passed the {passed_in}", 3: "Passed both houses", 4: "On the governor's desk",
                    5: "Signed into law", 6: "Vetoed"}[stage]
        else:
            desc = raw[-1] if raw else "Filed"

        def dates(test, mode="last"):
            ds = sorted({dd for dd, h, t, a in steps if test(h, t, a) and dd})
            return {"first": ds[0], "last": ds[-1], "all": ";".join(ds)}[mode] if ds else ""

        votes = []
        for r in d.get("rollCalls", []):
            # Passage votes only; amendment votes ("12  Braun  Pg 3 Ln 4") aren't the bill's.
            if not re.search(r"final passage", r.get("Motion") or "", re.I):
                continue
            h = "S" if r.get("Agency") == "Senate" else "H"
            vs = (r.get("Votes") or {}).get("Vote") or []
            vs = vs if isinstance(vs, list) else [vs]
            roll = [(v.get("MemberId"), v.get("Name"), v.get("VOte") or v.get("Vote")) for v in vs]
            votes.append([h, "F", None, (r.get("VoteDate") or "")[:10],
                          int((r.get("YeaVotes") or {}).get("Count") or 0), int((r.get("NayVotes") or {}).get("Count") or 0),
                          [[member(mid, nm), VOTE_CODE[v]] for mid, nm, v in roll if v in VOTE_CODE]])
        action_dates = [dd for dd, _, _, _ in steps if dd]
        chap = next((re.match(r"Chapter (\d+)", a).group(1) for a in raw if re.match(r"Chapter \d+, \d+ Laws", a)), None)
        prime_m = who.get(prime.get("Id")) if prime else None
        ver = {"p": p, "sponsor": sponsor, "district": (prime_m or {}).get("district") or 0,
               "cosponsors": cos, "primes": 1, "cosp": len(cos), "statusDesc": desc,
               "committee": committee if place == "committee" and stage in (0, 2) else None,
               "actions": [[dd, t] for dd, _, t, _ in steps]}
        rec = {
            "nums": [p], "base": [p], "prev": earlier(session, p),
            "title": title, "summary": "", "act": "", "lawCode": "", "law": None, "laws": [],
            "comms": comm_list, "topics": topics, "places": [], "narrow": P.narrow_kind(title),
            "commFate": fate, "mainTopic": topics[0] if topics else "", "local": "local" in topics,
            "senDeleg": False, "asmDeleg": False, "budget": bool(re.search(r"\bbudget\b|appropriations", title, re.I)),
            "passedS": "S" in passed, "passedA": "H" in passed, "program": None,
            "stage": stage, "passedIn": passed_in,
            "chapter": int(chap) if chap and stage == 5 else None,
            "veto": None, "memo": "", "vetoMemo": None,
            "simText": f"{title}. {about}. {text(top.get('LegalTitle'))}",
            "comm": committee if stage == 0 and place == "committee" else None,
            "first": min(action_dates, default=f"{session}-01-01"),
            "last": max(action_dates, default=f"{session}-01-01"),
            "cosp": len(cos),
            # Key dates: on the floor, passed the Senate, passed the House, (New York's return to committee: none here),
            # sent to the governor, signed, vetoed.
            "keyDates": [
                dates(lambda h, t, a: h == origin and t in ("REPORTED", "PLACED ON FLOOR"), "first"),
                dates(lambda h, t, a: t == "PASSED SENATE", "all"),
                dates(lambda h, t, a: t == "PASSED HOUSE", "all"),
                "",
                dates(lambda h, t, a: t == "DELIVERED TO GOVERNOR"),
                dates(lambda h, t, a: t == "SIGNED"),
                dates(lambda h, t, a: t == "VETOED"),
            ],
            "votes": votes, "firstComms": first_comms, "vers": [ver],
        }
        index[p] = len(recs)
        recs.append(rec)
    return recs, index, fetched, {"SENATE": [], "ASSEMBLY": []}


def agendas(session):
    """Bills on upcoming committee agendas (states/wa/fetch.py): bill -> [["House Housing", "2026-01-20T08:00:00"], ...]."""
    try:
        return json.load(open(os.path.join(folder(session), "agendas.json")))
    except (OSError, ValueError):
        return {}


_PARTIES = {}


def parties(session, recs):
    return {k: v for k, v in _PARTIES.get(session, {}).items() if v in ("D", "R")}


def seats(session):
    """Member id -> seat id ("S:21", "H:21a"), from data/wa/contacts_<session>.json (states/wa/contacts.py)."""
    path = os.path.join(P.DATA, f"contacts_{session}.json")
    if not os.path.exists(path):
        return {}
    return {p["id"]: sid for sid, p in json.load(open(path))["people"].items() if p.get("id")}
