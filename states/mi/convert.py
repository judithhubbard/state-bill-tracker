"""Michigan's bills (downloaded by states/mi/fetch.py: each bill's status file from the Legislature's document server) in
the shape build_data.py reads. House and Senate bills of each two-year Legislature, and the joint resolutions proposing
amendments to the state constitution (lettered: "HJR A" is HJRA); other resolutions are left out. An amendment needs
two-thirds of the members of each house and goes to the voters at the next general election (Michigan Constitution,
Art. XII, Sec. 1), never to the governor; its floor votes read "adopted by 2/3 vote Roll Call #..." or "not adopted".

The server writes the files in two formats: older ones repeat <historyitems>, <sponsors> and <categories> for each
item, newer ones wrap <HistoryItem>, <Sponsor> and <Category> elements in one of each (`kids()`).

Each status file has the digest title ("Labor: hours and wages; minimum hourly wage rate; modify."), sponsors in order
with member codes, tie-barred bills, subject categories, the public act number, and the history: each line with the
chamber whose journal records it. The House writes its lines in lower case, the Senate in capitals. A House committee
reports a bill "with recommendation" and it's "referred to second reading"; a Senate committee reports it "favorably"
to the Committee of the Whole. A passage is "passed; given immediate effect Roll Call #4 Yeas 63 Nays 41 ...". The
other house's line noting a passage ("PASSED BY HOUSE WITH IMMEDIATE EFFECT") isn't a vote. "Ordered enrolled" means
both houses passed the same text; then "presented to the Governor", "approved by the Governor", "assigned PA 12'25".
There are no summaries; votes are tallies (members' votes are only in the journals).
"""
import glob, json, os, re, sys
import xml.etree.ElementTree as ET
from datetime import datetime
from zoneinfo import ZoneInfo

from states.mi import profile as P

HOUSE = {"S": "Senate", "H": "House"}
CURRENT = P.session_of(datetime.now(ZoneInfo(P.TIMEZONE)).year)
_PARTIES = {}
# The bills' subject categories -> topics (by the category's first words).
CATEGORY_TOPICS = {"Environmental": "env", "Energy": "env", "Natural resources": "ag", "Agriculture": "ag", "Animals": "ag",
                   "Local government": "local", "Cities": "local", "Counties": "local", "Townships": "local", "Villages": "local",
                   "Taxation": "tax", "Property tax": "tax", "Income tax": "tax", "Sales tax": "tax", "Use tax": "tax",
                   "Corporate income tax": "tax", "Crimes": "safety", "Criminal procedure": "safety", "Corrections": "safety",
                   "Courts": "safety", "Law enforcement": "safety", "Weapons": "safety", "Juveniles": "safety",
                   "Children": "human", "Family law": "human", "Human services": "human", "Veterans": "human",
                   "Senior citizens": "human", "Health": "health", "Health facilities": "health", "Mental health": "health",
                   "Medical marihuana": "health", "Occupations": "biz", "Education": "edu", "School aid": "edu",
                   "Higher education": "edu", "Transportation": "transp", "Vehicles": "transp", "Traffic control": "transp",
                   "Highways": "transp", "Labor": "labor", "Retirement": "labor", "Civil service": "labor", "Housing": "housing",
                   "Land use": "housing", "Property": "housing", "Elections": "gov", "State": "gov", "Records": "gov",
                   "Insurance": "biz", "Financial institutions": "biz", "Commercial code": "biz", "Consumer protection": "biz",
                   "Economic development": "biz", "Liquor": "biz", "Gaming": "biz", "Businesses": "biz",
                   "Public utilities": "env", "Water supply": "env", "Drains": "env", "Individual income tax": "tax",
                   "Civil procedure": "safety", "Civil rights": "safety", "Torts": "safety", "Probate": "safety",
                   "Controlled substances": "safety", "Employment security": "labor", "Worker's compensation": "labor",
                   "Public employees": "labor", "Trade": "biz", "Marihuana": "biz", "Tobacco": "biz", "Food": "biz",
                   "Construction": "biz", "Communications": "biz", "Consumer credit": "biz", "Industrial Hemp": "ag",
                   "Recreation": "ag", "Watercraft": "ag", "Legislature": "gov", "Campaign finance": "gov",
                   "Administrative procedure": "gov", "Military affairs": "human", "Disabilities": "human",
                   "Aeronautics": "transp"}


