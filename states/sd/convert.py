"""South Dakota's bills (downloaded by states/sd/fetch.py from the Legislature's JSON API) in the shape build_data.py
reads. House and Senate bills of each year's regular session, plus the joint resolutions that propose constitutional
amendments; other resolutions and commemorations are left out.

Each action has a numeric kind (ActionId), the committee that acted (ActionCommittee, with FullBody true for the whole
House or Senate), the committee it was sent to (AssignedCommittee), a result (P passed, F failed) and its vote's id.
"Do Pass" (20), "Do Pass Amended" (21) and "Do Pass" on the consent calendar (191) are a committee's report when a
committee acts and the house's passage when the whole house does. 67/68/131/69/70/102 are referrals; 167/168/185 skip
the committee; "Deferred to the 41st legislative day" (28) and "Tabled" (26) in committee kill a bill (there are only 40);
91 is concurring in the other house's amendments, 93 adopting a conference report; 7/8 the presiding officers' signatures
(both houses agreed), 10 delivered to the governor, 9 signed, 14 vetoed, 17 a veto override. Votes are member by member
(votes/<id>.json, by SessionMemberId). There are no summaries: the title is the act's own one-line description
("provide for prescribed burning of state-owned land ...").
"""
import glob, html, json, os, re
from datetime import datetime
from zoneinfo import ZoneInfo

from states.sd import profile as P
from states.sd.contacts import seats

HOUSE = {"S": "Senate", "H": "House"}
CURRENT = P.session_of(datetime.now(ZoneInfo(P.TIMEZONE)).year)
_PARTIES = {}
PASS = (20, 21, 191)
REFER = (67, 68, 131, 69, 70, 102)
SKIP_COMMITTEE = (167, 168, 185)


def folder(session):
    return os.path.join(P.DATA, str(session))


def sessions():
    return sorted(int(os.path.basename(f)) for f in glob.glob(os.path.join(P.DATA, "[0-9]" * 4))
                  if len(glob.glob(os.path.join(f, "bills", "*.json"))) > 100 and os.path.exists(os.path.join(f, "members.json")))


def text(x):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", x or ""))).strip()


def comm_name(c):
    """"House Agriculture and Natural Resources", "Senate Committee on Appropriations" -> the committee's own name."""
    return re.sub(r"^(?:House|Senate|Joint) (?:Committee on )?", "", text((c or {}).get("FullName") or (c or {}).get("Name")))


def decode(a):
    """One action -> (house, shared wording, as written)."""
    ac = a.get("ActionCommittee") or {}
    h = ac.get("Body") if ac.get("Body") in HOUSE else "G"
    whole = bool(ac.get("FullBody"))
    k, r = a.get("ActionId"), a.get("Result")
    raw = text(a.get("StatusText"))
    assigned = a.get("AssignedCommittee")
    if k in REFER and assigned:
        h2 = assigned.get("Body") if assigned.get("Body") in HOUSE else h
        return h2, f"REFERRED TO {comm_name(assigned).upper()}", f"{raw} {text(assigned.get('FullName'))}"
    if k in SKIP_COMMITTEE:
        return h, "PLACED ON FLOOR", raw
    if k in PASS + (35, 36) and not whole:
        if r == "P":
            return h, "REPORTED", f"{text(ac.get('FullName'))}: {raw}"
        return h, f"{text(ac.get('FullName'))}: {raw} (failed)", f"{text(ac.get('FullName'))}: {raw} (failed)"
    if k in (28, 26) and not whole and r == "P":
        return h, "KILLED IN COMMITTEE", f"{text(ac.get('FullName'))}: {raw}"
    if k == 203:
        return h, "PLACED ON FLOOR", raw
    if k in PASS and whole:
        line = f"{HOUSE.get(h, '')} {raw.lower()}" + ("" if r == "P" else " (failed)")
        return h, (f"PASSED {HOUSE[h].upper()}" if r == "P" else "FAILED"), line.strip()
    if k == 58 and whole and r == "P":
        return h, "RECONSIDERED", f"{HOUSE.get(h, '')} reconsidered its vote".strip()
    if k in (91, 93) and h not in HOUSE:  # the conference committee's own vote, not a house's
        return "G", f"Conference committee: {raw.lower()}", f"Conference committee: {raw.lower()}"
    if k == 91 and r == "P":
        return h, "CONCURRED", f"{HOUSE.get(h, '')} concurred in amendments".strip()
    if k == 93 and r == "P":
        return h, "CONFERENCE REPORT ADOPTED", f"{HOUSE.get(h, '')} adopted the conference committee report".strip()
    if k in (7, 8):
        return h, "ENROLLED", raw
    if k == 10:
        return "G", "DELIVERED TO GOVERNOR", raw
    if k == 9:
        return "G", "SIGNED", raw
    if k == 14:
        return "G", "VETOED", raw
    if k == 17:
        line = f"{HOUSE.get(h, '')} {'voted to override' if r == 'P' else 'failed to override'} the veto"
        return h, ("OVERRIDDEN" if r == "P" else line), line
    return h, raw, raw


