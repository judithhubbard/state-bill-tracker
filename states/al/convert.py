"""Alabama's bills (downloaded by states/al/fetch.py from ALISON, the Legislature's website) in the shape build_data.py
reads. A page a year: the Legislature meets once a year in a regular session (30 legislative days within 105 calendar
days, from February, or January in an election year) and bills die when it ends. House and Senate bills only (HB, SB);
constitutional amendments are bills here ("By Representative Hill (Constitutional Amendment)"); resolutions and
special sessions are left out.

The history (data/al/<year>/history.json) is a list of lines, each with a date, the house that recorded it and the
action as written. Within a day the lines aren't in order (a passage can come before the amendment it adopted, the
second house's referral before the first house's engrossment), so they're sorted by day and then by step (`rank()`).
The steps:
- "Read for the first time and referred to the House Committee on Judiciary" (the referral; "Pending Committee Action
  in House of Origin" repeats it as a status, with the committee's name in its own field, and is dropped);
- "Re-referred to Committee in House of Origin" (to another committee, named in the line's committee field);
- "Reported Out of Committee House of Origin" (the committee approved it; Alabama's committees report bills favorably
  or not at all) and "Read for the Second Time and placed on the Calendar";
- "Third Reading in House of Origin" with a roll call: the vote on the bill's Budget Isolation Resolution (until the
  budgets pass, a bill needs three-fifths of those voting to be taken up before them). It isn't the passage, and isn't
  counted as a vote on the bill;
- "Motion to Read a Third Time and Pass [as Amended] - Adopted Roll Call 59" (the passage; "- Lost" failed);
  "Reconsider - Adopted" undoes the house's last vote. In the second house "as Amended" means the first has to agree:
  "Brown Concur In and Adopt - Adopted Roll Call 1238" (it did), or "Non-Concur and Appoint Conference Committee", then
  "Concur In and Adopt Conference Committee Report" in both houses;
- "Currently Indefinitely Postponed" (killed, often because a companion bill passed instead: "SB12 Substituted for HB34
  a Companion Bill");
- "Ready to Enroll", "Enrolled", "Signature Requested", "Delivered to Governor", then "Enacted" (with an Act number in
  bills.json: Act 2025-312) or, a few times a year, "Signed by Governor"; "Pocket Veto"; "Pending with Executive
  Amendment" (the governor sent it back with a proposed amendment: if both houses agree it goes back to the governor;
  if not, the governor can sign or veto it as passed); constitutional amendments are "Sent to Secretary of State" for
  the voters, never the governor, and are tagged "const" (they stop at "passed both houses" here, though they get Act
  numbers; a few local ones are also delivered to the governor and "Enacted").

Roll calls (votes.json) list every member by name: Y, N, A (abstain) and P (pass). Most members abstain on local bills,
which only the county's delegation votes on. In 2026, House roll calls 273 to 596 count a member they don't name (Kristin
Nelson, who joined the House then: her name appears from roll call 597): `fill_missing()` puts her back in the group
that's one short, as for Arkansas's Alan Clark.

Local bills (about a fifth: a county's name as the subject, "(N & P)" in the byline for a bill published with notice,
or a county or local legislation committee) are narrow kind "place" ("For one city or county"). "What it does" is the
act's summary (for laws) or the Legislative Services Agency's synopsis of the bill as introduced.
"""
import json, os, re
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from states.al import profile as P

HOUSE = {"S": "Senate", "H": "House"}
OTHER = {"S": "H", "H": "S"}
SEATS = {"S": 35, "H": 105}
_PARTIES, _CACHE = {}, {}
CODE = {"N": "N", "A": "B", "P": "B"}  # abstain and pass are both "didn't vote yes or no"; yes is left out


def folder(session):
    return os.path.join(P.DATA, str(session))


def sessions():
    out = []
    for f in sorted(os.listdir(P.DATA)) if os.path.isdir(P.DATA) else []:
        if re.fullmatch(r"\d{4}", f) and os.path.exists(os.path.join(P.DATA, f, "bills.json")) \
                and os.path.exists(os.path.join(P.DATA, f, "history.json")):
            out.append(int(f))
    return out


def load(session, name, default=None):
    key = (session, name)
    if key not in _CACHE:
        try:
            _CACHE[key] = json.load(open(os.path.join(folder(session), name), encoding="utf-8"))
        except (OSError, ValueError):
            _CACHE[key] = default
    return _CACHE[key]


# ---- Members ----

