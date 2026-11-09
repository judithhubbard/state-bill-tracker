"""Kentucky's bills (downloaded by states/ky/fetch.py from the Legislative Research Commission's bill record) in the shape
build_data.py reads. A page a year: the General Assembly meets once a year in a regular session (60 legislative days in
even years, January to mid-April; 30 in odd years, January to late March) and bills die when it ends. House and Senate
bills only (HB, SB); constitutional amendments are bills here ("AN ACT proposing to amend Section 77 of the Constitution
of Kentucky ..."). Joint resolutions (HJR, SJR) have the force of law and go to the governor, but they're mostly road
namings and directions to agencies, and the shared convention is bills plus amendments, so they're left out (the
status lists' totals below count bills only). Bills withdrawn before they were introduced ("WITHDRAWN", with only their
sponsors and no title) are left out too.

Each bill's page (data/ky/<year>/bills/HB1.html) has its title ("AN ACT relating to ..."), sponsors in order ("K. Moser";
in 2024 most link to the member's district page), the LRC's summaries of the original and, for laws, enacted version,
index headings, and the actions by date. The action lines don't always say which house acted: the bill is followed
("introduced in House", "received in Senate", committee referrals marked "(H)"/"(S)"), and a tally's size settles it
(the Senate has 38 members). The steps:
- "to Committee on Committees (H)": each house's Committee on Committees (its leaders) assigns every bill to a standing
  committee ("to Judiciary (H)"); many bills are never assigned. It's the gate (`STATE.gates`), shown as "Committees".
- "taken from Judiciary (H)", "1st reading", "returned to Judiciary (H)": readings while the bill stays in committee.
- "reported favorably, 1st reading, to Calendar [with Committee Substitute (1)]" (the committee approved it; Kentucky's
  committees report favorably or not at all), "2nd reading, to Rules", "posted for passage in the Regular Orders of the
  Day for ...", "3rd reading, passed 79-17 [with ...]" (the passage; in the second house "with" an amendment means the
  first house has to agree). "recommitted to X (H)" sends a reported bill back to a committee.
- Back in the first house: "House concurred in Senate Committee Substitute (1)" and "passed 90-5 with Committee
  Substitute (1)" (the bill passed again as amended), or "House refused to concur", "Senate refused to recede",
  "Conference Committee appointed", "Free Conference Committee report adopted in Senate" and "passed 36-1" in each house.
  A conference committee's report can be its failure to agree (then a free conference committee is appointed), so only
  the "passed" lines and enrollment count.
- "enrolled, signed by Speaker of the House / President of the Senate" (passed both houses), "delivered to Governor",
  "signed by Governor (Acts Ch. 4)", "became law without Governor's Signature (Acts Ch. 19)", "Vetoed", "23 line items
  vetoed", then, on the veto days, "veto overridden" and "passed 72-27" in each house and "delivered to Secretary of
  State (Acts Ch. 175)"; a veto after the session ends is final ("Vetoed and delivered with Veto Message to Secretary of
  State"). A law is a bill with an Acts chapter that isn't a constitutional amendment (they get chapters too, and go to
  the Secretary of State for the voters, never the governor).
Laws and vetoes agree with the LRC's status lists ("Signed By Governor", "Became Law Without Governor's Signature",
"Enacted Over Governor's Veto"; "Vetoed", "Veto Overridden", "Line Items Vetoed") bill for bill: `checks()` compares them.

Votes: the action lines give floor tallies only (members' votes are in PDFs, not downloaded), so each passage is a tally
with no names. "What it does" is the LRC's summary of the enacted version for a law, else of the bill as introduced.
"""
import html as H_, json, os, re
from collections import Counter, defaultdict
from datetime import datetime
from zoneinfo import ZoneInfo

from states.ky import profile as P

HOUSE = {"S": "Senate", "H": "House"}
OTHER = {"S": "H", "H": "S"}
SEATS = {"S": 38, "H": 100}
_PARTIES, _CACHE = {}, {}


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


def iso(d):
    """"02/19/26" -> "2026-02-19"."""
    m, dd, y = d.split("/")
    return f"20{y}-{m}-{dd}"


