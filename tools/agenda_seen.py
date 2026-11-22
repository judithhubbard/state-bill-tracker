#!/usr/bin/env python3
"""How much notice the public gets of committee meetings, state by state: when each bill first showed up on a committee
agenda (as this site's downloads saw it) against when the meeting is. Only collects for now; a page comes later.

Run by publish.yml after each build (about a second): it reads what the build already wrote, each built state's live
sessions' status files (_site/<st>/data/status_<session>.json, whose rows carry the committee meetings to come, from
the state converter's agendas(): build_data.py's status_inputs()), so no converter runs again and build_data.py never
reads the log (test/cache_key_check.py). One log per state, agenda_log/<st>.json, kept in its own Actions cache
(agenda-log-<run>), saved every run whether or not any state was rebuilt.

Each agenda item is keyed "<session>|<bill>|<committee>|<meeting time, the state's local time>" and records:
  first   the publish run that first saw it (UTC)
  seen    the state's download time then (data/<st>/last_checked, written by download.yml after each download; the run's
          time when there's none): the latest the item can have reached the site's downloads
  after   the state's download time at the run before: the earliest it can have (download runs are every 2 hours)
  last    the last run that saw it
  gone    the first run it was missing from (left out of the next build's status file the day after the meeting;
          before the meeting: canceled or moved); cleared if it comes back ("back" counts how often)
  moved   for an item that appeared when the same bill and committee lost a meeting still to come: that meeting's time
  start   it was already listed when the state's log began (its notice is unknown; left out of the numbers)
  gap     the state's previous look was over 12 hours before (a failed build, a lost cache): left out of the numbers

Usage:
  python3 tools/agenda_seen.py [--site _site] [--logs agenda_log] [--now 2026-11-22T10:00:00Z]   record one run
  python3 tools/agenda_seen.py --report [--logs agenda_log]                                       notice by state
"""
import argparse, json, os, re, sys
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GAP = timedelta(hours=12)
KEEP = timedelta(days=3 * 365)  # items whose meeting is older are dropped


def utc(s):
    return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def stamp(t):
    return t.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def zone(st):
    try:
        m = re.search(r'^TIMEZONE = "([^"]+)"', open(os.path.join(HERE, "states", st, "profile.py")).read(), re.M)
        return m.group(1)
    except (OSError, AttributeError):
        return "America/New_York"


def meeting_utc(when, tz):
    """A meeting's local "YYYY-MM-DDTHH:MM:SS" (some states give only the day: T00:00:00) in UTC."""
    try:
        return datetime.fromisoformat(when[:19]).replace(tzinfo=ZoneInfo(tz)).astimezone(timezone.utc)
    except ValueError:
        return None


def current_items(site, st):
    """{key: meeting time} for the bills on agendas in a built state's live sessions, or None if it isn't built."""
    try:
        index = json.load(open(os.path.join(site, st, "data", "status.json")))
    except (OSError, ValueError):
        return None
    items = {}
    for session, s in index.items():
        if not s.get("l") or (s.get("f") or {}).get("u"):
            continue
        try:
            bills = json.load(open(os.path.join(site, st, "data", f"status_{session}.json")))["bills"]
        except (OSError, ValueError, KeyError):
            continue
        for num, row in bills.items():
            # (A floor calendar's day carries its kind, [when, "Senate floor", "floor"(, "listed")]: logged the same way,
            # under the house's "committee", so its notice can be measured too.)
            for when, comm, *_ in (row[8] if len(row) > 8 and isinstance(row[8], list) else []):
                items[f"{session}|{num}|{comm}|{when}"] = when
    return items


def checked(st):
    try:
        t = open(os.path.join(HERE, "data", st, "last_checked")).read().strip()
        utc(t)
        return t
    except (OSError, ValueError):
        return ""


