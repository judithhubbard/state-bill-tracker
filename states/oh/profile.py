"""Ohio: the settings and wording that are particular to this state.

build_data.py reads these as P.<name>, with the same names as states/ny/profile.py.
"""
import os, re

DATA = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "oh"))
SITE_DIR = "oh"

STATE_NAME = "Ohio"
SITE_NAME = "Ohio Bill Tracker"
LEGISLATURE = "Ohio General Assembly"
TIMEZONE = "America/New_York"
PUBLIC_URL = "https://statebilltracker.org/oh/"
SITE_URL = os.environ.get("SITE_URL", PUBLIC_URL)

# Each General Assembly sits two years from January of an odd year (the 136th, 2025-26); bills stay alive until it
# ends and keep their numbers through both houses.
YEARS = 2
LOWER = "H"
LOWER_NAME = "House"
TITLES = {"S": "Sen.", "H": "Rep."}


def session_of(year):
    return year if year % 2 else year - 1


def assembly_of(session):
    """2025 -> 136."""
    return (session - 1753) // 2


def session_label(session):
    return f"{session}–{str(session + 1)[2:]}"


CF_ANALYTICS_TOKEN = ""
GOATCOUNTER_CODE = ""

DELEGATION_NAMES = set()
# Who decides which bills reach each house's floor: the Speaker and the Senate President, who chair each house's Rules
# and Reference Committee.
LEADERS = {"S": ("Rob McColley", "Senate President", "him"),
           "H": ("Matt Huffman", "Speaker of the House", "him")}


def delegation(session):
    return {}


# Topic: (label, committees, official subjects (none used), title words). Committees as the actions name them.
NO_SUBJECTS = re.compile(r"(?!)")
TOPICS = {
    "env": ("Environment & energy", {"Energy", "Energy and Natural Resources", "Natural Resources", "Agriculture and Natural Resources",
            "Energy and Public Utilities", "Public Utilities", "Environment"}, NO_SUBJECTS,
            r"\b(environment\w*|climate|emission\w*|renewable|solar|wind|pollut\w*|water|energy|utilit\w*|oil|gas)\b"),
    "local": ("Local government", {"Local Government", "Local Government and Elections"}, NO_SUBJECTS,
              r"\b(municipal\w*|county|counties|township\w*|local government|village\w*)\b"),
    "tax": ("Taxes", {"Ways and Means"}, NO_SUBJECTS, r"\b(tax\w*|revenue)\b"),
    "safety": ("Public safety & courts", {"Judiciary", "Criminal Justice", "Civil Justice", "Homeland Security", "Public Safety"}, NO_SUBJECTS,
               r"\b(crim\w*|firearm\w*|police|court\w*|sentenc\w*|prison\w*|jail\w*|felony|misdemeanor|corrections|offense\w*)\b"),
    "human": ("Human services", {"Families and Aging", "Children and Human Services", "Veterans Strategic Affairs", "Veterans and Public Safety"},
              NO_SUBJECTS, r"\b(child care|foster|veteran\w*|senior\w*|aging|disabilit\w*|homeless\w*)\b"),
    "health": ("Health & mental health", {"Health", "Medicaid", "Health Provider Services", "Insurance"}, NO_SUBJECTS,
               r"\b(health|medical|medicaid|hospital\w*|mental|pharmac\w*|nurs\w*|physician\w*)\b"),
    "edu": ("Education", {"Education", "Primary and Secondary Education", "Higher Education", "Workforce and Higher Education"}, NO_SUBJECTS,
            r"\b(school\w*|student\w*|teacher\w*|education|college\w*|universit\w*)\b"),
    "transp": ("Transportation", {"Transportation"}, NO_SUBJECTS, r"\b(vehicle\w*|highway\w*|road\w*|traffic|transit|driver\w*|motor)\b"),
    "labor": ("Labor & public employees", {"Workforce and Higher Education", "Commerce and Labor", "Pensions"}, NO_SUBJECTS,
              r"\b(wage\w*|employ\w*|worker\w*|labor|pension\w*)\b"),
    "housing": ("Housing", {"Housing"}, NO_SUBJECTS, r"\b(housing|landlord\w*|tenant\w*|rent|eviction\w*)\b"),
    "ag": ("Agriculture", {"Agriculture", "Agriculture and Natural Resources"}, NO_SUBJECTS, r"\b(agricultur\w*|farm\w*|livestock|animal\w*)\b"),
    "gov": ("Elections & state government", {"General Government", "Government Oversight", "Local Government and Elections", "State and Local Government"},
            NO_SUBJECTS, r"\b(election\w*|voter\w*|ballot\w*|state agenc\w*|ethics)\b"),
    "biz": ("Business & consumers", {"Commerce and Labor", "Financial Institutions", "Insurance", "Development", "Technology and Innovation",
            "Economic Development"}, NO_SUBJECTS, r"\b(consumer\w*|business\w*|insurance|bank\w*|licens\w*)\b"),
}
TOPIC_WORDS = {k: re.compile(v[3], re.I) for k, v in TOPICS.items() if v[3]}

COUNTIES = []
DISTRICTS_PATH = os.path.join(DATA, "district_counties.json")
TOWNS_PATH = os.path.join(DATA, "district_towns.json")

_NAMING = re.compile(r"\b(?:designat\w*|nam\w*)\b.*\b(?:bridge|interchange|highway|route|memorial|building|park)\b", re.I)
NARROW_KINDS = ["", "person", "org", "naming"]


def narrow_kind(title):
    return "naming" if _NAMING.search(title) else ""


# Governors and the day each took office (the second Monday of January after the election).
GOVERNORS = [("Kasich", "2011-01-10"), ("DeWine", "2019-01-14")]
GOV_SINCE = GOVERNORS[-1][1]


def governor_on(day):
    who = GOVERNORS[0][0]
    for name, start in GOVERNORS:
        if day >= start:
            who = name
    return who


TRENDS = []
WORDING = []
