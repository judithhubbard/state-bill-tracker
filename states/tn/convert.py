"""Tennessee's bills from LegiScan's files (downloaded by legiscan.py into data/tn/legiscan/<session_id>/; the General
Assembly's own site, capitol.tn.gov, asks automated readers not to), in the shape build_data.py reads. The shared reading
is states/legiscan_convert.py; this file says what's particular to Tennessee.

- What's shown: House and Senate Bills of each General Assembly's regular sessions (numbers under 6000: extraordinary
  sessions' bills are numbered from 6001 and 7001 in the same files, and left out), and the joint resolutions that
  propose amendments to the Tennessee Constitution ("A RESOLUTION to propose an amendment to Article II, Section 28 of
  the Constitution of Tennessee ..."). Other resolutions are left out.
- Companions: every bill is filed in both houses with the same text, a House Bill and a Senate Bill (LegiScan's sasts
  "Crossfiled"). Each moves through its own house's committees; when one passes its house, the other house substitutes
  it for its own companion ("Senate substituted House Bill for companion Senate Bill.", "Subst. for comp. HB.") and votes
  on it. The two are one record here, as New Jersey's and New York's identical bills are; the stage is the furthest the
  bill got, and each number keeps its own history.
- History lines: House "Ref. to Judiciary Committee - Health Committee" (the first named is where it goes now), "Assigned
  to s/c Civil Justice Subcommittee" (House committees work through subcommittees), "Rec for pass if am by s/c ref. to
  Judiciary Committee" (the subcommittee approved it), "Rec. for pass; ref to Calendar & Rules Committee" (the committee
  approved it; Calendar and Rules schedules floor votes), "H. Placed on Regular Calendar", "Passed H., as am., Ayes 80,
  Nays 10, PNV 2"; Senate "Passed on Second Consideration, refer to Senate Judiciary Committee", "Recommended for passage
  with amendment/s, refer to Senate Calendar Committee", "Placed on Senate Consent Calendar", "Passed Senate, Ayes 30,
  Nays 0". Set aside without a vote: "Taken off notice" (the sponsor), "Placed behind the budget" (bills that cost money
  wait in the House Finance, Ways and Means Subcommittee until the budget passes), "Assigned to General Subcommittee of
  Senate X Committee", "Deferred to Summer Study", "Lay on the Table". Then "Enrolled and ready for signatures" (passed
  both houses), "Signed by Senate Speaker", "Signed by H. Speaker", "Transmitted to Governor for action.", "Signed by
  Governor.", "Returned by Governor without signature." (a law: the governor doesn't sign it within 10 days), "Vetoed by
  Governor.", "Pub. Ch. 78" (a public chapter, the law's number; "Pr. Ch." a private act, for one city or county) and on
  the companion "Comp. became Pub. Ch. 78".
- Constitutional amendments pass a majority of each house's members in one General Assembly and two-thirds in the next,
  then the voters at the next governor's election; never the governor. The first house "Adopted" it; the second
  "Concurred" (without an amendment number).
- "What it does": the bill summary the General Assembly writes ("As introduced, ..." / "As enacted, ..."), which LegiScan
  carries as each bill's description.
"""
import importlib, json, os, re, sys

HERE = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from states import legiscan_convert as L
from states.tn import profile as P

HOUSE = L.HOUSE
AMENDMENT = re.compile(r"^A RESOLUTION (?:to |proposing |to propose )?(?:propose )?(?:an )?amend\w*\b.{0,200}?Constitution of (?:the State of )?Tennessee", re.I)


