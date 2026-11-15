# To do (started 2026-11-14)

One list of open work. Dated chores for January 2027 are in the january-2027-checks memory; the launch steps are
in CLAUDE.md's launch checklist.

## "What it does" (summaries)
- **New York:** done 2026-11-14 for Senate bills and Assembly bills with a Senate twin (the purpose and summary of
  provisions from the Senate sponsor's memo, data/texts_<session>.json, written by fetch_bills.py). Assembly bills:
  states/ny/memos.py (download.yml, started 2026-11-14; about 11,000 pages, three runs for the first copy).
- **Added 2026-11-14, filling in over the next runs:** New Hampshire, North Dakota (bills passed only), Nebraska, Idaho,
  North Carolina (bills a committee heard), Michigan (bills an agency analyzed).
- **Arizona:** House bill summaries and Senate fact sheets on azleg.gov/legtext (allowed, 120-second delay; file names from
  Open States' "documents"): about a week of runs. Waiting for the owner's go-ahead.
- **Michigan joint resolutions** (HJRA, SJRB ...) get no summary: the page and build_data.py key texts by `baseNum()`,
  which strips a final capital letter. Fix the key for letter-numbered resolutions.
- South Dakota has no summaries; Rhode Island shows the General Assembly's one-line description (the Legislative Council's
  explanation would cost LegiScan queries: left out).
- **Missouri** House bills' summaries, **Kansas** 2023-24 supplemental notes, **Louisiana** digests: their downloads
  read these as extras, a little each run (checked 2026-11-14); they fill in over days. Check coverage in a week.
- No summary exists in the sources: Alaska (decided 2026-11-08: the sponsor statement is an advocate's case),
  Arkansas, Massachusetts, Mississippi, Montana, Oklahoma, Maine, Vermont (LegiScan has bill texts, not summaries).

## States not yet on the site
- Louisiana: built; waiting for its first download on GitHub and contacts.
- Iowa (2026-11-14): legis.iowa.gov's firewall stops each GitHub run after about 45 requests. The first copy now comes
  from Open States (states/ia/openstates.py, 100 requests a day, about 3 days), and fetch.py reads every changed bill
  from the official site first, then the rest over the following weeks. Converter to write once the first copy is in:
  official history when there, else the Open States record.
- Open States' bulk files (2026-11-15; states/openstates_bulk.py, each state's bulk.json): Iowa 2023-24 and Florida
  2024-26 and Hawaii 2023-26 imported as first copies.
- Florida, Hawaii: downloads running (Florida about 2/3 through 2026's bills; Hawaii capped at 110 Open States requests a
  day); converters not started (Florida's emails from Open States unless the owner objects).

## National issues and search
- notes/issues-draft.md: the owner answered its four questions 2026-11-15 (all as drafted). The rules are issues.py,
  checked over every state's bills (notes/issues-check.md: 26-30 of 30 random matches right). The owner's two answers
  are in (2026-11-15). Built 2026-11-15: each state's build writes data/issues.json (build_data.py's write_issues()),
  issues_site.py builds /issues/ and /issues/<id>/, and the front page lists the issues. Later: issue tags on the state
  pages, the next issues (notes/issues-draft.md), the free-text search.
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
