#!/usr/bin/env python3
"""Download Alabama's bills from ALISON, the Legislature's website (https://alison.legislature.state.al.us/). Its pages
are built in the browser from a GraphQL endpoint, https://alison.legislature.state.al.us/graphql (no key; undocumented,
introspection off: the queries here are the ones the site's own page scripts send, with fields they ask for). There is
no robots.txt (checked 2026-11-08: /robots.txt answers with the site's "not found" page, and
gql.api.alison.legislature.state.al.us and cms.alison.legislature.state.al.us have none either; alisondb's name no
longer resolves), so nothing is barred and there is no crawl delay. One request at a time, a second apart (counted from
the end of the last answer); a few queries ask for several roll calls or committees at once (GraphQL aliases), as one
request.

Alabama's Legislature meets once a year in a regular session from early February (in the year after an election, from
early March) for 30 legislative days within 105 calendar days, usually ending in May; bills don't carry over. Special
sessions ("2026SS1") and organizational sessions are left out. For each year from two years back through this one
(session "<year>RS"), into data/al/<year>/:
- bills.json: {"read", "bills": [...]}, every House and Senate bill (instrumentType "B": HB1, SB1; constitutional
  amendments are bills here, "By Representative Hill (Constitutional Amendment)", subject "Constitutional Amendments
  Statewide", or a county's subject for a local one), with sponsor (surname as the site shows it, "Brown (C)") and
  sponsorId, cosponsorIds (member ids, comma-separated), subject (one of about 60, or a county's name, "Jefferson
  County", for a local bill: about a fifth of the bills), short title, the committee it's in (assignedCommittee) and
  every committee it went to (allCommittees, "Judiciary (Senate); Judiciary (House)"), prefiled and first-read dates,
  currentStatus ("Enacted", "Indefinitely Postponed in House of Origin", "Pending Committee Action in Second House"),
  lastAction and its date, the Act number ("2025-312") with the Secretary of State's act page and the act summary
  (actSummary, for laws), effective dates, the companion bill's record id (companionOid) and the versions' PDF links
  (introduced, engrossed, enrolled, reenrolled). Read every run until the year is finished.
- history.json: {"read", "lines": [...]}: every bill's history, in the order recorded (by line id): date, house, the
  action as written ("Read for the first time and referred to the Senate Committee on Judiciary", "Motion to Read a
  Third Time and Pass as Amended - Adopted Roll Call 59", "Delivered to Governor", "Enacted"), the committee (on
  committee steps), the amendment or substitute it concerns (with its PDF), and for a roll call its number and totals.
  Committee votes are not roll calls here. The whole session's history comes in a few large pages (about 14,000 lines,
  resolutions included and left out here).
- birs.json: the Budget Isolation Resolutions (until the budgets pass, a bill needs a three-fifths vote on one before
  its own vote), with their roll calls.
- votes.json: {"H59": {"yeas", "nays", "abstains", "passes", "votes": [{"memberName": "Phillip Pettus", "vote": "Y"}]}}:
  every roll call in the bills' histories and BIRs, member by member (Y, N, A abstain, P pass). Names are the members'
  full names as the roll call prints them ("M. Moore", "Artis 'A.J.' McCampbell"). Read once each; one the server has
  no record of ("Matching vote summary not found") is asked again on GIVE_UP_AFTER runs, then left out.
- texts_raw.json.gz: {"asked": {bill: version}, "texts": {"HB2": {"INTRODUCED": text, "ENROLLED": text}}}: each bill's
  text as the endpoint gives it (fullText: always the newest version's, with page and line numbers), read once and
  again when the bill's PDF links show a newer version; every version read is kept. texts.json is made from it each
  run (finished years too, so a better parser needs no downloads): {"HB2": {"version", "byline", "rfd", "synopsis",
  "synopsis_version", "title", "local_notice", "length"}}: the byline ("By Representative Treadaway(N & P)": "N & P"
  marks a local bill with notice and proof of publication; "(Constitutional Amendment)"; a bill's co-sponsors are named
  only here in 2024, whose cosponsorIds are empty), the committee it was referred to ("RFD: Jefferson County
  Legislation"), the Legislative Services Agency's SYNOPSIS (the plain account of what the bill would do: "Under
  existing law ... This bill would ..."), and the act's title ("Relating to vaccines; to amend Section 22-8-4 ...").
  Only introduced texts have a synopsis, so a bill first read after it was engrossed or enrolled has none: in a
  finished year about half the bills (every law; their actSummary in bills.json covers about three in four), and local
  bills seldom have one. Each introduced version's PDF (introducedFileUrl, not read) has it.
- state.json: when each part was last read, roll calls the server had no record of, and "finished" once the year's
  bills, histories and BIRs have been read after the session (from August 1 of the year) and every roll call and text.
And into data/al/members/ (weekly): members.json, every member record (the current ones have house, district, the
counties it covers, name, "Representative Jim Carns (R)" with the party, leadership title, Montgomery office address,
phone and email, district office, biography); committees.json, every committee shown to the public (33 House and 21
Senate standing committees, 31 joint and interim ones) with contact staff and its members with their positions ("Chair" or
"Chairperson", "Vice Chair", "Ranking Minority Member", "Pro Tempore", "Member"). The active members include the
Lieutenant Governor (the Senate's presiding officer, no district) and the Secretary of the Senate. Past members'
records have no names: departed sponsors are known only by the bills' sponsor surname and roll calls' names.

Local bills, most of the volume in many years' Acts: the subject is a county, the byline has "(N & P)" or the history
has the house's local legislation committee ("Jefferson County Legislation"); local constitutional amendments are
voted on in that county only. The converter decides; nothing here filters them.

Outcomes: a law's history ends "Delivered to Governor", then "Enacted", with an Act number in bills.json; "Signed by
Governor" appears only a few times a year. Constitutional amendments get Act numbers too ("Enacted") but go to the
Secretary of State, not the governor ("Sent to Secretary of State": 18, 5 and 29 bills in 2024-26), then to the
voters. Vetoes: 2024 has one "Pocket Veto" (history and currentStatus); no other veto or override line appears in
2024-26, so a vetoed bill may show only as "Enrolled" or "Delivered to Governor" without "Enacted" (2024: two
"Enrolled"). Compare with the governor's own veto lists.

Roll-call totals: in 2026, 277 of 2,508 roll calls' "yeas" are one more than the members listed as voting yes (never
fewer); 2024 and 2025 match. Local bills' votes show most members abstaining (only the delegation votes).

A first copy of three years took about 45 minutes (2026-11-08): per year, 3 history pages, a bill list, a BIR list,
about 230 roll-call requests (2,100-2,500 roll calls; mostly a second each, though some stretches were slow) and about
50 text requests (the server takes about 8 seconds to answer each). After that a run reads each unfinished year's bill
list, history and BIRs (5 requests, about 5 MB) and any new roll calls and texts: under a minute; a finished year
(from August 1) is left alone. The members and committees (about 11 requests) are read weekly; three joint interim
committees' members fail on the server every time ("Unexpected error."), and are saved without members.

data/al/incomplete says "running" during the first copy, then lists what was never downloaded (a year's bill list or
history, the members); it is removed when nothing is missing. Roll calls and texts fill in on later runs and never mark
the state incomplete. A request that fails where a last copy exists keeps that copy and doesn't count.
Usage: python3 states/al/fetch.py [year]   (default: every year above; a single year leaves the marker alone)
"""
import gzip, json, os, re, sys, time, urllib.error, urllib.request
from collections import Counter
from datetime import date, timedelta

