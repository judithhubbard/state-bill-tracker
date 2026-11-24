"""National issues: which bills, in every state, are about the same subject (notes/issues-draft.md; the owner's answers
2026-11-15). A bill is about an issue when its title, summary or "What it does" text matches one of the issue's rules.

A rule is a list of patterns that must all appear (the first is the anchor; the others within WINDOW characters of it,
so a long text doesn't match on words pages apart), and a list it must not have in that window. Patterns are regular
expressions matched without regard to case, except those starting "(?-i)"; one starting "!" is an exclusion for that
rule alone. Bills for one city or county (narrow
"place") and placeholder bills (shell) are left out. `filters` are the subsets an issue's page offers (AI: deepfakes,
chatbots ...); a bill can be in several. `words` (optional) are a few other terms a visitor might type for the issue
in the front page's search ("forever chemicals", "7-oh"); they don't change which bills match.

A match in the title or summary counts; so does one in a short "What it does" (under SHORT characters); a longer one
needs two mentions (budget and omnibus bills mention a subject once in passing; checked 2026-11-15), or the issue's
`body` (three for a few issues, 2026-11-17).

`issues_of(head, body)` gives the issue ids a bill matches (head: title and summary; body: "What it does");
`filters_of(issue, text)` its filters.
"""
import re

WINDOW = 400
# The menu's groups, in order (the owner's choice 2026-11-15); each issue is in one.
GROUPS = ["Education", "Environment and energy", "Health", "Housing", "Taxes", "Jobs and workers", "Business and consumers", "Technology", "Social services", "Public safety and courts", "Rights", "Elections and government"]
SHORT = 1500

# Shared exclusions for the second ten's rules.
# Tenants of shops, offices and farms, and "tenant improvements" (a construction term): not renting a home.
NOT_HOMES = r"!\b(?:commercial (?:tenants?|leases?|landlords?|propert\w*|space|courts?|rental\w*)|tenant improvements?|storefronts?|agricultural (?:land|leases?|tenants?|assets?)|farm(?:land| leases?| tenants?)|beginning farmers?|third-party tenants?|owners and any tenants)\b"
# Hunting seasons and licenses: firearms bills, but not about gun laws.
HUNTING = r"!\b(?:deer|turkeys?|bears?|antlerless|archery|crossbows?|muzzleloaders?|hunting seasons?|firearms? seasons?|game animals?|trapping|wildlife code|hunter (?:safety|education)|hunting licen\w*|rod and gun clubs?)\b"

# Shared exclusions for the fifth ten's rules.
# Animals' and plants' vaccines and quarantines.
ANIMALS = r"!\b(?:rabies|animals?|livestock|dogs?|cats?|pets?|veterinar\w*|poultry|cattle|swine|horses?|equine|brucellosis|wildlife|herds?|deer|hens?|chickens?|birds?|fowl|flocks?)\b"
# A passing mention of a union contract in a bill about something else ("subject to the collective bargaining agreement").
NOT_CBA = r"!\b(?:subject to (?:the terms of )?(?:a |the |any |an |applicable |such )?(?:existing )?collective bargaining agreements?|(?:not|nothing) (?:\w+ ){0,6}?(?:impair|supersede|affect|alter|abrogate|diminish|interfere)\w* (?:\w+ ){0,6}?collective bargaining agreements?|unless otherwise provided (?:in|by) (?:a |the |an )?(?:applicable )?collective bargaining agreements?|(?:consistent|in accordance) with (?:any |the |a |an )?(?:applicable )?collective bargaining agreements?|(?:notwithstanding|except as provided in) (?:any |a |the )?collective bargaining agreements?|(?:governed by|covered by|pursuant to|according to|violation of|set by|in) (?:a |an |the |any )?(?:applicable |valid |existing )?collective bargaining agreements?|labor peace agreements?)\b"
# Water and sewer utilities' rates (not energy).
NOT_WATER = r"!\b(?:sewer\w*|wastewater|water (?:utilit\w*|rates?|bills?|service|compan\w*|districts?|authorit\w*|systems?|corporations?))\b"
# Federal laws that ran "during the COVID-19 public health emergency" (telehealth, Medicaid): not about the powers.
NOT_PHE = r"!\b(?:telehealth|telemedicine|Medicare|Medicaid|flexibilit\w*|tax credits?|unemployment|supply chains?|drug shortages?|reserves?|sick leave)\b"
# Youth job programs: not child labor rules.
NOT_YOUTHJOBS = r"!\b(?:summer youth|youth employment (?:and \w+ )?(?:funds?|funding|programs?|immersion|initiatives?|opportunit\w*|services|grants?)|youth (?:jobs?|workforce) (?:programs?|initiatives?|grants?))\b"
# Lists of emergencies ("disaster, war, acts of terrorism, riot or civil disorder").
NOT_DISASTER = r"!\b(?:tornado\w*|storms?|cyberterrorism|tumult|public disasters?|earthquakes?|floods?|hurricanes?|acts? of (?:war|God|terrorism)|natural (?:or man-made )?disasters?|epidemics?)\b"
# Tax, bid and assessment protests.
NOT_TAXPROTEST = r"!\b(?:bid protests?|protest(?:s|ed)? (?:of |against )?(?:an? |the )?(?:award|bid|assessment|valuation|tax\w*|appraisal|levy|annexation|rates?)|under protest|tax protests?|protest petitions?|appraisal review|procurement|solicitation|contract awards?)\b"

# Shared exclusions for the sixth batch's rules.
# Insurance that isn't health coverage, and coverage of one kind of care alone.
NOT_COVER = r"!\b(?:workers'? compensation|pet insurance|animal insurance|travel insurance|dental (?:benefits? )?(?:plans?|insurance|benefits?|services|care|coverage|providers?|loss ratios?)|vision (?:plans?|insurance|care|benefits?|coverage)|disability income|long-term care insurance|life insurance|motor vehicles?|automobiles?|uninsured motorists?)\b"
# Medicaid bills about paying providers or covering one service, not about who is covered.
NOT_MCAID_SERVICE = r"!\b(?:reimbursement rates?|provider rates?|rates? of (?:payment|reimbursement)|payment rates?|fee schedules?|directed payments?|provider taxes|assessments? on hospitals)\b"
# The sex offender registry's administration.
NOT_REGISTRY = r"!\b(?:sex(?:ual)? offenders? registr\w*|registration of sex(?:ual)? offenders?|sex(?:ual)? offender registration|registered sex(?:ual)? offenders?|sex offender (?:residency|address|verification))\b"
# Lists of crimes (sentencing, voting rights, bail) that name rape or sexual assault among a dozen others.
NOT_CRIMELIST = r"!\b(?:arson|burglary|robbery|bribery|embezzlement|carjacking|theft|forgery|perjury|voter fraud|manslaughter)\b"
# Domestic violence named in a list of reasons in a custody, divorce or support bill.
NOT_PASSING = r"!\b(?:custody|parenting (?:time|plans?)|visitation|divorce|dissolution of marriage|alimony|spousal (?:support|maintenance)|child support)\b"

# Shared exclusions for the seventh batch's rules.
# A tax break for one kind of income or person ("eliminates the income tax on tips"), not the rates.
NOT_TAXITEM = r"!\b(?:income tax(?:es)? (?:on|for) (?:tips|overtime|social security|retirement|pensions?|military|veterans?|seniors?|unemployment|annuit\w*|capital gains|interest)|tip(?:ped)? (?:income|workers?|wages)|(?:be )?(?:deducted and )?withheld|endowments?)\b"
# Cannabis, psychedelics and kratom have their own issues.
NOT_OTHERDRUGS = r"!\b(?:cannabis|marijuana|marihuana|hemp|THC|psilocybin|psychedelic\w*|hallucinogen\w*|kratom|mitragyn\w*|tobacco|nicotine|alcohol\w*)\b"
# Wildlife fertility control.
NOT_WILDLIFE = r"!\b(?:wild horses?|burros?|deer|wildlife|feral|animals?|pets?|circus\w*|elephants?)\b"

