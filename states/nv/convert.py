"""Nevada's bills (downloaded by states/nv/fetch.py from NELIS, the Nevada Electronic Legislative Information System) in
the shape build_data.py reads. Assembly and Senate bills of each regular session (odd years only: the 83rd was 2025),
plus the joint resolutions that propose amendments to the Nevada Constitution (their bill draft number starts "C-":
"(BDR C-668)"); other joint resolutions (memorials: "Urges Congress to ...") and resolutions are left out.

Each bill's Overview page (bills/<AB1>.html) has its one-line summary, sponsors (members, by their legislator pages,
or a committee: "Assembly Committee on Commerce and Labor", for bills prefiled on behalf of agencies and officials),
the official title, the Legislative Counsel's Digest, the committee hearings with their recommendation, and the
history: a date and an action in plain English, several steps to a line ("Read third time. Passed, as amended. Title
approved. (Yeas: 24, Nays: 18.) To Senate."). The lines don't say which house acted: the bill is followed from house to
house ("To Senate." / "In Senate."; a veto message returns to the house of origin). Readings: "Read first time.
Referred to Committee on X." ("Resolution read." for resolutions); "From committee: Do pass." / "Amend, and do pass as
amended." / "Without recommendation." (a committee's report; there are no committee tallies, and no committee votes
bills down: a bill not reported by the deadline dies there, "(Pursuant to Joint Standing Rule No. 14.3.1, no further
action allowed.)"); "Rereferred to Committee on Ways and Means" (bills that cost money); "Read third time. Passed[, as
amended]. (Yeas: 35, Nays: 7.)" (the passage), "Lost." (failed: AB 500 of 2025 lost with 25 of 42 votes, since it needed
two-thirds), "Action of passage reconsidered." / "Action reconsidered." (undoes the house's last vote); the first house
"Senate Amendment No. 667 concurred in. To enrollment." or "not concurred in", then a conference committee whose report
both houses adopt ("Conference report adopted by Senate." and "... by Assembly."); "To enrollment." means passed both
houses; "Enrolled and delivered to Governor."; "Approved by the Governor. Chapter 60." (a chapter of the Statutes of
Nevada); "Vetoed by the Governor." A veto during the session is read to the house of origin, which may override it by
two-thirds of each house ("No further action taken." when it doesn't); a veto after the session goes to the next regular
session ("(Return to 83rd Session)"), which can still override it: a 2025 veto can be overridden in 2027 (a history
line says so, "Vetoed after the session ended: ...", which profile.js's STATE.vetoReturns() reads). Joint resolutions go to the Secretary of State ("Enrolled and delivered to Secretary of State. File No.
24."), never the governor, and have to pass two sessions in a row, then the voters.

Floor votes (votes/<AB1>.json): each final passage, member by member. NELIS calls every one "Passed" (AB 500's lost
votes too): the history line decides, and votes are matched to it by house, day and tally. The laws and vetoed lists
(list.json) decide laws and vetoes too, and agree with the histories bill for bill.
"""
import html, json, os, re
from datetime import date, datetime
from zoneinfo import ZoneInfo

from states.nv import profile as P

HOUSE = {"S": "Senate", "A": "Assembly"}
CHAMBER = {"Senate": "S", "Assembly": "A"}
_CACHE, _PAGES, _PARTIES, _SEATS = {}, {}, {}, {}
# Vetoes missing from NELIS (the bill's history and the vetoed list both): (session, bill) -> (day, history line).
# SB 99 of 2025 was vetoed June 2, 2025 and returned to the Senate with a veto message (FastDemocracy's record of the bill;
# the press counted 87 vetoes in 2025: NELIS's 86 and this one); NELIS shows only "(No further action taken.)".
VETO_FIX = {(2025, "SB99"): ("2025-06-02", "Vetoed June 2, 2025 (missing from NELIS's records; reported by the press)")}
KINDS = ("AB", "SB", "AJR", "SJR")


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
    """A session's files: "list" (bills, laws, vetoed), "committees", "members"."""
    key = (session, name)
    if key not in _CACHE:
        path = os.path.join(folder(session), "members", "members.json") if name == "members" else os.path.join(folder(session), f"{name}.json")
        try:
            data = json.load(open(path, encoding="utf-8"))
        except (OSError, ValueError):
            data = None
        if name == "members":
            data = (data or {}).get("members") or []
        _CACHE[key] = data if data is not None else ({} if name == "list" else [])
    return _CACHE[key]


def text(x):
    return re.sub(r"\s+", " ", html.unescape(str(x or "")).replace("\xa0", " ")).strip()


def strip_tags(x):
    return text(re.sub(r"<[^>]+>", " ", x or ""))


def day(s):
    """"Nov 19, 2024" / "Tuesday, November 19, 2024" -> "2024-11-19"."""
    s = text(s)
    for fmt in ("%b %d, %Y", "%B %d, %Y", "%A, %B %d, %Y"):
        try:
            return datetime.strptime(s, fmt).date().isoformat()
        except ValueError:
            pass
    return ""


def official(p):
    m = re.fullmatch(r"([A-Z]+)(\d+)", p)
    return f"{m.group(1)} {m.group(2)}" if m else p


def bdr(summary):
    """"... (BDR 52-503)" -> "52"; "(BDR S-299)" -> "S"; "(BDR C-668)" -> "C"."""
    m = re.search(r"\(BDR\s*([A-Z0-9]+)-[\w-]+\)", text(summary))
    return m.group(1) if m else ""


def is_amendment(p, summary):
    """A joint resolution proposing an amendment to the Nevada Constitution (its bill draft is a "C-" request)."""
    return "JR" in p and (bdr(summary) == "C" or bool(re.search(r"amend the (?:Nevada )?Constitution", summary or "", re.I)))


# ---- one bill's Overview page ----------------------------------------------------------------------------------------

def region(page, name):
    m = re.search(rf"<!--\s*#region {re.escape(name)}\s*-->(.*?)<!--\s*#endregion\s*-->", page, re.S)
    return m.group(1) if m else ""


