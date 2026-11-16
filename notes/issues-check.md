# National issues: first check (2026-11-15)

The ten issues in notes/issues-draft.md, as search rules in issues.py, run over every bill on the site (47 states, all
sessions each state's pages show: 365,378 bills; local bills for one place and placeholder bills left out). Scripts:
test/issues/get.py (downloads the published data) and test/issues/check.py (writes .issues-cache/report.txt).

How it was checked: for each issue, 30 matches picked at random and read (title and the words that matched), and a
search for bills whose titles use related words but didn't match, read over for real misses. The rules were then fixed
and the check run again (four rounds).

| Issue | Bills (this session) | Right of 30 read | States with none |
|---|---|---|---|
| Data centers | 640 (463) | 29 | NM, NV |
| PFAS | 508 (220) | 30 | AR, ID, ND, NE, SD, UT, WV, WY |
| Artificial intelligence | 1,399 (910) | 30 | none |
| Children online and social media | 491 (228) | 29 | NC, ND |
| Phones in schools | 199 (105) | 29-30 | CO, MA, ME, MT |
| Housing supply and zoning | 672 (322) | 28 | AK, AL, GA, IN, LA, MS, ND, OH, OK, SD, WY |
| Minimum wage | about 640 (230), limited 2026-11-15 | about 27 | AK, WY |
| Right to repair | 222 (85) | 29 | AK, AZ, ID, LA, ND, NE |
| Sports betting and online gambling | 634 (295) | about 27 | AZ, ID, NM, OR, SD, UT |
| Prescription drug costs | 1,113 (420) | about 26 | none |

"This session" is each state's current page; the larger number counts every session the site shows (New York and New
Jersey go back to 2017-18, most states to 2023 or 2024, so the totals aren't comparable between states: issue pages
should count the current session, or the same years in every state).

What the rounds changed:
- Budget and omnibus bills mention a subject once deep in their summaries (Kentucky's "Fiscal matters" names data
  centers once). A match in the title or summary counts; in a long "What it does" text it needs two mentions.
