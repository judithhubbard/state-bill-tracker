# Texas

Moved from CLAUDE.md (2026-11-19). Shared conventions, the data traps list and the site's code notes stay there.

- **Texas (started 2026-10-30):** `python3 states/tx/fetch.py` downloads each bill's history XML from the Legislature's FTP
  site (see the tx-data-sources memory; its Acceptable Use file asks data users to use it, not the TLO website), only
  files whose listing date changed, six folders at a time (about a second a file: the first full copy of three sessions
  takes hours). `complete()` re-downloads files cut off mid-transfer. Sessions are the Legislature's codes (`code_of()`:
  2025 -> "89R"); special sessions aren't shown. `states/tx/convert.py` reads the action codes (H555 House passed, S576
  Senate passed, E015 sent to the governor, E020/E025/E030 signed/filed without signature/signed with line-item vetoes,
  E035 vetoed; H/S 0xx-1xx referrals, 25x/28x reports, H245/S275 "left pending"); a reported House bill is shown in the
  Calendars Committee until it's placed on a calendar. H825/S825 "Transmitted to the Governor" is NOT a sending (it's on
  bills still in committee). One record per bill; companions show as similar bills. Committee votes are totals from the histories (House committees' members from the HRO floor reports, below);
  floor votes by member come from the journals (`states/tx/journals.py`): the House Journal's record votes by the "RV#"
  numbers in the histories, and the Senate Journal by each bill's heading (it has no record numbers), including the
  Local and Uncontested Calendar's list format and a date's second journal ("...SJ04-12-F1.HTM"); "(Same as previous
  roll call)" means the vote just before, motions included. About 98% of Senate passages are found; every list's
  count matches its tally. `states/tx/contacts.py`: the House's member and
  committee JSON, each senator's page, parties from the Legislative Reference Library; `dataName` is the last name, or
  "Bell, Keith" where two members share it. Counties with each district's share (`states/tx/towns.py`, run once, from the
  Texas Legislative Council's r4.pdf district reports). "What it does": the bill analyses
  (`states/tx/texts.py`): the current session's every run, and (2026-11-22) each earlier session's with six minutes a
  run until all are read (2023: about 3,200 analyses, a few runs; then 2021), cached by address in <code>/analyses.json. Session dates are computed (`opens()`, `sessionEnds()` = day 140, House deadline day 122,
  governor 10 days without Sundays or 20 after adjournment). Leaders: the Speaker, and for the Senate the Lieutenant
  Governor (not a senator). Totals for 2025 to check against: 1,047 signed, 140 filed without signature, 26 vetoed
  (reports/signedbygov.htm etc. on the FTP site).