def people(block):
    """The sponsors in a block: [(name as written, house letter or None, district or None, committee name or None)]."""
    out = []
    for href, label in re.findall(r'<a[^>]*href="([^"]*)"[^>]*>(.*?)</a>', block, re.S):
        label = strip_tags(label)
        m = re.search(r"/App/Legislator/A/(Assembly|Senate)/[^/]+/(\d+)", href)
        if m:
            name = re.sub(r"^(?:Assembly(?:member|man|woman)|Senator)\s+", "", label)
            out.append((name, CHAMBER[m.group(1)], int(m.group(2)), None))
        elif "/Committee/" in href:
            out.append((label, None, None, label or "?"))
    return out


def page(session, p):
    """The parts of bills/<p>.html this converter uses, or None when it wasn't downloaded."""
    key = (session, p)
    if key in _PAGES:
        return _PAGES[key]
    try:
        s = open(os.path.join(folder(session), "bills", f"{p}.html"), encoding="utf-8").read()
    except OSError:
        _PAGES[key] = None
        return None
    info = region(s, "General Bill Informantion")
    summary = re.search(r"Summary</div>\s*<div class=\"col\">(.*?)</div>", info, re.S)
    intro = re.search(r"Introduction Date</div>\s*<div class=\"col\">(.*?)</div>", info, re.S)
    title = re.search(r'<div id="title" class="collapse">(.*?)</div>', s, re.S)
    digest = re.search(r'<div id="digest" class="collapse">(.*?)</div>', s, re.S)
    hearings = []
    for row in re.findall(r"<tr>(.*?)</tr>", region(s, "Past Hearings") + region(s, "Upcoming Hearings"), re.S):
        c = re.search(r'data-th="Committee"[^>]*title="([^"]*)"|title="([^"]*)" data-th="Committee"', row)
        d = re.search(r'data-th="Date">(?:<a[^>]*>)?([^<]*)', row)
        t = re.search(r'data-th="Time">\s*(?:<a[^>]*>)?([^<]*)', row)
        rec = re.search(r'data-th="Recommendation">(.*?)</td>', row, re.S)
        if c and d:
            hearings.append({"committee": text(c.group(1) or c.group(2)), "date": day(d.group(1)), "time": text(t.group(1)) if t else "",
                             "rec": strip_tags(rec.group(1)) if rec else "", "work": "Work Session" in row})
    rows = []
    for d, a in re.findall(r'data-th="Date">([^<]*)</td>\s*<td class="col" data-th="Action">(.*?)</td>', region(s, "Bill History"), re.S):
        rows.append((day(d), text(re.sub(r"<[^>]+>", " ", a.replace("\n", " ")))))
    digest_text = ""
    if digest:
        paras = [strip_tags(x) for x in re.split(r"\n\s*", html.unescape(digest.group(1)).replace("\r", ""))]
        digest_text = "\n".join(x for x in paras if x)
    _PAGES[key] = {
        "summary": strip_tags(summary.group(1)) if summary else "",
        "intro": day(intro.group(1)) if intro else "",
        "primary": people(region(s, "Primary Sponsors")), "cosponsors": people(region(s, "Co-Sponsors")),
        "title": strip_tags(title.group(1)) if title else "", "digest": digest_text,
        "hearings": hearings, "rows": rows,
        "exempt": "DECLARED EXEMPT" in region(s, "Declared Exempt?"),
    }
    return _PAGES[key]


def votes_file(session, p):
    try:
        return json.load(open(os.path.join(folder(session), "votes", f"{p}.json"), encoding="utf-8"))
    except (OSError, ValueError):
        return None


# ---- names and seats ---------------------------------------------------------------------------------------------------

def name_parts(n):
    """"Hafen, Gregory T., II" -> ("hafen", "gregory"); "O’Neill, PK" -> ("o'neill", "pk")."""
    n = text(n).replace("’", "'")
    last, _, first = n.partition(",")
    first = re.sub(r"\(.*?\)|\"[^\"]*\"", " ", first)
    return last.strip().lower(), (first.split() or [""])[0].strip(".").lower()


def full_name(m):
    """A member's display name: "Daniele Monroe-Moreno"; "Gregory T. Hafen II"."""
    f = text(m.get("full"))
    if f:
        return re.sub(r"\s+", " ", f.replace("’", "'"))
    last, _, first = text(m.get("name")).replace("’", "'").partition(",")
    first = re.sub(r"\(.*\)$", "", first).strip().rstrip(".")
    suffix = ""
    sm = re.search(r",\s*(Jr\.?|Sr\.?|II|III|IV)$", first)
    if sm:
        suffix, first = " " + sm.group(1), first[:sm.start()].strip()
    return text(f"{first} {last}{suffix}")


def seats(session):
    """(house, last name, first name) -> seat id ("A:30", "S:6") for the session's members (one per seat: the member
    list shows each district's member at the end of the session; one who resigned after it, Toby Yurek in October 2025,
    is still listed). Also (house, last name, "") when the last name is one member's in the house."""
    if session in _SEATS:
        return _SEATS[session]
    out, count = {}, {}
    for m in load(session, "members"):
        h = CHAMBER.get(m.get("house"))
        if not h or not m.get("district"):
            continue
        last, first = name_parts(m.get("name"))
        sid = f"{h}:{int(m['district'])}"
        out[(h, last, first)] = sid
        count[(h, last)] = count.get((h, last), []) + [sid]
    for (h, last), sids in count.items():
        if len(sids) == 1:
            out[(h, last, "")] = sids[0]
    _SEATS[session] = out
    return out


def seat_of(session, h, name):
    """A roll call's name ("Anderson, Natha") -> its seat, else "A?Anderson"."""
    s = seats(session)
    last, first = name_parts(name)
    sid = s.get((h, last, first)) or s.get((h, last, ""))
    if not sid:
        # A first name written differently ("Cinthia Zermeño" / "Cinthia"): the same last name and initial.
        hits = {v for (hh, ll, ff), v in s.items() if hh == h and ll == last and ff[:1] == first[:1] and ff}
        # A member whose name changed: Sen. Heidi Seevers Gansert is "Seevers O'Gara, Heidi" in 2023's roll calls.
        hits = hits or {v for (hh, ll, ff), v in s.items() if hh == h and ff == first and ll.split()[0] == last.split()[0]}
        sid = hits.pop() if len(hits) == 1 else None
    return sid or f"{h}?{text(name).split(',')[0]}"


