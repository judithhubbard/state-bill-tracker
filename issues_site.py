#!/usr/bin/env python3
"""The national issue pages (/issues/ and /issues/<id>/), from each built state's data/issues_<session>.json
(build_data.py's write_issues(): each session's bills that issues.py matches). Run by build_site.sh after the states are
built, so a change here rebuilds no state; it also writes issues/summary.json (each issue's counts by year and state, and
the states with a session each year), which the front page's map reads.

Counts are by calendar year (last year, this year, and next year once a state lists prefiled bills): a bill counts in
every year it was alive, from the year it was introduced (its session's first year at the earliest, so a bill prefiled
in December counts in its session's year) through the year of its last action (the owner found New York's 2026 PFAS
view showing 4 of 24 bills when only the year introduced counted: two-year legislatures file most bills in year one);
laws count in the year they became law. Each issue has a page per year (index.html for this year,
<year>.html for the others) with a tile map shaded by the bills alive that year and the number that became law, a table by state
(under "Show as a table") and every bill, by state, linked to the bill on its state's page. States whose data has titles
only are marked as undercounted.

Usage: python3 issues_site.py SITE_DIR
"""
import html, json, os, re, sys

import issues
import site_meta

# States whose legislatures publish titles only (no summaries or "What it does"): matched on fewer words.
TITLES_ONLY = {"ak", "ar", "ma", "me", "ms", "mt", "nd", "ne", "nh", "ok", "vt"}
STAGES = ["In committee", "On the floor", "Passed one house", "Passed both houses", "On the governor’s desk",
          "Became law", "Vetoed"]
DESC = {
    "datacenters": "Bills about data centers and other very large electricity users: siting, power and water use, rates, tax breaks.",
    "pfas": "Bills about PFAS, the “forever chemicals”: bans in products, drinking water limits, firefighting foam, cleanup, and sewage sludge spread on farmland.",
    "ai": "Bills about artificial intelligence: deepfakes, chatbots, AI in hiring, insurance and health care, and government use.",
    "kidsonline": "Bills about children online: social media rules for minors, age checks, app stores, design codes.",
    "phones": "Bills about students’ phones and other devices in schools: bans, policies, phone-free days.",
    "housing": "Bills about building more homes: zoning, accessory dwelling units, lot sizes, parking rules, housing plans.",
    "minwage": "Bills that set or change a minimum wage: the state rate, tipped and subminimum wages, local wages.",
    "repair": "Bills giving owners and independent shops the parts, tools and manuals to fix what they own.",
    "betting": "Bills about sports betting, online casinos, fantasy sports, sweepstakes games and prediction markets.",
    "drugcosts": "Bills about what prescription drugs cost: insulin caps, pharmacy benefit managers, affordability boards, 340B.",
    "abortion": "Bills about abortion: bans and limits, access and protections, abortion pills, and amendments for the voters.",
    "firearms": "Bills about guns: carry permits, background checks and sales, red flag orders, ghost guns, guns in schools.",
    "vouchers": "Bills about public money for private schooling: vouchers, education savings accounts, tax-credit scholarships.",
    "voting": "Bills about how people vote and how elections are run: voter ID, mail voting, registration, counting and audits, and how presidential electors are chosen.",
    "immigration": "Bills about immigration: working with federal enforcement, sanctuary policies, status checks, benefits, licenses and tuition.",
    "tenants": "Bills about renting a home: rent limits, evictions, leases, security deposits, fees and tenants’ rights.",
    "proptax": "Bills about property tax relief for homeowners and residents: homestead exemptions, assessment caps, freezes, credits.",
    "transgender": "Bills about transgender people: sports, health care for minors, birth certificates and IDs, bathrooms, schools, protections.",
    "dei": "Bills about diversity, equity and inclusion programs: offices, training, statements and hiring, bans and protections.",
    "cannabis": "Bills about cannabis: legal sales, medical cannabis, hemp-derived THC such as delta-8, and clearing old records.",
    "privacy": "Bills about consumer data privacy: what businesses may collect and sell, data brokers, biometric, health and location data.",
    "campaignfinance": "Bills about money in politics: contribution limits, spending and disclosure, PACs, public financing of campaigns.",
    "redistricting": "Bills about drawing legislative and congressional districts: commissions, maps, the rules for drawing them.",
    "paidleave": "Bills about paid leave: family and medical leave programs, paid sick and safe time, parental leave.",
    "childcare": "Bills about child care: help paying for it, licensing, the child care workforce and tax credits.",
    "ivf": "Bills about IVF and fertility: insurance coverage, embryos, surrogacy, donors and fertility fraud.",
    "fluoride": "Bills about adding fluoride to public drinking water: bans, local choice, and the levels allowed.",
    "nuclear": "Bills about nuclear power: new reactors and small modular reactors, lifting moratoriums, fusion, plants and their costs.",
    "wildfire": "Bills about wildfires: prevention and prescribed burns, utilities’ wildfire plans and liability, insurance, firefighting.",
    "noncompete": "Bills about noncompete agreements and other limits on workers taking a new job, for all workers or for doctors and others.",
    "strentals": "Bills about short-term rentals such as Airbnb: local rules, registration, taxes and booking platforms.",
    "water": "Bills about who gets water: water rights, groundwater, drought, conservation and interstate river compacts.",
    "psychedelics": "Bills about psilocybin, MDMA, ibogaine and other psychedelics: therapy programs, research, decriminalization.",
    "cryptoatm": "Bills about crypto ATMs (virtual currency kiosks): licensing, transaction limits and fraud protections.",
    "medicaidwork": "Bills about work or community engagement requirements for people on Medicaid.",
    "dst": "Bills about daylight saving time: permanent standard or daylight time, or leaving the yearly clock change.",
    "books": "Bills about challenges to and removal of books and materials in schools and libraries, and librarians’ liability.",
    "medicaldebt": "Bills about medical debt: credit reports, collection limits, interest, relief programs and hospital financial assistance.",
    "police": "Bills about police accountability: use of force, body cameras, misconduct records, decertification, oversight.",
    "deathpenalty": "Bills about the death penalty: abolishing or restoring it, which crimes it covers, and how executions are carried out.",
    "vaccines": "Bills about vaccines and public health powers: requirements and exemptions, access, mRNA, and limits on emergency health orders.",
    "unions": "Bills about unions and collective bargaining: bargaining rights, union dues, right-to-work, public employees and strikes.",
    "initiatives": "Bills about citizens’ initiatives and referendums: signatures, vote thresholds, petition circulators and ballot titles.",
    "rcv": "Bills about ranked-choice (instant-runoff) voting and approval voting: allowing, adopting or banning them.",
    "utilityrates": "Bills about electric and gas bills: rates and rate cases, shutoffs, energy assistance, and who pays for grid upgrades.",
    "climate": "Bills about climate and clean energy: greenhouse gas limits, clean energy standards, carbon pricing, gas hookups, electric vehicles.",
    "esg": "Bills on politics in state investing and contracts: whether state funds may weigh environmental and social factors (\u201cESG\u201d), and boycotts of energy companies, gun makers or Israel.",
    "religion": "Bills about religion in public schools: Ten Commandments displays, chaplains, prayer, Bible courses and released time.",
    "childlabor": "Bills about child labor: work permits, hours and hazardous jobs for minors, penalties, and child performers’ and influencers’ earnings.",
    "protest": "Bills about protests and assembly: riot and unlawful assembly crimes, blocking roads, critical infrastructure, picketing homes, masks.",
    "kratom": "Bills about kratom and 7-OH (7-hydroxymitragynine): sales and age limits, labeling, bans and scheduling, consumer protection acts.",
    "coverage": "Bills about who has health insurance: single-payer and universal coverage, public options, Medicaid expansion and eligibility, state marketplaces and the Affordable Care Act's protections.",
    "assault": "Bills about sexual assault and domestic violence: rape kits, time limits for abuse cases, protective orders, stalking, sex trafficking, child sexual abuse and survivors' rights.",
    "homeless": "Bills about homelessness: bans on camping and sleeping in public, encampments, housing first, shelters and services.",
    "incometax": "Bills that cut personal income tax rates: lower rates, a flat tax, triggers, phasing out or ending the income tax.",
    "homeinsurance": "Bills about homeowners insurance: rates and cancellations, state insurers of last resort (Citizens, FAIR plans), fortified roofs and flood insurance.",
    "bail": "Bills about bail and pretrial release: cash bail, pretrial detention, release conditions, bail bond agents.",
    "overdose": "Bills about drug crimes and overdoses: fentanyl penalties, drug-induced homicide, naloxone, test strips, overdose prevention sites.",
    "contraception": "Bills about contraception: a right to birth control, insurance coverage, pharmacists prescribing it, emergency contraception.",
    "mentalhealth": "Bills about mental health crises and care: the 988 line, crisis teams, involuntary commitment, mental health in schools, insurance parity.",
    "foodadditives": "Bills about food dyes and additives: bans and warning labels, additives in school food, ultra-processed food.",
    "schoolmeals": "Bills about school meals: free meals for all students, school breakfast, lunch debt and lunch shaming.",
    "plastics": "Bills about plastics and packaging: bag and foam bans, producer responsibility for packaging, microplastics, bottle deposits, recycling labels.",
    "heat": "Bills that protect workers from heat: heat illness standards, water, rest and shade, and limits on local rules.",
    "samesex": "Bills about same-sex marriage: protecting marriage equality in state law, repealing old bans, or defining marriage as between a man and a woman.",
}

