"""Congress's bills (downloaded by states/us/fetch.py from GovInfo's BILLSTATUS bulk data) in the shape build_data.py
reads: House and Senate bills (HR, S) and joint resolutions (HJRES, SJRES) of each two-year Congress, one record each.
Joint resolutions proposing an amendment to the Constitution of the United States are tagged "const"; other joint
resolutions (continuing appropriations, disapprovals of agency rules under the Congressional Review Act, ...) go to
the President like bills. Simple and concurrent resolutions (H.Res., S.Con.Res. ...) aren't downloaded. Companion
bills (the same bill introduced in each house, marked "Identical bill" by the Congressional Research Service) are one
record with both numbers, as New York's identical bills are (pair_identical()).

Each bill's actions come three times over: the House's own lines (sourceSystem "House floor actions" / "House committee
actions", with codes like H11100 and times), the Senate's (no codes), and the Library of Congress's summary lines (codes
1000 introduced in the House, 10000 in the Senate, 5000/14000 reported, 5500/14500 committee discharged, 8000 passed the
House, 9000 failed in the House, 17000 passed the Senate, 18000 failed there, 19500/20500 resolving differences, 21000/
23000 conference report agreed to, 28000 presented to the President, 31000 vetoed, 33000/35000 failed over a veto,
36000 became law), which repeat a House or Senate line with a prefix ("Passed/agreed to in House: On motion to suspend
the rules and pass the bill, as amended Agreed to by voice vote."). The history shows each line once (the Library's
wording where it names the house), and the Library's codes decide the milestones.

How a bill moves: introduced and referred to one or more committees (the House often refers a bill to several, "and
in addition to"); a committee marks it up and reports it, or is discharged (often to let a bill pass under suspension);
it goes on a calendar (the House's Union or House Calendar, the Senate's Legislative Calendar). The House passes most
bills "under suspension of the rules" (40 minutes of debate, no amendments, two-thirds of those voting), the rest
under a rule from the Rules Committee. The Senate passes most bills by unanimous consent; others need cloture (60
votes) to end debate. When the second house passes a bill "with an amendment", the first has to agree, or agree with a
further amendment, or go to conference; when both houses have agreed to the same text it's enrolled and presented to
the President, who has 10 days (Sundays excepted) to sign or veto it; a bill not returned becomes law without the
signature, unless Congress has adjourned, which makes it a pocket veto. Overriding a veto takes two-thirds of each
house. A bill can also pass as part of another ("Senate incorporated this measure in H.R. 2670 as an amendment").

Floor votes are the roll calls on the bill's own questions (own_vote()): passage, suspension, agreeing to the other
house's amendment, conference reports, overrides, and the Senate's cloture votes and motions to proceed; member by
member from the House Clerk's and the Senate's XML where fetch.py has read them (data/us/<congress>/votes/), else the
tally from the action's wording. Committee votes are tallies from the House committees' markup lines ("Ordered to be
Reported (Amended) by the Yeas and Nays: 29 - 20."), no names.

"What it does" is the Congressional Research Service's latest summary (in the BILLSTATUS file), labelled with the
version it describes.
"""
import glob, html, io, json, os, re, xml.etree.ElementTree as ET, zipfile
from collections import Counter, defaultdict
from datetime import date, datetime
from zoneinfo import ZoneInfo

from states.us import profile as P
from states.undated import settle

# The 117th Congress (2021-22) onward, to the current one (the 120th from January 3, 2027). The 117th is older than the
# shared window's 2023 (states/window.py) but was kept from the start, as California's and Illinois's 2021 are: it gives
# the 118th its earlier versions and the statistics a second finished Congress.
CONGRESSES = list(range(117, P.congress_of(P.session_of(date.today().year)) + 1))
TYPES = ("hr", "s", "hjres", "sjres")
HOUSE = {"S": "Senate", "H": "House"}
OTHER = {"S": "H", "H": "S"}
PREFIX = {"HR": "HR", "S": "S", "HJRES": "HJRES", "SJRES": "SJRES"}
_CACHE, _PARTIES, _MEMBERS = {}, {}, {}


def folder(congress):
    return os.path.join(P.DATA, str(congress))


def sessions():
    return sorted(P.session_of_congress(c) for c in CONGRESSES
                  if glob.glob(os.path.join(folder(c), "BILLSTATUS-*-hr.zip")))


def text(x):
    return re.sub(r"\s+", " ", html.unescape(x or "")).strip()


# ---- reading the files --------------------------------------------------------------------------------------------

def bill_files(congress):
    """{"BILLSTATUS-118hr815.xml": (zip path or None, file path or name)}: the zips' files, with fetch.py's newer copies
    (updates/) in their place."""
    out = {}
    for t in TYPES:
        path = os.path.join(folder(congress), f"BILLSTATUS-{congress}-{t}.zip")
        if not os.path.exists(path):
            continue
        with zipfile.ZipFile(path) as z:
            for n in z.namelist():
                if n.endswith(".xml"):
                    out[n] = (path, n)
    for p in glob.glob(os.path.join(folder(congress), "updates", f"BILLSTATUS-{congress}*.xml")):
        out[os.path.basename(p)] = (None, p)
    return out


def raw_bills(congress):
    """(number, <bill> element) for each bill, one at a time (the parsed files would take gigabytes together)."""
    files = bill_files(congress)
    zips = {}
    try:
        for n in sorted(files):
            zp, name = files[n]
            if zp:
                if zp not in zips:
                    zips[zp] = zipfile.ZipFile(zp)
                data = zips[zp].read(name)
            else:
                data = open(name, "rb").read()
            try:
                b = ET.fromstring(data).find("bill")
            except ET.ParseError:
                continue
            if b is None or b.findtext("type") not in PREFIX:
                continue
            yield PREFIX[b.findtext("type")] + b.findtext("number"), b
    finally:
        for z in zips.values():
            z.close()


def actions(b):
    """Each action, oldest first: {date, time, code, type, src ("L" Library, "H" House, "S" Senate), text, comm, votes}.
    The file lists them newest first."""
    out = []
    acts = b.find("actions")
    for a in reversed(list(acts) if acts is not None else []):
        src = a.findtext("sourceSystem/name") or ""
        out.append({
            "date": a.findtext("actionDate") or "", "time": a.findtext("actionTime") or "",
            "code": a.findtext("actionCode") or "", "type": a.findtext("type") or "",
            "src": "L" if src.startswith("Library") else "H" if src.startswith("House") else "S",
            "text": text(a.findtext("text")),
            "comm": [text(c.findtext("name")) for c in a.findall("committees/item")],
            "votes": [(v.findtext("chamber") or "", v.findtext("rollNumber") or "", v.findtext("url") or "",
                       v.findtext("sessionNumber") or "", v.findtext("date") or "") for v in a.iter("recordedVote")],
        })
    out.sort(key=lambda a: a["date"])  # by day, keeping the file's order within a day
    return out


