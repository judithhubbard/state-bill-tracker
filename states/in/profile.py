"""Indiana: the settings and wording that are particular to this state.

build_data.py reads these as P.<name>, with the same names as states/ny/profile.py.
"""
import os, re

DATA = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "in"))
SITE_DIR = "in"

STATE_NAME = "Indiana"
SITE_NAME = "Indiana Bill Tracker"
LEGISLATURE = "Indiana General Assembly"
TIMEZONE = "America/Indiana/Indianapolis"
PUBLIC_URL = "https://statebilltracker.org/in/"
SITE_URL = os.environ.get("SITE_URL", PUBLIC_URL)

# A regular session a year: a long one in odd years (it must end by April 29, and writes the two-year budget) and a
# short one in even years (by March 14); bills die at its end (IC 2-2.1-1-2). Each General Assembly spans two years
# (the 124th is 2025-26), which matters only for constitutional amendments.
YEARS = 1
LOWER = "H"
LOWER_NAME = "House"
TITLES = {"S": "Sen.", "H": "Rep."}


def session_of(year):
    return year


def session_kind(session):
    """Sessions alternate: a long session in odd years (about four months, with the budget), a short one in even years
    (about two months). Statistics compare a session only with past sessions of the same kind."""
    return "long" if session % 2 else "short"


def session_label(session):
    return str(session)


CF_ANALYTICS_TOKEN = ""
GOATCOUNTER_CODE = ""

DELEGATION_NAMES = set()
# Who decides which bills reach each house's floor: the Speaker, and the Senate's President Pro Tempore (the Lieutenant
# Governor presides over the Senate but isn't a senator). Senate Republicans chose Chris Garten (August 2026) to follow
# Rodric Bray as President Pro Tempore once the Senate votes, after the November 2026 election: change it then.
LEADERS = {"S": ("Rodric Bray", "President Pro Tempore of the Senate", "them"),
           "H": ("Todd Huston", "Speaker of the House", "them")}
# Other leadership posts, shown on the members' cards (the API has none). Checked 2026-11-08.
POSITIONS = {("H", "Matt Lehman"): "Majority Floor Leader", ("S", "Chris Garten"): "Majority Floor Leader",
             ("H", "Philip GiaQuinta"): "Minority Leader", ("S", "Shelli Yoder"): "Minority Leader"}


def delegation(session):
    return {}


