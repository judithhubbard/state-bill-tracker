"""Minnesota's bills (downloaded by states/mn/fetch.py) in the shape build_data.py reads. One page per two-year
Legislature (the 94th is 2025-26): its House Files (HF) and Senate Files (SF), bill numbers running through both years.

Companions. Most bills are filed in both houses with the same text: a House File with a representative as chief author
and its Senate companion with a senator (the Revisor's record names each one's COMPANION). They are one record here, as
Tennessee's and New York's are: each number keeps its own history, and the record's lead is the number that got further.
When one passes its house, the other house usually takes it up in place of its own: the Senate "substitutes" the House
File for its Senate File ("HF substituted in committee", "Comm report: Subst. for SF on General Orders", "Rule 45-amend,
subst. General Orders": the House File amended to match the Senate's text), and the House the Senate File for its House
File ("Bills identical, SF substituted on General Register", then "HF indefinitely postponed").

The status record. Each number's record has each house's actions in its own list: an HF's House list, and its Senate list
once it reaches the Senate. Each list also copies the other house's messages ("Returned from Senate with amendment",
"Senate adopted conference committee report, bill repassed", "House conferees"); those copies are dropped (the house's own
list says it), except "Returned from ...", which is how the first house learns the second passed it. The governor's
actions are in both lists, with dates in the description and sometimes a day apart ("Governor approval 05/24/2023" in the
House list, "Governor's action Approval 05/25/23" in the Senate's): the bill's own house's list is used.
Wording: "Introduction and first reading, referred to" X; "Committee report, to adopt (as amended) and re-refer to" Y
(the House) and "Comm report: To pass (as amended) and re-refer to" Y (the Senate): approved and sent on; without a
committee, to the floor ("Second reading": the General Register or General Orders). Re-referrals for missed deadlines
("Joint rule 2.03, Deadlines, re-referred to" Rules), the first year's end ("House rule 4.20, interim disposition of bills,
returned to", "Rule 47, returned to") and so on are referrals. A motion's outcome is the next line ("Motion to re-refer"
X, then "Motion did not prevail": not a referral). Passages: "Bill was passed (as amended)" with a tally, "Third reading
Passed", "Bill was repassed as amended by the Senate" (the House agreeing to the Senate's changes), "Senate concurred and
repassed bill", "Bill was repassed as amended by Conference" / "Senate adopted CC report and repassed bill" (a conference
report, which needs both houses). The Senate writes one vote several ways on one day ("Senate adopted CC report and
repassed bill" 39-26 and "Third reading" 40-25): they are one passage, with the "Third reading" tally (the journal's).
Passed both houses: the first house's "Returned from Senate" (no amendment), its agreement to the second house's
amendments, or the same conference report adopted and repassed by both; the governor's action. Laws are chapters ("Laws
2025, chapter 39"), numbered through the Legislature (2024's chapters follow 2023's). Vetoed bills get chapter numbers
too (HF 2369 of 2023, chapter 65): "law" comes from the governor's approval, not the number.

Members' votes: the House's floor votes member by member from its vote pages (house_votes/); the Senate's from its
journal (journals/, text), where each roll call follows "The question was taken on the passage of the bill" and lists
"Those who voted in the affirmative were:" and "...in the negative...". Names are matched within each house: House
votes by the printed name the authors lists also use ("Anderson, P. E.") to the member's id, Senate ones by last name.
Members who voted that day in another roll call but not this one are shown as not voting.

Special sessions are left out (as in other states): the 2025 First Special Session (June 9, 2025) passed the budget, 15
laws in a day, bills numbered from HF 1 and SF 1 again. Resolutions are left out; constitutional amendments are bills
("... constitutional amendment proposed"), tagged "const": a majority of each house's members, then the voters.
"""
import gzip, json, os, re
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from states.mn import profile as P

HOUSE = {"S": "Senate", "H": "House"}
LIST_HOUSE = {"HOUSE": "H", "SENATE": "S"}
OTHER = {"H": "S", "S": "H"}
_CACHE, _PARTIES, _LOADED = {}, {}, {}
STATS = defaultdict(Counter)  # session -> what matched, for the report (python3 -m states.mn.convert)


def folder(session):
    return os.path.join(P.DATA, str(session))


def sessions():
    out = []
    for f in sorted(os.listdir(P.DATA)) if os.path.isdir(P.DATA) else []:
        d = os.path.join(P.DATA, f, "bills")
        if re.fullmatch(r"\d{4}", f) and os.path.isdir(d) and os.listdir(d):
            out.append(int(f))
    return out


def jload(path, default=None):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def text(x):
    return re.sub(r"\s+", " ", str(x or "").replace("​", "").replace("\xa0", " ")).strip()


def latest():
    return max(sessions())


def bills(session):
    """Bill number ("HF10") -> its status record, for every bill in the session's list."""
    key = ("bills", session)
    if key not in _CACHE:
        out = {}
        for n in listing(session):
            r = jload(os.path.join(folder(session), "bills", f"{n}.json"))
            if r:
                out[n] = r
        _CACHE[key] = out
    return _CACHE[key]


def listing(session):
    key = ("list", session)
    if key not in _CACHE:
        _CACHE[key] = jload(os.path.join(folder(session), "list.json"), {}) or {}
    return _CACHE[key]


def intro_year(session, n):
    """The year a bill was introduced (the Revisor's addresses use it): from the list's address."""
    uri = (listing(session).get(n) or {}).get("uri", "")
    m = re.search(r"/v1/\d+/(\d{4})/", uri)
    return int(m.group(1)) if m else session


def day(s):
    """"2025-02-06 00:00:00" / "05/23/2023" / "05/23/23" -> ISO date, or ""."""
    s = text(s)
    m = re.match(r"(\d{4})-(\d\d)-(\d\d)", s)
    if m:
        return m.group(0)
    m = re.search(r"\b(\d{1,2})/(\d{1,2})/(\d{4}|\d{2})\b", s)
    if m:
        y = int(m.group(3))
        try:
            return date(y + 2000 if y < 100 else y, int(m.group(1)), int(m.group(2))).isoformat()
        except ValueError:
            return ""
    return ""


def official(p):
    m = re.fullmatch(r"([HS]F)(\d+)", p)
    return f"{m.group(1)} {m.group(2)}" if m else p


# ---- members ---------------------------------------------------------------------------------------------------------

def members(house):
    """The current members (the latest Legislature's lists): House [{id, name, district "12A", party, ...}] and Senate
    [{mem_id, preferred_full_name, preferred_last_name, dist, party, ...}]."""
    key = ("members", house)
    if key not in _CACHE:
        name = "members_house.json" if house == "H" else "members_senate.json"
        out = []
        for s in sorted(sessions(), reverse=True):
            out = jload(os.path.join(folder(s), name), []) or []
            if out:
                break
        _CACHE[key] = out
    return _CACHE[key]


def seat_of(m, house):
    if house == "H":
        n = P.house_seat(m.get("district"))
        return f"H:{n}" if n else None
    d = re.fullmatch(r"0*(\d+)", text(m.get("dist")))
    return f"S:{int(d.group(1))}" if d else None


def full_name(m, house):
    return text(m.get("name") if house == "H" else m.get("preferred_full_name"))


def party_code(m):
    p = text(m.get("party")).upper()
    return "D" if p in ("DFL", "D") else "R" if p in ("R", "GOP") else ""


def house_keys(session):
    """The House's printed names ("Anderson, P. E.", as the authors lists, the vote pages and the conferee lists write
    them) -> the member's id on house.mn.gov, from every authors list of the session."""
    key = ("hkeys", session)
    if key not in _CACHE:
        seen = defaultdict(Counter)
        for r in bills(session).values():
            for a in (r.get("AUTHORS") or {}).get("HOUSE") or []:
                if a.get("MEMBER_NAME") and a.get("LEGISLATOR_KEY"):
                    seen[norm_name(a["MEMBER_NAME"])][str(a["LEGISLATOR_KEY"])] += 1
        _CACHE[key] = {n: c.most_common(1)[0][0] for n, c in seen.items() if len(c) == 1}
    return _CACHE[key]


def norm_name(n):
    return re.sub(r"\s+", " ", re.sub(r"\s*,\s*", ", ", text(n))).strip().lower()


