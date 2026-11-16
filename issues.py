"""National issues: which bills, in every state, are about the same subject (notes/issues-draft.md; the owner's answers
2026-11-15). A bill is about an issue when its title, summary or "What it does" text matches one of the issue's rules.

A rule is a list of patterns that must all appear (the first is the anchor; the others within WINDOW characters of it,
so a long text doesn't match on words pages apart), and a list it must not have in that window. Patterns are regular
expressions matched without regard to case, except those starting "(?-i)"; one starting "!" is an exclusion for that
rule alone. Bills for one city or county (narrow
"place") and placeholder bills (shell) are left out. `filters` are the subsets an issue's page offers (AI: deepfakes,
chatbots ...); a bill can be in several.

A match in the title or summary counts; so does one in a short "What it does" (under SHORT characters); a longer one
needs two mentions (budget and omnibus bills mention a subject once in passing; checked 2026-11-15).

`issues_of(head, body)` gives the issue ids a bill matches (head: title and summary; body: "What it does");
`filters_of(issue, text)` its filters.
"""
import re

WINDOW = 400
# The menu's groups, in order (the owner's choice 2026-11-15); each issue is in one.
GROUPS = ["Technology", "Schools", "Health", "Housing and taxes", "Work and the economy", "Environment and energy",
          "Rights and public safety", "Elections"]
SHORT = 1500

# Shared exclusions for the second ten's rules.
# Tenants of shops, offices and farms, and "tenant improvements" (a construction term): not renting a home.
NOT_HOMES = r"!\b(?:commercial (?:tenants?|leases?|landlords?|propert\w*|space|courts?|rental\w*)|tenant improvements?|storefronts?|agricultural (?:land|leases?|tenants?|assets?)|farm(?:land| leases?| tenants?)|beginning farmers?|third-party tenants?|owners and any tenants)\b"
# Hunting seasons and licenses: firearms bills, but not about gun laws.
HUNTING = r"!\b(?:deer|turkeys?|bears?|antlerless|archery|crossbows?|muzzleloaders?|hunting seasons?|firearms? seasons?|game animals?|trapping|wildlife code|hunter (?:safety|education)|hunting licen\w*|rod and gun clubs?)\b"

