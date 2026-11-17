#!/usr/bin/env python3
"""Download Virginia's legislative data files (the Legislative Information System's CSVs) into
data/va/<year>1/, from lis.blob.core.windows.net. Finished sessions are downloaded once; the current one,
and next year's (bills are prefiled from November), every run. Then the legislators (states/va/contacts.py,
once a day) and each locality's districts (states/va/towns.py).

Usage: python3 states/va/fetch.py [first_session]   (default: the shared window's first year, states/window.py)

The LIS files start with the 2024 session (20231/BILLS.CSV and the rest answer 404, checked 2026-11-16). A finished
session they don't have comes, once, from the legacy LIS (legacylis.virginia.gov/SiteInformation/csv/231/, linked from
its ftp.html; robots.txt allows everything): the same tables with mixed-case names, saved here under the names the
converter reads. Their formats differ (dates "02/15/23", padded bill numbers, "Last, First" member names, other summary
labels); states/va/convert.py and texts.py read both.
"""
import os, re, sys, time, urllib.error, urllib.request
from datetime import datetime
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
from states.va import profile as P
from states import window as W

FIRST = int(sys.argv[1]) if len(sys.argv) > 1 else W.first_year()
CURRENT = P.session_of(datetime.now(ZoneInfo(P.TIMEZONE)).year)
BASE = "https://lis.blob.core.windows.net/lisfiles"
# The names are case-sensitive.
FILES = ["BILLS.CSV", "HISTORY.CSV", "VOTE.CSV", "Members.csv", "Committees.csv", "Sponsors.csv",
         "Summaries.csv", "DOCKET.CSV", "SUBDOCKET.CSV", "FiscalImpactStatements.csv"]
LEGACY = "https://legacylis.virginia.gov/SiteInformation/csv"
# The legacy site's name -> the name saved (Docket.csv and Subdocket.csv are empty for a finished session). BILLS.CSV
# last: its presence marks the session as downloaded.
LEGACY_FILES = {"History.csv": "HISTORY.CSV", "Vote.csv": "VOTE.CSV", "Members.csv": "Members.csv",
                "Committees.csv": "Committees.csv", "Sponsors.csv": "Sponsors.csv", "Summaries.csv": "Summaries.csv",
                "Fiscalimpactstatements.csv": "FiscalImpactStatements.csv", "Bills.csv": "BILLS.CSV"}


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
        one(session)


def one(session):
    """One session's files (a finished one only once)."""
    folder = os.path.join(P.DATA, f"{session}1")
    if session < CURRENT and os.path.exists(os.path.join(folder, "BILLS.CSV")):
        return
    got = []
    for name in FILES:
        os.makedirs(folder, exist_ok=True)
        if get(f"{BASE}/{session}1/{name}", os.path.join(folder, name)):
            got.append(name)
    if not got and session < CURRENT:
        # A finished session the LIS files don't have: the legacy LIS, once.
        got = [name for src, name in LEGACY_FILES.items()
               if get(f"{LEGACY}/{str(session)[2:]}1/{src}", os.path.join(folder, name))]
        if got and "BILLS.CSV" not in got:
            print(f"{session}: the legacy LIS has no Bills.csv; tried again next run", file=sys.stderr)
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
    from states.va import texts  # "What it does", from the Legislature's summaries
    for s in sorted(int(f[:4]) for f in os.listdir(P.DATA) if re.fullmatch(r"\d{4}1", f)):
        texts.main(s)
