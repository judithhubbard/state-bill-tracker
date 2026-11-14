"""Nebraska's bills (downloaded by states/ne/fetch.py from nebraskalegislature.gov) in the shape build_data.py reads. A page
per two-year Legislature (2025 is the 109th, 2025-26). Every LB, every A bill ("LB 304A") and every proposed constitutional
amendment ("LR 19CA"); other resolutions are left out.

Nebraska has one house, so the shared code's houses are one: "L", the Legislature (P.LOWER). A bill passes when it
passes on Final Reading; there's no second house. Each bill's page (data/ne/<year>/bills/LB7.html) has its one-line title,
its primary introducer (a senator, linked by id, or a committee), and the history, newest first, with a link to each
recorded vote. The steps:
- "Referred to Judiciary Committee" (by the Reference Committee, the Executive Board), "Notice of hearing for ...". Every
  bill gets a public hearing. A committee advances a bill by placing it on General File ("Placed on General File with
  AM77": with its amendment), or kills it ("Indefinitely postponed" while the bill is in committee); most bills just stay.
- General File is the first round of floor debate: "Advanced to Enrollment and Review Initial" (a vote to advance; a
  filibuster there takes a cloture motion, 33 votes, to end), then "Placed on Select File" (the second round), "Advanced
  to Enrollment and Review for Engrossment", "Placed on Final Reading", "Passed on Final Reading 47-0-2" (yes, no, not
  voting; "with Emergency Clause" needs 33). "Returned to Select File for specific amendment" goes back a round.
- "President/Speaker signed", "Presented to Governor on April 10, 2026", "Approved by Governor on April 14, 2026",
  "Approved by Governor with line-item veto on ...", "Returned by Governor without approval on ..." (a veto), "Became law
  without Governor's signature", "Failed to become law notwithstanding the objections of the Governor 27-20-2" (an override
  that failed: it takes 30). The governor's lines are listed days late; their own wording dates them.
- "Indefinitely postponed": killed, by the committee or on the floor; on the second session's last day every bill still
  pending is indefinitely postponed (about 900 a Legislature): those just ran out of time.
- Motions are numbered ("Hunt MO506 Bracket until June 2, 2023 filed", then "MO506 prevailed"): a bracket or an
  indefinite postponement that prevails kills the bill; a recommittal sends it back to committee; cloture ("Invoke cloture
  pursuant to Rule 7, Sec. 10") ends debate, and when it fails the bill is set aside, usually for good.
- "Provisions/portions of LB80 amended into LB814 by AM915": a bill's text carried into another (Nebraska passes much of
  its work that way); shown on both bills.
- "Ballard priority bill", "Judiciary priority bill", "Speaker priority bill", "Speaker Major Proposal": each senator may
  name one priority bill a session, each committee two, and the Speaker 25; priority bills are the ones debated first.
- "Ballard name added": a co-sponsor (the introducer is the only sponsor the page names otherwise).
Laws and vetoes are checked against the Clerk's worksheets (worksheets/r1.pdf, r2.pdf), the official tallies: `checks()`.

Votes: each recorded vote member by member (votes/<KeyID>.json, linked from its history line). Kept: the bill's own votes
(advancing from General File and Select File, passing on Final Reading, cloture on it, overriding a veto), as floor votes
labelled with their round; amendments' and other motions' votes are left out. "What it does" isn't shown: the only plain
summary is the introducer's statement of intent, a PDF that isn't downloaded.
"""
import html as H_, json, os, re, shutil, subprocess
from collections import Counter, defaultdict
from datetime import date, datetime
from zoneinfo import ZoneInfo

from states.ne import profile as P

H = "L"  # the only house
HOUSE = {"L": "Legislature"}
SEATS = 49
_CACHE = {}


def folder(session):
    return os.path.join(P.DATA, str(session))


def sessions():
    out = []
    for f in sorted(os.listdir(P.DATA)) if os.path.isdir(P.DATA) else []:
        if re.fullmatch(r"\d{4}", f) and os.path.exists(os.path.join(P.DATA, f, "list.json")) \
                and os.path.isdir(os.path.join(P.DATA, f, "bills")):
            out.append(int(f))
    return out


def listing(session):
    key = (session, "list")
    if key not in _CACHE:
        try:
            _CACHE[key] = json.load(open(os.path.join(folder(session), "list.json"), encoding="utf-8"))
        except (OSError, ValueError):
            _CACHE[key] = {}
    return _CACHE[key]


def text(fragment):
    return re.sub(r"\s+", " ", H_.unescape(re.sub(r"<[^>]+>", " ", fragment or ""))).strip()


MONTHS = {m: i for i, m in enumerate(("January", "February", "March", "April", "May", "June", "July", "August",
                                      "September", "October", "November", "December"), 1)}


def iso(d):
    """"Feb 26, 2025" or "February 26, 2025" -> "2025-02-26"; "" when it isn't a date."""
    m = re.match(r"([A-Z][a-z]+)\.? (\d{1,2}), (\d{4})", (d or "").strip())
    if not m:
        return ""
    mon = next((i for k, i in MONTHS.items() if k.startswith(m.group(1)[:3])), None)
    return f"{m.group(3)}-{mon:02d}-{int(m.group(2)):02d}" if mon else ""


