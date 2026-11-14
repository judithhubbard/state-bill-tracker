#!/usr/bin/env python3
"""Download Louisiana's bills from the Legislature's website, legis.la.gov (an ASP.NET site; there is no API, bulk file
or feed), and members and committees from the House's and Senate's sites (house.louisiana.gov, senate.la.gov). Every
page read is a plain GET link the site's own pages use; no postback forms are driven. legis.la.gov has no robots.txt
(it answers 404, checked 2026-11-13), so nothing there is barred; house.louisiana.gov's and senate.la.gov's bar only
/private/ for all user agents, and none of the three sets a crawl delay. One request at a time, at most one a second,
across the three hosts. A 401, 403, 429 or challenge page stops the run.

Louisiana's Legislature meets once a year: in even years a general session (from the second Monday of March, 60
legislative days in 85 calendar days, to early June), in odd years a fiscal session (from the second Monday of April,
45 legislative days in 60 calendar days, to early June), where each member may introduce only five bills that aren't
about money. The governor's vetoes may be taken up in a veto session about 40 days after the session ends (held only if
a majority of either house doesn't decline it). Bills don't carry over. Constitutional amendments are bills (joint
resolutions numbered HB or SB: "(Constitutional Amendment)" in the title, two-thirds of each house, then the voters;
they don't go to the governor). Special (extraordinary) sessions ("24ES1") are left out. A session's code is "25RS".
For each regular session from two years back through this one (and next year's in November and December, once the
site has it), into data/la/<year>/:
- list.json: {"read": day, "counts": {"HB": 696, "SB": 254}, "bills": {"HB1": {"id": 248465, "author": "MCFARLAND",
  "status": "Signed by the Governor - Act 1", "considered": "Considered 4/29/25", "title": "APPROPRIATIONS: Provides
  for ..."}}, "vetoed": {"HB86": "Vetoed by the Governor - See Veto Message", "HB2": "Signed by the Governor - Act 2 -
  See Veto Message" (line-item vetoes)}, "amendments": [keys of the constitutional amendments]}. From the bill lists
  (BillSearchListQ.aspx?s=25RS&r=HB1-100: a range of 100 numbers per page, every bill in the range on one page; bills
  are numbered from 1 without gaps, so the ranges are read until one is empty), the vetoed list (VetoBills.aspx) and
  the list of constitutional amendments (ConstAmendments.aspx). Withdrawn bills ("Withdrawn from the files of the House
  - prior to introduction") and bills a committee replaced ("Substitute adopted on the House floor. Became HB694") are
  listed too.
- bills/<HB1>.json: each bill's page (BillInfo.aspx?s=25RS&b=HB1&sbi=y) as read: {"key", "id" (the site's instrument
  id), "session", "author" (the primary author's name), "author_title" ("Representative"/"Senator"), "author_page",
  "title" ("APPROPRIATIONS: Provides for the ordinary operating expenses ..."), "status", "authors": [{"name",
  "role" ("primary", "" for the co-authors), "page"}], "docs": [{"group" (Text, Amendments, Digests, Notes, Notices,
  Votes, Other),
  "label" ("Digest of HB1 Engrossed", "House Vote on HB 1 FINAL PASSAGE (#421)", "Committee Vote H-JUD 3/19/2026",
  "HB86 Veto Message"), "doc" (ViewDocument id) or "moi" (committee vote id)}] in the page's order (newest first within
  a group), "history": [{"date": "06/20", "day": "2025-06-20", "chamber": "H"/"S", "page": journal page, "journal":
  journal PDF path, "action": "Read third time by title, roll called on final passage, yeas 99, nays 0. Finally passed,
  title adopted, ordered to the Senate."}] newest first, as the page lists them}. The page gives dates without a year:
  "day" takes the session's year, or the year before for November and December (prefiling). Committee referrals,
  reports with their tallies ("Reported with amendments (23-0)"), floor passages with tallies, the governor's actions
  ("Signed by the Governor. Becomes Act No. 1.", "Vetoed by the Governor.") and veto-session overrides are history lines.
- docs/<id>.txt: documents read as text with pdftotext (they are PDFs, ViewDocument.aspx?d=<id>; each id is a fixed
  document, read once): every floor vote (-layout: "Sequence: 421 ... Date: 5/15/2025", the motion, then YEAS, NAYS and
  ABSENT, each a list of surnames in three columns, "Mr. Speaker"/"Mr. President", "Carter, R." for shared surnames,
  and "Total -- 99"), each bill's newest digest (the "Resume Digest" of what passed, else the newest "Digest of HB1
  Engrossed": House or Senate Legislative Services' plain summary, for "What it does"), and veto messages.
  votes/<id>.json is each floor vote read from it: {"doc", "label", "house", "sequence", "date", "time", "bill",
  "motion", "groups": {"YEAS": [names], "NAYS": [...], "ABSENT": [...]}, "totals": {"YEAS": 99, ...}}.
- cvotes/<moi>.json: committee votes member by member (CommitteeVote.aspx?moi=<n>, HTML; listed on bill pages from
  2026 on): {"moi", "label", "committee", "date", "bill", "motions": [{"by", "motion" ("Favorably", "Adopt" for an amendment), "kind"
  ("Final" for the committee's action on the bill, else ""), "time", "tally" ("17-0", "Without Objection"), "votes": [["Chenevert, Emily", "Yea"], ...]}], "final" ("Favorably (17-0)")}.
- state.json: when each bill was read ("read") and its list signal then ("sigs": status, considered, author, title),
  bills listed without a page ("absent"), documents that failed ("failed"), when the lists were read, and "none" when
  the site has no such session yet.
And into data/la/: members.json (read weekly) from the members lists (legis.la.gov Bios.aspx?cid=H and cid=S) and each
member's page (house.louisiana.gov/H_Reps/members?ID=<district>, senate.la.gov/smembers?ID=<district>), saved in
members/<H62>.txt (the page's text): {"read", "members": [{"house", "district", "name" ("Adams, Roy Daryl", as the
list writes it; "Vacant - District 77" for a vacant seat, "vacant" true, whose page shows the district office), "full"
("Roy Daryl Adams"), "party", "post" ("Senate President", "President Pro Tempore", "Senate Parliamentarian"; the
House's pages name no posts), "address" (district office lines), "phones", "fax", "email"
("hse062@legis.la.gov", "sen21@legis.la.gov"), "assistant", "parishes", "elected", "page", "committees" (the page's
committee line, as written)}], "missing"}; and committees.json (weekly) from the committee lists
(Committees.aspx?c=H, c=S) and each standing committee's page on the House's or Senate's site: [{"house", "name",
"url", "members": [{"name", "role" ("Chair", "Vice Chair", "Member", "Interim Member", "Ex Officio"), "district",
"party"}]}].

What's read again: the newest session's lists every run, older sessions' weekly; a bill's page when its list signal
changes (status, the "Considered"/"Sched. for" note, author or title), and while a session is live (February through
July of its year) every bill at least every two days, oldest first, at most REFRESH_MAX a run (history lines like
"Notice given." don't change the list). Documents are read once each, after every bill page is in, newest session
first. A first copy of three sessions (about 4,200 bills, a second each: 70 minutes, plus the members, 3 minutes; then
documents: 2026 alone has about 2,700 floor votes, 3,000 committee votes and 1,800 digests, so all three sessions'
take about five hours) builds up over several runs; a quiet run between sessions reads the lists and nothing else, a minute or two.

Not downloaded: bill texts, amendments, fiscal and actuarial notes, notices, other digests (PDFs; not needed); the
journals (PDFs the history links to by page); the House's committee roll-call and minutes documents (committee pages);
the Speaker and House leaders' posts (the House's member pages name none; the Speaker is an ex officio member of
every House committee);
concurrent and simple resolutions (not bills). Members who left are only in the votes, by surname.

data/la/incomplete says "running" during the first copy, then lists what was never downloaded (a session's lists, a
listed bill's page, the members); it is removed when nothing is missing. Documents, votes and committees fill in on
later runs and don't hold the state back; a session the site doesn't have yet doesn't either. A request that fails
where a last copy exists keeps that copy and doesn't count. PDFs need pdftotext (poppler-utils); without it documents
are skipped (the summary line says so).
Usage: python3 states/la/fetch.py [year]   (default: every session above; a single year leaves the marker alone)
"""
import html, json, os, re, shutil, subprocess, sys, tempfile, time, urllib.error, urllib.request
from collections import Counter
from datetime import date, timedelta

