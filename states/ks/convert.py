"""Kansas's bills (downloaded by states/ks/fetch.py from the Legislature's API, kslegislature.gov/api/v1/) in the shape
build_data.py reads. House and Senate bills of each two-year biennium (2025-26 is "b2025_26"), one record each, plus the
concurrent resolutions proposing amendments to the Kansas Constitution (their long title begins "A PROPOSITION to
amend"), tagged "const". Other concurrent resolutions (applications to Congress, joint rules) and each house's own
resolutions are left out.

Each history entry has an action code ("fa_fabc_340"), a house, the journal day (session_date), the time it was entered
(occurred_datetime) and plain wording ("Final Action - Passed as amended"). The wording decides: a few codes mean
different things on different lines (fa_fabc_925 is "Adopted as amended by required 2/3 Majority", efa_fabc_925
"Substitute passed"). Some lines carry only their code: fa_fabc_912 (the Senate's motion to advance a bill to emergency
final action, which fa_om_912 words in the House), ccal_rcc_820/850 and ccal_faccl_850 (days on the consent calendar),
ref_rbc_236/237 and cow_jcow_292 (left out), and five "#ACTION_CODES_UNKNOWN#" lines (on SB 28 of 2024, HB 2106, SB 125
and SB 367 of 2025-26, and House resolutions), whose text is only that code: procedural entries next to the Committee of
the Whole's work or a line-item override, left out. Lines with empty wording (misc_bs_100) are motions; when a roll call
belongs to one, its motion names it ("Line Item Veto Override 37(a) 74(Q)", "Motion to withdraw SB 355 from Committee
..."), else they're left out.

How a bill moves: introduced and referred to a committee ("Referred to Senate Committee on Judiciary"); the committee
reports it ("Committee Report recommending bill be passed as amended by", which doesn't name the committee: it's the one
the bill is in), and it goes on General Orders, where the whole house, sitting as the Committee of the Whole, debates and
amends it and recommends it "be passed"; the passage is the next day's roll call, "Final Action - Passed", or the same
day's when the house first votes to take it up at once, "Emergency Final Action - Passed". A committee can instead put
an uncontroversial bill on the Consent Calendar, where it passes after three days without debate ("Consent Calendar
Passed") unless a member objects ("Withdrawn from Consent Calendar and placed on General Orders"). Bills are often sent
back from the calendar to a committee ("Withdrawn from Calendar; Referred to House Committee on Appropriations") or
withdrawn from one committee and sent to another. A committee can replace a bill with a substitute ("Senate Substitute
for HB 2004"), which keeps its number. The second house passing a bill "as amended" or as a substitute needs the first
house's agreement: "Concurred with amendments" (or "... in conference"), or "Nonconcurred with amendments; Conference
Committee requested", and then a conference committee's report, which both houses adopt ("Conference Committee Report
was adopted"; "agree to disagree" and "not adopted" start a new conference). Then "Enrolled and presented to Governor on
<day>" (a constitutional amendment goes to the Secretary of State instead): "Approved by Governor on <day>", "Approved by
Governor except line item veto of 35a, 40d, ..." (appropriations), "Will become law without Governor's signature"
(after 10 days), "Vetoed by Governor; Returned to on <day>"; "Motion to override veto prevailed" in each house (both
needed: two-thirds of the members), "... failed; Veto sustained", "No motion to reconsider vetoed bill; Veto sustained";
line items are overridden one group at a time ("Motion to override line item veto prevailed; Line item veto 37(a)
overridden": the rest stand). At the end of the biennium, each unfinished bill gets a last line: "Died in Committee",
"Died on Calendar", "Died in Conference", dated the last day.

Floor votes are roll calls (committees don't take them): votes.json lists every one with its tally and the journal line
it belongs to (action code and time), and votes/<file>.json holds the members' votes, by legislator id (kpid), for those
downloaded so far; the rest show their tallies.

"What it does" is the Kansas Legislative Research Department's supplemental note on the bill's latest version
(notes/<bill>.json): its Brief, then its Background, as two parts.
"""
import json, os, re
from datetime import date, datetime
from zoneinfo import ZoneInfo

from states.ks import profile as P

HOUSE = {"S": "Senate", "H": "House"}
CH = {"house": "H", "senate": "S"}
OTHER = {"S": "H", "H": "S"}
KEPT = re.compile(r"^(HB|SB|HCR|SCR)(\d+)$")
_CACHE = {}
_PARTIES = {}
MONTHS = ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november",
          "december"]


def folder(session):
    return os.path.join(P.DATA, str(session))


def sessions():
    out = []
    for f in sorted(os.listdir(P.DATA)) if os.path.isdir(P.DATA) else []:
        if re.fullmatch(r"\d{4}", f) and os.path.exists(os.path.join(P.DATA, f, "bill_status.json")):
            out.append(int(f))
    return out


def load(session, name, default=None):
    """One of a biennium's files (bill_status, votes, legislators, committees ...), or a file under it ("notes/HB2004",
    "votes/year2_house_day045_0273_SB334")."""
    key = (session, name)
    if key not in _CACHE:
        try:
            _CACHE[key] = json.load(open(os.path.join(folder(session), f"{name}.json"), encoding="utf-8"))
        except (OSError, ValueError):
            _CACHE[key] = default
    return _CACHE[key]


def member_page(kpid):
    key = ("members", kpid)
    if key not in _CACHE:
        try:
            _CACHE[key] = json.load(open(os.path.join(P.DATA, "members", f"{kpid}.json"), encoding="utf-8"))
        except (OSError, ValueError):
            _CACHE[key] = None
    return _CACHE[key]


def text(x):
    return re.sub(r"\s+", " ", str(x or "").replace("\xa0", " ")).strip()


