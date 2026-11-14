"""Missouri's bills (downloaded by states/mo/fetch.py from the House's XML exports and the Senate's website) in the shape
build_data.py reads. A page a year: the General Assembly meets once a year in a regular session (early January to mid-May;
the governor acts by mid-July; the veto session is in September) and bills die when it ends. House and Senate bills (HB,
SB) and joint resolutions (HJR, SJR), which in Missouri propose constitutional amendments: passed by a majority of each
house's members, they go to the voters, never the governor (tagged "const"). Concurrent and simple resolutions and
extraordinary sessions are left out.

The two houses publish separately:
- House bills: data/mo/<year>/house/bills/<HB2>.xml, the House's export, with every action in both houses ("Referred:
  Emerging Issues(H)", "HCS Reported Do Pass (H)" with the committee's tally, "Perfected (H)", "Third Read and Passed (H)"
  with the floor tally, "Reported to the Senate and First Read (S)", "Third Read and Passed (S)", "House Adopts (H)",
  "Truly Agreed To and Finally Passed", "Delivered to Governor", "Approved by Governor (G)", "Vetoed in Part by Governor
  (G)"), sponsors and co-sponsors with their districts (senators are 200 + their district), the House's subject index.
  Each year's folder also holds the previous year's appropriation bills under their old numbers with nothing but the
  governor's spending restrictions ("Message Received from the Governor, pursuant to Article IV, Section 27", dated
  before the session): those files are skipped, and the restriction lines are kept as written but never read as vetoes.
- Senate bills: data/mo/<year>/senate/bills/<SB1>.html (sponsor, current version, committee, status, the Senate's bill
  summary) and actions/<SB1>.html, the "All Actions" list, newest first, both houses ("S Third Read and Passed", "H Third
  Read and Passed", "Truly Agreed To and Finally Passed", "Signed by Governor"), no tallies; the House's tallies on Senate
  bills come from its SenateActList.xml when the bill is there.
"Truly Agreed To and Finally Passed" means passed both houses (after the second house passed it unchanged, the first
agreed to its changes and passed it again, or both adopted a conference report and passed the conference substitute).
A bill combined into another ("HCS for HBs 594 and 508"; a House file's SubstitutedBy, the Senate's "Bill Combined")
ends there, with a line saying so. No bill was vetoed outright in 2024-2026 (the appropriation bills had items vetoed:
"Vetoed in Part by Governor"; a law with items vetoed is a law). "Governor took no action, sent to Secretary of
State/Article III, Sec. 31" is law without signature.

Votes: floor tallies come from the House's exports; the Senate's roll calls member by member from the Senate Journal's
text (journals/senate/DAY56.txt.gz: "On motion of Senator Trent, SS No. 2 for HCS for HBs 594 and 508 was read the 3rd
time and passed by the following vote: YEAS—Senators Bean Beck ..."), matched to the passage by day and bill number.
The House's journals weren't downloaded, so House floor votes are tallies only. Committee tallies (House committees
only) come from the exports.
"""
import gzip, html as H_, json, os, re
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from datetime import datetime, date
from zoneinfo import ZoneInfo

from states.mo import profile as P

HOUSE = {"S": "Senate", "H": "House"}
OTHER = {"S": "H", "H": "S"}
SEATS = {"S": 34, "H": 163}
KIND = re.compile(r"^(HB|HJR|SB|SJR)(\d+)$")
_CACHE, _PARTIES = {}, {}
STATS = Counter()  # how many Senate passages matched a journal roll call, for the summary


def folder(session):
    return os.path.join(P.DATA, str(session))


def sessions():
    out = []
    for f in sorted(os.listdir(P.DATA)) if os.path.isdir(P.DATA) else []:
        if re.fullmatch(r"\d{4}", f) and os.path.exists(os.path.join(P.DATA, f, "house", "BillList.xml")) \
                and os.path.exists(os.path.join(P.DATA, f, "senate", "list.json")):
            out.append(int(f))
    return out


def text(fragment):
    return re.sub(r"\s+", " ", H_.unescape(re.sub(r"<[^>]+>", " ", fragment or ""))).strip()


def mdy(d):
    """"04/23/2025" -> "2025-04-23"."""
    m = re.match(r"(\d{1,2})/(\d{1,2})/(\d{4})", d.strip())
    return f"{m.group(3)}-{int(m.group(1)):02d}-{int(m.group(2)):02d}" if m else ""


def num_text(p):
    m = KIND.match(p)
    return f"{m.group(1)} {m.group(2)}" if m else p


# ---- Reading the House's exports ----

def house_bill(session, key):
    """A House bill's export -> {key, title, short, subjects, sponsors [(name, house, district, type)], actions [(date,
    seq, description, comments, (yes, no, present) or None)], current, parent} or None."""
    path = os.path.join(folder(session), "house", "bills", f"{key}.xml")
    try:
        root = ET.parse(path).getroot()
    except (OSError, ET.ParseError):
        return None
    bi = root.find("BillInformation")
    if bi is None:
        return None
    g = lambda e, t: (e.findtext(t) or "").strip()
    sponsors = []
    for sp in bi.findall("Sponsor"):
        d = int(re.sub(r"\D", "", g(sp, "District")) or 0)
        h = "S" if d > 200 else "H"
        sponsors.append((g(sp, "FullName"), h, d - 200 if d > 200 else d, g(sp, "SponsorType")))
    actions = []
    for a in bi.findall("Action"):
        rc = a.find("RollCall")
        tally = None
        if rc is not None:
            tally = tuple(int(g(rc, t) or 0) for t in ("TotalYes", "TotalNo", "TotalPresent"))
        actions.append((g(a, "PubDate")[:10], int(g(a, "ActivitySequence") or 0), re.sub(r"\s+", " ", g(a, "Description")),
                        re.sub(r"\s+", " ", g(a, "Comments")), tally))
    actions.sort(key=lambda x: (x[0], x[1]))
    t = bi.find("Title")
    return {"key": key, "title": g(t, "LongTitle") if t is not None else "", "short": g(t, "ShortTitle") if t is not None else "",
            "subjects": [g(s, "SubjectName") for s in bi.findall("SubjectIndex")], "sponsors": sponsors,
            "actions": actions, "current": g(bi, "CurrentBillString"),
            "parent": (bi.find("SubstitutedBy").findtext("ParentBillString") or "").strip() if bi.find("SubstitutedBy") is not None else ""}


def senate_acts(session):
    """The House's actions on Senate bills: SB1 -> {actions, subjects} (SenateActList.xml)."""
    key = (session, "sacts")
    if key not in _CACHE:
        out = {}
        try:
            root = ET.parse(os.path.join(folder(session), "house", "SenateActList.xml")).getroot()
        except (OSError, ET.ParseError):
            root = None
        for bi in root.iter("BillInformation") if root is not None else []:
            k = (bi.findtext("BillNumber") or "").strip()
            acts = []
            for a in bi.findall("Action"):
                rc = a.find("RollCall")
                tally = tuple(int((rc.findtext(t) or "0").strip() or 0) for t in ("TotalYes", "TotalNo", "TotalPresent")) if rc is not None else None
                acts.append(((a.findtext("PubDate") or "")[:10], re.sub(r"\s+", " ", a.findtext("Description") or "").strip(), tally))
            out[k] = {"actions": acts, "subjects": [(s.findtext("SubjectName") or "").strip() for s in bi.iter("SubjectIndex")]}
        _CACHE[key] = out
    return _CACHE[key]


