"""North Dakota's bills (downloaded by states/nd/fetch.py from the Legislative Council's static JSON API) in the shape
build_data.py reads. House and Senate bills of each two-year Legislative Assembly (special sessions' too: their numbers
follow the regular session's, HB 1621 on, in the same files), plus the concurrent resolutions that propose amendments to
the Constitution of North Dakota; other resolutions (requests, memorials, studies) are left out.

Each action has a date, its house and a category, with plain wording: "Introduced, first reading, referred Judiciary
Committee"; "Reported back amended, do pass, amendment placed on calendar 13 0 1" (the committee's tally: yes, no,
absent); every committee report goes to the floor, "do not pass" too, so every bill gets a floor vote unless it's
withdrawn; "Rereferred to Appropriations" (bills that spend money, after the policy committee); "Request return from
committee" (the house takes it back, to the floor or another committee); "Second reading, passed, yeas 84 nays 9" (the
final vote, called second reading here; resolutions are "adopted"); "Second reading, failed to pass" ends the bill unless
"Reconsidered"; "Returned to House (12)" sends it back with the other house's amendments (a plain "Returned to House"
means the second house passed it unchanged); the first house then "Concurred" and passes it again, or "Refused to concur"
and a conference committee's report has to be adopted, and the bill passed again, by both houses; "Signed by President",
"Signed by Speaker", "Sent to Governor", "Signed by Governor 04/28" (the governor's own date), "Signed by Governor, but item
veto", "Vetoed by Governor 04/13", "Passed over veto, yeas 90 nays 0" (each house), "Veto sustained", "Filed with Secretary
Of State 04/20" (laws, and vetoed bills with the governor's objections). Committee hearings are each bill's Hearings (with
the committee's name); the actions' "Committee Hearing 09:00" lines are left out. Floor roll calls come member by member
(roll_call.json); committees' votes are only tallies (the members' votes are in the minutes, PDFs).

Laws are numbered as chapters of the Session Laws (chapters.json, from the bill index published after the session;
vetoed measures get chapter numbers too, "Measure Vetoed", so the history decides laws and vetoes). No plain-language
summary exists in the data: see load_session().
"""
import json, os, re
from datetime import date, datetime
from zoneinfo import ZoneInfo

from states.nd import profile as P

HOUSE = {"S": "Senate", "H": "House"}
CHAMBER = {"House": "H", "Senate": "S"}
_PARTIES, _CACHE = {}, {}


def folder(session):
    return os.path.join(P.DATA, str(session))


def sessions():
    out = []
    for f in sorted(os.listdir(P.DATA)) if os.path.isdir(P.DATA) else []:
        if re.fullmatch(r"\d{4}", f) and os.path.exists(os.path.join(P.DATA, f, "bills.json")):
            out.append(int(f))
    return out


def load(session, name):
    """One of an assembly's files: bills.json -> {"1012": bill}, roll_call.json -> [roll call], members.json ->
    [member], committees.json -> [committee], chapters.json, leaders.json."""
    key = (session, name)
    if key not in _CACHE:
        try:
            data = json.load(open(os.path.join(folder(session), f"{name}.json")))
        except (OSError, ValueError):
            data = None
        if isinstance(data, dict) and name in data:
            data = data[name]
        _CACHE[key] = data if data is not None else ({} if name in ("bills", "chapters") else [])
    return _CACHE[key]


def text(x):
    """Plain spacing; the API writes section numbers with non-breaking hyphens ("50‑06‑06.6") and spaces."""
    return re.sub(r"\s+", " ", (x or "").replace("‑", "-").replace(" ", " ")).strip()


def is_amendment(b):
    kind = (b.get("name") or "").split(" ")[0]
    return kind in ("HCR", "SCR") and bool(re.search(r"\bof the Constitution of North Dakota\b|\bto the Constitution of North Dakota\b",
                                                     text(b.get("title")), re.I))


def number(b):
    """"HB 1012" -> "HB1012"; "HCR 3003" -> "HCR3003"; other kinds -> None."""
    m = re.fullmatch(r"(HB|SB|HCR|SCR) (\d+)", text(b.get("name")))
    return f"{m.group(1)}{int(m.group(2))}" if m else None


def official(p):
    """"HB1012" -> "HB 1012", as the Legislature writes it."""
    m = re.fullmatch(r"([A-Z]+)(\d+)", p)
    return f"{m.group(1)} {m.group(2)}" if m else p


