"""New Jersey: reads the Legislature's bill database (data/nj/DB<session>_TEXT.zip) and its floor and
committee votes (data/nj/A<year>.zip, CA<session>-<session+1>.zip, ...), from states/nj/fetch.py, and
turns them into the bill records build_data.py works with.

Every state's convert.py has the same two functions: sessions() and load_session(session). This one
also has parties(), the sponsors' parties from each session's roster.

New Jersey writes its actions in codes ("INT 1RA REF ATR", "REP/ACA 2RA", "PA PBH"). They are turned
into the same wording New York's data uses ("INTRODUCED", "REFERRED TO ...", "PASSED ASSEMBLY"), so
the page's plain-language rules work for both. The codes are explained at njleg.state.nj.us/help.
"""
import csv, glob, io, os, re, zipfile
from collections import defaultdict

from datetime import datetime
from zoneinfo import ZoneInfo

from stages import rank
from . import profile as P

CURRENT = P.session_of(datetime.now(ZoneInfo(P.TIMEZONE)).year)

HOUSE = {"A": "Assembly", "S": "Senate"}


def sessions():
    """The sessions downloaded with a complete database (2022-23's text download has no MAINBILL)."""
    out = []
    for f in glob.glob(os.path.join(P.DATA, "DB*_TEXT.zip")):
        if "MAINBILL.TXT" in zipfile.ZipFile(f).namelist():
            out.append(int(re.search(r"DB(\d{4})", f).group(1)))
    return sorted(out)


def _rows(z, name):
    """A CSV table from a zip, with every value trimmed."""
    with z.open(name) as f:
        for r in csv.DictReader(io.TextIOWrapper(f, encoding="cp1252", errors="replace")):
            yield {k: (v or "").strip() for k, v in r.items() if k}


def iso(d):
    """"1/13/2026 0:00:00" or "05/18/2026" -> "2026-01-13"."""
    m = re.match(r"(\d+)/(\d+)/(\d{4})", d or "")
    return f"{m.group(3)}-{int(m.group(1)):02d}-{int(m.group(2)):02d}" if m else ""


def bill_refs(text):
    """Bill numbers in a note or list ("S3022 (1R)", "A274 S883") -> ["S3022", "A274", "S883"]."""
    return re.findall(r"\b[AS]\d+\b", text or "")


def person(name):
    """"Dunn, Aura K." -> "Aura K. Dunn"; "Testa, Michael L., Jr." -> "Michael L. Testa Jr."."""
    parts = [p.strip() for p in name.split(",")]
    return " ".join([parts[1], parts[0]] + parts[2:]) if len(parts) > 1 else name


def name_key(last, first):
    return (re.sub(r"[^a-z]", "", last.lower()), re.sub(r"[^a-z]", "", (first.split() or [""])[0].lower()))


# ---- Actions: the codes, in New York's wording.
FLOOR = re.compile(r"^2R[AS]$")


