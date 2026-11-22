# Arizona

Moved from CLAUDE.md (2026-11-19). Shared conventions, the data traps list and the site's code notes stay there.

- **Arizona (started 2026-10-31, from Open States: see the az-open-states memory):** `python3 states/az/fetch.py` reads
  v3.openstates.org with the owner's free API key (~/.openstates_api_key; GitHub secret OPENSTATES_API_KEY). The free tier
  allows 250 requests a day (20 bills each): the first copy of three sessions takes two days, resuming from the saved page,
  and stops cleanly at the daily limit; then a day's changes (updated_since) are a few requests. Local runs and GitHub's
  share the quota. Years older than the API's three (2023) come only from an Open States bulk file
  (`states/openstates_bulk.py az`, run before fetch.py; the owner names it in states/az/bulk.json:
  "AZ_56th-1st-regular_json_<id>.zip"), never from the API. The bulk file names sponsors and voters without person ids:
  `roster()` in convert.py ties each name to who held a seat in that house that session, from states/az/people.json
  (Open States' public-domain people data, current and retired, roles since 2023; made once by `states/az/people.py`
  from raw.githubusercontent.com, committed, since 2023's members won't change), by full name or another of the person's
  names, else first and last name, else last name and initial, else a last name only one candidate has (each looser test
  only when no stricter one matched in either house, the bill's house first: Sen. Anna Hernandez co-sponsoring a House
  bill isn't Rep. Alma Hernández); members seated that day first, then anyone seated that session (roll calls list members days after they leave: Liz Harris, expelled
  April 12, 2023). `ROLE_FIX` adds Flavio Bravo's House role (District 26 until his Senate appointment on May 8, 2023),
  missing from his file. Every 2023 sponsor name (6,384 on 1,562 bills) gets a party, and the
  prime sponsor's 2023 district goes on the bill; every roll-call name resolves to a 2023 member, but, as in the API's
  years, a vote is tied to a seat only when the voter holds one now (their current seat) (62% of 2023's not-yes names; the rest are
  members who have since left, kept as names: "S?Juan Mendez"). The API's years use the same people data: a sponsorship
  without an id (239 in 2024, members who had left) is matched by name the same way, also against roles that ended in the
  three months before the session for full names (Open States ends Amish Shah's, Jennifer Longdon's and Leezah Sun's terms
  on January 1, 2024, though they're named on 2024's bills), and one with an id gets that session's district and house
  (`by_id()`), not the person's current ones. Joseph Chaplik and David Marshall, Sr. left the House mid-2026 (Open States
  ends their terms March 25 and April 22; their last votes are February 26 and April 16), so their 2026 votes are names. `states/az/azleg.py` reads www.azleg.gov at its 120-second crawl delay (member rosters for phones and
  rooms; the committee pages list meetings only, so there are no chairs yet; resolutions' official titles to tell
  constitutional amendments from referred measures). `states/az/convert.py` uses Open States' action classifications;
  some committee reports don't name their committee. Open States has no chapter numbers, and about 10 bills a year stop
  after passing both houses (gaps in its records). 30 districts with a senator and two representatives each (New Jersey's
  scheme, "H:12a"/"H:12b"). Earlier years linked by short title.
