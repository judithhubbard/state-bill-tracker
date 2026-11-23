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
  when the court ends. Governor 10 days. No summaries in the data ("What it does" is a lead quoted from the bill's text
  since 2026-11-22, below); Senate and (since
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
  seat (the rest cite roll calls not yet in the 2026 file, or none). GitHub's download had none at first: its
  .github/states.json command didn't install poppler-utils, so every run printed "pdftotext isn't installed" (the data
  check's "split floor votes naming members: S 100%, H 0%" FAIL, 2026-11-22); the command installs it now.
- **Committee votes by member (2026-11-22).** Since the 194th General Court's joint rules (2025), committees post their
  votes in the API (robots.txt: "User-agent: * / Disallow:" with nothing barred). GET
  /api/GeneralCourts/<court>/Documents/<bill> carries CommitteeRecommendations[].Votes[]: the question ("Ought to pass",
  "Should H.600 be reported favorably to the House?", "Study", ...), the day, the bill it was taken on (a new draft's vote
  can be under the old number) and one group per branch of members' codes: Favorable, Adverse, ReserveRight,
  NoVoteRecorded. /api/GeneralCourts/194/Committees/CommitteeVotes lists the 37 committees that post them (joint
  committees, House Ways and Means, Senate Ways and Means, Senate Ethics and Rules ...); the 193rd's records have none.
  `committee_votes()` in fetch.py reads the document for each bill of the 194th on whose history has a committee report
  (about 8,100 of 9,000; 10 minutes a run, the bills never read first, so the first copy takes a few runs), again when its
  history grows; it keeps them in data/ma/<session>/committee_votes.json, with each committee code's name in
  committee_names.json (contacts.py writes them; fetch.py reads any missing). convert.py's `committee_votes()` makes one
  kind "C" vote for each branch's members of a joint committee (the joint rules count each branch's members apart), named
  in full ("Joint Committee on Housing", "House Committee on Ways and Means"; profile.js `voteWhat`: "Joint Committee on
  Housing (House members)"), turned so that "Yes" is for the bill going forward: a question for a study order or an
  adverse report ("Study", "Put bill into Study", "Ought Not to pass") counts its Favorable members as No. A question that
  names only the bill or the committee is read by the recommendation, and left out when that is Adverse, Study or
  Accompanied. ReserveRight ("reserved the right" to dissent) is "B", NoVoteRecorded "A". A vote with a member twice is
  left out; the same vote under an earlier draft's number and the new one's is kept once. Tested on 107 bills' documents
  (2026-11-22): 86 votes on 58 records, every member tied to a seat but one. Contacts now list each committee's members
  per branch from the members' own records (the committee record lists only chairs), so a legislator's committee votes
  show on their pages.
- **A member code with a space (2026-11-22):** Sen. Liz Miranda's code is "L M0"; contacts.py asked for her record
  unquoted, it failed, and she was missing from member_details.json and the contacts (39 senators). The address is
  quoted now. data_check's "named votes aren't tied to a seat" LOOK shows such a name ("S?L M0").
- **"What it does" from the bill's text (2026-11-22):** `states/ma/billtext.py` reads each bill's document record
  (/api/GeneralCourts/194/Documents/H100: its DocumentText, the bill as filed or as a committee redrafted it, plain text
  whose lines are sometimes wrapped) one at a time, eight minutes a run (fetch.py, last; the current court first, the
  bills acted on latest first; about 9,000 a court, so a few days of runs). "SECTION 1." begins a section; "... by
  inserting after section 116G the following section:-" is new law, "... striking out ... and inserting in place thereof
  ...:-" counts its new wording as added, a short instruction quoting its words ("by striking out “Thanksgiving day” in line
  22.") is itself the change, and a section with no instruction is uncodified new law. "Amends M.G.L. c. 90, § 32C." only
  when the section says "General Laws" (not special acts or town charters). Label "From the bill's text: ...". Hand check
  of 20 of 2025-26 (before the last fixes): 14 informative, 6 weak (two only "Amends", a heading, definitions, a charter
  instruction).
