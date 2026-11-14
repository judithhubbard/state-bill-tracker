"""West Virginia's bills (downloaded by states/wv/fetch.py from the Legislature's bill status pages) in the shape
build_data.py reads. A page a year: the Legislature meets once a year for 60 days (from the second Wednesday of January,
or of February in a year a governor is inaugurated) and bills die when the session ends. House and Senate bills (HB, SB)
and the joint resolutions (HJR, SJR), which in West Virginia propose constitutional amendments: two-thirds of each house's
members, then the voters, never the governor. Special sessions are left out.

Each bill's history page (data/wv/<year>/bills/SB8.html) has the short title ("SUMMARY:"), the lead sponsor and the
sponsors in order (surnames: "Thorne", "Smith, D."), the text versions, the roll calls with their links, the subjects,
and the actions, newest first, each with its house letter, date and journal page. The steps, read in date order:
- "Filed for introduction", "Introduced in Senate" (in the second house, "Introduced in House" means it arrived there),
  "Originating in House Finance" (a committee's own bill, reported as it's introduced).
- Referrals: "To Health and Human Resources then Judiciary" (the plan: the first committee, then a second) and "To House
  Health and Human Resources" (the referral itself: the same committee twice); "Referred to Finance", "Rereferred to X",
  "Recommitted to X on 2nd reading", "Committed to X on 1st reading".
- Committee reports: in the House "Do pass", "By substitute, do pass", "With amendment, do pass", "Without
  recommendation", "Be adopted" (resolutions); in the Senate "Reported do pass", "Committee substitute reported",
  "Reported be adopted". "..., but first to Judiciary" sends it on to a second committee; "2nd reference dispensed" skips
  that. "Reported in Com. Sub. for S. B. 50": the committee folded the bill into another one's substitute (the bill ends).
  "Markup Discussion" is a committee meeting, not a vote.
- Floor: "On 1st reading, Special Calendar" (the House's Rules Committee moves bills from the House Calendar to the
  Special Calendar, where they're voted on), "Read 1st/2nd/3rd time", "Passed House (Roll No. 93)", "Adopted by Senate"
  (resolutions), "House rejected (Roll No. 51)" (defeated). "Effective from passage (Roll No. 94)" is a separate vote (by
  two-thirds) on when the act takes effect, not the passage.
- The other house's changes: "Senate requests House to concur" (it amended the bill, or changed its effective date),
  "House concurred in Senate amendment and passed bill (Roll No. 731)", "... with amendment, passed bill" (the House
  changed it again: the Senate has to agree), "House refused to concur; requested Senate to recede", "Senate receded and
  passed", conference committees ("House adopted conference report and passed bill"). "Completed legislative action" is
  passed both houses (the Legislature's list of completed bills agrees).
- The governor: "To Governor 3/20/2025", "Approved by Governor 3/26/2025", "Approved by Governor with deletions [and
  reductions]" (line-item vetoes in an appropriation bill), "Vetoed by Governor", "Became law without Governor's
  signature" / "Became law 3/28/24", "Chapter 46, Acts, Regular Session, 2025". Each house's copy of these lines ("...
  - House Journal") is dated by its journal, often days off: the date written in the line is used, and the copies are
  dropped. A veto during the session can be met by amending the bill ("Senate amended, repassed bill as result of
  Governor's Veto", "House repassed to meet the obj. of the Governor": SB 369 of 2025, then approved) or overridden ("passed
  notwithstanding the objections", none in 2024-26); most vetoes come after the session ends and stand.
Laws and vetoes agree with the governor's lists (signed, vetoed, became law without signature) and the completed list
bill for bill: `checks()` compares them (python3 -m states.wv.convert).

Votes: floor roll calls member by member from the roll-call PDFs' text (votes/house/00093.txt: names under YEAS, NAYS,
NOT VOTING, EXCUSED; votes/senate/02-24-0019.txt: a Y/N/A/E letter before each surname in capitals, "MR PRESIDENT"),
matched to the history line by house and roll number. Only the bill's own passages and repassages (and resolutions'
adoptions) count. Names are tied to today's members' seats within the house for the current Legislature (2025-26); for
an earlier year only names that also vote in 2025 (continuing members) are tied, the rest kept as names.
"What it does" is the drafter's note in the bill's text ("The purpose of this bill is ..."), from the newest version that
has one (Senate committee substitutes and the engrossed and enrolled texts drop it).
"""
import glob, html as H_, json, os, re
from collections import Counter, defaultdict
from datetime import date, datetime
from zoneinfo import ZoneInfo

from states.wv import profile as P

HOUSE = {"S": "Senate", "H": "House"}
OTHER = {"S": "H", "H": "S"}
SEATS = {"S": 34, "H": 100}
FIRST_OF_LEGISLATURE = 2025  # the 87th Legislature (2025-26), elected in November 2024: today's members
# A bare surname that two of today's members share, from before the second one arrived (Sen. Zack Maynard and Del. Guy
# Ward were appointed in 2025-26): the member who was there first.
BARE = {("S", "maynard"): "m", ("H", "ward"): "b"}
_PARTIES, _CACHE = {}, {}
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
    """"02/19/26" -> "2026-02-19"; "3/26/2025" -> "2025-03-26"."""
    m, dd, y = d.split("/")
    y = int(y)
    return f"{2000 + y if y < 100 else y}-{int(m):02d}-{int(dd):02d}"


# ---- Reading a bill's page ----

ROW = re.compile(r'<tr id="act-\d+"[^>]*>\s*<td[^>]*>\s*([HSG]?)\s*</td>\s*<td[^>]*?data-com="([^"]*)"[^>]*>(.*?)</td>\s*'
                 r'<td[^>]*>\s*([\d/]*)\s*</td>\s*<td[^>]*>(.*?)</td>', re.S)


def field(page, name):
    m = re.search(rf"<strong>{name}:?</strong>.*?</td>\s*<td[^>]*>(.*?)</td>", page, re.S)
    return m.group(1) if m else ""


