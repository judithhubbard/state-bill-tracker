"""Idaho's bills (downloaded by states/id/fetch.py from legislature.idaho.gov's pages) in the shape build_data.py reads. A
page a year: the Legislature meets once a year, from early January to about April, and bills die when it adjourns (the
two-year Legislature's second year numbers its bills on from the first's: 2026's House bills start at H0501). House and
Senate bills, plus the joint resolutions (HJR, SJR), which in Idaho propose amendments to the state constitution;
concurrent resolutions, memorials and one house's resolutions are left out.

Each bill's page has its sponsor ("by STATE AFFAIRS COMMITTEE": nearly every bill is a committee's; the member who asked
for it is named only in the Statement of Purpose, a PDF not downloaded), a subject and one-line description, and the
history: a date (MM/DD, no year; blank for more steps the same day) and the action. The lines don't say which house
acted, so the bill is followed from house to house: it starts in its own house; "Received from the House ..." and
"Returned from the Senate ..." move it; "Title apvd - to Senate", "Signed by President; returned to House",
"... Transmitted to Senate" move it after the line. A roll call's size (70 representatives, 35 senators) confirms it.

The steps: "Introduced, read first time, referred to JRA for Printing" (a committee asked for the bill at a print hearing;
printing is a formality); "Reported Printed and Referred to State Affairs" (the standing committee: "REFERRED TO"); a
few go straight to the floor ("Reported Printed; Filed for Second Reading": the budget bills JFAC writes) or are filed
with the Chief Clerk and never sent anywhere (members' own bills); "Reported out of Committee with Do Pass
Recommendation" (approved); "... to 14th Order for amendment" (Senate) and "... Recommend place on General Orders"
(House): approved, with amendments to be made by the whole house; "Read second time"; "Read third time in full – PASSED
- 56-11-3" (ayes, nays, absent or excused), with AYES, NAYS and Absent lists by surname ("Crane(12)" where two share
one; a substitute first, the member they sit for in parentheses: "Coho(Lenney)"; the Speaker is "Mr. Speaker"); "FAILED"
ends the bill unless reconsidered ("Motion to reconsider - PASSED"); joint resolutions are "ADOPTED". A second house
that amends the bill sends it back ("Returned from the Senate Amended"); the first concurs ("House Concurred in Senate
Amendments") and passes it again as engrossed, or doesn't ("did not Concur": it dies). Passed both houses: enrolled
("to JRA for Enrolling", "referred to enrolling", "Title apvd - to enrol"), or the second house passed it unamended.
Then the presiding officers sign it; "Delivered to Governor at 3:04 p.m. on April 3, 2025"; "Reported Signed by
Governor on April 4, 2025"; "Session Law Chapter 296"; "Law without signature"; "Line item vetoed by Governor"
(appropriations: a law, part vetoed); "Returned from Governor vetoed on 03/29/25" and the override vote ("Senate vote to
override veto", "FAILED (less than two-thirds) - 20-14-1", "Veto SUSTAINED by Senate"). Joint resolutions go to the
Secretary of State (and the voters), never the governor.

The governor's lines carry their own date ("on April 4, 2025"), used for the step. Laws and vetoes are also read from the
year's legislation list (its Enacted Legislation table, chapter by chapter, and its vetoed bills), which decides them when
a history stops early. No plain-language summary is in the data: see load_session().
"""
import glob, html, json, os, re
from datetime import date, datetime
from zoneinfo import ZoneInfo

from states.id import profile as P

HOUSE = {"S": "Senate", "H": "House"}
OTHER = {"S": "H", "H": "S"}
_PARTIES, _CACHE = {}, {}
MONTHS = {m: i for i, m in enumerate(["January", "February", "March", "April", "May", "June", "July", "August",
                                      "September", "October", "November", "December"], 1)}


def folder(session):
    return os.path.join(P.DATA, str(session))


def sessions():
    out = []
    for f in sorted(os.listdir(P.DATA)) if os.path.isdir(P.DATA) else []:
        if re.fullmatch(r"\d{4}", f) and os.path.exists(os.path.join(P.DATA, f, "list.json")):
            out.append(int(f))
    return out


def text(fragment):
    """Plain text of an HTML fragment, spaces collapsed."""
    t = html.unescape(re.sub(r"<[^>]+>", " ", fragment or "")).replace("\xa0", " ")
    return re.sub(r"\s+", " ", t).strip()


def listing(session):
    key = (session, "list")
    if key not in _CACHE:
        try:
            _CACHE[key] = json.load(open(os.path.join(folder(session), "list.json"), encoding="utf-8"))
        except (OSError, ValueError):
            _CACHE[key] = {"bills": {}, "enacted": [], "vetoed": []}
    return _CACHE[key]


def number(key):
    """"H0003" -> "H3"; "HJR004" -> "HJR4"; "S1023" -> "S1023"."""
    m = re.fullmatch(r"([A-Z]+?)0*(\d+)", key)
    return f"{m.group(1)}{int(m.group(2))}" if m else key


def official(p):
    """"H3" -> "H0003", "HJR4" -> "HJR004": the Legislature's form, for links."""
    m = re.fullmatch(r"([A-Z]+)(\d+)", p)
    if not m:
        return p
    return f"{m.group(1)}{int(m.group(2)):04d}" if m.group(1) in ("H", "S") else f"{m.group(1)}{int(m.group(2)):03d}"


