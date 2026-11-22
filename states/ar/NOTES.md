# Arkansas

Moved from CLAUDE.md (2026-11-19). Shared conventions, the data traps list and the site's code notes stay there.

- **Arkansas (built 2026-11-08):** `python3 states/ar/fetch.py` reads
  the Bureau of Legislative Research's pipe files (webftp.blr.arkansas.gov) into data/ar/<biennium>/, and, for sessions with
  no kept copy of the files (2024F, 2024S2), arkleg.state.ar.us's bill pages in the files' shape (see its docstring);
  `--votes` reads members' votes from the roll-call pages (votes/), each once. A page a year: the regular session
  in odd years ("2025R"), the fiscal session in even years ("2026F": 30 days of appropriations; another bill needs two-thirds
  of each house to be introduced). Extraordinary sessions (2023S1, 2024S2, 2026S1: numbered from HB1001 again) are left
  out, as Texas's are. `session_kind()` is "regular"/"fiscal" and `session_label()` "2025 regular", so statistics compare
  like with like (each page compares with past sessions of its own kind: build_data.py's `insight_of`). `states/ar/convert.py`
  reads the history as written (each house has its own stamp wording: "Read the first time, rules suspended, read the
  second time and referred to the Committee on X- HOUSE" vs "Read first time, ... referred to X - SENATE"): "Returned by
  the Committee ... Do Pass" approved, "... do not pass" voted down, "Recommended for study in the Interim" (`heldAction`
  "INTERIM STUDY"); "Read the third time and passed" the passage (joint resolutions "adopted"/"concurred in"); "The vote by
  which HB1001 Passed was expunged" undoes it; "TO BE ENROLLED"/"ORDERED ENROLLED" passed both houses; "Correctly enrolled
  and ordered transmitted to the Governor's Office"/"DELIVERED TO GOVERNOR." sent; "Returned from the Governor as
  requested" takes it back; a law is its Act number (`STATE.lawWord` "Act"; signed, without signature or over a veto);
  "Governor Vetoed"/"Returned to House from Governor Having Been Vetoed" a veto; "line-item vetoed" stays a law. The
  history's ids aren't in date order: sorted by time. Sponsors are the members' Sponsor Names ("L. Johnson"), turned into
  full names from the members files (this General Assembly's, then the one before or after for members who left; the
  2023-24 file has one column fewer than 2025-26's). Members' votes: each roll call's Yeas, Nays, Non Voting (A), Present
  (B), Excused (E) by Sponsor Name, matched within the vote's house to that General Assembly's members ("H:12"); members
  who left are "H?McCollum". The 2023-24 roll-call pages never list Sen. Alan Clark, though their counts include him
  (HB1024's Senate vote: "Nays: 2", one name); `fill_missing()` puts back the house's members missing from every group
  when exactly one group is short by that many. Roll calls not yet read aren't shown (the files have no tallies). The title is
  the subtitle, sentence-cased (`titled()`); acts have a "What it does" from the BLR's Summary of General Legislation (below). Appropriation bills (most of a fiscal session)
  are `budget` ("Budget bill"). Joint resolutions proposing amendments (not Article V applications) are tagged "const":
  one passage by a majority of each house's members, then the voters at the next general election (`amendmentOnce`; up
  to three per election); the records show them enrolled and "Approved by the Governor", a formality, so they stop at
  stage 3. Topics from committees (`COMMITTEE_TOPICS`) and title words. Committee agendas from CommitteeAgendas.txt
  (`agendas()`). Legislators (`states/ar/contacts.py`, from the members, committees and chairs files, no web pages; run
  for each year): phones and emails from the members file (31 have no phone there); standing committees of each house and
  the joint committees bills go to (Joint Budget, Public Retirement, Energy, Military and Veterans Affairs), each listed
  for both houses with that house's members. Leaders from the members file's 2025 lines (`LEADERS`, `POSITIONS`); the
  96th General Assembly chooses new ones in January 2027. Governor 5 days (Sundays excepted) in session, 20 after
  adjournment; a veto is overridden by a majority of each house's members (legislatures.json "majority"). Each year's sine
  die day is in `STATE.dated` (add each year's). Totals, matching the Act numbering (Acts 1-N, none missing) and the news:
  2023 890 Acts and 3 vetoes (HB1189, HB1622, SB509; HB1176 line-item); 2024 176 Acts; 2025 1,026 Acts and 3 vetoes
  (HB1889, HB1961, SB451; HB1265 line-item: "four vetoes" in the news); 2026 174 Acts. Separate Senate (35) and House (100)
  districts by city, town or county (`states/ar/towns.py`).
- Next session's prefiled bills (2026-11-22: 15 bills of 2027R in the live folder, prefiled from mid-November) are shown as
  an upcoming session from the first one: `sessions()` in convert.py asks more than 100 bills only of sessions before
  this year (it hid 2027 at first).
- **What it does (2026-11-22):** the Bureau of Legislative Research's Summary of General Legislation, a book after each
  regular session summarizing every general act by subject ("ACT 28 (HB1204) limits the recovery of damages for ...").
  It's linked from the session's Session Documents page (arkleg.state.ar.us/Bills/SessionDocuments?a=1&
  ddBienniumSession=2025%2F2025R: "Summary of General Legislation"; 2023's "2023 Regular Session - General Legislative
  Summary") as a /Home/FTPDocument PDF (3-4 MB). robots.txt allows all but ChatGPT's agents. states/ar/summaries.py,
  called by fetch.py: the page, then the book when its address is new or the copy is 60 days old; read with pdftohtml
  -xml (poppler-utils), which keeps fonts: headings are bold or italic, or capitals; an act's text is the plain lines
  after its "ACT n (HB1234)" line at the same margin, carried over a page break. Proposed amendments (HJR 1018 of 2025)
  are a bold title, then "If approved by voters at the 2026 general election, the amendment would ...". Kept in
  <biennium>/general_summary_<year>.json, written to texts_<year>.json. Label: "From the Bureau of Legislative
  Research's summary of the act." Coverage: 2023 689 of 890 laws plus 1 amendment, 2025 845 of 1,026 plus 3; the rest
  are appropriations, whose fiscal summaries are tables of amounts (not used), as are the fiscal sessions' (2024, 2026:
  none). An act listed under several subjects has each different summary as a paragraph (SB 294 of 2023, the LEARNS Act,
  has 22). Traps: pdftohtml splits a line where the font changes ("... malpractice ac" + "tion."), so pieces with the
  same top are joined; the table of contents and index repeat headings and "ACT 986 ....... 18" lines, skipped.
- **Floor calendars (2026-11-22):** FloorCalendars.txt (already downloaded) lists each bill on each day's House or Senate
  calendar by its drafting id ("JLL443"), which LegislativeMeasures.txt turns into a bill and session (special sessions'
  bills aren't on the site). Its section codes aren't documented: `FLOOR_SECTIONS` keeps the ones where 77-100% of the
  bills listed in 2025-26 had a passage or concurrence vote that day or the next (third reading, concurrence, the
  appropriation calendars); amendments on second reading, bills just filed or withdrawn and resolutions are left out.
  Each is "listed" ("On the House calendar Wed, Apr 22"). Tested with FLOOR_TODAY: 2025, 1,176 bills; 2026 (fiscal), 175;
  all matched to records.