# ---- Reading a bill's page ----

def parse(session, key):
    """A bill page -> {key, title, sponsors [(short name, district page number or None)], original, enacted, headings,
    actions [(date, line)], chapter, last} or None when it's missing."""
    path = os.path.join(folder(session), "bills", f"{key}.html")
    try:
        s = open(path, encoding="utf-8").read()
    except OSError:
        return None
    head = s.split('id="actions"')[0]

    def field(name):
        m = re.search(rf"<th>{name}</th>\s*<td>(.*?)</td>", head, re.S)
        return m.group(1) if m else ""
    sponsors = []
    for sp in re.findall(r"<span>(.*?)</span>", field("Sponsors?"), re.S):
        link = re.search(r"DistrictNumber=(\d+)", sp)
        name = text(sp).rstrip(",").strip()
        if name:
            sponsors.append((name, int(link.group(1)) if link else None))
    headings = [text(h) for h in re.findall(r'<a href="\d+\.html">(.*?)</a>', field("Index Headings of Original Version"))]
    actions = []
    t = s[s.find('id="actions"'):] if 'id="actions"' in s else ""
    t = t.split('id="amendments"')[0]
    for d, body in re.findall(r"<th>(\d\d/\d\d/\d\d)</th>\s*<td>(.*?)</td>", t, re.S):
        for li in re.findall(r"<li>(.*?)</li>", body, re.S):
            line = text(li)
            if line:
                actions.append((iso(d), line))
    acts = re.search(r"Acts Chapter (\d+)", field("Bill Documents"))
    return {"key": key, "title": text(field("Title")), "sponsors": sponsors,
            "original": text(field("Summary of Original Version")), "enacted": text(field("Summary of Enacted Version")),
            "headings": headings, "actions": actions, "chapter": int(acts.group(1)) if acts else None,
            "last": text(field("Last Action")), "veto": bool(re.search(r"Governor's Veto Message", head)),
            "votes": bool(re.search(r"vote_history\.pdf", head))}


# ---- Members ----

def members():
    """The current members (data/ky/members/members.json): [{house, district, name, party, post, ...}]."""
    if "members" not in _CACHE:
        try:
            raw = json.load(open(os.path.join(P.DATA, "members", "members.json"), encoding="utf-8")).get("members") or []
        except (OSError, ValueError):
            raw = []
        _CACHE["members"] = [m for m in raw if m.get("house") in ("S", "H") and m.get("district") and m.get("name")]
    return _CACHE["members"]


def norm(s):
    return re.sub(r"[^a-z]", "", (s or "").lower())


def surname(name):
    """"G. Brown Jr." -> "Brown"; "George Brown Jr." -> "Brown"; "S. Funke Frommeyer" -> "Funke Frommeyer"."""
    n = re.sub(r",?\s+(?:Jr|Sr|II|III|IV)\.?$", "", name.strip())
    m = re.match(r"(?:[A-Z][A-Za-z]?\.|DJ)\s+(.+)$", n)
    return m.group(1) if m else n.split()[-1]


def resolve(h, short, page=None):
    """A sponsor as the record writes it ("K. Moser", "DJ Johnson", "G. Brown Jr."), in a house, with the district page
    number its link gives (2024: 1-100 House districts, 101-138 Senate districts 1-38) -> (name, district). A current
    member of that house with that initial and surname gives their full name and district; a link alone gives the
    district; otherwise the name as written and no district (a member who has left)."""
    last = norm(surname(short))
    first = short.strip()[:2] if short.startswith("DJ") else short.strip()[:1]
    hits = [m for m in members() if m["house"] == h and norm(re.sub(r",?\s+(?:Jr|Sr|II|III|IV)\.?$", "", m["name"])).endswith(last)
            and (m["name"].startswith(first) or not first)]
    district = None
    if page:
        district = page - 100 if page > 100 else page
        if (page > 100) != (h == "S"):
            district = None  # a link to the other house's district (none seen)
    if district:
        here = [m for m in hits if m["district"] == district]
        if here:
            return here[0]["name"], district
        return short, district
    if len(hits) == 1:
        return hits[0]["name"], hits[0]["district"]
    return short, None


