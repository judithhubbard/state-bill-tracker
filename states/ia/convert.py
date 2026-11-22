"""Iowa's bills (downloaded by states/ia/fetch.py from www.legis.iowa.gov, and first from Open States by
states/ia/openstates.py and states/openstates_bulk.py) in the shape build_data.py reads.

A page is a two-year General Assembly, named by its first year (2025 is the 91st, 2025-26): bill numbers run through both
years (the second year's from HF 2000 and SF 2000), and a bill not passed in the first year carries over to the second
where it stands ("* * * * * END OF 2025 ACTIONS * * * * *"). House and Senate Files (HF, SF) and the joint resolutions
proposing amendments to the Constitution of the State of Iowa (HJR, SJR; "A joint resolution proposing an amendment to the
Constitution of the State of Iowa ..."), tagged "const": a majority of each house's members in two General Assemblies in a
row, then the voters at a general election; never the governor ("Sent to Secretary of State"). Other joint resolutions
(state symbols, nullifying agencies' rules, calls for an Article V convention) and resolutions are left out.

Each bill comes from its official history page (data/ia/<year>/bills/HF100.html) when fetch.py has read it, else from its
Open States record (data/ia/<year>/openstates/HF100.json, public domain, copied from the same pages). A page holds the
histories of every related bill ("All Related Bills": the study bill it came from, earlier and later numbers, its
companion), one section each, so a bill's history is its own page's section, else its section on another bill's page,
else its Open States record. Both carry the same lines; the page's end in the journal page ("H.J. 120", "S.J. 172"),
which names the house that acted, and Open States gives the house as the line's organization (lower, upper, or
"legislature" for subcommittee lines and others, which happen where the bill is). `python3 -m states.ia.convert compare
2025` converts every bill both ways and lists the stages that differ.

Renumbering. Iowa's committees report a bill by giving it a new number: a committee's draft (a study bill, HSB or SSB) or
a member's bill the committee rewrites becomes a committee bill ("Committee report approving bill, renumbered as HF 581";
the new bill's title says "(Formerly HF 130.)"), and a bill can be renumbered again by the next committee (HF 130, HF
581, HF 971, HF 2353, HF 2741). Each chain is one record under its newest number, with the others as earlier numbers and
their histories in order; the member who filed the first one is its sponsor. Study bills never renumbered are committee
drafts that never became bills and aren't shown; a study bill's history is part of its bill's record when it's been read
(Open States has 2023-24's; 2025-26's come only from the pages). Companions (a House and a Senate bill with the same
text, "(C) SF 583") stay separate records: when one passes, the other house takes it up in place of its own ("Substituted
for HF 163."; the other "SF 583 substituted.", then "Withdrawn."), shown as replaced (`STATE.endedNote()`).

The history:
- "Introduced, referred to Transportation." (a member's bill: to a committee, then a subcommittee of three: "Subcommittee:
  Wood, Scholten and Williams.", "Subcommittee Meeting: 02/05/2025 12:45PM House Lounge.", "Subcommittee recommends
  passage."); "Introduced, placed on calendar." (a committee's bill, already approved: on the floor); "Introduced, placed
  on Appropriations calendar" / "Ways and Means calendar" (the money committees' own bills, on the floor).
- "Committee report, recommending [amendment and] passage." with "Committee vote: Yeas, 20. Nays, 0. Excused, 1." (a
  tally; no names), then "Placed on calendar."; "Committee report approving bill, renumbered as ..." (above);
  "Referred to"/"Rereferred to" (another committee, often Appropriations or Ways and Means). Committees don't vote bills
  down on the record: most bills die in committee at the "funnel" deadlines, with no line saying so.
- "Passed House, yeas 99, nays 0." is the passage ("Failed to pass" a defeat; "Motion to reconsider vote prevailed"
  undoes it). "Message from House." / "Read first time, referred to Education." is the other house receiving it; "Read
  first time, passed on file." / "attached to SF 583" puts it on the calendar with its companion.
- The second house passing it with amendments sends it back ("Message from Senate, with amendment H-1354", "Senate
  amendment H-1354 filed."): the first house concurs and passes it again ("House concurred in Senate amendment H-1354."
  then "Passed House"), or a conference committee settles it. "Reported correctly enrolled, signed by Speaker and
  President, and sent to Governor." is passed both houses and sent.
- "Signed by Governor." (a law), "Item vetoed, signed by Governor." (a law with items vetoed: budget bills), "Vetoed by
  Governor."; the chapter of the year's Iowa Acts is a document link on the page ("Acts Chapter 46", /iactc/91.1/:
  the 91st General Assembly's first session) or in Open States' documents (2023-24).
Lines aren't always in date order (they're in journal order): sorted by day, the source's order kept within a day.

Votes: each passage member by member from Open States' roll call ("Shall the bill pass?") of that house, day and tally,
else the history's tally (Open States has roll calls for about half of the passages; fetch.py's roll-call PDFs aren't
read here yet). 2025-26's roll calls name each voter's Open States person, with district; 2023-24's give surnames, tied to
this General Assembly's members within the house when only one has that surname. Committee votes are the history's
tallies, with no names.

"What it does": the Legislative Services Agency's explanation from the bill as introduced (texts/<bill>.json, read by
fetch.py) when it's there, labelled as describing the bill as introduced; otherwise none (the title is the official one).
"""
import csv, glob, html as H_, json, os, re, sys, unicodedata
from collections import Counter, defaultdict
from datetime import date, datetime
from zoneinfo import ZoneInfo

from states.ia import profile as P
from states.ia import vetoes as V
from states.undated import settle

HOUSE = {"S": "Senate", "H": "House"}
OTHER = {"S": "H", "H": "S"}
ORG = {"upper": "S", "lower": "H"}
BILL = re.compile(r"(HF|SF|HJR|SJR)\d+")
ANY = re.compile(r"(HF|SF|HJR|SJR|HSB|SSB)\d+")
AMENDMENT = re.compile(r"^A joint resolution proposing (?:an amendment|amendments) to the Constitution of the State of Iowa", re.I)
MONTHS = {m: i for i, m in enumerate(["January", "February", "March", "April", "May", "June", "July", "August",
                                      "September", "October", "November", "December"], 1)}
_CACHE, _PARTIES = {}, {}


def load(path, default=None):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def folder(session):
    return os.path.join(P.DATA, str(session))


def text(fragment):
    return re.sub(r"\s+", " ", H_.unescape(re.sub(r"<[^>]+>", " ", fragment or ""))).strip()


def tidy(s):
    """" Passed House , yeas 93" -> "Passed House, yeas 93"."""
    return re.sub(r"\s+([,.;)])", r"\1", re.sub(r"\(\s+", "(", s or "")).strip()


def fold(s):
    s = unicodedata.normalize("NFKD", s or "")
    return re.sub(r"[^a-z]", "", "".join(c for c in s if not unicodedata.combining(c)).lower())


def key_of(s):
    """"HF 581" / "House File 581" / "HSB 47" -> "HF581"."""
    s = (s or "").strip()
    m = re.match(r"(House|Senate) (File|Joint Resolution|Study Bill) (\d+)$", s)
    if m:
        return m.group(1)[0] + {"File": "F", "Joint Resolution": "JR", "Study Bill": "SB"}[m.group(2)] + m.group(3)
    return re.sub(r"\s+", "", s).upper()


def spaced(k):
    return re.sub(r"^([A-Z]+)(\d)", r"\1 \2", k)