def members():
    """Every member record with a name and a district (current and past): [{house, district, name, first, last, party,
    id, active, ...}]."""
    if "members" not in _CACHE:
        try:
            raw = json.load(open(os.path.join(P.DATA, "members", "members.json"), encoding="utf-8")).get("members") or []
        except (OSError, ValueError):
            raw = []
        out = []
        for m in raw:
            d = re.search(r"\d+", m.get("district") or "")
            name = (m.get("fullName") or "").strip()
            if m.get("body") not in ("House", "Senate") or not d or not name or name == "Vacant":
                continue
            out.append({**m, "house": m["body"][0], "district": int(d.group(0)), "name": name,
                        "last": (m.get("lastName") or name.split()[-1]).strip(), "first": (m.get("firstName") or "").strip(),
                        "party": m.get("affiliation") or ""})
        _CACHE["members"] = out
    return _CACHE["members"]


def voters(session):
    """(house, name) -> number of the year's roll calls the name is on."""
    key = (session, "voters")
    if key not in _CACHE:
        c = Counter()
        for k, v in (load(session, "votes.json", {}) or {}).items():
            for m in v.get("votes") or []:
                c[(k[0], m["memberName"])] += 1
        _CACHE[key] = c
    return _CACHE[key]


def seat_of(h, name):
    """A roll call's name in a house -> "H:45", or "H?Surname" for a name no member record of that house has."""
    if (h, name) in P.MOVED:
        return f"{h}:{P.MOVED[(h, name)]}"
    hits = [m for m in members() if m["house"] == h and m["name"] == name]
    if len(hits) == 1:
        return f"{h}:{hits[0]['district']}"
    if len(hits) > 1:  # the same name on an old and a new record: the current one
        live = [m for m in hits if m.get("active")]
        if len(live) == 1:
            return f"{h}:{live[0]['district']}"
    return f"{h}?{name.split()[-1] if name else name}"


def sponsor_resolver(session):
    """A bill's sponsor as the site writes it ("Brown (C)", "Wood (R)", "Coleman-Madison") in a house -> the member's
    record. Surnames shared within a house carry the first name's initial; among several matches, the one who voted
    that year."""
    vote_names = voters(session)

    def find(h, short):
        short = short.strip()
        m = re.match(r"(.+?)\s*\((\w)\)$", short)
        last, initial = (m.group(1), m.group(2)) if m else (short, None)
        norm = lambda s: re.sub(r"[^a-z]", "", s.lower())
        hits = [x for x in members() if x["house"] == h and norm(x["last"]) == norm(last)]
        if not hits:
            hits = [x for x in members() if x["house"] == h and norm(x["name"]).endswith(norm(last))]
        if initial:
            narrowed = [x for x in hits if x["first"][:1].upper() == initial.upper() or x["name"][:1].upper() == initial.upper()]
            hits = narrowed or hits
        if len(hits) > 1:
            voted = [x for x in hits if vote_names.get((h, x["name"]))]
            hits = voted or hits
        return hits[0] if len(hits) == 1 else None
    return find


def fill_missing(rc, h):
    """A roll call's members as (name, code) pairs. Put back a member the roll call counts but doesn't name (2026's House
    roll calls 273-596 leave out Kristin Nelson): when the year's members of the house missing from the list are exactly
    as many as the one group that's short, they belong to that group."""
    listed = [(m["memberName"], m["vote"]) for m in rc.get("votes") or []]
    have = Counter(c for _, c in listed)
    short = {"Y": (rc.get("yeas") or 0) - have["Y"], "N": (rc.get("nays") or 0) - have["N"],
             "A": (rc.get("abstains") or 0) - have["A"], "P": (rc.get("passes") or 0) - have["P"]}
    return listed, short


# ---- Wording ----

def comm_name(c):
    """"Ports, Waterways & Intermodal Transit" -> "Ports, Waterways and Intermodal Transit"; "Military and Veterans'
    Affairs" -> "Military and Veterans Affairs"."""
    c = re.sub(r"\s+", " ", (c or "").replace("&", "and")).strip(" .")
    c = re.sub(r"^(?:House|Senate) Committee on ", "", c)
    return c.replace("Veterans' Affairs", "Veterans Affairs")


def title_case(t):
    t = re.sub(r"\s+", " ", (t or "").strip())
    return t[:1].upper() + t[1:]


STOCK = re.compile(r"\s*This bill would (?:also )?make nonsubstantive, technical revisions to update the existing code "
                   r"language to current style\.|;? and in connection therewith would have as its purpose or effect the "
                   r"requirement of a new or increased expenditure of local funds within the meaning of (?:Amendment 621|"
                   r"Section 111\.05)[^.;]*", re.I)


def sentences(t):
    return [s.strip() for s in re.split(r"(?<=[a-z0-9)\"”][.])\s+(?=[A-Z])", t) if s.strip()]


