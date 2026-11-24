# Louisiana

Moved from CLAUDE.md (2026-11-19). Shared conventions, the data traps list and the site's code notes stay there.

- **Louisiana (built 2026-11-14):** `python3 states/la/fetch.py` reads
  legis.la.gov (no API; see its docstring) into data/la/<year>/; `python3 states/la/contacts.py` (every run; add it to
  states.json's run after fetch.py) builds the contacts; `states/la/towns.py` was run once (Census files; parishes). A page a
  year (`YEARS = 1`): a general session in even years (second Monday of March, 60 legislative days in 85 calendar days) and a
  fiscal session in odd years (second Monday of April, 45 in 60; five non-money bills per member), `session_kind()`
  "general"/"fiscal", labels "2026 general"; `opens()`/`sessionEnds()`/`vetoSession()` (40 days after) in profile.js compute
  them (no `dated`). HB and SB only; constitutional amendments are bills too (the site's ConstAmendments list, which also
  names three whose titles don't say so, HB 666/667 and SB 157 of 2024, or "Constitutional amendment" in the title): two-thirds
  of each house's members, then the voters at the election the bill names (`ballotLine()`), never the governor; they get Act
  numbers ("Becomes Act No. 406." after "presented to the Secretary of State"), kept as a step, no `chapter`, stage 3. Bills
  withdrawn before introduction are left out. `states/la/convert.py` reads each history line (newest first on the page; sorted
  by day, the page's order kept within a day): prefiling with a provisional referral (the introduction is the first-day
  referral), "Read by title, under the rules, referred to the Committee on X" / "Read second time by title and referred to";
  reports "Reported favorably (11-0)" (the House's carry tallies, kept as tally-only committee votes; the Senate's don't),
  "with amendments", "by substitute" (the old bill "Becomes HB 694": `endedNote()` "Replaced by HB 694"), "To be recommitted
  to" + "recommitted to the Committee on Appropriations" (a second committee); "Involuntarily deferred" (voted down, `commFate`
  "defeated"); the Legislative Bureau's review isn't a committee vote; "Recalled from Committee"/"Discharged" go to the floor.
  Passage: the House's "roll called on final passage, yeas 99, nays 0. Finally passed", the Senate's "passed by a vote of 39
  yeas and 0 nays"; "Failed to pass" (51-50 can lose: a majority of the members, 53/20, or two-thirds); "Reconsidered." undoes
  the house's last vote. "Received from the Senate with amendments" means the first house must concur ("Senate amendments
  concurred in" / "Amendments proposed by the House read and concurred in"), or both houses adopt a conference report;
  "Enrolled ..." is passed both houses. Governor: "Sent to the Governor", "Signed by the Governor [with one or more line-item
  vetoes]. Becomes Act No. 1.", "Becomes Act No. 300 without the Governor's signature.", "Vetoed by the Governor." or only
  "Veto message received and read" (trap: SB 89, SB 111, SB 181 of 2025 have no "Vetoed" line, and SB 89's status says
  "Reconsideration - Senate final passage"; the vetoed list decides). Totals match the bill statuses and the vetoed list
  (VetoBills.aspx) bill for bill (`python3 -m states.la.convert`): 2024 787 laws (37 without signature), 27 vetoes, line items
  HB 1, 2, 781, 782, 5 amendments; 2025 510 (56), 15 vetoes, line items HB 2, 460, 463, 6 amendments; 2026 962 (100), 6 vetoes,
  line items HB 1, 2, 312, 10 amendments. Act numbers run 1-792, 1-516, 1-972 with none missing or repeated (laws plus
  amendments). No override is recorded in 2024-26. Votes: floor votes member by member from votes/<doc>.json (YEAS, NAYS,
  ABSENT; matched by house, bill, day and tally; no co-author, amendment or motion votes), else the history's tally (on
  2026-11-14 only 2026's 360 vote PDFs were read: 300 of 2,625 floor votes name anyone). Committee votes member by member from
  2026's cvotes ("Favorably"/"Report with Amendments" with a recorded tally; "Without Objection" has none); "Defer Voluntary"
  adds "Deferred by the X Committee at the author's request" (`heldAction`, `commFate` "held", `heldLabel` "Deferred").
  Names: surnames, "Carter, R." where shared (matched to any given name's initial: "Johnson, T." is C. Travis Johnson),
  accents and suffixes aside ("Galle" is Gallé, Jr.; "Barthelemy" is Barthelemy II), "Mr. Speaker"/"Mr. President"
  (`SPEAKERS`, `PRESIDENTS`), within the house, never a member first elected after the session (members.json "elected");
  members who left are names (2026: Selders S14, Stagni H92, Wright H77, whose seats are vacant). Seats "S:12", "H:71"
  (separate maps, 39 and 105). Authors are tied to seats by their page link's district when the surname matches (Jason
  Hughes's and Julie Emerson's districts have new members), shown by their author name ("Tehmi Chassion"). "What it does" is
  the digest (docs/<doc>.txt): the résumé digest of the bill as passed, else the newest "Digest of HB1 ..." (House
  Legislative Services' for House bills), header and amendment summaries dropped, "Proposed law"/"New law" before "Present
  law"/"Prior law" background, page breaks mid-sentence rejoined, cut after 3,000 characters; on 2026-11-14 only 267 House
  digests of 2026 were downloaded (none for the Senate yet: check the label's "by ..." when they arrive). Titles: the part
  after the subject keyword ("COURTS: ..."), trailing notes (votes needed, fiscal notes, effective dates) dropped; the keyword
  is the summary line and gives topics (`KEYWORD_TOPICS`), with committees (`COMMITTEE_TOPICS`). Local and special bills (a
  "Public Notice" document, not retirement bills) are narrow "place"; APPROPRIATIONS/JUDGMENT bills "person". Earlier years
  linked by the same short title and primary author, never laws or budget bills. Contacts: members' pages (district office
  and phones, email, parishes, party), committees with chairs and vice chairs (ex officio members left out). Leaders: Senate
  President Cameron Henry (members' pages); the House's pages name no posts, so the Speaker, Phillip DeVillier, is the member
  ex officio on all 16 House committees (Mike Johnson, on 14, is presumably the Speaker Pro Tempore; not shown). Governor
  Jeff Landry (R, since January 8, 2024; John Bel Edwards before): 10 days in session, else 20 after delivery; item vetoes
  on appropriations; override two-thirds of each house's members (26, 70). The governor's contact page, Constituent Services
  phone and mail address are from gov.louisiana.gov/contact-the-governors-office (read by program 2026-11-14, not checked by
  the owner). Places (`towns.py`): cities, towns, villages, Census-designated places and parishes, separate Senate and House
  lists ("Albany town" is a real Louisiana town, not New York leaking in).

- **Veto messages (2026-11-22):** the "HB1194 Veto Message" documents fetch.py already reads (`wanted_docs()`, into
  docs/<id>.txt: scans with an OCR layer) are shown: convert.py's `veto_message()` keeps the letter from "Dear Speaker
  ...:" to "For Louisiana," without the "RECEIVED" stamp's fragments (lines with under three letters), the second page's
  header (its date, "House Bill 1194 Veto Message") and a line-item veto's list of lines struck ("Veto No. 1: Delete
  Lines 1 through 3 on Page 95 of 268"); a line-item veto is `kind: "line-item"` on the law. Checked on HB 1194 and HB 1
  of 2026 (the two the local copy has; the cache has the rest: 31 in 2024, 18 in 2025, 9 in 2026). Needs only a rebuild.
- **Committee agendas (2026-11-22):** `agendas()` in states/la/fetch.py, run after the bills, documents and committees,
  writes data/la/<year>/agendas.json ({"HB165": [["House Committee on Appropriations", "2026-04-27T09:00:00"]]}; next
  year's file too for prefiled bills); convert.py's `agendas()` words the names as the histories do ("House
  Appropriations"). It reads legis.la.gov/legis/ByCmte.aspx (the Committees page's "Upcoming meetings", House, Senate and
  joint, a plain GET; the home page's list needs a postback and isn't used), then each listed meeting's
  Agenda.aspx?m=<id> (HTML: linkTitle "House Committee on Appropriations", lDate "April 27, 2026", lTime "9:00 a.m.",
  lStatus, and the instruments, each linked BillInfo.aspx?i=<instrument id>). Only HB and SB, only when the instrument id
  is that bill's in the year's list.json (so an extraordinary session's HB 1 isn't taken for the regular session's), only
  meetings today to three weeks ahead, not canceled or postponed. legis.la.gov has no robots.txt (404). Tested on saved
  2026 agendas (House Appropriations 4/27/2026 and Transportation 5/11/2026, today set to 2026-04-20: 23 bills, all
  matching records; HR 243 left out) and live on 2026-11-22 (6 interim meetings listed, no bills). Untested live: the
  Senate's agenda pages during a session (same Agenda.aspx template, not seen with bills), and how far ahead meetings are
  listed (House notices are posted about a week ahead under the rules).
- **Summary line (2026-11-23):** the subject keyword ("Capital outlay", "Schools/charter") is the summary line only when it
  says something the title doesn't: when its words appear in order in the title (`repeats()` in states/lead_first.py:
  "Capital outlay" for "Provides for the comprehensive Capital Outlay budget") it's left out, so the panel's "What it
  does" isn't a label repeating the title. 348 of 1,484 bills (2024), 194 of 930 (2025), 349 of 1,776 (2026); no issue or
  trend match changed. Keywords that add a subject ("Property/expropriation" for "Enacts the Louisiana Landowners
  Protection Act") stay, above the digest: putting them after it would need a page change (the summary line always comes
  first). The keyword still gives topics.
