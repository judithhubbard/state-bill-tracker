# What's changing: how each state's trends were chosen (2026-11-22)

Statistics > Trends (`renderTrends()`, from `trends()` in build_data.py) shows, for each subject in a state's `TRENDS`
(states/<st>/profile.py), how many of every 1,000 bills name it in their title or summary (the first 600 characters), session
by session, and old-to-new wording pairs from `WORDING`. New York's were picked by hand from an automatic phrase scan; every
other state's were picked the same way on 2026-11-22, from the local data (a few days old; some states' 2023 wasn't in the
local copy: AL, ID, IN, KY, LA, MD, RI, UT, WV, WY start at 2024 there, and a full build that has 2023 will show it too).

How:

- **The scan.** For each state, every phrase of one to three words, and about 85 hand-written candidate subjects (AI,
  e-bikes, data centers, PFAS, immigration, COVID-19 ...), counted as bills per session, and the change between the first
  and last session scored as a two-proportion z. In states whose sessions alternate in kind (long and short, regular and
  budget or fiscal), the same-kind sessions were compared too.
- **The bar.** A subject goes in when its share clearly rises or falls: about |z| ≥ 3 between the first and last session (or
  a peak in a middle session well above both ends), at least 8 bills in its busiest session, and a steady direction. A
  few steady rises just under the bar are kept and marked so in their state's section. "rise" for rising subjects;
  "spike" for subjects that peaked or fell (the card then says "Peaked at N bills in ...").
- **What's left out.** Drafting habits and changes in how titles or summaries are written (Alabama 2024's boilerplate on
  local funds, Pennsylvania's added short titles, New Hampshire's title wording), kinds of bills rather than subjects
  (Nebraska's "intent to appropriate" bills), subjects too general to mean much (elections, Medicaid, property tax, unless
  the shift is real and explained), and anything under the bar.
- **Patterns** were checked by reading samples of the bills matched in each session, the newest especially. Traps found:
  "generative" matches "neurodegenerative" and "regenerative" (use `\bgenerative`); "mental health" matches "environmental
  health"; "tenant" matches "lieutenant"; "specie" matches "species"; "data center" matches Illinois's Early Childhood Data
  Center and Oklahoma's State Data Center (the census office); "wage" matches "wagering"; "grocery" matches wine sold in
  grocery stores; "shelter" matches animal shelters. `\bAI\b` is matched case-sensitively, with the rest in `(?i:...)`.
- **Names** are plain and neutral ("Gender identity", "Immigration", "Diversity, equity and inclusion").
- **Left empty** (no Trends button): Arkansas and Wyoming, for the reasons in their sections. States with two sessions
  shown, or short titles only, get fewer subjects.
