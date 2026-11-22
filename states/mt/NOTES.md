# Montana

Moved from CLAUDE.md (2026-11-19). Shared conventions, the data traps list and the site's code notes stay there.

- **Montana (built 2026-11-09):** `python3 states/mt/fetch.py` reads the Legislature's API (api.legmt.gov, the one the
  Bill Explorer uses; Crawl-delay 10; see its docstring) into data/mt/<year>/; `python3 states/mt/contacts.py` (every
  session; add it to states.json's run after fetch.py) builds the contacts. A page per two-year Legislature named by its
  session's year (`YEARS = 2`, label "2025"): the Legislature meets in regular session only in odd years, from the first
  Monday of January (January 2 when that's New Year's Day), 90 legislative days; `STATE.dated` holds each session's last
  day (add each new one). Special sessions and joint resolutions (HJ/SJ: studies, letters) are left out. Two formats:
  2025 on from the current system (status names "(H) 3rd Reading" with a result enum, member-by-member floor votes,
  committee "executive actions" member by member, co-sponsors), 2023 from the archive (plain-English actions newest
  first, "(S) 3rd Reading Concurred", tallies only, sponsors by law-entity id); `states/mt/convert.py` reads both into one
  list of steps (`steps_current()`, `steps_archive()`). Committees hear every bill and vote "do pass" ("be concurred in"
  in the second house) or table it (`heldAction` "Tabled in committee": most bills that die); "Take from Committee; Place
  on 2nd Reading" is a blast motion; second reading is the floor's real vote (amend, pass, "indefinitely postponed"),
  third reading the passage; "Missed Deadline for General Bill Transmittal" (and revenue, appropriation, referendum)
  ends a bill (`STATE.endedNote()` words floor defeats and missed deadlines). Passed both houses: "Returned to House"
  (unamended), the first house concurring on third reading, a conference report adopted on third reading by both, or
  enrollment; "Returned with Governor's Amendments" (amendatory veto) takes it back from the governor until it's
  transmitted again. Two traps in the current system's results: a committee report's result is often
  "BILL_NOT_CONCURRED_AS_AMENDED" after the committee voted "be concurred in as amended" (reports are only of approved
  bills: ignored), and some failed floor votes are marked passed ("BILL_CONCURRED" on HB 93 of 2025's 24-26 third
  reading; ties 25-25 and 50-50): with a roll call, a motion for the bill carries only with more ayes than noes, and a
  "Do Not Concur" motion decides by its own tally (`decide()` in `record()`); "Do Not ..." roll calls aren't listed as
  members' votes. A few committee records have no members' votes (dropped). The member list keeps one record per member
  overwritten with their latest house and district (13 members in 2025: House members since elected to the Senate show
  as senators, two senators as House members): the house comes from the roll calls and `P.SEAT_FIX` (checked against
  Open States 2026-11-09); members who left (Mercer, Stafman, Bertoglio, Marshall) are "H?Mercer" in votes. Laws are
  decided by the chapter number (`sessionLawChapterNumber`; "Chapter 479", `STATE.lawWord` "Chapter"), which runs 1-N
  with none missing or repeated: 2023 783 laws, 25 vetoes of which 4 overridden by mail poll (HB 29, HB 693, HB 868,
  SB 4), so 21 stand, and HB 5's line-item vetoes; 2025 778 laws, 45 vetoes (the news's count), 2 overridden by mail
  poll (HB 368, HB 643), 43 stand, line-item vetoes on HB 2. Laws without the governor's signature (about 7 a session)
  show only "Transmitted to Governor" and a chapter. Constitutional amendments are bills with the subject CAP, tagged
  "const": two-thirds of all 150 legislators (100 votes, both houses counted together), then the voters at the next
  general election (`amendmentOnce`, `ballotLine()`); "3rd Reading; 2nd Chamber Vote Required" is a house's vote short of
  two-thirds, and one that passed each house without reaching 100 (HB 372 and HB 517 of 2023) dies there; none passed in
  2023 or 2025. Governor (Greg Gianforte, R) 10 days after delivery, in or out of session (Constitution Art. VI, sec. 10,
  as amended: no Sundays rule and no 25-day rule any more); bills reach the governor weeks after the session
  (`passedBothBy` is 60 days after it); vetoes after adjournment are overridden by the Secretary of State's mail poll,
  two-thirds of each house's members (legislatures.json "2/3"). The data has only short titles (the summary is empty);
  "What it does" is the bill's full title (below, 2026-11-22). Titles are the short titles. Topics from the Legislative Services Division's subject codes
  (`SUBJECT_TOPICS`) and title words. Earlier sessions linked by short title (same prime sponsor, or one bill each), or
  the same prime sponsor with 60% of the title's words; never laws or appropriations. Bill links: the Bill Explorer,
  bills.legmt.gov/#/laws/bill/<session id>/<LC number> (2025) and /#/bill/20231/<LC number> (the archive; read from the
  site's own script, not checked in a browser). Contacts: emails from the member list; phones from Open States (about a
  third) plus the session message line (406) 444-4800 for all (not checked by the owner); committees with chairs and vice
  chairs. Leaders: Speaker Brandon Ler, Senate President Matt Regier (`LEADERS`); the 70th Legislature organizes in January
  2027. The governor's phone and contact page are from gov.mt.gov/contact (checked by program 2026-11-09, not by the owner).
  Places (`towns.py`, run once): cities, towns, Census-designated places and counties, separate Senate (50) and House
  (100) lists (Senate District n is House Districts 2n-1 and 2n).
