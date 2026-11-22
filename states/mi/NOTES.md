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
  Full-time Legislature; governor 14 days, Sundays included (Art. IV, sec. 33: "measured in hours and minutes"; the profile
  excepted Sundays until 2026-11-21).
- **Committee agendas (2026-11-22):** `agendas()` in fetch.py (after the legislators, before the status files) reads
  the meeting list, https://www.legislature.mi.gov/Committees/Meetings (each chamber's upcoming meetings; canceled ones
  struck through and marked "cancelled"), then each listed meeting's page (/Committees/Meeting?meetingID=6100; about
  20-40 a week in session, one a second) for its agenda: the bill links (/Search/ExecuteSearch?docTypes=House
  Bill&sessions=2025-2026&number=5317) and bills named in its text ("SB 979", "Senate Bill 878"). Into
  data/mi/<session>/agendas.json, meetings from yesterday to three weeks ahead; the committee is the list's name with its
  section's house ("Senate Local Government"). A failed list keeps the last file; a meeting page that fails is left out.
  Joint resolutions aren't read (lettered: build_data.py's lookup drops a final letter). Tested against an archived
  meeting list (2025-02-11: 6 of 10 meetings kept, the 4 canceled left out) and two 2026 meeting pages (HB 5317, SB 979,
  SB 960, SB 526; SB 878), all matched to records; the live list is empty now (November 2026). The RSS feed
  (documents/publications/RssFeeds/comschedule.xml) lists the same meetings but doesn't mark cancellations, so it isn't used.
- A session of this year or later is shown from its first bill (`sessions()` in convert.py, 2026-11-22; older ones need
  more than 1,000 status files), so 2027-28 shows from its first bills in January (Michigan has no prefiling; its status
  folders answer 404 until then).
