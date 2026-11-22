"""Maryland's bills (downloaded by states/md/fetch.py) in the shape build_data.py reads. House and Senate bills of each
regular session; joint resolutions and special sessions are left out.

The bill list gives each bill's committees, the date and result of each step in each house (first reading and
referral, hearing, committee report, second and third reading), how the houses settled differences
("InteractionBetweenChambers"), whether the General Assembly passed it, its chapter number and its status ("Approved by
the Governor - Chapter 437", "Vetoed by the Governor (Policy)"). It has no dates for the governor's actions and no votes.
Floor votes member by member come from each house's numbered roll-call PDFs (data/md/votes/<year>/<house>.json, read by
fetch.py's roll_calls()): each third reading's roll call, matched by house, bill and legislative day (`floor_vote()`).
Committee votes member by member come from each committee's voting record on the bill (data/md/votes/<year>/
committee.json, fetch.py's committee_votes(); `committee_votes()`).
A committee's unfavorable report kills a bill; most such bills are then withdrawn by their sponsors.

The governor's actions come from each passed bill's page (data/md/governor_<year>.json, from fetch.py): the day the
governor signed or vetoed it, and any override, which the bill list never shows (it was saved on 2025-12-01 and still says
"Vetoed" for the 19 bills of 2025 that became law over the veto on 2025-12-16, in the special session: "Became law per
Maryland Constitution, Chapter 9 of 2025 Special Session"). A bill whose page isn't read yet keeps the old reading, with
the governor's action on the bill's last day.
"""
import json, os, re, unicodedata
from collections import defaultdict
from datetime import datetime
from zoneinfo import ZoneInfo

from states import letters as L
from states.md import profile as P
from states.undated import settle

HOUSE = {"S": "Senate", "H": "House"}
CURRENT = P.session_of(datetime.now(ZoneInfo(P.TIMEZONE)).year)
_PARTIES = {}


def sessions():
    return sorted(int(f[12:16]) for f in os.listdir(P.DATA) if re.fullmatch(r"legislation_\d{4}RS\.json", f))


def text(x):
    return re.sub(r"\s+", " ", x or "").strip()


def load(session):
    return [b for b in json.load(open(os.path.join(P.DATA, f"legislation_{session}RS.json"))) if b["BillNumber"][:2] in ("HB", "SB")]


def number(n):
    return f"{n[:2]}{int(n[2:])}"


def governor(session):
    """Bill number ("HB0270") -> [[chamber, date, action]]: the governor's actions and what followed (overrides)."""
    path = os.path.join(P.DATA, f"governor_{session}.json")
    try:
        return {k: v["lines"] for k, v in json.load(open(path)).items()}
    except (OSError, ValueError):
        return {}


GOV_HOUSE = {"Post Passage": "G", "House": "H", "Senate": "S"}


def contacts():
    paths = sorted(f for f in os.listdir(P.DATA) if re.fullmatch(r"contacts_\d{4}\.json", f))
    return json.load(open(os.path.join(P.DATA, paths[-1])))["people"] if paths else {}


_EARLIER = {}


def _titles(session):
    if session not in _EARLIER:
        out = defaultdict(list)
        if session in sessions():
            for b in load(session):
                out[text(b["Title"]).lower()].append((number(b["BillNumber"]), text(b["SponsorPrimary"])))
        _EARLIER[session] = out
    return _EARLIER[session]


def earlier(session, b):
    """The same bill in the two sessions before: the same title, with the same lead sponsor or only one bill so titled."""
    out = set()
    k, who = text(b["Title"]).lower(), text(b["SponsorPrimary"])
    for y in (session - 1, session - 2):
        old = _titles(y).get(k, [])
        same = [n for n, s in old if s == who]
        if same:
            out.add((y, same[0]))
        elif len(old) == 1 and len(_titles(session).get(k, [])) == 1 and len(k.split()) >= 4:
            out.add((y, old[0][0]))
    return out


MONTH_DAY = re.compile(r"(January|February|March|April|May|June|July|August|September|October|November|December) (\d{1,2}), (\d{4})")


