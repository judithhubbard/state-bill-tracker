#!/usr/bin/env python3
"""Download Mississippi's bills from the Legislature's bill status system (https://billstatus.ls.state.ms.us/), static XML
files that its own pages show through XSLT stylesheets. Neither billstatus.ls.state.ms.us nor www.legislature.ms.gov has
a robots.txt (both answer 404; checked 2026-11-08), so nothing is barred; one request at a time, a second apart.

The server omits the intermediate certificate its own certificate needs (GlobalSign RSA OV SSL CA 2018), so it's fetched
from GlobalSign (the address the certificate itself names) and added to a copy of the system's certificates
(data/ms/ca.pem); the connection is still fully checked. Folders answer 403 (no listings), so what exists comes from the
index files below, and what changed from their contents and each file's Last-Modified (sent back as If-Modified-Since;
the server answers 304 when the file is unchanged). Every file is ISO-8859-1 and is saved as served (bytes).

One regular session a year (bills don't carry over); extraordinary sessions ("20261E") are left out. For each year from
two years back through this one (and next year's once it exists, from November), into data/ms/<year>/:
- allmsrs.xml (/<year>/pdf/all_measures/allmsrs.xml, "Report of All Measures"): every measure with its short title,
  principal author (as the history files' author link names him: "Horan", "Creekmore IV"), last action ("03/17 Approved
  by Governor", "02/03 (H) Died In Committee": month/day, no year) and FLAGS (* amended, % three-fifths vote required,
  $ revenue, @ exempted from deadline, V vetoed, P partially vetoed). Kinds: HB, SB, HC and SC (House and Senate
  concurrent resolutions: constitutional amendments, "Constitution; amend Section 26 ...", are among them, with joint
  rules, Quebec and the like), HR, SR (simple resolutions), SN (Senate nominations) and JR (a joint resolution:
  redistricting, 2026). Only HB, SB, HC and SC are read further; telling amendments from the other concurrent
  resolutions (by title) is the converter's job.
- history/<HB0001>.xml (/<year>/pdf/history/HB/HB0001.xml, the allmsrs entry's ACTIONLINK): short and long titles,
  DISPOSITION ("Law"), vote needed, revenue, effective date, CHAPNUM (chapter of the session laws), committees in each
  house (name, code link "../../House_cmtes/JB.xml", still in it), principal and co-authors (by author link), code
  sections amended, the numbered actions (ACT_DESC "01/08 (H) Passed As Amended": month/day, the house in parentheses,
  none for the governor's steps; a referral to two committees is "Referred To Judiciary, Division A;Appropriations",
  a double referral moving on "DR - TSDP: JA To AP"), and for each floor vote ACT_VOTE, a link to the roll call as a PDF
  (/<year>/pdf/votes/house/0030003.pdf). Also links to the bill's versions (PDF and HTML), amendments (with their
  disposition: "Adopted", "Voice Vote") and fiscal note.
- h_cmte.xml, s_cmte.xml (each house's committees, name and code), h_auth.xml, s_auth.xml (that session's members, full
  name and author link), read when they change.
- state.json: each bill's allmsrs entry when last read ("stamps"), the day it was read ("read") and its Last-Modified
  ("modified"); the list's Last-Modified; "finished" once a past year's bills have all been read after the year ended.
And into data/ms/members/ (the current members only; no per-session copies): hr_membs.xml and ss_membs.xml (the Speaker,
the Lieutenant Governor and pro tempores, each member's link) and each member's house/<slug>.xml and senate/<slug>.xml:
district, party, email user name ("khoran": @house.ms.gov or @senate.ms.gov is not given), home, business and Capitol
phones, Capitol room, counties, committees with OFFICER ("C" chair, "V" vice chair). The slug is the author link's
("anderson_(110th)"), so the history files' authors tie to members; links differ in case ("White.xml" and
"white.xml"), so slugs are saved in lower case. Read when older than a week.

A bill is read again when its allmsrs entry (action, flags, title, author) changes, which is how its history file
changes. Until a year is finished, bills not read for a week are also asked again with If-Modified-Since (at most 300 a
run, oldest first), for documents added without an action. A finished year's allmsrs is still asked each run (one
request, usually a 304: the 2024 list was regenerated in October 2026). A first copy of three years (about 3,700
histories a year, about 1.3 seconds each) takes about 4 hours; after that a run takes a minute or two, up to about 7
minutes when 300 week-old bills are asked again (mostly 304s).

Not downloaded: the floor roll calls, which are PDFs (one per ACT_VOTE; members' votes are only there), the House's
weekly summaries (PDFs), and bill texts. There are no committee roll calls and no plain-language summaries in the XML:
"What it does" can only be the long title.

data/ms/incomplete says "running" during a run, then lists what was never downloaded (a year's list, a listed bill's
history, the members); it is removed when nothing is missing. A request that fails where a last copy exists is reported
but doesn't count.
Usage: python3 states/ms/fetch.py [year]   (default: every year above; a single year leaves the marker alone)
"""
import json, os, re, ssl, sys, time, urllib.error, urllib.request
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import date, timedelta

