"""Montana's bills (downloaded by states/mt/fetch.py from the Legislature's API, api.legmt.gov) in the shape build_data.py
reads. House and Senate bills of each regular session (odd years; a page per two-year Legislature, named by its session's
year). Joint resolutions (HJ, SJ: studies, letters, memorials) are left out; constitutional amendments are bills here ("An
act submitting to the qualified electors of Montana an amendment to Article ..."), with the subject CAP.

Two formats, read into one list of steps (`steps_current()`, `steps_archive()`), then one reading (`record()`):
- 2025 on (the current system): each history step has a status name ("(H) 3rd Reading", "(S) Committee Executive
  Action", "Chapter Number Assigned"), a result ("BILL_PASSED", "BILL_CONCURRED_AS_AMENDED", "BILL_TABLED",
  "MOTION_FAILED", "VETO_OVERRIDDEN"), a timestamp, the committee (standingCommitteeId) and, for a floor vote, its vote id.
  Floor roll calls member by member (votes/<HB1>.json, by legislator id), committee votes member by member
  (committee/<HB1>.json, the "executive actions": do_pass, be_concurred_in ...). A committee report's result is often
  wrong ("BILL_NOT_CONCURRED_AS_AMENDED" after the committee voted "be concurred in as amended", 157 times in 2025):
  committees report only bills they approve, so a report's result is ignored. Co-sponsors from cosponsors.json.
- 2023 (the archive): plain-English actions, newest first ("(S) 3rd Reading Concurred", "(H) Committee Executive
  Action--Bill Passed as Amended", "(H) Veto Overridden by Legislature"), each with a date, the committee and, for votes,
  the tallies (yesVotes, noVotes) but not the members' votes; sponsors by law-entity id.

How a bill moves: introduced and referred to a standing committee, which hears it and votes ("executive action"): do pass
(be concurred in, in the second house), or the bill is tabled, where most bills die. A majority of the house can take a bill
from a committee to the floor ("Take from Committee; Place on 2nd Reading"). On the floor the house debates and votes on
second reading (which can amend, pass, kill it, "indefinitely postpone"), and passes it on third reading. Bills had to pass
their first house by the transmittal deadlines (general bills about day 45, revenue and appropriation bills and referenda
later: "Missed Deadline for General Bill Transmittal" ends a bill). The second house's amendments go back to the first
("Returned to House with Amendments"), which concurs on second and third reading or not; then conference or free
conference committees, whose report both houses adopt. Then "Sent to Enrolling", the presiding officers' signatures,
"Transmitted to Governor"; "Signed by Governor", a veto, a line-item veto, or the governor's proposed amendments
("Returned with Governor's Amendments", which both houses adopt or reject before it goes back to the governor). A bill the
governor neither signs nor vetoes within 10 days becomes law. Vetoes after adjournment are overridden by a poll of the
members by mail (two-thirds of each house). Every law gets a chapter number (1-N each session, none missing in 2023 or 2025),
which decides laws.

No summary of what a bill does exists in the data (the short title is all), so "What it does" isn't shown.
"""
import csv, glob, json, os, re
from collections import Counter
from datetime import date, datetime
from zoneinfo import ZoneInfo

from states.mt import profile as P

HOUSE = {"S": "Senate", "H": "House"}
_CACHE, _PARTIES, _KEYS = {}, {}, {}
KINDS = ("HB", "SB")


def folder(session):
    return os.path.join(P.DATA, str(session))


def sessions():
    out = []
    for f in sorted(os.listdir(P.DATA)) if os.path.isdir(P.DATA) else []:
        if re.fullmatch(r"\d{4}", f) and os.path.isdir(os.path.join(P.DATA, f, "bills")):
            out.append(int(f))
    return out


def archive(session):
    """2023 and before are in the archive's format; 2025 on in the current system's."""
    return session < 2025


def load(session, name, default=None):
    key = (session, name)
    if key not in _CACHE:
        try:
            _CACHE[key] = json.load(open(os.path.join(folder(session), f"{name}.json")))
        except (OSError, ValueError):
            _CACHE[key] = default
    return _CACHE[key]


def bills(session):
    """{"HB1": bill} for the session's House and Senate bills."""
    key = (session, "bills/")
    if key not in _CACHE:
        out = {}
        for path in glob.glob(os.path.join(folder(session), "bills", "*.json")):
            k = os.path.basename(path)[:-5]
            if re.fullmatch(r"(HB|SB)\d+", k):
                try:
                    out[k] = json.load(open(path))
                except ValueError:
                    pass
        _CACHE[key] = out
    return _CACHE[key]


def per_bill(session, kind, k):
    try:
        return json.load(open(os.path.join(folder(session), kind, f"{k}.json")))
    except (OSError, ValueError):
        return []


def text(x):
    return re.sub(r"\s+", " ", (x or "").replace(" ", " ")).strip()


def official(p):
    """"HB10" -> "HB 10", as the Legislature writes it."""
    m = re.fullmatch(r"([A-Z]+)(\d+)", p)
    return f"{m.group(1)} {m.group(2)}" if m else p


def comm_name(n):
    """"(H) State Administration" -> "State Administration"."""
    return re.sub(r"^\([HSJ]\)\s*", "", text(n))


def short_title(b):
    return text(b.get("shortTitle") or (b.get("draft") or {}).get("shortTitle"))


def subjects(b):
    if b.get("draft"):
        return [((s.get("subjectCode") or {}).get("code") or "") for s in b["draft"].get("subjects") or []]
    return [s.get("code") or "" for s in b.get("subjects") or []]


def subject_names(b):
    """"Courts Crimes Criminal Procedure": the subjects' names, without the index's "(see also: ...)"."""
    if b.get("draft"):
        xs = [((x.get("subjectCode") or {}).get("description") or "") for x in b["draft"].get("subjects") or []]
    else:
        xs = [((x.get("subject") or {}).get("description") or "") for x in b.get("subjects") or []]
    return " ".join(re.sub(r"\(.*?\)", "", x).strip() for x in xs)


