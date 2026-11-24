"""Connecticut: the settings and wording that are particular to this state.

build_data.py reads these as P.<name>, with the same names as states/ny/profile.py.
"""
import os, re

DATA = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "ct"))
SITE_DIR = "ct"

STATE_NAME = "Connecticut"
SITE_NAME = "Connecticut Bill Tracker"
LEGISLATURE = "Connecticut General Assembly"
TIMEZONE = "America/New_York"
PUBLIC_URL = "https://statebilltracker.org/ct/"
SITE_URL = os.environ.get("SITE_URL", PUBLIC_URL)

# One session a year: a long one in odd years (January to early June), a short one in even years (February to early
# May). Bills don't carry over to the next year. Bills keep their numbers through both houses.
YEARS = 1
LOWER = "H"
LOWER_NAME = "House"
TITLES = {"S": "Sen.", "H": "Rep."}


def session_of(year):
    return year


def session_kind(session):
    """Sessions alternate: a long session in odd years (five months), a short one in even years (three months, mostly the budget). Statistics compare a session only with past sessions of the same kind."""
    return "long" if session % 2 else "short"


def session_label(session):
    return str(session)


CF_ANALYTICS_TOKEN = ""
GOATCOUNTER_CODE = ""

DELEGATION_NAMES = set()
# Who decides which bills reach each house's floor: the Speaker (with the House Majority Leader) and, in the Senate,
# the President Pro Tempore (with the Senate Majority Leader).
LEADERS = {"S": ("Martin Looney", "Senate President Pro Tempore", "him"),
           "H": ("Matthew Ritter", "Speaker of the House", "him")}
# Leaders already chosen for the next legislature, each in place from the day they take the post (governors.py's
# apply_leaders()); pronouns only where their own official biography gives them, else "them". Checked 2026-11-19.
LEADERS_NEXT = {
    "S": ("Bob Duff", "Senate President Pro Tempore", "them", "2027-01-06"),
}


def delegation(session):
    return {}


# Topic: (label, committees, official subjects (none used), title words). Committees are joint (both houses share
# them), by their codes in the files.
NO_SUBJECTS = re.compile(r"(?!)")
TOPICS = {
    "env": ("Environment and energy", {"ENV", "ET"}, NO_SUBJECTS, r"\b(environment\w*|climate|emission\w*|renewable|solar|wind|pollut\w*|water|energy|utilit\w*)\b"),
    "local": ("Local government", {"PD"}, NO_SUBJECTS, r"\b(municipal\w*|town\w*|cities|city|local government|regional)\b"),
    "tax": ("Taxes", {"FIN"}, NO_SUBJECTS, r"\b(tax\w*|revenue)\b"),
    "safety": ("Public safety and courts", {"JUD", "PS"}, NO_SUBJECTS, r"\b(crim\w*|firearm\w*|police|court\w*|sentenc\w*|prison\w*|jail\w*|felony|misdemeanor|correction\w*)\b"),
    "human": ("Social services", {"HS", "KID", "AGE", "VA"}, NO_SUBJECTS, r"\b(child care|foster|veteran\w*|senior\w*|aging|disabilit\w*|homeless\w*)\b"),
    "health": ("Health", {"PH", "INS"}, NO_SUBJECTS, r"\b(health|medical|medicaid|hospital\w*|mental|pharmac\w*|nurs\w*|physician\w*)\b"),
    "edu": ("Education", {"ED", "HED"}, NO_SUBJECTS, r"\b(school\w*|student\w*|teacher\w*|education|college\w*|universit\w*)\b"),
    "transp": ("Transportation", {"TRA"}, NO_SUBJECTS, r"\b(vehicle\w*|highway\w*|road\w*|traffic|transit|driver\w*|motor)\b"),
    "labor": ("Jobs and workers", {"LAB"}, NO_SUBJECTS, r"\b(wage\w*|employ\w*|worker\w*|labor|pension\w*)\b"),
    "housing": ("Housing", {"HSG"}, NO_SUBJECTS, r"\b(housing|landlord\w*|tenant\w*|rent|eviction\w*)\b"),
    "ag": ("Agriculture and natural resources", {"ENV"}, NO_SUBJECTS, r"\b(agricultur\w*|farm\w*|livestock|animal\w*)\b"),
    "gov": ("Elections and government", {"GAE", "GL"}, NO_SUBJECTS, r"\b(election\w*|voter\w*|ballot\w*|state agenc\w*|ethics)\b"),
    "biz": ("Business and consumers", {"CE", "BA", "INS", "GL"}, NO_SUBJECTS, r"\b(consumer\w*|business\w*|insurance|bank\w*|licens\w*)\b"),
    # Joint resolutions proposing constitutional amendments (tagged by convert.py, not by words).
    "const": ("Constitutional amendments", set(), NO_SUBJECTS, ""),
}
TOPIC_WORDS = {k: re.compile(v[3], re.I) for k, v in TOPICS.items() if v[3]}

COUNTIES = []
DISTRICTS_PATH = os.path.join(DATA, "district_counties.json")
TOWNS_PATH = os.path.join(DATA, "district_towns.json")

_NAMING = re.compile(r"\b(?:designat\w*|nam\w*)\b.*\b(?:bridge|interchange|highway|route|memorial|building|park)\b", re.I)
NARROW_KINDS = ["", "person", "org", "naming"]


def narrow_kind(title):
    return "naming" if _NAMING.search(title) else ""


# Governors and the day each took office (the Wednesday after the first Monday of January after the election).
GOVERNORS = [("Malloy", "2011-01-05"), ("Lamont", "2019-01-09")]
GOV_SINCE = GOVERNORS[-1][1]


def governor_on(day):
    who = GOVERNORS[0][0]
    for name, start in GOVERNORS:
        if day >= start:
            who = name
    return who


# ---- What's changing: subjects whose share of bills changed most across the sessions shown, picked by hand from an
# automatic phrase scan and checked against samples of the bills matched (notes/trends.md). Long (odd-year) and short
# sessions were compared with their own kind too. Matched on the bills' titles (no separate summaries).
TRENDS = [
    ("rise", "Artificial intelligence", r"(?i:artificial intelligence|automated decision|algorithmic|deep ?fake|synthetic media|\bgenerative|chatbot)|\bAI\b", False),
    ("rise", "Cannabis", r"cannabis|marijuana", True),
    ("rise", "PFAS (“forever chemicals”)", r"\bPFAS\b|perfluoro|polyfluoro|forever chemical", True),
    ("rise", "Solar power", r"\bsolar\b", True),
    ("spike", "Opioids", r"opioid|opiate|naloxone", True),
    ("spike", "Sexual harassment", r"sexual harassment", True),
    ("spike", "COVID-19", r"covid|coronavirus|pandemic", True),
]
WORDING = []