def decode(code, comment, comms, passed):
    """One coded action -> the steps it records, each worded as New York's data words it. `passed`
    is the set of houses this bill has passed so far (a second pass is "REPASSED")."""
    if "COPY ON DESK" in code:
        return ["OTHER HOUSE'S COPY ON DESK"]
    if code == "WITHDRAWN APP":
        return ["WITHDRAWN: ALREADY LAW"]
    cname = lambda c: comms.get(c, ("", c))[1].upper()
    words, out, i = code.split(), [], 0
    while i < len(words):
        w, nxt = words[i], words[i + 1] if i + 1 < len(words) else ""
        if w == "INT":
            out.append("INTRODUCED")
        elif re.fullmatch(r"1R[AS]|SWR|AWR", w):
            pass  # first reading comes with introduction; "without reference" with the second reading
        elif w in ("REF", "TRANS", "RCM") and nxt:
            out.append({"REF": "REFERRED TO ", "TRANS": "COMMITTED TO ", "RCM": "RECOMMITTED TO "}[w] + cname(nxt))
            i += 1
        elif w == "NOT" and nxt.startswith("REP"):
            c = words[i + 2] if i + 2 < len(words) else ""
            out.append("NOT REPORTED" + (f" BY {cname(c)}" if c else ""))
            i += 2 if c else 1
        elif w.startswith("REP"):
            how = {"/ACA": " WITH COMMITTEE AMENDMENTS", "/SCA": " WITH COMMITTEE AMENDMENTS",
                   "/ACS": " AS A COMMITTEE SUBSTITUTE", "/SCS": " AS A COMMITTEE SUBSTITUTE"}.get(w[3:], "")
            if nxt == "REF" and i + 2 < len(words) and not how:
                out.append(f"REPORTED REFERRED TO {cname(words[i + 2])}")
                i += 2
            else:
                out.append("REPORTED" + how)
        elif FLOOR.match(w):
            out.append("ADVANCED TO THIRD READING")
        elif re.fullmatch(r"2R[AS]C", w):
            out.append("ON THE FLOOR TO AGREE TO THE OTHER HOUSE'S AMENDMENTS")
        elif re.fullmatch(r"2R[AS]G", w):
            out.append("ON THE FLOOR WITH THE GOVERNOR'S CHANGES")
        elif w in ("R/S", "R/A"):
            out.append(f"DELIVERED TO {HOUSE[w[2]].upper()}")
        elif w in ("PA", "PS"):
            h = w[1]
            out.append(("REPASSED " if h in passed else "PASSED ") + HOUSE[h].upper())
            passed.add(h)
        elif w == "PBH":
            out.append("PASSED BOTH HOUSES")
        elif w == "FILE":
            out.append("FILED")
        elif w == "SUB" and nxt in ("FOR", "BY"):
            other = (bill_refs(comment) or ["another bill"])[0]
            out.append(f"SUBSTITUTED {nxt} {other}")
            i += 1
        elif w == "APP":
            m = re.search(r"c\.\s*(\d+)", comment or "")
            out.append(f"SIGNED CHAP.{m.group(1)}" if m else "SIGNED")
        elif w == "W/LIV":
            out.append("SOME SPENDING ITEMS VETOED")
        elif w == "AV":
            out.append("VETOED")
        elif w == "PV":
            out.append("POCKET VETOED")
        elif w == "CV":
            out.append("CONDITIONALLY VETOED")
        elif w in ("SA", "AA"):
            out.append(f"AMENDED ON THE {HOUSE[w[0]].upper()} FLOOR")
        elif w in ("SS", "AS", "FSS"):
            out.append("FLOOR SUBSTITUTE ADOPTED")
        elif w == "MOTION":
            out.append("MOTION" + (f": {comment.upper()}" if comment else ""))
        elif w == "W":
            out.append("WITHDRAWN FROM CONSIDERATION")
        elif w == "COMB/W":
            out.append(f"COMBINED WITH {(bill_refs(comment) or ['ANOTHER BILL'])[0]} AND WITHDRAWN")
        elif w in ("RCON/V", "RSND/V"):
            out.append("VOTE RECONSIDERED" if w == "RCON/V" else "VOTE RESCINDED")
        elif w == "CONCUR":
            out.append("AGREED TO THE OTHER HOUSE'S AMENDMENTS")
            i += nxt in ("AA", "SA")
        else:
            out.append(w)
        i += 1
    return out


def version_stage(steps, live):
    """How far one bill got, 0-6, from its coded steps in order: (house, token) pairs. A conditional
    veto sends the bill back to both houses; it is with the governor again once they re-pass it.
    Until then it counts as passed both houses in a session still under way (`live`), and as vetoed
    once the session is over, since it died with the veto."""
    floor, passed, stage = set(), set(), 0
    for h, w in steps:
        if FLOOR.match(w) or re.fullmatch(r"2R[AS][CG]", w):
            floor.add(h)
        elif w in ("PA", "PS"):
            passed.add(w[1])
        elif w == "PBH":
            stage = 4
        elif w == "APP":
            stage = 5
        elif w in ("AV", "PV"):
            stage = 6
        elif w == "CV":
            stage = 3 if live else 6
    if stage:
        return stage
    return 3 if len(passed) == 2 else 2 if passed else 1 if floor else 0


def status_text(t):
    """A bill's last step as its status: "SUBSTITUTED BY S4307" -> "Substituted by S4307"."""
    if t.startswith("SIGNED"):
        return "Signed into law"
    t = t[:1] + t[1:].lower()
    return re.sub(r"\b([as])(\d+)\b", lambda m: m.group(1).upper() + m.group(2), re.sub(r"\b(senate|assembly)\b", lambda m: m.group(1).capitalize(), t))


# ---- Votes
FLOOR_VOTE = re.compile(r"PASSAGE|CONCUR|OVERRIDE|RECOMMENDATION")
VOTE_CODE = {"N": "N", "No": "N", "A": "B", "Abstain": "B", "": "A"}


