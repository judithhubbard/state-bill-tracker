"""Massachusetts's bills (downloaded by states/ma/fetch.py from the Legislature's API) in the shape build_data.py reads.
House and Senate bills of each two-year General Court.

A committee often rewrites a bill under a new number ("Accompanied a new draft, see H4321"), sometimes several bills
into one ("Accompanied H4321"): such a bill is an earlier version of the one it led to, followed through any chain, so
the record carries every number and takes its stage from the last. A study order ("Accompanied a study order") ends a
bill in committee. Each branch first passes a bill "to be engrossed"; both then enact it, and the Senate lays it before
the governor. Votes: the tallies are in the history lines ("154 YEAS to 3 NAYS"); the Senate's members' votes come from
the roll calls the lines cite ("see Roll Call #215"); the House's aren't in the API.
"""
import glob, json, os, re
from collections import defaultdict
from datetime import datetime
from zoneinfo import ZoneInfo

from states.ma import profile as P

HOUSE = {"S": "Senate", "H": "House"}
CURRENT = P.session_of(datetime.now(ZoneInfo(P.TIMEZONE)).year)


def folder(session):
    return os.path.join(P.DATA, str(session))


def sessions():
    return sorted(int(os.path.basename(f)) for f in glob.glob(os.path.join(P.DATA, "[0-9]" * 4))
                  if os.path.exists(os.path.join(f, "documents.json")) and glob.glob(os.path.join(f, "bills", "*.json")))


def text(x):
    return re.sub(r"\s+", " ", x or "").strip()


def load(session, name, default):
    try:
        return json.load(open(os.path.join(folder(session), name)))
    except (OSError, ValueError):
        return default


def titled(t):
    t = re.sub(r"^An Act\s+(?:relative to|relating to|concerning|regarding|to|establishing|providing for)?\s*", "", text(t), flags=re.I)
    return t[:1].upper() + t[1:]


_KNOWN = set()  # committee names, from lines that end with one (names have commas: "Steering, Policy and Scheduling")


def clean_comm(c):
    c = re.sub(r"\s+with the amendment pending$|^the\s+", "", c.strip(), flags=re.I)
    return re.sub(r"^(?:House |Senate )?Bills in the Thi?r?d Reading$", "Bills in the Third Reading", c, flags=re.I)


def committee_in(t):
    m = re.search(r"committee on (.+)", t, re.I)
    if not m:
        return None
    rest = m.group(1)
    best = max((k for k in _KNOWN if rest.lower().startswith(k.lower())), key=len, default=None)
    return clean_comm(best or re.split(r",| with the| and referred| -", rest)[0])


def decode(line, branch):
    """One history line -> [(house, shared wording)] (a report that sends a bill on is a report and a referral)."""
    t = text(line)
    h = {"House": "H", "Senate": "S"}.get(branch, "")
    out = []
    if re.search(r"Accompanied a study order", t, re.I):
        return [(h, "SENT TO STUDY")]
    if re.search(r"reported favorably|^Reported\b|Committee recommended (?:bill )?ought to pass", t, re.I):
        out.append((h, "REPORTED"))
    if re.search(r"(?:referred|Discharged) to the committee on", t, re.I):
        last = [m.start() for m in re.finditer(r"committee on", t, re.I)][-1]
        c = committee_in(t[last:])
        # The Committee on Bills in the Third Reading checks a bill's wording just before the floor vote.
        out.append((h, "PLACED ON FLOOR" if c == "Bills in the Third Reading" else f"REFERRED TO {c.upper()}"))
    if out:
        return out
    if re.search(r"passed to be engrossed|conference report accepted", t, re.I) and not re.search(r"reconsider", t, re.I):
        return [(h, f"PASSED {HOUSE.get(h, 'HOUSE').upper()}")]
    if re.search(r"placed in the Orders of the Day|ordered to a third reading", t, re.I):
        return [(h, "PLACED ON FLOOR")]
    if re.search(r"concurred in the (?:Senate|House) amendment", t, re.I):
        return [(h, "CONCURRED")]
    if re.search(r"laid before (?:t?he )?Governor", t, re.I):
        return [(h, "DELIVERED TO GOVERNOR")]
    if re.match(r"Enacted\b", t, re.I):
        return [(h, "ENACTED")]
    if re.match(r"Signed \(in part\)", t, re.I):
        return [("G", "SIGNED"), ("G", "Signed with item vetoes")]
    if re.match(r"Signed by the|Chapter \d+ of the Acts of \d+|Became law without", t, re.I):
        return [("G", "SIGNED")]
    if re.match(r"Governor returned", t, re.I):
        return [("G", "RETURNED")]
    if re.match(r"Vetoed by the Governor", t, re.I):
        return [("G", "VETOED")]
    return [(h or "G", t)]


