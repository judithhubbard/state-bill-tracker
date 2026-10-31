"""Georgia's bills (downloaded by states/ga/fetch.py from the General Assembly's web services) in the shape build_data.py
reads. House and Senate bills of each two-year regular session, and the House and Senate resolutions proposing amendments
to the state Constitution (LegislationType "CA"); other resolutions and special sessions are left out. An amendment needs
two-thirds of each house and then goes to the voters at the next even-year general election (Constitution, Art. X,
Sec. I, Para. II); the governor can't veto it, though passed ones are still "sent to the Governor" and get Act numbers.

Each bill's status history is coded, with the house where the step happened as the code's first letter: HFR/HSR (House
first and second readers: read and sent to committee), SRAR (Senate read and referred), HCFR/SCFR (committee favorably
reported, sometimes "By Substitute"), HTR/STR (third reading), HPA/SPA (passed), HASAS/SAHAS (agreed to the other
house's amendment or substitute), HCA/SCRA (conference report adopted), HSG/SSG (sent to the governor), HDSG/SDSG
(signed), a pseudo-step "Signed Gov" with "Act 73" or "Veto V7", STAB (tabled), HRECM/SR (recommitted). The referrals
don't name the committee: it's the bill's committee in that house. Floor votes are member by member.
"""
import glob, json, os, re
from datetime import datetime
from zoneinfo import ZoneInfo

from states.ga import profile as P

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


def load(session, name, default):
    try:
        return json.load(open(os.path.join(folder(session), name)))
    except (OSError, ValueError):
        return default


def purpose(summary):
    """The long title's purpose: "A BILL to be entitled an Act to amend ... so as to provide for X; to provide ..." ->
    "Provides for X; provides ..." (its verbs in the present tense), up to the stock closing clauses."""
    t = text(summary)
    m = re.search(r"\bso as to (.+)", t, re.I) or re.search(r"^A BILL to be entitled an Act to (.+)", t, re.I)
    if not m:
        return ""
    t = re.split(r";\s*to provide (?:for )?(?:an effective date|related matters)|;\s*to repeal conflicting laws", m.group(1), flags=re.I)[0]
    parts = [p.strip() for p in re.split(r";\s*to ", t) if p.strip()]
    def verb(p):
        w, _, rest = p.partition(" ")
        w = w.lower()
        v = (w[:-1] + "ies") if re.search(r"[^aeiou]y$", w) else (w + "es") if re.search(r"(s|sh|ch|x|z)$", w) else w + "s"
        return f"{v} {rest}".strip()
    out = "; ".join(verb(p) for p in parts[:6])
    return (out[:1].upper() + out[1:]).rstrip(" ;,") + "."


def is_amendment(b):
    """A House or Senate resolution proposing an amendment to the Georgia Constitution (SR 55 of 2023, also typed "CA",
    ratifies a federal amendment)."""
    return (b.get("DocumentType") in ("HR", "SR") and b.get("LegislationType") == "CA"
            and bool(re.match(r"A RESOLUTION proposing (?:an amendment|amendments) to the Constitution", text(b.get("Summary")), re.I)))


def kept(b):
    return b.get("DocumentType") in ("HB", "SB") or is_amendment(b)


def decode(h):
    """One status step -> (house, shared wording)."""
    code, desc = h.get("Code") or "", text(h.get("Description"))
    house = code[:1] if code[:1] in "HS" else "G"
    if code == "Signed Gov":
        return "G", "VETOED" if desc.startswith("Veto") else desc  # "Act 73" (the signing itself is HDSG/SDSG)
    if code in ("HFR", "SRAR", "HRECM", "SR", "SW&C"):
        return house, "REFERRED"
    if code in ("HCFR", "SCFR"):
        return house, "REPORTED"
    if code in ("HCUF", "SCUF"):
        return house, "Committee reported unfavorably"
    if code in ("HTR", "STR", "S2R"):
        return house, "PLACED ON FLOOR"
    if code in ("HPA", "SPA", "SRECP"):
        return house, f"PASSED {HOUSE[house].upper()}"
    if code in ("HTRL", "S3RLT"):
        return house, "FAILED"
    if code in ("HRECO", "SRECO"):
        return house, "RECONSIDERED"
    if code in ("HASAS", "SAHAS", "HCA", "SCRA"):
        return house, "CONCURRED"
    if code in ("HSG", "SSG"):
        return "G", "DELIVERED TO GOVERNOR"
    if code in ("HDSG", "SDSG"):
        return "G", "SIGNED"
    return house, desc


