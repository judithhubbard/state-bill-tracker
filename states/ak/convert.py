"""Alaska's bills (downloaded by states/ak/fetch.py from the Legislature's BASIS public service) in the shape build_data.py
reads. House and Senate bills of each two-year Legislature (special sessions' too, numbered from 1001), plus the joint
resolutions that propose amendments to the Alaska Constitution; other resolutions are left out.

Each action has a journal date, the house (or, for committee hearings, the committee: "HL&C") and a code with capitals
wording: 001 "READ THE FIRST TIME - REFERRALS" then 091 the committees in order ("L&C, EDC"); 002 a committee's report
("L&C RPT CS(L&C) 5DP 1NR", then 063 the members' recommendations, "DP: CARRICK, SADDLER", "NR: NELSON"; a report moves
the bill on to the next committee in the list, often with no "REFERRED TO" line, and after the last one to the Rules
Committee, which decides when it reaches the floor: 080 "RULES TO CALENDAR 4/11/2025"); 020 "PASSED Y34 N6" and 024
"PASSED ON RECONSIDERATION" (the passage), 128 "RESCINDED ACTION (PASSAGE)" undoes the house's last vote; 022 "TRANSMITTED
TO (S)"; 083 "TRANSMITTED TO (H) AS AMENDED" (the first house has to concur: 026 "CONCUR AM OF (S) Y31 N8", or 027 fails
and a conference committee's report has to be adopted by both houses, 032/058; 074 it failed); 090 "RETURN TO (S),
TRANSMIT TO GOVERNOR NEXT" (the second house passed it unchanged); 033 "9:15 A.M. 5/1/25 TRANSMITTED TO GOVERNOR"; 034
"SIGNED INTO LAW 6/24 CHAPTER 17 SLA 25", 036 "LAW W/O GOVERNOR SIGNATURE ...", 038 "VETOED BY GOVERNOR 5/19/25", 040
"GOVERNOR VETO OVERRIDDEN Y46 N14" (a joint session) and 129 "ASSIGNED CHAPTER 5 SLA 25", 039 "GOVERNOR VETO SUSTAINED".
The governor's lines are entered in the journal days or months later (the veto of SB 183 of 2025 on June 11 is in the
journal of July 30): their own wording gives the date. Some bills' actions stop before the governor's (12 laws of 2024,
"CHAPTER 38 SLA 24" only in the status): the status text decides laws and vetoes too. The record's Vetoed flag stays set
on vetoes that were overridden (HB 57 of 2025). Floor roll calls come member by member (Votes); committees have no roll
calls, only the recommendations. No "What it does": see load_session().
"""
import glob, json, os, re
from datetime import date, datetime
from zoneinfo import ZoneInfo

from states.ak import profile as P

HOUSE = {"S": "Senate", "H": "House"}
CURRENT = P.session_of(datetime.now(ZoneInfo(P.TIMEZONE)).year)
_PARTIES = {}
SKIP = {"105", "106", "107", "108", "103", "021", "041", "043", "048", "094", "095", "098", "042", "084", "087", "092",
        "100", "121", "130", "131", "132", "133", "011", "012", "013", "057", "124", "115", "136", "109", "059",
        "030", "050", "016", "017", "025", "062", "061", "126", "123", "078", "046", "047", "014", "018", "076", "019", "007"}


def folder(session):
    return os.path.join(P.DATA, str(session))


def sessions():
    return sorted(int(os.path.basename(f)) for f in glob.glob(os.path.join(P.DATA, "[0-9]" * 4))
                  if len(glob.glob(os.path.join(f, "bills", "*.json"))) > 100)


def text(x):
    return re.sub(r"\s+", " ", x or "").strip()


def is_amendment(b):
    return (b.get("BillNumber") or "")[:3] in ("HJR", "SJR") and bool(re.search(
        r"proposing (?:an )?amendments? to the constitution of the state of alaska", b.get("FullTitle") or "", re.I))


def number(b):
    """"HB  57" -> "HB57"; "HJR 12" -> "HJ12" (the site's two-letter kinds)."""
    m = re.match(r"([HS])(B|JR)\s*(\d+)", (b.get("BillNumber") or "").replace(" ", ""))
    return f"{m.group(1)}{'J' if m.group(2) == 'JR' else 'B'}{int(m.group(3))}" if m else None


def official(p):
    """"HJ12" -> "HJR 12", as the Legislature writes it."""
    return f"{p[0]}{'JR' if p[1] == 'J' else 'B'} {int(p[2:])}"