ISSUES = [
    {"id": "datacenters", "group": "Technology", "name": "Data centers",
     "rules": [[r"\bdata ?cent(?:er|re)s?\b"], [r"\bhyperscale"], [r"\bhigh[- ]performance computing\b"],
               [r"\b(?:large|high)[- ]loads?\b", r"!\b(?:vehicles?|trailers?|trucks?|highways?|lanes?)\b"],
               [r"\b(?:large|high)[- ](?:energy[- ]use|energy[- ]demand|energy|use|load[- ]factor)(?: electric)? (?:facilit\w+|customers?|users?|consumers?)\b"]],
     # Not call centers ("international call or data centers": Kentucky HB 508 of 2026, on veterans' benefits
     # consultants) or where a company keeps people's data.
     "none": [r"\bstate data cent(?:er|re)", r"\bconsolidat\w*\b.{0,60}\bdata cent", r"\bdata cent(?:er|re)s? (?:services|consolidation)\b",
              r"\bcall (?:or|and|centers? (?:or|and)) data cent", r"\b(?:international|overseas|offshore|foreign) data cent"]},
    {"id": "pfas", "group": "Environment and energy", "name": "PFAS (“forever chemicals”)",
     "rules": [[r"\bPFAS\b"], [r"perfluoro"], [r"polyfluoro"], [r"perfluorinated"], [r"\bforever chemicals?\b"],
               [r"\bPFOA\b"], [r"\bPFOS\b"], [r"\bfire[- ]?fighting foams?\b"], [r"(?-i)\bAFFF\b"],
               [r"\baqueous film[- ]forming foam"],
               [r"\b(?:turnout gear|firefighters?'? (?:personal )?protective (?:equipment|clothing))\b", r"\b(?:chemicals?|toxic|substances?)\b"]]},
    {"id": "ai", "group": "Technology", "name": "Artificial intelligence",
     "rules": [[r"\bartificial intelligence\b"], [r"\bgenerative (?:AI|artificial)"], [r"\bAI[- ]generated\b"],
               [r"(?-i)\bAI\b"], [r"\bdeep ?fakes?\b"], [r"\bsynthetic media\b"],
               [r"\bdigitally (?:altered|fabricated|manipulated|created)\b", r"\b(?:image|video|audio|likeness|depiction|recording)s?\b"],
               [r"\bdigital (?:replicas?|likeness(?:es)?)\b"], [r"\bsynthetic (?:sexual |intimate |explicit )?(?:images?|imagery|videos?)\b"],
               [r"\bpricing algorithms?\b"], [r"\bchat ?bots?\b"], [r"\bautomated decision(?:[- ]making)? (?:tools?|systems?)\b"],
               [r"\balgorithmic discrimination\b"]],
     "none": [r"\binsemination\b"],
     "filters": {"Deepfakes and elections": [r"\bdeep ?fake", r"\bsynthetic media\b", r"\bdigitally (?:altered|fabricated|manipulated|created)\b", r"\belection"],
                 "Chatbots": [r"\bchat ?bots?\b", r"\bcompanion\b"],
                 "Hiring, insurance and decisions": [r"\bautomated decision", r"\balgorithmic discrimination\b", r"\bemploy", r"\bhiring\b", r"\binsur"],
                 "Government use": [r"\bstate agenc", r"\bgovernmental? (?:entit|agenc|bod|unit)", r"\bpublic (?:bod|entit|agenc)"]}},
    {"id": "kidsonline", "group": "Technology", "name": "Children online and social media",
     "filters": {"Age checks for adult websites": [r"\bpornograph", r"\bharmful (?:to minors|material)\b", r"\badult[- ](?:only )?(?:websites?|content|material)\b", r"\bsexual material\b"],
                 "Social media": [r"\bsocial (?:media|networking)\b"], "App stores": [r"\bapp stores?\b"],
                 "Design and privacy codes": [r"\bage[- ]appropriate design\b", r"\bkids code\b", r"\b(?:data|privacy)\b"]},
     "rules": [[r"\bsocial (?:media|networking)\b", r"\b(?:minors?|child|children|teens?|teenagers?|under (?:the age of )?1[3-8]|age of 1[3-8]|parents?|youth)\b"],
               [r"\bage verification\b", r"\b(?:websites?|online|internet|apps?|applications?|platforms?)\b",
                r"!\b(?:alcohol|tobacco|vap(?:e|or|ing)|nicotine|firearms?|lottery|cannabis|marijuana|liquor|wager\w*|gaming|gambling|nitrite)\b"],
               [r"\b(?:online (?:services?|platforms?|products?)|digital services?)\b", r"\b(?:minors?|child|children|teens?|kids)\b"],
               [r"\bharmful (?:to minors|material)\b", r"\b(?:online|internet|websites?|digital|apps?)\b"],
               [r"\bage[- ]appropriate design\b"], [r"\bapp stores?\b", r"\b(?:minors?|age|parent)"]]},
    {"id": "phones", "group": "Schools", "name": "Phones in schools",
     "rules": [[r"\b(?:cell(?:ular)? ?(?:tele)?phones?|smart ?phones?|wireless (?:communication|telecommunication)s? devices?|personal (?:electronic|communication|telecommunications?) devices?|(?:mobile|wireless|portable electronic|internet[- ]enabled|electronic|electronic telecommunications?) devices?|phone[- ]free)\b",
                r"\b(?:schools?|students?|classrooms?|instructional (?:time|day))\b",
                r"\b(?:use|uses|using|possess\w*|prohibit\w*|ban|bans|banned|polic(?:y|ies)|restrict\w*|free|limit\w*|access)\b",
                r"!\b(?:recycl\w*|e-?waste|audits?)\b"]],
     "none": [r"\b(?:stopped|passing a) school bus", r"\bdistrict[- ]owned\b", r"\bwhile driving\b", r"\boperat\w* a (?:motor )?vehicle\b", r"\bbus drivers?\b", r"\bschool zones?\b"]},
    {"id": "housing", "group": "Housing and taxes", "name": "Housing supply and zoning",
     "rules": [[r"\baccessory dwelling"], [r"(?-i)\bADUs?\b"], [r"\bmissing[- ]middle\b"], [r"\bsingle[- ]family zon"],
               [r"\b(?:duplex|triplex|fourplex|quadplex)(?:es)?\b"], [r"\bminimum lot sizes?\b"],
               [r"\bparking (?:minimums?|requirements?|mandates?)\b", r"\bhous"], [r"\bby[- ]right\b", r"\bhous"],
               [r"\bhousing (?:production|supply)\b"], [r"\bhousing elements?\b"], [r"\bmulti-?family\b", r"\bzon(?:e|ed|ing)\b"],
               [r"\bdensity\b", r"\bhousing\b", r"\bzon(?:e|ed|ing)\b"], [r"\bstarter homes?\b"], [r"\bmanufactured hous", r"\bzon"]]},
    {"id": "minwage", "group": "Work and the economy", "name": "Minimum wage",
     # Only bills that set or change a minimum wage (the owner's decision 2026-11-15): not ones paying for its cost or
     # setting other pay by it.
     "rules": [[r"\bminimum (?:hourly )?wages?\W+(?:\w+\W+){0,6}?(?:increas\w*|rais\w*|establish\w*|eliminat\w*|repeal\w*|"
                r"exempt\w*|modif\w*|chang\w*|adjust\w*|index\w*|phas\w*|decreas\w*|reduc\w*|cost[- ]of[- ]living|per hour|"
                r"preempt\w*|ordinances?|rates?|act|law|amendments?|\$\d)"],
               [r"\b(?:increas\w*|rais\w*|establish\w*|sets?|eliminat\w*|repeal\w*|exempt\w*|modif\w*|chang\w*|adjust\w*|"
                r"index\w*|decreas\w*|reduc\w*|local|state|preempt\w*|regulat\w*|tipped)\W+(?:\w+\W+){0,6}?minimum (?:hourly )?wages?\b"],
               [r"\bsubminimum wages?\b"], [r"\btipped (?:minimum )?(?:wages?|employees?|workers?)\b"],
               [r"\btip credits?\b"], [r"\btraining wages?\b"]],
     "none": [r"\btimes the (?:state |federal |applicable )?minimum (?:hourly )?wage\b", r"\bjur(?:y|ors?)\b",
              r"\b(?:state funds?|operating costs?|costs? associated|reimburse\w*|tax credits?|grants?|grant programs?|"
              r"income tax|sales and use tax|sales tax|taxable income)\b"]},
    {"id": "repair", "group": "Technology", "name": "Right to repair",
     "rules": [[r"\bright[- ]to[- ]repair\b"], [r"\bdevices? repair\b"], [r"\bfair repair\b"], [r"\bdigital electronic (?:equipment|products?)\b", r"\brepair"],
               [r"\bindependent repair\b", r"\b(?:parts|tools|documentation|diagnostic)"],
               [r"\brepair", r"\b(?:powered wheelchairs?|wheelchairs?|agricultural equipment|farm equipment)\b"]],
     "none": [r"\bbody shops?\b", r"\bmotor vehicle repair\b", r"\bauto(?:mobile|motive)? repair\b"]},
    {"id": "betting", "group": "Work and the economy", "name": "Sports betting and online gambling",
     "rules": [[r"\bsports (?:wagering|betting|wagers?|pools?|gaming)\b"], [r"\bsportsbooks?\b"], [r"\bi-?gaming\b"],
               [r"\binternet (?:gambling|casino)"], [r"\b(?:internet|online) gaming\b", r"\b(?:wager\w*|casinos?|gambl\w*|bets?|betting)\b"],
               [r"\bonline (?:casino|gambling|poker|lottery|sports)"],
               [r"\bsweepstakes casino"], [r"\bsweepstakes\b", r"\bgam(?:ing|bling|es)\b"],
               [r"\bfantasy (?:sports|contests?)\b"], [r"\bprediction markets?\b"]],
     "none": [r"\braffles?\b", r"\bbingo\b"]},
    {"id": "drugcosts", "group": "Health", "name": "Prescription drug costs",
     "rules": [[r"\binsulin\b", r"\b(?:costs?|prices?|pricing|co-?pay(?:ment)?s?|cost[- ]sharing|caps?|capped|out-of-pocket|affordab)"],
               [r"\bprescription drug affordability\b"], [r"\bpharmacy benefits? managers?\b"], [r"(?-i)\bPBMs?\b"],
               [r"\bdrug pric(?:e|es|ing)\b"], [r"\b(?:prescription )?drug (?:costs?|affordability)\b"],
               [r"\bprescription drugs?\b", r"\b(?:cost[- ]sharing|co-?pay(?:ment)?s?|out-of-pocket)\b"], [r"\b340B\b"]]},
    # The second ten (2026-11-15; notes/issues-check.md).
    {"id": "abortion", "group": "Health", "name": "Abortion",
     "rules": [[r"\babortions?\b"], [r"\bterminat\w* (?:of )?(?:a |the |her )?pregnanc", r"!\b(?:miscarriage|childbirth|leave of absence)\b"], [r"\bmifepristone\b"], [r"\bmisoprostol\b"],
               [r"\bfetal heartbeat\b"], [r"\breproductive (?:freedom|rights|autonomy|liberty)\b"], [r"\blegally protected health care\b"],
               # Shield laws: protecting providers and patients from other states' subpoenas and prosecutions.
               [r"\breproductive (?:health ?care|health services)\b", r"\b(?:shield\w*|subpoena\w*|extradit\w*|out[- ]of[- ]state|interstate|another state|legally protected)\b"],
               [r"\b(?:crisis pregnancy|pregnancy (?:resource|help|care|support)) cent(?:er|re)s?\b"]],
     "filters": {"Bans and limits": [r"\bban\b", r"\bprohibit", r"\brestrict", r"\bheartbeat\b", r"\bgestation", r"\bweeks\b", r"\bcriminal", r"\bpenalt"],
                 "Access and protections": [r"\bright to\b", r"\bprotect", r"\bshield\b", r"\baccess\b", r"\breproductive (?:freedom|rights|autonomy|liberty|health care)\b", r"\bcoverage\b"],
                 "Medication abortion": [r"\bmifepristone\b", r"\bmisoprostol\b", r"\babortion[- ]inducing\b", r"\b(?:medication|chemical) abortion", r"\babortion pills?\b"],
                 "Ballot measures": [r"\bconstitution", r"\bballot\b", r"\breferendum\b", r"\bvoters\b"]}},
    {"id": "firearms", "group": "Rights and public safety", "name": "Firearms",
     "rules": [# "Other than by the discharge of a firearm" is the criminal code's way of setting firearms aside.
               [r"\bfirearms?\b", r"!\balcohol,? tobacco,? (?:and )?firearms\b", r"!\bother than (?:by )?(?:the )?discharg\w* of a firearm\b", HUNTING], [r"\bhandguns?\b"], [r"\b(?:rifles?|shotguns?|pistols?)\b", HUNTING],
               [r"\bguns?\b", r"!\b(?:nail|staple|spray|radar|glue|heat|paint|tattoo|speed|caulk|grease|stun) guns?\b|\bgun clubs?\b"],
               [r"\bammunition\b"], [r"\bconcealed (?:carry|weapons?|handguns?)\b"], [r"\bextreme risk protecti"], [r"\bred flag\b"],
               [r"\bbump[- ]stocks?\b"], [r"\bmachine ?guns?\b"], [r"\bassault weapons?\b"], [r"\bsecond amendment\b"], [r"\bgunfire\b"], [r"\bshooting ranges?\b"],
               [r"\b(?:carry|carrying|carries|concealed|possession of|possessing|possess) (?:a |of )?(?:concealed |deadly |dangerous )?weapons?\b"],
               [r"\b(?:permitless|constitutional) carry\b|\bright to carry\b|\bpermits? to carry\b"]],
     "filters": {"Carry permits": [r"\bcarry", r"\bconcealed\b"],
                 "Background checks and purchase rules": [r"\bbackground checks?\b", r"\bwaiting periods?\b", r"\bpurchas", r"\btransfers?\b", r"\bdealers?\b"],
                 "Red flag laws": [r"\bextreme risk", r"\bred flag\b", r"\brisk protection orders?\b"],
                 "Ghost guns and devices": [r"\bghost guns?\b", r"\bunserialized\b", r"\bprivately made\b", r"\b3-?D[- ]print", r"\bbump[- ]stock", r"\bmachine ?guns?\b", r"\bauto sears?\b", r"\bconversion devices?\b", r"\brapid[- ]fire\b", r"\bsilencers?\b", r"\bsuppressors?\b", r"\bframes? or receivers?\b"],
                 "Firearms in schools": [r"\bschools?\b", r"\bcampus"]}},
    {"id": "vouchers", "group": "Schools", "name": "School vouchers and education savings accounts",
     "rules": [[r"\bvouchers?\b", r"\b(?:schools?|tuition|students?)\b", r"!\b(?:housing|rent|rental|child ?care|day ?care|section 8|food|meals?|travel|bus|buses|vehicles?|trucks?|electric|plates?)\b"],
               [r"\beducation(?:al)? (?:savings|scholarship|freedom|opportunity) accounts?\b"], [r"\bempowerment scholarship"],
               [r"\bscholarship (?:granting|funding|tax credit)"], [r"\btax[- ]credit scholarships?\b"],
               # "School choice" also means choosing among public schools: only with private schooling in the same passage.
               [r"\bschool choice\b", r"\b(?:private|nonpublic|scholarships?|vouchers?|accounts?|tax credits?|tuition)\b",
                r"!\b(?:public school choice|interdistrict|inter-district|open enrollment|choice districts?|transfers?)\b"],
               # Wisconsin's bills on all schools name "a private school participating in a parental choice program" beside
               # "an independent charter school".
               [r"\bparental choice\b", r"!\bindependent charter schools?\b"], [r"\beducation(?:al)? (?:improvement |opportunity )?tax credits?\b"], [r"\bscholarship organizations?\b"],
               [r"\b(?:Utah Fits All|EdChoice|Educational Choice Scholarship)"],
               [r"\btuition tax credits?\b", r"!\b(?:colleges?|universit\w*|postsecondary|higher education)\b"],
               # West Virginia's education savings accounts; Georgia's and Tennessee's HOPE scholarships pay for college.
               [r"\bHope Scholarship (?:Program|Board|Act|accounts?)\b", r"!\b(?:colleges?|universit\w*|postsecondary|higher education|lottery)\b"],
               [r"\bscholarships?\b", r"\b(?:nonpublic|private|parochial|participating|religious) (?:schools?|elementary|secondary)\b",
                r"!\b(?:colleges?|universit\w*|postsecondary|higher education|community college|dual (?:enrollment|credit)|teach\w*|work obligation|independent charter schools?)\b"]]},
    {"id": "voting", "group": "Elections", "name": "Voting and elections",
     # How people vote and how elections are run. Not campaign finance, local election dates or district lines.
     "rules": [[r"\bvoter (?:ID|identification|registration|rolls?|lists?|fraud|intimidation|suppression|participation|access|eligibility|challenges?)\b"],
               # "registered voters" near a petition is usually a local referendum on something else (Louisiana's fluoridation
               # elections): recalls, initiatives and candidates' petitions are caught by their own rules.
               [r"\bregist\w* (?:to vote|voters?)\b", r"!\bpetition"], [r"\brecall (?:petitions?|elections?)\b"],
               [r"\binitiatives? and referend"], [r"\b(?:candidate|nominating|nomination) petitions?\b"], [r"\b(?:proof of )?citizenship\b", r"\b(?:voters?|vote|voting)\b"],
               [r"\babsentee (?:ballots?|voting|voters?)\b"], [r"\bmail(?:-in| in)? (?:ballots?|voting)\b"], [r"\bvote[- ]by[- ]mail\b"], [r"\bballots? by mail\b"], [r"\bvoted by mail\b"], [r"\bballot casting\b"],
               [r"\bstraight[- ](?:ticket|party) voting\b"], [r"\bpreferential voting\b"], [r"\brecanvass"], [r"\bnational popular vote\b"],
               [r"\b(?:illegal voting|vote fraud|voting fraud)\b"], [r"\b(?:youth voting|preregist\w*)\b"],
               [r"\b(?:early|advance|curbside|in-person) voting\b"],
               [r"\bballot (?:drop ?box\w*|drop-off|harvesting|collection|counting|tabulat\w*|curing|cure|security|images?|design|access|signatures?|envelopes?|processing|return|tracking|printing|marking)\b"],
               [r"\bvoting materials?\b"], [r"\bvoter (?:registrars?|guides?|assistance|education|qualifications?|verification|signatures?)\b"],
               [r"\bqualifications? (?:of|for) (?:voters|electors)\b"], [r"\brecounts?\b", r"\b(?:elections?|ballots?|votes?|candidates?)\b"],
               [r"\btabulat\w*\b", r"\b(?:ballots?|votes?|elections?)\b"], [r"\bcast vote records?\b"], [r"\brun-?off elections?\b"],
               [r"\b(?:voters?|vote|voting)\b", r"\b(?:incarcerat\w*|jail\w*|prison\w*|detained|felon\w*|convicted)\b"],
               [r"\bpolling (?:places?|locations?|sites?|hours)\b"], [r"\bpoll (?:watchers?|workers?|books?|challengers?|observers?)\b"],
               [r"\belection (?:officials?|workers?|judges?|administrat\w*|security|integrity|audits?|results?|equipment|machines?|crimes?|offenses?|fraud|interference|observers?|clerks?|inspectors?)\b"],
               [r"\bvoting (?:machines?|systems?|equipment|rights?|centers?|age|methods?|process)\b"], [r"\bright to vote\b"],
               [r"\branked[- ]choice\b"], [r"\binstant[- ]runoff\b"], [r"\bapproval voting\b"], [r"\brisk[- ]limiting\b"],
               [r"\bprovisional ballots?\b"], [r"\b(?:overseas|military) voters?\b"], [r"(?-i)\bUOCAVA\b"],
               [r"\b(?:open|closed|semi-closed|top[- ]two|nonpartisan|partisan) primar(?:y|ies)\b"], [r"\bprimary elections?\b", r"!\b(?:contributions?|campaign finance|political action committees?|expenditures?)\b"],
               [r"\bcanvass\w*\b", r"\b(?:elections?|ballots?|votes?)\b"], [r"\bballot initiatives?\b|\binitiative petitions?\b"],
               [r"\bsuffrage\b"], [r"\bdisenfranchis"]],
     # Not votes by a company's or cooperative's members, nor Mississippi's private bills restoring one person's right to
     # vote ("Suffrage; restore to Frankie Ward, Jr").
     "none": [r"\b(?:shareholders?|stockholders?|cooperatives?|homeowners'? associations?|condominiums?|voting (?:interests?|shares|stock|securities|power))\b",
              r"\brestore (?:the right of )?suffrage to (?!(?:persons|people|individuals|those|all|certain|any|felons|citizens|residents)\b)"],
     "filters": {"Voter ID": [r"\bvoter ID\b", r"\bidentification\b", r"\bphoto ID\b"],
                  "Mail and absentee voting": [r"\babsentee\b", r"\bmail(?:-in| in)? (?:ballots?|voting)\b", r"\bvote[- ]by[- ]mail\b", r"\bballots? by mail\b"],
                  "Voter registration": [r"\bregist\w* (?:to vote|voters?)\b", r"\bvoter (?:registration|rolls?|lists?)\b", r"\bsame[- ]day registration\b"],
                  "Election administration and security": [r"\baudits?\b", r"\btabulat", r"\bequipment\b", r"\bmachines?\b", r"\bsecurity\b", r"\bintegrity\b", r"\belection (?:officials?|workers?|judges?|administrat|clerks?)", r"\bpoll (?:watchers?|workers?|books?)", r"\bcanvass", r"\bcertif", r"\bdrop ?box"]}},
    {"id": "immigration", "group": "Rights and public safety", "name": "Immigration enforcement",
     # Working with federal immigration enforcement (287(g), detainers, sanctuary policies), state immigration crimes,
     # checks of immigration status (E-Verify), and what a person's status allows: benefits, licenses, in-state tuition.
     # Not noncitizen voting (Voting and elections), refugee services or foreign land ownership.
     "rules": [# Not "regardless of ... immigration status" in passing, nor a list of protected classes (hate crimes).
               [r"\bimmigration\b", r"!\b(?:immigration (?:and )?(?:naturalization|attorneys?|lawyers?)|citizenship and immigration services)\b",
                r"!\b(?:regardless|irrespective|without regard)\W+(?:\w+\W+){0,8}?immigration status\b", r"!\b(?:creed|ancestry|sexual orientation)\b",
                r"!\bthreat\w*\W+(?:\w+\W+){0,4}?immigration status\b"],
               [r"(?-i)\bICE\b", r"!\b(?:engines?|vehicles?|combustion|hockey|rinks?)\b"], [r"\b287 ?\(g\)"],
               [r"\bsanctuary\b", r"\b(?:cit(?:y|ies)|jurisdictions?|polic(?:y|ies)|state|count(?:y|ies)|immigra\w*)\b",
                r"!\b(?:second amendment|firearms?|wildlife|animals?|birds?|marine|unborn|life)\b"],
               [r"\bundocumented\b"], [r"\b(?:illegal|unauthorized|unlawful|criminal) aliens?\b"],
               [r"\baliens?\b", r"\b(?:unlawfully|lawfully|illegally) present\b"], [r"\baliens?\b", r"\b(?:medical assistance|medicaid|public benefits?|eligib\w*|immigra\w*)\b", r"!\b(?:insur\w*|species|invasive)\b"],
               [r"\bcitizenship status\b", r"!\b(?:vot\w*|electors?|elections?)\b"], [r"\b(?:unlawfully|not lawfully|illegally) present\b"],
               [r"\blawful (?:presence|status)\b"], [r"\bE-?Verify\b"], [r"(?-i)\bDACA\b"], [r"\bdeferred action\b", r"\bchildhood arrivals\b"],
               [r"\bnoncitizens?\b", r"!\b(?:vot\w*|elections?|ballots?|real property|real estate|land|agricultural land)\b"], [r"\bdeport\w*\b"],
               [r"\b(?:human smuggling|smuggling of (?:persons|individuals|people|aliens))\b"], [r"\billegal (?:entry|re-?entry)\b"],
               [r"\bimmigrants?\b", r"\b(?:status|benefits?|eligib\w*|enforce\w*|detain\w*|detention|federal|legal services|tuition|licen[cs]es?)\b"]],
     # Domestic violence laws list threats about a person's immigration status among forms of coercive control,
     # and "nonresident alien" is a tax term.
     "none": [r"\bcoercive control\b", r"\bnonresident aliens?\b"]},
    {"id": "tenants", "group": "Housing and taxes", "name": "Rent and tenants",
     "rules": [[r"\btenan(?:ts?|cy|cies)\b", r"!\b(?:tenants? in common|tenancy in common|tenancy by the entiret\w*|joint tenan\w*|life tenan\w*|tenancy at sufferance)\b", NOT_HOMES],
               [r"\blandlords?\b", r"!\b(?:employers|lenders|journalists),? (?:\w+,? )?(?:and )?landlords\b", NOT_HOMES], [r"\bevict\w*\b"], [r"\brent (?:control|stabiliz\w*|increases?|caps?|gouging|regulat\w*|limits?|hikes?|escrow|withholding)\b"],
               [r"\brental (?:housing|units?|propert\w*|agreements?|applications?|assistance|dwellings?|apartments?)\b",
                r"!\b(?:short[- ]term|vacation|construct\w*|develop\w*|housing tax credits?|low[- ]income housing tax|financ\w*|loans?|solar|valuation|property tax\w*|vehicles?|cars?)\b", NOT_HOMES],
               [r"\bsecurity deposits?\b", r"\b(?:rent\w*|leases?|tenants?|landlords?|residential|dwellings?|apartments?)\b"],
               [r"\b(?:residential|apartment|dwelling) leases?\b"], [r"\bforcible entry and detainer\b"], [r"\bunlawful detainer\b"],
               [r"\bsummary (?:possession|ejectment)\b"], [r"\bwarranty of habitability\b"], [r"\bsquatt\w*\b", r"\b(?:remov\w*|evict\w*|unlawful\w*|occup\w*)\b"], [r"\blot rent\b"],
               [r"\bhousing choice vouchers?\b"], [r"\bsource of income\b", r"\b(?:housing|rent\w*|landlords?|tenants?)\b"]]},
    {"id": "proptax", "group": "Housing and taxes", "name": "Property tax relief",
     # Relief for homeowners and residents: homestead exemptions, caps on assessments and levies, circuit breakers,
     # freezes and deferrals for seniors, exemptions for veterans and people with disabilities. Not business property,
     # one organization's exemption, or tax administration (appeals, collection, sales).
     "rules": [[r"\bhomestead\w*\b", r"\b(?:exempt\w*|credits?|tax\w*|assess\w*|valuation|rebates?|deferr\w*|freez\w*)\b",
                r"!\b(?:creditors?|bankruptcy|execution|judgments?|probate|surviving spouse's allowance|homestead resorts?|cash value)\b"],
               [r"\bproperty tax(?:es)? (?:relief|rebates?|freez\w*|circuit breakers?|deferr\w*|refunds?|reductions?|caps?|limits?|limitations?|credits?|assistance)\b",
                # Not funds or acts named for relief that pay for school aid ("Property Tax Relief Fund to DOE"), levy-cap
                # exceptions, or farmland.
                r"!\b(?:exclusions?|exceptions?|exceed\w*|overrid\w*|adjust\w*|waiv\w*|cap calculations?|property tax relief (?:fund|act)|"
                r"education (?:aid|equity)|equalization aid|school aid|agricultur\w*|farm\w*|grocery|stores?|business(?:es)?|cancellations?)\b"],
               [r"\b(?:relief|rebates?|refunds?) (?:from|of|on) (?:residential )?property tax"],
               [r"\bcircuit[- ]breaker\b", r"\b(?:tax\w*|property|renters?|homeowners?)\b"],
               [r"\b(?:assessment|valuation) (?:caps?|limit\w*|freez\w*)\b", r"!\b(?:vehicles?|cars|watercraft|boats|adjust\w*|exclusions?|exceptions?|megaprojects?|renovat\w*|affordable housing|job creation)\b"],
               [r"\b(?:caps?|limit\w*) (?:on |the )?(?:annual )?(?:increases? in )?(?:the )?(?:assessed|taxable|appraised) (?:value|valuation)s?\b", r"!\b(?:vehicles?|cars|watercraft|boats|annex\w*|freeholders?)\b"],
               # A relief word next to "property tax" ("property tax exemption", "credit against ad valorem taxes"), for
               # homeowners, seniors, veterans or people with disabilities, and not for businesses or organizations.
               [r"\b(?:real )?(?:property|ad valorem) tax(?:es|ation)?\W+(?:\w+\W+){0,3}?(?:exempt\w*|credits?|relief|rebates?|refunds?|deduct\w*|deferr\w*|freez\w*|reduc\w*|caps?|limit\w*|abat\w*)|"
                r"\b(?:exempt\w*|credits?|relief|rebates?|refunds?|deduct\w*|deferr\w*|freez\w*|reduc\w*|caps?|limit\w*)\W+(?:\w+\W+){0,5}?(?:real )?(?:property|ad valorem) tax",
                r"\b(?:homestead|homeowners?|residential|residences?|dwellings?|owner[- ]occupied|seniors?|elderly|older|aged|65 years|veterans?|disabilit\w*|disabled|surviving spouses?|widow\w*|low[- ]income|fixed[- ]income|primary residence|principal residence)\b",
                r"!\b(?:business|commercial|industrial|manufactur\w*|equipment|machinery|data cent\w*|aircraft|pipelines?|tangible personal property|church\w*|clergy|nonprofit|charitable|religious|hospitals?|economic development|enterprise zones?|housing (?:accommodations|projects?|developments?|compan\w+|authorit\w+)|levy caps?|payments? in lieu of taxes|development projects?|hotels?)\b"],
               [r"\brenters?'? (?:credits?|rebates?|refunds?)\b"],
               [r"\b(?:eliminat\w*|abolish\w*|repeal\w*) (?:the |all )?(?:residential |real )?(?:property|ad valorem) tax(?:es|ation)?\b(?! (?:exemptions?|credits?|code|laws?|provisions|abatements?))"]],
     # New Jersey's Energy Tax Receipts Property Tax Relief aid goes to municipalities, not households.
     "none": [r"\benergy tax receipts\b"]},
    {"id": "transgender", "group": "Rights and public safety", "name": "Transgender people",
     "rules": [[r"\btransgender\b"],
               # "Gender identity" in a list of protected classes or data fields (parole factors, data brokers, demographic
               # forms) isn't about transgender people; a bill adding it to such a list is.
               [r"\bgender identity\b", r"!\b(?:race|racial|ethnicity|religion|national origin|ancestry|color|creed)\b",
                r"!\b(?:demographic\w*|data brokers?|collect\w* (?:and maintain |and report )?(?:data|information))\b"],
               [r"\b(?:add\w*|includ\w*|inserts?|protect\w*)\W+(?:\w+\W+){0,6}?gender identity\b", r"!\b(?:demographic\w*|data brokers?)\b"], [r"\bgender[- ](?:affirming|transition\w*|reassignment|dysphoria|expression|markers?|nonconforming)\b"],
               [r"\bsex[- ](?:reassignment|change)\b"], [r"\bpuberty[- ]block\w*\b"], [r"\bcross-sex\b"], [r"\bnon-?binary\b"],
               [r"\bbiological(?:ly)? (?:sex|males?|females?|wom[ae]n|m[ae]n|boys?|girls?)\b"], [r"\bsex (?:assigned |designated |observed )?at birth\b"],
               [r"\bsex designations?\b"], [r"\bwomen'?s bill of rights\b"], [r"\b(?:women|girls)'?s? sports\b", r"!\bprofessional women'?s sports\b"],
               [r"\b(?:athletic|sports?|interscholastic|intercollegiate) (?:teams?|events?|competitions?)\b", r"\b(?:designated for|based on|according to|of the opposite) (?:biological )?(?:sex|females?|males?|girls|boys|women|men)\b"],
               [r"\b(?:restrooms?|bathrooms?|locker rooms?|changing (?:rooms?|facilities)|showers?)\b", r"\b(?:single[- ]sex|multiple[- ]occupancy|opposite sex|biological|sex)\b",
                r"!\b(?:baby|diaper|infant)"],
               [r"\bpronouns?\b", r"!\breplac\w* (?:certain |the )?pronouns\b"],
               # Only restrooms: not Kentucky's "gender-neutral language" clean-up bills.
               [r"\b(?:all-gender|gender-neutral|gender-inclusive) (?:restrooms?|bathrooms?|facilities|toilets?|changing|locker)"], [r"\b(?:preferred|chosen) names?\b", r"\b(?:students?|schools?|employees?|gender)\b"]],
     "filters": {"Sports": [r"\bsports?\b", r"\bathlet", r"\bteams?\b"],
                 "Health care": [r"\bgender[- ](?:affirming|transition|reassignment|dysphoria)", r"\bpuberty", r"\bhormon", r"\bsurg", r"\bhealth care\b", r"\bmedical\b"],
                 "Birth certificates and IDs": [r"\bbirth certificates?\b", r"\bdriver'?s licen", r"\bidentification cards?\b", r"\bsex designations?\b", r"\bgender markers?\b", r"\bvital records?\b"],
                 "Bathrooms and locker rooms": [r"\brestrooms?\b", r"\bbathrooms?\b", r"\blocker rooms?\b", r"\bchanging (?:rooms?|facilities)\b"],
                 "Schools": [r"\bschools?\b", r"\bstudents?\b", r"\bpronouns?\b"],
                 "Discrimination protections": [r"\bdiscriminat", r"\bcivil rights\b", r"\bhuman rights\b", r"\bhate crimes?\b"]}},
    {"id": "dei", "group": "Rights and public safety", "name": "Diversity, equity and inclusion",
     # DEI offices, officers, training, statements and plans, bans on them, and the nearby fights the same bills take up:
     # implicit bias training, "divisive concepts" and critical race theory, affirmative action and preferential treatment.
     "rules": [[r"\bdiversity,? equity,? (?:and )?inclusion\b"], [r"\bequity,? diversity,? (?:and )?inclusion\b"], [r"(?-i)\bDEI\b"],
               [r"\bdiversity,? (?:and|&)? ?inclusion\b", r"!\bsupplier diversity\b"], [r"\b(?:racial|ethnic|workforce|faculty|educator|teacher|judicial) diversity\b"],
               [r"\bracial equity\b", r"!\b(?:bidders?|purchase contracts?|procurement)\b"], [r"\b(?:implicit|unconscious) bias training\b"],
               # New Jersey's Chief Diversity Officer runs the state's contracting programs for minority-, women- and
               # disability-owned businesses: supplier diversity isn't counted, nor school enrollment "diversity plans".
               [r"\bdiversity (?:statements?|officers?|offices?|training|programs?|initiatives?|plans?|pledges?)\b",
                r"!\b(?:business(?:es)?|contracts?|contracting|procurement|enrollment|film production)\b"],
               [r"\binclusion (?:officers?|offices?)\b"], [r"\bdivisive concepts?\b"], [r"\bcritical race theory\b"],
               [r"\baffirmative action\b", r"!\b(?:affirmative action by|minority business\w*)\b"],
               [r"\bpreferential treatment\b", r"\b(?:race|sex|color|ethnicity|national origin)\b"]]},
    {"id": "cannabis", "group": "Rights and public safety", "name": "Cannabis",
     "rules": [[r"\bcannabis\b"], [r"\bmarijuana\b"], [r"\bmarihuana\b"], [r"(?-i)\bTHC\b"], [r"\btetrahydrocannabinol"], [r"\bdelta[- ]?[89]\b"],
               [r"\bhemp[- ]derived\b"], [r"\bcannabinoids?\b"], [r"(?-i)\bCBD\b"], [r"\bcannabidiol\b"],
               [r"\bhemp\b", r"\b(?:intoxicat\w*|consumable|ingestible|edibles?|beverages?|smokable|inhal\w*)\b"],
               [r"\bhemp products?\b", r"!\b(?:industrial hemp|fiber|grain)\b"], [r"\bdispensar(?:y|ies)\b", r"\b(?:retail|adult[- ]use|on-site consumption)\b"]],
     "filters": {"Medical cannabis": [r"\bmedical (?:cannabis|marijuana|marihuana)\b", r"\bmedicinal\b", r"\bqualifying (?:patients?|conditions?)\b"],
                 "Hemp-derived THC": [r"\bhemp\b", r"\bdelta[- ]?[89]\b", r"\bintoxicating\b"],
                 "Expungement": [r"\bexpunge", r"\bsealing\b", r"\bseal (?:the )?records?\b"]}},
]


