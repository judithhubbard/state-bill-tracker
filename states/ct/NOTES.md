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
