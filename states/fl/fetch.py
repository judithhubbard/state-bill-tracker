#!/usr/bin/env python3
"""Download Florida's bills from the Florida Senate's website (www.flsenate.gov), whose bill pages cover both houses'
bills (a House bill's page is /Session/Bill/2025/1205, the same as a Senate bill's: numbers are unique within a
session), and members and committees from both houses' websites. There is no API or bulk file open to us.

robots.txt (checked 2026-11-13):
- www.flsenate.gov (and flsenate.gov): Crawl-delay 10, for all user agents. Bars /api/ and /API/ (the API: not used),
  /_Admin/, /elmah.axd/, /Elmah/, /ex/, /Error/, /Webcheck, /_Email, /Senators/*/email and /Offices/email/ (the email
  forms), the tracker's account pages, /Legislators/index.cfm, /Public/GetFile.cfm, /SenateKids/, /Mail and
  /MobileSite/. It allows /Session/ (bill lists, bill pages and the vote and analysis PDFs under them), /Senators/ and
  /Committees/, which is all this script reads: one request every 10 seconds at most, counted from the end of the
  last answer. The site is behind Cloudflare: a challenge page, 401, 403 or 429 stops the run.
- www.flhouse.gov (www.myfloridahouse.gov redirects to it): no crawl delay. Bars /Sections/Bills/bills.aspx (the
  House's bill lists: not read; the Senate's lists cover House bills), /api, /LD, /UC_Page, /check.aspx,
  /CheckStatus/StatusPollerGrid.aspx, /Sections/Documents/loaddoc.aspx, some MyHouse and public-guide forms; bars
  LWP::Simple, lwp-trivial and Yandex entirely. Read here: /Sections/Representatives/ (member lists and contact pages)
  and /Sections/Committees/ (committee lists and pages), two seconds apart.
- www.leg.state.fl.us (Online Sunshine): bars only /employees/ (and everything for the Drifter and SemrushBot
  agents). It has the statutes and links to the two houses' bill pages, nothing structured about bills: not read.
- laws.flrules.org (Laws of Florida, the chapter laws): a Drupal robots.txt with Cloudflare's content signals; not read,
  since each bill page names its chapter ("Chapter No. 2025-21").

Florida's Legislature meets once a year for 60 days: from the first Tuesday after the first Monday in March in odd
years, and in January in even years. Bills for a session are filed from the summer before (SB 2 of 2025 was filed
8/2/2024); the next session's appear here from about November. Special sessions (2025A, 2025B, 2025C, 2026D ...) and
organization sessions (2026O) are left out. For each regular session from two years back through this one (and the next
one once it lists bills), into data/fl/<year>/:
- list.json: {"read": day, "bills": {"HB1205": {"n": 1205, "label": "CS/HB 1205", "title", "by", "last": "5/5/2025
  Chapter No. 2025-21"}}, "other": {label prefix: count}} from the Senate's bill lists (/Session/Bills/2025?chamber=
  senate|house&PageNumber=n, 50 rows a page, about 20 pages a house), which carry each bill's last action. Kept: House
  and Senate bills (HB, SB: general, local, claim, reviser's, trust fund and committee bills) and joint resolutions
  (HJR, SJR: in Florida a joint resolution proposes an amendment to the State Constitution, which goes to the voters,
  not the governor). Left out (counted in "other"): resolutions, concurrent resolutions, memorials.
- bills/<HB1205>.html: each bill's page (/Session/Bill/2025/1205, trimmed to its content): the title and short title,
  bill type ("GENERAL BILL", "CLAIM/LOCAL", "JOINT RESOLUTION"), sponsors in order ("State Affairs Committee;
  Persons-Mulicka; (CO-INTRODUCERS) Bankson; ..."), the effective date, the last action, the Senate committee
  references, then all tabs at once: the history by date and house ("CS passed as amended; YEAS 76, NAYS 31",
  "Approved by Governor", "Vetoed by Governor", "Chapter No. 2025-21"), related bills (identical, similar, compare,
  linked), the bill text versions, amendments, analyses, the vote history (each committee and floor vote with its
  tally and PDF), and the statutes cited. House committee votes aren't on it (only Senate committees').
- votes/<HB1205>.json: {path: {"kind": "floor"|"committee", "label", "text"}}: each vote PDF of the bill as text
  (pdftotext -layout), member by member: floor votes ("Y Abbott-5 ... N Dunkley-97", with the tally, the presiding
  officer, the session day and the motion: "Passage", "Third Reading") and Senate committee votes ("COMMITTEE VOTE
  RECORD": the senators with Yea/Nay columns, the chair marked "CHAIR", the final action). Floor votes on amendments
  (the vote history marks them "- Amendment 369878") aren't read: only their tallies, on the bill page.
- analyses/<HB1205>.json: the staff analysis the converter uses for "What it does": the newest one posted (the House's
  Final Bill Analysis once there is one; the Senate's "Bill Analysis and Fiscal Impact Statement"; a "Message Summary",
  which describes only amendments, only when there's nothing else): {"path", "type", "author", "posted", "text"}, the
  text of its first three pages (the summary is on the first: "SUMMARY ... Effect of the Bill:" for the House, "I.
  Summary:" for the Senate).
- state.json: per bill the list's last action it was read under ("signal"), when it was read ("read"), numbers that
  answer "does not exist" ("absent"), the vote PDFs and analysis it names ("pdfs", "analysis") and those read
  ("pdfs_read", "analysis_read"; PDFs that answer 404 in "pdfs_gone"), and when the lists were read.

And into data/fl/members/<first year>.json, one per two-year term ("2024": the 2024-2026 term, the 2025 and 2026
sessions), for the terms of the sessions read: the Senate list (/Senators/2024-2026: name, district, party, counties,
post ("President")) and the House list (/Sections/Representatives/representatives.aspx?LegislativeTermId=91: name,
member id, district, party, counties, dates); for the current term also each senator's page (/Senators/S10: offices
with phones, committee assignments) and each representative's contact page (contactmember.aspx?MemberId=4800: Capitol
and district offices with phones). Neither house publishes members' email addresses: senators are emailed through a
form under /Senators/*/email (barred by robots.txt) and representatives through a form on the contact page. Past terms'
lists are read once, the current one's weekly; each current member's page weekly, one try each, saved as it's read
("page_read"). Members elected in November have a contact page with no offices until they're assigned (29 of 120 on
2026-11-13).

And into data/fl/committees/: senate.json (the Senate's committee list, /Committees/, and each committee's page,
/Committees/Show/AP/ (it redirects to the latest session's): name, members with roles), house_<term id>.json (the
House's committee list for a term and each committee's page, committeesdetail.aspx?CommitteeId=n: name, leadership
(Chair, Vice Chair, ranking member) and members, by member id), for the current term weekly and past terms once. Just
after an election the new term's committees aren't named yet (November 2026: the Senate's say "TBA", the House lists
none), and the Senate's pages don't show a past term's members; the Senate committee vote PDFs name each chair.

What changes: a bill page is read when it's new or its last action on the list changed; while the session is live
(until September 1 of its year: the governor's actions, chapter numbers and final analyses come after the session), also
every bill not read in a week, oldest first, at most REFRESH_MAX a run; after September 1, each bill once more if it
was last read before then. The lists are read every run from January through June of the session's year, daily
otherwise while it's live, and once after it. Vote PDFs never change: each is read once. Each run reads the member lists
(when due), then the bill lists and bill pages, newest session first, then the members' pages and the committees (when
due), then the floor votes, the analyses and the committee votes. At 10 seconds a request, a first copy of three sessions (about 5,000 bill pages, 14 hours; then about
6,000 floor-vote PDFs, 3,000 analyses and 5,000 committee-vote PDFs, about 40 hours) builds up over many runs: the
bills in about a day of runs, then the votes and analyses, which don't hold the state back. Out of session a run reads
the next session's lists and new bills: about 10 minutes. During a session, about 40 list pages a run plus the bills
that moved.

data/fl/incomplete says "running" during the first copy, then lists what was never downloaded (a session's list, a
listed bill's page, a term's member lists); it is removed when nothing is missing. The next session, before it begins,
doesn't count; nor do members' pages, votes, analyses and committees, which fill in on later runs. A request that fails where a last
copy exists keeps that copy and doesn't count.
Usage: python3 states/fl/fetch.py [year]   (default: every session above; a single year leaves the marker alone)
"""
import html, json, os, re, subprocess, sys, tempfile, time, urllib.parse
from collections import Counter
from datetime import date, datetime, timedelta

