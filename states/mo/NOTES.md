# Missouri

Moved from CLAUDE.md (2026-11-19). Shared conventions, the data traps list and the site's code notes stay there.

- **Missouri (built 2026-11-13):** `python3 states/mo/fetch.py` reads the
  House's XML exports (documents.house.mo.gov, Crawl-delay 20; house.mo.gov bars "?" addresses and isn't read) and the
  Senate's website (see its docstring) into data/mo/<year>/; `python3 states/mo/contacts.py` (add it to states.json's run
  after fetch.py) builds the contacts; `states/mo/towns.py` was run once. A page a year (`YEARS = 1`): the session opens the
  first Wednesday after the first Monday of January, no bill passes after 6 p.m. on the first Friday after the second
  Monday in May (`lastBillDay()`, `sessionEnds()`), it ends May 30; the veto session is the first Wednesday after the second
  Monday in September (`vetoSession()`). Extraordinary sessions, concurrent and simple resolutions are left out. House bills
  (HB, HJR) come from the House's export, which carries every action in both houses with committee and floor tallies;
  Senate bills (SB, SJR) from the Senate's bill page and "All Actions" list (newest first, no tallies; the House's tallies on
  Senate bills only when the bill is in its SenateActList.xml, about half). Trap: each year's House folder also holds the
  previous year's appropriation bills under their old numbers (2024's HB 1-20 are 2023's budget bills) with nothing but
  "Message Received from the Governor, pursuant to Article IV, Section 27" (spending restrictions, not vetoes): `stub()`
  skips them, and the line is kept as written elsewhere. `states/mo/convert.py` (`walk_house_xml()`, `walk_senate_page()`
  into one `Walk`): House bills go from a standing committee to one of the House's Rules committees ("Rules -
  Administrative", "- Legislative", "- Regulatory Oversight"), which votes again; bills that cost money to Fiscal Review
  (House) / Fiscal Oversight (Senate): all shown as committees, the first standing committee is `firstComms`. "Voted Do
  Pass" lines are skipped (the "Reported Do Pass" report follows, with the House committee's tally); "Perfected" is the
  first floor vote (voice), "Third Read and Passed" the passage; "House Adopts" / "S concurs" agree to the other house's
  changes (the House's tally then is its repassage), conference reports need both houses; "Truly Agreed To and Finally
  Passed" is passed both houses (it happens only after the last vote; 0 bills passed both and weren't sent). A bill combined
  into another (a House file's SubstitutedBy, the Senate's "Bill Combined w/SCS SBs 3 & 5": lead is the first number) gets
  "Combined into HB 594" and stops. Governor: "Approved by Governor" / "Signed by Governor" (law), "Vetoed in Part by
  Governor" (a law with items vetoed: the 12 budget bills each year), "Governor took no action, sent to Secretary of
  State/Article III, Sec. 31" (law without signature: SB 751 of 2024), "Letter of approval" (kept as written), "Failed to
  Pass over Veto" (an item-veto override that failed). No bill was vetoed outright in 2024-2026 ("Vetoed" lines are read
  but none exist). Laws match the Senate's "Truly Agreed To and Finally Passed" lists (BillStatus/TATFP?year=) bill for bill
  (checked 2026-11-13): 2024 44 (29 HB, 15 SB), 2025 64 (37, 27; the governor's 2025 action list agrees), 2026 96 (58, 38).
  Constitutional amendments are joint resolutions: a majority of each house's members, then the voters at the next general
  election or a special election the governor calls (`amendmentOnce`, `ballotEvenYears`, `ballotLine()`); never the
  governor ("Delivered to Secretary of State"): 2024 SJR 71, SJR 78; 2025 HJR 23, HJR 73; 2026 HJR 173, SJR 87, SJR 95.
  Votes: senators member by member from the Senate Journal's text (`senate_rolls()`: "was read the 3rd time and passed by
  the following vote", the bill from the last abbreviated reference before it, "HBs 737 and 486"; conference reports and
  concurrences found too), matched to the passage by day and bill: 313 of 317 Senate passages (2024 61 of 64, 2025 106 of
  107, 2026 all 146; the rest are on journal days not downloaded, 2024-04-17 and 2025-04-22); every list adds up to the
  journal's printed totals. Names are "Brown (16)" (district) or a surname matched to the year's roster (Senate bill list
  sponsors with districts, the House's conferee entries with district 200+n, today's senators); 2024's journals write "Brown
  (16th Dist.)" and sometimes run two names together with one space ("Bernskoetter Brattin", `senate_seats()`). House
  journals: representatives member by member since 2026-11-22 (`house_rolls()`; fetch.py had downloaded the House
  Journal PDFs all along, from documents.house.mo.gov, whose robots.txt sets only a 20-second crawl delay, but the
  converter never read them, so House floor votes showed tallies without names). Each roll call ("AYES: 102" then names in
  columns, "Jones 12" where two share a surname, "Mr. Speaker"; NOES, PRESENT, ABSENT WITH LEAVE, VACANCIES) is used only
  when its names add up to the printed totals, and is matched to the passage by day, bill and the export's ayes and noes:
  2023 182 of 189 House passages, 2024 124 of 144, 2025 176 of 192, 2026 205 of 213; no name failed to match a seat
  (`house_seat()`: the year's member files, else the bills' sponsors and co-sponsors with districts). Committee
  tallies are the House's; committee votes by member since 2026-11-22 (below). "What it does" is the Senate's bill summary of a Senate bill's current version ("From the Missouri
  Senate's summary of the bill's current version (SS SCS SB 3)."): cross-references ("These provisions are identical to
  ...") and the analyst's name dropped, capitals headings in sentence case, "Current law ..." openings led by the "This act"
  sentence; House bills have none (the House's summaries, house/summaries/, weren't downloaded yet: about a third of laws
  have a summary). Titles: the official one-line description ("Modifies provisions relating to county officials"); the short
  title ("COUNTY OFFICIALS", House bills) as the summary line. Topics from committees (`COMMITTEE_TOPICS`), the House's subject
  index (`SUBJECT_TOPICS`) and title words. Earlier years linked by the same description and sponsor (one bill each),
  never laws or appropriations. Contacts: representatives from each year's member files (emails, Capitol phones, leadership;
  past years' files have no phones or emails), senators from members/senate.json (today's: the "Email the Senator" contact
  form, no emails; past senators who left are names only, without party); House committees from CommitteeList.xml, Senate's
  from committees.json. Leaders: Speaker Jonathan Patterson, President Pro Tem Cindy O'Laughlin (the General Assembly
  elected in November 2026 organizes in January 2027). Governor Mike Kehoe (R, since January 13, 2025; before him Mike
  Parson): 15 days, or 45 days from May 30 for bills delivered at the end (`govDeadline()`), else law without signature;
  item vetoes on appropriations; override two-thirds of each house's members (23, 109). The governor's phone and contact
  page are from governor.mo.gov/contact-us (checked by program 2026-11-13, not by the owner). Places (`towns.py`): cities,
  towns, villages, Census-designated places and counties, separate Senate (34) and House (163) lists; St. Louis city once.

