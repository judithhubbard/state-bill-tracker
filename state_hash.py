#!/usr/bin/env python3
"""Prints a fingerprint of everything one state's pages are built from, so build_site.sh rebuilds only the states whose
fingerprint changed and copies the rest from the last build (kept by publish.yml between runs).

It covers the state's data (data/<state>/, and New York's files at the top of data/), the shared page and build code
(tracker.html, build_data.py and the modules it imports), the state's own folder and New York's (whose settings other
states fall back to), the site's address (SITE_BASE) and today's date: some wording depends on the date (deadlines,
"in session"), so every state is rebuilt at least once a day.
Usage: python3 state_hash.py STATE
"""
import datetime, glob, hashlib, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
state = sys.argv[1]


def files():
    data = os.path.join(HERE, "data")
    if state == "ny":
        yield from sorted(glob.glob(os.path.join(data, "*.json")) + glob.glob(os.path.join(data, "*.json.gz")))
    else:
        for d, dirs, names in os.walk(os.path.join(data, state)):
            dirs.sort()
            for n in sorted(names):
                yield os.path.join(d, n)
    for f in ("tracker.html", "build_data.py", "stages.py", "fetch_contacts.py", "listing_dates.py"):
        yield os.path.join(HERE, f)
    for s in sorted({state, "ny"}):
        for d, dirs, names in os.walk(os.path.join(HERE, "states", s)):
            dirs[:] = sorted(x for x in dirs if x != "__pycache__")
            for n in sorted(names):
                yield os.path.join(d, n)


h = hashlib.sha256()
h.update(f"{datetime.date.today()} {os.environ.get('SITE_BASE', '')}\0".encode())
for path in files():
    h.update(os.path.relpath(path, HERE).encode() + b"\0")
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    h.update(b"\0")
print(h.hexdigest())