def agreed(own):
    """Both branches passed it: did they pass the same text? The second branch's passage counts unless it amended
    the bill, when the first has to concur."""
    second = max((i for i, s in enumerate(own) if s[2].startswith("PASSED")))
    amended = re.search(r"amend", own[second][3], re.I) or any(
        re.search(r"^Amend|amendment.*adopted", s[3], re.I) and s[1] == own[second][1] for s in own[second - 3:second] if s[0] == own[second][0])
    return not amended or any(s[2] == "CONCURRED" for s in own[second:])


def tally(t):
    m = re.search(r"(\d+) YEAS to (\d+) NAYS", t, re.I) or re.search(r"Yeas (\d+) to Nays (\d+)", t, re.I)
    return (int(m.group(1)), int(m.group(2))) if m else None


_TITLES = {}


def key(title):
    return " ".join(re.findall(r"[a-z0-9]+", titled(title).lower()))


def _titles(session):
    """Normalized title -> [(bill, sponsor)] for one session's bills (refiled bills keep their titles)."""
    if session not in _TITLES:
        out = defaultdict(list)
        for d in load(session, "documents.json", []):
            if re.match(r"(?:An Act|Resolve)\b", text(d.get("Title")), re.I):
                out[key(d["Title"])].append((d["BillNumber"], text((d.get("PrimarySponsor") or {}).get("Name"))))
        _TITLES[session] = out
    return _TITLES[session]


def earlier(session, title, sponsor):
    """The same bill in the General Court before: the same title, and the same lead sponsor, or a title of six words or
    more that only one bill has in each session."""
    k = key(title)
    if session - 2 not in sessions() or len(k.split()) < 3:
        return set()
    mine, theirs = _titles(session).get(k, []), _titles(session - 2).get(k, [])
    same = [b for b, who in theirs if who and who == sponsor]
    if same:
        return {(session - 2, same[0])}
    if len(theirs) == 1 and len(mine) == 1 and len(k.split()) >= 6:
        return {(session - 2, theirs[0][0])}
    return set()


