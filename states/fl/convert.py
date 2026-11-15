"""Florida's bills (downloaded by states/fl/fetch.py from the Florida Senate's website, and first from Open States' bulk
files by states/openstates_bulk.py) in the shape build_data.py reads. A page a year: the Legislature meets once a year for
60 days (from March in odd years, January in even ones) and bills die when it ends. House and Senate bills (HB, SB) and the
joint resolutions (HJR, SJR), which propose amendments to the State Constitution: three-fifths of each house's members,
then the voters at the next general election, never the governor ("Signed by Officers and filed with Secretary of State");
tagged "const", they stop at stage 3. Resolutions, concurrent resolutions and memorials aren't downloaded; bills
"Withdrawn prior to introduction" (or "Filed in error") are left out.

Each bill comes from its official page (data/fl/<year>/bills/HB1205.html) when fetch.py has read it, else from its Open
States record (data/fl/<year>/openstates/HB1205.json, public domain, taken from the same site). Both carry the same
history lines (Open States drops the journal pages, "-SJ 434", and a space before commas and parentheses), each with its
house, so `from_page()` and `from_openstates()` give one shape and `record()` reads either; `python3 -m states.fl.convert
compare 2026` converts every bill both ways and lists the stages that differ. The history:
- "Filed"; the Senate refers a bill to all its committees in one line, "Referred to Criminal Justice; Judiciary; Rules",
  the House one line each ("Referred to Criminal Justice Subcommittee", "Referred to Judiciary Committee"); "Now in X"
  says where it is; "Original reference(s) removed: X" and "Remaining references corrected to X; Y" change the list.
- Committee reports: the Senate's "Favorable by Criminal Justice; YEAS 9 NAYS 0", "CS by Criminal Justice; YEAS 9 NAYS 0"
  (a committee substitute: the same bill number, rewritten), "Favorable with 2 amendment(s) by- Fiscal Policy (...); YEAS
  ...", "Unfavorable by X; YEAS 3 NAYS 5", "Submitted as Committee Bill and Reported Favorably by X" (a committee's own
  bill), "Recommendation: Favorable by" (an appropriations subcommittee's); the House's "Favorable by X", "Favorable with
  CS by X", "Reported out of X" (no tallies). "Laid on Table under Rule 7.18(a)" after a House CS is the old text's
  formality. Committees rarely vote bills down: most die in committee at the end ("Died in Judiciary").
- The floor: "Placed on Calendar, on 2nd reading" / "Bill released to House Calendar", the special order calendar, "Read
  2nd time", "Read 3rd time", "CS passed as amended; YEAS 76, NAYS 31" (the passage; "failed to pass" a defeat, which ends
  it), "Reconsidered" (undoes the house's last vote when that was the passage). "In Messages" is the bill reaching the
  other house. Florida files most bills in both houses (companions): when one passes, the other house takes it up in
  place of its own ("Substituted for CS/SB 1346"), and its own is "Laid on Table, companion bill(s) passed, see CS/HB
  1195": shown as replaced (`STATE.endedNote()`), kept as its own record.
- Back in the first house: "Concurred in 1 amendment(s)" (or "Amendment 915478 Concur") and "Passed as amended; YEAS
  ..." again, "Refused to concur", conference reports ("Passed as amended by Conference Committee Report"). "Ordered
  enrolled" / "Ordered engrossed, then enrolled" is passed both houses: Florida enrolls only a bill both houses passed in
  the same text.
- "Signed by Officers and presented to Governor" (sent, often weeks after the session), "Approved by Governor", "Allowed
  to become Law without Governor's Signature", "Vetoed by Governor", "Governor vetoed specific Line Item(s)" (a law with
  items vetoed: the budget), "Chapter No. 2025-21" (the law's number in the Laws of Florida). A veto goes to the next
  regular session ("Veto Message received (2026 Regular Session)"), which can override it by two-thirds of each house
  ("Veto overridden; YEAS 113, NAYS 0"); otherwise "Veto Message transmitted to Secretary of State" a year later: the veto
  stands. The House's 2025 overrides of 2024 budget items (and the Senate's two) didn't change any bill's outcome.
Laws: a bill the governor approved or let become law (or both houses overrode), which gets a chapter number; a vetoed
bill gets none. `checks()` compares laws and vetoes with the last actions on the Senate's bill lists, bill for bill.

Votes: every floor passage, member by member from the vote PDF's text (votes/, "Y Abbott-5": the district gives the
seat) when fetch.py has read it, else from Open States' roll call (surnames, "Alvarez, D."), matched by house, day and
tally, else the history's tally. Committee votes: the Senate committee's vote record (votes/, an X under Yea or Nay),
else Open States' (Senate committees, and House committees from 2026), else the Senate history line's tally.

"What it does": the summary of the bill's newest staff analysis (analyses/: the House's "Effect of the Bill", the
Senate's "I. Summary") when fetch.py has read it; otherwise none: the bill's one-line description from the Senate's site (the
page's, or Open States' copy of it) is the summary line, shown under the title, and isn't repeated.
"""
import glob, html as H_, json, os, re, sys, unicodedata
from collections import Counter, defaultdict
from datetime import date, datetime
from zoneinfo import ZoneInfo

from states.fl import profile as P

HOUSE = {"S": "Senate", "H": "House"}
OTHER = {"S": "H", "H": "S"}
SEATS = {"S": 40, "H": 120}
KEEP = re.compile(r"(HB|SB|HJR|SJR)\d+")
_CACHE, _PARTIES = {}, {}


def folder(session):
    return os.path.join(P.DATA, str(session))


def load(path, default=None):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def sessions():
    if "sessions" in _CACHE:
        return _CACHE["sessions"]
    out = []
    for f in sorted(os.listdir(P.DATA)) if os.path.isdir(P.DATA) else []:
        d = os.path.join(P.DATA, f)
        if re.fullmatch(r"\d{4}", f) and (os.path.isdir(os.path.join(d, "bills")) or os.path.isdir(os.path.join(d, "openstates"))):
            if keys(int(f)):
                out.append(int(f))
    _CACHE["sessions"] = out
    return out


def listing(session):
    k = (session, "list")
    if k not in _CACHE:
        _CACHE[k] = load(os.path.join(folder(session), "list.json"), {}) or {}
    return _CACHE[k]


def keys(session):
    """The session's bills: the Senate's list when it's been read, else the Open States records."""
    lst = listing(session).get("bills") or {}
    ks = [k for k in lst if KEEP.fullmatch(k)]
    if not ks:
        ks = [os.path.basename(f)[:-5] for f in glob.glob(os.path.join(folder(session), "openstates", "*.json"))]
        ks += [os.path.basename(f)[:-5] for f in glob.glob(os.path.join(folder(session), "bills", "*.html"))]
        ks = sorted({k for k in ks if KEEP.fullmatch(k)})
    return sorted(ks, key=lambda k: (k[0] != "H", re.sub(r"\d", "", k), int(re.sub(r"\D", "", k))))


def text(fragment):
    return re.sub(r"\s+", " ", H_.unescape(re.sub(r"<[^>]+>", " ", fragment or ""))).strip()


def unmangle(s):
    """Open States' "LÃ³pez" (UTF-8 read as Latin-1) -> "López"."""
    if s and re.search(r"[ÃÂ]", s):
        try:
            return s.encode("latin-1").decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            return s
    return s


def iso(d):
    """"4/16/2025" -> "2025-04-16"."""
    m, dd, y = d.strip().split("/")
    y = int(y)
    return f"{y + 2000 if y < 100 else y:04d}-{int(m):02d}-{int(dd):02d}"


