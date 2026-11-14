#!/usr/bin/env python3
"""Download Idaho's bills from the Legislature's website (https://legislature.idaho.gov/), plain server-built HTML: there is
no API or bulk file. Its robots.txt (checked 2026-11-08) bars, for all user agents, only /wp-admin/ and the committee
calendar's views (/committee-calendar/action~*/, /*/action~*/), none of which are read; it sets no crawl delay for us (a
1-second one for OpenAI's bots, and bars some others by name). One request at a time, at most one a second.

Idaho's Legislature meets once a year, from early January to about April (bills don't carry over); extraordinary
sessions are left out. For each year from two years back through this one, into data/id/<year>/:
- list.html (/sessioninfo/<year>/legislation/, trimmed to the page's content): every bill, resolution and memorial with
  its short title and status ("H St Aff", "Law"), the subject index, the Enacted Legislation table (session law
  chapter, bill, governor's signature date, effective date) and the vetoed bills (with links to the veto letters).
  list.json is what this script reads from it: {"bills": {"H0003": {"label", "title", "status"}}, "enacted": [{"chapter",
  "bill", "title", "signed", "effective"}], "vetoed": ["S1023"]}.
- bills/<H0003>.html (/sessioninfo/<year>/legislation/H0003/, trimmed): each House and Senate bill (H0001, S1001) and
  joint resolution (HJR001, SJR101: in Idaho these propose constitutional amendments; concurrent resolutions, memorials
  and one house's resolutions are left out). The page has the sponsor ("by REVENUE AND TAXATION COMMITTEE": nearly all
  bills are a committee's; the member who asked is named only in the Statement of Purpose's "Contact:"), the subject
  and one-line description ("TAXATION – Amends existing law to ..."), links to the versions (S1023E2.pdf: engrossed
  after amendment), the Statement of Purpose (S1023SOP.pdf) and legislative co-sponsors (S1023LegCo.pdf), and the
  history: a date column (MM/DD, no year; blank for more steps the same day) and the action, with each floor vote member
  by member ("PASSED - 56-14-0", then AYES, NAYS and "Absent" or "Absent and excused" name lists, the floor sponsor and
  "Title apvd - to Senate"). Names are surnames, with the district where two share one ("Crane(12)") and a substitute
  in parentheses ("Cheatum(Phillips)"); the Speaker is "Mr. Speaker". Laws: "Session Law Chapter 1"; vetoes: "Returned
  from Governor vetoed", with any override vote. There are no committee roll calls (they are only in the minutes, PDFs).
- committees/<HJUD>.html (/sessioninfo/<year>/standingcommittees/HJUD/, and the joint finance committee at
  /sessioninfo/<year>/joint/jfac/): each standing committee's meetings that year (with links to agendas and minutes)
  and its members (chair and vice chair marked, district, Statehouse phone, email). The list of committees is the
  year's /sessioninfo/<year>/standingcommittees/ page (14 House and 10 Senate committees).
- state.json: each bill's list status when last read ("stamps") and the day it was read ("read"); when the committees
  were last read; "finished" once the year's bills have all been read after its session (from August 1 of the year).
And into data/id/members/: house.html and senate.html (/house/membership/, /senate/membership/: the current members
only; past members appear only in past years' committee pages and in roll calls), and members.json read from them:
name, party, email, district, seat ("A" or "B" for representatives), leadership post, home and Statehouse phones,
address, committees with "Chair"/"Vice Chair". Read when older than a week.

A bill is read again when its status in the list changes. Until a year is finished, bills not read for a week are also
read again (at most REFRESH_MAX a run, oldest first), for steps that don't change the status. The bill pages give no
Last-Modified. A first copy of three years (about 2,200 bills) takes about 40 minutes; after that a run reads one list
per unfinished year and the bills whose status changed: a minute or two out of session.

- sop/<H0003>.txt (/wp-content/uploads/sessioninfo/<year>/legislation/H0003SOP.pdf, as text by pdftotext -layout; robots.txt
  allows /wp-content/uploads/): each bill's Statement of Purpose / Fiscal Note, written for the bill's sponsor, the only
  plain account of what a bill does (`statements()`; states/id/texts.py turns them into texts_<year>.json). After the
  bills, every run; at the same one request a second. About 2,100 for three years, each about 640 KB (fonts embedded):
  the first copy takes about 40 minutes, over one or two runs.

Not downloaded: the co-sponsor lists, bill texts, committee minutes and agendas (PDFs).

data/id/incomplete says "running" during the first copy, then lists what was never downloaded (a year's list, a listed
bill's page, the members); it is removed when nothing is missing. A request that fails where a last copy exists keeps
that copy and doesn't count. The statements of purpose never count.
Usage: python3 states/id/fetch.py [year]   (default: every year above; a single year leaves the marker alone)
"""
import gzip, hashlib, html, json, os, re, shutil, subprocess, sys, tempfile, time, urllib.error, urllib.request
from collections import Counter
from datetime import date, timedelta

