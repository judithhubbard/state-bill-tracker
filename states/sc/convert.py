"""South Carolina's bills (downloaded by states/sc/fetch.py from scstatehouse.gov) in the shape build_data.py reads.
General Bills and Joint Resolutions of each two-year General Assembly (the 126th is 2025-26), one record each. Joint
resolutions have the force of law (most approve agencies' regulations or set one-time rules) and become Acts like
bills, so they're shown; the ones proposing an amendment to the South Carolina Constitution are tagged "const".
Concurrent resolutions and resolutions are left out.

The history ("Referred to Committee on Judiciary", "Committee report: Favorable with amendment Judiciary", "Read second
time", "Roll call Yeas-105 Nays-0", "Read third time and sent to Senate", ...) names the house on each line, except the
lines after passage ("Ratified R 167", "Signed By Governor", "Act No. 212"). A house passes a bill on third reading:
"Read third time and sent to Senate" (the first house), "Read third time and enrolled" (the second, unchanged),
"Read third time and returned to House with amendments" (the second, amended: the first has to agree). Back in the first
house: "Concurred in Senate amendment and enrolled", or "Non-concurrence ..." and a conference committee, whose report
both houses adopt ("Conference report received and adopted"), then "Ordered enrolled for ratification". The roll call
usually comes on second reading (the real vote: "Read second time" + "Roll call"); third reading is often by voice.
Enrolled bills are ratified (both presiding officers sign them, "Ratified R 167", the ratification number) and go to
the governor: "Signed By Governor", "Vetoed by Governor", "Certain items vetoed by Governor" (line items of the
budget; the rest is law), then "Veto overridden" in each house (two-thirds of the members present), "Veto sustained".
Acts are numbered through the General Assembly ("Act No. 212"; 2025's are 1-94, 2026's 95-274).

Constitutional amendments: a joint resolution "PROPOSING AN AMENDMENT TO ... THE CONSTITUTION OF SOUTH CAROLINA" passes
each house by two-thirds, is ratified ("No signature required": never the governor) and goes to the voters at the next
general election; if they approve, the next General Assembly passes "AN ACT TO RATIFY AN AMENDMENT ..." (also without
the governor). The proposals are tagged "const" and stop at stage 3; the ratifying acts are laws (Act numbers).
"""
import json, os, re
from datetime import date, datetime
from zoneinfo import ZoneInfo

from states.sc import profile as P

HOUSE = {"S": "Senate", "H": "House"}
CH = {"House": "H", "Senate": "S"}
_CACHE, _SEATS, _PARTIES, _NAMES = {}, {}, {}, {}


def folder(session):
    return os.path.join(P.DATA, str(session))


def sessions():
    out = []
    for f in sorted(os.listdir(P.DATA)) if os.path.isdir(P.DATA) else []:
        if re.fullmatch(r"\d{4}", f) and os.path.exists(os.path.join(P.DATA, f, "bills.json")):
            out.append(int(f))
    return out


def load(session, name, default=None):
    """One of a General Assembly's files (bills, numbers, votes_H, members_S, acts_2026 ...)."""
    key = (session, name)
    if key not in _CACHE:
        try:
            _CACHE[key] = json.load(open(os.path.join(folder(session), f"{name}.json"), encoding="utf-8"))
        except (OSError, ValueError):
            _CACHE[key] = default
    return _CACHE[key]


def member_page(code):
    key = ("members", code)
    if key not in _CACHE:
        try:
            _CACHE[key] = json.load(open(os.path.join(P.DATA, "members", f"{code}.json"), encoding="utf-8"))
        except (OSError, ValueError):
            _CACHE[key] = None
    return _CACHE[key]


def roll(session, key):
    try:
        return json.load(open(os.path.join(folder(session), "rollcalls", f"{key}.json"), encoding="utf-8"))
    except (OSError, ValueError):
        return None


def text(x):
    return re.sub(r"\s+", " ", str(x or "").replace("\xa0", " ")).strip()


def day(s):
    """"12/05/24" -> "2024-12-05"."""
    m = re.match(r"(\d{1,2})/(\d{1,2})/(\d{2,4})", text(s))
    if not m:
        return ""
    y = int(m.group(3))
    return date(y + 2000 if y < 100 else y, int(m.group(1)), int(m.group(2))).isoformat()


# ---- names ---------------------------------------------------------------------------------------------------------

SUFFIX = re.compile(r",?\s+(Jr\.|Sr\.|II|III|IV|V)$")


def parts(full):
    """'Representative James Mikell "Mike" Burns' -> ("James Mikell", "Mike", "Burns", ""); 'Senator Harvey S. Peeler,
    Jr.' -> ("Harvey S.", "", "Peeler", "Jr.")."""
    n = text(full)
    n = re.sub(r"^(?:Representative|Senator|Rep\.|Sen\.)\s+", "", n)
    n = re.sub(r"^Dr\.\s+|,?\s+(?:Ph\.\s?D\.|M\.\s?D\.|Ed\.\s?D\.|Esq\.)(?=,|$)", "", n)
    nick = ""
    m = re.search(r'"([^"]+)"', n)
    if m:
        nick, n = m.group(1), text(n[:m.start()] + n[m.end():])
    suf = ""
    m = SUFFIX.search(n)
    if m:
        suf, n = m.group(1), n[:m.start()].strip()
    words = n.split()
    return " ".join(words[:-1]), nick, words[-1] if words else "", suf


def display(full):
    """A member's name as the site shows it: the name they go by ('Mike Burns', 'Micah Caskey IV'), else as written
    ('G. Murrell Smith, Jr.')."""
    first, nick, last, suf = parts(full)
    name = f"{nick} {last}" if nick else f"{first} {last}".strip()
    return f"{name}{', ' if suf in ('Jr.', 'Sr.') else ' '}{suf}" if suf else name


def norm(w):
    return re.sub(r"[^a-z]", "", (w or "").lower())


# The member lists give each person's district in the office they hold now, not the one they held then: Russell Ott,
# Matt Leber and Jason Elliott are on the 2023-24 House list with their Senate districts (26, 41, 6), Deon Tedder with
# Senate 42, Jermaine Johnson with House 52 (he moved from 70 in 2024), and Wes Climer, now in Congress, with "5" (his
# U.S. House district; he held Senate 15). RJ May III's district is blank. Each correction fits the member's home county
# and the districts the list leaves empty (`python3 -m states.sc.convert` prints seats two members both held to the end).
DISTRICT_FIX = {(2023, "H", "0529545391"): "22", (2023, "H", "0943181705"): "70", (2023, "H", "1074431690"): "116",
                (2023, "H", "1195454402"): "88", (2025, "H", "1195454402"): "88", (2023, "H", "1433096420"): "93",
                (2023, "H", "1811931601"): "109", (2023, "S", "0356818139"): "15", (2025, "S", "0356818139"): "15"}


