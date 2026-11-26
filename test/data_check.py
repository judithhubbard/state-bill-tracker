#!/usr/bin/env python3
"""Runs the "Data traps found so far" list in CLAUDE.md against every state's data, so each check is made every time,
not only the newest ones. Each trap that can be checked by a program is a check here; the rest print what a person
should look at. Add a check here whenever a new trap goes on the list.

FAIL: a trap is present (exit status 1). LOOK: numbers or examples to read over (official totals, odd wording).
Usage: python3 test/data_check.py [state ...]   (default: every state with data; New York's own data isn't checked)
"""
import collections, glob, importlib, json, os, re, sys
from datetime import date, timedelta

HERE = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, HERE)
STATES = [s for s in ("ak", "al", "ar", "az", "ca", "co", "ct", "dc", "de", "ga", "hi", "ia", "id", "il", "in", "ks", "ky", "la", "ma", "md", "me", "mi", "mn", "mo", "ms", "mt", "nc", "nd", "ne", "nh", "nj", "nm", "nv", "oh", "ok", "or", "pa", "ri", "sc", "sd", "tn", "tx", "ut", "va", "vt", "wa", "wi", "wv", "wy", "us") if os.path.isdir(os.path.join(HERE, "data", s))
          and not os.path.exists(os.path.join(HERE, "data", s, "incomplete"))] + \
    (["ny"] if glob.glob(os.path.join(HERE, "data", "bills_*.json*")) else [])  # New York's data is in data/ itself
fails = []
# Contact fields a state's allowed sources don't have (see its NOTES.md): New Hampshire's member list leaves 142
# representatives without a phone; Florida's members' phones come from their pages, read over several runs. (Illinois's
# emails come from Open States, Ohio's phones from its members' pages and Hawaii's from the Public Access Room's
# directory, all since 2026-11-22.)
CONTACT_GAPS = {"nh": ("phone",), "fl": ("phone",)}
# Each legislature's seats (states/legislatures.json), to check votes against the size of their house.
LEGISLATURES = json.load(open(os.path.join(HERE, "states", "legislatures.json")))["states"]
# The topics every state uses, with the same names, so states can be compared ("Shared conventions" in CLAUDE.md).
TOPICS = {"ag": "Agriculture and natural resources", "biz": "Business and consumers", "const": "Constitutional amendments",
          "edu": "Education", "env": "Environment and energy", "gov": "Elections and government",
          "health": "Health", "housing": "Housing", "human": "Social services",
          "labor": "Jobs and workers", "local": "Local government", "safety": "Public safety and courts",
          "tax": "Taxes", "transp": "Transportation"}
# Whether a vote carried: its result where the converter gives one (vote[7], "P"/"F", "RP"/"RF" for a motion to
# reconsider: a California committee's 8-0 with 11 not voting failed), else more ayes than noes (tracker.html's voteCarried()).
carried = lambda v: v[7].endswith("P") if len(v) > 7 and v[7] else v[4] > v[5]


def say(state, kind, msg):
    print(f"  {kind:4} {msg}")
    if kind == "FAIL":
        fails.append(f"{state}: {msg}")


def wording(state, loaded):
    """The page's own wording of each bill's history (the reset, floor and law lines, committee votes) against the record:
    test/wording_check.js runs tracker.html's code on each session's bills as the page sees them."""
    import subprocess
    from stages import has_signature, unsigned
    profile = open(os.path.join(HERE, "states", state, "profile.js"), encoding="utf-8").read()
    day = lambda d: str(d or "")[:10]
    for s, recs in loaded.items():
        bills = []
        for r in recs:
            kd = [r.get("first")] + list(r.get("keyDates") or [])
            # (As tracker.html's decode() reads them: intro, floor, passS, passA, died, deliv, signed, vetoed.)
            k = lambda i: [x for x in (kd[i] or "").split(";") if x] if i < len(kd) and kd[i] else []
            last = lambda i: day(k(i)[-1]) if k(i) else None
            bills.append({"n": r["nums"], "stage": r["stage"],
                          "dates": {"floor": last(1), "died": last(4), "passSAll": [day(x) for x in k(2)], "passAAll": [day(x) for x in k(3)],
                                    "deliv": last(5), "signed": last(6), "vetoed": last(7)},
                          "vers": [{"p": v["p"], "actions": [[day(a[0]), a[1]] for a in v["actions"]]} for v in r["vers"]],
                          "votes": [[v[0], v[1], v[2], day(v[3]), v[4], v[5], v[7] if len(v) > 7 else ""] for v in r.get("votes") or []],
                          # (stages.py's reading of a law's history, for the governor's page's past sessions: compared there)
                          **({"sig": [has_signature(r), unsigned(r)]} if r["stage"] == 5 else {})})
        run = subprocess.run(["node", os.path.join(HERE, "test", "wording_check.js")], capture_output=True, text=True,
                             input=json.dumps({"profile": profile, "session": s, "current": s == max(loaded), "bills": bills}))
        if run.returncode:
            say(state, "FAIL", f"{s}: test/wording_check.js failed: {run.stderr.strip()[-400:]}")
            continue
        out = json.loads(run.stdout)
        for m in out["fails"]:
            say(state, "FAIL", f"wording: {m}")
        for m in out["looks"]:
            say(state, "LOOK", f"wording: {m}")