def comm(c):
    """A committee's name as the history writes it -> one spelling: "Senate Finance, Ways & Means Committee w/ negative
    recommendation" -> "Finance, Ways and Means"; "S. Cal Comm" -> "Calendar"; "Energy, Ag., and Nat. Resources" ->
    "Energy, Agriculture and Natural Resources"."""
    c = L.text(c)
    # "Health Committee -- Government Operations", "Health Committee--Finance": the first named, where it goes now.
    c = re.split(r"\s*--\s*|\s+-\s+|(?<=Committee)-\s*", c)[0]
    c = re.sub(r"\s+(?:as am\.?\s+)?(?:w/|with\b).*$|\s+for Review$|\s+of \d+\w* Extraordinary Session.*$|\s+(?:on |for )?\d+/\d+.*$|"
               r"\s+\d+ ayes.*$|(?<=Subcommittee)[HS]B\d+$", "", c, flags=re.I)
    c = re.sub(r"^(?:the )?(?:Senate|S\.|House|H\.)\s+", "", c)
    c = re.sub(r"[;`'\s]+$", "", c)
    c = re.sub(r"\s+Comm(?:ittee|itee)?\.?$", "", c).strip(" .,")
    c = c.replace("&", " and ").replace("Gov't", "Government").replace("Govenrment", "Government")
    c = re.sub(r"\s+", " ", c)
    c = re.sub(r"^Finance\. Ways", "Finance, Ways", c)
    c = re.sub(r"Ways and Mea?s?ns?$", "Ways and Means", c)
    c = re.sub(r"^F, W and Means$", "Finance, Ways and Means", c)
    c = re.sub(r"\bNR$", "Natural Resources", c)
    c = re.sub(r"\bF,\s*W\s*and\s*M\b|\bFW\s*and\s*M\b", "Finance, Ways and Means", c)
    c = re.sub(r"Finance, Ways,? and Means", "Finance, Ways and Means", c)
    c = re.sub(r"\bAg\.,?", "Agriculture,", c).replace("Agriculture,, ", "Agriculture, ").replace("Nat.", "Natural")
    c = re.sub(r"Energy, Agriculture,? (?:and )?Natural Resources", "Energy, Agriculture and Natural Resources", c)
    c = re.sub(r"^Cal$", "Calendar", c).replace("Tenncare", "TennCare")
    # The Senate's Finance, Ways and Means Committee works through its Revenue Subcommittee.
    c = re.sub(r"^(?:Finance, Ways and Means (?:Committee )?)?Revenue Subcommittee$", "Finance, Ways and Means Revenue Subcommittee", c)
    c = re.sub(r"\s+", " ", c).strip()
    return c


