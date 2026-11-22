# Ohio

Moved from CLAUDE.md (2026-11-19). Shared conventions, the data traps list and the site's code notes stay there.

- **Ohio (started 2026-10-31):** `python3 states/oh/fetch.py` reads the Legislative Service Commission's API
  (https://search-prod.lis.state.oh.us/api/v2/, JSON; see the oh-data-sources memory). legislature.ohio.gov,
  ohiohouse.gov, ohiosenate.gov and ohiosos.gov all answered automated requests with 403 in October 2026, so (decided
  2026-10-31) everything comes from the API except legislators' emails and page links, which come from Open States'
  public-domain file (data/oh/openstates_people.csv; it has no phones), named as the source in "About this data".
  Office phones (and the Columbus office address) since 2026-11-22: a recheck found both houses' robots.txt
  ("User-agent: *", "Disallow:") allowing everything, and one test from a GitHub runner with fetch.py's own `AGENT`
  (a throwaway workflow on a temporary branch, deleted after) got 200 for both robots.txt files and for
  /members/adam-c-bird and /members/rob-mccolley, with their phones. The owner approved reading them: fetch.py's
  `member_pages()` reads each current member's page (`page_of()` in contacts.py: the member's own house's
  /members/<slug> from Open States' links; a senator's list can name an old House page first, as Blackshear's did,
  which was the page link shown until then) into data/oh/member_pages.json, at most 50 a run, 3 seconds apart, each
  again after 7 days, and stops the run's reading on a 403 or 429 (the last copies stand). House pages say
  "Phone: (614) ..." and a "Fax:" line (left out); Senate pages a "Phone" label, and an address some give without the
  city (Columbus, OH 43215 is added). On 2026-11-22: before, 0 of 130 with a phone; a local read of 40 pages gave 39
  phones (brian-e-lampton answered 500), so the first three runs fill them all. Ohio is no longer in data_check.py's
  `CONTACT_GAPS` for phones. Sessions are
  General Assemblies (`assembly_of()`: 2025 -> 136). Each bill's versions (read again when its entry in the
  legislation list changes, its actions change, or it has passed both houses and waits on the governor: the list's
  `revno` doesn't change on enrollment or delivery, so HB 13, HB 397 and SB 214, sent 2026-11-17, were missed until
  2026-11-19) and actions (the current General Assembly's every run; about 1,500 requests, no change
  feed) go into data/oh/<session>/bills/<HB96>.json. Actions are structured, with each vote's members: committee and
  floor votes are member by member. The governor's signature is the enrolled version's governor_signed_date, not an
  action; a few have none (HB 110 of the 134th), so in a finished General Assembly an enrolled bill without "Veto
  receipt" is law; while one runs, a "Line item veto receipt" or the enrolled version's effective date is (SB 152 and
  HB 479 of the 136th had neither a signing date; a future effective date is dated the day it was sent, and a "sent" date
  after the effective date, SB 152's 2026-06-12, is dropped). "Line item veto receipt" stays as written (a law, part vetoed). "Reported - Re-referred to X" is a
  referral to X. Each house's Rules and Reference Committee schedules floor votes. "What it does" is the Legislative Service
  Commission's analysis where one has been read (below), else the long title's purpose clause, after the last list of
  sections, its verb turned into "Modifies ..." (`purpose()`, `texts.py`).
  Full-time Legislature (`floorVotesEnd: false`); governor 10 days, Sundays excepted. Separate Senate (33) and House
  (99) districts by city, village or county (`states/oh/towns.py`). The governor's phone and address are from the
  governor's contact page, checked by the owner 2026-10-31 (governor.ohio.gov answers automated requests "not found"). Built only once data/oh/incomplete is gone.
- **Next General Assembly (2026-11-22):** the API answers 500 for the 137th until it's set up, and bills are introduced
  only after it convenes (January 4, 2027), so it's read from January; until March 1 a list never read doesn't hold Ohio
  back, and its contacts wait until its legislators and committees are listed. The General Assembly just ended is read
  again until April 1 for bills still waiting on enrollment or the governor (the list's revno may not change).
- **Bill analyses for "What it does" (2026-11-22):** the Legislative Service Commission writes an analysis of each
  version of a bill, as introduced too, and a "Final Analysis" of a law. Each bill's documents page,
  https://www.legislature.ohio.gov/legislation/136/hb13/documents, lists them under "Analysis", newest first, each a PDF at
  /download?key=<n> (the page's links have "//download", which answers a 301 to "/download"). robots.txt is
  "User-agent: *", "Disallow:". fetch.py's `AGENT` got 200 for every page and PDF asked; curl's default agent got 403 (so
  the October 403s were probably the agent). The host doesn't send Sectigo's "OV R36" intermediate certificate:
  `context()` in states/oh/analyses.py fetches it from Sectigo (data/oh/sectigo_r36.pem, renewed monthly) and adds it to
  the system's trusted ones. `fetch()` reads the documents page and the final analysis if there is one, else the newest;
  pdftotext (-layout, first 12 pages) gives the text, and the SUMMARY's lines (layout kept) go into
  data/oh/<session>/analyses.json. texts.py turns them into paragraphs (`read()`): each bullet one paragraph, its
  sub-items ("") joined into its sentence, the summary's headings, page headers and footers, footnotes and footnote
  numbers left out. An analysis with no SUMMARY (short bills: HB 13 of the 136th, Roy Rogers Day) uses the DETAILED
  ANALYSIS's opening only when it starts "The bill ..."; else the title's purpose stands. Label: "From the Legislative
  Service Commission's analysis of the bill as passed by the House." (the PDF's "Version:" line: "as reported by the
  Senate Addiction and Community Revitalization Committee"), or "... final analysis." Each run reads at most 160 requests
  in 8 minutes, 2 seconds apart, laws first, then bills with more versions, the newest General Assembly first; a bill again
  only when its versions change (and weekly for 30 days after, while the new analysis is written), or after 60 days when
  none was found; the PDF only when the analysis's key changed. A 403 or 429 stops the reading (the last copies stand);
  PDFs over 20 MB (the budget bills') are skipped. It never fails the run. Coverage: before, 0 bills; a sample of 8 bills
  of the 136th (laws, passed one house, reported, introduced only) all had analyses, and 5 of the 6 PDFs read had a
  SUMMARY; HB 110 and HB 99 of the 134th have them too. About 3,700 bills in three General Assemblies at about 80 a run:
  the first copy takes about 4 days of runs. Needs pdftotext on the runner (poppler-utils).
- **Floor calendars (2026-11-22):** fetch.py's `floor_calendars()` reads the SOLAR API's calendar indexes
  (`/api/v2/general_assembly_<n>/calendars/house/` and `/senate/`, two requests a run; robots.txt allows all) and downloads
  each House and Senate calendar dated today or later when its revno is new (a PDF, read with pdftotext; the newest
  version of a day's calendar, _01, _02 ...; the Senate Rules calendar is left out), into `<session>/floor.json`. Each
  lists the "Bills for Third Consideration" (H. B., S. B., joint resolutions; concurrent resolutions aren't records),
  with the day and time. A calendar is issued the day before. Both are shown as "listed" (can come up that day): of 2026's
  calendars from May 20 to Nov 18 (162 bills on 12 calendars, all records), 32% of the House calendar's bills and 58% of
  the Senate's had a floor vote that day or the next (House bills wait on the calendar for weeks; SB 175 sat on the
  Senate's of Sept. 30 with no vote).