ENDPOINT = "https://alison.legislature.state.al.us/graphql"
DATA = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "al"))
AGENT = "statebilltracker.org (a nonprofit bill tracker; contact via github.com/judithhubbard)"
TODAY = date.today()
YEAR = TODAY.year
ONLY = int(sys.argv[1]) if len(sys.argv) > 1 else None
DELAY = 1.0  # seconds from the end of one answer to the next request
BILL = re.compile(r"^(HB|SB)\d+$")
HISTORY_PAGE = 5000  # history lines per request (about 1.2 MB)
TEXT_PAGE = 20  # bill texts per request (introduced texts average about 15 KB)
VOTE_PAGE = 10  # roll calls per request
GIVE_UP_AFTER = 3  # runs a roll call the server has no record of is asked for
MEMBER_DAYS = 7
MARKER = os.path.join(DATA, "incomplete")

# The run's own time limit (FETCH_MINUTES, set by the workflow): stop a few minutes early, with everything read so far
# saved and a summary printed, rather than be cut off silently mid-request.
START = time.time()
BUDGET = max(0.0, float(os.environ.get("FETCH_MINUTES") or 0) - 5) * 60
FAILS = Counter()  # why requests failed, for the summary
STATS = {"requests": 0, "votes": 0, "texts": 0}
LAST = [0.0]  # when the last answer ended