def body(title):
    """The official title without its opening: "A BILL for an Act to ..." / "AN ACT to ..." / "A concurrent resolution
    to ..." -> "to ..." (no closing period)."""
    t = text(title)
    t = re.sub(r"^(?:A BILL for an Act|AN ACT|A concurrent resolution)\s*,?\s*", "", t, flags=re.I)
    return t.rstrip(". ")


def relating(title):
    """The title's subjects: each "relating to ..." clause, up to its semicolon ("the veterans' aid fund")."""
    return [m.group(1).strip(" ,") for m in re.finditer(r"\brelating to (.+?)(?=;|$)", body(title))]


def cap(s):
    return s[:1].upper() + s[1:]


def titled(b, amendment=False):
    """A short title from the official one, which has none: the first subject ("Relating to the veterans' aid fund" ->
    "The veterans' aid fund"); an agency's budget ("to provide an appropriation for defraying the expenses of the
    department of health and human services" -> "Budget: department of health and human services"); else the first
    clause ("to provide an appropriation to the department of public instruction for ..." -> "Appropriation to the ...")."""
    t = body(b.get("title"))
    rel = relating(b.get("title"))
    m = re.match(r"to provide (?:an )?appropriations? for defraying the expenses of (?:the )?(?:various divisions of (?:the )?)?(.+?)(?=[;,]|$)", t, re.I)
    if m and not amendment:
        return f"Budget: {m.group(1)}"
    if re.match(r"to provide (?:an )?appropriations?\b", t, re.I) and not amendment:
        first = re.split(r";", t)[0]
        return cap(re.sub(r"^to provide (?:an )?", "", first, flags=re.I))
    if rel:
        lead = re.split(r";", t)[0]
        s = rel[0]
        if re.match(r"to provide for a legislative management study", lead, re.I):
            s = f"study of {s}"
        out = cap(s)
    else:
        first = re.split(r";", t)[0]
        first = re.sub(r"^to (?:amend and reenact|create and enact|repeal) .*? of the (?:North Dakota Century Code|Constitution of North Dakota),?\s*(?:which\s+)?", "", first, flags=re.I) or first
        first = re.sub(r"^to provide for a legislative management study (?:of|on|regarding|relating to)\s+", "study: ", first, flags=re.I)
        first = re.sub(r"^to provide for a legislative management study to\s+", "study to ", first, flags=re.I)
        out = cap(re.sub(r"^to ", "", first))
    if amendment:
        out = f"Constitutional amendment: {out[:1].lower() + out[1:]}"
    if len(out) > 180:
        cut = out[:180].rsplit(",", 1)[0] if "," in out[:180] else out[:180].rsplit(" ", 1)[0]
        out = cut + " …"
    return out


def sim_text(b):
    """The title's clauses without the section numbers, for matching similar bills."""
    t = body(b.get("title"))
    t = re.sub(r"\b(?:sections?|subsections?|subdivisions?|chapters?|titles?|articles?)\s+[\d.\-a-z]+(?:,?\s*(?:and\s+)?[\d.\-]+)*", " ", t, flags=re.I)
    t = re.sub(r"of the North Dakota Century Code|\bto (?:create and enact|amend and reenact|repeal)\b|\bnew\b", " ", t, flags=re.I)
    return text(t)


def tally(t):
    """"... yeas 84 nays 9" -> (84, 9)."""
    m = re.search(r"yeas (\d+) nays (\d+)", t)
    return (int(m.group(1)), int(m.group(2))) if m else None


def comm_tally(t):
    """A committee report's trailing tally: "... place on calendar 13 0 1" -> (13, 0, 1)."""
    m = re.search(r"(\d+) (\d+) (\d+)\s*$", t)
    return tuple(int(x) for x in m.groups()) if m else None


def text_date(t, d):
    """The governor's and the Secretary of State's lines carry their own date ("Signed by Governor 04/28", entered
    04/29): the year is the action's (a day after it moves to the year before)."""
    m = re.search(r"\b(\d{1,2})/(\d{1,2})\s*$", t)
    if not m or not d:
        return d
    try:
        x = date(int(d[:4]), int(m.group(1)), int(m.group(2)))
    except ValueError:
        return d
    if x.isoformat() > d:
        x = x.replace(year=x.year - 1)
    return x.isoformat() if (date.fromisoformat(d) - x).days < 120 else d