def member_by_seat(session):
    return {f"{CHAMBER[m['house']]}:{int(m['district'])}": m for m in load(session, "members")
            if CHAMBER.get(m.get("house")) and m.get("district")}


def sponsor_name(session, x):
    """A sponsor entry -> the member's full name from the session's member list, else as written; a committee as
    "Assembly Committee on Judiciary"."""
    name, h, d, comm = x
    if comm:
        return comm
    m = member_by_seat(session).get(f"{h}:{d}")
    if m and name_parts(m.get("name"))[0] in name.replace("’", "'").lower():
        return full_name(m)
    return text(name).replace("’", "'")


# ---- titles and texts --------------------------------------------------------------------------------------------------

def titled(summary):
    """The list's one-line summary without its bill draft number: "Prohibits manipulating the price of an essential good
    or service in this State.\""""
    t = re.sub(r"\s*\(BDR\s*[^)]*\)\s*$", "", text(summary)).strip()
    return t.rstrip(".")


SENT = re.compile(r"(?<=[a-z0-9)\"”’][.])\s+(?=[A-Z(])")
DOES = re.compile(r"^(?:(?:Under |With [^,]{0,40}, )?[Tt]his (?:bill|resolution|joint resolution|act)\b|(?:Under )?[Ss]ections? [\d.]+(?:(?:,|,? and| to|-)\s*[\d.]+)*(?:, inclusive,)?(?! of (?:Article|the Nevada Constitution|NRS|chapter|Chapter|Statutes))\b|The (?:proposed )?amendment)")
CITE = re.compile(r"\s*\((?:\d+ U\.S\.C\.|\d+ C\.F\.R\.|NRS|Chapter|Chapters|Section|Sections|Nev\. Const\.|Article|Art\.|[^()]*\bof NRS\b|[^()]*\bNRS \d)(?:[^()]|\([^()]*\))*\)")


def digest_text(d):
    """The Legislative Counsel's Digest as paragraphs, each led by what the bill does ("This bill ...", "Section 3 of
    this bill ...") and then the background it's written after ("Existing law ..."); paragraphs that are only background
    come last. Without the statute citations ("(NRS 598A.280)")."""
    lead, back = [], []
    for para in (d or "").split("\n"):
        para = CITE.sub("", text(para)).strip()
        if not para:
            continue
        ss = [s.strip() for s in SENT.split(para) if s.strip()]
        does = [s for s in ss if DOES.match(s)]
        rest = [s for s in ss if s not in does]
        # A paragraph that's only background ("Existing law ...") goes after the ones that say what the bill does.
        (lead if does else back).append(" ".join(does + rest))
    return "\n".join(lead + back)


def sim_text(title_):
    t = re.sub(r"^AN ACT relating to\s*", "", text(title_), flags=re.I)
    t = re.sub(r";?\s*and providing other matters properly relating thereto\.?$", "", t, flags=re.I)
    return t.lower()


def relating(title_):
    m = re.match(r"(?:AN ACT|A JOINT RESOLUTION)\s+relating to\s+([^;]+)", text(title_), re.I)
    return m.group(1) if m else ""


# ---- the history ---------------------------------------------------------------------------------------------------------

TOKENS = re.compile(r"""
  (?P<prefiled>\bPrefiled\.)
| (?P<first>\bRead\ first\ time\.)
| (?P<resread>\bResolution\ read\.)
| (?P<fromc>\bFrom\ committee:\s*(?P<rec>Concur\ in\ (?:Senate|Assembly)\ Amendments?\ Nos?\.\ [\w,\ ]+?(?:\ and\ further\ amend)?\.|[^.]+\.))
| (?P<ref>\b(?:[Rr]e-?)?(?:re)?[Rr]efer(?:red)?\ to\ (?:the\ )?(?P<sel>Select\ )?(?:Committee\ on\ )?(?P<comm>[A-Z][^.]*?)\.(?=\s|$))
| (?P<withdrawn>\bWithdrawn\ from\ (?:committee|Committee\ on\ (?P<wcomm>[^.]+?))\.)
| (?P<second>\bRead\ second\ time\.)
| (?P<third>\bRead\ third\ time\.)
| (?P<amended>\bAmended\.\ \((?:Conference\ )?Amend\.\ Nos?\.\ [^)]*\))
| (?P<camend>\((?:Conference\ )?Amend\.\ Nos?\.\ [^)]*\))
| (?P<passed>\bPassed(?P<asam>,\ as\ amended)?\.(?:\ Title\ approved(?:,\ as\ amended)?\.)?(?:\ Preamble\ adopted(?:,\ as\ amended)?\.)?(?:\ \((?P<tally>Yeas:[^)]*)\))?)
| (?P<lost>\bLost\.(?:\ \((?P<ltally>Yeas:[^)]*)\))?)
| (?P<recons>\bAction\ (?:of\ passage\ )?reconsidered\.)
| (?P<concur>\b(?P<cch>Senate|Assembly)\ Amendments?\ Nos?\.\ [\w,\ ]+?\ (?P<cnot>not\ )?concurred\ in\.)
| (?P<recede>\b(?P<rch>Senate|Assembly)\ Amendments?\ Nos?\.\ [\w,\ ]+?\ (?P<rnot>not\ )?receded\ from\.)
| (?P<confreq>\bConference\ requested\.)
| (?P<confappt>\bConference\ Committee\ appointed\ by\ (?P<cah>Senate|Assembly)\.)
| (?P<confadopt>\bConference\ report\ (?P<cfnot>not\ )?adopted\ by\ (?P<cfh>Senate|Assembly)\.)
| (?P<enroll>\bTo\ enrollment\.)
| (?P<deliv>\bEnrolled\ and\ delivered\ to\ (?P<to>Governor|Secretary\ of\ State)\.)
| (?P<fileno>\bFile\ No\.\ (?P<file>\d+)\.)
| (?P<signed>\bApproved\ by\ the\ Governor\.)
| (?P<nosign>\bBecame\ law\ without\ (?:the\ )?Governor's\ signature\.)
| (?P<chapter>\bChapter\ (?P<chap>\d+)\.)
| (?P<veto>\bVetoed\ by\ the\ Governor\.)
| (?P<ret>\(Return\ to\ (?P<retn>\d+\w*)\ Session\))
| (?P<vmsg>\bReturned\ to\ (?P<vh>Senate|Assembly)\ with\ Governor's\ veto\ message\.|\bBill\ read\ with\ Governor's\ veto\ message\.|\bBill\ read\.)
| (?P<override>\bPassed,?\ notwithstanding\ the\ veto\ of\ the\ Governor\.(?:\ \((?P<otally>Yeas:[^)]*)\))?)
| (?P<nfa>\(?No\ further\ action\ taken\.\)?|\bNo\ further\ consideration\.)
| (?P<deadline>\(Pursuant\ to\ Joint\ Standing\ Rule\ No\.\ (?P<rule>[\d.]+?),\ no\ further\ action\ allowed\.\))
| (?P<tohouse>\bTo\ (?P<toh>Senate|Assembly)\.)
| (?P<inhouse>\bIn\ (?P<inh>Senate|Assembly)\.)
| (?P<emerg>\bDeclared\ an\ emergency\ measure\ under\ the\ Constitution\.)
| (?P<exempt>\bNotice\ of\ eligibility\ for\ exemption\.|\bExemption\ effective\.|\bNotice\ of\ exemption\.|\bWaiver\ granted\ effective:\ [A-Z][a-z]+\ \d+,\ \d{4}\.|\bExempt\ pursuant\ to\ Joint\ Standing\ Rule\ [\d.]*\d(?:,\ subsection\ [\w()]+)?\.)
| (?P<desk>\bPlaced\ on\ (?:Chief\ Clerk's|Secretary's)\ desk\.|\bTo\ (?:Chief\ Clerk's|Secretary's)\ desk\.|\bAmendment\ No\.\ \d+\ placed\ on\ Chief\ Clerk's\ desk\.)
| (?P<undesk>\bTaken\ from\ (?:Chief\ Clerk's|Secretary's)\ desk\.)
| (?P<file_>\b(?:Placed\ on|Taken\ from)\ (?:Second\ Reading|General|Resolution)\ File(?:\ for\ next\ legislative\ day)?\.)
| (?P<special>\bMade\ Special\ Order\ of\ Business\ for\ [^.]*?[AP]\.M\.\.?)
| (?P<rescind>\bAction\ of\ (?:referral|rereferral|adoption\ of\ Amendment\ No\.\ \d+|concurrence\ in\ (?:Senate|Assembly)\ Amendment\ No\.\ \d+)\ rescinded\.)
| (?P<amwd>\bAmendment\ No\.\ \d+\ withdrawn\.)
| (?P<preamble>\bPreamble\ adopted(?:,\ as\ amended)?\.|\bTitle\ approved(?:,\ as\ amended)?\.)
| (?P<print>\bTo\ printer\.|\bFrom\ printer\.|\bTo\ (?:re-?)?engrossment\.|\b(?:Re-?)?[Ee]ngrossed\.|\b(?:First|Second|Third|Fourth|Fifth|Sixth)\ reprint\.|\bDispensed\ with\ reprinting\.|\bReprinting\ dispensed\ with\.|\bTo\ committee\.)
""", re.X)


