# Missouri

Moved from CLAUDE.md (2026-11-19). Shared conventions, the data traps list and the site's code notes stay there.

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