# ---- Wording ----

def comm_name(c):
    """"Elections, Const. Amendments & Intergovernmental Affairs" -> "Elections, Constitutional Amendments and
    Intergovernmental Affairs"; "Committee on Committees" -> "Committees"; "Licensing, Occupations, & Administrative
    Regulations" -> "Licensing, Occupations and Administrative Regulations"."""
    c = re.sub(r"\s+", " ", (c or "").strip())
    c = re.sub(r"\s*\((?:H|S)\)$", "", c)
    if c == "Committee on Committees":
        return "Committees"
    c = c.replace("Const. ", "Constitutional ").replace(", &", " and").replace(" & ", " and ")
    return c.strip(" .")


def title_of(official, const):
    """"AN ACT relating to the torture of a dog or cat." -> "The torture of a dog or cat"; an amendment: "Constitutional
    amendment: sessions of the General Assembly"; "AN ACT making appropriations ..." -> "Making appropriations ..."."""
    t = re.sub(r"\s+", " ", official or "").strip().rstrip(".")
    t = re.sub(r",? and declaring an emergency$", "", t, flags=re.I)
    t = re.sub(r",? and making an appropriation therefor$", "", t, flags=re.I)
    m = re.search(r"\brelating to (.+)$", t, re.I)
    if const:
        body = m.group(1) if m else re.sub(r"^AN ACT\s+", "", t, flags=re.I)
        return f"Constitutional amendment: {body[:1].lower() + body[1:] if not body[:2].isupper() else body}"
    if re.match(r"AN ACT relating to ", t, re.I):
        t = t[len("AN ACT relating to "):]
    else:
        t = re.sub(r"^AN ACT\s+", "", t, flags=re.I)
    return t[:1].upper() + t[1:]


def is_const(official):
    return bool(re.search(r"\bproposing (?:to amend|an amendment to|to create a new section of|to repeal)\b.*Constitution of Kentucky",
                          official or "", re.I))


TALLY = re.compile(r"\b(?:passed|adopted)(?: with)?\s+(\d+)-(\d+)(?:-(\d+))?", re.I)
CHAPTER = re.compile(r"Acts Ch\.?\s*(\d+)", re.I)


def tally(line):
    m = TALLY.search(line)
    return (int(m.group(1)), int(m.group(2))) if m else None


def amended_with(line):
    """A passage "with Committee Substitute (1) and Floor Amendment (2)" -> True (the house changed the bill)."""
    return bool(re.search(r"\bwith\b.*\b(?:Substitute|Amendment)", line, re.I)) and not re.search(r"Conference Committee Report", line, re.I)


# ---- One bill ----