SENATE = "https://www.flsenate.gov"
HOUSE = "https://www.flhouse.gov"
DATA = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "fl"))
AGENT = "statebilltracker.org (a nonprofit bill tracker; contact via github.com/judithhubbard)"
TODAY = date.today()
YEAR = TODAY.year
ONLY = int(sys.argv[1]) if len(sys.argv) > 1 else None
DELAYS = {SENATE: 10.0, HOUSE: 2.0}  # seconds from the end of one answer to the next request (flsenate: Crawl-delay 10)
TIMEOUT = 120  # seconds for a whole request
KEEP = re.compile(r"^(HB|SB|HJR|SJR)$")
REFRESH_MAX = 150  # bills read again per run for being stale (runs are two hours apart on GitHub)
WEEKLY = 7
PDF_PAGES = 3  # pages of an analysis kept
MARKER = os.path.join(DATA, "incomplete")
HAVE_PDFTOTEXT = bool(subprocess.run(["which", "pdftotext"], capture_output=True).stdout.strip())

# The run's own time limit (FETCH_MINUTES, set by the workflow): stop a few minutes early, with everything read so far
# saved and a summary printed, rather than be cut off silently mid-request.
START = time.time()
BUDGET = max(0.0, float(os.environ.get("FETCH_MINUTES") or 0) - 5) * 60
FAILS = Counter()  # why requests failed, for the summary
STATS = Counter()
LAST = {SENATE: 0.0, HOUSE: 0.0}  # when each host's last answer ended


