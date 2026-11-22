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
- **Committee votes member by member (2026-11-22).** Each standing committee's voting record on a bill is a one-page
  text PDF linked from the bill's page, named for the bill and the committee: /<year>RS/votes_comm/sb0448_b&t.pdf,
  /votes_comm/hb0141_app.pdf (mgaleg.maryland.gov/robots.txt answered 404, an IIS "File or directory not found" page, on
  2026-11-22: no robots.txt). A checkmark grid: "Budget and Taxation Committee", "Bill/Resolution Number: SB 448", "Voting
  Record - 2026 Regular Session", "Vote Date: 2/25/2026" (the committee's own day, usually the day before the bill list's
  report date), "Final Action: FAV" (FWA with amendments, UNF unfavorable, WDR the sponsor's withdrawal), each member's mark
  under Yea, Nay, Abstain, Excused or Absent, and a Totals line. A joint referral's second committee has its own record
  (HB 141 of 2026: _gvc, _app, _fin). File names (`COMM_ABBR` in fetch.py, read off 2023-26 bill pages): b&t, eee, fin,
  jpr (Senate); app, ecm, ent, hgo (through 2025), hlt and gvc (from 2026), jud, hru, w&m (House). The Senate's Rules and
  Executive Nominations committees post none (SB 844 of 2026: no link; sb0844_rul.pdf 404). The names are predictable, so
  bill pages aren't read for them: fetch.py's `committee_votes()` (after the floor roll calls, at most MD_COMM_MINUTES, 10,
  of what's left of the run) asks for each committee the bill list shows reporting a bill (favorable, with amendments or
  unfavorable; withdrawn bills have a record too, of the withdrawal, not asked), each once, as text, into
  data/md/votes/<year>/committee.json; a 404 is noted in committee_state.json and asked again weekly while this year's
  session can still post it (through June); "complete" once every record wanted has been asked. About 2,400-2,850 a year
  (25-60 KB each), 10,000 for 2023-26: a first copy takes many runs. Never marks the state incomplete. convert.py's
  `committee_votes()` uses a session's records once that first copy is complete and its floor votes are in (so a session
  never shows committee votes without floor votes, which data_check reads as missing roll calls; MD_VOTES_PARTIAL=1 for
  tests), each as kind "C", named as the bill list names the committee, dated by the Vote Date. A record whose own bill
  number or year isn't the file's is left out. Names only when every row has exactly one mark, each column's marks add up
  to its total and no seat is named twice; else the tally alone. Codes: Nay N, Abstain B, Excused E, Absent A. Traps:
  (1) a long name's title wraps around its mark ("Rosapepe, J., Vice" / mark / "Chair"): the mark belongs to the row above.
  (2) "Chair generally does not vote": the chair has no mark and isn't in the totals; listed as B (present, not voting),
  since a member left out of the list reads as a yes. (3) An unfavorable report's record counts the votes for the motion to
  kill the bill (HB 344 of 2026: 17-0): its yeas are votes against the bill, so yes and no are swapped (shows as "Voted
  down ... 0-17"); test/data_check.py now checks every state for committee votes that say the opposite of the committee's
  report (it also found 3 Colorado bills, HB24-1218, HB24-1310 and SB26-97, whose 9-0 votes to postpone indefinitely read
  as approval: LOOK, not looked into). (4) Names are written without accents and by the whole surname ("Pena-Melnyk, J.",
  "White Holland, J.", "Palakovich Carr, J.", "Lewis Young, K."), where the bill list's names are "Peña-Melnyk", "Holland",
  "Carr", "Young": `vote_seat()` (shared with the floor votes) folds accents and ties a surname to the one member of the
  house whose full name ends with it. Tested 2026-11-22 on 17 records of 2023-26 (every one read, every column added up;
  every name tied to a seat except two former delegates, Jacobs and Otto). Before: no committee votes.
