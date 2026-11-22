# Minnesota

Moved from CLAUDE.md (2026-11-19). Shared conventions, the data traps list and the site's code notes stay there.

- **Minnesota (built 2026-11-09):** `python3 states/mn/fetch.py` reads
  the Revisor of Statutes' bill status API and the House's, Senate's and Legislative Reference Library's pages (see its
  docstring) into data/mn/<first year>/; `python3 states/mn/contacts.py` (add it to states.json's run after fetch.py) builds
  the contacts; `states/mn/towns.py` was run once. A page per two-year Legislature (`YEARS = 2`; the 94th is 2025-26):
  sessions from January (odd years; the second Tuesday since 2025) or February (even years, set by resolution: `STATE.dated`
  holds each year's opening day, add each year's) to the Monday after the third Saturday in May (`adjourns()`). Special
  sessions are included on their Legislature's page (decided 2026-11-09, so the 2025 budget doesn't look as if it never
  passed): the 2025 First Special Session (data/mn/2025-s1, June 9, 2025) passed most of the budget, 15 laws (its chapters
  1-15, none missing), from bills numbered HF 1 and SF 1 again. They're numbered "HFS2"/"SFS17" (`special_num()`: the house's
  letter stays first, a letter S, T ... for the first, second ... special session; the page shows "HF 2 (1st Special
  Session)": `STATE.numText()`, `specialOf()`), titled "... (2025 1st Special Session)", with no `chapter` (their laws are
  "Laws 2025, First Special Session chapter 3", in the history and the law link), House votes from the special session's
  folder and Senate votes from the regular journals. Regular-session omnibus bills whose content passed there instead get
  a history line ("Passed instead in the 2025 First Special Session as HF 2 (1st Special Session chapter 3)",
  `link_specials()`): matched by identical description, plus `SPECIAL_LINKS` for the same budget area worded differently;
  13 bills, 4 of them numbers reused for different 2026 laws (HF 2433, HF 2438/SF 2082, SF 2077, HF 2484), which stay laws.
  The notice and How's "About this data" say so (`STATE.specials`). Resolutions are left
  out (HF 197 of 2023, the ERA memorial, has a "Resolution 1" law number). `states/mn/convert.py`: House Files and their
  Senate companions (COMPANION_TYPE/NUMBER, mutual pairs only) are one record, lead = the number that got further, each
  keeping its own history. Each number's record has one list per house; each list copies the other house's messages
  ("Senate accedes", "House conferees", "Senate adopted conference committee report, bill repassed"), which are dropped,
  except "Returned from Senate (with amendment)". The governor's lines come from the bill's own house's list (the other's
  dates can differ by a day; a mistyped year, "05/27/226" on HF 4591 of 2025-26, takes the other list's date). A House
  motion's outcome is the next line ("Motion to re-refer" X, "Motion did not prevail" is not a referral). The Senate writes
  one passage several ways on a day ("Senate adopted CC report and repassed bill" 39-26 and "Third reading" 40-25: one
  vote, the "Third reading" tally); "Senate concurred" alone is agreement, not the repassage (SF 4225 of 2023-24 never got
  its repassage: the constitutional deadline). Passed both houses: the first house's "Returned from" line without
  amendments, its repassage after agreeing to the second house's amendments, the same conference report repassed by both,
  or the governor; a second house that amended the bill (in committee, by Rule 45 to match its own text, or on the floor)
  and then passed it "plainly" still needs the first house (HF 1587 of 2023, SF 1943 of 2025). Laws are chapters numbered
  through the Legislature (2024 continues 2023), from the governor's approval; vetoed bills and constitutional amendments
  get chapter numbers too. Totals (`python3 -m states.mn.convert`): 2023 73 laws + 1 veto (HF 2369, chapter 65, Walz's only
  veto of 2023-26 on the LRL list) + 1 amendment (HF 1900, chapter 67) = chapters 1-75; 2024 52 laws, chapters 76-127;
  2025 39 laws, 1-39; 2026 91 laws + 1 amendment (HF 3900, chapter 114) = 40-131: none missing, no line-item vetoes.
  Constitutional amendments are bills ("constitutional amendment proposed"), tagged "const": a majority of each house's
  members, then the next general election (`amendmentOnce`, `ballotEvenYears`). Votes: House floor votes member by member
  from house_votes/ (passages matched 264 of 268 in 2023-24, 271 of 272 in 2025-26), the Senate's from the journal text
  (`senate_rolls()`: roll calls after "The question was taken on the (re)passage of the bill"; 190 of 190 and 202 of 202, every
  name list adding up to its tally); House names ("Anderson, P. E.") are tied to members through the authors lists'
  LEGISLATOR_KEY, Senate names by last name; members voting that day but not on the bill show as not voting. Only current
  members are listed (2023-24: 81% of House and 92% of Senate names tied to a seat; 2025-26 99%). No committee votes.
  "What it does": the newest House Research or Senate Counsel, Research and Fiscal Analysis summary of either number (PDF text:
  page furniture dropped, lines rejoined, lost "ti"/"fi" ligatures (U+FFFD) put back from the summaries' own words; House
  Research's section tables cut to each section's heading and first sentence; 4,000 characters at most), about a third of
  records; otherwise the Revisor's one-line description, the summary line, is all there is. Titles: the description's first
  clause when long. Seats: "S:12"; House districts 12A/12B are numbered 1-134 ("H:23" = 12A, `profile.house_seat()`) and
  data/mn/district_names.json gives the page their names (tracker.html's `DNAME()` treats "12A" as a number: "District 12A").
  The public site looks up an address (the Census geocoder answers "12A", matched to these names by tracker.html's `censusDistrict()`); `findReps` links the LCC's district finder on the Claude copies. Places: about 850 cities and
  the 87 counties, separate Senate and House lists. Balance: the House is tied 67-67 with a power-sharing agreement (Speaker Lisa
  Demuth, R; each committee a Republican and a DFL co-chair: the first listed is the chair on contact cards), so
  legislatures.json marks it `coalition` with a `note`; Senate DFL 34-33. DFL is counted as Democratic. Leaders: Speaker
  Demuth, Senate Majority Leader Erin Murphy (the 95th Legislature chooses its own in January 2027). Governor Tim Walz (D),
  3 days (Sundays excepted) in session, 14 days after adjournment for bills passed in the last 3 days, then a pocket veto;
  item vetoes on appropriations; override two-thirds. The governor's phone ((651) 201-3400) and address are from general
  knowledge: mn.gov's contact page doesn't answer automated readers; not checked by the owner. If a new governor takes office
  January 4, 2027, add them to `GOVERNORS` and legislatures.json.

- **Committee agendas (2026-11-22):** `agendas()` in states/mn/fetch.py (the current Legislature, every run, two requests)
  reads the House's schedule page, www.house.mn.gov/Schedules/All (HTML, every posted meeting of House committees and
  the joint commissions; each card's "Bills Added" links name the bills, `ssn=` the special session; else the HF/SF
  numbers in the agenda text; "Hearing Canceled" cards and floor sessions left out), and the Senate's schedule API,
  www.mnsenate.gov/api/schedule/range/<yesterday>/<3 weeks ahead> (the JSON behind its Vue schedule page: each agenda
  item's bill_type "S.F."/"H.F." and bill_number "0042"; "Meeting canceled" revisions and floor sessions, cmte_id 1, left
  out), into data/mn/<first year>/agendas.json, `{"HF743": [["House Commerce Finance and Policy", "2026-03-10T08:15:00"]]}`
  (House and Senate committees prefixed; commissions keep their own names); `agendas()` in convert.py keeps today's and
  later. A house whose schedule fails keeps its entries from the last file. Agendas are posted a few days ahead (the
  Senate's `public_notice_date` about four days before). robots.txt: house.mn.gov bars only /Fiscal2/, mnsenate.gov has
  none. Tested 2026-11-22 against March 10, 2026's House day page (same cards; 17 meetings, 54 bills) and the Senate's
  API for February 17 to March 10, 2026 (97 meetings, 179 bills): all 233 numbers match records. The live pages had only
  interim commissions (14 meetings, no bills). Untested live: the House's /Schedules/All with a session's worth of
  meetings (size), and special-session numbering.
- **The next Legislature (2026-11-22):** Minnesota has no prefiled bills; the Revisor lists session 0952027 already, with no bills (2026-11-22). fetch.py asks for its first bills each run (`has_bills()`, two searches) and makes its folder only then; a new Legislature with no bills on file, or in its first January, never holds Minnesota off the site (`holds()`), and members are read daily that January (`MEMBERS_DAYS`) so the new members replace the old within a day of the swearing-in (January 12, 2027).