def resolve(session, house, printed):
    """A printed name ("Anderson, P. E." in the House, "Johnson Stewart" in the Senate) -> (seat, full name, party) for
    a current member, else (None, the name as printed, "")."""
    key = ("resolve", session, house)
    if key not in _CACHE:
        _CACHE[key] = {}
    memo = _CACHE[key]
    if printed in memo:
        return memo[printed]
    out = (None, display(printed), "")
    if house == "H":
        k = house_keys(session).get(norm_name(printed))
        by_id = {str(m.get("id")): m for m in members("H")}
        m = by_id.get(k) if k else None
        if not m:
            # Not among the authors this session: a unique last name among the current members.
            last = norm_name(printed).split(",")[0]
            hits = [x for x in members("H") if norm_name(x["name"]).endswith(" " + last)]
            m = hits[0] if len(hits) == 1 and "," not in printed and session == latest() else None
        if m:
            out = (seat_of(m, "H"), full_name(m, "H"), party_code(m))
    else:
        want = norm_name(printed)
        hits = [x for x in members("S") if norm_name(x.get("preferred_last_name")) == want]
        if not hits:
            hits = [x for x in members("S") if norm_name(x.get("preferred_full_name")).endswith(" " + want)]
        if len(hits) == 1:
            m = hits[0]
            out = (seat_of(m, "S"), full_name(m, "S"), party_code(m))
    memo[printed] = out
    return out


def display(printed):
    """"Anderson, P. E." -> "P. E. Anderson"; "Hortman" stays."""
    m = re.fullmatch(r"(.+?),\s*(.+)", text(printed))
    return f"{m.group(2)} {m.group(1)}" if m else text(printed)


# ---- votes -------------------------------------------------------------------------------------------------------------

def house_rolls(session):
    """(date, bill number) -> the House's roll calls on the bill's passage that day: {yeas, nays, yes, no, kind}; and
    date -> every name voting in any roll call that day (to tell who didn't vote)."""
    key = ("hrolls", session)
    if key not in _CACHE:
        out, present = defaultdict(list), defaultdict(set)
        d = os.path.join(folder(session), "house_votes")
        for f in sorted(os.listdir(d)) if os.path.isdir(d) else []:
            for v in jload(os.path.join(d, f), []) or []:
                when = day(v.get("date"))
                names = [text(x) for x in (v.get("yes") or []) + (v.get("no") or [])]
                present[when] |= set(names)
                what = text(" ".join((v.get("description") or [])[1:]))
                if not re.search(r"\b(re)?passage\b", what, re.I):
                    continue
                m = re.fullmatch(r"([HS]F)0*(\d+)", text(v.get("bill")) or f[:-5])
                if not m:
                    continue
                out[(when, f"{m.group(1)}{m.group(2)}")].append({
                    "yeas": int(v.get("yeas") or 0), "nays": int(v.get("nays") or 0),
                    "yes": [text(x) for x in v.get("yes") or []], "no": [text(x) for x in v.get("no") or []], "what": what})
        _CACHE[key] = (out, present)
    return _CACHE[key]


PAGE_HEAD = re.compile(r"JOURNAL OF THE SENATE|^\s*\d+(?:ST|ND|RD|TH) DAY\]|^\s*\[?\d+(?:ST|ND|RD|TH) DAY")
NAME = re.compile(r"[A-Z][A-Za-z'’.\-]+(?: [A-Z][A-Za-z'’.\-]+){0,2}")


def name_rows(lines, i):
    """The names listed from line i on, until the list ends (a blank line followed by prose, or prose)."""
    names = []
    while i < len(lines):
        raw = lines[i]
        if not raw.strip() or PAGE_HEAD.search(raw):
            i += 1
            continue
        if raw.startswith("  "):  # an indented line: the next paragraph
            break
        cells = [c.strip() for c in re.split(r"\s{2,}", raw.strip()) if c.strip()]
        if not cells or not all(NAME.fullmatch(c) for c in cells):
            break
        names += cells
        i += 1
    return names, i


def senate_rolls(session):
    """(date, bill number) -> the Senate's roll calls on the bill's passage or repassage that day, from its journal:
    {yeas, nays, yes, no, kind}; and date -> every senator voting in any roll call that day."""
    key = ("srolls", session)
    if key not in _CACHE:
        out, present = defaultdict(list), defaultdict(set)
        d = os.path.join(folder(session), "journals")
        for f in sorted(os.listdir(d)) if os.path.isdir(d) else []:
            m = re.match(r"(\d{4})(\d\d)(\d\d)", f)
            if not m:
                continue
            when = f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
            try:
                raw = gzip.open(os.path.join(d, f), "rt", encoding="utf-8", errors="replace").read()
            except OSError:
                continue
            lines = [l.replace("​", "").replace("\x0c", "").rstrip() for l in raw.split("\n")]
            last_bill, question, prev = None, "", 0
            for i, l in enumerate(lines):
                bm = re.search(r"\b([HS])\.\s?F\.\s+No\.\s+(\d+)", l)
                if bm:
                    last_bill = f"{bm.group(1)}F{bm.group(2)}"
                qm = re.search(r"The question was taken on (.*)", l)
                if qm:
                    question = qm.group(1) + " " + (lines[i + 1] if i + 1 < len(lines) else "")
                rm = re.search(r"The roll was called, and there were yeas (\d+) and nays (\d+)", l)
                if not rm:
                    continue
                yeas, nays = int(rm.group(1)), int(rm.group(2))
                yes, no = [], []
                j = i + 1
                while j < len(lines) and j < i + 200:
                    if "voted in the affirmative were" in lines[j]:
                        yes, j = name_rows(lines, j + 1)
                        continue
                    if "voted in the negative were" in lines[j]:
                        no, j = name_rows(lines, j + 1)
                        break
                    if re.search(r"The roll was called|^\s+So the |The motion (did not )?prevail", lines[j]):
                        break
                    j += 1
                present[when] |= set(yes) | set(no)
                kind = "repass" if re.match(r"(?:the )?(?:final )?repassage", question.strip()) else \
                    "pass" if re.match(r"(?:the )?(?:final )?passage", question.strip()) else None
                question = ""
                if kind and last_bill:
                    out[(when, last_bill)].append({"yeas": yeas, "nays": nays, "yes": yes, "no": no, "kind": kind,
                                                   "listed": len(yes) == yeas and len(no) == nays})
        _CACHE[key] = (out, present)
    return _CACHE[key]


def floor_vote(session, h, p, d, tally, fold=None):
    """The roll call for a passage step: [house, "F", None, date, yeas, nays, [[seat or "H?Name", "N"/"A"], ...]]. A
    special session's House votes are in its own folder; its Senate votes in the regular session's journals."""
    rolls, present = house_rolls(fold or session) if h == "H" else senate_rolls(session)
    cands = rolls.get((d, p), [])
    if tally:
        same = [r for r in cands if (r["yeas"], r["nays"]) == tally]
        cands = same or ([] if len(cands) > 1 else cands)
    r = cands[-1] if cands else None
    STATS[session][f"{HOUSE[h]} passages"] += 1
    if not r:
        if not tally:
            return None
        return [h, "F", None, d, tally[0], tally[1], []]
    STATS[session][f"{HOUSE[h]} passages matched to a roll call"] += 1
    if h == "S" and not r.get("listed", True):
        STATS[session]["Senate roll calls whose name lists don't add up"] += 1
    listed, seen = [], set()
    for n in r["no"]:
        seat, name, _ = resolve(session, h, n)
        listed.append([seat or f"{h}?{name}", "N"])
        seen.add(n)
    for n in sorted(present.get(d, set()) - set(r["yes"]) - set(r["no"])):
        seat, name, _ = resolve(session, h, n)
        listed.append([seat or f"{h}?{name}", "A"])
    for n in r["yes"] + r["no"]:
        STATS[session][f"{HOUSE[h]} names"] += 1
        STATS[session][f"{HOUSE[h]} names tied to a current member's seat"] += bool(resolve(session, h, n)[0])
    return [h, "F", None, d, r["yeas"], r["nays"], listed]


# ---- one number's history ----------------------------------------------------------------------------------------------

def committee(c):
    return re.sub(r"\s+Committee$", "", text(c))


def tally_of(a):
    m = re.fullmatch(r"(\d+)-(\d+)", text(a.get("ROLL_CALL")))
    return (int(m.group(1)), int(m.group(2))) if m else None


