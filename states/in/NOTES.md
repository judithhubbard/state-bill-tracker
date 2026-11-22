# Indiana

Moved from CLAUDE.md (2026-11-19). Shared conventions, the data traps list and the site's code notes stay there.

- **Indiana (built 2026-11-08; in build_site.sh, publish.yml and states.json since):** `python3 states/in/fetch.py` reads the
  General Assembly's API (api.iga.in.gov, with the owner's key: INDIANA_API_KEY or ~/.indiana_api_key, a header, never
  printed): each regular session's bill list, every action and roll-call tally in one answer each, each HB, SB, HJ and SJ in
  full (authors, sponsors, versions with the Legislative Services Agency's digest, subjects), legislators and committees;
  `states/in/contacts.py` runs after it. The package is named "in", a Python keyword: its files load each other with
  importlib (like Oregon's). `states/in/convert.py` reads the plain-English actions, each with its chamber: "First reading:
  referred to Committee on X"; "Committee report: amend do pass, adopted" (the house adopting the report; "...; reassigned to
  Committee on Y" sends it on); "Recommitted to Committee on Ways and Means pursuant to House Rule 126.3" (bills that cost
  money); "Third reading: passed; Roll Call 143: yeas 40, nays 9" (the passage); a motion to refer that failed ("...; Failed,
  Roll Call ...") isn't a referral. Passed both houses: "Returned to the X without amendments", the first house concurring,
  the same conference report adopted by both houses, or the presiding officers' signatures; all three signatures (Speaker,
  President Pro Tempore, President of the Senate) mean presented to the governor (the presentment day isn't recorded, so the
  governor's 7-day deadline, `govDeadline()`, counts from the last signature: an estimate). Laws: "Signed by the Governor",
  "Bill Became Law on 8th Day Without Signature", a "Public Law 126" number (`STATE.lawWord` "Public Law"); "Vetoed by the
  Governor". Signatures and the governor's lines carry only a date: within a day, timed lines sort first. The authorship
  lines ("Authored by", "... added as coauthor") are dropped from the history (the sponsor lists hold them). Committees
  don't vote bills down on the record: a bill the chair never hears just stays ("no action"). Votes are tallies only (the
  roll calls' member lists are PDFs the API doesn't serve). Joint resolutions proposing amendments (not the "Vehicle joint
  resolution" placeholders, nor calls for a federal convention) are tagged "const": two General Assemblies in a row, then
  the voters, never the governor, though they get Public Law numbers; the digest says "has been agreed to by one general
  assembly" on the second passage (`STATE.amendmentFinal` reads it from the summary). "Vehicle Bill." placeholders (about
  60 a year) are `shell`. "What it does" is the latest version's digest, split into paragraphs of a few sentences. Topics
  from committees (`COMMITTEE_TOPICS`) and the subject index's headings (`SUBJECT_TOPICS`). Earlier years linked by short
  description and first author, never to a law. Legislators: the API's members and committees (chair, vice chair, ranking
  minority member); emails and caucus pages from Open States' public-domain file (as for Ohio and Pennsylvania; the API has
  none); phones are the caucuses' shared lines (House R 800-382-9841, House D 800-382-9842, Senate 317-232-9400 /
  800-382-9467). Leaders (`LEADERS`, `POSITIONS` in profile.py) checked 2026-11-08: Senate Republicans chose Chris Garten to
  follow Rodric Bray as President Pro Tempore once the Senate votes after the November 2026 election: change `LEADERS` then.
  A veto is overridden by a majority of each house's members (legislatures.json `"override": "majority"`), until the end of
  the next regular session. One session a year, long in odd years (by April 29), short in even (by March 14); each year's
  first and last days are in `STATE.opened`/`STATE.dated` (add each year's). Totals: 2024 171 laws and 1 veto (HEA 1002),
  matching the news; 2025 243 bills became Public Laws (P.L. 1-246, with two amendments and an Article V resolution; the
  Bankers Association counted 244); 2026 163 and no vetoes. Bill pages: iga.in.gov/legislative/<year>/bills/<house|senate>/
  <n>/details (the joint resolutions' address is a guess). Separate Senate (50) and House (100) districts by city, town or
  county (`states/in/towns.py`).

- **Committee agendas (2026-11-22):** `agendas()` in states/in/fetch.py, run for this year's session and next year's
  (when the API lists it) before the bills, writes data/in/<year>/agendas.json; `agendas()` in convert.py reads it and
  keeps meetings from today on. Source: the API's meetings, `/<year>/meetings?minDate=<yesterday>&maxDate=<+21 days>`
  (committee with its chamber, day, start time, "cancelled": "False"/"True"), then each meeting's detail
  (`/<year>/meetings/<id>`: `agenda[].bill.billName`, "HB1038"). No meetings answers `{"meetings": {"itemCount": 0,
  "items": [a blank item]}}`. Names: "House Public Policy", "Senate Appropriations"; conference committees and interim
  committees "Joint ...". A session's committees start meeting in December (2026's first was 2025-12-02, on prefiled
  bills), but build_data.py reads agendas only for the current session, so December's meetings show from January. One
  list plus one request per meeting (about 80 in a busy three weeks, 0.6 s apart). A failure keeps the last file.
  Tested 2026-11-22 with the date set to 2026-02-02: 189 bills on 79 meetings, every key matched a record; live today
  (no meetings). Not yet seen: a cancelled meeting in the window, and next session's first December meetings.