- **Veto messages (2026-11-22):** the governor's objections, from two sources. (1) The journals the site already reads
  (`journal_vetoes()` in convert.py): a veto during the session is a message read in a house ("TO THE MEMBERS OF THE
  HOUSE OF REPRESENTATIVES AND SENATE ..." or "... SENATE AND HOUSE ...": "do hereby disapprove and veto House Bill No.
  353 ... due to the following objections:"), and the Senate Journal's last day prints every post-session proclamation
  for Senate bills (88R: 53). The reasons run from "the following objections:" to "Since the ... Legislature ... by its
  adjournment" / "Since you remain gathered" / "Respectfully submitted". (2) House bills vetoed after the session are in
  no journal read here: `states/tx/vetoes.py` (run by fetch.py, 8 minutes at most, never holds Texas back) reads the
  governor's scans by OCR (states/letters.py): the legislative statements' list (gov.texas.gov/news/category/legislative,
  2021's one post per veto, "HB_1193_Veto_Statement.pdf") and the 2025 special session announcement's
  VETO_proclamations_SCANS_2025-06-22_(2).pdf (34 pages, one proclamation a page), split by the bill each page vetoes
  into <code>/vetoes/<HB305>.json; data/tx/veto_pdfs.json lists the PDFs read, so none is read twice. Messages from
  scans carry `ocr` and the PDF's `url`. The General Appropriations Act's line-item proclamations (SB 1) are left out.
  Counts on 2026-11-22 (journals, plus 4 OCR'd locally as a test): 2021 9 of 20 (the other 11 House bills' posts come
  with the first CI run), 2023 55 of 76, 2025 18 of 26 (the rest of the 2025 scan with the first run). 2023's 21
  post-session House vetoes have no allowed source: the Legislative Reference Library's scans
  (lrl.texas.gov/scanned/vetoes/88/...) are barred by its robots.txt (Disallow: /*.pdf), the Texas Register
  (sos.texas.gov) answers 403, and gov.texas.gov posted none for 2023. OCR quality: the typed proclamations read
  essentially word for word (HB 305, 413, 449 of 2025, HB 1193 of 2021 checked against the page images); only the
  blackletter heading ("Governor of the State of Cexaz") and signatures misread, and both are cut.
- **House committee votes by member (2026-11-22):** `states/tx/hro.py` (run by fetch.py, 8 minutes a session at most,
  never holds Texas back) reads the House Research Organization's Daily Floor Report,
  hro.house.texas.gov/pdf/fr<yyyy>/<yymmdd><A|B|C...>.PDF (no robots.txt on that host, 404, checked 2026-11-22; the owner
  approved). Only those PDFs are read there: never house.texas.gov (its robots.txt bars ClaudeBot by name) or
  capitol.texas.gov. There's no listing to read, so the days are the House's second-reading calendar days in the saved
  histories (codes 420-435, 465, 515, 522: about 41 a session), each day's parts asked A, B, C ... until a 404 (about 120
  PDFs a session; a 404 is asked again once a day while the day is under three days old). Each part is kept as pdftotext
  -layout text in <code>/hro/<yymmdd><L>.txt. Each bill analysis names its House committee ("COMMITTEE: State Affairs —
  committee substitute recommended") and every member's vote ("VOTE: 11 ayes — C. Bell, Zwiener, ...; 0 nays; 2 absent —
  ..."; "present not voting" too). A group whose names don't number its count is dropped; names split across lines are
  joined ("Leo\n Wilson", "Gervin-\nHawkins"), and a name the House writes with a comma ("Curry, Garcia, Linda, Olcott",
  CSHB 149 of 2025) is put back together when the pair is a member's dataName. convert.py puts the names (nays "N",
  present not voting "B", absent "A") on the committee vote the history already has, when the analysis's committee and
  ayes-nays are the history's; never a second vote (an analysis matching no vote is counted, `HRO_STATS`). Names go to
  seats as the journals' do (`floor_vote()`: "C. Bell" picks Cecil Bell; only the current session's members are tied to
  seats, earlier sessions' names stay "H?Name", like their floor votes). Tested 2026-11-22 on five parts (2025-04-22 A
  and B, 2025-05-26 A, 2023-04-03 A, 2021-03-30 A; 2025-04-22 C answered 404): 59 analyses with a committee vote, every
  one matching the history's committee and tally; 2025's 548 names: all tied to seats but VanDeaver and Schatzline (no
  longer members), none off the committee's current roster, 38 of 46 votes naming the whole roster. Coverage before:
  0 of 2,710 / 2,828 / 2,498 House committee votes (2025 / 2023 / 2021) named anyone; the full download (first CI run)
  should name about the bills that reached a second-reading calendar (1,500-2,000 a session). Limits: a committee vote
  with every member present and voting yes names nobody (yes votes aren't listed), and the page then can't say how a
  member voted, as for other states' unanimous committee votes; bills that never reached the floor have no analysis.

- **"What it does" from the bill's own text (2026-11-26):** bills with no bill analysis (about two thirds of a session)
  get a lead quoted from the bill as introduced (`states/tx/billtext.py`, states/billtext_lead.py): the history XML's
  "Introduced" version on the FTP site (billtext/HTML/.../HB00010I.HTM), a table of printed lines (an indented line starts a
  paragraph). "SECTION n." marks the bill's sections; a new code section ("Sec. 465.0051.", "Art. 42A.5025.") is underlined
  and counts as a section of new law; an amended one keeps its "Sec." plain and only its new whole sentences count.
  Transition clauses ("The change in law made by this Act applies ...", "This Act applies beginning with the 2025-2026
  school year.", rules "as soon as practicable") are boilerplate. fetch.py reads them before texts.py, at most 8 minutes a
  run, four at a time (about 120 a minute), laws first, then bills that passed a house; sections in
  data/tx/<code>/leads.json (read once). 89R: about 5,900 bills, about six runs.
