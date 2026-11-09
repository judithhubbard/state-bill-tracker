#!/usr/bin/env python3
"""Download South Carolina's bills from South Carolina Legislature Online (https://www.scstatehouse.gov/), the
Legislative Services Agency's site: server-built HTML (and PDF roll calls); there is no API or bulk file. Its robots.txt
(checked 2026-11-09; scstatehouse.gov only redirects to www.) bars /images/, /jpeg/, /gif/, /dashboard/ and /sys/ for all
user agents, none of which are read, and sets no crawl delay. One request at a time, at most one a second (counted from
the start of the last one). The site is behind Cloudflare: 401, 403, 429 or a challenge page stops the run. Its old
addresses ending in ".php" answer with a redirect to the same address without it; the new ones are asked directly.

South Carolina's General Assembly is numbered (the 126th is 2025-26, the 125th 2023-24) and meets from the second
Tuesday of January to early May each year (sine die; it comes back later for vetoes, conference reports and the budget,
as it did in June and August 2026). Bills not finished in the first year carry over to the second. Bills are prefiled
in December before each year. Each chamber numbers from its own range, shared by every kind of measure: Senate from 1,
House from 3001 (S 1, H 3001), so a number alone names the bill. Kinds: "General Bill", "Joint Resolution" (which have
the force of law; the ones that propose an amendment to the South Carolina Constitution are joint resolutions too,
"A JOINT RESOLUTION PROPOSING AN AMENDMENT TO SECTION 3, ARTICLE XVII OF THE CONSTITUTION ...": they pass each house by
two-thirds, go to the voters at the next general election without the governor, and are ratified by a later act;
telling them from other joint resolutions is the converter's job), "Concurrent Resolution" and "Resolution" (kept
only as counts). For FIRST_SESSION on (the 125th; and the next one once it has prefiled bills), into
data/sc/<first year>/:
- bills.json: {"H3020": {...}}, every General Bill and Joint Resolution, from the bill search
  (/billsearch?billnumbers=3001,3002,...&session=126&summary=B&headerfooter=1, which answers at most 20 bills a
  request: the whole of a session is about 190 requests). Each record: "kind", "star" (the "*" after the chamber
  letter: the bill has been amended), "rat" and "act" (ratification and Act numbers, "act_year"), "sponsors" in order
  ([{"code" (ten digits, zero-padded, as on the members' pages), "name" ("G.M. Smith"), "chamber"}]; a committee
  sponsor has no code), "by" (the byline as written: "Judiciary Committee"), "similar" (["S43", "H3560"]), "subject"
  ("Status Offenses"), "title" (the official title, which is all the summary there is: there are no plain-language
  summaries in the search; "title_note" keeps a trailer like "RATIFIED TITLE"), "text" (the bill text's address),
  "votes" and "fiscal" (whether the record links a vote history and a fiscal impact statement), "history" ([{"date"
  "12/05/24", "chamber" ("House", "Senate" or ""), "action" ("Referred to Committee on Judiciary", "Roll call
  Yeas-105 Nays-0", "Ratified R 167", "Signed By Governor", "Vetoed by Governor", "Act No. 212"), "vote" (the roll
  call's KEY, when linked), "journal" (the journal page's address)}], in the page's order (effective dates and Act
  numbers come last, out of date order) and "status" (the site's own status graphic data: [{"text": "Passed",
  "chamber": "H", "level": 3, ...}]).
- numbers.json: {"H": {"3001": "Resolution", ...}, "S": {...}}: every number the search answered and its kind, so
  the converter can count resolutions, and the next run knows where each chamber's numbers end.
- votes_H.json, votes_S.json: each chamber's roll-call list for the session (/votehistory?op=votehistorysearch&session=
  126&chamber=H: one page, about 2.5 MB): [{"key" (27477), "number" ("[S]-811"; "[J]-24" for joint elections),
  "bill" ("H3020"), "subject", "motion" ("2nd Reading", "Concur in Senate Amendments", "Override Veto"), "time"
  ("04/29/2026 04:53 pm"), "candidate", "counts" {"yeas", "nays", "not_voting", "excused", "present", "abstain",
  "total"}, "result"}]. Elections and motions with no bill are listed too.
- rollcalls/<KEY>.json: each roll call on a General Bill or Joint Resolution member by member, from its PDF
  (/votehistory?KEY=27477, about 40 KB: FPDF output, read here without a PDF library): {"key", "head" (the heading lines:
  "Senate Roll Call Vote Number 811", "Session: 126 (2025-2026)", the time, the motion, "RESULT: Passed", "Ayes: 42;
  Nays: 1; Excused Absence: 3", the bill and its subject), "groups": [["AYES", 42, ["Adams, Brian", ...]], ["NAYS", 1,
  [...]], ["EXCUSED ABSENCE", 3, [...]], ["NOT VOTING", ...]]}; names are "Last, First M., Jr." as the members' list
  writes them. Read once each (a roll call doesn't change); about 2,100 a session, so they fill in over several runs.
- acts_<year>.json: the year's Acts (/listofacts?Y=2026): [{"act" ("95"), "rat" ("98"), "bill" ("S336"),
  "description", "effective"}], to check laws against. Read daily while the year is live, once after.
- members_H.json, members_S.json: the session's members list (/member?chamber=H&session=126): [{"code", "district",
  "name" ("Representative Terry Alexander"), "party" ("D"), "address"}].
And into data/sc/:
- members/<code>.json: each member's page (/member?code=0011363635): {"code", "chamber", "name", "position" ("Minority
  Leader"), "party" ("Democrat"), "county", "district", "district_counties", "columbia" {"address", "phones":
  {"Business Phone": ...}}, "home" {...}, "committees" (names), "contact" (the page's message form: the site shows no
  email addresses)}. Read once for members of past sessions, weekly for the newest session's.
- committees_H.json, committees_S.json: the standing committees today (/committee?chamber=H): [{"name" ("Judiciary"),
  "note" ("Privileges & Elections"), "page", "chair" {"code", "name", "phone", "room"}, "members": [{"code", "name"
  ("Newton, Wm. Weston J."), "role" ("Chairman", "1st V.C.")}]}]. Weekly. Past sessions' committees aren't published.
- state.json: when each part was read, each session's ranges, the roll calls tried and failed.

What's read again: the newest session's bills and roll-call lists every run from January to June, daily otherwise; a
past session's monthly (about 190 requests). Members' pages weekly for the newest session; committees weekly. A first
copy of two sessions is about 380 bill-search requests, 8 lists, 8 acts lists and about 250 members' pages: about 12
minutes; the roll calls (about 4,300) take about 75 minutes more, over later runs. After that a run in session is about
200 requests plus new roll calls: about 4 minutes; out of session, a few requests (a run a day: about 4 minutes).

Not downloaded: bill texts (/sess126_2025-2026/bills/3020.htm), fiscal impact statements, journals, committee agendas
and minutes, amendments, the ratification sheets (the history has the same numbers), the governor's veto messages (in
the journals). The site's "LSA Bill Summary" search covers summaries of Acts only and isn't read.

data/sc/incomplete says "running" during the first copy, then lists what was never downloaded (a session's bill
ranges, a session's members list, a member's page); it is removed when nothing is missing. Roll calls, vote lists, acts
lists and committees fill in on later runs and don't hold the state back. A request that fails where a last copy exists
keeps that copy and doesn't count.
Usage: python3 states/sc/fetch.py [session number]   (default: every session above; one leaves the marker alone)
"""
import gzip, html, json, os, re, sys, time, urllib.error, urllib.request, zlib
from collections import Counter
from datetime import date, timedelta