def record(session, b, parties):
    p = b["key"]
    origin = "H" if p.startswith("H") else "S"
    other = OTHER[origin]
    const = is_const(b["title"])
    steps = []  # (date, house or "G", wording, kind)
    passed, amended_by, last_pass = set(), set(), {}
    where, place, comm = origin, "desk", None
    reported = set()  # houses whose committee reported it
    refs, first_ref, first_report = [], None, False
    concurred = False
    enrolled = set()
    sent = law = vetoed = overridden = to_sos = items = False
    vetoed_on = None
    fvotes = []
    chapter = None
    for d, t in b["actions"]:
        m = CHAPTER.search(t)
        if m:
            chapter = int(m.group(1))
        tl = t.lower()
        mh = re.match(r"(introduced|received) in (House|Senate)\b", t, re.I)
        if mh:
            where = mh.group(2)[0].upper()
            if mh.group(1).lower() == "introduced":
                steps.append((d, where, f"Introduced in the {HOUSE[where]}", "intro"))
            elif vetoed and not law:
                steps.append((d, where, f"Received in the {HOUSE[where]} for a vote on the governor's veto", "other"))
            else:
                steps.append((d, where, f"Received in the {HOUSE[where]}", "received"))
            continue
        mc = re.match(r"(to|reassigned to|recommitted to) (.+?) \((H|S)\)$", t)
        if mc:
            h = mc.group(3)
            where = h
            c = comm_name(mc.group(2))
            if c == "Rules":
                # Rules decides which reported bills reach the floor, and takes up concurrences and vetoes; a bill sent
                # there before any committee reported it waits in Rules like a committee.
                if h in reported or h in passed or vetoed or len(enrolled) == 2 or (h == origin and other in passed):
                    place = "floor"
                    steps.append((d, h, "Sent to the Rules Committee", "rules"))
                    continue
            if c == "Enrollment":
                steps.append((d, h, "Sent to the Enrollment Committee", "other"))
                continue
            verb = mc.group(1)
            comm, place = c, "committee"
            refs.append((h, c))
            if c != "Committees" and first_ref is None and h == origin:
                first_ref = c
            if verb == "to":
                steps.append((d, h, f"REFERRED TO {c.upper()}", "ref"))
            elif verb == "reassigned to":
                steps.append((d, h, f"Sent to another committee: the {c} Committee", "rereferred"))
            else:
                steps.append((d, h, f"Sent back to committee: the {c} Committee", "recommitted"))
            continue
        mt = re.match(r"(taken from|returned to) (.+?)(?: \((H|S)\))?$", t)
        if mt:
            c = comm_name(mt.group(2))
            if mt.group(1) == "taken from" and c == "Rules":
                place = "floor"
                steps.append((d, where, "Taken from the Rules Committee", "other"))
            elif mt.group(1) == "returned to" and c not in ("Rules",):
                comm, place = c, "committee"
            # readings while in committee aren't news
            continue
        if re.match(r"reported favorably", t, re.I):
            h = where
            reported.add(h)
            if h == origin:
                first_report = True
            cname = comm if comm and comm != "Committees" else None
            place, comm = "floor", None
            steps.append((d, h, "REPORTED", "reported"))
            rest = re.sub(r"^reported favorably,?\s*", "", t, flags=re.I)
            what = " (with a committee substitute)" if re.search(r"Committee Substitute", rest) else \
                " (with amendments)" if re.search(r"Committee Amendment", rest) else ""
            to = " to the consent calendar" if re.search(r"Consent|as a consent bill", rest, re.I) else ""
            steps.append((d, h, f"The {cname + ' ' if cname else ''}Committee reported it favorably{what}{to}", "report"))
            continue
        if re.fullmatch(r"(?:1st|2nd) reading(?:, to (?:Rules|Calendar)(?: as a consent bill)?)?", t, re.I):
            if re.search(r"to (?:Rules|Calendar)", t):
                place = "floor"
                steps.append((d, where, "Read the second time and sent to the Rules Committee" if "Rules" in t else "Read and placed on the calendar", "second"))
            continue
        if re.match(r"(?:posted for passage|passed over and retained|placed in the Orders of the Day)", t, re.I):
            if not re.search(r"concurrence|receding|veto|Conference", t, re.I) and where not in passed:
                place = "floor"
            steps.append((d, where, t[:1].upper() + t[1:], "posted"))
            continue
        if re.fullmatch(r"3rd reading", t, re.I):
            steps.append((d, where, "Read the third time", "third"))
            continue
        if re.search(r"(?:vote on bill )?reconsidered$", t, re.I):
            h = where
            passed.discard(h)
            amended_by.discard(h)
            steps.append((d, h, f"The {HOUSE[h]} voted to reconsider its vote", "reconsider"))
            continue
        mv = TALLY.search(t)
        if mv and re.match(r"(?:3rd reading, |Bill )?(?:passed|adopted)\b", t, re.I):
            y, n = int(mv.group(1)), int(mv.group(2))
            h = where
            if y + n > SEATS["S"] and h == "S":
                h = "H"  # a tally bigger than the Senate's
            where = h
            prior = [s for s in steps if s[1] == h]
            lastk = prior[-1][3] if prior else ""
            if (vetoed or items) and not to_sos:
                steps.append((d, h, f"The {HOUSE[h]} voted to override the veto, {y}-{n}", "overridevote"))
                continue
            if lastk in ("concur", "ccr", "recede") or (h in passed and h == origin and other in passed):
                kind = "final"
            else:
                kind = "pass"
            fvotes.append([h, "F", None, d, y, n, []])
            if kind == "pass" and h not in passed:
                passed.add(h)
                last_pass[h] = d
                if h == other and amended_with(t):
                    amended_by.add(h)
                if h == origin:
                    comm = None
                    place = "desk"
                steps.append((d, h, f"PASSED {HOUSE[h].upper()}", "pass"))
                steps.append((d, h, f"The {HOUSE[h]} vote: {y}-{n}" + (" (as amended)" if amended_with(t) else ""), "tally"))
            else:
                passed.add(h)
                if lastk == "recede" and h == other:
                    amended_by.discard(h)
                steps.append((d, h, f"The {HOUSE[h]} passed it again, {y}-{n}"
                              + (" (as the conference committee proposed)" if lastk == "ccr" or "Conference" in t else
                                 " (with the other house's changes)" if lastk == "concur" else ""), "final"))
            continue
        mcon = re.match(r"(House|Senate) (concurred|refused to concur|receded|refused to recede)\b(.*)$", t, re.I)
        if mcon:
            h = mcon.group(1)[0].upper()
            what = mcon.group(2).lower()
            if what == "concurred":
                if h == origin:
                    concurred = True
                steps.append((d, h, f"The {HOUSE[h]} agreed to the {HOUSE[OTHER[h]]}'s changes", "concur"))
            elif what == "refused to concur":
                steps.append((d, h, f"The {HOUSE[h]} refused to agree to the {HOUSE[OTHER[h]]}'s changes", "noconcur"))
            elif what == "receded":
                steps.append((d, h, f"The {HOUSE[h]} dropped its changes (receded)", "recede"))
            else:
                steps.append((d, h, f"The {HOUSE[h]} refused to drop its changes", "norecede"))
            where = h
            continue
        if re.search(r"Conference Committee", t, re.I):
            free = "free conference committee" if re.search(r"Free Conference", t, re.I) else "conference committee"
            hs = [x[0].upper() for x in re.findall(r"\b(House|Senate)\b", t)]
            hh = hs[0] if len(hs) == 1 else where
            if re.search(r"appointed", t, re.I):
                steps.append((d, hh, f"A {free} was appointed", "conf"))
            elif re.search(r"filed", t, re.I):
                steps.append((d, hh, f"The {free} reported", "conf"))
            elif re.search(r"adopted", t, re.I):
                for x in hs or [where]:
                    steps.append((d, x, f"The {HOUSE[x]} adopted the {free}'s report", "ccr"))
                if len(hs) == 1:
                    where = hs[0]
            else:
                steps.append((d, hh, t, "conf"))
            continue
        me = re.match(r"enrolled, signed by (Speaker of the House|President of the Senate)", t, re.I)
        if me:
            hh = "H" if "Speaker" in me.group(1) else "S"
            enrolled.add(hh)
            steps.append((d, hh, f"Signed by the {'Speaker' if hh == 'H' else 'Senate President'} (enrolled)", "enrolled"))
            continue
        if re.match(r"delivered to Governor", t, re.I):
            if not const:
                sent = True
            steps.append((d, "G", "DELIVERED TO GOVERNOR", "sent"))
            continue
        if re.match(r"signed by Governor", t, re.I):
            if not const:
                law = True
            steps.append((d, "G", "Signed by the governor" + (f" (Acts ch. {m.group(1)})" if m else ""), "signed"))
            continue
        if re.search(r"without Governor's signature", t, re.I):
            if not const:
                law = True
            if re.match(r"filed without", t, re.I) and any(s[3] == "nosign" for s in steps):
                steps.append((d, "G", "Filed with the Secretary of State without the governor's signature", "other"))
            else:
                steps.append((d, "G", "Became law without the governor's signature" + (f" (Acts ch. {m.group(1)})" if m else ""), "nosign"))
            continue
        if re.search(r"line items? vetoed|line vetoes", t, re.I) and not re.search(r"overridden|sustained|invalid", t, re.I):
            items = True
            n = re.match(r"(\d+) line", t)
            steps.append((d, "G", f"The governor vetoed {n.group(1) + ' ' if n else ''}items in it (a line-item veto)", "itemveto"))
            continue
        if re.match(r"Vetoed\b", t, re.I):
            vetoed, vetoed_on = True, d
            final = "Secretary of State" in t
            steps.append((d, "G", "VETOED" + (" (after the session: the veto stands)" if final else ""), "vetoed"))
            continue
        if re.search(r"overridden|sustained|ruled line item vetoes invalid", t, re.I):
            if re.search(r"overridden", t, re.I) and not re.search(r"partially|in-part", t, re.I) and vetoed and not items:
                overridden = True
            steps.append((d, where, f"{HOUSE[where]}: {t}", "override"))
            continue
        if re.match(r"(?:Veto not acted upon|Governor delivered bill and (?:veto )?message)", t, re.I):
            steps.append((d, "G", "The veto stands: the bill and the veto message went to the Secretary of State", "vetofinal"))
            continue
        if re.match(r"delivered to Secretary of State", t, re.I):
            to_sos = True
            if const:
                steps.append((d, "G", "Sent to the Secretary of State, for the voters at the next general election", "sos"))
            elif vetoed and not items and not m:
                # A veto after the session (SB 70 of 2026): the bill goes to the Secretary of State without a chapter.
                steps.append((d, "G", "The veto stands: the bill went to the Secretary of State", "vetofinal"))
            elif vetoed and not items:
                law = True
                steps.append((d, "G", "Became law over the governor's veto" + (f" (Acts ch. {m.group(1)})" if m else ""), "overridelaw"))
            else:
                if m or chapter:
                    law = law or bool(m)
                steps.append((d, "G", "Delivered to the Secretary of State" + (f" (Acts ch. {m.group(1)})" if m else ""), "sos"))
            continue
        # Amendments filed, withdrawn, defeated, ruled out of order: as written.
        steps.append((d, where, t[:1].upper() + t[1:], "other"))

    chapter = chapter or b.get("chapter")
    if chapter and not const and not (vetoed and not overridden and not items and not law):
        law = True
    # Passed both houses: both presiding officers signed it (enrolled); the second house passed it unamended; or the
    # first agreed to its changes (and passed it again); or it went on to the governor.
    both = (len(enrolled) == 2 or sent or law or vetoed or (const and to_sos)
            or (origin in passed and other in passed and (other not in amended_by or concurred
                                                          or any(s[3] == "final" and s[1] == origin for s in steps))))
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
        stage = 1 if place == "floor" else 0

    official = re.sub(r"\s+", " ", b["title"]).strip()
    title = title_of(official, const)
    topics = (["const"] if const else [])
    for h_, c in refs:
        if c in P.COMMITTEE_TOPICS and P.COMMITTEE_TOPICS[c] not in topics:
            topics.append(P.COMMITTEE_TOPICS[c])
    for hd in b["headings"][:6]:
        for tp in P.HEADING_TOPICS.get(hd.lower(), []):
            if tp not in topics:
                topics.append(tp)
    if not topics:
        topics = [k for k, rx in P.TOPIC_WORDS.items() if rx.search(f"{title} {b['original'][:300]}")]
    topics = list(dict.fromkeys(t for t in topics if t != "const" or const))

    # Sponsors in order: the first is the sponsor.
    names = []
    for short, page in b["sponsors"]:
        name, district = resolve(origin, short, page)
        names.append((name, district))
    sponsor, district = names[0] if names else ("—", None)
    cos = [n for n, _ in names[1:] if n != sponsor]
    for n, dd in names:
        m = next((x for x in members() if x["house"] == origin and x["name"] == n), None)
        if m and m.get("party") in ("R", "D"):
            parties[(origin, n)] = m["party"]

    cur = where
    if stage == 0:
        dsc = f"In {HOUSE[cur]} committee" if place == "committee" else "Introduced"
    elif stage == 1:
        dsc = f"On the {HOUSE[cur]} floor"
    else:
        dsc = {2: f"Passed the {HOUSE[origin] if origin in passed else HOUSE[other]}", 3: "Passed both houses",
               4: "On the governor's desk", 5: "Became law", 6: "Vetoed"}[stage]
    comm_now = comm if place == "committee" and stage in (0, 2) else None

    def dates(test, mode="last"):
        ds = sorted({s[0] for s in steps if test(s) and s[0]})
        return {"first": ds[0], "last": ds[-1], "all": ";".join(ds)}[mode] if ds else ""

    action_dates = [s[0] for s in steps if s[0]]
    what = None
    if stage == 5 and b["enacted"]:
        what = {"statement": b["enacted"], "label": "From the Legislative Research Commission's summary of the enacted version."}
    elif b["original"]:
        what = {"statement": b["original"], "label": "From the Legislative Research Commission's summary of the bill as introduced."}
    first_comm_fate = first_report or bool(passed)
    rec = {
        "nums": [p], "base": [p], "prev": earlier(session, b),
        "title": title, "summary": official, "act": "", "lawCode": "", "law": None, "laws": [],
        # (Not the Committee on Committees: it only routes bills, and counting it made every bill look sent to two.)
        "comms": sorted({f"{h_} · {c}" for h_, c in refs if c != "Committees"}), "topics": topics, "places": [],
        "narrow": P.narrow_kind(title),
        "commFate": "passed" if reported or passed else "none", "mainTopic": topics[0] if topics else "",
        "local": "local" in topics, "senDeleg": False, "asmDeleg": False,
        "budget": bool(re.search(r"\bappropriations?\b", official, re.I)) and not const,
        "passedS": "S" in passed, "passedA": "H" in passed, "program": None,
        "stage": stage, "passedIn": (HOUSE[origin] if origin in passed else HOUSE[other]) if stage == 2 else None,
        "chapter": chapter if stage == 5 else None,
        "veto": None, "memo": "", "vetoMemo": None,
        "simText": f"{title} {official} {b['original'][:600]}",
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
            dates(lambda s: s[3] in ("signed", "nosign", "overridelaw", "sos")) if stage == 5 else "",
            dates(lambda s: s[3] == "vetoed"),
        ],
        "votes": fvotes, "firstComms": [(origin, first_ref, first_comm_fate)] if first_ref else [],
        "vers": [{"p": p, "sponsor": sponsor, "district": district or 0, "cosponsors": cos,
                  "primes": 1, "cosp": len(cos), "statusDesc": dsc, "committee": comm_now,
                  "actions": [[s[0], s[2]] for s in steps]}],
    }
    if stage == 5 and not rec["keyDates"][5]:
        rec["keyDates"][5] = rec["last"]
    return rec, what


