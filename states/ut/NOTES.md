# Utah

Moved from CLAUDE.md (2026-11-19). Shared conventions, the data traps list and the site's code notes stay there.

- **Utah (started 2026-11-07):** `python3 states/ut/fetch.py` reads the Legislature's developer API (glen.le.utah.gov; the
  token is the UTAH_API_TOKEN secret or ~/.utah_api_token, never printed) and members' votes from le.utah.gov's vote pages
  (robots.txt allows /DynaBill/svotes.jsp and /mtgvotes.jsp; Crawl-delay 10), 40 minutes a run until all ~12,000 are read,
  each once; `states/ut/contacts.py` runs after it (the API has current members only). Since 2025 each action has a code
  ("HPASS3"), a time, its owner (who has the bill next: "House Transportation Committee") and its vote; 2024's records are
  older (wording and a date), so `states/ut/convert.py` gives them codes from the same wording in 2025-26 and takes their
  votes and times from each bill's status page (data/ut/2024/status/). Dates come as "2026-01-19 11:07:38" or "2/18/2025
  3:38 PM" (`stamp()`). Each house's Rules Committee is a gate (`STATE.gates`): new bills start there, it sends them to
  standing committees and later decides which reach the floor. A recall after the presiding officers sign undoes it (SB
  254 of 2025), and a reconsideration voted by voice shows 0-0. The vote pages' own lists beat the API's tallies (SB 141 of
  2026: 6-0 vs 5-1). A committee's substitute, amendment and final votes on one day show as one. "What it does" is the
  General Description and Highlighted Provisions. Laws and vetoes match the Legislature's passed list bill for bill (2025:
  544 and 6; 2026: 493 and 2). One 45-day session a year from the third Tuesday of January; governor 10 days (Sundays
  excepted) in session, 20 after. Separate Senate (29) and House (75) districts by city, town or county.
- **Committee agendas (2026-11-22):** two official sources, merged by `agendas()` in states/ut/convert.py. (1) Each bill's
  own `agendaList` in the API record fetch.py already reads (every agenda it was put on: committee name, "2026-01-28
  14:00:00.0", the agenda's address, an "upcomming" flag); 2026's records give 820 bills on 248 meetings, all HB/SB keys
  matching the records (the rest are resolutions left out). (2) `agendas()` in states/ut/fetch.py, run after `roster()`:
  for each meeting in legcal.json from yesterday to three weeks ahead (not canceled: committees.json's status "C"), the
  API's `agencal/<mtgID>` route (listed on le.utah.gov/data/developer.htm; one request a meeting, a second apart), every
  bill number in its answer, into data/ut/<year>/agendas.json; the answers as read go to agencal.json. Committee names
  drop " Standing Committee"/" Committee"; one without a house becomes "Joint ...". Times are Utah's own clock (legcal
  writes them with a "Z" and unpadded hours, "2026-11-10T9:00:00.000Z"). Untested: the agencal route's answer format
  (the local token answered "Invalid request" for every route on 2026-11-22, so the parser looks for bill numbers in any
  string of the answer: "SB0112", "H.B. 47", "HJR 3"), and whether a bill's updatetime changes when it's put on an agenda
  (if not, source 2 is the timely one). Check agencal.json in January.
- **Next year's bills (2026-11-22):** from November fetch.py also reads next year's general session (bills/<2027GS>/
  billlist; bills are numbered from early December: 2026's first on 2025-12-02; le.utah.gov's 2027 list was empty on
  2026-11-22); its folder is made only once the list has a bill, it shows from its first bill as an upcoming session
  (convert.py's `sessions()` asks 500 bills only of past years), and it never marks Utah incomplete before it convenes.
- **Floor calendars (2026-11-22): none.** Utah's reading calendars (House 3rd Reading, Senate 2nd/3rd Reading,
  Concurrence) are standing lists, not dated: the records say when a bill was placed on one ("Senate/ placed on 2nd Reading
  Calendar", 630 in 2026) but not the day it will come up, and le.utah.gov's calendar page is a live JavaScript list. The
  floor-calendar feature needs a day, so Utah has none; "Awaiting a floor vote" already says where the bill is.
- **Veto letters (2026-11-22):** states/ut/vetoes.py, no table: for each bill with "Governor Vetoed" or "Governor Line
  Item Veto", le.utah.gov/~<year>/veto/<HB0003>.veto.pdf (the Legislature's copy; 2024's HB 2 and HB 3 scanned, read by
  OCR); else the governor's last letter of the session on several bills, le.utah.gov/~<year>/veto/VetoLetter.pdf (2024's
  scanned, 2025's typed: "I have selected these bills for veto: 1. HB 152 ...") or the governor's own copies found by
  governor.utah.gov's WordPress media search (/wp-json/wp/v2/media?search=veto: all of 2026's). `section()` picks a
  bill's paragraphs from such a letter (from the first naming it, by number or by its number and short title, since OCR
  read "HB 239" as "Jub 239", to the next bill, list item or turn). Checked 2026-11-22: all 7, 6 and 2 vetoes of 2024-26
  and the line-item vetoes (HB 2, HB 3 of 2024; HB 3, SB 3 of 2025; HB 3 of 2026). Both sites' Crawl-delay is 10.
- **Wording fixes (2026-11-23):** "Became Law w/o Governor Signature" (GNOSIGN) was read as SIGNED, so six laws of 2024-26
  said "Signed into law"; it's now its own line. A committee's "Substitute Recommendation" or "Amendment Recommendation"
  followed that day by "Motion to Recommend Failed", "Held" or "Tabled" is the committee changing the bill, not reporting it
  ("Committee amended it": HB 86 of 2025, HB 109 of 2024; 15-22 a session read "Approved by committee and sent to the
  floor"). A vote to hold or table is against the bill: its tally and names are turned round.
