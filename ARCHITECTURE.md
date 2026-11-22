# How State Bill Tracker fits together

A map of the code: what runs, in what order, what it reads and writes, and where to look when something is wrong.
Rules, decisions and each state's data quirks are in [CLAUDE.md](CLAUDE.md) (and, as they move there, `states/<st>/NOTES.md`).
Where this file and the code disagree, the code is right: fix this file.

Site: https://statebilltracker.pages.dev/ until launch (statebilltracker.org later). New York's live site,
albanybilltracker.org, runs from another repository; nothing here may change it.

## 1. The pipeline, end to end

```
download.yml (GitHub, every 2 h)       publish.yml (after each quick-lane download)          the browser
  states/<st>/fetch.py ... ──cache──►  build_site.sh                                     ──►  Cloudflare Pages
  (data/<st>/)                           build_data.py --state <st>  (per state, if changed)
                                           states/<st>/convert.py → records
                                           tracker.html + profile.js + how.html + lists_pages/*.js
                                         issues_site.py, compare_site.py, search_site.py
                                         front page (home.html), /your-bills/, /list/, /lists/edit/
```

### Downloading

- **One job per state**, in `.github/workflows/download.yml`. The list of jobs is `.github/states.json`: for each, `code`
  (data folder), `key` (its Actions cache), `paths`, `minutes` (time limit of the Download step) and `run` (the shell
  command). New Jersey's job also downloads Virginia; the `legiscan` job covers TN, OK, ME, RI, VT and the District of
  Columbia (DC also reads the Council's law library, `states/dc/laws.py`, and dccouncil.gov, `states/dc/contacts.py`).
- The commands are each state's `states/<st>/fetch.py`, usually followed by `states/<st>/contacts.py` (writes
  `data/<st>/contacts_<session>.json`). Shared downloaders:
  - `legiscan.py` (TN, OK, ME, RI, VT): LegiScan's API into `data/<st>/legiscan/<session_id>/`. Counts every query in
    `data/legiscan/usage.json` and stops at 9,000 a month (`MONTHLY_STOP`; the free tier is 10,000).
  - `states/openstates_bulk.py <st>` (AZ, HI, IA, FL): Open States bulk files as a first copy (files named in
    `states/<st>/bulk.json`); the API then fills in changes (`states/az/fetch.py`, `states/hi/fetch.py`,
    `states/ia/openstates.py`), sharing the free tier's 250 requests a day (HI stops at 110, IA at 100).
  - `listing_dates.py`: compares FTP/folder listing dates across daylight-saving changes (TX, IL, MI).
  - `states/window.py`: which years every state keeps (`years()`, `first_session()`, `shown()`, `settle()`).
  - `photos.py` (every job, its own "Add photos" step after the download): legislators' photos where the contacts have
    none, as `data/<st>/photos.json` (Open States' people file, official sites only; Congress: unitedstates/images;
    Louisiana: the Legislature's photos by seat). The source is downloaded again weekly (`photos_source.json`);
    build_data.py's `legislators()` reads it (`photos.image_of()`), and test/data_check.py LOOKs when under 80% have one.
- **Lanes.** The `plan` job reads the run history and splits states: **quick** (last three downloads all 30 minutes or
  less) and **slow** (first copies, crawl delays). Each lane's run starts the next two hours after it began (the `next`
  job); the cron (`5 */2 * * *`) is a backup that runs everything. Only the quick lane starts `publish.yml` (the
  `publish` job); slow-lane data goes out with the next quick publish.
- After a successful download the job writes `data/<st>/last_checked` (the page's "updated" time) and saves the
  folder to its cache only when something changed (or the mark is over 12 hours old).
- **Markers that keep a state off the site:** `data/<st>/incomplete` (first copy not finished: the state isn't built,
  or keeps its last build's pages), and `data/<st>/incomplete_<session>` (one older session left out: `window.mark()`,
  `window.shown()`).
- New York (since 2026-11-22) is a download.yml job like the others, `states/ny/fetch.py`: the Assembly memos
  (`states/ny/memos.py`), the bills from the Senate's API (`fetch_bills.py --if-changed`: only when the API lists an
  update; the next session's prefiled bills in November and December of even years; the session just ended until
  February 15 of odd years), Assembly floor votes (`fetch_assembly_votes.py`), committee agendas (`fetch_agendas.py`) and
  contacts once a day (`fetch_contacts.py`). Its files are at the top of `data/` (its cache, `ny-data-v1`, names them by
  pattern), with the memos, the "last checked" mark and `problems.txt` in `data/ny/`. Past sessions'
  `bills_<year>.json.gz` and starting copies of contacts and Assembly votes are in git. Nothing comes from the
  ny-bill-tracker repository any more. `check_site.py` runs `check_fresh.py` for it once a day.
