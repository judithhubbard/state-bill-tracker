#!/usr/bin/env python3
"""Download Indiana's bills from the General Assembly's API (MyIGA API 2.0, https://api.iga.in.gov; documented at
https://docs.api.iga.in.gov). Every request carries the key (header x-api-key, from the INDIANA_API_KEY environment
variable or ~/.indiana_api_key) and a User-Agent starting "iga-api-client-", as the API asks. The key is a header, never
part of an address, and no message prints headers. The API answers 403 both for a bad key ("Invalid API key") and for a
path that doesn't exist ("The resource you requested does not exist"): only the first stops the run.

- Sessions: the session list (GET /): one regular session a year (long in odd years, short in even ones); special
  sessions ("2022ss1") are left out.
- Each regular session's bill list (/<year>/bills: every bill and resolution, one answer) into data/in/<year>/bills.json,
  every action of the session in one answer (/<year>/bill-actions: date, legislative day, sequence, chamber, the
  committee of a referral, description) into actions.json, and every roll call's tally (/<year>/rollcalls: chamber,
  number, the version, amendment or motion voted on, yeas and nays) into rollcalls.json.
- Each House and Senate bill and joint resolution (HB, SB, HJ, SJ; joint resolutions propose constitutional amendments,
  among other things; simple and concurrent resolutions are left out): its detail (/<year>/bills/<hb1001>: title,
  short description, authors, coauthors, sponsors and cosponsors with their legislator links, conferees and advisors,
  motions, every version with its digest, every roll call), with its actions from actions.json (as "actions", sorted by
  date and sequence), into data/in/<year>/bills/<HB1001>.json.
- The legislators (/<year>/legislators, then each one's detail: chamber, district, party, committees) into
  legislators.json, and the standing committees (each one's members, chair, vice chair, ranking minority member and
  assigned bills) into committees.json. The API has no emails, phones, offices or leadership posts.

Members' votes: the API's roll calls carry tallies only; each one's ?format=pdf answer redirects to
iga.in.gov/pdf-documents/..., which serves only the website's script page, not the PDF. So no member-by-member votes.

A bill's detail is read again when its fingerprint changes (its list entry, its actions and its roll calls; kept in
data/in/<year>/state.json) or the bill list's minUpdateDatetime filter names it. Sessions from last year on are checked
every run (three requests; a veto is overridden in the next year's session); an earlier one, once complete, is skipped.
Legislators and committees: this year's every run, an earlier year's once. One request at a time, 0.6 seconds apart.
FETCH_MINUTES (set by the workflow) stops the run five minutes before it with everything saved.
Usage: python3 states/in/fetch.py [first_year]   (default: two years back, through the newest listed session)
"""
import hashlib, json, os, sys, time, urllib.error, urllib.request
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta

API = "https://api.iga.in.gov"
DATA = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "in"))
AGENT = "iga-api-client-statebilltracker (statebilltracker.org; contact via github.com/judithhubbard)"
YEAR = date.today().year
FIRST = int(sys.argv[1]) if len(sys.argv) > 1 else YEAR - 2
KINDS = ("HB", "SB", "HJ", "SJ")
GAP = 0.6
START = time.time()
BUDGET = max(0.0, float(os.environ.get("FETCH_MINUTES") or 0) - 5) * 60
INCOMPLETE = set()
FAILS = Counter()
STATS = {"requests": 0, "last": 0.0}


class Refused(Exception):
    """The API turned the key away (401, 403 "Invalid API key") or asked us to slow down (429): stop the run."""


class OutOfTime(Exception):
    pass


def out_of_time():
    return bool(BUDGET) and time.time() - START > BUDGET


def key():
    k = os.environ.get("INDIANA_API_KEY") or ""
    if not k:
        try:
            with open(os.path.expanduser("~/.indiana_api_key")) as f:
                k = f.read()
        except OSError:
            pass
    return k.strip()


def progress():
    n = STATS["requests"]
    if n % 100 == 0:
        print(f"{n} requests, {round((time.time() - START) / 60)} min"
              + (f"; failures {dict(FAILS)}" if FAILS else "; no failures"), flush=True)


