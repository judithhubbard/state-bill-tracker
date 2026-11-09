#!/usr/bin/env python3
"""Download Nebraska's bills from the Legislature's website (https://nebraskalegislature.gov), plain server-built HTML:
there is no API or bulk file. Its robots.txt (checked 2026-11-09) bars, for all user agents, /trans/search.php,
/bills/search_by_date.php and /bills/search_by_introducer.php, none of which are read, and sets "Crawl-delay: 3": one
request at a time, three seconds apart (counted from the end of the last answer). A 401, 403 or 429 stops the run.

Nebraska's Legislature has one house, 49 senators elected without party labels (officially nonpartisan; no official
page lists a party: the member pages, the roster PDF and the committee pages don't). A Legislature lasts two years:
the 109th is 2025-26 (90 legislative days from January 2025, 60 from January 2026), the 108th 2023-24. Bills of the
first session carry over into the second; numbering runs on (the 109th's LB 1-715 in 2025, LB 716-1262 in 2026).
Bills are "LB"s; an appropriation bill that pays for one is "LB 304A" (the "A bill", passed and signed separately);
resolutions are "LR"s, and a proposed constitutional amendment is an LR with "CA" ("LR 19CA": it goes to the voters,
not the governor). Special sessions (108th First Special Session, 2024) are separate and left out. For the newest two
Legislatures, into data/ne/<first year>/ (2025 is the 109th):
- list.json: {"legislature": 109, "bills": {"LB1": 58014, "LB304A": 65965, "LR19CA": 59458}, (each bill's DocumentID,
  which addresses its page), "nomatch": {key: day} (numbers the search finds nothing for), "worksheets": what the
  worksheets list (below), "referred": {key: [committee number, status]} (the current Legislature's referral lists),
  "listed": day}. The keys come from:
  - the Clerk's worksheets (/FloorDocs/109/PDF/WorkSheet/r1dayfinal.pdf for the first session, r2dayfinal.pdf for the
    second; during a session the latest daily one, r2day30.pdf): every bill and resolution by status ("Approved by
    Governor (160): 60 70 ... 304A ...", "Returned by Governor Without Approval", "Passed Notwithstanding Objections
    of Governor", "Line-item Veto", "Became Law Without Governor's Signature", "Indefinitely Postponed"), with the
    numbers of bills, A bills and CA resolutions introduced. Saved in worksheets/ (the PDFs) and read with pdftotext
    (poppler-utils; without it the A bills are found only through the referral lists, with a note). They are the
    official tally of outcomes for the converter to check against.
  - the referral lists (/bills/search_by_referred.php?Committee=<n>: each standing committee's and the Executive
    Board's bills and resolutions with DocumentID and status), for the current Legislature only (the page ignores
    any other); they save a search per bill.
  - LB numbers from 1 to the worksheets' count (and, while a Legislature is live, past the highest until a number
    isn't found).
  A bill without a DocumentID is looked up with /bills/search_by_number.php?Prefix=LB&Number=7&Suffix=&Legislature=109
  (a GET; the 109th's worksheets list LB 951A, which the search doesn't find: kept in "nomatch"; it answers with a redirect to /bills/view_bill.php?DocumentID=58785, or a list when the number also exists
  in a special session: the special session's page, with "_S1" documents and the s1journal, is set aside).
- bills/<LB7>.html: each bill's page (/bills/view_bill.php?DocumentID=<id>, trimmed to the bill: scripts and the
  "Related Transcripts" list, which names unrelated hearings, left out): title ("LB7 - Change provisions relating to
  ..."), the primary introducer only ("DeKay"; "Executive Board: Hansen, Chairperson"; cosponsors are only in the
  bill text), date of introduction, links to the texts and to the statement of intent, committee statement and fiscal
  note (PDFs, not read: the statement of intent is the closest thing to a plain summary), and the history by date with
  journal pages ("Referred to Agriculture Committee", "Placed on General File with AM77", "Advanced to Enrollment and
  Review Initial", "Placed on Select File", "Passed on Final Reading 47-0-2", "Approved by Governor on April 7, 2025",
  "Indefinitely postponed"; amendments filed and adopted with their sponsors), each recorded vote linked by its KeyID.
- votes/<KeyID>.json: each recorded vote (/bills/view_votes.php?KeyID=<n>) member by member: {"key", "bill", "stage"
  ("General File", "Select File", "Final Reading"), "date", "motion" ("AM 835 Appropriations AM 1245 Raybould",
  "ADVANCE TO E&R INITIAL", "" for final passage), "totals": {"Yes", "No", "Present Not Voting", "Absent Not Voting",
  "Excused Not Voting"}, "members": [["Cavanaugh, J.", "Yes"], ...], "short": true when the list doesn't add up to the
  totals}. Names are surnames, with an initial where two senators share one. Votes don't change: each is read once.
  Committee votes are only in the committee statements (PDFs).
- state.json: when each bill was read ("read") and its page's fingerprint ("sigs"), each bill's vote KeyIDs ("votes"),
  the referral statuses it was read under ("status"), worksheet days found, and "finished" once a Legislature is over
  and fully read.
And into data/ne/members/ (read weekly): members.json, the current senators (/senators/senator_list.php, then each
district's page /senators/landing-pages/index.php?District=<n>: name, district, SenatorID (the "Introducer" id in
bill pages), Capitol room, phone, email, committees, photo, and the Speaker); committees.json, the 14 standing
committees (/committees/landing_pages/index.php?cid=<n>: members by SenatorID, "Chairperson", "Vice Chairperson",
when and where they meet) and the select and special committees (/committees/select-committees.php: Executive Board,
Rules, Committee on Committees and others, members by district). Former senators' pages are empty, so past
Legislatures' members are known only by name, from the votes.

What's read again: while a Legislature is live (until August 1 of its second year), its worksheets and referral lists
every run during a session (January to mid-June) and weekly otherwise; its bills once a day during a session and
weekly otherwise, stalest first, at most REFRESH_MAX a run, and at once when the referral list shows a new status.
After that, each bill is read once more and the Legislature is finished. A first copy of two Legislatures (about
2,800 bills, A bills and CA resolutions; the 109th's DocumentIDs mostly from the referral lists, the 108th's each by a
search; then about 4,000 votes, 1,109 for the first 779 bills of the 109th) is about 8,500 requests at about 3.3
seconds each: about 8 hours, built up over several runs (each run saves as it goes and starts where the last stopped). A run between sessions takes a minute or two (weekly: about
65 requests for members and committees, plus the bills' weekly reread of a live Legislature); during a session, the
day's changed bills and their new votes.

Not downloaded: bill texts, amendments, the statement of intent, committee statements and fiscal notes (PDFs),
cosponsors (in the bill texts), transcripts, special sessions, resolutions other than constitutional amendments.

data/ne/incomplete says "running" during the first copy, then lists what was never downloaded (a Legislature's list,
a listed bill's page, the members); it is removed when nothing is missing. Votes, worksheets and committees fill in
on later runs and don't hold the state back. A request that fails where a last copy exists keeps that copy and
doesn't count.
Usage: python3 states/ne/fetch.py [first year]   (default: the newest two Legislatures; one leaves the marker alone)
"""
import gzip, hashlib, html, json, os, re, shutil, subprocess, sys, tempfile, time, urllib.error, urllib.request
from collections import Counter
from datetime import date, timedelta

