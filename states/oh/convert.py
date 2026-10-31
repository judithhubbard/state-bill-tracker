"""Ohio's bills (downloaded by states/oh/fetch.py from the Legislative Service Commission's API) in the shape
build_data.py reads. Each House or Senate bill is one record ("HB96"); its versions are the stages it reached.

The actions are structured (chamber, action, committee, and each vote's members), so the steps the site's rules use
are put in the shared wording: "Refer to Committee" -> "REFERRED TO <committee>", "Reported" with a favorable result ->
"REPORTED", "Passed" -> "PASSED HOUSE/SENATE", and so on; other actions are kept as written. A committee that reports a
bill to another ("Reported - Re-referred to Finance") is a referral to that one. The governor's signature isn't an
action: it's the enrolled version's governor_signed_date (and to_governor_date for its delivery). Votes list each
member, committee votes included.

Joint resolutions proposing constitutional amendments ("HJR1", "SJR2") are records too: each house "Adopted" them, by
three-fifths, and an adopted resolution goes to the voters, never the governor (its enrolled version has no signing).
"""
import glob, json, os, re
from datetime import datetime
from zoneinfo import ZoneInfo

from states.oh import profile as P

HOUSE = {"S": "Senate", "H": "House"}
CURRENT = P.session_of(datetime.now(ZoneInfo(P.TIMEZONE)).year)


def folder(session):
    return os.path.join(P.DATA, str(session))


def sessions():
    return sorted(int(os.path.basename(f)) for f in glob.glob(os.path.join(P.DATA, "[0-9]" * 4))
                  if glob.glob(os.path.join(f, "bills", "*.json")))


def text(x):
    return re.sub(r"\s+", " ", x or "").strip()


GERUND = {"authorizing": "authorizes", "requiring": "requires", "establishing": "establishes", "creating": "creates",
          "permitting": "permits", "prohibiting": "prohibits", "modifying": "modifies", "making": "makes",
          "providing": "provides", "allowing": "allows", "designating": "designates", "revising": "revises",
          "increasing": "increases", "expanding": "expands", "changing": "changes", "regulating": "regulates",
          "eliminating": "eliminates", "extending": "extends", "naming": "names", "granting": "grants"}


def purpose(long_title):
    """What a bill does, from its long title: the part after the last list of sections ("To amend sections 319.202 ...
    of the Revised Code to modify the law that ..." -> "Modifies the law that ..."). The purpose can also follow as
    "regarding ...", "relating to ...", a participle ("authorizing ..."), or after an effective date."""
    t = text(long_title)
    # A joint resolution: "Proposing to amend Section 2 of Article XII of the Constitution of the State of Ohio to
    # require ..." -> "Requires ...".
    if re.match(r"Proposing\b", t):
        parts = re.split(r"\bof the Constitution of the State of Ohio\b,?\s*", t, maxsplit=1)
        rest = re.sub(r"^and\s+", "", parts[-1]) if len(parts) > 1 else ""
        lead = re.match(r"to, ([^,]+), (.+)$", rest)  # "to, beginning in 2027, exempt ..."
        if lead:
            return lead.group(1)[:1].upper() + lead.group(1)[1:] + ", " + third_person(lead.group(2)).lower()[:1] + third_person(lead.group(2))[1:]
        return third_person(rest) if re.match(r"to\s+[a-z]", rest) else t
    listing = r"(?:amend|enact|repeal|codify)\s+(?:new\s+)?(?:sections?|Sections?|for the purpose)\b"
    parts = re.split(r"\bof the Revised Code\b,?\s*", t)
    s = parts[-1].strip() if len(parts) > 1 else t
    s = re.sub(r"^(?:effective [A-Z][a-z]+ \d{1,2}, \d{4},\s*)?(?:and\s+)?", "", s, flags=re.I)
    if not s or s[0] in ";," or re.match(rf"(?:to\s+)?{listing}", s, re.I):
        # Budget titles go on to list other acts' sections ("... Section 6 of H.B. 150 of the 134th General Assembly");
        # the purpose starts at the first "to ..." after the last such list.
        ends = list(re.finditer(rf"(?:General Assembly|Revised Code)(?: as subsequently amended)?,?\s+(?:and\s+)?(?=to (?!{listing}))", t))
        if ends:
            s = t[ends[-1].end():]
        else:
            return t  # a title that only amends other acts' sections (a handful): shown as written
    # Text that doesn't open with a purpose ("that is scheduled to take effect ...; to make ...") gives way to its first
    # "to ...".
    if not re.match(r"(?:to\s|regarding\s|relative to\s|relating to\s|concerning\s|with (?:regard|respect) to\s|\w+ing\s)", s, re.I):
        first = re.search(rf";\s*(?=to (?!{listing})[a-z]+ )", s) or re.search(rf"\bto (?!{listing}|take effect)[a-z]+ ", s)
        if first:
            s = s[first.end():] if s[first.start()] == ";" else s[first.start():]
    about = re.match(r"(?:regarding|relative to|relating to|concerning|with regard to|with respect to)\s+(.+)$", s, re.I)
    if about:
        return "Concerns " + about.group(1)
    w, _, rest = s.partition(" ")
    if w.lower() in GERUND:
        return GERUND[w.lower()].capitalize() + " " + rest
    return third_person(s)


