"""Oregon's bills (downloaded by states/or/fetch.py from the Legislature's OData API) in the shape build_data.py reads.
One regular session a year (the API's "2025R1"); House and Senate bills only.

The history lines carry their house; the steps the site's rules use are put in the shared wording, the rest kept as
written. A committee's recommendation that sends a bill on ("Do pass and be referred to Ways and Means") is a referral
to that committee. Floor votes (MeasureVotes) belong to a history action, so their house is certain; committee votes
(CommitteeVotes) are by member too. The package is named "or", a Python keyword, so it's loaded with importlib.
"""
import glob, importlib, json, os, re
from collections import defaultdict
from datetime import datetime
from zoneinfo import ZoneInfo

P = importlib.import_module("states.or.profile")

HOUSE = {"S": "Senate", "H": "House"}
CURRENT = datetime.now(ZoneInfo(P.TIMEZONE)).year
VOTE_CODE = {"Nay": "N", "Excused": "E", "Absent": "A", "Excused for Business of the House": "E"}


def folder(session):
    return os.path.join(P.DATA, P.session_key(session))


def sessions():
    return sorted(int(os.path.basename(f)[:4]) for f in glob.glob(os.path.join(P.DATA, "[0-9]" * 4 + "R1"))
                  if os.path.exists(os.path.join(f, "Measures.json")))


def table(session, name):
    try:
        return json.load(open(os.path.join(folder(session), f"{name}.json")))
    except (OSError, ValueError):
        return []


def text(x):
    return re.sub(r"\s+", " ", x or "").strip()


def titled(relating):
    """ "Relating to firearms; declaring an emergency." -> "Firearms" """
    t = re.sub(r"^relating to\s+", "", text(relating), flags=re.I)
    t = re.sub(r";\s*(?:and\s+)?(?:declaring an emergency|prescribing an effective date|providing for (?:criminal )?sentences?.*|"
               r"amending ORS.*|creating new provisions.*|repealing ORS.*|and declaring an emergency).*$", "", t, flags=re.I)
    t = t.rstrip(".;, ")
    return t[:1].upper() + t[1:]


def digest(summary):
    """The measure summary's plain-language digest, without its readability score."""
    s = text(re.sub(r"<[^>]+>", " ", summary or ""))  # <b>...</b> marks what an amendment added
    s = re.sub(r"\s+([.,;:])", r"\1", s)
    s = re.sub(r"^Digest:\s*", "", s)
    s = re.sub(r"\s*\(Flesch Readability Score:[^)]*\)\.?", "", s)
    return s


def committees(session):
    """Name as the history writes it ("Judiciary", "Ways and Means") and code -> (house "H"/"S"/"J", name, code)."""
    out = {}
    for c in table(session, "Committees"):
        h, name, code = c.get("HouseOfAction"), text(c.get("CommitteeName")), c.get("CommitteeCode")
        out[code] = (h, name, code)
        out.setdefault((h, name.lower()), (h, name, code))
    return out


def find_committee(name, house, comms):
    # "Ways and Means by prior reference"; "Education, then Ways and Means" (the first now, the second after it).
    name = re.sub(r"\s+(?:by order of|by prior reference|with subsequent|and then).*$|,\s*then\s.*$", "", name.strip().rstrip("."), flags=re.I)
    name = re.sub(r"^the\s+", "", name, flags=re.I)
    for h in (house, "J"):
        if (h, name.lower()) in comms:
            return comms[(h, name.lower())]
    return None


