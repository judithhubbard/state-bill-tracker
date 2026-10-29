#!/usr/bin/env python3
"""Download California's legislative database tables into data/ca/<session>/ (session = its first, odd year).

The Legislature publishes the whole database as zips (states/ca/pubinfo.py reads only the tables out of them):
pubinfo_<year>.zip for each two-year session, refreshed weekly while it's current, and pubinfo_daily_<Day>.zip,
the current session as of each day. Finished sessions are read once; the current one from the newest daily zip
whenever it changes. The governor's veto messages are kept as vetoes.json beside the tables, and the bill texts
(states/ca/texts.py) as digests.json. Then the legislators (states/ca/contacts.py, once a day).

Usage: python3 states/ca/fetch.py [first_session]   (default 2021)
"""
import json, os, sys
from datetime import datetime
from email.utils import parsedate_to_datetime
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
from states.ca import profile as P
from states.ca import texts
from states.ca.pubinfo import BASE, Zip, head

FIRST = int(sys.argv[1]) if len(sys.argv) > 1 else 2021
CURRENT = P.session_of(datetime.now(ZoneInfo(P.TIMEZONE)).year)
TABLES = ["BILL", "BILL_HISTORY", "BILL_VERSION", "BILL_VERSION_AUTHORS", "BILL_SUMMARY_VOTE", "BILL_DETAIL_VOTE",
          "BILL_MOTION", "BILL_ANALYSIS", "COMMITTEE_HEARING", "COMMITTEE_AGENDA", "DAILY_FILE", "LEGISLATOR",
          "LOCATION_CODE", "VETO_MESSAGE"]


def save(url, stamp):
    """Read the tables and veto messages out of one zip into the folder of the session it holds."""
    z = Zip(url)
    got = z.read([f"{t}_TBL.dat" for t in TABLES])
    first = got["BILL_TBL.dat"].split(b"\n", 1)[0].split(b"\t")
    session = int(first[1].strip(b"`")[:4])
    folder = os.path.join(P.DATA, str(session))
    os.makedirs(folder, exist_ok=True)
    for name, body in got.items():
        with open(os.path.join(folder, name + ".tmp"), "wb") as f:
            f.write(body)
        os.replace(os.path.join(folder, name + ".tmp"), os.path.join(folder, name))
    lobs = [n for n in z.files if n.startswith("VETO_MESSAGE_TBL_") and n.endswith(".lob")]
    vetoes = {n: b.decode("utf-8", "replace") for n, b in z.read(lobs).items()}
    json.dump(vetoes, open(os.path.join(folder, "vetoes.json"), "w"), ensure_ascii=False)
    json.dump({"source": url, "modified": stamp}, open(os.path.join(folder, "source.json"), "w"))
    print(f"{session}: {len(got)} tables, {len(vetoes)} veto messages, from {url.rsplit('/', 1)[1]} ({stamp})")
    texts.update(session, z)
    return session


def had(session):
    try:
        return json.load(open(os.path.join(P.DATA, str(session), "source.json")))
    except (OSError, ValueError):
        return None


def main():
    os.makedirs(P.DATA, exist_ok=True)
    # The newest daily zip holds the current session (and, from December of an even year, perhaps the next).
    days = [(head(f"{BASE}/pubinfo_daily_{d}.zip"), d) for d in ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")]
    days = [(parsedate_to_datetime(h[1]), d) for h, d in days if h]
    daily_session = None
    if days:
        when, day = max(days)
        url, stamp = f"{BASE}/pubinfo_daily_{day}.zip", when.isoformat()
        known = [had(s) for s in (CURRENT, CURRENT + 2)]
        hit = next((k for k in known if k and k["source"] == url and k["modified"] == stamp), None)
        if hit:
            print(f"{url.rsplit('/', 1)[1]}: unchanged since {stamp}")
        else:
            daily_session = save(url, stamp)
    # Each session's own zip: finished sessions once, and the current one if the daily zip has moved on.
    for session in range(FIRST, CURRENT + 3, 2):
        if session == daily_session:
            continue
        # A copy from the daily zip stays current until the daily zip moves on to the next session (in December
        # of an even year); then this session's own zip has its final days.
        k = had(session)
        if k and "daily" in k["source"] and not daily_session:
            continue
        h = head(f"{BASE}/pubinfo_{session}.zip")
        if not h:
            continue
        stamp = parsedate_to_datetime(h[1]).isoformat()
        if k and (session < CURRENT or k["modified"] == stamp):
            continue
        save(f"{BASE}/pubinfo_{session}.zip", stamp)
    # Bill texts not read yet (a session saved before texts were read, or files that didn't match last time), from
    # the zip the tables came from, if it hasn't changed since.
    for session in range(FIRST, CURRENT + 3, 2):
        k = had(session)
        cached = texts.load(session)
        if not k or not any(v not in cached or "xhtml:" in cached[v]["digest"] for v in texts.latest(session)):
            continue
        h = head(k["source"])
        if h and parsedate_to_datetime(h[1]).isoformat() == k["modified"]:
            texts.update(session, Zip(k["source"]))


def legislators():
    """The current legislators and committees, once a day (about 200 pages)."""
    from states.ca import contacts
    path = os.path.join(P.DATA, f"contacts_{CURRENT}.json")
    today = datetime.now(ZoneInfo(P.TIMEZONE)).strftime("%Y-%m-%d")
    try:
        fresh = json.load(open(path)).get("fetched", "").startswith(today)
    except (OSError, ValueError):
        fresh = False
    if fresh:
        print(f"contacts_{CURRENT}.json: already refreshed today")
        return
    try:
        contacts.main(CURRENT)
    except Exception as e:  # a site down for the day: keep yesterday's file
        print(f"contacts not refreshed: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()
    legislators()
