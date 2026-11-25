# Light history

Older sessions kept as each bill's outcome, not as pages: for Statistics, Trends and the state comparison (the owner's
decision, 2026-11-24: back to 2015, light rather than full). Nothing here makes a page, a search entry or an issue match
yet; build_data.py's reading of these files comes in a later stage.

## Files

`data/<st>/light_<session>.json.gz`, one per state and session, written once by `states/light.py` (through
`.github/workflows/light-history.yml`) and kept in git (`.gitignore`'s `!data/*/light_*.json.gz`). A session is the
state's own session number as its converter uses it (Wyoming 2015, North Dakota's 64th Assembly 2015, Oregon 2015 for
"2015R1").

```
{"format": 1, "state": "mt", "session": 2015, "source": "...", "fetched": "2026-11-24T...Z",
 "has": ["chapter", "firstComms", "keyDates", "sponsor", "topics"], "lacks": ["summary"],
 "counts": {"bills", "passedOne", "passedBoth", "laws", "vetoed", "withChapter"},
 "noTopic": 33, "unmappedCommittees": ["..."],
 "parties": [["H", "Llew Jones", "R"], ...],
 "bills": [record, ...]}
```

Each record is the state converter's own record (`load_session()`) for that bill, with these fields only (the same
names and meanings as the current sessions' records, so the build can treat them alike):

| field | |
|---|---|
| nums, title | the bill's numbers as the converter writes them; its title |
| summary | the converter's summary, cut at 600 characters (Trends reads the first 600) |
| stage, passedS, passedA, passedIn | stages.py's stage, decided by the converter exactly as for current sessions |
| first, last, keyDates | introduced, last action; [floor, passS, passA, reset, delivered, signed, vetoed] (`;` between repeats) |
| firstComms, commFate, comms | first committee per house and whether the bill left it; the committees it went to |
| topics, mainTopic | the state's own topic mapping (committees, subjects or words, as now) |
| narrow, shell, budget, ballot, local, places | the converter's flags, where it has them |
| chapter, cosp | the law's chapter; co-sponsor count |
| vers | each version's number, sponsor, district, primes, cosp, statusDesc (no actions) |

Left out: actions, votes, texts, veto messages, similar-bill text. `parties` holds the converter's own party map
(`C.parties()`) for the sponsors named in the file. `noTopic` counts bills with no topic, and `unmappedCommittees` lists
first committees a state maps by name (`COMMITTEE_TOPICS`) that its table doesn't name (renamed since 2015, or never
mapped): their bills keep only the topics their words give.

## Adding a state

Write `states/<st>/light.py` with `SOURCE` (a line naming the source), `SESSIONS` (2015 up to the earliest full
session) and `fetch(session, data)`: download what the converter's `load_session()` reads for that session into `data`
(a scratch copy of `data/<st>/`), with the state's fetch.py's own functions where the old format matches, and return
True. Leave out what only pages need (texts, letters, agendas, member pages). Then
`gh workflow run light-history.yml -f state=<st>` and compare `python3 states/light.py --counts <st>` with the
official totals. `test/data_check.py` LOOKs at each file's counts and FAILs on future dates, law numbers on non-laws,
bills past both houses without both passage flags, and laws with neither a chapter nor a signing date.

## Pilots (2026-11-24)

| state | source | sessions | requests a session | lacks |
|---|---|---|---|---|
| Montana | api.legmt.gov archive/v1 (as 2023; steps_archive()) | 2015, 2017, 2019, 2021 | about 20-40, ten seconds apart | summaries (the archive has short titles only), member votes |
| Wyoming | lsoservice.wyoleg.gov BillInformation (list, then each bill) | 2015-2022 | about 450-550, a second apart | nothing the converter reads |
| North Dakota | ndlegis.gov API files + Session Laws index | 2015, 2017, 2019, 2021 | 6 | committee votes by member (minutes not read) |
| Oregon | api.oregonlegislature.gov OData (seven tables) | 2015-2021 | about 15-30 (paged) | nothing the converter reads |

Checked 2026-11-24 with one or two requests each: every source serves 2015 in the format the converter reads now. The
whole pipeline (download stand-in, converter, file, checks) was run on each state's current session.

## Second batch (written 2026-11-24, not yet run)

