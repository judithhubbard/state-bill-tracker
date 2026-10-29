"""Virginia: reads the Legislative Information System's data files for each session (data/va/<year><n>/,
from states/va/fetch.py; <n> is 1 for the regular session) and turns them into the bill records
build_data.py works with.

Every state's convert.py has the same functions: sessions(), load_session(session), agendas(session) and
parties(session, recs).

Virginia's history lines are plain English already ("Referred to Committee on Labor and Commerce",
"Read third time and passed House (64-Y 34-N 0-A)"). The steps the site's rules depend on (referrals,
committee reports, passage, the governor's actions) are put in the wording New York's data uses; the rest
are kept as written. Each bill passes both houses under its own number (HB1 goes to the Senate as HB1).
"""
import csv, glob, json, math, os, re
from collections import defaultdict
from datetime import datetime
from zoneinfo import ZoneInfo

from . import profile as P

CURRENT = P.session_of(datetime.now(ZoneInfo(P.TIMEZONE)).year)
HOUSE = {"H": "House", "S": "Senate"}


def folder(session):
    return os.path.join(P.DATA, f"{session}1")


def sessions():
    """The regular sessions downloaded (a folder with BILLS.CSV)."""
    return sorted(int(os.path.basename(f)[:4]) for f in glob.glob(os.path.join(P.DATA, "????1")) if os.path.exists(os.path.join(f, "BILLS.CSV")))


def rows(session, name):
    path = os.path.join(folder(session), name)
    if not os.path.exists(path):
        return
    with open(path, encoding="cp1252", errors="replace", newline="") as f:
        for r in csv.DictReader(f, skipinitialspace=True):
            yield {(k or "").strip(): (v or "").strip() for k, v in r.items() if k}


def iso(d):
    """"3/14/2026" or (the 2024 files) "2024-03-02T00:00:00" -> "2026-03-14"."""
    m = re.match(r"(\d+)/(\d+)/(\d{4})", d or "")
    if m:
        return f"{m.group(3)}-{int(m.group(1)):02d}-{int(m.group(2)):02d}"
    m = re.match(r"(\d{4})-(\d\d)-(\d\d)", d or "")
    return m.group(0) if m else ""


def num(bill):
    """"HB0001" or "HB1" -> "HB1"."""
    m = re.match(r"([A-Z]+)0*(\d+)", bill or "")
    return f"{m.group(1)}{m.group(2)}" if m else bill


TALLY = r"(?: \([^)]*\))*$"


def decode(desc, comms):
    """One history line in the site's shared wording (only the steps its rules use)."""
    d = desc.strip()
    m = re.match(r"(?:Referred|Rereferred|Re-referred) to (?:Committee (?:on|for) )?(.+?)" + TALLY, d)
    if m:
        return f"REFERRED TO {m.group(1).upper()}"
    m = re.match(r"Reported from (.+?) and (?:re)?referred to (?:Committee (?:on|for) )?(.+?)" + TALLY, d)
    if m:
        return f"REPORTED REFERRED TO {m.group(2).upper()}"
    if re.match(r"Reported from ", d):
        return "REPORTED"
    m = re.match(r"(?:Read third time and )?passed (House|Senate)\b", d, re.I)
    if m and not re.match(r"Passed by\b", d, re.I):
        return f"PASSED {m.group(1).upper()}"
    if re.match(r"(?:Enrolled Bill )?[Cc]ommunicated to Governor", d):
        return "DELIVERED TO GOVERNOR"
    # Signed, or enacted once the Legislature accepted the governor's amendments.
    m = re.match(r"(?:Approved by Governor-Chapter|Enacted, Chapter) (\d+)", d)
    if m:
        return f"SIGNED CHAP.{m.group(1)}"
    if re.match(r"Vetoed by Governor", d):
        return "VETOED"
    if re.match(r"Stricken (?:at|by) (?:the )?request of (?:the )?Patron", d, re.I):
        return "ENACTING CLAUSE STRICKEN"
    return re.sub(r"\s+", " ", d)


