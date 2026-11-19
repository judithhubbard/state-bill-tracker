# Texas

Moved from CLAUDE.md (2026-11-19). Shared conventions, the data traps list and the site's code notes stay there.

- **Texas (started 2026-10-30):** `python3 states/tx/fetch.py` downloads each bill's history XML from the Legislature's FTP
  site (see the tx-data-sources memory; its Acceptable Use file asks data users to use it, not the TLO website), only
  files whose listing date changed, six folders at a time (about a second a file: the first full copy of three sessions
  takes hours). `complete()` re-downloads files cut off mid-transfer. Sessions are the Legislature's codes (`code_of()`:
  2025 -> "89R"); special sessions aren't shown. `states/tx/convert.py` reads the action codes (H555 House passed, S576
  Senate passed, E015 sent to the governor, E020/E025/E030 signed/filed without signature/signed with line-item vetoes,
  E035 vetoed; H/S 0xx-1xx referrals, 25x/28x reports, H245/S275 "left pending"); a reported House bill is shown in the
  Calendars Committee until it's placed on a calendar. H825/S825 "Transmitted to the Governor" is NOT a sending (it's on
  bills still in committee). One record per bill; companions show as similar bills. Committee votes are totals from the histories;
  floor votes by member come from the journals (`states/tx/journals.py`): the House Journal's record votes by the "RV#"
  numbers in the histories, and the Senate Journal by each bill's heading (it has no record numbers), including the
  Local and Uncontested Calendar's list format and a date's second journal ("...SJ04-12-F1.HTM"); "(Same as previous
  roll call)" means the vote just before, motions included. About 98% of Senate passages are found; every list's
  count matches its tally. `states/tx/contacts.py`: the House's member and
  committee JSON, each senator's page, parties from the Legislative Reference Library; `dataName` is the last name, or
  "Bell, Keith" where two members share it. Counties with each district's share (`states/tx/towns.py`, run once, from the
  Texas Legislative Council's r4.pdf district reports). "What it does": the current session's bill analyses
  (`states/tx/texts.py`). Session dates are computed (`opens()`, `sessionEnds()` = day 140, House deadline day 122,
  governor 10 days without Sundays or 20 after adjournment). Leaders: the Speaker, and for the Senate the Lieutenant
  Governor (not a senator). Totals for 2025 to check against: 1,047 signed, 140 filed without signature, 26 vetoed
  (reports/signedbygov.htm etc. on the FTP site).