def read_votes(session, comms):
    """Every bill's floor and committee roll calls: bill -> [[house, "F"/"C", committee, date, yes, no,
    [[member, code], ...]], ...], listing only members who didn't vote yes. Members are "A?Name"."""
    calls = defaultdict(list)  # (bill, house, kind, committee, date, motion) -> [[name, vote], ...]
    for house in "AS":
        for year in (session, session + 1):
            path = os.path.join(P.DATA, f"{house}{year}.zip")
            if not os.path.exists(path):
                continue
            z = zipfile.ZipFile(path)
            for name in z.namelist():
                for r in _rows(z, name):
                    if FLOOR_VOTE.search(r.get("Action", "")):
                        calls[(r["Bill"], house, "F", None, iso(r["Session_Date"]), r["Action"])].append(
                            [r["Full_Name"], r["Legislator_Vote"]])
        path = os.path.join(P.DATA, f"C{house}{session}-{session + 1}.zip")
        if os.path.exists(path):
            z = zipfile.ZipFile(path)
            for name in z.namelist():
                for r in _rows(z, name):
                    code = r["Committee_House"]
                    calls[(r["Bill_Type"] + r["Bill_Number"], comms.get(code, (code[:1], ""))[0] or house, "C",
                           comms.get(code, ("", code))[1], iso(r["Agenda_Date"]), r["Agenda_Date"] + r["Agenda_Sequence"])].append(
                        [r["Name"], r["LegislatorVote"]])
    out = defaultdict(list)
    for (bill, house, kind, comm, date, _), votes in calls.items():
        # The same motion twice in a day (a vote taken again) lists each member twice: split them.
        rolls = [[]]
        for name, vote in votes:
            if any(n == name for n, _ in rolls[-1]):
                rolls.append([])
            rolls[-1].append((name, vote))
        for roll in rolls:
            yes = sum(v in ("Y", "Yes") for _, v in roll)
            no = sum(v in ("N", "No") for _, v in roll)
            out[bill].append([house, kind, comm, date, yes, no,
                              [[f"{house}?{person(n)}", VOTE_CODE.get(v, v)] for n, v in roll if v not in ("Y", "Yes")]])
    return out


# ---- Committee agendas
def agendas(session):
    """Bills on committee agendas: bill -> [["Assembly Health", "2026-11-05T10:00:00"], ...], as New York's
    agendas file has them. Floor sessions and meetings that were canceled or aren't meeting are left out."""
    z = zipfile.ZipFile(os.path.join(P.DATA, f"DB{session}_TEXT.zip"))
    comms = {r["Code"]: (r["House"], r["Description"]) for r in _rows(z, "COMMITTEE.TXT")}
    off = {(r["CommHouse"], r["Date"], r["Time"]) for r in _rows(z, "AGENDAS.TXT") if r["Status"] != "Scheduled"}
    out = defaultdict(list)
    for r in _rows(z, "BAGENDA.TXT"):
        house, name = comms.get(r["CommHouse"], ("", ""))
        if r["Type"] == "Session" or house not in HOUSE or (r["CommHouse"], r["Date"], r["Time"]) in off:
            continue
        m = re.match(r"(\d+):(\d+) ([AP])M", r["Time"])
        hour = (int(m.group(1)) % 12 + (12 if m.group(3) == "P" else 0)) if m else 0
        entry = [f"{HOUSE[house]} {name}", f"{iso(r['Date'])}T{hour:02d}:{int(m.group(2)) if m else 0:02d}:00"]
        bill = r["BillType"] + r["BillNumber"]
        if entry not in out[bill]:
            out[bill].append(entry)
    return dict(out)


# ---- Sponsors' parties, from each session's roster (filled by load_session).
_PARTIES = {}


def parties(session, recs):
    """Party ("D" or "R") for each sponsor as the records name them, keyed by (house, name)."""
    return _PARTIES.get(session, {})