def party_of(code):
    """A past General Assembly's member list has no parties: the member's party in another session's list, else their
    page's ("Democrat" -> "D")."""
    for s in sessions():
        for h in "HS":
            for m in load(s, f"members_{h}", []) or []:
                if m["code"] == code and m.get("party"):
                    return m["party"]
    pg = member_page(code) or {}
    return {"Democrat": "D", "Republican": "R", "Independent": "I"}.get(text(pg.get("party")), "")


def members(session):
    """code -> {"code", "house", "district", "name" (as shown), "full", "party", "last", "first"} for everyone on the
    General Assembly's member lists (both houses; a member who moved from the House to the Senate is in both)."""
    if session in _NAMES:
        return _NAMES[session]
    out = {}
    for h in "HS":
        for m in load(session, f"members_{h}", []) or []:
            first, nick, last, _ = parts(m.get("name"))
            dist = DISTRICT_FIX.get((session, h, m["code"])) or text(m.get("district"))
            party = m.get("party") or party_of(m["code"])
            out[(h, m["code"])] = {"code": m["code"], "house": h, "district": dist, "full": text(m.get("name")),
                                   "name": display(m.get("name")), "party": party, "last": last,
                                   "first": first.split()[0] if first else "", "nick": nick}
    _NAMES[session] = out
    return out


def roll_index(session):
    """(house, last, first) and (house, last) -> member code, for names as roll calls write them ("Peeler, Harvey S.,
    Jr.")."""
    key = ("rollidx", session)
    if key in _CACHE:
        return _CACHE[key]
    full, by_last = {}, {}
    for (h, code), m in members(session).items():
        full[(h, norm(m["last"]), norm(m["first"]))] = code
        if m["nick"]:
            full[(h, norm(m["last"]), norm(m["nick"]))] = code
        by_last.setdefault((h, norm(m["last"])), []).append(code)
    _CACHE[key] = (full, by_last)
    return _CACHE[key]


def roll_code(session, h, name):
    """A roll call's "Last, First M., Jr." -> the member's code, or None."""
    full, by_last = roll_index(session)
    ps = [p.strip() for p in text(name).replace('"', "").split(",")]
    last = norm(ps[0])
    first = norm(ps[1].split()[0]) if len(ps) > 1 and ps[1].split() else ""
    code = full.get((h, last, first))
    if code:
        return code
    cands = by_last.get((h, last), [])
    if len(cands) == 1:
        return cands[0]
    # "Bright Matthews, Margie" or a last name the list splits differently: the last word.
    words = ps[0].split()
    if len(words) > 1:
        return roll_code(session, h, ", ".join([words[-1]] + ps[1:]))
    return None


def vote_list(session):
    """roll-call KEY -> (house, the vote list's entry)."""
    key = ("votelist", session)
    if key not in _CACHE:
        out = {}
        for h in "HS":
            for v in load(session, f"votes_{h}", []) or []:
                out[v["key"]] = (h, v)
        _CACHE[key] = out
    return _CACHE[key]


def last_votes(session):
    """(house, code) -> the last day the member is named on a roll call in this General Assembly."""
    key = ("lastvotes", session)
    if key in _CACHE:
        return _CACHE[key]
    out = {}
    d = os.path.join(folder(session), "rollcalls")
    for f in os.listdir(d) if os.path.isdir(d) else []:
        r = roll(session, f[:-5])
        if not r or not r.get("head"):
            continue
        h = "S" if r["head"][0].startswith("Senate") else "H"
        when = day(next((x for x in r["head"] if re.match(r"\d\d/\d\d/\d{4}", x)), ""))
        for g, _, names in r.get("groups") or []:
            if g in ("EXCUSED ABSENCE",):
                continue
            for n in names:
                c = roll_code(session, h, n)
                if c:
                    out[(h, c)] = max(out.get((h, c), ""), when)
    _CACHE[key] = out
    return out


def seats(session):
    """(house, code) -> seat id ("S:12", "H:71") for the member who held each seat last in this General Assembly (by the
    last roll call each was named on); members who left (Wes Climer's predecessor, a member elected to the other house)
    are "H?Tedder"."""
    if session in _SEATS:
        return _SEATS[session]
    lv = last_votes(session)
    by = {}
    for (h, code), m in members(session).items():
        if re.fullmatch(r"\d+", m["district"]):
            by.setdefault(f"{h}:{int(m['district'])}", []).append(m)
    out = {}
    for sid, ms in by.items():
        h = sid[0]
        ms.sort(key=lambda m: (lv.get((h, m["code"]), ""), m["code"]))
        for i, m in enumerate(ms):
            out[(h, m["code"])] = sid if i == len(ms) - 1 else f"{h}?{m['last']}"
    _SEATS[session] = out
    return out


def sponsor_name(session, sp, origin):
    """A sponsor entry ({"code", "name": "C. Mitchell", "chamber"}) -> the name shown; a committee's byline as the
    committee's name."""
    code = sp.get("code")
    h = sp.get("chamber") or origin
    if not code:
        n = text(sp.get("name"))
        return n if re.search(r"Committee$", n) else f"{n} Committee"
    m = members(session).get((h, code)) or members(session).get(("S" if h == "H" else "H", code))
    if m:
        return m["name"]
    pg = member_page(code)
    return display(pg["name"]) if pg and pg.get("name") else text(sp.get("name"))


# ---- titles and "What it does" -------------------------------------------------------------------------------------

ALWAYS = {"south carolina": "South Carolina", "s.c.": "S.C.", "united states": "United States", "u.s.": "U.S.",
          "general assembly": "General Assembly", "code of laws": "Code of Laws", "medicaid": "Medicaid",
          "medicare": "Medicare", "dhec": "DHEC", "ffa": "FFA", "covid-19": "COVID-19", "i": "I", "ii": "II", "iii": "III",
          "iv": "IV", "v": "V", "vi": "VI", "vii": "VII", "viii": "VIII", "ix": "IX", "x": "X", "xi": "XI", "xii": "XII",
          "xiii": "XIII", "xiv": "XIV", "xv": "XV", "xvi": "XVI", "xvii": "XVII", "viii-a": "VIII-A", "llc": "LLC",
          "january": "January", "february": "February", "march": "March", "april": "April", "june": "June",
          "july": "July", "august": "August", "september": "September", "october": "October", "november": "November",
          "december": "December", "constitution": "Constitution", "atlantic": "Atlantic", "clemson": "Clemson",
          "usc": "USC", "sled": "SLED", "dmv": "DMV", "ems": "EMS", "pfas": "PFAS", "ai": "AI", "dna": "DNA", "hiv": "HIV",
          "fy": "FY", "beaufort": "Beaufort", "charleston": "Charleston", "columbia": "Columbia", "myrtle beach": "Myrtle Beach",
          "hilton head": "Hilton Head", "rock hill": "Rock Hill", "christian": "Christian", "american": "American",
          "america": "America", "african": "African", "native": "Native"}