def decode(line, house, comms):
    t = text(line)
    m = re.search(r"\b(?:be |and be |subsequent )?referred to ([^.;]+?)(?:\s+by order of[^.]*)?\.?\s*(?:\(Printed [^)]*\))?\.?$", t, re.I)
    if m and not re.search(r"Speaker's desk|President's desk", m.group(1), re.I):
        hit = find_committee(m.group(1), house, comms)
        if hit:
            return f"REFERRED TO {hit[1].upper()}", hit
    if re.match(r"(?:Recommendation:\s*)?(?:Do pass|Without recommendation)", t, re.I):
        return "REPORTED", None
    if re.match(r"Second reading", t, re.I):
        return "PLACED ON FLOOR", None
    # "Passed." alone follows motions made after the third reading ("Motion to refer to Rules failed."); consent-calendar
    # bills pass in one line.
    if re.search(r"\b(?:Third reading|third time)\b.*\bPassed\.?$", t, re.I) or re.fullmatch(r"Passed\.?", t) or \
            re.search(r"concurred in (?:House|Senate) amendments and repassed", t, re.I):
        return f"PASSED {HOUSE[house].upper()}", None
    if re.search(r"\bThird reading\b.*\bFailed\.?$", t, re.I):
        return "FAILED", None
    if re.match(r"(?:Speaker|President) signed", t, re.I):
        return "ENROLLED", None
    if re.match(r"Governor signed|Chapter \d+|Filed with Secretary of State without Governor's signature", t, re.I):
        return "SIGNED", None
    if re.match(r"Governor vetoed|Vetoed by Governor", t, re.I):
        return "VETOED", None
    return t, None


# ---- The same bill in earlier sessions. Bills come back under new numbers each year and the data doesn't link them, so:
# an earlier bill with the same short title whose digest shares at least 60% of its words (40% with the same chief
# sponsor). Up to two years back. Broad titles ("Elections") need the digest to agree.
_EARLIER = {}
_SKIP = {"the", "and", "that", "with", "for", "under", "this", "certain", "act", "takes", "effect", "declares", "emergency",
         "bill", "requires", "allows", "directs", "makes"}


def _session(session):
    if session not in _EARLIER:
        chief = {}
        for s in table(session, "MeasureSponsors"):
            if s.get("SponsorLevel") == "Chief" and s.get("LegislatoreCode"):
                chief.setdefault((s["MeasurePrefix"], s["MeasureNumber"]), s["LegislatoreCode"])
        out = {}
        for m in table(session, "Measures"):
            if m.get("MeasurePrefix") not in ("HB", "SB"):
                continue
            words = set(re.findall(r"[a-z0-9]{3,}", digest(m.get("MeasureSummary")).lower())) - _SKIP
            out[f"{m['MeasurePrefix']}{m['MeasureNumber']}"] = (titled(m.get("RelatingTo")).upper(), words,
                                                                 chief.get((m["MeasurePrefix"], m["MeasureNumber"])))
        _EARLIER[session] = out
    return _EARLIER[session]


def earlier(session, bill):
    out = set()
    me = _session(session).get(bill)
    if not me or len(me[1]) < 5:
        return out
    for y in (session - 1, session - 2):
        if not os.path.exists(os.path.join(folder(y), "Measures.json")):
            continue
        best = None
        for other, (title, words, who) in _session(y).items():
            if title != me[0]:
                continue
            j = len(me[1] & words) / max(1, len(me[1] | words))
            if j >= 0.6 or (j >= 0.4 and who and who == me[2]):
                if not best or j > best[0]:
                    best = (j, other)
        if best:
            out.add((y, best[1]))
    return out


