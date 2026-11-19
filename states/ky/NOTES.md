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
  2 and SB 143; 2026 SB 10), tagged "const", stage 3. Votes are tallies from the history only: members' votes are in each
  bill's vote_history.pdf (not downloaded; linked from the bill, and "About this data" says so). "What it does" is the LRC's
  summary of the enacted version for a law, else of the bill as introduced. Titles: the official "AN ACT relating to X"
  as "X" (amendments "Constitutional amendment: ..."); the summary is the official title. Sponsors in order as "K. Moser"
  (2024's link to the district page: 1-100 House, 101-138 Senate districts): matched to today's members by initial and
  surname ("DJ Johnson", "G. Brown Jr.", "S. Funke Frommeyer"), else kept as written with the linked district (`resolve()`);
  only current members are published, so a past year's contacts are the current members who sponsored that year. Topics
  from committees (`COMMITTEE_TOPICS`) and the first six LRC index headings (`HEADING_TOPICS`; the record writes "And" and
  "and", so they're matched in lower case). Earlier years linked by the same title and prime sponsor, or the same LRC
  summary word for word, one bill in each year, never laws or appropriations. Governor (Andy Beshear, D, term-limited;
  the next takes office in December 2027: add to `GOVERNORS` and legislatures.json) 10 days, Sundays excepted, in and after
  the session (no pocket veto: a bill not returned becomes law); line-item vetoes on appropriations; override a majority of
  each house's members ("majority"; the Republican supermajority overrides most vetoes). The governor's contact page
  (ppc.ky.gov's constituent services form) and main line (502) 564-2611 are from governor.ky.gov's footer (checked by
  program 2026-11-08, not by the owner). Most members list only "LRC: 502-564-8100", the LRC's message line for every member:
  shown as "Capitol (LRC message line)", after a member's own home or work number. Leaders from the member list (Speaker
  David W. Osborne; Senate President Robert Stivers, a senator); the General Assembly elected in November 2026 organizes in
  January 2027. Separate Senate (38) and House (100) districts by city or county (`states/ky/towns.py`, from the Census
  Bureau's 2024 district files).