def journal_free(line):
    """"Read 2nd time -SJ 434" -> "Read 2nd time"; "2026-163 ," -> "2026-163,"."""
    line = re.sub(r"\s+([,;)])", r"\1", unmangle(line))
    return re.sub(r"\s*-\s*[SH]J\s+[\d, ]+\s*$", "", line).strip()


# ---- One bill: the official page, else the Open States record, in one shape ----

def from_page(session, key):
    path = os.path.join(folder(session), "bills", f"{key}.html")
    try:
        s = open(path, encoding="utf-8").read()
    except OSError:
        return None
    h2 = re.search(r"<h2>(.*?)</h2>", s, re.S)
    if not h2:
        return None
    label, _, short = text(h2.group(1)).partition(": ")
    kind, sponsors = "", []
    byp = re.search(r"</h2>\s*<p>(.*?)</p>", s, re.S)
    if byp:
        kind_html, _, who = byp.group(1).partition("<span>by</span>")
        kind = text(kind_html)
        co = False
        for pc in re.split(r"(<span>;\s*</span>|<span>\(CO-INTRODUCERS\)\s*</span>)", who):
            if "CO-INTRODUCERS" in pc:
                co = True
            elif not re.fullmatch(r"<span>;\s*</span>", pc) and text(pc):
                sponsors.append((text(pc), co))
    ab = re.search(r'<p class="width80">\s*(.*?)</p>', s, re.S)
    abstract = text(ab.group(1)) if ab else ""
    hist = s[s.find('id="tabBodyBillHistory"'):s.find('id="tabBodyRelatedBills"')]
    actions = []
    for d, ch, body in re.findall(r'<tr>\s*<td class="centertext">([\d/]+)</td>\s*<td class="centertext">(.*?)</td>\s*'
                                  r'<td[^>]*>(.*?)</td>', hist, re.S):
        h = {"House": "H", "Senate": "S"}.get(text(ch), "")
        for li in re.split(r"&bull;", body):
            line = journal_free(text(li))
            if line:
                actions.append((iso(d), h, line))
    votes = []
    vh = s[s.find('id="tabBodyVoteHistory"'):s.find('id="tabBodyCitations"')]
    floor_at = vh.find('id="Votes"')
    for m in re.finditer(r"<tr>(.*?)</tr>", vh, re.S):
        link = re.search(r'href="(/Session/Bill/\d+/\d+/Vote/[^"]+)"', m.group(1))
        if link:
            cells = [text(c) for c in re.findall(r"<td[^>]*>(.*?)</td>", m.group(1), re.S)]
            votes.append({"kind": "floor" if 0 <= floor_at < m.start() else "committee",
                          "path": H_.unescape(link.group(1)), "cells": cells})
    return {"key": key, "label": label, "short": short, "kind": kind, "sponsors": sponsors, "abstract": abstract,
            "actions": actions, "votes": votes, "source": "page", "os_votes": []}


def from_openstates(session, key):
    d = load(os.path.join(folder(session), "openstates", f"{key}.json"))
    if not d:
        return None
    acts = []
    for a in d.get("actions") or []:
        h = {"upper": "S", "lower": "H"}.get((a.get("organization") or {}).get("classification") or "", "")
        line = journal_free(re.sub(r"\s+", " ", a.get("description") or "").strip())
        if line:
            acts.append(((a.get("date") or "")[:10], h, line))
    ab = ((d.get("abstracts") or [{}])[0] or {}).get("abstract") or ""
    sponsors = [(unmangle(re.sub(r"\s+", " ", x.get("name") or "").strip()), not x.get("primary")) for x in d.get("sponsorships") or []]
    return {"key": key, "label": d.get("identifier") or key, "short": unmangle(re.sub(r"\s+", " ", d.get("title") or "").strip()),
            "kind": "", "sponsors": [x for x in sponsors if x[0]], "abstract": unmangle(re.sub(r"\s+", " ", ab).strip()),
            "actions": acts, "votes": [], "source": "openstates", "os_votes": d.get("votes") or []}


def bill(session, key, prefer="page"):
    """The bill in one shape: its official page when there is one (with Open States' roll calls kept alongside, for
    votes whose PDFs aren't read yet), else its Open States record."""
    ck = ("bill", session, key, prefer)
    if ck not in _CACHE:
        b = from_page(session, key) if prefer == "page" else None
        o = from_openstates(session, key)
        if b and o:
            b["os_votes"] = o["os_votes"]
        _CACHE[ck] = b or o
    return _CACHE[ck]


def description(b):
    """"Fentanyl Testing; Requires hospitals ..." -> "Requires hospitals ...": the page's (and Open States') one-line
    description, without the short title it starts with."""
    a = b.get("abstract") or ""
    short = b.get("short") or ""
    if short and a.lower().startswith(short.lower()):
        a = a[len(short):].lstrip(" ;:")
    return a.replace(" & ", " and ").strip()


# ---- Members ----

def fold(s):
    s = unicodedata.normalize("NFKD", unmangle(s or ""))
    return re.sub(r"[^a-z]", "", "".join(c for c in s if not unicodedata.combining(c)).lower())


def display(name):
    """"Abbott, Shane G." -> "Shane G. Abbott"; 'Caruso, Michael A. "Mike"' -> "Mike Caruso"; "Rudman, Dr. Joel" -> "Joel
    Rudman"; "* Casello, Joe" -> "Joe Casello"; "Pizzo, Jason W. B." -> "Jason W. B. Pizzo"."""
    n = re.sub(r"^\*\s*", "", name or "").strip()
    last, _, given = n.partition(",")
    given = re.sub(r"\b(?:Dr|Rev)\.\s*", "", given).strip()
    nick = re.search(r'"([^"]+)"', given)
    if nick:
        given = nick.group(1)
        given = given.strip()
    sfx = re.match(r"^(.*?),?\s+(Jr\.|Sr\.|II|III|IV)$", given)
    if sfx:
        return re.sub(r"\s+", " ", f"{sfx.group(1)} {last.strip()} {sfx.group(2)}").strip()
    return re.sub(r"\s+", " ", f"{given} {last.strip()}").strip()


def members(term):
    """A term's members (data/fl/members/<term>.json): [{house, district, name, display, last, inits, start, end, party,
    member_id, page}]; the placeholder "Pending, Election" left out."""
    k = ("members", term)
    if k not in _CACHE:
        d = load(os.path.join(P.DATA, "members", f"{term}.json"), {}) or {}
        out = []
        for m in (d.get("senate") or []) + (d.get("house") or []):
            if not m.get("district") or re.match(r"Pending\b|Vacant\b", m.get("name") or ""):
                continue
            last, _, given = re.sub(r"^\*\s*", "", m["name"]).partition(",")
            given = re.sub(r"\b(?:Dr|Rev)\.\s*", "", given)
            start = end = ""
            dm = re.match(r"(\d+/\d+/\d+)\s*-\s*(\d+/\d+/\d+)", m.get("dates") or "")
            if dm:
                start, end = iso(dm.group(1)), iso(dm.group(2))
            last = re.sub(r",?\s+(?:Jr\.?|Sr\.?|II|III|IV)$", "", last.strip())
            alts = {fold(re.split(r"[-\s]", last)[0])}
            out.append({**m, "display": display(m["name"]), "last": fold(last), "lastRaw": last.strip(), "alts": alts,
                        "inits": {fold(w)[:1] for w in re.split(r"[\s.]+", given) if fold(w)},
                        "start": start, "end": end})
        _CACHE[k] = out
    return _CACHE[k]