class Refused(Exception):
    """The server turned us away (401/403/429, or a Cloudflare challenge): stop the run."""


GONE = object()  # a 404, or a bill number that "does not exist"


def out_of_time():
    return BUDGET and time.time() - START > BUDGET


def request(site, path, label, must=None, binary=False, tries=3):
    """GET site + path: the body (text, or bytes when binary), GONE for a 404, or None after three tries. must is a
    piece of text (or for binary, the bytes it starts with) the answer has to contain, else it's counted as a failure
    (an error page served as 200)."""
    for attempt in range(tries):
        if out_of_time():
            return None
        wait = LAST[site] + DELAYS[site] - time.time()
        if wait > 0:
            time.sleep(wait)
        STATS["requests"] += 1
        if STATS["requests"] % 100 == 0:
            print(f"  {STATS['requests']} requests, {round((time.time() - START) / 60)} min"
                  + (f"; failures {dict(FAILS)}" if FAILS else ""), flush=True)
        try:
            code, body = curl(site + path)
            LAST[site] = time.time()
            head = body[:4000].decode("utf-8", "replace") if binary else body[:20000]
            if "cf-chl" in head or "<title>Just a moment" in head:
                raise Refused(f"{label}: a Cloudflare challenge page")
            if code in (401, 403, 429):
                FAILS[f"HTTP {code}"] += 1
                raise Refused(f"{label}: HTTP {code}")
            if code == 404:
                FAILS["HTTP 404"] += 1
                return GONE
            if code != 200:
                FAILS[f"HTTP {code}"] += 1
            elif must and not (body.startswith(must) if binary else must in body):
                FAILS["unexpected page"] += 1
            else:
                return body
        except Refused:
            raise
        except Exception as e:
            LAST[site] = time.time()
            FAILS[type(e).__name__] += 1
        if attempt + 1 < tries:
            time.sleep(10 * (attempt + 1))
    print(f"{label}: failed" + (" three times" if tries == 3 else ""), flush=True)
    return None


def curl(url):
    """(HTTP status, body as text, or bytes for a PDF), following redirects (the Senate's committee and senator links
    redirect within the site). With curl, whose -m limits the whole transfer."""
    with tempfile.NamedTemporaryFile(dir=DATA, suffix=".part", delete=False) as tmp:
        part = tmp.name
    try:
        r = subprocess.run(["curl", "-s", "-S", "-L", "--max-redirs", "3", "--compressed", "-m", str(TIMEOUT),
                            "-A", AGENT, "-o", part, "-w", "%{http_code} %{content_type}", url],
                           capture_output=True, text=True, timeout=TIMEOUT + 30)
        if r.returncode:
            raise OSError(f"curl exit {r.returncode}")
        code, _, kind = r.stdout.strip().partition(" ")
        with open(part, "rb") as f:
            body = f.read()
        if "pdf" not in kind.lower() and not body.startswith(b"%PDF"):
            body = body.decode("utf-8", "replace")
        return int(code or 0), body
    finally:
        os.remove(part)


def pdf_text(body, layout=True, pages=None):
    """A PDF's text with pdftotext (poppler-utils), or None."""
    with tempfile.NamedTemporaryFile(dir=DATA, suffix=".pdf", delete=False) as tmp:
        tmp.write(body)
        path = tmp.name
    try:
        args = ["pdftotext", "-enc", "UTF-8"] + (["-layout"] if layout else []) + (["-l", str(pages)] if pages else [])
        r = subprocess.run(args + [path, "-"], capture_output=True, timeout=120)
        return r.stdout.decode("utf-8", "replace") if r.returncode == 0 else None
    except Exception:
        return None
    finally:
        os.remove(path)


def strip(page):
    page = re.sub(r"<script\b.*?</script>|<style\b.*?</style>|<input\b[^>]*>", "", page, flags=re.S)
    # Cloudflare's obfuscated email links: left out, not decoded.
    page = re.sub(r'<a href="/cdn-cgi/l/email-protection[^"]*">.*?</a>', "", page, flags=re.S)
    return "\n".join(line.strip() for line in page.split("\n") if line.strip())


def between(page, start, end):
    a = page.find(start)
    if a < 0:
        return page
    b = page.find(end, a)
    return page[a:b if b > 0 else len(page)]


def text(fragment):
    t = re.sub(r"<br\s*/?>", "\n", fragment)
    t = html.unescape(re.sub(r"<[^>]+>", " ", t)).replace("\xa0", " ")
    return "\n".join(x for x in (re.sub(r"[ \t]+", " ", line).strip() for line in t.split("\n")) if x)


def flat(fragment):
    return re.sub(r"\s+", " ", text(fragment)).strip()


def save_text(body, path):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(body)
    os.replace(tmp, path)


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


def ago(days):
    return (TODAY - timedelta(days=days)).isoformat()


# ---- sessions ----

def years():
    """This year's session and the two before it, newest first, plus next year's from August (prefiled bills)."""
    out = [YEAR, YEAR - 1, YEAR - 2]
    return ([YEAR + 1] if TODAY.month >= 8 else []) + out


