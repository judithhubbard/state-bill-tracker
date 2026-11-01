"""Wyoming's bills (downloaded by states/wy/fetch.py from the Legislative Service Office's API) in the shape build_data.py
reads. House Bills and Senate Files of each year's session, plus the joint resolutions that propose constitutional
amendments; other resolutions are left out.

Each action line begins with its house: "H Introduced and Referred to H09 - Minerals 59-2-1-0-0", "H09 -
Minerals:Recommend Amend and Do Pass 9-0-0-0-0", "H COW:Passed", "H 2nd Reading:Passed", "H 3rd Reading:Passed 53-4-5-0-0"
(the passage), "H Concur:Passed 47-12-3-0-0", "Assigned Number HEA No. 0016" (enrolled), "Governor Signed HEA No. 0016",
"Became Law without Signature", "Governor Vetoed HEA No. 0035", "Assigned Chapter Number 42". A tally's five numbers are
yes, no, excused, absent, conflict. Veto overrides appear only among the roll calls ("Veto Override 45-16-1-0-0"), so a
law is decided by its chapter number. In budget sessions (even years) a bill other than the budget needs two-thirds to be
introduced, and many end at "Failed Introduction". "What it does" is the LSO's bill summary (laws), else the official title's clauses.
"""
import glob, html, json, os, re
from datetime import datetime
from zoneinfo import ZoneInfo

from fetch_contacts import name_key
from states.wy import profile as P

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


def plain(h):
    """The digest's HTML -> paragraphs."""
    h = re.sub(r"(?s)<head.*?</head>|<style.*?</style>", "", h or "")
    h = re.sub(r"</p>|<br\s*/?>", "\n", h, flags=re.I)
    paras = [text(html.unescape(re.sub(r"<[^>]+>", " ", p))) for p in h.split("\n")]
    return [p for p in paras if p]


def summary(b):
    """The Legislative Service Office's bill summary (laws and a few others): the paragraphs under "Summary/Major
    Elements", up to its disclaimer."""
    paras = plain(b.get("summaryHTML"))
    i = next((i for i, x in enumerate(paras) if re.match(r"Summary/Major Elements", x)), None)
    if i is None:
        return []
    out = []
    for x in paras[i + 1:]:
        if re.match(r"The above summary is not", x):
            break
        if out or len(x.split()) > 6 or x.endswith("."):  # leading headings ("2025 Construction Projects") left out
            out.append(x)
    # Lead with what the bill does when the summary opens with the law as it stands.
    if len(out) > 1 and re.match(r"(?:Under )?(?:existing|current) law\b", out[0], re.I):
        out[0], out[1] = out[1], out[0]
    return out


# Verbs whose "-ing" form dropped an "e" (requiring -> requires), among the titles' clause-leading verbs.
E_STEMS = set("""provid requir authoriz revis declar remov calculat increas creat grant decreas revert us appropriat
notat reappropriat fil reclassify impos allocat designat justify commemorat exclud renam chang influenc conform expend driv
continu describ regulat restrict reduc cod cooperat prescrib terminat includ defin redirect oppos inser strik subject
disqualify revok preempt imped reauthoriz rul implement recogniz induc waiv updat resid renumber nominat approv reconstitut
surviv tabulat plac delet discharg licens encourag issu captur dedicat enforc mak eliminat
""".split()) - {"grant", "revert", "restrict", "redirect", "inser", "strik", "subject", "implement", "renumber", "disqualify",
                "reclassify", "justify", "expend", "impos", "conform", "preempt"} | {"impos", "strik", "enforc"}


