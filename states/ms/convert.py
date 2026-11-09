"""Mississippi's bills (downloaded by states/ms/fetch.py from the Legislature's bill status system,
billstatus.ls.state.ms.us) in the shape build_data.py reads. A page a year: the Legislature meets once a year, from the
Tuesday after the first Monday of January (90 days, 125 in the first year of a four-year term: 2024, 2028), and bills die
when it adjourns. House and Senate bills, plus the concurrent resolutions that propose constitutional amendments
("Constitution; amend Section 26 ..."); other resolutions are left out, and so are extraordinary sessions.

Each bill's history file (data/ms/<year>/history/HB0001.xml, ISO-8859-1) has the short title ("Third Chancery Court
District; revise number of chancellors."), the long title (the act's official title, in capitals), the principal and
co-authors (by their author pages: "Horan"), the committees, the chapter number, the vote it needs (Majority,
Three/Fifths, Two/Thirds) and the numbered actions, each "MM/DD (H) Passed" (month and day, no year; the house in
parentheses, none for the governor's steps). The steps:
- "Referred To Judiciary B" (a double referral: "Referred To Judiciary, Division A;Appropriations", the first committee
  first); "DR - TSDP: JA To AP" (the first committee approved it, "title sufficient, do pass", and it goes on to the
  second, by code); "Title Suff Do Pass" / "... As Amended" / "... Comm Sub" (approved, onto the calendar).
- Deadlines end most bills: "Died In Committee" (not reported by the committee deadline), "Died On Calendar" (not taken
  up by the floor deadline), "Died In Conference". A concurrent resolution can suspend a bill from the deadlines
  ("Suspend from Deadlines by HC  65").
- "Passed" / "Passed As Amended" (the house's passage), "Failed". "Motion to Reconsider Entered" holds the bill in the
  house until the motion is decided: "Motion to Reconsider Tabled" (the vote stands) or "Reconsidered" (the vote is
  undone and taken again).
- "Returned For Concurrence" (the second house amended it), "Concurred in Amend From Senate" (passed both houses),
  "Decline to Concur/Invite Conf", conferees, "Conference Report Adopted" (in both houses: passed both; a report adopted
  by one house only isn't), "Recommitted For Further Conf" (start over), "Died In Conference".
- "Returned For Enrolling" (the second house passed it as the first did: passed both houses), "Enrolled Bill Signed" by
  each house's presiding officer, after which it goes to the governor (the history doesn't show the delivery).
- "Approved by Governor", "Law W/out Governor's Signature", "Vetoed", "Partially Vetoed By Governor" (an appropriation
  bill with items vetoed: a law), "Veto Referred To ...", "Veto Overridden" / "Veto Sustained" in each house (an
  override takes both houses). The chapter number (CHAPNUM) is the law's number in the session laws.
Concurrent resolutions proposing amendments pass each house by two-thirds and go to the voters, never the governor.

Members' floor votes are PDFs (not downloaded) and the history lines carry no tallies, so there are no votes here.
There are no plain-language summaries: the long title, in sentence case, is the summary; no "What it does".
"""
import functools, glob, json, os, re
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from fetch_contacts import name_key
from states.ms import profile as P

HOUSE = {"S": "Senate", "H": "House"}
OTHER = {"S": "H", "H": "S"}
PRESIDING = {"H": "the Speaker", "S": "the Lieutenant Governor (the Senate's presiding officer)"}
_PARTIES = {}


def folder(session):
    return os.path.join(P.DATA, str(session))


def text(x):
    return re.sub(r"\s+", " ", (x or "").replace("\xa0", " ")).strip()


@functools.lru_cache(maxsize=None)
def sessions():
    out = []
    for f in glob.glob(os.path.join(P.DATA, "[0-9]" * 4)):
        if os.path.exists(os.path.join(f, "allmsrs.xml")) and len(glob.glob(os.path.join(f, "history", "*.xml"))) > 100:
            out.append(int(os.path.basename(f)))
    return tuple(sorted(out))


def xml(path):
    try:
        raw = open(path, "rb").read()
    except OSError:
        return None
    raw = re.sub(rb"<!DOCTYPE[^>]*>", b"", raw)
    try:
        return ET.fromstring(raw)
    except ET.ParseError:
        # A stray "&" in a title: escape it and try again.
        try:
            return ET.fromstring(re.sub(rb"&(?![a-zA-Z]+;|#\d+;)", b"&amp;", raw))
        except ET.ParseError:
            return None