def sessions():
    if "sessions" in _CACHE:
        return _CACHE["sessions"]
    out = []
    for f in sorted(os.listdir(P.DATA)) if os.path.isdir(P.DATA) else []:
        # A General Assembly of this year or later counts from its first bills (prefiled ones); an older one from 500.
        if re.fullmatch(r"\d{4}", f) and int(f) % 2 and len(glob.glob(os.path.join(P.DATA, f, "openstates", "*.json"))
                                                              + glob.glob(os.path.join(P.DATA, f, "bills", "*.html"))) \
                > (0 if int(f) >= datetime.now().year else 500):
            out.append(int(f))
    _CACHE["sessions"] = out
    return out


def listing(session):
    k = (session, "list")
    if k not in _CACHE:
        _CACHE[k] = (load(os.path.join(folder(session), "list.json"), {}) or {}).get("bills") or {}
    return _CACHE[k]


def all_keys(session):
    """Every bill and study bill of the General Assembly the data knows of."""
    ks = {k for k in listing(session) if ANY.fullmatch(k)}
    for sub in ("openstates", "bills", "study"):
        for f in glob.glob(os.path.join(folder(session), sub, "*.*")):
            k = os.path.basename(f).split(".")[0]
            if ANY.fullmatch(k):
                ks.add(k)
    ks |= set(page_sections(session))
    return sorted(ks, key=lambda k: (k[0] != "H", re.sub(r"\d", "", k), int(re.sub(r"\D", "", k))))


def iso_long(s):
    """"January 23, 2025" -> "2025-01-23"."""
    m = re.match(r"([A-Z][a-z]+) (\d{1,2}), (\d{4})", (s or "").strip())
    return f"{m.group(3)}-{MONTHS[m.group(1)]:02d}-{int(m.group(2)):02d}" if m and m.group(1) in MONTHS else ""


# ---- The official pages ----

def parse_page(s, ga):
    """One history page -> {bill: section}: each "Bill History for" section's title, sponsors (the first section's only),
    actions [(day, house, line)] and chapter."""
    out = {}
    starts = [m for m in re.finditer(r"Bill History for <a[^>]*ba=([A-Z]+ ?\d+)\"[^>]*>", s)]
    for i, m in enumerate(starts):
        part = s[m.start():starts[i + 1].start() if i + 1 < len(starts) else len(s)]
        k = key_of(m.group(1))
        sponsors = []
        by = re.search(r'class="divideVert">By\s*(.*?)</div>', part, re.S)
        if by and i == 0:
            sponsors = split_names(text(by.group(1)))
        if i == 0:
            tm = re.search(r'class="divideVert">By.*?</div>\s*<div>(.*?)</div>', part, re.S)
        else:
            tm = re.search(r'<div style="margin:10px">\s*<div>(.*?)</div>', part, re.S)
        title = tidy(text(tm.group(1))) if tm else ""
        actions = []
        for d, body in re.findall(r'<td(?:\s+sorttable_customkey="\d+")?>\s*([A-Z][a-z]+ \d\d, \d{4})\s*</td>\s*<td>.*?</td>\s*'
                                  r'<td\s*>(.*?)</td>', part, re.S):
            line = tidy(text(body))
            jm = re.search(r"\s*\b([HS])\.J\. [\d/]+\.?$", line)
            h = jm.group(1) if jm else ""
            if jm:
                line = line[:jm.start()].rstrip()
            line = line.rstrip()
            if line and not line.endswith("."):
                line += "."
            if line:
                actions.append((iso_long(d), h, line))
        chap = None
        cm = re.search(r"iactc/(\d+)\.(\d)/CH0*(\d+)\.pdf", part)
        if cm:
            chap = (int(cm.group(3)), first_year(int(cm.group(1))) + int(cm.group(2)) - 1)
        out[k] = {"key": k, "title": title, "sponsors": sponsors, "actions": actions, "chapter": chap, "source": "page"}
    return out


def first_year(ga):
    return 1845 + 2 * (ga - 1)


def page_sections(session):
    """Every section of every page read: bill -> section, a bill's own page first, else the newest page that has it."""
    k = (session, "sections")
    if k in _CACHE:
        return _CACHE[k]
    own, other = {}, {}
    files = sorted(glob.glob(os.path.join(folder(session), "bills", "*.html")) + glob.glob(os.path.join(folder(session), "study", "*.html")),
                   key=os.path.getmtime)
    for f in files:
        name = os.path.basename(f)[:-5]
        try:
            secs = parse_page(open(f, encoding="utf-8").read(), P.ga_of(session))
        except OSError:
            continue
        for bk, sec in secs.items():
            if bk == name:
                own[bk] = sec
            else:
                other[bk] = sec
    out = dict(other)
    out.update(own)
    _CACHE[k] = out
    return out


def split_names(s):
    """"Levin, Kurth, Wessel-Kroeschell, R. Johnson, Meyer, B and Wilburn" -> [("Levin", False), ...]; "Amos, Jr." and
    "Meyer, B" rejoin the name before them."""
    out = []
    for tok in re.split(r",\s*|\s+and\s+", s or ""):
        tok = tok.strip()
        if not tok:
            continue
        if out and re.fullmatch(r"(?:[A-Z]\.?|Jr\.?|Sr\.?|II|III|IV)", tok):
            out[-1] = (f"{out[-1][0]}, {tok}", False)
        else:
            out.append((tok, False))
    return out


# ---- Open States records ----

def from_openstates(session, k):
    d = load(os.path.join(folder(session), "openstates", f"{k}.json"))
    if not d:
        return None
    acts = []
    for a in d.get("actions") or []:
        h = ORG.get((a.get("organization") or {}).get("classification") or "", "")
        line = tidy(re.sub(r"\s+", " ", a.get("description") or ""))
        line = re.sub(r"\s*\b[HS]\.J\. [\d/]+\.?$", "", line).rstrip()
        if line and not line.endswith("."):
            line += "."
        if line:
            acts.append(((a.get("date") or "")[:10], h, line))
    chap = None
    for doc in d.get("documents") or []:
        for l in doc.get("links") or []:
            cm = re.search(r"iactc/(\d+)\.(\d)/CH0*(\d+)\.pdf", l.get("url") or "")
            if cm:
                chap = (int(cm.group(3)), first_year(int(cm.group(1))) + int(cm.group(2)) - 1)
    sponsors = []
    for s in d.get("sponsorships") or []:
        n = re.sub(r"\s+", " ", s.get("name") or "").strip()
        if sponsors and re.fullmatch(r"(?:[A-Z]\.?|Jr\.?|Sr\.?|II|III|IV)", n):
            sponsors[-1] = (f"{sponsors[-1][0]}, {n}", sponsors[-1][1], sponsors[-1][2])
            continue
        person = s.get("person") or {}
        role = person.get("current_role") or {}
        sponsors.append((n, not s.get("primary"), (ORG.get(role.get("org_classification")), role.get("district"), person.get("name"))))
    return {"key": k, "title": tidy(d.get("title") or ""), "sponsors": sponsors, "actions": acts, "chapter": chap,
            "source": "openstates", "votes": d.get("votes") or [], "subject": d.get("subject") or []}


def section(session, k, prefer="page"):
    """A bill's history in one shape: its page section when there is one (with Open States' roll calls and sponsors kept
    alongside), else its Open States record."""
    ck = ("section", session, k, prefer)
    if ck not in _CACHE:
        pg = page_sections(session).get(k) if prefer == "page" else None
        o = from_openstates(session, k)
        if pg:
            pg = dict(pg)
            pg["votes"] = (o or {}).get("votes") or []
            pg["subject"] = (o or {}).get("subject") or []
            if not pg["sponsors"] and o:
                pg["sponsors"] = o["sponsors"]
            if not pg["chapter"] and o:
                pg["chapter"] = o["chapter"]
            if not pg["title"] and o:
                pg["title"] = o["title"]
        _CACHE[ck] = pg or o
    return _CACHE[ck]