# Topic: (label, committees (unused), official subjects (unused; see SUBJECT_TOPICS), title words).
NO_SUBJECTS = re.compile(r"(?!)")
TOPICS = {
    "env": ("Environment & energy", set(), NO_SUBJECTS, r"\b(environment\w*|climate|emission\w*|renewable|solar|wind|pollut\w*|energy|utilit\w*|mining|coal|nuclear|carbon|electric\w*|PFAS)\b"),
    "local": ("Local government", set(), NO_SUBJECTS, r"\b(municipal\w*|county|counties|township\w*|annexation|local government)\b"),
    "tax": ("Taxes", set(), NO_SUBJECTS, r"\b(tax\w*|revenue)\b"),
    "safety": ("Public safety & courts", set(), NO_SUBJECTS, r"\b(crim\w*|firearm\w*|police|court\w*|sentenc\w*|prison\w*|jail\w*|felony|misdemeanor|correction\w*|expungement)\b"),
    "human": ("Human services", set(), NO_SUBJECTS, r"\b(child care|foster|veteran\w*|senior\w*|elderly|disabilit\w*|homeless\w*)\b"),
    "health": ("Health & mental health", set(), NO_SUBJECTS, r"\b(health|medical|medicaid|hospital\w*|mental|pharmac\w*|nurs\w*|physician\w*)\b"),
    "edu": ("Education", set(), NO_SUBJECTS, r"\b(school\w*|student\w*|teacher\w*|education|college\w*|universit\w*|tuition)\b"),
    "transp": ("Transportation", set(), NO_SUBJECTS, r"\b(vehicle\w*|highway\w*|road\w*|traffic|transit|driver\w*|driving|motor)\b"),
    "labor": ("Labor & public employees", set(), NO_SUBJECTS, r"\b(wage\w*|employ\w*|worker\w*|labor|pension\w*|retirement)\b"),
    "housing": ("Housing", set(), NO_SUBJECTS, r"\b(housing|landlord\w*|tenant\w*|rent|eviction\w*)\b"),
    "ag": ("Agriculture & natural resources", set(), NO_SUBJECTS, r"\b(agricultur\w*|farm\w*|livestock|fish\w*|wildlife|hunting|grain|water rights)\b"),
    "gov": ("Elections & state government", set(), NO_SUBJECTS, r"\b(election\w*|voter\w*|voting|ballot\w*|state agenc\w*|ethics|public records)\b"),
    "biz": ("Business & consumers", set(), NO_SUBJECTS, r"\b(consumer\w*|business\w*|insurance|bank\w*|licens\w*|corporat\w*|economic development|gaming|alcohol\w*)\b"),
    "const": ("Constitutional amendments", set(), NO_SUBJECTS, ""),
}
# Committee names (both houses') -> topic, for committees with one subject. Ways and Means, Appropriations, Rules and
# Public Policy (alcohol, gaming and more), and Veterans Affairs and Public Safety (two subjects) give none.
COMMITTEE_TOPICS = {
    "Agriculture and Rural Development": "ag", "Agriculture": "ag", "Natural Resources": "ag",
    "Commerce, Small Business and Economic Development": "biz", "Commerce and Technology": "biz",
    "Financial Institutions": "biz", "Insurance": "biz", "Insurance and Financial Institutions": "biz",
    "Courts and Criminal Code": "safety", "Corrections and Criminal Law": "safety", "Judiciary": "safety",
    "Education": "edu", "Education and Career Development": "edu",
    "Elections and Apportionment": "gov", "Elections": "gov", "Government and Regulatory Reform": "gov",
    "Employment, Labor and Pensions": "labor", "Pensions and Labor": "labor",
    "Environmental Affairs": "env", "Utilities, Energy and Telecommunications": "env", "Utilities": "env",
    "Family, Children and Human Affairs": "human", "Family and Children Services": "human",
    "Veterans Affairs and the Military": "human",
    "Local Government": "local",
    "Public Health": "health", "Health and Provider Services": "health",
    "Roads and Transportation": "transp", "Homeland Security and Transportation": "transp",
    "Tax and Fiscal Policy": "tax",
}
# The Legislative Services Agency's subject index ("HEALTH; Mental Health": the part before the semicolon) -> topic.
# AGENCIES, GENERAL ASSEMBLY, BOARDS, COMMISSIONS, AND COUNCILS and the like are on most bills and say nothing.
SUBJECT_TOPICS = {
    "HEALTH": "health", "HEALTH CARE PROFESSIONALS": "health", "HEALTH CARE FACILITIES": "health", "ADDICTION SERVICES": "health",
    "CRIMINAL LAW AND PROCEDURE": "safety", "COURTS": "safety", "LAW ENFORCEMENT": "safety", "CORRECTIONS": "safety",
    "FIREARMS AND WEAPONS": "safety", "PUBLIC DEFENDER": "safety", "CIVIL LAW AND PROCEDURE": "safety", "HOMELAND SECURITY": "safety",
    "SCHOOLS": "edu", "EDUCATION": "edu", "HIGHER EDUCATION": "edu", "LIBRARIES": "edu",
    "TAXES": "tax",
    "STATE GOVERNMENT": "gov", "STATE ELECTED OFFICIALS": "gov", "ELECTIONS": "gov", "ADMINISTRATIVE LAW": "gov",
    "PUBLIC RECORDS": "gov", "PUBLIC HEARINGS AND MEETINGS": "gov",
    "CHILDREN AND MINORS": "human", "SOCIAL SERVICES": "human", "SENIOR CITIZENS": "human", "VETERANS": "human",
    "MARRIAGE AND FAMILY LAW": "human",
    "ZONING AND PLANNING": "housing", "BUILDINGS AND BUILDING REGULATIONS": "housing",
    "REAL ESTATE APPRAISERS, BROKERS, AND SALESPERSONS": "housing",
    "TRANSPORTATION": "transp",
    "INSURANCE": "biz", "FINANCIAL SERVICES": "biz", "BUSINESS ORGANIZATIONS AND ASSOCIATIONS": "biz", "TECHNOLOGY": "biz",
    "TRADE REGULATIONS": "biz", "PROFESSIONAL AND OCCUPATIONAL LICENSING": "biz", "ECONOMIC DEVELOPMENT": "biz",
    "ALCOHOL AND TOBACCO": "biz", "GAMBLING, GAMING, AND WAGERING": "biz", "RETAIL MERCHANTS": "biz", "RESTAURANTS AND LODGING": "biz",
    "LOCAL GOVERNMENT": "local", "COUNTIES": "local", "COUNTY GOVERNMENT": "local", "LOCAL ELECTED OFFICIALS": "local",
    "CITIES AND TOWNS": "local", "CITIES": "local", "TOWNSHIPS AND TOWNSHIP OFFICERS": "local", "ANNEXATION OF TERRITORY": "local",
    "UTILITIES": "env", "ENVIRONMENT": "env", "ENERGY": "env",
    "LABOR AND EMPLOYMENT": "labor", "PENSIONS AND RETIREMENT BENEFITS": "labor",
    "NATURAL RESOURCES": "ag", "AGRICULTURE": "ag", "ANIMALS": "ag", "VETERINARIANS": "ag",
}
TOPIC_WORDS = {k: re.compile(v[3], re.I) for k, v in TOPICS.items() if v[3]}

COUNTIES = []
DISTRICTS_PATH = os.path.join(DATA, "district_counties.json")
TOWNS_PATH = os.path.join(DATA, "district_towns.json")

_NAMING = re.compile(r"\b(?:designat\w*|nam\w*)\b.*\b(?:bridge|interchange|highway|route|memorial|building|park)\b|\bmemorial (?:highway|bridge|interchange)\b", re.I)
NARROW_KINDS = ["", "person", "org", "naming"]


def narrow_kind(title):
    return "naming" if _NAMING.search(title) else ""


# Governors and the day each took office.
GOVERNORS = [("Pence", "2013-01-14"), ("Holcomb", "2017-01-09"), ("Braun", "2025-01-13")]
GOV_SINCE = GOVERNORS[-1][1]


def governor_on(day):
    who = GOVERNORS[0][0]
    for name, start in GOVERNORS:
        if day >= start:
            who = name
    return who


TRENDS = []
WORDING = []
