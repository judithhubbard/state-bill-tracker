"""Connecticut's bills (downloaded by states/ct/fetch.py from the General Assembly's FTP server) in the shape
build_data.py reads. One session a year; House and Senate bills only.

The history lines are kept as written except the steps the site's rules use. Committees are joint (both houses'
members), so a referral belongs to the house the bill is in; floor steps name their house ("HOUSE PASSED", "SEN.
PASSED, HO. AMEND. SCH.", "FAV. RPT., TAB. FOR CAL., SEN."). A Public Act number comes when a bill passes both houses,
before the governor acts (HB 7004 of 2025 got one and was vetoed), so it marks passing both houses, not a law; only
"SIGNED BY GOVERNOR" does. The files have no votes.
"""
import csv, glob, io, os, re
from datetime import datetime
from zoneinfo import ZoneInfo

from states.ct import profile as P

HOUSE = {"S": "Senate", "H": "House"}
CURRENT = datetime.now(ZoneInfo(P.TIMEZONE)).year


def folder(session):
    return os.path.join(P.DATA, str(session))


def sessions():
    return sorted(int(os.path.basename(f)) for f in glob.glob(os.path.join(P.DATA, "[0-9]" * 4))
                  if os.path.exists(os.path.join(f, "bill_info.csv")))


def rows(session, name):
    path = os.path.join(folder(session), f"{name}.csv")
    if not os.path.exists(path):
        return []
    raw = open(path, "rb").read()
    # Mostly UTF-8, but a few Windows-1252 bytes (0x96, a dash, in 2026's bill_info): decode as one or the other.
    try:
        body = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        body = raw.decode("cp1252", "replace")
    return [{k.strip(): (v or "").strip() for k, v in r.items() if k} for r in csv.DictReader(io.StringIO(body))]


def titled(t):
    """ "AN ACT CONCERNING ABSENTEE VOTING FOR ALL ..." -> "Absentee voting for all ..." """
    t = re.sub(r"^AN ACT\s+(?:CONCERNING|REGARDING|RELATING TO|ESTABLISHING|IMPLEMENTING|MAKING|ADOPTING|PROHIBITING|REQUIRING|AUTHORIZING)?\s*", "", t.strip(), flags=re.I)
    t = t.rstrip(".").lower()
    t = re.sub(r"\b(connecticut|hartford|new haven|bridgeport|stamford|waterbury|norwalk|danbury|uconn|covid|dss|dcf|dmv)\b",
               lambda m: m.group(1).upper() if len(m.group(1)) <= 4 else m.group(1).title(), t)
    return t[:1].upper() + t[1:]


def committees(session):
    return {r["comm_code"]: re.sub(r"\s+Committee$", "", re.sub(r"^(?:Joint )?Committee on\s+", "", r["comm_name"]))
            for r in rows(session, "committee")}


def legislators(session):
    """Introducer code ("006", "S06") -> (house, full name, district, party letter)."""
    out = {}
    for r in rows(session, "LegislatorDatabase"):
        h = r.get("office code")
        d = r.get("dist", "")
        if h not in ("H", "S") or not d.isdigit():
            continue
        name = " ".join(x for x in (r.get("commonly used name") or r.get("first name"), r.get("last name"), r.get("suffix")) if x and x.strip())
        code = d if h == "H" else f"S{int(d):02d}"
        out[code] = (h, name, int(d), (r.get("party") or "")[:1])
    return out


def decode(line, q1, origin, house, comms):
    """One history line -> (house, shared wording)."""
    up = line.upper()
    names = comms
    if up.startswith("REF. TO JOINT COMM. ON") and q1:
        return house, f"REFERRED TO {names.get(q1, q1).upper()}"
    m = re.match(r"(?:REF\. BY|CHG\. REF\.,|FAV\. CHG\. OF REF\.,?)\s*(HOUSE|SEN\.)\s+TO\s+COMM", up)
    if m and q1:
        return ("H" if m.group(1) == "HOUSE" else "S"), f"REFERRED TO {names.get(q1, q1).upper()}"
    if re.match(r"JOINT FAVORABLE(?! CHANGE)", up) and "CHANGE OF REFERENCE" not in up:
        return house, "REPORTED"
    if re.match(r"(?:FAV\. RPT\., )?TAB(?:LED|\.) FOR (?:HOUSE )?CAL", up):
        return ("S" if "SEN" in up else "H"), "PLACED ON FLOOR"
    if re.match(r"(HOUSE|SENATE|SEN\.) PASSED\b", up):
        return ("H" if up.startswith("HOUSE") else "S"), f"PASSED {'HOUSE' if up.startswith('HOUSE') else 'SENATE'}"
    if re.match(r"(?:TRANSMITTED BY SECRETARY OF THE STATE TO GOVERNOR|RULES SUSPENDED, TRANSMITTED TO THE GOVERNOR|IMMEDIATE TRANSMITTAL TO THE GOV)", up):
        return "G", "DELIVERED TO GOVERNOR"
    if re.match(r"SIGNED BY GOVERNOR|BECAME LAW WITHOUT", up):
        return "G", "SIGNED"
    if re.match(r"VETOED BY GOVERNOR", up):
        return "G", "VETOED"
    if re.match(r"(?:VETO OVERRIDDEN|PASSED OVER VETO|OVERRODE)", up):
        return house, "OVERRIDDEN"
    if re.match(r"(PUBLIC|SPECIAL) ACT$", up):
        return "G", "ACT NUMBER"
    # Kept as written, in sentence case, so "REFERRED TO OLR, OFA" (the research and fiscal offices) can't pass for
    # the shared "REFERRED TO <committee>".
    return house, line[:1].upper() + line[1:].lower() if line.isupper() else line