RENUMBER = re.compile(r"renumbered as ((?:HF|SF|HJR|SJR|HSB|SSB|HCR|SCR|HR|SR) ?\d+)")


def chains(session, prefer="page"):
    """The General Assembly's renumbering chains, oldest number first: [[HSB47, HF163], [HF130, HF581, ...], ...]."""
    ck = ("chains", session, prefer)
    if ck in _CACHE:
        return _CACHE[ck]
    nxt, has_prev = {}, set()
    secs = {}
    for k in all_keys(session):
        s = section(session, k, prefer)
        if not s:
            continue
        secs[k] = s
        for _, _, t in s["actions"]:
            m = RENUMBER.search(t)
            if m:
                n = key_of(m.group(1))
                if n != k:
                    nxt[k] = n
                    has_prev.add(n)
    out = []
    for k in secs:
        if k in has_prev:
            continue
        chain, seen = [k], {k}
        while chain[-1] in nxt and nxt[chain[-1]] not in seen:
            chain.append(nxt[chain[-1]])
            seen.add(chain[-1])
        out.append(chain)
    _CACHE[ck] = (out, secs)
    return out, secs


# ---- Members ----

def members(session):
    """The General Assembly's members: [{house, district, name, last, inits, party, person, served, gas}] from fetch.py's
    members.json, else its saved House and Senate lists (members/<year>/house.html, senate.html), else Open States' people
    file (today's members)."""
    k = ("members", session)
    if k in _CACHE:
        return _CACHE[k]
    base = os.path.join(P.DATA, "members", str(session))
    rows = (load(os.path.join(base, "members.json"), {}) or {}).get("members") or []
    if not rows:
        for house in ("house", "senate"):
            try:
                page = open(os.path.join(base, f"{house}.html"), encoding="utf-8").read()
            except OSError:
                continue
            for row in re.findall(r"<tr>(.*?)</tr>", page, re.S):
                cells = re.findall(r"<td[^>]*>(.*?)</td>", row, re.S)
                pid = re.search(r"personID=(\d+)", row)
                if len(cells) < 5 or not pid:
                    continue
                name = text(cells[1])
                sk = re.search(r'sorttable_customkey="([^"]*)"', row)
                served = re.search(r"\((\d\d)/(\d\d)/(\d{4}) - (\d\d)/(\d\d)/(\d{4})\)$", name)
                rows.append({"person": int(pid.group(1)), "chamber": text(cells[0]),
                             "name": name[:served.start()].strip() if served else name,
                             "served": [f"{served.group(3)}-{served.group(1)}-{served.group(2)}",
                                        f"{served.group(6)}-{served.group(4)}-{served.group(5)}"] if served else None,
                             "district": int(text(cells[2])) if text(cells[2]).isdigit() else None,
                             "party": text(cells[3]), "county": text(cells[4]),
                             "email": text(cells[5]).lower() if len(cells) > 5 else "",
                             "surname": re.sub(r"\s+(?:Jr|Sr|II|III|IV)\.?$", "", H_.unescape(sk.group(1))).strip() if sk else ""})
    out = []
    for r in rows:
        if not r.get("district"):
            continue
        pages = os.path.join(base, "pages", f"{r['person']}.html")
        gas = None
        try:
            gas = {int(g) for g in re.findall(r"General Assembly: (\d+)", open(pages, encoding="utf-8").read())}
        except OSError:
            pass
        out.append(member_entry("H" if r.get("chamber") == "House" else "S", r["district"], r["name"], r.get("party"),
                                person=r["person"], served=r.get("served"), gas=gas, email=r.get("email") or "", raw=r,
                                family=r.get("surname") or None))
    if not out:
        try:
            for r in csv.DictReader(open(os.path.join(P.DATA, "openstates_people.csv"), encoding="utf-8")):
                h = ORG.get(r.get("current_chamber"))
                if h and (r.get("current_district") or "").isdigit():
                    out.append(member_entry(h, int(r["current_district"]), r["name"], r.get("current_party"),
                                            email=r.get("email") or "", family=r.get("family_name")))
        except OSError:
            pass
    _CACHE[k] = out
    return out


def member_entry(h, district, name, party, person=None, served=None, gas=None, email="", family=None, raw=None):
    n = re.sub(r"\s+", " ", name or "").strip()
    n = re.sub(r"^(?:Dr|Rev)\.\s+|,?\s+(?:M\.D\.|Ph\.D\.|D\.O\.|Esq\.)$", "", n)
    core = re.sub(r",?\s+(?:Jr\.?|Sr\.?|II|III|IV)$", "", n)
    words = core.split()
    last = family or (words[-1] if words else "")
    # Two-word surnames the bills write in full ("Trone Garriott", "Kniff McCulla", "Wessel-Kroeschell").
    if not family and len(words) >= 3 and words[-2] in ("Trone", "Kniff", "Van", "De", "Mc"):
        last = " ".join(words[-2:])
    return {"house": h, "district": int(district), "name": n, "last": fold(last), "first": fold(words[0])[:1] if words else "",
            "inits": {fold(w)[:1] for w in words[:-1] if fold(w)}, "party": party_letter(party), "person": person,
            "served": served, "gas": gas, "email": email, "raw": raw or {}}


def party_letter(p):
    p = p or ""
    return "D" if p.startswith("Democrat") else "R" if p.startswith("Republican") else "I" if p else ""


def current_session():
    return P.session_of(datetime.now(ZoneInfo(P.TIMEZONE)).year)


def roster(session):
    """The members to tie a General Assembly's names to: its own list when there is one, else (2023-24) the newest list's
    members, keeping only those whose page shows they served in that General Assembly when the page has been read."""
    k = ("roster", session)
    if k in _CACHE:
        return _CACHE[k]
    own = os.path.isdir(os.path.join(P.DATA, "members", str(session)))
    if own:
        out = members(session)
    else:
        newest = max([int(os.path.basename(f)) for f in glob.glob(os.path.join(P.DATA, "members", "[0-9]" * 4))] or [current_session()])
        ga = P.ga_of(session)
        out = [m for m in members(newest) if m["gas"] is None or ga in m["gas"]]
    _CACHE[k] = out
    return out


def holders(session, h, name, day=""):
    """A name as the histories and roll calls write it ("R. Johnson", "Meyer, B", "Thomson, C.", "Amos Jr.", "STONE",
    "Trone Garriott") -> the members of that house it can be."""
    n = re.sub(r"\s+", " ", name or "").strip().rstrip(".")
    init = ""
    m = re.match(r"^([A-Z])\.\s+(.+)$", n)
    if m:
        init, n = m.group(1), m.group(2)
    last, _, rest = n.partition(",")
    rest = rest.strip().rstrip(".")
    if re.fullmatch(r"[A-Za-z]", rest):
        init = rest
    last = re.sub(r"\s+(?:Jr|Sr|II|III|IV)\.?$", "", last.strip())
    f = fold(last)
    hits = [x for x in roster(session) if x["house"] == h and (x["last"] == f or fold(x["name"].split()[-1]) == f
                                                               or fold(" ".join(x["name"].split()[-2:])) == f)]
    if init:
        hits = [x for x in hits if x["first"] == fold(init) or fold(init) in x["inits"]]
    if len(hits) > 1 and day:
        on = [x for x in hits if not x["served"] or x["served"][0] <= day <= x["served"][1]]
        hits = on or hits
    return hits


def seat_of(session, h, name, day="", person=None):
    """-> "H:62", else "H?Name"."""
    if person and person[0] == h and str(person[1] or "").isdigit() and session == current_session():
        return f"{h}:{int(person[1])}"
    hits = holders(session, h, name, day)
    if len(hits) == 1:
        return f"{h}:{hits[0]['district']}"
    return f"{h}?{display(name)}"


