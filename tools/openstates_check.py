#!/usr/bin/env python3
"""A daily cross-check of every state's live data against Open States (approved by the owner, 2026-11-25): an early warning
of silent failures, such as Montana's download hanging for two days (2026-11-23), a state's format changing, or a
legislature's website going down (West Virginia's, 2026-11-23 on). Not a second source: only numbers are compared.

For each live session the site shows (/status.json's "l": the current session, and the next one's prefiled bills), one
request to Open States' API v3: /bills?jurisdiction=..&session=..&classification=bill&sort=latest_action_desc&per_page=1,
whose pagination.total_items is the session's number of bills and whose one result is the bill with the newest action.
Compared with the site's own status file (_site/<st>/data/status_<session>.json: its bills, and the newest "last action"
day among them):

- Behind: Open States has an action newer than our newest. 3 days or more is a LOOK, 7 or more a FAIL (in session a
  legislature acts every week; out of session both sides are quiet and agree).
- Bills: the two counts never match exactly (ours keeps bills and constitutional amendments and merges some companion bills,
  New York's same-as bills, Rhode Island's twins; Open States' "bill" classification counts each house's bills, and some
  states' resolutions are classified as bills). So each state's ratio ours/theirs is kept day to day (.openstates-check/
  history.json, in an Actions cache) and compared with its own median over the last two weeks: a ratio 10% below it is a
  LOOK, 20% below a FAIL (bills lost). Until a state has three days' history, only a ratio under 0.5 is a LOOK.

The jurisdiction and session ids come from /jurisdictions?include=legislative_sessions (2 requests), kept in
.openstates-check/jurisdictions.json and read again weekly. Our session (its first year, 2025 for 2025-26) is Open States'
primary session starting that year. About 55 requests a day of the free tier's 250, shared with Arizona's fallback
(states/az/fetch.py): 6 seconds apart (the per-minute limit), and it stops at the daily limit (a LOOK, never a FAIL).

Usage: python3 tools/openstates_check.py [--site _site] [--states "ny nj"] [--dry-run] [--max N]
  --dry-run: print the mapping (our session -> Open States' session) and make no bill requests.
Prints LOOK and FAIL lines; writes them to $GITHUB_STEP_SUMMARY when set; exits 1 on a FAIL."""
import json, os, statistics, sys, time, urllib.error, urllib.parse, urllib.request
from datetime import date, datetime, timedelta

API = "https://v3.openstates.org"
AGENT = "statebilltracker.org (a nonprofit bill tracker; contact via github.com/judithhubbard)"
KEEP = os.environ.get("OPENSTATES_CHECK_DIR", ".openstates-check")
LAG_LOOK, LAG_FAIL = 3, 7  # days our newest action is behind Open States'
RATIO_LOOK, RATIO_FAIL = 0.90, 0.80  # today's ratio against the state's own recent median
JURISDICTION = {"us": "ocd-jurisdiction/country:us/government", "dc": "ocd-jurisdiction/country:us/district:dc/government"}


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


REQUESTS = [0]


def get(path, params):
    url = f"{API}{path}?" + urllib.parse.urlencode(params, doseq=True)
    for attempt in range(3):
        if REQUESTS[0]:
            time.sleep(6)
        REQUESTS[0] += 1
        try:
            req = urllib.request.Request(url, headers={"User-Agent": AGENT, "X-API-KEY": key()})
            with urllib.request.urlopen(req, timeout=90) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "replace")
            if e.code == 429 and ("per day" in body or "/day" in body):
                raise QuotaUsed(body[:200])
            if e.code == 429:
                time.sleep(60)
                continue
            if e.code in (401, 403):
                raise SystemExit(f"Open States refused the request ({e.code}): check the API key")
            if e.code == 404:
                return None
            time.sleep(10)
        except Exception:
            time.sleep(10)
    return None


def jid(st):
    return JURISDICTION.get(st, f"ocd-jurisdiction/country:us/state:{st}/government")


def jurisdictions():
    """Open States' jurisdiction id -> its legislative sessions, read again when a week old."""
    path = os.path.join(KEEP, "jurisdictions.json")
    try:
        saved = json.load(open(path))
        if (datetime.now() - datetime.fromisoformat(saved["at"])).days < 7:
            return saved["sessions"]
    except (OSError, ValueError, KeyError):
        saved = None
    out = {}
    for cls in ("state", "country"):
        page = 1
        while True:
            d = get("/jurisdictions", {"classification": cls, "include": "legislative_sessions", "per_page": 52, "page": page})
            if not d:
                break
            for j in d.get("results") or []:
                out[j["id"]] = [{k: s.get(k) for k in ("identifier", "name", "classification", "start_date", "end_date")}
                                for s in j.get("legislative_sessions") or []]
            if page >= (d.get("pagination") or {}).get("max_page", 1):
                break
            page += 1
    if JURISDICTION["dc"] not in out:  # (the District may be classified otherwise)
        d = get(f"/jurisdictions/{JURISDICTION['dc']}", {"include": "legislative_sessions"})
        if d:
            out[d["id"]] = [{k: s.get(k) for k in ("identifier", "name", "classification", "start_date", "end_date")}
                            for s in d.get("legislative_sessions") or []]
    if not out:
        return (saved or {}).get("sessions") or {}
    os.makedirs(KEEP, exist_ok=True)
    json.dump({"at": datetime.now().isoformat(timespec="seconds"), "sessions": out}, open(path, "w"), indent=0)
    return out


