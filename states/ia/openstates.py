#!/usr/bin/env python3
"""Iowa's first copy from Open States (https://v3.openstates.org/; the owner's free API key in ~/.openstates_api_key or
OPENSTATES_API_KEY, never printed), decided 2026-11-14. legis.iowa.gov's firewall shows GitHub's runs a script challenge
after about 45 requests (5 minutes at fetch.py's pace; checked 2026-11-14: from the owner's computer the same pages load),
and fetch.py stops there each run rather than work around it. That's plenty to follow changes (the Disposition of Bills
lists, then each bill that moved) but a first copy of every bill would take about a month. So each General Assembly's
bills are read once from Open States' public-domain records, and fetch.py reads the official page of every bill that
changed since (and, in the requests left, the rest, so the official record replaces these over time). The converter
uses a bill's official history when fetch.py has it, else this record.

Into data/ia/<first year>/openstates/<HF100>.json: each bill (classification=bill: HF, SF, HJR, SJR and the study bills
HSB, SSB), 20 to a request, with sponsorships, actions, votes (member by member), versions, abstracts, sources and related
bills; and data/ia/<first year>/openstates.json: {"complete", "page", "began", "done"}. Each General Assembly (the one
before this and this one; sessions are "2025-2026") is read whole once and then left alone; no updates are asked for.
About 3,000 bills each (150 requests). Also data/ia/openstates_people.csv (the current legislators: name, party, district,
emails, phones; data.openstates.org, not counted against the quota), daily, for contacts until fetch.py has read the
members' pages.

The quota: the free tier allows 250 requests a day, shared with Arizona's and Hawaii's runs. This script counts its own per
UTC day in data/ia/openstates_quota.json and stops at DAILY_MAX (100; OPENSTATES_IA_DAILY sets it), or at once when Open
States says the day's limit is used up; the place is saved and the next run resumes. One request every 6 seconds. It never
marks Iowa incomplete itself: fetch.py's marker counts a bill read here as downloaded.
Usage: python3 states/ia/openstates.py
"""
import json, os, time, urllib.error, urllib.parse, urllib.request
from datetime import date, datetime, timedelta, timezone

API = "https://v3.openstates.org"
PEOPLE = "https://data.openstates.org/people/current/ia.csv"
DATA = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "ia"))
AGENT = "statebilltracker.org (a nonprofit bill tracker; contact via github.com/judithhubbard)"
TODAY = date.today()
YEAR = TODAY.year
FIRST = (YEAR if YEAR % 2 else YEAR - 1) - 2  # the first year of the General Assembly before this one
DELAY = 6.0
DAILY_MAX = int(os.environ.get("OPENSTATES_IA_DAILY") or 100)
INCLUDE = ["sponsorships", "actions", "votes", "versions", "abstracts", "sources", "related_bills"]
QUOTA = os.path.join(DATA, "openstates_quota.json")

# The run's own time limit (FETCH_MINUTES, set by the workflow): stop a few minutes early, with everything read so far
# saved and a summary printed, rather than be cut off silently mid-request.
START = time.time()
BUDGET = max(0.0, float(os.environ.get("FETCH_MINUTES") or 0) - 5) * 60
STATS = {"requests": 0, "bills": 0, "failures": 0}
LAST = [0.0]


class Stop(Exception):
    """The day's quota (ours or Open States') or the run's time is used up: save the place and stop."""


def out_of_time():
    return BUDGET and time.time() - START > BUDGET


def key():
    k = os.environ.get("OPENSTATES_API_KEY") or ""
    if not k:
        try:
            k = open(os.path.expanduser("~/.openstates_api_key")).read()
        except OSError:
            pass
    return k.strip()


def load(path, default=None):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def save(obj, path):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False)
    os.replace(tmp, path)


def utc_day():
    return datetime.now(timezone.utc).date().isoformat()


def used_today():
    q = load(QUOTA, {})
    return q.get("used", 0) if q.get("day") == utc_day() else 0


def count_request():
    save({"day": utc_day(), "used": used_today() + 1}, QUOTA)


