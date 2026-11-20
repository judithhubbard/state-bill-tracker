# Washington

Moved from CLAUDE.md (2026-11-19). Shared conventions, the data traps list and the site's code notes stay there.

- **Washington (started 2026-10-30):** `python3 states/wa/fetch.py` reads the Legislature's web services
  (https://wslwebservices.leg.wa.gov/, plain GET, XML; see the wa-data-sources memory: their robots.txt says
  `Disallow: /`, but their documentation invites applications, and the owner decided to use them, politely). Each bill
  goes into data/wa/<session>/bills/<HB1003>.json: its versions (substitutes like "E2SHB 1003" are versions of HB1003),
  history, sponsors in order (with member ids) and, when the history shows a vote, its roll calls (every member, by id).
  A finished biennium is read once; the current one asks the change feed (GetLegislativeStatusChangesByDateRange) which
  bills changed since the last run. The first full copy (about 9,000 bills, three requests at a time) takes about 2½
  hours, so on GitHub it builds up over several runs (`began` in state.json). `states/wa/convert.py` reads the
  plain-English history. The lines don't say which house acted: committee steps carry the committee's acronym
  ("HSG - Majority; do pass."), passages match a roll call (which names its house), and otherwise the bill is in its
  house of origin until it passes. A bill a committee approves goes to that house's Rules Committee, which decides which
  reach the floor (shown in the Rules Committee, like Texas's Calendars; its "X file" is "held"). Two-year bienniums
  with a 105-day and a 60-day session (`opens()`, `adjourns()` in profile.js); the governor has 5 days, Sundays
  excepted, during a session and 20 after it (`govDeadline()`). `states/wa/contacts.py`: leg.wa.gov's legislator list
  (147 cards with the member ids the roll calls use) and committee pages (chairs, members matched by name and
  district); phones and emails from the web services' member list. Seat ids "S:21", "H:21a"/"H:21b" (New Jersey's
  scheme); the same districts for both houses. "What it does": the House or Senate staff's bill report
  (`states/wa/texts.py`: the Final Bill Report, else the latest report or analysis; its summary, not the background).
  Committee agendas for three weeks ahead (CommitteeMeetingService). Places from the Census relationship files
  (`states/wa/towns.py`; one district list per place, since both houses use the same districts). Earlier bienniums
  linked by short description and description words (`earlier()`). The history repeats lines (once per version) and
  isn't in date order: sorted and deduplicated. "Passed both houses" comes from the passage roll calls' motions
  (`both_agreed()`: "as Amended by the House" needs the Senate's agreement; a conference report needs both houses; the
  first house passing it again on third reading is starting over). At the end of the biennium's first session a bill that passed only its first house
  is "By resolution, returned to House Rules Committee for third reading": its passage is undone (`is_reset()`, keyDates[3],
  `STATE.resetNote()`, as New York's January reset); the same line at the end of the second session isn't. A few histories stop early (HB 2134 of 2023-24):
  a version's newer current status is added, "C 310 L 24" meaning chapter 310 of 2024. Laws include ones without the
  governor's signature, overridden vetoes and initiatives to the Legislature, so the governor's "signed" lists are a
  few short. Until the first full copy is complete, fetch.py writes data/wa/incomplete and build_site.sh and the
  checks skip Washington. GitHub downloaded the first full copy in one run (2026-10-31), and Washington is on the front page.
- **Sent back to committee from Rules (fixed 2026-11-19):** "Rules Committee relieved of further consideration.  On motion,
  referred to Ways & Means." (or "...; referred to ...") is a referral, not a floor placement: 17 Senate bills of 2025-26
  (SB 5659, SB 5085, SB 5797 ...) showed "On the floor" from the 2026 session's first day. And "Passed to Rules Committee
  for third reading." (a committee sending such a bill back, SB 5234) goes to Rules like "for second reading".
  And a referral to a committee the biennium's committees.json doesn't name (renamed since: 2023-24's "Community Safety,
  Justice, & Reentry", "Human Services, Youth, & Early Learning"; 2025-26's "Business, Financial Services & Trade") was
  kept as text, so 9 House bills of 2023-24 (HB 1098, HB 1108) sent back to committee in January 2024 showed on the floor:
  it's now a referral under the name as written ("and" matches "&").