def decode(a, h, b, kind):
    """One history line -> [(house, kind, text shown, extra)]."""
    jr = "JR" in b.get("bill_number", "")
    low = a.lower()
    R = lambda c: (h, "refer", f"REFERRED TO {comm(c).upper()}", {"comm": comm(c)})
    # The governor and the law's number (lines with no house).
    m = re.match(r"(Comp\. became )?(Pub|Pr)\. Ch\. (\d+)", a)
    if m:
        what = "Public Chapter" if m.group(2) == "Pub" else "Private Chapter"
        return [("G", "chapter", f"{'The companion bill became' if m.group(1) else 'Became'} {what} {m.group(3)}",
                 {"num": m.group(3), "private": m.group(2) == "Pr", "companion": bool(m.group(1))})]
    if re.match(r"signed by governor", low):
        return [("G", "signed", "Signed by the governor", {})]
    if re.match(r"returned by governor without signature", low):
        return [("G", "nosign", "Became law without the governor's signature", {})]
    if re.match(r"vetoed by governor", low):
        return [("G", "veto", "Vetoed by the governor", {})]
    if re.search(r"veto", low) and re.search(r"overrid", low) and not re.search(r"fail|not ", low):
        return [(h, "override", a, {})]
    if re.match(r"governor returned|senate requested governor to return|house requested governor to return", low):
        return [("G" if low.startswith("governor") else h, "unsent", a, {})]
    if re.match(r"Comp\. SB subst\.|Companion House Bill substituted", a):
        return [(h, "replaced", f"Replaced by its companion bill ({a})", {})]
    if re.match(r"transmitted to governor", low):
        return [(h, "sent", "DELIVERED TO GOVERNOR", {})]
    if re.match(r"(?:re-)?enrolled", low):
        return [(h, "enrolled", "Enrolled: passed both houses", {})]
    # Referrals.
    m = re.match(r"(?:P\dC|P2C|PNC)?,?\s*(?:held on desk[^,]*,\s*)?ref(?:\.|er)? to (.+?)(?:\s+-\s+.*)?$", a, re.I) \
        or re.match(r"Passed on Second Consideration, refer to (.+)$", a) \
        or re.match(r"(?:Re-)?[Rr]efer(?:red)? to (?:the )?(.+?)(?:\s+(?:w/|with) negative recommendation)?$", a)
    if m and not re.search(r"\bfailed\b", low) and not re.search(r"desk|caption", m.group(1), re.I):
        return [R(m.group(1))]
    # A House subcommittee works for its committee: the bill stays "in the Judiciary Committee" (its votes name the
    # subcommittee).
    m = re.match(r"Assigned to s/c (.+)$", a)
    if m:
        return [(h, None, a, {})]
    # Committee reports: a subcommittee's (House) or a committee's, sending it on.
    m = re.match(r"Rec\.?\s*for\s*(?:pass|adopt)\.?.*?\bby s/c\b.*?ref\.? to (.+)$", a, re.I)
    if m:
        return [(h, "subreport", "Approved by the subcommittee", {}), R(m.group(1))]
    m = re.match(r"Rec\.?\s*for\s*(?:pass|adopt)\.?.*?ref\.? to (.+)$", a, re.I) or \
        re.match(r"Recommended for (?:passage|adoption).*?,\s*refer(?: to)? (.+?)(?:,?\s+Ayes?\s*\d.*)?$", a)
    if m:
        return [(h, "report", "REPORTED", {}), R(m.group(1))]
    if re.match(r"(?:Assigned to General Subcommittee|Deferred to Summer Study|Lay on the Table|Tabled|Taken off notice|Placed behind the budget)", a, re.I):
        return [(h, "held", a, {})]
    if re.match(r"Failed (?:in |for lack of |\(no second\) in )", a) and not re.search(r"to pass", low):
        return [(h, "commfail", a, {})]
    if re.match(r"recalled from (?:the )?(?:senate |house )?(?!clerk)", low) and "committee" in low:
        return [(h, "recall", a, {})]
    # The floor.
    if re.match(r"(?:H\. |Senate )?(?:Placed|Reset) on (?:Senate )?(?:Regular|Consent|Message|Local|Final) Calendar", a) or \
            re.match(r"H\. Placed on (?:Regular|Consent|Message) Calendar", a):
        return [(h, "floor", a, {})]
    if re.match(r"Passed (?:H\.|Senate)[ ,]", a):
        return [(h, "pass", f"PASSED {HOUSE[h].upper()}", {"amended": bool(re.search(r"as am", a))})]
    if re.match(r"Failed to pass", a):
        return [(h, "fail", a, {})]
    if jr and re.match(r"(?:Adopted|Concurred)(?: as am\w*\.?)?,", a):
        return [(h, "pass", f"PASSED {HOUSE[h].upper()}", {"amended": bool(re.search(r"as am", a))})]
    if re.match(r"(?:H\. concurred in S\. am|Concurred(?:,| on HA)|Senate concurred)", a) and not re.search(r"refused|non-?concur", low):
        return [(h, "concur", a, {})]
    if re.search(r"(?:conf\.? comm\.?|conference committee) report (?:#\s*\d+ )?adopted|majority ccr \d* ?adopted|adopted majority ccr", low):
        return [(h, "ccr", a, {})]
    if re.match(r"Motion to reconsider (?:passage )?adopted\.?$", a):
        return [(h, "reconsider", a, {})]
    if re.match(r"Withdrawn\.?$", a):
        return [(h, "withdrawn", "Withdrawn by the sponsor", {})]
    return [(h, None, a, {})]


# ---- Committee meetings named in the history (agendas) ----