ISSUES = [
    {"id": "datacenters", "group": "Technology", "name": "Data centers", "words": ["data center", "hyperscale", "large load"],
     "rules": [[r"\bdata ?cent(?:er|re)s?\b"], [r"\bhyperscale"], [r"\bhigh[- ]performance computing\b"],
               [r"\b(?:large|high)[- ]loads?\b", r"!\b(?:vehicles?|trailers?|trucks?|highways?|lanes?)\b"],
               [r"\b(?:large|high)[- ](?:energy[- ]use|energy[- ]demand|energy|use|load[- ]factor)(?: electric)? (?:facilit\w+|customers?|users?|consumers?)\b"]],
     # Not call centers ("international call or data centers": Kentucky HB 508 of 2026, on veterans' benefits
     # consultants) or where a company keeps people's data.
     "none": [r"\bstate data cent(?:er|re)", r"\bconsolidat\w*\b.{0,60}\bdata cent", r"\bdata cent(?:er|re)s? (?:services|consolidation)\b",
              r"\bcall (?:or|and|centers? (?:or|and)) data cent", r"\b(?:international|overseas|offshore|foreign) data cent"]},
    {"id": "pfas", "group": "Environment and energy", "name": "PFAS (“forever chemicals”)", "words": ["forever chemicals", "pfoa", "pfos", "firefighting foam", "sludge", "biosolids"],
     "rules": [[r"\bPFAS\b"], [r"perfluoro"], [r"polyfluoro"], [r"perfluorinated"], [r"\bforever chemicals?\b"],
               [r"\bPFOA\b"], [r"\bPFOS\b"], [r"\bfire[- ]?fighting foams?\b"], [r"(?-i)\bAFFF\b"],
               [r"\baqueous film[- ]forming foam"],
               [r"\b(?:turnout gear|firefighters?'? (?:personal )?protective (?:equipment|clothing))\b", r"\b(?:chemicals?|toxic|substances?)\b"],
               # Sewage sludge spread on farmland, where PFAS concentrate (2026-11-17): bills on it count even when they don't
               # name PFAS. Not sludge turned into energy, wages, landfills or manure.
               [r"\b(?:sewage sludge|sewer sludge|biosolids?|septage|(?:wastewater|treatment plant) sludge|toxic sludge)\b",
                r"!\b(?:prevailing wage|renewable energy|biomethane|biogas|energy|swine|manure|oil (?:and|&) gas|landfills?|leachate)\b"]],
     "filters": {"Sludge on farmland": [r"\bsludge\b", r"\bbiosolids?\b", r"\bseptage\b", r"\bland[- ]appli"]}},
    {"id": "ai", "group": "Technology", "name": "Artificial intelligence", "words": ["ai", "deepfake", "chatbot", "algorithm"],
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
    {"id": "kidsonline", "group": "Technology", "name": "Children online and social media", "words": ["social media", "age verification", "app store", "kids online"],
     "filters": {"Age checks for adult websites": [r"\bpornograph", r"\bharmful (?:to minors|material)\b", r"\badult[- ](?:only )?(?:websites?|content|material)\b", r"\bsexual material\b"],
                 "Social media": [r"\bsocial (?:media|networking)\b"], "App stores": [r"\bapp stores?\b"],
                 "Design and privacy codes": [r"\bage[- ]appropriate design\b", r"\bkids code\b", r"\b(?:data|privacy)\b"]},
     "rules": [[r"\bsocial (?:media|networking)\b", r"\b(?:minors?|child|children|teens?|teenagers?|under (?:the age of )?1[3-8]|age of 1[3-8]|parents?|youth)\b"],
               [r"\bage verification\b", r"\b(?:websites?|online|internet|apps?|applications?|platforms?)\b",
                r"!\b(?:alcohol|tobacco|vap(?:e|or|ing)|nicotine|firearms?|lottery|cannabis|marijuana|liquor|wager\w*|gaming|gambling|nitrite)\b"],
               [r"\b(?:online (?:services?|platforms?|products?)|digital services?)\b", r"\b(?:minors?|child|children|teens?|kids)\b"],
               [r"\bharmful (?:to minors|material)\b", r"\b(?:online|internet|websites?|digital|apps?)\b"],
               [r"\bage[- ]appropriate design\b"], [r"\bapp stores?\b", r"\b(?:minors?|age|parent)"]]},
    {"id": "phones", "group": "Education", "name": "Phones in schools", "words": ["cell phone", "cellphone", "smartphone", "phone ban", "bell to bell"],
     "rules": [[r"\b(?:cell(?:ular)? ?(?:tele)?phones?|smart ?phones?|wireless (?:communication|telecommunication)s? devices?|personal (?:electronic|communication|telecommunications?) devices?|(?:mobile|wireless|portable electronic|internet[- ]enabled|electronic|electronic telecommunications?) devices?|phone[- ]free)\b",
                r"\b(?:schools?|students?|classrooms?|instructional (?:time|day))\b",
                r"\b(?:use|uses|using|possess\w*|prohibit\w*|ban|bans|banned|polic(?:y|ies)|restrict\w*|free|limit\w*|access)\b",
                r"!\b(?:recycl\w*|e-?waste|audits?)\b"]],
     "none": [r"\b(?:stopped|passing a) school bus", r"\bdistrict[- ]owned\b", r"\bwhile driving\b", r"\boperat\w* a (?:motor )?vehicle\b", r"\bbus drivers?\b", r"\bschool zones?\b",
              # School-issued devices and lessons about device use, unless the same passage restricts phones (2026-11-18:
              # California SB 1128 of 2025-26, kindergartners taking school devices home; Virginia HB 1486 and SB 568 of
              # 2026, teaching about the addictive potential of screen time).
              r"(?s)^(?!.*(?:\b(?:prohibit\w*|ban|bans|banned|restrict\w*|limit\w*)\W+(?:\w+\W+){0,5}?(?:use|uses|using|possession|access|cell|phones?|smart ?phones?|devices?)\b"
              r"|\bbell[- ]to[- ]bell\b|\bphone[- ]free\b|\bdistraction[- ]free\b))"
              r"(?=.*\b(?:school[- ](?:issued|provided)|addictive potential|instruction (?:concerning|on|about|regarding) (?:the )?(?:time spent|safe use|use of)|technology-based (?:instructional )?materials)\b)"]},
    {"id": "housing", "group": "Housing", "name": "Housing supply and zoning", "words": ["zoning", "adu", "accessory dwelling", "missing middle", "housing supply"],
     "rules": [[r"\baccessory dwelling"], [r"(?-i)\bADUs?\b"], [r"\bmissing[- ]middle\b"], [r"\bsingle[- ]family zon"],
               [r"\b(?:duplex|triplex|fourplex|quadplex)(?:es)?\b"], [r"\bminimum lot sizes?\b"],
               [r"\bparking (?:minimums?|requirements?|mandates?)\b", r"\bhous"], [r"\bby[- ]right\b", r"\bhous"],
               [r"\bhousing (?:production|supply)\b"], [r"\bhousing elements?\b"], [r"\bmulti-?family\b", r"\bzon(?:e|ed|ing)\b"],
               [r"\bdensity\b", r"\bhousing\b", r"\bzon(?:e|ed|ing)\b"], [r"\bstarter homes?\b"], [r"\bmanufactured hous", r"\bzon"]]},
    {"id": "minwage", "group": "Jobs and workers", "name": "Minimum wage", "words": ["minimum wage", "tipped wage", "living wage"],
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
    {"id": "repair", "group": "Technology", "name": "Right to repair", "words": ["right to repair", "fair repair"],
     "rules": [[r"\bright[- ]to[- ]repair\b"], [r"\bdevices? repair\b"], [r"\bfair repair\b"], [r"\bdigital electronic (?:equipment|products?)\b", r"\brepair"],
               [r"\bindependent repair\b", r"\b(?:parts|tools|documentation|diagnostic)"],
               [r"\brepair", r"\b(?:powered wheelchairs?|wheelchairs?|agricultural equipment|farm equipment)\b"]],
     "none": [r"\bbody shops?\b", r"\bmotor vehicle repair\b", r"\bauto(?:mobile|motive)? repair\b"]},
    {"id": "betting", "group": "Business and consumers", "name": "Sports betting and online gambling", "words": ["sports betting", "gambling", "igaming", "sweepstakes", "prediction market"],
     "rules": [[r"\bsports (?:wagering|betting|wagers?|pools?|gaming)\b"], [r"\bsportsbooks?\b"], [r"\bi-?gaming\b"],
               [r"\binternet (?:gambling|casino)"], [r"\b(?:internet|online) gaming\b", r"\b(?:wager\w*|casinos?|gambl\w*|bets?|betting)\b"],
               [r"\bonline (?:casino|gambling|poker|lottery|sports)"],
               [r"\bsweepstakes casino"], [r"\bsweepstakes\b", r"\bgam(?:ing|bling|es)\b"],
               [r"\bfantasy (?:sports|contests?)\b"], [r"\bprediction markets?\b"]],
     "none": [r"\braffles?\b", r"\bbingo\b"]},
    {"id": "drugcosts", "group": "Health", "name": "Prescription drug costs", "words": ["drug prices", "insulin", "pbm", "pharmacy benefit manager", "340b"],
     "rules": [[r"\binsulin\b", r"\b(?:costs?|prices?|pricing|co-?pay(?:ment)?s?|cost[- ]sharing|caps?|capped|out-of-pocket|affordab)"],
               [r"\bprescription drug affordability\b"], [r"\bpharmacy benefits? managers?\b"], [r"(?-i)\bPBMs?\b"],
               [r"\bdrug pric(?:e|es|ing)\b"], [r"\b(?:prescription )?drug (?:costs?|affordability)\b"],
               [r"\bprescription drugs?\b", r"\b(?:cost[- ]sharing|co-?pay(?:ment)?s?|out-of-pocket)\b"], [r"\b340B\b"]]},
    # The second ten (2026-11-15; notes/issues-check.md).
    {"id": "abortion", "group": "Health", "name": "Abortion", "words": ["reproductive rights", "pro-life", "abortion pill", "mifepristone", "heartbeat"],
     "rules": [[r"\babortions?\b"], [r"\bterminat\w* (?:of )?(?:a |the |her )?pregnanc", r"!\b(?:miscarriage|childbirth|leave of absence)\b"], [r"\bmifepristone\b"], [r"\bmisoprostol\b"],
               [r"\bfetal heartbeat\b"], [r"\breproductive (?:freedom|rights|autonomy|liberty)\b"], [r"\blegally protected health care\b"],
               # Shield laws: protecting providers and patients from other states' subpoenas and prosecutions.
               [r"\breproductive (?:health ?care|health services)\b", r"\b(?:shield\w*|subpoena\w*|extradit\w*|out[- ]of[- ]state|interstate|another state|legally protected)\b"],
               [r"\b(?:crisis pregnancy|pregnancy (?:resource|help|care|support)) cent(?:er|re)s?\b"]],
     "filters": {"Bans and limits": [r"\bban\b", r"\bprohibit", r"\brestrict", r"\bheartbeat\b", r"\bgestation", r"\bweeks\b", r"\bcriminal", r"\bpenalt"],
                 "Access and protections": [r"\bright to\b", r"\bprotect", r"\bshield\b", r"\baccess\b", r"\breproductive (?:freedom|rights|autonomy|liberty|health care)\b", r"\bcoverage\b"],
                 "Medication abortion": [r"\bmifepristone\b", r"\bmisoprostol\b", r"\babortion[- ]inducing\b", r"\b(?:medication|chemical) abortion", r"\babortion pills?\b"],
                 "Ballot measures": [r"\bconstitution", r"\bballot\b", r"\breferendum\b", r"\bvoters\b"]}},
    {"id": "firearms", "group": "Public safety and courts", "name": "Firearms", "words": ["guns", "gun control", "concealed carry", "red flag", "ghost gun", "second amendment"],
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
    {"id": "vouchers", "group": "Education", "name": "School vouchers and education savings accounts", "words": ["school choice", "esa", "education savings account", "voucher"],
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
    {"id": "voting", "group": "Elections and government", "name": "Voting and elections", "words": ["elections", "voter id", "mail ballots", "absentee", "voter registration", "popular vote", "electoral college", "winner-take-all"],
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
               [r"\bsuffrage\b"], [r"\bdisenfranchis"],
               # How presidential electors are chosen and vote (2026-11-17): the National Popular Vote compact, winner-take-all
               # or by congressional district, faithless and false electors.
               [r"\bpresidential electors?\b"], [r"\belectoral (?:college|votes?|count)\b"], [r"\belectors? (?:for|of) (?:the )?President\b"],
               [r"\bwinner[- ]take[- ]all\b", r"\b(?:elector\w*|president\w*)\b"], [r"\b(?:faithless|faithful|false|fake|alternate) (?:slates? of )?electors?\b"]],
     # Not votes by a company's or cooperative's members, nor Mississippi's private bills restoring one person's right to
     # vote ("Suffrage; restore to Frankie Ward, Jr").
     "none": [r"\b(?:shareholders?|stockholders?|cooperatives?|homeowners'? associations?|condominiums?|voting (?:interests?|shares|stock|securities|power))\b",
              r"\brestore (?:the right of )?suffrage to (?!(?:persons|people|individuals|those|all|certain|any|felons|citizens|residents)\b)"],
     "filters": {"Voter ID": [r"\bvoter ID\b", r"\bidentification\b", r"\bphoto ID\b"],
                  "Mail and absentee voting": [r"\babsentee\b", r"\bmail(?:-in| in)? (?:ballots?|voting)\b", r"\bvote[- ]by[- ]mail\b", r"\bballots? by mail\b"],
                  "Voter registration": [r"\bregist\w* (?:to vote|voters?)\b", r"\bvoter (?:registration|rolls?|lists?)\b", r"\bsame[- ]day registration\b"],
                  "Election administration and security": [r"\baudits?\b", r"\btabulat", r"\bequipment\b", r"\bmachines?\b", r"\bsecurity\b", r"\bintegrity\b", r"\belection (?:officials?|workers?|judges?|administrat|clerks?)", r"\bpoll (?:watchers?|workers?|books?)", r"\bcanvass", r"\bcertif", r"\bdrop ?box"],
                  "Presidential electors and popular vote": [r"\bpresidential electors?\b", r"\belectoral (?:college|votes?|count)\b", r"\bnational popular vote\b", r"\bwinner[- ]take[- ]all\b", r"\belectors? (?:for|of) (?:the )?President\b", r"\b(?:faithless|faithful|false|fake) (?:slates? of )?electors?\b", r"\bcongressional district method\b"]}},
    {"id": "immigration", "group": "Rights", "name": "Immigration", "words": ["immigrants", "ice", "sanctuary", "undocumented", "deportation"],
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
    {"id": "tenants", "group": "Housing", "name": "Rent and tenants", "words": ["rent", "renters", "eviction", "landlord", "rent control"],
     "rules": [[r"\btenan(?:ts?|cy|cies)\b", r"!\b(?:tenants? in common|tenancy in common|tenancy by the entiret\w*|joint tenan\w*|life tenan\w*|tenancy at sufferance)\b", NOT_HOMES],
               [r"\blandlords?\b", r"!\b(?:employers|lenders|journalists),? (?:\w+,? )?(?:and )?landlords\b", NOT_HOMES], [r"\bevict\w*\b"], [r"\brent (?:control|stabiliz\w*|increases?|caps?|gouging|regulat\w*|limits?|hikes?|escrow|withholding)\b"],
               [r"\brental (?:housing|units?|propert\w*|agreements?|applications?|assistance|dwellings?|apartments?)\b",
                r"!\b(?:short[- ]term|vacation|construct\w*|develop\w*|housing tax credits?|low[- ]income housing tax|financ\w*|loans?|solar|valuation|property tax\w*|vehicles?|cars?)\b", NOT_HOMES],
               [r"\bsecurity deposits?\b", r"\b(?:rent\w*|leases?|tenants?|landlords?|residential|dwellings?|apartments?)\b"],
               [r"\b(?:residential|apartment|dwelling) leases?\b"], [r"\bforcible entry and detainer\b"], [r"\bunlawful detainer\b"],
               [r"\bsummary (?:possession|ejectment)\b"], [r"\bwarranty of habitability\b"], [r"\bsquatt\w*\b", r"\b(?:remov\w*|evict\w*|unlawful\w*|occup\w*)\b"], [r"\blot rent\b"],
               [r"\bhousing choice vouchers?\b"], [r"\bsource of income\b", r"\b(?:housing|rent\w*|landlords?|tenants?)\b"]]},
    {"id": "proptax", "group": "Taxes", "name": "Property tax relief", "words": ["property tax", "homestead", "assessment cap"],
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
    {"id": "transgender", "group": "Rights", "name": "Transgender people", "words": ["trans", "gender identity", "gender-affirming care", "lgbtq"],
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
    {"id": "dei", "group": "Rights", "name": "Diversity, equity and inclusion", "words": ["diversity", "equity", "inclusion", "affirmative action"],
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
    {"id": "cannabis", "group": "Public safety and courts", "name": "Cannabis", "words": ["marijuana", "weed", "thc", "delta-8", "hemp"],
     "rules": [[r"\bcannabis\b"], [r"\bmarijuana\b"], [r"\bmarihuana\b"], [r"(?-i)\bTHC\b"], [r"\btetrahydrocannabinol"], [r"\bdelta[- ]?[89]\b"],
               [r"\bhemp[- ]derived\b"], [r"\bcannabinoids?\b"], [r"(?-i)\bCBD\b"], [r"\bcannabidiol\b"],
               [r"\bhemp\b", r"\b(?:intoxicat\w*|consumable|ingestible|edibles?|beverages?|smokable|inhal\w*)\b"],
               [r"\bhemp products?\b", r"!\b(?:industrial hemp|fiber|grain)\b"], [r"\bdispensar(?:y|ies)\b", r"\b(?:retail|adult[- ]use|on-site consumption)\b"]],
     "filters": {"Medical cannabis": [r"\bmedical (?:cannabis|marijuana|marihuana)\b", r"\bmedicinal\b", r"\bqualifying (?:patients?|conditions?)\b"],
                 "Hemp-derived THC": [r"\bhemp\b", r"\bdelta[- ]?[89]\b", r"\bintoxicating\b"],
                 "Expungement": [r"\bexpunge", r"\bsealing\b", r"\bseal (?:the )?records?\b"]}},
    # The third ten (2026-11-17; notes/issues-check.md).
    {"id": "privacy", "group": "Technology", "name": "Data privacy", "words": ["data privacy", "data broker", "biometric", "personal data"],
     # Consumer data privacy: what businesses may collect, keep and sell. Not government records or what agencies and
     # police may do, not "invasion of privacy" crimes, and not children's design codes (Children online), though a
     # broad consumer privacy act with parts for minors counts.
     "rules": [[r"\b(?:consumer|online|internet|genetic|biometric|health|location|customer) (?:data )?privacy\b",
                r"!\b(?:public records?|open records?|freedom of information|age[- ]appropriate design|kids code|invasion of (?:personal )?privacy|governmental data|state agenc\w*|law enforcement|police)\b"],
               # "Data privacy" alone is also a line in many bills about government programs' records.
               [r"\bdata privacy\b", r"\b(?:consumers?|businesses|controllers?|processors?|sell\w*|sale|targeted advertising)\b",
                r"!\b(?:public records?|open records?|governmental data|state agenc\w*|law enforcement|police)\b"],
               [r"\bdata brokers?\b"], [r"\bbiometric (?:data|information|identifiers?|surveillance|privacy)\b",
                r"!\b(?:state agenc\w*|government(?:al)? entit\w*|law enforcement|police|jury|probable cause|arrest\w*|background checks?|justice information|criminal justice)\b"],
               [r"\bconsumer health (?:data|information)\b"], [r"\bconsumer data protection\b"],
               [r"\b(?:precise )?geolocation (?:data|information)\b", r"!\bknown minors?\b"], [r"\blocation data\b", r"!\b(?:harvest|open records?|students?)\b"],
               [r"\bprivacy polic(?:y|ies)\b", r"\b(?:internet|websites?|online|consumers?|apps?|applications?|service providers?)\b"],
               [r"\bpersonal (?:data|information)\b", r"\b(?:controllers?|processors?|opt[- ]out|sell\w*|sale|targeted advertising|profiling|consumers?|businesses|business entit\w*)\b",
                r"!\b(?:public records?|open records?|freedom of information|data breach\w*|security breach\w*|breach of (?:the )?security|judges?|judicial|law enforcement officers?|public safety officers?|government(?:al)? entit\w*|state agenc\w*|election\w*|voters?|defraud\w*|fraudulent|identity theft)\b"]],
     # California's digests name the Consumer Privacy Act as background on bills about other things.
     "none": [r"\bstate (?:public protection and general government )?budget\b", r"\bExisting (?:state )?law, the California Consumer Privacy Act\b"]},
    {"id": "campaignfinance", "group": "Elections and government", "name": "Campaign finance", "words": ["campaign contributions", "pac", "dark money", "super pac"],
     # Money in politics: contributions, spending, disclosure, PACs, public financing. Not lobbying or ethics alone.
     "rules": [[r"\bcampaign financ\w*\b", r"!\bappropriat\w*\W+(?:\w+\W+){0,12}?campaign finance (?:and public disclosure )?board\b"],
               [r"\bcampaign (?:contributions?|expenditures?|spending|funds?|accounts?|disclosures?|committees?|finance reports?|treasurers?)\b",
                r"!\b(?:awareness|education(?:al)?|advertising|information(?:al)?|outreach|marketing|recruitment|media|prevention|safety) campaigns?\b"],
               [r"\bpolitical (?:contributions?|donations?|action committees?|committees?|expenditures?|spending)\b"],
               [r"\bpolitical (?:advertis\w*|ads?)\b", r"!\b(?:artificial intelligence|deep ?fakes?|synthetic|deceptive|materially|manipulated|AI)\b"],
               [r"(?-i)\b(?:super )?PACs?\b"], [r"\bdark money\b"], [r"\bindependent expenditures?\b"], [r"\belectioneering communications?\b", r"!\b(?:deep ?fakes?|synthetic media)\b"],
               [r"\bclean elections?\b"], [r"\bpublic (?:campaign )?financ\w*\b", r"\b(?:campaigns?|candidates?|elections?)\b"],
               [r"\bcontribution limits?\b"], [r"\bpay[- ]to[- ]play\b"],
               [r"\b(?:contributions?|donations?)\b", r"\b(?:candidates?|campaign committees?|political part(?:y|ies)|inaugura\w*)\b", r"\b(?:limit\w*|report\w*|disclos\w*|prohibit\w*|accept\w*|solicit\w*)\b"]],
     # California's digests open with the Political Reform Act as background on bills about other things.
     # Bills on AI and deepfakes in political ads name the committees that pay for them.
     "none": [r"\bprovides for the comprehensive regulation of campaign financing\b", r"\b(?:artificial intelligence|deep ?fakes?|synthetic media|materially deceptive)\b"]},
    {"id": "redistricting", "group": "Elections and government", "name": "Redistricting", "words": ["gerrymandering", "district maps"],
     # Drawing legislative and congressional districts. Local ward lines only when statewide rules change: not one
     # county's or city's map.
     "rules": [[r"\bredistrict\w*\b"], [r"\breapportion\w*\b", r"\b(?:districts?|legislat\w*|congress\w*|senate|house|census)\b"], [r"\bgerrymander\w*\b"],
               [r"\bapportion\w*\b", r"\b(?:legislative|congressional|senate|house|representatives?) districts?\b"],
               [r"\b(?:district (?:maps?|boundar\w*|lines)|districting plans?|composition of (?:the )?districts)\b",
                r"\b(?:(?:legislative|congressional|senate|house|state representative) (?:districts?|seats?)|house of representatives|members of the (?:senate|house|legislature)|congress)\b"]],
     "none": [r"(?-i)\b(?:County of [A-Z]\w+|[A-Z]\w+ County (?:Board|Citizens|Commission|Redistricting|Municipal)|City of [A-Z]\w+)",
              r"\bmaking an appropriation\b|\bappropriation for the purpose\b|\blegislative expenses\b|\bfor fiscal year\b",
              # Waiting "until the next redistricting", the Census Bureau's redistricting files, courts' and electors' districts.
              r"\b(?:until|before|after|following) (?:the )?(?:next )?(?:decennial )?redistricting\b", r"\bcensus redistricting (?:data|TIGER)",
              r"\b(?:judicial (?:redistricting|districts?)|supreme court districts?|redistricting of the (?:\w+ )?supreme court|chancery|circuit courts?|justices? of the peace|constables?|presidential electors?)\b",
              # Boards whose members are appointed or elected by district (school boards, regents, commissions).
              r"\b(?:school boards?|boards? of (?:education|regents)|university|appointed based|commissioners? (?:will|shall) be appointed)\b"]},
    {"id": "paidleave", "group": "Jobs and workers", "name": "Paid family and sick leave", "words": ["paid leave", "sick leave", "family leave", "parental leave", "fmla"],
     # Paid leave laws and programs: family and medical leave insurance, paid sick and safe leave, parental leave
     # (public employees' too). Not leave banks or donations for one employee, payouts of unused leave, or paid
     # administrative leave.
     "rules": [[r"\bpaid (?:family|medical|sick|parental|safe|maternity|paternity|prenatal)(?: and (?:medical|safe))? (?:leave|time|days?|benefits?)\b"], [r"\bfamily and medical leave\b"],
               [r"\bfamily (?:leave|temporary disability)\b"], [r"\bearned (?:sick|paid) (?:and safe )?(?:leave|time)\b"], [r"\bsick and safe (?:leave|time)\b"],
               [r"\bsick (?:leave|time|days)\b", r"\b(?:earn\w* (?:paid )?sick|hours worked|employers? (?:to|must|shall) provide|mandat\w*|requir\w* (?:all |private )?employers)\b",
                r"!\b(?:unused|payouts?|retirement|service credit)\b"],
               [r"\bparental leave\b"], [r"\bmaternity leave\b"], [r"\bpaternity leave\b"], [r"(?-i)\bFMLA\b"], [r"\bsafe leave\b"]],
     "none": [r"\bsick leave banks?\b", r"\b(?:unused|accumulated) (?:sick|annual|vacation)\b", r"\bdonat\w* (?:of )?(?:sick )?leave\b",
              r"\bpaid administrative leave\b", r"\bterminal leave\b"]},
    {"id": "childcare", "group": "Social services", "name": "Child care", "words": ["daycare", "day care", "early childhood"],
     # Child care for working families: subsidies, licensing, workforce, tax credits. Not K-12, pre-K or foster care,
     # and not lists of places near which something is banned (sex offenders, tobacco shops).
     "rules": [[r"\b(?:child|day)[- ]?care\b",
                r"!\b(?:adult day|sex offenders?|registrants?|within (?:\d|one|two|five)[\w,]* (?:feet|yards)|tobacco|nicotine|vap(?:e|or|ing)|firearms?|cannabis|marijuana|alcohol\w*|liquor)\b",
                r"!\b(?:child[- ]?care institutions?|child[- ]placing|residential child[- ]?care|host homes?|nontraditional child[- ]?care)\b"],
               [r"\bearly (?:care and education|learning (?:programs?|providers?|centers?))\b"], [r"\bearly childhood (?:care|services)\b"], [r"\bchild and dependent care\b"]],
     "none": [r"\bfoster care\b(?!.{0,40}child ?care)"]},
    {"id": "ivf", "group": "Health", "name": "IVF and fertility", "words": ["in vitro", "infertility", "surrogacy", "embryos"],
     "rules": [[r"\bin vitro\b", r"!\b(?:cell[- ]cultivated|cultured|cultivated meat|animal cells?)\b"], [r"(?-i)\bIVF\b"], [r"\binfertility\b"], [r"\bfertility[- ](?:treatments?|preservation|services|care|coverage|benefits?|clinics?|patients?|fraud|health|related)\b"],
               [r"\bassisted reproduct\w*\b"], [r"\bsurrogacy\b"], [r"\bgestational (?:carriers?|surroga\w*)\b"], [r"\bextrauterine\b"],
               [r"\b(?:egg|oocyte|sperm|semen|gamete|embryo) (?:donors?|donations?|banks?|freezing|retrieval|storage|transfer)\b"], [r"\bdonor[- ]conceived\b"],
               [r"\bembryos?\b", r"\b(?:frozen|cryopreserv\w*|fertility|in vitro|IVF|reproductive technolog\w*)\b", r"!\bfetal tissue\b"]]},
    {"id": "fluoride", "group": "Health", "name": "Fluoride in drinking water", "words": ["fluoridation", "water fluoride"],
     "rules": [[r"\bfluoridat\w*\b"], [r"\bfluorid\w*\b", r"\bwater\b", r"!\b(?:sulfuryl|hydrogen) fluoride\b", r"!\bfluoride varnish\b"],
               [r"\beffects? of fluoride\b"], [r"\blaws? (?:governing|regarding|concerning|relating to) fluoride\b"]]},
    {"id": "nuclear", "group": "Environment and energy", "name": "Nuclear energy", "words": ["nuclear power", "smr", "small modular reactor", "fusion"],
     # Nuclear power, including small modular reactors, fusion and repeals of moratoriums. Not weapons, medicine, or
     # radioactive waste alone; not lists that leave nuclear out ("other than fossil fuel or nuclear") or name nuclear
     # plants among targets of crimes.
     "rules": [[r"\bnuclear[- ](?:power(?:ed)?|energy|reactors?|generat\w*|electric\w*|plants?|fission|fusion|facilit\w*|fuel(?:ed)?|industry|innovation|development|technolog\w*|resources?|units?|workforce|recycling|and hydrogen|feasibility|production|moratorium)\b",
                r"!\bnuclear weapons?\b", r"!\b(?:fossil fuels? or nuclear|radiological|terroris\w*|security coverage|defense contractors?|submarines?|firearms?)\b"],
               [r"\bsmall modular reactors?\b"], [r"(?-i)\bSMRs?\b"], [r"\badvanced (?:nuclear|reactors?)\b"], [r"\bmicro-?reactors?\b"],
               [r"\bfusion (?:energy|power|technology|science|industry|reactors?)\b"], [r"\baneutronic\b"],
               [r"\bfusion\b", r"\b(?:renewable|clean) energ\w*\b", r"!\bfusion (?:voting|centers?)\b"]],
     "none": [r"\bnuclear medicine\b", r"\bnuclear pharmac\w*\b"]},
    {"id": "wildfire", "group": "Environment and energy", "name": "Wildfire", "words": ["wildfires", "prescribed burn", "forest fire"],
     # Prevention, utilities' wildfire liability and mitigation plans, insurance and rebuilding, firefighting. Not
     # ordinary fire codes.
     "rules": [[r"\bwild ?fires?\b"], [r"\bwildland[- ](?:fires?|firefight\w*|urban interface|fire ?fighters?)\b"], [r"\b(?:forest|brush|grass|range) ?fires?\b"], [r"\bprescribed (?:fires?|burn\w*)\b"], [r"\bcontrolled burn\w*\b"],
               [r"\bdefensible space\b"], [r"\bfire[- ]?wise\b"], [r"\bfire (?:hazard severity|risk) zones?\b"], [r"\bpublic safety power shut\w*\b"],
               [r"\bfuels? (?:reduction|breaks?|treatments?|management)\b", r"\bfires?\b"]],
     # California's 2024 bond act is named for wildfire prevention among other things; forest rangers' retirement titles.
     "none": [r"\bWildfire Prevention, Drought Preparedness, and Clean Air Bond Act\b", r"\bforest rangers?\b"]},
    {"id": "noncompete", "group": "Jobs and workers", "name": "Noncompete agreements", "words": ["non-compete", "noncompete", "no-poach"],
     # Noncompete agreements and other restraints on workers changing jobs ("non-solicitation", "no-poach"). Not
     # "noncompetitive" bidding or positions.
     "rules": [[r"\bnon-?compet(?:e|es|ition)\b"], [r"\bcovenants? not to (?:compete|solicit)\b"], [r"\bagreements? not to compete\b"],
               [r"\brestrictive (?:employment )?covenants?\b", r"\b(?:employ\w*|workers?|physicians?)\b"],
               [r"\bno-?poach\w*\b"], [r"\bnon-?solicitation\b", r"\bemploy\w*\b"]]},
    # The fourth ten (2026-11-17; notes/issues-check.md).
    {"id": "strentals", "group": "Housing", "name": "Short-term rentals", "words": ["airbnb", "vrbo", "vacation rental", "str"],
     # Homes rented by the night (Airbnb, Vrbo): local rules, registration, taxes. Not hotel taxes generally.
     "rules": [[r"\bshort[- ]term (?:residential )?rentals?\b", r"!\bshort[- ]term rentals? of (?:motor )?(?:vehicles?|cars?|equipment|passenger)", r"!\b(?:child is placed|placement of (?:a |the )?child)\b"],
               [r"\bvacation (?:rentals?|homes? rentals?)\b"], [r"\b(?:Airbnb|VRBO|home[- ]?sharing|homestay)\b", r"!\b(?:Amazon|eBay|Etsy)\b"],
               [r"\btransient (?:rentals?|occupancy|lodging|accommodations?)\b", r"\b(?:short[- ]term|vacation|hosting platforms?|residential (?:dwellings?|propert\w*|units?)|home[- ]?sharing)\b"],
               [r"\b(?:hosting|booking|rental) platforms?\b", r"\b(?:rentals?|lodging|accommodations?)\b"]]},
    {"id": "water", "group": "Environment and energy", "name": "Water rights and supply", "words": ["groundwater", "drought", "aquifer", "colorado river"],
     # Water rights, allocation, groundwater, drought and interstate compacts. Not water quality alone (PFAS and fluoride
     # are their own issues) or utility billing.
     # Not foreign ownership lists ("agricultural land, forest land, water rights, mining claims").
     "rules": [[r"\bwater rights?\b", r"!\bforeign (?:governments?|adversar\w*|principals?|entit\w*|state-controlled)\b"], [r"\bgroundwater\b", r"!\b(?:contaminat\w*|pollut\w*|remediat\w*|cleanup|PFAS|nitrate|cannabis|discharg\w*|stormwater|landfills?|waste|quality|groundwater protection|monitoring wells?|groundwater monitoring|carbon (?:sequestration|dioxide))\b"], [r"\baquifers?\b"],
               [r"\bdroughts?\b", r"!\bburn bans?\b"], [r"\bwater (?:allocation|appropriation|banking|transfers?|conservation|shortages?|scarcity|use permits?|resources? (?:plan|management|board|commission))\b"],
               [r"\b(?:interstate )?(?:water|river) compacts?\b"], [r"\binstream flow"], [r"\bprior appropriation\b", r"\bwater\b", r"!\bprior appropriation from\b"], [r"\bColorado River\b"],
               [r"\bwater suppl(?:y|ies)\b", r"\b(?:drought|shortage|long[- ]term|planning|plans?|future|regional|reservoirs?|storage|sustainab\w*)\b",
                r"!\b(?:public water suppl(?:y|ies)|drinking water|fluorid\w*|lead|PFAS|contaminat\w*|sewer|wastewater|solid waste|non-?payment|shutoffs?|discontinu\w*|water bills?)\b"]],
     # Soil and water conservation districts work on erosion and farm runoff; California's 2024 bond act's name.
     "none": [r"\bsoil\W*(?:and|&)\W*water conservation\b", r"\bwater rates\b", r"\bappliance\w*\b", r"\bwater conservation board\b", r"\bWildfire Prevention, Drought Preparedness, and Clean Air Bond Act\b"]},
    {"id": "psychedelics", "group": "Health", "name": "Psychedelics", "words": ["psilocybin", "magic mushrooms", "mdma", "ibogaine"],
     # Psilocybin, MDMA, ibogaine and the like: therapy programs, decriminalization, research. Not cannabis.
     # Not lists of controlled substances in sentencing laws.
     "rules": [[r"\bpsilocybin\b", r"!\b(?:heroin|cocaine|fentanyl|methamphetamine|phencyclidine)\b"], [r"\bpsilocin\b", r"!\b(?:heroin|cocaine|fentanyl|methamphetamine|phencyclidine)\b"], [r"\bpsychedelic"], [r"(?-i)\bMDMA\b"], [r"\bibogaine\b"], [r"\bentheogen"],
               [r"\bnatural medicines?\b", r"\b(?:healing|psilocybin|therapy|facilitat\w*|mushrooms?)\b"],
               [r"\bmethylenedioxymethamphetamine\b", r"\b(?:therap\w*|research|treatment|clinical)\b"]]},
    {"id": "cryptoatm", "group": "Technology", "name": "Crypto ATMs", "words": ["bitcoin atm", "crypto kiosk", "cryptocurrency"],
     "rules": [[r"\b(?:virtual|digital|crypto) ?(?:currency|assets?)? ?kiosks?\b"], [r"\bcryptocurrency kiosks?\b"], [r"\b(?:crypto|cryptocurrency|bitcoin|virtual currency) ATMs?\b"],
               [r"\bkiosks?\b", r"\b(?:virtual currenc\w*|cryptocurrenc\w*|crypto|digital assets?|digital currenc\w*|bitcoin)\b"]]},
    {"id": "medicaidwork", "group": "Social services", "name": "Medicaid work requirements", "words": ["work requirements", "medicaid"],
     "rules": [[r"\bwork (?:or|and) community engagement\b"], [r"\bcommunity engagement requirements?\b"],
               [r"\bwork requirements?\b", r"\b(?:medicaid|medical assistance|MassHealth|Medi-Cal|TennCare|SoonerCare|HUSKY|BadgerCare|KanCare|Healthy Indiana Plan|HIP|Pathways|ARHOME|Arkansas Works|expansion (?:population|adults?))\b"],
               [r"\bable-bodied adults?\b", r"\b(?:work|employment|volunteer)\b", r"\b(?:medicaid|medical assistance|Medicaid expansion)\b", r"!\b(?:SNAP|food (?:assistance|stamps))\b"],
               [r"\b(?:employment|work) (?:as a )?(?:condition|requirement) (?:of|for) (?:medicaid|medical assistance) eligibility\b"]]},
    {"id": "dst", "group": "Elections and government", "name": "Daylight saving time", "words": ["daylight saving", "daylight savings", "standard time", "clock change", "time change"],
     "rules": [[r"\bdaylight sav(?:ing|ings)\b"], [r"\bstandard time\b", r"\b(?:year[- ]round|permanent\w*|observ\w*|exempt\w*|daylight)\b"],
               [r"\b(?:Atlantic|Central|Eastern|Mountain|Pacific) (?:standard )?time\b", r"\b(?:year[- ]round|permanent\w*|observ\w*|time zones?)\b"]]},
    {"id": "books", "group": "Education", "name": "Book bans in schools and libraries", "words": ["book bans", "banned books", "library books", "obscenity"],
     # Challenges to and removal of books and materials, "harmful to minors" rules for libraries, librarians' liability.
     # Not library funding alone.
     "rules": [[r"\bbook (?:bans?|banning|removals?|challenges?)\b"], [r"\bfreedom to read\b"], [r"\bchallenged (?:books?|materials?)\b"],
               [r"\b(?:library|instructional|reading|classroom|school) (?:materials?|books?|collections?)\b",
                r"\b(?:challeng\w*|obscen\w*|harmful to minors|sexually explicit|pornograph\w*|reconsideration|censor\w*|book removals?|remov\w* (?:of |the )?(?:books?|materials?|titles?)|(?:books?|materials?|titles?) (?:to be |be |are |were )?removed)\b"],
               [r"\blibrar(?:y|ies|ians?)\b", r"\b(?:obscen\w*|harmful to minors|sexually explicit|pornograph\w*|censor\w*|book bans?)\b"],
               [r"\blibrarians?\b", r"\b(?:prosecut\w*|criminal liability|affirmative defense|immunit\w*)\b"]]},
    {"id": "medicaldebt", "group": "Business and consumers", "name": "Medical debt", "words": ["medical bills", "hospital bills", "debt collection"],
     # Not hospitals' liens on injury settlements, or charity care as a line in hospital reporting.
     "rules": [[r"\bmedical (?:debts?|bills?|billing)\b", r"\b(?:credit reports?|credit reporting|consumer reports?|collect\w*|interest|garnish\w*|debts?)\b"],
               [r"\bmedical debts?\b"], [r"\bhealth care debts?\b"], [r"\bextraordinary collection actions?\b"],
               [r"\b(?:debt collect\w*|collection actions?|wage garnishment)\b", r"\b(?:hospitals?|medical|health care (?:providers?|facilit\w*|services))\b"],
               [r"\b(?:hospital financial assistance|charity care|financial assistance polic(?:y|ies))\b", r"\b(?:medical debts?|collection actions?|debt collect\w*|collect\w* (?:a |the )?(?:debt|bill)s?|bills? (?:to|sent))\b"]]},
    {"id": "police", "group": "Public safety and courts", "name": "Police accountability", "words": ["police reform", "body cameras", "use of force", "qualified immunity"],
     # Use of force, body cameras, misconduct records, decertification, qualified immunity, civilian oversight. Not
     # police funding or pay alone.
     "rules": [[r"\buse of (?:deadly |physical |excessive )?force\b", r"\b(?:police|law enforcement|peace officers?|officers?)\b", r"!\b(?:self[- ]defense|security (?:guards?|officers?))\b"],
               [r"\bbody[- ](?:worn )?cameras?\b"], [r"\bchoke ?holds?\b", r"\b(?:police|law enforcement|peace officers?|officers?)\b"], [r"\bno[- ]knock\b"], [r"\bqualified immunity\b", r"\b(?:police|law enforcement|peace officers?|officers?|government\w*|public (?:officials?|employees?)|civil rights)\b"],
               [r"\bdecertif\w*\b", r"\b(?:police|law enforcement|peace officers?|officers?)\b"],
               [r"\bcivilian (?:review|oversight|complaint)"], [r"\b(?:police|officer|law enforcement) (?:misconduct|accountability|discipline|disciplinary)\b"],
               [r"\bexcessive force\b"], [r"\bduty to intervene\b"], [r"\bBrady (?:lists?|disclosures?|material)\b"],
               [r"\b(?:misconduct|disciplinary|personnel) records?\b", r"\b(?:police|law enforcement|peace officers?)\b", r"!\bstudents?\b"],
               [r"\bofficer[- ]involved (?:shootings?|deaths?)\b"], [r"\bdeadly force\b", r"\b(?:police|law enforcement|peace officers?|officers?)\b"]]},
    {"id": "deathpenalty", "group": "Public safety and courts", "name": "Death penalty", "words": ["capital punishment", "execution", "death row"],
     # "Capital murder" (Texas, Mississippi) is also the name of crimes punished by life in prison: only with death in
     # the same passage, unless the bill creates a capital crime.
     "rules": [[r"\bdeath penalty\b"], [r"\bcapital (?:punishment|cases?|sentenc\w*|defendants?|trials?|prosecutions?|sexual battery|child rape)\b"],
               [r"\bcapital (?:murder|offenses?|crimes?|felon\w*)\b", r"\b(?:death|executions?|aggravating|mitigating|creat\w*|establish\w*)\b"],
               # Louisiana's statutes call a felony a crime "for which an offender may be sentenced to death or imprisonment at hard labor".
               [r"\bsentences? of death\b"], [r"\bdeath sentences?\b"], [r"\bsentenced to death\b", r"!\bsentenced to death or (?:life )?imprisonment at hard labor\b"], [r"\bdeath row\b"], [r"\blethal injection\b", r"!\b(?:euthanasia|mercy killing|patients?|end of life|aid in dying)\b"],
               [r"\bnitrogen hypoxia\b"], [r"\bfiring squad\b"], [r"\belectrocution\b", r"\b(?:execut\w*|sentence)\b"],
               [r"\bexecutions?\b", r"\b(?:lethal|condemned|death|capital|execution (?:protocols?|drugs?|chambers?|teams?|methods?|witness\w*))\b",
                r"!\bexecution of (?:a |the |any )?(?:documents?|warrants?|instruments?|contracts?|wills?|deeds?|agreements?|search|judgments?|leases?)\b",
                r"!\bexecution of (?:their|his|her|its|the|such|official) (?:\w+ )?(?:duties|powers|functions|responsibilit\w*|office)\b"]]},
    # The fifth ten (2026-11-17; notes/issues-check.md).
    {"id": "vaccines", "group": "Health", "name": "Vaccines and public health powers", "words": ["vaccine", "vaccination", "immunization", "mrna", "vaccine exemption", "public health emergency"],
     # Vaccine requirements, exemptions, access and mRNA bills, and the limits of health officers' and governors' emergency
     # powers (quarantine, closures, mask orders). Not animals' vaccines or plant quarantines.
     "rules": [[r"\bvaccin\w*\b", ANIMALS], [r"\bimmuni[sz]ations?\b", ANIMALS], [r"\b(?:un)?immuni[sz](?:e|ed|ing)\b", r"\b(?:vaccin\w*|against|children|students?|diseases?|schools?)\b", ANIMALS, r"!\b(?:liab\w*|lawsuits?|claims?|suits?)\b"], [r"\bmRNA\b"], [r"\binoculat\w*\b", ANIMALS],
               [r"\bpublic health (?:orders?|powers?|authority|mandates?|disasters?)\b"],
               [r"\bpublic health emergenc\w*\b", r"\b(?:emergency powers?|governor'?s? (?:authority|powers?)|terminat\w*|renew\w*|extend\w* (?:a|an|the|any)|extension of|duration|legislat\w* (?:approval|consent|oversight)|limit\w* (?:on|the)|quarantin\w*|isolation|clos(?:e|ure|ing)|mandates?|process for declaring|(?:may|to) declare)\b", NOT_PHE],
               [r"\b(?:emergency (?:powers?|orders?|declarations?|executive orders?)|disaster emergenc\w*)\b", r"\b(?:public health|pandemic|epidemic|COVID|infectious disease|contagious disease|communicable disease|health officers?)\b", NOT_PHE],
               [r"\b(?:health officers?|boards? of health|health (?:directors?|commissioners?|departments?))\b", r"\b(?:quarantin\w*|isolation orders?|clos(?:e|ure|ing) (?:of )?(?:businesses|schools|churches|places of worship)|business closures?|mask (?:orders?|mandates?|requirements?)|emergency powers?|(?:authority|powers?) to (?:order|mandate|close|require))\b"],
               [r"\bquarantin\w*\b", ANIMALS, NOT_PHE, r"!\b(?:plants?|pests?|insects?|seeds?|nurser\w*|agricultur\w*|crops?|trees?|weeds?|beetles?|fruit|citrus|forest\w*)\b"],
               [r"\bmask (?:mandates?|requirements?|orders?)\b"], [r"\bmedical freedom\b"]]},
    {"id": "unions", "group": "Jobs and workers", "name": "Unions and collective bargaining", "words": ["union", "labor unions", "collective bargaining", "right to work", "strike"],
     # Bargaining rights, public and private; union dues and payroll deduction, right-to-work, recognition, strikes. Not
     # a passing "subject to the collective bargaining agreement" in a bill about something else.
     "rules": [[r"\bcollective(?:ly)? bargain\w*\b", NOT_CBA],
               [r"\b(?:labor|employee|public employee|employees'?) (?:unions?|organizations?)\b", r"\b(?:bargain\w*|dues|represent\w*|recogni\w*|organiz(?:e|ing)|strikes?|membership|release time|members' rights)\b", NOT_CBA, r"!\b(?:representatives? (?:of|from) (?:a |an |the )?(?:statewide )?(?:labor|employee) organizations?|members? of (?:a |an )?labor organization (?:that|who)|(?:one|two|three|four) (?:members?|representatives?) (?:of|from|representing|recommended by)|recommendation of the labor organization)\b"],
               [r"\b(?:labor organizing|unioni[sz](?:e|ed|ing|ation)|union (?:labor|busting|violence|organizing|avoidance)|anti-?union)\b"],
               [r"(?<!collective )(?<!collectively )\bbargain\w*\b", r"\b(?:employ\w*|workers?|unions?|labor|teachers?|physicians?|nurses?)\b", r"!\bplea (?:bargain\w*|agreements?)\b", NOT_CBA],
               [r"\bunions?\b", r"\b(?:dues|membership|organiz\w*|representation|recogni\w*|bargain\w*|members|officers|stewards?|release time|neutrality|card check)\b", r"\b(?:employ\w*|workers?|labor|teachers?)\b", NOT_CBA, r"!\b(?:credit unions?|European Union|civil unions?|union county|union (?:station|pacific|city|township|parish)|student unions?)\b"],
               [r"\bright[- ]to[- ]work\b", r"!\b(?:authori[sz]ation|documentation|immigra\w*|visas?|work permits?)\b"],
               [r"\bexclusive (?:bargaining )?represent\w*\b"], [r"\bcard check\b"], [r"\bmeet and confer\b", r"\b(?:employee organizations?|unions?|bargaining|labor relations|exclusive represent\w*|memorand(?:um|a) of understanding)\b"],
               [r"\b(?:public employment relations|public employee relations|labor relations (?:act|board|commission))\b"],
               [r"\bunfair labor practices?\b"], [r"\b(?:right to strike|work stoppages?|lockouts?|striking (?:workers|employees)|strikers)\b", r"!\bstrikers? (?:in|of) (?:bowling|baseball)\b"],
               [r"\bstrikes?\b", r"\b(?:public employees?|teachers?|labor disputes?|unions?|workers|employees)\b", r"!\b(?:strike (?:out|through|teams?|forces?)|strikes (?:all|the|section|sections|original|everything|out)|AM ?\d+ strikes|stricken|lightning|motions? to strike|three strikes?|drone strikes?|military strikes?|air ?strikes?|strike (?:a|the) (?:word|provision|language|section))\b"]],
     "none": [r"\bcredit unions?\b"]},
    {"id": "initiatives", "group": "Elections and government", "name": "Ballot initiative rules", "words": ["ballot initiative", "referendum", "ballot measure", "petition signatures"],
     # Citizens' initiatives and referendums: signature rules, vote thresholds, single subject, circulators, ballot
     # titles. These bills are under Voting and elections too.
     "rules": [[r"\binitiative (?:and referend\w* )?(?:petitions?|measures?|process\w*|proposals?|powers?|rights?)\b"], [r"\breferend(?:um|a|ums) (?:petitions?|process\w*|powers?|rights?)\b"],
               [r"\binitiative and referend\w*\b"], [r"\b(?:citizens?'?|people'?s|popular|indirect|direct) initiatives?\b"], [r"\bstatewide initiatives?\b", r"\b(?:ballot|voters|electors|petitions?|referend\w*|signatures?)\b"],
               [r"\binitiated (?:measures?|statutes?|constitutional amendments?|acts?|laws?|petitions?)\b(?!,? (?:no\. )?\d| of \d{4}| \d+ of \d{4})"],
               [r"\bballot (?:initiatives?|measures?|questions?)\b(?! committees?)", r"\b(?:petitions?|signatures?|circulat(?:ors?|ing petitions?|ion of (?:a |the )?petitions?)|proposed by initiative|citizen-initiated)\b"],
               
               [r"\bpetition (?:circulators?|circulation|signatures?|gatherers?)\b", r"\b(?:initiative|referend\w*|ballot|constitutional amendment)\b"],
               [r"\bsignature (?:gatherers?|gathering|requirements?|thresholds?|verification)\b", r"\b(?:initiative|referend\w*|ballot (?:measure|question|issue)|constitutional amendment)\b"],
               [r"\bballot (?:titles?|summar(?:y|ies))\b", r"\b(?:initiative|referend\w*|measures?|petitions?)\b"],
               [r"\bpeople'?s veto\b"]],
     # California's digests name the initiative acts a bill amends ("an initiative measure approved by the voters").
     # Oregon's bills say when they take effect "if the Act is referred to the people ... by referendum petition".
     "none": [r"\b(?:an|the|this) initiative (?:measure|statute|act)(?:,)? (?:approved|enacted|adopted|passed)\b", r"\breferred to the people by (?:either )?the Legislative Assembly or by referendum petition\b", r"\b(?:ordinance|regulation|resolution),? or initiative measure\b", r"\binfluence (?:\w+ ){0,3}?referendum petitions?\b", r"\b(?:enacted|approved|adopted) (?:in \d{4} )?by (?:an?|the) (?:citizens?'? )?initiative(?: measure)?\b", r"\ban initiative (?:measure|statute)[,.]", r"\bProposition \d+\b(?:.{0,80})\binitiative (?:measure|statute)\b(?!.{0,40}\b(?:petition|signature))"]},
    {"id": "rcv", "group": "Elections and government", "name": "Ranked-choice voting", "words": ["ranked choice", "instant runoff", "rcv", "approval voting"],
     # Ranked-choice (instant-runoff) voting, adopting or banning it, and approval voting. These bills are under Voting and
     # elections too.
     "rules": [[r"\branked[- ]choice\b"], [r"\binstant[- ]run-?offs?\b"], [r"\bapproval voting\b"], [r"\bpreferential (?:voting|ballots?)\b(?! pupil)"],
               [r"\branked (?:voting|ballots?)\b"], [r"\brank(?:ing)? (?:the )?candidates? in order of preference\b"], [r"\bfinal[- ]five voting\b"],
               [r"(?-i)\bSTAR voting\b"], [r"(?-i)\bRCV\b"]]},
    {"id": "utilityrates", "group": "Environment and energy", "name": "Energy costs and utility rates", "words": ["electric bills", "electricity prices", "utility bills", "rate case", "liheap", "shutoffs"],
     # Electric and gas rates and rate cases, shutoffs, energy assistance, who pays for grid upgrades (large loads). Not
     # water and sewer rates, phone or broadband. Net metering (what solar owners are paid) counts as a rate.
     "rules": [[r"\b(?:electric(?:al|ity)?|natural gas|gas utility|gas and electric) (?:rates?|bills?|prices?|costs?|affordability|tariffs?)\b", NOT_WATER],
               [r"\b(?:energy|power|utility|utilities) (?:rates?|bills?|prices?|costs?|affordability|tariffs?)\b", r"\b(?:customers?|ratepayers?|households?|residential|consumers?|families|public (?:service|utilit\w*) commission|electric\w*)\b", NOT_WATER, r"!\benergy cost sav\w*\b"],
               [r"\bratepayers?\b", NOT_WATER], [r"\brate (?:cases?|increases?|hikes?|base|design|freezes?|caps?|adjustments?|proceedings?|schedules?|filings?)\b", r"\b(?:electric\w*|natural gas|gas (?:utilit|compan|corporation)|energy|public (?:service|utilit\w*) commission|investor[- ]owned)\b", NOT_WATER],
               [r"\b(?:shut[- ]?offs?|disconnect\w*|terminat\w* of (?:utility |electric |gas )?service)\b", r"\b(?:electric\w*|natural gas|gas service|heat\w*|energy|utility service)\b", NOT_WATER, r"!\b(?:telecommunications?|telephone|broadband|internet|cable|power shutoffs?|public safety power|de-?energiz\w*|wildfires?)\b"],
               [r"(?-i)\bLIHEAP\b"], [r"\bnet (?:energy )?metering\b"], [r"\bretail (?:electric(?:ity)?|energy|gas) (?:suppliers?|providers?|customers?|choice)\b"],
               [r"\b(?:arrear\w*|past[- ]due (?:bills?|balances?)|payment (?:plans?|forgiveness))\b", r"\b(?:electric\w*|gas (?:utilit\w*|service)|energy|public utilit\w*)\b", NOT_WATER], [r"\b(?:(?:low[- ]income|home|household|heating|utility) energy assistance|energy assistance (?:programs?|funds?|payments?|benefits?))\b"], [r"\b(?:energy|utility) (?:burden|affordability|bill assistance|bill credits?)\b", NOT_WATER], [r"\butility assistance\b", NOT_WATER, r"!\b(?:rent(?:al)?|mortgage)\b"],
               [r"\bpercentage of income payment\b"], [r"\b(?:large[- ]loads?|large[- ]load customers?)\b", r"\b(?:rates?|tariffs?|costs?|ratepayers?|customers?|pay)\b", r"!\b(?:vehicles?|trailers?|trucks?|highways?)\b"],
               [r"\b(?:fuel (?:cost )?adjustment|cost recovery|securiti[sz]ation|rate of return|return on equity|storm recovery (?:costs?|charges?))\b", r"\b(?:electric\w*|gas utilit\w*|public utilit\w*|ratepayers?|energy)\b", NOT_WATER]],
     "none": [r"\b(?:water|sewer|wastewater) (?:rates?|bills?|utilit\w*|service)\b(?!.{0,80}\belectric)"]},
    {"id": "climate", "group": "Environment and energy", "name": "Climate and clean energy", "words": ["climate change", "greenhouse gas", "renewable energy", "clean energy", "carbon", "electric vehicles", "gas stoves"],
     # Greenhouse gas limits and targets, renewable and clean energy standards, carbon pricing, electrification and gas
     # hookups (bans and bans on bans), zero-emission vehicle rules, climate superfunds. Nuclear power counts when framed as
     # clean energy (and is its own issue too).
     "rules": [[r"\bclimate (?:change|crisis|emergency|action|goals?|targets?|plans?|policy|policies|pollution|superfund|resilien\w*|adaptation|leadership|mitigation|solutions?|council|commission|office|corps|bonds?|accountability|disclosure|risks?|justice|protection)\b"],
               [r"\bgreenhouse gas\w*\b"], [r"\b(?:carbon|GHG|CO2) emissions?\b"], [r"\bcarbon (?:neutral\w*|free|pricing|tax|fees?|dioxide removal|capture|sequestration|intensity|offsets?|markets?|reduction|budget|pollution|storage)\b"],
               [r"\bnet[- ]zero\b", r"\b(?:emissions?|carbon|energy|greenhouse|climate|buildings?)\b"], [r"\bdecarboni[sz]\w*\b"], [r"\bcap[- ]and[- ](?:trade|invest)\b"], [r"\bclimate superfund\b"],
               [r"\b(?:renewable|clean|alternative|zero[- ]carbon|carbon[- ]free) (?:energy|electricity) (?:portfolio )?(?:standards?|targets?|goals?|credits?|certificates?|requirements?|procurement|mandates?|plans?)\b"],
               [r"\brenewable portfolio\b"], [r"\bclean energy (?:and \w+ (?:\w+ )?)?(?:objectives|goals|plans?|targets?|transition|economy|future)\b"], [r"\bzero[- ]emissions? credits?\b"], [r"\btransportation electrification\b"], [r"\b(?:low|clean)[- ]carbon fuels? standards?\b"], [r"\bclean (?:heat|fuels?|transportation) (?:standards?|programs?)\b"],
               [r"\bzero[- ]emissions? (?:vehicles?|trucks?|buses|cars|standards?|mandates?)\b"], [r"\badvanced clean (?:cars|trucks|fleets)\b"],
               [r"\belectric vehicles?\b", r"\b(?:mandates?|requir\w* (?:the )?sale|sales? (?:of new )?(?:gas|gasoline|internal combustion)|phase[- ]?out|ban\w*|prohibit\w*)\b", r"\b(?:gas|gasoline|internal combustion|diesel)\b"],
               [r"\b(?:building )?electrification\b", r"\b(?:buildings?|homes?|appliances?|heat pumps?|gas)\b"],
               [r"\b(?:gas (?:stoves?|appliances?|bans?|hook-?ups?)|all[- ]electric (?:buildings?|construction|homes?))\b"],
               [r"\b(?:type|source|kind) of (?:energy|fuel|utility service)\b", r"\b(?:prohibit\w*|restrict\w*|discriminat\w*)\b", r"\b(?:political subdivisions?|municipal\w*|count(?:y|ies)|local governments?|ordinances?)\b"]],
     # California's digests open with its greenhouse gas law as background on bills about other things.
     "none": [r"\bcarbon monoxide\b(?!.{0,200}\b(?:emission|greenhouse))", r"\bdesignates the State Air Resources Board as the state agency (?:charged with|responsible for) monitoring and regulating sources of emissions of greenhouse gases\b"]},
    {"id": "esg", "group": "Business and consumers", "name": "State investing and boycott rules", "words": ["esg", "boycott", "divestment", "bds", "debanking"],
     # Whether state funds, pensions and contractors may weigh environmental, social and governance factors, and laws
     # barring contracts with or investments in companies that boycott energy, firearms or Israel. Divestment from fossil
     # fuels counts; divestment from countries (China, Russia, Iran) doesn't.
     "rules": [[r"(?-i)\bESG\b"], [r"\benvironmental, social,? (?:and|or|&) (?:corporate )?governance\b"],
               [r"\bboycott\w*\b", r"\b(?:energy|fossil fuels?|oil|gas|firearms?|ammunition|Israel\w*|contract\w*|companies|investments?|state funds?|public funds?|retirement|pension\w*)\b", r"!\b(?:consumer boycotts?|Islamophobia)\b"],
               [r"\bdivest\w*\b", r"\b(?:fossil fuels?|coal|oil|thermal coal|Israel\w*|firearms?|ammunition)\b", r"!\bdivestiture\b"],
               [r"\b(?:pecuniary|nonpecuniary|non-pecuniary) factors?\b"], [r"\bdebank\w*\b"],
               [r"\bfair access to (?:banking|financial services)\b"], [r"\bfair access\b", r"\b(?:banks?|financial (?:services|institutions?))\b", r"\b(?:deny|denial|refus\w*|discriminat\w*|political|social|environmental)\b"],
               [r"\bproxy (?:voting|votes?|advisors?|advisers?)\b", r"\b(?:state|retirement|pension|public funds?|investment)\b"],
               [r"\bsocial credit scor\w*\b"], [r"\b(?:discriminat\w*) against (?:the )?(?:firearm|fossil fuel|energy|oil and gas)\w* (?:industr\w*|compan\w*|entit\w*)\b"]]},
    {"id": "religion", "group": "Education", "name": "Religion in public schools", "words": ["ten commandments", "school prayer", "chaplains", "bible", "released time"],
     # Ten Commandments displays, school chaplains, Bible courses, prayer, released time for religious instruction,
     # "In God We Trust" in schools, religious expression and dress. Not vaccine exemptions or private religious schools.
     "rules": [[r"\b(?:Ten Commandments|Decalogue)\b", r"\b(?:schools?|classrooms?|students?|educational institutions?|boards? of education)\b"], [r"\bchaplains?\b", r"\b(?:schools?|students?|boards? of education)\b", r"!\b(?:hospitals?|police|law enforcement|fire|military|national guard|legislat\w*|correctional|prisons?|jails?)\b"],
               [r"\bbible\b", r"\b(?:schools?|courses?|electives?|curricul\w*|students?|literacy|classrooms?)\b", r"!\b(?:state book|museums?)\b"],
               [r"\bprayers?\b", r"\b(?:public schools?|school districts?|students?|classrooms?|school (?:day|events?|boards?|governing bod\w*))\b"],
               [r"\breleased[- ]time\b"], [r"\bIn God We Trust\b", r"\b(?:schools?|classrooms?|students?)\b"],
               [r"\bmoment of (?:silence|silent (?:reflection|prayer))\b"],
               [r"\breligio\w* (?:expression|liberty|liberties|freedom|instruction|texts?|clubs?|displays?|holidays?|attire|garb|dress|neutrality|viewpoints?|activit\w*|speech)\b",
                r"\b(?:public schools?|school districts?|students?|classrooms?|teachers?)\b", r"!\b(?:vaccin\w*|immuniz\w*|postsecondary|colleges?|universit\w*|retirement)\b"],
               [r"\b(?:religious|sectarian) (?:charter schools?|instruction)\b", r"!\b(?:nonpublic|tuition)\b"],
               [r"\breligio(?:n|us) (?:or religious )?(?:values|texts?|content|instruction|studies)\b", r"\b(?:instructional materials?|curricul\w*)\b", r"\b(?:public schools?|school districts?|students?)\b", r"!\b(?:vaccin\w*|immuniz\w*|nonpublic|private schools?|postsecondary|colleges?|universit\w*)\b"]],
     "none": [r"\bCouncil on (?:the )?Arts\b"]},
    {"id": "childlabor", "group": "Jobs and workers", "name": "Child labor", "words": ["child labor", "work permits", "teen jobs", "youth employment", "child influencers"],
     # Work permits, hours, hazardous jobs and penalties for employing minors, and child performers' and child
     # influencers' earnings. Not minor league athletes.
     "rules": [[r"\bchild labou?r\b"], [r"\b(?:employment|employing|employ) (?:of )?(?:minors|children|youth|persons under (?:the age of )?1[4-8])\b"],
               [r"\b(?:child|minor|youth|teen(?:age)?) (?:workers?|employees?|employment|labou?r)\b", r"!\b(?:minor league|work opportunity)\b", NOT_YOUTHJOBS],
               [r"\bminors?\b (?:\w+ ){0,8}?(?:to |may |who |shall )?(?:work|be employed|employed|working|in the workplace)\b", r"!\bminor (?:and|or) (?:technical|routine)\b", r"!\bminor (?:child|maintenance|repairs?|changes|modifications|revisions|amendments|construction|projects?|works?|alterations?|improvements?|capital)\b"],
               [r"\b(?:employ\w*|hir\w*|work) (?:of |with )?minors\b"],
               [r"\b(?:minors?|youths?|teens?|under (?:the age of )?1[4-8]|1[4-7][- ]year[- ]olds?)\b",
                r"\b(?:work permits?|employment certificates?|certificates? of (?:age|employment)|working papers|age certificates?|hazardous (?:occupations?|employment|work|jobs)|hours (?:of (?:work|employment)|worked)|work(?:ing)? hours|maximum hours)\b",
                r"\b(?:employ\w*|work\w*|jobs?)\b", r"!\bminor league\b"],
               [r"(?<!Whole )\bchild (?:performers?|actors?|entertainers?|influencers?|content creators?|models?)\b"],
               [r"\b(?:minors?|child|children)\b", r"\b(?:vlog\w*|content creat\w*|influencers?|monetiz\w*)\b", r"\b(?:compensat\w*|earnings?|trust|paid|income)\b"],
               [r"\bCoogan\b"]],
     "none": [r"\b(?:child ?care|day ?care)\b(?!.{0,60}\b(?:work permits?|employment of minors))"]},
    {"id": "protest", "group": "Public safety and courts", "name": "Protest and assembly laws", "words": ["protests", "riot", "protesters", "masks", "critical infrastructure"],
     # Riot and unlawful assembly crimes, blocking roads, critical infrastructure trespass, protests near homes, clinics
     # and schools, masks while committing crimes, drivers' liability for hitting protesters. Not prison riots, tax or
     # bid protests.
     "rules": [[r"\briot(?:s|ing|ous|ers?)?\b(?!, disorderly conduct and related offenses| gear| control equipment)", r"!\b(?:inmates?|prisoners?|correctional|jails?|detention|incarcerat\w*|offenders? in custody)\b", NOT_DISASTER, r"!\b(?:race riots?|massacres?|monuments?|memorials?|commemorat\w*|Election Day Riots?)\b"],
               [r"\bunlawful assembl\w*\b(?! or disassembl)"], [r"\bcivil disorders?\b", r"!\b(?:inmates?|prisoners?|correctional)\b", NOT_DISASTER], [r"\bpublic demonstrations?\b(?! of)", r"!\beducational purposes\b"], [r"\b(?:peaceabl[ey]|peacefully|right to) (?:to )?assembl\w*\b"],
               [r"\bprotest(?:s|ers?|ors?|ing)?\b", r"!\b(?:political prisoners|Iran\w*|Hong Kong|Cuba\w*|Venezuel\w*|Belarus\w*|Georgia's|Serbia\w*)\b", r"\b(?:demonstrat(?:ions?|ors?)|unlawful assembl\w*|peaceabl\w* assembl\w*|right to assemble|assemblies|picket\w*|riot\w*|masks?|first amendment|free speech|peaceful\w*|marches|block\w* (?:a |the )?(?:roads?|highways?|streets?|traffic|roadways?))\b", NOT_TAXPROTEST],
               [r"\bpicket\w*\b", r"\b(?:residences?|dwellings?|homes?|funerals?|clinics?|schools?|protest\w*)\b"],
               [r"\bcritical infrastructure\b", r"\b(?:trespass\w*|damag\w*|tamper\w*|imped\w*|interfer\w*|unauthori[sz]ed entry|enter\w*|vandal\w*)\b", r"!\b(?:cyber\w*|drones?|unmanned aircraft|ransom\w*|foreign (?:adversar\w*|countr\w*|principals?|entit\w*)|countr(?:y|ies) of concern|electromagnetic|computers?|electronic|data)\b"],
               [r"\b(?:obstruct\w*|block\w*|imped\w*)\b (?:\w+ ){0,3}?(?:highways?|roadways?|roads?|streets?|traffic|interstates?|sidewalks?)\b", r"\b(?:protest\w*|demonstrat(?:ions?|ors?)|riot\w*|unlawful assembl\w*|pedestrians?|on foot)\b", NOT_TAXPROTEST, r"!\b(?:trains?|railroads?|rail crossings?|grade crossings?)\b"],
               [r"\b(?:masks?|masked|masking|face coverings?|disguises?|disguised|hoods?)\b", r"\b(?:conceal\w* (?:\w+ )?identity|harass\w*|intimidat\w*|riot\w*|protest\w*|unlawful assembl\w*|while committing|loiter\w*|unlawful masking)\b", r"!\b(?:COVID|pandemic|health|medical|mandates?|respirat\w*|law enforcement|peace officers?|police|officers?|agents?|immigration|callers?|telephone|voice|caller ID)\b"],
               [r"\bbuffer zones?\b", r"\b(?:clinics?|health care facilit\w*|reproductive|abortion|funerals?|places? of worship|polling)\b"],
               [r"\b(?:obstruct\w*|imped\w*|interfer\w*)\b (?:\w+ ){0,3}?(?:access|entrance|passage)\b", r"\b(?:clinics?|reproductive health|places? of (?:religious )?worship|health care facilit\w*)\b"]]},
    {"id": "kratom", "group": "Health", "name": "Kratom", "words": ["kratom", "7-oh", "7-hydroxy", "mitragynine"],
     # Kratom and its alkaloids (mitragynine, 7-hydroxymitragynine, "7-OH"): sales and age limits, labeling, scheduling,
     # kratom consumer protection acts.
     "rules": [[r"\bkratom\b"], [r"\bmitragyn\w*\b"], [r"\b7[- ]?hydroxy[- ]?mitragyn\w*\b"], [r"\b7[- ]?hydroxy\b", r"\b(?:kratom|mitragyn\w*|alkaloids?)\b"], [r"(?-i)\b7[- ]OH\b"],
               [r"\bMitragyna speciosa\b"]]},
    # The sixth batch (2026-11-17; notes/issues-check.md).
    {"id": "coverage", "group": "Health", "name": "Health insurance coverage", "words": ["health insurance", "single payer", "medicare for all", "public option", "medicaid expansion", "obamacare", "aca", "uninsured"], "body": 3,
     # Who has health coverage: single-payer and universal coverage, public options, Medicaid expansion and eligibility,
     # state marketplaces and their subsidies, the Affordable Care Act's protections (pre-existing conditions, essential
     # benefits), coverage for the uninsured. Not a mandate to cover one treatment, Medicaid rates and billing, dental or
     # vision alone, or workers' compensation.
     "rules": [[r"\bsingle[- ]payer\b", NOT_COVER], [r"\buniversal (?:health ?care|health (?:coverage|insurance|benefits?|plans?|system|assurance|programs?)|coverage|access to health)\b", NOT_COVER],
               [r"\b(?:Medicare|health care|health ?care coverage) for all\b"], [r"\b(?:Healthy California|New York Health) (?:for All|Act)\b"],
               [r"\bpublic (?:health (?:insurance |care |benefit )?)?options?\b", r"\b(?:health|insurance|coverage|plans?)\b", NOT_COVER],
               [r"\b(?:Colorado Option|Cascade (?:Care|Select)|Battle Born State Plans?|basic health (?:program|plan))\b"], [r"\b(?:MinnesotaCare|Essential Plan)\b", r"\b(?:eligib\w*|buy-?in|public option|expan\w*|premiums?)\b", NOT_COVER, NOT_MCAID_SERVICE],
               [r"\b(?:short-term(?:,)? limited[- ]duration|association health plans?|catastrophic (?:health )?plans?|Small Business Health Options Program|health (?:insurance|coverage) across state lines)\b"],
               [r"\b(?:Medicaid|medical assistance) expansion\b"], [r"\bexpan\w* (?:of )?(?:Medicaid|medical assistance|Medi-Cal)\b(?! (?:coverage|services|benefits)\b)"],
               [r"\bexpansion (?:population|adults?|group)\b", r"\b(?:Medicaid|medical assistance)\b"],
               [r"\b(?:Medicaid|medical assistance|Medi-Cal|MassHealth|TennCare|SoonerCare|HUSKY|BadgerCare|KanCare|CHIP|children's health insurance program|(?:NJ )?FamilyCare|PeachCare|CoverKids|ARHOME|Healthy Indiana Plan|Apple Health|Medi-Cal) (?:eligibility|enrollment|expansion|buy-?in|coverage (?:for|to) (?:all |certain |low-income |eligible |uninsured )?(?:adults|children|immigrants|all|pregnant|postpartum|individuals|persons|people|residents|incarcerated|inmates|former foster|young adults|noncitizens|workers|women))\b", NOT_COVER, NOT_MCAID_SERVICE, r"!\b(?:eligibility (?:for|of) (?:hospitals?|providers?|facilit\w*|projects?|services|payments?)|for (?:the )?purposes? of (?:Medicaid|medical assistance) eligibility)\b"],
               [r"\b(?:(?:expan\w*|extend\w*|extension of|increas\w*|establish\w*|impos\w*|requir\w*|residency|regarding|calculat\w*|determin\w*|restor\w*|provid\w*|grant\w*|restor\w*|limit\w*|restrict\w*|terminat\w*|end\w*|reduc\w*|eliminat\w*|prohibit\w*|deny\w*|denial of|bar\w*)\W+(?:\w+\W+){0,8}?(?:eligib(?:le|ility) for)|(?:become|remain|shall be|not be|ineligible for|lose|losing|loss of)(?: eligible for)?) (?:the )?(?:state(?:\'s)? )?(?:Medicaid|medical assistance|Medi-Cal|MassHealth|TennCare|SoonerCare|HUSKY|BadgerCare|KanCare|CHIP|children's health insurance program|(?:NJ )?FamilyCare|PeachCare|CoverKids|ARHOME|Healthy Indiana Plan|Apple Health)(?! (?:payments?|reimbursement|funding|rates?|providers?|services|program funds))\b", NOT_COVER, NOT_MCAID_SERVICE, r"!\b(?:Court of Claims|vendors?|air ambulance|identification cards?|otherwise eligible)\b"],
               [r"\b(?:presumptive eligibility|continuous (?:eligibility|coverage|enrollment)|redetermination\w*|unwinding|disenroll\w*|auto(?:matic|-)? ?enroll\w*|express lane eligibility)\b", r"\b(?:Medicaid|medical assistance|Medi-Cal|MassHealth|TennCare|SoonerCare|HUSKY|BadgerCare|KanCare|CHIP|children's health insurance program|(?:NJ )?FamilyCare|PeachCare|CoverKids|ARHOME|Healthy Indiana Plan|Apple Health|Medi-Cal)\b", NOT_COVER, NOT_MCAID_SERVICE],
               [r"\bpostpartum (?:coverage|eligibility|period)\b", r"\b(?:Medicaid|medical assistance|Medi-Cal|CHIP)\b", r"\b(?:(?:12|twelve)[- ]months?|one year|365 days|\d+-day|extend\w*|extension|length)\b", r"!\b(?:depression|screening|doulas?|services? (?:for|of))\b"],
               [r"\b(?:special|open) enrollment periods?\b", r"\b(?:health|insurance|coverage|qualified health plans?|exchanges?|marketplaces?)\b", NOT_COVER, r"!\b(?:vouchers?|housing|retirement|pension|Medicare Part D)\b"],
               [r"\bhealth (?:insurance|benefits?|care) (?:exchanges?|marketplaces?)\b", r"!\bvoter registration\b"], [r"\bstate[- ]based (?:exchanges?|marketplaces?)\b"],
               [r"\b(?:Covered California|Connect for Health Colorado|Pennie|Get Covered (?:Illinois|New Jersey)|Maryland Health Connection|Nevada Health Link|Access Health CT|Washington Healthplanfinder|Covered Maine|BeWellnm|Kynect)\b"],
               [r"\b(?:premium (?:tax credits?|subsid\w*|assistance)|cost[- ]sharing reductions?)\b", r"\b(?:health|exchange|marketplace|qualified health plans?)\b", NOT_COVER],
               [r"\breinsurance\b", r"\b(?:health (?:insurance|benefit|care)|individual (?:health )?market|section 1332|1332 waiver)\b", NOT_COVER],
               [r"\b(?:Affordable Care Act|Patient Protection and Affordable Care Act|(?-i:ACA)(?! \d)|Obamacare)\b", r"\b(?:codif\w*|(?<!Patient )protect\w*|repeal\w*|pre-?existing|preexisting|essential health benefits|guaranteed issue|if (?:the )?(?:federal )?(?:act|law) is|invalidat\w*|struck down|marketplaces?|exchanges?)\b", NOT_COVER, r"!\b(?:defray\w*|section 1557|civil rights|voter registration|as an? essential health benefits?)\b"],
               [r"\bpre-?existing (?:medical )?conditions?\b", r"\b(?:health (?:insurance|benefit plans?|plans?|coverage)|insurers?|coverage|Medicare|Medigap|beneficiaries)\b", NOT_COVER],
               [r"\bguaranteed (?:issue|renewab\w*)\b", r"\bhealth\b", NOT_COVER],
               [r"\bessential health benefits?\b", r"\b(?:codif\w*|(?<!Patient )protect\w*|federal law|Affordable Care Act|(?-i:ACA)(?! \d))\b", NOT_COVER, r"!\b(?:defray\w*|in addition to (?:the )?essential health benefits|as an? essential health benefits?)\b"],
               [r"\b(?:uninsured rates?|(?:coverage|insurance) (?:for|to) (?:the )?uninsured|number of uninsured|uninsured (?:residents|individuals|people|population|children|adults|Texans|Californians|families|workers|immigrants)\W+(?:\w+\W+){0,5}?(?:coverage|insurance|enroll\w*|eligib\w*))\b", NOT_COVER, r"!\b(?:motorists?|motor vehicles?|underinsured motorist|uncompensated care|charity care|hospital (?:financial assistance|bills?)|medical debts?|employers'? fund)\b"],
               [r"\bhealth (?:insurance |care )?coverage (?:for|to) (?:all|every|undocumented|immigrants?|uninsured|residents)\b(?! (?:part-time |full-time )?(?:faculty|employees|staff|members))"],
               [r"\bindividual (?:health insurance )?market\b", r"\b(?:reinsurance|stabiliz\w*|affordab\w*|premium (?:assistance|subsid\w*|tax credits?)|public option)\b", NOT_COVER],
               [r"\bindividual (?:health insurance )?mandate\b|\bindividual (?:shared )?responsibility (?:payment|requirement|penalty)\b"]],
     # California's digests give the federal law's essential benefits as background on bills about other things.
     "none": [r"\bExisting federal law, the federal Patient Protection and Affordable Care Act \(PPACA\), requires a health benefit plan issuer that offers coverage in the small group or individual market to ensure that the coverage includes the essential health benefits package\b"],
     "filters": {"Single payer and universal coverage": [r"\bsingle[- ]payer\b", r"\buniversal\b", r"\bfor all\b", r"\bNew York Health Act\b"],
                 "Medicaid": [r"\bMedicaid\b", r"\bmedical assistance\b", r"\bMedi-Cal\b", r"\bMassHealth\b", r"\bTennCare\b", r"\bSoonerCare\b", r"\bHUSKY\b", r"\bBadgerCare\b", r"\bKanCare\b"],
                 "Public option": [r"\bpublic (?:health (?:insurance |care |benefit )?)?options?\b", r"\bColorado Option\b", r"\bCascade (?:Care|Select)\b", r"\bBattle Born State Plans?\b", r"\bbuy-?in\b", r"\bbasic health (?:program|plan)\b", r"\bEssential Plan\b", r"\bMinnesotaCare\b"],
                 "Marketplaces and the ACA": [r"\bexchanges?\b", r"\bmarketplaces?\b", r"\bAffordable Care Act\b", r"(?-i)\bACA\b", r"\bpremium (?:tax credits?|subsid|assistance)", r"\breinsurance\b", r"\bpre-?existing\b", r"\bessential health benefits?\b"]}},
    {"id": "assault", "group": "Public safety and courts", "name": "Sexual assault and domestic violence", "words": ["rape", "rape kit", "domestic violence", "stalking", "protective order", "sex trafficking", "child sexual abuse", "title ix"], "body": 0,
     # Rape kits and their backlogs, time limits for sexual abuse cases, campus sexual assault, survivors' rights and
     # confidentiality, protective orders, domestic and dating violence and stalking, sex trafficking, child sexual abuse.
     # Not the sex offender registry's administration, or bills that name domestic violence in a list of reasons
     # (custody, divorce, leave).
     "rules": [[r"\bsexual(?:ly)? (?:assault\w*|abuse[ds]?|abusing|batter\w*|violence|misconduct|exploit\w*|predators?|offen[cs]es?|crimes?|contact|conduct) (?:with |of |against )?(?:an? )?(?:minors?|child\w*|victims?|survivors?|students?|patients?|persons?|individuals?|adults?|vulnerable)\b", NOT_REGISTRY, NOT_CRIMELIST],
               [r"\bsexual(?:ly)? (?:assault\w*|abuse[ds]?|battery|violence|misconduct|exploitation)\b", NOT_REGISTRY, NOT_CRIMELIST],
               [r"\brap(?:e|es|ed|ist|ists)\b", r"!\b(?:canola|seed|oilseed|abortions?|pregnancy (?:resulted|resulting))\b", NOT_CRIMELIST], [r"\b(?:rape|sexual assault|forensic|evidence) kits?\b"], [r"\bsexual assault (?:nurse )?examin\w*\b"],
               [r"\b(?:child (?:molest\w*|sexual|sex abuse)|molestation|incest(?! (?:or|and) rape)(?!,? (?:in|to)? ?(?:which|the) (?:pregnancy|abortion))|indecent liberties|lewd (?:or lascivious|acts?|conduct) (?:with|upon|on|in the presence of) (?:a )?(?:child|minor))\b", r"!\babortions?\b"],
               [r"\b(?:child|children|minors?) (?:sexual abuse|sex abuse|pornography) material\b|\bchild pornography\b|(?-i:\bCSAM\b)"],
               [r"\bdomestic (?:violence|abuse|batter\w*|assault)\b", NOT_PASSING], [r"\b(?:intimate partner|dating|family|teen dating) (?:violence|abuse)\b", NOT_PASSING],
               [r"\bstalk(?:ing|ers?|ed)?\b", r"!\b(?:corn|celery|plant|stalk cutting|(?:bodily injury|death|property damage),? or stalking)\b", NOT_PASSING],
               [r"\b(?:protective orders?|orders? (?:of|for) protection|protection (?:from abuse|orders?)|restraining orders?|no[- ]contact orders?)\b",
                r"\b(?:abus\w*|violence|stalk\w*|harass\w*|victims?|assault\w*|threat\w*)\b", r"!\b(?:Election Code|extreme risk|red flag|risk protection|gun violence|workplace violence|firearms? (?:restraining|protective)|discovery|trade secrets?|confidential (?:business|commercial)|subpoena)\b", NOT_PASSING],
               [r"\bsex trafficking\b|\btrafficking (?:of|in) (?:persons|minors|children|humans) for (?:sexual|commercial sex)\b|\bcommercial sex(?:ual)? (?:exploitation|acts?)\b"],
               [r"\b(?:human|child) trafficking\b|\btrafficking (?:offenses?|victims?|survivors?|of (?:persons|minors|children))\b|\b(?:anti-?|human )trafficking\b", r"!\b(?:forced labor|Uyghur|supply chains?|labor trafficking|drugs?|fentanyl|narcotics?|firearms?|weapons?)\b"],
               [r"\bsex(?:ual)? offen[cs]es?\b|\bsexual (?:trauma|performance (?:of|by) a (?:child|minor))\b", NOT_REGISTRY, NOT_CRIMELIST],
               [r"\bsexual (?:abuse|assault) survivors?\b|\bsurvivors? of (?:sexual|domestic|rape|dating|child sexual)\b|\bvictims? of (?:sexual|domestic|rape|dating|stalking|child sexual)\b", NOT_PASSING],
               [r"(?-i)\bTitle IX\b", r"\b(?:sexual|harass\w*|assault|misconduct|grievance)\b"],
               [r"\bnon-?consensual (?:sexual|intimate|dissemination)|\b(?:revenge porn\w*|intimate (?:images?|visual depictions?))\b", r"\b(?:disseminat\w*|distribut\w*|shar\w*|publish\w*|consent)\b"],
               [r"\bsextortion\b"], [r"\bgrooming\b", r"\b(?:child|minors?|sexual)\b"], [r"\b(?:spousal|marital) rape\b|\bsexual consent\b"], [r"\baffirmative consent\b", r"\bsex\w*\b"]],
     # Leave laws list domestic violence and sexual assault among the reasons for leave (also under Paid leave).
     # Boards and task forces with a member from a state coalition against domestic or sexual violence.
     "none": [r"\b(?:(?:paid )?(?:family|sick|medical)|family and medical|safe) (?:leave|time)\b", r"\bCoalition (?:to End|Against|on|for the Prevention of) (?:Domestic|Sexual)"],
     "filters": {"Rape kits": [r"\bkits?\b", r"\bsexual assault (?:nurse )?examin", r"\bforensic (?:medical )?exam", r"\bsexual assault evidence\b"],
                 "Time limits": [r"\bstatutes? of limitations?\b", r"\blimitations? period", r"\bperiod of limitation", r"\btime limits?\b", r"\brevival\b", r"\brevive\w*\b", r"\blook-?back window", r"\bwithin \w+ years\b"],
                 "Domestic violence and stalking": [r"\bdomestic (?:violence|abuse|batter|assault)", r"\b(?:intimate partner|dating|family) (?:violence|abuse)\b", r"\bstalk", r"\bprotective orders?\b", r"\borders? (?:of|for) protection\b", r"\bprotection (?:from abuse|orders?)\b", r"\brestraining orders?\b", r"\bno[- ]contact orders?\b"],
                 "Child sexual abuse": [r"\bchild (?:sexual|sex abuse|molest|pornograph)", r"\bsexual (?:abuse|assault|exploitation|conduct|contact|misconduct) (?:of|with|against) (?:a )?(?:minor|child)", r"\bminors?\b.{0,60}\bsexual|\bsexual\b.{0,60}\bminors?\b", r"\bincest\b", r"\bgrooming\b", r"(?-i)\bCSAM\b"],
                 "Trafficking": [r"\btrafficking\b", r"\bcommercial sex"],
                 "Campus": [r"\b(?:campus|colleges?|universit\w*|postsecondary|higher education)\b"]}},
    # The seventh batch (2026-11-17; notes/issues-check.md).
    {"id": "homeless", "group": "Housing", "name": "Homelessness and camping bans", "words": ["homeless", "encampments", "camping ban", "unhoused", "housing first"], "body": 0,
     # Public camping and sleeping bans, encampment sweeps, housing first, homeless services and their funding, students
     # experiencing homelessness. Not homeless animals.
     "rules": [[r"\bhomeless\w*\b", r"\b(?:homelessness|homeless (?:shelters?|services|programs?|persons|individuals|people|population|youth|veterans|families|response|assistance|prevention|housing|encampments?|camps?|coordinat\w*|count|bill of rights|students|children)|shelters?|encampments?|unhoused|housing (?:first|assistance|programs?|vouchers?|grants?|stability))\b",
                r"!\bhomeless (?:animals?|pets?|dogs?|cats?)\b", r"!\b(?:foster care|disabilit\w*|residential care),? (?:\w+ ){0,2}?(?:or|and) (?:are |who are )?homeless\b", r"!\b(?:hospitals|jails|nursing homes|correctional facilities|group homes),? (?:\w+ ){0,3}?(?:and|or) homeless shelters\b"], [r"\bunhoused\b"], [r"(?-i:\b[Hh]ousing [Ff]irst\b)"],
               [r"\b(?:encampments?|(?:unauthori[sz]ed |unpermitted |public |unlawful |illegal )?camping)\b", r"\b(?:public (?:property|land|spaces?)|rights?-of-way|shelters?|housing|unauthori[sz]ed|prohibit\w*|ban|bans|sleeping|homeless\w*|unhoused|sidewalks?|underpass\w*|clear\w*|sweeps?)\b",
                r"!\b(?:campgrounds?|campsites?|state parks?|recreation\w*|hunting|fishing|RV parks?|camping (?:fees?|permits?|season)|day camps?|summer camps?|expressive activit\w*|protests?|demonstrat\w*|institutions? of higher education|higher education institutions?|universit\w*|colleges?|tents?|sleeping bags?|flame\w*)\b"],
               [r"\b(?:sleeping|sleep) (?:in|on) (?:public|streets?|sidewalks?)\b|\bpublic sleeping\b|\bsit[- ]lie\b"], [r"\b(?:unlawful|unauthori[sz]ed|unpermitted|illegal) camping\b|\bcamping bans?\b", r"!\b(?:campgrounds?|state parks?|wildlife|hunting)\b"]],
     "filters": {"Camping and sleeping bans": [r"\bcamping\b", r"\bencampments?\b", r"\bsleep(?:ing)?\b", r"\bsit[- ]lie\b"],
                 "Housing first and services": [r"\bhousing first\b", r"\bsupportive housing\b", r"\bshelters?\b", r"\bservices\b", r"\bgrants?\b", r"\bfunding\b"],
                 "Students": [r"\bstudents?\b", r"\bschools?\b", r"\byouth\b"]}},
    {"id": "incometax", "group": "Taxes", "name": "Income tax cuts", "words": ["income tax", "flat tax", "tax cut", "tax rates"], "body": 0,
     # Personal income tax rates: cuts, a flat rate, phase-outs and elimination, triggers that lower the rate. Not a
     # credit, deduction or exemption for one kind of income or person, and not corporate rates alone.
     "rules": [[r"\b(?:income tax(?:es)? (?:rates?|brackets?)|rates? of (?:the )?(?:\w+ )?income tax|tax rates? (?:on|for|of) (?:individual|personal|taxable) income|rates? of tax (?:on|for|imposed on) (?:individuals|residents|taxable income))\b",
                r"\b(?:reduc\w*|cut|cuts|lower\w*|decreas\w*|phas\w*[- ](?:out|down)|eliminat\w*|repeal\w*|abolish\w*|flat|single rate|triggers?|accelerat\w*)\b",
                r"!\b(?:corporat\w* (?:net )?(?:income |franchise )?tax rates?|pass-through|incentiv\w*|investment accounts?|foreign jurisdictions?|reincorporat\w*|carried interest|outsourc\w*|inversions?|foreign subsidiar\w*|(?:electrical|public utility|utility) corporations?|extend\w* (?:the )?(?:existing|current|top) (?:\w+ )?rates?|restor\w* the (?:\w+ )?(?:income tax )?rates?|higher (?:\w+ ){0,3}?rates? permanent)\b", NOT_TAXITEM],
               [r"\bflat (?:income )?tax\b|\bsingle (?:income )?tax rate\b", r"\bincome\b", NOT_TAXITEM, r"!\b(?:gambling|wager\w*|lottery)\b"],
               [r"\b(?:eliminat\w*|repeal\w*|abolish\w*|phas\w*[- ]out|end\w*)\b\W+(?:\w+ ){0,4}?(?:the )?(?:state |personal |individual )?income tax(?:es)?\b(?! (?:\w+ )?(?:on|for|credits?|deductions?|exemptions?|exclusions?|liability|incentives?|reciprocity|withholding|returns?|refunds?|modifications?|subtractions?|additions?|assessments?))", NOT_TAXITEM, r"!\b(?:(?<!individual and )(?<!personal and )(?:corporat\w*|pass-through|franchise) (?:net )?income tax\w*|school district (?:\w+ )?(?:and )?income tax\w*|defunct)\b"],
               [r"\b(?:personal|individual|state) income tax (?:rate )?(?:reductions?|cuts?|relief)\b|\bincome tax rates? (?:amendments|reductions?)\b|\b(?:reduc\w*|lower\w*) (?:the )?(?:personal |individual )?income tax (?:rate )?to zero\b", NOT_TAXITEM, r"!\b(?:incentiv\w*|investment accounts?|data centers?)\b"],
               [r"\bno (?:state )?income tax\b(?! on corporat)"],
               [r"\b(?:reduc\w*|eliminat\w*|lower\w*|decreas\w*|phase\w*-in a reduction in)\b (?:\w+ ){0,5}?(?:tax )?rates?\b|\brate reductions?\b", r"\b(?:individual|personal) income tax", NOT_TAXITEM, r"!\b(?:corporat\w* (?:net )?(?:income |franchise )?tax rates?|county income tax|incentiv\w*|sales and use tax rates?)\b"]],
     "filters": {"Elimination": [r"\beliminat", r"\brepeal", r"\babolish", r"\bphas\w*[- ]out\b", r"\bno (?:state )?income tax\b"],
                 "Flat tax": [r"\bflat\b", r"\bsingle (?:income )?tax rate\b"]}},
    {"id": "homeinsurance", "group": "Housing", "name": "Homeowners insurance", "words": ["home insurance", "property insurance", "fair plan", "citizens", "insurance rates"],
     # Homeowners and property insurance: rates, insurers leaving or not renewing, insurers of last resort (Citizens, FAIR
     # plans), discounts for fortified roofs and wildfire or hurricane mitigation, flood insurance. Not auto or title
     # insurance.
     # Bills that only extend the National Flood Insurance Program's authorization are left out (the owner, 2026-11-17).
     "none": [r"\b(?:NFIP (?:Automatic )?(?:Extension|Stopgap)|National Flood Insurance Program (?:Automatic )?Extension|extend (?:the (?:authorization|authority) (?:of|for) )?the National Flood Insurance Program (?:through|until|to))\b"],
     "rules": [[r"\b(?:homeowners?'?s?|homeowner's|residential property|property|dwelling|hazard|windstorm|wind(?:storm)? and hail|condominium|renters'?|flood) insurance\b(?! (?:valuation|taxes?) )", r"!\b(?:title insurance|property and casualty insurance|casualty insurance|auto(?:mobile)? insurance|liability and property insurance|commercial property insurance|credit property insurance|floodplain (?:management|regulations?|ordinances?))\b"],
               [r"\b(?:homeowners?'?s?|residential property|dwelling|property insurance) (?:polic(?:y|ies)|coverage|insurers?|premiums?|claims?)\b"],
               [r"\bFAIR plans?\b|\bFair Access to Insurance Requirements\b"], [r"\bCitizens Property Insurance\b"], [r"\binsurers? of last resort\b|\bresidual (?:property )?market\b"],
               [r"\b(?:fortif\w*|mitigation|hardening|wind-?resistant|roof)\b", r"\b(?:insurance|premiums?|insurers?)\b", r"\b(?:homes?|roofs?|wildfire|hurricane|windstorm|dwellings?|residential)\b", r"!\b(?:health|auto(?:mobile)?|motor vehicles?|crop)\b"],
               [r"\bwindstorm insurance\b|\bTexas Windstorm Insurance Association\b|\bwind pool\b"]]},
    {"id": "bail", "group": "Public safety and courts", "name": "Bail and pretrial release", "words": ["bail", "cash bail", "pretrial detention", "bail reform", "bond"],
     # Cash bail and bail reform, pretrial detention and release conditions, bail bond agents.
     "body": 0,
     "rules": [[r"\bbail(?: bonds?(?:men|man)?| agents?| reform| schedules?| funds?)?\b", r"!\b(?:bail ?outs?|bailing out)\b", r"!\b(?:promise to appear|released on bail or on (?:their|his or her) own recognizance pending trial)\b"], [r"\bpretrial (?:release|detention|services|risk|supervision|detainees?|monitoring|justice)\b"],
               [r"\brelease (?:on|without) (?:recognizance|bond|bail)\b"], [r"\bpretrial (?:reform|release|fairness)\b"],
               [r"\b(?:set\w* (?:a |the )?bonds?|bond (?:amounts?|conditions?|hearings?|schedules?|forfeitures?))\b", r"\b(?:defendants?|arrest\w*|criminal|accused|pretrial|offen[cs]es?|charged)\b", r"!\b(?:surety bonds? for (?:contractors?|notaries|licensees?)|performance bonds?|bonded indebtedness)\b"], [r"\b(?:own|personal) recognizance\b"],
               [r"\b(?:appearance|cash|surety|secured|unsecured|personal) bonds?\b", r"\b(?:defendants?|arrest\w*|criminal|accused|pretrial|release)\b"]]},
    {"id": "overdose", "group": "Public safety and courts", "name": "Drug penalties and overdoses", "words": ["fentanyl", "naloxone", "narcan", "overdose", "test strips", "xylazine", "drug-induced homicide", "harm reduction"],
     # Fentanyl and other drug crimes and penalties, drug-induced homicide, naloxone, test strips, overdose prevention
     # sites, Good Samaritan laws, syringe services. Cannabis, psychedelics and kratom have their own issues.
     "rules": [[r"\bfentanyl\w*\b"], [r"\boverdos\w*\b"], [r"\bnaloxone\b|\bnarcan\b|\bopioid (?:antagonists?|overdose reversal)\b"], [r"\bxylazine\b|\bnitazenes?\b|\bcarfentanil\b"],
               [r"\btest(?:ing)? strips?\b", r"\b(?:fentanyl|drugs?|xylazine|controlled substances?)\b"], [r"\bdrug[- ]induced (?:homicide|death)\b"],
               [r"\bGood Samaritan\b", r"\b(?:overdos\w*|drugs?|controlled substances?|opioids?)\b"],
               [r"\b(?:overdose prevention|safe (?:injection|consumption)|supervised (?:injection|consumption)) (?:sites?|centers?|programs?|facilit\w*|services)\b"],
               [r"\b(?:syringe|needle) (?:services|exchanges?|access|services programs?)\b"], [r"\bharm reduction\b", r"\b(?:drugs?|opioids?|syringes?|overdos\w*|substance)\b"],
               [r"\b(?:drug|narcotics?) (?:possession|trafficking|traffickers?|dealing|dealers?|distribution|offen[cs]es?|crimes?|penalt\w*|sentenc\w*|decriminali[sz]\w*|paraphernalia)\b", NOT_OTHERDRUGS],
               [r"\bcontrolled substances?\b", r"\b(?:penalt\w*|traffick\w*|possess\w*|sentenc\w*|felon\w*|misdemeanor|decriminali[sz]\w*|mandatory minimum|unlawful (?:delivery|distribution|manufactur\w*))\b", NOT_OTHERDRUGS, r"!\b(?:prescri\w*|pharmac\w*|practitioners?|monitoring program|veterinar\w*)\b"]],
     "filters": {"Fentanyl": [r"\bfentanyl", r"\bcarfentanil\b", r"\bnitazenes?\b", r"\bxylazine\b"],
                 "Naloxone and test strips": [r"\bnaloxone\b", r"\bnarcan\b", r"\bopioid (?:antagonists?|overdose reversal)\b", r"\btest(?:ing)? strips?\b"],
                 "Overdose prevention sites and harm reduction": [r"\boverdose prevention (?:sites?|centers?|programs?)", r"\b(?:safe|supervised) (?:injection|consumption)\b", r"\b(?:syringe|needle) (?:services|exchanges?|access)\b", r"\bharm reduction\b"],
                 "Penalties": [r"\bpenalt", r"\bsentenc", r"\btraffick", r"\bdrug[- ]induced\b", r"\bfelon", r"\bhomicide\b", r"\bmandatory minimum"]}},
    {"id": "contraception", "group": "Health", "name": "Contraception", "words": ["birth control", "plan b", "emergency contraception", "right to contraception"],
     # The right to contraception, insurance coverage, pharmacists prescribing birth control, emergency contraception,
     # vasectomy coverage. Not wildlife fertility control.
     # Abortion bans say they don't reach contraception; that isn't a contraception bill.
     "none": [r"\b(?:does not|shall not|do not) (?:\w+ ){0,4}?(?:include|apply to|prohibit|restrict) (?:\w+ ){0,6}?(?:contracept\w*|birth control)\b", r"\b(?:definition of abortion|abortion\W+(?:\w+\W+){0,3}?(?:does not|shall not) (?:include|mean))\b"],
     "rules": [[r"\bcontracept\w*\b", NOT_WILDLIFE], [r"\bbirth control\b", NOT_WILDLIFE], [r"\bfamily planning\b", NOT_WILDLIFE, r"!\bnatural family planning\b"], [r"\b(?:levonorgestrel|ulipristal)\b"], [r"\bPlan B\b", r"\b(?:contracept\w*|pills?|morning[- ]after|emergency|pharmac\w*)\b"],
               [r"\b(?:vasectom\w*|tubal ligations?)\b", r"\b(?:coverage|insur\w*|cost[- ]sharing|health (?:benefit )?plans?)\b"]],
     "filters": {"Right to contraception": [r"\bright to (?:obtain |use |access )?contracept", r"\bright to (?:obtain |use |access )?birth control\b"],
                 "Insurance coverage": [r"\bcoverage\b", r"\binsur", r"\bcost[- ]sharing\b", r"\bMedicaid\b", r"\bhealth (?:benefit )?plans?\b"],
                 "Pharmacists": [r"\bpharmacists?\b", r"\bover[- ]the[- ]counter\b"],
                 "Emergency contraception": [r"\bemergency contracept", r"\bPlan B\b", r"\blevonorgestrel\b", r"\bulipristal\b"]}},
    {"id": "mentalhealth", "group": "Health", "name": "Mental health and 988", "words": ["988", "crisis line", "suicide prevention", "involuntary commitment", "mental health parity", "crisis response"], "body": 4,
     # The 988 crisis line and its fees, crisis response teams and centers, involuntary commitment and assisted outpatient
     # treatment, mental health in schools, mental health parity. Not every bill naming mental health services.
     "rules": [[r"(?<![\d$.,-])\b988\b(?![\d,.]\d)", r"\b(?:crisis|suicide|lifeline|mental|behavioral|hotline|telephone|fee|surcharge)\w*\b"],
               [r"\b(?:suicide (?:and|&) crisis|crisis (?:lifeline|hotline|line|stabilization|response|intervention|receiving|centers?|care|services|teams?|units?))\b", r"\b(?:mental|behavioral|psychiatric|suicid\w*|substance use)\b", r"!\b(?:pregnancy|rape|sexual assault|domestic violence|caregivers?)\b"],
               [r"\bmobile (?:crisis|response) (?:teams?|units?|services)\b|\bcrisis (?:intervention teams?|call cent(?:er|re)s?|response services)\b|\bbehavioral health (?:response|crisis) (?:units?|teams?|services)\b", r"!\b(?:pregnancy|rape|sexual assault|domestic violence|caregivers?)\b"],
               [r"\binvoluntar\w* (?:commitment|treatment|hospitali[sz]ation|admissions?|examinations?|evaluations?|outpatient|holds?|psychiatric|detention|mental health)\b"],
               [r"\b(?:assisted outpatient treatment|civil commitment|emergency (?:custody|detention|evaluation|hold) (?:order|of|for)|Baker Act|Kendra's Law)\b", r"!\bsexually violent\b"],
               [r"\bparity\b", r"\b(?:mental health|behavioral health|substance use disorder|psychiatric)\b"],
               [r"\b(?:(?:school|student|pupil)s?'? (?:mental|behavioral) health|school-based (?:mental|behavioral) health|mental health days?|(?:mental|behavioral) health (?:\w+ ){0,3}?(?:in|for|at|of|to) (?:public )?(?:schools?|students?|pupils?)|(?:schools?|school districts?|students?|pupils?)'? (?:\w+ ){0,3}?(?:mental|behavioral) health (?:services|supports?|resources|screenings?|assessments?|programs?|professionals?|counselors?|days?|education|instruction|awareness|first aid|needs|absences?))\b", r"!\b(?:nursing|medical|social work|graduate) (?:schools?|students?)\b", r"!\b(?:careers?|degrees?|workforce|loan (?:repayment|forgiveness)|scholarships?|mobile devices?|cell ?phones?|bus drivers?|educator preparation|athletes?)\b"],
               [r"\bsuicide prevention\b", r"\b(?:schools?|students?|hotline|crisis|lifeline|veterans?|youth|plans?|training)\b"]],
     "filters": {"988 and crisis response": [r"\b988\b", r"\bcrisis\b", r"\bmobile (?:crisis|response)\b"],
                 "Involuntary treatment": [r"\binvoluntar", r"\bcivil commitment\b", r"\bassisted outpatient\b", r"\bemergency (?:custody|detention|evaluation|hold)\b", r"\bBaker Act\b", r"\bKendra's Law\b"],
                 "Schools": [r"\bstudents?\b", r"\bschools?\b", r"\bpupils?\b"],
                 "Parity": [r"\bparity\b"]}},
    {"id": "foodadditives", "group": "Health", "name": "Food additives and dyes", "words": ["food dyes", "red 40", "red dye", "additives", "ultra-processed", "maha", "seed oils"],
     # Bans and warning labels for food dyes and additives (Red 40, Red 3, titanium dioxide, potassium bromate), additives
     # in school food, ultra-processed food, "generally recognized as safe" loopholes, "Make America Healthy Again" food
     # bills. Not cosmetics alone.
     "none": [r"\b(?:animal feed|animal food|feed additives?|zootechnical|pet foods?|livestock|hermit crabs?|goldfish|industrial hemp|cannabis|cannabinoids?|cannabidiol|CBD|fortification|cottage food|sexual performance|menstrual|soil|dietary supplements?|diet pills?)\b"],
     "rules": [[r"\b(?:food|colou?r) (?:dyes?|additives?|colou?rings?|chemicals?)\b"], [r"\b(?:synthetic|artificial) (?:dyes?|colou?rs?|food colou?r\w*|colou?r additives?|colou?rings?)\b"],
               [r"(?-i:\b(?:Red|Yellow|Blue|Green|Citrus Red|Orange B)\b)(?: No\.?| Dye)? ?(?:3|40|5|6|1|2)\b", r"\b(?:food|dyes?|colou?r|beverages?|candy|schools?|ingredients?)\b"],
               [r"\b(?:titanium dioxide|brominated vegetable oil|potassium bromate|propylparaben|azodicarbonamide|butylated hydroxy\w*|tert-?butylhydroquinone)\b", r"!\bcosmetics?\b"],
               [r"\bultra-?processed\b"], [r"\bgenerally recognized as safe\b"], [r"\bseed oils?\b"],
               [r"\badditives?\b", r"\b(?:food|foods|drinks?|beverages?|meals?|snacks?|candy)\b", r"!\b(?:fuel|gasoline|diesel|concrete|manufacturing|vaccines?|tobacco|vapor|e-cigarettes?|IV bags?|medical)\b"],
               [r"\bMake America Healthy Again\b|(?-i:\bMAHA\b)", r"\b(?:food|nutrition|ingredients?|meals?|dyes?|additives?|snacks?|SNAP)\b"]],
     "filters": {"Dyes": [r"\bdyes?\b", r"\bcolou?r", r"(?-i:\bRed\b)"], "School food": [r"\bschools?\b", r"\bstudents?\b"],
                 "Labels and warnings": [r"\blabel", r"\bwarning", r"\bdisclos"], "Ultra-processed food": [r"\bultra-?processed\b"]}},
    {"id": "schoolmeals", "group": "Education", "name": "School meals", "words": ["school lunch", "free school meals", "school breakfast", "lunch debt", "lunch shaming"], "body": 4, "lead": False, "short": 2,
     # Universal free school meals, meal debt and lunch shaming, school breakfast, reimbursements for school meals.
     "rules": [[r"\bschool (?:meals?|lunch\w*|breakfasts?|nutrition|food (?:service|program|authorit)\w*)\b(?! Act)", r"!\b(?:child and adult care food program|child care|early childhood|restaurants?|caterers?|retail grocers?|food donations?)\b", r"!\b(?:eligible|eligibility|qualif\w*) (?:\w+ ){0,4}?(?:for|in) (?:the )?(?:free (?:and|or) reduced[- ]price |national )?school (?:lunch|meals?|breakfast)"],
               [r"\b(?:universal|free|reduced[- ]price|healthy) (?:school )?(?:meals?|lunch\w*|breakfasts?)\b", r"\b(?:schools?|students?|pupils?|school districts?)\b", r"!\b(?:(?:eligible|qualif\w*|eligibility) (?:\w+ ){0,3}?(?:for |to receive |to participate in )?(?:the )?free (?:or|and) reduced[- ]price (?:school )?(?:lunch|meals?)|reduced-price lunch rate)\b"],
               [r"\b(?:meal|lunch) (?:debts?|shaming|shame|charges?|accounts?)\b", r"\b(?:schools?|students?|pupils?)\b"], [r"\bbreakfast after the bell\b"],
               [r"\bcommunity eligibility provision\b"], [r"\bschool food\b"]],
     "filters": {"Free meals for all": [r"\buniversal\b", r"\bfree (?:school )?(?:meals?|lunch|breakfast)", r"\bcommunity eligibility\b", r"\ball students\b"],
                 "Meal debt and lunch shaming": [r"\bdebts?\b", r"\bshaming\b", r"\bshame\b", r"\bunpaid\b"]}},
    {"id": "plastics", "group": "Environment and energy", "name": "Plastics and packaging", "words": ["plastic bags", "plastic bag ban", "styrofoam", "microplastics", "epr", "bottle bill", "straws"], "body": 0,
     # Single-use plastic and bag bans, polystyrene foam, extended producer responsibility for packaging, microplastics,
     # recycling labels, bottle deposits, chemical recycling. Not plastic surgery.
     "rules": [[r"\bplastics?\b", r"\b(?:bags?|bottles?|straws?|waste|pollution|single[- ]use|packaging|recycl\w*|bans?|prohibit\w*|foam|containers?|utensils?|cutlery|foodware|products?|microplastics?|resins?|polymers?|litter|marine|ocean|compost\w*)\b", r"!\b(?:plastic (?:surger\w*|surgeons?|and reconstructive)|plastic explosives?|plastic (?:cards?|money|bullets?|applicators?)|kinetic impact|projectiles?|firearms?|frames?|receivers?|correctional|inmates?|alcoholic beverages?|budget trailer)\b"],
               [r"\b(?:single[- ]use|disposable|carry-?out|checkout) (?:bags?|cups?|utensils?|straws?|containers?|foodware|food service ware|products?|packaging|items?|beverage)\b"],
               [r"\bproducer responsibility\b", r"\b(?:packag\w*|paper products|plastics?)\b", r"!\b(?:paint|batter(?:y|ies)|mattress\w*|carpet|electronics?|pharmaceutical\w*|tires?)\b"], [r"\bpackaging\b", r"\b(?:producer responsibility|stewardship|packaging (?:waste|reduction|materials? (?:reduction|recovery))|(?:reduc\w*|reusable|refillable|compostable|recyclable|plastic|toxic\w*) (?:\w+ )?packaging|post-consumer|producers? of packaging|packaging producers?)\b", r"!\b(?:cannabis|marijuana|tobacco|nicotine|child-resistant|meat|seafood|reduced oxygen|homemade food|voter)\b"],
               [r"\b(?:polystyrene|styrofoam|expanded polystyrene)\b"], [r"\bmicro-?plastics?\b|\bnanoplastics?\b|\bmicrobeads?\b"],
               [r"\brecycl\w* (?:labels?|symbols?|claims?)\b|\bchasing arrows\b|\brecyclab\w* (?:claims?|labels?|packaging|plastics?)\b", r"!\bmetals?\b"], [r"\b(?:bottle (?:bill|deposits?)|(?:beverage )?container deposit\w*|container redemption|redemption cent(?:er|re)s?)\b"],
               [r"\b(?:advanced|chemical) recycling\b"], [r"\bbags?\b", r"\b(?:fees?|ban|bans|prohibit\w*|paper|reusable|retail\w*|stores?)\b", r"\b(?:carry-?out|checkout|grocery|shopping|retail)\b", r"!\b(?:body bags?|air ?bags?|bean bags?|sandbags?|evidence bags?|ballots?|diaper bags?|gift bags?|garments?|tariff|alcoholic beverages?)\b"]],
     "filters": {"Bag and foam bans": [r"\bbags?\b", r"\bpolystyrene\b", r"\bstyrofoam\b", r"\bstraws?\b", r"\bsingle[- ]use\b"],
                 "Producer responsibility": [r"\bproducer responsibility\b", r"(?-i:\bEPR\b)"],
                 "Microplastics": [r"\bmicro-?plastics?\b", r"\bnanoplastics?\b", r"\bmicrobeads?\b"],
                 "Bottle deposits": [r"\bbottle (?:bill|deposits?)\b", r"\bcontainer deposit", r"\bredemption\b"]}},
    {"id": "heat", "group": "Jobs and workers", "name": "Heat protections for workers", "words": ["heat illness", "extreme heat", "water breaks", "heat standard", "heat stress"],
     # Heat illness standards for workers outdoors and indoors (water, rest, shade), and laws that keep cities and counties
     # from setting their own.
     "rules": [[r"\bheat(?:[- ]related)? (?:illness\w*|stress|exposure|safety|standards?|injur\w*|protections?|strokes?|exhaustion|index|hazards?|plans?)\b", r"\b(?:workers?|employ\w*|workplaces?|occupational|outdoor work|laborers?|OSHA)\b", r"!\b(?:students?|athlet\w*|interscholastic|school sports)\b"],
               [r"\b(?:extreme|excessive|high|indoor) (?:heat|temperatures?)\b", r"\b(?:workers?|employees?|workplaces?|occupational|outdoor work|laborers?)\b", r"!\b(?:students?|athlet\w*|tenants?|rental|dwelling|cooling centers?)\b"],
               [r"\b(?:water|rest|shade|cool-?down) (?:and rest )?breaks?\b", r"\b(?:heat|temperatures?|hot)\b", r"\b(?:workers?|employ\w*|workplaces?)\b"],
               [r"\bworking conditions\W+(?:\w+\W+){0,3}?temperatures?\b"]]},
    {"id": "samesex", "group": "Rights", "name": "Same-sex marriage", "words": ["gay marriage", "marriage equality", "obergefell", "respect for marriage"],
     # Bills that protect marriage equality in state law or repeal old bans, and bills against it (marriage as between a man
     # and a woman, nullifying Obergefell). Resolutions urging the Supreme Court to reverse Obergefell aren't in the
     # data (resolutions are left out). Covenant marriage is about divorce, not counted.
     "rules": [[r"\bsame[- ](?:sex|gender) (?:marriages?|spouses?|unions?)\b"], [r"\bsame[- ](?:sex|gender) couples?\b", r"\bmarri\w*\b", r"!\b(?:infertility|in vitro|IVF|fertility|assisted reproduct\w*)\b"], [r"\bmarriage equality\b(?! for disabled)"], [r"\bObergefell\b"], [r"\bRespect for Marriage\b"], [r"\bDefense of Marriage\b"], [r"\bmarriages? between (?:two )?persons of the same (?:sex|gender)\b"],
               [r"\b(?:definition of marriage|defin\w* marriage)\b", r"!\bcommon[- ]law\b"],
               [r"\bmarriages?\b", r"\b(?:between (?:a|one) man and (?:a|one) woman|one man and one woman|two persons regardless of|regardless of (?:the )?(?:sex|gender)|natural marriage|(?:man|husband) and (?:a )?(?:woman|wife) (?:only|exclusively))\b"]]},
]


def _compile(p):
    if p.startswith("(?-i)"):
        return re.compile(p[5:])
    return re.compile(p, re.I)


# Anti-ESG and boycott laws list the industries and causes a company mustn't be penalized for ("companies that boycott
# businesses because the business engages in the fossil fuel or firearm industry ... or does not facilitate access to
# abortion or sex or gender change surgery": Alabama SB 261 of 2023). A mention there of abortion or gender surgery is
# the ESG issue's, not abortion's or transgender people's: those two skip a window that has one. Firearms keeps them (the
# owner's choice 2026-11-17: "firearm industry nondiscrimination" laws are followed as gun bills too).
NOT_BOYCOTT = (r"\b(?:boycott\w*|environmental, social,? (?:and|or|&) (?:corporate )?governance|economic boycott criteria"
               r"|corporate governance standards|(?:discriminat\w*) against (?:a |the )?(?:firearm|fossil fuel|energy|oil and gas)\w* "
               r"(?:industr\w*|compan\w*|entit\w*|trade associations?))\b|(?-i:\bESG\b)")
BOYCOTT_SKIP = {"abortion", "transgender"}


class _NotBoycott:
    """The exclusion above, except where "boycott" is a labor one (a labor peace agreement barring "picketing, work
    stoppages, boycotts": Hawaii SB 2241 of 2023 is still a cannabis bill)."""
    pat = re.compile(NOT_BOYCOTT, re.I)
    labor = re.compile(r"\b(?:labor peace|work stoppages?|picketing|labor organi[sz]ations?|strikes?)\b", re.I)

    def search(self, win):
        return self.pat.search(win) and not self.labor.search(win)

for _issue in ISSUES:
    _issue["_rules"] = [([_compile(p) for p in rule if not p.startswith("!")],
                         [_compile(p[1:]) for p in rule if p.startswith("!")]) for rule in _issue["rules"]]
    _issue["_none"] = [_compile(p) for p in _issue.get("none", [])] + ([_NotBoycott()] if _issue["id"] in BOYCOTT_SKIP else [])
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
    return [i["id"] for i in ISSUES if matches(i, head, body)]


def matches(issue, head, body=""):
    """Whether a bill is about the issue: a match in the title or summary, or enough in "What it does"."""
    if _hit(issue, head):
        return True
    # For issues with their own "body" (2026-11-17): the opening of "What it does" counts like the title and summary,
    # since it says what the bill does (Oregon's "Personal income taxation": "Modifies personal income tax brackets.
    # Decreases rates ..."); passing mentions in budget and omnibus bills come later in the text. Not for school meals
    # ("lead": False): school funding and early childhood bills name meals in their first sentence.
    if body and "body" in issue and issue.get("lead", True) and _hit(issue, lead(body)):
        return True
    need = body_need(issue, body)
    return bool(body and need and _hits(issue, body, need) >= need)


def lead(text, size=250):
    """The opening of a text: its first 250 characters, carried on to the end of that sentence if it ends within 150
    more."""
    if len(text) <= size:
        return text
    end = text.find(". ", size)
    return text[:end + 1] if 0 <= end <= size + 150 else text[:size]


def body_need(issue, body):
    """Mentions a "What it does" needs: one when it's short, else two, or the issue's own "body" (more for subjects that
    omnibus and budget bills name in passing again and again: homelessness, school meals). "body": 0 means "What it
    does" never counts alone (income tax cuts: tax bills describe the rates they leave alone). "short" is what a short
    "What it does" needs (two for school meals, whose one-line summaries name the lunch program in passing)."""
    if issue.get("body") == 0:
        return 0
    if len(body) < SHORT:
        return issue.get("short", 1)
    return issue.get("body", 2)


def snippet(issue_id, text):
    """The window that matched, for reading matches over."""
    return _hit(BY_ID[issue_id], text)


def filters_of(issue_id, text):
    return [k for k, ps in BY_ID[issue_id]["_filters"].items() if any(p.search(text) for p in ps)]


# A period that ends an abbreviation, not a sentence (2026-11-24: Texas's "S.B. 477 seeks to ..." was cut to "477 seeks to
# ...", and "Sec. 2", "No. 320", "R.S. 18:104", "c. 44" the same way).
_ABBR = re.compile(r"(?:\b(?:[A-Za-z]\.){2,}|\b(?:[Ss]ecs?|[Nn]os?|[Aa]rts?|[Cc]hs?|c|[Ss]tats?|[Ss]ubd|[Pp]ar|[Pp]ara|[Cc]l|Inc|Co|Corp|"
                   r"Jr|Sr|Mr|Mrs|Ms|Dr|St|Rev|Gen|Ann|Comp|[Vv]ol|vs|v|al|approx|Dept|Div|Regs?|Supp|pp|p|Minn|Fla|Tex|Ill|Mass|"
                   r"Wash|Mich|Wis|Tenn|Ala|Miss|Ariz|Colo|Conn|Okla)|\b[A-Z])\.$")


def _stop_before(text, i):
    """The last sentence end (". ") before i that isn't an abbreviation's period, or -1."""
    j = text.rfind(". ", 0, i)
    while j >= 0 and _ABBR.search(text[max(0, j - 12):j + 1]):
        j = text.rfind(". ", 0, j)
    return j


def _stop_after(text, i):
    """The first sentence end (". ") from i that isn't an abbreviation's period, or -1."""
    j = text.find(". ", i)
    while j >= 0 and _ABBR.search(text[max(0, j - 12):j + 1]):
        j = text.find(". ", j + 1)
    return j


# What an excerpt shouldn't start with: a bullet, stray punctuation (New York's memos: ": This bill would ..."), a dash,
# a list marker ("(2) ", "(iii) ", "4. ").
_LEAD_JUNK = re.compile(r"^(?:[\s•:;,.\-–—]+|\((?:\d{1,3}|[a-z]|[ivx]{1,5})\)\s+|\d{1,3}[.)]\s+)+")


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
                a = max(_stop_before(text, m.start()), text.rfind("; ", 0, m.start()), text.rfind("• ", 0, m.start()))
                b = min([x for x in (_stop_after(text, m.end()), text.find("; ", m.end()), text.find(" • ", m.end())) if x >= 0] or [len(text)])
                s = re.sub(r"\s+", " ", text[a + 2 if a >= 0 else 0:b]).strip()
                s = _LEAD_JUNK.sub("", s)
                s = re.sub(r"^(?:[Aa]mends?|[Cc]reates?|[Rr]epeals?)(?: (?:a )?new sections? of)? [A-Z]{2,5} (?:Chapter )?[\d.,A-Z\s-]+?(?:and [\d.]+ )?to ", "", s)
                if len(s) > limit:
                    s = s[:limit].rsplit(" ", 1)[0] + " …"
                return s[:1].upper() + s[1:]
    return ""