- **Committee hearings (2026-11-22):** `agendas()` in states/mo/fetch.py, run after both houses' work, writes
  data/mo/<year>/agendas.json ({"SB1617": [["Senate Education", "2026-02-24T08:00:00"]], "HB1607": [["House Emerging
  Issues", "2026-01-20T16:30:00"]]}), which convert.py's `agendas()` returns as it is. Two sources, both official:
  the Senate's hearing schedule, www.senate.mo.gov/hearingsschedule/hrings.htm (one request a run; robots.txt bars only
  /Trade/ and /DistrictWebApps/), HTML blocks between <hr /> lines: "Committee: <a>Education, Senator Rick Brattin,
  Chairman</a>" (-> "Senate Education"; "Joint Committee on X" -> "Joint X"), "Date: Tuesday, February 24" (no year:
  the nearest to today), "Time: 8:00am" ("10:30 a.m. or Upon Adjournment of ..." reads as 10:30), the bills heard as
  links ("SB 1617", "HCS HBs 1826, 2560, 2349 & 2194": every number; `bills_named()`) and the "Executive Session:" list
  ("SB 1653, 1194<br>SB 1404", up to the first note line); a block headed "Hearing Canceled: ..." is left out. The House:
  no request, since its exports already carry each bill's hearings (<Hearings> in house/bills/<HB>.xml and, for
  Senate bills in House committees, in SenateActList.xml: CommitteeName, NoticeDate, NoticeTime, or AltTime "4:30 PM or
  upon adjournment" when NoticeTime is midnight), read again when the bill's LastTimeRun changes (house.mo.gov's own
  hearing pages are barred: Crawl-delay 120, and "?" addresses). Today to three weeks ahead. When the Senate page can't
  be read, the last file's Senate hearings are kept. Tested on Wayback Machine copies of hrings.htm (2026-02-24: 17
  hearings, 2026-04-16: 10, 3 of them canceled) with the copied 2026 House exports, today set to each day: 450 and 204
  bills, all matching records but one concurrent resolution (SCR 21, now left out); live on 2026-11-22: "no hearings
  scheduled". Untested live: a session-time hrings.htm read by this code, and whether a House XML's LastTimeRun changes
  as soon as a hearing is added (if not, House hearings show up late).
