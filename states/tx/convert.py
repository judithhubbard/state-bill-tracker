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
Only regular-session House and Senate bills are shown, and joint resolutions (HJR/SJR) proposing constitutional
amendments: those need two-thirds of each house's members, never go to the governor ("Filed with the Secretary of
State" instead) and go to the voters (topic "const"). Other resolutions and special sessions' bills are left out.

Votes: committee votes are the histories' totals, with the House committees' members from the House Research
Organization's floor reports (states/tx/hro.py); floor votes by member from the journals (states/tx/journals.py).
"""
import glob, html, json, os, re
import xml.etree.ElementTree as ET
from collections import defaultdict
from datetime import datetime
from zoneinfo import ZoneInfo

from . import profile as P
from states.undated import settle
from states import letters as L

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
    """"HB 12.xml" -> "HB12", "HJR 4.xml" -> "HJR4"."""
    m = re.match(r"([HS]B|[HS]JR)\s*0*(\d+)", name)
    return f"{m.group(1)}{m.group(2)}" if m else None


def iso(d):
    m = re.match(r"(\d+)/(\d+)/(\d{4})", d or "")
    return f"{m.group(3)}-{int(m.group(1)):02d}-{int(m.group(2)):02d}" if m else ""


def names(s):
    return [x.strip() for x in (s or "").split("|") if x.strip()]


def bills(session):
    """Bill -> parsed history (dict), for every HB and SB file that parses, and every joint resolution proposing a
    constitutional amendment (not ones applying to Congress for a convention or ratifying a federal amendment)."""
    out = {}
    for f in glob.glob(os.path.join(folder(session), "*.xml")):
        p = num(os.path.basename(f))
        if not p:
            continue
        try:
            t = ET.parse(f).getroot()
        except ET.ParseError:
            continue  # a file cut off mid-download; the next run gets it again
        if p[1:3] == "JR" and not amendment(t.findtext("caption")):
            continue
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


def amendment(caption):
    """A joint resolution's caption that proposes a change to the Texas Constitution."""
    return bool(re.match(r"\s*Proposing (a |an )?(constitutional amendments?|amendments? to the (Texas )?Constitution)", caption or "", re.I))


def is_jr(p):
    return p[1:3] == "JR"


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
    # A joint resolution is "Adopted" (House 565/566, Senate 585/586) or "Passed" (Senate 576).
    if (house, n) in (("H", 555), ("H", 556), ("S", 576), ("S", 577), ("H", 565), ("H", 566), ("S", 585), ("S", 586)):
        return f"PASSED {HOUSE[house].upper()}"
    if house == "E" and n == 15:
        return "DELIVERED TO GOVERNOR"
    if house == "E" and n in (20, 30):  # signed, signed with line-item vetoes
        return "SIGNED"
    if house == "E" and n == 25:
        return "Filed without the governor's signature"
    if house == "E" and n == 35:
        return "VETOED"
    return desc


def stage_of(p, acts):
    """How far a bill got, 0-6, from its history's codes."""
    codes = {(h, n) for _, h, n, _, _ in acts}
    if is_jr(p):  # a constitutional amendment never goes to the governor: passing both houses is as far as it goes here
        return min(3, stage_of(p.replace("JR", "B"), [a for a in acts if a[1] != "E"]))
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
    # A concurrence later reconsidered and refused doesn't count (SB 155 of 2021: the Senate concurred, reconsidered,
    # refused, and went to a conference the House never adopted).
    seq = [(h, n) for _, h, n, _, _ in acts]
    concur = {c for c, refuse in ((("H", 701), ("H", 706)), (("S", 706), ("S", 711)))
              if c in seq and refuse not in seq[len(seq) - seq[::-1].index(c):]}
    if codes & {("H", 840), ("S", 840)} or concur or conference or (origin, 805) in codes:
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
        elif (h == "H" and n in (425, 430, 435, 465)) or (h == "S" and n in (400, 430)):  # H425: Constitutional Amendments Calendar
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


