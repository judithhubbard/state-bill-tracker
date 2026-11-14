"""Louisiana's bills (downloaded by states/la/fetch.py from legis.la.gov) in the shape build_data.py reads. A page a year:
the Legislature meets once a year, a general session in even years and a fiscal session in odd years, and bills die when
it ends. House and Senate bills (HB, SB); constitutional amendments are bills too (the site's list of them, or
"(Constitutional Amendment)" / "Constitutional amendment" in the title): two-thirds of each house's members, then the
voters, never the governor. Special sessions and resolutions are left out.

Each bill (data/la/<year>/bills/HB1.json) has its title ("APPROPRIATIONS: Provides for ..."), authors in order (each with
a link to the member's page, which names the district), its documents and its history, newest first, each line with its
house and date. The steps, read in date order (the page's order kept within a day):
- "Prefiled." / "Under the rules, provisionally referred to the Committee on X." (the House) / "Prefiled and under the
  rules provisionally referred to ..." (the Senate); "Read by title, under the rules, referred to the Committee on X." (the
  House's introduction, or the referral of a Senate bill), "Introduced in the Senate; read by title. Rules suspended. Read
  second time and referred to the Committee on X." (a Senate bill), "Read second time by title and referred to ..." (a
  House bill in the Senate). "Received in the House from the Senate ..." / "Received in the Senate ..." (the second house).
- Committee reports: "Reported favorably (11-0)." / "Reported with amendments (8-3)." (the House's, with the tally),
  "Reported favorably." / "Reported with amendments." (the Senate's, without), "Reported by substitute" (the committee
  wrote a new bill: "Becomes HB 694." / "Title of substitute read and adopted; becomes Senate Bill No. 400." on the old
  one, which ends), "... To be recommitted to the Committee on Appropriations" and then "Read by title, ...,
  recommitted to the Committee on X." (a second committee: money bills go to Appropriations or Ways and Means in the House,
  Finance or Revenue and Fiscal Affairs in the Senate), "Involuntarily deferred in committee." (killed). "Reported
  with(out) Legislative Bureau amendments" is the Legislative Bureau's technical review, not a committee vote.
- Floor: "passed to 3rd reading", "returned to the calendar", "Scheduled for floor debate"; the passage: "Read third
  time by title, roll called on final passage, yeas 99, nays 0. Finally passed, ..." (the House; constitutional
  amendments and some others "having received two-thirds vote of the elected members"), "Read by title, passed by a vote
  of 39 yeas and 0 nays, and sent to the House." (the Senate); "Failed to pass" / "failed to pass by a vote of" (lost),
  "Reconsidered." (the house undoes its last vote).
- The other house's changes: "Received from the Senate with amendments." (back in the first house) or "without
  amendments" (passed both houses); "Senate amendments concurred in" / "Amendments proposed by the House read and
  concurred in"; "rejected" leads to a conference committee, whose report both houses have to adopt ("The Conference
  Committee Report was adopted" / "Conference Committee Report read; adopted by a vote of"). "Enrolled and signed by the
  Speaker" / "Enrolled. Signed by the President of the Senate." is passed both houses.
- The governor: "Sent to the Governor ...", "Signed by the Governor. Becomes Act No. 1." ("with one or more line-item
  vetoes": appropriation bills), "Becomes Act No. 300 without the Governor's signature.", "Vetoed by the Governor." /
  "Veto message (from the Governor) received and read." (a veto during the session goes back to the house that wrote
  it, which can reconsider it). Constitutional amendments are "Taken by the Clerk of the House and presented to the
  Secretary of State" / "Sent to the Secretary of State by the Secretary of the Senate" and get an Act number too
  ("Becomes Act No. 406."), but aren't laws: they go to the voters.
Laws, vetoes and line-item vetoes are checked against the Legislature's list of vetoed bills and the Act numbers (which
run 1-N through laws and amendments with none missing): `checks()` (python3 -m states.la.convert).

Votes: floor votes member by member from the vote PDFs read as text (votes/<doc>.json: YEAS, NAYS and ABSENT, surnames,
"Carter, R." for shared ones, "Mr. Speaker", "Mr. President"), matched to the history line by house, day and tally; where
the PDF isn't downloaded yet, the line's tally alone. Committee votes member by member from 2026 (cvotes/<moi>.json,
"Yea"/"Nay"/"Abstain"); the House's committee reports' tallies otherwise. Names are tied to today's members' seats within
the house (accents and suffixes aside: "Galle" is Gallé, Jr.; "Barthelemy" is Barthelemy II), never to a member first
elected after the session; members who left (Stagni, Wright, Selders in 2026) stay names.
"What it does" is the bill's digest (data/la/<year>/docs/<doc>.txt): the résumé digest of the act as passed, else the
newest digest of the bill, written by the staff of the bill's house (House Legislative Services for House bills).
"""
import glob, json, os, re, unicodedata
from collections import Counter, defaultdict
from datetime import datetime
from zoneinfo import ZoneInfo

from states.la import profile as P

HOUSE = {"S": "Senate", "H": "House"}
OTHER = {"S": "H", "H": "S"}
SUFFIX = re.compile(r"^(?:jr|sr|ii|iii|iv|v)\.?$", re.I)
_CACHE, _PARTIES = {}, {}
UNREAD = Counter()


def folder(session):
    return os.path.join(P.DATA, str(session))


def sessions():
    out = []
    for f in sorted(os.listdir(P.DATA)) if os.path.isdir(P.DATA) else []:
        if re.fullmatch(r"\d{4}", f) and os.path.exists(os.path.join(P.DATA, f, "list.json")) \
                and os.path.isdir(os.path.join(P.DATA, f, "bills")):
            out.append(int(f))
    return out


def code(session):
    """2026 -> "26RS", the Legislature's code for a regular session."""
    return f"{session % 100:02d}RS"


def load(path, default=None):
    try:
        return json.load(open(path, encoding="utf-8"))
    except (OSError, ValueError):
        return default


def listing(session):
    k = (session, "list")
    if k not in _CACHE:
        _CACHE[k] = load(os.path.join(folder(session), "list.json"), {}) or {}
    return _CACHE[k]


def fold(s):
    """Lower case without accents: "Amedée" -> "amedee"."""
    return unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower().strip()


def bill(session, key):
    """A bill's record with its history oldest first (the page lists it newest first; sorted by day, the page's order
    kept within a day)."""
    k = (session, "bill", key)
    if k not in _CACHE:
        b = load(os.path.join(folder(session), "bills", f"{key}.json"))
        if b:
            rows = [(h.get("day") or "", i, h) for i, h in enumerate(reversed(b.get("history") or []))]
            rows.sort(key=lambda r: (r[0], r[1]))
            b["hist"] = [(d, (h.get("chamber") or "").upper(), re.sub(r"\s+", " ", h.get("action") or "").strip()) for d, _, h in rows]
        _CACHE[k] = b
    return _CACHE[k]