def written_day(t):
    """"Approved by Governor on Thursday, April 10, 2025" -> "2025-04-10" (the date in the wording), else ""."""
    m = re.search(r"\b(" + "|".join(MONTHS) + r")\s+(\d{1,2}),\s+(\d{4})", t, re.I)
    if not m:
        return ""
    try:
        return date(int(m.group(3)), MONTHS.index(m.group(1).lower()) + 1, int(m.group(2))).isoformat()
    except ValueError:
        return ""


def fmt(iso):
    y, m, d = iso.split("-")
    return f"{MONTHS[int(m) - 1].capitalize()} {int(d)}, {y}"


# ---- members --------------------------------------------------------------------------------------------------------

def norm(w):
    return re.sub(r"[^a-z]", "", (w or "").lower())


def members(session):
    """kpid -> {h, district, name, last, party ("D"/"R"), active}: everyone the API lists for the biennium (it lists
    past members too, as "Inactive")."""
    key = (session, "_members")
    if key not in _CACHE:
        out = {}
        for m in (load(session, "legislators", {}) or {}).get("legislators", []):
            h = CH.get((m.get("chamber") or "").lower())
            if not h or not m.get("kpid"):
                continue
            party = {"Republican": "R", "Democrat": "D", "Democratic": "D"}.get(m.get("party") or "", "")
            name = text(m.get("full_name")) or f"{text(m.get('first_name'))} {text(m.get('last_name'))}"
            out[m["kpid"]] = {"h": h, "district": text(m.get("district")), "name": name, "last": text(m.get("last_name")),
                              "party": party, "active": m.get("status") == "Active",
                              # a member who left during the biennium (their record was last changed after it began)
                              "recent": (m.get("rev_date") or "") >= f"{session}-01-01"}
        _CACHE[key] = out
    return _CACHE[key]


def roll_files(session):
    """apn -> the roll call's member lists, for those downloaded."""
    key = (session, "_rolls")
    if key not in _CACHE:
        out = {}
        d = os.path.join(folder(session), "votes")
        for f in sorted(os.listdir(d)) if os.path.isdir(d) else []:
            try:
                r = json.load(open(os.path.join(d, f), encoding="utf-8"))
            except (OSError, ValueError):
                continue
            if r.get("apn") and r.get("members"):
                out[r["apn"]] = r
        _CACHE[key] = out
    return _CACHE[key]


def seats(session):
    """kpid -> seat ("S:12", "H:71"): each active member of the biennium, and a member who left whose seat no active
    member holds (a vacancy) and who voted in the biennium's roll calls."""
    key = (session, "_seats")
    if key not in _CACHE:
        ms = members(session)
        out = {k: f"{m['h']}:{int(m['district'])}" for k, m in ms.items() if m["active"] and m["district"].isdigit()}
        held = set(out.values())
        voted = {}
        for r in roll_files(session).values():
            for group in (r.get("members") or {}).values():
                for x in group or []:
                    voted[x.get("kpid")] = max(voted.get(x.get("kpid"), ""), r.get("occurred") or "")
        for k, when in sorted(voted.items(), key=lambda e: e[1], reverse=True):
            m = ms.get(k)
            if m and not m["active"] and m["district"].isdigit():
                sid = f"{m['h']}:{int(m['district'])}"
                if sid not in held:
                    out[k] = sid
                    held.add(sid)
        _CACHE[key] = out
    return _CACHE[key]


def sponsored(session):
    """Bill -> kpids of the members whose own pages list it (the current biennium's active members), to tell apart two
    members with one surname ("Representative Carpenter": Blake or Will)."""
    key = (session, "_sponsored")
    if key not in _CACHE:
        out = {}
        bien = f"b{session}_{str(session + 1)[2:]}"
        for k, m in members(session).items():
            pg = member_page(k) if m["active"] else None
            if not pg or pg.get("biennium") != bien:
                continue
            for b in (pg.get("sponsored_bills") or []) + (pg.get("sponsored_resolutions") or []):
                out.setdefault(b.get("bill_no"), set()).add(k)
        _CACHE[key] = out
    return _CACHE[key]


def sponsor(session, s, bill):
    """"Senator Titus" -> ("S", "Kenny Titus", kpid, "R"); "House Committee on Taxation" -> (None, "House Committee on
    Taxation", None, ""). A surname two members of the biennium share stays a surname unless the member's page lists the
    bill (with their party when they share it)."""
    s = text(s)
    m = re.match(r"(Senator|Representative) (.+)$", s)
    if not m:
        return None, re.sub(r"^(House|Senate) Committee on (House|Senate) ", r"\1 ", s), None, ""
    h = "S" if m.group(1) == "Senator" else "H"
    last = norm(m.group(2))
    ms = members(session)
    cands = [k for k, x in ms.items() if x["h"] == h and norm(x["last"]) == last and x["active"]]
    if len(cands) > 1:
        cands = [k for k in cands if k in sponsored(session).get(bill, set())] or cands
    if not cands:
        cands = [k for k, x in ms.items() if x["h"] == h and norm(x["last"]) == last and (x["recent"] or k in seats(session))]
    if len(cands) == 1:
        return h, ms[cands[0]]["name"], cands[0], ms[cands[0]]["party"]
    ps = {ms[k]["party"] for k in cands}
    return h, text(m.group(2)), None, ps.pop() if len(ps) == 1 else ""


# ---- titles -----------------------------------------------------------------------------------------------------------

SUB_PREFIX = re.compile(r"^(?:(?:House|Senate) )?Substitute for [HS]B \d+ by (?:the )?(?:(?:House|Senate) )?Committee on .+? - ?\.?\s*")


def is_amendment(b):
    return bool(re.match(r"\s*A PROPOSITION to amend", b.get("LONGTITLE") or "", re.I))


def kept(b):
    m = KEPT.match(b.get("BILLNO") or "")
    return bool(m) and (m.group(1) in ("HB", "SB") or is_amendment(b))