LOC_PREFIX = re.compile(r"^(?:Passed/agreed to in (?:House|Senate):|Failed of passage/not agreed to in (?:House|Senate):?|"
                        r"Resolving differences -- (?:House|Senate) actions:|Conference report agreed to in (?:House|Senate):|"
                        r"Failed of passage in (?:House|Senate) over veto:?|Passed (?:House|Senate) over veto:|"
                        r"Conference report filed in House:)\s*")


CR_REF = re.compile(r"\s*\((?:text(?: of [^:)]*)?|consideration|CR)\b[^)]*\)(?:\s*;\s*\((?:text|consideration)[^)]*\))*")


def norm(t):
    return re.sub(r"[^a-z0-9]", "", LOC_PREFIX.sub("", t).lower())


# ---- members and seats --------------------------------------------------------------------------------------------

def congress_dates(congress):
    s = P.session_of_congress(congress)
    return f"{s}-01-03", f"{s + 2}-01-03"


def legislators():
    if "all" not in _MEMBERS:
        ms = []
        for name in ("legislators-historical", "legislators-current"):
            path = os.path.join(P.DATA, "members", f"{name}.json")
            if os.path.exists(path):
                ms += json.load(open(path))
        _MEMBERS["all"] = ms
    return _MEMBERS["all"]


def senate_letters():
    """Each state's two Senate classes: the lower is seat "a", the higher "b"."""
    if "letters" not in _MEMBERS:
        classes = defaultdict(set)
        for m in legislators():
            for t in m["terms"]:
                if t["type"] == "sen" and t.get("class") and t["start"] >= "1990":
                    classes[t["state"]].add(t["class"])
        _MEMBERS["letters"] = {st: {c: "ab"[i] for i, c in enumerate(sorted(cs)[:2])} for st, cs in classes.items()}
    return _MEMBERS["letters"]


def full_name(m):
    n = m["name"]
    return n.get("official_full") or " ".join(x for x in (n.get("first"), n.get("middle") if False else None, n.get("last"), n.get("suffix")) if x)


PARTY = {"Democrat": "Democratic", "Republican": "Republican", "Independent": "Independent",
         "Libertarian": "Libertarian", "Popular Democrat": "Popular Democratic", "New Progressive": "New Progressive"}


def members(congress):
    """Every member who served in this Congress: bioguide -> {name, last, lis, seats: {house: seat id}, party, end}.
    A member who served in both houses (Adam Schiff in the 118th) has a seat in each."""
    key = ("members", congress)
    if key in _MEMBERS:
        return _MEMBERS[key]
    start, end = congress_dates(congress)
    out = {}
    letters = senate_letters()
    for m in legislators():
        ts = [t for t in m["terms"] if t["start"] < end and t["end"] > start]
        if not ts:
            continue
        seats, last = {}, None
        for t in ts:
            st = t["state"]
            if st not in P.STATES:
                continue
            if t["type"] == "sen":
                letter = letters.get(st, {}).get(t.get("class"), "a")
                seats["S"] = f"S:{P.STATES[st][1]}{letter}"
            else:
                seats["H"] = f"H:{P.house_seat(st, t.get('district') or 0)}"
            last = t
        if not seats:
            continue
        out[m["id"]["bioguide"]] = {
            "name": full_name(m), "last": m["name"]["last"], "lis": m["id"].get("lis"), "seats": seats,
            "party": PARTY.get(last.get("party"), last.get("party") or ""), "end": max(t["end"] for t in ts),
            "start": min(t["start"] for t in ts), "term": last, "terms": ts, "bio": m,
        }
    _MEMBERS[key] = out
    return out


def by_lis(congress):
    return {v["lis"]: k for k, v in members(congress).items() if v.get("lis")}


def seat_of(congress, bioguide, house):
    m = members(congress).get(bioguide)
    return (m or {}).get("seats", {}).get(house)


# ---- roll calls ---------------------------------------------------------------------------------------------------

CLOTURE = re.compile(r"\bcloture\b.*\b(?:not )?invoked\b|\bMotion to proceed to (?:consideration of )?(?:the )?measure (?:agreed to|rejected|not agreed to)", re.I)


def vote_file(chamber, url):
    """The name fetch.py saves a roll call under, from its address."""
    m = re.search(r"/evs/(\d{4})/roll(\d+)\.xml", url)
    if m:
        return f"house_{m.group(1)}_{int(m.group(2))}.xml"
    m = re.search(r"vote_(\d+)_(\d+)_(\d+)\.xml", url)
    if m:
        return f"senate_{m.group(2)}_{int(m.group(3))}.xml"
    return None


def wanted_votes(congress):
    """{(chamber, roll file name): (file name, address)} for every roll call on a bill's own question."""
    out = {}
    for p, b in raw_bills(congress):
        for a in actions(b):
            if not a["votes"] or not own_vote(a):
                continue
            for chamber, roll, url, _, _ in a["votes"]:
                name = vote_file(chamber, url)
                if name:
                    out[(chamber, name)] = (name, url)
    return out


PASS_CODES = {"8000", "9000", "17000", "18000", "19500", "20500", "21000", "23000", "32000", "33000", "34000", "35000"}
OWN = re.compile(r"suspend the rules and (?:pass|agree)|^On passage|\bpass(?:ed)? (?:the )?(?:bill|joint resolution|Senate|House)|"
                 r"agree (?:with an amendment )?to the (?:Senate|House) amendment|agreed to the (?:House|Senate) amendment|"
                 r"concur|conference report|over veto|objections of the President|Passed Senate|Failed of passage", re.I)
NOT_OWN = re.compile(r"\(SA ?\d+\)|suspend the operation of Rule|Rule XXV|recommit|\bto reconsider\b|to table|motion to instruct|instruct (?:the )?conferees|close portions|amendment No\.|"
                     r"amendment SA \d|point of order|budgetary discipline|waive|to refer|previous question|"
                     r"amendments? (?:en bloc )?(?:offered|numbered)|appeal the ruling", re.I)


def own_vote(a):
    """Whether an action's roll call is on the bill's own question (not an amendment or a procedural motion)."""
    t = a["text"]
    if NOT_OWN.search(t) and not re.search(r"^Cloture on the motion to concur", t):
        return False
    return bool(a["code"] in PASS_CODES or OWN.search(t) or (a["src"] == "S" and CLOTURE.search(t)))


VOTE_CODE = {"Nay": "N", "No": "N", "Not Voting": "A", "Present": "B", "Present, Giving Live Pair": "B"}