def get(path):
    """One API answer as JSON (path like "/2026/bills"); None when it fails. At most 3 attempts, 30-second timeouts."""
    if out_of_time():
        raise OutOfTime()
    for attempt in range(3):
        wait = STATS["last"] + GAP - time.time()
        if wait > 0:
            time.sleep(wait)
        STATS["requests"] += 1
        progress()
        cause = None
        try:
            req = urllib.request.Request(API + path, headers={"x-api-key": key(), "User-Agent": AGENT,
                                                             "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=30) as r:
                body = r.read()
            STATS["last"] = time.time()
            return json.loads(body)
        except urllib.error.HTTPError as e:
            STATS["last"] = time.time()
            text = e.read()[:500].decode("utf-8", "replace")
            if e.code == 401 or (e.code == 403 and "invalid api key" in text.lower()):
                raise Refused(f"{path}: HTTP {e.code} (the key was refused)")
            if e.code == 429:
                raise Refused(f"{path}: HTTP 429 (too many requests)")
            if e.code in (403, 404):  # 403 "does not exist" is this API's not-found
                FAILS["not found"] += 1
                print(f"{path}: not found ({e.code})", flush=True)
                return None
            cause = f"HTTP {e.code}"
        except ValueError:
            STATS["last"] = time.time()
            cause = "not JSON"
        except (OSError, TimeoutError) as e:  # never str(e) with headers; urllib's messages don't carry them
            STATS["last"] = time.time()
            cause = type(e).__name__
        FAILS[cause] += 1
        print(f"{path}: {cause}" + ("; trying again" if attempt < 2 else "; giving up"), flush=True)
        if attempt < 2:
            time.sleep(5 * (attempt + 1))
    return None


def save(path, data):
    with open(path + ".tmp", "w") as f:
        json.dump(data, f, ensure_ascii=False)
    os.replace(path + ".tmp", path)


def load(path, default=None):
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def sessions():
    """Regular session years listed by the API, e.g. [2009, ..., 2026]."""
    d = get("/")
    if not isinstance(d, dict):
        return []
    years = []
    for s in d.get("sessions") or []:
        name = (s.get("link") or "").strip("/")
        if name.isdigit():
            years.append(int(name))
    return sorted(years)


def fingerprint(*parts):
    return hashlib.sha1(json.dumps(parts, sort_keys=True).encode()).hexdigest()


def bills(year):
    """The session's lists, then each bill whose fingerprint changed. Returns True when every wanted bill is saved."""
    folder = os.path.join(DATA, str(year))
    os.makedirs(os.path.join(folder, "bills"), exist_ok=True)
    state_path = os.path.join(folder, "state.json")
    state = load(state_path, {})
    if year < YEAR - 1 and state.get("complete"):
        print(f"{year}: complete, skipped", flush=True)
        return True
    run_start = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    listing = get(f"/{year}/bills")
    actions = get(f"/{year}/bill-actions")
    rolls = get(f"/{year}/rollcalls")
    # Only data never read holds Indiana off the site: once a year's first copy is whole ("complete"), a failed
    # refresh keeps the last copies.
    if not (isinstance(listing, dict) and isinstance(listing.get("items"), list) and listing["items"]):
        print(f"{year}: bill list unreadable; kept the last copies", flush=True)
        if not state.get("complete"):
            INCOMPLETE.add(f"{year}:list")
        return False
    if not (isinstance(actions, dict) and isinstance(actions.get("items"), list)):
        print(f"{year}: actions unreadable; kept the last copies", flush=True)
        if not state.get("complete"):
            INCOMPLETE.add(f"{year}:actions")
        return False
    if not (isinstance(rolls, dict) and isinstance(rolls.get("items"), list)):
        print(f"{year}: roll calls unreadable; kept the last copies", flush=True)
        if not os.path.exists(os.path.join(folder, "rollcalls.json")):
            INCOMPLETE.add(f"{year}:rollcalls")
        rolls = load(os.path.join(folder, "rollcalls.json"), {"items": []})
    else:
        save(os.path.join(folder, "rollcalls.json"), rolls)
    save(os.path.join(folder, "bills.json"), listing)
    save(os.path.join(folder, "actions.json"), actions)
    if actions.get("total_count") not in (None, len(actions["items"])):
        print(f"{year}: actions say {actions['total_count']} but hold {len(actions['items'])}", flush=True)
        INCOMPLETE.add(f"{year}:actions")
    by_bill = defaultdict(list)
    for a in actions["items"]:
        by_bill[((a.get("billName") or {}).get("billName") or "").upper()].append(a)
    rolls_by_bill = defaultdict(list)
    for r in rolls.get("items") or []:
        rolls_by_bill[(r.get("target") or "").split(".")[0].upper()].append(r)
    # Bills the API itself says changed since the last run (a day's overlap); added to the fingerprint check.
    named = set()
    if state.get("lastRun"):
        since = (datetime.fromisoformat(state["lastRun"]) - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%S")
        d = get(f"/{year}/bills?minUpdateDatetime={since}")
        if isinstance(d, dict):
            named = {(i.get("billName") or "").upper() for i in d.get("items") or []}
    prints = state.setdefault("prints", {})
    wanted = [i for i in listing["items"] if (i.get("billName") or "")[:2].upper() in KINDS]
    todo = []
    for i in wanted:
        name = i["billName"].upper()
        fp = fingerprint(i, sorted(by_bill.get(name, []), key=lambda a: a.get("link") or ""),
                         sorted(rolls_by_bill.get(name, []), key=lambda r: r.get("link") or ""))
        path = os.path.join(folder, "bills", f"{name}.json")
        if prints.get(name) != fp or name in named or not os.path.exists(path):
            todo.append((i, name, fp, path))
    got = 0
    try:
        for i, name, fp, path in todo:
            d = get(i.get("link") or f"/{year}/bills/{name.lower()}")
            if not (isinstance(d, dict) and d.get("billName")):
                FAILS["bill unreadable"] += 1
                continue
            d["actionsLink"] = (d.get("actions") or {}).get("link") if isinstance(d.get("actions"), dict) else None
            d["actions"] = sorted(by_bill.get(name, []), key=lambda a: (a.get("date") or "", int(a.get("sequence") or 0)))
            d["listEntry"] = i
            save(path, d)
            prints[name] = fp
            got += 1
            if got % 50 == 0:
                save(state_path, state)
    finally:
        save(state_path, state)
        print(f"{year}: {got} of {len(todo)} bills read ({len(wanted)} bills and joint resolutions, "
              f"{len(listing['items'])} listed, {len(actions['items'])} actions, {len(rolls.get('items') or [])} roll calls)",
              flush=True)
    done = got == len(todo)
    if done:
        state["complete"] = True
        state["lastRun"] = run_start
        save(state_path, state)
    elif any(not os.path.exists(os.path.join(folder, "bills", f"{i['billName'].upper()}.json")) for i in wanted):
        INCOMPLETE.add(f"{year}:bills")  # a bill never read (one whose refresh failed keeps its last copy)
    return done


def people(year):
    """Legislators and standing committees: this year's (and a future session's) every run, an earlier year's once."""
    folder = os.path.join(DATA, str(year))
    os.makedirs(folder, exist_ok=True)
    state_path = os.path.join(folder, "state.json")
    state = load(state_path, {})
    if year < YEAR and state.get("people"):
        return
    ok = True
    listing = get(f"/{year}/legislators")
    if not (isinstance(listing, dict) and listing.get("items")):
        # /2024/legislators answers HTTP 500 every time; each chamber's list works (and includes replacements)
        items = []
        for chamber in ("house", "senate"):
            d = get(f"/{year}/chambers/{chamber}/legislators")
            if isinstance(d, dict) and d.get("items"):
                items += d["items"]
            else:
                items = []
                break
        listing = {"items": items}
    if listing["items"]:
        out, failed = [], []
        for m in listing["items"]:
            d = get(m["link"]) if m.get("link") else None
            if isinstance(d, dict):
                out.append({**m, **{k: v for k, v in d.items() if k != "link"}, "link": m.get("link")})
            else:  # 2024's Mark Messmer answers HTTP 500 every time: keep his list entry, marked
                out.append({**m, "detailFailed": True})
                failed.append(m.get("link") or "?")
        save(os.path.join(folder, "legislators.json"), out)
        print(f"{year}: {len(out)} legislators" + (f"; no detail for {', '.join(failed)}" if failed else ""), flush=True)
        if len(failed) > 2:  # one or two records the server always fails on don't hold the copy incomplete
            ok = False
    else:
        ok = False
        print(f"{year}: legislators unreadable; kept the last copy", flush=True)
    listing = get(f"/{year}/committees?committee_type=standing")
    if isinstance(listing, dict) and listing.get("items"):
        out = []
        for c in listing["items"]:
            d = get(c["link"]) if c.get("link") else None
            if isinstance(d, dict):
                d.pop("meetings", None)
                out.append({**c, **d, "link": c.get("link"), "committeeType": c.get("committeeType")})
            else:
                out.append(c)
                ok = False
        save(os.path.join(folder, "committees.json"), out)
        print(f"{year}: {len(out)} standing committees", flush=True)
    else:
        ok = False
        print(f"{year}: committees unreadable; kept the last copy", flush=True)
    state = load(state_path, {})
    if ok:
        state["people"] = True
        save(state_path, state)
    elif not state.get("people") and year <= YEAR:  # read whole once: a failed refresh keeps the last copy
        # (A session not yet begun, listed in November with no members yet, mustn't hold Indiana off the site.)
        INCOMPLETE.add(f"{year}:people")


def begun(year):
    """Whether a year's session has convened (by the second Monday of January). The next session, listed from November
    with its first bills and no members yet, is read when it's there but never holds Indiana off the site."""
    return date.today() >= date(year, 1, 1 + (0 - date(year, 1, 1).weekday()) % 7 + 7)


def finish():
    print(f"run: {round((time.time() - START) / 60)} min, {STATS['requests']} requests"
          + ("; stopped at the time limit" if out_of_time() else "")
          + (f"; request failures {dict(FAILS)}" if FAILS else "; no request failures")
          + (f"; still to do: {' '.join(sorted(INCOMPLETE))}" if INCOMPLETE else ""), flush=True)
    marker = os.path.join(DATA, "incomplete")
    undone = {g for g in INCOMPLETE if not g[:4].isdigit() or begun(int(g[:4]))}
    if undone:
        with open(marker, "w") as f:
            f.write(" ".join(sorted(undone)) + "\n")
    elif os.path.exists(marker):
        os.remove(marker)


def main():
    if not key():
        raise SystemExit("No Indiana API key (INDIANA_API_KEY or ~/.indiana_api_key)")
    os.makedirs(DATA, exist_ok=True)
    whole = not os.path.exists(os.path.join(DATA, "incomplete"))  # the last run left nothing missing
    with open(os.path.join(DATA, "incomplete"), "w") as f:  # until this run finishes, the copy may be partial
        f.write("running\n")
    try:
        listed = sessions()
        if listed:
            save(os.path.join(DATA, "sessions.json"), listed)
        else:
            listed = load(os.path.join(DATA, "sessions.json"), []) or []  # a failed refresh: the last list
            if not listed:
                INCOMPLETE.add("sessions")
        years = [y for y in listed if y >= FIRST]
        for y in sorted(years, reverse=True):  # the newest session first
            bills(y)
        for y in sorted(years, reverse=True):
            people(y)
    except OutOfTime:
        if not whole:  # once whole, a run cut short leaves the last copies
            INCOMPLETE.add("time")
    except Refused as e:
        print(f"Stopped: {e}", flush=True)
        if not whole:
            INCOMPLETE.add("refused")
    finish()


if __name__ == "__main__":
    main()
