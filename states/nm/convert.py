"""New Mexico's bills (downloaded by states/nm/fetch.py from www.nmlegis.gov) in the shape build_data.py reads. A page a
year: the Legislature meets once a year from the third Tuesday of January, 60 days in odd years and 30 in even years
(the budget, bills on the governor's call and vetoed bills only), and bills die when the session ends. House and Senate
bills (HB, SB), plus the joint resolutions that propose constitutional amendments (HJR, SJR whose short title ends in
", CA"); other joint resolutions, memorials and special sessions are left out.

Each bill's page (data/nm/<year>/bills/HB5.html) has the short title (in capitals), sponsors in order (by sponsor code),
the current location ("Chaptered", "Vetoed", "Pocket Veto", "Died (API.)"), the actions in the Legislature's abbreviated
code ("ActionText": "[5] HHHC/HJC-HHHC [8] DP-HJC [11] DP/a [12] fl/a- PASSED/H (64-0) ... SGND BY GOV (Mar. 21) Ch. 13.";
the key is data/nm/abbreviations.html) and the same steps spelled out, each with its legislative and calendar day:
- "Sent to HHHC - Referrals: HHHC/HJC": the committees the bill goes to, in order; there's no line when it moves on to the
  next one, so the referral list is followed: a committee's report sends it to the next, the last one's to the floor.
  "Referred to: HEC/HGEIC", "re-ref HTRC" and "Sent to committee - Referrals: SFC" replace the list; "HAFC ref w/drn",
  "SCC referral removed" drop one. "Sent to HPREF" is a prefiled bill.
- "HJC: Reported by committee with Do Pass recommendation [with amendment(s)]", "... with Do Not Pass but with a Do Pass
  recommendation on Committee Substitution" (DNP-CS/DP: the committee's substitute bill goes on), "... without a
  recommendation"; "HJC: Do Not Pass, Bill Has Died"; "Tabled Indefinitely, Bill Has Died". In 30-day sessions every
  Senate bill goes first to the Senate Committees' Committee, which reports whether it's germane ("Reported by committee to
  fall within the purview of a 30 day session"): the gate (`STATE.gates`). "Not Printed" ("not prntd-HRC") is a bill
  introduced without being printed, sent to the House Rules and Order of Business Committee (or another): most die there.
- "Withdrawn from committee or daily calendar for subsequent action" (w/drn) takes it out of committee, to the floor or
  (the ActionText says) to another committee; "Withdrawn ..., ordered printed and referred to" prints a not-printed bill.
- "Passed in the House of Representatives - Y:64 N:0", "Passed in the Senate - Y:28 N:13" (the passage), "Failed to Pass
  in the Senate, Bill Has Died" (the tally is in the ActionText: "FAILED/S (14-25)"), "Motion to reconsider adopted".
  Floor amendments ("Senate Floor Amendment", "fl/aaaa", "Floor substitute adopted") and a second house's committee
  amendments or substitute mean the first house has to agree: "House has concurred with Senate Amendments", or "House has
  failed to concur", "Senate has receded its amendments", "Sent to committee - Referrals: CC" (a conference committee) and
  "House Report Adopted" / "Senate Report Adopted" (both are needed).
- The governor's lines carry no calendar day: "Signed by Governor - Chapter 13 - Mar. 21" (the law's chapter, "Laws 2025,
  chapter 13"), "LAW WITHOUT SIGNATURE." (the day and chapter from the ActionText), "Vetoed by Governor" (the day from the
  governor's message, else the governor's last day), "Pocket Veto" (not signed within 20 days after the session: the
  governor's last day), "(partial veto)" in the ActionText (line-item vetoes, on a law), "Veto Override Passed in House"
  (an override needs both houses). "Signed by one or both houses (for legislation not requiring Governor's signature)":
  a joint resolution passed (constitutional amendments "SGND (C.A. 3)", for the voters). "Action Postponed Indefinitely"
  (API.): the session ended. "Succeeding entries: H 2": the bill was folded into House Bill 2.
Laws and vetoes agree with the pages' "Current Location" and the Legislature's database (LegStats): `checks()`.

Votes: floor roll calls member by member from the vote PDFs' text (votes/HB0005HVOTE.PDF.txt: the final vote in each
house), matched to the history's passage lines by house and tally; committee votes from the committee reports
(reports/HB0005JC1.HTML.txt: "The roll call vote was 9 For 1 Against", the no, excused and absent members by name) and
the tabling reports (Tabled_Reports: "Motion to TABLE PASSED", shown as the committee voting against the bill). Members are
matched within the vote's house to that year's member list (members.txt), whose third column is the roll calls' way of
telling apart members with one last name ("Martinez, A.", "Romero, GA"). "What it does" is the synopsis in the
Legislative Finance Committee's fiscal impact report (firs/HB0005.PDF.txt): the bill's (or its newest committee
substitute's) synopsis, then the later amendments' (the report lists them newest first).
The Legislature's database (LegInfo<yy>.zip, an Access file) isn't read here: the pages carry everything shown.
"""
import csv, html as H_, io, json, os, re, unicodedata
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from states.nm import profile as P

HOUSE = {"S": "Senate", "H": "House"}
OTHER = {"S": "H", "H": "S"}
SEATS = {"S": 42, "H": 70}
MONTHS = {m: i for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}
_PARTIES, _CACHE = {}, {}
UNREAD = Counter()
# The action lines' codes that aren't in the committee list: the House Rules and Order of Business Committee is "HRC" in
# the actions and "HXRC" on its page; the Senate Committees' Committee "SCC" and "SXCC".
ALIAS = {"HRC": "HXRC", "SCC": "SXCC"}
# Committees no longer on the committee pages (none seen in 2024-26; from the abbreviations key, for older years).
OLD_COMMITTEES = {"HXRC": "House Rules & Order Of Business", "SXCC": "Senate Committees' Committee",
                  "SRC": "Senate Rules", "HCAL": "House Calendar", "SCAL": "Senate Calendar"}
GATES = {"HXRC", "SXCC"}


def folder(session):
    return os.path.join(P.DATA, str(session))


def sessions():
    out = []
    for f in sorted(os.listdir(P.DATA)) if os.path.isdir(P.DATA) else []:
        if re.fullmatch(r"\d{4}", f) and os.path.exists(os.path.join(P.DATA, f, "list.json")) \
                and os.path.isdir(os.path.join(P.DATA, f, "bills")):
            out.append(int(f))
    return out


def listing(session):
    key = (session, "list")
    if key not in _CACHE:
        try:
            _CACHE[key] = json.load(open(os.path.join(folder(session), "list.json"), encoding="utf-8"))
        except (OSError, ValueError):
            _CACHE[key] = {}
    return _CACHE[key]


def text(fragment):
    return re.sub(r"\s+", " ", H_.unescape(re.sub(r"<[^>]+>", " ", fragment or ""))).strip()


def read_text(path):
    """A file's text: UTF-8 first, then Windows-1252 (members.txt writes "Martínez" in it)."""
    raw = open(path, "rb").read()
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("cp1252", errors="replace")


def norm(s):
    s = unicodedata.normalize("NFKD", s or "")
    return re.sub(r"[^a-z]", "", "".join(c for c in s if not unicodedata.combining(c)).lower())


# ---- The calendar ----

def opens(year):
    """The third Tuesday of January."""
    d = date(year, 1, 1)
    d += timedelta(days=(1 - d.weekday()) % 7 + 14)
    return d.isoformat()


def adjourns(year):
    """60 days in odd years, 30 in even years, counted from the opening day (2025: January 21 to March 22)."""
    return (date.fromisoformat(opens(year)) + timedelta(days=60 if year % 2 else 30)).isoformat()


def gov_due(year):
    """The governor's last day for bills passed in the session's last three days: 20 days after adjournment."""
    return (date.fromisoformat(adjourns(year)) + timedelta(days=20)).isoformat()