def tally(t):
    """"Yeas: 24, Nays: 18, Excused: 1." -> {"Yeas": 24, "Nays": 18, "Excused": 1} ("None" is 0)."""
    return {k: (0 if n == "None" else int(n)) for k, n in re.findall(r"(Yeas|Nays|Excused|Absent|Not voting):\s*(\d+|None)", t or "")}


def committee_label(c):
    c = text(c).rstrip(".")
    c = re.sub(r"^(?:the )?Committee on ", "", c)
    return c


def tokens(t):
    """A history row's steps in order, and the text no pattern read (for checking the patterns)."""
    out, pos, left = [], 0, []
    for m in TOKENS.finditer(t):
        gap = t[pos:m.start()].strip(" /")
        if gap:
            left.append(gap)
        out.append(m)
        pos = m.end()
    if t[pos:].strip(" /"):
        left.append(t[pos:].strip(" /"))
    return out, left


UNREAD = {}


def load_session(session):
    """Read one session's bills and return (records, bill number -> record index, fetched time, delegation)."""
    lst = load(session, "list")
    parties = _PARTIES.setdefault(session, {})
    for m in load(session, "members"):
        h = CHAMBER.get(m.get("house"))
        pt = {"Democratic": "D", "Republican": "R"}.get(m.get("party"))
        if h and pt:
            parties[(h, full_name(m))] = pt
    # Co-sponsors from the other house are listed under the bill's house (build_data.py's bill_parties() looks names up
    # by the bill's house): each member under the other house's letter too, unless that name is taken there.
    for (h, n), pt in list(parties.items()):
        parties.setdefault(("A" if h == "S" else "S", n), pt)
    path = os.path.join(folder(session), "list.json")
    fetched = datetime.fromtimestamp(os.path.getmtime(path), ZoneInfo(P.TIMEZONE)).strftime("%Y-%m-%d %H:%M") if os.path.exists(path) else ""
    recs, index, texts = [], {}, {}
    bills = lst.get("bills") or {}
    order = lambda k: (KINDS.index(re.match(r"[A-Z]+", k).group(0)), int(re.search(r"\d+", k).group(0)))
    for p in sorted((k for k in bills if re.match(r"(AB|SB|AJR|SJR)\d+$", k)), key=order):
        row = bills[p]
        if "JR" in p and not is_amendment(p, row.get("summary")):
            continue  # memorials and other joint resolutions
        rec, what = record(session, p, row, lst)
        index[p] = len(recs)
        recs.append(rec)
        if what:
            texts[p] = {"statement": what, "label": "From the Legislative Counsel's Digest."}
    with open(os.path.join(P.DATA, f"texts_{session}.json"), "w", encoding="utf-8") as f:
        json.dump(texts, f, ensure_ascii=False)
    return recs, index, fetched, {"SENATE": [], "ASSEMBLY": []}


def adjourned(session):
    """The session's last day: sine die is the 120th day, counted from the first Monday of February."""
    t = date(session, 2, 1)
    while t.weekday() != 0:
        t = t.replace(day=t.day + 1)
    return date.fromordinal(t.toordinal() + 119).isoformat()


