#!/usr/bin/env python3
"""Download Arizona's bills from the Legislature's own data service, apps.azleg.gov, with its webmaster's permission
(2026-11-24, states/az/NOTES.md: "This should be fine"), on the terms asked: each bill's status, actions and votes and
the session's member list; only bills changed since the last run, plus the session's bill list; one request every 10
seconds, identified as statebilltracker.org. (Its robots.txt is "Disallow: /": nothing else there is read.)

For each regular session from FIRST (2025, the 57th Legislature) on (2023 and 2024 stay Open States' finished copies):
- GET /api/Bill/?sessionId=<id>: the session's bill list (every measure, about 2,000, with its reading dates, the
  governor's action, chapter, final disposition ...), compressed, about 7 MB: read at most every LIST_EVERY hours (a
  finished session once a week). Each entry also carries the public's Request to Speak positions (names of people and
  groups): they're dropped on arrival, never saved.
- For each House or Senate bill, and each concurrent resolution, whose list entry changed since its last read (a
  signature of its fields, `sig()`), or never read:
  GET /api/Bill/?billNumber=HB2001&sessionId=<id>&legislativeBody=H&verbose=true (every committee and floor action, with
  tallies, and the transmittals), GET /api/BillSponsor/?id=<BillId> (prime and co-sponsors, with party), and for each
  third-reading or final vote with a recorded roll call, GET /api/BillStatusFloorAction/?billStatusId=..&
  billStatusActionId=..&includeVotes=true (each member's vote). Committee of the Whole and concurrence motions have no
  roll call and aren't asked for. So a bill that never left committee is 2 requests; a law about 5.
  Order (so a partial copy is right where it matters): laws and vetoes first, then bills that passed a house or failed
  on the floor, then the rest; within each, the newest activity first.
The first copy of 2025-26 is about 10,600 requests (about 30 hours at the 10-second pace), over many runs; then a run
reads the list and the few bills it shows changed. A session's copy is whole (data/az/azleg_api/<year>/complete) once
every bill on its list has been read; convert.py uses this source for that session only then.

Into data/az/azleg_api/: sessions.json, <year>/list.json (the list's fields, positions dropped), <year>/bills/<HB2001>.json
({"detail", "sponsors", "votes": {actionId: [...]}, "sig", "read"}), <year>/state.json, <year>/complete.
Usage: python3 states/az/fetch_azleg.py [--minutes N]   (default: 5 minutes before FETCH_MINUTES, else no limit)
"""
import gzip, hashlib, json, os, re, sys, time, urllib.error, urllib.request
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
from states.az import profile as P

API = "https://apps.azleg.gov/api"
AGENT = "statebilltracker.org (a nonprofit bill tracker; contact via github.com/judithhubbard)"
DELAY = 10.0  # the terms granted: one request every 10 seconds, never faster
FIRST = 2025  # the 57th Legislature (2025-26) on; 2023-24 stay Open States'
ROOT = os.path.join(P.DATA, "azleg_api")
LIST_EVERY = 4 * 3600  # the bill list at most this often (a session finished: a week)
STARTED = time.time()
_args = sys.argv[1:]
BUDGET = (float(_args[_args.index("--minutes") + 1]) if "--minutes" in _args else
          max(0.0, float(os.environ.get("FETCH_MINUTES") or 0) - 5)) * 60
_last = [0.0]
REQUESTS = [0]
KEEP = re.compile(r"^(HB|SB|HCR|SCR)\d+$")
# Floor actions whose roll call is the bill's own vote (the converter's passages and failures).
ROLL = {"THIRD", "FINAL", "RECON", "OVERRIDE"}


def out_of_time():
    return bool(BUDGET) and time.time() - STARTED > BUDGET


