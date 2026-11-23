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

- **Committee agendas (2026-11-22):** `agendas()` in states/co/fetch.py runs first in each full run (before the bills,
  so the time limit never cuts it off) and writes data/co/<year>/agendas.json; `agendas()` in convert.py reads it and
  keeps meetings from today on. Source: leg.colorado.gov's own pages (robots.txt allows them; it bars only /house/calendar,
  /senate/calendar, journals and file downloads, none read here), three seconds apart like the rest: /schedule (today's
  meetings), /committees?sess=<year>a and each committee's page, whose "Upcoming Schedule" links its next meetings'
  agendas (/agenda/committee/<id>); each agenda page gives the committee ("Senate Local Government & Housing Agenda"),
  the day ("Thu Mar 12th, 2026"), the time ("1:30 PM | SCR 357"; "Upon Adjournment" is T00:00:00) and the bills
  (`<span class='bill-num-tag'>SB26-105</span>`, read as SB105). Meetings from yesterday to three weeks ahead; agendas
  naming "canceled" or "postponed" in their heading are left out; year-round committees are named "Joint ...". About
  40-60 requests a run in session (2-3 minutes). Only January to June 20 (`finished()`); otherwise it writes {}. A 403,
  406, 429 or bot challenge stops only the agendas (`page_quietly()`, never `refused()`), keeping the last file.
  Tested 2026-11-22 against archived session pages (web.archive.org copies of the 2026 schedule, the House Agriculture
  committee page of 2026-03-12 and the Senate Local Government agenda of 2026-03-12: SB105, SB98 matched the records)
  and live against the interim pages (16 meetings, no bills). Untested against a live session: whether committee pages
  list every upcoming meeting (the March copy listed two per committee, about a week), and the canceled wording. The
  schedule's week view is a POST with a CSRF token (it answered 500 between sessions) and isn't used.
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
- This year's session (or a later one) is shown from its first bill (`sessions()` in convert.py, 2026-11-22; older ones
  need more than 300), so 2027 shows from the day bills are introduced; the bill search had no "2027 Regular Session" on
  2026-11-22.
- (2026-11-22) Emails: a member page's first "mailto:" was sometimes its "share by email" link ("mailto:?body=https..."), saved as the email in 2024's and 2025's members.json; fetch.py now takes only an address, and contacts.py skips the old ones (data_check's "emails that aren't addresses" FAIL).
- **Photos (2026-11-22):** leg.colorado.gov's member photos are served from /rails/active_storage/, which its robots.txt
  disallows, so photos.py no longer asks for or copies them (it did before, from Open States' links). Light ones (13)
  stay linked from earlier answers; the heavy originals (1.5-5.7 MB, 32) are left out, and Ballotpedia's (17) remain. Asking
  the Legislature (or an allowed address for the photos) would bring the rest back.
- **Committee votes (2026-11-23):** "Lay Over" motions decide nothing and aren't kept; a "Postpone Indefinitely" vote is
  against the bill, so its tally and names are turned round (it read "Approved by").
