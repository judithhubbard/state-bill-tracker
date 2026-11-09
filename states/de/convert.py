"""Delaware's bills (downloaded by states/de/fetch.py from legis.delaware.gov) in the shape build_data.py reads. House
and Senate bills of each two-year General Assembly (the 153rd is 2025-26), one record each: a bill replaced by a
substitute ("HS 1 for HB 457", a new text that takes the bill's place, usually in its committee) is shown under its own
number with the substitute's title, synopsis, sponsors, committee reports and roll calls. Constitutional amendments are
bills here ("AN ACT PROPOSING AN AMENDMENT TO ARTICLE V OF THE DELAWARE CONSTITUTION ..."; the next General Assembly's
"AN ACT CONCURRING IN A PROPOSED AMENDMENT ..."), tagged "const". Resolutions are left out.

The action history is plain English with the house at the end: "Introduced and Assigned to Education Committee in House";
"Assigned to Finance Committee in Senate" (the second house's committee, or a second committee: Appropriations or Finance
for bills that cost money); "Reported Out of Committee (Education) in House with 7 Favorable, 7 On Its Merits, 1
Unfavorable" (a committee releases a bill when a majority of its members sign the report, each one favorable, "on its
merits" (neither for nor against) or unfavorable: counts only, no names); "Tabled in Committee" (how committees hold
bills); "Motion to Release Failed"; "Passed By House. Votes: 39 YES 1 NO 1 ABSENT" (the passage; every passage is a roll
call); "Defeated By House. Votes: ..." (failed; "... Reason Taken: motion to ..." is a motion, not the bill); "Laid On
Table" / "Lifted From Table"; "Stricken" (withdrawn); "Returned to the House", "Roll Call Rescinded in House" (the House
took it back and undid its vote: HB 59 of 2025-26); "Signed by Governor", "Enact w/o Sign by Governor", "Vetoed by
Governor", "Line-Item Veto - See Governor's Advisory #46". The substitute's own lines carry its name ("HS 1 for HB 457 -
Passed By House ..."), its amendments' lines "HS 1 for HB 457 -  - Passed In House by Voice Vote", and other amendments'
"Amendment SA 1 to HB 140 - Defeated By Senate ..." (amendments are voted on separately; only adopted ones matter). The
lines carry only a date; within a day they keep the site's order (by action id).

Passed both houses: both houses passed it, and if the second house adopted an amendment, the first passed it again
afterwards (Delaware's first house concurs by passing the amended bill again); or the governor acted on it. Laws are
chapters of the Laws of Delaware, a volume a General Assembly ("Volume 85, Chapter 341": the bill page's Volume:Chapter).
"""
import json, os, re
from datetime import date, datetime
from zoneinfo import ZoneInfo

from states.de import profile as P

HOUSE = {"S": "Senate", "H": "House"}
CHAMBER = {"House": "H", "Senate": "S", 1: "S", 2: "H"}
_PARTIES, _CACHE, _SEATS = {}, {}, {}


def folder(session):
    return os.path.join(P.DATA, str(session))


def sessions():
    out = []
    for f in sorted(os.listdir(P.DATA)) if os.path.isdir(P.DATA) else []:
        d = os.path.join(P.DATA, f, "bills")
        if re.fullmatch(r"\d{4}", f) and os.path.isdir(d) and os.listdir(d):
            out.append(int(f))
    return out


def load(session, name):
    """One of an Assembly's files: list.json, members.json, committees.json -> lists."""
    key = (session, name)
    if key not in _CACHE:
        try:
            data = json.load(open(os.path.join(folder(session), f"{name}.json")))
        except (OSError, ValueError):
            data = None
        _CACHE[key] = data if data is not None else []
    return _CACHE[key]


def bill_file(session, key):
    try:
        return json.load(open(os.path.join(folder(session), "bills", f"{key}.json")))
    except (OSError, ValueError):
        return None


def vote_file(session, rid):
    try:
        return json.load(open(os.path.join(folder(session), "votes", f"{rid}.json")))
    except (OSError, ValueError):
        return None


def text(x):
    return re.sub(r"\s+", " ", str(x or "").replace(" ", " ")).strip()


def day(s):
    """"6/25/26" / "7/1/26 04:12 AM" / "/Date(1782419826587)/" -> "2026-06-25"."""
    s = text(s)
    m = re.match(r"(\d{1,2})/(\d{1,2})/(\d{2,4})", s)
    if m:
        y = int(m.group(3))
        return date(y + 2000 if y < 100 else y, int(m.group(1)), int(m.group(2))).isoformat()
    m = re.match(r"/Date\((-?\d+)\)/", s)
    if m:
        return datetime.fromtimestamp(int(m.group(1)) / 1000, ZoneInfo(P.TIMEZONE)).date().isoformat()
    return ""


def number(code):
    """"HB 457" -> "HB457"; anything else (resolutions) -> None."""
    m = re.fullmatch(r"(HB|SB) (\d+)", text(code))
    return f"{m.group(1)}{m.group(2)}" if m else None


def official(p):
    m = re.fullmatch(r"([A-Z]+)(\d+)", p)
    return f"{m.group(1)} {m.group(2)}" if m else p


def sub_key(row):
    """A substitute's file name: "HS 1 for HB 457" -> "HS1-HB457"."""
    m = re.match(r"([HS]S) (\d+) for ([HS]B) (\d+)", text(row.get("LegislationDisplayCode")))
    return f"{m.group(1)}{m.group(2)}-{m.group(3)}{m.group(4)}" if m else None


# ---- names -------------------------------------------------------------------------------------------------------

def full_name(m):
    """A member's display name with single spaces, without degrees: "Stephanie  T. Bolden" -> "Stephanie T. Bolden"."""
    n = text(m.get("DisplayName")) or text(f"{m.get('FirstName') or ''} {m.get('LastName') or ''}")
    return re.sub(r",?\s+(?:Ph\.?D\.?|M\.?D\.?|Esq\.?)$", "", n)


_PAGES = []