def get(path, params):
    """The JSON answer, or None after five tries. Raises Stop at the daily limit or the time limit."""
    url = f"{API}{path}?" + urllib.parse.urlencode(params, doseq=True)
    for attempt in range(5):
        if out_of_time():
            raise Stop("the run's time limit")
        if used_today() >= DAILY_MAX:
            raise Stop(f"this script's daily share ({DAILY_MAX} requests)")
        wait = LAST[0] + DELAY - time.time()
        if wait > 0:
            time.sleep(wait)
        LAST[0] = time.time()
        STATS["requests"] += 1
        count_request()
        try:
            req = urllib.request.Request(url, headers={"User-Agent": AGENT, "X-API-KEY": key()})
            with urllib.request.urlopen(req, timeout=180) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            STATS["failures"] += 1
            if e.code == 429:
                body = e.read().decode("utf-8", "replace")
                if "per day" in body or "/day" in body:
                    raise Stop("Open States' daily limit")
                time.sleep(60 * (attempt + 1))  # over the per-minute limit: wait and try again
                continue
            if e.code in (401, 403):
                raise SystemExit(f"Open States refused the request ({e.code}): check the API key")
            time.sleep(10 * (attempt + 1))
        except Exception:
            STATS["failures"] += 1
            time.sleep(10 * (attempt + 1))
    return None


def session(first):
    sid = f"{first}-{first + 1}"
    folder = os.path.join(DATA, str(first), "openstates")
    os.makedirs(folder, exist_ok=True)
    state_path = os.path.join(DATA, str(first), "openstates.json")
    state = load(state_path, {})
    if state.get("complete"):
        return
    params = {"jurisdiction": "ia", "session": sid, "classification": "bill", "per_page": 20, "sort": "updated_asc",
              "include": INCLUDE}
    state.setdefault("began", datetime.now(timezone.utc).replace(tzinfo=None).isoformat(timespec="seconds"))
    page = state.get("page", 1)
    got = 0
    try:
        while True:
            d = get("/bills", dict(params, page=page))
            if d is None:
                print(f"{sid}: page {page} unreadable; asked again next run", flush=True)
                break
            for b in d.get("results") or []:
                save(b, os.path.join(folder, b["identifier"].replace(" ", "") + ".json"))
                got += 1
                STATS["bills"] += 1
            last = (d.get("pagination") or {}).get("max_page", 1) or 1
            if page >= last:
                state.update(complete=True, done=TODAY.isoformat())
                state.pop("page", None)
                break
            page += 1
            state["page"] = page
            save(state, state_path)
    finally:
        save(state, state_path)
        print(f"{sid}: {got} bills saved this run, {len(os.listdir(folder))} on file"
              + ("; complete" if state.get("complete") else f"; resumes at page {state.get('page', 1)}"), flush=True)


def people():
    try:
        req = urllib.request.Request(PEOPLE, headers={"User-Agent": AGENT})
        body = urllib.request.urlopen(req, timeout=60).read()
        if b"name" not in body[:200]:
            raise ValueError("not the people file")
        tmp = os.path.join(DATA, "openstates_people.csv.tmp")
        open(tmp, "wb").write(body)
        os.replace(tmp, os.path.join(DATA, "openstates_people.csv"))
        rows = body.count(b"\n") - 1
        print(f"people: {rows} legislators", flush=True)
    except Exception as e:
        print(f"people: {type(e).__name__}; kept the last copy", flush=True)


def main():
    if not key():
        raise SystemExit("No Open States API key (~/.openstates_api_key or OPENSTATES_API_KEY)")
    os.makedirs(DATA, exist_ok=True)
    stopped = ""
    try:
        for first in (YEAR if YEAR % 2 else YEAR - 1, FIRST):  # this General Assembly first
            session(first)
    except Stop as e:
        stopped = str(e)
    people()
    print(f"run: {STATS['requests']} requests ({STATS['bills']} bills), {round((time.time() - START) / 60)} min; "
          f"{used_today()} of this script's {DAILY_MAX} used today (UTC)"
          + (f"; stopped at {stopped}, the next run resumes" if stopped else "")
          + (f"; {STATS['failures']} request failures" if STATS["failures"] else "; no request failures"), flush=True)


if __name__ == "__main__":
    main()