def stage_of(b, acts, live):
    """How far a bill got, 0-6, from BILLS.CSV's flags and its history."""
    texts = [t for _, h, t, _ in acts]
    # The file's Approved and Vetoed flags are sometimes both set, or (2025) neither: the history decides,
    # and a signature after a veto (a vetoed bill can come back amended) wins.
    if any(t.startswith("SIGNED") for t in texts) or (b["Approved"] == "Y" and b["Chapter_id"]):
        return 5
    if b["Vetoed"] == "Y" or "VETOED" in texts:
        return 6
    # Sent back with the governor's amendments: the Legislature votes on them at the reconvened session.
    gov = [i for i, t in enumerate(texts) if re.search(r"Governor's (recommendation|amendment)", t, re.I)]
    if gov and not any(t == "DELIVERED TO GOVERNOR" for t in texts[gov[-1] + 1:]):
        return 3  # amendments aren't a veto: a bill whose amendments failed died having passed both houses
    if "DELIVERED TO GOVERNOR" in texts:
        return 4
    # The file marks a bill "Passed" when each house passed it, even if the two never agreed on one text
    # ("Different conference report agreed to by each chamber (failed)"): that bill died between the houses.
    failed = any(re.search(r"conference report.*\(failed\)|^Failed\b", t, re.I) for t in texts[-6:])
    if b["Passed"] == "Y" and not failed:
        return 3
    if b["Passed_house"] == "Y" or b["Passed_senate"] == "Y":
        return 2
    return 1 if on_floor(acts) else 0


def on_floor(acts):
    """Out of committee and waiting for a floor vote in its current house."""
    where = None
    for _, h, t, _ in acts:
        if t.startswith("REFERRED TO"):
            where = "comm"
        elif t == "REPORTED" or re.match(r"(Read (first|second) time|Engrossed)", t):
            where = "floor"
        elif t.startswith("REPORTED REFERRED TO"):
            where = "comm"
        elif t.startswith("PASSED"):
            where = "comm"  # now in the other house, which refers it to a committee
    return where == "floor"


def read_votes(session, members):
    """Roll calls by id: id -> [[member id, vote], ...] (Y, N, X = not voting, A = abstain)."""
    out = {}
    path = os.path.join(folder(session), "VOTE.CSV")
    if not os.path.exists(path):
        return out
    with open(path, encoding="cp1252", errors="replace", newline="") as f:
        for r in csv.reader(f):
            if len(r) > 2:
                out[r[0].strip()] = [(r[i].strip(), r[i + 1].strip()) for i in range(1, len(r) - 1, 2) if r[i].strip()]
    return out


VOTE_CODE = {"N": "N", "A": "B", "X": "A"}  # the page's codes: N no, B abstain, A absent or not voting
VOTES = re.compile(r"^(Reported from|Failed to report|Passed by indefinitely|Continued to|(?:Read third time and )?[Pp]assed (House|Senate)|"
                   r"(?:House|Senate) (?:concurred|rejected|agreed|sustained|overrode)|Passed (House|Senate))")


# ---- The same bill in earlier years. Virginia's numbers start over each year and its files don't link a bill
# to an earlier one, so: a bill continued from last year (same number, "Continued from last session"), or an
# earlier bill with the same subject heading ("Minimum wage; ...") whose Legislative Services summary shares at
# least 60% of its words (40% when the same legislator carries it), or is as close by rarity-weighted words
# (cosine 0.66, or 0.55 with the same legislator). Checked by hand on samples, 2026-10-29: about 95% of links are
# the same bill; some reworked bills are missed. Up to two years back.
_EARLIER = {}
_SKIP = {"bill", "this", "that", "with", "from", "which", "shall", "such", "provides", "requires", "under", "certain"}


def _heading(title):
    return re.sub(r"[^a-z ]", "", title.split(";")[0].lower()).strip()


def _words(text):
    return set(re.findall(r"[a-z0-9]{3,}", text.lower())) - _SKIP


_IDF = {}


def _idf():
    """How rare each word is across every year's summaries: "menopause" counts for more than "insurer"."""
    if not _IDF:
        docs = []
        for y in sessions():
            path = os.path.join(P.DATA, f"texts_{y}.json")
            if os.path.exists(path):
                docs += [set(re.findall(r"[a-z0-9]{3,}", t["statement"].lower())) for t in json.load(open(path)).values()]
        df = defaultdict(int)
        for d in docs:
            for w in d:
                df[w] += 1
        _IDF.update({w: math.log(len(docs) / n) for w, n in df.items()})
        _IDF[""] = math.log(max(2, len(docs)))
    return _IDF


def _vector(text):
    """A summary as rarity-weighted word counts, scaled to length 1."""
    idf, tf = _idf(), defaultdict(int)
    for w in re.findall(r"[a-z0-9]{3,}", text.lower()):
        tf[w] += 1
    v = {w: (1 + math.log(c)) * idf.get(w, idf[""]) for w, c in tf.items()}
    n = math.sqrt(sum(x * x for x in v.values())) or 1
    return {w: x / n for w, x in v.items()}