SITE = "https://www.scstatehouse.gov"
DATA = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "sc"))
AGENT = "statebilltracker.org (a nonprofit bill tracker; contact via github.com/judithhubbard)"
TODAY = date.today()
ONLY = int(sys.argv[1]) if len(sys.argv) > 1 else None
FIRST_SESSION = 125  # 2023-24
DELAY = 1.0  # seconds between the starts of two requests
CHUNK = 20  # the bill search answers at most 20 numbers a request
STARTS = {"S": 1, "H": 3001}
EMPTY_CHUNKS = 3  # this many empty chunks past the last number found end a chamber's range
KEPT = ("General Bill", "Joint Resolution")
KINDS = ("General Bill", "Joint Resolution", "Concurrent Resolution", "Resolution")
WEEKLY, MONTHLY = 7, 30
MEMBERS = os.path.join(DATA, "members")
STATE = os.path.join(DATA, "state.json")
MARKER = os.path.join(DATA, "incomplete")

# The run's own time limit (FETCH_MINUTES, set by the workflow): stop a few minutes early, with everything read so far
# saved and a summary printed, rather than be cut off silently mid-request.
START = time.time()
BUDGET = max(0.0, float(os.environ.get("FETCH_MINUTES") or 0) - 5) * 60
FAILS = Counter()  # why requests failed, for the summary
STATS = Counter()
LAST = [0.0]  # when the last request started
CODE = [0]  # the last request's HTTP status (404: not there)


class Refused(Exception):
    """The server turned us away (401/403/429, or a challenge page): stop the run."""


def out_of_time():
    return BUDGET and time.time() - START > BUDGET