def load_session(session):
    """Read one session's bills and return (records, bill number -> record index, fetched time, delegation)."""
    # Bills and resolves (both become law); not orders, study orders, reports or proposed constitutional amendments.
    docs = {d["BillNumber"]: d for d in load(session, "documents.json", [])
            if re.match(r"(?:An Act|Resolve)\b", text(d.get("Title")), re.I) and re.match(r"[HS]\d+$", d.get("BillNumber") or "")}
    hist = {}
    for f in glob.glob(os.path.join(folder(session), "bills", "*.json")):
        hist[os.path.basename(f)[:-5]] = sorted(json.load(open(f)), key=lambda a: (a.get("Date") or "")[:10])
    for acts in hist.values():
        for a in acts:
            m = re.match(r"Referred to the committee on (.+?)(?:, acting concurrently)?$", text(a.get("Action")), re.I)
            if m:
                _KNOWN.add(clean_comm(m.group(1)))
    # The session laws: every act and resolve with the bill it came from (some histories stop before the signing).
    court = P.court_of(session)
    laws = {}
    for f in glob.glob(os.path.join(P.DATA, "*", "laws_*.json")):
        for x in json.load(open(f)):
            o = x.get("OriginBill")
            if isinstance(o, dict) and o.get("GeneralCourtNumber") == court and x.get("ApprovedDate"):
                when = datetime.strptime(x["ApprovedDate"], "%b %d %Y").strftime("%Y-%m-%d")
                laws[o["BillNumber"]] = (int(x["ChapterNumber"]), when)
    rollcalls = load(session, "senate_rollcalls.json", {})
    seat_of = seats(session)
    stamp = max((os.path.getmtime(f) for f in glob.glob(os.path.join(folder(session), "bills", "*.json"))), default=0)
    fetched = datetime.fromtimestamp(stamp, ZoneInfo(P.TIMEZONE)).strftime("%Y-%m-%d %H:%M")

    # Which bill each one led to: "Accompanied a new draft, see H4321" or "Accompanied H4321" (not study orders).
    # A conference committee's report is a new bill ("Reported, in part, by H4040"), which takes over. The governor's
    # amendments to a law's sections come back as bills of their own ("see H4051 for section 15"): parts of the law.
    led_to, parts = {}, {}
    for b, acts in hist.items():
        for a in acts:
            t = text(a.get("Action"))
            m = (re.match(r"Accompanied (?:a new draft, see |the new draft, see )?([HS]\d+)\b", t)
                 or re.match(r"Reported,? (?:in part,? )?by ([HS]\d+)\b", t))
            if m and "study order" not in t and m.group(1) in docs and m.group(1) != b:
                led_to[b] = m.group(1)
            m = re.search(r"returned with recommendations? of amendments?, see ([HS]\d+)", t)
            if m and m.group(1) in docs:
                parts[m.group(1)] = b
    def final(b, seen=()):
        return final(led_to[b], seen + (b,)) if b in led_to and led_to[b] not in seen else b
    group = defaultdict(list)
    for b in docs:
        if b in hist and b not in parts:
            group[final(b)].append(b)
    for b, law in parts.items():
        if final(law) in group and b not in group[final(law)]:
            group[final(law)].append(b)

    member_names = {m["MemberCode"]: m["Name"] for m in load(session, "member_details.json", [])}

    def member(code):
        return seat_of.get(code) or f"S?{member_names.get(code, code)}"

    recs, index = [], {}
    for p in sorted(group, key=lambda b: (b[0], int(b[1:]))):
        nums = [p] + sorted((b for b in group[p] if b != p), key=lambda b: (b[0], int(b[1:])))
        d = docs[p]
        origin = p[0]
        steps = []
        for b in reversed(nums):  # the earlier drafts' steps first, then the bill's own
            for a in hist.get(b, []):
                for h, t in decode(a.get("Action"), a.get("Branch")):
                    steps.append(((a.get("Date") or "")[:10], h, t, text(a.get("Action")), b))
        steps.sort(key=lambda s: s[0])
        own = [s for s in steps if s[4] == p]
        texts = [s[2] for s in own]
        passed = {s[1] for s in own if s[2].startswith("PASSED")}
        last_sent = max((i for i, t in enumerate(texts) if t == "DELIVERED TO GOVERNOR"), default=-1)
        law = next((laws[b] for b in nums if b in laws), None)
        if "SIGNED" in texts or law:
            stage = 5
        elif "VETOED" in texts:
            stage = 6
        elif last_sent >= 0 and "RETURNED" not in texts[last_sent:]:
            stage = 4
        elif "ENACTED" in texts or last_sent >= 0 or (len(passed) == 2 and agreed(own)):
            stage = 3
        elif passed:
            stage = 2
        else:
            stage = None
        if stage is not None and stage >= 3:
            passed = {"S", "H"}
        where_h, place, committee = origin, "desk", None
        for dd, h, t, a, _ in own:
            if t.startswith("REFERRED TO"):
                where_h, place, committee = (h or where_h), "committee", t[len("REFERRED TO "):]
            elif t in ("PLACED ON FLOOR",):
                where_h, place, committee = (h or where_h), "floor", None
            elif t.startswith("PASSED"):
                place, committee = "desk", None
                where_h = "S" if h == "H" else "H"
            elif t == "SENT TO STUDY":
                place = "committee"
        if stage is None:
            stage = 1 if place == "floor" else 0
        refs = [(s[1] or origin, s[2][len("REFERRED TO "):]) for s in steps if s[2].startswith("REFERRED TO")]
        proper = lambda c: re.sub(r"\b(And|Of|The|On|For|To|In)\b", lambda m: m.group(1).lower(), c.title())
        committee = proper(committee) if committee else None
        comm_list = sorted({f"{h} · {proper(c)}" for h, c in refs})
        title = titled(d.get("Title"))
        topics = [P.COMMITTEE_TOPICS[w] for w in P.COMMITTEE_TOPICS if any(w.lower() in c.lower() for _, c in refs)]
        topics = list(dict.fromkeys(topics + [k for k, v in P.TOPICS.items() if k in P.TOPIC_WORDS and P.TOPIC_WORDS[k].search(title)]))
        first = next((i for i, s in enumerate(steps) if s[2].startswith("REFERRED TO")), None)
        first_comms = []
        if first is not None:
            later = [s[2] for s in steps[first + 1:]]
            left = any(t in ("REPORTED", "PLACED ON FLOOR") or t.startswith("PASSED") for t in later) or len(nums) > 1
            first_comms.append((steps[first][1] or origin, proper(steps[first][2][len("REFERRED TO "):]), left))
        fate = ("held" if any(s[2] == "SENT TO STUDY" for s in steps) and stage <= 1 and len(nums) == 1 else
                "passed" if first_comms and first_comms[0][2] else "none")
        sponsor = text((d.get("PrimarySponsor") or {}).get("Name")) or "—"
        cos = [text(c.get("Name")) for c in d.get("Cosponsors") or [] if text(c.get("Name")) != sponsor]
        if stage == 0 and committee:
            desc = f"In {HOUSE[where_h]} committee"
        elif stage <= 1 and place == "floor":
            desc = f"On the {HOUSE[where_h]} floor"
        elif stage >= 2:
            desc = {2: f"Passed the {HOUSE[max(s for s in passed)] if passed else 'House'}", 3: "Passed both houses",
                    4: "On the governor's desk", 5: "Signed into law", 6: "Vetoed"}[stage]
        else:
            desc = own[-1][3] if own else "Filed"
        last_pass = max(((s[0], s[1]) for s in own if s[2].startswith("PASSED")), default=None)
        passed_in = HOUSE.get(last_pass[1]) if stage == 2 and last_pass else None

        def dates(test, mode="last"):
            ds = sorted({s[0] for s in own if test(s[1], s[2], s[3]) and s[0]})
            return {"first": ds[0], "last": ds[-1], "all": ";".join(ds)}[mode] if ds else ""

        votes = []
        for dd, h, t, a, b in own:
            v = tally(a)
            if not v or h not in HOUSE or re.match(r"Item", a) or not re.search(r"engrossed|Enacted|concurred|accepted|passed over veto|adopted", a, re.I):
                continue
            rc = re.search(r"Roll Call #(\d+)", a)
            names = []
            if h == "S" and rc and rc.group(1) in rollcalls:
                r = rollcalls[rc.group(1)]
                names = [[member(c), "N"] for c in r.get("Nays") or []] + [[member(c), "A"] for c in r.get("Absent") or []]
            votes.append([h, "F", None, dd, v[0], v[1], names])
        chap = law[0] if law else next((re.search(r"Chapter (\d+)", s[3]).group(1) for s in own if s[2] == "SIGNED" and re.search(r"Chapter (\d+)", s[3])), None)
        action_dates = [s[0] for s in steps if s[0]]
        vers = [{"p": b, "sponsor": text((docs[b].get("PrimarySponsor") or {}).get("Name")) or "—", "district": 0,
                 "cosponsors": cos if b == p else [], "primes": 1, "cosp": len(cos) if b == p else 0,
                 "statusDesc": desc if b == p else f"Rewritten as {p}",
                 "committee": committee if b == p and place == "committee" and stage in (0, 2) else None,
                 "actions": [[s[0], s[2]] for s in steps if s[4] == b]} for b in nums]
        rec = {
            "nums": nums, "base": nums, "prev": earlier(session, title, sponsor),
            "title": title, "summary": "", "act": "", "lawCode": "", "law": None, "laws": [],
            "comms": comm_list, "topics": topics, "places": [], "narrow": P.narrow_kind(title),
            "commFate": fate, "mainTopic": topics[0] if topics else "", "local": "local" in topics,
            "senDeleg": False, "asmDeleg": False, "budget": bool(re.search(r"\bappropriations?\b|\bbudget\b", title, re.I)),
            "passedS": "S" in passed, "passedA": "H" in passed, "program": None,
            "stage": stage, "passedIn": passed_in, "chapter": int(chap) if chap and stage == 5 else None,
            "veto": None, "memo": "", "vetoMemo": None,
            "simText": title,
            "comm": committee if stage == 0 and place == "committee" else None,
            "first": min(action_dates, default=f"{session}-01-01"),
            "last": max(action_dates, default=f"{session}-01-01"),
            "cosp": len(cos),
            "keyDates": [
                dates(lambda h, t, a: t in ("REPORTED", "PLACED ON FLOOR"), "first"),
                dates(lambda h, t, a: t == "PASSED SENATE", "all"),
                dates(lambda h, t, a: t == "PASSED HOUSE", "all"),
                "",
                dates(lambda h, t, a: t == "DELIVERED TO GOVERNOR"),
                law[1] if law else dates(lambda h, t, a: t == "SIGNED"),
                dates(lambda h, t, a: t == "VETOED"),
            ],
            "votes": votes, "firstComms": first_comms, "vers": vers,
        }
        for b in nums:
            index[b] = len(recs)
        recs.append(rec)
    return recs, index, fetched, {"SENATE": [], "ASSEMBLY": []}


def agendas(session):
    return {}


_PARTIES = {}


def parties(session, recs):
    """Party for each sponsor, from the members' records (states/ma/contacts.py)."""
    out = {}
    for m in load(session, "member_details.json", []):
        h = "S" if m.get("Branch") == "Senate" else "H"
        if (m.get("Party") or "")[:1] in ("D", "R"):
            out[(h, m["Name"])] = m["Party"][:1]
    return out


def seats(session):
    """Member code -> seat id ("S:7", "H:24"), from data/ma/contacts_<session>.json (states/ma/contacts.py)."""
    path = os.path.join(P.DATA, f"contacts_{session}.json")
    if not os.path.exists(path):
        return {}
    return {p["id"]: sid for sid, p in json.load(open(path))["people"].items() if p.get("id")}