def synopsis_text(t):
    """The synopsis with what the bill does first: its "This bill would ..." sentences, then the background ("Under
    existing law ..."), as it's written. The stock sentence about technical revisions is dropped."""
    t = re.sub(r"\s+", " ", t or "").strip()
    if not t:
        return ""
    ss = sentences(t)
    does = [s for s in ss if re.match(r"This (?:bill|act|amendment|proposed amendment)\b", s)
            and not re.search(r"nonsubstantive, technical revisions", s)]
    rest = [s for s in ss if s not in does and not re.search(r"nonsubstantive, technical revisions", s)]
    if not does:
        return " ".join(rest)
    return " ".join(does) + ("\n" + " ".join(rest) if rest else "")


# ---- The steps ----

FIRST = re.compile(r"^Read for the first time and referred to the (House|Senate) Committee on (.+?)\s*$", re.I)
PASS = re.compile(r"Motion to Read (?:Again )?a Third Time and Pass( as Amended)?\s*-\s*(Adopted|Lost)", re.I)
ROLL = re.compile(r"Roll Call (\d+)", re.I)


def kind_of(t):
    """A history line -> (kind, rank within a day)."""
    if not t:
        return "skip", 0
    if FIRST.match(t):
        return "ref", 1
    if re.match(r"Pending Committee Action", t):
        return "pending", 2
    if re.match(r"Re-referred to Committee", t):
        return "reref", 3
    if re.match(r"Reported Out (?:of )?Committee", t):
        return "reported", 4
    if re.match(r"Read for the Second Time", t):
        return "second", 5
    if re.match(r"Third Reading in ", t):
        return "bir", 7
    if re.search(r"BIR", t):
        return "birline", 7
    if PASS.search(t):
        return "pass", 9
    if re.search(r"Reconsider", t, re.I) and re.search(r"Adopted", t, re.I) and not re.search(r"Local Application", t):
        return "reconsider", 10
    if re.match(r"Engrossed$", t):
        return "engrossed", 11
    if re.search(r"Indefinitely Postponed", t):
        return "ip", 12
    if re.search(r"Substituted for .* Companion", t):
        return "companion", 12
    if re.search(r"Executive Amendment", t, re.I):
        return ("govamend", 30) if re.match(r"Pending with", t) else ("execconcur", 31)
    if re.search(r"Conference Committee Report|Conf Rpt|Concurs? in Conference", t, re.I) and not re.search(r"Non[- ]?Concur|Lost", t, re.I):
        return "ccr", 22
    if re.search(r"Non[- ]?Concur|Nonconcur|Accede|Request for (?:New )?Conference|In Conference Committee|"
                 r"Reported Favorably From Conference|Conference Committee Substitute", t, re.I):
        return "conf", 21
    if re.search(r"\bConcur", t, re.I) and not re.search(r"Lost", t):
        return "concur", 20
    if re.match(r"Ready to Enroll", t):
        return "enroll", 40
    if re.match(r"Enrolled$", t):
        return "enrolled", 41
    if re.match(r"Signature Requested", t):
        return "signature", 42
    if re.match(r"Delivered to Governor", t):
        return "sent", 43
    if re.match(r"Sent to Secretary of State", t):
        return "sos", 43
    if re.match(r"Signed by Governor", t):
        return "signed", 44
    if re.match(r"Enacted$", t):
        return "enacted", 45
    if re.match(r"Pocket Veto", t):
        return "pocket", 45
    if re.search(r"\bveto", t, re.I):
        return "veto", 45
    if re.search(r"Local ?Certification ?Resolution|Local Application", t, re.I):
        return "localcert", 6
    if re.search(r"Carr(?:ied|y) Over", t, re.I):
        return "carried", 8
    if re.search(r"(?:Amendment|Substitute) Offered$", t):
        return "other", 7.5  # offered before it's voted on
    return "other", 8


PHASE_FINAL = {"concur", "conf", "ccr", "govamend", "execconcur", "enroll", "enrolled", "signature", "sent", "sos",
               "signed", "enacted", "pocket", "veto"}


def is_const(b, tx):
    """The byline's "(Constitutional Amendment)", the subject "Constitutional Amendments Statewide", a short title ending
    "Constitutional Amendment", or an official title "Proposing an amendment to the Constitution of Alabama" (not a bill
    "contingent upon ratification of a constitutional amendment")."""
    return bool(re.search(r"Constitutional Amendment", (tx.get("byline") or "") + " " + (b.get("subject") or ""))
                or re.search(r"Constitutional Amendment\W*$", b.get("shortTitle") or "", re.I)
                or re.search(r"proposing an amendment to the Constitution", tx.get("title") or "", re.I))


