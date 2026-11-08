"""Maine's bills from LegiScan's files (downloaded by legiscan.py into data/me/legiscan/<session_id>/; the Legislature's
own site, legislature.maine.gov, asks automated readers not to), in the shape build_data.py reads. The shared reading is
states/legiscan_convert.py; this file says what's particular to Maine.

- What's shown: the Legislative Documents (LDs) of each two-year Legislature's regular sessions: bills ("An Act to ..."),
  resolves ("Resolve, ...": laws with a limited purpose or time, numbered separately as "Resolves 2025, chapter 12") and
  the resolutions proposing amendments to the Constitution of Maine (tagged "const"). Joint orders, joint resolutions and
  other papers with no LD number (LegiScan's HP/SP records) are left out.
- Numbers: each LD starts as a House or a Senate paper (HP 870, SP 11), but people know it by its LD number. The page
  reads a bill's house from its number's first letter, so records are numbered with the house in front: "HLD1328" is LD
  1328, a House paper; the summary says "LD 1328 (House Paper 870)".
- Committees are joint: one Joint Standing Committee of senators and representatives hears each bill. The house of
  origin refers it ("The Bill was REFERRED to the Committee on TRANSPORTATION.") and the other house concurs ("...in
  concurrence"; not a second referral). The committee's lines have no house (LegiScan's "J"): "Work Session Held",
  "Voted: OTP-AM", "Reported Out: OTP-AM" (Ought to Pass as Amended; OTP, ONTP Ought Not to Pass, LTW Leave to Withdraw;
  "OTP-AM/ONTP" is a divided report, majority first). The report goes back to the house that referred the bill. A
  unanimous ONTP report kills the bill unless a member asks to take it up (Joint Rule 310.3: "Placed in Legislative Files
  (DEAD)"). Divided reports go to the floor, where each house votes on which report to accept.
- The floor: each house passes a bill twice. First "PASSED TO BE ENGROSSED" (approving its text, after the second
  reading), in each house, agreeing on amendments ("RECEDED and CONCURRED", "INSISTED", a Committee of Conference); then
  "PASSED TO BE ENACTED" (resolves and constitutional resolutions: "FINALLY PASSED"), the House first, then the Senate.
  A house passing it to be engrossed is a passage here (with the house's amendments, so "passed both houses" never comes
  from the engrossments alone), and enactment by both houses is "passed both houses". Bills that cost money are usually
  placed on the Senate's Special Appropriations Table pending enactment, and those not funded when the session ends die
  there, after the House enacted them.
- The governor: the history doesn't record a bill reaching the governor or being signed, nor its chapter number. A bill
  enacted by both houses whose chaptered text LegiScan holds (texts[].type "Chaptered") became law: it's marked as law on
  the day of its final enactment. Vetoes appear when the house of origin reconsiders the bill ("This Bill, having been
  returned by the Governor, together with objections ..."), with the vote ("...the veto was sustained", or "...become a
  law notwithstanding the objections of the Governor"). "HELD BY THE GOVERNOR" marks bills enacted at the end of a session
  that the governor keeps until the Legislature meets again (she then has three days); a bill still held when the
  Legislature ends for good, with no chaptered text, is a pocket veto. Bills "RECALLED From Governor's Desk" by joint order
  are back with the Legislature until enacted again.
- Votes: each roll call has its own history line ("ROLL CALL NO. 424 (Yeas 75 - Nays 65 - Absent 9 - Excused 2)",
  "Roll Call Ordered Roll Call Number 457 Yeas 19 - Nays 14 ..."), right after the motion it decides; it's a step of kind
  "rollcall" with that tally, so each roll call file finds its line. Only roll calls on the bill's own questions count as
  members' votes on it (accepting an Ought to Pass report, engrossment, enactment, final passage, overriding a veto); a
  "yea" to accept an Ought Not to Pass report or to indefinitely postpone is a vote against the bill, and those are left
  out. Committee votes aren't in the data.
- No summaries: LegiScan's description is the title. "What it does" isn't shown.
"""
import json, os, re, sys

HERE = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from states import legiscan_convert as L
from states.me import profile as P

HOUSE = L.HOUSE
AMENDMENT = re.compile(r"^RESOLUTION,?\s+Proposing an? Amendments? to the Constitution of Maine", re.I)
# The joint standing committees of 2023-26 (and the joint select Housing committee of 2023-24).
KNOWN = ["Agriculture, Conservation and Forestry", "Appropriations and Financial Affairs", "Criminal Justice and Public Safety",
         "Education and Cultural Affairs", "Energy, Utilities and Technology", "Environment and Natural Resources",
         "Health and Human Services", "Health Coverage, Insurance and Financial Services", "Housing and Economic Development",
         "Inland Fisheries and Wildlife", "Innovation, Development, Economic Advancement and Business", "Judiciary",
         "Labor and Housing", "Marine Resources", "State and Local Government", "Taxation", "Transportation",
         "Veterans and Legal Affairs", "Labor", "Housing"]