def label(key):
    """"LB304A" -> "LB 304A"."""
    return re.sub(r"^(LB|LR)", r"\1 ", key)


# ---- Reading a bill's page ----

def parse(session, key):
    """A bill page -> {key, title, introducer (name), senator (id or None), committee (name or None), rows [(date, line,
    vote KeyID or None)] oldest first} or None when it's missing."""
    path = os.path.join(folder(session), "bills", f"{key}.html")
    try:
        s = open(path, encoding="utf-8").read()
    except OSError:
        return None
    m = re.search(r"<h2>(.*?)</h2>", s, re.S)
    head = text(m.group(1)) if m else ""
    title = re.sub(rf"^{re.escape(key)}\s*-\s*", "", head)
    m = re.search(r'<li>Introduced By:\s*<a href="/bills/search_by_introducer\.php\?(Introducer|Committee)=(\d+)"[^>]*>(.*?)</a>(.*?)</li>', s, re.S)
    senator = committee = None
    intro, request = "", ""
    if m:
        intro = text(m.group(3))
        request = text(m.group(4))
        if m.group(1) == "Introducer":
            senator = int(m.group(2))
        else:
            committee = intro
    rows = []
    for d, body, rest in re.findall(r'<tr>\s*<td class="py-1">([A-Z][a-z]{2} \d\d, \d{4})</td>\s*<td class="py-1">(.*?)</td>(.*?)</tr>', s, re.S):
        k = re.search(r"KeyID=(\d+)", rest)
        rows.append((iso(d), text(body), int(k.group(1)) if k else None))
    rows.reverse()  # the page lists them newest first
    return {"key": key, "title": title, "introducer": intro, "senator": senator, "committee": committee,
            "request": request, "rows": rows}


def vote(session, key_id):
    path = os.path.join(folder(session), "votes", f"{key_id}.json")
    try:
        return json.load(open(path, encoding="utf-8"))
    except (OSError, ValueError):
        return None


# ---- Members ----

def members():
    """The current senators (data/ne/members/members.json): [{district, name, senator_id, room, phone, email, committees,
    photo, speaker}]."""
    if "members" not in _CACHE:
        try:
            raw = json.load(open(os.path.join(P.DATA, "members", "members.json"), encoding="utf-8")).get("members") or []
        except (OSError, ValueError):
            raw = []
        _CACHE["members"] = [m for m in raw if m.get("district") and m.get("name")]
    return _CACHE["members"]


def norm(s):
    return re.sub(r"[^a-z]", "", (s or "").lower())


def surname(name):
    """"R. Brad von Gillern" -> "von Gillern"; "Machaela Cavanaugh" -> "Cavanaugh"."""
    n = re.sub(r",?\s+(?:Jr|Sr|II|III|IV)\.?$", "", (name or "").strip())
    m = re.search(r"\b((?:von|van|de|del|la|le)\s+\S+)$", n, re.I)
    return m.group(1) if m else n.split()[-1] if n else ""


def by_id():
    return {m["senator_id"]: m for m in members() if m.get("senator_id")}


def seat_of_name(session, name):
    """A roll-call or history name ("Cavanaugh, J.", "von Gillern", "Meyer, F.", "Speaker Arch") -> "L:9", or "L?Linehan"
    for a senator who has left (only current senators are known)."""
    n = re.sub(r"^Speaker\s+", "", (name or "").strip().rstrip("*").strip())
    fix = P.VOTE_NAME_FIX.get((session, n))
    if fix:
        return fix
    m = re.match(r"(.+?),\s*([A-Z])\.?$", n)
    last, initial = (m.group(1), m.group(2)) if m else (n, "")
    hits = [x for x in members() if norm(surname(x["name"])) == norm(last) and (not initial or x["name"].startswith(initial))]
    if len(hits) == 1:
        return f"{H}:{hits[0]['district']}"
    return f"{H}?{n}"


# ---- Wording ----

def comm_name(c):
    """"Judiciary Committee" -> "Judiciary"; "the Education Committee" -> "Education"; "Executive Board" stays."""
    c = re.sub(r"\s+", " ", (c or "").strip())
    c = re.sub(r"^the\s+", "", c, flags=re.I)
    c = re.sub(r"\s+Committee$", "", c)
    c = re.sub(r"^Executive Board of the Legislative Council$", "Executive Board", c)
    return c.replace("Government, Military, and Veterans", "Government, Military and Veterans").strip(" .")


STANDING = None


def standing():
    """The committees' names as the committee pages give them (committees.json), for telling a committee's priority bill
    or amendment from a senator's."""
    global STANDING
    if STANDING is None:
        try:
            raw = json.load(open(os.path.join(P.DATA, "members", "committees.json"), encoding="utf-8")).get("committees") or []
        except (OSError, ValueError):
            raw = []
        STANDING = {comm_name(c["name"]) for c in raw if c.get("name")} | set(P.COMMITTEE_TOPICS) | {
            "Executive Board", "Legislature's Planning Committee", "Legislative Performance Audit", "State-Tribal Relations",
            "Legislative Oversight Committee", "Enrollment and Review", "Reference"}
    return STANDING