def load_session(session):
    """Read one session's bills and return (records, bill number -> record index, fetched time,
    delegation sponsor names)."""
    path = os.path.join(P.DATA, f"DB{session}_TEXT.zip")
    z = zipfile.ZipFile(path)
    fetched = "{}-{:02d}-{:02d} {:02d}:{:02d}".format(*max(i.date_time for i in z.infolist())[:5])
    comms = {r["Code"]: (r["House"], r["Description"]) for r in _rows(z, "COMMITTEE.TXT")}
    subj_names = {r["SubjAbbrev"]: r["Description"] for r in _rows(z, "SUBJHEADINGS.TXT")}

    roster = {}
    for r in _rows(z, "ROSTER.TXT"):
        roster[(r["House"],) + name_key(r["LastName"], r["Firstname"])] = (int(r["District"] or 0), r["Party"])

    def seat(house, sponsor):
        last, _, first = sponsor.partition(",")
        return roster.get((house,) + name_key(last, first.strip()), (0, ""))

    main = {}
    for r in _rows(z, "MAINBILL.TXT"):
        if r["BillType"] in ("A", "S") and r["CurrentStatus"] != "WAPP":
            main[r["BillType"] + r["BillNumber"]] = r
    hist = defaultdict(list)
    for r in _rows(z, "BILLHIST.TXT"):
        hist[r["BillType"] + r["BillNumber"]].append(r)
    for h in hist.values():
        h.sort(key=lambda r: int(r["Sequence"] or 0))
    spons = defaultdict(list)
    for r in _rows(z, "BILLSPON.TXT"):
        if r["Status"] != "W":
            spons[r["BillType"] + r["BillNumber"]].append(r)
    for s in spons.values():
        s.sort(key=lambda r: int(r["Sequence"] or 0))
    subjects = defaultdict(list)
    for r in _rows(z, "BILLSUBJ.TXT"):
        subjects[r["BillType"] + r["BillNumber"]].append(subj_names.get(r["SubjectKey"], r["SubjectKey"]))
    votes = read_votes(session, comms)

    # Union-find over identical bills and substitutions.
    parent = {p: p for p in main}

    def find(p):
        while parent[p] != p:
            parent[p] = parent[parent[p]]
            p = parent[p]
        return p

    def union(a, b):
        if a in parent and b in parent:
            parent[find(a)] = find(b)

    for p, m in main.items():
        for q in bill_refs(m["IdenticalBillNumber"]):
            union(p, q)
        for h in hist[p]:
            if h["Action"].startswith(("SUB FOR", "SUB BY")):
                for q in bill_refs(h["Comment"]):
                    union(p, q)
    groups = defaultdict(list)
    for p in main:
        groups[find(p)].append(p)

    # Each bill's history in New York's wording, and the coded steps behind it.
    vers = {}
    for p, m in main.items():
        passed, actions, steps = set(), [], []
        for h in hist[p]:
            d = iso(h["DateAction"])
            for w in h["Action"].split():
                steps.append((h["House"] if h["House"] in HOUSE else p[0], w, d))
            for text in decode(h["Action"], h["Comment"], comms, passed):
                actions.append([d, text])
        sp = spons[p]
        primes = [r["Sponsor"] for r in sp if r["Type"] == "P"]
        cos = [person(r["Sponsor"]) for r in sp if r["Type"] != "P"]
        status = m["CurrentStatus"]
        in_comm = status in comms and comms[status][0] in HOUSE
        if in_comm:
            desc = f"In {HOUSE[comms[status][0]]} committee"
        elif re.fullmatch(r"2R[AS]G", status):
            desc = f"Back on the {HOUSE[status[2]]} floor with the governor's changes"
        elif re.fullmatch(r"2R[AS]C?", status):
            desc = f"On the {HOUSE[status[2]]} floor"
        else:
            desc = status_text(next((t for _, t in reversed(actions)), "INTRODUCED"))
        vers[p] = {
            "p": p,
            "sponsor": person(primes[0]) if primes else "",
            "district": seat(p[0], primes[0])[0] if primes else 0,
            # Other prime sponsors come first, then co-sponsors.
            "cosponsors": [person(n) for n in primes[1:]] + cos,
            "cosp": max(0, len(primes) - 1) + len(cos),
            "statusDesc": desc,
            "committee": comms[status][1] if in_comm else None,
            "actions": actions,
            "_steps": steps,
            "_stage": version_stage([(h, w) for h, w, _ in steps], session >= CURRENT),
            "_sub": status == "SUB",
        }

    _PARTIES[session] = {(p[0], person(r["Sponsor"])): seat(p[0], r["Sponsor"])[1]
                         for p in main for r in spons[p] if seat(p[0], r["Sponsor"])[1] in ("D", "R")}

    recs, index = [], {}
    for members in groups.values():
        live = sorted(members, key=lambda p: (-rank(vers[p]["_stage"]), vers[p]["_sub"],
                                              -len(vers[p]["actions"]), p))
        lead, lm = vers[live[0]], main[live[0]]
        steps = [(h, w, d) for p in live for h, w, d in vers[p]["_steps"]]
        stage = max((vers[p]["_stage"] for p in live), key=rank)
        passed = {w[1] for _, w, _ in steps if w in ("PA", "PS")}
        passed_in = None
        if stage == 2:
            last_pass = max((d, w) for _, w, d in steps if w in ("PA", "PS"))
            passed_in = HOUSE[last_pass[1][1]]

        def dates(test, mode="last"):
            ds = sorted({d for h, w, d in steps if test(h, w) and d})
            return {"first": ds[0], "last": ds[-1], "all": ";".join(ds)}[mode] if ds else ""

        chapter = next((int(main[p]["ChapterLaw"]) for p in live if main[p]["ChapterLaw"].isdigit()), None)
        comm_codes = [w2 for p in live for h in hist[p] for w1, w2 in zip(h["Action"].split(), h["Action"].split()[1:])
                      if w1 in ("REF", "TRANS", "RCM") and w2 in comms]
        comm_list = sorted({f"{comms[c][0]} · {comms[c][1]}" for c in comm_codes if comms[c][0] in HOUSE})
        comm_names = {comms[c][1] for c in comm_codes}
        subj = sorted({s for p in live for s in subjects[p]})
        title = re.sub(r"\*+$", "", lm["Synopsis"]).strip()

        topics = []
        for k, (label, cset, sre, _) in P.TOPICS.items():
            if comm_names & cset or any(sre.search(s) for s in subj) or (k in P.TOPIC_WORDS and P.TOPIC_WORDS[k].search(title)):
                topics.append(k)

        # Each version's first committee in its own house, and whether the bill got out of it.
        first_comms = []
        for p in live:
            own = [(i, w2) for i, h in enumerate(hist[p]) if h["House"] == p[0]
                   for w1, w2 in zip(h["Action"].split(), h["Action"].split()[1:]) if w1 == "REF" and w2 in comms]
            if own:
                i0, code = own[0]
                left = any(h["House"] == p[0] and re.search(r"\bREP|\b2R[AS]\b", h["Action"]) and not h["Action"].startswith("NOT")
                           for h in hist[p][i0 + 1:])
                first_comms.append((p[0], comms[code][1], left))
        main_topic = next((t for _, name, _ in first_comms for t in topics if name in P.TOPICS[t][1]), topics[0] if topics else "")

        acts = [a for p in live for a in vers[p]["actions"]]
        fate = ("passed" if any(t.startswith("REPORTED") for _, t in acts) else
                "defeated" if any(t.startswith("NOT REPORTED") for _, t in acts) else
                "amended" if any(t.startswith("AMENDED") for _, t in acts) else "none")
        # A committee often votes on both identical bills at one meeting: keep one of each.
        all_votes, seen = [], set()
        for v in sorted((v for p in live for v in votes.get(p, [])), key=lambda v: v[3]):
            key = tuple(v[:6])
            if key not in seen:
                seen.add(key)
                all_votes.append(v)
        intro = min((iso(main[p]["IntroDate"]) for p in live if main[p]["IntroDate"]), default="")
        action_dates = [d for d, _ in acts if d]

        rec = {
            "nums": live,
            "base": members,
            "prev": {(session - 2, q) for p in members for q in bill_refs(main[p]["LastSessionFullBillNumber"])},
            "title": title,
            "summary": "",
            "act": "",
            "lawCode": "",
            "law": None,
            "laws": [],
            "comms": comm_list,
            "topics": topics,
            "places": [],
            "narrow": P.narrow_kind(title),
            "commFate": fate,
            "mainTopic": main_topic,
            "local": "local" in topics,
            "senDeleg": False,
            "asmDeleg": False,
            "budget": False,
            "passedS": "S" in passed,
            "passedA": "A" in passed,
            "program": None,
            "stage": stage,
            "passedIn": passed_in,
            "chapter": chapter if stage == 5 else None,
            "veto": None,
            "memo": "",
            "comm": lead["committee"] if stage == 0 else None,
            # A few bills carry no dates at all; they count from the session's start.
            "first": min(filter(None, [intro] + action_dates), default=f"{session}-01-01"),
            "last": max(action_dates, default=intro or f"{session}-01-01"),
            "cosp": max(vers[p]["cosp"] for p in live),
            # Key dates: on the floor, passed the Senate, passed the Assembly, died (not recorded),
            # sent to the governor (the day it passed both houses), signed, vetoed (not conditionally).
            "keyDates": [
                dates(lambda h, w: bool(FLOOR.match(w)), "first"),
                dates(lambda h, w: w == "PS", "all"),
                dates(lambda h, w: w == "PA", "all"),
                "",
                dates(lambda h, w: w == "PBH"),
                dates(lambda h, w: w == "APP"),
                # A conditional veto isn't the end of a bill, so it shows only in the list of actions.
                dates(lambda h, w: w in ("AV", "PV")),
            ],
            "votes": all_votes,
            "firstComms": first_comms,
            "vers": [{k: v for k, v in vers[p].items() if not k.startswith("_")} for p in live],
        }
        for p in members:
            index[p] = len(recs)
        recs.append(rec)
    return recs, index, fetched, {"SENATE": [], "ASSEMBLY": []}