def month_day(s, year):
    """"Mar. 21" / "Feb.19" / "April 3" -> "2025-03-21"."""
    m = re.search(r"\b([A-Z][a-z]{2})[a-z]*\.?\s*(\d{1,2})\b", s or "")
    if not m or m.group(1).lower() not in MONTHS:
        return ""
    return date(year, MONTHS[m.group(1).lower()], int(m.group(2))).isoformat()


# ---- Committees ----

def committees():
    if "comms" not in _CACHE:
        try:
            raw = json.load(open(os.path.join(P.DATA, "committees.json"), encoding="utf-8"))
        except (OSError, ValueError):
            raw = []
        out = dict(OLD_COMMITTEES)
        for c in raw:
            out[c["code"]] = c["name"]
        _CACHE["comms"] = out
    return _CACHE["comms"]


def code_of(c):
    return ALIAS.get(c, c)


def comm_name(code):
    """"HHHC" -> "Health and Human Services"; "HXRC" -> "Rules and Order of Business"; "SXCC" -> "Committees' Committee"."""
    full = committees().get(code_of(code))
    if not full:
        return code
    n = re.sub(r"^(?:House|Senate)\s+", "", full.strip())
    n = re.sub(r"\s+Committee$", "", n) if not n.endswith("Committees' Committee") else n
    n = n.replace(" & ", " and ").replace(" And ", " and ").replace(" Of ", " of ")
    return n


def code_by_name(h, name):
    """A report's "HEALTH & HUMAN SERVICES" in the House -> "HHHC"."""
    key = norm(re.sub(r"\b(and|committee|house|senate)\b", "", name.replace("&", " "), flags=re.I))
    for code in committees():
        if code[0] == h and norm(re.sub(r"\b(and|committee|house|senate)\b", "", comm_name(code).replace("&", " "), flags=re.I)) == key:
            return code
    return None


# ---- Members ----

def members_json():
    """The members' pages (members.json): sponsor code -> {house, name, party, district, current, ...}."""
    if "mj" not in _CACHE:
        try:
            raw = json.load(open(os.path.join(P.DATA, "members.json"), encoding="utf-8"))
        except (OSError, ValueError):
            raw = []
        _CACHE["mj"] = {m["code"]: m for m in raw}
    return _CACHE["mj"]


def former():
    """Members who have left, from their pages (members/<code>.html: "Former Senator Mark Moores - (R)", district,
    county, "Years of Service: 2013-2024") -> code -> {house, name, party, district, years}."""
    if "former" not in _CACHE:
        out = {}
        d = os.path.join(P.DATA, "members")
        for f in sorted(os.listdir(d)) if os.path.isdir(d) else []:
            if not f.endswith(".html"):
                continue
            s = read_text(os.path.join(d, f))
            ym = re.search(r'lblServiceYears">\s*(\d{4})\s*-\s*(\d{4})?', s)
            hm = re.search(r'lblHeader">\s*(Senator|Representative)\s+(.*?)\s*-\s*\((\w+)\)', s)
            dm = re.search(r'lblDistrict">\s*(\d+)', s)
            if ym and hm and dm:
                out[f[:-5]] = {"house": "S" if hm.group(1) == "Senator" else "H", "name": text(hm.group(2)), "party": hm.group(3),
                               "district": int(dm.group(1)), "years": (int(ym.group(1)), int(ym.group(2) or 9999))}
        _CACHE["former"] = out
    return _CACHE["former"]


def roster(session):
    """The year's members (members.txt: last name, first name, the roll calls' tag ("A.", "GA"), party, counties,
    district, address, city, state, zip, phone, Capitol room, Capitol phone, email, "R"/"S"): [{house, last, first, tag,
    party, district, ...}]."""
    key = (session, "roster")
    if key not in _CACHE:
        out = []
        path = os.path.join(folder(session), "members.txt")
        if os.path.exists(path):
            for r in csv.reader(io.StringIO(read_text(path))):
                if len(r) < 15 or not r[5].strip().isdigit():
                    continue
                out.append({"house": "S" if r[14].strip() == "S" else "H", "last": r[0].strip(), "first": r[1].strip(),
                            "tag": r[2].strip(), "party": r[3].strip(), "counties": r[4].strip(), "district": int(r[5]),
                            "address": ", ".join(x.strip() for x in r[6:10] if x.strip()), "phone": r[10].strip(),
                            "room": r[11].strip(), "capitol": r[12].strip(), "email": r[13].strip()})
        # Members who served that year and left before the list was made (2024 lacks four senators; Susan Herrera, House
        # 41, left after the 2026 session): from their own pages.
        have = {(m["house"], norm(bare(m["last"]))) for m in out}
        for code, m in former().items():
            last = m["name"].split()[-1] if not re.search(r"\b(?:Jr|Sr|II|III)\.?$", m["name"]) else m["name"].split()[-2]
            if m["years"][0] <= session <= m["years"][1] and (m["house"], norm(last)) not in have:
                out.append({"house": m["house"], "last": last, "first": m["name"].split()[0], "tag": "", "party": m["party"],
                            "counties": "", "district": m["district"], "address": "", "phone": "", "room": "", "capitol": "",
                            "email": "", "former": True})
        _CACHE[key] = out
    return _CACHE[key]


def seat_by_name(session, h, name):
    """A member's full name ("Michelle Paulene Abeyta") in a house -> that year's roster entry, by last name and first
    initial (last names of two words too: "Mirabal Moya", "Sedillo Lopez")."""
    n = norm(re.sub(r"\"[^\"]*\"|,? (?:Jr|Sr|II|III)\.?$", "", name or ""))
    first = norm((name or "").split()[0]) if name else ""
    hits = [m for m in roster(session) if m["house"] == h and n.endswith(norm(m["last"]))]
    if len(hits) > 1:
        hits = [m for m in hits if norm(m["first"])[:1] == first[:1]] or hits
    if len(hits) > 1:
        hits = [m for m in hits if norm(m["first"]).startswith(first) or first.startswith(norm(m["first"]))] or hits
    return hits[0] if len(hits) == 1 else None


def sponsor_seat(session, code, name):
    """(name to show, district) for a sponsor code: the member's page name and district when the code is a current
    member sitting in that seat that year; else the year's roster by name."""
    h = code[0] if code[:1] in ("H", "S") else None
    m = members_json().get(code) or {}
    if not m.get("name") and code in former():
        m = {**former()[code], "current": False}
    r = seat_by_name(session, h, m.get("name") or name) if h else None
    if m.get("name") and r and m.get("district") and int(m["district"]) == r["district"]:
        return m["name"], r["district"], m.get("party") or r["party"]
    if r:
        return name, r["district"], r["party"]
    if m.get("name") and m.get("house") == h and m.get("district"):
        return m["name"], int(m["district"]), m.get("party")
    return name, None, None


def vote_seats(session, h):
    """(house) -> {roll-call key: seat}: "martineza" ("Martinez, A."), "romeroga", "abeyta", "hallii"; Senate roll calls
    write last names in capitals ("OMALLEY", "SEDILLO-LOPEZ", "MCCUTCHEON" for "McCutcheon II")."""
    key = (session, "vs", h)
    if key not in _CACHE:
        mine = [m for m in roster(session) if m["house"] == h]
        last = lambda m: norm(bare(m["last"]))
        out, count = {}, Counter(last(m) for m in mine)
        held = {m["district"] for m in mine if not m.get("former")}
        latest = session == max(sessions())
        for m in mine:
            sid = f"{h}:{m['district']}"
            # A member who has left is named, not given the seat, when someone else holds it now or (this year's page,
            # whose legislators are today's) when they're no longer serving.
            if (m.get("former") and m["district"] in held) or (latest and not is_current(m)):
                sid = f"{h}?{bare(m['last'])}"
            if m["tag"]:
                out[last(m) + norm(m["tag"])] = sid
            if count[last(m)] == 1 or not m["tag"] and not any(last(x) == last(m) and not x["tag"] and x is not m for x in mine):
                out.setdefault(last(m), sid)
            out.setdefault(norm(m["last"]), sid)  # "Hall II" as written
        _CACHE[key] = out
    return _CACHE[key]


