# Nevada

Moved from CLAUDE.md (2026-11-19). Shared conventions, the data traps list and the site's code notes stay there.

- **Nevada (built 2026-11-09):** `python3 states/nv/fetch.py` reads
  NELIS (www.leg.state.nv.us/App/NELIS/REL/<session>/: server-built HTML fragments, no API; robots.txt bars only
  */Reports/* (the veto messages), exhibits, opinions and fiscal-note folders; see its docstring) into data/nv/<year>/;
  `python3 states/nv/contacts.py` (every session; add it to states.json's run after fetch.py) builds the contacts. The
  Legislature meets in regular session only in odd years, 120 days from the first Monday of February (`opens()`,
  `adjourns()` = day 120 in profile.js; the 83rd was 2025, the 84th opens February 1, 2027): a page per session labelled
  "2025–26" (`YEARS = 2`), the next session's prefiled bills (from late October) as the upcoming page. Special sessions
  are left out. The lower house is the Assembly (`LOWER = "A"`, seats "A:30", "Asm."; 42 Assembly and 21 Senate
  districts, drawn separately). `states/nv/convert.py` reads each bill's Overview page: the one-line summary is the title
  (without its "(BDR 52-503)"), the official "AN ACT relating to ..." title the summary, and the history, several steps to
  a line, matched by one tokenizer (`TOKENS`; `python3 -m states.nv.convert` prints any text it didn't read, and the laws
  and vetoes compared with the lists). The lines don't name the house: the bill is followed ("To Senate." / "In
  Senate."; a veto message goes to the house of origin). "From committee: Do pass" / "Amend, and do pass as amended" /
  "Without recommendation" are committee reports (no tallies; committees don't vote bills down: a bill not reported by the
  deadline dies, "(Pursuant to Joint Standing Rule No. 14.3.1, no further action allowed.)", the 14.3.1-.4 deadlines on
  days 68, 79, 102 and 109: `originDeadline()` is day 79, and `STATE.endedNote()` words the deadline deaths and floor
  defeats); "From committee: Concur in ... and further amend" is a conference committee's report, not a standing
  committee's. "Read third time. Passed[, as amended]. (Yeas: 24, Nays: 18.)" is the passage, "Lost." a defeat, "Action
  (of passage) reconsidered." undoes the house's last vote. "To enrollment." is passed both houses (after "Senate
  Amendment No. 667 concurred in." or both houses adopting a conference report), "Enrolled and delivered to Governor."
  sent, "Approved by the Governor. Chapter 60." a law (`STATE.lawWord` "Chapter", of the Statutes of Nevada), "Vetoed by
  the Governor." Laws and vetoes also come from the session's lists and agree with the histories bill for bill; chapters
  run 1-N with none missing: 2023 535 laws (AB 269, SB 266), 75 vetoes (the record reported at the time); 2025 519 laws
  (AB 288, SB 231), 87 vetoes (NELIS's list of 86 and SB 99, below). No veto was overridden. SB 99 of 2025 was vetoed June 2, 2025 and returned to the Senate with a veto
  message, but NELIS's history (read again 2026-11-09) shows only "Enrolled and delivered to Governor" and "(No further
  action taken.)", and it's on neither the laws nor the vetoed list: `VETO_FIX` in convert.py (a documented correction
  table) makes it a veto with a line saying the record misses it, for 87 vetoes in 2025, the press's count. Any other
  bill delivered and neither signed nor vetoed once the governor's time is up (`gov_due()`) gets "The records show no
  decision by the governor" and stays stage 4 without a deadline (`govDeadline()` returns none once past); under Art. 4,
  sec. 35 it would be law without signature, but SB 99 shows the record can just miss a veto, so no outcome is guessed. A veto
  during the session goes back to the bill's house at once ("Bill read with Governor's veto message", then "No further
  action taken"); a veto after the session (2023: 43; 2025: 54) goes to the next regular session, which can override it
  by two-thirds of each house (28 Assembly members, 14 senators): convert.py adds the line "Vetoed after the session
  ended: the veto goes back to the Legislature's 2027 session", which `STATE.vetoReturns()` reads (shared hook, added
  2026-11-09: tracker.html's status line, "what's next" and the ask to vote to override or sustain, until that session
  adjourns). An override would be "Passed, notwithstanding the veto of the Governor." (a guess at the wording: none in the
  data yet; check when the 2027 session acts). Joint resolutions whose bill draft is a "C-" request propose
  constitutional amendments: tagged "const", a majority of each house's members in two sessions in a row, then the voters
  at the next general election; they go to the Secretary of State ("File No. 24"), never the governor (2023 AJR 5, AJR 6,
  SJR 7; 2025 AJR 8: first passages). A resolution passed the second time is listed under its first session's number
  ("SJR 7 of the 82nd Session") in a list fetch.py doesn't read, so second passages are missing (`amendmentFinal` reads
  that wording if they're ever added). Other joint resolutions (memorials) are left out; the laws list includes
  resolutions, which aren't counted. Floor votes: each final passage member by member (votes/), matched to its history
  line by house, day and tally; NELIS calls every one "Passed", lost ones too (AB 500 of 2025: 25-17, short of
  two-thirds; then 20-22), so the history decides. SB 1 of 2023 carries two May roll calls that match none of its history
  lines (left out). Roll-call names "Anderson, Natha" match the session's member list by house, last name and first name;
  Sen. Heidi Seevers Gansert is "Seevers O'Gara, Heidi" in 2023's roll calls (`seat_of()` matches the first word of the
  last name). Committee-sponsored bills (prefiled for agencies, local governments and officials: 416 of 1,049 in 2023,
  453 of 1,119 in 2025) show the committee as sponsor ("Assembly Committee on Judiciary"), as Idaho's do, so
  legislators' sponsorship numbers count only their own bills; How's "About this data" says so. The next session's
  prefiled committee bills name no committee yet ("A Senate committee (not yet named)"). "What it does" is the
  Legislative Counsel's Digest ("From the Legislative Counsel's Digest."), each paragraph led by its "This bill ..." /
  "Section 3 of this bill ..." sentences, background-only paragraphs last, statute citations removed (`digest_text()`);
  appropriation bills have none. Topics: the NRS title in the bill draft number (`NRS_TOPICS`: "(BDR 52-503)" is Title
  52, Trade Regulations), committees (`COMMITTEE_TOPICS`) and title words. Earlier sessions linked by the same official
  title (one bill each), or the same member with 60% of the title's words and 40% of the summary's (`earlier()`; 26 from
  2025 to 2023, read over by hand), never laws or appropriations. Bill links: NELIS's overview by bill key. Hearings:
  `agendas()` reads each bill's Upcoming Hearings. Contacts: the member list (party, district, Carson City room and
  phone, Las Vegas office room, post), committees with chairs and vice chairs; emails from Open States' public-domain
  file (data/nv/openstates_people.csv; the Legislature's pages hide them behind Cloudflare's script), matched by seat
  and last name (2027's new members have none yet). Toby Yurek (Assembly 19) resigned in October 2025: left out of 2025's
  contacts. The 2027 list (members-elect, from November 2026) still shows 2025's leadership posts, so no posts are taken
  from it; Assembly members and senators take office the day after the election. Leaders: Speaker Steve Yeager, Senate
  Majority Leader Nicole Cannizzaro (the Lieutenant Governor presides over the Senate); the 84th session chooses its own:
  update `LEADERS`. Governor Joe Lombardo (R) ran again in November 2026; if a new governor takes office January 4, 2027,
  add them to `GOVERNORS` and legislatures.json. Governor 5 days (Sundays excepted) in session, 10 days after
  adjournment; a bill not acted on becomes law. The governor's phones and contact page are from gov.nv.gov (checked by
  program 2026-11-09, not by the owner). Places (`towns.py`, run once): cities, Census-designated places (most of the
  Las Vegas valley) and counties, separate Senate and Assembly lists.
