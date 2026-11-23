# Mississippi

Moved from CLAUDE.md (2026-11-19). Shared conventions, the data traps list and the site's code notes stay there.

- **Mississippi (built 2026-11-08):** `python3 states/ms/fetch.py`
  reads the Legislature's bill status system (billstatus.ls.state.ms.us: static XML, ISO-8859-1; no robots.txt; a CA bundle
  for the missing GlobalSign intermediate; see its docstring) into data/ms/<year>/; `python3 states/ms/contacts.py` (current
  year; add it to states.json's run) builds the contacts from data/ms/members/. A page a year (`YEARS = 1`): one session
  a year from the Tuesday after the first Monday of January, 90 days, 125 in a four-year term's first year (2024, 2028);
  each year's last floor day is in `STATE.dated` (add each year's). Extraordinary sessions are left out (2025's June budget
  session, where the three line-item vetoes of 2025 were). `states/ms/convert.py` reads each history file: actions are
  "MM/DD (H) ..." with no year (`dated()`: the session's, the next year's for a line months before the one above it).
  "Referred To X;Y" (a double referral: X first), "DR - TSDP: JA To AP" (X approved it, on to Y, by code: h_cmte.xml /
  s_cmte.xml; "TSDPAA", "TSDPCS", "TSDBA" variants), "Title Suff Do Pass ..." / "... Do Be Adopted" approved; deadlines
  kill most bills ("Died In Committee", "Died On Calendar", "Died In Conference": `STATE.endedNote()` words them);
  "Passed"/"Adopted" the passage; "Reconsidered" undoes the house's last decisive vote (passage, concurrence, conference
  report), and a "Motion to Reconsider Entered" never decided holds it: when the bill then dies, the vote never took effect
  (HB 1602 of 2026, shown as died on the House calendar). Passed both houses: "Concurred in Amend From ...", "Returned For
  Enrolling", a conference report adopted by both houses (since the last "Recommitted For Further Conf"), or a presiding
  officer's "Enrolled Bill Signed"; sent to the governor once both have signed (the history never shows the delivery).
  "Approved by Governor", "Law W/out Governor's Signature", "Partially Vetoed By Governor" (a law), "Vetoed", "Veto
  Overridden" in both houses; the chapter number (CHAPNUM) is the law's number, and a vetoed bill whose override passed
  only the House (HB 1648 of 2026: DISPOSITION says "Law", no chapter) stays vetoed. Concurrent resolutions whose short
  title starts "Constitution;" are tagged "const" (two-thirds of each house, then the voters: `amendmentOnce`,
  `ballotLine()`); other resolutions are left out. Titles are the short titles; the summary is the long title in sentence
  case (`sentence()`: names restored from the short title's capitalized phrases), plus "Passing it takes three-fifths of
  each house" when VOTETYPE says so; no "What it does" (there are no summaries). Floor votes: from the roll-call PDFs
  the history lines link (below, 2026-11-22); the history lines carry no tallies. Local and private bills (the Local and Private Legislation committees) are narrow kind
  "place" and topic "local"; "Suffrage; restore to <a person>" bills (20-70 a year) are narrow kind "person". Authors by their author-page slug ("creekmore_iv"), named from the current member files, else
  that year's h_auth.xml / s_auth.xml. Contacts: the member files (district, party, Capitol/business/home/cell phones,
  room, committees with "C" chair and "V" vice chair); emails are user names, completed with "@house.ms.gov" /
  "@senate.ms.gov", the domains the Legislature's own stylesheets add (members/dtds_xslts/house.xslt and senate.xslt,
  checked 2026-11-08). Sen. Chris Johnson is in District 44 (moved to 45 by `C.DISTRICT_FIX` until 2026-11-22, when the
  Senate's roster showed the files were stale: below); contacts.py reports any seat claimed twice. Leaders: Speaker
  Jason White; the Lieutenant Governor, Delbert Hosemann, presides over the Senate and refers its bills (not a senator: his
  phone and email from ltgovhosemann.ms.gov, checked by program 2026-11-08). The governor's phone and email are from
  governorreeves.ms.gov/contact/ (checked by program 2026-11-08, not by the owner). Governor 5 days (Sundays excepted) in
  session; a bill the adjournment keeps from being returned has 15 days, Sundays excepted, from presentment (sec. 72; until
  2026-11-21 the profile gave 15 calendar days from the adjournment); partial vetoes of appropriations; override two-thirds of each house. Earlier years linked
  by identical short title and principal author (or a title one bill had in each year), never laws or appropriations.
  Places (`towns.py`, run once): cities, towns, villages and counties, separate Senate (52) and House (122) districts, from
  the Census Bureau's 2024 files, which predate the districts redrawn for the November 2025 special elections (How's
  "About this data" says so). Totals (laws: each bill with a chapter number; chapters run 1-N, 301-N, 901-N (local and
  private) and 2001-N (resolutions) with none missing on the measures read, except 2025's 450, 455 and 2040; vetoes
  matching the news): 2024 409 laws, 6 vetoes (HB 922, SB 2180, four suffrage bills), part vetoes on HB 1707 and HB 1830;
  2025 259 laws, 8 vetoes (no part vetoes in the regular session); 2026 376 laws, 6 vetoes (HB 895, HB 1152, HB 1648,
  SB 2477, SB 2632, SB 3402; none overridden), part vetoes on HB 1653, HB 1924, SB 2189, SB 3071. No constitutional
  amendment passed both houses in 2024-26. A first copy of three years takes about 4 hours (230 minutes on 2026-11-08).