_CAPTIONS = {}


def _captions(session):
    """Caption -> [(bill, first author's member id)] for one session's bills."""
    if session not in _CAPTIONS:
        out = {}
        for f in glob.glob(os.path.join(folder(session), "bills", "*.json")):
            b = json.load(open(f))
            if kept(b):
                a = min(b.get("Authors") or [{}], key=lambda a: int(a.get("Sequence") or 0))
                out.setdefault(text(b.get("Caption")).lower(), []).append((f"{b['DocumentType']}{int(b['Number'])}", a.get("MemberId")))
        _CAPTIONS[session] = out
    return _CAPTIONS[session]


def earlier(session, b):
    """The same bill in the General Assembly before: the same caption, and the same first author or a caption of six
    words or more that only one bill has in each."""
    if session - 2 not in sessions():
        return set()
    k = text(b.get("Caption")).lower()
    who = min(b.get("Authors") or [{}], key=lambda a: int(a.get("Sequence") or 0)).get("MemberId")
    old = _captions(session - 2).get(k, [])
    same = [n for n, m in old if m and m == who]
    if same:
        return {(session - 2, same[0])}
    if len(old) == 1 and len(_captions(session).get(k, [])) == 1 and len(k.split()) >= 6:
        return {(session - 2, old[0][0])}
    return set()


