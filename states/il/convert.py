"""Illinois: reads the bill status files from the General Assembly's file repository (data/il/<GA>/billstatus/*.xml,
from states/il/fetch.py) and turns them into the bill records build_data.py works with.

Every state's convert.py has the same functions: sessions(), load_session(session), agendas(session) and
parties(session, recs).

The actions are plain English. Every bill goes first to its house's gatekeeper, the House Rules Committee or the
Senate Assignments Committee, which assigns it to a committee ("Assigned to Executive Committee") or keeps it; bills
that miss a deadline go back there ("Rule 19(a) / Re-referred to Rules Committee"). Committee and floor votes are
tallies ("012-000-000": yes, no, present); the repository has no member-by-member roll calls. A bill keeps its number
through both houses. The governor can approve, veto, or send it back with changes (an amendatory veto), which both
houses can accept. Only House and Senate bills are shown (not resolutions or constitutional amendments).
"""
import glob, json, os, re
from collections import defaultdict
from datetime import datetime
from zoneinfo import ZoneInfo
import html as _html

from . import profile as P

CURRENT = P.session_of(datetime.now(ZoneInfo(P.TIMEZONE)).year)
HOUSE = {"H": "House", "S": "Senate"}
GATE = {"H": "Rules", "S": "Assignments"}


def folder(session):
    return os.path.join(P.DATA, str(P.assembly_of(session)), "billstatus")


def sessions():
    out = []
    for d in glob.glob(os.path.join(P.DATA, "*", "billstatus")):
        ga = os.path.basename(os.path.dirname(d))
        if ga.isdigit() and glob.glob(os.path.join(d, "*.xml")):
            out.append(2 * int(ga) + 1817)
    return sorted(out)


def iso(d):
    m = re.match(r"(\d+)/(\d+)/(\d{4})", d or "")
    return f"{m.group(3)}-{int(m.group(1)):02d}-{int(m.group(2)):02d}" if m else ""


LOST = {"fa\ufffdade": "façade", "prot\ufffdg\ufffd": "protégé", "caf\ufffd": "café", "r\ufffdsum\ufffd": "résumé",
        "na\ufffdve": "naïve", "pi\ufffdata": "piñata", "Pe\ufffda": "Peña"}


def text(x):
    t = re.sub(r"\s+", " ", _html.unescape(x or "")).strip()
    if "\ufffd" in t:
        # Characters already lost in the files ("fa\ufffdade", "police\ufffdinvolved", "21 \ufffd Inpatient").
        for k, v in LOST.items():
            t = t.replace(k, v)
        t = re.sub(r"(?<=\w)\ufffd(?=\w)", "-", t).replace(" \ufffd ", " – ").replace("\ufffd", "")
    return t


def members(session):
    """(house letter, full name) for that Assembly's members, from its member lists."""
    ga, out = P.assembly_of(session), []
    for h, name in (("H", "House"), ("S", "Senate")):
        path = os.path.join(P.DATA, str(ga), f"{ga}{name}Members.xml")
        if os.path.exists(path):
            out += [(h, text(n)) for n in re.findall(r"<Name>([^<]+)</Name>", open(path, encoding="utf-8-sig").read())]
    return out


def split_sponsors(s, known):
    """"Rep. A-B-C, D, E-F and G" -> ([A, B, C], [D, E, F, G]): the chief sponsor and chief co-sponsors come first,
    joined by hyphens; later groups are separated by commas and can be hyphen-joined too. Names can have hyphens of
    their own, so groups are split against the member lists."""
    s = re.sub(r"^\(?(?:Rep|Sen)\.\s*", "", text(s).strip("() "))
    if not s:
        return [], []
    # "Evans, Jr.-Nabeela Syed": a suffix stays with its name, whether a comma, "and", a hyphen or the end follows.
    parts = re.split(r",(?!\s*(?:Jr|Sr|II|III|IV)\.?(?:,|$| and|-))\s*|\s+and\s+", s)
    names = sorted(known, key=len, reverse=True)

    def chain(x):
        """"A-B-C" -> [A, B, C], against the member list (names can have hyphens of their own)."""
        out = []
        while x:
            hit = next((n for n in names if x == n or x.startswith(n + "-")), None)
            if not hit:
                # Someone not on the member lists (they left mid-session): the name runs to the next hyphen that
                # starts a full name ("Mary Edly-Allen-Mattie Hunter" -> "Mary Edly-Allen", then "Mattie Hunter").
                m = re.search(r"-(?=[A-Z][^-\s]*\s)", x)
                hit = x[:m.start()] if m else x
            out.append(hit)
            x = x[len(hit) + 1:]
        return out

    pieces = [chain(p.strip()) for p in parts if p.strip()]
    chiefs = pieces[0] if pieces else []
    rest = [n for ps in pieces[1:] for n in ps]
    # A name whose accented letter was lost in the file ("Guzm-n") is the member's own spelling ("Guzmán").
    lost = {re.sub(r"[^\x00-\x7f]", "-", n): n for n in known}
    fix = lambda n: n if n in known else lost.get(n, n)
    return [fix(n) for n in chiefs], [fix(r.strip()) for r in rest if r.strip()]


