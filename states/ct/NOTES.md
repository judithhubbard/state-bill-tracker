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
  Windows-1252 bytes (decoded as one or the other). No votes: the vote sheets' only index is the bill status pages,
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