def party_letter(p):
    return "D" if (p or "").startswith("Democrat") else "R" if (p or "").startswith("Republican") else "I" if p else ""


def holders(term, h, last, init="", day=""):
    """The members of a house with that surname (and initial), on that day when several served."""
    hits = [m for m in members(term) if m["house"] == h and m["last"] == last]
    if not hits:
        # "Hart" for Hart-Lowman (a name changed mid-term), "Busatta Cabrera" for Busatta.
        hits = [m for m in members(term) if m["house"] == h and (last in m["alts"] or any(last.startswith(a) and len(a) >= 4 for a in {m["last"]}))]
    if init:
        hits = [m for m in hits if init in m["inits"]] or hits
    if len(hits) > 1 and day:
        on = [m for m in hits if (not m["start"] or m["start"] <= day) and (not m["end"] or day <= m["end"])]
        hits = on or hits
    return hits


def vote_seat(term, h, name, day=""):
    """A roll-call name ("Alvarez, D.", "President Albritton", "Smith, VICE CHAIR") -> "H:69", else "H?Name"."""
    n = re.split(r"\s{2,}", unmangle(name or "").strip())[0]
    n = re.sub(r",?\s*(?:VICE CHAIR|CHAIR|VC)$", "", n).strip()
    n = re.sub(r"^(?:President|Speaker|Mr\.|Madam)\s+", "", n).strip()
    last, _, init = n.partition(",")
    hits = holders(term, h, fold(last), fold(init)[:1], day)
    if len(hits) == 1:
        return f"{h}:{hits[0]['district']}"
    return f"{h}?{n}"


def sponsor_of(term, h, name, day=""):
    """A sponsor as the history writes it ("Harris", "Campbell, Daryl", "López, J.") -> (display name, district, party)
    for a member of the house, else None (a committee)."""
    last, _, given = unmangle(name).partition(",")
    hits = holders(term, h, fold(last), fold(given)[:1], day)
    if not hits:
        return None
    if len(hits) > 1:
        full = [m for m in hits if given.strip() and fold(given) in fold(m["name"].partition(",")[2])]
        hits = full or hits
    m = hits[-1] if len(hits) > 1 and not day else hits[0]
    return m["display"], m["district"], party_letter(m.get("party"))


# ---- Wording ----

def comm_name(c):
    """"Health Care Facilities & Systems Subcommittee" -> "Health Care Facilities and Systems"; "Judiciary Committee" ->
    "Judiciary"; "Appropriations Committee on Criminal and Civil Justice" -> "Criminal and Civil Justice Appropriations";
    "Select Committee on Property Taxes" -> "Property Taxes Select"; "Special Master on Claim Bills" -> "Claim Bills
    Special Master". The House's subcommittees keep their own names without "Subcommittee" (none shares a name with a
    full committee)."""
    c = re.sub(r"\s+", " ", (c or "").strip()).strip(" .;,-")
    c = re.sub(r"^(?:the )?(?:House |Senate )", "", c)
    c = c.replace(" & ", " and ").replace("&", " and ")
    c = re.sub(r"Pre-K ?- ?12", "Pre-K - 12", c)
    m = re.match(r"Appropriations Committee on (.+)$", c)
    if m:
        return f"{m.group(1)} Appropriations"
    m = re.match(r"Select Committee on (.+)$", c)
    if m:
        return f"{m.group(1)} Select"
    if c == "Special Master on Claim Bills":
        return "Claim Bills Special Master"
    c = re.sub(r" (?:Sub)?[Cc]ommittee$", "", c)
    return c


def bill_ref(s):
    """"CS/CS/SB 1346" -> "SB1346"."""
    m = re.search(r"(?:^|[/\s])(HB|SB|HJR|SJR|H|S)\s*(\d+)", s or "")
    if not m:
        return ""
    t = m.group(1)
    return (t + "B" if t in ("H", "S") else t) + m.group(2)


def spaced(k):
    """"HB1195" -> "HB 1195"."""
    return re.sub(r"^([A-Z]+)(\d)", r"\1 \2", k)


def is_budget(key, title):
    n = int(re.sub(r"\D", "", key))
    return bool(re.search(r"\bAppropriations?\b|\bGeneral Appropriations Act\b|^Implementing the|Trust Funds?\b", title or "", re.I)) \
        or (key.startswith("HB") and 5000 <= n <= 5999) or (key.startswith("SB") and 2500 <= n <= 2599)


LOCAL_TITLE = re.compile(r"(?:^|, )(?!Rural\b)(?:(?:[A-Z][\w.'\-]*\s?)+(?:and (?:[A-Z][\w.'\-]*\s?)+)?Count(?:y|ies)(?: Charter)?"
                         r"(?:, (?:[A-Z][\w.'\-]*\s?)+Count(?:y|ies))*|(?:City|Town|Village) of [\w .'\-]+)$")


def narrow(b):
    """Local bills (the page's "LOCAL BILL"; without a page, a House bill numbered 4001-4999, where the House files them,
    or a title ending in a county or city) are for one place; claim bills ("Relief of ...") pay one person or family."""
    k, t = b.get("kind") or "", b.get("short") or ""
    if re.search(r"CLAIM", k) or re.match(r"Relief of\b", t):
        return "person"
    if re.search(r"\bLOCAL\b", k):
        return "place"
    if not k and (re.fullmatch(r"HB4\d{3}", b["key"]) or LOCAL_TITLE.search(t)):
        return "place"
    return P.narrow_kind(t)


TALLY = re.compile(r"YEAS\s*(\d+),?\s*NAYS\s*(\d+)", re.I)
CHAPTER = re.compile(r"Chapter No\.\s*(\d{4})-(\d+)", re.I)


def tally(t):
    m = TALLY.search(t)
    return (int(m.group(1)), int(m.group(2))) if m else None


# ---- Votes ----

def official_votes(session, key):
    """The bill's vote PDFs read by fetch.py (votes/<key>.json), parsed: [{"h", "kind": "F"|"C", "day", "y", "n",
    "comm", "members": [(seat or "H?Name", code)]}]."""
    raw = load(os.path.join(folder(session), "votes", f"{key}.json"), {}) or {}
    out = []
    for path, v in raw.items():
        t = v.get("text") or ""
        if v.get("kind") == "floor":
            r = floor_pdf(session, t)
        else:
            r = committee_pdf(session, t)
        if r:
            r["path"] = path
            out.append(r)
    return out


CODES = {"Y": "Y", "N": "N", "EX": "E", "AV": "B"}


def floor_pdf(session, t):
    """A floor vote's text ("Y Abbott-5   N Dunkley-97", a blank code for not voting)."""
    h = "S" if "The Florida Senate" in t[:600] else "H" if "House of Representatives" in t[:600] else None
    dm = re.search(r"Date:\s*(\d+/\d+/\d+)", t)
    ym = re.search(r"Yeas\s*-\s*(\d+)\s+Nays\s*-\s*(\d+)", t)
    if not (h and dm and ym):
        return None
    listed = []
    body = t[ym.end():]
    body = body.split("Y=Yea")[0]
    for line in body.split("\n"):
        if re.match(r"\s*Presiding", line):
            continue
        toks = [x for x in re.split(r"\s{2,}", line.strip()) if x]
        code = None
        for tok in toks:
            m = re.fullmatch(r"(Y|N|EX|AV)(?:\s+(.+-\d+))?", tok)
            if m and not m.group(2):
                code = m.group(1)
                continue
            name = m.group(2) if m else tok
            nm = re.fullmatch(r"(.+?)-(\d{1,3})", name)
            c = (m.group(1) if m else code) or ""
            code = None
            if not nm:
                continue
            seat = f"{h}:{int(nm.group(2))}"
            mark = CODES.get(c, "A")
            if mark != "Y":
                listed.append([seat, mark])
    return {"h": h, "kind": "F", "day": iso(dm.group(1)), "y": int(ym.group(1)), "n": int(ym.group(2)), "comm": None,
            "members": listed}


