"""Committee votes by member from the House and Senate Journals (2026-11-22).

Each house's daily journal (www.legis.iowa.gov/docs/publications/HJNL/20260219_HJNL.pdf, SJNL for the Senate; under
/docs/, which robots.txt allows: it bars only /chambers/) prints the committees' reports with their final votes, member by
member. The Senate: "FINAL COMMITTEE REPORTS OF BILL ACTION", a committee heading ("COMMERCE"), then for each bill "Bill
Title: SENATE FILE 547 (SSB 1170), a bill for an act ...", "Recommendation: DO PASS.", "Final Vote: Yeas, 18: Bousselot,
Koelker, ... and Zumbach. Nays, 2: Knox and Schultz. Excused, none." (2023-24 and 2025-26 alike). The House, since 2025:
"COMMITTEE RECOMMENDATIONS", "COMMITTEE ON AGRICULTURE", "House File 2444, a bill for an act ..." or "Committee Bill
(Formerly House Study Bill 751), relating to ...", "Recommendation: Do Pass February 19, 2026.", "Final Vote: Yeas, 17:
Representatives Wulf-CH, Behn-VC, ... Nays, 6: Cooling, ... Excused, 0." The House's 2023-24 journals print the
recommendations without votes, so the House's committee votes of 2023-24 have no names (its committee minutes, prose
written differently by each committee's secretary, aren't read).

fetch.py saves each journal wanted as text (journals/<H|S><YYYYMMDD>.txt, pdftotext -layout), once: the days of the
"Committee report" lines in the bills' histories (`wanted()`), and for the House the next days up to a week after a
report whose bill the journals read so far don't have (the House prints a recommendation in a later day's journal: Commerce's
of February 18, 2026 in the 19th's). A journal that answers 404 (no session that day) is noted and not asked again.
convert.py ties each report line to a journal's entry for the same bill (any of its numbers: "Formerly House File
2283"), house and committee, within three days, whose tally matches the history's "Committee vote" line when there is
one (the Senate's histories have none: the journal's counts are the vote's), and only when each group's names add up to
its count.
"""
import os, re
from datetime import date, timedelta

GROUPS = {"yeas": "Y", "ayes": "Y", "nays": "N", "noes": "N", "excused": "E", "absent": "A", "present": "B",
          "not voting": "A", "abstaining": "B", "abstain": "B", "pass": "B"}
GROUP_RX = r"(Yeas|Ayes|Nays|Noes|Excused|Absent|Present|Not voting|Abstaining|Abstain)"
MONTHS = {m: i for i, m in enumerate(["january", "february", "march", "april", "may", "june", "july", "august",
                                      "september", "october", "november", "december"], 1)}
KINDS = {"FILE": "F", "JOINT RESOLUTION": "JR", "STUDY BILL": "SB"}


def url(site, h, day):
    """day "2026-02-19" -> the journal's PDF."""
    d = day.replace("-", "")
    return f"{site}/docs/publications/{h}JNL/{d}_{h}JNL.pdf"


def path(folder, h, day):
    return os.path.join(folder, "journals", f"{h}{day.replace('-', '')}.txt")


def bill_key(house, kind, num):
    """("Senate", "File", "547") -> "SF547"; ("SF", None, "329") -> "SF329"."""
    if kind is None:
        return re.sub(r"\s+", "", house).upper() + str(int(num))
    return house.strip()[0].upper() + KINDS[re.sub(r"\s+", " ", kind).upper()] + str(int(num))


REF = re.compile(r"\b(House|Senate|HOUSE|SENATE)\s+(File|Joint\s+Resolution|Study\s+Bill|FILE|JOINT\s+RESOLUTION|STUDY\s+BILL)\s+(\d+)"
                 r"|\b(HF|SF|HSB|SSB|HJR|SJR)\s*(\d+)\b")


def refs(s):
    out = []
    for m in REF.finditer(s):
        k = bill_key(m.group(1), m.group(2), m.group(3)) if m.group(1) else bill_key(m.group(4), None, m.group(5))
        if k not in out:
            out.append(k)
    return out