- **Committee agendas (2026-11-22):** official, not Open States: `agendas()` in states/az/azleg.py, first in its run,
  reads www.azleg.gov at the 120-second crawl delay (robots.txt allows /standing-committee and /agendas/; apps.azleg.gov,
  "Disallow: /", isn't read). /standing-committee lists every standing committee's meetings of the session (day, committee
  and its id, Revised and Cancelled boxes, time such as "2:00 P.M. or upon recess or adjournment of Floor", and the agenda
  PDF, /agendas/0217012170130.pdf); each PDF ("ARIZONA HOUSE OF REPRESENTATIVES ... COMMITTEE ON EDUCATION", one row per
  bill starting "HB2313") is read with pdftotext and kept as text in data/az/azleg/agendas/ (read.json: when each was
  read). Meetings from yesterday to three weeks ahead, cancelled ones left out, into data/az/<year>/agendas.json ("House
  Education", "Senate Rules"); `agendas()` in convert.py keeps meetings from today on. At the crawl delay about seven PDFs
  fit in a run (`AGENDA_LIMIT`, 14 minutes, with the list's own request): unread agendas first (soonest first), then ones
  the list shows revised or retimed, then any read over twelve hours ago (revisions keep the address: "REVISED #3").
  The workflow's az run needs pdftotext (poppler-utils), as MI's and NC's do. Tested 2026-11-22 offline with the list as
  served that day (388 meetings of 2026) and the House Education agenda of 2026-02-17 (21 bills; the five whose records
  were already downloaded matched, and the rest are in the same form, HB2313) and live (no meetings ahead). Untested: the
  list in January 2027 (whether it shows the 58th Legislature's meetings by default), Senate agendas' layout, and how
  far ahead agendas are posted against seven PDFs a run.
- **Next year's prefiled bills (2026-11-22):** Open States lists 58th-1st-regular (2027-01-11) already, with no bills on
  2026-11-22 (2026's first prefiled bill was dated 2025-11-15). fetch.py asks for one bill a run and makes data/az/2027/
  only once there is one; convert.py's `sessions()` shows this or next year from its first bill (500 only for past
  years). A year not begun never marks Arizona incomplete.
- **Summaries (2026-11-22): the yearly Summary of Legislation.** Both research staffs publish one PDF a year about two and
  a half months after sine die, on www.azleg.gov (robots.txt allows /alispdfs/): /alispdfs/<57>leg/<2R>/House/
  SummaryComplete.pdf (House Majority Research Staff's "Book", Last-Modified 2026-08-27 for the session that ended June 13)
  and .../Senate/SummaryComplete.pdf (Senate Research Staff's "Spiel", 2026-09-25). Each has a paragraph on every measure
  that passed the Legislature: laws (with chapter), vetoed bills and measures sent to the voters. `books()` in azleg.py,
  after the resolutions, reads each year's two once at the crawl delay (from August for the current year; a 404 again
  after a month) into data/az/azleg/books/<year>-House.txt and -Senate.txt (pdftotext). `states/az/books.py` reads them:
  the House's entries ("HB 2502 (Chapter 201): title", the paragraph, "Effective: ...", "Click here for bill history.")
  first, the Senate's ("title (S.B. 1020) – Chapter 13", then paragraphs to the next heading; its committee boxes, page
  numbers and "SEE THE ... COMMITTEE." pointers left out) for the rest. 2024's House file at that address is the House
  Journal, not the book, so 2024 is the Senate's. "What it does" says which ("From the House Majority Research Staff's
  Summary of Legislation."). A budget bill's mirror ("HB 4155/SB 1848") isn't given the summary: it didn't pass. Before:
  no "What it does" at all. After (2026-11-22, with a local copy whose 2026 first copy wasn't finished): 2024 333 of 1,708
  bills (19.5%: all 257 laws and every veto), 2025 440 of 1,779 (24.7%: all 265 laws, 174 vetoes); 2023 and 2026 the same
  once their bills are in (373 and 440 entries in the House books). Bills that never passed still have none (Open States'
  "documents" links to the House summaries and Senate fact sheets are the next step). The eight books were read once on
  2026-11-22 from the owner's computer.
- **Veto letters (2026-11-22, OCR, the owner's decision):** the governor's own copies (linked from azgovernor.gov's
  "Legislative Action Update" releases) are on mcusercontent.com, whose robots.txt is "Disallow: /" for every program,
  and azgovernor.gov's news index answers 403: not used. The Legislature keeps the same letters on www.azleg.gov, which
  its robots.txt allows: /govlettr/<56|57>leg/<1R|2R>/<hb4115>.pdf (2023-24 is the 56th, 2025-26 the 57th; 1R odd
  years). They are scans with no text layer. `veto_letters()` in states/az/azleg.py, last in its run, asks for the letter
  of each bill Open States shows vetoed, at the 120-second crawl delay, for at most 22 minutes a run (about ten letters;
  2024-26 is about 300 vetoes, so the first pass takes a few weeks of runs), the newest year first, and reads it once by
  OCR into data/az/<year>/vetoes/<HB4115>.json (states/letters.py's `scanned()`); a 404 is noted in
  azleg/veto_letters_missing.json and asked for again after a month. `veto_message()` in convert.py keeps the reasons
  (after "RE: ..." and "Speaker Montenegro,", to "Sincerely,") on the vetoed bill, with `ocr` and the letter's address
  (the page says it was read from a scan and links it). Quality on four letters (HB 4115 of 2026, HB 2091 and SB 1001 of
  2025, HB 2063 of 2024): typed, clean scans in Hobbs's one-page format; read with no errors seen against the page image.