def bare(name):
    """"Benny Shendo, Jr." -> "Benny Shendo"; "Hall II" -> "Hall"."""
    return re.sub(r",?\s+(?:Jr|Sr|II|III|IV)\.?$", "", (name or "").strip())


def is_current(m):
    """A roster entry is a member serving now (on the current members' pages, in that seat)."""
    return any(x.get("current") and x.get("house") == m["house"] and x.get("district") and int(x["district"]) == m["district"]
               and norm(bare(x.get("name"))).endswith(norm(bare(m["last"])))
               for x in members_json().values())


def seat_of(session, h, name):
    """A roll call's name ("Martinez, A.", "Hall II", "OMALLEY") -> its seat, else "H?Martinez"."""
    vs = vote_seats(session, h)
    n = re.sub(r"\s+(?:Jr|Sr|II|III|IV)\.?$", "", name.strip(), flags=re.I)
    for k in (norm(name), norm(n), norm(n.split(",")[0]) if "," not in n or not n.split(",")[1].strip() else None):
        if k and k in vs:
            return vs[k]
    if "," in n:
        last, tag = [x.strip() for x in n.split(",", 1)]
        same = [m for m in roster(session) if m["house"] == h and norm(m["last"]) == norm(last)]
        hits = {m["district"] for m in same if norm(m["tag"]) == norm(tag)} or \
            {m["district"] for m in same if not m["tag"] and norm(m["first"]).startswith(norm(tag)[:1])}
        if len(hits) == 1:
            d = hits.pop()
            m = next(m for m in same if m["district"] == d)
            return vs.get(norm(m["last"]) + norm(m["tag"])) or vs.get(norm(m["last"])) or f"{h}:{d}"
    # A name changed during the years: Sen. Crystal Diamond Brantley ("Diamond Brantley" in 2024's reports, "Diamond" or
    # "Brantley" on the lists).
    if " " in n.strip() and "," not in n:
        for w in n.split():
            if norm(w) in vs:
                return vs[norm(w)]
    last = bare(name.split(",")[0])
    return f"{h}?{last.title() if last.isupper() else last}"


# ---- Reading a bill's page ----

def parse(session, key):
    """A bill page -> {key, title, sponsors [(code, name)], actions [(legislative day, "MM/DD/YYYY" or "", line)],
    action_text, location} or None when it's missing."""
    path = os.path.join(folder(session), "bills", f"{key}.html")
    try:
        s = open(path, encoding="utf-8").read()
    except OSError:
        return None
    title = text((re.search(r'lblTitle"><b>(.*?)</b>', s, re.S) or [None, ""])[1])
    sponsors = []
    for code, name in re.findall(r'linkSponsor\d*" href="[^"]*SponCode=(\w+)"[^>]*><b>(?:<br/>)?(.*?)</b>', s, re.S):
        if code not in [c for c, _ in sponsors]:
            sponsors.append((code, text(name)))
    for code, name in re.findall(r'dataListSponsors_linkSponsor_\d+"[^>]*SponCode=(\w+)".*?lblSponsorName_\d+">(.*?)</span>', s, re.S):
        if code not in [c for c, _ in sponsors]:
            sponsors.append((code, text(name)))
    actions = []
    for sp in re.findall(r'dataListActions_lblAction_\d+" class="list-group-item">(.*?)</span>', s, re.S):
        m = re.match(r"\s*Legislative Day: (\d+)<br/>Calendar Day: (\S+)</br><strong>(.*)</strong>", sp, re.S)
        if m:
            actions.append((m.group(1), m.group(2), text(m.group(3))))
        else:
            actions.append(("", "", text(sp)))
    at = text((re.search(r'lblActionText">(.*?)</span>', s, re.S) or [None, ""])[1])
    loc = text((re.search(r'linkLocation"[^>]*><b>(.*?)</b>', s, re.S) or [None, ""])[1])
    return {"key": key, "title": title, "sponsors": sponsors, "actions": actions, "action_text": at, "location": loc,
            "final": bool(re.search(r"/final/", s))}


def is_const(key, title, action_text):
    return "JR" in key and (bool(re.search(r",\s*C\.?A\.?$", title.strip())) or bool(re.search(r"SGND \(C\.A\.", action_text)))


# ---- Titles ----

SMALL = {"a", "an", "and", "as", "at", "by", "for", "from", "in", "into", "of", "on", "or", "the", "to", "with", "per", "via", "vs"}


def case_words():
    """How the fiscal impact reports' short titles write each word ("Office of Child Advocate Act"): lower-case word ->
    its most common form, for turning the bill list's capitals into ordinary title case."""
    if "words" not in _CACHE:
        seen = defaultdict(Counter)
        for s in sessions():
            d = os.path.join(folder(s), "firs")
            for f in os.listdir(d) if os.path.isdir(d) else []:
                try:
                    t = read_text(os.path.join(d, f))
                except OSError:
                    continue
                m = re.search(r"SHORT TITLE\s+(.+?)\s{3,}", t)
                if m:
                    for w in re.findall(r"[A-Za-z][A-Za-z'.-]*", m.group(1)):
                        if not w.isupper() or len(w) <= 5:
                            seen[w.lower()][w] += 1
        _CACHE["words"] = {k: c.most_common(1)[0][0] for k, c in seen.items()}
    return _CACHE["words"]


def title_case(t, const):
    """"OFFICE OF CHILD ADVOCATE ACT" -> "Office of Child Advocate Act"; "SESSION LENGTH, SUBJECTS & OVERRIDES, CA" ->
    "Constitutional amendment: session length, subjects and overrides"."""
    t = re.sub(r"\s+", " ", t or "").strip()
    if const:
        t = re.sub(r",\s*C\.?A\.?$", "", t)
    words = case_words()
    out = []
    for i, w in enumerate(re.split(r"(\s+|/|-)", t)):
        if not re.search(r"[A-Za-z]", w):
            out.append(w)
            continue
        lw = w.lower()
        core = re.sub(r"[^a-z'.]", "", lw)
        if core in words and not (i and core in SMALL and words[core] != core):
            form = words[core]
            out.append(w.lower().replace(core, form) if core in w.lower() else form)
        elif i and core in SMALL:
            out.append(lw)
        elif len(core) <= 4 and not re.search(r"[aeiouy]", core):
            out.append(w)  # an abbreviation: "CYFD", "PRC"
        else:
            out.append(lw[:1].upper() + lw[1:])
    s = "".join(out).replace(" & ", " and ")
    s = s[:1].upper() + s[1:]
    if const:
        return f"Constitutional amendment: {s}"
    return s


# ---- Votes ----

def roll_calls(session, p):
    """A bill's final votes (votes/HB0005HVOTE.PDF.txt, HJR01SVOTE.pdf.txt, SJR0016SVOTE ...: the file names vary, so
    the house is read from the text) -> [{h, date, y, n, listed [(name, code)]}]. Codes: "N" no, "E" excused, "A" absent,
    "B" present not voting or recused; yes is left out."""
    key = (session, "votefiles")
    if key not in _CACHE:
        idx = defaultdict(list)
        d = os.path.join(folder(session), "votes")
        for f in sorted(os.listdir(d)) if os.path.isdir(d) else []:
            m = re.match(r"(HB|SB|HJR|SJR)0*(\d+)[HS]{1,2}VOTE\.", f, re.I)
            if m:
                idx[f"{m.group(1).upper()}{int(m.group(2))}"].append(f)
        _CACHE[key] = idx
    out = []
    for f in _CACHE[key].get(p, []):
        t = read_text(os.path.join(folder(session), "votes", f))
        r = read_roll(t)
        if r:
            r["h"] = "S" if "STATE SENATE" in t else "H"
            out.append(r)
    return out


LABELS = {"YEA": "Y", "YES": "Y", "NAY": "N", "NO": "N", "PNV": "B", "EXC": "E", "ABSENT": "A", "ABS": "A", "REC": "B"}