def committee_pdf(session, t):
    """A Senate committee's vote record: the committee, the meeting date and each senator's X under Yea or Nay in the
    FINAL VOTE columns (no X: absent)."""
    cm = re.search(r"COMMITTEE:\s*(.+)", t)
    dm = re.search(r"MEETING DATE:\s*\w+,\s*(\w+ \d+, \d{4})", t)
    if not (cm and dm):
        return None
    try:
        day = datetime.strptime(dm.group(1), "%B %d, %Y").strftime("%Y-%m-%d")
    except ValueError:
        return None
    lines = t.split("\n")
    head = next((i for i, l in enumerate(lines) if re.search(r"Yea\s+Nay\s+SENATORS", l)), None)
    if head is None:
        return None
    yea_at = lines[head].find("Yea")
    nay_at = lines[head].find("Nay")
    term = P.term_of(session)
    listed, y, n = [], 0, 0
    for l in lines[head + 1:]:
        if re.search(r"TOTALS|^\s*\d+\s+\d+\s", l):
            break
        m = re.match(r"^((?:\s*X)*\s*)([A-Z][A-Za-z'.\- ,]*?[a-zA-Z.])(?:\s{2,}|$)", l)
        if not m or re.match(r"(?:Yea|Nay|SENATORS|FINAL|CODES|REPORTING)\b", m.group(2)):
            continue
        name = m.group(2)
        marks = [mm.start() for mm in re.finditer(r"X", m.group(1))]
        seat = vote_seat(term, "S", name, day)
        if not marks:
            listed.append([seat, "A"])
            continue
        if abs(marks[0] - nay_at) < abs(marks[0] - yea_at):
            n += 1
            listed.append([seat, "N"])
        else:
            y += 1
    return {"h": "S", "kind": "C", "day": day, "y": y, "n": n, "comm": comm_name(cm.group(1)), "members": listed}


OS_CODE = {"yes": "Y", "no": "N", "not voting": "A", "excused": "E", "absent": "A", "abstain": "B", "other": "A"}


def os_votes(session, b):
    """Open States' roll calls in the same shape (names are surnames, matched to that term's members)."""
    out = []
    term = P.term_of(session)
    for v in b.get("os_votes") or []:
        h = {"upper": "S", "lower": "H"}.get((v.get("organization") or {}).get("classification"))
        day = (v.get("start_date") or "")[:10]
        if not h or not day:
            continue
        kinds = v.get("motion_classification") or []
        kind = "C" if "committee-passage" in kinds or "committee-failure" in kinds or re.search(r"Favorable|Unfavorable|Committee", v.get("motion_text") or "") else "F"
        counts = {c["option"]: c["value"] for c in v.get("counts") or []}
        listed = []
        for x in v.get("votes") or []:
            code = OS_CODE.get(x.get("option"), "A")
            if code != "Y":
                listed.append([vote_seat(term, h, x.get("voter_name"), day), code])
        cm = re.search(r"\((.+?)\)\s*$", v.get("motion_text") or "")
        out.append({"h": h, "kind": kind, "day": day, "y": counts.get("yes", 0), "n": counts.get("no", 0),
                    "comm": comm_name(cm.group(1)) if cm else None, "members": listed, "motion": v.get("motion_text") or ""})
    return out


def dedupe_seats(listed, h):
    """A seat named twice in one roll call (two members with the surname, unresolved) becomes the names."""
    c = Counter(s for s, _ in listed if "?" not in s)
    return [[s if c[s] <= 1 else f"{h}?{s}", code] for s, code in listed]


# ---- One bill ----

