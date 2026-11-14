"""New Hampshire's bills (downloaded by states/nh/fetch.py: the General Court's daily data files, and past years from its
SQL Server in the same shapes) in the shape build_data.py reads. House and Senate bills of each year's session, plus
CACRs (constitutional amendment concurrent resolutions, numbered "CACR 1" whichever house they start in; shown as
"HCACR1" or "SCACR1", since the site reads a bill's house from its number); other resolutions are left out.

A page is one session year. Each year's files hold the bills finished in it, so a bill a committee kept over to the
second year of the General Court ("Retained in Committee" in the House, "Rereferred to Committee, MA" in the Senate)
is in the second year's files only, with its whole history: the first year's page takes it from there, with the lines
dated in the first year, and both pages show it under the same number.

The Docket's history lines are written by each house's clerk, as written ("Ought to Pass with Amendment 2025-0695h: MA
RC 212-161 03/20/2025  HJ 9  P. 28"; the Senate's "Ought to Pass: MA, VV; OT3rdg; 05/15/2025;  SJ 12"). MA and MF are
"motion adopted" and "motion failed"; VV a voice vote, DV a division (a tally without names), RC a roll call. Every
bill gets a committee report and a floor vote: "Ought to Pass" (with or without amendment), "Inexpedient to Legislate"
(ITL: adopted, it kills the bill), "Refer for Interim Study" (also the end of the bill for the year), or, in the first
year, "Retained in Committee". A House bill that spends money or changes taxes goes on to Finance or Ways and Means
after its first report is adopted ("Referred to Finance"), and the House votes again on that committee's report; the
Senate's version is "Ought to Pass: MA, VV; Refer to Finance Rule 4-5". So a house passes a bill with the last "Ought to
Pass" it adopts that isn't followed by another referral. "OT3rdg" (ordered to third reading) is the Senate's passage:
third reading follows the same day without its own line. When the second house amends a bill, the first concurs ("House
Concurs with Senate Amendment", "Sen. X Moved to Concur with the House Amendment, MA") or a committee of conference
reports, and both houses have to adopt the report. Both houses then adopt the enrolled bills committee's report
("Enrolled (in recess of) ...", "Enrolled Adopted, VV"), and the bill goes to the governor: "Signed by Governor Ayotte
06/10/2025; Chapter 74; eff. 07/01/2025", "Vetoed by Governor ...", "Law Without Signature ...; Chapter 12", "Veto
Overridden ...: RC 300-80 by Required Two-Thirds Vote". CACRs pass each house by three-fifths and go to the voters.

The line's own date ("03/20/2025") is the event's; the entry's time is when the clerk wrote it, sometimes days later
and out of order (HB 10 of 2025: the House concurring was entered before the Senate's passage on the same day). Lines
are sorted by day, and within a day by the order the steps have to happen in. Members' votes are the roll calls'
(RollCallHistory); most bill votes are voice votes, with no names and no tally.
"""
import functools, glob, json, os, re
from collections import defaultdict
from datetime import datetime
from zoneinfo import ZoneInfo

from states.nh import profile as P

HOUSE = {"S": "Senate", "H": "House"}
CURRENT = P.session_of(datetime.now(ZoneInfo(P.TIMEZONE)).year)
_PARTIES = {}
# A bill's kind (LSRs column 4) -> its number's letters; 3 and 13 are CACRs.
KINDS = {"1": "HB", "2": "SB", "3": "CACR", "13": "CACR"}


def folder(session):
    return os.path.join(P.DATA, str(P.first_year(session)))


def rows(path, sep="|"):
    """A pipe-delimited file's rows (UTF-8 with a byte-order mark; fetch.py has rejoined records cut by line breaks)."""
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8-sig") as f:
        return [l.rstrip("\r\n").split(sep) for l in f if l.strip()]


@functools.lru_cache(maxsize=None)
def _sessions():
    return tuple(sorted(int(m.group(1)) for f in glob.glob(os.path.join(P.DATA, "[0-9]" * 4, "LSRs_*.txt"))
                  for m in [re.search(r"LSRs_(\d{4})\.txt$", f)] if m and len(rows(f)) > 100))


def sessions():
    return list(_sessions())


def text(x):
    return re.sub(r"\s+", " ", (x or "").replace(" ", " ")).strip()