def purpose(title):
    """The official title: "AN ACT relating to X; specifying ...; providing ...; and providing for an effective date." ->
    "Specifies ...; provides ...", without the stock closing clauses."""
    t = re.sub(r"^(?:AN ACT|A JOINT RESOLUTION) (?:relating to [^;]+;\s*)?", "", text(title), flags=re.I)
    parts = [re.sub(r"^and ", "", x.strip(" .")) for x in t.split(";")]
    parts = [x for x in parts if x and not re.match(r"providing (?:for )?(?:an )?effective dates?|providing for a delayed effective date|making conforming amendments", x, re.I)]
    def verb(x):
        w, _, rest = x.partition(" ")
        if re.fullmatch(r"\w+ly", w, re.I) and rest.split(" ")[0].endswith("ing"):  # "generally prohibiting ..."
            return f"{w.lower()} {verb(rest)}"
        w = w.lower()
        if not w.endswith("ing") or w in ("rulemaking", "standing", "sporting", "hunting", "fishing", "trapping"):
            return x
        w = w[:-3]
        if w in E_STEMS:
            w += "e"
        elif w in ("sett", "hir", "spend") or re.search(r"([bdgmnprt])\1$", w) and w not in ("add",):
            w = {"sett": "set", "hir": "hire"}.get(w, w[:-1] if re.search(r"([bdgmnprt])\1$", w) else w)
        v = (w[:-1] + "ies") if re.search(r"[^aeiou]y$", w) else (w + "es") if re.search(r"(s|sh|ch|x|z)$", w) else w + "s"
        return f"{v} {rest}".strip()
    out = "; ".join(verb(x) for x in parts[:6])
    return (out[:1].upper() + out[1:]).rstrip(" ;,") + "." if out else ""


def is_amendment(b):
    return b.get("billType") in ("HJ", "SJ") and bool(re.search(r"amend(?:ing|ment)?\b.*\bconstitution|constitutional amendment", text(b.get("billTitle")) + " " + text(b.get("catchTitle")), re.I))


def committee(a):
    m = re.search(r"\b[HSJ]\d{2} - ([^:]+?)(?::|\s+\d+-\d+|$)", a)
    return m.group(1).strip() if m else None


def decode(a, amendment):
    """One action line -> (house, shared wording)."""
    h = a[:1] if re.match(r"[HS] ", a) else ""
    low = a.lower()
    if re.search(r"introduced and referred to", low) and committee(a):
        return h, f"REFERRED TO {committee(a).upper()}"
    m = re.search(r"(?:re-?refer|^:?refer|referred) to ([HS])\d{2} - ([^:]+?)(?:\s+\d+-\d+.*)?$", a, re.I)
    if m:
        return m.group(1).upper(), f"REFERRED TO {m.group(2).strip().upper()}"
    if re.match(r"[hsj]\d{2} - [^:]+:recommend (?:amend and )?do pass", low):
        return a[:1].upper() if a[:1] in "HS" else h, "REPORTED"
    if re.match(r"[hsj]\d{2} - [^:]+:(?:recommend do not pass|do pass failed)", low):
        return a[:1].upper() if a[:1] in "HS" else h, "Committee voted it down"
    if re.search(r"died in committee returned bill|no report prior to cow cutoff", low):
        return h or "G", "No committee report by the deadline"
    if re.search(r"did not consider for cow", low):
        return h, "Not taken up by the Committee of the Whole"
    if re.search(r"postponed indefinitely", low):
        return h, "Postponed indefinitely"
    if re.search(r"placed on general file|cow:passed|2nd reading:passed", low):
        return h, "PLACED ON FLOOR"
    if re.search(r"3rd reading:passed", low):
        return h, f"PASSED {HOUSE.get(h, 'HOUSE').upper()}"
    if re.search(r"failed introduction|did not consider for introduction", low):
        return h, "FAILED INTRODUCTION"
    if re.search(r"(?:3rd reading|cow|2nd reading):failed", low):
        return h, "FAILED"
    if re.search(r"concur:passed|recede from non-concurrence passed|jcc\d* report adopted|adopted jcc", low):
        return h, "CONCURRED"
    if re.match(r"assigned number [hs]ea no", low):
        return "G", "ENROLLED"
    if amendment:
        return h or "G", a
    if re.match(r"governor signed and line item vetoed|governor line-item vetoed", low):
        return "G", "Signed with item vetoes"
    if re.match(r"governor signed|became law without signature", low):
        return "G", "SIGNED"
    if re.match(r"governor vetoed", low):
        return "G", "VETOED"
    return h or "G", a