- **Veto messages (2026-11-22):** a vetoed bill's history file links the governor's message (<VETOMSG><VETO_OTHER>
  /documents/<year>/html/veto/HB0895.htm, a Word page; no robots.txt). fetch.py's `veto_messages()` reads each once into
  data/ms/<year>/vetoes/; convert.py's `veto_message()` keeps the paragraphs after "GOVERNOR'S VETO MESSAGE FOR ..." up to
  the signature, joins paragraphs the page breaks mid-sentence, and drops the bill's long title quoted in full ("I am
  returning House Bill 895: "AN ACT TO AMEND ... FOR RELATED PURPOSES."" -> "I am returning House Bill 895."). Suffrage
  bills' vetoes come as a notice with no reasons ("MESSAGE FROM THE GOVERNOR ... has vetoed the following Senate Bill":
  SB 3402 of 2026): left out. Read 2026-11-22: 22 messages, 2024: 2 of 6 vetoes (the others have no link), 2025: 8 of 8,
  2026: 5 of 6, plus line-item vetoes on laws. Shows after the next download.
- **Committee agendas (2026-11-22): Senate only.** `agendas()` in states/ms/fetch.py (every run, two requests) reads
  www.legislature.ms.gov/calendars-and-schedules/senate-committee-agenda/ for the PDF it links (one file the Senate keeps
  rewriting, "CURRENT Committee Agendas, Updated: ..."; its name keeps an older year's, 2025_SENATE_COMMITTEE_AGENDAS.pdf
  in 2026), runs `pdftotext -layout` and reads each day line ("Tuesday, February 4, 2025"), each meeting line (a time,
  "AR" or "After" in the left column, "Judiciary, Division A Committee" in the right) and the bills under it ("S. B. No.
  2328: ...", "H. B. No. 1095", "S. C. R. No. 5"; nominations, "S. N. No.", aren't bills), yesterday to three weeks ahead,
  canceled meetings left out, into data/ms/<this year>/agendas.json, `{"SB2328": [["Senate Judiciary, Division A",
  "2025-02-04T08:30:00"]]}`; `agendas()` in convert.py keeps today's and later. It needs pdftotext (poppler-utils) on the
  runner: without it the last file is kept. The House posts no agendas: its committee schedule
  (billstatus.ls.state.ms.us/htms/h_sched.htm, also the Senate's s_sched.htm) gives only times and rooms. Agendas are
  posted a day or two ahead. Neither host has a robots.txt (404). Tested 2026-11-22 against two copies of the PDF from
  the Internet Archive (February 4 and March 12, 2025: 15 meetings, 73 bills, all matching records); the live file is
  an interim hearing's (presenters and topics, no meeting lines: nothing read). The Archive's February and March 2026
  copies held only the heading ("Updated: February 3, 2026"), so whether the Senate kept it up in 2026 is unknown:
  check in January 2027. Untested live.
- **House committee meetings ("committee meets", 2026-11-22).** The House publishes when its committees meet but not
  which bills they'll take up. `house_schedule()` in fetch.py (every run, one request; billstatus.ls.state.ms.us has no
  robots.txt, checked again 2026-11-22) reads /htms/h_sched.htm (one page, rewritten as meetings are set: a day line
  "TUESDAY, DECEMBER 08, 2026", then rows of time, room and committee, with "Standing Meeting", "Full Committee" or
  "Subcommittee 1" under the name) into data/ms/<this year>/house_meetings.json, `[["Judiciary A", "2027-01-20T10:00:00",
  ""], ["Rules", "2027-01-21T00:00:00", "after the House adjourns"]]`: yesterday to three weeks ahead; "WNM" (won't meet)
  and subcommittees left out; times written "AA+05" (after adjournment), "AR", "BC" are T00:00:00 with a note.
  `agendas()` in convert.py gives each meeting in the session's year to every bill now in that House committee that
  hasn't died (`_IN_COMM`, filled by load_session(); names matched by `comm_key()`: "Judiciary, Division A" = "Judiciary
  A"), as `["House Judiciary A", when, "meets"(, note)]`. The page keeps them apart from real agendas: the row tag says
  "House Judiciary A meets Tue, Jan 20" (outlined), the panel "The House Judiciary A Committee meets Tue, Jan 20, 10:00 AM;
  this bill could come up.", the pipeline has its own line, "Committee meets soon", and they're not in "On an upcoming
  committee agenda" or a legislator's "Coming up in committee"; on the watchlist the deadline reads "Committee meets
  Jan 20". The How page's "About this data" says the House doesn't publish which bills its committees will consider.
  Tested on the live page (one interim meeting, Management, December 8, 2026) and Internet Archive copies from 2025 (the
  page's present layout; 2024's plain-text layout isn't read): January 23, 2025 gave 3 meetings (two "will not meet"
  left out) and, with 2025's bills in committee, 189 bills; March 31, 2025, 2 meetings, 41 bills. January check: the
  log's "house schedule: N House committee meetings", and that names match (a schedule name no bill's committee matches
  simply attaches to nothing).
- This year's session (or next year's) is shown from its first bill history (`sessions()` in convert.py, 2026-11-22;
  older ones need more than 100); 2027's allmsrs.xml answered 404 on 2026-11-22.
