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


def session_label(session):
    return str(session)


CF_ANALYTICS_TOKEN = ""
GOATCOUNTER_CODE = ""

DELEGATION_NAMES = set()
# Who decides which bills reach each house's floor: the Speaker (with the House Majority Leader) and, in the Senate,
# the President Pro Tempore (with the Senate Majority Leader).
LEADERS = {"S": ("Martin Looney", "Senate President Pro Tempore", "him"),
           "H": ("Matthew Ritter", "Speaker of the House", "him")}


def delegation(session):
    return {}


# Topic: (label, committees, official subjects (none used), title words). Committees are joint (both houses share
# them), by their codes in the files.
NO_SUBJECTS = re.compile(r"(?!)")
TOPICS = {
    "env": ("Environment & energy", {"ENV", "ET"}, NO_SUBJECTS, r"\b(environment\w*|climate|emission\w*|renewable|solar|wind|pollut\w*|water|energy|utilit\w*)\b"),
    "local": ("Local government", {"PD"}, NO_SUBJECTS, r"\b(municipal\w*|town\w*|cities|city|local government|regional)\b"),
    "tax": ("Taxes", {"FIN"}, NO_SUBJECTS, r"\b(tax\w*|revenue)\b"),
    "safety": ("Public safety & courts", {"JUD", "PS"}, NO_SUBJECTS, r"\b(crim\w*|firearm\w*|police|court\w*|sentenc\w*|prison\w*|jail\w*|felony|misdemeanor|correction\w*)\b"),
    "human": ("Human services", {"HS", "KID", "AGE", "VA"}, NO_SUBJECTS, r"\b(child care|foster|veteran\w*|senior\w*|aging|disabilit\w*|homeless\w*)\b"),
    "health": ("Health & mental health", {"PH", "INS"}, NO_SUBJECTS, r"\b(health|medical|medicaid|hospital\w*|mental|pharmac\w*|nurs\w*|physician\w*)\b"),
    "edu": ("Education", {"ED", "HED"}, NO_SUBJECTS, r"\b(school\w*|student\w*|teacher\w*|education|college\w*|universit\w*)\b"),
    "transp": ("Transportation", {"TRA"}, NO_SUBJECTS, r"\b(vehicle\w*|highway\w*|road\w*|traffic|transit|driver\w*|motor)\b"),
    "labor": ("Labor & public employees", {"LAB"}, NO_SUBJECTS, r"\b(wage\w*|employ\w*|worker\w*|labor|pension\w*)\b"),
    "housing": ("Housing", {"HSG"}, NO_SUBJECTS, r"\b(housing|landlord\w*|tenant\w*|rent|eviction\w*)\b"),
    "ag": ("Agriculture", {"ENV"}, NO_SUBJECTS, r"\b(agricultur\w*|farm\w*|livestock|animal\w*)\b"),
    "gov": ("Elections & state government", {"GAE", "GL"}, NO_SUBJECTS, r"\b(election\w*|voter\w*|ballot\w*|state agenc\w*|ethics)\b"),
    "biz": ("Business & consumers", {"CE", "BA", "INS", "GL"}, NO_SUBJECTS, r"\b(consumer\w*|business\w*|insurance|bank\w*|licens\w*)\b"),
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


TRENDS = []
WORDING = []