def veto_message(session, p):
    """The governor's veto letter (data/md/vetoes/<year>/<SB448>.txt, fetch.py's veto_letters()) -> {year, signer,
    text}: from "Dear President Ferguson:" (or Speaker) to "Sincerely", or None."""
    try:
        raw = open(os.path.join(P.DATA, "vetoes", str(session), f"{p}.txt"), encoding="utf-8").read()
    except OSError:
        return None
    m = re.search(r"(?m)^\s*Dear [^\n]*[:,]+\s*$", raw)  # ("Dear President Ferguson:," and "Dear President Ferguson,")
    if not m:
        return None
    body = re.split(r"(?m)^\s*(?:Sincerely|Respectfully)", raw[m.end():])[0]
    lines = [ln for ln in body.split("\n") if not re.fullmatch(r"\s*(?:Page \d+( of \d+)?|-?\s*\d+\s*-?)\s*", ln)]
    text_ = L.cut(L.wrapped(lines))
    d = MONTH_DAY.search(raw[:m.start()])
    day = datetime.strptime(" ".join(d.groups()), "%B %d %Y").date().isoformat() if d else f"{session}-05-31"
    return {"year": int(day[:4]), "signer": P.governor_on(day), "text": text_} if text_ else None


# ---- Floor votes ---------------------------------------------------------------------------------------------------
# Each house's roll calls (data/md/votes/<year>/<house>.json, fetch.py's roll_calls(): the PDFs' text). A roll call:
#   SEQ NO. 1100                                Calendar Date: Apr 10, 2026 8:52 (PM)
#   Presiding: Mr. President                    Legislative Date: Mar 24, 2026
#      SB 411      Third Reading (SB) Calendar No.84
#      ...title...
#      On Third Reading
#               42 Yeas         0 Nays   2 Not Voting            0 Excused         3 Absent
#   Voting Yea - 42
#    Mr. President             Gallion        ...          (names in five columns, 2+ spaces apart)
#   Voting Nay - 0 / Not Voting - 2 / Excused from Voting - 0 / Excused (Absent) - 3
# The bill list dates each reading by the house's legislative day ("Legislative Date"), which runs behind the calendar
# late in the session (Mar 24 for a vote on April 10), so votes are matched and dated by it.
GROUPS = [("Voting Yea", "Y"), ("Voting Nay", "N"), ("Not Voting", "A"), ("Excused from Voting", "B"), ("Excused (Absent)", "E")]
TOTALS = {"Y": "Yeas", "N": "Nays", "A": "Not Voting", "B": "Excused", "E": "Absent"}
MON = {m: i + 1 for i, m in enumerate(("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"))}
# Who presided ("Speaker", "Mr. President" in the lists), by session, as the bill list names them (dataName): Speaker
# Adrienne A. Jones until she stepped down in December 2025, then Joseline A. Peña-Melnyk; Senate President Bill Ferguson.
PRESIDING = {"H": {2023: "Jones, A.", 2024: "Jones, A.", 2025: "Jones, A.", 2026: "Peña-Melnyk"}, "S": {}}
PRESIDING_DEFAULT = {"H": "Peña-Melnyk", "S": "Ferguson"}
VOTE_STATS = defaultdict(lambda: defaultdict(int))  # session -> what happened to the roll calls (for checks())


def parse_roll(t):
    """One roll call's text -> {seq, day (legislative, ISO), bill ("SB411"), motion, totals {code: n}, names {code:
    [names]}} or None. Names are as printed ("Washington, M.", "Lewis Young", "Speaker"); '*' (a changed vote) dropped."""
    m = re.search(r"SEQ NO\.\s*(\d+)", t)
    d = re.search(r"Legislative Date:\s*([A-Z][a-z]{2})[a-z]*\.? (\d{1,2}), (\d{4})", t)
    tot = re.search(r"(\d+) Yeas\s+(\d+) Nays\s+(\d+) Not Voting\s+(\d+) Excused\s+(\d+) Absent", t)
    if not (m and d and tot and d.group(1) in MON):
        return None
    head = t[:tot.start()]
    b = re.search(r"(?m)^\s*([HS])([BJ])\s+(\d+)\b", head)
    motion = ""
    lines = [ln.strip() for ln in head.split("\n") if ln.strip()]
    for ln in lines:
        if re.match(r"On (Third|Second) Reading|Bill is on Third Reading|On (Motion|Adoption|Concurrence|Override)|"
                    r"Conference Committee|Veto", ln, re.I):
            motion = re.sub(r"\s{2,}.*$", "", ln)
    names, cur = {}, None
    for ln in t[tot.end():].split("\n"):
        g = next(((code, int(x.group(1))) for label, code in GROUPS
                  if (x := re.match(rf"\s*{re.escape(label)}\s*-\s*(\d+)\s*$", ln))), None)
        if g:
            cur = g[0]
            names[cur] = []
            continue
        if re.search(r"Indicates Vote Change", ln) or re.fullmatch(r"\s*-\s*COPY\s*-\s*", ln, re.I):  # (a reposted copy's mark)
            cur = None
            continue
        if cur and ln.strip():
            names[cur] += [re.sub(r"\s*\*\s*$|^\*\s*", "", x).strip() for x in re.split(r"\s{2,}", ln.strip()) if x.strip("* ")]
    return {"seq": int(m.group(1)), "day": f"{d.group(3)}-{MON[d.group(1)]:02d}-{int(d.group(2)):02d}",
            "bill": f"{b.group(1)}{b.group(2)}{int(b.group(3))}" if b else "", "motion": motion,
            "totals": dict(zip("YNABE", (int(x) for x in tot.groups()))), "names": names}