def record(session, b, parties):
    p = b["key"]
    origin = p[0]
    other = OTHER[origin]
    const = "JR" in p
    term = P.term_of(session)
    steps = []  # (date, house or "G", wording, kind)
    passed, amended_by, concurred = set(), set(), False
    where, place, comm = origin, "desk", None
    queue = {"S": [], "H": []}
    refs, first_ref = [], None
    reported = set()  # (house, committee)
    defeated_first = False
    enrolled = sent = law = vetoed = items = to_sos = False
    overrides = set()
    chapter = None
    replaced_by, failed = None, None
    fvotes = []
    votes_pool = official_votes(session, p)
    pool_os = os_votes(session, b)
    used = set()

    def take(kind, h, d, y=None, n=None, comm_=None):
        """The member-by-member roll call for a step: an official PDF first, else Open States'."""
        for src in (votes_pool, pool_os):
            best = None
            for i, v in enumerate(src):
                if (id(src), i) in used or v["kind"] != kind or v["h"] != h or v["day"] != d:
                    continue
                if y is not None and (v["y"], v["n"]) != (y, n) and (
                        abs(v["y"] - y) + abs(v["n"] - (n or 0)) > 2 or sum(c == "N" for _, c in v["members"]) > (n or 0)):
                    continue  # another roll call that day (a local bills calendar's, an amendment's)
                if kind == "C" and comm_ and v.get("comm") and v["comm"] != comm_ and src is votes_pool:
                    continue
                best = i
                break
            if best is not None:
                used.add((id(src), best))
                return src[best]
        return None

    acts = sorted(b["actions"], key=lambda a: a[0])  # stable: the page's order within a day
    for i, (d, h, t) in enumerate(acts):
        hh = h or where
        if re.match(r"Withdrawn prior to introduction|Filed in error", t):
            return None, None
        m = CHAPTER.search(t)
        if m and re.match(r"Chapter No", t):
            chapter = f"{m.group(1)}-{m.group(2)}"
            if not (vetoed and not overrides >= {"S", "H"}):
                law = True
            steps.append((d, "G", f"Chapter {m.group(1)}-{m.group(2)}, Laws of Florida", "chapter"))
            continue
        if t == "Filed":
            steps.append((d, origin, f"Filed in the {HOUSE[origin]}", "filed"))
            continue
        if t == "Introduced" or (t.startswith("1st Reading (Original") and h == origin and not any(s[3] == "intro" for s in steps)):
            if h == origin and not any(s[3] == "intro" for s in steps):
                steps.append((d, origin, f"Introduced in the {HOUSE[origin]}", "intro"))
            continue
        if re.match(r"(?:\d\w\w Reading|(?:CS/)*CS by .* read 1st time|Read 1st time)", t):
            continue  # readings: not news
        mr = re.match(r"(?:Referred|Recommitted) to (.+)$", t)
        if mr and not re.search(r"Calendar$", mr.group(1)) and not t.startswith("Veto"):
            cs = [comm_name(x) for x in mr.group(1).split(";")] if hh == "S" else [comm_name(mr.group(1))]
            cs = [c for c in cs if c]
            same_day = [s for s in steps if s[0] == d and s[1] == hh and s[3] == "ref"]
            if hh != where or not queue[hh] or not same_day:
                queue[hh] = []
            for c in cs:
                if c not in queue[hh]:
                    queue[hh].append(c)
                refs.append((hh, c))
                if first_ref is None and hh == origin:
                    first_ref = c
            if not same_day or t.startswith("Recommitted"):
                comm, place, where = cs[0], "committee", hh
                steps.append((d, hh, f"REFERRED TO {cs[0].upper()}", "ref"))
                if len(cs) > 1:
                    steps.append((d, hh, f"Then to: {', '.join(cs[1:])}", "routine"))
            else:
                steps.append((d, hh, f"Then to: {', '.join(cs)}", "routine"))
            continue
        mn = re.match(r"Now in (.+)$", t)
        if mn:
            c = comm_name(mn.group(1))
            comm, place, where = c, "committee", hh
            if c not in queue[hh]:
                queue[hh].insert(0, c)
            if not any(x == (hh, c) for x in refs):
                refs.append((hh, c))
            steps.append((d, hh, f"Now in the {c} Committee", "routine"))
            continue
        mo = re.match(r"(Original reference\(?s?\)? removed|Remaining references corrected to):?\s*(.+)$", t)
        if mo:
            cs = [comm_name(x) for x in mo.group(2).split(";")]
            if mo.group(1).startswith("Original"):
                queue[hh] = [c for c in queue[hh] if c not in cs]
            else:
                done = [c for c, _ in [(c, 0) for c in queue[hh]] if (hh, c) in reported]
                queue[hh] = done + [c for c in cs if c not in done]
                for c in cs:
                    if (hh, c) not in refs:
                        refs.append((hh, c))
            steps.append((d, hh, t, "routine"))
            continue
        ma = re.match(r"(?:On Committee agenda--\s*(.+?), (\d+/\d+/\d+)|(?:PCS )?[Aa]dded (?:as workshop bill )?to (.+?) agenda)", t)
        if ma:
            c = comm_name(ma.group(1) or ma.group(3))
            when = f" for {datetime.strptime(iso(ma.group(2)), '%Y-%m-%d').strftime('%B %-d')}" if ma.group(2) else ""
            steps.append((d, hh, f"On the {c} Committee's agenda{when}", "agenda"))
            continue
        mrep = re.match(r"(?:(?P<cs>(?:CS/)*CS) by|(?P<fav>Favorable)(?: with (?P<am>\d+ )?amendment\(s\)| with (?P<wcs>CS))? by|"
                        r"(?P<unf>Unfavorable) by|Submitted as Committee Bill and (?P<sub>Reported Favorably) by|"
                        r"Recommendation: (?P<rec>Favorable) by)-?\s*(?P<c>.+?)(?:\s*\([\d, ]+\))?(?:;\s*YEAS.*)?$", t)
        if mrep and not re.search(r"read 1st time$", t):
            c = comm_name(mrep.group("c"))
            ty = tally(t)
            if mrep.group("unf"):
                if hh == origin and c == first_ref:
                    defeated_first = True
                steps.append((d, hh, f"The {c} Committee voted it down" + (f", {ty[0]}-{ty[1]}" if ty else ""), "commfail"))
                v = take("C", hh, d, *(ty or (None, None)), comm_=c)
                if v or ty:
                    fvotes.append([hh, "C", c, d, (v or {}).get("y", ty[0] if ty else 0), (v or {}).get("n", ty[1] if ty else 0),
                                   dedupe_seats(v["members"], hh) if v else []])
                continue
            reported.add((hh, c))
            if mrep.group("rec"):
                what = "recommended it to the full committee"
            elif mrep.group("cs") or mrep.group("wcs"):
                what = "approved it as a committee substitute (rewritten)"
            elif mrep.group("am") or "amendment" in t:
                what = "approved it with amendments"
            elif mrep.group("sub"):
                what = "introduced it as its own bill"
            else:
                what = "approved it"
            steps.append((d, hh, "REPORTED", "reported"))
            steps.append((d, hh, f"The {c} Committee {what}" + (f", {ty[0]}-{ty[1]}" if ty else ""), "report"))
            if c in queue[hh]:
                queue[hh].remove(c)
            v = take("C", hh, d, *(ty or (None, None)), comm_=c)
            if v or ty:
                fvotes.append([hh, "C", c, d, ty[0] if ty else v["y"], ty[1] if ty else v["n"],
                               dedupe_seats(v["members"], hh) if v else []])
            continue
        if re.match(r"(?:Reported out of|Submitted for consideration by|Temporarily postponed by|Removed from Meeting Agenda)", t):
            steps.append((d, hh, t, "routine" if t.startswith(("Reported out", "Submitted for")) else "other"))
            continue
        mw = re.match(r"Withdrawn from-?\s*(.+)$", t)
        if mw:
            c = comm_name(mw.group(1))
            if c in queue[hh]:
                queue[hh].remove(c)
            if comm == c and where == hh:
                comm = None
                place = "committee" if queue[hh] else "floor"
                if queue[hh]:
                    comm = queue[hh][0]
            steps.append((d, hh, f"Withdrawn from the {c} Committee", "withdrawn"))
            continue
        if re.match(r"(?:Placed on (?:Calendar|Special Order Calendar|Local Calendar|3rd reading)|Bill (?:released|referred) to House "
                    r"Calendar|Added to (?:Second|Third) Reading Calendar|Bill added to Special Order Calendar|Retained on "
                    r"(?:Special Order )?Calendar)", t):
            if hh == where or not (hh in passed):
                where = hh
                if not (hh == origin and origin in passed):
                    place, comm = "floor", None
            nice = re.sub(r"\s*--If Received$", "", t)
            steps.append((d, hh, nice, "calendar"))
            continue
        if re.match(r"(?:Read (?:2nd|3rd) time|Immediately certified|Senate Message List|In Possession List|Pending reference "
                    r"review|Pending withdrawal|CS Filed|Ordered engrossed$|Laid on Table under Rule)", t):
            steps.append((d, hh, t, "routine"))
            continue
        msub = re.match(r"Substituted for (.+)$", t)
        if msub:
            r_ = bill_ref(msub.group(1))
            where, place, comm = hh, "floor", None
            steps.append((d, hh, f"Took the place of its companion, {spaced(r_)}" if r_ else t, "subfor"))
            continue
        msb = re.match(r"Substituted (.+)$", t)
        if msb:
            r_ = bill_ref(msb.group(1))
            replaced_by = replaced_by or r_
            steps.append((d, hh, f"Replaced by its companion, {spaced(r_)}" if r_ else t, "replaced"))
            continue
        mlt = re.match(r"(?:Original bill )?[Ll]aid on Table(.*)$", t)
        if mlt:
            see = re.search(r"see (.+?)(?: \(|$)|refer to combined (.+)$", mlt.group(1))
            r_ = bill_ref(see.group(1) or see.group(2)) if see else ""
            if r_:
                replaced_by = replaced_by or r_
                steps.append((d, hh, f"Laid on the table: {spaced(r_)} passed instead", "tabled"))
            else:
                steps.append((d, hh, "Laid on the table", "tabled"))
            continue
        if re.match(r"CS combines this bill with", t):
            steps.append((d, hh, t, "other"))
            continue
        if re.match(r"In (?:returning )?[Mm]essages$", t):
            if hh != where:
                where = hh
                if hh == origin and other in passed:
                    steps.append((d, hh, f"Back in the {HOUSE[hh]}", "back"))
                else:
                    steps.append((d, hh, f"Received in the {HOUSE[hh]}", "received"))
                    place, comm = "desk", None
            continue
        if t == "Received":
            continue
        if re.match(r"Reconsidered$", t):
            prev = [s for s in steps if s[1] == hh and s[3] != "routine"]
            if prev and prev[-1][3] in ("pass", "fail"):
                if prev[-1][3] == "pass":
                    passed.discard(hh)
                    amended_by.discard(hh)
                    fvotes.reverse()
                    for j, fv in enumerate(fvotes):
                        if fv[0] == hh and fv[1] == "F":
                            del fvotes[j]
                            break
                    fvotes.reverse()
                else:
                    failed = None
                steps.append((d, hh, f"The {HOUSE[hh]} voted to reconsider its vote", "reconsider"))
            else:
                steps.append((d, hh, "Reconsidered", "routine"))
            continue
        mp = re.match(r"(?:(?:CS/)*CS )?([Pp]assed|failed to pass|[Ff]ailed)( as amended)?( by Conference Committee Report)?;\s*YEAS", t)
        if mp and not re.match(r"Veto|Line Item", t):
            y, n = tally(t)
            v = take("F", hh, d, y, n)
            fv = [hh, "F", None, d, y, n, dedupe_seats(v["members"], hh) if v else []]
            if mp.group(1).lower().startswith("fail"):
                failed = (d, hh, y, n)
                fvotes.append(fv)
                steps.append((d, hh, f"The {HOUSE[hh]} voted it down, {y}-{n}", "fail"))
                continue
            failed = None
            fvotes.append(fv)
            where = hh
            ccr = bool(mp.group(3))
            if hh not in passed and not (hh == origin and other in passed):
                passed.add(hh)
                if hh == other and mp.group(2):
                    amended_by.add(hh)
                if hh == origin:
                    place, comm = "desk", None
                steps.append((d, hh, f"PASSED {HOUSE[hh].upper()}", "pass"))
                steps.append((d, hh, f"The {HOUSE[hh]} vote: {y}-{n}" + (" (as amended)" if mp.group(2) else ""), "tally"))
            else:
                passed.add(hh)
                prior = [s for s in steps if s[1] == hh and s[3] in ("concur", "ccr")]
                if hh == origin and prior:
                    concurred = True
                steps.append((d, hh, f"The {HOUSE[hh]} passed it again, {y}-{n}" +
                              (" (as the conference committee proposed)" if ccr else " (with the other house's changes)" if prior else ""), "final"))
            continue
        if re.match(r"(?:Concurred in|Amendment \d+ Concur$)", t):
            further = bool(re.search(r"as amended", t))
            steps.append((d, hh, f"The {HOUSE[hh]} agreed to the {HOUSE[OTHER[hh]]}'s changes" + (", with further changes" if further else ""), "concur"))
            continue
        if re.match(r"(?:Refused to concur|Amendment \d+ Refuse to Concur|Refused to recede|Insist)", t):
            steps.append((d, hh, t, "noconcur"))
            continue
        if re.match(r"(?:Receded from|Amendment \d+ Recede|Requested (?:House|Senate) to recede)", t):
            steps.append((d, hh, t, "recede" if t.startswith(("Receded", "Amendment")) else "other"))
            continue
        if re.search(r"Conference Committee Report adopted", t):
            steps.append((d, hh, f"The {HOUSE[hh]} adopted the conference committee's report", "ccr"))
            continue
        if re.match(r"(?:Ordered enrolled|Ordered engrossed, then enrolled)", t):
            enrolled = True
            steps.append((d, hh, "Passed both houses (ordered enrolled)", "enrolled"))
            continue
        if re.match(r"Signed by Officers and presented to Governor", t):
            sent = sent or not const
            steps.append((d, "G", "DELIVERED TO GOVERNOR", "sent"))
            continue
        if re.match(r"Signed by Officers and filed with Secretary of State", t):
            to_sos = True
            steps.append((d, "G", "Filed with the Secretary of State, for the voters at the next general election", "sos"))
            continue
        if re.match(r"Approved by Governor", t):
            law = law or not const
            steps.append((d, "G", "SIGNED BY THE GOVERNOR", "signed"))
            continue
        if re.search(r"become Law without Governor's Signature", t, re.I):
            law = law or not const
            steps.append((d, "G", "Became law without the governor's signature", "nosign"))
            continue
        if re.match(r"Governor vetoed specific Line Item", t):
            items = True
            steps.append((d, "G", "The governor vetoed items in it (a line-item veto)", "itemveto"))
            continue
        if re.match(r"Vetoed by Governor", t):
            vetoed = True
            steps.append((d, "G", "VETOED", "vetoed"))
            continue
        mov = re.match(r"Veto overridden", t)
        if mov:
            ty = tally(t)
            if vetoed and not items:
                overrides.add(hh)
            steps.append((d, hh, f"The {HOUSE[hh]} voted to override the veto" + (f", {ty[0]}-{ty[1]}" if ty else "") +
                          (" (items of it)" if items else ""), "override"))
            continue
        if re.match(r"(?:Line Item )?Veto [Mm]essage transmitted to Secretary of State", t):
            steps.append((d, "G", "The veto stands: the veto message went to the Secretary of State" if not items else
                          "The vetoed items stand: the veto message went to the Secretary of State", "vetofinal"))
            continue
        mv = re.match(r"(?:Line Item )?Veto Message received(?: \((.+)\))?", t)
        if mv:
            regular = re.findall(r"(\d{4}) Regular Session", mv.group(1) or "")
            steps.append((d, hh, f"The {HOUSE[hh]} received the veto message" + (f", for the {regular[-1]} session to take up" if regular else ""), "vetomsg"))
            continue
        md = re.match(r"Died (in|on|pending) ?(.*?)(?:[,;] [Cc]ompanion bill.*)?$", t)
        if md:
            what = md.group(2)
            if md.group(1) == "in" and not re.match(r"(?:Conference Committee|Messages|returning Messages)$", what):
                c = comm_name(what)
                comm, place, where = c, "committee", hh
                steps.append((d, hh, f"Died in the {c} Committee", "died"))
            elif md.group(1) == "on":
                if not (hh in passed):
                    place, comm, where = "floor", None, hh
                steps.append((d, hh, f"Died on the {HOUSE[hh]} calendar", "died"))
            elif md.group(1) == "pending":
                steps.append((d, hh, "Died waiting for the committees' reference review", "died"))
            else:
                steps.append((d, hh, f"Died in {'the conference committee' if what.startswith('Conference') else 'messages between the houses'}", "died"))
            see = re.search(r"see (.+?)(?: \(|$)", t)
            if see and bill_ref(see.group(1)) and bill_ref(see.group(1)) != p:
                steps.append((d, hh, f"Its companion, {spaced(bill_ref(see.group(1)))}, passed instead", "other"))
            continue
        if re.match(r"Indefinitely postponed and withdrawn from consideration", t):
            steps.append((d, hh, "Withdrawn from consideration at the end of the session", "routine"))
            continue
        # Amendments, motions, conference committees and other lines: as written.
        steps.append((d, hh if h else "G", t, "other"))

    if law and vetoed and not items and overrides < {"S", "H"}:
        law = False  # (a chapter line after a veto: none seen)
    if vetoed and overrides >= {"S", "H"}:
        law = True
    both = enrolled or sent or law or vetoed or (const and to_sos)
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

    title = b["short"] or b["label"]
    desc = description(b)
    topics = ["const"] if const else []
    for h_, c in refs:
        tp = P.COMMITTEE_TOPICS.get(c)
        if tp and tp not in topics:
            topics.append(tp)
    if len(topics) <= (1 if const else 0):
        topics += [k for k, rx in P.TOPIC_WORDS.items() if rx.search(f"{title} {desc[:300]}") and k not in topics]
    topics = list(dict.fromkeys(t for t in topics if t != "const" or const))

    # Sponsors in order. Committees come first on a committee substitute ("State Affairs Committee; Persons-Mulicka"):
    # the sponsor is the first member; a committee's own bill has the committee as its sponsor.
    first_day = min((a[0] for a in acts), default=f"{session}-01-01")
    people, comms_by = [], []
    for name, co in b["sponsors"]:
        hit = sponsor_of(term, origin, name, first_day)
        if hit:
            people.append((hit, co))
            if hit[2] in ("R", "D"):
                parties[(origin, hit[0])] = hit[2]
        else:
            comms_by.append(name)
    primes = [x for x, co in people if not co]
    if people:
        sponsor, district = people[0][0][0], people[0][0][1]
        cos = [x[0] for x, _ in people[1:] if x[0] != sponsor]
        nprimes = max(1, len(primes))
    else:
        cn = comm_name(comms_by[0]) if comms_by else ""
        sponsor, district = (f"{HOUSE[origin]} {cn} Committee" if cn else "—"), None
        cos, nprimes = [], 1

    if stage == 0:
        dsc = f"In {HOUSE[where]} committee" if place == "committee" else "Filed"
    elif stage == 1:
        dsc = f"On the {HOUSE[where]} floor"
    else:
        dsc = {2: f"Passed the {HOUSE[origin] if origin in passed else HOUSE[other]}", 3: "Passed both houses",
               4: "On the governor's desk", 5: "Became law", 6: "Vetoed"}[stage]
        if const and stage == 3:
            dsc = "Passed both houses: on the ballot"
    comm_now = comm if place == "committee" and stage in (0, 2) else None

    def dates(test, mode="last"):
        ds = sorted({s[0] for s in steps if test(s) and s[0]})
        return {"first": ds[0], "last": ds[-1], "all": ";".join(ds)}[mode] if ds else ""

    action_dates = [s[0] for s in steps if s[0]]
    origin_reported = any(h_ == origin for h_, _ in reported)
    left_first = bool(first_ref and ((origin, first_ref) in reported or origin in passed))
    rec = {
        "nums": [p], "base": [p], "prev": earlier(session, b),
        "title": title, "summary": desc, "act": "", "lawCode": "", "law": None, "laws": [],
        "comms": sorted({f"{h_} · {c}" for h_, c in refs}), "topics": topics, "places": [],
        "narrow": narrow(b), "kind": b.get("kind") or "",
        "commFate": "passed" if origin_reported or origin in passed else "defeated" if defeated_first else "none",
        "mainTopic": topics[0] if topics else "",
        "local": narrow(b) == "place" or "local" in topics, "senDeleg": False, "asmDeleg": False,
        "budget": is_budget(p, title) and not const,
        "passedS": "S" in passed, "passedA": "H" in passed, "program": None,
        "stage": stage, "passedIn": (HOUSE[origin] if origin in passed else HOUSE[other]) if stage == 2 else None,
        "chapter": chapter if stage == 5 else None,
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
            dates(lambda s: s[3] == "sent") if stage >= 4 else "",
            dates(lambda s: s[3] in ("signed", "nosign", "chapter", "override")) if stage == 5 else "",
            dates(lambda s: s[3] == "vetoed"),
        ],
        "votes": fvotes, "firstComms": [(origin, first_ref, left_first)] if first_ref else [],
        "vers": [{"p": p, "sponsor": sponsor, "district": district or 0, "cosponsors": cos,
                  "primes": nprimes, "cosp": len(cos), "statusDesc": dsc, "committee": comm_now,
                  "actions": [[s[0], s[2]] for s in steps if s[3] != "routine" or s[2].startswith("Now in")]}],
        "source": b["source"],
    }
    if stage == 5 and not rec["keyDates"][5]:
        rec["keyDates"][5] = rec["last"]
    return rec, what_it_does(session, b, desc)


