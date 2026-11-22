# North Dakota

Moved from CLAUDE.md (2026-11-19). Shared conventions, the data traps list and the site's code notes stay there.

- **North Dakota (built 2026-11-08):** `python3
  states/nd/fetch.py` reads the Legislative Council's static JSON API (see its docstring) into data/nd/<first year>/, a
  two-year Legislative Assembly a page (the 69th is 2025-26; `YEARS = 2`), though the regular session meets only in the odd
  year (early January, 80 legislative days, to about May: `STATE.dated` holds each session's last floor day, add each new
  one); `python3 states/nd/contacts.py` (every assembly; add it to states.json's run) builds the contacts. Special sessions
  (October 2023; January and September 2026) are in the assembly's own files, numbered after the regular session's (HB 1621
  on), so they're shown with the rest, as Alaska's. `states/nd/convert.py` reads the categorized actions: "Introduced, first
  reading, referred X Committee"; "Rereferred to Appropriations"; "Request return from committee" (the house takes it back:
  to the floor, another committee, or to withdraw it); committee reports "Reported back (amended), do pass / do not pass /
  without recommendation ... 13 0 1" (a tally: yes, no, absent; no names). Every report goes to the floor, "do not pass" too:
  committees can't hold bills, so the only stage-0 bills in a finished session are withdrawn ones (`heldAction`
  "Withdrawn", commFate "held"); "do pass" is "REPORTED" (approved), "do not pass" commFate "defeated". About nine in ten
  bills recommended against fail on the floor, and nine in ten recommended pass. "Second reading, passed/adopted ..., yeas N
  nays N" is the passage (resolutions "adopted"); "failed to pass" ends the bill unless "Reconsidered" (stage 1, "Failed on
  the floor"); a bill voted on in parts fails when every part lost on final passage (SB 2384 of 2025). Passed both houses:
  the second house passed it unchanged ("Returned to House" with no "(12)"), the first concurred and passed it again, or both
  adopted a conference report and passed it again; the presiding officers' signatures or "Sent to Governor" otherwise. Laws:
  "Signed by Governor 04/28" (the line's own date), "Signed by Governor, but item veto", "Passed over veto" in both houses,
  or filed with the Secretary of State without a veto; "Veto sustained". Chapter numbers come from chapters.json (the
  Session Laws' bill index); vetoed measures get chapter numbers too ("Measure Vetoed"), so the history decides. SB 2015 of
  2023 (signed) was later declared void by the Supreme Court (2023 ND 185): kept as a law with that line. Floor roll calls
  member by member ("Final Passage"; a passage line without a roll-call id is matched to one by bill, day and tally); seats
  "S:12", "H:12a"/"H:12b" by name within the district (`seats()`, shared with contacts.py; subdistricts 4A/4B are "H:4a"/
  "H:4b"); members who left are "H?O'Brien". Titles: there are no short titles, so `titled()` takes the official title's
  first "relating to" subject, "Budget: <agency>" for an agency's appropriation, "Appropriation to ..." or "Study: ..."; the
  summary is the official title. "What it does" is the Legislative Council's Title Summaries (a PDF per session, "Summary
  of Bills Enacted by the 2023 Legislative Assembly", listed on /research-and-archives/title-summaries months after the
  session; fetch.py reads it with pdftotext, weekly, and never marks the state incomplete): a paragraph on each bill
  passed (laws and vetoed bills, "would have ..."), labelled "From the Legislative Council's summary of the bill as
  passed."; 2023: 515 bills (510 of 599 laws; budget bills only for the parts that change other laws); 2025's edition
  wasn't listed yet in November 2026 and is picked up when it is. Nothing else per bill exists (statements of purpose of
  amendment are budget tables), so bills that didn't pass have none. Topics from
  committees (`COMMITTEE_TOPICS`) and words in the title and subjects. Concurrent resolutions amending the Constitution of
  North Dakota are tagged "const" (one passage by a majority of each house's members, then the voters at the election the
  resolution names: `amendmentOnce`, `ballotLine()`); other resolutions are left out. Earlier assembly linked by title,
  or same prime sponsor with half the title words shared, never to a law (`earlier()`). Hearings come from each bill's
  Hearings (named committee); `agendas()` lists upcoming ones. Governor 3 legislative days in session (taken as weekdays), 15
  days, Saturdays and Sundays excepted, from delivery after adjournment (Art. V, sec. 9; until 2026-11-21 the profile
  excepted only Sundays and gave 15 calendar days from adjournment); item vetoes on appropriations; override two-thirds of each house's members. Between sessions the current
  page reads like a finished one (`STATE.between()`, a getter for `stageText.live`). Shared hooks added for North Dakota:
  `STATE.oddsExits` (the Statistics chart's first two exits, without the committee breakdown), `STATE.fateLabels`, and
  `STATE.endedNote(b)` (a bill voted down or withdrawn mid-session: its status and "what's next" say so). Contacts: members
  file (party, district), biography pages (phones Cell/Home/Work, each once; email), standing and joint committees with
  chairs, current leadership positions (expired "Effective ... - ..." ones dropped). The governor's phone and contact page
  are from governor.nd.gov's contact page (checked by program 2026-11-08, not by the owner). The 70th assembly (December
  2026) chooses new leaders: update `LEADERS`. Totals, matching the Session Laws' bill index bill for bill: 2023 599 laws
  (585 regular-session bills with chapters, 14 special-session), 7 vetoes (5 sustained, HB 1416 and HB 1463 overridden),
  item vetoes on SB 2015 and HB 1544; 2025-26 608 laws (597 with chapters, 11 special-session), 4 vetoes (HB 1540, SB 2160,
  SB 2261, SB 2307; all sustained), item vetoes on 6 budgets. Places (`towns.py`, run once): cities, Census-designated
  places and counties, one district list for both houses.
- **The next session's bills (checked 2026-11-22):** `fetch.py` reads every assembly assemblies.json lists, and an assembly listed with no bills file yet (a 404) is noted absent, without a folder; the 70th (2027) wasn't listed on 2026-11-22. Its prefiled bills appear from the organizational session in December; before it convenes (`begun()`) nothing of it holds North Dakota off the site.
