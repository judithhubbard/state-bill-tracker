"""Light history from Open States' bulk session files for states whose own converter reads their legislature's files, not
Open States (states/LIGHT.md, "Fourth batch"): IL, MA, MI, MN, NE, SC, TX, WA, UT, KS, MD, VA, AR. Open States' bulk
files (public domain) reach back to 2017 for most states (Illinois's to the 99th General Assembly, 2015-16), where those
states' own sources are slow (a request a bill) or gone. A state's hook (states/<st>/light.py) names its sessions; the
owner names each file in states/<st>/light_bulk.json ({"2017": "MI_2017-2018_json_<id>.zip"}: the names carry an id
listed only at open.pluralpolicy.com/data/session-json/, which needs her login).

fetch() downloads the file (one request a session, a few MB) and keeps the bills in the scratch folder; records() turns
them into light records (states/light.py's KEEP fields) from Open States' action classifications, the way a converter
would: the stage from the record's own outcome ("executive-signature", "became-law", "executive-veto", a veto override in
each house, "executive-receipt", each house's "passage", "committee-passage"). Open States marks some votes that aren't
the bill's passage as "passage" too (Arizona's Committee of the Whole "DP"), so where a session's records mark third
readings ("reading-3"), a house's passage is a "passage" line that is also a third reading. Unicameral Nebraska's
passage is "passed both" (as the District's). Constitutional amendments (Open States' "constitutional amendment", or a
joint resolution whose title proposes one) are kept and tagged "const", and stop at stage 3; other resolutions are left
out. Topics: the state's own committee names (P.TOPICS' sets, P.COMMITTEE_TOPICS), else its title words (P.TOPIC_WORDS),
as the converters do. No parties (the bulk files' sponsors carry none), no chapters unless an action names one."""
import io, json, os, re, zipfile

from states import openstates_bulk as B
from stages import STAGE_LABEL

SOURCE = "Open States bulk session files (open.pluralpolicy.com/data/session-json/, public domain)"


def names(st):
    return B.load(os.path.join(B.ROOT, "states", st, "light_bulk.json"), {}) or {}


def fetch(st, session, data):
    """The session's bulk file's bills into <data>/openstates_bills.json; False (and why) when it isn't named or readable."""
    name = names(st).get(str(session))
    if not name:
        print(f"{st} {session}: no Open States bulk file named in states/{st}/light_bulk.json", flush=True)
        return False
    try:
        z = zipfile.ZipFile(io.BytesIO(B.fetch(name)))
        bills = json.loads(z.read(next(n for n in z.namelist() if n.endswith("_bills.json"))))
    except Exception as e:
        print(f"{st} {session}: {name} unreadable ({type(e).__name__}: {e})", flush=True)
        return False
    for b in bills:
        b.pop("raw_text", None)
        b.pop("versions", None)
        b.pop("documents", None)
    B.save({"bulk": name, "bills": bills}, os.path.join(data, "openstates_bills.json"))
    print(f"{st} {session}: {len(bills)} records from {name}", flush=True)
    return True


CONST = re.compile(r"constitution", re.I)
APPROP = re.compile(r"\b(?:general appropriations?|budget|appropriations? act)\b", re.I)
CHAPTER = re.compile(r"\b(?:Chapter|Ch\.|Public Act|Act No\.?|Session Law|Acts? of \d{4}, ch(?:apter)?\.?)\s*(?:\d{2,4}-)?(\d{1,4})\b", re.I)
REFERRED = re.compile(r"(?:referred|re-?referred|assigned|committed) to (?:the )?(?:committee on |joint committee on )?(.+?)(?:\s+committee)?\s*$", re.I)


def _comm_name(c):
    c = re.sub(r"^(?:House|Senate|Joint)\s+", "", (c or "").strip())
    c = re.sub(r"^(?:Committee on|Committee for)\s+", "", c, flags=re.I)
    return re.sub(r"\s+Committee$", "", c, flags=re.I).strip(" .")