def who(name, session=None):
    """A name as a history line writes it ("Cavanaugh, M.", "Judiciary", "Speaker Arch") -> "Sen. Machaela Cavanaugh" (a
    current senator's full name; a former one's as written), "the Judiciary Committee", "Speaker Arch"."""
    name = name.strip()
    if comm_name(name) in standing() or re.search(r"Committee|Board", name):
        c = comm_name(name)
        return f"the {c}" + ("" if re.search(r"Board|Committee|Audit$", c) else " Committee")
    if name.startswith("Speaker"):
        return name
    sid = seat_of_name(session, name) if session else ""
    full = next((x["name"] for x in members() if f"{H}:{x['district']}" == sid), None) if sid and "?" not in sid else None
    return f"Sen. {full or name}"


ROUNDS = {"General File": "General File", "Select File": "Select File", "Final Reading": "Final Reading"}
CLOTURE_NEED = 33


def motion_kind(desc):
    """What a numbered motion does, from its description: "bracket", "ipp", "recommit", "cloture", "override", "return",
    "reconsider", "other"."""
    d = desc.lower()
    if "cloture" in d:
        return "cloture"
    if d.startswith("bracket"):
        return "bracket"
    if "indefinitely postpone" in d:
        return "ipp"
    if d.startswith("recommit"):
        return "recommit"
    if "notwithstanding the objections" in d or "override" in d:
        return "override"
    if "return to select file" in d or "return to select" in d:
        return "return"
    if d.startswith("reconsider"):
        return "reconsider"
    return "other"


def plain_motion(desc):
    """"Bracket until June 2, 2023" -> "to bracket it until June 2, 2023"; "Indefinitely postpone pursuant to Rule 6 Section
    3(f)" -> "to kill it (indefinitely postpone)"."""
    k = motion_kind(desc)
    if k == "bracket":
        return "to set it aside (bracket it) " + re.sub(r"^bracket\s*", "", desc, flags=re.I).strip()
    if k == "ipp":
        return "to kill it (indefinitely postpone)"
    if k == "recommit":
        m = re.search(r"to (?:the )?(.+?)(?: Committee)?$", desc, re.I)
        return f"to send it back to the {comm_name(m.group(1)) if m else ''} Committee".replace("the  Committee", "committee")
    if k == "cloture":
        return "to end debate and vote (cloture, 33 votes)"
    if k == "override":
        return "to override the governor's veto" if "line-item" not in desc.lower() else "to override part of the governor's line-item veto"
    if k == "return":
        return "to return it to Select File for an amendment"
    if k == "reconsider":
        return "to reconsider a vote"
    return f"“{desc}”"


VOTE_CODE = {"No": "N", "Present Not Voting": "B", "Absent Not Voting": "A", "Excused Not Voting": "E"}


def roll(session, v):
    """A vote file -> (yes, no, [[seat, code], ...]) with "Yes" left out."""
    t = v.get("totals") or {}
    listed = []
    for name, how in v.get("members") or []:
        code = VOTE_CODE.get(how)
        if code:
            listed.append([seat_of_name(session, name), code])
    return int(t.get("Yes") or 0), int(t.get("No") or 0), listed


def tally_of(line):
    """"Passed on Final Reading 29-20*-0" -> (29, 20, 0)."""
    m = re.search(r"(\d+)-(\d+)\*?-(\d+)\s*$", line)
    return (int(m.group(1)), int(m.group(2)), int(m.group(3))) if m else None


# ---- One bill ----

def link_of(session, k):
    """The Legislature's page for a bill, by the DocumentID the bill list keeps."""
    doc = (listing(session).get("bills") or {}).get(k)
    return f"https://nebraskalegislature.gov/bills/view_bill.php?DocumentID={doc}" if doc else ""


def last_day(session):
    """The Legislature's last day: the second session's adjournment, when every pending bill is indefinitely postponed."""
    return P.LAST_DAY.get(session + 1, "")


