"""The District of Columbia's bills in the shape build_data.py reads. A page per two-year Council Period (2025 is Council
Period 26, 2025-26).

Source: LegiScan's files for the Council (legiscan.py into data/dc/legiscan/<session_id>/; CC BY 4.0, credited on every
page), read with the shared helpers in states/legiscan_convert.py (bills(): each bill brought up to date from the last
master list; people(); folders(); fetched()). The Council's own Legislative Information Management System (LIMS,
lims.dccouncil.gov) has a public API, but it needs a developer key from a sign-up form, and LIMS's robots.txt says
"Disallow: /" for every reader: states/dc/NOTES.md. LegiScan copies its records from LIMS (each bill's `state_link` is
its LIMS page), with the same history wording.

One house: the Council ("B", P.LOWER; bills "B26-0001" are "B1" here, shown "B 1"). Only permanent bills are records.
Every act the Council passes is a "B" bill, and about half of them are emergency acts (one reading, in effect up to 90
days the moment the Mayor signs, never sent to Congress) or temporary acts (two readings, in effect up to 225 days after
Congress's review), usually passed alongside a permanent bill on the same subject to keep a rule in force while the
permanent one goes through. They're left out as records (the shared "bills only" rule: they'd count each change three
times) and named in their permanent bill's history ("Emergency version, B26-0849: ...") when their titles match
(`companion_key()`). Resolutions (PR, CER) are left out.

The steps of a permanent bill, as LIMS writes them:
- "Introduced in Office of the Secretary"; "Referred to Committee on Health" (the Chairman refers each bill; "Committee on
  Committee of the Whole" is the whole Council, chaired by the Chairman; "Retained by the Council": no committee).
- "Notice of Public Hearing Published in the DC Register", "Public Hearing Held" (or "Roundtable Hearing Held");
  "Committee Mark-up of B26-0799" (the committee's meeting to vote on its version; LIMS lists it ahead of time, dated the
  meeting's day, and records no committee roll calls), "Committee Report Filed" (the committee approved it). A hearing or
  mark-up dated after today is an upcoming meeting: `agendas()`, not the history.
- Two readings at legislative meetings at least 13 days apart (Home Rule Act sec. 412, D.C. Code 1-204.12): "First
  Reading" and "Final Reading" (", CC": on the consent agenda), each with a roll call; a reading whose roll call failed is
  a defeat. "Postponed Indefinitely" kills it; "Withdrawn" ends it.
- "Transmitted to Mayor, Response Due on November 2, 2026" (10 days, excluding Saturdays, Sundays and holidays:
  D.C. Code 1-204.04(e)); "Signed by the Mayor and Enacted with Act Number A26-0458", "Enacted without Mayor's Signature
  with Act Number ...", "Vetoed by the Mayor", "Override of Mayor's Veto" (two-thirds of those present and voting).
- "Transmitted to Congress[, Projected Law Date is Dec 15, 2026]": an act takes effect only after 30 days of Congress's
  session (60 for criminal law in Titles 22-24) unless Congress passes and the President signs a joint resolution
  disapproving it (D.C. Code 1-206.02(c)); then "Law L26-0132, Effective from Jun 11, 2026 ...".

Stages: an enacted act (signed, without signature, or over a veto) is stage 5 even while Congress reviews it, as a law
everywhere else on the site is counted from the governor's signature; its status words say "under review by Congress"
until the law number (STATE.lawText()). Votes: the readings' and overrides' roll calls, member by member; seats are the
current members' ("B:3", the at-large "B:9a" ...: contacts.py) in the current Council Period, names otherwise.
"""
import json, os, re
from datetime import date
from collections import Counter, defaultdict

from states import legiscan_convert as L
from states.dc import profile as P
from states.undated import settle

H = "B"  # the only house
HOUSE = {"B": "Council"}
SEATS = 13
_LOADED, _SEATS, _COMPANIONS = {}, {}, {}

# Emergency and temporary acts: "... Emergency Amendment Act of 2025", "... Temporary Act of 2026", "... Congressional
# Review Emergency Amendment Act of 2025", "... Emergency Approval Act ..." (not "Emergency Medical Services ... Act").
SHORT_TERM = re.compile(r"\b(Emergency|Temporary)(?: (?:Amendment|Approval|Declaration|Review Amendment))? (?:Act )?of \d{4}\b", re.I)
MONTHS = {m: i for i, m in enumerate("jan feb mar apr may jun jul aug sep oct nov dec".split(), 1)}