def live(year):
    """Bills can still change (the governor's actions, chapter numbers, final analyses): until September 1."""
    return TODAY < date(year, 9, 1)


def in_session(year):
    return date(year, 1, 1) <= TODAY <= date(year, 6, 30)


def begun(year):
    """The session has begun: the marker counts its bills only then (odd years from March, even from January)."""
    return TODAY >= date(year, 3 if year % 2 else 1, 1)


def term_of(year):
    """The first year of the two-year term a session belongs to: 2025 and 2026 -> 2024 (members elected in 2024)."""
    return year - 1 if year % 2 else year - 2


def current_term():
    """The term now serving: a new one from the November election (the sites switched by 2026-11-13)."""
    if YEAR % 2 == 0 and TODAY.month >= 11:
        return YEAR
    return YEAR - 1 if YEAR % 2 else YEAR - 2


def house_term_id(term):
    """The House site's LegislativeTermId: 92 is 2026-2028, 91 is 2024-2026."""
    return 92 + (term - 2026) // 2


# ---- lists and bills ----

def parse_list(page, year):
    out = {}
    for m in re.finditer(rf'<th scope="row"><a href="/Session/Bill/{year}/(\d+)">(.*?)</a></th>\s*<td>(.*?)</td>\s*'
                         r'<td>(.*?)</td>\s*<td>(.*?)</td>', page, re.S):
        label = flat(m.group(2))
        base = re.sub(r"^(?:[A-Z]+/)+", "", label)  # "CS/CS/HB 1205" -> "HB 1205"
        kind = base.split(" ")[0]
        out[label] = {"n": int(m.group(1)), "label": label, "kind": kind, "title": flat(m.group(3)),
                      "by": flat(m.group(4)), "last": re.sub(r"^Last Action:\s*", "", flat(m.group(5)))}
    return out


def lists_due(year, state):
    last = state.get("list_read") or ""
    if not last:
        return True
    if in_session(year):
        return True
    if live(year):
        return last < TODAY.isoformat()
    return last < date(year, 9, 1).isoformat()


def lists(year, folder, state):
    """Both houses' bill lists when due; the last copy otherwise, or when any page fails."""
    path = os.path.join(folder, "list.json")
    last = load(path)
    if last and not lists_due(year, state):
        return last
    rows = {}
    for house in ("senate", "house"):
        n = 1
        while True:
            if out_of_time():
                return last
            page = request(SENATE, f"/Session/Bills/{year}?chamber={house}&PageNumber={n}", f"{year} {house} list {n}",
                           "id=\"billListDiv\"")
            if not isinstance(page, str):
                if last:
                    print(f"{year}: list page unreadable; kept the last copy", flush=True)
                return last
            found = parse_list(page, year)
            rows.update(found)
            if not found or 'class="next"' not in page or n >= 60:
                break
            n += 1
    if not rows:
        print(f"{year}: no bills listed yet", flush=True)
        state["list_read"] = TODAY.isoformat()
        return last
    bills, other = {}, Counter()
    for r in rows.values():
        if KEEP.match(r["kind"]):
            bills[f"{r['kind']}{r['n']}"] = {k: r[k] for k in ("n", "label", "title", "by", "last")}
        else:
            other[r["kind"]] += 1
    out = {"read": TODAY.isoformat(), "bills": bills, "other": dict(other)}
    os.makedirs(os.path.join(folder, "bills"), exist_ok=True)
    save(out, path)
    state["list_read"] = TODAY.isoformat()
    print(f"{year}: {len(bills)} bills and joint resolutions listed (left out: "
          + ", ".join(f"{v} {k}" for k, v in sorted(other.items())) + ")", flush=True)
    return out


def trim_bill(page):
    return strip(between(page, '<div id="breadcrumbs">', '<div id="RelationShipTips"'))


def bill_extras(page):
    """The vote PDFs ([kind, path, label]: floor votes on amendments left out) and the analysis to read."""
    pdfs = []
    votes = between(page, 'id="tabBodyVoteHistory"', 'id="tabBodyCitations"')
    floor_at = votes.find('id="Votes"')
    for m in re.finditer(r"<tr>(.*?)</tr>", votes, re.S):
        link = re.search(r'href="(/Session/Bill/\d+/\d+/Vote/[^"]+)"', m.group(1))
        if not link:
            continue
        kind = "floor" if 0 <= floor_at < m.start() else "committee"
        cells = [flat(c) for c in re.findall(r"<td[^>]*>(.*?)(?=<td|</tr>|$)", m.group(1), re.S)]
        label = " | ".join(c for c in cells if c)
        if kind == "floor" and cells and "Amendment" in cells[0]:
            continue
        pdfs.append([kind, html.unescape(link.group(1)), label])
    found = []
    for m in re.finditer(r"<tr>(.*?)</tr>", between(page, 'id="tabBodyAnalyses"', 'id="tabBodyVoteHistory"'), re.S):
        cells = [flat(c) for c in re.findall(r"<td[^>]*>(.*?)</td>", m.group(1), re.S)]
        link = re.search(r'href="(/Session/Bill/\d+/\d+/Analyses/[^"]+)"', m.group(1))
        if len(cells) >= 4 and link:
            try:
                posted = datetime.strptime(cells[3], "%m/%d/%Y %I:%M %p").isoformat()
            except ValueError:
                posted = ""
            found.append({"path": html.unescape(link.group(1)), "type": cells[0], "author": cells[2],
                          "posted": posted})
    real = [a for a in found if "Message" not in a["type"]] or found
    analysis = max(real, key=lambda a: a["posted"]) if real else None
    return pdfs, analysis


