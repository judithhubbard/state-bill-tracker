# State Bill Tracker: the multi-state version (in progress)

The repository is public (made so 2026-11-01, for unlimited free GitHub Actions minutes). Never commit secrets: keys
live in ~/.<name> files and GitHub secrets; check `git log -p` before committing anything that reads a key.

This is a separate project, started 2026-10-27 as a copy of ny-bill-tracker (commit b312227), in
/Users/jk/Dropbox/Claude/AlbanyBillTracker. The live New York site, albanybilltracker.org, still runs
from that repo. **Nothing here may change it.**

Each state's data notes (sources, formats, quirks, totals checked) are in states/<code>/NOTES.md: read the state's
notes before changing its code. Shared notes on the LegiScan states are in states/LEGISCAN.md.

## Goal and plan

- One codebase with a profile per jurisdiction: chambers, session calendar, the governor's (or
  president's) deadline rule, stage wording and topics. Each jurisdiction lives in its own folder on
  statebilltracker.org (/ny/, /us/, /nj/ …). statebilltracker.org and .com are bought, at Porkbun, and
  parked on purpose until launch.
- Order:
  1. Move New York's rules out of the code into an NY profile, with NY's pages unchanged. `test/check.sh`
     guards this.
  2. Build one pilot: New Jersey (/nj/), chosen 2026-10-27. Its Legislature publishes bulk files with
     everything the site needs (see the nj-data-sources memory). Federal (/us/) comes after.
  3. Move New York here last. albanybilltracker.org must keep serving small pages that read each
     visitor's saved watchlist and pass it along while redirecting (a plain Porkbun forward would lose
     them). Map /kelles/ to /ny/kelles/, and so on. Interim forwards must be 302, never 301.
     **Approved by the owner 2026-11-18:** do it right after statebilltracker.org launches, before the January 2027
     sessions. albanybilltracker.org's pages become forwarding pages that pass each browser's saved data (watchlist,
     stances, action log, county; saved here as "abt:ny:..." by welcome-ny.html) to the matching statebilltracker.org/ny/ page,
     which saves it and clears it from the address; its published lists are copied from the albany-lists KV (LISTS) to
     state-lists (state "ny"), keeping their addresses. This is the one change allowed to the AlbanyBillTracker repo.
     Prepared 2026-11-18 (not switched): the forwarding pages and a publish-only workflow are on the local, unpushed
     branch `move-to-statebilltracker` in /Users/jk/Dropbox/Claude/AlbanyBillTracker (commit d34f749; steps in its
     SWITCH.md); this repo's side is lists_pages/welcome-ny.html (/welcome/ny/) and tools/copy_albany_lists.py.
     Albany had no published lists on 2026-11-18 (4 invite codes, 0 lists).
     **New York's downloads are this repo's own (2026-11-22):** download.yml's "New York" job (`states/ny/fetch.py`:
     memos, bills, prefiled bills, Assembly votes, agendas, contacts; cache `ny-data-v1`); publish.yml no longer reads
     the ny-bill-tracker repo, so the switch can freeze it. Past sessions' bills_<year>.json.gz are this repo's (with
     veto messages, which Albany's copies lack).
- **Decided 2026-10-28:** no new features on albanybilltracker.org (the ny-bill-tracker repo); only fixes and the
  January chores, made there and carried here by hand. New work happens here. **Decided 2026-10-29: leave
  albanybilltracker.org on its own code** (an interim switch of its build to this repo was planned, dry-run on
  2026-10-28 and dropped). New York moves only once, to statebilltracker.org/ny, with the forwarding pages
  below; avoid doing that at the start of a session (aim before January or after June).
- **Decided 2026-10-29:** every state is built from its own legislature's official files and done thoroughly, like
  New Jersey; not from Open States. Virginia came next, then California (chosen 2026-10-29), then Texas and Illinois (2026-10-30), then Washington (chosen 2026-10-30; see the wa-data-sources memory), then Ohio, Connecticut, Oregon, Massachusetts, Pennsylvania, Maryland, Georgia, Michigan, Wisconsin, Arizona and North Carolina (2026-10-31); Arizona is the exception (decided 2026-10-31): its Legislature's data service, apps.azleg.gov, has robots.txt
  "Disallow: /", and the owner chose not to ask permission, so Arizona's bills come from Open States, supplemented where
  needed from azleg.gov pages its robots.txt allows, at its 120-second crawl delay; the owner will do every state, in no particular order (see the state-survey-2026-10-31 memory: Oregon next); more states before launch.
- Generalize only what the pilot shows really varies. Label watchlists by jurisdiction, so a combined
  state + federal list is possible later.
- **Progress:** step 1 has started. New York's build settings (names, addresses, session rule,
  governors, delegation, leaders, topics, places, trends) are in `states/ny/profile.py`, which
  build_data.py reads as `P.<name>`. The code that reads NY's own data (Senate API milestones and
  action wording, Assembly vote codes, `memo_text()`) is in `states/ny/convert.py`, which build_data.py
  calls as `C.sessions()` and `C.load_session()`; the shared stage numbers are in `stages.py`.
  `--state nj` picks another state's folder. Still NY-shaped in build_data.py: contacts, legislators,
  parties and the Assembly vote-name resolver, which read NY's contacts file. The page's NY settings and rules are in
  `states/ny/profile.js` (the `STATE` object; see the map below). Still NY-only in tracker.html: its
  explanations (How a bill becomes law, chapter amendments, "held for consideration"), `PLAIN` and
  the NY action wording, which move when NJ needs its own.