SITE = "https://legislature.idaho.gov"
DATA = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "id"))
AGENT = "statebilltracker.org (a nonprofit bill tracker; contact via github.com/judithhubbard)"
TODAY = date.today()
YEAR = TODAY.year
ONLY = int(sys.argv[1]) if len(sys.argv) > 1 else None
DELAY = 1.0  # seconds between the starts of two requests
KIND = re.compile(r"^(HJR|SJR|H|S)\d+$")  # bills and joint resolutions (constitutional amendments)
JOINT = ("jfac",)  # joint committees read with the standing ones: Finance-Appropriations writes the budget bills
REFRESH_DAYS = 7
REFRESH_MAX = 300  # bills read again per run for being a week old (runs are two hours apart on GitHub)
MEMBER_DAYS = 7
MARKER = os.path.join(DATA, "incomplete")

# The run's own time limit (FETCH_MINUTES, set by the workflow): stop a few minutes early, with everything read so far
# saved and a summary printed, rather than be cut off silently mid-request.
START = time.time()
BUDGET = max(0.0, float(os.environ.get("FETCH_MINUTES") or 0) - 5) * 60
FAILS = Counter()  # why requests failed, for the summary
STATS = {"requests": 0, "bills": 0, "statements": 0}
PDFTOTEXT = shutil.which("pdftotext")
LAST = [0.0]  # when the last request started


class Refused(Exception):
    """The server turned us away (401/403/429): stop the run."""


def out_of_time():
    return BUDGET and time.time() - START > BUDGET


NOT_MODIFIED = object()  # request()'s answer to a conditional request when the document hasn't changed
HEADERS = {}  # the last answer's Last-Modified


def request(path, label, must=None, binary=False, since=None):
    """The page at SITE + path as text (bytes when binary), or None after three tries; None at once for a 404. must is a
    piece of text the page has to contain (else it's counted as a failure: an error page served as 200). since: a
    Last-Modified value to send as If-Modified-Since; NOT_MODIFIED when the server answers 304."""
    HEADERS.clear()
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
            headers = {"User-Agent": AGENT, "Accept-Encoding": "gzip"}
            if since:
                headers["If-Modified-Since"] = since
            req = urllib.request.Request(SITE + path, headers=headers)
            with urllib.request.urlopen(req, timeout=120) as r:
                body = r.read()
                if r.headers.get("Content-Encoding") == "gzip":
                    body = gzip.decompress(body)
                HEADERS["modified"] = r.headers.get("Last-Modified") or ""
            if binary:
                return body
            text = body.decode("utf-8", "replace")
            if must and must not in text:
                FAILS["unexpected page"] += 1
            else:
                return text
        except urllib.error.HTTPError as e:
            if e.code == 304 and since:
                return NOT_MODIFIED
            FAILS[f"HTTP {e.code}"] += 1
            if e.code in (401, 403, 429):
                raise Refused(f"{label}: HTTP {e.code}")
            if e.code == 404:
                return None
        except Exception as e:
            FAILS[type(e).__name__] += 1
        time.sleep(5 * (attempt + 1))
    print(f"{label}: failed three times", flush=True)
    return None


