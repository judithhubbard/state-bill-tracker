# LegiScan states

Moved from CLAUDE.md (2026-11-19). Each state's own notes: states/tn, ok, me, ri, vt/NOTES.md.

- **LegiScan states (2026-11-08): Tennessee, then Oklahoma, Maine, Rhode Island, Vermont.** Their legislatures' sites bar
  automated readers in robots.txt, so `legiscan.py` downloads LegiScan's data (CC BY 4.0; monthly query budget shared and
  counted on GitHub) into data/<st>/legiscan/<session_id>/. Converters read only those files, never the API.
  (Maine's robots.txt, read again 2026-11-19, bars only its search pages and LawMakerWeb: its laws' signing dates and
  chapters, which LegiScan lacks, come from their bill pages, states/me/laws.py; see states/me/NOTES.md.)
  The budget (reworked 2026-11-13, before the January sessions): every run reads each running session's getMasterList
  (status and last action for every bill, kept as the bill's "ml" in meta.json; `bills()` in legiscan_convert.py adds
  that last action to an older saved copy's history, so stages stay current; checked by cutting every bill's history
  mid-way: all stages matched); getBill only within a daily allowance (`allowance()`: the month's remainder less a
  300 margin, a Sunday reserve and the master lists still to come, over the days left), status changes and major
  actions first, then new bills, then minor changes paced through the day; Sunday's dataset fills in the rest. In
  session: ~2,000 a month of master lists, the rest for full records, ending near 8,700 at most. A session that
  hasn't opened (`OPENS`, `begun()`) never marks a state incomplete. The next Legislature's session (2026-11-22) is
  read as soon as LegiScan lists it (`wanted()`: starting no later than next year), its master list once a day until it
  opens (`MASTERLIST_BEFORE`), and `folders()` shows a session starting this year or later with any bills (older ones
  need 100); Oklahoma's even-year folder replaces the odd year's only once it has as many bills. `python3 legiscan.py --dry-run [--today=DATE]
  tn ok me ri vt` prints what a run would request, without queries.
  `states/legiscan_convert.py` holds everything shared: `folders()` (regular sessions, keyed by first year), `people()`,
  `person_house()` (from the district "SD-028": LegiScan's `role` is sometimes stale), `load_session(Rules, session)` and
  `link_earlier()`. A state subclasses `Rules` and sets `data_dir`, `include()` (bill / amendment / None), `decode()` (each
  history line -> steps in the shared vocabulary in the module's `KINDS`: refer, report, subreport, held, commfail, floor,
  pass, fail, reconsider, concur, ccr, enrolled, sent, unsent, signed, nosign, veto, override, chapter, replaced ...),
  `committee_vote()`/`floor_vote()` (which roll calls are committee votes and which floor ones can be the bill's own),
  `group()` (companion bills as one record), `title()`/`summary()`/`what()`, `topics()`, `narrow()`, `seat()`,
  `earlier_key()`, `gates` (committees that schedule floor votes). Stages come from the steps, each house's location kept
  apart; "passed both houses" needs one version passed by both (unamended by the second, or agreed to), a conference
  report adopted by both, or enrollment; a reconsidered passage doesn't count. Floor roll calls are tied to a passage or
  concurrence step of the same day and house with a tally within 5 votes (the history's tally is the journal's; the roll
  call's own totals are kept), committee roll calls to a committee step that day: LegiScan attaches some roll calls to the
  wrong bill (TN SB 5 of 2025 carries another bill's House votes). LegiScan's `status` is only checked against
  (`python3 states/<st>/convert.py` prints `Rules.checks`): Tennessee's two vetoes of 2025-26 are "Enrolled" there. Each
  state's how.html credits LegiScan with links (the license requires it), and `textLinks` links each bill's LegiScan page.
  Contacts: Open States' current list says who holds each seat (party, email), LegiScan's person records give ids (the roll
  calls'), phones and offices. LegiScan has no committee members or chairs.
- **Committee agendas (2026-11-22):** `agendas(R, session)` reads each saved bill's `calendar` (LegiScan's hearings for it:
  date, time, room, description), so it costs no queries. The committee comes from the description (`hearing_name()`:
  "Senate Education 2ND REVISED Hearing" -> "Senate Education"; floor sessions left out), else `Rules.hearing_committee()`
  (Maine's say only "Hearing"). Only the latest revision of a committee's agenda for a day is kept. How fresh it is depends
  on when each bill's full record is next read (the getBill allowance above): a newly posted hearing changes the bill's
  change_hash, so it is read as a minor change, paced through the day. Tennessee's House hearings are missing from LegiScan
  after January 2026.
  The bill histories as a second source (2026-11-22): `Rules.history_meetings(b)` gives (standing, dropped, named), from
  the history: meetings the bill is set for that nothing later undid, added where the calendar has none (with the time
  another bill's calendar gives that meeting, else the day alone); meetings the history says it was taken off, dropped
  from the calendar's entries (LegiScan's calendar keeps postponed and canceled hearings); and every committee the
  history ever set it for on each day, so a calendar entry that day naming another committee is left out (LegiScan
  mislabels some). `Rules.agenda_name()` gives both sources one spelling. Tennessee uses all three (its histories carry
  every placement, "Placed on s/c cal Cities & Counties Subcommittee for 3/18/2026", which fills in the missing House
  hearings), Rhode Island the second ("Meeting postponed (04/22/2025)"). Oklahoma, Maine and Vermont have nothing to add:
  their histories name no upcoming committee meetings (Oklahoma's and Vermont's calendar lines are floor calendars, "Direct
  to Calendar", "Entered on Notice Calendar"; Maine's "Work Session Held" is after the fact).
