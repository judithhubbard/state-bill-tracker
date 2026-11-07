"""Colorado's bills (downloaded by states/co/fetch.py from leg.colorado.gov) in the shape build_data.py reads. House and
Senate bills of each year's regular session. Concurrent resolutions, which propose constitutional amendments, aren't in
the download (its search reads bills only).

History lines name their house and are regular: "Introduced In House - Assigned to Business Affairs & Labor + Finance"
(the first committee; the rest are listed in order), "House Committee on Finance Refer Amended to Appropriations" (it
approved the bill and sent it on, or "to House Committee of the Whole" for the floor; "- Consent Calendar" too),
"House Committee on Judiciary Postpone Indefinitely" (the committee killed it), "... Lay Over Unamended - Amendment(s)
Failed" (held), "House Second Reading ... Passed" (the floor's first vote), "House Third Reading Passed" (the passage;
"Lost" a defeat, "Reconsidered" undone), "House Considered Senate Amendments - Result was to Concur - Repass" (agreeing),
"... First Conference Committee Report result was to Adopt Committee Report - Repass" (needed in both houses), "Signed by
the Speaker of the House" / "... President of the Senate" (both houses agreed), "Sent to the Governor", "Governor
Signed", "Governor Vetoed", "Vote to Override Passed". A bill's status ("Became Law", "Lost", "Did Not Become Law") and
session law chapter confirm the end. "What it does" is the summary Legislative Council Staff write ("The act:" and a
list). Floor votes name members by surname ("Gonzales J." where two share it); committee votes by full name.
"""
import glob, json, os, re
from datetime import datetime
from zoneinfo import ZoneInfo

from fetch_contacts import name_key
from states.co import profile as P

HOUSE = {"S": "Senate", "H": "House"}
CURRENT = P.session_of(datetime.now(ZoneInfo(P.TIMEZONE)).year)
_PARTIES = {}


def folder(session):
    return os.path.join(P.DATA, str(session))


def sessions():
    return sorted(int(os.path.basename(f)) for f in glob.glob(os.path.join(P.DATA, "[0-9]" * 4))
                  if len(glob.glob(os.path.join(f, "bills", "*.json"))) > 300)


def text(x):
    return re.sub(r"\s+", " ", x or "").strip()


def decode(h, a):
    """One history line -> (house letter, shared wording)."""
    house = {"House": "H", "Senate": "S"}.get(h, "G")
    m = re.match(r"Introduced In (House|Senate) - Assigned to (.+)$", a)
    if m:
        return m.group(1)[0], f"REFERRED TO {m.group(2).split(' + ')[0].strip().upper()}"
    m = re.match(r"(House|Senate) Committee on (.+?) Refer (?:Amended|Unamended)(?: - Consent Calendar)? to (.+)$", a)
    if m:
        dest = m.group(3).strip()
        if re.search(r"Committee of the Whole", dest):
            return m.group(1)[0], "REPORTED"
        return m.group(1)[0], f"REPORTED|REFERRED TO {dest.upper()}"
    if re.match(r"(House|Senate) Committee on .+ Postpone Indefinitely$", a):
        return house, "Committee voted it down"
    if re.match(r"(House|Senate) Committee on .+ Lay Over", a):
        return house, "HELD"
    if re.match(r"(House|Senate) Third Reading Passed", a):
        return house, f"PASSED {HOUSE[house].upper()}"
    if re.match(r"(House|Senate) Third Reading Reconsidered", a):
        return house, "RECONSIDERED"
    if re.match(r"(House|Senate) (?:Second|Third) Reading (?:Special Order - )?Lost", a):
        return house, "FAILED"
    if re.match(r"(House|Senate) Second Reading .*Passed", a):
        return house, "PLACED ON FLOOR"
    if re.match(r"(House|Senate) Considered (?:House|Senate) Amendments - Result was to Concur", a):
        return house, "CONCURRED"
    if re.search(r"Conference Committee Report result was to Adopt", a):
        return house, "CONFERENCE REPORT ADOPTED"
    if re.match(r"Signed by the (?:Speaker of the House|President of the Senate)", a):
        return house, "ENROLLED"
    if a == "Sent to the Governor":
        return "G", "DELIVERED TO GOVERNOR"
    if re.match(r"Governor Signed|Became Law Without", a):
        return "G", "SIGNED"
    if re.match(r"Governor Vetoed", a):
        return "G", "VETOED"
    if re.match(r"(?:House|Senate) Vote to Override Passed", a):
        return house, "OVERRIDDEN"
    return house, a