def load_session(session):
    """Read one session's bills and return (records, bill number -> record index, fetched time, delegation)."""
    path = os.path.join(P.DATA, f"contacts_{session}.json")
    people = json.load(open(path))["people"] if os.path.exists(path) else {}
    seat_of = {str(p["id"]): sid for sid, p in people.items() if p.get("id")}
    members = {str(m.get("Id")): m for m in load(session, "members.json", [])}
    parties = _PARTIES.setdefault(session, {})

    def person(a):
        """An author ({"MemberDescription": "Au, Michelle 50th", "MemberId": "4983"}) -> "Michelle Au"."""
        sid = seat_of.get(str(a.get("MemberId")))
        if sid:
            name = people[sid]["name"]
        else:
            d = re.sub(r"\s+\d+\w*$", "", text(a.get("MemberDescription")))
            last, _, first = d.partition(",")
            name = f"{first.strip()} {last.strip()}".strip()
        m = members.get(str(a.get("MemberId"))) or {}
        party = (m.get("Party") or "")[:1] or (people.get(sid, {}).get("party") or "")[:1]
        if party:
            parties[("S" if "Senate" in (a.get("Type") or "") else "H", name)] = party
        return name

    def member(m, h):
        """A voter -> seat id, or "H?Hutchinson" for a member who has since left."""
        sid = seat_of.get(str((m.get("Member") or {}).get("Id")))
        if sid:
            return sid
        last = re.sub(r",.*$", "", text((m.get("Member") or {}).get("Name"))).title()
        return f"{h}?{last}"

    files = glob.glob(os.path.join(folder(session), "bills", "*.json"))
    fetched = datetime.fromtimestamp(max(os.path.getmtime(f) for f in files), ZoneInfo(P.TIMEZONE)).strftime("%Y-%m-%d %H:%M")
    texts, recs, index = {}, [], {}
    for f in sorted(files, key=lambda f: (os.path.basename(f)[0], int(re.sub(r"\D", "", os.path.basename(f)) or 0))):
        b = json.load(open(f))
        if not kept(b):
            continue
        amend = is_amendment(b)
        p = f"{b['DocumentType']}{int(b['Number'])}"
        origin = p[0]
        hist = sorted(b.get("StatusHistory") or [], key=lambda h: (h.get("Date") or "", int(h.get("StatusListingId") or 0)))
        steps = [((h.get("Date") or "")[:10],) + decode(h) + (text(h.get("Description")),) for h in hist]
        comms = {c.get("Type"): c.get("Name") for c in b.get("Committees") or []}
        # Referrals don't name the committee: it's the bill's committee in that house.
        steps = [(d, h, f"REFERRED TO {comms[HOUSE[h]].upper()}" if t == "REFERRED" and comms.get(HOUSE.get(h)) else t, a)
                 for d, h, t, a in steps if not (t == "REFERRED" and not comms.get(HOUSE.get(h)) and a == "House Second Readers")]
        steps = [s for s in steps if s[2] != "REFERRED"]
        if amend:
            # The governor's part is a formality for an amendment: keep the lines as written, not as the steps of a bill.
            steps = [(d, h, (f"Numbered {t}" if re.match(r"Act \d+", t) else f"{a} (the governor can't veto an amendment)"
                             if t in ("DELIVERED TO GOVERNOR", "SIGNED", "VETOED") else t), a) for d, h, t, a in steps]
        passed = set()
        for d, h, t, a in steps:
            if t.startswith("PASSED"):
                passed.add(h)
            elif t == "RECONSIDERED":
                passed.discard(h)
        texts_ = [s[2] for s in steps]
        act = None if amend else re.search(r"\d+", b.get("ActVetoNumber") or "") if any(re.match(r"Act \d+", t) for t in texts_) else None
        if "VETOED" in texts_:
            stage = 6
        elif "SIGNED" in texts_ or act:
            stage = 5
        elif "DELIVERED TO GOVERNOR" in texts_:
            stage = 4
        elif len(passed) == 2 and agreed(steps):
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
        committee = comms.get(HOUSE[where_h]) if committee else None
        refs = [(h, comms.get(HOUSE[h])) for h in "HS" if comms.get(HOUSE[h]) and any(s[1] == h and s[2].startswith("REFERRED TO") for s in steps)]
        refs.sort(key=lambda r: r[0] != origin)
        comm_list = sorted({f"{h} · {c}" for h, c in refs})
        title = text(b.get("Caption"))
        if amend:
            title = "Constitutional amendment: " + re.sub(r"\s*-\s*CA\s*$", "", title).strip(" ;")
        local = b.get("LegislationType") == "LOC"
        topics = [v for k, v in P.COMMITTEE_TOPICS.items() if any(k.lower() in c.lower() for _, c in refs)]
        topics = list(dict.fromkeys((["const"] if amend else []) + (["local"] if local else []) + topics + [k for k in P.TOPIC_WORDS if P.TOPIC_WORDS[k].search(title)]))
        first = next((i for i, s in enumerate(steps) if s[2].startswith("REFERRED TO")), None)
        left = first is not None and any(t in ("REPORTED",) or t.startswith("PASSED") for _, _, t, _ in steps[first + 1:])
        fate = "passed" if left else "defeated" if any(s[2].startswith("Committee reported unfavorably") for s in steps) else "none"
        authors = sorted(b.get("Authors") or [], key=lambda a: int(a.get("Sequence") or 0))
        names = [person(a) for a in authors]
        sponsor = names[0] if names else "—"
        cos = names[1:]
        what = purpose(b.get("Summary"))
        if what:
            texts[p] = {"statement": what, "label": "From the bill's official title"}
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

        # Floor votes on passage (and on agreeing to the other house's changes), member by member.
        days = {(s[1], s[0]) for s in steps if s[2].startswith("PASSED") or s[2] in ("CONCURRED", "FAILED")}
        votes = []
        for v in b.get("Votes") or []:
            h = "S" if v.get("Branch") == "Senate" else "H"
            d = (v.get("Date") or "")[:10]
            cap = re.sub(r"(?:ADOPTION OF )?CONSTITUTIONAL AMENDMENT", "", v.get("Caption") or "")  # an amendment's own passage
            if (h, d) not in days or re.search(r"AMENDMENT|MOTION|TABLE|RECONSIDER|PREVIOUS QUESTION|AGENDA", cap, re.I):
                continue
            full = load(session, os.path.join("votes", f"{v.get('VoteId')}.json"), {})
            # Roll calls list vacant seats as "VACANT".
            names_ = [[member(m, h), "N" if m.get("MemberVoted") == "Nay" else "A"] for m in full.get("Votes") or []
                      if m.get("MemberVoted") != "Yea" and not text((m.get("Member") or {}).get("Name")).upper().startswith("VACANT")]
            votes.append([h, "F", None, d, int(v.get("Yeas") or 0), int(v.get("Nays") or 0), names_])
        action_dates = [s[0] for s in steps if s[0]]
        rec = {
            "nums": [p], "base": [p], "prev": earlier(session, b),
            "title": title, "summary": "", "act": "", "lawCode": "", "law": None, "laws": [],
            "comms": comm_list, "topics": topics, "places": [], "narrow": "place" if local else P.narrow_kind(title),  # local legislation: one city or county
            "commFate": fate, "mainTopic": topics[0] if topics else "", "local": local,
            "senDeleg": False, "asmDeleg": False, "budget": bool(re.search(r"\bGeneral Appropriations\b|\bSupplemental appropriations\b", title, re.I)),
            "passedS": "S" in passed, "passedA": "H" in passed, "program": None,
            "stage": stage, "passedIn": HOUSE.get(lp[1]) if stage == 2 and lp else None,
            "chapter": int(act.group(0)) if act and stage == 5 else None,
            "veto": None, "memo": "", "vetoMemo": None,
            "simText": f"{title} {what}",
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
                      "actions": [[s[0], s[2]] for s in steps], "link": f"https://www.legis.ga.gov/legislation/{b['Id']}"}],
        }
        index[p] = len(recs)
        recs.append(rec)
    json.dump(texts, open(os.path.join(P.DATA, f"texts_{session}.json"), "w"), ensure_ascii=False)
    return recs, index, fetched, {"SENATE": [], "ASSEMBLY": []}