def party_of(m):
    """"D" or "R": the member list's party, else the member's page heading ("Former Representative Ronald E. Gray (R)":
    the list has no party for Gray and Yearick)."""
    if m.get("PartyCode"):
        return m["PartyCode"]
    if not _PAGES:
        try:
            _PAGES.append(json.load(open(os.path.join(P.DATA, "people.json"))))
        except (OSError, ValueError):
            _PAGES.append({})
    hm = re.search(r"\(([DRI])\)\s*$", text((_PAGES[0].get(str(m.get("PersonId"))) or {}).get("heading")))
    return hm.group(1) if hm else ""


def last_votes(session):
    """(house, short name) -> the last day the member voted (Y, N, NV or C) on a roll call this Assembly."""
    out = {}
    d = os.path.join(folder(session), "votes")
    for f in os.listdir(d) if os.path.isdir(d) else []:
        v = vote_file(session, f[:-5])
        if not v:
            continue
        h, when = CHAMBER.get(v.get("ChamberName")), day(v.get("TakenAtDateTime"))
        for x in v.get("AssemblyMemberVotes") or []:
            if x.get("SelectVoteTypeCode") in ("Y", "N", "NV", "C"):
                k = (h, text(x.get("ShortName")))
                out[k] = max(out.get(k, ""), when)
    return out


def seats(session):
    """(house, short name) -> seat id ("S:12", "H:20") for the member who held each seat last in this Assembly (by the
    last roll call each voted on); members who left (Sarah McBride, Senate 1, in January 2025) are "S?McBride"."""
    if session in _SEATS:
        return _SEATS[session]
    lv = last_votes(session)
    by = {}
    for m in load(session, "members"):
        h = CHAMBER.get(m.get("ChamberId"))
        dm = re.fullmatch(r"\d+", text(m.get("DistrictNumber")))
        if not h or not dm:
            continue
        by.setdefault(f"{h}:{int(dm.group(0))}", []).append(m)
    out = {}
    for sid, ms in by.items():
        ms.sort(key=lambda m: (lv.get((sid[0], text(m.get("ShortName"))), ""), m.get("AssemblyMemberId") or 0))
        for i, m in enumerate(ms):
            out[(sid[0], text(m.get("ShortName")))] = sid if i == len(ms) - 1 else f"{sid[0]}?{text(m.get('LastName'))}"
    _SEATS[session] = out
    return out


def members_by_short(session):
    """(house, short name) -> member; also (None, short name) when the short name is one member's in the Assembly."""
    out, seen = {}, {}
    for m in load(session, "members"):
        h = CHAMBER.get(m.get("ChamberId"))
        s = text(m.get("ShortName"))
        out[(h, s)] = m
        seen.setdefault(s, []).append(m)
    for s, ms in seen.items():
        if len(ms) == 1:
            out[(None, s)] = ms[0]
    return out


def sponsor_name(session, x, house=None):
    """A sponsor list entry ({"name": "K. Johnson", "house": "H", ...}) -> the member's full name ("Kendra Johnson")."""
    s = text(x.get("name"))
    by = members_by_short(session)
    m = by.get((x.get("house") or house, s)) or by.get((None, s))
    if not m and x.get("personId"):
        m = next((y for y in load(session, "members") if y.get("PersonId") == x.get("personId")), None)
    return full_name(m) if m else s


# ---- titles --------------------------------------------------------------------------------------------------------

CAPWORD = r"(?:[A-Z][A-Za-z'’]*|[A-Z]{2,})"
NAME_RUN = re.compile(rf"{CAPWORD}(?:(?:\s+|-)(?:(?:of|and|for|the|&|on|in)\s+)*{CAPWORD})+")


def casing(*texts):
    """How the bill's own mixed-case text writes names, from the synopsis and short title, to put them back into a title
    written in capitals: (phrases, words). Phrases are runs of two or more capitalized words in mid-sentence
    ("Economic & Financial Advisory Council"; three capitalized words or more), used only where the whole run is in the
    title; words are acronyms ("DNREC")."""
    phrases, words, lower = {}, {}, set()
    for t in texts:
        for sent in re.split(r"(?<=[.!?:;])\s+|\n", t or ""):
            sent = re.sub(r"^\W*\S+", " ", sent)  # a sentence's first word is capitalized anyway
            for m in NAME_RUN.finditer(sent):
                if len(re.findall(CAPWORD, m.group(0))) >= 3:  # "Office of Suicide Prevention", not "Individual Privacy"
                    phrases.setdefault(m.group(0).lower(), m.group(0))
            runs = [(m.start(), m.end()) for m in NAME_RUN.finditer(sent)]
            for m in re.finditer(r"[A-Za-z][A-Za-z'’]*", sent):
                w = m.group(0)
                if w == w.lower():
                    lower.add(w)
                elif re.fullmatch(r"[A-Z]{2,}", w) and w.lower() not in SMALL:  # acronyms ("DNREC") only
                    words.setdefault(w.lower(), w)
    return phrases, {k: v for k, v in words.items() if k not in lower or re.fullmatch(r"[A-Z]{2,}", v)}


ALWAYS = {"delaware": "Delaware", "dnrec": "DNREC", "deldot": "DelDOT", "u.s.": "U.S.", "fy": "FY", "dart": "DART",
          "i": "I", "ii": "II", "iii": "III", "iv": "IV", "v": "V", "vi": "VI", "vii": "VII", "viii": "VIII", "ix": "IX",
          "x": "X", "xi": "XI", "xii": "XII", "xiii": "XIII", "xiv": "XIV", "xv": "XV", "xvi": "XVI", "llc": "LLC", "co2": "CO2", "pfas": "PFAS", "ems": "EMS",
          "covid-19": "COVID-19", "new castle": "New Castle", "kent": "Kent", "sussex": "Sussex", "wilmington": "Wilmington",
          "dover": "Dover", "newark": "Newark", "america": "America", "american": "American", "january": "January",
          "february": "February", "march": "March", "april": "April", "may": "May", "june": "June", "july": "July",
          "august": "August", "september": "September", "october": "October", "november": "November", "december": "December"}