SITE = "https://nebraskalegislature.gov"
DATA = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "ne"))
AGENT = "statebilltracker.org (a nonprofit bill tracker; contact via github.com/judithhubbard)"
TODAY = date.today()
ONLY = int(sys.argv[1]) if len(sys.argv) > 1 else None
DELAY = 3.0  # robots.txt's Crawl-delay, counted from the end of the last answer
REFRESH_MAX = 250  # bills read again per run for being stale (runs are two hours apart on GitHub)
WEEKLY = 7
STANDING = range(1, 15)  # the standing committees' numbers (cid, and Committee= in the referral lists)
REFERRAL_LISTS = list(STANDING) + [21]  # 21: the Executive Board (it refers bills, and is referred some)
MEMBERS = os.path.join(DATA, "members")
MARKER = os.path.join(DATA, "incomplete")
PDFTOTEXT = shutil.which("pdftotext")

# The run's own time limit (FETCH_MINUTES, set by the workflow): stop a few minutes early, with everything read so far
# saved and a summary printed, rather than be cut off silently mid-request.
START = time.time()
BUDGET = max(0.0, float(os.environ.get("FETCH_MINUTES") or 0) - 5) * 60
FAILS = Counter()  # why requests failed, for the summary
STATS = {"requests": 0, "searches": 0, "bills": 0, "votes": 0}
LAST = [0.0]  # when the last answer ended


class Refused(Exception):
    """The server turned us away (401/403/429): stop the run."""


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


OPENER = urllib.request.build_opener(NoRedirect)


def out_of_time():
    return BUDGET and time.time() - START > BUDGET


def request(path, label, must=None, binary=False, redirect=False):
    """GET SITE+path: the page as text (bytes if binary); None after three tries, or at once for a 404. With redirect,
    a 3xx answer returns ("redirect", Location). must is text the page has to contain (else it's counted as a failure:
    an error page served as 200)."""
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
        try:
            req = urllib.request.Request(SITE + path, headers={"User-Agent": AGENT, "Accept-Encoding": "gzip"})
            with OPENER.open(req, timeout=90) as r:
                body = r.read()
                if r.headers.get("Content-Encoding") == "gzip":
                    body = gzip.decompress(body)
            LAST[0] = time.time()
            if binary:
                return body
            page = body.decode("utf-8", "replace")
            if must and must not in page:
                FAILS["unexpected page"] += 1
            else:
                return page
        except urllib.error.HTTPError as e:
            LAST[0] = time.time()
            if redirect and e.code in (301, 302, 303, 307):
                return ("redirect", e.headers.get("Location") or "")
            FAILS[f"HTTP {e.code}"] += 1
            if e.code in (401, 403, 429):
                raise Refused(f"{label}: HTTP {e.code}")
            if e.code == 404:
                return None
        except Exception as e:
            LAST[0] = time.time()
            FAILS[type(e).__name__] += 1
        time.sleep(10 * (attempt + 1))
    print(f"{label}: failed three times", flush=True)
    return None