def load_session(session):
    """Read one session's bills and return (records, bill number -> record index, fetched time, delegation)."""
    live = session >= CURRENT
    comms = committees(session)
    measures = [m for m in table(session, "Measures") if m.get("MeasurePrefix") in ("HB", "SB")]
    hist, votes, cvotes, spons = defaultdict(list), defaultdict(list), defaultdict(list), defaultdict(list)
    for h in table(session, "MeasureHistoryActions"):
        hist[(h["MeasurePrefix"], h["MeasureNumber"])].append(h)
    for v in table(session, "MeasureVotes"):
        votes[v.get("MeasureHistoryId")].append(v)
    for v in table(session, "CommitteeVotes"):
        cvotes[(v["MeasurePrefix"], v["MeasureNumber"])].append(v)
    for s in table(session, "MeasureSponsors"):
        spons[(s["MeasurePrefix"], s["MeasureNumber"])].append(s)
    legs = {l["LegislatorCode"]: l for l in table(session, "Legislators")}
    # Members who left or changed houses mid-session ("Rep Neron" became "Sen Neron Misslin") are only in other years'
    # lists: their names from there.
    others = {l["LegislatorCode"]: l for y in sessions() if y != session for l in table(y, "Legislators")}
    seat_of = seats(session)
    stamp = os.path.getmtime(os.path.join(folder(session), "Measures.json"))
    fetched = datetime.fromtimestamp(stamp, ZoneInfo(P.TIMEZONE)).strftime("%Y-%m-%d %H:%M")

    def member(code):
        return seat_of.get(code) or f"{'S' if code.startswith('Sen') else 'H'}?{code.split(' ', 1)[-1]}"

    def person(code):
        l = legs.get(code) or others.get(code)
        return f"{l['FirstName']} {l['LastName']}" if l else code.split(" ", 1)[-1]

    recs, index = [], {}
    for m in sorted(measures, key=lambda m: (m["MeasurePrefix"], m["MeasureNumber"])):
        p = f"{m['MeasurePrefix']}{m['MeasureNumber']}"
        origin = p[0]
        rows = sorted(hist[(m["MeasurePrefix"], m["MeasureNumber"])], key=lambda h: (h.get("ActionDate") or "", h.get("MeasureHistoryId") or 0))
        steps, refs, house = [], [], origin
        for h in rows:
            hh = h.get("Chamber") if h.get("Chamber") in HOUSE else house
            t, hit = decode(h.get("ActionText"), hh, comms)
            if hit:
                refs.append((hh if hit[0] == "J" else hit[0] if hit[0] in HOUSE else hh, hit[1], hit[2]))
            steps.append(((h.get("ActionDate") or "")[:10], hh, t, text(h.get("ActionText")), h.get("MeasureHistoryId")))
            house = hh
        texts = [s[2] for s in steps]
        passed = {s[1] for s in steps if s[2].startswith("PASSED")}
        if "SIGNED" in texts or m.get("ChapterNumber"):
            stage = 5
        elif "VETOED" in texts or m.get("Vetoed"):
            stage = 6
        elif "ENROLLED" in texts:
            stage = 3
        elif passed:
            stage = 2
        else:
            stage = None
        if stage is not None and stage >= 3:
            passed = {"S", "H"}
        where_h, place, committee = origin, "desk", None
        for dd, hh, t, a, _ in steps:
            if t.startswith("REFERRED TO"):
                where_h, place, committee = hh, "committee", t[len("REFERRED TO "):]
            elif t in ("PLACED ON FLOOR",):
                where_h, place, committee = hh, "floor", None
            elif t == "REPORTED" and place == "committee":
                place, committee = "floor", None
            elif t.startswith("PASSED"):
                place, committee = "desk", None
                where_h = "S" if hh == "H" else "H"
        if stage is None:
            stage = 1 if place == "floor" else 0
        proper = {c[1].upper(): c[1] for c in comms.values() if isinstance(c, tuple)}
        committee = proper.get(committee, committee.title() if committee else None)
        last_pass = max(((s[0], s[1]) for s in steps if s[2].startswith("PASSED")), default=None)
        passed_in = HOUSE[last_pass[1]] if stage == 2 and last_pass else None
        comm_list = sorted({f"{h} · {n}" for h, n, _ in refs})
        codes = {c for _, _, c in refs}
        title = titled(m.get("RelatingTo")) or text(m.get("CatchLine"))
        about = digest(m.get("MeasureSummary")) or text(m.get("CatchLine"))
        topics = [k for k, (label, cset, _, _) in P.TOPICS.items()
                  if codes & cset or (k in P.TOPIC_WORDS and P.TOPIC_WORDS[k].search(title + " " + about[:400]))]
        own = [(h, n) for h, n, _ in refs if h == origin]
        first_comms = []
        if own:
            k0 = next(i for i, s in enumerate(steps) if s[2].startswith("REFERRED TO"))
            left = any(s[2] in ("REPORTED", "PLACED ON FLOOR") or s[2].startswith("PASSED") for s in steps[k0 + 1:])
            first_comms.append((origin, own[0][1], left))
        fate = "passed" if "REPORTED" in texts else "none"
        sp = sorted(spons[(m["MeasurePrefix"], m["MeasureNumber"])], key=lambda s: (s.get("SponsorLevel") != "Chief", int(s.get("PrintOrder") or 0)))
        names = []
        for s in sp:
            if s.get("LegislatoreCode"):
                n = person(s["LegislatoreCode"])
                l = legs.get(s["LegislatoreCode"])
                if l and (l.get("Party") or "")[:1] in ("D", "R"):
                    _PARTIES.setdefault(session, {})[(l["Chamber"], n)] = l["Party"][:1]
            elif s.get("CommitteeCode") and s["CommitteeCode"] in comms:
                c = comms[s["CommitteeCode"]]
                n = f"{ {'H': 'House', 'S': 'Senate', 'J': 'Joint'}.get(c[0], '')} {c[1]} Committee".strip()
            else:
                continue
            if n not in names:
                names.append(n)
        # Bills filed before the session "by order of the President" name who asked for them instead ("at the request of
        # Senate Interim Committee on Rules ...", an agency, the governor).
        if not names and m.get("AtTheRequestOf"):
            names = [re.sub(r"^\(?at the request of\s+", "", text(m["AtTheRequestOf"]), flags=re.I).rstrip(")")]
        sponsor = names[0] if names else "—"
        chief = next((legs.get(s.get("LegislatoreCode")) for s in sp if s.get("LegislatoreCode") in legs), None)
        if stage == 0 and committee:
            desc = f"In {HOUSE[where_h]} committee"
        elif stage <= 1 and place == "floor":
            desc = f"On the {HOUSE[where_h]} floor"
        elif stage >= 2:
            desc = {2: f"Passed the {passed_in}", 3: "Passed both houses", 4: "On the governor's desk",
                    5: "Signed into law", 6: "Vetoed"}[stage]
        else:
            desc = steps[-1][3] if steps else "Introduced"

        def dates(test, mode="last"):
            ds = sorted({s[0] for s in steps if test(s[1], s[2], s[3]) and s[0]})
            return {"first": ds[0], "last": ds[-1], "all": ";".join(ds)}[mode] if ds else ""

        out_votes = []
        for dd, hh, t, a, hid in steps:
            vs = votes.get(hid)
            if vs and t.startswith("PASSED") or (vs and t in ("FAILED",)):
                yes = sum(1 for v in vs if v.get("Vote") == "Aye")
                no = sum(1 for v in vs if v.get("Vote") == "Nay")
                out_votes.append([hh, "F", None, dd, yes, no, [[member(v["VoteName"]), VOTE_CODE.get(v.get("Vote"), "A")] for v in vs if v.get("Vote") != "Aye"]])
        by_report = defaultdict(list)
        for v in cvotes[(m["MeasurePrefix"], m["MeasureNumber"])]:
            by_report[(v.get("CommitteeReportId"), v.get("CommitteeCode"), (v.get("MeetingDate") or "")[:10])].append(v)
        for (_, code, dd), vs in sorted(by_report.items(), key=lambda kv: kv[0][2]):
            c = comms.get(code, ("", code, code))
            hh = c[0] if c[0] in HOUSE else origin
            yes = sum(1 for v in vs if v.get("Meaning") == "Aye")
            no = sum(1 for v in vs if v.get("Meaning") == "Nay")
            out_votes.append([hh, "C", c[1], dd, yes, no, [[member(v["VoteName"]), VOTE_CODE.get(v.get("Meaning"), "A")] for v in vs if v.get("Meaning") != "Aye"]])
        out_votes.sort(key=lambda v: v[3])
        action_dates = [s[0] for s in steps if s[0]]
        chapter = m.get("ChapterNumber")
        ver = {"p": p, "sponsor": sponsor, "district": int((chief or {}).get("DistrictNumber") or 0) if chief and person(chief["LegislatorCode"]) == sponsor else 0,
               "cosponsors": names[1:], "primes": 1, "cosp": len(names[1:]), "statusDesc": desc,
               "committee": committee if place == "committee" and stage in (0, 2) else None,
               "actions": [[s[0], s[2]] for s in steps]}
        rec = {
            "nums": [p], "base": [p], "prev": earlier(session, p),
            # The official short title ("Elections") is often broad; the catch line says what the bill does in a sentence.
            "title": title, "summary": text(m.get("CatchLine")), "act": "", "lawCode": "", "law": None, "laws": [],
            "comms": comm_list, "topics": topics, "places": [], "narrow": P.narrow_kind(title),
            "commFate": fate, "mainTopic": topics[0] if topics else "", "local": "local" in topics,
            "senDeleg": False, "asmDeleg": False, "budget": bool(re.search(r"\bbudget\b|appropriations", title, re.I)),
            "passedS": "S" in passed, "passedA": "H" in passed, "program": None,
            "stage": stage, "passedIn": passed_in,
            "chapter": int(re.sub(r"\D", "", str(chapter)) or 0) if chapter and stage == 5 else None,
            "veto": None, "memo": "", "vetoMemo": None,
            "simText": f"{title}. {about}",
            "comm": committee if stage == 0 and place == "committee" else None,
            "first": min(action_dates, default=f"{session}-01-01"),
            "last": max(action_dates, default=f"{session}-01-01"),
            "cosp": len(names[1:]),
            "keyDates": [
                dates(lambda h, t, a: t in ("REPORTED", "PLACED ON FLOOR") and h == origin, "first"),
                dates(lambda h, t, a: t == "PASSED SENATE", "all"),
                dates(lambda h, t, a: t == "PASSED HOUSE", "all"),
                "",
                "",
                dates(lambda h, t, a: t == "SIGNED"),
                dates(lambda h, t, a: t == "VETOED"),
            ],
            "votes": out_votes, "firstComms": first_comms, "vers": [ver],
        }
        index[p] = len(recs)
        recs.append(rec)
    return recs, index, fetched, {"SENATE": [], "ASSEMBLY": []}


