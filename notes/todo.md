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
- Iowa (2026-11-14): legis.iowa.gov's firewall stops each GitHub run after about 45 requests. The first copy now comes
  from Open States (states/ia/openstates.py, 100 requests a day, about 3 days), and fetch.py reads every changed bill
  from the official site first, then the rest over the following weeks. Converter to write once the first copy is in:
  official history when there, else the Open States record.
- Open States' bulk files (2026-11-15; states/openstates_bulk.py, each state's bulk.json): Iowa 2023-24 and Florida
  2024-26 and Hawaii 2023-26 imported as first copies.
- Florida built 2026-11-15 (official pages, else Open States' records; laws and vetoes match the Senate's lists). To fix:
  states/fl/fetch.py's parse_reps() sometimes puts 'Part of Orange">' in the counties field (contacts.py cleans it).
  Companion bills are separate records (about 1,100 "died awaiting a floor vote" are tabled companions): consider
  grouping them, as Tennessee's are.
- Hawaii built 2026-11-15 (Open States' records; a page per two-year Legislature; laws and vetoes match the governor's
  announcements). To check: committee codes for 2023-24 and the Senate's 2025 list were written from memory; members
  missing from Open States' people file (Ward, Kidani, Holt); the House's floor ayes are counted as 51 less the noes and
  excused, one too many while a seat is vacant; the shared committee note "few are sent to a second" is wrong for
  Hawaii (86-92% go to two or more): needs a STATE hook.
- Iowa built 2026-11-15 (official history pages, else Open States' records; renumbering chains as one record). Goes on
  the site once GitHub has read the committee pages (data/ia/incomplete). To do: read fetch.py's roll-call PDFs (votes/)
  and members' committee lists in the converter; 2025-26 chapter numbers fill in only as pages are read (56 of 370 now);
  the shared "Passed both houses" box counts a first-passage amendment as "to the governor".
- Florida, Hawaii: downloads running (Florida about 2/3 through 2026's bills; Hawaii capped at 110 Open States requests a
  day); converters not started (Florida's emails from Open States unless the owner objects).

## National issues and search
- notes/issues-draft.md: the owner answered its four questions 2026-11-15 (all as drafted). The rules are issues.py,
  checked over every state's bills (notes/issues-check.md: 26-30 of 30 random matches right). The owner's two answers
  are in (2026-11-15). Built 2026-11-15: each state's build writes data/issues.json (build_data.py's write_issues()),
  issues_site.py builds /issues/ and /issues/<id>/, and the front page lists the issues. Later: issue tags on the state
  pages, the next issues (notes/issues-draft.md), the free-text search.
## Owner's list (2026-11-16)
1. **More issues.** Twenty now (notes/issues-check.md). Candidates are the italic items in notes/issues-draft.md. First
   settle the owner's seven open questions on the second ten (campaign finance, redistricting, DEI's scope, supplier
   diversity, the name "Immigration enforcement", drag-show bills, school-aid "property tax relief"). Each new issue
   needs a check (30 random matches plus a hunt for misses) and rebuilds every state. Past about 40 issues, add a
   "Find an issue" box to the Show picker.
2. **More years back.** Most states show 2023-26 (New York from 2017, California from 2021). Choose between full
   history (every bill, every step) and laws only for the early years. Weigh per state: how far each source goes back
   (Open States' bulk files reach about 2009-2011 for most states; some official files go back decades), download time
   and LegiScan queries, and site size (Cloudflare Pages allows 20,000 files and 25 MB a file per deploy). Laws only
   would serve the issue trends ("how many states passed X, year by year") at a fraction of the cost.
   **Done 2026-11-16:** every state keeps 2023 on (states/window.py: this year and the four before, never before 2023),
   downloading on GitHub. Recommended next (owner agreed it's most useful): laws only back to about 2015 for the issue
   pages ("where this is already law"). Still open: Virginia's 2023 exists only as legacylis.virginia.gov pages (a new
   reader); Arizona's 2023 needs the owner's Open States bulk file (states/az/bulk.json), Florida's optionally (saves
   about 5 hours of pages).
3. **Federal bills (/us/).** Sources: GovInfo's bulk BILLSTATUS XML (every bill since the 113th Congress, 2013-14; no
   key) or the Congress.gov API (free key); House roll calls (clerk.house.gov XML) and Senate roll calls (senate.gov
   XML), member by member; Congressional Research Service summaries for "What it does". About 15,000-19,000 bills per
   two-year Congress, about 2-3% enacted. It differs from states: the President (10 days, Sundays excepted; pocket
   vetoes), 535 members, most bills never get a hearing, and members' "district" is a congressional district.
   **Done 2026-11-16** (the 117th-119th Congresses, live at /us/). Open: delegates titled "Rep." (should be "Del."); a
   Congress line on the issue pages (kept out of the states' counts for now); the 120th Congress's districts once the
   Census Bureau publishes them; whether to keep the 117th (before the 2023 floor); the White House phone and contact
   page unchecked; the cache is about 300 MB.
4. **Front page (2026-11-17):** in progress: a Congress tile on the map, and a star on each state's tile where the visitor
   has starred bills. "Your bills" shows each bill's stage and date; the legislatures' own last-action wording was
   dropped (capitals and jargon): the state pages' plainer wording could come back later.

## Site checks
- The daily site check (site-check.yml) runs on a schedule. Three moderate accessibility notes remain on every state
  (no main landmark, content outside landmarks, heading order); they don't fail the check.
- New York's data check fails until GitHub re-reads the 518 Assembly memos with stray bytes (states/ny/memos.py, fixed
  2026-11-16).
- In progress: the statistics flow chart's percentage labels overlap on thin bars (Congress).

## Fixes found, not yet made
- data_check LOOK lines not yet looked into: finished sessions' bills whose history predates the session
  (GA HB 2 and HB 10 of 2023, NH HB 333 of 2024, TN SB 6 of 2023).
- The stage name "Signed into law" (stage 5's label in counts and filters) covers laws without a signature too; the bill
  rows now say which (2026-11-14). Consider "Became law" as the stage name in states with many unsigned laws (OK, TX).
- notes/from-albany-2026-11-12.md: items 1-3 done; the note itself not committed.
- The owner's open questions on the second ten issues (above, item 1).

## Watching
- The download lanes keep chaining every 2 hours, and the quick lane's publishes go out.
- LegiScan's monthly use stays under budget (see the legiscan-budget-plan memory).