def short_title(b):
    t = text(SUB_PREFIX.sub("", text(b.get("SHORTTITLE"))))
    t = t.rstrip(".").strip() or text(b.get("NAME"))
    return t[:1].upper() + t[1:]


def long_summary(b):
    """The official title without "AN ACT" and the list of sections it amends and repeals: "Concerning taxation;
    relating to ...". """
    t = text(b.get("LONGTITLE"))
    t = re.sub(r"^(AN ACT|A PROPOSITION to amend)\s+", lambda m: "" if m.group(1) == "AN ACT" else "Proposing to amend ", t)
    t = re.sub(r";?\s*(and )?(amending|repealing)\b.*$", "", t, flags=re.I | re.S)
    t = re.sub(r"\s*;\s*$", "", t).strip()
    if not t:
        return ""
    t = t[:1].upper() + t[1:]
    return t if t.endswith(".") else t + "."


# ---- the history ----------------------------------------------------------------------------------------------------

COMM_IN = re.compile(r"(?:(House|Senate|Joint) )?Committee on (.+?)(?=;|,? Rereferred|,? Referred|$)", re.I)


def committee_name(c):
    c = text(c)
    c = re.sub(r"^(?:House |Senate )?Committee on ", "", c)
    c = re.sub(r"^(?:Senate )?Senate Select Committee on Veterans Affairs$", "Select Committee on Veterans Affairs", c)
    return c


def target(t):
    """The committee a line sends the bill to: the last "Committee on X" it names."""
    found = COMM_IN.findall(t)
    return committee_name(found[-1][1]) if found else None


PASS = re.compile(r"^(Emergency )?Final Action - (Substitute )?(passed|adopted)( as amended)?( by required 2/3 majority)?$", re.I)
FAIL = re.compile(r"^(Emergency )?Final Action - Not (passed|adopted)( by required 2/3 majority)?$", re.I)
COW_OK = re.compile(r"^Committee of the Whole - (?:Substitute (?:bill|concurrent resolution) )?Be (?:passed|adopted)(?: as (?:further )?amended)?$", re.I)
REPORT = re.compile(r"^Committee Report recommending (bill|resolution|substitute bill|substitute resolution) be (.*?) by$")


def bill_votes(session):
    """Bill -> its roll calls on the bill itself (final action, consent calendar, concurrence, conference reports, veto
    overrides; not amendments, motions or appointments): [(journal day, house, label, tally, apn, action code, time)]."""
    key = (session, "_billvotes")
    if key not in _CACHE:
        out = {}
        lines = {}
        for b in (load(session, "bill_status", {}) or {}).get("bills") or []:
            for x in b.get("HISTORY") or []:
                k = (x.get("action_code"), CH.get((x.get("chamber") or "").lower()), (x.get("occurred_datetime") or "")[:19])
                lines.setdefault(k, set()).add(b["BILLNO"])
                lines.setdefault(k[:2] + (k[2][:16],), set()).add(b["BILLNO"])
        for apn, v in ((load(session, "votes", {}) or {}).get("votes") or {}).items():
            je = v.get("journal_element") or {}
            code, lab = je.get("action_code") or "", text(je.get("action_label")).rstrip(";")
            motion = text(v.get("motion"))
            if code == "misc_bs_100" and re.match(r"Line Items? (?:Veto Override|on|SB|HB)", motion):
                label = "Line-item veto override"
            elif re.match(r"(Emergency )?Final Action - (?!Appointment)", lab):
                label = "Emergency final action" if lab.startswith("Emergency") else "Final action"
            elif code in ("ccal_faccl_900", "ccal_faccl_850") or lab.startswith("Consent Calendar"):
                label = "Consent calendar"
            elif code.startswith("cur_con_"):
                label = "Concurrence"
            elif code in ("ccac_om_832", "ccac_ccr_833", "ccac_ccr_860", "ccac_ccr_863", "ccac_ccr_867"):
                label = "Conference report"
            elif code in ("gov_avm_885", "gov_avm_336"):
                label = "Veto override"
            elif code in ("gov_avm_887", "gov_avm_349"):
                label = "Line-item veto override"
            else:
                continue
            h = CH.get((je.get("chamber") or v.get("chamber") or "").lower())
            when = (je.get("occurred") or v.get("occurred") or "")[:19]
            # The roll call belongs to the bill whose history has its line (the same action, house and minute): a roll
            # call's own bill number is sometimes wrong or missing (two 2026 Senate line-item override votes say HB 2315,
            # a bill that never left committee; HB 2551's House vote of March 14, 2024 has none).
            # (Several bills' final actions can share a minute: the second decides, then the roll call's own number.)
            exact, near = lines.get((code, h, when[:19]), set()), lines.get((code, h, when[:16]), set())
            pick = exact if len(exact) == 1 else (exact or near)
            bill = next(iter(pick)) if len(pick) == 1 else (v.get("bill_no") if v.get("bill_no") in pick else None)
            if bill:
                out.setdefault(bill, []).append((when[:10], h, label, v.get("tally") or {}, apn, code, when))
        _CACHE[key] = out
    return _CACHE[key]


def motions(session):
    """(bill, house, time to the minute) -> the motion of a roll call on an unworded line (misc_bs_100)."""
    key = (session, "_motions")
    if key not in _CACHE:
        out = {}
        for v in ((load(session, "votes", {}) or {}).get("votes") or {}).values():
            je = v.get("journal_element") or {}
            if je.get("action_code") == "misc_bs_100" and text(v.get("motion")):
                out[(v.get("bill_no"), CH.get((je.get("chamber") or "").lower()), (je.get("occurred") or "")[:16])] = text(v.get("motion"))
        _CACHE[key] = out
    return _CACHE[key]