| state | source | sessions | requests a session (pace) | about | lacks |
|---|---|---|---|---|---|
| California | pubinfo_<year>.zip, tables and digests by HTTP range (as fetch.py) | 2015, 2017, 2019 | a few hundred ranges of a 0.8-1.2 GB zip | 10-20 min | nothing the converter reads |
| Connecticut | FTP archive flat files (flat_year(), as 2023) + statements of purpose | 2015-2021 | 5 | 1 min | comm_ref, committee and actions files (as 2023); journals |
| Indiana | api.iga.in.gov (bills(), people()); INDIANA_API_KEY | 2015-2022 | 1,000-1,800 (0.6 s) | 20-25 min | agendas |
| Missouri | House past-exports zip + senate.mo.gov bill pages (house_zip(), senate_year()) | 2015-2022 | House 2 (20 s); Senate 1,000-1,400 (1 s) | 30-45 min | House summaries (PDFs), journals (member votes), Senate committee votes |
| Mississippi | billstatus.ls.state.ms.us lists and history XML (session()), current members | 2015-2022 | 3,500-4,000 (1 s) | about 80 min | roll-call PDFs, veto messages; parties from today's members |
| New Mexico | nmlegis.gov list, bill pages, database, members file, fiscal impact reports | 2015-2022 | 2,000-3,000 (1 s) | about an hour | floor-vote PDFs, committee reports, messages |
| South Dakota | sdlegislature.gov/api (session(), votes skipped), Title Summaries | 2015-2022 | 1,000-1,200 (1 s) | about 20 min | member votes |
| Congress | GovInfo BILLSTATUS zips (bills()) + congress-legislators (members()) | 114th-116th (2015, 2017, 2019) | 8 | a few min | roll calls, veto messages |
| Tennessee | LegiScan dataset (states/legiscan_light.py); LEGISCAN_API_KEY | 2015, 2017, 2019, 2021 | 1 query (+1 list a day) | 1 min | contacts |
| Oklahoma | LegiScan datasets, both years of each Legislature | 2015, 2017, 2019, 2021 | 2 queries | 1 min | staff summaries (supplements), veto pages |
| Rhode Island | LegiScan dataset | 2015-2022 | 1 query | 1 min | chapters (as now) |
| Vermont | LegiScan dataset | 2015, 2017, 2019, 2021 | 1 query | 1 min | Legislative Counsel summaries |
| District of Columbia | LegiScan dataset + the Council's law library (laws.py's refresh(), table()) | 2015, 2017, 2019, 2021 (Periods 21-24) | 1 query + 600-1,000 GitHub files (0.25 s) | 5 min | contacts |

Each state is one run (`gh workflow run light-history.yml -f state=<st>`); the 340-minute limit covers every state but
Mississippi (about 11 hours: run it again, and it goes on from the first session not yet committed) and perhaps Missouri
and New Mexico. LegiScan's queries (about 35 for all five states) are counted in the runner's own data/legiscan/usage.json,
not the download job's: legiscan.py's 300-query margin covers them.

Tried locally (2026-11-24): Connecticut 2015 end to end (3,247 bills, 269 laws, 9 vetoes); Rhode Island 2015 end to end
(1,537 bills, 320 laws, 0 vetoes; the 2015 committee names "H.E.W", "Municipal Government" and "Government Oversight" are now
in states/ri/profile.py's COMMITTEE_TOPICS); Congress's 114th joint resolutions (41, 4 vetoed, as the record shows). The
others with one or two requests: Indiana's 2015 list and bill detail, Missouri's 2015 zip listing and Senate pages, Mississippi's 2015 list and history
file, New Mexico's 2015 session id, bill page and firs folder, California's 2015-2019 zips (same tables).

Fixed after the first GitHub runs (2026-11-24):
- Congress's 115th: its BILLSTATUS records have no "Became Public Law No:" line (only "Signed by President." and the law in
  `<laws>`), so 113 laws read as only presented (330 laws). convert.py now takes the law from `<laws>` when the bill itself
  was signed, presented or overridden (a bill whose text another enacted names that law too: HR 766 of the 119th, never
  out of committee, "119-120"). The 115th: 443 laws (442 public, 1 private), 0 vetoes; the 114th's 9 vetoes plus JASTA
  (overridden) are Obama's 10 that Congress, the 116th's 9 plus the FY2021 NDAA (overridden) Trump's 10. The 117th-119th
  convert exactly as before (stages, laws, key dates and actions compared).
