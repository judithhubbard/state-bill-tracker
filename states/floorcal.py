"""Floor calendars: the bills set for (or able to come up for) a vote of the full house on a coming day, shared by the
converters' agendas() (notes/agendas-survey.md, "Floor calendars").

A floor calendar's day is an agenda entry of kind "floor", with the house as its "committee":
    ["Senate floor", "2027-03-02T10:00:00", "floor"]              a vote set for that day (New Jersey's board lists)
    ["Assembly floor", "2027-03-02T00:00:00", "floor", "listed"]  on the day's calendar, so it can come up for a vote, but
                                                                  bills often wait there for days (California's third
                                                                  reading file)
    ["House floor", "2027-02-10T00:00:00", "floor", "likely"]     no calendar: the bill's own history says its vote is
                                                                  likely that day (likely(): Virginia's bills read a
                                                                  second time, passed the next weekday 92% of the time)
The page shows it as a tag ("Senate floor vote Mon, Mar 2" / "On the Assembly calendar Mon, Mar 2" / "Likely floor
vote Mon, Mar 2"), a line in the
bill's panel, a watchlist deadline ("Floor vote Mar 2") and "On an upcoming floor calendar" under "Awaiting a floor
vote"; the card then asks the visitor's own legislators to vote.

Some calendars list a bill every day it waits (California's files: 66,801 rows in 2025-26), so readers keep only days
from today on (since()); FLOOR_TODAY=YYYY-MM-DD sets "today" back, to test a reader on a past session's calendars.
"""
import os
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo


def since(tz="America/New_York"):
    """The first day whose calendars are kept (ISO date): today in the state's time zone, or FLOOR_TODAY."""
    return os.environ.get("FLOOR_TODAY") or datetime.now(ZoneInfo(tz)).date().isoformat()


def replay():
    """FLOOR_TODAY, if set: a reader of likely votes leaves out history lines from that day on, as if run that morning."""
    return os.environ.get("FLOOR_TODAY") or ""


def entry(house, when, listed=False, likely=False):
    """An agenda entry for a floor calendar's day: house is the house's name as the page has it ("Senate"). likely: no
    calendar names the day; the bill's history makes a vote likely then (see likely())."""
    return [f"{house} floor", when, "floor"] + (["listed"] if listed else ["likely"] if likely else [])


def next_weekday(day):
    """The weekday after an ISO day ("2026-02-06", a Friday -> "2026-02-09")."""
    d = date.fromisoformat(day[:10]) + timedelta(days=1)
    while d.weekday() >= 5:
        d += timedelta(days=1)
    return d.isoformat()


def likely(out, bill, house, day, since):
    """A likely floor vote, for a state with no floor calendar: the bill's latest step in its house was the reading
    before the passage vote (or that vote put off) on `day`, and in that state the vote usually comes the next day the
    house meets (measured on each state's past sessions: notes/agendas-survey.md, "Likely floor votes"). The entry is
    the next weekday, kept only from `since` on; the converter stops adding it once the history moves on."""
    when = next_weekday(day)
    if when >= since:
        add(out, bill, entry(house, f"{when}T00:00:00", likely=True))


def likely_from_records(out, recs, second, between, put_off, houses, since, cut=""):
    """likely() for each record whose history (the records' own wording, [[day, text], ...]) last read it the second
    time (`second`), followed only by steps matching `between` or `put_off` (a vote put off: the next weekday counts
    from that line). houses(record) gives (its first house's name, the other's); the vote is in the other once the bill
    passed a house (keyDates) before that reading. cut: leave out lines from that day on (FLOOR_TODAY)."""
    for r in recs:
        acts = sorted(((a[0][:10], a[1]) for v in r["vers"] for a in v["actions"] if a[0] and not (cut and a[0][:10] >= cut)),
                      key=lambda a: a[0])
        i = max((k for k, a in enumerate(acts) if second.search(a[1])), default=None)
        if i is None or not all(between.search(t) or put_off.search(t) for _, t in acts[i + 1:]):
            continue
        day, kd, hs = acts[i][0], r.get("keyDates") or [], houses(r)
        passed = sum(1 for k in (1, 2) if len(kd) > k and any(d and d < day for d in (kd[k] or "").split(";")))
        if hs and passed < 2:
            likely(out, r["nums"][0], hs[passed], max([day] + [d for d, t in acts[i + 1:] if put_off.search(t)]), since)


def add(out, bill, e):
    """Add an entry to a reader's {bill: [entries]} once."""
    if e not in out.setdefault(bill, []):
        out[bill].append(e)
