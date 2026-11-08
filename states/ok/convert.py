"""Oklahoma's bills from LegiScan's files (downloaded by legiscan.py into data/ok/legiscan/<session_id>/; the
Legislature's own site, oklegislature.gov, asks automated readers not to), in the shape build_data.py reads. The shared
reading is states/legiscan_convert.py; this file says what's particular to Oklahoma.

- Sessions: each Legislature runs two years from an odd year (the 60th is 2025-26), meeting each year from the first
  Monday in February to the last Friday in May at the latest; bills carry over from the first year to the second with
  the same numbers. LegiScan files each year as a session of its own, but the even year's ("2026 Regular Session")
  holds every bill of the Legislature, both years', so `session_folders()` reads that folder as the session starting the
  odd year before (the odd year's folder, a subset, is left alone; while only it exists, it's used).
- What's shown: House and Senate Bills, and the joint resolutions that propose amendments to the Oklahoma Constitution
  ("Constitutional amendment; ...", "Oklahoma Constitution; ... ballot title; filing."). Other joint resolutions
  (approving or disapproving agencies' rules, which do go to the governor; applications to Congress for a convention;
  statutory referendums) and other resolutions are left out.
- History lines: "Second Reading referred to Judiciary and Public Safety Oversight" then "Referred to Civil Judiciary"
  (since 2025 a House bill goes to a policy committee working under an oversight committee: the policy committee is
  where it is, and its "Policy recommendation to the Judiciary and Public Safety Oversight committee; Do Pass Civil
  Judiciary" sends it to the oversight committee, whose "CR; Do Pass ... Committee" reports it; the Appropriations and
  Budget Committee works the same way through its subcommittees: "Recommendation to the full committee; Do Pass ...
  Subcommittee"). A referral the bill was then withdrawn from ("Second Reading referred to Rules", "Withdrawn from Rules
  Committee", "Referred to ...": most House bills of 2025-26 were parked in Rules at first) or that's followed directly
  by another (the oversight committee, then its policy committee) isn't where the bill went. Senate: "Second Reading
  referred to Judiciary Committee then to Appropriations Committee", "Reported Do Pass as amended Judiciary committee;
  CR filed", "Placed on General Order", "Measure passed: Ayes: 38 Nays: 5" (House: "Third Reading, Measure passed: ...").
  "Measure passed and Emergency failed" passes the bill without its emergency clause. A house's second vote on a bill it
  already passed (the House's "Fourth Reading", the Senate's "Measure passed" after "HAs adopted" or "CCR adopted") is
  its agreement to the other house's changes or to the conference report. "Motion to reconsider adopted" and "Third
  Reading, advancement rescinded" undo the house's passage, but only when the vote just before was the passage (not the
  emergency clause or a special election). "Referred for enrollment" and "Enrolled, signed, to ..." mean passed both
  houses. Then "Sent to Governor", "Approved by Governor 05/05/2025", "Becomes law without Governor's signature",
  "Vetoed 05/22/2025", "Pocket veto 06/15/2025" (after the session the governor has 15 days: a bill not signed doesn't
  become law), "Veto overridden: Ayes: 91 Nays: 1" in each house, "Line item vetoed" (appropriations; the rest is law).
- Laws: no chapter numbers in LegiScan's data (Oklahoma numbers them "Chapter 1, O.S.L. 2025" in the session laws).
- Constitutional amendments pass a majority of each house's members and go to the voters ("Filed with Secretary of
  State"), never the governor.
- "What it does": nothing. LegiScan's description for Oklahoma is the official title, and the bill texts and summaries
  are on oklegislature.gov, which asks automated readers not to read it.
- Shell bills: each year leaders file hundreds of placeholders whose whole title is a subject and a named act with an
  effective date ("Schools; Education Reform Act of 2026; effective date."), kept to be rewritten late in the session.
  Those never moved past a committee are marked `shell`, as Illinois's are.
"""
import json, os, re, sys

