#!/usr/bin/env python3
"""Download Michigan's bill and joint resolution status files from the Legislature's file server
(https://www.legislature.mi.gov/documents/<session>/status/<house|senate>/xml/; see the state-survey-2026-10-31
memory). Its Automated Data Collection Policy allows at most one request per second, so this waits a second between
requests. Joint resolutions ("2025-HJR-A.xml", lettered) are kept for the constitutional
amendments they propose; other resolutions are left out. A finished session's files are read once; the current
session's when the folder listing shows them newer.
Usage: python3 states/mi/fetch.py   (2023-2024 and 2025-2026)
"""
import json, os, re, sys, time, urllib.request
from collections import Counter
from datetime import date

SITE = "https://www.legislature.mi.gov"
DATA = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "mi"))
AGENT = "statebilltracker.org (a nonprofit bill tracker; contact via github.com/judithhubbard)"
YEAR = date.today().year
CURRENT = YEAR if YEAR % 2 else YEAR - 1


# The run's own time limit (FETCH_MINUTES, set by the workflow): stop a few minutes early, with everything read so far
# saved and a summary printed, rather than be cut off silently mid-request.
START = time.time()
BUDGET = max(0.0, float(os.environ.get("FETCH_MINUTES") or 0) - 5) * 60
FAILS = Counter()  # why requests failed, for the summary


def out_of_time():
    return BUDGET and time.time() - START > BUDGET


def get(url):
    for attempt in range(3):
        time.sleep(1)  # the Legislature's limit: one request a second
        try:
            req = urllib.request.Request(url, headers={"User-Agent": AGENT})
            with urllib.request.urlopen(req, timeout=120) as r:
                return r.read()
        except Exception as e:
            FAILS[f"HTTP {e.code}" if hasattr(e, "code") else type(e).__name__] += 1
            time.sleep(10 * (attempt + 1))
    return None


def main():
    """Each session's house and senate folders: files the listing shows as new or changed since the last run (by the
    listing's date and size, kept in data/mi/<session>/<house>/listing.json)."""
    only = int(sys.argv[1]) if len(sys.argv) > 1 else None
    incomplete = []
    marker = os.path.join(DATA, "incomplete")
    # A run cut off by its time limit leaves this, so a partial copy isn't published (cleared after a clean run).
    if not only and not os.path.exists(marker):
        os.makedirs(DATA, exist_ok=True)
        open(marker, "w").write("running\n")
    # The legislators first: a quick step, and the site's check needs them even when a run is cut off.
    sys.path.insert(0, os.path.normpath(os.path.join(DATA, "..", "..")))
    from states.mi import contacts
    from listing_dates import same
    try:
        contacts.main(CURRENT)
    except SystemExit as e:
        print(e)
    for start in (CURRENT, CURRENT - 2):  # the current session first
        if only and start != only:
            continue
        session = f"{start}-{start + 1}"
        for house in ("house", "senate"):
            folder = os.path.join(DATA, session, house)
            os.makedirs(folder, exist_ok=True)
            listing = (get(f"{SITE}/documents/{session}/status/{house}/xml/") or b"").decode("utf-8", "replace")
            entries = {m.group(3): f"{m.group(1)} {m.group(2)}" for m in
                       re.finditer(r"(\d+/\d+/\d{4}\s+\d+:\d+ [AP]M)\s+(\d+) <A HREF=\"[^\"]*/((?:\d{4})-(?:[HS]B-\d+|[HS]JR-[A-Z]+)\.xml)\"", listing)}
            if not entries:
                print(f"{session} {house}: no listing; kept the last copies")
                incomplete.append(f"{session}:{house}")
                continue
            seen_path = os.path.join(folder, "listing.json")
            try:
                seen = json.load(open(seen_path))
            except (OSError, ValueError):
                seen = {}
            todo = [n for n, stamp in sorted(entries.items()) if not os.path.exists(os.path.join(folder, n)) or not same(seen.get(n), stamp)]
            got = 0
            for i, n in enumerate(todo):
                if i and i % 100 == 0:
                    print(f"{session} {house}: {i} of {len(todo)} tried, {got} read, {round((time.time() - START) / 60)} min"
                          + (f"; failures {dict(FAILS)}" if FAILS else ""), flush=True)
                    json.dump(seen, open(seen_path, "w"))
                if out_of_time():
                    break
                body = get(f"{SITE}/documents/{session}/status/{house}/xml/{n}")
                if body and body.lstrip(b"\xef\xbb\xbf \r\n\t").startswith(b"<"):  # some files start with a byte-order mark
                    open(os.path.join(folder, n), "wb").write(body)
                    seen[n] = entries[n]
                    got += 1
            json.dump(seen, open(seen_path, "w"))
            if got < len(todo):
                incomplete.append(f"{session}:{house}")
            print(f"{session} {house}: {got} of {len(todo)} read ({len(entries)} listed)", flush=True)
    print(f"run: {round((time.time() - START) / 60)} min" + ("; stopped at the time limit" if out_of_time() else "")
          + (f"; request failures {dict(FAILS)}" if FAILS else "; no request failures"), flush=True)
    if incomplete:
        open(marker, "w").write(" ".join(incomplete) + "\n")
    elif os.path.exists(marker) and not only:
        os.remove(marker)


if __name__ == "__main__":
    main()