BILL_FIELDS = """id sessionAbbreviation sessionYear instrumentNbr instrumentType body sponsor sponsorId cosponsorIds
  subject shortTitle assignedCommittee allCommittees prefiledDate firstReadDate currentStatus lastAction lastActionDate
  actNbr viewEnacted actSummary effectiveDateCertain effectiveDateOther companionInstrumentNbr companionOid
  introducedFileUrl engrossedFileUrl enrolledFileUrl reenrolledFileUrl"""
HISTORY_FIELDS = """id instrumentNbr calendarDate body matter amdSub amdSubFileUrl committee voteType voteTitle
  rollCallNbr yeas nays"""
MEMBER_FIELDS = """id body active elected leader leadershipTitle fullName firstName lastName honorificFullNameAffiliation
  affiliation district counties phone email fullAddress districtOffice districtPhone districtEmail website imageUrl bio"""


class Refused(Exception):
    """The server turned us away (401/403/429, or an answer that isn't JSON): stop the run."""


def out_of_time():
    return BUDGET and time.time() - START > BUDGET


def gql(query, label, variables=None):
    """The endpoint's answer ({"data", "errors"}) to query, or None after three tries. A GraphQL error (a field the
    server doesn't know, a roll call it has no record of) comes back in "errors" and isn't retried."""
    for attempt in range(3):
        if out_of_time():
            return None
        wait = LAST[0] + DELAY - time.time()
        if wait > 0:
            time.sleep(wait)
        STATS["requests"] += 1
        if STATS["requests"] % 100 == 0:
            print(f"  {STATS['requests']} requests, {round((time.time() - START) / 60)} min"
                  + (f"; failures {dict(FAILS)}" if FAILS else ""), flush=True)
        headers = {"User-Agent": AGENT, "Accept": "application/json", "Accept-Encoding": "gzip",
                   "Content-Type": "application/json"}
        body = json.dumps({"query": query, "variables": variables or {}}).encode()
        try:
            try:
                with urllib.request.urlopen(urllib.request.Request(ENDPOINT, data=body, headers=headers),
                                            timeout=180) as r:
                    raw, kind, enc = r.read(), r.headers.get("Content-Type") or "", r.headers.get("Content-Encoding")
            except urllib.error.HTTPError as e:
                if e.code != 400:  # GraphQL servers answer a bad query with 400 and the errors as JSON
                    raise
                raw, kind, enc = e.read(), e.headers.get("Content-Type") or "", e.headers.get("Content-Encoding")
            LAST[0] = time.time()
            if enc == "gzip":
                raw = gzip.decompress(raw)
            if "json" not in kind:
                raise Refused(f"{label}: answered {kind or 'no type'}, not JSON (a challenge page?)")
            answer = json.loads(raw)
            if answer.get("errors") and not answer.get("data") and not any(
                    "path" in e for e in answer["errors"]):
                FAILS["query error"] += 1
                print(f"{label}: {answer['errors'][0].get('message', '')[:200]}", flush=True)
                return None
            return answer
        except Refused:
            raise
        except urllib.error.HTTPError as e:
            LAST[0] = time.time()
            FAILS[f"HTTP {e.code}"] += 1
            if e.code in (401, 403, 429):
                raise Refused(f"{label}: HTTP {e.code}")
        except Exception as e:
            LAST[0] = time.time()
            FAILS[type(e).__name__] += 1
        time.sleep(20 * (attempt + 1))
    print(f"{label}: failed three times", flush=True)
    return None


def q(s):
    """A string as a GraphQL literal."""
    return json.dumps(s)


def save(obj, path):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=0)
    os.replace(tmp, path)


def load(path, default=None):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def finished_by(year):
    """From this day a year's bills no longer change: its session ended months before (August 1 of the year)."""
    return f"{year}-08-01"


