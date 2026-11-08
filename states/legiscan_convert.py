"""Reading LegiScan's downloaded files (legiscan.py) into the record shape build_data.py reads, for the states whose
legislatures' websites turn automated readers away: Tennessee, Oklahoma, Maine, Rhode Island and Vermont. Never calls
LegiScan's API: only data/<st>/legiscan/<session_id>/ (bill/<number>.json, vote/<roll_call_id>.json,
people/<people_id>.json, meta.json; see legiscan.py's docstring). LegiScan's data is CC BY 4.0: every page built from it
credits LegiScan in "About this data" (each state's how.html) and links each bill to its LegiScan page.

A state's convert.py subclasses `Rules`, saying what's particular to it (which bills to show, how its history lines read,
its committees, titles, topics, links), and passes it to `load_session()`. What's shared:

- Sessions: each regular session's folder, keyed by its first year (`year_start`): a two-year session (Tennessee's General
  Assembly) is "2025", as for California and Washington.
- Steps: the state's `decode()` turns each history line into steps of one shared vocabulary (KINDS below), each with the
  house where it happened. Stages, the committee a bill is in, its first committee's fate and its key dates are worked
  out from the steps, never from LegiScan's `status` or `progress` (summaries: Tennessee's vetoes are "Enrolled" there).
  `check()` compares the two and is printed by `python3 states/<st>/convert.py`.
- Companions: `Rules.group()` can put bills together as one record (Tennessee files every bill twice, a House and a
  Senate number with the same text: LegiScan's `sasts` "Crossfiled"). Steps from all of them are read in date order,
  each house's state kept apart: a House bill passed and received in the Senate is "in the Senate committee" while its
  Senate companion is there.
- Passed both houses: enrolled (`enrolled`), or both houses passed it and the second didn't amend it, or the first agreed
  to the second's changes (`concur` after the last passage), or both houses adopted a conference report. A passage the
  house reconsidered (`reconsider` right after it) doesn't count until it passes again.
- Laws: signed, law without signature, a veto overridden by both houses, or a chapter number without a veto that stood.
  Constitutional amendments stop at stage 3 (they go to the voters).
- Votes: roll calls member by member (vote/<id>.json), tied to a history step: a floor vote has the date and house of a
  passage, concurrence, conference report or override and the same tally (LegiScan attaches some roll calls to the wrong
  bill: Tennessee's SB 5 of 2025 carries another bill's House votes); a committee vote, the date and house of a committee
  step. Noes are "N", not voting or absent "A"; members by seat ("S:12") when `Rules.seat()` knows them, else "S?Name".
"""
import glob, html, json, os, re
from collections import defaultdict

# The shared step vocabulary a state's decode() returns: (house, kind, text, extra).
#   refer (extra: comm), report (a committee approved it; extra comm), subreport (a subcommittee did), held (set aside
#   without a vote), commfail (voted down in committee), floor (placed on a floor calendar), pass (extra amended=True when
#   the house amended it), fail (failed on the floor), reconsider, concur (agreed to the other house's changes), ccr
#   (a conference report adopted by this house), enrolled, sent (to the governor), signed, nosign (law without signature),
#   veto, override (this house overrode the veto), chapter (extra num, private=True for a private/local act), withdrawn,
#   recall, unsent (the governor gave it back before acting: Tennessee's SB 1758 of 2026), replaced (this number gave way to
#   its companion, which carries on), None (kept as written; changes nothing).
KINDS = {"refer", "report", "subreport", "held", "commfail", "floor", "pass", "fail", "reconsider", "concur", "ccr",
         "enrolled", "sent", "signed", "nosign", "veto", "override", "chapter", "withdrawn", "recall", "unsent", "replaced", None}
HOUSE = {"S": "Senate", "H": "House"}
CREDIT = "LegiScan"
CREDIT_URL = "https://legiscan.com/"


def text(x):
    return re.sub(r"\s+", " ", html.unescape(x or "")).strip()


def read_json(path, default=None):
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def folders(data_dir):
    """{first year: folder} for each regular session downloaded with at least 100 bills."""
    out = {}
    for f in glob.glob(os.path.join(data_dir, "legiscan", "*", "meta.json")):
        meta = read_json(f, {}) or {}
        s = meta.get("session") or {}
        folder = os.path.dirname(f)
        if s.get("special") or len(glob.glob(os.path.join(folder, "bill", "*.json"))) < 100:
            continue
        out[int(s["year_start"])] = folder
    return dict(sorted(out.items()))