def line_day(x, read):
    t, code = text(x.get("status")), x.get("action_code") or ""
    occ = (x.get("occurred_datetime") or "")[:10]
    sd = (x.get("session_date") or "")[:10]
    if code == "misc_he_200":  # the hearing's day once it's past, else the day it was scheduled
        return sd if sd and sd <= read else occ or sd
    if code == "gov_mg_100":  # "Law effective July 1, 2023": entered when the governor signed
        return occ or sd
    w = written_day(t)
    if w:
        return w
    if code in ("gov_mg_151",):
        return occ or sd
    return sd or occ


def load_session(session):
    """Read one biennium's bills: (records, bill number -> record index, fetched time, delegation)."""
    raw = load(session, "bill_status", {}) or {}
    read = raw.get("read") or date.today().isoformat()
    path = os.path.join(folder(session), "bill_status.json")
    fetched = datetime.fromtimestamp(os.path.getmtime(path), ZoneInfo(P.TIMEZONE)).strftime("%Y-%m-%d %H:%M") if os.path.exists(path) else ""
    parties = _PARTIES.setdefault(session, {})
    recs, index, texts = [], {}, {}
    bills = [b for b in raw.get("bills") or [] if kept(b)]
    bills.sort(key=lambda b: (b["BILLNO"][0] != "H", "CR" in b["BILLNO"], int(re.sub(r"\D", "", b["BILLNO"]))))
    for b in bills:
        rec, what = record(session, b, read, parties)
        index[b["BILLNO"]] = len(recs)
        recs.append(rec)
        if what:
            texts[b["BILLNO"]] = {"statement": what[0], "label": what[1]}
    json.dump(texts, open(os.path.join(P.DATA, f"texts_{session}.json"), "w"), ensure_ascii=False)
    return recs, index, fetched, {"SENATE": [], "ASSEMBLY": []}