def kids(r, inner, outer):
    """Repeated elements in either format: <outer><Inner>...</Inner>...</outer> or <outer>...</outer> repeated."""
    return list(r.iter(inner)) or r.findall(outer)


def is_amendment(r):
    """A joint resolution amending the state constitution (not one ratifying a federal amendment: HJR T of 2024)."""
    amends = text(r.findtext("amends"))
    return (r.findtext("prefix") in ("HJR", "SJR") and bool(re.search(r"\bstate constitution\b", amends, re.I))
            and not re.match(r"Ratifies", amends))


def kept(r):
    return r.findtext("prefix") in ("HB", "SB") or is_amendment(r)


def number(r):
    """"HB4001", "HJRA" (joint resolutions are lettered: A ... Z, AA ...)."""
    i = text(r.findtext("identifier"))
    return f"{r.findtext('prefix')}{int(i) if i.isdigit() else i}"


def order(f):
    """Files in number order: house, then bills by number, then joint resolutions by letter (Z before AA)."""
    m = re.match(r"\d{4}-([HS])(B|JR)-(\w+)\.xml$", os.path.basename(f))
    i = m.group(3)
    return (m.group(1), m.group(2) != "B", int(i) if i.isdigit() else 0, len(i), i)


def session_dir(session):
    return os.path.join(P.DATA, f"{session}-{session + 1}")


def sessions():
    return sorted(int(os.path.basename(f)[:4]) for f in glob.glob(os.path.join(P.DATA, "[0-9]" * 4 + "-" + "[0-9]" * 4))
                  if len(glob.glob(os.path.join(f, "*", "*.xml"))) > 1000)


def text(x):
    return re.sub(r"\s+", " ", x or "").strip()


def titled(digest):
    """"Labor: hours and wages; minimum hourly wage rate; modify." -> ("Minimum hourly wage rate; modify", "Labor")."""
    t = text(digest).rstrip(".")
    subject, _, rest = t.partition("; ")
    rest = rest or subject
    return rest[:1].upper() + rest[1:], subject.split(":")[0]


def decode(item):
    """One history line -> (house, shared wording)."""
    a = text(item.findtext("historyaction"))
    h = {"house": "H", "senate": "S"}.get((item.findtext("journal/chamber") or "").lower(), "")
    low = a.lower()
    if re.match(r"(passed|adopted) by (house|senate)", low) or re.search(r"\b(passed|adopted) by (house|senate) with", low):
        return h, a  # the other house's passage, noted on arrival
    if re.match(r"not adopted\b", low) and "roll call" in low:
        return h, "FAILED"  # a joint resolution short of two-thirds
    if re.match(r"adopted\b", low) and "roll call" in low:
        return h, f"PASSED {HOUSE.get(h, 'HOUSE').upper()}"  # a joint resolution: "adopted by 2/3 vote Roll Call #12"
    m = re.search(r"referred to committee on (.+?)(?: with substitute.*)?$", a, re.I)
    if m and "committee of the whole" not in low:
        return h, f"REFERRED TO {m.group(1).strip().upper()}"
    if re.match(r"reported (with recommendation|favorably)", low):
        return h, "REPORTED"
    if re.match(r"referred to (second reading|committee of the whole)|placed on (third reading|order of third reading|order of general orders|immediate passage)|reported by committee of the whole", low):
        return h, "PLACED ON FLOOR"
    if re.match(r"passed\b", low) and "roll call" in low:
        return h, f"PASSED {HOUSE.get(h, 'HOUSE').upper()}"
    if re.search(r"failed to pass|^defeated", low) and "roll call" in low:
        return h, "FAILED"
    if re.search(r"vote on (?:passage|adoption) reconsidered|vote reconsidered", low):
        return h, "RECONSIDERED"
    if re.search(r"concurred in", low) and "roll call" in low:
        return h, "CONCURRED"
    if re.search(r"conference report adopted", low):
        return h, "CONFERENCE ADOPTED"
    if re.search(r"ordered enrolled", low):
        return h, "ENROLLED"
    # A house asking for a passed bill back (SB 6 of 2023: "House requests return", "ENROLLMENT VACATED"): its passage
    # and the enrollment are undone until it passes again.
    if re.search(r"(house|senate) requests return", low):
        return ("H" if low.startswith("house") else "S"), "RETURN REQUESTED"
    if re.search(r"enrollment vacated", low):
        return h, "ENROLLMENT VACATED"
    if re.match(r"presented to the governor", low):
        return "G", "DELIVERED TO GOVERNOR"
    if re.match(r"approved by (the )?governor", low):
        return "G", "SIGNED"
    # A bill the governor didn't sign after the Legislature adjourned for good is vetoed ("pocket veto 1/22/2025", HB 5190
    # of 2023-24).
    if re.match(r"vetoed by (the )?governor|veto|pocket veto", low):
        return "G", "VETOED"
    return h or "G", a


