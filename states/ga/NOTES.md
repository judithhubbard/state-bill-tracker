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
  API (/api/meetings?startDate=...&endDate=...) answers 401 without a token that the site's script makes from a key
  hidden in its code (/api/authentication/token?key=<SHA-512 of an embedded secret>). That's a deliberate gate on
  automated access, so it isn't used (the owner's rule: don't work around a block). The SOAP web services
  (webservices.legis.ga.gov) have no meetings or agendas (Committees has only committees and members; no Meetings,
  Calendar, Schedule or Agenda service), and the old chamber sites (www.house.ga.gov, www.senate.ga.gov) don't answer.
  `agendas()` stays empty. Asking the Legislature's web staff for API access or a feed would be the way in.