def tokens():
    """The front page's color tokens (home.html's :root blocks, light and dark), so both kinds of page share one palette:
    blue and red for party only, teal for amounts of bills, green for "became law", gold for the visitor's own."""
    src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "home.html"), encoding="utf-8").read()
    m = re.search(r"<style>\s*(:root \{.*?)\n\* \{ box-sizing", src, re.S)
    if not m:
        raise SystemExit("issues: home.html's color tokens weren't found")
    return m.group(1)


# The same components as the front page (home.html): the year buttons, the tile map, the legend, the stage labels and the
# party badges.
CSS_PARTS = """
* { box-sizing: border-box; }
body { margin: 0; background: var(--paper); color: var(--ink); font: 16px/1.5 var(--body); padding: 32px 16px 64px; }
main { max-width: 1080px; margin: 0 auto; }
a { color: var(--navy); }
a:focus-visible, button:focus-visible, input:focus-visible, select:focus-visible, summary:focus-visible { outline: 3px solid var(--hover); outline-offset: 2px; }
.crumbs { font-size: 14px; margin: 0 0 16px; }
h1 { font: 800 clamp(30px, 7vw, 42px)/1.08 var(--display); font-stretch: 85%; margin: 0 0 10px; }
h2 { font: 700 15px/1.2 var(--display); letter-spacing: .06em; text-transform: uppercase; color: var(--ink-2); margin: 32px 0 12px; }
h3 { font: 700 19px/1.2 var(--display); margin: 24px 0 8px; color: var(--navy); }
p.lede { color: var(--ink-2); margin: 0 0 20px; font-size: 17px; max-width: 760px; }
.note { color: var(--ink-2); font-size: 14px; }
.note abbr { text-decoration: none; cursor: help; }
/* The issues index: equal cards, each with its name and a two-line count (bills and states; laws in green). */
.cards { list-style: none; margin: 0; padding: 0; display: grid; gap: 10px; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); grid-auto-rows: 1fr; }
.cards li { display: flex; }
.cards a { display: flex; flex-direction: column; gap: 8px; flex: 1 1 auto; background: var(--sheet); border: 1px solid var(--rule); border-radius: 8px;
  padding: 12px 14px; color: var(--ink); text-decoration: none; }
.cards a:hover, .cards a:focus-visible { border-color: var(--navy); }
.cards b { display: block; font: 700 18px/1.2 var(--display); color: var(--navy); }
.cards .nums { margin-top: auto; display: flex; flex-direction: column; font-size: 14px; color: var(--ink-2); line-height: 1.4; font-variant-numeric: tabular-nums; }
.cards .nums .l { color: var(--lawn); font-weight: 600; }
.tablewrap { overflow-x: auto; }
table { width: 100%; border-collapse: collapse; background: var(--sheet); border: 1px solid var(--rule); border-radius: 8px; font-size: 15px; }
th, td { text-align: left; padding: 7px 10px; border-bottom: 1px solid var(--rule); }
th { font-weight: 600; color: var(--ink-2); font-size: 13px; }
td.n, th.n { text-align: right; font-variant-numeric: tabular-nums; }
td.sess { white-space: nowrap; }
tbody tr:last-child td { border-bottom: 0; }
.tools { display: flex; flex-wrap: wrap; gap: 8px; margin: 0 0 12px; align-items: center; }
.tools input { font: inherit; padding: 6px 10px; border: 1px solid var(--rule); border-radius: 8px; background: var(--sheet); color: var(--ink);
  min-width: 0; flex: 1 1 180px; }
.tools select { font: inherit; font-size: 15px; padding: 6px 10px; border: 1px solid var(--rule); border-radius: 8px; background: var(--sheet); color: var(--ink); max-width: 100%; }
.tools button.info { font: inherit; border: 0; background: none; color: var(--ink-2); padding: 2px 4px; font-size: 17px; line-height: 1; border-radius: 6px; margin-left: -4px; cursor: pointer; }
.tools button.info[aria-expanded="true"] { color: var(--navy); }
ul.bills { list-style: none; margin: 0; padding: 0; background: var(--sheet); border: 1px solid var(--rule); border-radius: 8px; }
ul.bills li { padding: 8px 12px; border-bottom: 1px solid var(--rule); display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 2px 12px; }
ul.bills li:last-child { border-bottom: 0; }
ul.bills a { font-weight: 600; text-decoration: none; }
ul.bills a:hover { text-decoration: underline; }
.t { grid-column: 1 / -1; overflow-wrap: anywhere; }
.why { grid-column: 1 / -1; color: var(--ink-2); font-size: 14px; overflow-wrap: anywhere; }
/* Where each bill is, as on the front page: grey in committee, blue moving, amber passed both houses or with the
   governor, green law, red-brown vetoed. Before it, the sponsors' party: D, R or Both (none for committee bills). */
.stg { display: inline-block; font: 600 12px/1.5 var(--body); padding: 0 7px; border-radius: 999px; white-space: nowrap;
  background: var(--st-0); color: var(--st-0-ink); }
.stg.s1, .stg.s2 { background: var(--st-1); color: var(--st-1-ink); }
.stg.s3, .stg.s4 { background: var(--st-3); color: var(--st-3-ink); }
.stg.s5 { background: var(--st-5); color: var(--st-5-ink); }
.stg.s6 { background: var(--st-6); color: var(--st-6-ink); }
.tags { display: inline-flex; gap: 4px; align-items: center; align-self: start; justify-self: end; }
.pty { display: inline-block; font: 700 11px/1.6 var(--body); padding: 0 5px; border-radius: 4px; white-space: nowrap; }
.pty.D { background: var(--ctl-d1); color: var(--ctl-d1-ink); }
.pty.R { background: var(--ctl-r1); color: var(--ctl-r1-ink); }
.pty.B { background: var(--tile-off); color: var(--tile-off-ink); }
.hidden, [hidden] { display: none !important; }
.vh { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; }
/* The year buttons (links here), as on the front page. */
.when { display: inline-flex; border: 1px solid var(--rule); border-radius: 8px; overflow: hidden; margin: 0 0 16px; font-size: 14px; max-width: 100%; }
.when a { color: var(--ink-2); background: var(--sheet); padding: 6px 12px; text-decoration: none; }
.when a + a { border-left: 1px solid var(--rule); }
.when a[aria-current="page"] { background: var(--navy); color: var(--sheet); font-weight: 600; }
.when a:hover { color: var(--ink); }
.when a:focus-visible { outline: 3px solid var(--hover); outline-offset: -3px; }
/* The map and, beside it (below it on a phone), the counts, the legend and the notes. */
.mapwrap { display: grid; gap: 12px 24px; margin: 0 0 16px; }
.mapcol { min-width: 0; }
.mapcol .tiles { margin-bottom: 10px; }
/* The panel beside the map (below it on narrow screens), as on the front page: the counts and notes, or the bills of the
   state pointed at or clicked (pinned). It keeps the map column's height (contain: size), and its list scrolls, so
   pointing at states moves nothing. */
@media (min-width: 900px) {
  .mapwrap { grid-template-columns: minmax(0, 600px) minmax(300px, 1fr); align-items: stretch; }
  .panel { contain: size; }
}
@media (max-width: 899.98px) { .panel { height: 360px; } }
.panel { background: var(--sheet); border: 1px solid var(--rule); border-radius: 8px; padding: 12px 12px 4px; min-width: 0;
  display: flex; flex-direction: column; overflow: hidden; }
.panel > div { display: flex; flex-direction: column; flex: 1 1 auto; min-height: 0; }
#pdefault { overflow-y: auto; }
.panel p { margin: 0 0 10px; font-size: 14px; color: var(--ink-2); }
.panel #lede { font-size: 17px; color: var(--ink); margin-bottom: 12px; }
.panel h3 { font: 700 18px/1.2 var(--display); color: var(--navy); margin: 0 0 4px; }
.panel ul { list-style: none; margin: 0 -12px; padding: 0; border-top: 1px solid var(--rule); overflow-y: auto; flex: 1 1 auto; min-height: 0; }
.panel li { position: relative; }
.panel li a { display: grid; grid-template-columns: auto minmax(0, 1fr); gap: 1px 8px; align-items: baseline; padding: 6px 44px 6px 12px;
  border-bottom: 1px solid var(--rule); color: var(--ink); text-decoration: none; font-size: 14px; }
.panel li:last-child a { border-bottom: 0; }
.panel li a:hover, .panel li a:focus-visible { background: var(--paper); }
.panel li a:focus-visible { outline: 3px solid var(--hover); outline-offset: -3px; }
.panel li b { font: 600 14px/1.3 var(--body); color: var(--navy); white-space: nowrap; }
.panel .tt { grid-row: 2; grid-column: 1 / -1; display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden; }
.panel .tt .why { color: var(--ink-2); }
.panel .tags { grid-row: 1; grid-column: 2; }
.star { position: absolute; right: 6px; top: 50%; margin-top: -16px; width: 32px; height: 32px; border: 0; background: none; cursor: pointer;
  font-size: 19px; line-height: 1; color: var(--ink-2); border-radius: 6px; padding: 0; }
.star[aria-pressed="true"] { color: var(--law-mark); }
.star:hover { background: var(--paper); }
.tiles a.sel { outline: 3px solid var(--ink); outline-offset: 1px; }
@media (hover: hover) { .panel .tap { display: none; } }
@media (hover: none) { .panel .hov { display: none; } }
.tiles { display: grid; grid-template-columns: repeat(11, 1fr); gap: 4px; margin: 0; }
.tiles > * { position: relative; }
.tiles a, .tiles span.off { aspect-ratio: 1; display: flex; flex-direction: column; align-items: center; justify-content: flex-start; padding-top: 17%;
  border-radius: 6px; font: 700 clamp(10px, 2.6vw, 15px)/1 var(--display); text-decoration: none; }
.tiles span.off { background: transparent; color: var(--ink); border: 1px dashed var(--rule); }
.tiles span.wait { border: 0; box-shadow: inset 0 0 0 1px var(--rule); color: var(--ink-2); }
.tiles span.nodata { border: 0; color: var(--ink-2); background: repeating-linear-gradient(135deg, transparent 0 4px, var(--rule) 4px 5.5px);
  box-shadow: inset 0 0 0 1px var(--rule); }
.tiles a:hover, .tiles a:focus-visible { outline: 3px solid var(--hover); outline-offset: 1px; }
.tiles a.h0 { background: var(--tile-off); color: var(--ink); }
.tiles a.h1 { background: var(--heat-1); color: var(--heat-ink-1); }
.tiles a.h2 { background: var(--heat-2); color: var(--heat-ink-2); }
.tiles a.h3 { background: var(--heat-3); color: var(--heat-ink-3); }
/* The number of bills on the issue that became law: a green badge pinned to the tile's bottom (a dot on a phone). */
.lawn { display: inline-flex; align-items: center; justify-content: center; min-width: 1.6em; height: 1.6em; padding: 0 .3em;
  border-radius: 999px; background: var(--lawn); color: var(--lawn-ink); font: 700 clamp(9px, 2vw, 12px)/1 var(--body); }
.tiles .lawn { position: absolute; left: 50%; bottom: 7%; transform: translateX(-50%); box-shadow: 0 0 0 1.5px var(--sheet); }
@media (max-width: 479.98px) {
  .tiles .lawn { min-width: 0; width: 7px; height: 7px; padding: 0; font-size: 0; bottom: 12%; box-shadow: 0 0 0 1px var(--sheet); }
}
/* Sponsors' party, as on the front page: a thin bar along each tile's bottom (Democratic, both, Republican, none), the
   law badge just above it; in the panel a bigger bar whose parts set the "Sponsor's party" menu. */
.tiles a, .tiles span.off { padding-top: 13%; }
.tiles .pbar { position: absolute; left: 7px; right: 7px; bottom: 3px; height: 4px; display: flex; gap: 1px; border-radius: 2px;
  overflow: hidden; background: var(--sheet); box-shadow: 0 0 0 1px var(--sheet); pointer-events: none; }
.pbar i { min-width: 1px; flex: 0 1 0; }
.pD { background: var(--pty-d); } .pB { background: var(--pty-b); } .pR { background: var(--pty-r); } .pN { background: var(--pty-n); }
.tiles > :has(.pbar) .lawn { bottom: 9px; height: 1.45em; font-size: clamp(9px, 1.8vw, 11px); }
@media (max-width: 479.98px) {
  .tiles .pbar { left: 4px; right: 4px; bottom: 2px; height: 3px; box-shadow: none; }
  .tiles > :has(.pbar) .lawn { bottom: 6px; left: auto; right: 3px; transform: none; height: 6px; min-width: 0; width: 6px; font-size: 0; }
}
.legend .pbs { display: inline-flex; width: 24px; height: 5px; gap: 1px; border-radius: 2px; overflow: hidden; }
.legend .pbs i { flex: 1 1 0; }
.pbig { display: flex; height: 18px; gap: 2px; border-radius: 5px; overflow: hidden; margin: 2px 0 6px; flex: 0 0 auto; }
.pbig button { border: 0; padding: 0; min-width: 6px; flex: 0 1 0; cursor: pointer; }
.pbig.f button:not([aria-pressed="true"]), .pkey.f button:not([aria-pressed="true"]) i { opacity: .3; }
.panel .pkey { display: flex; flex-wrap: wrap; gap: 2px 12px; font-size: 13px; color: var(--ink-2); margin: 0 0 8px; }
.pkey button { font: inherit; color: inherit; background: none; border: 0; padding: 0; cursor: pointer; display: inline-flex; align-items: center;
  gap: 5px; font-variant-numeric: tabular-nums; border-radius: 3px; }
.pkey button i { display: inline-block; width: 10px; height: 10px; border-radius: 2px; }
.pkey button:hover { color: var(--navy); text-decoration: underline; }
.pkey button[aria-pressed="true"] { color: var(--ink); font-weight: 700; }
.legend { color: var(--ink-2); font-size: 14px; margin: 0 0 12px; display: flex; gap: 6px 16px; flex-wrap: wrap; align-items: center; }
.legend .key { display: inline-flex; align-items: center; gap: 6px; }
.legend .sq { display: inline-block; width: 12px; height: 12px; border-radius: 3px; }
.legend .sq.h0 { background: var(--tile-off); } .legend .sq.h1 { background: var(--heat-1); }
.legend .sq.h2 { background: var(--heat-2); } .legend .sq.h3 { background: var(--heat-3); }
.legend .sq.wait { background: transparent; box-shadow: inset 0 0 0 1px var(--rule); }
.legend .sq.nodata { background: repeating-linear-gradient(135deg, transparent 0 4px, var(--rule) 4px 5.5px); box-shadow: inset 0 0 0 1px var(--rule); }
.legend .sq.off { background: transparent; border: 1px dashed var(--rule); }
/* "Map | Chart", as on the front page: the chart lies over the hidden map (same size, scrolls inside), one row per
   state with bills, most first, its bar split by sponsors' party; Congress below a rule, on the states' scale. */
.views { display: flex; flex-wrap: wrap; gap: 8px 10px; margin: 0 0 16px; }
.views .when { margin: 0; }
.when button { font: inherit; border: 0; background: var(--sheet); color: var(--ink-2); padding: 6px 12px; cursor: pointer; }
.when button[aria-pressed="true"] { background: var(--navy); color: var(--sheet); font-weight: 600; }
.when button:focus-visible { outline: 3px solid var(--hover); outline-offset: -3px; }
.mapbox { position: relative; margin: 0 0 10px; }
.mapbox.charted .tiles { visibility: hidden; }
.chart { display: none; }
.mapbox.charted .chart { display: flex; flex-direction: column; position: absolute; inset: 0; overflow-y: auto; overscroll-behavior: contain;
  background: var(--sheet); border: 1px solid var(--rule); border-radius: 8px; padding: 6px 0; }
.crow { display: grid; grid-template-columns: 8.6em minmax(0, 1fr); align-items: center; gap: 8px; width: 100%; flex: 0 0 auto; min-height: 22px;
  font: 13.5px/1.2 var(--body); color: var(--ink); background: none; border: 0; padding: 2px 10px; cursor: pointer; text-align: left; }
.crow:hover { background: var(--paper); }
.crow:focus-visible { outline: 3px solid var(--hover); outline-offset: -3px; }
.crow.sel { background: var(--paper); box-shadow: inset 3px 0 0 var(--ink); font-weight: 700; }
.crow .cn { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.crow .ab { display: none; }
.crow .ct { display: flex; align-items: center; gap: 6px; min-width: 0; }
.cbar { display: flex; gap: 1px; height: 12px; border-radius: 3px; overflow: hidden; flex: 0 0 auto; min-width: 2px; }
.cbar i { flex: 0 1 0; min-width: 1px; }
.cbar.cut { border-radius: 3px 0 0 3px; -webkit-mask-image: linear-gradient(90deg, #000 85%, transparent); mask-image: linear-gradient(90deg, #000 85%, transparent); }
.crow .cv { font-variant-numeric: tabular-nums; color: var(--ink-2); font-size: 12.5px; }
.crow .lawn { font-size: 11px; height: 1.45em; }
.chart .cfed { border-top: 1px solid var(--rule); margin-top: 6px; padding-top: 4px; }
.chart .cnote { margin: 4px 10px 0; font-size: 12.5px; color: var(--ink-2); }
@media (max-width: 479.98px) {
  .crow { grid-template-columns: 2.4em minmax(0, 1fr); padding: 2px 8px; gap: 6px; }
  .crow .full { display: none; }
  .crow .ab { display: inline; }
}
#legend { display: grid; }
#legend .kset { grid-area: 1 / 1; display: flex; gap: 6px 16px; flex-wrap: wrap; align-items: center; }
#legend .ck, #legend.charted .mk { visibility: hidden; }
#legend.charted .ck { visibility: visible; }
.legend .ck i { display: inline-block; width: 12px; height: 12px; border-radius: 3px; }
details.table { margin: 0 0 8px; }
details.table summary { cursor: pointer; color: var(--navy); font-weight: 600; font-size: 15px; margin: 0 0 8px; }
section.fed h3 small { font: 400 14px/1.3 var(--body); color: var(--ink-2); }
footer { margin-top: 32px; color: var(--ink-2); font-size: 14px; }
"""