def steps_of(session, p, r):
    """One number's history as steps {d, h, k, t, comm, tally, amended}, in order: the house's own lines from each list
    (the other house's messages dropped), the governor's from the bill's own house's list."""
    own = p[0]  # "H" or "S"
    lists = {LIST_HOUSE[k]: (v if isinstance(v, list) else [v]) for k, v in (r.get("ACTIONS") or {}).items() if k in LIST_HOUSE}
    gov_from = own if any(re.match(r"Presented to Governor|Presentment date|Governor|Governor's action", text(a.get("ACTION_TEXT")))
                          for a in lists.get(own, [])) else OTHER[own]
    # The governor's dates in the other list, for a line whose own date is mistyped ("Governor approval 05/27/226": HF
    # 4591 of 2025-26).
    alt = {}
    for a in lists.get(OTHER[gov_from], []):
        t = text(a.get("ACTION_TEXT"))
        k = "sent" if re.match(r"Presented to Governor|Presentment date", t) else "signed" if re.match(r"Governor approval|Governor's action Approval", t) \
            else "veto" if re.match(r"Governor veto|Governor's action Veto", t) else None
        if k and day(a.get("ACTION_DESCRIPTION")):
            alt[k] = day(a.get("ACTION_DESCRIPTION"))
    per = {}
    for h, acts in lists.items():
        out, last_d, pending = [], "", None
        for a in sorted(acts, key=lambda a: int(a.get("ACTION_NUMBER") or 0)):
            t, c, desc, tl = text(a.get("ACTION_TEXT")), committee(a.get("COMMITTEE_NAME")), text(a.get("ACTION_DESCRIPTION")), tally_of(a)
            d = day(a.get("ACTION_DATE")) or (day(desc) if re.search(r"Governor|Presentment|Secretary of State|Chapter", t) else "") or last_d
            last_d = d or last_d
            gov = re.match(r"(Presented to Governor|Presentment date|Governor approval|Governor's action|Governor veto|Secretary of State|Chapter number|Resolution number|Joint rule 3.02\(c\))", t)
            if gov and h != gov_from:
                continue
            res = decode(p, h, t, c, desc, tl, pending)
            if res == ["PENDING"]:
                if pending:  # a motion with no outcome line: as written
                    out.append({"k": "other", "t": pending[0] + (f" {pending[1]}" if pending[1] else "") + (f" ({pending[2]})" if pending[2] else ""), "d": pending[3], "h": h})
                pending = (t, c, desc, d)
                continue
            if res and res[0] == "RESOLVED":
                res, pending = res[1:], None
            elif pending:
                out.append({"k": "other", "t": pending[0] + (f" {pending[1]}" if pending[1] else "") + (f" ({pending[2]})" if pending[2] else ""), "d": pending[3], "h": h})
                pending = None
            for st in res:
                if st["k"] in alt and st.get("h") == "G" and not day(desc):
                    st["d"] = alt[st["k"]]
                st["d"] = st.get("d") or d
                st["h"] = st.get("h") or h
                out.append(st)
        per[h] = out
    return merge(per, own)


def merge(per, own):
    """Both houses' steps in date order. Within a day, the house the bill was in first: the house a "Received from" or
    "Returned from" line moves it out of goes before."""
    days = defaultdict(lambda: defaultdict(list))
    for h, ss in per.items():
        for s in ss:
            days[s["d"]][h].append(s)
    out = []
    for d in sorted(days):
        by = days[d]
        if len(by) == 1:
            out += next(iter(by.values()))
            continue
        later = {h for h, ss in by.items() if any(s["k"] in ("received", "returned", "returned_amended") for s in ss)}
        order = sorted(by, key=lambda h: (h in later, h != own))
        for h in order:
            out += by[h]
    # The governor's steps after the houses' on the same day.
    gov = ("sent", "signed", "veto", "itemveto", "chapter")
    return sorted(out, key=lambda s: (s["d"], s["h"] == "G" and s["k"] in gov))


REF = re.compile(r"referred to|returned to|re-refer|Re-referred to", re.I)


