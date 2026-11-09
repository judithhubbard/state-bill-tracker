#!/usr/bin/env python3
"""Download Kentucky's bills from the Legislative Research Commission's websites: the bill record on
apps.legislature.ky.gov (static HTML pages the LRC regenerates as a whole, each session's carrying one "Last updated"
stamp), and members and committees on legislature.ky.gov (SharePoint pages). There is no API or bulk file.
apps.legislature.ky.gov has no robots.txt (it answers 404, checked 2026-11-08), so nothing there is barred;
legislature.ky.gov's robots.txt bars, for all user agents, only /_Layouts/, /SiteAssets/, /Lists/, /_catalogs/ and
/WorkflowTasks/, none of which are read, and sets no crawl delay. One request at a time, at most one a second, across
both hosts.

Kentucky's General Assembly meets once a year from early January: 60 legislative days in even years (to mid-April),
30 in odd years (to late March), with a break before the last two days for veto overrides, which are common. Bills
don't carry over. Special (extraordinary) sessions are left out. Each regular session's record is at
/record/<yy>rs/ ("26rs"); for each year from two years back through this one (and next year's in November and
December, once it exists), into data/ky/<year>/:
- lists/<name>.html (trimmed to the page's content) and list.json, what this script reads from them:
  {"stamp", "bills": [keys], "lists": {name: [keys]}, "amendments": {key: [anchors]}}. The indexes (house_bills,
  senate_bills, house_resolutions, senate_resolutions) give the keys; the status lists give outcomes and which bills
  moved: law (by route: "Signed By Governor", "Became Law Without Governor's Signature", "Enacted Over Governor's
  Veto"), vetoed ("Vetoed", "Line Items Vetoed", "Veto Overridden"), passed_both_houses, passed_one_house, enrolled,
  for_concurrence, conference, and bills_and_amendments_by_date (each day's new bills and amendments, by anchor:
  "HB826.html#SCS1").
- bills/<HB1>.html (/record/26rs/hb1.html, trimmed): each House and Senate bill (HB, SB) and joint resolution (HJR,
  SJR). Kentucky's constitutional amendments are bills ("AN ACT proposing to amend Section 145 of the Constitution of
  Kentucky"; HB 8 of 2026); its joint resolutions have the force of law (they go to the governor, and are vetoed and
  overridden like bills; mostly road namings and directions to agencies), so they're kept for the converter to decide;
  concurrent and one house's resolutions are left out. The page has: Last Action, the title ("AN ACT relating to
  ..."), bill documents (Acts Chapter link "Acts Ch. 4", versions, fiscal notes; PDFs, not read), the bill request
  number, sponsors in order (initial and surname: "K. Moser"; committees too), the LRC's "Summary of Original Version"
  and, once enacted, "Summary of Enacted Version" (for "What it does"), index headings (subjects), links to the vote
  history and veto message (PDFs), then the actions by date ("to Appropriations & Revenue (H)", "reported favorably, to
  Rules", "3rd reading, passed 79-17 with Committee Substitute (1)", "vetoed", "veto overridden", "delivered to
  Secretary of State (Acts Ch. 4)"; floor votes as tallies) and each proposed amendment with its sponsor and summary.
- state.json: the record's stamp when each bill was last read ("read"), each bill's signal (which status lists it's
  on and its amendments, "signals"), its last action date ("last"), the stamp the lists were read under ("listed"),
  and bills that answer 404 ("absent").
And into data/ky/members/ (read when older than a week): senate.html and house.html (/Legislators/senate,
/Legislators/house-of-representatives: the current members' cards), profiles/<n>.html (Legislator-Profile.aspx?
DistrictNumber=<n>: 1-100 are House districts, 101-138 Senate districts 1-38), and members.json read from them: name,
title, party, leadership post, district, counties, committees with "(Chair)"/"(Vice Chair)", home city, mailing,
legislative and Capitol addresses, phones (nearly all "LRC: 502-564-8100", the LRC's shared message line), email,
and the sponsor-page id the record uses (IndividualSponsorPages/455.html). Also committees.json: each House and Senate
standing committee (Committee-Details.aspx?CommitteeRSN=<n>): name, jurisdiction, members by district number with
"Chair"/"Vice Chair", and the meeting-materials id; their pages in committees/<rsn>.html.

What changes: the bill pages give no Last-Modified, but a session's record is regenerated as a whole, and every page
of it carries the same "Last updated" stamp (2024's: 9/26/2024; 2026's: 8/19/2026). Each run reads the session's
record.html first: when its stamp is the one every bill was read under, nothing more is read for that year (one
request). When it changed, the lists are read again, and then the bills: first any not yet downloaded and those whose
signal changed, all of them; then the rest, most recently active first, at most REFRESH_MAX a run (the record is
regenerated often during a session, so a run doesn't re-read everything each time; the rest follow on later runs).
A first copy of three sessions (about 3,800 bills and joint resolutions, plus about 190 member and committee pages)
takes about 70 minutes at a request a second, so GitHub's runs build it over two; a quiet run takes a few seconds.

Not downloaded: votes member by member, which exist only as PDFs: each bill's vote_history.pdf (/record/26rs/hb1/
vote_history.pdf: every floor roll call on the bill, names by surname, with text that pdftotext reads), each day's
House and Senate committee vote PDFs (house_votes/60_comm_votes.pdf, from committee_votes_House.html), and the daily
floor vote PDFs. robots.txt allows them (apps.legislature.ky.gov has none); none are read yet. Also not read: bill
texts, fiscal notes, veto messages (PDFs), and committee meeting agendas.

data/ky/incomplete says "running" during the first copy, then lists what was never downloaded (a year's lists, a
listed bill's page, the members or committees); it is removed when nothing is missing. A request that fails where a
last copy exists keeps that copy and doesn't count; a bill page that answers 404 is noted and doesn't count.
Usage: python3 states/ky/fetch.py [year]   (default: every year above; a single year leaves the marker alone)
"""
import gzip, html, json, os, re, sys, time, urllib.error, urllib.parse, urllib.request
from collections import Counter
from datetime import date, datetime, timedelta