# Bill texts --------------------------------------------------------------------------------------------------------

VERSIONS = ("PREFILED", "INTRODUCED", "ENGROSSED", "ENROLLED", "REENROLLED")  # oldest first


def unnumber(t):
    """A text without its page numbers and line numbers. Line numbers are words of their own counting up through the
    bill (1, 2, 3 ... across pages; the cover page has its own), set between the lines or, in older texts, in blocks:
    each number is chained to the latest number one less before it, and chains of four or more are dropped, so a
    number in the text ("under 18 years") stays. The older texts also repeat a page's last line after "Page 1"
    ("... an equitable<tab>Page 1involving the sale or assignment of an equitable<tab>"): the copy goes."""
    out, at = [], 0
    for m in re.finditer(r"\bPage \d+", t):
        before = re.split(r"[\t\n]", t[max(0, m.start() - 300):m.start()].rstrip(" "))[-1].strip()
        rest = t[m.end():].lstrip(" ")
        out.append(t[at:m.start()] + " ")
        at = m.end()
        if len(before) >= 8 and rest.startswith(before):
            at = m.end() + (len(t[m.end():]) - len(rest)) + len(before)
    t = "".join(out) + t[at:]
    words = re.split(r"(\s+)", t)
    last, length, parent = {}, {}, {}
    for i, w in enumerate(words):
        if w.isdigit() and len(w) <= 4:
            v = int(w)
            p = last.get(v - 1)
            length[i], parent[i] = (length[p] + 1, p) if p is not None else (1, None)
            last[v] = i
    drop = set()
    for i in sorted(length, reverse=True):
        if length[i] >= 4 and i not in drop:
            while i is not None and i not in drop:
                drop.add(i)
                i = parent[i]
    return "".join(" " if i in drop else w for i, w in enumerate(words))


def tidy(t):
    """A piece of a bill's text (page and line numbers already gone) without its running heads ("HB2 INTRODUCED",
    "HB92 Enrolled", "PFD: 08-Jul-24", "First Read: 04-Feb-25") and the drafting stamp ("QVP8554-1 05/09/2024 GP (L)
    lg 2024-1803"); then one space between words."""
    t = re.sub(r"\b[HS]B\d+\s*(PREFILED|INTRODUCED|ENGROSSED|ENROLLED|REENROLLED)\b", " ", t, flags=re.I)
    t = re.sub(r"\b(PFD|First Read): \d\d-[A-Za-z]{3}-\d\d\b", " ", t)
    t = re.sub(r"\b[A-Z0-9]{6,9}-\d\b( \d\d/\d\d/\d{4} [^\n\t]*?(\d{4}-\d+|$))?", " ", t, flags=re.M)
    return re.sub(r"\s+", " ", t).strip()


def version_of(full):
    """The version a text is, from its first running head ("HB2 INTRODUCED", "HB92 ENROLLED")."""
    m = re.match(r"\s*[HS]B\d+\s*([A-Za-z]+)", full or "")
    return m.group(1).upper() if m and m.group(1).upper() in VERSIONS else "?"


def text_parts(versions):
    """The parts of a bill's texts the site uses (see the docstring), from {version: text}: the byline, referral and
    title from the latest version read, the synopsis from the latest one that has one (enrolled texts have none)."""
    order = sorted(versions, key=lambda v: VERSIONS.index(v) if v in VERSIONS else -1)
    versions = {v: unnumber(t) for v, t in versions.items()}
    full = versions[order[-1]] if order else ""
    head = full[:1500]
    byline = re.search(r"\bBy (?:Representatives?|Senators?)\b.*?(?=\s+\d*\s*RFD:|\s+\d*\s*First Read:|\s+\d*\s*PFD:|\n)",
                       head, re.S)
    rfd = re.search(r"\bRFD:\s*(.*?)(?=\s+\d*\s*First Read:|\s+\d*\s*PFD:|\s+Page \d|\n)", head, re.S)
    synopsis, source = "", ""
    for v in reversed(order):
        syn = re.search(r"SYNOPSIS:(.*?)(?:\bA BILL\b|\bTO BE ENTITLED\b)", versions[v], re.S)
        if syn:
            synopsis, source = tidy(syn.group(1)), v
            break
    title = re.search(r"(?:\bTO BE ENTITLED\b.{0,80}?\bAN ACT\b|\bEnrolled,\s+An Act,)(.*?)\bBE IT ENACTED\b", full,
                      re.S | re.I)
    return {"version": order[-1] if order else "",
            "byline": tidy(byline.group(0)) if byline else "",
            "rfd": tidy(rfd.group(1)) if rfd else "",
            "synopsis": synopsis, "synopsis_version": source,
            "title": tidy(title.group(1)) if title else "",
            "local_notice": bool(re.search(r"\(N ?& ?P\)|notice of intention to apply", "\n".join(versions.values()),
                                           re.I)),
            "length": len(full)}


