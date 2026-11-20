# Logic, wording, styles and data kept in more than one place

Inventory made 2026-11-19 by reading the code (not CLAUDE.md). Each entry: where the copies are, whether they agree
today, the risk, and where the one copy should live. Ranked by risk: the first ones already disagree, or would show a
visitor two different answers about the same bill.

## Done 2026-11-19 (items 1-5 of the first inventory)

`test/consistency.js` reads the same bills in every view (state Bills row and panel, state Watchlist, /your-bills/, the
front page's Your bills and search, issue pages and the front page's issue panel) and fails on any difference in the
status words, the watchlist group and deadline, or "New". `test/hash_check.py` checks the bill-number hash.

1. **The words for where a bill is: one copy.** `lists_pages/billfacts.js`: `BillFacts.words(S, f)` words the status
   from facts (`make(S, opt).factsOf(b)`: ended mid-session from `endedNote`/`heldAction`, carried over, Illinois's gate,
   the session's bills died, amendment and its second passage, sent to the voters, voters done; the profile's
   `stageText`, `passedBothText`, `executive`, `amendmentDone`). The state page uses it for its rows, panels and Watchlist
   (`statusParts()`, `watchRow()`); the build runs the same file in Node (`lists_pages/billlabels.js`, from
   build_data.py's `bill_labels()`) and writes the words into the status rows, the issue files and the search files, so
   the front page, issue pages, /your-bills/, /list/ and the list editor show them as written. Gone: watchrows.js's
   `where()`, home.html's `whereText()` and `STAGE_SHORT`, issues_site.py's `STAGES`/own wording, common.js's
   `whereText()`. The isAmendment/toVoters/secondPassage/ballotLine/votersDone/endedOf/billsDied/continuedTo helpers moved
   from tracker.html into billfacts.js (tracker.html keeps aliases).
2. **"New": one definition.** `BillFacts.newsDay(actions, routine)` (the latest day with an action that isn't paperwork:
   the state's `routine`, else `BillFacts.ROUTINE`) and `BillFacts.isNew(seen, day)`. The state page applies them to the
   bill's history; the build writes the day into the status row (its last column, left empty when it's the last
   action's day), which /your-bills/ (`freshStar()`) and the front page (`drawMine()`) read.
3. **/your-bills/ groups: the same inputs.** The status row's flags now carry what only the history tells: "e" ended
   before the session did, "r" a veto that can still be overridden, "d" decided by the voters, "a" an amendment, "2" its
   second passage. onelist.js passes them to `WR.canAct()` as tracker.html's `canActNow()` does, and the amendment's next
   step comes from `BillFacts.nextStep()` on both pages; `exec` is the profile's (`S.executive.title`).
4. **Watchlists in localStorage and the status reader: one copy.** `lists_pages/status.js` (`WKEY`, `readWatch`,
   `writeWatch`, `entryOf`, `statusIndex`, `statusOf`, `pieceOf`, `wholeStatus`, `rowOf`, `fmtDay`, `plainAct`), put by
   build_site.sh into the front page and, ahead of common.js, into the list pages. home.html and common.js lost their
   copies (the old `abt:watch` loop bug was already fixed in 8e2f58e).
5. **The bill-number hash: one JS copy.** `BillFacts.hash()`, used by tracker.html's `shardOf()` and status.js's
   `pieceOf()`; build_data.py's `shard_of()` is the Python side, and `test/hash_check.py SITE` runs both over every
   built state's numbers (4,497 on 2026-11-19: no difference).

On a build of NE, CO, VA, US, TN, NV, ND and DE (175 bills, about 800 views), the test found 204 differences before
(149 in the words, 45 in "New", 10 in the watchlist group or deadline) and none after. Found by it and left as they are:
Nebraska's appropriation bills share their bill's key ("LB525A" and "LB525" are both `2025:LB525`), so starring one
stars both on the state's Watchlist (the status row now keeps the bill numbered exactly); Nebraska's "LR19CA" is keyed
`LR19C` and `#LR19CA` doesn't open it, so it's missing from /your-bills/ and the search. Both need the key to stop
dropping a final letter that isn't a version letter.
Also new: the words depend on the day (a session's bills die, an election passes), so a state page and the build agree
only on the day the build ran (it runs daily).

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

Now one copy (lists_pages/status.js, 2026-11-19), still with New York's patterns only. Fix: the status row carries the
state page's own plain wording (`plainAction()`), written at build time.

## 9. Bill numbers as text (low-medium)

Maine's "HLD307" → "LD 307" and the space after the letters: status.js `numText()` (the front page and the list pages,
since 2026-11-19), watchrows.js `numText()`, issues_site.py (in the link text), states/me/profile.js `ld()`. Agree today.
Fix: one JS copy (status.js's, read by watchrows.js); issues_site.py writes the display number into bills.json.

## 10. Number search (low-medium)

home.html `numScore()` and the state-name parsing in its search, and lists_pages/edit.html `numScore()`, `stateIn()`,
`numbersIn()`: same code, two copies. Fix: move to status.js (already on both pages).

## 11. Colors (low: agree today)

- The teal (`--navy: #00777e`, dark `#4cc3be`) is written in tracker.html, home.html, lists_pages/common.css,
  about.html, notfound.html, lists_pages/welcome-ny.html and build_data.py (the legislator chooser page,
  `choose_page()`): 7 files.
- issues_site.py reads home.html's `:root` tokens (`tokens()`): one source, good.
- compare_site.py's `TOKENS` and `CSS` copy tracker.html's odds-chart colors and `.sankey` rules (agree today).

Fix: one tokens file (lists_pages/tokens.css) spliced into every page at build time, as rows.css is.

## 11a. A bill row's look (done 2026-11-20, with the "A · Tidied" bill design)

The status label had four copies of its CSS (home.html `.stg`, issues_site.py `.stg`, lists_pages/common.css `.stg`,
rows.css `.wr-stg`) and tracker.html had its own row pips (`.track .pip`) and status text (`.st`). Now one copy:
lists_pages/rows.css's `.pips`, `.stg` and `.stw`, put into every page that lists bills (tracker.html by build_data.py,
the list pages with common.css and home.html by build_site.sh, the issue pages by issues_site.py's `css()`). The pips'
HTML is `BillFacts.pips()` (lists_pages/billfacts.js) in every page's script. Left as copies:
- issues_site.py `pips()` writes the same pips in Python (the issue pages are written at build time); keep it in step
  with `BillFacts.pips()`. Both say a one-house legislature is Nebraska (`oneHouse()`); a state's own page reads its
  profile (`UNI`).
- The compact rows' layout (where the pips and label sit beside the number and title) is still each page's own:
  home.html's `.panel`, `.mine` and `.found`, issues_site.py's `ul.bills` and `.panel`, common.css's list rows. Only the
  parts are shared.
- tracker.html still has `.lineage .oc*` colors for "This bill in other sessions" (an outcome per session, not a bill's
  status label).

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
| State Bills list (tracker.html `billRow()`) | the page's own data (list part, rows part) | `BillFacts.words()` (`statusParts()`) | — | — | `numText`/profile |
| State bill panel (`fillDetail()`) | shard + stats part | `BillFacts.words()` (`statusParts()`), `nextSteps()` | own (`planFor()`) | — | profile |
| State Watchlist tab (`renderWatchView()` → `watchRow()`) | full bills | `BillFacts.words()` (`statusLabel()`) | shared rules, full inputs (`canActNow()`) | `BillFacts.isNew()` on the history | watchrows.js |
| /your-bills/ (`OneList.items()` → `itemOf()`) | status row (status.js `statusOf()`, `rowOf()`) + `profile.<hash>.js` + `/status.json` facts | the build's `BillFacts.words()` | shared rules, the row's flags (e, r, d, a, 2) | `BillFacts.isNew()` on the row's news day | watchrows.js |
| /your-bills/ and /list/ opened card | the state's page in a frame (`EMBED`) | tracker.html's | tracker.html's | tracker.html's | tracker.html's |
| /list/ rows for bills not in data | common.js `lookUp()` | the build's | — | — | status.js |
| Front page Your bills panel (`drawMine()`) | status row (status.js) | the build's | none | `BillFacts.isNew()` on the row's news day | status.js |
| Front page search (`run()`) | `search/<st>.json` | the build's (`w`) | — | — | status.js |
| Front page issue panel (`showPanel()`) | `issues/<id>/bills.json` | the build's | — | — | issues_site.py |
| Issue pages (`issues_site.py` `bill_items()`) | `data/issues_<session>.json` | the build's | — | — | issues_site.py |
| List editor (edit.html `drawBills()`) | `search/<st>.json` | the build's (`w`) | — | — | status.js |

`test/consistency.js` reads these views for a sample of bills (each stage, ended mid-session, amendments on first and
second passage, sent to the voters, Nebraska, Congress, past and prefiled sessions, bills on a national issue) and
compares them. /list/ isn't read (a shared list needs the lists Worker); its rows are the state page's card in a frame,
or `lookUp()`, the same words as /your-bills/.
