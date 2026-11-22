"""Texas: the settings and wording that are particular to this state.

build_data.py reads these as P.<name>, with the same names as states/ny/profile.py.
"""
import os, re

DATA = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "tx"))
SITE_DIR = "tx"

STATE_NAME = "Texas"
SITE_NAME = "Texas Bill Tracker"
LEGISLATURE = "Texas Legislature"
TIMEZONE = "America/Chicago"
PUBLIC_URL = "https://statebilltracker.org/tx/"
SITE_URL = os.environ.get("SITE_URL", PUBLIC_URL)

# The Legislature meets in regular session once every two years, for 140 days from the second Tuesday of January
# of odd years (the 89th Legislature, "89R", in 2025). Bills can be filed from the Monday after the November
# election before it. Each house numbers its own bills (HB, SB); companions are listed in each bill's history.
YEARS = 2
LOWER = "H"
LOWER_NAME = "House"
TITLES = {"S": "Sen.", "H": "Rep."}


def session_of(year):
    return year if year % 2 else year - 1


def code_of(session):
    """2025 -> "89R"."""
    return f"{(session - 1847) // 2}R"


def session_label(session):
    return str(session)


CF_ANALYTICS_TOKEN = ""
GOATCOUNTER_CODE = ""

DELEGATION_NAMES = set()
# Who decides which bills reach each house's floor. In the House, the Speaker (and the Calendars Committee); in the
# Senate, the Lieutenant Governor presides and decides which bills come up.
LEADERS = {"S": ("Dan Patrick", "Lieutenant Governor", "him"),
           "H": ("Dustin Burrows", "Speaker of the House", "him")}
# Leaders already chosen for the next legislature, each in place from the day they take the post (governors.py's
# apply_leaders()); pronouns only where their own official biography gives them, else "them". Checked 2026-11-19.
LEADERS_NEXT = {
    "S": ("Vikki Goodwin", "Lieutenant Governor", "them", "2027-01-19"),
}


def delegation(session):
    return {}


# Topic: (label, committees, official subjects, title words). Texas's histories have official subjects
# ("Environment--Air (I0112)"); they're matched on the start of their names.
TOPICS = {
    "env": ("Environment and energy", set(), re.compile(r"^(Environment|Energy|Electric Utilities|Water|Oil & Gas|Pollution|Natural Resources|Wildlife)", re.I),
            r"\b(climate|emission\w*|renewable|solar|wind|pollut\w*|water|drought|oil|gas|energy|grid)\b"),
    "local": ("Local government", set(), re.compile(r"^(City Government|County Government|Special Districts|Political Subdivisions)", re.I),
              r"\b(municipalit\w*|county|counties|special district\w*|political subdivision\w*)\b"),
    "tax": ("Taxes", set(), re.compile(r"^(Taxation|Property Tax|Sales Tax|Franchise Tax|Fees & Other Nontax Revenue)", re.I),
            r"\b(tax|taxes|taxation|appraisal)\b"),
    "safety": ("Public safety and courts", set(), re.compile(r"^(Crimes|Criminal Procedure|Courts|Law Enforcement|Corrections|Weapons|Juvenile)", re.I),
               r"\b(offense\w*|crim\w*|firearm\w*|peace officer\w*|court\w*|sentenc\w*|prison\w*|jail\w*|felony|misdemeanor)\b"),
    "human": ("Social services", set(), re.compile(r"^(Human Services|Family|Children|Aging|Veterans|Disabilities|Child Protective)", re.I),
              r"\b(child care|foster care|veterans?|aging|disabilit\w*|homeless\w*)\b"),
    "health": ("Health", set(), re.compile(r"^(Health|Mental Health|Medicaid|Hospitals|Insurance--Health)", re.I),
               r"\b(health|medical|medicaid|hospital\w*|mental|pharmac\w*|nurs\w*|physician\w*)\b"),
    "edu": ("Education", set(), re.compile(r"^(Education)", re.I), r"\b(school\w*|student\w*|teacher\w*|education|college\w*|universit\w*)\b"),
    "transp": ("Transportation", set(), re.compile(r"^(Transportation|Motor Vehicles|Highways|Traffic)", re.I),
               r"\b(vehicle\w*|highway\w*|road\w*|traffic|transit|driver\w*|toll\w*)\b"),
    "labor": ("Jobs and workers", set(), re.compile(r"^(Labor|Employment|State Employees|Retirement Systems)", re.I),
              r"\b(wage\w*|employ\w*|worker\w*|labor|retirement)\b"),
    "housing": ("Housing", set(), re.compile(r"^(Housing|Landlord)", re.I), r"\b(housing|landlord\w*|tenant\w*|rent|eviction\w*)\b"),
    "ag": ("Agriculture and natural resources", set(), re.compile(r"^(Agriculture|Animals)", re.I), r"\b(agricultur\w*|farm\w*|livestock|animal\w*)\b"),
    "gov": ("Elections and government", set(), re.compile(r"^(Elections|State Agencies|Legislature|Governor|Open Government)", re.I),
            r"\b(election\w*|voter\w*|ballot\w*|state agenc\w*)\b"),
    "biz": ("Business and consumers", set(), re.compile(r"^(Business|Consumer Protection|Insurance|Financial|Occupational Regulation|Commerce)", re.I),
            r"\b(consumer\w*|business\w*|insurance|bank\w*|licens\w*)\b"),
    # Joint resolutions proposing constitutional amendments (tagged by convert.py, not by subjects or words).
    "const": ("Constitutional amendments", set(), re.compile(r"(?!)"), ""),
}
TOPIC_WORDS = {k: re.compile(v[3], re.I) for k, v in TOPICS.items() if v[3]}