def third_person(s):
    """"to modify the law" -> "Modifies the law": the long title's verbs are "to ..." forms. An adverb first ("partially
    exempt", "no longer prohibit") leaves the verb after it."""
    s = re.sub(r"^[Tt]o\s+", "", s)
    m = re.match(r"((?:\w+ly|no longer|not)\s+)(.*)$", s, re.I)
    head, s = (m.group(1), m.group(2)) if m else ("", s)
    w, _, rest = s.partition(" ")
    lw = w.lower()
    if lw.isalpha() and lw not in ("the", "a", "an"):
        lw = lw[:-1] + "ies" if re.search(r"[^aeiou]y$", lw) else lw + "es" if re.search(r"(?:s|sh|ch|x|z|o)$", lw) else lw + "s"
        s = f"{lw} {rest}"
    s = head + s
    return s[:1].upper() + s[1:]


def step(a):
    """One action -> (date, house, shared wording, as written, committee)."""
    day = (a.get("occurred") or "")[:10]
    h = "S" if a.get("chamber") == "Senate" else "H"
    act = text(a.get("action"))
    code = (a.get("action_code") or "").rsplit("_", 1)[0]
    cm = text(a.get("committee") or a.get("cmte_name"))
    t = act
    re_ref = re.match(r"Reported - Re-referred to (.+)$", act)
    if re_ref:
        t, cm = f"REFERRED TO {re_ref.group(1).upper()}", re_ref.group(1)
    elif code == "refer" or act in ("Refer to Committee", "Re-referred"):
        t = f"REFERRED TO {cm.upper()}" if cm else act
    elif code == "crpt" and (a.get("result") or "").startswith("Favorable"):
        t = "REPORTED"
    elif code == "pass" and (a.get("result") or "Passed") in ("Passed", "Adopted"):
        t = f"PASSED {HOUSE[h].upper()}"
    elif re.match(r"Concurred in (?:House|Senate) amendments|Conference report agreed to", act) and (a.get("result") or "Passed") in ("Passed", "Adopted"):
        t = f"AGREED {HOUSE[h].upper()}"
    elif re.search(r"passed notwithstanding objections of the Governor|veto overridden", act, re.I) and "item" not in act.lower():
        t = "OVERRIDDEN"
    elif re.match(r"veto receipt$|vetoed\b", act, re.I):
        t = "VETOED"  # "Veto receipt"; a "Line item veto receipt" is a law with items vetoed, kept as written
    elif re.match(r"sent to governor$", act, re.I):
        t = "DELIVERED TO GOVERNOR"
    return day, h, t, act, cm


# ---- The same bill in earlier General Assemblies. Bills come back under new numbers and the data doesn't link them,
# so: an earlier bill with the same short title whose long title's purpose shares at least 60% of its words (40% with the
# same primary sponsor). Up to two General Assemblies back. Appropriation bills (a new one each time) don't match.
_EARLIER = {}
_SKIP = {"the", "and", "act", "that", "with", "for", "under", "section", "this", "law", "certain", "regarding", "relative"}