# ---- What it does ----

def paragraphs(lines):
    """pdftotext lines -> paragraphs: a line ending a sentence well short of the column, or a bullet, ends one."""
    out, cur = [], []
    width = max((len(l) for l in lines), default=80)
    for l in lines:
        l = l.strip()
        if not l:
            if cur:
                out.append(" ".join(cur))
                cur = []
            continue
        if re.match(r"[••-]\s", l) and cur:
            out.append(" ".join(cur))
            cur = []
        cur.append(re.sub(r"^[••]\s*", "• ", l))
        if re.search(r"[.:;]$", l) and len(l) < width * 0.8:
            out.append(" ".join(cur))
            cur = []
    if cur:
        out.append(" ".join(cur))
    return [re.sub(r"\s+", " ", x).strip() for x in out if x.strip()]


FURNITURE = re.compile(r"^(?:BILL:.*|[IVX]+\.|Page \d+|STORAGE NAME:.*|DATE:.*|\d+|JUMP TO|SUMMARY|ANALYSIS|RELEVANT INFORMATION|"
                       r"BILL HISTORY|PAGE: \d+)$")


def analysis_summary(a):
    """The summary of a staff analysis's text: the House's "Effect of the Bill:" (to "Fiscal or Economic Impact:"), or
    its older "SUMMARY ANALYSIS"; the Senate's "I. Summary:" (to "II. Present Situation:")."""
    t = (a.get("text") or "").replace("\r", "")
    m = re.search(r"Effect of the Bill:\s*\n(.*?)\n\s*Fiscal or Economic Impact:", t, re.S) \
        or re.search(r"SUMMARY ANALYSIS\s*\n(.*?)(?:\n\s*This document does not reflect|\n\s*FULL ANALYSIS|\n\s*I\.\s+SUBSTANTIVE)", t, re.S) \
        or re.search(r"\bI\.\s*Summary:\s*\n(.*?)\n\s*Present Situation:", t, re.S)
    if not m:
        return ""
    lines = [l for l in m.group(1).split("\n") if not FURNITURE.match(l.strip())]
    ps = paragraphs(lines)
    out = "\n".join(ps)
    if len(out) > 3500:
        cut = out[:3500]
        out = cut[:cut.rfind(". ") + 1] if ". " in cut else cut
    return out.strip()


