"""Hawaii's bills (downloaded by states/hi/fetch.py from Open States, and first from its bulk files by
states/openstates_bulk.py; the Legislature's own site turns automated requests away) in the shape build_data.py reads.

A page is a two-year Legislature, named by its first year (2025 is the 33rd Legislature, 2025-26): bill numbers run
through both years, and a bill not passed in the first year carries over to the second where it stands. Open States
keeps a session per year and repeats a carried-over bill in the second year with its whole history ("Carried over to
2026 Regular Session."), so each bill is read from the second year's folder when it's there, else the first's. House and
Senate bills (HB, SB); Hawaii proposes constitutional amendments as bills ("PROPOSING AN AMENDMENT TO ARTICLE ..."),
tagged "const": two-thirds of each house's members on final reading in one session, or a majority in two successive
sessions, then the voters at the next general election; the governor gets notice but has no veto (Art. XVII, sec. 3).

Each history line comes from one house's journal (Open States' organization: upper or lower; the governor's actions
appear in both), with its date; lines are put in order by date and Open States' order within a day. The history:
- "Introduced and Pass First Reading." / "Introduced." ; "Referred to HLT, CPC, FIN, referral sheet 1" (one after
  another) or "Referred to AEN/TCA, JDC/WAM." (AEN and TCA jointly, then JDC and WAM jointly); "Re-Referred to ..." (the
  second year's committees, or a change). Committees are named by code (P.COMMITTEES, by year).
- A committee's decision: "The committee(s) on AEN recommend(s) that the measure be PASSED, WITH AMENDMENTS. The votes in
  AEN were as follows: 4 Aye(s): Senator(s) Awa; Aye(s) with reservations: Senator(s) Gabbard, ...; 0 No(es): none; and 1
  Excused: Senator(s) DeCoite." (member by member; the count of ayes includes those with reservations); "... be
  deferred" / "deferred the measure." (set aside: most bills that die are never heard, or deferred); "... be HELD".
  Committees don't vote bills down on the record. Then "Reported from AEN (Stand. Com. Rep. No. 570) with recommendation
  of passage on Second Reading ... and referral to JDC" (the report), and the floor's second reading, which sends it on
  ("Report adopted; Passed Second Reading, as amended (SD 1) and referred to JDC.").
- "Passed Third Reading ..." is a house passing it. The House's line names those voting no and excused ("with
  Representative(s) Garcia voting aye with reservations; Representative(s) Amato voting no (2) and Representative(s)
  Ward excused (1)"); the Senate's gives counts and names ("Ayes, 24; ... Noes, 1 (Senator(s) Awa). Excused, 0").
- The second house passing it unamended sends it to the governor ("Returned from Senate (Sen. Com. No. 828)." /
  "Enrolled to Governor."). Passing it "as amended (SD 1)" sends it back: the first house agrees ("House agrees to Senate
  amendment(s).") and passes it on Final Reading, or disagrees and a conference committee reports a "CD 1" that both
  houses pass on Final Reading.
- "Transmitted to Governor." (House bills) / "Enrolled to Governor." (Senate bills); "Notice of intent to veto (Gov. Msg.
  No. 1301)"; "Act 250, on 06/30/2025 (Gov. Msg. No. 1353)." (signed: a law), "Became law without the Governor's
  signature, Act 245, ..."; "Vetoed on 07/03/2025 - Returned from the Governor without approval"; "Vetoed ..., line-item
  appropriations veto" (the budget: items vetoed, then signed as an Act); "Veto overridden - 2/3's vote" in each house,
  then "Act 029, 5/4/2023, veto override." The governor's lines carry their own date ("on 07/03/2023"), which is used.
Laws are numbered each year: "Act 250 of 2025" (chapter "250 of 2025").

Votes: committee votes and floor passages member by member, from the history lines' own lists (Open States' vote
records split "Lee, M." into two names, and have no House floor votes). The House's floor lines don't give the ayes:
they're the House's 51 seats less those voting no and excused. Names are surnames ("Lee, M." where two share one), tied
to today's members (data/hi/openstates_people.csv) within the house; for 2023-24 only names that also vote in the current
Legislature, so a new member with a departed one's surname isn't credited with the old votes; the rest stay names
("H?Saiki").

There are no plain summaries beyond each bill's description (Open States' abstract: the Legislature's one-paragraph
description of the current version, "Appropriates funds ... (CD1)"), which is the bill's summary; the title is its first
sentence (official titles are "RELATING TO TAXATION."), so "What it does" isn't shown.
"""
import csv, glob, json, os, re, sys, unicodedata
from collections import Counter, defaultdict
from datetime import date, datetime
from zoneinfo import ZoneInfo

from states.hi import profile as P
from states.undated import settle
from states.lead_first import repeats

HOUSE = {"S": "Senate", "H": "House"}
OTHER = {"S": "H", "H": "S"}
ORG = {"upper": "S", "lower": "H"}
KEEP = re.compile(r"(HB|SB)\d+$")
CURRENT = P.session_of(datetime.now(ZoneInfo(P.TIMEZONE)).year)
_PARTIES, _CACHE = {}, {}


def load(path, default=None):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def folder(year):
    return os.path.join(P.DATA, str(year), "bills")


def sessions():
    """Two-year Legislatures with a first copy of their first year (a later year's first copy may still be coming)."""
    if "sessions" in _CACHE:
        return _CACHE["sessions"]
    out = set()
    for f in glob.glob(os.path.join(P.DATA, "[0-9]" * 4)):
        y = int(os.path.basename(f))
        n = len(glob.glob(os.path.join(f, "bills", "*.json")))
        # A bulk import's partial first copy shows once it's big; a new Legislature's first year as soon as fetch.py's
        # first pass over it is whole and has a bill (January: a few hundred bills a day).
        if n > 500 or (n and (load(os.path.join(f, "state.json")) or {}).get("complete")):
            out.add(P.session_of(y))
    _CACHE["sessions"] = sorted(out)
    return _CACHE["sessions"]


