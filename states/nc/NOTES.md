# North Carolina

Moved from CLAUDE.md (2026-11-19). Shared conventions, the data traps list and the site's code notes stay there.

- **North Carolina (started 2026-10-31):** `python3 states/nc/fetch.py` reads ncleg.gov (see the nc-data-sources memory;
  robots.txt Crawl-delay 2): each session's bill list (RSS), each bill's page (sponsors, keywords, Public/Local, session
  law, roll-call table, history), each roll call member by member, members, committees with chairs. The first copy takes
  about 6 hours. `states/nc/convert.py` reads the history ("Ref to the Com on X, if favorable, Y": X first; "Passed 3rd
  Reading" is the passage; "Ordered Enrolled"/"Ratified" passed both houses; "Ch. SL 2025-13" a law, `STATE.lawWord`
  "Session Law"). Every Senate bill starts in the Senate Rules Committee (`STATE.gates`); both houses' Rules committees are
  called "Rules". Local bills become law when ratified, without the governor (narrow kind "place"); constitutional
  amendments are bills too ("Constitutional Amendment ..."), three-fifths, then the voters. Roll-call pages print "None"
  for an empty vote group. Emails from Open States (the pages hide them behind Cloudflare's script); members who resigned
  stay on the member list with a note. "What it does" is the Legislative Analysis Division's bill summary (neutral staff summaries,
  PDFs): fetch.py's `summaries()` runs last, in the time left, and never marks the state incomplete; it reads each heard
  bill's list (/Legislation/Bills/Summaries/<year>/<H4>; unheard bills have none) and each chosen PDF once
  (dashboard.ncleg.gov/api/Services/BillSummary/<year>/<id>; "(e3)", "(CS...)", "(CCS...)", "(sl)" in the id name the
  version), saved as text in summaries/. `states/nc/texts.py` takes the session law's summary (the conference version's
  when a law is summarized part by part, else up to 8 parts), else the newest bill summary, never an amendment's alone,
  and none when its title shares no words with the bill's current one (rewritten bills); it keeps the overview, the
  analysis when the overview is short and the effective date, without current law, tables or staff credits; the label
  names the version. From 2026-11-14 to 2026-11-22 the reader failed on every run (`part_key()` compared a number with a word when a law's parts mixed "Sec. 1D.10" with "Sec. A" or a plain title: TypeError) and read no summaries; its tokens are now tagged, and "Subpart II-B" sorts after "Part II". Checked on six bills of 2025 (H562, H1003, H1012, H1035, H1040, H1089). Counties and places by district (`towns.py`).
- **Committee agendas (2026-11-22):** `agendas()` in fetch.py reads the Legislative Calendar's month pages
  (https://www.ncleg.gov/LegislativeCalendar/<m>/<yyyy>: this month's, and the next one's when three weeks ahead falls in
  it; Crawl-delay 2, its own fetch `calendar_page()` that never stops the run) after the bills and contacts, before the
  summaries, into data/nc/<session>/agendas.json: meetings from yesterday to three weeks ahead. Each committee event has
  its chamber label ("House: "), its committee link (/Committees/CommitteeInfo/House/21; "-- UPDATED", "-- CANCELLED"
  after the name), its time and the bills it lists (/BillLookUp/2025/H126). Canceled and postponed meetings are left out;
  non-standing committees (no chamber label) are named "Joint ..." unless their name says the house. convert.py's
  `agendas()` keeps meetings from today on and calls each house's Rules Committee "Rules", as the histories do. Tested
  against June 2025's page (141 bills on 71 meetings; 135 matched records, the other 6 confirmation and honorary
  resolutions, which aren't kept); the live page has no committee meetings now (November 2026). The current calendar
  page (/LegislativeCalendar/) only lists what's ahead; month pages were used so a meeting from yesterday still shows.
- **Next session (2026-11-22):** the 2027 All Bills feed already answers, with no items (no prefiling: bills are filed
  after the session convenes, January 13, 2027). An empty feed for the current session doesn't hold the state back,
  convert.py's `sessions()` shows it from its first bill (past sessions still need over 1,000), and the session just
  ended has the bills whose feed entry changes read again until February 1.
- **Veto messages (2026-11-22, read by OCR, the owner's decision):** each vetoed bill's history links a "Veto Document" on its
  "Vetoed" line (webservices.ncleg.gov/ViewBillDocument/2025/7283/0/H96-BD-NBC-16795; that host has no robots.txt, the
  crawl delay of ncleg.gov's is kept): the governor's signed "Objections and Veto Message", then the ratified bill with the
  clerk's stamps, scanned. Some carry Acrobat's own OCR as a text layer ("State of :Nortfi Carol1na"), so `veto_letters()`
  in fetch.py reads each with tesseract itself (states/letters.py's `ocr_pdf()`, first 3 pages), once, into
  <session>/vetoes/<H96>.json, at most 8 minutes a run after the agendas; vetoes both houses overrode are skipped (43 of 47
  in 2023-26). `veto_message()` in convert.py keeps the reasons, from after the title ("House Bill 96: AN ACT ...") to
  "Therefore, I veto the bill.", for vetoes that stand, when the document names its own bill. 2023-24 has no standing veto
  (every one overridden); 2025-26 has 6 (H 96, H 171, H 377, H 437, H 958, S 50). Quality (H 96, H 171, H 377, S 50 checked
  against the scans, some faint photocopies): the message text read almost perfectly ("origmally" in H 96); the stamps and
  handwriting after it are junk and are cut off.

- **"What it does" from the bill's own text (2026-11-26):** bills with no staff summary get a lead quoted from the bill as
  filed (`states/nc/billtext.py`, states/billtext_lead.py): the "Filed" edition's HTML twin (.../HTML/H10v0.html, Windows
  text), at the 2-second crawl delay (fetch.py's clock), at most 8 minutes a run (about 240), after the summaries,
  laws first; section captions ("SECTION 1. Establishment. –") left out, "reads as rewritten:" read as an amendment (its
  underlined whole sentences count). Sections in data/nc/<session>/leads.json; texts.py adds the leads to
  texts_<session>.json for bills with no summary.
