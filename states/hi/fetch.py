#!/usr/bin/env python3
"""Download Hawaii's bills from Open States (https://v3.openstates.org/; the owner's free API key in
~/.openstates_api_key or the OPENSTATES_API_KEY environment variable, never printed). The Legislature's website,
www.capitol.hawaii.gov, turns automated requests away (a Cloudflare block, even for robots.txt; checked 2026-11-13), and
data.capitol.hawaii.gov serves the same site under another name without the block, so the owner decided (2026-11-13) to
use Open States' public-domain data, as for Arizona. Neither capitol.hawaii.gov host is read here. The bills' version
links and sources point at them (for visitors to follow).

Hawaii's Legislature sits for two years (2025-26 is the 33rd), with a regular session each year from the third Wednesday
of January to early May; bills not passed carry over from the first year to the second. Open States keeps a session per
year ("2023 Regular Session", then "2024", "2025", "2026"): a bill carried over appears in both years, the second year's
record with the whole history ("Carried over to 2026 Regular Session." on December 8). So each year of this biennium and
the last (2023-2026 now; 2025-2028 from 2027) is read, into data/hi/<year>/:
- bills/<HB9>.json: each House and Senate bill (HB, SB; Hawaii proposes constitutional amendments as bills, "PROPOSING AN
  AMENDMENT TO ARTICLE ..."), from /bills with classification=bill (leaving out resolutions and governor's messages),
  20 to a request, with sponsorships (introducers in order, "primary" first), actions (house, date, classification,
  text: committee votes are in the text, "The votes were as follows: 6 Ayes: Representative(s) ...; Ayes with
  reservations: ...; Noes: ...; Excused: ...", and floor votes as "Passed Third Reading with ... voting no (2) ..."),
  votes (Open States' vote events, member by member, committee and floor), versions with links (HTM, PDF), documents
  (empty in the first 100 bills checked; committee reports appear only as "Stand. Com. Rep. No. 765-26" in actions),
  abstracts, sources, other identifiers and related bills. Acts, vetoes,
  the governor's intent-to-veto notices and overrides are in the actions.
- state.json: whether the first copy is whole ("complete"), the page a first copy or an update stopped at, and the time
  the last whole pass began ("since"); later passes ask only for bills updated since then (updated_since, less six
  hours). A year before this one is read once, then left alone.
Also data/hi/openstates_people.csv: the current legislators (data.openstates.org's public people file: name, party,
district, chamber, emails, capitol and district phones and addresses; not counted against the API quota), and
data/hi/sessions.json (Open States' session ids, asked for weekly).
Not read: committees with chairs (not in the people file; Open States' API has a committees endpoint that could be
added, at a few requests a week), and the governor's intent-to-veto list as a list (it's in each bill's actions).

The quota: the free tier allows 250 requests a day, shared with Arizona's runs (states/az/fetch.py). This script counts
its own requests per UTC day in data/hi/quota.json and stops at DAILY_MAX (default 110; OPENSTATES_HI_DAILY sets it), so
Arizona keeps the rest; it also stops at once when Open States says the day's limit is used up. Either way the place
is saved and the next run resumes there. One request every 6 seconds (Open States' per-minute limit). About 18,000
bills in four years (2026: 5,309, 266 requests), roughly 870 requests: the first copy takes about eight days at 110 a
day; then a run asks a few requests for the current year's changes.

data/hi/incomplete lists what was never downloaded (a year whose first copy isn't whole, the people file); it's removed
when nothing is missing. A year Open States doesn't list yet (January, before the session) isn't missing. A failed page
or the daily limit during a later update keeps the saved bills; the next run asks again from the same place.
Usage: python3 states/hi/fetch.py
"""
import json, os, time, urllib.error, urllib.parse, urllib.request
from datetime import date, datetime, timedelta, timezone

API = "https://v3.openstates.org"
PEOPLE = "https://data.openstates.org/people/current/hi.csv"
DATA = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "hi"))
AGENT = "statebilltracker.org (a nonprofit bill tracker; contact via github.com/judithhubbard)"
TODAY = date.today()
YEAR = TODAY.year
FIRST = (YEAR if YEAR % 2 else YEAR - 1) - 2  # the first year of last biennium
DELAY = 6.0
DAILY_MAX = int(os.environ.get("OPENSTATES_HI_DAILY") or 110)
INCLUDE = ["sponsorships", "actions", "votes", "versions", "documents", "abstracts", "sources", "other_identifiers",
           "related_bills"]
MARKER = os.path.join(DATA, "incomplete")
QUOTA = os.path.join(DATA, "quota.json")

# The run's own time limit (FETCH_MINUTES, set by the workflow): stop a few minutes early, with everything read so far
# saved and a summary printed, rather than be cut off silently mid-request.
START = time.time()
BUDGET = max(0.0, float(os.environ.get("FETCH_MINUTES") or 0) - 5) * 60
STATS = {"requests": 0, "bills": 0, "failures": 0}
LAST = [0.0]
NOTES = []  # what this run didn't finish, for the summary


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