def is_amendment(b):
    return "CAP" in subjects(b)


def chapter_of(b):
    c = b.get("sessionLawChapterNumber")
    return int(c) if str(c or "").isdigit() else None


# ---------------------------------------------------------------- members

def person(first, last, suffix=None):
    first = re.sub(r'\s+"[^"]*"', "", text(first))  # Bruce "Butch" Gillespie -> Bruce Gillespie
    return text(f"{first} {text(last)}" + (f" {text(suffix)}" if suffix else ""))


def vote_houses(session):
    """Legislator id -> the house whose floor votes they cast (the member list keeps only each member's latest house)."""
    key = (session, "vote_houses")
    if key not in _CACHE:
        c = {}
        for path in glob.glob(os.path.join(folder(session), "votes", "*.json")):
            for v in json.load(open(path)):
                h = {"HOUSE": "H", "SENATE": "S"}.get((v.get("systemId") or {}).get("chamber"))
                for lv in v.get("legislatorVotes") or []:
                    c.setdefault(lv["legislatorId"], Counter())[h] += 1
        _CACHE[key] = {i: x.most_common(1)[0][0] for i, x in c.items() if x}
    return _CACHE[key]


def members(session):
    """The session's members: id -> {"name", "house", "district", "seat", "party", "email", "start", "end", "position",
    "current"}. Current system: the house they voted in, the district from the member list unless P.SEAT_FIX says
    otherwise. Archive: the house from their standing committees (the list has no house), the archive's law-entity id."""
    key = (session, "members")
    if key in _CACHE:
        return _CACHE[key]
    out = {}
    today = date.today().isoformat()
    if archive(session):
        for m in load(session, "legislators", []) or []:
            le = m.get("lawEntity") or {}
            hs = Counter(((a.get("committee") or {}).get("houseCode")) for a in m.get("committeeAssignments") or []
                         if (a.get("committee") or {}).get("committeeTypeName") == "ST")
            hs.pop(None, None)
            d = m.get("districtNumber")
            h = hs.most_common(1)[0][0] if hs else None
            party = ((m.get("politicalParty") or {}).get("partyCode") or "")
            out[le.get("entityIdSequence")] = {
                "name": person(le.get("firstName"), le.get("lastName")), "house": h, "district": d,
                "seat": f"{h}:{d}" if d and h else None, "party": party, "email": None, "start": "", "end": "",
                "position": ((m.get("position") or {}).get("description") or None), "current": True}
    else:
        fix = P.SEAT_FIX.get(session, {})
        voted = vote_houses(session)
        for m in load(session, "legislators", []) or []:
            i = m["id"]
            h = voted.get(i) or {"HOUSE": "H", "SENATE": "S"}.get(m.get("chamber"))
            d = (m.get("district") or {}).get("number")
            seat = fix.get(i) or (f"{h}:{d}" if h and d else None)
            if seat:
                h, d = seat[0], int(seat[2:])
            out[i] = {"name": person(m.get("firstName"), m.get("lastName"), m.get("nameSuffix")), "house": h, "district": d,
                      "seat": seat, "party": ((m.get("politicalParty") or {}).get("code") or ""),
                      "email": text(m.get("emailAddress")) or None, "start": (m.get("startDate") or "")[:10],
                      "end": (m.get("endDate") or "")[:10], "position": m.get("position"), "current": True}
        # A seat belongs to the member holding it now (or last); members who left are "H?Mercer" in votes.
        by_seat = {}
        for i, m in out.items():
            if m["seat"]:
                by_seat.setdefault(m["seat"], []).append(i)
        for s, ids in by_seat.items():
            if len(ids) > 1:
                keep = max(ids, key=lambda i: (out[i]["end"] >= today, out[i]["end"], out[i]["start"]))
                for i in ids:
                    out[i]["current"] = i == keep
    _CACHE[key] = out
    return out


def seat_of(session, mid):
    m = members(session).get(mid)
    if not m or not m["seat"]:
        return None
    return m["seat"] if m["current"] else f"{m['house']}?{m['name'].split()[-1]}"


# ---------------------------------------------------------------- steps

PASS = {"BILL_PASSED", "BILL_PASSED_AS_AMENDED", "BILL_CONCURRED", "BILL_CONCURRED_AS_AMENDED", "REPORT_ADOPTED",
        "RESOLUTION_ADOPTED", "RESOLUTION_ADOPTED_AS_AMENDED", "VETO_OVERRIDDEN", "MOTION_CARRIED",
        "REVOTE_ON_PREVIOUS_ACTION", "BILL_REMOVED_FROM_TABLE", "BILL_TABLED"}


def outcome(res):
    """True (the motion carried), False (it failed), None (no result)."""
    if not res:
        return None
    return res in PASS