def _year(session):
    """Bill -> (heading, summary words, chief patron id, weighted summary), for matching."""
    if session not in _EARLIER:
        path = os.path.join(P.DATA, f"texts_{session}.json")
        texts = json.load(open(path)) if os.path.exists(path) else {}
        out = {}
        for r in rows(session, "BILLS.CSV"):
            if r["Bill_id"][:2] in ("HB", "SB"):
                text = texts.get(num(r["Bill_id"]), {}).get("statement") or r["Bill_description"]
                out[num(r["Bill_id"])] = (_heading(r["Bill_description"]), _words(text), r["Patron_id"], _vector(text))
        _EARLIER[session] = out
    return _EARLIER[session]


def earlier(session, bill, continued):
    """{(year, bill), ...}: this bill in the two years before."""
    out = {(session - 1, bill)} if continued else set()
    me = _year(session).get(bill)
    if not me:
        return out
    for y in (session - 1, session - 2):
        if not os.path.exists(os.path.join(folder(y), "BILLS.CSV")):
            continue
        best = None
        for other, (head, words, patron, vec) in _year(y).items():
            # Claims ("Relief; ...") name different people, and the yearly drug-schedule bill adds different
            # substances each year: neither is the same bill coming back.
            if head != me[0] or not head or head in ("relief", "drug control act"):
                continue
            same = bool(patron) and patron == me[2]
            j = len(me[1] & words) / max(1, len(me[1] | words))
            cos = sum(x * vec.get(w, 0) for w, x in me[3].items())
            if j >= 0.6 or (j >= 0.4 and same) or cos >= 0.66 or (cos >= 0.55 and same):
                if not best or j > best[0]:
                    best = (j, other)
        if best:
            out.add((y, best[1]))
    return out


