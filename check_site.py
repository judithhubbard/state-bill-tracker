#!/usr/bin/env python3
"""Checks that statebilltracker.org's data is sound, after each update (.github/workflows/publish.yml runs it last, once a day,
so a problem fails the run and GitHub emails the owner; the site is already published by then).

- Each state's legislators were refreshed in the last 3 days, and there are about as many as there should be.
- New Jersey and California: the current session's bill texts ("What it does") are there.
- Virginia: the rule for its session dates (60 days in even years, 46 in odd, from the second Wednesday of
  January; states/va/profile.js) still fits: each finished session's last floor votes come within 10 days of the
  computed adjournment. If a year breaks the rule, add it to `dated` in states/va/profile.js.
- Each state's data is still updating (freshness(), below): its last successful download, its download step's recent
  runs, its newest bill action while its legislature is in session, and its bill count against the day before.
Problems fail the run (GitHub emails the owner); warnings are only written in the run's summary.
A failed download already fails the run before this.
Usage: python3 check_site.py            the checks
       python3 check_site.py --record   after each build (publish.yml): note each state's bill count and newest action in
                                        built/freshness.json, which the next day's check compares with
For a test, CHECK_DATA and CHECK_BUILT point at other data/ and built/ folders and CHECK_TODAY (YYYY-MM-DD) sets the day;
the download runs are read from GitHub only when GH_TOKEN or CHECK_RUNS=1 is set.
"""
import csv, json, os, re, sys
from datetime import date, datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.environ.get("CHECK_DATA") or os.path.join(HERE, "data")
BUILT = os.environ.get("CHECK_BUILT") or os.path.join(HERE, "built")
TODAY = date.fromisoformat(os.environ["CHECK_TODAY"]) if os.environ.get("CHECK_TODAY") else date.today()
NOW = datetime.combine(TODAY, datetime.now(timezone.utc).time(), timezone.utc) if os.environ.get("CHECK_TODAY") else datetime.now(timezone.utc)
problems = []
warnings = []
STATES_JSON = json.load(open(os.path.join(HERE, ".github", "states.json")))["states"]


# --- Freshness: is each state's data still updating? -----------------------------------------------------------------
# A download job can succeed while the data quietly stops changing (a source answering with old data, a copy that isn't
# saved, a converter dropping records), so each state is checked four ways, from what publish.yml has: the restored
# downloads (data/<st>/last_checked), the build it just made (built/<st>/data/status*.json: each bill's last action),
# built/freshness.json (each day's bill count, written by --record after every build and kept with the pages), and the
# download runs on GitHub.
DOWNLOAD_WARN_HOURS = 26   # a healthy state's mark is at most about 16 hours old (download.yml saves it every 12 hours)
DOWNLOAD_FAIL_HOURS = 48
LOG = os.path.join(BUILT, "freshness.json")


def state_name(st):
    try:
        m = re.search(r'^STATE_NAME = "([^"]+)"', open(os.path.join(HERE, "states", st, "profile.py")).read(), re.M)
    except OSError:
        m = None
    return m[1] if m else st.upper()


def short(d):
    d = date.fromisoformat(d[:10]) if isinstance(d, str) else d
    return f"{d:%b} {d.day}" + ("" if d.year == TODAY.year else f", {d.year}")


def days_text(n):
    return "1 day" if n == 1 else f"{n} days"


def built_states():
    if not os.path.isdir(BUILT):
        return []
    return sorted(st for st in os.listdir(BUILT) if os.path.exists(os.path.join(BUILT, st, "data", "status.json")))


def sessions(st, live_only=True):
    """The state's sessions in its last build, as (session, facts, rows): rows are its status file's bills (row[3] is the
    day of the bill's last action). live_only: only the current session and next year's prefiled bills."""
    out = []
    for s, v in sorted(json.load(open(os.path.join(BUILT, st, "data", "status.json"))).items()):
        f = v.get("f") or {}
        if live_only and not f.get("c", v.get("l")):
            continue
        path = os.path.join(BUILT, st, "data", f"status_{s}.json")
        if os.path.exists(path):
            d = json.load(open(path))
            out.append((s, f, Rows(d.get("bills") or {}, len(d.get("alias") or {}))))
    return out


