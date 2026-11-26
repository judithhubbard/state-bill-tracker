# Virginia

Moved from CLAUDE.md (2026-11-19). Shared conventions, the data traps list and the site's code notes stay there.

- **Virginia, step 1 (bills, stages, votes; built 2026-10-29):** `python3 states/va/fetch.py` downloads the Legislative
  Information System's CSVs into data/va/<year>1/ (see the va-data-sources memory); `states/va/convert.py` reads them.
  Sessions run one year (`YEARS = 1`) and the lower house is the House of Delegates (`LOWER = "H"`, members "Del.");
  tracker.html reads these as `YEARS`/`lastYear()` and `LOW`/`BOTH`/`TITLE`, so no code assumes "A" or two-year
  sessions. History lines are plain English and kept as written, except the steps the site's rules use. The
  file's Approved/Vetoed flags are unreliable (both set, or in 2025 neither): the history decides. A bill the
  governor sent back with amendments is "Passed both houses" until the reconvened session. Bills continued to
  the next year appear in the next year's folder under the same number. Legislators (step 2, 2026-10-29): `states/va/contacts.py` (run daily by fetch.py) reads the House member list and
  committee pages and the Senate's spreadsheet, email list and senator pages (committees marked "(Chair)"); seat ids
  are "S:34"/"H:71", and the data files' member ids ("S0100") match the Senate site's ("S100") once zero-padded.
  `states/va/towns.py` turns the districts' locality descriptions into data/va/district_towns.json, with separate
  Senate and House districts per locality; `renderTownRepsByHouse()` shows it (a split locality picks each district).
  "What it does" (step 3): `states/va/texts.py` takes each bill's latest Legislative Services summary into
  data/va/texts_<year>.json, with a label saying which version it describes. Step 4 (2026-10-29): states/va/how.html and
  weighin.html, a one-year calendar (`STATE.calendar`, `opens()`, `reconvenes()`), the notice between sessions
  (`STATE.sessionNotice`), "passed by indefinitely" (`heldLabel`/`heldTip`/`heldNote`), bills continued to next year
  (`STATE.continuedTo`, no "reintroduce" ask), and one number through both houses (`STATE.oneNumber`: no "it has no
  Senate version"). Statistics hide what a state's data can't support: repeat tries and "came back" without links
  across sessions (`linkedSessions()`), past party rows without past parties. The 2024 files write dates as
  "2024-03-02T00:00:00"; a bill that died in conference is still flagged "Passed" (it's one house's bill).
  Earlier years (2026-10-29): `earlier()` in states/va/convert.py links a bill to the same bill up to two years back
  (continued bills by number; otherwise the same subject heading and either a summary sharing 60% of its words, or a
  rarity-weighted similarity of 0.66; 40% and 0.55 with the same chief patron; never "Relief" claims or the yearly
  drug-schedule bill). Checked by hand 2026-10-29: of 30 random links, 27 were plainly the same bill and 3 closely
  related; some heavily reworked repeats are missed), so "this bill in other sessions", repeat tries and watchlist carry-over work. One-year
  sessions use `YEARS` for "the next session" (build_data.py's comeback counts, carryCandidates()). 2023 (added
  2026-11-17): the LIS files start with 2024, so fetch.py reads a finished session they lack once from the legacy LIS
  (legacylis.virginia.gov/SiteInformation/csv/231/<name>, robots.txt allows all; saved under the usual names). Its
  formats differ: dates "02/15/23", padded numbers ("HB0029"), Patron_id "H309", "Last, First" names (`member_name()`),
  governor's lines marked "G ", 2022's committee votes "H01C0038", summary kinds "Introduced"/"Passed House of
  Origin"/"Passed Both Chambers"/"Enacted", and Summaries.csv in UTF-8 (`rows()` tries UTF-8 first). Bills continued
  from 2022 (162 died in committee in November 2022) are in it. Totals: 811 laws (chapters 1-812, 739 being SJ 231, a
  constitutional amendment), 8 vetoes (3 in March, 5 in May; 819 bills sent, as the governor's office counted). It
  reconvened April 12 (`dated`; the rule gives April 5).

- **Fewer yearly chores (2026-10-29):** Virginia's session dates are computed (`opens()`, `sessionEnds()`, `crossover()` in
  states/va/profile.js: 60 or 46 days from the second Wednesday of January; crossover the 35th or 28th day), with
  `dated` for a year that differs. Crossover is each bill's deadline until it passes its own house
  (`STATE.originDeadline`), and after it the bill can't pass that year. Virginia's floor leaders and members' first
  years come from the houses' sites (contacts.py).
