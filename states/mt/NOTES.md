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
  two-thirds of each house's members (legislatures.json "2/3"). No "What it does": the data has only short titles (the
  summary is empty). Titles are the short titles. Topics from the Legislative Services Division's subject codes
  (`SUBJECT_TOPICS`) and title words. Earlier sessions linked by short title (same prime sponsor, or one bill each), or
  the same prime sponsor with 60% of the title's words; never laws or appropriations. Bill links: the Bill Explorer,
  bills.legmt.gov/#/laws/bill/<session id>/<LC number> (2025) and /#/bill/20231/<LC number> (the archive; read from the
  site's own script, not checked in a browser). Contacts: emails from the member list; phones from Open States (about a
  third) plus the session message line (406) 444-4800 for all (not checked by the owner); committees with chairs and vice
  chairs. Leaders: Speaker Brandon Ler, Senate President Matt Regier (`LEADERS`); the 70th Legislature organizes in January
  2027. The governor's phone and contact page are from gov.mt.gov/contact (checked by program 2026-11-09, not by the owner).
  Places (`towns.py`, run once): cities, towns, Census-designated places and counties, separate Senate (50) and House
  (100) lists (Senate District n is House Districts 2n-1 and 2n).
- **Veto letters (looked into 2026-11-22; not read):** api.legmt.gov's documents/v1/documents/getBillOther lists each vetoed bill's "VetoLetter" (and the override poll, "PollingResult") with a docs.legmt.gov download-ticket link, but the letters are scans with no text layer (HB 182 of 2025). They need OCR, the owner's decision; at the crawl delay of 10 s, two requests a veto.