_ROLLS = {}


def floor_ready(session):
    """Whether both houses' walks through the session's roll calls have reached their end (fetch.py's state.json)."""
    try:
        st = json.load(open(os.path.join(P.DATA, "votes", str(session), "state.json")))
    except (OSError, ValueError):
        st = {}
    return all(st.get(h, {}).get("ended") for h in ("senate", "house")) or bool(os.environ.get("MD_VOTES_PARTIAL"))


def rolls(session):
    """(house, bill, legislative day) -> the bill's third-reading roll calls that day, in order: the passage votes the bill
    list's history shows. Amendments, motions, quorum calls, the concurrence's "Bill is on Third Reading for Final
    Passage" and conference reports aren't kept: the bill list gives them no day, so they'd have no history line."""
    if session not in _ROLLS:
        out = defaultdict(list)
        # A session's roll calls are used once both houses' walks have reached their end (fetch.py's state.json), so a
        # first copy spread over several runs never shows a session with some of its votes (MD_VOTES_PARTIAL=1: for tests).
        if not floor_ready(session):
            VOTE_STATS[session]["waiting for the first copy"] = 1
            _ROLLS[session] = out
            return out
        for h, house in (("S", "senate"), ("H", "house")):
            try:
                texts = json.load(open(os.path.join(P.DATA, "votes", str(session), f"{house}.json")))
            except (OSError, ValueError):
                continue
            for k, t in texts.items():
                r = parse_roll(t)
                if not r:
                    VOTE_STATS[session]["unreadable"] += 1
                    continue
                if not r["bill"] or not re.match(r"On Third Reading$", r["motion"]):
                    continue
                VOTE_STATS[session]["third readings"] += 1
                out[(h, r["bill"], r["day"])].append(r)
        for v in out.values():
            v.sort(key=lambda r: r["seq"])
        _ROLLS[session] = out
    return _ROLLS[session]


def fold(s):
    """"Peña-Melnyk" -> "pena-melnyk": the committee records write names without accents."""
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower().strip()


def vote_seat(session, h, name, by_data, served):
    """A roll call's name in house h -> the member's seat ("H:44a"), else "H?Name". "Speaker" and "Mr. President" are
    whoever presided that session. A name ties to today's member written the same way in the bill list ("Washington,
    M.", "Lewis Young"), or the one member of the house with that surname (and initial), or (2026-11-22, the committee
    records) the one whose full name ends with it ("White Holland, J.": Jennifer White Holland, "Holland" in the bill
    list; "Pena-Melnyk", unaccented), only when that session's bill list names a sponsor of the house as the PDF does or
    as the bill list names that member (a member who has since left, or changed houses, stays a name)."""
    n = name
    if re.fullmatch(r"(Mr\.|Madam) President|President|Speaker|Madam Speaker|Mr\. Speaker", n):
        n = PRESIDING[h].get(session, PRESIDING_DEFAULT[h])
    key = (h, n) if (h, n) in by_data else None
    if not key:
        last, _, init = n.partition(",")
        last, init = fold(last), init.strip()[:1]
        house = [(k, x) for k, x in by_data.items() if k[0] == h and (not init or x[1][:1] == init)]
        hits = [k for k, x in house if fold(k[1].split(",")[0]) == last]
        if not hits:  # (the full name without "Jr.", "III": "Jennifer White Holland")
            hits = [k for k, x in house if re.sub(r",? (?:Jr\.|Sr\.|II|III|IV)$", "", fold(x[1])).endswith(" " + last)]
        if len(hits) == 1:
            key = hits[0]
    if key:
        known = served.get(h, ())
        if n != name or n in known or n.split(",")[0] in known or key[1] in known or key[1].split(",")[0] in known:
            return by_data[key][0]
    return f"{h}?{name}"