def keys(session):
    """Every HB and SB of the Legislature, in number order: (key, the year folder its record comes from)."""
    if (session, "keys") not in _CACHE:
        where = {}
        for y in (session, session + 1):
            for f in glob.glob(os.path.join(folder(y), "*.json")):
                k = os.path.basename(f)[:-5]
                if KEEP.fullmatch(k):
                    where[k] = y  # the second year's record holds the whole history
        _CACHE[(session, "keys")] = sorted(where.items(), key=lambda kv: (kv[0][0], int(re.sub(r"\D", "", kv[0]))))
    return _CACHE[(session, "keys")]


def bill(year, key):
    return load(os.path.join(folder(year), f"{key}.json"))


def text(s):
    return re.sub(r"\s+", " ", s or "").strip()


def fold(s):
    s = unicodedata.normalize("NFKD", s or "")
    return re.sub(r"[^a-z ]", "", "".join(c for c in s if not unicodedata.combining(c)).lower().replace("-", " ")).strip()


def us_date(s):
    """"07/03/2023", "7/3/2023", "04-21-23" -> ISO, or ""."""
    m = re.search(r"(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})", s or "")
    if not m:
        return ""
    mo, d, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
    y = y + 2000 if y < 100 else y
    try:
        return date(y, mo, d).isoformat()
    except ValueError:
        return ""


# ---- Members ----

def people():
    """Today's legislators from Open States' people file: [(house, seat, name, family, given, party)]."""
    if "people" not in _CACHE:
        out = []
        try:
            rows = list(csv.DictReader(open(os.path.join(P.DATA, "openstates_people.csv"), encoding="utf-8")))
        except OSError:
            rows = []
        for r in rows:
            h = ORG.get(r.get("current_chamber"))
            if not h or not (r.get("current_district") or "").isdigit():
                continue
            party = {"Democratic": "D", "Republican": "R"}.get(r.get("current_party"), (r.get("current_party") or "")[:1])
            out.append((h, f"{h}:{int(r['current_district'])}", r["name"], r.get("family_name") or "", r.get("given_name") or "", party))
        _CACHE["people"] = out
    return _CACHE["people"]


def split_names(s):
    """"Representative(s) Hashem, Lee, M., Morikawa " -> ["Hashem", "Lee, M.", "Morikawa"]; "none" -> []."""
    s = re.sub(r"^(?:Representative|Senator)\(?s?\)?\s*", "", text(s).strip(" .;"))
    if not s or s.lower() == "none":
        return []
    out = []
    for part in [p.strip() for p in s.split(",")]:
        if not part:
            continue
        if out and (re.fullmatch(r"[A-Z]\.?", part) or re.fullmatch(r"(?:Jr|Sr|II|III|IV)\.?", part)):
            out[-1] = f"{out[-1]}, {part}"
        else:
            out.append(part)
    return out


def _match(h, name):
    """A surname ("Lee, M.", "Keohokapu-Lee Loy", "DELA CRUZ") -> the seats of today's members in that house it fits."""
    last, _, init = name.partition(",")
    last, init = fold(last), init.strip(" .")[:1].upper()
    if not last:
        return []
    hits = []
    for hh, seat, full, fam, given, party in people():
        if hh != h:
            continue
        f = fold(full)
        ff = fold(fam)
        if ff == last or f.endswith(" " + last) or f == last or (" " in ff and last.endswith(" " + ff)):
            if init and not (given[:1].upper() == init or full[:1].upper() == init):
                continue
            hits.append(seat)
    return hits


def current_names():
    """Surnames voting in each house in the current Legislature's committee and floor lines (for tying 2023-24's)."""
    if "cur" not in _CACHE:
        names = {"S": set(), "H": set()}
        for k, y in keys(CURRENT):
            b = bill(y, k) or {}
            for a in b.get("actions") or []:
                h = ORG.get((a.get("organization") or {}).get("classification"))
                if not h or not re.search(r"votes? (?:were|in)|voting no|Noes,", a.get("description") or ""):
                    continue
                for seg in re.findall(r"((?:Representative|Senator)\(s\)[^;()]*)", a["description"]):
                    for n in split_names(re.split(r" voting | excused", seg)[0]):
                        names[h].add(fold(n.partition(",")[0]))
        _CACHE["cur"] = names
    return _CACHE["cur"]


def seat_of(session, h, name):
    """A vote or sponsor name -> "S:12", or "S?Name" when it isn't one of today's members (or, for an earlier
    Legislature, not one who also serves in the current one)."""
    k = (session, h, name)
    if k not in _CACHE:
        hits = _match(h, name)
        if session != CURRENT and fold(name.partition(",")[0]) not in current_names()[h]:
            hits = []
        _CACHE[k] = hits[0] if len(hits) == 1 else f"{h}?{display(name)}"
    return _CACHE[k]


def display(name):
    """"DELA CRUZ" -> "Dela Cruz"; "Lee, M." kept; "McKelvey" kept."""
    last, sep, init = name.partition(",")
    last = last.strip()
    if last.isupper():
        known = {fold(fam): fam for _, _, _, fam, _, _ in people()}
        known.update({fold(full.split()[-1]): full.split()[-1] for _, _, full, _, _, _ in people()})
        last = known.get(fold(last)) or re.sub(r"\b(Mc)(\w)", lambda m: m.group(1) + m.group(2).upper(), last.title())
    return f"{last},{init}" if sep else last


def member_name(seat):
    return next((full for _, s, full, _, _, _ in people() if s == seat), None)


def member_party(seat):
    return next((p for _, s, _, _, _, p in people() if s == seat), "")


# ---- Votes ----

CODES = {"no": "N", "excused": "E"}