def is_amendment(d):
    return d.get("BillType") in ("HJR", "SJR") and bool(re.search(r"amend(?:ment|ing)? .*constitution|constitutional amendment", text(d.get("Title")), re.I))


def load_session(session):
    """Read one year's bills and return (records, bill number -> record index, fetched time, delegation)."""
    path = os.path.join(P.DATA, f"contacts_{session}.json")
    if not os.path.exists(path):
        paths = sorted(glob.glob(os.path.join(P.DATA, "contacts_*.json")))
        path = paths[-1] if paths else ""
    contacts = json.load(open(path)) if path else {}
    people = contacts.get("people", {})
    members = json.load(open(os.path.join(folder(session), "members.json")))
    seat_of = seats(members)
    member = {m["SessionMemberId"]: m for m in members}
    parties = _PARTIES.setdefault(session, {})
    files = glob.glob(os.path.join(folder(session), "bills", "*.json"))
    fetched = datetime.fromtimestamp(max(os.path.getmtime(f) for f in files), ZoneInfo(P.TIMEZONE)).strftime("%Y-%m-%d %H:%M")
    recs, index = [], {}
    for f in sorted(files, key=lambda f: (os.path.basename(f)[0], int(re.sub(r"\D", "", os.path.basename(f)) or 0))):
        b = json.load(open(f))
        d, listing = b.get("detail") or {}, b.get("listing") or {}
        kind = d.get("BillType") or listing.get("BillType")
        amendment = is_amendment(d)
        if kind not in ("HB", "SB") and not amendment:
            continue
        p = f"{kind}{int(d.get('BillNumber') or listing.get('BillNumberOnly'))}"
        origin = p[0]
        other = "S" if origin == "H" else "H"
        acts = sorted(b.get("ActionLog") or [], key=lambda a: ((a.get("ActionDate") or "")[:10], a.get("StatusSort") or 0))
        steps = [((a.get("ActionDate") or "")[:10],) + decode(a) for a in acts]
        texts_ = [s[2] for s in steps]
        passed = set()
        for _, h, t, _ in steps:  # in order: a reconsidered vote no longer counts (HB 1113 of 2026 then failed)
            if t.startswith("PASSED"):
                passed.add(h)
            elif t == "RECONSIDERED":
                passed.discard(h)
        if "OVERRIDDEN" in texts_:
            passed = {"S", "H"}
        # Agreement: the presiding officers' signatures, the first house concurring, or both houses adopting a conference
        # report (HB 1140 of 2024: the Senate adopted it, the House didn't).
        agreed = ("ENROLLED" in texts_ or "CONCURRED" in texts_
                  or {s[1] for s in steps if s[2] == "CONFERENCE REPORT ADOPTED"} >= {"S", "H"})
        overridden = {s[1] for s in steps if s[2] == "OVERRIDDEN"} >= {"S", "H"}
        if amendment:
            stage = 3 if len(passed) == 2 and agreed else None
        elif "SIGNED" in texts_ or overridden:
            stage = 5
        elif "VETOED" in texts_:
            stage = 6
        elif "DELIVERED TO GOVERNOR" in texts_:
            stage = 4
        elif len(passed) == 2 and agreed:
            stage = 3
        elif passed:
            stage = 2
        else:
            stage = None
        if stage is not None and stage >= 3:
            passed = {"S", "H"}
        where_h, place, comm = origin, "desk", None
        for _, h, t, _ in steps:
            if t.startswith("REFERRED TO"):
                where_h, place, comm = (h if h in HOUSE else where_h), "committee", t[len("REFERRED TO "):]
            elif t in ("REPORTED", "PLACED ON FLOOR"):
                where_h, place, comm = (h if h in HOUSE else where_h), "floor", None
            elif t.startswith("PASSED"):
                place, comm = "desk", None
                where_h = other if h == origin else origin
        if stage is None:
            stage = 1 if place == "floor" else 0
        proper = lambda c: re.sub(r"\b(And|Of|The|On|For|To|In)\b", lambda m: m.group(1).lower(), c.title())
        comm = proper(comm) if comm else None
        refs = [(s[1] if s[1] in HOUSE else origin, proper(s[2][len("REFERRED TO "):])) for s in steps if s[2].startswith("REFERRED TO")]
        comm_list = sorted({f"{h} · {c}" for h, c in refs})
        raw_title = text(d.get("Title") or listing.get("Title"))
        title = re.sub(r",? and (?:to )?declare an emergency\.?$|\.$", "", raw_title)
        title = title[:1].upper() + title[1:]
        long_title = f"An Act to {raw_title}"
        keywords = [k.get("Keyword") for k in d.get("Keywords") or []]
        topics = list(dict.fromkeys((["const"] if amendment else []) +
                                    [P.KEYWORD_TOPICS[k] for k in keywords if k in P.KEYWORD_TOPICS] +
                                    [v for k, v in P.COMMITTEE_TOPICS.items() if any(c.lower().startswith(k.lower()) for _, c in refs)] +
                                    [k for k in P.TOPIC_WORDS if P.TOPIC_WORDS[k].search(title)]))
        left = any(t == "REPORTED" or t.startswith("PASSED") for _, _, t, _ in steps)
        fate = ("passed" if left else "held" if "KILLED IN COMMITTEE" in texts_
                else "defeated" if any(t.endswith("(failed)") for t in texts_) else "none")
        names = []
        for s in sorted(d.get("BillSponsor") or [], key=lambda s: s.get("SponsorType") != "P"):
            m = member.get(s.get("SessionMemberId")) or {}
            mm = s.get("Member") or {}
            full = re.sub(r"\s+", " ", f"{mm.get('FirstName') or m.get('FirstName') or ''} {mm.get('LastName') or m.get('LastName') or ''}").strip()
            if s.get("Politics") in ("D", "R"):
                parties[(s.get("MemberType"), full)] = s["Politics"]
            if full and full not in names:
                names.append(full)
        if not names:  # a committee bill: "The Chair of the Committee on Judiciary at the request of the Chief Justice"
            c = text(d.get("BillCommitteeSponsor"))
            m = re.match(r"The Chair of the (?:Committee on )?(.+?)(?: at the request of (.+))?$", c)
            names = [f"{m.group(1)} Committee" if m and not m.group(1).endswith("Committee") else m.group(1) if m else (c or "—")]
        sponsor, cos = names[0], names[1:]
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

        votes = []
        for a in acts:
            v = a.get("Vote") or {}
            ac = a.get("ActionCommittee") or {}
            h = ac.get("Body")
            if not v.get("VoteId") or h not in HOUSE or a.get("ActionId") in (37, 84, 82, 5, 141, 61):
                continue  # amendments, deferrals and procedural motions aren't shown
            try:
                rolls = json.load(open(os.path.join(folder(session), "votes", f"{v['VoteId']}.json"))).get("RollCalls") or []
            except (OSError, ValueError):
                rolls = []
            names_ = []
            for rc in rolls:
                how = (rc.get("Vote1") or "").lower()
                if how.startswith("yea"):
                    continue
                sid = seat_of.get(rc.get("SessionMemberId")) or f"{h}?{rc.get('UniqueName') or rc.get('LastName')}"
                names_.append([sid, "N" if how.startswith("nay") else "A"])
            whole = bool(ac.get("FullBody"))
            votes.append([h, "F" if whole else "C", None if whole else proper(comm_name(ac)), (a.get("ActionDate") or "")[:10],
                          int(v.get("Yeas") or 0), int(v.get("Nays") or 0), names_])
        action_dates = [s[0] for s in steps if s[0]]
        rec = {
            "nums": [p], "base": [p], "prev": earlier(session, d, p),
            "title": title, "summary": long_title, "act": "", "lawCode": "", "law": None, "laws": [],
            "comms": comm_list, "topics": topics, "places": [], "narrow": P.narrow_kind(title),
            "commFate": fate, "mainTopic": topics[0] if topics else "", "local": "local" in topics,
            "senDeleg": False, "asmDeleg": False, "budget": bool(re.search(r"general appropriations act", raw_title, re.I)),
            "passedS": "S" in passed, "passedA": "H" in passed, "program": None,
            "stage": stage, "passedIn": (HOUSE[origin] if origin in passed else HOUSE[other]) if stage == 2 else None,
            "chapter": None, "veto": None, "memo": "", "vetoMemo": None,
            "simText": f"{title} {' '.join(keywords)}",
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
                dates(lambda h, t: t in ("SIGNED", "OVERRIDDEN")),
                dates(lambda h, t: t == "VETOED"),
            ],
            "votes": votes, "firstComms": [(refs[0][0], refs[0][1], left)] if refs else [],
            "vers": [{"p": p, "sponsor": sponsor, "district": 0, "cosponsors": cos, "primes": 1, "cosp": len(cos),
                      "statusDesc": desc, "committee": comm if place == "committee" and stage in (0, 2) else None,
                      "actions": [[s[0], s[2] if s[2].isupper() else s[3]] for s in steps],
                      "link": f"https://sdlegislature.gov/Session/Bill/{d.get('BillId') or listing.get('BillId')}"}],
        }
        index[p] = len(recs)
        recs.append(rec)
    return recs, index, fetched, {"SENATE": [], "ASSEMBLY": []}


