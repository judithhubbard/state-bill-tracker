# LegiScan states

Moved from CLAUDE.md (2026-11-19). Each state's own notes: states/tn, ok, me, ri, vt/NOTES.md.

- **LegiScan states (2026-11-08): Tennessee, then Oklahoma, Maine, Rhode Island, Vermont.** Their legislatures' sites bar
  automated readers in robots.txt, so `legiscan.py` downloads LegiScan's data (CC BY 4.0; monthly query budget shared and
  counted on GitHub) into data/<st>/legiscan/<session_id>/. Converters read only those files, never the API.
  The budget (reworked 2026-11-13, before the January sessions): every run reads each running session's getMasterList
  (status and last action for every bill, kept as the bill's "ml" in meta.json; `bills()` in legiscan_convert.py adds
  that last action to an older saved copy's history, so stages stay current; checked by cutting every bill's history
  mid-way: all stages matched); getBill only within a daily allowance (`allowance()`: the month's remainder less a
  300 margin, a Sunday reserve and the master lists still to come, over the days left), status changes and major
  actions first, then new bills, then minor changes paced through the day; Sunday's dataset fills in the rest. In
  session: ~2,000 a month of master lists, the rest for full records, ending near 8,700 at most. A session that
  hasn't opened (`OPENS`, `begun()`) never marks a state incomplete. `python3 legiscan.py --dry-run [--today=DATE]
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
