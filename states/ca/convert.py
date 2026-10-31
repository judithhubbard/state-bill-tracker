"""California: reads the Legislature's database tables for each session (data/ca/<session>/, from
states/ca/fetch.py) and turns them into the bill records build_data.py works with.

Every state's convert.py has the same functions: sessions(), load_session(session), agendas(session) and
parties(session, recs).

California's history lines are plain English, with each committee abbreviated ("Referred to Com. on  W. P., & W.");
each line also says where the bill went (house, "Committee"/"Floor"/"Desk", and the committee's code). The steps
the site's rules depend on are put in the wording New York's data uses; the rest are kept as written, with the
committees' full names. A bill keeps its number through both houses (AB 1 goes to the Senate as AB 1). Only
regular-session Assembly and Senate bills and constitutional amendments (ACA, SCA) are shown (not other resolutions,
or special sessions' bills). A constitutional amendment passes each house by two-thirds ("Read third time. Adopted.")
and is filed with the Secretary of State ("Res. Chapter 176"), who puts it on the ballot; it never goes to the governor.
"""
import json, math, os, re
from collections import defaultdict
from datetime import datetime
from zoneinfo import ZoneInfo

from . import profile as P

CURRENT = P.session_of(datetime.now(ZoneInfo(P.TIMEZONE)).year)
HOUSE = {"A": "Assembly", "S": "Senate"}
LETTER = {"Assembly": "A", "Senate": "S"}
# The measures shown: bills, and constitutional amendments (which go to the voters, not the governor).
KINDS = ("AB", "SB", "ACA", "SCA")
AMENDMENTS = ("ACA", "SCA")
NUM = re.compile(r"\d{8}0(AB|SB|ACA|SCA)(\d+)$")


def is_amendment(p):
    return re.match(r"[A-Z]+", p)[0] in AMENDMENTS


def withdrawal(p, subject):
    """A measure taking an earlier amendment off the ballot ("Withdrawal of Assembly Constitutional Amendment No. 13"
    of 2025, ACA 21): a resolution that doesn't go to the voters, so it's left out like the others."""
    return is_amendment(p) and re.match(r"Withdrawal of", subject or "")


def folder(session):
    return os.path.join(P.DATA, str(session))


def sessions():
    """The sessions downloaded (a folder with BILL_TBL.dat)."""
    return sorted(int(f) for f in os.listdir(P.DATA) if f.isdigit() and os.path.exists(os.path.join(P.DATA, f, "BILL_TBL.dat")))


def rows(session, table):
    """A table's rows as lists: strings are in backticks, missing values are NULL."""
    path = os.path.join(folder(session), f"{table}_TBL.dat")
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            yield [None if x == "NULL" else x.strip("`") for x in line.rstrip("\n").split("\t")]


def iso(d):
    return (d or "")[:10]


def committees(session):
    """Location code -> (house letter, committee name): "CX25" -> ("A", "Appropriations")."""
    out = {}
    for r in rows(session, "LOCATION_CODE"):
        m = re.match(r"(Asm|Sen) (.+)", r[4] or "")
        if r[1][:2] in ("CS", "CX") and m:
            out[r[1]] = ("A" if m[1] == "Asm" else "S", (r[5] or m[2]).strip())
    return out


