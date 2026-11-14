#!/usr/bin/env python3
"""Download bills from LegiScan's API (https://api.legiscan.com/) for the states whose legislatures' websites turn
automated requests away in robots.txt: Tennessee, Oklahoma, Maine, Rhode Island and Vermont. LegiScan's data is
CC BY 4.0: the pages built from it must credit LegiScan.

The key (env LEGISCAN_API_KEY, or ~/.legiscan_api_key) travels in the address, so no message here prints an address,
and every error is scrubbed of the key before it's printed. Never write it to a file in this (public) repository.

LegiScan's rules (breaking them gets the key suspended), kept as hard limits:
- The free tier allows 10,000 queries a month: every query is counted in data/legiscan/usage.json ({"2026-11": n})
  before it's sent, and the run stops cleanly at 9,000 in a month. 0.6 seconds between requests.
- getDatasetList at most once a day per state (its answer is kept with the date in data/legiscan/datasetlist_<st>.json).
- getDataset (each session's weekly zip, made Sundays) only when the list's dataset_hash differs from the saved one.
- Between Sundays, for a session still running: getMasterList (not ...Raw, which lacks the status; one query either
  way) at most once an hour, so every run: each bill's change_hash, status, status date and last action go into
  meta.json (the bill's "ml"), and the converters bring an older saved copy up to date from it
  (legiscan_convert.bills() adds the last action to its history), so stages never wait for the full record.
- getBill (the full record: history, votes, sponsors) only for bills whose change_hash differs from the saved copy,
  never one bill twice within 3 hours, within a daily allowance (`allowance()`): what's left of the month at the day's
  first run (UTC), less MARGIN (300), a reserve for the Sundays left (each wanted session's dataset and each state's
  people) and the fixed queries of the days left (5 dataset lists, and each running session's master list at
  RUNS_PER_DAY = 12 runs), divided by the days left, today included; what a day leaves goes to the days after. The
  queue (all running sessions together): first bills whose status changed or whose last action is a passage, floor
  vote, concurrence, the governor, a law or a veto (these may spend the whole day's allowance at any run); then bills
  never saved (new), then minor changes, most recent first, paced through the day (the share of the day so far). What
  isn't read comes with Sunday's dataset. getRollCall only for roll calls not saved yet (they never change), counted
  in the allowance; getSessionPeople at most once a week, when a bill names someone not saved. usage.json's "day"
  holds the day's starting count and its getBill/getRollCall reads.
- No bill texts (getBillText) and never legiscan.com's pages.

In session (five running sessions): about 65 fixed queries a day (5 lists + 12 x 5 master lists), ~2,000 a month, about
20 each Sunday for datasets and people, and the rest (about 220 a day) for full records when bills change: the month
ends near 8,700 at most.

What's kept, per state: the regular sessions (special sessions left out) that end this year or in the two years
before and start no later than this year, in data/<st>/legiscan/<session_id>/ with the dataset's own layout:
bill/<bill_number>.json, vote/<roll_call_id>.json, people/<people_id>.json (each as LegiScan gives it: {"bill": ...},
{"roll_call": ...}, {"person": ...}), plus meta.json (the session, dataset_hash and date, the last master list's time,
each bill's number, change_hash, when it was last read and the master list's "ml"). data/<st>/incomplete says "running"
during a run, then lists the sessions that have opened (OPENS: each state's opening day) and whose dataset was never
downloaded; a session not yet open (prefiled bills in January) is downloaded when listed but never holds the state off
the site, nor do bills waiting for their full record or a failed refresh (the last copy stays). FETCH_MINUTES (set by
the workflow) stops the run five minutes before it.

--dry-run prints what a run would request today from the saved files (dataset lists, datasets, master lists, the
allowance and how many full records it would read), with no key, no queries and nothing written; --today=YYYY-MM-DD
pretends another day.

Usage: python3 legiscan.py [--dry-run [--today=YYYY-MM-DD]] tn [ok me ri vt]
"""
import base64, io, json, os, re, sys, time, urllib.error, urllib.parse, urllib.request, zipfile
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(ROOT, "data")
SHARED = os.path.join(DATA, "legiscan")
USAGE = os.path.join(SHARED, "usage.json")
API = "https://api.legiscan.com/"
AGENT = "statebilltracker.org (a nonprofit bill tracker; contact via github.com/judithhubbard)"
STATES = ("tn", "ok", "me", "ri", "vt")
MONTHLY_STOP = 9000      # LegiScan's free tier allows 10,000 a month
PAUSE = 0.6              # seconds between requests
MASTERLIST_EVERY = 3600  # once an hour per session
BILL_EVERY = 3 * 3600    # one bill at most every three hours
PEOPLE_EVERY = 7 * 86400 # once a week
RUNS_PER_DAY = 12        # download.yml runs every two hours
MARGIN = 300             # kept back from the daily allowances (retries, a late Sunday), so the stop isn't reached
TODAY = date.today()     # (a dry run can pretend another day: --today=YYYY-MM-DD)
YEAR = TODAY.year
PRETEND = False


