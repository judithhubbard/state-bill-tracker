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
