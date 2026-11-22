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
- **Members' votes from the journals (2026-11-22):** floor votes by name (none before) and committee votes, from the daily
  House and Senate Journals (states/mi/journals.py; www.legislature.mi.gov/documents/<session>/Journal/<House|Senate>/htm/
  <yyyy>-HJ-<mm>-<dd>-<nnn>.htm, -SJ- for the Senate; 2023-2024 has its own folder; no robots.txt, one request a second).
  fetch.py reads each listed journal once, newest days first, after the status files and analyses, and again when its
  listing entry changes (journals are rewritten months later: many of 2025's were relisted 2026-02-04; `listing_dates.same()`
  for the server's local clock), saved as plain text, gzipped (data/mi/<session>/journals/<name>.txt.gz, with
  listing.json); never marks Michigan incomplete. About 400 journals a session (House 203 and Senate 197 in 2025-26 so
  far, 189 and 214 in 2023-24), 45-57 MB of HTML per house and session (budget days are 5-10 MB each), about 12 MB kept in
  all; the first copy takes a few runs. Pages are UTF-8 or Windows-1252 (UTF-8 first: the Senate's 2025 pages read as
  "Yeasâ€”31" otherwise).
  - Floor votes: a history line's "Roll Call #241" (House lines add "Yeas 104 Nays 5 Excused 0 Not Voting 1"; most
    Senate lines give only the number, so those votes had no tally before) is that house's roll call of the year (numbers
    restart each January) in the journal of the line's day. Names only when the journal's yeas and nays are the line's,
    every group's names come to its count, and the bill the journal read just before ("Senate Bill No. 579, entitled";
    "Senate / Bill No. 716" can be split across lines) is the line's; else the tally alone. The Senate's roll calls name
    yeas, nays, excused and not voting; the House's only yeas and nays ("In The Chair: Smit" isn't a vote), so the others
    come from the day's opening roll ("Paiz—excused", "Xiong— e/d/s": entered during the session), as the line's counts
    say: all not voting when it says Excused 0 (the House's usual), all excused when Not Voting 0, else by the opening
    roll; a day whose roll doesn't leave exactly that many is tally only. Names: tab-separated columns, or space-separated
    short lists ("Albert Lindsey Nesbitt Runestad Bellino"); two-word names and initials ("St. Germaine", "McDonald Rivet",
    "Carter, B.", "Greene, J." even split over lines) are put back with the day's roll. A column run past its heading
    (the Senate's Roll Call 217 of 2026 prints two yeas under "Nays—0") goes back to the group short by as many. Seats are
    today's members (contacts_<current>.json) of that house with that surname and initial ("Myers-Phillips" is Tonya Myers
    Phillips) who sponsored a bill that session, else "H?Name" (2023-24: Filler, Fink, Beeler, Friske, Bezotte, Zorn ... ,
    former members).
  - Committee votes: the committee reports' "Favorable Roll Call / To Report Out: Yeas: Reps. VanderWall, ..., Brenda
    Carter, ... and Foreman / Nays: Rep. Meerman" (the Senate's "To Report Out: Yeas: Senators ... Nays: ..."; "To Refer:"
    too), kept when that journal's attendance report for the committee ("Meeting held on: Wednesday, March 4, 2026",
    "Present: ...", "Absent: ...", "Excused: ...") has every voter present (it lists the committee, so absent and excused
    members, and those present who didn't vote, "B", are named and nobody unnamed reads as a yes) and the bill's history
    has a line that day; the vote's day is the meeting's. A report whose attendance is in another day's journal is left
    out (counted as "committee vote without attendance").
  - Measured 2026-11-22 on 20 journals read locally (both houses, both sessions; GitHub reads the rest): before, 2023-24
    had 2,023 floor votes (tallies) and 2025-26 1,193, none naming anyone, no committee votes; after, 2,042 and 1,201
    (Senate lines without a tally now have the journal's), 95 and 119 tied to journals (89 and 119 naming someone: all
    yeas and nobody missing names no one), 13 and 11 committee votes; non-yes names tied to seats: 2025-26 1,114 of 1,114,
    2023-24 2,719 of 3,052 (the rest former members). No roll call's tally differed from its line, none sat on another
    day, no group's names failed to add up once the parsing above was in. Check after the first full copy:
    `VOTE_STATS` in convert.py (`python3 -m states.mi.convert` prints them: "no journal roll call" should fall to the Senate's few lines whose
    journal is missing, "House roster doesn't fit", "names don't add up", "journal reads another bill" near 0).