def trim(page):
    """The page's content: after the site's menus (the first <div class="container-fluid">) to the footer, without
    scripts and styles (the menus and footer are the same on every page)."""
    a = page.find('<div class="container-fluid">')
    b = page.find("<footer", max(a, 0))
    body = page[max(a, 0):b if b > 0 else len(page)]
    return re.sub(r"<script\b.*?</script>|<style\b.*?</style>", "", body, flags=re.S)


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


def parse_list(page, year):
    """{"bills": {key: {"title", "status"}}, "enacted": [...], "vetoed": [keys]} from the year's legislation page."""
    bills = {}
    # The row's label carries an "a" per amendment ("H0006a", "S1023aa,aa"), so it's part of the status; the key comes
    # from the link.
    for m in re.finditer(r'<tr id="bill[^"]*"[^>]*>(.*?)</tr>', page, re.S):
        link = re.search(rf"/sessioninfo/{year}/legislation/([A-Z]+\d+)", m.group(1))
        cells = [text(c) for c in re.findall(r"<td\b[^>]*>(.*?)</td>", m.group(1), re.S)]
        if link and len(cells) >= 4:
            bills[link.group(1)] = {"label": cells[0], "title": cells[1], "status": " ".join(cells[3:]).strip()}
    enacted = []
    t = page.find("enacted-legislation-table")
    if t >= 0:
        table = page[t:page.find("</table>", t)]
        for row in re.findall(r"<tr\b[^>]*>(.*?)</tr>", table, re.S)[1:]:
            cells = [text(c) for c in re.findall(r"<td\b[^>]*>(.*?)</td>", row, re.S)]
            link = re.search(rf"/sessioninfo/{year}/legislation/([A-Z]+\d+)", row)
            if len(cells) >= 5 and link:
                enacted.append({"chapter": cells[0], "bill": link.group(1), "title": cells[2], "signed": cells[3],
                                "effective": cells[4]})
    vetoed = []
    v = page.find("Legislation Vetoed</h2>")
    if v >= 0:
        end = page.find('<div class="tab-pane', v)
        vetoed = sorted(set(re.findall(rf"/sessioninfo/{year}/legislation/([A-Z]+\d+)", page[v:end if end > 0 else None])))
    return {"bills": bills, "enacted": enacted, "vetoed": vetoed}


def committees(year, folder, state, live):
    """The year's standing committees (and JFAC): read once, and weekly while the year isn't finished."""
    out = os.path.join(folder, "committees")
    last = state.get("committees") or ""
    if last and (not live or last >= (TODAY - timedelta(days=REFRESH_DAYS)).isoformat()):
        return
    page = request(f"/sessioninfo/{year}/standingcommittees/", f"{year} committee list", "standingcommittees/")
    codes = sorted(set(re.findall(rf"/sessioninfo/{year}/standingcommittees/([A-Z]+)/", page or "")))
    if not codes:
        print(f"{year} committees: no list; kept the last copies", flush=True)
        return
    os.makedirs(out, exist_ok=True)
    got = 0
    for code, path in [(c, f"/sessioninfo/{year}/standingcommittees/{c}/") for c in codes] + \
                      [(j.upper(), f"/sessioninfo/{year}/joint/{j}/") for j in JOINT]:
        if out_of_time():
            return
        page = request(path, f"{year} committee {code}", "lso-heading")
        if page:
            save_text(trim(page), os.path.join(out, f"{code}.html"))
            got += 1
    print(f"{year} committees: {got} of {len(codes) + len(JOINT)} read", flush=True)
    if got == len(codes) + len(JOINT):
        state["committees"] = TODAY.isoformat()


