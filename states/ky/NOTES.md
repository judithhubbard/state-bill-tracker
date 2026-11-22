# Kentucky

Moved from CLAUDE.md (2026-11-19). Shared conventions, the data traps list and the site's code notes stay there.

- **Kentucky (built 2026-11-08):** `python3 states/ky/fetch.py` reads the Legislative Research Commission's bill record
  (apps.legislature.ky.gov/record/<yy>rs/, static pages; see its docstring) into data/ky/<year>/; `python3
  states/ky/contacts.py` (every year; not yet in states.json's run) builds the contacts from members.json and
  committees.json. A page a year (`YEARS = 1`): a regular session from the first Tuesday after the first Monday of January,
  60 legislative days in even years (to April 15) and 30 in odd years (a few days in January, then February to March 30);
  `session_kind()` is "long"/"short", so statistics compare like with like. Each year's last day is in `STATE.dated` (add
  each year's). Special sessions are left out. House and Senate bills only: joint resolutions (HJR/SJR) have the force of law
  and go to the governor, but they're mostly road namings and directions to agencies, and the shared convention is bills
  plus amendments, so they're left out (the LRC's law lists include them: about 10 a year). Bills "WITHDRAWN" before
  introduction (no title, no history; about 25 a year) are left out. `states/ky/convert.py` follows the bill from house to
  house ("introduced in House", "received in Senate", referrals marked "(H)"/"(S)"; the passage lines don't name the house,
  and a tally larger than the Senate's 38 settles it). Every bill starts in its house's Committee on Committees (the
  leaders), which assigns it to a standing committee: `STATE.gates` ("Committees"); many bills are never assigned (492 in
  2024). "taken from X (H)", "1st reading", "returned to X (H)" are readings while the bill stays in committee; "reported
  favorably, 1st reading, to Calendar" (committees report favorably or not at all; no tallies); "2nd reading, to Rules" and
  "posted for passage in the Regular Orders of the Day" (Rules, the leaders, schedules floor votes); "recommitted to X (H)"
  puts a reported bill back in committee; "3rd reading, passed 79-17 with Committee Substitute (1)" is the passage (in the
  second house "with" an amendment means the first has to agree). Back in the first house: "House concurred in Senate
  Committee Substitute (1)" and "passed 90-5 ..." again, or "refused to concur", "Senate receded/refused to recede",
  conference and free conference committees ("Conference Committee report adopted in House and Senate" can be the report
  that they failed to agree, followed by a free conference committee: only "passed" lines and enrollment count). "enrolled,
  signed by Speaker of the House / President of the Senate" is passed both houses; "delivered to Governor"; "signed by
  Governor (Acts Ch. 4)", "became law without Governor's Signature (Acts Ch. 19)", "Vetoed", "23 line items vetoed", then on
  the veto days "veto overridden", "passed 72-27" (the override vote, not counted as a passage) and "delivered to Secretary
  of State (Acts Ch. 175)". A veto after the last day stands: "Vetoed and delivered with Veto Message to Secretary of
  State", or (SB 70 of 2026) "Vetoed" then "delivered to Secretary of State" with no chapter, which must not be read as an
  override. A law is a bill with an Acts chapter (`STATE.lawWord` "Acts ch."), not a constitutional amendment. Laws and
  vetoes match the LRC's status lists (list.json's `law_routes`/`veto_routes`) bill for bill (`python3 -m states.ky.convert`
  prints the comparison): 2024 212 laws (169 signed, 21 without signature, 21 over a veto, 1 filed without signature), 2
  vetoes standing (both after the session), 21 overridden, line-item vetoes on HB 1, HB 6, HB 265; 2025 148 laws (111, 11,
  26), every veto overridden, line items on HB 546, HB 566, HB 622, SB 25; 2026 191 laws (145, 17, 29), 1 veto standing (SB
  70), line items on 7 budget bills. Constitutional amendments are bills ("AN ACT proposing to amend Section 77 of the
  Constitution of Kentucky"): three-fifths of each house's members, then the voters at the next even-year November election
  (`amendmentOnce`, `ballotEvenYears`); they get Acts chapters and go to the Secretary of State, never the governor (2024 HB
  2 and SB 143; 2026 SB 10), tagged "const", stage 3. Votes: see "Members' floor votes" below. "What it does" is the LRC's
  summary of the enacted version for a law, else of the bill as introduced. Titles: the official "AN ACT relating to X"
  as "X" (amendments "Constitutional amendment: ..."); the summary is the official title. Sponsors in order as "K. Moser"
  (2024's link to the district page: 1-100 House, 101-138 Senate districts): matched to today's members by initial and
  surname ("DJ Johnson", "G. Brown Jr.", "S. Funke Frommeyer"), else kept as written with the linked district (`resolve()`);
  only current members are published, so a past year's contacts are the current members who sponsored that year. Topics
  from committees (`COMMITTEE_TOPICS`) and the first six LRC index headings (`HEADING_TOPICS`; the record writes "And" and
  "and", so they're matched in lower case). Earlier years linked by the same title and prime sponsor, or the same LRC
  summary word for word, one bill in each year, never laws or appropriations. Governor (Andy Beshear, D, term-limited;
  the next takes office in December 2027: add to `GOVERNORS` and legislatures.json) 10 days, Sundays excepted, in and after
  the session, from delivery or, for a bill the sine die adjournment keeps from being returned, from the adjournment (sec.
  88; until 2026-11-21 the profile counted from delivery only) (no pocket veto: a bill not returned becomes law); line-item vetoes on appropriations; override a majority of
  each house's members ("majority"; the Republican supermajority overrides most vetoes). The governor's contact page
  (ppc.ky.gov's constituent services form) and main line (502) 564-2611 are from governor.ky.gov's footer (checked by
  program 2026-11-08, not by the owner). Most members list only "LRC: 502-564-8100", the LRC's message line for every member:
  shown as "Capitol (LRC message line)", after a member's own home or work number. Leaders from the member list (Speaker
  David W. Osborne; Senate President Robert Stivers, a senator); the General Assembly elected in November 2026 organizes in
  January 2027. Separate Senate (38) and House (100) districts by city or county (`states/ky/towns.py`, from the Census
  Bureau's 2024 district files).

- **Committee agendas (2026-11-22):** `agendas()` in states/ky/fetch.py, run after the bills, writes
  data/ky/<year>/agendas.json ({"HB414": [["House Local Government (H)", "2026-02-17T13:00:00"]]}); convert.py's
  `agendas()` words the names as the histories do ("House Local Government"). It reads the LRC's weekly calendar
  (apps.legislature.ky.gov/LegislativeCalendar/) first: between sessions every day says "No Meetings Scheduled", and
  nothing more is read (one request; the file is emptied). During a session the calendar lists the days ahead in the week
  (archived copies of 2026-01-28 and 2026-02-17 show only that day), each meeting as a TimeAndLocation ("1:00 pm, Annex
  Room 171", "12:00 Noon", "Upon Adj. of the House": T00:00:00), a CommitteeName linked to its CommitteeRSN (named from
  committees.json) and an Agenda with "26RS HB 414" lines (`calendar_meetings()`). For the days the calendar doesn't show,
  it reads each House and Senate standing committee's meeting-materials page (apps.legislature.ky.gov/CommitteeDocuments/
  <id>/, about 46 pages, one a second, only while the calendar has meetings) and, for each meeting up to three weeks
  ahead (the page's <h3> date over the meeting's files), the file named "...Agenda..." (a PDF, pdftotext -layout; the
  time from its heading). This year's regular session only ("26RS"; joint resolutions on agendas are kept in the file
  but the converter has no such records). apps.legislature.ky.gov has no robots.txt. Tested on the archived calendar of
  2026-02-17 (6 meetings, today set to that day) plus three committees' materials pages and agenda PDFs read live: 43
  bills on 16 meetings, all but the two HJRs matching records. Untested live: a session-time calendar read by this code
  (its markup is from the Wayback Machine's copies), and how early agendas reach the materials pages.
- **Veto messages (2026-11-22, OCR, the owner's decision):** each vetoed or line-item vetoed bill's record page links
  "Governor's Veto Message" (/record/26rs/sb70/veto.pdf; 29 in 2024, 30 in 2025, 39 in 2026, most of them overridden).
  They are scans with no text layer. `veto_letters()` in fetch.py, after the agendas, reads each once by OCR into
  <year>/vetoes/<SB70>.json (states/letters.py's `scanned()`; at most 6 minutes a year a run, the rest next run).
  `veto_message()` in convert.py keeps the reasons: from after "I, Andy Beshear, Governor ... do hereby veto the
  following:" (and "Senate Bill 70 of the 2026 Regular Session ... in its entirety.") to "This, the 19th day of March,
  2025." A budget's line-item letter repeats that sentence for each part ("Page 8, line 21, after "annually" delete ...",
  then "I am vetoing this part because ..."); it goes on the law as kind "line-item". A veto the General Assembly
  overrode isn't shown (the page shows a message only on a bill still vetoed or a line-item law; the letters are kept, so
  showing them on overridden laws would need only that). Quality on four letters (SB 70 of 2026, HB 4 of 2025, HB 18 and
  the 8-page HB 6 of 2024): the typed text, italics too, reads with almost no errors ("Iam", "T am", fixed in the
  converter); the stamps, signatures and the "This, the 19th day" line come out garbled and are cut.
- **Members' floor votes (2026-11-22):** `vote_histories()` in states/ky/fetch.py (after the bills, at most 10 minutes a
  year a run) reads each voted bill's vote_history.pdf (/record/26rs/hb1/vote_history.pdf, linked from its record page;
  apps.legislature.ky.gov has no robots.txt) with pdftotext -layout into data/ky/<year>/votes/<HB1>.txt, again when the
  bill's history gains a tally line (votes/state.json keeps the lines it was read under). About 330 bills a year (329 in
  2024, 261 in 2025, 349 in 2026), so a first copy takes two or three runs. Each file holds every floor roll call on the
  bill, House ("Commonwealth of Kentucky / House of Representatives", "RCS# 134") and Senate ("COMMONWEALTH OF KENTUCKY
  SENATE", "RSN# 3843"): the bill, or the amendment voted on ("HB 1 HFA 6"), the date, the motion and time ("Pass",
  "Final Passage", "PASS HB 2 w/ SCS 1", "CONSENT PASSAGE OF HB 134", "Table", "Suspend the Rules", "Previous Question",
  "Adopt", "Veto Override", "OVERRIDE VETO FINAL PASSAGE HB"), the totals (YEAS, NAYS, ABSTAINED (the Senate's PASSES),
  NOT VOTING) and each group's surnames in columns ("Lewis D", "Bratcher S.", "Tackett Laferty"; the Senate's
  "ChambersArmstrong" has no space). convert.py gives each history tally the bill's own roll call that day in that house
  with those ayes and noes (not an amendment's or a procedural motion's; two 32-5 Senate votes on HB 2 of 2026 on April 1
  each take their own), only when every group's names add up to its total; abstentions are "B", not voting "A". Names
  go to the current member of that house with that surname (and initial) whose profile's Service line ("House 2022 - 24,
  Senate 2025 - Present") covers the year in that house, else stay names (2024's "H?Herron" and "H?Rawlings", now
  senators; members who left). Override votes ("veto overridden", "passed 72-27") aren't vote records, as before.
  `python3 -m states.ky.convert` prints "floor tallies" (named, no roll call read, unmatched) and up to ten tallies that
  matched no roll call read. Tested 2026-11-22 on 23 bills' files read live (HB 1, HB 2, HB 6, HB 4 and others across
  2024-26: passages, concurrences, free conference reports, consent passages): all 63 tallies matched, every group's names
  added up, every 2026 name tied to a seat, 2025's six untied all Senator Yates's (no longer a member), 2024's 36 all
  former members or members since moved to the Senate. Before: 1,770 floor votes, none naming members. The rest arrive with the next downloads.