def is_local(b, tx):
    subj = b.get("subject") or ""
    county = any(s.strip().endswith("County") for s in subj.split(";")) and "Statewide" not in subj
    notice = "N & P" in (tx.get("byline") or "") or bool(tx.get("local_notice"))
    comm = bool(re.search(r"(?:Local|County) Legislation", f"{b.get('allCommittees') or ''} {tx.get('rfd') or ''}"))
    return county or (notice and "Statewide" not in subj) or (comm and "Statewide" not in subj)


def load_session(session):
    """Read one year's bills and return (records, bill number -> record index, fetched time, delegation)."""
    bills = (load(session, "bills.json", {}) or {}).get("bills") or []
    lines = (load(session, "history.json", {}) or {}).get("lines") or []
    texts = load(session, "texts.json", {}) or {}
    votes = load(session, "votes.json", {}) or {}
    by = defaultdict(list)
    for i, l in enumerate(lines):
        by[l["instrumentNbr"]].append((i, l))
    find = sponsor_resolver(session)
    parties = _PARTIES.setdefault(session, {})
    path = os.path.join(folder(session), "bills.json")
    fetched = datetime.fromtimestamp(os.path.getmtime(path), ZoneInfo(P.TIMEZONE)).strftime("%Y-%m-%d %H:%M") if os.path.exists(path) else ""
    # Each house's members that year: everyone on its roll calls (names), for putting back a member a roll call leaves out.
    house_names = defaultdict(set)
    for (h, n), c in voters(session).items():
        if c >= 5:
            house_names[h].add(n)
    recs, index, whats = [], {}, {}
    for b in sorted(bills, key=lambda b: (b["instrumentNbr"][0] != "H", int(re.sub(r"\D", "", b["instrumentNbr"])))):
        p = b["instrumentNbr"]
        if not re.fullmatch(r"(HB|SB)\d+", p):
            continue
        rec, what = record(session, b, texts.get(p) or {}, by.get(p, []), votes, find, parties, house_names)
        index[p] = len(recs)
        recs.append(rec)
        if what:
            whats[p] = what
    try:
        json.dump(whats, open(os.path.join(P.DATA, f"texts_{session}.json"), "w"), ensure_ascii=False)
    except OSError:
        pass
    return recs, index, fetched, {"SENATE": [], "ASSEMBLY": []}


def roll_call(votes, h, n, house_names):
    """A roll call's [yeas, nays, [[seat, code], ...]] (yes votes left out), or None when it wasn't downloaded."""
    rc = votes.get(f"{h}{n}")
    if not rc or "votes" not in rc:
        return None
    listed, short = fill_missing(rc, h)
    names = {x for x, _ in listed}
    missing = sorted(house_names[h] - names)
    lacking = [g for g, k in short.items() if k > 0]
    if missing and len(lacking) == 1 and short[lacking[0]] == len(missing) and not any(k < 0 for k in short.values()):
        listed += [(x, lacking[0]) for x in missing]
    out, seen = [], set()
    for name, code in listed:
        sid = seat_of(h, name)
        if len(listed) > SEATS[h] and "?" in sid:
            continue  # a garbled list (2024's Senate roll call 607 also names senators of decades ago)
        if sid in seen:
            continue
        seen.add(sid)
        if code in CODE:
            out.append([sid, CODE[code]])
    return [int(rc.get("yeas") or 0), int(rc.get("nays") or 0), out]