# One year ---------------------------------------------------------------------------------------------------------

def read_bills(s, folder, state):
    """The session's bills (one request). Returns the list, or the last copy."""
    a = gql(f"query {{ instruments(where: {{sessionAbbreviation: {{eq: {q(s)}}}, instrumentType: {{eq: B}}}}, "
            f"order: [\"id\", \"ASC\"], limit: 5000) {{ count data {{ {BILL_FIELDS} }} }} }}", f"{s} bills")
    got = ((a or {}).get("data") or {}).get("instruments") or {}
    rows = [b for b in got.get("data") or [] if BILL.match(b.get("instrumentNbr") or "")]
    path = os.path.join(folder, "bills.json")
    if rows and len(got.get("data") or []) == got.get("count"):
        save({"read": TODAY.isoformat(), "bills": rows}, path)
        state["bills"] = TODAY.isoformat()
        return rows
    last = load(path)
    if last:
        print(f"{s} bills: unreadable; kept the last copy", flush=True)
        return last["bills"]
    return []


def read_history(s, folder, state):
    """The session's history lines for bills, in pages; saved only when every page came."""
    lines, offset, total = [], 0, None
    while total is None or offset < total:
        a = gql(f"query {{ instrumentHistories(where: {{sessionAbbreviation: {{eq: {q(s)}}}}}, order: [\"id\", \"ASC\"], "
                f"limit: {HISTORY_PAGE}, offset: {offset}) {{ count data {{ {HISTORY_FIELDS} }} }} }}",
                f"{s} history from {offset}")
        got = ((a or {}).get("data") or {}).get("instrumentHistories")
        if not got or not got.get("data") and offset < (got.get("count") or 0):
            print(f"{s} history: unreadable; kept the last copy", flush=True)
            return (load(os.path.join(folder, "history.json")) or {}).get("lines", [])
        total = got["count"]
        lines += got["data"]
        offset += HISTORY_PAGE
        if not got["data"]:
            break
    ids = [x["id"] for x in lines]
    if len(set(ids)) != len(ids) or len(ids) != total:
        print(f"{s} history: {len(ids)} lines for a count of {total} (changed while read?); kept the last copy",
              flush=True)
        return (load(os.path.join(folder, "history.json")) or {}).get("lines", [])
    lines = [x for x in lines if BILL.match(x.get("instrumentNbr") or "")]
    save({"read": TODAY.isoformat(), "lines": lines}, os.path.join(folder, "history.json"))
    state["history"] = TODAY.isoformat()
    return lines


def read_birs(s, folder, state):
    a = gql(f"query {{ birs(where: {{sessionAbbreviation: {{eq: {q(s)}}}}}, limit: 5000) {{ count data {{ "
            f"instrumentNbr birTitle calendarDate body matter voteType voteTitle rollCallNbr }} }} }}", f"{s} BIRs")
    got = ((a or {}).get("data") or {}).get("birs")
    path = os.path.join(folder, "birs.json")
    if got and len(got["data"]) == got["count"]:
        save({"read": TODAY.isoformat(), "birs": got["data"]}, path)
        state["birs"] = TODAY.isoformat()
        return got["data"]
    return (load(path) or {}).get("birs", [])


