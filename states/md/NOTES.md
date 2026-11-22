# Maryland

Moved from CLAUDE.md (2026-11-19). Shared conventions, the data traps list and the site's code notes stay there.

- **Maryland (started 2026-10-31):** `python3 states/md/fetch.py` reads each regular session's bill list
  (https://mgaleg.maryland.gov/<year>RS/misc/billsmasterlist/legislation.json; no robots.txt: sponsors, committees, the date
  and result of each reading in each house, the Department of Legislative Services' synopsis ("What it does"), chapter
  number and status) and the members' pages (district, party, committees with "(Chair)", Annapolis phone, email). Each
  house's member list is read every run, each member's page once a day (members_read.json: the day each was read) and at
  once for a member the list names for the first time (2026-11-21: a second run the same day makes 2 requests, not 189).
  `states/md/convert.py` builds each bill's steps from those dates (floor votes: below). Every bill the General Assembly passes gets a chapter number unless vetoed, so
  after mid-June a passed bill without one is vetoed (some vetoed bills' statuses show a later motion on the veto).
  Constitutional amendments pass once by three-fifths and go to the voters at the next even-year election
  (`STATE.amendmentOnce`, `ballotEvenYears`); they get chapter numbers but aren't laws. 47 districts, each with a senator
  and three delegates, some from subdistricts ("44A"): as in New Jersey, a district's senator and all its delegates are its
  legislators ("S:44", "H:44a/b/c"); the towns list (cities, towns, Census-designated communities and counties) gives one
  district list for both houses. `dataName` is the bill list's form ("Ebersole", "Lewis, R."). One 90-day session a year.
- **Veto letters (2026-11-22):** fetch.py's `veto_letters()` reads the governor's letter for each bill governor_<year>.json
  shows vetoed, at the address the bill page links (/<year>RS/veto_letters/sb0448.pdf; text PDFs, no robots.txt), once,
  into data/md/vetoes/<year>/<SB448>.txt (pdftotext -layout); convert.py's `veto_message()` keeps the letter from "Dear
  President Ferguson:" (or ",") to "Sincerely". A vetoed bill later passed over the veto is a law and doesn't show it.
  Checked on SB 448 of 2026 and SB 587 of 2025 (two pages). Shows after the next download (the local copy has no
  governor_<year>.json).
- **The governor's dates and veto overrides (2026-11-19):** the bill list has no dates for the governor's actions and
  never shows an override: 2025's list, last saved by the General Assembly on 2025-12-01, still says "Vetoed" for the
  bills that became law over the veto in the special session of 2025-12-16 (SB 587, "Chapter 9 of 2025 Special Session";
  HB 270, Chapter 3), and the site showed every law and veto on the bill's last legislative day (SB 448 of 2026: April 9;
  vetoed May 22). `fetch.py` now reads each passed bill's page (its history table: "Post Passage" lines with the
  governor's dates, then "Overridden (111-23)" in each house and "Became law per Maryland Constitution ..."), into
  data/md/governor_<year>.json: a decided bill once, a vetoed one weekly while it can be overridden (this year and last),
  an undecided one daily, every year's vetoes first, at most 11 minutes a run (about 900 to 1,050 pages a year, about 30
  a minute; a first copy takes several runs). A special session's bills in a year's list (HB 2101 of 2026, August) have
  pages under its own code (2026S1). Checked 2026-11-19: 2025, 29 vetoes (May 16), 19 overridden on 2025-12-16, 10 left;
  2026, 5 vetoes (May 22: the veto guide's count), HB 862 and SB 426 overridden in August; 2024, 4 vetoes.
  `convert.py` dates the signature, veto and override from it (keyDates 5 and 6, so an overridden law reads "Became law
  over the governor's veto"); a special session's chapter number isn't kept as the bill's (it repeats the regular
  session's numbers). "Enacted under Article II, Section 17(c)" is a law without the governor's signature. A bill whose
  page isn't read yet keeps the old, undated reading.
- **Committee agendas (2026-11-22):** `agendas()` in states/md/fetch.py (before the governor's pages) reads the hearing
  schedule for yesterday to three weeks ahead in one page,
  /mgawebsite/Meetings/Day/<MMDDYYYY><MMDDYYYY>?budget=show&cmte=allcommittees&updates=show&ys=<year>rs (the address the
  page's own "Range" form goes to; about 1 MB a week in session; the site has no robots.txt), and writes
  data/md/agendas_<year>.json; `agendas()` in convert.py reads it and keeps meetings from today on. `parse_meetings()`:
  each committee banner (class senate/house/other: "Senate Finance", "House Appropriations Capital Budget Subcommittee",
  county delegations as "Joint Anne Arundel Delegation") and its meetings (bill hearings and voting sessions: the day,
  "1:00 PM - ..." (no time: T00:00:00), the bills linked as SB0325, read as SB325). Left out: meetings marked "Canceled",
  bills struck through (removed, "hearsched-strike") and the footer's "Withdrawn bills: HB46, HB 296, ...". The bill list's
  HearingDateTime columns aren't used (no cancellations). Tested 2026-11-22 against the page for 2026-02-16 to 02-20 (105
  meetings, 423 bills, all matched; SB 518 and 519, removed, left out) and live (12 interim meetings, no bills).
  Untested: a range spanning a new session's first weeks under ys=2027rs.
- **Next year's prefiled bills (2026-11-22):** from November fetch.py also reads next year's bill list
  (/2027RS/misc/billsmasterlist/legislation.json answered "[]" on 2026-11-22; prefiled bills are "BillType":
  "Pre-Filed"); legislation_<year>RS.json is written only once it lists a bill, so the session shows as upcoming from its
  first prefiled bill. The bill list never marks Maryland incomplete.
- **Floor votes member by member (2026-11-22).** Each house posts every recorded vote as a numbered PDF the minute it's
  taken: https://mgaleg.maryland.gov/<year>RS/votes/senate/0234.pdf and /votes/house/0234.pdf (both paths checked; no
  robots.txt). Text PDFs: "SEQ NO.", the calendar date and the legislative date, the bill and calendar ("SB 411 Third
  Reading (SB) Calendar No.84"), the question ("On Third Reading"; "Bill is on Third Reading for Final Passage." for the
  vote after the other house's amendments; amendments, special orders, committee reports and quorum calls too), the totals
  line ("42 Yeas 0 Nays 2 Not Voting 0 Excused 3 Absent") and the names in five columns under "Voting Yea", "Voting Nay",
  "Not Voting", "Excused from Voting" and "Excused (Absent)" ("Mr. President", "Speaker", "Washington, M.", "Lewis Young").
  Numbers have gaps (2026's Senate starts at 6) and end at about 1,350 (Senate) and 1,750 (House) a session; 2023's exist.
  `roll_calls()` in fetch.py (last in each run, at most MD_VOTE_MINUTES, 15, of what's left of FETCH_MINUTES) walks each
  year's numbers from 1, each PDF once (150-300 KB, kept as pdftotext text, about 3 KB, in data/md/votes/<year>/<house>.json),
  until 30 numbers in a row are missing; while this year's session can vote (through June), each run asks the next three
  again and numbers missing below the highest once a week (state.json). About 3,100 PDFs a year, 12,000 for 2023-26: a first
  copy takes several runs. `convert.py` uses a session's votes only once both houses' walks have reached their end (so a
  partial first copy never shows; MD_VOTES_PARTIAL=1 for tests). It keeps the third-reading roll calls ("On Third Reading")
  and matches each to the bill list's third reading in that house on its legislative day (the bill list dates readings by
  the house's legislative day, which runs weeks behind the calendar late in the session: a Senate vote on April 10, 2026 is
  dated March 24), the day's last when there are two. Names only when every group's count matches the totals line (else the
  tally alone); "- COPY -" stamped on reposted roll calls isn't a name. Codes: Nay N, Not Voting A, Excused from Voting B,
  Excused (Absent) E. A name ties to today's member written the same way in the bill list (`dataName`), else the one member of
  the house with that surname (and initial), only when that session's bill list names a sponsor of the house so (a member
  who has left or changed houses stays a name, "S?Name"); "Speaker" is Adrienne A. Jones through 2025, Joseline A.
  Peña-Melnyk from 2026 (`PRESIDING`), "Mr. President" Bill Ferguson. Not kept: the final-passage vote after concurrence and
  conference reports (the bill list gives them no day, so they'd have no history line) and override votes; special
  sessions' bills (HB 2101 of 2026) have no roll calls here. Tested 2026-11-22 on 29 PDFs of 2023-26 (every group's names
  matched its count once "- COPY -" was dropped; the six third readings matched their bills, every name tied to a seat).
  Before: no votes at all. Shows once the first copy is in (GitHub Actions).
