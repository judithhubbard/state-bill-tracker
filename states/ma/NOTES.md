# Massachusetts

Moved from CLAUDE.md (2026-11-19). Shared conventions, the data traps list and the site's code notes stay there.

- **Massachusetts (started 2026-10-31):** `python3 states/ma/fetch.py` reads the General Court's API
  (https://malegislature.gov/api/; see the ma-data-sources memory): each two-year General Court's document list (2025 is the
  194th), each bill's history (one request per bill, three at a time; a finished court's are read once, the current one's
  again when active), the Senate's roll calls, members (`contacts.py`, run by fetch.py; past courts' members for names in
  roll calls) and the session laws. Only bills and resolves are shown (not orders, study orders or constitutional
  proposals). A committee's new draft has a new number ("Accompanied a new draft, see H4321"), and a conference report is
  a new bill ("Reported, in part, by H4040"): `load_session()` follows the chain, and the record takes the newest number
  with the others as earlier numbers; the governor's amended sections that come back as bills ("see H4051 for section
  15") join the law's record. Laws come from the session laws file (`laws_<year>.json`, by OriginBill), since some
  histories stop before the signing. A study order ends a bill in committee (`STATE.heldAction`, "Sent to study").
  "Passed to be engrossed" is a house passing it; "Enacted ... laid before the Governor" sends it. Committees are almost
  all joint; House Steering, Policy and Scheduling decides which bills reach the House floor; the Committee on Bills in
  the Third Reading counts as the floor. Formal sessions end July 31 of the second year (`formalEnds()`), informal ones
  when the court ends. Governor 10 days. No summaries in the data ("What it does" isn't shown); Senate and (since
  2026-11-22, below) House votes by member. Earlier courts linked by identical title (`earlier()`). Cities and towns (351) by district.
- **Passed both houses (2026-11-19):** only when the branches agree on one text: the second branch passed it unamended,
  or the first concurred in its amendment (the last word, not "NON-concurred" or "concurred ... with a further
  amendment"), or, after "Committee of conference appointed", both accepted the report (`agreed()`); or it was enacted.
  A changed title alone isn't an amendment (about 300 bills went from "Read third (title changed) and passed" straight to
  enactment). Bills each branch passed in its own version are stage 2, "In conference: each house passed its own version"
  or "Passed each house in a different version". Found by the pre-launch check: H5576, S2619 and 11 more of 2025-26 in
  conference; H1999, H4049, S2922 of 2023-24 amended by the second branch and never concurred in.
- **Dates after the file was read (2026-11-21):** the histories of H4716, H4721, H5685 and S3097 (chapters 261-264 of
  2026) say "Signed by the Governor" on 2026-11-30; the session laws, first also "Nov 30 2026", now say October 30. A
  history line dated after its bill's file was read takes the law's date for a signing, else the read day (`read_day` in
  `load_session()`); the session laws' own future dates were already capped the same way.
- **Committee hearings (2026-11-22):** `hearings()` in states/ma/fetch.py, run last, writes data/ma/<session>/agendas.json
  ({"H892": [["Joint Environment and Natural Resources", "2025-10-21T13:00:00"]]}), which convert.py's `agendas()`
  returns as it is. The API's /api/Hearings lists every hearing's id only (about 4,300, no dates); /api/Hearings/<id>
  gives the host committee ("Joint Committee on Housing" -> "Joint Housing"; HearingHost's GeneralCourtNumber picks the
  session), Status ("Confirmed", "Completed", "Canceled"; a moved hearing keeps its id, with the old date under
  RescheduledHearing), StartTime and the bills on its agenda (HearingAgendas' DocumentsInAgenda, BillNumber "H892").
  Each hearing read is kept in data/ma/hearings.json ({"floor", "hearings"}); a run reads the ids not yet kept from the
  floor up (the first run's newest 150, since ids rise as hearings are posted; at most 300 a run) and again every kept
  hearing dated from yesterday on, three at a time. Only today to three weeks ahead, not canceled, rescheduled or
  postponed. robots.txt allows everything. Tested live on 2026-11-22 (the newest 10 hearings: 4 upcoming with bills,
  H5668, H5296, H4963, S3301; the last two not yet in the copied documents.json) and on saved 2025 hearings with today
  set to 2025-10-01 (111 bills, all matching records). Joint committees hold nearly every bill's hearing; the House and
  Senate Ways and Means and the like appear as "House ..."/"Senate ...". Untested: the 195th General Court's first
  hearings (January-March 2027: the floor stays, so new ids are read as they appear).
- **The next General Court (2026-11-22):** the API answers 400 "Could not locate any public Documents in General Court "195"" until the 195th's first documents are public; bills are filed by mid-January and numbered mostly in February (6,357 of the 194th's bills have their first action in February 2025). fetch.py treats that answer as not there (no retries), makes no folder and never marks Massachusetts incomplete for the new court while the last court is on file, and reads the 194th's histories as a live court until March 1, 2027 (its informal sessions run to January 6 and the governor acts in the ten days after). The site shows 2027-28 once its first numbered bill's history is read. Docket filings (HD/SD numbers, before a bill number) aren't kept.
- **House roll calls by member (2026-11-22).** The API has none; the House Journal publishes one PDF a year of every
  "Yea and Nay" by member, https://malegislature.gov/Journal/House/<court>/<year>/RollCalls (194 for 2025 and 2026, 193
  for 2023 and 2024; numbered through the court: 2023 No. 1-70, 2024 No. 71-203, 2025 No. 1-116, 2026 No. 117-236 on
  2026-11-22, with No. 233 missing). `states/ma/house_votes.py` (run by fetch.py, after the Senate's roll calls; needs
  pdftotext) reads a year's file when it has none, a past year's once more after February 1 of the next year, and this
  year's when the histories cite a number it doesn't have yet (at most every 6 hours) or weekly; it keeps them, read, in
  data/ma/<session>/house_rollcalls.json. Each page: the bill and motion ("H. 4993 On passing to be engrossed"), day,
  "No. 121  154 YEAS  1 NAYS  3 N/V", then four columns of "Y|N|X|P <surname>" ("Moran F.", "Ramos, A.", "Mr. Speaker",
  "--Jones--" for a floor leader, "Tyler *" for a vote after the roll closed; P "present" is in none of the tallies). All
  438 roll calls of 2023-26 parse with names adding up to their tallies, and every name matches one member of that court
  (member_details.json: surname, with the initial where two share it). convert.py ties a House vote to the roll call its
  line cites ("(See YEA and NAY No. 117)", "(See YEA and NAY, No. 127)", "(See YEA and NAY in Supplement, No. 25)") when
  the day is the line's and the tally is too or the roll call is on one of the record's bills; then the roll call's own
  totals win (H5151 of 2025-26 "121 YEAS" for 129, S3106 "139" for 149, H4993 "0 NAYS" for 1). Names: N no, X "A" (not
  voting), P "B". The file lags the histories: on 2026-11-22 the 2026 file ended at No. 236 while histories cite up to 274.
  Coverage (histories of 2026-10-31): bills' House floor votes naming members, 2023-24 0 -> 89 of 97 (names as written,
  "H?Name", as the Senate's: there's no contacts file for a past court), 2025-26 0 -> 121 of 164, every name tied to a
  seat (the rest cite roll calls not yet in the 2026 file, or none).