def read_votes(s, folder, state, wanted):
    """The roll calls in wanted ({"H59", ...}) not yet read, VOTE_PAGE to a request."""
    path = os.path.join(folder, "votes.json")
    votes = load(path, {})
    missing = state.setdefault("no_record", {})  # roll calls the server had no record of: {key: runs asked}
    todo = sorted((k for k in wanted if k not in votes and missing.get(k, 0) < GIVE_UP_AFTER),
                  key=lambda k: (k[0], int(k[1:])))
    asked = set()
    got = 0
    while todo and not out_of_time():
        batch, todo = todo[:VOTE_PAGE], todo[VOTE_PAGE:]
        parts = [f"{k}: rollCallVotes(sessionAbbreviation: {q(s)}, body: {'House' if k[0] == 'H' else 'Senate'}, "
                 f"rollCallNbr: {int(k[1:])}) {{ yeas nays abstains passes votes {{ memberName vote }} }}" for k in batch]
        a = gql("query { " + " ".join(parts) + " }", f"{s} roll calls {batch[0]}..")
        if a is None:
            continue
        # One roll call the server has no record of voids the whole answer (data: null), with its alias in the
        # error's path: note it and ask for the others again.
        bad = {e["path"][0] for e in a.get("errors") or [] if e.get("path")} & set(batch)
        if a.get("errors") and not bad and not a.get("data"):
            FAILS["query error"] += 1
            continue
        for k in bad:
            if k not in asked:
                missing[k] = missing.get(k, 0) + 1
                asked.add(k)
        if bad:
            todo = [k for k in batch if k not in bad] + todo
            continue
        for k in batch:
            v = (a.get("data") or {}).get(k)
            if v:
                votes[k] = v
                missing.pop(k, None)
                got += 1
        if got and got % 100 < VOTE_PAGE:
            save(votes, path)
    save(votes, path)
    STATS["votes"] += got
    left = [k for k in wanted if k not in votes]
    print(f"{s} roll calls: {len(wanted)} in the histories, {got} read this run, {len(votes)} on file"
          + (f", {len(left)} not read ({sum(missing.get(k, 0) >= GIVE_UP_AFTER for k in left)} given up: no record)"
             if left else ""), flush=True)
    return not [k for k in left if missing.get(k, 0) < GIVE_UP_AFTER]


def latest_version(bill):
    """The newest version the bill's PDF links show ("ENROLLED"): its text is read again when this changes."""
    for v, field in (("REENROLLED", "reenrolledFileUrl"), ("ENROLLED", "enrolledFileUrl"),
                     ("ENGROSSED", "engrossedFileUrl"), ("INTRODUCED", "introducedFileUrl")):
        if bill.get(field):
            return v
    return "PREFILED"


def write_texts(folder, raw=None):
    """texts.json, made again from the kept texts each run (finished years too), so a better parser needs no new
    downloads."""
    if raw is None:
        try:
            with gzip.open(os.path.join(folder, "texts_raw.json.gz"), "rt", encoding="utf-8") as f:
                raw = json.load(f)
        except (OSError, ValueError):
            return
    save({k: text_parts(v) for k, v in raw.get("texts", {}).items()}, os.path.join(folder, "texts.json"))


def read_texts(s, folder, bills):
    """Each bill's text (the endpoint's fullText is the newest version's), TEXT_PAGE to a request: once, and again when
    a newer version appears. Every version read is kept, so a bill read while live keeps its introduced synopsis."""
    raw_path = os.path.join(folder, "texts_raw.json.gz")
    try:
        with gzip.open(raw_path, "rt", encoding="utf-8") as f:
            raw = json.load(f)
    except (OSError, ValueError):
        raw = {}
    raw.setdefault("asked", {})
    texts = raw.setdefault("texts", {})

    def keep():
        tmp = raw_path + ".tmp"
        with gzip.open(tmp, "wt", encoding="utf-8") as f:
            json.dump(raw, f, ensure_ascii=False)
        os.replace(tmp, raw_path)

    want = {b["instrumentNbr"]: latest_version(b) for b in bills}
    todo = [k for k, v in want.items() if raw["asked"].get(k) != v]
    got = 0
    while todo and not out_of_time():
        batch, todo = todo[:TEXT_PAGE], todo[TEXT_PAGE:]
        a = gql(f"query {{ instruments(where: {{sessionAbbreviation: {{eq: {q(s)}}}, instrumentNbr: {{in: "
                f"{json.dumps(batch)}}}}}) {{ data {{ instrumentNbr fullText }} }} }}", f"{s} texts {batch[0]}..")
        rows = (((a or {}).get("data") or {}).get("instruments") or {}).get("data")
        if rows is None:
            continue
        for x in rows:
            k = x["instrumentNbr"]
            if k in batch:
                if x.get("fullText"):
                    texts.setdefault(k, {})[version_of(x["fullText"])] = x["fullText"]
                raw["asked"][k] = want[k]  # a bill with no text yet is asked again only when a version appears
                got += 1
        if got % 200 < TEXT_PAGE:
            keep()
    if got:
        keep()
    write_texts(folder, raw)
    STATS["texts"] += got
    left = sum(raw["asked"].get(k) != v for k, v in want.items())
    print(f"{s} texts: {got} read this run, {len(texts)} on file" + (f", {left} not read" if left else ""), flush=True)
    return not left