class Rows(dict):
    """A status file's bills, with how many other numbers they answer to (2026-11-26: Virginia's identical House and
    Senate bills became one record each, and the bill count read 366 "lost"). count() is every bill number."""
    def __init__(self, bills, aliases):
        super().__init__(bills)
        self.aliases = aliases

    def count(self):
        return len(self) + self.aliases


def newest_action(rows):
    today = TODAY.isoformat()
    return max((r[3] for r in rows.values() if len(r) > 3 and r[3] and r[3] <= today), default="")


def record():
    """After each build: each state's live sessions' bill counts and newest action, one entry a day (the day's last
    build), three weeks kept. Never fails the publish."""
    try:
        log = json.load(open(LOG))
    except (OSError, ValueError):
        log = {}
    day, keep = TODAY.isoformat(), (TODAY - timedelta(21)).isoformat()
    for st in built_states():
        try:
            for s, f, rows in sessions(st):
                days = log.setdefault(st, {}).setdefault(s, [])
                days[:] = [d for d in days if keep <= d[0] < day] + [[day, rows.count(), newest_action(rows)]]
        except (OSError, ValueError, KeyError) as e:
            print(f"{st}: couldn't read its status files ({e})")
    for st in list(log):
        log[st] = {s: d for s, d in log[st].items() if any(x[0] >= keep for x in d)}
        if not log[st]:
            del log[st]
    with open(LOG + ".new", "w") as f:
        json.dump(log, f, separators=(",", ":"))
    os.replace(LOG + ".new", LOG)
    print(f"noted {sum(len(v) for v in log.values())} sessions in {LOG}")


def download_runs():
    """Each download job's Download step results, newest first ({job name: [(started, conclusion)]}), from the last 40
    download.yml runs; None when GitHub can't be asked."""
    if not (os.environ.get("GH_TOKEN") or os.environ.get("CHECK_RUNS")):
        return None
    import subprocess
    repo = os.environ.get("GITHUB_REPOSITORY") or "judithhubbard/state-bill-tracker"

    def api(path):
        out = subprocess.run(["gh", "api", path], capture_output=True, text=True)
        if out.returncode:
            raise RuntimeError(out.stderr.strip()[:200])
        return json.loads(out.stdout)
    try:
        jobs = {}
        for r in api(f"repos/{repo}/actions/workflows/download.yml/runs?status=completed&per_page=40")["workflow_runs"]:
            for j in api(f"repos/{repo}/actions/runs/{r['id']}/jobs?per_page=100")["jobs"]:
                step = next((s for s in j.get("steps") or [] if s.get("name") == "Download"), None)
                # A job a newer run bumped, or one that never reached the step, says nothing either way.
                if step and step.get("conclusion") in ("success", "failure"):
                    jobs.setdefault(j["name"], []).append((j.get("started_at") or "", step["conclusion"]))
        return {n: sorted(v, reverse=True) for n, v in jobs.items()}
    except (RuntimeError, ValueError, KeyError, OSError) as e:
        warnings.append(f"couldn't read the download runs from GitHub ({e}); their check was skipped")
        return None