SMALL = {"of", "the", "and", "or", "for", "to", "in", "on", "a", "an", "by", "with", "at", "as", "from"}


def recase(caps, synopsis="", short=""):
    """A title in capitals -> a sentence with the bill's own spelling of names: "THE DELAWARE ECONOMIC & FINANCIAL
    ADVISORY COUNCIL" -> "The Delaware Economic & Financial Advisory Council" when the synopsis writes it so."""
    t = text(caps).rstrip(". ")
    if re.search(r"[a-z]", t):
        return t[:1].upper() + t[1:]
    phrases, case = casing(synopsis, short)
    words = re.split(r"(\s+|-|/)", t.lower())
    out = []
    for w in words:
        core = re.match(r"^([^A-Za-z]*)(.*?)([^A-Za-z]*)$", w)
        pre, mid, post = core.groups() if core else ("", w, "")
        k = mid.lower()
        if k in ALWAYS:
            mid = ALWAYS[k]
        elif k in case:
            mid = case[k]
        out.append(pre + mid + post)
    t = "".join(out)
    for low, name in sorted(phrases.items(), key=lambda x: -len(x[0])):
        t = re.sub(rf"(?<![A-Za-z]){re.escape(low)}(?![A-Za-z])", name, t, flags=re.I)
    t = re.sub(r"\btitle (\d+)\b", r"Title \1", t)
    t = re.sub(r"\barticle ([ivx]+|\d+)\b", lambda m: "Article " + m.group(1).upper(), t, flags=re.I)
    t = re.sub(r"\bnew castle\b", "New Castle", t)
    t = re.sub(r"\b(New Castle|Kent|Sussex) county\b", r"\1 County", t)
    t = re.sub(r"\bDelaware (code|constitution)\b", lambda m: "Delaware " + m.group(1).title(), t)
    t = re.sub(r"\b(general assembly|transportation trust fund|Delaware transportation authority)\b", lambda m: m.group(1).title(), t)
    return t[:1].upper() + t[1:]


AMEND_KIND = re.compile(r"^\W*AN ACT (PROPOSING|CONCURRING IN)\b", re.I)


def relating(long_title):
    """The long title's subject: "... RELATING TO THEFT." -> "THEFT"; "... IN REGARD TO X" / "... CONCERNING X" too."""
    m = re.search(r"\b(?:RELATING TO|RELATIVE TO|IN REGARD TO|REGARDING|CONCERNING|WITH RESPECT TO)\s+(.+?)\s*\.?\s*$", text(long_title), re.I | re.S)
    return m.group(1) if m else ""


def titled(row, amendment=None):
    """A short title from the long one: its subject ("AN ACT TO AMEND TITLE 11 ... RELATING TO THEFT." -> "Theft"); else
    the act's own words ("AN ACT MAKING A ONE-TIME SUPPLEMENTAL APPROPRIATION ..." -> "Making a one-time supplemental
    appropriation ..."; "AN ACT TO AMEND THE CHARTER OF THE TOWN OF MILLVILLE" -> "The charter of the Town of
    Millville"). Constitutional amendments say so, and which passage: "Constitutional amendment (first passage): voting"."""
    long_ = text(row.get("LongTitle"))
    syn, short = row.get("Synopsis") or "", text(row.get("ShortTitle"))
    rel = relating(long_)
    named = re.sub(r"\s+", " ", short.replace("’", "'")).strip()
    if named and "/" not in named and re.search(r"\b(?:Act|Bill|Budget|Charter Change)\b", named) and not amendment:
        t = named
    elif rel:
        t = recase(rel, syn, short)
        t = re.sub(r"^(?:The|A|An) (?=[a-z])", lambda m: m.group(0), t)
    else:
        body = re.sub(r"^\W*AN ACT\s*,?\s*", "", long_, flags=re.I)
        body = re.split(r";", body)[0]
        m = re.match(r"TO AMEND (?:THE )?(CHARTER OF .+)$", body, re.I)
        if m:
            body = "THE " + m.group(1)
        else:
            body = re.sub(r"^TO ", "", body, flags=re.I)
        t = recase(body, syn, short)
    t = re.sub(r"\b(Town|City|Village) of\b", lambda m: m.group(1) + " of", t)
    t = re.sub(r"\bthe (town|city|village) of ([A-Z])", lambda m: f"the {m.group(1).title()} of {m.group(2)}", t)
    if amendment:
        t = f"Constitutional amendment ({'second' if amendment == 'CONCURRING IN' else 'first'} passage): {t[:1].lower() + t[1:] if not re.match(r'[A-Z]{2}|Delaware|Article', t) else t}"
    if len(t) > 180:
        cut = t[:180].rsplit(",", 1)[0] if "," in t[:180] else t[:180].rsplit(" ", 1)[0]
        t = cut + " …"
    return t


def amendment_kind(row):
    """"PROPOSING" (first passage) or "CONCURRING IN" (second) for a constitutional amendment, else None. Not an act
    about the procedure for amendments (HB 321 of 2025)."""
    long_ = text(row.get("LongTitle"))
    m = AMEND_KIND.match(long_)
    if m and re.search(r"\bCONSTITUTION\b", long_[:300], re.I):
        return m.group(1).upper()
    return None


def synopsis(row, detail):
    """The bill's synopsis (written with it and printed at its end; not part of the law), as paragraphs."""
    s = (row.get("Synopsis") or (detail.get("fields") or {}).get("Original Synopsis") or "").replace("\r", "")
    paras = [text(p) for p in re.split(r"\n+", s)]
    return "\n".join(p for p in paras if p)


def sim_text(row):
    t = text(row.get("LongTitle"))
    t = re.sub(r"\b(?:TITLES?|CHAPTERS?|SECTIONS?|ARTICLES?)\s+[\dIVX§.,\s]+(?:AND\s+[\dIVX§.]+)?", " ", t, flags=re.I)
    t = re.sub(r"\bAN ACT\b|\bTO AMEND\b|\bOF THE DELAWARE CODE\b|\bRELATING TO\b", " ", t, flags=re.I)
    return text(t).lower()


