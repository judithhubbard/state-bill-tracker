"""Minnesota: the settings and wording that are particular to this state.

build_data.py reads these as P.<name>, with the same names as states/ny/profile.py.
"""
import os, re

DATA = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "mn"))
SITE_DIR = "mn"

STATE_NAME = "Minnesota"
SITE_NAME = "Minnesota Bill Tracker"
LEGISLATURE = "Minnesota Legislature"
TIMEZONE = "America/Chicago"
PUBLIC_URL = "https://statebilltracker.org/mn/"
SITE_URL = os.environ.get("SITE_URL", PUBLIC_URL)

# Two-year Legislatures (the 94th is 2025-26), with a session each year: from January in odd years and February in even
# years, to the Monday after the third Saturday in May at the latest. Bill numbers run through both years and bills stay
# alive until the Legislature ends: one page per Legislature. Special sessions are left out (see convert.py).
YEARS = 2
LOWER = "H"
LOWER_NAME = "House"
TITLES = {"S": "Sen.", "H": "Rep."}


def session_of(year):
    return year if year % 2 else year - 1


def legislature(session):
    """2025 -> 94 (the 94th Legislature)."""
    return 94 + (session - 2025) // 2


def session_label(session):
    return f"{session}–{str(session + 1)[2:]}"


CF_ANALYTICS_TOKEN = ""
GOATCOUNTER_CODE = ""

DELEGATION_NAMES = set()
# The Speaker leads the House (in 2025-26, tied 67-67, under a power-sharing agreement: Speaker Lisa Demuth, a
# Republican, with every committee co-chaired by a Republican and a DFL member); the Senate's Majority Leader controls
# its floor (the President of the Senate, Bobby Joe Champion, presides). From the member lists, November 2026. The 95th
# Legislature elects its own in January 2027: change them then.
LEADERS = {"S": ("Erin Murphy", "Senate Majority Leader", "her"),
           "H": ("Lisa Demuth", "Speaker of the House", "her")}


def delegation(session):
    return {}


# Topic: (label, committees (unused; see COMMITTEE_TOPICS), official subjects (unused), title words).
NO_SUBJECTS = re.compile(r"(?!)")
TOPICS = {
    "env": ("Environment & energy", set(), NO_SUBJECTS, r"\b(environment\w*|climate|emission\w*|renewable|solar|wind energy|pollut\w*|energy|utilit\w*|electric\w*|carbon|recycl\w*|solid waste|wastewater|water quality|PFAS|clean water)\b"),
    "local": ("Local government", set(), NO_SUBJECTS, r"\b(municipal\w*|county|counties|cities|city of|town of|townships?|local government\w*|annexation|tax increment financing|local sales tax)\b"),
    "tax": ("Taxes", set(), NO_SUBJECTS, r"\b(tax\w*|revenue)\b"),
    "safety": ("Public safety & courts", set(), NO_SUBJECTS, r"\b(crim\w*|firearm\w*|guns?|police|peace officers?|court\w*|sentenc\w*|prison\w*|jail\w*|felony|misdemeanor|correction\w*|expunge\w*|offenses?|law enforcement|public safety)\b"),
    "human": ("Human services", set(), NO_SUBJECTS, r"\b(child care|foster|veteran\w*|seniors?|elderly|disabilit\w*|homeless\w*|human services|public assistance|MFIP|SNAP)\b"),
    "health": ("Health & mental health", set(), NO_SUBJECTS, r"\b(health|medical|medical assistance|MinnesotaCare|medicaid|hospital\w*|mental|pharmac\w*|nurs\w*|physician\w*|abortion|behavioral)\b"),
    "edu": ("Education", set(), NO_SUBJECTS, r"\b(schools?|students?|teachers?|education|college\w*|universit\w*|tuition|pupils?)\b"),
    "transp": ("Transportation", set(), NO_SUBJECTS, r"\b(vehicles?|highways?|roads?|traffic|transit|drivers?|driving|motor|trunk highway|railroad\w*|bridges?)\b"),
    "labor": ("Labor & public employees", set(), NO_SUBJECTS, r"\b(wages?|employ\w*|workers?|labor|pensions?|retirement|workforce|unemployment)\b"),
    "housing": ("Housing", set(), NO_SUBJECTS, r"\b(housing|landlords?|tenants?|rent\w*|eviction\w*|manufactured homes?|homeowners?|zoning)\b"),
    "ag": ("Agriculture & natural resources", set(), NO_SUBJECTS, r"\b(agricultur\w*|farm\w*|livestock|fish\w*|wildlife|hunting|game and fish|crops?|forest\w*|natural resources|mining|minerals?)\b"),
    "gov": ("Elections & state government", set(), NO_SUBJECTS, r"\b(elections?|voters?|voting|ballots?|state agenc\w*|ethics|data practices|campaign\w*|legislat\w*|state government)\b"),
    "biz": ("Business & consumers", set(), NO_SUBJECTS, r"\b(consumers?|business\w*|insurance|banks?|banking|licens\w*|corporat\w*|economic development|liquor|alcohol\w*|cannabis|gambling|commerce)\b"),
    # Bills proposing an amendment to the Minnesota Constitution (tagged by convert.py, not by words).
    "const": ("Constitutional amendments", set(), NO_SUBJECTS, ""),
}
TOPIC_WORDS = {k: re.compile(v[3], re.I) for k, v in TOPICS.items() if v[3]}

