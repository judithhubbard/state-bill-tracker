# Alaska

Moved from CLAUDE.md (2026-11-19). Shared conventions, the data traps list and the site's code notes stay there.

- **Alaska (built 2026-11-08):** `python3 states/ak/fetch.py` reads the
  Legislature's BASIS public service (see its docstring) into data/ak/<first year>/, a two-year Legislature a page (the 34th
  is 2025-26; `YEARS = 2`); `states/ak/contacts.py` builds the contacts from its members and committees files (no web pages).
  Special sessions belong to the Legislature: their bills (HB 1001 on) are shown with the rest, and regular bills can pass
  in them ("Chapter 1, FSSLA 2025"). `states/ak/convert.py` reads the action codes: 001 first reading with 091 the
  committees in order; 002 "L&C RPT ..." a committee's report (approved), followed by 063 each member's recommendation (DP
  do pass, NR, AM amend, DNP), shown as one line; a report moves the bill to the next committee in its list (usually with no
  "REFERRED TO" line; the record's Referrals keep the final list) and after the last to the Rules Committee (stage 0, "Rules",
  until 080 "RULES TO CALENDAR"); 020/024 the passage; 128, and 125 when it names a passage or concurrence, undoes the house's
  last vote; 083 sent back with the other house's changes, then 026 concur (027 refused: not passed both houses, HB 120 of
  2023-24), or a conference report both houses adopt (032/058; 074 failed); 090 "RETURN TO (S), TRANSMIT TO GOVERNOR NEXT" the
  second house passed it unchanged; 033 transmitted; 034/036/129 a chapter; 038 vetoed; 040/039 override in joint session.
  The governor's lines are entered in the journal weeks later: their own wording dates them (`text_date()`). Some histories
  stop before the governor (12 laws of 2024): the status text ("CHAPTER 38 SLA 24") decides laws and vetoes too, and the
  record's Vetoed flag stays set after an override. Floor roll calls member by member, on the bill's own questions
  (`floor_question()`: passage, concurrence, conference report, override; not amendments or effective-date clauses);
  committees have no roll calls. Seats: Senate districts are letters A-T, numbered 1-20 in seat ids ("S:1" is District A,
  `P.senate_number()`) and named by data/ak/district_names.json; tracker.html's `DNUM()` shows a one-letter name as
  "District A". House "H:1".."H:40"; each Senate district is two House districts. Members' code ("FIE") ties votes to seats;
  members who left are "H?Tilton"; a member who changed name has two active records (Robyn Niayuq Burke, now Frier: the
  "Name Changed" record is left out of contacts, its code kept for votes). Party "N" (nonpartisan or undeclared) is shown
  as "Independent". Bipartisan coalitions run both houses (legislatures.json `note`; seat counts show Republican majorities,
  so balance.py's "unified" and the front page's dots would mislead: fix before adding Alaska there). Titles are the short
  titles, sentence-cased with abbreviations spelled out (`titled()`); the summary is the official title. No "What it does"
  (decided 2026-11-08): the only plain account is the sponsor statement (PDF), an advocate's case for the bill as introduced
  (HB 57 of 2025's is about phones in classrooms; the law became the education funding bill), with letterheads and staff
  contacts, and on about half the bills. Constitutional amendments (HJR/SJR "Proposing amendments to the Constitution"):
  two-thirds of each house's members, then the voters (`amendmentOnce`); none passed both houses in 2023-26. Governor 15
  days, Sundays excepted, in session, 20 after adjournment, counted from transmittal (often months after passage, so
  `passedBothBy` is the year's end, as New York's); overrides take two-thirds of the 60 legislators in joint session, or
  three-fourths for appropriations (legislatures.json "2/3", per house; the note says it). Sessions: the third Tuesday of
  January, 121 days (`STATE.dated` holds each year's last day: add each year's). Totals, matching the chapter numbering
  (1-N, none missing) and the news: 2023 26 chapters SLA 23 and 2 FSSLA 23, 3 vetoes; 2024 61 chapters, 9 vetoes; 2025 25
  chapters and 1 FSSLA 25, 9 vetoes (HB 57 and SB 183 overridden); 2026 61 chapters, 23 vetoes (HB 195 and HB 314
  overridden): 32 in the 34th Legislature, a record (31 reported by August 27, then HB 10 on August 31). Places (`towns.py`,
  run once): cities, Census-designated places, boroughs and census areas; a district counts for a place when it's 0.5% of
  the place's land or the place holds most of the district (Anchorage's urban districts). Leaders from the members file's
  comments; the 35th Legislature (January 2027) chooses new ones, and a new governor takes office December 7, 2026 (add to
  `GOVERNORS` and legislatures.json). The governor's phone and contact page haven't been checked by the owner.
- A Legislature of this year or later is shown from its first bill (`sessions()` in convert.py, 2026-11-22; older ones
  need more than 100): the 35th's prefiled bills (BASIS answers "Invalid Session Number" for session=35 on 2026-11-22;
  the first prefile release is the second Friday of January) appear when fetch.py starts reading it on January 1.