# ---- the history ---------------------------------------------------------------------------------------------------

PREFIX = re.compile(r"^(?P<sub>[HS]S \d+ for [HS]B \d+) - (?P<rest>.*)$")
AMEND = re.compile(r"^Amendment (?P<am>[HS]A \d+(?: to [HS]A \d+)?) to (?P<to>.+?) - (?P<rest>.*)$")
TALLY = re.compile(r"Votes?:\s*(.*?)(?:\.\s*Reason Taken:\s*(.*))?$")
HOUSE_AT_END = re.compile(r"\b(?:in|By) (House|Senate)\b")


def tally(t):
    """"Votes: 39 YES 1 NO 1 ABSENT" -> {"YES": 39, "NO": 1, "ABSENT": 1}."""
    m = TALLY.search(t)
    part = m.group(1) if m else t  # "Veto Override Passed in House.  40 YES 1 ABSENT" has no "Votes:"
    return {k: int(n) for n, k in re.findall(r"(\d+) (YES|NO|NOT VOTING|ABSENT|VACANT|CONFLICT)\b", part)}


def tally_words(tl):
    return f"{tl.get('YES', 0)}-{tl.get('NO', 0)}"


def committee_name(c):
    """"Sunset Committee (Policy Analysis & Government Accountability)" stays; a stray closing parenthesis goes."""
    c = text(c)
    while c.count(")") > c.count("("):
        c = c[:c.rindex(")")] + c[c.rindex(")") + 1:]
    c = re.sub(r"^Sunset Committee \(", "Sunset (", c)  # "Sunset Committee (Policy Analysis ...)" -> "Sunset (...)"
    return re.sub(r"\s+Committee$", "", c).strip()


def report_counts(t):
    out = {"fav": 0, "merits": 0, "unfav": 0}
    for n, k in re.findall(r"(\d+) (Favorable|On Its Merits|Unfavorable)", t):
        out[{"Favorable": "fav", "On Its Merits": "merits", "Unfavorable": "unfav"}[k]] += int(n)
    return out


def line_key(t):
    """What a history line says, to find the same line in a bill's and its substitute's histories: the event after the
    last " - ", and for a vote its house, yeas and nays (one copy can count one more member not voting: HB 168 of 2023-24)."""
    e = t.split(" - ")[-1].strip(" -")
    am = re.search(r"\bAmendment ([HS]A \d+)\b", t)
    if am or re.search(r" - +- ", t):
        return f"amendment {am.group(1) if am else ''}: {e}"
    m = re.match(r"(Passed|Defeated) By (House|Senate)\. Votes?: (\d+) YES(?: (\d+) NO)?", e)
    return f"{m.group(1)} {m.group(2)} {m.group(3)}-{m.group(4) or 0}" if m else e


def load_session(session):
    """Read one General Assembly's bills and return (records, bill number -> record index, fetched time, delegation)."""
    rows = load(session, "list")
    subs = {}
    for r in rows:
        if r.get("LegislationTypeId") == 6:
            parent = number(r.get("SubstituteParentLegislationDisplayCode"))
            if parent:
                subs.setdefault(parent, []).append(r)
    seat = seats(session)
    parties = _PARTIES.setdefault(session, {})
    for m in load(session, "members"):
        h = CHAMBER.get(m.get("ChamberId"))
        if h and party_of(m) in ("D", "R"):
            parties[(h, full_name(m))] = party_of(m)
    path = os.path.join(folder(session), "list.json")
    fetched = datetime.fromtimestamp(os.path.getmtime(path), ZoneInfo(P.TIMEZONE)).strftime("%Y-%m-%d %H:%M") if os.path.exists(path) else ""
    recs, index, texts = [], {}, {}
    base = sorted((r for r in rows if r.get("LegislationTypeId") == 1 and number(r.get("LegislationNumber") or r.get("LegislationDisplayCode", "").split(" w/")[0])),
                  key=lambda r: (r.get("ChamberId") != 2, r.get("BaseLegislationNumberOrdering") or 0))
    for r in base:
        p = number(re.sub(r"\s*(?:w/|-[HS]A).*$", "", text(r.get("LegislationNumber") or r.get("LegislationDisplayCode"))))
        if not p or p in index:
            continue
        rec, what = record(session, r, p, subs.get(p, []), seat)
        index[p] = len(recs)
        recs.append(rec)
        if what:
            texts[p] = {"statement": what, "label": "From the bill's synopsis, written by its drafters and filed with it (not part of the law)."}
    json.dump(texts, open(os.path.join(P.DATA, f"texts_{session}.json"), "w"), ensure_ascii=False)
    return recs, index, fetched, {"SENATE": [], "ASSEMBLY": []}


