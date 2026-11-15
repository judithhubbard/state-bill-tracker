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