def save(obj, path):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False)
    os.replace(tmp, path)


def save_text(body, path):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(body)
    os.replace(tmp, path)


def load(path, default=None):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def text(fragment):
    """Plain text of an HTML fragment, whitespace collapsed."""
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", fragment))).strip()


def stale(day, days):
    return not day or day < (TODAY - timedelta(days=days)).isoformat()


def number_of(year):
    """The Legislature meeting in a year: 2025 and 2026 -> 109."""
    return 109 + (year - 2025) // 2


def first_year(legislature):
    return 2025 + 2 * (legislature - 109)


def live(year):
    """A Legislature (by first year) changes until August 1 of its second year."""
    return TODAY < date(year + 1, 8, 1)


def in_session():
    """Nebraska's sessions run from early January to April (even years) or early June (odd years)."""
    return date(TODAY.year, 1, 1) <= TODAY <= date(TODAY.year, 6, 15)


def sort_key(key):
    m = re.match(r"(L[BR])(\d+)(\w*)", key)
    return (m.group(1), int(m.group(2)), m.group(3)) if m else (key, 0, "")


# ---- worksheets: the Clerk's status list, for the A bills, the CA resolutions and the counts ----

def pdf_text(body):
    if not PDFTOTEXT:
        return None
    with tempfile.NamedTemporaryFile(suffix=".pdf") as f:
        f.write(body)
        f.flush()
        try:
            out = subprocess.run([PDFTOTEXT, "-layout", f.name, "-"], capture_output=True, timeout=120)
        except (OSError, subprocess.SubprocessError):
            return None
    return out.stdout.decode("utf-8", "replace") if out.returncode == 0 else None


def read_worksheet(body):
    """What a worksheet lists: {"a": ["304A"], "ca": ["LR19CA"], "lb": highest LB number introduced, "a_count",
    "ca_count"} (counts as the worksheet states them), or None without pdftotext."""
    t = pdf_text(body)
    if t is None:
        return None
    a = sorted({m + "A" for m in re.findall(r"(?<![\w.])(\d{1,4})Ae?(?![\w])", t)}, key=lambda k: int(k[:-1]))
    ca = sorted({f"LR{m}CA" for m in re.findall(r"\bLR\s?(\d+)CA\b", t)}, key=lambda k: int(k[2:-2]))
    lb = [int(n) for n in re.findall(r"Number of Bills Introduced \(excluding A Bills\)[^:\n]*:\s*(\d+)", t, re.I)]
    lb += [int(n) for n in re.findall(r"BILLS INTRODUCED \(excluding A Bills\):\s*First Session:\s*(\d+)", t, re.I)]
    lb += [int(n) for n in re.findall(r"BILLS INTRODUCED \(excluding A Bills\):[^\n]*?Total:\s*(\d+)", t, re.I)]
    a_count = re.search(r"Number of .A. Bills Introduced[^:\n]*:\s*(\d+)|A Bills \((\d+)\)", t)
    ca_count = re.search(r"Number of CA Resolutions Introduced[^:\n]*:\s*(\d+)", t)
    return {"a": a, "ca": ca, "lb": max(lb) if lb else None,
            "a_count": int(next(g for g in a_count.groups() if g)) if a_count else None,
            "ca_count": int(ca_count.group(1)) if ca_count else None}


def last_day(year, leg, name, lo, cap):
    """The newest daily worksheet of a session (r2day59.pdf) after day lo (0: none known): (day, PDF), or (lo, None)
    when there's no newer one. Days run on without gaps, so doubling the step, then halving it, takes a few
    requests."""
    got = {}

    def fetch(day):
        if day not in got:
            body = request(f"/FloorDocs/{leg}/PDF/WorkSheet/{name}day{day}.pdf", f"{year} {name} day {day}", binary=True)
            got[day] = body if body and body.startswith(b"%PDF") else None
        return got[day]

    start, step, hi = lo, 1, None
    while hi is None and lo < cap and not out_of_time():
        if fetch(min(lo + step, cap)):
            lo, step = min(lo + step, cap), step * 2
        else:
            hi = min(lo + step, cap)
    while hi is not None and hi - lo > 1 and not out_of_time():
        mid = (lo + hi) // 2
        lo, hi = (mid, hi) if fetch(mid) else (lo, mid)
    return (lo, got.get(lo)) if lo > start else (start, None)