def _session(session):
    if session not in _EARLIER:
        out = {}
        for f in glob.glob(os.path.join(folder(session), "bills", "*.json")):
            d = json.load(open(f))
            top = (d.get("versions") or [{}])[-1]
            short = text(top.get("short_title")).upper()
            if not short or re.search(r"APPROPRIATION|BUDGET", short):
                continue
            words = set(re.findall(r"[a-z0-9]{3,}", purpose(top.get("long_title") or "").lower())) - _SKIP
            prime = ((top.get("sponsors") or [{}])[0] or {}).get("member_id")
            out[os.path.basename(f)[:-5]] = (short, words, prime)
        _EARLIER[session] = out
    return _EARLIER[session]


def earlier(session, bill):
    out = set()
    me = _session(session).get(bill)
    if not me or len(me[1]) < 5:
        return out
    for y in (session - 2, session - 4):
        if not os.path.isdir(folder(y)):
            continue
        best = None
        for other, (short, words, prime) in _session(y).items():
            if short != me[0]:
                continue
            j = len(me[1] & words) / max(1, len(me[1] | words))
            if j >= 0.6 or (j >= 0.4 and prime and prime == me[2]):
                if not best or j > best[0]:
                    best = (j, other)
        if best:
            out.add((y, best[1]))
    return out


def agreed(raw, origin):
    """Whether both houses passed the same text: the second house reported and passed it without amendments, or the
    first house then concurred or adopted a conference report. A second house's "Passed - Amended" or substitute (HB 27
    of the 135th) leaves the first house's agreement to come."""
    second = [a for a in raw if ("S" if a.get("chamber") == "Senate" else "H") != origin]
    changed = any(re.search(r"Substitute|Amended", a.get("action") or "") for a in second
                  if re.match(r"Reported|Passed", a.get("action") or ""))
    first_ok = any(step(a)[2].startswith("AGREED") and ("S" if a.get("chamber") == "Senate" else "H") == origin for a in raw)
    return first_ok or not changed