def record(session, b, tx, hist, votes, find, parties, house_names):
    p = b["instrumentNbr"]
    origin = p[0]
    other = OTHER[origin]
    const = is_const(b, tx)
    local = is_local(b, tx)
    rows = []
    for i, l in hist:
        t = re.sub(r"\s+", " ", l.get("matter") or "").strip()
        k, r = kind_of(t)
        if k == "skip":
            continue
        h = (l.get("body") or HOUSE[origin])[0]
        phase = 2 if k in PHASE_FINAL else (0 if h == origin else 1)
        rows.append(((l.get("calendarDate") or "")[:10], phase, r, i, h, k, t, l))
    rows.sort()
    steps = []  # (date, house or "G", wording, kind)
    passed, failed, amended_by = set(), set(), set()
    last_vote = {}
    concurred = ccr = False
    ccr_houses = set()
    enrolled = sent = law = vetoed = to_sos = govamend = ip = False
    place, comm, where = "desk", None, origin
    refs, first_ref, first_report, dopass = [], None, None, False
    fvotes = []
    for d, phase, _, _, h, k, t, l in rows:
        H = HOUSE[h]
        n = None
        m = ROLL.search(t)
        if m:
            n = int(m.group(1))  # the line's own number (2024's field sometimes holds the BIR's)
        elif l.get("rollCallNbr"):
            n = int(l["rollCallNbr"])
        if k == "pending":
            c = comm_name(l.get("committee"))
            if c and comm is None and place != "floor":
                comm, place = c, "committee"
                refs.append((h, c))
            continue
        if k == "ref":
            c = comm_name(FIRST.match(t).group(2))
            where, comm, place = h, c, "committee"
            refs.append((h, c))
            if first_ref is None and h == origin:
                first_ref = c
            steps.append((d, h, f"REFERRED TO {c.upper()}", "ref"))
            continue
        if k == "reref":
            c = comm_name(l.get("committee"))
            place = "committee"
            if c:
                comm = c
                refs.append((h, c))
            steps.append((d, h, f"Sent to another committee{': the ' + c + ' Committee' if c else ''}", "rereferred"))
            continue
        if k == "reported":
            cname = comm_name(l.get("committee")) or comm
            if h == origin and first_report is None:
                first_report = "pass"
            dopass = True
            place = "floor"
            steps.append((d, h, "REPORTED", "reported"))
            steps.append((d, h, f"The {cname + ' ' if cname else ''}Committee reported it favorably" if cname else "Reported favorably by the committee", "report"))
            continue
        if k == "second":
            place = "floor"
            steps.append((d, h, "Read the second time and placed on the calendar", "second"))
            continue
        if k == "bir":
            if n:
                y, no = l.get("yeas"), l.get("nays")
                steps.append((d, h, f"The {H} adopted a budget isolation resolution to take it up before the budgets"
                              + (f", {y}-{no}" if y is not None else ""), "bir"))
            else:
                steps.append((d, h, "Read the third time", "third"))
            continue
        if k == "birline":
            steps.append((d, h, "The budget isolation resolution failed" if re.search(r"Lost|Failed", t) else t, "bir"))
            continue
        if k == "pass":
            pm = PASS.search(t)
            ok = pm.group(2).lower() == "adopted"
            rc = roll_call(votes, h, n, house_names) if n else None
            y, no = (rc[0], rc[1]) if rc else (l.get("yeas"), l.get("nays"))
            if rc:
                fvotes.append([h, "F", None, d, rc[0], rc[1], rc[2]])
            last_vote[h] = "pass" if ok else "fail"
            tally = f", {y}-{no}" if y is not None else ""
            if not ok:
                failed.add(h)
                steps.append((d, h, f"Failed to pass the {H}{tally}", "fail"))
                continue
            failed.discard(h)
            if h not in passed:
                passed.add(h)
                if h == other and pm.group(1):
                    amended_by.add(h)
            elif h == other and pm.group(1):
                amended_by.add(h)
            place = "desk" if h == origin else place
            if h == origin:
                comm = None
            steps.append((d, h, f"PASSED {H.upper()}", "pass"))
            steps.append((d, h, f"The {H} vote: {y}-{no}" + (" (as amended)" if pm.group(1) else ""), "tally"))
            continue
        if k == "reconsider":
            if last_vote.get(h) == "pass":
                passed.discard(h)
                amended_by.discard(h)
            elif last_vote.get(h) == "fail":
                failed.discard(h)
            elif last_vote.get(h) == "concur":
                concurred = False
            last_vote.pop(h, None)
            steps.append((d, h, f"The {H} voted to reconsider its vote", "reconsider"))
            continue
        if k == "engrossed":
            steps.append((d, h, "Engrossed (amendments written into the bill)", "engross"))
            continue
        if k == "ip":
            ip = True
            steps.append((d, h, f"Indefinitely postponed in the {H}", "ip"))
            continue
        if k == "companion":
            steps.append((d, h, re.sub(r"(\b[HS]B)(\d+)", r"\1 \2", t), "companion"))
            continue
        if k == "concur":
            rc = roll_call(votes, h, n, house_names) if n else None
            if rc:
                fvotes.append([h, "F", None, d, rc[0], rc[1], rc[2]])
            if h == origin:
                concurred = True
                last_vote[h] = "concur"
                steps.append((d, h, f"The {H} agreed to the {HOUSE[other]}'s amendments" + (f", {rc[0]}-{rc[1]}" if rc else ""), "concur"))
            else:
                steps.append((d, h, f"The {H} agreed to the {HOUSE[origin]}'s amendments" + (f", {rc[0]}-{rc[1]}" if rc else ""), "concur2"))
            continue
        if k == "conf":
            if re.search(r"Non[- ]?Concur|Nonconcur", t, re.I):
                steps.append((d, h, f"The {H} refused to agree to the other house's amendments and asked for a conference committee", "noconcur"))
            elif re.search(r"Accede", t, re.I):
                steps.append((d, h, f"The {H} agreed to a conference committee", "conf"))
            elif re.search(r"Reported Favorably", t, re.I):
                steps.append((d, h, "The conference committee reported", "conf"))
            elif re.search(r"In Conference", t, re.I):
                steps.append((d, h, "In conference committee", "conf"))
            else:
                steps.append((d, h, t, "conf"))
            continue
        if k == "ccr":
            rc = roll_call(votes, h, n, house_names) if n else None
            if rc:
                fvotes.append([h, "F", None, d, rc[0], rc[1], rc[2]])
            ccr_houses.add(h)
            steps.append((d, h, f"The {H} adopted the conference committee's report" + (f", {rc[0]}-{rc[1]}" if rc else ""), "ccr"))
            continue
        if k == "govamend":
            govamend = True
            steps.append((d, "G", "Returned by the governor with a proposed amendment (an executive amendment)", "govamend"))
            continue
        if k == "execconcur":
            rc = roll_call(votes, h, n, house_names) if n else None
            steps.append((d, h, f"The {H} agreed to the governor's amendment" + (f", {rc[0]}-{rc[1]}" if rc else ""), "execconcur"))
            continue
        if k in ("enroll", "enrolled"):
            enrolled = True
            if k == "enroll":
                steps.append((d, h, "Passed both houses; ready to be enrolled", "enroll"))
            else:
                steps.append((d, h, "Enrolled", "enrolled"))
            continue
        if k == "signature":
            steps.append((d, h, "Sent for the presiding officer's signature", "signature"))
            continue
        if k == "sent":
            if not const:
                sent = True
            steps.append((d, "G", "DELIVERED TO GOVERNOR", "sent"))
            continue
        if k == "sos":
            to_sos = True
            steps.append((d, "G", "Sent to the Secretary of State (for the voters)", "sos"))
            continue
        if k in ("signed", "enacted"):
            if not const:
                law = True
            act = b.get("actNbr")
            steps.append((d, "G", ("Signed by the governor" if k == "signed" else
                                   f"Became law: Act {act}" if act and not const else f"Act {act}" if act else "Enacted"), k))
            continue
        if k in ("pocket", "veto"):
            vetoed = True
            steps.append((d, "G", "VETOED (a pocket veto: not signed within 10 days after the session ended)" if k == "pocket" else "VETOED", "vetoed"))
            continue
        if k == "localcert":
            steps.append((d, h, "Local bill: notice certified", "localcert"))
            continue
        if k == "carried":
            steps.append((d, h, "Carried over" + (" to the call of the chair" if "Chair" in t else ""), "carried"))
            continue
        # Votes on amendments and motions: "Orr motion to Adopt - Adopted Roll Call 123" (an amendment or substitute,
        # named in the line's amdSub field) -> "Amendment adopted (Orr's motion), 32-0".
        mm = re.match(r"(?:(.+?) )?[Mm]otion to (Adopt|Table)\s*-\s*(Adopted|Lost)\b", t)
        if mm and (l.get("amdSub") or mm.group(2) == "Table"):
            y, no = l.get("yeas"), l.get("nays")
            what = {("Adopt", "Adopted"): "Amendment adopted", ("Adopt", "Lost"): "Amendment rejected",
                    ("Table", "Adopted"): "Amendment tabled", ("Table", "Lost"): "Motion to table an amendment failed"}[(mm.group(2), mm.group(3))]
            steps.append((d, h, what + (f" ({mm.group(1)}{chr(39) if mm.group(1).endswith('s') else chr(39) + 's'} motion)" if mm.group(1) else "") + (f", {y}-{no}" if y is not None else ""), "amend"))
            continue
        # Amendments offered, cloture petitions, cosponsors added: as written.
        steps.append((d, h, t, "other"))
    # Repeated lines (2024's "Delivered to Governor" twice): keep one.
    steps = [x for i, x in enumerate(steps) if not any(x[:3] == y[:3] for y in steps[:i])]

    # A passage the house took back: SB 346 of 2026 passed the House on March 31 and the same day was "Pending Committee
    # Action in Second House" again (no reconsideration line), its status ever since. The bill's status decides.
    status = b.get("currentStatus") or ""
    for role, hh in (("House of Origin", origin), ("Second House", other)):
        if status == f"Pending Committee Action in {role}" and hh in passed and not enrolled:
            passed.discard(hh)
            amended_by.discard(hh)
            place, where = "committee", hh
            steps.append((b.get("lastActionDate") or steps[-1][0], hh, f"Back in committee in the {HOUSE[hh]} (its passage there doesn't stand)", "rereferred"))
    act = b.get("actNbr")
    if act and not const and not vetoed:
        law = True
    if re.search(r"Pocket Veto|Vetoed", b.get("currentStatus") or "") and not law:
        vetoed = True
    # Passed both houses: enrolled; the second house passed it unamended; the first agreed to its amendments; or both
    # adopted a conference report.
    both = (enrolled or to_sos or sent or law or (origin in passed and other in passed and other not in amended_by)
            or (concurred and other in passed) or ccr_houses >= {"H", "S"})
    # Still on the governor's desk after the governor's last day (10 days after sine die): it died, a pocket veto; or,
    # when the governor had sent it back with an amendment the Legislature didn't take up, it died with that.
    end = P.SESSION_ENDS.get(session)
    if sent and not law and not vetoed and end:
        last_day = (date.fromisoformat(end) + timedelta(days=10)).isoformat()
        if date.today().isoformat() > last_day:
            vetoed = True
            steps.append((last_day, "G", "Died: the Legislature didn't act on the governor's amendment" if govamend
                          else "Not signed: died after the session (pocket veto)", "vetoed"))
    if const:
        stage = 3 if both else 2 if passed else None
    elif law:
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
        stage = 1 if place == "floor" or origin in failed else 0
    chapter = int(act.split("-")[1]) if stage == 5 and act and re.fullmatch(r"\d{4}-\d+", act) else None

    title = title_case(b.get("shortTitle") or tx.get("title") or p)
    title = re.sub(r"[;,]?\s*Constitutional Amendment\W*$", "", title, flags=re.I).strip()
    if const:
        title = f"Constitutional amendment: {title}"
    summary = re.sub(r"\s+", " ", tx.get("title") or "").strip()
    subjects = [s.strip() for s in (b.get("subject") or "").split(";") if s.strip()]
    topics = (["const"] if const else []) + (["local"] if local else [])
    for s in subjects:
        topics += P.SUBJECT_TOPICS.get(s, [])
        if s.endswith("County"):
            topics.append("local")
    topics += [P.COMMITTEE_TOPICS[c] for _, c in refs if c in P.COMMITTEE_TOPICS]
    if not topics:
        topics = [k for k, rx in P.TOPIC_WORDS.items() if rx.search(f"{title} {summary}")]
    topics = list(dict.fromkeys(t for t in topics if t != "const" or const))

    # Sponsors: the sponsor (member id), co-sponsors by id (2025-26) or from the byline.
    by_id = {m["id"]: m for m in members()}
    lead = by_id.get(str(b.get("sponsorId") or "")) or find(origin, b.get("sponsor") or "")
    sponsor = lead["name"] if lead else (b.get("sponsor") or "—")
    cos = []
    ids = [x.strip() for x in (b.get("cosponsorIds") or "").split(",") if x.strip()]
    if ids:
        for x in ids:
            m = by_id.get(x)
            if m and m["name"] != sponsor and m["name"] not in cos:
                cos.append(m["name"])
    else:
        bl = re.sub(r"\((?:N & P|Constitutional Amendment)\)", "", tx.get("byline") or "")
        bl = re.sub(r"^By (?:Representatives?|Senators?)\s*", "", bl.strip())
        for w in [x.strip() for x in re.split(r",\s*|\s+and\s+", bl) if x.strip()][1:]:
            m = find(origin, w)
            name = m["name"] if m else w
            if name != sponsor and name not in cos:
                cos.append(name)
    for m in [lead] + [x for x in members() if x["name"] in cos and x["house"] == origin]:
        if m and m.get("party") in ("R", "D"):
            parties[(origin, m["name"])] = m["party"]

    # Where it is now.
    cur = where
    if stage == 0:
        dsc = f"In {HOUSE[cur]} committee" if place == "committee" else "Introduced"
    elif stage == 1:
        dsc = f"Failed in the {HOUSE[origin]}" if origin in failed else f"On the {HOUSE[cur]} floor"
    else:
        dsc = {2: f"Passed the {HOUSE[origin] if origin in passed else HOUSE[other]}" + (f"; failed in the {HOUSE[other]}" if other in failed else ""),
               3: "Passed both houses", 4: "On the governor's desk", 5: "Became law", 6: "Vetoed"}[stage]
    if ip and stage <= 2:
        dsc = f"Indefinitely postponed in the {HOUSE[next((s[1] for s in reversed(steps) if s[3] == 'ip'), origin)]}"
    if govamend and stage == 4:
        dsc = "Returned by the governor with an amendment"
    comm_now = comm if place == "committee" and stage in (0, 2) and not ip else None

    def dates(test, mode="last"):
        ds = sorted({s[0] for s in steps if test(s) and s[0]})
        return {"first": ds[0], "last": ds[-1], "all": ";".join(ds)}[mode] if ds else ""

    action_dates = [s[0] for s in steps if s[0]]
    fvotes.sort(key=lambda v: v[3])
    # The newest text (PDF), for the bill's link.
    link = b.get("reenrolledFileUrl") or b.get("enrolledFileUrl") or b.get("engrossedFileUrl") or b.get("introducedFileUrl") or ""

    # What it does: for a law, the act's summary; else the Legislative Services Agency's synopsis of the bill as
    # introduced.
    what = None
    if stage == 5 and (b.get("actSummary") or "").strip():
        # One summary (HB 66 of 2024) has a replacement character for an apostrophe ("the commodities\ufffd country").
        t = re.sub(r"(?<=[a-z])\ufffd(?=\s|s\b)", "\u2019", re.sub(r"\s+", " ", b["actSummary"]).strip()).replace("\ufffd", "")
        what = {"statement": t, "label": "From the act's summary."}
    elif tx.get("synopsis"):
        what = {"statement": synopsis_text(tx["synopsis"]),
                "label": "From the Legislative Services Agency's synopsis of the bill as introduced."}
    sim = STOCK.sub("", f"{title} {summary} {re.sub(r'This bill would also make nonsubstantive[^.]*.', '', tx.get('synopsis') or '')[:600]}")
    rec = {
        "nums": [p], "base": [p], "prev": earlier(session, b),
        "title": title, "summary": summary, "act": "", "lawCode": "", "law": None, "laws": [],
        "comms": sorted({f"{h} · {c}" for h, c in refs}), "topics": topics, "places": [],
        "narrow": "place" if local else P.narrow_kind(title),
        "commFate": "passed" if dopass or passed else "none", "mainTopic": topics[0] if topics else "", "local": "local" in topics,
        "senDeleg": False, "asmDeleg": False,
        "budget": "Appropriations" in subjects and not const,
        "passedS": "S" in passed, "passedA": "H" in passed, "program": None,
        "stage": stage, "passedIn": (HOUSE[origin] if origin in passed else HOUSE[other]) if stage == 2 else None,
        "chapter": chapter,
        "veto": None, "memo": "", "vetoMemo": None,
        "simText": sim,
        "comm": comm_now if stage == 0 else None,
        "first": min(action_dates, default=f"{session}-01-01"),
        "last": max(action_dates, default=f"{session}-01-01"),
        "cosp": len(cos),
        "keyDates": [
            dates(lambda s: s[3] == "reported", "first"),
            dates(lambda s: s[2] == "PASSED SENATE", "all"),
            dates(lambda s: s[2] == "PASSED HOUSE", "all"),
            "",
            dates(lambda s: s[3] == "sent") if stage >= 4 else "",
            dates(lambda s: s[3] in ("signed", "enacted")) if stage == 5 else "",
            dates(lambda s: s[3] == "vetoed"),
        ],
        "votes": fvotes, "firstComms": [(origin, first_ref, first_report == "pass" or bool(passed))] if first_ref else [],
        "vers": [{"p": p, "sponsor": sponsor, "district": (lead or {}).get("district") or 0, "cosponsors": cos,
                  "primes": 1, "cosp": len(cos), "statusDesc": dsc, "committee": comm_now, "link": link,
                  "actions": [[s[0], s[2]] for s in steps]}],
    }
    if stage == 5 and not any(s[3] in ("signed", "enacted") for s in steps):
        when = b.get("lastActionDate") or rec["last"]
        rec["vers"][0]["actions"].append([when, f"Became law: Act {act}"])
        rec["keyDates"][5] = when
    return rec, what