def os_session(sessions, year):
    """Open States' primary session starting in our session's first year (Texas: the regular, not a called session)."""
    # (Maine's and California's Legislatures are sworn in the December before: Maine's 132nd starts 2024-12-04.)
    cands = [s for s in sessions if (s.get("start_date") or "")[:4] == str(year)
             or (s.get("start_date") or "")[:7] == f"{year - 1}-12"] or \
            [s for s in sessions if str(year) in (s.get("identifier") or "")]
    primary = [s for s in cands if (s.get("classification") or "primary") == "primary"]
    pick = sorted(primary or cands, key=lambda s: s.get("start_date") or "9999")
    return pick[0]["identifier"] if pick else None


def ours(site, st, session):
    """(bills, newest last-action day) from the site's own status file."""
    try:
        d = json.load(open(os.path.join(site, st, "data", f"status_{session}.json")))
    except (OSError, ValueError):
        return None, None
    rows = list((d.get("bills") or {}).values())
    days = [r[3] for r in rows if len(r) > 3 and isinstance(r[3], str) and r[3][:4].isdigit() and r[3] <= date.today().isoformat()]
    return len(rows), max(days, default=None)


def main():
    args = sys.argv[1:]
    site = args[args.index("--site") + 1] if "--site" in args else "_site"
    only = set(args[args.index("--states") + 1].split()) if "--states" in args else None
    cap = int(args[args.index("--max") + 1]) if "--max" in args else 120
    dry = "--dry-run" in args
    if not key():
        print("LOOK openstates: no Open States API key (OPENSTATES_API_KEY); cross-check skipped")
        return 0
    status = json.load(open(os.path.join(site, "status.json")))
    try:
        juris = jurisdictions()
    except QuotaUsed as e:
        print(f"LOOK openstates: Open States' daily limit is used up ({e}); cross-check skipped")
        return 0
    hist_path = os.path.join(KEEP, "history.json")
    try:
        hist = json.load(open(hist_path))
    except (OSError, ValueError):
        hist = {}
    today = date.today().isoformat()
    lines, unmapped = [], []
    for st in sorted(status):
        if only and st not in only:
            continue
        for session, f in sorted(status[st].items()):
            if not f.get("l"):
                continue
            ident = os_session(juris.get(jid(st)) or [], int(session))
            if not ident:
                unmapped.append(f"{st} {session}")
                continue
            if dry:
                print(f"{st} {session} -> {jid(st)} session {ident!r}")
                continue
            if REQUESTS[0] >= cap:
                lines.append(("LOOK", f"openstates: stopped at {cap} requests; {st} {session} and later not checked"))
                break
            n, newest = ours(site, st, session)
            if n is None:
                lines.append(("LOOK", f"openstates {st} {session}: no status file in the built site to compare"))
                continue
            try:
                d = get("/bills", {"jurisdiction": jid(st), "session": ident, "classification": "bill",
                                   "sort": "latest_action_desc", "per_page": 1})
            except QuotaUsed as e:
                lines.append(("LOOK", f"openstates: daily limit used up at {st} {session}; the rest not checked ({e})"))
                break
            if not d:
                lines.append(("LOOK", f"openstates {st} {session}: no answer for session {ident!r}"))
                continue
            theirs = (d.get("pagination") or {}).get("total_items") or 0
            top = (d.get("results") or [{}])[0] if d.get("results") else {}
            their_day = (top.get("latest_action_date") or "")[:10]
            if their_day > today:
                their_day = today
            label = f"{st} {session}"
            # Behind: an action Open States has and we don't.
            if their_day and newest:
                lag = (date.fromisoformat(their_day) - date.fromisoformat(newest)).days
                if lag >= LAG_LOOK:
                    lines.append(("FAIL" if lag >= LAG_FAIL else "LOOK",
                                  f"{label}: our newest action is {newest}, Open States has {top.get('identifier', '?')} acted on "
                                  f"{their_day} ({lag} days later)"))
            elif their_day and not newest and n:
                lines.append(("LOOK", f"{label}: no dated action in our {n} bills; Open States' newest is {their_day}"))
            # Bills: today's ratio against the state's own recent median.
            if theirs:
                ratio = n / theirs
                past = [r for d_, r in sorted(hist.get(label, {}).items()) if d_ >= (date.today() - timedelta(days=14)).isoformat() and d_ != today]
                if len(past) >= 3:
                    med = statistics.median(past)
                    if med and ratio < med * RATIO_FAIL:
                        lines.append(("FAIL", f"{label}: {n} bills against Open States' {theirs} ({ratio:.2f}; usually {med:.2f}): bills lost?"))
                    elif med and ratio < med * RATIO_LOOK:
                        lines.append(("LOOK", f"{label}: {n} bills against Open States' {theirs} ({ratio:.2f}; usually {med:.2f})"))
                elif ratio < 0.5:
                    lines.append(("LOOK", f"{label}: {n} bills against Open States' {theirs} ({ratio:.2f}; no history yet)"))
                hist.setdefault(label, {})[today] = round(ratio, 4)
                hist[label] = dict(sorted(hist[label].items())[-30:])
            print(f"  {label}: ours {n} bills, newest {newest} | Open States {theirs} bills, newest {their_day} ({top.get('identifier', '')})",
                  flush=True)
    if unmapped:
        lines.append(("LOOK", f"openstates: no Open States session for {', '.join(unmapped)}"))
    if not dry:
        os.makedirs(KEEP, exist_ok=True)
        json.dump(hist, open(hist_path, "w"), indent=0)
    print(f"openstates: {REQUESTS[0]} requests")
    for level, msg in lines:
        print(f"{level} {msg}")
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary and lines:
        with open(summary, "a") as fh:
            fh.write("### Open States cross-check\n\n" + "\n".join(f"- **{lv}** {m}" for lv, m in lines) + "\n")
    return 1 if any(lv == "FAIL" for lv, _ in lines) else 0


if __name__ == "__main__":
    sys.exit(main())
