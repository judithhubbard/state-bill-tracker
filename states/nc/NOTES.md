# North Carolina

Moved from CLAUDE.md (2026-11-19). Shared conventions, the data traps list and the site's code notes stay there.

- **North Carolina (started 2026-10-31):** `python3 states/nc/fetch.py` reads ncleg.gov (see the nc-data-sources memory;
  robots.txt Crawl-delay 2): each session's bill list (RSS), each bill's page (sponsors, keywords, Public/Local, session
  law, roll-call table, history), each roll call member by member, members, committees with chairs. The first copy takes
  about 6 hours. `states/nc/convert.py` reads the history ("Ref to the Com on X, if favorable, Y": X first; "Passed 3rd
  Reading" is the passage; "Ordered Enrolled"/"Ratified" passed both houses; "Ch. SL 2025-13" a law, `STATE.lawWord`
  "Session Law"). Every Senate bill starts in the Senate Rules Committee (`STATE.gates`); both houses' Rules committees are
  called "Rules". Local bills become law when ratified, without the governor (narrow kind "place"); constitutional
  amendments are bills too ("Constitutional Amendment ..."), three-fifths, then the voters. Roll-call pages print "None"
  for an empty vote group. Emails from Open States (the pages hide them behind Cloudflare's script); members who resigned
  stay on the member list with a note. "What it does" is the Legislative Analysis Division's bill summary (neutral staff summaries,
  PDFs): fetch.py's `summaries()` runs last, in the time left, and never marks the state incomplete; it reads each heard
  bill's list (/Legislation/Bills/Summaries/<year>/<H4>; unheard bills have none) and each chosen PDF once
  (dashboard.ncleg.gov/api/Services/BillSummary/<year>/<id>; "(e3)", "(CS...)", "(CCS...)", "(sl)" in the id name the
  version), saved as text in summaries/. `states/nc/texts.py` takes the session law's summary (the conference version's
  when a law is summarized part by part, else up to 8 parts), else the newest bill summary, never an amendment's alone,
  and none when its title shares no words with the bill's current one (rewritten bills); it keeps the overview, the
  analysis when the overview is short and the effective date, without current law, tables or staff credits; the label
  names the version. Counties and places by district (`towns.py`).
- **Committee agendas (2026-11-22):** `agendas()` in fetch.py reads the Legislative Calendar's month pages
  (https://www.ncleg.gov/LegislativeCalendar/<m>/<yyyy>: this month's, and the next one's when three weeks ahead falls in
  it; Crawl-delay 2, its own fetch `calendar_page()` that never stops the run) after the bills and contacts, before the
  summaries, into data/nc/<session>/agendas.json: meetings from yesterday to three weeks ahead. Each committee event has
  its chamber label ("House: "), its committee link (/Committees/CommitteeInfo/House/21; "-- UPDATED", "-- CANCELLED"
  after the name), its time and the bills it lists (/BillLookUp/2025/H126). Canceled and postponed meetings are left out;
  non-standing committees (no chamber label) are named "Joint ..." unless their name says the house. convert.py's
  `agendas()` keeps meetings from today on and calls each house's Rules Committee "Rules", as the histories do. Tested
  against June 2025's page (141 bills on 71 meetings; 135 matched records, the other 6 confirmation and honorary
  resolutions, which aren't kept); the live page has no committee meetings now (November 2026). The current calendar
  page (/LegislativeCalendar/) only lists what's ahead; month pages were used so a meeting from yesterday still shows.