def tally(a):
    m = re.search(r"(\d+)-(\d+)-\d+-\d+-\d+\s*$", a)
    return (int(m.group(1)), int(m.group(2))) if m else None


def load_session(session):
    """Read one year's bills and return (records, bill number -> record index, fetched time, delegation)."""
    path = os.path.join(P.DATA, f"contacts_{session}.json")
    if not os.path.exists(path):
        paths = sorted(glob.glob(os.path.join(P.DATA, "contacts_*.json")))
        path = paths[-1] if paths else ""
    contacts = json.load(open(path)) if path else {}
    people = contacts.get("people", {})
    comm_members = {"S": contacts.get("senateCommittees", {}), "H": contacts.get("assemblyCommittees", {})}
    # Roll-call names: floor "Campbell, K" (the members' voteName), committee "CAMPBELL" (last name in capitals).
    by_vote = {(sid[0], p["id"]): sid for sid, p in people.items()}
    lasts = {}
    for sid, p in people.items():
        lasts.setdefault((sid[0], p["id"].split(",")[0].upper()), set()).add(sid)
    by_upper = {k: next(iter(v)) for k, v in lasts.items() if len(v) == 1}
    by_last_name = {}
    for sid, p in people.items():
        by_last_name.setdefault((sid[0], p["name"].split()[-1]), []).append(sid)
    # Everyone who served that year, those who left included (for sponsors' names): (house, voteName) -> member.
    served = {}
    # A year's list can miss someone who left (Pearson, 2026), so the years around it fill in.
    for y, h in [(y, h) for y in (session, session - 1, session + 1, session - 2) for h in HOUSE]:
        try:
            for m in json.load(open(os.path.join(folder(y), f"members_{h}.json"))):
                served.setdefault((h, m.get("voteName") or m["name"].split()[-1]), m)
        except (OSError, ValueError):
            pass
    known = {v for (_, v) in served} | {p["id"] for p in people.values()}
    surnames = {v.split(",")[0] for v in known}
    by_surname = {}
    for (h, v), m in served.items():
        by_surname.setdefault((h, v.split(",")[0]), []).append(m)
    parties = _PARTIES.setdefault(session, {})
    files = glob.glob(os.path.join(folder(session), "bills", "*.json"))
    fetched = datetime.fromtimestamp(max(os.path.getmtime(f) for f in files), ZoneInfo(P.TIMEZONE)).strftime("%Y-%m-%d %H:%M")
    texts, recs, index = {}, [], {}
    for f in sorted(files, key=lambda f: (os.path.basename(f)[0], int(re.sub(r"\D", "", os.path.basename(f)) or 0))):
        b = json.load(open(f))
        kind = b.get("billType")
        amendment = is_amendment(b)
        if kind not in ("HB", "SF") and not amendment:
            continue
        p = f"{kind}{int(re.sub(r'\D', '', b['bill']))}"
        origin = p[0]
        other = "S" if origin == "H" else "H"
        acts = sorted(reversed(b.get("billActions") or []), key=lambda a: a.get("statusDate") or "")  # newest first, same-minute ties too
        steps = [((a.get("statusDate") or "")[:10],) + decode(text(a.get("statusMessage")), amendment) + (text(a.get("statusMessage")),) for a in acts]
        steps = [(d, h if h else ({"House": "H", "Senate": "S"}.get(text(a.get("location")), "G")), t, x) for (d, h, t, x), a in zip(steps, acts)]
        # Veto override votes appear only among the roll calls: add them to the history, as written.
        for r in b.get("rollCalls") or []:
            m = re.search(r"Override.*?(\d+)-(\d+)-\d+-\d+-\d+", text(r.get("action")))
            if m and r.get("chamber") in HOUSE:
                ok = not re.search(r"did not|failed", r["action"], re.I)  # "Did Not Override Veto 35-27" (two-thirds needed)
                line = f"{HOUSE[r['chamber']]} {'voted to override' if ok else 'failed to override'} the veto, {m.group(1)}-{m.group(2)}"
                steps.append(((r.get("voteDate") or "")[:10], r["chamber"], line, line))
        steps.sort(key=lambda s: (s[0], s[3].startswith("Assigned Chapter")))  # the chapter number follows the override
        passed = {s[1] for s in steps if s[2].startswith("PASSED")}
        texts_ = [s[2] for s in steps]
        chapter = (re.search(r"\d+", str(b.get("chapter") or ""))
                   or next((m for s in steps for m in [re.match(r"Assigned Chapter Number (\d+)", s[3])] if m), None))
        if amendment:
            stage = 3 if "ENROLLED" in texts_ else None
        elif chapter:
            stage = 5  # signed, without signature, or passed over a veto (the override is only among the roll calls)
        elif "VETOED" in texts_:
            stage = 6
        elif "ENROLLED" in texts_:
            stage = 4
        elif len(passed) == 2 and ("CONCURRED" in texts_ or not any(re.search(r"Received for Concurrence", s[3]) for s in steps)):
            stage = 3  # the second house passed it unchanged, or the first agreed to its changes (not: died in conference)
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
        proper = lambda c: re.sub(r"\b(And|Of|The|On|For|To|In)\b", lambda m: m.group(1).lower(), c.title())
        comm = proper(comm) if comm else None
        refs = [(s[1] if s[1] in HOUSE else origin, proper(s[2][len("REFERRED TO "):])) for s in steps if s[2].startswith("REFERRED TO")]
        comm_list = sorted({f"{h} · {c}" for h, c in refs})
        title = text(b.get("catchTitle")).rstrip(".") or text(b.get("billTitle"))
        if amendment and not re.match(r"constitution", title, re.I):
            title = f"Constitutional amendment: {title[:1].lower() + title[1:]}"
        long_title = text(b.get("billTitle"))
        topics = list(dict.fromkeys((["const"] if amendment else []) +
                                    [v for k, v in P.COMMITTEE_TOPICS.items() if any(k.lower() in c.lower() for _, c in refs)] +
                                    [k for k in P.TOPIC_WORDS if P.TOPIC_WORDS[k].search(f"{title} {long_title}")]))
        left = any(t in ("REPORTED",) or t.startswith("PASSED") for _, _, t, _ in steps)
        fate = ("passed" if left else "defeated" if "Committee voted it down" in texts_
                else "held" if "FAILED INTRODUCTION" in texts_ else "none")
        names = []
        for s in sorted(b.get("sponsors") or [], key=lambda s: not s.get("primarySponsor")):
            n = text(s.get("name"))
            h = s.get("house")
            if h not in HOUSE:  # a committee ("Water"): its full name is in the digest ("Sponsored By: Select Water Committee")
                m = re.search(r"Sponsored By:\s*([^<]*?Committee)", html.unescape(re.sub(r"<[^>]+>", " ", b.get("digestHTML") or "")))
                n = text(m.group(1)) if m else {"Mgt Council": "Management Council"}.get(n, f"{n} Committee")
            m = served.get((h, n)) or (lambda ms: ms[0] if len(ms) == 1 else None)(by_surname.get((h, n.split(",")[0]), []))
            full = text(m["name"]) if m else n
            if m and m.get("party"):
                parties[(h, full)] = m["party"][:1]
            if full and full not in names:
                names.append(full)
        sponsor = names[0] if names else "—"
        cos = names[1:]
        what = summary(b)
        if what:
            texts[p] = {"statement": "\n".join(what[:8]), "label": "From the Legislative Service Office's bill summary."}
        elif purpose(long_title):
            texts[p] = {"statement": purpose(long_title), "label": "From the bill's official title."}
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

        def seat(h, name, committee_vote, cname=None, both=False):
            """A roll-call name -> seat id: floor "Campbell, K" or "President Driskill", committee "CAMPBELL" (where two
            members share the surname, the one on the committee)."""
            n = re.sub(r"^(?:President|Speaker|Vice President|Chairman|Chairwoman)\s+", "", text(name))
            sur, _, first = n.partition(",")
            sid = by_vote.get((h, n)) or by_upper.get((h, sur.upper()))
            if not sid and first.strip():  # two members share the surname: "Zwonitzer, Dan", "Brown, G"
                hits = [x for x in lasts.get((h, sur.upper()), ()) if people[x]["name"].startswith(first.strip().rstrip("."))]
                sid = hits[0] if len(hits) == 1 else None
            if not sid and both:  # a conference committee's vote lists members of both houses
                o = "S" if h == "H" else "H"
                sid = by_vote.get((o, n)) or by_upper.get((o, sur.upper()))
            if not sid and committee_vote and cname:
                on = {name_key(x) for c in comm_members[h].values() if c["name"].lower().endswith(cname.lower()) or cname.lower() in c["name"].lower() for x in c["members"]}
                hits = [sid for sid in lasts.get((h, n.upper()), ()) if name_key(people[sid]["name"]) in on]
                sid = hits[0] if len(hits) == 1 else None
            return sid or f"{h}?{n.title() if committee_vote else n}"

        def split_names(s, is_comm):
            """"Allemand, Brown, G, Larson, JT, Burkhart, Jr, Larsen, Lloyd" -> names: a piece after a comma that is an
            initial, a suffix, or makes a known member's name with the one before belongs to it."""
            out = []
            for x in [x.strip() for x in (s or "").split(",") if x.strip()]:
                if out and is_comm and re.fullmatch(r"[A-Z]{1,2}\.?|JR\.?", x):  # "SMITH, S"
                    out[-1] += ", " + x
                elif out and not is_comm and (f"{out[-1]}, {x}" in known or re.fullmatch(r"[A-Z][A-Za-z]?\.?|[A-Z]{2,3}|Jr\.?|Sr\.?|I{2,3}", x)
                            or ("," not in out[-1] and x not in surnames and re.fullmatch(r"[A-Z][a-z]{2,6}", x))):  # "Larsen, Lloyd"
                    out[-1] += ", " + x
                else:
                    out.append(x)
            return out

        votes = []
        for r in b.get("rollCalls") or []:
            # The action names its house ("S Introduced ...", "H02 - Appropriations: ..."); the chamber field is sometimes wrong.
            h = (lambda a: a[:1] if re.match(r"[HS](?: |\d{2} - )", a) else r.get("chamber") if r.get("chamber") in HOUSE else None)(text(r.get("action")))
            act = text(r.get("action"))
            if not h:
                continue
            is_comm = r.get("voteType") == "C" or (r.get("voteID") or 0) < 0
            if not is_comm and not re.search(r"3rd Reading|Concur|JCC|Override|Introduc|COW", act, re.I):
                continue
            no = split_names(r.get("noVotes"), is_comm)  # committee lists are surnames in capitals
            nv = [x for k in ("excusedVotes", "absentVotes", "conflictVotes") for x in split_names(r.get(k), is_comm)]
            cname = committee(act) if is_comm else None
            both = bool(re.search(r"JCC", act))
            names_ = [[seat(h, x, is_comm, cname, both), "N"] for x in no] + [[seat(h, x, is_comm, cname, both), "A"] for x in nv]
            votes.append([h, "C" if is_comm else "F", proper(cname) if cname else None, (r.get("voteDate") or "")[:10],
                          int(r.get("yesVotesCount") or 0), int(r.get("noVotesCount") or len(no)), names_])
        votes.sort(key=lambda v: v[3])
        action_dates = [s[0] for s in steps if s[0]]
        rec = {
            "nums": [p], "base": [p], "prev": earlier(session, b, p),
            "title": title, "summary": long_title, "act": "", "lawCode": "", "law": None, "laws": [],
            "comms": comm_list, "topics": topics, "places": [], "narrow": P.narrow_kind(title),
            "commFate": fate, "mainTopic": topics[0] if topics else "", "local": "local" in topics,
            "senDeleg": False, "asmDeleg": False, "budget": bool(re.search(r"general government appropriations|\bbudget\b", long_title, re.I)),
            "passedS": "S" in passed, "passedA": "H" in passed, "program": None,
            "stage": stage, "passedIn": (HOUSE[origin] if origin in passed else HOUSE[other]) if stage == 2 else None,
            "chapter": int(chapter.group(chapter.lastindex or 0)) if chapter and stage == 5 else None,
            "veto": None, "memo": "", "vetoMemo": None,
            "simText": f"{title} {long_title}",
            "comm": comm if stage == 0 and place == "committee" else None,
            "first": min(action_dates, default=f"{session}-01-01"),
            "last": max(action_dates, default=f"{session}-01-01"),
            "cosp": len(cos),
            "keyDates": [
                dates(lambda h, t: t == "REPORTED", "first"),
                dates(lambda h, t: t == "PASSED SENATE", "all"),
                dates(lambda h, t: t == "PASSED HOUSE", "all"),
                "",
                dates(lambda h, t: t == "ENROLLED") if stage >= 4 and not amendment else "",
                dates(lambda h, t: t == "SIGNED") or (max(action_dates, default="") if stage == 5 else ""),
                dates(lambda h, t: t == "VETOED"),
            ],
            "votes": votes, "firstComms": [(refs[0][0], refs[0][1], left)] if refs else [],
            "vers": [{"p": p, "sponsor": sponsor, "district": 0, "cosponsors": cos, "primes": 1, "cosp": len(cos),
                      "statusDesc": desc, "committee": comm if place == "committee" and stage in (0, 2) else None,
                      "actions": [[s[0], s[2]] for s in steps]}],
        }
        index[p] = len(recs)
        recs.append(rec)
    json.dump(texts, open(os.path.join(P.DATA, f"texts_{session}.json"), "w"), ensure_ascii=False)
    return recs, index, fetched, {"SENATE": [], "ASSEMBLY": []}