def read_page(session, key):
    """A bill's page: {"label", "sponsor", "desc", "rows": [(MM/DD or "", [part, ...])]}, each history row's parts being
    its lines (split at the page's line breaks), as text."""
    path = os.path.join(folder(session), "bills", f"{key}.html")
    try:
        page = open(path, encoding="utf-8").read()
    except OSError:
        return None
    tabs = re.findall(r'<table class="bill-table">(.*?)</table>', page, re.S)
    if len(tabs) < 2:
        return None
    head = [text(c) for c in re.findall(r"<td\b[^>]*>(.*?)</td>", tabs[0], re.S)]
    rows = []
    for t in tabs[2:]:
        for r in re.findall(r"<tr>(.*?)</tr>", t, re.S):
            c = re.findall(r"<td\b[^>]*>(.*?)</td>", r, re.S)
            if len(c) < 3:
                continue
            parts = [text(x) for x in re.split(r"<br\s*/?>", c[2])]
            rows.append((text(c[1]), [x for x in parts if x]))
    return {"label": head[0] if head else key, "sponsor": re.sub(r"^by\s+", "", head[-1]) if head else "",
            "desc": text(tabs[1]), "rows": rows, "path": path}


# ---- Members ----

def _committee_members(session):
    """The year's committee pages: [{house, name, district, party, id, email, phone, code, committee, role}]."""
    out = []
    for path in sorted(glob.glob(os.path.join(folder(session), "committees", "*.html"))):
        code = os.path.basename(path)[:-5]
        page = open(path, encoding="utf-8").read()
        title = re.search(r"<h6>\s*\d{4}\s+(.*?)</h6>|<h1[^>]*>(.*?)</h1>", page, re.S)
        i = page.find("<h2><strong>Republicans")
        if i < 0:
            continue
        cols = page[i:].split('<div class="wpb_column vc_column_container col-xs-mobile-fullwidth col-sm-6">')
        for j, col in enumerate(cols[1:3]):
            for m in re.finditer(r'<strong><a href="/legislators/membership/\d+/id(\d+)">(.*?)</a>(.*?)</strong>(.*?)</p>', col, re.S):
                who = text(m.group(2))
                h = "S" if who.startswith("Sen.") else "H"
                rest = m.group(4)
                d = re.search(r"district=(\d+)", rest)
                ph = re.search(r'href="tel:\+1(\d{10})"', rest)
                em = re.search(r"mailto:([^\"]+)", rest)
                role = text(m.group(3)).strip(" ,")
                out.append({"house": h, "name": plain_name(re.sub(r"^(?:Rep|Sen)\.\s*", "", who)), "id": m.group(1),
                            "district": int(d.group(1)) if d else None, "party": "R" if j == 0 else "D",
                            "phone": f"({ph.group(1)[:3]}) {ph.group(1)[3:6]}-{ph.group(1)[6:]}" if ph else None,
                            "email": em.group(1) if em else None, "code": code, "role": role})
    return out


def plain_name(n):
    """"James W. “Jim” Woodward" -> "James W. Woodward"."""
    return re.sub(r"\s+", " ", re.sub(r"\s*[“\"][^”\"]*[”\"]", "", n)).strip()


def committee_names(session):
    """Committee code -> its name ("HJUD" -> "Judiciary, Rules and Administration"), from the pages' headings."""
    out = {}
    for path in sorted(glob.glob(os.path.join(folder(session), "committees", "*.html"))):
        page = open(path, encoding="utf-8").read()
        m = re.search(r"<h6[^>]*>(.*?)</h6>", page, re.S)
        t = text(m.group(1)) if m else ""
        t = re.sub(r"^\d{4}\s+(?:House|Senate)?\s*", "", t)
        out[os.path.basename(path)[:-5]] = comm_name(t)
    return out


def comm_name(c):
    """"Judiciary, Rules & Administration" / "JUDICIARY, RULES AND ADMINISTRATION COMMITTEE" -> "Judiciary, Rules and
    Administration"."""
    c = re.sub(r"\s+Committee$", "", text(c), flags=re.I).replace("&", "and").strip(" ,:")
    c = re.sub(r"\s+", " ", c)
    if c.isupper():
        small = {"and", "of", "the", "for"}
        c = " ".join(w.lower() if w.lower() in small and i else w.capitalize() for i, w in enumerate(c.split()))
    return c


def current_members():
    try:
        return json.load(open(os.path.join(P.DATA, "members", "members.json"), encoding="utf-8")).get("members") or []
    except (OSError, ValueError):
        return []


def surname(name):
    """"Bruce D. Skaug" -> "Skaug"; "John Vander Woude" -> "Vander Woude"; "Lori Den Hartog" -> "Den Hartog"; "Jr."
    isn't a surname."""
    words = [w for w in re.sub(r",?\s+(?:Jr\.?|Sr\.?|II|III|IV)$", "", name.strip()).split()]
    if len(words) >= 3 and words[-2] in ("Vander", "Den", "Van", "De", "Del", "La", "St."):
        return " ".join(words[-2:])
    return words[-1] if words else ""