def floor_vote(session, h, p, day, by_data, served):
    """The bill's third-reading vote in house h on that legislative day (the day's last, if it was voted twice):
    [h, "F", None, day, yeas, nays, [[seat, code], ...]] (yes votes left out), the names only when every group's count
    matches the totals line; None when no roll call was read."""
    hits = rolls(session).get((h, p, day))
    if not hits:
        return None
    r = hits[-1]
    T = r["totals"]
    whole = all(len(r["names"].get(c, [])) == T[c] for c in "YNABE")
    VOTE_STATS[session]["matched"] += 1
    if not whole:
        VOTE_STATS[session]["names don't add up"] += 1
        return [h, "F", None, day, T["Y"], T["N"], []]
    listed = [[vote_seat(session, h, x, by_data, served), c] for c in "NABE" for x in r["names"].get(c, [])]
    return [h, "F", None, day, T["Y"], T["N"], listed]


# ---- Committee votes -----------------------------------------------------------------------------------------------
# Each committee's voting record on a bill (data/md/votes/<year>/committee.json, fetch.py's committee_votes(): the PDFs'
# text), a checkmark grid:
#   Budget and Taxation Committee                         Bill/Resolution Number:                  SB 448
#   Voting Record - 2026 Regular Session                  Vote Date:                             2/25/2026
#                                                         Final Action:                               FAV
#             Name            Yea       Nay     Abstain     Excused       Absent     Amendment Numbers, ...
#   Rosapepe, J., Vice                                                                     Other
#                              ✓                                   (a long name's title wraps around its mark)
#   Chair
#   King, N.                   ✓
#   Korman, M., Chair                     Chair generally does not vote
#                    Totals    12          0      0             1           0
COMM_COLS = [("Yea", "Y"), ("Nay", "N"), ("Abstain", "B"), ("Excused", "E"), ("Absent", "A")]
COMM_ACTIONS = {"FAV", "FWA", "UNF"}  # favorable, with amendments, unfavorable (WDR, a sponsor's withdrawal, isn't kept)


def parse_committee(t):
    """One committee voting record's text -> {committee, year, bill ("HB141"), day (ISO), action ("FAV"), totals {code:
    n}, rows [(name "Rosapepe, J.", code)], ok}; ok is False when a row has no mark or two, or a column's marks don't add
    up to its total. A chair who "generally does not vote" is a row with code "B" (present, not voting: a chair left out
    of the list would read as a yes). None when it can't be read."""
    head = re.search(r"^\s*(.+?) Committee\s+Bill/Resolution Number:\s*([HS])([BJ])\s*(\d+)", t, re.M)
    year = re.search(r"Voting Record - (\d{4}) Regular Session", t)
    day = re.search(r"Vote Date:\s*(\d{1,2})/(\d{1,2})/(\d{4})", t)
    act = re.search(r"Final Action:\s*([A-Z]{2,4})\b", t)
    tot = re.search(r"Totals\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)", t)
    lines = t[:tot.start()].split("\n") if tot else []
    hdr = next((i for i, ln in enumerate(lines) if all(re.search(rf"\b{w}\b", ln) for w, _ in COMM_COLS)), None)
    if not (head and year and day and act and tot and hdr is not None):
        return None
    cols = [(lines[hdr].index(w) + len(w) / 2, c) for w, c in COMM_COLS]
    left, right = cols[0][0] - 4, cols[-1][0] + 6
    rows, cur, pending = [], None, []
    for ln in lines[hdr + 1:]:
        marks = [i for i, ch in enumerate(ln) if ch in "✓✔"]
        bare = re.sub(r"[✓✔]", " ", ln)
        name_part = " ".join(x.group(0).strip() for x in re.finditer(r"\S+(?: \S+)*", bare) if x.start() < left)
        note = re.search(r"does not vote", bare)
        if re.match(r"[A-Z][^,]*,\s*[A-Z]\.", name_part):
            cur = {"name": name_part, "marks": pending, "note": False}
            pending = []
            rows.append(cur)
        elif name_part and cur:
            cur["name"] += " " + name_part
        codes = [min(cols, key=lambda c: abs(c[0] - i))[1] for i in marks if left <= i <= right]
        if cur is None:
            pending += codes
        else:
            cur["marks"] += codes
            cur["note"] = cur["note"] or bool(note)
    out, ok = [], not pending
    for r in rows:
        m = re.match(r"([^,]+),\s*([A-Z])\.", r["name"])
        code = r["marks"][0] if len(r["marks"]) == 1 and not r["note"] else "B" if r["note"] and not r["marks"] else None
        if not m or not code:
            ok = False
            continue
        out.append((f"{m.group(1).strip()}, {m.group(2)}.", code))
    totals = dict(zip("YNBEA", (int(x) for x in tot.groups())))
    counted = defaultdict(int)
    for r in rows:
        for c in r["marks"]:
            counted[c] += 1
    ok = ok and all(counted[c] == totals[c] for c in totals)
    return {"committee": head.group(1).strip(), "year": int(year.group(1)), "bill": f"{head.group(2)}{head.group(3)}{int(head.group(4))}",
            "day": f"{day.group(3)}-{int(day.group(1)):02d}-{int(day.group(2)):02d}", "action": act.group(1),
            "totals": totals, "rows": out, "ok": ok}


