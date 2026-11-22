# Ohio

Moved from CLAUDE.md (2026-11-19). Shared conventions, the data traps list and the site's code notes stay there.

- **Ohio (started 2026-10-31):** `python3 states/oh/fetch.py` reads the Legislative Service Commission's API
  (https://search-prod.lis.state.oh.us/api/v2/, JSON; see the oh-data-sources memory). legislature.ohio.gov,
  ohiohouse.gov, ohiosenate.gov and ohiosos.gov all answer automated requests with 403, so (decided 2026-10-31)
  everything comes from the API except legislators' emails and page links, which come from Open States' public-domain
  file (data/oh/openstates_people.csv; it has no phones), named as the source in "About this data". Sessions are
  General Assemblies (`assembly_of()`: 2025 -> 136). Each bill's versions (read again when its entry in the
  legislation list changes, its actions change, or it has passed both houses and waits on the governor: the list's
  `revno` doesn't change on enrollment or delivery, so HB 13, HB 397 and SB 214, sent 2026-11-17, were missed until
  2026-11-19) and actions (the current General Assembly's every run; about 1,500 requests, no change
  feed) go into data/oh/<session>/bills/<HB96>.json. Actions are structured, with each vote's members: committee and
  floor votes are member by member. The governor's signature is the enrolled version's governor_signed_date, not an
  action; a few have none (HB 110 of the 134th), so in a finished General Assembly an enrolled bill without "Veto
  receipt" is law; while one runs, a "Line item veto receipt" or the enrolled version's effective date is (SB 152 and
  HB 479 of the 136th had neither a signing date; a future effective date is dated the day it was sent, and a "sent" date
  after the effective date, SB 152's 2026-06-12, is dropped). "Line item veto receipt" stays as written (a law, part vetoed). "Reported - Re-referred to X" is a
  referral to X. Each house's Rules and Reference Committee schedules floor votes. "What it does" is the long title's
  purpose clause, after the last list of sections, its verb turned into "Modifies ..." (`purpose()`, `texts.py`).
  Full-time Legislature (`floorVotesEnd: false`); governor 10 days, Sundays excepted. Separate Senate (33) and House
  (99) districts by city, village or county (`states/oh/towns.py`). The governor's phone and address are from the
  governor's contact page, checked by the owner 2026-10-31 (governor.ohio.gov answers automated requests "not found"). Built only once data/oh/incomplete is gone.
- **Next General Assembly (2026-11-22):** the API answers 500 for the 137th until it's set up, and bills are introduced
  only after it convenes (January 4, 2027), so it's read from January; until March 1 a list never read doesn't hold Ohio
  back, and its contacts wait until its legislators and committees are listed. The General Assembly just ended is read
  again until April 1 for bills still waiting on enrollment or the governor (the list's revno may not change).
