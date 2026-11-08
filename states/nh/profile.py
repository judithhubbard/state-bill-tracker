"""New Hampshire: the settings and wording that are particular to this state.

build_data.py reads these as P.<name>, with the same names as states/ny/profile.py.
"""
import os, re

DATA = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "nh"))
SITE_DIR = "nh"

STATE_NAME = "New Hampshire"
SITE_NAME = "New Hampshire Bill Tracker"
LEGISLATURE = "New Hampshire General Court"
TIMEZONE = "America/New_York"
PUBLIC_URL = "https://statebilltracker.org/nh/"
SITE_URL = os.environ.get("SITE_URL", PUBLIC_URL)

# Each General Court spans two years (2025-26) and meets in a session each year, January to June. A page is one year's
# session (decided 2026-11-08): each year has its own deadlines, laws ("Chapter 74, Laws of 2025") and governor's
# actions, and the General Court's own files are split by session year. A bill that doesn't pass dies with its year,
# except bills a committee keeps over to the second year ("Retained in Committee" in the House, "Rereferred to
# Committee" in the Senate): those appear on both years' pages under the same number, as Virginia's continued bills do.
YEARS = 1
LOWER = "H"
LOWER_NAME = "House"
TITLES = {"S": "Sen.", "H": "Rep."}


def session_of(year):
    return year


def session_label(session):
    return str(session)


def first_year(year):
    """The General Court a session year belongs to, by its first year (2025 and 2026 -> 2025): its data folder."""
    return year if year % 2 else year - 1


CF_ANALYTICS_TOKEN = ""
GOATCOUNTER_CODE = ""

DELEGATION_NAMES = set()
# Who decides which bills reach each house's floor: the Speaker and the Senate President. Checked 2026-11-08; a new
# General Court chooses them in December 2026.
LEADERS = {"S": ("Sharon Carson", "President of the Senate", "her"),
           "H": ("Sherman Packard", "Speaker of the House", "him")}
# Other leadership posts, shown on the members' cards (the data has none). Checked 2026-11-08.
POSITIONS = {("H", "Jason Osborne"): "Majority Leader", ("S", "Regina Birdsell"): "Majority Leader",
             ("H", "Alexis Simpson"): "Democratic Leader", ("S", "Rebecca Perkins Kwoka"): "Democratic Leader"}


def delegation(session):
    return {}


