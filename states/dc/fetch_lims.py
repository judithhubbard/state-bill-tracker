#!/usr/bin/env python3
"""Download the District of Columbia's bills from the Council's own Legislative Information Management System (LIMS,
lims.dccouncil.gov), through its public API with the owner's developer key (~/.dc_lims_key, or the DC_LIMS_KEY variable
in GitHub's runs; sent as the "Authorization" header, never printed). The owner's decision (2026-11-24,
states/dc/NOTES.md): the Council issues keys so programs can use the API, though LIMS's robots.txt says "Disallow: /";
we read it gently: one request every 3 seconds, identified as statebilltracker.org, and only what changed.

Each run, for each Council Period in the window (states/window.py; 25 = 2023-24, 26 = 2025-26, 27 once LIMS lists it):
- POST /api/v2/PublicData/BulkData/1/<period>: every bill ("Bill" category: permanent, emergency, temporary and
  congressional review emergency bills) with its whole history, its act and law numbers and status, in one answer
  (about 2 MB, 880 bills for the 26th Council). A finished period's list is read once a day.
- GET /api/v2/PublicData/LegislationDetails/<B26-0164>, for each permanent bill whose list entry changed since its
  details were read (a signature of its history, status, numbers and title: `sig()`), or never read: the introducers,
  co-introducers and co-sponsors as lists, the Secretary's abstract ("BILL SUMMARY - As introduced, ..."), the
  committees, hearings and mark-ups, the Mayor's and Congress's review dates, and every meeting action with its vote,
  member by member (voice votes included). Also re-read when 30 days old (a few a run), in case a vote changed alone.
- GET /api/v2/PublicData/Members/<period>: the period's Councilmembers (names, start and end dates), once a day.
The first copy is about 950 detail requests (48 minutes); later runs read a few.

Into data/dc/lims/<period>/: bulk.json, members.json, details/<number>.json, meta.json ({"bulk": time, "members": time,
"details": {number: [signature, time]}}).
Usage: python3 states/dc/fetch_lims.py [--minutes N] [period ...]   (--minutes: stop reading details after N minutes;
the rest come next run. Default: 5 minutes before FETCH_MINUTES, or no limit.)
"""
import hashlib, json, os, sys, time, urllib.error, urllib.request
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
from states import window as W
from states.dc import profile as P

API = "https://lims.dccouncil.gov/api/v2/PublicData"
AGENT = "statebilltracker.org (a nonprofit bill tracker; contact via github.com/judithhubbard)"
DELAY = 3.0
ROOT = os.path.join(P.DATA, "lims")
# The run's time limit (FETCH_MINUTES, from the workflow): stop a few minutes early with what's read so far saved.
BUDGET = max(0.0, float(os.environ.get("FETCH_MINUTES") or 0) - 5) * 60
STARTED = time.time()
REREAD = 30 * 86400  # details re-read after a month, at most REREAD_MAX a run
REREAD_MAX = 20
_last = [0.0]


def key():
    k = os.environ.get("DC_LIMS_KEY") or ""
    if not k:
        try:
            k = open(os.path.expanduser("~/.dc_lims_key")).read()
        except OSError:
            pass
    k = k.strip()
    if not k:
        raise SystemExit("No LIMS key: set DC_LIMS_KEY or write ~/.dc_lims_key")
    return k


def out_of_time():
    return bool(BUDGET) and time.time() - STARTED > BUDGET


def call(path, post=False, body=None):
    """One request to the API, DELAY seconds after the last; the parsed JSON, or None after three tries."""
    for attempt in range(3):
        wait = _last[0] + DELAY - time.time()
        if wait > 0:
            time.sleep(wait)
        _last[0] = time.time()
        data = json.dumps(body).encode() if body is not None else (b"" if post else None)
        req = urllib.request.Request(f"{API}/{path}", data=data, method="POST" if post else "GET",
                                     headers={"User-Agent": AGENT, "Authorization": KEY, "Accept": "application/json",
                                              **({"Content-Type": "application/json"} if data is not None else {})})
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            print(f"{path}: HTTP {e.code}", flush=True)
            if e.code in (401, 403, 404):
                return None
        except (OSError, ValueError) as e:
            print(f"{path}: {type(e).__name__}", flush=True)
        time.sleep(10 * (attempt + 1))
    return None


def save(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path + ".tmp", "w") as f:
        json.dump(obj, f, ensure_ascii=False)
    os.replace(path + ".tmp", path)


