#!/usr/bin/env python3
"""Download Utah's bills from the Legislature's developer API (https://glen.le.utah.gov; documented at
https://le.utah.gov/data/developer.htm). The developer token is read from the UTAH_API_TOKEN environment variable or
~/.utah_api_token. It is the last part of every request's path, so no address is ever printed or saved: messages name
the route without it.

- Each general session's bill list (bills/<2026GS>/billlist: number, trackingID, updatetime) into
  data/ut/<year>/billlist.json, and each bill (bills/<2026GS>/<HB0001>: actions with vote tallies, sponsors, versions,
  subjects, the "General Description" and "Highlighted Provisions", agendas) into data/ut/<year>/bills/<HB0001>.json.
  A bill is read again only when its updatetime changes (kept in data/ut/<year>/state.json), so a finished session
  is read once. passedlist.json (governor's action per passed bill) and filelist.json (unnumbered requests) too.
  Special sessions (2025S1 ...) are left out. Bills don't carry over: one session a year.
- The current legislators (legislators.json) and committees with members and meetings (committees.json), and the
  meeting calendar (legcal.json), into the current year's folder. The API has no past rosters.
- Member-by-member votes: the API gives each vote's id and tally only. le.utah.gov's own bill pages link each roll
  call to /DynaBill/svotes.jsp (floor) and /mtgvotes.jsp (committee), which its robots.txt allows (it disallows /asp/,
  /jsp/, /RSS/ and /templates/, with Crawl-delay 10). Each recorded vote (not voice votes) is read once, ten seconds
  apart, into data/ut/<year>/votes.json: {"H74": {"yeas": [...], "nays": [...], "absent": [...]}, ...}, names as the
  page prints them ("Peterson, K.") with the House or Senate district where the page links it. The first copy of three
  sessions takes many hours, so it resumes where the last run stopped; `--votes-minutes N` caps one run's share.
The glen API is read one request at a time, about a second apart.
Usage: python3 states/ut/fetch.py [--no-votes] [--votes-minutes N]
"""
import html, json, os, re, sys, time, urllib.error, urllib.request
from datetime import date

API = "https://glen.le.utah.gov"
SITE = "https://le.utah.gov"
DATA = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "ut"))
AGENT = "statebilltracker.org (a nonprofit bill tracker; contact via github.com/judithhubbard)"
YEAR = date.today().year
YEARS = (YEAR, YEAR - 1, YEAR - 2)  # the current session first


class Refused(Exception):
    """The server turned us away (401/403, or 429 again and again): stop the run."""


def token():
    t = os.environ.get("UTAH_API_TOKEN") or ""
    if not t:
        try:
            t = open(os.path.expanduser("~/.utah_api_token")).read()
        except OSError:
            pass
    return t.strip()


def scrub(text):
    """Any text that might hold an address, with the token taken out."""
    t = token()
    return str(text).replace(t, "<token>") if t else str(text)


def fetch(url, label, pause, tries=4):
    """GET url (label is what messages call it: never the url itself, which may carry the token). None after
    repeated failures; Refused on 401/403 or repeated 429; 404 returns None at once."""
    too_many = 0
    for attempt in range(tries):
        time.sleep(pause)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": AGENT})
            with urllib.request.urlopen(req, timeout=120) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code in (401, 403):
                raise Refused(f"{label}: HTTP {e.code}")
            if e.code == 404:
                return None
            if e.code == 429:
                too_many += 1
                if too_many >= 3:
                    raise Refused(f"{label}: HTTP 429 three times")
                time.sleep(60 * too_many)
                continue
            print(f"{label}: HTTP {e.code}, trying again", flush=True)
        except Exception as e:  # no str(e): some exceptions quote the address
            print(f"{label}: {type(e).__name__}, trying again", flush=True)
        time.sleep(10 * (attempt + 1))
    return None


def api(route):
    """One API route ("bills/2026GS/billlist"), parsed, or None."""
    body = fetch(f"{API}/{route}/{token()}", route, 1)
    if body is None:
        return None
    try:
        return json.loads(body)
    except ValueError:
        print(f"{route}: not JSON", flush=True)
        return None


def save(obj, path):
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(obj, f, ensure_ascii=False)
    os.replace(tmp, path)


