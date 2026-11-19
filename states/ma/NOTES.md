# Massachusetts

Moved from CLAUDE.md (2026-11-19). Shared conventions, the data traps list and the site's code notes stay there.

- **Massachusetts (started 2026-10-31):** `python3 states/ma/fetch.py` reads the General Court's API
  (https://malegislature.gov/api/; see the ma-data-sources memory): each two-year General Court's document list (2025 is the
  194th), each bill's history (one request per bill, three at a time; a finished court's are read once, the current one's
  again when active), the Senate's roll calls, members (`contacts.py`, run by fetch.py; past courts' members for names in
  roll calls) and the session laws. Only bills and resolves are shown (not orders, study orders or constitutional
  proposals). A committee's new draft has a new number ("Accompanied a new draft, see H4321"), and a conference report is
  a new bill ("Reported, in part, by H4040"): `load_session()` follows the chain, and the record takes the newest number
  with the others as earlier numbers; the governor's amended sections that come back as bills ("see H4051 for section
  15") join the law's record. Laws come from the session laws file (`laws_<year>.json`, by OriginBill), since some
  histories stop before the signing. A study order ends a bill in committee (`STATE.heldAction`, "Sent to study").
  "Passed to be engrossed" is a house passing it; "Enacted ... laid before the Governor" sends it. Committees are almost
  all joint; House Steering, Policy and Scheduling decides which bills reach the House floor; the Committee on Bills in
  the Third Reading counts as the floor. Formal sessions end July 31 of the second year (`formalEnds()`), informal ones
  when the court ends. Governor 10 days. No summaries in the data ("What it does" isn't shown); House votes are tallies,
  Senate votes by member. Earlier courts linked by identical title (`earlier()`). Cities and towns (351) by district.