def iso_long(s):
    m = re.search(r"\b([A-Z][a-z]+)\s+(\d{1,2}),\s+(\d{4})", s or "")
    if not m or m.group(1).lower() not in MONTHS:
        return ""
    return f"{m.group(3)}-{MONTHS[m.group(1).lower()]:02d}-{int(m.group(2)):02d}"


def names_of(s):
    """"Representatives Wulf-CH, Behn-VC, Thompson, M., Wills, J. and Sitzmann" -> ["Wulf", "Behn", "Thompson, M.",
    "Wills, J.", "Sitzmann"] (initials and suffixes belong to the name before)."""
    s = re.sub(r"^\s*(?:Representatives?|Senators?|Reps?\.)\s+", "", s or "")
    s = re.sub(r"-(?:CH|VC|RM)\b", "", s)
    s = re.sub(r",?\s*(?:Chair|Vice Chair|Ranking Member)\b", "", s)
    out = []
    for tok in re.split(r",\s*|\s+and\s+|;\s*", s):
        tok = tok.strip().strip("*").strip()
        if not tok:
            continue
        if tok.lower().startswith("and "):
            tok = tok[4:].strip()
        if out and re.fullmatch(r"(?:[A-Z]\.?|Jr\.?|Sr\.?|II|III|IV)", tok):
            out[-1] = f"{out[-1]}, {tok}"
        else:
            out.append(tok)
    return out


def vote_groups(s):
    """"Yeas, 18: A, B and C. Nays, 2: D and E. Excused, none." -> ({"Y": 18, "N": 2, "E": 0}, {"Y": [...], ...}), or
    None when a group's names don't add up to its count."""
    s = re.sub(r"\s+", " ", s).strip()
    counts, names = {}, {}
    rx = re.compile(GROUP_RX + r"\s*[,:]?\s*(none|None|NONE|\d+)\s*(?::\s*(.*?))?\s*\.?(?=\s+" + GROUP_RX + r"\s*[,:]?\s*(?:none|None|NONE|\d+)\b|\s*$)")
    pos = 0
    for m in rx.finditer(s):
        if s[pos:m.start()].strip():
            return None  # text between the groups that isn't one
        pos = m.end()
        code = GROUPS[m.group(1).lower()]
        n = 0 if m.group(2).lower() == "none" else int(m.group(2))
        listed = names_of(m.group(3) or "")
        if len(listed) != n:
            return None
        counts[code] = counts.get(code, 0) + n
        names.setdefault(code, []).extend(listed)
    if s[pos:].strip() or "Y" not in counts:
        return None
    return counts, names


PAGE_HEAD = re.compile(r"^\s*(?:\d+\s+JOURNAL OF THE (?:HOUSE|SENATE)\s+\d+\w\w Day|\d+\w\w Day\s+[A-Z]+DAY,\s+[A-Z]+ \d+, \d{4}\s+\d+"
                       r"|PROOF|\f)\s*$")
STOP = re.compile(r"^\s*(?:Fiscal Note|Placed on|ALSO:|Bill Title:|Committee (?:Bill|Resolution)\b|\*?(?:House|Senate) (?:File|Joint)|"
                  r"Recommendation:|\*Pursuant|[A-Z][A-Z ,&'\-]+$)")