APPS = "https://apps.legislature.ky.gov"
LEG = "https://legislature.ky.gov"
DATA = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "ky"))
AGENT = "statebilltracker.org (a nonprofit bill tracker; contact via github.com/judithhubbard)"
TODAY = date.today()
YEAR = TODAY.year
ONLY = int(sys.argv[1]) if len(sys.argv) > 1 else None
DELAY = 1.0  # seconds between the starts of two requests
KEY = re.compile(r'href="(HB|SB|HJR|SJR)(\d+)\.html(?:#(\w+))?"', re.I)  # bills and joint resolutions
INDEXES = ("house_bills", "senate_bills", "house_resolutions", "senate_resolutions")
STATUS = ("law", "vetoed", "passed_both_houses", "passed_one_house", "enrolled", "for_concurrence", "conference",
          "bills_and_amendments_by_date")
REFRESH_MAX = 400  # bills re-read per run only because the record's stamp changed (runs are two hours apart)
MEMBER_DAYS = 7
MARKER = os.path.join(DATA, "incomplete")

# The run's own time limit (FETCH_MINUTES, set by the workflow): stop a few minutes early, with everything read so far
# saved and a summary printed, rather than be cut off silently mid-request.
START = time.time()
BUDGET = max(0.0, float(os.environ.get("FETCH_MINUTES") or 0) - 5) * 60
FAILS = Counter()  # why requests failed, for the summary
STATS = {"requests": 0, "bills": 0}
LAST = [0.0]  # when the last request started
CODE = [0]  # the last request's HTTP status (404: not there)


class Refused(Exception):
    """The server turned us away (401/403/429): stop the run."""


def out_of_time():
    return BUDGET and time.time() - START > BUDGET