def committee_vote(line, h):
    """"... The votes in AEN were as follows: 4 Aye(s): Senator(s) Awa; Aye(s) with reservations: Senator(s) Gabbard;
    0 No(es): none; and 1 Excused: Senator(s) DeCoite." -> (ayes, noes, [(name, "N"|"E")]) or None."""
    m = re.search(r"votes?(?: of the [\w ]+?)?(?: in \S+)? were as follows:(.*)$", line, re.I)
    if not m:
        return None
    body = m.group(1)
    ayes = re.search(r"(\d+)\s*Aye\(?s?\)?:\s*(.*?);", body)
    resv = re.search(r"Aye\(?s?\)? with reservations:\s*(.*?)\s*;", body)
    noes = re.search(r"(\d*)\s*No\(?e?s\)?:\s*(.*?)(?:;|$)", body)
    exc = re.search(r"(\d*)\s*Excused:\s*(.*?)\.?\s*$", body)
    yes_names = (split_names(ayes.group(2)) if ayes else []) + (split_names(resv.group(1)) if resv else [])
    no_names = split_names(noes.group(2)) if noes else []
    ex_names = split_names(exc.group(2)) if exc else []
    y = len(yes_names) if yes_names or not ayes else int(ayes.group(1))
    return y, len(no_names), [(n, "N") for n in no_names] + [(n, "E") for n in ex_names], yes_names


def house_floor(line):
    """The House's "... with X voting aye with reservations; Y voting no (2) and Z excused (1)." -> (noes, excused) names."""
    m = re.search(r"(none|Representative\(s\)[^;]*?) voting no \((\d+)\)\s*and\s*(none|Representative\(s\).*?) excused \((\d+)\)", line)
    if not m:
        return None
    return split_names(m.group(1)), split_names(m.group(3))


def senate_floor(line):
    """"Ayes, 24; Aye(s) with reservations: none. Noes, 1 (Senator(s) Awa). Excused, 0 (none)." -> (ayes, noes, excused)."""
    par = r"\(((?:[^()]|\([^()]*\))*)\)"
    m = re.search(r"Ayes,\s*(\d+);.*?Noes,\s*(\d+)\s*" + par + r"\.?\s*Excused,\s*(\d+)\s*" + par, line)
    if not m:
        # The other form: "Ayes, 25; Aye(s) with reservations: none . 0 No(es): none.  1 Excused: Senator(s) Lee, C."
        m = re.search(r"Ayes,\s*(\d+);.*?(\d+)\s*No\(es\):\s*(.*?)\.\s+(\d+)\s*Excused:\s*(.*?)\.?\s*$", line)
        if not m:
            return None
    return int(m.group(1)), split_names(m.group(3)), split_names(m.group(5))


def override_vote(line, h):
    """"Veto overridden by 2/3's vote with 45 Ayes; 4 Noes Representative(s) Garcia, ...; and 2 Excused Representative(s)
    ..." (House) or the Senate's floor form."""
    if h == "S":
        return senate_floor(line)
    m = re.search(r"(\d+) Ayes; (\d+) Noes (none|Representative\(s\)[^;]*)?;?\s*and (\d+) Excused\s*(none|Representative\(s\).*?)?\.?$", line)
    if not m:
        return None
    return int(m.group(1)), split_names(m.group(3) or ""), split_names(m.group(5) or "")


# ---- One bill ----

def committees_in(s, year, h):
    """"AEN/TCA, JDC/WAM" -> [["Agriculture and Environment", "Transportation and Culture and the Arts"], [...]]."""
    groups = []
    for g in re.split(r",\s*", s.strip(" .")):
        codes = [c for c in re.split(r"[/ ]+", g) if re.fullmatch(r"[A-Z]{2,4}", c)]
        if codes:
            groups.append([P.committee_name(c, year, h) for c in codes])
    return groups


def is_const(title):
    return bool(re.match(r"PROPOSING\b", title or "") and re.search(r"CONSTITUTION", title or ""))


def is_budget(title, desc):
    return bool(re.search(r"\bSTATE BUDGET\b|\bMAKING (?:AN EMERGENCY )?APPROPRIATIONS?\b|\bEMERGENCY APPROPRIATION", title or "")
                or re.match(r"Appropriates funds for the operating and capital improvement budget", desc or ""))


def sentence(t):
    """"RELATING TO THE STATE BUDGET." -> "Relating to the state budget"."""
    t = text(t).rstrip(".")
    t = t[:1].upper() + t[1:].lower()
    for w in ("Hawaii", "Hawaiian", "Honolulu", "Maui", "Kauai", "Oahu", "Molokai", "Lanai", "Kalawao", "Office of Hawaiian Affairs",
              "University", "Article"):
        t = re.sub(rf"\b{w.lower()}\b", w, t)
    return re.sub(r"\b(article [ivxlc]+)\b", lambda m: m.group(1)[:8].capitalize() + m.group(1)[8:].upper(), t, flags=re.I)


def unquestion(t):
    """A few descriptions have "?" for an apostrophe or an ʻokina lost on the way ("Authority?s", "Hawai?i"): an
    apostrophe before a possessive or contraction ending, an ʻokina before a vowel (Hawaiian words: Hawaiʻi, Oʻahu)."""
    t = re.sub(r"(?<=[A-Za-z])\?(?=(?:s|t|d|ll|re|ve|m)\b)", "'", t)
    return re.sub(r"(?<=[A-Za-z])\?(?=[aeiouAEIOU])", "ʻ", t)


def description(b):
    """The bill's description (Open States' abstract) without its version tag "(CD1)": (text, tag)."""
    ab = unquestion(next((text(a.get("abstract")) for a in b.get("abstracts") or [] if a.get("abstract")), ""))
    m = re.search(r"\s*\(([HSC]D ?\d+|Proposed [HSC]D ?\d+)\)\s*$", ab)
    return (ab[:m.start()].strip() if m else ab), (m.group(1).replace(" ", "") if m else "")


def title_of(b, desc):
    """The description's first sentence (the official titles say only "Relating to taxation"), cut near 140 characters."""
    if not desc:
        return sentence(b.get("title"))
    first = re.split(r"(?<=[a-z0-9)%])\.\s+(?=[A-Z])", desc)[0].rstrip(".")
    if len(first) > 140:
        cut = first[:140].rsplit(" ", 1)[0].rstrip(",;:")
        first = cut + "…"
    return first