def iso(d):
    """"1/7/2026 12:00:00 AM" or "03/20/2025" -> "2026-01-07"."""
    m = re.search(r"(\d{1,2})/(\d{1,2})/(\d{4})", d or "")
    return f"{m.group(3)}-{int(m.group(1)):02d}-{int(m.group(2)):02d}" if m else ""


def number(kind, house, n):
    """The site's number: "HB54", "SB12", "HCACR1" (a CACR with its house of origin)."""
    letters = KINDS[kind]
    return f"{house}{letters}{int(n)}" if letters == "CACR" else f"{letters}{int(n)}"


def official(p):
    """The General Court's own number: "HCACR1" -> "CACR1"."""
    return re.sub(r"^[HS](?=CACR)", "", p)


# ---- Members: PersonID -> (house, name, party, county code, district), from the General Court's legislators file
# for the biennium (and, for the current one, the members who have left since).
_PEOPLE = {}


def people(first):
    if first not in _PEOPLE:
        out = {}
        for name in ("former_legislators.txt", "legislators.txt"):  # sitting members' rows win
            for r in rows(os.path.join(P.DATA, str(first), name)):
                if len(r) >= 9 and r[0].strip().isdigit():
                    full = text(f"{r[2]} {r[1]}")
                    out[int(r[0])] = {"house": r[4] or r[3], "name": full, "party": (r[8] or "").upper()[:1],
                                      "county": int(r[6]) if r[6].strip().isdigit() else 0,
                                      "district": int(r[7]) if r[7].strip().isdigit() else 0,
                                      "seat": r[5].strip(), "sitting": name == "legislators.txt"}
        _PEOPLE[first] = out
    return _PEOPLE[first]


def seat_ids(first):
    """PersonID -> seat id for the sitting members: "S:12"; "H:612a", "H:612b" ... for the members of a House district
    (Hillsborough 12: the county's code times 100 plus the district), lettered in the order of their seat numbers. The
    same ids as contacts.py's."""
    out, by_district = {}, defaultdict(list)
    for pid, m in people(first).items():
        if not m["sitting"] or not m["district"]:
            continue
        if m["house"] == "S":
            out[pid] = f"S:{m['district']}"
        else:
            by_district[m["county"] * 100 + m["district"]].append((int(m["seat"]) if m["seat"].isdigit() else 9999, pid))
    for d, ms in by_district.items():
        for i, (_, pid) in enumerate(sorted(ms)):
            out[pid] = f"H:{d}{chr(97 + i)}"
    return out


def committee_names(first):
    return {r[0].upper(): text(r[1]) for r in rows(os.path.join(P.DATA, str(first), "Committees.txt")) if len(r) > 1} or \
        {r[0].upper(): text(r[1]) for r in rows(os.path.join(P.DATA, str(CURRENT if CURRENT % 2 else CURRENT - 1), "Committees.txt")) if len(r) > 1}


def subject_codes(first):
    for f in (first, P.first_year(CURRENT)):
        got = {r[0]: r[1] for r in rows(os.path.join(P.DATA, str(f), "SubjectCodes.txt")) if len(r) > 1}
        if got:
            return got
    return {}


def committee(c):
    """"Health, Human Services and Elderly Affairs HJ 3 P. 5" -> the name; "Finance Rule 4-5" -> "Finance"."""
    c = re.sub(r"\s+(?:HJ|SJ|HC|SC)\s+\d.*$|\s+\d{1,2}/\d{1,2}/\d{4}.*$|\s+Rule [\d-]+.*$", "", text(c))
    c = re.sub(r"[;,.\s]+$", "", c)
    c = re.sub(r"^(?:the )?(?:House |Senate )?(?:Committee on )?", "", c)
    return re.sub(r"(?<=\s)(And|Of|The|On|For|To|In)\b", lambda m: m.group(1).lower(), c)


def tally(a):
    """A roll call's or division's count in a line: "RC 212-161", "DV 210-162", "RC 14Y-10N"."""
    m = re.search(r"\b(?:RC|DV)\s+(\d+)Y?-(\d+)N?\b", a)
    return (int(m.group(1)), int(m.group(2))) if m else None