# ---- Committees and members ----

# Committee names as the files abbreviate them.
COMMITTEE_NAMES = {"Environment Prot, Cons and Water Res": "Environment Protection, Conservation and Water Resources",
                   "Local and Private": "Local and Private Legislation"}


def comm_name(c):
    c = text(c).replace("&", "and")
    return COMMITTEE_NAMES.get(c, c)


@functools.lru_cache(maxsize=None)
def committee_codes(session, house):
    """A house's committee codes that year: "JA" -> "Judiciary, Division A" (from h_cmte.xml / s_cmte.xml)."""
    out = {}
    root = xml(os.path.join(folder(session), f"{house.lower()}_cmte.xml"))
    if root is None:
        return out
    for row in root.iter("CMTE"):
        for i in range(1, 4):
            n, l = row.findtext(f"C{i}_NAME"), row.findtext(f"C{i}_LINK")
            if n and l:
                out[os.path.basename(l)[:-4].upper()] = comm_name(n)
    return out


def slug(link):
    """"../../House_authors/Creekmore_IV.xml" -> "creekmore_iv"."""
    return os.path.basename(link or "")[:-4].lower() if (link or "").lower().endswith(".xml") else ""


@functools.lru_cache(maxsize=None)
def authors(session, house):
    """That year's members as the author lists name them: slug -> full name ("horan" -> "Kevin Horan")."""
    out = {}
    root = xml(os.path.join(folder(session), f"{house.lower()}_auth.xml"))
    if root is None:
        return out
    for row in root.iter("MEMBER"):
        for i in range(1, 7):
            n, l = row.findtext(f"M{i}_NAME"), row.findtext(f"M{i}_LINK")
            if n and l and slug(l):
                out[slug(l)] = text(n)
    return out


def phone(x):
    d = re.sub(r"\D", "", x or "")
    return f"({d[:3]}) {d[3:6]}-{d[6:10]}" if len(d) == 10 else None


# Districts the member files get wrong: Sen. Chris Johnson's file says District 44, which is Sen. John Polk's; his counties
# (Forrest, Lamar, Perry: Perry County lies wholly in District 45 in the Census Bureau's district files) and the vacant
# 45th seat say 45 (checked 2026-11-08). contacts.py reports any other seat claimed twice.
DISTRICT_FIX = {("S", "johnson"): 45}


@functools.lru_cache(maxsize=None)
def current_members():
    """The current members (data/ms/members/house|senate/<slug>.xml): (house, slug) -> {name, district, party, email,
    phones, room, counties, committees: [(name, officer)]}."""
    out = {}
    for h, sub, domain in (("H", "house", "@house.ms.gov"), ("S", "senate", "@senate.ms.gov")):
        for path in sorted(glob.glob(os.path.join(P.DATA, "members", sub, "*.xml"))):
            m = xml(path)
            if m is None or not text(m.findtext("DISTRICT")).isdigit():
                continue
            # The member files give the user name only ("khoran"); the Legislature's own stylesheets for these pages
            # (members/dtds_xslts/house.xslt and senate.xslt) add "@house.ms.gov" or "@senate.ms.gov" (checked
            # 2026-11-08). A few give a whole address.
            em = text(m.findtext("EMAIL/EMAIL_ADDRESS"))
            email = em if "@" in em else (em + domain if em else None)
            phones = []
            other = {"C": "Cell", "F": "Fax"}.get(text(m.findtext("OTH_TYPE")), "Other")
            for label, tag in (("Capitol", "CAP_PHONE"), ("Business", "B_PHONE"), ("Home", "H_PHONE"), (other, "OTH_PHONE")):
                ph = phone(m.findtext(tag))
                if ph and label != "Fax" and ph not in [x[1] for x in phones]:
                    phones.append([label, ph])
            out[(h, os.path.basename(path)[:-4])] = {
                "house": h, "name": re.sub(r"\.(?=[A-Z][a-z])", ". ", text(m.findtext("DISP_NAME"))), "short": text(m.findtext("U_MEM_NAM")),
                "district": DISTRICT_FIX.get((h, os.path.basename(path)[:-4]), int(text(m.findtext("DISTRICT")))), "party": text(m.findtext("PARTY"))[:1],
                "email": email, "phones": phones, "room": text(m.findtext("CAP_ROOM")),
                "counties": [text(c.text) for c in m.iter("COUNTY") if text(c.text)],
                "committees": [(comm_name(c.findtext("CMTE_NAME")), text(c.findtext("OFFICER")))
                               for c in m.iter("CMTE_INFO") if text(c.findtext("CMTE_NAME"))],
            }
    return out


