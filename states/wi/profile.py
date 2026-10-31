"""Wisconsin: the settings and wording that are particular to this state.

build_data.py reads these as P.<name>, with the same names as states/ny/profile.py.
"""
import os, re

DATA = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "wi"))
SITE_DIR = "wi"

STATE_NAME = "Wisconsin"
SITE_NAME = "Wisconsin Bill Tracker"
LEGISLATURE = "Wisconsin Legislature"
TIMEZONE = "America/Chicago"
PUBLIC_URL = "https://statebilltracker.org/wi/"
SITE_URL = os.environ.get("SITE_URL", PUBLIC_URL)

# Two-year sessions starting in January of odd years; the Legislature meets in floor periods set by joint resolution, the
# last for general business in the spring of the second year, when the bills still pending fail. The lower house is the
# Assembly. Special sessions aren't shown.
YEARS = 2
LOWER = "A"
LOWER_NAME = "Assembly"
TITLES = {"S": "Sen.", "A": "Rep."}


def session_of(year):
    return year if year % 2 else year - 1


def session_label(session):
    return f"{session}–{str(session + 1)[2:]}"



CF_ANALYTICS_TOKEN = ""
GOATCOUNTER_CODE = ""

DELEGATION_NAMES = set()
# Who decides which bills reach each house's floor: the Assembly Speaker, and the Senate Majority Leader (the Senate
# President presides).
LEADERS = {"S": ("Devin LeMahieu", "Senate Majority Leader", "him"),
           "A": ("Robin Vos", "Speaker of the Assembly", "him")}


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
    # Joint resolutions proposing constitutional amendments (tagged by convert.py, not by words).
    "const": ("Constitutional amendments", set(), NO_SUBJECTS, ""),
    "biz": ("Business & consumers", set(), NO_SUBJECTS, r"\b(consumer\w*|business\w*|insurance|bank\w*|licens\w*)\b"),
}
# Committee name words -> topic.
COMMITTEE_TOPICS = {"Environment": "env", "Energy": "env", "Natural Resources": "env", "Utilities": "env", "Local Government": "local",
                    "Ways and Means": "tax", "Revenue": "tax", "Finance": "tax", "Judiciary": "safety", "Criminal Justice": "safety",
                    "Corrections": "safety", "Public Safety": "safety", "Children": "human", "Families": "human", "Veterans": "human",
                    "Aging": "human", "Human Services": "human", "Health": "health", "Mental Health": "health", "Insurance": "biz",
                    "Education": "edu", "Colleges": "edu", "Universities": "edu", "Transportation": "transp", "Labor": "labor",
                    "Workforce": "labor", "Retirement": "labor", "Housing": "housing", "Agriculture": "ag", "Sporting Heritage": "ag",
                    "Forestry": "ag", "Campaigns and Elections": "gov", "Elections": "gov", "State Affairs": "gov", "Government Operations": "gov",
                    "Financial Institutions": "biz", "Consumer Protection": "biz", "Small Business": "biz", "Jobs": "biz", "Licensing": "biz"}
TOPIC_WORDS = {k: re.compile(v[3], re.I) for k, v in TOPICS.items() if v[3]}

COUNTIES = []
DISTRICTS_PATH = os.path.join(DATA, "district_counties.json")
TOWNS_PATH = os.path.join(DATA, "district_towns.json")

_NAMING = re.compile(r"\b(?:dedicat\w*|designat\w*|nam\w*)\b.*\b(?:bridge|interchange|highway|route|road|memorial|building|park)\b", re.I)
NARROW_KINDS = ["", "person", "org", "naming"]


def narrow_kind(title):
    return "naming" if _NAMING.search(title) else ""


# Governors and the day each took office (the first Monday of January after the election).
GOVERNORS = [("Walker", "2011-01-03"), ("Evers", "2019-01-07")]
GOV_SINCE = GOVERNORS[-1][1]


def governor_on(day):
    who = GOVERNORS[0][0]
    for name, start in GOVERNORS:
        if day >= start:
            who = name
    return who


TRENDS = []
WORDING = []
