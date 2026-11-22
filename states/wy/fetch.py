#!/usr/bin/env python3
"""Download Wyoming's bills from the Legislative Service Office's JSON API, the one wyoleg.gov's own pages use (no key;
its addresses are in https://wyoleg.gov/assets/config/config.jsonc: lsoServiceUrl https://lsoservice.wyoleg.gov and
apiUrl https://api.wyoleg.gov; neither host has a robots.txt). web.wyoleg.gov/LsoService/api/ answers the same paths
but is an older copy (its 2025 House list lacks a member seated mid-session), so it isn't used. One request at a time,
a second apart.

One session a year (a general session in odd years, a budget session in even years); bills don't carry over. For each
year of the shared window (states/window.py: this year and the four before, not before 2023; and next year's once bills
are numbered for it):
- The year's bill list (lsoservice /api/BillInformation/<year>: every HB, SF, HJ and SJ with its catch title, sponsor,
  last action and its date, chapter and enrolled numbers) into data/wy/<year>/bills.json.
- Each bill in full (/api/BillInformation/<year>/<HB0010>: actions with dates and house, sponsors, roll calls member
  by member (committee votes voteType "C", floor votes "F"), amendments, the LSO digest, summary and fiscal note as
  HTML, vetoes, signed date, chapter) into data/wy/<year>/bills/<HB0010>.json, without the bill's own text
  (currentBillHTML; the PDFs are linked). A finished year's bills are read once. This year's (and next year's) are
  read again when the list shows a new last action, date, chapter, enrolled number or signing (kept in seen.json),
  and otherwise in turn, the seventh of them read longest ago each run, so a fiscal note or digest added without an
  action is picked up within a week.
- The members (/api/legislator/<year>/H and /S: name, district, county, party, email, phone, home address,
  leadership position, the name roll calls use (voteName) and whether still serving) into members_H.json and
  members_S.json.
- The joint standing committees (api.wyoleg.gov /v1/Committee/List/<year>/J and /M, then /v1/Committee/Detail/<year>/
  <J09> for each): each has a House and a Senate side, which sit as that house's standing committee during the session
  ("H09 - Minerals"), with each member's chamber and chair. Into committees.json.
A finished year's members and committees are read once. data/wy/incomplete says "running" during a run and lists what
was never downloaded after it (a failed refresh keeps the last copy); it is removed when nothing is missing.
Usage: python3 states/wy/fetch.py [year]   (default: every year above; a single year leaves the marker alone)
"""
import glob, json, os, re, sys, time, urllib.error, urllib.parse, urllib.request
from datetime import date, datetime, timedelta, timezone
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
from states import window as W
from states import letters as L

LSO = "https://lsoservice.wyoleg.gov/api"
API = "https://api.wyoleg.gov/v1"
DATA = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "wy"))
AGENT = "statebilltracker.org (a nonprofit bill tracker; contact via github.com/judithhubbard)"
YEAR = date.today().year
ONLY = int(sys.argv[1]) if len(sys.argv) > 1 else None
REFRESH_DAYS = 7
# The list fields that change when something happens to a bill.
STAMP = ("lastAction", "lastActionDate", "chapter", "enrolledNumber", "signedDate", "isEngrossed")
INCOMPLETE = set()
READ = []  # the years this run reached (states/window.py's marks change only for these)
MISSING = object()  # a 404
MARKER = os.path.join(DATA, "incomplete")
WHOLE = [True]  # the last run left nothing missing (set in main)


def begun(year):
    """Whether a year's session has convened: the second Tuesday of January (general sessions, odd years) or the second
    Monday of February (budget sessions). Next year's, read once bills are numbered for it (members not yet listed),
    never holds Wyoming off the site before then."""
    month, weekday = (1, 1) if year % 2 else (2, 0)
    return date.today() >= date(year, month, 1 + (weekday - date(year, month, 1).weekday()) % 7 + 7)