def display(name):
    n = re.sub(r"\s+", " ", name or "").strip()
    if n.isupper():
        n = " ".join(w.capitalize() if not re.fullmatch(r"(?:II|III|IV)", w) else w for w in n.split())
        n = re.sub(r"\bMc(\w)", lambda m: "Mc" + m.group(1).upper(), n)
    return n


def member_at(session, seat):
    h, d = seat.split(":")
    hit = [m for m in roster(session) if m["house"] == h and m["district"] == int(d)]
    hit.sort(key=lambda m: bool(m["served"]))  # a sitting member before one who left
    return hit[0] if hit else None


# ---- Wording ----

def comm_name(c):
    """"COMMITTEE ON HEALTH AND HUMAN SERVICES" -> "Health and Human Services"."""
    c = re.sub(r"\s+", " ", c or "").strip(" .")
    c = re.sub(r"^(?:COMMITTEE ON |House |Senate )", "", c, flags=re.I)
    c = re.sub(r"\s+COMMITTEE$", "", c, flags=re.I)
    if c.isupper():
        c = " ".join(w.lower() if w in ("AND", "OF", "THE", "ON") else w.capitalize() for w in c.split())
    return c


def is_budget(title):
    return bool(re.search(r"\bappropriat\w+\b|\bstandings\b|\brebuild iowa infrastructure fund\b", title or "", re.I))


def clean_title(t):
    """The official title without "A bill for an act", the cross-references and the effective-date notes:
    "Relating to school safety by requiring ..."."""
    t = re.sub(r"\s*\((?:Formerly|See)\b[^)]*\)\.?", "", t or "")
    t = re.sub(r"\s*Effective date:.*$", "", t)
    t = re.sub(r"\s*(?:Applicability date|Item veto|Various effective dates).*$", "", t)
    t = re.sub(r"^A (?:bill for an act|joint resolution)\s+", "", t.strip(), flags=re.I).rstrip(" .")
    return t[:1].upper() + t[1:] if t else t


def short_title(t):
    """Drop the stock tail "..., and including effective date and applicability provisions"."""
    s = re.sub(r",?\s+and (?:including|providing) (?:an )?(?:effective date|applicability|retroactive applicability|penalties|"
               r"transition)[\w ,]*provisions?$", "", t)
    s = re.sub(r",?\s+and making penalties applicable$", "", s)
    return s or t


TALLY = re.compile(r"yeas\s*(\d+),?\s*nays?\s*(\d+)", re.I)
CTALLY = re.compile(r"Yeas,?\s*(\d+)[.,]?\s*Nays[.,]?\s*(\d+)", re.I)


def tally(t, rx=TALLY):
    m = rx.search(t)
    return (int(m.group(1)), int(m.group(2))) if m else None


# ---- Votes ----

def os_votes(session, s):
    """Open States' passage roll calls of a bill: [{h, day, y, n, members: [[seat, code]]}]."""
    out = []
    for v in s.get("votes") or []:
        h = ORG.get((v.get("organization") or {}).get("classification"))
        day = (v.get("start_date") or "")[:10]
        if not h or not day or not re.search(r"Shall the (?:bill pass|joint resolution be adopted)", v.get("motion_text") or ""):
            continue
        counts = {c["option"]: c["value"] for c in v.get("counts") or []}
        names = []
        for x in v.get("votes") or []:
            n = (x.get("voter_name") or "").strip()
            if re.fullmatch(r"(?:Open|Vacant|Vacancy)", n) or re.search(r"[\d:]", n):
                continue
            if names and re.fullmatch(r"(?:[A-Z]\.?|Jr\.?|Sr\.?|II|III|IV)", n):
                names[-1] = (f"{names[-1][0]}, {n}", names[-1][1], names[-1][2])
                continue
            role = ((x.get("voter") or {}).get("current_role") or {})
            names.append((n, x.get("option"), (ORG.get(role.get("org_classification")), role.get("district"))))
        names = rejoin(session, h, names)
        listed = []
        code = {"yes": "Y", "no": "N", "absent": "A", "not voting": "A", "excused": "E", "abstain": "B"}
        for n, opt, person in names:
            c = code.get(opt, "A")
            if c != "Y":
                listed.append([seat_of(session, h, n, day, person), c])
        out.append({"h": h, "day": day, "y": counts.get("yes", 0), "n": counts.get("no", 0), "members": dedupe(listed, h)})
    return out


def rejoin(session, h, names):
    """Open States' 2023-24 roll calls split two-word surnames ("Trone", "Garriott"; "Kniff", "McCulla") and run "De Witt"
    onto the name before it ("Dawson De Witt"): put them back as the roster writes them."""
    lasts = {m["last"] for m in roster(session) if m["house"] == h} | {m["last"] for m in members(current_session()) if m["house"] == h}
    out = []
    for n, opt, person in names:
        if out and fold(out[-1][0] + n) in lasts and fold(out[-1][0]) not in lasts:
            out[-1] = (f"{out[-1][0]} {n}", out[-1][1], out[-1][2])
            continue
        m = re.match(r"^(.+?) (De Witt)$", n)
        if m and fold(m.group(1)) in lasts:
            out.append((m.group(1), opt, person))
            continue
        out.append((n, opt, person))
    return out


def dedupe(listed, h):
    c = Counter(s for s, _ in listed if "?" not in s)
    return [[s if c[s] <= 1 else f"{h}?{s}", code] for s, code in listed]


# ---- One record ----