def request(url, label, must=None):
    """The page as text, or None after three tries; None at once for a 404 (CODE[0] is then 404). must is a piece of
    text the page has to contain (else it's counted as a failure: an error page served as 200)."""
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
            req = urllib.request.Request(url, headers={"User-Agent": AGENT, "Accept-Encoding": "gzip"})
            with urllib.request.urlopen(req, timeout=60) as r:
                body = r.read()
                if r.headers.get("Content-Encoding") == "gzip":
                    body = gzip.decompress(body)
            text = body.decode("utf-8", "replace")
            if must and must not in text:
                FAILS["unexpected page"] += 1
            else:
                return text
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


def strip(body):
    return re.sub(r"<script\b.*?</script>|<style\b.*?</style>|<input\b[^>]*>", "", body, flags=re.S)


def trim_record(page):
    """A record page's content: from the breadcrumbs to the footer (the menus and footer are the same everywhere)."""
    a = page.find('<div class="outerContainer breadcrumbRow')
    b = page.find("<footer", max(a, 0))
    return strip(page[max(a, 0):b if b > 0 else len(page)])


def trim_main(page):
    """A legislature.ky.gov page's content: its <main> element."""
    a = page.find("<main>")
    b = page.find("</main>", max(a, 0))
    return strip(page[max(a, 0):b + 7 if b > 0 else len(page)])


def text(fragment):
    t = re.sub(r"<br\s*/?>", "\n", fragment)
    t = html.unescape(re.sub(r"<[^>]+>", " ", t)).replace("\xa0", " ")
    return "\n".join(re.sub(r"[ \t]+", " ", line).strip() for line in t.split("\n")).strip()


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


def stamp_of(page):
    """The record's "Last updated: 8/19/2026 3:46 PM (EDT)" as "2026-08-19 15:46", or None."""
    m = re.search(r"Last updated:\s*(\d+/\d+/\d{4} \d+:\d+ [AP]M)", page or "")
    return datetime.strptime(m.group(1), "%m/%d/%Y %I:%M %p").strftime("%Y-%m-%d %H:%M") if m else None


def keys_in(page):
    """The bills and joint resolutions a record page links to, in order, and each one's anchors (amendments)."""
    keys, anchors = [], {}
    for m in KEY.finditer(page):
        k = m.group(1).upper() + m.group(2)
        if k not in anchors:
            keys.append(k)
            anchors[k] = []
        if m.group(3) and m.group(3) not in anchors[k]:
            anchors[k].append(m.group(3))
    return keys, anchors


def read_lists(code, folder, stamp):
    """The session's indexes and status lists, read under this stamp; None unless every index was read."""
    os.makedirs(os.path.join(folder, "lists"), exist_ok=True)
    out = {"stamp": stamp, "bills": [], "lists": {}, "amendments": {}}
    for name in INDEXES + STATUS:
        if out_of_time():
            return None
        page = request(f"{APPS}/record/{code}/{name}.html", f"{code} {name}", "Last updated")
        if page is None:
            if name in INDEXES:
                return None
            last = load(os.path.join(folder, "list.json")) or {}
            out["lists"][name] = (last.get("lists") or {}).get(name, [])
            print(f"{code} {name}: unreadable; kept the last copy", flush=True)
            continue
        save_text(trim_record(page), os.path.join(folder, "lists", f"{name}.html"))
        keys, anchors = keys_in(page)
        if name in INDEXES:
            out["bills"] += [k for k in keys if k not in out["bills"]]
        else:
            out["lists"][name] = keys
            if name == "bills_and_amendments_by_date":
                out["amendments"] = {k: a for k, a in anchors.items() if a}
    if "law" in out["lists"]:
        # The law list's routes, for checking totals: {"Signed By Governor": [keys], ...}
        page = open(os.path.join(folder, "lists", "law.html"), encoding="utf-8").read()
        out["law_routes"] = routes(page)
    if os.path.exists(os.path.join(folder, "lists", "vetoed.html")):
        out["veto_routes"] = routes(open(os.path.join(folder, "lists", "vetoed.html"), encoding="utf-8").read())
    return out