- Connecticut: the FTP server times out from GitHub's runners (the archive listing failed for 2016-2018; 2015 and
  2019-2021 each lost a file or two), and nothing was written. light.py no longer needs the listing (the files are named
  by year) and asks again for what's missing, five rounds a minute apart; a session missing only the legislator
  spreadsheet is written without sponsors' parties. All seven sessions were written from clean scratch folders locally:
  2015 3,247 bills, 269 laws, 9 vetoes; 2016 1,126/236/8; 2017 3,431/265/6; 2018 1,138/206/7; 2019 3,641/236/3; 2020
  (the session cut short in March) 1,035/14/0; 2021 2,838/237/4. About a quarter of bills have no topic (old years have no
  committee referral file; topics come from subjects).

The build reads light sessions only back from the first full one without a gap (`load_light()`): a state whose 2023 is still
downloading (marked incomplete_2023) shows none until it's in.

A hook that writes through the state's profile (CA's save(), CT's flat_year() and texts(): `P.DATA`) sets `P.DATA` to the
scratch folder itself: states/light.py points it there only after `fetch()`, and puts the real one back.

## Third batch, first half (written 2026-11-24, not yet run on GitHub)

Each state's own fetch.py functions read the old sessions in today's formats (each checked with a few requests); two
needed a converter change for older wording, two a fetch.py fix, noted below. robots.txt read for each host first.

| state | source | sessions | requests a session (pace) | about | lacks |
|---|---|---|---|---|---|
| Alaska | akleg.gov/publicservice/basis (legislature_run(); /publicservice/ allowed) | 2015-2021 (29th-32nd) | list + 900-1,200 bills (1 s) | 30-45 min | sponsor statements, texts, fiscal notes |
| Alabama | ALISON GraphQL (read_bills(), read_history()) | 2015-2022 | 2-8 (1 s) | 1 min | roll calls, texts, summaries |
| Idaho | legislature.idaho.gov /sessioninfo/<year>/ (session()) | 2015-2022 | list + 550-700 bills + 25 committees (1 s) | 12-15 min | statements of purpose |
| Iowa | Open States bulk JSON (as 2023-24; never legis.iowa.gov) | 2015-2021 (86th-89th GA) | 1 | 1 min | needs each file's name in states/ia/light_bulk.json |
| Kentucky | apps.legislature.ky.gov/record/<yy>rs/ (session(); no robots.txt) | 2015-2022 | 15 lists + 800-1,300 bills (1 s) | 15-25 min | members of the time (today's only), vote and veto PDFs |
| Louisiana | legis.la.gov lists and BillInfo pages (session(); no robots.txt) | 2015-2022 | 15-30 lists + 1,000-2,300 bills (1 s) | 20-40 min | floor-vote, digest and veto PDFs |
| North Carolina | ncleg.gov feed and bill pages (session(); Crawl-delay 2) | 2015-2021 | feed + 2,000-2,300 bills (2 s) | 70-80 min | roll calls, so sponsors' parties; summaries |

- **Alabama**: 2015-2022's history is in a third wording (neither 2023's nor today's): `older_wording()` and `older_dates()` in
  convert.py ("Read for the first time and referred to the House of Representatives committee on ...", "Motion to Read a
  Third Time and Pass adopted Roll Call 123", "Delivered to Governor at 3:15 p.m. on March 21, 2018." undated but for its
  text, "Assigned Act No." undated, "Pending third reading on day 11 Favorable from X" the undated report, an override's
  "Veto to the Contrary Not Withstanding"). Told apart by the House's referral wording, case and all; 2025 converts as
  before. Written locally from full downloads: 2015 1,210 bills, 346 laws, 3 vetoes; 2018 922 / 298 / 5 (the press: 922
  introduced, 324 passed both houses, ours 323); 2022 873 / 291 / 0.
- **Kentucky**: 2015's record says "(Acts, ch. 127)" where today's says "(Acts Ch. 4)": convert.py's `CHAPTER` reads both.
  The record's vetoed and enrolled status lists don't open for 15rs (the bill pages decide stages anyway).
- **North Carolina**: 2015's bill pages' headings name no session law ("Senate Bill 2"; today "House Bill 3 / SL 2025-13"),
  so parse_bill() takes it from the history's "Ch. SL 2015-75" line when the heading has none (S2 of 2015 then reads as
  a law over the veto, as it was).
- **Louisiana**: a list range holding one bill answers with that bill's page (18RS's HB 901, 2018's last House bill):
  read_lists() reads it as the range's one row.