- By hand: `gh workflow run download.yml -f states=wi` (one state, doesn't publish); `copy-data.yml` hands a state's
  cached data to your computer.

### Converting

- `build_data.py` loads `states/<st>/profile.py` as `P` and `states/<st>/convert.py` as `C`. A converter provides
  `C.sessions()` and `C.load_session(session)` → `(records, index by number, fetched, codes)`; optionally
  `C.agendas(session)` and `C.parties()`.
- A record is a dict with `nums`, `title`, `summary`, `stage` (0-6, `stages.py`), `comm`, `vers` (each version's
  actions), `keyDates`, `votes` (`[house, kind, committee, day, yes, no, [[member, code], ...]]`: kind "F" floor, "C"
  committee; "R" a committee report's signatures, AK and WA, code the recommendation's wording: shown in History by
  `reportLine()`, never counted as a vote), `topics`, `narrow`, `shell`, `budget`, `ballot`, `chapter`, `prev` ... The stage is
  decided here, from the history: this is where most "wrong status" bugs live.
- Shared converters: `states/legiscan_convert.py` (`Rules`, `load_session(Rules, session)`; each LegiScan state
  subclasses `Rules`), `states/openstates_bulk.py` (puts bulk records in the API's shape). New York's: `states/ny/convert.py`.
- Two Python packages are named after keywords (`states/or`, `states/in`): their files import each other with `importlib`.

### Building one state: `build_data.py --state <st> --github DIR`

`main()` loads every shown session, links bills across sessions, and for each session:

1. Works out statistics (`insights()`), profiles, networks, similar bills (`similar_bills()`), trends, contacts
   (`contacts_for()`, from `data/<st>/contacts_<session>.json`), party balance (`balance.py`), towns
   (`P.TOWNS_PATH`), agendas.
2. Writes the side files under `DIR/data/`:
   - `issues_<session>.json` (`write_issues()`, matching rules in `issues.py`),
   - `status_<session>.json` and its pieces `data/v/<session>.<hash>.t<k>.json` plus `data/status.json`
     (`write_status()`, `write_status_shards()`): where each bill is, for every page outside the state's own, with its
     status words, "New" day and watchlist flags from `bill_labels()` (which runs `lists_pages/billlabels.js` in Node:
     the page's own `billfacts.js` and the state's profile over every bill; the issues file carries the words too),
   - `data/v/profile.<hash>.js` (the state's `STATE` object, for /your-bills/),
   - `compare.json` (`write_compare()`, for /compare/),
   - `<session>-text/<letter><n>.json` ("What it does" pieces of 500 numbers, from `bill_texts()`, which reads
     `data/<st>/texts_<session>.json`).
3. Splits the page's data (`split_payload()`) into files under `data/v/`, each named by a hash of its contents:
   - **list part** (`<session>.<hash>.list.json`): every bill's numbers, stage, topics, sponsors, dates, places, plus
     titles and histories of the first 150 rows (`FIRST_ROWS`); legislators, contacts.
   - **rows part**: every bill's title, history and `ROW_COLS`.
   - **shards** (`.s<k>.json`, current session only): everything an opened bill shows. A bill's shard is FNV-1a of its
     number mod the shard count (`shard_of()` here, `shardOf()` in tracker.html).
   - **other parts** fetched on demand: `stats`, `net`, `search`, `votes`, `hist`, `cos`, `towns` (big towns lists).
   - a **past session** has no shards: list, rows, and one `more` file.
4. Assembles the page from `tracker.html` (written with New York's names, replaced here), splicing in:
   `states/<st>/how.html` (How tab), `states/<st>/weighin.html`, `lists_pages/watchrules.js` + `billfacts.js` +
   `watchrows.js` (`<script id="watch-rules">`), `lists_pages/rows.css` (at `/*rows.css*/`), `lists_pages/sankey.js`
   (`<script id="sankey">`), `states/<st>/profile.js` (`<script id="state-profile">`, via `state_profile_js()`) and, on
   the public site, `lists_pages/named.js` (`github_page()`). The data tag `#bill-data` names the part files
   (`data-src`, `data-parts`, `data-shards`, `data-texts`); `frame_tabs()` and `sessions_nav()` pre-draw the frame.
   On the public site `github_page()` then moves the styles and shared scripts out of each page into files named by
   their contents (`asset_file()`): `/assets/app.<hash>.css` (tracker.html's styles with rows.css, a `<link>` in the
   head), `/assets/lib.<hash>.js` (named.js, watchrules.js, billfacts.js, watchrows.js, sankey.js) and
   `/assets/app.<hash>.js` (the main script), ordinary blocking `<script src>` tags where the inline ones were (so the
   order is unchanged), preloaded from the head. The state's profile, `#page-names` (the two names the build writes in:
   `SITE_TITLE`, `LEGISLATURE_NAME`) and the data tag stay in the page. The files are the same for every state:
   build_site.sh moves each state's `assets/` to the site's top, one copy, kept by browsers for good (`_headers`). A
   page is about 40 KB instead of 580 KB; a change to tracker.html uploads three new files plus the small pages. The
   Claude copies keep everything inline.
   - **Fonts** are the site's own (`site_fonts.py`, files in `fonts/`, made by `tools/subset_fonts.py`; OFL licenses
     beside them): every source page keeps its Google Fonts lines (for the Claude copies and for viewing unbuilt), and
     the build swaps them for `@font-face` rules (`site_fonts.swap_google()`; on state pages at the top of app.css),
     files at `/assets/fonts/<name>.<hash>.woff2`.
5. Writes `index.html` (current session), `<year>.html` (others), `/<slug>/index.html` per legislator,
   `/governor/index.html` (Congress: `/president/`, `GOV_SLUG`), `/watchlist/index.html`.

Without `--github` it writes `site/<st>/<session>.html` with all data embedded (gzip+base64): the Claude copies.

### Building the whole site: `./build_site.sh [DIR]`

- Builds each state with `build_one` (4 at a time, biggest data first) into `built/<st>/`, unless `state_hash.py <st>`
  matches `built/<st>.hash` (then the last build is copied). The hash covers the state's data, the shared code, the
  state's folder and New York's (the fallback settings), `SITE_BASE`, `LAUNCHED` and **today's date**, so every state
  rebuilds at least daily. Outcome per state in `built/<st>.result` (rebuilt / failed / copy / skip), log in
  `built/<st>.log`. A failed state keeps its last pages.
- **What's worked out from the data is kept** (`built/cache/<st>/`, `BUILD_CACHE`; `.build-cache/` for build_data.py
  run alone): `bundle.pickle.gz`, build_data.py's `compute()` result per session (the split data files, the inputs of
  the issues, status and status-words files), keyed by `bundle_key()`: `state_hash.data_files()` (the state's data and
  all the build's Python code), the site's address and today's date. A change to the page's code only (`state_hash.
  page_files()`: tracker.html, lists_pages/*.js/css, the state's profile.js, how.html, weighin.html, issues.py) matches
  the key, and the build writes only the pages and page-dependent files ("data unchanged: pages only" in the log):
  seconds per state instead of minutes. Also kept: each bill's issue matches (`issues_<session>.json.gz`, keyed by its
  text and issues.py), billlabels.js's answers (`labels_<session>`), and, on a new day or new data, the last bundle's
  similar bills and split files where their inputs are unchanged. `BUILD_CACHE=off` works everything out.
- Then, from the built states: `issues_site.py` (/issues/, `issues/summary.json`, `issues/<id>/bills.json`),
  `compare_site.py` (/compare/, `compare/summary.json`), `search_site.py` (`search/<st>.json`, `search/topics.json`),
  `/status.json` (every state's `data/status.json`), the front page (home.html with JSON blocks `#issues`, `#compare`,
  `#power` from `front_page.map_data()`, `#after` from `front_page.next_data()`, `#past` from
  `states/party_history.json`), /about/, /your-bills/, /list/, /lists/edit/ (from `lists_pages/*.html` with
  `common.css`+`rows.css`, `billfacts.js`+`status.js`+`common.js`+`watchrows.js`, `named.js`, `embed.js`, `watchrules.js`,
  `onelist.js` spliced at `/*name*/` markers; the front page gets `billfacts.js`, `status.js` and `named.js` the same way), /welcome/ny/, `_headers`, `robots.txt`, 404.html.
- Fails above 19,500 files (Cloudflare Pages' limit is 20,000 a deployment).
- `ONLY="wy sd" ./build_site.sh /tmp/out` builds a few states locally.

### Publishing: `.github/workflows/publish.yml`

- Triggers: each quick-lane download run (`from_download=true`), by hand (`gh workflow run publish.yml`), and daily at
  10:50 UTC (which also runs the data checks). One publish at a time (`concurrency: site`, queued, never cancelled).
- Restores every state's cache (one step per state, New York's included: `check_site.py` fails if a state in
  states.json has none) and the `built/` cache, runs `build_site.sh _site` with `SITE_BASE=https://statebilltracker.pages.dev/`,
  notes each state's bill counts in `built/freshness.json` (`check_site.py --record`, for the daily check), saves `built/` (and deletes all but the newest two `built-pages-` copies: `tools/prune_caches.py`, which download.yml
  runs for each state's copies too), and deploys with `wrangler pages deploy` (project `statebilltracker`) only if some state was rebuilt
  (or it was started by hand).
- After deploying, every run (rebuilt or not): `tools/agenda_seen.py` logs, per state, when each bill first showed up on
  a committee agenda, to measure how much notice each state gives (collected since 2026-11-22; no page yet). It reads
  the live sessions' `_site/<st>/data/status_<session>.json` (whose rows carry the meetings to come), not the
  converters, and nothing in the build reads its logs. One file per state, `agenda_log/<st>.json`, in its own cache
  (`agenda-log-<run>`, saved every run, older copies pruned); each item keyed session|bill|committee|meeting time, with
  the run that first saw it, the state's `last_checked` then and at the run before (the 2-hour window), when it
  disappeared, and marks for items already listed when the log began or seen after a gap of over 12 hours.
  `python3 tools/agenda_seen.py --report --logs DIR` prints each state's notice (median, 10th and 90th percentile, in
  days); the step prints it in each publish run's log.
- A state whose build failed fails the run after deploying ("The build failed for: ..."), so GitHub emails the owner.

### Checking

| Check | Runs | Reports |
|---|---|---|
| `test/check.sh` | by hand, after editing tracker.html or build_data.py | terminal. Builds **New York** (`data/bills_*.json`), parses scripts, finds duplicate functions, clicks every control in headless Chrome (`test/crawl.js`) |
| `test/same.sh [commit]` | by hand, for changes that shouldn't change what visitors see | terminal; compares snapshots (`test/snapshot.js`) |
| `test/data_check.py [st ...]` | by hand after any converter change; daily in publish.yml | FAIL/LOOK lines, ends "`N problem(s)`"; nonzero exit fails the run |
| `check_site.py` | daily in publish.yml | contacts fresh and plentiful, NJ/CA texts present, VA date rule, publish.yml restores every state; each state's data still updating (`freshness()`): last successful download (`data/<st>/last_checked`; warn over 26 h, FAIL over 48 h; New York's is `check_fresh.py`'s), the Download step failing in each of a job's last 6-12 runs (FAIL) or half of them (warn), a live session's bill count down 2% and 5 bills from the last build of an earlier day (FAIL; `built/freshness.json`, written by `check_site.py --record` after every build), and, in session only (floor votes this year, before the day past same-parity years' last big floor-vote days say it ends), no new bill action for more than max(14, the state's usual quiet spell + 7) days (FAIL; half that warns). Warnings go to the run's summary only. Test with `CHECK_DATA`, `CHECK_BUILT`, `CHECK_TODAY` |
| `test/site_check.js` (site-check.yml, 11:30 UTC) | daily, against the live site | freshness (8 h quick lane, 30 h others), bill counts, script errors, phone-width overflow, axe-core, keyboard; ends "`N problems:`" |
| `test/issues/get.py`, `check.py` | by hand, after an issue rule change | samples of matches to read |
| `test/consistency.js` | by hand, against a local build (`ONLY="ne co va us tn nv nd de" SITE_BASE=http://localhost:8766/ ./build_site.sh DIR`, served) | FAIL when a bill's status words, watchlist group and deadline, or "New" differ between views; ends "`N problem(s)`" |
| `test/ports_check.js SITE`, `test/profile_check.py`, `test/tokens_check.py` | in `test/check.sh` | FAIL when the build's Python copies of page logic, profile.py and profile.js, or the pages' shared color tokens disagree (notes/duplication.md) |
| `test/hash_check.py SITE` | by hand, after touching `shard_of()` or `BillFacts.hash()` | FAIL on bill numbers the two place differently |
| `node test/deadlines.js` | in check.sh; daily in publish.yml | FAIL when a state's `govDeadline()` gives another day than its constitution's rule for a case in its table; KNOWN for recorded differences not yet fixed |
| `test/cache_key_check.py [st]` | in check.sh (Wyoming) and weekly in cache-check.yml | FAIL on a file the build imports (every state) or opens (one state's build, audit hook) that `state_hash.py`'s lists leave out, or that compute() reads but only `page_files()` lists |
| `test/cache_same.sh st ...` | weekly in cache-check.yml (WY, SD, RI, from publish's `built/cache`); by hand | FAIL when a build from the cache differs from one with `BUILD_CACHE=off` |

**Who sees failures:** only the owner, by GitHub's emails. A Claude session sees nothing unless it looks:
`gh run list --workflow publish.yml`, `gh run list --workflow site-check.yml`, `gh run view <id> --log-failed`.
`update.yml` (New York's old workflow, by hand only), `check_fresh.py` and `fingerprint.py` belong to it and don't run here.

## 2. Where each thing a visitor sees is drawn

### A state's page (`/<st>/`, `tracker.html`)

One script; `STATE` (the state's profile) is defined before it. Start-up: `hydrate()` → `wire()` (all event handlers)
→ `render()`. Data arrives on demand: `readParts()`, `need(part)`, `needBills()`, `needShard()`, `prefetchBill()`,
`getJson()` (a 404 re-reads the page for the new file names: `rename()`), merged by `MERGE`; hidden tabs are drawn when
opened (`later()`, `STALE`, `showView()`).

- **Bills tab** (`#view-bills`): filters `matches()`, `parseQuery()`, `sortBills()`; "Where it is now"
  `renderPipeline()`; topics `renderTopics()`; the Issue filter `loadIssues()`/`fillIssues()`; list `renderList()`.
- **A bill row:** `billRow()` → `statusText()`/`statusParts()` (the status words: `BillFacts.words()` from `BF.factsOf(b)`,
  lists_pages/billfacts.js, the same words every other view shows; the line under them: `STATE.stageText`,
  `endedOf()`, `STATE.endedNote`), `track()` (the pips: `BillFacts.pips()`), `panelTags()`, `partyTag()`, `watchButton()`.
  Every view's bill row has the same parts, styled once in lists_pages/rows.css (`.pips`, the status label `.stg`, the
  grey date line `.stw`): the Bills list, the Watchlist tab and /your-bills/ (watchrows.js), and at a compact size the
  front page's lists, /list/, the list editor and the issue pages (issues_site.py's `pips()` is the Python copy).
- **The opened panel:** `fillDetail()`, indented under the title with a rule down its left, in this order: "What you can
  do" (`nextSteps()` / `planFor()` / `contactBook()` / `holdUp()`, `oddsLine()`; `draftFor()` writes the email), "What
  it does" (the summary, `whatItDoes()`/`loadBillText()`), "History" (`historyBlock()`: the main steps with each passing
  floor vote's tally on its line, other votes on their own, committee reports' signatures (`reportLine()`), the governor's due date last), "Who sponsors it"
  (`sponsorsBlock()`, `panelTags()`), `chapterAmendment()`, `signingMemo()`, `vetoMemo()`, `twinLine()`, `lineage()`,
  `similarBlock()`, `verBlock()` (each version's "Every action"), then the official links (`STATE.textLinks()`) and "Copy
  link to this bill". `vetoMemo()` shows a record's `vetoMemo` (build_data.py's `veto_note()`); a message read from a
  scanned letter by OCR (states/letters.py's `scanned()`/`ocr_letter()`: WY, MT, OR, SC, NC, AZ, KY, TX, a few WI) carries
  the letter's address and ends with "Read from a scanned letter; a word may be off. Original letter ↗". A watchlist card opened below its row (`watchCard(x, true)`) is the same panel: its own "What you
  can do" (`.wcan`), then `fillDetail()` of a `details.morebill.inplace`. `historyTags()`.
- **Where you live** (`#whereBox`): `renderMyReps()`, `myReps()`, `setCounty()`, `setTown()`, `setRegion()` (Congress),
  `renderTownReps()`, `renderTownRepsByHouse()`, `lookUpReps()` (Census geocoder's 2026 districts, `STATE.addressLookup`, public
  site only; `censusDistrict()` matches named districts to `DATA.districtNames`, `floterials()` adds New Hampshire's).
- **Watchlist tab** (`#view-watch`): `renderWatchView()`. Its rows, groups and order come from
  `lists_pages/watchrows.js` (`WatchRows.place()`, `.draw()`; the words are `statusLabel()`'s) with deadlines from `lists_pages/watchrules.js`
  (`WR = WatchRules.make(STATE, ...)`; `deadlineOf()` and `W_GROUPS` are aliases). The card: `watchCard()`,
  `keyAction()`, `logBlock()`. News: `newActions()`, `newsBox()`, `updateWatchTab()`. Sharing: `shareBox()`,
  `publishAction()`, `schedulePub()`/`savePub()`. Embedded in /list/ and /your-bills/ frames: `EMBED`, `embedCard()`,
  `embedShow()`, `embedSize()`.
- **Statistics tab:** `renderStats()`, `sankey()` (draws with `lists_pages/sankey.js`), `monthChart()`, `renderNet()`,
  `renderWho()`, `renderTrends()`, `renderOutcomes()`.
- **How tab:** `showHowSec()`, `renderHowComm()` (`STATE.commPairs`), `renderHowCal()`; text from `states/<st>/how.html`.
- **Legislator pages** (`/<st>/<slug>/`, `PRESET.who`): `renderPerson()`, `renderPersonStats()` ("Their numbers"),
  `renderOpenNow()` / `comingUp()` ("Open for comment").
- **/<st>/governor/** (Congress: /us/president/; `PRESET.gov`, `frame_tabs(..., "gov")`): `renderGovCard()` (name, party,
  since: the list part's `govNow`; `GOV_REACH`), `renderGov()` in `#govRec` (the Record view; no tabs on
  this page): the desk (stage 4, by `b.due`), this session's decisions by the governor in office (`GOV_KINDS`: signed,
  without signature, vetoed, overridden), earlier sessions (the stats part's `govRecord`, `governor_record()`) and vetoes
  with a message (`vetoMsgs`). Linked from the party line's Governor panel and decided bills' "What you can do" (`govLink()`).
- **/<st>/watchlist/**: the same page with `frame_tabs(..., "watch")`.
- Notice above the tabs: `sessionNotice()`, `shortNotice()`, `staleNotice()`. Analytics: `countUse()`, `countOnce()`.

### Pages across states

| Page | Source | Main functions |
|---|---|---|
| Front page `/` | `home.html` (+ `named.js`) | map `drawMap()`, `control()`, `partyPanel()`; Show menu `render()`; issue view `drawIssue()`, `showPanel()` (reads `issues/<id>/bills.json`), `drawChart()`; "Bills that became law" `lawsView()`; Your bills panel `drawMine()`, `starClick()`, `markSeen()`, `mineView()`; search `prep()`, `load()`, `parse()`, `numScore()`, `run()`, `searchView()` (reads `search/<st>.json`) |
| `/issues/`, `/issues/<id>/` | `issues_site.py` | `main()`, `issue_page()`, `tile_map()`, `bill_items()`, `stage_text()` (the build's words, from the issues file) |
| `/compare/` | `compare_site.py` | `page()`, `latest()`; chart from `sankey.js` |
| `/your-bills/` | `lists_pages/yourbills.html` | tabs `syncTabs()`, `drawStrip()`; `drawStarred()`, `drawLists()`, `drawFollows()`; rows via `OneList.items()`/`.draw()` (`onelist.js`); a row opens the state's card in a frame (`embed.js`'s `Opener`) |
| `/list/#<slug>` | `lists_pages/list.html` | `load()`, `redraw()`, `drawButtons()`; `Frames.show()` with `listGroups()` (embed.js): each state's page draws its bills |
| `/lists/edit/` | `lists_pages/edit.html` | `openList()`, `drawBills()`, `addBill()`, `search()`, `save()` |
| `/about/`, 404 | `about.html`, `notfound.html` | static |
| `/welcome/ny/` | `lists_pages/welcome-ny.html` | takes New York visitors' saved data from albanybilltracker.org's forwarding pages |

## 3. Shared code and settings

- `lists_pages/billfacts.js` (`BillFacts`): **the status words** (`words(S, f)`), the facts they need from a bill's
  history (`make(S, opt).factsOf(b)`: ended mid-session, carried over, amendments and second passage, sent to the voters,
  the session's bills died), an amendment's next step (`nextStep`), "New" (`newsDay`, `isNew`), the bill-number hash
  (`hash`, = build_data.py's `shard_of()`), `runProfile` (a profile outside its page), an action in plain words
  (`make(S).plainAction()`, `newsWhat()`, `latestNews()`: the build writes the last into the status rows) and a bill
  number as shown (`numText`). On state pages, the list pages,
  the front page, and in the build (`lists_pages/billlabels.js`, run by `bill_labels()` in build_data.py).
- `lists_pages/status.js` (the front page and the list pages): watchlist storage (`WKEY`, `readWatch`, `writeWatch`,
  `entryOf`), the status reader (`statusIndex`, `statusOf`, `pieceOf`, `wholeStatus`, `rowOf`: a status row's columns by
  name), `fmtDay`, `numText`, and the number search (`BillSearch`: home.html's and the list editor's).
- `lists_pages/common.js` (/your-bills/, /list/, /lists/edit/): state names `NAMES`, `esc`, `countUse`, `infoTip`,
  `allStarred`, `lookUp`, `billRow`, the lists Worker (`api`, `myList`, `readFollows`, `readNamed`).
- `lists_pages/watchrules.js` (`WatchRules`): deadlines and groups; read by tracker.html, onelist.js and the build.
- `lists_pages/watchrows.js` (`WatchRows`): the watchlist's rows and groups, news box; `rows.css` styles them (classes
  `wr-*`).
- `lists_pages/onelist.js` (`OneList`): /your-bills/'s list across states; runs each state's `profile.<hash>.js`.
- `lists_pages/embed.js` (`Frames`, `Opener`, `listCodes`, `listGroups`): state pages in frames at `#embed=...`.
- `lists_pages/named.js` (`NamedLists`): the list button beside each star; on state pages, the front page, the editor.
- `lists_pages/sankey.js` (`drawSankey`): the odds chart, for the Statistics tab and /compare/.
- `lists_pages/common.css`: styles for the three list pages.
- Python: `governors.py` (`in_office()`: who is governor today, from `P.GOVERNORS` and `states/legislatures.json`;
  `apply_leaders()`), `balance.py` (seats by party), `states/window.py`, `stages.py`, `issues.py` (issue rules),
  `site_meta.py` (link previews, analytics, `SUPPORT`), `states/legislatures.json` (seats, override rule, governor).
- **The profile.** `states/<st>/profile.py` (Python: `DATA`, `SITE_DIR`, `STATE_NAME`, `LOWER`, `YEARS`, `GOVERNORS`,
  `LEADERS`, `TOPICS`, `TOWNS_PATH`, `TIMEZONE`, `session_of()`, `session_label()`) and `states/<st>/profile.js` (the
  `STATE` object). Main hooks: `code`, `houses`, `years`, `sessionLabel`, `stageText`, `govDeadline`, `passedBothBy`,
  `sessionEnds`, `opens`, `dated`, `originDeadline`, `endedNote`, `heldAction`, `amendments`/`amendmentOnce`/
  `amendmentFinal`, `gates`, `lawWord`, `vetoReturns`, `executive` (Congress), `listsApi`. **A missing setting falls
  back to New York's wording, silently.**
- **Saved in the browser** (localStorage): per state `abt:<st>:watch`, `:log`, `:stance`, `:reps`, `:county`,
  `:whoorder`, `:visit`, `:lastvisit`, `:statsec`, `:howsec`, `:commmode`, `:commsort`, `:carried:<session>`,
  `:published:<session>`, `:pubtext:<session>` (prefix `STORE` in tracker.html; New York's are
  `abt:ny:` since `moveNewYork()`, which copies its old plain `abt:...` names once). Site-wide: `abt:lists` (named
  lists), `abt:all:published`, `abt:follows`, `abt:supportnote`, `abt:issueview`, `abt:tabseen`,
  `abt:yourbills:tab` / `:recent` / `:bystate` / `:rows`.

## 4. Outside services

- **Cloudflare Pages**, project `statebilltracker` (secrets `CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID`).
- **Workers:** `state-lists` (`lists_worker/`, KV namespace STATE_LISTS bound as `LISTS`; secret `ADMIN_TOKEN`; every
  profile's `listsApi`); `state-cron` (`cron_worker/`, no timer); `state-ga-relay` (`ga_relay_worker/`, no storage; secret
  `RELAY_KEY`): fetches public www.legis.ga.gov/api/document/ files (Daily Reports, agendas) for states/ga/daily.py, which
  GitHub's runners can't reach (their connections time out; Cloudflare's network is answered normally); daily.py tries
  directly first and uses it only through `GA_RELAY_URL` / `GA_RELAY_KEY` (GitHub secrets, download.yml's Download step).
  Never deploy as, or bind to, the live NY site's
  `albany-lists` / `albany-cron` or its LISTS namespace. `lists_admin.py` manages lists and codes (token from
  `LISTS_ADMIN_TOKEN` or `~/.state_lists_admin`); `lists-backup.yml` exports (`tools/lists_backup.py`, paged `/admin/export`) and encrypts daily (`LISTS_BACKUP_KEY`), kept 90 days; restore steps in `tools/lists_backup.py`.
- **Keys** (names only): GitHub secrets `NYSENATE_API_KEY`, `OPENSTATES_API_KEY`, `UTAH_API_TOKEN`, `INDIANA_API_KEY`,
  `LEGISCAN_API_KEY`, `LISTS_ADMIN_TOKEN`, `LISTS_BACKUP_KEY`, `GA_RELAY_URL`, `GA_RELAY_KEY` (the relay Worker's
  `RELAY_KEY`; kept nowhere else); on the owner's computer `~/.nysenate_api_key`,
  `~/.openstates_api_key`, `~/.utah_api_token`, `~/.indiana_api_key`, `~/.legiscan_api_key`, `~/.state_lists_admin`,
  `~/.state_lists_backup_key`. The repository is public: never print or commit one.
- **Quotas:** LegiScan 10,000 queries a month (stops at 9,000); Open States 250 requests a day shared by AZ, HI, IA, and
  by local runs; Cloudflare Pages 500 deploys a month and 20,000 files a deploy; KV free tier 1,000 writes a day.
- **Analytics:** GoatCounter (`statebilltracker`), only once `LAUNCHED=1`.

## 5. Troubleshooting: if X looks wrong, look at Y first

- **A bill's stage or status is wrong.** The stage comes from `states/<st>/convert.py` (or `legiscan_convert.py`'s
  `work_out()` and the state's `decode()`). Load the session (`C.load_session(year)[0]`) and look at the record's `vers`
  actions and `stage`; about 19 converters also print totals against the official lists with
  `python3 -m states.<st>.convert`. Then `python3 test/data_check.py <st>` and read CLAUDE.md's
  "Data traps". If the stage is right but the words are wrong, see the next item.
- **The words for where a bill is differ between pages.** They all come from `BillFacts.words()`
  (lists_pages/billfacts.js): the state's page works them out in the browser, every other view shows what the build
  wrote (`bill_labels()` → status rows, issue files, search files). A difference means the build's run of a profile hook
  failed or saw other data (billlabels.js catches a hook's error and leaves that fact out), or the page and the build ran on
  different days. `test/consistency.js` compares every view on a local build.
- **A deadline or watchlist group is wrong.** `lists_pages/watchrules.js` (`deadlineOf`, `canAct`) with the profile's
  `govDeadline`, `passedBothBy`, `sessionEnds`, `originDeadline`, `dated`; then `WatchRows.place()`. On /your-bills/ the
  same rules run on a stand-in bill built from the status row (`onelist.js` `itemOf()`), with the facts `f` from
  `/status.json` (`write_status_shards()`).
- **The state Watchlist and Your bills disagree.** /your-bills/ has no history: what it needs from one comes as the status
  row's flags ("e" ended, "r" veto still open, "d" voters done, "a"/"2" amendment and second passage) and its "New" day,
  from the build. Compare `watchRow()`/`canActNow()` in tracker.html with `itemOf()` in onelist.js; `test/consistency.js`
  compares the groups and deadlines.
- **A page change isn't live.** Is a publish queued or running? `gh run list --workflow publish.yml`. A run can take
  35-50 minutes when many states rebuild, and runs queue one at a time. Did it deploy? A run started by a download
  deploys only if some state was rebuilt; start one by hand to force it. Did the change reach `state_hash.py`'s list?
  A file it doesn't cover (front page, issue pages) needs no state rebuild, but a new shared file a state page uses must
  be added there, or states keep their old pages until tomorrow.
- **The daily site check failed.** `gh run list --workflow site-check.yml`, then `gh run view <id> --log` and read from
  the line "`N problems:`" (FAIL lines first, then LOOK). For data checks, the publish run's "Check every state..." step:
  read from "`N problem(s)`". Run one state again: `gh workflow run site-check.yml -f states=wy`.
- **A state is missing from the site.** `data/<st>/incomplete` (first copy not done), no data yet (cache empty), or its
  build failed (publish run log: "BUILD FAILED" with the last 40 lines). Is it in `.github/states.json`, publish.yml's
  restore steps and `build_site.sh`'s `STATES`? A missing older session: `data/<st>/incomplete_<session>`.
- **A state is stale ("updated" old).** Its download job in the latest download.yml run (timed out? `continue-on-error`
  hides a failed Download step: read its log); `data/<st>/last_checked` is written only after a successful download.
  Which lane it's in is printed by the `plan` job.
- **Contacts wrong** (phone, email, committee, party). `states/<st>/contacts.py` → `data/<st>/contacts_<session>.json`
  → `contacts_for()` in build_data.py → `contactBook()` / `phonesHtml()` / `emailHtml()` / `formHtml()` in tracker.html.
  Governor contacts: the profile's `govReach`. Leaders: `P.LEADERS`, `governors.apply_leaders()`.
- **A 404 on a data file.** Files in `data/v/` are named by content and replaced on each build; a page open across a
  deploy re-reads its own HTML for the new names once (`rename()`). Repeated 404s mean the page and its files came from
  different builds, or `_headers` cached an old page. Status pieces fall back to `status_<session>.json`.
- **Phone layout overflows.** Check `document.documentElement.scrollWidth` with a bill open in a 375px frame; shared class
  names (`.key`, `.more`, `.num`) are the usual cause. `test/site_check.js` reports these per state.
- **Wrong governor or leader.** `governors.in_office()` reads `P.GOVERNORS` by date; never the list's last entry.
- **Issue page counts wrong.** `issues.py` rules → `write_issues()` → `issues_site.py`. Check with `test/issues/get.py`.
- **Search doesn't find a bill.** `search_site.py` reads only live sessions' `status_<session>.json`; home.html's
  `parse()` and status.js's `BillSearch.numScore()` match numbers.
- **The build is near the file limit.** build_site.sh prints the count; shards (`SHARD_GZ`) and status pieces
  (`STATUS_GZ`) are the files that grow.
