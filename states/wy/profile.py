"""Wyoming: the settings and wording that are particular to this state.

build_data.py reads these as P.<name>, with the same names as states/ny/profile.py.
"""
import os, re

DATA = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "wy"))
SITE_DIR = "wy"

STATE_NAME = "Wyoming"
SITE_NAME = "Wyoming Bill Tracker"
LEGISLATURE = "Wyoming Legislature"
TIMEZONE = "America/Denver"
PUBLIC_URL = "https://statebilltracker.org/wy/"
SITE_URL = os.environ.get("SITE_URL", PUBLIC_URL)

# A session a year: a general session in odd years (about 40 days from January) and a budget session in even years
# (about 20 days from February, where a bill other than the budget needs two-thirds to be introduced); bills die at its
# end. Senate bills are "Senate Files" (SF).
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
# Who decides which bills reach each house's floor: the Senate President and the Speaker.
LEADERS = {"S": ("Bo Biteman", "President of the Senate", "him"),
           "H": ("Chip Neiman", "Speaker of the House", "him")}


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
# Committee name words -> topic, for committees with one subject (Wyoming's standing committees are numbered, "H09 -
# Minerals", and most cover several: 09 is Minerals, Business and Economic Development, 10 Labor, Health and Social
# Services, 02 Appropriations takes any bill that spends money; those are left to the title words).
COMMITTEE_TOPICS = {"Judiciary": "safety", "Revenue": "tax", "Education": "edu", "Agriculture": "ag", "Travel": "ag",
                    "Corporations": "gov", "Transportation": "transp"}
TOPIC_WORDS = {k: re.compile(v[3], re.I) for k, v in TOPICS.items() if v[3]}

COUNTIES = []
DISTRICTS_PATH = os.path.join(DATA, "district_counties.json")
TOWNS_PATH = os.path.join(DATA, "district_towns.json")

_NAMING = re.compile(r"\b(?:designat\w*|nam\w*)\b.*\b(?:bridge|interchange|highway|route|memorial|building|park)\b", re.I)
NARROW_KINDS = ["", "person", "org", "naming"]


def narrow_kind(title):
    return "naming" if _NAMING.search(title) else ""


# Governors and the day each took office (the first Monday of January after the election).
GOVERNORS = [("Mead", "2011-01-03"), ("Gordon", "2019-01-07")]
GOV_SINCE = GOVERNORS[-1][1]


def governor_on(day):
    who = GOVERNORS[0][0]
    for name, start in GOVERNORS:
        if day >= start:
            who = name
    return who


TRENDS = []
WORDING = []