def record(session, chain, secs, parties):
    lead = chain[-1]
    if not BILL.fullmatch(lead):
        return None, None
    lead_sec = secs[lead]
    const = "JR" in lead
    if const and not AMENDMENT.match(lead_sec["title"] or ""):
        return None, None
    origin = chain[0][0]
    other = OTHER[origin]
    steps = []  # (day, house or "G", wording, kind, bill)
    passed, amended_back = set(), False
    where, place, comm = origin, "desk", None
    refs, first_ref, reported = [], None, set()
    enrolled = sent = law = vetoed = items = to_sos = False
    replaced_by, withdrawn, failed = None, False, None
    fvotes = []
    pool, used = [], set()
    chapter = None
    for k in chain:
        pool += [(k, v) for v in os_votes(session, secs[k])]
        if secs[k].get("chapter"):
            chapter = secs[k]["chapter"]
    committee_sponsor = next((comm_name(n[0]) for k in chain for n in secs[k]["sponsors"] if re.search(r"COMMITTEE", n[0], re.I)), None)

    def take(h, d, y, n):
        for i, (k, v) in enumerate(pool):
            if i in used or v["h"] != h or v["day"] != d:
                continue
            if (v["y"], v["n"]) != (y, n) and abs(v["y"] - y) + abs(v["n"] - n) > 2:
                continue
            used.add(i)
            return v
        return None

    last_vote_step = {}
    for ci, k in enumerate(chain):
        s = secs[k]
        final = ci == len(chain) - 1
        acts = sorted(s["actions"], key=lambda a: a[0])
        for d, h, t in acts:
            hh = h or where
            add = lambda w, kind, hs=None: steps.append((d, hs or hh, w, kind, k))
            if re.match(r"\*[\s*]*END OF", t):
                continue
            if re.match(r"(?:Fiscal note|Explanations? of votes?|NOBA|Lobbyist|Department's Memorandum|Chief Clerk's report|"
                        r"Secretary's report|Correction approved|Corrected version)", t):
                continue
            m = re.match(r"Introduced, (referred to (.+?)|placed on (?:(.+?) )?calendar)\.$", t)
            if m:
                if ci == 0:
                    add(f"Introduced in the {HOUSE[hh]}", "intro")
                if m.group(2):
                    c = comm_name(m.group(2))
                    comm, place, where = c, "committee", hh
                    refs.append((hh, c))
                    if first_ref is None and hh == origin:
                        first_ref = c
                    add(f"REFERRED TO {c.upper()}", "ref")
                else:
                    if ci == 0 and committee_sponsor and first_ref is None:
                        # A committee's own bill (from a study bill not read here): the committee already approved it.
                        first_ref = committee_sponsor
                        refs.append((hh, committee_sponsor))
                        reported.add((hh, committee_sponsor))
                    place, comm, where = "floor", None, hh
                    cal = m.group(3)
                    add(f"On the {HOUSE[hh]} calendar" + (f" (the {cal} calendar)" if cal else ""), "calendar")
                continue
            m = re.match(r"(?:Read first time, )?(?:Pursuant to Rule [\d.]+, )?(?:referred|Referred|Rereferred) to (.+?)\.$", t)
            if m and not re.search(r"calendar", m.group(1)):
                c = comm_name(m.group(1).split(". Attached")[0])
                if hh != where and hh == other:
                    add(f"Received in the {HOUSE[hh]}", "received")
                comm, place, where = c, "committee", hh
                refs.append((hh, c))
                if first_ref is None and hh == origin:
                    first_ref = c
                add(f"REFERRED TO {c.upper()}", "ref")
                continue
            m = re.match(r"(?:Read first time, )?(passed on file|attached to (?:companion )?(.+?)|placed on (.+?) calendar)\.$", t)
            if m and t.startswith(("Read first time", "Attached", "attached", "Passed on file")) or re.match(r"(?:Attached to (?:companion )?(.+)|Passed on file)\.$", t):
                if hh != where:
                    add(f"Received in the {HOUSE[hh]}", "received")
                place, comm, where = "floor", None, hh
                at = re.search(r"attached to (?:companion )?(\w+ ?\d+)", t, re.I)
                add(f"On the {HOUSE[hh]} calendar with its companion, {spaced(key_of(at.group(1)))}" if at else f"On file in the {HOUSE[hh]}, on the calendar", "calendar")
                continue
            m = re.match(r"Subcommittee(?: reassigned)?: (.+?)\.?$", t)
            if m:
                add(f"Subcommittee: {m.group(1)}", "routine")
                continue
            m = re.match(r"Subcommittee Meeting: (.+)$", t)
            if m:
                add(f"Subcommittee meeting: {m.group(1).rstrip('.')}", "agenda")
                continue
            m = re.match(r"Subcommittee (recommends|returns) (.+?)\.?(?:\s*Vote Total: (\d+)-(\d+))?\.?(?:\s*\[\])?$", t)
            if m:
                what = m.group(2).rstrip(". []")
                add(f"The subcommittee {m.group(1)} {what}" + (f" ({m.group(3)}-{m.group(4)})" if m.group(3) else ""), "subreport")
                continue
            m = re.match(r"Committee report,? (?:approving bill, renumbered as|recommending passage, renumbered as) (.+?)\.$", t)
            if m or re.match(r"Committee report approving bill, renumbered as (.+?)\.$", t):
                m = m or re.match(r"Committee report approving bill, renumbered as (.+?)\.$", t)
                n = key_of(m.group(1))
                c = comm or committee_sponsor or ""
                reported.add((hh, c))
                add("REPORTED", "reported")
                add(f"The {c} Committee approved it as a new bill, {spaced(n)}" if c else f"Approved by the committee as a new bill, {spaced(n)}", "renumber")
                continue
            m = re.match(r"Committee report,? (recommending (?:amendment and )?passage|approving bill|recommending indefinite postponement)", t)
            if m:
                c = comm or committee_sponsor or ""
                if "indefinite" in m.group(1):
                    add(f"The {c} Committee recommended indefinite postponement (killing it)", "commfail")
                    continue
                reported.add((hh, c))
                what = "approved it with amendments" if "amendment" in m.group(1) else "approved it"
                add("REPORTED", "reported")
                add(f"The {c} Committee {what}" if c else f"The committee {what}", "report")
                last_vote_step["C"] = (hh, c, d)
                continue
            m = re.match(r"Com+it+ee [Vv]ote:", t)
            if m:
                ty = tally(t, CTALLY)
                if ty:
                    hc = last_vote_step.get("C") or (hh, comm or committee_sponsor or "", d)
                    fvotes.append([hc[0], "C", hc[1] or None, d, ty[0], ty[1], []])
                    add(f"Committee vote: {ty[0]}-{ty[1]}", "routine")
                continue
            if re.match(r"Placed on (?:(.+?) )?calendar", t):
                if hh == where or place != "committee":
                    place, comm, where = "floor", None, hh
                if "unfinished business" in t:
                    add(f"On the {HOUSE[hh]} calendar under unfinished business", "calendar")
                else:
                    cal = re.match(r"Placed on (.+?) calendar", t)
                    add(f"On the {HOUSE[hh]} calendar" + (f" (the {cal.group(1)} calendar)" if cal and cal.group(1) != "" else ""), "calendar")
                continue
            m = re.match(r"(Passed|Failed to pass) (House|Senate),\s*(?:yeas\s*(\d+),?\s*nays?\s*(\d+))?", t)
            if m:
                hv = "H" if m.group(2) == "House" else "S"
                y, n = (int(m.group(3)), int(m.group(4))) if m.group(3) else (0, 0)
                v = take(hv, d, y, n)
                fvotes.append([hv, "F", None, d, (v or {}).get("y", y) if v else y, (v or {}).get("n", n) if v else n,
                               v["members"] if v else []])
                if m.group(1).startswith("Failed"):
                    failed = (d, hv)
                    add(f"The {HOUSE[hv]} voted it down, {y}-{n}", "fail", hv)
                    continue
                failed = None
                where = hv
                if hv not in passed and not (hv == origin and other in passed):
                    passed.add(hv)
                    add(f"PASSED {HOUSE[hv].upper()}", "pass", hv)
                    add(f"The {HOUSE[hv]} vote: {y}-{n}", "tally", hv)
                else:
                    passed.add(hv)
                    add(f"The {HOUSE[hv]} passed it again, {y}-{n}" + (" (with the other house's changes)" if amended_back else ""), "final", hv)
                    amended_back = False
                place, comm = "desk", None
                continue
            if re.match(r"Motion to reconsider vote prevailed", t):
                prev = [x for x in steps if x[1] == hh and x[3] in ("pass", "final", "fail")]
                if prev and prev[-1][3] != "fail":
                    passed.discard(hh)
                add(f"The {HOUSE[hh]} voted to reconsider its vote", "reconsider")
                continue
            if t == "Immediate message.":
                continue
            m = re.match(r"Message from (House|Senate)(, with amendment (.+?))?\.$", t)
            if m:
                if m.group(2):
                    amended_back = True
                    add(f"Back in the {HOUSE[hh]} with the {m.group(1)}'s changes ({m.group(3)})", "back")
                    where, place, comm = hh, "desk", None
                elif hh != where or place == "desk":
                    if hh == origin and other in passed:
                        add(f"Back in the {HOUSE[hh]}", "back")
                    else:
                        add(f"Received in the {HOUSE[hh]}", "received")
                    where, place, comm = hh, "desk", None
                continue
            m = re.match(r"(House|Senate) amendment ([HS]-\d+) filed", t)
            if m and hh == OTHER["H" if m.group(1) == "House" else "S"]:
                amended_back = True
                add(f"The {m.group(1)}'s amendment {m.group(2)} came back for the {HOUSE[hh]} to agree to", "other")
                continue
            m = re.match(r"(Substituted for|Attached to) (?:companion )?(.+?)\.$", t)
            if m and m.group(1).startswith("Substituted"):
                r_ = key_of(m.group(2))
                place, comm, where = "floor", None, hh
                add(f"Took the place of its companion, {spaced(r_)}", "subfor")
                continue
            m = re.match(r"((?:HF|SF|HJR|SJR) ?\d+) substituted\.$", t)
            if m:
                replaced_by = key_of(m.group(1))
                add(f"Replaced by its companion, {spaced(replaced_by)}", "replaced")
                continue
            if t == "Withdrawn.":
                if final and not replaced_by:
                    withdrawn = True
                    add(f"Withdrawn in the {HOUSE[hh]}", "withdrawn")
                continue
            if re.match(r"(?:House|Senate) concurred (?:in|with)", t):
                further = "as amended" in t
                add(f"The {HOUSE[hh]} agreed to the {HOUSE[OTHER[hh]]}'s changes" + (", with further changes" if further else ""), "concur")
                continue
            if re.match(r"(?:House|Senate) (?:refused to concur|insisted|receded)", t):
                add(t.rstrip("."), "noconcur" if "refused" in t or "insisted" in t else "recede")
                continue
            if re.match(r"Conference committee report (?:filed, )?adopted", t):
                add(f"The {HOUSE[hh]} adopted the conference committee's report", "ccr")
                continue
            if re.match(r"Reported correctly enrolled", t):
                enrolled = True
                add("Passed both houses (enrolled)", "enrolled")
                if "sent to Governor" in t:
                    sent = sent or not const
                    add("DELIVERED TO GOVERNOR", "sent", "G")
                continue
            if re.match(r"Item vetoed, signed by Governor", t):
                law = law or not const
                items = True
                add("SIGNED BY THE GOVERNOR, with items vetoed (a line-item veto)", "signed", "G")
                continue
            if re.match(r"Signed by Governor", t):
                law = law or not const
                add("SIGNED BY THE GOVERNOR", "signed", "G")
                continue
            if re.match(r"Vetoed by Governor", t):
                vetoed = True
                add("VETOED", "vetoed", "G")
                continue
            if re.match(r"Sent to Secretary of State", t):
                to_sos = True
                add("Filed with the Secretary of State" + (", for the next General Assembly to pass again or the voters" if const else ""), "sos", "G")
                continue
            if re.match(r"(?:Amendments? |Committee amendment |Point of order|Motion to suspend|Motion|Unanimous consent|Sponsors? (?:added|withdrawn)|Request to divide|Deferred|Tabled)", t):
                add(t.rstrip("."), "routine" if re.match(r"(?:(?:Committee )?Amendments? [HS]-[\d, and[HS]-]+ filed\.?$|Sponsors? (?:added|withdrawn)|Point of order|Motion to suspend|Unanimous consent|Request to divide)", t) else "other")
                continue
            m = re.match(r"(?:House|Senate) conference committee appointed", t)
            if m:
                add(t.rstrip("."), "other")
                continue
            add(t.rstrip("."), "other")
        if not final:
            where = where  # the next number picks up in the same house

    # Passed both houses: enrolled or sent; or both houses passed and nothing sent it back after the last passage.
    passes = [i for i, x in enumerate(steps) if x[3] in ("pass", "final")]
    agreed = False
    if passed >= {"S", "H"} and passes:
        later = steps[passes[-1] + 1:]
        agreed = not any(x[3] == "back" and "changes" in x[2] or (x[3] == "other" and "came back for" in x[2]) for x in later)
    both = enrolled or sent or law or vetoed or (const and to_sos) or agreed
    if law and vetoed:
        law = False
    if const:
        stage = 3 if both else 2 if passed else None
        law = vetoed = sent = False
    elif law:
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
    if stage is None:
        stage = 1 if place == "floor" else 0

    official = clean_title(lead_sec["title"])
    title = short_title(official)
    if const:
        title = "Constitutional amendment: " + re.sub(r"^Proposing (?:an amendment|amendments) to the Constitution of the State of Iowa\s*", "", title, flags=re.I).strip(" ,")
        title = title.rstrip(": ")
    # No summary line: the official title differs from the title only by the stock tail (", and including effective date
    # provisions"), which the page showed as if it were a summary (2026-11-22). "What it does" is the LSA's explanation.
    summary = ""
    topics = ["const"] if const else []
    for h_, c in refs:
        tp = P.COMMITTEE_TOPICS.get(c)
        if tp and tp not in topics:
            topics.append(tp)
    subjects = " ".join(lead_sec.get("subject") or [])
    if len(topics) <= (1 if const else 0):
        topics += [k for k, rx in P.TOPIC_WORDS.items() if rx.search(f"{official} {subjects}") and k not in topics]
    topics = list(dict.fromkeys(topics))

    # Sponsors: each number's own (the member who filed it, or the committee that introduced it).
    first_day = min((x[0] for x in steps if x[0]), default=f"{session}-01-01")

    def sponsors_of(k):
        people_, seen = [], set()
        for row in secs[k]["sponsors"]:
            name, co = row[0], row[1]
            person = row[2] if len(row) > 2 else None
            if re.search(r"COMMITTEE", name, re.I):
                continue
            sid = seat_of(session, origin, name, first_day, person and (person[0], person[1]))
            mem = member_at(session, sid) if "?" not in sid else None
            nm = mem["name"] if mem else display(name)
            if nm in seen:
                continue
            seen.add(nm)
            people_.append((nm, sid, not co))
            if mem and mem["party"] in ("D", "R"):
                parties[(origin, nm)] = mem["party"]
        if people_:
            return (people_[0][0], int(people_[0][1].split(":")[1]) if "?" not in people_[0][1] else 0,
                    [x[0] for x in people_[1:]], max(1, sum(1 for x in people_ if x[2])))
        cm = next((comm_name(n[0]) for n in secs[k]["sponsors"] if re.search(r"COMMITTEE", n[0], re.I)), None)
        if not cm and k[1:3] == "SB":  # a study bill is its committee's draft
            cm = next((comm_name(m.group(1)) for _, _, t in secs[k]["actions"] for m in [re.match(r"Introduced, referred to (.+?)\.$", t)] if m), None)
        return (f"{HOUSE[k[0]]} {cm} Committee" if cm else ""), 0, [], 1

    by_num = {k: sponsors_of(k) for k in chain}
    sponsor, district, cos, _ = by_num[lead]
    first_member = next((by_num[k] for k in chain if by_num[k][1] or (by_num[k][0] and not by_num[k][0].endswith("Committee"))), None)
    if not sponsor:
        sponsor = (first_member or by_num[chain[0]])[0] or "—"
    people_ = [(sponsor, "", True)]

    if stage == 0:
        dsc = f"In {HOUSE[where]} committee" if place == "committee" else "Introduced"
    elif stage == 1:
        dsc = f"On the {HOUSE[where]} floor"
    else:
        dsc = {2: f"Passed the {HOUSE[origin] if origin in passed else HOUSE[other]}", 3: "Passed both houses",
               4: "On the governor's desk", 5: "Became law", 6: "Vetoed"}[stage]
        if const and stage == 3:
            dsc = "Passed both houses"
    if replaced_by and stage <= 2:
        dsc = f"Replaced by {spaced(replaced_by)}"
    elif withdrawn and stage <= 2:
        dsc = "Withdrawn"
    comm_now = comm if place == "committee" and stage in (0, 2) and not replaced_by and not withdrawn else None

    def dates(test, mode="last"):
        ds = sorted({x[0] for x in steps if test(x) and x[0]})
        return {"first": ds[0], "last": ds[-1], "all": ";".join(ds)}[mode] if ds else ""

    action_dates = [x[0] for x in steps if x[0]]
    # The last action's day is the latest shown in the history: paperwork kept out of it ("routine") would leave the
    # status rows (/your-bills/, /list/, the front page) a day with no wording.
    shown_dates = [x[0] for x in steps if x[0] and x[3] != "routine"] or action_dates
    left_first = bool(first_ref and ((origin, first_ref) in reported or origin in passed))
    chap = f"{chapter[0]} of {chapter[1]}" if chapter and stage == 5 else None
    signed_on = dates(lambda x: x[3] == "signed")
    extra = bool(signed_on and signed_on > P.plus_days(P.SESSION_ENDS.get(int(signed_on[:4]), f"{signed_on[:4]}-06-01"), 45))
    if extra:
        # An extraordinary (special) session's law: its chapters are numbered on their own (2023's HF 732 is chapter 1 of
        # the 2023 First Extraordinary Session; Open States links it to the regular session's chapter 1).
        chap = f"{chapter[0]} of {chapter[1]}, Extraordinary Session" if chap else None
    if stage == 5 and chap:
        steps.append((signed_on or steps[-1][0], "G", f"Chapter {chapter[0]}, {chapter[1]} Iowa Acts" + (", Extraordinary Session" if extra else ""), "chapter", lead))
    order = list(reversed(chain))
    vers = []
    for k in order:
        own = [[x[0], x[2]] for x in sorted(steps, key=lambda x: x[0]) if x[4] == k and x[3] != "routine"]
        sp_k, d_k, cos_k, pr_k = by_num[k]
        if k == lead:
            sp_k = sp_k or sponsor
        vers.append({"p": k, "sponsor": sp_k, "district": d_k, "cosponsors": cos_k,
                     "primes": pr_k, "cosp": len(cos_k),
                     "statusDesc": dsc if k == lead else f"Renumbered as {spaced(chain[chain.index(k) + 1])}",
                     "committee": comm_now if k == lead else None, "actions": own})
    rec = {
        "nums": order, "base": order, "prev": set(),
        "title": title, "summary": summary, "act": "", "lawCode": "", "law": None, "laws": [],
        "comms": sorted({f"{h_} · {c}" for h_, c in refs if c}), "topics": topics, "places": [],
        "narrow": P.narrow_kind(title), "commFate": "passed" if left_first else "none",
        "mainTopic": topics[0] if topics else "", "local": "local" in topics, "senDeleg": False, "asmDeleg": False,
        "budget": is_budget(official) and not const,
        "passedS": "S" in passed, "passedA": "H" in passed, "program": None,
        "stage": stage, "passedIn": (HOUSE[max((x for x in steps if x[3] in ("pass", "final")), key=lambda x: x[0])[1]]
                                     if passes else HOUSE[origin]) if stage == 2 else None,
        "chapter": chap,
        "veto": None, "memo": "", "vetoMemo": None, "itemVeto": items,
        "simText": official,
        "comm": comm_now if stage == 0 else None,
        "first": min(action_dates, default=f"{session}-01-01"),
        "last": max(shown_dates, default=f"{session}-01-01"),
        "cosp": len(cos),
        "keyDates": [
            dates(lambda x: x[3] in ("reported", "renumber") and x[1] == origin, "first"),
            dates(lambda x: x[1] == "S" and x[3] in ("pass", "final"), "all"),
            dates(lambda x: x[1] == "H" and x[3] in ("pass", "final"), "all"),
            "",
            dates(lambda x: x[3] == "sent") if stage >= 4 else "",
            dates(lambda x: x[3] == "signed") if stage == 5 else "",
            dates(lambda x: x[3] == "vetoed"),
        ],
        "votes": sorted(fvotes, key=lambda v: v[3]), "firstComms": [(origin, first_ref, left_first)] if first_ref else [],
        "vers": vers,
        "source": lead_sec["source"],
        "_official": official, "_sponsor": (first_member or by_num[lead])[0], "_lead": lead,
    }
    if stage == 5 and not rec["keyDates"][5]:
        rec["keyDates"][5] = rec["last"]
    # The governor's letter (states/ia/vetoes.py): a veto's on the vetoed bill (or a law passed over it), an item
    # veto's on the signed law.
    m = V.message(session, list(reversed(chain))) if stage in (5, 6) else None
    day = rec["keyDates"][6] or rec["keyDates"][5]
    if m and day and (m["kind"] == "absolute" or stage == 5):
        rec["vetoMemo"] = {"year": int(day[:4]), "signer": P.governor_on(day), "text": m["text"]}
        if m["kind"] == "line-item":
            rec["vetoMemo"]["kind"] = "line-item"
        if m["ocr"]:
            rec["vetoMemo"].update(ocr=True, url=m["url"])
    return rec, what_it_does(session, chain)