def roll(congress, name):
    """(yes, no, [[seat or "H?Name", code], ...]) from a downloaded roll call, or None."""
    path = os.path.join(folder(congress), "votes", name)
    if not os.path.exists(path):
        return None
    try:
        r = ET.parse(path).getroot()
    except ET.ParseError:
        return None
    listed, yes, no = [], 0, 0
    if r.tag == "rollcall-vote":
        for rv in r.iter("recorded-vote"):
            leg = rv.find("legislator")
            v = (rv.findtext("vote") or "").strip()
            if v in ("Yea", "Aye"):
                yes += 1
                continue
            if v in ("Nay", "No"):
                no += 1
            code = VOTE_CODE.get(v, "A")
            sid = seat_of(congress, leg.get("name-id"), "H")
            listed.append([sid or f"H?{text(leg.text)}", code])
    else:
        if (r.findtext("tie_breaker/by_whom") or "").strip():
            listed.append(["TIE", "VP"])  # (taken off by _vote(): the Vice President broke a tie)
        lis = by_lis(congress)
        for m in r.iter("member"):
            v = (m.findtext("vote_cast") or "").strip()
            if v in ("Yea", "Guilty"):
                yes += 1
                continue
            if v in ("Nay", "Not Guilty"):
                no += 1
            sid = seat_of(congress, lis.get(m.findtext("lis_member_id")), "S")
            listed.append([sid or f"S?{text(m.findtext('last_name'))}", VOTE_CODE.get(v, "A")])
    return yes, no, listed


TALLY = re.compile(r"(?:Yeas and Nays|recorded vote|Yea-Nay Vote)[:.]?\s*:?\s*(\d+)\s*-\s*(\d+)", re.I)


# ---- titles, summaries, topics --------------------------------------------------------------------------------------

OFFICIAL_STYLE = re.compile(r"^(?:To |A bill |An act |An Act |Making |Providing |Proposing |Relating |Disapproving |Authorizing |For the relief )")
SHORT_ORDER = ["Short Titles as Enacted", "Short Title(s) as Passed Senate", "Short Titles as Passed Senate",
               "Short Title(s) as Passed House", "Short Titles as Passed House", "Short Title(s) as Reported to Senate",
               "Short Title(s) as Reported to House", "Short Title(s) as Introduced", "Short Titles as Introduced"]


def titles(b):
    """(title, summary line): congress.gov's display title, or, when that's an official title ("To amend ..."), the bill's
    own short title ("One Big Beautiful Bill Act" for H.R. 1 of the 119th, whose display title is "An act to provide for
    reconciliation ..."), never one for a portion of the bill; and its latest official title."""
    disp, official, short = text(b.findtext("title")), "", {}
    for t in b.findall("titles/item"):
        kind = t.findtext("titleType") or ""
        if kind == "Display Title":
            disp = text(t.findtext("title")) or disp
        elif kind.startswith("Official Title") and not official:
            official = text(t.findtext("title"))
        elif kind in SHORT_ORDER and kind not in short:
            short[kind] = text(t.findtext("title"))
    if OFFICIAL_STYLE.match(disp):
        best = next((short[k] for k in SHORT_ORDER if k in short), "")
        if best:
            if not official:
                official = disp
            disp = best
    return disp, official


VERSION_WORDS = [
    (r"^Public Law|^Became Private Law|^Private Law", "of the law as enacted"),
    (r"Passed Senate amended|Senate agreed to House amendment|House agreed to Senate amendment|^Conference report", "of the version both houses agreed to"),
    (r"^Passed Senate", "as passed by the Senate"), (r"^Passed House", "as passed by the House"),
    (r"^Reported to Senate", "as reported to the Senate"), (r"^Reported to House", "as reported to the House"),
    (r"^Introduced", "as introduced"),
]


def crs_summary(b, limit=4000):
    """The latest CRS summary as plain paragraphs (cut at a paragraph near the limit), and its label."""
    best = None
    for s in b.findall("summaries/summary"):
        key = (s.findtext("actionDate") or "", s.findtext("updateDate") or "")
        if best is None or key > best[0]:
            best = (key, s)
    if best is None:
        return "", ""
    s = best[1]
    raw = s.findtext("cdata/text") or s.findtext("text") or ""
    raw = re.sub(r"\s+", " ", raw)
    raw = re.sub(r"</(?:p|li|ul|ol|h\d|div)>|<br\s*/?>", "\n", raw, flags=re.I)
    raw = re.sub(r"<li[^>]*>", "\n- ", raw, flags=re.I)
    paras = [text(re.sub(r"<[^>]+>", "", x)) for x in raw.split("\n")]
    paras = [x for x in paras if x]
    # The first paragraph is often the bill's short title alone ("<b>Removing Extraneous ... Act</b>").
    if paras and len(paras) > 1 and not re.search(r"[.:;]$", paras[0]) and len(paras[0]) < 300:
        paras = paras[1:]
    out, n = [], 0
    for x in paras:
        if n + len(x) > limit and out:
            break
        out.append(x)
        n += len(x)
    if not out:
        return "", ""
    what = s.findtext("actionDesc") or ""
    words = next((w for pat, w in VERSION_WORDS if re.search(pat, what)), "")
    label = f"From the Congressional Research Service's summary{' ' + words if words else ''}."
    more = len(out) < len(paras)
    return "\n".join(out) + ("\n(The summary goes on; the full text is on congress.gov.)" if more else ""), label


def subjects(b):
    return [text(x.findtext("name")) for x in b.findall("subjects/legislativeSubjects/item")]


def committee_name(n):
    """"Veterans' Affairs Committee", "House Committee on Veterans' Affairs" -> "Veterans' Affairs"; the House's own
    "House Administration Committee" keeps its "House"."""
    n = text(n)
    n = re.sub(r"^(?:House |Senate )?Committee on (?:the )?", "", n)
    n = re.sub(r" Committee$", "", n)
    return re.sub(r" \((?:Permanent )?Select\)$", "", n)  # "Intelligence (Permanent Select)"


BUDGET = re.compile(r"^(?:Making (?:further )?(?:continuing |consolidated |emergency supplemental |supplemental |)appropriations|"
                    r"Making appropriations)|\bAppropriations Act, \d{4}|Continuing Appropriations|"
                    r"provide for reconciliation pursuant to", re.I)
AMENDMENT = re.compile(r"Proposing an amendment to the Constitution of the United States", re.I)


# ---- one bill ------------------------------------------------------------------------------------------------------

ROUTINE_LINE = re.compile(
    r"^(?:Motions? to reconsider laid on the table|DEBATE - |Considered under (?:suspension|the provisions of rule)|"
    r"Consideration by House|.*moved to suspend the rules|At the conclusion of debate|POSTPONED PROCEEDINGS|"
    r"The previous question was ordered|Considered as unfinished business|Message on (?:Senate|House) action sent|"
    r"Considered by Senate\.|Measure laid before Senate|Motion to proceed to (?:consideration of )?measure (?:made|considered)|"
    r"Cloture motion (?:on .*?)?presented|Cloture motion on the measure presented|Under the order of .* the motion to proceed was withdrawn|"
    r"The House (?:resolved|rose)|House resolved itself|The Speaker designated|The House rose from|Committee of the Whole House .* rises|"
    r"GENERAL DEBATE|The Chair (?:announced|laid before)|Pursuant to clause|UNFINISHED BUSINESS|"
    r"Sponsor introductory remarks|Rule provides for|Rules Committee Resolution|Mr\.|Ms\.|Mrs\.)", re.I)