def read_roll(t):
    lines = t.splitlines()
    dm = re.search(r"DATE:\s*(\d{1,2})/(\d{1,2})/(\d{2,4})", t)
    if not dm:
        return None
    y = int(dm.group(3))
    day = date(y + 2000 if y < 100 else y, int(dm.group(1)), int(dm.group(2))).isoformat()
    hi = next((i for i, l in enumerate(lines) if re.search(r"\b(YEA|YES)\b.*\b(YEA|YES)\b", l)), None)
    if hi is None:
        return None
    head = lines[hi]
    labels = [(mm.start(), mm.end(), mm.group()) for mm in re.finditer(r"\b(YEA|NAY|PNV|EXC|ABSENT|YES|NO|ABS|REC)\b", head)]
    half = len(labels) // 2
    if "REPRESENTATIVE" in head:
        split = [mm.start() for mm in re.finditer(r"REPRESENTATIVE", head)][1]
    else:
        split = labels[half - 1][1] + 2
    left, right = labels[:half], labels[half:]
    out, counts = [], Counter()
    for l in lines[hi + 1:]:
        if re.match(r"\s*(X\*|TOTAL|CERTIFIED|PASSED|FAILED)", l) or "TOTAL =>" in l:
            break
        toks = []
        for mm in re.finditer(r"\S+(?: \S+)*", l):
            w, at = mm.group(), mm.start()
            # A name and its mark one space apart ("SMITH X").
            sm = re.match(r"(.+?) (X\*?)$", w)
            if sm and not re.fullmatch(r"X\*?", w):
                toks.append((at, sm.group(1)))
                toks.append((at + len(sm.group(1)) + 1, sm.group(2)))
            else:
                toks.append((at, w))
        for side, cols in ((lambda a: a < split, left), (lambda a: a >= split, right)):
            mine = [(a, w) for a, w in toks if side(a)]
            names = [(a, w) for a, w in mine if not re.fullmatch(r"X\*?", w)]
            marks = [(a, w) for a, w in mine if re.fullmatch(r"X\*?", w)]
            if not names:
                continue
            name = " ".join(w for _, w in names)
            if not marks:
                continue
            a = marks[0][0]
            lab = min(cols, key=lambda c: abs((c[0] + c[1]) / 2 - a))[2]
            code = LABELS[lab]
            counts[code] += 1
            if code != "Y":
                out.append((name, code))
    ym = re.search(r"YEAS:\s*(\d+)\s+NAYS:\s*(\d+)", t) or re.search(r"TOTAL\s*=>\s*(\d+)\s+(\d+)", t)
    yes, no = (int(ym.group(1)), int(ym.group(2))) if ym else (counts["Y"], counts["N"])
    return {"date": day, "y": yes, "n": no, "listed": out, "counted": (counts["Y"], counts["N"])}


MONTH_RX = r"(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),\s+(\d{4})"


def split_names(s):
    """"Anaya, Cates, Chavez, N., Chávez, E., Martinez, A., Hall II" -> names; initials ("N.", "GA", "JF") and suffixes
    belong to the name before them."""
    s = re.sub(r"\s+", " ", s or "").strip().rstrip(".") if not re.search(r"\b[A-Z]\.$", (s or "").strip()) else re.sub(r"\s+", " ", s).strip()
    s = re.split(r"(?:^|\s+)(?:[A-Z]:\\|\.?\d{6}\.\d|[\w.]+\.wpd|[\w.]+\.frm)", s)[0].strip() if s else s
    if not s or re.match(r"(?i)(?:none|no)\b|\d+$|0$", s):
        return []
    out = []
    for part in [x.strip() for x in s.split(",")]:
        if not part:
            continue
        if out and (re.fullmatch(r"[A-Z]{1,2}\.?|[A-Z]\.[A-Z]\.?|Jr\.?|Sr\.?", part)):
            out[-1] += ", " + part
        else:
            out.append(part)
    return out


def reports(session, p):
    """A bill's committee reports and tabling reports -> [{h, code, date, y, n, listed, tabled, kind}]."""
    key = (session, "reports")
    if key not in _CACHE:
        idx = defaultdict(list)
        d = os.path.join(folder(session), "reports")
        for f in sorted(os.listdir(d)) if os.path.isdir(d) else []:
            m = re.match(r"(HB|SB|HJR|SJR)0*(\d+)([A-Z]{2})(\d+)(T?)", f)
            if m and m.group(3) not in ("FS", "FH", "CC", "ES"):
                idx[f"{m.group(1)}{int(m.group(2))}"].append(f)
        _CACHE[key] = idx
    out = []
    for f in _CACHE[key].get(p, []):
        r = read_report(session, read_text(os.path.join(folder(session), "reports", f)))
        if r:
            r["file"] = f
            out.append(r)
    return out


def read_report(session, t):
    flat = re.sub(r"\s+", " ", t)
    h = "H" if re.search(r"M(?:r|adam)\.? Speaker", flat) else "S" if re.search(r"M(?:r|adam)\.? President", flat) else None
    dm = re.search(MONTH_RX, flat)
    rm = re.search(r"roll call vote was (\d+) For (\d+) Against", flat)
    if not h or not dm or not rm or re.search(r"enrolled and engrossed|CONFERENCE COMMITTEE", flat):
        return None
    tabled = bool(re.search(r"Motion to TABLE\s+PASSED", flat, re.I))
    cm = re.search(r"Your (.+?) COMMITTEE\s*,", flat) or re.search(r"Chair, (.+?) COMMITTEE, report", flat)
    code = code_by_name(h, cm.group(1)) if cm else None
    if not code:
        return None
    if not tabled and re.search(r"Motion to", flat) and not re.search(r"to whom has been referred", flat):
        return None  # another motion's roll call
    day = date(int(dm.group(3)), list(MONTHS).index(dm.group(1)[:3].lower()) + 1, int(dm.group(2))).isoformat()
    lists = {}
    for lab, body in re.findall(r"\b(Yes|No|Excused|Absent):\s*(.*?)(?=\b(?:Yes|No|Excused|Absent):|_{3,}|\S+\.wpd|\S+\.frm|VoteKey|\.\d{6}|$)", flat):
        lists[lab] = split_names(body)
    y, n = int(rm.group(1)), int(rm.group(2))
    listed = []
    code_of_list = {"No": "N", "Excused": "E", "Absent": "A"}
    if tabled:
        # The motion to table: its "For" votes are against the bill. Shown as the bill's vote: the motion's noes are the
        # bill's ayes; the movers are named only when the report names the yes votes.
        y, n = n, y
        code_of_list = {"Yes": "N", "Excused": "E", "Absent": "A"}
    for lab, c in code_of_list.items():
        for name in lists.get(lab, []):
            listed.append([seat_of(session, h, name), c])
    rec = "tabled" if tabled else "without recommendation" if re.search(r"WITHOUT RECOMMENDATION", flat) else \
        "substitute" if re.search(r"DO NOT PASS", flat) else "do pass"
    return {"h": h, "code": code, "date": day, "y": y, "n": n, "listed": listed, "tabled": tabled, "rec": rec}


# ---- What it does ----

def fir_files(session):
    key = (session, "firs")
    if key not in _CACHE:
        idx = defaultdict(list)
        d = os.path.join(folder(session), "firs")
        for f in sorted(os.listdir(d)) if os.path.isdir(d) else []:
            m = re.match(r"(HB|SB|HJR|SJR)0*(\d+)", f, re.I)
            if m:
                idx[f"{m.group(1).upper()}{int(m.group(2))}"].append(f)
        _CACHE[key] = idx
    return _CACHE[key]


def fir_text(session, p):
    """The fiscal impact report's text for a bill (the newest, when there are two), or ""."""
    best, when = "", ""
    for f in fir_files(session).get(p, []):
        t = read_text(os.path.join(folder(session), "firs", f))
        m = re.search(r"LAST UPDATED\s+(\d{1,2})/(\d{1,2})/(\d{4})", t)
        w = f"{m.group(3)}-{int(m.group(1)):02d}-{int(m.group(2)):02d}" if m else ""
        if t.strip() and (not best or w > when):
            best, when = t, w
    return best