def parse(text, h, day):
    """One journal's committee reports with votes: [{"nums": ["SF547", "SSB1170"], "committee": "HEALTH AND HUMAN
    SERVICES", "day": recommendation's day or the journal's, "counts": {...}, "names": {...}}]; entries whose names
    don't add up are left out."""
    lines = [ln for ln in (text or "").replace("\f", "\n").split("\n") if not PAGE_HEAD.match(ln)]
    out = []
    committee, item, rec_day, in_reports = "", "", "", False
    i = 0
    while i < len(lines):
        ln = lines[i].rstrip()
        st = ln.strip()
        if h == "S" and re.fullmatch(r"FINAL COMMITTEE REPORTS OF BILL ACTION", st):
            in_reports, committee = True, ""
        elif h == "H" and re.fullmatch(r"COMMITTEE RECOMMENDATIONS", st):
            in_reports, committee = True, ""
        elif in_reports and h == "H" and re.fullmatch(r"COMMITTEE ON [A-Z ,&'\-]+", st):
            committee, item = st[len("COMMITTEE ON "):], ""
        elif in_reports and h == "S" and re.fullmatch(r"[A-Z][A-Z ,&'\-]+", st) and st not in ("ALSO:",) and not ln.startswith(" " * 6):
            committee, item = st, ""
        elif in_reports and h == "S" and re.match(r"(?:[A-Z ]{6,})$", st) and ln.startswith(" " * 6):
            in_reports = False  # the next centered section heading ends the reports
        elif re.match(r"\s*(?:Bill Title:|\*?(?:House|Senate) (?:File|Joint Resolution)\s+\d+|Committee (?:Bill|Resolution)\b)", ln) and in_reports:
            item, rec_day = st, ""
            j = i + 1
            while j < len(lines) and lines[j].strip() and not STOP.match(lines[j]) and len(item) < 400:
                item += " " + lines[j].strip()
                j += 1
        elif st.startswith("Recommendation:") and in_reports:
            rec_day = iso_long(st)
        elif st.startswith("Final Vote:") and in_reports and item:
            vt = st[len("Final Vote:"):]
            j = i + 1
            while j < len(lines) and j < i + 15 and not STOP.match(lines[j]):
                vt += " " + lines[j].strip()
                j += 1
            head = re.sub(r"\s+", " ", item)
            head = re.split(r",\s+(?:a bill|a joint resolution|relating|providing|proposing|establishing|creating|making|"
                            r"concerning|modifying|including|requiring|prohibiting|authorizing)\b", head, maxsplit=1)[0]
            nums = refs(re.sub(r"^Bill Title:\s*\*?", "", head))
            g = vote_groups(vt)
            if nums and g:
                out.append({"nums": nums, "committee": committee, "day": rec_day or day, "journal": day,
                            "counts": g[0], "names": g[1]})
            i = j
            continue
        i += 1
    return out


def read(folder):
    """Every journal read for a General Assembly: {"H": [entry, ...], "S": [...]}, each entry as parse() gives it."""
    out = {"H": [], "S": []}
    d = os.path.join(folder, "journals")
    for f in sorted(os.listdir(d)) if os.path.isdir(d) else []:
        m = re.fullmatch(r"([HS])(\d{4})(\d\d)(\d\d)\.txt", f)
        if not m:
            continue
        try:
            text = open(os.path.join(d, f), encoding="utf-8", errors="replace").read()
        except OSError:
            continue
        out[m.group(1)] += parse(text, m.group(1), f"{m.group(2)}-{m.group(3)}-{m.group(4)}")
    return out


def report_days(secs):
    """The days a history reports a bill from committee, by house: {("S", "2025-03-06"): {"SF245", ...}}. A line with no
    house (Open States' "legislature" lines) takes the house of the line before it that has one."""
    out = {}
    for k, s in secs.items():
        where = k[0] if k[0] in "HS" else ""
        for d, h, t in sorted(s.get("actions") or [], key=lambda a: a[0]):
            if h in ("H", "S"):
                where = h
            if d and where and re.match(r"Committee report", t) and not re.search(r"indefinite postponement", t):
                out.setdefault((h or where, d), set()).add(k)
    return out


def committee_bill_days(secs):
    """A committee's own bills: the day of the first line and the four weekdays before, in the bill's house."""
    out = []
    for k, s in secs.items():
        acts = sorted(s.get("actions") or [], key=lambda a: a[0])
        if k[0] in "HS" and acts and any(re.search(r"COMMITTEE", n[0], re.I) for n in s.get("sponsors") or []) \
                and acts[0][2].startswith("Introduced"):
            d = date.fromisoformat(acts[0][0])
            back = [d - timedelta(days=i) for i in range(0, 7)]
            out += [(k[0], x.isoformat()) for x in back if x.weekday() < 5][:5]
    return out


def next_days(day, n=7):
    d = date.fromisoformat(day)
    return [(d + timedelta(days=i)).isoformat() for i in range(1, n + 1) if (d + timedelta(days=i)).weekday() < 5]