AMEND_MSG = re.compile(r"(?:House|Senate) amendments? to (?:the )?(?:Senate|House) (?:bill|joint resolution|amendments?)|"
                       r"concur in the (?:House|Senate) amendment|(?:House|Senate) message to accompany|"
                       r"with (?:the|an) (?:House|Senate) amendment|agree(?:d)? (?:with an amendment )?to the (?:House|Senate) amendment", re.I)
# Paperwork and debate that come with a real step: left out of the history.
NOISE_CODES = {"H38310", "H30000", "H37220", "H37210", "H35000", "H32700", "H32050", "H32341", "H32020", "H32600", "H8A000",
               "H30300", "H41931", "H41400", "H40142", "H40140", "H40150", "H42831", "H40200", "H1L210", "H8B000"}
NOISE = re.compile(
    r"^(?:DEBATE - |GENERAL DEBATE|POSTPONED PROCEEDINGS|UNFINISHED BUSINESS|ORDER OF BUSINESS|Rule provides for|"
    r"Message on (?:Senate|House) action|Considered by Senate|Measure laid before Senate|Motion to proceed to measure considered|"
    r"Motion to proceed to consideration of measure made|Cloture motion .*presented|Star Print ordered|"
    r"Motion by Senator .* made in Senate|Motions? to reconsider laid on the table|Considered as unfinished business|"
    r"The previous question was ordered|Pursuant to a previous order of the House|The House resolved|House resolved itself|"
    r"The House rose|Committee of the Whole House on the state of the Union rises|On motion that the committee rise|"
    r"At the conclusion of debate|Considered under (?:suspension|the provisions of rule)|Consideration by House|"
    r"(?:Mr|Ms|Mrs)\. .{2,40}? (?:moved|asked unanimous consent)|Conference papers:|Under the order of .* withdrawn|"
    r"Cloture motion on .* withdrawn|The Speaker designated|The Chair announced|MODIFICATION TO CONFEREES|POSTPONED CONSIDERATION|"
    r"The Chair directed the Clerk|Conference report considered in Senate|The committee substitute withdrawn)", re.I)
# Placed on a calendar: on the floor.
CAL = re.compile(r"^Placed on (?:the )?(?:Union|House|Senate Legislative|Private) Calendar|Placed on Senate Legislative Calendar|"
                 r"Read the second time\. Placed on Senate Legislative Calendar|Placed on the Corrections Calendar|"
                 r"Placed on the Discharge Calendar", re.I)


