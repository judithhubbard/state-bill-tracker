"""Pennsylvania's bills (downloaded by states/pa/fetch.py) in the shape build_data.py reads. House and Senate bills of each
two-year regular session; resolutions and special sessions are left out.

The bill history file gives each bill's sponsors (with house, district and party), its printer's numbers and its actions,
each with its chamber ("E" for the governor), verb, committee and date. A bill is reported from committee, considered
three times on the floor (the House often tables bills after first consideration and takes them off the table later;
both houses send most bills to Appropriations before the third), and passes on "third consideration and final passage".
When the second house amends it, the first has to concur. Both houses' presiding officers sign it, and it's presented to
the governor, who signs it (an "Act No."), lets it become law, or vetoes it. Floor and committee votes by member come
from the roll-call pages fetch.py reads; committee votes carry the "Brief Description" used as "What it does".
"""
import glob, io, json, os, re, zipfile
import xml.etree.ElementTree as ET
from collections import defaultdict
from datetime import datetime
from zoneinfo import ZoneInfo

from states.pa import profile as P

HOUSE = {"S": "Senate", "H": "House"}
CURRENT = P.session_of(datetime.now(ZoneInfo(P.TIMEZONE)).year)
_PARTIES = {}


def sessions():
    return sorted(int(m.group(1)) for f in glob.glob(os.path.join(P.DATA, "billhistory_*_0.zip"))
                  if (m := re.search(r"billhistory_(\d{4})_0", f)))


def text(x):
    return re.sub(r"\s+", " ", x or "").strip()


def bills(session):
    z = zipfile.ZipFile(os.path.join(P.DATA, f"billhistory_{session}_0.zip"))
    root = ET.parse(io.BytesIO(z.read(z.namelist()[0]))).getroot()
    return [b for b in root.iter("bill") if b.findtext("type") == "B"]


def number(b):
    return f"{b.findtext('body')}B{int(b.findtext('number'))}"


def contacts(session):
    path = os.path.join(P.DATA, f"contacts_{session}.json")
    return json.load(open(path)) if os.path.exists(path) else {"people": {}, "senateCommittees": {}, "assemblyCommittees": {}}


def proper(name):
    n = re.sub(r"\b([A-Za-z])([A-Za-z']*)", lambda m: m.group(1).upper() + m.group(2).lower(), text(name))
    n = re.sub(r"\b(And|Of|The|On|For|To|In)\b", lambda m: m.group(1).lower(), n)
    return re.sub(r"\b(Mc)([a-z])", lambda m: m.group(1) + m.group(2).upper(), n)


def memo_title(b):
    """The co-sponsorship memo's short title ("Mandating Cursive Handwriting (Formerly HB1934)") -> (title, earlier numbers)."""
    t = text(b.findtext("cosponsorshipMemo"))
    notes = " ".join(re.findall(r"\((?:Former(?:ly)?|Previously|Prior)\b[^)]*\)", t, re.I))
    formerly = re.findall(r"\b([HS])(?:\.?\s*B\.?|ouse Bills?|enate Bills?)\s*(\d+)", notes)
    t = text(re.sub(r"\((?:Former(?:ly)?|Previously|Prior)\b[^)]*\)", "", t, flags=re.I)).strip(" .-")
    return t, [f"{h}B{int(n)}" for h, n in formerly]


def short(title):
    """The official title, shortened: "An Act amending the act of March 10, 1949 (P.L.30, No.14), known as the Public School
    Code of 1949, in terms and courses of study, further providing for ..." -> "Public School Code of 1949: in terms ..."."""
    t = text(title)
    m = re.match(r"An Act amending (?:the act of [^,]+, \d{4} \([^)]*\)|Title \d+ \([^)]*\) of the Pennsylvania Consolidated Statutes)"
                 r"(?:, (?:entitled \"[^\"]*\"|known as (?:the )?([^,]+(?:, \d{4})?)))?,? (.*)", t)
    if m:
        what = m.group(2)
        law = m.group(1) or re.search(r"\(([^)]*)\) of the Pennsylvania", t) and re.search(r"\(([^)]*)\) of the Pennsylvania", t).group(1)
        t = f"{law}: {what}" if law else what
    elif re.match(r"A Joint Resolution proposing", t):
        t = "Constitutional amendment: " + re.sub(r"^A Joint Resolution proposing (?:an amendment|amendments|separate and distinct amendments) to the Constitution of the Commonwealth of Pennsylvania,?\s*", "", t)
    else:
        t = re.sub(r"^An Act\s+", "", t)
    t = t[:1].upper() + t[1:]
    return t if len(t) <= 160 else t[:157].rsplit(" ", 1)[0] + "…"