def load(path, default):
    try:
        return json.load(open(path))
    except (OSError, ValueError):
        return default


def session_bills(year):
    """The session's bill list, then each bill that is new or whose updatetime changed. Returns problems."""
    sid = f"{year}GS"
    folder = os.path.join(DATA, str(year))
    os.makedirs(os.path.join(folder, "bills"), exist_ok=True)
    listing = api(f"bills/{sid}/billlist")
    if not isinstance(listing, list):
        if year == YEAR and listing is None:
            print(f"{sid}: no bill list yet", flush=True)
            return []
        print(f"{sid}: bill list unreadable; kept the last copies", flush=True)
        # Only a list never read holds the state off the site (the API answered 504 all morning on 2026-11-08).
        return [] if os.path.exists(os.path.join(folder, "billlist.json")) else [f"{year}:billlist"]
    save(listing, os.path.join(folder, "billlist.json"))
    state_path = os.path.join(folder, "state.json")
    state = load(state_path, {})
    seen = state.setdefault("updated", {})
    todo = [b for b in listing if b.get("number") and
            (seen.get(b["number"]) != b.get("updatetime") or
             not os.path.exists(os.path.join(folder, "bills", f"{b['number']}.json")))]
    got = 0
    for b in todo:
        num = b["number"]
        bill = api(f"bills/{sid}/{num}")
        if isinstance(bill, dict) and (bill.get("billNumber") or bill.get("bill")):  # 2024's older layout: "bill"
            save(bill, os.path.join(folder, "bills", f"{num}.json"))
            seen[num] = b.get("updatetime")
            got += 1
            if got % 100 == 0:
                save(state, state_path)
                print(f"{sid}: {got} of {len(todo)}", flush=True)
    save(state, state_path)
    for name in ("passedlist", "filelist"):
        route = f"bills/{sid}/{name}" if name == "passedlist" else f"bills/{sid}/filelist"
        d = api(route)
        if d is not None:
            save(d, os.path.join(folder, f"{name}.json"))
    print(f"{sid}: {got} of {len(todo)} read ({len(listing)} listed)", flush=True)
    # A bill whose new version failed keeps its last copy; only bills never read make the copy incomplete.
    missing = [b["number"] for b in listing if b.get("number") and not os.path.exists(os.path.join(folder, "bills", f"{b['number']}.json"))]
    if got < len(todo):
        print(f"{sid}: {len(todo) - got} unreadable, {len(missing)} of them never read", flush=True)
    problems = [f"{year}:bills"] if missing else []
    return problems + status_pages(year, listing)


