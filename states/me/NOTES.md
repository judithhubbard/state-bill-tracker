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