def paragraphs(block):
    """A report's text block -> paragraphs: page headers and footers dropped, lines joined, bullets kept as their own
    paragraphs."""
    lines = []
    for l in block.splitlines():
        if re.search(r"[–-] Page \d+\s*$", l) or re.match(r"\s*(House|Senate) (Bill|Joint Resolution|Memorial)\b.*[–-] Page", l):
            continue
        lines.append(l.rstrip())
    out, cur = [], []
    for l in lines:
        s = l.strip()
        bullet = re.match(r"^[•●▪•]\s*(.*)", s)
        if not s:
            if cur:
                out.append(" ".join(cur))
                cur = []
            continue
        if bullet:
            if cur:
                out.append(" ".join(cur))
            cur = ["• " + bullet.group(1)]
            continue
        cur.append(s)
    if cur:
        out.append(" ".join(cur))
    out = [re.sub(r"\s+", " ", re.sub(r"(\w)- (\w)", r"\1-\2", x)).strip() for x in out]
    out = [x for x in out if x and not re.fullmatch(r"[\d\s\W]*", x)]
    # A page break splits a paragraph (the footer between them is dropped): join a paragraph that stops mid-sentence to
    # the next, unless the next is a list item, or the list item before it ends a line of a list.
    joined = []
    for x in out:
        prev = joined[-1] if joined else ""
        if prev and not re.search(r"[.;:!?)\"”’]$", prev) and not x.startswith("•") and \
                (not prev.startswith("•") or x[:1].islower()):
            joined[-1] = f"{prev} {x}"
        else:
            joined.append(x)
    return joined


def synopsis(session, p):
    """The fiscal impact report's SUMMARY: the newest substitute's (or the bill's) synopsis, then the later amendments'
    synopses, oldest first. "" when there's none."""
    t = fir_text(session, p)
    if not t or "SUMMARY" not in t:
        return ""
    body = t.split("SUMMARY", 1)[1]
    body = re.split(r"\n\s*(?:FISCAL IMPLICATIONS|SIGNIFICANT ISSUES|PERFORMANCE IMPLICATIONS|ADMINISTRATIVE IMPLICATIONS)\b", body)[0]
    parts = re.split(r"(?m)^\s*(Synopsis of[^\n]*)\n", body)
    if len(parts) < 3:
        ps = paragraphs(body)
        return "\n".join(ps)
    sections = [(parts[i].strip(), parts[i + 1]) for i in range(1, len(parts) - 1, 2)]
    amendment = lambda hd: re.search(r"Amendment|\bSFl|\bHFl|\bFl\b", hd, re.I)
    base = next((i for i, (hd, _) in enumerate(sections) if re.search(r"Substitute", hd, re.I) and not amendment(hd)), None)
    if base is None:
        base = next((i for i, (hd, _) in enumerate(sections) if not amendment(hd)), len(sections) - 1)
    order = [sections[base]] + list(reversed(sections[:base]))
    out = []
    for hd, blk in order:
        out.extend(paragraphs(blk))
    s = ""
    for x in out:
        if len(s) + len(x) > 4000 and s:
            break
        s += ("\n" if s else "") + x
    return s


def veto_message(session, p):
    """The governor's message on a bill (messages/HB0012GovMsg.pdf.txt) -> (date, text) or None."""
    m = re.match(r"(HB|SB|HJR|SJR)(\d+)$", p)
    d = os.path.join(folder(session), "messages")
    for f in os.listdir(d) if os.path.isdir(d) else []:
        mm = re.match(r"(HB|SB|HJR|SJR)0*(\d+)GovMsg", f, re.I)
        if mm and mm.group(1).upper() == m.group(1) and int(mm.group(2)) == int(m.group(2)):
            t = read_text(os.path.join(d, f))
            dm = re.search(MONTH_RX, t)
            day = date(int(dm.group(3)), list(MONTHS).index(dm.group(1)[:3].lower()) + 1, int(dm.group(2))).isoformat() if dm else ""
            body = re.split(r"(?m)^\s*(?:Honorable|President|Speaker|Dear)[^\n]*:\s*$", t, maxsplit=1)
            body = body[1] if len(body) > 1 else t
            body = re.split(r"(?m)^\s*(?:Respectfully|Sincerely)", body)[0]
            ps = paragraphs(body)
            s = ""
            for x in ps:
                if len(s) + len(x) > 3500 and s:
                    break
                s += ("\n" if s else "") + x
            return day, s
    return None


# ---- One bill ----

def dated(session, b):
    """The page's actions with a date each, in date order (the file's order within a day). Lines with no calendar day:
    prefiling before the first dated line, the governor's from their wording, "Action Postponed Indefinitely" on the
    session's last day."""
    out, last = [], None
    first = next((d for _, d, _ in b["actions"] if d), "")
    at = b["action_text"]
    msg = veto_message(session, b["key"])
    for i, (lday, d, t) in enumerate(b["actions"]):
        iso = ""
        if d:
            mm, dd, yy = d.split("/")
            iso = f"{yy}-{mm}-{dd}"
        elif re.match(r"Sent to [HS]PREF", t):
            iso = min(datetime.strptime(first, "%m/%d/%Y").date().isoformat() if first else opens(session), opens(session))
        elif re.match(r"Signed by Governor", t):
            iso = month_day(t.split(" - ")[-1], session)
        elif re.match(r"LAW WITHOUT SIGNATURE", t):
            iso = month_day((re.search(r"LAW WITHOUT SIGNATURE\s*\(([^)]*)\)", at) or [None, ""])[1], session)
        elif re.match(r"Vetoed by Governor", t):
            iso = (msg[0] if msg and msg[0] else "") or month_day((re.search(r"VETO\s*\(([^)]*)\)", at) or [None, ""])[1], session)
            iso = iso or min(gov_due(session), max(last or opens(session), adjourns(session)))
        elif re.match(r"Pocket Veto", t, re.I):
            iso = gov_due(session)
        elif re.match(r"Action Postponed Indefinitely", t):
            iso = adjourns(session)
        iso = iso or last or opens(session)
        out.append((i, iso, lday, t))
        last = iso
    out.sort(key=lambda x: (x[1], x[0]))
    return [(d, l, t) for _, d, l, t in out]


