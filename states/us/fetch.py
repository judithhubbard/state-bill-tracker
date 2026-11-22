#!/usr/bin/env python3
"""Download Congress's bills, roll calls and members (no keys; see each site's notes below) into data/us/.

Bills: the Government Publishing Office's bulk data, BILLSTATUS (https://www.govinfo.gov/bulkdata/BILLSTATUS/), one XML
file per bill with everything congress.gov shows: titles, sponsor and cosponsors (bioguide ids), committees and their
activities, every action (the House's and the Senate's floor and committee lines, plus the Library of Congress's
summary lines with numeric codes: 8000 passed the House, 17000 passed the Senate, 28000 presented to the President,
36000 became law, 31000 vetoed ...), recorded votes on each action (roll number and the clerk's or Senate's XML
address), related bills, laws ("Public Law 118-50"), the policy area and subjects, and the Congressional Research
Service's summaries of each version. govinfo.gov's robots.txt bars only its site machinery (/core/, /admin/, /search/
...), not /bulkdata/, and lists the bulk data's sitemaps itself (checked 2026-11-16).
- Each Congress's bills of each kind come as one zip (BILLSTATUS-118-hr.zip, about 35 MB for the House's bills), kept as
  data/us/<congress>/BILLSTATUS-<congress>-<type>.zip, for hr, s, hjres and sjres (House and Senate bills and joint
  resolutions; simple and concurrent resolutions aren't downloaded: they don't make law).
- The zips are rebuilt every few days. Files changed since are found in the sitemap (sitemap/bulkdata/BILLSTATUS/
  119hr/sitemap.xml: each file's address and lastmod) and read one by one into data/us/<congress>/updates/, which the
  converter prefers to the zip's copy. A zip is downloaded again when the server's copy is a week newer than ours (the
  current Congress's), or a month newer (an earlier one's); updates older than the new zip are then removed.

Roll calls: each bill's own recorded floor votes (passage, suspension of the rules, agreeing to the other house's
amendment, conference reports, veto overrides, and the Senate's cloture votes on the bill; not amendments, motions to
recommit or procedural votes: convert.own_vote() decides), member by member, from the House Clerk
(clerk.house.gov/evs/<year>/roll<NNN>.xml) and the Senate (www.senate.gov/legislative/LIS/roll_call_votes/vote<congress>
<session>/vote_<congress>_<session>_<NNNNN>.xml), at the addresses the BILLSTATUS actions give. Neither site has a
robots.txt (clerk.house.gov answers 404; senate.gov redirects to its "file not found" page; checked 2026-11-16). One
request a second; each roll call is read once, into data/us/<congress>/votes/house_<year>_<roll>.xml or
senate_<session>_<roll>.xml. The first copy (about 2,500 roll calls for three Congresses) takes about 45 minutes, and a
run reads at most --votes-minutes (default 40) of them: the rest fill in on later runs and never hold the site back.

Members and committees: the public-domain congress-legislators data (https://unitedstates.github.io/
congress-legislators/; GitHub Pages, no robots.txt): legislators-current.json and committees-current.json and
committee-membership-current.json daily, legislators-historical.json (13 MB: every member since 1789) weekly, into
data/us/members/. contacts.py builds each Congress's contacts from them.

Veto messages: the House documents the President's messages are printed as, from GovInfo (`vetoes()`; a Senate bill's
message is printed only in the Congressional Record, not read).

data/us/incomplete lists what was never downloaded (a Congress's zip, the members); it is removed when nothing is
missing. A list that fails where a last copy exists keeps that copy.
Usage: python3 states/us/fetch.py [--votes-minutes N] [congress ...]   (default: the 117th to the current one)
"""
import json, os, re, sys, time, urllib.error, urllib.request, xml.etree.ElementTree as ET, zipfile
from datetime import date, datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", ".."))
from states.us import convert as C  # noqa: E402
from states.us import profile as P  # noqa: E402

DATA = os.path.normpath(os.path.join(HERE, "..", "..", "data", "us"))
AGENT = "statebilltracker.org (a nonprofit bill tracker; contact via github.com/judithhubbard)"
BULK = "https://www.govinfo.gov/bulkdata/BILLSTATUS"
SITEMAP = "https://www.govinfo.gov/sitemap/bulkdata/BILLSTATUS"
MEMBERS = "https://unitedstates.github.io/congress-legislators"
TYPES = ("hr", "s", "hjres", "sjres")
ARGS = sys.argv[1:]
VOTE_MINUTES = 40.0
if "--votes-minutes" in ARGS:
    i = ARGS.index("--votes-minutes")
    VOTE_MINUTES = float(ARGS[i + 1])
    del ARGS[i:i + 2]