# Status names (both systems, without the house) -> step.
STEP_NAMES = [
    (r"Introduced", "intro"), (r"(?:1st|First) Reading", "first"),
    (r"Referred to Committee", "ref"), (r"Rereferred to Committee", "ref"),
    (r"Hearing", "hearing"), (r"Hearing Canceled", "canceled"),
    (r"Committee Executive Action(?:--.*)?", "exec"), (r"Committee Report(?:--.*)?", "report"),
    (r"Tabled in Committee", "tabled"), (r"Taken from Table in Committee", "untabled"),
    (r"Take(?:n)? from Committee; Place(?:d)? on 2nd Reading", "blast"),
    (r"Taken from 3rd Reading; Placed on 2nd Reading", "back2"),
    (r"Scheduled for (?:2nd|3rd) Reading", "scheduled"),
    (r"2nd Reading Motion to Amend.*", "amend"), (r"2nd Reading Pass Consideration|3rd Reading Pass Consideration", "passcons"),
    (r"2nd Reading Indefinitely Postponed", "ip"),
    (r"(2nd|3rd) Reading (?:Senate|House) Amendments.*", "concur"),
    (r"3rd Reading (?:Not )?Passed as Amended by (?:Senate|House)", "concur3"),
    (r"(2nd|3rd) Reading (?:Free )?Conference Committee Report.*", "conf"),
    (r"(2nd|3rd) Reading Governor's (?:Proposed )?Amendments.*", "govamd"),
    (r"3rd Reading; 2nd Chamber Vote Required|3rd Reading Failed; 2nd House Vote Required|"
     r"2nd Reading .*; 3rd Reading Vote Required", "needs"),
    (r"(2nd|3rd) Reading(?: .*)?", "reading"),
    (r"Transmitted to (?:Senate|House)", "transmitted"),
    (r"Returned to (?:House|Senate) with Amendments", "returned_amended"),
    (r"Returned to (?:House|Senate)", "returned"),
    (r"(?:Free )?Conference Committee Appointed", "confcomm"), (r"(?:Free )?Conference Committee (?:Report Received|Dissolved)", "confother"),
    (r"Reconsidered Previous Action.*", "reconsider"),
    (r"Sent to Enrolling", "enrolling"), (r"Returned from Enrolling", "enrolled"),
    (r"Signed by Speaker", "speaker"), (r"Signed by President", "president"),
    (r"Transmitted to Governor", "togov"), (r"Signed by Governor", "signed"),
    (r"Returned with Governor's (?:Proposed )?Amendments", "govback"),
    (r"Transmitted to (?:Senate|House) for Consideration of Governor's Proposed Amendments|Returned to (?:Senate|House) Concurred in Governor's Proposed Amendments", "govamdother"),
    (r"Returned with Governor's Line-item Veto", "lineitem"),
    (r"Vetoed by Governor", "vetoed"),
    (r"Veto Override Vote(?: Mail Poll)? in Progress", "poll"),
    (r"Veto Overridden by Legislature", "override_ok"), (r"Veto Override Failed in Legislature|Line-item Veto Override Failed", "override_fail"),
    (r"Veto Override", "override"),
    (r"Filed with Secretary of State", "sos"), (r"Chapter Number Assigned", "chapter"),
    (r"Died in (?:Standing )?Committee", "died_comm"), (r"Died in Process", "died"),
    (r"Missed Deadline for (.*) Transmittal", "deadline"),
    (r"Bill Withdrawn.*", "withdrawn"), (r"Bill Not Heard at Sponsor's Request", "notheard"),
    (r"Motion(?: Carried| Failed)?|On Motion Rules Suspended|Rules Suspended.*", "motion"),
]
STEP_RE = [(re.compile(rx + r"$"), k) for rx, k in STEP_NAMES]
SKIP = re.compile(r"Fiscal|Sponsor Rebuttal|Sponsor List Modified|Draft|Text Available|Printed|Amendments Available|Legal Review|"
                  r"Executive Director|Fiscal Impact|Requester")

# The archive's result words -> the current system's results.
WORDS = [(r"Bill Passed as Amended|Passed as Amended", "BILL_PASSED_AS_AMENDED"), (r"Bill Passed|Passed", "BILL_PASSED"),
         (r"Bill Concurred as Amended|Concurred as Amended", "BILL_CONCURRED_AS_AMENDED"), (r"Bill Concurred|Concurred", "BILL_CONCURRED"),
         (r"Not Passed as Amended|Pass as Amended Motion Failed", "BILL_NOT_PASSED_AS_AMENDED"),
         (r"Bill Not Passed|Not Passed|Pass Motion Failed|Failed", "BILL_NOT_PASSED"),
         (r"Not Concurred as Amended|Concur as Amended Motion Failed", "BILL_NOT_CONCURRED_AS_AMENDED"),
         (r"Not Concurred|Concur Motion Failed", "BILL_NOT_CONCURRED"),
         (r"Resolution Adopted as Amended", "RESOLUTION_ADOPTED_AS_AMENDED"), (r"Resolution Adopted", "RESOLUTION_ADOPTED"),
         (r"Report Adopted|Adopted", "REPORT_ADOPTED"), (r"Report Rejected|Rejected|Not Adopted|Adopt Motion Failed", "REPORT_REJECTED"),
         (r"Not Adopt Motion Failed", None), (r"Carried", "MOTION_CARRIED")]


def archive_result(step, rest):
    """The result an archive line's wording gives: "3rd Reading Concurred" -> BILL_CONCURRED."""
    if step == "concur3":
        return "BILL_NOT_CONCURRED" if "Not Passed" in rest else "BILL_CONCURRED"
    if step in ("tabled",):
        return "BILL_TABLED"
    if step == "untabled":
        return "BILL_REMOVED_FROM_TABLE"
    if step == "ip":
        return "MOTION_CARRIED"
    if step == "blast":
        return "MOTION_CARRIED"
    if step == "reconsider":
        return "REVOTE_ON_PREVIOUS_ACTION"
    if step == "override_ok":
        return "VETO_OVERRIDDEN"
    if step == "override_fail":
        return "VETO_NOT_OVERRIDDEN"
    tail = re.sub(r"^(?:Committee (?:Executive Action|Report)--|(?:2nd|3rd) Reading (?:(?:Senate|House) Amendments |(?:Free )?Conference "
                  r"Committee Report |Governor's (?:Proposed )?Amendments )?)", "", rest)
    if re.fullmatch(r"Not Adopt Motion Failed|Not Concur Motion Failed", tail):
        return None  # a motion against it failed: no decision
    for rx, res in WORDS:
        if re.fullmatch(rx, tail):
            return res
    return None