COUNTIES = []
DISTRICTS_PATH = os.path.join(DATA, "district_counties.json")
TOWNS_PATH = os.path.join(DATA, "district_towns.json")

_NAMING = re.compile(r"\b(?:designat\w*|nam\w*)\b.*\b(?:bridge|interchange|highway|route|memorial|building|park)\b", re.I)
NARROW_KINDS = ["", "person", "org", "naming"]


def narrow_kind(title):
    return "naming" if _NAMING.search(title) else ""


# Governors and the day each took office (the third Tuesday of January after the election; next: January 2027,
# after the November 2026 election).
GOVERNORS = [("Perry", "2000-12-21"), ("Abbott", "2015-01-20"), ("Hinojosa", "2027-01-19")]  # governor-elect: in office from that day (governors.py)
GOV_SINCE = GOVERNORS[-1][1]


def governor_on(day):
    who = GOVERNORS[0][0]
    for name, start in GOVERNORS:
        if day >= start:
            who = name
    return who


# ---- What's changing: subjects whose share of bills changed most over the 2021, 2023 and 2025 sessions, picked by hand
# from an automatic phrase scan and checked against samples of the bills matched (notes/trends.md). Texas's records have
# captions only (no summaries), so these match the caption.
TRENDS = [
    ("rise", "Artificial intelligence", r"(?i:artificial intelligence|deep ?fake|\bgenerative|chatbot|algorithmic|machine learning)|\bAI\b", False),
    ("rise", "Diversity, equity and inclusion", r"diversity, equity|diversity and equity|diversity equity|\bDEI\b", True),
    ("rise", "Foreign adversaries", r"foreign (?:entit|adversar|governments?)|designated countr|countr(?:y|ies) of concern", True),
    ("rise", "Squatters", r"squatt|unlawful occupant|unauthorized occupant", True),
    ("rise", "Nuclear power", r"nuclear", True),
    ("rise", "School library books", r"library material|school librar|library catalog|librar(?:y|ies) .{0,30}(?:explicit|harmful|obscene)", True),
    ("rise", "Education savings accounts", r"education savings|scholarship account|education freedom", True),
    ("spike", "Fentanyl", r"fentanyl", True),
    ("spike", "COVID-19", r"covid|coronavirus|pandemic", True),
    ("spike", "Power grid", r"ercot|power region|electric grid|weatheriz|winter storm|power outage", True),
    ("spike", "Disaster declarations", r"declared (?:state of )?disaster|disaster declaration|declaration of (?:a )?(?:state of )?disaster", True),
    ("spike", "Cannabis", r"cannabis|marihuana|marijuana", True),
    ("spike", "Insulin", r"insulin", True),
]
WORDING = []