def parse(session, key):
    """A bill page -> {key, title, sponsors [surname as linked], docs [text file names, newest first], rolls [(house,
    pdf path, label)], subjects, actions [(date, house, line)] in date order} or None when it's missing."""
    path = os.path.join(folder(session), "bills", f"{key}.html")
    try:
        s = open(path, encoding="utf-8").read()
    except OSError:
        return None
    k = (session, "page", key)
    if k in _CACHE:
        return _CACHE[k]
    head = s.split("ACTIONS:")[0]
    sponsors = []
    for part in (field(head, "LEAD SPONSOR"), field(head, "SPONSORS")):
        for name in re.findall(r"(?:hsemem|senmem)=[^\"]*\"[^>]*>([^<]+)<", part):
            name = text(name)
            if name and name not in sponsors:
                sponsors.append(name)
    docs = []
    for d in re.findall(r"billdoc=([^&\"]+)", head):
        d = H_.unescape(d).replace("%20", " ")
        if d not in docs:
            docs.append(d)
    rolls = [(h[0].upper(), pdf, text(lbl)) for h, pdf, lbl in
             re.findall(r"(House|Senate)\s*-\s*<a href=\"(/legisdocs/[^\"]+\.pdf)\">(.*?)</a>", field(head, "ROLL CALL VOTES"))]
    subjects = [H_.unescape(x).replace("%20", " ") for x in re.findall(r"billsub=([^\"&]+)", head)]
    code = re.findall(r"code\.wvlegislature\.gov/([\d\w-]+)/", head)
    rows = []
    for i, (h, com, t, d, j) in enumerate(ROW.findall(s)):
        t = text(t)
        if t and d:
            rows.append((iso(d), h or "", t, -i))
    # Newest first in the page: date order, and the page's own order (reversed) within a day.
    rows.sort(key=lambda r: (r[0], r[3]))
    b = {"key": key, "title": text(field(head, "SUMMARY")), "sponsors": sponsors, "docs": docs, "rolls": rolls,
         "subjects": subjects, "code": code, "actions": [(d, h, t) for d, h, t, _ in rows],
         "last": text(field(head, "LAST ACTION"))}
    _CACHE[k] = b
    return b


# ---- Members and names ----

def members():
    """Today's members (data/wv/members/members.json), each with its seat: "H:62"; "S:5a"/"S:5b" (each Senate district
    elects two senators: the two are lettered by surname)."""
    if "members" not in _CACHE:
        try:
            raw = json.load(open(os.path.join(P.DATA, "members", "members.json"), encoding="utf-8")).get("members") or []
        except (OSError, ValueError):
            raw = []
        raw = [m for m in raw if m.get("house") in ("S", "H") and m.get("district") and m.get("name")]
        by_d = defaultdict(list)
        for m in raw:
            m = dict(m)
            m["d"] = int(m["district"])
            m["last"], m["init"] = name_key(re.sub(r"^(?:Delegate|Senator|Speaker|President)\s+", "", m["member"]))
            by_d[(m["house"], m["d"])].append(m)
        out = []
        for (h, d), ms in sorted(by_d.items()):
            ms.sort(key=lambda m: (m["last"], m["init"]))
            for i, m in enumerate(ms):
                m["seat"] = f"S:{d}{'ab'[i] if i < 2 else 'c'}" if h == "S" else f"H:{d}"
                out.append(m)
        _CACHE["members"] = out
    return _CACHE["members"]


def name_key(n):
    """"Smith, D." / "Smith, D" / "SMITH" / "Hanshaw (Mr. Speaker)" / "Speaker Hanshaw" -> ("smith", "d") ...; the initial
    is "" when the name has none."""
    n = re.sub(r"\((?:Mr\.|Madam) (?:Speaker|President)\)|^(?:Speaker|President|Delegate|Senator)\s+", "", n or "").strip()
    last, _, init = n.partition(",")
    return re.sub(r"[^a-z'-]", "", last.lower().replace("’", "'")), re.sub(r"[^a-z]", "", init.lower())[:1]


def member_of(h, name):
    """A name as the pages write it, in a house -> today's member, or None."""
    last, init = name_key(name)
    hits = [m for m in members() if m["house"] == h and m["last"] == last]
    if init:
        # "Clark, T" (2024) isn't today's only Clark, W.: an initial must match the member's, when the member has one.
        hits = [m for m in hits if m["init"] in (init, "")]
    elif len(hits) > 1 and (h, last) in BARE:
        hits = [m for m in hits if m["init"] == BARE[(h, last)]]
    return hits[0] if len(hits) == 1 else None


def roll_names(session):
    """Every name in a year's roll calls, by house: {"H": {("smith", "d"), ...}, "S": {...}} ("MR PRESIDENT" as that
    year's President)."""
    k = (session, "names")
    if k not in _CACHE:
        out = {"H": set(), "S": set()}
        for h, sub in (("H", "house"), ("S", "senate")):
            for f in glob.glob(os.path.join(folder(session), "votes", sub, "*.txt")):
                r = read_roll(f, h, session)
                if r:
                    out[h] |= {name_key(n) for n, _ in r["names"]}
        _CACHE[k] = out
    return _CACHE[k]


def seat_of(session, h, name):
    """A roll-call or sponsor name -> today's member's seat, for the current Legislature; for an earlier year only when
    the same name also votes in 2025 (a continuing member), else "H?Name"."""
    m = member_of(h, name)
    if m and session < FIRST_OF_LEGISLATURE and FIRST_OF_LEGISLATURE in sessions():
        if name_key(name) not in roll_names(FIRST_OF_LEGISLATURE)[h] and (name_key(name)[0], "") not in roll_names(FIRST_OF_LEGISLATURE)[h]:
            m = None
    if m:
        return m["seat"]
    n = re.sub(r"\s*\((?:Mr\.|Madam) (?:Speaker|President)\)", "", name).strip()
    return f"{h}?{n.title() if n.isupper() else n}"


def sponsor_name(session, h, name):
    """A sponsor's surname as linked -> (full name, seat district) for a member tied as in seat_of(), else (name, None)."""
    sid = seat_of(session, h, name)
    if "?" in sid:
        return re.sub(r"\s*\((?:Mr\.|Madam) (?:Speaker|President)\)", "", name).strip(), None
    m = next(x for x in members() if x["seat"] == sid)
    return m["name"], m["d"]


