"""North Carolina's bills (downloaded by states/nc/fetch.py from ncleg.gov) in the shape build_data.py reads. House and
Senate bills of each two-year session; resolutions and extra sessions are left out.

Each bill page gives sponsors (primary first, with member ids in the current session), attributes (Public or Local),
keywords, the session law ("SL 2025-13"), a table of roll calls and the history: "Ref To Com On X" (or "Ref to the Com on
X, if favorable, Y": X first), "Reptd Fav" / "Reptd Fav Com Substitute", "Passed 2nd Reading", "Passed 3rd Reading" (the
passage), "Concurred In S Com Sub", "Ordered Enrolled", "Ratified", "Pres. To Gov. 6/25/2025", "Signed by Gov.",
"Vetoed", "Veto Overridden", "Ch. SL 2025-13". Every Senate bill is first sent to the Senate Rules Committee, which
decides whether it goes on. Local bills become law when ratified, without the governor, and so do constitutional
amendments, which then go to the voters. There are no summaries in the data (the Legislative Analysis Division's are PDFs).
"""
import glob, json, os, re
from datetime import datetime
from zoneinfo import ZoneInfo

from states.nc import profile as P

HOUSE = {"S": "Senate", "H": "House"}
CURRENT = P.session_of(datetime.now(ZoneInfo(P.TIMEZONE)).year)
_PARTIES = {}


def folder(session):
    return os.path.join(P.DATA, str(session))


def sessions():
    return sorted(int(os.path.basename(f)) for f in glob.glob(os.path.join(P.DATA, "[0-9]" * 4))
                  if len(glob.glob(os.path.join(f, "bills", "*.json"))) > 1000)


def text(x):
    return re.sub(r"\s+", " ", x or "").strip()


def committee(a):
    """"Ref to the Com on Judiciary 1, if favorable, Rules, ..." -> "Judiciary 1"; "Re-ref Com On Finance" -> "Finance"."""
    m = re.search(r"\bCom(?:mittee)? (?:On|on) (.+?)(?:,? if fav|\. If fav|\s*$)", a, re.I) or re.search(r"\bRe-ref to (.+?)(?:\. If fav|,? if fav|\s*$)", a, re.I)
    return m.group(1).strip(" .,") if m else None


def short(name):
    """Each house's Rules Committee by its short name ("Rules and Operations of the Senate" -> "Rules")."""
    return re.sub(r"^Rules(?:, Calendar,)? and Operations of the (?:Senate|House)$", "Rules", name, flags=re.I)


def is_amendment(b):
    return bool(re.match(r"(?:Const(?:itutional)?\.? ?Amend|Constitutional Amendment|An Act to Amend the (?:North Carolina )?Constitution)", text(b.get("title")), re.I)
                or re.search(r"\bCONSTITUTIONAL AMENDMENTS?\b", b.get("keywords") or ""))


def decode(h, amendment):
    """One history line -> (house, shared wording)."""
    a = text(h.get("action"))
    house = {"House": "H", "Senate": "S"}.get(h.get("chamber"), "")
    low = a.lower()
    if re.match(r"(?:re-)?ref(?:erred)?\b|ref to|serial referral to", low) and "stricken" not in low and committee(a):
        return house, f"REFERRED TO {committee(a).upper()}"
    if re.match(r"reptd fav", low):
        return house, "REPORTED"
    if re.match(r"reptd unfav", low):
        return house, "Reported unfavorably"
    if re.match(r"placed on cal|added to calendar|cal pursuant|placed on today's calendar|passed 2nd reading|passed 1st reading$", low) and "1st" not in low:
        return house, "PLACED ON FLOOR"
    if re.match(r"passed (?:2nd & )?3rd reading|passed 2nd & 3rd reading", low):
        return house, f"PASSED {HOUSE.get(house, 'HOUSE').upper()}"
    if re.match(r"failed (?:2nd|3rd) reading", low):
        return house, "FAILED"
    if re.match(r"concurred in", low) or re.match(r"conf rpt adopted|adopted conf rpt|conference report adopted", low):
        return house, "CONCURRED"
    if re.match(r"ordered enrolled|ratified", low):
        return house or "G", "ENROLLED"
    if amendment:
        return house or "G", a  # constitutional amendments never go to the governor
    if re.match(r"pres\. to gov", low):
        return "G", "DELIVERED TO GOVERNOR"
    if re.match(r"signed by gov", low):
        return "G", "SIGNED"
    # Kept as written, so the page says how it became law: "Became Law W/o Signature", and "Veto Overridden" in each
    # house (a law once both have, with its Session Law number).
    if re.match(r"became law w/o signature", low):
        return "G", a
    if re.match(r"veto overridden", low):
        return house or "G", a
    if re.match(r"vetoed", low):
        return "G", "VETOED"
    return house or "G", a