# Topic: (label, committees (unused), official subjects (unused; see SUBJECT_TOPICS), title words).
NO_SUBJECTS = re.compile(r"(?!)")
TOPICS = {
    "env": ("Environment & energy", set(), NO_SUBJECTS, r"\b(environment\w*|climate|emission\w*|renewable|solar|wind|pollut\w*|energy|utilit\w*|nuclear|carbon|electric\w*|PFAS|landfill\w*|solid waste)\b"),
    "local": ("Local government", set(), NO_SUBJECTS, r"\b(municipal\w*|county|counties|town meeting\w*|selectmen|local government)\b"),
    "tax": ("Taxes", set(), NO_SUBJECTS, r"\b(tax\w*|revenue)\b"),
    "safety": ("Public safety & courts", set(), NO_SUBJECTS, r"\b(crim\w*|firearm\w*|police|court\w*|sentenc\w*|prison\w*|jail\w*|felony|misdemeanor|correction\w*|annulment)\b"),
    "human": ("Human services", set(), NO_SUBJECTS, r"\b(child care|foster|veteran\w*|senior\w*|elderly|disabilit\w*|homeless\w*)\b"),
    "health": ("Health & mental health", set(), NO_SUBJECTS, r"\b(health|medical|medicaid|hospital\w*|mental|pharmac\w*|nurs\w*|physician\w*)\b"),
    "edu": ("Education", set(), NO_SUBJECTS, r"\b(school\w*|student\w*|teacher\w*|education|college\w*|universit\w*|tuition)\b"),
    "transp": ("Transportation", set(), NO_SUBJECTS, r"\b(vehicle\w*|highway\w*|road\w*|traffic|transit|driver\w*|driving|motor)\b"),
    "labor": ("Labor & public employees", set(), NO_SUBJECTS, r"\b(wage\w*|employ\w*|worker\w*|labor|pension\w*|retirement)\b"),
    "housing": ("Housing", set(), NO_SUBJECTS, r"\b(housing|landlord\w*|tenant\w*|rent|eviction\w*|zoning)\b"),
    "ag": ("Agriculture & natural resources", set(), NO_SUBJECTS, r"\b(agricultur\w*|farm\w*|livestock|fish\w*|wildlife|hunting|forest\w*|timber)\b"),
    "gov": ("Elections & state government", set(), NO_SUBJECTS, r"\b(election\w*|voter\w*|voting|ballot\w*|state agenc\w*|ethics|right-to-know|public records)\b"),
    "biz": ("Business & consumers", set(), NO_SUBJECTS, r"\b(consumer\w*|business\w*|insurance|bank\w*|licens\w*|corporat\w*|economic development|gaming|gambling|liquor|alcohol\w*)\b"),
    "const": ("Constitutional amendments", set(), NO_SUBJECTS, ""),
}
# The General Court's subject codes (each bill has one; SubjectCodes.txt) -> topic. Agency Appropriations, Legislature,
# Memorials, Discrimination and Federal and International Relations give none.
SUBJECT_TOPICS = {
    "AGR": "ag", "ANI": "ag", "FNG": "ag", "PAR": "ag", "WAN": "env",
    "BAF": "biz", "BAI": "biz", "CAP": "biz", "INS": "biz", "OCC": "biz", "GAM": "biz", "LAB": "biz",
    "CCP": "safety", "CIV": "safety", "CTS": "safety", "POL": "safety",
    "CHI": "human", "DOM": "human", "MIL": "human", "WMM": "human",
    "COU": "local", "MUN": "local",
    "EDG": "edu", "EDF": "edu",
    "ENU": "env", "ENC": "env", "ENA": "env",
    "ELE": "gov", "STG": "gov", "RTK": "gov",
    "EPR": "labor", "RET": "labor", "WCU": "labor",
    "MOT": "transp", "TRA": "transp",
    "PMH": "health",
    "PRP": "housing", "ZAP": "housing",
    "TAL": "tax", "TAS": "tax",
}
# Committee names (both houses') -> topic, for committees with one subject. Finance, Ways and Means (taxes, but also
# gambling and fees: only the House's gives "tax"), Executive Departments and Administration, Legislative
# Administration, Rules and the special committees give none.
COMMITTEE_TOPICS = {
    "Education": "edu", "Education Policy and Administration": "edu", "Education Funding": "edu",
    "Education Finance": "edu", "Education and Workforce Development": "edu",
    "Environment and Agriculture": "ag", "Fish and Game and Marine Resources": "ag",
    "Resources, Recreation and Development": "ag",
    "Health, Human Services and Elderly Affairs": "health", "Health and Human Services": "health",
    "Judiciary": "safety", "Criminal Justice and Public Safety": "safety",
    "Labor, Industrial and Rehabilitative Services": "labor",
    "Municipal and County Government": "local",
    "Public Works and Highways": "transp", "Transportation": "transp",
    "Science, Technology and Energy": "env", "Energy and Natural Resources": "env",
    "State-Federal Relations and Veterans Affairs": "human", "Children and Family Law": "human",
    "Commerce and Consumer Affairs": "biz", "Commerce": "biz",
    "Election Law": "gov", "Housing": "housing",
}
TOPIC_WORDS = {k: re.compile(v[3], re.I) for k, v in TOPICS.items() if v[3]}

COUNTIES = []
DISTRICTS_PATH = os.path.join(DATA, "district_counties.json")
TOWNS_PATH = os.path.join(DATA, "district_towns.json")
# House districts have names ("Hillsborough 12"); their ids are the county's code times 100 plus the number (612).
DISTRICT_NAMES_PATH = os.path.join(DATA, "district_names.json")

_NAMING = re.compile(r"\b(?:designat\w*|nam\w*)\b.*\b(?:bridge|interchange|highway|route|memorial|building|park)\b|\bmemorial (?:highway|bridge|interchange)\b", re.I)
NARROW_KINDS = ["", "person", "org", "naming"]


def narrow_kind(title):
    return "naming" if _NAMING.search(title) else ""


# Governors and the day each took office (New Hampshire's governors serve two-year terms, from the first Thursday of
# January).
GOVERNORS = [("Hassan", "2013-01-03"), ("Sununu", "2017-01-05"), ("Ayotte", "2025-01-09")]
GOV_SINCE = GOVERNORS[-1][1]


def governor_on(day):
    who = GOVERNORS[0][0]
    for name, start in GOVERNORS:
        if day >= start:
            who = name
    return who


TRENDS = []
WORDING = []