def load_session(session):
    """Read one session's bills and return (records, bill number -> record index, fetched time, delegation)."""
    live = session >= CURRENT
    files = sorted(glob.glob(os.path.join(folder(session), "bills", "*.json")))
    try:
        listing = {i["number"].upper(): i for i in json.load(open(os.path.join(folder(session), "legislation.json")))}
    except (OSError, ValueError):
        listing = {}
    try:
        legs = {m["lpid"]: m for m in json.load(open(os.path.join(folder(session), "legislators.json")))}
    except (OSError, ValueError):
        legs = {}
    seat_of = seats(session)
    stamp = max((os.path.getmtime(f) for f in files), default=0)
    fetched = datetime.fromtimestamp(stamp, ZoneInfo(P.TIMEZONE)).strftime("%Y-%m-%d %H:%M")

    def member(lpid):
        m = legs.get(lpid) or {}
        return seat_of.get(lpid) or f"{'S' if lpid.startswith('sen_') else 'H'}?{m.get('lastname') or lpid.split('_')[1].title()}"

    recs, index = [], {}
    for f in sorted(files, key=lambda f: (os.path.basename(f)[:2], int(re.sub(r"\D", "", os.path.basename(f)) or 0))):
        p = os.path.basename(f)[:-5]
        d = json.load(open(f))
        vers = d.get("versions") or []
        item = listing.get(p, {})
        if not vers and not item:
            continue
        top = vers[-1] if vers else item
        origin, other = p[0], ("S" if p[0] == "H" else "H")
        amendment = p[1:3] == "JR"  # a joint resolution proposing a constitutional amendment
        raw = sorted(d.get("actions") or [], key=lambda a: a.get("occurred") or "")
        steps = [step(a)[:4] for a in raw]
        comms_of = [step(a)[4] for a in raw]
        en = next((v for v in vers if v.get("version_id") == "EN"), None)
        signed = (en or {}).get("governor_signed_date")
        sent = (en or {}).get("to_governor_date")
        # A few enrolled bills have no signing date (HB 110 of the 134th, the budget): in a finished General Assembly an
        # enrolled bill the governor didn't veto became law.
        vetoed = any(step(a)[2] == "VETOED" for a in raw)
        if amendment:
            signed = sent = None  # goes to the voters, not the governor
        if not signed and en and not live and not vetoed and not amendment:
            signed = en.get("effective_date") or en.get("concurrence_date") or (raw[-1].get("occurred") or "")[:10] or None
        if signed:
            steps.append((signed, "G", "SIGNED", "Signed by the governor"))
        if sent:
            steps.append((sent, "G", "DELIVERED TO GOVERNOR", "Sent to the governor"))
        steps.sort(key=lambda s: s[0])
        texts = [t for _, _, t, _ in steps]
        passed = {h for _, h, t, _ in steps if t.startswith("PASSED")}
        if "SIGNED" in texts or ("OVERRIDDEN" in texts and en):
            stage = 5
        elif "VETOED" in texts:
            stage = 6
        elif "DELIVERED TO GOVERNOR" in texts:
            stage = 4
        elif en or ((live or amendment) and len(passed) == 2 and agreed(raw, origin)):
            stage = 3  # enrolled; while it runs, also passed unamended by the second house or agreed to by the first
        elif passed:
            stage = 2
        else:
            stage = None
        if stage is not None and stage >= 3:
            passed = {"S", "H"}
        # Where it is now.
        house, place, committee = origin, "desk", None
        for a in raw:
            dd, h, t, act, cm = step(a)
            if t.startswith("REFERRED TO"):
                house, place, committee = h, "committee", cm
            elif t == "REPORTED":
                house, place, committee = h, "floor", None
            elif t.startswith("PASSED"):
                place, committee = "desk", None
                house = other if h == origin else origin
            elif act == "Introduced":
                house = h
        if stage is None:
            stage = 1 if place == "floor" else 0
        last_pass = max(((dd, h) for dd, h, t, _ in steps if t.startswith("PASSED")), default=None)
        passed_in = HOUSE[last_pass[1]] if stage == 2 and last_pass else None
        refs = [(h, cm) for (dd, h, t, a), cm in zip([step(x)[:4] for x in raw], comms_of) if t.startswith("REFERRED TO") and cm]
        gate = {"Rules and Reference"}
        comm_names = {c for _, c in refs}
        comm_list = sorted({f"{h} · {c}" for h, c in refs if c not in gate})
        title = text(top.get("short_title") or item.get("short_title"))
        if amendment:
            # "CA: Require 60% vote ..." -> "Constitutional amendment: Require 60% vote ..."
            rest = re.sub(r"^CA\s*:\s*", "", title)
            title = "Constitutional amendment: " + rest[:1].upper() + rest[1:]
        what = purpose(top.get("long_title") or (vers[0].get("long_title") if vers else ""))
        topics = [k for k, (label, cset, _, _) in P.TOPICS.items()
                  if comm_names & cset or (k in P.TOPIC_WORDS and P.TOPIC_WORDS[k].search(title + " " + what[:400]))]
        if amendment:
            topics.insert(0, "const")
        own = [c for h, c in refs if h == origin and c not in gate]
        first_comms = []
        if own:
            later = [step(x) for x in raw]
            k0 = next(i for i, s in enumerate(later) if s[1] == origin and s[2].startswith("REFERRED TO") and s[4] not in gate)
            left = any(s[1] == origin and (s[2] in ("REPORTED",) or s[2].startswith("PASSED")) for s in later[k0 + 1:])
            first_comms.append((origin, own[0], left))
        fate = "passed" if "REPORTED" in texts else "none"
        spons = item.get("sponsors") or top.get("sponsors") or []
        cosp = item.get("cosponsors") or top.get("cosponsors") or []
        sponsor = text(spons[0].get("full_name")) if spons else "—"
        co = [text(s.get("full_name")) for s in spons[1:] + cosp]
        for s in spons + cosp:
            pty = {"party_republican_1": "R", "party_democrat_1": "D"}.get(s.get("party"))
            if pty:
                _PARTIES.setdefault(session, {})[("S" if s.get("chamber") == "Senate" else "H", text(s.get("full_name")))] = pty
        if stage == 0 and committee:
            desc = f"In {HOUSE[house]} committee"
        elif stage <= 1 and place == "floor":
            desc = f"On the {HOUSE[house]} floor"
        elif stage >= 2:
            desc = {2: f"Passed the {passed_in}", 3: "Passed both houses", 4: "On the governor's desk",
                    5: "Signed into law", 6: "Vetoed"}[stage]
        else:
            desc = steps[-1][3] if steps else "Introduced"

        def dates(test, mode="last"):
            ds = sorted({dd for dd, h, t, a in steps if test(h, t, a) and dd})
            return {"first": ds[0], "last": ds[-1], "all": ";".join(ds)}[mode] if ds else ""

        votes = []
        for a in raw:
            dd, h, t, act, cm = step(a)
            yeas, nays = a.get("yeas") or [], a.get("nays") or []
            if not (yeas or nays):
                continue
            if t == "REPORTED" or (a.get("action_code") or "").startswith("crpt"):
                votes.append([h, "C", cm or None, dd, len(yeas), len(nays), [[member(x), "N"] for x in nays]])
            elif t.startswith(("PASSED", "AGREED")) or t == "OVERRIDDEN":
                votes.append([h, "F", None, dd, len(yeas), len(nays), [[member(x), "N"] for x in nays]])
        action_dates = [dd for dd, _, _, _ in steps if dd]
        district = int((spons[0].get("district") if spons else 0) or 0)
        ver = {"p": p, "sponsor": sponsor, "district": district, "cosponsors": co, "primes": max(1, len(spons)),
               "cosp": len(co), "statusDesc": desc,
               "committee": committee if place == "committee" and stage in (0, 2) else None,
               "actions": [[dd, t] for dd, _, t, _ in steps]}
        rec = {
            "nums": [p], "base": [p], "prev": earlier(session, p),
            "title": title, "summary": "", "act": "", "lawCode": "", "law": None, "laws": [],
            "comms": comm_list, "topics": topics, "places": [], "narrow": P.narrow_kind(title),
            "commFate": fate, "mainTopic": topics[0] if topics else "", "local": "local" in topics,
            "senDeleg": False, "asmDeleg": False, "budget": bool(re.search(r"\bappropriations?\b|\bbudget\b", title, re.I)),
            "passedS": "S" in passed, "passedA": "H" in passed, "program": None,
            "stage": stage, "passedIn": passed_in, "chapter": None,
            "veto": None, "memo": "", "vetoMemo": None,
            "simText": f"{title}. {what}",
            "comm": committee if stage == 0 and place == "committee" else None,
            "first": min(action_dates, default=f"{session}-01-01"),
            "last": max(action_dates, default=f"{session}-01-01"),
            "cosp": len(co),
            "keyDates": [
                dates(lambda h, t, a: h == origin and t == "REPORTED", "first"),
                dates(lambda h, t, a: t == "PASSED SENATE", "all"),
                dates(lambda h, t, a: t == "PASSED HOUSE", "all"),
                "",
                dates(lambda h, t, a: t == "DELIVERED TO GOVERNOR"),
                dates(lambda h, t, a: t == "SIGNED"),
                dates(lambda h, t, a: t == "VETOED"),
            ],
            "votes": votes, "firstComms": first_comms, "vers": [ver],
        }
        index[p] = len(recs)
        recs.append(rec)
    return recs, index, fetched, {"SENATE": [], "ASSEMBLY": []}


def agendas(session):
    try:
        return json.load(open(os.path.join(folder(session), "agendas.json")))
    except (OSError, ValueError):
        return {}


_PARTIES = {}


def parties(session, recs):
    return {k: v for k, v in _PARTIES.get(session, {}).items() if v in ("D", "R")}


def seats(session):
    """Member lpid -> seat id ("S:5", "H:63"), from data/oh/contacts_<session>.json (states/oh/contacts.py)."""
    path = os.path.join(P.DATA, f"contacts_{session}.json")
    if not os.path.exists(path):
        return {}
    return {p["id"]: sid for sid, p in json.load(open(path))["people"].items() if p.get("id")}
