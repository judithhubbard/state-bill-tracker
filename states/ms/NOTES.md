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
  each house" when VOTETYPE says so; no "What it does" (there are no summaries). No votes: roll calls are PDFs, and the
  history lines carry no tallies. Local and private bills (the Local and Private Legislation committees) are narrow kind
  "place" and topic "local"; "Suffrage; restore to <a person>" bills (20-70 a year) are narrow kind "person". Authors by their author-page slug ("creekmore_iv"), named from the current member files, else
  that year's h_auth.xml / s_auth.xml. Contacts: the member files (district, party, Capitol/business/home/cell phones,
  room, committees with "C" chair and "V" vice chair); emails are user names, completed with "@house.ms.gov" /
  "@senate.ms.gov", the domains the Legislature's own stylesheets add (members/dtds_xslts/house.xslt and senate.xslt,
  checked 2026-11-08). Sen. Chris Johnson's file says District 44 (Polk's); his counties put him in 45
  (`C.DISTRICT_FIX`); contacts.py reports any seat claimed twice. Senate Districts 24 and 26 are vacant (November 2026). Leaders: Speaker
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