# ---- Reading the Senate's pages ----

def senate_list(session):
    key = (session, "slist")
    if key not in _CACHE:
        try:
            raw = json.load(open(os.path.join(folder(session), "senate", "list.json"), encoding="utf-8"))
        except (OSError, ValueError):
            raw = []
        _CACHE[key] = {f"{r['billPrefix']}{r['billSuffix']}": r for r in raw if r.get("session", "R") == "R"}
    return _CACHE[key]


def senate_bill(session, key):
    """A Senate bill's page and actions -> {key, title, sponsors, actions [(date, line, journal)], status, summary,
    committee, current} or None."""
    row = senate_list(session).get(key)
    try:
        page = open(os.path.join(folder(session), "senate", "bills", f"{key}.html"), encoding="utf-8").read()
        acts = open(os.path.join(folder(session), "senate", "actions", f"{key}.html"), encoding="utf-8").read()
    except OSError:
        return None

    def field(label):
        m = re.search(rf'detail-grid__label[^>]*>\s*{label}\s*</span>(.*?)</div>\s*</div>', page, re.S)
        return text(m.group(1)) if m else ""
    actions = []
    for d, a, j in re.findall(r'<td class="col--date"[^>]*>(.*?)</td>\s*<td class="col--action"[^>]*>(.*?)</td>\s*<td>(.*?)</td>', acts, re.S):
        actions.append((mdy(text(d)), text(a), text(j)))
    actions.reverse()  # newest first on the page
    # Keep the page's order within a day (reversed), and sort by day.
    actions = [x for _, x in sorted(enumerate(actions), key=lambda e: (e[1][0], e[0]))]
    summary = ""
    m = re.search(r"CURRENT BILL SUMMARY.*?text-content--preformatted[^>]*>(.*?)</div>", page, re.S)
    if m:
        summary = m.group(1)
    title = text(re.search(r'main-header-description[^>]*>(.*?)</div>', page, re.S).group(1)) if 'main-header-description' in page else ""
    sponsors = []
    if row:
        sponsors.append((f"{row.get('sponsorFirstName') or ''} {row.get('sponsorLastName') or ''}".strip(), "S",
                         int(row.get("districtNumber") or 0), "Sponsor"))
    return {"key": key, "title": (row or {}).get("briefDescription") or title, "short": "", "sponsors": sponsors,
            "actions": actions, "status": field("Current Status"), "summary": summary_text(summary),
            "committee": field("Committee"), "current": field("Title"),
            "handler": f"{(row or {}).get('handlerFirstName') or ''} {(row or {}).get('handlerLastName') or ''}".strip()}


def summary_text(s):
    """The Senate's bill summary (preformatted text: one paragraph or heading a line) as paragraphs: the version line
    ("SS/SB 1 - This act ...") kept, cross-references ("These provisions are identical to ...") and the analyst's name
    (the last line, in capitals) dropped, headings in capitals turned into sentence case."""
    if not s:
        return ""
    lines = [re.sub(r"\s+", " ", x).strip() for x in re.split(r"\r?\n", H_.unescape(re.sub(r"<[^>]+>", " ", s)))]
    lines = [x for x in lines if x]
    if lines and re.fullmatch(r"[A-Z][A-Z .'\-]+", lines[-1]) and len(lines[-1].split()) <= 4:
        lines = lines[:-1]  # the analyst's name
    out = []
    for p in lines:
        if re.match(r"(?:These|This|The) (?:provisions?|act) (?:is|are) (?:identical|similar|substantially similar)", p):
            continue
        if p.isupper() and len(p) > 3:
            p = p[:1] + p[1:].lower()
            p = re.sub(r"\b(missouri|kansas city|st\. louis|saint louis|mo healthnet)\b", lambda m: m.group(1).title(), p)
            p = p.rstrip(" :") + ":"
        out.append(p)
    return "\n\n".join(out)


# ---- Members ----

def house_members(session):
    """The year's representatives: district -> {name, party, ...} (house/members/<001>.xml)."""
    key = (session, "hm")
    if key not in _CACHE:
        out = {}
        d = os.path.join(folder(session), "house", "members")
        for f in sorted(os.listdir(d)) if os.path.isdir(d) else []:
            try:
                ri = ET.parse(os.path.join(d, f)).getroot().find(".//RepresentativeInfo")
            except (OSError, ET.ParseError):
                continue
            if ri is None:
                continue
            g = lambda t: (ri.findtext(t) or "").strip()
            first, last = g("FirstName"), g("LastName")
            if not last or not g("DistrictNum").isdigit():
                continue
            out[int(g("DistrictNum"))] = {
                "name": f"{first} {last}".strip(), "first": first, "last": last, "party": g("Party"),
                "phone": g("PhoneNumber"), "email": g("EmailAddress"), "office": g("CapitolAddress"),
                "photo": g("PhotoLink"), "post": g("LeadershipPosition"),
                "counties": [(c.text or "").strip() for c in ri.iter("CountyName")],
                "committees": [((c.findtext("CommitteeName") or "").strip(), (c.findtext("CommitteePosition") or "").strip())
                               for c in ri.iter("Committee")]}
        if not out and session - 1 in sessions():
            out = house_members(session - 1)  # next year's prefiled bills, before its member files exist
        _CACHE[key] = out
    return _CACHE[key]


def senators_now():
    if "sn" not in _CACHE:
        try:
            _CACHE["sn"] = json.load(open(os.path.join(P.DATA, "members", "senate.json"), encoding="utf-8")).get("members") or []
        except (OSError, ValueError):
            _CACHE["sn"] = []
    return _CACHE["sn"]


def norm(s):
    return re.sub(r"[^a-z]", "", (s or "").replace("’", "'").lower())


def senate_roster(session):
    """The year's senators: district -> name, from the Senate's bill list (each sponsor with district), the House's
    conferee entries (district 200 + n) and, for senators still serving, the current list."""
    key = (session, "sr")
    if key not in _CACHE:
        out = {}
        for r in senate_list(session).values():
            d = int(r.get("districtNumber") or 0)
            if d and r.get("sponsorLastName"):
                out.setdefault(d, re.sub(r"\s*\(\d+\)$", "", f"{r.get('sponsorFirstName') or ''} {r['sponsorLastName']}".strip()))
        hb = os.path.join(folder(session), "house", "bills")
        for f in sorted(os.listdir(hb)) if os.path.isdir(hb) else []:
            s = open(os.path.join(hb, f), encoding="utf-8").read()
            for name, d in re.findall(r"<SponsorType>SenateConferee</SponsorType><FullName>(.*?)</FullName><District>(\d+)</District>", s):
                out.setdefault(int(d) - 200, H_.unescape(name))
        for m in senators_now():
            d = int(m.get("district") or 0)
            if d in out and norm(out[d].split()[-1]) == norm(m["name"].split()[-1]):
                out[d] = m["name"]
            elif session == max(sessions() or [session]) and d:
                out[d] = m["name"]
        _CACHE[key] = out
    return _CACHE[key]


def last_name(name):
    n = re.sub(r",?\s+(?:Jr|Sr|II|III|IV)\.?$", "", (name or "").strip())
    return n.split()[-1] if n.split() else n


def senate_seat(session, written):
    """A journal's name ("Brown (16)", "O'Laughlin") -> "S:16", else "S?Name"."""
    return senate_seats(session, written)[0]