def decode(text, kind, house, code, comms):
    """One history line in the site's shared wording (only the steps its rules use), else as written."""
    t = re.sub(r"\s+", " ", text).strip()
    name = comms.get(code, ("", ""))[1].upper() if code else ""
    if re.match(r"Read third time[.,] (?:and )?(?:amended\. )?(?:[Uu]rgency clause adopted\. )?[Pp]assed", t):
        return f"PASSED {HOUSE[house].upper()}"
    # A constitutional amendment (a resolution) is adopted, not passed.
    if re.match(r"(?:Read third time[.,] |Read\. )?Adopted(?: as amended)?(?:\.| and to (?:Senate|Assembly))", t):
        return f"PASSED {HOUSE[house].upper()}"
    # "From committee: Do pass and re-refer to Com. on APPR." is a committee vote; "From committee chair, with
    # author's amendments: Amend, and re-refer" is the sponsor's amendment going back to the same committee.
    if re.match(r"From committee:.*\b(do pass|be adopted)\b.*re-?refer", t, re.I) and kind == "Committee" and name:
        return f"REPORTED REFERRED TO {name}"
    if re.match(r"From committee:.*\b(Do pass|Be adopted|Ordered to (third|second) reading|Be ordered to)", t, re.I):
        return "REPORTED"
    if re.match(r"(Re-?referred|Referred) to Coms?\.", t) and kind == "Committee" and name:
        return f"REFERRED TO {name}"
    if re.match(r"Enrolled and presented to the Governor", t):
        return "DELIVERED TO GOVERNOR"
    if re.match(r"Vetoed by (the )?Governor", t):
        return "VETOED"
    m = re.match(r"Chaptered by Secretary of State\.? -? ?Chapter (\d+)", t)
    if m:
        return f"SIGNED CHAP.{m[1]}"
    return t


def stage_of(steps, status):
    """How far a bill got, 0-6, from its history (steps: (date, house, text, raw, kind)) and its status."""
    texts = [t for _, _, t, _, _ in steps]
    raws = [x for _, _, _, x, _ in steps]
    if status == "Chaptered" or any(t.startswith("SIGNED") for t in texts):
        return 5
    veto = max((i for i, t in enumerate(texts) if t == "VETOED"), default=-1)
    sent = max((i for i, t in enumerate(texts) if t == "DELIVERED TO GOVERNOR"), default=-1)
    if veto >= 0 and veto > sent:
        return 6
    if sent >= 0:
        return 4
    # Passed both houses: on its way to enrollment ("Ordered to Engrossing and Enrolling", "To enrollment"), unless
    # it was taken back later ("Withdrawn from Engrossing and Enrolling").
    enroll = max((i for i, x in enumerate(raws) if re.search(r"(?<!Withdrawn from )Engrossing and Enrolling|To enrollment", x)
                  and re.search(r"concurred in|Ordered to Engrossing and Enrolling|To enrollment", x)), default=-1)
    back = max((i for i, x in enumerate(raws) if re.match(r"Withdrawn from Engrossing and Enrolling", x)), default=-1)
    if enroll > back:
        return 3
    if any(t.startswith("PASSED") for t in texts):
        return 2
    return 1 if steps and steps[-1][4] == "Floor" else 0


def veto_messages(session):
    """Bill -> (date, the governor's reasons): the veto message without its greeting, its "I am returning ... without
    my signature" line and its signature."""
    path = os.path.join(folder(session), "vetoes.json")
    texts = json.load(open(path)) if os.path.exists(path) else {}
    out = {}
    for r in rows(session, "VETO_MESSAGE"):
        m = NUM.match(r[0] or "")
        t = texts.get(r[2] or "")
        if not (m and t):
            continue
        t = t.replace("\xa0", " ").replace("\r", "")
        t = re.sub(r"(?is)^\s*To the Members of the California State (Senate|Assembly):\s*", "", t)
        t = re.sub(r"(?is)^\s*I am returning [^.]*? without my signature\.\s*", "", t)
        t = re.split(r"\n\s*Sincerely,", t)[0]
        t = "\n\n".join(p.strip() for p in re.split(r"\n\s*\n", t) if p.strip())
        out[m[1] + m[2]] = (iso(r[1]), t)
    return out