def when(a):
    """The action's date. The one in its wording comes first: a "(Remarks see House Journal ...)" line is dated when the
    remarks were filed, months later, but its wording names the day of the vote."""
    m = re.search(r"\b(Jan|Feb|Mar|Apr|May|June?|July?|Aug|Sept?|Oct|Nov|Dec)\w*\.? (\d{1,2}), (\d{4})", text(a.findtext("fullAction")))
    if m:
        try:
            return datetime.strptime(f"{m.group(1)[:3]} {m.group(2)} {m.group(3)}", "%b %d %Y").strftime("%Y-%m-%d")
        except ValueError:
            pass
    d = a.findtext("date") or ""
    try:
        return datetime.strptime(d, "%m/%d/%y").strftime("%Y-%m-%d")
    except ValueError:
        return ""


def decode(a, origin):
    """One action -> (house, shared wording)."""
    h, verb, comm, full = a.get("actionChamber") or "", text(a.findtext("verb")), text(a.findtext("committee")), text(a.findtext("fullAction"))
    if re.match(r"(Re-)?referred to|Re-committed to|Reported with request to re-refer to", verb, re.I) and comm and not re.match(r"Reported with", verb):
        return h, f"REFERRED TO {comm.upper()}"
    if re.match(r"(Re-)?reported (as|with|on)", verb, re.I):
        return h, "REPORTED"
    if re.match(r"First consideration", verb, re.I):
        return h, "PLACED ON FLOOR"
    if re.search(r"defeated on final passage", verb, re.I):
        return h, "FAILED"
    if re.search(r"final passage,?$", verb, re.I) and "reconsidered" not in verb.lower():
        return h, f"PASSED {HOUSE.get(h, 'HOUSE').upper()}"
    if re.search(r"Vote on final passage reconsidered", verb, re.I):
        return h, "RECONSIDERED"
    if re.search(r"concurred in (?:House|Senate) amendments", verb, re.I):
        return h, "CONCURRED"
    if re.match(r"Presented to the Governor", verb, re.I):
        return "G", "DELIVERED TO GOVERNOR"
    if re.match(r"Approved by the Governor|Became Law without", full, re.I):
        return "G", "SIGNED"
    if re.search(r"Line Item Veto", full, re.I):
        return "G", "Signed with item vetoes"
    if re.search(r"Vetoed by the Governor|^Vetoed", full, re.I):
        return "G", "VETOED"
    # The rest as written, without the date ("Laid on the table, April 9, 2025").
    return h or "G", re.sub(r",?\s+(?:Jan|Feb|Mar|Apr|May|June?|July?|Aug|Sept?|Oct|Nov|Dec)\w*\.? \d{1,2}, \d{4}.*$", "", full).strip(" ,")


def rollcalls(session):
    """Bill -> [roll call records] (fetch.py's bill pages and roll-call files)."""
    folder = os.path.join(P.DATA, str(session))
    rc = {}
    for f in glob.glob(os.path.join(folder, "rollcalls", "*.json")):
        r = json.load(open(f))
        rc[r.get("link")] = r
    out = {}
    for f in glob.glob(os.path.join(folder, "bills", "*.json")):
        out[os.path.basename(f)[:-5]] = [rc[l] for l in json.load(open(f)).get("rollcalls", []) if l in rc]
    return out


def day(s):
    for fmt in ("%A %b %d, %Y", "%b %d, %Y", "%B %d, %Y"):
        try:
            return datetime.strptime(text(s), fmt).strftime("%Y-%m-%d")
        except ValueError:
            pass
    return ""


_KEYS = {}


def _session(session):
    """Bill -> (memo title, official title, prime sponsor's last name) for linking sessions."""
    if session not in _KEYS:
        out = {}
        if session in sessions():
            for b in bills(session):
                sp = b.find("sponsors/sponsor")
                out[number(b)] = (memo_title(b)[0].lower(), text(b.findtext("shortTitle")).lower(),
                                  text(sp.text).split()[-1].upper() if sp is not None and text(sp.text) else None)
        _KEYS[session] = out
    return _KEYS[session]