def routes(page):
    """A status list's sections: {"Vetoed": [keys], "Veto Overridden": [keys], ...} (headings are <h4>/<h3>)."""
    out, head = {}, None
    for m in re.finditer(r"<h[345][^>]*>(.*?)</h[345]>|" + KEY.pattern, page, re.S | re.I):
        if m.group(1) is not None:
            head = text(m.group(1))
        elif head:
            k = m.group(2).upper() + m.group(3)
            if k not in out.setdefault(head, []):
                out[head].append(k)
    return {h: ks for h, ks in out.items() if ks}


def last_action(page):
    m = re.search(r"<th>Last Action</th>\s*<td>\s*(\d\d)/(\d\d)/(\d\d)", page)
    return f"20{m.group(3)}-{m.group(1)}-{m.group(2)}" if m else ""


def session(year):
    """One session's lists and bills."""
    code = f"{year % 100:02d}rs"
    folder = os.path.join(DATA, str(year))
    state_path = os.path.join(folder, "state.json")
    state = load(state_path, {})
    page = request(f"{APPS}/record/{code}/record.html", f"{code} record", "Last updated")
    stamp = stamp_of(page)
    if not stamp:
        if page is None and CODE[0] == 404 and not os.path.exists(state_path):
            print(f"{year}: no record yet", flush=True)
        else:
            print(f"{year}: record page unreadable; kept the last copy", flush=True)
        return
    read, signals, lasts = state.setdefault("read", {}), state.setdefault("signals", {}), state.setdefault("last", {})
    absent = state.setdefault("absent", {})
    if state.get("stamp") == stamp and state.get("complete"):
        print(f"{year}: record unchanged since {stamp}; nothing to do", flush=True)
        return
    os.makedirs(os.path.join(folder, "bills"), exist_ok=True)
    listing = None
    if state.get("listed") != stamp:
        listing = read_lists(code, folder, stamp)
        if listing and listing["bills"]:
            save(listing, os.path.join(folder, "list.json"))
            state["listed"] = stamp
        elif not out_of_time():
            print(f"{year}: lists unreadable; kept the last copy", flush=True)
    listing = listing or load(os.path.join(folder, "list.json"))
    if not listing:
        save(state, state_path)
        return
    state["stamp"] = stamp
    on = {}
    for name, keys in listing["lists"].items():
        for k in keys:
            on.setdefault(k, []).append(name)
    wanted = {k: " ".join(on.get(k, []) + listing["amendments"].get(k, [])) for k in listing["bills"]}
    have = lambda k: os.path.exists(os.path.join(folder, "bills", f"{k}.html"))
    urgent = [k for k in wanted if (not have(k) and absent.get(k) != stamp) or (have(k) and signals.get(k) != wanted[k])]
    rest = [k for k in wanted if k not in urgent and read.get(k) != stamp and absent.get(k) != stamp]
    rest.sort(key=lambda k: lasts.get(k, ""), reverse=True)  # most recently active first
    todo = urgent + rest[:REFRESH_MAX]
    print(f"{year}: record of {stamp}; {len(wanted)} bills and joint resolutions listed; {len(urgent)} new or moved"
          f" and {len(rest)} older copies; {len(todo)} to read", flush=True)
    got = 0
    for k in todo:
        if out_of_time():
            break
        page = request(f"{APPS}/record/{code}/{k.lower()}.html", f"{year} {k}", 'class="bill-table')
        if not page:
            if CODE[0] == 404:
                absent[k] = stamp
            continue  # the last copy stays, and it's asked again next run
        save_text(trim_record(page), os.path.join(folder, "bills", f"{k}.html"))
        read[k], signals[k], lasts[k] = stamp, wanted[k], last_action(page)
        absent.pop(k, None)
        got += 1
        STATS["bills"] += 1
        if got % 25 == 0:
            save(state, state_path)
    state["complete"] = state.get("listed") == stamp and all(read.get(k) == stamp or absent.get(k) == stamp
                                                             for k in wanted)
    save(state, state_path)
    print(f"{year} bills: {got} of {len(todo)} read" + ("; all read under this stamp" if state["complete"] else ""),
          flush=True)