def load_session(session):
    """Read one year's bills and return (records, bill number -> record index, fetched time, delegation)."""
    lst = listing(session)
    parties = _PARTIES.setdefault(session, {})
    stamp = lst.get("stamp") or ""
    recs, index, whats = [], {}, {}
    keys = [k for k in lst.get("bills") or [] if re.fullmatch(r"(HB|SB)\d+", k)]
    for k in sorted(keys, key=lambda k: (k[0] != "H", int(re.sub(r"\D", "", k)))):
        b = parse(session, k)
        if not b or not b["title"] or (not b["actions"] and re.search(r"WITHDRAWN", b["last"])):
            continue  # withdrawn before it was introduced: no title, no history
        rec, what = record(session, b, parties)
        index[k] = len(recs)
        recs.append(rec)
        if what:
            whats[k] = what
    try:
        json.dump(whats, open(os.path.join(P.DATA, f"texts_{session}.json"), "w"), ensure_ascii=False)
    except OSError:
        pass
    # When the download last saved anything for this year (the bill record's own "Last updated" stamp, `stamp`, stays
    # the same for months between sessions). A run that finds the record unchanged writes nothing.
    paths = [os.path.join(folder(session), n) for n in ("state.json", "list.json")]
    times = [os.path.getmtime(x) for x in paths if os.path.exists(x)]
    fetched = datetime.fromtimestamp(max(times), ZoneInfo(P.TIMEZONE)).strftime("%Y-%m-%d %H:%M") if times else stamp
    return recs, index, fetched, {"SENATE": [], "ASSEMBLY": []}