SMALL = {"and", "of", "the", "on", "for", "to", "in"}
# Words that make a line a motion about the step rather than the step itself.
NOT_STEP = re.compile(r"reconsider|pending|\btabled?\b|failed|\bmoved\b|whereby|\bto recede\b|\bmotion\b.*\bto (?:accept|adopt|recede|insist)", re.I)
ENGROSS = re.compile(r"\b(?:PASSED|PASSAGE) TO (?:BE )?ENGROSSED\b", re.I)
ENACT = re.compile(r"^(?:Subsequently,?\s*)?PASSAGE TO BE ENACTED\b|\bPASSED TO (?:BE )?ENACTED\b|\bFINALLY PASSED\b|"
                   r"\b(?:INSISTED on|RECEDED and CONCURRED (?:to|with)) (?:PASSAGE TO BE ENACTED|FINAL PASSAGE)\b", re.I)
FAIL_ENACT = re.compile(r"\bFAILED (?:PASSAGE TO BE ENACTED|FINAL PASSAGE|ENACTMENT|PASSAGE TO BE ENGROSSED)\b", re.I)
VETO_RETURN = re.compile(r"having been returned by the Governor,? together with (?:its|his|her)?\s*objections", re.I)
OVERRIDE = re.compile(r"vote of the (?:House|Senate) that the (?:Bill|Resolve) become (?:a )?law", re.I)
ROLL = re.compile(r"ROLL CALL (?:NO\.|Number)\s*(\d+)V?\b", re.I)


def comm(c):
    """"HEALTH AND HUMAN SERVICES" -> "Health and Human Services"; "Joint Select Committee on Housing" -> "Housing"."""
    c = L.text(c).strip(" .,")
    c = re.sub(r"^(?:the )?(?:Joint (?:Standing |Select )?)?Committee on\s+", "", c, flags=re.I)
    c = re.sub(r"\s+(?:pursuant|and ordered|in concurrence|in non-concurrence).*$", "", c, flags=re.I).strip(" .,")
    words = c.lower().split()
    c = " ".join(w if i and w in SMALL else w[:1].upper() + w[1:] for i, w in enumerate(words))
    return c.replace(" And ", " and ")


def referral(t):
    """The committee a line refers the bill to, or None."""
    if re.search(r"without REFERENCE|INSISTED on REFERENCE|RECEDED and CONCURRED (?:to|with) (?:REFERENCE|the Bill REFERRED)|"
                 r"\bmoved\b|FAILED|pending|Report of the Committee on .* was READ and REJECTED", t, re.I) and not re.match(r"Committee on .+ suggested", t):
        return None
    m = re.search(r"(?:REFERRED|REFERENCE|COMMITTED)\s+to (?:the )?(?:Joint (?:Standing |Select )?)?Comm?itt?ee on ([A-Z][A-Z ,&'-]+[A-Z])(?![a-z])", t) or \
        re.search(r"(?:REFERRED|REFERENCE|COMMITTED)\s+to (?:the )?(?:Joint (?:Standing |Select )?)?Comm?itt?ee on ([A-Z][\w ,&'-]+?)(?:,|\s+pursuant|\s+and ordered|\s+in concurrence|\.|$)", t)
    if not m:
        return None
    c = comm(re.sub(r"\s+(?:PREVAILED|ORDERED|IN CONCURRENCE|IN NON-CONCURRENCE)\b.*$", "", m.group(1)))
    # A name cut at its first comma ("Energy, Utilities and Technology" written mixed-case): the full name.
    return c if c in KNOWN else next((k for k in KNOWN if k.startswith(c + ",") and len(c) >= 6), c)


def report_words(code):
    return {"OTP": "Ought to Pass", "OTP-AM": "Ought to Pass as Amended", "ONTP": "Ought Not to Pass", "LTW": "Leave to Withdraw",
            "OTP-ND": "Ought to Pass in a New Draft", "OTP-ND-NT": "Ought to Pass in a New Draft under a new title"}.get(code, code)


def tally(t):
    m = re.search(r"Yeas\s*(\d+)\s*-\s*Nays\s*(\d+)", t, re.I) or re.search(r"(\d+) having voted in the affirmative and (\d+) in the negative", t, re.I) \
        or re.search(r"objections of the Governor\?\"?\s*(\d+) and (\d+)", t, re.I)
    return (int(m.group(1)), int(m.group(2))) if m else None