def record(session, key, b, parties):
    origin = key[0]
    other = OTHER[origin]
    title_raw = text(b.get("title"))
    const = is_const(title_raw)
    desc, tag = description(b)
    acts = sorted(b.get("actions") or [], key=lambda a: ((a.get("date") or "")[:10], -(a.get("order") or 0)))
    steps = []  # (date, house or "G", wording, kind)
    passed, amended_by = set(), set()
    where, place, comm = origin, "desk", None
    queue = {"S": [], "H": []}
    refs, first_ref = [], None
    reported = set()
    held_first = False
    finals = set()  # houses passing it on final reading of the current text
    agreed = False
    conf = False
    sent = law = vetoed = items = intent = False
    overrides = set()
    chapter = None
    gov_seen = set()
    votes = []

    def seats(h, listed):
        out, seen = [], Counter()
        for n, code in listed:
            s = seat_of(session, h, n)
            seen[s] += 1
            out.append([s, code])
        return [[s if seen[s] <= 1 or "?" in s else f"{h}?{display(n)}", c] for (s, c), (n, _) in zip(out, listed)]

    def floor_vote(h, d, line, kind="F", label=None):
        if h == "H":
            r = house_floor(line)
            if not r:
                return None
            no, ex = r
            y = P.SEATS["H"] - len(no) - len(ex)
        else:
            r = senate_floor(line)
            if not r:
                return None
            y, no, ex = r
        votes.append([h, kind, label, d, y, len(no), seats(h, [(n, "N") for n in no] + [(n, "E") for n in ex])])
        return y, len(no)

    for a in acts:
        d = (a.get("date") or "")[:10]
        t = text(a.get("description"))
        h = ORG.get((a.get("organization") or {}).get("classification"), "")
        hh = h or where
        yr = int(d[:4]) if d[:4].isdigit() else session
        if not t:
            continue
        # The second house changing the bill (in committee, on second reading or on third): the first house then has to
        # agree, or the houses go to conference.
        if hh == other and origin in passed and re.search(r"as amended|amended in [HS]D|in amended form", t) and not re.match(r"Received", t):
            amended_by.add(other)
        # The governor's actions, recorded in each house's journal: once, on the day the line itself names.
        m = re.match(r"(?:Became law without the Governor's signature, )?Act (\d+),? (?:on )?([\d/-]+)?", t)
        if m and re.match(r"Act \d+|Became law without", t):
            day = us_date(m.group(2) or "") or d
            num = int(m.group(1))
            if ("act", num) in gov_seen:
                continue
            gov_seen.add(("act", num))
            chapter = f"{num} of {day[:4]}"
            if re.search(r"veto override", t, re.I):
                steps.append((day, "G", f"Became law over the governor's veto: Act {num} of {day[:4]}", "chapter"))
            elif t.startswith("Became law without"):
                steps.append((day, "G", "Became law without the governor's signature", "nosign"))
                steps.append((day, "G", f"Act {num} of {day[:4]}", "chapter"))
            else:
                steps.append((day, "G", "SIGNED BY THE GOVERNOR", "signed"))
                steps.append((day, "G", f"Act {num} of {day[:4]}", "chapter"))
            law = True
            continue
        if re.match(r"Vetoed\b", t):
            day = us_date(t) or d
            line_item = bool(re.search(r"line-item|various appropriations", t, re.I))
            if ("veto", line_item) in gov_seen:
                continue
            gov_seen.add(("veto", line_item))
            if line_item:
                items = True
                steps.append((day, "G", "The governor vetoed items in it (a line-item veto)", "itemveto"))
            else:
                vetoed = True
                steps.append((day, "G", "VETOED", "vetoed"))
            continue
        if re.match(r"Notice of [Ii]ntent to veto", t):
            if "intent" in gov_seen:
                continue
            gov_seen.add("intent")
            intent = True
            steps.append((us_date(t) or d, "G", "The governor gave notice of intent to veto it", "intent"))
            continue
        if re.match(r"Veto overridden", t):
            ov = override_vote(t, hh)
            if ov:
                y, no, ex = ov
                votes.append([hh, "F", "override", d, y, len(no), seats(hh, [(n, "N") for n in no] + [(n, "E") for n in ex])])
            overrides.add(hh)
            steps.append((d, hh, f"The {HOUSE[hh]} voted to override the veto" + (f", {ov[0]}-{len(ov[1])}" if ov else ""), "override"))
            continue
        if re.match(r"(?:Transmitted|Enrolled) to Governor", t):
            if "sent" in gov_seen:
                continue
            gov_seen.add("sent")
            if const:
                steps.append((d, "G", "Enrolled; a constitutional amendment goes to the voters, not to the governor for a signature", "other"))
                continue
            sent = True
            steps.append((d, "G", "DELIVERED TO GOVERNOR", "sent"))
            continue
        if re.match(r"Notice of (?:the final form of )?(?:a )?bill proposing constitutional amendment", t):
            steps.append((d, hh, "Notice of the proposed amendment sent to the governor (who can object, but has no veto)", "routine"))
            continue
        if re.match(r"Received from Governor", t):
            what = re.search(r"re:\s*(.+?) \(", t)
            steps.append((d, hh, f"A message from the governor: {what.group(1).lower() if what else 'see the journal'}", "other"))
            continue
        if re.match(r"Carried over to (\d{4})", t):
            steps.append((d, where, f"Carried over to the {t[16:20]} session", "carried"))
            continue
        if re.match(r"(?:Pending [Ii]ntroduction|Prefiled)", t):
            if not any(s[3] == "filed" for s in steps):
                steps.append((d, origin, f"Filed in the {HOUSE[origin]}", "filed"))
            continue
        if re.match(r"Introduced", t):
            if hh == origin and not any(s[3] == "intro" for s in steps):
                steps.append((d, origin, f"Introduced in the {HOUSE[origin]}", "intro"))
            continue
        if re.match(r"(?:Pass(?:ed)? First Reading|\d+ Hrs\. Notice|One Day Notice|Forty-eight|Received notice|Report filed|"
                    r"Separated Committee Report|Public notice requirement waived)", t):
            continue
        mr = re.match(r"(?:Re-?)?[Rr]e-?[Rr]eferred to (.+?)(?:, referral sheet.*)?\.?$|Referred to (.+?)(?:, referral sheet.*)?\.?$", t)
        if mr:
            groups = committees_in(mr.group(1) or mr.group(2), yr, hh)
            if groups:
                queue[hh] = [list(g) for g in groups]
                where, place, comm = hh, "committee", groups[0][0]
                for g in groups:
                    for c in g:
                        if (hh, c) not in refs:
                            refs.append((hh, c))
                if first_ref is None and hh == origin:
                    first_ref = groups[0][0]
                steps.append((d, hh, f"REFERRED TO {groups[0][0].upper()}", "ref"))
                if len(groups[0]) > 1:
                    steps.append((d, hh, f"Heard jointly with the {' and '.join(groups[0][1:])} Committee", "joint"))
                if len(groups) > 1:
                    steps.append((d, hh, "Then to: " + "; ".join(" and ".join(g) for g in groups[1:]), "routine"))
            else:
                steps.append((d, hh, t, "other"))
            continue
        mc = re.match(r"The (?:committee|Conference committee)\(?s?\)? (?:on\s+(\S+?)\s+)?recommends?(?:\(s\))? that the measure be (.+?)\.(?:\s|$)", t, re.I)
        conference = bool(re.match(r"The Conference", t, re.I))
        if mc:
            codes = [c for c in re.split(r"/", mc.group(1) or "") if c]
            cname = "Conference" if conference else " and ".join(P.committee_name(c, yr, hh) for c in codes) or "committee"
            what = mc.group(2).upper()
            if what.startswith("PASSED"):
                cv = committee_vote(t, hh)
                if not conference:
                    for c in codes:
                        reported.add((hh, P.committee_name(c, yr, hh)))
                verb = "approved it" + (" with amendments" if "AMEND" in what and "UNAMENDED" not in what else "")
                if "RECOMMIT" in what:
                    verb += " and kept it for more work"
                tally = f", {cv[0]}-{cv[1]}" if cv else ""
                if conference:
                    steps.append((d, hh, f"The conference committee's {HOUSE[hh]} members approved a compromise version{tally}", "report"))
                else:
                    steps.append((d, hh, f"The {cname} Committee {verb}{tally}", "report"))
                if cv:
                    votes.append([hh, "C", "Conference committee" if conference else cname, d, cv[0], cv[1], seats(hh, cv[2])])
            elif what.startswith("DEFERRED UNTIL"):
                steps.append((d, hh, f"The {cname} Committee put off its decision", "routine"))
            elif what.startswith(("DEFERRED", "HELD")):
                if hh == origin and first_ref and P.committee_name(codes[0], yr, hh) == first_ref if codes else False:
                    held_first = True
                steps.append((d, hh, f"Deferred by the {cname} Committee", "held"))
            else:
                steps.append((d, hh, t, "other"))
            continue
        mdef = re.match(r"The committee\(?s?\)? on\s+(\S+?)\s+deferred the measure\.?$", t)
        if mdef:
            codes = mdef.group(1).split("/")
            cname = " and ".join(P.committee_name(c, yr, hh) for c in codes)
            if hh == origin and first_ref and P.committee_name(codes[0], yr, hh) == first_ref:
                held_first = True
            steps.append((d, hh, f"Deferred by the {cname} Committee", "held"))
            continue
        if re.match(r"The committee\(?s?\)? on\s+\S+\s+deferred the measure until", t, re.I) or re.match(r"Deferred one day", t):
            continue
        mh = re.match(r"(?:Bill (?:re-)?scheduled to be heard by|The committee\(?s?\)? on)\s+(\S+?)\s+(?:on |has scheduled a public hearing on |"
                      r"will hold a public decision making on |has rescheduled its public hearing to |has rescheduled its decision making to )", t, re.I)
        if mh or re.match(r"Bill scheduled for decision making", t):
            steps.append((d, hh, re.sub(r"\s*VIA VIDEOCONFERENCE\.?$|\s*& Videoconference\.?$", "", t), "agenda"))
            continue
        mrep = re.match(r"Reported from (Conference Committee|\S+) \((?:Stand\.|Conf\.?) Com\. Rep\. No\. [\d-]+\)(.*)$", t) or \
            re.match(r"Reported from (Conference Committee)(.*)$", t)
        if mrep:
            rest = mrep.group(2)
            if mrep.group(1) == "Conference Committee":
                conf = True
                finals = set()
                steps.append((d, hh, f"The conference committee reported a compromise version{' (' + re.search(r'CD ?\d+', t).group(0).replace(' ', '') + ')' if re.search(r'CD ?\d+', t) else ''}", "ccr"))
                continue
            codes = mrep.group(1).split("/")
            names = [P.committee_name(c, yr, hh) for c in codes]
            for c in names:
                reported.add((hh, c))
            steps.append((d, hh, "REPORTED", "reported"))
            nxt = re.search(r"referral to (\S+?)[,.]?(?:\s|$)", rest)
            if queue[hh] and set(queue[hh][0]) & set(names):
                queue[hh].pop(0)
            if nxt:
                groups = committees_in(nxt.group(1), yr, hh)
                if groups:
                    comm, place, where = groups[0][0], "committee", hh
                    queue[hh] = groups + [g for g in queue[hh] if g != groups[0]]
                    for c in groups[0]:
                        if (hh, c) not in refs:
                            refs.append((hh, c))
            elif re.search(r"Third Reading|placement on the calendar", rest):
                place, comm, where = "floor", None, hh
            continue
        if re.match(r"Report adopted, as amended .* and recommitted to (\S+)", t, re.I):
            c = P.committee_name(re.search(r"recommitted to (\w+)", t).group(1), yr, hh)
            comm, place, where = c, "committee", hh
            steps.append((d, hh, f"RECOMMITTED TO {c.upper()}", "ref"))
            continue
        # Second reading: the floor adopts the committee's report (a vote, not the passage), and the bill goes on.
        if re.match(r"(?:Report [Aa]dopted[.;] )?(?:Passed Second Reading|referred to the committee)", t) and not re.match(r"(?:Report [Aa]dopted; )?Passed (?:Third|Final) Reading", t):
            mto = re.search(r"referred to (?:the committee\(s\) on )?(\S+?)[ .,]", t + " ")
            if mto:
                groups = committees_in(mto.group(1), yr, hh)
                if groups:
                    comm, place, where = groups[0][0], "committee", hh
                    for c in groups[0]:
                        if (hh, c) not in refs:
                            refs.append((hh, c))
                    steps.append((d, hh, f"REFERRED TO {groups[0][0].upper()}", "ref2"))
                    if len(groups[0]) > 1:
                        steps.append((d, hh, f"Heard jointly with the {' and '.join(groups[0][1:])} Committee", "joint"))
                    continue
            place, comm, where = "floor", None, hh
            steps.append((d, hh, "Second reading; on the calendar for third reading", "second"))
            continue
        mp = re.match(r"(?:Report [Aa]dopted; )?Passed (Third|Final) Reading(.*)$", t)
        if mp:
            r = floor_vote(hh, d, t)
            tally = f", {r[0]}-{r[1]}" if r else ""
            amended = bool(re.search(r"as amended|amended in [HS]D", mp.group(2))) or (hh == other and other in amended_by)
            if mp.group(1) == "Third" and hh not in passed:
                passed.add(hh)
                if hh == other and amended:
                    amended_by.add(hh)
                if hh == other and not amended:
                    finals = {origin, other}
                if hh == origin:
                    where, place, comm = other, "desk", None
                else:
                    where, place, comm = origin, "desk", None
                steps.append((d, hh, f"PASSED {HOUSE[hh].upper()}", "pass"))
                steps.append((d, hh, f"The {HOUSE[hh]} vote: {r[0]}-{r[1]}" + (" (as amended)" if amended else "") if r else f"The {HOUSE[hh]} passed it", "tally"))
            else:
                passed.add(hh)
                finals.add(hh)
                steps.append((d, hh, f"The {HOUSE[hh]} passed it on final reading{tally}" +
                              (" (the conference committee's version)" if conf else " (with the other house's changes)" if agreed else ""), "final"))
            continue
        mf = re.match(r"Failed to pass (Third|Final) Reading", t)
        if mf:
            r = floor_vote(hh, d, t)
            steps.append((d, hh, f"The {HOUSE[hh]} voted it down on {mf.group(1).lower()} reading" + (f", {r[0]}-{r[1]}" if r else ""), "fail"))
            continue
        mrc = re.match(r"Recommitted to (\S+?)(?: as amended| with|\.|$)", t)
        if mrc:
            if mrc.group(1).lower() == "conference":
                steps.append((d, hh, "Sent back to the conference committee", "routine"))
                continue
            groups = committees_in(mrc.group(1), yr, hh)
            if groups:
                comm, place, where = groups[0][0], "committee", hh
                steps.append((d, hh, f"RECOMMITTED TO {groups[0][0].upper()}", "ref"))
                continue
        if re.match(r"Floor [Aa]mendment|(?:House|Senate) Conferees? (?:Changed|Added)|Senators? .* (?:added|discharged)|Meeting Scheduled on .* has been", t):
            steps.append((d, hh, t, "routine"))
            continue
        if re.match(r"(?:House agrees to Senate|Senate agrees with House) amendment", t):
            agreed = True
            finals = set(f for f in finals if f != hh) | {OTHER[hh]}
            steps.append((d, hh, f"The {HOUSE[hh]} agreed to the {HOUSE[OTHER[hh]]}'s changes", "concur"))
            continue
        if re.match(r"(?:House disagrees with Senate|Senate disagrees with House) amendment", t):
            steps.append((d, hh, f"The {HOUSE[hh]} disagreed with the {HOUSE[OTHER[hh]]}'s changes (on to a conference committee)", "noconcur"))
            continue
        if re.match(r"Reconsideration of action taken", t):
            steps.append((d, hh, f"The {HOUSE[hh]} reconsidered an earlier vote", "routine"))
            continue
        if re.match(r"Received from (House|Senate)", t):
            if hh != where or place == "desk":
                where, place, comm = hh, "desk", None
            steps.append((d, hh, f"Received in the {HOUSE[hh]}", "received"))
            continue
        if re.match(r"Returned from (Senate|House)", t):
            amended = "amended form" in t
            if not amended and hh == origin:
                finals = {origin, other}
            steps.append((d, hh, f"Back in the {HOUSE[hh]}" + (" with the other house's changes" if amended else f", unchanged by the {HOUSE[OTHER[hh]]}"), "back"))
            where, place, comm = hh, "desk", None
            continue
        if re.match(r"(?:House|Senate) Conferees? Appointed|Conference committee meeting|Conference Committee Meeting|Bill scheduled for Conference|"
                    r"(?:House|Senate) Conferee\(s\) discharged|This measure has been deleted|The committee\(?s?\)? on .* (?:deleted|added) the measure", t, re.I):
            steps.append((d, hh, t, "routine"))
            continue
        steps.append((d, hh, t, "other"))

    both = sent or law or vetoed or finals >= {"S", "H"}
    if law and vetoed and overrides < {"S", "H"}:
        law = False
    if const:
        stage = 3 if both else 2 if passed else None
        law = vetoed = sent = False
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

    title = title_of(b, desc)
    official = sentence(title_raw)
    if const and not re.search(r"constitution", title, re.I):
        title = f"Constitutional amendment: {title[:1].lower() + title[1:]}"
    # The description first (what the bill does), then the official title ("Relating to taxation."), left out when every
    # word of it is already in the description; a description that's only the title's sentence isn't repeated.
    if not desc:
        summary = official
    elif repeats(official, desc):
        summary = "" if desc.rstrip(".") == title else desc
    else:
        stop = "" if re.search(r"[.!?)”\"]$", desc) else "."  # (a few descriptions end without one)
        summary = f"{desc}{stop} {official}."
    subjects = " ".join(b.get("subject") or [])
    topics = ["const"] if const else []
    for h_, c in refs:
        code = next((k for y in P.COMMITTEES for k, v in P.COMMITTEES[y][h_].items() if v == c), None)
        tp = P.COMMITTEE_TOPICS.get(code)
        if tp and tp not in topics:
            topics.append(tp)
    if len(topics) <= (1 if const else 0):
        topics += [k for k, rx in P.TOPIC_WORDS.items() if rx.search(f"{official} {title} {subjects} {desc[:300]}") and k not in topics]
    topics = list(dict.fromkeys(topics))

    # Introducers in order (Open States splits "LEE, M." into two names: put them back together).
    names = []
    for s in b.get("sponsorships") or []:
        n = text(s.get("name"))
        if names and re.fullmatch(r"[A-Z]\.?", n):
            names[-1] = (f"{names[-1][0]}, {n}", names[-1][1])
        elif n:
            names.append((n, bool(s.get("primary"))))
    people_, seen = [], set()
    for n, primary in names:
        sid = seat_of(session, origin, n)
        name = member_name(sid) if "?" not in sid else display(n)
        if name in seen:
            continue
        seen.add(name)
        people_.append((name, sid, primary))
        if "?" not in sid and member_party(sid) in ("D", "R"):
            parties[(origin, name)] = member_party(sid)
    sponsor = people_[0][0] if people_ else "—"
    district = int(people_[0][1].split(":")[1]) if people_ and "?" not in people_[0][1] else 0
    cos = [x[0] for x in people_[1:]]
    nprimes = max(1, sum(1 for x in people_ if x[2]))

    if stage == 0:
        dsc = f"In {HOUSE[where]} committee" if place == "committee" else "Introduced"
    elif stage == 1:
        dsc = f"On the {HOUSE[where]} floor"
    else:
        dsc = {2: f"Passed the {HOUSE[origin] if origin in passed else HOUSE[other]}", 3: "Passed both houses",
               4: "On the governor's desk", 5: "Became law", 6: "Vetoed"}[stage]
        if stage == 4 and intent:
            dsc = "On the governor's intent-to-veto list"
        if const and stage == 3:
            dsc = "Passed both houses: on the ballot"
    comm_now = comm if place == "committee" and stage in (0, 2) else None

    def dates(test, mode="last"):
        ds = sorted({s[0] for s in steps if test(s) and s[0]})
        return {"first": ds[0], "last": ds[-1], "all": ";".join(ds)}[mode] if ds else ""

    action_dates = [s[0] for s in steps if s[0]]
    # The last action's day is the latest shown in the history: paperwork kept out of it ("routine") would leave the
    # status rows (/your-bills/, /list/, the front page) a day with no wording.
    shown_dates = [s[0] for s in steps if s[0] and s[3] != "routine"] or action_dates
    origin_reported = any(h_ == origin for h_, _ in reported)
    left_first = bool(first_ref and ((origin, first_ref) in reported or origin in passed))
    rec = {
        "nums": [key], "base": [key], "prev": set(),
        "title": title, "summary": summary, "act": "", "lawCode": "", "law": None, "laws": [],
        "comms": sorted({f"{h_} · {c}" for h_, c in refs}), "topics": topics, "places": [],
        "narrow": P.narrow_kind(title), "commFate": "passed" if origin_reported or origin in passed else "held" if held_first else "none",
        "mainTopic": topics[0] if topics else "", "local": "local" in topics, "senDeleg": False, "asmDeleg": False,
        "budget": is_budget(title_raw, desc) and not const,
        "passedS": "S" in passed, "passedA": "H" in passed, "program": None,
        "stage": stage, "passedIn": (HOUSE[origin] if origin in passed else HOUSE[other]) if stage == 2 else None,
        "chapter": chapter if stage == 5 else None,
        "veto": None, "memo": "", "vetoMemo": None, "itemVeto": items,
        "simText": f"{official} {desc}",
        "comm": comm_now if stage == 0 else None,
        "first": min(action_dates, default=f"{session}-01-01"),
        "last": max(shown_dates, default=f"{session}-01-01"),
        "cosp": len(cos),
        "keyDates": [
            dates(lambda s: s[3] in ("reported", "report") and s[1] == origin, "first"),
            dates(lambda s: s[1] == "S" and s[3] in ("pass", "final"), "all"),
            dates(lambda s: s[1] == "H" and s[3] in ("pass", "final"), "all"),
            "",
            dates(lambda s: s[3] == "sent") if stage >= 4 else "",
            dates(lambda s: s[3] in ("signed", "nosign", "chapter")) if stage == 5 else "",
            dates(lambda s: s[3] == "vetoed"),
        ],
        "votes": sorted(votes, key=lambda v: v[3]), "firstComms": [(origin, first_ref, left_first)] if first_ref else [],
        "vers": [{"p": key, "sponsor": sponsor, "district": district, "cosponsors": cos, "primes": nprimes, "cosp": len(cos),
                  "statusDesc": dsc, "committee": comm_now,
                  "actions": [[s[0], s[2]] for s in sorted(steps, key=lambda s: s[0]) if s[3] != "routine"]}],
        "_desc": desc, "_official": title_raw, "_sponsor": people_[0][0] if people_ else "",
    }
    if stage == 5 and not rec["keyDates"][5]:
        rec["keyDates"][5] = rec["last"]
    return rec


