# Logic, wording, styles and data kept in more than one place

Inventory made 2026-11-19 by reading the code (not CLAUDE.md). Each entry: where the copies are, whether they agree
today, the risk, and where the one copy should live. Ranked by risk: the first ones already disagree, or would show a
visitor two different answers about the same bill.

## 1. The words for where a bill is (high: they disagree today)

Six places turn a stage number into words:

| Copy | Used by | Congress, stage 4 | Amendment passed (stage 3) | Nebraska, stage 3 |
|---|---|---|---|---|
| `tracker.html` `statusParts()` / `stageLong()` / `STATE.stageText`, `PASSED_BOTH`, `endedOf()` | state Bills list, panel | "the President" (`EXEC`) | the state's own (`amendmentFinal`, `amendmentDone`) | "Passed the Legislature" |
| `lists_pages/watchrows.js` `where()` | state Watchlist rows, common.js `whereText()` → /your-bills/, /list/ rows, editor | "On the President's desk" | "Constitutional amendment passed both houses"; Congress "Passed both houses; goes to the states" | "Passed both houses" |
| `home.html` `whereText()` (own copy, no state argument) | front page search results, Your bills panel | **"On the governor's desk"** | "Constitutional amendment passed both houses" (also for Congress) | "Passed both houses" |
| `home.html` `STAGE_SHORT` + inline rules in `showPanel()` | front page issue panel | **"Governor"** | "To voters" (also Congress) | "Passed both" |
| `issues_site.py` `stage_text()` / `STAGES` | issue pages | (Congress left out) | "Sent to the voters" (wrong for states where a first passage isn't the last) | "Passed the Legislature" |
| `stages.py` `STAGE_LABEL` | build logs only | — | — | — |

Disagreements now: a Congress bill on the President's desk reads "On the governor's desk" in the front page's search and
Your bills panel; the same Nebraska bill is "Passed the Legislature" on its page and issue page but "Passed both houses"
in its watchlist row and on the front page; an amendment is "Sent to the voters" on issue pages, "To voters" in the
front page panel, and "Constitutional amendment passed both houses" elsewhere. No copy but tracker.html knows a bill
that died mid-session (`endedNote`: floor defeat, withdrawn, replaced), so the others can say "On the floor" for a dead
bill.

Fix: one function in `watchrows.js` (`where(st, stage, comm, kind, live, up, extra)`), taking the state's words from its
profile (`passedBothText`, `executive`, `amendmentDone`), and an "ended" flag written into the status row by
`write_status()` (`endedOf()`'s answer worked out at build time). home.html should load it (it already has named.js
spliced in; add watchrows.js the same way) and issues_site.py should write the label into bills.json instead of
computing its own.

## 2. "New since you last looked" (high: three definitions)

- tracker.html `newActions()` / `hasNews()`: any action after the entry's `seen` day, skipping `ROUTINE` paperwork
  (`STATE.routine || WatchRows.ROUTINE`).
- lists_pages/yourbills.html `freshStar()`: the status row's last action is after `seen` and isn't routine (only the
  last action is known).
- home.html `drawMine()`: `last > seen`, no routine filter. So the front page can show "New" for paperwork the state's
  Watchlist doesn't count.

All three write `seen` the same way (`{...entry, seen: last}`): tracker `markSeen()`, home `markSeen()`, yourbills
`seeStar()`. Fix: one `isNew(entry, row, routine)` in common.js / watchrows.js, and a `routine` flag computed at build time
in the status row (so the status file decides, not three regexes).

## 3. Watchlist groups and deadlines on the state page vs /your-bills/ (high)

Both use `WatchRules` and `WatchRows.place()`, but with different inputs:

- tracker.html `watchRow()`: the full bill; `act` from `canActNow()` = `WR.canAct(b, WR.live(WR.standing(b), b.stage <= 2 && endedOf(b)), STATE.vetoReturns?.(b)?.live, votersDone(b))`;
  `next` hook for amendments ("Must pass again ..."); `exec: EXEC.title`.
- lists_pages/onelist.js `itemOf()`: a stand-in bill from the status row (no history, no versions' actions);
  `WR.canAct(bill, WR.live(WR.standing(bill), false), false, false)`; no `next` hook; `exec` "President"/"Governor".

So a bill that ended mid-session, a veto the next session can still override (NV), or an amendment the voters already
decided can sit in a different group on /your-bills/ than in the state's Watchlist tab; an amendment's "due" line differs.
Also any `originDeadline()` that reads the bill's history or versions sees an empty stand-in. Fix: write the facts only
the full bill knows (ended, vetoReturns live, voters done, the amendment's next step) into the status row at build time,
and have both pages pass them the same way. This is the first thing a consistency test should compare.

## 4. Reading watchlists from localStorage (high: one copy has a bug)

- tracker.html: `STORE`, `WATCH_STORE`, `loadWatch()`, `saveWatch()`, `setWatch()`, `moveNewYork()`.
- lists_pages/common.js: `WKEY`, `readWatch()`, `writeWatch()`, `entryOf()`, `allStarred()`.
- home.html: its own `WKEY`, `readWatch()`, `writeWatch()`, `starBtn()`, `starClick()`, `markSeen()`, and the loop in
  `drawMine()`.
- lists_pages/welcome-ny.html: merges New York's names.

They agree on the format (string or `{seen, stance}`). But `drawMine()` matches keys with
`/^abt:(?:([a-z]{2}):)?watch$/`, which also matches the old plain `abt:watch` (left in place by `moveNewYork()`), and then
calls `st.toUpperCase()` on `undefined`: the error is caught and ends the loop, so a browser that still has `abt:watch`
can show some or none of its starred bills on the front page. (common.js's `allStarred()` skips it safely.) Also the
comments at the top of common.js and in home.html (above `WKEY`) still say New York saves under `abt:watch`.

Fix: home.html should use common.js (splice it in as the list pages do) and drop its copies.

## 5. The status-file reader and the shard hash (medium: agree now; a mismatch would lose bills silently)

- FNV-1a of a bill's number without its letter: `build_data.py` `shard_of()`, tracker.html `shardOf()`,
  lists_pages/common.js `pieceOf()`, home.html `pieceOf()`. All four agree today. If one changes, bills "aren't found"
  or the page fetches the wrong shard.
- `statusOf()`, `statusIndex()`, `wholeStatus()`: common.js and home.html, identical except home.html uses relative
  paths (`status.json`) and common.js absolute ones (`/status.json`).

Fix: home.html loads common.js; a test that runs `shard_of()` and the JS `shardOf()` over every bill number of one state.

## 6. Python ports of page logic (medium: kept in step by hand)

- build_data.py `meeting_days()` ↔ tracker.html `walkCommittees()` / `meetings()` (the comment says "Keep the two in step").
- build_data.py `api_names()` ↔ tracker.html `setupLegislators()`.
- build_data.py `split_payload()`'s first 150 rows ↔ `sortBills()`'s "recent" order (if they differ, the first screen
  shows rows without titles until the rows part arrives).
- build_data.py reads profile.js with regular expressions: `write_compare()` (`oddsExits` and other chart settings) and
  the `endedNote` / `heldAction` hook check before `split_payload()`. A profile written differently (a getter, another
  spacing) is silently missed.

Fix: generate the JS side's inputs at build time where possible (the build already computes `meetingDays`); for the
profile, a small Node run that loads profile.js and prints the settings as JSON instead of regexes.

## 7. Settings written in both profile.py and profile.js (medium)

- Each year's last session day: `P.SESSION_ENDS` (al, fl, hi, ia) and `STATE.dated` in profile.js. They agree today
  (checked 2026-11-19; Hawaii's `dated` holds objects with `end`).
- `LOWER`/`houses`, `YEARS`/`years`, `TITLES`/`titles`, session labels (`session_label()` / `sessionLabel`).

Fix: one source per fact (JSON beside the profile, read by both), or a data_check test comparing them.

## 8. Plain wording of the last action (medium)

- tracker.html `plainAction()` / `PLAIN` and `STATE.actionWords` (Congress).
- lists_pages/common.js `plainAct()` and home.html `plainAct()` (identical copies), with New York's patterns only
  ("REFERRED TO", "DELIVERED TO GOVERNOR"), so other states' actions pass through as written and Congress says
  "governor" if a line matches.

Fix: one copy in common.js; ideally the status row carries the state page's own plain wording, written at build time.

## 9. Bill numbers as text (low-medium)

Maine's "HLD307" → "LD 307" and the space after the letters: common.js `numText()`, home.html `numText()`,
watchrows.js `numText()`, issues_site.py (in the link text), states/me/profile.js `ld()`. Agree today. Fix: watchrows.js's
copy only; issues_site.py writes the display number into bills.json.

## 10. Number search (low-medium)

home.html `numScore()` and the state-name parsing in its search, and lists_pages/edit.html `numScore()`, `stateIn()`,
`numbersIn()`: same code, two copies. Fix: move to common.js and load it on the front page.

## 11. Colors (low: agree today)

- The teal (`--navy: #00777e`, dark `#4cc3be`) is written in tracker.html, home.html, lists_pages/common.css,
  about.html, notfound.html, lists_pages/welcome-ny.html and build_data.py (the legislator chooser page,
  `choose_page()`): 7 files.
- issues_site.py reads home.html's `:root` tokens (`tokens()`): one source, good.
- compare_site.py's `TOKENS` and `CSS` copy tracker.html's odds-chart colors and `.sankey` rules (agree today).

Fix: one tokens file (lists_pages/tokens.css) spliced into every page at build time, as rows.css is.

## 12. ⓘ tips (low: different behavior, same look intended)

- tracker.html `TIP()`, `TIPI()`, `TIPR()`: a button whose text shows in one floating `#tipbox` (`showTip()`).
- lists_pages/common.js `infoTip()` with common.css `.info`: hover/focus CSS tooltip.
- issues_site.py: a `#partyInfo` button that opens a note below.

Fix: one component in common.js + common.css, used by tracker.html too.

## 13. Data tables in two languages (low: agree today)

- The tile map's `GRID`: home.html and issues_site.py (50 states, checked identical 2026-11-19).
- State names: common.js `NAMES` (lowercase keys), home.html `NAMES` (uppercase), each `P.STATE_NAME`.

---

## The same bill in different views

What each view computes itself and what it reads from shared code. This is the input for a consistency test: open one
bill in each view and compare the stage words, the group/deadline, "new", the number as shown, and the stance.

| View | Bill data from | Stage words | Group / deadline | "New" | Number shown |
|---|---|---|---|---|---|
| State Bills list (tracker.html `billRow()`) | the page's own data (list part, rows part) | own: `statusParts()` | — | — | `numText`/profile |
| State bill panel (`fillDetail()`) | shard + stats part | own: `statusParts()`, `nextSteps()` | own (`planFor()`) | — | profile |
| State Watchlist tab (`renderWatchView()` → `watchRow()`) | full bills | shared: `WatchRows.where()` | shared rules, full inputs (`canActNow()`) | own `newActions()` (all actions, routine skipped) | watchrows.js |
| /your-bills/ (`OneList.items()` → `itemOf()`) | status row (common.js `statusOf()`) + `profile.<hash>.js` + `/status.json` facts | shared: `WatchRows.where()` via `whereText()` | shared rules, stand-in inputs | own `freshStar()` (last action only) | watchrows.js |
| /your-bills/ and /list/ opened card | the state's page in a frame (`EMBED`) | tracker.html's own | tracker.html's | tracker.html's | tracker.html's |
| /list/ rows for bills not in data | common.js `lookUp()` | shared `whereText()` | — | — | common.js |
| Front page Your bills panel (`drawMine()`) | status row (home.html's own `statusOf()`) | own `whereText()` | none | own (`last > seen`) | home.html `numText()` |
| Front page search (`run()`) | `search/<st>.json` (stage, "c") | own `whereText()` | — | — | home.html `numText()` |
| Front page issue panel (`showPanel()`) | `issues/<id>/bills.json` | own `STAGE_SHORT` | — | — | issues_site.py |
| Issue pages (`issues_site.py` `bill_items()`) | `data/issues_<session>.json` | own `stage_text()` | — | — | issues_site.py |
| List editor (edit.html `drawBills()`) | `search/<st>.json` | shared `whereText()` | — | — | common.js |

A consistency test could, for a sample of bills per state (one per stage, plus an amendment, a Congress bill on the
President's desk, a Nebraska bill that passed, a bill that died mid-session), build the site once and compare: the
label from each column's function; `WatchRows.place()` with tracker's inputs vs onelist's; and "new" for an entry whose
`seen` is the day before the last action.