def _kept(b):
    """("bill" | "const" | None) for an Open States record."""
    kinds = set(b.get("classification") or [])
    if "constitutional amendment" in kinds:
        return "const"
    if "bill" in kinds:
        return "bill"
    if kinds & {"joint resolution", "resolution", "concurrent resolution"} and CONST.search(b.get("title") or "") and \
            re.search(r"\b(?:propos|amend)\w*", b.get("title") or "", re.I):
        return "const" if "joint resolution" in kinds or "concurrent resolution" in kinds else None
    return None


NOT_PASSAGE = re.compile(r"committee of the whole|\bC\.?O\.?W\.?\b|^\s*(?:DPA?|DP/SE|do pass)\b|reconsider|motion to", re.I)
GOV_SIGNED = re.compile(r"\b(?:approved by (?:the )?governor|governor signed|signed by (?:the )?governor)\b", re.I)
# (Maryland's laws that took effect without the governor's signature: "Enacted under Article II, Section 17(c) of the
# Maryland Constitution", 217 in 2019-20.)
GOV_NOSIGN = re.compile(r"\bbecame law\b|without (?:the )?governor'?s? signature|w/o governor|"
                        r"enacted under article ii, section 17", re.I)
GOV_LINE = re.compile(r"\bline[- ]item veto", re.I)
GOV_VETO = re.compile(r"\b(?:governor vetoed|vetoed by (?:the )?governor)\b", re.I)
GOV_SENT = re.compile(r"\b(?:to|communicated to|presented to|delivered to|sent to|transmitted to|laid before) (?:the )?governor\b", re.I)
GOV_NOT = re.compile(r"deadline|lieutenant|recommendation|override|sustain|if not signed", re.I)


def _implied(text, cls):
    """The governor's actions some states' records leave unclassified (Utah's "Became Law w/o Governor Signature",
    "Governor Line Item Veto"; Virginia's "Enrolled Bill communicated to Governor")."""
    if cls & {"executive-signature", "became-law", "executive-veto", "executive-veto-line-item", "executive-receipt"} \
            or GOV_NOT.search(text or ""):
        return set()
    for rx, c in ((GOV_LINE, "executive-veto-line-item"), (GOV_NOSIGN, "became-law"), (GOV_SIGNED, "executive-signature"),
                  (GOV_VETO, "executive-veto"), (GOV_SENT, "executive-receipt")):
        if rx.search(text or ""):
            return {c}
    return set()


def _whole(org):
    """An organization that is the whole legislature, not a house ("Utah State Legislature", "Virginia General Assembly")."""
    o = (org or "").lower()
    return bool(o) and not any(w in o for w in ("senate", "house", "delegates", "upper", "lower")) and \
        any(w in o for w in ("legislature", "general assembly", "general court"))


def _house_in(text, P):
    """The house a line's own words name ("Passed House BLOCK VOTE", "Senate/ passed 3rd reading"), or None."""
    t = text or ""
    s = re.search(r"\bSenate\b", t)
    h = re.search(r"\b(?:House|Assembly|Delegates)\b", t)
    if s and not h:
        return "S"
    if h and not s:
        return P.LOWER
    if s and h:
        return "S" if s.start() < h.start() else P.LOWER
    return None


def _house(org, P):
    org = (org or "").lower()
    if "senate" in org or org == "upper":
        return "S"
    if any(w in org for w in ("house", "assembly", "delegates", "lower")):
        return P.LOWER
    if "legislature" in org or "council" in org:
        return P.LOWER
    return None