- **Second pass (2026-11-22): Arkansas, Kentucky, New Hampshire, Utah, Wyoming**, first left empty, were scanned again from
  the full data the site uses (each state's download cache, through copy-data.yml: 2023-26 for all five), comparing sessions
  of one kind (Arkansas regular with regular and fiscal with fiscal; Kentucky's 60-day even years and 30-day odd years;
  Wyoming general with general and budget with budget). Kentucky, New Hampshire and Utah got subjects; Arkansas and Wyoming
  stay empty.

To redo a state: the scan scripts aren't kept in the repository; the method above is enough to repeat it with a short
script over `C.load_session()`'s records (title + " . " + summary[:600], as `trends()` reads them).

The sections below give, per state, each subject's bills and share per 1,000 by session and why it was chosen, any wording
pair, and what was looked at and left out.

## Alaska (ak)

Sessions shown: 2023-24 (684 bills), 2025-26 (707). Two sessions only, so only the two clearest shifts.

| Subject | Kind | Bills by session | Per 1,000 | Why |
|---|---|---|---|---|
| Natural gas pipeline and imports | rise | 1, 12 | 1.5, 17.0 | The scan's top real subject ("gasline", "gas pipeline", "natural gas": 0 to 9 each): the Alaska LNG pipeline's taxes and AGDC, and LNG import facilities for Cook Inlet's gas shortfall. Samples all on topic. |
| School funding | rise | 7, 20 | 10.2, 28.3 | "Schools" and "school funding" rose most among policy phrases: base student allocation bills. Samples all on topic. |

Wording pairs: none found.

Looked at and left out: "contributions" (11 to 33) mixes campaign, retirement, PFD and school contributions; paid leave (1 to 6) and AI (5 to 2) are too few to read as a trend.

## Alabama (al)

Sessions shown: 2024 (844 bills), 2025 (968), 2026 (1,046). (2023 isn't in the local copy.) 2024's summaries carry a stock paragraph on local funds that later years dropped; the drafting phrases that fell with it were left out.

| Subject | Kind | Bills by session | Per 1,000 | Why |
|---|---|---|---|---|
| Property tax breaks for seniors | rise | 2, 1, 25 | 2.4, 1.0, 23.9 | The scan's top subject: 2026 brought about twenty county constitutional amendments for senior property tax exemptions, plus homestead exemption bills. |
| Artificial intelligence | rise | 0, 1, 8 | 0.0, 1.0, 7.6 | Chatbots, AI in insurance coverage decisions, AI-generated content disclosure. All samples on topic. |
| Rural health care | rise | 2, 2, 11 | 2.4, 2.1, 10.5 | 2026's federal Rural Health Transformation money and rural provider bills. |
| Utilities | rise | 3, 12, 23 | 3.6, 12.4, 22.0 | "Utility" rose steadily: Public Service Commission changes, large-load (data center) contracts, utility tax exemptions, sewer systems. |

Wording pairs: none found.

Looked at and left out: Medicaid (1, 15, 13: 2024's single match looks low for the state and may reflect how 2024's records were written); hemp and THC (0, 6, 4) and vaccines (2, 11, 3) are too few.

## Arkansas (ar): skipped

Sessions shown: 2023 (1,472 bills), 2024 fiscal (179), 2025 (1,695), 2026 fiscal (180). No summaries in the records (titles only, about 130 characters a bill). Rechecked 2026-11-22 on the full data (the same four sessions as the local copy).

Left empty. The even-year fiscal sessions are almost all appropriation bills, so every policy subject drops to zero in them and the trend line zig-zags; the card's "N bills this session" would read 0 for the 2026 fiscal session. Regular against regular (2023 with 2025), no candidate subject reaches the bar: artificial intelligence is closest (0 to 8, z +2.6: deepfakes, AI in health care, AI policies for public entities), then fluoride (0 to 6), domestic violence (1 to 8) and foreign entities (4 to 10, z +1.3); the phrase scan's movers are drafting words ("regarding" 78 to 47, "prohibit" 37 to 80, "fiscal year"). Fiscal against fiscal (2024 with 2026, 180 bills each, nearly all appropriations) moves nothing. Worth adding if trends() ever compares sessions of one kind (as the statistics do with `session_kind()`), and again once 2027's regular session is in.

## Arizona (az)

Sessions shown: 2024 (1,708 bills), 2025 (1,779), 2026 (1,206). (2023 isn't in the local copy.) Open States' records: short titles ("Data centers; tax relief; repeal"), summaries for about 3% of bills, so the scan reads titles.

| Subject | Kind | Bills by session | Per 1,000 | Why |
|---|---|---|---|---|
| Data centers | rise | 0, 1, 10 | 0.0, 0.6, 8.3 | The clearest new subject: 2026 bills on data centers' tax breaks, energy costs and planning. All samples on topic. |
| Landlords and tenants | rise | 7, 22, 16 | 4.1, 12.4, 13.3 | "Landlord" and "tenant" rose together: evictions, application fees, habitable conditions, mobile homes. |
| Abortion | rise | 6, 11, 15 | 3.5, 6.2, 12.4 | After the 2024 ballot measure (Prop 139), more bills to repeal or keep abortion laws: waiting periods, reporting, abortion drugs. |

Wording pairs: none. ("Special plates" became "special plate" in titles in 2026: a drafting change, left out.)

Looked at and left out: elections (96, 88, 33 titles: real but a broad subject, left out as the rules ask); "continuation" (the agency sunset bills, 34, 22, 6: a cycle, not a subject); cryptocurrency (5, 11, 1).

## California (ca)

Sessions shown: 2021-22 (4,502 bills), 2023-24 (4,854), 2025-26 (4,271). The records carry titles only ("Vehicles: electric bicycles."), so the scan and the patterns read titles.

| Subject | Kind | Bills by session | Per 1,000 | Why |
|---|---|---|---|---|
| Artificial intelligence | rise | 1, 25, 51 | 0.2, 5.2, 11.9 | The scan's top rising phrase ("artificial", "intelligence": 0, 22, 33). The first pattern also hit "neurodegenerative" through "generative": fixed with a word boundary. |
| Immigration | rise | 13, 14, 43 | 2.9, 2.9, 10.1 | 2025's bills on immigration enforcement at schools, hospitals and courts, and cooperation with federal agents. |
| Data centers | rise | 0, 1, 11 | 0.0, 0.2, 2.6 | Electricity rates and power use of data centers. All samples on topic. |
| Wildfire | rise | 40, 33, 66 | 8.9, 6.8, 15.5 | Doubled after the January 2025 Los Angeles fires: mortgage forbearance, tax exclusions, rebuilding, prevention. |
| Home insurance | rise | 6, 12, 22 | 1.3, 2.5, 5.2 | "Residential property insurance" and "FAIR Plan" rose (0 to 11, 1 to 10) as insurers left fire areas. |
| E-bikes and scooters | rise | 2, 8, 12 | 0.4, 1.6, 2.8 | Electric bicycle rules, speed limits, a pilot license plate program. |
| COVID-19 | spike | 71, 7, 0 | 15.8, 1.4, 0.0 | The scan's top falling phrase. |
| Cannabis | spike | 59, 51, 18 | 13.1, 10.5, 4.2 | Fell steadily after the first years of legal sales. |
| Fentanyl | spike | 8, 25, 4 | 1.8, 5.2, 0.9 | Peaked in 2023-24 (sentencing bills); few since. |
| Homelessness | spike | 44, 44, 24 | 9.8, 9.1, 5.6 | Fell by almost half in 2025-26. |
| Mental health | spike | 76, 47, 32 | 16.9, 9.7, 7.5 | "Mental health services" fell (31, 11, 3); the Mental Health Services Act became the Behavioral Health Services Act in 2024 (Prop 1), but "behavioral health" didn't rise (17, 13, 11), so no wording pair. The pattern first matched "environmental health": fixed. |
| Catalytic converters | spike | 10, 3, 1 | 2.2, 0.6, 0.2 | The 2021 wave of thefts; few bills since. |

Wording pairs: none. ("Income taxes: credits" gave way to "Personal Income Tax Law: credits" in titles: a drafting change, left out.)

Looked at and left out: "gold and silver as money" (matched "species", false); paid leave (11, 8, 1) and broadband (22, 15, 7): too few or too slight; "budget" and "personal income tax" (drafting).

## Colorado (co)

Sessions shown: 2024 (705 bills), 2025 (657), 2026 (626). (2023 isn't in the local copy.)

| Subject | Kind | Bills by session | Per 1,000 | Why |
|---|---|---|---|---|
| Income tax credits | spike | 25, 7, 3 | 35.5, 10.7, 4.8 | The scan's top falling subject phrase: new or extended credits all but stopped once the state's budget shortfall began in 2025. Samples all on topic. |

Wording pairs: none.

Looked at and left out: the same shortfall shows in the drafting: "making an appropriation" fell from 173 bills to 72 and 48, and "reducing an appropriation" rose (14, 29, 35). A real change, but not a subject, so not a card. No candidate subject (AI, child care, elections, wildfire ...) moved by more than chance between 2024 and 2026.

## Connecticut (ct)

Sessions shown: 2022 (1,003 bills), 2023 (3,224), 2024 (990), 2025 (3,895), 2026 (1,110). Odd years are long sessions, even years short ones, so each subject was also compared within its kind (2023 with 2025; 2022, 2024, 2026). Titles only (no summaries in the records).

| Subject | Kind | Bills by session | Per 1,000 | Why |
|---|---|---|---|---|
| Artificial intelligence | rise | 0, 1, 3, 16, 6 | 0.0, 0.3, 3.0, 4.1, 5.4 | Rises in both kinds of session: AI rules, AI-made intimate images, AI data centers, automated decisions at work. |
| COVID-19 | spike | 16, 13, 1, 7, 1 | 16.0, 4.0, 1.0, 1.8, 0.9 | The scan's top falling phrase. |
| Mental health | spike | 23, 38, 10, 35, 7 | 22.9, 11.8, 10.1, 9.0, 6.3 | "Mental" and "behavioral" both fell, most of all in the short sessions (22.9, 10.1, 6.3). |

Wording pairs: none.

Looked at and left out: the meals tax (dedicating or sharing the local meals tax: 1, 9, 7, 14, 13) rose in short sessions only; elections (10.0 to 20.7 per 1,000) is broad and peaks in 2025; "elderly"/"senior" dropped only in 2026; paid leave and solar peak and fall back with no trend.

## Delaware (de)

Sessions shown: 2023-24 (785 bills), 2025-26 (833). Summaries are mostly the stock "An act to amend Title N of the Delaware Code relating to ...", so titles carry the subject. Two sessions only: one clear shift.

| Subject | Kind | Bills by session | Per 1,000 | Why |
|---|---|---|---|---|
| Utilities and utility rates | rise | 3, 21 | 3.8, 25.2 | The scan's top rising phrase ("utilities", 1 to 12): 2025's bills on utility rates, billing, shutoffs and the Public Service Commission after Delmarva Power's rate increases. All samples on topic. |

Wording pairs: none.

Looked at and left out: cryptocurrency (0 to 5) and child care (3 to 10) are too few; "health" and "insurance" fell (38 to 19, 35 to 17) without one subject behind it.

## Florida (fl)

Sessions shown: 2024 (1,747 bills), 2025 (1,809), 2026 (1,755). (2023 isn't in the local copy.) Few subjects moved much in three years.

| Subject | Kind | Bills by session | Per 1,000 | Why |
|---|---|---|---|---|
| Immigration | rise | 7, 20, 20 | 4.0, 11.1, 11.4 | Nearly tripled from 2025: state immigration enforcement, the State Board of Immigration Enforcement, services to noncitizens. All samples on topic. |
| Hurricanes and flooding | spike | 28, 30, 9 | 16.0, 16.6, 5.1 | Many bills after the 2022 and 2024 hurricanes (mitigation grants, insurance cancellations, local rules after a storm, flood disclosure); far fewer in 2026. |

Wording pairs: none.

Looked at and left out: domestic violence (8, 9, 18) doubled only in 2026; social media (13, 3, 4) peaked in 2024 only; condominiums (18, 20, 14) and property insurance hold steady.

## Georgia (ga)

Sessions shown: 2023-24 (2,156 bills), 2025-26 (2,288). Titles only (no summaries in the records). Two sessions only: the two clearest shifts.

| Subject | Kind | Bills by session | Per 1,000 | Why |
|---|---|---|---|---|
| School tax homestead exemptions | rise | 27, 63 | 12.5, 27.5 | The scan's top phrase ("school district ad valorem", 6 to 55): local bills giving homeowners an exemption from school property taxes, many after the 2024 law (HB 581) let school districts opt out of the new statewide exemption. Local bills, all on topic. |
| Data centers | rise | 1, 10 | 0.5, 4.4 | Data center tax breaks, transparency, moratoriums and electricity costs. All samples on topic. |

Wording pairs: none.

Looked at and left out: immigration (10 to 21: doubled, but under the bar for a two-session state); elections (107 to 79 titles: broad, and 2023-24 followed the 2021 election law); homestead exemptions in general (96 to 124) changed less than the school ones.

## Hawaii (hi)

Sessions shown: 2023-24 (5,810 bills), 2025-26 (5,631). Two sessions only, so only the five clearest shifts.

| Subject | Kind | Bills by session | Per 1,000 | Why |
|---|---|---|---|---|
| Immigration | rise | 6, 35 | 1.0, 6.2 | The scan's top candidate (z +4.6): 2025-26's bills on cooperation with federal immigration enforcement, notice of rights in custody, legal representation. Samples all on topic. |
| Homeowners and condo insurance | rise | 14, 47 | 2.4, 8.3 | Hawaii Property Insurance Association, condominium master policies, wildfire risk scores. Samples all on topic. |
| E-bikes and scooters | rise | 6, 27 | 1.0, 4.8 | "Electric bicycles" 1 to 21 in the scan: classes, safe riding, rebates. |
| Artificial intelligence | rise | 13, 44 | 2.2, 7.8 | Working groups, deepfakes in campaign ads, disclosure; "\bgenerative\b" keeps out "regenerative tourism". |
| Wildfire | spike | 75, 32 | 12.9, 5.7 | Peaked after the August 2023 Maui fires (Lahaina recovery, relief fund); fell in 2025-26. |

Wording pairs: none. The scan's biggest shift, "Hawaiʻi" (2023-24) to "Hawaii" (2025-26), is how the source spells the name, so no pattern names Hawaii; "Department of Agriculture and Biosecurity" is a 2025 agency rename.

Looked at and left out: invasive species and biosecurity (42 to 48, flat once the department's new name is left out); climate (45 to 66, z about 2.5); Medicaid (42 to 77) too general; phones in schools, PBMs, crypto, age verification (0 to 6 or 7) too few.

## Iowa (ia)

Sessions shown: 2023-24 (2,055 bills), 2025-26 (2,542). Two sessions, and only about 30% of bills have a summary (titles are short), so only three subjects.

| Subject | Kind | Bills by session | Per 1,000 | Why |
|---|---|---|---|---|
| Artificial intelligence | rise | 3, 22 | 1.5, 8.7 | z +3.3: AI in elections, chatbots, insurers' utilization review, ownership of AI output. Samples all on topic. |
| Gender identity | spike | 15, 4 | 7.3, 1.6 | z -3.0: 2023-24's bills on gender transition care, school instruction, restrooms and the civil rights act; fewer after those passed. |
| Cybersecurity | spike | 10, 0 | 4.9, 0.0 | z -3.5: 2023-24's ransomware and school cybersecurity bills; none in 2025-26. |

Wording pairs: “Medicaid” (23.8 to 12.2 per 1,000) to “medical assistance” (0 to 6.3), the name Iowa law uses; together they barely changed (23.8, 18.5), so it's wording, not subject.

Looked at and left out: immigration (1 to 10, z about 2.7); "regents institutions", "innovation zone schools" are drafting phrases.

## Idaho (id)

Sessions shown: 2024 (643 bills), 2025 (715), 2026 (730); 2023 isn't in the local data. Summaries are a line or two, so only two subjects pass.

| Subject | Kind | Bills by session | Per 1,000 | Why |
|---|---|---|---|---|
| Repealing outdated laws | rise | 1, 5, 25 | 1.6, 7.0, 34.2 | The scan's top real phrase ("code cleanup" 0, 1, 25): 2026's run of "Code cleanup, ..." bills repealing obsolete sections, after the 2025 Idaho Code cleanup act. |
| School building funding | spike | 12, 6, 2 | 18.7, 8.4, 2.7 | School facilities and modernization funds, steadily down after 2024's school facilities funding law. |

Wording pairs: none.

Looked at and left out: library materials harmful to minors (9, 4, 5: a 2024 peak, then flat); elections (36, 19, 21: 2024's long list of election bills, z -2.5); "FY", "trailer", "original" are budget drafting phrases.

## Illinois (il)

Sessions shown: 2021-22 (10,175 bills), 2023-24 (9,962), 2025-26 (10,082). The records carry only the short titles ("CRIM CD-Deepfake-Minor-Sexual"), no summaries, so patterns include the titles' abbreviations (VAX).

| Subject | Kind | Bills by session | Per 1,000 | Why |
|---|---|---|---|---|
| Artificial intelligence | rise | 1, 21, 58 | 0.1, 2.1, 5.8 | z +7.5, the scan's strongest rise: chatbots, deepfakes, AI in schools, health care and government. |
| Wind and solar power | rise | 19, 29, 48 | 1.9, 2.9, 4.8 | "solar" 2, 10, 30 in the scan: county siting rules, property tax on solar, permitting. |
| Data centers | rise | 4, 6, 17 | 0.4, 0.6, 1.7 | Tax incentives and hyperscale data centers; "Early Childhood Data Center" left out. |
| Paid leave | rise | 5, 21, 21 | 0.5, 2.1, 2.1 | Paid Leave for All Workers Act (2023) and its amendments. |
| COVID-19 | spike | 71, 12, 4 | 7.0, 1.2, 0.4 | z -7.7: 2021-22's relief and emergency bills. |
| Vaccines | spike | 26, 14, 8 | 2.6, 1.4, 0.8 | Mostly COVID vaccine mandates and exemptions, falling with COVID. |

Wording pairs: none (the titles' abbreviations change between bills, not over time).

Looked at and left out: pretrial release (11, 13, 44 by "pretrial" alone, but with "bail" 24, 15, 44: 2021-22 was already busy, so no steady rise); social media (4, 6, 14) and fentanyl (5, 18, 17), z under 3; unemployment insurance (28, 8, 12) uneven; "FY27", "-tech" (shell bills), "OCE" are drafting codes.

## Indiana (in)

Sessions shown: 2024 (745 bills, short session), 2025 (1,239, long), 2026 (748, short); 2023 isn't in the local data. Titles are short and general ("Various education matters") and summaries only name the Indiana Code title, so only one subject passes.

| Subject | Kind | Bills by session | Per 1,000 | Why |
|---|---|---|---|---|
| Utilities | rise | 14, 33, 36 | 18.8, 26.6, 48.1 | The scan's top rising phrase (z +3.2), and it holds between the two short sessions (14 to 36): utility costs and disconnections, sale of utilities, community energy and data centers' power. |

Wording pairs: none.

Looked at and left out: data centers (0, 2, 5) too few; "minors" (10, 3, 0) mixes age verification, work permits and checking accounts; no candidate subject reached |z| 2.5.

## Kansas (ks)

Sessions shown: 2023-24 (1,427 bills), 2025-26 (1,367). Two sessions only, so only the three clearest shifts.

| Subject | Kind | Bills by session | Per 1,000 | Why |
|---|---|---|---|---|
| Immigration | rise | 1, 18 | 0.7, 13.2 | z +4.0: ICE detainers and cooperation, E-Verify, public benefits for people unlawfully present. Samples all on topic. |
| Landlords and tenants | rise | 4, 22 | 2.8, 16.1 | "landlord and tenant" 1 to 15 in the scan: late fees, deposits, disclosures, local rental rules. "\btenant" keeps out "lieutenant". |
| Income tax rates and deductions | spike | 28, 6 | 19.6, 4.4 | The scan's strongest falls ("social security", "standard deduction", "income limit"): 2023-24's income tax cut bills, settled by the 2024 special session's law. |

Wording pairs: none.

Looked at and left out: abortion (30 to 12, z -2.7); sales tax on food ("sales and compensating use" 39 to 14) is part of the same 2023-24 tax package; opioid antagonists (0 to 6) too few.

## Kentucky (ky)

Sessions shown (full data, 2026-11-22): 2023 (865 bills, 30-day session), 2024 (1,206, 60-day budget session), 2025 (1,056, 30-day), 2026 (1,263, 60-day). Each subject was compared within its kind (2024 with 2026; 2023 with 2025) and across the two pairs (2023-24 with 2025-26). The records have only Kentucky's short titles ("Grooming a minor", with "AN ACT relating to ..." as the summary; about 86 characters a bill, the same every year), so one subject passes, just under the bar.

| Subject | Kind | Bills by session | Per 1,000 | Why |
|---|---|---|---|---|
| Housing and zoning | rise | 5, 5, 10, 19 | 5.8, 4.1, 9.5, 15.0 | The clearest candidate: 60-day sessions 5 to 19 (z +2.8), 30-day sessions 5 to 10, the two years together 10 to 29 (z +2.7); just under the bar, kept as a steady rise. Affordable housing and its trust fund, "Planning and zoning" bills (1, 11 in the phrase scan), accessory dwelling units, housing development districts, manufactured housing. All matches read; all on topic. |

Wording pairs: none found.

Looked at and left out: "making an appropriation therefor" (60, 78, 17, 26: falls in both kinds, z -5 to -6) is how titles are written, not a subject; vehicles (23, 29, 22, 17) is mixed (taxes, plates, dealers); the Supplemental Nutrition Assistance Program (0, 0, 0, 6 bills, after 2025's federal changes), data centers (1, 0, 0, 5), AI (0, 0, 2, 3) and crypto (0, 1, 2, 4) are too few; elections (17, 36, 18, 22) follows the session kind.

## Louisiana (la)

Sessions shown: 2024 (1,484 bills, regular), 2025 (930, fiscal), 2026 (1,776, regular); 2023 isn't in the local data. Each subject also holds between the two regular sessions, 2024 and 2026. Titles are short and the summaries are subject tags ("Energy/pipelines"), so few subjects pass.

| Subject | Kind | Bills by session | Per 1,000 | Why |
|---|---|---|---|---|
| Artificial intelligence | rise | 5, 1, 23 | 3.4, 1.1, 13.0 | z +3.0: chatbots and minors, deepfakes of students, AI in insurance, disclosure of AI content. Samples all on topic. |
| Carbon capture and storage | rise | 11, 25, 26 | 7.4, 26.9, 14.6 | Class VI wells, CO2 pipelines, parish control and liability; 2026 is double 2024 (the fiscal session's 26.9 is highest). |
| Concealed carry | spike | 11, 3, 1 | 7.4, 3.2, 0.6 | 2024's permitless-carry bills (law that year), then few. |

Wording pairs: none.

Looked at and left out: "libraries" (10, 0, 0) comes from a subject tag 2024's records use and later ones don't; pipelines and expropriation (5, 7, 30) overlap carbon capture and foreign-owned land; "memorial highway" and "suit captioned" are naming and settlement bills; elections (72, 28, 54) follows the session kind.

## Massachusetts (ma)

Sessions shown: 2023-24 (6,341 bills), 2025-26 (7,291). Two sessions, and the records have titles only (no summaries), so only five subjects.

| Subject | Kind | Bills by session | Per 1,000 | Why |
|---|---|---|---|---|
| Emergency family shelter | rise | 3, 24 | 0.5, 3.3 | "emergency assistance" 0 to 9, "shelter" 3 to 16 in the scan: residency rules, oversight and security in the state's emergency assistance shelter system. Animal shelters left out. |
| MBTA Communities zoning | rise | 1, 18 | 0.2, 2.5 | The scan's top rising phrase (z +3.6): bills to repeal or change the MBTA Communities Act's multi-family zoning rule. |
| Rat poisons | rise | 3, 17 | 0.5, 2.3 | Second-generation anticoagulant rodenticides: towns asking to ban them, and a statewide limit. |
| Artificial intelligence | rise | 4, 20 | 0.6, 2.7 | z +2.9: chatbots, AI in health care decisions, provenance, safety. Samples all on topic. |
| Civil service exemptions and exams | spike | 61, 30 | 9.6, 4.1 | The scan's strongest fall (z -4.1): towns' petitions to exempt police and fire positions from civil service and to let named people take the exam. |

Wording pairs: none.

Looked at and left out: "resilience" (16 to 40) is too broad (climate, power grid, farms, older adults); parcels, bridges and retirement boards are local and naming bills; no laws yet in 2025-26 for the rising subjects (the session runs to the end of 2026).

## Maryland (md)

Sessions shown: 2024 (2,714 bills), 2025 (2,605), 2026 (2,660); 2023 isn't in the local data. The records have titles only (no summaries).

| Subject | Kind | Bills by session | Per 1,000 | Why |
|---|---|---|---|---|
| Cryptocurrency | rise | 0, 3, 13 | 0.0, 1.2, 4.9 | z +3.6: virtual currency kiosks, digital asset regulation, a bitcoin reserve. Samples all on topic. |
| Immigration | rise | 4, 20, 17 | 1.5, 7.7, 6.4 | "immigration" 0, 11, 16 in the scan: enforcement at sensitive locations, detention standards, arrests at courthouses. |
| Data centers | rise | 1, 5, 10 | 0.4, 1.9, 3.8 | Siting, electricity rates and taxes for data centers. |

Wording pairs: none.

Looked at and left out: transmission lines (0, 14, 7: the 2025 Piedmont line fight, not steady); firearms (45, 30, 31, z about -1.5); "Frederick", "Harford", "Anne Arundel" are county bills; "sunset extension" is drafting.

## Maine (me)

Sessions shown: 2023-24 (2,291 bills), 2025-26 (2,245). Two sessions only, so only the two clearest shifts. Maine's summaries are short (the title and the LD line), so matching is mostly on titles.

| Subject | Kind | Bills by session | Per 1,000 | Why |
|---|---|---|---|---|
| Artificial intelligence | rise | 0, 11 | 0.0, 4.9 | Top candidate (z +3.4): AI in rent setting, insurance denials, campaign ads, mental health services, images of minors. Samples all on topic. |
| Paid family and medical leave | rise | 3, 17 | 1.3, 7.6 | The scan's "paid", "family and medical", "medical leave benefits" (z +3.2 to +3.6): changes, delays, exemptions and repeal bills for the new state program, whose benefits start in 2026. Includes earned paid leave. Samples all on topic. |

Wording pairs: none found.

Looked at and left out: hunting (29 to 16, z about -2.3) and MaineCare (47 to 24: drafting of titles varies) are not clear enough; "Veterans Memorial Bridge" renamings (0 to 14) are naming bills; minimum wage (10 to 0) and behavioral health services (10 to 0) are one-session clusters.

## Michigan (mi)

Sessions shown: 2023-24 (3,526 bills), 2025-26 (3,706). Two sessions, titles only, but big shifts: the falls are mostly 2023-24's packages carrying out the 2022 ballot proposals (abortion rights, voting, financial disclosure).

| Subject | Kind | Bills by session | Per 1,000 | Why |
|---|---|---|---|---|
| Data centers | rise | 3, 43 | 0.9, 11.6 | Top candidate (z +5.7): siting, water and power reporting, tax exemptions, community benefit acts. |
| Michigan Strategic Fund | rise | 2, 54 | 0.6, 14.6 | The scan's top phrase (z +6.8): a 2025 package of bills "to reflect elimination of the Michigan strategic fund" in each act that names it. |
| Cryptocurrency | rise | 2, 18 | 0.6, 4.9 | z +3.5: crypto kiosks, digital asset holdings. Samples all on topic. |
| Drones | rise | 1, 14 | 0.3, 3.8 | z +3.3: drones near critical infrastructure, state purchases. |
| Carbon capture | rise | 1, 13 | 0.3, 3.5 | z +3.1: carbon dioxide capture, pipelines, sequestration. |
| Earned wage access | rise | 0, 12 | 0.0, 3.2 | The scan's "earned wage access" (z +3.4): a 2025 package exempting the services from loan and money transmission laws. |
| Abortion | spike | 36, 5 | 10.2, 1.3 | z -5.0: 2023's repeal of abortion laws after Proposal 3, and its conforming bills. |
| Juvenile justice | spike | 26, 7 | 7.4, 1.9 | "Juveniles" (11 to 0), life without parole (12 to 0): 2023's juvenile justice package. |
| Financial disclosure | spike | 21, 3 | 6.0, 0.8 | z -3.8: 2023's bills carrying out Proposal 1's disclosure reports for officials and candidates. |
| Absentee voting | spike | 19, 1 | 5.4, 0.3 | "Absent voter" (18 to 1, z -4.0): 2023's bills carrying out Proposal 2. |

Wording pairs: none found.

Looked at and left out: the Uniform Commercial Code (0 to 33) and residential mortgage licensing (0 to 23) packages are conforming references; prior authorization (0 to 8) and medical debt (0 to 7) are too few; public health code (44 to 9) overlaps the abortion repeal.

## Minnesota (mn)

Sessions shown: 2023-24 (6,065 bills), 2025-26 (5,988). Two sessions only, so only the clearest shifts. About a fifth of bills have a summary; most matching is on the short titles, the same in both sessions.

| Subject | Kind | Bills by session | Per 1,000 | Why |
|---|---|---|---|---|
| Fraud | rise | 4, 43 | 0.7, 7.2 | The scan's "fraud" (4 to 39, z +5.4): fraud in state programs (medical assistance, child care, reporting by state employees, a fraud tip line, an investigating commission). A few are consumer fraud; all are about fraud. |
| Paid family and medical leave | rise | 13, 39 | 2.1, 6.5 | "Paid leave" (1 to 26, z +4.8), "Minnesota paid": changes, exemptions and repeal bills for the Paid Leave Law passed in 2023, whose benefits start in 2026; includes earned sick and safe time. |
| Data centers | rise | 2, 16 | 0.3, 2.7 | z +3.3: siting, hearings, energy rules and the sales tax exemption. Samples all on topic. |
| Artificial intelligence | rise | 4, 19 | 0.7, 3.2 | z +3.2: AI pricing, disclosures, generated abuse images, displaced workers; 2023-24's were deepfake bills. |
| Immigration | rise | 16, 37 | 2.6, 6.2 | "Immigration" (5 to 24, z +3.6): cooperation with ICE, detention flights, coverage of undocumented adults. Samples all on topic. |

Wording pairs: none found.

Looked at and left out: property tax (120 to 70) and the big falling phrases ("tax provisions modified", "money appropriated") are changes in how titles are written; homelessness (30 to 11, z -2.9) is mostly 2023's grant bills; social media and prior authorization (z +2.7) are close but small.

## Missouri (mo)

Sessions shown: 2024 (2,494 bills), 2025 (2,592), 2026 (3,055). Texts are short (titles and a topic line), so few subjects show a clear shift.

| Subject | Kind | Bills by session | Per 1,000 | Why |
|---|---|---|---|---|
| Artificial intelligence | rise | 0, 3, 19 | 0.0, 1.2, 6.2 | Top candidate (z +3.9): AI in elections, mental health, medical malpractice, law practice, synthetic media. Samples all on topic. |
| COVID-19 and vaccines | spike | 13, 4, 3 | 5.2, 1.5, 1.0 | COVID-19 (9, 3, 1) and vaccines (12, 2, 3) both fell (z about -2.8 each; together clearer): vaccine mandates, mRNA, vaccination status. |

Wording pairs: none found.

Looked at and left out: firearms (108, 51, 61) fell after 2024's many identical "Constitutional amendment: firearms" filings, so it isn't a steady change; age verification online (6, 4, 10) is too small, and the scan's "abusive website access litigation" is about ADA website lawsuits; kratom (0, 3, 9, z +2.7) and child care (25, 21, 13, z -2.6) are just short of the bar; disabled veterans' property tax exemptions (7, 14, 27) are a handful of repeated filings.

## Mississippi (ms)

Sessions shown: 2024 (3,390 bills), 2025 (3,329), 2026 (3,631). Most of the scan's biggest movers are appropriation and local-bill wording ("FY2027", "defraying costs", town names), left out.

| Subject | Kind | Bills by session | Per 1,000 | Why |
|---|---|---|---|---|
| Artificial intelligence | rise | 4, 9, 13 | 1.2, 2.7, 3.6 | Steady rise (z about +2.7): AI in political ads, deepfakes, education, fraud. Samples all on topic. |
| Weather modification | rise | 0, 2, 8 | 0.0, 0.6, 2.2 | Candidate scan (z +2.7), steady: geoengineering and "chemtrail" bans. Samples all on topic. |
| COVID-19 and pandemic aid | spike | 29, 16, 10 | 8.6, 4.8, 2.8 | COVID-19 (z -3.1) and federal pandemic aid (ARPA, the Coronavirus State Fiscal Recovery Fund; z -3.3) fell together as the money was spent; combined, since most bills name both. |

Wording pairs: none found.

Looked at and left out: broadband (12, 10, 3, z -2.5); hemp and THC (1, 7, 5); income tax (55, 71, 62) has no steady direction.

## Montana (mt)

Sessions shown: 2023 (1,534 bills), 2025 (1,516). Two sessions, and the records have short titles only (no summaries), so only the one clear shift.

| Subject | Kind | Bills by session | Per 1,000 | Why |
|---|---|---|---|---|
| Alcohol laws | spike | 56, 16 | 36.5, 10.6 | The scan's strongest real phrase ("alcohol" 45 to 15, z -3.9): 2023 had dozens of bills revising alcohol licenses, beer and wine rules; 2025 far fewer. Samples all on topic. |

Wording pairs: none found.

Looked at and left out: artificial intelligence (0 to 6) is too few; "voter" (2 to 12), "attorney" (1 to 11) and child protective services (8 to 0) are small and mixed.

## North Carolina (nc)

Sessions shown: 2023-24 (1,958 bills), 2025-26 (2,284). Two sessions, and the records have short titles only (about 38 characters), so only the clearest shifts.

| Subject | Kind | Bills by session | Per 1,000 | Why |
|---|---|---|---|---|
| Down-zoning | rise | 0, 30 | 0.0, 13.1 | The scan's second strongest phrase (0 to 30, z +5.1): "Restore Down-Zoning Authority" bills for counties and towns, after the 2024 disaster relief act barred local down-zoning. Local bills, but a real statewide shift. |
| Medicaid | rise | 11, 32 | 5.6, 14.0 | z +2.7: provider rates, the expansion trigger, plan contracts, during 2025's Medicaid funding standoff. Samples all on topic. |

Wording pairs: none recorded. The titles of school calendar bills changed from "School Calendar Flexibility/..." (2023-24) to "SchCalFlex/..." (2025-26), a clerk's abbreviation of the same local bills (27 and 39 with both forms), not a change of subject.

Looked at and left out: school calendar flexibility (27 to 39, z about +1.3); elections (52 to 36, z -2.5) and occupancy taxes (15 to 5) are small; disaster and Hurricane Helene bills (6 to 12) are too few.

Reviewed and dropped: vaping and nicotine (0 to 8, z +2.5) is under the bar.

## North Dakota (nd)

Sessions shown: 2023 (959 bills), 2025 (1,051). Two sessions only, so only the one clear shift.

| Subject | Kind | Bills by session | Per 1,000 | Why |
|---|---|---|---|---|
| Tribal governments and schools | rise | 3, 17 | 3.1, 16.2 | The scan's top policy phrase ("tribal" 2 to 15, z +3.0): tribal schools in school bills, tribal-state compacts, tribal consultation, tribal arrest warrants, tribal land and oil taxes. Samples all on topic. |

Wording pairs: none found.

Looked at and left out: "time" (0 to 11) mixes unrelated bills (central standard time, parenting time, instructional time); "schools" (5 to 19) and tax credits (18 to 7) are small and mixed; no candidate subject reached the bar.

## Nebraska (ne)

Sessions shown: 2023-24 (1,553 bills), 2025-26 (1,366). Two sessions only, so only the clearest shift.

| Subject | Kind | Bills by session | Per 1,000 | Why |
|---|---|---|---|---|
| Medical cannabis | rise | 1, 8 | 0.6, 5.9 | The scan's "medical cannabis" (0 to 8, z +3.0): bills changing the Medical Cannabis Patient Protection and Regulation Acts that voters adopted in November 2024. Samples all on topic. |

Wording pairs: none found.

Looked at and left out: immigration (0 to 7) and batteries (0 to 6) are too few; broadband (12 to 2) and voting (18 to 4) are small; "fees" and "eliminate" are drafting.

Reviewed and dropped: "spending requests" (bills stating intent to appropriate, 125 to 44) is a kind of bill, not a subject.

## New Hampshire (nh)

Sessions shown: 2023 (904 bills), 2024 (1,300), 2025 (1,034), 2026 (1,351). The records carry titles only (summaries on 1%), and the titles have grown longer and more specific (84 characters a bill in 2023, 101 in 2026: "Relative to ..." gave way to "enabling", "requiring", "defining", "modifying"), which lifts every subject's share by about a fifth; the phrase scan's movers are that wording, not subjects. A second-year session also lists the first year's retained bills again (224 of 2026's 1,351), as in each year's own list. Scanned again on 2026-11-22 for subjects only, from the full data (the same four sessions).

| Subject | Kind | Bills by session | Per 1,000 | Why |
|---|---|---|---|---|
| Housing and zoning | rise | 17, 34, 27, 56 | 18.8, 26.2, 26.1, 41.5 | The one real subject shift (2023 to 2026 z +3.0; more than doubled, well beyond what the longer titles add): zoning alone 9, 14, 13, 37. 2026's accessory dwelling units, multi-family homes on commercial land, parking minimums, zoning boards of adjustment, the housing champion program, workforce and affordable housing. All 2023, 2024 and 2026 matches read; all on housing (2024's SB 503 is a fish and game bill that also amends a housing law). |

Wording pairs: none found.

Looked at and left out: immigration enforcement (3, 6, 9, 10) and proof of citizenship for voters are too few; artificial intelligence (0, 8, 1, 7) has no steady direction; education freedom accounts (17, 18, 11, 22) are flat; elections (42, 61, 76, 66) peaks in 2025; chartered public schools (10, 6, 6, 6) fell only after 2023; PFAS (6, 10, 1, 4) and the opioid bills (6, 5, 1, 2) are too few; energy and utilities (8.8, 7.7, 16.4, 14.8 per 1,000, z about +2) is under the bar.

## New Jersey (nj)

Sessions shown: 2018-19 (7,106 bills), 2020-21 (7,240), 2022-23 (6,721), 2024-25 (7,451), 2026-27 (7,328). Matched on the synopsis (NJ has no separate summary; synopsis length steady at about 122 characters a bill). The five earlier subjects were kept (AI's pattern now also catches "Artificial Intelligence" capitalized and deepfakes); six added.

| Subject | Kind | Bills by session | Per 1,000 | Why |
|---|---|---|---|---|
| Artificial intelligence | rise | 2, 2, 7, 39, 69 | 0.3, 0.3, 1.0, 5.2, 9.4 | Strongest rise in the scan ("intelligence" 2 to 51). Samples: AI in hiring, state agencies, deepfakes. |
| Data centers | rise | 0, 1, 1, 10, 25 | 0.0, 0.1, 0.1, 1.3, 3.4 | Steady rise from nothing; energy use and siting of data centers. |
| Warehouses | rise | 1, 6, 22, 27, 27 | 0.1, 0.8, 3.3, 3.6, 3.7 | Scan phrase "warehouse" 0 to 16: siting, air permits, planning of large warehouses (movers' "warehousemen" excluded). |
| Menstrual products | rise | 3, 9, 29, 29, 26 | 0.4, 1.2, 4.3, 3.9, 3.5 | Scan phrase "menstrual" 2 to 22: free products in schools, prisons, colleges; menstrual disorders. Flat since 2022-23 but far above 2018-19. |
| Reproductive health care | rise | 3, 2, 8, 14, 16 | 0.4, 0.3, 1.2, 1.9, 2.2 | Scan phrase "reproductive health care" 0 to 14, after 2022: access fund, insurance coverage, protection of providers. |
| E-bikes and scooters | rise | 3, 2, 4, 12, 16 | 0.4, 0.3, 0.6, 1.6, 2.2 | Kept: helmets, battery testing, rebates for electric bicycles. |
| Nuclear power | rise | 4, 1, 11, 16, 19 | 0.6, 0.1, 1.6, 2.1, 2.6 | Advanced reactors, nuclear energy program in BPU. |
| Batteries and energy storage | rise | 5, 8, 16, 23, 23 | 0.7, 1.1, 2.4, 3.1, 3.1 | Storage procurement and EV battery recycling; no "assault and battery" hits. |
| Immigration | rise | 25, 22, 22, 43, 57 | 3.5, 3.0, 3.3, 5.8, 7.8 | Kept: detainers, detention ("detention" 5 to 28), coverage for undocumented immigrants. |
| Social media | rise | 7, 8, 16, 27, 27 | 1.0, 1.1, 2.4, 3.6, 3.7 | Kept. |
| COVID-19 | spike | 0, 289, 131, 75, 44 | 0.0, 39.9, 19.5, 10.1, 6.0 | Kept: the peak in 2020-21 and the fall since. |

Wording pairs: "marijuana" (4.9, 2.5, 2.1, 2.0, 1.9 per 1,000) to "cannabis" (1.3, 5.0, 7.3, 6.8, 6.0), after the 2021 adult-use law ("medical marijuana" 19 to 0 in the scan).

Looked at and left out: cannabis as a subject (flat since 2022-23; shown as the wording pair); bail and pretrial detention (4.1, 1.8, 3.4, 4.7, 4.6: no steady direction); utility rates (3.0, 2.1, 1.3, 4.6, 4.9: fell, then rose); PFAS, IVF, phones in schools, catalytic converters (too few); elections (steady around 23 per 1,000).

## New Mexico (nm)

Sessions shown: 2024 (688 bills, 30-day session), 2025 (1,216, 60-day), 2026 (702, 30-day). The records carry only a short title (about 38 characters, no summary), so the scan has little to work with; 2024 against 2026 compares two sessions of the same kind.

| Subject | Kind | Bills by session | Per 1,000 | Why |
|---|---|---|---|---|
| Interstate licensing compacts | rise | 1, 14, 12 | 1.5, 11.5, 17.1 | The scan's top rising word ("compact" 1, 15, 12): counseling, psychology, social work, dental, PA, EMS, teacher and medical licensure compacts, reintroduced in 2026. Every match read; the State-Tribal Education Compact Schools Act is excluded. |

Wording pairs: none found.

Looked at and left out: cannabis (12, 8, 3: falling, but z about 2.4 on so few bills); medical malpractice (4, 7, 8); "rate", "county", "plate" (drafting and budget-session words, not subjects).

## Nevada (nv)

Sessions shown: 2023 (1,049 bills), 2025 (1,119). Two sessions only, so only the two clearest shifts, both from almost nothing.

| Subject | Kind | Bills by session | Per 1,000 | Why |
|---|---|---|---|---|
| Artificial intelligence | rise | 0, 9 | 0.0, 8.0 | "Artificial" 0 to 9 in the scan: AI in elections, schools, health care and insurance, taxation. "Generative" is matched only as a word start (2023's one hit was "neurodegenerative"). |
| Prior authorization | rise | 0, 8 | 0.0, 7.1 | "Prior" 0 to 9: limits on insurers' and Medicaid's prior authorization. All matches on topic. |

Wording pairs: none found.

Looked at and left out: the 2023 budget's computer hardware and software replacement appropriations (37 to 8: one-time spending, not a subject); "revises provisions governing" (233 to 91: a change in how titles are written).

## Ohio (oh)

Sessions shown: 134th GA 2021-22 (1,134 bills), 135th 2023-24 (1,064), 136th 2025-26 (1,532). The records carry only a short title (about 56 characters, no summary), so only the clearest shifts.

| Subject | Kind | Bills by session | Per 1,000 | Why |
|---|---|---|---|---|
| Artificial intelligence | rise | 0, 4, 12 | 0.0, 3.8, 7.8 | Deepfakes and synthetic media in elections, AI by insurers and state agencies, an AI study commission. All matches on topic. |
| Data centers | rise | 0, 0, 10 | 0.0, 0.0, 6.5 | New in 2025-26: limits on construction, sales tax exemptions, water reports, a study commission. |
| Property tax | rise | 15, 25, 49 | 13.2, 23.5, 32.0 | "Property tax" was the scan's top rising subject phrase (9, 16, 34): freezes, limits on increases, homestead exemptions after the 2023-24 revaluations. |
| COVID-19 | spike | 24, 1, 0 | 21.2, 0.9, 0.0 | The scan's top falling phrase: vaccine mandates and status, relief money, emergency rules, all in 2021-22. |

Wording pairs: none found.

Looked at and left out: vaccines (14, 1, 0: nearly all COVID-19 vaccine bills, already in COVID-19); veterans (30, 19, 15: falling, but a steady group of designations and benefits, not one subject); Medicaid and child care (rising, z about 2); "enact" (a drafting habit).

## Oklahoma (ok)

Sessions shown: 2023-24 (5,269 bills), 2025-26 (5,809). LegiScan titles only (about 98 characters, no summary). Many of the scan's biggest moves are shell-bill title habits ("Schools; creating the ... Act" 133 to 19, "education reform" 2 to 97) and were ignored; each subject below was read in both sessions' samples.

| Subject | Kind | Bills by session | Per 1,000 | Why |
|---|---|---|---|---|
| Property tax | rise | 43, 109 | 8.2, 18.8 | "Ad valorem" 33 to 94 in the scan: homestead exemptions, senior valuation limits, proposals to repeal the property tax. |
| Eminent domain | rise | 8, 31 | 1.5, 5.3 | Limits on condemnation, pipelines and other facilities, landowners' costs. |
| Wind energy | rise | 2, 21 | 0.4, 3.6 | "Wind energy" 2 to 19: setbacks for wind towers, decommissioning, repeal of a tax credit. |
| Immigration | rise | 3, 19 | 0.6, 3.3 | State immigration enforcement, status checks for school enrollment, Medicaid and tuition. "Alien ownership of land" (foreign ownership) and a museum's "undocumented property" left out. |
| Data centers | rise | 0, 9 | 0.0, 1.5 | Data Centers Act, decommissioning, utility service classes. The Oklahoma State Data Center (census office) is excluded. |
| Medical marijuana | spike | 98, 61 | 18.6, 10.5 | The scan's top falling subject ("marijuana; creating" 40 to 9): licensing and enforcement bills after the 2019-22 boom in licenses. |

Wording pairs: none found.

Looked at and left out: Medicaid (32 to 69: real, but generic and mostly program code titles); AI (8 to 22, z 2.3), lab-grown meat (0 to 7), phones in schools (0 to 5), foreign land ownership (8 to 12): too few or too small a change.

## Oregon (or)

Sessions shown: 2022 (263 bills, short), 2023 (2,898, long), 2024 (271, short), 2025 (3,360, long), 2026 (290, short). The short sessions are too small to compare on their own, so the scan was also run on 2023 against 2025. That comparison is dominated by a change in how the summaries are written ("directs department" 127 to 0, "directs the department" 0 to 125: the 2025 summaries keep the articles), so phrase shares say little.

| Subject | Kind | Bills by session | Per 1,000 | Why |
|---|---|---|---|---|
| COVID-19 | spike | 6, 18, 3, 2, 0 | 22.8, 6.2, 11.1, 0.6, 0.0 | The one candidate that clearly fell in both the long sessions (18 to 2, z -3.9) and the short ones (6, 3, 0): vaccine mandates, relief, emergency-era rent. |

Wording pairs: none (the summaries' change is a house style, not a change of words for one thing).

Looked at and left out: vaccines (24 to 5 in the long sessions, but most 2023 hits are COVID-19 vaccine mandates already counted); property tax (no steady direction); every rising phrase in the long-session scan was a summary-style change.

## Pennsylvania (pa)

Sessions shown: 2023-24 (3,862 bills), 2025-26 (4,184). The records changed form: 2023-24 has only the formal title ("Crimes and Offenses: in abortion, further providing for ..."), 2025-26 a short title plus the formal title as its summary (text per bill 129 to 278 characters). That lifts every subject's share in 2025-26, and the scan's phrases mostly measure it ("amending" 144 to 3,322). So each candidate was also counted on the formal titles alone (2023-24's title against 2025-26's summary), and only shifts that hold there were kept.

| Subject | Kind | Bills by session | Per 1,000 | Why |
|---|---|---|---|---|
| Artificial intelligence | rise | 2, 47 | 0.5, 11.2 | Formal titles alone: 2 to 31. AI in schools, insurers' algorithms, political ads, companion apps. |
| Data centers | rise | 1, 42 | 0.3, 10.0 | Formal titles alone: 1 to 34. Siting controls, water analysis, repeal of the data center tax break. |

Wording pairs: none (the change is in the records' form).

Looked at and left out: abortion (10 to 44, but 2025-26's formal titles add death penalty bills naming "murder of unborn child"); child care (7 to 18 on formal titles), immigration (6 to 14), skill games and sports wagering (1 to 8): too small once the format change is allowed for.

## Rhode Island (ri)

Sessions shown here: 2024 (1,418 bills), 2025 (1,489), 2026 (1,714). LegiScan titles and descriptions, steady in form (about 230 characters a bill). No candidate subject moved by |z| 2.5 or more; one subject did in the phrase scan.

| Subject | Kind | Bills by session | Per 1,000 | Why |
|---|---|---|---|---|
| Affordable housing | rise | 13, 28, 40 | 9.2, 18.8, 23.3 | "Low and moderate income housing" (4, 20, 23) and "comprehensive permit" (0, 6, 10) rose most: definitions, land banks, ADUs counted as affordable, faith-based housing, and towns' (Tiverton, Coventry) limits on comprehensive-permit projects. |

Wording pairs: none found.

Looked at and left out: vaping (0, 2, 6), short-term rentals (6, 2, 1), COVID-19 (5, 4, 1): too few; Medicaid (12, 21, 27: z 1.8); "Tiverton" (2, 16, 20: one town's local bills, partly in affordable housing).

## South Carolina (sc)

Sessions shown: 2023-24 (2,253 bills), 2025-26 (2,286). Two sessions only, so only the two clearest subjects. Many of the scan's moves are the 2024 split of DHEC ("Department of Health and Environmental Control" 30 to 0, "Department of Environmental Services" 1 to 19) and judicial-election and precinct-map bills, not subjects.

| Subject | Kind | Bills by session | Per 1,000 | Why |
|---|---|---|---|---|
| Artificial intelligence | rise | 4, 16 | 1.8, 7.0 | AI in health insurance and therapy, chatbots, AI-made child abuse images, school electives. All matches on topic. |
| Data centers | rise | 0, 8 | 0.0, 3.5 | New in 2025-26: utility costs, water use reports, a moratorium. |

Wording pairs: "health care" (13.8 to 1.3 per 1,000) to "healthcare" (3.6 to 18.8): the same things (the Health Care Market Reform Measures Study Committee became the Healthcare ... Committee) written as one word from 2025.

Looked at and left out: proof of citizenship (2 to 14: voter rolls, benefits, remittances; few bills); immigration and other candidates (|z| under 2.5).

## South Dakota (sd)

Sessions shown: 2024 (489 bills), 2025 (499), 2026 (578). A small legislature, so only the two clearest shifts.

| Subject | Kind | Bills by session | Per 1,000 | Why |
|---|---|---|---|---|
| Property tax | rise | 5, 15, 23 | 10.2, 30.1, 39.8 | Steady rise: freezes, limits on assessment growth for owner-occupied homes, flat-rate constitutional amendments, replacement funds. All matches on topic. |
| Data centers | rise | 0, 1, 9 | 0.0, 2.0, 15.6 | The scan's top rising word ("data" 0, 2, 15): utility costs, nuisances, moratoriums on hyperscale data centers, sales tax exemptions. |

Wording pairs: none found.

Looked at and left out: tax increment financing (0, 0, 11: one year only, often local); "Indian" (13, 2, 5: no steady direction); other candidates under |z| 2.5.

## Tennessee (tn)

Sessions shown: 2023-24 (3,089 bills), 2025-26 (2,819). Two sessions only, so five subjects; the three rising ones are near the edge (z about 2.6-2.7) and were kept because their samples are all on topic and the rise is steady across the bills.

| Subject | Kind | Bills by session | Per 1,000 | Why |
|---|---|---|---|---|
| Immigration | rise | 11, 25 | 3.6, 8.9 | "immigration" was among the scan's top rising words (5 to 19); enforcement, detention, schooling of children unlawfully present. |
| Artificial intelligence | rise | 9, 20 | 2.9, 7.1 | Deepfakes, AI in health care, an advisory council, data-center tariffs. |
| Sales tax on groceries | rise | 7, 19 | 2.3, 6.7 | "food and food ingredients" (5 to 17): cutting or ending the state's sales tax on food, tax holidays. "Grocery" alone also matched wine-in-grocery-stores bills, so only "grocery tax". |
| Firearms | spike | 129, 65 | 41.8, 23.1 | The scan's strongest falling subject ("firearms" 89 to 35, "handgun", "carry"): 2023-24 followed the Covenant School shooting and an August 2023 special session. |
| Third-grade retention | spike | 16, 3 | 5.2, 1.1 | "third", "ela", "proficient" fell: 2023's bills revising the third-grade reading retention law, settled by 2025. |

Wording pairs: none found.

Looked at and left out: "public charter schools" (19 to 38) is a drafting habit (mandates on LEAs now name charter schools too); data centers (2 to 7), hemp (10 to 14) and abortion (22 to 12) are too few or too flat; "freedom" and "planning" are act names.

## Texas (tx)

Sessions shown: 2021 (7,145 bills), 2023 (8,342), 2025 (9,009), each with its special sessions. Texas's records carry captions only (no summaries, about 110 characters a bill in every session), so the shares compare; patterns are written for caption wording ("marihuana", "aliens or foreign entities", "ERCOT power region").

| Subject | Kind | Bills by session | Per 1,000 | Why |
|---|---|---|---|---|
| Artificial intelligence | rise | 0, 4, 32 | 0.0, 0.5, 3.6 | "artificial", "intelligence" among the scan's top risers. |
| Diversity, equity and inclusion | rise | 1, 2, 28 | 0.1, 0.2, 3.1 | "diversity equity", "inclusion initiatives" 0-1 to 19-26. |
| Foreign adversaries | rise | 0, 8, 35 | 0.0, 1.0, 3.9 | "foreign entities" 0, 6, 22: land, groundwater, lobbying and university money from certain foreign governments and companies. Plain "foreign country" left out (medical licenses for doctors trained abroad). |
| Squatters | rise | 0, 0, 17 | 0.0, 0.0, 1.9 | "occupants" 0 to 18: removing unauthorized occupants of a dwelling. Fourteen are the same caption filed again (several authors and the special sessions). |
| Nuclear power | rise | 0, 5, 14 | 0.0, 0.6, 1.6 | Advanced reactors, a nuclear energy authority and fund; every 2025 match is about nuclear power. |
| School library books | rise | 1, 12, 12 | 0.1, 1.4, 1.3 | Library materials in public schools (selection, removal, parents' notice). |
| Education savings accounts | rise | 0, 13, 9 | 0.0, 1.6, 1.0 | Up from none; enacted in 2025. |
| Fentanyl | spike | 2, 22, 2 | 0.3, 2.6, 0.2 | Peaked in 2023 (z +4 above both ends). |
| COVID-19 | spike | 54, 24, 8 | 7.6, 2.9, 0.9 | Strongest falling candidate. |
| Power grid | spike | 73, 61, 35 | 10.2, 7.3, 3.9 | "ERCOT power region", "independent organization" fell: 2021's bills after Winter Storm Uri. |
| Disaster declarations | spike | 61, 19, 9 | 8.5, 2.3, 1.0 | "disaster" 167 to 31, "declared" 64 to 13: the pandemic and the 2021 storm; the pattern takes declared disasters only. |
| Cannabis | spike | 46, 40, 24 | 6.4, 4.8, 2.7 | Steady fall. |
| Insulin | spike | 10, 3, 0 | 1.4, 0.4, 0.0 | Price caps in 2021, then gone. |

Wording pairs: none found (captions keep "marihuana" throughout).

Looked at and left out: municipal utility districts and hotel and convention center tax bills (big moves, but local bills for single places); "parental" (11 to 59) mixes parental rights with parental leave and termination of parental rights; hemp (10, 18, 22), data centers (1, 4, 4), bail and property tax relief are flat; broadband and cybersecurity fell a little.

## Congress (us)

Sessions shown: 117th, 2021-22 (13,340 bills), 118th, 2023-24 (14,588), 119th, 2025-26 (15,355). Plenty of bills, so fifteen subjects. Summaries are short (titles and Congress.gov's summaries, about 225 characters a bill in each Congress), so the shares compare.

| Subject | Kind | Bills by session | Per 1,000 | Why |
|---|---|---|---|---|
| Artificial intelligence | rise | 28, 131, 267 | 2.1, 9.0, 17.4 | The scan's strongest rising subject ("artificial" z +11). "generative" only as a word start (not "neurodegenerative"). |
| Data centers | rise | 2, 1, 49 | 0.1, 0.1, 3.2 | Energy, water and siting of data centers, all in 2025-26. |
| Government shutdowns | rise | 12, 36, 118 | 0.9, 2.5, 7.7 | "shutdown" and "lapse" rose (5 to 65, 5 to 59): pay and services during the 2025 shutdown. |
| Overturning agency rules | rise | 42, 159, 204 | 3.1, 10.9, 13.3 | "Providing for congressional disapproval under chapter 8 of title 5" (Congressional Review Act resolutions). |
| War powers | rise | 11, 8, 36 | 0.8, 0.5, 2.3 | "within or against ... hostilities" 0 to 24: resolutions directing the removal of U.S. forces from hostilities. |
| Immigration | rise | 295, 306, 478 | 22.1, 21.0, 31.1 | Flat, then up by half in 2025-26 ("immigration", "ICE" in the scan). |
| Wildfire | rise | 50, 75, 111 | 3.7, 5.1, 7.2 | Steady rise; smoke, response, victims' tax relief. |
| Child care | rise | 42, 57, 93 | 3.1, 3.9, 6.1 | Steady rise. |
| Antisemitism | rise | 2, 21, 18 | 0.1, 1.4, 1.2 | Up after October 2023 and stayed. |
| Pharmacy benefit managers | rise | 2, 21, 17 | 0.1, 1.4, 1.1 | Up in the 118th and stayed. |
| Diversity, equity and inclusion | rise | 1, 12, 16 | 0.1, 0.8, 1.0 | Small but steady. |
| Fentanyl | spike | 41, 94, 52 | 3.1, 6.4, 3.4 | Peaked in the 118th (z +4 above both ends). |
| COVID-19 | spike | 574, 134, 42 | 43.0, 9.2, 2.7 | The scan's strongest falling subject. |
| Russia and Ukraine | spike | 181, 97, 80 | 13.6, 6.6, 5.2 | Highest with the 2022 invasion. |
| Afghanistan | spike | 62, 21, 16 | 4.6, 1.4, 1.0 | The 2021 withdrawal and evacuees. |

Wording pairs: none found.

Looked at and left out: vaccines (196, 60, 34) and federal pandemic aid mostly repeat COVID-19; telehealth (66, 44, 30), broadband, hydrogen and electric vehicles fell but less clearly (pandemic-era and 2021-22 infrastructure bills); "fraud" (53 to 193) mixes many kinds of fraud; "codify executive order" and "Trump" are about one administration, not a subject; agriculture and the farm bill peaked in 2023-24 only with the farm bill's cycle; foreign adversaries (155, 243, 189) is too broad a pattern.

## Utah (ut)

Sessions shown (full data, 2026-11-22): 2023 (871 bills), 2024 (863), 2025 (912), 2026 (939), all general sessions. Utah's records are short (titles and a one-line summary, about 125 characters a bill), so two steady rises, each just under the bar, were kept.

| Subject | Kind | Bills by session | Per 1,000 | Why |
|---|---|---|---|---|
| Artificial intelligence | rise | 0, 3, 6, 9 | 0.0, 3.5, 6.6, 9.6 | Up every year (2023 to 2026 z +2.9): AI in political ads, the 2024 Artificial Intelligence Policy Act and its office, AI in schools, law enforcement use, impersonation, companion chatbots, algorithmic pricing. All matches read; all on topic. |
| Homelessness | rise | 1, 7, 8, 11 | 1.1, 8.1, 8.8, 11.7 | Up every year (z +2.8): homeless services and their board, the state homeless campus, property lost in camp cleanups, driver licenses for unhoused people. "Shelter" left out (animal shelters). All matches read. |

Wording pairs: none. The scan's biggest movers are drafting phrases: summaries moved from "This bill modifies provisions related to" (102 to 67) to "This bill addresses" (160 to 257). That's a change in how the summaries are written, not a wording pair for one thing, so it isn't shown.

Looked at and left out: mental health (17, 9, 7, 7) fell after 2023's recodification of the human services code, which named it in many summaries; firearms (21, 13, 13, 13) fell once and stayed; abortion (6, 2, 0, 1) and data centers (0, 0, 0, 3) are too few; elections (a 2025 bump only).

## Virginia (va)

Sessions shown: 2023 (2,094 bills), 2024 (2,296), 2025 (2,381), 2026 (2,376). Virginia's records have short titles only (about 77 characters, the same in every year, 2023's legacy files included), so these match the title. Sessions alternate long (even years) and short (odd), so each rise was checked within each kind (2023 against 2025, 2024 against 2026): all rise in both.

| Subject | Kind | Bills by session | Per 1,000 | Why |
|---|---|---|---|---|
| Artificial intelligence | rise | 0, 9, 19, 22 | 0.0, 3.9, 8.0, 9.3 | The scan's top candidate; Virginia's titles also say "synthetic media" and "artificial audio or visual media". |
| Data centers | rise | 4, 13, 28, 28 | 1.9, 5.7, 11.8, 11.8 | Siting, noise, water, tax exemptions, cost allocation. |
| Electric utilities | rise | 25, 28, 55, 84 | 11.9, 12.2, 23.1, 35.4 | "electric utilities" and "energy" among the top risers: rates, integrated resource plans, high-demand customers, the renewable standard. |
| Zoning | rise | 8, 18, 20, 30 | 3.8, 7.8, 8.4, 12.6 | Housing production, accessory dwelling units, small lots. |
| Solar power | rise | 7, 13, 13, 31 | 3.3, 5.7, 5.5, 13.0 | Shared solar, local siting, portable "balcony" solar in 2026. Weakest of the five (most of the rise is 2026). |
| Vaccines | spike | 11, 3, 1, 2 | 5.3, 1.3, 0.4, 0.8 | Fell within each kind of session (2023 to 2025 z -3.1). |
| COVID-19 | spike | 9, 0, 1, 0 | 4.3, 0.0, 0.4, 0.0 | Gone after 2023. |

Wording pairs: none. ("public institutions of higher educational" giving way to "higher education" is a drafting change.)

Looked at and left out: Medicaid (1, 10, 10, 15): 2023's titles say "medical assistance" more, so the rise may be wording; "\bwage" matched pari-mutuel "wagering"; minimum wage, immigration (2, 3, 10, 8) and skill games are flat or too few; cannabis (23, 13, 11, 14) fell only between the odd years; "delayed effective date" and "protection of employees" are drafting phrases.

## Vermont (vt)

Sessions shown: 2023-24 (1,202 bills), 2025-26 (1,286). Two sessions of a small legislature, so one subject.

| Subject | Kind | Bills by session | Per 1,000 | Why |
|---|---|---|---|---|
| Artificial intelligence | rise | 4, 20 | 3.3, 15.6 | The scan's top rising words ("artificial" 2 to 16). Developers' liability, chatbots, AI in health care decisions, automated decision systems, AI data centers. Samples all on topic. |

Wording pairs: none found.

Looked at and left out: immigration (4 to 11) and flooding (9 to 15) rose but too little to tell from chance (z about 2); "resilience" (13 to 4) is grant-program names; "flood response" (0 to 8) is a few bills' wording.

## Washington (wa)

Sessions shown: 2021-22 (2,153 bills), 2023-24 (2,851), 2025-26 (3,138). The records carry only Washington's short titles (about 27 characters: "AI companion chatbots", "LTSS trust exemptions"), so the patterns are written for them and only subjects a short title names clearly are used.

| Subject | Kind | Bills by session | Per 1,000 | Why |
|---|---|---|---|---|
| Artificial intelligence | rise | 1, 8, 17 | 0.5, 2.8, 5.4 | "ai" the scan's top riser (0, 5, 16); synthetic media, algorithmic discrimination, chatbots. |
| Wildfire | rise | 2, 6, 16 | 0.9, 2.1, 5.1 | "wildfire" 0, 2, 14: utility wildfire mitigation and costs, wildfire risk. |
| COVID-19 | spike | 40, 3, 0 | 18.6, 1.1, 0.0 | The scan's strongest faller. |
| Vaccines | spike | 16, 9, 1 | 7.4, 3.2, 0.3 | Mostly COVID-era vaccine bills, falling steadily. |
| Long-term care | spike | 25, 13, 8 | 11.6, 4.6, 2.5 | "long-term care" 21, 7, 3: the WA Cares (long-term services and supports) trust's delay, opt-outs and repeal bills in 2021-22, plus care facilities. |
| Unemployment insurance | spike | 17, 6, 6 | 7.9, 2.1, 1.9 | The pandemic's claims and overpayments. |

Wording pairs: none found.

Looked at and left out: child care (15, 24, 37) rose but not clearly enough (z about 2); elections (47, 40, 33) fell but is a broad subject with no single reason; accessory dwelling units (7, 3, 0) and telehealth (5, 5, 0) are too few; "less restrictive alternative" and "health carrier" are a few bills' wording.

## Wisconsin (wi)

Sessions shown: 2023-24 (2,382 bills), 2025-26 (2,456). Two sessions only, so the clearest five. The records carry the relating clause only (about 100 characters), the same in both sessions.

| Subject | Kind | Bills by session | Per 1,000 | Why |
|---|---|---|---|---|
| Data centers | rise | 2, 12 | 0.8, 4.9 | "data" among the scan's top risers (13 to 38): moratoriums, tax exemptions, large energy customers. |
| Nuclear power | rise | 0, 11 | 0.0, 4.5 | "nuclear" 0 to 11: siting study, a nuclear power summit, fusion tax exemptions. |
| Cryptocurrency | rise | 0, 9 | 0.0, 3.7 | Virtual currency kiosks, digital asset regulation and staking. |
| Hemp and THC products | rise | 0, 8 | 0.0, 3.3 | Regulating hemp-derived cannabinoid products. |
| Libraries | spike | 16, 0 | 6.7, 0.0 | "library" 10 to 0: 2023-24's bills on library materials, protection of library employees from prosecution, school librarians. |

Wording pairs: none. (The scan's "worker's compensation" and "operator's license" falling to 0 is a change of apostrophe character in 2025-26's records, not of wording.)

Looked at and left out: artificial intelligence (6 to 14, z about 2); reading and literacy (14 to 6); firearms (37 to 18) and evictions (21 to 8) fell but less clearly; "Wisconsin Shares", "village", "audiovisual" are a few bills' wording.

## West Virginia (wv)

Sessions shown here: 2024 (2,615 bills), 2025 (2,515), 2026 (2,841). Most of the scan's movers are appropriation and rule-making wording ("supplemental appropriation", "authorizing the board ... to promulgate") and the 2024 split of the Department of Health and Human Resources into three departments (its name falling, "Department of Human Services" rising), so only two subjects.

| Subject | Kind | Bills by session | Per 1,000 | Why |
|---|---|---|---|---|
| Data centers | rise | 0, 7, 14 | 0.0, 2.8, 4.9 | The top candidate (z +3.6): incentives for data centers, their taxes and water use, and the certified microgrid program created for them (2025's Power Generation and Consumption Act). |
| Immigration | rise | 5, 9, 18 | 1.9, 3.6, 6.3 | Steady rise (z about 2.5): cooperation with federal enforcement, driver's licenses, school enrollment. "undocumented" alone matched parking and museum property, so only "undocumented immigrant" and the like. |

Wording pairs: none. (The department names changed because the department was split, not reworded.)

Looked at and left out: artificial intelligence is flat (6, 6, 7); gender identity (15, 13, 7) and COVID-19 (7, 4, 2) fell too little; "rural" (2, 4, 29) is mostly 2026's federal Rural Health Transformation Program appropriations (7 bills) and unrelated programs.

## Wyoming (wy)

Sessions shown (full data, 2026-11-22): 2023 (485 bills, general session), 2024 (358, budget session), 2025 (546, general), 2026 (325, budget). Skipped: no subjects.

Even-year budget sessions take only bills two-thirds of a house votes to introduce, so each kind was compared with its own (2023 with 2025, 2024 with 2026). Nothing rises or falls in both: elections (39, 13, 49, 31 bills; 80, 36, 90, 95 per 1,000) rose only between the budget sessions (z +3.1) and is flat between the general ones; water (7, 7, 14, 14: water rights, the omnibus water bills, state engineer studies) rises in both but under the bar (z +1.3 and +1.8); "federal" (21, 19, 21, 4) fell only in 2026; property tax (23, 22, 26, 20) is flat; vaccines (2, 6, 2, 0), gender identity (2, 8, 3, 1) and COVID-19 (1, 4, 1, 0) peaked in 2024 on a few bills. The phrase scan's movers were drafting phrases (general sessions: "making conforming amendments" 76 to 151, "specifying applicability"; budget sessions: "providing rulemaking authority" 16 to 2). Water is the one to watch when 2027 is in.

Wording pairs: none found.