def person(name):
    """"Jonas, Jim" / "Rep. Pyle, Brandy L." -> "Jim Jonas" / "Brandy L. Pyle"."""
    n = re.sub(r"^(?:Rep|Sen)\.\s+", "", text(name))
    if "," in n:
        last, first = [x.strip() for x in n.split(",", 1)]
        m = re.match(r"(.*?)(?:,?\s+(Jr\.?|Sr\.?|II|III|IV))$", first)
        if m and m.group(1):
            return f"{m.group(1)} {last} {m.group(2)}"
        return f"{first} {last}".strip()
    return n


def last_name(name):
    return re.sub(r"^(?:Rep|Sen)\.\s+", "", text(name)).split(",")[0].strip()


def seats(session):
    """Member id -> seat id, for the assembly's members still serving: "S:12"; a district's two representatives
    "H:12a" and "H:12b" (by name; the subdistricts 4A and 4B, and 9A and 9B, each elect one: "H:4a", "H:4b"). Members
    who left have no seat (their votes are "H?Hoverson")."""
    out = {}
    ms = [m for m in load(session, "members") if m.get("active")]
    by = {}
    for m in ms:
        h = CHAMBER.get(m.get("chamber"))
        d = text(str(m.get("district") or ""))
        dm = re.fullmatch(r"(\d+)([AB]?)", d)
        if not h or not dm:
            continue
        if h == "S":
            out[m["id"]] = f"S:{int(dm.group(1))}"
        else:
            by.setdefault(int(dm.group(1)), []).append((dm.group(2), person(m["name"]), m["id"]))
    for d, xs in by.items():
        xs.sort()
        for i, (sub, _, mid) in enumerate(xs):
            out[mid] = f"H:{d}{sub.lower() if sub else 'abcdefg'[i]}"
    return out


PARTY = {"Republican": "R", "Democrat": "D", "Democratic": "D", "Democratic-NPL": "D"}


def committee_of(t):
    """"Introduced, first reading, (emergency), referred Industry, Business and Labor Committee" -> "Industry,
    Business and Labor"; "Rereferred to Appropriations" -> "Appropriations"."""
    m = re.search(r"(?:referred(?: to)?|, (?=[A-Z][A-Za-z ,]+ Committee$))\s*(.+?)(?: Committee)?\s*$", t)
    if not m:
        return None
    c = m.group(1).strip(" ,")
    return c if c and not re.match(r"(?:first reading|\(emergency\))", c) else None


def load_session(session):
    """Read one Legislative Assembly's bills and return (records, bill number -> record index, fetched time, delegation)."""
    bills = load(session, "bills")
    chapters = load(session, "chapters")
    rolls = {r.get("id"): r for r in load(session, "roll_call")}
    by_bill = {}
    for r in rolls.values():
        by_bill.setdefault(text(r.get("bill")), []).append(r)
    seat = seats(session)
    members = {m["id"]: m for m in load(session, "members")}
    parties = _PARTIES.setdefault(session, {})
    for m in members.values():
        h = CHAMBER.get(m.get("chamber"))
        if h and PARTY.get(m.get("party")):
            parties[(h, person(m["name"]))] = PARTY[m["party"]]
    path = os.path.join(folder(session), "bills.json")
    fetched = datetime.fromtimestamp(os.path.getmtime(path), ZoneInfo(P.TIMEZONE)).strftime("%Y-%m-%d %H:%M") if os.path.exists(path) else ""
    recs, index = [], {}
    order = lambda b: ({"HB": 0, "SB": 1, "HCR": 2, "SCR": 3}.get(text(b.get("name")).split(" ")[0], 9), int(b.get("number") or 0))
    for b in sorted(bills.values(), key=order):
        p = number(b)
        amendment = is_amendment(b)
        if not p or (p[1:3] == "CR" and not amendment):
            continue
        rec = record(session, b, p, amendment, chapters, rolls, by_bill, seat, members)
        index[p] = len(recs)
        recs.append(rec)
    # "What it does" is texts_<year>.json (build_data.py's bill_texts()), which fetch.py writes from the Legislative
    # Council's Title Summaries of the bills passed; other bills have only the official title (the summary).
    return recs, index, fetched, {"SENATE": [], "ASSEMBLY": []}