def tally(t):
    """"PASSED Y34 N6 E3" -> (34, 6); "Y20 N-" -> (20, 0)."""
    m = re.search(r"\bY(\d+|-)(?:\s+N(\d+|-))?", t)
    if not m:
        return None
    return (int(m.group(1)) if m.group(1).isdigit() else 0, int(m.group(2)) if m.group(2) and m.group(2).isdigit() else 0)


ABBREV = {"AK": "Alaska", "APPROP": "appropriation", "APPROPS": "appropriations", "MUNI": "municipal", "EXTND": "extend",
          "ADV": "advisory", "ACCT": "account", "PROG": "program", "PRGM": "program", "SVC": "service", "SVCS": "services",
          "GOV": "governor", "INS.": "insurance", "CORP.": "corporation", "EDU": "education", "MED.": "medical",
          "MED": "medical", "PERM": "permanent", "SUPP": "supplemental", "INFO": "information", "CHGS": "changes",
          "UNIV": "university", "CRIM.": "criminal", "BD": "board", "BDS": "boards", "BD.": "board", "COMP": "compensation",
          "CONST.": "constitutional", "CONST": "constitutional", "AM": "amendment", "DEPT": "department", "DEPT.": "department",
          "REG": "regulation", "REGS": "regulations", "TEMP": "temporary", "ENG": "engineering", "ARCH": "architecture",
          "LEG": "legislative", "AG": "agricultural", "EXEC.": "executive", "GOVT": "government", "COMM'N": "commission"}
UPPER = set("PFD POMV PFAS RCA AGDC AHFC TRS PERS BSA CPR SNAP UA DEED LB&A US U.S. AIDEA CBRF ERA GPS DNA DUI ATV DOT "
            "LLC LNG HIV AI ID REAL CO2 EV TV KTOO ANWR NPR-A II III IV VPSO PCE ESSER AMHS AHCC ARPA FY CDQ PF APOC SBA PTSD STEM "
            "K-12 ASMI RV REAA".split())
PROPER = re.compile(r"\b(alaska(?:n|ns)?|native|natives|cook inlet|juneau|anchorage|fairbanks|ketchikan|kodiak|sitka|"
                    r"denali|bristol bay|mat-su|matanuska|susitna|kenai|north slope|arctic|hispanic|heritage month|arbor day|"
                    r"permanent fund|marine highway|constitution|congress|medicaid|medicare|tribal|alaska railroad)\b", re.I)


def titled(short):
    """The short title in capitals -> a sentence: "CONST. AM: APPROP LIMIT" -> "Constitutional amendment: appropriation
    limit"; "AK COMMERCIAL FISHING & AG BANK; LOANS" -> "Alaska commercial fishing & agricultural bank; loans"."""
    words = []
    for w in re.split(r"(\s+|/|:|;|,)", text(short)):
        if not w.strip() or w in "/:;,":
            words.append(w)
            continue
        if w in UPPER:
            words.append(w)
        elif w in ABBREV:
            words.append(ABBREV[w])
        else:
            words.append(w.lower())
    t = "".join(words)
    t = re.sub(r"\s*:\s*", ": ", t)
    t = re.sub(r"\s*;\s*", "; ", t)
    t = PROPER.sub(lambda m: " ".join(x[:1].upper() + x[1:] for x in m.group(1).split(" ")), t)
    t = re.sub(r"(: |^)([a-z])", lambda m: m.group(1) + m.group(2).upper(), t, count=1)
    return t[:1].upper() + t[1:]


def full_title(b):
    """The official title without its quotes: "An Act relating to ...; and providing for an effective date."."""
    return text(b.get("FullTitle")).strip(' "').rstrip('"')


def text_date(t, journal, year_hint=None):
    """The date an action's own wording gives ("VETOED BY GOVERNOR 6/11/25", "SIGNED INTO LAW 6/24 CHAPTER 17 SLA 25",
    "9:15 A.M. 5/1/25 TRANSMITTED TO GOVERNOR"), when it's before the journal's and within a year of it."""
    m = re.search(r"\b(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?\b", t)
    if not m:
        return journal
    y = m.group(3)
    year = (2000 + int(y) if len(y) == 2 else int(y)) if y else (year_hint or int(journal[:4]))
    try:
        d = date(year, int(m.group(1)), int(m.group(2))).isoformat()
    except ValueError:
        return journal
    return d if d <= journal and (date.fromisoformat(journal) - date.fromisoformat(d)).days < 370 else journal