def freshness():
    # 1. Downloads: each state's last successful download (download.yml writes data/<st>/last_checked after one, and
    # saves it at least every 12 hours). New York is check_fresh.py's (below).
    stale_jobs = set()
    for job in STATES_JSON:
        if job["code"] == "ny":
            continue
        folders = [p for p in job["paths"] if "*" not in p and not p.endswith(".json")]
        stamps = []
        for p in folders:
            try:
                stamps.append(datetime.fromisoformat(open(os.path.join(DATA, os.path.basename(p), "last_checked")).read().strip().replace("Z", "+00:00")))
            except (OSError, ValueError):
                pass
        first = any(os.path.exists(os.path.join(DATA, os.path.basename(p), "incomplete")) for p in folders)
        if not stamps:
            warnings.append(f"{job['name']}: no successful download saved yet (no last_checked in {', '.join(folders)})")
            continue
        last = max(stamps)
        hours = (NOW - last).total_seconds() / 3600
        when = f"{days_text(int(hours // 24))}" if hours >= 48 else f"{int(hours)} hours"
        line = f"{job['name']}: no successful download for {when} (the last was {short(last.date())})"
        if hours > DOWNLOAD_FAIL_HOURS and not first:
            problems.append(line + ": see its job in the Download state data runs")
            stale_jobs.add(job["name"])
        elif hours > DOWNLOAD_WARN_HOURS:
            warnings.append(line + (" (its first copy is still being built)" if first else ""))

    # 2. The download step's recent runs: failing every time (and the copy not yet two days old, or 1. said so), or
    # failing in half of them (the mark stays fresh from the runs that work).
    runs = download_runs()
    for name, results in sorted((runs or {}).items()):
        last = results[:12]
        failed = sum(c == "failure" for _, c in last)
        if name in stale_jobs or len(last) < 4 or not failed:
            continue
        if failed == len(last) and len(last) >= 6:
            problems.append(f"{name}: the download failed in each of its last {len(last)} runs (since {short(last[-1][0])})")
        elif failed * 2 >= len(last):
            warnings.append(f"{name}: the download failed in {failed} of its last {len(last)} runs")

    try:
        log = json.load(open(LOG))
    except (OSError, ValueError):
        log = {}
    if not log:
        warnings.append(f"no bill counts from earlier builds ({LOG}); the bill-count check starts tomorrow")
    year, today = TODAY.year, TODAY.isoformat()
    for st in built_states():
        if os.path.exists(os.path.join(DATA, st, "incomplete")):
            continue
        name = state_name(st)
        try:
            every = sessions(st, live_only=False)
        except (OSError, ValueError) as e:
            warnings.append(f"{name}: couldn't read its built status files ({e})")
            continue
        for s, f, rows in every:
            if not f.get("c"):
                continue
            # 3. Bill counts: a live session with fewer bills than at the last build of an earlier day lost records
            # somewhere (a download or converter dropping them). Bills rarely leave a session; a stray record dropped by
            # a fix is a few at most.
            before = [d for d in (log.get(st) or {}).get(s, []) if d[0] < today]
            if before:
                day, n0 = before[-1][0], before[-1][1]
                lost = n0 - rows.count()
                label = f"{name}: {rows.count():,} bills in its {s} session, {lost:,} fewer than on {short(day)} ({n0:,})"
                if lost >= 5 and lost >= 0.02 * n0:
                    problems.append(label + ": were bills lost in the download or the build?")
                elif lost >= 3:
                    warnings.append(label)

            # 4. Bill actions, while the legislature is in session: it has held floor votes this year (the facts' "v", the
            # session's last one so far) and it's before the day its session usually ends (this year's scheduled end, else
            # the latest of the past same-parity years' last big floor-vote days, "t": a two-year session's two years
            # differ, and Texas's even years have none). Out of session, and in January before the first floor votes,
            # nothing is checked. The quiet spells allowed come from the state's own past (recesses, Michigan's spring
            # break): the median of the past years' longest gaps between bills' last-action days, from February 1 to
            # that year's end, which overstates the real gaps (a bill's earlier actions aren't counted), plus a week.
            if f.get("u"):
                continue
            end = (f.get("e") or {}).get(str(year))
            if not end:
                same = [t for t in f.get("t") or [] if int(t[:4]) % 2 == year % 2]
                end = f"{year}-{max(t[5:] for t in same)}" if same else ""
            if not end or not (f"{year}-01-01" <= (f.get("v") or "") <= today <= end):
                continue
            newest = newest_action(rows)
            if not newest:
                continue
            age = (TODAY - date.fromisoformat(newest)).days
            days = sorted({r[3] for _, _, rr in every for r in rr.values() if len(r) > 3 and r[3]})
            gaps = []
            for t in f.get("t") or []:
                win = [date.fromisoformat(x) for x in days if f"{t[:4]}-02-01" <= x <= t]
                if len(win) > 1:
                    gaps.append(max((b - a).days for a, b in zip(win, win[1:])))
            gaps.sort()
            usual = gaps[(len(gaps) - 1) // 2] if gaps else 7
            fail_after = max(14, usual + 7)
            warn_after = max(7, fail_after // 2)
            line = (f"{name}: no new bill actions for {days_text(age)} (the newest is from {short(newest)}), though the "
                    f"legislature is in session (it usually ends about {short(end)})")
            if age > fail_after:
                problems.append(line + ": is the source still updating?")
            elif age > warn_after:
                warnings.append(line)


if "--record" in sys.argv:
    record()
    sys.exit(0)


# A session that began this year: until February 15 its member list may not exist yet or be partial (many legislatures
# publish theirs only once they organize in January), so a missing or short list isn't a problem then.
NEW_SESSION_GRACE = TODAY.month == 1 or (TODAY.month == 2 and TODAY.day <= 15)


def contacts(state, session, at_least):
    path = os.path.join(DATA, state, f"contacts_{session}.json")
    new = NEW_SESSION_GRACE and int(session) == TODAY.year
    if not os.path.exists(path):
        if not new:
            problems.append(f"{state}: no legislators file for {session}")
        return
    d = json.load(open(path))
    day = datetime.strptime(d.get("fetched", "1970-01-01")[:10], "%Y-%m-%d").date()
    if (TODAY - day).days > 3:
        problems.append(f"{state}: legislators last refreshed {day} (more than 3 days ago)")
    if len(d.get("people", {})) < at_least and not new:
        problems.append(f"{state}: only {len(d.get('people', {}))} legislators (expected at least {at_least})")


def va_opens(year):
    jan1 = date(year, 1, 1)
    return jan1 + timedelta((2 - jan1.weekday()) % 7 + 7)  # the second Wednesday


# New Jersey: two-year sessions starting in even years.
nj = TODAY.year if TODAY.year % 2 == 0 else TODAY.year - 1
contacts("nj", nj, 115)
if not os.path.exists(os.path.join(DATA, "nj", f"texts_{nj}.json")):
    problems.append(f"nj: no bill texts for {nj}")

# California: two-year sessions starting in odd years, and the bill texts ("What it does").
ca = TODAY.year if TODAY.year % 2 else TODAY.year - 1
contacts("ca", ca, 110)
if not os.path.exists(os.path.join(DATA, "ca", f"texts_{ca}.json")):
    problems.append(f"ca: no bill texts for {ca}")

# Illinois: two-year General Assemblies starting in odd years.
contacts("il", TODAY.year if TODAY.year % 2 else TODAY.year - 1, 170)

# Connecticut: a session a year.
contacts("ct", TODAY.year, 180)

# Ohio: two-year General Assemblies starting in odd years (contacts once its first full download is done).
if not os.path.exists(os.path.join(DATA, "oh", "incomplete")):
    contacts("oh", TODAY.year if TODAY.year % 2 else TODAY.year - 1, 120)

# Washington: two-year bienniums starting in odd years.
contacts("wa", TODAY.year if TODAY.year % 2 else TODAY.year - 1, 140)

# Massachusetts: two-year General Courts starting in odd years (contacts once its first full download is done).
if not os.path.exists(os.path.join(DATA, "ma", "incomplete")):
    contacts("ma", TODAY.year if TODAY.year % 2 else TODAY.year - 1, 190)

# Georgia: two-year General Assemblies starting in odd years (contacts once its first full download is done).
if not os.path.exists(os.path.join(DATA, "ga", "incomplete")):
    contacts("ga", TODAY.year if TODAY.year % 2 else TODAY.year - 1, 220)

# Michigan: two-year sessions starting in odd years (contacts once its first full download is done).
if not os.path.exists(os.path.join(DATA, "mi", "incomplete")):
    contacts("mi", TODAY.year if TODAY.year % 2 else TODAY.year - 1, 140)

# Wisconsin: two-year sessions starting in odd years (contacts once its first full download is done).
if not os.path.exists(os.path.join(DATA, "wi", "incomplete")):
    contacts("wi", TODAY.year if TODAY.year % 2 else TODAY.year - 1, 125)

# Arizona: a session a year (from Open States).
if not os.path.exists(os.path.join(DATA, "az", "incomplete")):
    contacts("az", TODAY.year, 85)

# North Carolina: two-year sessions starting in odd years (contacts once its first full download is done).
if not os.path.exists(os.path.join(DATA, "nc", "incomplete")):
    contacts("nc", TODAY.year if TODAY.year % 2 else TODAY.year - 1, 160)

# Colorado: a session a year.
if not os.path.exists(os.path.join(DATA, "co", "incomplete")):
    contacts("co", TODAY.year, 90)

# South Dakota: a session a year.
if not os.path.exists(os.path.join(DATA, "sd", "incomplete")):
    contacts("sd", TODAY.year, 100)

# Utah: a session a year.
if not os.path.exists(os.path.join(DATA, "ut", "incomplete")):
    contacts("ut", TODAY.year, 95)

# Indiana: a session a year.
if not os.path.exists(os.path.join(DATA, "in", "incomplete")):
    contacts("in", TODAY.year, 140)

# North Dakota: two-year Legislative Assemblies starting in odd years.
if not os.path.exists(os.path.join(DATA, "nd", "incomplete")):
    contacts("nd", TODAY.year if TODAY.year % 2 else TODAY.year - 1, 120)

# Nebraska: two-year Legislatures starting in odd years; one house of 49 senators.
if not os.path.exists(os.path.join(DATA, "ne", "incomplete")):
    contacts("ne", TODAY.year if TODAY.year % 2 else TODAY.year - 1, 45)

# Alaska: two-year Legislatures starting in odd years.
if not os.path.exists(os.path.join(DATA, "ak", "incomplete")):
    contacts("ak", TODAY.year if TODAY.year % 2 else TODAY.year - 1, 55)

# Arkansas: a session a year.
if not os.path.exists(os.path.join(DATA, "ar", "incomplete")):
    contacts("ar", TODAY.year, 120)

# New Hampshire: a session a year (two-year General Courts).
if not os.path.exists(os.path.join(DATA, "nh", "incomplete")):
    contacts("nh", TODAY.year, 350)

# Rhode Island: a session a year (from LegiScan).
if not os.path.exists(os.path.join(DATA, "ri", "incomplete")):
    contacts("ri", TODAY.year, 100)

# Vermont: two-year bienniums starting in odd years (from LegiScan).
if not os.path.exists(os.path.join(DATA, "vt", "incomplete")):
    contacts("vt", TODAY.year if TODAY.year % 2 else TODAY.year - 1, 170)

# Tennessee: two-year General Assemblies starting in odd years (from LegiScan).
if not os.path.exists(os.path.join(DATA, "tn", "incomplete")):
    contacts("tn", TODAY.year if TODAY.year % 2 else TODAY.year - 1, 125)

# Maine: two-year Legislatures starting in odd years (from LegiScan).
if not os.path.exists(os.path.join(DATA, "me", "incomplete")):
    contacts("me", TODAY.year if TODAY.year % 2 else TODAY.year - 1, 180)

# Oklahoma: two-year Legislatures starting in odd years (from LegiScan).
if not os.path.exists(os.path.join(DATA, "ok", "incomplete")):
    contacts("ok", TODAY.year if TODAY.year % 2 else TODAY.year - 1, 140)

if not os.path.exists(os.path.join(DATA, "id", "incomplete")): contacts("id", TODAY.year, 95)  # Idaho: a session a year
if not os.path.exists(os.path.join(DATA, "al", "incomplete")): contacts("al", TODAY.year, 130)  # Alabama: a session a year
if not os.path.exists(os.path.join(DATA, "ky", "incomplete")): contacts("ky", TODAY.year, 130)  # Kentucky: a session a year
if not os.path.exists(os.path.join(DATA, "la", "incomplete")): contacts("la", TODAY.year, 130)  # Louisiana: a session a year
if not os.path.exists(os.path.join(DATA, "ms", "incomplete")): contacts("ms", TODAY.year, 160)  # Mississippi: a session a year
if not os.path.exists(os.path.join(DATA, "de", "incomplete")): contacts("de", TODAY.year if TODAY.year % 2 else TODAY.year - 1, 55)  # Delaware: two-year General Assemblies
if not os.path.exists(os.path.join(DATA, "sc", "incomplete")): contacts("sc", TODAY.year if TODAY.year % 2 else TODAY.year - 1, 150)  # South Carolina: two-year General Assemblies
if not os.path.exists(os.path.join(DATA, "mn", "incomplete")): contacts("mn", TODAY.year if TODAY.year % 2 else TODAY.year - 1, 190)  # Minnesota: two-year Legislatures
if not os.path.exists(os.path.join(DATA, "mt", "incomplete")): contacts("mt", TODAY.year if TODAY.year % 2 else TODAY.year - 1, 140)  # Montana: two-year Legislatures, sessions in odd years
if not os.path.exists(os.path.join(DATA, "nm", "incomplete")): contacts("nm", TODAY.year, 100)  # New Mexico: a session a year
if not os.path.exists(os.path.join(DATA, "nv", "incomplete")): contacts("nv", TODAY.year if TODAY.year % 2 else TODAY.year - 1, 55)  # Nevada: regular sessions in odd years
if not os.path.exists(os.path.join(DATA, "mo", "incomplete")): contacts("mo", TODAY.year, 180)  # Missouri: a session a year
if not os.path.exists(os.path.join(DATA, "wv", "incomplete")): contacts("wv", TODAY.year, 125)  # West Virginia: a session a year
if not os.path.exists(os.path.join(DATA, "ks", "incomplete")): contacts("ks", TODAY.year if TODAY.year % 2 else TODAY.year - 1, 150)  # Kansas: two-year bienniums
if not os.path.exists(os.path.join(DATA, "dc", "incomplete")) and os.path.isdir(os.path.join(DATA, "dc", "legiscan")):
    contacts("dc", TODAY.year if TODAY.year % 2 else TODAY.year - 1, 12)  # the District: two-year Council Periods, 13 members
# Congress: two-year Congresses; a new one's member list (January 3 of odd years) can take a few days to reach the data.
if not os.path.exists(os.path.join(DATA, "us", "incomplete")) and not (TODAY.year % 2 and TODAY.month == 1 and TODAY.day < 15):
    contacts("us", TODAY.year if TODAY.year % 2 else TODAY.year - 1, 520)
# Congress's committee meetings (states/us/meetings.py, once it has a key): listed at least every 3 days.
_meet = os.path.join(HERE, "data", "us", "meetings.json")
if os.path.exists(_meet):
    _listed = json.load(open(_meet)).get("listed", "")[:10]
    if not _listed or (TODAY - date.fromisoformat(_listed)).days > 3:
        problems.append(f"us: committee meetings last listed {_listed or 'never'} (more than 3 days ago; states/us/meetings.py, "
                        "the CONGRESS_API_KEY secret)")

# Wyoming: a session a year.
if not os.path.exists(os.path.join(DATA, "wy", "incomplete")):
    contacts("wy", TODAY.year, 85)

# Maryland: a session a year.
contacts("md", TODAY.year, 180)

# Pennsylvania: two-year sessions starting in odd years.
contacts("pa", TODAY.year if TODAY.year % 2 else TODAY.year - 1, 240)

# Oregon: a regular session a year.
contacts("or", TODAY.year, 85)

# Texas: regular sessions in odd years.
contacts("tx", TODAY.year if TODAY.year % 2 else TODAY.year - 1, 170)

# Virginia: a session a year.
contacts("va", TODAY.year, 130)
for year in range(TODAY.year - 2, TODAY.year + 1):
    path = os.path.join(DATA, "va", f"{year}1", "HISTORY.CSV")
    adjourns = va_opens(year) + timedelta((46 if year % 2 else 60) - 1)
    if not os.path.exists(path) or TODAY <= adjourns + timedelta(25):
        continue
    last = ""
    with open(path, encoding="cp1252", errors="replace", newline="") as f:
        for r in csv.DictReader(f, skipinitialspace=True):
            # Passage votes only ("H Read third time and passed House (64-Y ...)", "S Passed Senate"), not the
            # "Bill text as passed House and Senate" lines added when bills are enrolled weeks later.
            if re.match(r"[HS] (?:Read third time and )?passed (House|Senate)\b", r.get("History_description", ""), re.I):
                m = re.match(r"(\d+)/(\d+)/(\d{4})|(\d{4})-(\d\d)-(\d\d)", r.get("History_date", ""))
                if m:
                    d = date(int(m[3]), int(m[1]), int(m[2])) if m[1] else date(int(m[4]), int(m[5]), int(m[6]))
                    # The April reconvened session, five or six weeks later, is separate.
                    if d <= adjourns + timedelta(25):
                        last = max(last, d.isoformat())
    if last and abs((date.fromisoformat(last) - adjourns).days) > 10:
        problems.append(f"va: {year}'s last floor votes were on {last}, but the rule says it adjourned {adjourns}; "
                        "add the year to `dated` in states/va/profile.js")

# Leaders: the pages show the profile's (states/<st>/profile.py LEADERS, with LEADERS_NEXT from each one's first day).
# These states' contacts.py read the legislature's own leadership pages; when those name someone else, the profile
# needs checking (a new Speaker or President), so it fails here rather than going unnoticed.
OWN_LEADERS = ("ca", "fl", "ma", "va")
sys.path.insert(0, HERE)
import importlib, governors
def _key(name):
    return re.sub(r"[^a-z ]", "", name.lower().replace(".", " ")).split()[-1] if name.strip() else ""
for st in OWN_LEADERS:
    P = importlib.import_module(f"states.{st}.profile")
    governors.apply_leaders(P)
    files = sorted(f for f in os.listdir(os.path.join(DATA, st)) if re.fullmatch(r"contacts_\d{4}\.json", f)) \
        if os.path.isdir(os.path.join(DATA, st)) else []
    if not files:
        continue
    listed = json.load(open(os.path.join(DATA, st, files[-1]))).get("leaders", {})
    for h, v in listed.items():
        mine = P.LEADERS.get(h)
        if mine and _key(v.get("name", "")) and _key(v["name"]) != _key(mine[0]):
            problems.append(f"{st}: the legislature's site names {v['name']} ({v.get('role', h)}); the profile has "
                            f"{mine[0]}: update LEADERS (or LEADERS_NEXT) in states/{st}/profile.py")

# Every state in .github/states.json (what download.yml downloads) must be restored by publish.yml, or its saved
# copy never reaches the site.
states_list = json.load(open(os.path.join(HERE, ".github", "states.json")))["states"]
publish = open(os.path.join(HERE, ".github", "workflows", "publish.yml")).read()
for st in states_list:
    if f"restore-keys: {st['key']}-" not in publish:
        problems.append(f"{st['code']}: in .github/states.json but publish.yml doesn't restore {st['key']}")

# New York: its own freshness check (check_fresh.py: bills, Assembly votes, contacts, agendas, the session calendar), with
# the problems its last download noted (states/ny/fetch.py).
import subprocess
_y = datetime.now().year
_ny = subprocess.run([sys.executable, os.path.join(HERE, "check_fresh.py"), str(_y if _y % 2 else _y - 1),
                      os.path.join(DATA, "ny", "problems.txt")], capture_output=True, text=True)
if _ny.returncode:
    problems += [f"ny: {l[2:]}" for l in _ny.stdout.splitlines() if l.startswith("- ")] or [f"ny: check_fresh.py failed: {_ny.stderr.strip()[-300:]}"]

# Each state's data still updating (freshness(), above).
freshness()

report = ("## Problems\n\n" + "\n".join(f"- {p}" for p in problems) + "\n") if problems else "## Data looks sound\n"
if warnings:
    report += "\n## Worth a look (not failing the run)\n\n" + "\n".join(f"- {w}" for w in warnings) + "\n"
print(report)
if os.environ.get("GITHUB_STEP_SUMMARY"):
    with open(os.environ["GITHUB_STEP_SUMMARY"], "a") as f:
        f.write(report)
    for w in warnings:
        print(f"::warning::{w}")
sys.exit(1 if problems else 0)