# ---- Bills ----

def is_amendment(kind, title):
    """A concurrent resolution proposing an amendment to the Mississippi Constitution: "Constitution; amend Section 26 to
    ...", "Constitution; create new Section 7-A ..."; not the joint rules, memorials or deadline suspensions."""
    return kind == "C" and bool(re.match(r"(?:Mississippi )?Constitution(?: of 1890)?\s*;", title, re.I))


@functools.lru_cache(maxsize=None)
def listed(session):
    """The year's measures from allmsrs.xml: ["HB0001", ...] (bills and concurrent resolutions)."""
    root = xml(os.path.join(folder(session), "allmsrs.xml"))
    out = []
    for g in (root.iter("MSRGROUP") if root is not None else ()):
        m = re.fullmatch(r"([HS])([BC])\s*(\d+)", text(g.findtext("MEASURE")).replace(" ", ""))
        if m:
            out.append(f"{m.group(1)}{m.group(2)}{int(m.group(3)):04d}")
    return out


def history(session, key):
    root = xml(os.path.join(folder(session), "history", f"{key}.xml"))
    if root is None:
        return None
    acts = []
    for a in root.iter("ACTION"):
        d = text(a.findtext("ACT_DESC"))
        n = text(a.findtext("ACT_NUMBER"))
        if d:
            acts.append((int(n) if n.isdigit() else len(acts) + 1, d, bool(text(a.findtext("ACT_VOTE")))))
    auth = root.find("AUTHORS")
    princ = [(text(x.findtext("P_NAME")), slug(x.findtext("P_LINK")), x.findtext("P_LINK") or "") for x in (auth.iter("PRINCIPAL") if auth is not None else ())]
    co = [(text(x.findtext("CO_NAME")), slug(x.findtext("CO_LINK")), x.findtext("CO_LINK") or "") for x in (auth.iter("ADDITIONAL") if auth is not None else ())]
    bg = root.find("BACKGROUND")
    g = lambda tag: text(bg.findtext(tag)) if bg is not None else ""
    return {"short": text(root.findtext("SHORTTITLE")), "long": text(root.findtext("LONGTITLE")),
            "disposition": g("DISPOSITION"), "deadline": g("DEADLINE"), "vote": g("VOTETYPE"), "revenue": g("REVENUE"),
            "effective": g("EFFECTIVEDATE"), "chapter": g("CHAPNUM"),
            "authors": [(n, s, "S" if "senate_" in l.lower() else "H") for n, s, l in princ + co if n],
            "principals": len([1 for n, _, _ in princ if n]), "actions": sorted(acts)}


def dated(session, acts):
    """Each "MM/DD ..." line -> (ISO date, house or "", the rest), in order. Dates carry no year: the session's, unless a
    line comes months before the one above it (a veto taken up the next January), which is the next year."""
    out, year, prev = [], session, None
    for _, a, vote in acts:
        m = re.match(r"(\d\d)/(\d\d)\s+(?:\(([HS])\)\s*)?(.*)$", a)
        if not m:
            out.append(((out[-1][0] if out else ""), "", a, vote))
            continue
        try:
            d = date(year, int(m.group(1)), int(m.group(2)))
        except ValueError:
            out.append(((out[-1][0] if out else ""), m.group(3) or "", m.group(4), vote))
            continue
        if prev and (prev - d).days > 150:
            year += 1
            d = date(year, d.month, d.day)
        prev = d
        out.append((d.isoformat(), m.group(3) or "", text(m.group(4)), vote))
    # Same-day lines keep the file's order; a later line dated earlier (rare) is put in its place.
    return sorted(out, key=lambda x: x[0])