HERE = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from states import legiscan_convert as L
from states.ok import profile as P

HOUSE = L.HOUSE
# "Constitutional amendment; ...", "Oklahoma Constitution; ...", "Joint resolution; Oklahoma Constitution; ...",
# "Constitution; Vote of the People; ...". Not "Joint Resolution; Article V United States Constitution; Congress; term
# limits; application" (an application to Congress) or "calling a Constitutional Convention".
AMENDMENT = re.compile(r"^(?:Joint resolution;\s*)?(?:Constitutional amendment|(?:the )?Oklahoma Constitution|Constitution)\b"
                       r"|\bconstitutional amendment\b", re.I)
NOT_AMENDMENT = re.compile(r"United States Constitution|calling a Constitutional Convention|convention of the states", re.I)
SHELL = re.compile(r"^[^;]+;\s*[^;]*\bAct of 20\d\d\b[^;]*(?:[;.]\s*(?:effective date|noncodification|codification|emergency)\.?)*\s*$", re.I)
STOCK = re.compile(r"^(?:providing (?:for )?(?:an )?)?(?:effective dates?|emergency|declaring an emergency|(?:providing for )?(?:non)?codification|"
                   r"distribution|directing distribution|ballot title|filing|directing filing|providing ballot title)\.?$", re.I)
PASS = re.compile(r"^(?:(Third|Fourth) Reading, )?Measure(?: and Emergency)? passed\b", re.I)
FAIL = re.compile(r"^(?:(?:Third|Fourth) Reading, )?Measure failed\b", re.I)
VOTE_LINE = re.compile(r"(?:passed|failed)(?:, to \w+)?: Ayes", re.I)
UNDO_PASS = re.compile(r"^(?:Third Reading(?:,| and)? (?:advancement )?rescinded|Third Reading rescinded|Motion to Rescind vote on Third Reading|"
                       r"Motion to reconsider(?: vote)? adopted)", re.I)
UNDO_REPASS = re.compile(r"^(?:Fourth Reading\b.*rescinded|Motion to reconsider(?: vote)? adopted|Motion to Rescind)", re.I)


def comm(c):
    """A committee's name as the history or a roll call writes it -> one spelling, or None for a step that isn't a
    committee (the pension actuary's review). "Judiciary Committee then to Appropriations Committee" -> "Judiciary";
    "Appr/Sub-Health and Human Services" -> "Appropriations Subcommittee on Health and Human Services"; "Health & Human
    Services" -> "Health and Human Services"."""
    c = L.text(c)
    if re.search(r"actuar", c, re.I):
        return None
    c = re.split(r"\s+(?:Committee\s+)?then to\s+", c, flags=re.I)[0]
    c = re.sub(r"^(?:the )?(?:Senate|House)\s+", "", c)
    m = re.match(r"Appr/Sub-\s*(.+)$", c)
    if m:
        c = "Appropriations Subcommittee on " + m.group(1)
    c = re.sub(r"\s+[Cc]ommittee$", "", c).strip(" .,;")
    c = c.replace("&", " and ")
    c = re.sub(r"^Committee on Appropriations and Budget$", "Joint Committee on Appropriations and Budget", c)
    c = re.sub(r"^Veteran and Military", "Veterans and Military", c)
    c = re.sub(r"\s+", " ", c).strip()
    return c or None


def parent(sub):
    """The committee a House policy committee or subcommittee reports to, from the history's own words."""
    if sub.startswith("Appropriations and Budget"):
        return "Appropriations and Budget"
    return None


MODS = re.compile(r"^[,;]?\s*(?:as amended by committee substitute|amended by committee substitute|as amended|amended|"
                  r"strike the title|strike the enacting clause|and)\s*", re.I)


def after_mods(rest):
    rest = rest.strip()
    while True:
        new = MODS.sub("", rest, count=1)
        if new == rest:
            return rest.strip(" ,;")
        rest = new