# ---- A Legislature ----

def load_session(session):
    """Read one two-year Legislature's bills: (records, bill number -> record index, fetched time, delegation)."""
    k = (session, "loaded")
    if k in _CACHE:
        return _CACHE[k]
    parties = _PARTIES.setdefault(session, {})
    recs, index = [], {}
    for key, y in keys(session):
        b = bill(y, key)
        if not b:
            continue
        rec = record(session, key, b, parties)
        index[key] = len(recs)
        recs.append(rec)
    for r in recs:
        r["prev"] = earlier(session, r)
    for r in recs:
        for x in ("_desc", "_official", "_sponsor"):
            r.pop(x, None)
    paths = [os.path.join(P.DATA, str(y), n) for y in (session, session + 1) for n in ("state.json", "openstates.json")]
    times = [os.path.getmtime(x) for x in paths if os.path.exists(x)]
    fetched = datetime.fromtimestamp(max(times), ZoneInfo(P.TIMEZONE)).strftime("%Y-%m-%d %H:%M") if times else ""
    settle(recs, folder(session))  # bills with no history yet: never dated in the future (states/undated.py)
    _CACHE[k] = (recs, index, fetched, {"SENATE": [], "ASSEMBLY": []})
    return _CACHE[k]


# ---- Earlier Legislatures ----

