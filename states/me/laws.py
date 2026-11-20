#!/usr/bin/env python3
"""The governor's action and the chapter of Maine's laws, from each law's page on the Legislature's site
(legislature.maine.gov/legis/bills/display_ps.asp?LD=2116&snum=132, the page the site links to), kept in
data/me/laws.json for states/me/convert.py.

LegiScan's records (legiscan.py) never carry the governor's signature or the chapter number: its history stops at the
final enactment. The bill page has both: "Final Disposition ... Governor's Action: Signed, Apr 15, 2026" ("Signed",
"Unsigned" (law without the signature), "Emergency Signed", "Emergency Unsigned" (emergency laws, in effect at once);
"Veto" on vetoed bills) and "Chaptered Law": "ACTPUB, Chapter 699" (a public law; ACTPS a private and special law;
RESLV a resolve; each series numbered from 1 through a Legislature).

robots.txt (checked 2026-11-19) bars only the search pages and LawMakerWeb, with no crawl delay; pages are read one at a
time, at least 1.5 seconds apart, and only for laws (bills enacted by both houses with chaptered text, as convert.py
reads them) whose page hasn't given both facts yet; a page missing one is read again at most once a day. After the first
copy that's a handful a day. A run stops after --minutes (default 8, so the LegiScan job stays in the quick lane), and
on any refusal (403, 429, 503), three failed requests (502s, timeouts) or ten slow answers in a row (over 10 s; after a slow answer it
waits as long again) it stops and keeps what it has: the next run goes on from there. (The first copy, read locally on
2026-11-19, went at two seconds a page for 40 minutes, then the site slowed to half a minute a page and it was stopped.)

Usage: python3 states/me/laws.py [--minutes 8]
"""
import argparse, html, json, os, re, sys, time, urllib.error, urllib.request
from datetime import date

HERE = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from states import legiscan_convert as L
from states import window as W
from states.me import profile as P