def nth(year, month, weekday, n=1):
    """The n-th weekday (0 Monday ... 6 Sunday) of a month."""
    first = date(year, month, 1)
    return date.fromordinal(first.toordinal() + (weekday - first.weekday()) % 7 + 7 * (n - 1))


# When each state's regular session opens, by the LegiScan session's first year. A session that hasn't begun is
# downloaded when LegiScan has it (prefiled bills), but never marks the state incomplete.
OPENS = {
    "tn": lambda y: nth(y, 1, 1, 2),                     # second Tuesday of January
    "ok": lambda y: nth(y, 2, 0, 1),                     # first Monday of February (odd years' organizational day in
                                                         # January doesn't take up bills)
    "me": lambda y: nth(y - 1, 12, 2, 1) if y % 2 else nth(y, 1, 2, 1),  # a new Legislature (odd first year): the first
                                                         # Wednesday of December after the election; else early January
    "ri": lambda y: nth(y, 1, 1, 1),                     # first Tuesday of January
    "vt": lambda y: nth(y, 1, 0, 1) + timedelta(days=2),  # the Wednesday after the first Monday of January
}


def begun(st, ds):
    """Whether the session has opened (today on or after its opening day)."""
    return TODAY >= OPENS[st](int(ds["year_start"]))

START = time.time()
BUDGET = max(0.0, float(os.environ.get("FETCH_MINUTES") or 0) - 5) * 60
LAST = [0.0]


class Stop(Exception):
    """A reason to stop the whole run cleanly: the monthly limit, a refused key, an answer that isn't OK."""


def out_of_time():
    return BUDGET and time.time() - START > BUDGET


def load_key():
    key = (os.environ.get("LEGISCAN_API_KEY") or "").strip()
    if not key:
        try:
            key = open(os.path.expanduser("~/.legiscan_api_key")).read().strip()
        except OSError:
            pass
    if not key:
        sys.exit("No LegiScan key: set LEGISCAN_API_KEY or write it to ~/.legiscan_api_key")
    return key


KEY = None


def scrub(text):
    text = str(text)
    if KEY:
        text = text.replace(KEY, "<key>").replace(urllib.parse.quote(KEY), "<key>")
    return re.sub(r"key=[^&\s'\"]+", "key=<key>", text)


def read_json(path, default=None):
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def write_json(path, obj, **kw):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(obj, f, **kw)
    os.replace(tmp, path)


def month():
    return datetime.now(timezone.utc).strftime("%Y-%m")


def used():
    return (read_json(USAGE, {}) or {}).get(month(), 0)


def count_query():
    """Count a query before it's sent; refuse past the month's limit."""
    usage = read_json(USAGE, {}) or {}
    n = usage.get(month(), 0)
    if n >= MONTHLY_STOP:
        raise Stop(f"LegiScan: {n} queries this month already; stopping at {MONTHLY_STOP} (the free tier allows 10,000)")
    usage[month()] = n + 1
    write_json(USAGE, usage, indent=1, sort_keys=True)