# ---- Members and names ----

def split_name(n):
    """The member list's "Last, [Suffix,] Given" -> (folded surname, set of the given names' initials): "Cox, III, Vincent
    E." -> ("cox", {"v", "e"}); "Barthelemy II, Sidney" -> ("barthelemy", {"s"}); "Landry, Jr. Terry" -> ("landry",
    {"t"}); 'Wiley, Jeffrey "Jeff"' -> ("wiley", {"j"})."""
    parts = [p.strip() for p in (n or "").split(",")]
    last = " ".join(w for w in parts[0].split() if not SUFFIX.match(w))
    given = [w.strip('"“”') for p in parts[1:] for w in p.split() if not SUFFIX.match(w.strip('"“”'))]
    return fold(last), {fold(w)[:1] for w in given if fold(w)[:1].isalpha()}


def clean_author(n):
    """"Kyle M. Green , Jr." -> "Kyle M. Green, Jr."; 'John "Big John" Illg , Jr.' -> "John Illg, Jr."."""
    n = re.sub(r'\s*"[^"]*"\s*', " ", n or "")
    n = re.sub(r"\s+,", ",", re.sub(r"\s+", " ", n)).strip()
    return n


def author_last(n):
    words = [w for w in re.sub(r",", " ", clean_author(n)).split() if not SUFFIX.match(w)]
    return fold(words[-1]) if words else ""


def members():
    """Today's members (data/la/members.json), vacant seats left out, each with its seat ("S:12", "H:71": the Senate's 39
    and the House's 105 single-member districts), surname, initials, first year elected and party."""
    if "members" not in _CACHE:
        raw = (load(os.path.join(P.DATA, "members.json"), {}) or {}).get("members") or []
        out = []
        for m in raw:
            if m.get("vacant") or m.get("house") not in ("S", "H") or not m.get("district"):
                continue
            m = dict(m)
            m["seat"] = f"{m['house']}:{int(m['district'])}"
            m["last"], m["inits"] = split_name(m["name"])
            try:
                m["since"] = int(m.get("elected") or 0)
            except ValueError:
                m["since"] = 0
            m["p"] = "R" if m.get("party") == "Republican" else "D" if m.get("party") in ("Democrat", "Democratic") else ""
            out.append(m)
        _CACHE["members"] = out
        _CACHE["by_seat"] = {m["seat"]: m for m in out}
    return _CACHE["members"]


def by_seat(seat):
    members()
    return _CACHE["by_seat"].get(seat)


def names_of_authors():
    """Seat -> the name its member goes by as an author ("Tehmi Chassion", "Beau Beaullieu"), the most common across the
    sessions' bills, for a member whose surname matches."""
    if "author_names" not in _CACHE:
        seen = defaultdict(Counter)
        for s in sessions():
            for f in glob.glob(os.path.join(folder(s), "bills", "*.json")):
                b = load(f) or {}
                for a in b.get("authors") or []:
                    sid = page_seat(a.get("page"))
                    m = by_seat(sid) if sid else None
                    if m and author_matches(a.get("name"), m):
                        seen[sid][clean_author(a["name"])] += 1
        _CACHE["author_names"] = {sid: c.most_common(1)[0][0] for sid, c in seen.items()}
    return _CACHE["author_names"]


def page_seat(url):
    m = re.search(r"(H_Reps|smembers)[^?]*\?ID=(\d+)", url or "")
    return f"{'H' if m.group(1) == 'H_Reps' else 'S'}:{int(m.group(2))}" if m else None


def author_matches(name, m):
    """An author's name is the seat's member's: the member's surname ("st. blanc", "jackson-andrews") is in it."""
    a = " " + re.sub(r"[^a-z' .-]", " ", fold(clean_author(name))) + " "
    return bool(m["last"]) and f" {m['last']} " in a.replace(",", " ")


def display(m):
    """The name to show for a member: as an author, else the list's ("Adams, Roy Daryl" -> "Roy Daryl Adams"; a nickname
    in quotes is the first name: 'Firment, Michael "Gabe"' -> "Gabe Firment")."""
    n = names_of_authors().get(m["seat"])
    if n:
        return n
    parts = [p.strip() for p in m["name"].split(",")]
    sufs = [p for p in parts[1:] if SUFFIX.match(p)]
    given = " ".join(p for p in parts[1:] if not SUFFIX.match(p))
    nick = re.search(r'"([^"]+)"', given)
    first = nick.group(1) if nick else re.sub(r'\s*"[^"]*"', "", given).strip()
    return f"{first} {parts[0]}" + (f", {sufs[0]}" if sufs else "")


def vote_seat(session, h, name):
    """A roll-call name in a house -> today's member's seat, else "H?Name": "Mr. Speaker" is that year's Speaker, "Carter,
    R." a Carter whose given names start with R; never a member first elected after the session."""
    n = (name or "").strip()
    if n in ("Mr. Speaker", "Madam Speaker"):
        n = P.SPEAKERS.get(session, "")
    elif n in ("Mr. President", "Madam President"):
        n = P.PRESIDENTS.get(session, "")
    last, _, init = n.partition(",")
    last = " ".join(w for w in last.split() if not SUFFIX.match(w))
    init = fold(init.strip())[:1]
    hits = [m for m in members() if m["house"] == h and m["last"] == fold(last) and (not m["since"] or m["since"] <= session)]
    if init:
        hits = [m for m in hits if init in m["inits"]]
    if len(hits) == 1:
        return hits[0]["seat"]
    return f"{h}?{name.strip()}"


def author_of(session, h, a):
    """An author -> (name, district) for a sitting member who held the seat then (by the page's district and surname),
    else (the name as written, None)."""
    sid = page_seat(a.get("page"))
    m = by_seat(sid) if sid else None
    if m and author_matches(a.get("name"), m) and (not m["since"] or m["since"] <= session):
        return display(m), int(m["district"]), m["p"]
    return clean_author(a.get("name")), None, ""


# ---- Votes ----

def floor_votes(session):
    """(house letter, "HB1", day, yeas, nays) -> [vote records] from votes/*.json."""
    k = (session, "votes")
    if k not in _CACHE:
        out = defaultdict(list)
        for f in glob.glob(os.path.join(folder(session), "votes", "*.json")):
            v = load(f)
            if not v or v.get("house") not in ("House", "Senate"):
                continue
            try:
                mm, dd, yy = (v.get("date") or "").split("/")
                day = f"{int(yy)}-{int(mm):02d}-{int(dd):02d}"
            except ValueError:
                continue
            key = re.sub(r"\s+", "", v.get("bill") or "")
            t = v.get("totals") or {}
            out[(v["house"][0], key, day, int(t.get("YEAS") or 0), int(t.get("NAYS") or 0))].append(v)
        _CACHE[k] = out
    return _CACHE[k]