def session(year):
    s = f"{year}RS"
    folder = os.path.join(DATA, str(year))
    state_path = os.path.join(folder, "state.json")
    state = load(state_path, {})
    if state.get("finished"):
        write_texts(folder)
        print(f"{year}: finished and fully read; nothing to download", flush=True)
        return
    os.makedirs(folder, exist_ok=True)
    bills = read_bills(s, folder, state)
    if not bills:
        print(f"{s}: no bills" + (" yet" if year >= YEAR else ""), flush=True)
        save(state, state_path)
        return
    lines = read_history(s, folder, state) if not out_of_time() else []
    birs = read_birs(s, folder, state) if not out_of_time() else []
    save(state, state_path)
    wanted = {f"{x['body'][0]}{x['rollCallNbr']}" for x in lines + birs
              if x.get("rollCallNbr") and x.get("body") in ("House", "Senate")}
    status = Counter(b["currentStatus"] for b in bills)
    print(f"{s}: {len(bills)} bills ({sum(bool(b.get('actNbr')) for b in bills)} with Act numbers; "
          f"{status.get('Enacted', 0)} enacted), {len(lines)} history lines, {len(birs)} BIRs", flush=True)
    votes_done = read_votes(s, folder, state, wanted) if not out_of_time() else False
    save(state, state_path)
    texts_done = read_texts(s, folder, bills) if not out_of_time() else False
    after = TODAY.isoformat() >= finished_by(year)
    if after and votes_done and texts_done and all(state.get(k, "") >= finished_by(year)
                                                   for k in ("bills", "history", "birs")):
        state["finished"] = True
        print(f"{year}: finished", flush=True)
    save(state, state_path)


# Members and committees -------------------------------------------------------------------------------------------

def members():
    """Every member record and every public committee with its members, weekly. Returns True when there is a copy."""
    folder = os.path.join(DATA, "members")
    os.makedirs(folder, exist_ok=True)
    path, cpath = os.path.join(folder, "members.json"), os.path.join(folder, "committees.json")
    last = load(path)
    week_ago = (TODAY - timedelta(days=MEMBER_DAYS)).isoformat()
    if not (last and last.get("read", "") >= week_ago):
        a = gql(f"query {{ legislativeMembers(where: {{}}, limit: 5000) {{ count data {{ {MEMBER_FIELDS} }} }} }}",
                "members")
        got = ((a or {}).get("data") or {}).get("legislativeMembers")
        current = [m for m in (got or {}).get("data") or [] if m.get("active")]
        if got and len(got["data"]) == got["count"] and len(current) > 100:
            save({"read": TODAY.isoformat(), "members": got["data"]}, path)
            print(f"members: {sum(m['body'] == 'House' for m in current)} representatives, "
                  f"{sum(m['body'] == 'Senate' for m in current)} senators", flush=True)
        else:
            print("members: unreadable; kept the last copy", flush=True)
    last = load(cpath)
    if not (last and last.get("read", "") >= week_ago) and not out_of_time():
        a = gql("query { committees(where: {showToPublic: {eq: true}}, limit: 1000) { count data { id name body type "
                "contactName contactEmail contactPhone contactLocation } } }", "committees")
        got = ((a or {}).get("data") or {}).get("committees")
        comms = (got or {}).get("data") or []
        ok = bool(comms) and len(comms) == got.get("count")
        # A committee the server fails on ("Unexpected error.": a few joint interim ones) voids the whole answer, with
        # its alias in the error's path: it's left without members and the others are asked for again.
        todo = list(comms)
        while ok and todo:
            if out_of_time():
                ok = False
                break
            batch, todo = todo[:VOTE_PAGE], todo[VOTE_PAGE:]
            a = gql("query { " + " ".join(f"c{c['id']}: committee(id: {q(c['id'])}) {{ assignments {{ position "
                                          f"member {{ id fullName body }} }} }}" for c in batch) + " }",
                    f"committee members {batch[0]['name']}..")
            if a is None:
                ok = False
                break
            bad = {e["path"][0] for e in a.get("errors") or [] if e.get("path")} & {f"c{c['id']}" for c in batch}
            if bad:
                for c in batch:
                    if f"c{c['id']}" in bad:
                        c["members"] = None
                todo = [c for c in batch if f"c{c['id']}" not in bad] + todo
                continue
            if a.get("errors") or not a.get("data"):
                ok = False
                break
            for c in batch:
                c["members"] = [{"position": x["position"], **(x.get("member") or {})}
                                for x in (a["data"].get(f"c{c['id']}") or {}).get("assignments") or []]
        if ok:
            save({"read": TODAY.isoformat(), "committees": comms}, cpath)
            print(f"committees: {len(comms)} ({Counter(c['body'] + ' ' + (c['type'] or '') for c in comms)}), "
                  f"{sum(any(m['position'] in ('Chair', 'Chairperson') for m in c['members'] or []) for c in comms)} with a chair, "
                  f"{sum(c['members'] is None for c in comms)} whose members the server fails to give",
                  flush=True)
        else:
            print("committees: unreadable; kept the last copy", flush=True)
    return os.path.exists(path) and os.path.exists(cpath)