def load_session(session):
    """Read one session's bills and return (records, bill number -> record index, fetched time, delegation)."""
    path = os.path.join(P.DATA, f"contacts_{session}.json")
    if not os.path.exists(path):
        paths = sorted(glob.glob(os.path.join(P.DATA, "contacts_*.json")))
        path = paths[-1] if paths else ""
    people = json.load(open(path))["people"] if path else {}
    current = session == CURRENT
    seat_of = {str(p["id"]): sid for sid, p in people.items() if p.get("id")}
    # Roll-call names: "Adams", or "D. Hall" where two members share a last name.
    by_name = {}
    for sid, p in people.items():
        bare = re.sub(r",?\s+(?:Jr|Sr|II|III|MD)\.?$", "", p["name"]).split()
        last = bare[-1]
        by_name.setdefault((sid[0], last), set()).add(sid)
        if len(bare) > 2:  # "von Haefen", "Carson Smith"
            by_name.setdefault((sid[0], " ".join(bare[-2:])), set()).add(sid)
        by_name[(sid[0], f"{p['name'][0]}. {last}")] = {sid}
    by_name = {k: next(iter(v)) for k, v in by_name.items() if len(v) == 1}
    parties = _PARTIES.setdefault(session, {})
    files = glob.glob(os.path.join(folder(session), "bills", "*.json"))
    fetched = datetime.fromtimestamp(max(os.path.getmtime(f) for f in files), ZoneInfo(P.TIMEZONE)).strftime("%Y-%m-%d %H:%M")
    recs, index = [], {}
    for f in sorted(files, key=lambda f: (os.path.basename(f)[0], int(re.sub(r"\D", "", os.path.basename(f)) or 0))):
        b = json.load(open(f))
        if b.get("kind") not in ("HB", "SB"):
            continue
        p = b["number"]
        origin = p[0]
        other = "S" if origin == "H" else "H"
        amendment = is_amendment(b)
        local = "Local" in (b.get("attributes") or "")
        steps = [(h.get("date") or "",) + decode(h, amendment) + (text(h.get("action")),) for h in b.get("history") or []]
        passed = set()
        for d, h, t, a in steps:
            if t.startswith("PASSED"):
                passed.add(h)
        texts_ = [s[2] for s in steps]
        law = re.search(r"SL (\d{4}-\d+)", b.get("law") or "")
        if amendment:
            stage = 3 if "ENROLLED" in texts_ else None
        elif "SIGNED" in texts_ or (law and "VETOED" not in texts_) or (law and any("Veto Overridden" in s[3] for s in steps)):
            stage = 5
        elif "VETOED" in texts_:
            stage = 6
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
        where_h, place, comm = origin, "desk", None
        for d, h, t, a in steps:
            if t.startswith("REFERRED TO"):
                where_h, place, comm = (h if h in HOUSE else where_h), "committee", t[len("REFERRED TO "):]
            elif t in ("REPORTED", "PLACED ON FLOOR"):
                where_h, place, comm = (h if h in HOUSE else where_h), "floor", None
            elif t.startswith("PASSED"):
                place, comm = "desk", None
                where_h = other if h == origin else origin
        if stage is None:
            stage = 1 if place == "floor" else 0
        proper = lambda c: short(re.sub(r"\b(And|Of|The|On|For|To|In)\b", lambda m: m.group(1).lower(), c.title()))
        comm = proper(comm) if comm else None
        refs = [(s[1] if s[1] in HOUSE else origin, proper(s[2][len("REFERRED TO "):])) for s in steps if s[2].startswith("REFERRED TO")]
        comm_list = sorted({f"{h} · {c}" for h, c in refs})
        title = text(b.get("title")).rstrip(".")
        words = f"{title} {b.get('keywords') or ''}"
        topics = list(dict.fromkeys((["const"] if amendment else []) + (["local"] if local else []) +
                                    [v for k, v in P.COMMITTEE_TOPICS.items() if any(k.lower() in c.lower() for _, c in refs)] +
                                    [k for k in P.TOPIC_WORDS if P.TOPIC_WORDS[k].search(words)]))
        # The first real committee: Senate bills first sit in Rules and Operations of the Senate, which sends them on.
        first = next((r for r in refs if not re.match(r"Rules", r[1])), refs[0] if refs else None)
        left = bool(first) and any(t in ("REPORTED",) or t.startswith("PASSED") for _, _, t, _ in steps)
        fate = "passed" if left else "defeated" if "Reported unfavorably" in texts_ else "none"
        names = []
        for s in (b.get("primary") or []) + (b.get("sponsors") or []):
            sid = seat_of.get(str(s.get("id"))) if current else None
            name = people[sid]["name"] if sid else text(s.get("name"))
            if sid and people[sid].get("party"):
                parties[(sid[0], name)] = people[sid]["party"][:1]
            if name and name not in names:
                names.append(name)
        sponsor = names[0] if names else "—"
        cos = names[1:]
        if stage == 0:
            desc = f"In {HOUSE[where_h]} committee"
        elif stage == 1:
            desc = f"On the {HOUSE[where_h]} floor"
        else:
            desc = {2: f"Passed the {HOUSE[origin] if origin in passed else HOUSE[other]}", 3: "Passed both houses",
                    4: "On the governor's desk", 5: "Became law", 6: "Vetoed"}[stage]

        def dates(test, mode="last"):
            ds = sorted({s[0] for s in steps if test(s[1], s[2]) and s[0]})
            return {"first": ds[0], "last": ds[-1], "all": ";".join(ds)}[mode] if ds else ""

        # Roll calls on passage (second and third readings), concurrence, conference reports and veto overrides; not
        # amendments ("A1 McNeely Second Reading") or motions.
        votes = []
        for v in b.get("voteTable") or []:
            subj = text(v.get("subject"))
            if re.match(r"A\d|M\d+ (?!Concur)", subj) or not re.search(r"(Second|Third) Reading|Concur|Override|RPT Adoption|Adopt", subj) or "Not Concur" in subj:
                continue
            h = "S" if "[S]" in (v.get("rcs") or "") else "H"
            rid = re.sub(r"\D", "", v.get("rcs") or "")
            full = {}
            try:
                full = json.load(open(os.path.join(folder(session), "votes", f"{h}{rid}.json")))
            except (OSError, ValueError):
                pass
            d = full.get("date") or ""
            if not d:
                m = re.match(r"(\d+)/(\d+)/(\d{4})", v.get("time") or "")
                d = f"{m.group(3)}-{int(m.group(1)):02d}-{int(m.group(2)):02d}" if m else ""
            names_ = [[by_name.get((h, text(x.get("name")))) or f"{h}?{text(x.get('name'))}", "N" if x.get("vote") == "Noes" else "A"]
                      # (A vote group with no one in it reads "None" on the page.)
                      for x in full.get("members") or [] if x.get("vote") != "Ayes" and text(x.get("name")) not in ("None", "")]
            votes.append([h, "F", None, d, int(v.get("aye") or 0), int(v.get("no") or 0), names_])
        votes.sort(key=lambda v: v[3])
        action_dates = [s[0] for s in steps if s[0]]
        rec = {
            "nums": [p], "base": [p], "prev": earlier(session, b),
            "title": title, "summary": "", "act": "", "lawCode": "", "law": None, "laws": [],
            "comms": comm_list, "topics": topics, "places": [], "narrow": "place" if local else P.narrow_kind(title),
            "commFate": fate, "mainTopic": topics[0] if topics else "", "local": local,
            "senDeleg": False, "asmDeleg": False, "budget": bool(re.search(r"\bappropriations? act\b|\bbudget\b", title, re.I)),
            "passedS": "S" in passed, "passedA": "H" in passed, "program": None,
            "stage": stage, "passedIn": (HOUSE[origin] if origin in passed else HOUSE[other]) if stage == 2 else None,
            "chapter": int(law.group(1).split("-")[1]) if law and stage == 5 else None,
            "veto": None, "memo": "", "vetoMemo": None,
            "simText": words,
            "comm": comm if stage == 0 and place == "committee" else None,
            "first": min(action_dates, default=f"{session}-01-01"),
            "last": max(action_dates, default=f"{session}-01-01"),
            "cosp": len(cos),
            "keyDates": [
                dates(lambda h, t: t == "REPORTED", "first"),
                dates(lambda h, t: t == "PASSED SENATE", "all"),
                dates(lambda h, t: t == "PASSED HOUSE", "all"),
                "",
                dates(lambda h, t: t == "DELIVERED TO GOVERNOR"),
                dates(lambda h, t: t == "SIGNED" or bool(re.match(r"Became Law W/o Signature|Veto Overridden", t, re.I)))
                or (dates(lambda h, t: t == "ENROLLED") if stage == 5 else ""),
                dates(lambda h, t: t == "VETOED"),
            ],
            "votes": votes, "firstComms": [(first[0], first[1], left)] if first else [],
            "vers": [{"p": p, "sponsor": sponsor, "district": 0, "cosponsors": cos, "primes": len(b.get("primary") or []) or 1,
                      "cosp": len(cos), "statusDesc": desc, "committee": comm if place == "committee" and stage in (0, 2) else None,
                      "actions": [[s[0], s[2]] for s in steps]}],
        }
        index[p] = len(recs)
        recs.append(rec)
    return recs, index, fetched, {"SENATE": [], "ASSEMBLY": []}