def chapter_of(t):
    """"... CHAPTER 17 SLA 25" / "CH 38 SLA 24" / "CHAPTER 1 FSSLA 25" -> (17, "SLA", 2025)."""
    m = re.search(r"\bCH(?:APTER)?\.? (\d+),? (\w*SLA) (\d{2})\b", t)
    return (int(m.group(1)), m.group(2), 2000 + int(m.group(3))) if m else None


def law_name(ch):
    """(17, "SLA", 2025) -> "Chapter 17, SLA 2025" (session laws of Alaska; FSSLA: of the first special session)."""
    return f"Chapter {ch[0]}, {ch[1]} {ch[2]}"


def committees(session):
    """Committee code -> name, from committees.json (each house's standing and special committees) and P.COMMITTEES."""
    out = dict(P.COMMITTEES)
    try:
        for c in json.load(open(os.path.join(folder(session), "committees.json"))):
            if c.get("Catagory") in ("Standing Committee", "Special Committee") and c.get("Code") not in out:
                out[c["Code"]] = re.sub(r"^Special Committee on ", "", committee_name(c.get("Name")))
    except (OSError, ValueError):
        pass
    return out


SMALL = {"and", "of", "the", "on", "for", "to", "in"}


def committee_name(n):
    """"LABOR & COMMERCE" -> "Labor and Commerce"; "MILITARY & VETERANS' AFFAIRS" -> "Military and Veterans' Affairs"."""
    words = text(n).replace("&", "and").lower().split(" ")
    return " ".join(w if i and w in SMALL else w[:1].upper() + w[1:] for i, w in enumerate(words))


def members(session):
    """The session's members: (house, code) -> member, code -> seat id ("S:1" for district A, "H:12"). Members who
    left are left out of the seats (their votes are "H?Tilton"), except a member who changed name (Burke, now Frier: the
    old code takes the same seat), and old name -> new name."""
    try:
        ms = json.load(open(os.path.join(folder(session), "members.json")))
    except (OSError, ValueError):
        ms = []
    def sid(m):
        d = (m.get("District") or "").strip()
        return f"S:{P.senate_number(d)}" if m.get("Chamber") == "S" and re.fullmatch(r"[A-T]", d) else \
            f"H:{int(d)}" if m.get("Chamber") == "H" and d.isdigit() else None
    seats, by = {}, {}
    for m in ms:
        by[(m.get("Chamber"), m.get("Code"))] = m
        if m.get("IsActive") and sid(m):
            seats[(m["Chamber"], m["Code"])] = sid(m)
    renamed = {}
    for m in ms:
        if re.search(r"Name Changed", m.get("Comment") or "", re.I) and sid(m):
            now = next((x for x in ms if x is not m and x.get("IsActive") and sid(x) == sid(m)
                        and not re.search(r"Name Changed", x.get("Comment") or "", re.I)), None)
            if now:
                seats[(m["Chamber"], m["Code"])] = sid(m)
                renamed[person(m)] = person(now)
    return by, seats, renamed


def person(m):
    return text(f"{m.get('FirstName') or ''} {m.get('LastName') or ''}")


PARTY = {"D": "D", "R": "R", "N": "I"}


def floor_question(title):
    """A roll call's question, from its title lines ("SB 183 | Third Reading - Final Passage | Effective Date(s)"): the
    bill's own questions (passage, concurrence, a conference report, a veto override) -> a short kind; else None."""
    parts = [x.strip() for x in (title or "").replace("\r", "").split("\n") if x.strip()]
    parts = [x for x in parts if x not in ("HOUSE", "SENATE")][1:]  # the chamber and the bill's version
    q = " | ".join(parts)
    if re.match(r"Third Reading(?: - | \| )(?:Final Passage|On Reconsideration)", q) or re.fullmatch(r"Third Reading \| Final Passage.*", q):
        return "passage"
    if re.match(r"(?:Concur\b|Shall the Senate Concur)", q, re.I):
        return "concur"
    if re.match(r"(?:Adopt(?: \||$)|Shall the Senate Adopt the Conference)", q, re.I) or q == "Adopt":
        return "conference"
    if re.match(r"Shall the Senate recede", q, re.I):
        return "recede"
    if re.match(r"Veto Override", q):
        return "override"
    return None