# ---- Veto messages. Every veto proclamation is text in a journal fetch.py already saves (states/tx/journals.py): a
# veto while the Legislature meets is a message read in the bill's house ("TO THE MEMBERS OF THE HOUSE OF
# REPRESENTATIVES AND SENATE ..." or "... OF THE SENATE AND HOUSE ...": "do hereby disapprove and veto House Bill No. 353
# ..."), and the Senate Journal's last day
# prints the proclamations filed after the session for Senate bills ("VETO PROCLAMATIONS ... PROCLAMATION BY THE
# GOVERNOR OF THE STATE OF TEXAS"). House bills vetoed after the session are in no journal the site reads: their
# proclamations come from the governor's scans (fetch.py's veto_letters(), OCR, vetoes/<HB705>.json). The General
# Appropriations Act's line-item proclamation (a list of items) is left out.
_VETOES = {}
_START = re.compile(r"PROCLAMATION\s+BY\s+THE\s+GOVERNOR\s+OF\s+THE\s+STATE\s+OF\s+TEXAS|TO\s+THE\s+MEMBERS\s+OF\s+THE\s+(?:HOUSE\s+OF\s+"
                    r"REPRESENTATIVES\s+AND\s+(?:THE\s+)?SENATE|SENATE\s+AND\s+(?:THE\s+)?HOUSE\s+OF\s+REPRESENTATIVES)\s+OF\s+THE\s+"
                    r"[A-Z-]+\s+TEXAS\s+LEGISLATURE")
_WHICH = re.compile(r"disapprove\s+(?:of\s+)?and\s+veto\s+(?:(House|Senate)\s+Bill(?:\s+No\.)?\s*(\d+)|([HS])\.?\s?B\.?\s*(\d+))", re.I)
_REASONS = re.compile(r"(?:due\s+to|because\s+of)\s+the\s+following\s+objections?\s*:", re.I)
_REASONS_END = re.compile(r"Since (?:the [A-Z][\w\s,-]{0,90}?by (?:its|their) adjournment|you remain gathered|the Legislature (?:has )?adjourned)|"
                          r"IN TESTIMONY WHEREOF|Respectfully submitted|I am (?:therefore )?filing these objections", re.I)
_MONTHS = "January February March April May June July August September October November December".split()


def _journal_text(path):
    raw = open(path, encoding="utf-8", errors="replace").read()
    raw = re.sub(r"(?i)</div>|<br\s*/?>|</p>", "\n", raw)
    t = html.unescape(re.sub(r"<[^>]+>", "", raw)).replace("\xa0", " ")
    return "\n".join(re.sub(r"[ \t]+", " ", x).strip() for x in t.split("\n"))


def _when(chunk):
    """The proclamation's date: "this 13th day of June, 2023", or a message's "May 24, 2023" after its signature."""
    m = re.search(r"this (\d+)(?:st|nd|rd|th)? day of ([A-Z][a-z]+),? (\d{4})", chunk)
    if m and m.group(2) in _MONTHS:
        return f"{m.group(3)}-{_MONTHS.index(m.group(2)) + 1:02d}-{int(m.group(1)):02d}"
    m = re.search(r"Austin, Texas\s*\n\s*([A-Z][a-z]+) (\d{1,2}), (\d{4})", chunk)
    if m and m.group(1) in _MONTHS:
        return f"{m.group(3)}-{_MONTHS.index(m.group(1)) + 1:02d}-{int(m.group(2)):02d}"
    return ""


