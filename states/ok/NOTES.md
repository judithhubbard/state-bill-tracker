# Oklahoma

Moved from CLAUDE.md (2026-11-19). Shared conventions, the data traps list and the site's code notes stay there.
This state's data comes from LegiScan: the shared design (legiscan.py, the budget, states/legiscan_convert.py) is in states/LEGISCAN.md.

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
- **Committee agendas (2026-11-22):** from each bill's LegiScan `calendar` (its hearings: date, time, room, description), read with the bill (no queries of their own): `agendas()` calls legiscan_convert.agendas() (states/LEGISCAN.md). Today's and later meetings only. LegiScan's calendar has no cancellations; an entry dropped from a notice goes when the bill is next read, which within the daily getBill allowance can be hours after the change. Revised agendas ("2ND REVISED") keep only the latest revision for that committee and day. Tested against 2026's saved calendars (886 bills, all matched). January check: House and Senate entries both appear.
- **Veto messages (2026-11-22):** LegiScan has none. `states/ok/vetoes.py` (run last in the legiscan job) reads the
  governor's yearly veto page on oklahoma.gov (robots.txt "Allow: /"), weekly through the next year, into
  data/ok/vetoes_<year>.html: each veto under a "House Bill 3660 Veto Message" heading with a paragraph of his reasons
  (the headings' links to the Secretary of State's letters lead to that office's home page now). `veto_reasons()` in
  convert.py reads it; legiscan_convert.py's `Rules.veto_memo()` is the hook (None for the other LegiScan states). Only
  2026's page is in `PAGES`: 2025's (gov--stitt-s-2025-veto-list.html) is laid out differently and 2023-24's weren't
  found; add each year's page by hand. 33 of 2026's vetoes matched on 2026-11-22. Shows after the next legiscan run.
- **Staff summaries (2026-11-22, approved by the owner: laws, and vetoed bills too):** "What it does" for each law and
  vetoed bill is the House or Senate staff's bill summary of its latest whole version (conference report, the Senate's
  "House Amendment to Senate Bill" analysis, engrossed, committee substitute, introduced, in that order of preference by
  date; amendment-only summaries and fiscal impact statements left out). They're PDFs on oklegislature.gov's /cf_pdf/,
  which robots.txt bars: never read there. LegiScan keeps copies as each bill's supplements ("Fiscal Note/Analysis",
  "House: Engrossed"), one getSupplement query each: legiscan.py's `read_supplements()` reads them after the bills, only
  when no status change, major action or new bill waits, at most 60 a day (and a third of the day's allowance, counted in
  it); states/ok/summaries.py picks them, reads the analysis with pdftotext and keeps each for good in
  data/ok/summaries.json. About 1,900 documents (2025-26: 1,003 laws and vetoes; 2023-24: 892), so about a month at 60 a
  day, newest Legislature first, plus a retry for each summary whose analysis is "Pending" (then the bill's next one).
  Label: "From the Oklahoma House (or Senate) staff's bill summary, via LegiScan." Traps: HB 2110 of 2025 carries SB
  2110's summary (dated ten months after the law; a document dated over 60 days after the governor acted, or whose
  "Bill No.:" names another bill, isn't used); HB 2236 of 2023's conference summary says only "Pending". Two laws have
  only a floor amendment's summary (SB 1196 of 2024, HB 2513 of 2025) and get none. `python3 states/ok/summaries.py`
  prints the coverage.
- **Photos (2026-11-22):** the House's own from its roster page (www.okhouse.gov/representatives, no robots.txt): the
  page data lists every member's district and portrait; the 400x500 "small" size is used (about 35 KB). The Senate's site
  (oksenate.gov) answers its pages with a script challenge (Sucuri), so its roster isn't read; Open States' links to its
  photo files (/sites/default/files/, allowed) still load and are copied small.
- **Prefiled bills (2026-11-23).** LegiScan gives each prefiled bill its "First Reading" and "Authored by" lines on the day
  the session opens (HB 1001 of 2027, filed November 4, 2026: "2027-02-01 First Reading"). The shared reader
  (legiscan_convert.py's `bills()`) leaves out lines dated after today; until then the bill has no history and settle()
  dates it by its file. And 2027's LegiScan people came with phones for 7 of 146 members: contacts.py keeps the last
  contacts file's id, phone and office for a member in the same seat (as Tennessee's): 143 of 146.