- Wordings first missed: "large energy use facilities" and "new large loads" (data centers; the owner's "large load"
  decision covers them), "phone-free schools", "mobile devices", "personal telecommunications device" (Kentucky's 2025
  law), "electronic telecommunication devices" (Louisiana's 2024), "digital likeness", "synthetic sexual images",
  "right-to-repair" with hyphens, "device repair", "prescription drug cost", "sports gaming", "training wage",
  "housing element", multifamily and density with zoning, firefighters' protective gear with chemicals (PFAS).
- Words with a second meaning: "online gaming" counts only near wagering, casinos or gambling (it also means video
  games); "large loads" not near vehicles or highways; age verification not for alcohol, tobacco, gambling or sodium
  nitrite sales; school "electronic devices" not recycling or audits; "AI" not near "insemination".

The owner's answers (2026-11-15):
- Minimum wage: only bills that set or change a minimum wage. "Minimum wage" now needs a word for a change or a rate
  right next to it ("increases the minimum wage", "minimum wage; establish at $10.00", "local minimum wage"), and bills
  paying for its cost, tax credits and tax breaks, and "living wage" rules for state contractors are left out (about 27
  of 30 after the change).
- Pornography age-verification laws stay under "Children online and social media" (Claude's recommendation when the owner asked; not yet confirmed), with
  a filter on its page, "Age checks for adult websites", beside "Social media", "App stores" and "Design and privacy
  codes".

Still to say on the pages:
- "States with none" are mostly real (no data center bills in Nevada's 2023 and 2025 sessions), but states whose data
  has titles only (AK, AR, MA, ME, MS, MT, ND, NE, NH, OK, VT: no summaries) are undercounted; the issue pages should
  say so.

# National issues: the second ten (2026-11-15)

Abortion, firearms, school vouchers, voting, immigration enforcement, rent and tenants, property tax relief, transgender
people, DEI and cannabis, added to issues.py and checked the same way as the first ten, over the same 365,378 bills: 30
random matches per issue read in each round (title and the matched words), the possible misses (titles with related
words that didn't match) read over, then the rules fixed. Eight rounds, each with a fresh random sample; the table gives
the last round, read on the rules as committed.

| Issue | Bills (this session) | Right of 30 read | States with none |
|---|---|---|---|
| Abortion | 1,513 (518) | 27 | none |
| Firearms | 6,893 (2,180) | 30 | none |
| School vouchers and education savings accounts | 617 (271) | 28 | none (CT, DE, VA and AR this session) |
| Voting and elections | 6,980 (2,286) | 30 | none |
| Immigration enforcement | 1,976 (996) | 28 | none |
| Rent and tenants | 4,663 (1,651) | 27 | none |
| Property tax relief | 3,240 (1,223) | 26-27 | none |
| Transgender people | 1,354 (494) | 28 | none |
| Diversity, equity and inclusion | 481 (174) | 27 | AK, AZ, SD, UT (12 states this session) |
| Cannabis | 3,178 (1,081) | 29 | none |

Arkansas has none of most of these this session because its 2026 session was a fiscal session (appropriations only).
Rounds before the last ran 25-30 per issue; each issue reached 27 or more in at least two rounds except property tax
relief, whose wrong matches are passing mentions that change from sample to sample (a bill that names "the homestead
exemption" as one condition of a home loan program; a county's credit for grocery stores).

Scope decided here (the names are the subject, never a side):
- Voting and elections: how people vote and how elections are run (voter ID, registration, mail and absentee voting,
  early voting, polling places, counting, recounts and audits, election officials, primaries, ranked-choice voting,
  ballot initiatives, voting rights restoration). Not campaign finance: it's about money in politics, not voting (a
  separate issue if wanted). Not district lines, nor local election dates (no rule
  anchors on them; a bill that only moves a town's election date doesn't match). Not votes by shareholders,
  cooperatives or homeowners' associations, nor Mississippi's private bills restoring one person's right to vote
  ("Suffrage; restore to Frankie Ward, Jr": about 60 a year).
- Immigration enforcement: working with federal immigration enforcement (287(g), detainers, ICE access to courthouses
  and schools, sanctuary policies either way), state immigration crimes and human smuggling, checks of status (E-Verify,
  lawful presence), and what status allows (benefits, driver's licenses, professional licenses, in-state tuition, DACA).
  Legal help for people facing deportation counts. Not noncitizen voting (under Voting), refugee resettlement services,
  foreign land ownership, or "regardless of immigration status" in passing.
- Rent and tenants: renting a home, including mobile home lots, rent stabilization, eviction and its records, security
  deposits and fees, habitability, squatters' removal, rental assistance and housing vouchers, source-of-income
  discrimination. Not commercial leases, farm tenancies, short-term rentals, or building rental housing.
- Property tax relief: homestead exemptions, credits, rebates and refunds (renters' too), freezes and deferrals,
  assessment caps, levy limits, exemptions for seniors, veterans and people with disabilities, and repealing property
  tax. Not exemptions for businesses, organizations or development projects, school-aid formulas, or administration.
  Connecticut's and Virginia's car tax relief counts (it's a property tax on households' cars).
- Transgender people: restrictions and protections alike; "gender identity" counts when the bill is about it (adding it
  to a civil rights or hate crime law, conversion therapy, school policies), not when it's one item in a list of
  protected classes or data fields (parole factors, data brokers, demographic forms).
- DEI: offices, officers, training, statements, plans and hiring in government and public universities, bans on them,
  and the fights the same bills take up: implicit bias training, "divisive concepts" and critical race theory,
  affirmative action and preferential treatment. Not supplier diversity (New Jersey's Chief Diversity Officer runs the
  state's contracting programs for minority-, women- and disability-owned businesses).
- School vouchers: vouchers, education savings accounts (New Hampshire's education freedom accounts, West Virginia's
  Hope Scholarship), tax-credit scholarships and the federal tax-credit scholarship opt-in, Wisconsin's parental choice
  programs. "School choice" only with private schooling in the same passage (not public-school transfers or virtual
  charters); not college scholarships.
- Cannabis: legal sales, medical cannabis, hemp-derived THC (delta-8, intoxicating hemp products), CBD, expungement,
  impaired driving and workplace testing. Not industrial hemp farming.
- Abortion: bans and limits, access and shield laws ("legally protected health care", reproductive health care with
  subpoenas, extradition or out-of-state patients), abortion pills, pregnancy resource centers, constitutional
  amendments. Not "termination of pregnancy" in pregnancy-leave laws.

Filters on the issue pages: abortion (bans and limits, access and protections, medication abortion, ballot measures),
firearms (carry permits, background checks and purchase rules, red flag laws, ghost guns and devices, firearms in
schools), voting (voter ID, mail and absentee voting, voter registration, election administration and security), and,
added, transgender people (sports, health care, birth certificates and IDs, bathrooms and locker rooms, schools,
discrimination protections) and cannabis (medical cannabis, hemp-derived THC, expungement). A bill can be in several.

What the rounds changed:
- Lists that name a subject among others: protected classes (hate crimes, parole factors, data brokers: "gender
  identity", "immigration status"), domestic violence's forms of coercive control (threats about immigration status),
  "regardless of immigration status", the criminal code's "other than by the discharge of a firearm", lists of parties
  ("employers, landlords, lenders").
- Second meanings: "ICE" for internal combustion engines; "alien" insurers and nonresident aliens (tax); "Second
  Amendment sanctuary"; "gun clubs", nail and radar guns; hunting seasons, hunter education and the Wildlife Code;
  housing, child care, food and electric school bus "vouchers"; "school choice" among public schools; "crisis centers"
  (behavioral health); "homestead resorts" and creditors' homestead exemptions; commercial, storefront, farm and
  third-party tenants; tenant improvements (construction); rental cars; "voting interests" of companies; "Property Tax
  Relief Fund" paying school aid and New Jersey's Energy Tax Receipts aid; Kentucky's "gender-neutral language" bills;
  "replaces certain pronouns"; "professional women's sports"; "affirmative action by the student".
- Omnibus and budget bills: California's health and human services trailer bills mention abortion coverage, Medi-Cal for
  undocumented people and firearm excise taxes several times, so they pass the two-mention rule; left in (they do contain
  those provisions).
- Wordings first missed: "legally protected health care" and shield laws, "possession of a weapon", "permitless carry",
  "shooting ranges", "gunfire"; "parental choice", "educational tax credits", "scholarship organizations", "Hope
  Scholarship Program", "Utah Fits All", "tuition tax credit"; "advance", "curbside" and "in-person" voting, "voted by
  mail", "recanvass", "cast vote records", "straight-ticket voting", "national popular vote", preregistration,
  incarcerated voters; "citizenship status", aliens' medical assistance; "deductions" for veterans (New Jersey);
  "all-gender restrooms"; implicit bias training, racial equity offices, educator and judicial diversity; hemp products
  and dispensaries.

Questions for the owner:
1. Campaign finance: left out of "Voting and elections". Add it there, or make it its own issue?
2. Redistricting (statewide maps and commissions): left out with single districts' lines. Its own issue?
3. DEI: the issue includes implicit bias training (about 55 bills, many for health professionals and police), critical race
   theory and "divisive concepts" in schools, and affirmative action. Keep all three, or narrow it to DEI offices,
   statements and training by name?
4. Supplier diversity (contracting set-asides for minority-, women- and disability-owned businesses) is left out of
   DEI. Right?
5. Immigration enforcement includes immigrants' access to benefits, licenses and tuition and legal help in deportation
   cases (as the request said), so the name is narrower than the issue. Keep the name, or "Immigration" alone?
6. Transgender people: bills on drag shows and "adult cabaret" aren't included unless they mention transgender people.
   Right?
7. Property tax relief: levy limits and caps on total property taxes are in; school-aid formulas named "property tax
   relief" are out. Right?

## 2026-11-16: Voting, "registered voters" near a petition

The owner found Louisiana's fluoridation bills (SB 2 of 2025, SB 4 of 2026: a water system opts out if 15% of registered
voters petition for a local election) under Voting. "registered voters" near "petition" no longer counts on its own (23
bills fewer: local referendums on fluoride, police districts, town incorporation, a few school-board election bills);
recall elections, initiatives and referenda, and candidates' nominating petitions now count by their own rules (270 more,
read over in a sample: all election process). Voting goes from 6,980 to 7,227 bills across all sessions.