def finished_by(year):
    """From this day a year's bills no longer change: its session ended months before (August 1 of the year)."""
    return f"{year}-08-01"


def session(year):
    """One year's list, bills and committees."""
    folder = os.path.join(DATA, str(year))
    state_path = os.path.join(folder, "state.json")
    state = load(state_path, {})
    if state.get("finished"):
        print(f"{year}: finished and fully read; nothing to do", flush=True)
        return
    page = request(f"/sessioninfo/{year}/legislation/", f"{year} list", "Legislation by Bill Number")
    listing = parse_list(page, year) if page else None
    if listing and listing["bills"]:
        os.makedirs(os.path.join(folder, "bills"), exist_ok=True)
        save_text(trim(page), os.path.join(folder, "list.html"))
        save(listing, os.path.join(folder, "list.json"))
    else:
        listing = load(os.path.join(folder, "list.json"))
        if not listing:
            if page is not None or year < YEAR:
                print(f"{year}: no bill list", flush=True)
            return
        print(f"{year}: list unreadable; kept the last copy", flush=True)
    stamps, read = state.setdefault("stamps", {}), state.setdefault("read", {})
    wanted = {k: f'{b.get("label", "")} {b["status"]}' for k, b in listing["bills"].items() if KIND.match(k)}
    todo = [k for k, status in wanted.items()
            if stamps.get(k) != status or not os.path.exists(os.path.join(folder, "bills", f"{k}.html"))]
    stale = (TODAY - timedelta(days=REFRESH_DAYS)).isoformat()
    old = sorted((read.get(k, ""), k) for k in wanted if k not in todo and read.get(k, "") < stale)
    todo += [k for _, k in old[:REFRESH_MAX]]
    print(f"{year}: {len(wanted)} bills and joint resolutions listed ({len(listing['enacted'])} laws, "
          f"{len(listing['vetoed'])} vetoed); {len(todo)} to read", flush=True)
    got = 0
    for k in todo:
        if out_of_time():
            break
        page = request(f"/sessioninfo/{year}/legislation/{k}/", f"{year} {k}", 'class="bill-table"')
        if not page:
            continue  # the last copy stays, and it's asked again next run
        save_text(trim(page), os.path.join(folder, "bills", f"{k}.html"))
        stamps[k], read[k] = wanted[k], TODAY.isoformat()
        got += 1
        STATS["bills"] += 1
        if got % 25 == 0:
            save(state, state_path)
    save(state, state_path)
    print(f"{year} bills: {got} of {len(todo)} read", flush=True)
    live = not (TODAY.isoformat() >= finished_by(year))
    committees(year, folder, state, live)
    if not live and wanted and all(read.get(k, "") >= finished_by(year) for k in wanted) \
            and state.get("committees") and not out_of_time():
        state["finished"] = True
        print(f"{year}: finished", flush=True)
    save(state, state_path)


def pdf_text(body):
    """A PDF's text by pdftotext -layout (which keeps a blank line between paragraphs), or None."""
    if not PDFTOTEXT:
        return None
    with tempfile.NamedTemporaryFile(suffix=".pdf") as f:
        f.write(body)
        f.flush()
        try:
            out = subprocess.run([PDFTOTEXT, "-layout", "-enc", "UTF-8", f.name, "-"], capture_output=True, timeout=120)
        except (OSError, subprocess.SubprocessError):
            return None
    return out.stdout.decode("utf-8", "replace") if out.returncode == 0 else None