def roster(session):
    """The year's members, each once: {(house, id or name): {house, name, district, party, seat, email, phone, posts,
    committees: [(code, role)]}}. From the year's committee pages; the latest year adds the current member list (party,
    House seat A or B, phones, leadership posts). Seats: "S:12"; a district's two representatives "H:12a" (seat A) and
    "H:12b" (seat B), for past years from the current list where the member still holds the seat, else the seat left."""
    key = (session, "roster")
    if key in _CACHE:
        return _CACHE[key]
    people = {}
    for m in _committee_members(session):
        k = (m["house"], m["id"])
        p = people.setdefault(k, {"house": m["house"], "name": m["name"], "district": m["district"], "party": m["party"],
                                  "email": m["email"], "phone": m["phone"], "seat": "", "post": "", "home": None,
                                  "address": "", "committees": [], "id": m["id"]})
        p["committees"].append((m["code"], m["role"]))
    latest = session == max(sessions() or [session])
    cur = current_members()
    if latest:
        for c in cur:
            hit = next((p for p in people.values() if p["house"] == c["house"] and p["district"] == c["district"]
                        and surname(p["name"]).lower() == surname(c["name"]).lower()), None)
            if not hit:
                hit = people.setdefault((c["house"], c["name"]), {"house": c["house"], "name": plain_name(c["name"]), "district": c["district"],
                                                                 "party": c["party"], "email": c["email"], "phone": None,
                                                                 "seat": "", "post": "", "home": None, "address": "",
                                                                 "committees": [], "id": None})
            hit.update({"name": plain_name(c["name"]), "party": c["party"] or hit["party"], "email": c["email"] or hit["email"],
                        "seat": c.get("seat") or "", "post": c.get("post") or "", "home": c.get("home") or None,
                        "address": c.get("address") or "", "phone": c.get("statehouse") or hit["phone"]})
            hit["current"] = True
        # Members on a committee page who aren't on the current list (they left during the year) keep their committee
        # entry, for votes, but get no seat when someone else now holds it.
    seat_now = {(c["house"], c["district"], surname(c["name"]).lower()): c.get("seat") or "" for c in cur}
    by = {}
    for p in people.values():
        if p["house"] == "S":
            p["sid"] = f"S:{p['district']}" if p["district"] else None
        else:
            p["seat"] = p["seat"] or seat_now.get(("H", p["district"], surname(p["name"]).lower()), "")
            by.setdefault(p["district"], []).append(p)
    for d, ps in by.items():
        if not d:
            continue
        taken = {p["seat"] for p in ps if p["seat"]}
        for p in sorted(ps, key=lambda p: (not p["seat"], p["name"])):
            if not p["seat"]:
                free = [s for s in "AB" if s not in taken]
                if latest and not p.get("current") and len(ps) > 2:
                    p["sid"] = None  # left during the year; the seat is someone else's now
                    continue
                p["seat"] = free[0] if free else ""
                taken.add(p["seat"])
            p["sid"] = f"H:{d}{p['seat'].lower()}" if p["seat"] else None
    # Two members in one seat (a member replaced mid-year, both on committee pages): the current one keeps it.
    seen = {}
    for p in sorted(people.values(), key=lambda p: not p.get("current")):
        if p.get("sid"):
            if p["sid"] in seen and p["house"] == "H":
                p["sid"] = None
            elif p["sid"] in seen and latest and not p.get("current"):
                p["sid"] = None
            else:
                seen[p["sid"]] = p
    _CACHE[key] = people
    return people


def resolver(session):
    """A roll call's name ("Skaug", "Crane(12)", "Coho(Lenney)", "Mr. Speaker") in a house -> the member's seat id, or
    "H?Name" for a member not on that year's lists."""
    people = [p for p in roster(session).values()]
    speaker = P.LEADERS["H"][0]  # Mike Moyle, Speaker since December 2022
    held = {p["sid"] for p in people if p.get("sid")}
    later = []
    for c in current_members():
        if c["house"] == "S":
            later.append({**c, "sid": f"S:{c['district']}"})
        elif c.get("seat"):
            later.append({**c, "sid": f"H:{c['district']}{c['seat'].lower()}"})

    def norm(s):
        return re.sub(r"[^a-z]", "", s.lower().replace("’", "'"))

    def match(h, name, district):
        hits = [p for p in people if p["house"] == h and norm(surname(p["name"])) == norm(name)]
        if not hits:
            hits = [p for p in people if p["house"] == h and norm(p["name"]).endswith(norm(name))]
        if district:
            hits = [p for p in hits if p["district"] == district]
        live = [p for p in hits if p.get("sid")]
        if len(live) == 1:
            return live[0]["sid"]
        if not hits:
            # Not on the year's committee pages (the Speaker serves on none; some who left aren't listed): a current
            # member of that house with the name, whose seat no one on that year's lists holds.
            now = [c for c in later if c["house"] == h and norm(surname(c["name"])) == norm(name)
                   and (not district or c["district"] == district)]
            if len(now) == 1 and now[0]["sid"] not in held:
                return now[0]["sid"]
        return None

    def find(h, name):
        """A substitute's vote is written with both names: the House puts the member first ("Hill(Brown)": Brown sits
        for Hill), the Senate the substitute first ("Coho(Lenney)": Coho sits for Lenney). The vote counts for the
        member's seat; a name on that year's lists decides when the order doesn't."""
        name = name.strip()
        if re.match(r"Mr\.?\s*Speaker|Madam Speaker", name):
            name = surname(speaker)
        district = None
        groups = re.findall(r"\(([^()]*)\)", name)
        order = [name]
        if groups:
            base = name[:name.index("(")].strip()
            district = next((int(g) for g in groups if g.strip().isdigit()), None)  # "Crane(12)": two share the name
            other = [g.strip() for g in groups if g.strip() and not g.strip().isdigit()]
            order = ([base] + other if h == "H" else other + [base]) if other else [base]
        for n in order:
            sid = match(h, n, district)
            if sid:
                return sid
        return f"{h}?{order[0]}"
    return find


def names(s):
    """"Alfieri, Andrus, Vander Woude, Mr. Speaker" -> list; "None" -> []."""
    s = s.strip()
    if not s or s == "None":
        return []
    return [x.strip() for x in s.split(",") if x.strip() and x.strip() != "None"]


# ---- Wording ----

