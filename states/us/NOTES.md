# Congress

Moved from CLAUDE.md (2026-11-19). Shared conventions, the data traps list and the site's code notes stay there.

- **Congress (/us/, built 2026-11-16; on the front page's list, not its map):** `python3 states/us/fetch.py` reads the
  Government Publishing Office's bulk bill status files (www.govinfo.gov/bulkdata/BILLSTATUS/, no key; robots.txt bars only
  the site's machinery): one zip per Congress and kind (hr, s, hjres, sjres; about 150 MB for three Congresses) into
  data/us/<congress>/, downloaded again when the server's copy is a week newer (a finished Congress's, a month), plus each
  file the sitemap (sitemap/bulkdata/BILLSTATUS/119hr/sitemap.xml, per-file lastmod) shows changed since, into updates/;
  then each bill's own roll calls from the House Clerk (clerk.house.gov/evs/<year>/roll<NNN>.xml) and the Senate
  (senate.gov/legislative/LIS/roll_call_votes/...; neither site has a robots.txt), a second apart, each once (about 1,600
  for three Congresses; `--votes-minutes`); and the public-domain congress-legislators data (unitedstates.github.io/
  congress-legislators: members with their terms, offices, phones, contact forms; committees and their members) into
  data/us/members/. `python3 states/us/contacts.py` (in states.json's run after fetch.py) builds each Congress's contacts;
  `states/us/towns.py` was run once. A page per two-year Congress named by its first year (`YEARS = 2`; 2025 is the 119th,
  `P.congress_of()`); `C.CONGRESSES` runs from the 117th (2021-22, older than the shared window's 2023 but kept from the
  start, as California's 2021 is) to the current one, so the 120th is added on January 3, 2027 (its zips appear days
  later: a new Congress's missing zips don't mark it incomplete for 45 days). HR, S, HJRES and SJRES only (simple and
  concurrent resolutions don't make law); joint resolutions "Proposing an amendment to the Constitution of the United
  States" are tagged "const": two-thirds of each house, then three-fourths of the states, never the President
  (`amendmentOnce`, `amendmentDone` "Sent to the states"); none passed both houses in 2021-26. Companion bills stay
  separate records, as on congress.gov. `states/us/convert.py`: each action comes up to three times, the House's own line
  (codes like H11100, times), the Senate's (no code) and the Library of Congress's summary line with a numeric code and a
  prefix ("Passed/agreed to in House: On motion to suspend the rules and pass the bill ..."); they're one event when
  their wording matches (one a prefix of the other: the Library's copy can leave off "(text of amendment ...)") or they
  carry the same roll call, and the Library's codes decide the milestones: 1000/10000 introduced, 5000/14000 reported,
  5500/14500 discharged, 8000/17000 passed the House/Senate, 9000/18000 failed, 19500/20500 resolving differences,
  21000/23000 conference report agreed to, 28000 presented, 31000 vetoed, 33000/35000 failed over a veto, 36000 became
  law. Steps the shared code reads are written "PASSED HOUSE: <the line>", "FAILED IN THE SENATE: ...", "SIGNED BY THE
  PRESIDENT", "VETOED by the President", which profile.js's `actionWords()` words plainly. Debate, "motion to reconsider
  laid on the table", "Message on Senate action sent to the House" and the like are left out (`NOISE`, `NOISE_CODES`);
  the Speaker's conferee appointments are one line a day; "(text: CR H1126)" references are dropped. Committees: from the
  bill's committee list (referred, reported, discharged, markup; not one named only in a motion to commit); the House
  refers many bills to several committees, and a bill is on the floor when each has reported or been discharged, or it's
  placed on a calendar. Committee votes are tallies from the House's markup lines ("Ordered to be Reported (Amended) by
  the Yeas and Nays: 29 - 20."), no names. Passed both houses: presented, a law or a veto, or the second house passed it
  unchanged, the first agreed to the second's amendment (not "with an amendment", which sends it back), or both adopted a
  conference report. Trap: the House's passage line doesn't always say it amended a Senate bill (S. 1383 of the 119th:
  "On passage Passed", with the House's substitute); a later "House amendment to Senate bill" or "motion to concur in the
  House amendment" (`AMEND_MSG`) says so, and it's still with the Senate (`passedIn` is then the house that changed it,
  as West Virginia's). Trap: "disagree to the Senate amendment" contains
  "agree to the Senate amendment" (H.R. 4521 of the 117th showed as passed both houses until the match needed a word
  boundary). "Senate incorporated this measure in H.R. 2670 as an amendment" (S. 2226 of the 118th, the NDAA) is shown as
  "Passed as part of HR2670" (`endedNote()`), and the host gets a line; nothing else in the data says a bill went into
  another. Floor votes are the roll calls on the bill's own question (`own_vote()`: passage, suspension, agreeing to the
  other house's amendment, conference reports, overrides, the Senate's cloture votes and motions to proceed; not motions to
  recommit or table, amendments, "(SA 1623)" alternatives, budget waivers or cloture on suspending a Senate rule), member
  by member from the downloaded roll calls (House by bioguide id, Senate by LIS id, both tied to seats through the
  member data), else the tally in the wording. A Senate tie the Vice President broke (H.R. 1 of the 119th, 51-50) is the
  senators' 50-50 with "(the Vice President broke a tie)": the data check fails on tallies above a house's seats. Seats:
  the Senate's "S:6a"/"S:6b" (California's two senators by FIPS code, a for the lower Senate class), the House's "H:612"
  (100 times the FIPS code plus the district; at large "H:200"), the delegates' and Resident Commissioner's "H:1100" (DC),
  "H:7200" (Puerto Rico) and so on: listed with the House, marked `nonvoting` in the contacts, and left out of the House's
  party count (balance.py). data/us/district_names.json names them ("California's 12th", "Alaska at large"); `STATE.
  distPhrase`/`seatText` word them. Titles: congress.gov's display title, or, when that's an official title ("An act to
  provide for reconciliation ..."), the bill's own short title ("One Big Beautiful Bill Act"), never one for a portion;
  the summary is the official title. "What it does" is the latest Congressional Research Service summary in the file,
  labelled by version ("From the Congressional Research Service's summary of the law as enacted."), cut near 4,000
  characters with a note. Topics: the CRS policy area (`POLICY_TOPICS`) and words in the titles and subject terms (an
  omnibus bill's dozens of terms count only three to a topic); Congress has two topics the states don't, "defense" and
  "foreign" (with trade and immigration), and calls "gov" "Elections & government" (`EXTRA_TOPICS`, `TOPIC_NAMES`, which
  test/data_check.py accepts). Narrow: "naming" for post offices, buildings and landmarks, commemorative coins and
  Congressional Gold Medals; "person" for private bills ("For the relief of ..."). Budget: appropriations and
  reconciliation bills. Earlier Congress linked by the same title (four words or more, "of 2023" aside) and sponsor, or a
  title one bill has in each; never laws, budget or naming bills. The President, not a governor: tracker.html's `EXEC`
  (from `STATE.executive`: "the President", "The White House", "Dear Mr. President,") replaces every "governor" a state's
  page shows; `BODY` ("Congress") the Legislature. 10 days, Sundays excepted (`govDeadline()`); pocket veto when Congress
  has adjourned; overrides two-thirds of each house. Laws are "Public Law 119-21" (`lawWord`; private laws have no
  `chapter`, their status says "Became Private Law 118-1"). Totals, matching GovInfo's published laws (bulkdata/PLAW) and
  the Senate's veto lists: 117th 362 public and 3 private laws, no vetoes; 118th 274 public laws, 13 vetoes (Biden's: H.J.Res.
  27, 30, 39, 42, 45, 98, 109, S. 4199, S.J.Res. 9, 11, 24, 32, 38), none overridden; 119th to 2026-11-16 142 public and 2
  private laws (GovInfo had published 138 public) and 2 vetoes (H.R. 131, H.R. 504), 4 bills on the President's desk.
  Veto messages (2026-11-22): a House bill's BILLSTATUS names the House document its message was printed as ("the veto
  message would be printed as a House document (118-26)"); fetch.py's `vetoes()` reads each from GovInfo once
  (content/pkg/CDOC-118hdoc26/html/CDOC-118hdoc26.htm) into data/us/<congress>/vetoes/hdoc26.htm, and convert.py's
  `veto_message()` keeps the letter between "To the House of Representatives:" and the signature. All 9 House bills'
  messages (118th: 7, 119th: 2) read on 2026-11-22. The six Senate bills' messages (S. 4199, S.J.Res. 9, 11, 24, 32, 38)
  are printed only in the Congressional Record ("text: CR S2089-2090", on 2 of the 6): not read. tracker.html's
  `vetoMemo()` now says "the President" (EXEC) where it said "the governor".
  "Where you live": the state first, then the place (`STATE.townRegions`, `regionWord`; tracker.html's `setRegion()`),
  about 35,000 cities, towns, Census-designated places and counties from the Census Bureau's 119th Congress relationship
  files (1.9 MB, on the current page only); the address lookup reads the geocoder's congressional district
  (`STATE.lookupDistricts`). The 119th's districts are those elected in 2024: several states drew new maps for 2026, so run
  towns.py again with the 120th Congress's files when the Census Bureau publishes them. Contacts: no member publishes an
  email; senators' contact forms are in the data, representatives' aren't, so their website (whose contact page is the
  form) is the `form`. An appointed senator's term ends on the special election's day (Husted, Moody: 2026-11-03); they
  keep the seat until a successor's term starts. Committees: the current Congress's only (the data has no past
  committees); chairs from the "Chairman"/"Chair" title. Leaders: Speaker Mike Johnson; the Senate's Majority Leader, John
  Thune, stands for the Senate (the Vice President presides); the 120th Congress chooses its own on January 3, 2027
  (`LEADERS`). The White House's contact form is the only contact shown (the comments line, (202) 456-1111, was dropped 2026-11-17: whitehouse.gov lists only the form, and the line closed during the 2025 shutdown). Party balance: states/legislatures.json's "us" (`executive` "President", seats S 100, H 435). Not done: no CBO cost estimates, the Senate's committee roll calls, House
  committees' member votes. issues_site.py reads every two-letter folder, so it counts Congress among the states (a "Congress"
  row in each issue's table, and in the "N states" and bill counts; not on the tile maps, which only have states): to be
  kept out for now (an owner's decision; not changed here).
- **Committee meetings (2026-11-22):** `states/us/meetings.py` (run after contacts.py in states.json, never failing the
  download) reads the Congress.gov API's committee meetings (api.congress.gov/v3/committee-meeting/<congress>/<house|senate>)
  with a free api.data.gov key: the environment's CONGRESS_API_KEY (the GitHub secret of that name, to be added by the owner)
  or ~/.congress_api_key; without one it does nothing and keeps the last copy. Each run lists both houses' meetings updated in
  the last 21 days (the list filters by update time, not the meeting's day) and reads the details of the new or changed ones,
  a second apart, newest first, for at most 4 minutes; data/us/meetings.json keeps each meeting's day (UTC), kind, status,
  committees and bills (relatedItems, else the "H.R. 123" numbers its bill documents and title name), and drops meetings
  over a month past. It's rewritten only when a meeting changed, or twice a day for its "listed" time, which check_site.py
  fails on when more than 3 days old. `convert.agendas()` turns it into the shared agenda shape, with a third item, the
  kind: "markup" (the House's Markup, the Senate's Business Meeting or Executive Session) or "hearing"; canceled and
  postponed meetings are left out, times are Eastern (`STATE.meetZone` "ET"). The page says "Markup (committee vote): ..."
  or "Hearing: ..." where a state's says "On the agenda: ...". The DEMO_KEY allows only 10 requests an hour (enough to
  test, not to run). On 2026-11-22 (the Thanksgiving recess) no meeting still to come named a bill: the
  House's committee calendar (docs.house.gov) had no meetings posted from November 23 to December 4, and the Senate's five
  (senate.gov's hearings.xml) were nominations, closed briefings and a hearing on caregivers and AI.
- **A new Congress (2026-11-22):** the 120th becomes current on January 1, 2027 (its bills start January 3; govinfo
  answers 404 for /BILLSTATUS/120 until then). fetch.py reads its bills from the sitemaps before its first zips are built
  (updates/), its missing zips don't count for 45 days, and the 119th is read like the current Congress (sitemap updates,
  weekly zips) until March 1, for the President's last actions. convert.py's `sessions()` shows a Congress from its first
  House or Senate bill file. contacts.py skips the new Congress's contacts until March 1 while congress-legislators lists
  too few of its members (none of its terms on 2026-11-22).
