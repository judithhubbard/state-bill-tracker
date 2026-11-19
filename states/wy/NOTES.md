# Wyoming

Moved from CLAUDE.md (2026-11-19). Shared conventions, the data traps list and the site's code notes stay there.

- **Wyoming (started 2026-11-01):** `python3 states/wy/fetch.py` reads the Legislative Service Office's JSON API, the one
  wyoleg.gov's pages use (lsoservice.wyoleg.gov/api and api.wyoleg.gov; no robots.txt), a request a second: each year's
  bill list, each HB, SF, HJ and SJ in full (actions, sponsors, roll calls member by member in committee and on the floor,
  the LSO's bill summary), members and the joint committees; `states/wy/contacts.py` (run after it in the workflow) builds
  the contacts (93 members with emails and phones; a past year adds members who left, for seats no one else holds).
  One session a year: a general session in odd years (from the second Tuesday of January, 40 legislative days), a budget
  session in even years (from the second Monday of February, 20 days), where a bill other than the budget needs
  two-thirds to be introduced; "Failed Introduction" and "Did not Consider for Introduction" are `STATE.heldAction`
  ("Not introduced"). Each year's last day is in `STATE.dated` (add each new year's). `states/wy/convert.py`: actions
  begin with their house ("H 3rd Reading:Passed 53-4-5-0-0" is the passage; a tally is yes, no, excused, absent,
  conflict); the API lists them newest first. Each house's twelve standing committees have the same numbers and names
  ("H09 - Minerals" and "S09 - Minerals"); only single-subject ones give a topic. Both houses passing isn't passing both
  houses: a bill sent back for concurrence needs "Concur:Passed" (or a recede) or enrollment ("Assigned Number HEA
  No."); several died in conference. A law is decided by its chapter number: veto overrides appear only among the roll
  calls ("Veto Override 45-16-1-0-0", "Did Not Override Veto 35-27"), added to the history as written. Roll-call names:
  floor "Campbell, K" (the members' voteName), committee "CAMPBELL" (a shared surname resolved by committee membership);
  name lists split on commas, so initials, "Jr" and first names ("Larsen, Lloyd") rejoin the name before them; a roll
  call's chamber field is sometimes wrong (the action's house letter decides). Committee sponsors' full names ("Joint
  Judiciary Interim Committee") come from the digest's "Sponsored By:" line. "What it does" is the LSO's bill summary
  (mostly laws; background-first summaries reordered), else the official title's clauses (`purpose()`: "specifying" ->
  "Specifies"). Earlier years linked by catch title and prime sponsor, never to a bill that became law (yearly bills like
  "Omnibus water bill-construction" share titles). Governor 3 days, Sundays excepted, in session; 15 days after
  adjournment. The governor's phone and contact page (governor.wyo.gov/contact/governor) haven't been checked by the
  owner. A new governor takes office January 4, 2027 (Gordon is term-limited): add them to `GOVERNORS`.
