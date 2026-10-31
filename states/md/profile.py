"""Maryland: the settings and wording that are particular to this state.

build_data.py reads these as P.<name>, with the same names as states/ny/profile.py.
"""
import os, re

DATA = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "md"))
SITE_DIR = "md"

STATE_NAME = "Maryland"
SITE_NAME = "Maryland Bill Tracker"
LEGISLATURE = "Maryland General Assembly"
TIMEZONE = "America/New_York"
PUBLIC_URL = "https://statebilltracker.org/md/"
SITE_URL = os.environ.get("SITE_URL", PUBLIC_URL)

# One 90-day session a year, from the second Wednesday of January to early April; bills die at its end. The lower
# house is the House of Delegates.
YEARS = 1
LOWER = "H"
LOWER_NAME = "House of Delegates"
TITLES = {"S": "Sen.", "H": "Del."}


def session_of(year):
    return year


def session_label(session):
    return str(session)


CF_ANALYTICS_TOKEN = ""
GOATCOUNTER_CODE = ""

DELEGATION_NAMES = set()
# Who decides which bills reach each house's floor: the Senate President and the Speaker.
LEADERS = {"S": ("Bill Ferguson", "President of the Senate", "him"),
           "H": ("Joseline A. Peña-Melnyk", "Speaker of the House", "her")}


def delegation(session):
    return {}


# Topic: (label, committees (unused), official subjects (unused; see SUBJECT_TOPICS), title words).
NO_SUBJECTS = re.compile(r"(?!)")
TOPICS = {
    "env": ("Environment & energy", set(), NO_SUBJECTS, r"\b(environment\w*|climate|emission\w*|renewable|solar|wind|pollut\w*|energy|utilit\w*)\b"),
    "local": ("Local government", set(), NO_SUBJECTS, r"\b(municipal\w*|county|counties|local government)\b"),
    "tax": ("Taxes", set(), NO_SUBJECTS, r"\b(tax\w*|revenue)\b"),
    "safety": ("Public safety & courts", set(), NO_SUBJECTS, r"\b(crim\w*|firearm\w*|police|court\w*|sentenc\w*|prison\w*|jail\w*|felony|misdemeanor|correction\w*)\b"),
    "human": ("Human services", set(), NO_SUBJECTS, r"\b(child care|foster|veteran\w*|senior\w*|elderly|disabilit\w*|homeless\w*)\b"),
    "health": ("Health & mental health", set(), NO_SUBJECTS, r"\b(health|medical|medicaid|hospital\w*|mental|pharmac\w*|nurs\w*|physician\w*)\b"),
    "edu": ("Education", set(), NO_SUBJECTS, r"\b(school\w*|student\w*|teacher\w*|education|college\w*|universit\w*)\b"),
    "transp": ("Transportation", set(), NO_SUBJECTS, r"\b(vehicle\w*|highway\w*|road\w*|traffic|transit|driver\w*|motor)\b"),
    "labor": ("Labor & public employees", set(), NO_SUBJECTS, r"\b(wage\w*|employ\w*|worker\w*|labor|pension\w*|retirement)\b"),
    "housing": ("Housing", set(), NO_SUBJECTS, r"\b(housing|landlord\w*|tenant\w*|rent|eviction\w*)\b"),
    "ag": ("Agriculture & natural resources", set(), NO_SUBJECTS, r"\b(agricultur\w*|farm\w*|livestock|fish\w*|wildlife|hunting|chesapeake)\b"),
    "gov": ("Elections & state government", set(), NO_SUBJECTS, r"\b(election\w*|voter\w*|ballot\w*|state agenc\w*|ethics|public records)\b"),
    "biz": ("Business & consumers", set(), NO_SUBJECTS, r"\b(consumer\w*|business\w*|insurance|bank\w*|licens\w*)\b"),
    "const": ("Constitutional amendments", set(), NO_SUBJECTS, ""),
}
# The bill list's broad subjects -> topics (by the subject's first words).
SUBJECT_TOPICS = {"Agriculture": "ag", "Hunting": "ag", "Natural Resources": "ag", "Environment": "env", "Energy": "env",
                  "Utility": "env", "Counties": "local", "Municipalities": "local", "Local Government": "local",
                  "Bi-County": "local", "Local Debt": "local", "Taxes": "tax", "Criminal": "safety", "Corrections": "safety",
                  "Courts": "safety", "Juvenile": "safety", "Public Safety": "safety", "Civil Actions": "safety",
                  "Children": "human", "Disabled": "human", "Elderly": "human", "Social Services": "human",
                  "Family Law": "human", "Health": "health", "Public Health": "health", "Prior Authorizations": "health",
                  "Education": "edu", "Primary and Secondary": "edu", "Higher Education": "edu", "Community Colleges": "edu",
                  "Transportation": "transp", "Vehicle Laws": "transp", "Private Sector Labor": "labor",
                  "Unemployment": "labor", "Workers' Compensation": "labor", "State Government - Pensions": "labor",
                  "State Government - Personnel": "labor", "Housing": "housing", "Real Property": "housing",
                  "Elections": "gov", "Ethics": "gov", "State Government": "gov", "Business": "biz", "Commercial Law": "biz",
                  "Financial Institutions": "biz", "Insurance": "biz", "Corporations": "biz", "Cannabis": "biz",
                  "Alcoholic Beverages": "biz", "Gaming": "biz", "Economic Development": "biz"}
TOPIC_WORDS = {k: re.compile(v[3], re.I) for k, v in TOPICS.items() if v[3]}

COUNTIES = []
DISTRICTS_PATH = os.path.join(DATA, "district_counties.json")
TOWNS_PATH = os.path.join(DATA, "district_towns.json")

_NAMING = re.compile(r"\b(?:designat\w*|nam\w*)\b.*\b(?:bridge|interchange|highway|route|memorial|building|park)\b", re.I)
NARROW_KINDS = ["", "person", "org", "naming"]


def narrow_kind(title):
    return "naming" if _NAMING.search(title) else ""


# Governors and the day each took office (the third Wednesday of January after the election).
GOVERNORS = [("Hogan", "2015-01-21"), ("Moore", "2023-01-18")]
GOV_SINCE = GOVERNORS[-1][1]


def governor_on(day):
    who = GOVERNORS[0][0]
    for name, start in GOVERNORS:
        if day >= start:
            who = name
    return who


TRENDS = []
WORDING = []