def record(session, b, p, amendment, chapters, rolls, by_bill, seat, members):
    name = text(b.get("name"))
    origin = p[0]
    other = "S" if origin == "H" else "H"
    steps = []  # (date, house or "G", wording, kind)
    passed, failed = set(), set()
    last_vote = {}  # house -> "pass" / "fail" / "concur": what a reconsideration undoes
    second_amended = False  # the second house changed it: the first has to concur and pass it again
    concurred, conf, after_conf, repassed = set(), {}, set(), False
    signed_by = set()
    sent = law = vetoed = withdrawn = filed = item = False
    override = set()
    where_h, place, comm, first_ref, first_report, dopass = origin, "committee", None, None, None, False
    refs = []  # (house, committee) in order
    acts = sorted((a for a in b.get("actions") or [] if a.get("category") != "Committee hearing"),
                  key=lambda a: (a.get("date") or "")[:10])  # by day; the file's order within a day
    vote_actions = []  # (date, house, action) for floor votes on the bill's own question
    for a in acts:
        t, cat = text(a.get("description")), a.get("category") or ""
        d = (a.get("date") or "")[:10]
        h = CHAMBER.get(a.get("chamber")) or ""
        H = HOUSE.get(h, "")
        if cat in ("Introduced", "Introduced (emergency)"):
            c = committee_of(t)
            where_h, place = h, "committee"
            if h == origin and not any(s[3] == "intro" for s in steps):
                steps.append((d, h, "Introduced" + (" with an emergency clause" if "emergency" in t else ""), "intro"))
            if c:
                comm = c
                refs.append((h, c))
                if first_ref is None and h == origin:
                    first_ref = c
                steps.append((d, h, f"REFERRED TO {c.upper()}", "ref"))
            else:
                place = "floor"
                steps.append((d, h, "Read the first time and placed on the calendar", "first"))
            continue
        if cat == "Rereferred":
            c = committee_of(t)
            if c:
                comm, place, where_h = c, "committee", h
                refs.append((h, c))
                steps.append((d, h, f"REFERRED TO {c.upper()}", "ref"))
            continue
        if cat == "Request return from committee":
            place = "floor"
            steps.append((d, h, f"The {H} took it back from the committee", "recall"))
            continue
        if cat == "Committee report":
            if re.match(r"Reported back from conference committee", t):
                m = re.search(r"\((House|Senate) (accede|recede|accept|reject)\)", t)
                steps.append((d, h, "The conference committee reported" + (f" (the {m.group(1)} to {m.group(2)})" if m else ""), "confrep"))
                continue
            if re.match(r"Conference committee report (adopted|rejected)", t):
                ok = "adopted" in t
                conf[h] = ok
                if not ok:
                    after_conf.discard(h)
                steps.append((d, h, f"The {H} {'adopted' if ok else 'rejected'} the conference committee's report", "conf"))
                continue
            tl = comm_tally(t)
            cname = comm or "the"
            if re.search(r"\bdo pass\b", t) and not re.search(r"do not pass", t):
                kind = "pass"
            elif re.search(r"do not pass", t):
                kind = "fail"
            elif re.search(r"without recommendation", t):
                kind = "none"
            else:
                kind = None
            if kind:
                if h == origin and first_report is None and refs and refs[0][0] == origin:
                    first_report = kind
                words = {"pass": "recommended it pass", "fail": "recommended it not pass", "none": "reported it without a recommendation"}[kind]
                if kind == "pass":
                    dopass = True
                    steps.append((d, h, "REPORTED", "reported"))
                steps.append((d, h, f"The {cname} Committee {words}" + (" with amendments" if "amended" in t else "")
                              + (f", {tl[0]}-{tl[1]}" if tl else "") + (" (consent calendar)" if "consent calendar" in t else ""), "report"))
            elif re.match(r"Divided committee report", t):
                steps.append((d, h, f"The {cname} Committee was divided (majority and minority reports)", "report"))
            elif re.match(r"Minority report adopted", t):
                steps.append((d, h, f"The {H} adopted the committee's minority report", "report"))
            else:
                steps.append((d, h, "Placed on the calendar", "report"))
            place, where_h = "floor", h
            continue
        if cat in ("Amendment adopted", "Amendment failed", "Amended on floor"):
            steps.append((d, h, {"Amendment adopted": "Amendments adopted", "Amendment failed": "An amendment failed",
                                 "Amended on floor": "An amendment was offered on the floor"}[cat], "amend"))
            continue
        if cat == "Placed on calendar":
            place, where_h = "floor", h
            steps.append((d, h, "Placed on the calendar", "report"))
            continue
        if cat == "Passed" and re.match(r"Passed over veto", t):
            override.add(h)
            tl = tally(t)
            steps.append((d, h, f"The {H} voted to override the veto" + (f", {tl[0]}-{tl[1]}" if tl else ""), "override"))
            vote_actions.append((d, h, a))
            continue
        if cat == "Passed" or (cat == "Failed" and re.match(r"Second reading", t)):
            ok = cat == "Passed"
            tl = tally(t)
            vote_actions.append((d, h, a))
            last_vote[h] = "pass" if ok else "fail"
            if not ok:
                failed.add(h)
                steps.append((d, h, f"Failed to pass the {H}" + (f", {tl[0]}-{tl[1]}" if tl else "")
                              + (" (it needed two-thirds)" if "two-thirds" in t else " (it needed a majority of all members)" if "onstitutional majority" in t else ""), "fail"))
                continue
            failed.discard(h)
            first_time = h not in passed
            passed.add(h)
            if h == other and first_time:
                second_amended = "as amended" in t
                place, where_h = "desk", origin
            elif h == origin and first_time:
                place, where_h = "committee", other
                comm = None
            else:
                # A house passing it again: the first house after agreeing to the other's amendments, or either house
                # after adopting a conference committee's report.
                if h in concurred:
                    repassed = True
                if conf.get(h):
                    after_conf.add(h)
            steps.append((d, h, f"PASSED {H.upper()}", "pass"))
            if tl:
                steps.append((d, h, f"The {H} vote: {tl[0]}-{tl[1]}" + (" (with the emergency clause)" if "Emergency clause carried" in t else ""), "tally"))
            continue
        if cat == "Reconsider":
            if re.match(r"Reconsidered", t):
                if re.search(r"concur", t, re.I):
                    concurred.discard(h)
                elif last_vote.get(h) == "pass":
                    passed.discard(h)
                    if h == other:
                        second_amended = False
                elif last_vote.get(h) == "fail":
                    failed.discard(h)
                last_vote.pop(h, None)
                steps.append((d, h, f"The {H} voted to reconsider", "reconsider"))
            else:
                steps.append((d, h, "A motion to reconsider failed", "reconsider"))
            continue
        if cat in ("Received from House", "Received from Senate"):
            where_h, place = h, "committee"
            steps.append((d, h, f"Received from the {HOUSE['H' if 'House' in cat else 'S']}", "received"))
            continue
        if cat in ("Returned to House", "Returned to Senate"):
            if re.search(r"\(\d+\)", t):
                second_amended = True
                steps.append((d, h, f"Sent back to the {H} with the {HOUSE[other if h == origin else origin]}'s amendments", "returned"))
            else:
                steps.append((d, h, f"RETURNED TO {H.upper()}", "returned"))
            place, where_h = "desk", h
            continue
        if cat == "Concurred":
            concurred.add(h)
            last_vote[h] = "concur"
            steps.append((d, h, f"The {H} agreed to the {HOUSE[other if h == origin else origin]}'s amendments", "concur"))
            continue
        if cat == "Not concurred":
            steps.append((d, h, f"The {H} refused to agree to the {HOUSE[other if h == origin else origin]}'s amendments", "noconcur"))
            continue
        if cat == "Conference committee":
            steps.append((d, h, re.sub(r"^Conference committee appointed\s*", "Conference committee appointed: ", t) if "appointed" in t else t, "confcomm"))
            continue
        if cat in ("President signed", "Speaker signed"):
            signed_by.add(cat)
            steps.append((d, h, "Signed by the President of the Senate" if cat == "President signed" else "Signed by the Speaker of the House", "signature"))
            continue
        if cat == "Delivered to Governor":
            sent = True
            steps.append((d, h, "DELIVERED TO GOVERNOR", "sent"))
            continue
        if cat in ("Governor signed", "Governor signed (Item veto)"):
            law = True
            item = item or "Item" in cat
            ch = (chapters.get(name) or {}).get("chapter")
            words = (f"SIGNED CHAPTER {int(ch)}" if ch and str(ch).isdigit() and not item else
                     "Signed by the governor, with item vetoes" + (f" (chapter {ch})" if ch else "") if item else "Signed by the governor")
            steps.append((text_date(t, d), "G", words, "signed"))
            continue
        if cat == "Vetoed by Governor":
            vetoed = True
            steps.append((text_date(t, d), "G", "VETOED", "vetoed"))
            continue
        if cat == "Consideration of Governor's veto":
            steps.append((d, h, f"The {H} took up the governor's veto", "vetoconsider"))
            continue
        if cat == "Veto sustained":
            tl = tally(t)
            vote_actions.append((d, h, a))
            steps.append((d, h, f"The {H} sustained the veto (the override failed" + (f", {tl[0]}-{tl[1]}" if tl else "") + ")", "sustained"))
            continue
        if cat == "Filed with Secretary of State":
            filed = True
            steps.append((text_date(t, d), "G", "Filed with the Secretary of State", "filed"))
            continue
        if cat == "Voided by judicial action":
            m = re.search(r"(\d{4} ND \d+)", t)
            steps.append((d, "G", "Declared void by the North Dakota Supreme Court" + (f" ({m.group(1)})" if m else ""), "void"))
            continue
        if cat == "Withdrawn":
            withdrawn = True
            steps.append((d, h, "Withdrawn from further consideration", "withdrawn"))
            continue
        if cat == "Laid over":
            steps.append((d, h, t, "laid"))
            continue
        if cat in ("Emergency clause carried", "Emergency clause failed"):
            steps.append((d, h, "The emergency clause " + ("was adopted (two-thirds)" if "carried" in cat else "failed (it needs two-thirds)"), "emergency"))
            continue
        if cat.startswith("Division"):
            m = re.match(r"Division ([A-Z]) (passed|adopted|lost)", t)
            if m and (a.get("roll_call") or {}).get("description") == "Final Passage":
                # A bill voted on in parts: when every part lost, it failed (SB 2384 of 2025 in the House).
                parts = [x for x in acts if x.get("category", "").startswith("Division *") and (x.get("date") or "")[:10] == d
                         and CHAMBER.get(x.get("chamber")) == h and (x.get("roll_call") or {}).get("description") == "Final Passage"]
                if parts and all(re.search(r"\blost\b", text(x.get("description"))) for x in parts) and x_last(parts, a) and \
                        not any(x.get("category") == "Passed" and (x.get("date") or "")[:10] >= d and CHAMBER.get(x.get("chamber")) == h for x in acts):
                    failed.add(h)
                    last_vote[h] = "fail"
            if m:
                steps.append((d, h, f"Part {m.group(1)} {'approved' if m.group(2) != 'lost' else 'rejected'} (a divided vote)", "division"))
            else:
                steps.append((d, h, "The question was divided into parts" if "bill" in t else "The amendment was divided into parts", "division"))
            continue
        steps.append((d, h or "G", t, "other"))
    # Hearings, from the bill's own list (the actions' "Committee Hearing 09:00" lines don't name the committee).
    for x in b.get("hearings") or []:
        cn = text((x.get("committee") or {}).get("name"))
        m = re.match(r"(House|Senate|Joint) (.+)$", cn)
        if x.get("type") == "Bill Hearing" and m and x.get("date") and not re.search(r"cancel", text(x.get("description")), re.I):
            hh = CHAMBER.get(m.group(1), origin)
            steps.append((x["date"][:10], hh, f"Hearing in the {m.group(1) + ' ' if m.group(1) == 'Joint' else ''}{re.sub(r' - .*', '', m.group(2))} Committee"
                          , "hearing"))
    steps.sort(key=lambda s: s[0])  # by day; the order within a day stays

    # Passed both houses: the second house passed it unchanged, or the first agreed to its amendments and passed it
    # again, or both adopted a conference committee's report and passed it again; the presiding officers sign only then.
    both = (origin in passed and other in passed and not second_amended) or repassed or \
        (conf.get("H") and conf.get("S") and after_conf >= {"H", "S"}) or len(signed_by) == 2 or sent
    overridden = override >= {"H", "S"}
    chapter = (chapters.get(name) or {})
    if amendment:
        stage = 3 if both else 2 if passed else None
    elif law or overridden or (filed and both and not vetoed):
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
        # A bill withdrawn (from its committee, or taken back from it to be withdrawn) never reached a vote.
        stage = 0 if withdrawn else 1 if (place == "floor" or failed & {origin}) else 0
    ch_no = chapter.get("chapter") if stage == 5 and chapter.get("veto") != "Measure Vetoed" else None
    if stage == 5 and overridden and not any(s[3] == "lawnote" for s in steps):
        steps.append((max(s[0] for s in steps), "G", "Became law over the governor's veto" + (f" (chapter {ch_no})" if ch_no else ""), "lawnote"))
    elif stage == 5 and not law and not overridden:
        steps.append((max(s[0] for s in steps), "G", "Became law without the governor's signature" + (f" (chapter {ch_no})" if ch_no else ""), "lawnote"))

    # Where it is now.
    comm_now = comm if place == "committee" and stage in (0, 2) and not withdrawn else None
    title = titled(b, amendment)
    long_title = text(b.get("title"))
    topics = list(dict.fromkeys((["const"] if amendment else []) +
                                [P.COMMITTEE_TOPICS[c] for _, c in refs if c in P.COMMITTEE_TOPICS] +
                                [k for k in P.TOPIC_WORDS if P.TOPIC_WORDS[k].search(title + " " + " ".join(relating(b.get("title"))))]))
    # A committee that recommended it pass, then the bill died: "passed"; every committee reports, so none are "held".
    fate = "held" if withdrawn and not passed else "passed" if dopass or passed else "defeated" if first_report == "fail" else "none"
    # Sponsors in order: members ("Jim Jonas"), or a committee ("House Appropriations Committee").
    names_ = []
    primes = 0
    for s in b.get("sponsors") or []:
        if s.get("type") == "committee":
            n = text(s.get("name"))
            n = n if n.endswith("Committee") else f"{n} Committee"
        else:
            n = person(s.get("name"))
        if n and n not in names_:
            names_.append(n)
            primes += bool(s.get("primary"))
    sponsor = names_[0] if names_ else "—"
    cos = names_[1:]
    where = HOUSE.get(where_h, HOUSE[origin])
    if stage == 0:
        desc = "Withdrawn" if withdrawn else f"In {where} committee"
    elif stage == 1:
        desc = f"Failed in the {HOUSE[origin]}" if origin in failed else f"On the {where} floor"
    else:
        desc = {2: f"Passed the {HOUSE[origin] if origin in passed else HOUSE[other]}" + (f"; failed in the {HOUSE[other]}" if other in failed else ""),
                3: "Passed both houses", 4: "On the governor's desk", 5: "Became law", 6: "Vetoed"}[stage]

    def dates(test, mode="last"):
        ds = sorted({s[0] for s in steps if test(s) and s[0]})
        return {"first": ds[0], "last": ds[-1], "all": ";".join(ds)}[mode] if ds else ""

    votes = floor_votes(b, name, vote_actions, rolls, by_bill, seat, members)
    action_dates = [s[0] for s in steps if s[0]]
    return {
        "nums": [p], "base": [p], "prev": earlier(session, b, p),
        "title": title, "summary": long_title, "act": "", "lawCode": "", "law": None, "laws": [],
        "comms": sorted({f"{h} · {c}" for h, c in refs}), "topics": topics, "places": [], "narrow": P.narrow_kind(title),
        "commFate": fate, "mainTopic": topics[0] if topics else "", "local": "local" in topics,
        "senDeleg": False, "asmDeleg": False,
        "budget": bool(re.match(r"to provide (?:an )?appropriations? for defraying the expenses", body(b.get("title")), re.I)),
        "passedS": "S" in passed, "passedA": "H" in passed, "program": None,
        "stage": stage, "passedIn": (HOUSE[origin] if origin in passed else HOUSE[other]) if stage == 2 else None,
        "chapter": int(ch_no) if ch_no and str(ch_no).isdigit() else None,
        "veto": None, "memo": "", "vetoMemo": None,
        "simText": f"{title} {sim_text(b)}",
        "comm": comm_now if stage == 0 else None,
        "first": min(action_dates, default=f"{session}-01-01"),
        "last": max(action_dates, default=f"{session}-01-01"),
        "cosp": len(cos),
        "keyDates": [
            dates(lambda s: s[3] == "reported", "first"),
            dates(lambda s: s[2] == "PASSED SENATE", "all"),
            dates(lambda s: s[2] == "PASSED HOUSE", "all"),
            "",
            dates(lambda s: s[3] == "sent") if stage >= 4 and not amendment else "",
            (dates(lambda s: s[3] in ("signed", "lawnote")) or dates(lambda s: s[3] == "filed")) if stage == 5 else "",
            dates(lambda s: s[3] == "vetoed"),
        ],
        "votes": votes, "firstComms": [(origin, first_ref, first_report == "pass" or bool(passed))] if first_ref else [],
        "vers": [{"p": p, "sponsor": sponsor, "district": 0, "cosponsors": cos, "primes": max(1, primes), "cosp": len(cos),
                  "statusDesc": desc, "committee": comm_now, "link": text(b.get("url")),
                  "actions": [[s[0], s[2]] for s in steps]}],
    }


