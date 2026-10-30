"""Texas: reads the bill histories downloaded from the Legislature's FTP site (data/tx/<code>/billhistory/*.xml, from
states/tx/fetch.py) and turns them into the bill records build_data.py works with.

Every state's convert.py has the same functions: sessions(), load_session(session), agendas(session) and
parties(session, recs).

Each history line has a code: its first letter is the house that acted (H, S, or E for the governor's office), and
the number says what happened (H555 "Passed", S285 "Reported favorably w/o amendments", E020 "Signed by the
Governor"). Stages come from the codes; the wording is kept, except the steps the site's rules use, which are put in
the wording New York's data uses. A bill keeps its number through both houses (HB 12 goes to the Senate as HB 12);
its companion in the other house is a separate bill. In the House, a bill a committee reports goes to the Calendars
Committee, which decides which bills reach the floor: it's shown as in that committee until it's placed on a calendar.
Only regular-session House and Senate bills are shown (not resolutions or special sessions' bills).
"""
import glob, json, os, re
import xml.etree.ElementTree as ET
from collections import defaultdict
from datetime import datetime
from zoneinfo import ZoneInfo

from . import profile as P

CURRENT = P.session_of(datetime.now(ZoneInfo(P.TIMEZONE)).year)
HOUSE = {"H": "House", "S": "Senate"}


def folder(session):
    return os.path.join(P.DATA, P.code_of(session), "billhistory")


def sessions():
    out = []
    for d in glob.glob(os.path.join(P.DATA, "*R", "billhistory")):
        code = os.path.basename(os.path.dirname(d))
        if glob.glob(os.path.join(d, "*.xml")):
            out.append(2 * int(code[:-1]) + 1847)
    return sorted(out)


def num(name):
    """"HB 12.xml" -> "HB12"."""
    m = re.match(r"([HS]B)\s*0*(\d+)", name)
    return f"{m.group(1)}{m.group(2)}" if m else None


def iso(d):
    m = re.match(r"(\d+)/(\d+)/(\d{4})", d or "")
    return f"{m.group(3)}-{int(m.group(1)):02d}-{int(m.group(2)):02d}" if m else ""


def names(s):
    return [x.strip() for x in (s or "").split("|") if x.strip()]


def bills(session):
    """Bill -> parsed history (dict), for every HB and SB file that parses."""
    out = {}
    for f in glob.glob(os.path.join(folder(session), "*.xml")):
        p = num(os.path.basename(f))
        if not p:
            continue
        try:
            t = ET.parse(f).getroot()
        except ET.ParseError:
            continue  # a file cut off mid-download; the next run gets it again
        acts = []
        for a in t.iter("action"):
            code = a.findtext("actionNumber") or ""
            acts.append((iso(a.findtext("date")), code[:1], int(code[1:] or 0), (a.findtext("description") or "").strip(),
                         (a.findtext("comment") or "").strip()))
        comms = []
        for c in t.find("committees") if t.find("committees") is not None else []:
            if c.get("name"):
                comms.append((c.tag[0].upper(), c.get("name"), c.get("status") or "",
                              int(c.get("ayeVotes") or 0), int(c.get("nayVotes") or 0),
                              int(c.get("presentNotVotingVotes") or 0), int(c.get("absentVotes") or 0)))
        out[p] = {
            "caption": (t.findtext("caption") or "").strip(),
            "authors": names(t.findtext("authors")), "coauthors": names(t.findtext("coauthors")),
            "sponsors": names(t.findtext("sponsors")), "cosponsors": names(t.findtext("cosponsors")),
            "subjects": [re.sub(r"\s*\([A-Z]\d+\)$", "", s.text or "").strip() for s in t.iter("subject")],
            "companions": (t.findtext("companions") or "").strip(),
            "committees": comms, "actions": acts,
        }
    return out


# What each code range means (House "H" and Senate "S" codes share their numbers).
def is_referral(n, desc):
    return n < 200 and desc.startswith("Referred to ")


def is_report(n):
    return n in (250, 252, 285, 287) or 250 <= n <= 254 or 285 <= n <= 289