- **Committee votes by member (2026-11-22).** robots.txt, re-read 2026-11-22: documents.house.mo.gov "User-agent: * /
  Crawl-delay: 20"; www.senate.mo.gov "User-agent: * / Disallow: /Trade/ / Disallow: /DistrictWebApps/"; house.mo.gov's
  answered 404 that day (earlier notes: Crawl-delay 120 and every "?" address barred; not read). **House:** the House
  Journal's "COMMITTEE REPORTS" print each report's vote member by member ("Mr. Speaker: Your Committee on Commerce, to
  which was referred HB 1664, HB 1610, HB 1645 and HB 2182, begs leave to report ... by the following vote: / Ayes (6):
  Casteel, Mansur, ... / Noes (1): Kimble / Absent (3): Butz, Gragg and Peters"; "Smith (46)" where two share a surname;
  Present, Absent with leave). fetch.py already reads every journal a bill's actions point to, and the "Reported Do Pass"
  actions point to these, so only convert.py changed: `house_committee_reports()` reads them (a report counts only when
  each group's names add up to its count), `find_committee_report()` ties one to an export tally by bill (any bill the
  report names: combined bills share it), within three days, with the same ayes, noes and present, the same committee
  first; ayes left out, present members coded "B". Tested on four journals (2025 jrn039; 2026 jrn027, jrn028, jrn037),
  through a web fetch service since the House journals aren't in the local copy: 204 of 204 reports read whole; 75 House
  committee votes of 2025 and 150 of 2026 matched; 5 reports matched none (three Consent and Procedure reports naming no
  bill; HB 953's Rules report of 2025-03-13 and HB 2776's of 2026-02-26, which the export doesn't list); every name tied
  to a seat. **Senate:** its journals print committee reports without votes, and its bill pages give no tallies, but each
  committee's minutes page (/Committees/CommitteeMinutes?year=2026&ID=160, linked from its committee page) lists "Bill
  Votes" reports, PDFs (/Committees/Reports/IndexReports?handler=BillVoteReport&year=2026&voteId=6&src=Votes&Type=): the
  committee, bill, executive session date and a grid of each member's YES, NO, ABSENT, ABSTAIN or PRESENT (then a Consent
  grid when one was taken; "Reconsidered Consent" reports are separate and not read). voteIds run through the year (1 to
  about 430 in 2026). fetch.py `committee_votes()` reads the minutes pages (daily in session, weekly otherwise for a live
  year, once for a past one) and each listed report once (senate/committee_votes/<voteId>.txt); convert.py's
  `senate_vote_report()` reads the first grid (each member's row must have exactly one X under a heading, else the report
  isn't used) and `Walk.senate_committee_vote()` adds it as a kind "C" vote tied to the bill's "Voted Do Pass S
  <committee>" line (else its report line), the same committee, from the two weeks before; a "Voted Do Not Pass" line takes
  a report with no more ayes than noes. Senate committee votes had no tallies before (none shown); on the four reports
  saved for testing (SB 1300 of 2024; SB 869, SB 1142, HB 1707 of 2026) all four became named votes. The first copy is
  about 1,300 reports for 2024-2026 at a second each, alongside the Senate's other work.