def finish():
    if ONLY:
        return
    undone = {g for g in INCOMPLETE if not g[:4].isdigit() or begun(int(g[:4]))}
    # A year the window added back (2023) marks only itself (states/window.py).
    undone = set(W.settle(DATA, undone, READ))
    if undone:
        with open(MARKER, "w") as f:
            f.write(" ".join(sorted(undone)) + "\n")
    elif os.path.exists(MARKER):
        os.remove(MARKER)


def stop(why):
    print(f"{why}; stopping")
    if not WHOLE[0]:  # a refusal stops a first copy; once whole, the last copies stay
        INCOMPLETE.add("refused")
    finish()
    sys.exit(1)


def get(url):
    """The JSON at url; MISSING for a 404, None when it can't be read. Stops the run if the server refuses us or
    answers with something other than JSON (a bot challenge)."""
    refused = 0
    for attempt in range(4):
        time.sleep(1)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": AGENT, "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=120) as r:
                body = r.read()
                kind = r.headers.get("Content-Type") or ""
            if "json" not in kind:
                stop(f"{url}: answered {kind or 'no type'}, not JSON (a challenge page?)")
            return json.loads(body)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return MISSING
            if e.code in (401, 403):
                stop(f"{url}: refused ({e.code})")
            if e.code == 429:
                refused += 1
                if refused >= 2:
                    stop(f"{url}: too many requests (429) twice")
                time.sleep(60)
                continue
            time.sleep(10 * (attempt + 1))
        except (OSError, ValueError):
            time.sleep(10 * (attempt + 1))
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