SMALL = {"of", "and", "in", "the", "for", "to", "on", "a", "an", "or", "by", "with", "at"}


def titled(short, lower_words):
    """"TANF-FAMILY VIOLENCE OPTION" -> "TANF-Family Violence Option": words, but not acronyms, in title case."""
    out = []
    for k, w in enumerate(re.split(r"(\W+)", short)):
        lw = w.lower()
        if not w or not w[0].isalpha():
            out.append(w)
        elif lw in SMALL and k:
            out.append(lw)
        elif lw in lower_words or len(w) > 5:
            out.append(w.capitalize())
        else:
            out.append(w)
    return "".join(out)


def bills(session):
    out = {}
    for f in glob.glob(os.path.join(folder(session), "*.xml")):
        m = re.search(r"\d{5}(HB|SB)0*(\d+)\.xml$", f)
        if not m:
            continue
        t = open(f, encoding="utf-8", errors="replace").read()
        if not t.rstrip().endswith("</xml>"):
            continue
        acts = [(iso(d), {"House": "H", "Senate": "S"}.get(text(ch), "G"), text(a))
                for d, ch, a in re.findall(r"<statusdate>([^<]*)</statusdate><chamber>([^<]*)</chamber><action>(.*?)</action>",
                                           (re.search(r"<actions>(.*?)</actions>", t, re.S) or re.search(r"(.*)", "")).group(1), re.S)]
        out[m.group(1) + m.group(2)] = {
            "short": text(re.search(r"<shortdesc>(.*?)</shortdesc>", t, re.S).group(1)) if "<shortdesc>" in t else "",
            "sponsors": text(re.search(r"<sponsors>(.*?)</sponsors>", t, re.S).group(1)) if "<sponsors>" in t else "",
            "alt": text(re.search(r"<altsponsors>(.*?)</altsponsors>", t, re.S).group(1)) if "<altsponsors>" in t else "",
            "synopsis": text(re.sub(r"<[^>]+>", " ", re.search(r"<SynopsisText>(.*?)</SynopsisText>", t, re.S).group(1))) if "<SynopsisText>" in t else "",
            "refs": re.findall(r"<reference>([^<]+)</reference>", t),
            "actions": acts,
        }
    return out


PASS = re.compile(r"^(?:Third Reading(?: - Short Debate| - Consideration \w+)? - Passed|Third Reading - Passed)[;:]?\s*(\d{3})-(\d{3})-(\d{3})")
REPORT = re.compile(r"^(?:Do Pass|Recommends Do Pass|Do Pass as Amended|Reported Back To)\b(?: / (?:Short|Standard) Debate)?\s*(.*?)(?:;\s*(\d{3})-(\d{3})-(\d{3}))?$")


def decode(h, a):
    """One action in the site's shared wording (only the steps its rules use), else as written."""
    m = re.match(r"(?:Assigned|Re-assigned) to (.+?)(?: Committee)?$", a)
    if m:
        return f"REFERRED TO {m.group(1).upper()}"
    if re.match(r"(?:Referred to|Rule \S+ / Re-referred to) (Rules Committee|Assignments)", a):
        return f"REFERRED TO {GATE.get(h, 'RULES').upper()}"
    if re.match(r"(?:Do Pass|Recommends Do Pass)\b", a):
        return "REPORTED"
    if PASS.match(a) or re.match(r"Third Reading.* - Passed", a):
        return f"PASSED {HOUSE.get(h, 'HOUSE').upper()}"
    if a == "Sent to the Governor":
        return "DELIVERED TO GOVERNOR"
    if re.match(r"Governor Approved|Public Act\b|Governor Item/Reduction Veto PA|Governor Certifies Changes|Bill Overridden|Override", a):
        return "SIGNED"
    if re.match(r"Governor Vetoed|Total Veto Stands", a):
        return "VETOED"
    if a == "Governor Amendatory Veto":
        return "AMENDATORY VETO"
    return a