def load_session(session):
    """Read one Legislature's bills and return (records, bill number -> record index, fetched time, delegation)."""
    names = committees(session)
    by_member, seats, renamed = members(session)
    lasts = {}
    for (h, code), m in by_member.items():
        lasts[(h, (m.get("LastName") or "").upper())] = m.get("LastName")
    parties = _PARTIES.setdefault(session, {})
    files = glob.glob(os.path.join(folder(session), "bills", "*.json"))
    fetched = datetime.fromtimestamp(max(os.path.getmtime(f) for f in files), ZoneInfo(P.TIMEZONE)).strftime("%Y-%m-%d %H:%M")
    recs, index = [], {}
    order = lambda f: (os.path.basename(f)[0], len(re.sub(r"\d", "", os.path.basename(f))), int(re.sub(r"\D", "", os.path.basename(f)) or 0))
    for f in sorted(files, key=order):
        b = json.load(open(f))
        p = number(b)
        amendment = is_amendment(b)
        if not p or (p[1] == "J" and not amendment) or text(b.get("ShortTitle")) == "NOT INTRODUCED":
            continue  # (a number held for a bill that was never introduced)
        origin = p[0]
        other = "S" if origin == "H" else "H"
        cname = lambda code: names.get(code, committee_name(code))
        # Each house's committees in order ("HL&C", "HEDC", "SFIN"; the record keeps the final list).
        plan = {"H": [], "S": []}
        for r in b.get("Referrals") or []:
            if r[:1] in plan and r[1:] in names:
                plan[r[0]].append(r[1:])
        steps = []  # (date, house, shared or plain wording, code)
        passed, both, sent, vetoed, conf = set(), False, False, False, {}
        last_vote = {}  # house -> "passage" / "concur": what a rescinding undoes
        where_h, place, explicit, reported = origin, "committee", None, {"H": set(), "S": set()}
        chapter, first_ref = None, None
        acts = [a for a in b.get("Actions") or [] if a.get("Code") not in SKIP]
        i = 0
        while i < len(acts):
            a = acts[i]
            code, h, t, d = a.get("Code"), a.get("Chamber") or "", text(a.get("Text")), a.get("JrnDate") or ""
            i += 1
            if code in ("T", "M"):
                # A committee hearing's result: keep "Heard & Held" (a hearing with no vote yet); the report says the rest.
                if code == "T" and re.match(r"Heard & Held", t) and h[:1] in HOUSE and h[1:] in names:
                    steps.append((d, h[0], f"Heard and held in the {cname(h[1:])} Committee", code))
                continue
            if h not in HOUSE:
                continue
            if code in ("001", "052"):
                where_h, place, explicit = h, "committee", None
                refs = []
                if i < len(acts) and acts[i].get("Code") == "091":
                    refs = [x.strip() for x in text(acts[i].get("Text")).split(",") if x.strip()]
                    i += 1
                refs = [x for x in refs if x in names]
                if refs and first_ref is None and h == origin:
                    first_ref = refs[0]
                lead = "Sponsor substitute introduced" if code == "052" else "Read the first time"
                steps.append((d, h, f"{lead}; referred to {', then '.join(cname(x) for x in refs)}" if refs else lead, code))
                if refs:
                    steps.append((d, h, f"REFERRED TO {cname(refs[0]).upper()}", "ref"))
                continue
            if code == "091":
                continue
            if code == "002":
                c = t.split(" ")[0]
                reported[h].add(c)
                if explicit == c:
                    explicit = None
                # The members' recommendations that follow: "DP: CARRICK, SADDLER", "NR: NELSON", "AM: ...", "DNP: ...".
                recs_ = []
                while i < len(acts) and acts[i].get("Code") == "063":
                    m = re.match(r"(DP|NR|AM|DNP):\s*(.*)$", text(acts[i].get("Text")))
                    if m:
                        who = [lasts.get((h, x.strip()), x.strip().title()) for x in m.group(2).split(",") if x.strip()]
                        recs_.append((m.group(1), who))
                    elif recs_:  # a list carried onto the next line
                        recs_[-1][1].extend(lasts.get((h, x.strip()), x.strip().title()) for x in text(acts[i].get("Text")).split(",") if x.strip())
                    i += 1
                steps.append((d, h, "REPORTED", code))
                words = {"DP": "do pass", "NR": "no recommendation", "AM": "amend", "DNP": "do not pass"}
                if recs_:
                    steps.append((d, h, f"{cname(c)} Committee report: " + "; ".join(f"{words[k]} ({', '.join(v)})" for k, v in recs_), "063"))
                # On to the next committee in the list, or to the Rules Committee.
                nxt = next((x for x in plan[h] if x not in reported[h]), None)
                if nxt and c != "RLS":
                    steps.append((d, h, f"REFERRED TO {cname(nxt).upper()}", "ref"))
                continue
            if code == "063":
                continue
            if code in ("003", "051"):
                m = re.match(r"(?:REFERRED|RETURNED) TO (?:THE )?(.+?)(?: COMMITTEE)?(?:\s+Y\d+.*)?$", t)
                c = next((k for k, v in names.items() if m and (v.upper() == m.group(1).replace("&", "AND") or k == m.group(1))), None)
                if m and m.group(1) in ("RLS", "RULES"):
                    c = "RLS"
                if c:
                    explicit, place, where_h = c, "committee", h
                    reported[h].discard(c)
                    if not steps or steps[-1][2] != f"REFERRED TO {cname(c).upper()}":
                        steps.append((d, h, f"REFERRED TO {cname(c).upper()}" if code == "003" else f"Sent back to the {cname(c)} Committee", code))
                continue
            if code in ("004", "006"):
                steps.append((d, h, re.sub(r"\b([A-Z&]{2,4})\b", lambda m: cname(m.group(1)) if m.group(1) in names else m.group(1), t).capitalize(), code))
                continue
            if code in ("080", "086", "082"):
                place, where_h = "floor", h
                steps.append((d, h, "The Rules Committee put it on the calendar", code))
                continue
            if code == "008":
                place, where_h = "floor", h
                steps.append((d, h, "Read the second time (amendments can be offered)", code))
                continue
            if code in ("009", "122", "056"):
                # "FIN SCS ADOPTED UC", "L&C HCS ADOPTED Y28 N10 A2", "FAILED TO ADOPT FIN HCS Y16 N23 A1": a committee's
                # rewritten version (committee substitute) taken up on the floor.
                m = re.search(r"(?:^|ADOPT )(\S+) [HS]?C?S\b", t)
                tl = tally(t)
                if m and m.group(1) in names:
                    steps.append((d, h, f"The {cname(m.group(1))} Committee's version {'was not' if code == '056' else 'was'} adopted"
                                  + (f", {tl[0]}-{tl[1]}" if tl else ""), code))
                continue
            if code == "125":
                if re.search(r"\bCONCUR", t):
                    last_vote[h] = "concur"
                elif not re.search(r"\bPASS(?:ING|AGE)\b", t):
                    continue  # an amendment's vote rescinded
                code = "128"
            if code in ("015", "097"):
                steps.append((d, h, "Advanced to third reading (the vote)", code))
                continue
            if code in ("020", "024"):
                passed.add(h)
                last_vote[h] = "passage"
                place = "desk"
                where_h = other if h == origin else origin
                tl = tally(t)
                steps.append((d, h, f"PASSED {HOUSE[h].upper()}", code))
                if tl:
                    steps.append((d, h, f"The {HOUSE[h]} vote: {tl[0]}-{tl[1]}" + (" (on reconsideration)" if code == "024" else ""), "tally"))
                continue
            if code == "060":
                passed.discard(h)
                tl = tally(t)
                steps.append((d, h, f"Failed to pass the {HOUSE[h]}" + (f", {tl[0]}-{tl[1]}" if tl else ""), code))
                continue
            if code == "128":  # (also 125 on a passage, above)
                # Undoes the house's last vote on the bill (its passage, or its concurrence), which it then takes again.
                if last_vote.get(h) == "passage":
                    passed.discard(h)
                elif last_vote.get(h) == "concur":
                    both = False
                last_vote.pop(h, None)
                steps.append((d, h, "The vote was rescinded, to take it again", code))
                continue
            if code == "022":
                where_h, place = other if h == origin else origin, "committee"
                steps.append((d, h, f"DELIVERED TO {HOUSE[other if h == origin else origin].upper()}", code))
                continue
            if code == "083":
                to = other if h == origin else origin
                steps.append((d, h, f"Sent back to the {HOUSE[to]} with the {HOUSE[h]}'s changes", code))
                continue
            if code == "090":
                both = True
                steps.append((d, h, "Passed both houses (the second house didn't change it)", code))
                continue
            if code == "026":
                both = True
                last_vote[h] = "concur"
                tl = tally(t)
                steps.append((d, h, f"The {HOUSE[h]} agreed to the other house's changes" + (f", {tl[0]}-{tl[1]}" if tl else ""), code))
                continue
            if code in ("027", "028"):
                if code == "027":
                    both = False
                steps.append((d, h, (f"The {HOUSE[h]} refused the other house's changes" if code == "027" else f"The {HOUSE[h]} refused to drop its changes"), code))
                continue
            if code in ("029", "031"):
                steps.append((d, h, "Conference committee appointed" if code == "029" else "The conference committee may write a new version (free conference)", code))
                continue
            if code in ("032", "058", "074"):
                ok = code != "074"
                conf[h] = ok
                tl = tally(t)
                steps.append((d, h, f"The {HOUSE[h]} {'adopted' if ok else 'rejected'} the conference committee's report" + (f", {tl[0]}-{tl[1]}" if tl else ""), code))
                if conf.get("H") and conf.get("S"):
                    both = True
                continue
            if code == "033":
                sent = both = True
                steps.append((text_date(t, d), h, "DELIVERED TO GOVERNOR", code))
                continue
            if code in ("034", "036", "129"):
                ch = chapter_of(t)
                if ch:
                    chapter = ch
                if code == "034":
                    steps.append((text_date(t, d, ch[2] if ch else None), "G", f"SIGNED CHAPTER {ch[0]}" if ch else "SIGNED", code))
                elif code == "036":
                    steps.append((text_date(t, d, ch[2] if ch else None), "G", "Became law without the governor's signature" + (f" ({law_name(ch)})" if ch else ""), code))
                else:
                    steps.append((d, h, f"Law: {law_name(ch)}" if ch else t.capitalize(), code))
                continue
            if code == "035":
                steps.append((d, "G", "Signed with line-item vetoes and reductions", code))
                continue
            if code == "038":
                vetoed = True
                steps.append((text_date(t, d), "G", "VETOED", code))
                continue
            if code in ("039", "040"):
                tl = tally(t)
                steps.append((d, h, ("Veto overridden by the Legislature in joint session" if code == "040" else
                                     "The override failed in joint session; the veto stands") + (f", {tl[0]}-{tl[1]}" if tl else ""), code))
                continue
            if code in ("053", "089", "101"):
                steps.append((d, h, {"053": "Withdrawn by the sponsor", "089": f"Permanently filed in the {HOUSE[h]}",
                                     "101": "Not introduced"}[code], code))
                continue
            if code in ("023", "064", "135"):
                if code == "023":
                    steps.append((d, h, f"{t.split(' NOTICE')[0].title()} gave notice of reconsideration", code))
                continue
            if code == "077" and re.search(r"FIRST SPECIAL SESSION BILL|SPECIAL SESSION", t):
                steps.append((d, h, "Taken up in the special session", code))
                continue
        # The status text, for histories that stop early (HB 371 of 2023-24: "CHAPTER 38 SLA 24", no governor's lines).
        status = text(b.get("StatusText"))
        if not chapter and chapter_of(status):
            chapter = chapter_of(status)
            steps.append((b.get("StatusDate") or (steps[-1][0] if steps else ""), "G", f"Law: {law_name(chapter)}", "status"))
        if re.match(r"VETO(?:ED BY GOVERNOR| SUSTAINED)", status) and not vetoed:
            vetoed = True
            steps.append((b.get("StatusDate") or "", "G", "VETOED", "status"))
        steps.sort(key=lambda s: s[0])  # by day; the file's order within a day
        if amendment:
            stage = 3 if both else (2 if passed else None)
        elif chapter:
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
        if stage is not None and stage >= 3:
            passed = {"S", "H"}
        comm = None
        if place == "committee":
            comm = explicit or next((x for x in plan[where_h] if x not in reported[where_h]), None)
            if comm is None and (reported[where_h] or passed):
                comm = "RLS"  # every committee reported: the Rules Committee decides when it reaches the floor
        if stage is None:
            stage = 1 if place == "floor" else 0
        comm = cname(comm) if comm else None
        refs = [(h, cname(c)) for h in ("H", "S") for c in plan[h]]
        if first_ref is None and plan[origin]:
            first_ref = plan[origin][0]
        comm_list = sorted({f"{h} · {c}" for h, c in refs})
        title = titled(b.get("ShortTitle"))
        if amendment:
            title = re.sub(r"^Constitutional amendment[:/]?\s*", "", title)
            title = f"Constitutional amendment: {title if PROPER.match(title) or title[:2].isupper() else title[:1].lower() + title[1:]}"
        long_title = full_title(b)
        subjects = [text(s) for s in b.get("Subjects") or []]
        topics = list(dict.fromkeys((["const"] if amendment else []) +
                                    [P.COMMITTEE_TOPICS[c] for h in plan for c in plan[h] if c in P.COMMITTEE_TOPICS] +
                                    [P.SUBJECT_TOPICS[s] for s in subjects if s in P.SUBJECT_TOPICS] +
                                    [k for k in P.TOPIC_WORDS if P.TOPIC_WORDS[k].search(title)]))
        left = bool(first_ref and first_ref in reported[origin]) or bool(passed)
        fate = "passed" if left else "none"
        # Sponsors in order: members ("Fields"), or a committee: "Rules Committee, by request of the governor".
        names_, governor = [], False
        for s in sorted(b.get("Sponsors") or [], key=lambda s: (not s.get("isPrime"), s.get("SponsorSeq") or "")):
            m = s.get("SponsoringMember")
            if m:
                n = renamed.get(person(m), person(m))  # Burke's bills under her new name, Frier
                if PARTY.get(m.get("Party")) in ("D", "R"):
                    parties[(m.get("Chamber"), n)] = m["Party"]
            elif s.get("SponsoringCommittee"):
                c = s["SponsoringCommittee"]
                req = text(s.get("Requestor"))
                n = f"{HOUSE.get(c.get('Chamber'), '')} {committee_name(c.get('Name'))} Committee".strip()
                if re.match(r"THE GOVERNOR", req):
                    n += ", by request of the governor"
                    governor = True
            else:
                continue
            if n and n not in names_:
                names_.append(n)
        sponsor = names_[0] if names_ else "—"
        cos = names_[1:]
        if stage == 0:
            desc = f"In {HOUSE[where_h]} committee"
        elif stage == 1:
            desc = f"On the {HOUSE[where_h]} floor"
        else:
            desc = {2: f"Passed the {HOUSE[origin] if origin in passed else HOUSE[other]}", 3: "Passed both houses",
                    4: "On the governor's desk", 5: "Became law", 6: "Vetoed"}[stage]

        def dates(test, mode="last"):
            ds = sorted({s[0] for s in steps if test(s[1], s[2], s[3]) and s[0]})
            return {"first": ds[0], "last": ds[-1], "all": ";".join(ds)}[mode] if ds else ""

        # Floor roll calls on the bill's own questions, member by member: "Y", "N", "E" (excused), "A" (absent).
        calls = {}
        for v in b.get("Votes") or []:
            calls.setdefault(v.get("VoteNum"), []).append(v)
        votes = []
        for num, rows in calls.items():
            q = floor_question(rows[0].get("Title"))
            h = (num or "")[:1]
            if not q or h not in HOUSE:
                continue
            yes = sum(1 for r in rows if text(r.get("Vote")) == "Y")
            no = sum(1 for r in rows if text(r.get("Vote")) == "N")
            listed = [[seats.get((r.get("MemberChamber"), r.get("Member"))) or
                       f"{r.get('MemberChamber')}?{text(r.get('MemberName'))}", text(r.get("Vote"))]
                      for r in rows if text(r.get("Vote")) in ("N", "E", "A")]
            votes.append([h, "F", None, (rows[0].get("VoteDate") or "")[:10], yes, no, listed])
        votes.sort(key=lambda v: v[3])
        action_dates = [s[0] for s in steps if s[0]]
        rec = {
            "nums": [p], "base": [p], "prev": earlier(session, b, p),
            "title": title, "summary": long_title, "act": "", "lawCode": "", "law": None, "laws": [],
            "comms": comm_list, "topics": topics, "places": [], "narrow": P.narrow_kind(title),
            "commFate": fate, "mainTopic": topics[0] if topics else "", "local": "local" in topics,
            "senDeleg": False, "asmDeleg": False,
            "budget": bool(re.match(r"An Act making (?:and amending )?(?:supplemental |special )?appropriations", long_title, re.I)),
            "passedS": "S" in passed, "passedA": "H" in passed, "program": None,
            "stage": stage, "passedIn": (HOUSE[origin] if origin in passed else HOUSE[other]) if stage == 2 else None,
            "chapter": chapter[0] if chapter and stage == 5 else None,
            "veto": None, "memo": "", "vetoMemo": None,
            "simText": f"{title} {long_title}",
            "comm": comm if stage == 0 and place == "committee" else None,
            "first": min(action_dates, default=f"{session}-01-01"),
            "last": max(action_dates, default=f"{session}-01-01"),
            "cosp": len(cos),
            "keyDates": [
                dates(lambda h, t, c: t == "REPORTED", "first"),
                dates(lambda h, t, c: t == "PASSED SENATE", "all"),
                dates(lambda h, t, c: t == "PASSED HOUSE", "all"),
                "",
                dates(lambda h, t, c: t == "DELIVERED TO GOVERNOR") if stage >= 4 and not amendment else "",
                dates(lambda h, t, c: t.startswith("SIGNED") or t.startswith("Became law") or c == "129" or c == "status" and t.startswith("Law"))
                if stage == 5 else "",
                dates(lambda h, t, c: t == "VETOED"),
            ],
            "votes": votes, "firstComms": [(origin, cname(first_ref), left)] if first_ref else [],
            "vers": [{"p": p, "sponsor": sponsor, "district": 0, "cosponsors": cos, "primes": 1, "cosp": len(cos),
                      "statusDesc": desc, "committee": comm if place == "committee" and stage in (0, 2) else None,
                      "actions": [[s[0], s[2]] for s in steps]}],
        }
        index[p] = len(recs)
        recs.append(rec)
    # No "What it does": the only plain-language account is each sponsor's statement, an advocate's case for the bill as
    # introduced (HB 57 of 2025's is about phones in classrooms; the law became the education funding bill), with
    # letterheads and staff contacts mixed in. The official title (the summary) says what the bill touches.
    return recs, index, fetched, {"SENATE": [], "ASSEMBLY": []}