_TITLES = {}


def _titles(session):
    if session not in _TITLES:
        out = {}
        for f in glob.glob(os.path.join(folder(session), "bills", "[HS]*.json")):
            b = json.load(open(f))
            if b.get("kind") in ("HB", "SB"):
                sp = text(((b.get("primary") or [{}])[0]).get("name")).split()[-1:] or [""]
                out.setdefault(text(b.get("title")).lower().rstrip("."), []).append((b["number"], sp[0].lower()))
        _TITLES[session] = out
    return _TITLES[session]


def earlier(session, b):
    """The same bill in the session before: the same title, and the same first primary sponsor's last name or a title only
    one bill has in each session."""
    if session - 2 not in sessions():
        return set()
    k = text(b.get("title")).lower().rstrip(".")
    who = (text(((b.get("primary") or [{}])[0]).get("name")).split()[-1:] or [""])[0].lower()
    old = _titles(session - 2).get(k, [])
    same = [n for n, sp in old if sp and sp == who]
    if same:
        return {(session - 2, same[0])}
    if len(old) == 1 and len(_titles(session).get(k, [])) == 1 and len(k.split()) >= 4:
        return {(session - 2, old[0][0])}
    return set()


def agendas(session):
    return {}


def parties(session, recs):
    return {k: v for k, v in _PARTIES.get(session, {}).items() if v in ("D", "R")}