# ---- Roll calls ----

def read_roll(path, h, session):
    """A roll call's text -> {"y", "n", "a", "e", "names": [(name, "Y"/"N"/"A"/"E")]} or None."""
    k = ("roll", path)
    if k in _CACHE:
        return _CACHE[k]
    try:
        s = open(path, encoding="utf-8", errors="replace").read()
    except OSError:
        _CACHE[k] = None
        return None
    out = None
    if h == "H":
        m = re.search(r"Yeas:\s*(\d+)\s+Nays:\s*(\d+)\s+Absent:\s*(\d+)\s+Exc:\s*(\d+)", s)
        if m:
            names, code = [], None
            for line in s.splitlines():
                g = re.match(r"\s*(YEAS|NAYS|NOT VOTING|EXCUSED|ABSENT):\s*\d+\s*$", line)
                if g:
                    code = {"YEAS": "Y", "NAYS": "N", "NOT VOTING": "A", "ABSENT": "A", "EXCUSED": "E"}[g.group(1)]
                    continue
                if code and line.strip():
                    if re.search(r"[a-z]", line) or re.match(r"\s*Speaker ", line):
                        names += [(n.strip(), code) for n in re.split(r"\s{2,}", line.strip()) if n.strip()]
                    else:
                        code = None
            out = {"y": int(m.group(1)), "n": int(m.group(2)), "a": int(m.group(3)), "e": int(m.group(4)), "names": names}
    else:
        m = re.search(r"Yea:\s*(\d+)\s+Nay:\s*(\d+)\s+Absent:\s*(\d+)\s+Excused:\s*(\d+)", s)
        if m:
            names = []
            for line in s.splitlines():
                toks = re.split(r"\s{2,}", line.strip())
                if len(toks) >= 2 and len(toks) % 2 == 0 and all(t in ("Y", "N", "A", "E") for t in toks[0::2]):
                    for c, n in zip(toks[0::2], toks[1::2]):
                        if n == "MR PRESIDENT":
                            n = P.PRESIDENTS.get(session, "President").upper()
                        names.append((n, c))
            out = {"y": int(m.group(1)), "n": int(m.group(2)), "a": int(m.group(3)), "e": int(m.group(4)), "names": names}
    _CACHE[k] = out
    return out


def roll_path(session, h, d, number):
    if h == "H":
        return os.path.join(folder(session), "votes", "house", f"{int(number):05d}.txt")
    p = os.path.join(folder(session), "votes", "senate", f"{d[5:7]}-{d[8:10]}-{int(number):04d}.txt")
    if os.path.exists(p):
        return p
    hits = glob.glob(os.path.join(folder(session), "votes", "senate", f"*-{int(number):04d}.txt"))
    return hits[0] if len(hits) == 1 else p


def floor_vote(session, h, d, line):
    """A history line with "(Roll No. 93)" -> [house, "F", None, day, ayes, noes, [[seat, code], ...]] (yes votes left
    out), or None when there's no roll call or its text."""
    m = re.search(r"Roll No\.?\s*(\d+)", line)
    if not m:
        return None
    r = read_roll(roll_path(session, h, d, m.group(1)), h, session)
    if not r:
        return None
    # Every name in the roll call, so that a seat claimed by two names (two members matched to one) is left as names.
    seats = Counter(seat_of(session, h, n) for n, _ in r["names"])
    listed = [[sid if seats[sid] == 1 or "?" in sid else f"{h}?{n.title() if n.isupper() else n}", c]
              for n, c in r["names"] if c != "Y" for sid in [seat_of(session, h, n)]]
    return [h, "F", None, d, r["y"], r["n"], listed]


# ---- Wording ----

FIXES = {"Government Adminstration": "Government Administration", "Enviroment, Infrastructure, and Technology":
         "Environment, Infrastructure, and Technology", "Agriculture, Commerce and Tourism": "Agriculture, Commerce, and Tourism",
         "Select Committee on Jails and Prisons": "Jails and Prisons", "Health Care Regulation": "Health Care Regulations",
         "Energy, Industry and Mining": "Energy, Industry, and Mining", "Local Government": "Local Governments"}
KNOWN = set()  # committee names seen, for repairing lines with a name run into them
# The House's subcommittees since 2025 (its committees.json: "Courts Subcommittee" ...). Some had been full committees
# (Banking and Insurance, Economic Development, Energy and Manufacturing) until 2024.
SUBCOMMITTEES = {"Agriculture, Commerce, and Tourism", "Appropriations", "Banking and Insurance", "Courts", "Economic Development",
                 "Educational Choice", "Energy and Manufacturing", "Environment, Infrastructure, and Technology",
                 "Government Administration", "Health Care Regulations", "Higher Education", "Homeland Security",
                 "Human Services", "Investments", "Legal Services", "Local Governments", "Public Education", "Public Health",
                 "Revenue"}


def comm_name(c):
    """"House Judiciary" -> "Judiciary"; "the Committee on Senior, Children and Family Issues" -> "Senior, Children, and
    Family Issues"; typos fixed."""
    c = re.sub(r"\s+", " ", (c or "").strip()).strip(" .")
    c = re.sub(r"^(?:the )?(?:House |Senate )?(?:Select )?(?:Committee on (?:the )?)?", "", c)
    c = re.sub(r"^(?:House|Senate) (?=\S)", "", c)
    c = re.sub(r" (?:Committee|Subcommittee)$", "", c)
    c = FIXES.get(c, c)
    if c == "Senior, Children and Family Issues":
        c = "Senior, Children, and Family Issues"
    return c


def title_of(short, const):
    t = re.sub(r"\s+", " ", short or "").strip().rstrip(".")
    t = t[:1].upper() + t[1:]
    if const and not re.search(r"amendment", t, re.I):
        t = f"Constitutional amendment: {t[:1].lower() + t[1:] if not t[:2].isupper() else t}"
    return t


def relating(official):
    """The official title's "relating to ..." clause: "A BILL to amend ... relating to permitting ..." -> "Relating to
    permitting ..."; else the title without its code citations."""
    t = re.sub(r"\s+", " ", official or "").strip()
    m = re.search(r"\brelating (?:to|generally to) (.+)$", t, re.I)
    if m:
        body = m.group(1).rstrip(" .")
        return f"Relating to {body}."
    return t


