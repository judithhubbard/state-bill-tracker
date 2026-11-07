"""Colorado: the settings and wording that are particular to this state.

build_data.py reads these as P.<name>, with the same names as states/ny/profile.py.
"""
import os, re

DATA = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "co"))
SITE_DIR = "co"

STATE_NAME = "Colorado"
SITE_NAME = "Colorado Bill Tracker"
LEGISLATURE = "Colorado General Assembly"
TIMEZONE = "America/Denver"
PUBLIC_URL = "https://statebilltracker.org/co/"
SITE_URL = os.environ.get("SITE_URL", PUBLIC_URL)

# A 120-day regular session a year from the second Wednesday of January; bills die at its end.
YEARS = 1
LOWER = "H"
LOWER_NAME = "House"
TITLES = {"S": "Sen.", "H": "Rep."}


def session_of(year):
    return year


def session_label(session):
    return str(session)


CF_ANALYTICS_TOKEN = ""
GOATCOUNTER_CODE = ""

DELEGATION_NAMES = set()
# Who decides which bills reach each house's floor: the Speaker and the President of the Senate.
LEADERS = {"S": ("James Coleman", "President of the Senate", "them"),
           "H": ("Julie McCluskie", "Speaker of the House", "them")}


def delegation(session):
    return {}


# Topic: (label, committees (unused), official subjects (unused; see SUBJECT_TOPICS), title words).
NO_SUBJECTS = re.compile(r"(?!)")
TOPICS = {
    "env": ("Environment & energy", set(), NO_SUBJECTS, r"\b(environment\w*|climate|emission\w*|renewable|solar|wind|pollut\w*|energy|utilit\w*|mineral\w*|mining|oil|gas|coal|uranium|nuclear|carbon|electric\w*)\b"),
    "local": ("Local government", set(), NO_SUBJECTS, r"\b(municipal\w*|county|counties|local government)\b"),
    "tax": ("Taxes", set(), NO_SUBJECTS, r"\b(tax\w*|revenue)\b"),
    "safety": ("Public safety & courts", set(), NO_SUBJECTS, r"\b(crim\w*|firearm\w*|police|court\w*|sentenc\w*|prison\w*|jail\w*|felony|misdemeanor|correction\w*)\b"),
    "human": ("Human services", set(), NO_SUBJECTS, r"\b(child care|foster|veteran\w*|senior\w*|elderly|disabilit\w*|homeless\w*)\b"),
    "health": ("Health & mental health", set(), NO_SUBJECTS, r"\b(health|medical|medicaid|hospital\w*|mental|pharmac\w*|nurs\w*|physician\w*)\b"),
    "edu": ("Education", set(), NO_SUBJECTS, r"\b(school\w*|student\w*|teacher\w*|education|college\w*|universit\w*)\b"),
    "transp": ("Transportation", set(), NO_SUBJECTS, r"\b(vehicle\w*|highway\w*|road\w*|traffic|transit|driver\w*|motor)\b"),
    "labor": ("Labor & public employees", set(), NO_SUBJECTS, r"\b(wage\w*|employ\w*|worker\w*|labor|pension\w*|retirement)\b"),
    "housing": ("Housing", set(), NO_SUBJECTS, r"\b(housing|landlord\w*|tenant\w*|rent|eviction\w*)\b"),
    "ag": ("Agriculture & natural resources", set(), NO_SUBJECTS, r"\b(agricultur\w*|farm\w*|livestock|fish\w*|wildlife|hunting|ranch\w*|grazing|water rights)\b"),
    "gov": ("Elections & state government", set(), NO_SUBJECTS, r"\b(election\w*|voter\w*|ballot\w*|state agenc\w*|ethics|public records)\b"),
    "biz": ("Business & consumers", set(), NO_SUBJECTS, r"\b(consumer\w*|business\w*|insurance|bank\w*|licens\w*|corporat\w*|trademark\w*|economic development|currenc\w*)\b"),
    "const": ("Constitutional amendments", set(), NO_SUBJECTS, ""),
}
# Committee name words -> topic (committees with one subject).
COMMITTEE_TOPICS = {"Judiciary": "safety", "Finance": "tax", "Education": "edu", "Agriculture": "ag",
                    "Health & Human Services": "health", "Energy & Environment": "env", "Transportation": "transp",
                    "Local Government": "local", "Business": "biz", "State, ": "gov"}
# The General Assembly's subjects -> topic.
SUBJECT_TOPICS = {
    "State Government": "gov", "Elections & Redistricting": "gov", "General Assembly": "gov",
    "Health Care & Health Insurance": "health", "Public Health": "health",
    "Crimes, Corrections, & Enforcement": "safety", "Courts & Judicial": "safety",
    "Education & School Finance (Pre & K-12)": "edu", "Higher Education": "edu",
    "Fiscal Policy & Taxes": "tax", "State Revenue & Budget": "tax",
    "Local Government": "local", "Transportation & Motor Vehicles": "transp",
    "Business & Economic Development": "biz", "Professions & Occupations": "biz", "Insurance": "biz",
    "Financial Services & Commerce": "biz", "Telecommunications & Information Technology": "biz",
    "Liquor, Tobacco, & Marijuana": "biz", "Gaming, Lottery, & Racing": "biz",
    "Natural Resources & Environment": "env", "Energy": "env", "Water": "ag", "Agriculture": "ag",
    "Housing": "housing", "Labor & Employment": "labor",
    "Children & Domestic Matters": "human", "Human Services": "human", "Military & Veterans": "human",
}
TOPIC_WORDS = {k: re.compile(v[3], re.I) for k, v in TOPICS.items() if v[3]}

COUNTIES = []
DISTRICTS_PATH = os.path.join(DATA, "district_counties.json")
TOWNS_PATH = os.path.join(DATA, "district_towns.json")

_NAMING = re.compile(r"\b(?:designat\w*|nam\w*)\b.*\b(?:bridge|interchange|highway|route|memorial|building|park)\b", re.I)
NARROW_KINDS = ["", "person", "org", "naming"]


def narrow_kind(title):
    return "naming" if _NAMING.search(title) else ""


# Governors and the day each took office (the second Tuesday of January after the election).
GOVERNORS = [("Hickenlooper", "2011-01-11"), ("Polis", "2019-01-08")]
GOV_SINCE = GOVERNORS[-1][1]


def governor_on(day):
    who = GOVERNORS[0][0]
    for name, start in GOVERNORS:
        if day >= start:
            who = name
    return who


TRENDS = []
WORDING = []