ABBREV = [(r"\bApprop\b", "Appropriation"), (r"\badd[’']l\b", "additional"), (r"\borig\b", "original"),
          (r"\bHwy\b", "Highway"), (r"\bhwy\b", "highway"), (r"\bdept\b", "department"), (r"\bDept\b", "Department"),
          (r"\bcmsn\b", "commission"), (r"\bcomm\b", "commission"), (r"\bcomp\b", "compensation"),
          (r"\bgov[’']?t\b", "government"), (r"\bfed gov\b", "federal government"), (r"\batty gen\b", "attorney general"), (r"\bgov\b", "government"),
          (r"\bGov\b", "Governor"),
          (r"\breqs?\b", "requirements"), (r"\bschls\b", "schools"), (r"\bedu\b", "education"), (r"\bbd\b", "board"),
          (r"\bhlth\b", "health"), (r"\bsrv(?:c)?s\b", "services"), (r"\bassoc\b", "association"), (r"\bdist\b", "district"),
          (r"\bprgm\b", "program"), (r"\bvoc rehab\b", "vocational rehabilitation"), (r"\bExec\b", "Executive"),
          (r"\bauth\b", "authority"), (r"\btrlr\b", "trailer"), (r"\blegis\b", "legislative"), (r"\borg\b", "organization"),
          (r"\bag\b", "agriculture"), (r"\bRec\b", "Recreation"), (r"\brec\b", "recreation"), (r"\bH&W\b", "Health and Welfare"),
          (r"\bagric\b", "agriculture"), (r"\buniv\b", "university"), (r"\binfo\b", "information"), (r"\bprog\b", "program"),
          (r"\bjuv\b", "juvenile"), (r"\bevac\b", "evacuation"), (r"\bEvac\b", "Evacuation"), (r"\badmin\b", "administration")]


def titled(short, desc):
    """The list's short title, with its abbreviations spelled out: "Approp, ITS, add’l" -> "Appropriation, ITS,
    additional"; else the description's subject."""
    t = short.strip()
    for a, b in ABBREV:
        t = re.sub(a, b, t)
    if not t:
        t = subject(desc).capitalize()
    return t[:1].upper() + t[1:]


def subject(desc):
    """"TAXATION – Adds to existing law ..." -> "TAXATION"."""
    m = re.match(r"(.+?) – ", desc)
    return m.group(1) if m else ""


def what(desc):
    """The one-line description without its subject: "Adds to existing law to establish ..."."""
    m = re.match(r".+? – (?=[A-Z][a-z])", desc)
    return desc[m.end():] if m else desc


def text_date(t, d, session):
    """A line's own date: "on April 4, 2025", "on 03/29/25", "– April 10, 2024"; else the row's."""
    m = re.search(r"\b(January|February|March|April|May|June|July|August|September|October|November|December) (\d{1,2}), (\d{4})", t)
    try:
        if m:
            return date(int(m.group(3)), MONTHS[m.group(1)], int(m.group(2))).isoformat()
        m = re.search(r"\bon (\d{1,2})/(\d{1,2})/(\d{2,4})\b", t)
        if m:
            y = int(m.group(3))
            return date(y + 2000 if y < 100 else y, int(m.group(1)), int(m.group(2))).isoformat()
    except ValueError:
        pass
    return d


TALLY = re.compile(r"\b(PASSED|FAILED|ADOPTED)(?: \(less than two-thirds\))? - (\d+)-(\d+)-(\d+)")
REFER = re.compile(r"(?:Reported Printed(?: and|;) [Rr]eferred to|referred to:|Read First Time, Referred to|"
                   r"^Referred to|Previously Held at Desk, Referred to|Take bill off General Orders; referred to|Recommitted to|"
                   r"Reported out of Committee and referred to:|Reported out without amendments; referred to:|"
                   r"U\.C\. to be returned to)\s*(.+?)(?: Committee)?$")


def load_session(session):
    """Read one year's bills and return (records, bill number -> record index, fetched time, delegation)."""
    lst = listing(session)
    enacted = {e["bill"]: e for e in lst.get("enacted") or []}
    vetoed = set(lst.get("vetoed") or [])
    find = resolver(session)
    parties = _PARTIES.setdefault(session, {})
    for p in roster(session).values():
        if p["party"] in ("R", "D"):
            parties[(p["house"], p["name"])] = p["party"]
    path = os.path.join(folder(session), "list.json")
    fetched = datetime.fromtimestamp(os.path.getmtime(path), ZoneInfo(P.TIMEZONE)).strftime("%Y-%m-%d %H:%M") if os.path.exists(path) else ""
    recs, index = [], {}
    kinds = {"H": 0, "S": 1, "HJR": 2, "SJR": 3}
    keys = [k for k in lst["bills"] if re.fullmatch(r"(HJR|SJR|H|S)\d+", k)]
    for key in sorted(keys, key=lambda k: (kinds[re.match(r"[A-Z]+", k).group(0)], int(re.sub(r"\D", "", k)))):
        pg = read_page(session, key)
        if not pg:
            continue
        p = number(key)
        rec = record(session, key, p, pg, lst["bills"][key], enacted.get(key), key in vetoed, find)
        index[p] = len(recs)
        recs.append(rec)
    # No "What it does": the one-line description (the summary here) only names what the bill touches; the sponsor's
    # Statement of Purpose, the plain account, is a PDF (not downloaded).
    return recs, index, fetched, {"SENATE": [], "ASSEMBLY": []}