for _c in P.COUNTY_NAMES:
    ALWAYS[_c.lower() + " county"] = _c + " County"
# Agencies, courts and programs the titles name often (the titles are in capitals, so names are put back from this list).
for _n in ["Department of Transportation", "Department of Revenue", "Department of Health and Human Services",
           "Department of Education", "State Board of Education", "Department of Social Services", "Department of Corrections",
           "Department of Public Safety", "Department of Motor Vehicles", "Department of Natural Resources",
           "Department of Agriculture", "Department of Commerce", "Department of Labor, Licensing and Regulation",
           "Department of Juvenile Justice", "Department of Mental Health", "Department of Environmental Services",
           "Department of Public Health", "Department of Health and Environmental Control", "Department of Insurance",
           "Department of Employment and Workforce", "Department of Administration", "Department of Veterans' Affairs",
           "Department of Archives and History", "Department of Parks, Recreation and Tourism", "Department of Consumer Affairs",
           "Department of Disabilities and Special Needs", "Department of Alcohol and Other Drug Abuse Services",
           "Department of Probation, Parole and Pardon Services", "Public Service Commission", "Office of Regulatory Staff",
           "State Election Commission", "State Ethics Commission", "Judicial Merit Selection Commission",
           "Commission on Higher Education", "Revenue and Fiscal Affairs Office", "State Law Enforcement Division",
           "Workers' Compensation Commission", "Criminal Justice Academy", "Attorney General", "Secretary of State",
           "Lieutenant Governor", "Adjutant General", "Comptroller General", "State Treasurer", "Supreme Court",
           "Court of Appeals", "National Guard", "Palmetto Fellows", "LIFE Scholarship", "HOPE Scholarship",
           "University of South Carolina", "Medical University of South Carolina", "Clemson University", "The Citadel",
           "Coastal Carolina University", "Winthrop University", "South Carolina State University", "College of Charleston",
           "Francis Marion University", "Lander University", "United States Congress", "Congress",
           "Residential Landlord and Tenant Act", "Freedom of Information Act", "Administrative Procedures Act",
           "Alcoholic Beverage Control Act", "Children's Code", "Rural Infrastructure Authority", "Santee Cooper",
           "Ports Authority", "Education Lottery", "Retirement System", "Police Officers Retirement System",
           "Public Employee Benefit Authority", "Statehouse", "State House", "Capital Reserve Fund", "General Fund"]:
    ALWAYS[_n.lower()] = _n
_PHRASES = sorted((k for k in ALWAYS if " " in k or "." in k or "-" in k), key=len, reverse=True)
_WORDS = {k: v for k, v in ALWAYS.items() if k not in _PHRASES}
# Agencies and offices, after the general rules: "the Department of Health and Human Services".
_OFFICE = re.compile(r"\b(department|commission|board|office|division|council|authority|agency|institute|bureau|university|college|"
                     r"committee|panel|fund|trust|program|act|court|commissioner|secretary|inspector general|treasurer|comptroller|"
                     r"adjutant general|attorney general|governor|lieutenant governor|ombudsman)( of)? ")


def official(caps):
    """The official title without the trailer "- ratified title" some carry."""
    return re.sub(r"\s*-?\s*ratified title\.?\s*$", "", text(caps), flags=re.I)


def sentence(caps):
    """A title in capitals -> sentence case, with the names it can be sure of restored ("South Carolina", counties,
    "Code of Laws", months, Roman numerals); quoted act names are title-cased ('the "Fentanyl Awareness Act"')."""
    t = official(caps)
    if re.search(r"[a-z]", t):
        return t
    t = t.lower()
    for k in _PHRASES:
        t = re.sub(rf"(?<![a-z]){re.escape(k)}(?![a-z])", ALWAYS[k], t)
    t = re.sub(r"\b[a-z][a-z'-]*\b", lambda m: _WORDS.get(m.group(0), m.group(0)), t)
    t = re.sub(r"\bmay (?=\d)", "May ", t)
    t = re.sub(r'"([^"]+)"', lambda m: '"' + re.sub(r"\b([a-z])([a-z']*)", lambda w: w.group(0) if w.group(0) in ("of", "and", "the", "for", "to", "in", "on", "a", "an", "or") else w.group(1).upper() + w.group(2), m.group(1)).replace('" ', '"') + '"', t)
    t = re.sub(r'"([a-z])', lambda m: '"' + m.group(1).upper(), t)
    t = re.sub(r"\b(article|section|chapter|title|part|act|regulation document number|document number) ([0-9ivxl]+[a-z0-9.-]*)",
               lambda m: m.group(1) + " " + (m.group(2).upper() if re.fullmatch(r"[ivxl]+(-a)?", m.group(2)) else m.group(2)), t)
    return t[:1].upper() + t[1:]


def clauses(caps):
    """The official title's "SO AS TO ..." clauses (and a joint resolution's "TO ..."), each one thing the bill does:
    "AN ACT TO AMEND ... SECTION 63-1-40 ..., SO AS TO ELIMINATE PLAYING A PINBALL MACHINE AS A STATUS OFFENSE; AND BY
    REPEALING SECTION 63-19-2430 ..." -> ["eliminate playing a pinball machine as a status offense", "repealing section
    63-19-2430 ..."]. Section references and "relating to ..." stay out of the clauses but repeals and additions are
    kept as such."""
    t = official(caps).rstrip(". ")
    out = []
    for piece in re.split(r";\s*(?:AND\s+)?(?=BY |TO |AND TO )", t):
        m = re.search(r"\bSO AS TO (.+)$", piece, re.S)
        if m:
            out.append(m.group(1))
            continue
        m = re.match(r"^(?:A BILL|AN ACT|A JOINT RESOLUTION)\s+TO\s+(?!AMEND\b)(.+)$", piece, re.S) or \
            re.match(r"^(?:AND )?TO\s+(?!AMEND\b)(.+)$", piece, re.S)
        if m:
            out.append(m.group(1))
            continue
        m = re.match(r"^(?:AND )?BY (REPEALING .+)$", piece, re.S)
        if m:
            out.append(m.group(1))
    # Drop each clause's trailing "RELATING TO ..." when it's only a section's subject (after a section number).
    out = [re.sub(r"\s+", " ", c).strip(" ,;") for c in out]
    return [c for c in out if len(c) > 8]