def decode(p, h, t, c, desc, tl, pending):
    """One action line -> steps (dicts), "PENDING" (a motion whose outcome is the next line) or "RESOLVED"."""
    H = HOUSE[h]
    S = lambda k, txt, **kw: dict(k=k, t=txt, comm=kw.get("comm"), tally=kw.get("tally"), amended=kw.get("amended", False), h=kw.get("h"))
    low = t.lower()
    with_tally = (lambda s: f"{s}, {tl[0]}-{tl[1]}" if tl else s)
    # Authors, cross-references and filing: the sponsor lists hold the authors.
    chm = re.match(r"Chapter (\d+)", desc) if t == "Secretary of State" else None
    if chm:
        return [S("chapter", f"CHAPTER {chm.group(1)}", h="G") | {"num": chm.group(1)}]
    if re.match(r"(Chief )?Authors? (added|stricken|changed)|Chief author|Author changed|Authors changed|See$|See Also|See Senate file|\(Non-revisor companion\)|Secretary of State|Resolution number", t):
        return []
    # The other house's messages, copied into this house's list (the other house's own list has them).
    if h == "H" and re.match(r"Senate (accedes|conferees|adopted|refuses|not concur|concurred)", t):
        return []
    if h == "S" and re.match(r"House (accedes|conferees|adopted|refuses|not concur|conferee change)|Bill laid on table in House", t):
        return []
    # A motion and its outcome (the House writes them as two lines).
    if pending and re.match(r"Motion (prevailed|did not prevail)", t):
        mt, mc, md = pending[:3]
        ok = "did not" not in t
        what = re.sub(r"^Motion (to|for) ", "", mt).rstrip(",")
        what = f"{what} {mc}".strip() if mc else f"{what} ({md})" if md else what
        steps = [S("motion", f"A motion to {what} {'passed' if ok else 'failed'}" + (f", {tl[0]}-{tl[1]}" if tl else ""))]
        if ok and re.match(r"Motion to (recall and )?re-refer", mt) and mc:
            steps.append(S("ref", f"REFERRED TO {mc.upper()}", comm=mc))
        if ok and re.match(r"Motion for reconsideration", mt):
            steps.append(S("reconsider", f"The {H} voted to reconsider"))
        if ok and re.match(r"Motion to return bill to author", mt):
            steps.append(S("withdrawn", "Withdrawn and returned to its author"))
        return ["RESOLVED"] + steps
    if re.match(r"Motion (to|for) ", t) and not re.search(r"motion (prevailed|did not prevail)", low):
        return ["PENDING"]
    if re.search(r"did not prevail", low):
        what = desc or re.sub(r"^Motion (to|for) |,?\s*(motion )?did not prevail$", "", t, flags=re.I)
        what = re.sub(r"^(a motion |motion )", "", what, flags=re.I)
        what = what if re.match(r"(to|for) ", what) else f"to {what[:1].lower() + what[1:]}"
        return [S("motion", with_tally(f"A motion {what} failed"))]
    if t == "Motion prevailed" or t == "Motion":
        return [S("motion", with_tally(f"A motion {desc} passed" if desc else "A motion passed"))]
    if re.match(r"Motion to recall and re-refer, motion prevailed|Motion to recall pursuant", t) and c:
        return [S("ref", f"REFERRED TO {c.upper()}", comm=c)]
    if re.match(r"Motion to return bill to author, motion prevailed|Withdrawn and returned to author", t):
        return [S("withdrawn", "Withdrawn and returned to its author")]

    # Introduction and referral.
    if t == "Introduction and first reading, referred to":
        return [S("intro", "Introduced")] + ([S("ref", f"REFERRED TO {c.upper()}", comm=c)] if c else [])
    if t == "Introduction and first reading":
        return [] if p[0] != h else [S("intro", "Introduced")]
    if re.match(r"Received from (House|Senate)", t):
        return [S("received", f"Received in the {H}")]
    if re.match(r"Senate file first reading", t):
        steps = [S("received", "Received in the House")]
        if c:
            steps.append(S("ref", f"REFERRED TO {c.upper()}", comm=c))
        elif "comparison" in t:
            steps.append(S("floor", f"Held to compare with the House's own bill{', ' + desc if desc else ''}"))
        return steps
    if t == "Referred to" and c:
        if "comparison" in desc:
            return [S("ref", f"REFERRED TO {c.upper()}", comm=c), S("other", f"For comparison with {desc.replace('for comparison with ', '')}")]
        return [S("ref", f"REFERRED TO {c.upper()}", comm=c)]

    # Committee reports.
    if re.match(r"Committee report|Comm report:|Division action", t):
        if re.search(r"Subst\. for SF|subst\. General Orders", t):
            return [S("report", "REPORTED", amended="Rule 45" in t), S("floor", f"Took the place of {official(desc) if desc else 'the Senate File'} on General Orders" + (", amended to match it" if "Rule 45" in t else ""), amended="Rule 45" in t)]
        if re.search(r"Adopt previous comm report|Amend previous comm report", t):
            return [S("other", f"{H} committee report adopted again" + (f" ({desc})" if desc else ""))]
        amended = "amend" in low
        how = "approved it" + (" with amendments" if amended else "")
        if "no recommendation" in low or "without further recommendation" in low:
            how = "sent it on without a recommendation"
        steps = [S("report", "REPORTED", amended=amended)]
        if c and ("re-refer" in low or "re-referred" in low or "return to" in low):
            steps.append(S("ref", f"REFERRED TO {c.upper()}", comm=c))
        else:
            steps.append(S("floor", f"The committee {how}; to the floor"))
        steps[0]["how"] = how
        return steps
    if REF.search(t) and c and not re.search(r"did not prevail|author", low):
        return [S("ref", f"REFERRED TO {c.upper()}", comm=c)]
    if re.match(r"Referred by Chair to", t) and c:
        return [S("ref", f"REFERRED TO {c.upper()}", comm=c)]

    # Substitutions: this number gives way to the other house's.
    if re.match(r"HF substituted (in committee|by motion)", t) or (p.startswith("SF") and re.match(r"Rule 45(-amend)?[,;] subst\. General Orders", t)):
        return [S("replaced", f"Replaced by {official(desc) if desc else 'the House File'}, which the Senate took up in its place")]
    if re.match(r"Bills (not )?identical, SF substituted on General Register", t):
        if p.startswith("HF"):
            return [S("replaced", "Replaced by the Senate File, which the House took up in its place")]
        return [S("floor", "Took the place of the House File on the General Register")]
    if t == "HF indefinitely postponed":
        return [S("replaced", "Indefinitely postponed: the House passed the Senate File instead")]

    # The floor.
    if t == "Second reading":
        return [S("floor", "Second reading" + (": on the General Register" if h == "H" else ": on General Orders"))]
    if re.match(r"House rule 1\.21, placed on Calendar for the Day", t):
        return [S("floor", "Placed on the Calendar for the Day" + (f" ({desc})" if desc else ""))]
    if re.match(r"House rule 1\.23, placed on Consent Calendar|Committee report, .*Consent Calendar", t):
        return [S("floor", "Placed on the Consent Calendar")]
    if re.match(r"Special Order|Placed on General Orders|Rule 5\.1: withdrawn, placed on General Orders|Urgency declared|Rules suspended, urgency", t):
        am = "Amended" in t
        return [S("floor", {"Special Order": "Taken up as a special order", "Special Order: Amended": "Taken up as a special order and amended"}.get(t, t), amended=am)]
    if t in ("Amended", "Amendments offered"):
        return [S("amend", f"Amended on the {H} floor" if t == "Amended" else "Amendments offered")]
    if re.match(r"(Special Order: )?Rule 45:? amendment stricken", t):
        return [S("other", "The amendment matching it to the Senate File was struck")]

    # Passages.
    if h == "H" and re.match(r"Bill was (re)?passed", t):
        kind = "concur" if "by the Senate" in t else "ccr" if "by Conference" in t else "pass"
        return [S("pass", "PASSED HOUSE", tally=tl, amended="as amended" in t and kind == "pass", kind=kind) | {"kind": kind}]
    if h == "H" and re.match(r"Bill was not passed", t):
        return [S("fail", with_tally("Failed in the House"))]
    if h == "S" and t == "Senate concurred":
        # Agreeing to the House's amendments; the repassage is its own vote, which can fail to happen (SF 4225 of 2023-24:
        # "Third reading", "due to the constitutional deadline the bill was not passed").
        return [S("other", "The Senate agreed to the House's amendments")]
    if h == "S" and re.match(r"Third reading Passed|Bill passed|Bill repassed|Third Reading Repassed|Senate concurred and repassed|Senate adopted CC report", t):
        kind = "concur" if t.startswith("Senate concurred") else "ccr" if "CC report" in t else "pass"
        if t == "Senate adopted CC report":
            return [S("other", "The Senate adopted the conference committee report")]
        return [S("pass", "PASSED SENATE", tally=tl, amended="as amended" in t and kind == "pass") | {"kind": kind}]
    if h == "S" and t == "Third reading" and tl:
        return [S("pass", "PASSED SENATE", tally=tl) | {"kind": "pass", "weak": True}]
    if re.match(r"Third reading Failed", t):
        return [S("fail", with_tally("Failed in the Senate"))]
    if re.match(r"Third reading", t):
        return [S("reading", "Third reading" + (" as amended" if "amended" in t else "") + (f": {desc}" if desc else ""))]
    if t == "Reconsidered":
        return [S("reconsider", f"The {H} voted to reconsider")]
    if h == "H" and re.match(r"House adopted conference committee report", t):
        return [S("other", with_tally("The House adopted the conference committee report"))]

    # Between the houses.
    if re.match(r"Returned from (House|Senate) with amendment", t):
        return [S("returned_amended", f"Returned from the {HOUSE[OTHER[h]]} with amendments")]
    if re.match(r"Returned from (House|Senate)$", t):
        return [S("returned", f"Returned from the {HOUSE[OTHER[h]]} without amendments")]
    if re.search(r"refuses to concur|not concur|conference committee .*requested|New conference committee", t):
        return [S("conf", f"The {H} refused to agree to the {HOUSE[OTHER[h]]}'s amendments and asked for a conference committee"
                   if re.search(r"refuses|not concur", t) else "A conference committee was requested")]
    if re.search(r"accedes", t):
        return [S("conf", f"The {H} agreed to a conference committee")]
    if re.match(r"(House|Senate) conferees", t):
        return [S("other", f"{H} conferees: {desc}" if desc else f"{H} conferees named")]
    if re.match(r"Conference committee report", t):
        return [S("other", "Conference committee report" + (": a new text in place of the bill's" if "delete everything" in t else ""))]
    if re.match(r"Motion to reject CC report", t):
        return [S("motion", with_tally("A motion to reject the conference committee report failed"))]
    if re.search(r"conference committee discharged", t):
        return [S("other", "The conference committee was discharged at the session's end; the bill was laid on the table")]
    if re.match(r"Bill returned to conference committee", t):
        return [S("conf", "Sent back to the conference committee")]

    # The governor.
    if re.match(r"Presented to Governor|Presentment date", t):
        return [S("sent", "DELIVERED TO GOVERNOR", h="G") | ({"d": day(desc)} if day(desc) else {})]
    if re.match(r"Governor approval|Governor's action Approval", t):
        return [S("signed", "Signed by the governor", h="G") | ({"d": day(desc)} if day(desc) else {})]
    if re.match(r"Governor veto|Governor's action Veto", t):
        return [S("veto", "VETOED", h="G") | ({"d": day(desc)} if day(desc) else {})]
    if re.match(r"Governor's action Line|line item", t, re.I):
        return [S("itemveto", "The governor vetoed items of it (line-item veto)", h="G")]
    if t == "Chapter number":
        return [S("chapter", f"CHAPTER {desc}", h="G") | {"num": desc}]
    if re.match(r"Joint rule 3\.02\(c\)", t):
        return [S("other", "Returned by the governor and laid on the table")]
    if t == "Effective date":
        return [S("other", f"Takes effect: {desc}" if desc else "Effective date set", h="G")]

    if t in ("Laid on table",):
        return [S("table", f"Laid on the table in the {H}" + (f" ({desc})" if desc else ""))]
    if t == "Taken from table":
        return [S("other", f"Taken from the table in the {H}")]
    if t == "Withdrawn":
        return [S("other", f"Withdrawn {('(' + desc + ')') if desc else 'from committee'}")]
    if t == "Note":
        return [S("other", desc)] if desc else []
    # Anything else as written (points of order, rule notes).
    return [S("other", t + (f": {desc}" if desc else "") + (f" {c}" if c else "") + (f", {tl[0]}-{tl[1]}" if tl else ""))]


# ---- where a number got --------------------------------------------------------------------------------------------