def _norm(s):
    return re.sub(r"[^a-z0-9 ]", "", re.sub(r"\s+", " ", (s or "").lower())).strip()


def _keys(session):
    """An earlier Legislature's bills that didn't become law: description -> [bills], (official title, first introducer)
    -> [(bill, description words)]."""
    if (session, "earlier") not in _CACHE:
        by_desc, by_title = defaultdict(list), defaultdict(list)
        for key, y in keys(session):
            b = bill(y, key) or {}
            if any(re.match(r"Act \d+", a.get("description") or "") for a in b.get("actions") or []):
                continue
            desc, _ = description(b)
            if is_budget(b.get("title"), desc):
                continue
            dk = _norm(desc)
            if len(dk.split()) >= 8:
                by_desc[dk].append(key)
            sp = next((text(s.get("name")) for s in b.get("sponsorships") or []), "")
            by_title[(_norm(b.get("title")), fold(sp))].append((key, set(dk.split())))
        _CACHE[(session, "earlier")] = (by_desc, by_title)
    return _CACHE[(session, "earlier")]


def earlier(session, rec):
    """The same bill in the Legislature before: the same description word for word (one bill in each), or the same
    official title and first introducer with 60% of the description's words shared (one such bill). Never a budget bill."""
    out = set()
    old = session - 2
    if old not in sessions() or rec.get("budget"):
        return out
    by_desc, by_title = _keys(old)
    mine_desc, _ = _keys(session)
    dk = _norm(rec["_desc"])
    if len(dk.split()) >= 8 and len(by_desc.get(dk, [])) == 1 and len(mine_desc.get(dk, [])) <= 1:
        return {(old, by_desc[dk][0])}
    words = set(dk.split())
    cands = [k for k, w in by_title.get((_norm(rec["_official"]), fold(rec["_sponsor"].split()[-1] if rec["_sponsor"] else "")), [])
             if words and len(words & w) / max(1, len(words | w)) >= 0.6]
    if len(cands) == 1:
        out.add((old, cands[0]))
    return out