- **Iowa**: the 2015-21 files' names are listed only on open.pluralpolicy.com (the owner's login); the path was tested end to
  end with 2023-24's file (2,055 records, 352 laws, 2 vetoes, as the live site).

## Third batch, part b (written 2026-11-24, not yet run on GitHub)

Readers for states whose old sessions are in their current sources: each hook calls the state's own fetch.py functions
for an old session (members' votes, roll-call PDFs, committee records, texts and veto messages skipped), so the
converter reads them as it reads the window's years.

| state | source | sessions | requests a session (pace) | about | lacks |
|---|---|---|---|---|---|
| Ohio | LSC API v2 (session(): list, each bill's versions and actions) | 2015, 2017, 2019 (131st-133rd) | about 2,800 (three at a time) | 20-40 min | signing dates (the 131st-133rd versions carry none: a law is dated by its last action, HB 64 of 2015 by its 2016 line-item veto receipt); analyses |
| Georgia | SOAP services (session(): list, each bill's detail, members, committees; GetVote skipped) | 2015, 2017, 2019, 2021 | 1,900-2,700 (three at a time) | 30-45 min | members' votes, summaries (as now), veto messages |
| New Hampshire | public SQL Server (sql_year() for both years of the General Court, members_of()) + gc.nh.gov code tables | 2015-2022 | about 20 queries (1 s) + 5 pages (11 s crawl delay) | 2 min | analyses ("What it does"); old committee names read from the Docket keep journal page notes ("Commerce and Consumer Affairs Hj P. 18", "... (In Recess of"): their bills lose that committee's topic |
| Delaware | legis.delaware.gov (assembly_lists(), people(), assembly(); roll-call lists skipped) | 2015, 2017, 2019, 2021 (148th-151st) | 2,300-3,100 (1 s) | 40-55 min | roll calls by member, chapters on some bills (the 148th's pages say "N/A") |
| Nevada | NELIS (lists(), overviews(), members(), committees()) | 2015, 2017, 2019, 2021 (78th-81st) | 1,100-1,400 (1 s; Overviews take about 1.7 s) | 35-60 min | votes by member, committee minutes, veto messages (barred) |
| Wisconsin | docs.legis.wisconsin.gov (session(): lists, histories, LRB analyses, members, committees; roll calls, committee records, veto messages skipped) | 2015, 2017, 2019, 2021 | about 3,500-4,000 (1 s) | about an hour | votes by member, committee votes |
| West Virginia | wvlegislature.gov Bill_Status (members(), session(): lists and histories) | 2015-2022 | 2,000-2,500 (1 s) | 35-45 min | roll calls, drafters' notes; old sponsors' parties only where today's members have the name |
| Arizona | Open States bulk files (states/openstates_light.py), named in states/az/light_bulk.json | 2015-2022 | 1 download | 1 min | chapters; sponsors' parties (people.json's roles start in 2023) |
| Hawaii | Open States bulk files (both years of each Legislature), named in states/hi/light_bulk.json | 2015, 2017, 2019, 2021 | 2 downloads | 1 min | sponsors' parties (openstates_people.csv isn't in git) |

Tried locally (2026-11-24): New Hampshire 2015 and 2016 end to end (written: 869 bills, 274 laws, 11 vetoes; 1,057 bills,
330 laws, 13 vetoes; NHPR counted 330 laws and 13 vetoes in 2016, and 12 vetoes in 2015 counting the budget's HB 1 and
HB 2). One or a few bills each, converted: Ohio's 131st (HB 64), Georgia 2015 (HB 170, Act 46; SB 1), Delaware's 148th
(HB 450, HB 446: their passage lines are worded the old way, "Passed in House" and "Passed by Senate. Votes: Passed 21
YES ...", which convert.py's old_wording() now reads as today's; it changes none of 2023-26's lines), Nevada 2015 (AB 1,
AB 326 vetoed, SB 1 chapter 1; the official vetoed list has 7), Wisconsin 2015 (AB 1, AB 21, SB 21: 2015 Act 55). The
Open States path with the 2023 files on the owner's computer: Arizona 2023 205 laws and 143 vetoes, Hawaii 2023-24 516
laws and 18 vetoes. West Virginia wasn't tried: www.wvlegislature.gov didn't answer the owner's computer (GitHub's
runners read it daily), so its first run is the check. The Open States file names (each has an id) must come from the
owner: Arizona's 2015-2022 regular sessions ("AZ_52nd-1st-regular" ... "AZ_55th-2nd-regular") and Hawaii's 2015-2022
years, from open.pluralpolicy.com/data/session-json/ (login), into light_bulk.json (not bulk.json, whose names every
download imports into the site's own data).

## After the third batch's first runs (2026-11-25)

- **Resuming a session across runs:** states/light.py downloads into `$LIGHT_KEEP/<st>-<session>` when that's set (the
  workflow sets ~/light-keep, restored from and saved to an Actions cache per state, `light-keep-<st>-<run id>`; the
  reading step stops at 320 minutes so the save runs). A session that isn't finished keeps what it got, and the next run's
  fetch reads only what's missing; a written session's folder is deleted. Before this, a session longer than one run
  (Wisconsin's) could never finish.
- **West Virginia:** www.wvlegislature.gov answers nothing (connections time out) from GitHub's runners since at least
  2026-11-23 20:57 UTC, and from the owner's computer: the daily download fails the same way (every list "failed three
  times"; the site keeps the last copy). Not a reader problem; run `wv` again once the site answers.
- **Ohio:** the 131st-133rd's API answers some records with an empty body (HTTP 200, no JSON: about 15% of the 131st's
  versions, some actions too), counted as failures until 2026-11-25, so no session was ever whole; fetch.py's `LIGHT` mode
  (set by states/oh/light.py) reads them as "none" (the converter then takes the title and sponsors from the list's entry).
  The 132nd's legislation list answers HTTP 500 every time: its bills are found by number (`enumerate_bills()`: HB, SB,
  HJR, SJR 1, 2, ... until 25 in a row answer "[]"). Joint resolutions found that way lack the list's "CA:" title
  prefix, so the 132nd's proposed constitutional amendments may be left out. The reader retries a session's failed bills
  up to three passes.
- **Wisconsin:** from GitHub's machines each page took about 8 seconds (URLErrors on about one bill in three, retried), so
  2015-16 needed more than a run; the LRB analysis pages (/related/proposals/) are now left out (half the requests;
  "lacks" says summary), and the session resumes across runs.
- **Missouri:** every session stopped on "representatives" (each sitting member's own page, needed only for the live
  session); left out, and a session with under 1% of its Senate bills unreadable (2015's SB 631 and SB 796: HTTP 500 every
  time) is written without them.
- **New Hampshire 2021-22:** a docket line's own date that isn't a real date ("13/..."): `_real_day()` in convert.py
  falls back on the entry's day.
- **Alaska's 31st (2019-20):** 126 bills answered "FaultException" in one seven-minute stretch on 2026-11-24 (a server
  fault; they answer now): run again.