def tally(a):
    m = re.search(r"Yeas (\d+) Nays (\d+)", a, re.I)
    return (int(m.group(1)), int(m.group(2))) if m else None


def load_session(session):
    """Read one session's bills and return (records, bill number -> record index, fetched time, delegation)."""
    path = os.path.join(P.DATA, f"contacts_{session}.json")
    people = json.load(open(path))["people"] if os.path.exists(path) else {}
    by_name = {(sid[0], p["key"]): (sid, p) for sid, p in people.items()}
    parties = _PARTIES.setdefault(session, {})
    from fetch_contacts import name_key

    def person(name, sid=""):
        """"Sen. Jeff Irwin" -> "Jeff Irwin" (the contacts file's spelling where it's a sitting member). Older files
        write bare names; their sponsor ids ("S012A", "H078A") give the house."""
        n = text(name)
        h = sid[:1] if sid[:1] in ("S", "H") else "S" if re.search(r"\bSen\b", n) else "H"
        m = re.match(r"([^,]+), (?:Sen|Rep)\.?\s+(.+)", n)  # "Roth, Rep. John R."
        bare = f"{m.group(2)} {m.group(1)}" if m else re.sub(r"^(Sen|Rep)\.?\s+", "", n)
        last = name_key(bare).split()[-1:]
        hit = by_name.get((h, name_key(bare))) or next(iter([v for (hh, k), v in by_name.items() if hh == h and k.split()[-1:] == last][:1]
                                                             if sum(1 for (hh, k) in by_name if hh == h and k.split()[-1:] == last) == 1 else []), None)
        full = hit[1]["name"] if hit else bare
        if hit and hit[1].get("party"):
            parties[(h, full)] = hit[1]["party"][:1]
        return full

    files = sorted(glob.glob(os.path.join(session_dir(session), "*", "*.xml")))
    fetched = datetime.fromtimestamp(max(os.path.getmtime(f) for f in files), ZoneInfo(P.TIMEZONE)).strftime("%Y-%m-%d %H:%M")
    recs, index = [], {}
    for f in sorted(files, key=order):
        r = ET.parse(f).getroot()
        if not kept(r):
            continue
        amend = is_amendment(r)
        p = number(r)
        origin = p[0]
        items = sorted(kids(r, "HistoryItem", "historyitems"), key=lambda h: ((h.findtext("historydate") or "")[:10], int(h.findtext("sequence") or 0)))
        steps = [((h.findtext("historydate") or "")[:10],) + decode(h) + (text(h.findtext("historyaction")),) for h in items]
        passed, asked = set(), None
        for i, (d, h, t, a) in enumerate(steps):
            if t.startswith("PASSED"):
                passed.add(h)
            elif t == "RECONSIDERED":
                passed.discard(h)
            elif t == "RETURN REQUESTED":
                asked = h
            elif t == "ENROLLMENT VACATED" and asked:
                passed.discard(asked)
                steps[:i] = [s if s[2] != "ENROLLED" else (s[0], s[1], "Ordered enrolled (later vacated)", s[3]) for s in steps[:i]]
        texts_ = [s[2] for s in steps]
        pa = "" if amend else text(r.findtext("publicact/panumber"))
        if amend:
            # Never the governor's: passed both houses once the second house adopted the same text (or the first
            # concurred in its changes), "ordered enrolled" or "filed with the Secretary of State".
            last = max((i for i, s in enumerate(steps) if s[2].startswith("PASSED") and s[1] != origin), default=None)
            agreed = last is not None and (not re.search(r"substitute|amend", steps[last][3], re.I)
                                           or any(s[2] == "CONCURRED" and s[1] == origin for s in steps[last + 1:]))
            filed = any(re.search(r"secretary of state", s[3], re.I) for s in steps)
            stage = 3 if "ENROLLED" in texts_ or filed or (len(passed) == 2 and agreed) else 2 if passed else None
            steps = [(d, h, a if t in ("DELIVERED TO GOVERNOR", "SIGNED", "VETOED") else t, a) for d, h, t, a in steps]
        elif "VETOED" in texts_:
            stage = 6
        elif "SIGNED" in texts_ or pa:
            stage = 5
        elif "DELIVERED TO GOVERNOR" in texts_:
            stage = 4
        elif "ENROLLED" in texts_:
            stage = 3
        elif passed:
            stage = 2
        else:
            stage = None
        if stage is not None and stage >= 3:
            passed = {"S", "H"}
        where_h, place, committee = origin, "desk", None
        for d, h, t, a in steps:
            if t.startswith("REFERRED TO"):
                where_h, place, committee = (h if h in HOUSE else where_h), "committee", t[len("REFERRED TO "):]
            elif t in ("REPORTED", "PLACED ON FLOOR"):
                where_h, place, committee = (h if h in HOUSE else where_h), "floor", None
            elif t.startswith("PASSED"):
                place, committee = "desk", None
                where_h = "S" if h == "H" else "H"
        if stage is None:
            stage = 1 if place == "floor" else 0
        proper = lambda c: re.sub(r"\b(And|Of|The|On|For|To|In)\b", lambda m: m.group(1).lower(), c.title())
        committee = proper(committee) if committee else None
        refs = [(s[1] if s[1] in HOUSE else origin, proper(s[2][len("REFERRED TO "):])) for s in steps if s[2].startswith("REFERRED TO")]
        comm_list = sorted({f"{h} · {c}" for h, c in refs})
        title, subject = titled(r.findtext("digesttitle"))
        if amend:
            title = "Constitutional amendment: " + title[:1].lower() + title[1:]
        cats = [text(c.findtext("maincategory")) for c in kids(r, "Category", "categories")]
        topics = list(dict.fromkeys((["const"] if amend else []) + [v for c in cats for k, v in CATEGORY_TOPICS.items() if c.startswith(k)]))
        topics = list(dict.fromkeys(topics + [k for k in P.TOPIC_WORDS if P.TOPIC_WORDS[k].search(title)]))
        first = next((i for i, s in enumerate(steps) if s[2].startswith("REFERRED TO")), None)
        left = first is not None and any(t in ("REPORTED",) or t.startswith("PASSED") for _, _, t, _ in steps[first + 1:])
        fate = "passed" if left else "none"
        sps = sorted(kids(r, "Sponsor", "sponsors"), key=lambda s: int(s.findtext("sequence") or 0))
        names = [person(text(s.findtext("name")), text(s.findtext("sponsorid"))) for s in sps]
        sponsor = names[0] if names else (person(text(r.findtext("introduced_by"))) if r.findtext("introduced_by") else "—")
        cos = names[1:]
        if stage == 0 and committee:
            desc = f"In {HOUSE[where_h]} committee"
        elif stage <= 1 and place == "floor":
            desc = f"On the {HOUSE[where_h]} floor"
        elif stage >= 2:
            desc = {2: f"Passed the {HOUSE[max(passed)] if passed else 'House'}", 3: "Passed both houses",
                    4: "On the governor's desk", 5: "Signed into law", 6: "Vetoed"}[stage]
        else:
            desc = steps[-1][3] if steps else "Introduced"
        lp = max(((s[0], s[1]) for s in steps if s[2].startswith("PASSED") and s[1] in passed), default=None)

        def dates(test, mode="last"):
            ds = sorted({s[0] for s in steps if test(s[1], s[2]) and s[0]})
            return {"first": ds[0], "last": ds[-1], "all": ";".join(ds)}[mode] if ds else ""

        votes = [[h, "F", None, d] + list(tally(a)) + [[]] for d, h, t, a in steps
                 if h in HOUSE and (t.startswith("PASSED") or t in ("CONCURRED", "FAILED")) and tally(a)]
        action_dates = [s[0] for s in steps if s[0]]
        rec = {
            "nums": [p], "base": [p], "prev": earlier(session, r.findtext("digesttitle"), sponsor),
            "title": title, "summary": "", "act": "", "lawCode": "", "law": None, "laws": [],
            "comms": comm_list, "topics": topics, "places": [], "narrow": P.narrow_kind(title),
            "commFate": fate, "mainTopic": topics[0] if topics else "", "local": "local" in topics,
            "senDeleg": False, "asmDeleg": False, "budget": bool(re.search(r"\bappropriations?\b", title, re.I)),
            "passedS": "S" in passed, "passedA": "H" in passed, "program": None,
            "stage": stage, "passedIn": HOUSE.get(lp[1]) if stage == 2 and lp else None,
            "chapter": int(re.match(r"\d+", pa).group(0)) if pa and re.match(r"\d+", pa) and stage == 5 else None,
            "veto": None, "memo": "", "vetoMemo": None,
            "simText": f"{title} {subject} {text(r.findtext('amends'))}",
            "comm": committee if stage == 0 and place == "committee" else None,
            "first": min(action_dates, default=f"{session}-01-01"),
            "last": max(action_dates, default=f"{session}-01-01"),
            "cosp": len(cos),
            "keyDates": [
                dates(lambda h, t: t == "REPORTED", "first"),
                dates(lambda h, t: t == "PASSED SENATE", "all"),
                dates(lambda h, t: t == "PASSED HOUSE", "all"),
                "",
                dates(lambda h, t: t == "DELIVERED TO GOVERNOR"),
                dates(lambda h, t: t == "SIGNED"),
                dates(lambda h, t: t == "VETOED"),
            ],
            "votes": votes, "firstComms": [(refs[0][0], refs[0][1], left)] if refs else [],
            "vers": [{"p": p, "sponsor": sponsor, "district": 0, "cosponsors": cos, "primes": 1, "cosp": len(cos),
                      "statusDesc": desc, "committee": committee if place == "committee" and stage in (0, 2) else None,
                      "actions": [[s[0], s[2]] for s in steps],
                      "link": f"https://www.legislature.mi.gov/Bills/Bill?ObjectName={r.findtext('objectname')}"}],
        }
        index[p] = len(recs)
        recs.append(rec)
    return recs, index, fetched, {"SENATE": [], "ASSEMBLY": []}