def what_it_does(b):
    """The Legislative Council Staff summary: "The act:" or "The bill:" and its list, as lines."""
    out = []
    for kind, t in b.get("summary") or []:
        t = text(t)
        if not t or t.startswith("(Note:") or re.match(r"(?:The (?:act|bill)(?: [^:]{0,40})?:|APPROVED by Governor|EFFECTIVE)", t) and len(t) < 60:
            continue
        # A summary of an interim committee's bill starts with the committee's name ("Legislative Oversight Committee
        # Concerning the Treatment of ... Systems. Under existing law, ...").
        t = re.sub(r"^[A-Z][^.]{0,200}\bCommittee\b[^.]{0,200}\.\s+(?=(?:Under|Current|Existing|The bill|The act|Section)\b)", "", t)
        t = re.sub(r"[;,]?\s*(?:\band|\bor)?\s*[;,]?\s*$", "", t)
        out.append(t[:1].upper() + t[1:] + ("" if t.endswith((".", ":")) else "."))
    return "\n".join(out[:8])


def load_session(session):
    """Read one year's bills and return (records, bill number -> record index, fetched time, delegation)."""
    path = os.path.join(P.DATA, f"contacts_{session}.json")
    if not os.path.exists(path):
        paths = sorted(glob.glob(os.path.join(P.DATA, "contacts_*.json")))
        path = paths[-1] if paths else ""
    people = json.load(open(path))["people"] if path else {}
    by_slug = {p["id"]: (sid, p) for sid, p in people.items()}
    # Floor votes: "Pelton B." where two share a surname, else the surname; committee votes: the full name.
    # Everyone on that year's member list, members who resigned included (the contacts keep one person per seat). The
    # list gives each member's house and district as they stand today, so a member who has since moved to the other
    # house (Lisa Frizell, a representative in 2024) matches no one in the vote's house and is shown by name.
    by_floor, by_full = {}, {}
    try:
        roster = json.load(open(os.path.join(folder(session), "members.json")))["members"]
    except (OSError, ValueError):
        roster = []
    for m in roster:
        h = {"Senator": "S", "Representative": "H"}.get(m.get("title"))
        if not h or not str(m.get("district") or "").isdigit():
            continue
        sid = f"{h}:{int(m['district'])}"
        last, _, first = (m.get("name") or "").partition(", ")
        full = (m.get("page") or {}).get("fullName") or f"{first} {last}"
        for k in (last, f"{last} {first[:1]}."):
            by_floor.setdefault((h, k), set()).add(sid)
        by_full.setdefault(name_key(full), set()).add(sid)
    by_floor = {k: next(iter(v)) for k, v in by_floor.items() if len(v) == 1}
    by_full = {k: next(iter(v)) for k, v in by_full.items() if len(v) == 1}
    parties = _PARTIES.setdefault(session, {})
    files = glob.glob(os.path.join(folder(session), "bills", "*.json"))
    fetched = datetime.fromtimestamp(max(os.path.getmtime(f) for f in files), ZoneInfo(P.TIMEZONE)).strftime("%Y-%m-%d %H:%M")
    texts, recs, index = {}, [], {}
    for f in sorted(files, key=lambda f: (os.path.basename(f)[0], int(re.sub(r"\D", "", os.path.basename(f).split("-")[-1]) or 0))):
        b = json.load(open(f))
        m = re.match(r"([HS]B)\d\d-(\d+)$", b.get("number") or "")
        # House bills are numbered from 1001: a shorter "HB25-104" is a stray page the site answers for a link cut short.
        if not m or b.get("type") != "Bill" or (m.group(1) == "HB" and int(m.group(2)) < 1000):
            continue
        p = f"{m.group(1)}{int(m.group(2))}"
        origin = p[0]
        other = "S" if origin == "H" else "H"
        steps = []
        # The page lists the history newest first, but not always in date order: sorted by day, the page's order kept
        # (reversed) within a day.
        for h in sorted(reversed(b.get("history") or []), key=lambda h: h.get("date") or ""):
            house, t = decode(h.get("chamber"), text(h.get("action")))
            for part in t.split("|"):
                steps.append((h.get("date") or "", house, part, text(h.get("action"))))
        passed = set()
        for _, house, t, _ in steps:
            if t.startswith("PASSED"):
                passed.add(house)
            elif t == "RECONSIDERED":
                passed.discard(house)
        texts_ = [s[2] for s in steps]
        status = b.get("status") or ""
        laws = b.get("sessionLaws") or []
        # An override needs both houses (SB 25-086: the Senate overrode the veto, the House didn't).
        overridden = {s[1] for s in steps if s[2] == "OVERRIDDEN"} >= {"S", "H"}
        if b.get("outcome") == "signed" or status == "Became Law" or overridden:
            stage = 5
        elif b.get("outcome") == "vetoed" or "VETOED" in texts_:
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
        for _, house, t, _ in steps:
            if t.startswith("REFERRED TO"):
                where_h, place, comm = (house if house in HOUSE else where_h), "committee", t[len("REFERRED TO "):]
            elif t in ("REPORTED", "PLACED ON FLOOR"):
                where_h, place, comm = (house if house in HOUSE else where_h), "floor", None
            elif t.startswith("PASSED"):
                place, comm = "desk", None
                where_h = other if house == origin else origin
        if stage is None:
            stage = 1 if place == "floor" else 0
        proper = lambda c: re.sub(r"\b(And|Of|The|On|For|To|In)\b", lambda m: m.group(1).lower(), c.title()).replace(" & ", " & ")
        names_by_upper = {c["name"].upper(): c["name"] for h_ in ("house", "senate") for c in (b.get("committees") or {}).get(h_) or []}
        nice = lambda c: names_by_upper.get(c, proper(c)) if c else None
        comm = nice(comm)
        refs = [(s[1] if s[1] in HOUSE else origin, nice(s[2][len("REFERRED TO "):])) for s in steps if s[2].startswith("REFERRED TO")]
        comm_list = sorted({f"{h} · {c}" for h, c in refs})
        title = text(b.get("short")) or text(b.get("title"))
        long_title = text(b.get("title"))
        subjects = b.get("subjects") or []
        topics = list(dict.fromkeys([P.SUBJECT_TOPICS[s] for s in subjects if s in P.SUBJECT_TOPICS] +
                                    [v for k, v in P.COMMITTEE_TOPICS.items() if any(c and c.startswith(k) for _, c in refs)] +
                                    [k for k in P.TOPIC_WORDS if P.TOPIC_WORDS[k].search(f"{title} {long_title}")]))
        first = refs[0] if refs else None
        after = texts_[texts_.index(next(t for t in texts_ if t.startswith("REFERRED TO"))):] if first else []
        left = "REPORTED" in after or bool(passed)
        fate = "passed" if left else "defeated" if "Committee voted it down" in after else "held" if "HELD" in after else "none"
        names_ = []
        sp = b.get("sponsors") or {}
        for role in ("prime", "sponsor", "cosponsor"):
            for h_ in ("house", "senate"):
                for label, slug in (sp.get(role) or {}).get(h_) or []:
                    sid, person = by_slug.get(slug, (None, None))
                    name = person["name"] if person else re.sub(r"^(?:Rep|Sen)\. ", "", label)
                    if person and person.get("party"):
                        parties[(sid[0], name)] = person["party"][:1]
                    if name not in names_:
                        names_.append(name)
        sponsor, cos = (names_[0] if names_ else "—"), names_[1:]
        primes = max(1, len([1 for h_ in ("house", "senate") for _ in (sp.get("prime") or {}).get(h_) or []]))
        what = what_it_does(b)
        if what:
            texts[p] = {"statement": what, "label": "From the bill summary written by Legislative Council Staff."}
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
        for vid in b.get("votes") or []:
            try:
                v = json.load(open(os.path.join(folder(session), "votes", f"{vid}.json")))
            except (OSError, ValueError):
                continue
            motion = text(v.get("motion"))
            committee = v.get("kind") == "committee"
            # The bill's own votes: passage, concurrence, conference reports and overrides on the floor; a committee's vote
            # to send it on or kill it (not amendments).
            if committee and not re.search(r"\bRefer\b|Postpone Indefinitely|Lay Over", motion, re.I):
                continue
            if not committee and not (re.match(r"Third reading$", v.get("calendar") or "", re.I) and motion.lower() == "bill"
                                      or re.match(r"(?:Repass|Concur|Adopt(?: ccr)?|Override)\b", motion, re.I)):
                continue  # amendments ("Amd (h.001)", "Amend (l.008)"), "Perm", "Not concur" and other motions
            h = "H" if (v.get("house") == "house" or re.match(r"House", v.get("committee") or "")) else "S"
            counts = v.get("counts") or {}
            marks = []
            members = v.get("members") or []
            # The presiding officer can appear twice, by name and as "President" (SB26-009's votes): keep the named line.
            if len(members) > sum(int(x or 0) for x in counts.values()):
                members = [m for m in members if m[0] not in ("President", "Speaker")]
            # A member listed twice, "Yes" and "No" (a changed vote: f21664 of 2025), can't be placed: left out.
            twice = {n for n in {m[0] for m in members} if sum(1 for m in members if m[0] == n) > 1}
            for name, how in members:
                if name in twice:
                    continue
                if how == "Yes":
                    continue
                # A committee page's full name, else its surname in that house ("Stephani Luck" for Stephanie Luck).
                sid = (by_full.get(name_key(name)) or by_floor.get((h, name.split()[-1]))) if committee else by_floor.get((h, name))
                marks.append([sid or f"{h}?{name}", "N" if how == "No" else "A"])
            d = v.get("date") or ""
            if not d:
                mm = re.match(r"(\d\d)/(\d\d)/(\d{4})", v.get("time") or "")
                d = f"{mm.group(3)}-{mm.group(1)}-{mm.group(2)}" if mm else ""
            cname = re.sub(r"^(?:House|Senate) ", "", v.get("committee") or "") if committee else None
            votes.append([h, "C" if committee else "F", cname, d, int(counts.get("Yes") or counts.get("AYE") or 0),
                          int(counts.get("No") or counts.get("NO") or 0), marks])
        votes.sort(key=lambda v: v[3])
        action_dates = [s[0] for s in steps if s[0]]
        chapter = next((int(x["chapter"]) for x in laws if str(x.get("chapter") or "").isdigit()), None)
        rec = {
            "nums": [p], "base": [p], "prev": earlier(session, title, b),
            "title": title, "summary": long_title, "act": "", "lawCode": "", "law": None, "laws": [],
            "comms": comm_list, "topics": topics, "places": [], "narrow": P.narrow_kind(title),
            "commFate": fate, "mainTopic": topics[0] if topics else "", "local": "local" in topics,
            "senDeleg": False, "asmDeleg": False, "budget": bool(re.search(r"general appropriation act|long bill", f"{title} {long_title}", re.I)),
            "passedS": "S" in passed, "passedA": "H" in passed, "program": None,
            "stage": stage, "passedIn": (HOUSE[origin] if origin in passed else HOUSE[other]) if stage == 2 else None,
            "chapter": chapter if stage == 5 else None, "veto": None, "memo": "", "vetoMemo": None,
            "simText": f"{title} {long_title} {' '.join(subjects)}",
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
            "votes": votes, "firstComms": [(first[0], first[1], left)] if first else [],
            "vers": [{"p": p, "sponsor": sponsor, "district": 0, "cosponsors": cos, "primes": primes, "cosp": len(cos),
                      "statusDesc": desc, "committee": comm if place == "committee" and stage in (0, 2) else None,
                      "actions": [[s[0], s[2] if s[2].isupper() or s[2].startswith("Committee") else s[3]] for s in steps],
                      "link": b.get("url") or f"https://leg.colorado.gov/bills/{b.get('number')}"}],
        }
        index[p] = len(recs)
        recs.append(rec)
    json.dump(texts, open(os.path.join(P.DATA, f"texts_{session}.json"), "w"), ensure_ascii=False)
    return recs, index, fetched, {"SENATE": [], "ASSEMBLY": []}