def bills(year, folder, state, listing):
    signal, read, absent = state.setdefault("signal", {}), state.setdefault("read", {}), state.setdefault("absent", {})
    have = lambda k: os.path.exists(os.path.join(folder, "bills", f"{k}.html"))
    wanted = listing["bills"]
    urgent = [k for k, b in wanted.items()
              if (not have(k) and absent.get(k) != b["last"]) or (have(k) and signal.get(k) != b["last"])]
    if live(year):
        stale = ago(WEEKLY)
    else:
        stale = date(year, 9, 1).isoformat()  # a last read after the session's business is over
    rest = sorted((read.get(k, ""), k) for k in wanted if k not in urgent and have(k) and read.get(k, "") < stale)
    todo = urgent + [k for _, k in rest[:REFRESH_MAX]]
    print(f"{year}: {len(wanted)} listed; {len(urgent)} new or moved, {len(rest)} stale; {len(todo)} to read", flush=True)
    got = 0
    for k in todo:
        if out_of_time():
            break
        page = request(SENATE, f"/Session/Bill/{year}/{wanted[k]['n']}", f"{year} {k}", 'id="tabBodyBillHistory"')
        if isinstance(page, str) and "does not exist in the selected session" in page:
            page = GONE
        if page is GONE or page is None:
            if page is GONE:
                absent[k] = wanted[k]["last"]
            continue  # the last copy stays, and it's asked again next run
        save_text(trim_bill(page), os.path.join(folder, "bills", f"{k}.html"))
        signal[k], read[k] = wanted[k]["last"], TODAY.isoformat()
        absent.pop(k, None)
        pdfs, analysis = bill_extras(page)
        state.setdefault("pdfs", {})[k] = pdfs
        if analysis:
            state.setdefault("analysis", {})[k] = analysis
        got += 1
        STATS["bills"] += 1
        if got % 25 == 0:
            save(state, os.path.join(folder, "state.json"))
    print(f"{year} bills: {got} of {len(todo)} read", flush=True)


# ---- votes and analyses ----

def votes(year, folder, state, listing, kind):
    """The bill's vote PDFs of one kind, as text, each once."""
    if not HAVE_PDFTOTEXT:
        return
    done, gone = state.setdefault("pdfs_read", {}), state.setdefault("pdfs_gone", {})
    todo = [(k, p, label) for k in listing["bills"] for kd, p, label in state.get("pdfs", {}).get(k, [])
            if kd == kind and p not in done.get(k, []) and p not in gone.get(k, [])]
    if not todo:
        return
    print(f"{year}: {len(todo)} {kind} votes to read", flush=True)
    os.makedirs(os.path.join(folder, "votes"), exist_ok=True)
    got = 0
    for k, p, label in todo:
        if out_of_time():
            break
        body = request(SENATE, urllib.parse.quote(p, safe="/~"), f"{year} {k} vote", b"%PDF", binary=True)
        if body is GONE:
            gone.setdefault(k, []).append(p)
            continue
        if not isinstance(body, bytes):
            continue
        t = pdf_text(body)
        if t is None:
            FAILS["unreadable PDF"] += 1
            continue
        path = os.path.join(folder, "votes", f"{k}.json")
        out = load(path, {})
        out[p] = {"kind": kind, "label": label, "text": t}
        save(out, path)
        done.setdefault(k, []).append(p)
        got += 1
        STATS["votes"] += 1
        if got % 25 == 0:
            save(state, os.path.join(folder, "state.json"))
    print(f"{year} {kind} votes: {got} of {len(todo)} read", flush=True)


def analyses(year, folder, state, listing):
    """Each bill's chosen analysis: its first pages as text, read again when a newer one is posted."""
    if not HAVE_PDFTOTEXT:
        return
    done = state.setdefault("analysis_read", {})
    todo = [k for k in listing["bills"] if k in state.get("analysis", {})
            and done.get(k) != state["analysis"][k]["path"]]
    if not todo:
        return
    print(f"{year}: {len(todo)} analyses to read", flush=True)
    os.makedirs(os.path.join(folder, "analyses"), exist_ok=True)
    got = 0
    for k in todo:
        if out_of_time():
            break
        a = state["analysis"][k]
        body = request(SENATE, urllib.parse.quote(a["path"], safe="/~"), f"{year} {k} analysis", b"%PDF", binary=True)
        if body is GONE:
            done[k] = a["path"]  # not there: not asked again until another is posted
            continue
        if not isinstance(body, bytes):
            continue
        t = pdf_text(body, layout=False, pages=PDF_PAGES)
        if t is None:
            FAILS["unreadable PDF"] += 1
            continue
        save({**a, "text": t.strip()}, os.path.join(folder, "analyses", f"{k}.json"))
        done[k] = a["path"]
        got += 1
        STATS["analyses"] += 1
        if got % 25 == 0:
            save(state, os.path.join(folder, "state.json"))
    print(f"{year} analyses: {got} of {len(todo)} read", flush=True)