# ---- The same bill in earlier sessions. Bills come back under new numbers, and the files don't link them, so: an
# earlier bill whose subject starts the same way ("Firearms: ...") and whose digest says the same things the bill
# would do (cosine of rarity-weighted words at least 0.6, or 0.5 with the same lead author). Only the digest's
# "This bill would ..." sentences count: the "Existing law ..." part is shared by many bills, and some sentences are
# in thousands of digests ("no reimbursement is required by this act"). Placeholder bills (spot and intent bills),
# budget bills and the yearly claims and validation bills never match, nor bills naming different counties or cities ("deputy
# sheriffs: County of Modoc" and "... County of Merced"). Up to two sessions back.
_EARLIER, _IDF = {}, {}
_STOCK = re.compile(r"reimburse|state-mandated local program|findings and declarations|urgency statute|take effect immediately|"
                    r"intent of the Legislature|special statute|nonsubstantive|incorporate additional changes|operative only if", re.I)
_PLACE = re.compile(r"\b(?:County|City|Cities|Town) of ([A-Z][a-z]+(?: [A-Z][a-z]+)*)|\b([A-Z][a-z]+(?: [A-Z][a-z]+)?) County\b")


def _own(text):
    """The digest's sentences about what the bill would do, without the stock ones."""
    sents = re.split(r"(?<=[.;])\s+", text.replace("\n", " "))
    return " ".join(x for x in sents if re.match(r"(The|This) (bill|measure) (?:instead )?(would|also)", x) and not _STOCK.search(x))


def _texts(session):
    path = os.path.join(P.DATA, f"texts_{session}.json")
    return json.load(open(path)) if os.path.exists(path) else {}


def _idf():
    if not _IDF:
        docs = [set(re.findall(r"[a-z0-9]{3,}", _own(t["statement"]).lower())) for y in sessions() for t in _texts(y).values()]
        df = defaultdict(int)
        for d in docs:
            for w in d:
                df[w] += 1
        _IDF.update({w: math.log(len(docs) / n) for w, n in df.items()})
        _IDF[""] = math.log(max(2, len(docs)))
    return _IDF


def _vector(text):
    idf, tf = _idf(), defaultdict(int)
    for w in re.findall(r"[a-z0-9]{3,}", text.lower()):
        tf[w] += 1
    v = {w: (1 + math.log(c)) * idf.get(w, idf[""]) for w, c in tf.items()}
    n = math.sqrt(sum(x * x for x in v.values())) or 1
    return {w: x / n for w, x in v.items()}


def _session(session):
    """Bill -> (subject heading, lead author, places named, weighted digest), for matching."""
    if session not in _EARLIER:
        texts, out = _texts(session), {}
        subject = {r[0]: r[6] or "" for r in rows(session, "BILL_VERSION")}
        lead = {}
        for r in rows(session, "BILL_VERSION_AUTHORS"):
            if r[4] == "LEAD_AUTHOR" and r[0] not in lead:
                lead[r[0]] = r[3]
        for r in rows(session, "BILL"):
            if r[2] != "0" or r[3] not in KINDS:
                continue
            p, subj = f"{r[3]}{r[4]}", subject.get(r[10], "")
            text = texts.get(p, {}).get("statement", "")
            own = _own(text)
            if len(own) < 80 or re.match(r"(Budget Act|Claims against the state|Validations)", subj) or withdrawal(p, subj):
                continue
            head = re.sub(r"[^a-z ]", "", subj.split(":")[0].lower()).strip()
            places = {x or y for x, y in _PLACE.findall(subj + " " + own)}
            out[p] = (head, lead.get(r[10], ""), places, _vector(own))
        _EARLIER[session] = out
    return _EARLIER[session]


def earlier(session, bill):
    """{(session, bill), ...}: this bill in the two sessions before."""
    out = set()
    me = _session(session).get(bill)
    if not me:
        return out
    for y in (session - 2, session - 4):
        if not os.path.exists(os.path.join(folder(y), "BILL_TBL.dat")):
            continue
        best = None
        for other, (head, author, places, vec) in _session(y).items():
            if is_amendment(other) != is_amendment(bill) or head != me[0] or not head or (places and me[2] and not places & me[2]):
                continue
            cos = sum(x * vec.get(w, 0) for w, x in me[3].items())
            if cos >= 0.6 or (cos >= 0.5 and author and author == me[1]):
                if not best or cos > best[0]:
                    best = (cos, other)
        if best:
            out.add((y, best[1]))
    return out


