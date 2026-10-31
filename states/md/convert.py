"""Maryland's bills (downloaded by states/md/fetch.py) in the shape build_data.py reads. House and Senate bills of each
regular session; joint resolutions and special sessions are left out.

The bill list gives each bill's committees, the date and result of each step in each house (first reading and
referral, hearing, committee report, second and third reading), how the houses settled differences
("InteractionBetweenChambers"), whether the General Assembly passed it, its chapter number and its status ("Approved by
the Governor - Chapter 437", "Vetoed by the Governor (Policy)"). It has no dates for the governor's actions and no votes.
A committee's unfavorable report kills a bill; most such bills are then withdrawn by their sponsors.
"""
import json, os, re
from collections import defaultdict
from datetime import datetime
from zoneinfo import ZoneInfo

from states.md import profile as P

HOUSE = {"S": "Senate", "H": "House"}
CURRENT = P.session_of(datetime.now(ZoneInfo(P.TIMEZONE)).year)
_PARTIES = {}


def sessions():
    return sorted(int(f[12:16]) for f in os.listdir(P.DATA) if re.fullmatch(r"legislation_\d{4}RS\.json", f))


def text(x):
    return re.sub(r"\s+", " ", x or "").strip()


def load(session):
    return [b for b in json.load(open(os.path.join(P.DATA, f"legislation_{session}RS.json"))) if b["BillNumber"][:2] in ("HB", "SB")]


def number(n):
    return f"{n[:2]}{int(n[2:])}"


def contacts():
    paths = sorted(f for f in os.listdir(P.DATA) if re.fullmatch(r"contacts_\d{4}\.json", f))
    return json.load(open(os.path.join(P.DATA, paths[-1])))["people"] if paths else {}


_EARLIER = {}


def _titles(session):
    if session not in _EARLIER:
        out = defaultdict(list)
        if session in sessions():
            for b in load(session):
                out[text(b["Title"]).lower()].append((number(b["BillNumber"]), text(b["SponsorPrimary"])))
        _EARLIER[session] = out
    return _EARLIER[session]


def earlier(session, b):
    """The same bill in the two sessions before: the same title, with the same lead sponsor or only one bill so titled."""
    out = set()
    k, who = text(b["Title"]).lower(), text(b["SponsorPrimary"])
    for y in (session - 1, session - 2):
        old = _titles(y).get(k, [])
        same = [n for n, s in old if s == who]
        if same:
            out.add((y, same[0]))
        elif len(old) == 1 and len(_titles(session).get(k, [])) == 1 and len(k.split()) >= 4:
            out.add((y, old[0][0]))
    return out