def worksheets(year, folder, listing, state):
    """Each session's final worksheet once it exists, and a daily one: the latest during the session, the last day's
    after it (the final worksheet lists outcomes; the daily ones also list every A bill of the session)."""
    leg = listing["legislature"]
    found = listing.setdefault("worksheets", {})
    days = state.setdefault("worksheet_days", {})
    os.makedirs(os.path.join(folder, "worksheets"), exist_ok=True)

    def keep(entry, file, body, final):
        with open(os.path.join(folder, "worksheets", f"{entry}.pdf"), "wb") as f:
            f.write(body)
        info = read_worksheet(body)
        found[entry] = {"file": file, "final": final, **(info or {"unread": True})}
        print(f"{year} worksheet {file}: " + (f"{len(info['a'])} A bills, {len(info['ca'])} CA resolutions, LB to "
              f"{info['lb']}" if info else "saved, not read (no pdftotext)"), flush=True)

    for entry, w in list(found.items()):  # read now if pdftotext wasn't there before
        if w.get("unread") and PDFTOTEXT and os.path.exists(os.path.join(folder, "worksheets", f"{entry}.pdf")):
            with open(os.path.join(folder, "worksheets", f"{entry}.pdf"), "rb") as f:
                info = read_worksheet(f.read())
            if info:
                found[entry] = {"file": w["file"], "final": w["final"], **info}
    for n, sy in ((1, year), (2, year + 1)):
        name = f"r{n}"
        if TODAY < date(sy, 1, 5) or out_of_time():
            continue
        if not (found.get(name) or {}).get("final") and TODAY >= date(sy, 4, 1):
            body = request(f"/FloorDocs/{leg}/PDF/WorkSheet/{name}dayfinal.pdf", f"{year} {name} final worksheet",
                           binary=True)
            if body and body.startswith(b"%PDF"):
                keep(name, f"{name}dayfinal", body, True)
        daily = found.get(name + "daily") or {}
        over = (found.get(name) or {}).get("final")
        if (TODAY.year == sy and in_session() and not over) or (over and not daily.get("last")):
            cap = 90 if sy % 2 else 60  # legislative days in a long and a short session
            day, body = last_day(year, leg, name, days.get(name, 0), cap)
            if body:
                days[name] = day
                keep(name + "daily", f"{name}day{day}", body, False)
            if over:
                found.setdefault(name + "daily", {"file": None, "final": False})["last"] = True


# ---- the referral lists (current Legislature only) ----

ROW = re.compile(r'view_bill\.php\?DocumentID=(\d+)"[^>]*>\s*(L[BR]\d+[A-Z]*)\s*</a>(.*?)</tr>', re.S)


def referrals(year, listing):
    leg = listing["legislature"]
    got = {}
    for n in REFERRAL_LISTS:
        page = request(f"/bills/search_by_referred.php?Committee={n}", f"{year} referrals {n}", "Bill Search Matches")
        if page is None:
            return False
        head = re.search(r"Referred To (.*?) in the (\d+)\w\w Legislature", page)
        if not head or int(head.group(2)) != leg:
            print(f"{year} referrals: the lists are for another Legislature; skipped", flush=True)
            return False
        for doc, key, rest in ROW.findall(page):
            cells = re.findall(r"<td[^>]*>(.*?)</td>", rest, re.S)
            status = text(cells[1]) if len(cells) > 1 else ""
            if key.startswith("LB") or key.endswith("CA"):
                got[key] = [n, status, int(doc)]
    if not got:
        return False
    listing["referred"] = {k: v[:2] for k, v in got.items()}
    for k, v in got.items():
        listing["bills"].setdefault(k, v[2])
    print(f"{year} referrals: {len(got)} bills and CA resolutions", flush=True)
    return True


# ---- finding each bill's DocumentID ----

def special(page):
    """A special session's bill page (its documents end "_S1", its journal is s1journal)."""
    return bool(re.search(r"_S\d\.pdf|Journal/s\d+journal", page))


def search(year, listing, key):
    """The DocumentID for a key: an int, None when nothing is found, a list of candidates when the number exists in a
    special session too, or False when the request failed."""
    m = re.fullmatch(r"(L[BR])(\d+)(A|CA)?", key)
    got = request(f"/bills/search_by_number.php?Prefix={m.group(1)}&Number={m.group(2)}&Suffix={m.group(3) or ''}"
                  f"&Legislature={listing['legislature']}", f"{year} search {key}", redirect=True)
    STATS["searches"] += 1
    if got is None:
        return False
    if isinstance(got, tuple):
        doc = re.search(r"DocumentID=(\d+)", got[1])
        return int(doc.group(1)) if doc else False
    if "Bill Search Matches" not in got:
        FAILS["unexpected page"] += 1
        return False
    ids = [int(d) for d, k, _ in ROW.findall(got) if k == key]
    return None if not ids else ids[0] if len(ids) == 1 else ids