def journal_vetoes(session):
    """Bill ("HB353") -> {"text": the governor's objections as paragraphs, "day"}, from the session's House and Senate
    journals."""
    if session in _VETOES:
        return _VETOES[session]
    out = {}
    base = os.path.join(P.DATA, P.code_of(session), "journals")
    for path in sorted(glob.glob(os.path.join(base, "*.HTM")) + glob.glob(os.path.join(base, "senate", "*.HTM"))):
        try:
            t = _journal_text(path)
        except OSError:
            continue
        starts = [m.start() for m in _START.finditer(t)]
        for a, b in zip(starts, starts[1:] + [len(t)]):
            chunk = t[a:b]
            which = _WHICH.search(chunk[:1500])
            why = _REASONS.search(chunk[:2500])
            if not which or not why or re.search(r"General Appropriations", chunk[:600]):
                continue
            p = (f"{which.group(1)[0]}B{int(which.group(2))}" if which.group(1)
                 else f"{which.group(3).upper()}B{int(which.group(4))}")
            stop = _REASONS_END.search(chunk, why.end())
            body = chunk[why.end():stop.start() if stop else why.end() + 6000]
            paras = [re.sub(r"\s+", " ", x).strip() for x in body.split("\n")]
            paras = [x for x in paras if x and not re.fullmatch(r"\d+|S\s*\d+|Page \d+", x)]
            if paras and p not in out:
                out[p] = {"text": paras, "day": _when(chunk)}
    _VETOES[session] = out
    return out


def veto_message(session, p, stage, day):
    """The governor's veto proclamation for a vetoed bill -> its vetoMemo ({year, signer, text}, with "ocr" and "url"
    when read from a scan), or None: the journals' text first, else the OCR of the governor's scan (vetoes/<p>.json)."""
    if stage != 6:
        return None
    got = journal_vetoes(session).get(p)
    scan = None
    if not got:
        try:
            with open(os.path.join(P.DATA, P.code_of(session), "vetoes", f"{p}.json"), encoding="utf-8") as f:
                scan = json.load(f)
        except (OSError, ValueError):
            return None
        if not scan.get("raw"):
            return None
        # A proclamation: its reasons run from "... because of the following objections:" to "Since the ... Legislature,
        # by its adjournment, has prevented the return of this bill" (the OCR text, as one block, is cut there).
        raw = scan["raw"]
        why = _REASONS.search(raw)
        if not why:
            return None
        stop = _REASONS_END.search(raw, why.end())
        body = raw[why.end():stop.start() if stop else why.end() + 6000]
        # (A hyphen at a line's end is the word's own: the proclamations are typed, "trial-" / "related".)
        body = re.sub(r"(\w)-\n(?=[a-z])", r"\1-", body)
        got = {"text": L.ocr_letter("Dear X,\n\n" + body.strip(), P.governor_on(day or f"{session}-06-30")),
               "day": _when(raw)}
    day = got["day"] or day or f"{session}-06-30"
    text_ = L.cut(got["text"])
    if len(text_) < 40:
        return None
    m = {"year": int(day[:4]), "signer": P.governor_on(day), "text": text_}
    if scan:
        m.update(ocr=bool(scan.get("ocr")), url=scan["url"])
    return m


HRO_STATS = {}  # session -> House committee votes, those named from the floor reports, analyses matching no vote