def query(op, **params):
    """One API answer (a dict whose status is "OK"). Raises Stop when the answer isn't OK or the key is refused;
    returns None after three failed tries (network trouble)."""
    url = API + "?" + urllib.parse.urlencode({"key": KEY, "op": op, **params})
    for attempt in range(3):
        wait = PAUSE - (time.time() - LAST[0])
        if wait > 0:
            time.sleep(wait)
        count_query()
        LAST[0] = time.time()
        try:
            req = urllib.request.Request(url, headers={"User-Agent": AGENT})
            with urllib.request.urlopen(req, timeout=300) as r:
                body = r.read()
            answer = json.loads(body)
        except urllib.error.HTTPError as e:
            if e.code in (401, 403):
                raise Stop(f"LegiScan {op}: refused (HTTP {e.code})")
            print(scrub(f"LegiScan {op}: HTTP {e.code}; trying again"), flush=True)
            time.sleep(10 * (attempt + 1))
            continue
        except (OSError, ValueError) as e:
            print(scrub(f"LegiScan {op}: {e.__class__.__name__} {e}; trying again"), flush=True)
            time.sleep(10 * (attempt + 1))
            continue
        if not isinstance(answer, dict) or answer.get("status") != "OK":
            alert = answer.get("alert", {}).get("message") if isinstance(answer, dict) else None
            raise Stop(scrub(f"LegiScan {op}: status {answer.get('status') if isinstance(answer, dict) else '?'}"
                             + (f" ({alert})" if alert else "")))
        return answer
    return None


def dataset_list(st):
    """The state's datasets: from today's saved answer, else one getDatasetList."""
    path = os.path.join(SHARED, f"datasetlist_{st}.json")
    saved = read_json(path)
    today = TODAY.isoformat()
    if saved and saved.get("date") == today:
        return saved["datasetlist"]
    answer = query("getDatasetList", state=st.upper())
    if answer is None:
        return saved["datasetlist"] if saved else None
    write_json(path, {"date": today, "datasetlist": answer["datasetlist"]}, indent=1)
    return answer["datasetlist"]


def wanted(datasets):
    """Regular sessions ending this year or in the two before, and starting no later than this year."""
    return sorted((d for d in datasets if not int(d.get("special") or 0)
                   and int(d["year_end"]) >= YEAR - 2 and int(d["year_start"]) <= YEAR),
                  key=lambda d: -int(d["year_start"]))


def bill_entry(meta, bill, fetched):
    """The saved copy's number, change_hash and read time (the master list's "ml" stays)."""
    e = meta["bills"].setdefault(str(bill["bill_id"]), {})
    e.update({"number": bill["bill_number"], "change_hash": bill.get("change_hash"), "fetched": fetched})


def safe_name(name):
    return re.sub(r"[^A-Za-z0-9_.-]", "_", str(name))