VOTE_CODE = {"NOE": "N", "ABS": "A"}  # the page's codes: N no, B abstain, A absent or not voting


def load_session(session):
    """Read one session's bills and return (records, bill number -> record index, fetched time, delegation)."""
    comms = committees(session)
    bills = {}
    for r in rows(session, "BILL"):
        if r[2] == "0" and r[3] in KINDS:
            bills[r[0]] = r
    p_of = {bid: f"{r[3]}{r[4]}" for bid, r in bills.items()}

    # Each version's subject (the bill's short title) and authors; the latest version's are the bill's.
    subject, authors = {}, defaultdict(list)
    for r in rows(session, "BILL_VERSION"):
        subject[r[0]] = r[6] or ""
    for r in rows(session, "BILL_VERSION_AUTHORS"):
        if r[6] != "N":
            authors[r[0]].append((r[1], (r[2] or "")[:1], r[3] or "", r[4] or ""))

    # Members' full names by (house, the name the data uses): ("S", "Limón") -> "Monique Limón".
    full = {}
    for r in rows(session, "LEGISLATOR"):
        if r[3] in ("A", "S") and r[4]:
            full[(r[3], r[4])] = " ".join(x for x in (r[5], r[6]) if x) or r[4]

    hist = defaultdict(list)
    for r in rows(session, "BILL_HISTORY"):
        if r[0] in bills:
            hist[r[0]].append(r)

    # Committee abbreviations as each house writes them in the history ("APPR."), from the lines that name a
    # committee and give its code, so other lines can show the full name.
    abbr = {}
    for bid, hs in hist.items():
        for r in hs:
            m = re.match(r"(?:Re-?referred|Referred) to Com\. on\s+(.+?)\.?\s*$", re.sub(r"\s+", " ", r[3] or ""))
            if m and r[11] in comms and r[10] == "Committee":
                abbr[(comms[r[11]][0], m[1].rstrip(".") + ".")] = comms[r[11]][1]

    # Longest first, so "H. & C.D." isn't read as "H.".
    by_house = {h: sorted(((ab, name) for (hh, ab), name in abbr.items() if hh == h), key=lambda x: -len(x[0])) for h in HOUSE}

    def spell(text, house):
        """Committee abbreviations ("Com. on  H. & C.D.", "APPR. suspense file") as the committees' names."""
        t = re.sub(r"\s+", " ", text)
        for ab, name in by_house.get(house, []):
            if ab in t:
                t = re.sub(r"(Coms?\. on|and|Referred to|Placed on) " + re.escape(ab) + r"(?=[\s)]|$)", lambda m: f"{m[1]} {name}", t)
        return t.replace("Coms. on", "Committees on").replace("Com. on", "Committee on")

    # Roll calls: the summary of each vote and how each member voted.
    detail = defaultdict(list)
    for r in rows(session, "BILL_DETAIL_VOTE"):
        if r[0] in bills:
            detail[(r[0], r[1], r[3], r[4], r[6])].append((r[2], r[5]))
    summary = defaultdict(list)
    for r in rows(session, "BILL_SUMMARY_VOTE"):
        if r[0] in bills:
            summary[r[0]].append(r)

    seat_of, party_of = seats(session) if session == CURRENT else ({}, {})
    vetoes = veto_messages(session)
    # The digests (states/ca/texts.py), for finding similar bills; they aren't put in the page.
    tpath = os.path.join(P.DATA, f"texts_{session}.json")
    digests = json.load(open(tpath)) if os.path.exists(tpath) else {}

    def member(house, name):
        return seat_of.get((house, name)) or f"{house}?{full.get((house, name), name)}"

    src = json.load(open(os.path.join(folder(session), "source.json"))) if os.path.exists(os.path.join(folder(session), "source.json")) else {}
    stamp = src.get("modified") or datetime.fromtimestamp(os.path.getmtime(os.path.join(folder(session), "BILL_TBL.dat"))).isoformat()
    fetched = datetime.fromisoformat(stamp).astimezone(ZoneInfo(P.TIMEZONE)).strftime("%Y-%m-%d %H:%M")

    recs, index = [], {}
    for bid, b in sorted(bills.items(), key=lambda kv: (kv[1][3], int(kv[1][4]))):
        p = p_of[bid]
        origin = p[0]
        hs = sorted(hist[bid], key=lambda r: (r[2] or "", int(r[6] or 0), int(r[1] or 0)))
        steps = []
        for r in hs:
            house = LETTER.get(r[9] or "", "")
            raw = re.sub(r"\s+", " ", r[3] or "").strip()
            t = decode(raw, r[10] or "", house or origin, r[11], comms)
            # A passage the house undid ("Action rescinded whereby the bill was read third time, passed, ...").
            if re.match(r"Action rescinded whereby (?:the )?bill was read (?:a )?third time", raw):
                k = next((k for k in range(len(steps) - 1, -1, -1) if steps[k][2].startswith("PASSED")), None)
                if k is not None:
                    steps[k] = steps[k][:2] + (steps[k][3],) + steps[k][3:]
            steps.append((iso(r[2]), house, t if t != raw else spell(raw, house or origin), raw, r[10] or ""))
        status = b[17] or ""
        stage = stage_of(steps, status)
        amendment = is_amendment(p)
        # A constitutional amendment both houses adopted is filed with the Secretary of State ("Res. Chapter 176") and
        # goes to the voters: it never reaches the governor.
        if amendment and (stage >= 3 or status == "Chaptered" or any("Res. Chapter" in x for _, _, _, x, _ in steps)):
            stage = 3
        texts = [t for _, _, t, _, _ in steps]
        passed = {h for _, h, t, _, _ in steps if t.startswith("PASSED")}
        if stage >= 3:
            passed = {"S", "A"}  # it passed both houses, even where the history leaves out a vote (AB876 of 2023)
        passed_in = None
        if stage == 2:
            last = max(((d, h) for d, h, t, _, _ in steps if t.startswith("PASSED")), default=None)
            passed_in = HOUSE[last[1]] if last else HOUSE[origin]

        # Where it is now: the last line's house and place.
        where = steps[-1] if steps else ("", origin, "", "", "Desk")
        now_house = where[1] or origin
        code = hs[-1][11] if hs else None
        committee = comms[code][1] if where[4] == "Committee" and code in comms else None
        refs = [(h, t[len("REFERRED TO "):]) for _, h, t, _, _ in steps if t.startswith("REFERRED TO")] + \
               [(h, t[len("REPORTED REFERRED TO "):]) for _, h, t, _, _ in steps if t.startswith("REPORTED REFERRED TO")]
        by_upper = {(h, name.upper()): name for h, name in comms.values()}
        comm_names = {by_upper.get((h, c), c.title()) for h, c in refs}
        comm_list = sorted({f"{h} · {by_upper.get((h, c), c.title())}" for h, c in refs if h})
        latest = b[10]
        title = (subject.get(latest) or "").strip() or p
        if withdrawal(p, title):
            continue
        if amendment and not re.search(r"constitution", title, re.I):
            title = f"Constitutional amendment: {title}"

        topics = [k for k, (label, cset, _, _) in P.TOPICS.items()
                  if comm_names & cset or (k in P.TOPIC_WORDS and P.TOPIC_WORDS[k].search(title))]
        if amendment:
            topics = ["const"] + [t for t in topics if t != "const"]
        own = [by_upper.get((h, c), c.title()) for h, c in refs if h == origin]
        first_comms = []
        if own:
            i0 = next(i for i, (_, h, t, _, _) in enumerate(steps) if h == origin and "REFERRED TO" in t)
            left = any(h == origin and (t == "REPORTED" or t.startswith("REPORTED REFERRED") or t.startswith("PASSED"))
                       for _, h, t, _, _ in steps[i0 + 1:])
            first_comms.append((origin, own[0], left))
        main_topic = next((t for _, name, _ in first_comms for t in topics if name in P.TOPICS[t][1]), topics[0] if topics else "")
        raw = [x for _, _, _, x, _ in steps]
        fate = ("passed" if any(t == "REPORTED" or t.startswith("REPORTED REFERRED") for t in texts) else
                "defeated" if any(re.search(r"Failed passage", x) for x in raw) else
                "held" if any(re.search(r"Held (in committee and )?under submission", x) for x in raw) else "none")

        auth = authors.get(latest, [])
        leads = [(h, n) for kind, h, n, c in auth if c == "LEAD_AUTHOR"]
        co = [(h, n) for kind, h, n, c in auth if c in ("PRINCIPAL_COAUTHOR", "COAUTHOR")]

        def named(h, n):
            return full.get((h, n), n) if h in HOUSE else n

        lead_names = [named(h, n) for h, n in leads] or ["—"]
        sponsor = lead_names[0]
        lead_house = leads[0][0] if leads else origin

        if stage == 0 and committee:
            desc = f"In {HOUSE[now_house]} committee"
        elif stage == 2 and re.search(r"Concurrence in (Senate|Assembly) amendments pending", raw[-1] if raw else ""):
            desc = f"On the {HOUSE[origin]} floor, to agree to the {HOUSE['S' if origin == 'A' else 'A']}'s changes"
        elif stage <= 1 and where[4] == "Floor":
            desc = f"On the {HOUSE[now_house]} floor"
        elif stage >= 2:
            desc = {2: f"Passed the {passed_in}", 3: "Passed both houses", 4: "On the governor's desk",
                    5: "Signed into law", 6: "Vetoed"}[stage]
        else:
            desc = status.capitalize() if status else "Introduced"

        def dates(test, mode="last"):
            ds = sorted({d for d, h, t, x, k in steps if test(h, t, x) and d})
            return {"first": ds[0], "last": ds[-1], "all": ";".join(ds)}[mode] if ds else ""

        votes = []
        for r in sorted(summary[bid], key=lambda r: (r[2], int(r[3] or 0))):
            loc = r[1]
            if loc in ("AFLOOR", "SFLOOR"):
                vh, kind, cname = loc[0], "F", None
            elif loc in comms:
                vh, kind, cname = comms[loc][0], "C", comms[loc][1]
            else:
                continue
            roll = list(dict.fromkeys(detail.get((bid, loc, r[2], r[3], r[4]), [])))
            names = [[member(vh, n), VOTE_CODE.get(v, "A")] for n, v in roll if v != "AYE"]
            # Two roll calls with the same time, sequence and motion share one list (SB99 of 2023): when it can't be
            # this one's, leave the names off rather than show the wrong ones.
            if sum(1 for _, c in names if c == "N") != int(r[6] or 0):
                names = []
            votes.append([vh, kind, cname, iso(r[2]), int(r[5] or 0), int(r[6] or 0), names])

        action_dates = [d for d, _, _, _, _ in steps if d]
        for h, n in leads + co:
            if (h, n) in party_of:
                _PARTIES.setdefault(session, {})[(h, named(h, n))] = party_of[(h, n)]
        vers = {"p": p, "sponsor": sponsor, "district": int((seat_of.get((lead_house, leads[0][1])) if leads else "") and seat_of[(lead_house, leads[0][1])][2:] or 0),
                "cosponsors": [named(h, n) for h, n in leads[1:] + co], "primes": max(1, len(leads)), "cosp": len(leads[1:] + co),
                "statusDesc": desc, "committee": committee if stage in (0, 2) else None,
                "actions": [[d, t] for d, _, t, _, _ in steps]}
        chap = b[9]
        rec = {
            "nums": [p], "base": [p], "prev": earlier(session, p),
            "title": title, "summary": "", "act": "", "lawCode": "", "law": None, "laws": [],
            "comms": comm_list, "topics": topics, "places": [], "narrow": P.narrow_kind(title),
            "commFate": fate, "mainTopic": main_topic, "local": "local" in topics,
            "senDeleg": False, "asmDeleg": False, "budget": bool(re.match(r"Budget Act of", title)),
            "passedS": "S" in passed, "passedA": "A" in passed, "program": None,
            "stage": stage, "passedIn": passed_in,
            "chapter": int(chap) if chap and str(chap).isdigit() and stage == 5 else None,
            "veto": None, "memo": "",
            "vetoMemo": {"year": int(vetoes[p][0][:4]), "signer": P.governor_on(vetoes[p][0]), "text": vetoes[p][1]} if p in vetoes else None,
            "simText": digests.get(p, {}).get("statement", ""),
            "comm": committee if stage == 0 else None,
            "first": min(action_dates, default=f"{session}-01-01"),
            "last": max(action_dates, default=f"{session}-01-01"),
            "cosp": vers["cosp"],
            # Key dates: on the floor, passed the Senate, passed the Assembly, (New York's return to committee in the new
            # year: none here), sent to the governor, signed, vetoed.
            "keyDates": [
                dates(lambda h, t, x: h == origin and t == "REPORTED", "first"),
                dates(lambda h, t, x: t == "PASSED SENATE", "all"),
                dates(lambda h, t, x: t == "PASSED ASSEMBLY", "all"),
                "",
                dates(lambda h, t, x: t == "DELIVERED TO GOVERNOR"),
                dates(lambda h, t, x: t.startswith("SIGNED")),
                dates(lambda h, t, x: t == "VETOED"),
            ],
            "votes": votes, "firstComms": first_comms, "vers": [vers],
        }
        index[p] = len(recs)
        recs.append(rec)
    return recs, index, fetched, {"SENATE": [], "ASSEMBLY": []}