def request(path, label, must=None, binary=False):
    """GET SITE + path: the page as text (bytes if binary), or None after three tries; None at once for a 404 (CODE[0]
    is then 404). must is text the page has to contain (else it counts as a failure: an error page served as 200)."""
    CODE[0] = 0
    for attempt in range(3):
        if out_of_time():
            return None
        wait = LAST[0] + DELAY - time.time()
        if wait > 0:
            time.sleep(wait)
        LAST[0] = time.time()
        STATS["requests"] += 1
        if STATS["requests"] % 100 == 0:
            print(f"  {STATS['requests']} requests, {round((time.time() - START) / 60)} min"
                  + (f"; failures {dict(FAILS)}" if FAILS else ""), flush=True)
        try:
            req = urllib.request.Request(SITE + path, headers={"User-Agent": AGENT, "Accept-Encoding": "gzip"})
            with urllib.request.urlopen(req, timeout=90) as r:
                body = r.read()
                if r.headers.get("Content-Encoding") == "gzip":
                    body = gzip.decompress(body)
                length = r.headers.get("Content-Length")
            if length and r.headers.get("Content-Encoding") != "gzip" and int(length) != len(body):
                FAILS["cut off"] += 1
                continue
            if b"challenge-platform" in body[:20000] or b"Just a moment..." in body[:3000]:
                raise Refused(f"{label}: a challenge page")
            if binary:
                if must and not body.startswith(must):
                    FAILS["unexpected page"] += 1
                else:
                    return body
            else:
                page = body.decode("cp1252", "replace")
                if must and must not in page:
                    FAILS["unexpected page"] += 1
                else:
                    return page
        except Refused:
            raise
        except urllib.error.HTTPError as e:
            FAILS[f"HTTP {e.code}"] += 1
            if e.code in (401, 403, 429):
                raise Refused(f"{label}: HTTP {e.code}")
            if e.code == 404:
                CODE[0] = 404
                return None
        except Exception as e:
            FAILS[type(e).__name__] += 1
        time.sleep(5 * (attempt + 1))
    print(f"{label}: failed three times", flush=True)
    return None


def text(fragment):
    t = re.sub(r"<br\s*/?>", "\n", fragment, flags=re.I)
    t = html.unescape(re.sub(r"<[^>]+>", " ", t)).replace("\xa0", " ")
    return "\n".join(re.sub(r"[ \t\r]+", " ", line).strip() for line in t.split("\n")).strip()


def flat(fragment):
    return re.sub(r"\s+", " ", text(fragment)).strip()


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


def ago(day, days):
    """True when day (ISO) is missing or at least days old."""
    return not day or day <= (TODAY - timedelta(days=days)).isoformat()


def code10(code):
    return str(int(code)).zfill(10) if code and str(code).isdigit() else code


def first_year(session):
    return 2 * session + 1773  # 126 -> 2025


def bill_key(chamber, number):
    return f"{chamber}{int(number)}"


# Sessions


def sessions(state):
    """The sessions to read, newest first: FIRST_SESSION up to the newest the bill search offers (the next one appears
    with its prefiled bills). The search page's session list is read once a day."""
    found = state.get("sessions") or []
    if ago(state.get("sessions_read"), 1) or not found:
        page = request("/billsearch?op=billsearch", "sessions", must='name="session"')
        if page:
            offered = sorted({int(n) for n in re.findall(r'<option value="(\d{3})"', page)})
            if offered:
                found = [n for n in offered if n >= FIRST_SESSION]
                state["sessions"] = found
                state["sessions_read"] = TODAY.isoformat()
    if not found:
        found = [FIRST_SESSION, FIRST_SESSION + 1]
    out = sorted(found, reverse=True)
    return [s for s in out if not ONLY or s == ONLY]


def live(session):
    """A session's records change until the end of its second year (vetoes, Act numbers, effective dates)."""
    return TODAY <= date(first_year(session) + 1, 12, 31)


def in_session():
    return 1 <= TODAY.month <= 6


# Bills


ITEM = re.compile(r'<div class="bill-list-item"[^>]*>(.*?)(?=<div class="bill-list-item"|</div><script>\$\(\'\.bill-list-item)', re.S)