# ---- What it does ----

def what_it_does(session, chain):
    """The LSA's explanation from the introduced text of the chain's newest number that has one."""
    for k in reversed(chain):
        t = load(os.path.join(folder(session), "texts", f"{k}.json"))
        ex = (t or {}).get("explanation") or ""
        ex = re.sub(r"[ \t]+", " ", ex).strip()
        if len(ex) > 60:
            ps = [re.sub(r"\s+", " ", p).strip() for p in re.split(r"\n\s*\n", ex) if p.strip()]
            ps = [p for p in ps if not re.fullmatch(r"EXPLANATION|The inclusion of this explanation does not constitute agreement with the explanation's substance by the members of the general assembly\.", p, re.I)]
            out = "\n".join(ps)
            if len(out) > 3500:
                cut = out[:3500]
                out = cut[:cut.rfind(". ") + 1] if ". " in cut else cut
            if out:
                return {"statement": out, "label": f"From the Legislative Services Agency's explanation of {spaced(k)} as introduced."}
    return None


# ---- A General Assembly ----

def load_session(session, prefer="page"):
    """Read one General Assembly's bills: (records, bill number -> record index, fetched time, delegation)."""
    k = (session, "loaded", prefer)
    if k in _CACHE:
        return _CACHE[k]
    parties = _PARTIES.setdefault(session, {})
    recs, index, whats = [], {}, {}
    chs, secs = chains(session, prefer)
    for chain in chs:
        rec, what = record(session, chain, secs, parties)
        if not rec:
            continue
        for n in rec["nums"]:
            index[n] = len(recs)
        recs.append(rec)
        if what:
            whats[rec["nums"][0]] = what
    if prefer == "page":
        for r in recs:
            r["prev"] = earlier(session, r)
        # A constitutional amendment's second passage (the General Assembly before passed the same resolution) sends it to
        # the voters; P.SECOND_PASSAGES lists those whose first passage is before the earliest General Assembly read here.
        for r in recs:
            if "const" not in r["topics"] or r["stage"] != 3:
                continue
            before = any(y == session - 2 and y in sessions() and (lambda o: o[0][o[1][k]]["stage"] >= 3)(load_session(y)[:2])
                         for y, k in r["prev"])
            if before or set(r["nums"]) & P.SECOND_PASSAGES.get(session, set()):
                day = r["last"]
                r["vers"][0]["actions"].append([day, "Second passage: the General Assembly before this one passed it too, so it goes to the voters at the next general election"])
        try:
            with open(os.path.join(P.DATA, f"texts_{session}.json"), "w") as f:
                json.dump(whats, f, ensure_ascii=False)
        except OSError:
            pass
    for r in recs:
        for x in ("_official", "_sponsor", "_lead"):
            r.pop(x, None) if prefer == "page" else None
    paths = [os.path.join(folder(session), n) for n in ("state.json", "list.json", "openstates.json")]
    times = [os.path.getmtime(x) for x in paths if os.path.exists(x)]
    fetched = datetime.fromtimestamp(max(times), ZoneInfo(P.TIMEZONE)).strftime("%Y-%m-%d %H:%M") if times else ""
    settle(recs, folder(session))  # bills with no history yet: never dated in the future (states/undated.py)
    _CACHE[k] = (recs, index, fetched, {"SENATE": [], "ASSEMBLY": []})
    return _CACHE[k]