def verb(c):
    """"provide that ..." -> "Provides that ..."; "repealing section ..." -> "Repeals section ..."."""
    w, _, rest = c.partition(" ")
    lw = w.lower()
    if lw in ("further", "also") and rest:
        return f"{w} {verb(rest)}"
    if lw.endswith("ing"):
        base = lw[:-3]
        v = {"repeal": "repeals", "add": "adds", "amend": "amends", "provid": "provides", "establish": "establishes",
             "creat": "creates", "defin": "defines", "requir": "requires", "mak": "makes", "chang": "changes"}.get(base, base + "s")
    elif re.search(r"[^aeiou]y$", lw):
        v = lw[:-1] + "ies"
    elif re.search(r"(s|sh|ch|x|z|o)$", lw) and lw not in ("do",):
        v = lw + "es"
    else:
        v = lw + "s"
    return f"{v} {rest}".strip()


def purpose(caps):
    """What the official title says the bill does, as sentences: "Eliminates playing a pinball machine as a status
    offense. Repeals section 63-19-2430 ..."; "" when the title says only which sections it amends."""
    cs = clauses(caps)
    if not cs:
        return ""
    lines = []
    # A clause that goes on ", AND TO PROVIDE ..." is two.
    cs = [x.strip(" ,") for c in cs for x in re.split(r"(?:,? AND|,) TO (?!(?:THE|A|AN|BE|ITS|THIS|THAT|SUCH|WHICH|WHOM|ANY|EACH|ALL|CERTAIN)\b)(?=[A-Z]+ )", c) if x.strip(" ,")]
    for c in cs[:12]:
        s = verb(sentence(c)).rstrip(" ,;")
        s = s[:1].upper() + s[1:]
        lines.append(s + ("" if re.search(r"\.[\"”]?$", s) else "."))
    if len(cs) > 12:
        lines.append(f"And {len(cs) - 12} more changes (see the bill's title).")
    return "\n".join(lines)


AMEND_TITLE = re.compile(r"^\W*A JOINT RESOLUTION (?:TO )?(?:CONSTITUTION )?PROPOS\w* (?:AN?D? )?(?:AMENDMENTS? )?.*?\bCONSTITUTION OF (?:SOUTH CAROLINA|THIS STATE)", re.S)
RATIFY_TITLE = re.compile(r"^\W*AN ACT TO RATIFY (?:AN )?AMENDMENTS? TO .*?\b(?:CONSTITUTION OF SOUTH CAROLINA|S\.C\. CONSTITUTION|CONSTITUTION OF THIS STATE)", re.S)


def is_amendment(b):
    """A joint resolution proposing an amendment to the South Carolina Constitution (not one ratifying an amendment to
    the federal Constitution)."""
    return b.get("kind") == "Joint Resolution" and bool(AMEND_TITLE.match(text(b.get("title"))[:400]))


def relating(caps):
    """The title's first "RELATING TO X" subject, sentence-cased: "voter qualifications"."""
    m = re.search(r"\bRELATING TO (?:THE )?(.+?)(?:,? SO AS TO\b|,? BY \w+ING\b|,? TO PROVIDE\b|;|\.?$)", caps)
    if not m:
        return ""
    t = sentence(m.group(1))
    return t[:1].lower() + t[1:]


def kept(b):
    """General Bills and Joint Resolutions. The search's kind is sometimes wrong (S 729 of 2025-26, "A CONCURRENT
    RESOLUTION TO REQUEST ...", is listed as a General Bill; a 2023 "A SENATE RESOLUTION" too): the title decides."""
    return b.get("kind") in ("General Bill", "Joint Resolution") and \
        re.match(r"^\W*(?:A BILL|AN ACT|A JOINT RESOLUTION)\b", text(b.get("title"))) is not None


def titled(b, amendment):
    s = text(b.get("subject")).strip(" .")
    s = s[:1].upper() + s[1:] if s else sentence(re.sub(r"^\W*(?:A BILL|AN ACT|A JOINT RESOLUTION)\s+TO\s+", "", text(b.get("title"))))[:150]
    if amendment:
        # The subject line often says only "Constitutional amendment": what's left of it, else the title's subject.
        rest = re.sub(r"\b(?:constitutional (?:amendment|referendum|ballot question)(?: proposed)?|constitution|amendment)\b[\s,:-]*", "", s, flags=re.I).strip(" ,:-")
        if len(rest.split()) < 2 or len(rest) < 8:
            rest = relating(text(b.get("title"))) or rest or "proposed"
        s = rest
        return f"Constitutional amendment: {s if re.match(r'[A-Z]{2}|\S+ .*\b[A-Z]', s) else s[:1].lower() + s[1:]}"
    if RATIFY_TITLE.match(text(b.get("title"))):
        if re.search(r"\bratif|constitution", s, re.I):
            s = relating(text(b.get("title"))) or s
        return f"Ratifying a constitutional amendment: {s[:1].lower() + s[1:] if not re.match(r'[A-Z]{2}|[A-Z][a-z]+ [A-Z]', s) else s}"
    return s


# ---- the history ---------------------------------------------------------------------------------------------------

BILL_MOTION = re.compile(r"^(?:Passage of (?:Bill|Joint Resolution)|[23](?:nd|rd) Reading|Concur in (?:Senate|House) Amendments?|"
                         r"to concur|Adopt (?:Free )?Conference Report|to adopt the (?:free )?conference report|"
                         r"Override Veto(?: by the Governor)?|to override the veto|Sustain Veto)\s*$", re.I)
COMM = re.compile(r"^(?:Pursuant to Rule [\d.]+, )?(Referred to|Recommitted to|Committed to|Recalled from) Committee on (.+)$")
DELEG = re.compile(r"^(Referred to|Recommitted to|Committed to|Recalled from|Polled out of) (?:the )?(?:(\w[\w. ]*?) Delegation|delegation (?:from )?(\w[\w. ]*?)(?: County)?)$")
ENROLLED = re.compile(r"enrolled for ratificat|^Read third time and enrolled|^Concurred in (?:Senate|House) amendment and enrolled|^Enrolled for Ratification", re.I)
OTHER = {"S": "H", "H": "S"}


def committee_name(c):
    c = text(c).replace(" & ", " and ")
    return re.sub(r"^Regulations, Admin\. Procedures, Artificial Intelligence and Cybersecurity$", "Regulations and Administrative Procedures", c)


