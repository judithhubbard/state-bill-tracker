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
  official title without "A bill for an act" and the stock "and including effective date ... provisions" (kept in the
  summary). Topics from committees (`COMMITTEE_TOPICS`) and title words. Earlier General Assembly linked by the same
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
