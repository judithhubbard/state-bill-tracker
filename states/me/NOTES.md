# Maine

Moved from CLAUDE.md (2026-11-19). Shared conventions, the data traps list and the site's code notes stay there.
This state's data comes from LegiScan: the shared design (legiscan.py, the budget, states/legiscan_convert.py) is in states/LEGISCAN.md.

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
  Table after the House enacts them (stage 2; `passedIn` is the house that passed it last). LegiScan's history never records
  the governor's signature, the presentment or the chapter number: a bill enacted by both houses is a law when LegiScan
  holds its "Chaptered" text or its status is "Passed" (36 bills enacted on 2024's veto day have no chaptered text in
  LegiScan's 2023-24 copy). **Signing dates and chapters (2026-11-19, found by the pre-launch accuracy check: LD 2116 of
  2025-26 showed 4/13/26 and no chapter; its page says signed April 15, 2026, Public Law chapter 699):** `laws.py` reads
  each law's bill page (display_ps.asp?LD=2116&snum=132, which robots.txt allows; it bars only the search pages and
  LawMakerWeb), 1.5 s apart, only laws whose page hasn't given both facts (a page missing one is read again once a day), at
  most 8 minutes a run in the LegiScan job, into data/me/laws.json. Its "Final Disposition" box: "Governor's Action:
  Signed, Apr 15, 2026" ("Emergency Signed"; "Veto" on vetoed bills, whose history the converter already reads), and
  "Chaptered Law": ACTPUB (Public Law), ACTPS (Private and Special Law), RESLV (Resolve), "Chapter 699", each series numbered
  from 1 through a Legislature. `decode_bill()` adds "Signed by the governor" on that day and "Public Law, chapter 699";
  only a Public Law's number is the record's chapter (the page shows "Chapter N" with no series, and a resolve's chapter 10
  isn't Public Law chapter 10). A law not read yet keeps the old line, dated the final enactment. The first copy (1,899
  laws of 2023-26) was read locally on 2026-11-19 (the site slowed to half a minute a page for a while, so `laws.py` waits
  as long as a slow answer took and stops a run after ten slow answers or three errors); on GitHub it fills in over several
  runs. **The pages corrected 2023-24's totals:** 32 of the 36 veto-day bills LegiScan calls "Passed" (LD 1152, 1177, 444
  ...) were "Held by Governor, May 22, 2024" and "Died Upon Conclusion of the 131st, Dec 4, 2024", pocket vetoes, not laws
  (`died` in `decode_bill()`: a hold and a veto, the veto dated the Legislature's end); 3 (LD 25, 2205, 2210) have pages
  with no governor's action and no chapter; the Law and Legislative Reference Library's legislative histories
  (lldc.mainelegislature.org/Open/Meta/LegHist/131/lh131-LD-0025.pdf) say "Enacted, Held by Governor 05/22/24", so they're
  pocket vetoes too (`HELD_FIX` in convert.py, 2026-11-21). Any other bill like them still shows "No governor's action or
  chapter is recorded on the Legislature's page" (`silent`). LD 2015 of 2023 (Resolve chapter 86, "Emergency Finally Passed") has a
  chapter and no governor's action: a law dated its final passage. LD 1610 of 2023 (the Pine Tree Power initiative, "IB,
  Chapter 2", veto sustained) no longer carries a "Became law" line. Vetoes: "having been returned by
  the Governor, together with objections" (the reconsideration day), "...become a law notwithstanding" an override; "HELD BY
  THE GOVERNOR" is `sent` (bills enacted at a session's end that the governor holds until the Legislature returns; still
  held, unchaptered, when the Legislature ends: a pocket veto). Votes: each roll call has its own history line ("ROLL CALL
  NO. 424 (Yeas 75 - Nays 65 ...)", "Roll Call Ordered Roll Call Number 457 Yeas 19 - Nays 14", "ROLL CALL NO. 828V 72
  having voted in the affirmative ..."), a step of kind "rollcall" (`vote_kinds`) with that tally; members' votes count only
  on the bill's own questions (`floor_vote()`: accepting an Ought to Pass report, engrossment, enactment, final passage,
  "Reconsideration-veto"), never accepting an Ought Not to Pass report, indefinite postponement, amendments or "Recede And
  Concur" (either house's position). Committee names come from the uppercase referrals, completed from `KNOWN` when cut at a
  comma. No summaries ("What it does" isn't shown); no committee votes, members or chairs. Totals (each law's page read
  2026-11-19/20; official totals weren't read): 2023-24, 892 laws and 44 vetoes (4 in 2023, 8 in 2024, and the 32 pocket
  vetoes; LegiScan's statuses say 927 laws and 12 vetoes); 2025-26 (LegiScan's statuses agree), 971 laws (680 and 291) and 8 vetoes (5 and 3: news reports count 5 in
  June 2025, LD 1228 among the 61 held bills in January 2026, and LD 307 and LD 1911 sustained on April 29, 2026); HLD949 of
  2023-24 is "Passed" in LegiScan but was carried over to a special session that never met (not a law here). Seats "S:12",
  "H:75" (separate Senate 35 and House 151 districts); the two tribal representatives (Passamaquoddy, Houlton Band of
  Maliseet; the Penobscot seat is empty) have no district and no floor vote, so they aren't seats (their bills show their
  names). Senators' phones are often their caucus office's line (labelled so). "Where you live" lists cities, towns,
  plantations, unorganized territories and counties (Census county-subdivision files). Leaders: President Mattie Daughtry,
  Speaker Ryan Fecteau (the 133rd Legislature convenes December 2, 2026 and elects new ones: change `LEADERS`). Governor
  Janet Mills is term-limited: add the new governor (January 2027) to `GOVERNORS` and states/legislatures.json. Each session's
  last day is `STATE.dated`, the veto day `STATE.vetoDays` (add each year's). Governor's deadline (`govDeadline()`, 2026-11-21): 10 days,
  Sundays excepted; a bill whose 10 days pass the first session's end is held until 3 days after the second session opens;
  one whose 10 days pass veto day has no deadline (it dies unless signed); the break before veto day doesn't hold bills
  (Opinion of the Justices, 2015 ME 107). The governor's contact page and phone haven't
  been checked by the owner.
- **Committee agendas (2026-11-22):** from each bill's LegiScan `calendar` (its hearings: date, time, room, description), read with the bill (no queries of their own): `agendas()` calls legiscan_convert.agendas() (states/LEGISCAN.md). Today's and later meetings only. LegiScan's calendar has no cancellations; an entry dropped from a notice goes when the bill is next read, which within the daily getBill allowance can be hours after the change. Maine's entries say only "Hearing": the committee is the one the bill was last referred to by that day (`Maine.hearing_committee()`: its history's referral lines, else LegiScan's referrals), named "Joint ...". Tested against 2026's saved calendars (128 bills, all matched). January check: work sessions appear too, not only public hearings.
- **Veto messages (looked into 2026-11-22; not read):** the governor's Veto Messages page (maine.gov/governor/mills/official_documents/veto_messages) lists the letters, but www.maine.gov answered 403 to the letters' PDFs (LD 958, LD 1228) for a plain bot User-Agent: dropped, not worked around.
- **Committee reports' signers (2026-11-22):** Maine's joint committees report unanimously (the report names no one, and
  the committees' rosters aren't in the data: left out) or in a divided report, whose signers the bill page's "Divided
  Reports" box lists (display_ps.asp?LD=307&snum=132, #sec9: "A - Ought To Pass As Amended", "Senator Mark Lawrence of
  York, Chair", ...; MAJ/MIN for two reports, A, B, C ... for more; "Referred" is a report sending it to another
  committee). robots.txt, re-read 2026-11-22: "User-agent: * / Disallow: /bills/default_ps.asp / Disallow:
  /legis/bills/default_ps.asp / Disallow: /bills/search_ps.asp / Disallow: /legis/bills/search_ps.asp / Disallow:
  /LawMakerWeb / Disallow: /legis/LawMakerWeb" (no crawl delay). `states/me/reports.py` (after laws.py in the LegiScan
  job, at most 6 minutes a run, 1.5 s apart, laws.py's slow-site rules) reads only bills whose latest LegiScan "Reported
  Out:" line has a slash ("OTP-AM/ONTP": 849 of 2025-26, 844 of 2023-24), each once for that report's day (again once a
  day for a month while the page shows no division yet), into data/me/reports.json; the first copy, about 1,700 pages, fills
  in over about ten runs. The page shows only the latest report's division ("Latest Committee Report: Feb 27, 2026; IFW,
  MAJ: ..."; LD 1343 of 2025-26 was divided in May 2025 and again in February 2026; LD 1745 of 2023-24's divided referral
  report is gone once the second committee reported unanimously), so signers are kept only when the page's latest report
  is LegiScan's divided one. `add_reports()` in convert.py adds each as a vote of kind "R" ([house, "R", committee, day,
  signed Ought to Pass (as amended), signed Ought Not to Pass, [[signer, "Ought to Pass as Amended (majority)"], ...]],
  wording with "(majority)", "(minority)" or "(report B)", since two reports can both be "Ought to Pass as Amended" with
  different amendments), shown in History as the committee's report and never counted as votes. The record's house is
  the one the report goes back to (the house that referred the bill, as the "Reported Out" step), so the line reads
  "House Judiciary Committee report"; each signer is matched within the house the page names (Senator / Representative)
  among LegiScan's people of the session: seats ("S:29|Carney") in the current session, "H|Name" in earlier ones. Traps:
  names written shorter than LegiScan's (the page's "Tiffany Roberts" is "Roberts-Lovell": the last word of the name and
  the first name); a last name two members of a house share (2023-24's Anne and Joseph Perry, Rebecca and Sawin Millett;
  2025-26's Boyer, White, Wood: told apart by first name, shown "A. Perry"); a tribal representative LegiScan's people
  lack (Brian Reynolds of the Houlton Band of Maliseet Indians, 2025-26: "H|Reynolds"). Tested on 31 pages (12 of
  2023-24, 19 of 2025-26; 374 signatures, all matched); data_check.py counts unmatched signers, signers named twice on one
  report, and reports dated a day the history has no line on.