def parse_item(chunk):
    """One bill-list-item (with its billStatusJsonArray.push script) as a record; None if it isn't one."""
    head = re.search(r'<span style="font-weight:bold;">\s*([HS])([ *])(\d+)\s*(.*?)</span>', chunk, re.S)
    if not head:
        return None
    chamber, star, number, rest = head.groups()
    out = {"chamber": chamber, "number": int(number), "star": star == "*"}
    m = re.match(r"\s*\((.*?)\)\s*", rest)
    if m:
        inner = m.group(1)
        rat = re.search(r"Rat #0*(\d+)", inner)
        act = re.search(r"Act #0*(\d+)(?: of (\d{4}))?", inner)
        out["rat"] = rat.group(1) if rat else None
        out["act"] = act.group(1) if act else None
        out["act_year"] = act.group(2) if act and act.group(2) else None
        if not rat and not act:
            out["note"] = flat(inner)
        rest = rest[m.end():]
    kind = re.match(r"\s*(.*?),\s*By\s*(.*?)(?:<br\s*/?>)?\s*$", rest, re.S)
    if kind:
        out["kind"] = flat(kind.group(1))
        by = kind.group(2)
    else:
        out["kind"] = flat(rest)
        by = ""
    out["by"] = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", by)).replace("\xa0", " ")).strip()
    sponsors = []
    for link in re.finditer(r'<a href="/member\.php\?code=(\d+)&(?:amp;)?chamber=([HS])">(.*?)</a>', by):
        sponsors.append({"code": code10(link.group(1)), "name": flat(link.group(3)), "chamber": link.group(2)})
    if not sponsors and out["by"]:
        sponsors.append({"code": None, "name": out["by"], "chamber": chamber})  # a committee
    out["sponsors"] = sponsors
    after = chunk[head.end():]
    sim = re.search(r"Similar \((.*?)\)<br", after, re.S | re.I)
    out["similar"] = [k + str(int(n)) for k, n in re.findall(r">\s*([HS]) (\d+)\s*<", sim.group(1))] if sim else []
    summ = re.search(r"<b>Summary: </b>(.*?)<br\s*/?>(.*?)(?:<br class=\"nodisplay\"|<a href=\"/sess|<table)", after, re.S)
    if summ:
        out["subject"] = flat(summ.group(1))
        title = flat(summ.group(2))
        note = re.search(r"\s+-\s+([A-Z ]*TITLE)$", title)
        if note:
            out["title_note"] = note.group(1)
            title = title[:note.start()]
        out["title"] = title
    else:
        out["subject"], out["title"] = "", ""
    link = re.search(r'href="(/sess\d+_[^"]+/bills/[^"]+)"', after)
    out["text"] = link.group(1) if link else None
    out["votes"] = "votehistory.php?type=BILL" in after
    out["fiscal"] = "fiscalimpact.php" in after
    history = []
    for row in re.findall(r'<tr class="actionrow.*?</tr>', after, re.S):
        cells = re.findall(r"<td[^>]*>(.*?)</td>", row, re.S)
        if len(cells) < 3:
            continue
        action = cells[2]
        vote = re.search(r"votehistory\.php\?KEY=(\d+)", action)
        journal = re.search(r'href="(/sess\d+_[^"]+/[hs]j\d+/[^"]+)"', action)
        line = flat(re.sub(r"\(<a [^>]*>[^<]*Journal-page[^<]*</a>\)", "", action))
        history.append({"date": flat(cells[0]), "chamber": flat(cells[1]), "action": line,
                        "vote": int(vote.group(1)) if vote else None, "journal": journal.group(1) if journal else None})
    out["history"] = history
    status = re.search(r"billStatusJsonArray\.push\((.*?)\);\s*</script>", chunk, re.S)
    try:
        out["status"] = json.loads(status.group(1)) if status else None
    except ValueError:
        out["status"] = None
    return out


def parse_search(page):
    """The bill search's answer: [record], or None if the page isn't a results page."""
    if 'id="resultsbox"' not in page:
        return None
    out = []
    for m in ITEM.finditer(page):
        rec = parse_item(m.group(1))
        if rec:
            out.append(rec)
        else:
            FAILS["unreadable bill"] += 1
    return out


def read_bills(session, folder, state):
    """Every number of the session, 20 at a time, each chamber from its start until EMPTY_CHUNKS empty answers past
    the last number found (and past the last number known). A chunk that fails keeps its bills' last copies."""
    st = state.setdefault("bills", {}).setdefault(str(session), {})
    path = os.path.join(folder, "bills.json")
    bills = load(path, {}) or {}
    numbers = load(os.path.join(folder, "numbers.json"), {}) or {}
    ok_all, got = True, 0
    for chamber in ("S", "H"):
        known = numbers.setdefault(chamber, {})
        top = max([int(n) for n in known] or [STARTS[chamber]])
        start, empties, ok = STARTS[chamber], 0, True
        while empties < EMPTY_CHUNKS or start <= top:
            if out_of_time():
                ok = False
                break
            nums = list(range(start, start + CHUNK))
            page = request(f"/billsearch?billnumbers={','.join(map(str, nums))}&session={session}&summary=B&headerfooter=1",
                           f"{session} {chamber} {start}", must='id="resultsbox"')
            recs = parse_search(page) if page else None
            had = [n for n in nums if str(n) in known]
            if recs is None or (had and not recs):
                ok = False  # failed (or lost bills it had): keep the last copies
                if start > top:
                    empties += 1  # so a server that keeps failing can't keep the loop going
                start += CHUNK
                continue
            if recs:
                empties = 0
            elif start > top:
                empties += 1
            for r in recs:
                if r["chamber"] != chamber:
                    continue
                known[str(r["number"])] = r["kind"]
                if r["kind"] in KEPT:
                    bills[bill_key(chamber, r["number"])] = r
                    got += 1
                elif r["kind"] not in KINDS:
                    FAILS[f"kind {r['kind'][:30]}"] += 1
            start += CHUNK
        ok_all = ok_all and ok
        if ok:
            st[f"done_{chamber}"] = TODAY.isoformat()
    os.makedirs(folder, exist_ok=True)
    save(bills, path)
    save(numbers, os.path.join(folder, "numbers.json"))
    if ok_all:
        st["read"] = TODAY.isoformat()
    kinds = Counter(v for c in numbers.values() for v in c.values())
    print(f"{session} bills: {got} read this run, {len(bills)} kept; numbers {dict(kinds)}"
          + ("" if ok_all else "; some ranges not finished"), flush=True)
    return ok_all