class Oklahoma(L.Rules):
    data_dir = P.DATA
    lower = "H"
    gates = set()   # Floor votes are scheduled by each house's majority floor leader, not a committee.
    comm_vote_days = 4  # a committee's report ("CR filed") is entered the day after its vote, or after a weekend

    def __init__(self):
        super().__init__()
        self._pos = {}
        self.raw_titles = {}

    def session_folders(self):
        """{first (odd) year of the Legislature: folder}: the even year's LegiScan session holds the whole Legislature."""
        out = {}
        for year, folder in L.folders(self.data_dir).items():
            odd = P.session_of(year)
            if odd not in out or year > odd:  # the even year's folder wins over the odd year's subset
                out[odd] = folder
        return dict(sorted(out.items()))

    def include(self, b):
        n = b.get("bill_number") or ""
        m = re.match(r"([A-Z]+)0*(\d+)$", n)
        if not m:
            return None
        if m.group(1) in ("HB", "SB"):
            return "bill"
        t = L.text(b.get("title"))
        if m.group(1) in ("HJR", "SJR") and AMENDMENT.search(t) and not NOT_AMENDMENT.search(t):
            return "amendment"
        return None

    def _at(self, b, a):
        """Where this line is in the bill's history (decode() is called once per line, in order)."""
        hist = b.get("history") or []
        key = b.get("bill_id")
        i = self._pos.get(key, 0)
        if i >= len(hist) or L.text(hist[i].get("action")) != a:
            i = next((j for j, x in enumerate(hist) if L.text(x.get("action")) == a), 0)
        self._pos[key] = i + 1
        return i

    def decode(self, a, h, b, kind):
        hist = b.get("history") or []
        i = self._at(b, a)
        prev, nxt = hist[:i], hist[i + 1:]
        origin = L.number(b.get("bill_number") or "X")[0]
        low = a.lower()
        R = lambda c: (h, "refer", f"REFERRED TO {c.upper()}", {"comm": c})

        # The governor.
        if re.match(r"approved by governor", low):
            return [("G", "signed", "Signed by the governor", {})]
        if re.match(r"becomes law without governor", low):
            return [("G", "nosign", "Became law without the governor's signature", {})]
        if re.match(r"pocket veto", low):
            return [("G", "veto", "Pocket veto: the governor didn't sign it within 15 days after the session ended", {})]
        if re.match(r"vetoed\b", low):
            return [("G", "veto", "Vetoed by the governor", {})]
        if re.match(r"veto overridden", low):
            return [(h, "override", a, {})]
        if re.match(r"sent to governor", low):
            return [(h, "sent", "DELIVERED TO GOVERNOR", {})]
        if re.match(r"returned by governor", low):
            return [("G", "unsent", a, {})]
        if re.match(r"(?:referred for enrollment|enrolled\b)", low):
            # Unless it was recalled from enrollment and not enrolled again (HB 4248 of 2026: the House's vote agreeing
            # to the Senate's changes was rescinded).
            for x in nxt:
                t = L.text(x.get("action")).lower()
                if re.match(r"(?:referred for enrollment|enrolled\b)", t):
                    break
                if re.match(r"recalled from enrollment", t):
                    return [(h, None, a, {})]
            return [(h, "enrolled", "Passed both houses: referred for enrollment" if low.startswith("referred for enrollment") else a, {})]

        # Referrals.
        m = re.match(r"(?:Second Reading )?(?:re-?)?referred to (.+)$", a, re.I) or re.match(r"Withdrawn from Calendar; referred to (.+)$", a)
        if m and not re.match(r"(?:referred for|.*\b(?:engrossment|enrollment))", low):
            c = comm(m.group(1))
            if not c:
                return [(h, None, a, {})]
            # Superseded: the next step in this house is another referral (the bill was withdrawn from this committee,
            # or this is the oversight committee over the policy committee named next).
            for x in nxt:
                if x.get("chamber") != h:
                    continue
                t = L.text(x.get("action"))
                if re.match(r"(?:Withdrawn from .*Committee|Withdrawn from .*committee)", t) and not re.search(r"Calendar", t):
                    return [(h, None, a, {})]
                if re.match(r"(?:Second Reading )?referred to ", t, re.I) and comm(re.sub(r"^(?:Second Reading )?referred to ", "", t, flags=re.I)):
                    return [(h, None, a, {})]
                if re.match(r"(?:CR;|JCR;|Reported|Policy recommendation|Recommendation|Failed|General Order|Placed on|Direct to|"
                            r"(?:Third|Fourth) Reading|Measure)", t, re.I):
                    break
            return [R(c)]
        if re.match(r"(?:Second Reading, )?direct to (?:Joint )?Calendar", a, re.I):
            return [(h, "floor", a, {})]

        # Committee reports.
        m = re.match(r"Policy recommendation to the (.+?) committee; Do Pass(.*)$", a, re.I)
        if m:
            sub, to = comm(after_mods(m.group(2))), comm(m.group(1))
            return [(h, "report", f"Approved by the {sub} Committee", {"comm": sub}), R(to)]
        m = re.match(r"Recommendation to the full committee; Do Pass(.*)$", a, re.I)
        if m:
            sub = comm(after_mods(m.group(1)))
            out = [(h, "report", f"Approved by the {sub}", {"comm": sub})]
            return out + ([R(parent(sub))] if parent(sub) else [])
        m = re.match(r"J?CR; Do Pass(.*)$", a, re.I)
        if m:
            c = comm(after_mods(m.group(1)))
            return [(h, "report", f"REPORTED by the {c} Committee", {"comm": c})]
        m = re.match(r"Reported Do Pass(.*?)\s+committee; J?CR filed", a, re.I)
        if m:
            c = comm(after_mods(m.group(1)))
            return [(h, "report", f"REPORTED by the {c} Committee", {"comm": c})]
        if re.match(r"(?:Failed in Committee|(?:J?CR; )?Do not pass|Reported Do Not Pass)", a, re.I):
            return [(h, "commfail", a, {})]

        # The floor.
        if re.match(r"(?:Placed on General Order|General Order(?:,|$)|Advanced to Third Reading|Considered$)", a):
            return [(h, "floor", a, {})]
        if UNDO_PASS.match(a):
            last = next((L.text(x.get("action")) for x in reversed(prev) if x.get("chamber") == h and VOTE_LINE.search(L.text(x.get("action")))), "")
            return [(h, "reconsider" if PASS.match(last) else None, a, {})]
        m = PASS.match(a)
        if m:
            # Has this house already passed it (and not undone that)? Then this vote agrees to the other house's
            # changes, or to the conference report.
            standing, since = False, []
            for x in prev:
                t = L.text(x.get("action"))
                if x.get("chamber") == h and PASS.match(t):
                    standing, since = True, []
                elif x.get("chamber") == h and UNDO_PASS.match(t):
                    last = next((L.text(y.get("action")) for y in reversed(prev[:prev.index(x)]) if y.get("chamber") == h and VOTE_LINE.search(L.text(y.get("action")))), "")
                    if PASS.match(last):
                        standing = False
                else:
                    since.append(x)
            if m.group(1) == "Fourth" or standing:
                # Undone later (and not passed again): "Fourth Reading and signing rescinded".
                for x in nxt:
                    t = L.text(x.get("action"))
                    if x.get("chamber") == h and PASS.match(t):
                        break
                    if x.get("chamber") == h and UNDO_REPASS.match(t):
                        return [(h, None, a, {})]
                ccr = any(re.search(r"\bCCR adopted", L.text(x.get("action"))) and x.get("chamber") == h for x in since)
                return [(h, "ccr" if ccr else "concur", ("Agreed to the conference report and passed it again" if ccr else
                                                         "Agreed to the other house's changes and passed it again") + f" ({a})", {})]
            return [(h, "pass", f"PASSED {HOUSE[h].upper()}" + (" (emergency clause failed)" if re.search(r"Emergency failed", a, re.I) else ""),
                     {"amended": h != origin})]
        if FAIL.match(a):
            return [(h, "fail", a, {})]
        if re.match(r"Withdrawn by author|Withdrawn\.?$", a):
            return [(h, "withdrawn", "Withdrawn by the author", {})]
        return [(h, None, a, {})]

    def committee_vote(self, desc):
        """"House: Civil Judiciary Committee: DO PASS AS AMENDED BY CS", "Senate: Health & Human Services: DO PASS"
        (2023-24's Senate votes don't say "Committee"). A few name no committee ("Senate:  Committee: DO PASS"): left out."""
        m = re.match(r"(?:House|Senate):\s*([^:]*):\s*DO (?:NOT )?PASS", desc or "", re.I)
        if not m or L.text(m.group(1)) in ("", "Committee"):
            return None
        return comm(m.group(1))

    def floor_vote(self, desc):
        return bool(re.match(r"(?:House|Senate):\s*(?:THIRD READING|FOURTH READING|VETO OVERRIDE)", desc or "", re.I))

    def title(self, b):
        raw = L.text(b.get("title"))
        self.raw_titles[L.number(b.get("bill_number") or "")] = raw
        t = re.sub(r"\.\s+(?=(?:Effective date|Emergency)\b)", "; ", raw)
        parts = [p.strip() for p in re.split(r";\s*", t.rstrip(". ")) if p.strip()]
        keep = [p for p in parts if not STOCK.match(p)] or parts[:1]
        if self.include(b) == "amendment":
            keep = [p for p in keep if not re.match(r"^(?:Joint resolution|Constitutional amendment|(?:the )?Oklahoma Constitution|Constitution|Vote of the people)\.?$", p, re.I)]
            what = "; ".join(keep) or t
            return "Constitutional amendment: " + what[:1].upper() + what[1:]
        out = "; ".join(keep)
        if len(out) > 240:
            out = out[:240].rsplit(" ", 1)[0] + "…"
        return out[:1].upper() + out[1:]

    def summary(self, b):
        return ""

    def what(self, b):
        return None

    def topics(self, b, comms, title):
        subject = L.text(b.get("title")).split(";")[0].strip().rstrip(".").lower()
        return ([P.SUBJECT_TOPICS[subject]] if subject in P.SUBJECT_TOPICS else []) + \
            [P.COMMITTEE_TOPICS[c] for c in comms if c in P.COMMITTEE_TOPICS] + \
            [k for k, rx in P.TOPIC_WORDS.items() if rx.search(L.text(b.get("title")))]

    def narrow(self, b, title):
        return P.narrow_kind(L.text(b.get("title")))

    def link(self, b):
        return (b.get("state_link") or b.get("url") or "").replace("http://", "https://")

    def seat(self, session, pid, house, name):
        return _seats(session).get(pid)

    def earlier_key(self, b, kind):
        t = L.text(b.get("title"))
        if SHELL.match(t):
            return None
        parts = [p.strip().lower() for p in re.split(r"[;.]\s*", t) if p.strip() and not STOCK.match(p.strip())]
        # Without the subject that opens every title ("Motor vehicles; ..."), which would make unrelated bills look alike.
        key = re.sub(r"\b20\d\d\b", "", "; ".join(parts[1:])).strip()
        return key if len(key.split()) >= 4 else None


RULES = Oklahoma()
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
    return list(RULES.session_folders())


def load_session(session):
    """(records, number -> record index, fetched time, delegation), with earlier sessions' versions linked."""
    if session not in _LOADED:
        recs, index, fetched = L.load_session(RULES, session)
        for r in recs:
            raw = RULES.raw_titles.get(r["nums"][0], "")
            r["shell"] = bool(SHELL.match(raw)) and r["stage"] <= 1
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
        print(s, len(recs), "records;", RULES.checks.get(s))