def bills(folder):
    for f in sorted(glob.glob(os.path.join(folder, "bill", "*.json"))):
        b = (read_json(f) or {}).get("bill")
        if b:
            yield b


def people(folder):
    """people_id -> LegiScan's person record (everyone who served in the session, those who left included)."""
    out = {}
    for f in glob.glob(os.path.join(folder, "people", "*.json")):
        p = (read_json(f) or {}).get("person")
        if p:
            out[p["people_id"]] = p
    return out


def person_house(p, default=None):
    """A person's house from the district ("SD-028", "HD-075"): LegiScan's `role` is sometimes stale (Tennessee's Joseph
    Hensley, a senator since 2013, is "Rep" in 2023-24's people)."""
    d = (p.get("district") or "").upper()
    return "S" if d.startswith("SD") else "H" if d.startswith("HD") else default or {"Sen": "S", "Rep": "H"}.get(p.get("role"))


def district_of(p):
    m = re.search(r"(\d+)\s*([A-Z]?)$", p.get("district") or "")
    return int(m.group(1)) if m else 0


def number(bill_number):
    """"HB0005" -> "HB5", "SJR0001" -> "SJR1"."""
    m = re.match(r"([A-Z]+)0*(\d+)$", bill_number)
    return f"{m.group(1)}{m.group(2)}" if m else bill_number


def fetched(folder):
    """When the newest bill in the folder was read (meta.json), as "YYYY-MM-DD HH:MM" UTC."""
    from datetime import datetime, timezone
    meta = read_json(os.path.join(folder, "meta.json"), {}) or {}
    t = max((b.get("fetched") or 0 for b in (meta.get("bills") or {}).values()), default=0)
    if not t:
        return (meta.get("dataset_date") or "") + " 00:00"
    return datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%d %H:%M")


class Rules:
    """What a state's convert.py says about its own data. Override what differs."""
    data_dir = ""          # data/<st>
    lower = "H"
    gates = set()          # committees that schedule floor votes (a report sending a bill there sends it to the floor)

    def __init__(self):
        self.parties_ = {}   # session -> {(house, name): "D"/"R"}
        self.checks = {}     # session -> LegiScan's status against the stages here

    def include(self, b):
        """"bill", "amendment" (a constitutional amendment), or None to leave it out."""
        return "bill" if b.get("bill_type") == "B" else None

    def decode(self, action, chamber, b, kind):
        """One history line -> [(house, kind, text, extra)]; house "" where the line names none."""
        return [(chamber, None, action, {})]

    def committee_vote(self, desc):
        """A roll call's description -> the committee's name if it's a committee vote, else None (a floor vote)."""
        return None

    def floor_vote(self, desc):
        """Whether a floor roll call can be a vote on the bill itself (not on an amendment or a motion)."""
        return not re.search(r"amend", desc or "", re.I)

    def group(self, bills_by_number):
        """Lists of bill numbers shown as one record. Default: each alone."""
        return [[n] for n in bills_by_number]

    def title(self, b):
        return text(b.get("title"))

    def summary(self, b):
        return text(b.get("description"))

    def what(self, b):
        """("What it does" text, "From the ....") or None."""
        return None

    def topics(self, b, comms, title):
        return []

    def narrow(self, b, title):
        return ""

    def link(self, b):
        return b.get("state_link") or b.get("url") or ""

    def seat(self, session, people_id, house, name):
        """A member's seat id for votes ("S:12"), or None."""
        return None

    def comm_name(self, name):
        return name

    def earlier_key(self, b, kind):
        """The text that finds the same bill in an earlier session (None: never linked)."""
        return None


def sort_steps(steps):
    """By day, keeping each version's own order within a day (the file's order)."""
    return sorted(steps, key=lambda s: s["date"])


def rank(stage):
    return {None: -1, 0: 0, 1: 1, 2: 2, 3: 3, 4: 4, 6: 5, 5: 6}[stage]