def record(session, b):
    k = b["key"]
    const = k.endswith("CA")
    abill = bool(re.fullmatch(r"LB\d+A", k))
    main = label(k[:-1]) if abill else ""
    steps = []  # (date, house or "G", wording, kind)
    place, rnd, comm = "desk", None, None  # where it is: desk (introduced), committee, floor (with its round), done
    refs, first_ref = [], None
    reported = passed = enrolled = sent = law = vetoed = items = overridden = to_sos = False
    killed = None  # (date, how) when it was killed before the end
    ended = None  # the Legislature ended it
    first_report = False
    commfate = "none"
    motions = {}  # "MO506" -> description
    cosponsors, withdrawn = [], set()
    priority = []
    into, merged = [], []  # bills its text went into; bills whose text came into it
    fvotes = []
    gov_day = None
    end = last_day(session)

    def add(d, t, kind="other", h=H):
        steps.append((d, h, t, kind))

    def floor_vote(key, round_name, d):
        v = vote(session, key) if key else None
        if not v:
            return None
        y, n, listed = roll(session, v)
        fvotes.append([H, "F", round_name, d or iso(v.get("date")), y, n, listed])
        return y, n

    for d, t, key in b["rows"]:
        tl = t.lower()
        if t == "Date of introduction":
            add(d, "Introduced", "intro")
            continue
        m = re.match(r"(Re)?referred to (.+)$", t, re.I)
        if m:
            c = comm_name(m.group(2))
            comm, place = c, "committee"
            refs.append(c)
            if first_ref is None:
                first_ref = c
            add(d, f"REFERRED TO {c.upper()}", "ref")
            if m.group(1):
                add(d, f"Sent to another committee: the {c} Committee", "rereferred")
            continue
        m = re.match(r"Notice of hearing for (.+?)(\s*\(cancel(?:ed)?\))?$", t)
        if m:
            add(d, f"Public hearing set for {m.group(1)}" + (" (canceled)" if m.group(2) else ""), "hearing")
            continue
        m = re.match(r"Place[d]? on General [Ff]ile(?: with (.+))?$", t)
        if m:
            if place == "committee" and comm:
                reported, first_report, commfate = True, first_report or comm == first_ref, "passed"
                add(d, "REPORTED", "reported")
                add(d, f"The {comm} Committee advanced it to General File" + (" with its amendment" if m.group(1) else ""), "report")
            else:
                add(d, "Placed on General File", "gf")
            place, rnd, comm = "floor", "General File", None
            continue
        if re.match(r"(?:Re)?[Aa]dvance[d]? (?:to|for) Enrollment and Review Initial", t):
            tl_ = floor_vote(key, "General File", d)
            add(d, "Advanced from General File (first-round debate)" + (f", {tl_[0]}-{tl_[1]}" if tl_ else ""), "advance1")
            place, rnd = "floor", "Select File"
            continue
        if re.match(r"Failed to advance to Enrollment and Review Initial", t):
            tl_ = floor_vote(key, "General File", d)
            add(d, "Failed to advance from General File" + (f", {tl_[0]}-{tl_[1]}" if tl_ else ""), "failadvance")
            continue
        if re.match(r"Placed on Select File", t):
            place, rnd = "floor", "Select File"
            add(d, "Placed on Select File (second-round debate)", "sf")
            continue
        if re.match(r"(?:Re)?[Aa]dvance[d]? (?:to|for) Enrollment and Review (?:for )?(?:Re)?[Ee]ngross", t):
            tl_ = floor_vote(key, "Select File", d)
            add(d, "Advanced from Select File" + (f", {tl_[0]}-{tl_[1]}" if tl_ else ""), "advance2")
            place, rnd = "floor", "Final Reading"
            continue
        if re.match(r"Failed to advance to Enrollment and Review for Engrossment", t):
            tl_ = floor_vote(key, "Select File", d)
            add(d, "Failed to advance from Select File" + (f", {tl_[0]}-{tl_[1]}" if tl_ else ""), "failadvance")
            continue
        if re.match(r"Placed on Final Reading", t):
            place, rnd = "floor", "Final Reading"
            add(d, "Placed on Final Reading", "fr")
            continue
        if re.match(r"Returned to Select File", t):
            place, rnd = "floor", "Select File"
            add(d, "Returned to Select File for an amendment", "return")
            continue
        if re.match(r"Failed to return to Select File", t):
            add(d, "A motion to return it to Select File failed", "other")
            continue
        m = re.match(r"(Passed|Failed) on Final Reading(.*)$", t)
        if m:
            tl3 = tally_of(t)
            v = floor_vote(key, "Final Reading", d)
            y, n = (v if v else tl3[:2]) if (v or tl3) else (None, None)
            if not v and tl3:
                fvotes.append([H, "F", "Final Reading", d, tl3[0], tl3[1], []])
            extra = " with the emergency clause" if re.search(r"with Emergency Clause(?! stricken)", t) else \
                " without the emergency clause" if "stricken" in t else " for the general election ballot" if "General Election" in t else ""
            if m.group(1) == "Passed":
                passed = True
                place = "done"
                add(d, "PASSED LEGISLATURE", "pass")
                add(d, f"Passed on Final Reading{extra}" + (f", {y}-{n}" if y is not None else ""), "tally")
            else:
                add(d, f"Failed on Final Reading{extra}" + (f", {y}-{n}" if y is not None else ""), "failfinal")
            continue
        if re.match(r"President/Speaker signed|Correctly enrolled", t):
            enrolled = True
            add(d, "Signed by the Speaker and the presiding officer", "enrolled")
            continue
        m = re.match(r"Presented to (Governor|Secretary of State) (?:on\s+)?(.+)$", t)
        if m:
            dd = iso(m.group(2)) or d
            if m.group(1) == "Governor" and not const:
                sent = True
                add(dd, "DELIVERED TO GOVERNOR", "sent", "G")
            else:
                to_sos = True
                add(dd, "Sent to the Secretary of State for the voters at the next general election", "sos", "G")
            continue
        m = re.match(r"Approved by Governor( with line-item veto)? on (.+)$", t)
        if m:
            dd = iso(m.group(2)) or d
            gov_day = dd
            law = True
            if m.group(1):
                items = True
                add(dd, "SIGNED BY GOVERNOR, with a line-item veto", "signed", "G")
            else:
                add(dd, "SIGNED BY GOVERNOR", "signed", "G")
            continue
        m = re.match(r"Returned by Governor without approval(?: on (.+))?$", t)
        if m:
            dd = iso(m.group(1) or "") or d
            vetoed, gov_day = True, dd
            add(dd, "VETOED", "vetoed", "G")
            continue
        m = re.match(r"Bec(?:ame|omes) law without (?:the )?Governor's signature(?: on (.+))?$", t)
        if m:
            dd = iso(m.group(1) or "") or d
            law, gov_day = True, dd
            add(dd, "Became law without the governor's signature", "nosign", "G")
            continue
        m = re.match(r"(Failed to become law|Passed|Became law) notwithstanding the objections of the Governor(.*)$", t)
        if m:
            tl3 = tally_of(t)
            v = floor_vote(key, "Override", d)
            y, n = (v if v else tl3[:2]) if (v or tl3) else (None, None)
            if not v and tl3:
                fvotes.append([H, "F", "Override", d, tl3[0], tl3[1], []])
            if m.group(1).startswith("Failed"):
                add(d, f"The Legislature failed to override the veto" + (f", {y}-{n} (30 votes needed)" if y is not None else ""), "override")
            else:
                overridden = law = True
                add(d, "Became law over the governor's veto" + (f", {y}-{n}" if y is not None else ""), "overridelaw")
            continue
        if re.match(r"Indefinitely postponed$|Bill stands indefinitely postponed", t, re.I) or \
                re.match(r"Motion to suspend rules to indefinitely postpone prevailed", t):
            if passed or law:
                add(d, t, "other")
            elif d == end and not killed:
                ended = d
                add(d, "Died when the Legislature adjourned (indefinitely postponed)", "sinedie")
            elif not killed:
                killed = (d, "committee" if place == "committee" else "floor")
                if place == "committee":
                    commfate = "defeated" if commfate == "none" else commfate
                    add(d, f"Killed in the {comm} Committee (indefinitely postponed)" if comm else "Indefinitely postponed (killed)", "killed")
                elif into:
                    # (At the end of a session, bills whose text went into another are postponed in a batch.)
                    add(d, f"Indefinitely postponed: its provisions had gone into {label(into[-1][1])}", "killed")
                else:
                    add(d, "Indefinitely postponed (killed) by the Legislature", "killed")
            continue
        if re.match(r"Bill [Ww]ithdrawn", t):
            killed = killed or (d, "withdrawn")
            add(d, "Withdrawn by its introducer", "withdrawn")
            continue
        m = re.match(r"(?:(.+?) )?(MO\d+) (.+?) filed$", t)
        if m:
            motions[m.group(2)] = m.group(3)
            kind = motion_kind(m.group(3))
            if kind in ("bracket", "ipp", "recommit", "override", "cloture", "return"):
                by = who(m.group(1), session) if m.group(1) else "A senator"
                add(d, f"{by[:1].upper() + by[1:]} moved {plain_motion(m.group(3))}", "motion")
            continue
        m = re.match(r"(?:(.+?) )?(MO\d+) (prevailed|failed|withdrawn|not considered|out of order)$", t)
        if m:
            desc = motions.get(m.group(2), "")
            kind = motion_kind(desc)
            res = m.group(3)
            if kind == "cloture":
                v = floor_vote(key, f"Cloture ({rnd or 'floor'})", d)
                add(d, ("Cloture invoked: debate ended" if res == "prevailed" else "Cloture failed: debate goes on, and the bill is set aside")
                    + (f", {v[0]}-{v[1]} ({CLOTURE_NEED} votes needed)" if v else ""), "cloture" if res == "prevailed" else "clotfail")
                continue
            if kind not in ("bracket", "ipp", "recommit", "override", "return") or res in ("withdrawn", "not considered", "out of order"):
                continue
            if res == "failed":
                add(d, f"The motion {plain_motion(desc)} failed", "motionfail")
                continue
            if kind in ("bracket", "ipp") and not passed and not killed:
                killed = (d, "bracket" if kind == "bracket" else "floor")
                add(d, ("Bracketed: set aside for the session" if kind == "bracket" else "Killed (indefinitely postponed)")
                    + " on a motion", "killed")
            elif kind == "recommit":
                mm = re.search(r"to (?:the )?(.+?)(?: Committee)?$", desc, re.I)
                c = comm_name(mm.group(1)) if mm else (first_ref or "")
                place, rnd, comm = "committee", None, c
                add(d, f"Sent back to the {c} Committee", "recommitted")
            elif kind == "override" and "line-item" in desc.lower():
                add(d, "The Legislature overrode part of the line-item veto", "itemoverride")
            elif kind == "return":
                place, rnd = "floor", "Select File"
                add(d, "Returned to Select File for an amendment", "return")
            continue
        m = re.match(r"(.+?) (priority bill|priority resolution|Major Proposal)$", t)
        if m:
            w = m.group(1)
            if w.startswith("Speaker"):
                txt = "Named a Speaker major proposal" if "Major" in m.group(2) else "Named a Speaker priority bill"
                priority.append("Speaker")
            elif comm_name(w) in standing() or re.search(r"Committee|Board|Audit", w):
                txt = f"Named a priority bill of {who(w, session)}"
                priority.append("committee")
            else:
                txt = f"Named {who(w, session)}'s priority bill"
                priority.append("senator")
            add(d, txt, "priority")
            continue
        m = re.match(r"(.+?) name (added|withdrawn)$", t)
        if m:
            if m.group(2) == "added":
                cosponsors.append(m.group(1))
            else:
                withdrawn.add(m.group(1))
            continue
        m = re.match(r"Provisions/portions of (LB\d+A?) (?:amended (?:into|by)|in introduced version of) (LB\d+A?)(?: by (.+))?$", t)
        if m:
            src, dst = m.group(1), m.group(2)
            if src == k and dst != k:
                into.append((d, dst))
                add(d, f"Its provisions were amended into {label(dst)}" + (f" ({m.group(3)})" if m.group(3) else ""), "into")
            elif dst == k and src != k:
                merged.append((d, src))
            continue
        if re.match(r"Title printed\. Carryover", t):
            add(d, "Carried over to the second session", "carry")
            continue
        m = re.match(r"(?:(.+?) )?((?:AM|FA|ER|ST)\d+)(?: to (?:AM|FA|ER)\d+)? (adopted|lost|divided|not germane|is germane|reconsidered|filed|withdrawn|pending|Pending|refiled|not considered|not further considered|recorded|Recorded|reoffered)$", t)
        if m:
            res = m.group(3).lower()
            if res in ("adopted", "lost") and m.group(2)[:2] in ("AM", "FA"):
                by = who(m.group(1), session) if m.group(1) else ""
                add(d, f"Amendment {m.group(2)}" + (f" ({by.replace('the ', '') if by.startswith('the ') else by})" if by else "")
                    + f" {res}", "amend")
            continue
        if re.match(r"(?:.+ )?MO\d+ (?:Pending|pending)$|Pending$|Dispensing of reading|No objections to unanimous|Objection to unanimous|"
                    r".* explanation of vote$|.* unanimous consent|Motion to (?:suspend|return to Select File|overrule|cancel)|"
                    r"Correction$|Communication|Message from|Certificate|Attorney General|Minority Committee Statement|"
                    r"Corrected .* Filed|Chair ruled|Point of order|Passed over$|.* motion to suspend|.* motion to indefinitely", t):
            continue
        add(d, t[:1].upper() + t[1:], "other")

    # The governor's lines carry their own dates, days before they're listed: in day order, the page's order within a day.
    steps.sort(key=lambda s: s[0] or "")
    if merged:
        # One line for the bills whose text came into this one (an omnibus bill lists dozens), on the day the page says.
        day = max(dd for dd, _ in merged)
        names = sorted({src for _, src in merged}, key=lambda x: int(re.sub(r"\D", "", x)))
        steps.append((day, H, f"Includes provisions of {len(names)} other bill{'s' if len(names) > 1 else ''}: "
                      + ", ".join(label(x) for x in names), "merged"))
        steps.sort(key=lambda s: s[0] or "")

    if const:
        stage = 3 if passed else 1 if place == "floor" else 0
    elif law:
        stage = 5
    elif vetoed:
        stage = 6
    elif sent:
        stage = 4
    elif passed or enrolled:
        stage = 3
    else:
        stage = 1 if place == "floor" else 0

    title = b["title"]
    official = title
    if abill:
        title = f"Pays for {main} (its A bill)"
        official = f"Appropriation bill for {main}: Nebraska passes the spending a bill needs as a separate “A bill”."
    if const:
        t2 = re.sub(r"^Constitutional amendment (?:to )?", "", title, flags=re.I)
        title = f"Constitutional amendment: {t2[:1].lower() + t2[1:] if t2[:2] != t2[:2].upper() else t2}" if t2 != title else title
    topics = ["const"] if const else []
    for c in refs:
        tp = P.COMMITTEE_TOPICS.get(c)
        if tp and tp not in topics:
            topics.append(tp)
    if not topics or topics == ["gov"]:
        for tp, rx in P.TOPIC_WORDS.items():
            if rx.search(title) and tp not in topics:
                topics.append(tp)
    topics = list(dict.fromkeys(t for t in topics if t != "const" or const))

    # The introducer: a senator (by id), else a committee ("Urban Affairs Committee", "Executive Board: Hansen, Chairperson").
    district = 0
    if b["senator"] and b["senator"] in by_id():
        mm = by_id()[b["senator"]]
        sponsor, district = mm["name"], mm["district"]
    elif b["committee"] or re.search(r"Committee|Board", b["introducer"] or ""):
        sponsor = re.sub(r":.*$", "", b["committee"] or b["introducer"]).strip()
        if not re.search(r"Committee|Board", sponsor):
            sponsor += " Committee"
    else:
        sponsor = re.sub(r"^Speaker\s+", "", b["introducer"] or "—")
    cos = []
    for n in cosponsors:
        if n in withdrawn:
            continue
        sid = seat_of_name(session, n)
        full = next((x["name"] for x in members() if f"{H}:{x['district']}" == sid), None) if "?" not in sid else None
        nm = full or n
        if nm != sponsor and nm not in cos:
            cos.append(nm)

    if stage == 0:
        dsc = (f"In the {comm}" + ("" if "Board" in comm else " Committee")) if place == "committee" and comm else "Introduced"
    elif stage == 1:
        dsc = f"On the floor ({rnd or 'General File'})"
    else:
        dsc = {3: "Passed the Legislature", 4: "On the governor's desk", 5: "Became law", 6: "Vetoed"}[stage]
    comm_now = comm if place == "committee" and stage == 0 else None

    def dates(test, mode="last"):
        ds = sorted({s[0] for s in steps if test(s) and s[0]})
        return {"first": ds[0], "last": ds[-1], "all": ";".join(ds)}[mode] if ds else ""

    action_dates = [s[0] for s in steps if s[0]]
    passes = dates(lambda s: s[3] == "pass", "all")
    rec = {
        "nums": [k], "base": [k], "prev": earlier(session, b),
        "title": title, "summary": official, "act": "", "lawCode": "", "law": None, "laws": [],
        "comms": sorted({f"{H} · {c}" for c in refs}), "topics": topics, "places": [],
        "narrow": P.narrow_kind(title),
        # A bills only carry another bill's money: left out of the statistics like Illinois's shell bills, tagged "A bill".
        "shell": abill,
        "commFate": "passed" if reported or passed else commfate, "mainTopic": topics[0] if topics else "",
        "local": "local" in topics, "senDeleg": False, "asmDeleg": False,
        "budget": bool(re.search(r"\bappropriat", b["title"], re.I)) or abill,
        # One house: a bill that passed passed "both" (the shared code's test for stage 3 and on).
        "passedS": stage >= 3, "passedA": passed or stage >= 3, "program": None,
        "stage": stage, "passedIn": None,
        "chapter": None,
        "veto": None, "memo": "", "vetoMemo": None,
        "simText": f"{title}",
        "comm": comm_now,
        "first": min(action_dates, default=f"{session}-01-01"),
        "last": max(action_dates, default=f"{session}-01-01"),
        "cosp": len(cos),
        "keyDates": [
            dates(lambda s: s[3] == "reported", "first"),
            "",
            passes,
            "",
            dates(lambda s: s[3] == "sent") if stage >= 4 else "",
            dates(lambda s: s[3] in ("signed", "nosign", "overridelaw")) if stage == 5 else "",
            dates(lambda s: s[3] == "vetoed"),
        ],
        "votes": fvotes, "firstComms": [(H, first_ref, first_report or passed)] if first_ref else [],
        "vers": [{"p": k, "sponsor": sponsor, "district": district, "cosponsors": cos, "link": link_of(session, k),
                  "primes": 1, "cosp": len(cos), "statusDesc": dsc, "committee": comm_now,
                  "actions": [[s[0], s[2]] for s in steps]}],
        # Nebraska's own: priority designations ("senator", "committee", "Speaker"), and where its text went.
        "priority": priority, "into": [x for _, x in into],
    }
    if stage == 5 and not rec["keyDates"][5]:
        rec["keyDates"][5] = rec["last"]
    return rec