def what_it_does(session, b, desc):
    a = load(os.path.join(folder(session), "analyses", f"{b['key']}.json"))
    if a:
        s = analysis_summary(a)
        if s and len(s) > 60:
            house = "Senate" if re.search(r"/\d{4}s\d", a.get("path") or "") or "Fiscal Impact" in (a.get("type") or "") \
                or (a.get("text") or "")[:200].find("The Florida Senate") >= 0 else "House"
            author = re.sub(r"\s*\((?:Post-Meeting|Pre-Meeting|Final)\)\s*$", "", a.get("author") or "").strip()
            when = ""
            try:
                when = datetime.fromisoformat(a["posted"]).strftime("%B %-d, %Y") if a.get("posted") else ""
            except ValueError:
                pass
            final = "Final" in (a.get("type") or "") or "final" in (a.get("author") or "").lower()
            label = (f"From the {house} staff's {'final bill analysis' if final else 'bill analysis'}"
                     + (f" for the {author}" if author and not final else "") + (f" ({when})" if when else "") + ".")
            return {"statement": s, "label": label}
    # Without an analysis there's nothing more to say: the one-line description is already the bill's summary line
    # (shown under its title), and repeating it as "What it does" would show the same text twice.
    return None


# ---- A session ----

def load_session(session):
    """Read one year's bills: (records, bill number -> record index, fetched time, delegation)."""
    k = (session, "loaded")
    if k in _CACHE:
        return _CACHE[k]
    parties = _PARTIES.setdefault(session, {})
    recs, index, whats = [], {}, {}
    for key in keys(session):
        b = bill(session, key)
        if not b:
            continue
        rec, what = record(session, b, parties)
        if not rec:
            continue
        index[key] = len(recs)
        recs.append(rec)
        if what:
            whats[key] = what
    try:
        with open(os.path.join(P.DATA, f"texts_{session}.json"), "w") as f:
            json.dump(whats, f, ensure_ascii=False)
    except OSError:
        pass
    paths = [os.path.join(folder(session), n) for n in ("state.json", "list.json", "openstates.json")]
    times = [os.path.getmtime(x) for x in paths if os.path.exists(x)]
    fetched = datetime.fromtimestamp(max(times), ZoneInfo(P.TIMEZONE)).strftime("%Y-%m-%d %H:%M") if times else ""
    _CACHE[k] = (recs, index, fetched, {"SENATE": [], "ASSEMBLY": []})
    return _CACHE[k]


