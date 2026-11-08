"""Maine: the settings and wording that are particular to this state.

build_data.py reads these as P.<name>, with the same names as states/ny/profile.py.
"""
import os, re

DATA = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "me"))
SITE_DIR = "me"

STATE_NAME = "Maine"
SITE_NAME = "Maine Bill Tracker"
LEGISLATURE = "Maine Legislature"
TIMEZONE = "America/New_York"
PUBLIC_URL = "https://statebilltracker.org/me/"
SITE_URL = os.environ.get("SITE_URL", PUBLIC_URL)

# A page is one two-year Legislature (the 132nd is 2025-26; decided 2026-11-08): LD numbers run through both years, bills
# carry over from the first session to the second, and LegiScan keeps a Legislature as one session. The first (long)
# session runs from December of the election year to June; the second (short) one from January to April. Each
# Legislature has one long and one short session, so pages compare like with like without a session_kind().
YEARS = 2
LOWER = "H"
LOWER_NAME = "House"
TITLES = {"S": "Sen.", "H": "Rep."}


def session_of(year):
    return year if year % 2 else year - 1


def legislature(session):
    """2025 -> 132."""
    return 132 + (session - 2025) // 2


def session_label(session):
    return f"{session}–{str(session + 1)[2:]}"


CF_ANALYTICS_TOKEN = ""
GOATCOUNTER_CODE = ""

DELEGATION_NAMES = set()
# Who decides which bills reach each house's floor: the President of the Senate and the Speaker of the House, each
# elected by their house when a Legislature convenes (the 133rd convenes in December 2026 and elects new ones: change
# these then).
LEADERS = {"S": ("Mattie Daughtry", "President of the Senate", "her"),
           "H": ("Ryan Fecteau", "Speaker of the House", "him")}


def delegation(session):
    return {}


# Topic: (label, committees (unused; see COMMITTEE_TOPICS), official subjects (unused), title words).
NO_SUBJECTS = re.compile(r"(?!)")
TOPICS = {
    "env": ("Environment & energy", set(), NO_SUBJECTS, r"\b(environment\w*|climate|emission\w*|renewable|solar|pollut\w*|energy|utilit\w*|electric\w*|solid waste|landfill\w*|PFAS)\b"),
    "local": ("Local government", set(), NO_SUBJECTS, r"\b(municipal\w*|county|counties|cities|city of|town of|towns|local government\w*|charter|water district|sewer district|unorganized territory|plantation)\b"),
    "tax": ("Taxes", set(), NO_SUBJECTS, r"\b(tax\w*|revenue)\b"),
    "safety": ("Public safety & courts", set(), NO_SUBJECTS, r"\b(crim\w*|firearm\w*|police|court\w*|sentenc\w*|prison\w*|jail\w*|felony|correction\w*|offense\w*|law enforcement)\b"),
    "human": ("Human services", set(), NO_SUBJECTS, r"\b(child care|foster|veteran\w*|senior\w*|elderly|disabilit\w*|homeless\w*|general assistance)\b"),
    "health": ("Health & mental health", set(), NO_SUBJECTS, r"\b(health|medical|mainecare|medicaid|hospital\w*|mental|pharmac\w*|nurs\w*|physician\w*)\b"),
    "edu": ("Education", set(), NO_SUBJECTS, r"\b(school\w*|student\w*|teacher\w*|education|college\w*|universit\w*|tuition)\b"),
    "transp": ("Transportation", set(), NO_SUBJECTS, r"\b(vehicle\w*|highway\w*|road\w*|traffic|transit|driver\w*|driving|motor|bridge\w*)\b"),
    "labor": ("Labor & public employees", set(), NO_SUBJECTS, r"\b(wage\w*|employ\w*|worker\w*|labor|pension\w*|retirement)\b"),
    "housing": ("Housing", set(), NO_SUBJECTS, r"\b(housing|landlord\w*|tenant\w*|rent|eviction\w*|zoning)\b"),
    "ag": ("Agriculture & natural resources", set(), NO_SUBJECTS, r"\b(agricultur\w*|farm\w*|livestock|fish\w*|wildlife|hunting|forest\w*|lobster\w*|marine resources)\b"),
    "gov": ("Elections & state government", set(), NO_SUBJECTS, r"\b(election\w*|voter\w*|voting|ballot\w*|state agenc\w*|ethics|freedom of access|campaign\w*)\b"),
    "biz": ("Business & consumers", set(), NO_SUBJECTS, r"\b(consumer\w*|business\w*|insurance|bank\w*|licens\w*|corporat\w*|economic development|alcohol\w*|liquor|cannabis|gaming|gambling)\b"),
    "const": ("Constitutional amendments", set(), NO_SUBJECTS, ""),
}
TOPIC_WORDS = {k: re.compile(v[3], re.I) for k, v in TOPICS.items() if v[3]}

# The joint standing committees (as convert.py writes their names) -> topic, for committees with one subject.
# Appropriations and Financial Affairs, Judiciary, and State and Local Government give none (many subjects), except
# where the subject is plain.
COMMITTEE_TOPICS = {
    "Agriculture, Conservation and Forestry": "ag", "Inland Fisheries and Wildlife": "ag", "Marine Resources": "ag",
    "Criminal Justice and Public Safety": "safety",
    "Education and Cultural Affairs": "edu",
    "Energy, Utilities and Technology": "env", "Environment and Natural Resources": "env",
    "Health and Human Services": "health", "Health Coverage, Insurance and Financial Services": "health",
    "Housing": "housing", "Housing and Economic Development": "housing",
    "Innovation, Development, Economic Advancement and Business": "biz",
    "Labor": "labor", "Labor and Housing": "labor",
    "Taxation": "tax", "Transportation": "transp",
    "Veterans and Legal Affairs": "gov",
}

COUNTIES = []
DISTRICTS_PATH = os.path.join(DATA, "district_counties.json")
TOWNS_PATH = os.path.join(DATA, "district_towns.json")

_NAMING = re.compile(r"\b(?:designat\w*|nam\w*|renam\w*)\b.*\b(?:bridge|interchange|highway|route|memorial|building|park|road)\b|\bmemorial (?:highway|bridge|interchange)\b", re.I)
_PLACE = re.compile(r"\b(?:charter of the (?:city|town)|(?:water|sewer|sanitary|school|utility|lighting|fire|village) (?:district|corporation)|"
                    r"\bthe (?:City|Town|Village|Plantation) of [A-Z]\w+|deorganiz\w*|\b[A-Z]\w+ Plantation\b)", re.I)
_PERSON = re.compile(r"\bAuthorizing [A-Z][\w.'-]*(?: [A-Z][\w.'-]*){0,3} to (?:Sue|Bring)\b|\bto Sue the State\b", re.I)
NARROW_KINDS = ["", "place", "person", "org", "naming"]


def narrow_kind(title):
    if _NAMING.search(title):
        return "naming"
    if _PERSON.search(title):
        return "person"
    if _PLACE.search(title):
        return "place"
    return ""


# Governors and the day each took office. Janet Mills is term-limited: the governor elected in November 2026 takes office
# in January 2027; add them here (and in states/legislatures.json) then.
GOVERNORS = [("LePage", "2011-01-05"), ("Mills", "2019-01-02")]
GOV_SINCE = GOVERNORS[-1][1]


def governor_on(day):
    who = GOVERNORS[0][0]
    for name, start in GOVERNORS:
        if day >= start:
            who = name
    return who


TRENDS = []
WORDING = []
