"""Pennsylvania: the settings and wording that are particular to this state.

build_data.py reads these as P.<name>, with the same names as states/ny/profile.py.
"""
import os, re

DATA = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "pa"))
SITE_DIR = "pa"

STATE_NAME = "Pennsylvania"
SITE_NAME = "Pennsylvania Bill Tracker"
LEGISLATURE = "Pennsylvania General Assembly"
TIMEZONE = "America/New_York"
PUBLIC_URL = "https://statebilltracker.org/pa/"
SITE_URL = os.environ.get("SITE_URL", PUBLIC_URL)

# Two-year sessions starting in January of odd years; the Legislature meets all year, and bills die when the session
# ends November 30 of the even year. Special sessions are separate and not shown.
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
# Lieutenant Governor presides but isn't a senator) with the Majority Leader.
LEADERS = {"S": ("Kim Ward", "President Pro Tempore of the Senate", "her"),
           "H": ("Joanna McClinton", "Speaker of the House", "her")}


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
# Committee name words -> topic (the history file names committees in capitals: "ENVIRONMENTAL & NATURAL RESOURCE
# PROTECTION").
COMMITTEE_TOPICS = {"ENVIRONMENTAL": "env", "ENERGY": "env", "LOCAL GOVERNMENT": "local", "URBAN AFFAIRS": "housing",
                    "FINANCE": "tax", "JUDICIARY": "safety", "LAW & JUSTICE": "safety", "VETERANS": "human",
                    "CHILDREN": "human", "AGING": "human", "HUMAN SERVICES": "human", "HEALTH": "health",
                    "EDUCATION": "edu", "TRANSPORTATION": "transp", "LABOR": "labor", "HOUSING": "housing",
                    "AGRICULTURE": "ag", "GAME": "ag", "STATE GOVERNMENT": "gov", "CONSUMER": "biz", "COMMERCE": "biz",
                    "BANKING": "biz", "INSURANCE": "biz", "PROFESSIONAL LICENSURE": "biz", "COMMUNITY": "local"}
TOPIC_WORDS = {k: re.compile(v[3], re.I) for k, v in TOPICS.items() if v[3]}

COUNTIES = []
DISTRICTS_PATH = os.path.join(DATA, "district_counties.json")
TOWNS_PATH = os.path.join(DATA, "district_towns.json")

_NAMING = re.compile(r"\b(?:designat\w*|nam\w*)\b.*\b(?:bridge|interchange|highway|route|memorial|building|park)\b", re.I)
NARROW_KINDS = ["", "person", "org", "naming"]


def narrow_kind(title):
    return "naming" if _NAMING.search(title) else ""


# Governors and the day each took office (the third Tuesday of January after the election).
GOVERNORS = [("Wolf", "2015-01-20"), ("Shapiro", "2023-01-17")]
GOV_SINCE = GOVERNORS[-1][1]


def governor_on(day):
    who = GOVERNORS[0][0]
    for name, start in GOVERNORS:
        if day >= start:
            who = name
    return who


TRENDS = []
WORDING = []
