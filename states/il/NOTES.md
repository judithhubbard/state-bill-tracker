# Illinois

Moved from CLAUDE.md (2026-11-19). Shared conventions, the data traps list and the site's code notes stay there.

- **Illinois (started 2026-10-30):** `python3 states/il/fetch.py` downloads each bill's status XML from the General
  Assembly's public file repository, https://ftp.ilga.gov/ (see the il-data-sources memory: www.ilga.gov turns automated
  requests away and points to it), only files whose listing date changed; plus each General Assembly's member and
  committee XML, from which `states/il/contacts.py` builds the contacts (no web pages). Both servers omit an
  intermediate certificate: `ca_bundle()` adds Sectigo's to a copy of the system's (data/il/ca.pem); verification
  stays on. Sessions are General Assemblies (`assembly_of()`: 2025 -> 104). `states/il/convert.py` reads the plain-English
  actions: every bill starts in the House Rules or Senate Assignments Committee (the gatekeepers: `committeeNext` and
  `chairAsks` word their asks), "Assigned to X Committee" is the real referral, "Rule 19(a) / Re-referred to Rules" is
  "held"; amendments' own referrals aren't the bill's. Sponsor lists join the chief sponsors with hyphens
  (`split_sponsors()` splits them against that Assembly's members). Votes are tallies only (no roll calls in the
  repository). An amendatory veto is "passed both houses" until both houses accept it. "What it does" is the
  synopsis of the last amendment that rewrote the bill ("Replaces everything after the enacting clause"; more than half
  the laws), else of the bill as filed, then each later adopted amendment's (`synopsis()` in convert.py; the file's
  synopsis block also holds fiscal notes and veto messages, left out). About 30% of bills are shells ("Makes a technical
  change", $2 appropriations; `is_shell()`), which the House Executive Committee approves in bulk: decided 2026-10-30,
  the statistics and legislators' numbers (profiles, history, networks) leave out shells never rewritten
  (`without_shells()` in build_data.py, `outcomes()`, and `b.shell` in `netData()`/`whoData()`; the Speaker "sponsored"
  883 bills with them, 15 without), each Statistics
  note says so (`shellsOut()`), the list tags them "Shell bill" with a tip (`SHELL_TIP`), and they get no odds line. An
  amendment that "Reinserts the provisions of the introduced bill" is a change, not a rewrite. Rules and Assignments are `STATE.gates`: no New York
  "got as far as Rules" line, and a bill waiting there says the leader controls it; `STATE.commIntro` words the How
  tab's Committees points. "Where you live" lists cities, villages and counties from the Census Bureau's 2024 district relationship
  files (`states/il/towns.py`, run once; no key needed; works for any state). Bill links go to the repository's
  status pages and texts.
- **Veto messages (2026-11-22):** the repository keeps the governor's message on each vetoed bill in the bill's folder:
  /Legislation/104/HB/10400HB2682gms.htm ("gms", a Word page in Windows-1252), for total, amendatory and item/reduction
  vetoes alike (an earlier survey thought total vetoes had none). fetch.py's `veto_messages()` asks for it for each status
  file whose actions say "Governor Vetoed", "Governor Amendatory Veto" or "Governor Item/Reduction Veto", one request
  every 10 seconds (robots.txt's Crawl-delay), once, into data/il/<GA>/vetoes/HB2682.htm; a 404 is asked again a week
  later (vetoes/missing.json). An amendatory veto's letter says "return", not "veto": a saved page only has to be a letter
  ("General Assembly"). `veto_message()` in convert.py keeps the paragraphs between the salutation ("... General
  Assembly:") and "Sincerely," (they name the bill: "I veto House Bill 2682 of the 104th General Assembly"), kind
  "conditional" for an amendatory veto (the page's New Jersey wording: sent back with changes; signed after both houses
  accepted them; or not accepted in time), "line-item" for an item/reduction veto, and a total veto overridden shows
  "Became law over Governor Pritzker's veto" (HB 684 of 2021). Before: no veto messages. After (2026-11-22): 21, every
  bill with a governor's veto action in 2021-26 (102nd: 8, 103rd: 8, 104th: 5), all 12 vetoes that stood among them.
- **Committee agendas (2026-11-22):** the repository has no hearing schedules (folders: Committees, ILCS, JCAR,
  Legislation, Members, Public Acts) and www.ilga.gov, which has them, turns automated requests away (not fetched). But
  each bill's status file names the hearings it's posted for, `<committeehearing>`: "Judiciary - Criminal Committee
  Hearing Apr 17 2026 10:30AM Capitol Building Room 114 Springfield, IL", "Transportation: Vehicles & Safety Hearing ..."
  for a subcommittee, a red "** Canceled **" once called off, " - House Floor Amendment 2" for a hearing on an amendment.
  `agendas()` in states/il/convert.py reads them from the files fetch.py already downloads (no new requests): canceled and
  amendment hearings left out, the house from the bill's last "Assigned to <that committee>" action ("House Judiciary -
  Criminal"). The files are synchronized nightly, so a hearing appears the day after it's posted. Tested on what the files
  hold between sessions: HB 5598 of 2021-22 ("House Health Care Availability & Accessibility", 2022-03-31T09:00:00, with
  the date set back) and the 48 canceled 2026 hearings (all parse; each names a committee the bill was assigned to).
  Untested in session: Senate hearings' wording, and whether a hearing stays in the file after it's held (the date
  filter drops it either way).
- **Contacts: emails and page links from Open States (the owner's decision 2026-11-22, as for Pennsylvania):** the file
  repository's member files (ftp.ilga.gov/Members/ and each GA's folder) have names, parties, districts, Capitol and
  district addresses and phones, and nothing else: no email, no member id to build a page address from. So fetch.py's
  `people()` downloads Open States' public-domain file (data.openstates.org/people/current/il.csv, to
  data/il/openstates_people.csv; a failed or odd answer keeps the last copy), and contacts.py's `add_open_states()` takes
  each member's email and the address of their page on ilga.gov (the "https://www.ilga.gov/House/Members/Details/3358"
  form among the record's links), matched by house and district and a shared part of the last name (Open States' "Mike
  Simmons-Gessesse" is the files' "Mike Simmons"; a seat filled since gets neither). The ilga.gov pages are only linked,
  never read: ilga.gov asks programs to use the file repository. "About this data" names Open States. On 2026-11-22:
  before, 0 of 177 with an email or page; after, 174 emails (Faraci, Hills and Preston have none in Open States; a few
  addresses are personal ones, e.g. Simmons's gmail.com, as Open States lists them) and 177 pages. Illinois is no longer
  in data_check.py's `CONTACT_GAPS`. Open States' file also has photos (cdn.ilga.gov) not used yet.
- **The next General Assembly (2026-11-22):** members prefile bills from early December (1,081 of the 104th's were "Prefiled with Clerk" on 2024-12-02); fetch.py asks for the next Assembly's BillStatus folder every run (`main()`: up to `CURRENT + 2`; /Legislation/105/ answered 404 on 2026-11-22) and reads it as soon as it's listed, so the 105th shows as an upcoming session from its first prefiled bills. Its member and committee lists come later: until both member lists are on file, `contacts_session()` keeps refreshing the 104th's contacts (contacts.py couldn't read lists that aren't there), and a missing committee list reads as none.
- **"What it does" left as written (2026-11-23):** 78% of the LRB synopses open with the law they amend ("Amends the School
  Code.") and the next sentence says what the bill does ("Provides ...", "Requires ...", "Makes a technical change ...").
  Not reordered: the line is short, names the law changed, and in 952 of 2025-26's synopses each "Amends ..." heads its own
  part ("Amends the A Act. Provides ... Also amends the B Act. ..."), which moving the first would break.
- **Crawl-delay obeyed (2026-11-24):** ftp.ilga.gov's robots.txt asks every program for 10 seconds between requests
  ("User-agent: *  Crawl-delay: 10"); the bill status files had been read six at a time. fetch.py now makes one request
  every 10 seconds (`pace()`, for listings, files, member lists and veto messages), the most recently changed bills first,
  and stops 12 minutes before the step's limit (`FETCH_MINUTES`, 110 in .github/states.json); what's left comes next run.
  What that costs, measured from 2023's and 2025's histories (bills with an action that day, each a changed file): a
  typical session day (about 200) takes about 35 minutes; the busiest days (1,500-3,000, at the deadlines) take 4-8 hours,
  so on those days the last bills to change reach the site a few hours late. Illinois moves to the slow lane on its own
  when its runs are long.