def record(session, p, row, lst):
    origin = "A" if p.startswith("A") else "S"
    other = "S" if origin == "A" else "A"
    pg = page(session, p) or {"summary": row.get("summary") or "", "intro": "", "primary": [], "cosponsors": [], "title": row.get("title") or "",
                              "digest": "", "hearings": [], "rows": [], "exempt": False}
    summary_line = pg["summary"] or row.get("summary") or ""
    long_title = pg["title"] or row.get("title") or ""
    amendment = is_amendment(p, summary_line)

    steps = []  # (date, house or "G", wording, kind)
    cur = origin
    passed, failed = {}, set()
    last_vote = {}
    amended_after = {}
    concurred = enrolled = sent = signed = vetoed = to_sos = nosign = False
    conf = set()
    chapter_no = None
    returns_to = None
    deadline = None
    place, comm, refs, first_ref, reported = "committee", None, [], None, []
    introduced = set()
    vote_steps = []
    hearings = sorted(pg["hearings"], key=lambda x: x["date"])
    for d, t in pg["rows"]:
        ms, left = tokens(t)
        for x in left:
            UNREAD[x] = UNREAD.get(x, 0) + 1
        for m in ms:
            g = m.lastgroup
            k = m.group(0)
            H = HOUSE[cur]
            if g == "prefiled":
                steps.append((d, origin, "Prefiled", "prefiled"))
            elif g in ("first", "resread"):
                if cur not in introduced:
                    introduced.add(cur)
                    if cur == origin:
                        steps.append((d, cur, "Introduced", "intro"))
                    else:
                        steps.append((d, cur, f"Read the first time in the {H}", "read1"))
                    if place != "committee" or cur != origin:
                        place = "committee" if cur != origin else place
            elif g == "ref":
                c = committee_label(("Select Committee on " if m.group("sel") else "") + m.group("comm"))
                comm, place = c, "committee"
                refs.append((cur, c))
                if first_ref is None and cur == origin:
                    first_ref = c
                steps.append((d, cur, f"REFERRED TO {c.upper()}", "ref"))
            elif g == "withdrawn":
                place = "floor"
                steps.append((d, cur, f"Taken out of the {committee_label(m.group('wcomm')) + ' Committee' if m.group('wcomm') else 'committee'}", "withdrawn"))
                comm = None
            elif g == "fromc":
                rec = text(m.group("rec")).rstrip(".")
                if rec.startswith("Concur in"):
                    steps.append((d, cur, f"The conference committee's report: {rec[:1].lower() + rec[1:]}", "conf"))
                    continue
                rr = re.search(r"\b(?:and )?re-?refer to (?:the )?(?:Committee on )?(.+)$", rec, re.I)
                c = comm or "committee"
                if rr and not re.search(r"\bdo pass\b|without recommendation", rec, re.I):
                    # "From committee: Re-refer to Committee on X." sends it on without a recommendation.
                    nc = committee_label(rr.group(1))
                    steps.append((d, cur, f"The {c} Committee sent it to the {nc} Committee", "rerefer"))
                    comm = nc
                    refs.append((cur, nc))
                    steps.append((d, cur, f"REFERRED TO {nc.upper()}", "ref"))
                    continue
                reported.append((d, cur, c, rec))
                words = re.sub(r",? and re-?refer to .*$", "", rec, flags=re.I)
                steps.append((d, cur, "REPORTED", "reported"))
                steps.append((d, cur, f"The {c} Committee recommended: {words[:1].lower() + words[1:]}", "report"))
                if rr:
                    nc = committee_label(rr.group(1))
                    comm = nc
                    refs.append((cur, nc))
                    steps.append((d, cur, f"REFERRED TO {nc.upper()}", "ref"))
                else:
                    place, comm = "floor", None
            elif g == "second":
                place = "floor"
                steps.append((d, cur, f"Read the second time in the {H}", "read2"))
            elif g == "third":
                place = "floor"
            elif g == "amended":
                amended_after[cur] = len(steps)
                n = re.search(r"Nos?\.\s*([^)]*)", k)
                steps.append((d, cur, f"Amended in the {H}" + (f" (amendment {n.group(1).strip().rstrip('.')})" if n else ""), "amend"))
            elif g == "passed":
                tl = tally(m.group("tally"))
                first = cur not in passed
                passed[cur] = len(steps)
                failed.discard(cur)
                last_vote[cur] = "pass"
                if m.group("asam"):
                    amended_after[cur] = len(steps)
                vote_steps.append((len(steps), cur, tl, d))
                steps.append((d, cur, f"PASSED {H.upper()}", "pass"))
                if tl:
                    steps.append((d, cur, f"The {H} vote: {tl.get('Yeas', 0)}-{tl.get('Nays', 0)}", "tally"))
                place = "committee" if cur == origin and first else place
            elif g == "lost":
                tl = tally(m.group("ltally"))
                failed.add(cur)
                last_vote[cur] = "fail"
                vote_steps.append((len(steps), cur, tl, d))
                steps.append((d, cur, f"Failed in the {H}" + (f", {tl.get('Yeas', 0)}-{tl.get('Nays', 0)}" if tl else ""), "fail"))
            elif g == "recons":
                if last_vote.get(cur) == "pass":
                    passed.pop(cur, None)
                elif last_vote.get(cur) == "fail":
                    failed.discard(cur)
                last_vote.pop(cur, None)
                place = "floor"
                steps.append((d, cur, f"The {H} voted to reconsider its vote", "rescind"))
            elif g == "concur":
                if m.group("cnot"):
                    steps.append((d, cur, f"The {H} refused to agree to the {m.group('cch')}'s amendments", "noconcur"))
                else:
                    concurred = True
                    steps.append((d, cur, f"The {H} agreed to the {m.group('cch')}'s amendments", "concur"))
            elif g == "recede":
                steps.append((d, cur, f"The {H} {'refused to withdraw' if m.group('rnot') else 'withdrew'} its amendments", "recede"))
            elif g == "confreq":
                steps.append((d, cur, "A conference committee was requested", "confreq"))
            elif g == "confappt":
                pass  # the request says it; each house naming its members isn't news
            elif g == "confadopt":
                h = CHAMBER[m.group("cfh")]
                if not m.group("cfnot"):
                    conf.add(h)
                steps.append((d, h, f"The {HOUSE[h]} {'rejected' if m.group('cfnot') else 'adopted'} the conference committee's report", "ccr"))
            elif g == "enroll":
                enrolled = True
                steps.append((d, cur, "Passed both houses; to enrollment", "enrolled"))
            elif g == "deliv":
                if m.group("to") == "Governor":
                    sent = True
                    steps.append((d, "G", "DELIVERED TO GOVERNOR", "sent"))
                else:
                    to_sos = True
                    steps.append((d, "G", "Filed with the Secretary of State", "sos"))
            elif g == "fileno":
                steps.append((d, "G", f"File No. {m.group('file')}, Statutes of Nevada", "file"))
            elif g == "signed":
                signed = True
                steps.append((d, "G", "Signed by the governor", "signed"))
            elif g == "nosign":
                nosign = True
                steps.append((d, "G", "Became law without the governor's signature", "nosign"))
            elif g == "chapter":
                chapter_no = int(m.group("chap"))
            elif g == "veto":
                vetoed = True
                steps.append((d, "G", "VETOED", "vetoed"))
            elif g == "ret":
                returns_to = m.group("retn")  # "(Return to 83rd Session)": said for every veto after the session, below
            elif g == "vmsg":
                if m.group("vh"):
                    cur = CHAMBER[m.group("vh")]
                else:
                    cur = origin
                steps.append((d, cur, f"The governor's veto message was read in the {HOUSE[cur]}", "vetomsg"))
            elif g == "override":
                tl = tally(m.group("otally"))
                steps.append((d, cur, f"The {H} voted to override the veto" + (f", {tl.get('Yeas', 0)}-{tl.get('Nays', 0)}" if tl else ""), "override"))
            elif g == "nfa":
                steps.append((d, cur if not vetoed else origin, "No further action taken" if vetoed or enrolled else "No further action", "nfa"))
            elif g == "deadline":
                deadline = (d, cur, m.group("rule"))
                steps.append((d, cur, f"Missed a deadline (Joint Standing Rule {m.group('rule')}): no further action allowed", "deadline"))
            elif g == "tohouse":
                cur = CHAMBER[m.group("toh")]
            elif g == "inhouse":
                cur = CHAMBER[m.group("inh")]
            elif g == "emerg":
                steps.append((d, cur, "Declared an emergency measure", "other"))
            elif g == "exempt":
                if re.match(r"Exemption effective|Notice of exemption|Exempt pursuant", k):
                    steps.append((d, cur, "Exempt from the session's deadlines (it spends money or affects revenue)", "exempt"))
                elif k.startswith("Waiver"):
                    steps.append((d, cur, "Granted a waiver of the session's deadlines", "exempt"))
            elif g == "desk":
                steps.append((d, cur, f"Placed on the {'Chief Clerk' if 'Clerk' in k else 'Secretary'}'s desk (held)", "desk"))
            elif g == "special":
                steps.append((d, cur, k.rstrip(".").replace("Made Special Order of Business", "Set as a special order of business") + ".", "other"))
            elif g == "rescind":
                steps.append((d, cur, k.rstrip("."), "other"))
            # Readings onto files, printing and engrossing, titles and preambles: the clerks' steps, not shown.
    # Laws and vetoes from the session's lists (they agree with the histories; they also cover a history cut short).
    law_row = (lst.get("laws") or {}).get(p)
    veto_day = (lst.get("vetoed") or {}).get(p)
    if law_row and not amendment:
        chapter_no = chapter_no or (int(law_row["chapter"]) if str(law_row.get("chapter") or "").isdigit() else None)
        if not (signed or nosign):
            signed = True
            steps.append((max((s[0] for s in steps if s[0]), default=f"{session}-06-30"), "G", "Signed by the governor", "signed"))
    if veto_day and not vetoed:
        vetoed = True
        vd = day_slash(veto_day)
        steps.append((vd, "G", "VETOED", "vetoed"))
    steps.sort(key=lambda s: s[0])  # stable: the site's order within a day
    overridden = sum(1 for s in steps if s[3] == "override") >= 2
    # Vetoes NELIS's records miss (VETO_FIX). Any other bill delivered and neither signed nor vetoed once the governor's
    # time is up says so, without guessing an outcome: under Art. 4, sec. 35 it would be law without signature, but SB 99
    # of 2025 shows the record can simply miss a veto.
    fix = VETO_FIX.get((session, p))
    if fix and not vetoed:
        vetoed = True
        steps.append((fix[0], "G", "VETOED", "vetoed"))
        steps.append((fix[0], "G", fix[1], "other"))
        steps.sort(key=lambda s: s[0])
    elif sent and not (signed or nosign or vetoed or overridden) and not amendment:
        delivered = max(s[0] for s in steps if s[3] == "sent")
        due = gov_due(delivered, session)
        if due and due < date.today().isoformat():
            steps.append((due, "G", "The records show no decision by the governor", "other"))
            steps.sort(key=lambda s: s[0])
    law = bool(signed or nosign or overridden) and not amendment
    both = enrolled or sent or law or vetoed or to_sos or (concurred and origin in passed and other in passed) or conf >= {"A", "S"}
    if both:
        passed.setdefault(origin, -1)
        passed.setdefault(other, -1)
    if amendment:
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
    if stage is None:
        stage = 1 if place == "floor" or origin in failed else 0
    if law and chapter_no:
        when = max((s[0] for s in steps if s[3] in ("signed", "nosign", "override")), default="")
        steps.append((when, "G", f"SIGNED CHAPTER {chapter_no}", "chapter"))
        steps.sort(key=lambda s: s[0])
    chapter = chapter_no if stage == 5 else None
    # A veto after the session goes back to the next regular session, which can override it (two-thirds of each house).
    end = adjourned(session)
    veto_when = max((s[0] for s in steps if s[3] == "vetoed"), default="")
    later = stage == 6 and veto_when > end and not any(s[3] in ("nfa",) and s[0] >= veto_when for s in steps)
    if later:
        # profile.js's STATE.vetoReturns() reads this line.
        steps.append((veto_when, "G", f"Vetoed after the session ended: the veto goes back to the Legislature's {session + 2} session", "return"))
    passed_h = set(passed)
    where_h = cur
    comm_now = comm if place == "committee" and stage in (0, 2) else None
    title = titled(summary_line) or sim_text(long_title)[:150]
    code = bdr(summary_line)
    nrs = P.NRS_TOPICS.get(int(code)) if code.isdigit() else None
    topics = list(dict.fromkeys((["const"] if amendment else []) + ([nrs] if nrs else []) +
                                [P.COMMITTEE_TOPICS[c] for _, c in refs if c in P.COMMITTEE_TOPICS] +
                                [k for k in P.TOPIC_WORDS if P.TOPIC_WORDS[k].search(f"{title} {relating(long_title)}")]))
    if amendment:
        topics = ["const"] + [t for t in topics if t != "const"]
    first_reported = any(h == origin for _, h, _, _ in reported)
    fate = "passed" if first_reported or origin in passed else "none"

    # Sponsors: the primary sponsors (members, or a committee), then co-sponsors.
    names, primes = [], 0
    for group in ("primary", "cosponsors"):
        for x in pg[group]:
            n = sponsor_name(session, x)
            if n and n not in names:
                names.append(n)
                primes += group == "primary"
    first_x = (pg["primary"] or [None])[0]
    district = first_x[2] if first_x and first_x[1] == origin else 0
    if not names and pg["primary"] == [] and page(session, p):
        # A prefiled bill whose sponsoring committee isn't named yet (the next session's committees aren't set up).
        names = [f"A {HOUSE[origin]} committee (not yet named)"]
    sponsor = names[0] if names else "—"
    cos = names[1:]
    by_committee = bool(first_x and first_x[3])
    where = HOUSE.get(where_h, HOUSE[origin])
    if stage == 0:
        desc = f"In {where} committee" if comm_now else f"In {where} committee"
    elif stage == 1:
        desc = f"Failed in the {HOUSE[origin]}" if origin in failed else f"On the {where} floor"
    else:
        desc = {2: f"Passed the {HOUSE[origin] if origin in passed_h else HOUSE[other]}" + (f"; failed in the {HOUSE[other]}" if other in failed else ""),
                3: "Passed both houses", 4: "On the governor's desk", 5: "Became law", 6: "Vetoed"}[stage]

    def dates(test, mode="last"):
        ds = sorted({s[0] for s in steps if test(s) and s[0]})
        return {"first": ds[0], "last": ds[-1], "all": ";".join(ds)}[mode] if ds else ""

    votes = floor_votes(session, p, vote_steps)
    action_dates = [s[0] for s in steps if s[0]]
    what = digest_text(pg["digest"])
    budget = bool(re.match(r"(?:Makes|Authorizes) (?:an? |certain |supplemental )*(?:appropriations?|expenditures?)\b", title)) or \
        bool(re.search(r"\bbudget\b|\bbiennium\b.*\bappropriat", title, re.I) and code == "S")
    rec = {
        "nums": [p], "base": [p], "prev": earlier(session, p, row, pg),
        "title": title, "summary": long_title,
        "act": "", "lawCode": "", "law": None, "laws": [],
        "comms": sorted({f"{h} · {c}" for h, c in refs}), "topics": topics, "places": [], "narrow": P.narrow_kind(title),
        "commFate": fate, "mainTopic": topics[0] if topics else "", "local": "local" in topics,
        "senDeleg": False, "asmDeleg": False, "budget": budget,
        "passedS": "S" in passed_h, "passedA": "A" in passed_h, "program": None,
        "stage": stage, "passedIn": (HOUSE[origin] if origin in passed_h else HOUSE[other]) if stage == 2 else None,
        "chapter": chapter, "veto": None, "memo": "", "vetoMemo": None,
        "simText": f"{title} {sim_text(long_title)} {'' if amendment else what[:600]}",
        "comm": comm_now if stage == 0 else None,
        "first": min(action_dates, default=pg["intro"] or f"{session}-02-01"),
        "last": max(action_dates, default=pg["intro"] or f"{session}-02-01"),
        "cosp": len(cos),
        "keyDates": [
            dates(lambda s: s[3] == "reported", "first"),
            dates(lambda s: s[2] == "PASSED SENATE", "all"),
            dates(lambda s: s[2] == "PASSED ASSEMBLY", "all"),
            "",
            dates(lambda s: s[3] == "sent"),
            dates(lambda s: s[3] in ("signed", "nosign")) if stage == 5 else "",
            dates(lambda s: s[3] == "vetoed"),
        ],
        "votes": votes, "firstComms": [(origin, first_ref, bool(first_reported) or origin in passed)] if first_ref else [],
        "vers": [{"p": p, "sponsor": sponsor, "district": district, "cosponsors": cos, "primes": max(1, primes), "cosp": len(cos),
                  "statusDesc": desc, "committee": comm_now,
                  "link": f"https://www.leg.state.nv.us/App/NELIS/REL/{lst.get('session') or P.session_code(session)}/Bill/{row['key']}/Overview" if row.get("key") else "",
                  "actions": [[s[0], s[2]] for s in steps]}],
    }
    if by_committee:
        rec["vers"][0]["byCommittee"] = True
    if later:
        rec["vetoReturns"] = session + 2
    if deadline and stage <= 2:
        rec["deadline"] = deadline[2]
    if not page(session, p):
        rec["missing"] = True
    return rec, what