def record(session, b, parties):
    p = b["key"]
    origin = p[0]
    other = OTHER[origin]
    const = is_const(p, b["title"], b["action_text"])
    at = b["action_text"]
    steps = []  # (date, house or "G", wording, kind)
    passed, amended_by, last_pass = set(), set(), {}
    where, place, comm = origin, "desk", None
    chain = []
    reported = set()
    refs, first_ref, first_fate = [], None, None
    concurred = False
    conf = set()
    law = vetoed = pocket = items = jr_signed = folded = False
    overrides = set()
    killed = None
    chapter = None
    fvotes = []
    vote_steps = []
    failed_tallies = [(int(a), int(b_)) for a, b_ in re.findall(r"FAILED/[HS]\s*\((\d+)-(\d+)\)", at)]
    override_tallies = [(int(a), int(b_)) for a, b_ in re.findall(r"VETO OVERRIDE (?:PASSED|FAILED)/[HS]\s*\((\d+)-(\d+)\)", at)]
    withdrawals = re.findall(r"\bw/drn\b(?!-prntd| [hs]/cal)\s*(?:-\s*(?:ref\s*)?([HS][A-Z]{1,5})\b)?", at)
    not_printed = re.findall(r"not prntd-([A-Z]+)", at)

    def refer(d, code, also=()):
        nonlocal comm, place, where, first_ref
        c = code_of(code)
        h = c[0]
        where, comm, place = h, c, "committee"
        name = comm_name(c)
        if c not in GATES:
            refs.append((h, name))
            if first_ref is None and h == origin:
                first_ref = c
        steps.append((d, h, f"REFERRED TO {name.upper()}", "ref"))
        rest = [comm_name(code_of(x)) for x in also if code_of(x) != c]
        if rest:
            steps.append((d, h, f"Its committees, in order: the {name} Committee, then " + ", then ".join(rest), "other"))

    def advance(d, code):
        """A committee is done with the bill: on to the next committee on its list, or the floor."""
        nonlocal chain, comm, place
        c = code_of(code)
        if c in chain:
            chain = chain[chain.index(c) + 1:]
        elif chain and chain[0] == comm:
            chain = chain[1:]
        if chain:
            nxt = chain[0]
            comm = None
            refer(d, nxt)
        else:
            comm, place = None, "floor"
            to_floor.append(d)

    to_floor = []  # days a committee's report sent the bill to the floor
    for d, lday, t in dated(session, b):
        m = re.match(r"Sent to (\w+)(?: - Referrals: ([\w/]+))?$", t) or re.match(r"Sent to committee - Referrals: ([\w/]+)$()", t)
        if m:
            code = m.group(1)
            lst = [x for x in (m.group(2) or code).split("/") if x]
            if code in ("HPREF", "SPREF"):
                steps.append((d, origin, "Prefiled before the session", "other"))
                continue
            if code in ("HCAL", "SCAL"):
                place = "floor"
                steps.append((d, code[0], f"Placed on the {HOUSE[code[0]]} calendar", "other"))
                continue
            if code == "PASS":
                continue
            if code == "CC":
                steps.append((d, where, "A conference committee was appointed", "conf"))
                continue
            chain = [code_of(x) for x in lst]
            refer(d, code, lst)
            continue
        m = re.match(r"Referred to: ([\w/]+)$", t) or re.match(r"re-ref ([A-Z]+)$", t)
        if m:
            lst = m.group(1).split("/")
            chain = [code_of(x) for x in lst]
            steps.append((d, code_of(lst[0])[0], "Sent to a different committee", "rereferred"))
            refer(d, lst[0], lst)
            continue
        m = re.match(r"w/drn ([hs])/calendar", t)
        if m:
            steps.append((d, m.group(1).upper(), "Taken off the calendar and sent back to committee", "other"))
            continue
        if re.match(r"Withdrawn from committee or daily calendar, ordered printed and referred to", t):
            steps.append((d, where, "Withdrawn, printed and sent to a committee", "other"))
            continue
        if re.match(r"Withdrawn from committee or daily calendar for subsequent action", t):
            target = withdrawals.pop(0) if withdrawals else ""
            steps.append((d, where, "Taken out of committee (withdrawn)" if place == "committee" else "Withdrawn from the calendar", "other"))
            if target and code_of(target) in committees():
                chain = [code_of(target)]
                refer(d, target)
            else:
                chain, comm, place = [], None, "floor"
            continue
        if t == "Not Printed":
            code = code_of(not_printed.pop(0) if not_printed else ("HRC" if origin == "H" else "SRC"))
            chain = [code]
            steps.append((d, code[0], "Introduced, but not printed", "other"))
            refer(d, code)
            continue
        m = re.match(r"(?:([A-Z]+) referral removed|([A-Z]+) ref w/drn|(House|Senate) (.+?) Committee referral withdrawn)$", t)
        if m:
            code = code_of(m.group(1) or m.group(2) or code_by_name(m.group(3)[0], m.group(4)) or "")
            steps.append((d, code[:1] or where, f"No longer sent to the {comm_name(code)} Committee", "other"))
            if code in chain:
                was = comm == code
                chain.remove(code)
                if was:
                    if chain:
                        comm = None
                        refer(d, chain[0])
                    else:
                        comm, place = None, "floor"
            continue
        m = re.match(r"([A-Z]+): Reported by committee (.*)$", t)
        if m:
            code = code_of(m.group(1))
            h, rest, name = code[0], m.group(2), comm_name(code)
            where = h
            if re.search(r"purview of a \d+ day session", rest):
                steps.append((d, h, "The Committees' Committee found it germane (within what the 30-day session may take up)", "germane"))
                advance(d, code)
                continue
            reported.add(h)
            if first_fate is None and code == first_ref:
                first_fate = "passed"
            sub = "Committee Substitution" in rest
            amend = "amendment" in rest or "as amended" in rest
            rec = "without a recommendation" if re.search(r"without (?:a )?recommendation", rest) else "with a do-pass recommendation"
            what = " (as a committee substitute)" if sub else " (with amendments)" if amend else ""
            steps.append((d, h, "REPORTED", "reported"))
            steps.append((d, h, f"The {name} Committee reported it {rec}{what}", "report"))
            if (sub or amend) and h == other and origin in passed:
                amended_by.add(h)
            advance(d, code)
            continue
        m = re.match(r"([A-Z]+): Do Not Pass, Bill Has Died", t)
        if m:
            code = code_of(m.group(1))
            if first_fate is None and code == first_ref:
                first_fate = "defeated"
            killed = "committee"
            steps.append((d, code[0], f"The {comm_name(code)} Committee recommended it not pass, which ends it", "killed"))
            continue
        if re.match(r"Tabled Indefinitely", t):
            if first_fate is None and comm == first_ref:
                first_fate = "defeated"
            killed = "committee"
            steps.append((d, where, f"Tabled indefinitely{' by the ' + comm_name(comm) + ' Committee' if comm else ''}, which ends it", "killed"))
            continue
        m = re.match(r"Passed in the (House of Representatives|Senate) - Y:(\d+) N:(\d+)", t)
        if m:
            h = "S" if m.group(1) == "Senate" else "H"
            y, n = int(m.group(2)), int(m.group(3))
            where = h
            vote_steps.append((h, d, y, n))
            if h not in passed:
                passed.add(h)
                last_pass[h] = d
                steps.append((d, h, f"PASSED {HOUSE[h].upper()}", "pass"))
                steps.append((d, h, f"The {HOUSE[h]} vote: {y}-{n}", "tally"))
            else:
                steps.append((d, h, f"The {HOUSE[h]} passed it again, {y}-{n}", "final"))
            comm, chain = None, []
            if h == origin and other not in passed:
                where, place = other, "desk"
            elif h == other and other in amended_by:
                where = origin
            continue
        m = re.match(r"Failed to Pass in (?:the )?(House|Senate)", t)
        if m:
            h = m.group(1)[0]
            tl = failed_tallies.pop(0) if failed_tallies else None
            if tl:
                vote_steps.append((h, d, tl[0], tl[1]))
            steps.append((d, h, f"Failed in the {HOUSE[h]}" + (f", {tl[0]}-{tl[1]}" if tl else "") + ", which ends it", "failed"))
            killed = "floor"
            continue
        if re.match(r"Motion to reconsider adopted", t):
            passed.discard(where)
            steps.append((d, where, f"The {HOUSE[where]} voted to reconsider its vote", "reconsider"))
            continue
        m = re.match(r"(Senate|House of Representatives|HFL|SFL)? ?Floor (?:Amendment|substitute adopted)|multiple floor amendments|fl/a+$|Floor substitute adopted", t)
        if m:
            h = "S" if re.match(r"Senate|SFL", t) else "H" if re.match(r"House|HFL", t) else where
            if h == other and origin in passed:
                amended_by.add(h)
            steps.append((d, h, "A floor substitute was adopted" if "substitute" in t else "Amended on the floor", "amend"))
            continue
        m = re.match(r"(House|Senate) has concurred with (?:House|Senate) Amendments", t)
        if m:
            h = m.group(1)[0]
            if h == origin:
                concurred = True
            steps.append((d, h, f"The {HOUSE[h]} agreed to the {HOUSE[OTHER[h]]}'s changes", "concur"))
            continue
        if re.match(r"[sh]/partially concurred", t):
            h = t[0].upper()
            steps.append((d, h, f"The {HOUSE[h]} agreed to some of the {HOUSE[OTHER[h]]}'s changes", "concur"))
            continue
        if re.match(r"[sh]/receded on remaining amendments", t):
            h = t[0].upper()
            if h == other:
                amended_by.discard(h)
            steps.append((d, h, f"The {HOUSE[h]} dropped its remaining changes (receded)", "recede"))
            continue
        m = re.match(r"(House|Senate) has failed to concur", t)
        if m:
            h = m.group(1)[0]
            steps.append((d, h, f"The {HOUSE[h]} refused to agree to the {HOUSE[OTHER[h]]}'s changes", "noconcur"))
            continue
        m = re.match(r"(House|Senate) (?:has )?(receded|failed to recede)", t)
        if m:
            h = m.group(1)[0]
            if m.group(2) == "receded":
                if h == other:
                    amended_by.discard(h)
                steps.append((d, h, f"The {HOUSE[h]} dropped its changes (receded)", "recede"))
            else:
                steps.append((d, h, f"The {HOUSE[h]} refused to drop its changes", "norecede"))
            continue
        m = re.match(r"(House|Senate) Report Adopted", t)
        if m:
            h = m.group(1)[0]
            conf.add(h)
            steps.append((d, h, f"The {HOUSE[h]} adopted the conference committee's report", "ccr"))
            continue
        m = re.match(r"Succeeding entries: ([HS]) (\d+)", t)
        if m:
            folded = True
            killed = killed or "committee"
            steps.append((d, where, f"Folded into {m.group(1)}B {m.group(2)}: its later steps are that bill's", "other"))
            continue
        if re.match(r"Action Postponed Indefinitely", t):
            steps.append((d, where, "The session ended without it passing (action postponed indefinitely)", "died"))
            continue
        m = re.match(r"Signed by Governor - Chapter\s*(\d+)", t)
        if m:
            # The coded ActionText's chapter, when it has one: the spelled-out line is wrong twice in 2025 (SB 5 "Chapter
            # 6", SB 45 "Chapter 138"; the ActionText's 9 and 139 run 1-160 with none repeated or missing).
            cm = re.search(r"SGND BY GOV.*?Ch\.\s*(\d+)", at)
            chapter = int(cm.group(1)) if cm else int(m.group(1))
            if not const:
                law = True
            steps.append((d, "G", f"Signed by the governor (chapter {chapter})", "signed"))
            if re.search(r"partial veto", at, re.I):
                items = True
                steps.append((d, "G", "The governor vetoed parts of it (a line-item veto)", "itemveto"))
            continue
        if re.match(r"LAW WITHOUT SIGNATURE", t):
            cm = re.search(r"LAW WITHOUT SIGNATURE.*?Ch\.\s*(\d+)", at)
            chapter = int(cm.group(1)) if cm else chapter
            law = True
            steps.append((d, "G", "Became law without the governor's signature" + (f" (chapter {chapter})" if chapter else ""), "nosign"))
            continue
        if re.match(r"Vetoed by Governor", t):
            vetoed = True
            steps.append((d, "G", "VETOED", "vetoed"))
            continue
        if re.match(r"Pocket Veto", t, re.I):
            vetoed = pocket = True
            steps.append((d, "G", "VETOED (a pocket veto: not signed within 20 days after the session ended)", "vetoed"))
            continue
        m = re.match(r"Veto Override (Passed|Failed) in (?:the )?(House|Senate)", t)
        if m:
            h = m.group(2)[0]
            tl = override_tallies.pop(0) if override_tallies else None
            if m.group(1) == "Passed":
                overrides.add(h)
            steps.append((d, h, f"The {HOUSE[h]} voted to override the veto" + (f", {tl[0]}-{tl[1]}" if tl else "")
                          + ("" if m.group(1) == "Passed" else " (it failed)"), "overridevote"))
            continue
        if re.match(r"Signed by one or both houses", t):
            jr_signed = True
            steps.append((d, origin, "Signed by the presiding officers: passed by the Legislature" + (", for the voters at the next general election" if const else ""), "enrolled"))
            continue
        if re.match(r"Bill recalled from the House", t):
            steps.append((d, "S", "The Senate recalled it from the House for further consideration", "other"))
            continue
        UNREAD[re.sub(r"\d+", "#", t)[:80]] += 1
        steps.append((d, where, t[:1].upper() + t[1:], "other"))

    if overrides >= {"S", "H"} and vetoed:
        law, vetoed = True, False
        steps.append((steps[-1][0], "G", "Became law over the governor's veto", "overridelaw"))
    both = law or vetoed or (const and jr_signed) or (
        origin in passed and other in passed and (other not in amended_by or concurred or conf >= {"S", "H"}))
    if const:
        stage = 3 if both else 2 if passed else None
    elif law:
        stage = 5
    elif vetoed:
        stage = 6
    elif both:
        stage = 4
    elif passed:
        stage = 2
    else:
        stage = None
    if stage is not None and stage >= 3:
        passed = {"S", "H"}
    if stage is None:
        stage = 1 if place == "floor" and not killed else 0

    title = title_case(b["title"], const)
    topics = ["const"] if const else []
    for h_, c in refs:
        if c in P.COMMITTEE_TOPICS and P.COMMITTEE_TOPICS[c] not in topics:
            topics.append(P.COMMITTEE_TOPICS[c])
    syn = synopsis(session, p)
    if not topics:
        topics = [k for k, rx in P.TOPIC_WORDS.items() if rx.search(f"{title} {syn[:300]}")]
    topics = list(dict.fromkeys(t for t in topics if t != "const" or const))

    names = []
    for code, nm in b["sponsors"]:
        name, district, party = sponsor_seat(session, code, nm)
        h = code[0] if code[:1] in "HS" else origin
        names.append((name, district, h))
        if party in ("R", "D"):
            parties[(h, name)] = party
    # Sponsors from the other house are listed too ("Representative X" on a Senate bill); the record keys co-sponsors by
    # the bill's house, so they're named as written.
    sponsor, district = (names[0][0], names[0][1]) if names else ("—", None)
    if names and names[0][2] != origin:
        district = None
    cos = [n for n, _, _ in names[1:] if n != sponsor]

    cur = where
    if stage == 0:
        dsc = f"In {HOUSE[cur]} committee" if place == "committee" else "Introduced"
    elif stage == 1:
        dsc = f"On the {HOUSE[cur]} floor"
    else:
        dsc = {2: f"Passed the {HOUSE[origin] if origin in passed else HOUSE[other]}", 3: "Passed both houses",
               4: "On the governor's desk", 5: "Became law", 6: "Vetoed"}[stage]
    comm_now = comm_name(comm) if comm and place == "committee" and stage in (0, 2) else None

    # Committee votes from the reports, and tabling.
    votes = []
    for r in reports(session, p):
        cname = comm_name(r["code"])
        votes.append([r["h"], "C", cname, r["date"], r["y"], r["n"], r["listed"]])
        if r["tabled"]:
            steps.append((r["date"], r["h"], f"Tabled by the {comm_name(r['code'])} Committee, {r['n']}-{r['y']}", "tabled"))
            if first_fate is None and r["code"] == first_ref:
                first_fate = "defeated"
    steps.sort(key=lambda s: s[0])  # stable: the tabling lines join their day
    votes.extend(floor_votes(session, p, vote_steps))
    votes.sort(key=lambda v: v[3])

    def dates(test, mode="last"):
        ds = sorted({s[0] for s in steps if test(s) and s[0]})
        return {"first": ds[0], "last": ds[-1], "all": ";".join(ds)}[mode] if ds else ""

    sent = ""
    if stage >= 4:
        agree = [s[0] for s in steps if s[3] in ("pass", "final", "concur", "recede", "ccr")]
        sent = max(agree) if agree else ""
    vmemo = None
    if stage == 6 or items:
        msg = veto_message(session, p)
        if msg and msg[1]:
            vmemo = {"year": session, "signer": P.governor_on(msg[0] or f"{session}-03-01"), "text": msg[1],
                     **({"kind": "line-item"} if items and stage == 5 else {})}
    action_dates = [s[0] for s in steps if s[0]]
    what = {"statement": syn, "label": "From the Legislative Finance Committee's fiscal impact report."} if syn else None
    official = b["title"].strip()
    rec = {
        "nums": [p], "base": [p], "prev": earlier(session, b),
        "title": title, "summary": "", "act": "", "lawCode": "", "law": None, "laws": [],
        "comms": sorted({f"{h_} · {c}" for h_, c in refs}), "topics": topics, "places": [],
        "narrow": P.narrow_kind(title),
        "commFate": first_fate or ("passed" if reported or passed else "none"), "mainTopic": topics[0] if topics else "",
        "local": "local" in topics, "senDeleg": False, "asmDeleg": False,
        "budget": bool(re.search(r"\bAPPROPRIATION", official)) and not const,
        "passedS": "S" in passed, "passedA": "H" in passed, "program": None,
        "stage": stage, "passedIn": (HOUSE[origin] if origin in passed else HOUSE[other]) if stage == 2 else None,
        "chapter": chapter if stage == 5 else None,
        "veto": None, "memo": "", "vetoMemo": vmemo,
        "simText": f"{title} {syn[:600]}",
        "comm": comm_now if stage == 0 else None,
        "first": min(action_dates, default=opens(session)),
        "last": max(action_dates, default=opens(session)),
        "cosp": len(cos),
        "keyDates": [
            min(to_floor, default=""),
            dates(lambda s: s[2] == "PASSED SENATE", "all"),
            dates(lambda s: s[2] == "PASSED HOUSE", "all"),
            "",
            sent,
            dates(lambda s: s[3] in ("signed", "nosign", "overridelaw")) if stage == 5 else "",
            dates(lambda s: s[3] == "vetoed"),
        ],
        "votes": votes, "firstComms": [(origin, comm_name(first_ref), first_fate == "passed" or bool(passed))] if first_ref else [],
        "vers": [{"p": p, "sponsor": sponsor, "district": district or 0, "cosponsors": cos,
                  "primes": 1, "cosp": len(cos), "statusDesc": dsc, "committee": comm_now,
                  "actions": [[s[0], s[2]] for s in steps]}],
    }
    if stage == 5 and not rec["keyDates"][5]:
        rec["keyDates"][5] = rec["last"]
    return rec, what


