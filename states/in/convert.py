"""Indiana's bills (downloaded by states/in/fetch.py from the General Assembly's API) in the shape build_data.py reads.
House and Senate bills of each year's regular session, plus the joint resolutions that propose amendments to the Indiana
Constitution; other resolutions (and the "Vehicle joint resolution" placeholders) are left out.

Each action has a time (the presiding officers' signatures and the governor's actions only a date), the chamber where
it happened and plain-English wording: "First reading: referred to Committee on Public Health", "Committee report: amend
do pass, adopted" (the house adopting its committee's report), "Recommitted to Committee on Ways and Means pursuant to
House Rule 126.3" (a bill that costs money), "Second reading: amended, ordered engrossed", "Third reading: passed; Roll
Call 143: yeas 40, nays 9" (the passage), "Referred to the House", "Returned to the Senate with amendments" (then "Senate
concurred with House amendments; Roll Call ...", or a dissent and a conference committee report that both houses have to
adopt), "Returned to the Senate without amendments" (passed both houses), "Signed by the Speaker", "... President Pro
Tempore", "... President of the Senate" (then presented to the governor; the presentment itself isn't recorded), "Signed
by the Governor", "Bill Became Law on 8th Day Without Signature", "Vetoed by the Governor", "Public Law 126". Joint
resolutions also get Public Law numbers but go to the voters, not the governor. Committees don't vote bills down: a bill
the chair doesn't hear dies there. Votes are tallies only (the roll calls' member lists are PDFs the API doesn't serve).
"What it does" is the Legislative Services Agency's digest of the latest version.
"""
import glob, importlib, json, os, re
from datetime import datetime
from zoneinfo import ZoneInfo

P = importlib.import_module("states.in.profile")  # "in" is a Python keyword, so no import statement

HOUSE = {"S": "Senate", "H": "House"}
CURRENT = P.session_of(datetime.now(ZoneInfo(P.TIMEZONE)).year)
_PARTIES = {}


def folder(session):
    return os.path.join(P.DATA, str(session))


def sessions():
    return sorted(int(os.path.basename(f)) for f in glob.glob(os.path.join(P.DATA, "[0-9]" * 4))
                  if len(glob.glob(os.path.join(f, "bills", "*.json"))) > 100)


def text(x):
    return re.sub(r"\s+", " ", x or "").strip()


def house_of(a, default):
    return {"House": "H", "Senate": "S"}.get(((a.get("chamber") or {}).get("name") or ""), default)


def is_amendment(b):
    """A joint resolution proposing an amendment to the Indiana Constitution (not a placeholder, not a call for a federal
    convention or a ratification)."""
    return (b.get("billName") or "")[:2] in ("HJ", "SJ") and bool(re.search(
        r"proposing an amendment to .*?Constitution\s+of\s+the\s+State\s+of\s+Indiana", b.get("title") or "", re.I | re.S)) \
        and not re.match(r"vehicle", text(b.get("description")), re.I)


def is_shell(b):
    """A vehicle bill: a placeholder with no content ("Vehicle Bill."), filed so leaders can rewrite it later."""
    return bool(re.match(r"vehicle bill\b", text(b.get("description")), re.I))


def committee(c):
    """"Ways and Means pursuant to House Rule 126.3" -> "Ways and Means"; "Tax and Fiscal Policy." -> "Tax and Fiscal
    Policy"; "Committee on Joint Rules" -> "Joint Rules"; "Veterans Affairs and The Military" -> "... the Military"."""
    c = re.sub(r"\s+pursuant to .*$|[.;,\s]+$", "", text(c))
    c = re.sub(r"^(?:the )?Committee on ", "", c)
    return re.sub(r"(?<=\s)(And|Of|The|On|For|To|In)\b", lambda m: m.group(1).lower(), c)


def tally(a):
    m = re.search(r"yeas (\d+), nays (\d+)", a)
    return (int(m.group(1)), int(m.group(2))) if m else None