def _compile(p):
    if p.startswith("(?-i)"):
        return re.compile(p[5:])
    return re.compile(p, re.I)


for _issue in ISSUES:
    _issue["_rules"] = [([_compile(p) for p in rule if not p.startswith("!")],
                         [_compile(p[1:]) for p in rule if p.startswith("!")]) for rule in _issue["rules"]]
    _issue["_none"] = [_compile(p) for p in _issue.get("none", [])]
    _issue["_filters"] = {k: [_compile(p) for p in v] for k, v in _issue.get("filters", {}).items()}
BY_ID = {i["id"]: i for i in ISSUES}


def _hit(issue, text):
    """The first window of text where one of the issue's rules matches and no exclusion appears, or None."""
    for need, avoid in issue["_rules"]:
        for m in need[0].finditer(text):
            a, b = max(0, m.start() - WINDOW), m.end() + WINDOW
            win = text[a:b]
            if all(p.search(win) for p in need[1:]) and not any(p.search(win) for p in issue["_none"] + avoid):
                return win
    return None


def _hits(issue, text, enough):
    """How many mentions of the issue (anchor matches whose window passes) the text has, counting up to `enough`."""
    found = set()
    for need, avoid in issue["_rules"]:
        for m in need[0].finditer(text):
            win = text[max(0, m.start() - WINDOW):m.end() + WINDOW]
            if all(p.search(win) for p in need[1:]) and not any(p.search(win) for p in issue["_none"] + avoid):
                found.add(m.start())
                if len(found) >= enough:
                    return len(found)
    return len(found)


