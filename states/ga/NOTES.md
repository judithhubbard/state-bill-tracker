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
- **Committee agendas (looked into 2026-11-22; none read):** the meeting schedule is only on www.legis.ga.gov, whose
  API (/api/meetings?startDate=...&endDate=...) answers 401 without a token that the site's script makes from a key
  hidden in its code (/api/authentication/token?key=<SHA-512 of an embedded secret>). That's a deliberate gate on
  automated access, so it isn't used (the owner's rule: don't work around a block). The SOAP web services
  (webservices.legis.ga.gov) have no meetings or agendas (Committees has only committees and members; no Meetings,
  Calendar, Schedule or Agenda service), and the old chamber sites (www.house.ga.gov, www.senate.ga.gov) don't answer.
  `agendas()` stays empty. Asking the Legislature's web staff for API access or a feed would be the way in.
- **The next session's bills (2026-11-22):** from November of an even year `main()` also reads the next session once the Session service lists it (GetSessions; 2027-2028 not listed on 2026-11-22), one list request a run; its folder is made only when the list has an HB or SB (bills are prefiled after the general election), `sessions()` shows a session after the current one from its first bill (others need 100), and a session that hasn't convened (`begun()`: the second Monday of January) never marks Georgia incomplete.