# ---- The same bill in earlier years. Bills come back under new numbers each year and the files don't link them, so: an
# earlier bill with the same title whose statement of purpose shares at least 60% of its words (40% with the same
# introducer). Up to two years back. Committees' routine bills ("the legislative commissioners' recommendations for
# technical revisions") and budget bills don't match.
_EARLIER = {}
_SKIP = {"the", "and", "that", "with", "for", "under", "this", "certain", "concerning", "provide", "require"}


def _session(session):
    if session not in _EARLIER:
        intro = {}
        for r in rows(session, "introducer"):
            if r.get("intro_type") == "I":
                intro.setdefault(r.get("bill_num"), r.get("intro_code", "").strip())
        out = {}
        for r in rows(session, "bill_info"):
            num = r.get("bill_num", "")
            title = titled(r.get("bill_title", ""))
            if num[:2] not in ("HB", "SB") or re.search(r"technical revisions|appropriations|budget|bonds of the state", title, re.I):
                continue
            words = set(re.findall(r"[a-z0-9]{3,}", (r.get("stmt_purp") or "").lower())) - _SKIP
            out[num[:2] + str(int(num[2:]))] = (title.upper(), words, intro.get(num))
        _EARLIER[session] = out
    return _EARLIER[session]


def earlier(session, bill):
    out = set()
    me = _session(session).get(bill)
    if not me or len(me[1]) < 5:
        return out
    for y in (session - 1, session - 2):
        if not os.path.exists(os.path.join(folder(y), "bill_info.csv")):
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
    legs = legislators(session)
    info = {r["bill_num"]: r for r in rows(session, "bill_info") if r.get("bill_num", "")[:2] in ("HB", "SB")}
    hist = {}
    for r in rows(session, "bill_history"):
        if r.get("bill_num", "")[:2] in ("HB", "SB"):
            hist.setdefault(r["bill_num"], []).append(r)
    intro = {}
    for r in rows(session, "introducer"):
        intro.setdefault(r.get("bill_num"), []).append(r)
    stamp = os.path.getmtime(os.path.join(folder(session), "bill_info.csv"))
    fetched = datetime.fromtimestamp(stamp, ZoneInfo(P.TIMEZONE)).strftime("%Y-%m-%d %H:%M")

    recs, index = [], {}
    for raw_num, b in sorted(info.items(), key=lambda kv: (kv[0][:2], int(re.sub(r"\D", "", kv[0]) or 0))):
        p = raw_num[:2] + str(int(raw_num[2:]))  # "HB05001" -> "HB5001"
        origin = p[0]
        lines = sorted(hist.get(raw_num, []), key=lambda r: (r.get("act_date", ""), int(r.get("sort_order") or 0)))
        house, steps, act_no = origin, [], None
        for r in lines:
            day = (r.get("act_date") or "")[:10]
            line = r.get("act_desc", "")
            h, t = decode(line, r.get("qual1", ""), origin, house, comms)
            if t == "ACT NUMBER":
                act_no = r.get("qual1") or act_no
                t = line
            if h in HOUSE:
                house = h
            if t.startswith("PASSED"):
                house = "S" if h == "H" else "H"  # it goes to the other house next
            steps.append((day, h, t, line))
        texts = [t for _, _, t, _ in steps]
        passed = {h for _, h, t, _ in steps if t.startswith("PASSED")}
        if "SIGNED" in texts or "OVERRIDDEN" in texts:
            stage = 5
        elif "VETOED" in texts:
            stage = 6
        elif "DELIVERED TO GOVERNOR" in texts:
            stage = 4
        elif act_no:
            stage = 3  # the act number comes when both houses have passed the same text (not "disagreeing action")
        elif passed:
            stage = 2
        else:
            stage = None
        if stage is not None and stage >= 3:
            passed = {"S", "H"}
        # Where it is now.
        where_h, place, committee = origin, "desk", None
        for _, h, t, _ in steps:
            if t.startswith("REFERRED TO"):
                where_h, place, committee = (h if h in HOUSE else where_h), "committee", t[len("REFERRED TO "):]
            elif t in ("REPORTED", "PLACED ON FLOOR"):
                where_h, place, committee = (h if h in HOUSE else where_h), "floor", None
            elif t.startswith("PASSED"):
                place, committee = "desk", None
                where_h = "S" if h == "H" else "H"
        if stage is None:
            stage = 1 if place == "floor" else 0
        proper = {v.upper(): v for v in comms.values()}
        committee = proper.get(committee, committee.title() if committee else None)
        last_pass = max(((dd, h) for dd, h, t, _ in steps if t.startswith("PASSED")), default=None)
        passed_in = HOUSE[last_pass[1]] if stage == 2 and last_pass else None
        refs = [(h if h in HOUSE else origin, proper.get(t[len("REFERRED TO "):], t[len("REFERRED TO "):].title()))
                for _, h, t, _ in steps if t.startswith("REFERRED TO")]
        comm_names = {c for _, c in refs}
        comm_codes = {k for k, v in comms.items() if v in comm_names}
        comm_list = sorted({f"{h} · {c}" for h, c in refs})
        title = titled(b.get("bill_title", ""))
        about = b.get("stmt_purp", "")
        topics = [k for k, (label, cset, _, _) in P.TOPICS.items()
                  if comm_codes & cset or (k in P.TOPIC_WORDS and P.TOPIC_WORDS[k].search(title + " " + about))]
        own = [c for h, c in refs if h == origin]
        first_comms = []
        if own:
            k0 = next(i for i, (_, h, t, _) in enumerate(steps) if t.startswith("REFERRED TO"))
            left = any(t in ("REPORTED", "PLACED ON FLOOR") or t.startswith("PASSED") for _, h, t, _ in steps[k0 + 1:])
            first_comms.append((origin, own[0], left))
        fate = "passed" if "REPORTED" in texts or "PLACED ON FLOOR" in texts else "none"
        people = sorted(intro.get(raw_num, []), key=lambda r: (r.get("intro_type") != "I", int(r.get("sort_order") or 0)))
        names = []
        for r in people:
            code = r.get("intro_code", "").strip()
            if code in legs:
                names.append(legs[code][1])
                if legs[code][3] in ("D", "R"):
                    _PARTIES.setdefault(session, {})[(legs[code][0], legs[code][1])] = legs[code][3]
            elif code in comms:
                names.append(f"{comms[code]} Committee")
        sponsor = names[0] if names else "—"
        prime = next((legs[r.get("intro_code", "").strip()] for r in people if r.get("intro_code", "").strip() in legs), None)
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
            ds = sorted({dd for dd, h, t, a in steps if test(h, t, a) and dd})
            return {"first": ds[0], "last": ds[-1], "all": ";".join(ds)}[mode] if ds else ""

        action_dates = [dd for dd, _, _, _ in steps if dd]
        chapter = re.sub(r"\D", "", (act_no or "").split("-")[-1]) if act_no else ""
        ver = {"p": p, "sponsor": sponsor, "district": prime[2] if prime and prime[1] == sponsor else 0,
               "cosponsors": names[1:], "primes": 1, "cosp": len(names[1:]), "statusDesc": desc,
               "committee": committee if place == "committee" and stage in (0, 2) else None,
               "actions": [[dd, t] for dd, _, t, _ in steps]}
        rec = {
            "nums": [p], "base": [p], "prev": earlier(session, p),
            "title": title, "summary": "", "act": "", "lawCode": "", "law": None, "laws": [],
            "comms": comm_list, "topics": topics, "places": [], "narrow": P.narrow_kind(title),
            "commFate": fate, "mainTopic": topics[0] if topics else "", "local": "local" in topics,
            "senDeleg": False, "asmDeleg": False, "budget": bool(re.search(r"\bbudget\b|appropriations", title, re.I)),
            "passedS": "S" in passed, "passedA": "H" in passed, "program": None,
            "stage": stage, "passedIn": passed_in,
            "chapter": int(chapter) if chapter and stage == 5 else None,
            "veto": None, "memo": "", "vetoMemo": None,
            "simText": f"{title}. {about}",
            "comm": committee if stage == 0 and place == "committee" else None,
            "first": min(action_dates, default=f"{session}-01-01"),
            "last": max(action_dates, default=f"{session}-01-01"),
            "cosp": len(names[1:]),
            "keyDates": [
                dates(lambda h, t, a: t in ("REPORTED", "PLACED ON FLOOR"), "first"),
                dates(lambda h, t, a: t == "PASSED SENATE", "all"),
                dates(lambda h, t, a: t == "PASSED HOUSE", "all"),
                "",
                dates(lambda h, t, a: t == "DELIVERED TO GOVERNOR"),
                dates(lambda h, t, a: t == "SIGNED"),
                dates(lambda h, t, a: t == "VETOED"),
            ],
            "votes": [], "firstComms": first_comms, "vers": [ver],
        }
        index[p] = len(recs)
        recs.append(rec)
    return recs, index, fetched, {"SENATE": [], "ASSEMBLY": []}


def agendas(session):
    return {}


_PARTIES = {}


def parties(session, recs):
    return {k: v for k, v in _PARTIES.get(session, {}).items() if v in ("D", "R")}
