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

Floor votes come from the roll calls the history lines link (one PDF per vote, read as text by fetch.py into
<year>/rollcalls.json): each passage, failed passage, concurrence, conference report and veto vote gets its tally and,
when every group's names add up to its total, each member's vote (`roll_vote()`; names to seats by `vote_seat()`).
The history lines themselves carry no tallies. No committee votes: Mississippi publishes none.
There are no plain-language summaries: the long title, in sentence case, is the summary; no "What it does".
"""
import functools, glob, html, json, os, re
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from fetch_contacts import name_key
from states import letters as L
from states.ms import profile as P
from states.undated import settle

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
        # This year's session (or next year's, prefiled) counts from its first bills; an older one from 100.
        least = 0 if int(os.path.basename(f)) >= datetime.now().year else 100
        if os.path.exists(os.path.join(f, "allmsrs.xml")) and len(glob.glob(os.path.join(f, "history", "*.xml"))) > least:
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
            # (The roll call's PDF, "../../../../2026/pdf/votes/house/0030003.pdf", as "house/0030003".)
            vm = re.search(r"votes/((?:house|senate)/\d+)\.pdf", text(a.findtext("ACT_VOTE")))
            acts.append((int(n) if n.isdigit() else len(acts) + 1, d, vm.group(1) if vm else ""))
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


MONTH_DAY = re.compile(r"(January|February|March|April|May|June|July|August|September|October|November|December) (\d{1,2}), (\d{4})")


def veto_message(session, key):
    """The governor's veto message (vetoes/<HB0895>.htm, a Word page; fetch.py's veto_messages()) -> {year, signer,
    text}: its paragraphs after "GOVERNOR'S VETO MESSAGE FOR HOUSE BILL 895", up to the signature, or None."""
    try:
        page = open(os.path.join(folder(session), "vetoes", f"{key}.htm"), encoding="cp1252", errors="replace").read()
    except OSError:
        return None
    paras = [re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", x))).strip()
             for x in re.findall(r"(?is)<p\b[^>]*>(.*?)</p>", page)]
    paras = [x for x in paras if x and x != "\xa0"]
    # (A suffrage bill's veto comes as a notice, "MESSAGE FROM THE GOVERNOR ... has vetoed the following Senate Bill", with
    # no reasons: left out.)
    start = next((i + 1 for i, x in enumerate(paras) if re.match(r"GOVERNOR\W?S\W? (?:PARTIAL )?VETO MESSAGE", x, re.I)), None)
    if start is None:
        return None
    body, day = [], ""
    for x in paras[start:]:
        d = MONTH_DAY.search(x)
        if re.match(r"(?:Respectfully|Sincerely)|(?:TATE|Tate) REEVES|GOVERNOR$", x) or (d and len(x) < 60):
            day = day or (d and " ".join(d.groups())) or ""
            if body:
                break
            continue
        x = re.sub(r"^1 am\b", "I am", x)  # (an OCR'd "I")
        if body and not re.search(r"[.:;!?\"\u201d)]$", body[-1]):
            body[-1] += " " + x  # a paragraph the page breaks mid-sentence ("... WITH THE" / "PRACTITIONER AFTER THE ...")
        else:
            body.append(x)
    if not day:
        d = MONTH_DAY.search(" ".join(paras))
        day = " ".join(d.groups()) if d else ""
    iso = datetime.strptime(day, "%B %d %Y").date().isoformat() if day else f"{session}-04-30"
    # The bill's long title, quoted in full ("I am returning House Bill 895: "AN ACT TO AMEND ... FOR RELATED
    # PURPOSES.""), is already the page's title: left out.
    body = [re.sub(r"(Bill \d+)\s*:?\s*[\"\u201c]?\s*AN ACT\b.*?RELATED PURPOSES\.?\s*[\"\u201d]?", r"\1.", x, flags=re.S)
            for x in body]
    s = L.cut(body)
    return {"year": int(iso[:4]), "signer": P.governor_on(iso), "text": s} if s else None


# ---- Floor roll calls ----

# Each year's Speaker, who votes as "Mr. Speaker" (by the author page's slug). Philip Gunn to January 2024, Jason White since.
SPEAKERS = {2023: "gunn", 2024: "white", 2025: "white", 2026: "white", 2027: "white"}
# The groups of a roll call, as each house writes them, -> the site's codes ("Y" read only to count against the total).
GROUPS = [(re.compile(r"Yeas\s*-+"), "Y"), (re.compile(r"Nays\s*-+"), "N"),
          (re.compile(r"Absent (?:or|and) those not voting\s*-+"), "A"), (re.compile(r"(?:Voting )?Present\s*-+"), "B")]
GROUP_START = re.compile(r"(Yeas|Nays|Absent (?:or|and) those not voting|Voting Present|Present|Vacancies|Necessary for Passage)\s*-+")
# The decisive votes the history's lines link a roll call to (procedural ones, "Motion to Recommit Lost", "Tabled Failed",
# aren't the bill's own vote).
VOTE_KINDS = {"passed", "failed", "concurred", "confadopted", "confreject", "override", "sustained"}
ROLL_STATS = {}


@functools.lru_cache(maxsize=None)
def roll_texts(session):
    """data/ms/<year>/rollcalls.json (fetch.py's roll_calls()): "house/0030003" -> the PDF's text."""
    try:
        raw = json.load(open(os.path.join(folder(session), "rollcalls.json")))
    except (OSError, ValueError):
        return {}
    return {k: v["text"] for k, v in raw.items() if v.get("text")}


def parse_roll(t):
    """A roll call's text -> {"bill": "HB1", "groups": {"Y": [names], "N": ..., "A": ..., "B": ...}, "totals": {...},
    "paired": [names]}, or None. Names are as printed: "Anderson (110th)", "Simmons D. T. (12th)", "Mr. Speaker"; a name the
    layout breaks after a hyphen ("Butler-" / "Washington") is joined. "Total--116." (or "Total--5" without the period)
    ends a group; "None." and "Nays-0" are empty ones. Senators who "announced a pair" (each would have voted, one yea and
    one nay) are in no group: they're listed as paired."""
    t = re.sub(r"-\s*\n\s*", "-", t or "")
    t = re.sub(r"\s+", " ", t).strip()
    first = GROUP_START.search(t)
    if not first:
        return None
    head = t[:first.start()]
    m = re.search(r"\b([HS])\.\s*([BC])\.\s*(?:R\.\s*)?No\.\s*(\d+)", head)
    if not m:
        return None
    out = {"bill": f"{m.group(1)}{m.group(2)}{int(m.group(3))}", "groups": {}, "totals": {}, "paired": [], "head": head}
    starts = list(GROUP_START.finditer(t))
    for i, g in enumerate(starts):
        code = next((c for rx, c in GROUPS if rx.fullmatch(g.group(0).strip()) or rx.match(g.group(0))), None)
        end = starts[i + 1].start() if i + 1 < len(starts) else len(t)
        body = t[g.end():end].strip()
        if code is None:
            continue
        # (A pair announcement or a closing note can follow the last group: cut at its sentence.)
        tot = re.search(r"\.?\s*Total\s*-+\s*(\d+)\.?", body)
        if tot:
            names_part = body[:tot.start()]
            out["totals"][code] = int(tot.group(1))
        else:
            z = re.match(r"(None|0)\b\.?", body)
            names_part = "" if z else body.split(". ")[0]
            out["totals"][code] = 0 if z else None
        names = [re.sub(r"\s+", " ", x).strip(" .") for x in names_part.split(",")]
        out["groups"][code] = [x for x in names if x]
    for pm in re.finditer(r"(?:Senator|Representative)\s+([A-Z][A-Za-z'.() -]+?),?\s+who would have voted", t[first.start():]):
        out["paired"].append(pm.group(1).strip())
    vac = re.search(r"Vacanc(?:y|ies)\s*-+\s*(\d+)", t)
    out["vacant"] = int(vac.group(1)) if vac else 0
    out["paired"] = list(dict.fromkeys(x for x in out["paired"] if not any(x in g for g in out["groups"].values())))
    return out