def decode(a, h):
    """One action's wording -> [(house, shared wording)] (a committee report that sends the bill on gives two steps)."""
    if re.search(r"\b(?:failed|Failed)\b", a) and re.search(r"(?:referred|Recommitted|Referred) to", a):
        return [(h, a)]  # a motion to send it to a committee that failed
    m = re.match(r"First reading: referred to (?:the )?Committee on (.+)$", a)
    if m:
        return [(h, f"REFERRED TO {committee(m.group(1)).upper()}")]
    if re.match(r"(?:Rules Suspended\. )?Committee report\b", a) and not re.search(r"motion to correct|technical correction", a, re.I):
        out = [(h, "REPORTED")]
        m = re.search(r"reassigned to (?:the )?Committee on (.+)$", a)
        if m:
            out.append((h, f"REFERRED TO {committee(m.group(1)).upper()}"))
        return out
    m = re.match(r"(?:Recommitted|Referred|Reassigned|Pursuant to Senate Rule [^;]+; reassigned) to (?:the )?Committee on (.+)$", a)
    if m:
        return [(h, f"REFERRED TO {committee(m.group(1)).upper()}")]
    if re.match(r"Third reading: passed", a):
        return [(h, f"PASSED {HOUSE[h].upper()}")]
    if re.match(r"Third reading: (?:defeated|failed)", a):
        return [(h, "FAILED")]
    if re.match(r"Referred to the (House|Senate)$", a):
        return [(h, a)]
    if re.search(r"(?:concurred (?:with|in) (?:House|Senate) amendments)", a) and not re.search(r"failed|defeated", a, re.I):
        t = tally(a)
        if not t or t[0] > t[1]:
            return [(h, "CONCURRED")]
    m = re.search(r"Conference Committee Report (\d+): (adopted|rejected) by the (House|Senate)", a)
    if m:
        return [({"House": "H", "Senate": "S"}[m.group(3)], f"CCR {m.group(1)} {m.group(2).upper()}")]
    if re.match(r"Returned to the (?:House|Senate) without amendments", a):
        return [(h, "RETURNED UNCHANGED")]
    if re.match(r"Signed by the (?:Speaker|President Pro Tempore|President of the Senate)$", a):
        return [(h, a)]
    if re.match(r"Signed by the Governor", a):
        return [("G", "SIGNED")]
    if re.match(r"Bill Became Law .*Without Signature", a, re.I):
        return [("G", a)]
    if re.match(r"Vetoed by the Governor", a):
        return [("G", "VETOED")]
    if re.search(r"veto", a, re.I) and re.search(r"overrid", a, re.I) and not re.search(r"fail|defeat|not ", a, re.I):
        return [(h, "VETO OVERRIDDEN")]
    if a == "Withdrawn":
        return [(h, "Withdrawn by the author")]
    return [(h, a)]


# A sentence's end: a period before a capitalized word or a parenthesis (not a list's "(2)"), not after an initial or an
# abbreviation ("U.S. Code", "No. 2").
SENTENCE_END = re.compile(r"(?<![A-Z]\.[A-Z])(?<!\b[A-Z])(?<!\bNo)(?<!\bSec)(?<!\bInc)\.\)?(?=\s+(?:[A-Z][a-z]|\((?![0-9]+\)|[A-Za-z]\))))")


SPONSOR_LINE = re.compile(r"(?:Authored by|Coauthored by|(?:Representatives?|Senators?) .* (?:added|removed) as|(?:House|Senate) sponsors?:|Cosponsors?:)")


def digest(b):
    """The Legislative Services Agency's digest of the latest version, up to about 3,000 characters at a sentence's end.
    The digest is one paragraph; it's split into paragraphs of a few sentences (about 400 characters) to read easily."""
    d = text((b.get("latestVersion") or {}).get("digest"))
    if len(d) > 3000:
        cut = [m.end() for m in SENTENCE_END.finditer(d[:3000])]
        d = d[:cut[-1]] if cut else d
    paras, start, last = [], 0, 0
    for m in SENTENCE_END.finditer(d):
        if m.end() - start > 400 and last > start:
            paras.append(d[start:last].strip())
            start = last
        last = m.end()
    paras.append(d[start:].strip())
    return "\n".join(p for p in paras if p)


def person(x):
    """An author or sponsor entry -> (house, "First Last", party letter)."""
    h = "S" if (x.get("position_title") or "").startswith("Senator") else "H"
    name = text(f"{x.get('firstName') or ''} {x.get('lastName') or ''}") or re.sub(r"^(?:Representative|Senator) ", "", text(x.get("fullName")))
    return h, name, (x.get("party") or "")[:1]