def record(session, b, read, parties):
    p = b["BILLNO"]
    origin = "S" if p[0] == "S" else "H"
    other = OTHER[origin]
    amendment = is_amendment(b)
    hist = sorted(b.get("HISTORY") or [], key=lambda x: x.get("occurred_datetime") or "")
    hist = sorted(hist, key=lambda x: line_day(x, read))  # by day, keeping the order entered within a day
    mot = motions(session)

    steps = []  # (date, house or "G", wording, kind)
    passed, failed = {}, set()
    amended_by = None
    conf = set()
    both = False
    place, where_h, comm, first_ref, refs = "committee", origin, None, None, []
    reported = recalled = False
    enrolled = to_sos = signed = vetoed = item = no_sign = killed = False
    overrides, sustained = set(), False
    last_decisive = {}
    topic_comms = set()  # the committees that reported it, and each house's last one: the ones its topics come from

    def add(d, h, w, k):
        if steps and steps[-1][1:] == (h, w, k) and k in ("routine", "consent", "amend"):
            return  # the same step twice in a row (days on the consent calendar, amendments)
        steps.append((d, h, w, k))

    for x in hist:
        d = line_day(x, read)
        t = text(x.get("status"))
        code = x.get("action_code") or ""
        h = CH.get((x.get("chamber") or "").lower(), origin)
        H = HOUSE[h]
        if code in ("#ACTION_CODES_UNKNOWN#", "ref_rbc_236", "ref_rbc_237", "cow_jcow_292") or t == "#ACTION_CODES_UNKNOWN#":
            continue
        if code == "intro-iopbc_158":
            t = "Received and Introduced"
        if code == "fa_fabc_912" and t == code:
            add(d, h, f"The {H} voted to take it up at once (emergency final action)", "routine")
            continue
        if code in ("ccal_rcc_820", "ccal_rcc_850", "ccal_faccl_850") and t == code:
            add(d, h, f"On the {H} consent calendar", "consent")
            continue
        if not t or t == code:
            m = mot.get((p, h, (x.get("occurred_datetime") or "")[:16]))
            if m:
                add(d, h, f"{H} roll call: {m}", "other")
            continue

        if t.startswith("Prefiled for Introduction"):
            add(d, h, "Prefiled", "intro")
            continue
        if t in ("Introduced", "Received and Introduced"):
            add(d, h, "Introduced" if h == origin else f"Received in the {H}", "intro")
            where_h, place = h, "committee"
            continue
        if t == "Adopted without roll call":
            continue  # (resolutions only)
        if code == "misc_he_200" or t.startswith("Hearing:"):
            what = re.sub(r"^Hearing:\s*", "", t).replace(" — ", ", ")
            add(d, h, f"Hearing{'' if d >= (x.get('session_date') or '')[:10] else ' scheduled'}: {what}", "hearing")
            continue
        if t in ("Referred to Committee of the Whole",) or re.match(r"Withdrawn from and (?:re-)?referred to Committee of the Whole", t):
            place, where_h, recalled = "floor", h, True
            add(d, h, f"Taken out of committee and placed on the {H} calendar (General Orders)" if t.startswith("Withdrawn") else f"Sent to the {H} floor (General Orders) without a committee report", "recall")
            continue
        if re.match(r"(Referred to (?:House|Senate|Joint) Committee on|Withdrawn from (?:Calendar|(?:House|Senate) Committee on)|"
                    r"Ruled materially changed and referred to|Motion to refer bill to|Committee of the Whole - Referred to)", t) \
                and not t.endswith("not adopted"):
            c = target(t)
            if not c:
                add(d, h, t, "other")
                continue
            back = t.startswith("Withdrawn from Calendar")
            same = t.startswith("Withdrawn from") and not back and comm == c and place == "committee"
            if same:
                add(d, h, f"Withdrawn from the {c} Committee and sent back to it", "routine")
                continue
            comm, place, where_h = c, "committee", h
            refs.append((h, c))
            if first_ref is None and h == origin:
                first_ref = c
            add(d, h, f"REFERRED TO {c.upper()}" if not back else f"RECOMMITTED TO {c.upper()}", "ref")
            continue
        if t == "Referred separately to":
            continue
        m = REPORT.match(t)
        if m:
            what, how = m.group(1), m.group(2)
            reported = True
            if comm:
                topic_comms.add(comm)
            place, where_h = "floor", h
            add(d, h, "REPORTED", "reported")
            c = f"The {comm} Committee" if comm else "The committee"
            if "Consent Calendar" in how:
                add(d, h, f"{c} recommended it be passed and placed it on the consent calendar", "report")
            elif what.startswith("substitute"):
                add(d, h, f"{c} recommended a substitute {'bill' if 'bill' in what else 'resolution'} (it keeps the number)", "report")
            else:
                add(d, h, f"{c} recommended it be {how}", "report")
            continue
        if t == "Withdrawn from Consent Calendar and placed on General Orders":
            place = "floor"
            add(d, h, "Taken off the consent calendar (a member objected) and placed on General Orders for debate", "other")
            continue
        if t.startswith("Committee of the Whole - "):
            rest = t[len("Committee of the Whole - "):]
            if COW_OK.match(t):
                place, where_h = "floor", h
                add(d, h, f"The whole {H} (Committee of the Whole) recommended it be {re.sub(r'^(?:Substitute (?:bill|concurrent resolution) )?Be ', '', rest, flags=re.I)}", "cow")
            elif rest.startswith("Passed over"):
                add(d, h, "Passed over on General Orders (it keeps its place on the calendar)", "routine")
            elif rest.startswith("Amendment by was adopted"):
                add(d, h, f"Amended on the {H} floor", "amend")
            elif rest == "Motion to recommend favorably for passage failed":
                add(d, h, f"The whole {H} (Committee of the Whole) voted down a motion to recommend it", "other")
            elif rest.startswith("Motion by to rerefer to"):
                c = target(rest)
                add(d, h, f"A motion to send it back to the {c} Committee" if c else "A motion to send it back to committee", "other")
            elif re.match(r"Motion to re?refer to committee failed", rest):
                add(d, h, "A motion to send it back to committee failed", "other")
            continue  # (debate, committee reports adopted, amendments offered or rejected, rulings)
        if re.search(r"raised a question of germaneness|challenged the amendment under the Pay-Go", t):
            continue
        if t == "Motion to advance to Emergency Final Action adopted":
            add(d, h, f"The {H} voted to take it up at once (emergency final action)", "routine")
            continue
        if t == "Motion to advance to Emergency Final Action failed":
            add(d, h, f"A motion to take it up at once (emergency final action) failed in the {H}", "other")
            continue
        m = PASS.match(t)
        if m or t in ("Consent Calendar Passed", "Consent Calendar Adopted"):
            changed = bool(m and (m.group(2) or m.group(4)))
            place, where_h = "floor", h
            passed[h] = len(steps)
            failed.discard(h)
            last_decisive[h] = "pass"
            add(d, h, f"PASSED {H.upper()}", "pass")
            if m and m.group(5):
                add(d, h, f"Adopted by two-thirds of the {H}'s members", "routine")
            if passed.get(OTHER[h]) is not None and h != origin:
                if changed:
                    amended_by = h
                    place, where_h = "desk", OTHER[h]
                    add(d, h, f"Sent back to the {HOUSE[OTHER[h]]} with {'a substitute' if m and m.group(2) else 'amendments'}", "back")
                else:
                    both = True
                    add(d, h, "Passed both houses in the same form", "both")
            elif h == origin:
                place, where_h, comm = "committee", OTHER[h], None
            continue
        m = FAIL.match(t)
        if m:
            failed.add(h)
            last_decisive[h] = "fail"
            add(d, h, f"Failed in the {H}" + (" (it needed two-thirds of the members)" if m.group(3) else ""), "fail")
            continue
        if t == "Motion to Reconsider Adopted":
            k = last_decisive.pop(h, None)
            if k == "fail":
                failed.discard(h)
            elif k == "pass":
                passed.pop(h, None)
            add(d, h, f"The {H} voted to reconsider its last vote", "rescind")
            continue
        if t == "Motion to Reconsider Failed":
            add(d, h, f"A motion to reconsider failed in the {H}", "other")
            continue
        if t in ("Concurred with amendments", "Concurred with amendments in conference"):
            both = True
            passed[h] = len(steps)
            amended_by = None
            add(d, h, f"The {H} agreed to the {HOUSE[OTHER[h]]}'s changes", "concur")
            add(d, h, "Passed both houses in the same form", "both")
            continue
        if t.startswith("Nonconcurred with amendments"):
            add(d, h, f"The {H} refused to agree to the {HOUSE[OTHER[h]]}'s changes and asked for a conference committee", "nonconcur")
            continue
        if t == "Motion to concur with amendments failed":
            add(d, h, f"A motion to agree to the {HOUSE[OTHER[h]]}'s changes failed in the {H}", "other")
            continue
        if t == "Motion to nonconcur with amendments and appoint conferees failed":
            add(d, h, f"A motion to refuse the {HOUSE[OTHER[h]]}'s changes and go to conference failed in the {H}", "other")
            continue
        if t.startswith("Motion to accede adopted"):
            conf = set()
            add(d, h, f"The {H} agreed to a conference committee", "conf")
            continue
        if t == "Conference committee report now available":
            add(d, "G", "The conference committee's report was filed", "routine")
            continue
        if t == "Conference Committee Report was adopted":
            conf.add(h)
            add(d, h, f"The {H} adopted the conference committee's report", "ccr")
            if conf >= {"S", "H"}:
                both = True
                amended_by = None
                passed["S"], passed["H"] = passed.get("S", len(steps)), passed.get("H", len(steps))
                add(d, h, "Passed both houses in the same form", "both")
            continue
        if re.match(r"Conference Committee Report (?:agree to disagree adopted|not adopted|agree to disagree, not adopted)", t):
            conf = set()
            add(d, h, f"The {H} " + ("agreed the conferees couldn't agree; a new conference committee was named" if "agree to disagree adopted" in t
                                     else "rejected the conference committee's report"), "ccrfail")
            continue
        if t == "Substitute motion to not adopt and appoint a conference committee failed":
            add(d, h, f"A motion in the {H} to reject the report and name a new conference committee failed", "other")
            continue
        if t.startswith("Motion to not adopt Conference Committee Report passed"):
            killed = True
            add(d, h, f"The {H} rejected the conference committee's report, killing the bill", "kill")
            continue
        if re.search(r"appointed to replace .* on the Conference Committee", t):
            add(d, h, f"{H} conference committee members changed", "routine")
            continue
        if re.match(r"Died (in|on) ", t):
            add(d, h if "House" in t or "Senate" in t else "G", t.replace("Died in Committee", "Died in committee").replace("Died on Calendar", "Died on the calendar").replace("Died in Conference", "Died in conference committee"), "died")
            continue
        if re.match(r"(Re)?[Ee]ngrossed on |Enrolled on ", t):
            add(d, h, t.split(" on ")[0] + " (the bill's text reprinted with its amendments)" if "ngrossed" in t else "Enrolled", "routine")
            continue
        if t.startswith("Enrolled and presented to Governor"):
            enrolled = both = True
            add(d, "G", "DELIVERED TO GOVERNOR", "sent")
            continue
        if t.startswith("Enrolled and presented to Secretary of State"):
            to_sos = both = True
            add(d, "G", "Sent to the Secretary of State for the ballot (it doesn't go to the governor)" if amendment else "Sent to the Secretary of State", "nosign")
            continue
        if t.startswith("Approved by Governor except line item veto of"):
            signed = item = True
            items = re.sub(r"\s+on \w+day, \w+ \d+, \d{4}$", "", t[len("Approved by Governor except line item veto of"):]).strip()
            add(d, "G", f"Signed by the governor, with some items vetoed (line-item veto: {items})", "signed")
            continue
        if t.startswith("Approved by Governor"):
            signed = True
            add(d, "G", "Signed by the governor", "signed")
            continue
        if t == "Will become law without Governor's signature":
            no_sign = True
            add(d, "G", "Became law without the governor's signature", "nosign")
            continue
        if t.startswith("Vetoed by Governor"):
            vetoed = True
            add(d, "G", "VETOED", "vetoed")
            continue
        if t == "Motion to override veto prevailed":
            overrides.add(h)
            add(d, h, f"The {H} voted to override the veto", "override")
            continue
        if t in ("Motion to override veto failed; Veto sustained",):
            sustained = True
            add(d, h, f"The {H} failed to override the veto (sustained)", "sustain")
            continue
        if t == "No motion to reconsider vetoed bill; Veto sustained":
            sustained = True
            add(d, h, f"No override vote in the {H}: the veto stands", "sustain")
            continue
        m = re.match(r"Motion to override line item veto (prevailed|failed); Line item veto (.+?) (overridden|sustained)$", t)
        if m:
            add(d, h, f"The {H} {'overrode' if m.group(1) == 'prevailed' else 'failed to override'} the line-item veto of {m.group(2).replace('Secs. ', 'sections ')}", "other")
            continue
        if t.startswith("No motion to reconsider line item vetoes"):
            add(d, h, f"No override vote in the {H} on the remaining line-item vetoes: they stand", "other")
            continue
        m = re.match(r"Law effective (.+)$", t)
        if m:
            add(d, "G", f"Takes effect {m.group(1)}", "effective")
            continue
        if re.match(r"Motion to suspend|Motion to lay on table not adopted|Motion to withdraw from pending", t):
            continue
        if re.match(r"(?:Stricken from Calendar by Rule|Motion to strike from Calendar adopted)", t):
            add(d, h, f"Taken off the {H} calendar" + (f" (under Rule {re.search(r'Rule (\d+)', t).group(1)})" if re.search(r"Rule \d+", t) else ""), "other")
            continue
        m = re.match(r"Motion to withdraw from (?:House|Senate) Committee on (.+) not adopted", t)
        if m:
            add(d, h, f"A motion to take it out of the {committee_name(m.group(1))} Committee failed in the {H}", "other")
            continue
        add(d, h, t, "other")

    # Laws and vetoes. A veto stands unless both houses overrode it.
    overridden = vetoed and overrides >= {"S", "H"}
    law = (not amendment) and ((signed and not (vetoed and not overridden)) or overridden or no_sign)
    if overridden:
        last_override = max(s[0] for s in steps if s[3] == "override")
        steps.append((last_override, "G", "Became law over the governor's veto", "lawnote"))
    steps = [s for _, s in sorted(enumerate(steps), key=lambda e: (e[1][0] or "9999", e[0]))]

    both = (both or enrolled or to_sos or law or vetoed or conf >= {"S", "H"}) and not (amended_by and not enrolled and not to_sos and not law and not vetoed)
    if amendment:
        stage = 3 if both else 2 if passed else None
    elif law:
        stage = 5
    elif vetoed:
        stage = 6
    elif enrolled:
        stage = 4
    elif both:
        stage = 3
    elif passed:
        stage = 2
    else:
        stage = None
    passed_h = set(passed)
    if stage is not None and stage >= 3:
        passed_h = {"S", "H"}
    if stage is None:
        stage = 1 if place == "floor" or origin in failed else 0

    comm_now = comm if place == "committee" and stage in (0, 2) else None
    title = short_title(b)
    summary = long_summary(b) or title + "."
    if amendment and not title.lower().startswith(("proposing", "constitutional amendment", "a constitutional")):
        title = f"Constitutional amendment: {title[:1].lower() + title[1:]}"
    note = load(session, f"notes/{p}") or {}
    keywords = text(note.get("keywords"))
    narrow = P.narrow_kind(title)
    topics = list(dict.fromkeys((["const"] if amendment else []) +
                                [P.COMMITTEE_TOPICS[c] for c in sorted(topic_comms | last_in(refs)) if c in P.COMMITTEE_TOPICS] +
                                [k for k in P.TOPIC_WORDS if P.TOPIC_WORDS[k].search(P.AGENCY_NAMES.sub(" ", f"{title} {summary} {keywords}"))]))
    fate = "passed" if reported or recalled or passed else "none"

    names, kp = [], []
    for s in b.get("SPONSOR_NAMES") or []:
        h, n, k, party = sponsor(session, s, p)
        if n and n not in names:
            names.append(n)
            kp.append(k)
            if party:
                parties[(h or p[0], n)] = party
    sponsor_name = names[0] if names else "—"
    cos = names[1:]
    seat_ = seats(session).get(kp[0]) if kp and kp[0] else None
    district = int(seat_.split(":")[1]) if seat_ and seat_[0] == p[0] else 0
    where = HOUSE.get(where_h, HOUSE[origin])
    if stage == 0:
        desc = f"In {where} committee"
    elif stage == 1:
        desc = f"Failed in the {HOUSE[origin]}" if origin in failed else f"On the {where} calendar"
    else:
        desc = {2: f"Passed the {HOUSE[origin] if origin in passed_h else HOUSE[other]}" + (f"; failed in the {HOUSE[other]}" if other in failed else ""),
                3: "Passed both houses" + ("; goes to the voters" if amendment else ""), 4: "On the governor's desk",
                5: "Became law", 6: "Vetoed"}[stage]
    if killed and stage < 3:
        desc = "Killed in conference"

    def dates(test, mode="last"):
        ds = sorted({s[0] for s in steps if test(s) and s[0]})
        return {"first": ds[0], "last": ds[-1], "all": ";".join(ds)}[mode] if ds else ""

    days = {((x.get("action_code") or ""), CH.get((x.get("chamber") or "").lower()), (x.get("occurred_datetime") or "")[:16]): line_day(x, read) for x in hist}
    votes = floor_votes(session, p, days)
    action_dates = [s[0] for s in steps if s[0]]
    budget = bool(re.search(r"\bappropriations for (?:the )?fiscal years?\b", text(b.get("LONGTITLE")), re.I))
    rec = {
        "nums": [p], "base": [p], "prev": earlier(session, p, b),
        "title": title, "summary": summary,
        "act": "", "lawCode": "", "law": None, "laws": [],
        "comms": sorted({f"{h} · {c}" for h, c in refs}), "topics": topics, "places": [], "narrow": narrow,
        "commFate": fate, "mainTopic": topics[0] if topics else "", "local": "local" in topics,
        "senDeleg": False, "asmDeleg": False, "budget": budget,
        "passedS": "S" in passed_h, "passedA": "H" in passed_h, "program": None,
        "stage": stage, "passedIn": (HOUSE[origin] if origin in passed_h else HOUSE[other]) if stage == 2 else None,
        "chapter": None, "veto": None, "memo": "", "vetoMemo": None,
        "simText": f"{title} {summary} {keywords}",
        "comm": comm_now if stage == 0 else None,
        "first": min(action_dates, default=f"{session}-01-01"),
        "last": max(action_dates, default=f"{session}-01-01"),
        "cosp": len(cos),
        "keyDates": [
            dates(lambda s: s[3] in ("reported", "recall"), "first"),
            dates(lambda s: s[2] == "PASSED SENATE", "all"),
            dates(lambda s: s[2] == "PASSED HOUSE", "all"),
            "",
            dates(lambda s: s[3] == "sent"),
            dates(lambda s: s[3] in ("signed", "lawnote", "nosign")) if stage == 5 else "",
            dates(lambda s: s[3] == "vetoed"),
        ],
        "votes": votes, "firstComms": [(origin, first_ref, bool(reported or recalled or passed))] if first_ref else [],
        "vers": [{"p": p, "sponsor": sponsor_name, "district": district, "cosponsors": cos, "primes": 1, "cosp": len(cos),
                  "statusDesc": desc, "committee": comm_now,
                  "actions": [[s[0], s[2]] for s in steps]}],
    }
    if item and stage == 5:
        rec["vers"][0]["itemVeto"] = True
    # A conference committee's report often replaces a bill's contents with other bills' (HB 2043 of 2025-26: an
    # insurance bill as passed, a property tax law after conference), and the supplemental note describes the bill before
    # it. Such a note is dropped when it shares almost no words with the bill's final titles, else marked.
    what = what_it_does(note)
    if what and any(s_[3] == "ccr" for s_ in steps):
        brief = what.split("\nBackground: ")[0]
        tw, bw = content_words(f"{title} {summary}"), content_words(brief)
        if len(tw & bw) < 0.2 * max(1, len(tw)):
            return rec, None
        return rec, (what, "From the Legislative Research Department's supplemental note on the bill before the conference committee's report, which may have changed it.")
    return rec, (what, "From the Legislative Research Department's supplemental note.") if what else None