def record(site, logs, now):
    os.makedirs(logs, exist_ok=True)
    run = stamp(now)
    states = sorted(d for d in os.listdir(site) if os.path.isfile(os.path.join(site, d, "data", "status.json")))
    total = new = 0
    for st in states:
        cur = current_items(site, st)
        if cur is None:
            continue
        path = os.path.join(logs, f"{st}.json")
        try:
            log = json.load(open(path))
        except (OSError, ValueError):
            log = {"state": st, "tz": zone(st), "began": run, "runs": 0, "lastRun": "", "lastChecked": "", "items": {}}
        first_run = not log["runs"]
        gap = bool(log["lastRun"]) and now - utc(log["lastRun"]) > GAP
        seen = checked(st) or run
        items = log["items"]
        # Meetings still to come that disappeared this run, by session, bill and committee (for "moved").
        dropped = {}
        for k, it in items.items():
            if k not in cur and not it.get("gone"):
                it["gone"] = run
                m = meeting_utc(k.rsplit("|", 1)[1], log["tz"])
                if m and m > now:
                    dropped[k.rsplit("|", 1)[0]] = k.rsplit("|", 1)[1]
        for k, when in cur.items():
            it = items.get(k)
            if it:
                it["last"] = run
                if it.get("gone"):
                    it["gone"] = None
                    it["back"] = it.get("back", 0) + 1
                continue
            it = {"first": run, "seen": seen, "after": log["lastChecked"] or log["lastRun"], "last": run, "gone": None}
            if first_run:
                it["start"] = True
            elif gap:
                it["gap"] = True
            if k.rsplit("|", 1)[0] in dropped:
                it["moved"] = dropped[k.rsplit("|", 1)[0]]
            items[k] = it
            new += 1
        for k in [k for k in items if (m := meeting_utc(k.rsplit("|", 1)[1], log["tz"])) and now - m > KEEP]:
            del items[k]
        log.update(runs=log["runs"] + 1, lastRun=run, lastChecked=seen)
        tmp = path + ".tmp"
        with open(tmp, "w") as f:
            json.dump(log, f, separators=(",", ":"), sort_keys=True)
        os.replace(tmp, path)
        total += len(cur)
    print(f"agenda log: {len(states)} states, {total} agenda items listed, {new} new")


def pct(xs, p):
    if not xs:
        return None
    xs = sorted(xs)
    i = (len(xs) - 1) * p
    lo = int(i)
    return xs[lo] + (xs[min(lo + 1, len(xs) - 1)] - xs[lo]) * (i - lo)


def report(logs):
    files = sorted(f for f in os.listdir(logs) if f.endswith(".json")) if os.path.isdir(logs) else []
    if not files:
        print(f"no logs in {logs}")
        return
    head = f"{'state':5} {'since':10} {'runs':>5} {'items':>6} {'start':>6} {'gap':>4} {'late':>5} {'used':>5} " \
           f"{'p10':>6} {'median':>6} {'p90':>6} {'dayonly':>7} {'removed':>7} {'moved':>5}"
    print("notice in days: meeting time minus the download that first saw the bill on the agenda")
    print(head)
    for f in files:
        log = json.load(open(os.path.join(logs, f)))
        days, late, start, gap, dayonly, removed, moved = [], 0, 0, 0, 0, 0, 0
        for k, it in log["items"].items():
            when = k.rsplit("|", 1)[1]
            m = meeting_utc(when, log["tz"])
            if it.get("moved"):
                moved += 1
            if it.get("gone") and m and utc(it["gone"]) < m:
                removed += 1
            if it.get("start"):
                start += 1
                continue
            if it.get("gap"):
                gap += 1
                continue
            if not m:
                continue
            d = (m - utc(it["seen"])).total_seconds() / 86400
            if d < 0:
                late += 1
                continue
            dayonly += when[11:19] == "00:00:00"
            days.append(d)
        fmt = lambda x: "-" if x is None else f"{x:.1f}"
        print(f"{log['state']:5} {log['began'][:10]:10} {log['runs']:>5} {len(log['items']):>6} {start:>6} {gap:>4} "
              f"{late:>5} {len(days):>5} {fmt(pct(days, .1)):>6} {fmt(pct(days, .5)):>6} {fmt(pct(days, .9)):>6} "
              f"{dayonly:>7} {removed:>7} {moved:>5}")
    print("start: already listed when the log began; gap: first seen after a long gap; late: first seen after the "
          "meeting (all three left out); dayonly: meetings given without a time (counted from midnight); removed: "
          "dropped before the meeting; moved: listed again at another time")


def main():
    a = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    a.add_argument("--site", default=os.path.join(HERE, "_site"))
    a.add_argument("--logs", default=os.path.join(HERE, "agenda_log"))
    a.add_argument("--now", help="the run's time, for tests (UTC, 2026-11-22T10:00:00Z)")
    a.add_argument("--report", action="store_true")
    args = a.parse_args()
    if args.report:
        report(args.logs)
    else:
        record(args.site, args.logs, utc(args.now) if args.now else datetime.now(timezone.utc).replace(microsecond=0))


if __name__ == "__main__":
    main()