def load_session(session):
    """Read one session's bills and return (records, bill number -> record index, fetched time, delegation)."""
    people = contacts()
    by_data = {(sid[0], p["dataName"]): p for sid, p in people.items()}
    parties = _PARTIES.setdefault(session, {})

    def who(name):
        """"Delegate Ebersole" -> "Eric Ebersole"; committees, delegations and "Departmental" as written."""
        m = re.match(r"(Delegate|Senator) (.+)", text(name))
        if not m:
            return text(name)
        h = "H" if m.group(1) == "Delegate" else "S"
        p = by_data.get((h, m.group(2)))
        full = p["name"] if p else m.group(2)
        if p and p.get("party"):
            parties[(h, full)] = p["party"][:1]
        return full

    path = os.path.join(P.DATA, f"legislation_{session}RS.json")
    fetched = datetime.fromtimestamp(os.path.getmtime(path), ZoneInfo(P.TIMEZONE)).strftime("%Y-%m-%d %H:%M")
    texts, recs, index = {}, [], {}
    for b in sorted(load(session), key=lambda b: (b["BillNumber"][0], int(b["BillNumber"][2:]))):
        p = number(b["BillNumber"])
        origin, other = p[0], "S" if p[0] == "H" else "H"
        status = text(b["Status"])
        day = lambda k: (b.get(k) or "")[:10]
        steps = []
        for h, side in ((origin, "HouseOfOrigin"), (other, "OppositeHouse")):
            comm = text(b.get(f"CommitteePrimary{'Origin' if side == 'HouseOfOrigin' else 'Opposite'}"))
            comm2 = text(b.get(f"CommitteeSecondary{'Origin' if side == 'HouseOfOrigin' else 'Opposite'}"))
            if day(f"FirstReadingDate{side}"):
                steps.append((day(f"FirstReadingDate{side}"), h, f"REFERRED TO {comm.upper()}" if comm else "First reading"))
                if comm2:
                    steps.append((day(f"FirstReadingDate{side}"), h, f"REFERRED TO {comm2.upper()}"))
            if day(f"HearingDateTimePrimary{side}"):
                steps.append((day(f"HearingDateTimePrimary{side}"), h, f"Hearing ({comm})" if comm else "Hearing"))
            rep = text(b.get(f"ReportAction{side}"))
            if day(f"ReportDate{side}") and rep:
                steps.append((day(f"ReportDate{side}"), h, "REPORTED" if rep.startswith("Favorable") else
                              f"{rep} report" if rep == "Unfavorable" else rep))
            if day(f"SecondReadingDate{side}") and not (day(f"ReportDate{side}") and rep):
                steps.append((day(f"SecondReadingDate{side}"), h, "REPORTED"))  # reported, though the list has no date for it
            if day(f"SecondReadingDate{side}"):
                amended = "amend" in text(b.get(f"SecondReadingAction{side}")).lower()
                steps.append((day(f"SecondReadingDate{side}"), h, "Second reading, amended" if amended else "Second reading"))
            third = text(b.get(f"ThirdReadingAction{side}"))
            if day(f"ThirdReadingDate{side}") and third:
                steps.append((day(f"ThirdReadingDate{side}"), h, f"PASSED {HOUSE[h].upper()}" if third.startswith("Passed") else f"Third reading {third.lower()}"))
        steps.sort(key=lambda s: s[0])
        last_day = max((s[0] for s in steps), default=f"{session}-01-01")
        passed = {s[1] for s in steps if s[2].startswith("PASSED")}
        chapter = re.search(r"CH(\d+)", b.get("ChapterNumber") or "")
        # A constitutional amendment gets a chapter number but goes to the voters, not the governor.
        amendment = b.get("ConstitutionalAmendment") and not status.startswith("Approved by the Governor")
        if amendment and chapter:
            stage, chapter = 3, None
            steps.append(("", "S", "Goes to the voters at the next general election"))
        elif chapter:
            stage = 5
            steps.append(("", "G", "SIGNED" if status.startswith("Approved") else status))
        # Every bill the General Assembly passes gets a chapter number unless the governor vetoes it; the status of a
        # vetoed bill sometimes shows a later motion instead ("Special Order vote on veto until next session").
        elif status.startswith("Vetoed") or (b.get("PassedByMGA") and (re.search(r"\bveto", status, re.I) or str(datetime.now().date()) > f"{session}-06-15")):
            stage = 6
            steps.append(("", "G", "VETOED"))
        elif b.get("PassedByMGA"):
            stage = 3
        elif passed:
            stage = 2
        else:
            stage = None
        if "line item veto" in status.lower():
            steps.append(("", "G", "Signed with item vetoes"))
        if stage is not None and stage >= 3:
            passed = {"S", "H"}
        # Where it is: the last house to act, in committee until its committee reports.
        where_h = other if origin in passed and stage == 2 else origin
        side = "OppositeHouse" if where_h == other else "HouseOfOrigin"
        comm = text(b.get(f"CommitteePrimary{'Opposite' if where_h == other else 'Origin'}"))
        rep = text(b.get(f"ReportAction{side}"))
        on_floor = rep.startswith("Favorable") or bool(day(f"SecondReadingDate{side}"))
        if stage is None:
            stage = 1 if on_floor else 0
        committee = comm if not on_floor and comm else None
        refs = [(s[1], s[2][len("REFERRED TO "):].title().replace(" And ", " and ").replace(" Of ", " of ").replace(" The ", " the ")) for s in steps if s[2].startswith("REFERRED TO")]
        refs = [(h, next((x for x in (b.get("CommitteePrimaryOrigin"), b.get("CommitteeSecondaryOrigin"), b.get("CommitteePrimaryOpposite"),
                                     b.get("CommitteeSecondaryOpposite")) if x and x.lower() == c.lower()), c)) for h, c in refs]
        comm_list = sorted({f"{h} · {c}" for h, c in refs})
        first_rep = text(b.get("ReportActionHouseOfOrigin"))
        fate = ("passed" if first_rep.startswith("Favorable") or origin in passed else "defeated" if first_rep == "Unfavorable" else
                "held" if first_rep in ("Withdrawn", "To Interim Study") or "Withdrawn" in status else "none")
        title = text(b["Title"])
        subjects = [s["Name"] for s in b.get("BroadSubjects") or []]
        topics = list(dict.fromkeys([v for s in subjects for k, v in P.SUBJECT_TOPICS.items() if s.startswith(k)]))
        if amendment:
            topics.insert(0, "const")
        topics = list(dict.fromkeys(topics + [k for k in P.TOPIC_WORDS if P.TOPIC_WORDS[k].search(title)]))
        names = [who(s["Name"]) for s in b.get("Sponsors") or []]
        sponsor = who(b.get("SponsorPrimary")) if b.get("SponsorPrimary") else (names[0] if names else "—")
        cos = [n for n in names if n != sponsor]
        if text(b.get("Synopsis")):
            texts[p] = {"statement": text(b["Synopsis"]), "label": "The Department of Legislative Services' synopsis"}
        if stage == 0 and committee:
            desc = f"In {HOUSE[where_h]} committee"
        elif stage <= 1 and on_floor:
            desc = f"On the {HOUSE[where_h]} floor"
        elif stage >= 2:
            desc = {2: f"Passed the {HOUSE[origin]}", 3: "Passed both houses", 4: "On the governor's desk",
                    5: "Signed into law", 6: "Vetoed"}[stage]
        else:
            desc = status

        def dates(test, mode="last"):
            ds = sorted({s[0] for s in steps if test(s[1], s[2]) and s[0]})
            return {"first": ds[0], "last": ds[-1], "all": ";".join(ds)}[mode] if ds else ""

        # The governor's actions have no dates here: they're shown on the last day of the bill's record.
        actions = [[s[0] or last_day, s[2]] for s in steps]
        rec = {
            "nums": [p], "base": [p], "prev": earlier(session, b),
            "title": title, "summary": "", "act": "", "lawCode": "", "law": None, "laws": [],
            "comms": comm_list, "topics": topics, "places": [], "narrow": P.narrow_kind(title),
            "commFate": fate, "mainTopic": topics[0] if topics else "", "local": "local" in topics or any("Local" in s for s in subjects),
            "senDeleg": False, "asmDeleg": False, "budget": any("Budget" in s for s in subjects),
            "passedS": "S" in passed, "passedA": "H" in passed, "program": "Administration" in text(b.get("SponsorPrimary")) or None,
            "stage": stage, "passedIn": HOUSE[origin] if stage == 2 else None, "chapter": int(chapter.group(1)) if chapter else None,
            "veto": None, "memo": "", "vetoMemo": None,
            "simText": f"{title} {text(b.get('Synopsis'))}",
            "comm": committee if stage == 0 else None,
            "first": min((s[0] for s in steps if s[0]), default=f"{session}-01-01"),
            "last": last_day,
            "cosp": len(cos),
            "keyDates": [
                dates(lambda h, t: t == "REPORTED", "first"),
                dates(lambda h, t: t == "PASSED SENATE", "all"),
                dates(lambda h, t: t == "PASSED HOUSE", "all"),
                "", "", "", "",
            ],
            "votes": [], "firstComms": [(refs[0][0], refs[0][1], fate == "passed")] if refs else [],
            "vers": [{"p": p, "sponsor": sponsor, "district": 0, "cosponsors": cos, "primes": 1, "cosp": len(cos),
                      "statusDesc": desc, "committee": committee if stage in (0, 2) else None, "actions": actions}],
        }
        index[p] = len(recs)
        recs.append(rec)
    json.dump(texts, open(os.path.join(P.DATA, f"texts_{session}.json"), "w"), ensure_ascii=False)
    return recs, index, fetched, {"SENATE": [], "ASSEMBLY": []}


def agendas(session):
    return {}


def parties(session, recs):
    return {k: v for k, v in _PARTIES.get(session, {}).items() if v in ("D", "R")}


def seats(session):
    return {p["id"]: sid for sid, p in contacts().items()}