_DIGESTS = {}


def _digests(session):
    if session not in _DIGESTS:
        out = {}
        for f in glob.glob(os.path.join(session_dir(session), "*", "*.xml")):
            r = ET.parse(f).getroot()
            if kept(r):
                sp = min(kids(r, "Sponsor", "sponsors"), key=lambda s: int(s.findtext("sequence") or 0), default=None)
                out.setdefault(text(r.findtext("digesttitle")).lower(), []).append(
                    (number(r), re.sub(r"^(Sen|Rep)\.?\s+", "", text(sp.findtext("name"))) if sp is not None else ""))
        _DIGESTS[session] = out
    return _DIGESTS[session]


def earlier(session, digest, sponsor):
    """The same bill in the Legislature before: the same digest title, and the same first sponsor or a title only one bill
    has in each."""
    if session - 2 not in sessions():
        return set()
    k = text(digest).lower()
    old = _digests(session - 2).get(k, [])
    same = [n for n, s in old if s and s.split()[-1:] == sponsor.split()[-1:]]
    if same:
        return {(session - 2, same[0])}
    if len(old) == 1 and len(_digests(session).get(k, [])) == 1 and len(k.split()) >= 6:
        return {(session - 2, old[0][0])}
    return set()


def agendas(session):
    return {}


def parties(session, recs):
    return {k: v for k, v in _PARTIES.get(session, {}).items() if v in ("D", "R")}