def record(congress, p, b):
    session = P.session_of_congress(congress)
    btype = b.findtext("type")
    origin = "S" if btype in ("S", "SJRES") else "H"
    other = OTHER[origin]
    title, official = titles(b)
    amendment = btype in ("HJRES", "SJRES") and bool(AMENDMENT.search(f"{official} {title}"))
    acts = actions(b)

    # One line per event: a Library of Congress line and the House's or Senate's own line saying the same thing are one.
    seen, lines = {}, []
    for a in acts:
        if not a["text"]:
            continue
        # (Congress.gov's wording doubles "the" before some subcommittees: "Referred to the The Subcommittee on ...".)
        a["text"] = re.sub(r"\b([Tt]he) The\b", r"\1", CR_REF.sub("", a["text"]).strip())
        k = (a["date"], norm(a["text"]))
        # (The Library's copy of a line sometimes leaves off the end of the Senate's: "Passed Senate with an amendment by
        # Voice Vote." and "... by Voice Vote. (text of amendment ...)". The longer one names the same event.)
        if k not in seen and len(k[1]) >= 25:
            k = next((x for x in seen if x[0] == a["date"] and isinstance(x[1], str) and len(x[1]) >= 25
                      and (x[1].startswith(k[1]) or k[1].startswith(x[1]))), k)
        # (The same roll call on two lines, the Library's and the House's own: one event.)
        rk = (a["date"], tuple(sorted((v[0], v[1]) for v in a["votes"]))) if a["votes"] else None
        if k not in seen and rk and rk in seen:
            k = rk
        if k in seen:
            first = seen[k]
            first["codes"].add(a["code"])
            if a["src"] == "L" and LOC_PREFIX.match(a["text"]):
                first["text"] = a["text"]  # the Library's wording names the house
            first["votes"] = first["votes"] or a["votes"]
            first["comm"] = first["comm"] or a["comm"]
            if a["src"] != "L":
                first["src"] = a["src"]
            continue
        a = dict(a, codes={a["code"]})
        seen[k] = a
        if rk:
            seen.setdefault(rk, a)
        lines.append(a)

    steps = []  # (date, house or "G", wording, kind)
    passed, failed = {}, set()
    pending = {"S": set(), "H": set()}  # committees the bill is in, by house
    refs, first_ref, reported, discharged = [], None, False, False
    place, where_h = "committee", origin
    presented = signed = vetoed = law = pocket = no_sign = False
    law_no, law_kind = "", ""
    both = amended_by = None
    agree = set()       # houses that agreed to the same text after the second house changed it
    conf = set()        # houses that adopted the conference report
    overrides, sustained = set(), False
    votes, comm_votes = [], []
    into = None         # passed as part of another bill
    topic_comms = set()

    def add(d, h, w, k):
        steps.append((d, h, w, k))

    for a in lines:
        d, t, codes = a["date"], a["text"], a["codes"]
        if (codes & NOISE_CODES or NOISE.search(t)) and not codes & PASS_CODES:
            continue
        if t.startswith("The Speaker appointed conferees"):
            if steps and steps[-1][2] == "The Speaker named the House's conferees" and steps[-1][0] == d:
                continue
            t = a["text"] = "The Speaker named the House's conferees"
        h = "H" if a["src"] == "H" else "S" if a["src"] == "S" else ("H" if re.search(r"\bin House\b|House actions|^Introduced in House", t) else "S" if re.search(r"\bin Senate\b|Senate actions|^Introduced in Senate", t) else origin)
        H = HOUSE[h]
        body = LOC_PREFIX.sub("", t).strip()
        kind = "other"
        if codes & {"1000", "Intro-H"} or codes & {"10000", "Intro-S"}:
            add(d, h, f"Introduced in the {H}", "intro")
            continue
        if re.match(r"(?:Received in the (?:Senate|House)|Received in the Senate and)", t) and not re.search(r"referred", t, re.I):
            add(d, h, f"Received in the {H}" + (" and read twice" if "read twice" in t.lower() else ""), "received")
            if passed.get(OTHER[h]) is not None:
                where_h = h
            if CAL.search(t):
                place = "floor"
            continue
        # Referrals: the committees the action names.
        if re.search(r"\breferred to\b|\breferred jointly\b|\bsequentially referred\b", t, re.I) and not re.search(r"Subcommittee", t) \
                and not re.match(r"Motion|Motion by|.*with instructions", t):
            names = [committee_name(c) for c in a["comm"] if not re.search(r"Subcommittee", c)] or \
                    [committee_name(m) for m in re.findall(r"Committee on ([A-Z][\w,'’ ]+?)(?:[,.;]| and in addition| for a period|$)", t)]
            for c in names:
                if c and c not in pending[h]:
                    pending[h].add(c)
                    refs.append((h, c))
                    if first_ref is None and h == origin:
                        first_ref = c
            if names:
                place, where_h = "committee", h
            add(d, h, t, "ref")
            continue
        if re.match(r"Referred to the Subcommittee", t):
            add(d, h, t, "subref")
            continue
        m = re.search(r"Ordered to be Reported.*?(?:Yeas and Nays|recorded vote)[:.]?\s*:?\s*(\d+)\s*-\s*(\d+)", t, re.I)
        if m and a["comm"]:
            comm_votes.append([h, "C", committee_name(a["comm"][0]), d, int(m.group(1)), int(m.group(2)), []])
        if codes & {"5000", "14000", "14900", "H12200", "H12300"} or re.match(r"(?:Reported (?:\(Amended\) |with amendments? |without amendment )?by|Committee on .*\. Reported by)", t):
            reported = True
            for c in a["comm"] or []:
                pending[h].discard(committee_name(c))
                topic_comms.add(committee_name(c))
            if not a["comm"]:
                pending[h].clear()
            if not pending[h]:
                place, where_h = "floor", h
            add(d, h, t, "report")
            continue
        if codes & {"5500", "14500"} or re.search(r"\bdischarged\b", t) and re.search(r"Committee", t) and not re.match(r"Motion", t):
            if re.search(r"Subcommittee", t) and not re.search(r"Committee on .* discharged", t):
                add(d, h, t, "subref")
                continue
            discharged = True
            for c in a["comm"] or []:
                pending[h].discard(committee_name(c))
            if not a["comm"]:
                pending[h].clear()
            if not pending[h]:
                place, where_h = "floor", h
            add(d, h, t, "discharge")
            continue
        if CAL.search(t):
            if not (passed.get(h) is not None):
                place, where_h = "floor", h
                pending[h].clear()
            add(d, h, t, "calendar")
            continue
        # Passage and failure, by the Library's codes.
        if codes & {"8000", "17000"}:
            ph = "H" if "8000" in codes else "S"
            passed[ph] = d
            failed.discard(ph)
            changed = bool(re.search(r"with (?:an )?amendments?|, as amended|in the nature of a substitute", body, re.I)) and \
                not re.search(r"without amendment", body, re.I)
            # The House's passage line doesn't always say it amended the bill; the messages after it do ("House amendment
            # to Senate bill", "motion to concur in the House amendment": S. 1383 of the 119th).
            if ph != origin and not changed:
                changed = any(x["date"] >= d and AMEND_MSG.search(x["text"]) for x in lines if x is not a)
            add(d, ph, f"PASSED {HOUSE[ph].upper()}: {body}", "pass")
            if ph != origin and passed.get(origin) is not None:
                if changed:
                    amended_by = ph
                    where_h, place = origin, "desk"
                else:
                    both = True
                    amended_by = None
            elif ph == origin:
                where_h, place = other, "committee"
            _vote(a, ph, votes, congress, "Passage")
            continue
        if codes & {"9000", "18000"}:
            fh = "H" if "9000" in codes else "S"
            failed.add(fh)
            add(d, fh, f"FAILED IN THE {HOUSE[fh].upper()}: {body}", "fail")
            _vote(a, fh, votes, congress, "Passage (failed)")
            continue
        # Resolving differences between the houses.
        if a["type"] == "ResolvingDifferences" or codes & {"19500", "20500", "21000", "23000"}:
            if re.search(r"conference report", body, re.I) and re.search(r"Agreed to|agreed to conference report|Senate agreed to conference", body) \
                    and not re.search(r"instruct|close portions|motion to recommit", body, re.I):
                conf.add(h)
                add(d, h, f"The {H} agreed to the conference report: {body}" if not body.startswith(("Conference report agreed", "Senate agreed")) else body, "ccr")
                _vote(a, h, votes, congress, "Conference report")
                if conf >= {"S", "H"}:
                    both = True
                    amended_by = None
                continue
            if re.search(r"disagree|request a conference|appointed conferees|\binsists?\b|instruct", body, re.I):
                add(d, h, body, "conf")
                continue
            if re.search(r"\b(?:agree|agreed|concur|concurred) (?:in |to )?(?:with an amendment )?(?:to )?the (?:Senate|House) [Aa]mendment", body) \
                    and re.search(r"Agreed to|Senate agreed|Senate concurred|agreed to in Senate|without objection|by voice vote|by Unanimous Consent|by Yea-Nay", body) \
                    and not re.search(r"\bFailed\b|\brejected\b|not agreed", body):
                with_more = bool(re.search(r"with an amendment|with amendments?|with a further amendment", body))
                add(d, h, body, "concur" if not with_more else "amendback")
                _vote(a, h, votes, congress, "Agreeing to the other house's changes")
                if with_more:
                    amended_by = h
                    where_h, place = OTHER[h], "desk"
                else:
                    both = True
                    amended_by = None
                continue
            if re.search(r"disagree|request a conference|appointed conferees|insist", body, re.I):
                add(d, h, body, "conf")
                continue
            if ROUTINE_LINE.search(body):
                continue
            add(d, h, body, "other")
            continue
        if "28000" in codes or "E20000" in codes or t.startswith("Presented to President"):
            presented = True
            both = True
            add(d, "G", "Presented to the President", "sent")
            continue
        if t.startswith("Signed by President"):
            signed = True
            add(d, "G", "SIGNED BY THE PRESIDENT", "signed")
            continue
        m = re.match(r"Became (Public|Private) Law No: (\d+-\d+)", t)
        if m:
            law, law_kind, law_no = True, m.group(1), m.group(2)
            if re.search(r"without (?:the )?(?:President's )?signature", t, re.I):
                no_sign = True
            add(d, "G", f"Became {m.group(1)} Law {m.group(2)}" + (" without the President's signature" if no_sign else ""), "law")
            continue
        if re.match(r"Pocket Vetoed by President", t):
            pocket = vetoed = True
            add(d, "G", "Pocket vetoed by the President (Congress had adjourned)", "vetoed")
            continue
        if t.startswith("Vetoed by President"):
            vetoed = True
            add(d, "G", "VETOED by the President", "vetoed")
            continue
        if a["type"] == "Veto" or codes & {"32000", "33000", "34000", "35000"}:
            if re.search(r"objections of the President to the contrary notwithstanding (?:Passed|Agreed)|Passed (?:House|Senate) over veto", body) \
                    and not re.search(r"Failed", body):
                overrides.add(h)
                add(d, h, f"The {H} voted to override the veto: {body}", "override")
                _vote(a, h, votes, congress, "Veto override")
            elif re.search(r"Failed of passage .* over veto|objections of the President to the contrary notwithstanding Failed|over veto.*Failed|Failed.*over veto", t):
                sustained = True
                add(d, h, f"The {H} failed to override the veto: {body}", "sustain")
                _vote(a, h, votes, congress, "Veto override (failed)")
            elif re.search(r"refer the bill and (?:the )?accompanying veto message|veto message .* referred", body, re.I) and re.search(r"Agreed|agreed", body):
                sustained = True
                add(d, h, f"The {H} sent the veto message to committee: {body}", "sustain")
                _vote(a, h, votes, congress, "Referring the veto")
            elif not ROUTINE_LINE.search(body):
                add(d, h, body, "other")
            continue
        mm = re.match(r"Senate incorporated this measure in ((?:H\.R\.|S\.|H\.J\.Res\.|S\.J\.Res\.) ?\d+)", t)
        if mm:
            into = re.sub(r"[ .]", "", mm.group(1)).upper()
            add(d, h, t, "into")
            continue
        # The Senate's cloture votes and motions to proceed; other floor lines as written.
        if a["votes"] and own_vote(a):
            label = "Cloture (ending debate)" if re.search(r"cloture", t, re.I) else "Motion to proceed" if re.search(r"motion to proceed", t, re.I) else "Floor vote"
            add(d, h, t, "cloture" if label.startswith("Cloture") else "other")
            _vote(a, h, votes, congress, label)
            continue
        if ROUTINE_LINE.search(t):
            continue
        add(d, h, t, kind)

    # Laws and vetoes. A veto stands unless both houses overrode it.
    overridden = vetoed and overrides >= {"S", "H"}
    if law and vetoed and not overridden:
        overridden = True  # the record names the law; the override lines may be missing
    both = bool(both or presented or law or vetoed) and not (amended_by and not presented and not law and not vetoed)
    if amendment:
        stage = 3 if (both or (passed.get("S") and passed.get("H"))) else 2 if passed else None
    elif law:
        stage = 5
    elif vetoed:
        stage = 6
    elif presented:
        stage = 4
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
        stage = 1 if (place == "floor" and where_h == origin) or origin in failed else 0

    narrow = P.narrow_kind(f"{official} {title}", text(b.findtext("policyArea/name")))
    policy = text(b.findtext("policyArea/name"))
    subj = subjects(b)
    # Words in the titles, and in the CRS's subject terms; an omnibus bill's dozens of terms count for a topic only when
    # three of them name it.
    words = f"{title} {official} {' '.join(subj) if len(subj) <= 8 else ''}"
    many = len(subj) > 8
    topics = list(dict.fromkeys((["const"] if amendment else []) + ([P.POLICY_TOPICS[policy]] if policy in P.POLICY_TOPICS else []) +
                                [k for k, rx in P.TOPIC_WORDS.items() if rx.search(words) or (many and sum(1 for x in subj if rx.search(x)) >= 3)]))
    if amendment and not title.lower().startswith(("proposing", "constitutional amendment")):
        title = f"Constitutional amendment: {title[:1].lower() + title[1:]}" if title else "Constitutional amendment"
    budget = bool(BUDGET.search(f"{official} {title}"))

    # Sponsor and cosponsors (withdrawn cosponsors left out).
    ms = members(congress)
    sp = b.find("sponsors/item")
    sponsor, district, sp_id = "—", 0, None
    if sp is not None:
        sp_id = sp.findtext("bioguideId")
        sponsor = (ms.get(sp_id) or {}).get("name") or re.sub(r"^(?:Rep\.|Sen\.|Del\.|Resident Commissioner) ", "", re.sub(r"\s*\[.*\]$", "", text(sp.findtext("fullName"))))
        if "," in sponsor:
            last, first = sponsor.split(",", 1)
            sponsor = f"{first.strip()} {last.strip()}"
        seat = seat_of(congress, sp_id, origin)
        district = int(re.sub(r"\D", "", seat.split(":")[1])) if seat else 0
        party = (sp.findtext("party") or "")[:1]
        if party in ("D", "R"):
            _PARTIES.setdefault(congress, {})[(origin, sponsor)] = party
    cos = []
    for c in b.findall("cosponsors/item"):
        if c.findtext("sponsorshipWithdrawnDate"):
            continue
        cid = c.findtext("bioguideId")
        n = (ms.get(cid) or {}).get("name")
        if not n:
            n = re.sub(r"^(?:Rep\.|Sen\.|Del\.|Resident Commissioner) ", "", re.sub(r"\s*\[.*\]$", "", text(c.findtext("fullName"))))
            if "," in n:
                last, first = n.split(",", 1)
                n = f"{first.strip()} {last.strip()}"
        party = (c.findtext("party") or "")[:1]
        if party in ("D", "R"):
            _PARTIES.setdefault(congress, {})[(origin, n)] = party
        cos.append(n)

    # Every committee that had the bill (referred, reported an original measure, discharged), from the committees list.
    for c in b.findall("committees/item"):
        ch = {"House": "H", "Senate": "S"}.get(c.findtext("chamber") or "")
        acts_ = {(x.findtext("name") or "").lower() for x in c.findall("activities/item")}
        if not acts_ & {"referred to", "reported by", "reported original measure", "discharged from", "markup by"}:
            continue  # (a committee named only in a motion to commit, or only in a hearing)
        if ch and (c.findtext("type") or "") != "Joint":
            refs.append((ch, committee_name(c.findtext("name"))))
            if first_ref is None and ch == origin:
                first_ref = committee_name(c.findtext("name"))
    where = HOUSE.get(where_h, HOUSE[origin])
    comm_now = sorted(pending[where_h])[0] if stage in (0, 2) and place == "committee" and pending.get(where_h) else None
    if stage == 0:
        desc = f"In the {where} {comm_now} Committee" if comm_now else f"In {where} committee"
    elif stage == 1:
        desc = f"Failed in the {HOUSE[origin]}" if origin in failed else f"On the {where} calendar"
    else:
        desc = {2: (f"Passed the {HOUSE[origin] if origin in passed_h else HOUSE[other]}"
                    + (f"; failed in the {HOUSE[other]}" if other in failed else "")
                    + (f"; changed by the {HOUSE[amended_by]}, back in the {HOUSE[OTHER[amended_by]]}" if amended_by and len(passed_h) == 2 else "")),
                3: "Passed both houses" + ("; goes to the states for ratification" if amendment else ""),
                4: "Presented to the President", 5: f"Became {law_kind or 'Public'} Law {law_no}".strip(),
                6: "Vetoed" + (" (pocket veto)" if pocket else "")}[stage]
    if into and stage < 3:
        desc = f"Passed as part of {into}"
        steps.append((steps[-1][0] if steps else "", "G", f"Its text went into {into}, which carried it forward", "into"))

    def dates(test, mode="last"):
        ds = sorted({s[0] for s in steps if test(s) and s[0]})
        return {"first": ds[0], "last": ds[-1], "all": ";".join(ds)}[mode] if ds else ""

    action_dates = [s[0] for s in steps if s[0]]
    what = crs_summary(b)
    url = text(b.findtext("legislationUrl"))
    rec = {
        "nums": [p], "base": [p], "prev": set(),
        "title": title or official or p, "summary": official if official and official != title else (title or official),
        "act": "", "lawCode": "", "law": None, "laws": [],
        "comms": sorted({f"{h} · {c}" for h, c in refs}), "topics": topics, "places": [], "narrow": narrow,
        "commFate": "passed" if reported or discharged or passed else "none", "mainTopic": topics[0] if topics else "",
        "local": "local" in topics, "senDeleg": False, "asmDeleg": False, "budget": budget,
        "passedS": "S" in passed_h, "passedA": "H" in passed_h, "program": None,
        # (Both houses passed it, but the second changed it: it's "passed" by that house, waiting on the first.)
        "stage": stage, "passedIn": (HOUSE[amended_by] if amended_by and len(passed_h) == 2 else HOUSE[origin] if origin in passed_h else HOUSE[other]) if stage == 2 else None,
        "chapter": law_no if stage == 5 and law_no and law_kind == "Public" else None,  # (private laws: their status says so)
        "veto": None, "memo": "", "vetoMemo": None,
        "simText": f"{title} {official} {' '.join(subj[:12])}",
        "comm": comm_now if stage == 0 else None,
        "first": min(action_dates, default=text(b.findtext("introducedDate")) or f"{session}-01-03"),
        "last": max(action_dates, default=text(b.findtext("introducedDate")) or f"{session}-01-03"),
        "cosp": len(cos),
        "keyDates": [
            dates(lambda s: s[3] in ("report", "discharge"), "first"),
            dates(lambda s: s[3] in ("pass", "concur", "ccr") and s[1] == "S", "all"),
            dates(lambda s: s[3] in ("pass", "concur", "ccr") and s[1] == "H", "all"),
            "",
            dates(lambda s: s[3] == "sent"),
            dates(lambda s: s[3] in ("law", "signed")) if stage == 5 else "",
            dates(lambda s: s[3] == "vetoed"),
        ],
        "votes": comm_votes + [v for i, v in enumerate(votes) if not any(w[0] == v[0] and w[3] == v[3] and w[4:6] == v[4:6] for w in votes[:i])],
        "firstComms": [(origin, first_ref, bool(reported or discharged or passed))] if first_ref else [],
        "vers": [{"p": p, "sponsor": sponsor, "district": district, "cosponsors": cos, "primes": 1, "cosp": len(cos),
                  "statusDesc": desc, "committee": comm_now, "link": url,
                  "actions": [[s[0], s[2]] for s in steps]}],
        "_sponsor": sp_id, "_official": official, "_into": into, "_ident": identical(congress, b),
    }
    if law_kind == "Private" and not narrow:
        rec["narrow"] = "person"
    if stage == 5 and law_kind == "Private":
        rec["vers"][0]["statusDesc"] = f"Became Private Law {law_no}"
    if overridden and stage == 5:
        steps.append((max(s[0] for s in steps if s[3] == "override") if any(s[3] == "override" for s in steps) else rec["last"], "G", "Became law over the President's veto", "lawnote"))
        rec["vers"][0]["actions"] = [[s[0], s[2]] for s in steps]
    return rec, what


