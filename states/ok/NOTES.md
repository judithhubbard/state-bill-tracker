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