# A bill set for a committee meeting: the House "Placed on s/c cal Cities & Counties Subcommittee for 3/18/2026",
# "Placed on cal. Judiciary Committee for 3/25/2026", "Action Def. in s/c Health Subcommittee to 3/24/2026", "Action def.
# in Judiciary Committee to 4/02/2025"; the Senate "Placed on Senate Finance, Ways, and Means Committee calendar for
# 4/21/2026", "Action deferred in Senate Judiciary Committee to 3/24/2026", "Rule #83(8) Suspended, to be heard in Senate
# Finance, Ways, and Means Committee for 4/15/2024". Floor calendars ("Placed on Senate Consent Calendar for ...", "H.
# Placed on Regular Calendar for ...") aren't committee meetings.
SET_FOR = [
    ("H", re.compile(r"Placed on s/c cal\.? (.+?) for (\d+/\d+/\d+)$")),
    (None, re.compile(r"Placed on cal\.? (.+?) for (\d+/\d+/\d+)$")),
    ("S", re.compile(r"Placed on Senate (.+?(?:Committee|Subcommittee)) calendar for (\d+/\d+/\d+)$")),
    (None, re.compile(r"Rule #\S+ Suspended, to be heard in (.+?) (?:for|on) (\d+/\d+/\d+)\b")),
    (None, re.compile(r"Action def(?:erred|\.)? in (?:s/c )?(.+?) to (\d+/\d+/\d+)$", re.I)),
]
# Lines that don't change where a bill is set to be heard.
QUIET = re.compile(r"Sponsor|Amendment|Fiscal|Caption|Engrossed|Filed for intro|Comp\. became", re.I)


def set_for(a, h):
    """A history line setting the bill for a committee meeting -> (house, committee as written, "YYYY-MM-DD"), else None."""
    for house, rx in SET_FOR:
        m = rx.match(a.strip())
        if not m:
            continue
        name = m.group(1).strip()
        if re.match(r"(?:Senate |H\. )?(?:Consent|Regular|Message|Local|Final|Appropriations)\b|cal\b", name, re.I) or "Extraordinary" in name:
            return None
        house = "S" if re.match(r"Senate\b", name) else house or ("S" if h == "S" else "H")
        mo, dd, yy = m.group(2).split("/")
        try:
            from datetime import date
            day = date(int(yy) + (2000 if len(yy) == 2 else 0), int(mo), int(dd)).isoformat()
        except ValueError:
            return None
        return house, name, day
    return None


def meeting_name(house, name):
    """The committee as the page names it: "House Judiciary", "House Cities and Counties Subcommittee", "Senate Finance,
    Ways and Means", "Senate Finance, Ways and Means Revenue Subcommittee" (comm()'s spelling, the site's committee names)."""
    name = re.sub(r"^(?:House|Senate)\s+", "", L.text(name))
    # LegiScan's calendar: "Revenue Subcommittee of Finance, Ways & Means".
    name = re.sub(r"^Revenue Subcommittee of Finance, Ways (?:&|and) Means$", "Revenue Subcommittee", name)
    return f"{HOUSE[house]} {comm(name)}"


def history_meetings(b):
    """What the history says of the bill's committee meetings (legiscan_convert's Rules.history_meetings()): (standing,
    dropped, named), the first two [(committee, day)], named {day: {committees}}. A setting
    stands until a later line moves the bill or takes it off the meeting: another setting (a new date, a deferral, the
    next committee), "Taken off notice", "Meeting Canceled", a committee's report or vote, a referral or subcommittee
    assignment elsewhere, a floor calendar. Lines about sponsors and amendments don't. Dropped: settings undone before
    their day, or taken off notice or canceled (LegiScan's calendar keeps those hearings: 218 of 2025-26's)."""
    out, dropped, named = {}, set(), {}

    def undo(x, a):
        for k in out:
            if x.get("date", "") < k[1] or re.match(r"Taken off notice|Meeting Canceled", a, re.I):
                dropped.add(k)
    for x in b.get("history") or []:
        a, h = L.text(x.get("action")), x.get("chamber") or ""
        s = set_for(a, h)
        if s:
            k = (meeting_name(s[0], s[1]), s[2])
            named.setdefault(k[1], set()).add(k[0])
            if k not in out:
                # (a deferral and the placement for the same meeting come as two lines: one setting; settings written
                # the same day all stand: the Senate's Finance, Ways and Means places bills on two days' calendars at
                # once, "for 4/20/2026" and "for 4/21/2026")
                if any(d != x.get("date") for d in out.values()):
                    undo(x, a)
                    out = {}
                out[k] = x.get("date")
            dropped.discard(k)
            continue
        if not a or QUIET.match(a):
            continue
        m = re.match(r"(?:Passed on Second Consideration, |Received from House, |Re-?)?(?:ref(?:er)?\.?(?: to)?|Assigned to s/c) (.+)$", a, re.I)
        if m and out:
            # A referral to the committee it's set for (the Senate sometimes places a bill on a committee's calendar
            # before its referral line) leaves it.
            to = meeting_name("S" if h == "S" else "H", m.group(1))
            if any(n == to for n, _ in out):
                continue
        undo(x, a)
        out = {}
    return list(out), sorted(dropped - set(out)), named