_TITLES = {}


def _titles(session):
    if session not in _TITLES:
        out = {}
        for f in glob.glob(os.path.join(folder(session), "bills", "*.json")):
            b = json.load(open(f))
            sp = next((s.get("name") for s in b.get("sponsors") or [] if s.get("primarySponsor")), "")
            if not re.search(r"\d", str(b.get("chapter") or "")):  # a law isn't tried again (yearly bills share titles)
                out.setdefault(text(b.get("catchTitle")).lower(), []).append((f"{b.get('billType')}{int(re.sub(r'\D', '', b['bill']))}", sp))
        _TITLES[session] = out
    return _TITLES[session]


def earlier(session, b, p):
    """The same bill in the two years before: the same catch title, with the same prime sponsor (or committee) or a title
    only one bill has in each year."""
    out = set()
    k = text(b.get("catchTitle")).lower()
    who = next((s.get("name") for s in b.get("sponsors") or [] if s.get("primarySponsor")), "")
    if len(k.split()) < 2:
        return out
    for y in (session - 1, session - 2):
        if y not in sessions():
            continue
        old = _titles(y).get(k, [])
        same = [n for n, sp in old if sp and sp == who]
        if same:
            out.add((y, same[0]))
        elif len(old) == 1 and len(_titles(session).get(k, [])) == 1:
            out.add((y, old[0][0]))
    return out


def agendas(session):
    return {}


def parties(session, recs):
    return {k: v for k, v in _PARTIES.get(session, {}).items() if v in ("D", "R")}