LEGIS = "https://legis.la.gov/legis"
HOUSE = "https://house.louisiana.gov"
SENATE = "https://senate.la.gov"
DATA = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "la"))
AGENT = "statebilltracker.org (a nonprofit bill tracker; contact via github.com/judithhubbard)"
TODAY = date.today()
YEAR = TODAY.year
ONLY = int(sys.argv[1]) if len(sys.argv) > 1 else None
DELAY = 1.0  # seconds between the starts of two requests
TYPES = ("HB", "SB")
SPAN = 100  # bill numbers per list page
REFRESH_MAX = 300  # bills read again per run only for being stale (runs are two hours apart on GitHub)
STALE_DAYS = 2
WEEKLY = 7
PDFTOTEXT = shutil.which("pdftotext")
MARKER = os.path.join(DATA, "incomplete")

# The run's own time limit (FETCH_MINUTES, set by the workflow): stop a few minutes early, with everything read so far
# saved and a summary printed, rather than be cut off silently mid-request.
START = time.time()
BUDGET = max(0.0, float(os.environ.get("FETCH_MINUTES") or 0) - 5) * 60
FAILS = Counter()  # why requests failed, for the summary
STATS = {"requests": 0, "bills": 0, "docs": 0, "cvotes": 0}
LAST = [0.0]  # when the last request started
CODE = [0]  # the last request's HTTP status (404: not there)