def keys(session):
    """The Legislature's bills, A bills and constitutional amendments, in number order."""
    ks = [k for k in listing(session).get("bills") or {} if re.fullmatch(r"LB\d+A?|LR\d+CA", k)]
    return sorted(ks, key=lambda k: (k.startswith("LR"), int(re.sub(r"\D", "", k)), k))


def load_session(session):
    """Read one Legislature's bills and return (records, bill number -> record index, fetched time, delegation)."""
    key = (session, "load")
    if key in _CACHE:
        return _CACHE[key]
    recs, index = [], {}
    for k in keys(session):
        b = parse(session, k)
        if not b or not b["title"]:
            continue
        rec = record(session, b)
        index[k] = len(recs)
        recs.append(rec)
    # A bill whose text went into another: the history line says how that one ended.
    for r in recs:
        for dst in r.get("into") or []:
            j = index.get(dst)
            if j is None:
                continue
            o = recs[j]
            fate = {5: "became law", 6: "was vetoed", 3: "passed the Legislature", 4: "went to the governor"}.get(o["stage"])
            if fate:
                acts = r["vers"][0]["actions"]
                for a in acts:
                    if a[1].startswith(f"Its provisions were amended into {label(dst)}") and "(it " not in a[1]:
                        a[1] += f" (it {fate})"
    # When the download last saved anything for this Legislature.
    paths = [os.path.join(folder(session), n) for n in ("state.json", "list.json")]
    times = [os.path.getmtime(x) for x in paths if os.path.exists(x)]
    fetched = datetime.fromtimestamp(max(times), ZoneInfo(P.TIMEZONE)).strftime("%Y-%m-%d %H:%M") if times else ""
    _CACHE[key] = (recs, index, fetched, {"SENATE": [], "ASSEMBLY": []})
    return _CACHE[key]