def work_out(steps, origin, kind):
    """The stage and where it is from one record's steps (all versions, in date order). Returns a dict."""
    passed = {}   # house -> date of its standing passage (any version)
    # Per version: its standing passages, whether the later one amended it, whether the first house then agreed. Both
    # houses passing different versions (a House bill and its Senate companion, each in its own house) isn't both.
    vpass, vamended, vconcur = defaultdict(dict), {}, {}
    ccr = set()
    enrolled = sent = signed = nosign = vetoed = False
    overrides, chapters = set(), []
    place = {"S": ("desk", None), "H": ("desk", None)}
    now = origin
    last_vote = {}  # house -> kind of its last floor step (for a reconsideration)
    for s in steps:
        h, k = s["house"], s["kind"]
        if k == "refer" and h in HOUSE:
            place[h] = ("committee", s["comm"])
        elif k in ("report", "floor") and h in HOUSE:
            if place[h][0] != "floor" or k == "floor":
                place[h] = ("floor", None)
        elif k == "recall" and h in HOUSE:
            place[h] = ("desk", None)
        elif k == "pass" and h in HOUSE:
            passed[h] = s["date"]
            vpass[s["ver"]][h] = s["date"]
            vamended[s["ver"]], vconcur[s["ver"]] = bool(s["extra"].get("amended")), False
            place[h] = ("desk", None)
            now = "S" if h == "H" else "H"
        elif k == "reconsider" and h in HOUSE and last_vote.get(h) == "pass":
            passed.pop(h, None)
            for v in vpass.values():
                v.pop(h, None)
            place[h] = ("floor", None)
            now = h
        elif k == "concur":
            vconcur[s["ver"]] = True
        elif k == "ccr" and h in HOUSE:
            ccr.add(h)
        elif k == "enrolled":
            enrolled = True
        elif k == "sent":
            sent = True
        elif k == "unsent":
            sent = False
        elif k == "signed":
            signed = True
        elif k == "nosign":
            nosign = True
        elif k == "veto":
            vetoed = True
        elif k == "override" and h in HOUSE:
            overrides.add(h)
        elif k == "chapter":
            chapters.append(s["extra"])
        if h in HOUSE and k in ("pass", "fail", "concur", "ccr", "reconsider", "floor"):
            last_vote[h] = k
    both = enrolled or ccr >= {"S", "H"} or any(len(p) == 2 and (not vamended.get(v) or vconcur.get(v)) for v, p in vpass.items())
    overridden = overrides >= {"S", "H"}
    if kind == "amendment":
        stage = 3 if both else 2 if passed else None
    elif signed or nosign or (vetoed and overridden) or (chapters and not vetoed):
        stage = 5
    elif vetoed:
        stage = 6
    elif sent:
        stage = 4
    elif both:
        stage = 3
    elif passed:
        stage = 2
    else:
        stage = None
    where, comm = place[now]
    if stage is None:
        stage = 1 if where == "floor" else 0
    return {"stage": stage, "passed": set(passed) | ({"S", "H"} if stage >= 3 else set()), "now": now, "place": where,
            "comm": comm, "overridden": overridden and vetoed,
            "chapter": next((c for c in chapters if not c.get("companion")), chapters[0] if chapters else None)}


def tally_of(t):
    m = re.search(r"Ayes,?\s*\(?(\d+)\)?,?\s*Nay\w*\s*\(?(\d+)", t or "", re.I)
    return (int(m.group(1)), int(m.group(2))) if m else None