def gov_date(t, d):
    """The date written in a governor's line ("Approved by Governor 3/26/2025 - Senate Journal"), else the row's."""
    m = re.search(r"(\d{1,2}/\d{1,2}/\d{2,4})", t)
    try:
        return iso(m.group(1)) if m else d
    except ValueError:
        return d


# ---- One bill ----

PASS = re.compile(r"^(?:Passed (House|Senate)\b|Adopted by (House|Senate)\b)", re.I)
REPASS = re.compile(r"^(House|Senate) (?:concurred? in .*?\b(?:passed|adopted)\b|receded(?: in part)? and passed|"
                    r"reconsidered(?: action)? and passed|adopted conference report and passed|amended,? repassed|repassed|"
                    r"amend(?:s|ed) (?:House|Senate) amendment and passed)|^Suspended rule concurred .*passed", re.I)
REPORT_H = re.compile(r"^(?:(?:By substitute(?: for substitute)?|With (?:title )?amendments?(?: and title amendment)?),\s*)?"
                      r"(?:do pass|be adopted|without recommendation)(?:, Dispense 2nd Ref\.)?(?:,? but first (?:re)?(?:referred )?to (.+))?$", re.I)
REPORT_S = re.compile(r"^(?:Reported (?:do pass|be adopted|without recommendation)|(?:Committee substitute|Com\. sub\.)(?: for (?:committee substitute|com\. sub\.))? reported"
                      r"|Without recommendation)\b(.*)$", re.I)


