# Tennessee

Moved from CLAUDE.md (2026-11-19). Shared conventions, the data traps list and the site's code notes stay there.
This state's data comes from LegiScan: the shared design (legiscan.py, the budget, states/legiscan_convert.py) is in states/LEGISCAN.md.

- **Tennessee (built 2026-11-08 from LegiScan):** `states/tn/convert.py`
  (the `Tennessee` rules), `contacts.py` (run after legiscan.py), `towns.py` (run once). Two-year General Assemblies (2025 is
  the 114th, 2025-26), sessions each year from the second Tuesday of January to late April (`STATE.dated`: add each year's
  last day). Only HB/SB under 6000 (extraordinary sessions' bills are 6001+, 7001+ in the same files) and the joint
  resolutions proposing amendments to the Tennessee Constitution (majority in one General Assembly, two-thirds in the next,
  then the voters at the next governor's election: `ballotYear()`); other resolutions left out. Every bill is filed in both
  houses with the same text; LegiScan's sasts "Crossfiled" (and, for joint resolutions, the same title) put the two numbers in
  one record, as NJ's and NY's identical bills are; when one passes, the other house substitutes it for its own ("Comp. SB
  subst." marks the number that gave way: `replaced`). House bills go through subcommittees ("Assigned to s/c ..."): the
  bill stays in the parent committee; subcommittee votes keep their names. Calendar and Rules (House) and Calendar (Senate)
  schedule floor votes (`gates`). Set aside (`heldAction`): "Taken off notice", "Assigned to General Subcommittee", "Deferred
  to Summer Study", "Lay on the Table" ("Placed behind the budget" is a wait, not counted). Laws: "Signed by Governor.",
  "Returned by Governor without signature." (law), "Pub. Ch. 78" and "Pr. Ch." (private acts, narrow "place"); a governor
  recalled by the Senate ("Governor returned.", SB 1758 of 2026) is `unsent`. Public chapters are numbered through the
  General Assembly with no gaps, so laws here match them exactly: 2023-24 1,069 public + 68 private = 1,137; 2025-26 1,142 +
  74 = 1,216; vetoes 0 and 2 (SB 455 of 2025, HB 1882 of 2026). "What it does" is the General Assembly's bill summary
  ("As introduced, ..." / "As enacted, ...", LegiScan's description); the title is its first clause. Governor 10 days,
  Sundays excepted, no pocket veto; override a majority of the members. Leaders: Speaker Cameron Sexton; Lt. Gov. and Senate
  Speaker Randy McNally, who didn't run in 2026 (change `LEADERS` when the 115th General Assembly elects a new one in January
  2027). Governor Bill Lee is term-limited: add the new governor (January 2027) to `GOVERNORS` and states/legislatures.json.
  The governor's contact page and phone haven't been checked by the owner. sos.tn.gov turns automated requests away.
- **Committee agendas (2026-11-22):** from each bill's LegiScan `calendar` (its hearings: date, time, room, description), read with the bill (no queries of their own): `agendas()` calls legiscan_convert.agendas() (states/LEGISCAN.md). Today's and later meetings only. LegiScan's calendar has no cancellations; an entry dropped from a notice goes when the bill is next read, which within the daily getBill allowance can be hours after the change. Tested against 2026's saved calendars (with an earlier "today": 976 bills, all matched to records). LegiScan has Tennessee's House hearings until January 2026 only; February-April 2026 are Senate only (391, 1,434, 369 entries), so House committee agendas may be missing in 2027 too. capitol.tn.gov's robots.txt is "Disallow: /" for everyone but named search engines: no other source. January check: are there House entries in the calendars?
  **From the histories too (2026-11-22):** the bill histories name each committee meeting a bill is set for, House
  and Senate: "Placed on s/c cal Cities & Counties Subcommittee for 3/18/2026", "Placed on cal. Judiciary Committee for
  3/25/2026", "Action Def. in s/c Health Subcommittee to 3/24/2026", "Placed on Senate Finance, Ways, and Means Committee
  calendar for 4/21/2026", "Action deferred in Senate Judiciary Committee to 3/24/2026", "Rule #83(8) Suspended, to be
  heard in Senate ... Committee for 4/15/2024" (`set_for()` in convert.py; floor calendars, "Placed on Senate Consent
  Calendar for ...", "H. Placed on Regular Calendar for ...", aren't committee meetings and are left out).
  `history_meetings()` keeps a setting until a later line moves the bill or takes it off: another setting (settings
  written the same day all stand: Senate Finance, Ways and Means places bills on two days' calendars at once), "Taken off
  notice for cal in s/c ...", "Meeting Canceled", the committee's report or vote, a referral or subcommittee assignment
  elsewhere, a floor calendar; sponsor and amendment lines don't. legiscan_convert.agendas() adds the standing ones
  (today's and later) where the calendar has none, with the time another bill's calendar gives that meeting, else none
  (House meetings show the day alone). It also uses the history against the calendar: an entry for a meeting the history
  says the bill was taken off (LegiScan's calendar keeps them: 218 off-notice or canceled hearings of 2025-26 were still
  listed), or one naming another committee than the history's setting that day, is left out (LegiScan labels about one
  in seven of 2025-26's hearings with the wrong committee: 1,021 of 6,985, mostly "Senate Revenue Subcommittee of
  Finance, Ways & Means" for bills the history sets before State and Local Government or Commerce and Labor; 450 of
  9,473 in 2023-24). Both sources' committee names now read as the site's (`meeting_name()`, comm()'s spelling): "House
  Judiciary", "House Cities and Counties Subcommittee", "Senate State and Local Government".
  Tested by cutting the saved histories at an earlier morning (the calendars as saved): as of 2026-03-10, 2,125 entries
  (1,224 from the calendar, 901 added from the histories, almost all House); of the 901, 894 had the committee's action
  (a report, deferral, vote, off notice) on the meeting day or the next, 6 were undone before the day by lines not yet
  written that morning, 1 had nothing. As of 2026-04-13: 297 added, 285 acted on that day or the next, 12 undone before.
  How far ahead the settings are written (each meeting's first setting line against its day): 2025, House 3,815: 3% the
  same day, 18% the day before, 28% 5-6 days, 50% 7 days, 1% more; Senate 1,731: 16% the day before, 32% 4-6 days, 50%
  7 days. 2026, House 4,926: 7% the same day, 14% the day before, 30% 5-6 days, 47% 7 days; Senate 2,459: 9% the day before,
  36% 4-6 days, 52% 7 days. (Same-day and day-before settings are mostly the House Calendar and Rules Committee, about half;
  then Senate Judiciary and the House and Senate Finance, Ways and Means committees; half to two thirds of them in April.) A setting reaches the site when the bill is next read: its change_hash changes, and
  until its full record is read the master list's last action is added as a history line (bills() above), so a placement
  that is the bill's latest action shows within a run or two.
  Open States (looked into 2026-11-22, not used: the owner's decision): its v3 /events had 11 Tennessee meetings (November
  18 to December 17, 2026: Government Operations, Fiscal Review, the State Building Commission and other joint or interim
  committees), none with agenda items or bills. Their source is wapp.capitol.tn.gov/apps/schedule/WeeklyView.aspx, whose
  robots.txt is "Disallow: /" for everyone but named search engines, like capitol.tn.gov's. The API returns only recent and
  upcoming events, so 2025-26's House meetings can't be counted or matched from it; it would have to be polled in session.
- **Phones for a new General Assembly (2026-11-22).** LegiScan's people for the 115th (2027) came with its first prefiled
  bills, when only 22 of 131 members had a record there, so contacts_2027.json had a phone for 22 (the data check's FAIL).
  contacts.py now keeps, for a member in the same seat as in the last contacts file (same name), that file's LegiScan id,
  phone and office until LegiScan lists them: 131 of 131. A member first elected in November 2026 has none until LegiScan
  or Open States lists them.