def senate_seats(session, written):
    """A journal's name -> [seat]; two names the layout ran together with one space ("Bernskoetter Brattin") -> both."""
    one = _seat(session, written)
    if "?" in one and len(written.split()) == 2 and "(" not in written:
        two = [_seat(session, x) for x in written.split()]
        if not any("?" in x for x in two):
            return two
    return [one]


def _seat(session, written):
    m = re.match(r"(.+?)\s*\((\d+)\)$", written.strip())
    if m:
        return f"S:{int(m.group(2))}"
    hits = [d for d, n in senate_roster(session).items() if norm(last_name(n)) == norm(written)
            or norm(n).endswith(norm(written)) and len(norm(written)) > 3]
    return f"S:{hits[0]}" if len(set(hits)) == 1 else f"S?{written.strip()}"


# ---- Senate Journal roll calls ----

DAY = re.compile(r"\b(?:DAY|Day)\s*[-–—]\s*(?:MONDAY|TUESDAY|WEDNESDAY|THURSDAY|FRIDAY|SATURDAY|SUNDAY|Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),\s+([A-Za-z]+ \d{1,2}, \d{4})")
REF = re.compile(r"\b(SJRs?|HJRs?|SBs?|HBs?)\s+((?:\d+)(?:(?:,\s*(?:and\s+)?|\s+and\s+|\s*&\s*)\d+)*)")
GROUPS = [("Y", r"YEAS—"), ("N", r"NAYS—"), ("A", r"Absent—"), ("E", r"Absent with leave—"), ("V", r"Vacancies—")]


def _names(chunk):
    lines = []
    for ln in chunk.split("\n"):
        if re.search(r"Day\s*[-–—]|Journal of the Senate|^\s*\d+\s*$", ln):
            continue
        lines.append(ln)
    t = "\n".join(lines).strip()
    t = re.sub(r"^Senators?\s*", "", t).strip(" —")
    t = re.sub(r"—\s*(?:None|\d+)\s*$", "", t.strip()).strip(" —")
    if not t or t == "None":
        return []
    t = re.sub(r"\((\d+)(?:st|nd|rd|th)? Dist\.?\)", r"(\1)", t)
    t = re.sub(r"\)\s+", ")  ", t)  # "Brown (26) Carter": two names
    return [n.strip(" —") for n in re.split(r"\s{2,}|\n|—", t) if n.strip(" —") and not n.strip().isdigit()]


def senate_rolls(session):
    """Every roll call in the year's Senate Journal: [{date, kind, bills {"SB1", ...}, Y, N, A, E}]. kind: "pass" (read
    the 3rd time and passed), "ccr" (a conference report adopted), "concur" (the House's version adopted), "override",
    else "other"."""
    key = (session, "rolls")
    if key in _CACHE:
        return _CACHE[key]
    out = []
    d = os.path.join(folder(session), "journals", "senate")
    for f in sorted(os.listdir(d)) if os.path.isdir(d) else []:
        try:
            s = gzip.open(os.path.join(d, f), "rt", encoding="utf-8", errors="replace").read()
        except OSError:
            continue
        s = s.replace("’", "'").replace("\f", "\n")
        m = DAY.search(s[:3000])
        if not m:
            continue
        try:
            day = datetime.strptime(m.group(1).title(), "%B %d, %Y").date().isoformat()
        except ValueError:
            continue
        starts = [x.start() for x in re.finditer(r"YEAS—Senator", s)]
        prev_end = 0
        for i, st in enumerate(starts):
            end = starts[i + 1] if i + 1 < len(starts) else len(s)
            block = s[st:end]
            stop = re.search(r"\n\s*(?:Vacancies—[^\n]*)", block)
            block = block[:stop.end()] if stop else block[:3000]
            window = s[prev_end:st]
            prev_end = st + len(block)
            lead = re.sub(r"\s+", " ", window[-600:])
            sentence = lead.split(". ")[-1] if ". " in lead[-400:] else lead[-400:]
            if re.search(r"3rd time and (?:finally )?passed", lead[-300:]):
                kind = "pass"
            elif re.search(r"conference committee report be adopted", lead[-300:]):
                kind = "ccr"
            elif re.search(r"(?:override|notwithstanding the objections)", lead[-300:], re.I):
                kind = "override"
            elif re.search(r"moved that HCS.{0,80}be adopted|moved that HA \d", lead[-300:]):
                kind = "concur"
            else:
                kind = "other"
            refs = list(REF.finditer(window))
            bills = set()
            if refs:
                r = refs[-1]
                typ = re.sub(r"s$", "", r.group(1))
                bills = {f"{typ}{n}" for n in re.findall(r"\d+", r.group(2))}
            pos = {}
            for code, lab in GROUPS:
                mm = re.search(lab, block)
                pos[code] = mm.start() if mm else None
            groups, printed = {}, {}
            order = sorted((p, c) for c, p in pos.items() if p is not None)
            for j, (p, c) in enumerate(order):
                nxt = order[j + 1][0] if j + 1 < len(order) else len(block)
                lab = dict(GROUPS)[c]
                chunk = block[p + len(lab):nxt]
                groups[c] = _names(chunk) if c != "V" else []
                pm = re.search(r"—\s*(\d+)\s*$", chunk.strip())
                printed[c] = int(pm.group(1)) if pm else 0
            tallies = re.findall(r"—(\d+)\s*\n", block)
            out.append({"date": day, "kind": kind, "bills": bills, "first": sorted(bills)[0] if bills else "",
                        "Y": groups.get("Y", []), "N": groups.get("N", []), "A": groups.get("A", []), "E": groups.get("E", []), "printed": printed})
    _CACHE[key] = out
    return out


def find_roll(session, key, day, used, kinds=("pass",)):
    """The journal's roll call on that day for that bill (a passage, or a conference report adopted)."""
    for i, r in enumerate(senate_rolls(session)):
        if i in used or r["date"] != day or key not in r["bills"] or r["kind"] not in kinds:
            continue
        used.add(i)
        return r
    return None


# ---- Wording ----

def comm_name(c):
    """"Commerce, Consumer Protection, Energy & the Environment Committee" -> "Commerce, Consumer Protection, Energy and the
    Environment"; "Rules, Joint Rules, Resolutions & Ethics" -> "Rules, Joint Rules, Resolutions and Ethics"."""
    c = re.sub(r"\s+", " ", (c or "").strip())
    c = re.sub(r"\s*\((?:H|S)\)$", "", c)
    c = re.sub(r"\s+Committee$", "", c)
    c = re.sub(r"\s*\((?:[A-Z][\w'’ .-]*)\)$", "", c)
    c = re.sub(r"\s+w/SCS$", "", c)
    c = c.replace(" & ", " and ")
    return c.strip(" .-")


GATE_COMMS = re.compile(r"^(?:Rules - |Rules, Joint Rules|Fiscal Review$|Fiscal Oversight$)")


def title_of(desc, const):
    t = re.sub(r"\s+", " ", desc or "").strip().rstrip(".")
    if const:
        t = re.sub(r"^Proposes (?:a )?constitutional amendments? (?:relating to |to |that |establishing |modifying )?", "", t, flags=re.I)
        t = re.sub(r"^Amends the Constitution to ", "", t, flags=re.I)
        return f"Constitutional amendment: {t[:1].lower() + t[1:] if t[:2] != t[:2].upper() else t}"
    return t[:1].upper() + t[1:]


