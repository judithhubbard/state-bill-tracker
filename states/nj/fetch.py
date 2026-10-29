#!/usr/bin/env python3
"""Download New Jersey's legislative data files into data/nj/: each session's bill database
(DB<year>_TEXT.zip: bills, actions, sponsors, subjects, committees, agendas, roster) and its floor
and committee votes, all from pub.njleg.gov.

Usage: python3 states/nj/fetch.py [first_session]   (default 2018, through the current session)

Sessions start in even years and run two years (2026 = the 2026-27 session). Finished sessions'
files don't change, so they are downloaded only once; the current session's every time.
"""
import json, os, sys, time, urllib.error, urllib.request, zipfile
from datetime import datetime
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
from states.nj import profile as P

FIRST = int(sys.argv[1]) if len(sys.argv) > 1 else 2018
CURRENT = P.session_of(datetime.now(ZoneInfo(P.TIMEZONE)).year)
BASE = "https://pub.njleg.gov"


def files(session):
    """(address, file name) for one session: the database, then floor votes for each year
    (the second year's file also has the January days before the next session) and committee votes."""
    yield f"{BASE}/leg-databases/{session}data/DB{session}_TEXT.zip", f"DB{session}_TEXT.zip"
    for house in "AS":
        for year in (session, session + 1):
            yield f"{BASE}/votes/{house}{year}.zip", f"{house}{year}.zip"
        yield f"{BASE}/votes/C{house}{session}-{session + 1}.zip", f"C{house}{session}-{session + 1}.zip"


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
    tmp = path + ".tmp"
    with open(tmp, "wb") as f:
        f.write(body)
    if zipfile.ZipFile(tmp).testzip() is not None:
        raise SystemExit(f"damaged zip: {url}")
    os.replace(tmp, path)
    return True


def main():
    os.makedirs(P.DATA, exist_ok=True)
    for session in range(FIRST, CURRENT + 1, 2):
        for url, name in files(session):
            path = os.path.join(P.DATA, name)
            if session < CURRENT and os.path.exists(path):
                continue
            # A second year that hasn't started has no floor votes yet.
            if get(url, path):
                print(f"{name}: {os.path.getsize(path) / 1e6:.1f} MB")
            else:
                print(f"{name}: not published yet")
    # The current session's legislators, committees and leaders, once a day (it's one request per legislator).
    from states.nj import contacts
    path = os.path.join(P.DATA, f"contacts_{CURRENT}.json")
    today = datetime.now(ZoneInfo(P.TIMEZONE)).strftime("%Y-%m-%d")
    try:
        fresh = json.load(open(path)).get("fetched", "").startswith(today)
    except (OSError, ValueError):
        fresh = False
    if fresh:
        print(f"contacts_{CURRENT}.json: already refreshed today")
    else:
        contacts.main(CURRENT)


if __name__ == "__main__":
    main()