# ---- Earlier General Assemblies ----

def _norm(s):
    return re.sub(r"[^a-z0-9 ]", "", re.sub(r"\s+", " ", (s or "").lower())).strip()


def _keys(session):
    """A General Assembly's records that didn't become law: official title -> [leads], (title, first sponsor) -> [leads]."""
    if (session, "earlier") not in _CACHE:
        by_title, by_both = defaultdict(list), defaultdict(list)
        recs = load_session(session, "page")[0] if (session, "loaded", "page") in _CACHE else None
        if recs is None:
            # Build without linking (avoids recursion): convert the chains directly.
            chs, secs = chains(session)
            recs = []
            for chain in chs:
                r, _ = record(session, chain, secs, {})
                if r:
                    recs.append(r)
        for r in recs:
            if r["stage"] == 5 or r.get("budget"):
                continue
            t = _norm(r.get("_official") or r["simText"])
            if len(t.split()) < 6:
                continue
            by_title[t].append(r["nums"][0])
            sp = first_sponsor(r)
            by_both[(t, fold(sp.split()[-1] if sp else ""))].append(r["nums"][0])
        _CACHE[(session, "earlier")] = (by_title, by_both)
    return _CACHE[(session, "earlier")]


def first_sponsor(r):
    """The member who filed the chain's first number, else the newest number's sponsor (a committee)."""
    return next((v["sponsor"] for v in reversed(r["vers"]) if v["sponsor"] and not v["sponsor"].endswith("Committee")),
                r["vers"][0]["sponsor"] or "")


