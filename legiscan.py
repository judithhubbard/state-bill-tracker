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
- Between Sundays, for a session still running: getMasterListRaw at most once an hour, then getBill only for bills
  whose change_hash differs from the saved copy (and never one bill twice within 3 hours), getRollCall only for roll
  calls not saved yet (they never change), getSessionPeople at most once a week, when a bill names someone not saved.
- No bill texts (getBillText) and never legiscan.com's pages.

What's kept, per state: the regular sessions (special sessions left out) that end this year or in the two years
before and start no later than this year, in data/<st>/legiscan/<session_id>/ with the dataset's own layout:
bill/<bill_number>.json, vote/<roll_call_id>.json, people/<people_id>.json (each as LegiScan gives it: {"bill": ...},
{"roll_call": ...}, {"person": ...}), plus meta.json (the session, dataset_hash and date, the last master list's time,
each bill's number, change_hash and when it was last read). data/<st>/incomplete says "running" during a run, then lists
what was never downloaded (a session's dataset, a new bill); a failed refresh keeps the last copy and doesn't count.
FETCH_MINUTES (set by the workflow) stops the run five minutes before it.

Usage: python3 legiscan.py tn [ok me ri vt]
"""
import base64, io, json, os, re, sys, time, urllib.error, urllib.parse, urllib.request, zipfile
from datetime import date, datetime, timezone

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
YEAR = date.today().year

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
    today = date.today().isoformat()
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
    meta["bills"][str(bill["bill_id"])] = {"number": bill["bill_number"], "change_hash": bill.get("change_hash"),
                                          "fetched": fetched}


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


def catch_up(folder, meta, session_id):
    """Between Sundays: the master list, then the bills whose change_hash changed, their new roll calls, and new
    people. Returns False if a bill never saved was left unread: a failed re-read keeps the last copy, and roll calls
    and people not read now come with Sunday's dataset, so neither holds the state off the site."""
    done = True
    now = time.time()
    if now - meta.get("masterlist_time", 0) < MASTERLIST_EVERY:
        print("  master list read within the hour; skipped")
        return True
    answer = query("getMasterListRaw", id=session_id)
    if answer is None:
        return True  # the dataset's copies stay
    meta["masterlist_time"] = time.time()
    entries = [v for k, v in answer["masterlist"].items() if k != "session"]
    todo = [e for e in entries if (meta["bills"].get(str(e["bill_id"])) or {}).get("change_hash") != e["change_hash"]]
    print(f"  master list: {len(entries)} bills, {len(todo)} changed since the saved copies", flush=True)
    got = 0
    new_people = set()
    never = lambda rest: any(str(x["bill_id"]) not in meta["bills"] for x in rest)  # bills never saved
    for i, e in enumerate(todo):
        if out_of_time():
            return not never(todo[i:])
        old = meta["bills"].get(str(e["bill_id"])) or {}
        if time.time() - old.get("fetched", 0) < BILL_EVERY:
            continue  # read within three hours: next run
        answer = query("getBill", id=e["bill_id"])
        if answer is None:
            if not old:
                done = False
            continue
        bill = answer["bill"]
        write_json(os.path.join(folder, "bill", safe_name(bill["bill_number"]) + ".json"), {"bill": bill})
        bill_entry(meta, bill, time.time())
        got += 1
        for v in bill.get("votes") or []:
            path = os.path.join(folder, "vote", f"{v['roll_call_id']}.json")
            if os.path.exists(path):
                continue
            if out_of_time():
                return not never(todo[i + 1:])
            rc = query("getRollCall", id=v["roll_call_id"])
            if rc is None:
                continue
            write_json(path, {"roll_call": rc["roll_call"]})
            for m in rc["roll_call"].get("votes") or []:
                new_people.add(m.get("people_id"))
        for s in bill.get("sponsors") or []:
            new_people.add(s.get("people_id"))
        if got % 25 == 0:
            write_json(os.path.join(folder, "meta.json"), meta, indent=1)
    if todo:
        print(f"  {got} bills read again", flush=True)
    missing = {p for p in new_people if p and not os.path.exists(os.path.join(folder, "people", f"{p}.json"))}
    if missing:
        if time.time() - meta.get("people_time", 0) < PEOPLE_EVERY:
            print(f"  {len(missing)} people not saved yet; the session's people are read once a week")
        elif not out_of_time():
            answer = query("getSessionPeople", id=session_id)
            if answer is not None:
                meta["people_time"] = time.time()
                for p in answer["sessionpeople"]["people"]:
                    write_json(os.path.join(folder, "people", f"{p['people_id']}.json"), {"person": p})
                print(f"  people: {len(answer['sessionpeople']['people'])} read", flush=True)
    return done


def run_state(st):
    """One state's sessions. Returns the parts left undone."""
    undone = []
    base = os.path.join(DATA, st, "legiscan")
    datasets = dataset_list(st)
    if datasets is None:
        return ["datasetlist"]
    for ds in wanted(datasets):
        sid = ds["session_id"]
        folder = os.path.join(base, str(sid))
        meta_path = os.path.join(folder, "meta.json")
        meta = read_json(meta_path) or {"bills": {}}
        # Only a session never downloaded holds the state off the site; a failed refresh keeps the last dataset.
        read_once = bool(meta.get("dataset_hash"))
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
            # A session over before this year waits for the weekly datasets; the running ones are caught up.
            if int(ds["year_end"]) >= YEAR and not int(ds.get("sine_die") or 0):
                if not catch_up(folder, meta, sid):
                    undone.append(f"{sid}:bills")
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
            if not (read_json(os.path.join(DATA, st, "legiscan", str(d["session_id"]), "meta.json")) or {}).get("dataset_hash")]


def main():
    global KEY
    states = [a.lower() for a in sys.argv[1:]]
    if not states or any(s not in STATES for s in states):
        sys.exit(f"Usage: python3 legiscan.py {' '.join(STATES)}   (one or more)")
    KEY = load_key()
    stopped = None
    for st in states:
        marker = os.path.join(DATA, st, "incomplete")
        os.makedirs(os.path.dirname(marker), exist_ok=True)
        if not os.path.exists(marker):
            with open(marker, "w") as f:
                f.write("running\n")
        undone = []
        # A run stopped early (the month's limit, an error) leaves the saved copies as they were: only sessions never
        # downloaded keep the state off the site.
        if stopped:
            undone = never_read(st)
        else:
            try:
                undone = run_state(st)
            except Stop as e:
                stopped = str(e)
                print(stopped, flush=True)
                undone = never_read(st)
            except Exception as e:  # never let a message carry the key
                print(scrub(f"{st.upper()}: {e.__class__.__name__} {e}"), flush=True)
                undone = never_read(st)
        if undone:
            with open(marker, "w") as f:
                f.write(" ".join(undone) + "\n")
            print(f"{st.upper()}: incomplete ({' '.join(undone)})", flush=True)
        elif os.path.exists(marker):
            os.remove(marker)
    print(f"run: {round((time.time() - START) / 60)} min" + ("; stopped at the time limit" if out_of_time() else ""))
    print(f"LegiScan queries this month: {used():,} of {MONTHLY_STOP:,} allowed", flush=True)
    if stopped:
        sys.exit(1)


if __name__ == "__main__":
    main()