def load_session(session):
    """Read one General Assembly's bills: (records, bill number -> record index, fetched time, delegation)."""
    bills = load(session, "bills", {}) or {}
    seat = seats(session)
    parties = _PARTIES.setdefault(session, {})
    for (h, code), m in members(session).items():
        if m["party"] in ("D", "R"):
            parties[(h, m["name"])] = m["party"]
    path = os.path.join(folder(session), "bills.json")
    fetched = datetime.fromtimestamp(os.path.getmtime(path), ZoneInfo(P.TIMEZONE)).strftime("%Y-%m-%d %H:%M") if os.path.exists(path) else ""
    acts = {}
    for y in (session, session + 1):
        for a in load(session, f"acts_{y}", []) or []:
            acts[a["bill"]] = (y, a)
    recs, index, texts = [], {}, {}
    keys = sorted(bills, key=lambda k: (k[0] != "H", int(re.sub(r"\D", "", k))))
    for k in keys:
        b = bills[k]
        if not kept(b):
            continue
        rec, what = record(session, k, b, seat, acts.get(k))
        index[k] = len(recs)
        recs.append(rec)
        if what:
            texts[k] = {"statement": what, "label": "From the bill's official title."}
    json.dump(texts, open(os.path.join(P.DATA, f"texts_{session}.json"), "w"), ensure_ascii=False)
    return recs, index, fetched, {"SENATE": [], "ASSEMBLY": []}