_TITLES = {}


def _titles(session):
    """An earlier year's bills that didn't become law, by short title: [(number, prime sponsors' slugs)]."""
    if session not in _TITLES:
        out = {}
        for f in glob.glob(os.path.join(folder(session), "bills", "*.json")):
            b = json.load(open(f))
            m = re.match(r"([HS]B)\d\d-(\d+)$", b.get("number") or "")
            if not m or b.get("status") == "Became Law":
                continue  # a law isn't tried again
            out.setdefault(text(b.get("short")).lower(), []).append((f"{m.group(1)}{int(m.group(2))}", primes_of(b)))
        _TITLES[session] = out
    return _TITLES[session]


def primes_of(b):
    sp = (b.get("sponsors") or {}).get("prime") or {}
    return {slug for h in ("house", "senate") for _, slug in sp.get(h) or []}


def earlier(session, title, b):
    """The same bill in the two years before: the same short title with a prime sponsor in common, or a title only one
    bill had."""
    out = set()
    k = title.lower()
    if len(k.split()) < 2:
        return out
    who = primes_of(b)
    for y in (session - 1, session - 2):
        if y not in sessions():
            continue
        old = _titles(y).get(k, [])
        same = [n for n, sp in old if sp & who]
        if same:
            out.add((y, same[0]))
        elif len(old) == 1:
            out.add((y, old[0][0]))
    return out


def agendas(session):
    return {}


def parties(session, recs):
    return {k: v for k, v in _PARTIES.get(session, {}).items() if v in ("D", "R")}
