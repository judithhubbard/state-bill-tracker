# Oregon

Moved from CLAUDE.md (2026-11-19). Shared conventions, the data traps list and the site's code notes stay there.

- **Oregon (started 2026-10-31):** `python3 states/or/fetch.py` reads the Legislature's OData API
  (https://api.oregonlegislature.gov/odata/odataservice.svc/; see the state-survey-2026-10-31 memory): whole tables per
  regular session ("2025R1") into data/or/<key>/<Table>.json, in a few minutes, every run. The package is named "or", a
  Python keyword: its files load each other with importlib. One session a year (`years: 1`; long in odd years from the
  second Monday of January, short in even years from the first Monday of February). History lines carry their house;
  "Do pass and be referred to Ways and Means" is a referral; "by prior reference" and "X, then Ways and Means" are
  stripped from committee names; "Passed." alone (after a motion) and consent-calendar lines are passages. Floor votes
  belong to a history action (MeasureHistoryId); committee votes are by member (CommitteeVotes). Laws and vetoes match
  the API's ChapterNumber and Vetoed flags. Title: the official "Relating to ..." short title without the stock ";
  declaring an emergency"; the catch line is the one-line summary; "What it does" is the staff digest (tags stripped).
  Bills filed before the session "by order of the President" have no member sponsor: the "at the request of" field names
  who asked. Joint committees (Ways and Means) are listed for both houses. Governor 5 weekdays, or 30 business days after
  adjournment. Separate Senate (30) and House (60) districts by city or county.
- **The next session's bills (2026-11-22):** from November `main()` asks the API once a run for one measure of next year's session (Measures, `$top=1`) and reads its tables, into data/or/<year>R1/, only once one is there (2025's pre-session filed measures were created 2024-12-31; 2027R1 wasn't in LegislativeSessions on 2026-11-22). The fetcher writes no incomplete marker.
- **Veto letters (2026-11-22, read by OCR, the owner's decision):** the Governor's letters are scans on oregon.gov/gov/Documents
  (robots.txt allows it). `veto_letters()` in fetch.py, after the tables: for 2025 on, each vetoed measure's (the
  Measures `Vetoed` flag, or "Governor vetoed" / "Governor signed with line-item veto" in its history) letter under
  SB302_Veto_Letter.pdf or SB-976_Veto_Letter.pdf (both names are used); for 2023, Kotek's letters to the Secretary of
  State are one 21-page scan, 2023_Bill_Letters.pdf (from her 2023-08-04 newsroom post; `COMPILATIONS`), read whole into
  2023R1/vetoes/_letters.json, and `veto_message()` in convert.py picks the letter whose head (down to "Dear ...") names
  the bill (the compilation's signing letters are never shown). Each letter is read once (states/letters.py's
  `scanned()`), two seconds apart, at most 8 minutes a run; a measure found under neither name is asked again weekly
  (vetoes/asked.json). Not found on 2026-11-22: SB 736, SB 875, SB 1047 (2025) and HB 4177 (2026) are under other names
  (the newsroom posts for SB 976 and SB 1047 link "SB-1047_Veto_Letter.pdf", so SB 1047 should be found on its run; the
  data check LOOKs at HB 4177). 2024 had no vetoes; 2022 is Brown's (none). Shown: vetoed bills, and SB 1095 and SB 5506
  of 2023 as line-item vetoes. Quality (SB 302, SB 976, HB 3795 of 2025 and the 2023 compilation, checked against the
  page images): typed letters, word-perfect apart from bullets read as "e" (put back as "•") and specks in the margin
  read as marks (dropped before paragraphs are joined).
- **Floor calendars (2026-11-22):** the OData FloorSessionAgendaItems table (fetch.py now downloads it with the others:
  one more paged request per session a run), each house's order of business for a day: bills on "Third Reading Of ..."
  (and special orders) are set for a vote that day ("Senate floor vote Mon, Feb 16"); "Possible Consideration Of House
  Amendments" (concurrence) may not come up: "listed". First and second readings left out. Day only, no time. 2026R1 had
  1,185 rows (posted a median 2.6 days ahead, the survey says); with FLOOR_TODAY=2026-01-01, 300 third-reading entries and
  23 concurrence entries, every one with a floor action that day or the next.