# Committee names (either house, 2023-26) -> topic, for committees with one subject. Ways and Means, Finance, Capital
# Investment, Rules, State and Local Government and the like take bills on any subject, so theirs come from the title.
COMMITTEE_TOPICS = {
    "Agriculture Finance and Policy": "ag", "Agriculture, Broadband, and Rural Development": "ag",
    "Agriculture, Veterans, Broadband, and Rural Development": "ag",
    "Children and Families Finance and Policy": "human", "Human Services Finance": "human",
    "Human Services Finance and Policy": "human", "Human Services Policy": "human", "Human Services": "human",
    "Climate and Energy Finance and Policy": "env", "Energy Finance and Policy": "env",
    "Energy, Utilities, Environment, and Climate": "env",
    "Environment and Natural Resources Finance and Policy": "env", "Environment, Climate, and Legacy": "env",
    "Sustainable Infrastructure Policy": "env",
    "Commerce Finance and Policy": "biz", "Commerce and Consumer Protection": "biz",
    "Economic Development Finance and Policy": "biz", "Jobs and Economic Development": "biz",
    "Education Finance": "edu", "Education Policy": "edu", "Higher Education Finance and Policy": "edu",
    "Higher Education": "edu",
    "Elections Finance and Government Operations": "gov", "Elections Finance and Policy": "gov", "Elections": "gov",
    "Health Finance and Policy": "health", "Health and Human Services": "health",
    "Housing Finance and Policy": "housing", "Housing and Homelessness Prevention": "housing",
    "Judiciary Finance and Civil Law": "safety", "Public Safety Finance and Policy": "safety",
    "Judiciary and Public Safety": "safety",
    "Labor and Industry Finance and Policy": "labor", "Workforce Development Finance and Policy": "labor",
    "Workforce, Labor, and Economic Development Finance and Policy": "labor", "Labor": "labor",
    "Property Tax Division": "tax", "Taxes": "tax",
    "Transportation Finance and Policy": "transp", "Transportation": "transp",
    "Veterans and Military Affairs Division": "human", "Veterans and Military Affairs Finance and Policy": "human",
    "Legacy Finance": "env",
}

COUNTIES = []
DISTRICTS_PATH = os.path.join(DATA, "district_counties.json")
TOWNS_PATH = os.path.join(DATA, "district_towns.json")
# The House's districts are each Senate district's halves, 1A to 67B; seat numbers count them 1 to 134 ("H:23" is 12A),
# and this file gives the page their names ({"H": {"23": "12A", ...}}). Written by towns.py.
DISTRICT_NAMES_PATH = os.path.join(DATA, "district_names.json")


def house_seat(district):
    """"12A" / "012A" -> 23; "12B" -> 24."""
    m = re.fullmatch(r"0*(\d+)([AB])", (district or "").strip().upper())
    return 2 * int(m.group(1)) - 1 + (m.group(2) == "B") if m else None


def house_district(seat):
    """23 -> "12A"."""
    return f"{(seat + 1) // 2}{'A' if seat % 2 else 'B'}"


_NAMING = re.compile(r"\b(?:designat\w*|nam\w*)\b.*\b(?:bridge|highway|route|memorial|building|interchange|road)\b|\bmemorial (?:highway|bridge)\b", re.I)
NARROW_KINDS = ["", "place", "person", "org", "naming"]


def narrow_kind(title):
    return "naming" if _NAMING.search(title) else ""


# Governors and the day each took office (the first Monday in January after the election).
GOVERNORS = [("Dayton", "2011-01-03"), ("Walz", "2019-01-07")]
GOV_SINCE = GOVERNORS[-1][1]


def governor_on(day):
    who = GOVERNORS[0][0]
    for name, start in GOVERNORS:
        if day >= start:
            who = name
    return who


TRENDS = []
WORDING = []