def issues_of(head, body=""):
    """The ids of the issues a bill matches: in its title and summary (head), or twice in its "What it does" (body)."""
    need = 1 if len(body) < SHORT else 2
    return [i["id"] for i in ISSUES if _hit(i, head) or (body and _hits(i, body, need) >= need)]


def snippet(issue_id, text):
    """The window that matched, for reading matches over."""
    return _hit(BY_ID[issue_id], text)


def filters_of(issue_id, text):
    return [k for k, ps in BY_ID[issue_id]["_filters"].items() if any(p.search(text) for p in ps)]


def excerpt(issue_id, head, body="", limit=220):
    """The sentence (or clause between semicolons) where the issue matched, for showing why a bill with a bare title
    ("Wages") is on the issue: from the summary if it matched there, else from "What it does". A leading statute
    reference ("Amend KRS 337.275 to raise ...") is dropped. "" when nothing matched."""
    issue = BY_ID[issue_id]
    for text in (head, body):
        if not text:
            continue
        for need, avoid in issue["_rules"]:
            for m in need[0].finditer(text):
                win = text[max(0, m.start() - WINDOW):m.end() + WINDOW]
                if not all(p.search(win) for p in need[1:]) or any(p.search(win) for p in issue["_none"] + avoid):
                    continue
                a = max(text.rfind(". ", 0, m.start()), text.rfind("; ", 0, m.start()))
                b = min([x for x in (text.find(". ", m.end()), text.find("; ", m.end())) if x >= 0] or [len(text)])
                s = re.sub(r"\s+", " ", text[a + 2 if a >= 0 else 0:b]).strip()
                s = re.sub(r"^(?:[Aa]mends?|[Cc]reates?|[Rr]epeals?)(?: (?:a )?new sections? of)? [A-Z]{2,5} (?:Chapter )?[\d.,A-Z\s-]+?(?:and [\d.]+ )?to ", "", s)
                if len(s) > limit:
                    s = s[:limit].rsplit(" ", 1)[0] + " …"
                return s[:1].upper() + s[1:]
    return ""
