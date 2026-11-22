# Hawaii

Moved from CLAUDE.md (2026-11-19). Shared conventions, the data traps list and the site's code notes stay there.

- **Hawaii (built 2026-11-15, from Open States):** the Legislature's site (capitol.hawaii.gov) turns automated readers
  away, and data.capitol.hawaii.gov is the same site without the block, so neither is ever read (the owner's decision
  2026-11-13; links on the page point there for visitors). `states/openstates_bulk.py hi` puts Open States' bulk records
  down as the first copy and `python3 states/hi/fetch.py` asks the API for changes (see its docstring; 110 requests a day,
  sharing the free tier with Arizona) into data/hi/<year>/bills/; `python3 states/hi/contacts.py` (in states.json's run
  after fetch.py) builds the contacts; `states/hi/towns.py` was run once. A page per two-year Legislature (`YEARS = 2`,
  2025-26 is the 33rd; decided 2026-11-15): bill numbers run through both years and an unpassed bill carries over to the
  second year where it stands, which Open States repeats in the second year with its whole history ("Carried over to 2026
  Regular Session."), so a bill is read from the second year's folder when it's there (`keys()`); laws are numbered each
  year, so `chapter` is "250 of 2025" ("Act 250 of 2025"). Sessions from the third Wednesday of January to early May;
  `STATE.dated` and `P.SESSION_ENDS` hold each year's sine die and the governor's 35th and 45th working days after it
  (add each year's; `STATE.workdays()` leaves out weekends, Memorial Day, Kamehameha Day and July 4, which reproduces
  2023-26's deadlines). HB and SB only; constitutional amendments are bills ("PROPOSING AN AMENDMENT TO ARTICLE ..."):
  tagged "const", two-thirds of each house's members on final reading (or a majority in two successive sessions), then the
  voters; the governor gets notice, no veto; "Enrolled to Governor" on them isn't a sending (2024 HB 2802 and SB 2927; 2026
  SB 121 and SB 3219, matching Ballotpedia; HB 2509 of 2024 and SB 2152 of 2026 died in conference).
  `states/hi/convert.py` reads the history lines, each from one house's journal (the governor's lines appear in both:
  kept once, dated by the date the line names); sorted by date and Open States' `order` (newest first within a day, so
  reversed). Referrals "Referred to HLT, CPC, FIN" (in turn) and "AEN/TCA, JDC/WAM" (a slash: jointly; the first named is
  the bill's committee, "Heard jointly with ..." a step); committee codes named by year in `P.COMMITTEES` (from the houses'
  announced lists: the Senate reorganized in 2025 and 2026, the House in 2025). A committee's decision: "The committee(s) on
  AEN recommend(s) that the measure be PASSED, WITH AMENDMENTS. The votes in AEN were as follows: 4 Aye(s): ...; Aye(s)
  with reservations: ...; 0 No(es): none; and 1 Excused: ..." (member by member: `committee_vote()`); "deferred" / "HELD"
  is `heldAction` ("Deferred"; committees never vote bills down on the record); "deferred until <date>" is only a
  postponement. "Reported from X (Stand. Com. Rep. No. 570) ... referral to JDC" is the report; the second reading
  ("Report adopted; Passed Second Reading ... and referred to JDC", House "Passed Second Reading ...; placed on the calendar
  for Third Reading") sends it on; "Passed Third Reading" is the passage. The second house amending the bill anywhere (in
  committee, on second reading, which is where the Senate usually amends, or on third) means the first house must agree
  ("House agrees to Senate amendment(s)" then "Passed Final Reading") or both pass a conference draft (CD 1) on final
  reading; "Returned from Senate (Sen. Com. No. 828)." without "in amended form" is passed unchanged. "Transmitted to
  Governor." / "Enrolled to Governor." sent; "Notice of intent to veto" (a step; stage-4 status "On the governor's
  intent-to-veto list"); "Act 250, on 06/30/2025" signed, "Became law without the Governor's signature, Act 245", "Vetoed
  on ..." a veto, "... line-item appropriations veto" / "various appropriations throughout the bill" items vetoed (then
  signed as an Act), "Veto overridden - 2/3's vote" in each house then "Act 029, ..., veto override" (SB 921 of 2023, vetoed
  during the session). Laws and vetoes by year, matching the governor's announcements exactly (`python3 -m
  states.hi.convert`; Act numbers run 1-N with none missing): 2023 263 laws (263 of 274 enacted, 5 without signature, SB 921
  over a veto) and 11 vetoes; 2024 253 and 7; 2025 313 and 8 (321 enrolled less 8); 2026 266 and 1 (SB 3262; line items
  on SB 2600). Votes from the lines' own lists, not Open States' vote records (which split "Lee, M." into two voters and
  have no House floor votes): committee votes and every third/final reading and override member by member; the Senate's
  floor lines give the ayes ("Ayes, 24; ... Noes, 1 (Senator(s) Awa). Excused, 0 (none)." or "0 No(es): none. 1 Excused:
  ..."), the House's name only noes and excused, so its ayes are 51 less those (one too many while a seat is vacant: SB 121's
  House vote shows 43-6, the press 42-6). Names are surnames ("Lee, M.", "Keohokapu-Lee Loy" for Sue Lee Loy) tied to
  today's members (`seat_of()`; people file); for 2023-24 only surnames that also vote in the current Legislature's
  house; the rest stay names ("H?Ward", "S?Kidani": both voted in 2025-26 and are off the November 2026 people file).
  Sponsors: Open States splits "LEE, M." into "LEE" and "M." (joined back). Titles: the official titles say only
  "RELATING TO TAXATION.", so the title is the first sentence of Open States' abstract (the Legislature's description of
  the current draft, cut near 140 characters) and the summary is the official title plus the whole description; there's no
  other summary, so no "What it does" (How's "About this data" says so, and explains "Effective 7/1/3000", the defective
  date that keeps a bill in play for conference). Topics from committees (`COMMITTEE_TOPICS`) and words in the title,
  description and subject terms. Earlier Legislature linked by the same description word for word, or the same official
  title and first introducer with 60% of the description's words (454 of 2025-26's bills). Contacts: the people file (party,
  district, email; no phones exist there, none shown; photos on capitol.hawaii.gov left out); committees with the members
  who voted in them in the latest year, no chairs (the histories don't name them). Leaders: Speaker Nadine Nakamura,
  President Ron Kouchi; the 34th Legislature organizes in January 2027. Governor Josh Green (D): 10 working days during the
  session; for bills sent in its last 10 days or after (most), the intent-to-veto list by the 35th working day after sine
  die and a decision by the 45th, else law without signature; item vetoes on appropriations; override two-thirds of each
  house's members, in a special session on the 45th day for vetoes after the session (Art. III, sec. 16-17). The
  governor's contact form and phone ((808) 586-0034) are from governor.hawaii.gov's contact pages (read by program
  2026-11-15, not checked by the owner); the governor elected in November 2026 takes office December 7, 2026: add to
  `GOVERNORS` and legislatures.json if it isn't Green. Places (`towns.py`): Census-designated places (Hawaii has no
  incorporated cities) and the counties, separate Senate (25) and House (51) lists. data/hi/incomplete, written by fetch.py
  before the bulk import, stays until fetch.py's next run on GitHub removes it; until then build_site.sh skips Hawaii.
- (2026-11-19) A record's `last` is the day of the latest line the history shows, not of a "routine" line it leaves out
  (floor amendments, conferee changes, rescheduled meetings): 257 of 2025-26's and 324 of 2023-24's status rows had a date
  and no wording (HB 48: 2026-04-01, now 2025-12-08 "Carried over to the 2026 session").
- **The next Legislature (2026-11-22):** Hawaii has no prefiled bills: the 34th Legislature's (2027-28) are introduced from the opening day, January 20, 2027. fetch.py asks Open States for its session list daily while this year's is missing and reads it once listed; the current year's first copy never holds Hawaii back (`never_downloaded()`), and convert.py's `sessions()` shows a year as soon as fetch.py's first pass over it is whole and has a bill (the 500-bill rule is for a bulk import's partial copy).
- **Phones (2026-11-22):** from the Public Access Room's "Email, Room & Phone Directory" (the Legislative Reference
  Bureau's lrb.hawaii.gov, not capitol.hawaii.gov; robots.txt bars only /wp-admin/). The PDF's name changes with each
  edition (2026/11/2027-Room-Phone-Email-A.pdf, the 34th Legislature's, dated 11/10/2026), so `directory()` in
  states/hi/contacts.py reads the link from https://lrb.hawaii.gov/par/current-legislature/ once a day and the PDF only
  when the link changes (data/hi/par_directory.json). It lists names ("Awa, Brenton"), email, room and phone, no
  districts: each people-file member is matched in the same house by email, else surname and first name ("Keohokapu-
  Lee Loy, Sue L." is Sue Lee Loy). Until the 34th Legislature sits (January 20, 2027), the people file is the 33rd's:
  67 of its 76 members are in the new directory in the same house and get its phone; the 9 leaving (Belatti, Cochran,
  Gedeon, Pierick, Shimizu, Ihara, Rhoads, Fevella; Sayama, moving to the Senate) have none, as before. The directory's
  typo "sensayama@capitol.hawaii,gov" is fixed; emails stay Open States' (they agree for 66 of the 67; Sue Lee Loy's is repleeloy@ there, repkeohokapuleeloy@ in the directory). data_check's "emails
  that aren't addresses" FAIL came from it, and found three more states' (CT, AL, CO: their NOTES).