def agendas(session):
    """Bills on committee agendas from today on: bill -> [["House Judiciary", "2026-02-03T13:00:00"], ...]."""
    comms = committees(session)
    today = datetime.now(ZoneInfo(P.TIMEZONE)).strftime("%Y-%m-%d")
    out = {}
    for a in table(session, "CommitteeAgendaItems"):
        if not a.get("MeasurePrefix") in ("HB", "SB") or (a.get("MeetingDate") or "") < today:
            continue
        c = comms.get(a.get("CommitteCode"), ("", a.get("CommitteCode"), ""))
        name = f"{ {'H': 'House', 'S': 'Senate', 'J': 'Joint'}.get(c[0], '')} {c[1]}".strip()
        entry = [name, a["MeetingDate"]]
        b = f"{a['MeasurePrefix']}{a['MeasureNumber']}"
        if entry not in out.setdefault(b, []):
            out[b].append(entry)
    return out


_PARTIES = {}


def parties(session, recs):
    return {k: v for k, v in _PARTIES.get(session, {}).items() if v in ("D", "R")}


def seats(session):
    """Legislator code ("Rep Andersen") -> seat id ("H:19"), from data/or/contacts_<session>.json (states/or/contacts.py),
    else from that session's legislator table."""
    path = os.path.join(P.DATA, f"contacts_{session}.json")
    if os.path.exists(path):
        return {p["id"]: sid for sid, p in json.load(open(path))["people"].items() if p.get("id")}
    return {l["LegislatorCode"]: f"{l['Chamber']}:{int(l['DistrictNumber'])}" for l in table(session, "Legislators")
            if str(l.get("DistrictNumber", "")).isdigit()}
