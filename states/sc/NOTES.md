# South Carolina

Moved from CLAUDE.md (2026-11-19). Shared conventions, the data traps list and the site's code notes stay there.

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
  clauses as sentences (`purpose()`, "From the bill's official title."; none for budgets), unless House Research's
  Legislative Update has a summary (below). Floor votes member by member: each history roll call whose motion (from the
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

- **Summaries from the Legislative Update (2026-11-22):** the House Research Staff's weekly Legislative Update, its
  issues on prefiled bills, bills the House passed and each year's Acts (www.scstatehouse.gov/reports/hupdate/session-126/
  <name>.htm, Word pages in Windows-1252, 1-7 MB; robots.txt bars only /images/, /jpeg/, /gif/, /dashboard/, /sys/) have a
  plain paragraph on each bill they cover. The Bill Summary Index (legislativeupdates.scstatehouse.gov/api/BillSummaryIndex/126,
  JSON, the public hupdate.php page's source; that host has no robots.txt) names each bill's issues and dates: 1,669 bills
  of 2025-26 in 35 issues on 2026-11-22. The 125th's index is empty, so 2023-24 has none. `states/sc/updates.py`, run by
  fetch.py for the two newest sessions: the index once a day, each issue once and again when the index dates it later than
  the copy (3 seconds apart), into data/sc/<year>/updates/; then each bill's summary (summaries.json): the Acts issue's
  first, else the latest issue's, passing over a short paragraph that only reports a step ("did not concur", "Conference
  Committee"). Parsing (`summaries_in()`): Word's paragraphs, inline tags dropped without a space (it splits words into
  spans), the contents and index left out; an entry is a heading ("H. 4641 No Kratom Sales To Minors ..." in Title Case,
  or the Acts issue's "Taxation of Watercraft (H. 3858, A. 109)") and its paragraphs to the next heading or section
  heading ("House Floor"); a paragraph Word split at a page break is joined; a weekly issue's opening step ("The House
  amended and adopted H. 3247.") is dropped. Two traps in the weekly issues: a heading placed before the end of the last
  bill's text (H. 4145's heading over a paragraph on H. 4755: when a later paragraph names the heading's bill, the ones
  before go back to the last entry), and a heading with a typo ("H. 5146" over "H. 5164"'s paragraph: an entry whose text
  never names its bill but opens naming another is dropped). Every summary kept opens naming its own bill or none (checked
  2026-11-22: 0 of 1,646). "From the House Research Staff's Legislative Update." 2025-26: 1,633 of 2,286 bills (71%, from
  0 plain summaries), 242 of 274 laws (the rest, mostly local bills, aren't in the index; the budget's H 5126 and H 5127
  open naming each other and are left out).
- **Committee agendas (2026-11-22):** `agendas()` in states/sc/fetch.py (the newest session, every run) reads each
  chamber's meeting schedule a week a request (/meetings?chamber=H&selecteddate=<Monday>, this week and the next three:
  8 requests), keeps the meetings from yesterday to three weeks ahead (not "CANCELED", not the floor sessions named
  "House"/"Senate"), takes the bills from each title's links ("Senate Judiciary Subcommittee on S.362 , S.631": the name
  without the "on ..." part), and for a committee meeting whose title names none reads its agenda PDF
  (/agendas/126h15874.pdf, Word-made; pdftotext: "H. 5043", "S. 655"), once per revision (agendas_read.json keeps what
  each named, by meeting id and revisions text). Only numbers in the session's bills.json count. A meeting on both
  chambers' schedules (the same id: Education Oversight, Judicial Merit Selection) keeps its own name; others are
  prefixed "House"/"Senate". Into data/sc/<first year>/agendas.json, `{"H3013": [["House Judiciary Domestic Relations,
  Business & Probate Laws Subcommittee", "2026-02-10T10:30:00"]]}`; `agendas()` in convert.py keeps today's and later.
  Meetings are posted about a week ahead ("Meeting added on ..." 4-10 days before). "Upon adjournment of the Senate" has
  no clock time (T00:00:00). robots.txt bars only /images/, /jpeg/, /gif/, /dashboard/, /sys/. Tested 2026-11-22 as if
  on February 10, 2026 (three days: 58 meetings, 28 agenda PDFs, 59 bills, all matching records). Needs pdftotext on the
  runner for the PDFs (without it, title links only). In session a first run may read 50-100 agenda PDFs (about a second
  each), later runs only changed ones.
- **The next session's bills (2026-11-22):** the bill search's session list offers the next General Assembly (127, 2027-28) once it has prefiled bills (not yet on 2026-11-22: session=127 answers "An error has occurred loading the bill results"); `sessions()` reads it daily. A session offered before it has a bill gets no folder (`read_bills()` writes no empty bills.json, and `main()` reads nothing else of it: agendas, members' pages and roll calls go to the newest session with bills), and one not convened (`begun()`) never holds South Carolina off the site.
- **Veto messages (2026-11-22, read by OCR, the owner's decision):** `veto_letters()` in fetch.py reads the governor's list,
  governor.sc.gov/executive-branch/veto-messages, once a day into veto_letters.json (a link's text names the year and the bill,
  "2024- S. 112 Fraudulent Check Expungement", which puts it in a General Assembly), and each letter once, 2 s apart, at most
  8 minutes a run, into <first year>/vetoes/<S112>.json (states/letters.py's `scanned()`: the PDFs are scans, read by tesseract).
  The budget's line-item veto letters are left out (with a text layer, but their first pages are a speech about the budget,
  not the items' reasons). `veto_message()` in convert.py gives a veto that stands (stage 6) the letter from after "Dear Mr.
  Speaker ...:" to the closing, without the letterhead's footer, with a few SC slips fixed ("$.C." for "S.C.", "art. IH"),
  and only when the letter names its own bill ("R-70, H. 3969"); the page says it was read from a scan and links it. On
  2026-11-22 the list had 3 such letters for 2023-24's 3 standing vetoes (H 4413, S 112, S 1166) and 3 for 2025-26's
  (H 3969, H 5164, H 5182), plus overridden bills' letters (read, not shown). Quality (H 3969, S 112, H 5182 checked against
  the scans): clean typed letters; about one slip a letter, mostly in legal citations ("Article Til" for III).