- **New Jersey (built 2026-10-27)**: see states/nj/NOTES.md.
- **Virginia (built 2026-10-29)**: see states/va/NOTES.md.
- **California (built 2026-10-29)**: see states/ca/NOTES.md.
- **Texas (started 2026-10-30)**: see states/tx/NOTES.md.
- **Illinois (started 2026-10-30)**: see states/il/NOTES.md.
- **Washington (started 2026-10-30)**: see states/wa/NOTES.md.
- **Ohio (started 2026-10-31)**: see states/oh/NOTES.md.
- **Connecticut (started 2026-10-31)**: see states/ct/NOTES.md.
- **Oregon (started 2026-10-31)**: see states/or/NOTES.md.
- **Massachusetts (started 2026-10-31)**: see states/ma/NOTES.md.
- **Pennsylvania (started 2026-10-31)**: see states/pa/NOTES.md.
- **Maryland (started 2026-10-31)**: see states/md/NOTES.md.
- **Georgia (started 2026-10-31)**: see states/ga/NOTES.md.
- **Michigan (started 2026-10-31)**: see states/mi/NOTES.md.
- **Wisconsin (started 2026-10-31)**: see states/wi/NOTES.md.
- **Arizona (started 2026-10-31, from Open States)**: see states/az/NOTES.md.
- **North Carolina (started 2026-10-31)**: see states/nc/NOTES.md.
- **Wyoming (started 2026-11-01)**: see states/wy/NOTES.md.
- **South Dakota (started 2026-11-01)**: see states/sd/NOTES.md.
- **Utah (started 2026-11-07)**: see states/ut/NOTES.md.
- **Colorado (built 2026-11-07)**: see states/co/NOTES.md.
- **Indiana (built 2026-11-08)**: see states/in/NOTES.md.
- **Arkansas (built 2026-11-08)**: see states/ar/NOTES.md.
- **New Hampshire (built 2026-11-08)**: see states/nh/NOTES.md.
- **Alaska (built 2026-11-08)**: see states/ak/NOTES.md.
- **North Dakota (built 2026-11-08)**: see states/nd/NOTES.md.
- **Idaho (built 2026-11-08)**: see states/id/NOTES.md.
- **Alabama (built 2026-11-08)**: see states/al/NOTES.md.
- **Kentucky (built 2026-11-08)**: see states/ky/NOTES.md.
- **Mississippi (built 2026-11-08)**: see states/ms/NOTES.md.
- **Delaware (built 2026-11-08)**: see states/de/NOTES.md.
- **Montana (built 2026-11-09)**: see states/mt/NOTES.md.
- **Nevada (built 2026-11-09)**: see states/nv/NOTES.md.
- **Minnesota (built 2026-11-09)**: see states/mn/NOTES.md.
- **Missouri (built 2026-11-13)**: see states/mo/NOTES.md.
- **New Mexico (built 2026-11-13)**: see states/nm/NOTES.md.
- **West Virginia (built 2026-11-13)**: see states/wv/NOTES.md.
- **Nebraska (built 2026-11-13)**: see states/ne/NOTES.md.
- **South Carolina (built 2026-11-13)**: see states/sc/NOTES.md.
- **Kansas (built 2026-11-13)**: see states/ks/NOTES.md.
- **Louisiana (built 2026-11-14)**: see states/la/NOTES.md.
- **Florida (built 2026-11-15)**: see states/fl/NOTES.md.
- **District of Columbia (built 2026-11-22, /dc/; bills from LegiScan because LIMS needs a key and bars robots; laws from the Council's law library)**: see states/dc/NOTES.md.
- **LegiScan states (2026-11-08): Tennessee, then Oklahoma, Maine, Rhode Island, Vermont.** Their shared design (legiscan.py, the query budget, states/legiscan_convert.py): see states/LEGISCAN.md.
- **Tennessee (built 2026-11-08 from LegiScan)**: see states/tn/NOTES.md.
- **Oklahoma (built 2026-11-08 from LegiScan)**: see states/ok/NOTES.md.
- **Rhode Island (built 2026-11-08 from LegiScan)**: see states/ri/NOTES.md.
- **Vermont (built 2026-11-08 from LegiScan)**: see states/vt/NOTES.md.
- **Maine (built 2026-11-08 from LegiScan)**: see states/me/NOTES.md.
- **Fewer yearly chores (2026-10-29):** Virginia's computed session dates and crossover: see states/va/NOTES.md.
  `check_site.py` runs last in publish.yml (daily) and fails the run (GitHub
  emails) when legislators are stale or too few, New Jersey's bill texts are missing, Virginia's date rule stops
  fitting the floor votes, or a state's data stops updating (2026-11-22, `freshness()`: no successful download for 2 days,
  the download failing every run, a live session losing bills since the day before, or, in session only, no new bill
  action for two weeks or more; milder cases are warnings in the run's summary). Still by hand: a new governor (`GOVERNORS`) every four years, next January 2030.
- **Wikidata and Commons (the owner's decision, 2026-11-22):** query.wikidata.org's robots.txt disallows /sparql and
  commons.wikimedia.org's /w/ (the API), but Wikimedia's User-Agent policy and API rules welcome identified programs; the
  owner chose to use them, gently (one request a second, maxlag, a User-Agent naming statebilltracker.org, no email), for
  governors' photos (tools/governor_photos.py) and legislators' photos missing elsewhere (photos.py's Wikidata fallback;
  credits in photos.json, shown on each photo and in How's "About this data"). The photos themselves (upload.wikimedia.org)
  are allowed. Every other host's robots.txt is still obeyed.
- **Governors' photos (2026-11-22):** states/governor_photos.json, from Wikidata (P18) and Wikimedia Commons thumbnails, by
  tools/governor_photos.py (matched by name and the state's governor's office; a governor-elect by name when only one U.S.
  politician fits; `PICK` settles namesakes, e.g. Wisconsin's David Crowley). publish.yml asks again weekly and when
  legislatures.json names someone new (its own cache, gov_photos/). The build shows the photo of whoever is in office that
  day (`govNow.photo`): the governor's page card and the header's Governor panel; the credit is in How's "About this data".
- **Tabs (2026-11-19):** a state's page has Bills, Watchlist, Statistics and How laws are made. The Weigh in tab is gone
  (the owner's decision): "Find your legislators" (`#whereBox`, `renderMyReps()`, drawn when opened; "Where you live"
  until 2026-11-20; the names link to their pages) is a line under the title on every tab, the only place to pick a
  county, town or address (the sidebar keeps only "Hide bills about other places", shown once a county is chosen); each state's weighin.html (how to weigh in, the governor's office, who decides)
  is still put in `#view-act` by the build and moved at startup to the end of How's "Having an impact" (`#impact`). A
  legislator's page keeps `#view-act` as its "Open for comment" tab (`renderOpenNow()`). Statistics opens on "Odds of
  becoming law" (the "How far bills get" bars were dropped); Statistics' Committees and Timing link to How's Committees and
  calendar, and How's Committees back (`data-gostat`).
- **Saved settings are per state (2026-10-29):** the states share one web address, and a browser keeps one set of saved
  settings per address, so tracker.html prefixes every saved name with `STORE` ("abt:nj:", "abt:va:", and "abt:ny:" since
  2026-11-19; New York kept the plain "abt:" names until then, which made other states' old stars show as New York's in
  Your bills). `adoptShared()` takes a state's own bills, once, from the watchlist, log and stances saved under the plain
  names before this; New York's page moves its own once (`moveNewYork()`: odd-year A and S bills, odd-year sessions'
  settings). Every watchlist scan (`/^abt:([a-z]{2}):watch$/`) needs the state in the name. Site-wide names stay plain:
  abt:follows, abt:lists, abt:all:published, abt:yourbills:*, abt:tabseen, abt:issueview, abt:supportnote.
- **Adding a state (learned from NJ and VA):** missing settings fall back to New York's rules and wording, silently.
  Copy states/nj or states/va and decide each of these: in profile.py, `YEARS`, `LOWER`/`LOWER_NAME`/`TITLES`,
  `LEADERS`, `GOVERNORS`, `TOPICS`, `TOWNS_PATH`; in profile.js, `code`, `houses`, `titles`, `memberWords`,
  `greetings`, `years`, `sessionLabel`, `govReach`, `billUrl`/`textLinks`, `sessionEnds`, `govDeadline`, `dueLabel`,
  `passedBothBy`/`passedBothNote`/`passedBothGroup`/`passedBothNext`, `floorVotesEnd`, `diesAfterFloor`,
  `outOfTimeLine`, `sessionNotice`, `waitingHead`, `govYearsNote`, `partySource`, `openUntil`, `heldLabel`/`heldTip`/
  `heldNote`, `routine`, `oneNumber`, `continuedTo`, `requestsBills` (New York only), `townWord`/`findReps`,
  `stageText`/`stageTips`/`pastStageTips`/`outOfTime`, `commPairs`/`commNotes`/`moneyCommittees`/`secondCommittee`,
  `calendar`/`calendarDays`, `tracks`/`unsigned`/`override` (How's picture, `renderHowPic()`: "twins" or "relay"; what a bill the
  governor doesn't sign does, as `law` and `dies` lines with a tip; Nebraska's `trackVote`); and write how.html and weighin.html. Then run the review: record every tab, Statistics
  section, How section, bill panels at each stage and a watchlist, and grep the text for other states' names and rules.
- **Years kept (2026-11-16): every state keeps the same window,** `states/window.py`: this year and the four before, never
  before 2023 (`first_year()` = max(2023, year - 4): 2023-26 now, 2023-27 in 2027, 2024-28 in 2028). A two-year session
  counts while any of its years is in the window (2023-24 until 2029; New Jersey's 2022-23 until 2028). Each fetch.py takes
  its years from it (`W.years()`, `W.first_session()`); legiscan.py keeps sessions ending in it. States that already had
  older sessions keep them (CA, IL, TX, WA, OH from 2021; CT, OR from 2022; NJ from 2018). A year the window added back
  (2023 for the one-year states) never holds a state off the site: only this year and last (`W.recent()`) can;
  `W.settle()` turns an older year's missing parts into its own marker, data/<st>/incomplete_<session>, and build_data.py
  and data_check.py leave just that session out (`W.shown()`) until a later run finishes it. Exceptions: Virginia's LIS
  files start with 2024, so 2023 comes once from the legacy LIS's CSVs (Virginia paragraph); Arizona's 2023
  waits for its bulk file (above); Florida's 2023 is read from flsenate.gov's pages unless the owner adds its bulk file
  (FL_2023_json_<id>.zip) to states/fl/bulk.json. A one-year state's 2023 may need its `STATE.dated` / `SESSION_ENDS`
  entry once the data is there (each falls back to the computed rule).
- **Shared conventions (2026-11-01), so states can be compared later** (a "Compare states" page waits until most
  states are built). Every state follows these; `test/data_check.py` fails when one doesn't:
  - The same 14 topics with the same names (`TOPICS` in data_check.py): ag, biz, const, edu, env, gov, health, housing,
    human, labor, local, safety, tax, transp. A state maps its own committees, subjects or keywords onto them.
  - "What it does" names its source as a sentence: "From the Legislative Reference Bureau's synopsis."
  - Bills only (each chamber's bill type), plus constitutional amendments tagged "const"; other resolutions left out.
  - What skews comparisons is marked on the record: narrow bills (`narrow`: "place" for local bills for one city or
    county, as in GA and NC; "person", "org", "naming"), placeholder bills (`shell`, IL), and the session length
    (`YEARS`, `session_kind()` for states alternating long and short sessions). Two-year legislatures holding a different
    session each year (Arkansas regular + fiscal, Wyoming general + budget, Kentucky short + long; 2026-11-22, the owner's
    decision) set `STAT_CYCLE = True`: Statistics, Timing (24 months), the Sessions table (each cycle, then its two
    sessions by `sessionKind`) and /compare/ count each odd-even pair as one cycle ("2023–24"), as New York's two-year
    sessions (build_data.py's `to_cycles()`, `cycle_years()`); each session keeps its own pages, and the deadline rules
    still read past sessions of the page's own kind (`sessionTiming`).
  - Laws are stage 5 whatever the route (signed, without signature, over a veto, local bills ratified in NC); amendments
    stop at stage 3.
- **Data traps found so far.** `python3 test/data_check.py` checks every state for all of these that a program can
  check (FAIL), and prints what a person should read over (LOOK: totals to compare with the official ones, odd wording);
  the daily run runs it too. Run it after any change to a state's data code, and when a new trap goes on this list,
  add its check there and run it against every state, not just the one where it turned up:
  - Status flags that disagree with the history (VA's Approved/Vetoed: both set, or neither). Decide stages from the
    history, and count bills by stage against the Legislature's own totals (e.g. vetoes per year).
  - "Passed" flags that mean one house (a VA bill that died in conference is still "Passed").
  - Formats that change between years: dates ("3/14/2026" vs "2024-03-02T00:00:00"), and tables missing from an
    older year's download (NJ 2022–23 lacked four; filled once by fill2022.py). Columns too: AR's 2023-24 members file
    has one column fewer than 2025-26's, and a reader requiring 22 fields dropped every member, leaving that session's
    sponsors as "L. Johnson" with no party. The check flags a session whose sponsors mostly have no party.
  - Characters lost in the export: VA's summaries have "?" for §, dashes and apostrophes. Grep the text for
    " ? " and a letter, "?", then a letter. WA's bill reports (a few) have "?" for an "fi"/"ff" ligature ("speci?c")
    and for non-breaking spaces ("establish?rate", ".??"): put back what makes words the other texts use.
  - Labels that mean a different procedure in different states: "Constitutional amendments" in NY are resolutions
    that never go to the governor (they pass two separately elected Legislatures, then the voters); in VA they're
    bills that set up the ballot question, which the governor signs. Rules that follow from a tag belong in a state
    setting (`STATE.amendments`), not in shared code; the check fails if a tagged NY amendment reaches the governor.
  - Codes written two ways across files: committee "S2" vs "S02", member "S0100" vs "S100". Join on a normalized key
    and count rows that fail to join.
  - Empty columns that look filled in the documentation (NJ ROSTER.TXT's Email); vacant seats (VA House District 20).
  - History wording in mixed case or plain English: match case-insensitively, and keep text the rules don't need as written.
  - Settings left out fall back to New York's silently (above); grep the built pages for "Assembly", "Albany", "Hochul".
  - A website that blocks automated requests (governor.virginia.gov): drop that data and tell the owner. Don't work
    around the block.
  - Every wording of a floor vote: list each history line that mentions "passed" but isn't read as a passage, and
    look at the most common. CA writes "Read third time. Urgency clause adopted. Passed." (about 700 votes missed at
    first). And votes the house undid: CA "Action rescinded whereby the bill was read third time, passed",
    VA "Reconsideration of passage agreed to by Senate" (a bill then showed as passed by a house that undid it).
  - Votes missing from the record: a bill that passed both houses passed each one, whatever its history says
    (CA AB876 of 2023 has no Senate vote). Count bills at stage 3-6 without both passage flags; it should be 0.
  - Steps that look like committee votes but aren't: CA "From committee chair, with author's amendments: Amend, and
    re-refer" is the sponsor's amendment. Check committee pass rates look plausible.
  - Summary text: the files' own line breaks aren't paragraph breaks (collapse whitespace before turning </p> into
    a break); count paragraphs that end without punctuation (CA and VA had about 15% cut mid-sentence; NJ's are
    real headings and list items). Lead with what the bill does when the text opens with background (CA's digests
    start "Existing law ...").
  - Ids padded in one file and not another (CA's text files write "AB__001698" for AB1698: every bill under 1000
    failed to match at first). When a fixed share fails, suspect the matching, not the data.
  - Two file formats from one server: MI's status files come in an older and a newer layout; reading only the newer one
    left 3,088 of 3,494 bills of 2023-24 with no history ("In committee"). Count bills with no history lines.
  - Tallies that disagree within the source: WI's history line for SB 541 of 2023 says "Noes 8"; its roll call lists nine
    noes by name. Prefer the roll call's own totals; the check counts vote lists with more noes than their tally.
  - Members who change house or name mid-session: OR's "Rep Neron" became "Sen Neron Misslin", and a session's member
    list shows only the end state; look the old code up in other years' lists.
  - Names: degrees and titles ("Dr.", "M.D.", "Ph.D.", "Esq.") aren't part of a name; "Jr."/"III" are, but aren't the
    last name (`shortName()`). Check each contacts file for duplicate phone numbers.
  - Placeholder bills (CA "spot bills": technical, nonsubstantive changes; "intent" bills) and stock sentences
    ("no reimbursement is required by this act") make unrelated bills look alike; keep them out of matching.
  - The other state's settings in shared slots: each `keyDates` entry means the same thing in every state (the 4th
    is a passage undone between a two-year session's years: New York's January return to committee, Washington's
    "By resolution, returned to Senate Rules Committee for third reading" at the end of the first year's session (not the
    second's, when bills just die); only a state with `STATE.resetNote` fills it in).
  - Agreeing to the other house's changes "as amended" is a new change, not the end (GA's "House Agreed Senate Amend or
    Sub As Amended": HB 196 of 2023-24 then died in conference).
  - A conference report passes only when both houses adopt it (TX HB3104 of 2023: the House adopted it, the Senate never
    did, and it showed as passed both houses). Same for any step one house can take alone.
  - Passing each house isn't passing both: when the second house amends a bill, the first has to agree (WA's "Final
    Passage as Amended by the House", OH's "Passed - Amended" or a substitute: 19 OH bills of 2023-24 and 5 WA bills of
    2021-22 showed as passed both houses). Use enrollment, or the roll calls' motions; count bills "passed both houses
    but not sent" in a finished session, which should be about 0.
  - Histories where some lines carry a time and some only a date (MA's S2913: sorting by the full time put "Read second"
    after "Laid before the Governor"). Sort by day and keep the file's order within a day; the check counts out-of-order lines.
  - Dates that aren't the event's: PA's "(Remarks see House Journal ...)" lines carry the day the remarks were filed,
    months after the vote their wording names. The out-of-order check catches these.
  - Dates missing from a few records: OH's HB 110 of the 134th (the budget) has no signing date; WA's HB 2134 of
    2023-24 has a history that stops in committee. Fall back to what else the record says (enrolled and not vetoed in a
    finished session; a "C 310 L 24" status), and compare totals with the legislature's own lists.
  - Numbers that look final but aren't: CT gives a Public Act number when a bill passes both houses, before the
    governor signs or vetoes it (HB 7004 of 2025 got one, then a veto). Decide "law" from the signature, not the number.
  - A record the server fails on every time (OH's HB 178 of the 134th: its actions answer 500): keep the last copy or
    what loads, mark it, and don't let one record hold the whole download "incomplete".
  - A file's encoding: read UTF-8 first ("bedï¿½a" in TX analyses read as Windows text). Grep built texts for "ï¿½" and "\ufffd".
  - Summaries of the bill as filed when an amendment rewrote it: IL laws summarized as shell bills ("Makes a technical
    change"). Read every amendment's summary the files carry; the check counts laws summarized as placeholders.
  - Summaries that only repeat the title (TX "C.S.H.B. 2 amends current law relating to ...") say nothing: drop them, or
    use an earlier version's.
  - Look at every part of a bill panel at phone width (375px iframe): the similar-bills list once collapsed its number
    column in every state. Class names shared by unrelated parts: chart legends' `.key` (nowrap) also styled the
    contact card's `li.key` and pushed IL and NJ panels sideways; the co-sponsor list's `more` took the "Show more"
    button's box. Check `document.documentElement.scrollWidth` with a bill open.
  - A field that names the wrong house: a few of WY's roll calls say "H" for a Senate vote ("S Introduced and Referred to
    S04 ..."); senators then looked like House voters who didn't match a seat. Take the house from the action's text.
  - A member a roll-call page counts but never names: AR's 2023-24 pages leave out Sen. Alan Clark in every group (29
    votes listed fewer noes than their tally). When the unnamed are exactly the house's members missing from all groups
    and one group is short, they belong there; the "fewer noes than their tally" check catches it.
  - Lists split on commas when names contain commas: WY's "Brown, G, Larson, JT, Burkhart, Jr" (initials, suffixes and
    first names belong to the name before). Count each vote list against its tally.
  - Folder listings whose dates are on the server's local clock (TX, IL, MI): when daylight saving time ends or starts
    every file's time moves an hour, so every file looked changed and runs downloaded everything again (2026-11-01:
    Texas took 41 minutes, Illinois ran out of time). `listing_dates.same()` treats the same size an hour apart as
    unchanged; use it for any download that compares listing dates.
  - A roll call that lists a member twice: CO's Senate President by name and as "President" (drop the title line when the
    list is longer than the tally), and members who changed their vote, listed "Yes" and "No" (f21664 of 2025: leave them
    out; which came last isn't shown). The "more noes than their tally" check catches both.
  - A past year's member list showing today's positions and houses (CO: Lisa Frizell, a representative in 2024, listed as
    a senator; James Coleman as 2024's Senate President). Don't take past leaders from it; match votes within the vote's
    house and leave the rest as names.
  - Stray records from links cut short: CO's site answers "HB25-104" with a jumbled page instead of an error. Check
    numbers against the state's numbering (House bills from 1001).
  - Bills the Legislature sends to the voters instead of the governor (CO's SB26-135, a TABOR question: status "Adopted",
    no governor's action) looked like bills waiting on the governor. The converter marks them `ballot`; the page says
    "Sent to the voters, not the governor" and leaves them out of the governor's count. The "passed both houses but not
    sent" LOOK line finds them.
  - Failed motions worded like the step: IN's "Referred to Committee on Ways and Means pursuant to House Rule 84; Failed,
    Roll Call 185: yeas 28, nays 59" is a motion that lost, not a referral. The check fails on committee names carrying a
    motion's wording ("Failed", "Roll Call", "pursuant to").
  - Steps that undo "passed both houses" (2026-11-08, one bill each, found by the "passed both houses but not sent" LOOK
    line): a house asking for a passed bill back (MI SB 6 of 2023: "House requests return", "ENROLLMENT VACATED"); a
    concurrence "as amended by the House" (PA HB 27 of 2023: the other house must agree again); a concurrence reconsidered
    and refused (TX SB 155 of 2021, codes S706 then S605/S711); a conference report one house rejects (GA SB 13 of 2023-24:
    a later report needs both houses again). And a pocket veto is a veto (MI HB 5190 of 2023-24: "pocket veto 1/22/2025").
  - An official file that's out of date: NH's HouseDistricts.txt still has the 2012 map (Belknap has 9 districts there, 8
    in the law and the member list); the districts come from the law (RSA 662:5). The check fails when a legislator's
    district isn't in any place's list in "Find your legislators". And NH Members.txt's electedStatus "Former" is on 18 members
    still sitting and voting.
  - Typos in a line's year: NH's HB 425 of 2025 "03/06/2035", HB 49 of 2023 "04/13/2022" (the entry time is used when
    they're more than 180 days apart). The check fails on history dates years from the session.
  - The same number written twice, differently: NH's history lines give SB 62 and HB 511 of 2025 both "Chapter 39" (the
    LSRs file's column says 38 and 39). Prefer the structured column; the check LOOKs at law numbers given to two bills.
  - Lists carried onto the next history line: AK's "CROSS SPONSOR(S): TOBIN, ..., GRAY-JACKSON," then "KIEHL, ..." (and its
    committee reports' "DP: ..." lists). Join them before reading; the check LOOKs at history lines ending in a comma.
  - Land shares that drop small districts: a municipality as big as Anchorage holds whole urban districts under 0.5% of its
    land. Keep a district the place holds most of; the check that every legislator's district is in some place's list caught it.
  - A failed refresh marking a state "incomplete" takes it off the site (Utah on 2026-11-08, its API answering 504;
    Georgia the same day, 2 of 2,288 bills failing). Only data never downloaded may mark a state incomplete; a failed
    refresh keeps the last copy, and votes still to read fill in on later runs.
  - Law numbers on bills that aren't laws: ND's Session Laws give vetoed measures chapter numbers ("Measure Vetoed": HB 1273
    of 2023, chapter 586). Decide laws from the history; the check fails on a law number on a bill that isn't stage 5.
  - History lines that don't say which house acted (ID): the converter follows the bill from house to house, and a slip
    puts a vote in the wrong house. The check fails on floor votes with more ayes and noes than the house has seats.
  - Substitutes written with both names in a different order in each house (ID: House "Hill(Brown)", member first; Senate
    "Coho(Lenney)", substitute first). The check fails on unresolved vote names with parentheses.
  - A procedural vote recorded on a line that reads like the bill's step: AL's "Third Reading in House of Origin" carries the
    roll call on the bill's Budget Isolation Resolution, taken just before the passage (and 2024's passage lines sometimes
    carry the BIR's number in their roll-call field; the line's text has the right one). The check LOOKs when more than half
    the bills with floor votes have two in one house on one day (CO and VA reach about a third legitimately).
  - A passage held by a motion to reconsider and never released (MS: "Motion to Reconsider Entered" after "Passed", then
    "Died On Calendar" in the same house: HB 1602 of 2026). The vote never took effect; the check fails on bills shown as
    passed by one house that then died in that house's committee or calendar.
  - A history that copies another record's lines under the day they were copied: DE's bills carry their substitutes' lines
    ("HS 2 for HB 168 - Signed by Governor" 10/2/24; the substitute's own page says 9/30/24). The check fails (LOOK under
    1%) on bills with the governor's action on two different days.
  - Records that look like votes but aren't (found by the "passages whose floor votes all failed" check, 2026-11-13): AZ's
    Open States records list the Committee of the Whole's voice vote as "PASSED" on the day the third-reading vote
    failed (HB 2044 of 2024, failed 18-40; about a hundred bills a year showed as passing the House); AR served an empty
    roll-call page (SB 16 of 2026's House vote: no counts, no names) that read as a 0-0 vote.
  - When editing code with a script, check the file's size afterwards. A bad Python edit once emptied convert.py.
  - A result field that says passed on a lost vote: MT's current system marks some failed third readings "BILL_CONCURRED"
    (HB 93 of 2025: 24-26; ties too), after a second reading that passed, so not every vote in that house lost. Decide from
    the roll call; the check counts "PASSED" lines whose same-day floor votes in that house all had no more ayes than noes.
  - A line laws and vetoed bills share: KY's "delivered to Secretary of State" follows a veto override ("(Acts Ch. 175)")
    and also a veto after the session (SB 70 of 2026, no chapter): read as an override at first. The check lists laws with a
    veto date and no override line (LOOK: on 2026-11-08 it also lists 43 NC laws of 2023-26, WA SB 5017 and SB 5810 of 2021,
    NJ A4975 of 2020, not yet looked into).
  - A roll call's result field that's the same for every vote: NV's records call each final passage "Passed", lost ones
    too (AB 500 of 2025: 25-17, short of the two-thirds it needed). Decide from the history line ("Lost."), and match roll
    calls to it by house, day and tally; the check LOOKs at houses shown as passing a bill where every floor vote there had
    more noes than ayes (the 25-17 kind only the history shows; in NH and ME a vote on a motion against the bill, "Inexpedient
    to Legislate" or "Ought Not to Pass", loses that way when the bill survives).
  - An official list and history that miss a veto: NV's SB 99 of 2025 was vetoed June 2, 2025 (with a message to the
    Senate), but NELIS shows it delivered and then "(No further action taken.)", and its vetoed list leaves it out (86;
    the press counted 87). Don't infer an outcome from the constitution's default (law without signature): keep a
    documented correction (`VETO_FIX`) and say "no decision recorded" otherwise. The check's "on the governor's desk"
    count for a finished session should be 0, and vetoes per year should be compared with the press's count.
  - A concurrence that isn't the repassage: MN's "Senate concurred" (agreeing to the House's amendments) is followed by a
    separate repassage vote, which can fail to happen (SF 4225 of 2023-24: "due to the constitutional deadline the bill was
    not passed"). And a second house that amends a bill to match its own (MN's Rule 45) and then passes it "plainly" still
    needs the first house's agreement. The "passed both houses but not sent" LOOK line found both.
  - A roll-call surname that names different members over a session: NE's "Meyer" was Glen Meyer (District 17) until Fred
    Meyer joined in January 2026, after which the lists write "Meyer, F." and "Meyer, G." Matching plain "Meyer" by surname
    alone fails or picks one; check who else is on the list (McKeon, the seat's earlier holder) and keep a documented fix
    (`VOTE_NAME_FIX`). The check fails (LOOK under 0.5%) on roll calls naming one seat twice.
  - Fonts whose ligatures come out as U+FFFD in PDF text (MN's Senate summaries: "Ar\ufffdcle", "par\ufffdcipa\ufffdon"): put
    back the letters that make words the other texts use. The "wrongly decoded characters" check caught it.
  - The same record written twice, disagreeing: NM's spelled-out action line says "Chapter 6" for SB 5 of 2025 and "Chapter
    138" for SB 45, while the coded ActionText says 9 and 139 (which run 1-160 with none repeated). Prefer the code; the
    "law numbers given to two bills" LOOK line caught it.
  - A record from an earlier session filed under a new one: MO's House exports put the previous year's budget bills (same
    numbers, HB 1-20 or HB 2002-2020) in each new year's folder with only the governor's spending restrictions ("Message
    Received from the Governor, pursuant to Article IV, Section 27", dated before the session); read as bills they'd be a
    dozen stray records, or vetoes. The check LOOKs at bills in a finished session whose whole history comes before the
    session's first year (MO's few left are bills prefiled and withdrawn before January; on 2026-11-13 it also lists
    VA 2025's 374 bills continued from 2024 and SC 2023's 510 bills prefiled in December 2022, expected, and GA HB 2 and HB 10
    of 2023, NH HB 333 of 2024, TN SB 6 of 2023, not looked into).
  - A law number on the wrong bill: WV's HB 4756 of 2026, never out of committee, carries HB 4755's "Chapter 104, Acts" line,
    and the completed list's chapter column has its own slips (SB 75 of 2025: 226 there, 220 in its history). A chapter
    never makes a law by itself: decide laws from the governor's actions and lists, and keep a chapter only on a law. The
    "law numbers given to two bills" LOOK and the "law number on a bill that isn't a law" FAIL catch both.
  - A record's kind that disagrees with its title: SC's bill search lists S 729 of 2025-26, "A CONCURRENT RESOLUTION TO
    REQUEST ...", as a General Bill (it showed as passed both houses and never ratified). Decide what's kept by the title;
    the check fails on records whose title says they're resolutions (other than constitutional amendments).
  - A member list that gives each member's district in the office they hold now: SC's 2023-24 House list puts members since
    elected to the Senate in their Senate districts (Russell Ott "26", shared with Raye Felder), and Wes Climer, now in
    Congress, in Senate District "5" (his U.S. House district), shared with Tom Corbin, so Senate 15 looked vacant. Correct
    with the member's home county and the districts the list leaves empty (`DISTRICT_FIX`); the check LOOKs at names voting
    in the last four months of the newest session's roll calls that aren't tied to a seat.
  - A roll call filed under the wrong bill: KS's vote records carry their own bill number, and two 2026 Senate line-item
    override votes on the budget (HB 2513) say HB 2315, a bill that never left committee (another has none). NY's Senate API does it too (S2347 of 2025, in committee, with a June 2026
    floor vote; S810 of 2025, signed in March, with one in June): a Senate floor vote with no action of the bill's within
    three days is dropped (`DROPPED` in states/ny/convert.py lists them: about one to three a session). Tie votes to
    the history line they belong to (action, house, time); the check LOOKs at bills that never left committee but have
    floor votes (on 2026-11-13: WY's budget-session votes to introduce a bill, expected; MI HB 4195 and "HJRU" of 2025, NH
    HB 565 and HB 620 of 2023, NY S2347 of 2025, not looked into).
  - A summary of a version another bill's contents replaced: KS conference reports often carry other bills' contents, and
    the supplemental note describes the bill before (HB 2043 of 2025-26: insurance as passed, property tax as law). The check
    LOOKs at laws whose summary shares almost no words with their title.
  - (2026-11-16, found when 2023 was added) A roll call listed twice under one id, its name lists doubled: WY's SF 22
    of 2023 (voteID 345 twice; "Biteman, ..., Steinmetz, Biteman, ..., Steinmetz") and SF 71's veto override (voteID
    5600, first labelled "Amendment Reconsideration Motion"). `roll_calls()` in states/wy/convert.py keeps a floor
    voteID's last copy and reads a list that is the same list twice once. The "more noes than their tally" check caught it.
  - A history tally that can't be right: NM's SB 142 of 2023, "Passed in the Senate - Y:26 N:19" in a 42-seat Senate;
    the roll call lists 22-19 by name (and HB 165 of 2026 "30-0" for 30-10). `floor_votes()` in states/nm/convert.py
    takes the house's only roll call that day, when its names add up to its totals, and the history line says what the
    record wrote. The "more ayes and noes than seats" check caught it.
  - Stray bytes in pages that say UTF-8: NY Assembly memos carry single 0x95 bytes where a space belongs ("to be
    known\x95as"; 518 of 2025's), decoded with "replace" as U+FFFD; `states/ny/memos.py` reads them as spaces and reads
    those memos again. And PDFs whose own text is mojibake (NE's committee statement for LB 94 of 2023: "Commissionâ€™s",
    "â€œminorâ€•"): `unmangle()` in states/ne/texts.py. The "wrongly decoded characters" check caught both.
  - A finished session's bulk file that stops before a later override: MD's 2025 bill list (saved 2025-12-01) still says
    "Vetoed" for the 19 bills (of 29 vetoed) that became law over the veto in the special session of 2025-12-16, and it
    has no dates for the governor's actions (each law and veto showed on the bill's last legislative day). Read each
    passed bill's page (states/md/NOTES.md); the check LOOKs at laws and vetoes with no date for the governor's action.
  - A refusal worded like the agreement: MA's "House NON-concurred in the Senate amendment" matched "concurred in the Senate
    amendment", so 13 bills of 2025-26 in conference (H5576, S2619) showed as passed both houses; a second house's "Read
    second, amended" was missed too (H1999 of 2023-24). The check fails on bills passed both houses whose last step is a
    refusal to concur or a conference committee.
  - A line read by its opening words when it ends in another step: WA's "Rules Committee relieved of further consideration.
    On motion, referred to Ways & Means." read as placed on the floor (17 Senate bills of 2025-26, SB 5659); the referral wins.
    And a referral to a committee the session's list no longer names (renamed) was kept as text (9 WA bills of 2023-24).
    The check LOOKs (FAIL over 0.5%) at bills on the floor whose last line refers them to a committee.
  - A change marker that doesn't change: OH's legislation list keeps a bill's `revno` when it's enrolled or sent to the
    governor (HB 13 of the 136th, sent 2026-11-17), so versions read only on a new revno missed every delivery. fetch.py
    reads versions again when the actions change or the bill waits on the governor (`waiting()`). No data check can see
    it; the accuracy check against the API found it. And OH laws of a running session with no signing date (SB 152, HB 479
    of the 136th): a "Line item veto receipt" or the enrolled version's effective date is the law, while it runs too.
  - (2026-11-19) One house's override sorted after the other's sustaining vote: NH's SB 434 of 2026 (Senate overrode, House
    sustained) showed "VETO OVERRIDDEN" as its last action though the veto stood. `decode()` in states/nh/convert.py reads
    "Veto Sustained" as its own step, placed last in the day; the check fails on vetoed bills whose last action reads as an
    override when the history has a sustaining vote.
  - (2026-11-19) A last action's day taken from lines the history leaves out: IA's and HI's converters dated bills by
    paperwork they hide ("Subcommittee: ...", floor amendments filed; IA's HF 29 of 2025), so status rows on /your-bills/,
    /list/ and the front page had a date and no wording (523 IA, 257 HI bills). "last" is now the latest shown line's day;
    the check counts bills whose last action's day has no history line.
  - (2026-11-21) An official bill page silent on the outcome: Maine's pages for LD 25, 2205 and 2210 of 2023-24 name no
    governor's action, chapter or final disposition; the Law and Legislative Reference Library's legislative history says
    "Enacted, Held by Governor 05/22/24" (pocket vetoes). When the legislature's own page is silent, look for a second
    official source (a state law library, the session laws, the journal) before showing "no outcome recorded"; states/me/laws.py
    now reads the Law Library's history for such bills itself. The "on the governor's desk in a finished session" count finds them.
  - (2026-11-19) An aggregator's "Passed" on bills the governor held until the Legislature ended: LegiScan calls 36 of Maine's
    2023-24 veto-day bills passed; their official pages say "Held by Governor" and "Died Upon Conclusion of the 131st" (32,
    pocket vetoes) or nothing (3). Read the official page (states/me/laws.py) and re-read robots.txt rather than trusting an
    old note that it bars everything. The check LOOKs at laws whose history ends with the governor holding them.
  - (2026-11-21) Messages that arrive after the action: NY's veto messages reach the Senate API days or weeks after the
    veto (S1239 of 2025, "VETOED MEMO.19" on 2026-11-20, had none that day). fetch_bills.py --if-changed still downloads
    them (the updates list counts "Bill Veto" updates). The check LOOKs at vetoes 2 weeks to a year old with no message,
    in any state whose vetoes carry them (pocket vetoes left out: NY's say "no veto message issued").
  - (2026-11-21) A year the window added back, in an older wording the converter was never written for: ALISON's 2023
    history ("Introduced and Referred", "Read a Third Time and Pass", "Assigned Act No. 2023-291.") was read as other
    lines, so 46 bills that passed one house showed as on its floor; its "Pass" lines include lost votes (SB 181, 11-20).
    `old_wording()` in states/al/convert.py. When the window adds a year, list its history wordings against the newest
    year's. The "on the floor but referred to a committee" check caught it.
  - (2026-11-21) A record's fallback date in the future: a bill listed but with no history yet (NV's prefiled bills whose
    pages a run didn't reach, AB 69-80 of 2027; MT's SB 32 of 2027, numbered with only drafting steps) was dated the
    session's first day, months ahead. Every converter's load_session() now ends with `settle()` (states/undated.py): a bill
    with no dated history line and a future "first"/"last" takes the UTC day its own file (bills/AB69.html) or else the
    session's bill list was last written, today only when no file is found. Not today itself: that moved the bill's date
    every day (sorts, status files, shards). A new converter must call it too. (A fetcher that rewrites its list every run,
    as NV's does, moves such a bill's day with each run until its own page is read.) And a source's typo a month ahead:
    MA's histories sign H4716, H4721, H5685 and S3097 "2026-11-30" (the session laws say October 30): a line dated after
    its file was read takes the law's date, else the read day. The "in the future" check catches both.
  - (2026-11-22, a coverage audit of the live site) A copy on the owner's computer that GitHub's doesn't match: CO's local
    data had every floor vote, GitHub's none, because pages a download can't save (about 900 committee voice votes) were
    read again first every run until time ran out. Save what a page says even when it's "nothing to record", read the most
    important records first, and compare a state's live pages with a local build (`copy-data.yml` hands GitHub's copy over).
    The check fails when under a fifth of the bills that passed a house have a floor vote.
  - File names that collide: PA's House and Senate roll calls are both numbered from 1 (`rcNum`), and files named by the
    number alone kept one house's out; the Senate's votes showed tallies without names. The check fails when one house's
    split floor votes name members far less often than the other's. And files downloaded but never read: MO's House
    Journals were fetched all along while the converter said they weren't.
  - Contacts emptied after an election: SD's API cleared the outgoing session's emails and phones; Open States' "current"
    file (NV's emails) moved to the members-elect. A refreshed list keeps the last copy's fields; the check fails when the
    current session's contacts have email (or form), phone or page for under half the members (`CONTACT_GAPS` lists what a
    state's sources never had).
  - Page wording built from written-out lines: billfacts.js's `plainAction()` turned Congress's "Referred to the Committee
    on ..." into "Referred to the The Committee On ... Committee" in every status row; Maine's own lines say "the The
    Majority ... Report". The check fails on "the the" in history lines.
  - (2026-11-22) An aggregator's hearing list that keeps canceled hearings and names the wrong committee: LegiScan's
    Tennessee `calendar` field kept 218 hearings of 2025-26 after the bill was taken off notice or the meeting canceled, and
    named the wrong committee on 1,021 of 6,985 (mostly "Senate Revenue Subcommittee of Finance, Ways & Means"); Rhode
    Island's kept hearings the history postpones. The bill's own history ("Placed on s/c cal ... for 3/18/2026", "Taken off
    notice") decides (states/legiscan_convert.py's `history_meetings()` hook). Look in histories for announced meetings when a
    state's agenda source is missing or weak (Tennessee's House hearings were only there).
  - (2026-11-22, when roll-call PDFs were read in MS, KY, MD, MA, MI and TX's HRO reports) A total that disagrees with its
    own names: MS's override vote on HB 1924 of 2026 lists seven absent members under "Total--5" (110 + 0 + 5 + 7 = 122, the
    whole House). Keep names only when every group adds up, or the yeas and nays do and every seat is named once. And the
    names must add up to the house: the check FAILs when a floor vote's ayes plus the members it names are more than the
    house's seats, and when a floor vote falls on a day the bill's history has no line for.
  - A watermark read as a name: MD's reposted roll calls are stamped "- COPY -" under the names (2026 Senate SEQ 6-8, 15).
    And roll calls dated by a legislative day weeks behind the calendar (MD: a Senate vote of April 10, 2026 is legislative
    day March 24): match and date by the day the history uses.
  - A bill's vote file holds every roll call on it: KY's vote_history.pdf lists amendment votes ("HB 1 HFA 6"), "Table",
    "Suspend the Rules" and "Previous Question" the same day as the passage, and two passages can have one tally on one day
    (HB 2 of 2026, Senate, April 1). Match on the bill's own number, the motion and the tally; give each roll call to one line.
  - A name with a comma in a comma-separated list: TX's HRO VOTE lines write "Curry, Garcia, Linda, Olcott" (CSHB 149 of 2025).
    Join a pair that is a member's name; drop a group whose names don't number its count.
  - A roll call whose column runs past its heading: the Michigan Senate Journal's Roll Call 217 of 2026 prints two yeas under
    "Nays—0". When a group has more names than its count and the group before is short by as many, they belong there
    (states/mi/journals.py). And MI House roll calls name only yeas and nays: the others come from that day's opening roll,
    kept only when it leaves exactly the right number of members.
  - A member list the legislature stopped updating: MS's ss_membs.xml (Last-Modified 2025-07-01) and member files still have
    members the November 2025 special elections replaced, while 2026's author lists and roll calls have the new ones (DuPree,
    Hartness, Crosby ...). The "names voting in the last four months aren't tied to a seat" LOOK found it.
  - (2026-11-23, an audit of every line the site writes in its own words; test/wording_check.js runs tracker.html's own
    wording code on every state's bills from data_check.py, "wording:" lines) Words that claim more than the record:
    - The second-year reset: "Sent back to committee for the new year" for every New York bill, while Assembly bills go back
      to the floor calendar (A836 of 2025) and some to a committee (A5577B: Ways and Means). Each state that resets
      passages says where from the record (`STATE.resetLine(b, short)`: NY reads the day's lines; WA's Rules Committee);
      the check fails on a state with resets and no resetLine, and on a line naming a committee or calendar the day's
      lines don't.
    - A committee vote's count isn't its result: a committee needs a majority of its members (CA's 8-0 with 11 not voting
      failed, AB 273 of 2021; TN's 4-3), a vote to reconsider isn't a vote on the bill (CA's "Reconsideration granted"),
      and a motion against the bill carries with its yeas (SD's "Deferred to the 41st legislative day" and "Tabled", 571
      votes in 2024-26; UT's "Held"; CO's "Postpone Indefinitely"): all read "Approved by". Votes on amendments in
      committee read as the bill's (PA's "Adopt Amendment", 9-12 "Voted down" the day it was reported). Converters keep
      only votes on the bill, turn round votes against it (as ND's), and give the result where the count says otherwise
      (vote[7]: "P"/"F", "RP"/"RF" reconsideration; CA, SD, LegiScan's `passed`). The check fails on committee votes
      read as carried on a day the record says the bill failed there.
    - "Signed into law" for laws the record doesn't show signed: AL's laws carry only "Became law: Act 2025-403"; NC's
      local acts aren't presented to the governor; UT's "Became Law w/o Governor Signature" was mapped to SIGNED; VA's
      "Enacted, Chapter N" (the governor's amendments accepted) was "SIGNED CHAP."; and
      stage 5's name "Signed into law" counted laws over a veto or without the signature. The page says "Signed" only
      with a signature line (`signedLaw()`); the check fails when a profile names stage 5 "Signed ..." and a law isn't.
    - "Approved by committee and sent to the floor" for bills taken out of committee (NY's Senate "COMMITTEE DISCHARGED"),
      reported without a recommendation (NV, NM, MN, WV), placed on the calendar "without going to a committee" (SC, a
      fifth of its floor dates) or with no committee step at all (Congress's Senate calendar, MA's "Rules suspended"), and
      UT's "Substitute Recommendation" followed by a failed motion to recommend read as a report (HB 109 of 2024 died in
      committee). `floorLine()` reads the record: an approval that day or in the two weeks before, else what it shows.
- **Hawaii (built 2026-11-15, from Open States)**: see states/hi/NOTES.md.
- **Iowa (built 2026-11-15; official pages, else Open States)**: see states/ia/NOTES.md.
- **Congress (/us/, built 2026-11-16; on the front page's list, not its map)**: see states/us/NOTES.md.
- **National issues (built 2026-11-15):** the same subjects across states, sixty-five of them: data centers, PFAS, AI, children
  online, phones in schools, housing supply, minimum wage, right to repair, sports betting, prescription drug costs (the
  first ten, chosen in notes/issues-draft.md with the owner's answers), and abortion, firearms, school vouchers and
  education savings accounts, voting and elections, immigration (named "Immigration enforcement" until 2026-11-17; the id
  is still "immigration"), rent and tenants, property tax relief, transgender people, diversity, equity and inclusion,
  cannabis (the second ten, added the same day), and data privacy, campaign finance, redistricting, paid family and sick
  leave, child care, IVF and fertility, fluoride in drinking water, nuclear energy, wildfire, noncompete agreements (the
  third ten, 2026-11-17, after the owner's answers on the second ten), and short-term rentals, water rights and supply,
  psychedelics, crypto ATMs, Medicaid work requirements, daylight saving time (group "", shown under "Other"), book
  removals in schools and libraries, medical debt, police accountability, death penalty (the fourth ten, the same day),
  and vaccines and public health powers, unions and collective bargaining, ballot initiatives, ranked-choice voting
  (nearly all ranked-choice and about two thirds of initiative bills also match voting), energy costs and utility
  rates, climate and clean energy, ESG investing and boycott laws, religion in public schools, child labor, protest and
  assembly laws, and kratom (the fifth ten plus one, the same day), and health insurance coverage, sexual assault and
  domestic violence (the sixth batch, with PFAS's "Sludge on farmland" filter and Voting's "Presidential electors and
  popular vote"), and homelessness and camping bans, income tax cuts, homeowners insurance, bail and pretrial release, drug
  penalties and overdoses, contraception, mental health and 988, food additives and dyes, school meals, plastics and
  packaging, heat protections for workers, same-sex marriage (the seventh batch, the same day). Groups (`GROUPS`) include
  "Drugs" (cannabis, psychedelics, kratom, overdoses). Each issue may have `words`, a few extra terms for the front page's search (not used for matching).
  Each one's scope, the checks, the owner's answers
  and open questions are in notes/issues-check.md. `issues.py` holds each issue's rules (patterns that must appear within
  400 characters of each other, exclusions, filters such as AI's "Chatbots"); a match in the title or summary counts, one
  only in a long "What it does" needs two mentions (budget bills name subjects in passing), or as many as the issue's
  `"body"` says (`0`: the title or summary must name it; homelessness, income tax cuts, bail, assault, plastics); for those
  issues the opening of "What it does" (`lead()`) counts like the summary, except school meals (`"lead": False`). Minimum wage is only bills
  that set or change one (the owner's decision). Each state's build writes data/issues_<session>.json
  (`write_issues()` in build_data.py; local and placeholder bills left out); `issues_site.py`, run by build_site.sh
  after the states, builds /issues/ and /issues/<id>/ (a table by state, every bill linked to its state's page, filters)
  and issues/summary.json (each issue's counts by state). The front page's map has a "Show" menu: party control, or an
  issue, which shades each state by its bills on it (none, 1-4, 5-14, 15 or more; a gold mark where one became law) and
  links each square to the state's bills on the issue page (the owner's choice 2026-11-15: no issue cards on the front
  page), with a Year menu: counts are by calendar year (last year, this year, and next year's prefiled bills once any
  state lists them; a bill counts in the year it was introduced, its session's first year at the earliest, and if it
  became law in that year too), each square showing the number that became law (the owner's choice: a number, not a
  dot; "became law", not "signed", since many aren't signed); `#issue=ai&year=2027` in the address picks one. Each
  state's build writes data/issues_<session>.json for every session it shows. The front page's controls (2026-11-15, the owner's
  choices): year buttons first (for party control, this year is now and next year the reported 2026 election results,
  replacing the old Now / From January switch; last year has no party view), then the Show menu. Party control colors
  each state: red or blue when one party holds the governor and both houses (darker with a supermajority in both),
  purple when split, grey for Nebraska; states not on the site are outlined. With an issue shown, a panel beside the
  map (below it on a phone) lists the bills of the state pointed at, or clicked to keep it open
  (issues/<id>/bills.json, from issues_site.py). Each issue page leads with the same map, the table under "Show as a
  table", and one menu (all bills, became law, still moving, the issue's filters). A second menu, "Sponsor's party"
  (approved by the owner 2026-11-17, to tell apart, say, transgender bills that restrict from those that protect, with
  party as an honest stand-in), filters by `sponsor_class()` in build_data.py (each issues row's last field): "D"/"R" when
  every prime sponsor with a known party is of that party; "B" when the primes include both, or the other party has at
  least one in five of the bill's sponsors and co-sponsors with a known party (one Democrat among twenty Republican
  co-sponsors isn't bipartisan; a Republican and a Democrat alone are); "" for committee bills, bills by request, unknown
  parties and Nebraska. Only Democrats and Republicans count (independents don't make a bill bipartisan). On an issue
  page both menus now drive the map's shading, the counts line and the table (counted in the browser from the list's
  items); a ⓘ note explains. The front page's panel has the same menu (`#pparty`, `PARTY`, `#...&party=R` in the
  address); the map follows it, counted from bills.json (rows carry the class and whether they count in the year's bills
  and laws), so summary.json stays small. Each bill in the panel and on the issue pages carries a small badge before its
  stage, "D", "R" or "Both" (none for committee bills), in the map's muted party colors (`--ctl-d1`, `--ctl-r1`). Past
  sessions with no parties of their own (Virginia's; California's now come from each session's LEGISLATOR table) borrow
  a name's party from the other sessions shown when they all agree (`other_party` in main()). In a build of CA, NE, NY,
  TX, VA and Congress (2026-11-17): transgender 65% D, 28% R, under 1% both, 7% none; abortion 57/28/2/13; firearms
  57/30/6/7. Check a rule change with test/issues/get.py and check.py (30
  random matches and possible misses per issue; notes/issues-check.md has both checks: 26-30 of 30 right).
- **Find a bill (built 2026-11-17):** a search box on the front page's controls row (its own line on a phone; results
  open over the map). `search_site.py`, run by build_site.sh after issues_site.py, writes search/<st>.json for each
  built state and Congress from its live data/status_<session>.json (the current session and next year's prefiled
  bills; past sessions left out, as they'd more than double the download): number, title cut at 110 characters, stage,
  "c" for an amendment, the record's other numbers. home.html loads nothing until the search box is focused, then
  every state's file, the most populous first (`BY_PEOPLE`: Congress, California, Texas ...), four at a time (2026-11-18);
  a query naming a state ("texas data center", "NY A5663"; two-letter codes that are words, "in", "or", "me", count
  only in capitals) or one picked in the results loads that one at once. Results update as each file arrives. Numbers in any form ("H.B. 1234", "hb1234"; "HB" also
  finds "H", "LD" Maine's "HLD"; aliases such as NY's other house's number) come first, then bills whose title has
  every word (a word matches the start of a title word; three letters or fewer only whole); bills with most of the
  words show only when none has them all ("No bill has all those words; these have most of them"), rarer words
  first. 50 at a time; each with its status label and a star that writes the state's watchlist (with the last
  action's date from the status file). Size: 50,000 bills (NY, NJ, TX, VA, US) are 0.9 MB brotli; all states should
  be about 3 MB the first time someone searches every state.
  **Earlier sessions (2026-11-22):** an "Earlier sessions" checkbox in the results' head (remembered in abt:searchpast)
  also loads search/<st>.past.json (every other session the state's site shows, newest first; a state whose earlier
  sessions are over 600 KB gzipped, as New York's, puts the others in search/<st>.past.<session>.json, named in "more"),
  most populous first, four at a time. Their bills come after this session's under "Earlier sessions", each with its
  session's label, linking to that session's page (#<num>) with a star for that session's watchlist; "Show on the map"
  then counts every session, and the panel groups a state's bills by session, newest first. Sizes (5 states, brotli):
  past 1.8 MB vs. current 0.7 MB; all states' past files should be about 7 MB, about 60 files.
- **How the states compare (built 2026-11-19, approved by the owner):** each state's build writes data/compare.json
  (`write_compare()` in build_data.py): every finished session's odds chart numbers (`reached()`, as `insights()` counts
  them) one session at a time, without shells, narrow bills and constitutional amendments; as a check, the same counts with
  the amendments kept, summed over the Statistics tab's sessions, must equal its "general bills" odds chart (a mismatch is
  printed as "compare: ..." in the state's build log). `compare_site.py`, run by build_site.sh after issues_site.py, writes
  /compare/ (one sortable table, a row per state, Congress apart; a menu for the latest finished session, all since 2023,
  or sessions that began in a year; the odds chart for one state or two, stacked) and compare/summary.json, which
  build_site.sh puts in the front page for the map's "Bills that became law" (a CUSTOM view, `lawsView()` in home.html:
  shaded under 10%, 10-24%, 25% or more). The odds chart's drawing is `drawSankey()` in lists_pages/sankey.js, shared by
  tracker.html's `sankey()` (build_data.py puts the file in each page) and /compare/; its styles stay in each page.
- **"What it does" from a bill's own text (2026-11-22):** for bills with no official summary, `states/billtext_lead.py`
  quotes the bill as written, no AI: its statement of intent ("It is the intent of the legislature to ..."), the opening
  sentence of each section that makes new law (skipping definitions, effective dates, severability, short titles,
  appropriation boilerplate), or the whole sentences an amendment adds (underlined), else "Amends RCW 59.12.040."; only
  whitespace and section numbers change, a long sentence is cut at a clause with "…". Paragraph plus "• " lines (as other
  states' lists), label "From the bill's text as introduced: its statement of intent and the opening of its new sections."
  (worded for what's there). Shared readers: `paragraphs()` (HTML with underline/strike), `split()` at "SECTION 1." marks.
  Wired in WA (bills with no bill report), AK and MA (no summaries); measured and left out: MS (long titles already say
  it, and quoted sections of restated law misled), OK (LegiScan getBillText would cost about 11,000 queries).
  States cache sections (not leads) in data/<st>/<session>/leads.json, so a rule change needs no download. data_check
  fails (over 1%) on leads that are boilerplate, over 1,200 characters, or the title's words again.
- **Hosting (set up 2026-10-29):** statebilltracker.org will be served by Cloudflare Pages (project
  `statebilltracker`), not GitHub Pages. `./build_site.sh [DIR]` builds the whole site: `home.html` (the
  list of states) at the top, the icons, and each state's public site in its folder (`--github DIR/<state>`).
  Until launch it writes `robots.txt` and `_headers` telling search engines not to list anything (`LAUNCHED=1`
  turns that off). Two workflows (split 2026-11-07, so nothing waits on anything else):
  `.github/workflows/download.yml` downloads every 2 hours in two lanes (2026-11-14): a quick lane (states whose last three downloads each took 30 minutes or less; about half an hour a run, then publish.yml publishes) and a slow lane (first copies and crawl delays; it doesn't publish, its data goes out with the next quick publish), the lane decided at each run's start from the run history, so a state moves to the quick lane by itself; (each full run starts the next, two hours after it began, since GitHub's scheduler skips runs; the schedule is only a backup), each state in its own job and cache (a state's runs never
  overlap; states never wait for each other; a copy is saved only when something changed); its states, commands and time
  limits are in `.github/states.json`. Test one state without touching the site: `gh workflow run download.yml -f
  states=wi`. `.github/workflows/publish.yml` builds from every state's latest saved copy and deploys after each download run (a `workflow_run` trigger, not a schedule)
  (about 360 deploys a month; Cloudflare's free plan allows 500) and by hand (`gh workflow run publish.yml`, for a design change); it rebuilds only the states whose data, code or
  settings changed (`state_hash.py`, which includes the date, so each state is rebuilt at least daily; a change to page code
  alone reuses what build_data.py worked out from the data, kept in `built/cache/`: ARCHITECTURE.md) and copies the rest
  from the last build (the `built/` folder, kept in its cache; `ONLY="wy sd" ./build_site.sh` builds a few states locally); the data checks run in its 10:50 UTC run or with `-f checks=true`. A new state needs an
  entry in states.json and a restore step in publish.yml (check_site.py fails if one is missing); it needs the
  secrets CLOUDFLARE_API_TOKEN and CLOUDFLARE_ACCOUNT_ID. The domain stays parked at Porkbun until launch.
  Until then the site is at https://statebilltracker.pages.dev/ (first put up 2026-10-29, built with
  `SITE_BASE=https://statebilltracker.pages.dev/` (each state's SITE_URL is SITE_BASE/<state>/); unlisted, and marked noindex). It's a classic Pages project
  (created with `--force`, which isn't needed again). Deploy by hand from an empty folder, never from
  lists_worker/ or cron_worker/ (wrangler picks up that folder's wrangler.toml):
  `npx -y wrangler@4.152.0 pages deploy <repo>/_site --project-name=statebilltracker --branch=main --commit-dirty=true`.
- **Launched 2026-11-21.** statebilltracker.org is a Cloudflare zone in the owner's account (nameservers aurora and randall
  .ns.cloudflare.com, set at Porkbun; registration stays at Porkbun) with the Pages project's custom domains
  statebilltracker.org and www.statebilltracker.org; statebilltracker.pages.dev serves the same files. statebilltracker.com
  forwards with a Porkbun 302 (path kept). publish.yml builds with SITE_BASE=https://statebilltracker.org/ and LAUNCHED=1
  (search engines allowed, GoatCounter on). **New York moved here 2026-11-22:** albanybilltracker.org (the
  AlbanyBillTracker repo's main, merged from move-to-statebilltracker) now serves only forwarding pages that carry each
  visitor's saved settings to statebilltracker.org/ny/ (checked: /, /kelles/, /2023.html, /watchlist/, /#S1234 all
  land with the watchlist); Albany's 4 (revoked, test) invite codes were copied to state-lists; /ny/ is open to search
  engines; New York downloads everything itself (states/ny/fetch.py). The albany-cron timer still calls the Albany
  workflow, which ignores it; switch it off in the Cloudflare dashboard (Workers > albany-cron > Triggers) when convenient. Shared lists stay on
  state-lists.lists-worker.workers.dev (its CORS already allows statebilltracker.org); a route on the zone is optional.
  albanybilltracker.org is also at Porkbun: on launch day its nameservers were changed by mistake and put back within
  minutes; check which domain a registrar page is for before changing it. Checklist items done: 2, 3, 4, 6 (site check);
  still to do: 1 (run more often in January), 7 (Stripe's website field), 8 (uptime alerts).
- **Launch checklist for statebilltracker.org** (do these together when the owner says to launch):
  1. `.github/workflows/publish.yml` and `download.yml`: run more often while legislatures meet (e.g. hourly on weekdays),
     minding Cloudflare Pages' monthly deployment limit (500 on the free plan; skip deploys when nothing changed, or pay).
  2. Build with the real address: drop `SITE_URL` from the workflow (states use `PUBLIC_URL`), and set
     `LAUNCHED=1` so `build_site.sh` stops telling search engines to stay away.
  3. Point statebilltracker.org (and .com, forwarding with 302) at the Pages project: add it as a custom domain
     in Cloudflare Pages and change the DNS at Porkbun.
  4. Analytics: GoatCounter's code is `statebilltracker` (site_meta.GOATCOUNTER, one for the whole site; counted only
     with LAUNCHED=1). The front page and issue pages count anonymous events too ("home/...", "issue/...": topics, Map or
     Chart, party filter, search found / found nothing / opened, stars, Your bills, links into states; never typed words).
     Cloudflare Web Analytics: none yet.
     Contributions: site_meta.SUPPORT (a Stripe Payment Link; the About page, the footers, and the state pages' "Glad this
     helped" note, `supportNote()` in tracker.html: after an email is copied or an action logged, once per 90 days per
     browser; events support/shown, give, share, close).
  5. Shared lists: the `state-lists` Worker is deployed with its own KV (2026-11-18); check each state's `listsApi`
     points at it (not albany-lists).
     Once the domain is on Cloudflare, route statebilltracker.org/lists/*, /admin/* and /manage to the Worker (or give it
     a custom domain), point every `listsApi` there, and tell the owner the admin page's new address,
     statebilltracker.org/manage (until then https://state-lists.lists-worker.workers.dev/manage).
  6. Check every state's pages once more (test/crawl.js) and republish the private NJ Claude copy.
  8. Uptime alerts (the owner sets them up with Claude's help, not before launch): UptimeRobot (free) with
     statebilltracker@gmail.com, monitoring https://statebilltracker.org/ and the lists Worker's /health address.
  7. Contributions: in the State Bill Tracker Stripe account (a separate account, not the Substack one), Settings →
     Business details: change the website from https://statebilltracker.pages.dev/ to https://statebilltracker.org/.
- Fixes made in ny-bill-tracker still get carried over here by hand (compare against `git log` there since
  b312227; 5fe4339 is already in).

## What's switched off in this copy (so it can't touch the live NY site)

- **The workflow** (`.github/workflows/update.yml`) runs only when started by hand: no schedule, no
  push trigger. It has no GitHub Pages site.
- **The Workers are renamed:** `state-lists` and `state-cron` (with no timer, aimed at this repo). Never deploy them
  under the names `albany-lists` or `albany-cron`. A third, `state-ga-relay` (ga_relay_worker/, 2026-11-22; no KV, secret
  `RELAY_KEY`), fetches only public www.legis.ga.gov/api/document/ files for Georgia's download, because GitHub's runners
  can't reach that server (Cloudflare can; states/ga/NOTES.md). `state-lists` (https://state-lists.lists-worker.workers.dev, deployed
  2026-11-18) has its own KV namespace, STATE_LISTS (id in lists_worker/wrangler.toml); the account's other namespace,
  LISTS, is the live NY site's: never bind or write to it. Shared watchlists (2026-11-18): anyone can share a list (random
  address, up to 10 new lists a day per IP, title only); a group with an invite code also gets a named address, an
  introduction and notes, and view counts (KV's free tier allows 1,000 writes a day, so other lists aren't counted);
  saves at least 10 seconds apart. **`lists_admin.py`** now talks to `state-lists` (token in ~/.state_lists_admin, also
  the Worker secret ADMIN_TOKEN): `lists`, `list-hide`/`list-show SLUG`, `list-delete SLUG`, codes as before. Every
  state's `listsApi`, New York's included, points at state-lists.
- **`artifact_urls.json` is empty.** Never publish to the NY Claude copies from here.

The notes below are ny-bill-tracker's, copied as they were. They describe the code as it stands.

---

# Albany Bill Tracker: notes for making changes

Read README.md for what each script downloads. This file covers how to change the site safely.

## The pieces

- **tracker.html** is the whole site: one HTML file with all CSS and one large script. There's no
  framework or bundler. `build_data.py` embeds each session's data into a copy of it.
- **build_data.py** reads `data/bills_<session>.json(.gz)` and the other data files, and works out
  stages, topics, places, votes and statistics (`insights()`). It then writes:
  - `site/<session>.html`, with the data embedded (gzip+base64, `data-enc="gzip64"`, unpacked in the
    browser by `unpack()`). These are the Claude copies. They have no ROOT, so public-only features are off.
  - with `--github DIR`: the public site. `index.html` is the current session and `<year>.html` the
    past ones; legislator pages go at `/<slug>/` and the watchlist at `/watchlist/`. `github_page()` adds the
    document head, icons and the analytics tags, and moves the styles and shared scripts into /assets/app.<hash>.css,
    lib.<hash>.js and app.<hash>.js (`asset_file()`, one copy for every state; ARCHITECTURE.md step 4): the main script
    must stay the same in every state, so per-state words go in the page (`#page-names`, the profile), never in the script. Each session's data is split so a visitor downloads only what they
    look at (`split_payload()`, 2026-11-18), in files named by a hash of their contents, `data/v/<session>.<hash>.<part>.json`,
    which build_site.sh's `_headers` lets browsers keep for a year. The page's data tag names them: `data-src` (the list
    part, preloaded), `data-parts` ("rows:<hash> stats:<hash> ..."), `data-shards` (one hash per shard) and `data-v`,
    `data-session` (tracker.html's `readParts()`, `partUrl()`); `data-texts` for the `data/<session>-text/` pieces.
    - The **list part** is what the first view needs: every bill's numbers, stage, topics, sponsors, dates, places,
      agendas, flags and current committee (the pipeline, the topic counts, the sort, stars, the notice), and
      everything else about the first 150 bills in the list's usual order (`FIRST_ROWS`, `rowsIn`): titles, histories
      and `ROW_COLS`. Constitutional amendments keep every field there (`STATE.amendmentFinal` can read a summary,
      votes or other sessions, for the row), as do law codes naming the bills a chapter amendment changes (other law
      codes aren't published: nothing shows them). Each legislator carries `apiName`, the name the bill data uses for
      them, worked out by the build (`api_names()`, the one copy: `setupLegislators()` reads it), so the sponsors' districts it's read
      from aren't published.
    - The **rows part** is every bill's title, history and `ROW_COLS` (laws, committees, co-sponsor count, program,
      law, parties, main topic; each version's co-sponsor count, status and committee): `b.rowIn`. Any other list of
      bills reads it, and so do a search (titles), the committee, law and party filters and the sort by co-sponsors
      (`listNeeds()`), their counts (`fillStaleSelects()`) and How's committees. It's fetched (at low priority) when the
      visitor reaches for the filters, the search box, the sort or "Show more", or when something needs it, else 4
      seconds after the list is drawn once no shard is downloading.
    - The **shards** (`.s<k>.json`) hold everything an opened bill shows: summary, history, co-sponsors, votes, its
      versions in other sessions with their numbers, similar bills, the governor's veto message, and the titles of the
      similar bills it names (with their histories where the state's `endedNote`/`heldAction` reads them: the build
      checks profile.js for those names). A bill's shard is FNV-1a of its first number without the version letter,
      modulo the number of shards (`shard_of()` = tracker.html's `shardOf()`), so a page can fetch it before the list
      arrives (`#S1234`, a shared `#w=` list, the visitor's own watchlist on `#watch` or /watchlist/:
      `prefetchFromAddress()`). Only a current or upcoming session's page has shards, each about 40 KB gzipped
      (`SHARD_GZ`; 22 KB made NY's watchlist of ten 0.6 s faster but doubled the files): opening a bill fetches one (`needBills()`, `b.full`), and pointing at, touching or tabbing to a
      row starts it (`prefetchBill()`, which also fetches the bill's text piece). The watchlist tab's "N new" reads
      the watched bills' shards (the rows part for more than 20).
    - The other parts are fetched when something needs them (`need(part)`): `stats` (statistics and legislators'
      profiles: the Statistics tab, an opened bill's odds line and votes, the watchlist's deadlines, How's committees,
      the vote filter, a legislator's page), `net` (networks, and each bill's versions in other sessions as [session,
      stage]: the Statistics tab, the history filter, the sort by sessions, `b.earlier`/`b.later`, `b.histIn`),
      `search` (summaries: a text search shows title matches first, then all once it's in), `votes` (the vote filter, a legislator's
      numbers), `hist` (other sessions' bill numbers: the watchlist's "back this session" box), `cos` (co-sponsors:
      legislators' pages, the live network, "Their numbers"), `towns` (a towns list over 500 KB, Congress's: "Where
      you live").
    - A **past session's page** (rarely visited) has no shards and no separate parts: after the list and rows parts,
      everything is one file, `more` (its parts, and every bill's details as one shard without titles and histories),
      fetched the first time anything needs it (`needMore()`; `data-bundle` names the parts it holds). So a past session
      is 3 files, as before 2026-11-18.
    Each part has its own strings table. A new field the first view reads belongs in the list part; one an opened bill
    reads belongs in the shards. test/issues/get.py puts them back together. A current session is 8 files plus about 7
    shards per 1,000 bills (3 to 9 by state; NY 2025-26: 101): mind Cloudflare Pages' 20,000 files a deployment (build_site.sh warns
    at 18,000 and fails the build at 19,500). The site was 10,761 files before shards, and about 12,100 with them (measured on eight states and extrapolated by bills, 2026-11-18) (each
    state's legislator pages are most of it).
- **.github/workflows/update.yml** downloads, builds and deploys every morning, hourly on weekdays
  January through June (agendas, floor votes), every two hours on weekdays July through December
  (the governor's requests and actions), and on every push to main. Contacts refresh once a day.
  A scheduled run publishes only if `fingerprint.py` (the built site minus the time of day in the
  "updated" stamp) differs from the live `/fingerprint.txt`, so at least once a day. The `alert`
  email goes out once a day per set of problems (an Actions cache key per day and problem list). `check_fresh.py` runs after
  each build. If data is behind, the `alert` job fails, which makes GitHub email the owner; the
  site still deploys. It also catches: Assembly agendas that list meetings but yield no bills
  (`fetch_agendas.py` writes to `PROBLEMS_FILE`), one house with upcoming agendas and the other none,
  and contacts parts kept from an older copy (`kept` in `contacts_<session>.json`; a new session's
  Senate committees carry over from the last one until the API names them, warned after Feb 15).
- **Prefiled bills:** in November and December of even years the workflow also downloads the next
  session. `build_data.py` decides the current session by the calendar (`CURRENT`); a later one is
  "upcoming": its page is `<year>.html`, its data has `current` and `upcoming` true, its stages
  read "Prefiled" (`STAGE_TEXT.prefiled`), and it has no Statistics tab. Statistics and
  outcomes leave it out. Stars made there carry into January, since watchlists are keyed by session.
- **cron_worker/** is a Cloudflare Worker that starts the update workflow on time (GitHub's own
  schedule often runs late or skips runs; it stays in update.yml as a backup). It fires hourly and
  checks New York time against the same schedule, then calls workflow_dispatch with `timed=true`, which
  publishes only on change, like a scheduled run. Its secret `GITHUB_TOKEN` is a fine-grained token
  (this repo, Actions read/write) kept in `~/.albany_cron_token`; it expires, so renew it yearly.
  Deploy with `cd cron_worker && npx -y wrangler@4.152.0 deploy`.
- **lists_worker/** is the Cloudflare Worker for published watchlists (KV namespace LISTS):
  - It serves `GET /lists/:slug` publicly and counts views in `views:<slug>`, except views by the
    list's editors.
  - Creating a list (POST) needs an invite code. Changing it (PUT/DELETE) needs the edit key in
    `X-Edit-Key`. `/admin/*` needs `Authorization: Bearer <ADMIN_TOKEN>`.
  - Deploy with `cd lists_worker && npx -y wrangler@4.152.0 deploy`.
  - **lists_admin.py** runs the admin commands: `code-new "Group"`, `codes`, `code-revoke CODE`,
    `lists`, `list-delete SLUG`.
- **Data the build commits back:** `data/assembly_votes_*.json` and `data/contacts_*.json`. Past
  sessions are stored as `data/bills_<year>.json.gz`.

## Map of tracker.html (search for these names; line numbers drift)

ARCHITECTURE.md (repo root) is the map of the whole site: the pipeline from download to publish, which checks run where, where each visible part is drawn, shared code, and a troubleshooting list. Read it first when diagnosing a problem; this section is tracker.html's detail.

- **Top:**
  - CSS, with color tokens on `:root`. Dark mode is defined twice: under
    `@media (prefers-color-scheme: dark)` and under `:root[data-theme="dark"]`. Change both.
  - The page markup: the header, `#notice`, the tabs, `#view-bills`, `#view-watch` (`#wl`,
    `#wlActions`, `#wlList`), `#view-act`, `#view-stats` and `#view-how`.
- **The state's profile:** `states/ny/profile.js` defines `STATE`: the public site and lists
  addresses, house names, the session label, the governor's contact links, links to bill text, the
  governor's deadline (`govDeadline()`), the deadline for bills that passed both houses
  (`passedBothBy()`, `passedBothGroup`), what comes next for such a bill and whom to ask (`passedBothNext()`;
  NJ: the governor, or the house voting on a conditional veto), stage names and tips. build_data.py puts it in each page
  just before the main script (`<script id="state-profile">`). tracker.html keeps short aliases
  (`STAGE_TEXT`, `HOUSE`, `GOV_REACH`, `span`, `LISTS_API`, `PUBLIC_SITE` …), so it can't run unbuilt.
- **Constants:** `STAGE_TEXT` (stage names, live vs. final sessions), `STAGE_TIPS`, and
  `plainAction()` (plain-language wording for actions: lists_pages/billfacts.js's, with its `PLAIN` list; the build
  writes each bill's latest news in those words into the status rows).
- **Bills list:** `matches()` (filters), `sortBills()`, `renderPipeline()` ("Where it is now"),
  `renderList()`, `billRow()`, `statusText()`, `track()` (the progress bar in each row),
  `fillDetail()` (the panel that opens under a bill, indented under its title: What you can do, What it does, History
  (`historyBlock()`: steps and votes in one list), Who sponsors it, the rest, the official links and "Copy link to this
  bill" last; the owner's chosen design "A · Tidied", 2026-11-20; a row's pips, label and date are lists_pages/rows.css's,
  the same in every view) and `nextSteps()` / `planFor()` /
  `contactBook()` (who to contact and what to ask; `draftBtn()` adds "Copy email" / "Copy message",
  which uses `draftFor()`).
  `holdUp()` adds the leader (and, for a money committee, the governor) when a bill stuck in committee
  shows signs the decision is above the committee: it's in or reached Rules; its sponsors are most of
  the committee and the chair is one; or it's in the money committee (`STATE.moneyCommittees`) with
  most of the committee sponsoring. A chair or leader who sponsors the bill is still asked to schedule it ("(you sponsor it)";
  decided 2026-10-29); other sponsors aren't asked. A card shows one "Decides" person (the leader first when the
  decision looks higher up, `leaderFirst`); anyone else who decides goes in its "Also" line. The last two wait until the committee has met `SKIPPED_ENOUGH` (5)
  times since the bill arrived without taking it up (`meetingsSkipped()`, counting days it approved a bill,
  so meetings on resolutions or nominations alone are missed), and the money one until the year's budget
  bills pass (`budgetPassed()`). In 2017–24, about half of NY bills sponsored by most of a house
  still died there, many in Ways and Means. Leaders' pronouns are in `LEADERS`.
- **Your legislators:** `HOME` (county), `setCounty()`, `myReps()`, `votePeople()` and
  `lookUpReps()`. The party line under the title (`#power`, balance.py's `summary_html(buttons=True)`, current session
  only) names each house and the governor as buttons (`data-legs`): `openLegs()` / `renderLegs()` show, in `#legsBox`
  under the header, the house's members (party, district, bills sponsored and laws this session, from the list part's
  sponsors: `legCounts()`; sortable, a name filter; the leader marked) or the governor's contacts (`GOV_REACH`, the
  bills waiting for them); the same name again closes it (2026-11-22). Legislator pages: `PRESET`, `PAST_WHO`, `renderPerson()` and `renderPersonStats()`.
  The governor's page (2026-11-22), /<st>/governor/ (Congress: /us/president/, build_data.py's `GOV_SLUG` from
  legislatures.json's "executive"; `PRESET.gov`): `renderGovCard()` and `renderGov()` (`#govRec`, the Record view; the page
  has no tabs, the owner's choice 2026-11-22: the card's "All bills" link goes to the list): on the desk (soonest deadline first), this session's decisions by the governor in office
  (decided on or after `govNow.since`; signed, without signature, vetoed, overridden: `GOV_KINDS`), earlier sessions under
  the same governor (`govRecord` in the stats part, `governor_record()`: by the governor in office on the decision's day;
  its `NO_SIGNATURE` is tracker.html's, keep them alike) and vetoes with a message (`vetoMsgs`). Bills open in place
  (`billRow()`). Linked from the Governor panel and from a decided bill's "What you can do" line (`govLink()`, `govFrom()`).
- **Statistics:** `renderStats()`, which builds every stats section, plus `sankey()` (odds),
  `monthChart()`, `oddsLine()` (the "In past sessions…" line in a bill panel) and the network
  (`renderNet()` / `drawNet()`, which loads d3 on demand).
- **Who works on what:** `whoData()`, `whoLayout()`, `whoSvg()`, `whoPanel()`, `renderWho()` and
  `whoDrag()` (current session only).
  - Each legislator is placed among topic anchors around a ring, weighted by share²÷typical share.
  - The ring order comes from `topic_ring()` in build_data.py: the exact best cycle, where neighbors
    share the most bills.
  - Visitors can drag topics to reorder the ring; the order is saved in `abt:whoorder`.
  - Dots split between two distant topics get a gold outline.
- **Signing memos and chapter amendments:** `amendedBills()` reads a follow-up bill's "as proposed in
  S.x & A.y" line; `chapterAmendment()` shows it. A bill signed with a memo (`b.memo`, from the API's
  `approvalMessage`, cleaned by `memo_text()` in build_data.py) gets `signingMemo()`: the memo text and
  its follow-up bills (`followUps()`) with their status.
- **Veto messages:** `fetch_bills.py` keeps each vetoed bill's `vetoMemo` ({year, signer, text}); past sessions were
  filled in 2026-10-28. `veto_text()` in states/ny/convert.py keeps the reasons (after "NOT APPROVED"). `vetoMemo()`
  shows them on the vetoed bill and on a reintroduced version; if the current governor vetoed the earlier
  version, `planFor()` lists the governor ("support it this time"). Before the year's budget passes, a bill
  stuck in the money committee with most members sponsoring gets "include it in the budget".
- **Near-identical bills:** `twinLine()` names them, and `likelierOf()` says which version is more
  likely to move: matching bills in both houses first, then the one that got further, then the
  sponsor's newer version.
- **What's changing:** `renderTrends()` draws `DATA.insights.trends`, from `trends()` in build_data.py.
  Its subjects (`TRENDS`) and wording pairs (`WORDING`, both in states/ny/profile.py) were picked by
  hand from an automatic phrase scan; check new ones before adding.
  Every state's (and Congress's) were picked the same way on 2026-11-22, in its own profile.py: notes/trends.md has the
  method, each subject's counts and why (AR, KY, NH, UT and WY left empty). A subject that fell makes the heading read
  "Subjects that rose or fell"; committees aren't listed as "Most bills now".
- **Watchlist:**
  - One watchlist, two views (the owner's decision, 2026-11-19): a state's Watchlist tab shows what /your-bills/ shows,
    that state's bills only (this session; other sessions' stars are the "3 more in 2023–24 ›" line), with the same rows,
    groups, order and deadlines: lists_pages/watchrows.js (`WatchRows`: `place()` a bill's group and deadline, `draw()`,
    `rowHtml()`, `newsHtml()`, `ordered()`, `where()`) and rows.css draw both (build_data.py puts them in each state page
    beside watchrules.js; build_site.sh with common.js/common.css). Groups: Due soon, Before the session ends, the state's
    year-end group (`passedBothGroup`), Later, Out of time this session (current session, nothing to ask for:
    watchrules.js's `canAct` false), Decided or ended (laws, vetoes, past sessions); within a group the soonest deadline,
    then furthest along, then the latest action. No drag order any more (the old `abt:<st>:worder` values are left alone,
    not read). A row opens its card below it: on the state page drawn by the page itself (`toggleRow()`, `watchCard(x,
    true)`: the card's body, with "Your side" and the sponsors at its top), on /your-bills/ by the state's page in a frame
    ({sbtShow, mine: true}: the person's own card, with their side and action log). The header line: "Your bills in New
    York · All your bills (12 in 4 states) ›" (`allStars()`); a Your bills link is in every state page's header
    (`#siteNav`, `siteYours`). `watchRow()` makes a row from the page's bill (`canActNow()`: planFor()'s actionable).
    A list someone shared (`SHARED`) and /list/'s frames (`EMBED`) still show the cards (`watchItems()`: Needs action,
    Out of time this session, Decided).
  - Storage and actions: `WATCH` (localStorage), `watchItems()` (each bill's ask: `keyAction()`), `deadlineOf()` /
    `W_GROUPS` (`sessionEnd()` reads `data/session_calendar.json`, else when past sessions ended), `renderWatchView()`,
    `logBlock()` / `actionRecord()` (the action log) and `draftFor()` (email text; a group's "Copy one email about all
    3" is `groupExtra`).
  - Sharing: the state's tab shares that state's bills ("Share your New York bills"); Your bills shares all of them
    ("Share all your bills"), a separate list on purpose. Both save their bills in the order the list shows them.
  - News: `newsBox()` ("New since you last looked", at the top; rows open the card, "Mark all as seen"),
    `newActions()` (actions since the bill was last opened, skipping `ROUTINE` paperwork,
    most important first by `WEIGHT`), `newsTags()` (the "New: …" and "Coming up: …" tags),
    `nextMeeting()` (from committee agendas) and `updateWatchTab()` (the "N new" badge on the tab).
  - New session: `carryCandidates()` / `carryBox()` offer bills from last session's watchlist that
    are back under new numbers (handled ones are kept in `abt:carried:<session>`).
- **Committee agendas:** `state.agenda` ("On an upcoming committee agenda", a sub-row under In
  committee, turned on by `setAgenda()`, which also sorts by `meeting`), the "On the agenda" tag on
  bill rows, and `comingUp()` (a legislator's "Open for comment" tab: the next two weeks' meetings, each folding open to its bills).
  `CHANGED` also has "Introduced since your last visit" and "in the last 7 days" (`b.dates.intro`).
    `markSeen()` runs when a bill's details or its watchlist card are opened.
  - Sharing (2026-11-18; public site only): "Share this list" makes one live list in the state-lists Worker (every
    profile's `listsApi`), viewed at /list/#<slug> (lists_pages/list.html); no code needed. `shareBox()` draws the
    options (Copy link, share icons, "Use this list on another device", "Stop sharing", the group-code line, the
    contribution line once in 90 days: `thanksOnce()`, shared with `supportNote()` and Your bills), `publishAction()`
    handles them. `saveWatch()` calls `schedulePub()`, which saves (`savePub()`, `pubPayload()`) a minute
    after the last change, and `flushPub()` on pagehide. My list is `myPublished()` ({slug, editKey, title, group,
    saved}); a group code adds the introduction and per-bill notes (`pubText()`). `followedHere()` lists followed lists
    with this state's bills. Old addresses, `watchlist/#list=<slug>`, redirect to /list/ before the data loads; snapshot
    links, `#w=<session>.S1234.-A5678` ("-" means oppose), still open here with "Add all to my watchlist".
  - /list/ draws the same rows as Your bills (2026-11-23, the owner's decision; watchrows.js, onelist.js): the same groups,
    both bill numbers (the status files' last column), the group line ("4 of these need the governor's office. Copy one
    message about all 4", also on /your-bills/), and an ⓘ for a browser that didn't make the list. A bill's side or removal
    is changed through Edit. The paragraph below describes the frames that open each row's card.
  - A shared list's bills open in place on /list/ (2026-11-18): each row is a button that opens, below it, the bill's
    watchlist card drawn by its state's page in a frame. One frame per state's session (list.html's `FRAMES`), loaded at
    `#embed=<session>` (only the list part): the first state shown as soon as the list's bills are known (at the state's
    main page; tracker.html moves a frame asked for another session to that session's page), the next two once the list
    is drawn, one after another; others when a row is pointed at. Opening a bill posts `{sbtShow: "2026.-A1234"}` ("-"
    for oppose) and pointing at a row `{sbtWarm}` (its shard and the stats part); the frame answers `{sbtReady}`,
    `{sbtLoaded}` and `{sbtEmbed: height, bill}` and is shown once it shows the bill asked for. The frame is moved under
    the open row with `moveBefore()` (which keeps it loaded); without it, it's laid over the row's slot (`place()`,
    `aria-owns`). One bill per state is open at a time. tracker.html's `EMBED` mode shows only the card body
    (`embedCard()`, "More about this bill" open), hides the header, tabs and footer (`html.embed`), draws nothing else
    (`drawAll()`), doesn't fetch the rows part on its own, and opens links it doesn't handle in the whole window. "Who
    decides" counts committee meetings from `meetingDays` in the stats part (build_data.py's `meeting_days()`, a port of
    `walkCommittees()`/`meetings()`: test/ports_check.js fails when they differ), so an opened bill never needs the rows part. Measured 2026-11-18
    (slow 4G, 4x CPU, phone, cold cache): first bill 1.3-1.7 s after the list shows, another of the same state 0.1-0.8 s;
    the list itself shows after 6-7 s, almost all of it the states' whole status files (NY's is 517 KB).
  - Your bills as one list (2026-11-19): every tab of /your-bills/ draws its bills from all states and sessions as one
    list (lists_pages/onelist.js, drawn by watchrows.js, as each state's Watchlist tab): Due soon, Before the session
    ends, a later deadline (a state's `passedBothGroup` name when the group is one state's, else "Due later"), No
    deadline yet → Later, Out of time this session, then Decided or ended (laws, vetoes, past
    sessions), soonest deadline first; "Group by state" (abt:yourbills:bystate) instead. A starred bill is new until
    it's opened anywhere (its watch entry's `seen`, which the state's page, the front page and Your bills all set; not
    abt:tabseen, which only list tabs use), and paperwork (the state's `routine`, else `WatchRows.ROUTINE`) isn't news;
    "New since you last looked" is at the top of the Starred tab, as on the state's tab. The deadline rules exist once, in lists_pages/watchrules.js (`WatchRules.make(STATE, facts, hooks)`:
    `sessionEnd`, `floorVotesOver`, `standing` (adjourned, recess, a missed crossover), `live`, `canAct`, `deadlineOf`,
    `dueText`, the groups; `nextMeeting`): build_data.py puts it in every state page before the profile, and tracker.html's
    `WR` calls it (planFor(), the watchlist), so test/same.sh shows the pages unchanged. Your bills runs each starred
    state's own profile (data/v/profile.<hash>.js, written by build_data.py, named by each session's `f.s` in
    /status.json) in its own scope (`new Function` with fmtDate, esc, isoToday, lastYear, span, monthDay, DATA, BILLS), with
    the session's facts in /status.json (`f`: c current, u upcoming, e scheduled last days, v last floor vote, t past
    sessions' last votes) and the bill's status row, whose columns after the seventh are what the rules read: the day it
    went to the governor (stage 4), upcoming committee meetings, flags ("b" budget, "v" sent to the voters), and its
    version in the newest later session ([session, number]: "Back in 2025–26 as A 1234" with its own star); trailing empty
    columns are left off (about +50 B a current session, +4-8% on past sessions' pieces). Bills from a session /status.json
    doesn't name say "<session>: no longer on this site" with Remove. What the rows can't know (a bill a floor vote or
    withdrawal ended early, Nevada's exempt bills, whether the state's card has someone to ask) differs from the state's
    own watchlist only there. A row opens its card in place (embed.js's `Opener`: one frame per session page at
    #embed=<session>, {sbtShow}, moveBefore; 1f77f66's design, brought back). Rows are kept in abt:yourbills:rows and
    drawn at once on the next visit. Lists made in the editor are changed there (Edit), not in their cards.
  - Status pieces (2026-11-18): the pages that show a few bills from a state's status file (/list/, /your-bills/, the
    list editor: common.js's `statusOf(st, session, num)`; the front page's "Your bills" and search stars: home.html's
    copy of it) read it in pieces. build_data.py's `write_status_shards()` writes, beside status_<session>.json (still
    written: search_site.py reads it, and it's the fallback), data/v/<session>.<8-hex hash>.t<k>.json, {bills, alias},
    a bill or other number in piece `shard_of(number, n)` (FNV-1a, as the bill shards); an alias's record can be in
    another piece, fetched next. Pieces are about 12 KB gzipped for a live session, 40 KB for a past one
    (`STATUS_GZ`); each state's data/status.json lists its sessions' {"p": page, "l": live, "h": the hashes}, and
    build_site.sh gathers them into /status.json (about 1 KB per big state; revalidated on each visit, preloaded by the
    three lists pages; the pieces are immutable under _headers' data/v rule). A state or session /status.json doesn't
    name reads the whole file; a session missing from a named state is "not found" at once (it would have 404'd), and a
    piece that fails (a deploy mid-visit) falls back to the whole file. About 800 files across the site (12 KB / 40 KB;
    1,450 if past sessions were 12 KB too). Measured 2026-11-18 (slow 4G, 4x CPU, phone, cold cache, HTTP/2): /list/
    with 10 NY bills 6.1 s -> 1.6 s (517 KB -> 124 KB); NJ+NY 6.8 -> 1.4 s; /your-bills/ with 10 bills in 3 states
    5.5 -> 1.5 s; the front page's Your bills 5.4 -> 1.6 s.
  - Named lists from any bill row: `lists_pages/named.js` (one global, `NamedLists`; put in every public state page by
    `github_page()`, in home.html and the list editor by build_site.sh) draws a list button beside the star (state rows
    and watchlist cards: `listButton()`; the front page's search results and panel rows: `listBtn()`) when this browser
    has lists from the editor (common.js's NAMED), and its menu (checkboxes for the lists, "New list…" to
    `/lists/edit/#new&add=<code>`). Changes are kept in localStorage at once and PUT to the Worker 2.5 s later, at least
    10 s after the list's last save (`savedAt`, which the editor also writes and respects); unsent saves go out when the
    next page with named.js opens. The editor's payload and signature are named.js's.
- **Analytics:**
  - `countUse(name)` sends an anonymous GoatCounter event, but only on the public site.
  - `countError()` and `countVisit()` are built on it. `staleNotice()` warns visitors when data is
    2 or more days old.
  - Contact links: `emailHtml()`, `phonesHtml()` and `GOV_REACH` render mailto and tel links that
    carry `data-contact="how|role"`, where the role comes from `roleKind()`. One page-wide click
    listener counts `contact/<role>/<how>`.
  - `step()` counts pairs of steps within one visit (`steps/opened a bill → starred`, and so on).
    `countOnce()` counts tab moves (`move/`), sections (`stats/`, `how/`), tips (`tip/`) and
    searches (`search/used`, `search/found nothing`; never the words typed).
  - Event names in use: `starred/`, `opened/`, `email-copied/`, `email-copied-several`,
    `share-link-copied`, `list-viewed`, `list-published`, `list-updated`, `list-link-copied`,
    `shared-list-added`, `action-logged`, `county/`, `error/`, `visit/first`, `visit/returning`,
    `watchlist/`.
- **How a bill becomes law:** subtabs via `showHowSec()` (sections are `.howsec`; links use
  `data-how="<id>"`). The steps open with a picture (`renderHowPic()`, 2026-11-20, approved by the owner): one lane per
  house, twins or house to house (`STATE.tracks`), the governor's branches (`STATE.unsigned`, `STATE.override`), and "N in 10
  stop here" pills from the stats part's odds (drawn without them until it's in); under 600px the lanes become columns. The Committees tab is `renderHowComm()`: it pairs Senate and Assembly
  committees by name, or through `COMM_PAIRS` when the names differ, with notes in `COMM_NOTES`.
  "N bills" links set `state.comm` and open the Bills tab.
- **Similar bills:** `similar_bills()` in build_data.py (TF-IDF on title, summary and the law
  sections amended; it leaves out narrow bills) adds each bill's matches as the last row element.
  `similarBlock()` shows them in the bill panel, and a score of 70 or more is marked "Nearly the same."
- **View links:** `viewParams()`, `viewLink()`, `applyViewLink()` and `syncViewHash()`. Filters
  ride in the address (`#v&stage=3,4&topics=env&nearby=1&county=Tompkins`). The public site keeps
  the address current as you filter. A link's county is applied without changing the viewer's saved
  county, and `LINK_COUNTY` offers to switch back. "Add all to watchlist" is the `#starAllBox` code
  in `renderList()`.
- **Startup:** `hydrate(raw)` sets `DATA` and `BILLS`, then `wire()` attaches event handlers and
  `render()` draws the Bills tab. On the public site everything else arrives in parts (`need(part)`, merged by
  `MERGE`) and shards (`needBills(bills)`, `mergeShard()`), each fetched once; on Claude copies `SPLIT` is null and
  every part and bill is ready (`partReady()`, `b.full`). What needs data waits for exactly that, with "Loading…" in
  place: a list of bills not in yet (`renderList()`: their shards for up to 3, else the rows part), an opened bill
  (`fillDetail()`: its shard and the stats part), the list under a search, the vote or co-sponsor filter or on a
  legislator's page (`listNeeds()`: `render()` shows "Loading…" in the list; the page's frame stays until they're in,
  as it does for a bill named in the address). Hidden tabs (Statistics, Watchlist, How, a legislator's Open for comment and Their numbers) are
  drawn when opened: their render functions start with `later(view, key, fn, box, needs)`, which keeps them in `STALE`
  and says "not now"; `needs()` returns the parts and bills the drawing reads (the watchlist: its bills, the stats
  part); `showView()` draws what's stale. A drawing that finds it needs a part only while it runs (`meetings()` reads
  every bill's history, for "who decides") adds it to `MISSING` and is drawn again once it's in (`fillDetail()`,
  `renderWatchView()`). `renderNet()`, `renderWho()` and `renderTrends()` wait with `waitParts()`. The "More filters"
  lists are counted only while the panel is open (`fillStaleSelects()`, on its `toggle`), or when one has a choice made
  (the vote filter's counts fetch the votes part). The Statistics tab's buttons are set up the first time it's drawn
  (`setupStats()`).

## Rules and traps

- **One big script, one shared namespace.** A second `function foo` silently replaces the first.
  That happened with `track()`, and the progress bars vanished with no error. A duplicate `const`
  breaks the whole page. Before adding a top-level name, grep for it. `test/check.sh` catches
  duplicate functions.
- **Only the frame shows until the list is drawn.** CSS (`html:not(.ready)`) shows the title, the tabs (not
  clickable: `pointer-events: none`) and `#frameLoad`, a screen-tall box saying "Loading 13,864 bills…" (the build
  writes the count), and hides everything else until the loader adds `ready` after `hydrate()` (on the public site,
  once the list part is drawn, and what `listNeeds()` or a bill in the address needs). This stops layout jumps, which Cloudflare scores as CLS, and
  early taps that ran code before `DATA` existed. The build writes the header line (`#sessionLabel`), the session
  buttons (`sessions_nav()`), the front page link (`github_page()`) and the tabs the page will have (`frame_tabs()`:
  past sessions, prefiled bills, legislators' pages, /watchlist/) into the page so they don't change on load. Anything added later above the tabs, like a banner that appears after loading, makes
  the tabs jump: the notice (`#notice`) still does, when there is one.
- **Public-only features check `ROOT`:** the publish box, analytics, the stale notice and the
  legislator page links. ROOT is empty on Claude copies.
- **Every event handler is in `wire()`**, mostly delegated from `#list`, `#openNow`, `#wlList` and
  `document`. Watchlist card buttons inside the clickable card head must be real `<button>`s;
  otherwise clicking them also opens or closes the card.
- **Wording.** The owner wants plain, short wording that sounds like a person, not a program. Say
  "inflation" or "actual dollars", not invented terms. Explain jargon with `TIP("…")` or `TIPI("…")`
  (the ⓘ tips), not more paragraphs.
- **Layout and colors.** It must work at phone width with no sideways scroll. Check light and dark
  mode.
- **Never print or commit secrets.** The NY Senate API key is in `~/.nysenate_api_key` and the GitHub
  secret `NYSENATE_API_KEY`. The lists admin token is in `~/.albany_lists_admin`, also the Worker
  secret `ADMIN_TOKEN`. The analytics tokens in states/ny/profile.py are public by design.
- **Don't bulk-download from nyassembly.gov on the owner's computer.** That means
  `fetch_assembly_votes.py` and `fetch_agendas.py`. Let GitHub Actions do it, and pull its commits.
- **Commits:**
  - Use the email `84396466+judithhubbard@users.noreply.github.com` and end the message with
    `Co-Authored-By: Claude …`.
  - The daily build pushes data commits, so if a push is rejected, `git pull --rebase` first.

## Making a change

1. Edit `tracker.html` (or `build_data.py` for data and statistics).
2. Run `test/check.sh`. It checks that the script parses and has no duplicate functions, builds
   the current session, then has headless Chrome click every control and report errors.
   - For a change that shouldn't change what visitors see (like moving code into a profile), run
     `test/same.sh [commit] [sessions]`. It records every tab, How section, 25 open bills and a
     watchlist (`test/snapshot.js`) from pages built here and at the commit (default HEAD), and
     compares them.
3. To look at the result, append a small `<script>` to a copy of `site/<session>.html`. The script
   should star bills, switch tabs and so on, then screenshot it with
   `"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless=new --window-size=1100,1400 --virtual-time-budget=9000 --screenshot=out.png file://…`.
   - Headless Chrome won't go narrower than about 500px, so for phone width load the page in a
     375px `<iframe>`.
   - Set `document.documentElement.dataset.theme = "dark"` to check dark mode.
4. To test public-site features (`ROOT` set), run
   `SITE_URL=http://localhost:8765/ python3 build_data.py --github /tmp/gh` and serve it with
   `python3 -m http.server 8765`. A local SITE_URL leaves out the analytics tags.
5. Commit and push. The site updates about 7 minutes later; GitHub's build takes about 6.
6. Update the Claude copies:
   - Run `python3 build_data.py`, which builds every session into `site/`.
   - Publish each `site/<year>.html` to its URL in `artifact_urls.json`.
   - **Never publish tracker.html itself.**
   - Claude allows 200 publishes a day, reset at midnight UTC.

## Each January of an odd year (new session)

- The workflow switches sessions on its own (see README). Check `LEADERS` and `DELEGATION` in
  states/ny/profile.py.
- Check that the Assembly agenda parser in `fetch_agendas.py` matches the real pages. It was
  written between sessions, without live agendas to test against. The freshness check now warns
  when it reads no bills.
- Check `DELEGATION_NAMES` (Webb, Kelles) against the November election.
- Add the year's scheduled last session day to `data/session_calendar.json` (from the Legislature's
  session calendar), each January, not just in odd years. `check_fresh.py` warns from February if it's missing.
- If a new governor takes office, add them to `GOVERNORS` in states/ny/profile.py (the "In past
  Octobers, the governor usually asked for bills…" line on waiting bills uses only the current
  governor's record).
- Publish the new session's Claude copy (a new artifact) and add its URL to `artifact_urls.json`.

- **Constitutional amendments (2026-10-31):** shown in every state where the data has them, tagged "const": as bills (PA, MD),
  concurrent resolutions (NY), or joint resolutions the converters now include (OH, WA, IL, GA, MI, WI; CA, OR, AZ, TX, CT,
  NJ, MA, VA in progress). Each state's profile.js says how they pass (`amendments`, `amendmentOnce`, `amendmentVote`,
  `amendmentFinal()`, `amendmentAgain()`) and when the voters decide (`ballotEvenYears`, `ballotYear()`, `ballotLine()`
  when the resolution names the election: OH, WI). They never reach the governor's stages, even where the state logs the
  governor receiving them (GA numbers them as Acts).