def gov_due(delivered, session):
    """The last day for the governor to act on a bill delivered that day: 5 days, Sundays excepted, during the session;
    10 days after adjournment when the session ends first (profile.js's govDeadline())."""
    end = adjourned(session)
    if delivered >= end:
        return date.fromordinal(date.fromisoformat(end).toordinal() + 10).isoformat()
    t, n = date.fromisoformat(delivered), 5
    while n:
        t = date.fromordinal(t.toordinal() + 1)
        n -= t.weekday() != 6
    return t.isoformat() if t.isoformat() <= end else date.fromordinal(date.fromisoformat(end).toordinal() + 10).isoformat()


def day_slash(s):
    """"6/5/2025" -> "2025-06-05"."""
    m = re.match(r"(\d{1,2})/(\d{1,2})/(\d{4})", text(s))
    return date(int(m.group(3)), int(m.group(1)), int(m.group(2))).isoformat() if m else ""


def floor_votes(session, p, vote_steps):
    """The bill's final passage votes, member by member ("N" no, "E" excused, "A" absent, "B" not voting; yes is left
    out), each matched to its history line by house, day and tally. NELIS marks every one "Passed", lost votes too, so
    the history line decides the result; a line with no roll call keeps its tally."""
    vf = votes_file(session, p) or {}
    rolls = [v for v in vf.get("votes") or [] if v.get("type") == "Final Passage"]
    used, out = set(), []
    for i, h, tl, d in vote_steps:
        def fits(v, same_day):
            c = v.get("counts") or {}
            return (CHAMBER.get(text(v.get("house")).split(" (")[0]) == h and (not same_day or v.get("date") == d)
                    and (not tl or (c.get("Yea"), c.get("Nay")) == (tl.get("Yeas", 0), tl.get("Nays", 0))))
        cands = [v for v in rolls if v.get("key") not in used and fits(v, True)] or \
                [v for v in rolls if v.get("key") not in used and fits(v, False) and tl]
        v = cands[0] if cands else None
        if v:
            used.add(v.get("key"))
            c = v.get("counts") or {}
            listed = []
            for name, how in v.get("members") or []:
                code = {"Nay": "N", "Excused": "E", "Absent": "A", "Not Voting": "B"}.get(how)
                if code:
                    listed.append([seat_of(session, h, name), code])
            out.append([h, "F", None, d, int(c.get("Yea") or 0), int(c.get("Nay") or 0), listed])
        elif tl:
            out.append([h, "F", None, d, tl.get("Yeas", 0), tl.get("Nays", 0), []])
    return out