def sentence_case(s):
    s = (s or "").strip()
    return s[:1] + s[1:].lower() if s.isupper() else s


# ---- One bill's steps, from either source ----

class Walk:
    """Follows a bill through both houses, collecting steps (date, house or "G", wording, kind) and what they decide."""

    def __init__(self, session, key):
        self.session, self.key = session, key
        self.origin = "H" if key.startswith("H") else "S"
        self.where = self.origin
        self.place = "desk"
        self.comm = {"S": None, "H": None}
        self.first_comm = {"S": None, "H": None}
        self.refs = []
        self.steps = []
        self.passed, self.changed = set(), set()
        self.reported = set()
        self.tafp = self.sent = self.law = self.vetoed = self.items = self.nosign = self.to_sos = self.overridden = False
        self.combined = ""
        self.withdrawn = False
        self.fvotes, self.cvotes = [], []
        self.used = set()

    def add(self, d, h, wording, kind):
        self.steps.append((d, h, wording, kind))

    def floor_vote(self, d, h, tally, roll=None):
        if roll:
            seats = {c: [x for n in roll[c] for x in senate_seats(self.session, n)] for c in "YNAE"}
            listed = [[m, c] for c in ("N", "A", "E") for m in seats[c]]
            STATS["names"] += sum(len(v) for v in seats.values())
            STATS["unmatched names"] += sum(1 for v in seats.values() for m in v if "?" in m)
            self.fvotes.append([h, "F", None, d, len(seats["Y"]), len(seats["N"]), listed])
        elif tally:
            self.fvotes.append([h, "F", None, d, tally[0], tally[1], []])

    def referral(self, d, h, c, how="ref"):
        c = comm_name(c)
        self.where = h
        self.comm[h] = c
        self.place = "committee"
        self.refs.append((h, c))
        if not GATE_COMMS.match(c) and self.first_comm[h] is None:
            self.first_comm[h] = c
        if how == "ref":
            self.add(d, h, f"REFERRED TO {c.upper()}", "ref")
        else:
            self.add(d, h, f"Sent back to committee: the {c} Committee", "recommitted")

    def report(self, d, h, sub, consent, tally=None):
        c = self.comm.get(h)
        self.reported.add(h)
        self.place = "floor"
        what = " (with a committee substitute)" if sub else ""
        to = " for the consent calendar" if consent else ""
        self.add(d, h, "REPORTED", "reported")
        self.add(d, h, f"The {c + ' ' if c else ''}Committee voted do pass{what}{to}" + (f", {tally[0]}-{tally[1]}" if tally else ""), "report")
        if tally and c:
            self.cvotes.append([h, "C", c, d, tally[0], tally[1], []])
        self.comm[h] = None

    def commfail(self, d, h, tally=None):
        c = self.comm.get(h)
        self.add(d, h, f"The {c + ' ' if c else ''}Committee voted it down" + (f", {tally[0]}-{tally[1]}" if tally else ""), "commfail")
        if tally and c:
            self.cvotes.append([h, "C", c, d, tally[0], tally[1], []])

    def passage(self, d, h, tally=None, amended=False, conference=False):
        self.where = h
        roll = find_roll(self.session, self.key, d, self.used, ("pass",)) if h == "S" else None
        if h == "S":
            STATS["senate passages"] += 1
            STATS["matched"] += bool(roll)
        if roll:
            tally = tuple(sum(len(senate_seats(self.session, n)) for n in roll[c]) for c in "YN") + (0,)
        y_n = f", {tally[0]}-{tally[1]}" if tally else ""
        if h in self.passed and (h == self.origin and OTHER[h] in self.passed or conference):
            self.add(d, h, f"The {HOUSE[h]} passed it again{y_n}" + (" (as the conference committee proposed)" if conference
                                                                     else " (with the other house's changes)"), "final")
        else:
            self.passed.add(h)
            if h != self.origin and amended:
                self.changed.add(h)
            self.add(d, h, f"PASSED {HOUSE[h].upper()}", "pass")
            if tally:
                self.add(d, h, f"The {HOUSE[h]} vote: {tally[0]}-{tally[1]}" + (" (as amended)" if amended else ""), "tally")
        self.floor_vote(d, h, tally, roll)
        if h == self.origin:
            self.place = "desk"

    def defeat(self, d, h, tally=None):
        self.add(d, h, f"The {HOUSE[h]} voted it down" + (f", {tally[0]}-{tally[1]}" if tally else ""), "defeat")
        if tally:
            self.fvotes.append([h, "F", None, d, tally[0], tally[1], []])

    def reconsider(self, d, h):
        prior = [s for s in self.steps if s[1] == h and s[3] in ("pass", "defeat", "final")]
        if prior and prior[-1][3] in ("pass",):
            self.passed.discard(h)
            self.changed.discard(h)
        self.add(d, h, f"The {HOUSE[h]} voted to reconsider its vote", "reconsider")

    def received(self, d, h, wording=None):
        self.where = h
        self.place = "desk"
        self.add(d, h, wording or f"Received in the {HOUSE[h]}", "received")

    def tafp_step(self, d, tally=None):
        self.tafp = True
        self.add(d, self.where, "Truly agreed to and finally passed: passed both houses", "tafp")

    def governor(self, d, line):
        l = line.lower()
        if l.startswith("delivered to governor"):
            if not self.const:
                self.sent = True
            self.add(d, "G", "DELIVERED TO GOVERNOR", "sent")
        elif re.match(r"(?:approved|signed) by governor", l):
            self.law = True
            self.add(d, "G", "Signed by the governor", "signed")
        elif l.startswith("vetoed in part"):
            self.law = self.items = True
            self.add(d, "G", "Signed by the governor, with items vetoed (a line-item veto)", "itemveto")
        elif re.match(r"vetoed(?: by governor)?\b", l):
            self.vetoed = True
            self.add(d, "G", "VETOED", "vetoed")
        elif "governor took no action" in l:
            self.law = self.nosign = True
            self.add(d, "G", "Became law without the governor's signature", "nosign")
        elif l.startswith("letter of approval"):
            self.add(d, "G", "The governor sent a letter of approval", "other")
        elif l.startswith("delivered to secretary of state"):
            self.to_sos = True
            if self.const:
                self.add(d, "G", "Sent to the Secretary of State, for the voters", "sos")
            else:
                self.add(d, "G", "Delivered to the Secretary of State", "sosroutine")
        elif "article iv, section 27" in l:
            self.add(d, "G", "The governor restricted spending under it (Article IV, Section 27)", "other")
        else:
            self.add(d, "G", line, "other")

    @property
    def const(self):
        return "JR" in self.key


SUB = re.compile(r"^(?:(?:H|S)CS(?:#\d+)?|HS|SS(?:#\d+)?)\s+", re.I)