def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def bills(year, folder, live):
    index = get(f"{LSO}/BillInformation/{year}")
    if not isinstance(index, list):
        print(f"{year}: no bill list; kept the last copy")
        index = load(os.path.join(folder, "bills.json"))
        if index is None:  # only a list never read holds the state off the site
            INCOMPLETE.add(f"{year}:list")
            return 0
    elif not index:
        return 0  # no bills numbered for this year yet
    else:
        save(os.path.join(folder, "bills.json"), index)
    index = [x for x in index if not x.get("specialSessionValue")]  # regular session only
    os.makedirs(os.path.join(folder, "bills"), exist_ok=True)
    seen_path = os.path.join(folder, "seen.json")
    seen = load(seen_path, {})  # {"HB0010": {"stamp": [...], "read": "2026-11-01T..."}}
    stamps = {x["bill"]: [x.get(k) for k in STAMP] for x in index}
    have = {n for n in stamps if os.path.exists(os.path.join(folder, "bills", f"{n}.json"))}
    todo = [n for n in sorted(stamps) if n not in have or (live and (seen.get(n) or {}).get("stamp") != stamps[n])]
    if live:  # and bills read more than a week ago, a seventh at most a run (runs are two hours apart), so every bill is read weekly
        week = (datetime.now(timezone.utc) - timedelta(days=REFRESH_DAYS)).strftime("%Y-%m-%dT%H:%M:%SZ")
        rest = sorted((n for n in have if n not in todo), key=lambda n: (seen.get(n) or {}).get("read", ""))
        todo += [n for n in rest[:-(-len(stamps) // REFRESH_DAYS)] if (seen.get(n) or {}).get("read", "") < week]
    got = 0
    for n in todo:
        d = get(f"{LSO}/BillInformation/{year}/{n}")
        if not isinstance(d, dict):
            print(f"{year} {n}: {'not found' if d is MISSING else 'failed'}")
            continue
        d.pop("currentBillHTML", None)  # the bill's own text; the PDFs are linked
        save(os.path.join(folder, "bills", f"{n}.json"), d)
        seen[n] = {"stamp": stamps[n], "read": now()}
        got += 1
        if got % 100 == 0:
            save(seen_path, seen)
            print(f"{year}: {got} of {len(todo)} read", flush=True)
    save(seen_path, seen)
    # A bill whose refresh failed keeps its last copy; only bills never read make the copy incomplete.
    if any(not os.path.exists(os.path.join(folder, "bills", f"{n}.json")) for n in stamps):
        INCOMPLETE.add(f"{year}:bills")
    print(f"{year}: {got} of {len(todo)} bills read ({len(stamps)} listed)", flush=True)
    return len(stamps)


def get_pdf(url):
    """A PDF's bytes, or None."""
    for attempt in range(3):
        time.sleep(1)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": AGENT})
            with urllib.request.urlopen(req, timeout=120) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code in (403, 404, 410):
                return None
            time.sleep(10 * (attempt + 1))
        except OSError:
            time.sleep(10 * (attempt + 1))
    return None


def veto_letters(year, folder, minutes=8):
    """The governor's veto letter each vetoed (or line-item vetoed) bill links ("Governor's Veto Message" / "Governor's
    Line Item Veto Message": wyoleg.gov/2025/Veto/HB0036-Veto.pdf), read once by OCR into vetoes/<HB0036>.json
    (states/letters.py's scanned(): the letters are scans with no text). At most `minutes` a run; the rest next run.
    Never holds Wyoming back."""
    if not L.ocr_ready():
        print(f"{year}: veto letters: pdftoppm or tesseract isn't installed", flush=True)
        return
    stop_at = time.time() + minutes * 60
    todo = []
    for path in sorted(glob.glob(os.path.join(folder, "bills", "*.json"))):
        n = os.path.basename(path)[:-5]
        link = next((v.get("vetoLinkPath") for v in (load(path) or {}).get("vetoes") or []
                     if re.search(r"Veto Message", v.get("vetoLinkText") or "", re.I) and v.get("vetoLinkPath")), None)
        if link and not os.path.exists(os.path.join(folder, "vetoes", f"{n}.json")):
            todo.append((n, "https://wyoleg.gov/" + urllib.parse.quote(link.lstrip("/"))))
    got = 0
    for n, url in todo:
        if time.time() > stop_at:
            break
        if L.scanned(os.path.join(folder, "vetoes"), n, url, get_pdf):
            got += 1
    print(f"{year}: veto letters: {got} of {len(todo)} read now", flush=True)


def members(year, folder, live):
    for house in ("H", "S"):
        path = os.path.join(folder, f"members_{house}.json")
        if os.path.exists(path) and not live:
            continue
        d = get(f"{LSO}/legislator/{year}/{house}")
        if not isinstance(d, list) or not d:
            print(f"{year}: no {house} member list; kept the last copy")
            if not os.path.exists(path):
                INCOMPLETE.add(f"{year}:members")
            continue
        save(path, d)
        print(f"{year}: {len(d)} members ({house})", flush=True)


def committees(year, folder, live):
    path = os.path.join(folder, "committees.json")
    if os.path.exists(path) and not live:
        return
    out = []
    last = {e["listing"].get("ownerID"): e["detail"] for e in load(path, []) or []
            if isinstance(e, dict) and e.get("detail") and isinstance(e.get("listing"), dict)}
    for kind in ("J", "M"):  # joint standing committees; Management Council
        d = get(f"{API}/Committee/List/{year}/{kind}")
        if not isinstance(d, dict):
            print(f"{year}: no {kind} committee list; kept the last copy")
            if not os.path.exists(path):
                INCOMPLETE.add(f"{year}:committees")
            return
        for c in d.get("committeeList") or []:
            detail = get(f"{API}/Committee/Detail/{year}/{c['ownerID']}")
            if not isinstance(detail, dict):
                detail = last.get(c["ownerID"])  # a failed refresh keeps the last copy's
                if detail is None:
                    INCOMPLETE.add(f"{year}:committees")
            else:  # the committee's history and reports aren't needed
                for k in ("commYears", "commReports", "interimTopics"):
                    detail.pop(k, None)
            out.append({"listing": c, "detail": detail})
    save(path, out)
    print(f"{year}: {len(out)} committees", flush=True)


def agendas(year):
    """Bills on committee agendas from yesterday to three weeks ahead, into data/wy/<year>/agendas.json:
    {"HB105": [["House Appropriations", "2026-02-09T16:00:00"], ...]}. From the calendar wyoleg.gov's own Calendar page
    reads (api.wyoleg.gov /v2/Calendar/Events/<YYYYMMDD>: about five weeks of meetings around the day, each with its
    committee, house (meetingType "House", "Senate", "Joint"), start (local time; "Upon Adjournment" meetings carry
    the day's 16:00) and the bills it takes up, sessionMeetingBills). Two requests a run (today and three weeks on).
    Never stops the run: a failure keeps the last copy."""
    first, last = (date.today() - timedelta(days=1)).isoformat(), (date.today() + timedelta(days=21)).isoformat()
    events, failed = {}, 0
    for day in (date.today(), date.today() + timedelta(days=21)):
        try:
            time.sleep(1)
            req = urllib.request.Request(f"{API}/v2/Calendar/Events/{day:%Y%m%d}",
                                         headers={"User-Agent": AGENT, "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=120) as r:
                got = json.loads(r.read())
        except Exception as e:
            print(f"agendas: calendar for {day}: {type(e).__name__}", flush=True)
            failed += 1
            continue
        for ev in got if isinstance(got, list) else []:
            events[ev.get("id")] = ev
    if failed == 2:
        print("agendas: calendar unreadable; kept the last copy", flush=True)
        return
    out, meetings = {}, 0
    for ev in events.values():
        when = ev.get("startDate") or ""
        name = ((ev.get("committee") or {}).get("shortName") or "").strip()
        house = ev.get("meetingType") or ""
        if not ev.get("sessionMeetingBills") or not first <= when[:10] <= last or not name or \
                house not in ("House", "Senate", "Joint") or "cancel" in json.dumps(ev.get("purpose") or "").lower():
            continue
        meetings += 1
        stamp = when[:19] if len(when) >= 19 else f"{when[:10]}T00:00:00"
        for b in ev["sessionMeetingBills"]:
            m = re.match(r"([A-Z]+)0*(\d+)$", (b.get("billNumber") or "").strip())
            if m:
                key, entry = f"{m.group(1)}{int(m.group(2))}", [f"{house} {name}", stamp]
                if entry not in out.setdefault(key, []):
                    out[key].append(entry)
    os.makedirs(os.path.join(DATA, str(year)), exist_ok=True)
    save(os.path.join(DATA, str(year), "agendas.json"), out)
    print(f"agendas: {len(out)} bills on {meetings} meetings", flush=True)


def main():
    os.makedirs(DATA, exist_ok=True)
    WHOLE[0] = not os.path.exists(MARKER)
    # A run cut off by its time limit leaves this, so a partial copy isn't published (cleared after a clean run).
    if not ONLY and not os.path.exists(MARKER):
        with open(MARKER, "w") as f:
            f.write("running\n")
    years = [ONLY] if ONLY else [YEAR + 1] + W.years()[::-1]  # the newest first
    for year in years:
        folder = os.path.join(DATA, str(year))
        live = year >= YEAR
        if year > YEAR:  # next year's session: only once bills are numbered for it
            index = get(f"{LSO}/BillInformation/{year}")
            if not index:
                continue
        os.makedirs(folder, exist_ok=True)
        members(year, folder, live)
        committees(year, folder, live)
        bills(year, folder, live)
        READ.append(year)
        try:
            veto_letters(year, folder)
        except Exception as e:  # never holds Wyoming back
            print(f"{year}: veto letters: failed ({type(e).__name__})", flush=True)
    if not ONLY:
        try:
            agendas(YEAR)  # never holds Wyoming back
        except Exception as e:
            print(f"agendas: failed ({type(e).__name__}); kept the last copy", flush=True)
    finish()


if __name__ == "__main__":
    main()