def decode(session, h, a):
    """One action in house h -> (shared wording the rules use or a readable line, kind)."""
    H = HOUSE.get(h, "")
    m = re.match(r"(?:Re-?)?referred To (.+)$", a, re.I)
    if m and not re.match(r"Veto ", a):
        cs = [comm_name(c) for c in m.group(1).split(";") if text(c)]
        return f"REFERRED TO {cs[0]}", ("ref", cs)
    # "DR - TSDP: JA To AP", "DR - TSDPAA: ..." (as amended), "DR - TSDPCS: ..." (a committee substitute), "DR - TSDBA:
    # ..." (a resolution: "do be adopted").
    m = re.match(r"DR - TSD(?!NP)\w*:\s*(\w+)\s+To\s+(\w+)", a, re.I)
    if m:
        codes = committee_codes(session, h)
        to = codes.get(m.group(2).upper(), m.group(2))
        return f"REPORTED REFERRED TO {to}", ("dr", to)
    if re.match(r"DR - TSDNP|Title Suff Do Not Pass|Do Not Pass", a, re.I):
        return f"{H}: the committee recommended it not pass", ("defeated", None)
    if re.match(r"Title Suff (?:Do Pass|Do Be Adopted|Adopted)|Do Pass", a, re.I):
        return "REPORTED", ("reported", None)
    if re.match(r"(?:Passed|Adopted)(?: As Amended)?$", a, re.I):
        return f"PASSED {H.upper()}", ("passed", None)
    if re.match(r"Failed$", a, re.I):
        return f"Failed in the {H}", ("failed", None)
    if re.match(r"Reconsidered$", a, re.I):
        return f"The {H} reconsidered its vote", ("reconsidered", None)
    if re.match(r"Died In Committee", a, re.I):
        return f"Died in {H} committee (deadline)", ("died", "committee")
    if re.match(r"Died On Calendar", a, re.I):
        return f"Died on the {H} calendar (deadline)", ("died", "floor")
    if re.match(r"Died In Conference", a, re.I):
        return "Died in conference", ("died", "conference")
    if re.match(r"Died by Other Means", a, re.I):
        return "Died (by other means)", ("died", "other")
    if re.match(r"Recommitted to Committee", a, re.I):
        return f"Sent back to committee by the {H}", ("recommitted", None)
    if re.match(r"Transmitted To (House|Senate)", a, re.I):
        return f"Sent to the {HOUSE[OTHER[h]] if h else 'other house'}", ("sent", None)
    if re.match(r"Returned For Concurrence", a, re.I):
        return f"Sent back to the {HOUSE[OTHER[h]] if h else 'first house'} to agree to the {H}'s changes", ("back", None)
    if re.match(r"Concurred in Amend", a, re.I):
        return f"The {H} agreed to the other house's changes", ("concurred", None)
    if re.match(r"Decline(?:d)? to Concur(?!.*Lost)", a, re.I):
        return f"The {H} declined the other house's changes and asked for a conference", ("conf", None)
    m = re.match(r"Conferees Named\s*(.*)$", a, re.I)
    if m:
        return f"{H} conference committee members: {', '.join(text(x) for x in m.group(1).split(','))}", ("conferees", None)
    if re.match(r"Conference Report Filed", a, re.I):
        return f"Conference committee report filed in the {H}", ("conffiled", None)
    if re.match(r"Conference Report Adopted", a, re.I):
        return f"The {H} adopted the conference committee report", ("confadopted", None)
    if re.match(r"Conference Report Failed|Conference Report Not Adopted", a, re.I):
        return f"The {H} rejected the conference committee report", ("confreject", None)
    if re.match(r"Recommitted For Further Conf|Returned to Conference", a, re.I):
        return f"Sent back to the conference committee by the {H}", ("reconf", None)
    if re.match(r"Returned For Enrolling", a, re.I):
        return f"Passed both houses; sent back to the {HOUSE[OTHER[h]] if h else 'first house'} for enrolling", ("enroll", None)
    if re.match(r"Enrolled Bill Signed", a, re.I):
        return f"Signed by {PRESIDING.get(h, 'the presiding officer')}", ("signed", None)
    if re.match(r"Approved by Governor", a, re.I):
        return "Signed by the governor", ("approved", None)
    if re.match(r"Law W/?out Governor", a, re.I):
        return "Became law without the governor's signature", ("nosig", None)
    if re.match(r"Partially Vetoed", a, re.I):
        return "Partially vetoed by the governor", ("partial", None)
    if re.match(r"Vetoed$", a, re.I):
        return "VETOED", ("vetoed", None)
    m = re.match(r"Veto Referred To (.+)$", a, re.I)
    if m:
        return f"The veto was referred to the {H} {comm_name(m.group(1))} Committee", ("vetoref", None)
    if re.match(r"Veto Overridden", a, re.I):
        return f"The {H} overrode the veto", ("override", None)
    if re.match(r"Veto Sustained", a, re.I):
        return f"The {H} sustained the veto", ("sustained", None)
    m = re.match(r"Suspend from Deadlines by ([HS])C\s*(\d+)", a, re.I)
    if m:
        return f"Exempted from the deadlines ({HOUSE[m.group(1).upper()]} Concurrent Resolution {m.group(2)})", ("suspend", None)
    m = re.match(r"Motion to Reconsider Entered\s*(.*)$", a, re.I)
    if m:
        return f"{H}: motion to reconsider entered{(' ' + m.group(1)) if m.group(1) else ''}", ("mtr", None)
    if re.match(r"Motion to Reconsider Tabled", a, re.I):
        return f"{H}: motion to reconsider tabled", ("mtrdone", None)
    return (f"{H}: {a}" if H else a), ("other", None)


