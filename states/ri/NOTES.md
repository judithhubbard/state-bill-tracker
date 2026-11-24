# Rhode Island

Moved from CLAUDE.md (2026-11-19). Shared conventions, the data traps list and the site's code notes stay there.
This state's data comes from LegiScan: the shared design (legiscan.py, the budget, states/legiscan_convert.py) is in states/LEGISCAN.md.

- **Rhode Island (built 2026-11-08 from LegiScan):** `states/ri/convert.py` (the `RhodeIsland` rules), `contacts.py` (run
  after legiscan.py), `towns.py` (run once: the 39 cities and towns, Census county subdivisions). One session a year from the
  first Tuesday of January to June (`STATE.dated`: add each year's last floor day); bills don't carry over. Bills (H/S) and
  the joint resolutions proposing constitutional amendments (a majority of each house's members, then the voters at the
  next general election: `amendmentOnce`, `ballotEvenYears`); other resolutions left out, including joint resolutions with
  the force of law (grants, study commissions: 6-14 a year sent to the governor). Companions: most bills are filed in both
  houses with the same text and, unlike Tennessee's, both versions pass and both become separate public laws. LegiScan has
  no link between them (no sasts): a House and a Senate bill with exactly the same description, when no other bill shares
  it, are one record (`group()`), so laws here are records, about 60% of the official count of bills signed. History:
  "in concurrence" means agreeing to the version the other house passed (the second house passing it unchanged is a
  passage; the first house accepting the second's substitute is `concur`, shown "Agreed to the Senate's version"); a
  second house's passage without it changed the bill (an added line says so). "Committee recommended measure be held for
  further study" is `held` (`heldAction`, "Held for further study"): the usual end, though a held bill can come back;
  "indefinite postponement" is voted down. The text's house beats the line's chamber field (some are wrong). No Rules or
  Calendar committee (`gates` empty): the Speaker and the Senate President schedule. History lines have no tallies, so
  floor roll calls go to that day's passage in the bill they're filed under (`votes_by_version`, a shared-module option;
  when there are more roll calls than passages that day, the earlier ones were floor amendments, also labeled "Passage");
  Senate committees' votes to hold or postpone aren't shown (the page reads committee votes as approvals). Laws have no
  numbers in the data ("Public Law 2025-123" isn't in LegiScan). Totals by bill number, matching LegiScan's statuses and the
  news (Rhode Island Current: 513 bills sent in 2025, two pairs vetoed; five pairs in 2024; one pair in 2026): sent to the
  governor 509 / 507 / 480 bills (2024/25/26), laws 499 / 503 / 478 (signed 398/382/349, without signature
  101/121/129), vetoed 10 / 4 / 2; as records 307 / 318 / 280 laws and 5 / 2 / 1 vetoes. Governor 6 days, Sundays excepted
  (the data's "Effective without Governor's signature" lines come 7 non-Sunday days after transmittal); 10 days after an
  adjournment, but the General Assembly recesses in June. Override three-fifths of the members present in each house.
  Local acts (bonds, charters, fire districts) are narrow "place" (`place_act()`), marriage-solemnization bills "person".
  Leaders: Speaker Chris Blazejewski (since May 7, 2026, after Joe Shekarchi stepped down) and Senate President Val Lawson
  (check both when the General Assembly elected in November 2026 meets in January 2027). Governor Dan McKee; add a new
  governor (January 2027) to `GOVERNORS` and states/legislatures.json. The governor's contact page and phone (401-222-2080)
  haven't been checked by the owner. rilegislature.gov does NOT bar automated readers (corrected 2026-11-24; the note of 2026-11-08 said it did): its robots.txt
  ("Updated: August 2026", re-read 2026-11-24) bars only committee testimony PDFs (/Special/comdoc/*.pdf,
  /senators/SenateComDocs/*.pdf), and its pages answer a named program 200. Bills still come from LegiScan; reading the
  Legislature's own pages (bill status, committee agendas) needs no permission, only a gentle pace.
- **Committee agendas (2026-11-22):** from each bill's LegiScan `calendar` (its hearings: date, time, room, description), read with the bill (no queries of their own): `agendas()` calls legiscan_convert.agendas() (states/LEGISCAN.md). Today's and later meetings only. LegiScan's calendar has no cancellations; an entry dropped from a notice goes when the bill is next read, which within the daily getBill allowance can be hours after the change. "Consideration" entries (a committee vote after the hearing) count as meetings. Times are often 00:00 ("Rise of the House/Senate"). Tested against 2026's saved calendars (2,144 bills, all matched).
  The history (2026-11-22): every dated "Scheduled for hearing and/or consideration (04/02/2025)" line of 2024-26 is
  also in the calendar (2,852, 2,909 and 3,221 of them; posted 2-6 days ahead), so the history adds no meetings. But the
  calendar keeps hearings the history says were called off: "Meeting postponed (04/22/2025)" (270 still listed),
  "Committee postponed at request of sponsor (05/15/2025)" (143), "Withdrawn at sponsor's request (04/09/2025)" (29).
  `history_meetings()` in convert.py leaves out the calendar's meetings on those days (unless a later line schedules the
  bill for that day again): as of 2026-03-01, 2,828 entries instead of 2,914.
- **Official agendas looked into (2026-11-24; not built):** the General Assembly's own agendas can't be read within its robots
  rules. Its committee calendars and agendas are on status.rilegislature.gov (agendas.aspx, legislative_committee_calendar.aspx,
  calendars.aspx), whose robots.txt is "User-agent: * / Disallow: /". On www.rilegislature.gov the agendas themselves are PDFs
  in the committee document libraries, /Special/comdoc/<Committee> <year>/ (House) and /senators/SenateComDocs/ (Senate), which
  robots.txt bars ("Blocks all testimony and agenda PDFs"). What is allowed is each library's HTML index (Forms/AllItems.aspx,
  30 files a page, 5 s apart): file names, posting time, "Agenda Date" and one "Bill Number" per file, e.g.
  "01-22-2026---Agenda--enr" posted 1/21 9:59 AM, and testimony files "01-22-2026--H7071--Adam_Yorks(...)--enr". That gives a
  committee's agenda days and the bills someone sent testimony on, not the bills on an agenda, times, rooms or cancellations,
  and it's incomplete: House Environment and Natural Resources 2026 (23 pages, 663 files) lists 11 agendas; LegiScan's
  calendar has 11 meeting days; 10 agree. 3/31 has no agenda file but testimony on exactly the 10 bills LegiScan lists that
  day (the hearing was held); 1/29 has an agenda file (posted 1/24) but no LegiScan entries, no testimony and no history line
  for that committee and day. So LegiScan's calendar stays the source; the index could at most add a check, at about 400
  requests a year for all committees, which isn't worth it. A request to Legislative Data Systems (Nicholas Budano,
  Director, 401-222-3580) for permission to read status.rilegislature.gov's agendas, or an agenda feed, is the way to
  official agendas.
- **Could the Legislature's own sites replace LegiScan (surveyed 2026-11-24)?** Not for status: bill histories, sponsors and
  agendas are on status.rilegislature.gov (barred, above). Allowed: floor roll calls by session day at
  votes.rilegislature.gov (no robots.txt; /Votes/House/Session/20260106 ..., one page a session day: about 60 a year per
  house, 2003 on), bill text at webserver.rilegislature.gov/BillText<yy>/ (no robots.txt; one PDF a bill and version), and
  the House and Senate Journals on www (/journals/). LegiScan already has member-by-member roll calls and texts, so these
  would replace only what works; replacing LegiScan needs status.rilegislature.gov.
