# Florida

Moved from CLAUDE.md (2026-11-19). Shared conventions, the data traps list and the site's code notes stay there.

- **Florida (built 2026-11-15):** `python3 states/fl/fetch.py` reads flsenate.gov's bill pages (both houses' bills; Crawl-delay
  10; see its docstring) into data/fl/<year>/, after `states/openstates_bulk.py fl` puts Open States' public-domain records
  (data/fl/<year>/openstates/) down as the first copy; `python3 states/fl/contacts.py` (in states.json's run after fetch.py)
  builds the contacts; `states/fl/towns.py` was run once. A page a year (`YEARS = 1`): 60 days from the first Tuesday after
  the first Monday in March (odd years) or the second Tuesday after the first Monday in January (even years); `STATE.dated`
  and `P.SESSION_ENDS` hold each year's last day (2025's ran to June 16 for the budget: add each year's). Special and
  organization sessions are left out; next year's prefiled bills are the upcoming page. HB, SB, and HJR/SJR (constitutional
  amendments: three-fifths of each house's members, then the voters, never the governor: "Signed by Officers and filed with
  Secretary of State", tagged "const", stage 3); bills "Withdrawn prior to introduction" or "Filed in error" are left out.
  `states/fl/convert.py` reads a bill's official page when there is one, else its Open States record: both carry the same
  history lines with their house (Open States drops "-SJ 434" and the space before ",", ";" and ")": `journal_free()`), so
  `from_page()`/`from_openstates()` give one shape; `python3 -m states.fl.convert compare 2026` converts every bill both ways
  (1,755 of 1,755 gave the same stage, houses and committee). The Senate refers a bill to all its committees in one line
  ("Referred to Criminal Justice; Judiciary; Rules"), the House one line each; "Now in X" says where it is. Reports: the
  Senate's "CS by X; YEAS 9 NAYS 0", "Favorable by- X; ...", "Unfavorable by", "Submitted as Committee Bill and Reported
  Favorably by", "Recommendation: Favorable by" (appropriations subcommittees); the House's "Favorable [with CS] by X" (no
  tallies). A committee substitute keeps the number ("CS/CS/HB 1195"). "CS passed as amended; YEAS 76, NAYS 31" is the
  passage ("failed to pass" ends it: `endedNote()`); "Reconsidered" undoes it only when the house's last step was the vote
  (HB 6017 of 2025 reconsidered a postponement). Most bills have a companion in the other house: the one that passes is
  "Substituted for CS/SB 1346" and the other "Laid on Table, companion bill(s) passed": kept as separate records, the
  tabled one shown as "Replaced by HB 1195" (this puts many companions at "died on the floor" in the statistics). "Ordered
  enrolled" / "Ordered engrossed, then enrolled" is passed both houses; "Signed by Officers and presented to Governor"
  (weeks or months after the session), "Approved by Governor", "Allowed to become Law without Governor's Signature",
  "Vetoed by Governor", "Governor vetoed specific Line Item(s)" (a law), "Chapter No. 2025-19" (`chapter` is the string
  "2025-19"). Vetoes go to the next regular session ("Veto Message received (2026 Regular Session)", then "Veto Message
  transmitted to Secretary of State": the veto stands); the 2025 House's overrides of 2024 budget items (and two by the Senate,
  January 2025) changed no bill's outcome. Laws and vetoes match the last actions on the Senate's bill lists bill for bill
  (`python3 -m states.fl.convert`): 2024 299 laws (line items HB 5001), 14 vetoes, amendments HJR 7017 and SJR 1114; 2025
  251 laws (line items HB 7031, SB 2500), 11 vetoes (the press counted nine by July 2 "with a few remaining"), HJR 1215 and
  HJR 5019; 2026 228 laws, 8 vetoes (the 2026 budget passed in a special session, left out). No override made a law.
  Votes: floor passages member by member from the vote PDFs (votes/, "Y Abbott-5": the district is the seat), else Open
  States' roll call (surnames, "Alvarez, D."; mangled UTF-8 "LÃ³pez" put back by `unmangle()`) matched by house, day and
  tally (exactly, or within 2 with no more noes than the tally: a local-bills calendar's one roll call and amendments'
  votes share the day), else the tally. Committee votes: the Senate's vote records (votes/, an X under Yea or Nay; names
  "Smith, VICE CHAIR"), else Open States' (Senate committees, House committees from 2026), else the Senate line's tally.
  Names are tied to the term's member list (data/fl/members/<term>.json; 2024 is the 2024-2026 term) by surname and
  initial, with suffixes ("Brannan III", "Mooney Jr.") and changed names ("Hart" for Hart-Lowman, "Busatta Cabrera") handled;
  every name in 2024-26 resolves. "What it does" is the newest staff analysis's summary (analyses/: the House's "Effect of
  the Bill:", older "SUMMARY ANALYSIS", the Senate's "I. Summary:"), labelled with the committee and date; without one there
  is none: the one-line description from the Senate's site (the page's, or Open States' copy) is the summary line, and
  repeating it showed it twice. Titles are the short titles. Committee names: "& " -> "and", " Committee"/"Subcommittee"
  dropped (no House subcommittee shares a full committee's name), "Appropriations Committee on X" -> "X Appropriations",
  "Select Committee on X" -> "X Select", "Claim Bills Special Master". Sponsors: committees come first on a committee
  substitute ("State Affairs Committee; Persons-Mulicka"): the sponsor is the first member, or the committee for a
  committee's own bill. Local bills (page type "LOCAL BILL"; without a page, House bills 4001-4999 or titles ending in a
  county or city) are narrow "place"; claim bills ("Relief of ...", "CLAIM") "person". Earlier years linked by the same short
  title and first sponsor, or the same description word for word, one bill each, never laws or budget bills. Contacts:
  each term's member lists (party, district, counties; the Senate's posts), offices and phones from members' pages once
  fetch.py reads them (none locally on 2026-11-15), committees from data/fl/committees/ for the current term (not
  downloaded yet). No emails exist: `form` is the senator's page (its email form) or the House's contactmember.aspx; a past
  session's member who still holds the seat gets today's form. The House list's counties field sometimes carries a stray
  'Part of Orange">' (fetch.py's `parse_reps()`; cleaned in contacts.py). Leaders by term (`P.OFFICERS`): Passidomo/Renner,
  Albritton/Perez, Boyd/Garrison (designates; the organization session, November 17, 2026, elects them: check). The
  2026-2028 member list (read 2026-11-14) gives the Senate R25-D13-NPA1 with one vacancy and the House R70-D50 (the 2024-2026
  lists, counting replacements: R30-D13-NPA1, R91-D36): check against the election results. Governor Ron DeSantis, term-limited: the governor elected in
  November 2026 takes office January 5, 2027 (add to `GOVERNORS` and legislatures.json). 7 days in session, 15 after
  adjournment or presentment (`govDeadline()`), else law without signature; item vetoes on appropriations; override
  two-thirds of each house. The governor's contact page (flgov.com/eog/contact) and address were read by program
  2026-11-15 (the page has no phone; (850) 717-9337 is from general knowledge, unchecked; flgov.com's robots.txt bars AI
  crawlers by name). Places (`towns.py`): cities, towns, villages, Census-designated places and counties, separate Senate
  (40) and House (120) lists.
- **Contacts of 2026 (checked 2026-11-22):** about a third of the 2026 session's members have no contact form or phone:
  Florida's terms end at the November election, and members who left then are no longer on the Senate's or the House's
  pages (the 2027 session's contacts have every member's form). data_check.py's contacts check leaves Florida's phones
  out (`CONTACT_GAPS`: they come from members' pages, read over several runs).
- **Photos (2026-11-22):** the House's own by MemberId (the contacts' "id"), www.flhouse.gov/FileStores/Web/Imaging/
  Member/<id>.jpg, as its roster page shows them; the Senate's from its list of senators (/Senators/, one request a week:
  /PublishedContent/Senators/2026-2028/Photos/S27_5342.jpg, the thumbnail's name without "_Thumbnail"). So the 2027
  members have photos before Open States lists them. flsenate.gov's Crawl-delay (10) is kept.
