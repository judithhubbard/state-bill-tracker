#!/usr/bin/env python3
"""Checks that statebilltracker.org's data is sound, after each update (.github/workflows/site.yml runs it last,
so a problem fails the run and GitHub emails the owner; the site is already published by then).

- Each state's legislators were refreshed in the last 3 days, and there are about as many as there should be.
- New Jersey: the current session's bill texts ("What it does") are there.
- Virginia: the rule for its session dates (60 days in even years, 46 in odd, from the second Wednesday of
  January; states/va/profile.js) still fits: each finished session's last floor votes come within 10 days of the
  computed adjournment. If a year breaks the rule, add it to `dated` in states/va/profile.js.
A failed download already fails the run before this.
Usage: python3 check_site.py
"""
import csv, json, os, re, sys
from datetime import date, datetime, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
TODAY = date.today()
problems = []


def contacts(state, session, at_least):
    path = os.path.join(HERE, "data", state, f"contacts_{session}.json")
    if not os.path.exists(path):
        problems.append(f"{state}: no legislators file for {session}")
        return
    d = json.load(open(path))
    day = datetime.strptime(d.get("fetched", "1970-01-01")[:10], "%Y-%m-%d").date()
    if (TODAY - day).days > 3:
        problems.append(f"{state}: legislators last refreshed {day} (more than 3 days ago)")
    if len(d.get("people", {})) < at_least:
        problems.append(f"{state}: only {len(d.get('people', {}))} legislators (expected at least {at_least})")


def va_opens(year):
    jan1 = date(year, 1, 1)
    return jan1 + timedelta((2 - jan1.weekday()) % 7 + 7)  # the second Wednesday


# New Jersey: two-year sessions starting in even years.
nj = TODAY.year if TODAY.year % 2 == 0 else TODAY.year - 1
contacts("nj", nj, 115)
if not os.path.exists(os.path.join(HERE, "data", "nj", f"texts_{nj}.json")):
    problems.append(f"nj: no bill texts for {nj}")

# Virginia: a session a year.
contacts("va", TODAY.year, 130)
for year in range(TODAY.year - 2, TODAY.year + 1):
    path = os.path.join(HERE, "data", "va", f"{year}1", "HISTORY.CSV")
    adjourns = va_opens(year) + timedelta((46 if year % 2 else 60) - 1)
    if not os.path.exists(path) or TODAY <= adjourns + timedelta(25):
        continue
    last = ""
    with open(path, encoding="cp1252", errors="replace", newline="") as f:
        for r in csv.DictReader(f, skipinitialspace=True):
            # Passage votes only ("H Read third time and passed House (64-Y ...)", "S Passed Senate"), not the
            # "Bill text as passed House and Senate" lines added when bills are enrolled weeks later.
            if re.match(r"[HS] (?:Read third time and )?passed (House|Senate)\b", r.get("History_description", ""), re.I):
                m = re.match(r"(\d+)/(\d+)/(\d{4})|(\d{4})-(\d\d)-(\d\d)", r.get("History_date", ""))
                if m:
                    d = date(int(m[3]), int(m[1]), int(m[2])) if m[1] else date(int(m[4]), int(m[5]), int(m[6]))
                    # The April reconvened session, five or six weeks later, is separate.
                    if d <= adjourns + timedelta(25):
                        last = max(last, d.isoformat())
    if last and abs((date.fromisoformat(last) - adjourns).days) > 10:
        problems.append(f"va: {year}'s last floor votes were on {last}, but the rule says it adjourned {adjourns}; "
                        "add the year to `dated` in states/va/profile.js")

if problems:
    print("Problems:\n" + "\n".join(f"- {p}" for p in problems))
    sys.exit(1)
print("Data looks sound.")
