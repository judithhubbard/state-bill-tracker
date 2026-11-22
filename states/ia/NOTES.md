# Iowa

Moved from CLAUDE.md (2026-11-19). Shared conventions, the data traps list and the site's code notes stay there.

- **Iowa (built 2026-11-15; official pages, else Open States):** `states/ia/openstates.py` (and `openstates_bulk.py` for
  2023-24) makes the first copy of every bill from Open States, and `states/ia/fetch.py` reads legis.iowa.gov's history
  pages (a request every 6 seconds; on GitHub the site's bot check ends each run after about 45 requests, so the official
  record replaces Open States' a few hundred bills a week; never fetch the site from the owner's computer), the
  Disposition of Bills lists, members, committees, roll-call PDFs and the LSA's explanations; `python3 states/ia/contacts.py`
  runs after it (states.json). A page per two-year General Assembly (`YEARS = 2`; 2025 is the 91st): bills carry over from
  the first year's session to the second's, numbers run on (the second year's from HF 2000/SF 2000); laws are chapters of
  each year's Iowa Acts, the second year's numbered from 1001 ("46 of 2025", "1056 of 2026"). `states/ia/convert.py`: a
  bill's history is its own page's section, else its section on a related bill's page (every page holds the histories of
  all related bills: study bill, earlier and later numbers, companion), else its Open States record; the same lines either
  way (the page's journal reference, "H.J. 167", names the house; Open States' organization, or "legislature" for
  subcommittee lines, which happen where the bill is). `python3 -m states.ia.convert compare 2025` converts both ways:
  169 (2025-26) and 284 (2023-24) bills with both, every stage the same. **Renumbering:** a committee reports a study bill
  (HSB/SSB, its own draft) or rewrites a member's bill by introducing it under a new number ("Committee report approving
  bill, renumbered as HF 581"), sometimes several times (HF 130, 581, 971, 2353, 2741); each chain is one record under its
  newest number (`nums` newest first, one `vers` per number with that number's own sponsor and history; the member who
  filed the first is the first sponsor for linking). Study bills never introduced aren't shown (drafts, not bills; about
  1,000 a General Assembly); a study bill's history joins its bill's record when read (2023-24 from Open States; 2025-26's
  only from pages, so most 2025-26 committee bills start "On the House calendar" with the committee as sponsor and its
  approval inferred). Companions stay separate records: "Substituted for HF 163." / "SF 583 substituted." then "Withdrawn."
  (`STATE.endedNote()`: "Replaced by SF 583"; also "Withdrawn" and floor defeats). The history: "Introduced, referred to X"
  (a member's bill), "Introduced, placed on [Appropriations | Ways and Means] calendar" (a committee's bill: on the floor),
  "Subcommittee: A, B and C" / "Subcommittee Meeting: 02/19/2025 8:30AM Room 217" (`agendas()` lists upcoming ones) /
  "Subcommittee recommends passage"; "Committee report, recommending [amendment and] passage" + "Committee vote: Yeas, 20.
  Nays, 0. Excused, 1." (tallies only); committees never vote bills down on the record (the funnel deadlines kill them
  silently); "Passed House, yeas 99, nays 0." the passage; "Read first time, passed on file" / "attached to SF 583" puts a
  received bill on the calendar with its companion; the second house's amendments come back ("Message from Senate, with
  amendment", "Senate amendment H-1354 filed"), the first house concurs and "Passed House" again (sometimes with no
  concurrence line: HF 1003 of 2025-26); "Reported correctly enrolled, signed by Speaker and President, and sent to
  Governor"; "Signed by Governor", "Item vetoed, signed by Governor" (`itemVeto`), "Vetoed by Governor"; joint resolutions
  "Sent to Secretary of State". Lines are in journal order: sorted by day, the source's order within a day. Chapters come from
  the page's "Acts Chapter 46" link (/iactc/91.1/CH0046.pdf: 91st General Assembly, first session) or Open States'
  documents (2023-24 only; the API records have none), so only about 56 of 2025-26's 370 laws have one until fetch.py reads
  the rest. Special sessions' bills are numbered with the regular ones (July 2023: HF 732; October 2026: HF 2801); a law signed
  more than 45 days after its year's sine die (`P.SESSION_ENDS`, kept with profile.js's `STATE.dated`) is "N of YYYY,
  Extraordinary Session" (Open States links HF 732 to the regular session's chapter 1). Joint resolutions proposing
  amendments to the Constitution of the State of Iowa are tagged "const" (others, state symbols, rule nullifications and
  Article V calls, are left out): a majority of each house's members in two General Assemblies in a row, then the voters;
  a second passage gets a history line ("Second passage: ...", read by `STATE.amendmentFinal`) when the General Assembly
  before passed the same resolution (SJR 11 of 2025-26 after HJR 2006 of 2023-24) or it's in `P.SECOND_PASSAGES` (HJR 3 and
  SJR 9 of 2023, first passed in 2021-22, on the November 2024 ballot). Votes: passages member by member from Open States'
  roll calls ("Shall the bill pass?") matched by house, day and tally (about half the passages), else tallies; 2025-26 voters
  carry their Open States person and district; 2023-24's bulk names are split ("Trone", "Garriott"; "Amos", "Jr."; "Dawson
  De Witt"): `rejoin()` and `split_names()` put them back, and a surname is tied to a current member of that house only
  when one has it (a member page read by fetch.py also has to list the 90th General Assembly); departed members stay names
  ("H?Abdul-Samad"). fetch.py's roll-call PDFs (votes/) and committee pages aren't read by the converter yet. "What it
  does": the LSA's explanation from texts/<bill>.json when fetch.py has read it (none yet on 2026-11-15). Titles: the
  official title without "A bill for an act" and the stock "and including effective date ... provisions" (no summary line:
  until 2026-11-22 the full official title was the summary, repeating the title with only that tail). Topics from committees (`COMMITTEE_TOPICS`) and title words. Earlier General Assembly linked by the same
  official title and first member sponsor, or the same title (eight words or more) held by one bill each; never laws or
  budget bills. Contacts (`contacts.py`): the saved House and Senate member lists (members.json once fetch.py writes it),
  emails; the Capitol phone is each house's switchboard ((515) 281-3221 House, (515) 281-3371 Senate), labelled so; no
  photos (served by legis.iowa.gov); committees only from data/ia/committees.json, which isn't downloaded yet (none shown
  until then). Leaders: Speaker Pat Grassley, Senate Majority Leader Mike Klimesh (since September 2025; Amy Sinclair is
  President); the 92nd General Assembly organizes in January 2027. Governor Kim Reynolds (R) didn't run in 2026; Rob Sand (D)
  takes office in January 2027 (the day wasn't announced on 2026-11-15): add him to `GOVERNORS` and legislatures.json. 3 days
  (Sundays excepted) in session; 30 days after adjournment for bills sent in its last 3 days, else a pocket veto; item vetoes
  on appropriations; override two-thirds of each house's members. The governor's phone ((515) 281-5211) and contact page
  are from search results (governor.iowa.gov answers automated requests with 403); not checked by the owner. Totals (by the
  year of the governor's action): 2023 167 laws (HF 732 of the July special session included) and 1 veto (SF 388), item veto
  SF 563, chapters 1-166 none missing; 2024 185 and 1 (HF 2539), chapters 1001-1185 none missing; 2025 169 and 2 (HF 383, HF
  639), item veto SF 647 (the news: 169 signed, 2 vetoed); 2026 201 (HF 2801 of October's special session included) and 5
  (HF 2667, SF 2207, SF 2299, SF 2320, SF 2453), item vetoes on HF 2782, HF 2783, HF 2800, SF 2484 (the news: 200 signed, 5
  vetoed, four budgets item-vetoed). Places (`towns.py`, run once): cities, Census-designated places and counties, separate
  Senate (50) and House (100) lists. data/ia/incomplete (committees not downloaded yet) keeps Iowa off the site until
  fetch.py removes it on GitHub.
- (2026-11-19) A record's `last` is the day of the latest line the history shows: "routine" lines (subcommittee
  assignments, committee tallies, amendments filed, sponsors added) are left out of the history, and dating by them left
  523 of 2025-26's status rows with a date and no wording (HF 29: 2026-04-20 "Subcommittee: Wulf, Gjerde and Meggers",
  now 2025-01-14 "REFERRED TO WAYS AND MEANS").
- A General Assembly of this year or later is shown from its first bill (`sessions()` in convert.py, 2026-11-22; older
  ones need more than 500), so the 92nd's prefiled bills show as they're read (about 43 a run); its disposition lists
  weren't up on 2026-11-22 ("92: not listed yet").
- **Texts before the backfill (2026-11-22):** the bot check ends each GitHub run after about 45 requests, and the
  histories' backfill took all of them, so fetch.py never reached the texts (the LSA's explanations, "What it does"). Now
  `main()` reads EARLY_TEXTS (8) texts of the current General Assembly each run right after the bills that moved and the
  members, before the backfill: laws and vetoes first (the list's last action), then the bills that moved most recently.
  About 380 laws and vetoes of 2025-26: a few days of runs. Not run from the owner's computer; shows as the runs read them.
- **Committee votes by member (2026-11-22):** from the House and Senate Journals' committee reports
  (www.legis.iowa.gov/docs/publications/HJNL/20260219_HJNL.pdf, SJNL for the Senate; robots.txt, re-read 2026-11-22, is
  "User-agent: * / Disallow: /chambers/ / Sitemap: ...", so /docs/ is allowed). Each report prints "Final Vote: Yeas, 18:
  Bousselot, ... Nays, 2: Knox and Schultz. Excused, none." (Senate, 2023-24 and 2025-26) or "Final Vote: Yeas, 17:
  Representatives Wulf-CH, ... Nays, 6: Cooling, ... Excused, 0." (House, since 2025 only: its 2023-24 journals print the
  recommendations without votes, so the House's 2023-24 committee votes have no names). fetch.py `journals()` reads each
  wanted day's journal once as text (journals/<H|S><YYYYMMDD>.txt): the days of the histories' committee reports, for the
  House also the two weekdays after (Commerce's recommendation of February 18, 2026 is in the 19th's journal) and the four
  before a committee bill's first line; about 500 for the 90th and 91st. EARLY_JOURNALS (6) requests a run go before the
  histories' backfill, the rest with the extras; a 404 (no session that day) is noted and not asked again. Never fetched
  from the owner's computer (the samples for writing it, 2026-11-22, came through a web fetch service). `states/ia/journals.py`
  parses them; convert.py's `committee_names()` ties each "Committee report" line to the journal's entry for one of the
  chain's numbers (or the study bill the Disposition of Bills lists as renumbered into it: "Committee Bill (Formerly House
  Study Bill 751)" is HF 2709), same house and committee, within three days, only when every group's names add up to its
  count and, where the history has a "Committee vote" tally (the House since 2025), the yeas and nays agree. The Senate's
  histories have no committee tallies, so its committee votes come only from the journals (a new kind "C" vote on the
  report line); a committee's own bill whose study bill isn't read gets its committee's vote dated the journal's
  recommendation day. Names are matched like floor votes' (surnames, "J. Taylor", "Trone Garriott"; senators who left
  stay names: "S?Boulton"); yeas are left out. On the four journals saved for testing (S 2025-03-06, S 2024-02-14,
  H 2026-02-19, H 2023-03-01; the last has no votes): all 95 "Final Vote" entries parsed, and 93 are on a bill's
  committee vote with names (Senate 33 of 33 in 2023-24, 26 of 26 in 2025-26; House 34 of 36: 16 named into the history's
  tallies, 18 committee bills from study bills, HSB 676's HF 2699 among them, referred on to Appropriations); the two left
  are HSB 753 (not yet listed as renumbered) and HJR 2004 (not a constitutional amendment, left out). Committee votes with
  names on that data: 2023-24 0 -> 33, 2025-26 0 -> 60 (of 598 committee votes, most still tallies only until fetch.py
  has read their journals). Not read: the
  committee minutes (legis.iowa.gov/committees/meetings/minutes?meetingID=..., PDFs in prose written differently by each
  secretary: "on a roll call vote of 14 ayes (Representatives ...), 6 nays (...)", "Short form vote was called. Nays:
  ...", "Ayes all"; the Senate's give no counts and say members excused "until they arrive"), which would be the only
  source for the House's 2023-24 committee votes.
