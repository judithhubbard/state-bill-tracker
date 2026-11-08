"""Oklahoma: the settings and wording that are particular to this state.

build_data.py reads these as P.<name>, with the same names as states/ny/profile.py.
"""
import os, re

DATA = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "ok"))
SITE_DIR = "ok"

STATE_NAME = "Oklahoma"
SITE_NAME = "Oklahoma Bill Tracker"
LEGISLATURE = "Oklahoma Legislature"
TIMEZONE = "America/Chicago"
PUBLIC_URL = "https://statebilltracker.org/ok/"
SITE_URL = os.environ.get("SITE_URL", PUBLIC_URL)

# Each Legislature runs two years from an odd year (the 60th is 2025-26). It meets each year from the first Monday in
# February until the last Friday in May at the latest (Oklahoma Constitution, Art. V, sec. 26); bills not finished in
# the first year carry over to the second, with the same numbers. LegiScan files each year as its own session, but the
# even year's holds the whole Legislature's bills (convert.py reads that one).
YEARS = 2
LOWER = "H"
LOWER_NAME = "House"
TITLES = {"S": "Sen.", "H": "Rep."}


def session_of(year):
    return year if year % 2 else year - 1


def legislature(session):
    """2025 -> 60."""
    return 60 + (session - 2025) // 2


def session_label(session):
    return f"{session}–{str(session + 1)[2:]}"


CF_ANALYTICS_TOKEN = ""
GOATCOUNTER_CODE = ""

DELEGATION_NAMES = set()
# Who decides which bills reach each house's floor: the Speaker of the House and the Senate's President Pro Tempore (the
# Lieutenant Governor presides over the Senate in name only), through their majority floor leaders. Both are for the
# 60th Legislature (2025-26); the 61st elects its own in January 2027: change them then.
LEADERS = {"S": ("Lonnie Paxton", "President Pro Tempore of the Senate", "him"),
           "H": ("Kyle Hilbert", "Speaker of the House", "him")}


def delegation(session):
    return {}


# Topic: (label, committees (unused; see COMMITTEE_TOPICS), official subjects (unused; see SUBJECT_TOPICS), title words).
NO_SUBJECTS = re.compile(r"(?!)")
TOPICS = {
    "env": ("Environment & energy", set(), NO_SUBJECTS, r"\b(environment\w*|climate|emission\w*|renewable|solar|wind energy|pollut\w*|energy|utilit\w*|electric\w*|solid waste|landfill\w*|biosolids?|oil and gas)\b"),
    "local": ("Local government", set(), NO_SUBJECTS, r"\b(municipal\w*|county|counties|cities and towns|local government\w*|annexation)\b"),
    "tax": ("Taxes", set(), NO_SUBJECTS, r"\b(tax\w*|revenue)\b"),
    "safety": ("Public safety & courts", set(), NO_SUBJECTS, r"\b(crim\w*|firearm\w*|handgun\w*|police|court\w*|sentenc\w*|prison\w*|jail\w*|felony|misdemeanor|correction\w*|expunge\w*|law enforcement)\b"),
    "human": ("Human services", set(), NO_SUBJECTS, r"\b(child care|foster|veteran\w*|senior\w*|elderly|disabilit\w*|homeless\w*|human services|poor persons)\b"),
    "health": ("Health & mental health", set(), NO_SUBJECTS, r"\b(health|medical|medicaid|hospital\w*|mental|pharmac\w*|nurs\w*|physician\w*|abortion)\b"),
    "edu": ("Education", set(), NO_SUBJECTS, r"\b(school\w*|student\w*|teacher\w*|education|college\w*|universit\w*|tuition)\b"),
    "transp": ("Transportation", set(), NO_SUBJECTS, r"\b(vehicle\w*|highway\w*|road\w*|traffic|transit|driver\w*|driving|motor|turnpike\w*|airport\w*)\b"),
    "labor": ("Labor & public employees", set(), NO_SUBJECTS, r"\b(wage\w*|employ\w*|worker\w*|labor|pension\w*|retirement)\b"),
    "housing": ("Housing", set(), NO_SUBJECTS, r"\b(housing|landlord\w*|tenant\w*|rent|eviction\w*|zoning)\b"),
    "ag": ("Agriculture & natural resources", set(), NO_SUBJECTS, r"\b(agricultur\w*|farm\w*|livestock|fish\w*|wildlife|hunting|forest\w*|water rights|animals?)\b"),
    "gov": ("Elections & state government", set(), NO_SUBJECTS, r"\b(election\w*|voter\w*|voting|ballot\w*|state agenc\w*|ethics|open records|open meeting|campaign\w*|state government)\b"),
    "biz": ("Business & consumers", set(), NO_SUBJECTS, r"\b(consumer\w*|business\w*|insurance|bank\w*|licens\w*|corporat\w*|economic development|alcohol\w*|beer|wine|gaming|professions and occupations)\b"),
    "const": ("Constitutional amendments", set(), NO_SUBJECTS, ""),
}
TOPIC_WORDS = {k: re.compile(v[3], re.I) for k, v in TOPICS.items() if v[3]}