def bill_link(p, session):
    kind = "bills" if p[1] == "B" else "resolutions"
    house = "house" if p[0] == "H" else "senate"
    return f"https://iga.in.gov/legislative/{session}/{kind}/{house}/{'joint/' if p[1] == 'J' else ''}{int(p[2:])}/details"


def load_session(session):
    """Read one year's bills and return (records, bill number -> record index, fetched time, delegation)."""
    parties = _PARTIES.setdefault(session, {})
    files = glob.glob(os.path.join(folder(session), "bills", "*.json"))
    fetched = datetime.fromtimestamp(max(os.path.getmtime(f) for f in files), ZoneInfo(P.TIMEZONE)).strftime("%Y-%m-%d %H:%M")
    texts, recs, index = {}, [], {}
    for f in sorted(files, key=lambda f: (os.path.basename(f)[0], os.path.basename(f)[1], int(re.sub(r"\D", "", os.path.basename(f)) or 0))):
        b = json.load(open(f))
        name = (b.get("billName") or os.path.basename(f)[:-5]).upper()
        kind = name[:2]
        amendment = is_amendment(b)
        if kind not in ("HB", "SB") and not amendment:
            continue
        p = f"{kind[0]}{'J' if kind[1] == 'J' else 'B'}{int(re.sub(r'\D', '', name))}"
        origin = p[0]
        other = "S" if origin == "H" else "H"

        def order(a):
            """By day; within a day, timed lines first (the signatures and the governor's lines carry only a date)."""
            d = a.get("date") or ""
            return (d[:10], d[11:19] in ("", "00:00:00"), d[11:19], int(a.get("sequence") or 0))
        acts = sorted(b.get("actions") or [], key=order)
        steps = []  # (date, house, shared wording, as written, tally)
        for a in acts:
            desc = text(a.get("description"))
            if SPONSOR_LINE.match(desc):
                continue  # who signed on, and when: the sponsor lists say it (and it would pass for the bill's latest step)
            for h, t in decode(desc, house_of(a, origin)):
                steps.append(((a.get("date") or "")[:10], h, t, desc, tally(desc)))
        texts_ = [s[2] for s in steps]
        passed = set()
        for _, h, t, _, _ in steps:
            if t.startswith("PASSED"):
                passed.add(h)
        ccr = {}
        for _, h, t, _, _ in steps:
            m = re.match(r"CCR (\d+) (ADOPTED|REJECTED)", t)
            if m:
                ccr.setdefault(m.group(1), {})[h] = m.group(2) == "ADOPTED"
        signed_by = {s[3] for s in steps if s[3].startswith("Signed by the") and s[1] != "G"}
        # Passed both houses: the second house passed it unchanged, the first agreed to its changes, both adopted the same
        # conference report, or the presiding officers signed it (enrollment).
        both = (len(passed) == 2 and ("RETURNED UNCHANGED" in texts_ or "CONCURRED" in texts_
                                      or any(v.get("H") and v.get("S") for v in ccr.values()))) or bool(signed_by)
        presented = {"Signed by the Speaker", "Signed by the President of the Senate"} <= signed_by
        law_no = next((m.group(1) for s in steps for m in [re.match(r"Public Law (\d+)$", s[3])] if m), None)
        overridden = {s[1] for s in steps if s[2] == "VETO OVERRIDDEN"} >= {"H", "S"}
        no_signature = any(re.match(r"Bill Became Law", s[3]) for s in steps)
        if amendment:
            stage = 3 if both else (2 if passed else None)
        elif "SIGNED" in texts_ or no_signature or overridden or (law_no and "VETOED" not in texts_):
            stage = 5
        elif "VETOED" in texts_:
            stage = 6
        elif presented:
            stage = 4
        elif both:
            stage = 3
        elif passed:
            stage = 2
        else:
            stage = None
        if stage is not None and stage >= 3:
            passed = {"S", "H"}
        where_h, place, comm = origin, "desk", None
        for _, h, t, a, _ in steps:
            if t.startswith("REFERRED TO"):
                where_h, place, comm = (h if h in HOUSE else where_h), "committee", t[len("REFERRED TO "):]
            elif t == "REPORTED" or re.match(r"(?:Second reading|Reread second time|Placed back on second reading)", a):
                where_h, place, comm = (h if h in HOUSE else where_h), "floor", None
            elif t.startswith("PASSED"):
                place, comm = "desk", None
                where_h = other if h == origin else origin
        if stage is None:
            stage = 1 if place == "floor" else 0
        proper = lambda c: re.sub(r"(?<=\s)(And|Of|The|On|For|To|In)\b", lambda m: m.group(1).lower(), c.title())
        comm = proper(comm) if comm else None
        refs = [(s[1] if s[1] in HOUSE else origin, proper(s[2][len("REFERRED TO "):])) for s in steps if s[2].startswith("REFERRED TO")]
        comm_list = sorted({f"{h} · {c}" for h, c in refs})
        title = text(b.get("description")).rstrip(".") or text(b.get("title"))
        if amendment and not re.match(r"constitutional amendment", title, re.I):
            title = f"Constitutional amendment: {title[:1].lower() + title[1:]}"
        elif amendment:
            title = "Constitutional amendment" + re.sub(r"^constitutional amendment( on| concerning)?", lambda m: ":" if m.group(1) else "", title, flags=re.I)
        what = digest(b)
        # The official title ("A BILL FOR AN ACT to amend the Indiana Code concerning ..."); the digest is "What it does".
        summary = text((b.get("latestVersion") or {}).get("title") or b.get("title"))
        if amendment:
            # "This proposed amendment has been agreed to by one general assembly": its second passage (STATE.amendmentFinal
            # reads it from the summary), kept after the title as a plain fact.
            agreed = re.search(r"This proposed amendment has (?:not )?been (?:previously )?agreed to by (?:one|a) general assembly\.", what.replace("\n", " "), re.I)
            if agreed and agreed.group(0) not in summary:
                summary = f"{summary} {agreed.group(0)}"
        subjects = [text(s.get("entry")).split(";")[0] for s in (b.get("latestVersion") or {}).get("subjects") or []]
        topics = list(dict.fromkeys((["const"] if amendment else []) +
                                    [P.COMMITTEE_TOPICS[c] for _, c in refs if c in P.COMMITTEE_TOPICS] +
                                    [P.SUBJECT_TOPICS[s] for s in subjects if s in P.SUBJECT_TOPICS] +
                                    [k for k in P.TOPIC_WORDS if P.TOPIC_WORDS[k].search(title)]))
        # A bill's first committee: approved (its report adopted), or never heard (Indiana's committees don't vote bills down).
        left = "REPORTED" in texts_ or bool(passed)
        fate = "passed" if left else "none"
        names, seen = [], set()
        for group in ("authors", "coauthors", "sponsors", "cosponsors"):
            for x in b.get(group) or []:
                h, n, party = person(x)
                if party in ("D", "R"):
                    parties[(h, n)] = party
                if n and n not in seen:
                    seen.add(n)
                    names.append(n)
        sponsor = names[0] if names else "—"
        cos = names[1:]
        if what:
            texts[p] = {"statement": what, "label": "From the Legislative Services Agency's digest."}
        if stage == 0:
            desc = f"In {HOUSE[where_h]} committee"
        elif stage == 1:
            desc = f"On the {HOUSE[where_h]} floor"
        else:
            desc = {2: f"Passed the {HOUSE[origin] if origin in passed else HOUSE[other]}", 3: "Passed both houses",
                    4: "On the governor's desk", 5: "Became law", 6: "Vetoed"}[stage]

        def dates(test, mode="last"):
            ds = sorted({s[0] for s in steps if test(s[1], s[2], s[3]) and s[0]})
            return {"first": ds[0], "last": ds[-1], "all": ";".join(ds)}[mode] if ds else ""

        votes = []
        for d, h, t, a, tl in steps:
            if tl and h in HOUSE and (t.startswith("PASSED") or t in ("FAILED", "CONCURRED", "VETO OVERRIDDEN") or t.startswith("CCR ")):
                votes.append([h, "F", None, d, tl[0], tl[1], []])
        action_dates = [s[0] for s in steps if s[0]]
        rec = {
            "nums": [p], "base": [p], "prev": earlier(session, b, p),
            "title": title, "summary": summary, "act": "", "lawCode": "", "law": None, "laws": [],
            "comms": comm_list, "topics": topics, "places": [], "narrow": P.narrow_kind(title),
            "commFate": fate, "mainTopic": topics[0] if topics else "", "local": "local" in topics,
            "senDeleg": False, "asmDeleg": False, "budget": bool(re.search(r"\bbudget\b", title, re.I)),
            "shell": is_shell(b) and stage < 3,
            "passedS": "S" in passed, "passedA": "H" in passed, "program": None,
            "stage": stage, "passedIn": (HOUSE[origin] if origin in passed else HOUSE[other]) if stage == 2 else None,
            "chapter": int(law_no) if law_no and stage == 5 else None,
            "veto": None, "memo": "", "vetoMemo": None,
            "simText": f"{title} {what[:800]}".replace("\n", " "),
            "comm": comm if stage == 0 and place == "committee" else None,
            "first": min(action_dates, default=f"{session}-01-01"),
            "last": max(action_dates, default=f"{session}-01-01"),
            "cosp": len(cos),
            "keyDates": [
                dates(lambda h, t, a: t == "REPORTED", "first"),
                dates(lambda h, t, a: t == "PASSED SENATE", "all"),
                dates(lambda h, t, a: t == "PASSED HOUSE", "all"),
                "",
                # The presiding officers' last signature (the day it's presented to the governor isn't recorded).
                dates(lambda h, t, a: a.startswith("Signed by the") and h != "G") if stage >= 4 and not amendment else "",
                dates(lambda h, t, a: t == "SIGNED" or a.startswith("Bill Became Law")) or (max(action_dates, default="") if stage == 5 else ""),
                dates(lambda h, t, a: t == "VETOED"),
            ],
            "votes": votes, "firstComms": [(refs[0][0], refs[0][1], left)] if refs else [],
            "vers": [{"p": p, "sponsor": sponsor, "district": 0, "cosponsors": cos, "primes": 1, "cosp": len(cos),
                      "statusDesc": desc, "committee": comm if place == "committee" and stage in (0, 2) else None,
                      "actions": [[s[0], s[2] if s[2].isupper() and not s[2].startswith(("CCR ", "RETURNED")) else s[3]] for s in steps],
                      "link": bill_link(p, session)}],
        }
        index[p] = len(recs)
        recs.append(rec)
    json.dump(texts, open(os.path.join(P.DATA, f"texts_{session}.json"), "w"), ensure_ascii=False)
    return recs, index, fetched, {"SENATE": [], "ASSEMBLY": []}


