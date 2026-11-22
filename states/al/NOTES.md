# Alabama

Moved from CLAUDE.md (2026-11-19). Shared conventions, the data traps list and the site's code notes stay there.

- **Alabama (built 2026-11-08):** `python3 states/al/fetch.py` reads ALISON's GraphQL endpoint (see its docstring) into
  data/al/<year>/; `python3 states/al/contacts.py` (every year) builds the contacts from members.json and committees.json
  (no web pages). A page a year (`YEARS = 1`): one regular session, 30 legislative days within 105 calendar days, from the
  first Tuesday of February (the second Tuesday of January in an election year, the first Tuesday of March the year
  after: `opens()`); each year's last day is in `STATE.dated` (add each year's). Special sessions are left out.
  `states/al/convert.py` reads the history lines, which within a day aren't in order: sorted by day, then house of origin /
  second house / between the houses and the governor, then step (`kind_of()`'s rank). "Read for the first time and referred
  to the House Committee on X" (the "Pending Committee Action" status lines are dropped); "Reported Out of Committee"
  (committees report favorably or not at all); "Third Reading in House of Origin" with a roll call is the vote on the
  bill's Budget Isolation Resolution (three-fifths, to take it up before the budgets), not the passage; "Motion to Read a
  Third Time and Pass [as Amended] - Adopted Roll Call 59" is the passage (2024's roll-call field sometimes holds the BIR's number: the
  line's own number decides); "Concur In and Adopt" by the first house, "Non-Concur and Appoint Conference Committee" and
  a conference report adopted by both; "Currently Indefinitely Postponed" ends a bill (often its companion passed instead:
  `endedNote()`); "Ready to Enroll"/"Enrolled" passed both houses; "Delivered to Governor"; "Enacted" with the Act number
  (`STATE.lawWord` "Act", chapter = 312 of "2025-312"); "Pocket Veto"; "Pending with Executive Amendment" (the governor's
  proposed amendment). SB 346 of 2026 passed the House and went back to committee with no line saying so: a status
  "Pending Committee Action in X" undoes that house's passage. Constitutional amendments are bills ("(Constitutional
  Amendment)" in the byline, the subject "Constitutional Amendments Statewide", a short title ending "Constitutional
  Amendment", or an official title "Proposing an amendment"): tagged "const", three-fifths of each house's members, then
  the voters (`amendmentOnce`, `ballotLine()`); they get Act numbers and go to the Secretary of State (a few local ones
  are also "Delivered to Governor" and "Enacted"), so they stop at stage 3. Local bills (a county as the subject, "(N &
  P)" in the byline or a local notice, or a local or county legislation committee; not "Statewide" amendments) are narrow
  kind "place": 151, 182 and 187 a year. Roll calls name every member (Y, N, A abstain, P pass: both shown as
  "Abstained"); only the bill's passage, concurrence and conference-report votes are the bill's (BIRs and amendment votes
  are history lines: "Amendment adopted (Orr's motion), 32-0"). Seats "S:12", "H:45" by full name from the member records
  (past members keep their records); Matt Woods moved from House District 13 to Senate District 5 (`P.MOVED`). 2026's House
  roll calls 273-596 count Kristin Nelson (sworn in then) without naming her: `roll_call()` puts back the year's members
  missing from the list when one group is short by exactly that many. 2024's Senate roll call 607 (a BIR) lists senators
  of decades ago; names that don't resolve are dropped when a list is longer than the house. "What it does": the act's
  summary for a law ("From the act's summary."), else the Legislative Services Agency's synopsis of the bill as introduced,
  its "This bill would ..." sentences first (`synopsis_text()`); HB 66 of 2024's summary has a replacement character for an
  apostrophe. Bills first read after they were engrossed (the endpoint gives only the newest text, which has no synopsis)
  get it from their introduced PDF (2026-11-22: fetch.py's `intro_pdfs()`, once a bill, general bills that aren't laws
  with an act summary; 76 such bills in 2026, more in finished years, read as each run's time allows). Checked on HB 1,
  HB 37, HB 97, HB 123 and SB 26 of 2026. Shows after the next download runs. Topics from the Legislature's subjects (`SUBJECT_TOPICS`; a county is "local") and committees. Titles are
  the short titles; the summary is the official "Relating to ..." title. Bill links: ALISON has no page per bill, so the
  newest text PDF, the introduced PDF and the Secretary of State's act page. Earlier years linked by identical short title
  (four words or more), never laws or appropriations. Governor (Kay Ivey, term-limited; a new governor takes office in
  January 2027: add to `GOVERNORS` and legislatures.json) 6 days (Sundays excepted) in session; 10 days after adjournment,
  then a pocket veto; override a majority of each house's members ("majority"). Leaders: Speaker Nathaniel Ledbetter,
  President Pro Tempore Garlan Gudger (the members list also gives Matt Woods that title; dropped); the Legislature elected
  November 2026 organizes in January 2027. Totals (Act-numbered bills, as the data has them): 2024 302 laws and 17
  amendments (Acts on bills; Act numbers up to 453 include joint resolutions, not downloaded), 1 pocket veto (HB 446); 2025
  305 laws and 5 amendments (the governor's office announced 287 bills and 147 resolutions signed: not reconciled); 2026
  366 laws and 34 amendments; SB 240 of 2026 got an executive amendment the Legislature didn't take up before adjourning,
  and died (the news; its history shows only "Delivered to Governor"). A bill still at "Delivered to Governor" 10 days
  after sine die (`P.SESSION_ENDS`, kept with profile.js's `STATE.dated`) is stage 6: "Not signed: died after the session
  (pocket veto)", or "Died: the Legislature didn't act on the governor's amendment" when the history shows the
  amendment; SB 240 gets the first. The governor's site has no veto lists. Separate Senate (35) and House (105)
  districts by city, town or county (`states/al/towns.py`, from the Census Bureau's 2024 district files). Shared change
  made for Alabama: the "reintroduce it in January" ask (`reintroAsk()`) names the month the next session opens
  (`STATE.opens()`, March in 2027), where a state has `opens`.
- **2023 (added by the window 2026-11-16; read 2026-11-21):** ALISON's 2023 history is in its older wording ("Introduced
  and Referred" with the committee in its own field, "Reported Favorably", "Read a Third Time and Pass", "Indefinitely
  Postpone", "Sent to Governor on May 25, 2023 at 12:00 PM", "Assigned Act No. 2023-291.", "Executive Amendment"), which
  the converter had read as other lines: bills that passed one house showed as on its floor (46 failed the "refers them
  to a committee" check). `old_wording()` puts each in the newer wording for a year whose history has "Introduced and
  Referred"; within a day the older lines keep their file order (a "Reconsider" sits between a passage and "Read Again a
  Third Time and Pass"). Its passage lines say "Pass" for lost votes too (SB 181, 11-20): the tally decides. The governor's
  list names HB 58, never out of committee (dropped). Last day June 6, 2023; four local bills delivered June 1 and never
  numbered (HB 411, 449, 506, 508) are pocket vetoes. Totals: 396 laws, 4 pocket vetoes.
- **Committee agendas (2026-11-22):** `agendas()` in states/al/fetch.py (every full run, after the members) asks ALISON's
  GraphQL endpoint for `meetings` from yesterday to 22 days ahead with their `agendaItems` (the query the site's "Today's
  Schedule" page sends; one request) and writes data/al/<year>/agendas.json ({"HB61": [["House Economic Development and
  Tourism", "2026-02-04T14:30:00"]]}); `agendas()` in convert.py keeps meetings from today on. Times come in UTC and are
  saved as Montgomery's (America/Chicago). "Judiciary (Senate)" becomes "Senate Judiciary"; canceled meetings say so in
  the description or location ("CANCELED", "**MEETING CANCELED**", "Cancelled") and are left out; only HB/SB items are
  kept (Rules agendas also list resolutions; "SCF" items are calendars). A meeting's status is "Released" once posted,
  "Closed" after it. Tested by running it as of 2026-03-03 (past meetings come back the same way): 106 meetings, 344
  bills, every key a 2026 record. Not yet seen live in a session. A failed request keeps the last file.