def _vote(a, h, votes, congress, label):
    """The action's roll call: member by member when downloaded, else its tally from the wording; none for a voice vote.
    A Senate tie the Vice President broke (H.R. 1 of the 119th, 51-50) is shown as the senators' 50-50, with a note: the
    Vice President isn't a senator, and a tally above the Senate's 100 seats would be a misreading."""
    tally = None
    for chamber, rollno, url, _, _ in a["votes"]:
        if ("H" if chamber.startswith("House") else "S") != h:
            continue
        name = vote_file(chamber, url)
        r = roll(congress, name) if name else None
        if r:
            tally = r
            break
        m = TALLY.search(a["text"])
        if m:
            tally = (int(m.group(1)), int(m.group(2)), [])
            break
    if tally is None and not a["votes"]:
        m = TALLY.search(a["text"])
        if m:
            tally = (int(m.group(1)), int(m.group(2)), [])
    if tally is None:
        return
    yes, no, listed = tally[:3]
    tie = ["TIE", "VP"] in listed
    listed = [x for x in listed if x != ["TIE", "VP"]]
    if h == "S" and (tie or yes + no > 100):
        yes = min(yes, 100 - no)
        label += " (the Vice President broke a tie)"
    votes.append([h, "F", label, a["date"], yes, no, listed])