def parties(session, recs):
    if session not in _PARTIES:
        load_session(session)
    return {k: v for k, v in _PARTIES.get(session, {}).items() if v in ("D", "R")}


def agendas(session):
    """Bills on upcoming committee hearings: bill -> [["House Health", "2026-02-05T09:00:00"], ...]."""
    today = date.today().isoformat()
    out = {}
    for key, y in keys(session):
        b = bill(y, key) or {}
        for a in b.get("actions") or []:
            t = text(a.get("description"))
            h = ORG.get((a.get("organization") or {}).get("classification"))
            m = re.match(r"(?:Bill (?:re-)?scheduled to be heard by|The committee\(?s?\)? on)\s+(\S+?)\s+(?:on |has scheduled a public hearing on |"
                         r"will hold a public decision making on |has rescheduled its public hearing to )(?:\w+day,? )?(\d\d-\d\d-\d\d)\s+(\d{1,2}:\d\d\s*[AP]M)", t, re.I)
            if not m or not h:
                continue
            day = us_date(m.group(2))
            if not day or day < today:
                continue
            try:
                when = datetime.strptime(f"{day} {m.group(3).replace(' ', '').upper()}", "%Y-%m-%d %I:%M%p").strftime("%Y-%m-%dT%H:%M:%S")
            except ValueError:
                when = f"{day}T00:00:00"
            for c in m.group(1).split("/"):
                entry = [f"{HOUSE[h]} {P.committee_name(c, int(day[:4]), h)}", when]
                if entry not in out.setdefault(key, []):
                    out[key].append(entry)
    return out


