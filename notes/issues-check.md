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

Abortion, firearms, school vouchers, voting, immigration (named "Immigration enforcement" until 2026-11-17), rent and tenants, property tax relief, transgender
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
| Immigration | 1,976 (996) | 28 | none |
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
- Immigration: working with federal immigration enforcement (287(g), detainers, ICE access to courthouses
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

## The owner's answers on the second ten (2026-11-17)

1. Campaign finance becomes its own issue (below), not part of "Voting and elections".
2. Statewide redistricting becomes its own issue (below).
3. DEI stays as written: implicit bias training, "divisive concepts", critical race theory and affirmative action stay in.
4. Supplier diversity stays out of DEI.
5. "Immigration enforcement" is renamed "Immigration" (the id stays "immigration", so links keep working).
6. Drag-show and "adult cabaret" bills count under Transgender people only when they mention transgender people (as now).
7. School-aid funds named "property tax relief" stay out of Property tax relief (as now).

# National issues: the third ten (2026-11-17)

Data privacy, campaign finance, redistricting, paid family and sick leave, child care, IVF and fertility, fluoride in
drinking water, nuclear energy, wildfire and noncompete agreements, added to issues.py and checked as the second ten were,
over the same 365,378 bills (the copy of 2026-11-15): 30 random matches per issue read in each round (title and the matched
window), the possible misses (titles with related words that didn't match) read over, then the rules fixed. Four rounds;
the table gives the last round, read on the rules as committed. The first twenty issues' rules are unchanged (compared
with the commit before: only the immigration issue's name differs).

| Issue | Bills (this session) | Right of 30 read | States with none |
|---|---|---|---|
| Data privacy | 633 (291) | 28 | ND, SD |
| Campaign finance | 1,672 (585) | 28 | none |
| Redistricting | 345 (118) | 29 | ID, KS, ND, SD |
| Paid family and sick leave | 820 (280) | 28 | SD |
| Child care | 3,068 (1,163) | 29 | none |
| IVF and fertility | 467 (180) | 28 | AK, KS, WY |
| Fluoride in drinking water | 74 (41) | 30 | AL, CA, CO, DE, ID, MD, MI, NC, NM, NV, OR, RI, WI, WY |
| Nuclear energy | 506 (211) | 28 | AK, AL, DE, ID, NC, NV, SD |
| Wildfire | 630 (247) | 27-28 | DE, KY, MA, MD, MI, MO, MS, NC, NH, OH, TN, VA, VT |
| Noncompete agreements | 211 (80) | 30 | AK, AL, DE, MT, NC, ND, WV |

Earlier rounds: privacy 26, then 27; campaign finance 23-26, then 28; redistricting 25, 22-24 (a sample heavy with local
and passing mentions), then 29; paid leave 19 (sick leave banks for one employee, payouts of unused leave), then 26-28;
child care 26, then 29; IVF 29; fluoride 30; nuclear 24-27, then 28; wildfire 28; noncompete 24 ("noncompetitive" bids and
positions), then 30. Fluoride's states with none are real: the subject came up in 2025, mostly in states that moved to ban
it.

Scope decided here (the names are the subject, never a side):
- Data privacy: what businesses may collect, keep and sell: comprehensive consumer privacy acts, data brokers, biometric
  privacy (Illinois's BIPA bills), consumer health data, location data, privacy policies. Not government records and open
  records, what agencies and police may collect (license plate readers, facial recognition for arrests), protecting judges'
  and officers' home addresses from publication (unless the bill regulates data brokers), "invasion of privacy" crimes,
  data breach notification alone, or children's design codes and kids' online acts (Children online). California's
  digests name the Consumer Privacy Act as background on bills about other things; those windows are left out, which
  also drops a few real California privacy bills whose titles don't say so.
- Campaign finance: contributions, spending, disclosure, PACs, dark money, independent expenditures, public financing and
  clean elections, personal use of campaign funds, pay-to-play. Not lobbying or ethics alone, and not AI or deepfakes in
  political ads (under AI) even when the bill names the committees that pay for them.
- Redistricting: drawing legislative and congressional districts, commissions, standards, counting prisoners at home,
  mid-decade maps. Statewide rules for local districts count (a law on when counties redraw after a census); one county's,
  city's, school board's or university board's districts don't, nor judicial districts, presidential electors, or
  "until the next redistricting" in passing.
- Paid family and sick leave: paid family and medical leave programs and insurance, paid sick and safe time, parental and
  maternity leave (public employees' too), and unpaid family leave laws (FMLA-style). Not sick leave banks for one
  employee (Massachusetts files dozens), donating or buying back leave, payouts of unused leave or retirement credit for
  it, paid administrative leave.
- Child care: subsidies and eligibility, licensing and background checks, the workforce, tax credits (including child and
  dependent care credits), employer child care, facilities. Not foster or residential child care ("child care
  institutions", child-placing agencies, host homes), pre-K and K-12, and not lists of places something may not be near
  (sex offenders, tobacco, firearms).
- IVF and fertility: IVF, infertility coverage, fertility preservation, embryos as they bear on IVF (Alabama's 2024
  immunity law), surrogacy and parentage of children born by assisted reproduction, donors, fertility fraud. Abortion-only
  bills stay under Abortion; lab-grown meat ("in vitro animal cell cultures") is left out.
- Fluoride in drinking water: fluoridation bans, local choice and elections, levels, warnings, studies of its effects. Not
  fluoride varnish for children's teeth.
- Nuclear energy: reactors and small modular reactors, moratorium repeals, fusion energy, plants' taxes, workers,
  decommissioning and emergency planning, nuclear in clean energy standards. Not weapons, nuclear medicine, "fusion
  voting" or "fusion centers", radioactive waste alone, or lists that leave nuclear out ("other than fossil fuel or
  nuclear") or name plants among crime targets.
- Wildfire: prevention, prescribed burns, defensible space, fire hazard zones, utilities' wildfire plans, shutoffs and
  liability, insurance, tax relief and rebuilding after fires, wildland firefighters. Not ordinary fire codes, forest
  rangers' retirement, or California's 2024 bond act named "Safe Drinking Water, Wildfire Prevention ...".
- Noncompete agreements: noncompetes, "covenants not to compete", non-solicitation and no-poach clauses, restrictive
  employment covenants, for all workers or for doctors, nurses and others. Not "noncompetitive" bids, grants or positions.

What the rounds changed:
- Words with a second meaning: "personal privacy" (voyeurism crimes), "data privacy" as a line in bills about government
  programs; "awareness campaign fund"; "reapportions the nominations" (a commission's members); "paid medical expenses";
  "noncompetitive"; "in vitro" cell cultures; "nuclear-powered submarines" in a firearms bill; "wildland areas" (a park).
- Wordings first missed: "Consumer Data Protection Act" (Virginia's), privacy policies, "composition of districts"
  (Texas's map bills), pay-to-play, donations to inaugural committees, "early childhood care", "extrauterine" embryos,
  "fertility-related services", "the law governing fluoride" (Ohio), fusion technology and fusion in clean energy
  standards, "nuclear-fueled", "nuclear workforce".

Questions for the owner:
1. Data privacy leaves out government surveillance (police buying data, facial recognition, license plate readers) and
   data breach notification laws. Add either, or make government surveillance its own issue?
2. Paid leave includes unpaid family and medical leave laws (state FMLA bills) and parental leave for public employees.
   Keep both?
3. Redistricting includes statewide laws on how counties and cities redraw their own districts. Keep, or legislative and
   congressional maps only?
4. Nuclear energy includes nuclear plants' security, emergency planning and decommissioning. Keep?
**Answered 2026-11-17 (owner, agreeing with the drafts):** 1, no: data privacy stays without surveillance and breach laws;
2, keep both; 3, keep; 4, keep. No rule changes.

# National issues: the fourth ten (2026-11-17)

Short-term rentals, water rights and supply, psychedelics, crypto ATMs, Medicaid work requirements, daylight saving time,
book removals in schools and libraries, medical debt, police accountability and the death penalty, approved by the owner
the same day, added and checked the same way over the same bills: three to five rounds, a fresh random sample each. The
first thirty issues' rules are unchanged by this batch. Daylight saving time has no group (`"group": ""`): the issues index
(issues_site.py) and the front page's menu (home.html) both put issues outside issues.GROUPS under "Other", so it shows
there.

| Issue | Bills (this session) | Right of 30 read | States with none |
|---|---|---|---|
| Short-term rentals | 277 (97) | 28 | ND, NM, NV, SD, WY |
| Water rights and supply | 953 (394) | 27-28 | AK, KY, NC, OH, VT |
| Psychedelics | 182 (89) | 29 | AL, AR, DE, ID, NC, ND, OH, SC, TN, WY |
| Crypto ATMs | 87 (72) | 29 | AR, CA, GA, MT, ND, NE, NM, NV, OR, VT |
| Medicaid work requirements | 48 (30) | 28 | 27 states (AK, AL, AR, AZ, DE, GA, IL, KY, LA, MA, ME, MI, NC, ND, NM, NV, OH, OK, OR, RI, SC, TN, TX, VA, VT, WA, WI) |
| Daylight saving time | 194 (72) | 30 | AL, AZ, CO, DE, LA, MT, OH, SD, WY |
| Book removals in schools and libraries | 137 (50) | 28 | AZ, DE, IN, KS, KY, MA, ME, NC, NH, OR, WA |
| Medical debt | 231 (106) | 28 | AL, AR, AZ, MS, ND, NH, UT, WV |
| Police accountability | 873 (283) | 28-29 | MT, SD |
| Death penalty | 332 (120) | 28 | AK, ME, ND, RI, VT, WY |

Earlier rounds: water 26, then 24-26 (passing mentions of groundwater and water supply), then 27-28; medical debt 13 at
first ("financial assistance" and liens in unrelated bills), then 28; books 27, then 28; police 26, then 28; death penalty
26, then 28; short-term rentals 28; the others 28-30 from the start. Medicaid work requirements are few because the
federal requirement (2025) left little for states to pass, and some states (Georgia's Pathways, Arkansas) set theirs by
waiver; Crypto ATMs are mostly 2025-26 bills, so the session totals are nearly all this session.

Scope decided here:
- Short-term rentals: local regulation and its limits, registration, hosting platforms, occupancy and sales taxes on
  short-term rentals, safety rules, property tax classification. Not hotel taxes generally (a bill on lodging taxes counts
  when it names short-term rentals), car rentals, or a child's short-term placement.
- Water rights and supply: water rights and their transfer or abandonment, groundwater management and conservation
  districts, aquifers, drought plans, water conservation, water banks and markets, interstate compacts, the Colorado River,
  long-term supply planning. Not water quality (contamination, discharge permits, monitoring wells, stormwater), soil and
  water conservation districts, appliance efficiency standards, utility rates and shutoffs, foreign land ownership lists,
  "prior appropriation" of money, or California's bond act named for drought among other things.
- Psychedelics: psilocybin (therapy programs, Oregon's and Colorado's "natural medicine" services, decriminalization,
  rescheduling when the FDA approves it), MDMA, ibogaine research. Not lists of controlled substances in sentencing laws.
- Crypto ATMs: virtual currency, cryptocurrency and digital asset kiosks; broader crypto laws only where they cover kiosks.
- Medicaid work requirements: work or community engagement requirements for Medicaid (and its state names), waivers to
  seek them, studies of their effects, constitutional amendments allowing them. Not SNAP or TANF work rules alone.
  2026-11-25: a rule for the requirement in other words ("to engage in community service, work, or other activities in
  order to qualify for Medicaid": H.R. 1 of the 119th, Sec. 71119, which the section rule missed). Over the published
  bills (458,764, test/issues/check.py's cache) it adds no other bill; among Congress's sections it finds H.R. 1's Sec.
  71119 and the 2023 Limit, Save, Grow Act's Sec. 321 (already found), both right.
- Daylight saving time: permanent standard or daylight time, leaving or joining the clock change, time zones, studies.
- Book removals: challenges to and removal of books and materials in school and public libraries, "harmful to minors"
  and obscenity rules for libraries (including removing schools' and libraries' exemption from obscenity laws), "freedom
  to read" laws, review of instructional materials for sexual content, librarians' liability. Not library funding, and not
  ordinary curriculum or instructional materials adoption.
- Medical debt: credit reporting of medical debt, collection limits (liens on homes, garnishment, lawsuits), interest
  caps, debt relief programs, hospital financial assistance and charity care tied to bills and collection, price
  transparency laws that bar collection. Not hospitals' liens on injury settlements or charity care as a reporting line.
- Police accountability: use of force (including chokeholds and deadly force), body and dashboard cameras and their
  footage, no-knock warrants, qualified immunity, decertification, misconduct records and databases, civilian oversight,
  independent investigation of police killings, duty to intervene. Body-camera grants count (not funding alone in general,
  but the cameras are the subject); correctional officers' cameras and standards count too. Not security guards or
  general strangulation crimes.
- Death penalty: abolition and reinstatement, methods (nitrogen hypoxia, firing squad), execution procedures and secrecy,
  which crimes are capital, intellectual disability and mental illness exemptions, capital defense. "Capital murder" alone
  (a life-sentence crime in Texas and Mississippi) needs death in the same passage, unless the bill creates a capital
  crime. Not "execution" of documents or duties, physician-assisted death, or Louisiana's phrase for any felony ("may be
  sentenced to death or imprisonment at hard labor").

Questions for the owner:
1. Police accountability includes correctional officers (body cameras in prisons, a corrections standards commission).
   Keep, or police only?
2. Water rights and supply includes water conservation (turf and landscaping limits, homeowners' associations and
   lawns). Keep?
3. Medical debt includes hospital price transparency laws when they bar collecting from patients of noncompliant
   hospitals. Keep?
**Answered 2026-11-17 (owner, agreeing with the drafts):** keep all three. No rule changes.

# National issues: the fifth ten (2026-11-17)

Vaccines and public health powers, unions and collective bargaining, ballot initiatives, ranked-choice voting, energy
costs and utility rates, climate and clean energy, ESG investing and boycott laws, religion in public schools, child labor,
and protest and assembly laws, approved by the owner the same day, plus kratom, added on the owner's approval during the
work. All were added and checked the same way, over every bill the published site shows (454,901 bills in 50 states and
Congress, read with test/issues/get.py; local and placeholder bills left out). There were five or six rounds, each with a
fresh random sample of 30 per issue (title and the words that matched) and a search for likely misses (titles with related
words that didn't match). The first forty issues' rules are unchanged. Every issue now also has `words`, a few extra terms
for the front page's search, which don't change what matches. Groups: Health (vaccines, kratom), Work and the economy
(unions, child labor, ESG), Elections (initiatives, ranked-choice voting), Environment and energy (utility rates, climate),
Schools (religion), Rights and public safety (protest).

| Issue | Bills (this session) | Right of 30 read | States with none |
|---|---|---|---|
| Vaccines and public health powers | 2,623 (643) | 27-28 | none |
| Unions and collective bargaining | 2,065 (788) | 26-27 | ND |
| Ballot initiatives | 451 (136) | 27 | AK, DE, MN, NC, NH, NM, PA, VA, VT |
| Ranked-choice voting | 290 (87) | 30 | AZ, DE, NC, NE, NV, TN |
| Energy costs and utility rates | 1,683 (820) | 27 | ND, SD |
| Climate and clean energy | 3,207 (1,027) | 27 | none |
| ESG investing and boycott laws | 324 (83) | 29 | AK, DE, NM, RI |
| Religion in public schools | 321 (135) | 28 | AK, CO, DE, MA, NM, VT, WA |
| Child labor | 376 (128) | 27 | DE, MT, NC, SC, SD, VT |
| Protest and assembly laws | 339 (155) | 26-27 | AK, AR, CO, MA, ME, MT, NE, RI, SD, UT, WY |
| Kratom | 278 (145) | 30 | AK, AL, ME, NM |

Counts include Congress. Earlier rounds: vaccines 22, then 25-26, then 28 (bills that mention "the COVID-19 public health
emergency" in passing: telehealth, tax credits, price gouging); unions 22-25, then 26-27 ("collective bargaining
agreement" in passing, labor organizations named on task forces and boards, "meet and confer" in court rules, Nebraska's
"AM 503 strikes ..."); initiatives 19, then 22, then 27 (Arkansas's "initiated Act 1 of 2000" and California's "an
initiative measure approved by the voters" as background, local tax referendums, Oregon's "referred to the people ... by
referendum petition" clause); utility rates 26, then 27 (water bills, "energy cost savings" contracts, the "Coastal Resources
and Energy Assistance Act", wildfire power shutoffs); climate 26-27 ("net-zero endowment", California's digests opening
with its greenhouse gas law); religion 25, then 28 (state-house Ten Commandments monuments, vaccine exemptions, religious
holidays in arts-council grants); child labor 19, then 27 (child care, youth job programs, "minor construction",
"Whole Child Model"); protest 21, then 25-27 (Pennsylvania's crimes-code heading "riot, disorderly conduct and related
offenses", lists of emergencies "disaster, war, riot", bid and tax protests, "demonstration programs", race-riot monuments,
officers' masks, the "Legislative Assembly" read as assembly); ESG, ranked-choice voting and kratom 29-30 from the start.
Ranked-choice voting's 290 bills are nearly all under Voting and elections too (284); about two thirds of initiative bills
are (the other third name initiatives, referendums or petitions without words Voting's rules use; Voting's rules weren't
changed). New York's S8925A of 2025-26 ("Prohibits the sale of 7-hydroxymitragynine products") matches Kratom.

Scope decided here:
- Vaccines and public health powers: requirements and exemptions (school, employer, religious, medical), mRNA bans and
  labels, vaccine status discrimination, access (pharmacists, dentists, insurance coverage), immunization registries
  (counted as vaccine records; trivial registry bills are few), and limits on governors' and health officers' emergency
  powers (declarations, quarantine, closures, mask orders). Not animals' vaccines (rabies, livestock, hens) or plant
  quarantines, and not bills that only run "during the public health emergency".
- Unions and collective bargaining: bargaining rights for public and private workers (including rideshare drivers and
  graduate assistants), dues and payroll deduction, right-to-work, exclusive representation, arbitration and impasse,
  strikes and strikers' benefits, captive-audience meetings, union contracts' ratification and funding. Not a passing
  "subject to (or covered by) the collective bargaining agreement", labor organizations named among a board's members,
  plea bargains, credit unions.
- Ballot initiatives: citizens' initiatives and referendums, statewide and local processes (a county initiative act),
  signatures and circulators, thresholds for initiated amendments, ballot titles and summaries, single subject, fiscal
  statements. Not laws that were themselves enacted by initiative, local tax referendums, or recall and nominating
  petitions.
- Ranked-choice voting: adopting, allowing, studying or banning ranked-choice (instant-runoff, "preferential") voting,
  and approval voting. Not runoff elections.
- Energy costs and utility rates: electric and gas rates and rate cases, fixed charges, fuel and purchased-power cost
  recovery, shutoffs and disconnections, energy assistance (LIHEAP, arrearage programs), public benefits charges, retail
  energy suppliers, net metering, who pays for large loads (data centers; also under Data centers). Not water and sewer
  rates, phone and broadband, or energy-savings contracts.
- Climate and clean energy: greenhouse gas limits and targets, renewable and clean energy standards, cap-and-trade and
  carbon pricing (RGGI), clean fuel and clean heat standards, zero-emission vehicle rules, building electrification and
  bans on gas hookups (and bans on those bans), climate superfunds, climate risk disclosure, climate education and
  resilience, carbon capture and storage. Nuclear power counts when framed as clean energy (zero-emission credits).
- ESG investing and boycott laws: ESG factors in state pensions, contracts and banking, proxy voting, "fair access" and
  debanking laws, social credit scores, laws on contractors that boycott energy, firearms or Israel, and divestment from
  fossil fuels, firearms or Israel (both directions). Not divestment from countries (Russia, China, Iran).
- Religion in public schools: Ten Commandments displays, "In God We Trust", chaplains, prayer and moments of silence, Bible
  courses, released time, religious expression and dress, religious holidays and parents' notice of religious content. Not
  vaccine exemptions, private or religious schools, or Ten Commandments monuments outside schools.
- Child labor: work permits and certificates, hours, hazardous jobs, penalties and enforcement, minors in particular jobs
  (referees, theater, athletes), child performers' and child influencers' earnings and trust accounts, and laws against
  buying goods made with child labor. Not youth job programs, child care, or a "minor child" of an employee.
- Protest and assembly laws: riot and unlawful assembly crimes and penalties, rioting organizers, blocking roads, critical
  infrastructure trespass and damage, picketing homes of judges and others, clinic buffer zones and access, masked
  intimidation and loitering while masked, campus protest rules, liability for protest damage. Not prison riots, tax or bid
  protests, police officers' masks, drone and cyber attacks on infrastructure, or protests abroad.
- Kratom: kratom, mitragynine and 7-hydroxymitragynine ("7-OH"): consumer protection acts, age limits, labeling, sales bans
  and scheduling. Not tianeptine ("gas station heroin") unless kratom is in the bill.

Questions for the owner (each with a suggested answer):
1. Unions includes the bills that fund or ratify public employees' union contracts (Hawaii files one per bargaining unit
   each year: 174 of Hawaii's bills; Wisconsin and California ratify agreements). Keep? Suggested: keep; they are the
   contracts.
2. Child labor includes child influencers' earnings (as asked) and bills barring the state from buying goods made with
   child labor abroad (electric vehicle batteries, cobalt, solar). Keep both? Suggested: keep influencers; keep
   supply-chain bills too.
3. Climate includes carbon capture and storage (CO2 storage rules, pipelines' eminent domain) and climate education.
   Keep? Suggested: keep.
4. Utility rates includes net metering (what solar owners are paid). Keep? Suggested: keep (it's how they're billed).
5. ESG includes Israel divestment bills of both kinds (barring boycotts of Israel, and divesting from Israel). Keep both?
   Suggested: keep; the issue is the subject, not a side.
6. Protest includes anti-mask crimes generally (masked harassment and intimidation), since most were written with
   protests in mind; it leaves out bills on police and immigration agents' masks. Keep? Suggested: keep.
7. Ballot initiatives includes local initiative and referendum processes (county and city), not just statewide. Keep?
   Suggested: keep.

## Mentions inside anti-ESG and boycott lists (2026-11-17)

Alabama SB 261 of 2023 bars contracts with companies that boycott businesses in "the fossil fuel or firearm industry ...
or [that don't] facilitate access to abortion or sex or gender change surgery", and it counted for Abortion and
Firearms. issues.py now skips a match whose window also has "boycott", "environmental, social(,) and governance", "ESG",
"economic boycott criteria", "corporate governance standards" or "discriminates against firearm entities"
(`NOT_BOYCOTT`), except for ESG itself, DEI (anti-ESG bills often target DEI programs too: Kentucky HB 388 of 2025), unions
(labor boycotts) and climate (climate risk disclosure beside ESG metrics: H.R. 1187 of the 117th Congress); a labor
peace agreement's "picketing, work stoppages, boycotts" doesn't count as such a list (Hawaii SB 2241 of 2023 stays a
cannabis bill).

Run over every cached bill (.issues-cache, only bills with one of those words compared, before and after): 10 matches
leave, none join, ESG unchanged.
- Abortion 1: AL SB 261 of 2023.
- Firearms 9: AL SB 261 of 2023, AR SB 62 of 2023, KY HB 254 and HB 533 of 2023, UT SB 298 of 2026 (programmable money;
  "lawful ownership of a firearm" among the grounds an issuer can't deny), WV SB 112 of 2023, SB 275 of 2024, HB 3342 and
  SB 776 of 2025 ("Firearms Industry Nondiscrimination Act": banks and contractors that boycott gun makers). All read
  over: each is about boycotts of the gun industry, not gun laws, and stays in ESG (whose description names "boycotts
  of ... gun makers"). For the owner: keep them out of Firearms? Suggested: yes.
- Transgender: none moved (SB 261 never matched it).

**2026-11-17, owner:** the anti-ESG boycott-list exclusion applies to abortion and transgender people only; the nine "firearm industry nondiscrimination" bills stay under Firearms as well as ESG (AL SB 261 of 2023 is now Firearms and ESG, not Abortion).

# National issues: the sixth batch (2026-11-17)

Health insurance coverage and sexual assault and domestic violence, approved by the owner the same day, plus a "Sludge on
farmland" filter for PFAS, a "Presidential electors and popular vote" filter for Voting, and a new menu group, "Drugs"
(cannabis, psychedelics and kratom moved into it; overdoses joined it in the seventh batch). Checked the same way as the
fifth ten, over every bill the published site shows (454,708 bills in 50 states and Congress, .issues-cache refreshed
2026-11-17 after that afternoon's publish): four to six rounds, each a fresh random sample of 30 per issue, and searches
for likely misses. The other issues' rules are unchanged, except Voting (new rules for electors, below) and PFAS (sludge).
Groups: Health (coverage), Rights and public safety (assault). Short names: "health coverage", "sexual & domestic abuse"
(the full name doesn't fit the front page's column).

| Issue | Bills (this session) | Right of 30 read | States with none |
|---|---|---|---|
| Health insurance coverage | 1,608 (574) | 16, 21, 22, 24, then 28, 27, 25 | none |
| Sexual assault and domestic violence | 7,752 (2,707) | 24, 26, 27, 26, then 27-28, 26 | none |
| PFAS (with sludge) | 764 (299); was 730 | sludge filter 27-28 | AR, ID, ND, NE, SD, UT, WY |
| Voting: electors filter | 269 in the filter (voting 8,680) | 27 | |

Filters: coverage: Medicaid 1,016, Marketplaces and the ACA 652, Single payer and universal coverage 141, Public option 133.
Assault: Domestic violence and stalking 3,085, Trafficking 1,683, Child sexual abuse 1,047, Time limits 389, Rape kits 296,
Campus 253. PFAS: Sludge on farmland 110. Voting: Presidential electors and popular vote 269 (the National Popular Vote
compact, joining and leaving it in CT, MN, ME, NJ, OR, RI; winner-take-all vs. by congressional district: Nebraska LB 3 of
2025, Maine HLD1356 of 2025, Michigan HB 4216, Mississippi HB 600/823, Connecticut HB 6072 and HB 6005; faithless and false
electors; the Electoral Count Reform Act). Voting's new rules: "presidential elector(s)", "electoral college/votes/count",
"electors for/of the President", "winner-take-all" near "elector" or "president", "faithless/faithful/false/fake/alternate
electors". Before, about 120 titles with those words matched nothing (Nebraska LB 3, the Uniform Faithful Presidential
Electors Acts, Maine's switch to winner-take-all). The filter's misses in the sample are ranked-choice and omnibus bills
whose long text names presidential electors.

What went wrong in early rounds and was fixed:
- Coverage: "eligible for medical assistance" in passing (a hospital's eligibility, "a person eligible for medical
  assistance" in a court-of-claims or air-ambulance bill, enrollees of a drug purchasing program); now Medicaid needs
  eligibility, enrollment or expansion worded as the subject ("expands eligibility for Medicaid", "Medicaid eligibility",
  presumptive or continuous eligibility, postpartum coverage extended). The Affordable Care Act's own name ("Patient
  Protection ...") satisfied "protect"; California's digests give the federal essential benefits as background ("none");
  "ACA 1" is a California Assembly Constitutional Amendment; mandates "as an essential health benefit" (IVF, hearing
  aids) are left out; "uninsured" only as a population ("uninsured rate", "coverage for the uninsured"), never motorists.
- Assault: rape "or incest" exceptions in abortion bills; lists of crimes in sentencing, bail and voting-rights bills
  (`NOT_CRIMELIST`); leave laws ("safe leave from domestic violence, stalking, sexual assault"); boards with a member from
  a state coalition against domestic violence; gun-violence and workplace-violence protective orders; "affirmative
  consent" in auto-renewal laws.
- Remaining misses are mostly lists of victims in other programs (address confidentiality, victim compensation), counted
  wrong in about 1 of 30.

Scope decided here:
- Health insurance coverage: single-payer and universal coverage, public options and Medicaid buy-ins, Medicaid expansion
  and eligibility rules (who qualifies, enrollment, renewals, postpartum and immigrant coverage, coverage for people
  leaving prison), CHIP eligibility, state marketplaces and their subsidies and reinsurance, the ACA's protections
  (pre-existing conditions, guaranteed issue, codifying the ACA), special enrollment periods, short-term and association
  plans, coverage for the uninsured. Not a mandate to cover one treatment, Medicaid rates and billing, dental or vision
  alone, workers' compensation. Medicaid work requirements are also their own issue (overlap allowed).
- Sexual assault and domestic violence: sexual assault and abuse crimes and penalties, rape kits and forensic exams,
  time limits for abuse cases, campus sexual assault and Title IX, survivors' rights and confidentiality, protective orders,
  domestic and dating violence, stalking, human trafficking (decided: all of it, sex and otherwise, except forced-labor
  supply chains and drug trafficking; nearly all state trafficking bills are about sex trafficking), child sexual abuse
  and child sexual abuse material, intimate images shared without consent, sextortion and grooming. Not the sex offender
  registry's administration (`NOT_REGISTRY`; bills about where registrants live or how they register), divorce, custody and
  support bills that name domestic violence among other factors (`NOT_PASSING`), leave laws, sexual harassment alone.
- PFAS: sewage sludge, biosolids and septage spread on land count, even when the bill doesn't name PFAS (decided: these
  are the PFAS-on-farmland fights in Maine, Texas, Oklahoma and Michigan; about 40 such bills). Not sludge turned into
  energy, prevailing wages at treatment plants, sludge in landfills or leachate, or manure. Every sludge bill that names
  PFAS already matched before.

Questions for the owner (each with a suggested answer):
1. PFAS now includes about 40 sludge and biosolids bills that don't mention PFAS (Oklahoma's biosolids bans, Florida's
   "Biosolids Management", Connecticut's "use of biosolids by farmers"). Keep? Suggested: keep, under the filter.
2. Assault includes all human trafficking bills, not only sex trafficking (1,683 under the filter). Keep? Suggested: keep;
   or rename the filter "Trafficking" to make it plain.
3. Assault includes child sexual abuse material and nonconsensual intimate images (deepfakes too: those are also under
   AI). Keep? Suggested: keep.
4. Coverage includes Medicare bills about who's covered (Medigap's pre-existing conditions, "Choose Medicare") and
   federal ACA subsidy bills. Keep? Suggested: keep.
5. The NY bills that make an offense "qualifying" for bail (doxing a police officer, stolen property) are in Bail and
   pretrial release (seventh batch) and, when sexual, here. Fine as is? Suggested: yes.

**Answered 2026-11-17 (owner): as suggested.**

# National issues: the seventh batch (2026-11-17)

Twelve issues approved by the owner the same day: homelessness and camping bans, income tax cuts, homeowners insurance,
bail and pretrial release, drug penalties and overdoses, contraception, mental health and 988, food additives and dyes,
school meals, plastics and packaging, heat protections for workers, same-sex marriage. Same method: three or four rounds
of 30 random matches each, plus misses searches. One shared change: an issue can ask for more mentions in a long "What it
does" (`"body": 3`, read by `body_need()` in issues.py; the default stays two, so no other issue changes): homelessness and
school meals, which budget trailer bills and omnibus education bills name again and again. Groups: Housing and taxes
(homelessness, income tax, homeowners insurance), Rights and public safety (bail, same-sex marriage), Drugs (overdoses),
Health (contraception, mental health, food additives), Schools (school meals), Environment and energy (plastics), Work and
the economy (heat).

| Issue | Short name | Bills (this session) | Right of 30 read (rounds) | States with none |
|---|---|---|---|---|
| Homelessness and camping bans | homelessness | 1,586 (518) | 23, 25, 20, then 24-25 | AR, WY |
| Income tax cuts | income tax cuts | 260 (81) | 23, 25, 23, then 24-25 | AL, CA, FL, MD, NH, NV, SD, TN, TX, VA, WA, WY |
| Homeowners insurance | homeowners insurance | 906 (339) | 25, 26, 25, 27-28 | OH, SD, WY |
| Bail and pretrial release | bail and pretrial | 1,426 (512) | 21, 26-27, 24 | AZ, ID, WY |
| Drug penalties and overdoses | drugs and overdoses | 2,665 (751) | 25, 28, 27 | none |
| Contraception | contraception | 699 (203) | 25, 26, 26-27, 28-29 | SD, UT, VT, WY |
| Mental health and 988 | mental health and 988 | 1,990 (658) | 22, 24-25, 26 | none |
| Food additives and dyes | food additives | 154 (97) | 18, 26, 25-26, 27 | CO, IA, ME, MT, NC, ND, NM, NV, SD, WA, WY |
| School meals | school meals | 880 (314) | 22, 25-26, 25 | AL, ID, OH, WY |
| Plastics and packaging | plastics and packaging | 903 (309) | 21, 25, 26-27 | AR, MS, OH, OK, SD |
| Heat protections for workers | workplace heat | 83 (38) | 29, 28-29, 29-30 | 29 states |
| Same-sex marriage | same-sex marriage | 111 (34) | 24, 27, 28-29 | 23 states |

Several are below the 27 aimed for. What's left wrong, by issue:
- Homelessness (24-25): bills that name homeless people among other groups (veterans' documents, school funding weights,
  vital-records fee waivers count, as they're about homeless people; lists of "foster care, disabilities or homeless" don't)
  and budget trailer bills. A homelessness match now needs a homelessness word nearby (shelters, services, encampments,
  "homeless persons", housing programs). Tightening further would drop real bills (ID waivers, shelter rules).
- Income tax (24-25): rate bills that also change other taxes, and Missouri's and Minnesota's omnibus tax bills; bills on
  one kind of income ("income tax on tips", "liability on the earned income of a minor") are left out (`NOT_TAXITEM`).
  Rate changes worded only "modified" ("Individual income tax rates modified", Oklahoma's "income tax; rates; brackets")
  are left out unless they say cut, reduce, lower, phase out, eliminate, flat or trigger.
- Bail (24): New York bills that make an offense qualifying for bail (doxing a police officer, stolen property) and bills
  on electronic monitoring and failure to appear; pretrial intervention and diversion programs are left out.
- Mental health (26): "mental health" is everywhere, so it counts only for 988 and crisis lines and teams, involuntary
  commitment and treatment (Kendra's Law, the Baker Act, CARE Court), parity, suicide prevention, and mental health in
  schools; the rest are veterans' and correctional programs that name crisis services.
- School meals (25): omnibus education and appropriation bills (three mentions needed in a long text), family child care
  meals; summer EBT and summer meals count only when they say school meals.
- Plastics (26-27): composting and paint-recycling bills that mention packaging; plastic guns, plastic bullets and plastic
  utensils in prisons are left out.

Scope decided here:
- Homelessness and camping bans: camping and sleeping bans and encampments (Grants Pass laws, "unlawful camping"),
  housing first, shelters and services and their funding, homeless youth and students, IDs and records for homeless
  people. Not campgrounds, state-park camping fees, or campus protest encampments (those are under Protest).
- Income tax cuts: personal income tax rate cuts, a flat tax, triggers, phase-outs and elimination, and bills that suspend
  scheduled cuts. Not credits, deductions and exemptions for one kind of income or person, and not corporate rates alone.
  Filters: Elimination 125, Flat tax 28.
- Homeowners insurance: homeowners, dwelling, renters, condominium and flood insurance (including the National Flood
  Insurance Program's extensions: about a fifth of the bills, mostly in Congress), cancellations and nonrenewals, insurers
  of last resort (Citizens, FAIR plans, Hawaii Property Insurance Association, Texas Windstorm), fortified roofs and
  mitigation discounts, dog-breed underwriting. Not title, auto, commercial or credit property insurance. No filters.
- Bail and pretrial release: bail and bail reform, pretrial detention and release conditions, bail bond agents, bond
  amounts and schedules, personal recognizance. Not pretrial diversion programs. No filters.
- Drug penalties and overdoses: fentanyl and other drug crimes and penalties, drug-induced homicide, naloxone and other
  opioid antagonists, test strips, xylazine and nitazenes, Good Samaritan laws, syringe services and overdose prevention
  sites, harm reduction. Cannabis, psychedelics, kratom, tobacco and alcohol are left out (`NOT_OTHERDRUGS`); a bill
  naming both counts. Filters: Penalties 1,003, Fentanyl 921, Naloxone and test strips 645, Overdose prevention sites and
  harm reduction 174.
- Contraception: a right to contraception, insurance and Medicaid coverage (including vasectomies), pharmacists
  prescribing birth control, over-the-counter pills, emergency contraception (including in sexual assault care), family
  planning services. Not abortion bills that say they don't reach contraception, or wildlife fertility control. Filters:
  Insurance coverage 270, Pharmacists 123, Emergency contraception 83, Right to contraception 45.
- Mental health and 988: as above. Filters: Schools 851, 988 and crisis response 577, Involuntary treatment 436, Parity 127.
- Food additives and dyes: dye and additive bans (Red 40, Red 3, titanium dioxide, potassium bromate, brominated vegetable
  oil), additives in school food and SNAP, ultra-processed food, "generally recognized as safe", seed oils, "Make America
  Healthy Again" food bills. Not animal feed, pet food, hemp and CBD, dietary supplements, or cosmetics and menstrual
  products. Filters: School food 74, Dyes 73, Ultra-processed food 31, Labels and warnings 27.
- School meals: universal free meals, the community eligibility provision, school breakfast and breakfast after the bell,
  meal debt and lunch shaming, school nutrition standards and plant-based options. Filters: Free meals for all 305, Meal
  debt and lunch shaming 55.
- Plastics and packaging: bag, foam, straw and foodware bans (and repeals of them), extended producer responsibility for
  packaging, microplastics and microbeads, recycling labels, bottle deposits and redemption centers, chemical recycling.
  Filters: Bag and foam bans 450, Bottle deposits 111, Producer responsibility 72, Microplastics 60.
- Heat protections for workers: heat illness standards (water, rest, shade, training) and extreme-temperature protections,
  outdoors and indoors, and state laws barring local ones (Florida's "Employment Regulations"/"Labor Regulations"). Not
  student athletes, prisons or housing temperatures. No filters.
- Same-sex marriage: repealing state bans and constitutional definitions, protecting marriage equality (Respect for
  Marriage Act), gender-neutral marriage law, and bills against it (marriage "between one man and one woman", against
  Obergefell). Resolutions urging the Supreme Court to reverse Obergefell aren't in the site's data (resolutions are left
  out), so only bills and constitutional amendments show. Not covenant marriage (divorce rules), IVF coverage for
  same-sex couples, or SSI's "marriage penalty" (the "Marriage Equality for Disabled Adults Act"). No filters.

Questions for the owner (each with a suggested answer):
1. Homelessness includes students experiencing homelessness (school enrollment, coordinators: 380 under "Students") and
   ID fee waivers. Keep? Suggested: keep.
2. Income tax cuts leaves out rate bills that only say "modified" or "amendments" (Minnesota's "rates and brackets
   modified", Utah's "Income Tax Rate Amendments" is in only because of its title's wording); some raise rates. Keep it
   to clear cuts? Suggested: yes; or rename the issue "Income tax rates" and take every rate bill.
3. Homeowners insurance includes flood insurance and the National Flood Insurance Program's many short extensions in
   Congress. Keep? Suggested: keep flood insurance; consider leaving out bare NFIP extensions.
4. Contraception includes family planning services and their funding (Texas's women's health program, Title X). Keep?
   Suggested: keep.
5. Mental health and 988 includes suicide prevention training and programs. Keep? Suggested: keep.
6. Drug penalties and overdoses includes every drug crime bill (possession, trafficking, paraphernalia), not only fentanyl.
   Keep? Suggested: keep; the Penalties filter separates them.
7. Same-sex marriage can't show the Obergefell resolutions (resolutions aren't in the data). Add resolutions on this one
   subject? Suggested: no; say so on the issue page's description if visitors ask.

**Answered 2026-11-17 (owner): as suggested** (questions 1-11 across both batches: all kept; income tax cuts stays clear
cuts only; flood insurance kept, bills that only extend the National Flood Insurance Program dropped, by Homeowners
insurance's `none`; no resolutions).

## Final rounds (2026-11-17, after review)

The issues under 27 were tightened until two fresh samples in a row (new seeds, never reused) read 27 or better. Nearly
every remaining error was a bill matched only in a long "What it does" (budget trailer bills, omnibus education and tax
bills, programs that list homeless people or crime victims among others), so the main change is `"body"` in issues.py
(read by `body_need()`; `matches()` is the one test): how many mentions a long "What it does" needs, `0` meaning it never
counts on its own and the title or summary has to name the subject (the coordinator's suggestion). Other issues keep the
default, two.

| Issue | "body" | Bills (this session), before -> after | Last two samples |
|---|---|---|---|
| Homelessness and camping bans | 0 | 1,586 (518) -> 1,236 (379) | 28-29, 27-28 |
| Income tax cuts | 0 | 260 (81) -> 159 (45) | 30, 29 (then 29) |
| Bail and pretrial release | 0 | 1,426 (512) -> 1,141 (376) | 29, 28 |
| School meals | 4 | 880 (314) -> 790 (287) | 27, 27 |
| Mental health and 988 | 4 | 1,990 (658) -> 1,698 (549) | 27, 27 |
| Health insurance coverage | 3 | 1,608 (574) -> 1,511 (537) | 27, 27 |
| Sexual assault and domestic violence | 0 | 7,752 (2,707) -> 6,014 (1,948) | 29-30, 28-29 |
| Plastics and packaging | 0 | 903 (309) -> 676 (213) | 30, 29 |
| Homeowners insurance (NFIP extensions out) | 2 | 906 (339) -> 893 (328) | 28 |

Other fixes in these rounds:
- Income tax: rate-change wording in the summary only, and not for a business incentive ("income tax rate reductions"
  for a manufacturing reinvestment account), a corporate rate ("corporation net income tax rate"), tips and withholding,
  extending or restoring a rate (New York City's, Idaho's 2026 restoration), a defunct act's repeal, school district
  income taxes, or assessments; "Personal Income Tax Reduction Fund" in a data center revenue bill still counts (it funds
  cuts). States with none rise to 18 (AK, AL, CA, DE, FL, IL, KY, MD, NE, NH, NV, PA, SD, TN, TX, VA, WA, WY): several
  have no income tax, and Delaware, Illinois, Kentucky and Pennsylvania's rate bills say so only in "What it does".
- Bail: bills making an offense "qualifying" for bail (New York's lists since 2020) are counted right; they change who
  can be held on bail. Pretrial diversion programs stay out.
- Mental health: schools count only for "school/student mental health" services, screenings, staff, days and
  instruction ("school bus drivers' mental health evaluations", careers in mental health and educator preparation don't).
- Coverage: "for purposes of Medicaid eligibility" (disability definitions), "expansion of Medicaid services", benefits
  for part-time faculty, "individual mandate" only (not Texas's benefit-mandate review center), animal insurance, dental
  loss ratios.
- School meals: the National School Lunch Act named in child care and CACFP bills, "school food authority" in food
  donation laws, "eligible for free or reduced-price lunch" as an income test for other programs (prekindergarten seats,
  bus passes).
- Plastics: producer responsibility only for packaging, paper products and plastics (not paint, batteries, mattresses).
- Assault: "Election Code" restraining orders.

The cost is recall: bills whose title and summary are bland and whose subject shows only in "What it does" are now missed
for the six issues set to 0 or 4 (California's digests and Nebraska's statements are the usual cases: "Crimes: diversion"
that's about domestic violence; "Personal income taxation" that cuts Oregon's rates). For the owner: accept the lower
counts for precision? Suggested: yes for now; a later pass could let a "What it does" count when its first sentence
names the subject.

## The opening of "What it does" counts (2026-11-17)

For the eight issues with their own `"body"`, a match in the opening of "What it does" (its first 250 characters, carried
to the end of that sentence if it ends within 150 more: `lead()` in issues.py) now counts like the title and summary
(`matches()`). The opening says what the bill does; budget and omnibus bills name these subjects later. It brings back
bills like Oregon's "Personal income taxation" ("Modifies personal income tax brackets. Decreases rates ..."), Kentucky's
"The individual income tax rate", Michigan's rate rollback, Illinois's and Louisiana's digests, California's digests and
New York's memos that start with what the bill does. Not for school meals (`"lead": False`): school funding and early
childhood bills name the lunch program in their first sentence (a sample read 25-26); school meals also needs two
mentions in a short "What it does" (`"short": 2`: one-line summaries that use free-lunch eligibility as an income test).
Income tax also gained a rule for "reduce/eliminate/phase in a reduction in the (top) tax rate" near "individual income
tax" (Alabama's HB 115 and SB 48 of 2023), and lost "withholding" as an exclusion (it blocked Pennsylvania's "Elimination
of the Personal Income Tax", whose summary mentions withholding; only "be deducted and withheld" is excluded now); Iowa's
"individual and corporate income taxes" no longer trip the corporate-only exclusion.

| Issue | Bills (this session): head only -> with the opening | States with none, before -> after | Two fresh samples |
|---|---|---|---|
| Homelessness and camping bans | 1,236 (379) -> 1,410 (451) | AR, WY -> same | 28, 28 |
| Income tax cuts | 159 (45) -> 230 (68) | 18 -> 11 | 28, 27 (earlier version 28, 27-28) |
| Bail and pretrial release | 1,141 (376) -> 1,267 (432) | AZ, ID, WY -> same | 27, 29 |
| School meals (opening not used) | 790 (287) -> 716 (261) | AL, ID, OH, WY -> same | 28-29, 28 |
| Mental health and 988 | 1,698 (549) -> 1,747 (569) | none | 28, 27 |
| Health insurance coverage | 1,511 (537) -> 1,533 (545) | none | 27-28, 27 |
| Sexual assault and domestic violence | 6,014 (1,948) -> 6,837 (2,265) | none | 28, 28 |
| Plastics and packaging | 676 (213) -> 744 (250) | AR, IN, MS, NE, OH, OK, SD, TN, UT -> AR, MS, OH, OK, SD, TN, UT | 28, 29 |

Income tax's states with none went from 18 (AK, AL, CA, DE, FL, IL, KY, MD, NE, NH, NV, PA, SD, TN, TX, VA, WA, WY) to 11:
the nine without a tax on wages (AK, FL, NH, NV, SD, TN, TX, WA, WY), Maryland (its 2024 "Alteration of Brackets and Rates"
and 2026 "Income Tax and Sales and Use Tax - Rate Reductions" don't say an individual cut; county income tax rates and
corporate rate cuts are left out) and Virginia (only inflation indexing of brackets, SB 702 of 2026). Alabama, California,
Delaware, Illinois, Kentucky, Nebraska and Pennsylvania now have bills. School meals is smaller than before because of
`"short": 2`. In the samples, openings that look like passing mentions mostly turned out to be on the subject (Louisiana's
domestic abuse battery registry rule, New Jersey's earned income credit for domestic abuse victims, Utah's civil actions
for human trafficking).

## Large bills: one section about the issue (2026-11-25, the owner's approval)

Why: H.R. 1 of the 119th Congress ("One Big Beautiful Bill Act", P.L. 119-21) created the federal tax-credit scholarships
that start in 2027 (Sec. 70411), but wasn't on School vouchers: budget-sized bills need two mentions in "What it does", and
Congress's "What it does" is the CRS summary cut at 4,000 characters (the scholarship section is far past that).

The rule (issues.py `part_issues()`): a large bill also counts for an issue when one of its sections' openings (heading and
first sentence, `opening()`) matches the issue's rules, says it changes something (`CHANGE`: establishes, creates,
expands, amends, repeals, eliminates, requires, prohibits, increases, makes permanent ...), and isn't money or paperwork
(`FUNDS_ONLY`: appropriations and "funds" riders, apportionment, extensions to a date, authorizations of a year's
activities or of projects, reports, studies, "whether", "nothing in this title"). Examples a section gives in passing,
"(e.g., ...)", are dropped first. Sections: Congress's full CRS summary, one per "(Sec. N)" paragraph (records'
`sections`, states/us/convert.py `crs_sections()`, only when the summary shown is cut); else a "What it does" of 6,000+
characters marked "Section N." or "(Sec. N)" (`sections()`). Voting is left out (`"sections": False`: its patterns caught
"a unanimous vote of all Board members in order to grant parole", Kansas SB 459 of 2025). Lists say "One part of a larger
bill" and show the section as the line under the title. `OVERRIDES` (hand-picked, with a reason each) is empty.

Tried and dropped: California's digests in "This bill would ..." paragraphs as sections (28 additions in 2021-22, about
half wrong: a foster-care "payment or voucher" on School vouchers, a bankruptcy exemption for "sick leave, family leave" on
paid leave, a bail bond disclosure on bail).

Issue rules tightened on the way (they also apply to ordinary matching): campaign finance's "contribution limit" not with
ABLE accounts, IRAs, 401(k)s, health or education savings, 529s; property tax relief's credits not "refueling property",
"energy property" (federal equipment credits).

H.R. 1 (2025) now on: School vouchers (Sec. 70411, the scholarship credit), Prescription drug costs (71203, orphan drugs in
negotiation), Abortion and Contraception (71113, Medicaid payments to Planned Parenthood), Firearms (70436, the $200 tax on
silencers and short-barreled rifles ended), Immigration (10108, SNAP for some lawfully present noncitizens), Paid leave
(70304), Child care (70401, the employer credit), Nuclear energy (70510), Energy costs (10103, LIHEAP and SNAP), Climate
(50402, the ATVM loan cap), Health insurance coverage (71107, Medicaid redeterminations every six months). All real
sections that change the program.

Congress, all additions read (2021-22: 31, 2023-24: 45, 2025-26: 20, from 11, 26 and 9 large bills): about 90% right. Wrong
or doubtful, left as they are: NDAA FY2024's ERCIP projects on Firearms, its civilian pay rates on DEI, a wildfire
operations line; two appropriations acts' Sec. 210 (food service providers) on Plastics; an advisory committee's members on
Child care; DOJ reentry grants on Sexual assault. Right examples: the American Rescue Plan's family leave, child care and
premium credits; the Inflation Reduction Act's nuclear credit and Medicare vaccine cost-sharing; the 2023 omnibus's
continuous Medicaid eligibility for children; the Safer Communities Act's domestic violence gun restriction; FY2026's
hemp redefinition (Cannabis); the ROAD to Housing Act's housing supply grants.

States: only texts marked off in sections qualify. In a survey of every state's newest texts file (2026-11-25), they're in
Kansas, Missouri, Delaware and some New Jersey bills; Arizona, Florida, Iowa, Utah, West Virginia, Indiana and Ohio store
short summaries with no sections (no additions there: their budget-created programs, if any, need `OVERRIDES`). Additions
in the sample (KS 2023-25, MO 2024-26, DE 2023-25, NJ 2022-26): 5, all right: Missouri SB 894 and SB 1294 of 2026
("dangerous felony" to include statutory rape: Sexual assault), SB 1066 and SB 1410 of 2026 (short-term rentals assessed
as residential property), Delaware HB 2 of 2023 (the Marijuana Control Act's section on possessing a handgun: Firearms),
New Jersey S682 of 2026-27 (residential parking standards in redevelopment plans: Housing supply).

## National Popular Vote compact (2026-11-26, the owner)

Its own issue (`popularvote`, group Elections and government), from Voting's filter "Presidential electors and popular
vote", which stays. Scope: bills to join, leave or repeal the National Popular Vote Interstate Compact, and constitutional
amendments adopting it (Nevada's AJR 6 of 2023, which passed once and wasn't passed again in 2025). Rules: "national popular
vote", "popular vote (interstate) compact" (Alaska's short titles: "US president elect. popular vote compact"), "Agreement
Among the States to Elect the President", and "interstate compact" near electing the President or presidential electors.

Decided: presidential electors in general (winner-take-all or by congressional district, faithless and false electors) stay
in Voting and its filter, not here: they're a different question (how a state's own electors are chosen), and a page for
the compact reads clearer without them.

Known laws checked: Minnesota 2023 (in the state government and elections omnibus, HF 1830, Laws 2023 ch. 62 art. 4: the
site's summary is the Senate's of SF 1426 before conference and never names it, so it's in `OVERRIDES`; the standalone
HF 642 / SF 538 died), Maine LD 1578 (2023-24, law in 2024), Virginia HB 965 and SB 322 (2026). The earlier joins (MD, NJ
2007 ... CO, DE, NM, OR 2019) are before the issues' window (2023 on).

Check (2026-11-26, the published bills of 2026-11-17/19 in .issues-cache, plus a local build of VA, MN, ME, NV, CO, AK):
85 matches in 25 states and Congress, every one read: 83 right (joining, withdrawing, repealing, Missouri's SJR 17 of 2023
barring the state from entering it, Michigan's companion bills on the compact's electors), 2 wrong (Congress's H.J.Res. 23
of 2023 and H.J.Res. 102 of 2025: at-large Senators and electors by a U.S. constitutional amendment), now in `EXCLUDE`.
Of 111 bills whose titles name presidential electors or the popular vote and didn't match, a sample of 30 were all about
electors in general (faithful electors, district allocation, the electors' meeting day), as intended. Light history
(2015-22, titles and summaries only) would find Connecticut 2018, Delaware 2019 and Oregon 2019 as laws; Colorado has no
light history and New Mexico's 2019-20 is missing.
