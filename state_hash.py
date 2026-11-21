#!/usr/bin/env python3
"""Prints a fingerprint of everything one state's pages are built from, so build_site.sh rebuilds only the states whose
fingerprint changed and copies the rest from the last build (kept by publish.yml between runs).

It covers the state's data (data/<state>/, and New York's files at the top of data/), the shared page and build code
(tracker.html, build_data.py and the modules it imports), the state's own folder and New York's (whose settings other
states fall back to), the site's address (SITE_BASE) and today's date: some wording depends on the date (deadlines,
"in session"), so every state is rebuilt at least once a day.

The files are in two groups: the page's code (page_files(): tracker.html, lists_pages/, the state's profile.js, how.html
and weighin.html, issues.py), which build_data.py only wraps the data in, and everything else (data_files()), which the
data is worked out from. build_data.py keeps what it worked out from the data between builds, keyed by data_files() (its
bundle_key()), so a change to the page's code alone rewrites the pages without working the data out again.
Usage: python3 state_hash.py STATE
"""
import datetime, glob, hashlib, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
# The page's code: what build_data.py reads only to write the pages, the issues file and the status words (bill_labels()).
PAGE_CODE = ["tracker.html", "issues.py"] + [os.path.join("lists_pages", f) for f in (
    "named.js", "watchrules.js", "sankey.js", "watchrows.js", "rows.css", "billfacts.js", "billlabels.js")]
PAGE_IN_STATE = ("profile.js", "how.html", "weighin.html")


def _all(state):
    """(path, page?) for every file the state's build reads."""
    data = os.path.join(HERE, "data")
    if state == "ny":
        for p in sorted(glob.glob(os.path.join(data, "*.json")) + glob.glob(os.path.join(data, "*.json.gz"))):
            yield p, False
    else:
        for d, dirs, names in os.walk(os.path.join(data, state)):
            dirs.sort()
            for n in sorted(names):
                # The "last checked" mark changes every download; the date below covers it (the page's "updated" may
                # lag a quiet day's last check by a few hours, but never by a day).
                if n != "last_checked":
                    yield os.path.join(d, n), False
    # The shared code in states/ (legiscan_convert.py, window.py, openstates_bulk.py ...): several states' converters
    # import it, and the list below once missed it.
    # (And its tables: legislatures.json, party_history.json, elected_2026.json.)
    for p in sorted(glob.glob(os.path.join(HERE, "states", "*.py")) + glob.glob(os.path.join(HERE, "states", "*.json"))):
        yield p, False
    for f in ("governors.py", "party_history.py", "build_data.py", "stages.py", "fetch_contacts.py", "listing_dates.py",
              "balance.py", "site_meta.py", "state_hash.py"):
        yield os.path.join(HERE, f), False
    for f in PAGE_CODE:
        yield os.path.join(HERE, f), True
    # The tab and home-screen icons, which build_data.py copies into each state's folder.
    for p in sorted(glob.glob(os.path.join(HERE, "static", "*"))):
        yield p, True
    # The fonts (site_fonts.py: their @font-face rules go in the pages' styles, the files in assets/fonts/).
    yield os.path.join(HERE, "site_fonts.py"), True
    for p in sorted(glob.glob(os.path.join(HERE, "fonts", "*"))):
        yield p, True
    for s in sorted({state, "ny"}):
        for d, dirs, names in os.walk(os.path.join(HERE, "states", s)):
            dirs[:] = sorted(x for x in dirs if x != "__pycache__")
            for n in sorted(names):
                yield os.path.join(d, n), d == os.path.join(HERE, "states", s) and n in PAGE_IN_STATE


def data_files(state):
    return [p for p, page in _all(state) if not page]


def page_files(state):
    return [p for p, page in _all(state) if page]


def digest(h, paths):
    for path in paths:
        h.update(os.path.relpath(path, HERE).encode() + b"\0")
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
        h.update(b"\0")
    return h


if __name__ == "__main__":
    state = sys.argv[1]
    h = hashlib.sha256()
    h.update(f"{datetime.date.today()} {os.environ.get('SITE_BASE', '')} {os.environ.get('LAUNCHED', '0')}\0".encode())
    print(digest(h, [p for p, _ in _all(state)]).hexdigest())