def work_out(steps, origin):
    """Stage and place from one number's steps: {stage, passed (houses), now, place, comm, both, law, veto, sent,
    replaced, withdrawn}. Passed both houses: the first house's "Returned from" line (no amendments), its agreement to
    the second house's amendments, the same conference report repassed by both, or the governor's action."""
    other = OTHER[origin]
    passed, failed = {}, set()
    now, place, comm = origin, "committee", None
    both, need, ccr = False, None, set()
    sent = law = veto = replaced = withdrawn = False
    chapter = None
    last_pass = {}
    changed = False  # the second house amended it since it got there
    for i, s in enumerate(steps):
        k, h = s["k"], s["h"]
        if h == other and origin in passed and (k == "amend" or s.get("amended")) and k != "pass":
            changed = True
        if k == "ref" and h in HOUSE:
            now, place, comm = h, "committee", s["comm"]
        elif k in ("floor", "reading") and h in HOUSE:
            now, place = h, "floor"
        elif k == "received" and h in HOUSE:
            now, place, comm = h, "committee", None
        elif k == "pass" and h in HOUSE:
            kind = s.get("kind", "pass")
            passed[h] = i
            last_pass[h] = i
            failed.discard(h)
            if kind == "concur" and need == "concur":
                both, need = True, None
            elif kind == "ccr":
                ccr.add(h)
                if ccr >= {"H", "S"}:
                    both, need = True, None
            elif h == other and need is None and not both:
                amended = s.get("amended") or changed
                both = not amended
                need = "concur" if amended else None
            if h == other:
                changed = False
            if h == origin and other not in passed:
                now, place, comm = other, "committee", None
            elif h == other and not both:
                now, place = origin, "desk"
        elif k == "fail" and h in HOUSE:
            failed.add(h)
        elif k == "reconsider" and h in HOUSE:
            if h in passed:
                passed.pop(h)
                both = False
            failed.discard(h)
            place, now = "floor", h
        elif k == "returned":
            if other in passed or origin in passed:
                both, need = True, None
        elif k == "returned_amended":
            both, need = False, "concur"
            now, place = origin, "desk"
        elif k == "conf":
            both, need, ccr = False, "conf", set()
        elif k == "sent":
            sent = True
        elif k == "signed":
            law = True
        elif k == "veto":
            veto = True
        elif k == "chapter":
            chapter = s.get("num")
        elif k == "replaced":
            replaced = True
        elif k == "withdrawn":
            withdrawn = True
    if law or veto or sent:
        both = True
    if both:
        passed = {"H": 1, "S": 1}
    stage = 5 if law and not veto else 6 if veto else 4 if sent else 3 if both else 2 if passed else \
        1 if (place == "floor" or origin in failed) else 0
    return {"stage": stage, "passed": set(passed), "now": now, "place": place, "comm": comm, "law": law, "veto": veto,
            "sent": sent, "replaced": replaced, "withdrawn": withdrawn, "chapter": chapter, "failed": failed}


def merge_passes(steps):
    """The Senate writes one vote as several passage lines on one day; keep one, with the "Third reading" tally."""
    out = []
    for s in steps:
        if s["k"] == "pass":
            j = next((x for x in range(len(out) - 1, -1, -1) if out[x]["h"] == s["h"] and out[x]["d"] == s["d"]
                      and out[x]["k"] in ("pass", "reconsider", "fail", "returned_amended", "conf")), None)
            if j is not None and out[j]["k"] == "pass":
                prev = out[j]
                if s.get("tally") and (s.get("weak") or not prev.get("tally") or s["t"] == prev["t"]):
                    prev["tally"] = s["tally"]
                if s.get("kind") in ("concur", "ccr"):
                    prev["kind"] = s["kind"]
                prev["amended"] = prev.get("amended") or s.get("amended")
                continue
            if s.get("weak"):
                s = {**s, "weak": False}
        out.append(s)
    return out


# ---- texts --------------------------------------------------------------------------------------------------------------

MONTHS = "January|February|March|April|May|June|July|August|September|October|November|December"


def long_date(s):
    try:
        return datetime.strptime(text(s), "%B %d, %Y").date().isoformat()
    except ValueError:
        return ""


HEADING = re.compile(r"(Sections? \d+(?:\s*(?:to|and|-|–)\s*\d+)?\s*\[|Sec(?:tion|s?\.) \d+[A-Za-z]?(?:\s*(?:to|and|-|–)\s*\d+)?\.\s|Article \d+[:.]|ARTICLE \d+|Overview$|Summary$|Introduction$|Background$)")
LIGATURES = ("ti", "fi", "ff", "fl", "ffi", "ffl", "ft", "tt")
_VOCAB = []


def paragraphs(lines):
    """PDF lines -> paragraphs: lines joined, breaks at blank lines and before headings ("ARTICLE 1 – APPROPRIATIONS",
    "Section 3 [Greater Minnesota transit account]") when the line before ended a sentence."""
    out, cur = [], []

    def flush():
        if cur:
            out.append(text(" ".join(cur)))
            cur.clear()
    for l in lines:
        s = text(l)
        if not s:
            flush()
            continue
        if s in ("▪", "•", "\uf0a7", "◼", "o"):
            flush()
            continue
        if re.fullmatch(r"\d+(?:\s*[-–,]\s*\d+)*", s):  # a section number alone (House Research's tables)
            flush()
            out.append(s)
            continue
        caps = (len(s) > 3 and not re.search(r"[a-z]", s) and re.search(r"[A-Z]{3}", s)) or \
            (re.match(r"Article \d+[:.]", s) and len(s) < 90 and not re.search(r"[.;,]$", s))
        if caps or (HEADING.match(s) and (not cur or re.search(r"[.:;!?)\"”]$", cur[-1]))):
            flush()
        cur.append(s)
        if caps:
            flush()
    flush()
    out = [re.sub(r"\s*[▪•\uf0a7◼]\s*", " ", p).strip() for p in out if p]
    # A sentence cut by a page break: the next paragraph goes on in lower case.
    joined = []
    for p in out:
        if joined and not re.search(r"[.:;!?)\"”]$", joined[-1]) and re.match(r"[a-z(]", p) and \
                not re.fullmatch(r"[\d\s,–-]+", joined[-1]):
            joined[-1] += " " + p
        else:
            joined.append(p)
    return joined


def ligatures(t, vocab):
    """Characters the PDF's ligatures lost ("Ar\ufffdcle", "Sec\ufffdon": "ti"): the letters that make a word the
    summaries use elsewhere, else "ti"."""
    def fix(m):
        w = m.group(0)
        for lig in LIGATURES:
            cand = w.replace("\ufffd", lig)
            if cand.lower() in vocab:
                return cand
        return w.replace("\ufffd", "ti")
    return re.sub(r"[A-Za-z]*\ufffd[A-Za-z\ufffd]*", fix, t)


def cap(paras, limit=4000):
    # A heading in capitals alone ("ARTICLE 1", "ARTICLE 1 – APPROPRIATIONS") leads the paragraph after it.
    joined = []
    for p in paras:
        if joined and not re.search(r"[a-z]", joined[-1]) and len(joined[-1]) < 90 and not joined[-1].endswith(":"):
            joined[-1] = f"{joined[-1].rstrip('.')}: {p}"
        else:
            joined.append(p)
    paras = joined
    out, n = [], 0
    for p in paras:
        if n + len(p) > limit and out:
            out.append("The full summary is longer: see the bill's page.")
            break
        out.append(p)
        n += len(p)
    return "\n".join(out)


ABBR = re.compile(r"(?:\b(?:subds?|paras?|Minn|Stat|No|Nos|sec|secs|art|ch|U\.S|e\.g|i\.e|etc|Inc|Co|St|Dr|Mr|Ms|Jr|vs|approx|cl)|\b[A-Z])\.$")


def split_sentence(t):
    """(first sentence, the rest): a period, then a space and a capital letter or "§", not after an abbreviation."""
    for m in re.finditer(r"[.;]\s+(?=[A-Z§(“\"])", t):
        if not ABBR.search(t[:m.start() + 1]):
            return t[:m.start() + 1].strip(), t[m.end():].strip()
    return t.strip(), ""


def hrd_text(raw):
    """House Research's summary: its overview, or its summary's prose; for a table of sections, each section's heading
    and first sentence. -> (text, version, ISO date)."""
    lines = [l.rstrip() for l in raw.replace("\x0c", "\n").replace("​", "").split("\n")]
    joined = "\n".join(lines)
    ver = re.search(r"^[HS]\.F\. \d+\s*\n(.+)$", joined, re.M)
    dm = re.search(rf"^Date\s*\n+\s*((?:{MONTHS}) \d+, \d{{4}})", joined, re.M)
    when = long_date(dm.group(1)) if dm else ""
    # Drop page furniture: running heads, page numbers, the footer.
    body, skip = [], False
    head = re.compile(r"^([HS]\.F\. \d+|Minnesota House Research Department|Page \d+|Section Description.*|Section\s*$|Description\s*$)$")
    for l in lines:
        s = l.strip()
        if s.startswith("Minnesota House Research Department provides"):
            break
        if head.match(s) or (ver and s == ver.group(1).strip()):
            continue
        body.append(l)
    txt = "\n".join(body)
    start = re.search(r"^(Overview|Summary)\s*$", txt, re.M)
    if not start:
        return "", ver.group(1).strip() if ver else "", when
    rest = txt[start.end():].split("\n")
    paras = paragraphs(rest)
    # Section tables: a number alone, then "Heading." and the description: "Section 1: Heading. First sentence." Once
    # the table starts, only the sections' first lines and the articles' introductions are kept.
    out, i, table = [], 0, False
    while i < len(paras):
        p = paras[i]
        if re.fullmatch(r"\d+(?:\s*[-–,]\s*\d+)*", p) and i + 1 < len(paras):
            table = True
            head, body = split_sentence(paras[i + 1])
            # Not the citation ("Amends § 144.98, subd. 8."): the first sentence after it.
            while re.match(r"(Amends|Adds|Repeals|Creates|Modifies|Instructs the revisor)\b[^.]*?(§|subd\.|section|Laws \d{4}|Minnesota Rules)", body) and split_sentence(body)[1]:
                body = split_sentence(body)[1]
            first = split_sentence(body)[0] if body else ""
            if re.match(r"(Amends|Adds|Repeals) (§|subd)", first):
                first = ""
            out.append(f"Section {p}: {head} {first}".strip())
            i += 2
            continue
        if p in ("Summary", "Overview"):
            i += 1
            continue
        if re.match(r"Article \d+[:.]", p) and len(p) < 90 and not p.endswith(".") and i + 1 < len(paras) and \
                not re.fullmatch(r"[\d\s,–-]+", paras[i + 1]):
            out.append(f"{p}. {paras[i + 1]}")
            i += 2
            continue
        if not table or re.match(r"Article \d+", p):
            out.append(re.sub(r"^(Overview|Summary)\s+", "", p))
        i += 1
    return cap(out), ver.group(1).strip() if ver else "", when