def record(session, p, b, seat, act_row):
    origin = p[0]
    other = OTHER[origin]
    amendment = is_amendment(b)
    ratifying = bool(RATIFY_TITLE.match(text(b.get("title"))))
    votelist = vote_list(session)
    hist = b.get("history") or []

    steps = []  # (date, house or "G", wording, kind)
    vote_steps = []  # (date, house, key)
    passed, failed = {}, set()  # house -> index in steps of its passage
    amended_by = None  # the house that last amended it after the other passed it (the other has to agree)
    conf = set()  # houses that adopted the conference report
    both = False
    where_h, place, comm, first_ref, refs = origin, "committee", None, None, []
    reported = recalled = delegated = False
    ratified = no_sign = signed = vetoed = item = False
    overrides, sustained = set(), False
    last_decisive = {}
    intro_done = False
    pending_ref = {}  # house -> committee of a prefiled referral, to drop the repeat at introduction
    for i, x in enumerate(hist):
        d, t = day(x.get("date")), text(x.get("action"))
        h = CH.get(x.get("chamber"), "")
        H = HOUSE.get(h, "")
        if x.get("vote"):
            lh, entry = votelist.get(x["vote"], (h, None))
            if entry and BILL_MOTION.match(text(entry.get("motion"))):
                vote_steps.append((d, lh or h, x["vote"]))
        if t == "Prefiled":
            steps.append((d, h, "Prefiled", "intro"))
            intro_done = True
            continue
        if re.match(r"Introduced", t):
            if not intro_done or h != origin:
                steps.append((d, h, "Introduced" if h == origin else f"Received in the {H}", "intro"))
            intro_done = True
            where_h = h
            if "placed on calendar without reference" in t:
                place = "floor"
                steps.append((d, h, f"Placed on the {H} calendar without going to a committee", "nocomm"))
            elif "local & uncontested calendar" in t:
                place = "floor"
                steps.append((d, h, "Placed on the Senate's local and uncontested calendar", "nocomm"))
            continue
        m = COMM.match(t)
        if m:
            verbw, c = m.group(1), committee_name(m.group(2))
            if c.endswith(" Delegation"):  # "Referred to Committee on Greenville Delegation"
                delegated = True
            if verbw == "Recalled from":
                place, recalled = "floor", True
                steps.append((d, h, f"Taken out of the {c} Committee and placed on the calendar", "recall"))
                continue
            if verbw == "Referred to" and pending_ref.get(h) == c and steps and steps[-1][3] in ("intro", "ref"):
                continue  # the prefiled referral, repeated at introduction
            pending_ref[h] = c
            comm, place, where_h = c, "committee", h
            refs.append((h, c))
            if first_ref is None and h == origin:
                first_ref = c
            steps.append((d, h, f"REFERRED TO {c.upper()}" if verbw == "Referred to" else f"{verbw.upper()} {c.upper()}", "ref"))
            continue
        m = DELEG.match(t)
        if m:
            county = text(m.group(2) or m.group(3))
            c = f"{county} County Delegation" if not county.endswith("County") else f"{county} Delegation"
            delegated = True
            if m.group(1) == "Recalled from":
                place, recalled = "floor", True
                steps.append((d, h, f"Taken back from the {c} and placed on the calendar", "recall"))
                continue
            if m.group(1) == "Polled out of":
                place, reported = "floor", True
                steps.append((d, h, "REPORTED", "reported"))
                continue
            comm, place, where_h = c, "committee", h
            refs.append((h, c))
            if first_ref is None and h == origin:
                first_ref = c
            steps.append((d, h, f"REFERRED TO {c.upper()}", "ref"))
            continue
        m = re.match(r"(?:Committee|Delegation) report: (.+)$", t)
        if m:
            body = m.group(1)
            mm = re.match(r"(Majority favorable(?: with amend\.)?,? minority unfavorable|Favorable with amendment|Favorable|Unfavorable)\s+(.+)$", body)
            kind_, c = (mm.group(1), committee_name(mm.group(2))) if mm else ("", committee_name(body))
            if c.endswith(" Delegation") and not re.search(r"County Delegation$", c):
                c = c.replace(" Delegation", " County Delegation")
            if kind_.startswith("Unfavorable"):
                steps.append((d, h, f"The {c} reported it unfavorably", "unfav"))
                place = "floor"
                continue
            reported = True
            place, where_h = "floor", h
            steps.append((d, h, "REPORTED", "reported"))
            how = {"Favorable with amendment": "approved it with amendments", "Favorable": "approved it"}.get(kind_, "approved it (a minority opposed)")
            steps.append((d, h, f"The {c}{'' if c.endswith('Delegation') else ' Committee'} {how}", "report"))
            continue
        m = re.match(r"Polled out of committee (.+)$", t)
        if m:
            c = committee_name(m.group(1))
            reported = True
            place, where_h = "floor", h
            steps.append((d, h, "REPORTED", "reported"))
            steps.append((d, h, f"Polled out of the {c} Committee (its members approved it by a written poll)", "report"))
            continue
        m = re.match(r"Referred to Subcommittee: (.+)$", t)
        if m:
            steps.append((d, h, f"Sent to a subcommittee: {m.group(1)}", "subref"))
            continue
        if t == "Read second time":
            place, where_h = "floor", h
            last_decisive[h] = "second"
            steps.append((d, h, f"Read a second time in the {H} (its main vote)", "second"))
            continue
        m = re.match(r"Roll call (?:Yeas|Ayes)-(\w+) Nays-(\w+)", t)
        if m:
            steps.append((d, h, f"The {H} vote: {m.group(1)}-{m.group(2)}" if m.group(1).isdigit() else f"The {H} vote (a roll call)", "tally"))
            continue
        if t in ("Second Reading Failed", "Rejected"):
            failed.add(h)
            last_decisive[h] = "fail"
            steps.append((d, h, f"Failed in the {H} on second reading" if t.startswith("Second") else f"Rejected by the {H}", "fail"))
            continue
        m = re.match(r"(?:Read third time|Adopted)(?: and (sent to|returned to|enrolled)\s*(House|Senate)?(?: with (amendments|concurrence))?|, (sent to|returned to) (House|Senate)(?: with (concurrence))?)?$", t)
        if m and h:
            kind = m.group(1) or m.group(4) or ""
            amended = m.group(3) == "amendments"
            place, where_h = "floor", h
            passed[h] = len(steps)
            failed.discard(h)
            last_decisive[h] = "pass"
            steps.append((d, h, f"PASSED {H.upper()}", "pass"))
            if kind == "enrolled" or (kind == "returned to" and not amended and passed.get(OTHER[h]) is not None):
                both = True
                steps.append((d, h, "Enrolled: passed both houses in the same form", "enrolled"))
            elif kind == "returned to" and amended:
                amended_by = h
                place, where_h = "desk", OTHER[h]
                steps.append((d, h, f"Sent back to the {HOUSE[OTHER[h]]} with amendments", "back"))
            elif kind == "sent to":
                place, where_h, comm = "committee", OTHER[h], None
            continue
        if t in ("Reconsidered vote whereby read third time", "Reconsider vote whereby read third time and returned with amendments"):
            passed.pop(h, None)
            last_decisive.pop(h, None)
            place, where_h = "floor", h
            steps.append((d, h, f"The {H} voted to reconsider its passage", "rescind"))
            continue
        if t == "Reconsider vote whereby read second time" or (t == "Reconsidered" and last_decisive.get(h) == "fail"):
            failed.discard(h)
            last_decisive.pop(h, None)
            steps.append((d, h, f"The {H} voted to reconsider its vote", "rescind"))
            continue
        m = re.match(r"Concurred in (House|Senate) amendment and enrolled", t)
        if m:
            both = True
            passed[h] = len(steps)
            steps.append((d, h, f"The {H} agreed to the {m.group(1)}'s amendments", "concur"))
            steps.append((d, h, "Enrolled: passed both houses in the same form", "enrolled"))
            continue
        m = re.match(r"Non-concurrence in (House|Senate) amendment", t)
        if m:
            steps.append((d, h, f"The {H} refused to agree to the {m.group(1)}'s amendments", "nonconcur"))
            continue
        if re.match(r"(House|Senate) amendment amended$", t):
            amended_by = h
            steps.append((d, h, f"The {H} amended the {re.match(r'(House|Senate)', t).group(1)}'s amendments", "amend"))
            continue
        m = re.match(r"(?:Returned to (House|Senate) with amendments|Returned to (House|Senate)|Returned)$", t)
        if m:
            steps.append((d, h, f"Sent back to the {m.group(1) or m.group(2) or HOUSE.get(OTHER.get(h, ''), 'other house')}" + (" with amendments" if "amendments" in t else ""), "back"))
            continue
        m = re.match(r"(?:Free )?[Cc]onference report (?:received and )?adopted", t)
        if m:
            conf.add(h)
            steps.append((d, h, f"The {H} adopted the {'free ' if t.startswith('Free') else ''}conference committee's report", "ccr"))
            if conf >= {"S", "H"}:
                both = True
                passed["S"], passed["H"] = passed.get("S", len(steps)), passed.get("H", len(steps))
            continue
        if re.match(r"Conference report rejected", t):
            conf.discard(h)
            steps.append((d, h, f"The {H} rejected the conference committee's report", "ccrfail"))
            continue
        if re.search(r"(?:insists upon amendment and )?conference committee appointed|Free conference (?:committee appointed|powers)", t, re.I):
            conf_txt = re.sub(r"^.*?(conference committee appointed|free conference committee appointed|free conference powers \w+)\s*", lambda mm: mm.group(1)[:1].upper() + mm.group(1)[1:] + ": ", t, flags=re.I).rstrip(": ")
            if re.match(r"(?:House|Senate) insists", t):
                conf_txt = f"The {H} insisted on its amendments; " + conf_txt[:1].lower() + conf_txt[1:]
            if re.search(r"powers", t, re.I):
                conf = set()  # free conference powers: a new report, which both houses need
            steps.append((d, h, conf_txt, "conf"))
            continue
        m = re.match(r"(House|Senate) recedes from (?:\w+ )?amendment", t)
        if m:
            steps.append((d, h, f"The {H} dropped its amendments", "recede"))
            continue
        if ENROLLED.search(t):
            both = True
            steps.append((d, h, "Enrolled: passed both houses in the same form", "enrolled"))
            continue
        m = re.match(r"Ratified R (\d+)", t)
        if m:
            ratified = True
            both = True
            steps.append((d, "G", f"Ratified (R {m.group(1)}): signed by the presiding officers", "ratified"))
            if not amendment and not ratifying:
                steps.append((d, "G", "DELIVERED TO GOVERNOR", "sent"))
            continue
        if t == "No signature required":
            no_sign = True
            steps.append((d, "G", "No signature required: it doesn't go to the governor", "nosign"))
            continue
        if t == "Signed By Governor":
            signed = True
            steps.append((d, "G", "Signed by the governor", "signed"))
            continue
        if t == "Certain items vetoed by Governor":
            signed = item = True
            steps.append((d, "G", "Signed by the governor, with some items vetoed (line-item veto)", "signed"))
            continue
        if t == "Vetoed by Governor":
            vetoed = True
            steps.append((d, "G", "VETOED", "vetoed"))
            continue
        m = re.match(r"Veto overridden(?: by originating body)? (?:Yeas|Ayes)-(\d+) Nays-(\d+)", t)
        if m and h:
            overrides.add(h)
            steps.append((d, h, f"The {H} voted to override the veto, {m.group(1)}-{m.group(2)}", "override"))
            continue
        m = re.match(r"Veto sustained (?:Yeas|Ayes)-(\d+) Nays-(\d+)", t)
        if m:
            sustained = True
            steps.append((d, h, f"The {H} failed to override the veto (sustained), {m.group(1)}-{m.group(2)}", "sustain"))
            continue
        if t == "Veto tabled":
            steps.append((d, h, f"The {H} tabled the veto (no override vote)", "vetotable"))
            continue
        m = re.match(r"Vetos? ([\d ,-]+?) ?continued", t)
        if m:
            steps.append((d, h, f"The {H} put off the vetoed items ({m.group(1).replace(' ', '')})", "other"))
            continue
        m = re.match(r"Act No\. (\d+)", t)
        if m:
            steps.append((d, "G", f"Act No. {m.group(1)}", "actno"))
            continue
        if t.startswith("Effective date"):
            rest = text(t[len("Effective date"):])
            steps.append((d, "G", f"Takes effect {day(rest) and fmt(day(rest)) or rest[:1].lower() + rest[1:]}" if rest else "Effective date set", "effective"))
            continue
        if t == "Amended" or t == "Committee Amendment Adopted":
            steps.append((d, h, f"Amended in the {H}" if t == "Amended" else f"The committee's amendment was adopted in the {H}", "amend"))
            continue
        if t.startswith("Member(s) request name"):
            steps.append((d, h, t.replace("Member(s) request name added as sponsor:", "Sponsors added:").replace("Member(s) request name removed as sponsor:", "Sponsors removed:"), "cosp"))
            continue
        if t == "Scrivener's error corrected":
            steps.append((d, h or "G", "Scrivener's error corrected", "routine"))
            continue
        if t.startswith("Requests for debate"):
            steps.append((d, h, re.sub(r"^Requests for debate( removed)?-Rep\(s\)\.\s*", lambda mm: "Debate requests withdrawn: " if mm.group(1) else "Debate requested (a contested bill): ", t), "routine"))
            continue
        if re.match(r"Unanimous consent for (?:second and )?third reading", t):
            steps.append((d, h, f"Third reading set for the next day, by unanimous consent", "routine"))
            continue
        steps.append((d, h or "G", t, "other"))

    # Sort by day, keeping the site's order within a day (Act numbers and effective dates are listed last).
    steps = [s for _, s in sorted(enumerate(steps), key=lambda e: (e[1][0] or "9999", e[0]))]

    # Laws and vetoes. A veto stands unless both houses overrode it.
    overridden = vetoed and overrides >= {"S", "H"}
    law = (signed and not (vetoed and not overridden)) or overridden or (no_sign and not amendment)
    if act_row and not law and not amendment and not vetoed:
        law = True  # in the Acts list though the history stops short
        steps.append((day(act_row[1].get("effective")) or steps[-1][0] if steps else f"{act_row[0]}-01-01", "G", "Became law (from the list of Acts)", "lawnote"))
    if overridden and not any(s[3] == "lawnote" for s in steps):
        last_override = max(s[0] for s in steps if s[3] == "override")
        steps.append((last_override, "G", "Became law over the governor's veto", "lawnote"))
        steps = [s for _, s in sorted(enumerate(steps), key=lambda e: (e[1][0] or "9999", e[0]))]

    both = both or ratified or law or vetoed or conf >= {"S", "H"}
    # The second house amended it and the first hasn't agreed: not passed both houses, whatever came before.
    if amendment:
        stage = 3 if both else 2 if passed else None
    elif law:
        stage = 5
    elif vetoed:
        stage = 6
    elif ratified:
        stage = 4
    elif both:
        stage = 3
    elif passed:
        stage = 2
    else:
        stage = None
    passed_h = set(passed)
    if stage is not None and stage >= 3:
        passed_h = {"S", "H"}
    if stage is None:
        stage = 1 if place == "floor" or origin in failed else 0

    act_no = text(b.get("act")) if stage == 5 and b.get("act") else (text(act_row[1]["act"]) if stage == 5 and act_row else "")
    chapter = int(act_no) if act_no.isdigit() else None
    comm_now = comm if place == "committee" and stage in (0, 2) else None
    title = titled(b, amendment)
    caps = official(b.get("title"))
    summary = sentence(caps)
    narrow = P.narrow_kind(caps, delegated)
    topics = list(dict.fromkeys((["const"] if amendment else []) +
                                (["local"] if narrow == "place" else []) +
                                [P.COMMITTEE_TOPICS[c] for _, c in refs if c in P.COMMITTEE_TOPICS] +
                                [k for k in P.TOPIC_WORDS if P.TOPIC_WORDS[k].search(text(b.get("subject")) + " " + summary)]))
    first_released = reported or recalled
    fate = "passed" if first_released or passed else "none"

    names = []
    for sp in b.get("sponsors") or []:
        n = sponsor_name(session, sp, origin)
        if n and n not in names:
            names.append(n)
    sponsor = names[0] if names else (text(b.get("by")) or "—")
    cos = names[1:]
    where = HOUSE.get(where_h, HOUSE[origin])
    if stage == 0:
        desc = f"In the {comm}" if comm and comm.endswith("Delegation") else f"In {where} committee"
    elif stage == 1:
        desc = f"Failed in the {HOUSE[origin]}" if origin in failed else f"On the {where} calendar"
    else:
        desc = {2: f"Passed the {HOUSE[origin] if origin in passed_h else HOUSE[other]}" + (f"; failed in the {HOUSE[other]}" if other in failed else ""),
                3: "Passed both houses" + ("" if not amendment else "; goes to the voters"), 4: "On the governor's desk",
                5: "Became law", 6: "Vetoed"}[stage]

    def dates(test, mode="last"):
        ds = sorted({s[0] for s in steps if test(s) and s[0]})
        return {"first": ds[0], "last": ds[-1], "all": ";".join(ds)}[mode] if ds else ""

    votes = floor_votes(session, vote_steps, seat)
    action_dates = [s[0] for s in steps if s[0]]
    budget = bool(re.match(r"^\W*AN ACT TO MAKE APPROPRIATIONS AND TO PROVIDE REVENUES", caps)) or \
        bool(re.match(r"^\W*A JOINT RESOLUTION TO APPROPRIATE MONIES FROM THE CAPITAL RESERVE FUND", caps))
    what = "" if budget else purpose(caps)  # (the budget's title says only that it makes appropriations)
    rec = {
        "nums": [p], "base": [p], "prev": earlier(session, p, b),
        "title": title, "summary": summary if re.search(r"\.[\"”]$", summary) else summary.rstrip(".") + ".",
        "act": "", "lawCode": "", "law": None, "laws": [],
        "comms": sorted({f"{h} · {c}" for h, c in refs}), "topics": topics, "places": [], "narrow": narrow,
        "commFate": fate, "mainTopic": topics[0] if topics else "", "local": "local" in topics,
        "senDeleg": False, "asmDeleg": False, "budget": budget,
        "passedS": "S" in passed_h, "passedA": "H" in passed_h, "program": None,
        "stage": stage, "passedIn": (HOUSE[origin] if origin in passed_h else HOUSE[other]) if stage == 2 else None,
        "chapter": chapter, "veto": None, "memo": "", "vetoMemo": None,
        "simText": f"{title} {sim_text(caps)}",
        "comm": comm_now if stage == 0 else None,
        "first": min(action_dates, default=f"{session}-01-01"),
        "last": max(action_dates, default=f"{session}-01-01"),
        "cosp": len(cos),
        "keyDates": [
            dates(lambda s: s[3] in ("reported", "recall", "nocomm", "second"), "first"),
            dates(lambda s: s[2] == "PASSED SENATE", "all"),
            dates(lambda s: s[2] == "PASSED HOUSE", "all"),
            "",
            dates(lambda s: s[3] == "sent"),
            dates(lambda s: s[3] in ("signed", "lawnote", "nosign")) if stage == 5 else "",
            dates(lambda s: s[3] == "vetoed"),
        ],
        "votes": votes, "firstComms": [(origin, first_ref, bool(first_released) or bool(passed))] if first_ref else [],
        "vers": [{"p": p, "sponsor": sponsor, "district": 0, "cosponsors": cos, "primes": 1, "cosp": len(cos),
                  "statusDesc": desc, "committee": comm_now,
                  "actions": [[s[0], s[2]] for s in steps]}],
    }
    if item and stage == 5:
        rec["vers"][0]["itemVeto"] = True
    return rec, what