STOP = set("the a an of and or to in for on by with from that this be is are as at certain such any providing relating "
           "concerning bill would act state kansas amend amending law laws establishing requiring".split())


def content_words(t):
    return {w for w in re.findall(r"[a-z]{4,}", t.lower()) if w not in STOP}


def last_in(refs):
    """Each house's last committee."""
    out = {}
    for h, c in refs:
        out[h] = c
    return set(out.values())


def floor_votes(session, p, days=None):
    """The bill's own floor roll calls, member by member where the roll call's detail is downloaded ("N" no, "B" present
    and passing, "A" absent or not voting; yes is left out), else the tally alone. Each is dated by its history line
    (days: (action code, house, time) -> day), since a vote after midnight belongs to the day before's journal."""
    out = []
    seat = seats(session)
    ms = members(session)
    rolls = roll_files(session)
    for d, h, label, tally, apn, code, when in sorted(bill_votes(session).get(p, []), key=lambda v: v[6]):
        yes, no = int(tally.get("yea") or 0), int(tally.get("nay") or 0)
        d = (days or {}).get((code, h, when[:16]), d)  # the journal day its history line carries
        listed = []
        r = rolls.get(apn)
        if r:
            for group, c in (("nay", "N"), ("present", "B"), ("absent", "A"), ("not_voting", "A")):
                for x in (r.get("members") or {}).get(group) or []:
                    k = x.get("kpid")
                    sid = seat.get(k)
                    if sid and sid[0] != h:
                        sid = None
                    last = (ms.get(k) or {}).get("last") or text(x.get("name")).split(" ")[-1]
                    listed.append([sid or f"{h}?{last}", c])
        out.append([h, "F", label, d, yes, no, listed])
    return out