- **Kentucky, Mississippi, New Mexico:** only ran out of time (Kentucky's LRC record at about 9 seconds a request, about
  2.5 hours a session); runs resume.

## How the build uses them (stage 2, 2026-11-24)

`load_light()` in build_data.py reads the light sessions in an unbroken run back from the state's first full session (one
every `YEARS`; a gap stops it, so Wyoming's 2015-16 wait until 2017-2023 are in). They never join `SESSIONS`: no page, nav
button, search, issue or status file. They do count in:

- `insights()`: the odds chart, committee tables, timing, the steps' odds. What needs links between versions, co-sponsors'
  parties or the profile's governors (persistence, what happened to bills that died, the party table, the governor's
  counts) counts full sessions only; `insights.fullPast` names them, and the page's notes say those years.
- The Sessions table: each light session with a "*" and the note "No page on this site for these sessions: counted from
  each bill's outcome in the Legislature's records." (`DATA.lightSessions`, with each file's `lacks`).
- `trends()`: like for like, when any light session lacks summaries every session is matched on titles alone
  (`trends.titlesOnly`; the ⓘ then says "title").
- `write_compare()` / /compare/: each light session is a row of compare.json (with no "back next session" numbers); the
  page's "Sessions that began in" menu lists their years; "All finished sessions since 2023" is unchanged.
- "This bill in other sessions": `link_light()` links the first full session's bills to the light session just before
  (same sponsor surname, titles sharing at least three in four words, the best match only), shown with the light
  record's outcome and the Legislature's link (MT 30, ND 13, OR 18 bills); never to an earlier law or budget bill.
- Parties come from each file's header (`LIGHT_PARTIES`).