def wanted(listing):
    """Every key the Legislature has, as far as known: LB 1 to the highest number, A bills and CA resolutions from
    the worksheets and referral lists."""
    keys = set(listing["bills"]) | set(listing.get("candidates", {}))
    top = max([w.get("lb") or 0 for w in listing.get("worksheets", {}).values()]
              + [int(k[2:]) for k in keys if re.fullmatch(r"LB\d+", k)] + [0])
    keys |= {f"LB{n}" for n in range(1, top + 1)}
    for w in listing.get("worksheets", {}).values():
        keys |= {f"LB{a}" for a in w.get("a", [])} | set(w.get("ca", []))
    return keys


def resolve(year, listing):
    """Look up every wanted key without a DocumentID; while live, also the numbers past the highest LB until one isn't
    found."""
    nomatch = listing.setdefault("nomatch", {})
    cands = listing.setdefault("candidates", {})
    retry = WEEKLY if live(year) else 10 ** 5
    todo = sorted((k for k in wanted(listing) if k not in listing["bills"] and k not in cands
                   and stale(nomatch.get(k), retry)), key=sort_key)
    found = 0
    for key in todo:
        if out_of_time():
            break
        got = search(year, listing, key)
        if got is False:
            continue
        if got is None:
            nomatch[key] = TODAY.isoformat()
        elif isinstance(got, list):
            cands[key] = got
        else:
            listing["bills"][key] = got
            nomatch.pop(key, None)
            found += 1
        if found and found % 50 == 0:
            save(listing, os.path.join(DATA, str(year), "list.json"))
    # Past the highest known LB (new bills during a session; a list without a worksheet count).
    no_worksheet_count = not any(w.get("lb") for w in listing.get("worksheets", {}).values())
    if live(year) or (no_worksheet_count and not listing.get("probed_top")):
        misses, n = 0, max([int(k[2:]) for k in wanted(listing) if re.fullmatch(r"LB\d+", k)] + [0])
        while misses < (1 if live(year) and not no_worksheet_count else 3) and not out_of_time():
            n += 1
            key = f"LB{n}"
            if key in listing["bills"]:
                continue
            got = search(year, listing, key)
            if got is False:
                break
            if got is None:
                misses += 1
                nomatch[key] = TODAY.isoformat()
            else:
                misses = 0
                if isinstance(got, list):
                    cands[key] = got
                else:
                    listing["bills"][key] = got
        if misses and not live(year):
            listing["probed_top"] = TODAY.isoformat()
    print(f"{year}: {len(listing['bills'])} bills with a DocumentID, {len(cands)} to tell from a special session's, "
          f"{sum(1 for k in nomatch if k in wanted(listing))} numbers not found", flush=True)


# ---- bill pages ----

def trim(page):
    """The bill's part of its page: from the title to the amendments, without scripts or the transcripts list."""
    i = page.find("<h2>L")
    j = page.find("Related Videos", i)
    part = page[i:j if j > 0 else None]
    part = re.sub(r"<script\b.*?</script>|<style\b.*?</style>|<noscript>.*?</noscript>", "", part, flags=re.S)
    return re.sub(r"\n\s*\n+", "\n", re.sub(r"[ \t]+\n", "\n", part))


def bill_page(year, key, doc):
    """The trimmed page for a DocumentID, or None."""
    page = request(f"/bills/view_bill.php?DocumentID={doc}", f"{year} {key}")
    if page is None:
        return None
    if not re.search(r"<h2>\s*" + re.escape(key) + r"\b", page):
        FAILS["not the bill's page"] += 1
        print(f"{year} {key}: DocumentID {doc} isn't its page", flush=True)
        return None
    STATS["bills"] += 1
    return page


def store_bill(folder, state, key, page):
    part = trim(page)
    save_text(part, os.path.join(folder, "bills", f"{key}.html"))
    state["read"][key] = TODAY.isoformat()
    state["sigs"][key] = hashlib.sha1(part.encode()).hexdigest()[:16]
    state["votes"][key] = sorted({int(k) for k in re.findall(r"view_votes\.php\?KeyID=(\d+)", part)})