def walk_house_xml(w, actions):
    """The House export's actions (both houses) -> steps."""
    for d, seq, t, comments, tally in actions:
        tag = re.search(r"\((H|S|G)\)\s*$", t)
        h = tag.group(1) if tag else w.where
        base = re.sub(r"\s*\((?:H|S|G)\)\s*$", "", t).strip()
        bl = base.lower()
        if h == "G" or re.match(r"(?:delivered to governor|message received from the governor|letter of approval|governor took no action)", bl):
            w.governor(d, base)
            continue
        if re.match(r"prefiled", bl):
            w.add(d, "H", "Prefiled", "prefile")
            continue
        if re.match(r"(?:introduced and )?read first time", bl):
            if h == w.origin and not any(s[3] == "intro" for s in w.steps):
                w.where = h
                w.add(d, h, f"Introduced in the {HOUSE[h]}", "intro")
            elif h != w.where:
                w.received(d, h)
            continue
        m = re.match(r"reported to the (senate|house) and first read", bl)
        if m:
            if not (w.steps and w.steps[-1][3] == "received" and w.steps[-1][1] == m.group(1)[0].upper()):
                w.received(d, m.group(1)[0].upper())
            continue
        if re.match(r"delivered to the senate", bl):
            if not any(s[3] == "received" and s[1] == "S" for s in w.steps[-6:]):
                w.received(d, "S")
            continue
        if re.match(r"reported to the house with", bl):
            w.received(d, "H", f"Returned to the House with the Senate's changes ({comments})" if comments else
                       "Returned to the House with the Senate's changes")
            continue
        m = re.match(r"(?:second read and referred|referred|re-referred to committee|re-committed to committee|committed to):\s*(.+)$", base, re.I)
        if m:
            w.referral(d, h, m.group(1), "ref" if re.match(r"(?:second read|referred)", bl) else "back")
            continue
        if re.match(r"(?:voted to )?return(?:ed)? to (?:the )?committee of origin", bl):
            c = w.first_comm.get(h)
            if c:
                w.referral(d, h, c, "back")
            continue
        if re.match(r"(?:public hearing (?:completed|held|continued))", bl):
            w.add(d, h, f"Public hearing held{' by the ' + w.comm[h] + ' Committee' if w.comm.get(h) else ''}", "hearing")
            continue
        if re.match(r"public hearing scheduled|executive session|house message|senate message|taken up|title of bill|laid over"
                    r"|action postponed|read second time|signed by (?:house speaker|president pro tem)|bill reconsidered$|see comments"
                    r"|placed on informal calendar|motion adopted|motion to adopt withdrawn|conferee removed", bl) and not re.match(r"taken up for third", bl):
            if bl.startswith("signed by"):
                w.add(d, h, "Signed by the Speaker" if "speaker" in bl else "Signed by the President Pro Tem", "enrolled")
            elif re.match(r"placed on informal calendar", bl):
                w.add(d, h, "Placed on the informal calendar" + (f" ({comments})" if comments else ""), "calendar")
            elif re.match(r"bill reconsidered", bl):
                w.reconsider(d, h)
            continue
        if re.match(r"taken up for third", bl):
            continue
        if re.search(r"voted do pass", bl):
            continue  # the report follows
        m = re.match(r"((?:(?:H|S)CS(?:#\d+)?|HS) )?reported do pass(.*)$", base, re.I)
        if m:
            w.report(d, h, bool(m.group(1)), "consent" in (m.group(2) or "").lower() and "not consent" not in (m.group(2) or "").lower(), tally)
            continue
        if re.search(r"reported do not pass|voted do not pass|motion to do pass failed", bl):
            w.commfail(d, h, tally)
            continue
        if re.match(r"placed (?:back )?on (?:the )?(?:informal|formal)? ?.*calendar|dropped from calendar|objection filed", bl):
            w.place = "floor" if w.place != "committee" else w.place
            w.add(d, h, base[:1] + base[1:].lower() if base.isupper() else base, "calendar")
            continue
        m = re.match(r"((?:(?:H|S)CS(?:#\d+)?|HS|SS(?:#\d+)?)) (adopted|offered|withdrawn|defeated)", base, re.I)
        if m:
            if m.group(2).lower() == "adopted" and h != w.origin:
                w.changed.add(h)
            w.add(d, h, f"{m.group(1)} {m.group(2).lower()}" + (f" ({comments})" if comments else ""), "amend")
            continue
        if re.match(r"perfection defeated", bl):
            w.defeat(d, h, tally)
            continue
        if re.match(r"(?:re-)?perfected", bl):
            w.place = "floor"
            w.add(d, h, "Perfected" + (" with amendments" if "amend" in bl else " by consent" if "consent" in bl else "")
                  + " (approved on the first floor vote; a final vote follows)", "perfected")
            continue
        if re.match(r"third read and passed", bl):
            w.passage(d, h, tally, amended="amend" in bl)
            continue
        if re.match(r"third read and defeated", bl):
            w.defeat(d, h, tally)
            continue
        if re.match(r"motion to reconsider adopted", bl):
            w.reconsider(d, h)
            continue
        if re.match(r"house adopts conference committee report|senate adopts conference committee report", bl):
            hh = "H" if bl.startswith("house") else "S"
            w.add(d, hh, f"The {HOUSE[hh]} adopted the conference committee's report" + (f", {tally[0]}-{tally[1]}" if tally else ""), "ccr")
            roll = find_roll(w.session, w.key, d, w.used, ("ccr",)) if hh == "S" else None
            continue
        if re.match(r"house adopts$|house concurs|senate concurs", bl):
            hh = "H" if bl.startswith("house") else "S"
            w.add(d, hh, f"The {HOUSE[hh]} agreed to the {HOUSE[OTHER[hh]]}'s changes" + (f" ({comments})" if comments else ""), "concur")
            if tally:
                w.passage(d, hh, tally)
            continue
        if re.match(r"house refuses to adopt|senate refuses|house refuses|senate grants|house grants", bl):
            hh = "S" if bl.startswith("senate") else "H"
            if re.match(r"house refuses to adopt", bl):
                words = "refused to adopt the Senate's changes and asked for a conference"
            elif re.match(r"senate refuses to recede", bl):
                words = "refused to drop its changes and agreed to a conference"
            elif "refuses" in bl:
                words = "refused the other house's position"
            else:
                words = "agreed to a conference"
            w.add(d, hh, f"The {HOUSE[hh]} {words}", "noconcur" if "refuses to adopt" in bl else "conf")
            continue
        if re.search(r"conference committee|conferees", bl):
            if re.search(r"appointed", bl):
                w.add(d, h, f"{HOUSE[h]} conferees appointed", "conf")
            elif re.search(r"exceed", bl):
                w.add(d, h, f"The {HOUSE[h]}'s conferees allowed to go beyond the differences", "conf")
            # distributing and submitting the report aren't news
            continue
        if re.match(r"truly agreed to and finally passed", bl):
            # The final vote: in the house that passed it last (its tally repeats the passage or concurrence vote).
            last = [s for s in w.steps if s[3] in ("pass", "final", "concur", "ccr") and s[0] == d]
            if tally and not last:
                w.passage(d, w.where, tally, conference=any(s[3] == "ccr" for s in w.steps))
            elif tally and any(s[3] == "ccr" for s in last) and not any(s[3] in ("pass", "final") for s in last):
                w.passage(d, last[-1][1], tally, conference=True)
            w.tafp_step(d, tally)
            continue
        if re.search(r"failed to pass over veto", bl):
            w.add(d, h, f"The {HOUSE[h]} voted on overriding the veto: it failed" + (f", {tally[0]}-{tally[1]}" if tally else ""), "overridefail")
            continue
        if re.search(r"passed over veto|veto overridden", bl):
            w.add(d, h, f"The {HOUSE[h]} voted to override the veto" + (f", {tally[0]}-{tally[1]}" if tally else ""), "overridevote")
            if sum(1 for s in w.steps if s[3] == "overridevote") >= 2:
                w.overridden = True
            continue
        if re.match(r"withdrawn", bl):
            w.withdrawn = True
            w.add(d, h, "Withdrawn by its sponsor", "withdrawn")
            continue
        if re.match(r"emergency clause", bl):
            w.add(d, h, base + (f", {tally[0]}-{tally[1]}" if tally else ""), "other")
            continue
        w.add(d, h, base + (f" ({comments})" if comments and len(comments) < 80 else ""), "other")


