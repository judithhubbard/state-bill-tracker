"""Rhode Island's bills from LegiScan's files (downloaded by legiscan.py into data/ri/legiscan/<session_id>/; the General
Assembly's own site, rilegislature.gov, asks automated readers not to), in the shape build_data.py reads. The shared
reading is states/legiscan_convert.py; this file says what's particular to Rhode Island.

- What's shown: House and Senate bills of each year's regular ("January") session, and the joint resolutions proposing
  amendments to the Rhode Island Constitution ("JOINT RESOLUTION TO APPROVE AND PUBLISH AND SUBMIT TO THE ELECTORS A
  PROPOSITION OF AMENDMENT TO THE CONSTITUTION -- ..."). Other resolutions are left out, including joint resolutions
  that go to the governor and have the force of law (appropriations to named organizations, study commissions).
- Companions: most bills are introduced in both houses with the same text, a House bill and a Senate bill. Unlike
  Tennessee's, both versions keep moving: each passes its own house and then the other house ("in concurrence"), and
  each goes to the governor and becomes its own public law (so the official count of laws counts most new laws twice).
  LegiScan has no link between them (no "sasts"); a House and a Senate bill with exactly the same description (the
  heading and summary), when no other bill shares it, are shown as one record here, its stage the furthest either got.
  Each number keeps its own history and votes.
- History lines: "Introduced, referred to House Finance", "Referred to Senate Judiciary" (the second house),
  "Committee transferred to House Corporations", "Scheduled for hearing and/or consideration (03/04/2025)",
  "Committee recommended measure be held for further study" (how most bills end: a committee hears a bill and holds it;
  it can still be taken up again, as New York's "held for consideration"), "Committee recommends passage [of Sub A] [in
  concurrence]", "Committee recommended indefinite postponement" (voted down), "Placed on House Calendar (03/18/2025)",
  "House read and passed", "Senate passed Sub A", "Senate passed Sub A as amended". "In concurrence" means the house is
  agreeing to the version the other house already passed: the second house passing the bill unchanged ("Senate passed
  in concurrence"), or the first house accepting the second house's substitute ("House passed Sub A in concurrence").
  A second house's passage without it changed the bill, which goes back to the first house. Then "Transmitted to
  Governor", "Signed by Governor", "Effective without Governor's signature" (a law), "Vetoed by Governor". Some lines'
  chamber field names the wrong house ("Senate passed as amended in concurrence" filed under the House): a house named
  in the text decides.
- Laws have no numbers in the data (the official "Public Law 2025-123" isn't in LegiScan's records).
- Votes: floor roll calls ("Passage", "Passage In Concurrence", "Passage As Amended") and committee votes ("Senate
  Committee on Judiciary: Passage of Sub A"). Senate committees also vote to hold bills ("Be held for further study") or
  postpone them indefinitely; those votes aren't shown (the page lists committee votes as votes to approve). The history
  lines have no tallies, so each floor roll call goes to that day's passage in the bill it's filed under
  (`votes_by_version`).
- "What it does": the General Assembly's one-line description of the bill, which LegiScan carries as the bill's title.
"""
import os, re, sys

HERE = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from states import legiscan_convert as L
from states.ri import profile as P

HOUSE = L.HOUSE
AMENDMENT = re.compile(r"AMENDMENT TO THE CONSTITUTION", re.I)
SMALL = set("a an and as at by for from in into of on or the to with".split())


def comm(c):
    """"House Municipal Government & Housing" -> "Municipal Government and Housing"; "Senate Artificial Intelligence &
    Emerging Technol" -> "Artificial Intelligence and Emerging Technology"."""
    c = L.text(c)
    c = re.sub(r"^(?:the )?(?:House|Senate)\s+", "", c)
    c = re.sub(r"^Committee on\s+", "", c)
    c = re.sub(r"\s*\(.*$", "", c)
    c = re.sub(r",?\s*&\s*", " and ", c).replace("Internet and", "Internet, and")
    c = re.sub(r"Emerging Tech\w*$", "Emerging Technology", c)
    c = re.sub(r"\s+Committee$", "", c)
    return re.sub(r"\s+", " ", c).strip(" .,")