# ---- members ----

def parse_senators(page):
    out = []
    for m in re.finditer(r'<tr class="All[^"]*">\s*<th[^>]*>(.*?)</th>\s*<td[^>]*>(.*?)</td>\s*<td[^>]*>(.*?)</td>\s*'
                         r'<td[^>]*>(.*?)</td>', page, re.S):
        link = re.search(r'class="senatorLink" href="([^"]+)"[^>]*>.*?>([^<]*)</a>', m.group(1), re.S)
        post = re.search(r"<strong>(.*?)</strong>", m.group(1), re.S)
        if not link:
            continue
        out.append({"house": "S", "district": int(flat(m.group(2)) or 0), "name": html.unescape(link.group(2)).strip(),
                    "party": flat(m.group(3)), "counties": flat(m.group(4)), "post": flat(post.group(1)) if post else "",
                    "page": link.group(1)})
    return out


def parse_reps(page):
    out = []
    for box in page.split('<div class="team-box">')[1:]:
        link = re.search(r'details\.aspx\?MemberId=(\d+)&(?:amp;)?LegislativeTermId=(\d+)', box)
        name = re.search(r"<h5>(.*?)</h5>", box, re.S)
        line = re.search(r"<p>\s*([^<&]*?)\s*&mdash;\s*<span[^>]*>\s*District:\s*(\d+)", box)
        counties = re.search(r'<p class="rep-counties"[^>]*>(.*?)</p>', box, re.S)
        ps = re.findall(r"<p>\s*([\d/]+\s*-\s*[\d/]+)\s*</p>", box)
        if not (link and name):
            continue
        out.append({"house": "H", "member_id": int(link.group(1)), "name": flat(name.group(1)),
                    "party": line.group(1).strip() if line else "", "district": int(line.group(2)) if line else None,
                    "counties": flat(counties.group(1)) if counties else "",
                    "dates": re.sub(r"\s+", " ", ps[0]) if ps else ""})
    return out


def parse_senator_page(page):
    side = between(page, 'id="sidebar"', 'class="senator grid-autoRight"')
    offices = {}
    for m in re.finditer(r"<h4>(.*?)</h4>\s*<div[^>]*>(.*?)</div>", side, re.S):
        offices[flat(m.group(1))] = text(m.group(2)).split("\n")
    comms = between(page, "Committee Assignments", 'id="memberPageTabInformation"')
    items = [flat(x) for x in re.findall(r"<li[^>]*>(.*?)</li>", comms, re.S)]
    return {"offices": offices, "phones": re.findall(r"\(\d{3}\) \d{3}-\d{4}", text(side)),
            "committees": [x for x in items if x]}


def parse_rep_contact(page):
    offices = {}
    for m in re.finditer(r"<section aria-label=\"[^\"]*\"\s*class=\"address-block[^\"]*\">\s*<h2[^>]*>(.*?)</h2>(.*?)</section>",
                         page, re.S):
        lines = [flat(x) for x in re.findall(r'<span class="info[^"]*">(.*?)</span>', m.group(2), re.S)]
        offices[flat(m.group(1))] = [x for x in lines if x and x != "Map/Driving Directions"]
    return {"offices": offices}


def member_key(m):
    return f"{m['house']}{m.get('district')}:{m['name']}"


def member_lists(terms):
    """Each term's Senate and House lists: the current term's weekly, past terms' once. Each member's page fields, read
    by member_pages(), carry over from the last copy."""
    folder = os.path.join(DATA, "members")
    os.makedirs(folder, exist_ok=True)
    cur = current_term()
    for term in sorted(terms, reverse=True):
        if out_of_time():
            return
        path = os.path.join(folder, f"{term}.json")
        last = load(path)
        if last and (term != cur or last.get("read", "") >= ago(WEEKLY)):
            continue
        page = request(SENATE, f"/Senators/{term}-{term + 2}", f"{term} senators", "senatorLink")
        senate = parse_senators(page) if isinstance(page, str) else []
        page = request(HOUSE, f"/Sections/Representatives/representatives.aspx?LegislativeTermId={house_term_id(term)}",
                       f"{term} representatives", "team-box")
        house = parse_reps(page) if isinstance(page, str) else []
        if not senate or not house:
            print(f"{term} members: a list unreadable" + ("; kept the last copy" if last else ""), flush=True)
            continue
        before = {member_key(m): m for m in (last or {}).get("senate", []) + (last or {}).get("house", [])}
        for m in senate + house:
            old = before.get(member_key(m), {})
            m.update({k: v for k, v in old.items() if k not in m})
        save({"read": TODAY.isoformat(), "term": f"{term}-{term + 2}", "senate": senate, "house": house}, path)
        print(f"{term}-{term + 2} members: {len(senate)} senators, {len(house)} representatives", flush=True)