_COMM = {}


def committee_records(session):
    """Bill ("HB141") -> [(house, parsed record)], once the session's first copy is complete and its floor votes are in."""
    if session not in _COMM:
        out = defaultdict(list)
        folder = os.path.join(P.DATA, "votes", str(session))
        try:
            st = json.load(open(os.path.join(folder, "committee_state.json")))
            texts = json.load(open(os.path.join(folder, "committee.json")))
        except (OSError, ValueError):
            st, texts = {}, {}
        # (And once its floor votes are in: a session with committee votes and no floor votes would look like one whose
        # roll calls went missing, test/data_check.py's "floor votes missing?".)
        if not (st.get("complete") and floor_ready(session)) and not os.environ.get("MD_VOTES_PARTIAL"):
            texts = {}
            if st:
                VOTE_STATS[session]["committee: waiting for the first copy"] = 1
        for k, t in sorted(texts.items()):
            bill, abbr = k.split("_", 1)
            house = "S" if abbr in ("b&t", "eee", "fin", "jpr") else "H"
            r = parse_committee(t)
            if not r:
                VOTE_STATS[session]["committee: unreadable"] += 1
                continue
            # A record filed under another bill or year (the trap list's KS and NY roll calls) isn't this bill's.
            if r["bill"] != bill or r["year"] != session:
                VOTE_STATS[session]["committee: another bill's record"] += 1
                continue
            out[bill].append((house, r))
        _COMM[session] = out
    return _COMM[session]


def committee_votes(session, p, comm_names, by_data, served):
    """The bill's committee votes: [h, "C", committee, day, yes, no, [[seat, code], ...]] (yes votes left out), the
    committee named as the bill list names it ("Budget and Taxation"). An unfavorable report's record counts the votes
    on the motion to kill the bill: its yeas are votes against the bill, its nays for it. Names only when every row has
    one mark, the columns add up to the totals line and no seat is named twice; else the tally alone."""
    out = []
    for h, r in committee_records(session).get(p, []):
        if r["action"] not in COMM_ACTIONS:
            continue
        name = next((c for c in comm_names.get(h, ()) if c.lower() == r["committee"].lower()), r["committee"])
        T = dict(r["totals"])
        flip = r["action"] == "UNF"
        if flip:
            T["Y"], T["N"] = T["N"], T["Y"]
        VOTE_STATS[session]["committee votes"] += 1
        listed = []
        if r["ok"]:
            swap = {"Y": "N", "N": "Y"} if flip else {}
            listed = [[vote_seat(session, h, n, by_data, served), swap.get(c, c)] for n, c in r["rows"]]
            seats_ = [s for s, _ in listed if "?" not in s]
            if len(seats_) != len(set(seats_)):
                VOTE_STATS[session]["committee: a seat named twice"] += 1
                listed = []
            else:
                VOTE_STATS[session]["committee: names"] += 1
                VOTE_STATS[session]["committee: names not tied to a seat"] += sum(1 for s, _ in listed if "?" in s)
        else:
            VOTE_STATS[session]["committee: names don't add up"] += 1
        out.append([h, "C", name, r["day"], T["Y"], T["N"], [x for x in listed if x[1] != "Y"]])
    out.sort(key=lambda v: v[3])
    return out


