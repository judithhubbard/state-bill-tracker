# Wisconsin

Moved from CLAUDE.md (2026-11-19). Shared conventions, the data traps list and the site's code notes stay there.

- **Wisconsin (started 2026-10-31):** `python3 states/wi/fetch.py` reads docs.legis.wisconsin.gov (see the wi-data-sources
  memory; robots.txt blocks the feeds, so changes are found from the bill lists and the journals, plus a weekly re-read):
  each bill's history, authors and the Legislative Reference Bureau's analysis ("What it does"), the roll calls member by
  member, the committee records, members and committees. The first copy takes about 6-7 hours at a request a second.
  `states/wi/convert.py` reads the history lines ("Read a third time and passed, Ayes 53, Noes 45"; the second house
  "concurred in"; "Report correctly enrolled"; "Report approved by the Governor ... 2023 Wisconsin Act 123", with partial
  vetoes; bills pending at the last floor period "Failed to pass pursuant to Senate Joint Resolution 1"). The lower house
  is the Assembly (`LOWER = "A"`, seats "A:82"). Senate roll calls give names in capitals cut to 14 characters
  (`members_index()`). The last general-business floor period's date is `STATE.dated` (add each session's). The Assembly
  Committee on Rules and the Committee on Senate Organization schedule floor votes. Cities and villages crossing county
  lines are one entry (`towns.py`); towns that share a name carry their county.
