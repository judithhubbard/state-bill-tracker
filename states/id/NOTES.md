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
  Secretary of State, never the governor (2024 HJR 5; 2025 HJR 4 and HJR 6). Sponsors: nearly every bill is a committee's
  ("House State Affairs Committee"); the member who asked is named only in the Statement of Purpose (a PDF, not
  downloaded), and the floor sponsors are history lines ("Floor sponsor: Bruce"), so legislators' sponsorship numbers
  count only the ~20 personal bills a year ("by RUBEL"); How's "About this data" says so. Titles are the list's short
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
