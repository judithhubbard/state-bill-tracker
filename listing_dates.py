"""Comparing the dates in a server's folder listing, for downloads that fetch only the files that changed (Texas,
Illinois, Michigan).

These servers list each file's time on their local clock, so when daylight saving time starts or ends every file's time
moves by an hour, sometimes across midnight ("2/26/2025 12:21 AM" -> "2/25/2025 11:21 PM", "03-20-25 02:00AM" ->
"03-20-25 01:00AM"; 2026-11-01), and every file looked changed: a run downloaded everything again. A listing entry with
the same size and a time exactly an hour away is the same file.
"""
from datetime import datetime

FORMATS = ("%m/%d/%Y %I:%M %p", "%m-%d-%y %I:%M%p")


def _when(text):
    for f in FORMATS:
        try:
            return datetime.strptime(text, f)
        except ValueError:
            pass
    return None


def same(old, new):
    """Whether two listing entries ("<date> <time> <size>") describe the same file."""
    if old == new:
        return True
    if not old or not new:
        return False
    (o, so), (n, sn) = old.rsplit(None, 1), new.rsplit(None, 1)
    to, tn = _when(" ".join(o.split())), _when(" ".join(n.split()))
    return so == sn and to is not None and tn is not None and abs((to - tn).total_seconds()) == 3600