SEATS = {"H": 122, "S": 52}
# The year the member files (data/ms/members/, the current members) are from.
MEMBERS_YEAR = date.today().year


def roll_adds_up(r, h):
    """Every group's names are as many as its total, and there are yeas. Or the yeas and nays do, and every seat is
    named once (with the vacancies): the total under the absent members is the slip (HB 1924 of 2026's override vote,
    "Absent or those not voting--" seven names, "Total--5", 110 + 0 + 5 + 7 = 122 seats)."""
    if "Y" not in r["groups"]:
        return False
    if all(r["totals"].get(c) is not None and r["totals"][c] == len(xs) for c, xs in r["groups"].items()):
        return True
    every = [x for xs in r["groups"].values() for x in xs] + r["paired"]
    return all(r["totals"].get(c) == len(r["groups"].get(c, [])) for c in ("Y", "N")) and \
        len(every) == len(set(every)) and len(every) + r.get("vacant", 0) == SEATS[h]


def fold(s):
    return re.sub(r"[^a-z]", "", (s or "").lower())


@functools.lru_cache(maxsize=None)
def vote_seat(session, h, name):
    """A roll-call name in house h -> the seat of a current member who sat that year ("H:110"), else "H?Name". The name is
    the member's short name, the author page's slug in lower case with underscores ("Anderson (110th)" =
    anderson_(110th)), or the surname with initials or a district where two members share it ("Simmons D. T. (12th)" =
    simmons_(12th)). "Mr. Speaker" is that year's Speaker. A current member counts only when that year's author list
    has the same slug and name (a seat's earlier holder of the same surname isn't today's member)."""
    n = re.sub(r"\s+", " ", (name or "").strip())
    sl = SPEAKERS.get(session) if h == "H" and re.match(r"M(?:r|adam)\.? Speaker", n) else None
    cur = current_members()
    year = authors(session, h)

    def words(x):
        return [w for w in re.sub(r"[^a-z\s-]", " ", (x or "").lower()).split() if w not in ("jr", "sr", "ii", "iii", "iv")]

    def served(s, m):
        """The slug is in that year's author list under the member's name: the same surname (spelled with or without its
        hyphen: "Angela Turner Ford" is turner-ford; the slug's, as the short name can be misspelled: "Butler-Washinton") and the same first initial or a given name in common ("Briggs Hopson"
        = "W. Briggs Hopson III", "Chuck Younger" = "Charles Younger"). In the member files' own year the surname is
        enough (that year's list says "Tamarra Butler-Washington", her member file "Grace Butler-Washington")."""
        full = year.get(s)
        sur = fold(" ".join(w for w in re.sub(r"\s*\(\d+\w*\)", "", s.replace("_", " ")).split()
                            if not re.fullmatch(r"(?i)jr\.?|sr\.?|ii|iii|iv", w)))
        if not full or not sur or not fold(" ".join(words(full))).endswith(sur):
            return False
        a, b = words(full)[:-1], words(m["name"])[:-1]
        return session >= MEMBERS_YEAR or bool(a and b and a[0][:1] == b[0][:1]) or \
            any(x.startswith(y) or y.startswith(x) for x in a for y in b if len(x) > 1 and len(y) > 1)

    cands = []
    if sl:
        cands = [(h, sl)]
    else:
        cands = [(h, n.lower().replace(" ", "_"))]
        if cands[0] not in cur:
            pm = re.match(r"(.+?)(?:\s+((?:[A-Z]\.\s*)+))?(?:\s+\((\d+)(?:st|nd|rd|th)\))?$", n)
            last, inits, dist = (pm.group(1), pm.group(2) or "", pm.group(3)) if pm else (n, "", None)
            hits = []
            for (hh, s), m in cur.items():
                if hh != h:
                    continue
                short = re.sub(r"\s*\(\d+\w*\)$", "", m["short"] or s)
                parts = [fold(x) for x in re.split(r"[ -]", short) if x]
                if fold(short) != fold(last) and fold(last) not in parts and fold(short.split()[0] if short else "") != fold(last):
                    continue
                if dist and f"({dist}" not in s and str(m["district"]) != dist:
                    continue
                if inits and not name_key(m["name"]).startswith(inits.strip()[0].lower()):
                    continue
                hits.append((hh, s))
            cands = hits
    good = [c for c in cands if c in cur and served(c[1], cur[c])]
    if len(good) == 1:
        return f"{h}:{cur[good[0]]['district']}"
    return f"{h}?{'Mr. Speaker' if sl else n}"