class Session:
    """One session's files, read once."""

    def __init__(self, rules, session):
        self.R, self.session = rules, session
        self.folder = folders(rules.data_dir)[session]
        self.people = people(self.folder)
        self._votes = {}

    def roll_call(self, rid):
        if rid not in self._votes:
            self._votes[rid] = (read_json(os.path.join(self.folder, "vote", f"{rid}.json")) or {}).get("roll_call")
        return self._votes[rid]

    def member(self, pid, house):
        p = self.people.get(pid) or {}
        name = text(p.get("name")) or str(pid)
        return self.R.seat(self.session, pid, house, name) or f"{house}?{name}"

    def votes(self, bs, steps):
        """Roll calls tied to the record's steps, as [house, "F"/"C", committee, date, yes, no, [[seat, code]]]."""
        R = self.R
        floor_steps = [s for s in steps if s["house"] in HOUSE and s["kind"] in ("pass", "fail", "concur", "ccr", "override")]
        comm_days = {(s["house"], s["date"]) for s in steps if s["house"] in HOUSE and s["kind"] in
                     ("report", "subreport", "commfail", "refer", "held", None)}
        calls, seen = [], set()
        for b in bs:
            for v in b.get("votes") or []:
                rid = v.get("roll_call_id")
                if rid in seen:
                    continue
                seen.add(rid)
                r = self.roll_call(rid) or v
                calls.append(r)
        out, used = [], set()
        for r in sorted(calls, key=lambda r: (r.get("date") or "", r.get("roll_call_id") or 0)):
            h, d, desc = r.get("chamber"), r.get("date") or "", text(r.get("desc"))
            if h not in HOUSE:
                continue
            comm = R.committee_vote(desc)
            if comm:
                if (h, d) not in comm_days:
                    continue  # no committee step that day: not this bill's vote
                kind = "C"
            else:
                if not R.floor_vote(desc):
                    continue
                same = [s for s in floor_steps if s["house"] == h and s["date"] == d and id(s) not in used]
                tl = (int(r.get("yea") or 0), int(r.get("nay") or 0))
                # The history's tally is the journal's and can differ from the roll call by a vote or two (Tennessee's
                # "Passed H., as am., Ayes 60, Nays 30" for a roll call of 60-29): the nearest within 5, and the roll
                # call's own totals are kept. A line without a tally takes the day's only floor roll call.
                near = sorted((abs(s["tally"][0] - tl[0]) + abs(s["tally"][1] - tl[1]), i) for i, s in enumerate(same) if s["tally"])
                hit = same[near[0][1]] if near and near[0][0] <= 5 else \
                    next((s for s in same if not s["tally"] and not any(c is not r and c.get("chamber") == h and c.get("date") == d
                                                                    and R.floor_vote(text(c.get("desc"))) for c in calls)), None)
                if not hit:
                    continue  # a vote on an amendment or a motion, or another bill's
                used.add(id(hit))
                kind = "F"
            key = (h, kind, comm, d, r.get("yea"), r.get("nay"))
            if key in used:
                continue  # the same vote recorded twice
            used.add(key)
            names = [[self.member(m["people_id"], h), "N" if m.get("vote_text") == "Nay" else "A"]
                     for m in r.get("votes") or [] if m.get("vote_text") != "Yea"]
            out.append([h, kind, comm, d, int(r.get("yea") or 0), int(r.get("nay") or 0), names])
        return out