def agendas(session):
    """Bills set for committee hearings: bill -> [["Assembly Appropriations", "2026-08-14T00:00:00"], ...]."""
    comms = committees(session)
    out = defaultdict(list)
    for r in rows(session, "COMMITTEE_HEARING"):
        m = NUM.match(r[0] or "")
        if not m or r[4] not in comms:
            continue
        h, name = comms[r[4]]
        entry = [f"{HOUSE[h]} {name}", f"{iso(r[3])}T00:00:00"]
        if entry not in out[m[1] + m[2]]:
            out[m[1] + m[2]].append(entry)
    return dict(out)


# ---- Sponsors' parties, from the current legislators (filled by load_session).
_PARTIES = {}


def parties(session, recs):
    """Party ("D" or "R") for each sponsor as the records name them, keyed by (house, name)."""
    return {k: v for k, v in _PARTIES.get(session, {}).items() if v in ("D", "R")}


def seats(session):
    """(house, the name the data uses) -> seat id ("S:2", "A:3"), and -> party letter, from
    data/ca/contacts_<session>.json (states/ca/contacts.py), else from LEGISLATOR_TBL's districts."""
    seat_of, party_of = {}, {}
    path = os.path.join(P.DATA, f"contacts_{session}.json")
    if os.path.exists(path):
        for sid, p in json.load(open(path))["people"].items():
            if p.get("dataName"):
                seat_of[(sid[0], p["dataName"])] = sid
                party_of[(sid[0], p["dataName"])] = (p.get("party") or "")[:1]
        return seat_of, party_of
    for r in rows(session, "LEGISLATOR"):
        if r[3] in ("A", "S") and r[4] and r[13] != "N":
            seat_of[(r[3], r[4])] = f"{r[3]}:{int(r[0][2:])}"
            party_of[(r[3], r[4])] = {"DEM": "D", "REP": "R"}.get(r[11] or "", "")
    return seat_of, party_of
