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