def x_last(parts, a):
    return parts[-1] is a


def floor_votes(b, name, vote_actions, rolls, by_bill, seat, members):
    """The bill's own floor roll calls (passage, failure, veto override or sustained), member by member: "N" no, "A"
    absent. An action's roll call by id; a passage line without one is matched to an unlinked "Final Passage" roll call
    of the same bill, day and tally."""
    linked = {(a.get("roll_call") or {}).get("id") for bb in [b] for a in bb.get("actions") or [] if (a.get("roll_call") or {}).get("id")}
    spare = [r for r in by_bill.get(name, []) if r.get("id") not in linked and r.get("description") == "Final Passage" and not r.get("division")]
    out, used = [], set()
    for d, h, a in vote_actions:
        rid = (a.get("roll_call") or {}).get("id")
        r = rolls.get(rid) if rid else None
        if r is None:
            tl = tally(text(a.get("description")))
            r = next((x for x in spare if x["id"] not in used and (x.get("date") or "")[:10] == d and tl and
                      (x.get("total_yeas"), x.get("total_nays")) == tl and CHAMBER.get(x.get("chamber")) == h), None)
        if r is None or r["id"] in used:
            continue
        used.add(r["id"])
        listed = []
        for v in r.get("member_votes") or []:
            code = {"Nay": "N", "Absent": "A"}.get(v.get("vote"))
            if not code:
                continue
            sid = seat.get(v.get("member_id"))
            if not sid or sid[0] != h:
                sid = f"{h}?{last_name(v.get('name'))}"
            listed.append([sid, code])
        out.append([h, "F", None, (r.get("date") or d)[:10], int(r.get("total_yeas") or 0), int(r.get("total_nays") or 0), listed])
    out.sort(key=lambda v: v[3])
    return out


