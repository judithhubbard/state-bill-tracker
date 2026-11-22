# Kansas

Moved from CLAUDE.md (2026-11-19). Shared conventions, the data traps list and the site's code notes stay there.

- **Kansas (built 2026-11-13):** `python3 states/ks/fetch.py` reads the
  Legislature's API (kslegislature.gov/api/v1; see its docstring) into data/ks/<first year>/; `python3 states/ks/contacts.py`
  (every run; add it to states.json's run after fetch.py) builds the contacts; `states/ks/towns.py` was run once. A page per
  biennium (`YEARS = 2`; "b2025_26"): each year's session opens the second Monday of January, runs to first adjournment in
  late March or early April, and comes back for the veto session in late April; `STATE.dated` holds each year's first
  adjournment, veto session and last day (from the roll calls' journal days; add each new year's), `STATE.days()` estimates
  a year not listed. House and Senate bills, plus the concurrent resolutions proposing constitutional amendments (long title
  "A PROPOSITION to amend ...": two-thirds of each house's members, then the voters; "Enrolled and presented to Secretary of
  State", never the governor; tagged "const", stage 3: HCR 5004 and SCR 1611 of 2025-26 passed; SCR 1611 named the August 4, 2026 primary:
  `STATE.ballotDates`). Other HCRs/SCRs (Article V
  convention applications, joint rules) and HRs/SRs are left out; their STATUS says "Approved by Governor" though they never
  go to the governor (trap: the status field). `states/ks/convert.py` reads each history line's wording (the action codes
  don't always mean one thing: fa_fabc_925 is "Adopted as amended by required 2/3 Majority", efa_fabc_925 "Substitute
  passed"), sorted by day (the date in the wording when it has one: "Enrolled and presented to Governor on Monday, March 30,
  2026" is entered days later; hearings by the hearing's day once it's past; "Died in Committee" by the journal day, the
  biennium's last). Steps: referral; "Withdrawn from X; Referred to Y" (the API often names Y twice: the referral decides),
  "Withdrawn from Calendar; Referred to ..." (back to committee), "Withdrawn from and referred to Committee of the Whole"
  (to the floor); "Committee Report recommending bill be passed [as amended | and placed on Consent Calendar] by" (no
  committee named: the one it's in) = reported; the Committee of the Whole's "Be passed" on General Orders is a voice
  recommendation, not the passage; "Final Action - Passed [as amended]" (a later day) or "Emergency Final Action - ..." (the
  same day, after "Motion to advance to Emergency Final Action adopted", which the Senate's lines give only as the code
  fa_fabc_912), or "Consent Calendar Passed", is the passage; "Final Action - Not passed" fails. The second house passing it
  "as amended" or as a substitute needs "Concurred with amendments [in conference]" or both houses' "Conference Committee
  Report was adopted" ("agree to disagree" / "not adopted" start over; "Motion to not adopt ... (Bill is killed)"). Lines
  carrying only their code: ccal_rcc_820/850, ccal_faccl_850 (days on the consent calendar), ref_rbc_236/237 and
  cow_jcow_292 (left out); "#ACTION_CODES_UNKNOWN#" (SB 28 of 2024, HB 2106, SB 125, SB 367 of 2025-26, House resolutions)
  has no wording at all and sits among the Committee of the Whole's or a line-item override's steps: left out. Empty lines
  (misc_bs_100) are motions, worded from their roll call's motion when one has one. Governor: "Approved by Governor",
  "... except line item veto of 35a, ..." (a law, `itemVeto`), "Will become law without Governor's signature", "Vetoed by
  Governor", "Motion to override veto prevailed" in each house (both needed), line items overridden one group at a time.
  Laws and vetoes match the API's governor's-actions list bill for bill (`python3 -m states.ks.convert`): 2023 98 laws, 17
  vetoes (8 overridden, 9 stand); 2024 111 laws, 21 vetoes (7 overridden, 14 stand); 2025 129 laws, 19 vetoes, 14 overridden, 5 stand (KHI's and Foulston's
  count); 2026 157 laws, 34 vetoes, 20 overridden, 14 stand. No chapter numbers in the data (laws show no chapter). Votes:
  every roll call on the bill itself (final action, consent calendar, concurrence, conference reports, overrides; not
  amendments, motions or appointments) from votes.json, tied to the bill whose history line has the same action code, house
  and second (several bills' final actions share a minute; trap: a roll call's own bill_no can be wrong or missing: two 2026 Senate line-item override votes on HB 2513
  say HB 2315, a bill never out of committee; HB 2551's House vote of March 14, 2024 has none), dated by that line's journal
  day (after-midnight votes belong to the day before). Members' votes by kpid from votes/<file>.json where downloaded (2025-26:
  317 of 1,342 on 2026-11-13; 2023-24 none yet), else tallies alone (shown as everyone voting yes, as in IL and MO). 2 of
  1,518 passages have no roll call in the list (SB 157 and SB 315 of 2025-26). Seats "S:12", "H:71" (separate maps, 40 and 125):
  the biennium's "Active" members, plus a member who left and voted whose seat stayed empty (Dan Goddard, H:7). Sponsors are
  "Senator Titus" / "Representative Carpenter" or committees (most bills): a surname two members share is resolved by the
  member's page's sponsored bills (current biennium only), else left as the surname (Ruiz, Miller, Smith, Williams in
  2023-24). "What it does" is the Legislative Research Department's supplemental note on the latest version
  (notes/<bill>.json): the Brief, then "Background: ...", headings joined to their paragraph, keywords and footnote dropped
  (2025-26: 552 bills; 2023-24 not downloaded yet). Trap: a conference report often replaces a bill's contents with other
  bills' (HB 2043 of 2025-26: an insurance bill as passed, a property tax law after conference), and the note describes the
  bill before it: after a conference report, a note sharing under a fifth of the final titles' words is dropped (41), the
  rest are labelled as describing the bill before the conference report (109). Titles are the short titles ("Senate Substitute for HB 2004 by Committee
  on ... - ." stripped); the summary is the long title without "AN ACT" and the "amending ... repealing" list. Topics from the
  committees that reported it and each house's last committee (`COMMITTEE_TOPICS`), and title, summary and the note's
  keywords (agency names like "Department of Health and Environment" taken out first). Earlier biennium linked by the same
  short title (six words or more) and first sponsor, never laws. Contacts: members' pages (Topeka office room and phone, home
  phone, email; Amyx and Woodard share the minority leaders' line), committees with chairs, vice chairs and meeting times;
  a past biennium's have emails only. Leaders: Speaker Daniel Hawkins, President Ty Masterson (`LEADERS`; the House elected
  in November 2026 organizes in January 2027). Governor Laura Kelly (D, since January 14, 2019), term-limited: a new governor
  takes office January 11, 2027: add them to `GOVERNORS` and legislatures.json. 10 calendar days, else law without signature
  (no pocket veto); line items on appropriations; override two-thirds of the members (27, 84). governor.ks.gov answers
  automated requests with 403: the phone (785) 296-3232 and address are from general knowledge, unchecked. Places
  (`towns.py`): cities, Census-designated places and counties, separate Senate and House lists.

- **Committee agendas (2026-11-22):** `agendas()` in states/ks/fetch.py reads the API's hearings list
  (`/api/v1/hearings/?biennium=b2027_28&from=<yesterday>&to=<3 weeks ahead>`, JSON, one or two requests a run; built from
  the journal's "Hearing: Tuesday, February 11, 2025, 9:30 AM — Room 548-S" lines, misc_he_200) into
  data/ks/<first year>/agendas.json, `{"HB2001": [["House Education", "2027-01-20T13:30:00"], ...]}` (canceled hearings
  left out; "Senate Select Committee on Veterans Affairs" keeps its own name); `agendas()` in convert.py keeps today's and
  later. Hearings are posted 1 to 9 days ahead (mostly 5-7; 2025-26's history lines). Only bills scheduled for a hearing
  are listed: committees' "final action" (working) meetings aren't in the journal as hearings. Tested 2026-11-22 against
  February 2026's hearings (234 bills on 161 hearings, 233 matching records; HCR 5022, a resolution, isn't kept); between
  sessions the list is empty. A failed read keeps the last file.
- **The next biennium (2026-11-22):** from November 1 (and through January, while the API's /biennia/ doesn't list it), fetch.py asks /api/v1/bill_status/?biennium=b2027_28 for one bill each run (`waiting()`: 0 on 2026-11-22) and reads the biennium like the active one once it lists a bill (prefiled bills, if the API lists them before the session opens January 11, 2027); a biennium with no bills on file is never saved and never holds Kansas back, nor do a new Legislature's member details in its first January. contacts.py writes no contacts for a biennium with fewer than 150 members and no contacts file yet (the page builds without legislators until the API lists them).