def decode(a, h):
    """One history line -> (shared wording, kind of step), or (the line as written, "") for lines the rules don't use.
    Kinds: intro (introduced and referred), refer (a later referral), report, pass, kill, retain, table, untable, reconsider, concur, ccr, enroll, sign, nosign, veto,
    override."""
    adopted = bool(re.search(r"(?::|,|;)\s*MA\b|\bMA\s+(?:VV|RC|DV)\b|\bMA\s*[;,]", a)) and not re.search(r"\bMF\b", a)
    m = re.match(r"(?:To Be )?Introduced\b.*?\band [Rr]eferred to (.+)$", a)
    if m:
        return f"REFERRED TO {committee(m.group(1)).upper()}", "intro"
    m = re.match(r"(?:Referred|Rereferred) to (Finance|Ways and Means|Capital Budget|[A-Z][\w ,&'-]+?)(?:\s+\d{1,2}/|\s+HJ\b|;|$)", a)
    if m and not re.match(r"Rereferred to Committee", a):
        return f"REFERRED TO {committee(m.group(1)).upper()}", "refer"
    if re.match(r"Referral Waived", a):
        return a, "waive"  # the second committee gave up its referral: the house's passage stands
    if re.match(r"Retained in Committee", a) or (re.match(r"Rereferred to Committee\b", a) and adopted):
        return a, "retain"
    m = re.match(r"(?:Majority )?Committee Report:\s*(.+)$", a)
    if m:
        rec = m.group(1)
        if re.match(r"(?:Ought to Pass|Without Recommendation)", rec, re.I):
            return a, "report-otp" if re.match(r"Ought to Pass", rec, re.I) else "report"
        if re.match(r"(?:Inexpedient|Refer(?:red)? (?:for|to) Interim Study)", rec, re.I):
            return a, "report-kill"
        if re.match(r"(?:Retain|Rereferred)", rec, re.I):
            return a, ""
        return a, "report"
    # The Senate's floor vote names the committee referral in the same line.
    if re.match(r"Ought [Tt]o Pass", a) and adopted:
        m = re.search(r"Refer to (Finance|Ways and Means|Capital Budget)", a)
        if m:
            return f"REFERRED TO {m.group(1).upper()}", "refer"
        # The Senate passes a bill when it orders it to third reading ("OT3rdg"); "Ought to Pass: MA" alone leaves that
        # motion pending (and the bill can be tabled on it: HB 246 of 2026).
        if h == "S" and not re.search(r"OT3rdg|Third Time", a, re.I):
            return a, ""
        return f"PASSED {HOUSE[h].upper()}", "pass"
    if re.match(r"OT3rdg;", a):
        return f"PASSED {HOUSE[h].upper()}", "pass"
    if re.match(r"Pending Motion", a):
        return a, ""
    if re.match(r"(?:Inexpedient to Legislate|Indefinitely Postpone|Refer(?:red)? (?:for|to) Interim Study)", a) and \
            (adopted or re.match(r"Inexpedient to Legislate, Senate Rule", a)):
        return a, "kill"
    if re.search(r"\bon (?:the )?Table\b|Laid on Table", a) and not re.search(r"Remove|Taken off|Died on", a, re.I) and adopted:
        return a, "table"
    if re.search(r"Remove(?:r)? [Ff]rom (?:the )?Tab|Taken off the Table", a) and adopted:
        return a, "untable"
    if re.match(r"Died on (?:the )?Table", a):
        return a, ""
    # A house undoing its passage: "Reconsider OTPA (Rep. X): MA", "... Reconsider the Vote on Third Reading and Final
    # Passage ..., MA", "The Chair rescinded OT3rdg". Not "Reconsider HB 1: MA" alone (it reconsiders the last vote, here a
    # conference report or a veto) or a reconsidered nonconcurrence.
    if (re.search(r"\bReconsider(?:ation)?\b.*\b(?:OTPA?|Ought to Pass|Third Reading|Final Passage)\b", a, re.I) and adopted) or \
            re.search(r"rescinded OT3rdg", a, re.I):
        return a, "reconsider"
    if re.search(r"House Concurs with Senate Amendment|Moved to Concur with the House Amendment", a) and adopted:
        return "CONCURRED", "concur"
    if re.match(r"Conference Committee Report\b", a) and re.search(r"\bAdopted\b", a) and not re.search(r"\bMF\b|Not Adopted|Rejected", a):
        return f"CCR ADOPTED {HOUSE[h].upper()}", "ccr"
    if re.match(r"Enrolled(?: Adopted)?\b", a) and not re.match(r"Enrolled Bill Amendment", a):
        return "ENROLLED", "enroll"
    if re.match(r"Signed by (?:the )?Governor", a):
        return "SIGNED", "sign"
    if re.match(r"Law Without Signature|Enacted in accordance with Article", a, re.I):
        return a, "nosign"
    if re.match(r"Vetoed by (?:the )?Governor", a):
        return "VETOED", "veto"
    if re.search(r"Veto Overridden", a) and not re.search(r"Sustained", a):
        return "VETO OVERRIDDEN", "override"
    return a, ""