def texts_module():
    """states/id/texts.py, loaded by its path (this file runs as a script)."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("id_texts", os.path.join(os.path.dirname(os.path.abspath(__file__)), "texts.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def statements(year, only=None):
    """Each bill's Statement of Purpose / Fiscal Note (/wp-content/uploads/sessioninfo/<year>/legislation/H0003SOP.pdf),
    saved as text in sop/H0003.txt. There is one per bill, replaced in place when the sponsor revises it (its footer then
    says "Bill SOP/FN REVISED: 02/04/2026", usually around the committee hearing), so: read once; while the year is live,
    asked again (If-Modified-Since, so an unchanged one costs a 304) whenever the bill's list status has changed since;
    a document the server doesn't have (an HTML page instead of a PDF) is tried again weekly while the year is live.
    sop.json: {"H0003": {"read", "stamp" (the list status then), "modified" (Last-Modified), "sha"} or {"read",
    "stamp", "missing": true}}. Never holds the state back: what isn't read now is read on a later run. only: keys to
    read (for testing)."""
    if not PDFTOTEXT:
        print(f"{year} statements of purpose: pdftotext isn't installed; not read", flush=True)
        return
    folder = os.path.join(DATA, str(year))
    state = load(os.path.join(folder, "state.json"), {})
    stamps = state.get("stamps", {})
    live = TODAY.isoformat() < finished_by(year)
    index_path = os.path.join(folder, "sop.json")
    index = load(index_path, {})
    out = os.path.join(folder, "sop")
    bills_dir = os.path.join(folder, "bills")
    todo = []
    for name in sorted(os.listdir(bills_dir) if os.path.isdir(bills_dir) else []):
        key = name[:-5]
        if not name.endswith(".html") or (only and key not in only):
            continue
        try:
            page = open(os.path.join(bills_dir, name), encoding="utf-8").read()
        except OSError:
            continue
        if f"/sessioninfo/{year}/legislation/{key}SOP.pdf" not in page:
            continue
        have = index.get(key)
        if not have:
            todo.append(key)
        elif have.get("missing"):
            if live and have["read"] < (TODAY - timedelta(days=REFRESH_DAYS)).isoformat():
                todo.append(key)
        elif live and have.get("stamp") != stamps.get(key):
            todo.append(key)
    got, same, missing = 0, 0, 0
    for key in todo:
        if out_of_time():
            break
        have = index.get(key) or {}
        since = have.get("modified") if have.get("sha") and os.path.exists(os.path.join(out, f"{key}.txt")) else None
        body = request(f"/wp-content/uploads/sessioninfo/{year}/legislation/{key}SOP.pdf", f"{year} {key} SOP",
                       binary=True, since=since)
        if body is NOT_MODIFIED:
            have.update(read=TODAY.isoformat(), stamp=stamps.get(key))
            same += 1
            continue
        if body is None and out_of_time():
            break
        if body is None or not body.startswith(b"%PDF"):
            if body is not None:
                FAILS["not a PDF"] += 1
            if not have.get("sha"):  # a copy read before stays
                index[key] = {"read": TODAY.isoformat(), "stamp": stamps.get(key), "missing": True}
            missing += 1
            continue
        t = pdf_text(body)
        if t is None:
            FAILS["unreadable PDF"] += 1
            continue
        os.makedirs(out, exist_ok=True)
        save_text(t, os.path.join(out, f"{key}.txt"))
        index[key] = {"read": TODAY.isoformat(), "stamp": stamps.get(key), "modified": HEADERS.get("modified", ""),
                      "sha": hashlib.sha1(body).hexdigest()[:16]}
        got += 1
        STATS["statements"] += 1
        if got % 25 == 0:
            save(index, index_path)
    save(index, index_path)
    print(f"{year} statements of purpose: {got} read, {same} unchanged, {missing} not on the server "
          f"({len(todo)} were due)", flush=True)
    try:
        texts_module().write(year)
    except Exception as e:  # a text that fails to read mustn't stop the run
        print(f"{year} texts: failed ({type(e).__name__}: {e})", flush=True)


def member(block, house):
    """One member's entry on a membership page."""
    m = re.match(r"<p><strong>(.*?)</strong>\s*\(([A-Z])\)(.*)</p>", block, re.S)
    name, party, rest = text(m.group(1)), m.group(2), m.group(3)
    lines = [text(x) for x in re.split(r"<br\s*/?>", rest.split("<strong>Committees:</strong>")[0])]
    lines = [x for x in lines if x]
    email = re.search(r"mailto:([^\"]+)", rest)
    district = re.search(r"district=(\d+)", rest)
    seat = re.search(r"House Seat ([AB])", rest)
    post = re.search(r"</a></strong><br />\s*<strong>([^<]+)</strong>", rest)
    home = next((x[5:].strip() for x in lines if x.startswith("Home ")), "")
    statehouse = next((re.sub(r"\s*\(Session Only\)", "", x[11:]).strip() for x in lines if x.startswith("Statehouse ")), "")
    address = next((x for x in lines if re.search(r",\s*ID\s+\d{5}", x)), "")
    comms = []
    if "<strong>Committees:</strong>" in rest:
        for c in re.finditer(r'standingcommittees/([A-Z]+)/">(.*?)</a>([^<]*)', rest.split("<strong>Committees:</strong>")[1]):
            role = text(c.group(3)).strip(" –-")
            comms.append({"code": c.group(1), "name": text(c.group(2)), "role": role})
    return {"house": house, "name": re.sub(r"\s+", " ", name), "party": party,
            "email": email.group(1) if email else "", "district": int(district.group(1)) if district else None,
            "seat": seat.group(1) if seat else "", "post": text(post.group(1)) if post else "",
            "home": home, "statehouse": statehouse, "address": address, "committees": comms}