def house_of(line, default):
    m = re.search(r"(?:^|\s)(S|H)(?=\s|$)", line)
    return m.group(1) if m else default


def walk_senate_page(w, actions, house_tallies):
    """The Senate page's actions (both houses, no tallies) -> steps. house_tallies: the House's floor tallies for the
    bill by day, from its SenateActList."""
    for d, t, journal in actions:
        tl = t.lower()
        h = house_of(t, w.where)
        if re.match(r"(?:delivered to governor|signed by governor|letter of approval|governor took no action|delivered to secretary of state|vetoed)", tl):
            w.governor(d, t)
            continue
        if tl == "prefiled":
            w.add(d, "S", "Prefiled", "prefile")
            continue
        if re.match(r"s first read", tl):
            w.where = "S"
            w.add(d, "S", "Introduced in the Senate", "intro")
            continue
        if re.match(r"h first read", tl):
            w.received(d, "H")
            continue
        if re.match(r"(?:h|s) second read$", tl):
            continue
        m = re.match(r"(?:second read and referred|(?:hcs(?:#\d+)? )?referred|re-referred|committed to) (S|H) (.+)$", t, re.I)
        if m:
            w.referral(d, m.group(1).upper(), m.group(2), "back" if re.match(r"re-|committed", tl) else "ref")
            continue
        m = re.match(r"returned to (?:the )?committee of origin(?: - (?:H |S )?(.+))?", t, re.I)
        if m or re.match(r"voted to return to (?:the )?committee of origin", tl):
            c = (m.group(1) if m and m.group(1) else None) or w.first_comm.get(h)
            if c and not re.match(r"\(", c):
                w.referral(d, h, c, "back")
            continue
        if re.match(r"hearing conducted", tl):
            w.add(d, h, f"Public hearing held{' by the ' + w.comm[h] + ' Committee' if w.comm.get(h) else ''}", "hearing")
            continue
        if re.match(r"hearing (?:cancelled|scheduled)|executive session|(?:h|s) distributes|.*\bdistributes cc|informal calendar|formal calendar"
                    r"|reported truly|reported duly enrolled|in conference$|message received|requests to recede|h calendar|updated fiscal note"
                    r"|s bills with h amendments|h informal calendar", tl):
            if re.search(r"calendar", tl) and w.place != "committee":
                w.place = "floor"
            if re.match(r"updated fiscal note", tl):
                w.place = "floor"
                w.comm[h] = None
            continue
        if re.match(r"bill placed on (?:h )?(?:informal|formal) calendar|bill placed on h formal", tl):
            w.place = "floor" if w.place != "committee" else w.place
            w.add(d, h, "Placed on the informal calendar" if "informal" in tl else "Placed on the calendar", "calendar")
            continue
        if re.match(r"(?:(?:h|s)cs(?:#\d+)? )?voted do pass", tl):
            continue
        m = re.match(r"(SCS )?reported from (S|H) (.+?)(?: w/SCS)?(?: - Consent)?$", t, re.I)
        if m:
            w.report(d, m.group(2).upper(), "w/SCS" in t or bool(m.group(1)), "consent" in tl)
            continue
        m = re.match(r"((?:hcs|hs)(?:#\d+)? )?reported do pass(?:-placed on .*consent calendar)?(?: - consent)? (S|H) (.+?)(?: - Consent)?$", t, re.I)
        if m:
            tally = house_tallies.get((d, "report"))
            w.report(d, m.group(2).upper(), bool(m.group(1)), "consent" in tl, tally)
            continue
        if re.match(r"reported do pass", tl):
            w.report(d, h, False, "consent" in tl)
            continue
        if re.match(r"motion to pass bill as consent taken by .* - consent vote adopted", tl):
            mm = re.search(r"taken by (S|H) ", t)
            w.report(d, mm.group(1) if mm else h, False, True)
            continue
        if re.match(r"voted do not pass|motion to vote bill (?:do pass|as consent) failed", tl):
            mm = re.search(r"\b(S|H) ", t[10:])
            w.commfail(d, mm.group(1) if mm else h)
            continue
        if re.match(r"(?:re-)?perfected", tl):
            w.place = "floor"
            w.add(d, "S" if w.where == "S" else w.where, "Perfected" + (" with amendments" if "amended" in tl else "")
                  + " (approved on the first floor vote; a final vote follows)", "perfected")
            continue
        m = re.match(r"(ccs )?(S|H) third read and passed(.*)$", t, re.I)
        if m:
            hh = m.group(2).upper()
            tally = house_tallies.get((d, "pass")) if hh == "H" else None
            if m.group(1):
                w.passage(d, hh, tally, conference=True)
            else:
                w.passage(d, hh, tally, amended="as amended" in tl or hh in w.changed)
            continue
        if re.match(r"defeated on (?:h )?third reading", tl):
            w.defeat(d, "H" if " h " in f" {tl} " else w.where)
            continue
        if re.match(r"motion to reconsider (?:h |s )?third reading vote", tl):
            mm = re.search(r"\b(S|H) adopted", t)
            if mm or "adopted" in tl:
                w.reconsider(d, mm.group(1) if mm else w.where)
            continue
        m = re.match(r"(hcs|hs|scs|ss)(?:#\d+)?(?: for (?:hcs|scs))?,?(?: as amended,?)? (H|S) adopted", t, re.I)
        if m:
            hh = m.group(2).upper()
            if hh != w.origin:
                w.changed.add(hh)
            w.add(d, hh, f"{t.split(' ' + hh + ' adopted')[0]} adopted", "amend")
            continue
        m = re.match(r"(?:HA|SA) \d+.*? (H|S) (?:offered & )?adopted", t)
        if m:
            if m.group(1) != w.origin:
                w.changed.add(m.group(1))
            continue  # amendments aren't news
        m = re.match(r"(S|H) concurs in (.+)$", t)
        if m:
            hh = m.group(1)
            w.add(d, hh, f"The {HOUSE[hh]} agreed to the {HOUSE[OTHER[hh]]}'s changes", "concur")
            roll = find_roll(w.session, w.key, d, w.used, ("concur", "pass"))
            continue
        m = re.match(r"(S|H) (refuses|recedes|requests|grants|dissolves)(.*)$", t, re.I)
        if m:
            hh = m.group(1).upper()
            words = {"refuses": "refused to agree to the other house's changes" if "concur" in tl else "refused to drop its changes",
                     "recedes": "dropped its changes (receded)", "requests": "asked the other house to recede or meet in conference",
                     "grants": "agreed to a conference", "dissolves": "dissolved the conference committee"}[m.group(2).lower()]
            if m.group(2).lower() == "recedes" and hh != w.origin:
                w.changed.discard(hh)
            w.add(d, hh, f"The {HOUSE[hh]} {words}", "noconcur" if m.group(2).lower() == "refuses" else "conf")
            continue
        if re.match(r"(?:senate|house) conferees (?:re-)?appointed", tl):
            hh = "S" if tl.startswith("senate") else "H"
            w.add(d, hh, f"{HOUSE[hh]} conferees appointed", "conf")
            continue
        m = re.match(r"(S|H) adopt(?:s|ed) CCR", t)
        if m:
            hh = m.group(1)
            w.add(d, hh, f"The {HOUSE[hh]} adopted the conference committee's report", "ccr")
            if hh == "S":
                find_roll(w.session, w.key, d, w.used, ("ccr",))
            continue
        if re.match(r"truly agreed to and finally passed", tl):
            w.tafp_step(d)
            continue
        if re.match(r"signed by (?:senate president pro tem|house speaker)", tl):
            w.add(d, "S" if "senate" in tl else "H", "Signed by the President Pro Tem" if "senate" in tl else "Signed by the Speaker", "enrolled")
            continue
        m = re.match(r"bill combined (?:\()?w/\s*\(?(.+?)\)?\)?(?:\s+[A-Z][\w ,]+Committee)?$", t, re.I)
        if m:
            nums = re.findall(r"\d+", m.group(1))
            typ = "SJR" if "SJR" in m.group(1) else "SB"
            lead = f"{typ}{nums[0]}" if nums else ""
            if lead and lead != w.key:
                w.combined = lead
                w.add(d, h, f"Combined into {num_text(lead)} ({m.group(1).strip('() ')})", "combined")
            else:
                w.add(d, h, f"Combined with other bills ({m.group(1).strip('() ')})", "other")
            continue
        if re.match(r"bill withdrawn", tl):
            w.withdrawn = True
            w.add(d, "S", "Withdrawn by its sponsor", "withdrawn")
            continue
        if re.search(r"\boffered\b|laid on the table|\bwithdrawn\b|point of order|motion to lay|motion to reconsider|\bdefeated\b|removed s consent"
                     r"|conferees allowed|substitute motion|motion to concur|motion to allow|consent vote reconsidered|committee vote reconsidered"
                     r"|laid over|executive session action postponed|taken up", tl):
            if re.search(r"motion to reconsider (?:the )?committee vote|committee vote reconsidered", tl):
                pass
            continue
        w.add(d, h, t, "other")