def profile(page, n):
    """One member's profile page."""
    h2 = re.search(r'<div class="row profile-top"><h2>(.*?)</h2>(?:<h3>(.*?)</h3>)?', page, re.S)
    head = re.sub(r"\s+", " ", text(h2.group(1))) if h2 else ""
    m = re.match(r"(Senator|Representative)\s+(.*?)\s*\(([A-Z])\)$", head)
    title, name, party = (m.group(1), m.group(2), m.group(3)) if m else ("", head, "")
    comms = []
    for box in re.finditer(r'<p class="title">([^<]*)</p><ul class="committee-list">(.*?)</ul>', page, re.S):
        for c in re.finditer(r'CommitteeRSN=(\d+)[^"]*">(.*?)</a>', box.group(2), re.S):
            label = re.sub(r"\s+", " ", text(c.group(2)))
            role = re.search(r"\(([^()]*)\)$", label)
            comms.append({"kind": text(box.group(1)), "rsn": int(c.group(1)),
                          "name": label[:role.start()].strip() if role else label,
                          "role": role.group(1) if role else ""})

    def field(title_):
        f = re.search(rf'<p class="title">{re.escape(title_)}</p>(.*?)(?=<p class="title">|</div>)', page, re.S)
        return [x for x in text(f.group(1)).split("\n") if x] if f else []

    district = re.search(r'District:</h3><div class="circle"><h3>(\d+)</h3></div><div><ul><li>(.*?)</li>', page, re.S)
    sponsor = re.search(r"IndividualSponsorPages/(\d+)\.html", page)
    return {"number": n, "house": "S" if n > 100 else "H", "district": int(district.group(1)) if district else n % 100 or 100,
            "counties": [c.strip() for c in text(district.group(2)).split(",")] if district else [],
            "title": title, "name": name, "party": party, "post": text(h2.group(2)) if h2 and h2.group(2) else "",
            "committees": comms, "home_city": " ".join(field("Home City")),
            "mailing": field("Mailing Address"), "legislative": field("Legislative Address"),
            "capitol": field("Capitol Address"), "phones": field("Phone Number(s)"),
            "email": " ".join(field("Email")), "sponsor_id": int(sponsor.group(1)) if sponsor else None}


def members():
    """The current members of both houses, weekly. A profile that fails keeps its last copy."""
    folder = os.path.join(DATA, "members")
    os.makedirs(os.path.join(folder, "profiles"), exist_ok=True)
    path = os.path.join(folder, "members.json")
    last = load(path) or {}
    if last.get("read", "") >= (TODAY - timedelta(days=MEMBER_DAYS)).isoformat() and not last.get("missing"):
        return
    numbers = []
    for house, page_path in (("senate", "/Legislators/senate"), ("house", "/Legislators/house-of-representatives")):
        page = request(LEG + page_path, f"{house} members", "Legislator-Card")
        cards = re.findall(r'DistrictNumber=(\d+)" class="Legislator-Card', page or "")
        if not cards:
            print(f"{house} members: list unreadable; kept the last copy", flush=True)
            return
        save_text(trim_main(page), os.path.join(folder, f"{house}.html"))
        numbers += [int(n) for n in cards]
    before = {m["number"]: m for m in last.get("members", [])}
    out, missing = [], []
    for n in numbers:
        if out_of_time():
            return
        page = request(f"{LEG}/Legislators/Pages/Legislator-Profile.aspx?DistrictNumber={n}", f"member {n}", "profile-top")
        if page:
            save_text(trim_main(page), os.path.join(folder, "profiles", f"{n}.html"))
            out.append(profile(page, n))
        elif n in before:
            out.append(before[n])
        else:
            missing.append(n)
    save({"read": TODAY.isoformat(), "members": out, "missing": missing}, path)
    print(f"members: {sum(m['house'] == 'H' for m in out)} representatives, {sum(m['house'] == 'S' for m in out)} "
          f"senators, {sum(bool(m['email']) for m in out)} with emails"
          + (f"; {len(missing)} never read" if missing else ""), flush=True)