# ---- earlier sessions ------------------------------------------------------------------------------------------------

_KEYS = {}
STOP = {"and", "the", "certain", "provisions", "relating", "revising", "providing", "other", "matters", "properly", "thereto",
        "governing", "revises", "makes", "various", "changes", "this", "state", "for", "with"}


def _norm(s):
    return re.sub(r"[^a-z0-9 ]", "", text(s).lower())


def _words(s):
    return set(re.findall(r"[a-z]{3,}", text(s).lower())) - STOP


def _member_key(x):
    """A sponsor entry -> (house, last name), for matching across sessions; None for a committee."""
    name, h, _, comm = x
    return (h, text(name).split()[-1].lower()) if h and not comm else None


def _keys(session):
    """A session's bills that didn't become law (not appropriations): [(bill, official title, title words, summary
    words, member sponsor)]."""
    if session not in _KEYS:
        lst, out = load(session, "list"), []
        for p, row in (lst.get("bills") or {}).items():
            if not re.match(r"(AB|SB)\d+$", p) or p in (lst.get("laws") or {}):
                continue
            pg = page(session, p) or {}
            t = sim_text(pg.get("title") or row.get("title"))
            if re.search(r"\bappropriation|\bbudget\b", t):
                continue
            x = (pg.get("primary") or [None])[0]
            out.append((p, _norm(t), _words(t), _words(titled(row.get("summary"))), _member_key(x) if x else None))
        _KEYS[session] = out
    return _KEYS[session]