# ---- what it does ---------------------------------------------------------------------------------------------------

def what_it_does(note):
    """The supplemental note's Brief, then its Background (the hearing, the committees' amendments), without the note's
    heading lines, its keywords and its footnote. Paragraphs are separated by line breaks."""
    t = (note or {}).get("text") or ""
    if not t:
        return ""
    t = t.replace("\r", "")
    t = re.split(r"\n_{5,}\n", t)[0]
    i = re.search(r"(?m)^Brief\*?\s*$", t)
    if not i:
        return ""
    body = t[i.end():]
    j = re.search(r"(?m)^Background\s*$", body)
    brief, background = (body[:j.start()], body[j.end():]) if j else (body, "")

    def paras(s, limit):
        ps = [text(x) for x in re.split(r"\n\s*\n", s) if text(x)]
        kw = text(note.get("keywords"))
        ps = [x for x in ps if x != kw]
        # Headings ("Definitions", "Senate Committee on Judiciary", "Fiscal Information") lead the paragraph after them.
        joined = []
        for x in ps:
            last = joined[-1] if joined else ""
            if last and len(last) < 100 and not last.startswith(("●", "○")) and (
                    not re.search(r"[.!?:;)\]\"”’]$", last) or re.fullmatch(r"(?:[HS]B|[HS]CR) \d+ \(.*\)", last)):
                joined[-1] = f"{joined[-1]}: {x}"
            else:
                joined.append(x)
        ps = joined
        out, n = [], 0
        for x in ps:
            if n + len(x) > limit and out:
                break
            out.append(x)
            n += len(x)
        return out

    b = paras(brief, 6000)
    if not b:
        return ""
    g = paras(background, 4000)
    return "\n".join(b + (["Background: " + g[0]] + g[1:] if g else []))