CONGRESSES = [int(a) for a in ARGS] or C.CONGRESSES
NOW = datetime.now(timezone.utc)
missing = []


def get(url, binary=True, tries=3):
    """The answer's bytes and its Last-Modified header; None after three failures (a 404 at once)."""
    for n in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": AGENT})
            with urllib.request.urlopen(req, timeout=300) as r:
                return r.read(), r.headers.get("Last-Modified")
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None, None
            print(f"  {url}: HTTP {e.code}")
        except Exception as e:  # noqa: BLE001 (timeouts, resets)
            print(f"  {url}: {e}")
        time.sleep(5 * (n + 1))
    return None, None


def head(url):
    """The server's Last-Modified for a file, as a datetime, or None."""
    try:
        req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": AGENT})
        with urllib.request.urlopen(req, timeout=60) as r:
            lm = r.headers.get("Last-Modified")
            return datetime.strptime(lm, "%a, %d %b %Y %H:%M:%S %Z").replace(tzinfo=timezone.utc) if lm else None
    except Exception as e:  # noqa: BLE001
        print(f"  {url}: {e}")
        return None


def save(path, data):
    """Writes a file, unless it already holds exactly this (download.yml saves a state's copy only when a file changed)."""
    if os.path.exists(path) and os.path.getsize(path) == len(data) and open(path, "rb").read() == data:
        return
    tmp = path + ".tmp"
    with open(tmp, "wb") as f:
        f.write(data)
    os.replace(tmp, path)


def state(congress):
    path = os.path.join(DATA, str(congress), "state.json")
    return json.load(open(path)) if os.path.exists(path) else {}


def save_state(congress, st):
    save(os.path.join(DATA, str(congress), "state.json"), json.dumps(st, indent=1, sort_keys=True).encode())


def bills(congress):
    """The zips, then the files changed since (the current Congress)."""
    folder = os.path.join(DATA, str(congress))
    os.makedirs(os.path.join(folder, "updates"), exist_ok=True)
    st = state(congress)
    current = congress == max(C.CONGRESSES)
    # The Congress just ended is read like the current one until March 1: the President's actions on its last bills
    # (ten days, Sundays excepted, after they're presented) come in through January.
    newest = P.session_of_congress(max(C.CONGRESSES))
    live = current or (congress == max(C.CONGRESSES) - 1 and NOW.date() < date(newest, 3, 1))
    for t in TYPES:
        name = f"BILLSTATUS-{congress}-{t}.zip"
        path = os.path.join(folder, name)
        url = f"{BULK}/{congress}/{t}/{name}"
        ours = st.get("zips", {}).get(t)
        if os.path.exists(path) and ours:
            theirs = head(url)
            ours_t = datetime.fromisoformat(ours)
            if not theirs or (theirs - ours_t).days < (7 if live else 30):
                continue
        print(f"{congress} {t}: downloading {name}")
        data, lm = get(url)
        if not data or not zipfile.is_zipfile(__import__("io").BytesIO(data)):
            # A new Congress's zips appear some days after January 3: until then it isn't missing, just not there yet.
            new = current and (NOW.date() - date(P.session_of_congress(congress), 1, 3)).days < 45
            if not os.path.exists(path) and not new:
                missing.append(name)
            continue
        save(path, data)
        when = datetime.strptime(lm, "%a, %d %b %Y %H:%M:%S %Z").replace(tzinfo=timezone.utc) if lm else NOW
        st.setdefault("zips", {})[t] = when.isoformat()
        # Updates the new zip already holds are removed.
        upd = st.setdefault("updates", {})
        for f, lastmod in list(upd.items()):
            if f.startswith(f"BILLSTATUS-{congress}{t}") and re.match(rf"BILLSTATUS-{congress}{t}\d", f) and lastmod <= when.isoformat():
                p = os.path.join(folder, "updates", f)
                if os.path.exists(p):
                    os.remove(p)
                del upd[f]
        save_state(congress, st)
        time.sleep(2)
    if not live:
        return
    # Files changed since each zip was made: the sitemap's lastmod is later than the zip's and than our copy's. A new
    # Congress's files are read from its sitemaps before its first zips are built (every file then counts as changed).
    upd = st.setdefault("updates", {})
    n = 0
    for t in TYPES:
        if t not in st.get("zips", {}) and not current:
            continue
        raw, _ = get(f"{SITEMAP}/{congress}{t}/sitemap.xml", tries=1 if t not in st.get("zips", {}) else 3)
        if not raw:
            continue
        ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        zip_t = st.get("zips", {}).get(t, "")
        for u in ET.fromstring(raw).findall("s:url", ns):
            loc, lastmod = u.findtext("s:loc", "", ns), u.findtext("s:lastmod", "", ns)
            f = loc.rsplit("/", 1)[-1]
            lm = datetime.fromisoformat(lastmod.replace("Z", "+00:00")).isoformat() if lastmod else ""
            if not lm or lm <= zip_t or upd.get(f, "") >= lm:
                continue
            data, _ = get(loc)
            if data and data.lstrip().startswith(b"<?xml"):
                save(os.path.join(folder, "updates", f), data)
                upd[f] = lm
                n += 1
                if n % 100 == 0:
                    save_state(congress, st)
            time.sleep(0.5)
        time.sleep(1)
    save_state(congress, st)
    print(f"{congress}: {n} bills changed since the zips ({len(upd)} kept in updates/)")