def step_of(name):
    for rx, k in STEP_RE:
        m = rx.match(name)
        if m:
            return k, m
    return None, None


def steps_current(session, b):
    """The current system's history: [{"d", "t", "h", "step", "res", "comm", "vote", "id", "name"}], in time order."""
    comms = {c["id"]: comm_name((((c.get("committeeDetails") or {}).get("committeeCode")) or {}).get("name"))
             for c in load(session, "committees", []) or []}
    out = []
    for s in (b.get("draft") or {}).get("billStatuses") or []:
        name = text((s.get("billStatusCode") or {}).get("name"))
        m = re.match(r"\((H|S|LC)\) (.*)", name)
        h, rest = (m.group(1), m.group(2)) if m else ("", name)
        if h == "LC" or SKIP.search(rest):
            continue
        step, mm = step_of(rest)
        if not step:
            step = "other"
        out.append({"d": (s.get("timeStamp") or "")[:10], "t": s.get("timeStamp") or "", "h": h if h in HOUSE else "",
                    "step": step, "res": s.get("result"), "comm": comms.get(s.get("standingCommitteeId")),
                    "vote": (s.get("vote") or {}).get("id"), "id": s.get("id"), "name": rest,
                    "reading": (mm.group(1) if mm and mm.groups() and mm.group(1) in ("2nd", "3rd") else None)})
    out.sort(key=lambda x: x["t"])
    return out


def steps_archive(session, b):
    out = []
    acts = list(reversed(b.get("billActions") or []))  # the archive lists them newest first
    for i, a in enumerate(acts):
        name = text((a.get("actionType") or {}).get("description"))
        m = re.match(r"\((H|S|C)\) (.*)", name)
        h, rest = (m.group(1), m.group(2)) if m else ("", name)
        if h == "C" or SKIP.search(rest):
            continue
        step, mm = step_of(rest)
        if not step:
            step = "other"
        y, n = a.get("yesVotes"), a.get("noVotes")
        out.append({"d": (a.get("date") or "")[:10], "t": a.get("date") or "", "h": h if h in HOUSE else "", "step": step,
                    "res": archive_result(step, rest), "comm": comm_name((a.get("committee") or {}).get("committeeName")) or None,
                    "vote": None, "id": i, "name": rest,
                    "tally": (int(y), int(n)) if str(y or "").isdigit() and str(n or "").isdigit() else None,
                    "reading": (mm.group(1) if mm and mm.groups() and mm.group(1) in ("2nd", "3rd") else None)})
    out.sort(key=lambda x: x["t"])  # by time; the file's order within the same time
    return out


# ---------------------------------------------------------------- votes

FLOOR_MOTIONS = re.compile(r"^(?:Do Pass|Do Concur|Do Adopt|Do Pass As Amended|Do Concur As Amended)$", re.I)
FLOOR_CODES = {"YES": None, "YES_EXCUSED": None, "NO": "N", "NO_EXCUSED": "N", "ABSENT": "A", "EXCUSED": "A"}
COMM_MOTIONS = {"do_pass", "do_pass_as_amended", "be_concurred_in", "be_concurred_in_as_amended"}
COMM_CODES = {"YES": None, "YES_BY_PROXY": None, "NO": "N", "NO_BY_PROXY": "N", "ABSTAINED": "A", "NO_VOTE": "A"}


def roll(session, h, pairs, codes):
    """[(legislator id, vote)] -> (yes, no, [[seat, "N"/"A"], ...])."""
    y = n = 0
    listed = []
    for mid, how in pairs:
        code = codes.get(how, "A")
        if code is None:
            y += 1
            continue
        n += code == "N"
        sid = seat_of(session, mid)
        if not sid or sid[0] != h:
            m = members(session).get(mid)
            sid = f"{h}?{m['name'].split()[-1] if m else mid}"
        listed.append([sid, code])
    return y, n, listed


def floor_votes(session, k):
    """The current system's floor roll calls, by vote id: {"vote": [h, "F", None, date, yes, no, [[seat, "N"/"A"]]],
    "against": True for a motion against the bill ("Do Not Concur", "Do Not Pass"), "own": True for the bill's own
    question (second and third reading, concurring, conference reports, the governor's amendments; not amendments or
    procedural motions, which aren't linked to those steps)}."""
    out = {}
    for v in per_bill(session, "votes", k):
        motion = text(v.get("motion"))
        h = {"HOUSE": "H", "SENATE": "S"}.get((v.get("systemId") or {}).get("chamber"))
        if not h:
            continue
        y, n, listed = roll(session, h, [(lv["legislatorId"], lv.get("voteType")) for lv in v.get("legislatorVotes") or []], FLOOR_CODES)
        against = bool(re.match(r"Do Not\b", motion, re.I))
        out[v["id"]] = {"vote": [h, "F", None, (v.get("dateTime") or "")[:10], y, n, listed], "against": against,
                        "own": not against and (not motion or bool(FLOOR_MOTIONS.match(motion)))}
    return out


def committee_votes(session, k):
    out = []
    for a in per_bill(session, "committee", k):
        if a.get("motion") not in COMM_MOTIONS:
            continue
        sc = (a.get("standingCommitteeMeeting") or {}).get("standingCommittee") or {}
        h = {"HOUSE": "H", "SENATE": "S"}.get(sc.get("chamber"))
        cname = comm_name((((sc.get("committeeDetails") or {}).get("committeeCode")) or {}).get("name"))
        if not h or not a.get("legislatorVotes"):
            continue  # (a few records have no members' votes: HB 232 of 2025)
        y, n, listed = roll(session, h, [((lv.get("membership") or {}).get("legislatorId"), lv.get("committeeVote"))
                                         for lv in a.get("legislatorVotes") or []], COMM_CODES)
        out.append({"status": a.get("billStatusId"), "vote": [h, "C", cname, (a.get("voteTime") or "")[:10], y, n, listed]})
    return out