# Roll calls


def parse_vote_list(page):
    out = []
    for row in re.findall(r'<tr style="background-color:#[0-9a-fA-F]+;" onMouseOver.*?</tr>', page, re.S):
        key = re.search(r'votehistory\.php\?KEY=(\d+)"[^>]*>(.*?)</a>', row)
        if not key:
            continue
        cells = re.findall(r"<td[^>]*>(.*?)</td>", row, re.S)
        if len(cells) < 13:
            continue
        bill = re.search(r">\s*([HS]) (\d+)\s*</a>", cells[1])
        subj = re.match(r"\s*\((.*?)\)\s*<br>", cells[2], re.S)
        n = [flat(c) for c in cells[5:12]]
        out.append({"key": int(key.group(1)), "number": flat(key.group(2)),
                    "bill": bill_key(bill.group(1), bill.group(2)) if bill else None,
                    "subject": flat(subj.group(1)) if subj else "",
                    "motion": flat(cells[2][subj.end():] if subj else cells[2]), "time": flat(cells[3]),
                    "candidate": flat(cells[4]),
                    "counts": dict(zip(("yeas", "nays", "not_voting", "excused", "present", "abstain", "total"),
                                       [int(x) if x.isdigit() else None for x in n])),
                    "result": flat(cells[12])})
    return out


def read_vote_lists(session, folder, state):
    st = state.setdefault("vote_lists", {}).setdefault(str(session), {})
    for chamber in ("H", "S"):
        if out_of_time():
            return
        path = os.path.join(folder, f"votes_{chamber}.json")
        page = request(f"/votehistory?op=votehistorysearch&session={session}&chamber={chamber}&headerfooter=1",
                       f"{session} {chamber} roll calls", must="Vote History")
        rows = parse_vote_list(page) if page else []
        if not rows:
            print(f"{session} {chamber} roll calls: none read" + ("; kept the last copy" if os.path.exists(path) else ""),
                  flush=True)
            continue
        save(rows, path)
        st[chamber] = TODAY.isoformat()
        print(f"{session} {chamber} roll calls: {len(rows)} ({sum(1 for r in rows if r['bill'])} on a bill)", flush=True)


def pdf_string(s):
    s = re.sub(r"\\([0-7]{1,3})", lambda m: chr(int(m.group(1), 8)), s)
    return re.sub(r"\\(.)", r"\1", s)


def parse_rollcall(body):
    """A roll-call PDF's lines: {"head": [...], "groups": [[label, count, [names]]]}; None if none were found."""
    pages = []
    for m in re.finditer(rb"stream\r?\n", body):
        if body[max(0, m.start() - 3):m.start()] == b"end":
            continue
        start = body.rfind(b"<<", 0, m.start())
        while start > 0 and body[start - 2:start] == b"<<":
            start -= 2
        info = body[start:m.start()]  # the stream's dictionary (with any nested ones)
        length = re.search(rb"/Length (\d+)", info)
        if b"/Image" in info or not length:
            continue
        raw = body[m.end():m.end() + int(length.group(1))]
        try:
            data = zlib.decompress(raw) if b"FlateDecode" in info else raw
        except zlib.error:
            continue
        content = data.decode("cp1252", "replace")
        lines = [pdf_string(t) for t in re.findall(r"BT [\d.]+ [\d.]+ Td \((.*?)\) Tj ET", content)]
        if not lines:
            continue
        page_no = next((int(p) for p in re.findall(r"^Page (\d+) of \d+$", "\n".join(lines), re.M)), len(pages) + 1)
        pages.append((page_no, lines))
    if not pages:
        return None
    head, groups = [], []
    for _, lines in sorted(pages, key=lambda p: p[0]):
        for line in lines:
            if re.fullmatch(r"Page \d+ of \d+", line):
                continue
            g = re.fullmatch(r"([A-Z][A-Z /]+?) - (\d+)(?: \(?[Cc]ontinued\)?)?", line.strip())
            if g:
                if groups and groups[-1][0] == g.group(1):
                    continue  # the group goes on from the page before
                groups.append([g.group(1), int(g.group(2)), []])
            elif groups:
                groups[-1][2].append(line.strip())
            else:
                head.append(line.strip())
    return {"head": head, "groups": groups}