def decode(house, n, desc):
    """One history line in the site's shared wording (only the steps its rules use), else as written."""
    if house in HOUSE and is_referral(n, desc):
        return f"REFERRED TO {desc[len('Referred to '):].upper()}"
    if house in HOUSE and is_report(n):
        return "REPORTED"
    if (house, n) in (("H", 555), ("H", 556), ("S", 576), ("S", 577)):
        return f"PASSED {HOUSE[house].upper()}"
    if house == "E" and n == 15:
        return "DELIVERED TO GOVERNOR"
    if house == "E" and n in (20, 25, 30):  # signed, filed without signature, signed with line-item vetoes
        return "SIGNED"
    if house == "E" and n == 35:
        return "VETOED"
    return desc


def stage_of(p, acts):
    """How far a bill got, 0-6, from its history's codes."""
    codes = {(h, n) for _, h, n, _, _ in acts}
    if codes & {("E", 20), ("E", 25), ("E", 30)}:
        return 5
    if ("E", 35) in codes:
        return 6
    if ("E", 15) in codes:
        return 4
    # Passed both houses: enrolled, the first house agreed to the second's changes, or the second passed it unchanged
    # ("Senate passage reported" on a House bill), or both adopted a conference report.
    origin = p[0]
    # A conference report passes only when both houses adopt it (House 750 + Senate's 751/761, or the reverse).
    conference = (("H", 750) in codes and codes & {("H", 751), ("S", 761)}) or (("S", 761) in codes and codes & {("S", 762), ("H", 750)})
    if codes & {("H", 840), ("S", 840), ("H", 701), ("S", 706)} or conference or (origin, 805) in codes:
        return 3
    if any(decode(h, n, d).startswith("PASSED") for _, h, n, d, _ in acts) or (origin, 806) in codes:
        return 2
    return 1 if where(p, acts)[1] == "floor" else 0


def where(p, acts):
    """(house, "committee"/"floor", committee name) the bill is in now: in the House, a reported bill waits in the
    Calendars Committee until it's placed on a calendar."""
    house, place, comm = p[0], "desk", None
    for _, h, n, d, _ in acts:
        if h not in HOUSE:
            continue
        if n in (800,) and h != house:  # "Received from the House/Senate"
            house, place, comm = h, "desk", None
        if is_referral(n, d):
            house, place, comm = h, "committee", d[len("Referred to "):]
        elif is_report(n):
            place, comm = ("committee", "Calendars") if h == "H" else ("floor", None)
        elif h == "H" and n in (400, 405, 410, 475):
            place, comm = "committee", ("Local & Consent Calendars" if n == 410 else "Calendars")
        elif (h == "H" and n in (430, 435, 465)) or (h == "S" and n in (400, 430)):
            place, comm = "floor", None
        elif decode(h, n, d).startswith("PASSED"):
            house, place, comm = ("S" if h == "H" else "H"), "desk", None
    return house, place, comm


# ---- The same bill in earlier sessions. Bills come back under new numbers, and the files don't link them, so: an
# earlier bill whose caption has at least 90% of the same words (60% with the same lead author). Captions that name
# places ("the creation of the Harris County Municipal Utility District No. 568") must name the same ones, since
# many local bills differ only in that; and the General Appropriations Act doesn't count. Up to two sessions back.
_EARLIER = {}
_SKIP = {"relating", "to", "the", "of", "a", "an", "and", "or", "in", "for", "on", "by", "certain", "provision", "provisions"}


def _caption_words(caption):
    return set(re.findall(r"[a-z0-9]{2,}", caption.lower())) - _SKIP


def _places(caption):
    """Capitalized names in a caption (not its first word): "Harris County", "Lower Neches Valley Authority", "568"."""
    words = re.findall(r"\b[A-Z][a-zA-Z.'-]+|\bNo\. \d+|\b\d{2,}\b", caption)
    return {w for w in words[1:] if w not in ("Relating", "Texas", "State", "The")}


def _session(session):
    if session not in _EARLIER:
        out = {}
        for p, b in bills(session).items():
            cap = b["caption"]
            if re.search(r"general appropriations", cap, re.I):
                continue
            out[p] = (_caption_words(cap), b["authors"][0] if b["authors"] else "", _places(cap))
        _EARLIER[session] = out
    return _EARLIER[session]


