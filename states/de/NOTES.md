# Delaware

Moved from CLAUDE.md (2026-11-19). Shared conventions, the data traps list and the site's code notes stay there.

- **Delaware (built 2026-11-08):** `python3 states/de/fetch.py` reads
  legis.delaware.gov's own JSON and pages (no robots.txt; see its docstring) into data/de/<first year>/; `python3
  states/de/contacts.py` (every General Assembly; add it to states.json's run after fetch.py) builds the contacts. A page per
  two-year General Assembly (`YEARS = 2`; the 153rd is 2025-26): sessions run from the second Tuesday of January to June 30
  each year, bill numbers run through both years and bills stay alive until the General Assembly ends; the next one's
  members take office at the November election (fetch.py lists the 154th from then). `states/de/convert.py`: one record
  per bill; a substitute ("HS 1 for HB 457", even "SS 2 for SB 100") keeps the bill's number and gives it its title,
  synopsis, sponsors and roll calls. The original's history copies its substitutes' lines ("HS 1 for HB 449 - Passed By
  House ...") under the day they were copied, so the governor's action can show twice days apart (HS 2 for HB 168 of 2023-24:
  9/30/24 and 10/2/24): the substitute's own history is used, the original's copies only for a substitute never read, and
  lines are matched by `line_key()` (an amendment's vote "Amendment SA 1 to SS 2 - Passed By Senate ..." isn't the bill's).
  History wording: "Introduced and Assigned to X Committee in House"; "(Re-)Assigned to X" (the second house, or
  Appropriations/Finance); "Reported Out of Committee (X) in House with 7 Favorable, 7 On Its Merits, 1 Unfavorable" (a
  committee releases a bill when most members sign, any of the three; committee votes are those counts, favorable plus
  merits as yes, no names); "Tabled in Committee" (`heldAction`); "Motion to Release Failed"; "Passed By House. Votes: 39
  YES 1 NO 1 ABSENT" (every passage is a roll call, matched member by member by short name within the house); "Defeated By
  ..." (with "Reason Taken" a motion); "Reconsidered in"/"Roll Call Rescinded in" undo the house's last vote; "Stricken";
  "Signed by Governor", "Enact w/o Sign by Governor", "Vetoed by Governor", "Veto Override Passed in House", "Enacted into
  Law", "Line-Item Veto - See Governor's Advisory #46". Passed both houses: both passed and, if the second adopted an
  amendment, the first passed it again. The list's status decides laws and vetoes too, and agrees bill for bill. Chapters
  (`Volume:Chapter` "85:341") number 1-N with none missing once the constitutional amendments, which get chapters too, are
  counted: 2023-24 (Volume 84) 524 laws + 7 amendment passages = chapters 1-531, 1 veto standing (HB 140, End of Life
  Options) and 1 overridden (HB 282); 2025-26 (Volume 85, to date) 539 laws + 11 amendment passages = 1-550, 4 vetoes standing
  (HB 393, SB 231, SB 279, HS 1 for HB 329) and 2 overridden (SB 63, SB 75). The records don't show when a bill is presented
  to the governor (often months after passing), so there's no stage 4 and no deadline estimate. Constitutional amendments
  are bills ("AN ACT PROPOSING ..." first passage, "AN ACT CONCURRING IN ..." second, two-thirds of each house's members in
  two General Assemblies), tagged "const", never the governor and never the voters: `STATE.amendmentFinal` reads the title,
  and `STATE.amendmentDone` (added 2026-11-08, read by tracker.html's pipeline counts, status line and odds line) replaces
  "went to the voters". Titles: the named act from the short title when it has one ("Fairness in Girls' Sports Act"), else
  the long title's "relating to" subject, put back in sentence case with the synopsis's spelling of names (`recase()`:
  three-capital-word phrases and acronyms only); the summary is the long title. "What it does" is the synopsis (the bill's
  own explanation, printed at its end, not part of the law). Seats "S:1".."S:21", "H:1".."H:41" (single-member, separate
  maps); a seat goes to the member who voted last in it, and members who left are "H?Parker Selby" (`seats()`); the member
  list has no party for Ronald Gray and Lyndon Yearick, taken from their pages' headings (`party_of()`). Contacts: members
  file, members' pages (Legislative Hall phone, email; a number three or more members list is labelled "Caucus office";
  former members' pages lose them), committees with chairs. Leaders (`LEADERS`): Speaker Melissa Minor-Brown, President Pro
  Tempore David Sokola (the Lieutenant Governor presides); the 154th chooses its own in January 2027. Governor Matt Meyer
  (D) since January 21, 2025; 10 days (Sundays excepted) after presentment, 30 after final adjournment (pocket veto);
  line-item vetoes on appropriations; override three-fifths of each house's members. The governor's phones and contact page
  are from governor.delaware.gov/contact/ (checked by program 2026-11-08, not by the owner). Places (`towns.py`, run once):
  cities, towns, Census-designated places and counties, separate Senate and House lists.
- **Committee agendas (2026-11-22):** `agendas()` in states/de/fetch.py (every full run, before the bills) reads the
  Committee Meetings page's grid (POST /json/CommitteeMeetings/GetUpcomingCommitteeMeetings; an empty body when nothing
  is scheduled) and, for each meeting from yesterday to three weeks ahead that isn't "Cancelled" (or postponed), its
  agenda (POST /json/MeetingNotice/GetCommitteeMeetingItems?committeeMeetingId=N: one request a meeting; items with a
  LegislationId and a display code "SB 311", "HS 1 for HB 457 w/ HA 1", which gives the bill's number; minutes and other
  items are left out), into data/de/<first year>/agendas.json for the meeting's Assembly ({"SB311": [["Senate
  Agriculture", "2026-05-20T11:00:00"]]}; times are local, "5/20/26 11:00 AM"). A joint meeting of a Senate and a House
  committee (SharedCommitteeName) names the committee each bill is assigned to. `agendas()` in convert.py keeps meetings
  from today on. Tested with past meetings in the same format (each committee page's GetCommitteePastMeetings grid,
  same fields as the upcoming grid): Senate Agriculture and House Judiciary in May and June 2026, 6 meetings, 16 bills,
  all matching 2025-26 records. The upcoming grid itself was empty on 2026-11-22, so its date format is assumed to be
  the past grid's (the run prints how many meeting times it didn't understand). A failed request keeps the last files.