SITE = "https://billstatus.ls.state.ms.us"
DATA = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "ms"))
AGENT = "statebilltracker.org (a nonprofit bill tracker; contact via github.com/judithhubbard)"
INTERMEDIATE = "http://secure.globalsign.com/cacert/gsrsaovsslca2018.crt"
SYSTEM_CAS = ["/etc/ssl/certs/ca-certificates.crt", "/etc/ssl/cert.pem", "/etc/pki/tls/certs/ca-bundle.crt"]
CA = os.path.join(DATA, "ca.pem")
TODAY = date.today()
YEAR = TODAY.year
ONLY = int(sys.argv[1]) if len(sys.argv) > 1 else None
KINDS = ("HB", "SB", "HC", "SC")
REFRESH_DAYS = 7
REFRESH_MAX = 300  # bills asked again per run for being a week old (runs are two hours apart on GitHub)
MARKER = os.path.join(DATA, "incomplete")

# The run's own time limit (FETCH_MINUTES, set by the workflow): stop a few minutes early, with everything read so far
# saved and a summary printed, rather than be cut off silently mid-request.
START = time.time()
BUDGET = max(0.0, float(os.environ.get("FETCH_MINUTES") or 0) - 5) * 60
FAILS = Counter()  # why requests failed, for the summary
STATS = {"requests": 0, "unchanged": 0}
NOT_MODIFIED = object()  # a 304
CONTEXT = None


class Refused(Exception):
    """The server turned us away (401/403/429): stop the run."""


def out_of_time():
    return BUDGET and time.time() - START > BUDGET


def ca_bundle():
    """The system's certificates plus GlobalSign's intermediate (refreshed monthly)."""
    if not (os.path.exists(CA) and time.time() - os.path.getmtime(CA) < 30 * 86400):
        os.makedirs(DATA, exist_ok=True)
        req = urllib.request.Request(INTERMEDIATE, headers={"User-Agent": AGENT})
        with urllib.request.urlopen(req, timeout=60) as r:
            pem = ssl.DER_cert_to_PEM_cert(r.read())
        system = next(p for p in SYSTEM_CAS if os.path.exists(p))
        with open(CA + ".tmp", "w") as f:
            f.write(open(system).read() + "\n" + pem)
        os.replace(CA + ".tmp", CA)
    return ssl.create_default_context(cafile=CA)


def request(url, label, since=None, end=None):
    """GET url: (body, Last-Modified); (NOT_MODIFIED, since) for a 304; (None, None) for a 404 or after three tries.
    end is bytes the whole file ends with (a cut-off transfer is retried). Refused on 401/403/429."""
    for attempt in range(3):
        if out_of_time():
            return None, None
        time.sleep(1)
        STATS["requests"] += 1
        if STATS["requests"] % 200 == 0:
            print(f"  {STATS['requests']} requests, {round((time.time() - START) / 60)} min"
                  + (f"; failures {dict(FAILS)}" if FAILS else ""), flush=True)
        headers = {"User-Agent": AGENT}
        if since:
            headers["If-Modified-Since"] = since
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=60, context=CONTEXT) as r:
                body = r.read()
                modified = r.headers.get("Last-Modified")
            if end and end not in body[-200:]:
                FAILS["cut off"] += 1
            else:
                return body, modified
        except urllib.error.HTTPError as e:
            if e.code == 304:
                STATS["unchanged"] += 1
                return NOT_MODIFIED, since
            FAILS[f"HTTP {e.code}"] += 1
            if e.code in (401, 403, 429):
                raise Refused(f"{label}: HTTP {e.code}")
            if e.code == 404:
                return None, None
        except Exception as e:
            FAILS[type(e).__name__] += 1
        time.sleep(5 * (attempt + 1))
    print(f"{label}: failed three times", flush=True)
    return None, None


