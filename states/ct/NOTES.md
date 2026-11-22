# Connecticut

Moved from CLAUDE.md (2026-11-19). Shared conventions, the data traps list and the site's code notes stay there.

- **Connecticut (started 2026-10-31):** `python3 states/ct/fetch.py` reads the General Assembly's CSV files from its FTP
  server (ftp://ftp.cga.ct.gov/pub/data/; see the ct-data-sources memory): bill_info (titles, statements of purpose, act
  numbers), bill_history, introducer, comm_ref, committee, subject and the legislator database, for the current year (top
  folder) and archive/<year>; small, so read in full each run. 2023 and before are only flat files at the archive's top
  level ("2023bill_info.csv", bill_history, introducer, subject, "2023LegislatorData.xlsx": no comm_ref, committee or
  actions); fetch.py reads those years once, under the usual names, the spreadsheet as LegislatorData.csv (read without
  dependencies), and keeps four years back (2022-26: two finished sessions of each kind for the statistics). There, dates
  are "1/23/2023" (`rows()` makes them ISO), introducer codes are unpadded ("1", "115A" for a mid-session replacement:
  the spreadsheet's dist_code), and committees come from the nearest later year's list (referral lines carry the code).
  2022: 169 laws, 2 vetoed (PA 22-1..146, SA 22-1..24); 2023: 235 and 5 (PA 23-1..208, SA 23-1..31). One session a year (`years: 1`; long in odd years, short
  in even: `opens()`/`sessionEnds()` in profile.js are the Wednesday after the first Monday of January or February, June
  or May). Committees are joint (both houses' members); `commIntro` says so. Sponsors are codes: "006" a House
  district, "S06" a Senate district, letters a committee (committee bills). A Public Act number comes when both houses
  pass the same text, before the governor acts (HB 7004 of 2025 got one and was vetoed): it decides "passed both
  houses", and only "SIGNED BY GOVERNOR" is a law. History lines kept as written are in sentence case so "REFERRED TO
  OLR, OFA" (research and fiscal offices) can't pass for a committee referral. The files are UTF-8 with a few
  Windows-1252 bytes (decoded as one or the other). No votes in the files (floor votes now come from the journals: below); the vote sheets' only index is the bill status pages,
  which robots.txt disallows (and the site omits GoDaddy's G2 intermediate certificate). "What it does" is the
  statement of purpose. Legislators (phones, emails, committees, leadership) from the database; Capitol phones are the
  caucus offices' shared lines. Towns from the Census county-subdivision files (169). Earlier years linked by title and
  purpose words.
- **Committee agendas (2026-11-22):** the FTP server has no meeting data, so `agendas()` in states/ct/fetch.py reads
  www.cga.ct.gov (robots.txt disallows /asp/cgabillstatus/, /asp/menu/ and a few others, not these): the Schedule of
  Events' own feed, `/basin/api/v1/calendar-events/` (what calendarofevents.asp's script reads: about a year of events, each
  with its committee code `office_code`, kind `mtg_type` (COM a committee meeting, PHR a public hearing, PHC a hearing
  followed by a meeting), start in Eastern time written with a false "Z", and `url`, its agenda PDF once posted:
  /2026/JUDdata/ca/pdf/2026ca-00323-R001000JUD-ca.pdf, .../pha/pdf/...-pha.pdf for hearings), then each agenda from
  yesterday to three weeks ahead through pdftotext: bills read "S.B. No. 89", "H.B. No. 5308", "H.J. No. 1". Events whose
  title begins "CANCELLED" are left out. Committee names from committee.csv, as "Joint Judiciary". The site omits GoDaddy's
  G2 intermediate certificate, so fetch.py adds it to a copy of the system's certificates (data/ct/ca.pem, as Illinois
  does). One request for the feed plus one per posted agenda (31 in the three weeks from 2026-03-20). Tested with the date
  set to 2026-03-20 against the saved feed and the Judiciary agendas of 3/23 (18 bills, all matching records) and 3/4
  (hearing: SB 89, 262, 294, 296, 297); a hearing of nominations only lists no bills. Needs pdftotext on the runner (the
  workflow's run line installs poppler-utils). Untested: how early agendas are posted in session, and revised agendas.
- **The next session (2026-11-22):** the FTP server has no prefiled bills; its top folder moves on to the new year around the session's first bills (2024's archive folder appeared 2025-01-06, 2025's 2026-02-25). fetch.py reads a year only once the top folder holds it (`newest()`; also before January 1 if it moves early), makes no folder for a year the server doesn't have, and reads every year from the archive while the top folder's bill_info has no bills, so an empty new session never overwrites the last one; the site shows 2027 from the run after its first bills appear (the session opens January 6, 2027).
- **Floor votes (2026-11-22):** from the House and Senate Journals (www.cga.ct.gov/<year>/jnl/, which robots.txt allows):
  `states/ct/journals.py`. One PDF a session day, its address built from the day, `/2025/jnl/h/pdf/2025HJL00501-R00-JNL.PDF`
  (Senate `/s/pdf/...SJL...`); the folder has no listing (403), so the days asked for are those the history names for a
  floor vote in that house (`floor_steps()`: "HOUSE PASSED", "SEN. PASSED, HO. AMEND. SCH.", "ADOPTED, HOUSE", "HOUSE
  REJECTED BILL" ...). PDFs are 1-8 MB; only their text is kept (data/ct/<year>/journals/H0501.txt), each read once; a
  404 is asked again at most once a day for 60 days (`missing.json`). fetch.py gives it ten minutes a run, newest days
  first: about 50 journals a long session, 36 a short one (2026: 36 in 2.3 minutes), so a first copy of 2022-26 takes two
  runs (until then data_check FAILs "floor votes missing?" for the older years). Each roll call prints its totals ("Those
  voting Yea .... 144"), the sentence ("On a roll call vote House Bill No. 7083 as amended by ... was passed.") and a grid:
  House surnames ("Y ALLIE-BRENNAN", "X JACOBSON", "JOHNSON, D."; matched to the year's legislator list, then the year
  before's for members who left mid-session, Kevin Ryan and Robert Sanchez in 2025), Senate districts and names ("N 21
  JASON PERILLO"); X or A is absent. The names must add up to the printed totals, else only the tally is kept (one in 2025:
  SB 1234, whose grid the Senate Journal of 2025-05-08 left out). Layout quirks handled: "VACANT" and a bare district number
  for an empty seat, a letter alone on its line with the name on the next, a page break between the sentence and the grid.
  The Senate's consent calendar is one roll call ("On the roll call vote the Consent Calendar No. 1 was adopted.") for every
  bill placed on it since the day's last one, placed one at a time ("the bill was placed on the Consent Calendar", after the
  bill's heading) or as a list ("The following bills ... placed on the Consent Calendar"). Amendments' roll calls are left
  out. A roll call is kept only when the bill's history has a floor vote in that house that day or the next; the journals'
  slips: a sentence naming another number than its heading ("Senate Bill No. 247" under "S.B. No. 274", 2026-04-14: given
  to the heading's bill when the sentence's has no floor vote then), numbers wrong in both (HB 5542 for HB 5442, SB 465 for
  SB 425 in a consent list, 2026: left out, 4 a year), a passage printed over another vote's grid (SB 148 of 2026, "was
  passed" over an amendment's 11-21: a "passed" whose tally lost is left out), and bills whose roll call the journal never
  prints (SB 3 of 2025, its sentence right after an amendment's grid). 2025: 309 of 317 bills that passed a house have a
  floor vote (517 roll calls); 2026: 257 of 258 (444). Timeliness: the House's journals are posted the day after (2026's
  Last-Modified: 03:00-08:00 the next morning; the last day's, May 6, on May 12); the Senate's are revised months later
  (several re-posted in September 2026), and a journal once read isn't read again. Not found under these addresses: the
  November 2025 special session (H1112, S1112, S1113 answer 404). The vote sheets (/2025/VOTE/H/PDF/2025HV-00059-R00HB06434-HV.PDF)
  aren't used: their numbers can't be derived. Committee votes still aren't published anywhere readable.
- (2026-11-22) The legislator database's email column holds the Senate Democrats' contact-form addresses
  ("https://www.senatedems.ct.gov/senator/john-fonfara/email-contact"), 25 of them: contacts.py shows them as the form.
- **Veto messages (2026-11-22):** from the governor's numbered Bill Notifications on portal.ct.gov
  (/governor/-/media/office-of-the-governor/bill-notifications/<year>/bill-notification-<year>-<n>.pdf; robots.txt allows
  it; a missing number answers a "404 Error Page" in HTML), found by number, no table: states/ct/vetoes.py. Each
  notification lists the bills signed, "signed and line-item vetoed" and vetoed; a veto's entry says on which page its
  letter is ("The veto message can be found on page 4", 2025; "The veto message for this bill can be found on page", 2023),
  or (2024, 2026) the letter follows with no page given and is found by its "Senate Bill 226". Letters are typed (2025's
  HB 5002, SB 8; 2026's SB 298) or scanned (read by OCR: 2022-24 and 2025's HB 7004 and line-item vetoes). Checked
  2026-11-22: every veto of 2022-25 (2, 5, 2, 3) has its message, plus the line-item vetoes of HB 7066 and HB 7067 of 2025
  and SB 298 of 2026 (shown on the law). Notifications per year: 17, 13, 13, 19, 13. OLR's yearly "Veto Package" has only
  excerpts. The FTP files have no line-item veto step, so a line-item veto shows only as the governor's letter.