def decode_bill(b, kind):
    """Every history line of one LD -> its steps, reading each line with the ones around it."""
    hist = b.get("history") or []
    origin = b.get("body") if b.get("body") in HOUSE else "H"
    lines = [((a.get("date") or "")[:10], a.get("chamber") if a.get("chamber") in HOUSE else "", L.text(a.get("action"))) for a in hist]
    # A law: LegiScan holds its chaptered text, or (for bills enacted on a session's last day, whose chaptered texts
    # LegiScan's 2023-24 copy lacks) LegiScan's status is "Passed".
    chaptered = any((t.get("type") or "") == "Chaptered" for t in b.get("texts") or []) or int(b.get("status") or 0) == 4
    out = [[] for _ in lines]
    comm_house, last_report = origin, None
    enacted = {"S": False, "H": False}
    engrossed = {"S": False, "H": False}  # a standing engrossment in each house
    completes = []   # indexes of lines where both houses' enactments stood
    enact_lines = []
    held_at = None
    for i, (d, h, t) in enumerate(lines):
        nxt = [x for x in lines[i + 1:i + 3] if x[0] == d and x[1] == h]
        steps = out[i]
        if not h:
            # The joint committee's lines.
            m = re.match(r"Reported Out:\s*(.+)$", t, re.I)
            if m:
                codes = [c.strip().upper() for c in m.group(1).split("/")]
                main = codes[0]
                last_report = main
                words = report_words(main) + (f" (divided report; the minority: {', '.join(report_words(c) for c in codes[1:])})" if len(codes) > 1 else "")
                if main.startswith("OTP"):
                    steps.append((comm_house, "report", f"Committee report: {words}", {}))
                elif main == "ONTP":
                    steps.append((comm_house, "commfail", f"Committee report: {words}", {}))
                elif main == "LTW":
                    steps.append((comm_house, "held", f"Committee report: {words}", {}))
                else:
                    steps.append((comm_house, None, t, {}))
            elif re.match(r"HELD BY (?:THE )?GOVERNOR", t, re.I):
                held_at = i
                steps.append(("G", "sent", "Held by the governor until the Legislature meets again", {}))
            else:
                steps.append((comm_house, None, t, {}))
            continue
        if re.match(r"HELD BY (?:THE )?GOVERNOR", t, re.I):
            held_at = i
            steps.append(("G", "sent", "Held by the governor until the Legislature meets again", {}))
            continue
        if re.search(r"RECALLED From Governor", t, re.I):
            held_at = None
            enacted = {"S": False, "H": False}
            engrossed = {"S": False, "H": False}
            steps.append(("G", "unsent", "Recalled from the governor's desk by the Legislature", {}))
            continue
        # Vetoes: the house of origin reconsiders the returned bill; the Senate's line carries its vote too.
        if VETO_RETURN.search(t):
            held_at = None
            steps.append(("G", "veto", "Vetoed by the governor", {}))
            tl = tally(t)
            if tl:
                steps.append((h, "rollcall", t, {"tally": tl}))
            if OVERRIDE.search(t) and not re.search(r"that the (?:Bill|Resolve) not become", t, re.I):
                steps.append((h, "override", f"The {HOUSE[h]} overrode the veto", {}))
            continue
        m = ROLL.search(t)
        if m or re.match(r"Roll Call Ordered", t):
            tl = tally(t)
            steps.append((h, "rollcall", t, {"tally": tl} if tl else {}))
            if OVERRIDE.search(t) and not re.search(r"that the (?:Bill|Resolve) not become", t, re.I):
                steps.append((h, "override", f"The {HOUSE[h]} overrode the veto", {}))
            continue
        c = referral(t)
        if c:
            concur = re.search(r"in concurrence", t, re.I) or any(re.match(r"In concurrence", x[2], re.I) for x in nxt)
            if concur and h != comm_house:
                steps.append((h, None, t, {}))  # agreeing to the other house's referral
            else:
                comm_house = h
                steps.append((h, "refer", f"REFERRED TO {c.upper()}", {"comm": c}))
            continue
        if FAIL_ENACT.search(t) and not re.search(r"RECONSIDER", t, re.I):
            if re.search(r"ENACT|FINAL", t, re.I):
                enacted[h] = False
            steps.append((h, "fail", t, {}))
            continue
        if re.search(r"RECONSIDER\w* (?:its |their )?actions? whereby the (?:The )?(?:Bill|Resolve|RESOLUTION) was\s+PASSED TO BE (?:ENGROSSED|ENACTED)|"
                     r"RECONSIDERED whereby the (?:Bill|Resolve|RESOLUTION) was\s+(?:FINALLY )?PASSED|RECONSIDERED\s+PASSAGE TO (?:BE )?(?:ENGROSSED|ENACTED)", t, re.I) \
                and not re.search(r"\bmoved\b", t):
            if re.search(r"ENACTED|FINALLY", t, re.I):
                enacted[h] = False
            else:
                engrossed[h] = False
            steps.append((h, "reconsider", t, {}))
            continue
        if re.search(r"INDEFINITELY POSTPONED", t) and re.search(r"Bill|Resolve|RESOLUTION|papers", t) and \
                not re.search(r"Amendment \"?[A-Z]\"? \([HS]-\d+\) (?:was )?INDEFINITELY|INDEFINITELY POSTPONED (?:Committee|House|Senate) Amendment", t) and not NOT_STEP.search(t):
            steps.append((h, "fail", t, {}))
            continue
        if ENACT.search(t) and not NOT_STEP.search(t):
            what = "FINALLY PASSED" if re.search(r"FINAL", t, re.I) else "PASSED TO BE ENACTED"
            steps.append((h, "pass", f"{what} BY THE {HOUSE[h].upper()}", {"amended": True}))
            enacted[h] = True
            enact_lines.append(i)
            if enacted["S"] and enacted["H"]:
                completes.append(i)
            continue
        if ENGROSS.search(t) and not NOT_STEP.search(t):
            # A house's engrossment counts once: receding and concurring or insisting on its own passage later only
            # settles the text (the line is kept as written).
            if engrossed[h]:
                steps.append((h, None, t, {}))
            else:
                am = " AS AMENDED" if re.search(r"AS AMENDED", t, re.I) else ""
                steps.append((h, "pass", f"PASSED TO BE ENGROSSED BY THE {HOUSE[h].upper()}{am}", {"amended": True}))
                engrossed[h] = True
            continue
        # Accepting a committee report on the floor.
        if re.search(r"ACCEPT", t, re.I) and re.search(r"Report", t, re.I) and not NOT_STEP.search(t):
            if re.search(r"Ought Not to Pass|ONTP", t, re.I):
                steps.append((h, "fail", t, {}))
            elif re.search(r"Ought to Pass|OTP", t, re.I) or (re.match(r"(?:The Committee )?Report (?:was )?READ and ACCEPTED", t, re.I)
                                                             and last_report and last_report.startswith("OTP")):
                steps.append((h, "floor", t, {}))
            elif re.match(r"(?:The Committee )?Report (?:was )?READ and ACCEPTED", t, re.I) and last_report == "ONTP":
                steps.append((h, "fail", t, {}))
            else:
                steps.append((h, None, t, {}))
            continue
        if re.match(r"CONSENT CALENDAR - FIRST DAY", t, re.I):
            steps.append((h, "floor", t, {}))
            continue
        steps.append((h, None, t, {}))
    # Passed both houses: the last line where both houses' enactments stood, unless a recall or a failed vote undid it
    # and the bill wasn't enacted again.
    if completes and enacted["S"] and enacted["H"]:
        i = completes[-1]
        out[i].append((lines[i][1], "enrolled", "ENACTED BY BOTH HOUSES", {}))
    if enact_lines and kind == "bill" and enacted["S"] and enacted["H"]:
        i = enact_lines[-1]
        if chaptered:
            out[i].append(("G", "chapter", "Became law (the date the governor signed it isn't in the record)", {"num": ""}))
        elif held_at is not None and b.get("session", {}).get("sine_die") and held_at == max(j for j, x in enumerate(lines) if x[2]):
            # Held by the governor when the Legislature ended for good, and not a law: a pocket veto.
            out[held_at].append(("G", "veto", "Not signed: the Legislature ended while the governor held it (a pocket veto)", {}))
    return out


