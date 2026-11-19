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