def bills(year, folder, listing, state):
    """Pages never read first (and the candidates of numbers shared with a special session), then those whose
    referral status changed, then, while live, the stalest, at most REFRESH_MAX; once the Legislature is over, every
    page once more after it."""
    os.makedirs(os.path.join(folder, "bills"), exist_ok=True)
    for key in ("read", "sigs", "votes", "status"):
        state.setdefault(key, {})
    cands = listing.get("candidates", {})
    for key in sorted(cands, key=sort_key):
        if out_of_time():
            return
        for doc in sorted(cands[key]):
            page = bill_page(year, key, doc)
            if page and not special(trim(page)):
                listing["bills"][key] = doc
                store_bill(folder, state, key, page)
                break
        if key in listing["bills"]:
            del cands[key]
    have = lambda k: os.path.exists(os.path.join(folder, "bills", f"{k}.html"))
    keys = sorted(listing["bills"], key=sort_key)
    new = [k for k in keys if not have(k)]
    referred = listing.get("referred", {})
    moved = [k for k in keys if have(k) and k in referred and state["status"].get(k) not in (None, referred[k][1])]
    end = date(year + 1, 8, 1).isoformat()
    if live(year):
        days = 1 if in_session() else WEEKLY
        old = sorted((k for k in keys if have(k) and k not in moved and stale(state["read"].get(k), days)),
                     key=lambda k: state["read"].get(k, ""))[:REFRESH_MAX]
    else:
        old = sorted((k for k in keys if have(k) and state["read"].get(k, "") < end), key=lambda k: state["read"].get(k, ""))
    for i, key in enumerate(new + moved + old):
        if out_of_time():
            break
        page = bill_page(year, key, listing["bills"][key])
        if page is None:
            continue
        store_bill(folder, state, key, page)
        if key in referred:
            state["status"][key] = referred[key][1]
        if i % 50 == 49:
            save(state, os.path.join(folder, "state.json"))
    for key in keys:  # statuses first seen with a page read before
        if key in referred and key not in state["status"] and have(key):
            state["status"][key] = referred[key][1]
    print(f"{year} bills: {len(new)} new, {len(moved)} with a new status, {len(old)} stale; "
          f"{sum(1 for k in keys if have(k))} of {len(keys)} pages", flush=True)


# ---- votes ----

def parse_vote(page, key_id):
    def field(label):
        m = re.search(r"<b>" + re.escape(label) + r":</b>\s*</span>\s*<span[^>]*>(.*?)</span>", page, re.S)
        return text(m.group(1)) if m else ""
    totals = {}
    for label in ("Yes", "No", "Present Not Voting", "Absent Not Voting", "Excused Not Voting"):
        m = re.search(r"<b>" + label + r":</b>\s*(\d+)", page)
        totals[label] = int(m.group(1)) if m else None
    bill = re.search(r"<h2>\s*(L[BR]\d+[A-Z]*)\b", page) or re.search(r">\s*(L[BR]\d+[A-Z]*) - ", page)
    members = []
    i = page.find("Individual Votes")
    if i >= 0:
        cells = re.findall(r'<div class="col py-1( text-end)?[^"]*">(.*?)</div>', page[i:], re.S)
        name = None
        for vote_cell, content in cells:
            if vote_cell:
                if name:
                    members.append([name, text(content)])
                name = None
            else:
                name = text(content) or None
    out = {"key": key_id, "bill": bill.group(1) if bill else None, "stage": field("Stage"),
           "date": field("Date of Vote"), "motion": field("Motion/Amendment"), "totals": totals, "members": members}
    if None not in totals.values() and len(members) != sum(totals.values()):
        out["short"] = True
    return out


def votes(year, folder, state):
    """Each vote a bill page links to, once."""
    os.makedirs(os.path.join(folder, "votes"), exist_ok=True)
    bill_of = {v: k for k, keys in state.get("votes", {}).items() for v in keys}
    todo = sorted(v for v in bill_of if not os.path.exists(os.path.join(folder, "votes", f"{v}.json")))
    got = 0
    for key_id in todo:
        if out_of_time():
            break
        page = request(f"/bills/view_votes.php?KeyID={key_id}", f"{year} vote {key_id}", "Individual Votes")
        if page is None:
            continue
        vote = parse_vote(page, key_id)
        vote["bill"] = vote["bill"] or bill_of[key_id]
        if not vote["members"]:
            FAILS["vote without members"] += 1
            continue
        save(vote, os.path.join(folder, "votes", f"{key_id}.json"))
        STATS["votes"] += 1
        got += 1
    print(f"{year} votes: {got} of {len(todo)} read", flush=True)
    return got == len(todo)


# ---- members and committees ----

def member_page(page, district):
    out = {"district": district}
    name = re.search(r"<h1>\s*Sen\.\s*(.*?)\s*</h1>", page)
    out["name"] = text(name.group(1)) if name else ""
    sid = re.search(r"SenatorID=(\d+)", page) or re.search(r"Introducer=(\d+)", page)
    out["senator_id"] = int(sid.group(1)) if sid else None
    addr = re.search(r'<address class="feature-content">(.*?)</address>', page, re.S)
    if addr:
        lines = [text(x) for x in re.split(r"<br\s*/?>", addr.group(1))]
        lines = [x for x in lines if x]
        out["room"] = next((x for x in lines if x.startswith("Room")), None)
        out["phone"] = next((x for x in lines if re.fullmatch(r"\(\d{3}\) \d{3}-\d{4}", x)), None)
        out["address"] = [x for x in lines if not x.startswith("Email") and x != out["phone"]]
    email = re.search(r'href="mailto:([^"]+)"', page)
    out["email"] = email.group(1).strip() if email else None
    box = page.find("Committee Assignments")
    if box >= 0:
        end = page.find("</ul>", box)
        out["committees"] = [text(c) for c in re.findall(r"<li>(.*?)</li>", page[box:end], re.S)]
    photo = re.search(r'id="sen-image"[^>]*src="([^"]+)"', page)
    out["photo"] = photo.group(1) if photo else None
    return out