class Maine(L.Rules):
    data_dir = P.DATA
    lower = "H"
    gates = set()
    vote_kinds = ("rollcall",)

    def __init__(self):
        super().__init__()
        self._lines = {}

    def include(self, b):
        n = b.get("bill_number") or ""
        if not n.startswith("LD") or b.get("bill_type") != "B":
            return None
        return "amendment" if AMENDMENT.search(L.text(b.get("title"))) else "bill"

    def number(self, b):
        """"LD1328" from a House paper -> "HLD1328"."""
        return (b.get("body") if b.get("body") in HOUSE else "H") + L.number(b["bill_number"])

    def decode_line(self, i, action, chamber, b, kind):
        return self.decode_line_all(b, kind)[i]

    def decode_line_all(self, b, kind=None):
        key = b.get("bill_id")
        if key not in self._lines:
            self._lines[key] = decode_bill(b, kind or self.include(b))
        return self._lines[key]

    def committee_vote(self, desc):
        return None

    def floor_vote(self, desc):
        """The bill's own questions, where "yea" is for the bill: accepting an Ought to Pass report ("Acc Maj Otp As
        Amended Rep RC #424"), engrossment, enactment, final passage, adoption, a veto override ("Reconsideration - Veto").
        Not accepting an Ought Not to Pass report or indefinite postponement (a "yea" is against the bill), amendments,
        tabling, receding (to either house's position), insisting, referral."""
        d = re.sub(r"\s*RC\s*#?\d+\s*$", "", (desc or "").strip(), flags=re.I).lower()
        if re.search(r"reconsideration\s*-\s*veto|veto override", d):
            return True
        if re.search(r"not to pass|ontp|indef|table|^adopt (?!ion)|amendment \(|\b[hsc]a[hs]-|\b[hs][a-z]h-|\b[hs][a-z]s-|suspend|reconsider|"
                     r"insist|commit|reference|recede|motion|further|divided|rule", d):
            return False
        return bool(re.search(r"ought to pass|\botp\b|otp-am|enact|final passage|passage|pass to be|^adoption|^acc(?:ept)? (?:maj|min)", d))

    def title(self, b):
        t = L.text(b.get("title"))
        if AMENDMENT.search(t):
            what = re.sub(r"^RESOLUTION,?\s+Proposing an? Amendments? to the Constitution of Maine,?\s*", "", t, flags=re.I)
            what = re.sub(r"^(?:to |To )", "", what)
            return "Constitutional amendment: " + (what[:1].lower() + what[1:] if what else t)
        t = re.sub(r"^An Act [Tt]o\s+", "", t)
        return t[:1].upper() + t[1:]

    def summary(self, b):
        n = L.number(b["bill_number"])[2:]
        paper = next((m.group(1) for x in b.get("texts") or [] for m in [re.search(r"paper=([HS]P)0*(\d+)", x.get("state_link") or "")] if m), None)
        pnum = next((m.group(2) for x in b.get("texts") or [] for m in [re.search(r"paper=([HS]P)0*(\d+)", x.get("state_link") or "")] if m), None)
        where = f" ({'House' if paper == 'HP' else 'Senate'} Paper {pnum})" if paper else ""
        return f"LD {n}{where}: {L.text(b.get('title'))}"

    def what(self, b):
        return None

    def topics(self, b, comms, title):
        return ([P.COMMITTEE_TOPICS[c] for c in comms if c in P.COMMITTEE_TOPICS] +
                [k for k, rx in P.TOPIC_WORDS.items() if rx.search(L.text(b.get("title")))])

    def narrow(self, b, title):
        return P.narrow_kind(L.text(b.get("title")))

    def link(self, b):
        return b.get("state_link") or b.get("url") or ""

    def seat(self, session, pid, house, name):
        return _seats(session).get(pid)

    def earlier_key(self, b, kind):
        t = re.sub(r"^(?:An Act|Resolve,?|RESOLUTION,?)\s+(?:to\s+)?", "", L.text(b.get("title")), flags=re.I).lower()
        return t if len(t.split()) >= 5 else None


RULES = Maine()
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


def load_session(session):
    """(records, number -> record index, fetched time, delegation), with earlier sessions' versions linked."""
    if session not in _LOADED:
        recs, index, fetched = L.load_session(RULES, session)
        # A bill both houses passed to be engrossed but only one enacted is "passed one house": the house that passed it
        # last (the shared reading picks by day, and both often act the same day).
        last_pass = {}
        for b in L.bills(RULES.session_folders()[session]):
            if RULES.include(b):
                st = [x for line in RULES.decode_line_all(b) for x in line if x[1] == "pass"]
                if st:
                    last_pass[RULES.number(b)] = st[-1][0]
        for r in recs:
            if r["stage"] == 2 and r["passedS"] and r["passedA"] and last_pass.get(r["nums"][0]) in HOUSE:
                r["passedIn"] = HOUSE[last_pass[r["nums"][0]]]
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
    for s in sessions():
        recs = load_session(s)[0]
        from collections import Counter
        print(s, len(recs), "records;", sorted(Counter(r["stage"] for r in recs if r["_kind"] == "bill").items()),
              "amendments", sorted(Counter(r["stage"] for r in recs if r["_kind"] == "amendment").items()), RULES.checks.get(s))