def member_pages():
    """The current term's members' pages (offices, phones, the Senate's committee assignments), each weekly, one try
    each (a failure is asked again next run), saved as they're read."""
    path = os.path.join(DATA, "members", f"{current_term()}.json")
    d = load(path)
    if not d:
        return
    todo = [m for m in d["senate"] + d["house"] if m.get("page_read", "") < ago(WEEKLY)]
    if not todo:
        return
    got = 0
    for m in todo:
        if out_of_time():
            break
        if m["house"] == "S":
            n = re.search(r"/S(\d+)", m["page"])
            p = request(SENATE, f"/Senators/S{n.group(1)}", f"senator {m['district']}", "senatorName", tries=1) if n else None
            if isinstance(p, str):
                m.update(parse_senator_page(p))
        else:
            p = request(HOUSE, f"/Sections/Representatives/contactmember.aspx?MemberId={m['member_id']}",
                        f"representative {m['district']}", 'id="contact-member"', tries=1)  # new members: no offices yet
            if isinstance(p, str):
                m.update(parse_rep_contact(p))
                m["phones"] = [x for o in m["offices"].values() for x in o if re.fullmatch(r"\(\d{3}\) \d{3}-\d{4}", x)]
        if isinstance(p, str):
            m["page_read"] = TODAY.isoformat()
            got += 1
            if got % 10 == 0:
                save(d, path)
    save(d, path)
    people = d["senate"] + d["house"]
    print(f"members' pages: {got} of {len(todo)} read; {sum(bool(m.get('page_read')) for m in people)} of {len(people)} "
          f"on file, {sum(bool(m.get('phones')) for m in people)} with phones", flush=True)


# ---- committees ----

def senate_committees():
    path = os.path.join(DATA, "committees", "senate.json")
    last = load(path)
    if last and last.get("read", "") >= ago(WEEKLY):
        return
    page = request(SENATE, "/Committees/", "Senate committees", "/Committees/Show/")
    if not isinstance(page, str):
        return
    codes = []
    for code, name in re.findall(r'href="/Committees/Show/([A-Z0-9]+)/?"[^>]*>(.*?)</a>', page, re.S):
        if code not in [c for c, _ in codes]:
            codes.append((code, flat(name)))
    out = []
    for code, name in codes:
        if out_of_time():
            return
        p = request(SENATE, f"/Committees/Show/{code}/", f"Senate committee {code}", 'id="members"')
        if not isinstance(p, str):
            old = next((c for c in (last or {}).get("committees", []) if c["code"] == code), None)
            if old:
                out.append(old)
            continue
        block = between(p, 'id="members"', '<div class="filter')
        full = re.findall(r'<h2 class="committeeName">(.*?)</h2>', p, re.S)
        mems = []
        for li in re.findall(r"<li[^>]*>(.*?)</li>", block, re.S) or re.findall(r"<a [^>]*/Senators/[^>]*>.*?</a>[^<]*", block, re.S):
            t = flat(li)
            if t:
                link = re.search(r'href="(/Senators/[^"]+)"', li)
                mems.append({"text": t, "page": link.group(1) if link else ""})
        out.append({"code": code, "name": flat(full[-1]) if full else name, "term": flat(full[0]) if full else "",
                    "members": mems, "members_html": strip(block)[:6000]})
    save({"read": TODAY.isoformat(), "committees": out}, path)
    print(f"Senate committees: {len(out)} ({sum(bool(c['members']) for c in out)} with members listed)", flush=True)


def house_committees(term_id, current):
    path = os.path.join(DATA, "committees", f"house_{term_id}.json")
    last = load(path)
    if last and (not current or last.get("read", "") >= ago(WEEKLY)):
        return
    page = request(HOUSE, f"/Sections/Committees/committees.aspx?LegislativeTermId={term_id}", f"House committees {term_id}",
                   "</html>")
    if not isinstance(page, str):
        return
    ids = []
    for cid in re.findall(r'committeesdetail\.aspx\?CommitteeId=(\d+)', page):
        if cid not in ids:
            ids.append(cid)
    out = []
    for cid in ids:
        if out_of_time():
            return
        p = request(HOUSE, f"/Sections/Committees/committeesdetail.aspx?CommitteeId={cid}", f"House committee {cid}",
                    "committee-name")
        if not isinstance(p, str):
            old = next((c for c in (last or {}).get("committees", []) if c["id"] == int(cid)), None)
            if old:
                out.append(old)
            continue
        name = re.search(r'<span class="committee-name"\s*>(.*?)</span>', p, re.S)
        term = re.search(r'<span class="committee-term">(.*?)</span>', p, re.S)

        def cards(part, roles):
            got = []
            for card in part.split('<div class="member-card')[1:]:
                role = re.search(r'<div class="textLargerBold">(.*?)</div>', card, re.S)
                who = re.search(r'details\.aspx\?MemberId=(\d+)"[^>]*>(.*?)</a>', card.split('class="portrait-title">')[-1], re.S)
                dates = re.search(r'<div class="dates">(.*?)</div>', card, re.S)
                if who:
                    got.append({"member_id": int(who.group(1)), "name": flat(who.group(2)),
                                "role": flat(role.group(1)) if roles and role else "",
                                "dates": flat(dates.group(1)) if dates else "",
                                "active": "inactive-membership" not in card.split(">")[0]})
            return got
        lead = between(p, 'class="leadership-section', 'name="representatives"')
        rest = between(p, 'name="representatives"', 'name="committee-docs"')
        out.append({"id": int(cid), "name": flat(name.group(1)) if name else "", "term": flat(term.group(1)) if term else "",
                    "leaders": cards(lead, True), "members": cards(rest, False)})
    save({"read": TODAY.isoformat(), "term_id": term_id, "committees": out}, path)
    print(f"House committees ({term_id}): {len(out)} ({sum(bool(c['leaders']) for c in out)} with leaders)", flush=True)


