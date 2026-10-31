"""Michigan: the settings and wording that are particular to this state.

build_data.py reads these as P.<name>, with the same names as states/ny/profile.py.
"""
import os, re

DATA = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "mi"))
SITE_DIR = "mi"

STATE_NAME = "Michigan"
SITE_NAME = "Michigan Bill Tracker"
LEGISLATURE = "Michigan Legislature"
TIMEZONE = "America/Detroit"
PUBLIC_URL = "https://statebilltracker.org/mi/"
SITE_URL = os.environ.get("SITE_URL", PUBLIC_URL)

# Two-year Legislatures starting in odd years (the 103rd is 2025-26); a full-time Legislature that meets all year, and
# bills carry over from the first year to the second. Special sessions aren't shown.
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
# Who decides which bills reach each house's floor: the Speaker, and the Senate Majority Leader (the Lieutenant Governor
# presides but isn't a senator).
LEADERS = {"S": ("Winnie Brinks", "Senate Majority Leader", "her"),
           "H": ("Matt Hall", "Speaker of the House", "him")}


def delegation(session):
    return {}


# Topic: (label, committee names (unused; see COMMITTEE_TOPICS), official subjects (none), title words).
NO_SUBJECTS = re.compile(r"(?!)")
TOPICS = {
    "env": ("Environment & energy", set(), NO_SUBJECTS, r"\b(environment\w*|climate|emission\w*|renewable|solar|pollut\w*|water|energy|utilit\w*)\b"),
    "local": ("Local government", set(), NO_SUBJECTS, r"\b(municipal\w*|county|counties|city of|township\w*|local government)\b"),
    "tax": ("Taxes", set(), NO_SUBJECTS, r"\b(tax\w*|revenue|homestead exemption)\b"),
    "safety": ("Public safety & courts", set(), NO_SUBJECTS, r"\b(crim\w*|firearm\w*|police|court\w*|sentenc\w*|prison\w*|jail\w*|felony|misdemeanor|correction\w*|sheriff\w*)\b"),
    "human": ("Human services", set(), NO_SUBJECTS, r"\b(child care|foster|veteran\w*|senior\w*|aging|disabilit\w*|homeless\w*)\b"),
    "health": ("Health & mental health", set(), NO_SUBJECTS, r"\b(health|medical|medicaid|hospital\w*|mental|pharmac\w*|nurs\w*|physician\w*)\b"),
    "edu": ("Education", set(), NO_SUBJECTS, r"\b(school\w*|student\w*|teacher\w*|education|college\w*|universit\w*)\b"),
    "transp": ("Transportation", set(), NO_SUBJECTS, r"\b(vehicle\w*|highway\w*|road\w*|traffic|transit|driver\w*|motor)\b"),
    "labor": ("Labor & public employees", set(), NO_SUBJECTS, r"\b(wage\w*|employ\w*|worker\w*|labor|pension\w*|retirement)\b"),
    "housing": ("Housing", set(), NO_SUBJECTS, r"\b(housing|landlord\w*|tenant\w*|rent|eviction\w*)\b"),
    "ag": ("Agriculture & natural resources", set(), NO_SUBJECTS, r"\b(agricultur\w*|farm\w*|livestock|fish\w*|wildlife|hunting|timber)\b"),
    "gov": ("Elections & state government", set(), NO_SUBJECTS, r"\b(election\w*|voter\w*|ballot\w*|state agenc\w*|ethics|open records)\b"),
    "biz": ("Business & consumers", set(), NO_SUBJECTS, r"\b(consumer\w*|business\w*|insurance|bank\w*|licens\w*)\b"),
}
# Committee name words -> topic.
COMMITTEE_TOPICS = {"Natural Resources": "env", "Energy": "env", "Environment": "env", "Local Government": "local",
                    "Finance": "tax", "Tax": "tax", "Judiciary": "safety", "Public Safety": "safety", "Criminal": "safety",
                    "Civil Rights": "safety", "Families": "human", "Veterans": "human", "Housing and Human": "housing",
                    "Health": "health", "Insurance": "biz", "Education": "edu", "Transportation": "transp",
                    "Labor": "labor", "Workforce": "labor", "Agriculture": "ag", "Elections": "gov", "Election": "gov",
                    "Ethics": "gov", "Oversight": "gov", "Government Operations": "gov", "Regulatory": "biz",
                    "Economic": "biz", "Commerce": "biz", "Consumer": "biz"}
TOPIC_WORDS = {k: re.compile(v[3], re.I) for k, v in TOPICS.items() if v[3]}

COUNTIES = []
DISTRICTS_PATH = os.path.join(DATA, "district_counties.json")
TOWNS_PATH = os.path.join(DATA, "district_towns.json")

_NAMING = re.compile(r"\b(?:dedicat\w*|designat\w*|nam\w*)\b.*\b(?:bridge|interchange|highway|route|road|memorial|building|park)\b", re.I)
NARROW_KINDS = ["", "person", "org", "naming"]


def narrow_kind(title):
    return "naming" if _NAMING.search(title) else ""


# Governors and the day each took office (January 1 after the election).
GOVERNORS = [("Snyder", "2011-01-01"), ("Whitmer", "2019-01-01")]
GOV_SINCE = GOVERNORS[-1][1]


def governor_on(day):
    who = GOVERNORS[0][0]
    for name, start in GOVERNORS:
        if day >= start:
            who = name
    return who


TRENDS = []
WORDING = []
