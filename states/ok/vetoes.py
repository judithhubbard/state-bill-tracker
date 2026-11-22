#!/usr/bin/env python3
"""Download the Oklahoma governor's yearly veto pages (oklahoma.gov; robots.txt "User-agent: * Allow: /"): each veto of
the year with a paragraph of the governor's reasons, under a "House Bill 3660 Veto Message" heading (its link to the
Secretary of State's copy of the letter now leads to that office's home page). LegiScan carries no veto letters.

Each year's page is in PAGES (the addresses aren't predictable: 2025's page is laid out differently and isn't read; add
each new year's page when it's posted, after the session). A page is read again weekly through the year after its own
(vetoes are final once the governor's time is up), into data/ok/vetoes_<year>.html; a failure keeps the last copy.
convert.py's veto_reasons() reads it. Never holds the run back.
Usage: python3 states/ok/vetoes.py
"""
import os, sys, time, urllib.request
from datetime import date

DATA = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "ok"))
AGENT = "statebilltracker.org (a nonprofit bill tracker; contact via github.com/judithhubbard)"
PAGES = {2026: "https://oklahoma.gov/governor/newsroom/newsroom/2026-veto-page.html"}


def main():
    os.makedirs(DATA, exist_ok=True)
    today = date.today()
    for year, url in sorted(PAGES.items()):
        path = os.path.join(DATA, f"vetoes_{year}.html")
        fresh = os.path.exists(path) and time.time() - os.path.getmtime(path) < 7 * 86400
        if (os.path.exists(path) and today.year > year + 1) or fresh:
            continue
        time.sleep(2)
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": AGENT}), timeout=60) as r:
                page = r.read()
        except Exception as e:  # noqa: BLE001 (kept the last copy)
            print(f"{year} veto page: {e}")
            continue
        if b"Veto Message" in page:
            with open(path + ".tmp", "wb") as f:
                f.write(page)
            os.replace(path + ".tmp", path)
            print(f"{year} veto page: read ({len(page)} bytes)")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # noqa: BLE001
        print(f"veto pages: failed ({type(e).__name__}: {e})")
    sys.exit(0)