def roll(session, h, key, d, y, n):
    """A floor vote: [house, "F", None, day, yeas, noes, [[seat or name, "N"/"A"], ...]] (yes votes left out), member by
    member when its PDF has been read, else the tally alone."""
    hits = [v for v in floor_votes(session).get((h, key, d, y, n), [])
            if not re.search(r"CO-AUTHOR|AMENDMENT|MODIFY|RECOMMIT|RECONSIDER", v.get("motion") or "", re.I)]
    if not hits:
        return [h, "F", None, d, y, n, []]
    g = hits[0].get("groups") or {}
    names = [(x, "N") for x in g.get("NAYS") or []] + [(x, "A") for x in g.get("ABSENT") or []]
    everyone = [x for xs in g.values() for x in xs]
    seats = Counter(vote_seat(session, h, x) for x in everyone)
    listed = []
    for x, c in names:
        sid = vote_seat(session, h, x)
        listed.append([sid if "?" in sid or seats[sid] == 1 else f"{h}?{x}", c])
    return [h, "F", None, d, y, n, listed]


def committee_votes(session, b, h_of):
    """Committee votes member by member (2026 on): {(house, day): [house, "C", committee, day, yeas, noes, listed]} for the
    committee's final action on the bill when it was a recorded vote to report it ("Favorably", "Report with
    Amendments")."""
    out, defers = {}, []
    for doc in b.get("docs") or []:
        if not doc.get("moi"):
            continue
        cv = load(os.path.join(folder(session), "cvotes", f"{doc['moi']}.json"))
        if not cv:
            continue
        h = "S" if (cv.get("committee") or "").startswith("Senate") else "H"
        comm = comm_name(cv.get("committee"))
        try:
            day = datetime.strptime(cv.get("date") or "", "%B %d, %Y").strftime("%Y-%m-%d")
        except ValueError:
            continue
        for mo in cv.get("motions") or []:
            if mo.get("kind") != "Final":
                continue
            what = mo.get("motion") or ""
            if re.match(r"Defer", what, re.I):
                defers.append((day, h, comm, what))
                continue
            votes = mo.get("votes") or []
            if not votes or not re.match(r"(?:Report )?(?:Favorably|with Amendments|by Substitute)", what, re.I):
                continue
            code = {"Yea": "Y", "Nay": "N", "Abstain": "B", "Absent": "A"}
            y = sum(1 for _, x in votes if x == "Yea")
            n = sum(1 for _, x in votes if x == "Nay")
            listed = []
            for name, x in votes:
                if code.get(x, "A") == "Y":
                    continue
                last, _, given = name.partition(",")
                sid = vote_seat(session, h, f"{last}, {given.strip()[:1]}" if given.strip() else last)
                listed.append([sid, code.get(x, "A")])
            out[(h, day)] = [h, "C", comm, day, y, n, listed]
    return out, defers


# ---- Wording ----

def comm_name(c):
    """"the Committee on Senate and Governmental Affairs" / "House Committee on Judiciary" -> "Senate and Governmental
    Affairs" / "Judiciary"; "House & Governmental Affairs" -> "House and Governmental Affairs"."""
    c = re.sub(r"\s+", " ", (c or "").strip()).strip(" .")
    c = re.sub(r"\s*\(\d[\d-]*\)?\.?$", "", c)
    c = re.sub(r"^(?:the )?(?:House |Senate )?Committee on (?:the )?", "", c)
    c = c.replace(" & ", " and ")
    return c


def subject(title):
    """"PORTS/HARBORS/TERMINALS: Requires the board ... (2/3-CA6s43(3))(8/1/25)" -> ("PORTS/HARBORS/TERMINALS", "Requires
    the board ...") without the trailing notes (votes needed, effective dates, fiscal notes)."""
    t = re.sub(r"\s+", " ", title or "").strip()
    m = re.match(r"([A-Z0-9][A-Z0-9 &/'.,()-]{1,45}?):\s+(.*)$", t)
    kw, rest = (m.group(1).strip(), m.group(2)) if m else ("", t)
    while True:
        r2 = re.sub(r"\s*\((?:[^()]|\([^()]*\))*\)\s*$", "", rest)
        if r2 == rest:
            break
        rest = r2
    # A note left unclosed: "(2/3 - C13s1(A) (OR +$39,230 SD EX See Note"
    rest = re.sub(r"\s*\((?:2/3|OR |EN |EG |RE |RR |GF |SG |LF |SEE |gov |\d+/\d+/\d+)[^()]*(?:\([^()]*\))?[^()]*$", "", rest)
    return kw, rest.strip().rstrip(".")


def title_of(title, const):
    kw, t = subject(title)
    t = re.sub(r"^\(Constitutional Amendment\)\s*", "", t, flags=re.I)
    t = t[:1].upper() + t[1:]
    if const and not re.match(r"Constitutional amendment", t, re.I):
        t = f"Constitutional amendment: {t[:1].lower() + t[1:]}"
    t = re.sub(r"^Constitutional Amendment", "Constitutional amendment", t)
    return t


def keyword_text(kw):
    """"TAX/AD VALOREM" -> "Tax/ad valorem"."""
    kw = (kw or "").strip()
    return kw[:1] + kw[1:].lower() if kw else ""


def tally(t):
    """The yeas and nays in a line: "yeas 99, nays 0" (the House) or "39 yeas and 0 nays" (the Senate); "nays ." is 0."""
    m = re.search(r"yeas (\d+),? nays\s*(\d*)", t, re.I) or re.search(r"(\d+) yeas and (\d*) ?nays", t, re.I)
    if not m:
        return None
    return int(m.group(1)), int(m.group(2) or 0)


# ---- One bill ----