# Within a day: the house of origin's steps, then the other house's, then the steps between the houses, enrollment, the
# governor and overrides; within each, the clerks' entry order (which isn't reliable across the two houses: HB 10 of
# 2025's concurrence was entered before the Senate's passage).
GROUP = {"concur": 2, "ccr": 2, "enroll": 3, "sign": 4, "nosign": 4, "veto": 4, "override": 5}
# And within a house's day: referral, the committee's report, amendments and motions, the vote, a second referral.
PHASE = {"intro": 0, "report": 1, "report-otp": 1, "report-kill": 1, "retain": 1, "pass": 3, "kill": 3, "reconsider": 3.5, "refer": 4, "waive": 5}
BETWEEN = re.compile(r"Non-?Concur|Request(?:s)? (?:for )?(?:a )?(?:CofC|Committee of Conference)|Accedes|Conferee|Appoints|Conference Committee", re.I)


def entry_time(s):
    try:
        return datetime.strptime(text(s), "%m/%d/%Y %I:%M:%S %p").isoformat()
    except ValueError:
        return ""


def clean_title(t):
    """"(New Title) establishing a parental bill of rights." -> "Establishing a parental bill of rights"."""
    t = re.sub(r"^\((?:\w+ )?New Title\)\s*", "", text(t), flags=re.I)  # also "(Second New Title)"
    return t[:1].upper() + t[1:]


def bill_rows(session):
    """The session's bills and CACRs: (LSRs row, number, Docket rows, sponsor rows, carried over to the next year?)."""
    f = P.first_year(session)
    lsrs = [(r, False) for r in rows(os.path.join(P.DATA, str(f), f"LSRs_{session}.txt"))]
    docket_years = [session]
    if session % 2:
        # The first year's bills kept over to the second: in the second year's files ("25-0010").
        nxt = [(r, True) for r in rows(os.path.join(P.DATA, str(f), f"LSRs_{session + 1}.txt"))
               if len(r) > 8 and r[8].startswith(f"{session % 100:02d}-")]
        lsrs += nxt
        docket_years.append(session + 1)
    else:
        docket_years.insert(0, session - 1)  # a carried bill's roll calls of the first year
    dockets = defaultdict(list)
    for y in set(docket_years):
        for r in rows(os.path.join(P.DATA, str(f), f"Docket_{y}.txt")):
            if len(r) >= 6:
                dockets[(int(r[0]), r[3].replace(" ", "").upper())].append(r)
    sponsors = defaultdict(list)
    for y in set(docket_years):
        for r in rows(os.path.join(P.DATA, str(f), f"LsrSponsors_{y}.txt")):
            if len(r) >= 5 and r[1].strip().isdigit():
                sponsors[(int(r[0]), int(r[1]))].append(r)
    out = []
    for r, carried in lsrs:
        if len(r) < 30 or r[4] not in KINDS or not r[10].strip():
            continue
        n = re.sub(r"\D", "", r[10])
        if not n:
            continue
        p = number(r[4], r[3] or "H", n)
        y = int(r[0])
        out.append((r, p, dockets.get((y, r[10].replace(" ", "").upper()), []), sponsors.get((y, int(r[1]))) or [], carried))
    return out