def begun(year):
    """Whether a year's regular session has convened: the second Tuesday of January in election years (2026), the first
    Tuesday of March in the year after (2027), else the first Tuesday of February. Prefiled bills of one not yet begun
    are read when they're there but never hold Alabama off the site."""
    month, nth = {2: (1, 2), 3: (3, 1)}.get(year % 4, (2, 1))
    return TODAY >= date(year, month, 1 + (1 - date(year, month, 1).weekday()) % 7 + 7 * (nth - 1))


def never_downloaded(years):
    """What was never downloaded: a year's bill list or history, the members or committees. (A failed refresh with a
    last copy doesn't count; nor does a year with no bills yet; nor roll calls and texts, which fill in run by run.)"""
    out = []
    for name in ("members", "committees"):
        if not os.path.exists(os.path.join(DATA, "members", f"{name}.json")):
            out.append(name)
    for year in years:
        if not begun(year):
            continue
        folder = os.path.join(DATA, str(year))
        if not os.path.exists(os.path.join(folder, "bills.json")):
            if year < YEAR:
                out.append(f"{year}:bills")
            continue
        for name in ("history", "birs"):
            if not os.path.exists(os.path.join(folder, f"{name}.json")):
                out.append(f"{year}:{name}")
    return out


def main():
    os.makedirs(DATA, exist_ok=True)
    # Before the first copy, a run cut off without its summary leaves this, so a partial copy isn't published.
    if not ONLY and not any(name.isdigit() for name in os.listdir(DATA)):
        with open(MARKER, "w") as f:
            f.write("running\n")
    years = [ONLY] if ONLY else [YEAR, YEAR - 1, YEAR - 2]
    refused = False
    try:
        if not ONLY:
            members()
        for year in years:  # the current year first
            if out_of_time():
                break
            session(year)
    except Refused as e:
        print(f"Stopped: the server refused a request ({e})", flush=True)
        refused = True
    missing = never_downloaded(years)
    print(f"run: {STATS['requests']} requests ({STATS['votes']} roll calls, {STATS['texts']} texts), "
          f"{round((time.time() - START) / 60)} min"
          + ("; stopped at the time limit" if out_of_time() else "")
          + ("; refused" if refused else "")
          + (f"; request failures {dict(FAILS)}" if FAILS else "; no request failures")
          + (f"; never downloaded: {' '.join(missing)}" if missing else "; nothing missing"), flush=True)
    if ONLY:
        return
    # Left while data that was never downloaded is missing, so a partial first copy isn't published.
    if missing:
        with open(MARKER, "w") as f:
            f.write(" ".join(missing) + "\n")
    elif os.path.exists(MARKER):
        os.remove(MARKER)


if __name__ == "__main__":
    main()
