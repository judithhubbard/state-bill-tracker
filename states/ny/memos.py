#!/usr/bin/env python3
"""Download the Assembly sponsors' memos from nyassembly.gov (the Senate's Open Legislation API has Senate memos only)
into data/ny/assembly_memos_<session>.json: {"A1001D": "<memo text>"}, keyed by bill number and version.

robots.txt (checked 2026-11-14) bars only GPTBot. One page a second, like fetch_assembly_votes.py. Which bills and
versions exist comes from the Senate's API (NYSENATE_API_KEY or ~/.nysenate_api_key); a bill's memo is read once per
version, so after the first copy (about 11,000 Assembly bills a session: several runs, saved as it goes) a run reads only
new bills and amended ones. Run on GitHub (download.yml), not on the owner's computer.

fetch_bills.py (run when the site is published) turns each memo's purpose and summary of provisions into "What it
does". The memos never hold New York off the site: there is no "incomplete" marker.

Usage: python3 states/ny/memos.py [session_year]   (default: the current session)
"""
import html, json, os, re, sys, time, urllib.parse, urllib.request
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.normpath(os.path.join(HERE, "..", "..", "data", "ny"))
YEAR = date.today().year
SESSION = int(sys.argv[1]) if len(sys.argv) > 1 else (YEAR if YEAR % 2 else YEAR - 1)
OUT = os.path.join(DATA, f"assembly_memos_{SESSION}.json")
UA = "Mozilla/5.0 (compatible; StateBillTracker/1.0; +https://statebilltracker.pages.dev/)"
START = time.time()
BUDGET = max(0.0, float(os.environ.get("FETCH_MINUTES") or 0) - 5) * 60  # stop a few minutes before the job's limit
SAVE_EVERY = 100


def key():
    return os.environ.get("NYSENATE_API_KEY") or open(os.path.expanduser("~/.nysenate_api_key")).read().strip()


def assembly_bills():
    """{"A1001": "D"}: each Assembly bill (not resolutions) and its active version, from the Senate's API."""
    out, offset, total = {}, 1, None
    while total is None or offset <= total:
        q = urllib.parse.urlencode({"key": key(), "limit": 1000, "offset": offset})
        for attempt in range(5):
            try:
                with urllib.request.urlopen(f"https://legislation.nysenate.gov/api/3/bills/{SESSION}?{q}", timeout=180) as r:
                    d = json.load(r)
                break
            except Exception as e:
                print(f"  retry {attempt + 1} at offset {offset}: {e}", flush=True)
                time.sleep(5 * (attempt + 1))
        else:
            raise SystemExit(f"bill list failed at offset {offset}")
        total = d["total"]
        for b in d["result"]["items"]:
            bt = b.get("billType") or {}
            if bt.get("chamber") == "ASSEMBLY" and not bt.get("resolution"):
                out[b["basePrintNo"]] = b.get("activeVersion") or ""
        offset += 1000
    return out


def memo(print_no):
    """The memo's text on the bill's Assembly page ("" when it has none), or None when the request failed."""
    bn = print_no[0] + print_no[1:].zfill(5)
    url = f"https://nyassembly.gov/leg/?default_fld=&leg_video=&bn={bn}&term={SESSION}&Memo=Y"
    for attempt in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=60) as r:
                page = r.read().decode("utf-8", "replace")
            time.sleep(1)  # be gentle with the Assembly's site
            break
        except Exception as e:
            print(f"  {bn}: {e}", flush=True)
            time.sleep(3 * (attempt + 1))
    else:
        return None
    return parse(page)


def parse(page):
    """The memo's text from a bill's Assembly page, from "BILL NUMBER:" on ("" when there's none)."""
    m = re.search(r"<h3 id='jump_to_Memo'>.*?</h3>(.*?)(?:<h3 |<hr|</body>)", page, re.S)
    if not m:
        return ""
    t = re.sub(r"<br\s*/?>", "\n", m.group(1), flags=re.I)
    t = re.sub(r"<STYLE>.*?</STYLE>", "", t, flags=re.S | re.I)
    t = re.sub(r"<[^>]+>", "", t)
    t = html.unescape(re.sub(r"&nbsp(?!;)", " ", t)).replace("\xa0", " ")
    # The heading lines ("NEW YORK STATE ASSEMBLY", "MEMORANDUM IN SUPPORT ...") come before "BILL NUMBER:".
    i = t.find("BILL NUMBER")
    return t[i:].split("Go to top")[0].strip() if i >= 0 else ""


def main():
    os.makedirs(DATA, exist_ok=True)
    have = json.load(open(OUT)) if os.path.exists(OUT) else {}
    bills = assembly_bills()
    todo = [p + v for p, v in sorted(bills.items(), key=lambda x: int(x[0][1:])) if p + v not in have]
    print(f"{SESSION}: {len(bills)} Assembly bills, {len(have)} memos kept, {len(todo)} to read", flush=True)
    got = failed = 0

    def save():
        with open(OUT + ".tmp", "w") as f:
            json.dump(have, f, ensure_ascii=False)
        os.replace(OUT + ".tmp", OUT)

    for n in todo:
        if BUDGET and time.time() - START > BUDGET:
            print("stopping at the time limit; the rest next run", flush=True)
            break
        text = memo(re.sub(r"[A-Z]$", "", n))
        if text is None:
            failed += 1
            continue
        have[n] = text  # "" for a bill with no memo, so it isn't asked for again until it's amended
        got += 1
        if got % SAVE_EVERY == 0:
            save()
            print(f"  {got} of {len(todo)} read", flush=True)
    save()
    print(f"{SESSION}: {got} read ({sum(1 for n in todo if have.get(n))} with a memo), {failed} failed; "
          f"{sum(1 for v in have.values() if v)} memos in all, {round((time.time() - START) / 60)} min", flush=True)


if __name__ == "__main__":
    main()