def earlier(session, p, row, pg):
    """The same bill in the session before: the same official title (one bill with it in each session), or a bill from
    the same member whose title and one-line summary share most of their words (checked by hand 2026-11-09: 23 links
    from 2025 to 2023, all the same proposal). Never appropriations, or bills that became law."""
    y = session - 2
    if y not in sessions() or "JR" in p:
        return set()
    t = sim_text(pg.get("title") or row.get("title"))
    if len(t.split()) < 6 or re.search(r"\bappropriation|\bbudget\b", t):
        return set()
    old, mine = _keys(y), _keys(session)
    same = [q for q, n, _, _, _ in old if n == _norm(t)]
    if len(same) == 1 and sum(1 for _, n, _, _, _ in mine if n == _norm(t)) == 1:
        return {(y, same[0])}
    x = (pg.get("primary") or [None])[0]
    mk = _member_key(x) if x else None
    if not mk:
        return set()
    w, sw = _words(t), _words(titled(row.get("summary")))
    jac = lambda a, b: len(a & b) / max(1, len(a | b))
    best = max(((jac(w, ow), q) for q, _, ow, osw, omk in old if omk == mk and jac(w, ow) >= 0.6 and jac(sw, osw) >= 0.4),
               default=None)
    return {(y, best[1])} if best else set()


# ---- hearings and parties -----------------------------------------------------------------------------------------------

def agendas(session):
    """Bills on upcoming committee hearings: bill -> [["Assembly Commerce and Labor", "2027-02-10T13:30:00"], ...]."""
    today = date.today().isoformat()
    out = {}
    for p in (load(session, "list").get("bills") or {}):
        pg = page(session, p)
        for x in (pg or {}).get("hearings") or []:
            if x["date"] < today:
                continue
            c = re.sub(r"^(Assembly|Senate) Committee on ", r"\1 ", x["committee"])
            try:
                t = datetime.strptime(x["time"], "%I:%M %p").strftime("%H:%M:00")
            except ValueError:
                t = "00:00:00"
            entry = [c, f"{x['date']}T{t}"]
            if entry not in out.setdefault(p, []):
                out[p].append(entry)
    return out


def parties(session, recs):
    if session not in _PARTIES:
        load_session(session)
    return {k: v for k, v in _PARTIES.get(session, {}).items() if v in ("D", "R")}


if __name__ == "__main__":
    import collections, sys
    for s in ([int(sys.argv[1])] if len(sys.argv) > 1 else sessions()):
        recs, _, _, _ = load_session(s)
        st = collections.Counter(r["stage"] for r in recs)
        lst = load(s, "list")
        laws = {p for p in lst.get("laws") or {} if re.match(r"(AB|SB)\d+$", p)}
        vetoes = set(lst.get("vetoed") or {})
        mine_laws = {r["nums"][0] for r in recs if r["stage"] == 5}
        mine_vetoes = {r["nums"][0] for r in recs if r["stage"] == 6}
        print(s, len(recs), dict(sorted(st.items())), f"laws {len(mine_laws)} (list {len(laws)}; differ {sorted(mine_laws ^ laws)[:6]}),"
              f" vetoes {len(mine_vetoes)} (list {len(vetoes)}; differ {sorted(mine_vetoes ^ vetoes)[:6]}),"
              f" returning {sum(1 for r in recs if r.get('vetoReturns'))}")
    for k, n in sorted(UNREAD.items(), key=lambda x: -x[1])[:25]:
        print(n, k[:160])
