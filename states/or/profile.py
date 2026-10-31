"""Oregon: the settings and wording that are particular to this state.

build_data.py reads these as P.<name>, with the same names as states/ny/profile.py.
"""
import os, re

DATA = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "or"))
SITE_DIR = "or"

STATE_NAME = "Oregon"
SITE_NAME = "Oregon Bill Tracker"
LEGISLATURE = "Oregon Legislative Assembly"
TIMEZONE = "America/Los_Angeles"
PUBLIC_URL = "https://statebilltracker.org/or/"
SITE_URL = os.environ.get("SITE_URL", PUBLIC_URL)

# One regular session a year: a long one in odd years (January to June, 160 days at most) and a short one in even
# years (February to March, 35 days); bills don't carry over. Special sessions are separate and not shown.
YEARS = 1
LOWER = "H"
LOWER_NAME = "House"
TITLES = {"S": "Sen.", "H": "Rep."}


def session_of(year):
    return year


def session_kind(session):
    """Sessions alternate: a long session in odd years (up to 160 days), a short one in even years (35 days, with fewer bills allowed). Statistics compare a session only with past sessions of the same kind."""
    return "long" if session % 2 else "short"


def session_label(session):
    return str(session)


def session_key(session):
    """2025 -> "2025R1", the API's name for the regular session."""
    return f"{session}R1"


CF_ANALYTICS_TOKEN = ""
GOATCOUNTER_CODE = ""

DELEGATION_NAMES = set()
# Who decides which bills reach each house's floor: the Speaker and the Senate President.
LEADERS = {"S": ("Rob Wagner", "Senate President", "him"),
           "H": ("Julie Fahey", "Speaker of the House", "her")}


def delegation(session):
    return {}


# Topic: (label, committees, official subjects (none used), title words). Committees by their codes (House "H...",
# Senate "S...", joint "J...").
NO_SUBJECTS = re.compile(r"(?!)")
TOPICS = {
    # Joint resolutions proposing constitutional amendments (tagged by convert.py, not by words).
    "const": ("Constitutional amendments", set(), NO_SUBJECTS, ""),
    "env": ("Environment & energy", {"HCEE", "SEE", "HALNRW", "SNRW", "JWMNR"}, NO_SUBJECTS, r"\b(environment\w*|climate|emission\w*|renewable|solar|wind|pollut\w*|water|energy|utilit\w*|wildfire\w*|forest\w*)\b"),
    "local": ("Local government", set(), NO_SUBJECTS, r"\b(municipal\w*|county|counties|cities|city|local government|special district\w*)\b"),
    "tax": ("Taxes", {"HREV", "SFR"}, NO_SUBJECTS, r"\b(tax\w*|revenue)\b"),
    "safety": ("Public safety & courts", {"HJUD", "SJUD", "JWMPS"}, NO_SUBJECTS, r"\b(crim\w*|firearm\w*|police|court\w*|sentenc\w*|prison\w*|jail\w*|felony|misdemeanor|correction\w*)\b"),
    "human": ("Human services", {"HECHS", "SHS", "JWMHS", "HEMV", "SVEMFW"}, NO_SUBJECTS, r"\b(child care|foster|veteran\w*|senior\w*|aging|disabilit\w*|homeless\w*)\b"),
    "health": ("Health & mental health", {"HHC", "SHC", "HBH", "SECBH"}, NO_SUBJECTS, r"\b(health|medical|medicaid|hospital\w*|mental|pharmac\w*|nurs\w*|physician\w*)\b"),
    "edu": ("Education", {"HED", "SED", "JWMED"}, NO_SUBJECTS, r"\b(school\w*|student\w*|teacher\w*|education|college\w*|universit\w*)\b"),
    "transp": ("Transportation", {"HCT", "SCT", "JTO", "JWMTR"}, NO_SUBJECTS, r"\b(vehicle\w*|highway\w*|road\w*|traffic|transit|driver\w*|motor)\b"),
    "labor": ("Labor & public employees", {"HLWD", "SLB"}, NO_SUBJECTS, r"\b(wage\w*|employ\w*|worker\w*|labor|pension\w*)\b"),
    "housing": ("Housing", {"HHOUSH", "SHDEV"}, NO_SUBJECTS, r"\b(housing|landlord\w*|tenant\w*|rent|eviction\w*|homeless\w*)\b"),
    "ag": ("Agriculture & natural resources", {"HALNRW", "SNRW"}, NO_SUBJECTS, r"\b(agricultur\w*|farm\w*|livestock|fish\w*|wildlife|timber)\b"),
    "gov": ("Elections & state government", {"SCGG", "HRULES", "SRULES", "JWMGG"}, NO_SUBJECTS, r"\b(election\w*|voter\w*|ballot\w*|state agenc\w*|ethics|public records)\b"),
    "biz": ("Business & consumers", {"HCCP", "HECDSB", "SLB", "SCGG"}, NO_SUBJECTS, r"\b(consumer\w*|business\w*|insurance|bank\w*|licens\w*)\b"),
}
TOPIC_WORDS = {k: re.compile(v[3], re.I) for k, v in TOPICS.items() if v[3]}

COUNTIES = []
DISTRICTS_PATH = os.path.join(DATA, "district_counties.json")
TOWNS_PATH = os.path.join(DATA, "district_towns.json")

_NAMING = re.compile(r"\b(?:designat\w*|nam\w*)\b.*\b(?:bridge|interchange|highway|route|memorial|building|park)\b", re.I)
NARROW_KINDS = ["", "person", "org", "naming"]


def narrow_kind(title):
    return "naming" if _NAMING.search(title) else ""


# Governors and the day each took office (the second Monday of January after the election; Brown succeeded Kitzhaber).
GOVERNORS = [("Brown", "2015-02-18"), ("Kotek", "2023-01-09")]
GOV_SINCE = GOVERNORS[-1][1]


def governor_on(day):
    who = GOVERNORS[0][0]
    for name, start in GOVERNORS:
        if day >= start:
            who = name
    return who


TRENDS = []
WORDING = []
