# South Dakota

Moved from CLAUDE.md (2026-11-19). Shared conventions, the data traps list and the site's code notes stay there.

- **South Dakota (started 2026-11-01):** `python3 states/sd/fetch.py` reads the Legislature's JSON API
  (https://sdlegislature.gov/api/, the one its own pages use; no key): each regular session's bill list and action logs,
  each bill's detail (sponsors in order, subject keywords), every vote member by member (votes/<id>.json, by
  SessionMemberId), members, committees, and the Legislature's lists of bills signed and vetoed (logs.json, to check
  totals: 2026's 240 and 2 match). `states/sd/contacts.py` runs after it. `states/sd/convert.py` reads each action's
  kind (ActionId) and who acted: "Do Pass" is a committee's report when a committee acts and the house's passage when
  the whole house does (ActionCommittee.FullBody); "Deferred to the 41st legislative day" (there are 40) and tabling kill
  a bill in committee (`heldLabel`); "Reconsidered" undoes the house's earlier vote, and a new vote follows. A floor
  "Do Pass Amended" in the second house doesn't mean it changed the bill: passed both houses needs the presiding
  officers' signatures, a concurrence or a conference report adopted in both (steps with no house are the conference
  committee's own votes, "Concurred in amendments 4-2", and don't count; HB 1140 of 2024 died in conference). Topics from the subject keywords
  (`KEYWORD_TOPICS`). No summaries: the title is the act's one-line description ("Provide for ..."). Bill pages are
  addressed by the Legislature's bill id (a version's `link`). Each district elects a senator and two representatives
  (26 and 28 from subdistricts 26A/26B): seats "S:12", "H:12a"/"H:12b" (New Jersey's scheme), one district list for both
  houses. Members' phones are the House's and Senate's switchboards. One session a year from the second Tuesday of
  January (40 days in odd years, 35 in even), plus a veto day near the end of March (`vetoDay()`); each year's last
  regular day is in `STATE.dated` (add each year's). Governor 5 days, not counting Saturdays, Sundays or holidays (Art. IV, sec. 4 as amended in 2002; until 2026-11-21 the
  profile excepted only Sundays), in session; 15 calendar days after the last regular day (counted from it, not from delivery).
- **Contacts after the election (2026-11-22):** the API's 2026 member list (`SessionMembers/Session/71`) lost every
  member's CapitolPhone and EmailState after the November 2026 election (the 2027 session's list, 174, has them for the
  members elected), and the next download's contacts had no email or phone. Now fetch.py keeps a refreshed list's emptied
  fields from the last copy, and saves the next session's members (data/sd/members_next.json); contacts.py fills a
  missing email from states/sd/emails_2026.json (the API's emails as downloaded on 2026-11-01, all 105 members: those not
  re-elected sit until January), else the next session's list (same PersonId), and a missing phone with the member's
  house's switchboard (`SWITCHBOARD`: every member's Capitol phone was one of the two). For 2027, check that list keeps
  its emails through the session.
