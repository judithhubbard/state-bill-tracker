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
- **Contacts without emails or page links (checked 2026-11-22):** the file repository's member files (ftp.ilga.gov/Members/
  and each GA's folder) have names, parties, districts, Capitol and district addresses and phones, and nothing else: no
  email, no member id to build a page address from (the bill status files name sponsors only by name). www.ilga.gov, where
  the member pages are, turns automated requests away, so it isn't read. data_check.py's contacts check leaves Illinois's
  email and page out (`CONTACT_GAPS`). Open States' people file could supply emails, as for Pennsylvania (the owner's
  decision there), if the owner wants it here too.