# ---- Checks ----

def checks(session):
    """Laws, vetoes and line-item vetoes by the year of the governor's action, and amendments sent to the voters."""
    recs = load_session(session)[0]
    by_year = defaultdict(lambda: {"laws": 0, "vetoes": 0, "without signature": 0, "over a veto": 0})
    items, amend = [], []
    for r in recs:
        acts = r["vers"][0]["actions"]
        if r["stage"] == 5:
            y = r["chapter"].split(" of ")[1]
            by_year[y]["laws"] += 1
            if any(t.startswith("Became law without") for _, t in acts):
                by_year[y]["without signature"] += 1
            if any(t.startswith("Became law over") for _, t in acts):
                by_year[y]["over a veto"] += 1
        if r["stage"] == 6:
            by_year[r["keyDates"][6][:4]]["vetoes"] += 1
        if r.get("itemVeto"):
            items.append(r["nums"][0])
        if "const" in r["topics"] and r["stage"] == 3:
            amend.append(r["nums"][0])
    numbers = defaultdict(list)
    for r in recs:
        if r.get("chapter"):
            numbers[r["chapter"].split(" of ")[1]].append(int(r["chapter"].split(" of ")[0]))
    gaps = {y: sorted(set(range(1, max(n) + 1)) - set(n)) for y, n in numbers.items()}
    stuck = [r["nums"][0] for r in recs if r["stage"] in (3, 4) and "const" not in r["topics"]]
    return {"by year": dict(by_year), "line-item vetoes": items, "amendments to the voters": amend,
            "Act numbers missing": gaps, "passed both or sent, no outcome": stuck,
            "stages": dict(Counter(r["stage"] for r in recs)), "bills": len(recs)}


if __name__ == "__main__":
    for s in ([int(sys.argv[1])] if len(sys.argv) > 1 else sessions()):
        print(s, json.dumps(checks(s), indent=1))