def roll_calls(session):
    """Each floor roll call on a bill: bill number -> [(house, date and time, question, yeas, nays, vote key)], and each
    vote's members: (year, house, vote number) -> [(PersonID, vote)]. A carried bill's first-year roll calls too."""
    f = P.first_year(session)
    years = [session] + ([session - 1] if session % 2 == 0 else [])
    by_bill, members = defaultdict(list), defaultdict(list)
    for y in years:
        for r in rows(os.path.join(P.DATA, str(f), f"RollCallSummary_{y}.txt")):
            if len(r) < 12 or not r[4].strip():
                continue
            by_bill[r[4].replace(" ", "").upper()].append((r[1], r[3], text(r[11]), int(r[5] or 0), int(r[6] or 0), (y, r[1], r[2])))
        for r in rows(os.path.join(P.DATA, str(f), f"RollCallHistory_{y}.txt")):
            if len(r) >= 7 and (r[4].strip().isdigit() or r[3].strip().isdigit()):
                # Three 2023-24 representatives have only an employee number (no PersonID): kept by that number.
                members[(y, r[1], r[2])].append((int(r[4]) if r[4].strip().isdigit() else f"#{r[3].strip()}", r[6].strip()))
    return by_bill, members


# A roll call's question where "yea" is a vote for the bill: passage (the House's OTP and OTPA; the Senate's "Ought to
# Pass"), concurring, adopting a conference report, and overriding a veto. Not amendments, tabling, ITL or parts of a
# divided question.
FOR_BILL = re.compile(r"^(?:OTP|OTPA|Ought [Tt]o Pass(?: w/ ?Amendment| with Amendment)?|Concur|Adopt CofC Report|"
                      r"Conference Committee Report|Veto Override|VETO MESSAGE.*)$")
VOTE_CODES = {"Nay": "N", "Not Voting/Excused": "E", "Not Voting/Not Excused": "A", "Presiding": "Presiding"}


def bill_link(p, session, lsr, carried):
    """The bill's status page on gc.nh.gov (a kept-over bill's is under the second year)."""
    sy = session + 1 if carried else session
    return (f"https://gc.nh.gov/bill_status/legacy/bs2016/bill_status.aspx?lsr={int(lsr)}&sy={sy}"
            f"&txtsessionyear={sy}&txtbillnumber={official(p)}")


