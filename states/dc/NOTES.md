# District of Columbia

Started 2026-11-22. Shared conventions, the data traps list and the site's code notes are in CLAUDE.md.

- **LIMS decided (2026-11-24, the owner's decision):** the owner registered for a LIMS developer key (~/.dc_lims_key, GitHub
  secret DC_LIMS_KEY; header "Authorization: <key>"; tested: /api/v2/PublicData/CouncilPeriods answers 200) and chose to
  use the API despite robots.txt's blanket "Disallow: /": the Council issues keys so programs can use it. Gently: one
  request every few seconds, identified as statebilltracker.org, only changed records; LegiScan stays as the fallback until
  the LIMS build matches or beats it.
- **Source (decided by necessity, for the owner to confirm).** The Council's own system, LIMS (lims.dccouncil.gov), has a
  documented public API (Swagger at /api/help/index.html, spec /api-docs/v2.0/swagger.json: PublicData/BulkData,
  LegislationDetails, Members, Committees, LegislationVoteDetails ...), but (1) every endpoint answers 401 "Valid Access
  Token required": a developer key comes from a sign-up form that emails it (the owner's email can't be sent from here),
  and (2) LIMS's robots.txt is `User-agent: * / Disallow: /` (checked 2026-11-22), like Washington's web services, which
  the owner chose to use anyway, and Arizona's, which she chose not to. So the bills come from **LegiScan** (legiscan.py,
  the shared LegiScan job; states/LEGISCAN.md), which copies LIMS's records (same history wording, roll calls member by
  member, the Secretary's abstracts as `description`). The first copy was 3 queries (2 datasets) plus a one-time catch-up
  (below). To move to LIMS later: the owner registers for a key (~/.dc_lims_key, secret DC_LIMS_KEY) and decides on the
  robots.txt question; then a fetch.py reading BulkData per category and period could replace legiscan.py for DC.