def agreed(steps):
    """Both houses passed it: the same text, unless the second house changed it ("By Substitute", "As Amended") and the
    first hasn't agreed. Agreeing "As Amended" changes it again (the other house must agree in turn), disagreeing leads to
    a conference, and a conference report needs both houses (HB 196 of 2023-24 died in conference after "House Agreed
    Senate Amend or Sub As Amended")."""
    last = max(i for i, s in enumerate(steps) if s[2].startswith("PASSED"))
    pending = bool(re.search(r"Substitute|Amended", steps[last][3], re.I))
    conference = set()
    for d, h, t, a in steps[last + 1:]:
        if re.search(r"Agreed (?:House|Senate) Amend or Sub", a):
            pending = bool(re.search(r"As Amended", a))
        elif re.search(r"Disagreed|Insisted|Conference Committee Appointed", a):
            pending = True
        elif re.search(r"Recede", a):
            pending = False  # it withdrew its own changes, so it agrees to the other house's version (HR 1022 of 2023-24)
        elif re.search(r"Conference (?:Committee )?Report Adopted", a):
            conference.add(h)
            if conference >= {"H", "S"}:
                pending = False
    return not pending


def agendas(session):
    return {}


def parties(session, recs):
    return {k: v for k, v in _PARTIES.get(session, {}).items() if v in ("D", "R")}


def seats(session):
    path = os.path.join(P.DATA, f"contacts_{session}.json")
    return {str(p["id"]): sid for sid, p in json.load(open(path))["people"].items()} if os.path.exists(path) else {}