def floor_votes(session, p, vote_steps):
    """Each passage or failed vote: member by member when the house's vote PDF has that tally, else the tally."""
    out = []
    rolls = roll_calls(session, p)
    used = set()
    for h, d, y, n in vote_steps:
        r = next((r for i, r in enumerate(rolls) if i not in used and r["h"] == h and (r["y"], r["n"]) == (y, n)), None)
        if r:
            used.add(rolls.index(r))
            out.append([h, "F", None, d, y, n, [[seat_of(session, h, name), c] for name, c in r["listed"]]])
        else:
            out.append([h, "F", None, d, y, n, []])
    return out


def load_session(session):
    """Read one year's bills and return (records, bill number -> record index, fetched time, delegation)."""
    lst = listing(session)
    parties = _PARTIES.setdefault(session, {})
    stamp = lst.get("stamp") or ""
    recs, index, whats = [], {}, {}
    keys = []
    for k, row in (lst.get("bills") or {}).items():
        if row.get("type") == "B" or (row.get("type") == "JR" and re.search(r",\s*C\.?A\.?$", row.get("title") or "")):
            keys.append(k)
    for k in sorted(keys, key=lambda k: (k[0] != "H", "JR" in k, int(re.sub(r"\D", "", k)))):
        b = parse(session, k)
        if not b or not b["title"]:
            continue
        if "JR" in k and not is_const(k, b["title"], b["action_text"]):
            continue
        rec, what = record(session, b, parties)
        index[k] = len(recs)
        recs.append(rec)
        if what:
            whats[k] = what
    try:
        json.dump(whats, open(os.path.join(P.DATA, f"texts_{session}.json"), "w"), ensure_ascii=False)
    except OSError:
        pass
    paths = [os.path.join(folder(session), n) for n in ("state.json", "list.json")]
    times = [os.path.getmtime(x) for x in paths if os.path.exists(x)]
    fetched = datetime.fromtimestamp(max(times), ZoneInfo(P.TIMEZONE)).strftime("%Y-%m-%d %H:%M") if times else stamp
    return recs, index, fetched, {"SENATE": [], "ASSEMBLY": []}


