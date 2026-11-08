"""Vermont's bills from LegiScan's files (downloaded by legiscan.py into data/vt/legiscan/<session_id>/; the
Legislature's own site, legislature.vermont.gov, asks automated readers not to), in the shape build_data.py reads. The
shared reading is states/legiscan_convert.py; this file says what's particular to Vermont.

- What's shown: House and Senate bills (H.1, S.1) of each biennium's regular session. Resolutions (joint, concurrent,
  simple) are left out. Constitutional amendments are "Proposals" (Prop. 1 ...), which LegiScan doesn't carry, so none
  are shown.
- The history is the two journals' wording, each line with the house that wrote it. A house's own lines decide; the
  other house's echoes ("Senate Message: Passed in concurrence ...", "House message: Governor approved bill ...") are
  kept as written and change nothing.
  - Referrals: "Read first time and referred to the Committee on X" (House), "Read 1st time & referred to Committee on
    X" (Senate), "Referred to Committee on Appropriations per Rule 35(a)" / "per Senate Rule 31" (bills that cost money or
    raise revenue go on to the money committees), "Committed/Recommitted to Committee on X".
  - Committee reports: the House's "Notice Calendar: Favorable with Amendment" (the committee reported it; it's on the
    notice calendar), "Pending entry on Notice Calendar, referred to Committee on Ways and Means" (reported, and sent on);
    the Senate's "Favorable report with proposal of amendment by Committee on X", "Reported without recommendation".
    Committees never vote bills down: a bill a committee doesn't take up just dies with the biennium. Committee bills
    ("Committee bill read first time and placed on Notice Calendar") start on the floor.
  - The floor: "Third Reading ordered" / "3rd reading ordered" is the second-reading vote (step "second": usually the
    decisive one, and where most roll calls are taken); "Read third time and passed" / "Read 3rd time & passed" the
    passage. The second house "passed in concurrence" (passed it unchanged) or "passed in concurrence with proposal of
    amendment" (changed it): then the first house "concurred in" the proposal (passed both houses), concurred "with
    further amendment" (back to the other house), or refused and asked for a Committee of Conference, whose report both
    houses have to adopt.
  - Roll calls: the Senate writes them on the question's own line ("3rd reading ordered on roll call ... Yeas = 19,
    Nays = 10"); the House on a line of their own, "Roll Call Results Passed -- ... Yeas = 98, Nays = 46" before the line
    that says what passed ("Third Reading ordered"), or "Which was agreed to on a Roll Call ..." after it.
    `classify()` reads a bill's lines together and puts each roll call's tally on its question, so the shared code ties
    the right roll call to it; roll calls on amendments and motions aren't the bill's.
  - The governor: "Delivered to the Governor on May 30, 2025", "Signed by Governor on June 5, 2025", "Allowed to become
    law without the signature of the Governor", "Vetoed by the Governor" / "Governor vetoed bill", "Veto of the Governor
    overriden by a vote of Yeas = 107, Nays = 42" (each house). The Act number isn't in the history: it's the name of
    the "As Enacted" text ("ACT044 As Enacted.pdf"; municipal acts, charters mostly, are "ACTM003"), added as the
    bill's last step. Acts are numbered through the biennium with no gaps (2023-24: 1-185 and M-1 to M-28; 2025-26:
    1-179 and M-1 to M-12).
- No summaries: LegiScan's description is the official title ("An act relating to ..."), and the Legislative Counsel's
  "statement of purpose" is only in the bill texts (PDFs on the Legislature's site), so there's no "What it does".
"""
import json, os, re, sys

HERE = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from states import legiscan_convert as L
from states.vt import profile as P

HOUSE = L.HOUSE
MESSAGE = re.compile(r"^(?:Senate|House) [Mm]essage\b")
TALLY = re.compile(r"Yeas\s*[=-]?\s*(\d+),?\s*Nays\s*[=-]?\s*(\d+)", re.I)
VOTE_KINDS = ("pass", "fail", "concur", "ccr", "override", "second")
# Lines between a question and its roll call that say nothing about the bill.
ASIDE = re.compile(r"^(?:Rep\.|Reps\.|Senator|Sen\.) .*(?:demanded yeas and nays|explained (?:his |her |their )?vote)|^Roll Call, [Rr]equested by [^,]*$|"
                   r"^Senator .* explained vote", re.I)


def comm(c):
    """"Appropriations per Senate Rule 31" -> "Appropriations"; "Judiciary on motion of Senator Hashim" -> "Judiciary"."""
    c = L.text(c)
    c = re.split(r"\s+(?:per |on motion of |with (?:the )?report |under suspension |, which was )|,\s*which was |,\s*on motion ", c)[0]
    c = re.sub(r"\s+", " ", c).strip(" .,;")
    return c