# ---- a Congress -----------------------------------------------------------------------------------------------------

ORDER = {"HR": 0, "HJRES": 1, "S": 2, "SJRES": 3}


def load_session(session):
    """One Congress's bills: (records, number -> index, fetched time, delegation)."""
    if session in _CACHE:
        return _CACHE[session]
    congress = P.congress_of(session)
    recs, texts = [], {}
    for p, b in raw_bills(congress):
        rec, what = record(congress, p, b)
        recs.append(rec)
        if what and what[0]:
            texts[p] = {"statement": what[0], "label": what[1]}
    recs.sort(key=lambda r: (ORDER[re.match(r"[A-Z]+", r["nums"][0]).group()], int(re.sub(r"\D", "", r["nums"][0]))))
    index = {r["nums"][0]: i for i, r in enumerate(recs)}
    link_into(recs, index)
    recs, texts = pair_identical(recs, texts)
    index = {n: i for i, r in enumerate(recs) for n in r["nums"]}
    link_earlier(session, recs)
    for r in recs:
        for k in ("_sponsor", "_official", "_into", "_ident"):
            r.pop(k, None)
    json.dump(texts, open(os.path.join(P.DATA, f"texts_{session}.json"), "w"), ensure_ascii=False)
    paths = glob.glob(os.path.join(folder(congress), "*.zip")) + glob.glob(os.path.join(folder(congress), "updates", "*.xml"))
    newest = max((os.path.getmtime(p) for p in paths), default=0)
    fetched = datetime.fromtimestamp(newest, ZoneInfo(P.TIMEZONE)).strftime("%Y-%m-%d %H:%M") if newest else ""
    settle(recs, folder(congress))  # bills with no history yet: never dated in the future (states/undated.py)
    out = (recs, index, fetched, {"SENATE": [], "ASSEMBLY": []})
    _CACHE[session] = out
    return out