# ---------------------------------------------------------------- one bill

def tally_text(t):
    return f", {t[0]}-{t[1]}" if t else ""


def record(session, k, b):
    p = k
    origin = p[0]
    other = "S" if origin == "H" else "H"
    amendment = is_amendment(b)
    steps = steps_archive(session, b) if archive(session) else steps_current(session, b)
    fv = {} if archive(session) else floor_votes(session, k)
    cv = [] if archive(session) else committee_votes(session, k)
    cv_by_status = {c["status"]: c["vote"] for c in cv if c["status"]}
    out = []  # (date, house or "G", wording, kind)
    votes = []
    passed, failed = set(), set()
    last_vote = {}
    second_amended = False
    concur_ok = conf_ok = False
    conf = {}
    signed_by = set()
    enrolled = sent = signed = vetoed = law_line = item = overridden = govback = withdrawn = False
    tabled = died_comm = False
    place, where_h, comm = "committee", origin, None
    refs = []
    first_ref, first_fate = None, None
    exec_ok = False
    deadline = None
    def decide(s, ok, tl):
        """A floor vote's outcome and tally, adding its roll call to the bill's votes. The current system's result is
        wrong on some failed votes ("BILL_CONCURRED" on HB 93 of 2025's 24-26 third reading; ties too): with a roll
        call, a motion for the bill carries only with more ayes than noes (a result of failure stands: some votes need
        two-thirds), and a motion against it ("Do Not Concur") decides by its own tally."""
        r = fv.get(s["vote"]) if s["vote"] else None
        if r:
            v = r["vote"]
            if r["own"]:
                votes.append(v)
            if r["against"]:
                return v[4] <= v[5], None
            return (ok and v[4] > v[5]), (v[4], v[5])
        if tl and s["h"]:
            votes.append([s["h"], "F", None, s["d"], tl[0], tl[1], []])
        return ok, tl

    for s in steps:
        d, h, st, res, ok = s["d"], s["h"], s["step"], s["res"], outcome(s["res"])
        H = HOUSE.get(h, "")
        tl = s.get("tally")
        if st == "intro":
            if h == origin and not any(x[3] == "intro" for x in out):
                out.append((d, h, "Introduced", "intro"))
            continue
        if st == "ref":
            c = s["comm"]
            if c:
                comm, place, where_h = c, "committee", h
                tabled = False
                refs.append((h, c))
                if first_ref is None and h == origin:
                    first_ref = c
                out.append((d, h, f"REFERRED TO {c.upper()}", "ref"))
            continue
        if st == "hearing":
            if s["comm"]:
                out.append((d, h, f"Hearing in the {s['comm']} Committee", "hearing"))
            continue
        if st == "exec":
            c = s["comm"] or comm or ""
            v = cv_by_status.get(s["id"])
            if v:
                tl = (v[4], v[5])
            amended = "AS_AMENDED" in (res or "")
            word = "pass" if h == origin else "concur"
            if tl and archive(session):
                votes.append([h, "C", c, d, tl[0], tl[1], []])
            if ok:
                exec_ok = True
                if first_fate is None and h == origin and c == first_ref:
                    first_fate = "passed"
                out.append((d, h, "REPORTED", "reported"))
                out.append((d, h, f"The {c} Committee voted to recommend it {'pass' if word == 'pass' else 'be concurred in'}"
                            + (" with amendments" if amended else "") + tally_text(tl), "exec"))
            elif ok is False:
                if first_fate is None and h == origin and c == first_ref:
                    first_fate = "defeated"
                out.append((d, h, f"A motion in the {c} Committee to recommend it {'pass' if word == 'pass' else 'be concurred in'} failed"
                            + tally_text(tl), "exec"))
            continue
        if st == "report":
            place, where_h = "floor", h
            tabled = False
            out.append((d, h, "The committee's report was read on the floor", "report"))
            continue
        if st == "tabled":
            tabled = True
            if first_fate in (None, "defeated") and h == origin and (s["comm"] or comm) == first_ref:
                first_fate = "held"
            out.append((d, h, "Tabled in committee", "tabled"))
            continue
        if st == "untabled":
            tabled = False
            out.append((d, h, "Taken off the table in committee", "untabled"))
            continue
        if st == "blast":
            if ok is False:
                out.append((d, h, f"A motion to take it from the committee to the {H} floor failed", "blastfail"))
            else:
                place, where_h, tabled = "floor", h, False
                out.append((d, h, f"The {H} took it from the committee and placed it on second reading", "blast"))
            continue
        if st == "back2":
            out.append((d, h, "Sent back to second reading", "back2"))
            continue
        if st in ("scheduled", "passcons", "first", "canceled", "motion", "confother", "govamdother", "poll", "enrolled"):
            if st == "poll":
                out.append((d, "G", "The Secretary of State polled the legislators by mail on overriding the veto", "poll"))
            elif st == "enrolled":
                enrolled = True
            elif st == "passcons":
                out.append((d, h, "Passed over for the day", "passcons"))
            continue
        if st == "amend":
            if ok is not None:
                out.append((d, h, f"An amendment {'was adopted' if ok else 'failed'} on second reading", "amend"))
            continue
        if st == "ip":
            if ok:
                failed.add(h)
                last_vote[h] = "fail"
                place = "floor"
                out.append((d, h, f"The {H} killed it on second reading (indefinitely postponed)", "ip"))
            continue
        if st == "needs":
            # A constitutional amendment short of two-thirds in this house: it needs the other house's votes to reach
            # 100 of the 150 legislators.
            out.append((d, h, f"The {H}'s vote fell short of two-thirds; the amendment needs 100 of the 150 legislators' votes counting both houses", "needs"))
            if h == origin:
                passed.add(h)
                last_vote[h] = "pass"
                place, where_h, comm = "committee", other, None
            continue
        if st == "reading":
            rd = s["reading"]
            if ok is None:
                continue
            ok, tl = decide(s, ok, tl)
            amended = "AS_AMENDED" in (res or "")
            if not ok:
                failed.add(h)
                last_vote[h] = "fail"
                place, where_h = "floor", h
                out.append((d, h, f"Failed {'second' if rd == '2nd' else 'third'} reading in the {H}" + tally_text(tl), "fail"))
                continue
            failed.discard(h)
            if rd == "2nd":
                place, where_h = "floor", h
                out.append((d, h, f"Approved on second reading in the {H}" + (" with amendments" if amended else "") + tally_text(tl), "second"))
                continue
            last_vote[h] = "pass"
            first_time = h not in passed
            passed.add(h)
            if h == origin and first_time:
                place, where_h, comm = "committee", other, None
            out.append((d, h, f"PASSED {H.upper()}", "pass"))
            if tl:
                out.append((d, h, f"The {H} vote: {tl[0]}-{tl[1]}", "tally"))
            continue
        if st == "transmitted":
            out.append((d, h, f"Sent to the {HOUSE[other if h == origin else origin]}", "transmitted"))
            continue
        if st == "returned_amended":
            second_amended = True
            place, where_h = "desk", origin
            out.append((d, h, f"Sent back to the {HOUSE[origin]} with the {HOUSE[other]}'s amendments", "returned"))
            continue
        if st == "returned":
            out.append((d, h, f"RETURNED TO {HOUSE[origin].upper()}", "returned"))
            continue
        if st == "concur" or st == "concur3":
            rd = "3rd" if st == "concur3" else s["reading"]
            if ok is None:
                continue
            ok, tl = decide(s, ok, tl)
            if ok and rd == "3rd":
                concur_ok = True
                last_vote[h] = "concur"
            out.append((d, h, f"The {H} {'agreed' if ok else 'refused'} to the {HOUSE[other if h == origin else origin]}'s amendments"
                        + (" on second reading" if rd == "2nd" else "") + tally_text(tl), "concur"))
            continue
        if st == "confcomm":
            conf = {}
            out.append((d, h, "Conference committee appointed" if not s["name"].startswith("Free") else "Free conference committee appointed", "confcomm"))
            continue
        if st == "conf":
            rd = s["reading"]
            if ok is None:
                continue
            ok, tl = decide(s, ok, tl)
            if rd == "3rd":
                conf[h] = ok
            out.append((d, h, f"The {H} {'adopted' if ok else 'rejected'} the conference committee's report"
                        + (" on second reading" if rd == "2nd" else "") + tally_text(tl), "conf"))
            continue
        if st == "reconsider":
            if ok:
                lv = last_vote.pop(h, None)
                if lv == "pass":
                    passed.discard(h)
                elif lv == "fail":
                    failed.discard(h)
                elif lv == "concur":
                    concur_ok = False
                out.append((d, h, f"The {H} voted to reconsider its last vote", "reconsider"))
            continue
        if st == "enrolling":
            enrolled = True
            out.append((d, h, "Sent to enrolling (passed both houses)", "enrolling"))
            continue
        if st in ("speaker", "president"):
            signed_by.add(st)
            out.append((d, h, "Signed by the Speaker of the House" if st == "speaker" else "Signed by the President of the Senate", "signature"))
            continue
        if st == "togov":
            sent = True
            govback = False
            out.append((d, h, "DELIVERED TO GOVERNOR", "sent"))
            continue
        if st == "govback":
            sent, govback = False, True
            out.append((d, "G", "The governor sent it back with proposed amendments", "govback"))
            continue
        if st == "govamd":
            if ok is None:
                continue
            ok, tl = decide(s, ok, tl)
            out.append((d, h, f"The {H} {'adopted' if ok else 'rejected'} the governor's proposed amendments"
                        + (" on second reading" if s["reading"] == "2nd" else "") + tally_text(tl), "govamd"))
            continue
        if st == "signed":
            signed = True
            out.append((d, "G", "Signed by the governor", "signed"))
            continue
        if st == "lineitem":
            item = True
            out.append((d, "G", "Signed by the governor, with line-item vetoes", "signed"))
            continue
        if st == "vetoed":
            vetoed = True
            out.append((d, "G", "VETOED", "vetoed"))
            continue
        if st in ("override", "override_ok", "override_fail"):
            if ok is None:
                continue
            if "Line-item" in s["name"]:
                out.append((d, "G", "The legislators' poll failed to override the line-item vetoes", "override"))
                continue
            overridden = overridden or ok
            out.append((d, "G", "The legislators overrode the veto (two-thirds of each house, by mail poll)" if ok
                        else "The veto stood: the legislators' poll fell short of two-thirds of each house", "override"))
            continue
        if st == "sos":
            out.append((d, "G", "Filed with the Secretary of State", "sos"))
            continue
        if st == "chapter":
            law_line = law_line or d
            continue  # the chapter is shown once, below
        if st == "died_comm":
            died_comm = True
            out.append((d, h, "Died in committee", "died"))
            continue
        if st == "died":
            out.append((d, h, "Died in process", "died"))
            continue
        if st == "deadline":
            what = s["name"]
            mm = re.search(r"Missed Deadline for (.*) Transmittal", what)
            kind = (mm.group(1).lower() if mm else "general bill").replace("bill", "bills").replace("proposal", "proposals")
            deadline = d
            out.append((d, h, f"Missed the deadline for {kind} to pass their first house", "deadline"))
            continue
        if st in ("withdrawn", "notheard"):
            withdrawn = withdrawn or st == "withdrawn"
            out.append((d, h, "Withdrawn" if st == "withdrawn" else "Not heard, at the sponsor's request", st))
            continue
        out.append((d, h or "G", s["name"], "other"))
    out.sort(key=lambda x: x[0])  # by day; the order within a day stays

    chapter = chapter_of(b)
    both = (origin in passed and other in passed and not second_amended) or concur_ok or \
        (conf.get("H") and conf.get("S")) or enrolled or len(signed_by) == 2 or sent or chapter is not None or vetoed
    if amendment:
        # Two-thirds of all 150 legislators, both houses' votes counted together: one that passed each house but fell short
        # of 100 dies (HB 372 and HB 517 of 2023); one that reached it is enrolled and goes to the Secretary of State.
        if both and (enrolled or any(x[3] == "sos" for x in out)):
            stage = 3
        elif origin in passed and other in passed:
            passed.discard(other)
            # (The second house's vote counts toward the 100, not as its passage.)
            out = [(x[0], x[1], f"The {HOUSE[other]} voted for it, short of the two-thirds needed" if x[2] == f"PASSED {HOUSE[other].upper()}" else x[2], x[3]) for x in out]
            last = max(x[0] for x in out)
            out.append((last, "G", "It fell short of the 100 votes (two-thirds of the 150 legislators, both houses counted together) a constitutional amendment needs", "short"))
            stage = 2
        else:
            stage = 2 if passed else None
        chapter = None
    elif chapter:
        stage = 5
    elif vetoed:
        stage = 6
    elif sent:
        stage = 4
    elif both:
        stage = 3
    elif passed:
        stage = 2
    else:
        stage = None
    if stage is not None and stage >= 3:
        passed = {"S", "H"}
    if stage is None:
        stage = 1 if (place == "floor" or origin in failed) and not tabled else 0
    if stage == 5:
        how = ("Became law over the governor's veto" if overridden else "Signed by the governor, with line-item vetoes" if item
               else "Signed by the governor" if signed else "Became law without the governor's signature")
        when = max((x[0] for x in out if x[3] in ("signed", "override")), default=None) or law_line or \
            max((x[0] for x in out if x[3] in ("sent", "sos")), default=None) or max(x[0] for x in out)
        out = [x for x in out if not (x[3] == "signed" and not overridden)]
        out.append((when, "G", f"SIGNED CHAPTER {chapter}" if signed and not item and not overridden else f"{how} (chapter {chapter})", "law"))
        out.sort(key=lambda x: x[0])

    title = short_title(b)
    if amendment and not re.search(r"constitution", title, re.I):
        title = f"Constitutional amendment: {title[:1].lower() + title[1:]}"
    subj = subjects(b)
    topics = list(dict.fromkeys((["const"] if amendment else []) +
                                [P.SUBJECT_TOPICS[c] for c in subj if c in P.SUBJECT_TOPICS] +
                                [t for t in P.TOPIC_WORDS if P.TOPIC_WORDS[t].search(title)]))
    fate = first_fate or ("passed" if exec_ok or passed else "none")
    comm_now = comm if place == "committee" and stage in (0, 2) else None
    where = HOUSE.get(where_h, HOUSE[origin])
    if stage == 0:
        desc = "Tabled in committee" if tabled else "Withdrawn" if withdrawn else f"In {where} committee"
    elif stage == 1:
        desc = f"Failed in the {HOUSE[origin]}" if origin in failed else f"On the {where} floor"
    else:
        desc = {2: f"Passed the {HOUSE[origin] if origin in passed else HOUSE[other]}" + (f"; failed in the {HOUSE[other]}" if other in failed else ""),
                3: "Passed both houses", 4: "On the governor's desk", 5: "Became law", 6: "Vetoed"}[stage]

    # Sponsors.
    sponsor, district, cos = "—", 0, []
    if archive(session):
        for r in b.get("primarySponsorBillRoles") or []:
            le = r.get("lawEntity") or {}
            m = members(session).get(le.get("entityIdSequence"))
            sponsor = m["name"] if m else person(le.get("firstName"), le.get("lastName"))
            district = (m or {}).get("district") or ((r.get("legislator") or {}).get("districtNumber")) or 0
            break
    else:
        ms = members(session)
        m = ms.get(b.get("sponsorId"))
        if m:
            sponsor, district = m["name"], m["district"] or 0
        cos = [ms[i]["name"] for i in (load(session, "cosponsors", {}) or {}).get(k, []) if i in ms and ms[i]["name"] != sponsor]

    def dates(test, mode="last"):
        ds = sorted({x[0] for x in out if test(x) and x[0]})
        return {"first": ds[0], "last": ds[-1], "all": ";".join(ds)}[mode] if ds else ""

    votes.extend(c["vote"] for c in cv)
    votes.sort(key=lambda v: v[3])
    action_dates = [x[0] for x in out if x[0]]
    # The Legislature's Bill Explorer: /#/laws/bill/<session id>/<LC number> (current system), /#/bill/20231/LC0375 (archive).
    link = (f"https://bills.legmt.gov/#/laws/bill/{b.get('sessionId')}/{(b.get('draft') or {}).get('draftNumber')}?open_tab=sum"
            if not archive(session) else f"https://bills.legmt.gov/#/bill/{(b.get('id') or {}).get('sessionId')}/{(b.get('id') or {}).get('billDraftNumber')}")
    return {
        "nums": [p], "base": [p], "prev": earlier(session, b, p),
        "title": title, "summary": "", "act": "", "lawCode": "", "law": None, "laws": [],
        "comms": sorted({f"{h} · {c}" for h, c in refs}), "topics": topics, "places": [], "narrow": P.narrow_kind(title),
        "commFate": fate, "mainTopic": topics[0] if topics else "", "local": "local" in topics,
        "senDeleg": False, "asmDeleg": False,
        "budget": bool(re.search(r"\b(?:general appropriations act|appropriat\w+|budget|pay plan|long-range)\b", title, re.I) and "APP" in subj),
        "passedS": "S" in passed, "passedA": "H" in passed, "program": None,
        "stage": stage, "passedIn": (HOUSE[origin] if origin in passed else HOUSE[other]) if stage == 2 else None,
        "chapter": chapter if stage == 5 else None,
        "veto": None, "memo": "", "vetoMemo": None,
        # The short title and the subjects' names: titles are short, and words only one bill has don't count, so a title
        # alone made "Establish compensation for wrongful conviction" (HB 93 of 2025) "nearly the same" as HB 72 (militia pay).
        "simText": f"{title} {subject_names(b)}",
        "comm": comm_now if stage == 0 else None,
        "first": min(action_dates, default=f"{session}-01-01"),
        "last": max(action_dates, default=f"{session}-01-01"),
        "cosp": len(cos),
        "keyDates": [
            dates(lambda x: x[3] == "reported", "first"),
            dates(lambda x: x[2] == "PASSED SENATE", "all"),
            dates(lambda x: x[2] == "PASSED HOUSE", "all"),
            "",
            dates(lambda x: x[3] == "sent") if stage >= 4 else "",
            dates(lambda x: x[3] == "law") if stage == 5 else "",
            dates(lambda x: x[3] == "vetoed"),
        ],
        "votes": votes, "firstComms": [(origin, first_ref, fate == "passed")] if first_ref else [],
        "vers": [{"p": p, "sponsor": sponsor, "district": district, "cosponsors": cos, "primes": 1, "cosp": len(cos),
                  "statusDesc": desc, "committee": comm_now, "link": link,
                  "actions": [[x[0], x[2]] for x in out]}],
    }