def earlier(session, rec):
    """The same bill in the General Assembly before: the same official title and first sponsor, or the same official title
    held by one bill in each. Never a law (a constitutional amendment's first passage is kept: it has to pass again) or a
    budget bill."""
    out = set()
    old = session - 2
    if old not in sessions() or rec.get("budget"):
        return out
    by_title, by_both = _keys(old)
    t = _norm(rec["_official"])
    if len(t.split()) < 6:
        return out
    sp = first_sponsor(rec)
    both = by_both.get((t, fold(sp.split()[-1] if sp else "")), [])
    if len(both) == 1 and not sp.endswith("Committee"):
        return {(old, both[0])}
    if len(t.split()) >= 8 and len(by_title.get(t, [])) == 1:
        out.add((old, by_title[t][0]))
    return out


def parties(session, recs):
    if session not in _PARTIES:
        load_session(session)
    return {k: v for k, v in _PARTIES.get(session, {}).items() if v in ("D", "R")}


def agendas(session):
    """Bills with an upcoming subcommittee meeting ("Subcommittee Meeting: 02/19/2025 8:30AM Room 217"): bill -> [["Senate
    Education subcommittee", "2025-02-19T08:30:00"], ...]."""
    today = date.today().isoformat()
    out = {}
    recs, index = load_session(session)[:2]
    for r in recs:
        for v in r["vers"]:
            for d, t in v["actions"]:
                m = re.match(r"Subcommittee meeting: (\d\d)/(\d\d)/(\d{4})\s+(\d{1,2}:\d\d\s*[AP]M)?", t)
                if not m:
                    continue
                day = f"{m.group(3)}-{m.group(1)}-{m.group(2)}"
                if day < today:
                    continue
                try:
                    when = datetime.strptime(f"{day} {m.group(4).replace(' ', '')}", "%Y-%m-%d %I:%M%p").strftime("%Y-%m-%dT%H:%M:%S")
                except (ValueError, AttributeError):
                    when = f"{day}T00:00:00"
                h = r["nums"][0][0]
                entry = [f"{HOUSE.get(h, 'House')} {r['comm'] or ''} subcommittee".replace("  ", " "), when]
                if entry not in out.setdefault(r["nums"][0], []):
                    out[r["nums"][0]].append(entry)
    return out


# ---- Checks ----

def checks(session):
    """Laws, vetoes and item vetoes by the year of the governor's action; the enrolled lists, where read, compared bill for
    bill; chapter numbers missing."""
    recs = load_session(session)[0]
    by_year = defaultdict(lambda: {"laws": 0, "vetoes": 0, "item vetoes": 0, "with chapter": 0})
    for r in recs:
        if r["stage"] == 5:
            y = r["keyDates"][5][:4]
            by_year[y]["laws"] += 1
            by_year[y]["with chapter"] += bool(r["chapter"])
            by_year[y]["item vetoes"] += bool(r.get("itemVeto"))
        if r["stage"] == 6:
            by_year[r["keyDates"][6][:4]]["vetoes"] += 1
    numbers = defaultdict(list)
    for r in recs:
        if r.get("chapter"):
            n, y = r["chapter"].split(" of ")
            numbers[y].append(int(n))
    gaps = {y: sorted(set(range(min(n), max(n) + 1)) - set(n)) for y, n in numbers.items()}
    dup = {y: sorted(x for x, c in Counter(n).items() if c > 1) for y, n in numbers.items()}
    enrolled = {}
    for y in (session, session + 1):
        e = load(os.path.join(folder(session), f"enrolled_{y}.json"))
        if e:
            listed = {key_of(x.get("bill")) for x in (e.get("bills") if isinstance(e, dict) else e) or []}
            mine = {r["nums"][0] for r in recs if r["stage"] >= 4 and r["keyDates"][4][:4] == str(y)}
            enrolled[y] = {"listed": len(listed), "here": len(mine), "listed not here": sorted(listed - mine)[:20],
                           "here not listed": sorted(mine - listed)[:20]}
    return {"by year": dict(by_year), "vetoes": sorted(r["nums"][0] for r in recs if r["stage"] == 6),
            "item vetoes": sorted(r["nums"][0] for r in recs if r.get("itemVeto")),
            "amendments passed": sorted((r["nums"][0], r["stage"]) for r in recs if "const" in r["topics"] and r["stage"] >= 2),
            "chapters missing": gaps, "chapters twice": dup, "enrolled lists": enrolled,
            "stuck at 3-4": sorted(r["nums"][0] for r in recs if r["stage"] in (3, 4) and "const" not in r["topics"]),
            "stages": dict(sorted(Counter(r["stage"] for r in recs).items())), "records": len(recs),
            "from pages": sum(r["source"] == "page" for r in recs), "from Open States": sum(r["source"] == "openstates" for r in recs)}


def compare(session):
    """Every chain whose lead bill has both a page section and an Open States record, converted both ways."""
    a, _, _, _ = load_session(session, "page")
    o, oi, _, _ = load_session(session, "openstates")
    diff, n = [], 0
    for r in a:
        if r["source"] != "page":
            continue
        lead = r["nums"][0]
        if lead not in oi:
            continue
        x = o[oi[lead]]
        n += 1
        ka = (r["stage"], r["passedS"], r["passedA"], r["comm"])
        kb = (x["stage"], x["passedS"], x["passedA"], x["comm"])
        if ka != kb:
            diff.append((lead, ka, kb))
    return n, diff


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "compare":
        n, diff = compare(int(sys.argv[2]))
        print(f"{n} bills compared; {len(diff)} differ")
        for d in diff:
            print(" ", d)
    else:
        for s in ([int(sys.argv[1])] if len(sys.argv) > 1 else sessions()):
            print(s, json.dumps(checks(s), indent=1))
