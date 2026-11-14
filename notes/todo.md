# To do (started 2026-11-14)

One list of open work. Dated chores for January 2027 are in the january-2027-checks memory; the launch steps are
in CLAUDE.md's launch checklist.

## "What it does" (summaries)
- **New York:** done 2026-11-14 for Senate bills and Assembly bills with a Senate twin (the purpose and summary of
  provisions from the Senate sponsor's memo, data/texts_<session>.json, written by fetch_bills.py). Assembly bills:
  states/ny/memos.py (download.yml, started 2026-11-14; about 11,000 pages, three runs for the first copy).
- **New Hampshire, North Dakota, Nebraska:** being added (2026-11-14): bill text analyses, staff summaries, committee
  statements.
- **Missouri:** House bills' summaries (house/summaries/), not downloaded yet.
- **Kansas:** 2023-24 supplemental notes, not downloaded yet.
- **Louisiana:** Senate digests, and House digests beyond the 267 read so far.
- No summary exists in the sources: Alaska (decided 2026-11-08: the sponsor statement is an advocate's case),
  Arkansas, Massachusetts, Mississippi, Montana, Oklahoma, Maine, Vermont (LegiScan has bill texts, not summaries).

## States not yet on the site
- Louisiana: built; waiting for its first download on GitHub and contacts.
- Iowa, Florida, Hawaii: downloads running; converters not started (Florida's emails from Open States unless the
  owner objects).

## National issues and search
- Owner to review notes/issues-draft.md (10 starter issues). Then tag at build time, check each issue's matches,
  build the issue pages; later the free-text search.

## Site checks
- Daily site health and accessibility check (test/site_check.js, site-check.yml): review findings with the owner,
  then commit and schedule.

## Fixes found, not yet made
- data_check LOOK lines not yet looked into: finished sessions' bills whose history predates the session
  (GA HB 2 and HB 10 of 2023, NH HB 333 of 2024, TN SB 6 of 2023).
- The stage name "Signed into law" (stage 5's label in counts and filters) covers laws without a signature too; the bill
  rows now say which (2026-11-14). Consider "Became law" as the stage name in states with many unsigned laws (OK, TX).
- notes/from-albany-2026-11-12.md: items 1-3 done; the note itself not committed.

## Watching
- The download lanes keep chaining every 2 hours, and the quick lane's publishes go out.
- LegiScan's monthly use stays under budget (see the legiscan-budget-plan memory).
