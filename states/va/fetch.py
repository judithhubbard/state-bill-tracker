#!/usr/bin/env python3
"""Download Virginia's legislative data files (the Legislative Information System's CSVs) into
data/va/<year>1/, from lis.blob.core.windows.net. Finished sessions are downloaded once; the current one,
and next year's (bills are prefiled from November), every run. Then the legislators (states/va/contacts.py,
once a day) and each locality's districts (states/va/towns.py).

Usage: python3 states/va/fetch.py [first_session]   (default 2024)
"""
import os, sys, time, urllib.error, urllib.request
from datetime import datetime
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
from states.va import profile as P

FIRST = int(sys.argv[1]) if len(sys.argv) > 1 else 2024
CURRENT = P.session_of(datetime.now(ZoneInfo(P.TIMEZONE)).year)
BASE = "https://lis.blob.core.windows.net/lisfiles"
# The names are case-sensitive.
FILES = ["BILLS.CSV", "HISTORY.CSV", "VOTE.CSV", "Members.csv", "Committees.csv", "Sponsors.csv",
         "Summaries.csv", "DOCKET.CSV", "SUBDOCKET.CSV", "FiscalImpactStatements.csv"]


def get(url, path):
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "statebilltracker.org data fetch"})
            with urllib.request.urlopen(req, timeout=120) as r:
                body = r.read()
            break
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return False
            print(f"  retry {attempt + 1}: {url}: {e}", file=sys.stderr)
        except Exception as e:
            print(f"  retry {attempt + 1}: {url}: {e}", file=sys.stderr)
        time.sleep(5 * (attempt + 1))
    else:
        raise SystemExit(f"failed: {url}")
    with open(path + ".tmp", "wb") as f:
        f.write(body)
    os.replace(path + ".tmp", path)
    return True


def main():
    for session in range(FIRST, CURRENT + 2):
        folder = os.path.join(P.DATA, f"{session}1")
        if session < CURRENT and os.path.exists(os.path.join(folder, "BILLS.CSV")):
            continue
        got = []
        for name in FILES:
            os.makedirs(folder, exist_ok=True)
            if get(f"{BASE}/{session}1/{name}", os.path.join(folder, name)):
                got.append(name)
        print(f"{session}: {len(got)} files" if got else f"{session}: not published yet")
        if not got and not os.listdir(folder):
            os.rmdir(folder)


def legislators():
    """The current legislators and committees (once a day; it's about 60 pages) and each locality's districts."""
    import json
    from states.va import contacts, towns
    path = os.path.join(P.DATA, f"contacts_{CURRENT}.json")
    today = datetime.now(ZoneInfo(P.TIMEZONE)).strftime("%Y-%m-%d")
    try:
        fresh = json.load(open(path)).get("fetched", "").startswith(today)
    except (OSError, ValueError):
        fresh = False
    if fresh:
        print(f"contacts_{CURRENT}.json: already refreshed today")
    else:
        try:
            contacts.main(CURRENT)
        except Exception as e:  # a site down for the day: keep yesterday's file
            print(f"contacts not refreshed: {e}", file=sys.stderr)
    if os.path.exists(path):
        towns.main(CURRENT)


if __name__ == "__main__":
    main()
    legislators()