def css():
    return tokens() + CSS_PARTS


HEAD = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{desc}">
{meta}<link rel="icon" type="image/png" sizes="32x32" href="/favicon-32.png">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wdth,wght@75..100,500..800&family=Public+Sans:wght@400;600;700&display=swap">
<style>{css}</style>
</head>
<body>
<main>
"""

e = html.escape


# The issue pages' and the front page panel's "Sponsor's party" menu (build_data.py's sponsor_class()).
PARTY_NOTE = ("Sponsor&rsquo;s party is the party of a bill&rsquo;s main sponsors, not what the bill does: bills on the "
              "same issue often pull opposite ways, and party is a rough guide to which. &ldquo;Both parties&rdquo;: main "
              "sponsors from both, or at least one in five of its sponsors and co-sponsors from the other party. Committee "
              "bills and Nebraska&rsquo;s nonpartisan Legislature have no party.")


def party(b):
    """A bill row's sponsor-party class ("D", "R", "B" or ""; build_data.py's write_issues())."""
    return b[11] if len(b) > 11 else ""


PARTY_TAGS = {"D": ("D", "Sponsored by Democrats"), "R": ("R", "Sponsored by Republicans"),
              "B": ("Both", "Sponsored by both parties")}


def party_tag(c):
    """The badge before a bill's stage: D, R or Both, or nothing for committee bills and unknown parties."""
    if c not in PARTY_TAGS:
        return ""
    short, words = PARTY_TAGS[c]
    return f'<span class="pty {c}" role="img" title="{words}" aria-label="{words}">{short}</span>'