# ---- Earlier Legislatures ----

_KEYS = {}


def _title_key(title):
    t = re.sub(r"[^a-z0-9 ]", "", re.sub(r"\s+", " ", (title or "").lower())).strip()
    return t if len(t.split()) >= 6 and not re.search(r"\bappropriat|\bstate government\b|\bbiennium\b", t) else ""


def _keys(session):
    """A Legislature's LBs that didn't become law: (title, introducer) -> [bills], title -> [bills]."""
    if session not in _KEYS:
        by_both, by_title = defaultdict(list), defaultdict(list)
        for k in keys(session):
            if not re.fullmatch(r"LB\d+", k):
                continue
            b = parse(session, k)
            if not b or any(re.match(r"Approved by Governor|Became law|Bec(?:ame|omes) law", t) for _, t, _ in b["rows"]):
                continue  # a law isn't tried again (yearly bills like the budget share titles)
            tk = _title_key(b["title"])
            if tk:
                by_title[tk].append(k)
                by_both[(tk, b["senator"] or b["introducer"])].append(k)
        _KEYS[session] = (by_both, by_title)
    return _KEYS[session]


def earlier(session, b):
    """The same bill in the Legislature before: the same title and introducer, or the same title (one bill in each
    Legislature, six words or more). Never appropriations, nor a bill that became law."""
    out = set()
    if not re.fullmatch(r"LB\d+", b["key"]):
        return out
    tk = _title_key(b["title"])
    if not tk:
        return out
    prev = session - 2
    if prev not in sessions():
        return out
    by_both, by_title = _keys(prev)
    mine_both, mine_title = _keys(session)
    who_ = b["senator"] or b["introducer"]
    for key, old, mine in (((tk, who_), by_both, mine_both), (tk, by_title, mine_title)):
        if len(old.get(key, [])) == 1 and len(mine.get(key, [])) <= 1:
            out.add((prev, old[key][0]))
            break
    return out