class Refused(Exception):
    """The server turned us away (401/403/429 or a challenge page): stop the run."""


def out_of_time():
    return BUDGET and time.time() - START > BUDGET


def request(url, label, must=None, binary=False):
    """The page as text (bytes if binary), or None after three tries; None at once for a 404 (CODE[0] is then 404).
    must is a piece of text the page has to contain (else it's counted as a failure: an error page served as 200)."""
    CODE[0] = 0
    for attempt in range(3):
        if out_of_time():
            return None
        wait = LAST[0] + DELAY - time.time()
        if wait > 0:
            time.sleep(wait)
        LAST[0] = time.time()
        STATS["requests"] += 1
        if STATS["requests"] % 200 == 0:
            print(f"  {STATS['requests']} requests, {round((time.time() - START) / 60)} min"
                  + (f"; failures {dict(FAILS)}" if FAILS else ""), flush=True)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": AGENT})
            with urllib.request.urlopen(req, timeout=90) as r:
                body = r.read()
            if binary:
                return body
            text_ = body.decode("utf-8", "replace")
            if "Just a moment..." in text_[:3000] or "challenge-platform" in text_[:5000]:
                raise Refused(f"{label}: challenge page")
            if must and must not in text_:
                FAILS["unexpected page"] += 1
            else:
                return text_
        except urllib.error.HTTPError as e:
            FAILS[f"HTTP {e.code}"] += 1
            if e.code in (401, 403, 429):
                raise Refused(f"{label}: HTTP {e.code}")
            if e.code == 404:
                CODE[0] = 404
                return None
        except Refused:
            raise
        except Exception as e:
            FAILS[type(e).__name__] += 1
        time.sleep(5 * (attempt + 1))
    print(f"{label}: failed three times", flush=True)
    return None


def text(fragment):
    t = re.sub(r"<br\s*/?>|</tr>|</p>|</div>|</li>|</h\d>", "\n", fragment or "")
    t = html.unescape(re.sub(r"<[^>]+>", " ", t)).replace("\xa0", " ")
    return "\n".join(x for x in (re.sub(r"[ \t\r]+", " ", line).strip() for line in t.split("\n")) if x)


def one_line(fragment):
    return re.sub(r"\s+", " ", text(fragment)).strip()


def save_text(body, path):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(body)
    os.replace(tmp, path)