# ---- Earlier years ----

_KEYS = {}


def _keys(session):
    """A year's bills that didn't become law: (title key -> [bills], summary key -> [bills])."""
    if session not in _KEYS:
        by_title, by_summary = defaultdict(list), defaultdict(list)
        for k in listing(session).get("bills") or []:
            if not re.fullmatch(r"(HB|SB)\d+", k):
                continue
            b = parse(session, k)
            if not b or not b["title"] or b["chapter"] or any(CHAPTER.search(t) for _, t in b["actions"]):
                continue  # a law isn't tried again (yearly bills like the budgets share titles)
            tk, sk = _title_key(b), _summary_key(b)
            if tk:
                by_title[tk].append(k)
            if sk:
                by_summary[sk].append(k)
        _KEYS[session] = (by_title, by_summary)
    return _KEYS[session]


def _title_key(b):
    """The title and the sponsor's surname, for titles specific enough (four words or more after "relating to")."""
    t = re.sub(r"[^a-z0-9 ]", "", re.sub(r"\s+", " ", b["title"].lower()))
    words = re.sub(r"^an act relating to ", "", t).split()
    if len(words) < 4 or re.search(r"\bappropriation", t) or not b["sponsors"]:
        return ""
    return t + "|" + norm(surname(b["sponsors"][0][0]))