# ---- One bill ----

def record(session, b, src):
    p = b["key"]
    w = Walk(session, p)
    const = w.const
    if src == "house":
        walk_house_xml(w, b["actions"])
        if b.get("parent") and b["parent"] != p:
            w.combined = b["parent"]
            last = w.steps[-1][0] if w.steps else f"{session}-01-01"
            w.add(last, "H", f"Combined into {num_text(b['parent'])}, which went on in its place", "combined")
    else:
        ht = {}
        for d, t, tally in (senate_acts(session).get(p) or {}).get("actions") or []:
            if not tally:
                continue
            tl = t.lower()
            if re.match(r"third read and passed.*\(h\)", tl) or re.match(r"house adopts", tl):
                ht[(d, "pass")] = tally
            elif re.search(r"reported do pass", tl):
                ht[(d, "report")] = tally
        walk_senate_page(w, b["actions"], ht)

    origin, other = w.origin, OTHER[w.origin]
    steps = w.steps
    passed = set(w.passed)
    both = w.tafp or w.sent or w.law or w.vetoed or (const and w.to_sos)
    law = w.law and not const and (not w.vetoed or w.overridden or w.items)
    if const:
        stage = 3 if both else 2 if passed else None
    elif law:
        stage = 5
    elif w.vetoed:
        stage = 6
    elif w.sent:
        stage = 4
    elif both:
        stage = 3
    elif passed:
        stage = 2
    else:
        stage = None
    if stage is not None and stage >= 3:
        passed = {"S", "H"}
    if stage is None:
        stage = 1 if w.place == "floor" else 0

    title = title_of(b["title"] or sentence_case(b.get("short")), const)
    topics = ["const"] if const else []
    for h_, c in w.refs:
        tp = P.COMMITTEE_TOPICS.get(c)
        if tp and tp not in topics:
            topics.append(tp)
    for s in (b.get("subjects") or [])[:6]:
        for tp in P.SUBJECT_TOPICS.get(s.upper(), []):
            if tp not in topics:
                topics.append(tp)
    if not topics or topics == ["const"]:
        topics += [k for k, rx in P.TOPIC_WORDS.items() if rx.search(f"{title} {(b.get('summary') or '')[:300]}") and k not in topics]
    topics = list(dict.fromkeys(t for t in topics if t != "const" or const))

    # Sponsors: the sponsor first, then co-sponsors (House bills).
    spons = [x for x in b["sponsors"] if x[3] == "Sponsor"]
    cosp = [x for x in b["sponsors"] if x[3] == "Co-Sponsor"]
    sponsor, district = (spons[0][0], spons[0][2]) if spons else ("—", 0)
    cos = [x[0] for x in cosp if x[0] != sponsor]
    parties = _PARTIES.setdefault(session, {})
    hm = house_members(session)
    for name, h_, dd, _ in spons[:1] + cosp:
        party = None
        if h_ == "H" and dd in hm and norm(last_name(hm[dd]["name"])) == norm(last_name(name)):
            party = hm[dd]["party"]
        elif h_ == "S":
            m = next((x for x in senators_now() if int(x.get("district") or 0) == dd and norm(last_name(x["name"])) == norm(last_name(name))), None)
            party = m["party"] if m else None
        if party:
            parties[(h_, name)] = "R" if "Republican" in party else "D" if "Democrat" in party else None

    cur = w.where if w.where in ("S", "H") else origin
    if w.combined and stage < 2:
        dsc = f"Combined into {num_text(w.combined)}"
    elif w.withdrawn and stage == 0:
        dsc = "Withdrawn"
    elif stage == 0:
        dsc = f"In {HOUSE[cur]} committee" if w.place == "committee" else "Introduced"
    elif stage == 1:
        dsc = f"On the {HOUSE[cur]} floor"
    else:
        dsc = {2: f"Passed the {HOUSE[origin] if origin in passed else HOUSE[other]}", 3: "Passed both houses",
               4: "On the governor's desk", 5: "Became law", 6: "Vetoed"}[stage]
        if const and stage == 3:
            dsc = "Passed both houses: goes to the voters"
    comm_now = w.comm.get(cur) if w.place == "committee" and stage in (0, 2) else None

    def dates(test, mode="last"):
        ds = sorted({s[0] for s in steps if test(s) and s[0]})
        return {"first": ds[0], "last": ds[-1], "all": ";".join(ds)}[mode] if ds else ""

    action_dates = [s[0] for s in steps if s[0]]
    what = None
    if b.get("summary"):
        st, version = b["summary"], ""
        mv = re.match(r"([A-Z#\d/&, ]*?(?:SBs?|SJRs?|HBs?|HJRs?) [\d, &and]+?)\s*-\s*(?=This|The|Under|Currently|[A-Z])", st)
        if mv:
            version, st = mv.group(1).strip(), st[mv.end():]
        # Lead with what the bill does when the summary opens with current law ("Currently, ... This act ...").
        paras = st.split("\n\n")
        if paras and re.match(r"(?:Currently|Current law|Under current law|Under existing law|Existing law)", paras[0]):
            sents = re.split(r"(?<=[.)])\s+(?=[A-Z])", paras[0])
            does = [x for x in sents if re.match(r"This (?:act|joint resolution)", x)]
            if does:
                paras[0] = " ".join(does + [x for x in sents if x not in does])
            st = "\n\n".join(paras)
        what = {"statement": st, "label": "From the Missouri Senate's summary of the bill's current version"
                + (f" ({version.replace('/', ' ')})." if version else ".")}
    first_ref = w.first_comm.get(origin)
    link = f"https://house.mo.gov/Bill.aspx?bill={p}&year={session}&code=R" if src == "house" else \
        (senate_list(session).get(p) or {}).get("mainBillUrl") or "https://www.senate.mo.gov/BillTracking/Bills/BillList"
    rec = {
        "nums": [p], "base": [p], "prev": earlier(session, b),
        "title": title, "summary": sentence_case(b.get("short")), "act": "", "lawCode": "", "law": None, "laws": [],
        "comms": sorted({f"{h_} · {c}" for h_, c in w.refs}), "topics": topics, "places": [],
        "narrow": P.narrow_kind(title),
        "commFate": "passed" if w.reported or passed else "none", "mainTopic": topics[0] if topics else "",
        "local": "local" in topics, "senDeleg": False, "asmDeleg": False,
        "budget": bool(re.search(r"\bappropriat", f"{b['title']} {b.get('short')}", re.I)) and not const,
        "passedS": "S" in passed, "passedA": "H" in passed, "program": None,
        "stage": stage, "passedIn": (HOUSE[origin] if origin in passed else HOUSE[other]) if stage == 2 else None,
        "chapter": None,
        "veto": None, "memo": "", "vetoMemo": None,
        "simText": f"{title} {b['title']} {(b.get('summary') or '')[:600]}",
        "comm": comm_now if stage == 0 else None,
        "first": min(action_dates, default=f"{session}-01-01"),
        "last": max(action_dates, default=f"{session}-01-01"),
        "cosp": len(cos),
        "keyDates": [
            dates(lambda s: s[3] == "reported", "first"),
            dates(lambda s: s[2] == "PASSED SENATE", "all"),
            dates(lambda s: s[2] == "PASSED HOUSE", "all"),
            "",
            dates(lambda s: s[3] == "sent") if stage >= 4 else "",
            dates(lambda s: s[3] in ("signed", "itemveto", "nosign", "overridelaw")) if stage == 5 else "",
            dates(lambda s: s[3] == "vetoed"),
        ],
        "votes": w.fvotes + w.cvotes, "firstComms": [(origin, first_ref, bool(origin in w.reported) or origin in passed)] if first_ref else [],
        "vers": [{"p": p, "sponsor": sponsor, "district": district or 0, "cosponsors": cos,
                  "primes": 1, "cosp": len(cos), "statusDesc": dsc, "committee": comm_now,
                  "actions": [[s[0], s[2]] for s in steps], "link": link}],
    }
    if stage == 5 and not rec["keyDates"][5]:
        rec["keyDates"][5] = rec["last"]
    return rec, what


