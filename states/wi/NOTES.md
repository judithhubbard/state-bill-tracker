# Wisconsin

Moved from CLAUDE.md (2026-11-19). Shared conventions, the data traps list and the site's code notes stay there.

- **Wisconsin (started 2026-10-31):** `python3 states/wi/fetch.py` reads docs.legis.wisconsin.gov (see the wi-data-sources
  memory; robots.txt blocks the feeds, so changes are found from the bill lists and the journals, plus a weekly re-read):
  each bill's history, authors and the Legislative Reference Bureau's analysis ("What it does"), the roll calls member by
  member, the committee records, members and committees. The first copy takes about 6-7 hours at a request a second.
  `states/wi/convert.py` reads the history lines ("Read a third time and passed, Ayes 53, Noes 45"; the second house
  "concurred in"; "Report correctly enrolled"; "Report approved by the Governor ... 2023 Wisconsin Act 123", with partial
  vetoes; bills pending at the last floor period "Failed to pass pursuant to Senate Joint Resolution 1"). The lower house
  is the Assembly (`LOWER = "A"`, seats "A:82"). Senate roll calls give names in capitals cut to 14 characters
  (`members_index()`). The last general-business floor period's date is `STATE.dated` (add each session's). The Assembly
  Committee on Rules and the Committee on Senate Organization schedule floor votes. Cities and villages crossing county
  lines are one entry (`towns.py`); towns that share a name carry their county.
- **Committee agendas (2026-11-22):** `agendas()` in states/wi/fetch.py (first in each full run) reads the Legislature's
  committee schedule, https://committeeschedule.legis.wisconsin.gov/ (no robots.txt; the docs site's robots.txt, which
  bars /feed/, doesn't cover it), one page: the address its stub page's script loads,
  `/?StartDate=<today>&CommitteeID=-1&CommItemVisibleName=-1&TopicID=-1&ViewType=listWeek&ReloadCache=True` (about 2 MB),
  which carries every meeting of the biennium as calendar events in its script (`parse_schedule()`: title "Judiciary and
  Public Safety (Senate)", start, classNames with "canceledMtg" when canceled, eItems "SB6; SB25"). Public hearings and
  executive sessions from yesterday to three weeks ahead go into data/wi/<session>/agendas.json ("Senate Judiciary and
  Public Safety", "Assembly Rules", "Joint Finance"; Legislative Council study committees "Joint ..."); `agendas()` in
  convert.py keeps meetings from today on. A failure keeps the last file. Tested 2026-11-22 on the page as served that
  day (840 meetings of 2025-26 listed, 22 canceled left out): 2026-02-02 to 02-23 gave 93 meetings and 283 bills, every
  one matched a record; live, no meetings ahead. Untested: the page in January 2027 (whether StartDate in the new
  biennium lists 2027-28's meetings), and an "eItems" naming a substitute amendment rather than the bill.
- **Next session (2026-11-22):** docs.legis answers 404 for /2027/ (bills, legislators, committees) on 2026-11-22; the
  session is read from January (it convenes January 4, 2027). Its missing list, members and committees don't hold
  Wisconsin back until April 1 (bill pages never read still do), and convert.py's `sessions()` shows it from its first
  bill (past sessions still need over 1,000).