def load_session(session):
    """Read one session's bills and return (records, bill number -> record index, fetched time, delegation)."""
    recs, index = [], {}
    bs = bills(session)
    for k in sorted(bs, key=lambda k: (KINDS.index(k[:2]), int(k[2:]))):
        index[k] = len(recs)
        recs.append(record(session, k, bs[k]))
    parties = _PARTIES.setdefault(session, {})
    for m in members(session).values():
        if m["party"] in ("D", "R"):
            parties[(m["house"], m["name"])] = m["party"]
    path = os.path.join(P.DATA, "last_checked")
    when = ""
    if os.path.exists(path):
        try:
            when = datetime.fromisoformat(open(path).read().strip().replace("Z", "+00:00")).astimezone(ZoneInfo(P.TIMEZONE)).strftime("%Y-%m-%d %H:%M")
        except ValueError:
            when = ""
    # No "What it does": the data has no summary of what a bill does, only its short title.
    return recs, index, when, {"SENATE": [], "ASSEMBLY": []}


# ---------------------------------------------------------------- earlier sessions

_STOP = set("the a an of to and or for in on by with revise revising generally provide providing create creating laws law "
            "related relating act establish require requiring".split())


def _prime(session, b):
    if archive(session):
        r = (b.get("primarySponsorBillRoles") or [{}])[0]
        le = r.get("lawEntity") or {}
        return person(le.get("firstName"), le.get("lastName"))
    m = members(session).get(b.get("sponsorId"))
    return m["name"] if m else ""