def load_session(R, session):
    """(records, number -> record index, fetched time, delegation) for build_data.py, plus R.checks[session] (LegiScan's
    own status against the stages worked out here)."""
    S = Session(R, session)
    by_num = {}
    kinds = {}
    for b in bills(S.folder):
        k = R.include(b)
        if k:
            n = number(b["bill_number"])
            by_num[n], kinds[n] = b, k
    parties = {}
    for p in S.people.values():
        if p.get("party") in ("D", "R"):
            parties[(person_house(p), text(p.get("name")))] = p["party"]
    R.parties_[session] = parties
    texts, recs, index = {}, [], {}
    check = defaultdict(int)
    for group in R.group(by_num):
        bs = [by_num[n] for n in group]
        kind = "amendment" if any(kinds[n] == "amendment" for n in group) else "bill"
        vers_steps = {}
        for b in bs:
            n = number(b["bill_number"])
            st = []
            for i, a in enumerate(b.get("history") or []):
                written = text(a.get("action"))
                ch = a.get("chamber") if a.get("chamber") in HOUSE else ""
                for h, k, t, extra in R.decode(written, ch, b, kind):
                    if h not in HOUSE:
                        h = "G" if k in ("signed", "nosign", "veto", "chapter", "sent") else (ch or "G")
                    st.append({"date": (a.get("date") or "")[:10], "house": h, "kind": k, "text": t, "written": written,
                               "comm": R.comm_name(extra.get("comm")) if extra.get("comm") else None, "extra": extra,
                               "tally": tally_of(written), "ver": n})
            vers_steps[n] = sort_steps(st)
        # Each version alone (to pick the lead), then all together.
        alone = {n: work_out(vers_steps[n], n[0], kind) for n in vers_steps}
        order = sorted(vers_steps, key=lambda n: (-rank(alone[n]["stage"]), -len(vers_steps[n]), n))
        steps = sort_steps([s for n in order for s in vers_steps[n]])
        lead_n = order[0]
        lead = by_num[lead_n]
        origin = lead_n[0]
        w = work_out(steps, origin, kind)
        stage, passed = w["stage"], w["passed"]
        other = "S" if origin == "H" else "H"
        # LegiScan's own status (1 introduced, 2 engrossed, 3 enrolled, 4 passed, 5 vetoed, 6 failed) for the check.
        st_max = max(int(b.get("status") or 0) for b in bs)
        if kind == "bill":
            check["laws"] += stage == 5
            check["vetoes"] += stage == 6
            check["legiscan passed"] += st_max == 4
            check["legiscan vetoed"] += st_max == 5
            check["law here, not passed in LegiScan"] += stage == 5 and st_max != 4
            check["passed in LegiScan, not a law here"] += st_max == 4 and stage != 5
            check["vetoed in LegiScan, not here"] += st_max == 5 and stage != 6
        refs = [(s["house"], s["comm"]) for s in steps if s["kind"] == "refer" and s["house"] in HOUSE]
        comm_list = sorted({f"{h} · {c}" for h, c in refs})
        title = R.title(lead)
        summary = R.summary(lead)
        topics = list(dict.fromkeys((["const"] if kind == "amendment" else []) +
                                    [t for t in R.topics(lead, [c for _, c in refs], title) if t != "const"]))
        # The first committee in the bill's own house, and whether the bill got out of it.
        first = next(((h, c, i) for i, s in enumerate(steps) for h, c in [(s["house"], s["comm"])]
                      if s["kind"] == "refer" and h == origin), None)
        if first:
            after = steps[first[2] + 1:]
            left = any(s["kind"] in ("report", "pass") for s in after) or stage >= 2
            fate = ("passed" if left else "defeated" if any(s["kind"] == "commfail" for s in after)
                    else "held" if any(s["kind"] == "held" for s in after) else "none")
        else:
            left, fate = stage >= 2, "passed" if stage >= 2 else "none"
        vers = []
        for n in order:
            b = by_num[n]
            sp = sorted(b.get("sponsors") or [], key=lambda s: (int(s.get("sponsor_order") or 99)))
            primes = [s for s in sp if int(s.get("sponsor_type_id") or 0) in (0, 1)]
            cos = [s for s in sp if s not in primes]
            names = [text(s.get("name")) for s in primes + cos]
            names = list(dict.fromkeys(x for x in names if x))
            for s in sp:
                if s.get("party") in ("D", "R"):
                    parties[(person_house(s, n[0]), text(s.get("name")))] = s["party"]
            a = alone[n]
            vs = a["stage"]
            if any(s["kind"] == "replaced" for s in vers_steps[n]) and vs < 3:
                desc = f"Replaced by {' / '.join(x for x in order if x != n)}"
            elif vs == 0:
                desc = f"In {HOUSE[a['now']]} committee"
            elif vs == 1:
                desc = f"On the {HOUSE[a['now']]} floor"
            else:
                desc = {2: f"Passed the {HOUSE[n[0]] if n[0] in a['passed'] else HOUSE['S' if n[0] == 'H' else 'H']}",
                        3: "Passed both houses", 4: "On the governor's desk", 5: "Became law", 6: "Vetoed"}[vs]
            vers.append({"p": n, "sponsor": names[0] if names else "—",
                         "district": district_of(primes[0]) if primes else 0,
                         "cosponsors": names[1:], "primes": max(1, len(primes)), "cosp": max(0, len(names) - 1),
                         "statusDesc": desc,
                         "committee": a["comm"] if a["place"] == "committee" and vs in (0, 2) else None,
                         "actions": [[s["date"], s["text"]] for s in vers_steps[n]],
                         "link": R.link(b)})
        what = R.what(lead)
        if what:
            texts[lead_n] = {"statement": what[0], "label": what[1]}

        def dates(test, mode="last"):
            ds = sorted({s["date"] for s in steps if test(s) and s["date"]})
            return {"first": ds[0], "last": ds[-1], "all": ";".join(ds)}[mode] if ds else ""

        action_dates = [s["date"] for s in steps if s["date"]]
        ch = w["chapter"]
        rec = {
            "nums": order, "base": order, "prev": set(),
            "title": title, "summary": summary, "act": "", "lawCode": "", "law": None, "laws": [],
            "comms": comm_list, "topics": topics, "places": [], "narrow": R.narrow(lead, title),
            "commFate": fate, "mainTopic": topics[0] if topics else "", "local": "local" in topics,
            "senDeleg": False, "asmDeleg": False, "budget": bool(re.search(r"\bgeneral appropriations\b|\bbudget\b", title, re.I)),
            "shell": False,
            "passedS": "S" in passed, "passedA": R.lower in passed, "program": None,
            "stage": stage,
            "passedIn": HOUSE[max(passed, key=lambda h: dates(lambda s: s["kind"] == "pass" and s["house"] == h) or "")] if stage == 2 and passed else None,
            "chapter": int(ch["num"]) if ch and stage == 5 and str(ch.get("num", "")).isdigit() else None,
            "veto": None, "memo": "", "vetoMemo": None,
            "simText": f"{title} {summary} {what[0][:600] if what else ''}",
            "comm": w["comm"] if stage == 0 and w["place"] == "committee" else None,
            "first": min(action_dates, default=f"{session}-01-01"),
            "last": max(action_dates, default=f"{session}-01-01"),
            "cosp": max(v["cosp"] for v in vers),
            "keyDates": [
                # Approved and sent toward the floor: placed on a floor calendar, or a committee report that doesn't send
                # it on to another committee (a gate like Tennessee's Calendar Committee counts as the floor's).
                min(filter(None, [dates(lambda s: s["kind"] == "floor", "first")] +
                           [s["date"] for i, s in enumerate(steps) if s["kind"] == "report" and not any(
                               t["kind"] == "refer" and t["date"] == s["date"] and t["house"] == s["house"] and t["comm"] not in R.gates
                               for t in steps[i + 1:i + 3])]), default=""),
                dates(lambda s: s["kind"] == "pass" and s["house"] == "S", "all"),
                dates(lambda s: s["kind"] == "pass" and s["house"] == R.lower, "all"),
                "",
                dates(lambda s: s["kind"] == "sent") if stage >= 4 and kind == "bill" else "",
                dates(lambda s: s["kind"] in ("signed", "nosign")) or (dates(lambda s: s["kind"] == "chapter") if stage == 5 else ""),
                dates(lambda s: s["kind"] == "veto"),
            ],
            "votes": S.votes(bs, steps),
            "firstComms": [(first[0], first[1], left)] if first else [],
            "vers": vers,
            "_key": R.earlier_key(lead, kind), "_kind": kind,
        }
        if kind == "amendment":
            rec["keyDates"][4] = rec["keyDates"][5] = rec["keyDates"][6] = ""
        for n in group:
            index[n] = len(recs)
        recs.append(rec)
    R.checks[session] = dict(check)
    os.makedirs(R.data_dir, exist_ok=True)
    json.dump(texts, open(os.path.join(R.data_dir, f"texts_{session}.json"), "w"), ensure_ascii=False)
    return recs, index, fetched(S.folder)


