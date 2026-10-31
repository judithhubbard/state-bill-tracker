"""Massachusetts: the settings and wording that are particular to this state.

build_data.py reads these as P.<name>, with the same names as states/ny/profile.py.
"""
import os, re

DATA = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "ma"))
SITE_DIR = "ma"

STATE_NAME = "Massachusetts"
SITE_NAME = "Massachusetts Bill Tracker"
LEGISLATURE = "Massachusetts General Court"
TIMEZONE = "America/New_York"
PUBLIC_URL = "https://statebilltracker.org/ma/"
SITE_URL = os.environ.get("SITE_URL", PUBLIC_URL)

# Each General Court sits two years from January of an odd year (the 194th, 2025-26); formal sessions end July 31 of
# the second year, informal ones run to its end. A committee's new draft of a bill gets a new number (merged here).
YEARS = 2
LOWER = "H"
LOWER_NAME = "House"
TITLES = {"S": "Sen.", "H": "Rep."}


def session_of(year):
    return year if year % 2 else year - 1


def court_of(session):
    """2025 -> 194."""
    return (session - 1637) // 2


def session_label(session):
    return f"{session}–{str(session + 1)[2:]}"


CF_ANALYTICS_TOKEN = ""
GOATCOUNTER_CODE = ""

DELEGATION_NAMES = set()
# Who decides which bills reach each house's floor: the Speaker and the Senate President (through each branch's Ways
# and Means and the House Steering, Policy and Scheduling Committee).
LEADERS = {"S": ("Karen E. Spilka", "Senate President", "her"),
           "H": ("Ronald Mariano", "Speaker of the House", "him")}


def delegation(session):
    return {}


# Topic: (label, committee name words, official subjects (none used), title words). Massachusetts's committees are
# mostly joint; topics come from their names and the titles.
NO_SUBJECTS = re.compile(r"(?!)")
TOPICS = {
    "env": ("Environment & energy", set(), NO_SUBJECTS, r"\b(environment\w*|climate|emission\w*|renewable|solar|wind|pollut\w*|water|energy|utilit\w*)\b"),
    "local": ("Local government", set(), NO_SUBJECTS, r"\b(municipal\w*|town of|city of|county|counties|local government|regional)\b"),
    "tax": ("Taxes", set(), NO_SUBJECTS, r"\b(tax\w*|revenue)\b"),
    "safety": ("Public safety & courts", set(), NO_SUBJECTS, r"\b(crim\w*|firearm\w*|police|court\w*|sentenc\w*|prison\w*|jail\w*|felony|misdemeanor|correction\w*)\b"),
    "human": ("Human services", set(), NO_SUBJECTS, r"\b(child care|foster|veteran\w*|senior\w*|elder\w*|disabilit\w*|homeless\w*)\b"),
    "health": ("Health & mental health", set(), NO_SUBJECTS, r"\b(health|medical|masshealth|hospital\w*|mental|pharmac\w*|nurs\w*|physician\w*)\b"),
    "edu": ("Education", set(), NO_SUBJECTS, r"\b(school\w*|student\w*|teacher\w*|education|college\w*|universit\w*)\b"),
    "transp": ("Transportation", set(), NO_SUBJECTS, r"\b(vehicle\w*|highway\w*|road\w*|traffic|transit|driver\w*|motor|mbta)\b"),
    "labor": ("Labor & public employees", set(), NO_SUBJECTS, r"\b(wage\w*|employ\w*|worker\w*|labor|pension\w*|retirement)\b"),
    "housing": ("Housing", set(), NO_SUBJECTS, r"\b(housing|landlord\w*|tenant\w*|rent|eviction\w*)\b"),
    "ag": ("Agriculture", set(), NO_SUBJECTS, r"\b(agricultur\w*|farm\w*|livestock|animal\w*)\b"),
    "gov": ("Elections & state government", set(), NO_SUBJECTS, r"\b(election\w*|voter\w*|ballot\w*|state agenc\w*|ethics|public records)\b"),
    "biz": ("Business & consumers", set(), NO_SUBJECTS, r"\b(consumer\w*|business\w*|insurance|bank\w*|licens\w*)\b"),
    # Proposals for legislative amendments to the Constitution (tagged by convert.py, not by words).
    "const": ("Constitutional amendments", set(), NO_SUBJECTS, ""),
}
# Committee name words -> topic (the committees are mostly joint and their names are long).
COMMITTEE_TOPICS = {"Environment": "env", "Energy": "env", "Municipalities": "local", "Revenue": "tax", "Judiciary": "safety",
                    "Public Safety": "safety", "Children, Families": "human", "Elder": "human", "Veterans": "human",
                    "Health": "health", "Mental Health": "health", "Education": "edu", "Higher Education": "edu",
                    "Transportation": "transp", "Labor": "labor", "Public Service": "labor", "Housing": "housing",
                    "Agriculture": "ag", "Election Laws": "gov", "State Administration": "gov", "Consumer Protection": "biz",
                    "Financial Services": "biz", "Economic Development": "biz"}
TOPIC_WORDS = {k: re.compile(v[3], re.I) for k, v in TOPICS.items() if v[3]}

COUNTIES = []
DISTRICTS_PATH = os.path.join(DATA, "district_counties.json")
TOWNS_PATH = os.path.join(DATA, "district_towns.json")
DISTRICT_NAMES_PATH = os.path.join(DATA, "district_names.json")

_NAMING = re.compile(r"\b(?:designat\w*|nam\w*)\b.*\b(?:bridge|interchange|highway|route|memorial|building|park)\b", re.I)
NARROW_KINDS = ["", "person", "org", "naming"]


def narrow_kind(title):
    return "naming" if _NAMING.search(title) else ""


# Governors and the day each took office (the first Thursday after the first Wednesday of January after the election).
GOVERNORS = [("Baker", "2015-01-08"), ("Healey", "2023-01-05")]
GOV_SINCE = GOVERNORS[-1][1]


def governor_on(day):
    who = GOVERNORS[0][0]
    for name, start in GOVERNORS:
        if day >= start:
            who = name
    return who


TRENDS = []
WORDING = []
