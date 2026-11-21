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

## Done 2026-11-21 (items 6-13)

Where the build (Python) and the pages (JavaScript) must each have a copy, a test now fails when they disagree; all of
these run in `test/check.sh`:
- `test/ports_check.js SITE` (check.sh builds wy's public pages for it): tracker.html's own functions, extracted from
  the file and run in Node, against what the build wrote (items 6 and 9).
- `test/profile_check.py`: profile.py against profile.js and the pages' state-name tables (items 7 and 13).
- `test/tokens_check.py`: every page's color tokens (item 11).
- `lists_pages/profilefacts.js` runs a state's profile.js (`BillFacts.runProfile()`) and prints its settings as JSON: the
  build (`profile_settings()`) and profile_check.py read the profile through it, never with regular expressions.

6. **Python ports of page logic.**
   - `api_names()`: the one copy. The Claude copies get `apiName` from the build too, and tracker.html's
     `setupLegislators()` no longer works it out (it reads `L.apiName`, else the name).
   - The profile read with regular expressions (`save_compare()`'s chart wording, `profile_hooks()`): now
     `profile_settings()`, from profilefacts.js. The same answers for all 51 profiles (checked before the switch).
   - `meeting_days()` ↔ `walkCommittees()`/`meetings()`, and the list part's first rows ↔ `sortBills()` "recent": left as
     two copies (the build has to write the days and choose the rows; the page needs the walk for each bill's
     `meetingsSkipped()`, and its own sort), checked by ports_check.js (every committee's days, and that the list's first
     `PAGE` bills all have their titles in the list part). meetings()'s own walk over every bill stays for past sessions,
     whose pages have no `meetingDays`.
7. **profile.py and profile.js.** Left as two copies (the build is Python, the page JavaScript; a JSON file read by both
   would mean rewriting 51 profiles), checked by profile_check.py: houses and the lower house's name, years, titles (each
   house's), the session label for 2017-2028, SESSION_ENDS against `dated`. All agree.
8. **Plain wording of the last action: one copy.** tracker.html's `plainAction()` (with `PLAIN`, `STATE.actionWords`),
   `newsWhat()` and the news weights (`WEIGHT`, `weightOf`) moved to billfacts.js (`BillFacts.make(S).plainAction()`,
   `.newsWhat()`, `.latestNews()`; tracker.html keeps aliases). The build writes each bill's latest news in those words
   into the status row's action column (billlabels.js's 4th answer), and /your-bills/, its "New since you last looked" and
   the front page's Your bills show it as written, with the news's day. status.js's `plainAct()` (New York's patterns
   only) is gone. **A real disagreement fixed**: on ct, nh, ks, al that column changed for 14,237 rows ("REFERRED TO
   HEALTH" was "Sent to the Health Committee" there and "Referred to the Health Committee" on the state's page; CT's
   "File no." paperwork line is now "Placed on floor"; Congress's "Became Public Law 119-21" is "Signed by the President",
   as on its page). Left: the state's tab names the most important action since the visitor last looked (any day);
   the build can't know that day, so the row names the most important one on the latest day with news. They differ
   only when someone hasn't looked for several days of news.
9. **Bill numbers as text: one JS copy,** `BillFacts.numText()` (watchrows.js and status.js read it). issues_site.py's
   `shown()` stays (the issue pages are written in Python): ports_check.js compares the two over every built state's
   numbers. states/me/profile.js `ld()` isn't a copy (it strips the letters for Maine's addresses).
10. **Number search: one copy,** status.js's `BillSearch` (`fold`, `STOP`, `WORDY`, `numParts`, `stem`, `prepRow`,
    `numbersIn`, `numScore`), used by home.html and edit.html. Left: each page's own state-name parsing, which differs on
    purpose (the editor reads a code before "." or ":" in pasted lines; the front page knows "u.s."). 14 queries typed into
    both pages read the same before and after.
11. **Colors.** The odds chart's `.sankey` rules are one file, lists_pages/sankey.css (tracker.html's `/*sankey.css*/`,
    read by compare_site.py). The tokens stay in each page (a shared tokens file would change every page's stylesheet
    for no visible gain); tokens_check.py fails when a token two pages define differs (53 shared, the teal in 7 files;
    build_data.py's chooser page calls it `--link`). It found tracker.html's `--dem`, `--rep`, `--ind`, unused there and
    different from the front page's: removed. `--pty-d`/`--pty-r` are two different colors under one name (tracker.html's
    party chips, home.html's party badges), listed in the test as each page's own.
12. **ⓘ tips: left as they are.** The three don't copy one another's code; they behave differently (tracker.html's
    floating box, which works inside long panels on a phone; the list pages' hover tooltip; the issue page's note that
    opens below), so making them one would change what visitors see. Worth doing only as a design decision.
13. **Data tables.** issues_site.py reads home.html's `GRID` (one copy; the issue pages byte for byte the same).
    The state names (home.html's and common.js's `NAMES`) are checked against each profile.py's `STATE_NAME` by
    profile_check.py.

Still copies, outside this list: issues_site.py's `pips()` (item 11a) has no test against `BillFacts.pips()`.

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
