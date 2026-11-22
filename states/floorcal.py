"""Floor calendars: the bills set for (or able to come up for) a vote of the full house on a coming day, shared by the
converters' agendas() (notes/agendas-survey.md, "Floor calendars").

A floor calendar's day is an agenda entry of kind "floor", with the house as its "committee":
    ["Senate floor", "2027-03-02T10:00:00", "floor"]              a vote set for that day (New Jersey's board lists)
    ["Assembly floor", "2027-03-02T00:00:00", "floor", "listed"]  on the day's calendar, so it can come up for a vote, but
                                                                  bills often wait there for days (California's third
                                                                  reading file)
The page shows it as a tag ("Senate floor vote Mon, Mar 2" / "On the Assembly calendar Mon, Mar 2"), a line in the
bill's panel, a watchlist deadline ("Floor vote Mar 2") and "On an upcoming floor calendar" under "Awaiting a floor
vote"; the card then asks the visitor's own legislators to vote.

Some calendars list a bill every day it waits (California's files: 66,801 rows in 2025-26), so readers keep only days
from today on (since()); FLOOR_TODAY=YYYY-MM-DD sets "today" back, to test a reader on a past session's calendars.
"""
import os
from datetime import datetime
from zoneinfo import ZoneInfo


def since(tz="America/New_York"):
    """The first day whose calendars are kept (ISO date): today in the state's time zone, or FLOOR_TODAY."""
    return os.environ.get("FLOOR_TODAY") or datetime.now(ZoneInfo(tz)).date().isoformat()


def entry(house, when, listed=False):
    """An agenda entry for a floor calendar's day: house is the house's name as the page has it ("Senate")."""
    return [f"{house} floor", when, "floor"] + (["listed"] if listed else [])


def add(out, bill, e):
    """Add an entry to a reader's {bill: [entries]} once."""
    if e not in out.setdefault(bill, []):
        out[bill].append(e)
