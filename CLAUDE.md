# State Bill Tracker: the multi-state version (in progress)

The repository is public (made so 2026-11-01, for unlimited free GitHub Actions minutes). Never commit secrets: keys
live in ~/.<name> files and GitHub secrets; check `git log -p` before committing anything that reads a key.

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
- **Washington (started 2026-10-30):** `python3 states/wa/fetch.py` reads the Legislature's web services
  (https://wslwebservices.leg.wa.gov/, plain GET, XML; see the wa-data-sources memory: their robots.txt says
  `Disallow: /`, but their documentation invites applications, and the owner decided to use them, politely). Each bill
  goes into data/wa/<session>/bills/<HB1003>.json: its versions (substitutes like "E2SHB 1003" are versions of HB1003),
  history, sponsors in order (with member ids) and, when the history shows a vote, its roll calls (every member, by id).
  A finished biennium is read once; the current one asks the change feed (GetLegislativeStatusChangesByDateRange) which
  bills changed since the last run. The first full copy (about 9,000 bills, three requests at a time) takes about 2½
  hours, so on GitHub it builds up over several runs (`began` in state.json). `states/wa/convert.py` reads the
  plain-English history. The lines don't say which house acted: committee steps carry the committee's acronym
  ("HSG - Majority; do pass."), passages match a roll call (which names its house), and otherwise the bill is in its
  house of origin until it passes. A bill a committee approves goes to that house's Rules Committee, which decides which
  reach the floor (shown in the Rules Committee, like Texas's Calendars; its "X file" is "held"). Two-year bienniums
  with a 105-day and a 60-day session (`opens()`, `adjourns()` in profile.js); the governor has 5 days, Sundays
  excepted, during a session and 20 after it (`govDeadline()`). `states/wa/contacts.py`: leg.wa.gov's legislator list
  (147 cards with the member ids the roll calls use) and committee pages (chairs, members matched by name and
  district); phones and emails from the web services' member list. Seat ids "S:21", "H:21a"/"H:21b" (New Jersey's
  scheme); the same districts for both houses. "What it does": the House or Senate staff's bill report
  (`states/wa/texts.py`: the Final Bill Report, else the latest report or analysis; its summary, not the background).
  Committee agendas for three weeks ahead (CommitteeMeetingService). Places from the Census relationship files
  (`states/wa/towns.py`; one district list per place, since both houses use the same districts). Earlier bienniums
  linked by short description and description words (`earlier()`). The history repeats lines (once per version) and
  isn't in date order: sorted and deduplicated. "Passed both houses" comes from the passage roll calls' motions
  (`both_agreed()`: "as Amended by the House" needs the Senate's agreement; a conference report needs both houses; the
  first house passing it again on third reading is starting over). At the end of the biennium's first session a bill that passed only its first house
  is "By resolution, returned to House Rules Committee for third reading": its passage is undone (`is_reset()`, keyDates[3],
  `STATE.resetNote()`, as New York's January reset); the same line at the end of the second session isn't. A few histories stop early (HB 2134 of 2023-24):
  a version's newer current status is added, "C 310 L 24" meaning chapter 310 of 2024. Laws include ones without the
  governor's signature, overridden vetoes and initiatives to the Legislature, so the governor's "signed" lists are a
  few short. Until the first full copy is complete, fetch.py writes data/wa/incomplete and build_site.sh and the
  checks skip Washington. GitHub downloaded the first full copy in one run (2026-10-31), and Washington is on the front page.
- **Ohio (started 2026-10-31):** `python3 states/oh/fetch.py` reads the Legislative Service Commission's API
  (https://search-prod.lis.state.oh.us/api/v2/, JSON; see the oh-data-sources memory). legislature.ohio.gov,
  ohiohouse.gov, ohiosenate.gov and ohiosos.gov all answer automated requests with 403, so (decided 2026-10-31)
  everything comes from the API except legislators' emails and page links, which come from Open States' public-domain
  file (data/oh/openstates_people.csv; it has no phones), named as the source in "About this data". Sessions are
  General Assemblies (`assembly_of()`: 2025 -> 136). Each bill's versions (read again when its entry in the
  legislation list changes) and actions (the current General Assembly's every run; about 1,500 requests, no change
  feed) go into data/oh/<session>/bills/<HB96>.json. Actions are structured, with each vote's members: committee and
  floor votes are member by member. The governor's signature is the enrolled version's governor_signed_date, not an
  action; a few have none (HB 110 of the 134th), so in a finished General Assembly an enrolled bill without "Veto
  receipt" is law. "Line item veto receipt" stays as written (a law, part vetoed). "Reported - Re-referred to X" is a
  referral to X. Each house's Rules and Reference Committee schedules floor votes. "What it does" is the long title's
  purpose clause, after the last list of sections, its verb turned into "Modifies ..." (`purpose()`, `texts.py`).
  Full-time Legislature (`floorVotesEnd: false`); governor 10 days, Sundays excepted. Separate Senate (33) and House
  (99) districts by city, village or county (`states/oh/towns.py`). The governor's phone and address are from the
  governor's contact page, checked by the owner 2026-10-31 (governor.ohio.gov answers automated requests "not found"). Built only once data/oh/incomplete is gone.
- **Connecticut (started 2026-10-31):** `python3 states/ct/fetch.py` reads the General Assembly's CSV files from its FTP
  server (ftp://ftp.cga.ct.gov/pub/data/; see the ct-data-sources memory): bill_info (titles, statements of purpose, act
  numbers), bill_history, introducer, comm_ref, committee, subject and the legislator database, for the current year (top
  folder) and archive/<year>; small, so read in full each run. 2023 and before are only flat files at the archive's top
  level ("2023bill_info.csv", bill_history, introducer, subject, "2023LegislatorData.xlsx": no comm_ref, committee or
  actions); fetch.py reads those years once, under the usual names, the spreadsheet as LegislatorData.csv (read without
  dependencies), and keeps four years back (2022-26: two finished sessions of each kind for the statistics). There, dates
  are "1/23/2023" (`rows()` makes them ISO), introducer codes are unpadded ("1", "115A" for a mid-session replacement:
  the spreadsheet's dist_code), and committees come from the nearest later year's list (referral lines carry the code).
  2022: 169 laws, 2 vetoed (PA 22-1..146, SA 22-1..24); 2023: 235 and 5 (PA 23-1..208, SA 23-1..31). One session a year (`years: 1`; long in odd years, short
  in even: `opens()`/`sessionEnds()` in profile.js are the Wednesday after the first Monday of January or February, June
  or May). Committees are joint (both houses' members); `commIntro` says so. Sponsors are codes: "006" a House
  district, "S06" a Senate district, letters a committee (committee bills). A Public Act number comes when both houses
  pass the same text, before the governor acts (HB 7004 of 2025 got one and was vetoed): it decides "passed both
  houses", and only "SIGNED BY GOVERNOR" is a law. History lines kept as written are in sentence case so "REFERRED TO
  OLR, OFA" (research and fiscal offices) can't pass for a committee referral. The files are UTF-8 with a few
  Windows-1252 bytes (decoded as one or the other). No votes: the vote sheets' only index is the bill status pages,
  which robots.txt disallows (and the site omits GoDaddy's G2 intermediate certificate). "What it does" is the
  statement of purpose. Legislators (phones, emails, committees, leadership) from the database; Capitol phones are the
  caucus offices' shared lines. Towns from the Census county-subdivision files (169). Earlier years linked by title and
  purpose words.
- **Oregon (started 2026-10-31):** `python3 states/or/fetch.py` reads the Legislature's OData API
  (https://api.oregonlegislature.gov/odata/odataservice.svc/; see the state-survey-2026-10-31 memory): whole tables per
  regular session ("2025R1") into data/or/<key>/<Table>.json, in a few minutes, every run. The package is named "or", a
  Python keyword: its files load each other with importlib. One session a year (`years: 1`; long in odd years from the
  second Monday of January, short in even years from the first Monday of February). History lines carry their house;
  "Do pass and be referred to Ways and Means" is a referral; "by prior reference" and "X, then Ways and Means" are
  stripped from committee names; "Passed." alone (after a motion) and consent-calendar lines are passages. Floor votes
  belong to a history action (MeasureHistoryId); committee votes are by member (CommitteeVotes). Laws and vetoes match
  the API's ChapterNumber and Vetoed flags. Title: the official "Relating to ..." short title without the stock ";
  declaring an emergency"; the catch line is the one-line summary; "What it does" is the staff digest (tags stripped).
  Bills filed before the session "by order of the President" have no member sponsor: the "at the request of" field names
  who asked. Joint committees (Ways and Means) are listed for both houses. Governor 5 weekdays, or 30 business days after
  adjournment. Separate Senate (30) and House (60) districts by city or county.
- **Massachusetts (started 2026-10-31):** `python3 states/ma/fetch.py` reads the General Court's API
  (https://malegislature.gov/api/; see the ma-data-sources memory): each two-year General Court's document list (2025 is the
  194th), each bill's history (one request per bill, three at a time; a finished court's are read once, the current one's
  again when active), the Senate's roll calls, members (`contacts.py`, run by fetch.py; past courts' members for names in
  roll calls) and the session laws. Only bills and resolves are shown (not orders, study orders or constitutional
  proposals). A committee's new draft has a new number ("Accompanied a new draft, see H4321"), and a conference report is
  a new bill ("Reported, in part, by H4040"): `load_session()` follows the chain, and the record takes the newest number
  with the others as earlier numbers; the governor's amended sections that come back as bills ("see H4051 for section
  15") join the law's record. Laws come from the session laws file (`laws_<year>.json`, by OriginBill), since some
  histories stop before the signing. A study order ends a bill in committee (`STATE.heldAction`, "Sent to study").
  "Passed to be engrossed" is a house passing it; "Enacted ... laid before the Governor" sends it. Committees are almost
  all joint; House Steering, Policy and Scheduling decides which bills reach the House floor; the Committee on Bills in
  the Third Reading counts as the floor. Formal sessions end July 31 of the second year (`formalEnds()`), informal ones
  when the court ends. Governor 10 days. No summaries in the data ("What it does" isn't shown); House votes are tallies,
  Senate votes by member. Earlier courts linked by identical title (`earlier()`). Cities and towns (351) by district.
- **Pennsylvania (started 2026-10-31):** `python3 states/pa/fetch.py` downloads each session's bill history file
  (https://www.palegis.us/data, a zipped XML refreshed hourly: sponsors with house, district and party; actions with
  chamber, verb, committee and date) into data/pa/billhistory_<year>_0.zip, then, at one request a second, each voted-on
  bill's page and its roll calls (floor and committee, member by member; committee ones carry a "Brief Description",
  used as "What it does"). The first full copy takes several hours. robots.txt limits only an accessibility scanner.
  `states/pa/convert.py`: "Third consideration and final passage" is a passage ("Vote on final passage reconsidered"
  undoes it); "First consideration" puts a bill on the floor; most bills are re-committed to Appropriations before the
  final vote; "Presented to the Governor", "Approved by the Governor", "Act No. 28 of 2025" (`STATE.lawWord` = "Act").
  An action's date comes from its wording: "(Remarks see House Journal ...)" lines are dated when the remarks were filed.
  Titles are the co-sponsorship memo's ("Mandating Cursive Handwriting"), with the official title as the summary.
  Joint resolutions proposing constitutional amendments are bills here (HB/SB) and never go to the governor
  (`STATE.amendments`, topic "const"). Earlier sessions linked by the memo's "(Former HB 1934)", else the same official
  title and prime sponsor. Legislators (`contacts.py`): the member and committee feeds (phones, offices; majority chairs);
  emails from Open States (owner's decision 2026-10-31: the Senate's pages hide them behind an anti-collection script).
  The 2,572 municipalities by district (`towns.py`); townships that share a name carry their county. Full-time
  Legislature (`floorVotesEnd: false`); the session ends November 30 of the even year; governor 10 days, Sundays excepted.
- **Maryland (started 2026-10-31):** `python3 states/md/fetch.py` reads each regular session's bill list
  (https://mgaleg.maryland.gov/<year>RS/misc/billsmasterlist/legislation.json; no robots.txt: sponsors, committees, the date
  and result of each reading in each house, the Department of Legislative Services' synopsis ("What it does"), chapter
  number and status) and the members' pages (district, party, committees with "(Chair)", Annapolis phone, email).
  `states/md/convert.py` builds each bill's steps from those dates; there are no votes and no dates for the governor's
  actions (shown on the bill's last day). Every bill the General Assembly passes gets a chapter number unless vetoed, so
  after mid-June a passed bill without one is vetoed (some vetoed bills' statuses show a later motion on the veto).
  Constitutional amendments pass once by three-fifths and go to the voters at the next even-year election
  (`STATE.amendmentOnce`, `ballotEvenYears`); they get chapter numbers but aren't laws. 47 districts, each with a senator
  and three delegates, some from subdistricts ("44A"): as in New Jersey, a district's senator and all its delegates are its
  legislators ("S:44", "H:44a/b/c"); the towns list (cities, towns, Census-designated communities and counties) gives one
  district list for both houses. `dataName` is the bill list's form ("Ebersole", "Lewis, R."). One 90-day session a year.
- **Georgia (started 2026-10-31):** `python3 states/ga/fetch.py` reads the General Assembly's SOAP web services (plain
  HTTP; see the ga-data-sources memory): each regular session's legislation list (session ids in P.SESSION_IDS), each
  bill's detail (sponsors in order, committees, coded status history, floor votes) into data/ga/<year>/bills/, each
  floor vote member by member (votes/), members and committees. The first copy takes about an hour; the current
  session's bills are read again every run (no change feed). `states/ga/convert.py` decodes the status codes (the first
  letter is the house where the step happened; referrals don't name the committee: it's the bill's committee in that
  house). Agreeing to the other house's changes "As Amended" changes the bill again, disagreeing leads to conference, and
  a conference report needs both houses (`agreed()`; HB 196 of 2023-24). Laws are "Act 696" (`STATE.lawWord`). "What it
  does" is the long title's "so as to ..." clauses (`purpose()`); there are no plain summaries and no committee votes.
  Local legislation (one city or county) is narrow kind "place" ("For one city or county"), kept out of similar-bill
  matching. Bill pages are addressed by legislation id: a version's `link` (shared: build_data.py passes it, the page
  reads `v.link`). Two-year General Assemblies, 40-day sessions each year; each year's last day is in `STATE.dated`
  (add the new year's after its session). Governor 6 days in session, 40 after it. The Lieutenant Governor presides over
  the Senate (not a senator).
- **Michigan (started 2026-10-31):** `python3 states/mi/fetch.py` downloads each bill's status XML from the Legislature's
  document server (https://www.legislature.mi.gov/documents/<session>/status/<house|senate>/xml/; no robots.txt; its
  policy allows one request a second), only files the folder listing shows as new or changed (date and size, kept in
  listing.json). Some files start with a byte-order mark. `states/mi/convert.py`: each history line's journal names the
  chamber; House lines are lower case, Senate capitals; "passed; given immediate effect Roll Call #4 Yeas 63 Nays 41" is a
  passage (tallies only: members' votes are in the journals), "PASSED BY HOUSE ..." in the Senate's journal isn't;
  "ordered enrolled" means passed both houses; laws are "Public Act 2" (`STATE.lawWord`). Titles are the digest titles
  without the subject; topics from the subject categories (`CATEGORY_TOPICS`). No summaries. Bill pages are addressed by
  the year introduced ("2026-SB-0968"): a version's `link`. Legislators from the web service
  (https://legislature.mi.gov/litwebservices/litwebservices.asmx: GetLegislatorInformation for emails and phones,
  GetLegislatorInformationBySession for websites); party from the caucus website (housedems/senatedems = Democratic,
  gophouse or "rep..."/"senator..." sites = Republican; Open States for any other). Committees: the House's from www.house.mi.gov
  (each standing committee's page; the site omits its DigiCert intermediate certificate: `ca_bundle()` adds it, as for
  Illinois), the Senate's chairs and meeting times from senate.michigan.gov's committee list. Cities and townships by district (`towns.py`).
  Full-time Legislature; governor 14 days, Sundays excepted.
- **Wisconsin (started 2026-10-31):** `python3 states/wi/fetch.py` reads docs.legis.wisconsin.gov (see the wi-data-sources
  memory; robots.txt blocks the feeds, so changes are found from the bill lists and the journals, plus a weekly re-read):
  each bill's history, authors and the Legislative Reference Bureau's analysis ("What it does"), the roll calls member by
  member, the committee records, members and committees. The first copy takes about 6-7 hours at a request a second.
  `states/wi/convert.py` reads the history lines ("Read a third time and passed, Ayes 53, Noes 45"; the second house
  "concurred in"; "Report correctly enrolled"; "Report approved by the Governor ... 2023 Wisconsin Act 123", with partial
  vetoes; bills pending at the last floor period "Failed to pass pursuant to Senate Joint Resolution 1"). The lower house
  is the Assembly (`LOWER = "A"`, seats "A:82"). Senate roll calls give names in capitals cut to 14 characters
  (`members_index()`). The last general-business floor period's date is `STATE.dated` (add each session's). The Assembly
  Committee on Rules and the Committee on Senate Organization schedule floor votes. Cities and villages crossing county
  lines are one entry (`towns.py`); towns that share a name carry their county.
- **Arizona (started 2026-10-31, from Open States: see the az-open-states memory):** `python3 states/az/fetch.py` reads
  v3.openstates.org with the owner's free API key (~/.openstates_api_key; GitHub secret OPENSTATES_API_KEY). The free tier
  allows 250 requests a day (20 bills each): the first copy of three sessions takes two days, resuming from the saved page,
  and stops cleanly at the daily limit; then a day's changes (updated_since) are a few requests. Local runs and GitHub's
  share the quota. `states/az/azleg.py` reads www.azleg.gov at its 120-second crawl delay (member rosters for phones and
  rooms; the committee pages list meetings only, so there are no chairs yet; resolutions' official titles to tell
  constitutional amendments from referred measures). `states/az/convert.py` uses Open States' action classifications;
  some committee reports don't name their committee. Open States has no chapter numbers, and about 10 bills a year stop
  after passing both houses (gaps in its records). 30 districts with a senator and two representatives each (New Jersey's
  scheme, "H:12a"/"H:12b"). Earlier years linked by short title.
- **North Carolina (started 2026-10-31):** `python3 states/nc/fetch.py` reads ncleg.gov (see the nc-data-sources memory;
  robots.txt Crawl-delay 2): each session's bill list (RSS), each bill's page (sponsors, keywords, Public/Local, session
  law, roll-call table, history), each roll call member by member, members, committees with chairs. The first copy takes
  about 6 hours. `states/nc/convert.py` reads the history ("Ref to the Com on X, if favorable, Y": X first; "Passed 3rd
  Reading" is the passage; "Ordered Enrolled"/"Ratified" passed both houses; "Ch. SL 2025-13" a law, `STATE.lawWord`
  "Session Law"). Every Senate bill starts in the Senate Rules Committee (`STATE.gates`); both houses' Rules committees are
  called "Rules". Local bills become law when ratified, without the governor (narrow kind "place"); constitutional
  amendments are bills too ("Constitutional Amendment ..."), three-fifths, then the voters. Roll-call pages print "None"
  for an empty vote group. Emails from Open States (the pages hide them behind Cloudflare's script); members who resigned
  stay on the member list with a note. No summaries (PDFs). Counties and places by district (`towns.py`).
- **Wyoming (started 2026-11-01):** `python3 states/wy/fetch.py` reads the Legislative Service Office's JSON API, the one
  wyoleg.gov's pages use (lsoservice.wyoleg.gov/api and api.wyoleg.gov; no robots.txt), a request a second: each year's
  bill list, each HB, SF, HJ and SJ in full (actions, sponsors, roll calls member by member in committee and on the floor,
  the LSO's bill summary), members and the joint committees; `states/wy/contacts.py` (run after it in the workflow) builds
  the contacts (93 members with emails and phones; a past year adds members who left, for seats no one else holds).
  One session a year: a general session in odd years (from the second Tuesday of January, 40 legislative days), a budget
  session in even years (from the second Monday of February, 20 days), where a bill other than the budget needs
  two-thirds to be introduced; "Failed Introduction" and "Did not Consider for Introduction" are `STATE.heldAction`
  ("Not introduced"). Each year's last day is in `STATE.dated` (add each new year's). `states/wy/convert.py`: actions
  begin with their house ("H 3rd Reading:Passed 53-4-5-0-0" is the passage; a tally is yes, no, excused, absent,
  conflict); the API lists them newest first. Each house's twelve standing committees have the same numbers and names
  ("H09 - Minerals" and "S09 - Minerals"); only single-subject ones give a topic. Both houses passing isn't passing both
  houses: a bill sent back for concurrence needs "Concur:Passed" (or a recede) or enrollment ("Assigned Number HEA
  No."); several died in conference. A law is decided by its chapter number: veto overrides appear only among the roll
  calls ("Veto Override 45-16-1-0-0", "Did Not Override Veto 35-27"), added to the history as written. Roll-call names:
  floor "Campbell, K" (the members' voteName), committee "CAMPBELL" (a shared surname resolved by committee membership);
  name lists split on commas, so initials, "Jr" and first names ("Larsen, Lloyd") rejoin the name before them; a roll
  call's chamber field is sometimes wrong (the action's house letter decides). Committee sponsors' full names ("Joint
  Judiciary Interim Committee") come from the digest's "Sponsored By:" line. "What it does" is the LSO's bill summary
  (mostly laws; background-first summaries reordered), else the official title's clauses (`purpose()`: "specifying" ->
  "Specifies"). Earlier years linked by catch title and prime sponsor, never to a bill that became law (yearly bills like
  "Omnibus water bill-construction" share titles). Governor 3 days, Sundays excepted, in session; 15 days after
  adjournment. The governor's phone and contact page (governor.wyo.gov/contact/governor) haven't been checked by the
  owner. A new governor takes office January 4, 2027 (Gordon is term-limited): add them to `GOVERNORS`.
- **South Dakota (started 2026-11-01):** `python3 states/sd/fetch.py` reads the Legislature's JSON API
  (https://sdlegislature.gov/api/, the one its own pages use; no key): each regular session's bill list and action logs,
  each bill's detail (sponsors in order, subject keywords), every vote member by member (votes/<id>.json, by
  SessionMemberId), members, committees, and the Legislature's lists of bills signed and vetoed (logs.json, to check
  totals: 2026's 240 and 2 match). `states/sd/contacts.py` runs after it. `states/sd/convert.py` reads each action's
  kind (ActionId) and who acted: "Do Pass" is a committee's report when a committee acts and the house's passage when
  the whole house does (ActionCommittee.FullBody); "Deferred to the 41st legislative day" (there are 40) and tabling kill
  a bill in committee (`heldLabel`); "Reconsidered" undoes the house's earlier vote, and a new vote follows. A floor
  "Do Pass Amended" in the second house doesn't mean it changed the bill: passed both houses needs the presiding
  officers' signatures, a concurrence or a conference report adopted in both (steps with no house are the conference
  committee's own votes, "Concurred in amendments 4-2", and don't count; HB 1140 of 2024 died in conference). Topics from the subject keywords
  (`KEYWORD_TOPICS`). No summaries: the title is the act's one-line description ("Provide for ..."). Bill pages are
  addressed by the Legislature's bill id (a version's `link`). Each district elects a senator and two representatives
  (26 and 28 from subdistricts 26A/26B): seats "S:12", "H:12a"/"H:12b" (New Jersey's scheme), one district list for both
  houses. Members' phones are the House's and Senate's switchboards. One session a year from the second Tuesday of
  January (40 days in odd years, 35 in even), plus a veto day near the end of March (`vetoDay()`); each year's last
  regular day is in `STATE.dated` (add each year's). Governor 5 days, Sundays excepted, in session; 15 after.
- **Utah (started 2026-11-07):** `python3 states/ut/fetch.py` reads the Legislature's developer API (glen.le.utah.gov; the
  token is the UTAH_API_TOKEN secret or ~/.utah_api_token, never printed) and members' votes from le.utah.gov's vote pages
  (robots.txt allows /DynaBill/svotes.jsp and /mtgvotes.jsp; Crawl-delay 10), 40 minutes a run until all ~12,000 are read,
  each once; `states/ut/contacts.py` runs after it (the API has current members only). Since 2025 each action has a code
  ("HPASS3"), a time, its owner (who has the bill next: "House Transportation Committee") and its vote; 2024's records are
  older (wording and a date), so `states/ut/convert.py` gives them codes from the same wording in 2025-26 and takes their
  votes and times from each bill's status page (data/ut/2024/status/). Dates come as "2026-01-19 11:07:38" or "2/18/2025
  3:38 PM" (`stamp()`). Each house's Rules Committee is a gate (`STATE.gates`): new bills start there, it sends them to
  standing committees and later decides which reach the floor. A recall after the presiding officers sign undoes it (SB
  254 of 2025), and a reconsideration voted by voice shows 0-0. The vote pages' own lists beat the API's tallies (SB 141 of
  2026: 6-0 vs 5-1). A committee's substitute, amendment and final votes on one day show as one. "What it does" is the
  General Description and Highlighted Provisions. Laws and vetoes match the Legislature's passed list bill for bill (2025:
  544 and 6; 2026: 493 and 2). One 45-day session a year from the third Tuesday of January; governor 10 days (Sundays
  excepted) in session, 20 after. Separate Senate (29) and House (75) districts by city, town or county.
- **Colorado (built 2026-11-07):** `python3 states/co/fetch.py` reads leg.colorado.gov's pages (no API; three seconds
  apart, since it answers "too many requests" faster; robots.txt bars the file downloads, which aren't read): each bill's
  page (history, sponsors by slug, committees, subjects, the Legislative Council Staff summary, session laws), every
  committee and floor vote member by member, members and committees; `states/co/contacts.py` runs after it. Members'
  votes don't hold the state off the site: they fill in run by run. `states/co/convert.py`: history lines name their
  house ("House Committee on Finance Refer Amended to Appropriations": approved and sent on; "Postpone Indefinitely":
  killed; "Lay Over": held; "Third Reading Passed": the passage); the page lists them newest first but not always in
  order (sorted by day). The bill's status ("Became Law", "Did Not Become Law") decides laws and vetoes, which match it
  exactly; an override needs both houses (SB 25-086: only the Senate overrode). Floor votes count only the bill's own
  motions (third reading "Bill", Concur, Repass, Adopt, Override), not amendments. Concurrent resolutions (constitutional
  amendments) aren't downloaded. Leaders are named only for the current year: past years' member pages show today's
  positions and houses.
- **Indiana (built 2026-11-08; not yet in build_site.sh, publish.yml or states.json):** `python3 states/in/fetch.py` reads the
  General Assembly's API (api.iga.in.gov, with the owner's key: INDIANA_API_KEY or ~/.indiana_api_key, a header, never
  printed): each regular session's bill list, every action and roll-call tally in one answer each, each HB, SB, HJ and SJ in
  full (authors, sponsors, versions with the Legislative Services Agency's digest, subjects), legislators and committees;
  `states/in/contacts.py` runs after it. The package is named "in", a Python keyword: its files load each other with
  importlib (like Oregon's). `states/in/convert.py` reads the plain-English actions, each with its chamber: "First reading:
  referred to Committee on X"; "Committee report: amend do pass, adopted" (the house adopting the report; "...; reassigned to
  Committee on Y" sends it on); "Recommitted to Committee on Ways and Means pursuant to House Rule 126.3" (bills that cost
  money); "Third reading: passed; Roll Call 143: yeas 40, nays 9" (the passage); a motion to refer that failed ("...; Failed,
  Roll Call ...") isn't a referral. Passed both houses: "Returned to the X without amendments", the first house concurring,
  the same conference report adopted by both houses, or the presiding officers' signatures; all three signatures (Speaker,
  President Pro Tempore, President of the Senate) mean presented to the governor (the presentment day isn't recorded, so the
  governor's 7-day deadline, `govDeadline()`, counts from the last signature: an estimate). Laws: "Signed by the Governor",
  "Bill Became Law on 8th Day Without Signature", a "Public Law 126" number (`STATE.lawWord` "Public Law"); "Vetoed by the
  Governor". Signatures and the governor's lines carry only a date: within a day, timed lines sort first. The authorship
  lines ("Authored by", "... added as coauthor") are dropped from the history (the sponsor lists hold them). Committees
  don't vote bills down on the record: a bill the chair never hears just stays ("no action"). Votes are tallies only (the
  roll calls' member lists are PDFs the API doesn't serve). Joint resolutions proposing amendments (not the "Vehicle joint
  resolution" placeholders, nor calls for a federal convention) are tagged "const": two General Assemblies in a row, then
  the voters, never the governor, though they get Public Law numbers; the digest says "has been agreed to by one general
  assembly" on the second passage (`STATE.amendmentFinal` reads it from the summary). "Vehicle Bill." placeholders (about
  60 a year) are `shell`. "What it does" is the latest version's digest, split into paragraphs of a few sentences. Topics
  from committees (`COMMITTEE_TOPICS`) and the subject index's headings (`SUBJECT_TOPICS`). Earlier years linked by short
  description and first author, never to a law. Legislators: the API's members and committees (chair, vice chair, ranking
  minority member); emails and caucus pages from Open States' public-domain file (as for Ohio and Pennsylvania; the API has
  none); phones are the caucuses' shared lines (House R 800-382-9841, House D 800-382-9842, Senate 317-232-9400 /
  800-382-9467). Leaders (`LEADERS`, `POSITIONS` in profile.py) checked 2026-11-08: Senate Republicans chose Chris Garten to
  follow Rodric Bray as President Pro Tempore once the Senate votes after the November 2026 election: change `LEADERS` then.
  A veto is overridden by a majority of each house's members (legislatures.json `"override": "majority"`), until the end of
  the next regular session. One session a year, long in odd years (by April 29), short in even (by March 14); each year's
  first and last days are in `STATE.opened`/`STATE.dated` (add each year's). Totals: 2024 171 laws and 1 veto (HEA 1002),
  matching the news; 2025 243 bills became Public Laws (P.L. 1-246, with two amendments and an Article V resolution; the
  Bankers Association counted 244); 2026 163 and no vetoes. Bill pages: iga.in.gov/legislative/<year>/bills/<house|senate>/
  <n>/details (the joint resolutions' address is a guess). Separate Senate (50) and House (100) districts by city, town or
  county (`states/in/towns.py`).
- **Arkansas (built 2026-11-08):** `python3 states/ar/fetch.py` reads
  the Bureau of Legislative Research's pipe files (webftp.blr.arkansas.gov) into data/ar/<biennium>/, and, for sessions with
  no kept copy of the files (2024F, 2024S2), arkleg.state.ar.us's bill pages in the files' shape (see its docstring);
  `--votes` reads members' votes from the roll-call pages (votes/), each once. A page a year: the regular session
  in odd years ("2025R"), the fiscal session in even years ("2026F": 30 days of appropriations; another bill needs two-thirds
  of each house to be introduced). Extraordinary sessions (2023S1, 2024S2, 2026S1: numbered from HB1001 again) are left
  out, as Texas's are. `session_kind()` is "regular"/"fiscal" and `session_label()` "2025 regular", so statistics compare
  like with like (each page compares with past sessions of its own kind: build_data.py's `insight_of`). `states/ar/convert.py`
  reads the history as written (each house has its own stamp wording: "Read the first time, rules suspended, read the
  second time and referred to the Committee on X- HOUSE" vs "Read first time, ... referred to X - SENATE"): "Returned by
  the Committee ... Do Pass" approved, "... do not pass" voted down, "Recommended for study in the Interim" (`heldAction`
  "INTERIM STUDY"); "Read the third time and passed" the passage (joint resolutions "adopted"/"concurred in"); "The vote by
  which HB1001 Passed was expunged" undoes it; "TO BE ENROLLED"/"ORDERED ENROLLED" passed both houses; "Correctly enrolled
  and ordered transmitted to the Governor's Office"/"DELIVERED TO GOVERNOR." sent; "Returned from the Governor as
  requested" takes it back; a law is its Act number (`STATE.lawWord` "Act"; signed, without signature or over a veto);
  "Governor Vetoed"/"Returned to House from Governor Having Been Vetoed" a veto; "line-item vetoed" stays a law. The
  history's ids aren't in date order: sorted by time. Sponsors are the members' Sponsor Names ("L. Johnson"), turned into
  full names from the members files (this General Assembly's, then the one before or after for members who left; the
  2023-24 file has one column fewer than 2025-26's). Members' votes: each roll call's Yeas, Nays, Non Voting (A), Present
  (B), Excused (E) by Sponsor Name, matched within the vote's house to that General Assembly's members ("H:12"); members
  who left are "H?McCollum". The 2023-24 roll-call pages never list Sen. Alan Clark, though their counts include him
  (HB1024's Senate vote: "Nays: 2", one name); `fill_missing()` puts back the house's members missing from every group
  when exactly one group is short by that many. Roll calls not yet read aren't shown (the files have no tallies). No summaries: the title is
  the subtitle, sentence-cased (`titled()`), and there's no "What it does". Appropriation bills (most of a fiscal session)
  are `budget` ("Budget bill"). Joint resolutions proposing amendments (not Article V applications) are tagged "const":
  one passage by a majority of each house's members, then the voters at the next general election (`amendmentOnce`; up
  to three per election); the records show them enrolled and "Approved by the Governor", a formality, so they stop at
  stage 3. Topics from committees (`COMMITTEE_TOPICS`) and title words. Committee agendas from CommitteeAgendas.txt
  (`agendas()`). Legislators (`states/ar/contacts.py`, from the members, committees and chairs files, no web pages; run
  for each year): phones and emails from the members file (31 have no phone there); standing committees of each house and
  the joint committees bills go to (Joint Budget, Public Retirement, Energy, Military and Veterans Affairs), each listed
  for both houses with that house's members. Leaders from the members file's 2025 lines (`LEADERS`, `POSITIONS`); the
  96th General Assembly chooses new ones in January 2027. Governor 5 days (Sundays excepted) in session, 20 after
  adjournment; a veto is overridden by a majority of each house's members (legislatures.json "majority"). Each year's sine
  die day is in `STATE.dated` (add each year's). Totals, matching the Act numbering (Acts 1-N, none missing) and the news:
  2023 890 Acts and 3 vetoes (HB1189, HB1622, SB509; HB1176 line-item); 2024 176 Acts; 2025 1,026 Acts and 3 vetoes
  (HB1889, HB1961, SB451; HB1265 line-item: "four vetoes" in the news); 2026 174 Acts. Separate Senate (35) and House (100)
  districts by city, town or county (`states/ar/towns.py`).
- **New Hampshire (built 2026-11-08):** `python3 states/nh/fetch.py`
  downloads the General Court's daily data files (the current year), and past years (2023-25) from its public SQL Server in
  the same shapes (see its docstring), into data/nh/<first year of the General Court>/; `states/nh/contacts.py` runs after
  it. A page is one session year (`YEARS = 1`; decided 2026-11-08): each year has its own deadlines, laws ("Chapter 74,
  Laws of 2025") and governor's actions, and the files are split by session year. A bill dies with its year unless a
  committee keeps it over to the second year of the General Court ("Retained in Committee" in the House, "Rereferred to
  Committee, MA" in the Senate): such bills are only in the second year's files, so `bill_rows()` gives the first year's
  page those with its LSR prefix ("25-"), their history cut at the line that kept them, and both pages show them under the
  same number (`STATE.continuedTo`, "Carried over to 2026 in the Finance Committee"). CACRs (constitutional amendments)
  are numbered "CACR 1" in both houses; the site reads a bill's house from its number, so they're "HCACR1"/"SCACR1"
  (`official()` drops the letter for links). `states/nh/convert.py` reads the Docket's lines as written ("Ought to Pass
  with Amendment 2025-0695h: MA RC 212-161 03/20/2025 HJ 9 P. 28"; MA/MF motion adopted/failed): a house passes a bill
  with the last "Ought to Pass" it adopts that isn't followed by a second referral ("Referred to Finance", the Senate's
  "...; Refer to Finance Rule 4-5"), unless that committee waives it ("Referral Waived by Committee Chair per House Rule
  47(f)"); the Senate's passage needs "OT3rdg" ("Ought to Pass: MA" alone leaves the motion pending, and the bill can be
  tabled on it: HB 246 of 2026). Adopting "Inexpedient to Legislate", interim study or indefinite postponement kills it:
  stage 0, shown as "Killed" (`STATE.heldAction` is a pattern here); its first committee's report decides `commFate`
  (no "held"). Passed both houses: both passed, and enrolled, or the first concurred, or both adopted a conference
  report, or the second passed it with no amendment. Line dates are the event's; entry times are the clerks' and out of
  order across houses, so lines sort by day, then house of origin / other house / between the houses / enrollment /
  governor, then step. Members' votes are the roll calls on the bill's own question (OTP, OTPA, Concur, conference
  report, veto override; not ITL, whose "yea" is against the bill); most votes are voice votes. Seats: "S:12", and a
  House district's members "H:612a", "H:612b" ... (Hillsborough 12 = county code times 100 plus the number; up to 10 a
  district), named by data/nh/district_names.json. "Where you live" (`states/nh/towns.py`, run once) reads the districts
  from the law, RSA 662:3 and 662:5, by town and city ward; a place votes in all its House districts (its own and a
  "floterial" one over it and its neighbors: `STATE.townInAllDistricts`, read by `myReps()`/`setTown()`). "What it
  does" is the analysis at the top of each bill's latest text (by the Office of Legislative Services; `analyses()` in
  fetch.py: billText.aspx?id=...&sy=...; the id from LsrsOnly, from the LSR number and year for 2023-24, else from the
  bill's status page), labelled by version ("... of the final version", "... as amended by the House", "... as introduced"
  when the analysis wasn't rewritten). A bill is read again only when the Docket shows a new adopted amendment or a
  chapter (data/nh/<first year>/analyses_<year>.json); summaries never mark the state incomplete, and the first copy (about
  5,100 requests at the 11-second delay, about 12 minutes a run) fills in over about a week. The budget bills say "No
  analysis needed." and have none. 142 representatives list no phone; none is invented. The governor's phone and contact page haven't been
  checked by the owner. Laws and vetoes match the LSRs file's chapters and status codes exactly (2023: 243 and 9; 2024:
  381 and 13; 2025: 305 and 12; 2026: 344 and 25). Add each year's first and last floor days to `opened`/`dated`.
- **Alaska (built 2026-11-08):** `python3 states/ak/fetch.py` reads the
  Legislature's BASIS public service (see its docstring) into data/ak/<first year>/, a two-year Legislature a page (the 34th
  is 2025-26; `YEARS = 2`); `states/ak/contacts.py` builds the contacts from its members and committees files (no web pages).
  Special sessions belong to the Legislature: their bills (HB 1001 on) are shown with the rest, and regular bills can pass
  in them ("Chapter 1, FSSLA 2025"). `states/ak/convert.py` reads the action codes: 001 first reading with 091 the
  committees in order; 002 "L&C RPT ..." a committee's report (approved), followed by 063 each member's recommendation (DP
  do pass, NR, AM amend, DNP), shown as one line; a report moves the bill to the next committee in its list (usually with no
  "REFERRED TO" line; the record's Referrals keep the final list) and after the last to the Rules Committee (stage 0, "Rules",
  until 080 "RULES TO CALENDAR"); 020/024 the passage; 128, and 125 when it names a passage or concurrence, undoes the house's
  last vote; 083 sent back with the other house's changes, then 026 concur (027 refused: not passed both houses, HB 120 of
  2023-24), or a conference report both houses adopt (032/058; 074 failed); 090 "RETURN TO (S), TRANSMIT TO GOVERNOR NEXT" the
  second house passed it unchanged; 033 transmitted; 034/036/129 a chapter; 038 vetoed; 040/039 override in joint session.
  The governor's lines are entered in the journal weeks later: their own wording dates them (`text_date()`). Some histories
  stop before the governor (12 laws of 2024): the status text ("CHAPTER 38 SLA 24") decides laws and vetoes too, and the
  record's Vetoed flag stays set after an override. Floor roll calls member by member, on the bill's own questions
  (`floor_question()`: passage, concurrence, conference report, override; not amendments or effective-date clauses);
  committees have no roll calls. Seats: Senate districts are letters A-T, numbered 1-20 in seat ids ("S:1" is District A,
  `P.senate_number()`) and named by data/ak/district_names.json; tracker.html's `DNUM()` shows a one-letter name as
  "District A". House "H:1".."H:40"; each Senate district is two House districts. Members' code ("FIE") ties votes to seats;
  members who left are "H?Tilton"; a member who changed name has two active records (Robyn Niayuq Burke, now Frier: the
  "Name Changed" record is left out of contacts, its code kept for votes). Party "N" (nonpartisan or undeclared) is shown
  as "Independent". Bipartisan coalitions run both houses (legislatures.json `note`; seat counts show Republican majorities,
  so balance.py's "unified" and the front page's dots would mislead: fix before adding Alaska there). Titles are the short
  titles, sentence-cased with abbreviations spelled out (`titled()`); the summary is the official title. No "What it does"
  (decided 2026-11-08): the only plain account is the sponsor statement (PDF), an advocate's case for the bill as introduced
  (HB 57 of 2025's is about phones in classrooms; the law became the education funding bill), with letterheads and staff
  contacts, and on about half the bills. Constitutional amendments (HJR/SJR "Proposing amendments to the Constitution"):
  two-thirds of each house's members, then the voters (`amendmentOnce`); none passed both houses in 2023-26. Governor 15
  days, Sundays excepted, in session, 20 after adjournment, counted from transmittal (often months after passage, so
  `passedBothBy` is the year's end, as New York's); overrides take two-thirds of the 60 legislators in joint session, or
  three-fourths for appropriations (legislatures.json "2/3", per house; the note says it). Sessions: the third Tuesday of
  January, 121 days (`STATE.dated` holds each year's last day: add each year's). Totals, matching the chapter numbering
  (1-N, none missing) and the news: 2023 26 chapters SLA 23 and 2 FSSLA 23, 3 vetoes; 2024 61 chapters, 9 vetoes; 2025 25
  chapters and 1 FSSLA 25, 9 vetoes (HB 57 and SB 183 overridden); 2026 61 chapters, 23 vetoes (HB 195 and HB 314
  overridden): 32 in the 34th Legislature, a record (31 reported by August 27, then HB 10 on August 31). Places (`towns.py`,
  run once): cities, Census-designated places, boroughs and census areas; a district counts for a place when it's 0.5% of
  the place's land or the place holds most of the district (Anchorage's urban districts). Leaders from the members file's
  comments; the 35th Legislature (January 2027) chooses new ones, and a new governor takes office December 7, 2026 (add to
  `GOVERNORS` and legislatures.json). The governor's phone and contact page haven't been checked by the owner.
- **North Dakota (built 2026-11-08):** `python3
  states/nd/fetch.py` reads the Legislative Council's static JSON API (see its docstring) into data/nd/<first year>/, a
  two-year Legislative Assembly a page (the 69th is 2025-26; `YEARS = 2`), though the regular session meets only in the odd
  year (early January, 80 legislative days, to about May: `STATE.dated` holds each session's last floor day, add each new
  one); `python3 states/nd/contacts.py` (every assembly; add it to states.json's run) builds the contacts. Special sessions
  (October 2023; January and September 2026) are in the assembly's own files, numbered after the regular session's (HB 1621
  on), so they're shown with the rest, as Alaska's. `states/nd/convert.py` reads the categorized actions: "Introduced, first
  reading, referred X Committee"; "Rereferred to Appropriations"; "Request return from committee" (the house takes it back:
  to the floor, another committee, or to withdraw it); committee reports "Reported back (amended), do pass / do not pass /
  without recommendation ... 13 0 1" (a tally: yes, no, absent; no names). Every report goes to the floor, "do not pass" too:
  committees can't hold bills, so the only stage-0 bills in a finished session are withdrawn ones (`heldAction`
  "Withdrawn", commFate "held"); "do pass" is "REPORTED" (approved), "do not pass" commFate "defeated". About nine in ten
  bills recommended against fail on the floor, and nine in ten recommended pass. "Second reading, passed/adopted ..., yeas N
  nays N" is the passage (resolutions "adopted"); "failed to pass" ends the bill unless "Reconsidered" (stage 1, "Failed on
  the floor"); a bill voted on in parts fails when every part lost on final passage (SB 2384 of 2025). Passed both houses:
  the second house passed it unchanged ("Returned to House" with no "(12)"), the first concurred and passed it again, or both
  adopted a conference report and passed it again; the presiding officers' signatures or "Sent to Governor" otherwise. Laws:
  "Signed by Governor 04/28" (the line's own date), "Signed by Governor, but item veto", "Passed over veto" in both houses,
  or filed with the Secretary of State without a veto; "Veto sustained". Chapter numbers come from chapters.json (the
  Session Laws' bill index); vetoed measures get chapter numbers too ("Measure Vetoed"), so the history decides. SB 2015 of
  2023 (signed) was later declared void by the Supreme Court (2023 ND 185): kept as a law with that line. Floor roll calls
  member by member ("Final Passage"; a passage line without a roll-call id is matched to one by bill, day and tally); seats
  "S:12", "H:12a"/"H:12b" by name within the district (`seats()`, shared with contacts.py; subdistricts 4A/4B are "H:4a"/
  "H:4b"); members who left are "H?O'Brien". Titles: there are no short titles, so `titled()` takes the official title's
  first "relating to" subject, "Budget: <agency>" for an agency's appropriation, "Appropriation to ..." or "Study: ..."; the
  summary is the official title. "What it does" is the Legislative Council's Title Summaries (a PDF per session, "Summary
  of Bills Enacted by the 2023 Legislative Assembly", listed on /research-and-archives/title-summaries months after the
  session; fetch.py reads it with pdftotext, weekly, and never marks the state incomplete): a paragraph on each bill
  passed (laws and vetoed bills, "would have ..."), labelled "From the Legislative Council's summary of the bill as
  passed."; 2023: 515 bills (510 of 599 laws; budget bills only for the parts that change other laws); 2025's edition
  wasn't listed yet in November 2026 and is picked up when it is. Nothing else per bill exists (statements of purpose of
  amendment are budget tables), so bills that didn't pass have none. Topics from
  committees (`COMMITTEE_TOPICS`) and words in the title and subjects. Concurrent resolutions amending the Constitution of
  North Dakota are tagged "const" (one passage by a majority of each house's members, then the voters at the election the
  resolution names: `amendmentOnce`, `ballotLine()`); other resolutions are left out. Earlier assembly linked by title,
  or same prime sponsor with half the title words shared, never to a law (`earlier()`). Hearings come from each bill's
  Hearings (named committee); `agendas()` lists upcoming ones. Governor 3 days (Sundays excepted) in session, 15 after
  adjournment; item vetoes on appropriations; override two-thirds of each house's members. Between sessions the current
  page reads like a finished one (`STATE.between()`, a getter for `stageText.live`). Shared hooks added for North Dakota:
  `STATE.oddsExits` (the Statistics chart's first two exits, without the committee breakdown), `STATE.fateLabels`, and
  `STATE.endedNote(b)` (a bill voted down or withdrawn mid-session: its status and "what's next" say so). Contacts: members
  file (party, district), biography pages (phones Cell/Home/Work, each once; email), standing and joint committees with
  chairs, current leadership positions (expired "Effective ... - ..." ones dropped). The governor's phone and contact page
  are from governor.nd.gov's contact page (checked by program 2026-11-08, not by the owner). The 70th assembly (December
  2026) chooses new leaders: update `LEADERS`. Totals, matching the Session Laws' bill index bill for bill: 2023 599 laws
  (585 regular-session bills with chapters, 14 special-session), 7 vetoes (5 sustained, HB 1416 and HB 1463 overridden),
  item vetoes on SB 2015 and HB 1544; 2025-26 608 laws (597 with chapters, 11 special-session), 4 vetoes (HB 1540, SB 2160,
  SB 2261, SB 2307; all sustained), item vetoes on 6 budgets. Places (`towns.py`, run once): cities, Census-designated
  places and counties, one district list for both houses.
- **Idaho (built 2026-11-08):** `python3 states/id/fetch.py` reads
  legislature.idaho.gov's pages (no API; see its docstring) into data/id/<year>/; `python3 states/id/contacts.py` (every
  year) builds the contacts. A page a year (`YEARS = 1`): the two-year Legislature (the 68th is 2025-26) meets once a year,
  from the second Monday of January to late March or April, and bills die at each adjournment (the second year's numbers
  carry on: 2026's House bills from H0501); laws, deadlines and the governor's actions are yearly. Bills are "H3", "S1023",
  "HJR4" (`official()` pads them back: "H0003"). `states/id/convert.py` reads each bill page's history, whose lines don't
  name the house: the bill is followed ("Received from the House ...", "Returned from the Senate ..." move it before the
  line; "Title apvd - to Senate", "Signed by President; returned to House", "Transmitted to Senate" after it), and a roll
  call's size (70 or 35) settles it. "Introduced, read first time, referred to JRA for Printing" is the print hearing's
  formality (a committee voted to introduce it); "Reported Printed and Referred to X" is the referral; budget bills from
  JFAC go straight to the floor ("Reported Printed; Filed for Second Reading"); members' personal bills are "Filed in the
  Office of the Chief Clerk" and go nowhere. "Reported out of Committee with Do Pass Recommendation", "... to 14th Order for
  amendment" (Senate) and "... Recommend place on General Orders" (House) are approvals; "Reported out without
  recommendation, as amended" is the Committee of the Whole, not a committee. "PASSED - 56-11-3" (ayes, nays, absent) with
  AYES/NAYS/Absent lists by surname; "FAILED" ends a bill unless "Motion to reconsider - PASSED" (`endedNote()`, as North
  Dakota's). Passed both houses: enrolled ("to JRA for Enrolling", "referred to enrolling"), or the second house passed it
  unamended, or the first concurred and passed it again (Idaho re-passes the engrossed bill after concurring). Governor's
  lines carry their own date ("Reported Signed by Governor on April 4, 2025", "Delivered to Governor at 3:04 p.m. on ...").
  Laws and vetoes also come from the list page's Enacted Legislation table and vetoed list, which agree with the histories
  bill for bill: 2024 330 laws (chapters 1-330), 2 vetoes; 2025 340 laws (one with line-item vetoes, H 482), 1 veto (S 1023,
  override failed in the Senate); 2026 344 laws, 4 vetoes; no veto was overridden. Joint resolutions (HJR/SJR) propose
  constitutional amendments: two-thirds of each house's members, then the voters (`amendmentOnce`); they go to the
  Secretary of State, never the governor (2024 HJR 5; 2025 HJR 4 and HJR 6). Sponsors: nearly every bill is a committee's
  ("House State Affairs Committee"); the member who asked is named only in the Statement of Purpose (a PDF, not
  downloaded), and the floor sponsors are history lines ("Floor sponsor: Bruce"), so legislators' sponsorship numbers
  count only the ~20 personal bills a year ("by RUBEL"); How's "About this data" says so. Titles are the list's short
  titles with abbreviations spelled out (`ABBREV`: "Approp, ITS, add'l" -> "Appropriation, ITS, additional"); the summary
  is the one-line description; "What it does" is the bill's Statement of Purpose, written for its sponsor
  ("From the sponsor's statement of purpose."; sponsors' statements kept, the owner's decision 2026-11-14), from
  /wp-content/uploads/sessioninfo/<year>/legislation/H0003SOP.pdf: only the purpose, without the fiscal note, contact or
  disclaimer, cut at 2,500 characters (`states/id/texts.py`). fetch.py's `statements()` reads each once (pdftotext; sop/
  and sop.json) and, while a year is live, asks again with If-Modified-Since when the bill's status changes (sponsors
  revise them in place); a missing one is an HTML page with status 200 (checked for "%PDF"). The first copy (about
  2,100) takes about 50 minutes; statements never mark Idaho incomplete. Roll-call
  names: "Crane(12)" (district), "Mr. Speaker" (Moyle), and substitutes written with both names, in a different order in
  each house: the House puts the member first ("Hill(Brown)": Brown sits for Hill), the Senate the substitute first
  ("Coho(Lenney)"); a name on that year's lists decides (`resolver()`). Members come from each year's committee pages
  (party by column; no House seat letter: past years take the current member's seat A/B where they still hold it, else
  the one left) and, for the latest year, the current member list; members not on a year's committee pages (the Speaker
  serves on none) take a current member's seat when it's free; members who left are "H?Achilles" (2024: Chew, Lee, Dixon,
  Nash; 2025: Achilles, Andrus). Each district elects a senator and two representatives: seats "S:12", "H:12a" (seat A),
  "H:12b"; one district list for both houses (`towns.py`: cities, communities and counties, "Boise City city" as "Boise
  city"). Topics from committees (`COMMITTEE_TOPICS`) and words in the subject heading and title. Earlier years linked by
  identical short title, one bill in each year, never appropriations or laws. Governor 5 days (Sundays excepted) in
  session, 10 days (Sundays excepted) after adjournment; no pocket veto; override two-thirds of the members present (each
  year's last floor day is in `STATE.dated`: add each year's). The governor's phone and contact page are from
  gov.idaho.gov/contact/ (checked by program 2026-11-08, not by the owner). Leaders from the member list (Speaker Mike
  Moyle, President Pro Tempore Kelly Anthon); the 69th Legislature organizes in December 2026.
- **Alabama (built 2026-11-08):** `python3 states/al/fetch.py` reads ALISON's GraphQL endpoint (see its docstring) into
  data/al/<year>/; `python3 states/al/contacts.py` (every year) builds the contacts from members.json and committees.json
  (no web pages). A page a year (`YEARS = 1`): one regular session, 30 legislative days within 105 calendar days, from the
  first Tuesday of February (the second Tuesday of January in an election year, the first Tuesday of March the year
  after: `opens()`); each year's last day is in `STATE.dated` (add each year's). Special sessions are left out.
  `states/al/convert.py` reads the history lines, which within a day aren't in order: sorted by day, then house of origin /
  second house / between the houses and the governor, then step (`kind_of()`'s rank). "Read for the first time and referred
  to the House Committee on X" (the "Pending Committee Action" status lines are dropped); "Reported Out of Committee"
  (committees report favorably or not at all); "Third Reading in House of Origin" with a roll call is the vote on the
  bill's Budget Isolation Resolution (three-fifths, to take it up before the budgets), not the passage; "Motion to Read a
  Third Time and Pass [as Amended] - Adopted Roll Call 59" is the passage (2024's roll-call field sometimes holds the BIR's number: the
  line's own number decides); "Concur In and Adopt" by the first house, "Non-Concur and Appoint Conference Committee" and
  a conference report adopted by both; "Currently Indefinitely Postponed" ends a bill (often its companion passed instead:
  `endedNote()`); "Ready to Enroll"/"Enrolled" passed both houses; "Delivered to Governor"; "Enacted" with the Act number
  (`STATE.lawWord` "Act", chapter = 312 of "2025-312"); "Pocket Veto"; "Pending with Executive Amendment" (the governor's
  proposed amendment). SB 346 of 2026 passed the House and went back to committee with no line saying so: a status
  "Pending Committee Action in X" undoes that house's passage. Constitutional amendments are bills ("(Constitutional
  Amendment)" in the byline, the subject "Constitutional Amendments Statewide", a short title ending "Constitutional
  Amendment", or an official title "Proposing an amendment"): tagged "const", three-fifths of each house's members, then
  the voters (`amendmentOnce`, `ballotLine()`); they get Act numbers and go to the Secretary of State (a few local ones
  are also "Delivered to Governor" and "Enacted"), so they stop at stage 3. Local bills (a county as the subject, "(N &
  P)" in the byline or a local notice, or a local or county legislation committee; not "Statewide" amendments) are narrow
  kind "place": 151, 182 and 187 a year. Roll calls name every member (Y, N, A abstain, P pass: both shown as
  "Abstained"); only the bill's passage, concurrence and conference-report votes are the bill's (BIRs and amendment votes
  are history lines: "Amendment adopted (Orr's motion), 32-0"). Seats "S:12", "H:45" by full name from the member records
  (past members keep their records); Matt Woods moved from House District 13 to Senate District 5 (`P.MOVED`). 2026's House
  roll calls 273-596 count Kristin Nelson (sworn in then) without naming her: `roll_call()` puts back the year's members
  missing from the list when one group is short by exactly that many. 2024's Senate roll call 607 (a BIR) lists senators
  of decades ago; names that don't resolve are dropped when a list is longer than the house. "What it does": the act's
  summary for a law ("From the act's summary."), else the Legislative Services Agency's synopsis of the bill as introduced,
  its "This bill would ..." sentences first (`synopsis_text()`); HB 66 of 2024's summary has a replacement character for an
  apostrophe. Topics from the Legislature's subjects (`SUBJECT_TOPICS`; a county is "local") and committees. Titles are
  the short titles; the summary is the official "Relating to ..." title. Bill links: ALISON has no page per bill, so the
  newest text PDF, the introduced PDF and the Secretary of State's act page. Earlier years linked by identical short title
  (four words or more), never laws or appropriations. Governor (Kay Ivey, term-limited; a new governor takes office in
  January 2027: add to `GOVERNORS` and legislatures.json) 6 days (Sundays excepted) in session; 10 days after adjournment,
  then a pocket veto; override a majority of each house's members ("majority"). Leaders: Speaker Nathaniel Ledbetter,
  President Pro Tempore Garlan Gudger (the members list also gives Matt Woods that title; dropped); the Legislature elected
  November 2026 organizes in January 2027. Totals (Act-numbered bills, as the data has them): 2024 302 laws and 17
  amendments (Acts on bills; Act numbers up to 453 include joint resolutions, not downloaded), 1 pocket veto (HB 446); 2025
  305 laws and 5 amendments (the governor's office announced 287 bills and 147 resolutions signed: not reconciled); 2026
  366 laws and 34 amendments; SB 240 of 2026 got an executive amendment the Legislature didn't take up before adjourning,
  and died (the news; its history shows only "Delivered to Governor"). A bill still at "Delivered to Governor" 10 days
  after sine die (`P.SESSION_ENDS`, kept with profile.js's `STATE.dated`) is stage 6: "Not signed: died after the session
  (pocket veto)", or "Died: the Legislature didn't act on the governor's amendment" when the history shows the
  amendment; SB 240 gets the first. The governor's site has no veto lists. Separate Senate (35) and House (105)
  districts by city, town or county (`states/al/towns.py`, from the Census Bureau's 2024 district files). Shared change
  made for Alabama: the "reintroduce it in January" ask (`reintroAsk()`) names the month the next session opens
  (`STATE.opens()`, March in 2027), where a state has `opens`.
- **Kentucky (built 2026-11-08):** `python3 states/ky/fetch.py` reads the Legislative Research Commission's bill record
  (apps.legislature.ky.gov/record/<yy>rs/, static pages; see its docstring) into data/ky/<year>/; `python3
  states/ky/contacts.py` (every year; not yet in states.json's run) builds the contacts from members.json and
  committees.json. A page a year (`YEARS = 1`): a regular session from the first Tuesday after the first Monday of January,
  60 legislative days in even years (to April 15) and 30 in odd years (a few days in January, then February to March 30);
  `session_kind()` is "long"/"short", so statistics compare like with like. Each year's last day is in `STATE.dated` (add
  each year's). Special sessions are left out. House and Senate bills only: joint resolutions (HJR/SJR) have the force of law
  and go to the governor, but they're mostly road namings and directions to agencies, and the shared convention is bills
  plus amendments, so they're left out (the LRC's law lists include them: about 10 a year). Bills "WITHDRAWN" before
  introduction (no title, no history; about 25 a year) are left out. `states/ky/convert.py` follows the bill from house to
  house ("introduced in House", "received in Senate", referrals marked "(H)"/"(S)"; the passage lines don't name the house,
  and a tally larger than the Senate's 38 settles it). Every bill starts in its house's Committee on Committees (the
  leaders), which assigns it to a standing committee: `STATE.gates` ("Committees"); many bills are never assigned (492 in
  2024). "taken from X (H)", "1st reading", "returned to X (H)" are readings while the bill stays in committee; "reported
  favorably, 1st reading, to Calendar" (committees report favorably or not at all; no tallies); "2nd reading, to Rules" and
  "posted for passage in the Regular Orders of the Day" (Rules, the leaders, schedules floor votes); "recommitted to X (H)"
  puts a reported bill back in committee; "3rd reading, passed 79-17 with Committee Substitute (1)" is the passage (in the
  second house "with" an amendment means the first has to agree). Back in the first house: "House concurred in Senate
  Committee Substitute (1)" and "passed 90-5 ..." again, or "refused to concur", "Senate receded/refused to recede",
  conference and free conference committees ("Conference Committee report adopted in House and Senate" can be the report
  that they failed to agree, followed by a free conference committee: only "passed" lines and enrollment count). "enrolled,
  signed by Speaker of the House / President of the Senate" is passed both houses; "delivered to Governor"; "signed by
  Governor (Acts Ch. 4)", "became law without Governor's Signature (Acts Ch. 19)", "Vetoed", "23 line items vetoed", then on
  the veto days "veto overridden", "passed 72-27" (the override vote, not counted as a passage) and "delivered to Secretary
  of State (Acts Ch. 175)". A veto after the last day stands: "Vetoed and delivered with Veto Message to Secretary of
  State", or (SB 70 of 2026) "Vetoed" then "delivered to Secretary of State" with no chapter, which must not be read as an
  override. A law is a bill with an Acts chapter (`STATE.lawWord` "Acts ch."), not a constitutional amendment. Laws and
  vetoes match the LRC's status lists (list.json's `law_routes`/`veto_routes`) bill for bill (`python3 -m states.ky.convert`
  prints the comparison): 2024 212 laws (169 signed, 21 without signature, 21 over a veto, 1 filed without signature), 2
  vetoes standing (both after the session), 21 overridden, line-item vetoes on HB 1, HB 6, HB 265; 2025 148 laws (111, 11,
  26), every veto overridden, line items on HB 546, HB 566, HB 622, SB 25; 2026 191 laws (145, 17, 29), 1 veto standing (SB
  70), line items on 7 budget bills. Constitutional amendments are bills ("AN ACT proposing to amend Section 77 of the
  Constitution of Kentucky"): three-fifths of each house's members, then the voters at the next even-year November election
  (`amendmentOnce`, `ballotEvenYears`); they get Acts chapters and go to the Secretary of State, never the governor (2024 HB
  2 and SB 143; 2026 SB 10), tagged "const", stage 3. Votes are tallies from the history only: members' votes are in each
  bill's vote_history.pdf (not downloaded; linked from the bill, and "About this data" says so). "What it does" is the LRC's
  summary of the enacted version for a law, else of the bill as introduced. Titles: the official "AN ACT relating to X"
  as "X" (amendments "Constitutional amendment: ..."); the summary is the official title. Sponsors in order as "K. Moser"
  (2024's link to the district page: 1-100 House, 101-138 Senate districts): matched to today's members by initial and
  surname ("DJ Johnson", "G. Brown Jr.", "S. Funke Frommeyer"), else kept as written with the linked district (`resolve()`);
  only current members are published, so a past year's contacts are the current members who sponsored that year. Topics
  from committees (`COMMITTEE_TOPICS`) and the first six LRC index headings (`HEADING_TOPICS`; the record writes "And" and
  "and", so they're matched in lower case). Earlier years linked by the same title and prime sponsor, or the same LRC
  summary word for word, one bill in each year, never laws or appropriations. Governor (Andy Beshear, D, term-limited;
  the next takes office in December 2027: add to `GOVERNORS` and legislatures.json) 10 days, Sundays excepted, in and after
  the session (no pocket veto: a bill not returned becomes law); line-item vetoes on appropriations; override a majority of
  each house's members ("majority"; the Republican supermajority overrides most vetoes). The governor's contact page
  (ppc.ky.gov's constituent services form) and main line (502) 564-2611 are from governor.ky.gov's footer (checked by
  program 2026-11-08, not by the owner). Most members list only "LRC: 502-564-8100", the LRC's message line for every member:
  shown as "Capitol (LRC message line)", after a member's own home or work number. Leaders from the member list (Speaker
  David W. Osborne; Senate President Robert Stivers, a senator); the General Assembly elected in November 2026 organizes in
  January 2027. Separate Senate (38) and House (100) districts by city or county (`states/ky/towns.py`, from the Census
  Bureau's 2024 district files).
- **Mississippi (built 2026-11-08):** `python3 states/ms/fetch.py`
  reads the Legislature's bill status system (billstatus.ls.state.ms.us: static XML, ISO-8859-1; no robots.txt; a CA bundle
  for the missing GlobalSign intermediate; see its docstring) into data/ms/<year>/; `python3 states/ms/contacts.py` (current
  year; add it to states.json's run) builds the contacts from data/ms/members/. A page a year (`YEARS = 1`): one session
  a year from the Tuesday after the first Monday of January, 90 days, 125 in a four-year term's first year (2024, 2028);
  each year's last floor day is in `STATE.dated` (add each year's). Extraordinary sessions are left out (2025's June budget
  session, where the three line-item vetoes of 2025 were). `states/ms/convert.py` reads each history file: actions are
  "MM/DD (H) ..." with no year (`dated()`: the session's, the next year's for a line months before the one above it).
  "Referred To X;Y" (a double referral: X first), "DR - TSDP: JA To AP" (X approved it, on to Y, by code: h_cmte.xml /
  s_cmte.xml; "TSDPAA", "TSDPCS", "TSDBA" variants), "Title Suff Do Pass ..." / "... Do Be Adopted" approved; deadlines
  kill most bills ("Died In Committee", "Died On Calendar", "Died In Conference": `STATE.endedNote()` words them);
  "Passed"/"Adopted" the passage; "Reconsidered" undoes the house's last decisive vote (passage, concurrence, conference
  report), and a "Motion to Reconsider Entered" never decided holds it: when the bill then dies, the vote never took effect
  (HB 1602 of 2026, shown as died on the House calendar). Passed both houses: "Concurred in Amend From ...", "Returned For
  Enrolling", a conference report adopted by both houses (since the last "Recommitted For Further Conf"), or a presiding
  officer's "Enrolled Bill Signed"; sent to the governor once both have signed (the history never shows the delivery).
  "Approved by Governor", "Law W/out Governor's Signature", "Partially Vetoed By Governor" (a law), "Vetoed", "Veto
  Overridden" in both houses; the chapter number (CHAPNUM) is the law's number, and a vetoed bill whose override passed
  only the House (HB 1648 of 2026: DISPOSITION says "Law", no chapter) stays vetoed. Concurrent resolutions whose short
  title starts "Constitution;" are tagged "const" (two-thirds of each house, then the voters: `amendmentOnce`,
  `ballotLine()`); other resolutions are left out. Titles are the short titles; the summary is the long title in sentence
  case (`sentence()`: names restored from the short title's capitalized phrases), plus "Passing it takes three-fifths of
  each house" when VOTETYPE says so; no "What it does" (there are no summaries). No votes: roll calls are PDFs, and the
  history lines carry no tallies. Local and private bills (the Local and Private Legislation committees) are narrow kind
  "place" and topic "local"; "Suffrage; restore to <a person>" bills (20-70 a year) are narrow kind "person". Authors by their author-page slug ("creekmore_iv"), named from the current member files, else
  that year's h_auth.xml / s_auth.xml. Contacts: the member files (district, party, Capitol/business/home/cell phones,
  room, committees with "C" chair and "V" vice chair); emails are user names, completed with "@house.ms.gov" /
  "@senate.ms.gov", the domains the Legislature's own stylesheets add (members/dtds_xslts/house.xslt and senate.xslt,
  checked 2026-11-08). Sen. Chris Johnson's file says District 44 (Polk's); his counties put him in 45
  (`C.DISTRICT_FIX`); contacts.py reports any seat claimed twice. Senate Districts 24 and 26 are vacant (November 2026). Leaders: Speaker
  Jason White; the Lieutenant Governor, Delbert Hosemann, presides over the Senate and refers its bills (not a senator: his
  phone and email from ltgovhosemann.ms.gov, checked by program 2026-11-08). The governor's phone and email are from
  governorreeves.ms.gov/contact/ (checked by program 2026-11-08, not by the owner). Governor 5 days (Sundays excepted) in
  session, 15 after adjournment; partial vetoes of appropriations; override two-thirds of each house. Earlier years linked
  by identical short title and principal author (or a title one bill had in each year), never laws or appropriations.
  Places (`towns.py`, run once): cities, towns, villages and counties, separate Senate (52) and House (122) districts, from
  the Census Bureau's 2024 files, which predate the districts redrawn for the November 2025 special elections (How's
  "About this data" says so). Totals (laws: each bill with a chapter number; chapters run 1-N, 301-N, 901-N (local and
  private) and 2001-N (resolutions) with none missing on the measures read, except 2025's 450, 455 and 2040; vetoes
  matching the news): 2024 409 laws, 6 vetoes (HB 922, SB 2180, four suffrage bills), part vetoes on HB 1707 and HB 1830;
  2025 259 laws, 8 vetoes (no part vetoes in the regular session); 2026 376 laws, 6 vetoes (HB 895, HB 1152, HB 1648,
  SB 2477, SB 2632, SB 3402; none overridden), part vetoes on HB 1653, HB 1924, SB 2189, SB 3071. No constitutional
  amendment passed both houses in 2024-26. A first copy of three years takes about 4 hours (230 minutes on 2026-11-08).
- **Delaware (built 2026-11-08):** `python3 states/de/fetch.py` reads
  legis.delaware.gov's own JSON and pages (no robots.txt; see its docstring) into data/de/<first year>/; `python3
  states/de/contacts.py` (every General Assembly; add it to states.json's run after fetch.py) builds the contacts. A page per
  two-year General Assembly (`YEARS = 2`; the 153rd is 2025-26): sessions run from the second Tuesday of January to June 30
  each year, bill numbers run through both years and bills stay alive until the General Assembly ends; the next one's
  members take office at the November election (fetch.py lists the 154th from then). `states/de/convert.py`: one record
  per bill; a substitute ("HS 1 for HB 457", even "SS 2 for SB 100") keeps the bill's number and gives it its title,
  synopsis, sponsors and roll calls. The original's history copies its substitutes' lines ("HS 1 for HB 449 - Passed By
  House ...") under the day they were copied, so the governor's action can show twice days apart (HS 2 for HB 168 of 2023-24:
  9/30/24 and 10/2/24): the substitute's own history is used, the original's copies only for a substitute never read, and
  lines are matched by `line_key()` (an amendment's vote "Amendment SA 1 to SS 2 - Passed By Senate ..." isn't the bill's).
  History wording: "Introduced and Assigned to X Committee in House"; "(Re-)Assigned to X" (the second house, or
  Appropriations/Finance); "Reported Out of Committee (X) in House with 7 Favorable, 7 On Its Merits, 1 Unfavorable" (a
  committee releases a bill when most members sign, any of the three; committee votes are those counts, favorable plus
  merits as yes, no names); "Tabled in Committee" (`heldAction`); "Motion to Release Failed"; "Passed By House. Votes: 39
  YES 1 NO 1 ABSENT" (every passage is a roll call, matched member by member by short name within the house); "Defeated By
  ..." (with "Reason Taken" a motion); "Reconsidered in"/"Roll Call Rescinded in" undo the house's last vote; "Stricken";
  "Signed by Governor", "Enact w/o Sign by Governor", "Vetoed by Governor", "Veto Override Passed in House", "Enacted into
  Law", "Line-Item Veto - See Governor's Advisory #46". Passed both houses: both passed and, if the second adopted an
  amendment, the first passed it again. The list's status decides laws and vetoes too, and agrees bill for bill. Chapters
  (`Volume:Chapter` "85:341") number 1-N with none missing once the constitutional amendments, which get chapters too, are
  counted: 2023-24 (Volume 84) 524 laws + 7 amendment passages = chapters 1-531, 1 veto standing (HB 140, End of Life
  Options) and 1 overridden (HB 282); 2025-26 (Volume 85, to date) 539 laws + 11 amendment passages = 1-550, 4 vetoes standing
  (HB 393, SB 231, SB 279, HS 1 for HB 329) and 2 overridden (SB 63, SB 75). The records don't show when a bill is presented
  to the governor (often months after passing), so there's no stage 4 and no deadline estimate. Constitutional amendments
  are bills ("AN ACT PROPOSING ..." first passage, "AN ACT CONCURRING IN ..." second, two-thirds of each house's members in
  two General Assemblies), tagged "const", never the governor and never the voters: `STATE.amendmentFinal` reads the title,
  and `STATE.amendmentDone` (added 2026-11-08, read by tracker.html's pipeline counts, status line and odds line) replaces
  "went to the voters". Titles: the named act from the short title when it has one ("Fairness in Girls' Sports Act"), else
  the long title's "relating to" subject, put back in sentence case with the synopsis's spelling of names (`recase()`:
  three-capital-word phrases and acronyms only); the summary is the long title. "What it does" is the synopsis (the bill's
  own explanation, printed at its end, not part of the law). Seats "S:1".."S:21", "H:1".."H:41" (single-member, separate
  maps); a seat goes to the member who voted last in it, and members who left are "H?Parker Selby" (`seats()`); the member
  list has no party for Ronald Gray and Lyndon Yearick, taken from their pages' headings (`party_of()`). Contacts: members
  file, members' pages (Legislative Hall phone, email; a number three or more members list is labelled "Caucus office";
  former members' pages lose them), committees with chairs. Leaders (`LEADERS`): Speaker Melissa Minor-Brown, President Pro
  Tempore David Sokola (the Lieutenant Governor presides); the 154th chooses its own in January 2027. Governor Matt Meyer
  (D) since January 21, 2025; 10 days (Sundays excepted) after presentment, 30 after final adjournment (pocket veto);
  line-item vetoes on appropriations; override three-fifths of each house's members. The governor's phones and contact page
  are from governor.delaware.gov/contact/ (checked by program 2026-11-08, not by the owner). Places (`towns.py`, run once):
  cities, towns, Census-designated places and counties, separate Senate and House lists.
- **Montana (built 2026-11-09):** `python3 states/mt/fetch.py` reads the Legislature's API (api.legmt.gov, the one the
  Bill Explorer uses; Crawl-delay 10; see its docstring) into data/mt/<year>/; `python3 states/mt/contacts.py` (every
  session; add it to states.json's run after fetch.py) builds the contacts. A page per two-year Legislature named by its
  session's year (`YEARS = 2`, label "2025"): the Legislature meets in regular session only in odd years, from the first
  Monday of January (January 2 when that's New Year's Day), 90 legislative days; `STATE.dated` holds each session's last
  day (add each new one). Special sessions and joint resolutions (HJ/SJ: studies, letters) are left out. Two formats:
  2025 on from the current system (status names "(H) 3rd Reading" with a result enum, member-by-member floor votes,
  committee "executive actions" member by member, co-sponsors), 2023 from the archive (plain-English actions newest
  first, "(S) 3rd Reading Concurred", tallies only, sponsors by law-entity id); `states/mt/convert.py` reads both into one
  list of steps (`steps_current()`, `steps_archive()`). Committees hear every bill and vote "do pass" ("be concurred in"
  in the second house) or table it (`heldAction` "Tabled in committee": most bills that die); "Take from Committee; Place
  on 2nd Reading" is a blast motion; second reading is the floor's real vote (amend, pass, "indefinitely postponed"),
  third reading the passage; "Missed Deadline for General Bill Transmittal" (and revenue, appropriation, referendum)
  ends a bill (`STATE.endedNote()` words floor defeats and missed deadlines). Passed both houses: "Returned to House"
  (unamended), the first house concurring on third reading, a conference report adopted on third reading by both, or
  enrollment; "Returned with Governor's Amendments" (amendatory veto) takes it back from the governor until it's
  transmitted again. Two traps in the current system's results: a committee report's result is often
  "BILL_NOT_CONCURRED_AS_AMENDED" after the committee voted "be concurred in as amended" (reports are only of approved
  bills: ignored), and some failed floor votes are marked passed ("BILL_CONCURRED" on HB 93 of 2025's 24-26 third
  reading; ties 25-25 and 50-50): with a roll call, a motion for the bill carries only with more ayes than noes, and a
  "Do Not Concur" motion decides by its own tally (`decide()` in `record()`); "Do Not ..." roll calls aren't listed as
  members' votes. A few committee records have no members' votes (dropped). The member list keeps one record per member
  overwritten with their latest house and district (13 members in 2025: House members since elected to the Senate show
  as senators, two senators as House members): the house comes from the roll calls and `P.SEAT_FIX` (checked against
  Open States 2026-11-09); members who left (Mercer, Stafman, Bertoglio, Marshall) are "H?Mercer" in votes. Laws are
  decided by the chapter number (`sessionLawChapterNumber`; "Chapter 479", `STATE.lawWord` "Chapter"), which runs 1-N
  with none missing or repeated: 2023 783 laws, 25 vetoes of which 4 overridden by mail poll (HB 29, HB 693, HB 868,
  SB 4), so 21 stand, and HB 5's line-item vetoes; 2025 778 laws, 45 vetoes (the news's count), 2 overridden by mail
  poll (HB 368, HB 643), 43 stand, line-item vetoes on HB 2. Laws without the governor's signature (about 7 a session)
  show only "Transmitted to Governor" and a chapter. Constitutional amendments are bills with the subject CAP, tagged
  "const": two-thirds of all 150 legislators (100 votes, both houses counted together), then the voters at the next
  general election (`amendmentOnce`, `ballotLine()`); "3rd Reading; 2nd Chamber Vote Required" is a house's vote short of
  two-thirds, and one that passed each house without reaching 100 (HB 372 and HB 517 of 2023) dies there; none passed in
  2023 or 2025. Governor (Greg Gianforte, R) 10 days after delivery, in or out of session (Constitution Art. VI, sec. 10,
  as amended: no Sundays rule and no 25-day rule any more); bills reach the governor weeks after the session
  (`passedBothBy` is 60 days after it); vetoes after adjournment are overridden by the Secretary of State's mail poll,
  two-thirds of each house's members (legislatures.json "2/3"). No "What it does": the data has only short titles (the
  summary is empty). Titles are the short titles. Topics from the Legislative Services Division's subject codes
  (`SUBJECT_TOPICS`) and title words. Earlier sessions linked by short title (same prime sponsor, or one bill each), or
  the same prime sponsor with 60% of the title's words; never laws or appropriations. Bill links: the Bill Explorer,
  bills.legmt.gov/#/laws/bill/<session id>/<LC number> (2025) and /#/bill/20231/<LC number> (the archive; read from the
  site's own script, not checked in a browser). Contacts: emails from the member list; phones from Open States (about a
  third) plus the session message line (406) 444-4800 for all (not checked by the owner); committees with chairs and vice
  chairs. Leaders: Speaker Brandon Ler, Senate President Matt Regier (`LEADERS`); the 70th Legislature organizes in January
  2027. The governor's phone and contact page are from gov.mt.gov/contact (checked by program 2026-11-09, not by the owner).
  Places (`towns.py`, run once): cities, towns, Census-designated places and counties, separate Senate (50) and House
  (100) lists (Senate District n is House Districts 2n-1 and 2n).
- **Nevada (built 2026-11-09):** `python3 states/nv/fetch.py` reads
  NELIS (www.leg.state.nv.us/App/NELIS/REL/<session>/: server-built HTML fragments, no API; robots.txt bars only
  */Reports/* (the veto messages), exhibits, opinions and fiscal-note folders; see its docstring) into data/nv/<year>/;
  `python3 states/nv/contacts.py` (every session; add it to states.json's run after fetch.py) builds the contacts. The
  Legislature meets in regular session only in odd years, 120 days from the first Monday of February (`opens()`,
  `adjourns()` = day 120 in profile.js; the 83rd was 2025, the 84th opens February 1, 2027): a page per session labelled
  "2025–26" (`YEARS = 2`), the next session's prefiled bills (from late October) as the upcoming page. Special sessions
  are left out. The lower house is the Assembly (`LOWER = "A"`, seats "A:30", "Asm."; 42 Assembly and 21 Senate
  districts, drawn separately). `states/nv/convert.py` reads each bill's Overview page: the one-line summary is the title
  (without its "(BDR 52-503)"), the official "AN ACT relating to ..." title the summary, and the history, several steps to
  a line, matched by one tokenizer (`TOKENS`; `python3 -m states.nv.convert` prints any text it didn't read, and the laws
  and vetoes compared with the lists). The lines don't name the house: the bill is followed ("To Senate." / "In
  Senate."; a veto message goes to the house of origin). "From committee: Do pass" / "Amend, and do pass as amended" /
  "Without recommendation" are committee reports (no tallies; committees don't vote bills down: a bill not reported by the
  deadline dies, "(Pursuant to Joint Standing Rule No. 14.3.1, no further action allowed.)", the 14.3.1-.4 deadlines on
  days 68, 79, 102 and 109: `originDeadline()` is day 79, and `STATE.endedNote()` words the deadline deaths and floor
  defeats); "From committee: Concur in ... and further amend" is a conference committee's report, not a standing
  committee's. "Read third time. Passed[, as amended]. (Yeas: 24, Nays: 18.)" is the passage, "Lost." a defeat, "Action
  (of passage) reconsidered." undoes the house's last vote. "To enrollment." is passed both houses (after "Senate
  Amendment No. 667 concurred in." or both houses adopting a conference report), "Enrolled and delivered to Governor."
  sent, "Approved by the Governor. Chapter 60." a law (`STATE.lawWord` "Chapter", of the Statutes of Nevada), "Vetoed by
  the Governor." Laws and vetoes also come from the session's lists and agree with the histories bill for bill; chapters
  run 1-N with none missing: 2023 535 laws (AB 269, SB 266), 75 vetoes (the record reported at the time); 2025 519 laws
  (AB 288, SB 231), 87 vetoes (NELIS's list of 86 and SB 99, below). No veto was overridden. SB 99 of 2025 was vetoed June 2, 2025 and returned to the Senate with a veto
  message, but NELIS's history (read again 2026-11-09) shows only "Enrolled and delivered to Governor" and "(No further
  action taken.)", and it's on neither the laws nor the vetoed list: `VETO_FIX` in convert.py (a documented correction
  table) makes it a veto with a line saying the record misses it, for 87 vetoes in 2025, the press's count. Any other
  bill delivered and neither signed nor vetoed once the governor's time is up (`gov_due()`) gets "The records show no
  decision by the governor" and stays stage 4 without a deadline (`govDeadline()` returns none once past); under Art. 4,
  sec. 35 it would be law without signature, but SB 99 shows the record can just miss a veto, so no outcome is guessed. A veto
  during the session goes back to the bill's house at once ("Bill read with Governor's veto message", then "No further
  action taken"); a veto after the session (2023: 43; 2025: 54) goes to the next regular session, which can override it
  by two-thirds of each house (28 Assembly members, 14 senators): convert.py adds the line "Vetoed after the session
  ended: the veto goes back to the Legislature's 2027 session", which `STATE.vetoReturns()` reads (shared hook, added
  2026-11-09: tracker.html's status line, "what's next" and the ask to vote to override or sustain, until that session
  adjourns). An override would be "Passed, notwithstanding the veto of the Governor." (a guess at the wording: none in the
  data yet; check when the 2027 session acts). Joint resolutions whose bill draft is a "C-" request propose
  constitutional amendments: tagged "const", a majority of each house's members in two sessions in a row, then the voters
  at the next general election; they go to the Secretary of State ("File No. 24"), never the governor (2023 AJR 5, AJR 6,
  SJR 7; 2025 AJR 8: first passages). A resolution passed the second time is listed under its first session's number
  ("SJR 7 of the 82nd Session") in a list fetch.py doesn't read, so second passages are missing (`amendmentFinal` reads
  that wording if they're ever added). Other joint resolutions (memorials) are left out; the laws list includes
  resolutions, which aren't counted. Floor votes: each final passage member by member (votes/), matched to its history
  line by house, day and tally; NELIS calls every one "Passed", lost ones too (AB 500 of 2025: 25-17, short of
  two-thirds; then 20-22), so the history decides. SB 1 of 2023 carries two May roll calls that match none of its history
  lines (left out). Roll-call names "Anderson, Natha" match the session's member list by house, last name and first name;
  Sen. Heidi Seevers Gansert is "Seevers O'Gara, Heidi" in 2023's roll calls (`seat_of()` matches the first word of the
  last name). Committee-sponsored bills (prefiled for agencies, local governments and officials: 416 of 1,049 in 2023,
  453 of 1,119 in 2025) show the committee as sponsor ("Assembly Committee on Judiciary"), as Idaho's do, so
  legislators' sponsorship numbers count only their own bills; How's "About this data" says so. The next session's
  prefiled committee bills name no committee yet ("A Senate committee (not yet named)"). "What it does" is the
  Legislative Counsel's Digest ("From the Legislative Counsel's Digest."), each paragraph led by its "This bill ..." /
  "Section 3 of this bill ..." sentences, background-only paragraphs last, statute citations removed (`digest_text()`);
  appropriation bills have none. Topics: the NRS title in the bill draft number (`NRS_TOPICS`: "(BDR 52-503)" is Title
  52, Trade Regulations), committees (`COMMITTEE_TOPICS`) and title words. Earlier sessions linked by the same official
  title (one bill each), or the same member with 60% of the title's words and 40% of the summary's (`earlier()`; 26 from
  2025 to 2023, read over by hand), never laws or appropriations. Bill links: NELIS's overview by bill key. Hearings:
  `agendas()` reads each bill's Upcoming Hearings. Contacts: the member list (party, district, Carson City room and
  phone, Las Vegas office room, post), committees with chairs and vice chairs; emails from Open States' public-domain
  file (data/nv/openstates_people.csv; the Legislature's pages hide them behind Cloudflare's script), matched by seat
  and last name (2027's new members have none yet). Toby Yurek (Assembly 19) resigned in October 2025: left out of 2025's
  contacts. The 2027 list (members-elect, from November 2026) still shows 2025's leadership posts, so no posts are taken
  from it; Assembly members and senators take office the day after the election. Leaders: Speaker Steve Yeager, Senate
  Majority Leader Nicole Cannizzaro (the Lieutenant Governor presides over the Senate); the 84th session chooses its own:
  update `LEADERS`. Governor Joe Lombardo (R) ran again in November 2026; if a new governor takes office January 4, 2027,
  add them to `GOVERNORS` and legislatures.json. Governor 5 days (Sundays excepted) in session, 10 days after
  adjournment; a bill not acted on becomes law. The governor's phones and contact page are from gov.nv.gov (checked by
  program 2026-11-09, not by the owner). Places (`towns.py`, run once): cities, Census-designated places (most of the
  Las Vegas valley) and counties, separate Senate and Assembly lists.
- **Minnesota (built 2026-11-09):** `python3 states/mn/fetch.py` reads
  the Revisor of Statutes' bill status API and the House's, Senate's and Legislative Reference Library's pages (see its
  docstring) into data/mn/<first year>/; `python3 states/mn/contacts.py` (add it to states.json's run after fetch.py) builds
  the contacts; `states/mn/towns.py` was run once. A page per two-year Legislature (`YEARS = 2`; the 94th is 2025-26):
  sessions from January (odd years; the second Tuesday since 2025) or February (even years, set by resolution: `STATE.dated`
  holds each year's opening day, add each year's) to the Monday after the third Saturday in May (`adjourns()`). Special
  sessions are included on their Legislature's page (decided 2026-11-09, so the 2025 budget doesn't look as if it never
  passed): the 2025 First Special Session (data/mn/2025-s1, June 9, 2025) passed most of the budget, 15 laws (its chapters
  1-15, none missing), from bills numbered HF 1 and SF 1 again. They're numbered "HFS2"/"SFS17" (`special_num()`: the house's
  letter stays first, a letter S, T ... for the first, second ... special session; the page shows "HF 2 (1st Special
  Session)": `STATE.numText()`, `specialOf()`), titled "... (2025 1st Special Session)", with no `chapter` (their laws are
  "Laws 2025, First Special Session chapter 3", in the history and the law link), House votes from the special session's
  folder and Senate votes from the regular journals. Regular-session omnibus bills whose content passed there instead get
  a history line ("Passed instead in the 2025 First Special Session as HF 2 (1st Special Session chapter 3)",
  `link_specials()`): matched by identical description, plus `SPECIAL_LINKS` for the same budget area worded differently;
  13 bills, 4 of them numbers reused for different 2026 laws (HF 2433, HF 2438/SF 2082, SF 2077, HF 2484), which stay laws.
  The notice and How's "About this data" say so (`STATE.specials`). Resolutions are left
  out (HF 197 of 2023, the ERA memorial, has a "Resolution 1" law number). `states/mn/convert.py`: House Files and their
  Senate companions (COMPANION_TYPE/NUMBER, mutual pairs only) are one record, lead = the number that got further, each
  keeping its own history. Each number's record has one list per house; each list copies the other house's messages
  ("Senate accedes", "House conferees", "Senate adopted conference committee report, bill repassed"), which are dropped,
  except "Returned from Senate (with amendment)". The governor's lines come from the bill's own house's list (the other's
  dates can differ by a day; a mistyped year, "05/27/226" on HF 4591 of 2025-26, takes the other list's date). A House
  motion's outcome is the next line ("Motion to re-refer" X, "Motion did not prevail" is not a referral). The Senate writes
  one passage several ways on a day ("Senate adopted CC report and repassed bill" 39-26 and "Third reading" 40-25: one
  vote, the "Third reading" tally); "Senate concurred" alone is agreement, not the repassage (SF 4225 of 2023-24 never got
  its repassage: the constitutional deadline). Passed both houses: the first house's "Returned from" line without
  amendments, its repassage after agreeing to the second house's amendments, the same conference report repassed by both,
  or the governor; a second house that amended the bill (in committee, by Rule 45 to match its own text, or on the floor)
  and then passed it "plainly" still needs the first house (HF 1587 of 2023, SF 1943 of 2025). Laws are chapters numbered
  through the Legislature (2024 continues 2023), from the governor's approval; vetoed bills and constitutional amendments
  get chapter numbers too. Totals (`python3 -m states.mn.convert`): 2023 73 laws + 1 veto (HF 2369, chapter 65, Walz's only
  veto of 2023-26 on the LRL list) + 1 amendment (HF 1900, chapter 67) = chapters 1-75; 2024 52 laws, chapters 76-127;
  2025 39 laws, 1-39; 2026 91 laws + 1 amendment (HF 3900, chapter 114) = 40-131: none missing, no line-item vetoes.
  Constitutional amendments are bills ("constitutional amendment proposed"), tagged "const": a majority of each house's
  members, then the next general election (`amendmentOnce`, `ballotEvenYears`). Votes: House floor votes member by member
  from house_votes/ (passages matched 264 of 268 in 2023-24, 271 of 272 in 2025-26), the Senate's from the journal text
  (`senate_rolls()`: roll calls after "The question was taken on the (re)passage of the bill"; 190 of 190 and 202 of 202, every
  name list adding up to its tally); House names ("Anderson, P. E.") are tied to members through the authors lists'
  LEGISLATOR_KEY, Senate names by last name; members voting that day but not on the bill show as not voting. Only current
  members are listed (2023-24: 81% of House and 92% of Senate names tied to a seat; 2025-26 99%). No committee votes.
  "What it does": the newest House Research or Senate Counsel, Research and Fiscal Analysis summary of either number (PDF text:
  page furniture dropped, lines rejoined, lost "ti"/"fi" ligatures (U+FFFD) put back from the summaries' own words; House
  Research's section tables cut to each section's heading and first sentence; 4,000 characters at most), about a third of
  records; otherwise the Revisor's one-line description, the summary line, is all there is. Titles: the description's first
  clause when long. Seats: "S:12"; House districts 12A/12B are numbered 1-134 ("H:23" = 12A, `profile.house_seat()`) and
  data/mn/district_names.json gives the page their names (tracker.html's `DNAME()` treats "12A" as a number: "District 12A").
  No address lookup (the Census geocoder answers "12A"); `findReps` links the LCC's district finder. Places: about 850 cities and
  the 87 counties, separate Senate and House lists. Balance: the House is tied 67-67 with a power-sharing agreement (Speaker Lisa
  Demuth, R; each committee a Republican and a DFL co-chair: the first listed is the chair on contact cards), so
  legislatures.json marks it `coalition` with a `note`; Senate DFL 34-33. DFL is counted as Democratic. Leaders: Speaker
  Demuth, Senate Majority Leader Erin Murphy (the 95th Legislature chooses its own in January 2027). Governor Tim Walz (D),
  3 days (Sundays excepted) in session, 14 days after adjournment for bills passed in the last 3 days, then a pocket veto;
  item vetoes on appropriations; override two-thirds. The governor's phone ((651) 201-3400) and address are from general
  knowledge: mn.gov's contact page doesn't answer automated readers; not checked by the owner. If a new governor takes office
  January 4, 2027, add them to `GOVERNORS` and legislatures.json.
- **Missouri (built 2026-11-13):** `python3 states/mo/fetch.py` reads the
  House's XML exports (documents.house.mo.gov, Crawl-delay 20; house.mo.gov bars "?" addresses and isn't read) and the
  Senate's website (see its docstring) into data/mo/<year>/; `python3 states/mo/contacts.py` (add it to states.json's run
  after fetch.py) builds the contacts; `states/mo/towns.py` was run once. A page a year (`YEARS = 1`): the session opens the
  first Wednesday after the first Monday of January, no bill passes after 6 p.m. on the first Friday after the second
  Monday in May (`lastBillDay()`, `sessionEnds()`), it ends May 30; the veto session is the first Wednesday after the second
  Monday in September (`vetoSession()`). Extraordinary sessions, concurrent and simple resolutions are left out. House bills
  (HB, HJR) come from the House's export, which carries every action in both houses with committee and floor tallies;
  Senate bills (SB, SJR) from the Senate's bill page and "All Actions" list (newest first, no tallies; the House's tallies on
  Senate bills only when the bill is in its SenateActList.xml, about half). Trap: each year's House folder also holds the
  previous year's appropriation bills under their old numbers (2024's HB 1-20 are 2023's budget bills) with nothing but
  "Message Received from the Governor, pursuant to Article IV, Section 27" (spending restrictions, not vetoes): `stub()`
  skips them, and the line is kept as written elsewhere. `states/mo/convert.py` (`walk_house_xml()`, `walk_senate_page()`
  into one `Walk`): House bills go from a standing committee to one of the House's Rules committees ("Rules -
  Administrative", "- Legislative", "- Regulatory Oversight"), which votes again; bills that cost money to Fiscal Review
  (House) / Fiscal Oversight (Senate): all shown as committees, the first standing committee is `firstComms`. "Voted Do
  Pass" lines are skipped (the "Reported Do Pass" report follows, with the House committee's tally); "Perfected" is the
  first floor vote (voice), "Third Read and Passed" the passage; "House Adopts" / "S concurs" agree to the other house's
  changes (the House's tally then is its repassage), conference reports need both houses; "Truly Agreed To and Finally
  Passed" is passed both houses (it happens only after the last vote; 0 bills passed both and weren't sent). A bill combined
  into another (a House file's SubstitutedBy, the Senate's "Bill Combined w/SCS SBs 3 & 5": lead is the first number) gets
  "Combined into HB 594" and stops. Governor: "Approved by Governor" / "Signed by Governor" (law), "Vetoed in Part by
  Governor" (a law with items vetoed: the 12 budget bills each year), "Governor took no action, sent to Secretary of
  State/Article III, Sec. 31" (law without signature: SB 751 of 2024), "Letter of approval" (kept as written), "Failed to
  Pass over Veto" (an item-veto override that failed). No bill was vetoed outright in 2024-2026 ("Vetoed" lines are read
  but none exist). Laws match the Senate's "Truly Agreed To and Finally Passed" lists (BillStatus/TATFP?year=) bill for bill
  (checked 2026-11-13): 2024 44 (29 HB, 15 SB), 2025 64 (37, 27; the governor's 2025 action list agrees), 2026 96 (58, 38).
  Constitutional amendments are joint resolutions: a majority of each house's members, then the voters at the next general
  election or a special election the governor calls (`amendmentOnce`, `ballotEvenYears`, `ballotLine()`); never the
  governor ("Delivered to Secretary of State"): 2024 SJR 71, SJR 78; 2025 HJR 23, HJR 73; 2026 HJR 173, SJR 87, SJR 95.
  Votes: senators member by member from the Senate Journal's text (`senate_rolls()`: "was read the 3rd time and passed by
  the following vote", the bill from the last abbreviated reference before it, "HBs 737 and 486"; conference reports and
  concurrences found too), matched to the passage by day and bill: 313 of 317 Senate passages (2024 61 of 64, 2025 106 of
  107, 2026 all 146; the rest are on journal days not downloaded, 2024-04-17 and 2025-04-22); every list adds up to the
  journal's printed totals. Names are "Brown (16)" (district) or a surname matched to the year's roster (Senate bill list
  sponsors with districts, the House's conferee entries with district 200+n, today's senators); 2024's journals write "Brown
  (16th Dist.)" and sometimes run two names together with one space ("Bernskoetter Brattin", `senate_seats()`). House
  journals and House roll-call PDFs aren't downloaded: House floor votes are tallies (none for most Senate bills). Committee
  tallies are the House's. "What it does" is the Senate's bill summary of a Senate bill's current version ("From the Missouri
  Senate's summary of the bill's current version (SS SCS SB 3)."): cross-references ("These provisions are identical to
  ...") and the analyst's name dropped, capitals headings in sentence case, "Current law ..." openings led by the "This act"
  sentence; House bills have none (the House's summaries, house/summaries/, weren't downloaded yet: about a third of laws
  have a summary). Titles: the official one-line description ("Modifies provisions relating to county officials"); the short
  title ("COUNTY OFFICIALS", House bills) as the summary line. Topics from committees (`COMMITTEE_TOPICS`), the House's subject
  index (`SUBJECT_TOPICS`) and title words. Earlier years linked by the same description and sponsor (one bill each),
  never laws or appropriations. Contacts: representatives from each year's member files (emails, Capitol phones, leadership;
  past years' files have no phones or emails), senators from members/senate.json (today's: the "Email the Senator" contact
  form, no emails; past senators who left are names only, without party); House committees from CommitteeList.xml, Senate's
  from committees.json. Leaders: Speaker Jonathan Patterson, President Pro Tem Cindy O'Laughlin (the General Assembly
  elected in November 2026 organizes in January 2027). Governor Mike Kehoe (R, since January 13, 2025; before him Mike
  Parson): 15 days, or 45 days from May 30 for bills delivered at the end (`govDeadline()`), else law without signature;
  item vetoes on appropriations; override two-thirds of each house's members (23, 109). The governor's phone and contact
  page are from governor.mo.gov/contact-us (checked by program 2026-11-13, not by the owner). Places (`towns.py`): cities,
  towns, villages, Census-designated places and counties, separate Senate (34) and House (163) lists; St. Louis city once.
- **New Mexico (built 2026-11-13):** `python3 states/nm/fetch.py`
  reads www.nmlegis.gov (see its docstring) into data/nm/<year>/; `python3 states/nm/contacts.py` (every run; add it to
  states.json's run after fetch.py: check_site.py wants contacts_<year>.json fresh) builds the contacts; `states/nm/towns.py`
  was run once. A page a year (`YEARS = 1`): a session from the third Tuesday of January, 60 days in odd years and 30 in even
  years (only the budget, the governor's call and vetoed bills), `session_kind()` "long"/"short"; `opens()`/`sessionEnds()`
  in profile.js compute both (no `dated`). Special sessions, memorials and joint resolutions other than constitutional
  amendments are left out. The converter reads no database: the Access file (LegInfo<yy>.zip) isn't needed (it was read
  once, by hand, with the pure-Python `access-parser` in a scratch environment, to check totals; it fails on LegInfo25), so
  nothing beyond Python's standard library is needed on GitHub. `states/nm/convert.py` reads each bill page's spelled-out
  actions (with calendar days) and, where they're short, the coded ActionText ("[5] HHHC/HJC-HHHC [8] DP-HJC ... SGND BY GOV
  (Mar. 21) Ch. 13."; key in data/nm/abbreviations.html): "Sent to HHHC - Referrals: HHHC/HJC" lists the committees in order,
  and there's no line when the bill moves on, so the referral list is followed (a report sends it to the next committee, the
  last one's to the floor; "Referred to:", "re-ref", "HAFC ref w/drn", "SCC referral removed" change it); "Withdrawn from
  committee ... for subsequent action" goes to the floor or the committee the ActionText's "w/drn-HTRC" names. Committee
  reports: "Do Pass", "Do Not Pass but ... Do Pass ... on Committee Substitution", "without a recommendation", "Do Not Pass,
  Bill Has Died", "Tabled Indefinitely". In 30-day sessions the Senate Committees' Committee (SCC = SXCC) rules each Senate
  bill germane first ("Reported by committee to fall within the purview of a 30 day session"); "Not Printed" ("not prntd-HRC")
  bills go to House Rules (HRC = HXRC): both are `STATE.gates`. "Passed in the House of Representatives - Y:64 N:0" is the
  passage; "Failed to Pass in the Senate, Bill Has Died" takes its tally from the ActionText. Second-house amendments (its
  committee's amendments or substitute, "Senate Floor Amendment", "fl/aaaa", "Floor substitute adopted") need "House has
  concurred", the other house receding, or both houses' "Report Adopted" (conference). The governor's lines have no calendar
  day: "Signed by Governor - Chapter 13 - Mar. 21", "LAW WITHOUT SIGNATURE." (day and chapter from the ActionText),
  "Vetoed by Governor" (dated from the governor's message), "Pocket Veto" (dated the governor's last day, 20 days after the
  session), "(partial veto)" in the ActionText (line items), "Veto Override Passed in House" (HB 65 of 2025: the Senate never
  voted, the veto stands). Chapters come from the ActionText: the spelled-out line is wrong twice (below). "Succeeding
  entries: H 2": folded into HB 2 (HB 3 each year). "Action Postponed Indefinitely": the session ended. Totals match the
  pages' "Current Location" bill for bill and the Legislature's own counts: 2024 69 laws, 1 veto, 2 pocket vetoes (LegStats:
  69 chapters, 1 veto, 72 to the governor), line items on HB 2, HB 252, HB 308, SB 246, SB 275; 2025 160 laws, 18 vetoes, 17
  pocket vetoes (the Legislature's and the press's count; LegStats unreadable), line items on HB 2, HB 450, SB 5, SB 31, SB
  425; 2026 71 laws, 2 vetoes, 1 pocket veto (LegStats the same), line items on HB 2, HB 332, SB 240, SB 273. Chapters run
  1-N with none missing or repeated. No law without signature but SB 104 of 2026. Constitutional amendments are joint
  resolutions whose short title ends ", CA": a majority of each house's members, then the voters (`amendmentOnce`,
  `ballotEvenYears`); "Signed by one or both houses ... SGND (C.A. 3)" is passed (2024 SJR 1, SJR 16; 2025 HJR 2; 2026 HJR 1,
  HJR 5, SJR 1), tagged "const", stage 3, never the governor. Votes: floor votes member by member from the vote PDFs' text
  (`read_roll()`: two columns of names, each X placed under its nearest column heading; YEA/NAY/PNV/EXC/ABSENT, Senate
  YES/NO/ABS/EXC/REC; file names vary, "HJR01HSVOTE", "SJR0016SVOTE", so the house comes from the text), matched to the
  passage lines by house and tally: 173 of 174 (2024), 509 of 511, 200 of 203 (the rest have a later or earlier roll call
  than the one PDF). Committee votes from the committee reports ("The roll call vote was 9 For 1 Against"; House reports name
  the no, excused and absent members, Senate reports the yes votes too) and the tabling reports ("Motion to TABLE PASSED":
  shown as the committee's vote against the bill, with a "Tabled by" line): 476, 1,413, 494. Names are matched to that year's
  members.txt within the vote's house, whose third column is the roll calls' tag ("Martinez, A.", "Romero, GA"); members who
  served that year but aren't on it (2024 lacks four senators; Herrera, Ferrary, Reeb left in 2026) come from their own pages
  (members/<code>.html, "Years of Service"); a member whose seat someone else now holds, or (this year's page) who no longer
  serves, is named ("H?Herrera"), not given the seat; all other names match. "What it does" is the Legislative Finance
  Committee's fiscal impact report synopsis ("From the Legislative Finance Committee's fiscal impact report."): the bill's
  (or its newest committee substitute's), then later amendments' (the report lists them newest first), page footers dropped
  and paragraphs split by page breaks rejoined; 62%, 89% and 67% of bills have one (2024-26). Titles are the short titles in title case
  (each word as the reports' "SHORT TITLE" writes it). Topics from committees (`COMMITTEE_TOPICS`), else title and synopsis
  words. Earlier years linked by the same short title and prime sponsor code, one bill each year, never laws or
  appropriations. Contacts: each year's members.txt (Capitol room and (505) 986 phone, several shared; email), names and
  pages from the members' pages, committees with chairs from committees.json; this year's page lists only members serving
  now (House 37 and 64 vacant). Leaders: Speaker Javier Martínez, President Pro Tempore Mimi Stewart (the Lieutenant
  Governor presides over the Senate); the Legislature elected in November 2026 organizes in January 2027: update `LEADERS`.
  Governor Michelle Lujan Grisham (D), term-limited: a new governor takes office January 1, 2027: add them to `GOVERNORS` and
  legislatures.json. Governor 3 days (Sundays excepted) in session, else law without signature; 20 days after adjournment
  for bills passed in its last 3 days, then a pocket veto (`govDeadline()`); override two-thirds. The governor's phone,
  address and contact page are from governor.state.nm.us/contact-the-governor/ (checked by program 2026-11-13, not by the
  owner). Places (`towns.py`): cities, towns, villages, Census-designated places and counties, separate Senate (42) and
  House (70) lists.
- **West Virginia (built 2026-11-13):** `python3 states/wv/fetch.py` reads the Legislature's bill status pages on
  www.wvlegislature.gov (no API; see its docstring) into data/wv/<year>/; `python3 states/wv/contacts.py` (every year; add
  it to states.json's run after fetch.py) builds the contacts; `states/wv/towns.py` was run once. A page a year
  (`YEARS = 1`): one 60-day regular session from the second Wednesday of January, or of February in a year a governor is
  inaugurated (2025, 2029; `opens()`, `sessionEnds()` = day 60 in profile.js, `STATE.dated` for each year's last day).
  Special sessions are left out. The lower house is the House of Delegates (`LOWER = "H"`, "Del."). Bills (HB, SB) and
  the joint resolutions (HJR, SJR), which are the constitutional amendments: tagged "const", two-thirds of each house's
  members, then the voters (`amendmentOnce`, `ballotEvenYears`), never the governor (2024 HJR 28 and 2026 SJR 9 passed;
  "Completed legislative action" decides). `states/wv/convert.py` reads each bill's history page (newest first: sorted by
  day, the page's order kept within a day): "To Health and Human Resources then Judiciary" (the plan) plus "To House Health
  and Human Resources" (the referral: the same committee twice); since 2025 the House's committees send bills to their
  subcommittees ("To House Courts", then back "To House Judiciary": `SUBCOMMITTEES`, shown as a step, not a referral);
  reports "Do pass" / "By substitute, do pass" / "Reported do pass" / "Committee substitute reported", "..., but first to
  Finance" (a second committee), "2nd reference dispensed"; "Reported in Com. Sub. for S. B. 50" folds the bill into
  another's substitute (`STATE.endedNote()`, with floor defeats "House rejected" and withdrawals); "Passed House (Roll No.
  93)", "Adopted by Senate"; "Senate requests House to concur" (it changed the bill, or the effective date), "House
  concurred in Senate amendment and passed bill", "... with amendment, passed bill" (changed again), conference reports.
  "Effective from passage (Roll No. 94)" is a separate two-thirds vote on the effective date, not the passage.
  "Completed legislative action" is passed both houses (the completed list agrees bill for bill). A bill both houses
  passed whose last step is one house asking the other to concur reads "In the House, to agree to the Senate's changes"
  (`passedIn` is the house that changed it). The governor's lines appear once per house, the journal copies ("... - House
  Journal") dated days off: the date written in the line decides and the copies are dropped. Laws and vetoes match the
  governor's lists (signed, became law without signature, vetoed) and the completed list bill for bill (`python3 -m
  states.wv.convert`): 2024 271 laws (2 without signature), 8 vetoes, line-item vetoes on SB 200 (the budget); 2025 243
  laws (10 without signature), 6 vetoes standing, line items on HB 2026; 2026 294 laws (10 without signature), 12 vetoes,
  line items on SB 250. Chapters run 1-N with none missing or repeated. SB 369 of 2025 was vetoed during the session,
  amended "to meet the objections of the Governor", passed again by both houses and signed (a law; no veto key date, so
  statistics don't count it as overridden). No veto was overridden in 2024-26; most vetoes come after the session ends,
  and stand. Crossover: the 50th day is the last for a bill to pass its own house, except budget, supplementary
  appropriation and expiring-funds bills (`budget`; `STATE.originDeadline`, checked against 2024-26's votes). Members'
  votes: every passage and repassage roll call member by member from the PDFs' text (House: names under YEAS/NAYS/NOT
  VOTING/EXCUSED; Senate: a Y/N/A/E letter before each surname in capitals, "MR PRESIDENT" as `P.PRESIDENTS[year]`),
  found by house and roll number (votes/house/00093.txt, votes/senate/MM-DD-0019.txt); 2,929 of 2,930 found, every name list
  adding up to its tally. Names are tied to today's members within the house for the current Legislature (2025-26: 87% and
  95% of noes, absences and excusals tied; the rest are members who left, Kump, Pritt, Linville and Flanigan among them,
  who voted through the 2026 session and are off the roster); for 2024 only names that also vote in 2025 (66%), so a
  new member sharing a departed one's surname isn't credited with the old votes. Two current members sharing a surname
  that the rolls once wrote bare: `BARE` (Sen. M. Maynard, Del. B. Ward). A name's initial must match the member's (2024-25's
  "Clark, T" isn't today's only Clark, W.), and a seat two names in one roll call claim is left as names. Seats: "H:62"; "S:5a"/"S:5b" (17 Senate districts
  of two senators, lettered by surname). Sponsors are surnames ("Smith, D.", "Hanshaw (Mr. Speaker)"), tied to today's
  members the same way; others stay as surnames. "What it does" is the drafter's note in the bill's text ("The purpose of
  this bill is ..."), from the newest version that has one ("From the drafter's note in the committee substitute." / "in
  the bill." / "in the bill as introduced." when a later substitute dropped it), cut at a sentence after 3,000 characters
  (HB 4273 of 2024's runs to 45,000); 95-99% of bills have one. Titles are the short titles; the summary is the official
  title's "relating to" clause. Topics from committees (`COMMITTEE_TOPICS`) and the Legislature's subjects
  (`SUBJECT_TOPICS`). About a third of each year's bills authorize agencies' rules ("DEP rule relating to ...",
  "Authorizing ... to promulgate legislative rules"), many folded into one bill per department: kept, but never linked
  across years. Earlier years linked by the same short title and lead sponsor, or the same drafter's note word for word,
  one bill each year, never laws, budget or rule bills (checked 25 by hand: 23 the same bill, 2 the same proposal by
  another sponsor). Contacts: the rosters and member pages (party, district, Capitol office and phone, email, post,
  committees), committees with chairs and vice chairs (the Senate's Confirmations, Enrolled Bills and Interstate
  Cooperation left out); six delegates share three office phones in pairs. Leaders: Speaker Roger Hanshaw, Senate President
  Randy Smith (2024: Craig Blair); the House and half the Senate elected in November 2026 organize in January 2027.
  Governor Patrick Morrisey (R) since January 2025 (Jim Justice before): 5 days (Sundays excepted) in session, 15 days
  (Sundays excepted) after adjournment (the vetoes' dates fit); line-item vetoes and reductions on appropriations; override
  by a majority of each house's members (two-thirds for budget and supplementary appropriation bills). The governor's phone
  ((304) 558-2000, toll-free (888) 438-2731), address and contact form (wv.accessgov.com) are from governor.wv.gov's footer
  (checked by program 2026-11-13, not by the owner). Places (`towns.py`): cities, towns, villages, Census-designated places
  and counties, separate Senate (17) and House (100) lists.
- **Nebraska (built 2026-11-13):** `python3 states/ne/fetch.py` reads
  nebraskalegislature.gov's pages (see its docstring; Crawl-delay 3) into data/ne/<first year>/; `python3
  states/ne/contacts.py` (add it to states.json's run after fetch.py) builds the contacts; `states/ne/towns.py` was run once.
  A page per two-year Legislature (`YEARS = 2`; the 109th is 2025-26): a 90-day session in the odd year (to early June) and a
  60-day one in the even year (to mid-April), each from the first Wednesday after the first Monday of January; bills carry
  over, and every bill still pending on the second session's last day is indefinitely postponed (`P.LAST_DAY` and
  `STATE.dated` hold each session's last day: add each new one). **One house:** the shared code's houses are one letter,
  "L" (`P.LOWER`, bills "LB 7", seats "L:12", "Sen."), `STATE.houses = { L: "Legislature" }`; tracker.html's `UNI` (one
  entry in `STATE.houses`) leaves out stage 2 ("passed one house": never used), the pipeline row, the second chamber in
  progress filters, the odds chart's step (`L3`), the month row, persistence and person-stats rows, the house choices in
  "Who works on what/with whom", the committees' second column, and words "Passed both houses" as `STATE.passedBothText`
  ("Passed the Legislature", `PASSED_BOTH`). A passed bill carries `passedS` and `passedA` both (data_check's "both houses"
  test). **Nonpartisan:** no party anywhere (contacts' party is empty; `C.parties()` is {}); `STATE.nonpartisan` (`NOPARTY`)
  hides the party filter, the party statistics and keys; states/legislatures.json `"nonpartisan": true` makes balance.py
  count members as "N" with no majority ("Legislature: nonpartisan" and the note in the header) and front_page.py give a
  neutral ring (home.html `.dot.N`, legend "Nonpartisan"). The governor is partisan (Jim Pillen, R). `states/ne/convert.py`
  reads each bill's history (oldest first after reversing the page): referral; "Notice of hearing" (every bill is heard);
  "Placed on General File [with AM..]" = the committee advanced it; General File, Select File and Final Reading are the
  three floor rounds (`statusDesc` "On the floor (Select File)"); "Passed on Final Reading 47-0-2" the passage ("with
  Emergency Clause" needs 33); "Presented to Governor on ...", "Approved by Governor [with line-item veto] on ...", "Returned
  by Governor without approval" (veto), "Became law without Governor's signature", "Failed to become law notwithstanding the
  objections ..." (override failed; 30 votes). Governor's lines are listed days late: their own wording dates them. Numbered
  motions ("Hunt MO506 Bracket until ... filed", then "MO506 prevailed") are read by their filed description: bracket and
  indefinite postponement kill, recommit sends back, cloture (33 votes) ends a filibuster; amendments' filed/withdrawn lines
  are dropped, adopted/lost kept. "Indefinitely postponed" on the Legislature's last day is "Died when the Legislature
  adjourned"; earlier, in committee it's a committee kill, on the floor a floor kill, except that at the end of each first
  session the bills whose text already went into another are postponed in a batch (148 in 2023, 46 in 2025): their line
  says so. "Provisions/portions of LB80 amended into LB814 by AM915" is on both bills: the source gets "Its provisions were
  amended into LB 814 (it became law)" and `STATE.endedNote()` shows "Amended into LB 814"; the host gets one line listing
  them. Priority designations ("Ballard priority bill", committee, "Speaker priority bill", "Speaker Major Proposal") are
  history lines; `STATE.rowTags()` (a shared hook) tags the row "Priority bill". "X name added" lines are the co-sponsors.
  **A bills** ("LB 304A", the appropriation for LB 304) are shown, marked `shell` (left out of the statistics and
  legislators' numbers, tagged "A bill": `STATE.shellTag`, `shellTip`, `shellNote`). Constitutional amendments are "LR 19CA"
  resolutions: three-fifths (30) on Final Reading, then the voters ("Presented to Secretary of State"), tagged "const",
  stage 3 (`amendmentOnce`; 2025's LR 19CA, term limits). Votes: every vote file linked from a bill's own steps, member by
  member: General File and Select File advances, Final Reading, cloture on the bill, override (labelled by round in the
  vote's committee slot; `STATE.voteWhat` names it); amendments' votes left out; roll-call names are surnames ("Cavanaugh,
  J."; a trailing "*" dropped), tied to current senators only (`VOTE_NAME_FIX`: plain "Meyer" is Fred Meyer in 2023-24,
  Glen Meyer in 2025 until Fred Meyer came back in January 2026). Totals match the Clerk's final worksheets bill for bill
  (`python3 -m states.ne.convert`, `checks()`): 108th 250 laws (67 A bills; LB 20 and LB 20A without signature; LB 818
  line-item veto; LB 814, the budget, line-item veto partly overridden), 2 vetoes standing (LB 25, LB 307; the override of
  LB 307 failed 27-20); 109th 364 laws (44 A bills; LB 1237 and LB 1237A without signature), 7 vetoes (LB 287, 319, 839,
  878, 929, 1029, 1256; every override failed), LR 19CA to the voters. Topics from the referral committee
  (`COMMITTEE_TOPICS`) and title words. "What it does" (`states/ne/texts.py`, from PDFs fetch.py's `statements()` saves as text in
  data/ne/<year>/docs/) is the committee statement's "Summary of purpose" when the committee advanced the bill (about 40%
  of bills), with its "Explanation of amendments" as what the committee changed (or as the statement itself when the
  amendment replaced the bill); vote tables, testifier lists and the section-by-section part are dropped. Otherwise it's
  the introducer's statement of intent, labelled as such (kept: the owner's decision 2026-11-14; about 98% of bills have
  one or the other). Committee statements
  are re-read when the bill is placed on General File again; A bills have none. The first copy is about 2,700 PDFs (about
  3 hours at the crawl delay) and never marks the state incomplete; the summary line is the one-line title. Earlier Legislature linked by the same title (six words or more) and
  introducer, never laws or appropriations. Contacts: 49 senators with Capitol room, phone, email, photo; 14 standing
  committees and the Executive Board with chairs and vice chairs (meeting days shortened by `meets()`); Speaker John Arch
  (`LEADERS`; the 110th Legislature elects its own in January 2027). A past Legislature's contacts are current senators who
  introduced bills in it; former senators are names only. Places (`towns.py`): cities, villages, Census-designated places and
  counties with their districts, one list (New Jersey's shape: a district has one senator). The governor's contact page and
  phone ((402) 471-2244) are from governor.nebraska.gov (checked by program 2026-11-13, not by the owner); Pillen ran again
  in November 2026: if a new governor takes office in January 2027, add them to `GOVERNORS` and legislatures.json.
- **South Carolina (built 2026-11-13):** `python3 states/sc/fetch.py`
  reads scstatehouse.gov (server-built pages and roll-call PDFs; see its docstring) into data/sc/<first year>/; `python3
  states/sc/contacts.py` (every General Assembly; add it to states.json's run after fetch.py) builds the contacts;
  `states/sc/towns.py` was run once. A page per two-year General Assembly (`YEARS = 2`; the 126th is 2025-26): sessions from
  the second Tuesday of January to sine die, by law the second Thursday of May (`sineDie()`, `sessionEnds()`), with a sine
  die resolution bringing the houses back for vetoes, conference reports and the budget (June; August 2026). Bills carry
  over to the second year with the same numbers. General Bills and Joint Resolutions are shown (joint resolutions have the
  force of law and become Acts: most approve agencies' regulations), so laws match the Acts lists; concurrent resolutions
  and resolutions are left out, by the title (`kept()`: the bill search's kind called S 729 of 2025-26, "A CONCURRENT
  RESOLUTION ...", a General Bill). `states/sc/convert.py` reads the history (each line names its house except the
  governor's): "Referred to Committee on X" (a prefiled bill's referral repeats at introduction), "Committee report:
  Favorable [with amendment] X" (committees report favorably or not at all; no tallies, no "held"), "Polled out of
  committee X", "Recalled from Committee on X", "Introduced, read first time, placed on calendar without reference" /
  "placed on local & uncontested calendar"; local bills go to a county delegation ("Referred to Greenville Delegation",
  "Referred to delegation from Charleston"; narrow "place", topic "local", as are bills amending a local act that name their
  place: `P.narrow_kind()`). "Read second time" + "Roll call Yeas-105 Nays-0" is the main vote; "Read third time and sent to
  Senate" the passage; "Read third time and enrolled" (second house, unchanged) or "Concurred in Senate amendment and
  enrolled" / both houses' "Conference report (received and) adopted" / "Ordered enrolled for ratification" passed both
  houses; "Read third time and returned to House with amendments" needs the first house; "Second Reading Failed",
  "Rejected"; "Reconsidered vote whereby read third time" undoes a passage. "Ratified R 167" (both presiding officers
  sign) sends it to the governor: "Signed By Governor", "Vetoed by Governor", "Certain items vetoed by Governor" (the
  budget: a law, `itemVeto`), "Veto overridden [by originating body] Yeas-98 Nays-11" in each house (both needed: S 1166 of
  2023-24 only in the Senate, a veto that stands), "Veto sustained", "Veto tabled"; "Act No. 212" (`lawWord` "Act", numbered
  through the General Assembly). Totals (`python3 -m states.sc.convert`; laws match the Acts lists bill for bill, by the
  year of the law's last step): 2023 102 laws (incl. the ratifying act S 381), 4 vetoes (3 overridden; H 4413 stands),
  line items H 4300; 2024 147 laws + 1 amendment with an Act number (S 1126) = 148 Acts, 3 vetoes (H 4248 overridden; S 112
  and S 1166 stand), line items H 5100; 2025 94 laws, 3 vetoes (S 136 and S 623 overridden in 2026; H 3969 tabled, stands),
  line items H 4025; 2026 180 laws (incl. the ratifying act S 582), 6 vetoes (4 overridden; H 5164 and H 5182 stand), line
  items H 5126. No law without signature in 2023-26. Constitutional amendments are joint resolutions "PROPOSING AN
  AMENDMENT TO ... THE CONSTITUTION OF SOUTH CAROLINA" (`is_amendment()`): two-thirds of each house's members, ratified
  with "No signature required" and an Act number (never the governor; no `chapter`, stage 3), then the voters at the next
  general election (`amendmentOnce`, `ballotEvenYears`, `ballotLine()`); if they approve, the next General Assembly passes
  "AN ACT TO RATIFY AN AMENDMENT ..." (also without the governor), shown as a law ("Ratifying a constitutional amendment:
  ...", not tagged "const"). Only S 1126 of 2024 (voter qualifications) passed in 2023-26; S 582 of 2026 ratified it.
  Titles are the bill search's subject line ("Status Offenses"); the summary is the official title in sentence case
  (`sentence()`: counties, agencies and programs put back from `ALWAYS`); "What it does" is the title's "so as to ..."
  clauses as sentences (`purpose()`, "From the bill's official title."; none for budgets): the only plain summaries,
  the LSA's, cover Acts and aren't downloaded. Floor votes member by member: each history roll call whose motion (from the
  session's vote list) is the bill's own (second and third readings, concurrence, conference reports, overrides; not
  amendments or motions), matched to members by "Last, First" within the house (`roll_code()`); codes N, E (excused), B (not
  voting, abstain, present). No committee votes. Seats "S:12", "H:71" (separate maps, 46 and 124); a seat goes to the member
  last named on a roll call in it (`seats()`); members who left are "H?Cox". Two traps in the member lists: a past General
  Assembly's lists have no parties (taken from another session's list or the member's page; 31 former members of the 125th
  have neither), and every list gives a member's district in the office they hold now, so `DISTRICT_FIX` corrects six members
  of the 2023-24 House (Ott 93, Leber 116, Elliott 22, Tedder 109, Jermaine Johnson 70, RJ May 88) and Wes Climer (Senate
  15, listed "5": his U.S. House district; his page says "U.S. Representative"), each checked against the member's home
  county and the districts the list leaves empty. Contacts: members' pages (Columbia office and phone, home or business
  phones, the page's contact form: the Legislature publishes no emails, so `form` and never `email`), committees with chairs
  (today's only; past sessions have none). Leaders: Speaker G. Murrell Smith, Jr.; President of the Senate Thomas C.
  Alexander (a senator; since 2019 the Lieutenant Governor doesn't preside); the House elected in November 2026 organizes in
  December. Governor Henry McMaster (R, term-limited): the governor elected in November 2026 takes office in January 2027
  (add to `GOVERNORS` and legislatures.json). 5 days (Sundays excepted) after ratification; a bill not returned becomes
  law, and after an adjournment the governor has until the second day of the next meeting; item vetoes on appropriations;
  override two-thirds of the members present. The governor's contact form and address are from governor.sc.gov (read by
  program 2026-11-13); the phone, (803) 734-2100, isn't on that page and hasn't been checked by the owner. Earlier General
  Assemblies linked by the same subject line and prime sponsor, or the same title without section numbers, or a subject
  one bill has in each (519 of 2025-26's; 15 read over, all the same bill). Places (`towns.py`): cities, towns,
  Census-designated places and counties, separate Senate and House lists.
- **Kansas (built 2026-11-13):** `python3 states/ks/fetch.py` reads the
  Legislature's API (kslegislature.gov/api/v1; see its docstring) into data/ks/<first year>/; `python3 states/ks/contacts.py`
  (every run; add it to states.json's run after fetch.py) builds the contacts; `states/ks/towns.py` was run once. A page per
  biennium (`YEARS = 2`; "b2025_26"): each year's session opens the second Monday of January, runs to first adjournment in
  late March or early April, and comes back for the veto session in late April; `STATE.dated` holds each year's first
  adjournment, veto session and last day (from the roll calls' journal days; add each new year's), `STATE.days()` estimates
  a year not listed. House and Senate bills, plus the concurrent resolutions proposing constitutional amendments (long title
  "A PROPOSITION to amend ...": two-thirds of each house's members, then the voters; "Enrolled and presented to Secretary of
  State", never the governor; tagged "const", stage 3: HCR 5004 and SCR 1611 of 2025-26 passed; SCR 1611 named the August 4, 2026 primary:
  `STATE.ballotDates`). Other HCRs/SCRs (Article V
  convention applications, joint rules) and HRs/SRs are left out; their STATUS says "Approved by Governor" though they never
  go to the governor (trap: the status field). `states/ks/convert.py` reads each history line's wording (the action codes
  don't always mean one thing: fa_fabc_925 is "Adopted as amended by required 2/3 Majority", efa_fabc_925 "Substitute
  passed"), sorted by day (the date in the wording when it has one: "Enrolled and presented to Governor on Monday, March 30,
  2026" is entered days later; hearings by the hearing's day once it's past; "Died in Committee" by the journal day, the
  biennium's last). Steps: referral; "Withdrawn from X; Referred to Y" (the API often names Y twice: the referral decides),
  "Withdrawn from Calendar; Referred to ..." (back to committee), "Withdrawn from and referred to Committee of the Whole"
  (to the floor); "Committee Report recommending bill be passed [as amended | and placed on Consent Calendar] by" (no
  committee named: the one it's in) = reported; the Committee of the Whole's "Be passed" on General Orders is a voice
  recommendation, not the passage; "Final Action - Passed [as amended]" (a later day) or "Emergency Final Action - ..." (the
  same day, after "Motion to advance to Emergency Final Action adopted", which the Senate's lines give only as the code
  fa_fabc_912), or "Consent Calendar Passed", is the passage; "Final Action - Not passed" fails. The second house passing it
  "as amended" or as a substitute needs "Concurred with amendments [in conference]" or both houses' "Conference Committee
  Report was adopted" ("agree to disagree" / "not adopted" start over; "Motion to not adopt ... (Bill is killed)"). Lines
  carrying only their code: ccal_rcc_820/850, ccal_faccl_850 (days on the consent calendar), ref_rbc_236/237 and
  cow_jcow_292 (left out); "#ACTION_CODES_UNKNOWN#" (SB 28 of 2024, HB 2106, SB 125, SB 367 of 2025-26, House resolutions)
  has no wording at all and sits among the Committee of the Whole's or a line-item override's steps: left out. Empty lines
  (misc_bs_100) are motions, worded from their roll call's motion when one has one. Governor: "Approved by Governor",
  "... except line item veto of 35a, ..." (a law, `itemVeto`), "Will become law without Governor's signature", "Vetoed by
  Governor", "Motion to override veto prevailed" in each house (both needed), line items overridden one group at a time.
  Laws and vetoes match the API's governor's-actions list bill for bill (`python3 -m states.ks.convert`): 2023 98 laws, 17
  vetoes (8 overridden, 9 stand); 2024 111 laws, 21 vetoes (7 overridden, 14 stand); 2025 129 laws, 19 vetoes, 14 overridden, 5 stand (KHI's and Foulston's
  count); 2026 157 laws, 34 vetoes, 20 overridden, 14 stand. No chapter numbers in the data (laws show no chapter). Votes:
  every roll call on the bill itself (final action, consent calendar, concurrence, conference reports, overrides; not
  amendments, motions or appointments) from votes.json, tied to the bill whose history line has the same action code, house
  and second (several bills' final actions share a minute; trap: a roll call's own bill_no can be wrong or missing: two 2026 Senate line-item override votes on HB 2513
  say HB 2315, a bill never out of committee; HB 2551's House vote of March 14, 2024 has none), dated by that line's journal
  day (after-midnight votes belong to the day before). Members' votes by kpid from votes/<file>.json where downloaded (2025-26:
  317 of 1,342 on 2026-11-13; 2023-24 none yet), else tallies alone (shown as everyone voting yes, as in IL and MO). 2 of
  1,518 passages have no roll call in the list (SB 157 and SB 315 of 2025-26). Seats "S:12", "H:71" (separate maps, 40 and 125):
  the biennium's "Active" members, plus a member who left and voted whose seat stayed empty (Dan Goddard, H:7). Sponsors are
  "Senator Titus" / "Representative Carpenter" or committees (most bills): a surname two members share is resolved by the
  member's page's sponsored bills (current biennium only), else left as the surname (Ruiz, Miller, Smith, Williams in
  2023-24). "What it does" is the Legislative Research Department's supplemental note on the latest version
  (notes/<bill>.json): the Brief, then "Background: ...", headings joined to their paragraph, keywords and footnote dropped
  (2025-26: 552 bills; 2023-24 not downloaded yet). Trap: a conference report often replaces a bill's contents with other
  bills' (HB 2043 of 2025-26: an insurance bill as passed, a property tax law after conference), and the note describes the
  bill before it: after a conference report, a note sharing under a fifth of the final titles' words is dropped (41), the
  rest are labelled as describing the bill before the conference report (109). Titles are the short titles ("Senate Substitute for HB 2004 by Committee
  on ... - ." stripped); the summary is the long title without "AN ACT" and the "amending ... repealing" list. Topics from the
  committees that reported it and each house's last committee (`COMMITTEE_TOPICS`), and title, summary and the note's
  keywords (agency names like "Department of Health and Environment" taken out first). Earlier biennium linked by the same
  short title (six words or more) and first sponsor, never laws. Contacts: members' pages (Topeka office room and phone, home
  phone, email; Amyx and Woodard share the minority leaders' line), committees with chairs, vice chairs and meeting times;
  a past biennium's have emails only. Leaders: Speaker Daniel Hawkins, President Ty Masterson (`LEADERS`; the House elected
  in November 2026 organizes in January 2027). Governor Laura Kelly (D, since January 14, 2019), term-limited: a new governor
  takes office January 11, 2027: add them to `GOVERNORS` and legislatures.json. 10 calendar days, else law without signature
  (no pocket veto); line items on appropriations; override two-thirds of the members (27, 84). governor.ks.gov answers
  automated requests with 403: the phone (785) 296-3232 and address are from general knowledge, unchecked. Places
  (`towns.py`): cities, Census-designated places and counties, separate Senate and House lists.
- **Louisiana (built 2026-11-14):** `python3 states/la/fetch.py` reads
  legis.la.gov (no API; see its docstring) into data/la/<year>/; `python3 states/la/contacts.py` (every run; add it to
  states.json's run after fetch.py) builds the contacts; `states/la/towns.py` was run once (Census files; parishes). A page a
  year (`YEARS = 1`): a general session in even years (second Monday of March, 60 legislative days in 85 calendar days) and a
  fiscal session in odd years (second Monday of April, 45 in 60; five non-money bills per member), `session_kind()`
  "general"/"fiscal", labels "2026 general"; `opens()`/`sessionEnds()`/`vetoSession()` (40 days after) in profile.js compute
  them (no `dated`). HB and SB only; constitutional amendments are bills too (the site's ConstAmendments list, which also
  names three whose titles don't say so, HB 666/667 and SB 157 of 2024, or "Constitutional amendment" in the title): two-thirds
  of each house's members, then the voters at the election the bill names (`ballotLine()`), never the governor; they get Act
  numbers ("Becomes Act No. 406." after "presented to the Secretary of State"), kept as a step, no `chapter`, stage 3. Bills
  withdrawn before introduction are left out. `states/la/convert.py` reads each history line (newest first on the page; sorted
  by day, the page's order kept within a day): prefiling with a provisional referral (the introduction is the first-day
  referral), "Read by title, under the rules, referred to the Committee on X" / "Read second time by title and referred to";
  reports "Reported favorably (11-0)" (the House's carry tallies, kept as tally-only committee votes; the Senate's don't),
  "with amendments", "by substitute" (the old bill "Becomes HB 694": `endedNote()` "Replaced by HB 694"), "To be recommitted
  to" + "recommitted to the Committee on Appropriations" (a second committee); "Involuntarily deferred" (voted down, `commFate`
  "defeated"); the Legislative Bureau's review isn't a committee vote; "Recalled from Committee"/"Discharged" go to the floor.
  Passage: the House's "roll called on final passage, yeas 99, nays 0. Finally passed", the Senate's "passed by a vote of 39
  yeas and 0 nays"; "Failed to pass" (51-50 can lose: a majority of the members, 53/20, or two-thirds); "Reconsidered." undoes
  the house's last vote. "Received from the Senate with amendments" means the first house must concur ("Senate amendments
  concurred in" / "Amendments proposed by the House read and concurred in"), or both houses adopt a conference report;
  "Enrolled ..." is passed both houses. Governor: "Sent to the Governor", "Signed by the Governor [with one or more line-item
  vetoes]. Becomes Act No. 1.", "Becomes Act No. 300 without the Governor's signature.", "Vetoed by the Governor." or only
  "Veto message received and read" (trap: SB 89, SB 111, SB 181 of 2025 have no "Vetoed" line, and SB 89's status says
  "Reconsideration - Senate final passage"; the vetoed list decides). Totals match the bill statuses and the vetoed list
  (VetoBills.aspx) bill for bill (`python3 -m states.la.convert`): 2024 787 laws (37 without signature), 27 vetoes, line items
  HB 1, 2, 781, 782, 5 amendments; 2025 510 (56), 15 vetoes, line items HB 2, 460, 463, 6 amendments; 2026 962 (100), 6 vetoes,
  line items HB 1, 2, 312, 10 amendments. Act numbers run 1-792, 1-516, 1-972 with none missing or repeated (laws plus
  amendments). No override is recorded in 2024-26. Votes: floor votes member by member from votes/<doc>.json (YEAS, NAYS,
  ABSENT; matched by house, bill, day and tally; no co-author, amendment or motion votes), else the history's tally (on
  2026-11-14 only 2026's 360 vote PDFs were read: 300 of 2,625 floor votes name anyone). Committee votes member by member from
  2026's cvotes ("Favorably"/"Report with Amendments" with a recorded tally; "Without Objection" has none); "Defer Voluntary"
  adds "Deferred by the X Committee at the author's request" (`heldAction`, `commFate` "held", `heldLabel` "Deferred").
  Names: surnames, "Carter, R." where shared (matched to any given name's initial: "Johnson, T." is C. Travis Johnson),
  accents and suffixes aside ("Galle" is Gallé, Jr.; "Barthelemy" is Barthelemy II), "Mr. Speaker"/"Mr. President"
  (`SPEAKERS`, `PRESIDENTS`), within the house, never a member first elected after the session (members.json "elected");
  members who left are names (2026: Selders S14, Stagni H92, Wright H77, whose seats are vacant). Seats "S:12", "H:71"
  (separate maps, 39 and 105). Authors are tied to seats by their page link's district when the surname matches (Jason
  Hughes's and Julie Emerson's districts have new members), shown by their author name ("Tehmi Chassion"). "What it does" is
  the digest (docs/<doc>.txt): the résumé digest of the bill as passed, else the newest "Digest of HB1 ..." (House
  Legislative Services' for House bills), header and amendment summaries dropped, "Proposed law"/"New law" before "Present
  law"/"Prior law" background, page breaks mid-sentence rejoined, cut after 3,000 characters; on 2026-11-14 only 267 House
  digests of 2026 were downloaded (none for the Senate yet: check the label's "by ..." when they arrive). Titles: the part
  after the subject keyword ("COURTS: ..."), trailing notes (votes needed, fiscal notes, effective dates) dropped; the keyword
  is the summary line and gives topics (`KEYWORD_TOPICS`), with committees (`COMMITTEE_TOPICS`). Local and special bills (a
  "Public Notice" document, not retirement bills) are narrow "place"; APPROPRIATIONS/JUDGMENT bills "person". Earlier years
  linked by the same short title and primary author, never laws or budget bills. Contacts: members' pages (district office
  and phones, email, parishes, party), committees with chairs and vice chairs (ex officio members left out). Leaders: Senate
  President Cameron Henry (members' pages); the House's pages name no posts, so the Speaker, Phillip DeVillier, is the member
  ex officio on all 16 House committees (Mike Johnson, on 14, is presumably the Speaker Pro Tempore; not shown). Governor
  Jeff Landry (R, since January 8, 2024; John Bel Edwards before): 10 days in session, else 20 after delivery; item vetoes
  on appropriations; override two-thirds of each house's members (26, 70). The governor's contact page, Constituent Services
  phone and mail address are from gov.louisiana.gov/contact-the-governors-office (read by program 2026-11-14, not checked by
  the owner). Places (`towns.py`): cities, towns, villages, Census-designated places and parishes, separate Senate and House
  lists ("Albany town" is a real Louisiana town, not New York leaking in).
- **LegiScan states (2026-11-08): Tennessee, then Oklahoma, Maine, Rhode Island, Vermont.** Their legislatures' sites bar
  automated readers in robots.txt, so `legiscan.py` downloads LegiScan's data (CC BY 4.0; monthly query budget shared and
  counted on GitHub) into data/<st>/legiscan/<session_id>/. Converters read only those files, never the API.
  The budget (reworked 2026-11-13, before the January sessions): every run reads each running session's getMasterList
  (status and last action for every bill, kept as the bill's "ml" in meta.json; `bills()` in legiscan_convert.py adds
  that last action to an older saved copy's history, so stages stay current; checked by cutting every bill's history
  mid-way: all stages matched); getBill only within a daily allowance (`allowance()`: the month's remainder less a
  300 margin, a Sunday reserve and the master lists still to come, over the days left), status changes and major
  actions first, then new bills, then minor changes paced through the day; Sunday's dataset fills in the rest. In
  session: ~2,000 a month of master lists, the rest for full records, ending near 8,700 at most. A session that
  hasn't opened (`OPENS`, `begun()`) never marks a state incomplete. `python3 legiscan.py --dry-run [--today=DATE]
  tn ok me ri vt` prints what a run would request, without queries.
  `states/legiscan_convert.py` holds everything shared: `folders()` (regular sessions, keyed by first year), `people()`,
  `person_house()` (from the district "SD-028": LegiScan's `role` is sometimes stale), `load_session(Rules, session)` and
  `link_earlier()`. A state subclasses `Rules` and sets `data_dir`, `include()` (bill / amendment / None), `decode()` (each
  history line -> steps in the shared vocabulary in the module's `KINDS`: refer, report, subreport, held, commfail, floor,
  pass, fail, reconsider, concur, ccr, enrolled, sent, unsent, signed, nosign, veto, override, chapter, replaced ...),
  `committee_vote()`/`floor_vote()` (which roll calls are committee votes and which floor ones can be the bill's own),
  `group()` (companion bills as one record), `title()`/`summary()`/`what()`, `topics()`, `narrow()`, `seat()`,
  `earlier_key()`, `gates` (committees that schedule floor votes). Stages come from the steps, each house's location kept
  apart; "passed both houses" needs one version passed by both (unamended by the second, or agreed to), a conference
  report adopted by both, or enrollment; a reconsidered passage doesn't count. Floor roll calls are tied to a passage or
  concurrence step of the same day and house with a tally within 5 votes (the history's tally is the journal's; the roll
  call's own totals are kept), committee roll calls to a committee step that day: LegiScan attaches some roll calls to the
  wrong bill (TN SB 5 of 2025 carries another bill's House votes). LegiScan's `status` is only checked against
  (`python3 states/<st>/convert.py` prints `Rules.checks`): Tennessee's two vetoes of 2025-26 are "Enrolled" there. Each
  state's how.html credits LegiScan with links (the license requires it), and `textLinks` links each bill's LegiScan page.
  Contacts: Open States' current list says who holds each seat (party, email), LegiScan's person records give ids (the roll
  calls'), phones and offices. LegiScan has no committee members or chairs.
- **Tennessee (built 2026-11-08 from LegiScan):** `states/tn/convert.py`
  (the `Tennessee` rules), `contacts.py` (run after legiscan.py), `towns.py` (run once). Two-year General Assemblies (2025 is
  the 114th, 2025-26), sessions each year from the second Tuesday of January to late April (`STATE.dated`: add each year's
  last day). Only HB/SB under 6000 (extraordinary sessions' bills are 6001+, 7001+ in the same files) and the joint
  resolutions proposing amendments to the Tennessee Constitution (majority in one General Assembly, two-thirds in the next,
  then the voters at the next governor's election: `ballotYear()`); other resolutions left out. Every bill is filed in both
  houses with the same text; LegiScan's sasts "Crossfiled" (and, for joint resolutions, the same title) put the two numbers in
  one record, as NJ's and NY's identical bills are; when one passes, the other house substitutes it for its own ("Comp. SB
  subst." marks the number that gave way: `replaced`). House bills go through subcommittees ("Assigned to s/c ..."): the
  bill stays in the parent committee; subcommittee votes keep their names. Calendar and Rules (House) and Calendar (Senate)
  schedule floor votes (`gates`). Set aside (`heldAction`): "Taken off notice", "Assigned to General Subcommittee", "Deferred
  to Summer Study", "Lay on the Table" ("Placed behind the budget" is a wait, not counted). Laws: "Signed by Governor.",
  "Returned by Governor without signature." (law), "Pub. Ch. 78" and "Pr. Ch." (private acts, narrow "place"); a governor
  recalled by the Senate ("Governor returned.", SB 1758 of 2026) is `unsent`. Public chapters are numbered through the
  General Assembly with no gaps, so laws here match them exactly: 2023-24 1,069 public + 68 private = 1,137; 2025-26 1,142 +
  74 = 1,216; vetoes 0 and 2 (SB 455 of 2025, HB 1882 of 2026). "What it does" is the General Assembly's bill summary
  ("As introduced, ..." / "As enacted, ...", LegiScan's description); the title is its first clause. Governor 10 days,
  Sundays excepted, no pocket veto; override a majority of the members. Leaders: Speaker Cameron Sexton; Lt. Gov. and Senate
  Speaker Randy McNally, who didn't run in 2026 (change `LEADERS` when the 115th General Assembly elects a new one in January
  2027). Governor Bill Lee is term-limited: add the new governor (January 2027) to `GOVERNORS` and states/legislatures.json.
  The governor's contact page and phone haven't been checked by the owner. sos.tn.gov turns automated requests away.
- **Oklahoma (built 2026-11-08 from LegiScan):** `states/ok/convert.py` (the `Oklahoma` rules), `contacts.py` (run after
  legiscan.py), `towns.py` (run once: 672 places and counties). Two-year Legislatures (2025 is the 60th, 2025-26; `YEARS = 2`),
  sessions each year from the first Monday in February to the last Friday in May at the latest (`STATE.dated` holds each
  year's last day, 2026's was May 14: add each year's). Bills carry over to the second year with the same numbers, and
  LegiScan's even-year session holds the whole Legislature's bills, so `Rules.session_folders()` (a shared hook) reads the
  2026 folder as session 2025 and the 2024 folder as 2023 (the odd year's folder is a subset, used only until the even one
  exists). Only HB/SB, and HJR/SJR proposing amendments to the Oklahoma Constitution (titles opening "Constitutional
  amendment;", "Oklahoma Constitution;", "Constitution;"; a majority of each house's members, then the voters at the next
  general election or a special election: `amendmentOnce`, `ballotLine()`); the joint resolutions approving agencies' rules
  (which do go to the governor, about 10 a year) and applications to Congress are left out. History lines: since 2025 a
  House bill goes to an oversight committee and, within it, a policy committee ("Second Reading referred to Judiciary and
  Public Safety Oversight", "Referred to Civil Judiciary"); a referral followed directly by another, or one the bill was
  withdrawn from (most House bills of 2025-26 were parked in Rules first: "Withdrawn from Rules Committee"), is kept as
  written, so the first committee is the one that heard it. "Policy recommendation to the X committee; Do Pass Y" and
  "Recommendation to the full committee; Do Pass ... Subcommittee" are the policy committee's or subcommittee's report and
  send it to X / Appropriations and Budget; "CR; Do Pass X Committee" and the Senate's "Reported Do Pass ... X committee;
  CR filed" report it; "Failed in Committee - X" kills it. A house's second passing vote ("Fourth Reading, Measure passed",
  or the Senate's "Measure passed" after "HAs adopted"/"CCR adopted") is `concur`/`ccr`, so a second-house passage alone
  (marked amended) never makes "passed both houses": enrollment ("Referred for enrollment", "Enrolled, ...") or that
  agreement does. Undone: "Motion to reconsider adopted" and "Third Reading, advancement rescinded" only when the vote just
  before was the passage (not "Special Election failed" or the emergency clause); "Fourth Reading and signing rescinded"
  and "Recalled from enrollment" (HB 4248 of 2026). The decoder looks along each bill's history (`_at()`). Governor:
  "Approved by Governor", "Becomes law without Governor's signature", "Vetoed", "Pocket veto" (a veto: 15 days after sine
  die without a signature), "Veto overridden" in each house (two-thirds; three-fourths for bills with an emergency clause:
  legislatures.json `note`), "Line item vetoed" (the rest is law). No chapter numbers, summaries or committee members in
  the data; "What it does" isn't shown. Committee roll calls are dated the day before (or a weekend before) the history's
  report line, so `comm_vote_days = 4` (a shared option, default 0). 2023-24's Senate committee votes don't say
  "Committee" ("Senate: Judiciary: DO PASS"). Shell bills ("Schools; Education Reform Act of 2026; effective date."; about
  1,250-1,450 a Legislature) that never got past a committee are `shell` (`STATE.shellTip`/`shellNote` word them), and
  build_data.py's `similar_bills()` now leaves all states' shells out. Titles drop the stock "effective date; emergency;
  codification" items; topics from the title's first item (its subject: `SUBJECT_TOPICS`), committees and words. Earlier
  Legislatures linked by title without its subject. LegiScan's own status is wrong for pocket vetoes (shown as passed) and
  line-item vetoes (shown as vetoed). Totals by year of the governor's action (bills only): 2023 378 laws and 35 vetoes
  standing (55 vetoes, 5 of them pocket, 20 overridden); 2024 452 and 28 (33 vetoes, 5 overridden); 2025 494 and 27 (69 vetoes
  plus 5 pocket, 47 overridden; 148 signed, 299 without signature: matches KGOU's 147 + 1 line-item, 69, 47, 5 and 305
  counting the rules resolutions); 2026 447 and 36 (37 vetoes plus 3 pocket, 4 overridden; the Municipal League's 40 and 4
  match, KGOU's "vetoed 59" doesn't, and the data's sent bills add up without it). Leaders: Speaker Kyle Hilbert,
  President Pro Tempore Lonnie Paxton (the 61st Legislature elects new ones in January 2027: change `LEADERS`). Governor
  Kevin Stitt is term-limited: the new governor takes office January 11, 2027 (add to `GOVERNORS` and
  states/legislatures.json). The governor's contact page and phone haven't been checked by the owner.
- **Rhode Island (built 2026-11-08 from LegiScan):** `states/ri/convert.py` (the `RhodeIsland` rules), `contacts.py` (run
  after legiscan.py), `towns.py` (run once: the 39 cities and towns, Census county subdivisions). One session a year from the
  first Tuesday of January to June (`STATE.dated`: add each year's last floor day); bills don't carry over. Bills (H/S) and
  the joint resolutions proposing constitutional amendments (a majority of each house's members, then the voters at the
  next general election: `amendmentOnce`, `ballotEvenYears`); other resolutions left out, including joint resolutions with
  the force of law (grants, study commissions: 6-14 a year sent to the governor). Companions: most bills are filed in both
  houses with the same text and, unlike Tennessee's, both versions pass and both become separate public laws. LegiScan has
  no link between them (no sasts): a House and a Senate bill with exactly the same description, when no other bill shares
  it, are one record (`group()`), so laws here are records, about 60% of the official count of bills signed. History:
  "in concurrence" means agreeing to the version the other house passed (the second house passing it unchanged is a
  passage; the first house accepting the second's substitute is `concur`, shown "Agreed to the Senate's version"); a
  second house's passage without it changed the bill (an added line says so). "Committee recommended measure be held for
  further study" is `held` (`heldAction`, "Held for further study"): the usual end, though a held bill can come back;
  "indefinite postponement" is voted down. The text's house beats the line's chamber field (some are wrong). No Rules or
  Calendar committee (`gates` empty): the Speaker and the Senate President schedule. History lines have no tallies, so
  floor roll calls go to that day's passage in the bill they're filed under (`votes_by_version`, a shared-module option;
  when there are more roll calls than passages that day, the earlier ones were floor amendments, also labeled "Passage");
  Senate committees' votes to hold or postpone aren't shown (the page reads committee votes as approvals). Laws have no
  numbers in the data ("Public Law 2025-123" isn't in LegiScan). Totals by bill number, matching LegiScan's statuses and the
  news (Rhode Island Current: 513 bills sent in 2025, two pairs vetoed; five pairs in 2024; one pair in 2026): sent to the
  governor 509 / 507 / 480 bills (2024/25/26), laws 499 / 503 / 478 (signed 398/382/349, without signature
  101/121/129), vetoed 10 / 4 / 2; as records 307 / 318 / 280 laws and 5 / 2 / 1 vetoes. Governor 6 days, Sundays excepted
  (the data's "Effective without Governor's signature" lines come 7 non-Sunday days after transmittal); 10 days after an
  adjournment, but the General Assembly recesses in June. Override three-fifths of the members present in each house.
  Local acts (bonds, charters, fire districts) are narrow "place" (`place_act()`), marriage-solemnization bills "person".
  Leaders: Speaker Chris Blazejewski (since May 7, 2026, after Joe Shekarchi stepped down) and Senate President Val Lawson
  (check both when the General Assembly elected in November 2026 meets in January 2027). Governor Dan McKee; add a new
  governor (January 2027) to `GOVERNORS` and states/legislatures.json. The governor's contact page and phone (401-222-2080)
  haven't been checked by the owner. rilegislature.gov bars automated readers: never fetch it.
- **Vermont (built 2026-11-08 from LegiScan):** `states/vt/convert.py` (the `Vermont` rules), `contacts.py` (run after
  legiscan.py), `towns.py` (run once). A page is a biennium (`YEARS = 2`; 2025-26 is one): bills are numbered once for it,
  live through both years' sessions (January to May or June) and die at its end, and Acts are numbered through it. Only H.
  and S. bills; resolutions left out. Constitutional amendments are Senate "Proposals", which LegiScan doesn't carry: none
  shown. The history is the two journals' wording, each line with its house; the other house's echoes ("Senate Message:
  ...", "House message: ...") change nothing. "Notice Calendar: Favorable ..." (House) and "Favorable report ... by
  Committee on X" (Senate) are a committee's report; "Pending entry on Notice Calendar, referred to Committee on X" a report
  and a second referral (House Rule 35(a), Senate Rule 31: Appropriations, Ways and Means, Finance). Committees never vote
  bills down. "Third Reading ordered" is the second-reading vote (step "second", added to the shared vocabulary: it changes
  nothing, but a roll call can be tied to it, `vote_kinds`); "Read third time and passed" the passage; the second house
  "passed in concurrence" (unchanged) or "... with proposal of amendment" (changed), then the first house "concurred in"
  it (not "with further amendment", which sends it back), or both adopt a Committee of Conference report. Roll calls: the
  Senate writes the tally on the question's line; the House on its own line, "Roll Call Results ..." before the line that
  says what passed or "Which was agreed to on a Roll Call ..." after it, so `classify()` reads a bill's lines together
  (the shared module's `decode_line()` hook, with the line's index) and puts each tally on its question; LegiScan's roll
  call's description is sometimes the other of the two lines (H.141 of 2025-26), so votes are matched by result and tally
  (`vote_key()`). Most votes are voice votes: about 60 roll calls a biennium are the bill's own. The governor's lines are
  filed under the journal day the house heard of them, often weeks off: their own wording dates them ("Signed by
  Governor on June 13, 2024"; the shared module's `extra["date"]`), with year slips fixed ("Vetoed ... May 23, 2023" filed
  in 2024, H.289). The Act number isn't in the history: it's the "As Enacted" text's name ("ACT044", municipal acts
  "ACTM003", shown "Act M-3", narrow "place"), added as the last step, and decides: H.890 of 2023-24 (Act 185) has a
  history ending with the Senate sustaining a veto, while the Legislature's status page says the governor approved it June
  28, 2024. Acts 1-N with no gaps; laws match them exactly: 2023-24 185 + 28 municipal = 213 (97 signed in 2023, 116 in
  2024); 2025-26 179 + 12 = 191 (78 and 113). Vetoes, matching the news: 2023 8 (6 overridden: S.5, H.217, H.494, H.509,
  H.386, H.305), 2024 10 (6 overridden June 17, plus H.890), 2025 5 (H.91, H.141, H.219, H.489, S.125), 2026 8 (H.674,
  H.710, H.727, H.817, S.183, S.190, S.218, S.230); none overridden since Democrats lost their supermajority in 2024. No
  summaries ("What it does" isn't shown): LegiScan's description is the official title. Seats: districts have names,
  numbered alphabetically in data/vt/district_names.json (towns.py, from the Census relationship files): Senate 1-16
  ("Chittenden Central" is 4), House 1-109; members "S:4a", "S:4b", "S:4c", "H:37a", "H:37b" in the order of their last names
  (New Jersey's scheme, both houses). "Where you live" lists the 255 towns and cities (Census county subdivisions; Essex
  Junction, a city since 2022, is still inside Essex there), split towns by land share. The address lookup is off (the
  Census geocoder gives district names, not numbers). Open States gives Progressives' party as "Democratic/Progressive"
  (counted with the Democrats) and three independents. Most members' phone is the State House's message line (shown as
  such). Governor 5 days, Sundays excepted; a pocket veto only if the General Assembly adjourns within three days of
  delivery; override two-thirds of members present. Each year's opening and last day are in `STATE.opened`/`dated` (add
  each year's). Leaders: Speaker Jill Krowinski, President pro tempore Philip Baruth (the new General Assembly chooses in
  January 2027). If the governor elected in November 2026 isn't Phil Scott, add them to `GOVERNORS` and legislatures.json.
  The governor's phone and contact page haven't been checked by the owner.
- **Maine (built 2026-11-08 from LegiScan):** `states/me/convert.py` (the `Maine` rules), `contacts.py` (run after
  legiscan.py), `towns.py` (run once). A page is a two-year Legislature (the 132nd is 2025-26; `YEARS = 2`): LD numbers
  and carried-over bills run through both sessions (long first, short second, so every page has one of each and needs no
  `session_kind()`). Only LDs are shown (bills, resolves, and "RESOLUTION, Proposing an Amendment to the Constitution of
  Maine", tagged "const": two-thirds of each house once, then the voters, `amendmentOnce`); LegiScan's HP/SP records
  (joint orders) are left out. The page reads a bill's house from its number, so records are the LD with the paper's house
  in front: "HLD1328" is LD 1328, a House paper (`Rules.number()`, a hook added to legiscan_convert.py for this; the summary
  says "LD 1328 (House Paper 870)", and searching "LD 1328" finds it). History lines are read together
  (`decode_line()` over `decode_bill()`): committees are joint (the referral is the origin house's; "...in concurrence" isn't
  a second one); the committee's own "J" lines ("Reported Out: OTP-AM", "ONTP", "LTW", "OTP-AM/ONTP" divided, majority
  first) go to the house that referred it; LTW is `heldAction` ("Withdrawn"). A house passes a bill when it first passes it
  "to be engrossed" (later "RECEDED and CONCURRED"/"INSISTED" lines only settle the text), and again when it enacts it
  ("PASSED TO BE ENACTED", "FINALLY PASSED", "RECEDED and CONCURRED to PASSAGE TO BE ENACTED"); every pass is marked amended,
  so "passed both houses" comes only from both houses' enactments standing ("enrolled"; undone by a reconsideration, a failed
  enactment or "RECALLED From Governor's Desk"). Bills that cost money mostly die on the Senate's Special Appropriations
  Table after the House enacts them (stage 2; `passedIn` is the house that passed it last). The history never records the
  governor's signature, the presentment or the chapter number: a bill enacted by both houses is a law when LegiScan holds
  its "Chaptered" text or its status is "Passed" (36 bills enacted on 2024's veto day have no chaptered text in LegiScan's
  2023-24 copy), dated the day of final enactment (`STATE.lawWord` "Chapter", no number). Vetoes: "having been returned by
  the Governor, together with objections" (the reconsideration day), "...become a law notwithstanding" an override; "HELD BY
  THE GOVERNOR" is `sent` (bills enacted at a session's end that the governor holds until the Legislature returns; still
  held, unchaptered, when the Legislature ends: a pocket veto). Votes: each roll call has its own history line ("ROLL CALL
  NO. 424 (Yeas 75 - Nays 65 ...)", "Roll Call Ordered Roll Call Number 457 Yeas 19 - Nays 14", "ROLL CALL NO. 828V 72
  having voted in the affirmative ..."), a step of kind "rollcall" (`vote_kinds`) with that tally; members' votes count only
  on the bill's own questions (`floor_vote()`: accepting an Ought to Pass report, engrossment, enactment, final passage,
  "Reconsideration-veto"), never accepting an Ought Not to Pass report, indefinite postponement, amendments or "Recede And
  Concur" (either house's position). Committee names come from the uppercase referrals, completed from `KNOWN` when cut at a
  comma. No summaries ("What it does" isn't shown); no committee votes, members or chairs. Totals (LegiScan's statuses
  agree; official totals weren't read: legislature.maine.gov's robots.txt bars automated readers): 2023-24, 927 laws (635 in
  2023, 292 in 2024) and 12 vetoes (4 and 8); 2025-26, 971 laws (680 and 291) and 8 vetoes (5 and 3: news reports count 5 in
  June 2025, LD 1228 among the 61 held bills in January 2026, and LD 307 and LD 1911 sustained on April 29, 2026); HLD949 of
  2023-24 is "Passed" in LegiScan but was carried over to a special session that never met (not a law here). Seats "S:12",
  "H:75" (separate Senate 35 and House 151 districts); the two tribal representatives (Passamaquoddy, Houlton Band of
  Maliseet; the Penobscot seat is empty) have no district and no floor vote, so they aren't seats (their bills show their
  names). Senators' phones are often their caucus office's line (labelled so). "Where you live" lists cities, towns,
  plantations, unorganized territories and counties (Census county-subdivision files). Leaders: President Mattie Daughtry,
  Speaker Ryan Fecteau (the 133rd Legislature convenes December 2, 2026 and elects new ones: change `LEADERS`). Governor
  Janet Mills is term-limited: add the new governor (January 2027) to `GOVERNORS` and states/legislatures.json. Each session's
  last day is `STATE.dated`, the veto day `STATE.vetoDays` (add each year's). The governor's contact page and phone haven't
  been checked by the owner.
- **Fewer yearly chores (2026-10-29):** Virginia's session dates are computed (`opens()`, `sessionEnds()`, `crossover()` in
  states/va/profile.js: 60 or 46 days from the second Wednesday of January; crossover the 35th or 28th day), with
  `dated` for a year that differs. Crossover is each bill's deadline until it passes its own house
  (`STATE.originDeadline`), and after it the bill can't pass that year. Virginia's floor leaders and members' first
  years come from the houses' sites (contacts.py). `check_site.py` runs last in publish.yml (daily) and fails the run (GitHub
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
- **Shared conventions (2026-11-01), so states can be compared later** (a "Compare states" page waits until most
  states are built). Every state follows these; `test/data_check.py` fails when one doesn't:
  - The same 14 topics with the same names (`TOPICS` in data_check.py): ag, biz, const, edu, env, gov, health, housing,
    human, labor, local, safety, tax, transp. A state maps its own committees, subjects or keywords onto them.
  - "What it does" names its source as a sentence: "From the Legislative Reference Bureau's synopsis."
  - Bills only (each chamber's bill type), plus constitutional amendments tagged "const"; other resolutions left out.
  - What skews comparisons is marked on the record: narrow bills (`narrow`: "place" for local bills for one city or
    county, as in GA and NC; "person", "org", "naming"), placeholder bills (`shell`, IL), and the session length
    (`YEARS`, `session_kind()` for states alternating long and short sessions).
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
    district isn't in any place's list in "Where you live". And NH Members.txt's electedStatus "Former" is on 18 members
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
  settings changed (`state_hash.py`, which includes the date, so each state is rebuilt at least daily) and copies the rest
  from the last build (the `built/` folder, kept in its cache; `ONLY="wy sd" ./build_site.sh` builds a few states locally); the data checks run in its 10:50 UTC run or with `-f checks=true`. A new state needs an
  entry in states.json and a restore step in publish.yml (check_site.py fails if one is missing); it needs the
  secrets CLOUDFLARE_API_TOKEN and CLOUDFLARE_ACCOUNT_ID. The domain stays parked at Porkbun until launch.
  Until then the site is at https://statebilltracker.pages.dev/ (first put up 2026-10-29, built with
  `SITE_BASE=https://statebilltracker.pages.dev/` (each state's SITE_URL is SITE_BASE/<state>/); unlisted, and marked noindex). It's a classic Pages project
  (created with `--force`, which isn't needed again). Deploy by hand from an empty folder, never from
  lists_worker/ or cron_worker/ (wrangler picks up that folder's wrangler.toml):
  `npx -y wrangler@4.152.0 pages deploy <repo>/_site --project-name=statebilltracker --branch=main --commit-dirty=true`.
- **Launch checklist for statebilltracker.org** (do these together when the owner says to launch):
  1. `.github/workflows/publish.yml` and `download.yml`: run more often while legislatures meet (e.g. hourly on weekdays),
     minding Cloudflare Pages' monthly deployment limit (500 on the free plan; skip deploys when nothing changed, or pay).
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
  push trigger. It has no GitHub Pages site.
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

- **Constitutional amendments (2026-10-31):** shown in every state where the data has them, tagged "const": as bills (PA, MD),
  concurrent resolutions (NY), or joint resolutions the converters now include (OH, WA, IL, GA, MI, WI; CA, OR, AZ, TX, CT,
  NJ, MA, VA in progress). Each state's profile.js says how they pass (`amendments`, `amendmentOnce`, `amendmentVote`,
  `amendmentFinal()`, `amendmentAgain()`) and when the voters decide (`ballotEvenYears`, `ballotYear()`, `ballotLine()`
  when the resolution names the election: OH, WI). They never reach the governor's stages, even where the state logs the
  governor receiving them (GA numbers them as Acts).