_TITLES = {}


def _titles(session):
    if session not in _TITLES:
        out = {}
        for f in glob.glob(os.path.join(folder(session), "bills", "*.json")):
            b = json.load(open(f))
            if is_shell(b) or any(re.match(r"Public Law \d+", text(a.get("description"))) for a in b.get("actions") or []):
                continue  # placeholders, and laws (yearly bills like "Technical corrections" share titles)
            n = (b.get("billName") or "").upper()
            if n[:2] not in ("HB", "SB") and not is_amendment(b):
                continue
            who = person(b["authors"][0])[1] if b.get("authors") else ""
            out.setdefault(text(b.get("description")).lower(), []).append((f"{n[0]}{'J' if n[1] == 'J' else 'B'}{int(re.sub(r'\D', '', n))}", who))
        _TITLES[session] = out
    return _TITLES[session]


def earlier(session, b, p):
    """The same bill in the two years before: the same short description with the same first author, or a description
    only one bill has in each year."""
    out = set()
    k = text(b.get("description")).lower()
    who = person(b["authors"][0])[1] if b.get("authors") else ""
    if len(k.split()) < 2 or is_shell(b):
        return out
    for y in (session - 1, session - 2):
        if y not in sessions():
            continue
        old = _titles(y).get(k, [])
        same = [n for n, sp in old if sp and sp == who]
        if same:
            out.add((y, same[0]))
        elif len(old) == 1 and len(_titles(session).get(k, [])) == 1:
            out.add((y, old[0][0]))
    return out


def agendas(session):
    return {}


def parties(session, recs):
    return {k: v for k, v in _PARTIES.get(session, {}).items() if v in ("D", "R")}