def stage_of(steps, live):
    texts = [t for _, _, t, _ in steps]
    raw = [x for _, _, _, x in steps]
    if "SIGNED" in texts:
        return 5
    if "VETOED" in texts:
        return 6
    if "AMENDATORY VETO" in texts:
        # Sent back with the governor's changes: both houses can accept them; a finished session's not accepted died.
        return 3 if live else 6
    if "DELIVERED TO GOVERNOR" in texts:
        return 4
    if "Passed Both Houses" in raw:
        return 3
    if any(t.startswith("PASSED") for t in texts):
        return 2
    return 1 if where(steps)[1] == "floor" else 0


def where(steps):
    """(house, "committee"/"floor"/"desk", committee) the bill is in now."""
    house, place, comm = None, "desk", None
    for _, h, t, a in steps:
        if h not in HOUSE:
            continue
        if house is None:
            house = h
        if re.match(r"Arrived? in (House|Senate)", a):
            house, place, comm = h, "desk", None
        if t.startswith("REFERRED TO"):
            house, place = h, "committee"
            comm = GATE[h] if t == f"REFERRED TO {GATE[h].upper()}" else re.sub(r" Committee$", "", re.sub(r"^(?:Assigned|Re-assigned) to ", "", a))
        elif t == "REPORTED" or re.match(r"Placed on Calendar (Order of )?(2nd|3rd|Second|Third)", a) or re.match(r"Approved for Consideration", a):
            if not (t != "REPORTED" and place == "committee" and comm not in (GATE.get(h), None) and "Approved for Consideration" not in a and not re.match(r"Placed on Calendar", a)):
                place, comm = "floor", None
        elif t.startswith("PASSED"):
            place, comm = "desk", None
    return house, place, comm


def tally(a):
    m = re.search(r"(\d{3})-(\d{3})-(\d{3})", a)
    return (int(m.group(1)), int(m.group(2)), int(m.group(3))) if m else None


# ---- The same bill in earlier General Assemblies. Bills come back under new numbers, and the files don't link
# them, so: an earlier bill with the same short title ("MILITARY SERVICE-TECH") whose synopsis shares at least 60% of
# its words (40% with the same chief sponsor). Shell bills ("Makes a technical change", the $2 "-TECH" appropriations)
# never match: they're placeholders. Up to two General Assemblies back.
_EARLIER = {}
_SKIP = {"the", "and", "act", "amends", "creates", "provides", "that", "with", "for", "under", "section", "this"}


def _session(session):
    if session not in _EARLIER:
        out = {}
        for p, b in bills(session).items():
            syn = b["synopsis"]
            # Shells: "Makes a technical change", and the $2 placeholder appropriations ("$DEPT AGING-TECH").
            if not syn or (re.search(r"technical change|Effective immediately\.?$", syn) and len(syn) < 200) or \
                    re.search(r"-TECH$", b["short"]) or re.match(r"Appropriates \$[12] ", syn):
                continue
            words = set(re.findall(r"[a-z0-9]{3,}", syn.lower())) - _SKIP
            sponsor = re.split(r"[-,]| and ", re.sub(r"^\(?(?:Rep|Sen)\.\s*", "", b["sponsors"]))[0].strip()
            out[p] = (b["short"].upper(), words, sponsor)
        _EARLIER[session] = out
    return _EARLIER[session]


def earlier(session, bill):
    out = set()
    me = _session(session).get(bill)
    if not me or len(me[1]) < 8:
        return out
    for y in (session - 2, session - 4):
        if not os.path.isdir(folder(y)):
            continue
        best = None
        for other, (short, words, sponsor) in _session(y).items():
            if short != me[0]:
                continue
            j = len(me[1] & words) / max(1, len(me[1] | words))
            if j >= 0.6 or (j >= 0.4 and sponsor and sponsor == me[2]):
                if not best or j > best[0]:
                    best = (j, other)
        if best:
            out.add((y, best[1]))
    return out