def take_dataset(folder, meta, ds):
    """Download and unpack a session's dataset. A bill read on its own since the dataset was made keeps that copy."""
    answer = query("getDataset", id=ds["session_id"], access_key=ds["access_key"])
    if answer is None:
        return False
    raw = base64.b64decode(answer["dataset"]["zip"])
    made = datetime.strptime(ds.get("dataset_date") or "1970-01-01", "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp()
    counts = {"bill": 0, "vote": 0, "people": 0, "kept": 0}
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        for name in z.namelist():
            parts = name.split("/")
            if len(parts) < 2 or not parts[-1].endswith(".json") or parts[-2] not in ("bill", "vote", "people"):
                continue
            kind = parts[-2]
            data = json.loads(z.read(name))
            if kind == "bill":
                bill = data["bill"]
                old = meta["bills"].get(str(bill["bill_id"]))
                if old and old.get("fetched", 0) > made + 86400 and old.get("change_hash") != bill.get("change_hash") \
                        and os.path.exists(os.path.join(folder, "bill", safe_name(bill["bill_number"]) + ".json")):
                    counts["kept"] += 1  # read on its own after this dataset was made
                    continue
                out = os.path.join(folder, "bill", safe_name(bill["bill_number"]) + ".json")
                bill_entry(meta, bill, made)
            elif kind == "vote":
                out = os.path.join(folder, "vote", f"{data['roll_call']['roll_call_id']}.json")
            else:
                out = os.path.join(folder, "people", f"{data['person']['people_id']}.json")
            os.makedirs(os.path.dirname(out), exist_ok=True)
            with open(out, "wb") as f:
                f.write(z.read(name))
            counts[kind] += 1
    meta["dataset_hash"] = ds["dataset_hash"]
    meta["dataset_date"] = ds.get("dataset_date")
    print(f"  dataset of {ds.get('dataset_date')}: {counts['bill']} bills, {counts['vote']} roll calls, "
          f"{counts['people']} people" + (f"; {counts['kept']} newer bills kept" if counts["kept"] else ""), flush=True)
    return True


def running(ds):
    """A session still meeting: its bills are caught up between Sundays."""
    return int(ds["year_end"]) >= YEAR and not int(ds.get("sine_die") or 0)


def utc_today():
    return TODAY if PRETEND else datetime.now(timezone.utc).date()


def allowance():
    """(the day's allowance for getBill and getRollCall, those already made today, how it was worked out). The allowance
    is what's left of the month at the day's first run, less a reserve for the Sundays left (each wanted session's dataset
    and each state's people) and for the fixed queries of the days left (each state's dataset list, and each running
    session's master list at every run), shared among the days left, today included. What one day leaves unspent goes
    to the days after."""
    today = utc_today()
    usage = read_json(USAGE, {}) or {}
    day = usage.get("day") or {}
    start = day.get("start", used()) if day.get("date") == today.isoformat() else used()
    spent = day.get("reads", 0) if day.get("date") == today.isoformat() else 0
    nxt = date(today.year + today.month // 12, today.month % 12 + 1, 1)
    days = (nxt - today).days
    sundays = sum(1 for k in range(days) if (today.toordinal() + k) % 7 == 0)  # (toordinal() % 7 == 0: Sunday)
    sessions = runs = 0
    for st in STATES:
        saved = read_json(os.path.join(SHARED, f"datasetlist_{st}.json")) or {}
        ws = wanted(saved.get("datasetlist") or [])
        sessions += len(ws)
        runs += sum(1 for d in ws if running(d))
    reserve = sundays * (sessions + len(STATES))
    fixed = days * (len(STATES) + RUNS_PER_DAY * runs)
    each = max(0, (MONTHLY_STOP - MARGIN - start - reserve - fixed) // days)
    how = (f"{MONTHLY_STOP:,} - {MARGIN} margin - {start:,} used before today - {reserve} for {sundays} Sundays - {fixed:,} fixed "
           f"({len(STATES)} lists + {RUNS_PER_DAY} runs x {runs} running sessions, x {days} days), / {days} days")
    return each, spent, how


def count_read(n=1):
    """Count getBill and getRollCall queries against the day's allowance (usage.json's "day")."""
    usage = read_json(USAGE, {}) or {}
    today = utc_today().isoformat()
    day = usage.get("day") or {}
    if day.get("date") != today:
        day = {"date": today, "start": usage.get(month(), 0), "reads": 0}
    day["reads"] = day.get("reads", 0) + n
    usage["day"] = day
    write_json(USAGE, usage, indent=1, sort_keys=True)


def mark_day():
    """Note the month's count at the day's first run (the allowance is worked out from it)."""
    usage = read_json(USAGE, {}) or {}
    today = utc_today().isoformat()
    if (usage.get("day") or {}).get("date") != today:
        usage["day"] = {"date": today, "start": usage.get(month(), 0), "reads": 0}
        write_json(USAGE, usage, indent=1, sort_keys=True)


# A last action that moves a bill along (a passage, a floor or concurrence vote, the governor, a law or a veto) puts
# it first in line for its full record (its roll calls and full history); one whose status changed, too.
MAJOR = re.compile(r"pass|third reading|3rd reading|ayes|yeas|nays|concur|conference|enrol|governor|sign|veto|override|"
                   r"chapter|public (?:law|act|ch)|became law|adopted|failed|defeated|withdrawn", re.I)


def take_masterlist(meta, session_id):
    """One getMasterList (at most hourly): each bill's change_hash, status, status date and last action, kept in
    meta.json as the bill's "ml" (the converters bring an older saved copy up to date from it: legiscan_convert.bills()).
    Returns False when it wasn't read (within the hour, or a failure)."""
    if time.time() - meta.get("masterlist_time", 0) < MASTERLIST_EVERY:
        print("  master list read within the hour; skipped")
        return False
    answer = query("getMasterList", id=session_id)
    if answer is None:
        return False
    meta["masterlist_time"] = time.time()
    n = 0
    for k, e in answer["masterlist"].items():
        if k == "session" or not isinstance(e, dict) or not e.get("bill_id"):
            continue
        entry = meta["bills"].setdefault(str(e["bill_id"]), {"number": e.get("number")})
        entry["ml"] = {f: e.get(f) for f in ("change_hash", "status", "status_date", "last_action", "last_action_date")}
        n += 1
    print(f"  master list: {n} bills", flush=True)
    return True


def queue(folder, meta, session_id):
    """The session's bills whose full record is older than the master list, as (tier, -last action day, ...): 0 a status
    change or a major action, 1 a bill never saved, 2 a minor change (waits for leftover allowance or Sunday's dataset)."""
    out = []
    for bid, e in meta["bills"].items():
        ml = e.get("ml") or {}
        if not ml.get("change_hash") or ml["change_hash"] == e.get("change_hash"):
            continue
        if not e.get("change_hash"):
            tier, why = 1, "new"
        else:
            saved = (read_json(os.path.join(folder, "bill", safe_name(e.get("number")) + ".json")) or {}).get("bill") or {}
            moved = ml.get("status") not in (None, saved.get("status"))
            tier, why = (0, "status" if moved else "major") if moved or MAJOR.search(ml.get("last_action") or "") else (2, "minor")
        day = (ml.get("last_action_date") or "")[:10]
        out.append((tier, -int(day.replace("-", "") or 0), session_id, int(bid), why, folder, meta))
    return out


def read_bills(todo, dry=False):
    """getBill for the queued bills in order, within the day's allowance: the first tier may spend all of it at any run,
    the others only their share of the day so far (a run every two hours), so a busy morning leaves room for the
    afternoon's floor votes. Each bill's roll calls not saved yet come with it (they never change) and count too.
    Returns the people named who aren't saved yet ({folder: set})."""
    each, spent, how = allowance()
    hour = 12 if PRETEND else datetime.now(timezone.utc).hour
    paced = -(-each * min(24, hour + 2) // 24)
    print(f"Daily allowance for full bill records: {each} ({how}); {spent} used today; "
          f"minor changes and new bills up to {paced} by this hour", flush=True)
    todo = sorted(todo, key=lambda t: t[:4])
    tiers = defaultdict(int)
    for t in todo:
        tiers[t[4]] += 1
    print("  waiting: " + (", ".join(f"{n} {w}" for w, n in sorted(tiers.items())) or "none"), flush=True)
    new_people = defaultdict(set)
    got = skipped = 0
    for tier, _, sid, bid, why, folder, meta in todo:
        if out_of_time():
            break
        if spent >= (each if tier == 0 else paced):
            break
        entry = meta["bills"][str(bid)]
        if time.time() - entry.get("fetched", 0) < BILL_EVERY:
            skipped += 1
            continue  # read within three hours: a later run
        if dry:
            spent += 1
            got += 1
            continue
        answer = query("getBill", id=bid)
        spent += 1
        count_read()
        if answer is None:
            continue
        bill = answer["bill"]
        write_json(os.path.join(folder, "bill", safe_name(bill["bill_number"]) + ".json"), {"bill": bill})
        bill_entry(meta, bill, time.time())
        got += 1
        for v in bill.get("votes") or []:
            path = os.path.join(folder, "vote", f"{v['roll_call_id']}.json")
            if os.path.exists(path) or out_of_time():
                continue
            rc = query("getRollCall", id=v["roll_call_id"])
            spent += 1
            count_read()
            if rc is None:
                continue
            write_json(path, {"roll_call": rc["roll_call"]})
            for m in rc["roll_call"].get("votes") or []:
                new_people[folder].add(m.get("people_id"))
        for s in bill.get("sponsors") or []:
            new_people[folder].add(s.get("people_id"))
        if got % 25 == 0:
            write_json(os.path.join(folder, "meta.json"), meta, indent=1)
    verb = "would read" if dry else "read"
    print(f"  {got} bills {verb}" + (" (roll calls not counted)" if dry else "") +
          (f"; {skipped} read within 3 hours wait" if skipped else "") +
          f"; {len(todo) - got - skipped} wait for a later day or Sunday's dataset", flush=True)
    return new_people


def take_people(folder, meta, session_id, missing):
    if time.time() - meta.get("people_time", 0) < PEOPLE_EVERY:
        print(f"  {len(missing)} people not saved yet; the session's people are read once a week")
        return
    if out_of_time():
        return
    answer = query("getSessionPeople", id=session_id)
    if answer is not None:
        meta["people_time"] = time.time()
        for p in answer["sessionpeople"]["people"]:
            write_json(os.path.join(folder, "people", f"{p['people_id']}.json"), {"person": p})
        print(f"  people: {len(answer['sessionpeople']['people'])} read", flush=True)


def prepare_state(st, sessions, dry=False):
    """One state's dataset list, datasets and running sessions' master lists. Adds each running session to `sessions`
    as (folder, meta, session_id). Returns the parts left undone (sessions never downloaded)."""
    undone = []
    base = os.path.join(DATA, st, "legiscan")
    if dry:
        path = os.path.join(SHARED, f"datasetlist_{st}.json")
        saved = read_json(path) or {}
        fresh = saved.get("date") == TODAY.isoformat()
        print(f"{st.upper()}: getDatasetList " + ("already read today" if fresh else "x1"))
        datasets = saved.get("datasetlist")
    else:
        datasets = dataset_list(st)
    if datasets is None:
        return ["datasetlist"]
    for ds in wanted(datasets):
        sid = ds["session_id"]
        folder = os.path.join(base, str(sid))
        meta_path = os.path.join(folder, "meta.json")
        meta = read_json(meta_path) or {"bills": {}}
        # Only a session never downloaded holds the state off the site, and only once it has begun; a failed refresh
        # keeps the last dataset.
        holds = not meta.get("dataset_hash") and begun(st, ds)
        read_once = not holds
        if dry:
            note = ("getDataset x1 if listed (never read" + ("" if holds else f"; opens {OPENS[st](int(ds['year_start']))}, "
                    "so it can't mark the state incomplete") + ")") if not meta.get("dataset_hash") else \
                "getDataset x1 (saved list's hash is newer)" if meta.get("dataset_hash") != ds["dataset_hash"] else \
                "dataset unchanged in the saved list (getDataset only if today's list has a new hash: Sundays)"
            run = running(ds)
            ml = "" if not run else ("; getMasterList x1" if time.time() - meta.get("masterlist_time", 0) >= MASTERLIST_EVERY
                                     else "; master list read within the hour")
            print(f"  {ds['session_name']} ({sid}, {ds['year_start']}-{ds['year_end']}"
                  f"{', running' if run else ', over'}): {note}{ml}")
            if holds:
                undone.append(f"{sid}:dataset")
            if run:
                sessions.append((folder, meta, sid))
            continue
        if out_of_time():
            if not read_once:
                undone.append(f"{sid}:time")
            continue
        meta["session"] = {k: ds.get(k) for k in ("session_id", "state_id", "year_start", "year_end", "session_name",
                                                  "session_title", "special", "sine_die", "prior")}
        print(f"{st.upper()} {ds['session_name']} (session {sid}, {ds['year_start']}-{ds['year_end']})", flush=True)
        try:
            if meta.get("dataset_hash") != ds["dataset_hash"]:
                if not take_dataset(folder, meta, ds):
                    if not read_once:
                        undone.append(f"{sid}:dataset")
                    continue
                write_json(meta_path, meta, indent=1)
            else:
                print(f"  dataset unchanged ({ds.get('dataset_date')})")
            # A session over waits for the weekly datasets; the running ones are caught up.
            if running(ds):
                take_masterlist(meta, sid)
                sessions.append((folder, meta, sid))
        finally:
            write_json(meta_path, meta, indent=1)
    return undone


def never_read(st):
    """The sessions (from the last saved dataset list) whose dataset was never downloaded: what keeps the marker when a
    run stops early."""
    saved = read_json(os.path.join(SHARED, f"datasetlist_{st}.json"))
    if not saved:
        return ["datasetlist"]
    return [f"{d['session_id']}:dataset" for d in wanted(saved["datasetlist"])
            if begun(st, d) and not (read_json(os.path.join(DATA, st, "legiscan", str(d["session_id"]), "meta.json")) or {}).get("dataset_hash")]


def main():
    global KEY, TODAY, YEAR, PRETEND
    args = [a.lower() for a in sys.argv[1:]]
    dry = "--dry-run" in args
    pretend = [a.split("=", 1)[1] for a in args if a.startswith("--today=")]
    states = [a for a in args if not a.startswith("--")]
    if not states or any(s not in STATES for s in states) or (pretend and not dry):
        sys.exit(f"Usage: python3 legiscan.py [--dry-run [--today=YYYY-MM-DD]] {' '.join(STATES)}   (one or more)")
    if dry:
        if pretend:
            TODAY, PRETEND = date.fromisoformat(pretend[0]), True
            YEAR = TODAY.year
        print(f"Dry run{' for ' + TODAY.isoformat() if pretend else ''}: no queries, nothing written. "
              f"LegiScan queries this month so far: {used():,} of {MONTHLY_STOP:,}")
        sessions = []
        for st in states:
            undone = prepare_state(st, sessions, dry=True)
            print(f"  {st.upper()} would be " + (f"incomplete ({' '.join(undone)}) unless today's list and datasets fill it"
                                                 if undone else "complete (on the site)"))
        todo = [t for folder, meta, sid in sessions for t in queue(folder, meta, sid)]
        print(f"Running sessions: {len(sessions)}; bills behind the saved master lists: {len(todo)}"
              " (today's master lists may show more)")
        read_bills(todo, dry=True)
        return
    KEY = load_key()
    mark_day()
    stopped = None
    undone = {}
    sessions = []
    for st in states:
        marker = os.path.join(DATA, st, "incomplete")
        os.makedirs(os.path.dirname(marker), exist_ok=True)
        if not os.path.exists(marker):
            with open(marker, "w") as f:
                f.write("running\n")
        # A run stopped early (the month's limit, an error) leaves the saved copies as they were: only sessions never
        # downloaded keep the state off the site.
        if stopped:
            undone[st] = never_read(st)
            continue
        try:
            undone[st] = prepare_state(st, sessions)
        except Stop as e:
            stopped = str(e)
            print(stopped, flush=True)
            undone[st] = never_read(st)
        except Exception as e:  # never let a message carry the key
            print(scrub(f"{st.upper()}: {e.__class__.__name__} {e}"), flush=True)
            undone[st] = never_read(st)
    # Full records for all the running sessions together, most important first (no state's backlog crowds out
    # another's floor votes), then people. Bills not read now are shown from the master list and complete on Sunday.
    if sessions and not stopped:
        try:
            todo = [t for folder, meta, sid in sessions for t in queue(folder, meta, sid)]
            new_people = read_bills(todo)
            for folder, meta, sid in sessions:
                missing = {p for p in new_people.get(folder, ()) if p and not os.path.exists(os.path.join(folder, "people", f"{p}.json"))}
                if missing:
                    take_people(folder, meta, sid, missing)
        except Stop as e:
            stopped = str(e)
            print(stopped, flush=True)
        except Exception as e:
            print(scrub(f"bills: {e.__class__.__name__} {e}"), flush=True)
        finally:
            for folder, meta, sid in sessions:
                write_json(os.path.join(folder, "meta.json"), meta, indent=1)
    for st in states:
        marker = os.path.join(DATA, st, "incomplete")
        if undone.get(st):
            with open(marker, "w") as f:
                f.write(" ".join(undone[st]) + "\n")
            print(f"{st.upper()}: incomplete ({' '.join(undone[st])})", flush=True)
        elif os.path.exists(marker):
            os.remove(marker)
    print(f"run: {round((time.time() - START) / 60)} min" + ("; stopped at the time limit" if out_of_time() else ""))
    print(f"LegiScan queries this month: {used():,} of {MONTHLY_STOP:,} allowed", flush=True)
    if stopped:
        sys.exit(1)


if __name__ == "__main__":
    main()