def summary_text(b):
    return L.text(b.get("description"))


def short_title(b):
    """The summary's first clause, without "As introduced," and the list of laws it amends: "As introduced, increases the
    amount of compensation ...; requires ... - Amends TCA Title 29." -> "Increases the amount of compensation ..."."""
    d = re.sub(r"^As (?:introduced|enacted|amended|engrossed|passed[^,]*)[^,]*,\s*", "", summary_text(b))
    d = re.split(r"\s+-\s+(?:Amends|Enacts|Repeals|Amends and)\b", d)[0].strip()
    first = re.split(r";\s+", d)[0].strip().rstrip(".")
    first = re.split(r":\s+(?=[a-z])", first)[0]  # "... for the following offenses: act of terrorism" (a list follows)
    if len(first) > 220:
        first = first[:220].rsplit(" ", 1)[0] + "…"
    first = first[:1].upper() + first[1:]
    if not first:
        m = re.search(r"relative to (.+?)\.?$", L.text(b.get("title")))
        first = (m.group(1)[:1].upper() + m.group(1)[1:]) if m else L.text(b.get("title"))
    return first


class Tennessee(L.Rules):
    data_dir = P.DATA
    timezone = P.TIMEZONE
    lower = "H"
    gates = {"Calendar", "Calendar and Rules"}

    def include(self, b):
        n = b.get("bill_number") or ""
        m = re.match(r"([A-Z]+)0*(\d+)$", n)
        if not m or int(m.group(2)) >= 6000:
            return None  # extraordinary sessions' bills (6001, 7001 ...)
        if m.group(1) in ("HB", "SB"):
            return "bill"
        if m.group(1) in ("HJR", "SJR") and AMENDMENT.search(L.text(b.get("title"))) and not re.search(r"United States", L.text(b.get("title"))[:120]):
            return "amendment"
        return None

    def decode(self, action, chamber, b, kind):
        return decode(action, chamber, b, kind)

    def comm_name(self, name):
        return name

    def history_meetings(self, b):
        return history_meetings(b)

    def agenda_name(self, name):
        m = re.match(r"(House|Senate)\s+(.+)$", name)
        return meeting_name(m.group(1)[0], m.group(2)) if m else name

    def committee_vote(self, desc):
        m = re.match(r"(?:HOUSE |SENATE )?(.+?(?:COMMITTEE|SUBCOMMITTEE)):", desc or "")
        if not m or desc.startswith("FLOOR VOTE"):
            return None
        return comm(m.group(1).title().replace(" And ", " and ").replace(" Of ", " of "))

    def floor_vote(self, desc):
        d = desc or ""
        return d.startswith("FLOOR VOTE") and not re.search(r"AMENDMENT|AMEND#|AMEND\s*#|LAY ON THE TABLE|MOTION TO (?:TABLE|CONSIDER|RE-?REFER|RECALL)|PREVIOUS QUESTION(?! (?:AS AMENDED )?PASSAGE)", d.upper()) \
            or bool(re.search(r"CONCUR|Concur", d))

    def group(self, by_num):
        parent = {n: n for n in by_num}

        def find(n):
            while parent[n] != n:
                parent[n] = parent[parent[n]]
                n = parent[n]
            return n
        for n, b in by_num.items():
            for s in b.get("sasts") or []:
                o = L.number(s.get("sast_bill_number") or "")
                if s.get("type") == "Crossfiled" and o in parent and o[0] != n[0]:
                    parent[find(o)] = find(n)
        # Joint resolutions carry no "Crossfiled" link: a House and a Senate resolution with the same title (HJR 81 and
        # SJR 158 of 2023) are companions too.
        same = {}
        for n, b in by_num.items():
            if "JR" in n:
                same.setdefault(L.text(b.get("title")).lower(), []).append(n)
        for ns in same.values():
            for o in ns[1:]:
                if {x[0] for x in ns} == {"H", "S"}:
                    parent[find(o)] = find(ns[0])
        groups = {}
        for n in by_num:
            groups.setdefault(find(n), []).append(n)
        return list(groups.values())

    def title(self, b):
        t = short_title(b)
        if "JR" in b.get("bill_number", ""):
            # "Proposes an amendment to Article I, Section 35 of the Constitution of Tennessee to expand the rights of crime
            # victims" -> "Constitutional amendment: to expand the rights of crime victims".
            m = re.search(r"Constitution of Tennessee,?\s+(?:to |that |regarding |relative to |establishing |authorizing )(.+)$", t)
            what = m.group(1) if m else re.sub(r"^Proposes (?:an )?(?:amendment|additional language|adding a provision)\s*", "", t)
            what = re.sub(r"^(?:in |to )?Article [IVX]+(?:,? Sections? [\d, and]+)?(?: of the (?:Tennessee )?Constitution(?: of Tennessee)?)?,?\s*(?:to )?", "", what)
            what = re.sub(r"^(?:proposes (?:a )?constitutional amendment (?:to Article [IVX]+, Section \d+ of the Tennessee Constitution )?|"
                          r"of the (?:Tennessee )?Constitution(?: of Tennessee)? |proposes (?:that )?)?(?:to )?", "", what, flags=re.I)
            t = "Constitutional amendment: " + (what[:1].lower() + what[1:] if what else t)
        return t

    def summary(self, b):
        return L.text(b.get("title"))

    def what(self, b):
        d = summary_text(b)
        if len(d.split()) < 6:
            return None
        d = re.sub(r"\s+-\s+((?:Amends|Enacts|Repeals)\b.*)$", r"\n\1", d)
        return d, "From the General Assembly's bill summary (as LegiScan publishes it)."

    def topics(self, b, comms, title):
        subjects = [L.text(s.get("subject_name")) for s in b.get("subjects") or []]
        return ([P.COMMITTEE_TOPICS[c] for c in comms if c in P.COMMITTEE_TOPICS] +
                [P.SUBJECT_TOPICS[s] for s in subjects if s in P.SUBJECT_TOPICS] +
                [k for k, rx in P.TOPIC_WORDS.items() if rx.search(f"{title} {L.text(b.get('title'))}")])

    def narrow(self, b, title):
        cap, desc = L.text(b.get("title")), summary_text(b)
        if re.search(r"Private Acts of|subject to local approval", f"{cap} {desc}", re.I) or \
                any(re.match(r"(?:Comp\. became )?Pr\. Ch\.", L.text(a.get("action"))) for a in b.get("history") or []):
            return "place"
        return P.narrow_kind(f"{title} {cap}")

    def link(self, b):
        return b.get("state_link") or b.get("url") or ""

    def seat(self, session, pid, house, name):
        return _seats(session).get(pid)

    def earlier_key(self, b, kind):
        d = re.sub(r"^As (?:introduced|enacted|amended)[^,]*,\s*", "", summary_text(b)).lower()
        return d if len(d.split()) >= 8 and not re.match(r"subject to local approval", d) else None


RULES = Tennessee()
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
        older = {s: load_session(s)[0] for s in sessions() if session - 4 <= s < session}
        L.link_earlier(RULES, session, recs, older)
        _LOADED[session] = (recs, index, fetched)
    recs, index, fetched = _LOADED[session]
    return recs, index, fetched, {"SENATE": [], "ASSEMBLY": []}


def agendas(session):
    """Bills on upcoming committee meetings, from LegiScan's calendar of each bill (legiscan_convert.agendas())."""
    return L.agendas(RULES, session)


def parties(session, recs):
    return RULES.parties_.get(session, {})


if __name__ == "__main__":
    for s in sessions():
        recs = load_session(s)[0]
        print(s, len(recs), "records;", RULES.checks.get(s))