def stage_text(state, stage, kind):
    if kind == "const" and stage == 3:
        return "Sent to the voters"
    if state == "ne" and stage == 3:
        return "Passed the Legislature"
    if state == "us" and stage == 4:
        return "On the President’s desk"
    return STAGES[stage]


def load(site, congress=False):
    """{state: {"name", "files": [each session's issues file]}} for the states built; with congress=True, Congress's
    alone ({"us": ...}, or {} when it isn't built)."""
    out = {}
    for s in sorted(os.listdir(site)):
        folder = os.path.join(site, s, "data")
        # Congress (/us/) isn't a state: kept out of the issue pages' state counts, tables and maps. The front page's
        # map shows it as its own tile, from summary.json's "us" entries and bills.json's "us" list (main()).
        if len(s) != 2 or (s == "us") != congress or not os.path.isdir(folder):
            continue
        files = []
        for name in sorted(os.listdir(folder)):
            if re.fullmatch(r"issues_\d{4}\.json", name):
                try:
                    files.append(json.load(open(os.path.join(folder, name), encoding="utf-8")))
                except ValueError:
                    pass
        if files:
            out[s] = {"name": files[0]["name"], "files": files}
    return out


def shown(num, others=(), st=""):
    """A bill number as people write it: "HB1005" -> "HB 1005"; with a record's other numbers, "A 11560 / S 8443".
    Maine's records are "HLD307"/"SLD307" (the house that has the paper, then its LD number): "LD 307"."""
    out = [re.sub(r"^([A-Z]+)(\d)", r"\1 \2", n) for n in [num, *others]]
    if st == "me":
        out = [re.sub(r"^[HS]LD ", "LD ", n) for n in out]
    return " / ".join(out)


def link(f, num):
    page = f["page"] if f["page"] != "./" else ""
    return f"../../{f['state']}/{page}#{re.sub(r'[A-Z]$', '', num)}"


# The tile map's grid (row, column), as on the front page (home.html's GRID).
GRID = {"AK": (0, 0), "ME": (0, 10), "VT": (1, 9), "NH": (1, 10),
        "WA": (2, 0), "ID": (2, 1), "MT": (2, 2), "ND": (2, 3), "MN": (2, 4), "IL": (2, 5), "WI": (2, 6), "MI": (2, 7), "NY": (2, 8),
        "RI": (2, 9), "MA": (2, 10), "OR": (3, 0), "NV": (3, 1), "WY": (3, 2), "SD": (3, 3), "IA": (3, 4), "IN": (3, 5), "OH": (3, 6),
        "PA": (3, 7), "NJ": (3, 8), "CT": (3, 9), "CA": (4, 0), "UT": (4, 1), "CO": (4, 2), "NE": (4, 3), "MO": (4, 4), "KY": (4, 5),
        "WV": (4, 6), "VA": (4, 7), "MD": (4, 8), "DE": (4, 9), "AZ": (5, 1), "NM": (5, 2), "KS": (5, 3), "AR": (5, 4), "TN": (5, 5),
        "NC": (5, 6), "SC": (5, 7), "OK": (6, 3), "LA": (6, 4), "MS": (6, 5), "AL": (6, 6), "GA": (6, 7), "HI": (7, 0), "TX": (7, 3),
        "FL": (7, 7)}
SHORT = {"datacenters": "data centers", "pfas": "PFAS", "ai": "artificial intelligence", "kidsonline": "children online",
         "phones": "phones in schools", "housing": "housing supply", "minwage": "minimum wage", "repair": "right to repair",
         "betting": "sports betting", "drugcosts": "drug costs", "abortion": "abortion", "firearms": "firearms",
         "vouchers": "school vouchers", "voting": "voting", "immigration": "immigration",
         "tenants": "rent and tenants", "proptax": "property tax relief", "transgender": "transgender people", "dei": "DEI",
         "cannabis": "cannabis", "privacy": "data privacy", "campaignfinance": "campaign finance",
         "redistricting": "redistricting", "paidleave": "paid leave", "childcare": "child care", "ivf": "IVF and fertility",
         "fluoride": "fluoride", "nuclear": "nuclear energy", "wildfire": "wildfire", "noncompete": "noncompetes",
         "strentals": "short-term rentals", "water": "water rights", "psychedelics": "psychedelics", "cryptoatm": "crypto ATMs",
         "medicaidwork": "Medicaid work requirements", "dst": "daylight saving time", "books": "book bans",
         "medicaldebt": "medical debt", "police": "police accountability", "deathpenalty": "death penalty",
         "vaccines": "vaccines", "unions": "unions", "initiatives": "ballot initiative rules", "rcv": "ranked-choice voting",
         "utilityrates": "utility rates", "climate": "climate and clean energy", "esg": "investing and boycotts",
         "religion": "religion in schools", "childlabor": "child labor", "protest": "protest laws", "kratom": "kratom",
         "coverage": "health coverage", "assault": "sexual & domestic abuse",
         "homeless": "homelessness", "incometax": "income tax cuts", "homeinsurance": "homeowners insurance",
         "bail": "bail and pretrial", "overdose": "drugs and overdoses", "contraception": "contraception",
         "mentalhealth": "mental health and 988", "foodadditives": "food additives", "schoolmeals": "school meals",
         "plastics": "plastics and packaging", "heat": "workplace heat", "samesex": "same-sex marriage"}


def step(n):
    return 3 if n >= 15 else 2 if n >= 5 else 1 if n else 0


def covers(f, year):
    return f["session"] <= year < f["session"] + (f.get("years") or 1)


def met(f, year):
    """Whether the legislature met that year: a session file covering it, with bills introduced or acted on then (a
    two-year session's file covers an even year Texas's Legislature doesn't meet in; a few stray actions don't count)."""
    if not covers(f, year):
        return False
    if "active" not in f:
        return True
    n = f["active"].get(str(year), 0)
    return n > 0 if f.get("upcoming") else n >= max(5, 0.02 * (f.get("total") or 0))


def year_view(iid, states, year):
    """For one issue and calendar year: {state: (bills alive that year, became law that year, rows)}, the states with a
    session that year, and each state's session label and bill total. A bill is alive from the year it was introduced
    through the year of its last action."""
    by, open_, info = {}, set(), {}
    for st, d in states.items():
        rows, seen = [], set()
        for f in d["files"]:
            if covers(f, year):
                info[st] = (f["label"], f.get("total") or 0)
            if met(f, year):
                open_.add(st)
            for b in f["bills"]:
                if iid not in b[0]:
                    continue
                intro, law = (b[7] if len(b) > 7 else f["session"]), (b[8] if len(b) > 8 else "")
                # Alive through its last action, but not past its session's end: Illinois and New Jersey close a General
                # Assembly with a line on every pending bill in the next January, which isn't the bill moving then.
                last = min(int((b[5] or "0")[:4] or 0), f["session"] + (f.get("years") or 1) - 1)
                new, passed = intro <= year <= max(intro, last), law[:4] == str(year)
                key = (f["session"], b[2])
                if (new or passed) and key not in seen:
                    seen.add(key)
                    rows.append((f, b, new, passed))
        if rows:
            by[st] = (sum(1 for r in rows if r[2]), sum(1 for r in rows if r[3]), rows)
    return by, open_, info


def badge(laws):
    return f'<span class="lawn" aria-hidden="true">{laws}</span>' if laws else ""


# Sponsors' party on the maps: each state's bills that year split D, B (both), R, and none (committee or unknown), left
# to right like the political spectrum (home.html draws the same bar from summary.json's counts).
PARTS = (("D", "Democratic"), ("B", "both"), ("R", "Republican"), ("-", "committee"))


def split(rows):
    """[D, B, R, none]: a state's bills alive that year by sponsors' party."""
    out = [0, 0, 0, 0]
    for _, b, new, _ in rows:
        if new:
            out["DBR".find(party(b)) if party(b) in ("D", "B", "R") else 3] += 1
    return out


def split_words(sp):
    return ", ".join(f"{k} {w}" for k, (_, w) in zip(sp, PARTS) if k)


def pbar(sp):
    """The thin bar along a tile's bottom: not drawn (the owner's choice 2026-11-17: hard to see on the green; the panel and
    the chart view show the split)."""
    return ""