_TITLES = {}


def _titles(session):
    """An earlier year's bills that didn't become law, by title: [(number, prime sponsor's member id)]."""
    if session not in _TITLES:
        out = {}
        for f in glob.glob(os.path.join(folder(session), "bills", "*.json")):
            b = json.load(open(f))
            d = b.get("detail") or {}
            if any(a.get("ActionId") == 9 for a in b.get("ActionLog") or []):
                continue  # a law isn't tried again
            sp = next((s.get("Member", {}).get("UniqueName") for s in d.get("BillSponsor") or [] if s.get("SponsorType") == "P"), "")
            key = re.sub(r"\W+", " ", text(d.get("Title")).lower()).strip()
            out.setdefault(key, []).append((f"{d.get('BillType')}{d.get('BillNumber')}", sp))
        _TITLES[session] = out
    return _TITLES[session]


def earlier(session, d, p):
    """The same bill in the two years before: the same title, with the same prime sponsor, or a title only one bill has in
    each year."""
    out = set()
    k = re.sub(r"\W+", " ", text(d.get("Title")).lower()).strip()
    who = next((s.get("Member", {}).get("UniqueName") for s in d.get("BillSponsor") or [] if s.get("SponsorType") == "P"), "")
    if len(k.split()) < 4:
        return out
    for y in (session - 1, session - 2):
        if y not in sessions():
            continue
        old = _titles(y).get(k, [])
        same = [n for n, sp in old if sp and sp == who]
        if same:
            out.add((y, same[0]))
        elif len(old) == 1:
            out.add((y, old[0][0]))
    return out


def agendas(session):
    return {}


def parties(session, recs):
    return {k: v for k, v in _PARTIES.get(session, {}).items() if v in ("D", "R")}
