# Idaho

Moved from CLAUDE.md (2026-11-19). Shared conventions, the data traps list and the site's code notes stay there.

- **Idaho (built 2026-11-08):** `python3 states/id/fetch.py` reads
  legislature.idaho.gov's pages (no API; see its docstring) into data/id/<year>/; `python3 states/id/contacts.py` (every
  year) builds the contacts. A page a year (`YEARS = 1`): the two-year Legislature (the 68th is 2025-26) meets once a year,
  from the second Monday of January to late March or April, and bills die at each adjournment (the second year's numbers
  carry on: 2026's House bills from H0501); laws, deadlines and the governor's actions are yearly. Bills are "H3", "S1023",
  "HJR4" (`official()` pads them back: "H0003"). `states/id/convert.py` reads each bill page's history, whose lines don't
  name the house: the bill is followed ("Received from the House ...", "Returned from the Senate ..." move it before the
  line; "Title apvd - to Senate", "Signed by President; returned to House", "Transmitted to Senate" after it), and a roll
  call's size (70 or 35) settles it. "Introduced, read first time, referred to JRA for Printing" is the print hearing's
  formality (a committee voted to introduce it); "Reported Printed and Referred to X" is the referral; budget bills from
  JFAC go straight to the floor ("Reported Printed; Filed for Second Reading"); members' personal bills are "Filed in the
  Office of the Chief Clerk" and go nowhere. "Reported out of Committee with Do Pass Recommendation", "... to 14th Order for
  amendment" (Senate) and "... Recommend place on General Orders" (House) are approvals; "Reported out without
  recommendation, as amended" is the Committee of the Whole, not a committee. "PASSED - 56-11-3" (ayes, nays, absent) with
  AYES/NAYS/Absent lists by surname; "FAILED" ends a bill unless "Motion to reconsider - PASSED" (`endedNote()`, as North
  Dakota's). Passed both houses: enrolled ("to JRA for Enrolling", "referred to enrolling"), or the second house passed it
  unamended, or the first concurred and passed it again (Idaho re-passes the engrossed bill after concurring). Governor's
  lines carry their own date ("Reported Signed by Governor on April 4, 2025", "Delivered to Governor at 3:04 p.m. on ...").
  Laws and vetoes also come from the list page's Enacted Legislation table and vetoed list, which agree with the histories
  bill for bill: 2024 330 laws (chapters 1-330), 2 vetoes; 2025 340 laws (one with line-item vetoes, H 482), 1 veto (S 1023,
  override failed in the Senate); 2026 344 laws, 4 vetoes; no veto was overridden. Joint resolutions (HJR/SJR) propose
  constitutional amendments: two-thirds of each house's members, then the voters (`amendmentOnce`); they go to the
  Secretary of State, never the governor (2024 HJR 5; 2025 HJR 4 and HJR 6). Sponsors (2026-11-22): nearly every bill is a committee's
  ("House State Affairs Committee"); the member who asked is named only in the Statement of Purpose's "Contact:" section
  ("Representative Jordan Redman", one a line, a phone under some; sometimes several, sometimes agency staff: "Bryan
  Nickels", "Office of Administrative Hearings"; titles after a comma: "Senator Ben Toews, Majority Caucus Chair").
  `texts.contacts()` reads them from sop/<key>.txt and `member_named()` in convert.py matches each to the year's members
  (roster(): the title's house and surname, the first name too when two share a surname or there's no title; "Ted Hill"
  = 2024's "Edward H. Hill"). The first in the bill's own house is its sponsor, through the committee (vers' `via`:
  "Jordan Redman, through the House Health and Welfare Committee"), others there are sponsors too (primes, counted as
  sponsors on legislators' pages and in sponsor_class()); members of the other house named (usually who carries it
  there) are shown ("with Sen. Tammy Nichols", `with`), not counted; untitled names are kept only when they're a
  member's full name. A statement naming no member leaves the committee as sponsor ("for Rep. X" when it names only one
  of the other house: S 1276 of 2024). Floor sponsors ("Floor sponsor - Ehardt", "Sponsors - Boyle & Shirts") are
  resolved to members of the house acting (`resolver()`) and shown as "Floor sponsors: Barbara Ehardt (House) and Carl
  J. Bjerke (Senate)" (`floor`); they aren't counted as sponsorships (a floor sponsor carries a bill the committee
  already sent out; counting them would credit leaders and chairs with most of the year's bills). build_data.py's
  `sponsor_extra()` writes via/with/floor after the version's link (every other state writes nothing there). In 38
  statements read on 2026-11-22 (7 a year on the owner's computer, 18 more fetched by hand) every titled name matched;
  the whole count per year is data_check.py's LOOK line ("N of M statements name a member of the bill's house"; FAIL
  when under 60% of 50 or more, or when titled names match no member). The personal bills ("by RUBEL", ~20 a year)
  keep their named member. Titles are the list's short
  titles with abbreviations spelled out (`ABBREV`: "Approp, ITS, add'l" -> "Appropriation, ITS, additional"); the summary
  is the one-line description; "What it does" is the bill's Statement of Purpose, written for its sponsor
  ("From the sponsor's statement of purpose."; sponsors' statements kept, the owner's decision 2026-11-14), from
  /wp-content/uploads/sessioninfo/<year>/legislation/H0003SOP.pdf: only the purpose, without the fiscal note, contact or
  disclaimer, cut at 2,500 characters (`states/id/texts.py`). fetch.py's `statements()` reads each once (pdftotext; sop/
  and sop.json) and, while a year is live, asks again with If-Modified-Since when the bill's status changes (sponsors
  revise them in place); a missing one is an HTML page with status 200 (checked for "%PDF"). The first copy (about
  2,100) takes about 50 minutes; statements never mark Idaho incomplete. Roll-call
  names: "Crane(12)" (district), "Mr. Speaker" (Moyle), and substitutes written with both names, in a different order in
  each house: the House puts the member first ("Hill(Brown)": Brown sits for Hill), the Senate the substitute first
  ("Coho(Lenney)"); a name on that year's lists decides (`resolver()`). Members come from each year's committee pages
  (party by column; no House seat letter: past years take the current member's seat A/B where they still hold it, else
  the one left) and, for the latest year, the current member list; members not on a year's committee pages (the Speaker
  serves on none) take a current member's seat when it's free; members who left are "H?Achilles" (2024: Chew, Lee, Dixon,
  Nash; 2025: Achilles, Andrus). Each district elects a senator and two representatives: seats "S:12", "H:12a" (seat A),
  "H:12b"; one district list for both houses (`towns.py`: cities, communities and counties, "Boise City city" as "Boise
  city"). Topics from committees (`COMMITTEE_TOPICS`) and words in the subject heading and title. Earlier years linked by
  identical short title, one bill in each year, never appropriations or laws. Governor 5 days (Sundays excepted) in
  session, 10 days (Sundays excepted) after adjournment; no pocket veto; override two-thirds of the members present (each
  year's last floor day is in `STATE.dated`: add each year's). The governor's phone and contact page are from
  gov.idaho.gov/contact/ (checked by program 2026-11-08, not by the owner). Leaders from the member list (Speaker Mike
  Moyle, President Pro Tempore Kelly Anthon); the 69th Legislature organizes in December 2026.
- **Committee agendas (2026-11-22):** `agendas()` in states/id/fetch.py (every full run, after the members) reads the
  House and Senate Committee Agendas pages (/sessioninfo/agenda/hagenda/ and sagenda/; robots.txt allows them: it bars
  only the committee calendar's action~ views) for links to the agenda PDFs, named by day, committee and time
  ("/wp-content/uploads/sessioninfo/2026/standingcommittees/260309_hjud_0130PM-Agenda.pdf",
  "260311_hjud_other_meet_time-Agenda.pdf"; "no_meeting" files skipped). When those pages link none during January to
  April it reads each standing committee's page instead (about 25 requests), whose meeting lists link the same files.
  Each PDF dated yesterday to three weeks ahead is read every run (amended agendas keep the file name: "AMENDED AGENDA
  #2") with pdftotext: the heading gives the committee ("HOUSE JUDICIARY, RULES & ADMINISTRATION COMMITTEE" -> "House
  Judiciary, Rules and Administration", the converter's wording), the time ("1:30 P.M. or Upon Adjournment") and the day;
  the SUBJECT column's "H 681", "S 1296", "HJR 4" are the bills ("RS 33000", a draft at its print hearing, isn't one
  yet). Into data/id/<this year>/agendas.json; `agendas()` in convert.py keeps meetings from today on. Tested on the
  2026 committee pages saved here (HJUD, SSTA) with their agenda PDFs for March 9-11, 2026: 4 agendas, 16 bills, all
  matching 2026 records. Untested: what the two agendas pages look like during a session (on 2026-11-22 they say "No
  agendas currently available"); if they don't link the PDFs the committee pages are read instead. A failed request
  keeps the last file; without pdftotext it's skipped.
- **The next session (2026-11-22):** Idaho lists no bills before the session (/sessioninfo/2027/legislation/ answered 404 on 2026-11-22); 2027 is read from January 1 (the window's new year) and appears once its list has a bill, from about January 12, 2027. The current year's missing bill pages never hold Idaho back (`never_downloaded()`: one a run missed is read the next run).
