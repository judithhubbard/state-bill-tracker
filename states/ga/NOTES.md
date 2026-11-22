# Georgia

Moved from CLAUDE.md (2026-11-19). Shared conventions, the data traps list and the site's code notes stay there.

- **Georgia (started 2026-10-31):** `python3 states/ga/fetch.py` reads the General Assembly's SOAP web services (plain
  HTTP; see the ga-data-sources memory): each regular session's legislation list (session ids in P.SESSION_IDS), each
  bill's detail (sponsors in order, committees, coded status history, floor votes) into data/ga/<year>/bills/, each
  floor vote member by member (votes/), members and committees. The first copy takes about an hour; the current
  session's bills are read again every run (no change feed). `states/ga/convert.py` decodes the status codes (the first
  letter is the house where the step happened; referrals don't name the committee: it's the bill's committee in that
  house). Agreeing to the other house's changes "As Amended" changes the bill again, disagreeing leads to conference, and
  a conference report needs both houses (`agreed()`; HB 196 of 2023-24). Laws are "Act 696" (`STATE.lawWord`). "What it
  does" is the long title's "so as to ..." clauses (`purpose()`); there are no plain summaries and no committee votes.
  Local legislation (one city or county) is narrow kind "place" ("For one city or county"), kept out of similar-bill
  matching. Bill pages are addressed by legislation id: a version's `link` (shared: build_data.py passes it, the page
  reads `v.link`). Two-year General Assemblies, 40-day sessions each year; each year's last day is in `STATE.dated`
  (add the new year's after its session). Governor 6 days in session, 40 after it. The Lieutenant Governor presides over
  the Senate (not a senator).
- **Veto messages (2026-11-22):** the governor posts one PDF a year on gov.georgia.gov, "Veto Messages and Signing
  Statement(s)" (robots.txt bars only /core/, /profiles/ and the like), linked from
  /executive-action/legislation/vetoed-legislation/<year> (2019-2022 pages end "-vetoed-legislation"; special sessions
  have their own pages, not read). fetch.py's `veto_messages()` reads the index, a year's page until the PDF is posted
  (after the governor's last day, in May), then the PDF once, into data/ga/vetoes/<year>.txt; convert.py's
  `veto_messages()` splits it at "VETO n" (each ends "I VETO HOUSE BILL 308.") and leaves the signing statements out.
  All 45 vetoes of 2023-26 matched on 2026-11-22 (2023: 14, 2024: 12, 2025: 7, 2026: 12). Shows after the next download.
- **Committee agendas (looked into 2026-11-22; none read):** the meeting schedule is only on www.legis.ga.gov, whose
- **House committee agendas, from the Daily Report (built 2026-11-22; `states/ga/daily.py`, run by fetch.py):** the House
  Budget & Research Office's Daily Report is a public PDF under www.legis.ga.gov/api/document/docs/default-source/
  house-budget-and-research-office-document-library/2026-daily-report/ld24_wed_feb_25_2026.pdf (no token: the document
  path answers anyone, as bill texts and floor calendars do), one per legislative day, posted that afternoon (the Internet
  Archive caught 2022's LD1 at 4 p.m.). Its last page, "Committee Meeting Schedule", lists the House's meetings of the next
  day (the days to the next legislative day after a long break: LD5 of 2026 listed Jan 20-23), each with time, room and,
  in 2026's reports, a link to its agenda PDF (284 of 321 meetings in 2026; 2025's reports had no links). Its first page
  says when the House meets next ("reconvene for its 25th Legislative Day on Thursday, February 26"), so the next report's
  name is known but for its spelling (2025: "thurs", "thur", "march", "feb_03" or "mar_3", and LD1-2 as
  "2025-daily-report-ld-1.pdf"; 2026: "thu", always two-digit days; 2025's folder was "daily-report-2025"). There's no
  listing: the office's page is drawn from the gated API, so names are tried, the last spelling first, at most 8 a run
  (4 once the folder is known), and a day's report not before noon. In a test walk from LD1 of 2026, all 40 reports were
  found with 51 requests. Agenda PDFs are read from the report's own links (their names are staff folders and free text:
  "Retirement/Higher Education Meeting Notice 03.05.26.pdf", "Juvenile Justice/Committee Agenda 3.5.2026.pdf" for Public
  and Community Health, so they can't be guessed), with pdftohtml -xml (which keeps each row's links and place on the
  page) and pdftotext; again every 6 hours until the meeting (agendas change). Each run: 0-4 report requests and one per
  upcoming agenda (about 5-20 in session), 2 seconds apart; nothing between mid-April and the second Monday of January.
  `agendas()` in convert.py: a bill named on an agenda gets ["House Ways & Means", "2026-03-05T13:00:00"]; a full
  committee's meeting whose agenda names no bills ("TBD", the Rules Committee's notices) or that has none is given to every
  bill now in that House committee with kind "meets" (as Mississippi's House); subcommittee meetings only name bills.
  Schedule names are matched to the bills' committees ignoring case, "&"/"and" and the report's typos ("PUBLIC SAFTEY",
  "JUDCIARY": difflib at 0.88); "CANCELED:" rows are dropped. Tested on 2026-03-04's report as of March 5: 16 meetings, 16
  agendas, 47 bills named, all records. Gaps: the Senate (no schedule outside the gated API; its press office announces
  only interim meetings), meetings on the first legislative day after a committee day (no report lists them: LD27's report
  lists March 5, a committee day, not LD28's March 6), and meetings or agendas added after the report.
  **Not yet seen working from GitHub's runners:** the check below found www.legis.ga.gov timing out from a runner on
  2026-11-22 (all tests here were run from the owner's computer). A run that can't connect stops after one request
  (`Unreachable`) and keeps the last copy. If the runners can't reach it, that may be the server refusing cloud addresses:
  don't route around it (another host, a proxy); ask the owner.
  The Digital Library of Georgia (dlg.usg.edu, the University System's) archives the Daily Report too, months later (March
  2024's were there by June 2024; 2026-02-25's first seen in October): no use for upcoming meetings.
- **Committee agendas (looked into 2026-11-22, before the Daily Report was found):** the meeting schedule is only on www.legis.ga.gov, whose
  API (/api/meetings?startDate=...&endDate=...) answers 401 without a token that the site's script makes from a key
  hidden in its code (/api/authentication/token?key=<SHA-512 of an embedded secret>). That's a deliberate gate on
  automated access, so it isn't used (the owner's rule: don't work around a block). The SOAP web services
  (webservices.legis.ga.gov) have no meetings or agendas (Committees has only committees and members; no Meetings,
  Calendar, Schedule or Agenda service), and the old chamber sites (www.house.ga.gov, www.senate.ga.gov) don't answer.
  The gated schedule is still not used; the Daily Report (above) covers the House. Asking the web staff for API access or a feed would add the Senate.
  Checked again 2026-11-22 from a GitHub Actions runner (a throwaway workflow on a branch since deleted): www.house.ga.gov,
  www.senate.ga.gov (robots.txt and pages, http and https) and www.legis.ga.gov all timed out on connecting, so GitHub's
  runners can't reach any of them. The chamber sites are retired anyway: the Internet Archive shows www.house.ga.gov
  redirecting to www.legis.ga.gov/house since January 2025 and www.senate.ga.gov serving a bare IIS page in August 2026,
  then 404. No direct source is left.
  Open States (looked into 2026-11-22, not used: the owner's decision): its v3 /events had 6 Georgia meetings
  (November 17-23, 2026, interim study committees and Senate Urban Affairs), none with agenda items or bills; their
  source is www.legis.ga.gov/schedule/all, the same gated schedule. The API returns only recent and upcoming events
  (none before about November 2026 for any state tried, CA and NY included), and events carry no "created" time, so how
  far ahead meetings appear and how many name bills can only be learned by polling it during a session.
- **The next session's bills (2026-11-22):** from November of an even year `main()` also reads the next session once the Session service lists it (GetSessions; 2027-2028 not listed on 2026-11-22), one list request a run; its folder is made only when the list has an HB or SB (bills are prefiled after the general election), `sessions()` shows a session after the current one from its first bill (others need 100), and a session that hasn't convened (`begun()`: the second Monday of January) never marks Georgia incomplete.
