# Rhode Island

Moved from CLAUDE.md (2026-11-19). Shared conventions, the data traps list and the site's code notes stay there.
This state's data comes from LegiScan: the shared design (legiscan.py, the budget, states/legiscan_convert.py) is in states/LEGISCAN.md.

- **Rhode Island (built 2026-11-08 from LegiScan):** `states/ri/convert.py` (the `RhodeIsland` rules), `contacts.py` (run
  after legiscan.py), `towns.py` (run once: the 39 cities and towns, Census county subdivisions). One session a year from the
  first Tuesday of January to June (`STATE.dated`: add each year's last floor day); bills don't carry over. Bills (H/S) and
  the joint resolutions proposing constitutional amendments (a majority of each house's members, then the voters at the
  next general election: `amendmentOnce`, `ballotEvenYears`); other resolutions left out, including joint resolutions with
  the force of law (grants, study commissions: 6-14 a year sent to the governor). Companions: most bills are filed in both
  houses with the same text and, unlike Tennessee's, both versions pass and both become separate public laws. LegiScan has
  no link between them (no sasts): a House and a Senate bill with exactly the same description, when no other bill shares
  it, are one record (`group()`), so laws here are records, about 60% of the official count of bills signed. History:
  "in concurrence" means agreeing to the version the other house passed (the second house passing it unchanged is a
  passage; the first house accepting the second's substitute is `concur`, shown "Agreed to the Senate's version"); a
  second house's passage without it changed the bill (an added line says so). "Committee recommended measure be held for
  further study" is `held` (`heldAction`, "Held for further study"): the usual end, though a held bill can come back;
  "indefinite postponement" is voted down. The text's house beats the line's chamber field (some are wrong). No Rules or
  Calendar committee (`gates` empty): the Speaker and the Senate President schedule. History lines have no tallies, so
  floor roll calls go to that day's passage in the bill they're filed under (`votes_by_version`, a shared-module option;
  when there are more roll calls than passages that day, the earlier ones were floor amendments, also labeled "Passage");
  Senate committees' votes to hold or postpone aren't shown (the page reads committee votes as approvals). Laws have no
  numbers in the data ("Public Law 2025-123" isn't in LegiScan). Totals by bill number, matching LegiScan's statuses and the
  news (Rhode Island Current: 513 bills sent in 2025, two pairs vetoed; five pairs in 2024; one pair in 2026): sent to the
  governor 509 / 507 / 480 bills (2024/25/26), laws 499 / 503 / 478 (signed 398/382/349, without signature
  101/121/129), vetoed 10 / 4 / 2; as records 307 / 318 / 280 laws and 5 / 2 / 1 vetoes. Governor 6 days, Sundays excepted
  (the data's "Effective without Governor's signature" lines come 7 non-Sunday days after transmittal); 10 days after an
  adjournment, but the General Assembly recesses in June. Override three-fifths of the members present in each house.
  Local acts (bonds, charters, fire districts) are narrow "place" (`place_act()`), marriage-solemnization bills "person".
  Leaders: Speaker Chris Blazejewski (since May 7, 2026, after Joe Shekarchi stepped down) and Senate President Val Lawson
  (check both when the General Assembly elected in November 2026 meets in January 2027). Governor Dan McKee; add a new
  governor (January 2027) to `GOVERNORS` and states/legislatures.json. The governor's contact page and phone (401-222-2080)
  haven't been checked by the owner. rilegislature.gov bars automated readers: never fetch it.
