#!/usr/bin/env python3
"""A daily cross-check of every state's live data against Open States (approved by the owner, 2026-11-25): an early warning
of silent failures, such as Montana's download hanging for two days (2026-11-23), a state's format changing, or a
legislature's website going down (West Virginia's, 2026-11-23 on). Not a second source: only numbers are compared.

For each live session the site shows (/status.json's "l": the current session, and the next one's prefiled bills), one
request to Open States' API v3: /bills?jurisdiction=..&session=..&classification=bill&sort=latest_action_desc&per_page=1,
whose pagination.total_items is the session's number of bills and whose one result is the bill with the newest action.
Compared with the site's own status file (_site/<st>/data/status_<session>.json: its bills, and the newest "last action"
day among them):

- Behind: one of the five bills Open States saw act most recently (the request asks for five, with their actions) has a
  real step newer than our own record of that bill, or isn't in our data at all. A real step is a classified action dated
  no later than today that isn't paperwork (effective dates, often in the future; fiscal notes; filing with the Secretary of
  State; printer and enrollment lines); resolutions Open States classifies as bills (Nevada's "SR 9") are skipped. 3 days
  or more is a LOOK, 7 or more a FAIL. (Until 2026-11-25 it compared Open States' newest action of any kind with our newest
  day: the first run's six FAILs, GA, IA, MN, ND, NM and NV, were all paperwork, future effective dates or a resolution.)
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
import json, os, re, statistics, sys, time, urllib.error, urllib.parse, urllib.request
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
    """(bills, newest last-action day, {number: last-action day}) from the site's own status file."""
    try:
        d = json.load(open(os.path.join(site, st, "data", f"status_{session}.json")))
    except (OSError, ValueError):
        return None, None, {}
    bills = d.get("bills") or {}
    rows = list(bills.values())
    ok = lambda x: isinstance(x, str) and x[:4].isdigit() and x <= date.today().isoformat()
    days = [r[3] for r in rows if len(r) > 3 and ok(r[3])]
    # {number: (last-action day, stage)}: whether Open States shows a bill further along is decided on the stage.
    last = {norm(k): ((r[3] if len(r) > 3 and ok(r[3]) else ""), (r[2] if len(r) > 2 and isinstance(r[2], int) else 0))
            for k, r in bills.items()}
    for other, lead in (d.get("alias") or {}).items():
        if norm(lead) in last:
            last.setdefault(norm(other), last[norm(lead)])
    return len(rows), max(days, default=None), last


def norm(num):
    """"HB 1234", "H.B.1234", "HB1234A" -> "HB1234" (a version letter left off)."""
    n = re.sub(r"[\s.]", "", num or "").upper()
    return re.sub(r"(?<=\d)[A-Z]$", "", n)


# What we don't record as a step, so it can't put us "behind" (2026-11-25, the first run's six false alarms): effective
# dates (often future: Georgia SB 160's "2028-07-01"), fiscal notes, explanations of votes, filing with the Secretary of
# State (North Dakota's, classified "introduction"), printer and enrollment paperwork, chapter numbers given afterwards.
PAPERWORK = re.compile(r"effective date|fiscal note|explanation of vote|filed with (?:the )?secretary of state|"
                       r"secretary of state|printer|enroll|chapter \d+|act \d+$|transmitted to|journal", re.I)
# Resolutions Open States classifies as bills (Nevada's "SR 9"): we keep bills and constitutional amendments only.
RESOLUTION = re.compile(r"^[A-Z]{0,3}R\d")  # (on norm()'s form: SR9, HCR3, SJR5, HR12; Congress's HR is a bill)


def their_stage(bill):
    """How far Open States shows a bill (our stage numbers: 2 passed one house, 3 both, 4 sent to the governor, 5 law,
    6 vetoed), from its classified steps. Dates aren't compared (2026-11-25: Alaska's HB 10 "VETOED BY GOVERNOR 8/31/26" is
    dated the day Open States posted it, Sep 30; Montana's HB 643 has "Chapter Number Assigned" a week after its override)."""
    kinds = [c for a in bill.get("actions") or [] for c in (a.get("classification") or [])
             if not PAPERWORK.search(a.get("description") or "") or c in ("became-law", "executive-signature")]
    if "became-law" in kinds or "executive-signature" in kinds or "veto-override-passage" in kinds:
        return 5
    if "executive-veto" in kinds:
        return 6
    if "executive-receipt" in kinds:
        return 4
    n = kinds.count("passage")
    return 3 if n >= 2 else 2 if n == 1 else 0


def behind(ours_stage, theirs):
    """Whether our record is short of where Open States has the bill (a law or a veto, either way, counts as decided)."""
    if theirs >= 5:
        return ours_stage < 5
    return ours_stage < theirs


def newest_step(bill):
    """The day of a bill's newest real step in Open States (classified, dated no later than today, not paperwork)."""
    today = date.today().isoformat()
    days = [(a.get("date") or "")[:10] for a in bill.get("actions") or []
            if (a.get("classification") or []) and (a.get("date") or "")[:10] <= today
            and not PAPERWORK.search(a.get("description") or "")]
    return max(days, default="")


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
            n, newest, last = ours(site, st, session)
            if n is None:
                lines.append(("LOOK", f"openstates {st} {session}: no status file in the built site to compare"))
                continue
            try:
                # (The five bills Open States saw act most recently, with their actions: each compared with our own
                # record of the same bill, one request as before.)
                d = get("/bills", {"jurisdiction": jid(st), "session": ident, "classification": "bill",
                                   "sort": "latest_action_desc", "per_page": 5, "include": "actions"})
            except QuotaUsed as e:
                lines.append(("LOOK", f"openstates: daily limit used up at {st} {session}; the rest not checked ({e})"))
                break
            if not d:
                lines.append(("LOOK", f"openstates {st} {session}: no answer for session {ident!r}"))
                continue
            theirs = (d.get("pagination") or {}).get("total_items") or 0
            label = f"{st} {session}"
            # Behind: a real step Open States has on a bill and our record of that bill doesn't (each of the five
            # compared with its own record, not our newest day with theirs: paperwork and future effective dates gave
            # six false alarms on the first run).
            worst, top, their_day = None, {}, ""
            for b in d.get("results") or []:
                num = norm(b.get("identifier"))
                if st != "us" and RESOLUTION.match(num):
                    continue
                step = newest_step(b)
                if not step:
                    continue
                if step > their_day:
                    top, their_day = b, step
                rec = last.get(num)
                mine, mine_stage = rec if rec else (None, 0)
                if rec is None:
                    gap = (date.fromisoformat(step) - date.fromisoformat(newest)).days if newest else 0
                    if gap >= LAG_LOOK:
                        worst = max(worst or (0, ""), (gap, f"{b.get('identifier')} isn't in our data (Open States: a step on {step})"))
                    continue
                st_their = their_stage(b)
                if mine and step > mine and behind(mine_stage, st_their):
                    lag = (date.fromisoformat(step) - date.fromisoformat(mine)).days
                    if lag >= LAG_LOOK:
                        worst = max(worst or (0, ""), (lag, f"{b.get('identifier')}: we show stage {mine_stage} (last action {mine}), Open States shows it further along (stage {st_their}, a step on {step})"))
            if worst:
                lines.append(("FAIL" if worst[0] >= LAG_FAIL else "LOOK", f"{label}: {worst[1]} ({worst[0]} days later)"))
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