def load(path, default=None):
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def sig(b):
    """What a bill's list entry says, as a short hash: a change means its details may have changed."""
    keep = [b.get(k) for k in ("title", "status", "actResNumber", "lawNumber", "projectedLawDate", "committeeReferral",
                               "committeeReReferral", "coSponsors", "introducedBy")]
    keep.append([(h.get("actionDate"), h.get("actionDescription")) for h in b.get("legislationHistory") or []])
    return hashlib.sha1(json.dumps(keep, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:16]


def periods():
    """The Council Periods in the window, by LIMS's own list: {period: first year}."""
    ps = call("CouncilPeriods") or []
    first = W.first_session()
    out = {}
    for p in ps:
        y = int((p.get("startDate") or "0")[:4] or 0)
        if y >= first and y <= date.today().year:
            out[int(p["councilPeriodId"])] = y
    return out


def period(pid, year):
    folder = os.path.join(ROOT, str(pid))
    meta = load(os.path.join(folder, "meta.json"), {}) or {}
    meta.setdefault("details", {})
    finished = year + 1 < date.today().year
    day = 86400
    if not os.path.exists(os.path.join(folder, "members.json")) or time.time() - meta.get("members", 0) > day:
        m = call(f"Members/{pid}")
        if isinstance(m, list) and m:
            save(os.path.join(folder, "members.json"), m)
            meta["members"] = time.time()
    bulk_path = os.path.join(folder, "bulk.json")
    if not os.path.exists(bulk_path) or not finished or time.time() - meta.get("bulk", 0) > day:
        bulk = call(f"BulkData/1/{pid}", post=True)
        if isinstance(bulk, list) and bulk:
            old = load(bulk_path, []) or []
            if len(bulk) < 0.9 * len(old):  # (an answer cut short never replaces the last copy)
                print(f"period {pid}: the list has {len(bulk)} bills, the last copy {len(old)}; kept the last copy", flush=True)
            else:
                save(bulk_path, bulk)
                meta["bulk"] = time.time()
        else:
            print(f"period {pid}: no bill list in the answer; kept the last copy", flush=True)
    bulk = load(bulk_path, []) or []
    perm = [b for b in bulk if b.get("legislationSubCategory") == "Permanent Bill"]
    now = time.time()
    todo = [b for b in perm if (meta["details"].get(b["legislationNumber"]) or [None])[0] != sig(b)
            or not os.path.exists(os.path.join(folder, "details", b["legislationNumber"] + ".json"))]
    stale = sorted((b for b in perm if b not in todo and now - (meta["details"].get(b["legislationNumber"]) or [0, 0])[1] > REREAD),
                   key=lambda b: (meta["details"].get(b["legislationNumber"]) or [0, 0])[1])[:REREAD_MAX]
    # Newest activity first: the bills that just moved reach the site first when a run runs out of time.
    last = lambda b: max([_iso(h.get("actionDate")) for h in b.get("legislationHistory") or []] + [""])
    todo.sort(key=last, reverse=True)
    got = 0
    for b in todo + stale:
        if out_of_time():
            break
        n = b["legislationNumber"]
        d = call(f"LegislationDetails/{n}")
        if isinstance(d, dict) and d.get("legislationNumber") == n:
            save(os.path.join(folder, "details", n + ".json"), d)
            meta["details"][n] = [sig(b), time.time()]
            got += 1
        if got % 25 == 0:
            save(os.path.join(folder, "meta.json"), meta)
    # (The build reads a period from LIMS only once every permanent bill's details are in: `whole`, lims_source.available().)
    left = sum(1 for b in perm if not os.path.exists(os.path.join(folder, "details", b["legislationNumber"] + ".json")))
    if perm and not left:
        meta["whole"] = True
    save(os.path.join(folder, "meta.json"), meta)
    print(f"period {pid} ({year}-{str(year + 1)[2:]}): {len(bulk)} bills listed, {len(perm)} permanent; {got} details read"
          + (f", {left} left for the next run" if left > 0 else ""), flush=True)
    return left


MONTHS = {m: i for i, m in enumerate("jan feb mar apr may jun jul aug sep oct nov dec".split(), 1)}


def _iso(s):
    """"Jan 06, 2025" -> "2025-01-06"."""
    try:
        m, d, y = (s or "").replace(",", "").split()
        return f"{y}-{MONTHS[m[:3].lower()]:02d}-{int(d):02d}"
    except (ValueError, KeyError):
        return ""


KEY = ""

if __name__ == "__main__":
    args = sys.argv[1:]
    if "--minutes" in args:
        i = args.index("--minutes")
        BUDGET = float(args[i + 1]) * 60
        del args[i:i + 2]
    KEY = key()
    ps = periods()
    if not ps:
        raise SystemExit("LIMS: no Council Periods in the answer")
    want = [int(a) for a in args] or sorted(ps, reverse=True)
    for pid in want:
        if pid in ps:
            period(pid, ps[pid])