def read_rollcalls(found, state):
    """Each roll call on a kept bill, once, newest session first, newest first. A roll call never finished ("RESULT:
    Pending") has no groups. One saved with a group shorter than its count (cut off) is read again."""
    tried = state.setdefault("rollcalls_failed", {})
    got = left = 0
    for session in found:
        folder = os.path.join(DATA, str(first_year(session)))
        bills = load(os.path.join(folder, "bills.json"), {}) or {}
        out = os.path.join(folder, "rollcalls")
        os.makedirs(out, exist_ok=True)
        have = set()
        for n in os.listdir(out):
            if n.endswith(".json"):
                saved = load(os.path.join(out, n), {}) or {}
                if all(g[1] == len(g[2]) for g in saved.get("groups") or []) and "head" in saved:
                    have.add(n[:-5])
        rows = [r for c in ("H", "S") for r in load(os.path.join(folder, f"votes_{c}.json"), []) or []]
        todo = sorted({r["key"] for r in rows if r["bill"] in bills and str(r["key"]) not in have
                       and tried.get(str(r["key"]), 0) < 3}, reverse=True)
        for key in todo:
            if out_of_time():
                left += 1
                continue
            body = request(f"/votehistory?KEY={key}", f"roll call {key}", must=b"%PDF", binary=True)
            vote = parse_rollcall(body) if body else None
            if not vote or not (vote["groups"] or any("Roll Call Vote Number" in h for h in vote["head"])):
                if body:
                    FAILS["unreadable roll call"] += 1
                tried[str(key)] = tried.get(str(key), 0) + 1
                continue
            vote["key"] = key
            save(vote, os.path.join(out, f"{key}.json"))
            tried.pop(str(key), None)
            got += 1
            if got % 100 == 0:
                save(state, STATE)
    print(f"roll calls: {got} read" + (f", {left} left for later runs" if left else ""), flush=True)


# Acts


def read_acts(session, folder, state):
    st = state.setdefault("acts", {})
    for year in (first_year(session), first_year(session) + 1):
        if year > TODAY.year or out_of_time():
            continue
        path = os.path.join(folder, f"acts_{year}.json")
        if os.path.exists(path) and not ago(st.get(str(year)), 1 if year >= TODAY.year - 1 else 365):
            continue
        page = request(f"/listofacts?Y={year}", f"acts {year}", must="contentsection")
        if not page:
            continue
        acts = []
        for dt, dd in re.findall(r"<dt>(.*?)</dt>\s*<dd>(.*?)</dd>", page, re.S):
            m = re.search(r"Act No\.\s*<a[^>]*>(\d+)</a>\s*\(R(\d+),\s*([HS])\s*(\d+)\)", dt)
            if not m:
                continue
            desc = flat(dd).lstrip("- ").strip()
            eff = re.search(r"\s*Effective (.*)$", desc)
            acts.append({"act": m.group(1), "rat": m.group(2), "bill": bill_key(m.group(3), m.group(4)),
                         "description": desc[:eff.start()].strip() if eff else desc,
                         "effective": eff.group(1).strip() if eff else None})
        if not acts:
            print(f"acts {year}: none on the page" + ("; kept the last copy" if os.path.exists(path) else ""), flush=True)
            continue
        save(acts, path)
        st[str(year)] = TODAY.isoformat()
        print(f"acts {year}: {len(acts)}", flush=True)


# Members and committees


def read_member_lists(session, folder, state, newest):
    st = state.setdefault("member_lists", {}).setdefault(str(session), {})
    for chamber in ("H", "S"):
        path = os.path.join(folder, f"members_{chamber}.json")
        if os.path.exists(path) and not (live(session) and ago(st.get(chamber), WEEKLY)):
            continue
        if out_of_time():
            return
        page = request(f"/member?chamber={chamber}&session={session}", f"{session} {chamber} members", must="memberOutline")
        if not page:
            continue
        rows = []
        for block in re.findall(r'<div class="member">(.*?)</div>\s*</div>', page, re.S):
            code = re.search(r"member\.php\?code=(\d+)", block)
            dist = re.search(r">District (\w+)<", block)
            name = re.search(r'class="membername"[^>]*>(.*?)</a>\s*(?:\((\w+)\))?', block, re.S)
            addr = re.search(r'<div id="address">(.*?)</div>', block, re.S)
            if code:
                rows.append({"code": code10(code.group(1)), "district": dist.group(1) if dist else None,
                             "name": flat(name.group(1)) if name else "", "party": name.group(2) if name else None,
                             "address": flat(addr.group(1)) if addr else ""})
        if not rows:
            print(f"{session} {chamber} members: none on the page", flush=True)
            continue
        save(rows, path)
        st[chamber] = TODAY.isoformat()
        print(f"{session} {chamber} members: {len(rows)}", flush=True)


