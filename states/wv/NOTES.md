# West Virginia

Moved from CLAUDE.md (2026-11-19). Shared conventions, the data traps list and the site's code notes stay there.

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
