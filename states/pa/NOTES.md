# Pennsylvania

Moved from CLAUDE.md (2026-11-19). Shared conventions, the data traps list and the site's code notes stay there.

- **Pennsylvania (started 2026-10-31):** `python3 states/pa/fetch.py` downloads each session's bill history file
  (https://www.palegis.us/data, a zipped XML refreshed hourly: sponsors with house, district and party; actions with
  chamber, verb, committee and date) into data/pa/billhistory_<year>_0.zip, then, at one request a second, each voted-on
  bill's page and its roll calls (floor and committee, member by member; committee ones carry a "Brief Description",
  used as "What it does"). The first full copy takes several hours. robots.txt limits only an accessibility scanner.
  `states/pa/convert.py`: "Third consideration and final passage" is a passage ("Vote on final passage reconsidered"
  undoes it); "First consideration" puts a bill on the floor; most bills are re-committed to Appropriations before the
  final vote; "Presented to the Governor", "Approved by the Governor", "Act No. 28 of 2025" (`STATE.lawWord` = "Act").
  An action's date comes from its wording: "(Remarks see House Journal ...)" lines are dated when the remarks were filed.
  Titles are the co-sponsorship memo's ("Mandating Cursive Handwriting"), with the official title as the summary.
  Joint resolutions proposing constitutional amendments are bills here (HB/SB) and never go to the governor
  (`STATE.amendments`, topic "const"). Earlier sessions linked by the memo's "(Former HB 1934)", else the same official
  title and prime sponsor. Legislators (`contacts.py`): the member and committee feeds (phones, offices; majority chairs);
  emails from Open States (owner's decision 2026-10-31: the Senate's pages hide them behind an anti-collection script).
  The 2,572 municipalities by district (`towns.py`); townships that share a name carry their county. Full-time
  Legislature (`floorVotesEnd: false`); the session ends November 30 of the even year; governor 10 days (calendar days: Art. IV, sec. 15
  excepts no Sundays), or 30 days after the session ends for a bill still waiting then.
- **"What it does" from the House Calendar (2026-11-22, going forward):** the House's floor calendars
  (/house/session/calendars, its Tabled Bill Calendar ?c=22 and Uncontested Calendar ?c=23; each links only its current
  calendar, /house/session/calendars/view?CalendarId=11117&ext=HTML) end each bill's row with a staff sentence ("This
  bill bans paraquat."; resolutions have none). Neutral staff wording, unlike the co-sponsorship memos' text (not used:
  the owner's decision). `calendars()` in fetch.py looks at the three lists every 6 hours and reads each new calendar
  once (4-6 requests a session day) into data/pa/<year>/calendar_descriptions.json ({bill: [calendar day, sentence]}, each
  bill's latest; calendars_read.json remembers which were read). No archive of past calendars was found, so bills only
  get one once they're on a calendar from now on. convert.py uses it before the committee roll call's "Brief
  Description" ("From the House Calendar's description of the bill."). Either is left out when it only says the title
  again (`says_title()`: every word of it in the title, the committee's often being the memo's title, "Save Women's Sports
  Act"; data_check failed on 10 such in 2025-26). On 2026-11-22: 3 calendars, 306 bills (all of them already had a
  committee description, so coverage didn't rise: 2025-26 has 940 of 4,184 bills, 22.5%, after dropping 29 title-only
  descriptions; 263 now read from the calendar).
- **Committee agendas (2026-11-22):** `agendas()` in fetch.py reads each chamber's committee meeting RSS feed
  (https://www.palegis.us/house/rss/committee/schedule and /senate/rss/committee/schedule; two requests a run, before the
  roll calls) into data/pa/<session>/agendas.json, meetings from yesterday to three weeks ahead. Each item has
  `<parss:MeetingDate>` (MM/DD/YYYY), `<parss:MeetingTime>` ("9:30 AM", or "Call of Chair"/"Off the Floor": no time),
  `<parss:Committee>` ("HOUSE HEALTH"; commissions without a house get the feed's) and `<parss:Bills>` ("HB1964,HB2131,HR403",
  the records' own numbers; only HB/SB kept). Items whose title or description says canceled or postponed are left out.
  A feed that fails keeps the last file; convert.py's `agendas()` keeps meetings from today on. Tested against an archived
  House feed of 2026-03-20 (27 bills on 24 meetings, all matched to 2025-26 records); untested against live session
  feeds and against the Senate feed with bills (the same format, by its schema). Joint hearings name one committee.
- **Senate roll calls kept out by the House's (fixed 2026-11-22):** the House and the Senate number their floor roll calls
  alike (`rcNum=202` in each), and fetch.py named each file by the link's query alone, so whichever house's was saved first
  kept the other's out: 397 Senate and 57 House floor roll calls of 2023-24 and 305 and 66 of 2025-26 were never saved, and
  the Senate's split votes showed tallies without names (26% and 36% named; the House 96%). New files start with the house
  (`rc_key()`: "senate_...", "house_..."); the old files are matched by the link they hold, and each run reads the roll
  calls that bill pages already read list but that aren't saved, without reading the bill page again. data_check.py's
  "split floor votes naming members" check compares the houses.
- **Next session (2026-11-22):** bills are introduced only once a session convenes (January 5, 2027); its bill history
  file answers 404 until then. From January fetch.py asks for it every run; a missing or bill-less file doesn't hold
  Pennsylvania back until March 1, and the session just ended is read again until February 1.
- **Committee roll calls (2026-11-23):** only the committee's votes on the bill (report, re-report, re-refer; the
  Senate's motions are blank) are kept: votes on amendments, tabling and other motions read "Approved by" or "Voted down in"
  the committee (HB 181 of 2023: "Voted down ... 9-12" was an amendment, the day the committee reported the bill 11-10;
  about 500 a session).