def members():
    """The current members of both houses, weekly. Returns True when there is a copy."""
    folder = os.path.join(DATA, "members")
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, "members.json")
    last = load(path)
    if last and last.get("read", "") >= (TODAY - timedelta(days=MEMBER_DAYS)).isoformat():
        return True
    out, ok = [], True
    for house, page_path in (("H", "/house/membership/"), ("S", "/senate/membership/")):
        page = request(page_path, f"{house} members", "mailto:")
        blocks = re.findall(r"<p><strong>[^<]*</strong>\s*\([A-Z]\)<br />.*?</p>", page or "", re.S)
        if not blocks:
            ok = False
            print(f"{house} members: unreadable; kept the last copy", flush=True)
            continue
        save_text(trim(page), os.path.join(folder, f"{'house' if house == 'H' else 'senate'}.html"))
        out += [member(b, house) for b in blocks]
    if ok:
        save({"read": TODAY.isoformat(), "members": out}, path)
        print(f"members: {sum(m['house'] == 'H' for m in out)} representatives, "
              f"{sum(m['house'] == 'S' for m in out)} senators", flush=True)
    return os.path.exists(path)


def begun(year):
    """Whether a year's session has convened (the second Monday of January)."""
    return TODAY >= date(year, 1, 1 + (0 - date(year, 1, 1).weekday()) % 7 + 7)


def never_downloaded(years):
    """What was never downloaded: a year's list, a listed bill's page, the members. (A failed refresh with a last copy
    doesn't count; nor does a year whose list doesn't exist yet.)"""
    out = []
    if not os.path.exists(os.path.join(DATA, "members", "members.json")):
        out.append("members")
    for year in years:
        if not begun(year):
            continue  # its bills are read when listed, but don't hold Idaho back before the session
        folder = os.path.join(DATA, str(year))
        listing = load(os.path.join(folder, "list.json"))
        if not listing:
            if year < YEAR or TODAY.month > 1:
                out.append(f"{year}:list")
            continue
        if any(KIND.match(k) and not os.path.exists(os.path.join(folder, "bills", f"{k}.html")) for k in listing["bills"]):
            out.append(f"{year}:bills")
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
        # Statements of purpose ("What it does") after every year's bills, so they never hold the bills back.
        for year in years:
            if out_of_time():
                break
            statements(year)
    except Refused as e:
        print(f"Stopped: the server refused a request ({e})", flush=True)
        refused = True
    missing = never_downloaded(years)
    print(f"run: {STATS['requests']} requests ({STATS['bills']} bills, {STATS['statements']} statements of purpose), {round((time.time() - START) / 60)} min"
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