def parse_member(page, code):
    a = page.find('id="contentsection"')
    if a < 0:
        return None
    body = page[a:]
    name = re.search(r'<h2 class="barheader">(.*?)</h2>', body, re.S)
    if not name:
        return None
    paras = [flat(p) for p in re.findall(r'<p style="[^"]*font-size: 1[57]px[^"]*">(.*?)</p>', body[:body.find("Columbia Address") if "Columbia Address" in body else 4000], re.S)]
    out = {"code": code, "name": flat(name.group(1)), "position": "", "party": None, "county": None, "district": None,
           "district_counties": None}
    for p in paras:
        d = re.match(r"District (\w+)\s*-\s*(.*?)(?:\s*-\s*Map)?$", p)
        pc = re.match(r"(Democrat|Republican|Independent|Libertarian|[A-Z][a-z]+)\s*-\s*(.+)$", p)
        if d:
            out["district"], out["district_counties"] = d.group(1), d.group(2)
        elif pc and not out["party"]:
            out["party"], out["county"] = pc.group(1), pc.group(2)
        elif p and not out["position"]:
            out["position"] = p
    out["chamber"] = "S" if out["name"].startswith("Senator") else "H" if out["name"].startswith("Representative") else None
    for label, key in (("Columbia Address", "columbia"), ("Home Address", "home")):
        m = re.search(rf"<h2[^>]*>{label}</h2>(.*?)</div>", body, re.S)
        if m:
            ps = re.findall(r"<p[^>]*>(.*?)</p>", m.group(1), re.S)
            phones = {}
            for p in ps:
                for lab, num in re.findall(r'<span style="font-weight: bold;">(.*?)</span>\s*([^<]+)', p):
                    phones[flat(lab)] = flat(num)
            addr = [text(p) for p in ps if "font-weight: bold" not in p]
            out[key] = {"address": "\n".join(addr).strip(), "phones": phones}
    comm = re.search(r"Committee Assignments</h2>\s*<ul[^>]*>(.*?)</ul>", body, re.S)
    out["committees"] = [flat(li) for li in re.findall(r"<li[^>]*>(.*?)</li>", comm.group(1), re.S)] if comm else []
    form = re.search(r'href="(/email\.php\?T=M&(?:amp;)?C=\d+)"', body)
    out["contact"] = SITE + html.unescape(form.group(1)) if form else None
    return out


def read_member_pages(found, state):
    os.makedirs(MEMBERS, exist_ok=True)
    seen = state.setdefault("member_pages", {})  # code -> {"read": day} or {"gone": day}
    want, current = {}, set()
    for i, session in enumerate(found):
        folder = os.path.join(DATA, str(first_year(session)))
        for chamber in ("H", "S"):
            for m in load(os.path.join(folder, f"members_{chamber}.json"), []) or []:
                want.setdefault(m["code"], chamber)
                if i == 0:
                    current.add(m["code"])
    todo = [c for c in want if not seen.get(c, {}).get("gone")
            and (not os.path.exists(os.path.join(MEMBERS, f"{c}.json")) or (c in current and ago(seen.get(c, {}).get("read"), WEEKLY)))]
    got = 0
    for code in todo:
        if out_of_time():
            break
        page = request(f"/member?code={code}&chamber={want[code]}", f"member {code}", must="contentsection")
        if page is None and CODE[0] == 404:
            seen[code] = {"gone": TODAY.isoformat()}
            continue
        info = parse_member(page, code) if page else None
        if not info:
            if page:
                print(f"member {code}: not a member's page" + ("; kept the last copy" if os.path.exists(
                    os.path.join(MEMBERS, f"{code}.json")) else ""), flush=True)
            continue
        save(info, os.path.join(MEMBERS, f"{code}.json"))
        seen[code] = {"read": TODAY.isoformat()}
        got += 1
    print(f"members' pages: {got} of {len(todo)} read ({len(want)} members)", flush=True)


def parse_committees(page):
    a = page.find('id="contentsection"')
    body = page[a:]
    chairs = {}
    for row in re.findall(r'<div style="width: 750px; height: 16px; margin: 0 0 0 -25px;.*?</div></div>', body, re.S):
        cells = re.findall(r'<div style="float:left;[^"]*">(.*?)</div>', row, re.S)
        anchor = re.search(r'HREF="#(\w+)"', row)
        chair = re.search(r"member\.php\?code=(\d+)", row)
        if anchor and len(cells) >= 4:
            chairs[anchor.group(1)] = {"code": code10(chair.group(1)) if chair else None, "name": flat(cells[1]),
                                       "phone": flat(cells[2]), "room": flat(cells[3])}
    out = []
    parts = re.split(r'<a name="(\w+)"></a>', body)
    for i in range(1, len(parts) - 1, 2):
        anchor, chunk = parts[i], parts[i + 1]
        h4 = re.search(r"<h4[^>]*>(.*?)</h4>", chunk, re.S)
        if not h4:
            continue
        lines = text(h4.group(1)).split("\n")
        page_link = re.search(r'href="(/CommitteeInfo/[^"]+)"', h4.group(1))
        members = []
        box = re.search(r'<div id="comm_\w+"(.*?)<div style="clear: both;"></div>', chunk, re.S)
        for code, inner in re.findall(r'<a [^>]*href="/member\.php\?code=(\d+)">(.*?)</a>', box.group(1) if box else "", re.S):
            role = re.search(r"<span[^>]*font-style: italic;[^>]*>(.*?)</span>", inner, re.S)
            name = flat(re.sub(r"<span.*?</span>", "", inner, flags=re.S)).rstrip(", ")
            members.append({"code": code10(code), "name": name, "role": flat(role.group(1)) if role else ""})
        out.append({"anchor": anchor, "name": lines[0].strip(), "note": " ".join(l.strip("() ") for l in lines[1:]).strip(),
                    "page": page_link.group(1) if page_link else None, "chair": chairs.get(anchor), "members": members})
    return out