# Committee names (as convert.py writes them) -> topic, for committees with one subject. Appropriations, Rules and the
# House's oversight committees over several subjects give none, except where the subject is plain.
COMMITTEE_TOPICS = {
    # House (2025-26: policy committees under oversight committees; 2023-24 names too)
    "Agriculture": "ag", "Wildlife": "ag", "Agriculture and Rural Development": "ag",
    "Energy and Natural Resources Oversight": "env", "Energy": "env", "Utilities": "env", "Energy and Natural Resources": "env",
    "Alcohol, Tobacco and Controlled Substances": "biz", "Banking, Financial Services and Pensions": "biz",
    "Business": "biz", "Business and Commerce": "biz", "Insurance": "biz", "Commerce and Economic Development Oversight": "biz",
    "Tourism": "biz",
    "Children, Youth and Family Services": "human", "Veterans and Military Affairs": "human", "Veteran and Military Affairs": "human",
    "Civil Judiciary": "safety", "Criminal Judiciary": "safety", "Judiciary and Public Safety Oversight": "safety",
    "Public Safety": "safety", "Judiciary - Civil": "safety", "Judiciary - Criminal": "safety",
    "Criminal Justice and Corrections": "safety",
    "Common Education": "edu", "Education Oversight": "edu", "Postsecondary Education": "edu",
    "Higher Education and Career Tech": "edu", "Education": "edu",
    "County and Municipal Government": "local", "Local and County Government": "local",
    "Elections and Ethics": "gov", "Government Oversight": "gov", "General Government": "gov", "State Powers": "gov",
    "Government Modernization and Technology": "gov", "Administrative Rules": "gov",
    "Public Health": "health", "Health and Human Services Oversight": "health", "Health Services and Long-Term Care": "health",
    "Health and Human Services": "health",
    "Transportation": "transp", "Aeronautics and Transportation": "transp",
    # Senate
    "Agriculture and Wildlife": "ag", "Business and Insurance": "biz", "Business and Commerce": "biz",
    "Economic Development, Workforce and Tourism": "biz", "Energy and Telecommunications": "env",
    "Retirement and Insurance": "labor", "Retirement and Government Resources": "labor",
    "Revenue and Taxation": "tax", "Finance": "tax", "Appropriations and Budget Finance - Revenue and Taxation Subcommittee": "tax",
    "Tourism and Wildlife": "ag", "Technology and Telecommunications": "biz",
}

