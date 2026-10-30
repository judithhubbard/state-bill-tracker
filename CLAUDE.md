# State Bill Tracker: the multi-state version (private, in progress)

This is a separate project, started 2026-10-27 as a copy of ny-bill-tracker (commit b312227), in
/Users/jk/Dropbox/Claude/AlbanyBillTracker. The live New York site, albanybilltracker.org, still runs
from that repo. **Nothing here may change it.**

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
- **Decided 2026-10-28:** no new features on albanybilltracker.org (the ny-bill-tracker repo); only fixes and the
  January chores, made there and carried here by hand. New work happens here. **Decided 2026-10-29: leave
  albanybilltracker.org on its own code** (an interim switch of its build to this repo was planned, dry-run on
  2026-10-28 and dropped). New York moves only once, to statebilltracker.org/ny, with the forwarding pages
  below; avoid doing that at the start of a session (aim before January or after June).
- **Decided 2026-10-29:** every state is built from its own legislature's official files and done thoroughly, like
  New Jersey; not from Open States. Virginia came next, then California (chosen 2026-10-29), then Texas and Illinois (2026-10-30); more states before launch.
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
- **New Jersey, milestone 1 (bills, stages, votes; built 2026-10-27):** `python3 states/nj/fetch.py`
  downloads each session's database and vote files into data/nj/ (not in git yet), and
  `python3 build_data.py --state nj` builds site/nj/<session>.html. `states/nj/convert.py` turns NJ's
  action codes into NY's wording, so the page's plain-language rules work unchanged. A state's How tab
  text is `states/<code>/how.html` (else New York's, in tracker.html); its committee pairings, calendar
  and "passed both houses" line are in its profile.js. Committee agendas come from `C.agendas()`. A
  conditional veto the Legislature hasn't acted on counts as passed both houses while the session runs.
  Legislators (milestone 2, 2026-10-28): `states/nj/contacts.py` (run by fetch.py) writes
  data/nj/contacts_<session>.json from the roster, biography and committee files in NY's shape. Seat ids
  are "S:12", and "A:12a"/"A:12b" for a district's two Assembly members (`seat_ids()` in convert.py, which
  also ties the current session's votes to them). "Where you live" picks a town (`renderTownReps()`, from
  data/nj/district_towns.json, made once by `states/nj/towns.py` from the Apportionment Commission's table);
  a town's district gives its senator and both Assembly members. ROSTER.TXT's Email column is empty, so
  contacts.py reads each legislator's email (`SenX@njleg.org`) and contact form from the Legislature's website
  (`/api/legislatorData/legislatorBio/<Roster Key>`), keeping the last copy's when a request fails; the page shows
  the form as "Contact form" (`formHtml()`). 2022–23's text download lacks MAINBILL, ROSTER, COMMITTEE and SUBJHEADINGS;
  `states/nj/fill2022.py` filled them in once (2026-10-29) and the result, data/nj/DB2022_TEXT.zip, is in git. Earlier
  versions come from LastSessionFullBillNumber (one session back) and OldBillNumber (two back). The governor's veto messages (absolute, conditional, line-item) come from pub.njleg.gov
  (`states/nj/vetoes.py`, run by fetch.py, into data/nj/vetoes_<session>.json); `vetoMemo()` words each kind. What each bill does (the sponsor's statement, the latest committee statement, the fiscal
  estimate's summary) comes from `states/nj/texts.py` (current session; documents already read are kept in
  data/nj/docs_<session>.json); build_data.py's `bill_texts()` writes it to data/<session>-text/<A10>.json in pieces
  of 500 bill numbers (packed into Claude copies), and `whatItDoes()` shows it when a bill is opened. Not done yet: published lists and the "public site" tip; the daily workflow for NJ.
- **Virginia, step 1 (bills, stages, votes; built 2026-10-29):** `python3 states/va/fetch.py` downloads the Legislative
  Information System's CSVs into data/va/<year>1/ (see the va-data-sources memory); `states/va/convert.py` reads them.
  Sessions run one year (`YEARS = 1`) and the lower house is the House of Delegates (`LOWER = "H"`, members "Del.");
  tracker.html reads these as `YEARS`/`lastYear()` and `LOW`/`BOTH`/`TITLE`, so no code assumes "A" or two-year
  sessions. History lines are plain English and kept as written, except the steps the site's rules use. The
  file's Approved/Vetoed flags are unreliable (both set, or in 2025 neither): the history decides. A bill the
  governor sent back with amendments is "Passed both houses" until the reconvened session. Bills continued to
  the next year appear in the next year's folder under the same number. Legislators (step 2, 2026-10-29): `states/va/contacts.py` (run daily by fetch.py) reads the House member list and
  committee pages and the Senate's spreadsheet, email list and senator pages (committees marked "(Chair)"); seat ids
  are "S:34"/"H:71", and the data files' member ids ("S0100") match the Senate site's ("S100") once zero-padded.
  `states/va/towns.py` turns the districts' locality descriptions into data/va/district_towns.json, with separate
  Senate and House districts per locality; `renderTownRepsByHouse()` shows it (a split locality picks each district).
  "What it does" (step 3): `states/va/texts.py` takes each bill's latest Legislative Services summary into
  data/va/texts_<year>.json, with a label saying which version it describes. Step 4 (2026-10-29): states/va/how.html and
  weighin.html, a one-year calendar (`STATE.calendar`, `opens()`, `reconvenes()`), the notice between sessions
  (`STATE.sessionNotice`), "passed by indefinitely" (`heldLabel`/`heldTip`/`heldNote`), bills continued to next year
  (`STATE.continuedTo`, no "reintroduce" ask), and one number through both houses (`STATE.oneNumber`: no "it has no
  Senate version"). Statistics hide what a state's data can't support: repeat tries and "came back" without links
  across sessions (`linkedSessions()`), past party rows without past parties. The 2024 files write dates as
  "2024-03-02T00:00:00"; a bill that died in conference is still flagged "Passed" (it's one house's bill).
  Earlier years (2026-10-29): `earlier()` in states/va/convert.py links a bill to the same bill up to two years back
  (continued bills by number; otherwise the same subject heading and either a summary sharing 60% of its words, or a
  rarity-weighted similarity of 0.66; 40% and 0.55 with the same chief patron; never "Relief" claims or the yearly
  drug-schedule bill). Checked by hand 2026-10-29: of 30 random links, 27 were plainly the same bill and 3 closely
  related; some heavily reworked repeats are missed), so "this bill in other sessions", repeat tries and watchlist carry-over work. One-year
  sessions use `YEARS` for "the next session" (build_data.py's comeback counts, carryCandidates()).
- **California (built 2026-10-29):** `python3 states/ca/fetch.py` reads the Legislature's database tables out of its pubinfo
  zips (see the ca-data-sources memory) into data/ca/<session>/ (session = its odd first year); `states/ca/pubinfo.py`
  reads only the wanted files from a remote zip by HTTP range (with curl: the server turns away Python's client), so
  a day's run reads about 11 MB, not 1.2 GB. The daily zip's text files are numbered differently each day, so the
  bill texts (the Legislative Counsel's Digest, `states/ca/texts.py`, cached by version in digests.json) and veto
  messages (vetoes.json) are read from the same zip as the tables. `states/ca/convert.py` decodes the plain-English
  history (each line also says where the bill went: house, Committee/Floor/Desk, committee code) and spells out the
  committee abbreviations; "From committee chair, with author's amendments" is not a committee vote. Only regular-session
  AB and SB bills are shown. Joint authors are all primes. Deadlines (`originBy()`, `lastDay()` in states/ca/profile.js)
  were fitted to the 2021-26 floor votes; the governor has 12 days, or 30 days after the first year's last day, or
  until September 30. `states/ca/contacts.py` reads the Senate's senator, committee and leadership pages and the
  Assembly's member-data API; each member carries `dataName`, the name the database uses ("Limón"), to tie votes and
  authors to seats ("S:21", "A:30"). "Where you live" picks a county (`states/ca/towns.py`, run once: the Senate's
  counties PDF and the Assembly's list) and, on the public site, looks up an address with the Census geocoder
  (`STATE.addressLookup`). Earlier sessions are linked by subject and digest (`earlier()`, like Virginia's), never
  spot bills. A new governor takes office January 4, 2027: add them to `GOVERNORS`.
- **Texas (started 2026-10-30):** `python3 states/tx/fetch.py` downloads each bill's history XML from the Legislature's FTP
  site (see the tx-data-sources memory; its Acceptable Use file asks data users to use it, not the TLO website), only
  files whose listing date changed, six folders at a time (about a second a file: the first full copy of three sessions
  takes hours). `complete()` re-downloads files cut off mid-transfer. Sessions are the Legislature's codes (`code_of()`:
  2025 -> "89R"); special sessions aren't shown. `states/tx/convert.py` reads the action codes (H555 House passed, S576
  Senate passed, E015 sent to the governor, E020/E025/E030 signed/filed without signature/signed with line-item vetoes,
  E035 vetoed; H/S 0xx-1xx referrals, 25x/28x reports, H245/S275 "left pending"); a reported House bill is shown in the
  Calendars Committee until it's placed on a calendar. H825/S825 "Transmitted to the Governor" is NOT a sending (it's on
  bills still in committee). One record per bill; companions show as similar bills. Committee votes are totals from the histories;
  floor votes by member come from the journals (`states/tx/journals.py`): the House Journal's record votes by the "RV#"
  numbers in the histories, and the Senate Journal by each bill's heading (it has no record numbers), including the
  Local and Uncontested Calendar's list format and a date's second journal ("...SJ04-12-F1.HTM"); "(Same as previous
  roll call)" means the vote just before, motions included. About 98% of Senate passages are found; every list's
  count matches its tally. `states/tx/contacts.py`: the House's member and
  committee JSON, each senator's page, parties from the Legislative Reference Library; `dataName` is the last name, or
  "Bell, Keith" where two members share it. Counties with each district's share (`states/tx/towns.py`, run once, from the
  Texas Legislative Council's r4.pdf district reports). "What it does": the current session's bill analyses
  (`states/tx/texts.py`). Session dates are computed (`opens()`, `sessionEnds()` = day 140, House deadline day 122,
  governor 10 days without Sundays or 20 after adjournment). Leaders: the Speaker, and for the Senate the Lieutenant
  Governor (not a senator). Totals for 2025 to check against: 1,047 signed, 140 filed without signature, 26 vetoed
  (reports/signedbygov.htm etc. on the FTP site).
- **Illinois (started 2026-10-30):** `python3 states/il/fetch.py` downloads each bill's status XML from the General
  Assembly's public file repository, https://ftp.ilga.gov/ (see the il-data-sources memory: www.ilga.gov turns automated
  requests away and points to it), only files whose listing date changed; plus each General Assembly's member and
  committee XML, from which `states/il/contacts.py` builds the contacts (no web pages). Both servers omit an
  intermediate certificate: `ca_bundle()` adds Sectigo's to a copy of the system's (data/il/ca.pem); verification
  stays on. Sessions are General Assemblies (`assembly_of()`: 2025 -> 104). `states/il/convert.py` reads the plain-English
  actions: every bill starts in the House Rules or Senate Assignments Committee (the gatekeepers: `committeeNext` and
  `chairAsks` word their asks), "Assigned to X Committee" is the real referral, "Rule 19(a) / Re-referred to Rules" is
  "held"; amendments' own referrals aren't the bill's. Sponsor lists join the chief sponsors with hyphens
  (`split_sponsors()` splits them against that Assembly's members). Votes are tallies only (no roll calls in the
  repository). An amendatory veto is "passed both houses" until both houses accept it. "What it does" is the
  synopsis of the last amendment that rewrote the bill ("Replaces everything after the enacting clause"; more than half
  the laws), else of the bill as filed, then each later adopted amendment's (`synopsis()` in convert.py; the file's
  synopsis block also holds fiscal notes and veto messages, left out). About 30% of bills are shells ("Makes a technical
  change", $2 appropriations; `is_shell()`), which the House Executive Committee approves in bulk: decided 2026-10-30,
  the statistics and legislators' numbers (profiles, history, networks) leave out shells never rewritten
  (`without_shells()` in build_data.py, `outcomes()`, and `b.shell` in `netData()`/`whoData()`; the Speaker "sponsored"
  883 bills with them, 15 without), each Statistics
  note says so (`shellsOut()`), the list tags them "Shell bill" with a tip (`SHELL_TIP`), and they get no odds line. An
  amendment that "Reinserts the provisions of the introduced bill" is a change, not a rewrite. Rules and Assignments are `STATE.gates`: no New York
  "got as far as Rules" line, and a bill waiting there says the leader controls it; `STATE.commIntro` words the How
  tab's Committees points. "Where you live" lists cities, villages and counties from the Census Bureau's 2024 district relationship
  files (`states/il/towns.py`, run once; no key needed; works for any state). Bill links go to the repository's
  status pages and texts.
- **Fewer yearly chores (2026-10-29):** Virginia's session dates are computed (`opens()`, `sessionEnds()`, `crossover()` in
  states/va/profile.js: 60 or 46 days from the second Wednesday of January; crossover the 35th or 28th day), with
  `dated` for a year that differs. Crossover is each bill's deadline until it passes its own house
  (`STATE.originDeadline`), and after it the bill can't pass that year. Virginia's floor leaders and members' first
  years come from the houses' sites (contacts.py). `check_site.py` runs last in site.yml and fails the run (GitHub
  emails) when legislators are stale or too few, New Jersey's bill texts are missing, or Virginia's date rule stops
  fitting the floor votes. Still by hand: a new governor (`GOVERNORS`) every four years, next January 2030.