def members():
    """The current senators, weekly. False when they couldn't be read."""
    os.makedirs(MEMBERS, exist_ok=True)
    path = os.path.join(MEMBERS, "members.json")
    old = load(path, {})
    if old and not stale(old.get("read"), WEEKLY):
        return True
    page = request("/senators/senator_list.php", "senator list", "landing-pages/index.php?District=")
    if page is None:
        return False
    districts = sorted({int(d) for d in re.findall(r"landing-pages/index\.php\?District=(\d+)\"", page)})
    speaker = re.search(r"District=(\d+)&(?:amp;)?Speaker=true", page)
    found, failed = [], 0
    for d in districts:
        if out_of_time():
            return os.path.exists(path)
        p = request(f"/senators/landing-pages/index.php?District={d}", f"senator {d}", "feature-content")
        info = member_page(p, d) if p else None
        if not info or not info["name"]:
            failed += 1
            prior = next((m for m in old.get("members", []) if m.get("district") == d), None)
            if prior:
                found.append({**prior, "kept": True})
            continue
        info["speaker"] = bool(speaker and int(speaker.group(1)) == d)
        found.append(info)
    if not found:
        return os.path.exists(path)
    save({"read": TODAY.isoformat(), "members": found}, path)
    print(f"members: {len(found)} senators ({failed} pages failed)", flush=True)
    return True


def committees():
    """The standing, select and special committees with their members, weekly."""
    path = os.path.join(MEMBERS, "committees.json")
    old = load(path, {})
    if old and not stale(old.get("read"), WEEKLY):
        return
    out = []
    for cid in STANDING:
        if out_of_time():
            return
        page = request(f"/committees/landing_pages/index.php?cid={cid}", f"committee {cid}", "Committee Members")
        if page is None:
            prior = next((c for c in old.get("committees", []) if c.get("cid") == cid), None)
            if prior:
                out.append(prior)
            continue
        name = re.search(r'<div class="card-header leg-header">\s*<h1>(.*?)</h1>', page, re.S)
        box = page.find("Committee Members")
        rows = re.findall(r'SenatorID=(\d+)">(.*?)</a>', page[box:page.find("</ul>", box)], re.S)
        people = []
        for sid, label in rows:
            label = text(label)
            role = re.search(r",\s*((?:Vice )?Chairperson)$", label)
            people.append({"senator_id": int(sid), "name": re.sub(r"^Sen\.\s*|,\s*(Vice )?Chairperson$", "", label),
                           "role": role.group(1) if role else ""})
        meets = re.search(r"<p>(During session, .*?)</p>", page, re.S)
        out.append({"cid": cid, "kind": "standing", "name": text(name.group(1)) if name else "",
                    "members": people, "meets": text(meets.group(1)) if meets else ""})
    page = request("/committees/select-committees.php", "select committees", "Select committees")
    if page:
        kind = "select"
        for part in re.split(r'(?=<div class="card-header leg-header" role="tab")|(?=Special committees)', page):
            if part.startswith("Special committees"):
                kind = "special"
                continue
            head = re.search(r'id="reportheading(\d+)".*?</i>\s*([^<]+)</a>', part, re.S)
            if not head:
                continue
            people = []
            for d, label, extra in re.findall(r'District=(\d+)"><i[^>]*></i>\s*([^<]*)(<small>.*?</small>)?</a>', part, re.S):
                label = text(label)
                role = re.search(r",\s*((?:Vice )?Chairperson)$", label)
                people.append({"district": int(d), "name": re.sub(r"^Sen\.\s*|,\s*(Vice )?Chairperson$", "", label),
                               "role": role.group(1) if role else ("Ex Officio" if "Ex Officio" in extra else "")})
            out.append({"cid": int(head.group(1)), "kind": kind, "name": text(head.group(2)), "members": people})
    elif old:
        out += [c for c in old.get("committees", []) if c.get("kind") != "standing"]
    if out:
        save({"read": TODAY.isoformat(), "committees": out}, path)
        print(f"committees: {sum(c['kind'] == 'standing' for c in out)} standing, "
              f"{sum(c['kind'] != 'standing' for c in out)} select and special", flush=True)


# ---- the run ----

def years():
    """The newest two Legislatures, by first year (the next one from the January it meets)."""
    cur = first_year(number_of(TODAY.year))
    return [cur, cur - 2]