# ---- earlier bienniums --------------------------------------------------------------------------------------------------

_KEYS = {}


def _key(b):
    return re.sub(r"[^a-z0-9 ]", "", short_title(b).lower())


def _keys(session):
    """A biennium's bills that didn't become law: short title -> [(number, first sponsor)]."""
    if session not in _KEYS:
        out = {}
        for b in (load(session, "bill_status", {}) or {}).get("bills") or []:
            if not kept(b) or b.get("measure_state") == "enacted":
                continue
            out.setdefault(_key(b), []).append((b["BILLNO"], text((b.get("ORIGINAL_SPONSOR") or [""])[0])))
        _KEYS[session] = out
    return _KEYS[session]


def earlier(session, p, b):
    """The same bill in the biennium before: the same short title (six words or more) and the same first sponsor, or
    the same short title when only one bill in each biennium has it. Never appropriations bills."""
    out = set()
    y = session - 2
    if y not in sessions():
        return out
    k = _key(b)
    if len(k.split()) < 6 or re.search(r"\bappropriation", k):
        return out
    old = _keys(y).get(k, [])
    if not old:
        return out
    sp = text((b.get("ORIGINAL_SPONSOR") or [""])[0])
    same = [n for n, s in old if s and s == sp]
    if same:
        out.add((y, same[0]))
    elif len(old) == 1 and len(_keys(session).get(k, [])) <= 1:
        out.add((y, old[0][0]))
    return out


def parties(session, recs):
    if session not in _PARTIES:
        load_session(session)
    return {k: v for k, v in _PARTIES.get(session, {}).items() if v in ("D", "R")}


if __name__ == "__main__":
    # Laws, vetoes and overrides by year, against the API's governor's actions.
    from collections import Counter
    for s in sessions():
        recs, index, _, _ = load_session(s)
        gov = {g["bill_no"]: g for g in (load(s, "governor_actions", {}) or {}).get("governor_actions") or []}
        by = Counter()
        for r in recs:
            if r["stage"] == 5:
                by[("law", (r["keyDates"][5] or "")[:4])] += 1
            if r["keyDates"][6]:
                by[("vetoed", r["keyDates"][6][:4])] += 1
                by[("veto stands" if r["stage"] == 6 else "overridden", r["keyDates"][6][:4])] += 1
            if r["vers"][0].get("itemVeto"):
                by[("item vetoes", (r["keyDates"][5] or "")[:4])] += 1
        print(s, dict(sorted(by.items())))
        print("  governor's actions:", Counter((g["status"], g["last_date"][:4]) for g in gov.values()))
        law_api = {n for n, g in gov.items() if g["status"] in ("signed", "veto-overridden", "line-item-veto", "partial-override")}
        veto_api = {n for n, g in gov.items() if g["status"] == "vetoed"}
        laws = {r["nums"][0] for r in recs if r["stage"] == 5}
        vetoes = {r["nums"][0] for r in recs if r["stage"] == 6}
        print("  laws here not in the API's list:", sorted(laws - law_api), "| API laws not laws here:", sorted(law_api - laws))
        print("  vetoes here not in the API's list:", sorted(vetoes - veto_api), "| API vetoes not here:", sorted(veto_api - vetoes))
        print("  stages:", sorted(Counter(r["stage"] for r in recs).items()))
        print("  amendments:", [(r["nums"][0], r["stage"]) for r in recs if "const" in r["topics"] and r["stage"] >= 2])