def house_named(a, h):
    m = re.match(r"(?:Introduced, referred to |Referred to |Committee transferred to |Placed on (?:the )?)?(House|Senate)\b", a)
    return {"House": "H", "Senate": "S"}[m.group(1)] if m else h


def decode(a, h, b, kind):
    """One history line -> [(house, kind, text shown, extra)]."""
    h = house_named(a, h)
    low = a.lower()
    origin = (b.get("bill_number") or "H")[0]
    if re.match(r"signed by governor", low):
        return [("G", "signed", "Signed by the governor", {})]
    if re.match(r"effective without governor'?s signature", low):
        return [("G", "nosign", "Became law without the governor's signature", {})]
    if re.match(r"vetoed by governor", low):
        return [("G", "veto", "Vetoed by the governor", {})]
    if re.search(r"veto", low) and re.search(r"overrid|overrode", low) and not re.search(r"fail|not ", low):
        return [(h, "override", a, {})]
    if re.match(r"transmitted to governor", low):
        return [(h, "sent", "DELIVERED TO GOVERNOR", {})]
    # Referrals (also to a second committee, and a bill sent back to committee from the floor).
    m = re.match(r"(?:Introduced, referred to|Referred to|Committee transferred to|(?:House|Senate) voted to recommit to)\s+(?:House|Senate)\s+(.+)$", a)
    if m:
        c = comm(m.group(1))
        return [(h, "refer", f"REFERRED TO {c.upper()}", {"comm": c})]
    if re.match(r"committee recommend(?:ed|s) (?:measure|substitute \w+|as amended)[^.]*be held for further study", low):
        return [(h, "held", a, {})]
    if re.match(r"committee recommended indefinite postponement|committee recommends no passage|defeated in committee", low):
        return [(h, "commfail", a, {})]
    if re.match(r"committee recommends passage", low):
        return [(h, "report", "REPORTED", {})]
    if re.match(r"recommended for immediate consideration", low) or \
            re.match(r"placed on (?:the )?(?:house|senate) (?:consent )?calendar", low):
        return [(h, "floor", a, {})]
    m = re.match(r"(House|Senate) (?:read and passed|passed\b.*)$", a)
    if m:
        h = {"House": "H", "Senate": "S"}[m.group(1)]
        other = HOUSE["S" if h == "H" else "H"]
        if "in concurrence" in low:
            # The first house agreeing to the second house's version, or the second house passing the first's unchanged.
            if h == origin:
                return [(h, "concur", f"Agreed to the {other}'s version ({a[len(m.group(1)) + 1:]})", {"amended": False})]
            return [(h, "pass", f"PASSED {HOUSE[h].upper()}", {"amended": False})]
        out = [(h, "pass", f"PASSED {HOUSE[h].upper()}", {"amended": h != origin})]
        if h != origin:
            sub = re.search(r"\bSub [A-Z]\b", a)
            out.append((h, None, f"Changed by the {HOUSE[h]}{f' ({sub.group(0)})' if sub else ''}: back to the {other} to agree", {}))
        return out
    if re.match(r"(?:house|senate) voted to reconsider$", low):
        return [(h, "reconsider", a, {})]
    if re.match(r"withdrawn at sponsor'?s request", low):
        return [(h, "withdrawn", "Withdrawn at the sponsor's request", {})]
    return [(h, None, a, {})]


def parts(b):
    """(heading, plain description): "COMMERCIAL LAW -- GENERAL REGULATORY PROVISIONS -- RIGHT TO ... - Requires
    manufacturers ..." Local acts outside the General Laws are written the other way round (LegiScan's description is
    the plain one, its title the heading); a joint resolution's title is "JOINT RESOLUTION ... (Proposes ...)"."""
    d, t = L.text(b.get("description")), L.text(b.get("title"))
    if b.get("bill_type") == "JR":
        m = re.match(r"(.*?)\s*\((.+?)\)?$", t)
        return (m.group(1), m.group(2)) if m else (t, "")
    m = re.match(r"([^a-z]+?) - (.+)$", d)
    if m:
        return m.group(1).strip(), m.group(2).strip()
    if not re.search(r"[a-z]", t):
        return t, d
    return "", d or t