SMALL = {"a", "an", "and", "as", "at", "by", "for", "from", "in", "into", "of", "on", "or", "the", "to", "with"}


ACRONYMS = re.compile(r"\b(dna|dfa|mdot|mdoc|mdhs|mde|mdeq|mema|ihl|pers|mda|fy|u\.s\.|llc|ems|gps|atv|ii|iii|iv)\b")


def sentence(long, short):
    """The long title in capitals -> a sentence: "AN ACT TO AMEND SECTION 9-5-13, MISSISSIPPI CODE OF 1972, TO REVISE THE
    NUMBER OF CHANCELLORS FOR THE THIRD CHANCERY COURT DISTRICT ..." -> "An act to amend Section 9-5-13, Mississippi Code
    of 1972, to revise the number of chancellors for the Third Chancery Court District ...". Names come back from the
    short title's capitalized phrases ("Third Chancery Court District") and acronyms ("CON", "MDOT")."""
    t = text(long)
    if not t:
        return ""
    if re.search(r"[a-z]", t):
        return t
    t = t.lower()
    t = re.sub(r"\bmississippi\b", "Mississippi", t)
    t = re.sub(r"\bsections?\b(?= \d)", lambda m: m.group(0).capitalize(), t)
    t = re.sub(r"\bcode of 1972\b", "Code of 1972", t)
    t = re.sub(r"\b(chapter|title|article) (\d+)", lambda m: f"{m.group(1).capitalize()} {m.group(2)}", t)
    t = re.sub(r"\b(january|february|march|april|may(?= \d)|june|july|august|september|october|november|december)\b",
               lambda m: m.group(1).capitalize(), t)
    t = re.sub(r"\b(united states|state of Mississippi|gulf of mexico|medicaid|medicare|internet|national guard|god|english)\b",
               lambda m: " ".join(w if w in SMALL or w[0].isupper() else w.capitalize() for w in m.group(1).split()), t)
    # Names: runs of two or more capitalized words in the short title ("Oktibbeha County", "Department of Revenue").
    for name in re.findall(r"\b[A-Z][\w'’.-]*(?:\s+(?:of|and|for|the|on)?\s*[A-Z][\w'’.-]*)+", short):
        name = re.sub(r"^(?:An?|The)\s+", "", text(name))
        if len(name.split()) >= 2:
            t = re.sub(r"\b" + re.escape(name) + r"\b", name, t, flags=re.I)
            if name.startswith("MS "):  # "MS Task Force ..." in the short title, "Mississippi Task Force ..." in the long
                full = "Mississippi " + name[3:]
                t = re.sub(r"\b" + re.escape(full) + r"\b", full, t, flags=re.I)
    # Acronyms and single proper words the short title spells in capitals or capitalizes mid-phrase.
    for w in set(re.findall(r"\b[A-Z]{2,}\b", short)):
        if w.lower() not in SMALL:
            t = re.sub(r"\b" + w.lower() + r"\b", w, t)
    t = ACRONYMS.sub(lambda m: m.group(1).upper(), t)
    t = re.sub(r"\bmississippi\b", "Mississippi", t)
    t = re.sub(r"\bMississippi constitution\b", "Mississippi Constitution", t)
    return t[:1].upper() + t[1:]