def link_earlier(R, session, recs, older):
    """Fill each record's "prev" from the sessions before (older: {session: records}): the same key (Rules.earlier_key)
    with the same prime sponsor, or a key only one record has in each session. Laws aren't linked as earlier tries
    (yearly bills share titles)."""
    def table(rs):
        out = defaultdict(list)
        for r in rs:
            if r.get("_key"):
                out[r["_key"]].append(r)
        return out
    mine = table(recs)
    for s, rs in older.items():
        theirs = table([r for r in rs if r["stage"] != 5])
        for k, here in mine.items():
            there = theirs.get(k)
            if not there:
                continue
            for r in here:
                who = {v["sponsor"] for v in r["vers"]}
                same = [o for o in there if who & {v["sponsor"] for v in o["vers"]}]
                top = max(o["stage"] for o in there)
                furthest = [o for o in there if o["stage"] == top]
                if same:
                    r["prev"].add((s, same[0]["nums"][0]))
                elif len(here) == 1 and (len(there) == 1 or (top >= 2 and len(furthest) == 1)):
                    r["prev"].add((s, furthest[0]["nums"][0]))  # (two tries at an amendment: the one that passed)
        # Reworded since: a record by the same prime sponsor whose key shares at least 60% of its words.
        by_sponsor = defaultdict(list)
        for o in rs:
            if o["stage"] != 5 and o.get("_key"):
                for v in o["vers"]:
                    by_sponsor[v["sponsor"]].append(o)
        for r in recs:
            if r["prev"] or not r.get("_key"):
                continue
            mine_w = words(r["_key"])
            best = max(((len(mine_w & words(o["_key"])) / max(1, min(len(mine_w), len(words(o["_key"])))), o["nums"][0])
                        for v in r["vers"] for o in by_sponsor.get(v["sponsor"], []) +
                        # (an amendment tried again by other sponsors: any amendment of that session)
                        ([o for o in rs if o.get("_kind") == "amendment" and o.get("_key")] if r.get("_kind") == "amendment" else [])),
                       default=(0, None))
            if best[0] >= 0.6 and len(mine_w) >= 6:
                r["prev"].add((s, best[1]))


STOP = set("a an and the of to in for on or by with as from that this is be are its any which who under certain "
           "amends tca title chapter section part sections resolution propose proposes proposing amendment article "
           "constitution tennessee relative".split())


def words(t):
    return {w for w in re.findall(r"[a-z]{3,}", (t or "").lower()) if w not in STOP}
