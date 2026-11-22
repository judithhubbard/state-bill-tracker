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
- **Floor votes missing from the site (fixed 2026-11-22):** the live 2026 page had 1,226 committee votes and no floor vote.
  fetch.py read votes in id order, committee votes ("c...") before floor votes ("f..."), and saved a vote only when its page
  had tallies or members' votes it could read. About 900 committee voice votes ("Pass without objection", every member
  "(Voice Vote)", no tallies; `vote_members()` didn't read the hyphenated "voice-vote" tag) were never saved, so every run
  read the same ones again for its whole 45 minutes and never reached a floor vote: GitHub's copy had 1,733 votes of 2026,
  all committee votes, and none of 2023-2025 (a copy made on the owner's computer had them all, so local builds looked
  right). Now floor votes come first, every year's, newest year first, and a voice vote is saved marked `voice` (left out
  by convert.py: no tallies, no member's vote). At about 850 votes a run, the floor votes (about 1,600-1,800 a year) take
  about two runs a year. data_check.py fails on a session where under a fifth of the bills that passed a house have a
  floor vote.