def sessions():
    return list(L.folders(P.DATA))


def number(n):
    """"B26-0001" -> "B1" (the Council Period is the page's)."""
    m = re.match(r"B\d+-0*(\d+)$", n or "")
    return f"B{m.group(1)}" if m else None


def official(n, session):
    """"B1" on Council Period 26's page -> "B26-0001", as LIMS writes it."""
    return f"B{P.period_of(session)}-{int(n[1:]):04d}"


def iso(text):
    """"November 2, 2026", "Jan 27, 2027", "11/17/2026" -> "2026-11-02", or ""."""
    m = re.search(r"\b([A-Z][a-z]{2})[a-z]*\.? (\d{1,2}),? (\d{4})", text or "")
    if m and m.group(1).lower() in MONTHS:
        return f"{m.group(3)}-{MONTHS[m.group(1).lower()]:02d}-{int(m.group(2)):02d}"
    m = re.search(r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b", text or "")
    return f"{m.group(3)}-{int(m.group(1)):02d}-{int(m.group(2)):02d}" if m else ""


def kind_of(b):
    """"emergency", "temporary" or "" (a permanent bill), from the title as introduced."""
    m = SHORT_TERM.search(base_title(b.get("title")))
    return m.group(1).lower() if m else ""


def base_title(t):
    return re.sub(r"\s*\(now known as .*$", "", L.text(t)).strip()


def title_of(b):
    """The bill's title as it stands: a bill renamed in committee says 'Juvenile Curfew Amendment Act of 2025 (now known as
    "Youth Curfew Amendment Act of 2026")': the new name."""
    t = L.text(b.get("title"))
    m = re.search(r"\(\s*now known as\s+[\"'“”]+(.+?)[\"'“”)]*\s*$", t)
    if m:
        t = m.group(1).strip(" \"'“”")
    return t.rstrip("”\"").strip()


COMPANION_STOP = {"emergency", "temporary", "congressional", "review", "second", "third", "continuation", "supplemental",
                  "act", "amendment", "of", "the", "and", "approval", "declaration"}


def companion_key(t):
    """The words a permanent bill and its emergency and temporary versions share: "Rent Stabilized Housing Inflation
    Protection Continuation Emergency Amendment Act of 2025" -> "housing inflation protection rent stabilized"."""
    ws = re.findall(r"[a-z0-9]+", base_title(t).lower())
    ws = [w for w in ws if w not in COMPANION_STOP and not re.fullmatch(r"(?:19|20)\d\d", w)]
    return " ".join(sorted(set(ws))) if len(ws) >= 2 else ""


def comm_name(c):
    """"Committee on Health" -> "Health"; "Committee on Committee of the Whole[, Subcommittee on ...]" -> "Committee of the
    Whole" (a subcommittee's bills stay with the committee)."""
    c = L.text(c)
    c = re.sub(r"^(?:the )?Committee on (?=Committee of the Whole)", "", c)
    c = re.sub(r",\s*Subcommittee on .*$", "", c)
    c = re.sub(r"^(?:the )?Committee on (?:the )?", "", c)
    return c.replace(", and ", " and ").strip()


def roll_calls(folder, b):
    """The bill's roll calls (vote/<id>.json), oldest first."""
    out = []
    for v in b.get("votes") or []:
        r = (L.read_json(os.path.join(folder, "vote", f"{v['roll_call_id']}.json")) or {}).get("roll_call") or v
        out.append(r)
    return sorted(out, key=lambda r: (r.get("date") or "", r.get("roll_call_id") or 0))


def seats(session):
    """people_id -> seat for the members holding a seat now (contacts_<session>.json, built by contacts.py), in the current
    Council Period only: earlier periods' seats may have been held by others, so their voters keep their names."""
    if session not in _SEATS:
        out = {}
        if session == max(sessions() or [session]):
            c = L.read_json(os.path.join(P.DATA, f"contacts_{session}.json"), {}) or {}
            out = {int(p["id"]): sid for sid, p in (c.get("people") or {}).items() if str(p.get("id", "")).isdigit()}
        _SEATS[session] = out
    return _SEATS[session]


def companions(session, bills):
    """companion_key -> [(kind, bill)] for the session's emergency and temporary acts."""
    out = defaultdict(list)
    for b in bills:
        k = kind_of(b)
        if k:
            key = companion_key(b.get("title"))
            if key:
                out[key].append((k, b))
    return out


def outcome_line(kind, b, session):
    """One history line for an emergency or temporary version: what became of it, or None while it's still moving."""
    num = b["bill_number"]
    word = "Emergency" if kind == "emergency" else "Temporary"
    hist = [(a.get("date") or "", L.text(a.get("action"))) for a in b.get("history") or []]
    law = next(((d, t) for d, t in hist if re.match(r"Law (?:Number )?L\d", t)), None)
    act = next(((d, t) for d, t in hist if re.match(r"(?:Signed by the Mayor and Enacted|Enacted without Mayor's Signature)", t)), None)
    if kind == "temporary" and law:
        m = re.search(r"Law (?:Number )?(L[\d-]+)", law[1])
        ends = re.search(r"Expires on (.+)$", law[1])
        return law[0], f"{word} version, {num}: became law{f' ({m.group(1)})' if m else ''}" + (f", in effect until {ends.group(1)}" if ends else "")
    if act:
        m = re.search(r"Act Number (A[\d-]+)", act[1])
        ends = re.search(r"Expires on (.+)$", act[1])
        how = "signed by the Mayor" if act[1].startswith("Signed") else "enacted without the Mayor's signature"
        tail = (", in effect until " + ends.group(1)) if kind == "emergency" and ends else \
            "; it takes effect after Congress's review, for up to 225 days" if kind == "temporary" else ""
        return act[0], f"{word} version, {num}: {how}{f' ({m.group(1)})' if m else ''}{tail}"
    if any(re.match(r"(?:First|Final) Reading", t) for _, t in hist):
        return None  # still moving: its own page has the rest
    return None


def decode(t):
    """A history line -> (kind, extra). Kinds: intro, refer, retained, hearing, report, first, final, sent, signed, nosign,
    veto, override, congress, law, withdrawn, killed, amend, None (kept as written, changes nothing)."""
    m = re.match(r"(?:Re-?)?[Rr]eferred to (?:the )?(Committee .+?)(?: with comments from .*)?$", t)
    if m:
        return "refer", {"comm": comm_name(m.group(1))}
    if t.startswith("Introduced"):
        return "intro", {}
    if t.startswith("Retained by the Council"):
        return "retained", {}
    if re.match(r"(?:Public|Roundtable) Hearing Held", t):
        return "hearing", {}
    if re.match(r"Committee Mark-?up of", t):
        return "markup", {}
    if re.match(r"Committee Report Filed", t):
        return "report", {}
    if re.match(r"First Reading", t):
        return "first", {}
    if re.match(r"Final Reading", t):
        return "final", {}
    if t.startswith("Transmitted to Mayor"):
        return "sent", {"due": iso(t)}
    if t.startswith("Signed by the Mayor"):
        m = re.search(r"Act Number (A[\d-]+)", t)
        return "signed", {"act": m.group(1) if m else ""}
    if t.startswith("Enacted without Mayor"):
        m = re.search(r"Act Number (A[\d-]+)", t)
        return "nosign", {"act": m.group(1) if m else ""}
    if re.match(r"Vetoed by the Mayor", t):
        return "veto", {}
    if re.match(r"Override of Mayor's Veto|Veto Override", t, re.I):
        return "override", {}
    if t.startswith("Transmitted to Congress"):
        return "congress", {"projected": iso(t)}
    m = re.match(r"Law (?:Number )?(L\d+)-0*(\d+)", t)
    if m:
        return "law", {"law": f"{m.group(1)}-{int(m.group(2)):04d}", "num": int(m.group(2)), "effective": iso(t.split("Effective from", 1)[-1]) if "Effective from" in t else ""}
    if re.match(r"Withdrawn", t, re.I):
        return "withdrawn", {}
    if re.match(r"Postponed Indefinitely|Tabled", t, re.I):
        return "killed", {}
    if re.search(r"\bamendment\b|\bANS\b", t, re.I):
        return "amend", {}
    return None, {}


def plain(t, kind, extra, b, session):
    """A history line as the page shows it."""
    if kind == "refer":
        c = extra["comm"]
        return f"Referred to the {c}" if c.startswith("Committee") else f"Referred to the Committee on {c}"
    if kind == "markup":
        return "Marked up by the committee"
    if kind == "report":
        return "Committee report filed (approved by the committee)"
    if t == "Public Hearing":
        return "Public hearing"
    if kind == "first":
        return "First reading" + (" (consent agenda)" if t.endswith(", CC") else "")
    if kind == "final":
        return "Final reading" + (" (consent agenda)" if t.endswith(", CC") else "")
    if kind == "sent":
        return f"Sent to the Mayor (response due {t.split('Response Due on', 1)[1].strip()})" if "Response Due on" in t else "Sent to the Mayor"
    if kind == "signed":
        return f"Signed by the Mayor (Act {extra['act']})" if extra.get("act") else "Signed by the Mayor"
    if kind == "nosign":
        return f"Enacted without the Mayor's signature (Act {extra['act']})" if extra.get("act") else "Enacted without the Mayor's signature"
    if kind == "veto":
        return "Vetoed by the Mayor"
    if kind == "override":
        return "The Council overrode the Mayor's veto"
    if kind == "congress":
        return "Sent to Congress for review" + (f"; projected to become law {t.split('Projected Law Date is', 1)[1].strip()}" if "Projected Law Date is" in t else "")
    if kind == "law":
        eff = re.search(r"Effective from ([A-Z][a-z]+ \d+, \d{4})", t)
        return f"Became law ({extra['law']})" + (f", effective {eff.group(1)}" if eff else "")
    if kind == "intro":
        return "Introduced"
    if kind == "retained":
        return "Kept by the full Council (no committee)"
    m = re.match(r"Notice of Intent to Act on .* Published in the DC Register", t)
    if m:
        return "Notice of intent to act published in the D.C. Register"
    if t.startswith("Act A") and "Published in DC Register" in t:
        return re.sub(r"^Act (A[\d-]+) Published in DC Register", r"Act \1 published in the D.C. Register", t)
    if t == "Returned from Mayor":
        return "Returned from the Mayor"
    return t[:1].upper() + t[1:]


def passed_call(calls, day, label):
    """The roll call on a reading that day (label "First Reading" / "Final Reading" / "Override"): (yes, no, passed, call)
    or None when there's none."""
    same = [r for r in calls if (r.get("date") or "")[:10] == day and re.match(label, L.text(r.get("desc")), re.I)]
    if not same:
        return None
    r = same[-1]
    # (Decided from the tally: LegiScan's "passed" is 0 on some unanimous readings, B25-0202's 13-0 Final Reading. An
    # override needs two-thirds of those voting.)
    yes, no = int(r.get("yea") or 0), int(r.get("nay") or 0)
    ok = yes * 3 >= 2 * (yes + no) if re.search("Override|Veto", label, re.I) else yes > no
    return yes, no, ok and yes > 0, r


def record(session, folder, b, comps, ppl):
    n = number(b["bill_number"])
    hist = sorted(enumerate(b.get("history") or []), key=lambda x: ((x[1].get("date") or "")[:10], x[0]))
    calls = roll_calls(folder, b)
    steps = []   # (date, kind, text, extra)
    today = date.today().isoformat()
    for _, a in hist:
        d = (a.get("date") or "")[:10]
        t = L.text(a.get("action"))
        k, extra = decode(t)
        if d > today:
            # A step LIMS lists ahead of time: an upcoming hearing or mark-up (agendas()), or a referral that takes effect
            # at the next legislative meeting (B26-0883: introduced November 16, 2026, "Referred" December 1).
            continue
        if k in ("first", "final"):
            rc = passed_call(calls, d, "First Reading" if k == "first" else "Final Reading")
            if rc and not rc[2]:
                k = "failed"
                extra = {"tally": rc[:2], "reading": "first" if t.startswith("First") else "final"}
        if k == "override":
            rc = passed_call(calls, d, r"Override|Veto")
            if rc and not rc[2]:
                k = "overridefail"
        txt = plain(t, k, extra, b, session) if k != "failed" else \
            f"{'First' if extra['reading'] == 'first' else 'Final'} reading failed, {extra['tally'][0]}-{extra['tally'][1]}"
        if k == "overridefail":
            txt = "The Council's vote to override the Mayor's veto failed"
        steps.append((d, k, txt, extra))
    # The Council's law library (states/dc/laws.py: github.com/DCCouncil/law-xml) where LegiScan's history stops short:
    # the act's enactment and the law's number and effective date (LegiScan's 25th Council ends in January 2025).
    lx = law_table(session).get(b["bill_number"]) or {}
    kinds = {k for _, k, _, _ in steps}
    if lx.get("act") and not kinds & {"signed", "nosign", "override", "veto"} and lx.get("enacted"):
        steps.append((lx["enacted"][:10], "enacted", f"Enacted (Act A{lx['act']}; the Council's law library)", {"act": "A" + lx["act"]}))
    if lx.get("law") and "law" not in kinds:
        m = re.match(r"(\d+)-0*(\d+)$", lx["law"])
        if m:
            day = (lx.get("effective") or "")[:10] or (lx.get("enacted") or "")[:10]
            if day > today:
                # (A law whose effective date is still to come: dated by its last step before, never in the future.)
                day = max([x for x, _, _, _ in steps if x <= today] + [(lx.get("enacted") or "")[:10]])
            eff = f", effective {fmt(day)}" if lx.get("effective") else ""
            steps.append((day, "law", f"Became law (L{m.group(1)}-{int(m.group(2)):04d}){eff}",
                          {"law": f"L{m.group(1)}-{int(m.group(2)):04d}", "num": int(m.group(2)), "effective": lx.get("effective") or ""}))
    # Emergency and temporary versions, named in this bill's history on the day each was enacted.
    for kind, c in comps:
        line = outcome_line(kind, c, session)
        if line and line[0]:
            steps.append((line[0][:10], "companion", line[1], {"num": c["bill_number"]}))
    steps.sort(key=lambda s: s[0])

    place, comm, passed, sent, enacted, vetoed, overridden, lawnum, ended = "desk", None, False, False, "", False, False, None, ""
    first_ref, reported = None, False
    for d, k, t, e in steps:
        if k == "refer":
            place, comm = "committee", e["comm"]
            first_ref = first_ref or e["comm"]
        elif k == "retained" and not passed:
            place, comm = "floor", None
        elif k in ("report", "markup", "first") and not passed:
            # (A mark-up held is the committee's approval: its report usually follows within weeks; LIMS writes a
            # cancellation notice when one is called off.)
            place = "floor"
            reported = True
        elif k is None and re.match(r"Notice of Mark-?up Cancellation", t) and not passed and \
                not any(k2 in ("report", "first") for d2, k2, _, _ in steps if d2 <= d):
            place, reported = "committee", False
        elif k == "final":
            passed = True
        elif k == "failed":
            ended = "failed"
        elif k == "sent":
            sent = True
        elif k in ("signed", "nosign", "enacted"):
            enacted = k
        elif k == "veto":
            vetoed = True
        elif k == "override":
            overridden = True
        elif k == "law":
            lawnum = e
        elif k in ("withdrawn", "killed") and not passed:
            ended = k
    if enacted or (vetoed and overridden) or lawnum:
        stage = 5
    elif vetoed:
        stage = 6
    elif sent:
        stage = 4
    elif passed:
        stage = 3
    else:
        stage = 1 if place == "floor" else 0
    if stage == 3 and not any(k == "final" for _, k, _, _ in steps):
        stage = 1

    title = title_of(b)
    refs = [e["comm"] for _, k, _, e in steps if k == "refer"]
    topics = []
    for c in refs:
        tp = P.COMMITTEE_TOPICS.get(c)
        if tp and tp not in topics:
            topics.append(tp)
    if not topics:
        for tp, rx in P.TOPIC_WORDS.items():
            if rx.search(title) and tp not in topics:
                topics.append(tp)
    topics = [t for t in topics if t != "const"]

    sp = sorted(b.get("sponsors") or [], key=lambda s: int(s.get("sponsor_order") or 99))
    names = list(dict.fromkeys(L.text(s.get("name")) for s in sp if s.get("name")))
    sponsor = names[0] if names else "—"
    district = 0
    if sp:
        pid = sp[0].get("people_id")
        seat = seats(session).get(pid)
        district = int(re.match(r"B:(\d+)", seat).group(1)) if seat else 0

    first_out = reported or stage >= 3
    if stage == 0:
        dsc = "In committee" if place == "committee" and comm else "Introduced"
    elif stage == 1:
        dsc = "Before the full Council"
    else:
        dsc = {3: "Passed the Council", 4: "On the Mayor's desk", 5: "Enacted" if not lawnum else "Became law", 6: "Vetoed"}[stage]
    comm_now = comm if place == "committee" and stage == 0 else None

    def dates(test, mode="last"):
        ds = sorted({d for d, k, t, e in steps if test(k, e) and d})
        return {"first": ds[0], "last": ds[-1], "all": ";".join(ds)}[mode] if ds else ""

    action_dates = [d for d, k, _, _ in steps if d]
    votes = []
    for r in calls:
        desc = L.text(r.get("desc"))
        label = "First reading" if re.match(r"First Reading", desc) else "Final reading" if re.match(r"Final Reading", desc) \
            else "Veto override" if re.search(r"override|veto", desc, re.I) else None
        if not label:
            continue  # amendments, postponements: not votes on the bill
        day = (r.get("date") or "")[:10]
        names_ = []
        for m in r.get("votes") or []:
            if m.get("vote_text") == "Yea":
                continue
            p = ppl.get(m.get("people_id")) or {}
            who = seats(session).get(m.get("people_id")) or f"{H}?{L.text(p.get('name')) or m.get('people_id')}"
            names_.append([who, "N" if m.get("vote_text") == "Nay" else "A"])
        v = [H, "F", label, day, int(r.get("yea") or 0), int(r.get("nay") or 0), sorted(names_)]
        if v not in votes:  # (LegiScan has some readings twice: B26-0164's final reading of September 17, 2025)
            votes.append(v)

    law_line = lawnum["law"] if lawnum else ""
    rec = {
        "nums": [n], "base": [n], "prev": set(),
        "title": title, "summary": title, "act": "", "lawCode": "", "law": None, "laws": [],
        "comms": sorted({f"{H} · {c}" for c in refs}), "topics": topics, "places": [],
        "narrow": P.narrow_kind(title), "shell": False,
        "commFate": "passed" if first_out else "none", "mainTopic": topics[0] if topics else "",
        "local": "local" in topics, "senDeleg": False, "asmDeleg": False,
        "budget": bool(re.search(r"\bBudget (?:Support )?Act\b|\bLocal Budget\b", title)),
        # One house: a bill that passed passed "both" (the shared code's test for stage 3 and on).
        "passedS": stage >= 3, "passedA": stage >= 3, "program": None,
        "stage": stage, "passedIn": None,
        # (No chapter: an act's law number comes after Congress's review, and the History's enactment line would name it
        # beside the Mayor's signature; "Every action" has "Became law (L26-0132)".)
        "chapter": None,
        "veto": None, "memo": "", "vetoMemo": None,
        "simText": title,
        "comm": comm_now,
        "first": min(action_dates, default=f"{session}-01-01"),
        "last": max(action_dates, default=f"{session}-01-01"),
        "cosp": max(0, len(names) - 1),
        "keyDates": [
            dates(lambda k, e: k in ("report", "first", "retained"), "first"),
            "",
            dates(lambda k, e: k == "final", "all"),
            "",
            dates(lambda k, e: k == "sent") if stage >= 4 else "",
            dates(lambda k, e: k in ("signed", "nosign", "override", "enacted")) or (dates(lambda k, e: k == "law") if stage == 5 else ""),
            dates(lambda k, e: k == "veto"),
        ],
        "votes": votes, "firstComms": [(H, first_ref, first_out)] if first_ref else [],
        "vers": [{"p": n, "sponsor": sponsor, "district": district, "cosponsors": names[1:],
                  "primes": 1, "cosp": max(0, len(names) - 1), "statusDesc": dsc, "committee": comm_now,
                  "actions": [[d, t] for d, _, t, _ in steps], "link": b.get("state_link") or b.get("url") or ""}],
        "_key": earlier_key(title),
    }
    return rec


def fmt(day):
    """"2025-03-21" -> "Mar 21, 2025" (as LIMS writes dates)."""
    y, m, d = day.split("-")
    return f"{'Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec'.split()[int(m) - 1]} {int(d):02d}, {y}"


def law_table(session):
    """The Council Period's acts and laws by bill number (data/dc/laws_<session>.json, written by laws.py)."""
    key = ("laws", session)
    if key not in _SEATS:
        _SEATS[key] = L.read_json(os.path.join(P.DATA, f"laws_{session}.json"), {}) or {}
    return _SEATS[key]


# Paragraphs of an abstract that are about the Council's handling, not the bill: referral notes ("Please see Referral Memo.
# COMMITTEE REFERRAL IS AS FOLLOWS:", "Title I – Human Services; Title II – Housing; ...", "The Chairman is referring ...").
ABSTRACT_SKIP = re.compile(r"^(?:The Chair(?:man)? is referring|This (?:bill|legislation) (?:is|was) (?:being )?(?:sequentially )?referred|"
                           r"Sequential referral|Referred sequentially|Please see (?:the )?Referral Memo|COMMITTEE REFERRAL|"
                           r"Title [IVXL]+\s*[–-]\s*[^;]+;)", re.I)
# Labelled notes the Secretary adds ("FISCAL NOTE - This bill is Subject to Appropriations."), kept after the description.
NOTE = re.compile(r"^(FISCAL NOTE|FUNDING NOTE|LEGISLATIVE NOTE|RACIAL EQUITY ANALYSIS|BUDGET NOTE)\s*[-:–]\s*", re.I)


def abstract(b):
    """The Secretary's abstract LIMS gives each bill ("As introduced, Bill 26-776 would establish ..."), LegiScan's
    `description`, as (description, notes): without the notes about referrals, and the labelled notes ("Fiscal note: ...")
    apart; ("", ...) when it only repeats the title."""
    d = (b.get("description") or "").replace("\r", "")
    if L.text(d) == L.text(b.get("title")):
        return "", ""
    main, notes = [], []
    for p in (L.text(x) for x in re.split(r"\n", d)):
        if not p or ABSTRACT_SKIP.match(p) or p == L.text(b.get("title")):
            continue
        m = NOTE.match(p)
        if m:
            notes.append(m.group(1).capitalize() + ": " + p[m.end():])
            continue
        main.append(re.sub(r"^As introduced,? Bill \d+-\d+ would\b", "As introduced, it would", p))
    return "\n".join(main), "\n".join(notes)


def earlier_key(title):
    t = re.sub(r"\b(?:Amendment )?Act of \d{4}\b", "", title)
    t = re.sub(r"[^a-z0-9 ]", "", re.sub(r"\s+", " ", t.lower())).strip()
    return t if len(t.split()) >= 4 and not re.search(r"\bbudget\b|\bclosing\b|\bdesignation\b", t) else ""


def load_session(session):
    """(records, number -> record index, fetched time, delegation)."""
    if session in _LOADED:
        return _LOADED[session]
    folder = L.folders(P.DATA)[session]
    bills = [b for b in L.bills(folder) if b.get("bill_type") == "B" and number(b.get("bill_number"))]
    ppl = L.people(folder)
    comp = companions(session, bills)
    recs, index = [], {}
    for b in sorted(bills, key=lambda b: int(number(b["bill_number"])[1:])):
        if kind_of(b):
            continue
        key = companion_key(b.get("title"))
        rec = record(session, folder, b, comp.get(key, []) if key else [], ppl)
        index[rec["nums"][0]] = len(recs)
        recs.append(rec)
    # The same bill in the Council Period before: the same title (four words or more, without "Amendment Act of 2025")
    # and the same introducer, or a title only one bill has in each period. Laws aren't linked as earlier tries.
    prev = session - 2
    if prev in sessions():
        old = [r for r in load_session(prev)[0] if r["stage"] != 5 and r.get("_key")]
        by_key = defaultdict(list)
        for r in old:
            by_key[r["_key"]].append(r)
        mine = Counter(r["_key"] for r in recs if r.get("_key"))
        for r in recs:
            there = by_key.get(r.get("_key") or "")
            if not there:
                continue
            same = [o for o in there if o["vers"][0]["sponsor"] == r["vers"][0]["sponsor"]]
            if same:
                r["prev"].add((prev, same[0]["nums"][0]))
            elif len(there) == 1 and mine[r["_key"]] == 1:
                r["prev"].add((prev, there[0]["nums"][0]))
    # "What it does": the abstract, and the long title of the act as enacted (the law library's).
    texts = {}
    for b in bills:
        n = number(b["bill_number"])
        if kind_of(b) or n not in index:
            continue
        a, notes = abstract(b)
        lx = law_table(session).get(b["bill_number"]) or {}
        long = L.text(lx.get("long"))
        if long.startswith("To "):
            long = "to " + long[3:]
        if a or long:
            body = "\n".join(x for x in (a, f"As enacted, it is an act {long}" if long else "", notes) if x)
            label = ("From the Council's abstract of the bill as introduced" + (" and the enacted act's long title" if long else "") + "."
                     if a else "From the enacted act's long title, in the Council's law library" + (", and the Council's notes on the bill" if notes else "") + ".")
            texts[n] = {"statement": body, "label": label}
    os.makedirs(P.DATA, exist_ok=True)
    json.dump(texts, open(os.path.join(P.DATA, f"texts_{session}.json"), "w"), ensure_ascii=False)
    settle(recs, folder)  # bills with no history yet: never dated in the future (states/undated.py)
    _LOADED[session] = (recs, index, L.fetched(folder, P.TIMEZONE), {"SENATE": [], "ASSEMBLY": []})
    return _LOADED[session]


def agendas(session):
    """Bills on upcoming committee meetings: LIMS lists a scheduled public hearing ("Public Hearing") and mark-up ("Committee
    Mark-up of B26-0799") in the bill's history ahead of time, dated the meeting's day (no hour), and LegiScan copies the
    lines: {"B167": [["Council Health", "2026-12-03T00:00:00", "hearing"], ...]}, today's and later meetings, with the
    committee the bill was last referred to. (LegiScan's own `calendar` is empty for the Council.) As fresh as the bill's
    full record, which legiscan.py reads within its daily allowance once the master list shows the change."""
    if session != max(sessions() or [0]):
        return {}
    today = date.today().isoformat()
    out = {}
    folder = L.folders(P.DATA)[session]
    for b in L.bills(folder):
        n = number(b.get("bill_number"))
        if b.get("bill_type") != "B" or not n or kind_of(b):
            continue
        comm = None
        for a in sorted(b.get("history") or [], key=lambda a: (a.get("date") or "")[:10]):
            d, t = (a.get("date") or "")[:10], L.text(a.get("action"))
            k, extra = decode(t)
            if k == "refer":
                comm = extra["comm"]
            elif d >= today and comm and (k == "markup" or t == "Public Hearing"):
                e = [f"{HOUSE[H]} {comm}", f"{d}T00:00:00", "markup" if k == "markup" else "hearing"]
                if e not in out.setdefault(n, []):
                    out[n].append(e)
    return out


def parties(session, recs):
    """(house, name) -> party, from LegiScan's people records (Democrats, independents; "I" counts as neither party)."""
    folder = L.folders(P.DATA).get(session)
    out = {}
    for p in (L.people(folder) if folder else {}).values():
        if p.get("party") in ("D", "R", "I") and re.match(r"SD-|HD-", p.get("district") or "") and p.get("state_id") == 51:
            out[(H, L.text(p.get("name")))] = p["party"]
    return out


def checks(session):
    """Totals to compare with LIMS's: permanent bills, acts and laws, vetoes."""
    recs = load_session(session)[0]
    c = Counter(r["stage"] for r in recs)
    law = lambda r: any(t.startswith("Became law (") for _, t in r["vers"][0]["actions"])
    review = sum(1 for r in recs if r["stage"] == 5 and not law(r))
    return {"records": len(recs), "by stage": dict(sorted(c.items())), "enacted, not yet law": review,
            "laws": sum(1 for r in recs if law(r))}


if __name__ == "__main__":
    for s in sessions():
        print(s, checks(s))