def parse_status(page):
    """A static bill page's "Bill Status / Votes" table: [{"date", "action", "location", "vote", "voteLink"}]."""
    i = page.find("Bill Status / Votes")
    if i < 0:
        return None
    table = page[i:]
    table = table[:table.lower().find("</table>")] if "</table>" in table.lower() else table
    rows = []
    for r in re.findall(r"<tr\b[^>]*>(.*?)</tr>", table, re.S | re.I):
        cells = re.findall(r"<td[^>]*>(.*?)</td>", r, re.S | re.I)
        if len(cells) < 4:
            continue
        text = [re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", c))).strip() for c in cells[:4]]
        if text[0] == "Date":
            continue
        link = re.search(r'href="([^"]*votes\.jsp[^"]*)"', cells[3], re.I)
        rows.append({"date": text[0], "action": text[1], "location": text[2], "vote": text[3],
                     "voteLink": html.unescape(link.group(1)) if link else ""})
    return rows


def status_pages(year, listing):
    """Bills in the API's older layout (2024: actions with dates only, no times, codes or votes) also get their static
    page's status table from le.utah.gov (/~2024/bills/static/HB0001.html, allowed by robots.txt), read once, ten seconds
    apart, into data/ut/<year>/status/<HB0001>.json: each action's date and time, and each vote's tally and link."""
    folder = os.path.join(DATA, str(year))
    out = os.path.join(folder, "status")
    todo = []
    for b in listing:
        num = b.get("number")
        bill = load(os.path.join(folder, "bills", f"{num}.json"), {}) if num else {}
        if bill and "actionHistoryList" not in bill and not os.path.exists(os.path.join(out, f"{num}.json")):
            todo.append(num)
    if not todo:
        return []
    os.makedirs(out, exist_ok=True)
    got = 0
    for num in todo:
        body = fetch(f"{SITE}/~{year}/bills/static/{num}.html", f"{year} page {num}", 10, tries=3)
        rows = parse_status(body.decode("utf-8", "replace")) if body else None
        if rows:
            save(rows, os.path.join(out, f"{num}.json"))
            got += 1
            if got % 100 == 0:
                print(f"{year} status pages: {got} of {len(todo)}", flush=True)
    print(f"{year} status pages: {got} of {len(todo)} read", flush=True)
    return [] if got == len(todo) else [f"{year}:status"]


def roster():
    """Current legislators, committees and the meeting calendar, into the current year's folder."""
    folder = os.path.join(DATA, str(YEAR))
    os.makedirs(folder, exist_ok=True)
    problems = []
    for route, key in (("legislators", "legislators"), ("committees", "committees"), ("legcal", None)):
        d = api(route)
        if d is None or (key and not (d.get(key) if isinstance(d, dict) else None)):
            print(f"{route}: unreadable; kept the last copy", flush=True)
            if key and not os.path.exists(os.path.join(folder, f"{route}.json")):
                problems.append(route)
            continue
        save(d, os.path.join(folder, f"{route}.json"))
        if key:
            print(f"{route}: {len(d[key])}", flush=True)
    return problems


# ---- roll calls from le.utah.gov --------------------------------------------------------------------------------

def _names(chunk):
    """[[name, district or ""], ...] from a block of a vote page."""
    out = []
    for m in re.finditer(r"<td[^>]*>(.*?)</td>|([^<>\n][^<>]*?)<br\s*/?>", chunk, re.S):
        cell = m.group(1) if m.group(1) is not None else m.group(2)
        dist = re.search(r"dist=(\d+)", cell)
        name = html.unescape(re.sub(r"<[^>]+>", " ", cell))
        name = re.sub(r"\s+", " ", name).strip()
        if name:
            out.append([name, dist.group(1) if dist else ""])
    return out


def parse_floor(page):
    """svotes.jsp: a heading block, then "Yeas - 73", "Nays - 0", "Absent or not voting - 2", each with a table."""
    parts = re.split(r"<font[^>]*size=\"5\"[^>]*>\s*(Yeas|Nays|Absent or not voting)\s*-\s*(\d+)\s*</font>", page)
    if len(parts) < 7:
        return None
    head = html.unescape(re.sub(r"<[^>]+>", "\n", parts[0]))
    out = {"head": [l.strip() for l in head.splitlines() if l.strip() and l.strip() != "-"][:12]}
    ok = True
    for i in range(1, len(parts) - 1, 3):
        key = {"Yeas": "yeas", "Nays": "nays"}.get(parts[i], "absent")
        out[key] = _names(parts[i + 2].split("</table>")[0])
        ok &= len(out[key]) == int(parts[i + 1])
    out["ok"] = ok
    return out


def parse_committee(page):
    """mtgvotes.jsp: committee, date, motion and bill lines, then a table with Yeas / Nays / Absent columns."""
    main = page[page.find("<main"):]
    main = main[:main.find("</main>")] if "</main>" in main else main
    m = re.search(r"<b>Yeas</b>\s*-\s*(\d+).*?<b>Nays</b>\s*-\s*(\d+).*?<b>Absent</b>\s*-\s*(\d+)\s*</td>\s*</tr>(.*?)</table>",
                  main, re.S)
    if not m:
        return None
    head = html.unescape(re.sub(r"<[^>]+>", "\n", main[:m.start()]))
    out = {"head": [l.strip() for l in head.splitlines() if l.strip() and l.strip() not in ("-", "Votes:")][:12]}
    cols = re.findall(r"<td valign=\"top\">(.*?)</td>", m.group(4), re.S)
    if len(cols) != 3:
        return None
    ok = True
    for key, col, n in zip(("yeas", "nays", "absent"), cols, m.groups()[:3]):
        out[key] = [[name, ""] for name in (html.unescape(re.sub(r"\s+", " ", x)).strip() for x in re.split(r"<br\s*/?>", col)) if name]
        ok &= len(out[key]) == int(n)
    out["ok"] = ok
    return out


def votes(minutes):
    """Each session's recorded votes not yet read, the current session first. Returns how many are left."""
    deadline = time.time() + minutes * 60 if minutes else None
    left = 0
    for year in YEARS:
        folder = os.path.join(DATA, str(year))
        path = os.path.join(folder, "votes.json")
        have = load(path, {})
        wanted = {}
        bills = os.path.join(folder, "bills")
        for name in sorted(os.listdir(bills)) if os.path.isdir(bills) else []:
            b = load(os.path.join(bills, name), {})
            for a in b.get("actionHistoryList") or []:
                vid = (a.get("voteID") or "").strip()
                if not vid or a.get("voiceVote") == "1":
                    continue
                if a.get("actionClass") == "A":
                    wanted[f"C{vid}"] = (f"{SITE}/mtgvotes.jsp?voteid={vid}", parse_committee)
                elif a.get("voteHouse") in ("H", "S"):
                    h = a["voteHouse"]
                    wanted[f"{h}{vid}"] = (f"{SITE}/DynaBill/svotes.jsp?sessionid={year}GS&voteid={vid}&house={h}", parse_floor)
        status = os.path.join(folder, "status")
        for name in sorted(os.listdir(status)) if os.path.isdir(status) else []:
            for a in load(os.path.join(status, name), []):
                link, tally = a.get("voteLink") or "", (a.get("vote") or "").lower()
                if not link or "voice" in tally:
                    continue
                m = re.search(r"mtgvotes\.jsp\?voteid=(\d+)", link)
                if m:
                    wanted[f"C{m.group(1)}"] = (f"{SITE}/mtgvotes.jsp?voteid={m.group(1)}", parse_committee)
                    continue
                m = re.search(r"voteid=(\d+)&house=([HS])", link)
                if m:
                    vid, h = m.groups()
                    wanted[f"{h}{vid}"] = (f"{SITE}/DynaBill/svotes.jsp?sessionid={year}GS&voteid={vid}&house={h}", parse_floor)
        todo = [k for k in sorted(wanted) if k not in have]
        got = bad = 0
        for k in todo:
            if deadline and time.time() > deadline:
                break
            url, parse = wanted[k]
            body = fetch(url, f"{year} vote {k}", 10, tries=3)  # le.utah.gov's robots.txt: Crawl-delay 10
            v = parse(body.decode("utf-8", "replace")) if body else None
            if v is None:
                bad += 1
                continue
            have[k] = v
            got += 1
            if got % 50 == 0:
                save(have, path)
        save(have, path)
        left += len(todo) - got
        print(f"{year} votes: {got} of {len(todo)} read ({len(wanted)} recorded votes; {bad} unreadable)", flush=True)
    return left


def main():
    args = sys.argv[1:]
    minutes = float(args[args.index("--votes-minutes") + 1]) if "--votes-minutes" in args else 0
    if not token():
        raise SystemExit("No Utah developer token (UTAH_API_TOKEN or ~/.utah_api_token)")
    os.makedirs(DATA, exist_ok=True)
    marker = os.path.join(DATA, "incomplete")
    whole = not os.path.exists(marker)  # the last run left nothing missing
    # A run cut off by its time limit leaves this, so a partial copy isn't published (cleared after a clean run).
    open(marker, "w").write("running\n")
    problems = []
    try:
        problems += roster()
        for year in YEARS:
            problems += session_bills(year)
        if "--no-votes" not in args:
            left = votes(minutes)
            if left:
                print(f"votes: {left} still to read; the next run continues", flush=True)
    except Refused as e:
        print(f"Stopped: the server refused a request ({scrub(e)})", flush=True)
        if not whole:  # a refusal stops a first copy; once whole, the last copies stay
            problems.append("refused")
    except Exception as e:
        if whole and not problems:
            os.remove(marker)  # the last copies stand as they were
        else:
            open(marker, "w").write(" ".join(problems + ["failed"]) + "\n")
        raise SystemExit(f"Failed: {type(e).__name__}: {scrub(e)}")
    if problems:
        open(marker, "w").write(" ".join(problems) + "\n")
    elif os.path.exists(marker):
        os.remove(marker)


if __name__ == "__main__":
    main()