def tile_map(iid, by, names, open_, year, upcoming, nodata=()):
    """The tile map, each state shaded by its bills on the issue introduced that year, with the number that became law,
    each square a link to the state's bills below. A state with no bills that year is "no session" when its legislature
    didn't meet (Texas in even years), "no data" when it met but the site has no data for that year (nodata), and "no
    bills filed yet" for next year."""
    out = []
    for code, (r, c) in GRID.items():
        st = code.lower()
        style = f"grid-row:{r + 1};grid-column:{c + 1}"
        if st not in names:
            out.append(f'<span class="off" style="{style}" title="Coming soon" aria-label="{code}, coming soon">{code}</span>')
            continue
        n, laws = by[st][:2] if st in by else (0, 0)
        if st not in open_ and not n and not laws:
            gap = not upcoming and st in nodata
            label = (f"{names[st]}: no bills filed yet for {year}" if upcoming else
                     f"{names[st]}: no data on this site for {year}" if gap else f"{names[st]}: no regular session in {year}")
            out.append(f'<span class="off {"nodata" if gap else "wait"}" style="{style}" title="{e(label)}" aria-label="{e(code + ", " + label)}">{code}</span>')
            continue
        label = (f"{names[st]}: {n} bill{'' if n == 1 else 's'}{' prefiled' if upcoming else ''} in {year}" if n else f"{names[st]}: none in {year}")
        label += f", {laws} became law" if laws else ""
        sp = split(by[st][2]) if st in by else [0, 0, 0, 0]
        said = f"; sponsors: {split_words(sp)}" if n else ""
        href = f"#{st}" if st in by else "#bills"
        out.append(f'<a href="{href}" data-st="{st}" data-name="{e(names[st])}" class="h{step(n)}" style="{style}" title="{e(label + said)}" aria-label="{e(code + ", " + label + said)}" aria-controls="panel">{code}{badge(laws)}{pbar(sp)}</a>')
    return ('<div class="mapbox" id="mapbox"><div class="tiles">' + "".join(out) + "</div>"
            '<div class="chart" id="chart" role="group" aria-label="States by number of bills"></div></div>')


def no_data(states, year):
    """The states whose legislature met that year but whose data for it isn't on the site: no session file covers the
    year (Indiana's, Utah's and Virginia's pages begin with 2024)."""
    return {st for st, d in states.items() if not any(covers(f, year) for f in d["files"])}


def page_name(year, default):
    return "./" if year == default else f"{year}.html"


def bill_items(iid, st, mine):
    """A state's (or Congress's) bills on the issue, one line each: laws first, then the furthest along; within a stage,
    the latest action first."""
    items = []
    for f, b, new, passed in sorted(sorted(mine, key=lambda x: x[1][5], reverse=True), key=lambda x: (x[1][4] != 5, -x[1][4])):
        fl = " ".join(re.sub(r"[^a-z]+", "-", x.lower()) for x in (b[1].get(iid) or []))
        why = (b[9].get(iid) if len(b) > 9 else "") or ""
        items.append(f'<li data-stage="{b[4]}" data-f="{e(fl)}" data-p="{party(b) or "-"}" data-n="{int(new)}" data-l="{int(passed)}" data-k="{f["session"]}|{e(b[2])}|{e(b[5] or "")}"><a href="{e(link(f, b[2]))}">{e(shown(b[2], b[10] if len(b) > 10 else (), st))}</a>'
                     f'<span class="tags">{party_tag(party(b))}<span class="stg s{b[4]}">{e(stage_text(st, b[4], b[6]) + (f" in {b[8][:4]}" if b[4] == 5 and not passed and b[8] else ""))}</span></span>'
                     f'<span class="t">{e(b[3])}</span>'
                     + (f'<span class="why">{e(why)}</span>' if why and why.lower() not in b[3].lower() else "")
                     + '</li>')
    return "".join(items)


STAR_TIP = "The legislature publishes only bill titles, so some of its bills on this issue may be missed."