- **Saved settings are per state (2026-10-29):** the states share one web address, and a browser keeps one set of saved
  settings per address, so tracker.html prefixes every saved name with `STORE` ("abt:nj:", "abt:va:"; New York keeps
  plain "abt:" so its visitors' watchlists still load after the move). `adoptShared()` takes a state's own bills, once,
  from the watchlist, log and stances saved under the plain names before this.
- **Adding a state (learned from NJ and VA):** missing settings fall back to New York's rules and wording, silently.
  Copy states/nj or states/va and decide each of these: in profile.py, `YEARS`, `LOWER`/`LOWER_NAME`/`TITLES`,
  `LEADERS`, `GOVERNORS`, `TOPICS`, `TOWNS_PATH`; in profile.js, `code`, `houses`, `titles`, `memberWords`,
  `greetings`, `years`, `sessionLabel`, `govReach`, `billUrl`/`textLinks`, `sessionEnds`, `govDeadline`, `dueLabel`,
  `passedBothBy`/`passedBothNote`/`passedBothGroup`/`passedBothNext`, `floorVotesEnd`, `diesAfterFloor`,
  `outOfTimeLine`, `sessionNotice`, `waitingHead`, `govYearsNote`, `partySource`, `openUntil`, `heldLabel`/`heldTip`/
  `heldNote`, `routine`, `oneNumber`, `continuedTo`, `requestsBills` (New York only), `townWord`/`findReps`,
  `stageText`/`stageTips`/`pastStageTips`/`outOfTime`, `commPairs`/`commNotes`/`moneyCommittees`/`secondCommittee`,
  `calendar`/`calendarDays`; and write how.html and weighin.html. Then run the review: record every tab, Statistics
  section, How section, bill panels at each stage and a watchlist, and grep the text for other states' names and rules.
- **Data traps found so far.** `python3 test/data_check.py` checks every state for all of these that a program can
  check (FAIL), and prints what a person should read over (LOOK: totals to compare with the official ones, odd wording);
  the daily run runs it too. Run it after any change to a state's data code, and when a new trap goes on this list,
  add its check there and run it against every state, not just the one where it turned up:
  - Status flags that disagree with the history (VA's Approved/Vetoed: both set, or neither). Decide stages from the
    history, and count bills by stage against the Legislature's own totals (e.g. vetoes per year).
  - "Passed" flags that mean one house (a VA bill that died in conference is still "Passed").
  - Formats that change between years: dates ("3/14/2026" vs "2024-03-02T00:00:00"), and tables missing from an
    older year's download (NJ 2022–23 lacked four; filled once by fill2022.py).
  - Characters lost in the export: VA's summaries have "?" for §, dashes and apostrophes. Grep the text for
    " ? " and a letter, "?", then a letter.
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
  - Names: degrees and titles ("Dr.", "M.D.", "Ph.D.", "Esq.") aren't part of a name; "Jr."/"III" are, but aren't the
    last name (`shortName()`). Check each contacts file for duplicate phone numbers.
  - Placeholder bills (CA "spot bills": technical, nonsubstantive changes; "intent" bills) and stock sentences
    ("no reimbursement is required by this act") make unrelated bills look alike; keep them out of matching.
  - The other state's settings in shared slots: each `keyDates` entry means the same thing in every state (the 4th
    is New York's return to committee in a new year; leave it "" elsewhere).
  - A conference report passes only when both houses adopt it (TX HB3104 of 2023: the House adopted it, the Senate never
    did, and it showed as passed both houses). Same for any step one house can take alone.
  - A file's encoding: read UTF-8 first ("bedï¿½a" in TX analyses read as Windows text). Grep built texts for "ï¿½" and "\ufffd".
  - Summaries of the bill as filed when an amendment rewrote it: IL laws summarized as shell bills ("Makes a technical
    change"). Read every amendment's summary the files carry; the check counts laws summarized as placeholders.
  - Summaries that only repeat the title (TX "C.S.H.B. 2 amends current law relating to ...") say nothing: drop them, or
    use an earlier version's.
  - Look at every part of a bill panel at phone width (375px iframe): the similar-bills list once collapsed its number
    column in every state. Class names shared by unrelated parts: chart legends' `.key` (nowrap) also styled the
    contact card's `li.key` and pushed IL and NJ panels sideways; the co-sponsor list's `more` took the "Show more"
    button's box. Check `document.documentElement.scrollWidth` with a bill open.
  - When editing code with a script, check the file's size afterwards. A bad Python edit once emptied convert.py.
- **Hosting (set up 2026-10-29):** statebilltracker.org will be served by Cloudflare Pages (project
  `statebilltracker`), since this repo is private. `./build_site.sh [DIR]` builds the whole site: `home.html` (the
  list of states) at the top, the icons, and each state's public site in its folder (`--github DIR/<state>`).
  Until launch it writes `robots.txt` and `_headers` telling search engines not to list anything (`LAUNCHED=1`
  turns that off). `.github/workflows/site.yml` downloads, builds and deploys, once a day (10:23 UTC; GitHub often starts it hours late) and by hand; it needs the
  secrets CLOUDFLARE_API_TOKEN and CLOUDFLARE_ACCOUNT_ID. The domain stays parked at Porkbun until launch.
  Until then the site is at https://statebilltracker.pages.dev/ (first put up 2026-10-29, built with
  `SITE_BASE=https://statebilltracker.pages.dev/` (each state's SITE_URL is SITE_BASE/<state>/); unlisted, and marked noindex). It's a classic Pages project
  (created with `--force`, which isn't needed again). Deploy by hand from an empty folder, never from
  lists_worker/ or cron_worker/ (wrangler picks up that folder's wrangler.toml):
  `npx -y wrangler@4.152.0 pages deploy <repo>/_site --project-name=statebilltracker --branch=main --commit-dirty=true`.
- **Launch checklist for statebilltracker.org** (do these together when the owner says to launch):
  1. `.github/workflows/site.yml`: run more often (e.g. hourly on weekdays while the Legislature meets, every two
     hours otherwise, like ny-bill-tracker's update.yml); mind GitHub's 2,000 free minutes a month for a private
     repo (a run takes about 2) and Cloudflare Pages' monthly deployment limit.
  2. Build with the real address: drop `SITE_URL` from the workflow (states use `PUBLIC_URL`), and set
     `LAUNCHED=1` so `build_site.sh` stops telling search engines to stay away.
  3. Point statebilltracker.org (and .com, forwarding with 302) at the Pages project: add it as a custom domain
     in Cloudflare Pages and change the DNS at Porkbun.
  4. Analytics: GoatCounter and Cloudflare Web Analytics codes in each state's profile.py (none yet).
  5. Published lists: a KV namespace for the `state-lists` Worker and each state's `listsApi`.
  6. Check every state's pages once more (test/crawl.js) and republish the private NJ Claude copy.
- Fixes made in ny-bill-tracker still get carried over here by hand (compare against `git log` there since
  b312227; 5fe4339 is already in).

## What's switched off in this copy (so it can't touch the live NY site)

- **The workflow** (`.github/workflows/update.yml`) runs only when started by hand: no schedule, no
  push trigger. The repo is private, so it has no GitHub Pages site anyway.
- **The Workers are renamed:** `state-lists` (with no KV namespace yet) and `state-cron` (with no timer,
  aimed at this repo). Never deploy them under the names `albany-lists` or `albany-cron`.
- **`lists_admin.py`** and the `LISTS_API` address in tracker.html still point at the live NY lists
  Worker. Don't run admin commands from here.
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
    past ones; data goes in `data/<session>.json`; legislator pages go at `/<slug>/` and the watchlist
    at `/watchlist/`. `github_page()` adds the document head, icons and the analytics tags.
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
  read "Prefiled" (`STAGE_TEXT.prefiled`), and it has no Weigh in or Statistics tab. Statistics and
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
  `PLAIN` / `plainAction()` (plain-language wording for actions).
- **Bills list:** `matches()` (filters), `sortBills()`, `renderPipeline()` ("Where it is now"),
  `renderList()`, `billRow()`, `statusText()`, `track()` (the progress bar in each row),
  `fillDetail()` (the panel that opens under a bill) and `nextSteps()` / `planFor()` /
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
  `lookUpReps()`. Legislator pages: `PRESET`, `PAST_WHO`, `renderPerson()` and `renderPersonStats()`.
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
- **Watchlist:**
  - Storage and actions: `WATCH` (localStorage), `ORDER` (drag order), `watchItems()` (splits bills
    into "Needs action" and "Can't move right now", then sorts them), `keyAction()` (the one ask on
    each card), `deadlineOf()` / `W_GROUPS` (splits "Needs action" into Due soon, Before the session
    ends, By December 31 and No deadline yet; `sessionEnd()` reads `data/session_calendar.json`, else
    when past sessions ended), `renderWatchView()` (the cards), `logBlock()` / `actionRecord()` (the action log) and
    `draftFor()` (email text).
  - Decided bills (signed or vetoed) get their own section below "Can't move right now". The header is
    one line with a "Share this list" button (`W_SHARE_OPEN`) that opens the share options.
  - News: `newsBox()` ("New since you last looked", at the top; rows open the card, "Mark all as seen"),
    `newActions()` (actions since the bill was last opened, skipping `ROUTINE` paperwork,
    most important first by `WEIGHT`), `newsTags()` (the "New: …" and "Coming up: …" tags),
    `nextMeeting()` (from committee agendas) and `updateWatchTab()` (the "N new" badge on the tab).
  - New session: `carryCandidates()` / `carryBox()` offer bills from last session's watchlist that
    are back under new numbers (handled ones are kept in `abt:carried:<session>`).
- **Committee agendas:** `state.agenda` ("On an upcoming committee agenda", a sub-row under In
  committee, turned on by `setAgenda()`, which also sorts by `meeting`), the "On the agenda" tag on
  bill rows, and `comingUp()` (Weigh in: the next two weeks' meetings, each folding open to its bills).
  `CHANGED` also has "Introduced since your last visit" and "in the last 7 days" (`b.dates.intro`).
    `markSeen()` runs when a bill's details or its watchlist card are opened.
  - Sharing: share links are `#w=<session>.S1234.-A5678`, where "-" means oppose. Published lists use
    `publishBox()`, `publishAction()`, `listsApi()` and `loadPublishedList()`. A published list is
    viewed at `watchlist/#list=<slug>`.
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
  `data-how="<id>"`). The Committees tab is `renderHowComm()`: it pairs Senate and Assembly
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
  `render()` draws everything.

## Rules and traps

- **One big script, one shared namespace.** A second `function foo` silently replaces the first.
  That happened with `track()`, and the progress bars vanished with no error. A duplicate `const`
  breaks the whole page. Before adding a top-level name, grep for it. `test/check.sh` catches
  duplicate functions.
- **Nothing shows until the data is drawn.** CSS hides everything but the title (`html:not(.ready)`)
  until the loader adds `ready` after `hydrate()`. This stops layout jumps, which Cloudflare scores
  as CLS, and early taps that ran code before `DATA` existed. The build writes the header line
  (`#sessionLabel`) into the page so it doesn't change length on load. Anything added later above
  the tabs, like a banner that appears after loading, makes the page jump again.
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
