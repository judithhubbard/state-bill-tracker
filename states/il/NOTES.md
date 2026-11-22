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
- **Contacts without emails or page links (checked 2026-11-22):** the file repository's member files (ftp.ilga.gov/Members/
  and each GA's folder) have names, parties, districts, Capitol and district addresses and phones, and nothing else: no
  email, no member id to build a page address from (the bill status files name sponsors only by name). www.ilga.gov, where
  the member pages are, turns automated requests away, so it isn't read. data_check.py's contacts check leaves Illinois's
  email and page out (`CONTACT_GAPS`). Open States' people file could supply emails, as for Pennsylvania (the owner's
  decision there), if the owner wants it here too.