def roll_vote(session, key, p, h, d, k):
    """The floor vote a history line links, as a record's vote: [house, "F", None, day, yeas, nays, [[seat, code], ...]]
    (yes votes left out; absent and paired "A", voting present "B"), or None when the roll call isn't read yet or isn't
    this bill's. Names only when every group's names add up to its total; else the tally alone."""
    st = ROLL_STATS.setdefault(session, {"lines": 0, "read": 0, "wrong": 0, "named": 0, "unparsed": 0})
    st["lines"] += 1
    if not key or k not in VOTE_KINDS:
        return None
    txt = roll_texts(session).get(key)
    if not txt:
        return None
    st["read"] += 1
    r = parse_roll(txt)
    if not r or "Y" not in r["totals"]:
        st["unparsed"] += 1
        return None
    if r["bill"] != re.sub(r"^([HS][BC])0*", r"\1", p) or {"house": "H", "senate": "S"}[key.split("/")[0]] != h:
        st["wrong"] += 1  # filed under another bill or house
        return None
    y, n = r["totals"].get("Y") or 0, r["totals"].get("N") or 0
    listed = []
    if roll_adds_up(r, h):
        st["named"] += 1
        for code in ("N", "A", "B"):
            listed += [[vote_seat(session, h, x), code] for x in r["groups"].get(code, [])]
        listed += [[vote_seat(session, h, x), "A"] for x in r["paired"]]
    return [h, "F", None, d, y, n, listed]


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
        votes = []
        for d, h, a, vote in dated(session, x["actions"]):
            shown, (k, extra) = decode(session, h, a)
            steps.append((d, h, shown, k, extra))
            v = roll_vote(session, vote, p, h, d, k) if vote else None
            if v:
                votes.append(v)
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
        vmemo = veto_message(session, key) if stage == 6 or (stage == 5 and partial) else None
        if vmemo and stage == 5:
            vmemo["kind"] = "line-item"  # signed with parts vetoed
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
            "veto": None, "memo": "", "vetoMemo": vmemo,
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
            "votes": votes, "firstComms": [(refs[0][0], refs[0][1], fate == "passed")] if refs else [],
            "vers": [{"p": p, "sponsor": sponsor, "district": district, "cosponsors": cos, "primes": max(1, x["principals"]),
                      "cosp": len(cos), "statusDesc": desc,
                      "committee": comm if place == "committee" and stage in (0, 2) else None,
                      "actions": [[s[0], s[2]] for s in steps],
                      "link": bill_link(key, session)}],
        }
        if place == "committee" and stage in (0, 2) and comm and not died:
            _IN_COMM.setdefault(session, {})[p] = (where_h, comm)
        index[p] = len(recs)
        recs.append(rec)
    _IN_COMM.setdefault(session, {})
    settle(recs, folder(session))  # bills with no history yet: never dated in the future (states/undated.py)
    return recs, index, fetched, {"SENATE": [], "ASSEMBLY": []}


