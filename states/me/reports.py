#!/usr/bin/env python3
"""Who signed each of a Maine committee's divided reports, from the bill's page on the Legislature's site
(legislature.maine.gov/legis/bills/display_ps.asp?LD=307&snum=132, its "Divided Reports" box), kept in
data/me/reports.json for states/me/convert.py, which shows them in History as the committee's report (votes of kind "R":
signatures, never counted as votes).

Maine's joint committees report unanimously or in a divided report: a majority and a minority report ("MAJ - Ought To
Pass As Amended", "MIN - Ought Not To Pass"), or three or more ("A - Ought To Pass As Amended", "B - Ought To Pass As
Amended", "C - Ought Not To Pass"), each with its signers: "Senator Joseph Baldacci of Penobscot, Chair",
"Representative Mike Lance of Paris". A unanimous report names no one (and the committees' rosters aren't in the data),
so only divided reports are read. The page shows the latest report's division only ("Latest Committee Report: Feb 27,
2026; IFW, MAJ: ...": LD 1343 of 2025-26 was divided in May 2025 and again in February 2026; LD 1745 of 2023-24's first,
divided report, a referral, is gone once the second committee reported unanimously).

Which bills: LegiScan's history (legiscan.py) has the committee's "Reported Out: OTP-AM/ONTP" line (a slash: a divided
report), so only bills whose latest "Reported Out" line is divided are read, each once for that report's day; a page that
shows no division yet (the site a day behind) is read again once a day for a month.

robots.txt (read 2026-11-22) bars only /bills/default_ps.asp, /legis/bills/default_ps.asp, /bills/search_ps.asp,
/legis/bills/search_ps.asp, /LawMakerWeb and /legis/LawMakerWeb, with no crawl delay. Pages are read one at a time, at
least 1.5 seconds apart (as laws.py), newest session and newest reports first, at most --minutes a run (default 6, after
laws.py in the LegiScan job); a refusal (403, 429, 503), three errors or ten slow answers end the run, and what was read is
kept. Nothing here marks the state incomplete.

Usage: python3 states/me/reports.py [--minutes 6]
"""
import argparse, html, json, os, re, sys, time, urllib.error
from datetime import date, timedelta

HERE = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from states import legiscan_convert as L
from states import window as W
from states.me import profile as P
from states.me import laws

PATH = os.path.join(P.DATA, "reports.json")
DIVIDED = re.compile(r"^Reported Out:\s*\S+/", re.I)


def latest_report(b):
    """The day of the bill's latest "Reported Out" line, and whether that report was divided."""
    rs = [((a.get("date") or "")[:10], L.text(a.get("action"))) for a in b.get("history") or []
          if re.match(r"Reported Out:", L.text(a.get("action")), re.I)]
    if not rs:
        return "", False
    d = max(x[0] for x in rs)
    return d, any(x[0] == d and DIVIDED.match(x[1]) for x in rs)


def parse(page):
    """A bill page -> {"day": "2026-02-27" (its latest committee report), "reports": [["MAJ", "Ought To Pass As Amended",
    [["S", "Joseph Baldacci", "Penobscot", true], ...]], ...]} (signers as [house, name, place, chair])."""
    out = {"reports": []}
    m = re.search(r"Latest Committee Report:\s*</span>\s*<span[^>]*>\s*([^<;]+)", page)
    if m:
        out["day"] = laws.day(m.group(1).strip())
    m = re.search(r'id="sec9".*?</table>', page, re.S)
    if not m:
        return out
    cur = None
    for row in re.findall(r"<tr[^>]*>(.*?)(?=<tr|</table>)", m.group(0), re.S):
        cells = [re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", c))).strip()
                 for c in re.findall(r"<td[^>]*>(.*?)(?=<td|</tr>|$)", row, re.S)]
        if len(cells) < 2:
            continue
        head = re.match(r"([A-Z]{1,3}) - (.+)$", cells[0])
        if head:
            cur = [head.group(1), head.group(2).strip(), []]
            out["reports"].append(cur)
        s = re.match(r"(Senator|Representative) (.+?) of (.+?)(, Chair)?$", cells[1])
        if cur is not None and s:
            cur[2].append(["S" if s.group(1) == "Senator" else "H", s.group(2).strip(), s.group(3).strip(), bool(s.group(4))])
        elif cur is not None and cells[1]:
            cur[2].append(["", cells[1], "", False])  # kept as written; the data check counts these
    return out


def read():
    return L.read_json(PATH, {}) or {}


def save(cache):
    tmp = PATH + ".tmp"
    with open(tmp, "w") as f:
        json.dump(cache, f, indent=0, sort_keys=True, ensure_ascii=False)
    os.replace(tmp, PATH)


def wanted(x, day, today):
    """Whether a bill whose latest report (on `day`) was divided needs its page (again)."""
    if not x or (x.get("want") or "") < day:
        return True
    if x.get("reports") or x.get("checked") == today:
        return False
    return day >= (date.fromisoformat(today) - timedelta(days=30)).isoformat()


def todo(cache, today):
    from states.me import convert as C
    out = []
    for session in sorted(C.sessions(), reverse=True):
        if session + 1 < W.first_year():
            continue
        mine = []
        for b in L.bills(C.RULES.session_folders()[session]):
            if not C.RULES.include(b):
                continue
            day, divided = latest_report(b)
            ld = L.number(b["bill_number"])[2:]
            if divided and wanted(cache.get(str(session), {}).get(ld), day, today):
                mine.append((day, session, ld))
        out += sorted(mine, reverse=True)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--minutes", type=float, default=6)
    a = ap.parse_args()
    stop = time.time() + a.minutes * 60
    today = date.today().isoformat()
    cache = read()
    jobs = todo(cache, today)
    print(f"me reports: {len(jobs)} pages to read", file=sys.stderr)
    n = got = 0
    last, wait, slow, errors = 0.0, laws.GAP, 0, 0
    for day, session, ld in jobs:
        if time.time() > stop:
            break
        time.sleep(max(0.0, last + wait - time.time()))
        last = time.time()
        try:
            page = laws.get(laws.PAGE.format(ld=ld, snum=laws.snum(session)))
        except urllib.error.HTTPError as e:
            print(f"me reports: LD {ld} of {session}: HTTP {e.code}", file=sys.stderr)
            errors += 1
            if e.code in (403, 429, 503) or errors >= 3:
                break
            continue
        except Exception as e:
            print(f"me reports: LD {ld} of {session}: {e}", file=sys.stderr)
            errors += 1
            if errors >= 3:
                break
            continue
        took = time.time() - last
        wait = max(laws.GAP, took)
        slow = slow + 1 if took > 10 else 0
        n += 1
        x = parse(page)
        # The page's division belongs to its latest report: kept only when that's the day LegiScan's divided report
        # names (else the page is behind, or ahead of LegiScan with a newer report).
        if x.get("day") != day:
            x["reports"] = []
        x.update(want=day, checked=today)
        cache.setdefault(str(session), {})[ld] = x
        got += bool(x["reports"])
        if n % 25 == 0:
            save(cache)
        if slow >= 10:
            print("me reports: the site is answering slowly; stopping for this run", file=sys.stderr)
            break
    save(cache)
    print(f"me reports: read {n} pages ({got} with a divided report's signers); {len(jobs) - n} left for later runs",
          file=sys.stderr)


if __name__ == "__main__":
    main()