def same_comm(a, b):
    """"Ways & Means" = "Ways and Means"; "Licensing & Administrative Procedures" = "Licensing and Administrative ..."."""
    k = lambda s: _plain(re.sub(r"&", " and ", s or "")).replace(" and ", " ")
    return k(a) == k(b)


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
    from states.tx import hro
    hro_votes = hro.analyses(session)
    HRO_STATS[session] = {"house": 0, "named": 0, "unmatched": 0}

    def member(name):
        # "Garcia, Linda" (a member's name as the House writes it) -> "L. Garcia".
        m = re.match(r"(.+?),\s*([A-Z])[a-z]+$", name)
        return floor_vote(f"{m.group(2)}. {m.group(1)}" if m else name, members) or f"H?{name}"
    stamp = max((os.path.getmtime(f) for f in glob.glob(os.path.join(folder(session), "*.xml"))), default=0)
    fetched = datetime.fromtimestamp(stamp, ZoneInfo(P.TIMEZONE)).strftime("%Y-%m-%d %H:%M")

    def named(h, n):
        return full.get((h, n), n if "," not in n else " ".join(reversed([x.strip() for x in n.split(",", 1)])))

    recs, index = [], {}
    for p, b in sorted(data.items(), key=lambda kv: (re.match(r"\D+", kv[0]).group(), int(re.search(r"\d+", kv[0]).group()))):
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
        if is_jr(p):  # "Proposing a constitutional amendment to ..." -> "Constitutional amendment to ..."
            rest = re.sub(r"^Proposing (a |an )?(constitutional amendments?|amendments? to the (Texas )?Constitution)\s*", "",
                          b["caption"], flags=re.I).rstrip(".").strip()
            title = f"Constitutional amendment {rest}." if rest else "Constitutional amendment."

        topics = [k for k, (label, cset, sre, _) in P.TOPICS.items()
                  if comm_names & cset or any(sre.search(s) for s in b["subjects"]) or
                  (k in P.TOPIC_WORDS and P.TOPIC_WORDS[k].search(title))]
        if is_jr(p):
            topics = ["const"] + [k for k in topics if k != "const"]
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

        # Committee votes: the date the committee reported the bill, or the last time it took it up. The histories give
        # totals; a House committee's members come from the House Research Organization's analysis of the bill
        # (states/tx/hro.py), when its committee and tally are the history's (never a second vote).
        votes = []
        own_hro = list(hro_votes.get(p, []))
        for h, cname, status, yes, no, pnv, absent in b["committees"]:
            if yes or no:
                when = dates(lambda hh, t, n: hh == h and (t == "REPORTED" or n in (249, 280)))
                listed = []
                if h == "H":
                    hit = next((a for a in own_hro if a["ayes"] == yes and a["nays"] == no and same_comm(a["committee"], cname)), None)
                    if hit:
                        own_hro.remove(hit)
                        listed = [[member(x), code] for code, k in (("N", "nays"), ("B", "pnv"), ("A", "absent"))
                                  for x in hit["names"][k]]
                        HRO_STATS[session]["named"] += 1
                    HRO_STATS[session]["house"] += 1
                votes.append([h, "C", cname, when or dates(lambda hh, t, n: hh == h), yes, no, listed])
        HRO_STATS[session]["unmatched"] += len(own_hro)
        # House floor votes (the House Journal's record votes): final passage, agreeing to the Senate's changes, and
        # adopting a conference report; second reading's vote only when third reading had none.
        floor, prev = [], None
        for d, h, n, desc, comment in acts:
            rv = re.search(r"RV#(\d+)", comment) if (h, n) == ("H", 630) else None
            if rv and rv.group(1) in house_votes and prev in (535, 536, 555, 556, 565, 566, 701, 750):
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
            "veto": None, "memo": "",
            "vetoMemo": veto_message(session, p, stage, dates(lambda h, t, n: t == "VETOED")[:10]),
            "comm": committee if stage == 0 and place == "committee" else None,
            "first": min(action_dates, default=f"{session}-01-01"),
            "last": max(action_dates, default=f"{session}-01-01"),
            "cosp": vers["cosp"],
            # Key dates: on the floor, passed the Senate, passed the House, (New York's return to committee in a new
            # year: none here), sent to the governor, signed, vetoed.
            "keyDates": [
                dates(lambda h, t, n: h == origin and n in (425, 430, 435, 465, 400) and h == "H" or (h == origin == "S" and t == "REPORTED"), "first"),
                dates(lambda h, t, n: t == "PASSED SENATE", "all"),
                dates(lambda h, t, n: t == "PASSED HOUSE", "all"),
                "",
                dates(lambda h, t, n: t == "DELIVERED TO GOVERNOR"),
                dates(lambda h, t, n: t == "SIGNED" or (h, n) == ("E", 25)),
                dates(lambda h, t, n: t == "VETOED"),
            ],
            "votes": votes, "firstComms": first_comms, "vers": [vers],
        }
        index[p] = len(recs)
        recs.append(rec)
    settle(recs, folder(session))  # bills with no history yet: never dated in the future (states/undated.py)
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