def bill_link(key, session):
    """The bill's status page (the history file, which the browser shows through the Legislature's stylesheet)."""
    return f"https://billstatus.ls.state.ms.us/{session}/pdf/history/{key[:2]}/{key}.xml"


_TITLES = {}
_IN_COMM = {}  # session -> {bill: (house, committee)} for bills in a committee now and not dead (agendas())


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


def comm_key(c):
    """A committee name for matching the House's schedule to the bills' committees: "Judiciary, Division A",
    "Judiciary A" and "JUDICIARY A COMMITTEE" are one."""
    c = comm_name(c).lower().replace("division ", "")
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", re.sub(r"\bcommittee\b", "", c))).strip()


def agendas(session):
    """Bills on upcoming Senate committee agendas (states/ms/fetch.py's agendas(): the Senate's agendas PDF), today or
    later: {"SB2328": [["Senate Judiciary, Division A", "2027-02-04T08:30:00"], ...]}. The House posts no agendas, only
    when its committees meet (fetch.py's house_schedule()): each such meeting is given to every bill in that House
    committee that hasn't died, with the kind "meets" (the page says the committee meets and the bill could come up, not
    that it's on the agenda) and a note when there's no clock time: ["House Judiciary A", "2027-01-20T00:00:00", "meets",
    "after the House adjourns"]. Only meetings in the session's own year count."""
    today = date.today().isoformat()
    out = {}
    try:
        data = json.load(open(os.path.join(folder(session), "agendas.json")))
    except (OSError, ValueError):
        data = {}
    for bill, meets in data.items():
        keep = [m for m in meets if m[1][:10] >= today]
        if keep:
            out[bill] = keep
    try:
        house = json.load(open(os.path.join(folder(session), "house_meetings.json")))
    except (OSError, ValueError):
        house = []
    house = [m for m in house if m[1][:10] >= today and m[1][:4] == str(session)]
    if house:
        if session not in _IN_COMM:
            load_session(session)
        by_comm = {}
        for name, when, note in house:
            by_comm.setdefault(comm_key(name), []).append((name, when, note))
        for bill, (h, comm) in _IN_COMM[session].items():
            for name, when, note in by_comm.get(comm_key(comm), []) if h == "H" else []:
                if any(m[1][:10] == when[:10] and m[0] == f"House {comm}" for m in out.get(bill, [])):
                    continue
                out.setdefault(bill, []).append([f"House {comm}", when, "meets"] + ([note] if note else []))
    for meets in out.values():
        meets.sort(key=lambda m: m[1])
    return out


def parties(session, recs):
    if session not in _PARTIES:
        load_session(session)
    return {k: v for k, v in _PARTIES.get(session, {}).items() if v in ("D", "R")}
