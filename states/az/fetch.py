#!/usr/bin/env python3
"""Download Arizona's bills from Open States (https://v3.openstates.org/; free API key in ~/.openstates_api_key or the
OPENSTATES_API_KEY environment variable). Arizona's own data service, apps.azleg.gov, has robots.txt "Disallow: /", and
the owner decided (2026-10-31) to use Open States' public-domain data instead; see the az-open-states memory.

- Each regular session's bills, 20 to a request, with sponsors, actions, votes (member by member) and abstracts, into
  data/az/<year>/bills/<HB2001>.json. A finished session is read once; the current one asks only for bills updated since
  the last run (updated_since).
- The current legislators (data.openstates.org's public people file, as for Ohio) into data/az/openstates_people.csv.
Sessions are one a year ("57th-1st-regular" is 2025). One request every 6 seconds. The free tier allows 250 requests a
day (20 bills each), so a first copy of three sessions (about 300 requests) takes two days; then a day's changes are a
few requests.
Usage: python3 states/az/fetch.py
"""
import json, os, sys, time, urllib.error, urllib.parse, urllib.request
from datetime import date, datetime, timedelta, timezone

API = "https://v3.openstates.org"
PEOPLE = "https://data.openstates.org/people/current/az.csv"
DATA = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "az"))
AGENT = "statebilltracker.org (a nonprofit bill tracker; contact via github.com/judithhubbard)"
YEAR = date.today().year
INCOMPLETE = []


class QuotaUsed(Exception):
    pass


def key():
    k = os.environ.get("OPENSTATES_API_KEY") or ""
    if not k:
        try:
            k = open(os.path.expanduser("~/.openstates_api_key")).read()
        except OSError:
            pass
    return k.strip()


def get(path, params):
    url = f"{API}{path}?" + urllib.parse.urlencode(params, doseq=True)
    for attempt in range(5):
        time.sleep(6)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": AGENT, "X-API-KEY": key()})
            with urllib.request.urlopen(req, timeout=180) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code == 429:
                body = e.read().decode("utf-8", "replace")
                if "per day" in body or "/day" in body:
                    # The free tier allows 250 requests a day: stop, and resume from this page on the next run.
                    raise QuotaUsed(body)
                time.sleep(60 * (attempt + 1))  # over the per-minute limit: wait and try again
                continue
            if e.code in (401, 403):
                raise SystemExit(f"Open States refused the request ({e.code}): check the API key")
            time.sleep(10 * (attempt + 1))
        except Exception:
            time.sleep(10 * (attempt + 1))
    return None


def sessions():
    """Year -> Open States session id, for the regular sessions of the last three years."""
    j = get("/jurisdictions/ocd-jurisdiction/country:us/state:az/government", {"include": "legislative_sessions"}) or {}
    out = {}
    for s in j.get("legislative_sessions") or []:
        if "regular" in s["identifier"] and (s.get("start_date") or "")[:4].isdigit():
            y = int(s["start_date"][:4])
            if y >= YEAR - 2:
                out[y] = s["identifier"]
    return out


def begun(year):
    """Whether a year's session has convened (the second Monday of January): one listed earlier is read when it's there
    but its first copy never holds Arizona off the site."""
    return date.today() >= date(year, 1, 1 + (0 - date(year, 1, 1).weekday()) % 7 + 7)


def session(year, sid):
    folder = os.path.join(DATA, str(year), "bills")
    os.makedirs(folder, exist_ok=True)
    state_path = os.path.join(DATA, str(year), "state.json")
    try:
        state = json.load(open(state_path))
    except (OSError, ValueError):
        state = {}
    finished = state.get("complete") and year < YEAR
    if finished:
        return
    params = {"jurisdiction": "az", "session": sid, "per_page": 20, "sort": "updated_asc",
              "include": ["sponsorships", "actions", "votes", "abstracts", "sources"]}
    started = datetime.now(timezone.utc).replace(tzinfo=None).isoformat(timespec="seconds")
    if state.get("complete") and state.get("since"):
        params["updated_since"] = (datetime.fromisoformat(state["since"]) - timedelta(hours=6)).isoformat(timespec="seconds")
    # A first copy too long for one run resumes where the last stopped (pages are in order of last update).
    page, got = (state.get("page", 1) if not state.get("complete") else 1), 0
    while True:
        d = get("/bills", dict(params, page=page))
        if d is None:
            INCOMPLETE.append(f"{year}:page{page}")
            break
        state["page"] = page
        for b in d.get("results") or []:
            num = b["identifier"].replace(" ", "")
            json.dump(b, open(os.path.join(folder, f"{num}.json"), "w"), ensure_ascii=False)
            got += 1
        if page >= (d.get("pagination") or {}).get("max_page", 1):
            state.update(complete=True, since=state.get("first_started") or started, page=1)
            state.pop("first_started", None)
            break
        if not state.get("complete"):
            state.setdefault("first_started", started)
            json.dump(state, open(state_path, "w"))
        page += 1
    json.dump(state, open(state_path, "w"))
    print(f"{year} ({sid}): {got} bills saved", flush=True)


def main():
    if not key():
        raise SystemExit("No Open States API key (~/.openstates_api_key or OPENSTATES_API_KEY)")
    os.makedirs(DATA, exist_ok=True)
    try:
        for year, sid in sorted(sessions().items(), reverse=True):  # the current session first
            session(year, sid)
    except QuotaUsed as e:
        print(f"Open States' daily limit is used up ({e}); the next run continues")
        INCOMPLETE.append("daily limit")
    try:
        body = urllib.request.urlopen(urllib.request.Request(PEOPLE, headers={"User-Agent": AGENT}), timeout=60).read()
        open(os.path.join(DATA, "openstates_people.csv"), "wb").write(body)
    except Exception as e:
        print(f"people: {e}; kept the last copy")
    marker = os.path.join(DATA, "incomplete")
    # Only a session whose first copy isn't whole keeps Arizona off the site: a failed page or the daily limit during a
    # later run's update keeps the saved bills (the next run asks again from the same time).
    if INCOMPLETE:
        print(f"not read this run: {' '.join(INCOMPLETE)}")
    if any(not os.path.exists(os.path.join(DATA, str(y), "state.json")) or
           not json.load(open(os.path.join(DATA, str(y), "state.json"))).get("complete") for y in range(YEAR - 2, YEAR + 1)
           if begun(y)):
        INCOMPLETE.append("first copy")
        open(marker, "w").write(" ".join(INCOMPLETE) + "\n")
    elif os.path.exists(marker):
        os.remove(marker)


if __name__ == "__main__":
    main()
