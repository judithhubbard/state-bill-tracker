# New Jersey

Moved from CLAUDE.md (2026-11-19). Shared conventions, the data traps list and the site's code notes stay there.

- **New Jersey, milestone 1 (bills, stages, votes; built 2026-10-27):** `python3 states/nj/fetch.py`
  downloads each session's database and vote files into data/nj/ (not in git yet), and
  `python3 build_data.py --state nj` builds site/nj/<session>.html. `states/nj/convert.py` turns NJ's
  action codes into NY's wording, so the page's plain-language rules work unchanged. A state's How tab
  text is `states/<code>/how.html` (else New York's, in tracker.html); its committee pairings, calendar
  and "passed both houses" line are in its profile.js. Committee agendas come from `C.agendas()`. A
  conditional veto the Legislature hasn't acted on counts as passed both houses while the session runs.
  Legislators (milestone 2, 2026-10-28): `states/nj/contacts.py` (run by fetch.py) writes
  data/nj/contacts_<session>.json from the roster, biography and committee files in NY's shape. Seat ids
  are "S:12", and "A:12a"/"A:12b" for a district's two Assembly members (`seat_ids()` in convert.py, which
  also ties the current session's votes to them). "Where you live" picks a town (`renderTownReps()`, from
  data/nj/district_towns.json, made once by `states/nj/towns.py` from the Apportionment Commission's table);
  a town's district gives its senator and both Assembly members. ROSTER.TXT's Email column is empty, so
  contacts.py reads each legislator's email (`SenX@njleg.org`) and contact form from the Legislature's website
  (`/api/legislatorData/legislatorBio/<Roster Key>`), keeping the last copy's when a request fails; the page shows
  the form as "Contact form" (`formHtml()`). 2022–23's text download lacks MAINBILL, ROSTER, COMMITTEE and SUBJHEADINGS;
  `states/nj/fill2022.py` filled them in once (2026-10-29) and the result, data/nj/DB2022_TEXT.zip, is in git. Earlier
  versions come from LastSessionFullBillNumber (one session back) and OldBillNumber (two back). The governor's veto messages (absolute, conditional, line-item) come from pub.njleg.gov
  (`states/nj/vetoes.py`, run by fetch.py, into data/nj/vetoes_<session>.json); `vetoMemo()` words each kind. What each bill does (the sponsor's statement, the latest committee statement, the fiscal
  estimate's summary) comes from `states/nj/texts.py` (current session; documents already read are kept in
  data/nj/docs_<session>.json); build_data.py's `bill_texts()` writes it to data/<session>-text/<A10>.json in pieces
  of 500 bill numbers (packed into Claude copies), and `whatItDoes()` shows it when a bill is opened. Not done yet: published lists and the "public site" tip; the daily workflow for NJ.
- **Floor calendars (2026-11-22):** the voting sessions' board lists are BAGENDA.TXT's "Session" rows (CommHouse "A" or
  "S"), skipped by the committee reader until now: `agendas()` gives each bill listed ["Senate floor", time, "floor"]
  (states/floorcal.py), a vote set for that day, so the page says "Senate floor vote Thu, Oct 22" and the card asks your
  own legislators to vote; a session AGENDAS.TXT marks canceled drops its whole day. Simple resolutions (AR, SR) left out.
  2026: 13 sessions, 492 bills (posted 1-6 days ahead); 24 are joint or concurrent resolutions that aren't records (the
  same kind the committee agendas already had: the data check's "aren't records' numbers" FAIL was there before).