- **Committee votes by member: looked into, not built (2026-11-22).** No text source: committees report "favorably" with
  no tally in the bill histories, each bill's vote_history.pdf has floor roll calls only, and the standing committees'
  meeting-materials pages (CommitteeDocuments/<id>/) carry agendas and amendments, no minutes. The only record is the
  LRC's daily scans (/record/26rs/committee_votes_House.html -> house_votes/<day>_comm_votes.pdf, and the Senate's;
  60 House and 60 Senate PDFs in 2024 and 2026, 30 each in 2025; 4 to 13 pages each; apps.legislature.ky.gov's
  robots.txt answers 404, none). Each page is a 300 dpi scan of the committee's report form: the House's lists "Rep Chad
  Aull ... Yes No Pass" with the vote circled by hand; the Senate's a grid of Yea/Nay/Pass cells with hand checkmarks.
  The totals ("ROLL CALL 14 Yes 3 No 2 Pass", the Senate's "Totals") are handwritten. Measured on HB 20's day (2026
  House PDF 20, 12 roll-call sheets, and Senate PDF 20): tesseract reads the printed names, bill and committee well
  (House; the Senate's grid lines garble them), but none of the 11 nonzero handwritten totals (best of psm 7/8/10/13,
  digits only, underline removed), so no sheet can be checked against its own totals. A prototype reading the House's
  circles (ink in the gaps around each printed Yes/No/Pass) got 40 of 42 members right on two sheets after tuning on
  those same sheets; the two misses (a "No" circle drawn mostly over the Yes-No gap, a stray tick by an absent
  member's Yes) look like real votes to it, and one of the two sheets came out wrong. Left out until the totals can be
  read (a handwriting-capable reader) or the LRC publishes the tallies as text.