def parties(session, recs):
    """Nebraska's senators are elected without party labels and no official page lists a party: none."""
    return {}


def agendas(session):
    """Bills with a public hearing still to come: bill -> [["Legislature Judiciary", "2027-02-10T13:30:00"]] (the notice
    gives the day only)."""
    today = date.today().isoformat()
    out = {}
    if session != max(sessions() or [0]):
        return out
    for k in keys(session):
        b = parse(session, k)
        if not b:
            continue
        comm = None
        for d, t, _ in b["rows"]:
            m = re.match(r"(?:Re)?[Rr]eferred to (.+)$", t)
            if m:
                comm = comm_name(m.group(1))
            m = re.match(r"Notice of hearing for (.+)$", t)
            if m and comm and "cancel" not in t and iso(m.group(1)) >= today:
                out.setdefault(k, []).append([f"{HOUSE[H]} {comm}", f"{iso(m.group(1))}T00:00:00"])
    return out


# ---- Checks against the Clerk's worksheets ----

def worksheet(session, which):
    """A final worksheet's status lists (worksheets/r1.pdf or r2.pdf, read with pdftotext): {"Approved by Governor":
    {"LB60", "LB304A", ...}, ...} with the bills' and A bills' numbers ("e" marks an emergency clause, dropped)."""
    path = os.path.join(folder(session), "worksheets", f"{which}.pdf")
    tool = shutil.which("pdftotext")
    if not tool or not os.path.exists(path):
        return {}
    t = subprocess.run([tool, "-layout", path, "-"], capture_output=True, text=True).stdout
    out = {}
    for head in ("Approved by Governor", "Line-item Veto", "Returned by Governor Without Approval",
                 "Passed Notwithstanding Objections of Governor", "Became Law Without Governor's Signature",
                 "Failed on Final Reading", "Resolutions Delivered to Secretary of State", "Indefinitely Postponed"):
        m = re.search(re.escape(head) + r" \((\d+)\):(.*?)(?=\n\s*\n|\n[A-Z][a-z]+[^\n]*\(\d+\):)", t, re.S)
        if not m:
            continue
        nums = set()
        for tok in m.group(2).split():
            tok = tok.strip("*")
            mm = re.fullmatch(r"(LR)?(\d+)(A?)(CA)?e?", tok)
            if mm:
                nums.add(f"{mm.group(1) or 'LB'}{mm.group(2)}{mm.group(3)}{mm.group(4) or ''}")
        out[head] = {"count": int(m.group(1)), "bills": nums}
    return out


