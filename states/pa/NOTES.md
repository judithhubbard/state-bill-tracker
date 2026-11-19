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
  Legislature (`floorVotesEnd: false`); the session ends November 30 of the even year; governor 10 days, Sundays excepted.