def identical(congress, b):
    """The bills in the other house that the Congressional Research Service marks as identical to this one (relatedBills,
    relationshipDetails "Identical bill"), in the same Congress. (Identical bills in the same house, mostly a bill
    introduced again, aren't companions: left out.)"""
    mine = "S" if b.findtext("type") in ("S", "SJRES") else "H"
    out = []
    for it in b.findall("relatedBills/item"):
        if "Identical bill" not in {x.findtext("type") for x in it.findall("relationshipDetails/item")}:
            continue
        t = it.findtext("type") or ""
        if it.findtext("congress") != str(congress) or t not in PREFIX:
            continue
        if ("S" if t in ("S", "SJRES") else "H") != mine:
            out.append(PREFIX[t] + (it.findtext("number") or ""))
    return out


RANK = {5: 7, 6: 6}  # (a law beats a veto)


def pair_identical(recs, texts):
    """Companion bills, the same bill introduced in each house, as one record, as New York's identical Senate and
    Assembly bills are: those the Congressional Research Service marks "Identical bill" (in either bill's file: about one
    pair in fifteen is marked on one side only). The lead is the number that got further (stage, then the latest
    action); each number keeps its own sponsor, history and status as a version, and its floor votes say which number
    they were on. A group with more than one bill that reached the President stays apart (none in 2021-26), so no law
    or veto is lost."""
    by = {r["nums"][0]: r for r in recs}
    parent = {}

    def find(x):
        while parent.setdefault(x, x) != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for r in recs:
        for o in r["_ident"]:
            if o in by and o != r["nums"][0]:
                parent[find(r["nums"][0])] = find(o)
    groups = defaultdict(list)
    for n in parent:
        groups[find(n)].append(by[n])
    merged = {}
    for g in groups.values():
        if len(g) < 2 or sum(1 for r in g if r["stage"] >= 4) > 1:
            continue
        g.sort(key=lambda r: (RANK.get(r["stage"], r["stage"]), r["last"]), reverse=True)
        lead, rest = g[0], g[1:]
        for r in rest:
            p = r["nums"][0]
            for v in r["votes"]:
                if v[1] == "F":
                    v[2] = f"{v[2]} of {p}"
            lead["votes"] += r["votes"]
            lead["vers"] += r["vers"]
            lead["nums"].append(p)
            lead["comms"] = sorted(set(lead["comms"]) | set(r["comms"]))
            lead["topics"] += [t for t in r["topics"] if t not in lead["topics"]]
            lead["first"] = min(lead["first"], r["first"])
            lead["last"] = max(lead["last"], r["last"])
            lead["cosp"] = max(lead["cosp"], r["cosp"])
            if lead["nums"][0] not in texts and p in texts:
                texts[lead["nums"][0]] = texts[p]
            texts.pop(p, None)
            merged[p] = lead
        lead["base"] = lead["nums"]
    return [r for r in recs if r["nums"][0] not in merged], texts


def link_into(recs, index):
    """A bill whose text went into another ("Senate incorporated this measure in H.R. 2670"): the host gets a line naming
    it. (The Senate's "struck all after the Enacting Clause and substituted the language of S. 2226" says the same on
    the host's side.)"""
    for r in recs:
        host = r.get("_into")
        if host and host in index:
            h = recs[index[host]]
            when = r["last"]
            h["vers"][0]["actions"].append([when, f"Carries the text of {r['nums'][0]}, which the Senate put into it"])
            h["vers"][0]["actions"].sort(key=lambda a: a[0])


_KEYS = {}


def _key(title):
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", re.sub(r"\b(?:of|act)\s+\d{4}\b", "", (title or "").lower()))).strip()


def link_earlier(session, recs):
    """The same bill in the Congress before: the same title (four words or more, the year in "Act of 2023" aside) and
    the same sponsor, or the same title when only one bill in each Congress has it. Never laws, appropriations or
    naming bills (the same post office can be named twice; budget bills share titles every year)."""
    prev = session - 2
    if prev not in sessions():
        return
    old = load_session(prev)[0]
    by = defaultdict(list)
    for r in old:
        if r["stage"] == 5 or r["budget"] or r["narrow"]:
            continue
        by[_key(r["title"])].append(r)
    count = Counter(_key(r["title"]) for r in recs)
    for r in recs:
        if r["budget"] or r["narrow"]:
            continue
        k = _key(r["title"])
        if len(k.split()) < 4 or k not in by:
            continue
        hits = by[k]
        mine = {v["sponsor"] for v in r["vers"]}  # (companions: either number's sponsor)
        same = [o for o in hits if mine & {v["sponsor"] for v in o["vers"]}]
        if same:
            r["prev"].add((prev, same[0]["nums"][0]))
        elif len(hits) == 1 and count[k] == 1:
            r["prev"].add((prev, hits[0]["nums"][0]))


def parties(session, recs):
    if P.congress_of(session) not in _PARTIES:
        load_session(session)
    return dict(_PARTIES.get(P.congress_of(session), {}))


def show(congress, nums):
    """Print bills' records (python3 -m states.us.convert show 118 HR4521 S2226)."""
    for p, b in raw_bills(congress):
        if p in nums:
            rec, what = record(congress, p, b)
            print(p, rec["title"], "| stage", rec["stage"], "|", rec["vers"][0]["statusDesc"], "| comms", rec["comms"], "| topics", rec["topics"], rec["narrow"])
            for a in rec["vers"][0]["actions"]:
                print("   ", a[0], a[1][:180])
            for v in rec["votes"]:
                print("    vote", v[:6], len(v[6]), "listed")
            print("    keyDates", rec["keyDates"])


if __name__ == "__main__":
    import sys
    if sys.argv[1:2] == ["show"]:
        show(int(sys.argv[2]), set(sys.argv[3:]))
        sys.exit()
    # Laws, vetoes and stages per Congress, to compare with the official counts.
    for s in sessions():
        recs, index, _, _ = load_session(s)
        c = P.congress_of(s)
        st = Counter(r["stage"] for r in recs)
        laws = [r for r in recs if r["stage"] == 5]
        print(f"{c}th Congress ({s}-{s + 1}): {len(recs)} bills and joint resolutions; stages {sorted(st.items())}")
        print("  public laws:", sum(1 for r in laws if r["narrow"] != "person" or not str(r['vers'][0]['statusDesc']).startswith('Became Private')),
              " private laws:", sum(1 for r in laws if r['vers'][0]['statusDesc'].startswith('Became Private')))
        print("  vetoed (veto stands):", [r["nums"][0] for r in recs if r["stage"] == 6])
        print("  overridden:", [r["nums"][0] for r in recs if r["stage"] == 5 and r["keyDates"][6]])
        print("  presented, no action:", [r["nums"][0] for r in recs if r["stage"] == 4])
        print("  passed both, not presented:", [r["nums"][0] for r in recs if r["stage"] == 3 and "const" not in r["topics"]][:40])