def issue_page(issue, states, year, years, default, upcoming, congress=None):
    iid = issue["id"]
    names = {st: d["name"] for st, d in states.items()}
    by, open_, info = year_view(iid, states, year)
    nodata = set() if upcoming else no_data(states, year)
    rows, blocks, intro_n, laws_n, moving = [], [], 0, 0, 0
    for st in sorted(by, key=lambda s: names[s]):
        n, laws, mine = by[st]
        n_moving = sum(1 for f, b, new, _ in mine if new and 1 <= b[4] <= 4)
        intro_n, laws_n, moving = intro_n + n, laws_n + laws, moving + n_moving
        flag = f'&nbsp;<abbr title="{STAR_TIP}">*</abbr>' if st in TITLES_ONLY else ""
        label, total = info.get(st, ("", 0))
        rows.append((n, f'<tr data-st="{st}"><th scope="row"><a href="#{st}">{e(names[st])}</a>{flag}</th><td class="n">{n}</td>'
                        f'<td class="n">{laws}</td><td class="n">{n_moving}</td><td class="n">{f"{total:,}" if total else ""}</td>'
                        f'<td class="sess">{e(label)}</td></tr>'))
        blocks.append(f'<section class="st" data-name="{e(names[st].lower())}"><h3 id="{st}">{e(names[st])} '
                      f'<span class="note">(<span class="cnt">{n}</span>{flag})</span></h3><ul class="bills">{bill_items(iid, st, mine)}</ul></section>')
    # Congress: its own line under the map and its own list after the states', never in the states' counts.
    us_n = us_l = 0
    fed_line = fed_block = ""
    if congress:
        us_by, _, _ = year_view(iid, congress, year)
        if "us" in us_by:
            us_n, us_l, mine = us_by["us"]
            fed_block = (f'<section class="st fed" data-name="congress"><h3 id="us">Congress <small>(not in the states&rsquo; counts)</small> '
                         f'<span class="note">(<span class="cnt">{us_n}</span>)</span></h3><ul class="bills">{bill_items(iid, "us", mine)}</ul></section>')
        fed_line = (f'<p class="note" id="fedLine">Congress, not counted above: <b id="usN">{us_n}</b> bill{"" if us_n == 1 else "s"}{" prefiled" if upcoming else ""} in {year}'
                    + ("" if upcoming else f', <b id="usL">{us_l}</b> became law')
                    + (f'. <a href="#us">See Congress&rsquo;s bills</a>.' if fed_block else ".") + "</p>")
    in_states = len([1 for st in by if by[st][0]])
    rows.sort(key=lambda r: -r[0])
    quiet = [st for st in names if st not in open_ and st not in by]
    none = sorted(names[st] for st in open_ if st not in by)
    gaps = sorted(names[st] for st in quiet if st in nodata)
    nosession = sorted(names[st] for st in quiet if st not in nodata)
    unbuilt = any(code.lower() not in names for code in GRID)
    cur, pre = ' aria-current="page"', ' title="Prefiled so far"'
    year_links = "".join(f'<a href="{page_name(y, default)}"{cur if y == year else ""}{pre if y > default else ""}>{y}</a>'
                         for y in years)
    fopts = "".join(f'<option value="f:{e(re.sub(r"[^a-z]+", "-", k.lower()))}">{e(k)}</option>' for k in issue.get("filters", {}))
    verb = "prefiled" if upcoming else "with action"
    up = "../../"
    lede_counts = (f'<b id="nBills">{intro_n:,}</b> bills {verb} in <b id="nStates">{in_states}</b> states in {year}'
                   + ("" if upcoming else f'; <b id="nLaws">{laws_n:,}</b> became law in {year}') + ".")
    keys = ['<span class="key"><i class="sq h0"></i>None</span>', '<span class="key"><i class="sq h1"></i>1&ndash;4 bills</span>',
            '<span class="key"><i class="sq h2"></i>5&ndash;14</span>', '<span class="key"><i class="sq h3"></i>15 or more</span>']
    # The chart view's keys (the party colors and the law badge), in the same place as the map's.
    ckeys = ['<span class="key"><i class="pD"></i>Democratic sponsors</span>', '<span class="key"><i class="pB"></i>Both parties</span>',
             '<span class="key"><i class="pR"></i>Republican</span>', '<span class="key"><i class="pN"></i>Committee or none</span>']
    if not upcoming:
        keys.append('<span class="key"><span class="lawn">3</span>Number that became law</span>')
        ckeys.append(keys[-1])
    if upcoming and quiet:
        keys.append('<span class="key"><i class="sq wait"></i>No bills filed yet</span>')
    if not upcoming and nosession:
        keys.append('<span class="key"><i class="sq wait"></i>No session that year</span>')
    if gaps:
        keys.append('<span class="key"><i class="sq nodata"></i>No data for this year</span>')
    if unbuilt:
        keys.append('<span class="key"><i class="sq off"></i>Not on the site yet</span>')
    notes = []
    if upcoming:
        notes.append("Most legislatures start taking bills in January; these are the bills prefiled so far.")
    if none:
        notes.append(f"None in {year}: {e(', '.join(none))}.")
    if upcoming and quiet:
        notes.append(f"No bills filed yet for {year}: {e(', '.join(sorted(names[st] for st in quiet)))}.")
    if not upcoming and nosession:
        notes.append(f"No regular session in {year} (these legislatures meet every other year): {e(', '.join(nosession))}.")
    if gaps:
        notes.append(f"No data on this site for {year} (the legislature met; this site&rsquo;s data for it begins later): {e(', '.join(gaps))}.")
    note_html = "".join(f'<p class="note">{x}</p>' for x in notes)
    star_note = (f'<p class="note">* {STAR_TIP}</p>' if any(st in TITLES_ONLY for st in by) else "")
    # Link previews and the canonical link (site_meta.py): the default year's page is the issue's folder.
    meta = site_meta.tags(f"{issue['name']}: bills in every state, {year} · State Bill Tracker", DESC.get(iid, ""),
                          site_meta.root() + f"issues/{iid}/" + ("" if year == default else f"{year}.html"))
    body = HEAD.format(title=f"{issue['name']}: bills in every state, {year}", desc=e(DESC.get(iid, "")), meta=meta, css=css()) + f"""
<p class="crumbs"><a href="{up}">State Bill Tracker</a> / <a href="../">Issues</a></p>
<h1>{e(issue['name'])}</h1>
<p class="lede">{e(DESC.get(iid, ""))}</p>
<div class="views"><nav class="when" aria-label="Year">{year_links}</nav>
<div class="when" id="vsw" role="group" aria-label="Show as"><button type="button" data-v="map" aria-pressed="true">Map</button><button type="button" data-v="chart" aria-pressed="false">Chart</button></div></div>
<div class="mapwrap">
<div class="mapcol">
{tile_map(iid, by, names, open_, year, upcoming, nodata)}
<p class="legend" id="legend"><span class="kset mk">{"".join(keys)}</span><span class="kset ck">{"".join(ckeys)}</span></p>
</div>
<aside class="panel" id="panel">
<div id="pdefault">
<p id="lede">{lede_counts}</p>
<div id="pall"></div>
{note_html}{fed_line}

</div>
<div id="pstate" aria-live="polite" hidden></div>
</aside>
</div>
<details class="table"><summary>Show as a table</summary>
<div class="tablewrap"><table>
<thead><tr><th scope="col">State</th><th scope="col" class="n">{"Prefiled" if upcoming else "Bills"}</th><th scope="col" class="n">Became law</th><th scope="col" class="n">Moving</th><th scope="col" class="n">All bills</th><th scope="col">Session</th></tr></thead>
<tbody>{"".join(r for _, r in rows)}</tbody></table></div>
<p class="note">A bill counts in each year from its introduction to its last action in its session (in a two-year legislature, most are filed in the first year and keep moving in the second); &ldquo;Became law&rdquo; counts the year it did. &ldquo;Moving&rdquo;: out of committee, not yet law or vetoed. &ldquo;All bills&rdquo;: every bill in the state's session, for scale.</p>
{star_note}
</details>
<h2 id="bills">The bills</h2>
<div class="tools">
<label for="filter" class="vh">Show</label>
<select id="filter"><option value="">All bills</option><option value="law">Became law</option><option value="moving">Still moving</option>{fopts}</select>
<label for="party" class="vh">Sponsor's party</label>
<select id="party"><option value="">Sponsor&rsquo;s party: all</option><option value="D">Democrats</option><option value="R">Republicans</option><option value="B">Both parties</option><option value="-">Committee or none</option></select><button type="button" class="info" id="partyInfo" aria-expanded="false" aria-controls="partyNote" aria-label="About sponsor&rsquo;s party">&#9432;</button>
<input type="search" id="find" placeholder="Find a state" aria-label="Find a state">
</div>
<p class="note hidden" id="partyNote">{PARTY_NOTE}</p>
<p class="note" id="count" aria-live="polite"></p>
{"".join(blocks)}{fed_block}
<footer>Bills are found by the words in their titles and summaries, so a few are missed and a few are only partly about the issue. Bills for one city or county are left out. Open a bill for its status, votes and who to contact.</footer>
</main>
<script>
// Both menus filter the bills, and the map, the counts line and the table follow them (counted from the list's own
// items: data-n, alive that year; data-l, became law that year; data-p, the sponsors' party). "Find a state" only
// hides states' lists. Congress's list (section.fed) is filtered too, and counted on its own line.
const UPCOMING = {"true" if upcoming else "false"}, YEAR = {year};
const step = (n) => (n >= 15 ? 3 : n >= 5 ? 2 : n ? 1 : 0);
// Sponsors' party: each state's bills that year (as the Show menu filters them) split D, B, R and none, drawn as a thin
// bar on its tile (hidden when one party is chosen) and a bigger one in the panel, whose parts set the party menu.
const PARTS = [["D", "Democratic"], ["B", "both"], ["R", "Republican"], ["-", "committee"]];
const PCLASS = {{ D: "pD", B: "pB", R: "pR", "-": "pN" }};
const PWORDS = {{ D: "Democratic sponsors", B: "sponsors from both parties", R: "Republican sponsors", "-": "no party sponsor (committee bills)" }};
let SPLIT = {{}}, PP_FOCUS = null;
const splitWords = (sp) => PARTS.map(([, w], i) => (sp[i] ? `${{sp[i]}} ${{w}}` : "")).filter(Boolean).join(", ");
const pbar = (sp) => (false && sp && sp.some(Boolean) ? `<span class="pbar" aria-hidden="true">${{PARTS.map(([c], i) => (sp[i] ? `<i class="${{PCLASS[c]}}" style="flex-grow:${{sp[i]}}"></i>` : "")).join("")}}</span>` : "");
function pbig(sp) {{
  if (!sp || !sp.some(Boolean)) return "";
  const pv = document.getElementById("party").value, f = pv ? " f" : "", on = (c) => String(pv === c);
  return `<div class="pbig${{f}}">${{PARTS.map(([c], i) => (sp[i] ? `<button type="button" class="${{PCLASS[c]}}" style="flex-grow:${{sp[i]}}" data-pp="${{c}}" aria-pressed="${{on(c)}}" tabindex="-1" aria-hidden="true" title="${{esc(`${{sp[i]}} with ${{PWORDS[c]}}`)}}"></button>` : "")).join("")}}</div>`
    + `<p class="pkey${{f}}"><span>Sponsors:</span>${{PARTS.map(([c, w], i) => (sp[i] ? `<button type="button" data-pp="${{c}}" aria-pressed="${{on(c)}}" aria-label="${{esc(`${{sp[i]}} with ${{PWORDS[c]}}: ${{pv === c ? "show all bills" : "show only these"}}`)}}"><i class="${{PCLASS[c]}}"></i>${{sp[i]}} ${{w}}</button>` : "")).join("")}}</p>`;
}}
function ppClick(e) {{
  const b = e.target.closest("[data-pp]");
  if (!b) return false;
  const sel = document.getElementById("party");
  sel.value = sel.value === b.dataset.pp ? "" : b.dataset.pp;
  PP_FOCUS = b.closest(".pkey") ? b.dataset.pp : null;
  const box = b.closest("#pall") ? document.getElementById("pall") : pst;
  apply();
  if (PP_FOCUS) box.querySelector(`.pkey button[data-pp="${{PP_FOCUS}}"]`)?.focus();
  PP_FOCUS = null;
  return true;
}}
function apply() {{
  const q = document.getElementById("find").value.trim().toLowerCase(), v = document.getElementById("filter").value;
  const pv = document.getElementById("party").value;
  let shown = 0, bills = 0, laws = 0, states = 0, usBy = null;
  const by = {{}};
  for (const sec of document.querySelectorAll("section.st")) {{
    let any = 0, n = 0, l = 0, mv = 0;
    const sp = [0, 0, 0, 0];
    for (const li of sec.querySelectorAll("li")) {{
      const s = +li.dataset.stage, f = li.dataset.f.split(" ");
      const shows = !v || (v === "law" && s === 5) || (v === "moving" && s >= 1 && s <= 4) || (v.startsWith("f:") && f.includes(v.slice(2)));
      if (shows && li.dataset.n === "1") sp[Math.max(0, PARTS.findIndex(([c]) => c === li.dataset.p))]++;
      const ok = shows && (!pv || li.dataset.p === pv);
      li.classList.toggle("hidden", !ok);
      if (!ok) continue;
      any++;
      if (li.dataset.n === "1") {{ n++; if (s >= 1 && s <= 4) mv++; }}
      if (li.dataset.l === "1") l++;
    }}
    sec.querySelector(".cnt").textContent = any;
    const vis = any && (!q || sec.dataset.name.includes(q));
    sec.classList.toggle("hidden", !vis);
    if (vis) shown += any;
    if (sec.classList.contains("fed")) {{
      SPLIT.us = sp;
      const un = document.getElementById("usN"), ul = document.getElementById("usL");
      if (un) un.textContent = n;
      if (ul) ul.textContent = l;
      usBy = [n, l];
      continue;
    }}
    by[sec.querySelector("h3").id] = [n, l, mv];
    SPLIT[sec.querySelector("h3").id] = sp;
    bills += n; laws += l; states += n ? 1 : 0;
  }}
  document.getElementById("count").textContent = (v || q || pv) ? `Showing ${{shown.toLocaleString()}} bills.` : "";
  document.getElementById("nBills").textContent = bills.toLocaleString();
  document.getElementById("nStates").textContent = states;
  const nl = document.getElementById("nLaws");
  if (nl) nl.textContent = laws.toLocaleString();
  const all = [0, 0, 0, 0];
  for (const [st, sp] of Object.entries(SPLIT)) if (st !== "us") sp.forEach((k, i) => {{ all[i] += k; }});
  document.getElementById("pall").innerHTML = pbig(all);
  for (const a of document.querySelectorAll(".tiles a[data-st]")) {{
    const [n, l] = by[a.dataset.st] || [0, 0], code = a.dataset.st.toUpperCase();
    a.className = `h${{step(n)}}` + (a.dataset.st === pinned ? " sel" : "");
    for (const old of a.querySelectorAll(".lawn, .pbar")) old.remove();
    if (l) a.insertAdjacentHTML("beforeend", `<span class="lawn" aria-hidden="true">${{l}}</span>`);
    const sp = !pv && n ? SPLIT[a.dataset.st] : null;
    if (sp) a.insertAdjacentHTML("beforeend", pbar(sp));
    const label = (n ? `${{a.dataset.name}}: ${{n}} bill${{n === 1 ? "" : "s"}}${{UPCOMING ? " prefiled" : ""}} in ${{YEAR}}` : `${{a.dataset.name}}: none in ${{YEAR}}`)
      + (l ? `, ${{l}} became law` : "") + (sp ? `; sponsors: ${{splitWords(sp)}}` : "");
    a.title = label;
    a.setAttribute("aria-label", `${{code}}, ${{label}}`);
  }}
  drawChart(by, usBy, pv);
  for (const tr of document.querySelectorAll("tr[data-st]")) {{
    const [n, l, mv] = by[tr.dataset.st] || [0, 0, 0], td = tr.querySelectorAll("td.n");
    td[0].textContent = n; td[1].textContent = l; td[2].textContent = mv;
    tr.classList.toggle("hidden", !n && !l);
  }}
  if (showing) showState(showing);
}}
// The panel: pointing at a state (or focusing it) lists its bills on the issue, as the menus filter them; clicking pins
// it (a tap does, on a phone). Stars write the state's watchlist in this browser, as on the state's page and the front
// page ("abt:<st>:watch"; New York's "abt:watch").
const pdef = document.getElementById("pdefault"), pst = document.getElementById("pstate"), tiles = document.querySelector(".tiles");
const canHover = matchMedia("(hover: hover)").matches;
let pinned = null, showing = null;
const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({{ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }}[c]));
const WKEY = (st) => (st === "ny" ? "abt:watch" : `abt:${{st}}:watch`);
function readWatch(st) {{
  try {{ const o = JSON.parse(localStorage.getItem(WKEY(st)) || "{{}}"); return o && typeof o === "object" && !Array.isArray(o) ? o : {{}}; }} catch (e) {{ return {{}}; }}
}}
function writeWatch(st, o) {{ try {{ localStorage.setItem(WKEY(st), JSON.stringify(o)); }} catch (e) {{}} }}
const baseNum = (n) => n.replace(/[A-Z]$/, "");
function starBtn(st, k, label) {{
  const [session, num] = k.split("|"), on = `${{session}}:${{baseNum(num)}}` in readWatch(st);
  return `<button type="button" class="star" data-st="${{st}}" data-k="${{esc(k)}}" aria-pressed="${{on}}" aria-label="${{esc(`${{on ? "Remove" : "Star"}} ${{label}}${{on ? " from your bills" : ": follow it in Your bills"}}`)}}" title="${{on ? "Remove from your bills" : "Star: follow it in Your bills"}}">${{on ? "★" : "☆"}}</button>`;
}}
const FILTER_WORDS = () => {{
  const f = document.getElementById("filter"), p = document.getElementById("party");
  return [f.value ? f.options[f.selectedIndex].text.toLowerCase() : "", p.value ? `sponsors: ${{p.options[p.selectedIndex].text}}` : ""].filter(Boolean).join(", ");
}};
function showState(st) {{
  showing = st;
  pst.hidden = !st; pdef.hidden = !!st;
  if (!st) return;
  const tile = tiles.querySelector(`a[data-st="${{st}}"]`), name = tile ? tile.dataset.name : st === "us" ? "Congress" : st.toUpperCase();
  const h = document.getElementById(st), sec = h && h.closest("section.st");
  const items = sec ? [...sec.querySelectorAll("li:not(.hidden)")] : [];
  const n = items.filter((li) => li.dataset.n === "1").length, l = items.filter((li) => li.dataset.l === "1").length;
  const fw = FILTER_WORDS(), only = fw ? ` (${{fw}})` : "";
  const links = st === pinned ? ` ${{items.length ? `<a href="#${{st}}" data-jump>Jump to its bills below</a> · ` : ""}}<a href="#" data-close>Close</a>` : "";
  pst.innerHTML = `<h3>${{esc(name)}}</h3><p>${{n ? `${{n}} bill${{n === 1 ? "" : "s"}}${{UPCOMING ? " prefiled" : ""}} in ${{YEAR}}` : `No bills in ${{YEAR}}`}}${{only}}${{l ? `, ${{l}} became law` : ""}}.${{links}}</p>`
    + pbig(SPLIT[st])
    + (items.length ? `<ul>${{items.map((li) => {{
      const a = li.querySelector("a"), why = li.querySelector(".why"), t = li.querySelector(".t").textContent;
      return `<li><a href="${{esc(a.getAttribute("href"))}}" title="${{esc(t)}}"><b>${{esc(a.textContent)}}</b>${{li.querySelector(".tags").outerHTML}}`
        + `<span class="tt">${{esc(why ? t.replace(/[.\\s]+$/, "") : t)}}${{why ? `<span class="why">: ${{esc(why.textContent)}}</span>` : ""}}</span></a>`
        + `${{li.dataset.k ? starBtn(st, li.dataset.k, a.textContent) : ""}}</li>`;
    }}).join("")}}</ul>` : "");
}}
function pin(st) {{
  pinned = st;
  for (const t of tiles.querySelectorAll("a[data-st]")) t.classList.toggle("sel", t.dataset.st === pinned);
  for (const t of chartEl.querySelectorAll("button.crow")) {{ t.classList.toggle("sel", t.dataset.st === pinned); t.setAttribute("aria-pressed", String(t.dataset.st === pinned)); }}
  showState(pinned);
}}
// "Map | Chart": the chart (one bar per state with bills, most first, split by sponsors' party; Congress below, on the
// states' scale) is drawn by apply() with the map. The choice is kept in the address (?view=chart) and in this browser,
// shared with the front page.
const chartEl = document.getElementById("chart"), vsw = document.getElementById("vsw");
let CHART = false;
try {{ CHART = localStorage.getItem("abt:issueview") === "chart"; }} catch (e) {{}}
{{ const v = new URLSearchParams(location.search).get("view"); if (v === "chart" || v === "map") CHART = v === "chart"; }}
function chartRow(st, name, n, l, sp, pv, max) {{
  const cut = n > max, frac = Math.min(n, max) / (max || 1);
  const parts = pv ? `<i class="${{PCLASS[pv]}}" style="flex-grow:1"></i>`
    : sp && sp.some(Boolean) ? PARTS.map(([c], i) => (sp[i] ? `<i class="${{PCLASS[c]}}" style="flex-grow:${{sp[i]}}"></i>` : "")).join("") : `<i class="pN" style="flex-grow:1"></i>`;
  const fw = FILTER_WORDS(), words = `${{name}}: ${{n ? `${{n}} bill${{n === 1 ? "" : "s"}}${{UPCOMING ? " prefiled" : ""}} in ${{YEAR}}` : `none in ${{YEAR}}`}}${{fw ? ` (${{fw}})` : ""}}`
    + (l ? `, ${{l}} became law` : "") + (sp && !pv && n ? `; sponsors: ${{splitWords(sp)}}` : "");
  return `<button type="button" class="crow${{st === pinned ? " sel" : ""}}" data-st="${{st}}" title="${{esc(words)}}" aria-label="${{esc(words)}}" aria-pressed="${{st === pinned}}" aria-controls="panel">`
    + `<span class="cn"><span class="full">${{esc(name)}}</span><span class="ab">${{st === "us" ? "U.S." : st.toUpperCase()}}</span></span>`
    + `<span class="ct">${{n ? `<span class="cbar${{cut ? " cut" : ""}}" style="width:calc((100% - 5.5em) * ${{frac.toFixed(4)}})" aria-hidden="true">${{parts}}</span>` : ""}}`
    + `<span class="cv" aria-hidden="true">${{n}}</span>${{l ? `<span class="lawn" aria-hidden="true">${{l}}</span>` : ""}}</span></button>`;
}}
function drawChart(by, usBy, pv) {{
  const name = (st) => tiles.querySelector(`a[data-st="${{st}}"]`)?.dataset.name || st.toUpperCase();
  const rows = Object.entries(by).filter(([, [n, l]]) => n || l)
    .sort((a, b) => b[1][0] - a[1][0] || b[1][1] - a[1][1] || name(a[0]).localeCompare(name(b[0])));
  const max = Math.max(1, ...rows.map((r) => r[1][0]));
  let html = rows.map(([st, [n, l]]) => chartRow(st, name(st), n, l, SPLIT[st], pv, max)).join("");
  if (!rows.length) html += `<p class="cnote">No state has bills that match.</p>`;
  if (usBy && (usBy[0] || usBy[1])) {{
    html += `<div class="cfed">${{chartRow("us", "Congress", usBy[0], usBy[1], SPLIT.us, pv, max)}}`
      + (usBy[0] > max ? `<p class="cnote">Congress&rsquo;s bar is cut short: its ${{usBy[0]}} bills are more than any state&rsquo;s ${{max}}.</p>` : "") + "</div>";
  }}
  chartEl.innerHTML = html;
}}
function setChart() {{
  for (const b of vsw.querySelectorAll("button")) b.setAttribute("aria-pressed", String((b.dataset.v === "chart") === CHART));
  document.getElementById("mapbox").classList.toggle("charted", CHART);
  document.getElementById("legend").classList.toggle("charted", CHART);
  tiles.inert = CHART;
}}
vsw.addEventListener("click", (e) => {{
  const b = e.target.closest("button[data-v]");
  if (!b || (b.dataset.v === "chart") === CHART) return;
  CHART = b.dataset.v === "chart";
  try {{ localStorage.setItem("abt:issueview", CHART ? "chart" : "map"); }} catch (e) {{}}
  try {{ history.replaceState(null, "", (CHART ? "?view=chart" : location.pathname) + location.hash); }} catch (e) {{}}
  setChart();
}});
chartEl.addEventListener("pointerover", (e) => {{
  const b = e.target.closest("button.crow");
  if (b && !pinned && canHover) showState(b.dataset.st);
}});
chartEl.addEventListener("mouseleave", () => {{ if (!pinned && canHover) showState(null); }});
chartEl.addEventListener("focusin", (e) => {{ const b = e.target.closest("button.crow"); if (b && !pinned) showState(b.dataset.st); }});
chartEl.addEventListener("focusout", (e) => {{ if (!pinned && !chartEl.contains(e.relatedTarget)) showState(null); }});
chartEl.addEventListener("click", (e) => {{
  const b = e.target.closest("button.crow");
  if (!b) return;
  pin(pinned === b.dataset.st ? null : b.dataset.st);
  if (!pinned && canHover) showState(b.dataset.st);
}});
tiles.addEventListener("pointerover", (e) => {{
  const a = e.target.closest("a[data-st]");
  if (a && !pinned && canHover) showState(a.dataset.st);
}});
tiles.addEventListener("mouseleave", () => {{ if (!pinned && canHover) showState(null); }});
tiles.addEventListener("focusin", (e) => {{ const a = e.target.closest("a[data-st]"); if (a && !pinned) showState(a.dataset.st); }});
tiles.addEventListener("focusout", (e) => {{ if (!pinned && !tiles.contains(e.relatedTarget)) showState(null); }});
tiles.addEventListener("click", (e) => {{
  const a = e.target.closest("a[data-st]");
  if (!a) return;
  e.preventDefault();
  pin(pinned === a.dataset.st ? null : a.dataset.st);
  if (!pinned && canHover) showState(a.dataset.st);
}});
document.getElementById("pall").addEventListener("click", ppClick);
pst.addEventListener("click", (e) => {{
  if (ppClick(e)) return;
  if (e.target.closest("[data-close]")) {{ e.preventDefault(); const was = pinned; pin(null); (CHART ? chartEl.querySelector(`button.crow[data-st="${{was}}"]`) : tiles.querySelector(`a[data-st="${{was}}"]`))?.focus(); return; }}
  const b = e.target.closest("button.star");
  if (!b) return;
  const [session, num, last] = b.dataset.k.split("|"), w = readWatch(b.dataset.st), k = `${{session}}:${{baseNum(num)}}`;
  if (k in w) delete w[k]; else w[k] = {{ seen: last, stance: "support" }};
  writeWatch(b.dataset.st, w);
  const label = b.getAttribute("aria-label").replace(/^(Star|Remove) /, "").replace(/(: follow it in Your bills| from your bills)$/, "");
  b.outerHTML = starBtn(b.dataset.st, b.dataset.k, label);
  pst.querySelector(`button.star[data-k="${{CSS.escape(b.dataset.k)}}"]`)?.focus();
}});
document.getElementById("filter").addEventListener("change", apply);
document.getElementById("party").addEventListener("change", apply);
document.getElementById("find").addEventListener("input", apply);
document.getElementById("partyInfo").addEventListener("click", (ev) => {{
  const note = document.getElementById("partyNote"), open = note.classList.toggle("hidden") === false;
  ev.currentTarget.setAttribute("aria-expanded", String(open));
}});
// Firefox and Safari keep a menu's choice when the page is reloaded or reached with Back.
// apply() also draws the panel's party bar (and keeps the menus' choices after a reload or Back).
apply();
setChart();
</script>
</body>
</html>
"""
    return body, {"bills": intro_n, "states": in_states, "laws": laws_n, "by": {st: by_entry(v) for st, v in by.items()}}, open_