# ---- Earlier years ----

_KEYS = {}


def _norm(s):
    return re.sub(r"[^a-z0-9 ]", "", re.sub(r"\s+", " ", (s or "").lower())).strip()


def _sponsor_last(b):
    for name, co in b["sponsors"]:
        if not re.search(r"Committee|Subcommittee", name) and not co:
            return fold(name.partition(",")[0])
    return ""


def _is_law(b):
    return any(CHAPTER.search(t) and t.startswith("Chapter") for _, _, t in b["actions"])


def _keys(session):
    """A year's bills that didn't become law: (title|sponsor -> [bills], description -> [bills])."""
    if session not in _KEYS:
        by_title, by_desc = defaultdict(list), defaultdict(list)
        for k in keys(session):
            b = bill(session, k)
            if not b or _is_law(b) or is_budget(k, b["short"]):
                continue
            tk, dk = _title_key(b), _desc_key(b)
            if tk:
                by_title[tk].append(k)
            if dk:
                by_desc[dk].append(k)
        _KEYS[session] = (by_title, by_desc)
    return _KEYS[session]


def _title_key(b):
    t = _norm(b["short"])
    if len(t.split()) < 3 or not _sponsor_last(b):
        return ""
    return t + "|" + _sponsor_last(b)


def _desc_key(b):
    d = _norm(description(b))
    return d if len(d.split()) >= 12 else ""


def earlier(session, b):
    """The same bill in the two years before: the same short title and first sponsor, or the same one-line description
    word for word, held by one bill in each year. Never a law, a budget bill or a claim bill's yearly title alone."""
    out = set()
    if is_budget(b["key"], b["short"]):
        return out
    tk, dk = _title_key(b), _desc_key(b)
    mine_t, mine_d = _keys(session)
    for y in (session - 1, session - 2):
        if y not in sessions():
            continue
        by_title, by_desc = _keys(y)
        for key, old, mine in ((tk, by_title, mine_t), (dk, by_desc, mine_d)):
            if key and len(old.get(key, [])) == 1 and len(mine.get(key, [])) <= 1:
                out.add((y, old[key][0]))
                break
    return out


def parties(session, recs):
    if session not in _PARTIES:
        load_session(session)
    return {k: v for k, v in _PARTIES.get(session, {}).items() if v in ("D", "R")}


def agendas(session):
    """Bills on upcoming Senate committee agendas ("On Committee agenda-- Criminal Justice, 04/01/25, 1:30 pm, ..."):
    bill -> [["Senate Criminal Justice", "2025-04-01T13:30:00"], ...]. (The House's lines give no date.)"""
    today = date.today().isoformat()
    out = {}
    for k in keys(session):
        b = bill(session, k)
        for d, h, t in (b or {}).get("actions") or []:
            m = re.match(r"On Committee agenda--\s*(.+?), (\d+/\d+/\d+), (\d+:\d+ [ap]m)", t)
            if not m:
                continue
            day = iso(m.group(2))
            if day < today:
                continue
            try:
                when = datetime.strptime(f"{day} {m.group(3)}", "%Y-%m-%d %I:%M %p").strftime("%Y-%m-%dT%H:%M:%S")
            except ValueError:
                when = f"{day}T00:00:00"
            entry = [f"{HOUSE.get(h or 'S')} {comm_name(m.group(1))}", when]
            if entry not in out.setdefault(k, []):
                out[k].append(entry)
    return out


# ---- Checks ----

def list_outcome(last):
    """The Senate's list's last action -> "law", "veto", "sos" or ""."""
    if re.search(r"Chapter No\.", last or ""):
        return "law"
    if re.search(r"Vetoed by Governor|Veto Message", last or "") and not re.search(r"Line Item", last or ""):
        return "veto"
    if re.search(r"filed with Secretary of State", last or ""):
        return "sos"
    return ""


def checks(session):
    """Laws and vetoes compared with the last action on the Senate's bill list, bill for bill (laws: a chapter number;
    vetoes: the veto or its message last)."""
    recs = load_session(session)[0]
    lst = listing(session).get("bills") or {}
    by = {r["nums"][0]: r for r in recs}
    items = sorted(k for k, r in by.items() if any("line-item veto" in a[1] for a in r["vers"][0]["actions"]))
    laws = {k for k, v in lst.items() if (list_outcome(v.get("last")) == "law" or k in items) and k in by}
    vetoes = {k for k, v in lst.items() if list_outcome(v.get("last")) == "veto" and k in by and k not in items}
    mine_law = {k for k, r in by.items() if r["stage"] == 5}
    mine_veto = {k for k, r in by.items() if r["stage"] == 6}
    return {"laws": len(mine_law), "list laws": len(laws), "laws not on the list": sorted(mine_law - laws),
            "listed laws not here": sorted(laws - mine_law), "vetoes": len(mine_veto), "list vetoes": len(vetoes),
            "vetoes not on the list": sorted(mine_veto - vetoes), "listed vetoes not here": sorted(vetoes - mine_veto),
            "line items": items, "amendments to the voters": sorted(k for k, r in by.items() if "const" in r["topics"] and r["stage"] == 3),
            "from pages": sum(r["source"] == "page" for r in recs), "from Open States": sum(r["source"] == "openstates" for r in recs)}


def compare(session):
    """Every bill with both an official page and an Open States record, converted both ways: the stages that differ."""
    diff, n = [], 0
    for k in keys(session):
        a, o = from_page(session, k), from_openstates(session, k)
        if not (a and o):
            continue
        ra, ro = record(session, a, {})[0], record(session, o, {})[0]
        if not ra or not ro:
            if bool(ra) != bool(ro):
                diff.append((k, "left out one way"))
            continue
        n += 1
        if (ra["stage"], ra["passedS"], ra["passedA"], ra["comm"]) != (ro["stage"], ro["passedS"], ro["passedA"], ro["comm"]):
            diff.append((k, (ra["stage"], ra["passedS"], ra["passedA"], ra["comm"]), (ro["stage"], ro["passedS"], ro["passedA"], ro["comm"])))
    return n, diff


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "compare":
        n, diff = compare(int(sys.argv[2]))
        print(f"{n} bills compared; {len(diff)} differ")
        for d in diff:
            print(" ", d)
    else:
        for s in sessions():
            print(s, json.dumps(checks(s)))