def load_session(session):
    """Read one session's bills and return (records, bill number -> record index, fetched time, delegation)."""
    people = contacts()
    by_data = {(sid[0], p["dataName"]): p for sid, p in people.items()}
    seat_of = {(sid[0], p["dataName"]): (sid, p["name"]) for sid, p in people.items()}
    # The names each house's sponsors go by in this session's bill list: who served then (for the roll calls' names).
    served = defaultdict(set)
    for b in load(session):
        for s_ in [b.get("SponsorPrimary")] + [x.get("Name") for x in b.get("Sponsors") or []]:
            m_ = re.match(r"(Delegate|Senator) (.+)", text(s_))
            if m_:
                served["H" if m_.group(1) == "Delegate" else "S"].add(m_.group(2))
                served["H" if m_.group(1) == "Delegate" else "S"].add(m_.group(2).split(",")[0])
    parties = _PARTIES.setdefault(session, {})

    def who(name):
        """"Delegate Ebersole" -> "Eric Ebersole"; committees, delegations and "Departmental" as written."""
        m = re.match(r"(Delegate|Senator) (.+)", text(name))
        if not m:
            return text(name)
        h = "H" if m.group(1) == "Delegate" else "S"
        p = by_data.get((h, m.group(2)))
        full = p["name"] if p else m.group(2)
        if p and p.get("party"):
            parties[(h, full)] = p["party"][:1]
        return full

    path = os.path.join(P.DATA, f"legislation_{session}RS.json")
    fetched = datetime.fromtimestamp(os.path.getmtime(path), ZoneInfo(P.TIMEZONE)).strftime("%Y-%m-%d %H:%M")
    texts, recs, index = {}, [], {}
    gov = governor(session)
    for b in sorted(load(session), key=lambda b: (b["BillNumber"][0], int(b["BillNumber"][2:]))):
        p = number(b["BillNumber"])
        origin, other = p[0], "S" if p[0] == "H" else "H"
        status = text(b["Status"])
        day = lambda k: (b.get(k) or "")[:10]
        steps = []
        for h, side in ((origin, "HouseOfOrigin"), (other, "OppositeHouse")):
            comm = text(b.get(f"CommitteePrimary{'Origin' if side == 'HouseOfOrigin' else 'Opposite'}"))
            comm2 = text(b.get(f"CommitteeSecondary{'Origin' if side == 'HouseOfOrigin' else 'Opposite'}"))
            if day(f"FirstReadingDate{side}"):
                steps.append((day(f"FirstReadingDate{side}"), h, f"REFERRED TO {comm.upper()}" if comm else "First reading"))
                if comm2:
                    steps.append((day(f"FirstReadingDate{side}"), h, f"REFERRED TO {comm2.upper()}"))
            if day(f"HearingDateTimePrimary{side}"):
                steps.append((day(f"HearingDateTimePrimary{side}"), h, f"Hearing ({comm})" if comm else "Hearing"))
            rep = text(b.get(f"ReportAction{side}"))
            if day(f"ReportDate{side}") and rep:
                steps.append((day(f"ReportDate{side}"), h, "REPORTED" if rep.startswith("Favorable") else
                              f"{rep} report" if rep == "Unfavorable" else rep))
            if day(f"SecondReadingDate{side}") and not (day(f"ReportDate{side}") and rep):
                steps.append((day(f"SecondReadingDate{side}"), h, "REPORTED"))  # reported, though the list has no date for it
            if day(f"SecondReadingDate{side}"):
                amended = "amend" in text(b.get(f"SecondReadingAction{side}")).lower()
                steps.append((day(f"SecondReadingDate{side}"), h, "Second reading, amended" if amended else "Second reading"))
            third = text(b.get(f"ThirdReadingAction{side}"))
            if day(f"ThirdReadingDate{side}") and third:
                steps.append((day(f"ThirdReadingDate{side}"), h, f"PASSED {HOUSE[h].upper()}" if third.startswith("Passed") else f"Third reading {third.lower()}"))
        steps.sort(key=lambda s: s[0])
        # Each third reading's roll call, matched by house, bill and legislative day.
        # The committees' votes first (fetch.py's committee_votes()), named as this bill's committees are.
        names_ = {origin: [text(b.get("CommitteePrimaryOrigin")), text(b.get("CommitteeSecondaryOrigin"))],
                  other: [text(b.get("CommitteePrimaryOpposite")), text(b.get("CommitteeSecondaryOpposite"))]}
        votes = committee_votes(session, p, names_, seat_of, served)
        for d_, h_, t_ in steps:
            if t_.startswith("PASSED") or t_.startswith("Third reading"):
                v_ = floor_vote(session, h_, p, d_, seat_of, served)
                if v_:
                    votes.append(v_)
                else:
                    VOTE_STATS[session]["no roll call"] += 1
        last_day = max((s[0] for s in steps), default=f"{session}-01-01")
        passed = {s[1] for s in steps if s[2].startswith("PASSED")}
        chapter = re.search(r"CH(\d+)", b.get("ChapterNumber") or "")
        # The governor's actions and overrides, from the bill's page (dated); else from the list's status (undated).
        lines = gov.get(b["BillNumber"], []) if b.get("PassedByMGA") else []
        first = lambda pat: next((l for l in lines if re.search(pat, l[2], re.I)), None)
        vetoed_on = first(r"^Vetoed by the Governor")
        approved_on = first(r"^Approved by the Governor")
        unsigned_on = first(r"^Enacted under")
        # Became law over the veto: "Became law per Maryland Constitution, Chapter 9 of 2025 Special Session" (the list's
        # status still says "Vetoed"), or in the same year's numbering ("Gubernatorial Veto Override - Chapter 879").
        over_on = first(r"^Became law|^Gubernatorial Veto Override") if vetoed_on else None
        gov_steps = []
        for h, d, t in lines:
            if re.match(r"(Veto )?Overridden\b", t):
                t = "Veto overridden " + re.sub(r"^(Veto )?Overridden\s*", "", t)
            elif approved_on and t == approved_on[2]:
                t = "SIGNED"
            elif vetoed_on and t == vetoed_on[2]:
                t = "VETOED"
            elif unsigned_on and t == unsigned_on[2] and "17(c)" in t:
                t = "Became law without the governor's signature"
            gov_steps.append((d, GOV_HOUSE.get(h, "G"), t.strip()))
        signed_day = veto_day = ""
        # A constitutional amendment gets a chapter number but goes to the voters, not the governor.
        amendment = b.get("ConstitutionalAmendment") and not status.startswith("Approved by the Governor")
        if amendment and chapter:
            stage, chapter = 3, None
            steps.append(("", "S", "Goes to the voters at the next general election"))
        elif over_on:
            stage, signed_day, veto_day = 5, over_on[1], vetoed_on[1]
            # A special session's chapters are numbered on their own ("Chapter 9 of 2025 Special Session"): not this one's.
            if "Special Session" in over_on[2]:
                chapter = None
            steps += gov_steps
        elif chapter:
            stage = 5
            law_on = approved_on or unsigned_on
            if law_on:
                signed_day = law_on[1]
                steps += gov_steps
            else:
                steps.append(("", "G", "SIGNED" if status.startswith("Approved") else status))
        # Every bill the General Assembly passes gets a chapter number unless the governor vetoes it; the status of a
        # vetoed bill sometimes shows a later motion instead ("Special Order vote on veto until next session").
        elif vetoed_on:
            stage, veto_day = 6, vetoed_on[1]
            steps += gov_steps
        elif status.startswith("Vetoed") or (b.get("PassedByMGA") and (re.search(r"\bveto", status, re.I) or str(datetime.now().date()) > f"{session}-06-15")):
            stage = 6
            steps.append(("", "G", "VETOED"))
        elif b.get("PassedByMGA"):
            stage = 3
        elif passed:
            stage = 2
        else:
            stage = None
        if "line item veto" in status.lower():
            steps.append((signed_day, "G", "Signed with item vetoes"))
        if stage is not None and stage >= 3:
            passed = {"S", "H"}
        # Where it is: the last house to act, in committee until its committee reports.
        where_h = other if origin in passed and stage == 2 else origin
        side = "OppositeHouse" if where_h == other else "HouseOfOrigin"
        comm = text(b.get(f"CommitteePrimary{'Opposite' if where_h == other else 'Origin'}"))
        rep = text(b.get(f"ReportAction{side}"))
        on_floor = rep.startswith("Favorable") or bool(day(f"SecondReadingDate{side}"))
        if stage is None:
            stage = 1 if on_floor else 0
        committee = comm if not on_floor and comm else None
        refs = [(s[1], s[2][len("REFERRED TO "):].title().replace(" And ", " and ").replace(" Of ", " of ").replace(" The ", " the ")) for s in steps if s[2].startswith("REFERRED TO")]
        refs = [(h, next((x for x in (b.get("CommitteePrimaryOrigin"), b.get("CommitteeSecondaryOrigin"), b.get("CommitteePrimaryOpposite"),
                                     b.get("CommitteeSecondaryOpposite")) if x and x.lower() == c.lower()), c)) for h, c in refs]
        comm_list = sorted({f"{h} · {c}" for h, c in refs})
        first_rep = text(b.get("ReportActionHouseOfOrigin"))
        fate = ("passed" if first_rep.startswith("Favorable") or origin in passed else "defeated" if first_rep == "Unfavorable" else
                "held" if first_rep in ("Withdrawn", "To Interim Study") or "Withdrawn" in status else "none")
        title = text(b["Title"])
        subjects = [s["Name"] for s in b.get("BroadSubjects") or []]
        topics = list(dict.fromkeys([v for s in subjects for k, v in P.SUBJECT_TOPICS.items() if s.startswith(k)]))
        if amendment:
            topics.insert(0, "const")
        topics = list(dict.fromkeys(topics + [k for k in P.TOPIC_WORDS if P.TOPIC_WORDS[k].search(title)]))
        names = [who(s["Name"]) for s in b.get("Sponsors") or []]
        sponsor = who(b.get("SponsorPrimary")) if b.get("SponsorPrimary") else (names[0] if names else "—")
        cos = [n for n in names if n != sponsor]
        if text(b.get("Synopsis")):
            texts[p] = {"statement": text(b["Synopsis"]), "label": "From the Department of Legislative Services' synopsis."}
        if stage == 0 and committee:
            desc = f"In {HOUSE[where_h]} committee"
        elif stage <= 1 and on_floor:
            desc = f"On the {HOUSE[where_h]} floor"
        elif stage >= 2:
            desc = {2: f"Passed the {HOUSE[origin]}", 3: "Passed both houses", 4: "On the governor's desk",
                    5: "Signed into law", 6: "Vetoed"}[stage]
        else:
            desc = status

        def dates(test, mode="last"):
            ds = sorted({s[0] for s in steps if test(s[1], s[2]) and s[0]})
            return {"first": ds[0], "last": ds[-1], "all": ";".join(ds)}[mode] if ds else ""

        # The governor's actions without a page read yet have no dates: they're shown on the last day of the bill's record.
        actions = [[s[0] or last_day, s[2]] for s in steps]
        last_day = max([last_day] + [s[0] for s in steps if s[0]])
        rec = {
            "nums": [p], "base": [p], "prev": earlier(session, b),
            "title": title, "summary": "", "act": "", "lawCode": "", "law": None, "laws": [],
            "comms": comm_list, "topics": topics, "places": [], "narrow": P.narrow_kind(title),
            "commFate": fate, "mainTopic": topics[0] if topics else "", "local": "local" in topics or any("Local" in s for s in subjects),
            "senDeleg": False, "asmDeleg": False, "budget": any("Budget" in s for s in subjects),
            "passedS": "S" in passed, "passedA": "H" in passed, "program": "Administration" in text(b.get("SponsorPrimary")) or None,
            "stage": stage, "passedIn": HOUSE[origin] if stage == 2 else None, "chapter": int(chapter.group(1)) if chapter else None,
            "veto": None, "memo": "", "vetoMemo": veto_message(session, p) if stage == 6 else None,
            "simText": f"{title} {text(b.get('Synopsis'))}",
            "comm": committee if stage == 0 else None,
            "first": min((s[0] for s in steps if s[0]), default=f"{session}-01-01"),
            "last": last_day,
            "cosp": len(cos),
            "keyDates": [
                dates(lambda h, t: t == "REPORTED", "first"),
                dates(lambda h, t: t == "PASSED SENATE", "all"),
                dates(lambda h, t: t == "PASSED HOUSE", "all"),
                "", "", signed_day, veto_day,
            ],
            "votes": votes, "firstComms": [(refs[0][0], refs[0][1], fate == "passed")] if refs else [],
            "vers": [{"p": p, "sponsor": sponsor, "district": 0, "cosponsors": cos, "primes": 1, "cosp": len(cos),
                      "statusDesc": desc, "committee": committee if stage in (0, 2) else None, "actions": actions}],
        }
        index[p] = len(recs)
        recs.append(rec)
    json.dump(texts, open(os.path.join(P.DATA, f"texts_{session}.json"), "w"), ensure_ascii=False)
    settle(recs, [], (path,))  # bills with no history yet: never dated in the future (states/undated.py)
    return recs, index, fetched, {"SENATE": [], "ASSEMBLY": []}


def agendas(session):
    """Bills on upcoming committee hearings and voting sessions (states/md/fetch.py's agendas(), from the hearing
    schedule): bill -> [["House Ways and Means", "2026-02-17T13:00:00"], ...], meetings from today on."""
    try:
        got = json.load(open(os.path.join(P.DATA, f"agendas_{session}.json")))
    except (OSError, ValueError):
        return {}
    today = datetime.now(ZoneInfo(P.TIMEZONE)).date().isoformat()
    out = {k: [e for e in v if e[1][:10] >= today] for k, v in got.items()}
    return {k: v for k, v in out.items() if v}


def parties(session, recs):
    return {k: v for k, v in _PARTIES.get(session, {}).items() if v in ("D", "R")}


def seats(session):
    return {p["id"]: sid for sid, p in contacts().items()}