def earlier(session, b, num):
    """The same bill last session: the memo's "(Former HB 1934)", else the same memo title, or the same official title
    and the same prime sponsor (or a long official title only one bill has in each session)."""
    prev = session - 2
    if prev not in sessions():
        return set()
    old = _session(prev)
    memo, formerly = memo_title(b)
    hits = [n for n in formerly if n in old]
    if hits:
        return {(prev, hits[0])}
    me = _session(session).get(num)
    if not me:
        return set()
    if len(me[0].split()) >= 3:
        same = [n for n, v in old.items() if v[0] == me[0]]
        if len(same) == 1:
            return {(prev, same[0])}
    same = [n for n, v in old.items() if v[1] == me[1]]
    mine = [n for n, v in _session(session).items() if v[1] == me[1]]
    by_sponsor = [n for n in same if old[n][2] == me[2]]
    if len(by_sponsor) == 1:
        return {(prev, by_sponsor[0])}
    if len(same) == 1 and len(mine) == 1 and len(me[1].split()) >= 25:
        return {(prev, same[0])}
    return set()


def load_session(session):
    """Read one session's bills and return (records, bill number -> record index, fetched time, delegation)."""
    con = contacts(session) if session == CURRENT else {"people": {}, "senateCommittees": {}, "assemblyCommittees": {}}
    seat_of_id = {p["id"]: sid for sid, p in con["people"].items() if p.get("id")}
    comm_name = {re.sub(r"[^a-z]", "", c["name"].lower().replace("and", "").replace("&", "")): c["name"]
                 for k in ("senateCommittees", "assemblyCommittees") for c in con[k].values()}
    def cname(c):
        return comm_name.get(re.sub(r"[^a-z]", "", c.lower().replace("and", "").replace("&", ""))) or proper(c)
    rolls = rollcalls(session)
    path = os.path.join(P.DATA, f"billhistory_{session}_0.zip")
    fetched = datetime.fromtimestamp(os.path.getmtime(path), ZoneInfo(P.TIMEZONE)).strftime("%Y-%m-%d %H:%M")
    parties = _PARTIES.setdefault(session, {})
    texts = {}
    recs, index = [], {}
    for b in sorted(bills(session), key=lambda b: (b.findtext("body"), int(b.findtext("number")))):
        p = number(b)
        origin = p[0]
        sps = list(b.iter("sponsor"))

        def who(s):
            sid = f"{s.get('body')}:{int(s.get('districtNumber') or 0)}"
            person = con["people"].get(sid)
            name = person["name"] if person and person["key"].split()[-1:] == [re.sub(r"[^a-z-]", "", text(s.text).split()[-1].lower())] else proper(s.text)
            parties[(s.get("body"), name)] = s.get("party")
            return name
        names = [who(s) for s in sps]
        sponsor = names[0] if names else "—"
        cos = names[1:]
        steps = []
        for a in b.iter("action"):
            h, t = decode(a, origin)
            steps.append((when(a), h, t, text(a.findtext("fullAction"))))
        # A passage the house reconsidered doesn't count (until it passes again).
        passed, last_pass = set(), {}
        for i, (d, h, t, a) in enumerate(steps):
            if t.startswith("PASSED"):
                passed.add(h)
                last_pass[h] = i
            elif t == "RECONSIDERED":
                passed.discard(h)
        texts_ = [s[2] for s in steps]
        signed_both = any("Signed in House" in s[3] for s in steps) and any("Signed in Senate" in s[3] for s in steps)
        if "SIGNED" in texts_:
            stage = 5
        elif "VETOED" in texts_:
            stage = 6
        elif "DELIVERED TO GOVERNOR" in texts_:
            stage = 4
        elif signed_both or (len(passed) == 2 and agreed(steps, last_pass)):
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
        committee = cname(committee) if committee else None
        refs = [(s[1] if s[1] in HOUSE else origin, cname(s[2][len("REFERRED TO "):])) for s in steps if s[2].startswith("REFERRED TO")]
        comm_list = sorted({f"{h} · {c}" for h, c in refs})
        memo, _ = memo_title(b)
        official = text(b.findtext("shortTitle"))
        title = memo or short(official)
        topics = [P.COMMITTEE_TOPICS[w] for w in P.COMMITTEE_TOPICS if any(w.lower() in c.lower() for _, c in refs)]
        if re.match(r"A Joint Resolution proposing", official):
            topics.insert(0, "const")
        topics = list(dict.fromkeys(topics + [k for k in P.TOPICS if k in P.TOPIC_WORDS and P.TOPIC_WORDS[k].search(f"{title} {official}")]))
        first = next((i for i, s in enumerate(steps) if s[2].startswith("REFERRED TO")), None)
        first_comms = []
        if first is not None:
            later = [s[2] for s in steps[first + 1:]]
            left = any(t in ("REPORTED",) or t.startswith("PASSED") for t in later)
            first_comms.append((refs[0][0], refs[0][1], left))
        fate = "passed" if first_comms and first_comms[0][2] else "none"
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
        passed_in = HOUSE.get(lp[1]) if stage == 2 and lp else None

        def dates(test, mode="last"):
            ds = sorted({s[0] for s in steps if test(s[1], s[2]) and s[0]})
            return {"first": ds[0], "last": ds[-1], "all": ";".join(ds)}[mode] if ds else ""

        def member(m):
            sid = seat_of_id.get(m[0])
            return sid or f"{'S' if 'Sen' in m[1] else 'H'}?{re.sub(r'^(Rep|Sen)\. ', '', m[1])}"
        code = {"Nay": "N", "Yea": "Y"}
        votes, floor_days = [], set()
        for r in rolls.get(p, []):
            ms = r.get("members") or []
            yes = sum(1 for m in ms if m[2] == "Yea")
            no = sum(1 for m in ms if m[2] == "Nay")
            d = day(r.get("date"))
            if r["kind"] == "F":
                if not re.search(r"PASSAGE|CONCUR", r.get("motion") or "", re.I):
                    continue
                floor_days.add((r["house"], d))
                votes.append([r["house"], "F", None, d, yes, no, [[member(m), code.get(m[2], "A")] for m in ms if m[2] != "Yea"]])
            else:
                votes.append([r["house"], "C", cname(r.get("committee") or ""), d, yes, no, [[member(m), code.get(m[2], "A")] for m in ms if m[2] != "Yea"]])
                if r.get("description"):
                    texts[p] = {"statement": r["description"], "label": "The committee's description"}
        for d, h, t, a in steps:
            m = re.search(r"\((\d+)-(\d+)\)", a)
            if m and h in HOUSE and (t.startswith("PASSED") or t in ("CONCURRED", "FAILED")) and (h, d) not in floor_days:
                votes.append([h, "F", None, d, int(m.group(1)), int(m.group(2)), []])
        votes.sort(key=lambda v: v[3])
        act = next((re.search(r"Act No\. (\d+)", s[3]).group(1) for s in steps if re.search(r"Act No\. \d+", s[3])), None)
        action_dates = [s[0] for s in steps if s[0]]
        rec = {
            "nums": [p], "base": [p], "prev": earlier(session, b, p),
            "title": title, "summary": official if memo else "", "act": "", "lawCode": "", "law": None, "laws": [],
            "comms": comm_list, "topics": topics, "places": [], "narrow": P.narrow_kind(title),
            "commFate": fate, "mainTopic": topics[0] if topics else "", "local": "local" in topics,
            "senDeleg": False, "asmDeleg": False, "budget": bool(re.search(r"\bGeneral Appropriation\b|\bappropriations?\b", official, re.I)),
            "passedS": "S" in passed, "passedA": "H" in passed, "program": None,
            "stage": stage, "passedIn": passed_in, "chapter": int(act) if act and stage == 5 else None,
            "veto": None, "memo": "", "vetoMemo": None,
            "simText": f"{title} {official}",
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
            "votes": votes, "firstComms": first_comms,
            "vers": [{"p": p, "sponsor": sponsor, "district": int(sps[0].get("districtNumber") or 0) if sps else 0,
                      "cosponsors": cos, "primes": 1, "cosp": len(cos), "statusDesc": desc,
                      "committee": committee if place == "committee" and stage in (0, 2) else None,
                      "actions": [[s[0], s[2]] for s in steps]}],
        }
        index[p] = len(recs)
        recs.append(rec)
    if session == CURRENT or not os.path.exists(os.path.join(P.DATA, f"texts_{session}.json")):
        json.dump(texts, open(os.path.join(P.DATA, f"texts_{session}.json"), "w"), ensure_ascii=False)
    return recs, index, fetched, {"SENATE": [], "ASSEMBLY": []}


def agreed(steps, last_pass):
    """Both houses passed it: the same text, unless the second house amended it and the first hasn't concurred."""
    first, second = sorted(last_pass, key=lambda h: last_pass[h])
    start = next((i for i, s in enumerate(steps) if s[1] == second), 0)
    amended = any(re.search(r"amend", s[3], re.I) and s[1] == second for s in steps[start:last_pass[second] + 1])
    return not amended or any(s[2] == "CONCURRED" and s[1] == first for s in steps[last_pass[second]:])


def agendas(session):
    return {}


def parties(session, recs):
    return {k: v for k, v in _PARTIES.get(session, {}).items() if v in ("D", "R")}


def seats(session):
    return {p["id"]: sid for sid, p in contacts(session)["people"].items() if p.get("id")}