def save(obj, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
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


def pdf_text(body, layout):
    """A PDF's text (pdftotext, -layout for the vote sheets' columns), or None."""
    if not body or not body.startswith(b"%PDF") or not PDFTOTEXT:
        return None
    with tempfile.TemporaryDirectory() as tmp:
        src = os.path.join(tmp, "in.pdf")
        with open(src, "wb") as f:
            f.write(body)
        try:
            out = subprocess.run([PDFTOTEXT] + (["-layout"] if layout else []) + ["-enc", "UTF-8", src, "-"],
                                 capture_output=True, timeout=300)
        except Exception:
            return None
        return out.stdout.decode("utf-8", "replace") if out.returncode == 0 else None


def code_of(year):
    return f"{year % 100:02d}RS"


def live(year):
    """A session whose bills still change: its own year, February through July (the session and the veto session)."""
    return year == YEAR and 2 <= TODAY.month <= 7


def days_ago(day):
    try:
        return (TODAY - date.fromisoformat(day)).days
    except (TypeError, ValueError):
        return 10 ** 6


# --- Lists -----------------------------------------------------------------------------------------------------------

def list_rows(page):
    """A results list's rows: {key: {"id", "author", "status", "considered", "title"}}, in order."""
    cells = {}
    for m in re.finditer(r'ListView(?:SearchResults|Bills)_ctrl(\d+)_(\w+)"([^>]*)>(.*?)</(?:a|span)>', page, re.S):
        row = cells.setdefault(int(m.group(1)), {})
        row[m.group(2)] = (m.group(3), m.group(4))
    out = {}
    for n in sorted(cells):
        row = cells[n]
        link = row.get("HyperLink1")
        if not link:
            continue
        key = one_line(link[1]).replace(" ", "")
        inst = re.search(r"BillInfo\.aspx\?i=(\d+)", link[0])
        author = row.get("LinkAuthor") or row.get("LabelAuthor") or ("", "")
        out[key] = {"id": int(inst.group(1)) if inst else None, "author": one_line(author[1]),
                    "status": one_line((row.get("LabelStatus") or ("", ""))[1]),
                    "considered": one_line((row.get("LabelConsidered") or ("", ""))[1]),
                    "title": one_line((row.get("LabelKWordAndSTitle") or ("", ""))[1])}
    return out


def count_of(page):
    m = re.search(r"There are (\d+) Instruments", page or "")
    return int(m.group(1)) if m else None


def read_lists(year, folder):
    """The session's bill lists, vetoed list and constitutional amendments. Returns the listing, None when unreadable,
    or "none" when the site has no such session."""
    code = code_of(year)
    out = {"read": TODAY.isoformat(), "counts": {}, "bills": {}, "vetoed": {}, "amendments": []}
    for kind in TYPES:
        n = 1
        while True:
            if out_of_time():
                return None
            page = request(f"{LEGIS}/BillSearchListQ.aspx?s={code}&r={kind}{n}-{n + SPAN - 1}", f"{code} {kind}{n}")
            if page is None:
                return None
            count = count_of(page)
            if count is None:
                if "Session ID" in page and n == 1 and kind == TYPES[0]:
                    return "none"  # "An invalid Session ID was provided": the site has no such session yet
                FAILS["unexpected page"] += 1
                return None
            rows = list_rows(page)
            if len(rows) != count:
                print(f"{code} {kind}{n}: {count} listed but {len(rows)} read", flush=True)
                return None
            out["bills"].update(rows)
            if count == 0:
                break
            n += SPAN
        out["counts"][kind] = sum(1 for k in out["bills"] if re.match(kind + r"\d", k))
    last = load(os.path.join(folder, "list.json")) or {}
    page = request(f"{LEGIS}/VetoBills.aspx?sid={code}", f"{code} vetoed", "Instruments")
    out["vetoed"] = {k: r["status"] for k, r in list_rows(page).items()} if page else last.get("vetoed", {})
    page = request(f"{LEGIS}/ConstAmendments.aspx?sid={code}", f"{code} amendments", "Instruments")
    out["amendments"] = list(list_rows(page)) if page else last.get("amendments", [])
    return out


# --- Bills -----------------------------------------------------------------------------------------------------------

def bill(page, key, year):
    """A bill page's parts (see the docstring)."""
    def span(name):
        m = re.search(rf'id="ctl00_PageBody_{name}"[^>]*>(.*?)</(?:span|a)>', page, re.S)
        return one_line(m.group(1)) if m else ""

    link = re.search(r'id="ctl00_PageBody_LinkAuthor" href="([^"]*)"', page)
    inst = re.search(r'id="ctl00_PageBody_HiddenFieldInstId" value="(\d+)"', page)
    out = {"key": key, "id": int(inst.group(1)) if inst else None, "session": span("LabelSession"),
           "author": span("LinkAuthor") or span("LabelAuthor").replace("by ", ""),
           "author_title": span("LabelAuthor").replace("by", "").strip(),
           "author_page": html.unescape(link.group(1)) if link else "", "title": span("LabelShortTitle"),
           "status": re.sub(r"^Current Status:\s*", "", span("LabelCurrentStatus")), "authors": [], "docs": [], "history": []}
    # The documents menu: its headings (Text, Amendments, Digests, Notices, Votes, Other, Authors) come first, then
    # each heading's items in a block "MenuDocumentsn<heading's index>Items".
    group, heads = "", []
    for m in re.finditer(r'id="ctl00_PageBody_MenuDocumentsn(\d+)Items"|'
                         r'<a class="ctl00_PageBody_MenuDocuments_1[^"]*" href="([^"]*)"[^>]*>(.*?)</a>', page, re.S):
        if m.group(1) is not None:
            n = int(m.group(1))
            group = heads[n] if n < len(heads) else ""
            continue
        href, label = html.unescape(m.group(2)), one_line(m.group(3))
        g = re.search(r"BillDocs\.aspx\?i=\d+&t=(\w+)", href)
        if g:
            heads.append(label or g.group(1))
            continue
        d = re.search(r"ViewDocument\.aspx\?d=(\d+)", href)
        c = re.search(r"CommitteeVote\.aspx\?moi=(\d+)", href)
        if d:
            out["docs"].append({"group": group, "label": label, "doc": int(d.group(1))})
        elif c:
            out["docs"].append({"group": group, "label": label, "moi": int(c.group(1))})
        elif group == "Authors" or "(primary)" in label:
            r = re.match(r"(.*?)\s*\(([^()]*)\)$", label)
            out["authors"].append({"name": r.group(1) if r else label, "role": r.group(2) if r else "", "page": href})
    a = page.find("ListViewHistory")
    for row in re.findall(r'<tr valign="top"[^>]*>(.*?)</tr>', page[a:] if a > 0 else "", re.S):
        cells = re.findall(r"<td[^>]*>(.*?)</td>", row, re.S)
        if len(cells) < 4:
            continue
        when = one_line(cells[0])
        journal = re.search(r'href="([^"]*)"', cells[2])
        day = ""
        m = re.match(r"(\d\d)/(\d\d)$", when)
        if m:
            day = f"{year - 1 if int(m.group(1)) >= 11 else year}-{m.group(1)}-{m.group(2)}"
        out["history"].append({"date": when, "day": day, "chamber": one_line(cells[1]), "page": one_line(cells[2]),
                               "journal": html.unescape(journal.group(1)) if journal else "",
                               "action": one_line(cells[3])})
    return out


def signal(row):
    return "|".join((row.get("status", ""), row.get("considered", ""), row.get("author", ""), row.get("title", "")))


def session(year):
    """One session's lists and bill pages."""
    code = code_of(year)
    folder = os.path.join(DATA, str(year))
    state_path = os.path.join(folder, "state.json")
    state = load(state_path, {})
    read, sigs, absent = state.setdefault("read", {}), state.setdefault("sigs", {}), state.setdefault("absent", {})
    listing = load(os.path.join(folder, "list.json"))
    if listing is None or year >= YEAR or days_ago(state.get("listed")) >= WEEKLY:
        got = read_lists(year, folder)
        if got == "none":
            state["none"] = TODAY.isoformat()
            save(state, state_path)
            if not listing:
                print(f"{year}: the site has no {code} session yet", flush=True)
                return
        elif got and got["bills"]:
            listing = got
            save(listing, os.path.join(folder, "list.json"))
            state["listed"] = TODAY.isoformat()
            state.pop("none", None)
        elif got is not None and not got["bills"]:
            print(f"{year}: {code} has no bills yet", flush=True)
            state["listed"] = TODAY.isoformat()
            save(state, state_path)
            if not listing:
                save(got, os.path.join(folder, "list.json"))
                return
        elif not out_of_time():
            print(f"{year}: lists unreadable; kept the last copy", flush=True)
    if not listing:
        save(state, state_path)
        return
    os.makedirs(os.path.join(folder, "bills"), exist_ok=True)
    rows = listing["bills"]
    have = lambda k: os.path.exists(os.path.join(folder, "bills", f"{k}.json"))
    urgent = [k for k in rows if (not have(k) and absent.get(k) != signal(rows[k]))
              or (have(k) and sigs.get(k) != signal(rows[k]))]
    rest = []
    if live(year):
        rest = [k for k in rows if k not in urgent and have(k) and days_ago(read.get(k)) >= STALE_DAYS]
        rest.sort(key=lambda k: read.get(k, ""))
    todo = urgent + rest[:REFRESH_MAX]
    print(f"{year}: {len(rows)} bills listed ({', '.join(f'{n} {k}' for k, n in listing['counts'].items())}); "
          f"{len(urgent)} new or changed, {len(rest)} stale; {len(todo)} to read", flush=True)
    got = 0
    for k in todo:
        if out_of_time():
            break
        page = request(f"{LEGIS}/BillInfo.aspx?s={code}&b={k}&sbi=y", f"{year} {k}", "ctl00_PageBody_LabelBillID")
        if not page:
            if CODE[0] == 404:
                absent[k] = signal(rows[k])
            continue  # the last copy stays, and it's asked again next run
        save(bill(page, k, year), os.path.join(folder, "bills", f"{k}.json"))
        read[k], sigs[k] = TODAY.isoformat(), signal(rows[k])
        absent.pop(k, None)
        got += 1
        STATS["bills"] += 1
        if got % 50 == 0:
            save(state, state_path)
    save(state, state_path)
    print(f"{year} bills: {got} of {len(todo)} read", flush=True)


# --- Documents and votes -----------------------------------------------------------------------------------------------

def floor_vote(txt, doc, label):
    """A floor vote sheet's text (pdftotext -layout) as {"sequence", "date", ..., "groups", "totals"}."""
    out = {"doc": doc, "label": label, "house": "House" if label.startswith("House") else
           "Senate" if label.startswith("Senate") else "", "sequence": "", "date": "", "time": "", "bill": "",
           "motion": "", "groups": {}, "totals": {}}
    head, _, body = txt.partition("The roll was called")
    for name, pat in (("sequence", r"Sequence:\s*(\d+)"), ("date", r"Date:\s*([\d/]+)"),
                      ("time", r"Time:\s*([\d:]+ [AP]M)"), ("bill", r"\b((?:HB|SB) \d+) BY\b")):
        m = re.search(pat, head)
        out[name] = m.group(1) if m else ""
    lines = [x.strip() for x in head.split("\n") if x.strip() and not re.search(r"Regular Session|ROLL CALL", x)]
    out["motion"] = lines[-1] if lines else ""
    group = None
    for line in body.split("\n")[1:]:
        s = line.strip()
        if not s or s.startswith("with the following"):
            continue
        t = re.match(r"Total\s*--\s*(\d+)", s)
        if t:
            if group:
                out["totals"][group] = int(t.group(1))
            continue
        if re.fullmatch(r"[A-Z][A-Z /]*", s) and len(s) > 3:
            group = s
            out["groups"].setdefault(group, [])
            continue
        if group:
            out["groups"][group] += [n.strip() for n in re.split(r"\s{2,}", s) if n.strip()]
    return out


def committee_vote(page, moi, label):
    """A committee vote page (CommitteeVote.aspx) as {"committee", "date", "bill", "motions", "final"}."""
    a = page.find('id="ctl00_PageBody_divData"')
    body = page[a:page.find("</main>", max(a, 0))] if a > 0 else ""
    h4 = re.search(r"<h4>(.*?)</h4>", body, re.S)
    head = [one_line(x) for x in re.split(r"<br\s*/?>", h4.group(1))] if h4 else []
    head = [x for x in head if x]
    out = {"moi": moi, "label": label, "committee": head[1] if len(head) > 1 else "",
           "date": head[2] if len(head) > 2 else "", "bill": head[3] if len(head) > 3 else "", "motions": []}
    for m in re.finditer(r'<table class="tmotion">(.*?)</table>.*?<table class="tvote">(.*?)</table>', body, re.S):
        fields = {}
        for c1, c2 in re.findall(r'class="c1">(.*?)</td>\s*<td[^>]*class="c2">(.*?)</td>', m.group(1), re.S):
            fields[one_line(c1).rstrip(":")] = one_line(c2)
        kind = next((f for f in fields if f == "Motion" or f.startswith("Motion (")), "")
        out["motions"].append({"by": fields.get("Motion made by", ""), "motion": fields.get(kind, ""),
                               "kind": kind[8:-1] if kind.startswith("Motion (") else "", "time": fields.get("Motion date", ""),
                               "tally": fields.get("Vote", ""),
                               "votes": [[one_line(n), one_line(v)] for n, v in
                                         re.findall(r'class="c3">(.*?)</td>\s*<td class="c4">(.*?)</td>', m.group(2), re.S)]})
    f = re.search(r"<h4>Final action:\s*(.*?)</h4>", body, re.S)
    out["final"] = one_line(f.group(1)) if f else ""
    return out


def wanted_docs(b):
    """A bill's documents to read: its votes, its newest digest and any veto message."""
    out = [d for d in b["docs"] if d["group"] == "Votes" or re.search(r"\bVote on\b", d["label"])]
    digests = [d for d in b["docs"] if "doc" in d and d["label"].startswith("Resume Digest")] or \
              [d for d in b["docs"] if "doc" in d and d["label"].startswith("Digest of")]
    out += digests[:1]
    out += [d for d in b["docs"] if "doc" in d and "Veto Message" in d["label"]]
    return out


def documents(year):
    """The documents not yet read for this session's bills."""
    folder = os.path.join(DATA, str(year))
    if not os.path.isdir(os.path.join(folder, "bills")):
        return
    state_path = os.path.join(folder, "state.json")
    state = load(state_path, {})
    failed = state.setdefault("failed", {})
    for sub in ("docs", "votes", "cvotes"):
        os.makedirs(os.path.join(folder, sub), exist_ok=True)
    todo = []
    for name in sorted(os.listdir(os.path.join(folder, "bills"))):
        b = load(os.path.join(folder, "bills", name))
        for d in wanted_docs(b or {"docs": []}):
            if "moi" in d:
                if not os.path.exists(os.path.join(folder, "cvotes", f"{d['moi']}.json")):
                    todo.append(d)
            elif PDFTOTEXT and not os.path.exists(os.path.join(folder, "docs", f"{d['doc']}.txt")):
                todo.append(d)
    todo.sort(key=lambda d: failed.get(str(d.get("doc") or d.get("moi")), 0))  # ones that failed before go last
    if not todo:
        return
    print(f"{year}: {len(todo)} documents to read", flush=True)
    got = 0
    for d in todo:
        if out_of_time():
            break
        ident = str(d.get("doc") or d.get("moi"))
        if "moi" in d:
            page = request(f"{LEGIS}/CommitteeVote.aspx?moi={d['moi']}", f"{year} committee vote {ident}", "divData")
            v = committee_vote(page, d["moi"], d["label"]) if page else None
            if v and v["motions"]:
                save(v, os.path.join(folder, "cvotes", f"{ident}.json"))
                STATS["cvotes"] += 1
                got += 1
                failed.pop(ident, None)
            else:
                failed[ident] = failed.get(ident, 0) + 1
            continue
        vote = d["group"] == "Votes" or "Vote on" in d["label"]
        body = request(f"{LEGIS}/ViewDocument.aspx?d={ident}", f"{year} document {ident}", binary=True)
        txt = pdf_text(body, layout=vote)
        if txt is None or not txt.strip():
            failed[ident] = failed.get(ident, 0) + 1
            continue
        save_text(txt, os.path.join(folder, "docs", f"{ident}.txt"))
        if vote:
            save(floor_vote(txt, int(ident), d["label"]), os.path.join(folder, "votes", f"{ident}.json"))
        STATS["docs"] += 1
        got += 1
        failed.pop(ident, None)
        if got % 50 == 0:
            save(state, state_path)
    save(state, state_path)
    print(f"{year} documents: {got} of {len(todo)} read", flush=True)


# --- Members and committees ------------------------------------------------------------------------------------------

def member(page, house, district, name, url):
    """A member's page on the House's or Senate's site."""
    a = page.find("<main")
    lines = text(re.sub(r"<script\b.*?</script>|<style\b.*?</style>", "", page[a if a > 0 else 0:], flags=re.S)
                 ).split("\n")
    title = "State Representative" if house == "H" else "State Senator"
    i = lines.index(title) if title in lines else 0
    full = lines[i + 1] if i else ""
    # The name, then a post ("Senate President", "President Pro Tempore") when there is one, then the party.
    after = lines[i + 2:i + 4] if i else []
    party = next((x for x in after if x in ("Republican", "Democrat", "Independent", "No Party")), "")
    post = after[0] if after and after[0] != party and after[0] != "District" else ""
    phone = re.compile(r"\(?\d{3}\)?[ -.]?\d{3}-\d{4}|\d{3}-\d\d[A-Z]{5} \(\d{3}-\d{4}\)")
    out = {"house": house, "district": district, "name": name, "full": full, "party": party, "post": post,
           "vacant": name.startswith("Vacant"), "address": [],
           "phones": [], "fax": [], "email": "", "assistant": "", "parishes": "", "elected": "", "page": url,
           "committees": ""}
    j = next((n for n, x in enumerate(lines) if x.upper() == "DISTRICT INFORMATION"), None)
    if j is not None:
        for x in lines[j + 1:j + 20]:
            if re.search(r"@|Legislative Assistant|Representing|Corresponding|BACKGROUND|About|Year Elected", x):
                break
            if phone.search(x):
                number = phone.search(x).group(0)
                kind = out["fax"] if re.search(r"FAX|^F:", x, re.I) else out["phones"]
                if number not in kind:
                    kind.append(number)
            else:
                out["address"].append(x)
    for x in lines[i:]:
        m = re.search(r"[\w.\-]+@legis\.la\.gov", x)
        if m and not out["email"] and not re.match(r"web(sen|hse)", m.group(0)):
            out["email"] = m.group(0)
    for n, x in enumerate(lines):
        if x.startswith("Legislative Assistant"):
            v = x.split(":", 1)[1].strip()
            out["assistant"] = v or (lines[n + 1] if n + 1 < len(lines) else "")
        elif x.startswith("Representing Parishes:"):
            out["parishes"] = x.split(":", 1)[1].strip()
        elif x == "(Representing)" and n + 1 < len(lines):
            out["parishes"] = lines[n + 1]
        elif x.startswith("Year Elected:"):
            out["elected"] = x.split(":", 1)[1].strip()
        elif x.upper() in ("COMMITTEE ASSIGNMENTS", "COMMITTEES") and i < n < len(lines) - 1 and not out["committees"]:
            out["committees"] = lines[n + 1]
    return out


def members():
    """The current members of both houses, weekly. A page that fails keeps its last copy."""
    path = os.path.join(DATA, "members.json")
    last = load(path) or {}
    if days_ago(last.get("read")) < WEEKLY and not last.get("missing"):
        return
    folder = os.path.join(DATA, "members")
    os.makedirs(folder, exist_ok=True)
    found = []
    for house, cid in (("H", "H"), ("S", "S")):
        page = request(f"{LEGIS}/Bios.aspx?cid={cid}", f"{house} members", "district map")
        links = re.findall(r"<a href='(https://(?:house\.louisiana\.gov/H_Reps/members\.aspx|senate\.la\.gov/smembers)"
                           r"\?ID=(\d+))'[^>]*>([^<]*)</a>", page or "")
        if not links:
            print(f"{house} members: list unreadable; kept the last copy", flush=True)
            return
        found += [(house, int(d), html.unescape(n).strip(), u) for u, d, n in links]
    before = {(m["house"], m["district"]): m for m in last.get("members", [])}
    out, missing = [], []
    for house, district, name, url in found:
        if out_of_time():
            return
        url = url.replace("members.aspx?", "members?")  # where the House's old address redirects
        page = request(url, f"member {house}{district}", "State Representative" if house == "H" else "State Senator")
        if page:
            m = member(page, house, district, name, url)
            a = page.find("<main")
            save_text(text(re.sub(r"<script\b.*?</script>|<style\b.*?</style>", "", page[max(a, 0):], flags=re.S)),
                      os.path.join(folder, f"{house}{district}.txt"))
            out.append(m)
        elif (house, district) in before:
            out.append(before[(house, district)])
        else:
            missing.append(f"{house}{district}")
    save({"read": TODAY.isoformat(), "members": out, "missing": missing}, path)
    print(f"members: {sum(m['house'] == 'H' for m in out)} representatives, {sum(m['house'] == 'S' for m in out)} "
          f"senators, {sum(bool(m['email']) for m in out)} with emails, {sum(bool(m['phones']) for m in out)} with phones"
          + (f"; {len(missing)} never read" if missing else ""), flush=True)


def committee(page):
    """A standing committee's page: its name and members ("Butler, Rhonda Gaye" / "Chair | Dist. 38 | R")."""
    lines = text(re.sub(r"<script\b.*?</script>|<style\b.*?</style>", "", page, flags=re.S)).split("\n")
    mems = []
    for n, x in enumerate(lines[1:], 1):
        m = re.fullmatch(r"(.+?) \| Dist\. (\d+) \| ([A-Z]+)", x)
        if m:
            mems.append({"name": lines[n - 1], "role": m.group(1), "district": int(m.group(2)), "party": m.group(3)})
    title = re.search(r"<title>(.*?)</title>", page, re.S)
    head = next((x for x in lines if re.search(r"Committee$|^Committee on|Committee on ", x)
                 and not x.startswith(("Committee Members", "Committee Staff", "Committee Jurisdiction"))), "")
    return {"name": head or one_line(title.group(1) if title else ""), "members": mems}


def committees():
    """The House's and Senate's standing committees, weekly. A committee that fails keeps its last copy."""
    path = os.path.join(DATA, "committees.json")
    last = load(path) or {}
    if days_ago(last.get("read")) < WEEKLY and not last.get("missing"):
        return
    found = []
    for house, pat in (("H", r"https://house\.louisiana\.gov/H_Cmtes/[\w]+(?:\.aspx)?"),
                       ("S", r"https://senate\.la\.gov/Sen_Committees/[\w]+")):
        page = request(f"{LEGIS}/Committees.aspx?c={house}", f"{house} committees")
        urls = list(dict.fromkeys(re.findall(pat, page or "")))
        if not urls:
            print(f"{house} committees: list unreadable; kept the last copy", flush=True)
            return
        found += [(house, u.replace(".aspx", "")) for u in urls]
    before = {c["url"]: c for c in last.get("committees", [])}
    out, missing = [], []
    for house, url in found:
        if out_of_time():
            return
        page = request(url, f"committee {url.rsplit('/', 1)[-1]}", "Committee Members")
        if page:
            out.append(dict(house=house, url=url, **committee(page)))
        elif url in before:
            out.append(before[url])
        else:
            missing.append(url)
    save({"read": TODAY.isoformat(), "committees": out, "missing": missing}, path)
    print(f"committees: {len(out)} ({sum(any(m['role'] == 'Chair' for m in c['members']) for c in out)} with a chair)"
          + (f"; {len(missing)} never read" if missing else ""), flush=True)


# --- The run ---------------------------------------------------------------------------------------------------------

def begun(year):
    """Whether a year's regular session has convened: the second Monday of March in even years, of April in odd years."""
    month = 4 if year % 2 else 3
    return TODAY >= date(year, month, 1 + (0 - date(year, month, 1).weekday()) % 7 + 7)


def never_downloaded(years):
    """What was never downloaded: a session's lists, a listed bill's page, the members. (A failed refresh with a last
    copy doesn't count; nor does a session the site doesn't have yet, a bill page that answers 404, or documents.)"""
    out = []
    m = load(os.path.join(DATA, "members.json"))
    if not m or m.get("missing"):
        out.append("members")
    for year in years:
        if not begun(year):
            continue  # prefiled bills are read when listed, but don't hold Louisiana back before the session
        folder = os.path.join(DATA, str(year))
        state = load(os.path.join(folder, "state.json")) or {}
        listing = load(os.path.join(folder, "list.json"))
        if not listing:
            if not state.get("none"):
                out.append(f"{year}:lists")
            continue
        absent = state.get("absent", {})
        if any(not os.path.exists(os.path.join(folder, "bills", f"{k}.json")) and k not in absent
               for k in listing["bills"]):
            out.append(f"{year}:bills")
    return out


def main():
    os.makedirs(DATA, exist_ok=True)
    # Before the first copy, a run cut off without its summary leaves this, so a partial copy isn't published.
    if not ONLY and not any(name.isdigit() for name in os.listdir(DATA)):
        with open(MARKER, "w") as f:
            f.write("running\n")
    years = [ONLY] if ONLY else [YEAR, YEAR - 1, YEAR - 2]
    nxt = [YEAR + 1] if not ONLY and TODAY.month >= 11 else []  # next session's prefiled bills, once listed
    refused = False
    try:
        if not ONLY:
            members()
        for year in nxt + years:  # the newest first
            if out_of_time():
                break
            session(year)
        if not ONLY and not out_of_time():
            committees()
        for year in nxt + years:
            if out_of_time():
                break
            documents(year)
    except Refused as e:
        print(f"Stopped: the server refused a request ({e})", flush=True)
        refused = True
    missing = never_downloaded(years)
    print(f"run: {STATS['requests']} requests ({STATS['bills']} bills, {STATS['docs']} documents, {STATS['cvotes']} "
          f"committee votes), {round((time.time() - START) / 60)} min"
          + ("; stopped at the time limit" if out_of_time() else "")
          + ("; refused" if refused else "")
          + ("" if PDFTOTEXT else "; no pdftotext (documents skipped)")
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
