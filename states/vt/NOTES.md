# Vermont

Moved from CLAUDE.md (2026-11-19). Shared conventions, the data traps list and the site's code notes stay there.
This state's data comes from LegiScan: the shared design (legiscan.py, the budget, states/legiscan_convert.py) is in states/LEGISCAN.md.

- **Vermont (built 2026-11-08 from LegiScan):** `states/vt/convert.py` (the `Vermont` rules), `contacts.py` (run after
  legiscan.py), `towns.py` (run once). A page is a biennium (`YEARS = 2`; 2025-26 is one): bills are numbered once for it,
  live through both years' sessions (January to May or June) and die at its end, and Acts are numbered through it. Only H.
  and S. bills; resolutions left out. Constitutional amendments are Senate "Proposals", which LegiScan doesn't carry: none
  shown. The history is the two journals' wording, each line with its house; the other house's echoes ("Senate Message:
  ...", "House message: ...") change nothing. "Notice Calendar: Favorable ..." (House) and "Favorable report ... by
  Committee on X" (Senate) are a committee's report; "Pending entry on Notice Calendar, referred to Committee on X" a report
  and a second referral (House Rule 35(a), Senate Rule 31: Appropriations, Ways and Means, Finance). Committees never vote
  bills down. "Third Reading ordered" is the second-reading vote (step "second", added to the shared vocabulary: it changes
  nothing, but a roll call can be tied to it, `vote_kinds`); "Read third time and passed" the passage; the second house
  "passed in concurrence" (unchanged) or "... with proposal of amendment" (changed), then the first house "concurred in"
  it (not "with further amendment", which sends it back), or both adopt a Committee of Conference report. Roll calls: the
  Senate writes the tally on the question's line; the House on its own line, "Roll Call Results ..." before the line that
  says what passed or "Which was agreed to on a Roll Call ..." after it, so `classify()` reads a bill's lines together
  (the shared module's `decode_line()` hook, with the line's index) and puts each tally on its question; LegiScan's roll
  call's description is sometimes the other of the two lines (H.141 of 2025-26), so votes are matched by result and tally
  (`vote_key()`). Most votes are voice votes: about 60 roll calls a biennium are the bill's own. The governor's lines are
  filed under the journal day the house heard of them, often weeks off: their own wording dates them ("Signed by
  Governor on June 13, 2024"; the shared module's `extra["date"]`), with year slips fixed ("Vetoed ... May 23, 2023" filed
  in 2024, H.289). The Act number isn't in the history: it's the "As Enacted" text's name ("ACT044", municipal acts
  "ACTM003", shown "Act M-3", narrow "place"), added as the last step, and decides: H.890 of 2023-24 (Act 185) has a
  history ending with the Senate sustaining a veto, while the Legislature's status page says the governor approved it June
  28, 2024. Acts 1-N with no gaps; laws match them exactly: 2023-24 185 + 28 municipal = 213 (97 signed in 2023, 116 in
  2024); 2025-26 179 + 12 = 191 (78 and 113). Vetoes, matching the news: 2023 8 (6 overridden: S.5, H.217, H.494, H.509,
  H.386, H.305), 2024 10 (6 overridden June 17, plus H.890), 2025 5 (H.91, H.141, H.219, H.489, S.125), 2026 8 (H.674,
  H.710, H.727, H.817, S.183, S.190, S.218, S.230); none overridden since Democrats lost their supermajority in 2024. No
  summaries ("What it does" isn't shown): LegiScan's description is the official title. Seats: districts have names,
  numbered alphabetically in data/vt/district_names.json (towns.py, from the Census relationship files): Senate 1-16
  ("Chittenden Central" is 4), House 1-109; members "S:4a", "S:4b", "S:4c", "H:37a", "H:37b" in the order of their last names
  (New Jersey's scheme, both houses). "Where you live" lists the 255 towns and cities (Census county subdivisions; Essex
  Junction, a city since 2022, is still inside Essex there), split towns by land share. The address lookup is off (the
  Census geocoder gives district names, not numbers). Open States gives Progressives' party as "Democratic/Progressive"
  (counted with the Democrats) and three independents. Most members' phone is the State House's message line (shown as
  such). Governor 5 days, Sundays excepted; a pocket veto only if the General Assembly adjourns within three days of
  delivery; override two-thirds of members present. Each year's opening and last day are in `STATE.opened`/`dated` (add
  each year's). Leaders: Speaker Jill Krowinski, President pro tempore Philip Baruth (the new General Assembly chooses in
  January 2027). If the governor elected in November 2026 isn't Phil Scott, add them to `GOVERNORS` and legislatures.json.
  The governor's phone and contact page haven't been checked by the owner.
- **Committee agendas (2026-11-22):** from each bill's LegiScan `calendar` (its hearings: date, time, room, description), read with the bill (no queries of their own): `agendas()` calls legiscan_convert.agendas() (states/LEGISCAN.md). Today's and later meetings only. LegiScan's calendar has no cancellations; an entry dropped from a notice goes when the bill is next read, which within the daily getBill allowance can be hours after the change. Vermont's committees take bills up many times (testimony, walk-throughs); each is a meeting. Tested against 2026's saved calendars (203 bills, all matched).
