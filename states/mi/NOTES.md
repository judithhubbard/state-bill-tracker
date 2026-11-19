# Michigan

Moved from CLAUDE.md (2026-11-19). Shared conventions, the data traps list and the site's code notes stay there.

- **Michigan (started 2026-10-31):** `python3 states/mi/fetch.py` downloads each bill's status XML from the Legislature's
  document server (https://www.legislature.mi.gov/documents/<session>/status/<house|senate>/xml/; no robots.txt; its
  policy allows one request a second), only files the folder listing shows as new or changed (date and size, kept in
  listing.json). Some files start with a byte-order mark. `states/mi/convert.py`: each history line's journal names the
  chamber; House lines are lower case, Senate capitals; "passed; given immediate effect Roll Call #4 Yeas 63 Nays 41" is a
  passage (tallies only: members' votes are in the journals), "PASSED BY HOUSE ..." in the Senate's journal isn't;
  "ordered enrolled" means passed both houses; laws are "Public Act 2" (`STATE.lawWord`). Titles are the digest titles
  without the subject; topics from the subject categories (`CATEGORY_TOPICS`). "What it does" is the House and Senate Fiscal Agencies' bill analyses (`states/mi/texts.py`;
  `analyses()` in fetch.py reads the documents/<session>/billanalysis/house/pdf/ and senate/htm/ listings after the
  status files, each document once, never marking Michigan incomplete). A file's number is the bill's or a package's
  highest ("2025-HLA-0002" can be House Concurrent Resolution 2), so the bills and version come from each document's
  heading; the furthest version is used, the House's "SUMMARY:" without "Background" and the Senate's "CONTENT", labelled
  ("From the Senate Fiscal Agency's analysis of this bill and 2 others as passed by the Senate."). Joint resolutions get
  none (`baseNum()` would merge HJRA and HJRB). The first copy (about 6,200 documents) takes 4-6 runs. Bill pages are addressed by
  the year introduced ("2026-SB-0968"): a version's `link`. Legislators from the web service
  (https://legislature.mi.gov/litwebservices/litwebservices.asmx: GetLegislatorInformation for emails and phones,
  GetLegislatorInformationBySession for websites); party from the caucus website (housedems/senatedems = Democratic,
  gophouse or "rep..."/"senator..." sites = Republican; Open States for any other). Committees: the House's from www.house.mi.gov
  (each standing committee's page; the site omits its DigiCert intermediate certificate: `ca_bundle()` adds it, as for
  Illinois), the Senate's chairs and meeting times from senate.michigan.gov's committee list. Cities and townships by district (`towns.py`).
  Full-time Legislature; governor 14 days, Sundays excepted.