# The first item of a bill's official title is its subject ("Schools; ...", "Revenue and taxation; ..."): subject ->
# topic, for the common ones.
_S = {
    "ag": "agriculture|game and fish|waters and water rights|water and water rights|animals|wildlife|fish and wildlife|"
          "mines and mining|public lands|commissioners of the land office|state parks|water|weights and measures",
    "biz": "professions and occupations|insurance|alcoholic beverages|corporation commission|economic development|tourism|"
           "amusements and sports|banks and trust companies|consumer protection|securities|corporations|"
           "uniform consumer credit code|consumer credit code|financial institutions|alcoholic beverage licenses|"
           "department of commerce|partnerships|commercial code|uniform commercial code|trusts and pools|"
           "pharmacy benefit managers|construction industries board|contracts|abstracting|technology|artificial intelligence|"
           "social media|cybersecurity|aerospace|mortgages",
    "edu": "schools|higher education|education|teachers|school employees|charter schools|students|"
           "oklahoma higher learning access program|school district boards of education|state board of education|"
           "public libraries|libraries|school funding|education employees|school curriculum|teacher certification|"
           "career and technology education|special education|state department of education|school security|"
           "boards of education|teacher compensation|strong readers act|school district elections",
    "env": "environment and natural resources|oil and gas|energy|utilities|public utilities|wind energy facilities|"
           "nuclear energy|biosolids|department of environmental quality|oklahoma water resources board",
    "gov": "state government|elections|sunset|initiative and referendum|oklahoma open meeting act|records|"
           "oklahoma open records act|open records|open meeting act|statutes and reports|state fiscal affairs|"
           "voter registration|conduct of elections|attorney general|office of management and enterprise services|"
           "vital records|administrative rules|administrative procedures act|absentee ballots|absentee voting|"
           "ethics commission|campaign finance|congressional and legislative districts|service oklahoma|"
           "oklahoma historical society|oklahoma historical societies and associations|state property|"
           "public buildings and public works|capitol improvement authority|oklahoma capitol improvement authority|"
           "emergency management|definitions and general provisions|officers|legal tender",
    "health": "public health and safety|medical marijuana|mental health|health care|medicaid|health insurance|"
              "public health|long-term care|practice of pharmacy|abortion|hospitals|state department of health|"
              "department of mental health and substance abuse services|health|state medicaid program|"
              "practice of nursing|marijuana|prescription drugs|substance abuse services|oklahoma health care authority|"
              "emergency medical services|practice of medicine|medicolegal investigations|community health workers",
    "human": "children|poor persons|child care|veterans|department of human services|oklahoma children's code|"
             "domestic violence|child custody|marriage|soldiers and sailors|guardian and ward|foster care|"
             "protection from domestic abuse act|marriage and family|oklahoma juvenile code|domestic abuse|"
             "discrimination|parental rights|public assistance programs|victim protective orders|militia|"
             "oklahoma national guard",
    "labor": "labor|retirement|workers' compensation|public retirement systems|oklahoma public employees retirement system|"
             "teachers' retirement system of oklahoma|teachers' retirement system|state employees|"
             "state employee compensation|workers compensation|firefighters|oklahoma police pension and retirement system|"
             "oklahoma firefighters pension and retirement system|oklahoma employees insurance and benefits act",
    "local": "cities and towns|counties and county officers|counties|county officers|municipalities|county commissioners|"
             "county sheriffs",
    "safety": "crimes and punishments|firearms|criminal procedure|civil procedure|prisons and reformatories|public safety|"
              "courts|torts|controlled dangerous substances|human trafficking|law enforcement|driving under the influence|"
              "probate procedure|oklahoma state bureau of investigation|crimes and punishment|governmental tort claims act|"
              "damages|criminal justice|department of corrections|nuisances|uniform controlled dangerous substances act|"
              "sex offenders|assault and battery|oklahoma self-defense act|law enforcement officers|pardon and parole board|"
              "criminal law|district attorneys|jurors|corrections|council on law enforcement education and training|"
              "court reporters|larceny|department of public safety|wills and succession|notaries public|liens|"
              "conveyances|cemeteries",
    "tax": "revenue and taxation|income tax|sales tax|income tax credit|ad valorem tax|sales tax exemption|"
           "sales and use tax|taxation|excise tax|oklahoma tax commission|oklahoma parental choice tax credit act|fees",
    "transp": "motor vehicles|transportation|driver licenses|railroads|turnpikes|oklahoma turnpike authority|"
              "aircraft and airports|memorial highways|memorial roads and bridges|memorial bridges|license plates|"
              "roads and bridges|roads, bridges and ferries|memorial highways and bridges|motor carriers|"
              "department of transportation|airports|common carriers",
    "housing": "landlord and tenant|housing|property|eminent domain",
}
SUBJECT_TOPICS = {s: t for t, names in _S.items() for s in names.split("|")}

COUNTIES = []
DISTRICTS_PATH = os.path.join(DATA, "district_counties.json")
TOWNS_PATH = os.path.join(DATA, "district_towns.json")

_NAMING = re.compile(r"\b(?:designat\w*|nam\w*)\b.*\b(?:bridge|interchange|highway|route|memorial|building|park|road)\b|"
                     r"^memorial (?:highways?|roads|bridges)|\bmemorial (?:highway|bridge|interchange)\b", re.I)
NARROW_KINDS = ["", "place", "person", "org", "naming"]


def narrow_kind(title):
    return "naming" if _NAMING.search(title) else ""


# Governors and the day each took office. Kevin Stitt is term-limited: the governor elected in November 2026 takes office
# January 11, 2027 (the second Monday of January); add them here (and in states/legislatures.json) then.
GOVERNORS = [("Fallin", "2011-01-10"), ("Stitt", "2019-01-14")]
GOV_SINCE = GOVERNORS[-1][1]


def governor_on(day):
    who = GOVERNORS[0][0]
    for name, start in GOVERNORS:
        if day >= start:
            who = name
    return who


TRENDS = []
WORDING = []