def save(obj, path):
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(obj, f, ensure_ascii=False)
    os.replace(tmp, path)


def write(body, path):
    tmp = path + ".tmp"
    with open(tmp, "wb") as f:
        f.write(body)
    os.replace(tmp, path)


def load(path, default):
    try:
        return json.load(open(path))
    except (OSError, ValueError):
        return default


def fetch_file(url, path, label, modified, end):
    """Download url into path unless unchanged since modified (only asked when the file is there). Returns the new
    Last-Modified, or None when it failed."""
    body, stamp = request(url, label, modified if os.path.exists(path) else None, end)
    if body is NOT_MODIFIED:
        return stamp
    if body is None:
        return None
    write(body, path)
    return stamp or ""


def measures(year):
    """A year's saved allmsrs.xml -> {"HB0001": (stamp, history path under /<year>/pdf/)} for the kinds read; None
    when there's no list."""
    try:
        root = ET.parse(os.path.join(DATA, str(year), "allmsrs.xml")).getroot()
    except (OSError, ET.ParseError):
        return None
    out = {}
    for g in root.iter("MSRGROUP"):
        link = (g.findtext("ACTIONLINK") or "").strip()
        m = re.fullmatch(r"\.\./(history/([A-Z]+)/(\2\d+)\.xml)", link)
        if not m or m.group(2) not in KINDS:
            continue
        stamp = "|".join((g.findtext(f) or "").strip() for f in ("ACTION", "FLAGS", "SHORTTITLE", "AUTHOR"))
        out[m.group(3)] = (stamp, m.group(1))
    return out


def session(year):
    """One year's lists and bill histories."""
    folder = os.path.join(DATA, str(year))
    base = f"{SITE}/{year}/pdf"
    state_path = os.path.join(folder, "state.json")
    state = load(state_path, {})
    for field in ("stamps", "read", "modified", "lists"):
        state.setdefault(field, {})
    list_path = os.path.join(folder, "allmsrs.xml")
    if year > YEAR and not os.path.exists(list_path):  # next year's session: only once it exists
        body, _ = request(f"{base}/all_measures/allmsrs.xml", f"{year} list", end=b"</LASTACTION>")
        if not body:
            return
    os.makedirs(os.path.join(folder, "history"), exist_ok=True)

    for name, end in (("all_measures/allmsrs.xml", b"</LASTACTION>"), ("h_cmte.xml", b"</COMMITTEES>"),
                      ("s_cmte.xml", b"</COMMITTEES>"), ("h_auth.xml", b"</LEGISLATURE>"), ("s_auth.xml", b"</LEGISLATURE>")):
        path = os.path.join(folder, os.path.basename(name))
        stamp = fetch_file(f"{base}/{name}", path, f"{year} {name}", state["lists"].get(name), end)
        if stamp is None:
            if out_of_time():
                return
            print(f"{year} {name}: unreadable; " + ("kept the last copy" if os.path.exists(path) else "none yet"), flush=True)
        else:
            state["lists"][name] = stamp
    save(state, state_path)
    listed = measures(year)
    if listed is None:
        return

    have = {k for k in listed if os.path.exists(os.path.join(folder, "history", f"{k}.xml"))}
    todo = [k for k in sorted(listed) if k not in have or state["stamps"].get(k) != listed[k][0]]
    if not state.get("finished"):  # and those not read for a week, so documents added without an action are caught
        week_ago = (TODAY - timedelta(days=REFRESH_DAYS)).isoformat()
        stale = sorted((k for k in have if k not in todo and state["read"].get(k, "") < week_ago),
                       key=lambda k: state["read"].get(k, ""))
        todo += stale[:REFRESH_MAX]
    got = 0
    for k in todo:
        if out_of_time():
            break
        path = os.path.join(folder, "history", f"{k}.xml")
        stamp = fetch_file(f"{base}/{listed[k][1]}", path, f"{year} {k}", state["modified"].get(k), b"</HISTORY>")
        if stamp is None:
            continue
        state["stamps"][k] = listed[k][0]
        state["read"][k] = TODAY.isoformat()
        state["modified"][k] = stamp
        got += 1
        if got % 100 == 0:
            save(state, state_path)
    missing = [k for k in listed if not os.path.exists(os.path.join(folder, "history", f"{k}.xml"))]
    # A past year is finished once every bill has been read after it ended.
    if year < YEAR and not missing and all(state["read"].get(k, "") >= f"{year + 1}-01-01" for k in listed):
        state["finished"] = True
    save(state, state_path)
    kinds = Counter(re.match(r"[A-Z]+", k).group() for k in listed)
    print(f"{year}: {got} of {len(todo)} histories read; {len(listed)} listed ({', '.join(f'{n} {c}' for c, n in sorted(kinds.items()))})"
          + (f"; {len(missing)} never downloaded" if missing else "") + ("; finished" if state.get("finished") else ""),
          flush=True)