def check(state):
    P = importlib.import_module(f"states.{state}.profile")
    C = importlib.import_module(f"states.{state}.convert")
    print(f"== {P.STATE_NAME}")
    loaded = {s: C.load_session(s)[0] for s in importlib.import_module("states.window").shown(P.DATA, C.sessions())}
    if not loaded:  # (no session's data at all: the District's folder before its first LegiScan download crashed here)
        say(state, "FAIL", "no session's data to check (download missing?)")
        return
    wording(state, loaded)
    # A converter's own checks of its sources (Arizona: apps.azleg.gov's codes, and its stages beside Open States').
    for level, msg in (getattr(C, "source_checks", None) or (lambda _: []))(loaded):
        say(state, level, msg)
    # Committee reports' signatures (AK, WA, ME: votes of kind "R") aren't votes: the vote checks below never see them.
    # Each signer is a seat ("H:12|Carrick"), a member with no seat now ("S|Hughes"), or no member of the committee's
    # house ("H?Name"), which is the name read wrongly (or a list split wrongly).
    for s, recs in loaded.items():
        for r in recs:
            r["reports"] = [v for v in r["votes"] if v[1] == "R"]
            r["votes"] = [v for v in r["votes"] if v[1] != "R"]
        reps = [(r["nums"][0], v) for r in recs for v in r["reports"]]
        if reps:
            loose = [(n, m) for n, v in reps for m, _ in v[6] if "?" in m]
            bad = sorted({n for n, v in reps if not v[2] or not v[3] or not v[6]})
            say(state, "FAIL" if len(loose) > 0.01 * sum(len(v[6]) for _, v in reps) else "LOOK",
                f"{s}: {len(reps)} committee reports with {sum(len(v[6]) for _, v in reps)} signatures; {len(loose)} signers "
                f"not matched to a member of the house{f', e.g. {collections.Counter(m for _, m in loose).most_common(4)}' if loose else ''}")
            if bad:
                say(state, "FAIL", f"{s}: {len(bad)} committee reports with no committee, day or signers, e.g. {bad[:4]}")
            # A signer named twice on one report (a list read twice, two members matched to one seat), and reports dated a
            # day the bill's history has no line on (ME's bill pages show only the latest report's division: LD 1343 of
            # 2025-26 was divided in May 2025 and again in February 2026, so a page's signers belong to its latest report).
            twice = sorted({n for n, v in reps if len({m for m, _ in v[6]}) < len(v[6])})
            if twice:
                say(state, "FAIL" if len(twice) > 0.005 * len(reps) else "LOOK",
                    f"{s}: {len(twice)} committee reports naming a signer twice, e.g. {twice[:4]}")
            days = {r["nums"][0]: {a[0] for x in r["vers"] for a in x["actions"]} for r in recs if r["reports"]}
            off = sorted({n for n, v in reps if str(v[3])[:10] not in days.get(n, set())})
            if off:
                say(state, "LOOK", f"{s}: {len(off)} committee reports on a day with no history line, e.g. {off[:4]}")

    # The shared topics, with the shared names.
    mine = {k: v[0] for k, v in P.TOPICS.items()}
    # (Congress adds topics no state needs, and names "gov" for itself: P.EXTRA_TOPICS, P.TOPIC_NAMES.)
    shared = {**TOPICS, **getattr(P, "TOPIC_NAMES", {})}
    off = {k: mine.get(k) for k in shared if mine.get(k) != shared[k]} | {k: v for k, v in mine.items() if k not in shared and k not in getattr(P, "EXTRA_TOPICS", ())}
    if off:
        say(state, "FAIL", f"topics differ from the shared list: {off}")

    for s, recs in loaded.items():
        # (Constitutional amendments stop at "passed both houses": they go to the voters, not the governor.)
        stages = collections.Counter(r["stage"] for r in recs if not (r["stage"] == 3 and "const" in r["topics"]))
        # Count bills by stage against the Legislature's own totals (signed, vetoed).
        say(state, "LOOK", f"{s}: {len(recs)} bills; signed {stages[5]}, vetoed {stages[6]}, passed both houses but not "
                           f"sent {stages[3]}, on the governor's desk {stages[4]} (compare with the official totals)")
        # Sponsors named only in another document: Idaho's committee bills name the member who asked for them in the
        # Statement of Purpose's "Contact:" section, matched to the year's members. A session where most don't match (a
        # new layout, a member list that didn't load) shows committees again; names titled as legislators that match no
        # member mean the matching slipped.
        if hasattr(C, "contact_stats"):
            cs = C.contact_stats(s)
            if cs["statements"]:
                say(state, "LOOK", f"{s}: {cs['own']} of {cs['statements']} statements name a member of the bill's house as "
                                   f"its contact, {cs['other']} only one of the other house; none named: {cs['none'][:5]}")
                if cs["statements"] >= 50 and cs["own"] < 0.6 * cs["statements"]:
                    say(state, "FAIL", f"{s}: only {cs['own']} of {cs['statements']} statements' contacts matched a member "
                                       f"of the bill's house")
                if cs["missed"]:
                    say(state, "FAIL" if len(cs["missed"]) > max(3, 0.01 * cs["statements"]) else "LOOK",
                        f"{s}: {len(cs['missed'])} contacts titled as legislators match no member, e.g. {cs['missed'][:5]}")
        # A bill that passed both houses passed each one (missing votes, one-house conference reports).
        missing = [r["nums"][0] for r in recs if r["stage"] >= 3 and not (r["passedS"] and r["passedA"])]
        if missing:
            say(state, "FAIL", f"{s}: {len(missing)} bills past both houses without both houses' passage, e.g. {missing[:4]}")
        # Passed both houses while the houses still disagree: MA's "House NON-concurred in the Senate amendment", read as
        # a concurrence, then "Committee of conference appointed" (H5576 of 2025-26, and 12 more). A bill whose last step
        # is a refusal to concur or a conference committee's appointment hasn't passed both houses in one version.
        split = [r["nums"][0] for r in recs if r["stage"] == 3 and "const" not in r["topics"] and r["vers"][0]["actions"]
                 and re.search(r"\bnon-?concur|refuse[sd]? to concur|conference (?:committee )?(?:appointed|requested)|"
                               r"committee of conference appointed|appointed? (?:a )?conference committee",
                               r["vers"][0]["actions"][-1][1], re.I)]
        if split:
            say(state, "FAIL" if len(split) > 0.002 * len(recs) else "LOOK",
                f"{s}: {len(split)} bills shown as passed both houses whose last step is a refusal to concur or a conference "
                f"committee, e.g. {split[:4]}")
        # A passage that never took effect: a bill shown as passed by one house that then died in that same house (MS's
        # HB 1602 of 2026: passed, held there by a motion to reconsider entered and never decided, "Died On Calendar").
        lower = getattr(P, "LOWER_NAME", "Assembly")
        undone = [r["nums"][0] for r in recs if r["stage"] == 2 and r["passedS"] != r["passedA"] and r["vers"][0]["actions"]
                  and re.search(rf"\bdied (?:in|on) (?:the )?{'Senate' if r['passedS'] else lower} (?:committee|calendar)", r["vers"][0]["actions"][-1][1], re.I)]
        # (Not "Died in House at Sine Die adjournment", AR's line for a bill back in its own house when the session ends.)
        if undone:
            say(state, "FAIL" if len(undone) > 0.005 * len(recs) else "LOOK",
                f"{s}: {len(undone)} bills passed by one house that then died in that house (a passage undone?), e.g. {undone[:4]}")
        # A record whose kind disagrees with its title: SC's bill search lists S 729 of 2025-26 ("A CONCURRENT RESOLUTION TO
        # REQUEST ...") as a General Bill. Resolutions are left out (other than constitutional amendments): decide by the title.
        resol = [r["nums"][0] for r in recs if "const" not in r["topics"] and
                 re.match(r"^\W*(?:an? )?(?:senate |house |assembly )?(?:concurrent )?resolution\b", r["summary"] or "", re.I)]
        if resol:
            say(state, "FAIL" if len(resol) > 0.005 * len(recs) else "LOOK", f"{s}: {len(resol)} records whose title says they're resolutions, e.g. {resol[:4]}")
        # The 4th key date is a passage undone between a two-year session's years (New York's January return to committee,
        # Washington's end-of-first-session return): only states whose page explains it (STATE.resetNote) fill it in.
        if any(r["keyDates"][3] for r in recs) and "resetNote(" not in open(os.path.join(HERE, "states", state, "profile.js")).read():
            say(state, "FAIL", f"{s}: the 4th key date (a passage undone between years) is filled in, with no resetNote to explain it")
        # Committee names carrying a motion's tail: a failed motion to refer read as a referral (IN's "Referred to
        # Committee on Ways and Means pursuant to House Rule 84; Failed, Roll Call 185: yeas 28, nays 59").
        tails = sorted({c for r in recs for c in r["comms"] if re.search(r"\b(?:failed|roll call|yeas|nays|pursuant to)\b|;", c, re.I)})
        if tails:
            say(state, "FAIL", f"{s}: {len(tails)} committee names carry a motion's wording, e.g. {tails[:3]}")
        # A summary line that is the title again with a stock tail: Iowa's was the official title, whose only difference
        # from the title is ", and including effective date provisions" (2026-11-22).
        norm_t = lambda t: re.sub(r"[^a-z0-9 ]", "", (t or "").lower()).split()
        # (Only a stock tail: many states' summary line is the full title, which starts with the short one.)
        stock = re.compile(r"^(?:and )?(?:including|providing|making|with) (?:an )?(?:effective dates?|applicability|retroactive|"
                           r"penalties|transition)[a-z ]*(?:provisions?|applicable)?$")
        echo = [r["nums"][0] for r in recs if r["summary"] and (st := norm_t(r["title"])) and len(st) >= 3
                and (sm := norm_t(r["summary"]))[:len(st)] == st and len(sm) > len(st) and stock.match(" ".join(sm[len(st):]))]
        if echo:
            say(state, "FAIL" if len(echo) > 0.05 * len(recs) else "LOOK",
                f"{s}: {len(echo)} summary lines are the title with a stock tail, e.g. {echo[:4]}")
        # (The same words as the title: the rows leave it out, an opened bill shows it. NE, WV and others: only a LOOK.)
        same = [r["nums"][0] for r in recs if r["summary"] and norm_t(r["summary"]) == norm_t(r["title"])]
        if same:
            say(state, "LOOK", f"{s}: {len(same)} summary lines repeat the title word for word, e.g. {same[:4]}")
        # A doubled word in history lines: Congress.gov's "Referred to the The Subcommittee on ..." (states/us/convert.py
        # drops it; billfacts.js's plainAction() made its own "the The Committee On ..." of written-out referrals, fixed
        # 2026-11-22).
        doubled = [r["nums"][0] for r in recs for v in r["vers"] for _, t in v["actions"] if re.search(r"\bthe the\b", t, re.I)]
        if doubled:
            say(state, "FAIL" if len(doubled) > 0.001 * len(recs) else "LOOK",
                f"{s}: {len(doubled)} history lines with \"the the\", e.g. {doubled[:4]}")
        # Committee pass rates that look wrong (sponsors' amendments read as committee votes).
        fate = collections.Counter(r["commFate"] for r in recs)
        say(state, "LOOK", f"{s}: first committee: {fate['passed']} approved, {fate['held']} held, {fate['defeated']} voted down, "
                           f"{fate['none']} no action ({100 * fate['passed'] // max(1, len(recs))}% approved)")
        # Floor-vote wording not read as a passage.
        odd = collections.Counter()
        for r in recs:
            for _, t in r["vers"][0]["actions"]:
                if re.search(r"\bpassed\b|rescind|reconsider", t, re.I) and not t.startswith("PASSED") and \
                        not re.search(r"passed (to (engrossment|third|3rd|second|2nd)|by indefinitely|over)|Passed by|"
                                      r"to engrossment|Bill text as passed|Reported|Committee|Passed Both Houses|Motion (Filed )?to Reconsider", t, re.I):
                    odd[re.sub(r"\(.*", "", re.sub(r"\d+", "#", t))[:70]] += 1
        if odd:
            say(state, "LOOK", f"{s}: history lines mentioning passage not read as one: " +
                "; ".join(f"{n}× {k}" for k, n in odd.most_common(4)))
        # A line read by its opening words when it ends in another step: WA's "Rules Committee relieved of further
        # consideration.  On motion, referred to Ways & Means." was read as placed on the floor (SB 5659 of 2025-26).
        # A bill shown on the floor whose last line sends it to a committee (not Rules, Assignments or a calendar).
        refloor = []
        for r in recs:
            acts = sorted(r["vers"][0]["actions"], key=lambda a: a[0] or "") if r["stage"] == 1 else []
            if acts and re.search(r"\b(?:re-?)?referred to (?!(?:the )?(?:\w+ )?(?:Rules|Assignments|Calendar|third|3rd|second|2nd|"
                                  r"engross|enroll|floor|Senate\b|House\b|Assembly\b|Governor))", acts[-1][1], re.I):
                refloor.append(r["nums"][0])
        if refloor:
            say(state, "FAIL" if len(refloor) > 0.005 * len(recs) else "LOOK",
                f"{s}: {len(refloor)} bills shown on the floor whose last line refers them to a committee, e.g. {refloor[:4]}")
        # Histories out of order: some lines with a time and some with only a date (MA's S2913: sorting by the full
        # time put "Read second" after "Laid before the Governor"). Sort by day and keep the file's order within a day.
        unsorted = [r["nums"][0] for r in recs for v in r["vers"] if any(a[0] > b[0] for a, b in zip(v["actions"], v["actions"][1:]) if a[0] and b[0])]
        # (A few are the source's own order: New York's Senate lines after a substitution.)
        if unsorted:
            say(state, "FAIL" if len(unsorted) > 0.01 * len(recs) else "LOOK",
                f"{s}: {len(unsorted)} bills with history lines out of date order, e.g. {unsorted[:4]}")
        # A last action's day with no history line on it: the status rows (/your-bills/, /list/, the front page) then show a
        # date and no wording (IA and HI dated a bill by paperwork the history leaves out, "Subcommittee: ...": HF 29 of 2025).
        blank = [r["nums"][0] for r in recs if r["last"] and any(v["actions"] for v in r["vers"])
                 and not any(a[0] == r["last"] for v in r["vers"] for a in v["actions"])]
        if blank:
            say(state, "FAIL" if len(blank) > 0.01 * len(recs) else "LOOK",
                f"{s}: {len(blank)} bills whose last action's day has no history line, e.g. {blank[:4]}")
        # The governor's action twice, days apart: DE's bill histories copy a substitute's lines under the day they were
        # copied (HS 2 for HB 168 of 2023-24: signed 9/30/24, copied 10/2/24); read the substitute's own history.
        GOV_ACT = re.compile(r"^(?:(?:Signed|Approved|Vetoed) by (?:the )?[Gg]overnor\b|VETOED$)")
        twice = [r["nums"][0] for r in recs for v in r["vers"][:1]
                 if any(len({d for d, t in v["actions"] if t == x}) > 1 for x in {t for _, t in v["actions"] if GOV_ACT.match(t)})]
        if twice:
            say(state, "FAIL" if len(twice) > 0.01 * len(recs) else "LOOK",
                f"{s}: {len(twice)} bills with the governor's action on two different days, e.g. {twice[:4]}")
        # Law numbers on bills that aren't laws: ND's Session Laws give vetoed measures chapter numbers too (HB 1273 of 2023,
        # "Measure Vetoed", chapter 586); a chapter number alone doesn't make a law.
        numbered = [r["nums"][0] for r in recs if r.get("chapter") and r["stage"] != 5]
        if numbered:
            say(state, "FAIL", f"{s}: {len(numbered)} bills that aren't laws carry a law number, e.g. {numbered[:4]}")
        # A veto read as overridden: KY's SB 70 of 2026 was vetoed after the session and "delivered to Secretary of State"
        # with no chapter, a line laws over a veto also carry. A law with a veto date should show the override.
        ovr = re.compile(r"overrid|over (?:the )?(?:governor'?s? )?veto|notwithstanding|not sustained", re.I)
        unover = [r["nums"][0] for r in recs if r["stage"] == 5 and r["keyDates"][6] and not any(ovr.search(t) for v in r["vers"] for _, t in v["actions"])]
        if unover:
            say(state, "LOOK", f"{s}: {len(unover)} laws vetoed with no override in their history (a veto read as overridden?), e.g. {unover[:4]}")
        # The governor's action with no date of its own: MD's bill list has none, and its laws and vetoes were shown on the
        # bill's last legislative day (SB 448 of 2026: April 9; vetoed May 22); the dates are on each bill's page.
        # Laws and vetoes should each carry the day of the governor's action (or of the override).
        undated = [r["nums"][0] for r in recs if (r["stage"] == 5 and not r["keyDates"][5]) or (r["stage"] == 6 and not r["keyDates"][6])]
        if undated:
            say(state, "LOOK", f"{s}: {len(undated)} of {sum(r['stage'] in (5, 6) for r in recs)} laws and vetoes with no date "
                               f"for the governor's action, e.g. {undated[:4]}")
        # A veto message that never arrived: New York's memos come from the Senate API's vetoMessages, often days after
        # the veto (S1239 of 2025, vetoed 2026-11-20 as "VETOED MEMO.19", had none that day), and a run that kept the
        # last copy (fetch_bills.py --if-changed) would keep showing none. In a state whose vetoes carry messages, the
        # vetoes of the last year more than 14 days old without one. (A state's own gaps, vetoes the files give no
        # message for, show here too; this is to read over, not a failure. Pocket vetoes are left out: New York's say
        # "no veto message issued", as A8883 of 2025's.)
        if any(r.get("vetoMemo") for rs in loaded.values() for r in rs):
            today = date.today()
            late = [r["nums"][0] for r in recs if r["stage"] == 6 and r["keyDates"][6]
                    and today - timedelta(days=365) <= date.fromisoformat(r["keyDates"][6][:10]) <= today - timedelta(days=14)
                    and not (r.get("vetoMemo") or {}).get("text")
                    and not any(re.search(r"pocket veto", t, re.I) for v in r["vers"] for _, t in v["actions"])]
            if late:
                say(state, "LOOK", f"{s}: {len(late)} bills vetoed 2 weeks to a year ago with no veto message, e.g. {late[:4]}")
        # A veto message filed under the wrong bill (2026-11-22, when messages came from shared documents: GA's yearly
        # PDF of every veto, SD's journals with several letters, OK's yearly page): one whose veto statement ("I am
        # returning House Bill 895", "I have VETOED House Bill 1138", "I VETO HOUSE BILL 308", "I respectfully return to
        # you House Bill 1132") names a bill, never the record's own. (Other bills named in passing, "my veto of House
        # Bill 3006", "SB 28 (2021)", don't count: most messages say "this bill".) FAIL over 2% of a session's, else LOOK.
        def named(t):
            out = set()
            for m in re.finditer(r"(?i:returning|return to you|am vetoing|have vetoed|I (?:hereby )?veto)\s+(?:herewith\s+)?"
                                 r"(?:(House|Senate|Assembly)\s+(Bill|Joint Resolution|File)\s+(?:No\.\s*)?0*(\d+)|"
                                 r"([HSA])\.?\s?([BF]|J\.?R)\.?\s?0*(\d+)\b)", t, re.I):
                if m.group(1):
                    out.add((m.group(1)[0].upper(), m.group(3)))
                else:
                    out.add((m.group(4), m.group(6)))
            return out
        msgs = [r for r in recs if (r.get("vetoMemo") or {}).get("text")]
        wrong = []
        for r in msgs:
            got = named(r["vetoMemo"]["text"])
            own = {(re.match(r"[A-Z]", n).group(0), str(int(re.search(r"\d+", n).group(0))))
                   for n in r["nums"] if re.search(r"\d", n)}
            # (One letter for several bills, "I have decided to veto SENATE BILL 315 ... as well as SENATE BILL 327", NM
            # 2025: fine when the record's own bill is named anywhere.)
            anywhere = {(m.group(1)[0].upper(), m.group(3)) for m in re.finditer(
                r"\b(House|Senate|Assembly)\s+(Bill|Joint Resolution|File)\s+(?:No\.\s*)?0*(\d+)", r["vetoMemo"]["text"], re.I)}
            # (Or abbreviated: NH's one letter for two bills, "I have vetoed HB 1491 and SB 661", 2026.)
            anywhere |= {(m.group(1).upper(), m.group(2)) for m in re.finditer(
                r"\b([HSA])\.?\s?B\.?\s?0*(\d+)\b", r["vetoMemo"]["text"])}
            if got and not got & own and not anywhere & own:
                wrong.append(r["nums"][0])
        if wrong:
            say(state, "FAIL" if len(wrong) > 0.02 * len(msgs) else "LOOK",
                f"{s}: {len(wrong)} of {len(msgs)} veto messages name other bills but never their own (filed under the "
                f"wrong bill?), e.g. {wrong[:4]}")
        # A veto that stood, whose last action reads as an override: NH's SB 434 of 2026, overridden by the Senate and
        # sustained by the House, showed "VETO OVERRIDDEN" (one house's override sorted after the other's sustaining vote).
        def last_line(r):
            acts = [a for v in r["vers"] for a in v["actions"] if a[0] == r["last"]]
            return acts[-1][1] if acts else ""
        # (Only where the history has a sustaining vote: a veto one house overrode and the other never took up stands too.)
        sustained = lambda r: any(re.search(r"\bveto sustained|sustain(?:ed|s)? the (?:governor'?s? )?veto", t, re.I) for v in r["vers"] for _, t in v["actions"])
        stood = [r["nums"][0] for r in recs if r["stage"] == 6 and re.search(r"overrid", last_line(r), re.I)
                 and not re.search(r"sustain|fail|lost|\bnot\b|n't|\bno\b|requires|message", last_line(r), re.I) and sustained(r)]
        if stood:
            say(state, "FAIL", f"{s}: {len(stood)} vetoed bills whose last action reads as an override, e.g. {stood[:4]}")
        # A law whose history ends with the governor holding it: LegiScan's "Passed" status on ten of Maine's 2023-24 bills
        # the governor held until the Legislature ended (LD 1152: "Held by Governor", then "Died Upon Conclusion of the
        # 131st"), a pocket veto. A held law should show a signature, a chapter or an override after the hold.
        held = re.compile(r"held by (?:the )?governor", re.I)
        after = re.compile(r"sign|became law|chapter|overrid|notwithstanding|\bact\b|public law|session law", re.I)
        heldlaw = [r["nums"][0] for r in recs if r["stage"] == 5 and any(
            any(held.search(t) for _, t in v["actions"]) and not any(after.search(t) for _, t in v["actions"][max(i for i, (_, t) in enumerate(v["actions"]) if held.search(t)) + 1:])
            for v in r["vers"])]
        if heldlaw:
            say(state, "LOOK", f"{s}: {len(heldlaw)} laws whose history ends with the governor holding them (a pocket veto?), e.g. {heldlaw[:4]}")
        # Law numbers given twice (NH's history lines: SB 62 and HB 511 of 2025 both "Chapter 39"; the LSRs file's column is
        # right). In one-year sessions a chapter, act or public law number belongs to one bill.
        if getattr(P, "YEARS", 2) == 1:
            twice = [k for k, n in collections.Counter(r["chapter"] for r in recs if r.get("chapter")).items() if n > 1]
            if twice:
                say(state, "LOOK", f"{s}: {len(twice)} law numbers given to two bills, e.g. {twice[:4]}")
        # Dates with a typo in the year (NH's HB 425 of 2025: "03/06/2035"; HB 49 of 2023: "04/13/2022"): far outside the
        # session. (Carried-over bills reach back a year or two; laws are signed and vetoes taken up a year after.)
        years = getattr(P, "YEARS", 2)
        stray = [r["nums"][0] for r in recs for v in r["vers"] for d, _ in v["actions"]
                 if d and re.match(r"\d{4}", str(d)) and not s - 3 <= int(str(d)[:4]) <= s + years + 1]
        if stray:
            say(state, "FAIL" if len(set(stray)) > 0.005 * len(recs) else "LOOK",
                f"{s}: {len(stray)} history lines dated years from the session, e.g. {sorted(set(stray))[:4]}")
        # Dates in the future: an effective date read as the event's (NH "Chapter 340;eff. 01/01/2027", GA's "Effective
        # Date" lines), a typo in a year (VT H.790 of 2025-26 "February 27, 2027", WV SB 239 of 2023 "2/20/2202"), a
        # source's own future date (MA's session laws). A day's grace for time zones.
        tomorrow = (date.today() + timedelta(days=1)).isoformat()
        future = sorted({r["nums"][0] for r in recs if any(str(d)[:10] > tomorrow for d in
                         [r.get("last") or ""] + list(r["keyDates"]) + [d for v in r["vers"] for d, _ in v["actions"] if d])})
        if future:
            say(state, "FAIL", f"{s}: {len(future)} bills with a history line, key date or last action in the future, e.g. {future[:4]}")
        # A year or more after the session's end: a typo or an effective date that's still in the past.
        late_by = f"{s + years}-12-31"
        late = sorted({r["nums"][0] for r in recs for v in r["vers"] for d, _ in v["actions"] if d and tomorrow >= str(d)[:10] > late_by})
        if late:
            say(state, "LOOK", f"{s}: {len(late)} bills with history lines more than a year after the session ended, e.g. {late[:4]}")
        # Titles: blank (NJ's number-only placeholders, NH's HB 8002-8012 of 2024), or with HTML entities left in
        # (PA's "&#8211;"), or with a "?" for a lost apostrophe or okina (HI's "Authority?s", "Hawai?i").
        # (A number with no title and no dates is a placeholder build_data.py leaves out: IL SB 4214 of 2025; one with dates
        # gets a stand-in title there: OH SB 342 of 2023, LOOK.)
        blank = [r["nums"][0] for r in recs if not (r.get("title") or "").strip() and (r.get("first") or r.get("stage"))]
        if blank:
            say(state, "FAIL" if len(blank) > 3 else "LOOK", f"{s}: {len(blank)} bills with no title, e.g. {blank[:4]}")
        ents = [r["nums"][0] for r in recs if re.search(r"&(?:#\d+|#x[0-9a-f]+|amp|lt|gt|quot|apos|nbsp|ndash|mdash|lsquo|rsquo|ldquo|rdquo|hellip|sect|reg|copy|trade);", (r.get("title") or "") + " " + (r.get("summary") or ""), re.I)]
        if ents:
            say(state, "FAIL", f"{s}: {len(ents)} titles or summaries with HTML entities (&#8211;), e.g. {ents[:4]}")
        qmark = [r["nums"][0] for r in recs if re.search(r"[a-z]\?[a-z]", r.get("title") or "", re.I)]
        if qmark:
            say(state, "LOOK", f"{s}: {len(qmark)} titles with a '?' between letters (a lost apostrophe?), e.g. {qmark[:4]}")
        # A record left over from an earlier session: MO's House exports file the previous year's budget bills under each
        # new year with nothing but the governor's spending restrictions, dated before the session ("Message Received from
        # the Governor, pursuant to Article IV, Section 27", 12/27/2023 in 2024's folder). In a finished session, a bill
        # whose whole history comes before the session's first year is a stray (or a prefiled bill never introduced).
        import datetime as _dt
        if s + years - 1 < _dt.date.today().year:
            before = [r["nums"][0] for r in recs if all(str(d)[:4].isdigit() and int(str(d)[:4]) < s for v in r["vers"] for d, _ in v["actions"] if d)
                      and any(d for v in r["vers"] for d, _ in v["actions"])]
            if before:
                say(state, "LOOK", f"{s}: {len(before)} bills whose whole history comes before the session (left over from an earlier one?), e.g. {before[:4]}")
        after = [r["nums"][0] for r in recs for v in r["vers"] for i, (d, t) in enumerate(v["actions"])
                 if t == "DELIVERED TO GOVERNOR" and any(d2 == d and re.match(r"PASSED|PLACED ON FLOOR|REFERRED", t2) for d2, t2 in v["actions"][i + 1:])]
        if after:
            say(state, "LOOK", f"{s}: {len(after)} bills with a passage or referral after going to the governor the same day, e.g. {after[:4]}")
        # A list carried onto the next history line (AK's "CROSS SPONSOR(S): TOBIN, ..., GRAY-JACKSON," then "KIEHL, ...";
        # its committee reports' "DP: ..." lists too): a line ending in a comma is half of one.
        cont = [r["nums"][0] for r in recs for v in r["vers"] for _, t in v["actions"] if re.search(r",\s*$", t)]
        if cont:
            say(state, "LOOK", f"{s}: {len(cont)} history lines end in a comma (a list carried onto the next line?), e.g. {sorted(set(cont))[:4]}")
        # Vote lists that don't match their tallies.
        bad = sum(1 for r in recs for v in r["votes"] if sum(1 for _, c in v[6] if c == "N") > v[5])
        if bad:
            say(state, "FAIL", f"{s}: {bad} votes list more noes than their tally")
        # Fewer: a name list split wrongly (WY's "Brown, G, Larson, JT" read as four names, then joined too eagerly).
        few = [r["nums"][0] for r in recs for v in r["votes"] if 0 < sum(1 for _, c in v[6] if c == "N") < v[5]]
        if few:
            say(state, "FAIL" if len(few) > 0.01 * sum(len(r["votes"]) for r in recs) else "LOOK",
                f"{s}: {len(few)} votes list fewer noes than their tally, e.g. {few[:4]}")
        # Names that can't add up: a roll call's yes votes are left out of its list, so its ayes plus the members it names
        # (no, absent, excused, abstaining) can't be more than the house's seats; a list that is (a group read twice, a
        # roll call matched to the wrong vote) would count members who weren't there. And a list that names yes votes
        # ("Y") must name as many as the tally (2026-11-22, when MS, KY, MA, MI and MD floor votes were read from PDFs).
        seats_h = LEGISLATURES.get(state, {}).get("seats", {})
        over = [r["nums"][0] for r in recs for v in r["votes"] if v[1] == "F" and v[6] and seats_h.get(v[0])
                and v[4] + sum(1 for _, c in v[6] if c != "Y") > seats_h[v[0]]]
        if over:
            say(state, "FAIL" if len(over) > 0.005 * max(1, sum(len(r["votes"]) for r in recs)) else "LOOK",
                f"{s}: {len(over)} floor votes whose ayes plus the members they name are more than the house's seats, e.g. {over[:4]}")
        ayes = [r["nums"][0] for r in recs for v in r["votes"] if any(c == "Y" for _, c in v[6]) and sum(1 for _, c in v[6] if c == "Y") != v[4]]
        if ayes:
            say(state, "FAIL", f"{s}: {len(ayes)} votes naming yes votes name a different number than their tally, e.g. {ayes[:4]}")
        # A committee vote that says the opposite of the committee's report: MD's voting record on an unfavorable report
        # counts the yeas for the motion to kill the bill (HB 344 of 2026: 17-0, read at first as "Approved by"). A bill
        # its first committee voted down whose votes there all have more ayes than noes, or one it approved whose votes
        # there all have more noes (2026-11-22).
        ckey = lambda n: re.sub(r"[^a-z]", "", (n or "").lower().replace("and", ""))
        upside = []
        for r in recs:
            if not r.get("firstComms") or r["commFate"] not in ("passed", "defeated"):
                continue
            h, cname = r["firstComms"][0][0], r["firstComms"][0][1]
            cv = [v for v in r["votes"] if v[1] == "C" and v[0] == h and ckey(v[2]) == ckey(cname) and v[4] + v[5]]
            # A bill past its committee whose report was against it is no contradiction where every report goes to the
            # floor: ND's HB 1139 of 2025, "recommended it not pass, 8-5", then passed the House 49-38.
            if r["commFate"] == "passed" and any(re.search(r"not pass|unfavorabl", a, re.I) for v in r["vers"] for _, a in v["actions"]):
                continue
            if cv and (all(carried(v) for v in cv) if r["commFate"] == "defeated" else all(not carried(v) and v[5] > v[4] for v in cv)):
                upside.append(r["nums"][0])
        if upside:
            with_c = sum(1 for r in recs if any(v[1] == "C" for v in r["votes"]))
            say(state, "FAIL" if len(upside) > 0.01 * max(1, with_c) else "LOOK",
                f"{s}: {len(upside)} bills whose first committee's votes say the opposite of its report (an unfavorable "
                f"report's yeas read as approval?), e.g. {upside[:4]}")
        # Votes on a day the bill's history has no line for: a roll call matched to the wrong bill or day (KS's override
        # votes filed under HB 2315; a PDF's date read wrongly). Each floor vote should fall on a day of the bill's history.
        fl_all = [(r, v) for r in recs for v in r["votes"] if v[1] == "F" and v[3]]
        nohist = sorted({r["nums"][0] for r, v in fl_all
                         if str(v[3])[:10] not in {str(d)[:10] for x in r["vers"] for d, _ in x["actions"] if d}})
        if nohist:
            # (A FAIL over 5%: a day read wrongly for a whole kind of vote. Under it, on 2026-11-22: AK 2023's seven House
            # votes of 2024-05-16 after histories that end earlier, NY 2021's 57 Assembly votes, a few in CA, CO, MT, NH,
            # TX, WA; not looked into.)
            say(state, "FAIL" if len(nohist) > 0.05 * max(1, len({r["nums"][0] for r, _ in fl_all})) else "LOOK",
                f"{s}: {len(nohist)} bills with a floor vote on a day their history has no line for, e.g. {nohist[:4]}")
        # Two names in one roll call tied to the same seat: a surname that meant different members over the session (NE's
        # "Meyer": Glen Meyer until January 2026, then "Meyer, F." and "Meyer, G." for two members).
        dup = [r["nums"][0] for r in recs for v in r["votes"]
               if (ids := [m for m, _ in v[6] if isinstance(m, str) and "?" not in m]) and len(ids) != len(set(ids))]
        if dup:
            say(state, "FAIL" if len(dup) > 0.005 * sum(len(r["votes"]) for r in recs) else "LOOK",
                f"{s}: {len(dup)} votes name one seat twice (a surname tied to the wrong member?), e.g. {dup[:4]}")
        # Committee votes counting more members than the committee has: NV's ayes are the members the minutes list as
        # present less those named (2026-11-22), so a members list read wrongly, or a motion tied to another committee's
        # minutes, gives a count above the committee's usual one. (Members away and not named only lower it; a committee
        # that grew mid-session raises it legitimately, so this LOOKs.)
        sizes = {}
        for r in recs:
            for v in r["votes"]:
                if v[1] == "C" and v[6]:
                    sizes.setdefault((v[0], v[2]), []).append(v[4] + sum(1 for _, c in v[6] if c != "Y"))
        big_c = []
        for k, ns in sizes.items():
            usual = max(set(ns), key=ns.count)
            big_c += [f"{k[0]} {k[1]}: {n} (usually {usual})" for n in ns if n > usual + 1]
        if big_c:
            say(state, "LOOK", f"{s}: {len(big_c)} committee votes count more members than their committee usually has, e.g. {big_c[:3]}")
        # A committee's vote on a motion against the bill read as a vote for it: ND's committees vote on "Do Not Pass"
        # (Y for the motion is against the bill; states/nd/convert.py's committee_vote() turns it round, 2026-11-22). A
        # committee vote that carried on the day the history says the committee recommended against the bill, and nothing
        # that day says it recommended for it, shows "Approved by the ... Committee". ("Unfavorable" isn't counted: DE's
        # reports list members' signatures, "1 favorable, 6 on its merits, 1 unfavorable", 85 bills.)
        against = re.compile(r"recommended it not pass|\bdo not pass\b|ought not to pass|inexpedient to legislate", re.I)
        favor = re.compile(r"recommended it pass|\bdo pass\b|ought to pass\b|\bfavorabl|reported it without|\bapproved\b|\badvanced\b", re.I)
        flipped = []
        for r in recs:
            days = collections.defaultdict(list)
            for x in r["vers"]:
                for d, t in x["actions"]:
                    days[str(d)[:10]].append(t)
            for v in r["votes"]:
                ts = days.get(str(v[3])[:10], [])
                if v[1] == "C" and carried(v) and any(against.search(t) for t in ts) and \
                        not any(favor.search(t) and not against.search(t) for t in ts):
                    flipped.append(r["nums"][0])
                    break
        if flipped:
            say(state, "LOOK", f"{s}: {len(flipped)} bills with a committee vote that carried on a day the committee "
                               f"recommended against them (a vote on a motion against the bill?), e.g. {flipped[:4]}")
        # Votes put in the wrong house: more ayes and noes than the house has seats (ID's history lines don't name the
        # house, so the converter follows the bill from house to house; WY's roll calls sometimes name the wrong one).
        seats = LEGISLATURES.get(state, {}).get("seats", {})
        big = [r["nums"][0] for r in recs for v in r["votes"] if v[1] == "F" and seats.get(v[0]) and v[4] + v[5] > seats[v[0]]]
        if big:
            say(state, "FAIL", f"{s}: {len(big)} floor votes have more ayes and noes than their house has seats, e.g. {big[:4]}")
        # Votes that never arrived: CO's download read committee votes first, and about 900 voice votes it couldn't save
        # took every run's time (2026-11-22), so the live site had 1,226 committee votes and no floor vote. A state with
        # roll calls should have a floor vote for most bills that passed a house.
        # (A session with no votes at all counts too when another session of the state has floor votes: CO's 2025.)
        passed = [r for r in recs if r["passedS"] or r["passedA"]]
        if passed and (any(r["votes"] for r in recs) or any(v[1] == "F" for x in loaded.values() for r in x for v in r["votes"])):
            with_floor = sum(1 for r in passed if any(v[1] == "F" for v in r["votes"]))
            share = with_floor / len(passed)
            # (A FAIL needs a sign roll calls exist: committee votes this session, or floor votes on most passed bills in
            # another session. NH and VT pass many bills by voice vote; next year's prefiled session isn't checked.)
            elsewhere = any(sum(1 for r in x if (r["passedS"] or r["passedA"]) and any(v[1] == "F" for v in r["votes"]))
                            >= 0.6 * max(1, sum(1 for r in x if r["passedS"] or r["passedA"])) for k, x in loaded.items() if k != s)
            # (Committee votes are a sign only when the session has no floor votes at all: Massachusetts's committees
            # post every vote by member while its houses pass most bills by voice, 111 of 564 with a roll call in 2025-26.)
            if len(passed) >= 30 and share < 0.2 and s <= date.today().year and \
                    (elsewhere or not with_floor and any(v[1] == "C" for r in recs for v in r["votes"])):
                say(state, "FAIL", f"{s}: only {with_floor} of {len(passed)} bills that passed a house have a floor vote "
                                   f"({sum(1 for r in recs for v in r['votes'] if v[1] == 'C')} committee votes): floor votes missing?")
            elif share < 0.6:
                say(state, "LOOK", f"{s}: {with_floor} of {len(passed)} bills that passed a house have a floor vote")
        # Roll calls without the members' names in one house: PA's Senate floor votes named members on about a third of
        # split votes, the House on nearly all (2026-11-22). A house's split floor votes (ayes and noes both) should name
        # members as often as the other house's.
        split_named = {}
        for h in ("S", getattr(P, "LOWER", "A")):
            fl = [v for r in recs for v in r["votes"] if v[0] == h and v[1] == "F" and v[4] and v[5]]
            if len(fl) >= 20:
                split_named[h] = (sum(1 for v in fl if v[6]) / len(fl), len(fl))
        if len(split_named) == 2:
            (a, na), (b, nb) = split_named.values()
            if max(a, b) >= 0.8 and min(a, b) < 0.5:
                say(state, "FAIL", f"{s}: split floor votes naming members: " +
                    ", ".join(f"{h} {100 * x:.0f}% of {n}" for h, (x, n) in split_named.items()) + " (one house's names missing?)")
            elif min(a, b) < 0.8 and max(a, b) >= 0.5:
                say(state, "LOOK", f"{s}: split floor votes naming members: " +
                    ", ".join(f"{h} {100 * x:.0f}% of {n}" for h, (x, n) in split_named.items()))
        # Roll calls filed under the wrong bill: KS's roll-call records name their bill, and two 2026 Senate line-item override
        # votes on the budget (HB 2513) say HB 2315, a bill that never left committee. Floor votes on a bill that never
        # left committee. (Only a LOOK: WY's budget sessions vote on introducing a bill, two-thirds needed, and the bills that
        # fail never reach a committee.)
        # A bill that reached the floor and was then sent back (MI HB 4195 of 2025: failed 39-64, then referred to a
        # committee; NH HB 565 of 2023: "Ought to Pass with Amendment ... RC 184-179", then sent to Finance) isn't one.
        floor = re.compile(r"^(?:PLACED ON FLOOR|FAILED|ADVANCED TO (?:SECOND|THIRD) READING|Ought to Pass)", re.I)
        stray = [r["nums"][0] for r in recs if r["stage"] == 0 and r["commFate"] == "none" and not r["passedS"] and not r["passedA"]
                 and any(v[1] == "F" for v in r["votes"]) and not any(floor.match(t) for v in r["vers"] for _, t in v["actions"])]
        if stray:
            say(state, "LOOK",
                f"{s}: {len(stray)} bills that never left committee have floor votes (filed under the wrong bill?), e.g. {stray[:4]}")
        # A lost vote read as a passage: NV's roll-call records say "Passed" for every final passage vote, lost ones too
        # (AB 500 of 2025: 25-17 short of two-thirds, then 20-22). A house shown as passing a bill whose every floor vote
        # there had more noes than ayes.
        low = getattr(P, "LOWER", "A")
        lost = [r["nums"][0] for r in recs for h, flag in (("S", "passedS"), (low, "passedA"))
                if r[flag] and any(v[0] == h and v[1] == "F" for v in r["votes"])
                and all(v[4] < v[5] for v in r["votes"] if v[0] == h and v[1] == "F")]
        # (Only a LOOK: where the bill's own question is a motion against it, NH's "Inexpedient to Legislate" and ME's "Ought
        # Not to Pass" reports, more noes than ayes means the bill survived.)
        if lost:
            say(state, "LOOK", f"{s}: {len(lost)} bills shown as passing a house where every floor vote had more noes than ayes, e.g. {lost[:4]}")
        # The same on the passage's own day: MT's current system marks some failed third readings "BILL_CONCURRED" (HB 93 of
        # 2025: 24-26; ties too) after a second reading that passed, so not every vote in the house lost. A "PASSED HOUSE"
        # line whose floor votes that day in that house all had no more ayes than noes.
        lostday = [r["nums"][0] for r in recs for v0 in r["vers"][:1] for d, t in v0["actions"]
                   if re.match(r"PASSED (SENATE|HOUSE|ASSEMBLY)$", t)
                   and (fl := [v for v in r["votes"] if v[1] == "F" and v[3] == d and v[0] == ("S" if t.endswith("SENATE") else low)])
                   and all(v[4] <= v[5] for v in fl)]
        if lostday:
            say(state, "FAIL" if len(lostday) > 0.005 * len(recs) else "LOOK",
                f"{s}: {len(lostday)} passages on a day whose floor votes in that house all had no more ayes than noes, e.g. {lostday[:4]}")
        # Procedural votes read as the bill's own: AL's "Third Reading in House of Origin" line carries the roll call on the
        # bill's Budget Isolation Resolution, taken just before the passage. Bills with two floor votes in one house on one
        # day: up to about a third in CO and VA (passage and a re-passage, a concurrence or an emergency clause the same
        # day); a BIR read as a passage would put nearly every AL bill there.
        twice = [r["nums"][0] for r in recs if r["votes"] and max(collections.Counter((v[0], v[3]) for v in r["votes"] if v[1] == "F").values() or [0]) > 1]
        voted = sum(1 for r in recs if r["votes"])
        if voted and len(twice) > 0.5 * voted:
            say(state, "LOOK", f"{s}: {len(twice)} of {voted} bills with floor votes have two in one house on one day (a procedural vote read as the bill's?), e.g. {twice[:4]}")
        # A substitute's vote written with both names ("Hill(Brown)" in ID's House: Brown sits for Hill; "Coho(Lenney)" in
        # its Senate: Coho sits for Lenney) left as a name: the vote belongs to the member's seat. (TX's "Speaker(C)", the
        # chair's mark, isn't a name.)
        subs = collections.Counter(m for r in recs for v in r["votes"] for m, _ in v[6] if isinstance(m, str) and "?" in m and re.search(r"\([A-Za-z][A-Za-z'’ -]+\)", m))
        if subs:
            say(state, "FAIL", f"{s}: {sum(subs.values())} votes by names with parentheses not tied to a seat, e.g. {subs.most_common(3)}")

    # Sponsors tied to a party, session by session: a session far below the others has a member list that failed to
    # match (AR's 2023-24 members file has one column fewer than 2025-26's, and every member was dropped at first).
    if hasattr(C, "parties"):
        share = {}
        for s, recs in loaded.items():
            named = [r for r in recs if r["vers"][0]["sponsor"] not in ("", "—", "?") and  # members, not committees or "?" (NV 2027's prefiled bills)
                     not re.search(r"Committee|Management|Council|Commission|Caucus|Efficiency|Rules", r["vers"][0]["sponsor"])]
            party = C.parties(s, recs)
            if len(named) >= 20:
                share[s] = sum(1 for r in named if (r["vers"][0]["p"][0], r["vers"][0]["sponsor"]) in party) / len(named)
        low = {s: f"{100 * v:.0f}%" for s, v in share.items() if share and v < 0.5 * max(share.values())}
        # (A FAIL for this year's sessions, the one before and next year's (2026-11-26: Virginia's 2025 and 2027 had none,
        # its past and prefiled sessions reading parties only for the current one; a LOOK didn't stand out). Older ones
        # stay a LOOK: GA, MI and NC 2023.)
        bad = {s: v for s, v in low.items() if s >= date.today().year - 2}
        if bad and max(share.values()) >= 0.8:
            say(state, "FAIL", f"recent sessions whose sponsors mostly have no party (a member list that didn't match?): "
                               f"{bad}, best {100 * max(share.values()):.0f}%")
        elif low:
            say(state, "LOOK", f"sessions whose sponsors mostly have no party (a member list that didn't match?): {low}, "
                               f"best {100 * max(share.values()):.0f}%")

    # Each session against the state's others (2026-11-26, after Virginia's 2025 laws lost their chapters: its bill list
    # stopped carrying the column, 0 of 721, while 2023, 2024 and 2026 had all): a share far below what another session
    # shows means a reader stopped finding something. A FAIL for recent sessions, a LOOK for older ones (whose sources
    # can be thinner: MT and KS 2023's roll calls).
    def against_others(what, shares, floor=0.8, low=0.5):
        if not shares:
            return
        best_s = max(shares, key=lambda k: shares[k][0])
        best = shares[best_s][0]
        if best < floor:
            return
        drops = {k: v for k, v in shares.items() if v[0] < low * best}
        for k, (x, n) in sorted(drops.items()):
            say(state, "FAIL" if k >= date.today().year - 2 else "LOOK",
                f"{k}: {what} {100 * x:.0f}% of {n}, {best_s} {100 * best:.0f}% of {shares[best_s][1]}")

    laws_ch = {}
    for s, recs in loaded.items():
        laws = [r for r in recs if r["stage"] == 5 and "const" not in r["topics"]]
        if len(laws) >= 20:
            laws_ch[s] = (sum(1 for r in laws if r.get("chapter")) / len(laws), len(laws))
    against_others("laws with a chapter or act number", laws_ch)
    # Split floor votes (ayes and noes both) that name members, house by house: unanimous votes are left out, since a
    # state may list only the members who didn't vote yes (DC: 2025-26's votes were more often unanimous with everyone
    # present, so fewer named anyone at all, 27% against 54%, with every member accounted for).
    for h in sorted({v[0] for recs in loaded.values() for r in recs for v in r["votes"] if v[1] == "F"}):
        named = {}
        for s, recs in loaded.items():
            fl = [v for r in recs for v in r["votes"] if v[0] == h and v[1] == "F" and v[4] and v[5]]
            if len(fl) >= 20:
                named[s] = (sum(1 for v in fl if v[6]) / len(fl), len(fl))
        against_others(f"{h} split floor votes naming members", named, low=0.6)

    # The current session's votes should name seats, not leftover names. Former members are expected: a name missing from its
    # house's last 30 days of roll calls has left (the District's Council, 13 members, lost two at-large members in 2025-26,
    # 12% of its named votes); only names still voting then count toward a FAIL (a member list that fails to match leaves
    # every recent name loose).
    cur = max(loaded)
    who = [m for r in loaded[cur] for v in r["votes"] for m, _ in v[6]]
    loose = [m for m in who if "?" in m]
    if who:
        endday = {}
        for r in loaded[cur]:
            for v in r["votes"]:
                if v[1] == "F":
                    endday[v[0]] = max(endday.get(v[0], ""), v[3])
        still = {m for r in loaded[cur] for v in r["votes"] if v[1] == "F" and endday.get(v[0]) and
                 v[3] >= (date.fromisoformat(endday[v[0]]) - timedelta(days=30)).isoformat() for m, _ in v[6]}
        share = 100 * len(loose) / len(who)
        staying = 100 * sum(1 for m in loose if m in still) / len(who)
        say(state, "FAIL" if staying > 10 else "LOOK", f"{cur}: {share:.1f}% of named votes aren't tied to a seat "
            f"({staying:.1f}% by names still voting in the last 30 days; former members are expected), "
            f"e.g. {collections.Counter(loose).most_common(3)}")

    # A member still voting at the session's end but not tied to a seat: a member list giving someone's district in the office
    # they hold now (SC's lists put Wes Climer, now in Congress, in Senate District "5", shared with Tom Corbin; his seat, 15,
    # looked vacant). Names voting (other than yes) in the house's last four months of roll calls that aren't seats.
    lastday = {}
    for r in loaded[cur]:
        for v in r["votes"]:
            if v[1] == "F":
                lastday[v[0]] = max(lastday.get(v[0], ""), v[3])
    late = collections.Counter(m for r in loaded[cur] for v in r["votes"] if v[1] == "F" and lastday.get(v[0]) and
                               v[3] >= (date.fromisoformat(lastday[v[0]]) - timedelta(days=120)).isoformat()
                               for m, _ in v[6] if isinstance(m, str) and "?" in m)
    if late:
        say(state, "LOOK", f"{cur}: {len(late)} names voting in the last four months of roll calls aren't tied to a seat "
                           f"(a member list's district wrong?), e.g. {late.most_common(3)}")

    # "What it does" says where it's from, as a sentence: "From the Legislative Reference Bureau's synopsis."
    for path in sorted(glob.glob(os.path.join(P.DATA, "texts_*.json")))[-1:]:
        labels = {v.get("label") for v in json.load(open(path)).values() if v.get("label")}
        odd = sorted(l for l in labels if not re.match(r"From the .*\.$", l))
        if odd:
            say(state, "FAIL", f"{os.path.basename(path)}: source notes not written as 'From the ....': {odd[:3]}")

    # Summary text: encoding, characters lost in the export, paragraphs cut mid-sentence, title-only summaries.
    for path in sorted(glob.glob(os.path.join(P.DATA, "texts_*.json"))):
        entries = json.load(open(path))
        texts = [t for v in entries.values() for t in (v.get("statement"), v.get("fiscal")) if t]
        name = os.path.basename(path)
        # Empty, or a placeholder where the analysis goes (2026-11-22, Oklahoma's staff summaries: "Research Analysis
        # Pending", "Please see previous summary of this measure", "The measure is currently under review"). LOOK: on
        # 2026-11-22 the owner's copies also had Indiana's "None" (about 63 a year), West Virginia's empty HB 4601 and
        # HB 5018 of 2024, Virginia 2024's cut summaries ("Installation") and Pennsylvania's one-word ones, not yet fixed.
        hollow = sorted(n for n, v in entries.items() if "statement" in v and (len((v.get("statement") or "").strip()) < 15 or re.fullmatch(
            r"(?:pending|n/?a|none|tbd|to be (?:completed|determined)|please see (?:the )?previous summary.*|"
            r"the (?:measure|bill) is (?:currently )?under review.*)\.?", (v.get("statement") or "").strip(), re.I)))
        if hollow:
            say(state, "LOOK", f"{name}: {len(hollow)} texts empty or a placeholder (\"Pending\"), e.g. {hollow[:4]}")
        enc = sum(1 for t in texts if re.search("ï¿½|�|â€|Ã©", t))
        lost = sum(1 for t in texts if re.search(r"(?<=[a-z])\?(?=[a-z]+[\s.,;])|(^|\s)\?\s+\d", re.sub(r"\S*[/=]\S*", "", t)))
        # ("…" ends a sentence a lead from a bill's text cut on purpose.)
        cut = sum(1 for t in texts if any(len(p) > 20 and not re.search(r"[.:;?!)\"”\]…]$", p.strip()) for p in t.split("\n")[:-1]))
        title = sum(1 for t in texts if re.fullmatch(r"(?:As proposed, )?(?:C\.S\.)?\S+ amends current law relating to [^.]*\.?", t.strip()))
        if enc:
            say(state, "FAIL", f"{name}: {enc} texts with wrongly decoded characters")
        if lost:
            say(state, "FAIL", f"{name}: {lost} texts with characters lost as \"?\"")
        if title:
            say(state, "FAIL", f"{name}: {title} texts that only repeat the title")
        if texts and cut / len(texts) > 0.05:
            say(state, "LOOK", f"{name}: {100 * cut // len(texts)}% of texts have a paragraph without end punctuation "
                               f"(cut mid-sentence, or real headings and lists)")

    for s, recs in loaded.items():
        path = os.path.join(P.DATA, f"texts_{s}.json")
        T = json.load(open(path)) if os.path.exists(path) else {}
        # (2026-11-23) "What it does" opens with what the bill does: not with the law as it stands ("Under current law,
        # ..." in Wisconsin's and Colorado's analyses, moved after the bill's part by states/lead_first.py), nor with a
        # subject label that repeats the title (Missouri's "Gender transition procedures", Louisiana's "Capital outlay",
        # Hawaii's "Relating to building codes."). The panel's first line is the summary when it isn't the title, else the
        # statement. LOOK over 5% of a session's texts (left: bills whose part about the bill leans on the background,
        # "This bill eliminates that prohibition.", or has no "This bill" sentence).
        from states import lead_first as LF
        firsts = [(r["nums"][0], r.get("summary") if r.get("summary") and r.get("summary") != r["title"]
                   else (T.get(r["nums"][0]) or {}).get("statement") or "", r) for r in recs]
        firsts = [x for x in firsts if x[1]]
        back = [n for n, t, _ in firsts if LF.opens_with_background(t)]
        label = [n for n, t, r in firsts if t == r.get("summary") and (LF.repeats(t, r["title"]) or re.match(r"Relating to [^.;]{1,80}\.(?:\s|$)", t))]
        for what, ns in (("open with the law as it stands (\"Under current law, ...\")", back),
                         ("open with a subject label that repeats the title", label)):
            if firsts and len(ns) > 0.05 * len(firsts):
                say(state, "LOOK", f"{s}: {len(ns)} of {len(firsts)} \"What it does\" texts ({100 * len(ns) // len(firsts)}%) {what}, e.g. {ns[:4]}")

    # Laws whose "What it does" describes a placeholder: the summary of the bill as filed, when an amendment rewrote it
    # (Illinois's shell bills: "Makes a technical change"; California's spot bills).
    for s, recs in loaded.items():
        path = os.path.join(P.DATA, f"texts_{s}.json")
        if not os.path.exists(path):
            continue
        T = json.load(open(path))
        laws = [r["nums"][0] for r in recs if r["stage"] == 5]
        found = [n for n in laws if n in T]
        # Short ones only: real summaries often also mention "technical changes".
        shell = [n for n in found if len(T[n].get("statement") or "") < 300 and re.search(
            r"technical change in a section|nonsubstantive change|intent of the Legislature to enact legislation", T[n].get("statement") or "", re.I)]
        # (Not "technical changes" alone: Connecticut's technical-revisions acts are real laws, and say so.)
        if found and len(shell) > 0.01 * len(found):
            say(state, "FAIL", f"{s}: {len(shell)} of {len(found)} laws are summarized as placeholders, e.g. {shell[:3]}")
        elif laws and len(found) < 0.5 * len(laws):
            say(state, "LOOK", f"{s}: only {len(found)} of {len(laws)} laws have a summary in {os.path.basename(path)}")
        # A staff summary that only says the title again (2026-11-22, when GA's Daily Reports, AZ's and SC's books were
        # added): every word of it in the bill's title. Texts made from the title by design ("From the bill's official
        # title.") aren't counted. LOOK only: Missouri's titles are its summaries' first sentence (SB 89 of 2025), and on
        # 2026-11-22 the owner's local copies also showed Virginia 2024's summaries cut to a few words ("Installation" for
        # HB 1037), both to look into before this can fail a run.
        tw_ =lambda t: set(re.findall(r"[a-z]{3,}", (t or "").lower())) - {"the", "and", "for", "this", "bill", "act", "that", "with"}
        bytitle = {r["nums"][0]: r["title"] for r in recs}
        echo = [n for n, v in T.items() if n in bytitle and v.get("statement") and "official title" not in (v.get("label") or "")
                and (sw := tw_(re.sub(r"^\W*(?:[HSA]\.?\s?[BRJC]*\.?\s*\d+|(?:House|Senate) Bill \d+)\b", "", v["statement"])))
                and sw <= tw_(bytitle[n])]
        if echo:
            say(state, "LOOK", f"{s}: {len(echo)} summaries only repeat the title's words, e.g. {echo[:4]}")
        # Leads quoted from a bill's own text where there's no summary (states/billtext_lead.py, 2026-11-22: WA, AK,
        # MA): none may be only boilerplate (an effective date, severability), longer than 1,200 characters, or the
        # title's words again. FAIL over 1% of them, else LOOK.
        from states import billtext_lead
        leads = [(n, v["statement"]) for n, v in T.items() if (v.get("label") or "").startswith("From the bill's text")]
        bad = collections.defaultdict(list)
        for n, t in leads:
            for p in billtext_lead.problems(t, bytitle.get(n, "")):
                bad[p].append(n)
        for p, ns in sorted(bad.items()):
            say(state, "FAIL" if len(ns) > 0.01 * len(leads) else "LOOK",
                f"{s}: {len(ns)} of {len(leads)} leads from bill texts: {p}, e.g. {ns[:4]}")
        if leads:
            amends = sum(1 for _, t in leads if t.startswith("Amends "))
            say(state, "LOOK", f"{s}: {len(leads)} leads from bill texts ({amends} only name the laws they amend)")
        # A summary of an earlier version that another bill's contents replaced: KS conference reports often put other
        # bills into a bill (HB 2043 of 2025-26: an insurance bill as passed, a property tax law after conference), and the
        # supplemental note describes it before. Laws whose summary shares almost no words with their own title.
        words = lambda t: {w for w in re.findall(r"[a-z]{5,}", (t or "").lower())} - {"would", "provide", "providing", "concerning", "relating", "certain", "requiring", "amend", "amending", "state", "statute", "statutes"}
        byn = {r["nums"][0]: r for r in recs}
        apart = [n for n in found if (tw := words(byn[n]["title"])) and len(tw) >= 4
                 and len(tw & words((T[n].get("statement") or "")[:3000])) < 0.15 * len(tw)]
        if apart:
            say(state, "LOOK", f"{s}: {len(apart)} of {len(found)} laws' summaries share almost no words with their title "
                               f"(a summary of a version another bill's contents replaced?), e.g. {apart[:4]}")

    # Contacts that lost a field: South Dakota's API emptied the 2026 members' emails and phones after the November
    # election, and Open States' file (Nevada's emails) moved to the members-elect, so the next download's contacts had
    # none (2026-11-22). The current session's and the newest file: each of email or contact form, phone and page link
    # for most members, except what the state's sources don't have (CONTACT_GAPS, each in the state's NOTES.md).
    for path in sorted({os.path.join(P.DATA, f"contacts_{cur}.json")} | set(sorted(glob.glob(os.path.join(P.DATA, "contacts_*.json")))[-1:])):
        if not os.path.exists(path):
            continue
        people = list(json.load(open(path))["people"].values())
        have = {"email or form": sum(1 for p in people if p.get("email") or p.get("form")),
                "phone": sum(1 for p in people if p.get("phone")), "page": sum(1 for p in people if p.get("url"))}
        # Emails that aren't addresses: a source's typo ("sensayama@capitol.hawaii,gov" in Hawaii's directory, "SL
        # Jones@..." in Alabama's), a contact form's address in the email column (25 Connecticut senators'), a share
        # link read as one ("?body=https..." on Colorado's pages). Each would make a broken "mailto:" link.
        bad = [p.get("email") for p in people if p.get("email") and not re.fullmatch(
            r"[^@\s,;:/<>()]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}", p["email"])]
        if bad:
            say(state, "FAIL", f"{os.path.basename(path)}: {len(bad)} emails that aren't addresses, e.g. {bad[:3]}")
        for field, n in have.items():
            if not people or field in CONTACT_GAPS.get(state, ()):
                continue
            if n < 0.5 * len(people):
                say(state, "FAIL", f"{os.path.basename(path)}: {field} for only {n} of {len(people)} legislators")
            elif n < 0.9 * len(people):
                say(state, "LOOK", f"{os.path.basename(path)}: {field} for {n} of {len(people)} legislators")

    # Legislators: degrees in names, odd spacing, duplicate phones, missing parties or phones.
    for path in sorted(glob.glob(os.path.join(P.DATA, "contacts_*.json")))[-1:]:
        people = json.load(open(path))["people"]
        deg = [p["name"] for p in people.values() if re.search(r"^(Dr|Rev|Hon)\.\s|\b(M\.D\.|Ph\.D\.|Ed\.D\.|Esq\.?)$", p["name"])]
        spaces = [p["name"] for p in people.values() if re.search(r"\s{2,}|\blll\b", p["name"])]
        dup = [p["name"] for p in people.values() if len(p.get("phones") or []) != len({tuple(x) for x in p.get("phones") or []})]
        noparty = [p["name"] for p in people.values() if not p.get("party")]
        nophone = [p["name"] for p in people.values() if not p.get("phone")]
        for label, xs in (("names with a degree or title", deg), ("names with odd spacing or \"lll\"", spaces),
                          ("legislators with a phone number twice", dup)):
            if xs:
                say(state, "FAIL", f"{os.path.basename(path)}: {label}: {xs[:4]}")
        if noparty or nophone:
            say(state, "LOOK", f"{os.path.basename(path)}: no party {noparty[:3]}, no phone {nophone[:3]}")
        # Photos on the legislators' pages: the contacts' own, else photos.py's (data/<state>/photos.json).
        import photos
        nophoto = [p["name"] for sid, p in people.items() if not photos.image_of(P.DATA, sid, p)]
        if people and len(nophoto) > 0.2 * len(people):
            say(state, "LOOK", f"{os.path.basename(path)}: only {len(people) - len(nophoto)} of {len(people)} legislators "
                               f"have a photo (initials instead), e.g. no photo for {nophoto[:3]}")
        # A district map that doesn't match the member list (New Hampshire's HouseDistricts.txt still has the 2012 map):
        # every legislator's district is one some place in "Where you live" gives.
        towns = json.load(open(P.TOWNS_PATH)) if os.path.exists(getattr(P, "TOWNS_PATH", "")) else []
        if towns and isinstance(towns[0], list) and len(towns[0]) >= 3:
            # (Members elected at large, the District's Council's district 9, P.AT_LARGE, represent every place.)
            have = {"S": set(), "L": {P.AT_LARGE} if hasattr(P, "AT_LARGE") else set()}
            for t in towns:
                for key, i in (("S", 2), ("L", 3 if len(t) > 3 else 2)):
                    have[key] |= {int(d[0]) for d in t[i] if isinstance(d, list) and str(d[0]).isdigit()}
            off = [sid for sid in people if re.match(r"\d+", sid[2:]) and
                   int(re.match(r"\d+", sid[2:]).group()) not in have["S" if sid[0] == "S" else "L"]]
            if off:
                say(state, "FAIL", f"{os.path.basename(P.TOWNS_PATH)}: {len(off)} legislators' districts aren't in any place's list, e.g. {off[:4]}")

    # A label that means a different procedure in different states. "Constitutional amendments" in New York are
    # resolutions that never go to the governor (STATE.amendments in profile.js); in Virginia they're bills that set up
    # the ballot question, which the governor signs. Where the profile says amendments skip the governor, none may reach
    # the governor's desk; elsewhere the tag is only a topic.
    skips = re.search(r"^\s*amendments:\s*true", open(os.path.join(HERE, "states", state, "profile.js")).read(), re.M)
    for s, recs in loaded.items():
        tagged = [r for r in recs if "const" in r["topics"]]
        sent = [r["nums"][0] for r in tagged if r["stage"] >= 4]
        if skips and sent:
            say(state, "FAIL", f"{s}: {len(sent)} constitutional amendments went to the governor, though they skip the governor: {sent[:4]}")
        elif sent:
            say(state, "LOOK", f"{s}: {len(sent)} bills tagged constitutional amendments went to the governor (bills, not the amendments; "
                               f"the page mustn't say they skip the governor): {sent[:3]}")

    # Committee agendas (the newest session's, as build_data.py reads them): every bill named must be a record's number (a
    # number written another way, "HB0005" or "H.B. 5", shows nothing), each entry a committee with its house and a local
    # ISO time. LOOK at the count, so a reader that stops finding meetings mid-session is noticed.
    # (New York has no agendas(): its file, data/agendas_<session>.json from fetch_agendas.py, as build_data.py reads it.)
    ny_file = os.path.join(P.DATA, f"agendas_{max(loaded)}.json") if loaded and not hasattr(C, "agendas") else ""
    if (hasattr(C, "agendas") or os.path.exists(ny_file)) and loaded:
        s = max(loaded)
        try:
            ag = (C.agendas(s) if hasattr(C, "agendas") else json.load(open(ny_file))) or {}
        except Exception as e:  # (a reader that fails here fails the build too)
            ag = {}
            say(state, "FAIL", f"{s}: agendas() failed: {e!r}")
        nums = {re.sub(r"[A-Z]$", "", v["p"]) for r in loaded[s] for v in r["vers"]}
        stray = sorted(k for k in ag if k not in nums)
        if stray:
            say(state, "FAIL" if len(stray) > max(2, len(ag) // 50) else "LOOK",
                f"{s}: {len(stray)} of {len(ag)} bills on committee agendas aren't records' numbers: {stray[:5]}")
        # (A third item is the meeting's kind: Congress's "markup" or "hearing", or "meets" for a meeting that names no bills,
        # given to every bill in that committee (the Mississippi House), which may have a fourth, a note on the time.)
        # A floor calendar's day (kind "floor") names the house as its committee, "Senate floor" (one of the state's houses),
        # with a fourth item "listed" when the calendar lists bills that can come up that day rather than a vote set for it,
        # or "likely" for a day guessed from the bill's history where no calendar is read (states/floorcal.py's likely()).
        houses = set(getattr(P, "HOUSES", {}).values()) if isinstance(getattr(P, "HOUSES", None), dict) else set()
        try:
            js = open(os.path.join(HERE, "states", state, "profile.js")).read()
            m = re.search(r"houses:\s*\{([^}]*)\}", js)
            houses |= set(re.findall(r'"([^"]+)"', m.group(1))) if m else set()
        except OSError:
            pass
        floor_ok = lambda e: (len(e) in (3, 4) and e[2] == "floor" and (len(e) < 4 or e[3] in ("", "listed", "likely"))
                              and re.fullmatch(r"(.+) floor", e[0] or "") and (not houses or e[0][:-6] in houses))
        bad = [(k, e) for k, es in ag.items() for e in es
               if not (isinstance(e, (list, tuple)) and 2 <= len(e) <= 4 and re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d(?::\d\d)?", e[1] or "")
                       and (floor_ok(e) if len(e) > 2 and e[2] == "floor" else
                            re.match(r"(?:House|Senate|Assembly|Joint|Legislative|Unicameral|Council) \S", e[0] or "")
                            and (len(e) < 3 or e[2] in ("", "markup", "hearing", "meets")) and (len(e) < 4 or e[2] == "meets")))]
        if bad:
            say(state, "FAIL", f"{s}: {len(bad)} agenda entries aren't [\"House Committee\", \"YYYY-MM-DDTHH:MM:SS\"(, kind)]"
                               f" or [\"Senate floor\", \"YYYY-MM-DDTHH:MM:SS\", \"floor\"(, \"listed\" or \"likely\")]: {bad[:3]}")
        # Floor calendars: each bill named is a record's number (above); one still in committee in the house whose calendar
        # names it would be a misread (a committee calendar read as the floor's). LOOK at the count.
        flo = {k: [e for e in es if len(e) > 2 and e[2] == "floor"] for k, es in ag.items()}
        flo = {k: es for k, es in flo.items() if es}
        if flo:
            rec_of = {re.sub(r"[A-Z]$", "", v["p"]): r for r in loaded[s] for v in r["vers"]}
            early = sorted(k for k in flo if k in rec_of and rec_of[k]["stage"] == 0)
            days = {(e[0], e[1][:10]) for es in flo.values() for e in es}
            listed = sum(1 for es in flo.values() if all(len(e) > 3 and e[3] == "listed" for e in es))
            likely = sum(1 for es in flo.values() if all(len(e) > 3 and e[3] == "likely" for e in es))
            # A likely vote (no calendar: the next weekday after the bill's reading) on a weekend, or for a bill past the
            # floor (passed both houses), would be a misread history. (Not in a replay, FLOOR_TODAY: the stages are today's.)
            from datetime import date as _date
            odd = sorted(k for k, es in flo.items() for e in es if len(e) > 3 and e[3] == "likely"
                         and (_date.fromisoformat(e[1][:10]).weekday() >= 5 or (k in rec_of and rec_of[k]["stage"] >= 3 and not os.environ.get("FLOOR_TODAY"))))
            if odd:
                say(state, "FAIL", f"{s}: {len(odd)} likely floor votes on a weekend or for bills past the floor: {odd[:5]}")
            say(state, "LOOK", f"{s}: {len(flo)} bills on {len(days)} house floor calendars"
                               + (f" ({listed} only listed as able to come up, not set for a vote)" if listed else "")
                               + (f" ({likely} likely votes guessed from the bills' histories, no calendar)" if likely else "")
                               + (f"; {len(early)} of them still in committee now: {early[:5]}" if early else ""))
        ag = {k: [e for e in es if not (len(e) > 2 and e[2] == "floor")] for k, es in ag.items()}
        ag = {k: es for k, es in ag.items() if es}
        if ag:
            named = {k: [e for e in es if len(e) < 3 or e[2] != "meets"] for k, es in ag.items()}
            meets = {tuple(e) for es in named.values() for e in es}
            only = {tuple(e) for es in ag.values() for e in es if len(e) > 2 and e[2] == "meets"}
            say(state, "LOOK", f"{s}: {sum(1 for es in named.values() if es)} bills on {len(meets)} upcoming committee meetings' agendas"
                + (f"; {sum(1 for es in ag.values() if any(len(e) > 2 and e[2] == 'meets' for e in es))} bills in committees with"
                   f" {len(only)} meetings that name no bills" if only else ""))

    # Other states' names and rules on this state's pages (settings that fell back to New York's).
    words = r"Albany|Hochul|Heastie|Stewart-Cousins|Kelles|Tompkins|New York State|nysenate|nyassembly"
    pages = [] if state == "ny" else sorted(glob.glob(os.path.join(HERE, "site", P.SITE_DIR, "*.html")))[-1:] + \
        glob.glob(os.path.join(HERE, "_site", P.SITE_DIR, "index.html"))  # the Claude copy, or the public build
    for page in pages:
        html = open(page).read()
        html = re.sub(r"(?s)<script[^>]*>.*?</script>", "", html)  # the code (comments mention other states)
        hits = sorted(set(re.findall(words, html)))
        if hits:
            say(state, "FAIL", f"{os.path.basename(page)}: New York's names on the page: {hits}")


def check_balance(state):
    """The balance of power (balance.py): every built state has its legislature in states/legislatures.json and a member
    list, and each chamber's party counts and vacancies add up to its seats."""
    sys.path.insert(0, HERE)
    import balance
    if state not in balance.table():
        say(state, "FAIL", "not in states/legislatures.json (seats, veto override, governor)")
        return
    b = balance.current(state)
    if not b:
        say(state, "FAIL", "no member list for the balance of power")
        return
    for c, ch in b["chambers"].items():
        if ch["vacant"] < 0:
            say(state, "FAIL", f"{c}: {sum(ch['parties'].values())} members for {ch['seats']} seats")
        elif ch["vacant"] > 0.05 * ch["seats"]:
            say(state, "LOOK", f"{c}: {ch['vacant']} of {ch['seats']} seats vacant (a stale member list?)")
        if "?" in ch["parties"]:
            say(state, "FAIL", f"{c}: {ch['parties']['?']} members with no party")
    say(state, "LOOK", "balance: " + " | ".join(f"{c} " + "-".join(f"{k}{v}" for k, v in ch["parties"].items())
                                               + (f" +{ch['vacant']} vacant" if ch["vacant"] else "")
                                               + (" (can override)" if ch["canOverride"] else "")
                                               for c, ch in b["chambers"].items()) + f" | governor {b['governor'][1]}")


def check_light(state):
    """The state's light history (data/<st>/light_<session>.json.gz, states/LIGHT.md): its counts to compare with the
    official totals (LOOK), and what can't be right (FAIL): a date in the future, a law number on a bill that isn't a law,
    passage flags that disagree with the stage, a law with no signature, chapter or other date where the session's laws
    otherwise have one."""
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
    import states.light as LH
    P = importlib.import_module(f"states.{state}.profile")
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    for s in LH.sessions_on_disk(P.DATA):
        b = LH.read(P.DATA, s)
        if not b:
            say(state, "FAIL", f"light {s}: unreadable")
            continue
        bills = b["bills"]
        say(state, "LOOK", f"light {s}: {b['counts']} (compare with the official totals); lacks {b['lacks'] or 'nothing'}; "
                            f"{b.get('noTopic', 0)} with no topic")
        # (What build_data.py's light_plausible() leaves off the site, said here so a held-back session is seen:
        # Open States' Virginia 2018 and Michigan 2019-20 stop short of the governor's actions, 2026-11-25.)
        laws = sum(1 for x in bills if x.get("stage") == 5)
        waiting = sum(1 for x in bills if x.get("stage") in (3, 4) and "const" not in (x.get("topics") or []))
        one = sum(1 for x in bills if (x.get("stage") or 0) < 3 and (x.get("passedS") or x.get("passedA")))
        if laws > 50 and waiting > 0.15 * (laws + waiting):
            say(state, "LOOK", f"light {s}: left off the site: {waiting} bills past both houses with no outcome against {laws} laws "
                                f"(records that stop short of the governor's actions)")
        elif state not in ("ne", "dc") and len(bills) > 300 and laws > 50 and not one:
            say(state, "LOOK", f"light {s}: left off the site: {laws} laws but no bill past one house only")
        future = sorted({x["nums"][0] for x in bills if any(str(d)[:10] > tomorrow for d in
                         [x.get("first") or "", x.get("last") or ""] + [p for d in x.get("keyDates") or [] for p in str(d).split(";")])})
        if future:
            say(state, "FAIL", f"light {s}: {len(future)} bills dated in the future, e.g. {future[:4]}")
        # (DC's B21-0455 of 2015 had "2016/11/29" from the law library, and the build stopped on it: dates are ISO only.)
        odd = sorted({x["nums"][0] for x in bills if any(p and not re.fullmatch(r"\d{4}-\d\d-\d\d.*", p) for p in
                      [x.get("first") or "", x.get("last") or ""] + [p for d in x.get("keyDates") or [] for p in str(d).split(";")])})
        if odd:
            say(state, "FAIL", f"light {s}: {len(odd)} bills with dates not written YYYY-MM-DD, e.g. {odd[:4]}")
        chap = [x["nums"][0] for x in bills if x.get("chapter") and x.get("stage") != 5]
        if chap:
            say(state, "FAIL" if len(chap) > 0.005 * len(bills) else "LOOK",
                f"light {s}: {len(chap)} law numbers on bills that aren't laws, e.g. {chap[:4]}")
        one_house = getattr(P, "UNICAMERAL", False) or state == "ne"
        both = [x["nums"][0] for x in bills if not one_house and x.get("stage") in (3, 4, 5, 6)
                and "const" not in (x.get("topics") or []) and not (x.get("passedS") and x.get("passedA"))]
        if both:
            say(state, "FAIL" if len(both) > 0.005 * len(bills) else "LOOK",
                f"light {s}: {len(both)} bills past both houses without both passage flags, e.g. {both[:4]}")
        laws = [x for x in bills if x.get("stage") == 5]
        bare = [x["nums"][0] for x in laws if not x.get("chapter") and not (x.get("keyDates") or [""] * 7)[5]]
        if laws and "chapter" in b["has"] and bare:
            say(state, "FAIL" if len(bare) > 0.02 * len(laws) else "LOOK",
                f"light {s}: {len(bare)} of {len(laws)} laws with neither a chapter nor a signing date, e.g. {bare[:4]}")


def main():
    for state in (sys.argv[1:] or STATES):
        check(state)
        check_balance(state)
        check_light(state)
    print(f"\n{len(fails)} problem(s)" + ("".join(f"\n- {f}" for f in fails) if fails else ""))
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