def senate_text(raw):
    """A Senate summary: the text after its date, without page numbers. -> (text, the version it describes, ISO date)."""
    if re.search(r"BE IT ENACTED|A bill for an act", raw):
        return "", "", ""
    lines = [l.rstrip() for l in raw.replace("\x0c", "\n").replace("​", "").split("\n")]
    joined = "\n".join(lines)
    dm = re.search(rf"^Date:\s*\n+\s*((?:{MONTHS}) \d+, \d{{4}})", joined, re.M)
    if not dm:
        return "", "", ""
    head = re.split(r"\nAuthor:", joined[:dm.start()])[0]
    ver = re.search(r"\(((?:[^()@]|\([^()@]*\))+)\)\s*$", text(head))
    body = [l for l in joined[dm.end():].split("\n") if not re.match(
        r"\s*(Page \d+( of \d+)?|h?t?tps?://\S+|Senate Counsel, Research,? and Fiscal Analysis|Minnesota Senate Building.*|\(?651\)?[-/ ]\d{3}-\d{4})\s*$", l)]
    paras = paragraphs(body)
    return cap(paras), ver.group(1) if ver else "", long_date(dm.group(1))


def summaries(session):
    """Bill number -> [(ISO date, text, label)] from House Research and the Senate's summaries."""
    key = ("summ", session)
    if key in _CACHE:
        return _CACHE[key]
    out = defaultdict(list)
    f = folder(session)
    vocab = set()
    for sub in ("house", "senate"):
        d = os.path.join(f, "summaries", sub)
        for name in os.listdir(d) if os.path.isdir(d) else []:
            try:
                vocab |= set(w.lower() for w in re.findall(r"[A-Za-z]+", open(os.path.join(d, name), encoding="utf-8", errors="replace").read()))
            except OSError:
                pass
    for k, v in (jload(os.path.join(f, "hrd.json"), {}) or {}).items():
        try:
            raw = open(os.path.join(f, "summaries", "house", f"{k}.txt"), encoding="utf-8", errors="replace").read()
        except OSError:
            continue
        body, ver, when = hrd_text(raw)
        body = ligatures(body, vocab)
        n = text(v.get("bill")).replace(" ", "")
        if body and n:
            ver = ver.lower() if ver and re.fullmatch(r"[A-Za-z ]+", ver) else ver
            out[n].append((when, body, f"From the House Research Department's summary of {official(n).replace('HF', 'H.F.').replace('SF', 'S.F.')}"
                           f"{(' (' + ver + ')') if ver else ''}{(', ' + fmt(when)) if when else ''}."))
    for k, v in (jload(os.path.join(f, "senate_summaries.json"), {}) or {}).items():
        try:
            raw = open(os.path.join(f, "summaries", "senate", f"{k}.txt"), encoding="utf-8", errors="replace").read()
        except OSError:
            continue
        body, ver, when = senate_text(raw)
        body = ligatures(body, vocab)
        n = f"{text(v.get('bill_type')).replace('.', '')}{text(v.get('bill_number'))}"
        if body and re.fullmatch(r"[HS]F\d+", n):
            out[n].append((when, body, f"From the Senate Counsel, Research and Fiscal Analysis office's summary of "
                                       f"{n[:1]}.F. {n[2:]}{(' (' + ver + ')') if ver else ''}{(', ' + fmt(when)) if when else ''}."))
    _CACHE[key] = out
    return out


def fmt(iso):
    d = date.fromisoformat(iso)
    return f"{d.strftime('%B')} {d.day}, {d.year}"


# ---- titles and topics ---------------------------------------------------------------------------------------------

def title_of(desc):
    """The Revisor's description, shortened to its first clause when long: "Paid family, bonding, and applicant's serious
    medical condition benefits provided; employment leaves regulated ..." -> "Paid family, bonding, and applicant's
    serious medical condition benefits provided"."""
    t = text(desc).rstrip(".")
    if len(t) > 110 and ";" in t:
        t = t.split(";")[0]
    if len(t) > 140:
        cut = t[:140].rsplit(",", 1)[0] if "," in t[:140] else ""
        t = cut if len(cut) > 60 else t[:137].rsplit(" ", 1)[0].rstrip(",;") + "…"
    return t[:1].upper() + t[1:]


AMEND = re.compile(r"constitutional amendment", re.I)


def is_amendment(desc):
    return bool(AMEND.search(desc or ""))


def is_resolution(r):
    return text(r.get("LAW_TYPE")) == "Resolution" or re.match(r"\s*A resolution\b", r.get("DESCRIPTION") or "", re.I)


_PLACES = []


def place_names():
    """Minnesota's cities and counties ("Duluth", "Olmsted County"), from the towns file."""
    if not _PLACES:
        names = set()
        for row in jload(P.TOWNS_PATH, []) or []:
            n = re.sub(r" city$", "", row[0])
            names.add(n)
        _PLACES.append(names)
    return _PLACES[0]


def narrow_of(descs):
    """"place" for a bill about one city or county: the House's "Duluth; community health and wellness center funding
    provided ..." form, or the Senate's "Lakeville water treatment ... bond issue and appropriation"."""
    for d in descs:
        m = re.match(r"([A-Z][\w.' -]+?);", d or "")
        if m and m.group(1) in place_names():
            return "place"
        m = re.match(r"(?:City of |Town of )?([A-Z][\w.'-]+(?: [A-Z][\w.'-]+){0,2})", d or "")
        if m and re.search(r"\bbond|local sales|special law|tax increment|liquor license|appropriation\b", d or "", re.I):
            for k in range(3, 0, -1):
                cand = " ".join(m.group(1).split()[:k])
                if cand in place_names() and not re.match(r"(Minnesota|State)\b", cand):
                    return "place"
    return P.narrow_kind(descs[0] if descs else "")


# ---- records ------------------------------------------------------------------------------------------------------------

def groups(session):
    """Companions as one group: [[lead candidates...]]: mutual companions together, everything else alone."""
    B = bills(session)
    seen, out = set(), []
    for n in sorted(B, key=lambda x: (x[0] != "H", int(x[2:]))):
        if n in seen:
            continue
        r = B[n]
        c = f"{text(r.get('COMPANION_TYPE'))}{text(r.get('COMPANION_NUMBER'))}"
        g = [n]
        if c in B and c not in seen and f"{text(B[c].get('COMPANION_TYPE'))}{text(B[c].get('COMPANION_NUMBER'))}" == n:
            g.append(c)
        seen.update(g)
        out.append(g)
    return out


def specials(session):
    """The Legislature's special sessions' folders: ["2025-s1"]."""
    out = []
    for f in sorted(os.listdir(P.DATA)) if os.path.isdir(P.DATA) else []:
        m = re.fullmatch(r"(\d{4})-s(\d+)", f)
        if m and session <= int(m.group(1)) < session + P.YEARS and os.path.isdir(os.path.join(P.DATA, f, "bills")):
            out.append(f)
    return out


ORD = {1: "1st", 2: "2nd", 3: "3rd"}


def special_num(fold, n):
    """A special session's number on the page: "HF2" of the 2025 First Special Session -> "HFS2" (the house's letter
    first, as the page needs; a second special session's would be "HFT2")."""
    k = int(fold.split("-s")[1])
    return f"{n[:2]}{chr(ord('S') + k - 1)}{n[2:]}"