def title_of(short):
    return text(short).rstrip(" .;,")


VOTE_NOTE = {"Three/Fifths": "Passing it takes three-fifths of each house.",
             "Two/Thirds": "Passing it takes two-thirds of each house."}


def load_session(session):
    """Read one year's bills and return (records, bill number -> record index, fetched time, delegation)."""
    cur = current_members()
    by_slug = {(h, s): m for (h, s), m in cur.items()}
    parties = _PARTIES.setdefault(session, {})
    paths = [os.path.join(folder(session), "allmsrs.xml")]
    fetched = datetime.fromtimestamp(max(os.path.getmtime(f) for f in paths if os.path.exists(f)), ZoneInfo(P.TIMEZONE)).strftime("%Y-%m-%d %H:%M")
    recs, index = [], {}
    for key in listed(session):
        hs, kind, num = key[0], key[1], int(key[2:])
        x = history(session, key)
        if not x or not x["actions"] or not x["short"]:
            continue  # a number never used (HB 925 of 2026: no title, no actions)
        title = title_of(x["short"])
        amendment = is_amendment(kind, title)
        if kind == "C" and not amendment:
            continue
        origin, other = hs, OTHER[hs]
        p = f"{hs}{kind}{num}"
        steps = []  # (date, house, shown text, kind, extra)
        for d, h, a, vote in dated(session, x["actions"]):
            shown, (k, extra) = decode(session, h, a)
            steps.append((d, h, shown, k, extra))
            if k == "ref" and len(extra) > 1:
                for c in extra[1:]:
                    steps.append((d, h, f"Also referred to the {HOUSE[h]} {c} Committee, after the first", "ref2", c))
        # Each house's last decisive vote (a passage, a concurrence, adopting a conference report), which "Reconsidered"
        # undoes; a motion to reconsider entered and never decided holds the vote: when the bill then dies (HB 1602 of
        # 2026, held in the House on a motion to reconsider until the deadline), the vote never took effect.
        passed, last_vote, mtr = set(), {}, set()
        concurred = enrolled = False
        signed_by, conf = set(), set()
        law = veto = partial = died = False
        overrides = set()

        def undo(h):
            nonlocal concurred
            kv = last_vote.pop(h, None)
            if kv == "passed":
                passed.discard(h)
            elif kv == "concurred":
                concurred = False
            elif kv == "confadopted":
                conf.discard(h)

        for d, h, t, k, extra in steps:
            if k == "passed":
                passed.add(h)
            elif k == "concurred":
                concurred = True
            elif k == "confadopted":
                conf.add(h)
            elif k == "reconsidered":
                undo(h)
                mtr.discard(h)
            elif k == "mtr":
                mtr.add(h)
            elif k in ("mtrdone", "sent", "back", "enroll", "signed"):
                mtr.discard(h)
            elif k == "reconf":
                conf = set()
            if k in ("passed", "failed", "concurred", "confadopted"):
                last_vote[h] = k
            if k == "enroll":
                enrolled = True
            elif k == "signed":
                signed_by.add(h)
            elif k in ("approved", "nosig"):
                law = True
            elif k == "partial":
                law = partial = True
            elif k == "vetoed":
                veto = True
            elif k == "override":
                overrides.add(h)
            elif k == "died":
                died = True
        if died:
            for h in mtr:
                undo(h)
        both = concurred or enrolled or conf >= {"S", "H"} or bool(signed_by)
        chapter = x["chapter"].strip()
        if veto and overrides >= {"S", "H"}:
            law = True
        if chapter.isdigit() and not (veto and not law):
            law = True
        sent = signed_by >= {"S", "H"} or law or veto
        if sent or both:
            both = True
        if amendment:
            stage = 3 if both else (2 if passed else None)
        elif law:
            stage = 5
        elif veto:
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
        # Where a bill that hasn't passed its own house is (or ended).
        where_h, place, comm, pending = origin, "desk", None, []
        for d, h, t, k, extra in steps:
            if k == "ref":
                where_h, place, comm, pending = h, "committee", extra[0], list(extra[1:])
            elif k == "dr":
                where_h, place, comm = h, "committee", extra
            elif k == "reported":
                where_h, place, comm = h, "floor", None
            elif k == "recommitted":
                where_h, place = h, "committee"
            elif k == "passed":
                where_h, place, comm = OTHER[h], "desk", None
            elif k == "back":
                where_h, place, comm = OTHER[h], "floor", None
        death = [extra for _, _, _, k, extra in steps if k == "died"]
        if death and stage is None and passed == set():
            # Its death line says where it was: "Died On Calendar" (a vote held on a motion to reconsider, too).
            place = "floor" if death[-1] == "floor" else "committee" if death[-1] == "committee" else place
            where_h = next((h for _, h, _, k, _ in reversed(steps) if k == "died" and h), where_h)
        if stage is None:
            stage = 1 if place == "floor" else 0
        refs = [(h, extra[0]) for _, h, _, k, extra in steps if k == "ref"] + \
               [(h, extra) for _, h, _, k, extra in steps if k in ("dr", "ref2")]
        comm_list = sorted({f"{h} · {c}" for h, c in refs})
        # A bill's first committee: approved (reported, or passed on to its second committee), or no action (most bills
        # die there at the deadline; Mississippi's committees rarely vote a bill down).
        first_ref = next((i for i, s in enumerate(steps) if s[3] == "ref"), None)
        after = [s[3] for s in steps[first_ref + 1:]] if first_ref is not None else []
        fate = ("passed" if "reported" in after or "dr" in after or passed else "defeated" if "defeated" in after else "none")
        local = any(c == "Local and Private Legislation" for _, c in refs)
        long_s = sentence(x["long"], x["short"])
        if amendment:
            t2 = re.sub(r"^(?:Mississippi )?Constitution(?: of 1890)?\s*;\s*", "", title, flags=re.I)
            title = "Constitutional amendment: " + t2 if t2 else "Constitutional amendment"
        topics = list(dict.fromkeys((["const"] if amendment else []) + (["local"] if local else []) +
                                    [P.COMMITTEE_TOPICS[c] for _, c in refs if c in P.COMMITTEE_TOPICS] +
                                    [k for k in P.TOPIC_WORDS if P.TOPIC_WORDS[k].search(x["short"])]))
        # Authors: the principal authors first, then co-authors, by their author pages; full names from the current
        # member files, else that year's author list.
        names, district = [], 0
        for i, (short, sl, h) in enumerate(x["authors"]):
            m = by_slug.get((h, sl))
            full = m["name"] if m else authors(session, h).get(sl) or short
            if m and m["party"] in ("D", "R"):
                parties[(h, full)] = m["party"]
            if i == 0 and m and h == origin:
                district = m["district"]
            if full and full not in names:
                names.append(full)
        sponsor = names[0] if names else "—"
        cos = names[1:]
        if stage == 0:
            desc = f"In {HOUSE[where_h]} committee"
        elif stage == 1:
            desc = f"On the {HOUSE[where_h]} floor"
        else:
            desc = {2: f"Passed the {HOUSE[origin] if origin in passed else HOUSE[other]}", 3: "Passed both houses",
                    4: "On the governor's desk", 5: "Became law", 6: "Vetoed"}[stage]

        def dates(test, mode="last"):
            ds = sorted({s[0] for s in steps if test(s) and s[0]})
            return {"first": ds[0], "last": ds[-1], "all": ";".join(ds)}[mode] if ds else ""

        action_dates = [s[0] for s in steps if s[0]]
        sigs = sorted(s[0] for s in steps if s[3] == "signed" and s[0])
        gov_day = dates(lambda s: s[3] in ("approved", "nosig", "partial"), "first")
        veto_day = dates(lambda s: s[3] == "vetoed", "first")
        override_day = dates(lambda s: s[3] == "override", "last")
        summary = " ".join(t for t in (long_s, VOTE_NOTE.get(x["vote"], "") if not amendment else "") if t)
        rec = {
            "nums": [p], "base": [p], "prev": earlier(session, x, p, law),
            "title": title, "summary": summary, "act": "", "lawCode": "", "law": None, "laws": [],
            "comms": comm_list, "topics": topics, "places": [],
            "narrow": "place" if local else P.narrow_kind(title),
            "commFate": fate, "mainTopic": topics[0] if topics else "", "local": "local" in topics,
            "senDeleg": False, "asmDeleg": False, "budget": x["deadline"] == "Appropriation",
            "passedS": "S" in passed, "passedA": "H" in passed, "program": None,
            "stage": stage, "passedIn": (HOUSE[origin] if origin in passed else HOUSE[other]) if stage == 2 else None,
            "chapter": int(chapter) if chapter.isdigit() and stage == 5 else None,
            "veto": None, "memo": "", "vetoMemo": None,
            "simText": f"{x['short']} {x['long'].lower()}",
            "comm": comm if stage == 0 and place == "committee" else None,
            "first": min(action_dates, default=f"{session}-01-01"),
            "last": max(action_dates, default=f"{session}-01-01"),
            "cosp": len(cos),
            "keyDates": [
                dates(lambda s: s[3] in ("reported", "dr"), "first"),
                dates(lambda s: s[3] == "passed" and s[1] == "S", "all") if "S" in passed else "",
                dates(lambda s: s[3] == "passed" and s[1] == "H", "all") if "H" in passed else "",
                "",
                (sigs[-1] if len(sigs) >= 2 else sigs[-1] if sigs else "") if stage >= 4 and not amendment else "",
                (gov_day or override_day or max(action_dates, default="")) if stage == 5 else "",
                veto_day if stage == 6 or (stage == 5 and veto and not partial) else "",
            ],
            "votes": [], "firstComms": [(refs[0][0], refs[0][1], fate == "passed")] if refs else [],
            "vers": [{"p": p, "sponsor": sponsor, "district": district, "cosponsors": cos, "primes": max(1, x["principals"]),
                      "cosp": len(cos), "statusDesc": desc,
                      "committee": comm if place == "committee" and stage in (0, 2) else None,
                      "actions": [[s[0], s[2]] for s in steps],
                      "link": bill_link(key, session)}],
        }
        index[p] = len(recs)
        recs.append(rec)
    return recs, index, fetched, {"SENATE": [], "ASSEMBLY": []}