# ---- Earlier years ----

_KEYS = {}


def _key(b):
    return re.sub(r"[^a-z0-9 ]", "", re.sub(r"\s+", " ", (b.get("shortTitle") or "").lower())).strip()


def _keys(session):
    """A year's bills that didn't become law: short title -> [bill numbers]."""
    if session not in _KEYS:
        out = {}
        for b in (load(session, "bills.json", {}) or {}).get("bills") or []:
            if not re.fullmatch(r"(HB|SB)\d+", b["instrumentNbr"]) or b.get("actNbr"):
                continue  # a law isn't tried again (yearly bills like the budgets share titles)
            out.setdefault(_key(b), []).append(b["instrumentNbr"])
        _KEYS[session] = out
    return _KEYS[session]


def earlier(session, b):
    """The same bill in the two years before: the same short title, held by one bill in each year. Never appropriations
    (each year's are new bills), nor a bill that became law."""
    out = set()
    k = _key(b)
    if len(k.split()) < 4 or "Appropriations" in (b.get("subject") or ""):
        return out
    mine = _keys(session).get(k, [])
    for y in (session - 1, session - 2):
        if y not in sessions():
            continue
        old = _keys(y).get(k, [])
        if len(old) == 1 and len(mine) <= 1:
            out.add((y, old[0]))
    return out


def parties(session, recs):
    if session not in _PARTIES:
        load_session(session)
    return {k: v for k, v in _PARTIES.get(session, {}).items() if v in ("D", "R")}
