"""The years every state keeps: the four calendar years before this one, and this one, but never before 2023.

    first_year() = max(2023, this year - 4)

2026: 2023-26 (and 2027's prefiled bills where a state lists them). 2027: 2023-27. 2028: 2024-28. A session is kept
when any of its years is in the window: a two-year session from its first year if that's odd (2023-24 is kept until
2029), and New Jersey's even-year sessions from the year before (2022-23 is kept until 2028). The floor is where the
site's data starts for nearly every state; states that already had older sessions (California, Illinois, Texas,
Washington and Ohio from 2021, Connecticut and Oregon from 2022, New Jersey from 2018, New York) keep them.

A fetch.py downloads the window; its converter shows whatever was downloaded. A year added back to the window (2023
for the states that kept only three years) must never mark the state incomplete: only the current session and the one
before it (the years the state had before the window grew) may hold a state off the site. An older session whose first
copy isn't finished is marked on its own (data/<state>/incomplete_<session>, `mark()`), and build_data.py leaves just
that session out (`shown()`) until a later run finishes it.
"""
import os
from datetime import date

FLOOR = 2023


def first_year(today=None):
    """The window's first calendar year."""
    return max(FLOOR, (today or date.today()).year - 4)


def years(today=None, ahead=0):
    """The window's calendar years, oldest first (ahead=1 adds next year, for prefiled bills)."""
    y = (today or date.today()).year
    return list(range(first_year(today), y + 1 + ahead))


def first_session(first_years_odd=True, today=None):
    """The first year of the oldest two-year session in the window: odd-year sessions (2023-24) by default, even-year
    ones (New Jersey's 2022-23) with first_years_odd=False."""
    f = first_year(today)
    return f if (f % 2 == 1) == first_years_odd else f - 1


def recent(year, today=None):
    """A year that may hold a state off the site while its first copy downloads: this year and last year. Older years
    (the ones the window added back) fill in without holding anything back."""
    return year >= (today or date.today()).year - 1


def marker(data_dir, session):
    return os.path.join(data_dir, f"incomplete_{session}")


def mark(data_dir, session, missing):
    """Mark an older session whose first copy isn't finished (missing: a list of what's missing, or empty when done)."""
    path = marker(data_dir, session)
    if missing:
        os.makedirs(data_dir, exist_ok=True)
        with open(path, "w") as f:
            f.write((" ".join(missing) if isinstance(missing, (list, tuple, set)) else str(missing)) + "\n")
    elif os.path.exists(path):
        os.remove(path)


def shown(data_dir, sessions):
    """The sessions to build: those not marked as still downloading."""
    return [s for s in sessions if not os.path.exists(marker(data_dir, s))]


def settle(data_dir, undone, years, session_of=None):
    """Of a run's list of what was never downloaded ("2023:bills", "members"), the entries for years the window added
    back (not `recent()`) mark their session on its own (`mark()`), and the marks of the older years in `years` (the ones
    this run read through) are cleared once nothing of theirs is missing; a year a run didn't reach keeps its mark.
    Returns the rest, which may still hold the state off the site. `session_of` turns a year into the converter's
    session number (default: the year itself)."""
    session_of = session_of or (lambda y: y)
    old, rest = {}, []
    for u in undone:
        head = str(u).split(":", 1)[0]
        if head[:4].isdigit() and not recent(int(head[:4])):
            old.setdefault(session_of(int(head[:4])), []).append(str(u))
        else:
            rest.append(u)
    for s, missing in old.items():
        mark(data_dir, s, missing)
    for y in years:
        if not recent(y) and session_of(y) not in old:
            mark(data_dir, session_of(y), None)
    return rest
