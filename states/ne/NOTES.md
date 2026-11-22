# Nebraska

Moved from CLAUDE.md (2026-11-19). Shared conventions, the data traps list and the site's code notes stay there.

- **Nebraska (built 2026-11-13):** `python3 states/ne/fetch.py` reads
  nebraskalegislature.gov's pages (see its docstring; Crawl-delay 3) into data/ne/<first year>/; `python3
  states/ne/contacts.py` (add it to states.json's run after fetch.py) builds the contacts; `states/ne/towns.py` was run once.
  A page per two-year Legislature (`YEARS = 2`; the 109th is 2025-26): a 90-day session in the odd year (to early June) and a
  60-day one in the even year (to mid-April), each from the first Wednesday after the first Monday of January; bills carry
  over, and every bill still pending on the second session's last day is indefinitely postponed (`P.LAST_DAY` and
  `STATE.dated` hold each session's last day: add each new one). **One house:** the shared code's houses are one letter,
  "L" (`P.LOWER`, bills "LB 7", seats "L:12", "Sen."), `STATE.houses = { L: "Legislature" }`; tracker.html's `UNI` (one
  entry in `STATE.houses`) leaves out stage 2 ("passed one house": never used), the pipeline row, the second chamber in
  progress filters, the odds chart's step (`L3`), the month row, persistence and person-stats rows, the house choices in
  "Who works on what/with whom", the committees' second column, and words "Passed both houses" as `STATE.passedBothText`
  ("Passed the Legislature", `PASSED_BOTH`). A passed bill carries `passedS` and `passedA` both (data_check's "both houses"
  test). **Nonpartisan:** no party anywhere (contacts' party is empty; `C.parties()` is {}); `STATE.nonpartisan` (`NOPARTY`)
  hides the party filter, the party statistics and keys; states/legislatures.json `"nonpartisan": true` makes balance.py
  count members as "N" with no majority ("Legislature: nonpartisan" and the note in the header) and front_page.py give a
  neutral ring (home.html `.dot.N`, legend "Nonpartisan"). The governor is partisan (Jim Pillen, R). `states/ne/convert.py`
  reads each bill's history (oldest first after reversing the page): referral; "Notice of hearing" (every bill is heard);
  "Placed on General File [with AM..]" = the committee advanced it; General File, Select File and Final Reading are the
  three floor rounds (`statusDesc` "On the floor (Select File)"); "Passed on Final Reading 47-0-2" the passage ("with
  Emergency Clause" needs 33); "Presented to Governor on ...", "Approved by Governor [with line-item veto] on ...", "Returned
  by Governor without approval" (veto), "Became law without Governor's signature", "Failed to become law notwithstanding the
  objections ..." (override failed; 30 votes). Governor's lines are listed days late: their own wording dates them. Numbered
  motions ("Hunt MO506 Bracket until ... filed", then "MO506 prevailed") are read by their filed description: bracket and
  indefinite postponement kill, recommit sends back, cloture (33 votes) ends a filibuster; amendments' filed/withdrawn lines
  are dropped, adopted/lost kept. "Indefinitely postponed" on the Legislature's last day is "Died when the Legislature
  adjourned"; earlier, in committee it's a committee kill, on the floor a floor kill, except that at the end of each first
  session the bills whose text already went into another are postponed in a batch (148 in 2023, 46 in 2025): their line
  says so. "Provisions/portions of LB80 amended into LB814 by AM915" is on both bills: the source gets "Its provisions were
  amended into LB 814 (it became law)" and `STATE.endedNote()` shows "Amended into LB 814"; the host gets one line listing
  them. Priority designations ("Ballard priority bill", committee, "Speaker priority bill", "Speaker Major Proposal") are
  history lines; `STATE.rowTags()` (a shared hook) tags the row "Priority bill". "X name added" lines are the co-sponsors.
  **A bills** ("LB 304A", the appropriation for LB 304) are shown, marked `shell` (left out of the statistics and
  legislators' numbers, tagged "A bill": `STATE.shellTag`, `shellTip`, `shellNote`). Constitutional amendments are "LR 19CA"
  resolutions: three-fifths (30) on Final Reading, then the voters ("Presented to Secretary of State"), tagged "const",
  stage 3 (`amendmentOnce`; 2025's LR 19CA, term limits). Votes: every vote file linked from a bill's own steps, member by
  member: General File and Select File advances, Final Reading, cloture on the bill, override (labelled by round in the
  vote's committee slot; `STATE.voteWhat` names it); amendments' votes left out; roll-call names are surnames ("Cavanaugh,
  J."; a trailing "*" dropped), tied to current senators only (`VOTE_NAME_FIX`: plain "Meyer" is Fred Meyer in 2023-24,
  Glen Meyer in 2025 until Fred Meyer came back in January 2026). Totals match the Clerk's final worksheets bill for bill
  (`python3 -m states.ne.convert`, `checks()`): 108th 250 laws (67 A bills; LB 20 and LB 20A without signature; LB 818
  line-item veto; LB 814, the budget, line-item veto partly overridden), 2 vetoes standing (LB 25, LB 307; the override of
  LB 307 failed 27-20); 109th 364 laws (44 A bills; LB 1237 and LB 1237A without signature), 7 vetoes (LB 287, 319, 839,
  878, 929, 1029, 1256; every override failed), LR 19CA to the voters. Topics from the referral committee
  (`COMMITTEE_TOPICS`) and title words. "What it does" (`states/ne/texts.py`, from PDFs fetch.py's `statements()` saves as text in
  data/ne/<year>/docs/) is the committee statement's "Summary of purpose" when the committee advanced the bill (about 40%
  of bills), with its "Explanation of amendments" as what the committee changed (or as the statement itself when the
  amendment replaced the bill); vote tables, testifier lists and the section-by-section part are dropped. Otherwise it's
  the introducer's statement of intent, labelled as such (kept: the owner's decision 2026-11-14; about 98% of bills have
  one or the other). Committee statements
  are re-read when the bill is placed on General File again; A bills have none. Committee votes (2026-11-22): the same statement's "Roll Call Vote - Final Committee Action" ("Aye: 7 Senators Bosn, DeBoer, ...", "Nay: 1 Senator McKinney", "Absent:", "Present Not Voting:"; senators who share a surname are "Cavanaugh, M.") is the committee's vote to advance the bill, dated by its "Placed on General File" line (`committee_roll()` in convert.py; only bills advanced: committees vote in executive session and publish no vote on bills they hold). Checked on the 14 statements the local copy has; needs only a rebuild. The first copy is about 2,700 PDFs (about
  3 hours at the crawl delay) and never marks the state incomplete; the summary line is the one-line title. Earlier Legislature linked by the same title (six words or more) and
  introducer, never laws or appropriations. Contacts: 49 senators with Capitol room, phone, email, photo; 14 standing
  committees and the Executive Board with chairs and vice chairs (meeting days shortened by `meets()`); Speaker John Arch
  (`LEADERS`; the 110th Legislature elects its own in January 2027). A past Legislature's contacts are current senators who
  introduced bills in it; former senators are names only. Places (`towns.py`): cities, villages, Census-designated places and
  counties with their districts, one list (New Jersey's shape: a district has one senator). The governor's contact page and
  phone ((402) 471-2244) are from governor.nebraska.gov (checked by program 2026-11-13, not by the owner); Pillen ran again
  in November 2026: if a new governor takes office in January 2027, add them to `GOVERNORS` and legislatures.json.
- **Next Legislature (2026-11-22):** Nebraska has no prefiling: the 110th's bills (LB 1 on) come from its first day,
  January 6, 2027. fetch.py starts the new Legislature on January 5 (one search for LB 1 a run until it's there); a
  Legislature with LB 1 looked up and not found yet doesn't hold the state back, and convert.py's `sessions()` shows it
  from its first bill page.