def special_label(fold):
    y, k = fold.split("-s")
    return f"{y} {ORD.get(int(k), f'{k}th')} Special Session"


def load_session(session):
    """Read one Legislature's bills: (records, bill number -> record index, fetched time, delegation)."""
    if session in _LOADED:
        return _LOADED[session]
    recs, index, texts = [], {}, {}
    parties = _PARTIES.setdefault(session, {})
    descs_of = []  # each record's (folder, descriptions, first day)
    for fold, g in [(session, g) for g in groups(session)] + [(sp, g) for sp in specials(session) for g in groups(sp)]:
        B = bills(fold)
        summ = summaries(fold)
        sp = fold != session
        if any(is_resolution(B[n]) for n in g):
            continue
        vsteps = {n: merge_passes(steps_of(session, n, B[n])) for n in g}
        alone = {n: work_out(vsteps[n], n[0]) for n in g}
        rank = lambda st: (st >= 3, st)
        order = sorted(g, key=lambda n: (-rank(alone[n]["stage"])[0], -alone[n]["stage"], alone[n]["replaced"], -len(vsteps[n]), n[0] != "H"))
        lead = order[0]
        w = alone[lead]
        origin = lead[0]
        descs = [text(B[n].get("DESCRIPTION")) for n in sorted(g, key=lambda n: n[0] != "H")]
        amendment = any(is_amendment(d) for d in descs)
        stage = w["stage"]
        if amendment and stage > 3:
            stage = 3
        steps = sorted([s for n in order for s in vsteps[n]], key=lambda s: s["d"])
        refs = [(s["h"], s["comm"]) for n in order for s in vsteps[n] if s["k"] == "ref" and s["h"] in HOUSE]
        title = title_of(descs[0])
        if amendment and not title.lower().startswith("constitutional amendment"):
            title = f"Constitutional amendment: {title[:1].lower() + title[1:]}"
        topics = list(dict.fromkeys((["const"] if amendment else []) +
                                    [P.COMMITTEE_TOPICS[c] for _, c in refs if c in P.COMMITTEE_TOPICS] +
                                    [k for k, rx in P.TOPIC_WORDS.items() if rx.search(" ".join(descs))]))
        # The first committee in the lead's own house, and whether the bill got out of it.
        lsteps = vsteps[lead]
        first = next(((s["h"], s["comm"], i) for i, s in enumerate(lsteps) if s["k"] == "ref" and s["h"] == origin), None)
        if first:
            left = any(s["k"] in ("report", "pass", "floor") for s in lsteps[first[2] + 1:]) or stage >= 2
            fate = "passed" if left else "none"
        else:
            left, fate = stage >= 2, "passed" if stage >= 2 else "none"

        vers = []
        for n in order:
            r = B[n]
            a = alone[n]
            authors = (r.get("AUTHORS") or {}).get("HOUSE" if n[0] == "H" else "SENATE") or []
            names, district = [], 0
            for i, x in enumerate(authors):
                seat, nm, party = resolve(session, n[0], text(x.get("MEMBER_NAME")))
                if nm and nm not in names:
                    names.append(nm)
                    if party:
                        parties[(n[0], nm)] = party
                    if i == 0 and seat:
                        district = int(seat[2:])
            vs = a["stage"]
            if amendment and vs > 3:
                vs = 3
            if a["replaced"] and vs < 3:
                desc = f"Replaced by {' / '.join(official(x) for x in order if x != n)}"
            elif a["withdrawn"] and vs < 2:
                desc = "Withdrawn by its author"
            elif vs == 0:
                desc = f"In {HOUSE[a['now']]} committee"
            elif vs == 1:
                desc = f"On the {HOUSE[a['now']]} floor"
            else:
                desc = {2: f"Passed the {HOUSE[n[0]] if n[0] in a['passed'] else HOUSE[OTHER[n[0]]]}",
                        3: "Passed both houses", 4: "On the governor's desk", 5: "Became law", 6: "Vetoed"}[vs]
            y = intro_year(fold, n)
            vers.append({"p": n, "sponsor": names[0] if names else "—", "district": district,
                         "cosponsors": names[1:], "primes": 1, "cosp": max(0, len(names) - 1), "statusDesc": desc,
                         "committee": a["comm"] if a["place"] == "committee" and vs in (0, 2) and not a["replaced"] else None,
                         "actions": [],
                         "link": f"https://www.revisor.mn.gov/bills/{P.legislature(session)}/{y}/{fold.split('-s')[1] if sp else 0}/{n[:2]}/{n[2:]}/"})
            # The vote count on a passage, as its own line (as other states show it).
            acts = []
            for s in vsteps[n]:
                if not s["t"] or not s["d"]:
                    continue
                acts.append([s["d"], s["t"]])
                if s["k"] == "pass" and s.get("tally"):
                    acts.append([s["d"], f"The {HOUSE[s['h']]} vote: {s['tally'][0]}-{s['tally'][1]}"])
                if s["k"] == "report" and s.get("how"):
                    acts.append([s["d"], f"The {HOUSE[s['h']]} committee {s['how']}"])
            vers[-1]["actions"] = acts

        # Members' votes: each passage of each number with its roll call.
        votes = []
        for n in order:
            for s in vsteps[n]:
                if s["k"] == "pass" and s["h"] in HOUSE and s["d"]:
                    v = floor_vote(session, s["h"], n, s["d"], s.get("tally"), fold)
                    if v:
                        votes.append(v)
        votes.sort(key=lambda v: v[3])

        def dates(test, mode="last", ss=None):
            ds = sorted({s["d"] for s in (ss or steps) if test(s) and s["d"]})
            return {"first": ds[0], "last": ds[-1], "all": ";".join(ds)}[mode] if ds else ""

        passed = w["passed"]
        if stage >= 3:
            passed = {"H", "S"}
        action_dates = [s["d"] for s in steps if s["d"]]
        chapter = int(w["chapter"]) if stage == 5 and str(w.get("chapter") or "").isdigit() else None
        if stage == 5 and not chapter:
            ch = text(B[lead].get("LAW_NUMBER"))
            chapter = int(ch) if ch.isdigit() and text(B[lead].get("LAW_TYPE")) == "Chapter" else None
        # "What it does": the newest summary of either number.
        cands = sorted((x for n in order for x in summ.get(n, [])
                        # (a special session's folder also lists the regular session's summaries of the same numbers)
                        if not sp or x[0] >= min(action_dates, default="")), key=lambda x: x[0], reverse=True)
        if cands:
            lab = cands[0][2]
            if sp and "special session" not in lab.lower():
                lab = re.sub(r"(of [HS]\.F\. \d+)", rf"\1 of the {special_label(fold)}", lab, count=1)
            texts[special_num(fold, lead) if sp else lead] = {"statement": cands[0][1], "label": lab}
            STATS[session]["records with a summary"] += 1
        budget = any(re.search(r"\bomnibus\b.*\b(appropriation|finance|budget)|\b(appropriation|finance|budget) bill\b|^Omnibus", d, re.I) for d in descs) and \
            not any(re.search(r"^[A-Z][\w.' -]+?;", d) and narrow_of([d]) == "place" for d in descs)
        rec = {
            "nums": order, "base": order, "prev": set(),
            "title": title, "summary": descs[0] if len(descs[0]) > len(title) + 2 else "",
            "act": "", "lawCode": "", "law": None, "laws": [],
            "comms": sorted({f"{h} · {c}" for h, c in refs}), "topics": topics, "places": [], "narrow": narrow_of(descs),
            "commFate": fate, "mainTopic": topics[0] if topics else "", "local": "local" in topics,
            "senDeleg": False, "asmDeleg": False, "budget": budget, "shell": False,
            "passedS": "S" in passed, "passedA": "H" in passed, "program": None,
            "stage": stage,
            "passedIn": (HOUSE[next(iter(passed))] if len(passed) == 1 else HOUSE[origin]) if stage == 2 else None,
            "chapter": chapter, "veto": None, "memo": "", "vetoMemo": None,
            "simText": " ".join([title] + descs + ([cands[0][1][:600]] if cands else [])),
            "comm": w["comm"] if stage == 0 and w["place"] == "committee" else None,
            "first": min(action_dates, default=f"{session}-01-01"),
            "last": max(action_dates, default=f"{session}-01-01"),
            "cosp": max(v["cosp"] for v in vers),
            "keyDates": [
                dates(lambda s: s["k"] == "floor", "first", lsteps),
                dates(lambda s: s["k"] == "pass" and s["h"] == "S", "all", lsteps if stage < 3 else None),
                dates(lambda s: s["k"] == "pass" and s["h"] == "H", "all", lsteps if stage < 3 else None),
                "",
                dates(lambda s: s["k"] == "sent", "last", lsteps) if stage >= 4 and not amendment else "",
                dates(lambda s: s["k"] == "signed", "last", lsteps) if stage == 5 else "",
                dates(lambda s: s["k"] == "veto", "last", lsteps) if stage == 6 else "",
            ],
            "votes": votes,
            "firstComms": [(first[0], first[1], left)] if first else [],
            "vers": vers,
        }
        if amendment:
            rec["amendment"] = True
        if sp:
            # A special session's bill: numbered "HFS2", titled with its session, its chapter one of that session's.
            ren = lambda t: re.sub(r"\b([HS]F) ?(\d+)\b", lambda m: special_num(fold, m.group(1) + m.group(2)), t)
            label = special_label(fold)
            num = int(w["chapter"]) if stage == 5 and str(w.get("chapter") or "").isdigit() else None
            rec["nums"] = rec["base"] = [special_num(fold, n) for n in order]
            rec["title"] = f"{rec['title']} ({label})"
            rec["chapter"] = None
            for v in rec["vers"]:
                v["p"] = special_num(fold, v["p"])
                v["statusDesc"] = ren(v["statusDesc"])
                v["actions"] = [[d, f"{label} chapter {num}" if re.fullmatch(r"CHAPTER \d+", t) and num else ren(t)] for d, t in v["actions"]]
            rec["special"] = {"label": label, "chapter": num, "law": stage == 5, "fold": fold, "raw": list(order),
                              "day": rec["keyDates"][5] or rec["last"]}
            g = [special_num(fold, n) for n in g]
        descs_of.append((fold, {_key(d) for d in descs}, rec["first"]))
        for n in g:
            index[n] = len(recs)
        recs.append(rec)
    link_specials(session, recs, descs_of)
    link_earlier(session, recs)
    json.dump(texts, open(os.path.join(P.DATA, f"texts_{session}.json"), "w"), ensure_ascii=False)
    path = os.path.join(folder(session), "list.json")
    fetched = datetime.fromtimestamp(os.path.getmtime(path), ZoneInfo(P.TIMEZONE)).strftime("%Y-%m-%d %H:%M") if os.path.exists(path) else ""
    _LOADED[session] = (recs, index, fetched, {"SENATE": [], "ASSEMBLY": []})
    return _LOADED[session]