_KEYS = {}
_STOP = set("the a an of to and or for in on by with relating provide provides create enact amend reenact repeal section "
            "sections chapter north dakota century code new subsection subdivision legislative management study report "
            "effective date penalty appropriation act bill application exemption transfer".split())


def _words(b):
    return {w for w in re.findall(r"[a-z]{3,}", sim_text(b).lower()) if w not in _STOP}


def _prime(b):
    return next((person(s["name"]) for s in b.get("sponsors") or [] if s.get("primary") and s.get("type") != "committee"), "")


def _keys(session):
    """An assembly's bills that didn't become law: short title -> [(bill number, prime sponsor)], and prime sponsor ->
    [(bill number, title words)]."""
    if session not in _KEYS:
        out, by = {}, {}
        for b in load(session, "bills").values():
            p = number(b)
            if not p or (p[1:3] == "CR" and not is_amendment(b)) or re.match(r"Governor signed|Passed over veto", b.get("current_status") or ""):
                continue  # a law isn't tried again (yearly bills like the budgets share titles)
            out.setdefault(titled(b, is_amendment(b)).lower(), []).append((p, _prime(b)))
            if _prime(b):
                by.setdefault(_prime(b), []).append((p, _words(b)))
        _KEYS[session] = (out, by)
    return _KEYS[session]