def checks(session):
    """Laws, vetoes and constitutional amendments compared with the Clerk's final worksheets, bill for bill."""
    recs = load_session(session)[0]
    law = defaultdict(set)
    for which, year in (("r1", session), ("r2", session + 1)):
        ws = worksheet(session, which)
        for h, v in ws.items():
            law[h] |= v["bills"]
    # (A line-item veto's bill is a law, listed under "Line-item Veto" instead of "Approved by Governor"; LB 814 of 2023, the
    # budget, is "Passed Notwithstanding" because the Legislature overrode part of its line-item veto.)
    official_laws = law["Approved by Governor"] | law["Line-item Veto"] | law["Became Law Without Governor's Signature"] | law["Passed Notwithstanding Objections of Governor"]
    official_vetoes = law["Returned by Governor Without Approval"] - law["Passed Notwithstanding Objections of Governor"]
    mine_law = {r["nums"][0] for r in recs if r["stage"] == 5}
    mine_veto = {r["nums"][0] for r in recs if r["stage"] == 6}
    mine_const = {r["nums"][0] for r in recs if "const" in r["topics"] and r["stage"] == 3}
    return {"bills": len(recs), "laws": len(mine_law), "official laws": len(official_laws),
            "laws not on the worksheets": sorted(mine_law - official_laws), "worksheet laws not here": sorted(official_laws - mine_law),
            "of which A bills": sum(1 for x in mine_law if x.endswith("A")),
            "without signature": sorted(law["Became Law Without Governor's Signature"]),
            "line-item vetoes": sorted(law["Line-item Veto"]), "overrides": sorted(law["Passed Notwithstanding Objections of Governor"]),
            "vetoes": len(mine_veto), "official vetoes": len(official_vetoes),
            "vetoes not on the worksheets": sorted(mine_veto - official_vetoes), "worksheet vetoes not here": sorted(official_vetoes - mine_veto),
            "amendments to the voters": sorted(mine_const), "worksheets": sorted(law["Resolutions Delivered to Secretary of State"])}


if __name__ == "__main__":
    for s in sessions():
        recs = load_session(s)[0]
        print(s, dict(sorted(Counter(r["stage"] for r in recs).items())))
        print(json.dumps(checks(s), indent=1))