def nice_heading(h):
    """"COMMERCIAL LAW -- RIGHT TO CONSUMER ACCESS" -> "Commercial Law -- Right to Consumer Access"."""
    words = h.split(" ")
    out = []
    for i, w in enumerate(words):
        lw = w.lower()
        if i and lw in SMALL:
            out.append(lw)
        elif re.search(r"\d", w) or len(w) <= 1:
            out.append(w)
        else:
            out.append(re.sub(r"[A-Za-z]+", lambda m: m.group(0).capitalize(), lw, count=1) if w.isupper() else w)
    return " ".join(out)


def short_title(text):
    first = re.split(r";\s+", text)[0].strip().rstrip(".")
    if len(first) > 220:
        first = first[:220].rsplit(" ", 1)[0] + "…"
    return first[:1].upper() + first[1:]


GENERAL_LAWS = set(P.TITLE_TOPICS) | {"STATUTES AND STATUTORY CONSTRUCTION", "SOLEMNIZATION OF MARRIAGES", "HOLIDAYS AND DAYS OF SPECIAL OBSERVANCE",
                                       "LIBRARIES", "CAPITAL DEVELOPMENT PROGRAM", "THE CAPITAL DEVELOPMENT PROGRAM", "PROBATE PRACTICE AND PROCEDURE",
                                       "PUBLIC PROPERTY AND WORKS", "FIDUCIARIES", "MILITARY AFFAIRS"}
TOWN_RX = re.compile(r"\b(?:" + "|".join(re.escape(t) for t in P.TOWN_NAMES) + r")\b", re.I)


def place_act(heading, plain):
    """A local act: for one city, town or district (bonds, charters, fire and water districts)."""
    segs = [s.strip() for s in re.split(r"\s+--?\s+", heading) if s.strip()]
    top = segs[0] if segs else ""
    if top and top not in GENERAL_LAWS and not top.startswith("MAKING") and \
            re.search(r"\b(?:TOWN|CITY|DISTRICT|CHARTER|LAND TRUST|SCHOOL|COMMISSION)\b|16-7-44", f"{heading} {plain.upper()}") and \
            (TOWN_RX.search(f"{heading} {plain}") or re.search(r"\bDISTRICT\b", heading)):
        return True
    # "TOWNS AND CITIES -- TOWN OF WARREN ..." or "-- BRISTOL COUNTY WATER AUTHORITY": a general-laws heading naming one place.
    return any(re.match(r"(?:(?:THE )?(?:TOWN|CITY) OF )?(?:" + "|".join(re.escape(t.upper()) for t in P.TOWN_NAMES) + r")\b", s) for s in segs[1:])


def same_text(b):
    return re.sub(r"\W+", " ", L.text(b.get("description")).lower()).strip()