def finished(year, folder, listing, state):
    """Over and fully read: every wanted key resolved (or not found), every page read after the Legislature ended,
    every vote read, a final worksheet for each session."""
    if live(year):
        return False
    end = date(year + 1, 8, 1).isoformat()
    keys = wanted(listing)
    nomatch = listing.get("nomatch", {})
    if any(k not in listing["bills"] and k not in nomatch for k in keys) or listing.get("candidates"):
        return False
    if any(state.get("read", {}).get(k, "") < end for k in listing["bills"]):
        return False
    if any(not os.path.exists(os.path.join(folder, "votes", f"{v}.json"))
           for ks in state.get("votes", {}).values() for v in ks):
        return False
    ws = listing.get("worksheets", {})
    return all((ws.get(n) or {}).get("final") for n in ("r1", "r2"))


def never_downloaded(yrs):
    """What was never downloaded: a Legislature's list, a listed bill's page (or a number never looked up), the
    members. (A failed refresh with a last copy doesn't count.)"""
    out = []
    for year in yrs:
        if TODAY < date(year, 1, 5):
            continue
        folder = os.path.join(DATA, str(year))
        listing = load(os.path.join(folder, "list.json"))
        if not listing or not listing.get("bills"):
            out.append(f"{year}:list")
            continue
        nomatch = listing.get("nomatch", {})
        if any(k not in listing["bills"] and k not in nomatch for k in wanted(listing)) \
                or any(not os.path.exists(os.path.join(folder, "bills", f"{k}.html")) for k in listing["bills"]):
            out.append(f"{year}:bills")
    if not os.path.exists(os.path.join(MEMBERS, "members.json")):
        out.append("members")
    return out


def main():
    os.makedirs(DATA, exist_ok=True)
    # Before the first copy, a run cut off without its summary leaves this, so a partial copy isn't published.
    if not ONLY and not any(name.isdigit() for name in os.listdir(DATA)):
        with open(MARKER, "w") as f:
            f.write("running\n")
    if not PDFTOTEXT:
        print("pdftotext isn't installed (poppler-utils): worksheets are saved but not read", flush=True)
    yrs = [ONLY] if ONLY else years()
    refused = False
    found = {}
    try:
        if not ONLY:
            members()
            if not out_of_time():
                committees()
        for year in yrs:
            if out_of_time():
                break
            if TODAY < date(year, 1, 5):
                continue
            folder = os.path.join(DATA, str(year))
            os.makedirs(folder, exist_ok=True)
            list_path, state_path = os.path.join(folder, "list.json"), os.path.join(folder, "state.json")
            state = load(state_path, {})
            if state.get("finished"):
                print(f"{year}: finished and fully read; nothing to do", flush=True)
                continue
            listing = load(list_path) or {"legislature": number_of(year), "bills": {}}
            found[year] = (folder, state, listing)
            ws = listing.get("worksheets", {})
            settled = all((ws.get(n) or {}).get("final") and (ws.get(n + "daily") or {}).get("last") for n in ("r1", "r2"))
            if live(year):
                due = in_session() or stale(listing.get("listed"), WEEKLY)
            else:  # once after it's over, and weekly until both sessions' final worksheets are in
                due = listing.get("listed", "") < date(year + 1, 8, 1).isoformat() or (
                    not settled and stale(listing.get("listed"), WEEKLY))
            if due:
                worksheets(year, folder, listing, state)
                if number_of(TODAY.year) == listing["legislature"] and not out_of_time():
                    referrals(year, listing)
                if not out_of_time():
                    listing["listed"] = TODAY.isoformat()
                save(listing, list_path)
                save(state, state_path)
            resolve(year, listing)
            save(listing, list_path)
            bills(year, folder, listing, state)
            save(listing, list_path)
            save(state, state_path)
        for year, (folder, state, listing) in found.items():
            if out_of_time():
                break
            votes(year, folder, state)
            if not out_of_time() and finished(year, folder, listing, state):
                state["finished"] = True
                print(f"{year}: finished", flush=True)
            save(state, os.path.join(folder, "state.json"))
    except Refused as e:
        print(f"Stopped: the server refused a request ({e})", flush=True)
        refused = True
    for year, (folder, state, listing) in found.items():
        save(listing, os.path.join(folder, "list.json"))
        save(state, os.path.join(folder, "state.json"))
    missing = never_downloaded(yrs)
    sizes = []
    for year in yrs:
        folder = os.path.join(DATA, str(year))
        listing = load(os.path.join(folder, "list.json")) or {}
        if listing.get("bills"):
            pages = sum(1 for k in listing["bills"] if os.path.exists(os.path.join(folder, "bills", f"{k}.html")))
            nvotes = len(os.listdir(os.path.join(folder, "votes"))) if os.path.isdir(os.path.join(folder, "votes")) else 0
            sizes.append(f"{year} {pages} of {len(listing['bills'])} bill pages, {nvotes} votes")
    print(f"run: {STATS['requests']} requests ({STATS['searches']} searches, {STATS['bills']} bills, "
          f"{STATS['votes']} votes), {round((time.time() - START) / 60, 1)} min"
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