- **Acts and laws: the Council's law library** (`states/dc/laws.py`): github.com/DCCouncil/law-xml, the source of
  code.dccouncil.gov (GitHub isn't under LIMS's robots.txt; code.dccouncil.gov's robots allows all but AI-training bots).
  One XML file per act and per law per Council Period, with law, act and bill numbers, short and long titles, effective date,
  `<temporary/>`, enactment date. Read once a day (GitHub's contents API listing, then only new or changed files from
  raw.githubusercontent.com; about 900 files the first time, ~4 minutes). Into data/dc/laws_<first year>.json.
  **Data trap:** LegiScan stops updating a finished Council Period a few weeks after it ends (the 25th Council's dataset is
  dated 2024-12-29; its bills' records stop about January 31, 2025), before the last acts get to the Mayor and through
  Congress's review. legiscan.py now treats DC's periods as running until June 30 after they end (`AFTER_END`) and reads a
  finished period's master list once (`catch_up()`; 2026-11-22: 234 bills read for the 25th Council), and the law library
  supplies law numbers LegiScan never got: 2023-24 had 52 acts showing "under review by Congress"; with the library, 3 (B10,
  a street closing transmitted with a projected law date of March 6, 2025, and two Federal Portion Budget Request Acts,
  which aren't laws). Every permanent law in the library is a law here (159 in 2023-24, 102 so far in 2025-26).
- **Records: permanent bills only.** About half of the "B" numbers are emergency acts (one reading, in effect up to 90
  days, no Congress review) and temporary acts (225 days, after review), usually passed alongside a permanent bill: left
  out (the shared "bills only" rule, and they'd count each change three times; `SHORT_TERM` reads the title: "...
  Emergency Amendment Act of 2025", "... Temporary Act ...", not "Emergency Medical Services ..."). Each permanent bill's
  history names its emergency and temporary versions when their titles match (`companion_key()`: the title's words without
  emergency/temporary/congressional review/continuation/second...), on the day each was enacted ("Emergency version,
  B25-0339: enacted without the Mayor's signature (A25-0168), in effect until Oct 08, 2023"), and `textLinks` links them.
  Resolutions (PR, CER) are left out. 2023-24: 467 permanent bills; 2025-26: 478 (to 2026-11-22).
- **Numbers.** LIMS writes B26-0001; the site's records are "B1" on each period's page (the shared code wants letters and
  up to 5 digits, and a number's first letter is its house): the house letter is "B" (`P.LOWER`, `STATE.houses = { B:
  "Council" }`, one house like Nebraska's "L": tracker.html's `UNI`). `STATE.official()` turns "B1" back into B26-0001 for
  links and the panel's link labels. A search for "B26-0123" doesn't find it (open question: an alias in the search files).
- **Stages** (`states/dc/convert.py`, from the history): referred (0) → marked up or a committee report filed, or "Retained
  by the Council", or first reading (1, "Before the full Council") → final reading passed (3, "Passed the Council") →
  "Transmitted to Mayor, Response Due on ..." (4) → signed, enacted without signature, or a veto overridden (5) → vetoed (6).
  A reading passes when its roll call has more yes than no (LegiScan's `passed` is 0 on some unanimous readings: B25-0202's
  13-0 Final Reading); an override needs two-thirds of those voting. LIMS lists a hearing or mark-up ahead of time, dated
  the meeting's day ("Public Hearing", "Committee Mark-up of B26-0425"), and a referral that takes effect at the next
  legislative meeting (B26-0883: introduced November 16, "Referred" December 1): lines dated after today stay out of the
  history; hearings and mark-ups are `agendas()` (22 bills on 8 upcoming meetings on 2026-11-22). A mark-up held counts as
  the committee's approval unless a cancellation notice follows (LIMS records no committee votes).
- **Congress's review: the stage choice.** An enacted act is stage 5, like a signed law everywhere on the site (shared
  convention: laws are stage 5 whatever the route; /compare/ counts them), because Congress almost never blocks one (four
  times since 1973; the Revised Criminal Code Act in 2023). Its status words say where it is (`STATE.lawText()`, a new
  shared hook read in billfacts.js's `factsOf()`): "Enacted; goes to Congress for review" (signed, not yet transmitted),
  "Enacted; under review by Congress", then "Became law" once a law number is recorded (LegiScan's "Law L26-0132,
  Effective from ..." or the law library). The pipeline and charts say "Enacted". The History's enactment line is "Signed by
  the Mayor" / "Enacted without the Mayor's signature" / "Enacted over the Mayor's veto" (`STATE.lawLine`), and "Every
  action" has "Became law (L26-0132), effective ...". If Congress ever disapproves an act, the converter has no line for it
  yet (none in the window): add one (stage 6, worded "Blocked by Congress").
- **The Mayor's deadline** (`govDeadline`): 10 days excluding Saturdays, Sundays and the District's legal holidays (D.C.
  Code 1-204.04(e)); `STATE.holidays()` includes Emancipation Day (April 16) and Inauguration Day. Checked against all 1,202
  "Response Due" dates in the files: 1,147 match; most of the rest are LIMS's own (April 2024's skip no Emancipation Day,
  some a day early). Each act's own due date is in its history line.
- **Votes:** first and final readings and override votes, member by member, labelled by reading (`STATE.voteWhat`);
  amendments and motions left out; duplicate roll calls dropped (B26-0164's September 17, 2025 final reading is in the
  files twice). Seats are the current members' in the current period; former members (Kenyan McDuffie, who left in
  December 2025; Robert White, October 2026; Doni Crawford, interim February-July 2026) are names. With 13 members two
  departures are 11% of the named votes, so test/data_check.py's "votes not tied to a seat" check now FAILs only on names
  still voting in the last four months (9.6% on 2026-11-22, falling as Robert White's last votes age).
- **"What it does":** the Secretary's abstract ("As introduced, it would ..."), with referral notes dropped and the labelled
  notes kept after it ("Fiscal note: ...", "Racial equity analysis: ..."), and the enacted act's long title from the law
  library ("As enacted, it is an act to amend ..."). 450 of 478 bills in 2025-26, 352 of 467 in 2023-24.
- **Members and committees** (`states/dc/contacts.py`): dccouncil.gov (robots allows all), once a day: the 13 members'
  pages (seat, email, phone, office, affiliation, committees, photo) and each committee page (chair, members). Seats:
  wards "B:1"-"B:8", at large "B:9a"-"B:9e" (the Chairman first), district 9 named "At-large" (data/dc/district_names.json).
  LegiScan ids by name; a page with no affiliation yet (Jamal Holtz, November 2026) takes LegiScan's party. 2026-11-22: 11
  Democrats, 2 independents (Christina Henderson, Elissa Silverman). Committees: 10, the Housing Committee's page names no
  chair (Robert White chaired it), and the Business and Economic Development page answered an error.
- **Find your Councilmembers:** a neighborhood list (`states/dc/towns.py`, run once: DC GIS's "Neighborhood Labels" points
  in the "Wards from 2022" polygons; 132 neighborhoods, one ward each, kept in git), a ward picker, and the address lookup
  (the Census geocoder files DC's wards as "State Legislative Districts - Upper": "Ward 2"). The five at-large members
  represent everyone (`STATE.atLarge`, a new tracker.html hook in `myReps()`, and `STATE.atLargeLine`).
- **The Mayor:** Muriel Bowser (D) since January 2, 2015; Janeese Lewis George (D, the Ward 4 Councilmember) elected
  November 3, 2026, takes office January 2, 2027 (`GOVERNORS`, legislatures.json `governorNext`). The Mayor's page is
  /dc/mayor/ (legislatures.json `executive`).
- **January 2027 checks:** Council Period 27 begins January 2 (members elected in November 2026: Chairman, two at-large
  seats, Wards 1, 3, 5, 6); Ward 4's seat is vacant once Lewis George becomes Mayor (a special election follows); check the
  Chairman (`LEADERS`), and that LegiScan lists the 27th Council (`folders()`), and the at-large seat letters.
- **Front page:** a tile below Maryland ([5, 8], the usual tile-map spot), named "District of Columbia"; party control
  colors it like a state (Council and Mayor both Democratic: blue, with a supermajority ring, 11 of 13).