def stub(b):
    """A previous year's appropriation bill filed under this year with only the governor's spending restrictions."""
    return b["actions"] and all(re.match(r"Message Received from the Governor", a[2]) for a in b["actions"])


def bills(session):
    """[(key, source, parsed bill)] for the year: House bills and joint resolutions, then the Senate's."""
    key = (session, "bills")
    if key in _CACHE:
        return _CACHE[key]
    out = []
    hb = os.path.join(folder(session), "house", "bills")
    for f in os.listdir(hb) if os.path.isdir(hb) else []:
        k = f[:-4]
        if not KIND.match(k):
            continue
        b = house_bill(session, k)
        if not b or not b["actions"] or stub(b):
            continue
        out.append((k, "house", b))
    for k in senate_list(session):
        if not KIND.match(k):
            continue
        b = senate_bill(session, k)
        if not b or not b["actions"]:
            continue
        out.append((k, "senate", b))
    order = {"HB": 0, "HJR": 1, "SB": 2, "SJR": 3}
    out.sort(key=lambda x: (order[KIND.match(x[0]).group(1)], int(KIND.match(x[0]).group(2))))
    _CACHE[key] = out
    return out


def load_session(session):
    """Read one year's bills and return (records, bill number -> record index, fetched time, delegation)."""
    recs, index, whats = [], {}, {}
    for k, src, b in bills(session):
        rec, what = record(session, b, src)
        index[k] = len(recs)
        recs.append(rec)
        if what:
            whats[k] = what
    try:
        json.dump(whats, open(os.path.join(P.DATA, f"texts_{session}.json"), "w"), ensure_ascii=False)
    except OSError:
        pass
    paths = [os.path.join(folder(session), "state", n) for n in ("house.json", "senate.json")] + [os.path.join(P.DATA, "last_checked")]
    times = [os.path.getmtime(x) for x in paths if os.path.exists(x)]
    fetched = datetime.fromtimestamp(max(times), ZoneInfo(P.TIMEZONE)).strftime("%Y-%m-%d %H:%M") if times else ""
    return recs, index, fetched, {"SENATE": [], "ASSEMBLY": []}


# ---- Earlier years ----

_KEYS = {}


def _key(b):
    """The description and the sponsor's surname, for descriptions specific enough (five words or more)."""
    t = re.sub(r"[^a-z0-9 ]", "", re.sub(r"\s+", " ", (b.get("title") or "").lower())).strip()
    sp = [x for x in b["sponsors"] if x[3] == "Sponsor"]
    if len(t.split()) < 5 or re.search(r"\bappropriat", t) or not sp:
        return ""
    return f"{b['key'][0]}|{t}|{norm(last_name(sp[0][0]))}"


def _keys(session):
    if session not in _KEYS:
        out = defaultdict(list)
        for k, src, b in bills(session):
            acts = " ".join(a[2] if src == "house" else a[1] for a in b["actions"])
            if re.search(r"Approved by Governor|Signed by Governor|Vetoed in Part|Governor took no action", acts):
                continue  # a law isn't tried again
            kk = _key(b)
            if kk:
                out[kk].append(k)
        _KEYS[session] = out
    return _KEYS[session]


def earlier(session, b):
    """The same bill in the two years before: the same description and sponsor, one bill with them in each year. Never
    appropriations, nor a bill that became law."""
    out = set()
    kk = _key(b)
    if not kk:
        return out
    for y in (session - 1, session - 2):
        if y not in sessions():
            continue
        old, mine = _keys(y).get(kk, []), _keys(session).get(kk, [])
        if len(old) == 1 and len(mine) <= 1:
            out.add((y, old[0]))
            break
    return out


def parties(session, recs):
    if session not in _PARTIES:
        load_session(session)
    return {k: v for k, v in _PARTIES.get(session, {}).items() if v in ("D", "R")}


def agendas(session):
    return {}


if __name__ == "__main__":
    import sys
    for s in ([int(sys.argv[1])] if len(sys.argv) > 1 else sessions()):
        STATS.clear()
        recs = load_session(s)[0]
        st = Counter(r["stage"] for r in recs)
        laws = [r["nums"][0] for r in recs if r["stage"] == 5]
        print(s, len(recs), dict(sorted(st.items())), "laws", len(laws), "(HB", sum(1 for x in laws if x.startswith("H")),
              "SB", sum(1 for x in laws if x.startswith("S")), ") items vetoed",
              sum(1 for r in recs if any("line-item" in a[1] for a in r["vers"][0]["actions"])),
              "without signature", sum(1 for r in recs if any("without the governor" in a[1] for a in r["vers"][0]["actions"])),
              "amendments to the voters", [r["nums"][0] for r in recs if "const" in r["topics"] and r["stage"] == 3],
              dict(STATS))
