"""North Carolina: the settings and wording that are particular to this state.

build_data.py reads these as P.<name>, with the same names as states/ny/profile.py.
"""
import os, re

DATA = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "nc"))
SITE_DIR = "nc"

STATE_NAME = "North Carolina"
SITE_NAME = "North Carolina Bill Tracker"
LEGISLATURE = "North Carolina General Assembly"
TIMEZONE = "America/New_York"
PUBLIC_URL = "https://statebilltracker.org/nc/"
SITE_URL = os.environ.get("SITE_URL", PUBLIC_URL)

# Two-year sessions: a long session from January of the odd year, a short session in the even year; bills stay alive
# through both (subject to crossover deadlines). Extra sessions are separate and not shown.
YEARS = 2
LOWER = "H"
LOWER_NAME = "House"
TITLES = {"S": "Sen.", "H": "Rep."}


def session_of(year):
    return year if year % 2 else year - 1


def session_label(session):
    return f"{session}–{str(session + 1)[2:]}"


CF_ANALYTICS_TOKEN = ""
GOATCOUNTER_CODE = ""

DELEGATION_NAMES = set()
# Who decides which bills reach each house's floor: the Speaker, and in the Senate the President Pro Tempore (the
# Lieutenant Governor presides but isn't a senator), through each house's Rules Committee.
LEADERS = {"S": ("Phil Berger", "President Pro Tempore of the Senate", "him"),
           "H": ("Destin Hall", "Speaker of the House", "him")}


def delegation(session):
    return {}


# Topic: (label, committees (unused; see COMMITTEE_TOPICS), official subjects (none used), title words).
NO_SUBJECTS = re.compile(r"(?!)")
TOPICS = {
    "env": ("Environment & energy", set(), NO_SUBJECTS, r"\b(environment\w*|climate|emission\w*|renewable|solar|wind|pollut\w*|water|energy|utilit\w*|oil and gas)\b"),
    "local": ("Local government", set(), NO_SUBJECTS, r"\b(municipal\w*|county|counties|borough\w*|township\w*|local government|city of)\b"),
    "tax": ("Taxes", set(), NO_SUBJECTS, r"\b(tax\w*|revenue)\b"),
    "safety": ("Public safety & courts", set(), NO_SUBJECTS, r"\b(crim\w*|firearm\w*|police|court\w*|sentenc\w*|prison\w*|jail\w*|felony|misdemeanor|correction\w*)\b"),
    "human": ("Human services", set(), NO_SUBJECTS, r"\b(child care|foster|veteran\w*|senior\w*|older adult\w*|aging|disabilit\w*|homeless\w*)\b"),
    "health": ("Health & mental health", set(), NO_SUBJECTS, r"\b(health|medical|medicaid|hospital\w*|mental|pharmac\w*|nurs\w*|physician\w*)\b"),
    "edu": ("Education", set(), NO_SUBJECTS, r"\b(school\w*|student\w*|teacher\w*|education|college\w*|universit\w*)\b"),
    "transp": ("Transportation", set(), NO_SUBJECTS, r"\b(vehicle\w*|highway\w*|road\w*|traffic|transit|driver\w*|motor)\b"),
    "labor": ("Labor & public employees", set(), NO_SUBJECTS, r"\b(wage\w*|employ\w*|worker\w*|labor|pension\w*|retirement)\b"),
    "housing": ("Housing", set(), NO_SUBJECTS, r"\b(housing|landlord\w*|tenant\w*|rent|eviction\w*)\b"),
    "ag": ("Agriculture & natural resources", set(), NO_SUBJECTS, r"\b(agricultur\w*|farm\w*|livestock|hunting|fish\w*|game|wildlife)\b"),
    "gov": ("Elections & state government", set(), NO_SUBJECTS, r"\b(election\w*|voter\w*|ballot\w*|state agenc\w*|ethics|public records)\b"),
    # Joint resolutions proposing constitutional amendments (tagged by convert.py, not by words).
    "const": ("Constitutional amendments", set(), NO_SUBJECTS, ""),
    "biz": ("Business & consumers", set(), NO_SUBJECTS, r"\b(consumer\w*|business\w*|insurance|bank\w*|licens\w*)\b"),
}
# Committee name words -> topic.
COMMITTEE_TOPICS = {"Environment": "env", "Energy": "env", "Local Government": "local", "State and Local": "local",
                    "Finance": "tax", "Judiciary": "safety", "Justice": "safety", "Homeland Security": "safety",
                    "Families": "human", "Aging": "human", "Health": "health", "Insurance": "biz", "Education": "edu",
                    "Universities": "edu", "Transportation": "transp", "Commerce": "biz", "Regulatory": "biz",
                    "Pensions": "labor", "Election": "gov", "State Government": "gov", "Agriculture": "ag",
                    "Wildlife": "ag", "Marine": "ag", "Housing": "housing", "Banking": "biz", "Alcoholic": "biz"}
TOPIC_WORDS = {k: re.compile(v[3], re.I) for k, v in TOPICS.items() if v[3]}

COUNTIES = []
DISTRICTS_PATH = os.path.join(DATA, "district_counties.json")
TOWNS_PATH = os.path.join(DATA, "district_towns.json")

_NAMING = re.compile(r"\b(?:designat\w*|nam\w*)\b.*\b(?:bridge|interchange|highway|route|memorial|building|park)\b", re.I)
NARROW_KINDS = ["", "person", "org", "naming"]


def narrow_kind(title):
    return "naming" if _NAMING.search(title) else ""


# Governors and the day each took office (January 1 after the election).
GOVERNORS = [("Cooper", "2017-01-01"), ("Stein", "2025-01-01")]
GOV_SINCE = GOVERNORS[-1][1]


def governor_on(day):
    who = GOVERNORS[0][0]
    for name, start in GOVERNORS:
        if day >= start:
            who = name
    return who


TRENDS = []
WORDING = []