def load_session(session):
    """Read one session's bills and return (records, bill number -> record index, fetched time, delegation)."""
    live = session >= CURRENT
    comms = {r["COM_COMNO"]: (r["CHAMBER"], r["COM_NAME"]) for r in rows(session, "Committees.csv")}
    names = {r["MBR_MBRNO"]: re.sub(r"\s+", " ", r["MBR_NAME"]).strip() for r in rows(session, "Members.csv")}
    bills = {num(r["Bill_id"]): r for r in rows(session, "BILLS.CSV") if r["Bill_id"][:2] in ("HB", "SB")}
    hist = defaultdict(list)
    for r in rows(session, "HISTORY.CSV"):
        b = num(r["Bill_id"])
        if b in bills:
            hist[b].append(r)
    spons = defaultdict(list)
    for r in rows(session, "Sponsors.csv"):
        spons[num(r["BILL_NUMBER"])].append(r)
    calls = read_votes(session, names)
    fetched = datetime.fromtimestamp(os.path.getmtime(os.path.join(folder(session), "BILLS.CSV")),
                                     ZoneInfo(P.TIMEZONE)).strftime("%Y-%m-%d %H:%M")

    # The current session's members are tied to their seats ("S:34", "H:71"), so the page can show how each
    # legislator voted and which bills they sponsor; earlier sessions' members keep their names.
    seat_of, party_of = seats(session) if session == CURRENT else ({}, {})

    def member(mid):
        return seat_of.get(mid) or f"{mid[:1]}?{names.get(mid, mid)}"

    recs, index = [], {}
    for p, b in sorted(bills.items(), key=lambda kv: (kv[0][:2], int(re.sub(r"\D", "", kv[0]) or 0))):
        acts, votes = [], []
        for h in hist[p]:
            desc = h["History_description"]
            house = desc[:1] if desc[:2] in ("H ", "S ") else ""
            text = desc[2:] if house else desc.strip()
            d = iso(h["History_date"])
            t = decode(text, comms)
            acts.append((d, house, t, text))
            ref = h["History_refid"]
            if ref in calls and VOTES.match(text):
                roll = calls[ref]
                cm = re.match(r"([HS]\d+)V", ref)
                # Vote records write Senate committees "S2"; the committee list writes "S02".
                code = cm and cm.group(1)[0] + cm.group(1)[1:].zfill(2)
                comm = comms.get(code, ("", ""))[1] if cm else None
                vhouse = cm.group(1)[0] if cm else ("S" if ref.startswith("S") else "H")
                votes.append([vhouse, "C" if cm else "F", comm, d,
                              sum(v == "Y" for _, v in roll), sum(v == "N" for _, v in roll),
                              [[member(m), VOTE_CODE.get(v, v)] for m, v in roll if v != "Y"]])
        stage = stage_of(b, acts, live)
        texts = [t for _, _, t, _ in acts]
        passed = {h for _, h, t, _ in acts if t.startswith("PASSED")}
        passed_in = None
        if stage == 2:
            last = max(((d, h) for d, h, t, _ in acts if t.startswith("PASSED")), default=None)
            passed_in = HOUSE[last[1]] if last else HOUSE["S" if b["Passed_senate"] == "Y" else "H"]

        # Where it is now: the committee it was last sent to in the house it's in.
        now_house = ("S" if p.startswith("H") else "H") if passed and stage == 2 else p[0]
        cid = b["Last_senate_committee_id"] if now_house == "S" else b["Last_house_committee_id"]
        committee = comms.get(cid, ("", ""))[1] or None
        in_comm = stage == 0
        refs = [(h, t[len("REFERRED TO "):]) for _, h, t, _ in acts if t.startswith("REFERRED TO")] + \
               [(h, t[len("REPORTED REFERRED TO "):]) for _, h, t, _ in acts if t.startswith("REPORTED REFERRED TO")]
        by_upper = {name.upper(): (ch, name) for ch, name in comms.values()}
        comm_list = sorted({f"{h or by_upper.get(c, ('', ''))[0]} · {by_upper.get(c, ('', c.title()))[1]}" for h, c in refs if h or c in by_upper})
        comm_names = {by_upper.get(c, ("", c.title()))[1] for _, c in refs}
        title = b["Bill_description"].strip()

        topics = [k for k, (label, cset, _, _) in P.TOPICS.items()
                  if comm_names & cset or (k in P.TOPIC_WORDS and P.TOPIC_WORDS[k].search(title))]
        own = [by_upper.get(c, ("", c.title()))[1] for h, c in refs if h == p[0]]
        first_comms = []
        if own:
            i0 = next(i for i, (_, h, t, _) in enumerate(acts) if h == p[0] and "REFERRED TO" in t)
            left = any(h == p[0] and (t == "REPORTED" or t.startswith("REPORTED REFERRED")) for _, h, t, _ in acts[i0 + 1:])
            first_comms.append((p[0], own[0], left))
        main_topic = next((t for _, name, _ in first_comms for t in topics if name in P.TOPICS[t][1]), topics[0] if topics else "")
        raw = [x for _, _, _, x in acts]
        fate = ("passed" if any(t.startswith("REPORTED") for t in texts) else
                "defeated" if any(re.match(r"Failed to report \(defeated\)", x) for x in raw) else
                "held" if any(re.match(r"Passed by indefinitely", x) for x in raw) else "none")

        sp = spons[p]
        chief = [names.get(r["MEMBER_ID"], re.sub(r"\s+", " ", r["MEMBER_NAME"])) for r in sp if "Chief Patron" in r["PATRON_TYPE"]]
        chief_co = [re.sub(r"\s+", " ", r["MEMBER_NAME"]).strip() for r in sp if "Chief Co-Patron" in r["PATRON_TYPE"]]
        co = [re.sub(r"\s+", " ", r["MEMBER_NAME"]).strip() for r in sp if re.search(r"\bCo-Patron\b", r["PATRON_TYPE"]) and "Chief" not in r["PATRON_TYPE"]]
        sponsor = chief[0].strip() if chief else names.get(b["Patron_id"], b["Patron_name"])
        if stage == 0 and committee:
            desc = f"In {HOUSE[now_house]} committee"
        elif stage == 1:
            desc = f"On the {HOUSE[now_house]} floor"
        elif stage >= 2:
            desc = {2: f"Passed the {passed_in}", 3: "Passed both houses", 4: "On the governor's desk",
                    5: "Signed into law", 6: "Vetoed"}[stage]
        else:
            desc = (lambda t: t[:1].upper() + t[1:].lower() if t.isupper() else t)(next((t for t in reversed(texts)), "Introduced"))

        def dates(test, mode="last"):
            ds = sorted({d for d, h, t, x in acts if test(h, t, x) and d})
            return {"first": ds[0], "last": ds[-1], "all": ";".join(ds)}[mode] if ds else ""

        chap = re.match(r"CHAP0*(\d+)", b["Chapter_id"] or "")
        intro = iso(b["Introduction_date"])
        action_dates = [d for d, _, _, _ in acts if d]
        chief_id = next((r["MEMBER_ID"] for r in sp if "Chief Patron" in r["PATRON_TYPE"]), b["Patron_id"])
        for r in sp:
            if r["MEMBER_ID"] in party_of:
                _PARTIES.setdefault(session, {})[(r["MEMBER_ID"][0], re.sub(r"\s+", " ", r["MEMBER_NAME"]).strip())] = party_of[r["MEMBER_ID"]]
        _PARTIES.setdefault(session, {})[(p[0], sponsor)] = party_of.get(chief_id, "")
        vers = {"p": p, "sponsor": sponsor, "district": int(seat_of.get(chief_id, "X:0")[2:]),
                "cosponsors": chief_co + co, "primes": 1 + len(chief_co), "cosp": len(chief_co) + len(co),
                # The committee it's in: in its own house, or (passed one house) the other house's.
                "statusDesc": desc, "committee": committee if stage == 0 or (stage == 2 and not on_floor(acts)) else None,
                "actions": [[d, t] for d, _, t, _ in acts]}
        rec = {
            "nums": [p], "base": [p],
            "prev": earlier(session, p, any(re.match(r"Continued from (last|\d{4}) session", x) for _, _, _, x in acts)),
            "title": title, "summary": "", "act": "", "lawCode": "", "law": None, "laws": [],
            "comms": comm_list, "topics": topics, "places": [], "narrow": P.narrow_kind(title),
            "commFate": fate, "mainTopic": main_topic, "local": "local" in topics,
            "senDeleg": False, "asmDeleg": False, "budget": bool(re.match(r"Budget Bill", title)),
            "passedS": "S" in passed, "passedA": "H" in passed, "program": None,
            "stage": stage, "passedIn": passed_in,
            "chapter": int(chap.group(1)) if chap and stage == 5 else None,
            "veto": None, "memo": "", "vetoMemo": None,
            "comm": committee if stage == 0 else None,
            "first": min(filter(None, [intro] + action_dates), default=f"{session}-01-01"),
            "last": max(action_dates, default=intro or f"{session}-01-01"),
            "cosp": vers["cosp"],
            # Key dates: on the floor, passed the Senate, passed the House, died (not recorded), sent to the
            # governor, signed, vetoed.
            "keyDates": [
                dates(lambda h, t, x: t == "REPORTED" or bool(re.match(r"Read first time", x)), "first"),
                dates(lambda h, t, x: t == "PASSED SENATE", "all"),
                dates(lambda h, t, x: t == "PASSED HOUSE", "all"),
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
    """Bills on committee agendas (DOCKET.CSV): bill -> [["House Labor and Commerce", "2026-01-20T00:00:00"], ...]."""
    comms = {r["COM_COMNO"]: (r["CHAMBER"], r["COM_NAME"]) for r in rows(session, "Committees.csv")}
    out = defaultdict(list)
    for r in rows(session, "DOCKET.CSV"):
        house, name = comms.get(r["Com_no"], ("", ""))
        if house not in HOUSE:
            continue
        entry = [f"{HOUSE[house]} {name}", f"{iso(r['Doc_date'])}T00:00:00"]
        b = num(r["Bill_no"])
        if entry not in out[b]:
            out[b].append(entry)
    return dict(out)


# ---- Sponsors' parties, from the current legislators (filled by load_session).
_PARTIES = {}


def parties(session, recs):
    """Party ("D" or "R") for each sponsor as the records name them, keyed by (house, name)."""
    return {k: v for k, v in _PARTIES.get(session, {}).items() if v in ("D", "R")}


def seats(session):
    """Member id (as the data files write it, "H0386", "S0100") -> seat id, and -> party letter, from
    data/va/contacts_<session>.json (states/va/contacts.py). The Senate's site writes "S100" for "S0100"."""
    path = os.path.join(P.DATA, f"contacts_{session}.json")
    if not os.path.exists(path):
        return {}, {}
    seat_of, party_of = {}, {}
    for sid, p in json.load(open(path))["people"].items():
        mid = p.get("id") or ""
        if mid:
            mid = mid[0] + mid[1:].zfill(4)
            seat_of[mid] = sid
            party_of[mid] = (p.get("party") or "")[:1]
    return seat_of, party_of