- **Floor calendars (looked for 2026-11-22): none from an allowed source.** The daily floor calendars ("Daily Floor
  Calendars", lis.virginia.gov/session-details/<session>/calendar) are only in the new LIS, a page that reads them from
  the LIS API (lisva.azurewebsites.net/Calendar), whose key is for personal, non-commercial use (not used; the page's own
  key isn't ours to use). Their PDFs are lis.blob.core.windows.net/files/<number>.PDF, numbered with every other LIS
  document, so they can't be found without the API. The LIS CSV files (lis.blob.core.windows.net/lisfiles/<session>/, and
  the legacy list on legacylis.virginia.gov/SiteInformation/ftp.html) have no calendar: its "Agenda.csv" was "not created
  yet" and answers 404 for 2023-25; CALENDAR.CSV and the like answer 404 too. The Senate Clerk's calendar app
  (apps.senate.virginia.gov/calendar/cal.php, public in 2023-25: "SENATE CALENDAR ... THIRD READING ...") now sends
  visitors to a Senate HUB login (apps.senate.virginia.gov/docket/, seen from February 2026). The House's site
  (house.vga.virginia.gov: robots.txt allows all) has committee meetings, agendas and the minutes after the day, no floor
  calendar; vga.virginia.gov's "Meeting Calendars & Schedules" page links the LIS calendar. Asking the Clerks (House Clerk's
  Office, Senate Clerk's Office) for a public file, or a key whose terms fit, is the owner's call.

- **Likely floor votes (2026-11-22):** the LIS files have no floor calendar (the API that has one needs a key we don't
  use yet), so `likely_votes()` in convert.py guesses the day from HISTORY.CSV: a bill whose last line in its house is
  the second reading ("Read second time and engrossed"; the Senate's "Constitutional reading dispensed (on 2nd
  reading)"), followed only by amendments, engrossment and the like, gets the next weekday as a "likely" floor day
  (states/floorcal.py); a "Passed by for the day" moves it to the next weekday after that line. Measured on 2024-26
  (notes/agendas-survey.md, "Likely floor votes"): of 6,234 second readings that were a bill's latest step, the third
  reading came the next session day 91.6%, two days later 7.3%, three 0.8%, four or more 0.3%; replayed evening by
  evening, the vote came on the predicted day 92.2%, the bill was passed by for the day then 6.5% (the next evening
  predicts again), later 0.8%, never 0.4%. Floor days are weekdays (a Saturday or Sunday 1-3 times a session). Lines of
  bills continued from the last session (dated then) are left out. Not handled: a second reading on the session's last
  day or on crossover day (the next weekday is past the deadline; rare).
- **Chapters and parties in every session (2026-11-26):** 2025's BILLS.CSV (saved 2025-10-29) has no Approved flag and no
  Chapter_id on any bill, so its 721 laws had no chapter; convert.py now takes the chapter from the history's "Approved by
  Governor-Chapter 366" / "Enacted, Chapter N" line when the column is empty (721 of 721). Sponsors' parties were read only
  for the current session (contacts_<session>.json), so 2023-25 and the prefiled 2027 had none (0%; issue pages'
  "Sponsor's party" and the Statistics party rows were blank). LIS member ids ("H0386") are the same in every session:
  other sessions take each id's party from the newest contacts file that has it, then from states/va/parties.json
  (states/va/parties.py, run by hand: the 82 members who left, from Open States' public-domain people data by house and
  name, a member who changed houses by name, and three by hand). Now 96% (2023), 99%, 99%, 97% (2026), 100% (2027); the
  rest are committees and the Governor's bills. test/data_check.py FAILs when a recent session's sponsor parties or laws'
  chapters fall far below another session's.
- **"Enacted, Chapter N" (2026-11-23):** a bill that became law when the General Assembly accepted the governor's
  amendments (about 60 a year) is "ENACTED CHAP.N", not "SIGNED CHAP.N": the page said "Signed into law"; now "Became law".
- **Identical House and Senate bills are one record (2026-11-26, the owner's request: HB 965 and SB 322 of 2026, the
  National Popular Vote Compact, were two rows everywhere).** Members file the same bill in both houses and Virginia often
  passes and signs both, each with its own chapter. The LIS files have no companion field; `pair_up()` in convert.py
  pairs one House and one Senate bill (or joint resolution) when a summary says so ("This bill is identical to SB 388.",
  in the summaries of bills as passed: 283 pairs in 2026), or when they have the same short description (spacing and
  punctuation aside; bills incorporated into another left out) and summaries 80% alike (shared words, or shared runs of
  six letters where a file runs words together); never when both reached the governor with different results. Pairs:
  316 (2023), 314 (2024), 280 (2025), 366 (2026), 25 (2027). About 50 read by hand: no false pairs; the least alike are
  companions one house amended (HB 24 / SB 115 of 2026). As in New Jersey, the record leads with the bill that got
  further (else the House bill), keeps each bill's history, votes and sponsors as its versions, and answers to both
  numbers (links, stars, search); the chapter shown is the leading bill's.
  **Counted once, and said so (the owner's choice, 2026-11-26):** a pair that both became law is one law here and two
  chapters in Virginia's totals; its record's `twinLaws` counts the second. build_data.py's `outcomes()` carries the
  count per session and topic (sixth number) and `write_compare()` per session ("pairedLaws"), so the Sessions table's
  "Became law" ⓘ ("Virginia's 1,126 chapters include 277 laws passed twice, once from each house; each pair counts once
  here."), the odds chart's note and /compare/'s "Became law" ⓘ say how many. Laws + second chapters = Virginia's
  chapters: 580 + 231 = 811 (2023), 657 + 186 = 843 (2024), 581 + 140 = 721 (2025), 849 + 277 = 1,126 (2026);
  test/data_check.py's "compare with the official totals" line adds them up beside the highest chapter number.
  The light history is paired by the same rule (`light_twins()`, called by build_data.py's `load_light()`): 251 laws
  passed twice in 2020, 52 in 2021 (a short session), 116 in 2017. 2017's and 2019's files lack a summary for about half
  their bills (937 and 1,204), so same-title pairs with no summary stay two records there (about 90 a year); 2018 and 2019
  are held off the site anyway (records that stop short of the governor).