- **Committee votes and veto messages (2026-11-22):** committee votes member by member come from the Records of
  Committee Proceedings fetch.py already saved (rocp/<id>.json): `committee_votes()` in convert.py reads each record's
  paragraphs again (`motions()`), keeping the motions on the bill itself ("... that Assembly Bill 1 be recommended for
  passage", "... for concurrence", "... for adoption"; amendments and Joint Finance's budget papers left out), passed or
  failed ("WITHOUT RECOMMENDATION, Ayes 4, Noes 12"). The Senate's executive sessions are mostly "Held by Paper Ballot",
  whose motions read "Moved that Senate Bill 124 be recommended ..." with no mover: fetch.py's `parse_rocp()` read only
  "Moved by ..." before this, so the converter doesn't trust its saved motions. A joint committee (Finance, Tax
  Exemptions) gives one vote per house. The committee's name is today's (from the record's address, "utilities_
  technology_and_tourism"), matched to contacts' committees as the page matches names. Checked on the local copy (Nov 1):
  684 votes on 550 bills of 2025-26, every name tied to a seat, and 1,093 of 1,106 "Report passage recommended ... Ayes
  n, Noes m" history lines matched a vote with that tally (the rest had records the local copy lacked).
  Veto messages: `veto_messages()` in fetch.py reads the "Veto Message" PDF each vetoed bill's page links
  (/document/vetomessages/<year>/AB1.pdf) once into vetoes/<AB1>.txt (pdftotext -layout; an empty file for a scan: 2023-24's
  SB 145 and a few others are scans, read by OCR since 2026-11-22: see below). `veto_message()` in convert.py puts the two columns in order
  (states/letters.py) and keeps the letter from "To the Honorable Members of the ..." to "Respectfully submitted", cut at
  3,500 characters; a partly vetoed law gets it as `kind: "line-item"`. Both show after the next download run (the PDFs
  aren't in the cache yet; the committee votes need only a rebuild).
  Scanned veto messages (2026-11-22, OCR approved by the owner): after the text pass, `veto_messages()` reads each
  message whose .txt is empty once more through states/letters.py's `scanned()` (pdftoppm at 300 dpi, tesseract), into
  vetoes/<SB145>.json ({url, ocr, raw}), at most 6 minutes a run; never read twice. `scanned_message()` in convert.py
  keeps "To the Honorable Members ..." to "Respectfully submitted" (OCR runs both into the paragraph next to them, so
  they're split off first) and marks it `ocr` with the PDF's `url` (the page says it was read from a scan and links the
  original). Which of the 167 messages (72 for 2023-24, 95 for 2025-26 on 2026-11-22) are scans shows only after the
  next run; locally only SB 145 of 2023 (APRN licensure, a one-page Ricoh scan) was checked: word for word against the
  page image (one "I]" for "I", fixed).
- **Committee agendas (2026-11-22):** `agendas()` in states/wi/fetch.py (first in each full run) reads the Legislature's
  committee schedule, https://committeeschedule.legis.wisconsin.gov/ (no robots.txt; the docs site's robots.txt, which
  bars /feed/, doesn't cover it), one page: the address its stub page's script loads,
  `/?StartDate=<today>&CommitteeID=-1&CommItemVisibleName=-1&TopicID=-1&ViewType=listWeek&ReloadCache=True` (about 2 MB),
  which carries every meeting of the biennium as calendar events in its script (`parse_schedule()`: title "Judiciary and
  Public Safety (Senate)", start, classNames with "canceledMtg" when canceled, eItems "SB6; SB25"). Public hearings and
  executive sessions from yesterday to three weeks ahead go into data/wi/<session>/agendas.json ("Senate Judiciary and
  Public Safety", "Assembly Rules", "Joint Finance"; Legislative Council study committees "Joint ..."); `agendas()` in
  convert.py keeps meetings from today on. A failure keeps the last file. Tested 2026-11-22 on the page as served that
  day (840 meetings of 2025-26 listed, 22 canceled left out): 2026-02-02 to 02-23 gave 93 meetings and 283 bills, every
  one matched a record; live, no meetings ahead. Untested: the page in January 2027 (whether StartDate in the new
  biennium lists 2027-28's meetings), and an "eItems" naming a substitute amendment rather than the bill.
- **Next session (2026-11-22):** docs.legis answers 404 for /2027/ (bills, legislators, committees) on 2026-11-22; the
  session is read from January (it convenes January 4, 2027). Its missing list, members and committees don't hold
  Wisconsin back until April 1 (bill pages never read still do), and convert.py's `sessions()` shows it from its first
  bill (past sessions still need over 1,000).
- **Floor calendars (2026-11-22, states/floorcal.py):** no new download. `floor_days()` in convert.py reads each bill's own
  history: "Placed on calendar 2-11-2026 by Committee on Rules" (or "pursuant to Senate Rule 18(1)", "Joint Rule 82") names
  the day the house takes it up, filed a day to a week ahead in the house the line is under. Shown as "On the Senate
  calendar <day>" (`"listed"`): in 2025-26, 94% of Senate and 76% of Assembly placements had a floor vote that day or the
  next; the rest were laid on the table or sent back to Rules. Days from today on. Tested with FLOOR_TODAY=2026-01-01: 357
  bills on 12 calendar days, all records' numbers. (`agendas()` no longer returns nothing when agendas.json is missing.)
- **"What it does" leads with the bill (2026-11-23):** a third of the LRB analyses open with current law ("Under current
  law, ..."), and in most of those "This bill ..." comes third or later. `lead_first()` (states/lead_first.py, shared with
  CO) now moves the first sentence that says what the bill does ("This bill ...", "Under the bill, ...", "Beginning ..., this
  bill requires ...") to the top with the rest of its paragraph and any numbered list it introduces; the background follows
  in its own order, word for word (only the order and, where a paragraph is split, a line break change). It stays put when
  that sentence leans on the background ("This bill eliminates that prohibition.", "expands this definition", "the same",
  "instead", "these", "the program" with nothing saying which), so 14-15% still open with current law (32% and 35%
  before; data_check LOOKs over 5%). On the local copy: 400 of 2,295 analyses of 2023-24 and 481 of 2,424 of 2025-26 reordered; no word added
  or lost. A few issue matches move with the new opening (issues.py reads the first 250 characters like the summary):
  2023-24 +4/-2 "assault"; 2025-26 +8/-2 "assault", -4 "homeless" (e.g. AB 596, AB 597).
  Done in convert.py when texts_<session>.json is written: a rebuild picks it up, no download.