def earlier(session, bill):
    """{(session, bill), ...}: this bill in the two sessions before."""
    out = set()
    me = _session(session).get(bill)
    if not me or len(me[0]) < 4:
        return out
    for y in (session - 2, session - 4):
        if not os.path.isdir(folder(y)):
            continue
        best = None
        for other, (words, author, places) in _session(y).items():
            if places != me[2]:
                continue
            j = len(me[0] & words) / max(1, len(me[0] | words))
            if j >= 0.9 or (j >= 0.6 and author and author == me[1]):
                if not best or j > best[0]:
                    best = (j, other)
        if best:
            out.add((y, best[1]))
    return out


def _plain(s):
    import unicodedata
    s = unicodedata.normalize("NFD", s or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"\s+", " ", re.sub(r"[^a-z]", " ", s)).strip()


def floor_members(session, house="H"):
    """The journal's name for a member ("Bell, C.", "Wu", "Speaker"; the Senate's "A. Hinojosa") -> seat id, for the
    current session."""
    path = os.path.join(P.DATA, f"contacts_{session}.json")
    if session != CURRENT or not os.path.exists(path):
        return {}
    people = [(sid, p) for sid, p in json.load(open(path))["people"].items() if sid[0] == house]
    out = {}
    for sid, p in people:
        last = _plain((p.get("dataName") or "").split(",")[0])
        out.setdefault(last, []).append((sid, _plain(p["name"])[:1]))
        if p.get("position") == "Speaker of the House":
            out["speaker"] = [(sid, "")]
    return out


def floor_vote(name, members):
    """A journal name's seat, or None."""
    name = re.sub(r"\(C\)$", "", name.strip())  # "(C)": the member presiding
    m = re.match(r"(.+?),\s*([A-Z])\.?$", name) or re.match(r"([A-Z])\.\s+(.+)$", name)
    if m and m.re.pattern.startswith("([A-Z])"):
        last, initial = _plain(m.group(2)), m.group(1).lower()
    else:
        last, initial = (_plain(m.group(1)), m.group(2).lower()) if m else (_plain(name), "")
    hits = members.get(last, [])
    if initial and len(hits) > 1:
        hits = [h for h in hits if h[1] == initial]
    return hits[0][0] if len(hits) == 1 else None