- **Veto letters (2026-11-22, read by OCR, the owner's decision):** `veto_letters()` in fetch.py asks, for each bill whose
  record mentions a veto (34 in 2023, 58 in 2025: vetoes, line-item vetoes, amendatory vetoes), the Bill Explorer's
  documents list (docs/v1/documents/getBillOther?legislatureOrdinal=69&sessionOrdinal=20251&billType=HB&billNumber=182;
  2023 is legislatureOrdinal 68, sessionOrdinal 20231), takes the letter (DocumentType "VetoLetter"; 2023's have no type,
  so a file name like "HB0033GovVeto.pdf", never the "VetoPoll"; a re-upload "HB0002GovVeto(1).pdf" after the original)
  and reads it once by OCR (states/letters.py's `scanned()`) into <year>/vetoes/<HB182>.json. Two requests a letter at the
  10-second delay, at most 10 minutes a run; a bill listed with no letter (amendatory vetoes have none) is asked again a
  week later (vetoes/asked.json). The link is docs.legmt.gov's download ticket, the one the Bill Explorer links (the same
  ticket each time it's asked). `veto_message()` in convert.py keeps the letter after "Dear Speaker ... and President
  ...:" up to "Sincerely" (`tidy()` drops margin specks read as marks, "They’ ve", the budget's footnote numbers);
  vetoed bills show it, HB 2 (2025) and HB 5 (2023) as line-item vetoes; laws passed over a veto keep it unshown. Quality
  (HB 182 and HB 2 of 2025, HB 33 of 2023, checked against the page image): typed letters, near word-perfect ("officialsk—"
  for "officials—" in HB 33).
- **What it does (2026-11-22): the bill's full title.** No plain summary exists: the Bill Explorer has the short title,
  and fiscal notes ("Description of Proposed Legislation") are scans, on about half the bills (769 of 1,641 flagged in
  2025), and describe cost. The full title the Legislative Services Division's drafters put at the top of every bill
  lists what the act does: "AN ACT CREATING A SENIOR CITIZEN CENTER GRANT PROGRAM ...; PROVIDING AN APPROPRIATION;
  AMENDING SECTIONS ..., MCA; AND PROVIDING AN EFFECTIVE DATE AND A TERMINATION DATE." (HB 182 of 2025; short title
  "Provide grant funding for senior citizen centers"). `titles()` in fetch.py and states/mt/texts.py read each House and
  Senate bill's text, a PDF with a text layer, from the documents service (robots.txt re-read 2026-11-22: api.legmt.gov
  and docs.legmt.gov "User-agent: * / Crawl-delay: 10", nothing disallowed). Only the enrolled text (as passed) or the
  introduced one: amended versions in between show amendments in place, and struck words stay in the text layer (trap:
  a title read from them could keep words taken out). 2025 on, docs/v1/documents/getBillText?legislatureOrdinal=69&
  sessionOrdinal=20251&billType=HB&billNumber=182 (the latest version's PDF itself, one request) for bills never amended
  and for laws and vetoed bills (enrolled: no 'A BILL FOR AN ACT ENTITLED' wrapper); otherwise, and for 2023
  (getBillText answers 404 there), getBillVersions and the "_x" (enrolled) ticket, else "_1", two requests. Labels "From
  the bill's full title as passed by the Legislature." or "... as introduced." The title goes in
  <year>/titles/<HB182>.json with the bill's version (re-read when versionNumber changes); a bill with no text is asked again a week later (titles/asked.json). Laws first, then the bills with the
  longest histories; 15 minutes a run for every session together (TITLE_MINUTES, about 90 texts at the delay); the first
  copy (1,516 bills of 2025, 1,534 of 2023: about 4,000-5,000 requests) takes about 50 runs. texts_<year>.json is written every
  run: the title in sentence case, each word as the bill's own text writes it after a lower-case word ("Montana",
  "Title 75", "June"; Montana's statutes write agencies and courts in lower case, so the titles do too), without the
  lists of sections amended or repealed, effective and applicability dates (a termination date is kept as "providing a
  termination date") and "providing definitions"; introduced bills' 'A BILL FOR AN ACT ENTITLED: "..."' wrapper and line
  numbers are dropped; a budget's long title is cut at a clause after 1,500 characters; a title that then adds fewer
  than two words to the short title is left out. Checked by
  hand on HB 182 and HB 93 of 2025, SB 44 and HB 2 of 2023. Never holds Montana back (a refusal stops the step; errors
  are logged).