- **Floor votes member by member (2026-11-22).** Each decisive floor action in a history file (Passed, Failed, Concurred,
  Conference Report Adopted/Failed, Veto Overridden/Sustained) links its roll call in ACT_VOTE, one PDF per vote
  (/<year>/pdf/votes/house/0030003.pdf: legislative day and sequence; text, posted the day of the vote; no robots.txt).
  fetch.py's `roll_calls()` reads each once with pdftotext into data/ms/<year>/rollcalls.json (the text up to the
  disclaimer), at most 900 a run, the newest year first; a 404 is asked again after a week (HB 1653 of 2026's "Veto Referred
  To" line links one that doesn't exist). About 1,400-1,750 decisive votes a year (4,713 linked in 2024-26 on 2026-11-08),
  so a first copy takes several runs; nothing waits on it. convert.py's `roll_vote()` checks the PDF names the same bill
  ("H. B. No. 1", "H.B. No. 1924", "S. C. R. No. 501") and house, takes the totals ("Yeas--... Total--116.", "Nays--None.",
  "Nays-0", "Absent or those not voting--", the Senate's "Absent and those not voting----None.", "Voting Present--" or
  "Present--"), and names members only when every group's names add up to its total, or the yeas and nays do and every
  seat is named once with the "Vacancies--1" (HB 1924 of 2026's override: seven absent names under "Total--5", 110 + 0 + 5
  + 7 = 122). Senators who "announced a pair" are in no group: listed as absent. Names: the short name, which is the
  author page's slug ("Anderson (110th)" = anderson_(110th)), or surname, initials and the district where two share it
  ("Simmons D. T. (12th)" = simmons_(12th)); "Mr. Speaker" is that year's Speaker (`SPEAKERS`); a name is tied to a current
  member's seat only when that year's author list has the slug under the same person (surname from the slug, as the
  short name can be misspelled, "Butler-Washinton"; the first initial or a given name in common, "Chuck"/"Charles
  Younger", "Briggs"/"W. Briggs Hopson III"). Tested 2026-11-22 on 49 roll calls of 12 bills (2024-26): all parsed, all
  added up (one by the seat count), none under another bill; non-yes names not tied to a seat were former members (Horhn,
  Branning, Jordan) and the members below.
- **The member files are out of date (found and corrected 2026-11-22).** ss_membs.xml (Last-Modified 2025-07-01,
  before the November 2025 special elections in the redrawn districts) and hr_membs.xml (2025-10-14) list Sens. David
  Parker (2), John Polk (44), Robin Robinson (42) and Reps. Jonathan Lancaster (22), Orlando Paden (26), who aren't in
  2026's author lists; those lists have Sens. Johnny DuPree, Theresa Gillespie Isom, Kamesha Mumford, Don Hartness,
  Justin Pope and Reps. Justin Crosby, Otha Williams, who had no member file but vote in 2026's roll calls ("S?Hartness").
  Confirmed against the chambers' own rosters: billstatus.ls.state.ms.us/members/s_roster.pdf (the page
  legislature.ms.gov/legislators/senate-roster/ shows; Last-Modified 2026-11-17, text) and h_roster.pdf (a scan dated
  July 7, 2026; read here by eye and OCR, not by the program). They also show Sens. Jeff Tate (33) and Juan Barnett (34)
  gone ("Vacant") and Reps. Bo Brown (70) and Price Wallace (77) not on the House's list (both authored 2026 bills).
  legislature.ms.gov has no robots.txt; its member pages (/legislators/senators/) are an iframe of /member/?chamber=S,
  which answered 500 to the site's requests. convert.py's `FORMER` drops those nine; `ADDED` gives the seven new members
  as the rosters do (district, party, email, Capitol phone and room, counties, the Senate's committees; the House roster
  lists no committees, and no phone or room for Crosby and Williams), used only while no member file has the slug.
  `current_members()` also reads only the files the lists link (a file a list drops stays on disk). fetch.py saves the
  Senate roster's text weekly (members/s_roster.txt) and contacts.py prints "Senate roster disagrees: ..." for any
  district where it and the seats differ (none on 2026-11-22: 50 senators, 120 representatives). The House roster is a
  scan: check it by hand after elections (h_roster.pdf's Last-Modified). The Census district files (towns.py) still
  predate the 2025 maps. data_check's "names voting in the last four months ... aren't tied to a seat" LOOK now lists
  the four who left after the 2026 session.
- **Leads from bill texts: measured, not used (2026-11-22).** The shared extractor (states/billtext_lead.py) read 250
  bills of 2026 as introduced (billstatus.ls.state.ms.us/documents/2026/html/..IN.htm, a new section's mark underlined) and
  gave a lead for 208; a hand check of 20: 15 local appropriations that only add the dollar amount to the long title, 3
  more informative, and 2 misleading (SC 504 and SB 3328 quote sections of existing law the bill restates in full, as if
  new). The long title, already the summary, says what these leads say; the reader stays out of fetch.py.