# ---- the run ----

def never_downloaded(yrs):
    """What was never downloaded: a session's list (once it has begun), a listed bill's page (once the session has
    begun), a term's member lists. (A failed refresh with a last copy doesn't count; nor do votes, analyses and
    committees.)"""
    out = []
    for term in sorted({term_of(y) for y in yrs if begun(y)}):
        m = load(os.path.join(DATA, "members", f"{term}.json"))
        if not m:
            out.append(f"members:{term}")
    for year in yrs:
        if not begun(year):
            continue
        folder = os.path.join(DATA, str(year))
        listing = load(os.path.join(folder, "list.json"))
        if not listing:
            out.append(f"{year}:list")
            continue
        absent = (load(os.path.join(folder, "state.json"), {}) or {}).get("absent", {})
        if any(not os.path.exists(os.path.join(folder, "bills", f"{k}.html")) and k not in absent
               for k in listing["bills"]):
            out.append(f"{year}:bills")
    return out


def main():
    os.makedirs(DATA, exist_ok=True)
    # Before the first copy, a run cut off without its summary leaves this, so a partial copy isn't published.
    if not ONLY and not any(name.isdigit() for name in os.listdir(DATA)):
        with open(MARKER, "w") as f:
            f.write("running\n")
    if not HAVE_PDFTOTEXT:
        print("pdftotext isn't installed: votes and analyses are skipped this run", flush=True)
    yrs = [ONLY] if ONLY else years()
    refused = False
    found = {}
    try:
        if not ONLY:
            member_lists({term_of(y) for y in yrs} | {current_term()})
        for year in yrs:  # the newest first
            if out_of_time():
                break
            folder = os.path.join(DATA, str(year))
            state_path = os.path.join(folder, "state.json")
            state = load(state_path, {})
            listing = lists(year, folder, state)
            if listing is None and not os.path.isdir(folder):
                continue
            os.makedirs(folder, exist_ok=True)
            save(state, state_path)
            if not listing:
                continue
            found[year] = (folder, state, listing)
            bills(year, folder, state, listing)
            save(state, state_path)
        if not ONLY and not out_of_time():
            member_pages()
            os.makedirs(os.path.join(DATA, "committees"), exist_ok=True)
            if not out_of_time():
                senate_committees()
            for tid in sorted({house_term_id(term_of(y)) for y in yrs if y <= YEAR} | {house_term_id(current_term())},
                              reverse=True):
                if not out_of_time():
                    house_committees(tid, tid == house_term_id(current_term()))
        for step in ("floor", "analyses", "committee"):
            for year, (folder, state, listing) in found.items():
                if out_of_time():
                    break
                if step == "analyses":
                    analyses(year, folder, state, listing)
                else:
                    votes(year, folder, state, listing, step)
                save(state, os.path.join(folder, "state.json"))
    except Refused as e:
        print(f"Stopped: the server refused a request ({e})", flush=True)
        refused = True
        for year, (folder, state, listing) in found.items():
            save(state, os.path.join(folder, "state.json"))
    missing = never_downloaded(yrs)
    sizes = []
    for year in yrs:
        folder = os.path.join(DATA, str(year))
        listing = load(os.path.join(folder, "list.json"))
        if listing:
            st = load(os.path.join(folder, "state.json"), {}) or {}
            n_pdfs = sum(len(v) for v in st.get("pdfs", {}).values())
            sizes.append(f"{year} {len(listing['bills'])} listed, {len(st.get('read', {}))} read, "
                         f"{sum(len(v) for v in st.get('pdfs_read', {}).values())} of {n_pdfs} votes, "
                         f"{len(st.get('analysis_read', {}))} of {len(st.get('analysis', {}))} analyses")
    print(f"run: {STATS['requests']} requests ({STATS['bills']} bills, {STATS['votes']} votes, "
          f"{STATS['analyses']} analyses), {round((time.time() - START) / 60)} min"
          + (f"; {'; '.join(sizes)}" if sizes else "")
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