AGENT = "statebilltracker.org (a nonprofit bill tracker; contact via github.com/judithhubbard)"
PAGE = "https://legislature.maine.gov/legis/bills/display_ps.asp?LD={ld}&snum={snum}"
PATH = os.path.join(P.DATA, "laws.json")
GAP = 1.5
SERIES = {"ACTPUB": "Public Law", "ACTPS": "Private and Special Law", "RESLV": "Resolve", "IB": "Initiated Bill"}
MONTHS = {m: i + 1 for i, m in enumerate("Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split())}


def snum(session):
    """2025 -> 132 (the 132nd Legislature, 2025-26)."""
    return (session - 1761) // 2


def day(s):
    """"Apr 15, 2026" -> "2026-04-15"."""
    m = re.match(r"([A-Z][a-z]{2})[a-z]*\.? (\d{1,2}), (\d{4})", s or "")
    return f"{m.group(3)}-{MONTHS[m.group(1)]:02d}-{int(m.group(2)):02d}" if m and m.group(1) in MONTHS else ""


def parse(page):
    """A bill page -> {"gov": "Signed", "date": "2026-04-15", "enacted": "2026-04-15", "series": "Public Law",
    "chapter": 699} (what the page says; missing parts left out)."""
    out = {}
    m = re.search(r'class="story_heading">Final Disposition</span>(.*?)</p>', page, re.S)
    if m:
        box = html.unescape(re.sub(r"<[^>]+>", " ", m.group(1)))
        box = re.sub(r"\s+", " ", box).strip()
        # The outcome: "Enacted, Apr 15, 2026", "Finally Passed, ...", "Veto Sustained, ...", "Died Upon Conclusion of
        # the 131st, Dec 4, 2024" (a bill the governor held until the Legislature ended: a pocket veto).
        e = re.match(r"(.+?),? ([A-Z][a-z]+\.? \d{1,2}, \d{4})", box)
        if e:
            out["final"], out["final_date"] = e.group(1).strip(), day(e.group(2))
            if re.match(r"Enacted|Finally Passed", e.group(1)):
                out["enacted"] = day(e.group(2))
        g = re.search(r"Governor's Action:\s*([A-Za-z][A-Za-z ]*?),?\s+([A-Z][a-z]+\.? \d{1,2}, \d{4})", box)
        if g:
            out["gov"], out["date"] = g.group(1).strip(), day(g.group(2))
        elif re.search(r"Governor's Action:\s*(\w[\w ]*)", box):
            out["gov"] = re.search(r"Governor's Action:\s*(\w[\w ]*)", box).group(1).strip()
    m = re.search(r'class="story_heading">Chaptered Law</span>(.*?)(?:Printed Chapter|</span>\s*</span>)', page, re.S)
    if m:
        box = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", m.group(1))))
        c = re.search(r"\b([A-Z&]{2,})\W*Chapter (\d+)", box)
        if c:
            out["series"] = SERIES.get(c.group(1), c.group(1))
            out["chapter"] = int(c.group(2))
    return out


def done(x):
    """The page has said all it will: a law's signing and chapter, or an end that isn't a law (a sustained veto, a bill
    that died held by the governor)."""
    return bool(x and ((x.get("chapter") and x.get("date") and x.get("gov")) or
                       re.match(r"Died|Veto Sustained", x.get("final") or "")))


def read():
    return L.read_json(PATH, {}) or {}


def save(cache):
    tmp = PATH + ".tmp"
    with open(tmp, "w") as f:
        json.dump(cache, f, indent=0, sort_keys=True)
    os.replace(tmp, PATH)


def laws_lacking(cache, today):
    """(session, LD number) for every law in the window's sessions whose page hasn't given both facts, oldest first
    within newest session first (the current session's new laws come first)."""
    from states.me import convert as C
    out = []
    for session in sorted(C.sessions(), reverse=True):
        if session + 1 < W.first_year():
            continue
        folder = C.RULES.session_folders()[session]
        for b in L.bills(folder):
            if C.RULES.include(b) != "bill":
                continue
            steps = [x for line in C.decode_bill(b, "bill", {}) for x in line]
            if not any(k == "chapter" for _, k, _, _ in steps):
                continue
            ld = L.number(b["bill_number"])[2:]
            x = cache.get(str(session), {}).get(ld)
            if done(x) or (x and x.get("checked") == today):
                continue
            out.append((session, ld))
    return out


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": AGENT, "Accept": "text/html"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode("utf-8", "replace")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--minutes", type=float, default=8)
    a = ap.parse_args()
    stop = time.time() + a.minutes * 60
    today = date.today().isoformat()
    cache = read()
    todo = laws_lacking(cache, today)
    print(f"me laws: {len(todo)} pages to read", file=sys.stderr)
    n = got = 0
    last, wait, slow, errors = 0.0, GAP, 0, 0
    for session, ld in todo:
        if time.time() > stop:
            break
        time.sleep(max(0.0, last + wait - time.time()))
        last = time.time()
        try:
            page = get(PAGE.format(ld=ld, snum=snum(session)))
        except urllib.error.HTTPError as e:
            print(f"me laws: LD {ld} of {session}: HTTP {e.code}", file=sys.stderr)
            errors += 1
            if e.code in (403, 429, 503) or errors >= 3:
                break
            continue
        except Exception as e:
            print(f"me laws: LD {ld} of {session}: {e}", file=sys.stderr)
            errors += 1
            if errors >= 3:
                break
            continue
        # A server slow to answer is a busy one: wait as long again as it took (pages usually take under a second), and
        # stop for this run after ten slow answers in a row.
        took = time.time() - last
        wait = max(GAP, took)
        slow = slow + 1 if took > 10 else 0
        n += 1
        x = parse(page)
        x["checked"] = today
        cache.setdefault(str(session), {})[ld] = x
        got += done(x)
        if n % 25 == 0:
            save(cache)
        if slow >= 10:
            print("me laws: the site is answering slowly; stopping for this run", file=sys.stderr)
            break
    save(cache)
    left = len(todo) - n
    print(f"me laws: read {n} pages ({got} with the signing and chapter); {left} left for later runs", file=sys.stderr)


if __name__ == "__main__":
    main()