def tally_in(a):
    m = TALLY.search(a)
    return (int(m.group(1)), int(m.group(2))) if m else None


MONTHS = {m: i + 1 for i, m in enumerate("January February March April May June July August September October November December".split())}


def text_date(a):
    """"Signed by Governor on June 13, 2024" -> "2024-06-13". The governor's lines are filed under the journal day the
    house learned of it, often weeks earlier or later (H.10 of 2023-24: delivered June 7 and signed June 13, both filed
    under May 10)."""
    m = re.search(r"\b(January|February|March|April|May|June|July|August|September|October|November|December) ?(\d{1,2}),\s*(\d{4})", a)
    if m:
        return f"{m.group(3)}-{MONTHS[m.group(1)]:02d}-{int(m.group(2)):02d}"
    m = re.search(r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b", a)
    return f"{m.group(3)}-{int(m.group(1)):02d}-{int(m.group(2)):02d}" if m else None


def decode(a, h, b, kind):
    """One history line -> [(house, kind, text shown, extra)], without its neighbors (classify() adds roll calls)."""
    low = a.lower()
    when = {"date": text_date(a)} if re.match(r"(?:Bill )?Delivered to|Signed by|Allowed to become law|Vetoed by|Governor vetoed", a) and text_date(a) else {}
    if MESSAGE.match(a) or re.match(r"As passed by Senate and House|House proposal of amendment(?:; text)?$|Title (?:amended|revised)", a):
        return [(h, None, a, {})]
    # The governor.
    if re.match(r"(?:Bill )?Delivered to (?:the )?Governor\b", a):
        return [(h, "sent", "DELIVERED TO GOVERNOR", when)]
    if re.match(r"Signed by (?:the )?Governor\b", a):
        return [("G", "signed", "Signed by the governor", when)]
    if re.match(r"Allowed to become law without (?:the )?signature", a, re.I):
        return [("G", "nosign", "Became law without the governor's signature", when)]
    if re.match(r"(?:Vetoed by (?:the )?Governor|Governor vetoed bill)\b", a):
        return [("G", "veto", "Vetoed by the governor", when)]
    if re.match(r"Veto of (?:the )?Governor overrid+en", a):
        return [(h, "override", f"{HOUSE[h]} overrode the veto" if h in HOUSE else a, {"tally": tally_in(a)})]
    # Referrals and committee reports.
    m = re.match(r"Pending entry on Notice Calendar, referred to (?:the )?Committee on (.+)$", a)
    if m:
        return [(h, "report", "REPORTED", {}), (h, "refer", f"REFERRED TO {comm(m.group(1)).upper()}", {"comm": comm(m.group(1))})]
    m = re.match(r"(?:Committee bill )?[Rr]ead (?:first|1st) time (?:and|&) referred to (?:the )?Committee on (.+)$", a) or \
        re.match(r"(?:Rules suspended (?:&|and) (?:bill )?)?(?:Re-?)?(?:[Rr]eferred|[Cc]ommitted|Recommitted) to (?:the )?Committee on (.+)$", a) or \
        re.match(r"(?:Rep|Sen)\.? .*?moved (?:to (?:re)?commit (?:the )?bill|that the bill be (?:re)?committed) to (?:the )?Committee on (.+?),? which was agreed to", a)
    if m and not re.search(r"not agreed to|disagreed", a):
        c = comm(m.group(1))
        return [(h, "refer", f"REFERRED TO {c.upper()}", {"comm": c})]
    if re.match(r"Notice Calendar:\s*(?:Favorable|Unfavorable|Without recommendation)", a, re.I) or \
            re.match(r"(?:Favorable report|Reported favorably|Reported without recommendation|Read 2nd time, reported (?:favorably|without))", a):
        m = re.search(r"Committee on (.+?)(?: with (?:proposal|recommendation).*)?$", a)
        return [(h, "report", a, {"comm": comm(m.group(1))} if m else {})]
    if re.match(r"Committee bill read (?:the )?first time|Committee [Bb]ill for Second Reading|(?:New|Unfinished) Business/Committee Bill", a):
        return [(h, "floor", a, {})]
    # The floor.
    if re.match(r"(?:Third Reading ordered|3rd reading ordered)", a, re.I):
        return [(h, "second", a, {"tally": tally_in(a)})]
    if re.match(r"Read (?:3rd|third) time (?:&|and) (?:passed|adopted)\b|Passed(?: in concurrence)?(?: with proposal(?:\(s\))? of amendment)?(?: on (?:roll call|division)\b.*)?$", a):
        amended = bool(re.search(r"in concurrence with proposal", a))
        m = re.search(r"on division (\d+)-(\d+)", a)
        t = tally_in(a) or ((int(m.group(1)), int(m.group(2))) if m else None)
        return [(h, "pass", f"PASSED {HOUSE[h].upper()}" + (" WITH CHANGES" if amended else ""), {"amended": amended, "tally": t})]
    if re.search(r"proposal of amendment\b.*\bconcurred in\b", a) and not re.search(r"not concurred|refuse|concurred in with|further", low) \
            and re.match(r"(?:House|Senate) proposal of amendment", a):
        return [(h, "concur", a, {"tally": tally_in(a)})]
    if re.match(r"Committee of Conference report adopted", a):
        return [(h, "ccr", a, {"tally": tally_in(a)})]
    return [(h, None, a, {})]


def act_of(b):
    """("44", False) for "ACT044 As Enacted.pdf", ("M-3", True) for a municipal act's "ACTM003", or None."""
    for t in b.get("texts") or []:
        m = re.search(r"/ACTS/ACT(M?)0*(\d+)/", t.get("state_link") or "")
        if t.get("type") == "Chaptered" and m:
            return (f"M-{m.group(2)}" if m.group(1) else m.group(2)), bool(m.group(1))
    return None


_CLASSIFIED = {}


def classify(b):
    """Every history line's steps, with each roll call's tally on the question it decided."""
    key = b.get("bill_id")
    if key in _CLASSIFIED:
        return _CLASSIFIED[key]
    hist = b.get("history") or []
    lines = [(L.text(a.get("action")), a.get("chamber") if a.get("chamber") in HOUSE else "") for a in hist]
    out = [decode(a, h, b, None) for a, h in lines]
    # Year slips in the governor's lines (H.289 of 2023-24: "Vetoed by the Governor on May 23, 2023", filed in May 2024
    # and messaged as May 23, 2024): a date well before the journal day it's filed under takes that day's year.
    for i, steps in enumerate(out):
        filed = (hist[i].get("date") or "")[:10]
        for st in steps:
            d = st[3].get("date")
            if d and filed and d < filed and (int(filed[:4]) - int(d[:4])) * 365 > 45 and d[:4] < filed[:4]:
                st[3]["date"] = filed[:4] + d[4:]

    def vote_step(i):
        return next((s for s in out[i] if s[1] in VOTE_KINDS), None)
    for i, (a, h) in enumerate(lines):
        t = tally_in(a)
        if not t or vote_step(i) or MESSAGE.match(a):
            continue
        # A result line: "Roll Call Results ..." comes before the line saying what passed (the House); "Which was agreed
        # to on a Roll Call ..." and the Senate's "Roll Call, requested by Senator X, Passed -- ..." after the question.
        before = bool(re.match(r"Roll Call Results|Division results", a))
        order = range(i + 1, min(len(lines), i + 3)) if before else range(i - 1, max(-1, i - 4), -1)
        for j in order:
            if lines[j][1] != h or ASIDE.search(lines[j][0]):
                continue
            s = vote_step(j)
            if s and not s[3].get("tally"):
                s[3]["tally"] = t
            if s and s[3]["tally"] == t:
                VOTE_LINES.add(vote_key(a))
            break
    for i, (a, h) in enumerate(lines):
        s = vote_step(i)
        if s and s[3].get("tally") and re.search(r"roll call|overrid", a, re.I):
            VOTE_LINES.add(vote_key(a))
    # The Act number, after the last line.
    act = act_of(b)
    if act and out:
        num, municipal = act
        steps = [x for o in out for x in o]
        vetoed = any(x[1] == "veto" for x in steps)
        overridden = {x[0] for x in steps if x[1] == "override"} >= {"S", "H"}
        if vetoed and not overridden:
            # An Act number after a veto that stands in this history: the record stops early (H.890 of 2023-24, Act 185:
            # its history ends with the Senate sustaining a veto; the Legislature's status page says the governor approved
            # it June 28, 2024). The Act number decides: it's a law, dated by the enacted text.
            when = next((t.get("date") for t in b.get("texts") or [] if t.get("type") == "Chaptered"), None)
            out[-1] = out[-1] + [("G", "signed", f"Became Act {num} (the history LegiScan has stops before the governor's final action)",
                                  {"date": when} if when else {})]
        out[-1] = out[-1] + [("G", "chapter", f"Became Act {num}" + (" (a municipal act)" if municipal else ""),
                              {"num": num, "private": municipal})]
    _CLASSIFIED[key] = out
    return out


# The roll calls on a bill's own question (passage, third reading, concurrence, conference report, override), from
# classify(), by their result and tally ("Passed -- Needed 69 of 138 to Pass -- Yeas = 87, Nays = 51"): LegiScan's roll
# call carries a history line as its description, but not always the same one ("Roll Call Results Passed ..." for the
# history's "Which was agreed to on a Roll Call Passed ...", H.141 of 2025-26).
VOTE_LINES = set()


def vote_key(a):
    m = re.search(r"(?:Passed|Failed)?\s*--\s*Needed.*$|Yeas\s*=.*$", a or "")
    return re.sub(r"\s+", " ", m.group(0)).strip() if m else a


def short_title(b):
    """"An act relating to the role and structure of the Agency of Education" -> "The role and structure of the Agency
    of Education"."""
    t = L.text(b.get("title"))
    t = re.sub(r"^An act (?:relating to|to)\s+", "", t, flags=re.I).strip().rstrip(".")
    return t[:1].upper() + t[1:]


class Vermont(L.Rules):
    data_dir = P.DATA
    lower = "H"
    gates = set()
    vote_kinds = ("second",)

    def include(self, b):
        n = b.get("bill_number") or ""
        return "bill" if re.match(r"[HS]0*\d+$", n) and b.get("bill_type") == "B" else None

    def decode(self, action, chamber, b, kind):
        return decode(action, chamber, b, kind)

    def decode_line(self, i, action, chamber, b, kind):
        steps = classify(b)
        return steps[i] if i < len(steps) else decode(action, chamber, b, kind)

    def committee_vote(self, desc):
        return None  # LegiScan has no committee roll calls for Vermont

    def floor_vote(self, desc):
        return vote_key(L.text(desc)) in VOTE_LINES

    def title(self, b):
        return short_title(b)

    def summary(self, b):
        return L.text(b.get("title"))

    def what(self, b):
        return None

    def topics(self, b, comms, title):
        return ([P.COMMITTEE_TOPICS[c] for c in comms if c in P.COMMITTEE_TOPICS] +
                [k for k, rx in P.TOPIC_WORDS.items() if rx.search(title)])

    def narrow(self, b, title):
        act = act_of(b)
        if act and act[1]:
            return "place"
        return P.narrow_kind(L.text(b.get("title")))

    def link(self, b):
        return b.get("state_link") or b.get("url") or ""

    def seat(self, session, pid, house, name):
        return _seats(session).get(pid)

    def earlier_key(self, b, kind):
        t = re.sub(r"^an act relating to\s+", "", L.text(b.get("title")).lower())
        return t if len(t.split()) >= 3 and not P._PLACE.search(t) and not re.search(r"miscellaneous|appropriations|fees|technical corrections", t) else None


RULES = Vermont()
_SEATS, _LOADED = {}, {}


def _seats(session):
    """people_id -> seat for the members holding a seat now (contacts_<session>.json, built by contacts.py), in the
    current session only: earlier sessions' seats were held by others, so their voters keep their names."""
    if session not in _SEATS:
        out = {}
        if session == max(sessions() or [session]):
            c = L.read_json(os.path.join(P.DATA, f"contacts_{session}.json"), {}) or {}
            out = {int(p["id"]): sid for sid, p in (c.get("people") or {}).items() if str(p.get("id", "")).isdigit()}
        _SEATS[session] = out
    return _SEATS[session]


def sessions():
    return list(L.folders(P.DATA))


BUDGET = re.compile(r"\bappropriations for the support of government\b|\bmaking (?:supplemental |additional )?appropriations\b|\bcapital construction\b|\bTransportation Program\b", re.I)


def load_session(session):
    """(records, number -> record index, fetched time, delegation), with earlier sessions' versions linked."""
    if session not in _LOADED:
        recs, index, fetched = L.load_session(RULES, session)
        for r in recs:
            r["budget"] = bool(BUDGET.search(r["summary"]))
        older = {s: load_session(s)[0] for s in sessions() if session - 4 <= s < session}
        L.link_earlier(RULES, session, recs, older)
        _LOADED[session] = (recs, index, fetched)
    recs, index, fetched = _LOADED[session]
    return recs, index, fetched, {"SENATE": [], "ASSEMBLY": []}


def agendas(session):
    return {}


def parties(session, recs):
    return RULES.parties_.get(session, {})


if __name__ == "__main__":
    import collections
    for s in sessions():
        recs = load_session(s)[0]
        print(s, len(recs), "records;", sorted(collections.Counter(r["stage"] for r in recs).items()), RULES.checks.get(s))