def record(session, b, parties):
    p = b["key"]
    lst = listing(session)
    origin = "H" if p.startswith("H") else "S"
    other = OTHER[origin]
    const = p in (lst.get("amendments") or []) or bool(re.search(r"\bConstitutional Amendment\b", b.get("title") or "", re.I))
    kw, short = subject(b.get("title") or (lst.get("bills", {}).get(p) or {}).get("title"))
    steps = []  # (date, house or "G", wording, kind)
    passed, amended_by, concurred = set(), set(), set()
    ccr = set()
    where, place, comm = origin, "desk", None
    reported, refs = set(), []
    first_ref, first_report = None, False
    intro = False
    enrolled = sent = law = vetoed = items = nosign = to_sos = withdrawn = False
    replaced = None
    defeated = None
    deferred = None
    chapter = None
    fvotes = []
    last_vote = {}  # house -> "pass" / "fail", for "Reconsidered."
    cvotes, defers = committee_votes(session, b, None)
    used_cv = set()

    def add(d, h, text, kind):
        steps.append((d, h, text, kind))

    def refer(d, h, c, kind="ref", provisional=False):
        nonlocal comm, place, first_ref, where, intro
        c = comm_name(c)
        if not c:
            return
        if h == origin and not intro and kind == "ref" and not provisional:
            intro = True
            add(d, h, f"Introduced in the {HOUSE[h]}", "intro")
        where = h
        if comm == c and place == "committee":
            return  # the prefiled referral, repeated at introduction
        comm, place = c, "committee"
        refs.append((h, c))
        if first_ref is None and h == origin:
            first_ref = c
        add(d, h, f"REFERRED TO {c.upper()}" if kind == "ref" else f"RECOMMITTED TO {c.upper()}", kind)

    def vote(d, h, t, kind):
        tl = tally(t)
        if not tl:
            return None
        v = roll(session, h, p, d, tl[0], tl[1])
        fvotes.append(v)
        return v

    for d, h, t in b["hist"]:
        h = h if h in ("H", "S") else where
        tl = t.lower()
        if not t or t == "Rules suspended.":
            continue
        # The governor.
        if re.match(r"Sent to the Governor", t, re.I):
            if not const:
                sent = True
                add(d, "G", "DELIVERED TO GOVERNOR", "sent")
            continue
        ma = re.search(r"Becomes Act No\. ?(\d+)", t, re.I)
        if re.match(r"Signed by the Governor", t, re.I) or ma:
            n = int(ma.group(1)) if ma else None
            if const:
                add(d, "G", f"Act No. {n} (sent to the voters)" if n else t, "other")
                continue
            if re.match(r"Signed by the Governor", t, re.I):
                law, vetoed, chapter = True, False, n or chapter
                add(d, "G", f"SIGNED BY THE GOVERNOR (Act {n})" if n else "SIGNED BY THE GOVERNOR", "signed")
                if re.search(r"line-item veto", t, re.I):
                    items = True
                    add(d, "G", "The governor vetoed items in it (a line-item veto)", "itemveto")
            elif re.search(r"without the Governor", t, re.I):
                law, nosign, vetoed, chapter = True, True, False, n
                add(d, "G", f"Became law without the governor's signature (Act {n})", "nosign")
            else:
                law, chapter = True, n
                add(d, "G", f"Became law (Act {n})", "nosign")
            continue
        if re.match(r"Vetoed by the Governor", t, re.I):
            if not const and not law:
                vetoed = True
                add(d, "G", "VETOED", "vetoed")
            continue
        if re.match(r"Veto message", t, re.I):
            if not const and not law and not vetoed:
                vetoed = True
                add(d, "G", "VETOED", "vetoed")
            add(d, h, f"The {HOUSE[h]} received the governor's veto message", "vetomsg")
            continue
        if re.search(r"notwithstanding the (?:veto|objections)|veto (?:was )?overridden|override", t, re.I):
            add(d, h, t, "override")
            UNREAD["(override) " + re.sub(r"\d+", "#", t)[:70]] += 1
            continue
        if re.search(r"Secretary of State", t, re.I):
            if const:
                to_sos = True
                add(d, h, "Sent to the Secretary of State, for the voters", "sos")
            else:
                add(d, h, t, "other")
            continue
        if re.match(r"Effective date", t, re.I):
            add(d, "G" if law else h, t, "effective")
            continue
        if re.match(r"(?:Enrolled and signed by the Speaker|Enrolled\. Signed by the President)", t, re.I):
            enrolled = True
            add(d, h, "Passed both houses (enrolled)", "enrolled")
            continue
        if re.match(r"Signed by the (?:Speaker|President)", t, re.I):
            add(d, h, re.sub(r" on \d+/\d+/\d+\.?$", "", t).rstrip("."), "signedby")
            continue
        # Prefiling, withdrawal, substitutes.
        if re.match(r"Prefiled", t, re.I):
            add(d, origin, "Prefiled", "prefiled")
            mpr = re.search(r"provisionally referred to the Committee on (.+?)\.?$", t, re.I)
            if mpr:
                refer(d, origin, mpr.group(1), provisional=True)
            continue
        mpr = re.match(r"Under the rules, provisionally referred to the Committee on (.+?)\.?$", t, re.I)
        if mpr:
            refer(d, origin, mpr.group(1), provisional=True)
            continue
        if re.search(r"withdrawn (?:prior to introduction|from the files)", t, re.I):
            withdrawn = True
            add(d, h, "Withdrawn by its author" + (" before it was introduced" if re.search(r"prior to introduction", t, re.I) else ""), "withdrawn")
            continue
        mb = re.match(r"Becomes (HB|SB) (\d+)\.?$", t, re.I) or re.search(r"becomes (House|Senate) Bill No\. (\d+)", t, re.I)
        if mb:
            replaced = f"{mb.group(1)[0].upper()}B {mb.group(2)}"
            add(d, h, f"Replaced by the committee's substitute, {replaced}", "replaced")
            continue
        msub = re.search(r"substitute for (HB|SB|House Bill|Senate Bill) No\. ?(\d+)", t, re.I)
        if msub:
            intro = True
            old = f"{msub.group(1)[0].upper()}B {msub.group(2)}"
            mc = re.search(r"reported by the Committee on (.+?)\.?$", t, re.I)
            c = comm_name(mc.group(1)) if mc else comm
            first_ref = first_ref or c
            if c:
                refs.append((h, c))
            reported.add(h)
            first_report = True
            place, comm = "floor", None
            add(d, h, f"Introduced as the {c + ' ' if c else ''}Committee's substitute for {old}", "intro")
            add(d, h, "REPORTED", "reported")
            continue
        # The second house receiving it, and the first house getting it back.
        mrec = re.match(r"Received in the (House|Senate)", t, re.I)
        if mrec:
            hh = mrec.group(1)[0].upper()
            where, place, comm = hh, "desk", None
            add(d, hh, f"Received in the {HOUSE[hh]}", "received")
            mr = re.search(r"referred to the Committee on (.+?)\.?$", t, re.I)
            if mr:
                refer(d, hh, mr.group(1))
            continue
        mback = re.match(r"Received from the (House|Senate) (with|without) amendments", t, re.I)
        if mback:
            hh = mback.group(1)[0].upper()
            where = OTHER[hh]
            if mback.group(2).lower() == "with":
                amended_by.add(hh)
                concurred.discard(OTHER[hh])
                add(d, where, f"Back from the {HOUSE[hh]}, which changed it: the {HOUSE[where]} has to agree", "askconcur")
            else:
                add(d, where, f"Back from the {HOUSE[hh]} without changes", "back")
            continue
        # Conference committees.
        if re.search(r"Conference Committee Report", t, re.I) and re.search(r"\badopted\b|\brejected\b|failed to be adopted|not adopted", t, re.I) \
                and not re.match(r"Notice", t, re.I):
            v = vote(d, h, t, "ccr")
            yes = re.search(r"was adopted|; adopted by|the Conference Committee Report was adopted", t, re.I) and not \
                re.search(r"not adopted|failed to be adopted|rejected|not having received", t, re.I)
            if yes:
                ccr.add(h)
                passed.add(h)
                add(d, h, f"The {HOUSE[h]} adopted the conference committee's report" + (f", {v[4]}-{v[5]}" if v else ""), "ccr")
            else:
                ccr.discard(h)
                add(d, h, f"The {HOUSE[h]} rejected the conference committee's report" + (f", {v[4]}-{v[5]}" if v else ""), "conf")
            continue
        if re.search(r"recommitted (?:the (?:bill|report) )?to (?:the )?Conference Committee|discharged (?:the |from )?(?:Conference|Comference)", t, re.I) \
                and not re.match(r"Notice", t, re.I):
            ccr.clear()
            add(d, h, t.rstrip("."), "conf")
            continue
        # Concurring in the other house's amendments.
        if re.search(r"(?:Senate amendments|Amendments proposed by the House|the amendments proposed by the Senate)", t, re.I) \
                and not re.match(r"Notice", t, re.I):
            v = vote(d, h, t, "concur")
            if re.search(r"concurred in", t, re.I) and not re.search(r"refused to concur|not concurred|failed to be concurred|rejected", t, re.I):
                concurred.add(h)
                amended_by.discard(OTHER[h])
                passed.add(h)
                add(d, h, f"The {HOUSE[h]} agreed to the {HOUSE[OTHER[h]]}'s changes" + (f", {v[4]}-{v[5]}" if v else ""), "concur")
            else:
                add(d, h, f"The {HOUSE[h]} refused to agree to the {HOUSE[OTHER[h]]}'s changes" + (f", {v[4]}-{v[5]}" if v else "")
                    + (" and asked for a conference committee" if re.search(r"conference", t, re.I) else ""), "noconcur")
            continue
        # Floor passage (or defeat).
        is_pass = re.search(r"roll called on final passage", t, re.I) or \
            (re.search(r"\bpassed by a vote of\b|failed to pass by a vote of", t, re.I) and not re.search(r"Motion to recommit", t, re.I))
        if is_pass:
            v = vote(d, h, t, "pass")
            tally_s = f"{v[4]}-{v[5]}" if v else ""
            if re.search(r"failed to pass", t, re.I):
                defeated = h
                last_vote[h] = "fail"
                need = {"H": 53, "S": 20}[h]
                add(d, h, f"The {HOUSE[h]} voted it down" + (f", {tally_s}" if tally_s else "")
                    + (" (it needed two-thirds of the members)" if re.search(r"two-thirds", t, re.I) else
                       f" (it needed {need} votes, a majority of the members)" if v and v[4] > v[5] else ""), "defeated")
                continue
            last_vote[h] = "pass"
            if defeated == h:
                defeated = None
            if h in passed:
                add(d, h, f"The {HOUSE[h]} passed it again" + (f", {tally_s}" if tally_s else ""), "final")
                continue
            passed.add(h)
            where = h
            if h == origin:
                place, comm = "desk", None
            add(d, h, f"PASSED {HOUSE[h].upper()}", "pass")
            add(d, h, f"The {HOUSE[h]} vote: {tally_s}" if tally_s else f"The {HOUSE[h]} vote", "tally")
            continue
        if re.match(r"(?:Read by title, )?reconsidered\b|Reconsidered\b", t, re.I) and not re.search(r"amendments were rejected", t, re.I):
            if vetoed and not law:
                add(d, h, f"The {HOUSE[h]} took up the vetoed bill (reconsidered it); no vote to override is recorded", "reconsider")
                continue
            if last_vote.get(h) == "pass" or re.search(r"by which .* passed", t, re.I):
                passed.discard(h)
                last_vote[h] = None
            elif last_vote.get(h) == "fail" and defeated == h:
                defeated = None
            add(d, h, f"The {HOUSE[h]} voted to reconsider its vote", "reconsider")
            if re.search(r"returned to the calendar", t, re.I):
                place = "floor"
            continue
        # Committee reports.
        mrep = re.match(r"(?:Rules suspended\. )?Reported (favorably|with amendments|by substitute|without amendments|without action)", t, re.I)
        if mrep:
            how = mrep.group(1).lower()
            c = comm
            reported.add(h)
            if h == origin:
                first_report = True
            mt = re.search(r"\((\d+)\s*-\s*(\d+)", t)
            cv = cvotes.get((h, d))
            if cv:
                fvotes.append(cv)
                used_cv.add((h, d))
            elif mt:
                fvotes.append([h, "C", c, d, int(mt.group(1)), int(mt.group(2)), []])
            add(d, h, "REPORTED", "reported")
            nxt = re.search(r"(?:To be recommitted|recommendation to recommit) to the Committee on (.+?)\.?$", t, re.I)
            word = {"favorably": "", "with amendments": " with amendments", "by substitute": " as a new bill (a substitute)",
                    "without amendments": "", "without action": " without action"}[how]
            add(d, h, f"The {c + ' ' if c else ''}Committee recommended it{word}" + (f", {mt.group(1)}-{mt.group(2)}" if mt else "")
                + (f", to go next to {comm_name(nxt.group(1))}" if nxt else ""), "report")
            place, comm = "floor", None
            if re.search(r"Committee amendments read and adopted", t, re.I):
                pass
            mrc = re.search(r"recommitted to the Committee on (.+?)\.?$", t, re.I)
            if mrc and not nxt:
                refer(d, h, mrc.group(1), "rereferred")
            elif re.search(r"passed to third reading|referred to the Legislative Bureau", t, re.I):
                place = "floor"
            continue
        if re.match(r"Involuntarily deferred", t, re.I):
            deferred = "involuntary"
            add(d, h, f"Deferred by the {comm + ' ' if comm else ''}Committee (involuntarily), which ends it for the session", "held")
            continue
        if re.search(r"Recalled from (?:the )?Committee", t, re.I):
            place, comm = "floor", None
            add(d, h, f"Taken from the committee (recalled) and put before the full {HOUSE[h]}", "discharged")
            continue
        mdis = re.match(r"Discharged from the Committee on (.+?)\.?$", t, re.I)
        if mdis:
            place, comm = "floor", None
            add(d, h, f"Taken from the {comm_name(mdis.group(1))} Committee (discharged) and put before the full {HOUSE[h]}", "discharged")
            continue
        mrc = re.search(r"recommitted to the Committee on (.+?)\.?$", t, re.I)
        if mrc:
            refer(d, h, mrc.group(1), "rereferred")
            continue
        mref = re.search(r"referred to the Committee on (.+?)\.?$", t, re.I)
        if mref and not re.search(r"Legislative Bureau", mref.group(1)):
            if h == origin and not intro and re.search(r"Introduced", t, re.I):
                intro = True
                add(d, h, f"Introduced in the {HOUSE[h]}", "intro")
            refer(d, h, mref.group(1))
            continue
        if re.match(r"Introduced in the Senate", t, re.I) or re.match(r"Rules suspended\. Introduced in the Senate", t, re.I):
            if not intro:
                intro = True
                add(d, h, f"Introduced in the {HOUSE[h]}", "intro")
            if re.search(r"placed on the Calendar", t, re.I):
                place = "floor"
            continue
        if re.search(r"Legislative Bureau", t, re.I):
            add(d, h, "Sent to the Legislative Bureau, which reviews its wording" if re.search(r"referred to the Legislative Bureau", t, re.I)
                and not re.search(r"Reported (?:with|without) Legislative Bureau", t, re.I) else
                "The Legislative Bureau reviewed its wording" + (" and proposed changes" if re.search(r"with Legislative Bureau amendments", t, re.I) else ""), "bureau")
            if re.search(r"passed to third reading", t, re.I):
                place = "floor"
            continue
        if re.search(r"passed to (?:3rd|third) reading|returned to the calendar|Called from the calendar|placed on the Calendar|"
                     r"Scheduled for floor debate|Special Order|Interim Calendar|lies over|called out of its regular order|"
                     r"called from regular order|Involuntary Calendar", t, re.I):
            if place != "committee" and not re.match(r"Scheduled for floor debate|First appeared", t, re.I):
                place = "floor"
            elif re.match(r"Scheduled for floor debate", t, re.I) and place != "committee":
                place = "floor"
            add(d, h, t.rstrip("."), "calendar")
            continue
        if re.search(r"conferees|Conference Committee members|conference committee appointment|Conference Committee report received|"
                     r"Conference committee report received|Conference Committee membership", t, re.I):
            add(d, h, t.rstrip("."), "conf")
            continue
        if re.match(r"Notice|Scheduled for concurrence", t, re.I):
            add(d, h, t.rstrip("."), "notice")
            continue
        # Amendments, motions: as written.
        UNREAD[re.sub(r"\d+", "#", t)[:80]] += 1
        add(d, h, t[:1].upper() + t[1:].rstrip("."), "other")

    # Voluntary deferrals (the author's request) appear only in the committee's vote records.
    for day, h, c, what in defers:
        if not any(s_[0] == day and s_[3] == "held" for s_ in steps):
            if re.search(r"Voluntar", what, re.I):
                add(day, h, f"Deferred by the {c} Committee at the author's request", "deferred")
                deferred = deferred or "voluntary"
            elif re.search(r"Involuntar", what, re.I):
                add(day, h, f"Deferred by the {c} Committee (involuntarily), which ends it for the session", "held")
                deferred = "involuntary"
            else:
                add(day, h, f"The {c} Committee put off its decision" + (" to a later date" if re.search(r"date", what, re.I) else ""), "deferred")

    # Laws and vetoes, checked against the Legislature's vetoed list.
    vlist = (lst.get("vetoed") or {}).get(p) or ""
    status = (b.get("status") or (lst.get("bills", {}).get(p) or {}).get("status") or "")
    if not const:
        if re.match(r"Vetoed", vlist, re.I) and not law:
            vetoed = True
        if re.match(r"Signed by the Governor", vlist) and law:
            items = True
        if not law and not vetoed:
            ms = re.match(r"(?:Signed by the Governor|Became law without the Governor's signature) - Act (\d+)", status)
            if ms:
                law, chapter = True, int(ms.group(1))
    if vetoed and not any(s_[3] == "vetoed" for s_ in steps):
        add(steps[-1][0] if steps else f"{session}-06-30", "G", "VETOED", "vetoed")
    if items and not any(s_[3] == "itemveto" for s_ in steps):
        add(next((s_[0] for s_ in steps if s_[3] == "signed"), steps[-1][0] if steps else ""), "G",
            "The governor vetoed items in it (a line-item veto)", "itemveto")
    pending = bool(amended_by - {OTHER[h_] for h_ in concurred}) and not (ccr >= {"S", "H"})
    both = enrolled or sent or law or vetoed or to_sos or (passed >= {"S", "H"} and not pending and not amended_by)
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
        stage = 1 if place == "floor" and not withdrawn and not replaced else 0
    if stage == 1 and defeated == origin:
        stage = 1

    title = title_of(b.get("title") or "", const)
    topics = ["const"] if const else []
    for h_, c in refs:
        tp = P.COMMITTEE_TOPICS.get(c)
        if tp and tp not in topics:
            topics.append(tp)
    for tp in P.keyword_topics(kw):
        if tp not in topics:
            topics.append(tp)
    if not topics:
        topics = [k for k, rx in P.TOPIC_WORDS.items() if rx.search(short)]
    topics = [t_ for t_ in dict.fromkeys(topics) if t_ != "const" or const]

    # Authors in order: the primary author first. Co-authors from the other house keep their own house for parties.
    authors = b.get("authors") or []
    names = []
    for a in authors:
        sid = page_seat(a.get("page"))
        ah = sid[0] if sid else origin
        n, dist, party = author_of(session, ah, a)
        names.append((n, dist, ah))
        if party and ah == origin:
            parties[(origin, n)] = party
    sponsor, district = (names[0][0], names[0][1]) if names else (clean_author(b.get("author")) or "—", None)
    cos = [n for n, _, _ in names[1:] if n != sponsor]

    cur = where
    if stage == 0:
        dsc = f"In {HOUSE[cur]} committee" if place == "committee" else "Introduced"
    elif stage == 1:
        dsc = f"On the {HOUSE[cur]} floor"
    else:
        dsc = {2: f"Passed the {HOUSE[origin] if origin in passed else HOUSE[other]}", 3: "Passed both houses",
               4: "On the governor's desk", 5: "Became law", 6: "Vetoed"}[stage]
    passed_in = (HOUSE[origin] if origin in passed else HOUSE[other]) if stage == 2 else None
    if stage == 2 and len(passed) == 2 and pending:
        amender = next(iter(amended_by))
        passed_in = HOUSE[amender]
        dsc = f"In the {HOUSE[OTHER[amender]]}, to agree to the {HOUSE[amender]}'s changes"
    comm_now = comm if place == "committee" and stage in (0, 2) else None

    def dates(test, mode="last"):
        ds = sorted({s[0] for s in steps if test(s) and s[0]})
        return {"first": ds[0], "last": ds[-1], "all": ";".join(ds)}[mode] if ds else ""

    steps.sort(key=lambda s_: s_[0] or "")  # (stable: the committees' deferrals from their vote records go in by day)
    action_dates = [s[0] for s in steps if s[0]]
    held = deferred == "involuntary"
    fate = "passed" if reported or passed else "defeated" if held else "held" if deferred else "none"
    local_bill = any(x.get("group") == "Notices" and x.get("label") == "Public Notice" for x in b.get("docs") or [])
    rec = {
        "nums": [p], "base": [p], "prev": earlier(session, b),
        "title": title, "summary": keyword_text(kw), "act": "", "lawCode": "", "law": None, "laws": [],
        "comms": sorted({f"{h_} · {c}" for h_, c in refs}), "topics": topics, "places": [],
        "narrow": "" if const else P.narrow_kind(short, kw, local_bill),
        "commFate": fate, "mainTopic": topics[0] if topics else "",
        "local": "local" in topics, "senDeleg": False, "asmDeleg": False,
        "budget": bool(re.match(r"APPROPRIATIONS|CAPITAL OUTLAY", kw)) and not const,
        "passedS": "S" in passed, "passedA": "H" in passed, "program": None,
        "stage": stage, "passedIn": passed_in,
        "chapter": chapter if stage == 5 else None,
        "veto": None, "memo": "", "vetoMemo": None,
        "simText": f"{keyword_text(kw)} {short}",
        "comm": comm_now if stage == 0 else None,
        "first": min(action_dates, default=f"{session}-03-01"),
        "last": max(action_dates, default=f"{session}-03-01"),
        "cosp": len(cos),
        "keyDates": [
            dates(lambda s: s[3] == "reported", "first"),
            dates(lambda s: s[2] == "PASSED SENATE", "all"),
            dates(lambda s: s[2] == "PASSED HOUSE", "all"),
            "",
            dates(lambda s: s[3] == "sent") if stage >= 4 else "",
            dates(lambda s: s[3] in ("signed", "nosign")) if stage == 5 else "",
            dates(lambda s: s[3] == "vetoed") if stage != 5 else "",
        ],
        "votes": fvotes, "firstComms": [(origin, first_ref, first_report or bool(passed))] if first_ref else [],
        "vers": [{"p": p, "sponsor": sponsor, "district": district or 0, "cosponsors": cos,
                  "primes": 1, "cosp": len(cos), "statusDesc": dsc, "committee": comm_now,
                  "actions": [[s[0], s[2]] for s in steps],
                  "link": f"https://legis.la.gov/legis/BillInfo.aspx?s={code(session)}&b={p}&sbi=y"}],
    }
    if items and stage == 5:
        rec["vers"][0]["itemVeto"] = True
    if stage == 5 and not rec["keyDates"][5]:
        rec["keyDates"][5] = rec["last"]
    return rec