def load_session(session):
    """Read one year's bills and return (records, bill number -> record index, fetched time, delegation)."""
    f = P.first_year(session)
    parties = _PARTIES.setdefault(session, {})
    who = people(f)
    seats = seat_ids(f) if f == P.first_year(CURRENT) else {}
    subjects = subject_codes(f)
    rc_by_bill, rc_members = roll_calls(session)
    paths = glob.glob(os.path.join(P.DATA, str(f), f"*_{session}.txt")) + glob.glob(os.path.join(P.DATA, str(f), f"*_{session + 1}.txt"))
    fetched = datetime.fromtimestamp(max(os.path.getmtime(x) for x in paths), ZoneInfo(P.TIMEZONE)).strftime("%Y-%m-%d %H:%M")
    recs, index = [], {}
    for r, p, docket, sps, carried in sorted(bill_rows(session), key=lambda x: (x[1][0], x[1][1], int(re.sub(r"\D", "", x[1])))):
        origin = p[0]
        other = "S" if origin == "H" else "H"
        amendment = "CACR" in p
        steps = []  # (date, house, shared wording, as written, kind, entry time)
        for d in docket:
            a = text(d[5])
            h = d[4] if d[4] in HOUSE else origin
            day = iso(a) or iso(d[2])
            if iso(d[2]) and abs((datetime.fromisoformat(iso(d[2])) - datetime.fromisoformat(day)).days) > 180:
                day = iso(d[2])  # a slip in the line's date ("04/13/2022" in HB 49 of 2023, "03/06/2035" in HB 425 of 2025)
            if re.match(r"(?:Signed by|Vetoed by|Law Without|Enacted in accordance)", a, re.I):
                h = "G"
            t, kind = decode(a, h if h in HOUSE else origin)
            steps.append((day, h, t, a, kind, entry_time(d[2])))
        if carried:
            steps = [s for s in steps if s[0] <= f"{session}-12-31"]  # the first year's page: its own year's lines
        if carried:
            # Up to the line that kept it over (the committee's fall work is for the second year).
            kept = [s[0] for s in steps if s[4] == "retain"]
            steps = [s for s in steps if not kept or s[0] <= max(kept)]
        group = lambda s: GROUP.get(s[4], 2 if BETWEEN.search(s[3]) else 0 if s[1] == origin else 1)
        steps.sort(key=lambda s: (s[0], group(s), PHASE.get(s[4], 2), s[5]))
        passed, killed, tabled, enrolled = set(), None, False, set()
        concurred, ccr, retained = False, set(), False
        plain_second = False  # the second house passed it without amending it
        amended_second = False
        where_h, place, comm = origin, "desk", None
        refs, first_report = [], None
        pass_days = {"H": [], "S": []}  # the passages that stood (not a vote the house then sent to Finance or undid)
        sent_on = {}  # a house's passage set aside by a second referral, back if that committee waives it
        last_pass, set_aside = {}, set()  # step indexes: a house's latest passage; passages a second referral set aside
        for i, (day, h, t, a, kind, _) in enumerate(steps):
            if h == other and re.search(r"(?:Amendment\b.*[:,]\s*AA\b|with Amendment.*\bMA\b)", a):
                amended_second = True
            if kind in ("intro", "refer"):
                c = t[len("REFERRED TO "):]
                refs.append((h, c))
                where_h, place, comm = h, "committee", c
                if kind == "refer" and h in passed:
                    sent_on[h] = pass_days[h]
                    set_aside.add(last_pass.get(h))
                passed.discard(h)  # a house that adopted a report and sent the bill on hasn't passed it yet
                pass_days[h] = []
                retained = False
            elif kind.startswith("report"):
                place = "floor"
                if first_report is None:
                    first_report = kind
            elif kind == "waive" and sent_on.get(h):
                set_aside.discard(last_pass.get(h))
                passed.add(h)
                pass_days[h] = sent_on.pop(h)
                place, comm = "desk", None
                where_h = other if h == origin else origin
            elif kind == "retain":
                retained = True
            elif kind == "pass":
                last_pass[h] = i
                passed.add(h)
                pass_days[h].append(day)
                killed = None
                if h != origin:
                    plain_second = not amended_second and not re.search(r"with Amendment|w/ ?Amendment", a, re.I)
                place, comm = "desk", None
                where_h = other if h == origin else origin
            elif kind == "kill":
                killed = h
                passed.discard(h)
                pass_days[h] = []
            elif kind == "reconsider":
                passed.discard(h)
                pass_days[h] = []
                killed = None
            elif kind == "table":
                tabled = True
            elif kind == "untable":
                tabled = False
            elif kind == "concur":
                concurred = True
            elif kind == "ccr":
                ccr.add(h)
            elif kind == "enroll":
                enrolled.add(h)
        # A vote the house then sent to Finance (or Ways and Means) isn't its passage yet: shown as written ("Ought to Pass
        # with Amendment 2023-0304h: MA RC 184-179 ..."), not "PASSED HOUSE" (HB 565 of 2023).
        steps = [(d_, h_, a_ if j in set_aside else t_, a_, k_, e_) for j, (d_, h_, t_, a_, k_, e_) in enumerate(steps)]
        kinds = {s[4] for s in steps}
        # The LSRs file's chapter number; the history line's has slips (SB 62 of 2025 says "Chapter 0039", HB 511's).
        chapter = (int(r[11]) if r[11].strip().isdigit() else None) or next((int(m.group(1)) for s in steps for m in [re.search(r"Chapter\s+(\d+)", s[3])] if m and s[4] in ("sign", "nosign")), None)
        overridden = {s[1] for s in steps if s[4] == "override"}
        # Passed both houses: enrolled, the first house agreed to the second's changes, both adopted a conference report,
        # or the second house passed it unchanged.
        # (An enrollment line on a bill that didn't pass both houses is a clerk's slip: SB 286 of 2025, killed in the Senate.)
        both = len(passed) == 2 and (bool(enrolled) or concurred or ccr >= {"H", "S"} or plain_second)
        if enrolled and not both:
            steps = [(d_, h_, a_ if k_ == "enroll" else t_, a_, "" if k_ == "enroll" else k_, e_) for d_, h_, t_, a_, k_, e_ in steps]
        if amendment:
            stage = 3 if both else (2 if passed else None)
        elif "sign" in kinds or "nosign" in kinds or {"H", "S"} <= overridden:
            stage = 5
        elif "veto" in kinds:
            stage = 6
        elif both and (enrolled >= {"H", "S"} or (enrolled and session < CURRENT)):
            stage = 4
        elif both:
            stage = 3
        elif passed:
            stage = 2
        else:
            stage = None
        if stage is not None and stage >= 3:
            passed = {"S", "H"}
        dead_here = killed is not None and stage is None  # killed in its own house
        if stage is None:
            stage = 1 if place == "floor" and not dead_here else 0
        proper = lambda c: re.sub(r"(?<=\s)(And|Of|The|On|For|To|In)\b", lambda m: m.group(1).lower(), c.title())
        refs = [(h, proper(c)) for h, c in refs]
        comm = proper(comm) if comm else None
        comm_list = sorted({f"{h} · {c}" for h, c in refs})
        raw = clean_title(r[2])
        # The title is one or two sentences: "relative to X." and, for CACRs and some bills, "Providing that ...".
        first, _, rest = raw.partition(". ")
        title = first.rstrip(".")
        summary = rest.strip() if rest else ""
        if amendment:
            title = "Constitutional amendment " + title[:1].lower() + title[1:]
        subj = P.SUBJECT_TOPICS.get(r[12].strip()) if len(r) > 12 else None
        topics = list(dict.fromkeys((["const"] if amendment else []) + ([subj] if subj else []) +
                                    [P.COMMITTEE_TOPICS[c] for _, c in refs if c in P.COMMITTEE_TOPICS] +
                                    [k for k in P.TOPIC_WORDS if P.TOPIC_WORDS[k].search(title)]))
        # A bill's first committee: approved ("Ought to Pass"), voted down (ITL or interim study), or neither (kept over
        # to the next year, or never reported).
        left = first_report == "report-otp" or bool(passed)
        fate = "passed" if left else "defeated" if first_report == "report-kill" or (killed and not passed) else "none"
        names = []
        for s in sorted(sps, key=lambda s: (s[4].strip() != "1", int(s[2]) if s[2].strip().isdigit() else 99)):
            m = who.get(int(s[3])) if s[3].strip().isdigit() else None
            if not m or m["name"] in names:
                continue
            names.append(m["name"])
            if m["party"] in ("D", "R"):
                parties[(m["house"], m["name"])] = m["party"]
        sponsor = names[0] if names else "—"
        prime = next((who.get(int(s[3])) for s in sps if s[4].strip() == "1" and s[3].strip().isdigit()), None)
        cos = names[1:]
        if stage == 0:
            desc = "Killed" if dead_here else f"In {HOUSE[where_h]} committee"
        elif stage == 1:
            desc = f"On the {HOUSE[where_h]} floor"
        else:
            desc = {2: f"Passed the {HOUSE[origin] if origin in passed else HOUSE[other]}", 3: "Passed both houses",
                    4: "On the governor's desk", 5: "Became law", 6: "Vetoed"}[stage]

        def dates(test, mode="last"):
            ds = sorted({s[0] for s in steps if test(s[1], s[2], s[4]) and s[0]})
            return {"first": ds[0], "last": ds[-1], "all": ";".join(ds)}[mode] if ds else ""

        votes = []
        for h, when, question, yes, no, key in rc_by_bill.get(official(p), []):
            if h not in HOUSE or not FOR_BILL.match(question):
                continue
            if carried and iso(when) > f"{session}-12-31":
                continue
            ny = []
            for pid, v in rc_members.get(key, []):
                code = VOTE_CODES.get(v)
                if not code:
                    continue
                sid = seats.get(pid) or (f"{h}?{who[pid]['name']}" if pid in who else f"{h}?Member {pid}")
                if sid:
                    ny.append([sid, code])
            votes.append((entry_time(when) or iso(when), [h, "F", None, iso(when), yes, no, ny]))
        votes = [v for _, v in sorted(votes, key=lambda x: x[0])]
        action_dates = [s[0] for s in steps if s[0]]
        lsr = r[1]
        rec = {
            "nums": [p], "base": [p], "prev": earlier(session, p, r, prime["name"] if prime else "", carried=not carried and session % 2 == 0 and r[8][:3] == f"{(session - 1) % 100:02d}-"),
            "title": title, "summary": summary, "act": "", "lawCode": "", "law": None, "laws": [],
            "comms": comm_list, "topics": topics, "places": [], "narrow": P.narrow_kind(title),
            "commFate": fate, "mainTopic": topics[0] if topics else "", "local": "local" in topics,
            "senDeleg": False, "asmDeleg": False, "budget": bool(re.search(r"\bstate budget\b|\boperating budget\b|making appropriations for the expenses", raw, re.I)),
            "shell": False,
            "passedS": "S" in passed, "passedA": "H" in passed, "program": None,
            "stage": stage, "passedIn": (HOUSE[origin] if origin in passed else HOUSE[other]) if stage == 2 else None,
            "chapter": chapter if stage == 5 else None,
            "veto": None, "memo": "", "vetoMemo": None,
            "simText": f"{title} {summary}",
            "comm": comm if stage == 0 and place == "committee" and not dead_here else None,
            "first": min(action_dates, default=f"{session}-01-01"),
            "last": max(action_dates, default=f"{session}-01-01"),
            "cosp": len(cos),
            "keyDates": [
                dates(lambda h, t, k: k == "report-otp", "first"),
                ";".join(sorted(set(pass_days["S"]))) if "S" in passed else "",
                ";".join(sorted(set(pass_days["H"]))) if "H" in passed else "",
                "",
                # Both houses adopting the enrolled bills report (the day it's presented to the governor isn't recorded).
                dates(lambda h, t, k: k == "enroll") if stage >= 4 and not amendment else "",
                dates(lambda h, t, k: k in ("sign", "nosign")) or (dates(lambda h, t, k: k == "override") if stage == 5 else ""),
                dates(lambda h, t, k: k == "veto"),
            ],
            "votes": votes, "firstComms": [(refs[0][0], refs[0][1], left)] if refs else [],
            "vers": [{"p": p, "sponsor": sponsor, "district": (prime["county"] * 100 + prime["district"] if prime and prime["house"] == "H" else prime["district"] if prime else 0),
                      "cosponsors": cos, "primes": 1, "cosp": len(cos),
                      "statusDesc": desc, "committee": comm if place == "committee" and stage in (0, 2) and not dead_here else None,
                      "actions": [[s[0], s[2] if s[2].isupper() else s[3]] for s in steps],
                      "link": bill_link(p, session, lsr, carried)}],
        }
        index[p] = len(recs)
        recs.append(rec)
    return recs, index, fetched, {"SENATE": [], "ASSEMBLY": []}


