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
- **Veto letters (looked into 2026-11-22; not read):** oregon.gov/gov/Documents/<SB-976>_Veto_Letter.pdf is predictable from the bill number, but SB 976's is a scan with no text layer. OCR would be the owner's decision.