# ---- "What it does" ----

STARTS = re.compile(r"^(?:Abstract:|Present law|Proposed law|Prior law|Existing law|New law|Effective|\(Amends|\(Adds|\(Repeals|"
                    r"\(Enacts|\(Amends and|Provides that|Specifies|Requires|Authorizes|Further provides|Vetoed by|Section \d|"
                    r"Summary of|The Committee Amendments|The House Floor|The Senate|The House|Prepared by)")
BACKGROUND = re.compile(r"^(?:Present law|Prior law|Existing law)\b")
DOES = re.compile(r"^(?:Proposed law|New law|Proposed constitutional amendment|Abstract)\b")


def digest_doc(session, b):
    """The bill's digest that's been downloaded: the résumé digest of the act as passed, else the newest digest of the bill
    ("Digest of HB1 Reengrossed")."""
    have = []
    for x in b.get("docs") or []:
        if x.get("group") == "Digests" and x.get("doc") and re.match(r"(?:Resume Digest|Digest of)", x.get("label") or ""):
            have.append(x)
    have.sort(key=lambda x: not x["label"].startswith("Resume"))
    for x in have[:1]:
        path = os.path.join(folder(session), "docs", f"{x['doc']}.txt")
        if os.path.exists(path):
            return x, open(path, encoding="utf-8", errors="replace").read()
    return None, ""