def _summary_key(b):
    s = re.sub(r"[^a-z0-9 ]", "", re.sub(r"\s+", " ", (b["original"] or "").lower())).strip()
    return s if len(s.split()) >= 15 else ""


def earlier(session, b):
    """The same bill in the two years before: the same title and prime sponsor, or the same LRC summary word for word,
    held by one bill in each year. Never appropriations, nor a bill that became law."""
    out = set()
    tk, sk = _title_key(b), _summary_key(b)
    for y in (session - 1, session - 2):
        if y not in sessions():
            continue
        by_title, by_summary = _keys(y)
        mine_t, mine_s = _keys(session)
        for key, old, mine in ((tk, by_title, mine_t), (sk, by_summary, mine_s)):
            if key and len(old.get(key, [])) == 1 and len(mine.get(key, [])) <= 1:
                out.add((y, old[key][0]))
                break
    return out


def parties(session, recs):
    if session not in _PARTIES:
        load_session(session)
    return {k: v for k, v in _PARTIES.get(session, {}).items() if v in ("D", "R")}


def agendas(session):
    return {}


# ---- Checks against the LRC's status lists ----

def checks(session):
    """Compare laws and vetoes with the LRC's status lists, bill for bill (bills only)."""
    recs = load_session(session)[0]
    lst = listing(session)
    bills = lambda ks: {k for k in ks if re.fullmatch(r"(HB|SB)\d+", k)}
    laws = set().union(*[bills(v) for v in (lst.get("law_routes") or {}).values()]) if lst.get("law_routes") else set()
    vr = lst.get("veto_routes") or {}
    vetoed = bills(vr.get("Vetoed", [])) - bills(vr.get("Veto Overridden", []))
    mine_law = {r["nums"][0] for r in recs if r["stage"] == 5}
    mine_veto = {r["nums"][0] for r in recs if r["stage"] == 6}
    const = {r["nums"][0] for r in recs if "const" in r["topics"] and r["stage"] == 3}
    return {"laws": len(mine_law), "official laws": len(laws), "laws not on the list": sorted(mine_law - laws),
            "listed laws not here": sorted(laws - mine_law), "vetoes": len(mine_veto), "official vetoes": len(vetoed),
            "vetoes not on the list": sorted(mine_veto - vetoed), "listed vetoes not here": sorted(vetoed - mine_veto),
            "overridden": len(bills(vr.get("Veto Overridden", []))), "line items": sorted(bills(vr.get("Line Items Vetoed", []))),
            "amendments to the voters": sorted(const), "routes": {k: len(bills(v)) for k, v in (lst.get("law_routes") or {}).items()}}


if __name__ == "__main__":
    for s in sessions():
        print(s, json.dumps(checks(s)))