class RhodeIsland(L.Rules):
    data_dir = P.DATA
    lower = "H"
    gates = set()
    votes_by_version = True

    def include(self, b):
        n = b.get("bill_number") or ""
        if b.get("bill_type") == "B" and re.match(r"[HS]\d+$", n):
            return "bill"
        if b.get("bill_type") == "JR" and AMENDMENT.search(L.text(b.get("title"))) and not re.search(r"UNITED STATES", L.text(b.get("title")), re.I):
            return "amendment"
        return None

    def decode(self, action, chamber, b, kind):
        return decode(action, chamber, b, kind)

    def committee_vote(self, desc):
        m = re.match(r"(House|Senate) Committee on (.+?):\s*(.*)$", desc or "")
        if not m:
            return None
        if not re.match(r"Passage", m.group(3)):
            return None  # a vote to hold or postpone: not shown (floor_vote leaves committee votes out)
        return comm(m.group(2))

    def floor_vote(self, desc):
        return not re.search(r"Amendment|Article|Committee", desc or "")

    def group(self, by_num):
        same = {}
        for n, b in by_num.items():
            same.setdefault(same_text(b), []).append(n)
        out, done = [], set()
        for ns in same.values():
            if len(ns) == 2 and {x[0] for x in ns} == {"H", "S"} and len(same_text(by_num[ns[0]]).split()) >= 4:
                out.append(sorted(ns))
                done.update(ns)
        out += [[n] for n in by_num if n not in done]
        return out

    def title(self, b):
        heading, plain = parts(b)
        if b.get("bill_type") == "JR":
            m = re.search(r"CONSTITUTION(?: OF THE STATE)?\s*[-–]*\s*(?:OF\s+)?(.+)$", heading)
            what = m.group(1).strip(" -–").lower() if m else plain
            what = re.sub(r"\brhode island\b", "Rhode Island", what)
            return "Constitutional amendment: " + (what or short_title(plain))
        return short_title(plain) if plain else nice_heading(heading)

    def summary(self, b):
        heading, plain = parts(b)
        return nice_heading(heading) if heading else ""

    def what(self, b):
        heading, plain = parts(b)
        if len(plain.split()) < 6:
            return None
        return plain[:1].upper() + plain[1:], "From the General Assembly's description of the bill (as LegiScan publishes it)."

    def topics(self, b, comms, title):
        heading, plain = parts(b)
        top = re.split(r"\s+--?\s+", heading)[0].strip() if heading else ""
        out = [P.COMMITTEE_TOPICS[c] for c in comms if c in P.COMMITTEE_TOPICS]
        if top in P.TITLE_TOPICS:
            out.insert(0, P.TITLE_TOPICS[top])
        if self.narrow(b, title) == "place":
            out.append("local")
        return out + [k for k, rx in P.TOPIC_WORDS.items() if rx.search(f"{title} {heading}")]

    def narrow(self, b, title):
        heading, plain = parts(b)
        if re.match(r"SOLEMNIZATION OF MARRIAGE", heading) or re.search(r"\bjoin\b.{0,120}\bin marriage\b|\bsolemnize\b.{0,80}\bmarriage\b", plain, re.I):
            return "person"
        if re.search(r"FORFEITURE OR REVOCATION OF THE CHARTER|\bINCORPORATE THE\b(?!.*\bDISTRICT\b)", heading.upper()):
            return "org"  # a lodge's, club's or company's charter restored
        if b.get("bill_type") == "B" and place_act(heading, plain):
            return "place"
        return P.narrow_kind(f"{title} {heading}")

    def link(self, b):
        return b.get("url") or ""

    def seat(self, session, pid, house, name):
        return _seats(session).get(pid)

    def earlier_key(self, b, kind):
        heading, plain = parts(b)
        d = plain.lower()
        return d if len(d.split()) >= 8 else None


RULES = RhodeIsland()
_SEATS, _LOADED = {}, {}


def _seats(session):
    """people_id -> seat for the members holding a seat now (contacts_<session>.json, built by contacts.py), in the
    current session only: earlier sessions' seats may have been held by others, so their voters keep their names."""
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
    """(records, number -> record index, fetched time, delegation), with earlier years' versions linked."""
    if session not in _LOADED:
        recs, index, fetched = L.load_session(RULES, session)
        older = {s: load_session(s)[0] for s in sessions() if session - 2 <= s < session}
        L.link_earlier(RULES, session, recs, older)
        _LOADED[session] = (recs, index, fetched)
    recs, index, fetched = _LOADED[session]
    return recs, index, fetched, {"SENATE": [], "ASSEMBLY": []}


def agendas(session):
    return {}


def parties(session, recs):
    return RULES.parties_.get(session, {})


if __name__ == "__main__":
    for s in sessions():
        recs = load_session(s)[0]
        print(s, len(recs), "records;", RULES.checks.get(s))