def record(session, key, p, pg, listed, enacted, vetoed_listed, find):
    amendment = p.startswith(("HJR", "SJR"))
    origin = p[0]
    other = OTHER[origin]
    cur = origin
    steps = []  # (date, house or "G", wording, kind)
    passed, failed = set(), set()
    last_vote = {}
    second_amended = False
    concurred, repassed = set(), False
    enrolled = sent = law = vetoed = nosign = item = to_sos = False
    override, override_failed = set(), set()
    pending_override = None
    place, comm, first_ref, first_report, dopass = "desk", None, None, None, False
    refs = []
    chapter = None
    votes = []
    vote_ctx = None  # the roll call being read: [house, date, yeas, nays, listed]
    d = f"{session}-01-01"
    for mmdd, parts in pg["rows"]:
        m = re.match(r"(\d{2})/(\d{2})", mmdd)
        if m:
            d = f"{session}-{m.group(1)}-{m.group(2)}"  # the session's own year (it meets January to April)
        for t in parts:
            # Roll-call lists belong to the vote just read.
            lm = re.match(r"^(AYES|NAYS|Absent and excused|Absent|Excused from voting|Excused)\s*[–-]\s*(.*)$", t)
            if lm:
                if vote_ctx is not None:
                    code = {"AYES": None, "NAYS": "N", "Absent": "A"}.get(lm.group(1), "E")
                    for n in names(lm.group(2)):
                        if code:
                            vote_ctx[4].append([find(vote_ctx[0], n), code])
                continue
            fm = re.match(r"^Floor Sponsors? - (.*)$", t)
            if fm:
                who = fm.group(1).strip()
                if who and not re.match(r"No sponsor data", who):
                    steps.append((d, cur, f"Floor sponsor: {who.replace(' & ', ' and ')}", "floorsponsor"))
                continue
            # Before the line: the house that records it.
            mv = re.match(r"(?:Received|Returned) (?:from|From) (?:the )?(House|Senate)\b", t)
            if mv:
                cur = OTHER[mv.group(1)[0]]
            if re.match(r"Returned from Governor", t):
                cur = origin
            h, H = cur, HOUSE[cur]
            tm = TALLY.search(t)
            if re.match(r"(?:House|Senate) vote to override veto", t):
                pending_override = t[0]
                steps.append((d, pending_override, f"The {HOUSE[pending_override]} voted on overriding the veto", "overridevote"))
                continue
            if re.match(r"Motion to reconsider - (?:PASSED|motion carried)", t):
                if last_vote.get(h) == "pass":
                    passed.discard(h)
                    if h == other:
                        second_amended = False
                elif last_vote.get(h) == "fail":
                    failed.discard(h)
                last_vote.pop(h, None)
                steps.append((d, h, f"The {H} voted to reconsider", "reconsider"))
                if tm:
                    vote_ctx = None
                continue
            if tm:
                y, n, a = int(tm.group(2)), int(tm.group(3)), int(tm.group(4))
                total = y + n + a
                if total >= 50:
                    h = cur = "H"
                elif 0 < total <= 40:
                    h = cur = "S"
                H = HOUSE[h]
                ok = tm.group(1) in ("PASSED", "ADOPTED")
                vote_ctx = [h, d, y, n, []]
                if pending_override:
                    votes.append(vote_ctx)
                    if ok:
                        override.add(h)
                    else:
                        override_failed.add(h)
                    steps.append((d, h, f"The {H} {'voted to override' if ok else 'failed to override'} the veto, {y}-{n}"
                                  + ("" if ok else " (it needed two-thirds)"), "override"))
                    pending_override = None
                    continue
                votes.append(vote_ctx)
                last_vote[h] = "pass" if ok else "fail"
                if not ok:
                    failed.add(h)
                    # More ayes than nays and still failed: it needed two-thirds (a joint resolution, or a vote to
                    # suspend the rules), or a majority of the members.
                    steps.append((d, h, f"Failed to pass the {H}, {y}-{n}" + (" (it needed two-thirds)" if y > n else ""), "fail"))
                    continue
                failed.discard(h)
                first_time = h not in passed
                passed.add(h)
                if h == other and first_time:
                    # Amended in the second house: the first has to agree ("Returned from the Senate Amended" says so too).
                    second_amended = second_amended or bool(re.search(rf"as amended in (?:the )?{H}", t))
                    place = "desk"
                elif h == origin and first_time:
                    place, comm = "committee", None
                elif h in concurred:
                    repassed = True
                steps.append((d, h, f"PASSED {H.upper()}", "pass"))
                steps.append((d, h, f"The {H} vote: {y}-{n}" + (f", {a} absent" if a else ""), "tally"))
                continue
            vote_ctx = None if not re.match(r"Tie vote", t) else vote_ctx
            # The governor and the Secretary of State.
            if re.match(r"(?:Reported )?[Dd]elivered to Governor", t):  # not "... & ordered delivered to Governor"
                sent = True
                steps.append((text_date(t, d, session), "G", "DELIVERED TO GOVERNOR", "sent"))
                continue
            if re.search(r"Transmitted to Secretary of State|Delivered to Secretary of State", t):
                to_sos = True
                steps.append((text_date(t, d, session) if "Delivered" in t else d, "G",
                              "Delivered to the Secretary of State (for the voters)" if "Delivered" in t else
                              "Signed by the President of the Senate; sent to the Secretary of State", "sos"))
                continue
            if re.search(r"Signed by Governor", t, re.I):
                law = True
                steps.append((text_date(t, d, session), "G", "Signed by the governor", "signed"))
                cm = re.search(r"Session Law Chapter (\d+)", t)
                if cm:
                    chapter = int(cm.group(1))
                continue
            if re.match(r"Law without signature", t):
                law = nosign = True
                cm = re.search(r"Session Law Chapter (\d+)", t)
                if cm:
                    chapter = int(cm.group(1))
                steps.append((text_date(t, d, session), "G", "Became law without the governor's signature", "nosign"))
                continue
            if re.match(r"Line item vetoed by Governor", t):
                law = item = True
                steps.append((text_date(t, d, session), "G", "Signed by the governor, with line-item vetoes", "signed"))
                continue
            if re.match(r"Returned from Governor vetoed", t):
                vetoed = True
                steps.append((text_date(t, d, session), "G", "VETOED", "vetoed"))
                continue
            cm = re.match(r"Session Law Chapter (\d+)", t)
            if cm:
                chapter = int(cm.group(1))
                steps.append((steps[-1][0] if steps and steps[-1][1] == "G" else d, "G", f"SIGNED CHAPTER {chapter}" if not nosign and not item else f"Session Law chapter {chapter}", "chapter"))
                continue
            if re.match(r"Effective:", t) or (re.match(r"\d{2}/\d{2}/\d{2,4}\b|all other SECTIONS", t) and steps and steps[-1][3] == "effective"):
                if steps and steps[-1][3] == "effective":
                    steps[-1] = (steps[-1][0], "G", steps[-1][2].rstrip(";") + "; " + t.rstrip(";"), "effective")
                else:
                    steps.append((steps[-1][0] if steps and steps[-1][1] == "G" else d, "G", "Takes effect: " + t[10:].strip().rstrip(";"), "effective"))
                continue
            if re.search(r"Veto SUSTAINED", t, re.I):
                steps.append((d, h, f"The veto stands (the {H} didn't override it)", "sustained"))
                continue
            # Introduction and referrals.
            if re.match(r"Introduced.*for Printing", t):
                if not any(s[3] == "intro" for s in steps):
                    steps.append((d, h, "Introduced (a committee asked for it at a print hearing); sent to be printed", "intro"))
                place = "desk"
                continue
            if re.search(r"for concurrence recommendation", t):
                c = comm_name(re.sub(r"^Referred to\s*|\s*for concurrence recommendation.*$", "", t))
                steps.append((d, h, f"Sent to the {c} Committee for a recommendation on the other house's amendments", "concurref"))
                continue
            rm = REFER.search(t)
            if rm and not re.search(r"\b(?:Order|Committee of the Whole|JRA|JR for|enrol|engross)", rm.group(1)):
                c = comm_name(rm.group(1))
                comm, place = c, "committee"
                refs.append((h, c))
                if first_ref is None and h == origin:
                    first_ref = c
                if re.search(r"Recommitted|returned to|Take bill off General Orders", t):
                    steps.append((d, h, f"Sent back to the {c} Committee" if not re.search(r"General Orders", t) else f"Taken off General Orders and sent to the {c} Committee", "rereferred"))
                steps.append((d, h, f"REFERRED TO {c.upper()}", "ref"))
                continue
            if re.match(r"Reported Printed; Filed for Second Reading", t):
                place = "floor"
                steps.append((d, h, "Printed and placed on the calendar for second reading (no committee)", "first"))
                continue
            if re.match(r"(?:Reported Printed; )?Filed in (?:the )?[Oo]ffice of (?:the )?(?:Chief Clerk|Secretary of (?:the )?Senate)", t):
                steps.append((d, h, "Filed in the office of the " + ("Chief Clerk" if "Clerk" in t else "Secretary of the Senate")
                              + (" (never sent to a committee)" if not refs and not passed and h == origin else ""), "filed"))
                continue
            if re.match(r"Reported Printed and Held at Desk|Read First Time, Held at Desk|Reported out of Committee Misdirected", t):
                place, comm = "desk", None
                steps.append((d, h, "Held at the desk", "held"))
                continue
            # Committee reports.
            if re.match(r"Reported out without amendments; filed", t):
                place = "floor"
                steps.append((d, h, "Came out of the amending stage without amendments", "flooramend0"))
                continue
            if re.match(r"Reported out of [Cc]ommittee", t):
                if re.search(r"Do Pass", t, re.I):
                    kind, words = "pass", "recommended it pass"
                elif re.search(r"14th Order|General Orders", t):
                    kind, words = "pass", "recommended it pass with amendments"
                elif re.search(r"without Recommendation|w/o Recommendation", t, re.I):
                    kind, words = "none", "reported it without a recommendation"
                elif re.search(r"Recommend Concurrence", t):
                    steps.append((d, h, "The committee recommended agreeing to the other house's amendments", "report"))
                    continue
                elif re.search(r"re-referral", t):
                    steps.append((d, h, f"The {comm or 'the'} Committee sent it back to the desk to go to another committee", "report"))
                    place = "desk"
                    continue
                else:
                    kind, words = "none", "reported it"
                cname = comm or "the"
                if h == origin and first_report is None and refs and refs[0][0] == origin:
                    first_report = kind
                if kind == "pass":
                    dopass = True
                    steps.append((d, h, "REPORTED", "reported"))
                steps.append((d, h, f"The {cname} Committee {words}", "report"))
                place = "floor"
                continue
            if re.match(r"Reported out (?:without recommendation,? as amended|as amended)", t):
                steps.append((d, h, f"Amended on the floor (the {'Committee of the Whole' if h == 'H' else 'amending order'})", "flooramend"))
                place = "floor"
                continue
            if re.match(r"(?:Placed in|Referred to) the Committee of the Whole|Referred to 1[04]th Order for (?:amendment|possible concurrence)", t):
                place = "floor"
                steps.append((d, h, "Sent to the whole " + ("House (General Orders)" if h == "H" else "Senate (the amending order)") + " for amendment"
                              if "concurrence" not in t else "Placed on the order for concurring in the other house's amendments", "amendorder"))
                continue
            if re.match(r"Read second time", t, re.I):
                place = "floor"
                steps.append((d, h, "Read the second time; placed on the calendar for third reading", "second"))
                continue
            if re.match(r"Received from (?:the )?(?:House|Senate)(?: passed|, Filed| enrolled)", t):
                if "enrolled" not in t:
                    place, comm = "desk", None
                steps.append((d, h, f"Received from the {HOUSE[OTHER[h]]}" + (" (enrolled, for the presiding officer's signature)" if "enrolled" in t else ""), "received"))
                continue
            if re.match(r"Returned from (?:the )?(?:Senate|House),? [Aa]mended", t):
                second_amended = True
                place = "desk"
                steps.append((d, h, f"Returned from the {HOUSE[OTHER[h]]} with amendments", "returned"))
                continue
            if re.match(r"Returned (?:from|From) (?:the )?(?:Senate|House) Failed", t):
                steps.append((d, h, f"Returned from the {HOUSE[OTHER[h]]}, which voted it down", "returned"))
                continue
            if re.search(r"Concurred in (?:Senate|House) [Aa]mendments", t) and not re.search(r"not Concur", t, re.I):
                concurred.add(h)
                last_vote[h] = "concur"
                steps.append((d, h, f"The {H} agreed to the {HOUSE[OTHER[h]]}'s amendments", "concur"))
                continue
            if re.search(r"did not Concur", t, re.I):
                steps.append((d, h, f"The {H} refused to agree to the {HOUSE[OTHER[h]]}'s amendments", "noconcur"))
                continue
            if re.search(r"to JRA for Enrolling|referred to enrolling|Title apvd - to enrol|Reported [Ee]nrolled", t):
                if re.search(r"Title apvd - to enrol", t):
                    enrolled = True
                    continue
                enrolled = True
                if re.match(r"Returned (?:from|From)", t):
                    steps.append((d, h, f"Returned from the {HOUSE[OTHER[h]]}, passed; sent to be enrolled", "enroll"))
                else:
                    steps.append((d, h, "Enrolled; signed by the " + ("Speaker" if h == "H" else "President of the Senate"), "signature"))
            elif re.search(r"Signed by (?:the )?(?:Speaker|President)", t, re.I):
                who = "Speaker of the House" if re.search(r"Speaker", t) and not re.match(r"Returned Signed by the President", t) else "President of the Senate"
                if re.match(r"Reported signed by the Speaker", t):
                    who = "Speaker of the House"
                if re.match(r"Returned Signed by the President", t):
                    steps.append((d, h, "Back from the Senate with the President's signature; to be delivered to the governor", "signature"))
                elif re.match(r"Reported signed by the Speaker", t, re.I):
                    steps.append((d, h, "Back from the House with the Speaker's signature; to be delivered to the governor", "signature"))
                else:
                    steps.append((d, h, f"Signed by the {who}", "signature"))
            elif re.match(r"Title apvd - to (?:House|Senate)", t):
                pass
            elif re.match(r"Tie vote - President voted (AYE|NAY)", t):
                steps.append((d, "S", f"A tie: the Lieutenant Governor, presiding, voted {'yes' if 'AYE' in t else 'no'}", "tie"))
            elif re.match(r"(?:Ret’d|Order ret’d|Ret'd) to (?:House|Senate)$", t):
                pass
            elif re.match(r"U\.?C\.? to hold place|Retained on (?:calendar|General Orders)|U\.C\. to place at bottom|Motion to hold place", t):
                place = "floor"
                steps.append((d, h, "Held on the calendar", "laid"))
            elif re.match(r"Ret’d to 3rd Reading|File for 2nd Reading|Take bill off General Orders; filed", t):
                place = "floor"
                steps.append((d, h, t, "other"))
            elif re.match(r"(?:Amendments|Bills? as Amended|Reported [Ee]ngrossed|Read first time as amended|Filed for First Reading|Amendments reported printed|Amendments ordered printed)", t):
                steps.append((d, h, t, "engross"))
            elif re.match(r"(?:Read First Time, Filed for Second Reading|Bill Previously Held at Desk, File for 2nd Reading)", t):
                place = "floor"
                steps.append((d, h, "Read the first time; placed on the calendar (no committee)", "first"))
            else:
                steps.append((d, h, t, "other"))
            # After the line: where it went.
            mt = re.search(r"\b(?:to|To) (House|Senate)(?: for signature of Speaker)?$", t)
            if mt:
                cur = mt.group(1)[0]
        # A passage's "Title apvd - to Senate" sits among its parts: move after the row's parts are read.
        for t in parts:
            mt = re.match(r"(?:Title apvd - to|Ret’d to|Order ret’d to) (House|Senate)$", t)
            if mt:
                cur = mt.group(1)[0]
    steps.sort(key=lambda s: s[0])  # by day; the order within a day stays
    # The pages repeat a few lines ("Returned from the Senate Amended; Held at Desk" twice): keep one.
    steps = [x for i, x in enumerate(steps) if not (i and x[:3] == steps[i - 1][:3])]

    # Passed both houses: enrolled; or the second house passed it unamended; or the first agreed to its amendments and
    # passed it again.
    both = enrolled or (origin in passed and other in passed and not second_amended) or repassed or to_sos
    if enacted and not vetoed:
        law = True
    if vetoed_listed and not enacted:
        vetoed = True
    overridden = override >= {"H", "S"}
    if amendment:
        stage = 3 if both else 2 if passed else None
    elif law or overridden:
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
        stage = 1 if (place == "floor" or origin in failed) else 0
    if enacted and str(enacted.get("chapter") or "").isdigit():
        chapter = int(enacted["chapter"]) if stage == 5 else chapter
    ch_no = chapter if stage == 5 else None
    if stage == 5 and not any(s[3] in ("signed", "nosign") for s in steps):
        # A history that stops at "Delivered to Governor": the list's Enacted Legislation table has the law.
        signed = (enacted or {}).get("signed") or ""
        sm = re.fullmatch(r"(\d{2})/(\d{2})/(\d{2})", signed)
        when = f"20{sm.group(3)}-{sm.group(1)}-{sm.group(2)}" if sm else max(s[0] for s in steps)
        steps.append((when, "G", f"SIGNED CHAPTER {ch_no}" if ch_no else "Became law", "signed"))
        steps.sort(key=lambda s: s[0])
    if stage == 5 and overridden:
        steps.append((max(s[0] for s in steps), "G", "Became law over the governor's veto" + (f" (chapter {ch_no})" if ch_no else ""), "lawnote"))

    # Where it is now.
    comm_now = comm if place == "committee" and stage in (0, 2) else None
    title = titled(listed.get("title") or "", pg["desc"])
    if amendment:
        title = f"Constitutional amendment: {title[:1].lower() + title[1:]}"
    desc = what(pg["desc"])
    subj = subject(pg["desc"])
    topics = list(dict.fromkeys((["const"] if amendment else []) +
                                [P.COMMITTEE_TOPICS[c] for _, c in refs if c in P.COMMITTEE_TOPICS] +
                                [k for k in P.TOPIC_WORDS if P.TOPIC_WORDS[k].search(f"{subj} {title}")]))
    fate = "passed" if dopass or passed else "none"
    # Sponsors: the committee that introduced it ("House State Affairs Committee"), or the members named.
    sp = pg["sponsor"]
    if re.search(r"COMMITTEE$", sp):
        sponsor, cos = f"{HOUSE[origin]} {comm_name(sp)} Committee", []
    else:
        who = [w.strip() for w in re.split(r"\s+AND\s+|,\s*", sp) if w.strip()]
        full = []
        for w in who:
            sid = find(origin, w.title() if not w.startswith("MC") else "Mc" + w[2:].title())
            person = next((x for x in roster(session).values() if x.get("sid") == sid), None)
            full.append(person["name"] if person else w.title())
        sponsor, cos = (full[0] if full else "—"), full[1:]
    where = HOUSE[cur] if stage in (0, 1) else HOUSE[origin]
    if stage == 0:
        if not refs and not passed:
            dsc = "Filed with the Chief Clerk" if any(s[3] == "filed" for s in steps) else "Introduced"
        else:
            dsc = f"In {HOUSE[(refs[-1][0] if refs else origin)]} committee"
    elif stage == 1:
        dsc = f"Failed in the {HOUSE[origin]}" if origin in failed else f"On the {HOUSE[origin]} floor"
    else:
        dsc = {2: f"Passed the {HOUSE[origin] if origin in passed else HOUSE[other]}" + (f"; failed in the {HOUSE[other]}" if other in failed else ""),
               3: "Passed both houses", 4: "On the governor's desk", 5: "Became law", 6: "Vetoed"}[stage]

    def dates(test, mode="last"):
        ds = sorted({s[0] for s in steps if test(s) and s[0]})
        return {"first": ds[0], "last": ds[-1], "all": ";".join(ds)}[mode] if ds else ""

    action_dates = [s[0] for s in steps if s[0]]
    fvotes = sorted(([v[0], "F", None, v[1], v[2], v[3], v[4]] for v in votes), key=lambda v: v[3])
    return {
        "nums": [p], "base": [p], "prev": earlier(session, p, listed, pg),
        "title": title, "summary": desc, "act": "", "lawCode": "", "law": None, "laws": [],
        "comms": sorted({f"{h} · {c}" for h, c in refs}), "topics": topics, "places": [], "narrow": P.narrow_kind(title),
        "commFate": fate, "mainTopic": topics[0] if topics else "", "local": "local" in topics,
        "senDeleg": False, "asmDeleg": False,
        "budget": bool(re.match(r"APPROPRIATIONS", subj)) and not amendment,
        "passedS": "S" in passed, "passedA": "H" in passed, "program": None,
        "stage": stage, "passedIn": (HOUSE[origin] if origin in passed else HOUSE[other]) if stage == 2 else None,
        "chapter": ch_no,
        "veto": None, "memo": "", "vetoMemo": None,
        "simText": f"{title} {desc}",
        "comm": comm_now if stage == 0 else None,
        "first": min(action_dates, default=f"{session}-01-01"),
        "last": max(action_dates, default=f"{session}-01-01"),
        "cosp": len(cos),
        "keyDates": [
            dates(lambda s: s[3] == "reported", "first"),
            dates(lambda s: s[2] == "PASSED SENATE", "all"),
            dates(lambda s: s[2] == "PASSED HOUSE", "all"),
            "",
            dates(lambda s: s[3] == "sent") if stage >= 4 and not amendment else "",
            (dates(lambda s: s[3] in ("signed", "nosign", "lawnote"))) if stage == 5 else "",
            dates(lambda s: s[3] == "vetoed"),
        ],
        "votes": fvotes, "firstComms": [(origin, first_ref, first_report == "pass" or bool(passed))] if first_ref else [],
        "vers": [{"p": p, "sponsor": sponsor, "district": 0, "cosponsors": cos, "primes": 1 + len(cos) if cos else 1,
                  "cosp": len(cos), "statusDesc": dsc, "committee": comm_now,
                  "link": f"https://legislature.idaho.gov/sessioninfo/{session}/legislation/{key}/",
                  "actions": [[s[0], s[2]] for s in steps]}],
    }


# ---- Earlier years ----

_KEYS = {}


def _key(listed):
    return re.sub(r"\s+", " ", (listed.get("title") or "").lower()).strip()


def _keys(session):
    """A year's bills that didn't become law: short title -> [bill numbers]."""
    if session not in _KEYS:
        lst = listing(session)
        laws = {e["bill"] for e in lst.get("enacted") or []}
        out = {}
        for k, b in lst["bills"].items():
            if not re.fullmatch(r"(HJR|SJR|H|S)\d+", k) or k in laws:
                continue  # a law isn't tried again (yearly bills like the budgets share titles)
            out.setdefault(_key(b), []).append(number(k))
        _KEYS[session] = out
    return _KEYS[session]


def earlier(session, p, listed, pg):
    """The same bill in the two years before: the same short title, held by one bill in each year. Never
    appropriations (each year's are new bills), nor a bill that became law."""
    out = set()
    k = _key(listed)
    if len(k.split()) < 2 or re.match(r"approp\b|appropriation", k) or subject(pg["desc"]).startswith("APPROPRIATIONS"):
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