def bill_link(key, session):
    """The bill's status page (the history file, which the browser shows through the Legislature's stylesheet)."""
    return f"https://billstatus.ls.state.ms.us/{session}/pdf/history/{key[:2]}/{key}.xml"


_TITLES = {}


def _titles(session):
    if session not in _TITLES:
        out = {}
        for key in listed(session):
            x = history(session, key)
            if not x or not x["short"] or x["chapter"].strip().isdigit() or x["disposition"] == "Law":
                continue  # laws aren't tried again (yearly bills share titles)
            if key[1] == "C" and not is_amendment("C", title_of(x["short"])):
                continue
            first = x["authors"][0][1] if x["authors"] else ""
            out.setdefault(title_of(x["short"]).lower(), []).append((f"{key[0]}{key[1]}{int(key[2:])}", first))
        _TITLES[session] = out
    return _TITLES[session]


def earlier(session, x, p, law=False):
    """The same bill in the two years before: the same short title and the same principal author, or a short title only
    one bill had that year and has this year. Appropriations aren't linked (each year's are new bills)."""
    out = set()
    k = title_of(x["short"]).lower()
    who = x["authors"][0][1] if x["authors"] else ""
    if len(k.split()) < 4 or re.match(r"appropriations?\b", k):
        return out
    for y in (session - 1, session - 2):
        if y not in sessions():
            continue
        old = _titles(y).get(k, [])
        same = [n for n, sp in old if sp and sp == who]
        if same:
            out.add((y, same[0]))
        elif len(old) == 1 and len(_titles(session).get(k, [])) <= 1:
            out.add((y, old[0][0]))
    return out


def parties(session, recs):
    if session not in _PARTIES:
        load_session(session)
    return {k: v for k, v in _PARTIES.get(session, {}).items() if v in ("D", "R")}