def earlier(session, b, p):
    """The same bill in the assembly before: the same subject with the same prime sponsor, or a subject only one bill
    has in each, or the same prime sponsor with half the title's words in common. Never agency budgets or appropriations
    (each assembly has its own), nor a bill that became law."""
    out = set()
    k = titled(b, is_amendment(b)).lower()
    if len(k.split()) < 3 or re.match(r"budget:|appropriation", k):
        return out
    who = _prime(b)
    y = session - 2
    if y in sessions():
        titles, by = _keys(y)
        old = titles.get(k, [])
        same = [n for n, sp in old if sp and sp == who]
        if same:
            out.add((y, same[0]))
        elif len(old) == 1 and len(_keys(session)[0].get(k, [])) == 1:
            out.add((y, old[0][0]))
        elif who:
            w = _words(b)
            best = max(((len(w & ow) / max(1, len(w | ow)), n) for n, ow in by.get(who, [])), default=(0, None))
            if best[0] >= 0.5:
                out.add((y, best[1]))
    return out


def agendas(session):
    """Bills on upcoming committee hearings (each bill's Hearings): bill -> [["House Education", "2027-01-14T09:00:00"], ...]."""
    today = date.today().isoformat()
    out = {}
    for b in load(session, "bills").values():
        p = number(b)
        if not p:
            continue
        for x in b.get("hearings") or []:
            when = x.get("date") or ""
            cn = re.sub(r" - .*$", "", text((x.get("committee") or {}).get("name")))
            if when[:10] < today or not cn or re.search(r"cancel", text(x.get("description")), re.I):
                continue
            entry = [cn, when[:19]]
            if entry not in out.setdefault(p, []):
                out[p].append(entry)
    return out


def parties(session, recs):
    if session not in _PARTIES:
        load_session(session)
    return {k: v for k, v in _PARTIES.get(session, {}).items() if v in ("D", "R")}