def _keys(session):
    """A session's bills that didn't become law: short title -> [(bill number, prime sponsor)]."""
    if session not in _KEYS:
        out = {}
        for k, b in bills(session).items():
            if chapter_of(b):
                continue  # a law isn't tried again (yearly bills like the budgets share titles)
            out.setdefault(short_title(b).lower(), []).append((k, _prime(session, b)))
        _KEYS[session] = out
    return _KEYS[session]


def earlier(session, b, p):
    """The same bill in the session before: the same short title and prime sponsor, or a short title only one bill has in
    each session. Never appropriations, nor a bill that became law, nor the stock "Generally revise ..." titles."""
    out = set()
    k = short_title(b).lower()
    if len(k.split()) < 3 or re.match(r"(?:generally revise|revise|appropriat)", k) and len(k.split()) < 5 or "APP" in subjects(b):
        return out
    y = session - 2
    if y in sessions():
        old = _keys(y).get(k, [])
        who = _prime(session, b)
        same = [n for n, sp in old if sp and sp == who]
        if same:
            out.add((y, same[0]))
        elif len(old) == 1 and len([1 for x in bills(session).values() if short_title(x).lower() == k]) == 1:
            out.add((y, old[0][0]))
        elif who:
            # The same prime sponsor with most of the title's words ("Create offense of trespass by unmanned aerial
            # vehicle" -> "Establish the offense of ...").
            w = _words(k)
            best = max(((len(w & _words(t)) / max(1, len(w | _words(t))), n) for t, xs in _keys(y).items() for n, sp in xs if sp == who),
                       default=(0, None))
            if best[0] >= 0.6 and len(w) >= 2:
                out.add((y, best[1]))
    return out


def _words(t):
    return {w for w in re.findall(r"[a-z]{3,}", t.lower()) if w not in _STOP}


def agendas(session):
    """Bills with a committee hearing still to come: bill -> [["House Judiciary", "2027-01-14T08:00:00"], ...]."""
    today = date.today().isoformat()
    out = {}
    if archive(session):
        return out
    for k, b in bills(session).items():
        for s in steps_current(session, b):
            if s["step"] == "hearing" and s["t"][:10] >= today and s["comm"]:
                entry = [f"{HOUSE.get(s['h'], '')} {s['comm']}".strip(), s["t"][:19]]
                if entry not in out.setdefault(k, []):
                    out[k].append(entry)
    return out


def parties(session, recs):
    if session not in _PARTIES:
        load_session(session)
    return {k: v for k, v in _PARTIES.get(session, {}).items() if v in ("D", "R")}