def fmt(iso):
    y, m, d = iso.split("-")
    return f"{['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'][int(m) - 1]} {int(d)}, {y}"


def floor_votes(session, vote_steps, seat):
    """The bill's own floor roll calls (second and third readings, concurrence, conference reports, veto overrides),
    member by member from each roll call's PDF: "N" no, "E" excused absence, "B" not voting, abstaining or present; yes
    is left out. Amendment and procedural roll calls aren't the bill's."""
    out, used = [], set()
    for d, h, key in vote_steps:
        if key in used:
            continue
        used.add(key)
        r = roll(session, key)
        lh, entry = vote_list(session).get(key, (h, {}))
        h = lh or h
        if not r:
            c = (entry or {}).get("counts") or {}
            if c:
                out.append([h, "F", None, d, int(c.get("yeas") or 0), int(c.get("nays") or 0), []])
            continue
        yes = no = 0
        listed = []
        for g, n, names in r.get("groups") or []:
            if g in ("YEAS", "AYES"):
                yes = n
                continue
            code = {"NAYS": "N", "EXCUSED ABSENCE": "E", "NOT VOTING": "B", "ABSTAIN": "B", "PRESENT": "B"}.get(g)
            if g == "NAYS":
                no = n
            if not code:
                continue
            for name in names:
                mc = roll_code(session, h, name)
                sid = seat.get((h, mc)) if mc else None
                listed.append([sid or f"{h}?{text(name).split(',')[0]}", code])
        out.append([h, "F", None, d, yes, no, listed])
    out.sort(key=lambda v: v[3])
    return out