def committee(page, rsn, kind):
    title = re.search(r'<div class="col-sm-12 committee-title"><h2>(.*?)</h2>', page, re.S)
    name = text(title.group(1)).split("\n")[-1] if title else ""
    juris = re.search(r'<div class="jurisdiction">(.*?)</div>', page, re.S)
    mems = []
    block = re.search(r'<ul class="member-list">(.*?)</ul>', page, re.S)
    for m in re.finditer(r'DistrictNumber=(\d+)"><span>(.*?)</span>', block.group(1) if block else "", re.S):
        parts = [p.strip() for p in text(m.group(2)).split(" - ")]
        mems.append({"number": int(m.group(1)), "name": parts[0],
                     "role": parts[2] if len(parts) > 2 else ""})
    materials = re.search(r"CommitteeDocuments/(\d+)", page)
    return {"rsn": rsn, "kind": kind, "name": name, "jurisdiction": text(juris.group(1)) if juris else "",
            "members": mems, "materials": int(materials.group(1)) if materials else None}


def committees():
    """The House and Senate standing committees, weekly. A committee that fails keeps its last copy."""
    folder = os.path.join(DATA, "committees")
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(DATA, "committees.json")
    last = load(path) or {}
    if last.get("read", "") >= (TODAY - timedelta(days=MEMBER_DAYS)).isoformat() and not last.get("missing"):
        return
    found = []
    for kind, page_path in (("House Standing Committee", "/Committees/house-standing-committee"),
                            ("Senate Standing Committee", "/Committees/senate-standing-committee")):
        page = request(LEG + page_path, kind, "Committee-Details")
        rsns = sorted(set(int(r) for r in re.findall(r"CommitteeRSN=(\d+)&amp;CommitteeType=" + kind, page or "")))
        if not rsns:
            print(f"{kind} list: unreadable; kept the last copy", flush=True)
            return
        found += [(r, kind) for r in rsns]
    before = {c["rsn"]: c for c in last.get("committees", [])}
    out, missing = [], []
    for rsn, kind in found:
        if out_of_time():
            return
        url = f"{LEG}/Committees/Pages/Committee-Details.aspx?CommitteeRSN={rsn}&CommitteeType={urllib.parse.quote(kind)}"
        page = request(url, f"committee {rsn}", "committee-title")
        if page:
            save_text(trim_main(page), os.path.join(folder, f"{rsn}.html"))
            out.append(committee(page, rsn, kind))
        elif rsn in before:
            out.append(before[rsn])
        else:
            missing.append(rsn)
    save({"read": TODAY.isoformat(), "committees": out, "missing": missing}, path)
    print(f"committees: {len(out)} ({sum(any(m['role'] == 'Chair' for m in c['members']) for c in out)} with a chair)"
          + (f"; {len(missing)} never read" if missing else ""), flush=True)


def never_downloaded(years):
    """What was never downloaded: a year's lists, a listed bill's page, the members, the committees. (A failed refresh
    with a last copy doesn't count; nor does a year whose record doesn't exist yet, or a bill page that answers 404.)"""
    out = []
    m = load(os.path.join(DATA, "members", "members.json"))
    if not m or m.get("missing"):
        out.append("members")
    c = load(os.path.join(DATA, "committees.json"))
    if not c or c.get("missing"):
        out.append("committees")
    for year in years:
        folder = os.path.join(DATA, str(year))
        listing = load(os.path.join(folder, "list.json"))
        if not listing:
            if year < YEAR or (year == YEAR and TODAY.month > 1):
                out.append(f"{year}:lists")
            continue
        absent = (load(os.path.join(folder, "state.json")) or {}).get("absent", {})
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
    years = [ONLY] if ONLY else [YEAR, YEAR - 1, YEAR - 2]
    nxt = [YEAR + 1] if not ONLY and TODAY.month >= 11 else []  # next session's record, once it exists
    refused = False
    try:
        if not ONLY:
            members()
        if not ONLY and not out_of_time():
            committees()
        for year in nxt + years:  # the newest first
            if out_of_time():
                break
            session(year)
    except Refused as e:
        print(f"Stopped: the server refused a request ({e})", flush=True)
        refused = True
    missing = never_downloaded(years)
    print(f"run: {STATS['requests']} requests ({STATS['bills']} bills), {round((time.time() - START) / 60)} min"
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