def member_links(path):
    """A member list's links to members' files ("house/aguirre.xml"; not the Lieutenant Governor's website)."""
    try:
        root = ET.parse(path).getroot()
    except (OSError, ET.ParseError):
        return set()
    return {(e.text or "").strip() for e in root.iter()
            if e.tag.endswith("_LINK") and re.fullmatch(r"(house|senate)/[^/]+\.xml", (e.text or "").strip())}


def never_downloaded(years):
    """What was never downloaded (a year's list, a listed bill's history, a member list or member): what keeps the
    marker. A failed request where a last copy exists doesn't count."""
    missing = []
    for year in years:
        if year > YEAR and not os.path.isdir(os.path.join(DATA, str(year))):
            continue  # next year's session isn't up yet
        listed = measures(year)
        if listed is None:
            missing.append(f"{year}:list")
        elif any(not os.path.exists(os.path.join(DATA, str(year), "history", f"{k}.xml")) for k in listed):
            missing.append(f"{year}:bills")
    folder = os.path.join(DATA, "members")
    for index in ("hr_membs.xml", "ss_membs.xml"):
        links = member_links(os.path.join(folder, index))
        if not links or any(not os.path.exists(os.path.join(folder, link.lower())) for link in links):
            missing.append(f"members:{index[:2]}")
    return missing


def members():
    """The current members of both houses (read when older than a week)."""
    folder = os.path.join(DATA, "members")
    state_path = os.path.join(folder, "state.json")
    state = load(state_path, {"modified": {}})
    week_ago = (TODAY - timedelta(days=REFRESH_DAYS)).isoformat()
    if state.get("read", "") >= week_ago:
        return
    clean = True
    for index in ("hr_membs.xml", "ss_membs.xml"):
        os.makedirs(os.path.join(folder, "house" if index.startswith("h") else "senate"), exist_ok=True)
        path = os.path.join(folder, index)
        stamp = fetch_file(f"{SITE}/members/{index}", path, f"members {index}", state["modified"].get(index), b"</LEGISLATURE>")
        if stamp is None:
            clean = False
            if not os.path.exists(path):
                continue
        else:
            state["modified"][index] = stamp
        links = member_links(path)
        for link in sorted(links, key=str.lower):
            if out_of_time():
                return
            name = link.lower()
            target = os.path.join(folder, name)
            stamp = fetch_file(f"{SITE}/members/{link}", target, f"member {link}", state["modified"].get(name), b"</MEMBINFO>")
            if stamp is None:
                clean = False
            else:
                state["modified"][name] = stamp
        print(f"members {index}: {len(links)}", flush=True)
    if clean:
        state["read"] = TODAY.isoformat()
    save(state, state_path)


def main():
    global CONTEXT
    os.makedirs(DATA, exist_ok=True)
    # A run cut off by its time limit leaves this, so a partial copy isn't published (cleared after a clean run).
    if not ONLY:
        open(MARKER, "w").write("running\n")
    CONTEXT = ca_bundle()
    years = [ONLY] if ONLY else [YEAR, YEAR - 1, YEAR - 2] + ([YEAR + 1] if TODAY.month >= 11 else [])
    try:
        if not ONLY:
            members()
        for year in years:  # the current year first
            if out_of_time():
                break
            session(year)
    except Refused as e:
        print(f"Stopped: the server refused a request ({e})", flush=True)
    missing = never_downloaded(years)
    print(f"run: {STATS['requests']} requests ({STATS['unchanged']} unchanged), {round((time.time() - START) / 60)} min"
          + ("; stopped at the time limit" if out_of_time() else "")
          + (f"; request failures {dict(FAILS)}" if FAILS else "; no request failures")
          + (f"; never downloaded: {' '.join(missing)}" if missing else ""), flush=True)
    if ONLY:
        return
    if missing:
        open(MARKER, "w").write(" ".join(missing) + "\n")
    elif os.path.exists(MARKER):
        os.remove(MARKER)


if __name__ == "__main__":
    main()