def votes(deadline):
    """Each bill's own roll calls, member by member, one request a second, until the deadline."""
    n = left = 0
    for congress in CONGRESSES:
        folder = os.path.join(DATA, str(congress), "votes")
        os.makedirs(folder, exist_ok=True)
        absent = state(congress).get("absentVotes", [])
        wanted = sorted({(name, url) for _, (name, url) in C.wanted_votes(congress).items()})
        todo = [(name, url) for name, url in wanted if not os.path.exists(os.path.join(folder, name)) and name not in absent]
        for name, url in todo:
            if time.time() > deadline:
                left += 1
                continue
            data, _ = get(url)
            time.sleep(1)
            if data and b"<" in data[:200] and (b"rollcall-vote" in data[:400] or b"roll_call_vote" in data[:400]):
                save(os.path.join(folder, name), data)
                n += 1
            elif data is None:
                st = state(congress)
                st.setdefault("absentVotes", []).append(name)
                save_state(congress, st)
        print(f"{congress}: {len(wanted)} roll calls wanted, {len(wanted) - len(todo)} already here")
    print(f"roll calls: {n} read this run, {left} left for later runs")


def vetoes():
    """The President's veto messages the House printed as documents (BILLSTATUS names each: "printed as a House document
    (118-26)"), from GovInfo, https://www.govinfo.gov/content/pkg/CDOC-<congress>hdoc<n>/html/CDOC-<congress>hdoc<n>.htm
    (allowed: robots.txt bars only /core/, /profiles/ ...), each once, into data/us/<congress>/vetoes/hdoc<n>.htm. A few a
    Congress; one a second. A message that fails is tried again next run and never holds the copy back."""
    for congress in CONGRESSES:
        docs = C.veto_docs(congress)
        n = 0
        for doc in sorted(docs):
            path = C.veto_file(congress, doc)
            if os.path.exists(path):
                continue
            pkg = f"CDOC-{congress}hdoc{doc}"
            data, _ = get(f"https://www.govinfo.gov/content/pkg/{pkg}/html/{pkg}.htm")
            time.sleep(1)
            if data and b"VETO MESSAGE" in data.upper():
                os.makedirs(os.path.dirname(path), exist_ok=True)
                save(path, data)
                n += 1
        print(f"{congress}: {len(docs)} veto messages printed as House documents, {n} read this run")


def members():
    os.makedirs(os.path.join(DATA, "members"), exist_ok=True)
    for name, days in (("legislators-current", 0), ("committees-current", 0), ("committee-membership-current", 0),
                       ("legislators-historical", 6)):
        path = os.path.join(DATA, "members", f"{name}.json")
        if os.path.exists(path) and (time.time() - os.path.getmtime(path)) / 86400 < days:
            continue
        data, _ = get(f"{MEMBERS}/{name}.json")
        try:
            ok = data and len(json.loads(data)) > 10
        except ValueError:
            ok = False
        if ok:
            save(path, data)
        elif not os.path.exists(path):
            missing.append(f"members/{name}.json")
        time.sleep(1)


def main():
    sys.stdout.reconfigure(line_buffering=True)
    start = time.time()
    os.makedirs(DATA, exist_ok=True)
    for congress in CONGRESSES:
        bills(congress)
    members()
    try:  # never holds the run back
        vetoes()
    except Exception as e:  # noqa: BLE001
        print(f"veto messages: failed ({type(e).__name__}: {e})")
    votes(start + VOTE_MINUTES * 60 + (time.time() - start))
    marker = os.path.join(DATA, "incomplete")
    if missing:
        open(marker, "w").write("\n".join(missing) + "\n")
        print("never downloaded:", ", ".join(missing))
    elif os.path.exists(marker):
        os.remove(marker)


if __name__ == "__main__":
    main()