def record(session, row, p, sub_rows, seat):
    origin = "H" if p.startswith("H") else "S"
    other = "S" if origin == "H" else "H"
    f = bill_file(session, p) or {}
    # The substitute that holds the bill's place now: the one not itself replaced (SS 2 for SB 100 after SS 1).
    sub_rows = sorted(sub_rows, key=lambda r: r.get("SubstituteLegislationNumberOrdering") or 0)
    live_sub = next((r for r in reversed(sub_rows) if r.get("StatusName") != "Lieu/Substituted"), sub_rows[-1] if sub_rows else None)
    sub_files = [(r, bill_file(session, sub_key(r)) or {}) for r in sub_rows]
    cur_row = live_sub or row
    cur_file = next((sf for r, sf in sub_files if r is live_sub), None) if live_sub else f
    cur_file = cur_file or {}
    detail = cur_file.get("detail") or {}
    amend_kind = amendment_kind(cur_row) or amendment_kind(row)
    amendment = bool(amend_kind)

    # Every action line of the bill and its substitutes, each once. The original's history copies its substitutes'
    # lines ("HS 1 for HB 449 - Passed By House ..."), but a substitute's own history is fuller (its amendments by name)
    # and dates the governor's action as its status does (HS 2 for HB 168 of 2023-24: signed 9/30/24, copied 10/2/24): the
    # substitute's own lines are used, and the original's copies only for a substitute whose page wasn't read.
    label_of = lambda r: re.sub(r"\s+(?:w/|-[HS]A).*$", "", text(r.get("LegislationDisplayCode")))
    own = {label_of(r) for r, sf in sub_files if sf.get("actions")}
    acts, have = [], set()

    def add(d, i, t):
        k = (d, line_key(t))
        if k not in have:
            have.add(k)
            acts.append((d, i, t))
    for r, sf in sub_files:
        for a in sf.get("actions") or []:
            t, d = text(a.get("ActionDescription")), day(a.get("OccuredAtDateTime"))
            if re.match(r"(?:was introduced and )?adopted in lieu of", t, re.I):
                continue
            m = PREFIX.match(t)
            if m and m.group("sub") in own and m.group("sub") != label_of(r):
                continue  # another substitute's line, copied (SS 1 for SB 278 carries SS 2's)
            add(d, a.get("LegislationActionLogId") or 0, t if m else f"{label_of(r)} - {t}")
    for a in f.get("actions") or []:
        t, d = text(a.get("ActionDescription")), day(a.get("OccuredAtDateTime"))
        m = PREFIX.match(t)
        if m and m.group("sub") in own:
            continue
        add(d, a.get("LegislationActionLogId") or 0, t)
    # The same line twice on one day ("Reported Out of Committee ..." entered twice) is one step.
    acts.sort(key=lambda a: (a[0], a[1]))
    dedup, last = [], set()
    for d, i, t in acts:
        if (d, t) in last:
            continue
        last.add((d, t))
        dedup.append((d, i, t))
    acts = dedup

    steps = []  # (date, house or "G", wording, kind)
    passed, failed = {}, set()  # house -> index of its last passage
    amended_after = {}  # house -> index of the last amendment it adopted
    where_h, place, comm, first_ref, first_report = origin, "committee", None, None, None
    refs, reports, tabled, released_fail = [], [], False, False
    stricken = signed = vetoed = no_sign = override_done = item = enacted = False
    last_vote = {}
    overrides, subs_named = set(), set()
    vote_steps = []  # (step index, house, tally, date, ok) for matching roll calls
    for d, _, t0 in acts:
        t = t0
        m = PREFIX.match(t)
        sub_label = None
        if m:
            sub_label, t = m.group("sub"), m.group("rest")
        am = AMEND.match(t)
        blank_am = t.startswith(" - ") or t.startswith("- ")
        if am or blank_am:
            label = am.group("am") if am else "an amendment"
            rest = am.group("rest") if am else re.sub(r"^\s*-\s*", "", t)
            hm = HOUSE_AT_END.search(rest)
            h = CHAMBER.get(hm.group(1)) if hm else (label[0] if am else where_h)
            name = f"Amendment {label}" if am else "An amendment"
            if re.match(r"Introduced and Placed With Bill", rest):
                steps.append((d, h, f"{name} filed", "amendfile"))
            elif re.match(r"Passed", rest):
                amended_after[h] = len(steps)
                tl = tally(rest)
                steps.append((d, h, f"{name} adopted" + (f", {tally_words(tl)}" if tl else " by voice vote"), "amend"))
            elif re.match(r"Defeated", rest):
                tl = tally(rest)
                steps.append((d, h, f"{name} failed" + (f", {tally_words(tl)}" if tl else ""), "amendfail"))
            elif re.match(r"Stricken", rest):
                steps.append((d, h, f"{name} withdrawn", "amendfile"))
            else:
                steps.append((d, h, f"{name}: {rest}", "amendfile"))
            continue
        hm = HOUSE_AT_END.search(t)
        h = CHAMBER.get(hm.group(1)) if hm else ""
        H = HOUSE.get(h, "")
        mm = re.match(r"(Introduced and )?(Re-)?Assigned to (.+?) Committee in (House|Senate)$", t)
        if mm:
            c = committee_name(mm.group(3))
            h = CHAMBER[mm.group(4)]
            if mm.group(1) and not any(s[3] == "intro" for s in steps):
                steps.append((d, h, "Introduced", "intro"))
            comm, place, where_h = c, "committee", h
            refs.append((h, c))
            if first_ref is None and h == origin:
                first_ref = c
            steps.append((d, h, f"REFERRED TO {c.upper()}", "ref"))
            continue
        mm = re.match(r"Reported Out of Committee \((.+)\) in (House|Senate) with (.*)$", t)
        if mm:
            c = committee_name(mm.group(1))
            h = CHAMBER[mm.group(2)]
            n = report_counts(mm.group(3))
            if h == origin and first_report is None:
                first_report = True
            reports.append((d, h, c, n))
            parts = [f"{n['fav']} favorable" if n["fav"] else "", f"{n['merits']} on its merits" if n["merits"] else "",
                     f"{n['unfav']} unfavorable" if n["unfav"] else ""]
            steps.append((d, h, "REPORTED", "reported"))
            steps.append((d, h, f"Released by the {c} Committee: {', '.join(x for x in parts if x)}", "report"))
            place, where_h, tabled = "floor", h, False
            continue
        if t == "Not Worked in Committee":
            steps.append((d, where_h, "On the committee's agenda, but not taken up", "notworked"))
            continue
        if t == "Tabled in Committee":
            tabled = True
            steps.append((d, where_h, "Tabled in committee", "tabled"))
            continue
        if t == "Lifted From Table in Committee":
            tabled = False
            steps.append((d, where_h, "Taken off the table in committee", "untabled"))
            continue
        if t in ("Motion to Release Failed", "Not Enough Signatures to Release"):
            released_fail = True
            steps.append((d, where_h, "Not released: too few committee members signed" if t.startswith("Not Enough") else "A motion to release it from committee failed", "relfail"))
            continue
        if re.match(r"(?:was introduced and )?adopted in lieu of", t, re.I):
            continue
        mm = re.match(r"Substituted in (House|Senate) by (.+)$", t)
        if mm:
            label = text(mm.group(2))
            if label not in subs_named:
                subs_named.add(label)
                steps.append((d, CHAMBER[mm.group(1)], f"Replaced by a substitute bill, {label}", "substituted"))
            continue
        mm = re.match(r"(Passed|Defeated) By (House|Senate)\. Votes?:", t)
        if mm and "Reason Taken" not in t:
            h = CHAMBER[mm.group(2)]
            H = HOUSE[h]
            tl = tally(t)
            ok = mm.group(1) == "Passed"
            last_vote[h] = "pass" if ok else "fail"
            vote_steps.append((len(steps), h, tl, d, ok))
            if ok:
                first = h not in passed
                passed[h] = len(steps)
                failed.discard(h)
                if h == origin and first:
                    place, where_h, comm = "committee", other, None
                elif h == other:
                    place, where_h = "desk", origin
                steps.append((d, h, f"PASSED {H.upper()}", "pass"))
                steps.append((d, h, f"The {H} vote: {tally_words(tl)}", "tally"))
            else:
                failed.add(h)
                steps.append((d, h, f"Failed in the {H}, {tally_words(tl)}", "fail"))
            continue
        if "Reason Taken" in t or t.startswith("Motion to Suspend Rules"):
            reason = re.search(r"Reason Taken:\s*(.*)$", t)
            ok = not re.search(r"Defeated", t)
            r_ = text(reason.group(1)) if reason else "a motion to suspend the rules"
            r_ = r_[:1].lower() + r_[1:]
            if re.match(r"Tabled in", t):
                steps.append((d, h, f"Laid on the table by a vote of the {H}", "table"))
            else:
                steps.append((d, h, f"The {H} {'agreed to' if ok else 'rejected'} {r_.rstrip('.')}", "motion"))
            continue
        if re.match(r"Suspension of Rules in", t):
            place, where_h = "floor", h
            steps.append((d, h, f"The {H} suspended its rules to take it up", "suspend"))
            continue
        if re.match(r"Laid On Table in", t):
            steps.append((d, h, f"Laid on the table in the {H}", "table"))
            continue
        if re.match(r"Lifted From Table in", t):
            steps.append((d, h, f"Taken from the table in the {H}", "untable"))
            continue
        if re.match(r"Stricken in", t):
            stricken = True
            steps.append((d, h, f"Stricken (withdrawn) in the {H}", "stricken"))
            continue
        mm = re.match(r"Returned to the (House|Senate)", t)
        if mm:
            steps.append((d, CHAMBER[mm.group(1)], f"Returned to the {mm.group(1)} at its request", "returned"))
            continue
        if re.match(r"Restored in", t):
            steps.append((d, h, f"Restored to the {H}'s agenda", "restored"))
            continue
        if re.match(r"Roll Call Rescinded in|Reconsidered in", t):
            # The house undid its last vote: a passage (HB 59 of 2025-26: the House asked for it back from the Senate,
            # then passed it again with another amendment) or a defeat (HB 140 of 2023-24, reconsidered and passed).
            if last_vote.get(h) == "pass":
                passed.pop(h, None)
            elif last_vote.get(h) == "fail":
                failed.discard(h)
            last_vote.pop(h, None)
            place, where_h = "floor", h
            if not (steps and steps[-1][3] == "rescind" and steps[-1][1] == h and steps[-1][0] == d):
                steps.append((d, h, f"The {H} voted to reconsider its vote", "rescind"))
            continue
        if t == "Enacted into Law":
            enacted = True
            steps.append((d, "G", "Became law", "lawnote"))
            continue
        if re.search(r"Assigned to Ready List", t):
            place, where_h = "floor", h or where_h
            steps.append((d, h or where_h, "Placed on the ready list", "ready"))
            continue
        mm = re.match(r"Vote type changed from .*? to (.+?) by amendment", t)
        if mm:
            steps.append((d, h or where_h, f"An amendment raised the vote it needs to {mm.group(1).replace('Majority', 'majority')}", "other"))
            continue
        if re.search(r"Motion to Table", t):
            ok = not re.search(r"Failed|Defeated", t)
            steps.append((d, h, f"A motion to lay it on the table {'passed' if ok else 'failed'}", "motion"))
            continue
        if re.match(r"Signed by Governor", t):
            signed = True
            steps.append((d, "G", "Signed by the governor", "signed"))
            continue
        if re.match(r"Enact w/o Sign", t):
            no_sign = True
            steps.append((d, "G", "Became law without the governor's signature", "nosign"))
            continue
        if re.match(r"Vetoed by Governor", t):
            vetoed = True
            steps.append((d, "G", "VETOED", "vetoed"))
            continue
        mm = re.match(r"Line-Item Veto(?: - See Governor's Advisory #(\d+))?", t)
        if mm:
            item = True
            steps.append((d, "G", "The governor vetoed items of it (line-item veto)" + (f"; Governor's Advisory #{mm.group(1)}" if mm.group(1) else ""), "itemveto"))
            continue
        mm = re.match(r"Veto Override (?:Passed|Failed|Defeated) in (?:the )?(House|Senate)", t, re.I)
        if mm:
            hh = CHAMBER[mm.group(1)]
            ok = not re.search(r"Defeated|Failed|Sustained", t, re.I)
            if ok:
                overrides.add(hh)
            tl = tally(t)
            vote_steps.append((len(steps), hh, tl, d, None))
            steps.append((d, hh, f"The {HOUSE[hh]} voted to override the veto" + (f", {tally_words(tl)}" if tl else "") if ok else
                          f"The {HOUSE[hh]} failed to override the veto" + (f", {tally_words(tl)}" if tl else ""), "override"))
            continue
        steps.append((d, h or "G", t, "other"))
    steps.sort(key=lambda s: s[0])  # stable: the site's order within a day
    status_day = day(cur_row.get("LegislationStatusDateTime")) or f"{session}-01-01"

    def end(kinds=None):
        return max((s[0] for s in steps if s[0] and (kinds is None or s[3] in kinds)), default=status_day)

    # Laws and vetoes from the bill page's status and chapter, which agree with the history except where the history
    # stops short.
    status = text(cur_row.get("StatusName"))
    vol_ch = text((detail.get("fields") or {}).get("Volume:Chapter"))
    chm = re.fullmatch(r"(\d+)\s*:\s*(\d+)", vol_ch)
    if status == "Veto Overridden":
        overrides |= {"H", "S"}
    overridden = overrides >= {"H", "S"}
    law = signed or no_sign or overridden or enacted
    if not law and status in ("Signed", "Enact w/o Sign"):
        law = True
        steps.append((status_day, "G", "Signed by the governor" if status == "Signed" else "Became law without the governor's signature", "signed"))
    if status == "Vetoed":
        vetoed = True

    # Passed both houses: both passed, and the first house passed it again after any amendment the second adopted.
    def after(h, i):
        return passed.get(h, -1) > i
    both = origin in passed and other in passed
    if both:
        o_i, x_i = passed[origin], passed[other]
        if x_i > o_i and amended_after.get(other, -1) > o_i:
            both = False  # the second house changed it; the first hasn't passed the changed bill
    both = both or law or vetoed
    if amendment:
        stage = 3 if both or status in ("Approved", "Passed") and len(passed) == 2 else 2 if passed else None
    elif law:
        stage = 5
    elif vetoed:
        stage = 6
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
        stage = 1 if (place == "floor" or origin in failed) and not stricken else 0
    if stage == 5 and overridden and not any(s[3] == "lawnote" for s in steps):
        steps.append((end(), "G", "Became law over the governor's veto", "lawnote"))
    chapter = int(chm.group(2)) if chm and stage == 5 else None
    if chapter:
        steps.append((end(("signed", "nosign", "lawnote", "override")), "G", f"CHAPTER {chapter}, VOLUME {chm.group(1)}", "chapter"))
        steps.sort(key=lambda s: s[0])

    comm_now = comm if place == "committee" and stage in (0, 2) and not stricken else None
    title = titled(cur_row, amend_kind)
    long_title = text(cur_row.get("LongTitle"))
    topics = list(dict.fromkeys((["const"] if amendment else []) +
                                [P.COMMITTEE_TOPICS[c] for _, c in refs if c in P.COMMITTEE_TOPICS] +
                                [k for k in P.TOPIC_WORDS if P.TOPIC_WORDS[k].search(title + " " + relating(long_title))]))
    first_released = any(h == origin for _, h, _, _ in reports)
    fate = ("passed" if first_released or passed else "held" if tabled else "defeated" if released_fail else "none")

    # Sponsors in order: the primary sponsor, then the additional sponsors, then co-sponsors, as full names.
    sp = detail.get("sponsors") or {}
    names, primes = [], 0
    for group in ("primary", "additional", "cosponsors"):
        for x in sp.get(group) or []:
            n = sponsor_name(session, x, origin if group == "primary" else None)
            if n and n not in names:
                names.append(n)
                primes += group == "primary"
    if not names and cur_row.get("Sponsor"):
        names = [sponsor_name(session, {"name": cur_row["Sponsor"], "personId": cur_row.get("SponsorPersonId")}, origin)]
    sponsor = names[0] if names else "—"
    cos = names[1:]
    where = HOUSE.get(where_h, HOUSE[origin])
    if stage == 0:
        desc = "Stricken" if stricken else "Tabled in committee" if tabled else f"In {where} committee"
    elif stage == 1:
        desc = "Stricken" if stricken else f"Failed in the {HOUSE[origin]}" if origin in failed else f"On the {where} floor"
    else:
        desc = {2: f"Passed the {HOUSE[origin] if origin in passed_h else HOUSE[other]}" + (f"; failed in the {HOUSE[other]}" if other in failed else ""),
                3: "Passed both houses", 4: "On the governor's desk", 5: "Became law", 6: "Vetoed"}[stage]

    def dates(test, mode="last"):
        ds = sorted({s[0] for s in steps if test(s) and s[0]})
        return {"first": ds[0], "last": ds[-1], "all": ";".join(ds)}[mode] if ds else ""

    votes = floor_votes(session, f, sub_files, steps, vote_steps, seat)
    for d, h, c, n in reports:
        votes.append([h, "C", c, d, n["fav"] + n["merits"], n["unfav"], []])
    votes.sort(key=lambda v: v[3])
    action_dates = [s[0] for s in steps if s[0]]
    what = synopsis(cur_row, detail)
    budget = bool(re.search(r"\b(?:BUDGET|APPROPRIATION|BOND AND CAPITAL IMPROVEMENTS|GRANTS-IN-AID)\b", long_title[:160], re.I)) and \
        re.match(r"^\W*AN ACT (?:MAKING|TO MAKE|APPROPRIATING|A BOND|AUTHORIZING)|^\W*A BOND|^\W*AN ACT MAKING", long_title, re.I) is not None
    link_id = cur_file.get("id") or cur_row.get("LegislationId") or f.get("id") or row.get("LegislationId")
    rec = {
        "nums": [p], "base": [p], "prev": earlier(session, row, p),
        "title": title, "summary": recase(long_title, cur_row.get("Synopsis") or "", text(cur_row.get("ShortTitle"))) + ".",
        "act": "", "lawCode": "", "law": None, "laws": [],
        "comms": sorted({f"{h} · {c}" for h, c in refs}), "topics": topics, "places": [], "narrow": P.narrow_kind(long_title),
        "commFate": fate, "mainTopic": topics[0] if topics else "", "local": "local" in topics,
        "senDeleg": False, "asmDeleg": False, "budget": budget,
        "passedS": "S" in passed_h, "passedA": "H" in passed_h, "program": None,
        "stage": stage, "passedIn": (HOUSE[origin] if origin in passed_h else HOUSE[other]) if stage == 2 else None,
        "chapter": chapter, "veto": None, "memo": "", "vetoMemo": None,
        # (Not a constitutional amendment's synopsis: its stock sentences about the first and second "leg" match each other.)
        "simText": f"{title} {sim_text(cur_row)} {'' if amendment else what[:600]}",
        "comm": comm_now if stage == 0 else None,
        "first": min(action_dates, default=day(row.get("IntroductionDateTime")) or f"{session}-01-01"),
        "last": max(action_dates, default=day(row.get("IntroductionDateTime")) or f"{session}-01-01"),
        "cosp": len(cos),
        "keyDates": [
            dates(lambda s: s[3] == "reported", "first"),
            dates(lambda s: s[2] == "PASSED SENATE", "all"),
            dates(lambda s: s[2] == "PASSED HOUSE", "all"),
            "",
            "",
            dates(lambda s: s[3] in ("signed", "nosign", "lawnote")) if stage == 5 else "",
            dates(lambda s: s[3] == "vetoed"),
        ],
        "votes": votes, "firstComms": [(origin, first_ref, bool(first_released) or bool(passed))] if first_ref else [],
        "vers": [{"p": p, "sponsor": sponsor, "district": 0, "cosponsors": cos, "primes": max(1, primes), "cosp": len(cos),
                  "statusDesc": desc, "committee": comm_now, "link": f"https://legis.delaware.gov/BillDetail?LegislationId={link_id}" if link_id else "",
                  "sub": text(live_sub.get("LegislationDisplayCode")).split(" w/")[0].split(" -")[0] if live_sub else "",
                  "actions": [[s[0], s[2]] for s in steps]}],
    }
    if item and stage == 5:
        rec["vers"][0]["itemVeto"] = True
    if amendment:
        rec["amendLeg"] = 2 if amend_kind == "CONCURRING IN" else 1
    if not f:
        rec["missing"] = True
    return rec, what