# ---- earlier Legislatures -----------------------------------------------------------------------------------------------

def _key(desc):
    return re.sub(r"[^a-z0-9 ]", "", text(desc).lower()).strip()


def _keys(session):
    """A Legislature's bills that didn't become law: description -> [(number, chief author)]."""
    key = ("keys", session)
    if key not in _CACHE:
        out = defaultdict(list)
        for n, r in bills(session).items():
            if is_resolution(r) or (text(r.get("LAW_NUMBER")) and not any(
                    re.search(r"veto", text(a.get("ACTION_TEXT")), re.I) for acts in (r.get("ACTIONS") or {}).values() for a in acts)):
                continue
            au = ((r.get("AUTHORS") or {}).get("HOUSE" if n[0] == "H" else "SENATE") or [{}])[0]
            out[_key(r.get("DESCRIPTION"))].append((n, n[0], text(au.get("MEMBER_NAME"))))
        _CACHE[key] = out
    return _CACHE[key]


def rec_num(rec):
    n = rec["nums"][0]
    return f"{n[:2]} {n[3:]}"


# Regular-session omnibus bills for the same budget area whose descriptions differ from the special session's bill's
# (the rest are matched by description). Several 2025 omnibus numbers carried different 2026 laws (HF 2433, SF 2077,
# HF 2484): their records stay laws, with the 2025 version's fate as a history line.
SPECIAL_LINKS = {"2025-s1": {"HF2": ["HF2436"], "HF5": ["HF2433"], "SF3": ["SF2077"], "HF18": ["HF2484"]}}


def link_specials(session, recs, descs_of):
    """A regular-session bill whose content passed in a special session instead (the 2025 omnibus budget bills): the
    special session's bill with the same description (either house's number), introduced before it, not a law itself,
    gets a history line naming it ("Passed instead in the 2025 First Special Session as HF 2 (1st Special Session chapter
    3)"). It stays where it died (or, for a number used again for a 2026 law, a law)."""
    STATS[session]["regular bills linked to a special-session law"] = 0
    for i, r in enumerate(recs):
        sp = r.get("special")
        if not sp or not sp["law"]:
            continue
        keys = descs_of[i][1]
        extra = {n for raw in sp["raw"] for n in SPECIAL_LINKS.get(sp["fold"], {}).get(raw, [])}
        for j, o in enumerate(recs):
            if o.get("special") or descs_of[j][0] != session or o["first"] > sp["day"]:
                continue
            if not (descs_of[j][1] & keys or extra & set(o["nums"])):
                continue
            if o["stage"] == 5 and o["keyDates"][5] <= sp["day"]:
                continue  # a law of its own before the special session
            if o["stage"] == 5:
                STATS[session]["of them, numbers used again for a 2026 law"] += 1
            k, y = sp["label"].split(" ", 1)[1].split()[0], sp["label"].split()[0]
            line = f"Passed instead in the {y} {'First' if k == '1st' else k} Special Session as {rec_num(r)} ({k} Special Session chapter {sp['chapter']})"
            acts = o["vers"][0]["actions"]
            pos = next((x for x, (d, _) in enumerate(acts) if d > sp["day"]), len(acts))
            acts.insert(pos, [sp["day"], line])
            o["last"] = max(o["last"], sp["day"])
            o.setdefault("laterSpecial", []).append(r["nums"][0])
            STATS[session]["regular bills linked to a special-session law"] += 1


def link_earlier(session, recs):
    """The same bill in the Legislature before: the same description from the same chief author in the same house, or a
    description only one bill has in each (at least five words). Never laws or budget bills."""
    y = session - 2
    if y not in sessions():
        return
    old, mine = _keys(y), _keys(session)
    for r in recs:
        if r["budget"]:
            continue
        for v in r["vers"]:
            if v["p"] not in bills(session):
                continue  # a special session's bill
            k = _key(bills(session)[v["p"]].get("DESCRIPTION"))
            if len(k.split()) < 4:
                continue
            au = ((bills(session)[v["p"]].get("AUTHORS") or {}).get("HOUSE" if v["p"][0] == "H" else "SENATE") or [{}])[0]
            same = [n for n, h, a in old.get(k, []) if h == v["p"][0] and a and a == text(au.get("MEMBER_NAME"))]
            if same:
                r["prev"].add((y, same[0]))
            elif len(old.get(k, [])) == 1 and len(mine.get(k, [])) == 1 and len(k.split()) >= 5:
                r["prev"].add((y, old[k][0][0]))


def parties(session, recs):
    if session not in _PARTIES:
        load_session(session)
    return {k: v for k, v in _PARTIES.get(session, {}).items() if v in ("D", "R")}


def report(session):
    """Totals to compare with the official ones: laws and vetoes by year, chapters, votes matched."""
    recs = load_session(session)[0]
    B = bills(session)
    by_year = defaultdict(list)
    for r in recs:
        if r.get("special"):
            if r["stage"] == 5:
                by_year[r["special"]["label"]].append((5, r["special"]["chapter"], " / ".join(r["nums"])))
            continue
        if r["stage"] in (5, 6):
            y = (r["keyDates"][5] or r["keyDates"][6] or "????")[:4]
            ch = text(B[r["nums"][0]].get("LAW_NUMBER"))
            by_year[y].append((r["stage"], int(ch) if ch.isdigit() else None, " / ".join(r["nums"])))
    print(f"== {session}-{str(session + 1)[2:]}: {len(recs)} records")
    for y, xs in sorted(by_year.items()):
        laws = sorted(c for s, c, _ in xs if s == 5 and c)
        vetoes = [(c, n) for s, c, n in xs if s == 6]
        chs = sorted(c for _, c, _ in xs if c)
        gaps = sorted(set(range(chs[0], chs[-1] + 1)) - set(chs)) if chs else []
        print(f"  {y}: {len(laws)} laws, {len(vetoes)} vetoes {vetoes}; chapters {chs[0] if chs else '-'}-{chs[-1] if chs else '-'}, missing {gaps}")
    st = Counter(r["stage"] for r in recs)
    print("  stages", dict(sorted(st.items())), "amendments", sum(1 for r in recs if "const" in r["topics"]),
          "passed both (amendments)", sum(1 for r in recs if "const" in r["topics"] and r["stage"] >= 3))
    for k, v in sorted(STATS[session].items()):
        print(f"  {k}: {v}")


if __name__ == "__main__":
    for s in sessions():
        report(s)