def read_committees(state):
    st = state.setdefault("committees", {})
    for chamber in ("H", "S"):
        path = os.path.join(DATA, f"committees_{chamber}.json")
        if os.path.exists(path) and not ago(st.get(chamber), WEEKLY):
            continue
        if out_of_time():
            return
        page = request(f"/committee?chamber={chamber}", f"{chamber} committees", must="contentsection")
        found = parse_committees(page) if page else []
        if not found:
            print(f"{chamber} committees: none read" + ("; kept the last copy" if os.path.exists(path) else ""), flush=True)
            continue
        save(found, path)
        st[chamber] = TODAY.isoformat()
        print(f"{chamber} committees: {len(found)} ({sum(len(c['members']) for c in found)} seats)", flush=True)


# The run


def never_downloaded(found, state):
    gaps = []
    pages = state.get("member_pages") or {}
    for i, session in enumerate(found):
        folder = os.path.join(DATA, str(first_year(session)))
        st = (state.get("bills") or {}).get(str(session)) or {}
        for chamber in ("S", "H"):
            if not st.get(f"done_{chamber}"):
                gaps.append(f"{session}:bills_{chamber}")
            path = os.path.join(folder, f"members_{chamber}.json")
            if not os.path.exists(path):
                gaps.append(f"{session}:members_{chamber}")
            elif any(not os.path.exists(os.path.join(MEMBERS, f"{m['code']}.json"))
                     and not pages.get(m["code"], {}).get("gone") for m in load(path, []) or []):
                gaps.append(f"{session}:members_{chamber}_pages")
    return gaps


def main():
    os.makedirs(DATA, exist_ok=True)
    # Before the first copy, a run cut off without its summary leaves this, so a partial copy isn't published.
    if not ONLY and not any(name.isdigit() for name in os.listdir(DATA)):
        with open(MARKER, "w") as f:
            f.write("running\n")
    state = load(STATE, {}) or {}
    refused, found = False, []
    try:
        found = sessions(state)
        for i, session in enumerate(found):  # the newest first
            if out_of_time():
                break
            folder = os.path.join(DATA, str(first_year(session)))
            os.makedirs(folder, exist_ok=True)
            st = (state.get("bills") or {}).get(str(session)) or {}
            often = live(session) and (i == 0 or first_year(session) + 1 >= TODAY.year)
            due = (not st.get("read") or (often and (in_session() or ago(st.get("read"), 1)))
                   or ago(st.get("read"), MONTHLY))
            if due:
                read_bills(session, folder, state)
                read_vote_lists(session, folder, state)
            read_acts(session, folder, state)
            read_member_lists(session, folder, state, i == 0)
            save(state, STATE)
        read_member_pages(found, state)
        save(state, STATE)
        if not ONLY:
            read_committees(state)
        save(state, STATE)
        read_rollcalls(found, state)
    except Refused as e:
        print(f"Stopped: the server refused a request ({e})", flush=True)
        refused = True
    save(state, STATE)
    gaps = never_downloaded(found, state)
    if not found:
        gaps.append("sessions")
    sizes = []
    for session in found:
        folder = os.path.join(DATA, str(first_year(session)))
        bills = load(os.path.join(folder, "bills.json"), {}) or {}
        rc = os.path.join(folder, "rollcalls")
        n = len([x for x in os.listdir(rc) if x.endswith(".json")]) if os.path.isdir(rc) else 0
        if bills:
            sizes.append(f"{session} {len(bills)} bills, {n} roll calls")
    print(f"run: {STATS['requests']} requests, {round((time.time() - START) / 60, 1)} min"
          + (f"; {'; '.join(sizes)}" if sizes else "")
          + ("; stopped at the time limit" if out_of_time() else "")
          + ("; refused" if refused else "")
          + (f"; request failures {dict(FAILS)}" if FAILS else "; no request failures")
          + (f"; still missing: {' '.join(gaps)}" if gaps else "; nothing missing"), flush=True)
    if ONLY:
        return
    # Left while data that was never downloaded is missing, so a partial first copy isn't published.
    if gaps:
        with open(MARKER, "w") as f:
            f.write(" ".join(gaps) + "\n")
    elif os.path.exists(MARKER):
        os.remove(MARKER)


if __name__ == "__main__":
    main()