def call(path):
    """One GET, DELAY seconds after the last; parsed JSON, or None (a 404, or three failures)."""
    for attempt in range(3):
        wait = _last[0] + DELAY - time.time()
        if wait > 0:
            time.sleep(wait)
        _last[0] = time.time()
        REQUESTS[0] += 1
        req = urllib.request.Request(f"{API}/{path}", headers={"User-Agent": AGENT, "Accept": "application/json",
                                                               "Accept-Encoding": "gzip"})
        try:
            # (The bill lists are about 7 MB compressed; everything else is small. A stalled connection gives up.)
            with urllib.request.urlopen(req, timeout=300 if path.startswith("Bill/?sessionId") else 60) as r:
                body = r.read()
                if r.headers.get("Content-Encoding") == "gzip":
                    body = gzip.decompress(body)
                return json.loads(body.decode("utf-8"))
        except urllib.error.HTTPError as e:
            print(f"{path}: HTTP {e.code}", flush=True)
            if e.code in (400, 404):
                return None
            if e.code in (403, 429):
                raise SystemExit(f"apps.azleg.gov answered {e.code}: stopping (the terms: stop at once if asked)")
        except (OSError, ValueError) as e:
            print(f"{path}: {type(e).__name__}", flush=True)
    return None


def load(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def save(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path + ".tmp", "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, separators=(",", ":"))
    os.replace(path + ".tmp", path)


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def age(stamp):
    try:
        return time.time() - datetime.fromisoformat(stamp).timestamp()
    except (TypeError, ValueError):
        return float("inf")


def scalars(x):
    """A list or detail entry without its lists (positions, actions) and nested records."""
    return {k: v for k, v in x.items() if not isinstance(v, (list, dict))}


def sig(entry):
    return hashlib.sha1(json.dumps(scalars(entry), sort_keys=True).encode()).hexdigest()[:16]


def sessions():
    """Year -> SessionId for the regular sessions from FIRST ("2026 - Fifty-seventh Legislature - Second Regular
    Session"); asked for once a month."""
    path = os.path.join(ROOT, "sessions.json")
    got = load(path, {})
    if age(got.get("read")) > 30 * 86400:
        rows = call("Session/")
        if rows:
            got = {"read": now(), "rows": [{"id": r["SessionId"], "code": r["Code"], "name": r["Name"]} for r in rows]}
            save(path, got)
    out = {}
    for r in got.get("rows", []):
        m = re.match(r"(\d{4}) - .* Regular Session", r["name"])
        if m and int(m.group(1)) >= FIRST:
            out[int(m.group(1))] = r["id"]
    return out


def activity(e):
    """The latest date the list shows for a bill (for the order)."""
    ds = [v for k, v in e.items() if isinstance(v, str) and re.match(r"\d{4}-\d\d-\d\dT", v)]
    return max(ds, default="")


def rank(e):
    """0: laws and vetoes; 1: passed a house or failed on the floor; 2: the rest."""
    if e.get("GovernorAction") or e.get("ChapterNumber"):
        return 0
    other = e.get("Senate1stRead") if e["Number"][0] == "H" else e.get("House1stRead")
    if other or re.search(r"Third Reading|Committee of Whole|Concurrence|Final", e.get("FinalDisposition") or ""):
        return 1
    return 2


def kinds(year):
    """Concurrent resolution -> "amendment" | "measure" | "other", from www.azleg.gov's official titles (azleg.py's
    resolutions.json)."""
    return {k: v.get("kind") for k, v in load(os.path.join(P.DATA, "azleg", "resolutions.json"), {}).get(str(year), {}).items()}


def wanted(e, kind):
    """House and Senate bills, and the concurrent resolutions that propose constitutional amendments (or aren't known
    yet): the only measures the site shows (convert.py)."""
    n = e["Number"]
    return n[:2] in ("HB", "SB") or kind.get(n) in (None, "amendment")


def read_bill(year, sid, e):
    """A bill's status record, sponsors and roll calls -> the saved record, or None if the status didn't load."""
    num = e["Number"]
    detail = call(f"Bill/?billNumber={num}&sessionId={sid}&legislativeBody={num[0]}&verbose=true")
    if not isinstance(detail, dict) or not detail.get("BillId"):
        return None
    detail.pop("BillPositions", None)  # the public's Request to Speak positions: never kept
    sponsors = call(f"BillSponsor/?id={detail['BillId']}")
    if sponsors is None:
        return None
    votes = {}
    for h in detail.get("FloorHeaders") or []:
        if h.get("CommitteeShortName") in ROLL and (h.get("TotalVotes") or 0) > 0:
            got = call(f"BillStatusFloorAction/?billStatusId={detail['BillId']}&billStatusActionId={h['BillStatusActionId']}&includeVotes=true")
            if got is None:
                return None
            votes[str(h["BillStatusActionId"])] = got
    return {"detail": detail, "sponsors": sponsors, "votes": votes, "sig": sig(e), "read": now()}


def main():
    years = sessions()
    # (For tests: --year 2025 reads one session; --bills HB2001,SB1002 only those bills.)
    if "--year" in _args:
        years = {y: s for y, s in years.items() if y == int(_args[_args.index("--year") + 1])}
    only = set(_args[_args.index("--bills") + 1].split(",")) if "--bills" in _args else None
    todo = []
    for year, sid in sorted(years.items(), reverse=True):
        folder = os.path.join(ROOT, str(year))
        state = load(os.path.join(folder, "state.json"), {})
        finished = os.path.exists(os.path.join(folder, "complete")) and year < datetime.now().year
        if age(state.get("list")) > (7 * 86400 if finished else LIST_EVERY):
            got = call(f"Bill/?sessionId={sid}")
            if isinstance(got, dict) and got.get("ListItems"):
                rows = [scalars(x) for x in got["ListItems"] if KEEP.match(x.get("Number") or "")]
                save(os.path.join(folder, "list.json"), rows)
                state["list"] = now()
                save(os.path.join(folder, "state.json"), state)
                print(f"{year}: the bill list, {len(rows)} bills and concurrent resolutions", flush=True)
        kind = kinds(year)
        rows = [e for e in load(os.path.join(folder, "list.json"), []) if wanted(e, kind)]
        for e in rows:
            path = os.path.join(folder, "bills", f"{e['Number']}.json")
            saved = load(path, {}) if os.path.exists(path) else {}
            if saved.get("sig") != sig(e) and (only is None or e["Number"] in only):
                todo.append((rank(e), activity(e), year, sid, e, path))
    # Laws and vetoes first, then passed a house, then the rest; the newest activity first within each.
    todo.sort(key=lambda t: t[1], reverse=True)
    todo.sort(key=lambda t: t[0])
    print(f"{len(todo)} bills to read", flush=True)
    done = 0
    for _, _, year, sid, e, path in todo:
        if out_of_time():
            break
        rec = read_bill(year, sid, e)
        if rec:
            save(path, rec)
            done += 1
            if done % 25 == 0:
                print(f"  {done} read ({REQUESTS[0]} requests, {round((time.time() - STARTED) / 60)} minutes)", flush=True)
    for year in years:
        folder = os.path.join(ROOT, str(year))
        kind = kinds(year)
        rows = [e for e in load(os.path.join(folder, "list.json"), []) if wanted(e, kind)]
        missing =[e["Number"] for e in rows if not os.path.exists(os.path.join(folder, "bills", f"{e['Number']}.json"))]
        if rows and not missing and not os.path.exists(os.path.join(folder, "complete")):
            open(os.path.join(folder, "complete"), "w").write(now())
            print(f"{year}: every bill read; the site can use this copy", flush=True)
        elif missing:
            print(f"{year}: {len(missing)} of {len(rows)} bills not read yet", flush=True)
    print(f"{done} bills read, {REQUESTS[0]} requests, {round((time.time() - STARTED) / 60)} minutes", flush=True)


if __name__ == "__main__":
    main()
