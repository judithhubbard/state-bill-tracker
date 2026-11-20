# Maryland

Moved from CLAUDE.md (2026-11-19). Shared conventions, the data traps list and the site's code notes stay there.

- **Maryland (started 2026-10-31):** `python3 states/md/fetch.py` reads each regular session's bill list
  (https://mgaleg.maryland.gov/<year>RS/misc/billsmasterlist/legislation.json; no robots.txt: sponsors, committees, the date
  and result of each reading in each house, the Department of Legislative Services' synopsis ("What it does"), chapter
  number and status) and the members' pages (district, party, committees with "(Chair)", Annapolis phone, email).
  `states/md/convert.py` builds each bill's steps from those dates; there are no votes. Every bill the General Assembly passes gets a chapter number unless vetoed, so
  after mid-June a passed bill without one is vetoed (some vetoed bills' statuses show a later motion on the veto).
  Constitutional amendments pass once by three-fifths and go to the voters at the next even-year election
  (`STATE.amendmentOnce`, `ballotEvenYears`); they get chapter numbers but aren't laws. 47 districts, each with a senator
  and three delegates, some from subdistricts ("44A"): as in New Jersey, a district's senator and all its delegates are its
  legislators ("S:44", "H:44a/b/c"); the towns list (cities, towns, Census-designated communities and counties) gives one
  district list for both houses. `dataName` is the bill list's form ("Ebersole", "Lewis, R."). One 90-day session a year.
- **The governor's dates and veto overrides (2026-11-19):** the bill list has no dates for the governor's actions and
  never shows an override: 2025's list, last saved by the General Assembly on 2025-12-01, still says "Vetoed" for the
  bills that became law over the veto in the special session of 2025-12-16 (SB 587, "Chapter 9 of 2025 Special Session";
  HB 270, Chapter 3), and the site showed every law and veto on the bill's last legislative day (SB 448 of 2026: April 9;
  vetoed May 22). `fetch.py` now reads each passed bill's page (its history table: "Post Passage" lines with the
  governor's dates, then "Overridden (111-23)" in each house and "Became law per Maryland Constitution ..."), into
  data/md/governor_<year>.json: a decided bill once, a vetoed one weekly while it can be overridden (this year and last),
  an undecided one daily, every year's vetoes first, at most 11 minutes a run (about 900 to 1,050 pages a year, about 30
  a minute; a first copy takes several runs). A special session's bills in a year's list (HB 2101 of 2026, August) have
  pages under its own code (2026S1). Checked 2026-11-19: 2025, 29 vetoes (May 16), 19 overridden on 2025-12-16, 10 left;
  2026, 5 vetoes (May 22: the veto guide's count), HB 862 and SB 426 overridden in August; 2024, 4 vetoes.
  `convert.py` dates the signature, veto and override from it (keyDates 5 and 6, so an overridden law reads "Became law
  over the governor's veto"); a special session's chapter number isn't kept as the bill's (it repeats the regular
  session's numbers). "Enacted under Article II, Section 17(c)" is a law without the governor's signature. A bill whose
  page isn't read yet keeps the old, undated reading.