# ---- The same bill in earlier years: a kept-over bill is the first year's bill under the same number; otherwise the
# same title ("relative to the state's mental health system") with the same prime sponsor, or a title only one bill has
# in each year. Never a bill that became law (yearly bills share titles: "making appropriations for capital
# improvements").
_TITLES = {}


def _titles(session):
    if session not in _TITLES:
        out = defaultdict(list)
        who = people(P.first_year(session))
        for r, p, docket, sps, carried in bill_rows(session):
            if r[11].strip() or carried:
                continue
            prime = next((who[int(s[3])]["name"] for s in sps if s[4].strip() == "1" and s[3].strip().isdigit() and int(s[3]) in who), "")
            out[clean_title(r[2]).partition(". ")[0].rstrip(".").lower()].append((p, prime))
        _TITLES[session] = out
    return _TITLES[session]


def earlier(session, p, r, prime="", carried=False):
    out = {(session - 1, p)} if carried and session - 1 in sessions() else set()
    k = clean_title(r[2]).partition(". ")[0].rstrip(".").lower()
    if len(k.split()) < 4:
        return out
    for y in (session - 1, session - 2):
        if y not in sessions() or (carried and y == session - 1):
            continue
        old = _titles(y).get(k, [])
        same = [n for n, sp in old if sp and sp == prime]
        if same:
            out.add((y, same[0]))
        elif len(old) == 1 and len(_titles(session).get(k, [])) <= 1:
            out.add((y, old[0][0]))
    return out


def agendas(session):
    """Bills set for a hearing (the LSRs file's next hearing: committee, time): bill -> [["House Judiciary",
    "2026-02-03T10:00:00"]], for the current session."""
    if session != CURRENT:
        return {}
    names = committee_names(P.first_year(session))
    out = {}
    for r, p, docket, sps, carried in bill_rows(session):
        if len(r) < 32 or not r[30].strip() or not r[31].strip():
            continue
        try:
            when = datetime.strptime(text(r[31]), "%m/%d/%Y %I:%M:%S %p").isoformat()
        except ValueError:
            continue
        code = r[30].strip().upper()
        name = names.get(code)
        if name and code[0] in HOUSE:
            out.setdefault(p, []).append([f"{HOUSE[code[0]]} {name}", when])
    return out


def parties(session, recs):
    return {k: v for k, v in _PARTIES.get(session, {}).items() if v in ("D", "R")}