def floor_votes(session, f, sub_files, steps, vote_steps, seat):
    """The bill's own floor roll calls (its passage or defeat, and veto overrides), member by member: "N" no, "A" absent,
    "B" not voting or a declared conflict. Each passage line is matched to a roll call of the bill (or its substitute) in
    the same house on the same day with the same yeas and nays."""
    rolls = []
    for src in [f] + [sf for _, sf in sub_files]:
        for r in src.get("rollCalls") or []:
            if r.get("RollCallId") and r["RollCallId"] not in {x["RollCallId"] for x in rolls}:
                rolls.append(r)
    out, used = [], set()
    for i, h, tl, d, ok in vote_steps:
        cands = [r for r in rolls if r["RollCallId"] not in used and CHAMBER.get(r.get("ChamberName")) == h
                 and (r.get("YesTotal"), r.get("NoTotal")) == (tl.get("YES", 0), tl.get("NO", 0))
                 ]
        cands.sort(key=lambda r: r.get("RollCallResultTypeName") == "Rescinded")
        same_day = [r for r in cands if day(r.get("TakenAtDateTime")) == d]
        r = (same_day or cands or [None])[0]
        v = vote_file(session, r["RollCallId"]) if r else None
        listed = []
        yes, no = tl.get("YES", 0), tl.get("NO", 0)
        if v:
            used.add(r["RollCallId"])
            yes, no = int(v.get("YesVoteCount") or 0), int(v.get("NoVoteCount") or 0)
            for x in v.get("AssemblyMemberVotes") or []:
                code = {"N": "N", "A": "A", "NV": "B", "C": "B"}.get(x.get("SelectVoteTypeCode"))
                if not code:
                    continue
                s = text(x.get("ShortName"))
                listed.append([seat.get((h, s)) or f"{h}?{s.split('. ')[-1]}", code])
        elif r is None and not tl:
            continue
        out.append([h, "F", None, d, yes, no, listed])
    return out


