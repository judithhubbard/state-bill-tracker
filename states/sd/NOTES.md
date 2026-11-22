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
- **Veto letters (2026-11-22):** each "Vetoed by the Governor" action names the day's House or Senate Journal
  (DocumentId), which prints the governor's letter; fetch.py's `veto_journals()` reads that journal once
  (Documents/<id>.html) into data/sd/<year>/journals/, and convert.py's `veto_message()` takes the letter whose first
  paragraphs name the bill and the veto ("I respectfully return to you House Bill 1132 with my VETO"), from "Dear ..." to
  "Sincerely,". All four vetoes of 2025-26 (HB 1132, HB 1169, HB 1077, HB 1138) read on 2026-11-22 (2024 had none: the
  Legislature's VetoedByGovernor list is empty too). Shows after the next download.
- **Committee agendas (2026-11-22):** `agendas()` in states/sd/fetch.py, run for this year's session after the bills: for
  each committee in committees.json other than the whole House and Senate (about 32), the API's
  `SessionCommittees/Documents/<SessionCommitteeId>?Type=3&Type=5` (what the committee page's Agendas tab reads: each
  meeting's agenda DocumentId, DocumentDate with its offset, "2026-01-28T10:00:00-06:00", and NoMeeting for a canceled
  one); for each agenda from yesterday to three weeks ahead, its text, `Documents/<id>.html`, whose bills read "HB 1115"
  (sometimes with a line break between). Written to data/sd/<year>/agendas.json; `agendas()` in convert.py keeps today's
  and later. Committee names drop "Committee on " ("House Appropriations"). Any failure keeps the last copy and never marks
  the state incomplete. Tested against the 2026 House Judiciary agendas (1/16 and 1/28: HB 1055; HB 1115, 1126, 1132,
  1107) with the date set back; the live run's timing in session is untested (agendas are posted a few days ahead). Not
  used: `Documents/Schedule` (the site's upcoming-meetings list: agendas' DocumentIds with SessionCommitteeId; in
  November only interim meetings), which could replace the 32 committee requests once its session shape is seen.
- **Contacts after the election (2026-11-22):** the API's 2026 member list (`SessionMembers/Session/71`) lost every
  member's CapitolPhone and EmailState after the November 2026 election (the 2027 session's list, 174, has them for the
  members elected), and the next download's contacts had no email or phone. Now fetch.py keeps a refreshed list's emptied
  fields from the last copy, and saves the next session's members (data/sd/members_next.json); contacts.py fills a
  missing email from states/sd/emails_2026.json (the API's emails as downloaded on 2026-11-01, all 105 members: those not
  re-elected sit until January), else the next session's list (same PersonId), and a missing phone with the member's
  house's switchboard (`SWITCHBOARD`: every member's Capitol phone was one of the two). For 2027, check that list keeps
  its emails through the session.
- **Next session (2026-11-22):** the API lists next year's session from about November (2027's, SessionId 174, with its
  members and committees; no bills on 2026-11-22); fetch.py reads it every run and saves it once it has a bill, and an
  empty list before the session convenes never holds the state back. convert.py's `sessions()` shows this year's and
  next year's session from its first bill (past years still need over 100).
- **Floor calendars (2026-11-22, states/floorcal.py):** `agendas()` in fetch.py no longer skips the two FullBody
  "committees" (House of Representatives, SessionCommitteeId 1266 in 2026; Senate 1288): their documents are each floor
  day's calendar, posted before the day (two more list requests a run, plus one per calendar in the window).
  `floor_bills()` keeps the bills under "SECOND READING OF HOUSE/SENATE BILLS AND JOINT RESOLUTIONS" and "SECOND READING
  AND CONSIDERATION OF CONSENT CALENDAR ITEMS" (South Dakota's passage vote is on second reading), not committee reports,
  motions, commemorations or conferences; they go in agendas.json as ["House floor", when, "floor"], a vote set for that
  day (91% of Senate and 93% of House listings had a vote that day or the next; the rest were tabled or deferred).
  Tested on nine saved calendars of Feb 23-Mar 2, 2026 (127 bills, all records' numbers but SJR 508, a joint resolution
  the converter leaves out).
