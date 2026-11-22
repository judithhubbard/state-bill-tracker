# New Mexico

Moved from CLAUDE.md (2026-11-19). Shared conventions, the data traps list and the site's code notes stay there.

- **New Mexico (built 2026-11-13):** `python3 states/nm/fetch.py`
  reads www.nmlegis.gov (see its docstring) into data/nm/<year>/; `python3 states/nm/contacts.py` (every run; add it to
  states.json's run after fetch.py: check_site.py wants contacts_<year>.json fresh) builds the contacts; `states/nm/towns.py`
  was run once. A page a year (`YEARS = 1`): a session from the third Tuesday of January, 60 days in odd years and 30 in even
  years (only the budget, the governor's call and vetoed bills), `session_kind()` "long"/"short"; `opens()`/`sessionEnds()`
  in profile.js compute both (no `dated`). Special sessions, memorials and joint resolutions other than constitutional
  amendments are left out. The converter reads no database: the Access file (LegInfo<yy>.zip) isn't needed (it was read
  once, by hand, with the pure-Python `access-parser` in a scratch environment, to check totals; it fails on LegInfo25), so
  nothing beyond Python's standard library is needed on GitHub. `states/nm/convert.py` reads each bill page's spelled-out
  actions (with calendar days) and, where they're short, the coded ActionText ("[5] HHHC/HJC-HHHC [8] DP-HJC ... SGND BY GOV
  (Mar. 21) Ch. 13."; key in data/nm/abbreviations.html): "Sent to HHHC - Referrals: HHHC/HJC" lists the committees in order,
  and there's no line when the bill moves on, so the referral list is followed (a report sends it to the next committee, the
  last one's to the floor; "Referred to:", "re-ref", "HAFC ref w/drn", "SCC referral removed" change it); "Withdrawn from
  committee ... for subsequent action" goes to the floor or the committee the ActionText's "w/drn-HTRC" names. Committee
  reports: "Do Pass", "Do Not Pass but ... Do Pass ... on Committee Substitution", "without a recommendation", "Do Not Pass,
  Bill Has Died", "Tabled Indefinitely". In 30-day sessions the Senate Committees' Committee (SCC = SXCC) rules each Senate
  bill germane first ("Reported by committee to fall within the purview of a 30 day session"); "Not Printed" ("not prntd-HRC")
  bills go to House Rules (HRC = HXRC): both are `STATE.gates`. "Passed in the House of Representatives - Y:64 N:0" is the
  passage; "Failed to Pass in the Senate, Bill Has Died" takes its tally from the ActionText. Second-house amendments (its
  committee's amendments or substitute, "Senate Floor Amendment", "fl/aaaa", "Floor substitute adopted") need "House has
  concurred", the other house receding, or both houses' "Report Adopted" (conference). The governor's lines have no calendar
  day: "Signed by Governor - Chapter 13 - Mar. 21", "LAW WITHOUT SIGNATURE." (day and chapter from the ActionText),
  "Vetoed by Governor" (dated from the governor's message), "Pocket Veto" (dated the governor's last day, 20 days after the
  session), "(partial veto)" in the ActionText (line items), "Veto Override Passed in House" (HB 65 of 2025: the Senate never
  voted, the veto stands). Chapters come from the ActionText: the spelled-out line is wrong twice (below). "Succeeding
  entries: H 2": folded into HB 2 (HB 3 each year). "Action Postponed Indefinitely": the session ended. Totals match the
  pages' "Current Location" bill for bill and the Legislature's own counts: 2024 69 laws, 1 veto, 2 pocket vetoes (LegStats:
  69 chapters, 1 veto, 72 to the governor), line items on HB 2, HB 252, HB 308, SB 246, SB 275; 2025 160 laws, 18 vetoes, 17
  pocket vetoes (the Legislature's and the press's count; LegStats unreadable), line items on HB 2, HB 450, SB 5, SB 31, SB
  425; 2026 71 laws, 2 vetoes, 1 pocket veto (LegStats the same), line items on HB 2, HB 332, SB 240, SB 273. Chapters run
  1-N with none missing or repeated. No law without signature but SB 104 of 2026. Constitutional amendments are joint
  resolutions whose short title ends ", CA": a majority of each house's members, then the voters (`amendmentOnce`,
  `ballotEvenYears`); "Signed by one or both houses ... SGND (C.A. 3)" is passed (2024 SJR 1, SJR 16; 2025 HJR 2; 2026 HJR 1,
  HJR 5, SJR 1), tagged "const", stage 3, never the governor. Votes: floor votes member by member from the vote PDFs' text
  (`read_roll()`: two columns of names, each X placed under its nearest column heading; YEA/NAY/PNV/EXC/ABSENT, Senate
  YES/NO/ABS/EXC/REC; file names vary, "HJR01HSVOTE", "SJR0016SVOTE", so the house comes from the text), matched to the
  passage lines by house and tally: 173 of 174 (2024), 509 of 511, 200 of 203 (the rest have a later or earlier roll call
  than the one PDF). Committee votes from the committee reports ("The roll call vote was 9 For 1 Against"; House reports name
  the no, excused and absent members, Senate reports the yes votes too) and the tabling reports ("Motion to TABLE PASSED":
  shown as the committee's vote against the bill, with a "Tabled by" line): 476, 1,413, 494. Names are matched to that year's
  members.txt within the vote's house, whose third column is the roll calls' tag ("Martinez, A.", "Romero, GA"); members who
  served that year but aren't on it (2024 lacks four senators; Herrera, Ferrary, Reeb left in 2026) come from their own pages
  (members/<code>.html, "Years of Service"); a member whose seat someone else now holds, or (this year's page) who no longer
  serves, is named ("H?Herrera"), not given the seat; all other names match. "What it does" is the Legislative Finance
  Committee's fiscal impact report synopsis ("From the Legislative Finance Committee's fiscal impact report."): the bill's
  (or its newest committee substitute's), then later amendments' (the report lists them newest first), page footers dropped
  and paragraphs split by page breaks rejoined; 62%, 89% and 67% of bills have one (2024-26). Titles are the short titles in title case
  (each word as the reports' "SHORT TITLE" writes it). Topics from committees (`COMMITTEE_TOPICS`), else title and synopsis
  words. Earlier years linked by the same short title and prime sponsor code, one bill each year, never laws or
  appropriations. Contacts: each year's members.txt (Capitol room and (505) 986 phone, several shared; email), names and
  pages from the members' pages, committees with chairs from committees.json; this year's page lists only members serving
  now (House 37 and 64 vacant). Leaders: Speaker Javier Martínez, President Pro Tempore Mimi Stewart (the Lieutenant
  Governor presides over the Senate); the Legislature elected in November 2026 organizes in January 2027: update `LEADERS`.
  Governor Michelle Lujan Grisham (D), term-limited: a new governor takes office January 1, 2027: add them to `GOVERNORS` and
  legislatures.json. Governor 3 days (Sundays excepted) in session, else law without signature; 20 days after adjournment
  for bills passed in its last 3 days, then a pocket veto (`govDeadline()`); override two-thirds. The governor's phone,
  address and contact page are from governor.state.nm.us/contact-the-governor/ (checked by program 2026-11-13, not by the
  owner). Places (`towns.py`): cities, towns, villages, Census-designated places and counties, separate Senate (42) and
  House (70) lists.
- **Committee agendas (2026-11-22):** `agendas()` in states/nm/fetch.py (every full run, before the bills) reads the
  Session Calendar page (/Calendar/Session), which during a session links each committee's hearing agenda
  (/Agendas/Standing/HJCageFeb04.26.pdf: code, "age", day) and each house's daily schedule of committee hearings
  (hSched020426.pdf, sSched020426.pdf; a day's schedule also lists the next days' hearings); when it links none, it reads
  the year's archive instead (/Calendar/Session_Archive?Year=2026, the page the "Archive" button goes to, which lists
  every agenda and schedule posted that year with its hearing day and posting time). The PDFs dated (by file name) from
  yesterday to three weeks ahead are read each run, as text by pdftotext: a hearing is a heading ("HOUSE JUDICIARY
  COMMITTEE - Christine Chandler, Chair"; the Senate's schedule leaves out "SENATE": "FINANCE COMMITTEE - ..."; a long
  heading wraps: "HOUSE RURAL DEVELOPMENT, LAND GRANTS AND CULTURAL - LINDA SERRATO, CHAIR" / "AFFAIRS COMMITTEE"), its day
  and time ("Wednesday, February 4, 2026 - 1:30 PM or 15 minutes after the floor - Room 309") and its bills ("HB 70",
  "CS/HB 49", "SB 3/a", "HJR 1 /a"; memorials and resolutions left out). A committee's own agenda (often "REVISED")
  replaces what the schedule says about its hearing that day. Committee names: "House Judiciary", "Senate Tax, Business
  and Transportation" ("&" as "and"). Into data/nm/<this year>/agendas.json; `agendas()` in convert.py keeps meetings from
  today on. Tested as of 2026-02-04 with the 2026 archive (16 PDFs for February 3-4): 23 hearings, 88 bills, all matching
  2026 records. Untested: the live Session Calendar's own list during a session (its committee lists say "No Committee
  Schedule Found" now; the archive is the fallback). The HTML committee calendar (/Entity/House/Committee_Calendar) is
  empty between sessions and wasn't used. A failed request keeps the last file; without pdftotext it's skipped.