# ---- earlier General Assemblies ------------------------------------------------------------------------------------

_KEYS = {}


def _prime(row):
    return text(row.get("Sponsor"))


def _key(row):
    return text(relating(text(row.get("LongTitle"))) or re.sub(r"^\W*AN ACT\s*", "", text(row.get("LongTitle")))).lower().rstrip(". ")


def _keys(session):
    """An Assembly's bills that didn't become law (and constitutional amendments that passed, for their second
    passage): subject -> [(bill number, prime sponsor, amendment kind)]."""
    if session not in _KEYS:
        out = {}
        for r in load(session, "list"):
            if r.get("LegislationTypeId") not in (1, 6):
                continue
            p = number(r.get("SubstituteParentLegislationDisplayCode") if r.get("LegislationTypeId") == 6 else r.get("LegislationNumber"))
            if not p:
                continue
            kind = amendment_kind(r)
            if r.get("StatusName") in ("Signed", "Enact w/o Sign", "Veto Overridden") and not kind:
                continue
            k = _key(r)
            if (p, _prime(r), kind) not in out.get(k, []):
                out.setdefault(k, []).append((p, _prime(r), kind))
        _KEYS[session] = out
    return _KEYS[session]


def earlier(session, row, p):
    """The same bill in the General Assembly before: the same subject with the same prime sponsor, or a subject only one
    bill has in each; a second passage of a constitutional amendment ("CONCURRING IN") to the first passage of the same
    subject. Never budgets or bills that became law."""
    out = set()
    y = session - 2
    if y not in sessions():
        return out
    k = _key(row)
    kind = amendment_kind(row)
    if len(k.split()) < 2 or re.search(r"\bappropriation|budget|bond and capital|grants-in-aid", k):
        return out
    old = _keys(y).get(k, [])
    if kind == "CONCURRING IN":
        firsts = [n for n, _, kd in old if kd == "PROPOSING"]
        if firsts:
            out.add((y, firsts[0]))
        return out
    old = [x for x in old if x[2] != "CONCURRING IN"]
    same = [n for n, sp, _ in old if sp and sp == _prime(row)]
    if same:
        out.add((y, same[0]))
    elif len({n for n, _, _ in old}) == 1 and len({n for n, _, _ in _keys(session).get(k, [])}) == 1 and len(k.split()) >= 3:
        out.add((y, old[0][0]))
    return out


def parties(session, recs):
    if session not in _PARTIES:
        load_session(session)
    return {k: v for k, v in _PARTIES.get(session, {}).items() if v in ("D", "R")}