def sim_text(caps):
    t = re.sub(r"\b(?:SECTIONS?|CHAPTERS?|ARTICLES?|TITLES?)\s+[\d\-A-Z.,\s]*\d[\d\-A-Z.]*", " ", caps)
    t = re.sub(r"\bTO AMEND THE SOUTH CAROLINA CODE OF LAWS\b|\bBY AMENDING\b|\bBY ADDING\b|\bRELATING TO\b|\bSO AS TO\b|\bA BILL\b|\bAN ACT\b", " ", t)
    return text(t).lower()[:800]


# ---- earlier General Assemblies ------------------------------------------------------------------------------------

_KEYS = {}


def _subject(b):
    return re.sub(r"[^a-z0-9 ]", "", text(b.get("subject")).lower())


def _prime(b):
    sp = b.get("sponsors") or []
    return sp[0].get("code") or text(sp[0].get("name")) if sp else ""


def _keys(session):
    """A General Assembly's bills that didn't become law (and not budgets): subject -> [(number, prime sponsor code,
    title without its section numbers)]."""
    if session not in _KEYS:
        out = {}
        for k, b in (load(session, "bills", {}) or {}).items():
            if not kept(b) or b.get("act"):
                continue
            out.setdefault(_subject(b), []).append((k, _prime(b), sim_text(text(b.get("title")))))
        _KEYS[session] = out
    return _KEYS[session]


def earlier(session, p, b):
    """The same bill in the General Assembly before: the same subject line and prime sponsor; or the same subject and
    the same title apart from section numbers; or a subject only one bill has in each. Never budgets, regulation
    approvals or one-word subjects shared by many bills."""
    out = set()
    y = session - 2
    if y not in sessions():
        return out
    k = _subject(b)
    if len(k.split()) < 2 or re.search(r"\bappropriation|budget|regulation doc", k) or re.search(r"APPROVE REGULATIONS", text(b.get("title"))):
        return out
    old = _keys(y).get(k, [])
    if not old:
        return out
    same = [n for n, sp, _ in old if sp and sp == _prime(b)]
    st = sim_text(text(b.get("title")))
    alike = [n for n, _, t in old if t == st]
    if same:
        out.add((y, same[0]))
    elif alike:
        out.add((y, alike[0]))
    elif len(old) == 1 and len(_keys(session).get(k, [])) == 1 and len(k.split()) >= 3:
        out.add((y, old[0][0]))
    return out


def parties(session, recs):
    if session not in _PARTIES:
        load_session(session)
    return {k: v for k, v in _PARTIES.get(session, {}).items() if v in ("D", "R")}


if __name__ == "__main__":
    # Laws and vetoes by year, against the Acts lists.
    from collections import Counter
    for s in sessions():
        recs, index, _, _ = load_session(s)
        acts = {}
        for y in (s, s + 1):
            for a in load(s, f"acts_{y}", []) or []:
                acts[a["bill"]] = y
        by = Counter()
        for r in recs:
            p = r["nums"][0]
            if r["stage"] == 5:
                by[("law", (r["keyDates"][5] or "")[:4])] += 1
            if r["keyDates"][6]:
                by[("vetoed", r["keyDates"][6][:4])] += 1
                if r["stage"] == 6:
                    by[("veto stands", r["keyDates"][6][:4])] += 1
            if r["vers"][0].get("itemVeto"):
                by[("item vetoes", (r["keyDates"][5] or "")[:4])] += 1
        laws = {r["nums"][0] for r in recs if r["stage"] == 5}
        amend = {r["nums"][0] for r in recs if "const" in r["topics"] and r["stage"] == 3}
        print(s, dict(sorted(by.items())))
        print("  Acts list:", Counter(acts.values()), "| laws not in it:", sorted(laws - set(acts))[:10],
              "| Acts that aren't laws here:", sorted((set(acts) - laws) - amend)[:10], "| amendments with Acts:", sorted(set(acts) & amend))
        print("  stages:", Counter(r["stage"] for r in recs))
        # Seats two members both held to the end (a district the member list got wrong).
        lv, ends = last_votes(s), {}
        for (h, code), m in members(s).items():
            ends.setdefault((h, m["district"]), []).append((lv.get((h, code), ""), m["name"]))
        last = max(lv.values(), default="")
        shared = {k: v for k, v in ends.items() if sum(1 for d, _ in v if d and d >= last[:7]) > 1}
        print("  seats held by two members to the end:", shared or "none")