def load_session(session):
    """Read one session's bills and return (records, bill number -> record index, fetched time, delegation)."""
    live = session >= CURRENT
    data = bills(session)
    # Members of this and the other downloaded Assemblies: someone who left mid-session is in an earlier list.
    known = members(session) + [m for s in sessions() if s != session for m in members(s)]
    seat_of, party_of = seats(session)
    # Words the synopses write in lowercase: a title word that never is ("TANF", "AI") stays in capitals.
    lower_words = {w for b in data.values() for w in re.findall(r"\b[a-z]+\b", b["synopsis"])}
    by_name = {n: h for h, n in known}
    stamp = max((os.path.getmtime(f) for f in glob.glob(os.path.join(folder(session), "*.xml"))), default=0)
    fetched = datetime.fromtimestamp(stamp, ZoneInfo(P.TIMEZONE)).strftime("%Y-%m-%d %H:%M")

    recs, index = [], {}
    for p, b in sorted(data.items(), key=lambda kv: (kv[0][:2], int(kv[0][2:]))):
        origin, other = p[0], ("S" if p[0] == "H" else "H")
        # The files list a few actions out of order (a veto's outcome before "Sent to the Governor"): by date, keeping
        # the file's order within a day.
        steps = [(d, h, decode(h, a), a) for d, h, a in sorted(b["actions"], key=lambda x: x[0])]
        stage = stage_of(steps, live)
        texts = [t for _, _, t, _ in steps]
        passed = {h for _, h, t, _ in steps if t.startswith("PASSED")}
        if stage >= 3:
            passed = {"S", "H"}
        passed_in = HOUSE[max(((d, h) for d, h, t, _ in steps if t.startswith("PASSED")))[1]] if stage == 2 and passed else None
        now_house, place, committee = where(steps)
        now_house = now_house or origin
        refs = [(h, re.sub(r" Committee$", "", re.sub(r"^(?:Assigned|Re-assigned) to ", "", a))) for _, h, t, a in steps
                if t.startswith("REFERRED TO") and not t.endswith(("RULES", "ASSIGNMENTS"))]
        comm_names = {c for _, c in refs}
        comm_list = sorted({f"{h} · {c}" for h, c in refs})
        title = titled(b["short"], lower_words) if b["short"].isupper() else b["short"]
        synopsis = re.sub(r"^\s*(Amends|Creates)\b", r"\1", b["synopsis"])
        topics = [k for k, (label, cset, _, _) in P.TOPICS.items()
                  if comm_names & cset or (k in P.TOPIC_WORDS and P.TOPIC_WORDS[k].search(b["short"] + " " + synopsis[:300]))]
        own = [c for h, c in refs if h == origin]
        first_comms = []
        if own:
            i0 = next(i for i, (_, h, t, a) in enumerate(steps) if h == origin and t.startswith("REFERRED TO") and not t.endswith(("RULES", "ASSIGNMENTS")))
            left = any(h == origin and (t == "REPORTED" or t.startswith("PASSED")) for _, h, t, _ in steps[i0 + 1:])
            first_comms.append((origin, own[0], left))
        main_topic = topics[0] if topics else ""
        raw = [a for _, _, _, a in steps]
        fate = ("passed" if "REPORTED" in texts else
                "defeated" if any(re.match(r"Do Pass.*Failed|Motion Do Pass.*Lost|Failed", a) for a in raw) else
                "held" if own and any(re.match(r"Rule \S+ / Re-referred to", a) for a in raw) else "none")

        chiefs, co = split_sponsors(b["sponsors"], [n for h, n in known if h == origin])
        alt_chiefs, alt_co = split_sponsors(b["alt"], [n for h, n in known if h == other]) if b["alt"] else ([], [])
        sponsor = chiefs[0] if chiefs else "—"
        if stage == 0 and committee:
            desc = f"In {HOUSE[now_house]} committee"
        elif stage <= 1 and place == "floor":
            desc = f"On the {HOUSE[now_house]} floor"
        elif stage >= 2:
            desc = {2: f"Passed the {passed_in}", 3: "Passed both houses", 4: "On the governor's desk",
                    5: "Signed into law", 6: "Vetoed"}[stage]
            if stage == 3 and "AMENDATORY VETO" in texts:
                desc = "Sent back with the governor's changes"
        else:
            desc = next((a for a in reversed(raw) if not re.match(r"(Added|Removed|Remove) .*Sponsor", a)), "Filed")

        def dates(test, mode="last"):
            ds = sorted({d for d, h, t, a in steps if test(h, t, a) and d})
            return {"first": ds[0], "last": ds[-1], "all": ";".join(ds)}[mode] if ds else ""

        votes, comm_now = [], {}
        for d, h, t, a in steps:
            if t.startswith("REFERRED TO"):
                comm_now[h] = re.sub(r" Committee$", "", re.sub(r"^(?:Assigned|Re-assigned) to ", "", a)) if not t.endswith(("RULES", "ASSIGNMENTS")) else GATE.get(h)
            v = tally(a)
            if v and h in HOUSE:
                if t == "REPORTED":
                    votes.append([h, "C", comm_now.get(h), d, v[0], v[1], []])
                elif t.startswith("PASSED") or re.match(r"(?:\w+ )*(?:House|Senate) Concurs|Accept Amendatory Veto|Override", a):
                    votes.append([h, "F", None, d, v[0], v[1], []])
        action_dates = [d for d, _, _, _ in steps if d]
        for n in chiefs + co:
            if (origin, n) in party_of:
                _PARTIES.setdefault(session, {})[(origin, n)] = party_of[(origin, n)]
        for n in alt_chiefs + alt_co:
            if (other, n) in party_of:
                _PARTIES.setdefault(session, {})[(other, n)] = party_of[(other, n)]
        pa = next((re.search(r"(\d+)-(\d+)", a).group(2) for a in raw if re.match(r"Public Act|Governor Item/Reduction Veto PA", a) and re.search(r"\d+-\d+", a)), None)
        vers = {"p": p, "sponsor": sponsor, "district": int((seat_of.get((origin, sponsor)) or "X:0")[2:]),
                "cosponsors": chiefs[1:] + co + alt_chiefs + alt_co, "primes": max(1, len(chiefs)),
                "cosp": len(chiefs[1:] + co + alt_chiefs + alt_co),
                "statusDesc": desc, "committee": committee if place == "committee" and stage in (0, 2) else None,
                "actions": [[d, t] for d, _, t, _ in steps]}
        rec = {
            "nums": [p], "base": [p], "prev": earlier(session, p),
            "title": title, "summary": "", "act": "", "lawCode": "", "law": None, "laws": [],
            "comms": comm_list, "topics": topics, "places": [], "narrow": P.narrow_kind(title),
            "commFate": fate, "mainTopic": main_topic, "local": "local" in topics,
            "senDeleg": False, "asmDeleg": False, "budget": bool(re.search(r"\bBUDGET\b|APPROPRIATION", b["short"], re.I)),
            "passedS": "S" in passed, "passedA": "H" in passed, "program": None,
            "stage": stage, "passedIn": passed_in,
            "chapter": int(pa) if pa and stage == 5 else None,
            "veto": None, "memo": "", "vetoMemo": None,
            "simText": synopsis,
            "comm": committee if stage == 0 and place == "committee" else None,
            "first": min(action_dates, default=f"{session}-01-01"),
            "last": max(action_dates, default=f"{session}-01-01"),
            "cosp": vers["cosp"],
            # Key dates: on the floor, passed the Senate, passed the House, (New York's return to committee: none here),
            # sent to the governor, signed, vetoed.
            "keyDates": [
                dates(lambda h, t, a: h == origin and (t == "REPORTED" or bool(re.match(r"Placed on Calendar (Order of )?2nd", a))), "first"),
                dates(lambda h, t, a: t == "PASSED SENATE", "all"),
                dates(lambda h, t, a: t == "PASSED HOUSE", "all"),
                "",
                dates(lambda h, t, a: t == "DELIVERED TO GOVERNOR"),
                dates(lambda h, t, a: t == "SIGNED"),
                dates(lambda h, t, a: t == "VETOED"),
            ],
            "votes": votes, "firstComms": first_comms, "vers": [vers],
        }
        index[p] = len(recs)
        recs.append(rec)
    return recs, index, fetched, {"SENATE": [], "ASSEMBLY": []}


def agendas(session):
    return {}  # the repository has no committee hearing schedules


_PARTIES = {}


def parties(session, recs):
    return {k: v for k, v in _PARTIES.get(session, {}).items() if v in ("D", "R")}


def seats(session):
    """(house, full name) -> seat id and party letter, from that Assembly's member lists (district and party)."""
    ga, seat_of, party_of = P.assembly_of(session), {}, {}
    for h, name in (("H", "House"), ("S", "Senate")):
        path = os.path.join(P.DATA, str(ga), f"{ga}{name}Members.xml")
        if not os.path.exists(path):
            continue
        for m in re.findall(r"<Member>(.*?)</Member>", open(path, encoding="utf-8-sig").read(), re.S):
            n = re.search(r"<Name>([^<]+)</Name>", m)
            d = re.search(r"<District>(\d+)</District>", m)
            party = re.search(r"<Party>([^<]*)</Party>", m)
            if n and d:
                seat_of[(h, text(n.group(1)))] = f"{h}:{int(d.group(1))}"
                party_of[(h, text(n.group(1)))] = (party.group(1) if party else "")[:1]
    return seat_of, party_of
