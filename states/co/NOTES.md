# Colorado

Moved from CLAUDE.md (2026-11-19). Shared conventions, the data traps list and the site's code notes stay there.

- **Colorado (built 2026-11-07):** `python3 states/co/fetch.py` reads leg.colorado.gov's pages (no API; three seconds
  apart, since it answers "too many requests" faster; robots.txt bars the file downloads, which aren't read): each bill's
  page (history, sponsors by slug, committees, subjects, the Legislative Council Staff summary, session laws), every
  committee and floor vote member by member, members and committees; `states/co/contacts.py` runs after it. Members'
  votes don't hold the state off the site: they fill in run by run. `states/co/convert.py`: history lines name their
  house ("House Committee on Finance Refer Amended to Appropriations": approved and sent on; "Postpone Indefinitely":
  killed; "Lay Over": held; "Third Reading Passed": the passage); the page lists them newest first but not always in
  order (sorted by day). The bill's status ("Became Law", "Did Not Become Law") decides laws and vetoes, which match it
  exactly; an override needs both houses (SB 25-086: only the Senate overrode). Floor votes count only the bill's own
  motions (third reading "Bill", Concur, Repass, Adopt, Override), not amendments. Concurrent resolutions (constitutional
  amendments) aren't downloaded. Leaders are named only for the current year: past years' member pages show today's
  positions and houses.