# ---- Earlier years ----

_KEYS = {}


def _keys(session):
    """A year's bills that didn't become law: (short title, prime sponsor code) -> [bills]."""
    if session not in _KEYS:
        out = defaultdict(list)
        for k, row in (listing(session).get("bills") or {}).items():
            if row.get("type") != "B":
                continue
            if re.search(r"\bCh\.\s*\d+|LAW WITHOUT SIGNATURE", row.get("actions") or ""):
                continue  # a law isn't tried again (yearly bills like the budget share titles)
            key = _key(row.get("title"), (row.get("sponsors") or [[""]])[0][0])
            if key:
                out[key].append(k)
        _KEYS[session] = out
    return _KEYS[session]


def _key(title, code):
    t = re.sub(r"[^A-Z0-9 ]", "", (title or "").upper()).strip()
    if len(t.split()) < 3 or re.search(r"\bAPPROPRIATION|\bCAPITAL OUTLAY|\bBUDGET\b", t) or not code:
        return ""
    return f"{t}|{code}"


def earlier(session, b):
    """The same bill in the two years before: the same short title and prime sponsor, held by one bill in each year.
    Never appropriations, nor a bill that became law."""
    if "JR" in b["key"] or not b["sponsors"]:
        return set()
    key = _key(b["title"], b["sponsors"][0][0])
    if not key:
        return set()
    out = set()
    for y in (session - 1, session - 2):
        if y not in sessions():
            continue
        old, mine = _keys(y), _keys(session)
        if len(old.get(key, [])) == 1 and len(mine.get(key, [])) <= 1:
            out.add((y, old[key][0]))
    return out


def parties(session, recs):
    if session not in _PARTIES:
        load_session(session)
    return {k: v for k, v in _PARTIES.get(session, {}).items() if v in ("D", "R")}


def agendas(session):
    return {}


# ---- Checks ----

def checks(session):
    """Laws, vetoes and pocket vetoes against the pages' "Current Location"."""
    recs, index = load_session(session)[:2]
    loc = Counter()
    for k in index:
        b = parse(session, k)
        loc[re.sub(r"\s*\(.*", "", b["location"])] += 1
    st = Counter(r["stage"] for r in recs)
    pocket = sum(1 for r in recs if r["stage"] == 6 and any("pocket veto" in a[1] for a in r["vers"][0]["actions"]))
    items = sorted(r["nums"][0] for r in recs if any("line-item veto" in a[1] for a in r["vers"][0]["actions"]))
    unmatched = Counter()
    total = Counter()
    for r in recs:
        for v in r["votes"]:
            for m, _ in v[6]:
                total[v[1]] += 1
                if "?" in m:
                    unmatched[(v[1], m)] += 1
    return {"bills": len(recs), "stages": dict(sorted(st.items())), "laws": st[5], "vetoes": st[6] - pocket, "pocket": pocket,
            "line items": items, "locations": dict(loc), "amendments passed": sum(1 for r in recs if "const" in r["topics"] and r["stage"] == 3),
            "floor votes": sum(1 for r in recs for v in r["votes"] if v[1] == "F"),
            "floor votes by member": sum(1 for r in recs for v in r["votes"] if v[1] == "F" and (v[6] or v[4] + v[5] > 0)),
            "committee votes": sum(1 for r in recs for v in r["votes"] if v[1] == "C"),
            "names not matched": sum(unmatched.values()), "names": dict(total), "unmatched": unmatched.most_common(8)}


if __name__ == "__main__":
    import sys
    for s in ([int(sys.argv[1])] if len(sys.argv) > 1 else sessions()):
        print(s, json.dumps(checks(s), ensure_ascii=False))
    for k, n in UNREAD.most_common(25):
        print(n, k)