def sessions():
    """Year -> Open States session id, for regular sessions from FIRST on; asked weekly, else the saved copy."""
    path = os.path.join(DATA, "sessions.json")
    saved = load(path, {})
    fresh = saved.get("read", "") >= (TODAY - timedelta(days=7)).isoformat()
    # A year not listed yet (January) is asked for daily rather than weekly.
    if fresh and (str(YEAR) in saved.get("ids", {}) or saved["read"] == TODAY.isoformat()):
        return {int(y): s for y, s in saved["ids"].items()}
    j = get("/jurisdictions/ocd-jurisdiction/country:us/state:hi/government", {"include": "legislative_sessions"})
    if not j:
        print("sessions: unreadable; kept the last copy", flush=True)
        return {int(y): s for y, s in saved.get("ids", {}).items()}
    ids = {}
    for s in j.get("legislative_sessions") or []:
        start = s.get("start_date") or ""
        if "special" in (s.get("classification") or "") or "special" in s["identifier"].lower() or not start[:4].isdigit():
            continue
        ids[start[:4]] = s["identifier"]
    save({"read": TODAY.isoformat(), "ids": ids, "starts": {s["start_date"][:4]: s["start_date"]
                                                           for s in j.get("legislative_sessions") or []
                                                           if (s.get("start_date") or "")[:4].isdigit()}}, path)
    return {int(y): s for y, s in ids.items()}


def session(year, sid):
    folder = os.path.join(DATA, str(year), "bills")
    os.makedirs(folder, exist_ok=True)
    state_path = os.path.join(DATA, str(year), "state.json")
    state = load(state_path, {})
    if state.get("complete") and year < YEAR:
        return  # a past year, read whole once
    params = {"jurisdiction": "hi", "session": sid, "classification": "bill", "per_page": 20, "sort": "updated_asc",
              "include": INCLUDE}
    now = datetime.now(timezone.utc).replace(tzinfo=None).isoformat(timespec="seconds")
    if state.get("complete"):
        # A later pass: bills updated since the last whole pass began (less six hours), resuming a pass cut short.
        p = state.get("pass") or {"from": (datetime.fromisoformat(state["since"]) - timedelta(hours=6))
                                  .isoformat(timespec="seconds"), "began": now, "page": 1}
        state["pass"] = p
        params["updated_since"] = p["from"]
        page = p["page"]
    else:
        state.setdefault("began", now)
        page = state.get("page", 1)
    got = 0
    try:
        while True:
            d = get("/bills", dict(params, page=page))
            if d is None:
                NOTES.append(f"{year}:page{page}")
                break
            for b in d.get("results") or []:
                save(b, os.path.join(folder, b["identifier"].replace(" ", "") + ".json"))
                got += 1
                STATS["bills"] += 1
            last = (d.get("pagination") or {}).get("max_page", 1) or 1
            if page >= last:
                if state.get("complete"):
                    state["since"] = state.pop("pass")["began"]
                else:
                    state.update(complete=True, since=state.pop("began"))
                    state.pop("page", None)
                break
            page += 1
            if state.get("complete"):
                state["pass"]["page"] = page
            else:
                state["page"] = page
            save(state, state_path)
    finally:
        save(state, state_path)
        total = len(os.listdir(folder))
        print(f"{year} ({sid}): {got} bills saved this run, {total} on file"
              + ("" if state.get("complete") else f"; first copy resumes at page {state.get('page', 1)}"), flush=True)


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


def never_downloaded(ids):
    out = []
    if not os.path.exists(os.path.join(DATA, "openstates_people.csv")):
        out.append("people")
    starts = load(os.path.join(DATA, "sessions.json"), {}).get("starts", {})
    for year in range(FIRST, YEAR + 1):
        if year == YEAR and (year not in ids or starts.get(str(year), "") > TODAY.isoformat()):
            continue  # the session isn't listed yet, or hasn't begun (its bills are read but don't hold Hawaii back)
        if not (load(os.path.join(DATA, str(year), "state.json")) or {}).get("complete"):
            out.append(f"{year}:first copy")
    return out


def main():
    if not key():
        raise SystemExit("No Open States API key (~/.openstates_api_key or OPENSTATES_API_KEY)")
    os.makedirs(DATA, exist_ok=True)
    if not os.path.exists(MARKER) and not any(n.isdigit() for n in os.listdir(DATA)):
        open(MARKER, "w").write("running\n")
    ids = {}
    stopped = ""
    try:
        ids = sessions()
        for year in sorted((y for y in ids if FIRST <= y <= YEAR), reverse=True):  # the current year first
            session(year, ids[year])
    except Stop as e:
        stopped = str(e)
    people()
    missing = never_downloaded(ids)
    print(f"run: {STATS['requests']} requests ({STATS['bills']} bills), {round((time.time() - START) / 60)} min; "
          f"{used_today()} of this script's {DAILY_MAX} used today (UTC)"
          + (f"; stopped at {stopped}, the next run resumes" if stopped else "")
          + (f"; {STATS['failures']} request failures" if STATS["failures"] else "; no request failures")
          + (f"; not finished: {' '.join(NOTES)}" if NOTES else "")
          + (f"; never downloaded: {' '.join(missing)}" if missing else "; nothing missing"), flush=True)
    # Only data never downloaded keeps Hawaii off the site.
    if missing:
        open(MARKER, "w").write(" ".join(missing) + "\n")
    elif os.path.exists(MARKER):
        os.remove(MARKER)


if __name__ == "__main__":
    main()