def by_entry(v):
    """summary.json's count for a state: [bills, laws], then its bills by sponsors' party, D, B, R (the rest have none),
    trailing zeros left off (home.html's tiles draw the party bar from them)."""
    sp = split(v[2])[:3]
    while sp and not sp[-1]:
        sp.pop()
    return [v[0], v[1], *sp]


def main(site):
    from datetime import date
    states, congress = load(site), load(site, congress=True)
    if not states:
        print("issues: no state has data/issues_<session>.json; not built")
        return
    default = date.today().year
    upcoming_years = {f["session"] for d in states.values() for f in d["files"] if f.get("upcoming")}
    # Every year from the first that nearly all states have data for (90%: most states' pages begin with 2023, New
    # York's with 2017), through this year, and next year once any state lists prefiled bills.
    have = lambda y: sum(1 for d in states.values() if any(covers(f, y) for f in d["files"]))
    first = default - 1
    while have(first - 1) >= 0.9 * len(states):
        first -= 1
    years = list(range(first, default + 1)) + ([default + 1] if default + 1 in upcoming_years else [])
    os.makedirs(os.path.join(site, "issues"), exist_ok=True)
    summary, opened = [], {}
    # The legislatures that met each year but whose data for it isn't on the site (the front page's map marks them "no
    # data", apart from "no session").
    nodata = {str(y): sorted(no_data(states, y)) for y in years if y <= default}
    for issue in issues.ISSUES:
        os.makedirs(os.path.join(site, "issues", issue["id"]), exist_ok=True)
        per_year, panel = {}, {}
        for y in years:
            # The front page map's panel (home.html): each state's bills that year, one line each, laws first.
            by, _, _ = year_view(issue["id"], states, y)
            # Congress: its own entries, apart from the states' totals ("N bills in M states" leaves it out).
            us_by, us_open, _ = year_view(issue["id"], congress, y) if congress else ({}, set(), {})
            panel[str(y)] = {st: [[shown(b[2], b[10] if len(b) > 10 else (), st), b[3], (b[9].get(issue["id"]) if len(b) > 9 else "") or "", b[4],
                                   link(f, b[2])[len("../../"):], b[6],
                                   # For the star (home.html): the bill's number, its session and its last action's
                                   # date, which make its watchlist entry, as on the state's own page.
                                   b[2], f["session"], b[5],
                                   # The sponsors' party, and whether it counts in the year's bills and laws (the map
                                   # follows the panel's "Sponsor's party" menu).
                                   party(b), int(new), int(passed)]
                                  for f, b, new, passed in sorted(sorted(rows, key=lambda x: x[1][5], reverse=True),
                                                                  key=lambda x: (x[1][4] != 5, -x[1][4]))]
                             for st, (n, laws, rows) in {**by, **us_by}.items()}
            page, info, open_ = issue_page(issue, states, y, years, default, y > default, congress)
            name = "index.html" if y == default else f"{y}.html"
            open(os.path.join(site, "issues", issue["id"], name), "w", encoding="utf-8").write(page)
            if us_by:
                info["by"]["us"] = by_entry(us_by["us"])
            per_year[str(y)] = info
            opened[str(y)] = sorted(open_ | us_open)
        json.dump(panel, open(os.path.join(site, "issues", issue["id"], "bills.json"), "w"), ensure_ascii=False,
                  separators=(",", ":"))
        summary.append({"id": issue["id"], "name": issue["name"], "group": issue.get("group", ""),
                        "short": SHORT.get(issue["id"], issue["name"]), "y": per_year})
    # The issues by group (issues.GROUPS), as in the front page's menu.
    def card(s):
        y = s["y"][str(default)]
        return (f'<li><a href="{s["id"]}/"><b>{e(s["name"])}</b><span class="nums"><span>{y["bills"]:,} bill{"" if y["bills"] == 1 else "s"} in '
                f'{y["states"]} state{"" if y["states"] == 1 else "s"}</span><span class="l">{y["laws"]:,} became law</span></span></a></li>')
    # Alphabetical within each group.
    abc = sorted(summary, key=lambda s: s["name"].lower())
    cards = "".join(f'<h2>{e(g)}</h2><ul class="cards">{"".join(card(s) for s in abc if s["group"] == g)}</ul>'
                    for g in issues.GROUPS if any(s["group"] == g for s in summary))
    cards += "".join(card(s) for s in abc if s["group"] not in issues.GROUPS) and \
        f'<h2>Other</h2><ul class="cards">{"".join(card(s) for s in abc if s["group"] not in issues.GROUPS)}</ul>'
    lede = "The same subjects in every state legislature: how many bills, where, and which became law."
    index = HEAD.format(title="Issues across the states", desc=lede, css=css(),
                        meta=site_meta.tags("Issues across the states · State Bill Tracker", lede, site_meta.root() + "issues/")) + f"""
<p class="crumbs"><a href="../">State Bill Tracker</a></p>
<h1>Issues across the states</h1>
<p class="lede">The same subjects in every state legislature: how many bills, where, and which became law.</p>
{cards}
<footer>Counts are for {default} ({len(states)} states; Congress is on each issue&rsquo;s page, apart from the states). Bills are found by the words in their titles and summaries; see each issue's page for what counts.</footer>
</main>
</body>
</html>
"""
    open(os.path.join(site, "issues", "index.html"), "w", encoding="utf-8").write(index)
    json.dump({"years": years, "default": default, "open": opened, "nodata": nodata, "groups": issues.GROUPS, "issues": summary},
              open(os.path.join(site, "issues", "summary.json"), "w"), ensure_ascii=False)
    print("issues:", ", ".join(f"{s['name']} {s['y'][str(default)]['bills']}" for s in summary), "; years", years)


if __name__ == "__main__":
    main(sys.argv[1])