_TITLES = {}


def _titles(session):
    if session not in _TITLES:
        out = {}
        for f in glob.glob(os.path.join(folder(session), "bills", "*.json")):
            b = json.load(open(f))
            p = number(b)
            if not p or (p[1] == "J" and not is_amendment(b)) or chapter_of(text(b.get("StatusText"))):
                continue  # a law isn't tried again (yearly bills like the budget share titles)
            prime = next((person(s["SponsoringMember"]) for s in b.get("Sponsors") or [] if s.get("isPrime") and s.get("SponsoringMember")), "")
            out.setdefault(text(b.get("ShortTitle")).lower(), []).append((p, prime))
        _TITLES[session] = out
    return _TITLES[session]


def earlier(session, b, p):
    """The same bill in the Legislature before: the same short title with the same prime sponsor, or a short title only
    one bill has in each."""
    out = set()
    k = text(b.get("ShortTitle")).lower()
    who = next((person(s["SponsoringMember"]) for s in b.get("Sponsors") or [] if s.get("isPrime") and s.get("SponsoringMember")), "")
    if len(k.split()) < 2 or re.match(r"approp", k):
        return out
    y = session - 2
    if y in sessions():
        old = _titles(y).get(k, [])
        same = [n for n, sp in old if sp and sp == who]
        if same:
            out.add((y, same[0]))
        elif len(old) == 1 and len(_titles(session).get(k, [])) == 1:
            out.add((y, old[0][0]))
    return out


def agendas(session):
    """Bills on upcoming committee meetings (each bill's Meetings, read with the bill): bill -> [["House Labor and
    Commerce", "2027-02-03T15:15:00"], ...]."""
    names = committees(session)
    today = date.today().isoformat()
    out = {}
    for f in glob.glob(os.path.join(folder(session), "bills", "*.json")):
        b = json.load(open(f))
        p = number(b)
        if not p:
            continue
        for m in b.get("Meetings") or []:
            if (m.get("MeetingDate") or "") < today or m.get("MeetingCanceled") or re.search(r"Canceled|Not Heard", m.get("BillChangeText") or "", re.I):
                continue
            h = HOUSE.get(m.get("Chamber"))
            c = names.get(m.get("MeetingSponsor"))
            if not h or not c:
                continue
            entry = [f"{h} {c}", f"{m['MeetingDate']}T{(m.get('MeetingTime') or '00:00:00')[:8]}"]
            if entry not in out.setdefault(p, []):
                out[p].append(entry)
    return out


def parties(session, recs):
    return {k: v for k, v in _PARTIES.get(session, {}).items() if v in ("D", "R")}
