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
    third = any("reading-3" in (a.get("classification") or []) for b in bills for a in b.get("actions") or [])
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
        steps = []
        for a in acts:
            cls = set(a.get("classification") or [])
            org = a.get("organization__name") or (a.get("organization") or {}).get("name") or ""
            steps.append(((a.get("date") or "")[:10], cls, _house(org, P), org, a.get("description") or "", a))

        def days(test):
            return sorted({s[0] for s in steps if s[0] and test(s)})

        passed = {}
        for h in ("S", P.LOWER):
            passed[h] = days(lambda s, h=h: s[2] == h and "passage" in s[1] and (not third or "reading-3" in s[1])
                             and "failure" not in s[1])
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
        elif both:
            stage = 3
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