def records(st, session, data, P):
    """(records, parties) from the bills fetch() kept."""
    d = B.load(os.path.join(data, "openstates_bills.json"), {}) or {}
    bills = d.get("bills") or []
    uni = not getattr(P, "UPPER", True) or st == "ne"
    # (Whether the session's records say when bills went to the governor: classified, or in words _implied() reads.)
    receipts = any("executive-receipt" in (a.get("classification") or []) or "executive-receipt" in _implied(a.get("description") or "", set())
                   for b in bills for a in b.get("actions") or [])
    narrow = getattr(P, "narrow_kind", None)
    table = getattr(P, "COMMITTEE_TOPICS", None) or {}
    by_comm = {}
    for k, v in (getattr(P, "TOPICS", None) or {}).items():
        for c in (v[1] if isinstance(v, (tuple, list)) and len(v) > 1 and isinstance(v[1], (set, frozenset, list)) else []):
            by_comm.setdefault(_comm_name(c).lower(), k)
    words = getattr(P, "TOPIC_WORDS", None) or {}
    recs = []
    for b in bills:
        kind = _kept(b)
        if not kind:
            continue
        num = re.sub(r"\s+", "", b.get("identifier") or "")
        if not num:
            continue
        acts = sorted(b.get("actions") or [], key=lambda a: ((a.get("date") or "")[:10], a.get("order") or 0))
        origin = "S" if (b.get("chamber") or "") == "upper" else P.LOWER
        other = P.LOWER if origin == "S" else "S"
        steps = []
        passes_seen = []  # (Utah's records name no house at all: passages go to the origin house, then the other.)
        for a in acts:
            cls = set(a.get("classification") or [])
            org = a.get("organization__name") or (a.get("organization") or {}).get("name") or ""
            text = a.get("description") or ""
            h = (P.LOWER if uni else None) if _whole(org) else _house(org, P)
            if h is None:
                # (Virginia's and Utah's records name the whole legislature: the line's own words may name the house.)
                h = _house_in(text, P)
            if h is None and "passage" in cls and not uni and not NOT_PASSAGE.search(text):
                day = (a.get("date") or "")[:10]
                if day not in passes_seen:
                    passes_seen.append(day)
                h = origin if passes_seen.index(day) == 0 else other
            cls |= _implied(text, cls)
            steps.append(((a.get("date") or "")[:10], cls, h, org, text, a))

        def days(test):
            return sorted({s[0] for s in steps if s[0] and test(s)})

        passed = {}
        for h in ("S", P.LOWER):
            # (A passage line is the house's vote on the bill unless it's the Committee of the Whole's or a "do pass"
            # recommendation, which Open States also marks "passage" (Arizona's "DP"). Third readings are on the passage
            # line in some states, on a line of their own in others (Texas, Michigan), and missing from Virginia's block
            # votes, so they decide nothing (until 2026-11-25 they did, and most passages were lost).)
            passed[h] = days(lambda s, h=h: s[2] == h and "passage" in s[1] and "failure" not in s[1]
                             and not NOT_PASSAGE.search(s[4]))
        if uni:
            both_dates = passed[P.LOWER] or passed["S"]
            passed = {"S": both_dates, P.LOWER: both_dates}
        override = {h: days(lambda s, h=h: s[2] == h and "veto-override-passage" in s[1]) for h in ("S", P.LOWER)}
        signed = days(lambda s: "executive-signature" in s[1])
        became = days(lambda s: "became-law" in s[1])
        veto = days(lambda s: "executive-veto" in s[1])
        line_item = days(lambda s: "executive-veto-line-item" in s[1])
        sent = days(lambda s: "executive-receipt" in s[1])
        reported = days(lambda s: "committee-passage" in s[1] or "committee-passage-favorable" in s[1])
        overridden = bool(veto) and (all(override[h] for h in ("S", P.LOWER)) if not uni else bool(override[P.LOWER] or override["S"]))
        both = bool(passed["S"]) and bool(passed[P.LOWER])
        one = bool(passed["S"]) or bool(passed[P.LOWER])
        if kind == "const":
            stage = 3 if both else 2 if one else 1 if reported else 0
        elif signed or became or line_item or overridden:
            stage = 5
        elif veto:
            stage = 6
        elif sent:
            stage = 4
        elif both and (not receipts or uni):
            stage = 3
        elif both:
            # (A finished session's bill past each house but never sent to the governor died between them: the second
            # house amended it and the first never agreed, or a conference failed. Washington 2017-18: 447 such, all
            # "passed both houses" until 2026-11-25. Light history is always finished sessions; where a session's
            # records carry no delivery lines at all, stage 3 stays.)
            stage = 2
            passed = {**passed, other: []}
        elif one:
            stage = 2
        elif reported:
            stage = 1
        else:
            stage = 0
        if stage >= 3 and kind != "const" and not both:
            # (A law with a passage line missing: it passed each house, whatever the record lists.)
            passed = {h: passed[h] or [] for h in passed}
        refs = []
        for s in steps:
            if "referral-committee" in s[1]:
                ent = next((e.get("name") for e in s[5].get("related_entities") or [] if e.get("entity_type") == "organization"), None)
                m = REFERRED.search(s[4]) if not ent else None
                name = _comm_name(ent or (m.group(1) if m else ""))
                if name and s[2]:
                    refs.append((s[2], name))
        topics = ["const"] if kind == "const" else []
        for _, c in refs:
            tp = table.get(c) or by_comm.get(c.lower())
            if tp and tp not in topics:
                topics.append(tp)
        if len(topics) <= (1 if kind == "const" else 0):
            text = f"{b.get('title') or ''} {' '.join(b.get('subject') or [])}"
            topics += [k for k, rx in words.items() if rx.search(text) and k not in topics]
        title = re.sub(r"\s+", " ", b.get("title") or "").strip()
        abstract = next((x.get("abstract") for x in b.get("abstracts") or [] if x.get("abstract")), "") or ""
        chapter = None
        if stage == 5:
            for s in steps:
                m = CHAPTER.search(s[4])
                if m and re.search(r"chapter|ch\.|public act|act no|session law", s[4], re.I):
                    chapter = int(m.group(1))
        sponsors = b.get("sponsors") or []
        primes = [x.get("name") for x in sponsors if x.get("primary")] or [x.get("name") for x in sponsors[:1]]
        dates = [s[0] for s in steps if s[0]]
        house_of = "S" if (b.get("chamber") or "") == "upper" else P.LOWER
        recs.append({
            "nums": [num], "title": title, "summary": re.sub(r"\s+", " ", abstract).strip(),
            # (A bill past both houses passed each one, whatever its records say: Open States' older sessions often miss a
            # house's vote line. The data check's "past both houses without both passage flags", 2026-11-25.)
            "stage": stage, "passedS": bool(passed["S"]) or stage >= 3, "passedA": bool(passed[P.LOWER]) or stage >= 3,
            "passedIn": ("Senate" if passed["S"] else getattr(P, "LOWER_NAME", "House")) if stage == 2 and not uni else None,
            "first": min(dates, default=f"{session}-01-01"), "last": max(dates, default=f"{session}-01-01"),
            "keyDates": [reported[0] if reported else "", ";".join(passed["S"]), ";".join(passed[P.LOWER]), "",
                         sent[-1] if sent and stage >= 4 and kind != "const" else "",
                         ((signed or became or override[P.LOWER] or override["S"])[-1:] or [""])[0] if stage == 5 else "",
                         veto[-1] if veto and kind != "const" else ""],
            "firstComms": [(refs[0][0], refs[0][1], stage >= 1)] if refs else [],
            "commFate": "passed" if reported else "none",
            "comms": sorted({f"{h} · {c}" for h, c in refs}), "topics": topics, "mainTopic": topics[0] if topics else "",
            "narrow": narrow(title) if narrow else None, "shell": False, "budget": bool(APPROP.search(title)),
            "ballot": False, "chapter": chapter, "local": "local" in topics, "places": [],
            "cosp": max(0, len(sponsors) - 1),
            "vers": [{"p": num, "sponsor": primes[0] if primes and primes[0] else "", "district": None,
                      "primes": max(1, len(primes)), "cosp": max(0, len(sponsors) - 1), "statusDesc": STAGE_LABEL[stage]}],
            "_house": house_of,
        })
    for r in recs:
        r.pop("_house", None)
    return recs, {}
