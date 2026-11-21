"""Dates for bills with no history yet (shared by every state's converter).

A bill can be listed before it has a history: the next session's prefiled bills whose pages a run hasn't reached (NV's AB 69-80
of 2027), a numbered draft not yet introduced (MT's SB 32 of 2027), a record the server failed on. The converters date such a
bill by its session's first day (or its introduction date), which for the next session is months away, so its "first" and
"last" were in the future (the data check's FAIL, 2026-11-21). `settle()`, called at the end of each converter's
load_session(), gives such a bill the day the file it came from was last written (UTC): its own file (bills/HB1.json,
bills/AB69.html ...) when the state has one per bill, else the session's bill list. Today would move the bill's date every
day (to the top of "latest action" sorts, and changing the status files and shards daily); a file's time changes only when a
download writes it. Today is the last resort, when no file is found. Bills with a dated history line, and every bill whose
dates aren't in the future, are left as they are.
"""
import glob, os
from datetime import date, datetime, timezone

# Each state's bill list, the file a bill with no file of its own comes from (the first found in the session's folder).
LISTS = ("list.json", "bills.json", "legislation.json", "documents.json", "bill_status.json", "billlist.json", "allmsrs.xml",
         "BILLS.CSV", "bill_info.csv", "BILL_TBL.dat", "Measures.json", "openstates.json", "LegislativeMeasures.txt")


def file_day(path):
    """The UTC day a file was last written, or "" if it isn't there."""
    try:
        return datetime.fromtimestamp(os.path.getmtime(path), timezone.utc).strftime("%Y-%m-%d")
    except OSError:
        return ""


def _own_files(folders):
    """{"HB1": path}: the per-bill files in the folders' subfolders (bills/HB1.json, bills/AB69.html)."""
    out = {}
    for f in folders:
        # bills/ first (votes/HB1.json is the same bill's, but written when its votes are read)
        for p in sorted(glob.glob(os.path.join(f, "*", "*")), key=lambda p: os.path.basename(os.path.dirname(p)) != "bills"):
            stem = os.path.splitext(os.path.basename(p))[0]
            if stem.endswith(".json"):  # "HB1.json.gz"
                stem = stem[:-5]
            out.setdefault(stem, p)
    return out


def settle(recs, folders, lists=()):
    """Re-date the records with no dated history line whose "first" or "last" is after today. folders: the session's data
    folder (or several); lists: the bill list's path where it isn't one of LISTS in those folders."""
    today = date.today().isoformat()
    todo = [r for r in recs if (str(r.get("first") or "") > today or str(r.get("last") or "") > today)
            and not any(d for v in r.get("vers") or [] for d, _ in v.get("actions") or [])]
    if not todo:
        return recs
    folders = [folders] if isinstance(folders, str) else list(folders)
    own = _own_files(folders)
    listed = next((d for d in (file_day(p) for p in list(lists) + [os.path.join(f, n) for f in folders for n in LISTS]) if d), "")
    for r in todo:
        day = next((file_day(own[n]) for n in r.get("nums") or [] if n in own), "") or listed or today
        day = min(day, today)
        first = r.get("first") if str(r.get("first") or "") <= today else ""
        if str(r.get("first") or "") > today:
            r["first"] = first = day if not first else first
        if str(r.get("last") or "") > today:
            r["last"] = max(day, first or day)
    return recs