def record(session, b, parties):
    p = b["key"]
    origin = "H" if p.startswith("H") else "S"
    other = OTHER[origin]
    const = "JR" in p
    steps = []  # (date, house or "G", wording, kind)
    passed, amended_by, concurred = set(), set(), set()
    where, place, comm = origin, "desk", None
    reported = set()
    refs, first_ref, first_report = [], None, False
    completed = sent = law = vetoed = items = folded = withdrawn = False
    nosign = False
    fvotes = []
    chapter = None
    intro = False
    gov_seen = set()
    vetoed_on = None
    defeated = None

    def refer(d, h, c, verb):
        nonlocal comm, place, first_ref, where, intro
        c = comm_name(c)
        if not c or c.lower() in ("conference",):
            return
        if not intro and h == origin:
            # The page lists the referral just before "Introduced in Senate" on the same day.
            intro = True
            steps.append((d, h, f"Introduced in the {HOUSE[h]}", "intro"))
        where = h
        if c == "Rules" and h == "S" and (h in reported or place == "floor" or h in passed):
            place, comm = "floor", None
            steps.append((d, h, "Sent to the Rules Committee, which decides when it comes up", "rules"))
            return
        if comm == c and place == "committee":
            return  # the same referral written twice ("To Judiciary then Finance", then "To House Judiciary")
        if h == "H" and session >= 2025 and c in SUBCOMMITTEES and place == "committee" and comm and comm not in SUBCOMMITTEES:
            # Since 2025 the House's committees send bills to their subcommittees ("To House Courts"), which send them
            # back ("To House Judiciary") before the committee reports: work within the committee, not a new referral.
            steps.append((d, h, f"Sent to the {comm} Committee's {c} Subcommittee", "subcommittee"))
            return
        if h == "H" and session >= 2025 and comm in SUBCOMMITTEES and place == "committee" and c not in SUBCOMMITTEES \
                and refs and refs[-1] == (h, c):
            return  # back from the subcommittee
        comm, place = c, "committee"
        refs.append((h, c))
        if first_ref is None and h == origin:
            first_ref = c
        steps.append((d, h, f"REFERRED TO {c.upper()}" if verb == "to" else
                      f"Sent back to committee: the {c} Committee" if verb == "back" else
                      f"Sent to another committee: the {c} Committee", "ref" if verb == "to" else "rereferred"))

    gov_lines = defaultdict(list)
    for d, h, t in b["actions"]:
        if re.match(r"(?:To Governor|Approved by Governor|Vetoed by Governor|Became law)", t, re.I):
            gov_lines[re.sub(r"\s*-\s*(?:House|Senate) Journal\s*$", "", t).strip().lower()[:12]].append(t)

    for d, h, t in b["actions"]:
        h = h or where
        tl = t.lower()
        # The governor's lines: one per event, dated by the date written in it.
        if re.match(r"(?:To Governor|Approved by Governor|Vetoed by Governor|Became law)", t, re.I):
            if re.search(r"Journal\s*$", t) and any(not re.search(r"Journal\s*$", x) for x in gov_lines[re.sub(r"\s*-\s*(?:House|Senate) Journal\s*$", "", t).strip().lower()[:12]]):
                continue
            kind = "sent" if tl.startswith("to governor") else "veto" if tl.startswith("vetoed") else \
                "nosign" if "without" in tl or re.match(r"became law \d", tl) else "signed"
            gd = gov_date(t, d)
            if kind == "nosign" and "nosign" in gov_seen:
                continue
            if (kind, gd) in gov_seen and kind != "nosign":
                continue
            gov_seen.add((kind, gd))
            gov_seen.add(kind) if kind == "nosign" else None
            if const:
                steps.append((gd, "G", t, "other"))
                continue
            if kind == "sent":
                sent = True
                steps.append((gd, "G", "DELIVERED TO GOVERNOR", "sent"))
            elif kind == "signed":
                law, vetoed = True, False
                steps.append((gd, "G", "Signed by the governor", "signed"))
                if re.search(r"with deletions", t, re.I):
                    items = True
                    steps.append((gd, "G", "The governor vetoed items in it" + (" and reduced others" if "reduction" in tl else "")
                                  + " (a line-item veto)", "itemveto"))
            elif kind == "veto":
                vetoed, vetoed_on = True, gd
                steps.append((gd, "G", "VETOED", "vetoed"))
            else:
                law, nosign = True, True
                steps.append((gd, "G", "Became law without the governor's signature", "nosign"))
            continue
        mch = re.match(r"Chapter (\d+), Acts", t, re.I)
        if mch:
            # Only a law keeps it (below): HB 4756 of 2026, never out of committee, carries HB 4755's "Chapter 104". (The
            # completed list's chapter column has its own slips: SB 75 of 2025 is chapter 220, not 226.)
            chapter = int(mch.group(1))
            steps.append((d, "G", f"Acts chapter {chapter} ({session})", "chapter"))
            continue
        if re.match(r"Fil\w* for introduction", t, re.I):
            continue
        mi = re.match(r"Introduc\w* in (House|Senate)", t, re.I)
        if mi:
            hh = mi.group(1)[0].upper()
            where = hh
            if hh == origin and not intro:
                intro = True
                steps.append((d, hh, f"Introduced in the {HOUSE[hh]}", "intro"))
            elif hh != origin:
                if place != "committee" or comm is None or where != hh:
                    place = "desk"
                steps.append((d, hh, f"Received in the {HOUSE[hh]}", "received"))
            continue
        mo = re.match(r"Originat\w* in (?:House|Senate) (.+)$", t, re.I)
        if mo:
            c = comm_name(mo.group(1))
            intro = True
            refs.append((h, c))
            first_ref = first_ref or c
            reported.add(h)
            first_report = True
            place, comm = "floor", None
            steps.append((d, h, f"Introduced by the {c} Committee", "intro"))
            steps.append((d, h, "REPORTED", "reported"))
            continue
        if re.match(r"(?:House received Senate message|House Message received|Senate received House message|Communicated to|Ordered to)", t, re.I):
            continue
        if re.match(r"Completed legislative action", t, re.I):
            completed = True
            steps.append((d, h, "Passed both houses (legislative action completed)", "completed"))
            continue
        # Committee reports.
        mr = REPORT_H.match(t) if h == "H" else None
        ms = REPORT_S.match(t) if not mr else None
        mfold = re.match(r"Reported in Com\. Sub\. for ([HS])\. ?(B|J\. ?R)\. ?(\d+)", t, re.I)
        if mfold:
            folded = True
            into = f"{mfold.group(1)}{'B' if mfold.group(2).upper() == 'B' else 'JR'} {mfold.group(3)}"
            steps.append((d, h, f"The {comm + ' ' if comm else ''}Committee folded it into its substitute for {into}", "folded"))
            continue
        if mr or ms or re.match(r"Do Pass, Dispense", t, re.I):
            rest = (mr.group(1) if mr else ms.group(1) if ms else "") or ""
            nxt = None
            mn = re.search(r"but first (?:re)?(?:referred )?to (.+?)(?: then .*)?$", t, re.I)
            if mn:
                nxt = mn.group(1)
            how = "without a recommendation" if re.search(r"without recommendation", t, re.I) else \
                "with a committee substitute" if re.search(r"substitute|Com\. sub", t, re.I) else \
                "with amendments" if re.search(r"amend", t, re.I) else ""
            cname = comm
            reported.add(h)
            if h == origin:
                first_report = True
            steps.append((d, h, "REPORTED", "reported"))
            steps.append((d, h, f"The {cname + ' ' if cname else ''}Committee recommended it" + (f" {how}" if how else "")
                          + (f", and sent it on to {comm_name(nxt)}" if nxt else ""), "report"))
            if nxt:
                place = "between"
                refer(d, h, nxt, "on")
            else:
                place, comm = "floor", None
            continue
        if re.match(r"(?:2nd |Committee )?reference dispensed|Motion to dispense the second reference(?: to .*)? adopted|"
                    r"2nd reference dispensed", t, re.I):
            if not re.search(r"rejected", t, re.I):
                place, comm = "floor", None
                steps.append((d, h, "The second committee was skipped" if re.match(r"2nd|Motion", t, re.I) else "Sent to the floor without a committee", "other"))
            continue
        if re.match(r"(?:Committee discharged|Unanimous consent to discharge|Motion to discharge (?:from )?committee adopted)", t, re.I):
            place, comm = "floor", None
            steps.append((d, h, "Taken from the committee (discharged) and put before the full house", "discharged"))
            continue
        mref = re.match(r"(?:On (?:\d\w+|second) reading,? )?(To|Referred to|Rereferred to|Recommitted to|Committed to|referred to|rereferred to)\s+(.+?)"
                        r"(?: on \d\w+ reading)?$", t, re.I)
        if mref and not re.match(r"To (?:Governor|conference)", t, re.I) and not re.search(r"\b(?:adopted|rejected|tabled)\b", t, re.I):
            verb = mref.group(1).lower()
            target = re.split(r" then ", mref.group(2))[0]
            target = re.sub(r"^(?:House|Senate) ", "", target)
            for k_ in sorted(KNOWN, key=len, reverse=True):
                if target.startswith(k_) and target != k_ and target[len(k_):] in KNOWN:
                    target = k_  # "Government OrganizationGovernment Organization", "EducationGovernment Organization"
                    break
            if target.strip() in ("*", ""):
                continue
            KNOWN.add(comm_name(target))
            refer(d, h, target, "back" if verb.startswith(("recommitted", "committed")) else "on" if verb.startswith("rereferred")
                  or (verb.startswith("referred") and h in reported) else "to")
            continue
        mp = PASS.match(t)
        if mp:
            hh = (mp.group(1) or mp.group(2))[0].upper()
            where = hh
            v = floor_vote(session, hh, d, t)
            if v:
                fvotes.append(v)
            tally = f", {v[4]}-{v[5]}" if v else ""
            if hh in passed:
                steps.append((d, hh, f"The {HOUSE[hh]} passed it again{tally}", "final"))
                continue
            passed.add(hh)
            if hh == origin:
                comm, place = None, "desk"
            elif re.search(r"amended title", t, re.I):
                amended_by.add(hh)
            steps.append((d, hh, f"PASSED {HOUSE[hh].upper()}", "pass"))
            steps.append((d, hh, f"The {HOUSE[hh]} vote: {v[4]}-{v[5]}" if v else f"The {HOUSE[hh]} vote: by voice", "tally"))
            continue
        mrp = REPASS.match(t)
        if mrp:
            hh = (mrp.group(1) or h)[0].upper()
            where = hh
            v = floor_vote(session, hh, d, t)
            if v:
                fvotes.append(v)
            tally = f", {v[4]}-{v[5]}" if v else ""
            again = re.search(r"with (?:further |amend\w*)|amend(?:s|ed) (?:House|Senate) amendment|amended,? repassed", t, re.I)
            passed.add(hh)
            if again:
                amended_by.add(hh)
                concurred.discard(OTHER[hh])
            else:
                concurred.add(hh)
                amended_by.discard(OTHER[hh])
            what = "agreed to the other house's changes and passed it again" if re.search(r"concur", t, re.I) and not again else \
                "changed the other house's amendments and passed it again" if again and not re.search(r"Governor", t, re.I) else \
                "amended it to meet the governor's objections and passed it again" if re.search(r"Governor", t, re.I) else \
                "dropped its changes and passed it again" if re.search(r"receded", t, re.I) else \
                "adopted the conference committee's report and passed it again" if re.search(r"conference", t, re.I) else \
                "passed it again"
            steps.append((d, hh, f"The {HOUSE[hh]} {what}{tally}", "final"))
            continue
        mrej = re.match(r"(?:(House|Senate) rejected|Rejected by (House|Senate)|(House|Senate) concurred in .* and rejected bill)\b(?! conference)", t, re.I)
        if mrej and re.search(r"Roll No|vote", t, re.I) and not re.search(r"conference|amendment \(", t, re.I):
            hh = (mrej.group(1) or mrej.group(2) or mrej.group(3))[0].upper()
            v = floor_vote(session, hh, d, t)
            if v:
                fvotes.append(v)
            defeated = hh
            steps.append((d, hh, f"The {HOUSE[hh]} voted it down" + (f", {v[4]}-{v[5]}" if v else ""), "defeated"))
            continue
        if re.match(r"(?:House|Senate) reconsidered (?:its action|passage|effective date and passage)|Motion to reconsider passage adopted", t, re.I):
            hh = h
            if re.search(r"passage|its action", t, re.I):
                passed.discard(hh)
            steps.append((d, hh, f"The {HOUSE[hh]} voted to reconsider its vote", "reconsider"))
            continue
        mreq = re.match(r"(House|Senate) requests? (?:House|Senate) to concur", t, re.I)
        if mreq:
            hh = mreq.group(1)[0].upper()
            amended_by.add(hh)
            concurred.discard(OTHER[hh])
            steps.append((d, hh, f"The {HOUSE[hh]} asked the {HOUSE[OTHER[hh]]} to agree to its changes"
                          + (" (to when the act takes effect)" if "effective" in tl else ""), "askconcur"))
            continue
        mcon = re.match(r"(House|Senate) (concurred in|concur in part|refused to (?:concur|agree)|receded|refused to recede|agreed to conference|"
                        r"adopted conference report|rejected conference report)", t, re.I)
        if mcon:
            hh = mcon.group(1)[0].upper()
            w = mcon.group(2).lower()
            if w.startswith("concurred"):
                concurred.add(hh)
                amended_by.discard(OTHER[hh])
                steps.append((d, hh, f"The {HOUSE[hh]} agreed to the {HOUSE[OTHER[hh]]}'s changes" + (" (to when the act takes effect)" if "effective" in tl else ""), "concur"))
            elif w.startswith(("refused to concur", "refused to agree", "concur in part")):
                steps.append((d, hh, f"The {HOUSE[hh]} refused to agree to the {HOUSE[OTHER[hh]]}'s changes", "noconcur"))
            elif w == "receded":
                amended_by.discard(hh)
                steps.append((d, hh, f"The {HOUSE[hh]} dropped its changes (receded)", "recede"))
            elif w == "refused to recede":
                steps.append((d, hh, f"The {HOUSE[hh]} refused to drop its changes, and asked for a conference committee", "norecede"))
            elif w == "agreed to conference":
                steps.append((d, hh, f"The {HOUSE[hh]} agreed to a conference committee", "conf"))
            elif w == "adopted conference report":
                steps.append((d, hh, f"The {HOUSE[hh]} adopted the conference committee's report", "ccr"))
            else:
                steps.append((d, hh, f"The {HOUSE[hh]} rejected the conference committee's report", "conf"))
            continue
        if re.match(r"(?:Senate appoint|House appointed conferees|House conferees|To conference|Conference report)", t, re.I):
            steps.append((d, h, re.sub(r"(?i)^To conference$", "Sent to a conference committee", t), "conf"))
            continue
        if re.match(r"(?:On (?:\d\w+|second) reading|Read \d\w+ time|Placed on House Calendar|From House\w? Calendar|Having been read|Immediate consideration|Taken from table and placed)", t, re.I):
            if place not in ("committee", "between") or re.match(r"From House|Placed on House Calendar|On [23]\w+ reading", t, re.I):
                if place == "between":
                    pass
                elif place != "committee":
                    place = "floor"
            if re.match(r"Read \d\w+ time", t, re.I):
                n = re.match(r"Read (\d)", t).group(1)
                steps.append((d, h, f"Read the {['', 'first', 'second', 'third'][int(n)]} time", "reading"))
            elif re.match(r"On \d\w+ reading|Placed on House Calendar|From House", t, re.I):
                steps.append((d, h, t[:1].upper() + t[1:], "calendar"))
            continue
        if re.match(r"Markup Discussion", t, re.I):
            steps.append((d, h, f"The {comm + ' ' if comm else ''}Committee discussed it", "markup"))
            continue
        if re.match(r"Bill withdrawn by lead sponsor", t, re.I):
            withdrawn = True
            steps.append((d, h, "Withdrawn by its lead sponsor", "other"))
            continue
        if re.match(r"(?:Effective|Effect from)", t, re.I):
            steps.append((d, h, re.sub(r"\s*\((?:Roll No\.? \d+|Voice vote)\)", "", t) + " (voted)", "effective"))
            continue
        if re.match(r"Postponed indefinitely|Tabled (?:on|amendment and bill)|Tabled by", t, re.I):
            steps.append((d, h, t, "other"))
            continue
        # Amendments, motions, readings postponed: as written.
        UNREAD[re.sub(r"\d+", "#", t)[:80]] += 1
        steps.append((d, h, t[:1].upper() + t[1:], "other"))

    # Laws and vetoes, checked against the governor's lists.
    lst = listing(session)
    gov = lst.get("governor") or {}
    if not const:
        if p in (gov.get("SIGNED") or {}) or p in (gov.get("BECAME LAW (NO SIGNATURE)") or {}):
            law = True
        if p in (gov.get("VETOED") or {}) and not law:
            vetoed = True
    # Passed both houses: "Completed legislative action" (and the completed list), or the governor's desk.
    both = completed or sent or law or vetoed or p in (lst.get("laws") or {})
    if not law or const:
        chapter = None
        steps = [s_ for s_ in steps if s_[3] != "chapter"]
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

    title = title_of(b["title"], const)
    official = b.get("official") or ""
    topics = ["const"] if const else []
    for h_, c in refs:
        tp = P.COMMITTEE_TOPICS.get(c)
        if tp and tp not in topics:
            topics.append(tp)
    for sj in b["subjects"]:
        for tp in P.SUBJECT_TOPICS.get(sj.lower(), []):
            if tp not in topics:
                topics.append(tp)
    if not topics:
        topics = [k for k, rx in P.TOPIC_WORDS.items() if rx.search(f"{title} {official[:300]}")]
    topics = list(dict.fromkeys(t for t in topics if t != "const" or const))

    # Sponsors in order: the lead sponsor first.
    names = [sponsor_name(session, origin, n) for n in b["sponsors"]]
    sponsor, district = names[0] if names else ("—", None)
    cos = [n for n, _ in names[1:] if n != sponsor]
    for n, dd in names:
        m = next((x for x in members() if x["house"] == origin and x["name"] == n), None)
        if m and m.get("party") in ("Republican", "Democrat", "Democratic"):
            parties[(origin, n)] = "R" if m["party"] == "Republican" else "D"

    cur = where
    if stage == 0:
        dsc = f"In {HOUSE[cur]} committee" if place in ("committee", "between") else "Introduced"
    elif stage == 1:
        dsc = f"On the {HOUSE[cur]} floor"
    else:
        dsc = {2: f"Passed the {HOUSE[origin] if origin in passed else HOUSE[other]}", 3: "Passed both houses",
               4: "On the governor's desk", 5: "Became law", 6: "Vetoed"}[stage]
    passed_in = (HOUSE[origin] if origin in passed else HOUSE[other]) if stage == 2 else None
    asks = [s_ for s_ in steps if s_[3] in ("askconcur", "final", "pass", "concur", "noconcur", "norecede", "conf", "ccr")]
    if stage == 2 and len(passed) == 2 and asks and asks[-1][3] == "askconcur":
        # Both houses passed it, but the last one changed it: back in the other house, to agree to the changes.
        amender = asks[-1][1]
        passed_in = HOUSE[amender]
        dsc = f"In the {HOUSE[OTHER[amender]]}, to agree to the {HOUSE[amender]}'s changes"
    comm_now = comm if place in ("committee", "between") and stage in (0, 2) else None

    def dates(test, mode="last"):
        ds = sorted({s[0] for s in steps if test(s) and s[0]})
        return {"first": ds[0], "last": ds[-1], "all": ";".join(ds)}[mode] if ds else ""

    steps.sort(key=lambda s: s[0])  # (stable: the governor's lines take the date written in them)
    action_dates = [s[0] for s in steps if s[0]]
    rec = {
        "nums": [p], "base": [p], "prev": earlier(session, b),
        "title": title, "summary": relating(official) if official else "", "act": "", "lawCode": "", "law": None, "laws": [],
        "comms": sorted({f"{h_} · {c}" for h_, c in refs}), "topics": topics, "places": [],
        "narrow": P.narrow_kind(title),
        "commFate": "passed" if reported or passed else "none", "mainTopic": topics[0] if topics else "",
        "local": "local" in topics, "senDeleg": False, "asmDeleg": False,
        "budget": bool(re.search(r"\b(?:budget|appropriat\w*|expiring funds)", title, re.I)) and not const,
        "passedS": "S" in passed, "passedA": "H" in passed, "program": None,
        "stage": stage, "passedIn": passed_in,
        "chapter": chapter if stage == 5 else None,
        "veto": None, "memo": "", "vetoMemo": None,
        "simText": f"{title} {official} {' '.join(b['code'][:8])}",
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
            dates(lambda s: s[3] in ("signed", "nosign")) if stage == 5 else "",
            # (Not for a law: SB 369 of 2025, vetoed, then amended to meet the governor's objections, passed again and
            # signed, wasn't overridden.)
            dates(lambda s: s[3] == "vetoed") if stage != 5 else "",
        ],
        "votes": fvotes, "firstComms": [(origin, first_ref, first_report or bool(passed))] if first_ref else [],
        "vers": [{"p": p, "sponsor": sponsor, "district": district or 0, "cosponsors": cos,
                  "primes": 1, "cosp": len(cos), "statusDesc": dsc, "committee": comm_now,
                  "actions": [[s[0], s[2]] for s in steps]}],
    }
    if stage == 5 and not rec["keyDates"][5]:
        rec["keyDates"][5] = rec["last"]
    return rec