def digest_text(raw, limit=3000):
    """A digest's text as paragraphs, led by what the bill does (the abstract, "Proposed law ...", "New law ..."), the
    background ("Present law ...") after, without the header, the citations ("(Amends R.S. 15:828(E))") and the summary
    of amendments; cut at a sentence after limit characters."""
    lines = [l.rstrip() for l in raw.replace("\f", "\n").splitlines()]
    # The header ends at the author's line, after "<year> Regular Session".
    start = 0
    for i, l in enumerate(lines[:30]):
        if re.match(r"\s*\d{4} Regular Session\s*$", l):
            j = i + 1
            while j < len(lines) and not lines[j].strip():
                j += 1
            start = j + 1  # the line after the author's name
            break
    body = lines[start:]
    cut = next((i for i, l in enumerate(body) if re.match(r"\s*(?:Summary of (?:Amendments|House|Senate)|The Committee Amendments Proposed|"
                                                              r"Committee Amendments Proposed|House Floor Amendments|Senate Committee Amendments|"
                                                              r"Senate Floor Amendments|Conference Committee Amendments)", l)), None)
    if cut is not None:
        body = body[:cut]
    width = max((len(l) for l in body), default=80)
    paras, cur = [], []
    for l in body:
        s = l.strip()
        if not s:
            # A blank line ends a paragraph only after a sentence: page breaks fall mid-sentence too.
            if cur and re.search(r"[.:;?!)\"”]$", cur[-1]):
                paras.append(" ".join(cur))
                cur = []
            continue
        if re.fullmatch(r"Page \d+ of \d+|CODING:.*|\d+", s):
            continue
        if cur and (STARTS.match(s) or (cur and re.search(r"[.:;)]$", cur[-1]) and len(cur[-1]) < 0.75 * width and s[:1].isupper())):
            paras.append(" ".join(cur))
            cur = []
        cur.append(s)
    if cur:
        paras.append(" ".join(cur))
    paras = [re.sub(r"\s+", " ", re.sub(r"(\w)- (\w)", r"\1-\2", p)).strip() for p in paras]
    paras = [p for p in paras if p and not re.match(r"\((?:Amends|Adds|Repeals|Enacts|Redesignates)\b", p)
             and not re.fullmatch(r"\d+\.?|Page \d+ of \d+", p)]
    out_lead, out_back = [], []
    for p in paras:
        p = re.sub(r"^Abstract:\s*", "", p)
        (out_back if BACKGROUND.match(p) and not out_lead else out_lead).append(p)
    text = "\n".join(out_lead + out_back)
    if len(text) > limit:
        c = text[:limit].rfind(". ")
        text = text[:c + 1 if c > limit // 2 else limit].rstrip() + " …"
    return text


def what_it_does(session, b):
    x, raw = digest_doc(session, b)
    if not raw:
        return None
    text = digest_text(raw)
    if len(text) < 40:
        return None
    lab = x["label"]
    by = "House Legislative Services" if "House Legislative Services" in raw[:600] else \
        "Senate staff" if re.search(r"Senate", raw[:600]) and b["key"].startswith("S") else ""
    if lab.startswith("Resume"):
        label = "From the résumé digest of the bill as passed" + (f", by {by}." if by else ".")
    else:
        ver = re.sub(r"^Digest of [HS]B ?\d+\s*", "", lab).strip().lower()
        what = {"original": "the bill as introduced", "engrossed": "the bill as engrossed (after its first committee)",
                "reengrossed": "the bill as passed by its house", "re-reengrossed": "the bill as passed by its house",
                "enrolled": "the bill as passed"}.get(ver, "the bill")
        label = f"From the digest of {what}" + (f", by {by}." if by else ".")
    return {"statement": text, "label": label}


def load_session(session):
    """Read one year's bills and return (records, bill number -> record index, fetched time, delegation)."""
    k = (session, "loaded")
    if k in _CACHE:
        return _CACHE[k]
    lst = listing(session)
    parties = _PARTIES.setdefault(session, {})
    recs, index, whats = [], {}, {}
    keys = [k_ for k_ in lst.get("bills") or [] if re.fullmatch(r"(HB|SB)\d+", k_)]
    for k_ in sorted(keys, key=lambda k_: (k_[0] != "H", int(re.sub(r"\D", "", k_)))):
        b = bill(session, k_)
        if not b or not b.get("hist"):
            continue
        if all(re.search(r"withdrawn .*prior to introduction|Withdrawn prior to introduction", t, re.I) or t == "Prefiled." or
               re.match(r"Prefiled|Under the rules, provisionally", t) for _, _, t in b["hist"]) and \
                any(re.search(r"prior to introduction", t, re.I) for _, _, t in b["hist"]):
            continue  # withdrawn before it was introduced: never a bill of the session
        rec = record(session, b, parties)
        what = what_it_does(session, b)
        index[k_] = len(recs)
        recs.append(rec)
        if what:
            whats[k_] = what
    try:
        json.dump(whats, open(os.path.join(P.DATA, f"texts_{session}.json"), "w"), ensure_ascii=False)
    except OSError:
        pass
    paths = [os.path.join(folder(session), n) for n in ("state.json", "list.json")]
    times = [os.path.getmtime(x) for x in paths if os.path.exists(x)]
    fetched = datetime.fromtimestamp(max(times), ZoneInfo(P.TIMEZONE)).strftime("%Y-%m-%d %H:%M") if times else ""
    _CACHE[k] = (recs, index, fetched, {"SENATE": [], "ASSEMBLY": []})
    return _CACHE[k]


# ---- Earlier years ----

_KEYS = {}


def _norm(s):
    return re.sub(r"[^a-z0-9 ]", "", re.sub(r"\s+", " ", fold(s))).strip()


def _key(session, b):
    """The short description and primary author's surname, or "" for budget bills."""
    kw, short = subject(b.get("title") or "")
    if re.match(r"APPROPRIATIONS|CAPITAL OUTLAY", kw):
        return ""
    t = _norm(short)
    if len(t.split()) < 4:
        return ""
    a = (b.get("authors") or [{}])[0].get("name") or b.get("author") or ""
    return f"{t}|{author_last(a)}"


def _keys(session):
    """A year's bills that didn't become law: key -> [bills]."""
    if session not in _KEYS:
        out = defaultdict(list)
        lst = listing(session)
        for k, v in (lst.get("bills") or {}).items():
            if not re.fullmatch(r"(HB|SB)\d+", k) or re.match(r"(?:Signed by the Governor|Became Act|Sent to the Secretary)", v.get("status") or ""):
                continue
            b = bill(session, k)
            if b:
                key = _key(session, b)
                if key:
                    out[key].append(k)
        _KEYS[session] = out
    return _KEYS[session]


def earlier(session, b):
    """The same bill in the two years before: the same short description and primary author, held by one bill in each
    year; never budget bills, nor a bill that became law."""
    out = set()
    key = _key(session, b)
    if not key:
        return out
    for y in (session - 1, session - 2):
        if y not in sessions():
            continue
        old, mine = _keys(y), _keys(session)
        if len(old.get(key, [])) == 1 and len(mine.get(key, [])) <= 1:
            out.add((y, old[key][0]))
    return out


def parties(session, recs):
    if session not in _PARTIES:
        load_session(session)
    return {k: v for k, v in _PARTIES.get(session, {}).items() if v in ("D", "R")}


def agendas(session):
    return {}


# ---- Checks against the Legislature's lists ----

def checks(session):
    """Laws, vetoes and line-item vetoes against the vetoed list and the Act numbers."""
    recs = load_session(session)[0]
    lst = listing(session)
    vl = lst.get("vetoed") or {}
    off_veto = {k for k, v in vl.items() if not re.match(r"Signed", v)}
    off_items = {k for k, v in vl.items() if re.match(r"Signed", v)}
    mine_law = {r["nums"][0] for r in recs if r["stage"] == 5}
    mine_veto = {r["nums"][0] for r in recs if r["stage"] == 6}
    mine_items = {r["nums"][0] for r in recs if r["vers"][0].get("itemVeto")}
    acts = Counter(r["chapter"] for r in recs if r["chapter"])
    ca_acts = []
    for r in recs:
        if "const" in r["topics"]:
            for _, t in r["vers"][0]["actions"]:
                m = re.match(r"Act No\. (\d+) \(sent to the voters\)", t)
                if m:
                    ca_acts.append(int(m.group(1)))
    every = sorted(list(acts) + ca_acts)
    top = max(every, default=0)
    status_law = {k for k, v in (lst.get("bills") or {}).items() if re.match(r"(?:Signed by the Governor|Became law without)", v.get("status") or "")}
    nosig = sorted(r["nums"][0] for r in recs if any("without the governor" in a[1] for a in r["vers"][0]["actions"]))
    const = sorted(r["nums"][0] for r in recs if "const" in r["topics"] and r["stage"] == 3)
    votes = [v for r in recs for v in r["votes"] if v[1] == "F"]
    named = [m for v in votes for m, _ in v[6]]
    return {"bills": len(recs), "laws": len(mine_law), "laws by status": len(status_law), "differ": sorted(mine_law ^ status_law)[:10],
            "without signature": len(nosig), "vetoes": len(mine_veto), "vetoed list": len(off_veto),
            "vetoes differ": sorted(mine_veto ^ off_veto), "line items": sorted(mine_items), "line items listed": sorted(off_items),
            "amendments to the voters": const, "acts": f"1-{top}: {len(every)} numbers, missing {sorted(set(range(1, top + 1)) - set(every))[:10]}, "
                                                    f"repeated {[c for c, n in Counter(every).items() if n > 1]}",
            "floor votes": len(votes), "naming a no or absence": sum(1 for v in votes if v[6]),
            "noes and absences tied to seats": f"{sum(1 for m in named if '?' not in m)} of {len(named)}"}


if __name__ == "__main__":
    import sys
    for s in ([int(sys.argv[1])] if len(sys.argv) > 1 else sessions()):
        print(s, json.dumps(checks(s)))
    for k, n in UNREAD.most_common(40):
        print(n, k)