def load_session(session):
    """Read one session's bills and return (records, bill number -> record index, fetched time, delegation)."""
    data = bills(session)
    seat_of, party_of, full = seats()
    vpath = os.path.join(P.DATA, P.code_of(session), "house_votes.json")
    house_votes = json.load(open(vpath)) if os.path.exists(vpath) else {}
    members = floor_members(session)
    spath = os.path.join(P.DATA, P.code_of(session), "senate_votes.json")
    senate_votes = json.load(open(spath)) if os.path.exists(spath) else {}
    senators = floor_members(session, "S")
    stamp = max((os.path.getmtime(f) for f in glob.glob(os.path.join(folder(session), "*.xml"))), default=0)
    fetched = datetime.fromtimestamp(stamp, ZoneInfo(P.TIMEZONE)).strftime("%Y-%m-%d %H:%M")

    def named(h, n):
        return full.get((h, n), n if "," not in n else " ".join(reversed([x.strip() for x in n.split(",", 1)])))

    recs, index = [], {}
    for p, b in sorted(data.items(), key=lambda kv: (kv[0][:2], int(kv[0][2:]))):
        origin, other = p[0], ("S" if p[0] == "H" else "H")
        acts = sorted(b["actions"], key=lambda a: a[0])
        steps = [(d, h, decode(h, n, desc), desc, n) for d, h, n, desc, _ in acts]
        stage = stage_of(p, acts)
        texts = [t for _, _, t, _, _ in steps]
        passed = {h for _, h, t, _, _ in steps if t.startswith("PASSED")}
        if (origin, 805) in {(h, n) for _, h, n, _, _ in acts} or (origin, 806) in {(h, n) for _, h, n, _, _ in acts}:
            passed.add(other)
        if stage >= 3:
            passed = {"S", "H"}
        passed_in = None
        if stage == 2:
            passed_in = HOUSE[other] if other in passed else HOUSE[origin]
        now_house, place, committee = where(p, acts)
        refs = [(h, t[len("REFERRED TO "):]) for _, h, t, _, _ in steps if t.startswith("REFERRED TO")]
        comm_names = {c.title() for _, c in refs}
        by_upper = {}
        for _, h, n, desc, _ in acts:
            if is_referral(n, desc):
                by_upper[(h, desc[len("Referred to "):].upper())] = desc[len("Referred to "):]
        comm_names = {by_upper.get((h, c), c.title()) for h, c in refs}
        comm_list = sorted({f"{h} · {by_upper.get((h, c), c.title())}" for h, c in refs})
        title = re.sub(r"^Relating to (the )?", "", b["caption"]).rstrip(".").strip()
        title = (title[:1].upper() + title[1:] + ".") if title else p

        topics = [k for k, (label, cset, sre, _) in P.TOPICS.items()
                  if comm_names & cset or any(sre.search(s) for s in b["subjects"]) or
                  (k in P.TOPIC_WORDS and P.TOPIC_WORDS[k].search(title))]
        own = [by_upper.get((h, c), c.title()) for h, c in refs if h == origin]
        first_comms = []
        if own:
            i0 = next(i for i, (_, h, t, _, _) in enumerate(steps) if h == origin and t.startswith("REFERRED TO"))
            left = any(h == origin and t == "REPORTED" for _, h, t, _, _ in steps[i0 + 1:])
            first_comms.append((origin, own[0], left))
        main_topic = topics[0] if topics else ""
        own_steps = [(h, n) for _, h, n, _, _ in acts if h == origin]
        fate = ("passed" if any(t == "REPORTED" for t in texts) else
                "defeated" if any(n in (249, 280) for h, n in own_steps) else
                "held" if any(n in (245, 275) for h, n in own_steps) else "none")

        authors = [named(origin, n) for n in b["authors"]] or ["—"]
        co = [named(origin, n) for n in b["coauthors"]] + [named(other, n) for n in b["sponsors"] + b["cosponsors"]]
        if stage == 0 and committee:
            desc = f"In {HOUSE[now_house]} committee"
        elif stage <= 1 and place == "floor":
            desc = f"On the {HOUSE[now_house]} floor"
        elif stage >= 2:
            desc = {2: f"Passed the {passed_in}", 3: "Passed both houses", 4: "On the governor's desk",
                    5: "Signed into law", 6: "Vetoed"}[stage]
        else:
            desc = next((t for t in reversed(texts)), "Filed")

        def dates(test, mode="last"):
            ds = sorted({d for d, h, t, x, n in steps if test(h, t, n) and d})
            return {"first": ds[0], "last": ds[-1], "all": ";".join(ds)}[mode] if ds else ""

        # Committee votes (totals only): the date the committee reported the bill, or the last time it took it up.
        votes = []
        for h, cname, status, yes, no, pnv, absent in b["committees"]:
            if yes or no:
                when = dates(lambda hh, t, n: hh == h and (t == "REPORTED" or n in (249, 280)))
                votes.append([h, "C", cname, when or dates(lambda hh, t, n: hh == h), yes, no, []])
        # House floor votes (the House Journal's record votes): final passage, agreeing to the Senate's changes, and
        # adopting a conference report; second reading's vote only when third reading had none.
        floor, prev = [], None
        for d, h, n, desc, comment in acts:
            rv = re.search(r"RV#(\d+)", comment) if (h, n) == ("H", 630) else None
            if rv and rv.group(1) in house_votes and prev in (535, 536, 555, 556, 701, 750):
                floor.append((prev in (535, 536), d, house_votes[rv.group(1)]))
            elif h == "H" and n not in (630, 631, 633):
                prev = n
        if any(not second for second, _, _ in floor):
            floor = [f for f in floor if not f[0]]
        for _, d, v in floor:
            def who(name):
                return floor_vote(name, members) or f"H?{name}"
            votes.append(["H", "F", None, d, len(v["Y"]), len(v["N"]),
                          [[who(n), "N"] for n in v["N"]] + [[who(n), "B"] for n in v["P"]] + [[who(n), "A"] for n in v["A"]]])
        # Senate floor votes (the Senate Journal): final passage, agreeing to the House's changes, conference reports;
        # second reading's only when third reading's wasn't found.
        sv = senate_votes.get(p, [])
        keep = [x for x in sv if x[1] != "second"] or [x for x in sv if x[1] == "second"][-1:]
        for d, kind, yes, no, v in keep:
            def sname(name):
                return floor_vote(name, senators) or f"S?{name}"
            votes.append(["S", "F", None, d, yes, no,
                          [[sname(n), "N"] for n in v["N"]] + [[sname(n), "B"] for n in v["P"]] + [[sname(n), "A"] for n in v["A"]]])
        votes.sort(key=lambda x: x[3] or "")
        action_dates = [d for d, _, _, _, _ in steps if d]
        for h, n in [(origin, x) for x in b["authors"] + b["coauthors"]] + [(other, x) for x in b["sponsors"] + b["cosponsors"]]:
            if (h, n) in party_of:
                _PARTIES.setdefault(session, {})[(h, named(h, n))] = party_of[(h, n)]
        lead = b["authors"][0] if b["authors"] else ""
        vers = {"p": p, "sponsor": authors[0], "district": int((seat_of.get((origin, lead)) or "X:0")[2:]),
                "cosponsors": authors[1:] + co, "primes": len(authors), "cosp": len(authors[1:] + co),
                "statusDesc": desc, "committee": committee if place == "committee" and stage in (0, 2) else None,
                "actions": [[d, t] for d, _, t, _, _ in steps]}
        rec = {
            "nums": [p], "base": [p], "prev": earlier(session, p),
            "title": title, "summary": "", "act": "", "lawCode": "", "law": None, "laws": [],
            "comms": comm_list, "topics": topics, "places": [], "narrow": P.narrow_kind(title),
            "commFate": fate, "mainTopic": main_topic, "local": "local" in topics,
            "senDeleg": False, "asmDeleg": False, "budget": bool(re.search(r"general appropriations", b["caption"], re.I)),
            "passedS": "S" in passed, "passedA": "H" in passed, "program": None,
            "stage": stage, "passedIn": passed_in, "chapter": None,
            "veto": None, "memo": "", "vetoMemo": None,
            "comm": committee if stage == 0 and place == "committee" else None,
            "first": min(action_dates, default=f"{session}-01-01"),
            "last": max(action_dates, default=f"{session}-01-01"),
            "cosp": vers["cosp"],
            # Key dates: on the floor, passed the Senate, passed the House, (New York's return to committee in a new
            # year: none here), sent to the governor, signed, vetoed.
            "keyDates": [
                dates(lambda h, t, n: h == origin and n in (430, 435, 465, 400) and h == "H" or (h == origin == "S" and t == "REPORTED"), "first"),
                dates(lambda h, t, n: t == "PASSED SENATE", "all"),
                dates(lambda h, t, n: t == "PASSED HOUSE", "all"),
                "",
                dates(lambda h, t, n: t == "DELIVERED TO GOVERNOR"),
                dates(lambda h, t, n: t == "SIGNED"),
                dates(lambda h, t, n: t == "VETOED"),
            ],
            "votes": votes, "firstComms": first_comms, "vers": [vers],
        }
        index[p] = len(recs)
        recs.append(rec)
    return recs, index, fetched, {"SENATE": [], "ASSEMBLY": []}