# ---- "What it does" ----

def texts_of(session, p):
    try:
        return json.load(open(os.path.join(folder(session), "texts", f"{p}.json"), encoding="utf-8")).get("docs") or {}
    except (OSError, ValueError):
        return {}


def note_text(note, limit=3000):
    """"NOTE: The purpose of this bill is to ..." -> "The purpose of this bill is to ..." (cut at a sentence after limit
    characters: one note revising the criminal code runs to 45,000)."""
    t = re.sub(r"\s+", " ", note or "").strip()
    t = re.sub(r"^NOTE:?\s*", "", t)
    t = re.sub(r"\s*Strike-throughs indicate .*$", "", t)
    if len(t) > limit:
        cut = t[:limit].rfind(". ")
        t = t[:cut + 1 if cut > limit // 2 else limit].rstrip() + " …"
    return t


def what_it_does(session, b):
    """The newest text version's drafter's note (the page lists versions newest first), with its source."""
    docs = texts_of(session, b["key"])
    order = [d for d in b["docs"] if d in docs] + [d for d in docs if d not in b["docs"]]
    for i, d in enumerate(order):
        x = docs[d]
        if x.get("title") and not b.get("official"):
            b["official"] = x["title"]
        if x.get("note"):
            v = (x.get("version") or "").lower()
            newest = i == 0 or all(not docs[o].get("note") and re.search(r"engross|enroll", docs[o].get("version") or "", re.I)
                                   for o in order[:i])
            where = "the committee substitute" if "substitute" in v and newest else \
                "the bill" if newest or "introduc" not in v else "the bill as introduced"
            if "JR" in b["key"]:
                where = where.replace("bill", "resolution")
            return {"statement": note_text(x["note"]), "label": f"From the drafter's note in {where}."}
    return None


def load_session(session):
    """Read one year's bills and return (records, bill number -> record index, fetched time, delegation)."""
    k = (session, "loaded")
    if k in _CACHE:
        return _CACHE[k]
    lst = listing(session)
    parties = _PARTIES.setdefault(session, {})
    recs, index, whats = [], {}, {}
    keys = [k_ for k_ in lst.get("bills") or [] if re.fullmatch(r"(HB|SB|HJR|SJR)\d+", k_)]
    for k_ in sorted(keys, key=lambda k_: ("JR" in k_, k_[0] != "H", int(re.sub(r"\D", "", k_)))):
        b = parse(session, k_)
        if not b or not b["actions"]:
            continue
        what = what_it_does(session, b)
        rec = record(session, b, parties)
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
RULES = re.compile(r"\bpromulgat|legislative rules?\b|\brules? relating\b|\bbudget\b|\bappropriat|\bsupplement", re.I)


def _norm(s):
    return re.sub(r"[^a-z0-9 ]", "", re.sub(r"\s+", " ", (s or "").lower())).strip()


def _keys(session):
    """A year's bills that didn't become law (not rule-making, budget or appropriation bills): (title and lead sponsor ->
    [bills], drafter's note -> [bills])."""
    if session not in _KEYS:
        by_title, by_note = defaultdict(list), defaultdict(list)
        lst = listing(session)
        for k in lst.get("bills") or []:
            if not re.fullmatch(r"(HB|SB)\d+", k) or k in (lst.get("laws") or {}):
                continue
            b = parse(session, k)
            if not b or not b["title"] or RULES.search(b["title"]):
                continue
            tk, nk = _title_key(b), _note_key(session, b)
            if tk:
                by_title[tk].append(k)
            if nk:
                by_note[nk].append(k)
        _KEYS[session] = (by_title, by_note)
    return _KEYS[session]


def _title_key(b):
    t = _norm(b["title"])
    if len(t.split()) < 3 or not b["sponsors"]:
        return ""
    return t + "|" + name_key(b["sponsors"][0])[0]


def _note_key(session, b):
    for x in texts_of(session, b["key"]).values():
        if x.get("note") and "intr" in (x.get("version") or "").lower():
            s = _norm(note_text(x["note"]))
            return s if len(s.split()) >= 15 else ""
    return ""


def earlier(session, b):
    """The same bill in the two years before: the same short title and lead sponsor, or the same drafter's note (as
    introduced) word for word, held by one bill in each year. Never rule-making, budget or appropriation bills, nor a
    bill that became law."""
    out = set()
    if "JR" in b["key"] or RULES.search(b["title"] or ""):
        return out
    tk, nk = _title_key(b), _note_key(session, b)
    for y in (session - 1, session - 2):
        if y not in sessions():
            continue
        by_title, by_note = _keys(y)
        mine_t, mine_n = _keys(session)
        for key, old, mine in ((tk, by_title, mine_t), (nk, by_note, mine_n)):
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


# ---- Checks against the Legislature's lists ----

def checks(session):
    """Compare laws, vetoes and completed bills with the governor's and the completed lists, bill for bill."""
    recs = load_session(session)[0]
    lst = listing(session)
    gov = lst.get("governor") or {}
    laws = set(gov.get("SIGNED") or {}) | set(gov.get("BECAME LAW (NO SIGNATURE)") or {})
    vetoes = set(gov.get("VETOED") or {}) - laws
    done = set(lst.get("laws") or {})
    mine_law = {r["nums"][0] for r in recs if r["stage"] == 5}
    mine_veto = {r["nums"][0] for r in recs if r["stage"] == 6}
    mine_done = {r["nums"][0] for r in recs if r["stage"] >= 3 and "const" not in r["topics"]}
    chapters = Counter(r["chapter"] for r in recs if r["chapter"])
    const = sorted(r["nums"][0] for r in recs if "const" in r["topics"] and r["stage"] == 3)
    items = sorted(r["nums"][0] for r in recs if any("line-item" in a[1] for a in r["vers"][0]["actions"]))
    nosig = sorted(r["nums"][0] for r in recs if any("without the governor" in a[1] for a in r["vers"][0]["actions"]))
    votes = [v for r in recs for v in r["votes"]]
    named = [m for v in votes for m, _ in v[6]]
    return {"bills": len(recs), "laws": len(mine_law), "official laws": len(laws), "differ": sorted(mine_law ^ laws),
            "without signature": nosig, "vetoes": len(mine_veto), "official vetoes": len(vetoes),
            "vetoes differ": sorted(mine_veto ^ vetoes), "completed": len(mine_done), "official completed": len(done),
            "completed differ": sorted(mine_done ^ done), "line items": items, "amendments to the voters": const,
            "chapters": f"{min(chapters, default=0)}-{max(chapters, default=0)}, {len(chapters)} numbers, "
                        f"repeated {[c for c, n in chapters.items() if n > 1]}",
            "floor votes": len(votes),
            "noes tied to seats": f"{sum(1 for m in named if '?' not in m)} of {len(named)}"}


if __name__ == "__main__":
    import sys
    for s in ([int(sys.argv[1])] if len(sys.argv) > 1 else sessions()):
        print(s, json.dumps(checks(s)))
    for k, n in UNREAD.most_common(30):
        print(n, k)
