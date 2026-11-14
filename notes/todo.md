# To do (started 2026-11-14)

One list of open work. Dated chores for January 2027 are in the january-2027-checks memory; the launch steps are
in CLAUDE.md's launch checklist.

## "What it does" (summaries)
- **New York:** done 2026-11-14 for Senate bills and Assembly bills with a Senate twin (the purpose and summary of
  provisions from the Senate sponsor's memo, data/texts_<session>.json, written by fetch_bills.py). Still missing:
  Assembly-only bills (about half): the Senate API has no Assembly memos; nyassembly.gov has them, one page per bill
  (GitHub only, never from the owner's computer; check its robots.txt first).
- **New Hampshire:** each bill text's analysis, one request per bill at the 11-second crawl delay (about 12 hours
  for a year's bills once, then only new bills and versions): a slow-lane job.
- **North Dakota:** the Legislative Council's staff summaries and fiscal notes are PDFs (pdftotext is on GitHub).
- **Nebraska:** statements of intent and committee statements are PDFs (crawl delay 3).
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
- Washington: the end-of-year return rule.
- "2024 general (general session)": duplicated wording in Louisiana's session label.
- "Signed into law" shown for laws that became law without a signature (KY, AR).
- data_check LOOK lines not yet looked into: NC's 43 laws with a veto date and no override line; WA SB 5017 and
  SB 5810 of 2021; NJ A4975 of 2020; floor votes on bills that never left committee (MI HB 4195 and "HJRU" of 2025,
  NH HB 565 and HB 620 of 2023, NY S2347 of 2025); finished sessions' bills whose history predates the session
  (GA HB 2 and HB 10 of 2023, NH HB 333 of 2024, TN SB 6 of 2023).
- notes/from-albany-2026-11-12.md: items 1-3 done; the note itself not committed.

## Watching
- The download lanes keep chaining every 2 hours, and the quick lane's publishes go out.
- LegiScan's monthly use stays under budget (see the legiscan-budget-plan memory).