def agendas(session):
    """Bills scheduled for committee hearings: bill -> [["House State Affairs", "2027-03-12T00:00:00"], ...]."""
    out = defaultdict(list)
    for p, b in bills(session).items():
        comm = {}
        for d, h, n, desc, _ in sorted(b["actions"], key=lambda a: a[0]):
            if h in HOUSE and is_referral(n, desc):
                comm[h] = desc[len("Referred to "):]
            if h in HOUSE and n == 228 and comm.get(h):
                entry = [f"{HOUSE[h]} {comm[h]}", f"{d}T00:00:00"]
                if entry not in out[p]:
                    out[p].append(entry)
    return dict(out)


_PARTIES = {}


def parties(session, recs):
    return {k: v for k, v in _PARTIES.get(session, {}).items() if v in ("D", "R")}


def seats():
    """(house, the name the histories use) -> seat id, party letter and full name, from the current legislators
    (data/tx/contacts_<session>.json, states/tx/contacts.py)."""
    seat_of, party_of, full = {}, {}, {}
    path = os.path.join(P.DATA, f"contacts_{CURRENT}.json")
    if os.path.exists(path):
        for sid, p in json.load(open(path))["people"].items():
            if p.get("dataName"):
                key = (sid[0], p["dataName"])
                seat_of[key], party_of[key], full[key] = sid, (p.get("party") or "")[:1], p["name"]
    return seat_of, party_of, full
