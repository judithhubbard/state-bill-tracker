"""Arkansas: the settings and wording that are particular to this state.

build_data.py reads these as P.<name>, with the same names as states/ny/profile.py.
"""
import os, re

DATA = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "ar"))
SITE_DIR = "ar"

STATE_NAME = "Arkansas"
SITE_NAME = "Arkansas Bill Tracker"
LEGISLATURE = "Arkansas General Assembly"
TIMEZONE = "America/Chicago"
PUBLIC_URL = "https://statebilltracker.org/ar/"
SITE_URL = os.environ.get("SITE_URL", PUBLIC_URL)

# Each General Assembly spans two years (the 95th is 2025-26): a regular session in odd years (from the second Monday of
# January, 60 days unless extended; it recesses in April and adjourns sine die weeks later) and a fiscal session in even
# years (from the second Wednesday of April, 30 days), which is for appropriations: any other bill needs two-thirds of
# each house to be introduced (Arkansas Constitution, Art. 5, sec. 5, Amendment 86). Bills die when a session adjourns.
# A page a year: its regular or fiscal session. Extraordinary sessions (2023S1, 2024S2, 2026S1: a few bills each, numbered
# from HB1001 again) are left out, as Texas's special sessions are.
YEARS = 1
LOWER = "H"
LOWER_NAME = "House"
TITLES = {"S": "Sen.", "H": "Rep."}


def session_of(year):
    return year


def session_id(session):
    """The Legislature's code for a page's session: 2025 -> "2025R", 2026 -> "2026F"."""
    return f"{session}{'R' if session % 2 else 'F'}"


def session_kind(session):
    """Regular sessions (odd years) and fiscal sessions (even years, almost all appropriations) are compared only with
    their own kind in the statistics."""
    return "regular" if session % 2 else "fiscal"


def session_label(session):
    return f"{session} {session_kind(session)}"


CF_ANALYTICS_TOKEN = ""
GOATCOUNTER_CODE = ""

DELEGATION_NAMES = set()
# Who decides which bills reach each house's floor: the Speaker, and the Senate's President Pro Tempore (the Lieutenant
# Governor presides over the Senate but isn't a senator). From the members file's public-service lines ("Speaker of the
# House 2025", "2025 President Pro Tempore"), 2026-11-08; the 96th General Assembly chooses its own in January 2027.
LEADERS = {"S": ("Bart Hester", "President Pro Tempore of the Senate", "him"),
           "H": ("Brian S. Evans", "Speaker of the House", "him")}
# Other leadership posts, shown on the members' cards: the ones the members file names for 2025 (its House majority and
# minority leaders' lines are years old, so they're left out).
POSITIONS = {("S", "Blake Johnson"): "Majority Leader", ("S", "Greg Leding"): "Minority Leader"}


def delegation(session):
    return {}


# Topic: (label, committees (unused; see COMMITTEE_TOPICS), official subjects (none), title words).
NO_SUBJECTS = re.compile(r"(?!)")
TOPICS = {
    "env": ("Environment & energy", set(), NO_SUBJECTS, r"\b(environment\w*|climate|emission\w*|renewable|solar|wind|pollut\w*|energy|utilit\w*|mining|oil and gas|brine|lithium|nuclear|carbon|electric\w*|PFAS)\b"),
    "local": ("Local government", set(), NO_SUBJECTS, r"\b(municipal\w*|county|counties|annexation|local government|city|cities)\b"),
    "tax": ("Taxes", set(), NO_SUBJECTS, r"\b(tax\w*|revenue)\b"),
    "safety": ("Public safety & courts", set(), NO_SUBJECTS, r"\b(crim\w*|firearm\w*|police|court\w*|sentenc\w*|prison\w*|jail\w*|felony|misdemeanor|correction\w*|expungement|law enforcement)\b"),
    "human": ("Human services", set(), NO_SUBJECTS, r"\b(child care|foster (?:care|child\w*|parent\w*|home\w*|youth)|veteran\w*|senior\w*|elderly|disabilit\w*|homeless\w*|human services)\b"),
    "health": ("Health & mental health", set(), NO_SUBJECTS, r"\b(health|medical|medicaid|hospital\w*|mental|pharmac\w*|nurs\w*|physician\w*)\b"),
    "edu": ("Education", set(), NO_SUBJECTS, r"\b(school\w*|student\w*|teacher\w*|education|college\w*|universit\w*|tuition)\b"),
    "transp": ("Transportation", set(), NO_SUBJECTS, r"\b(vehicle\w*|highway\w*|road\w*|traffic|transit|driver\w*|driving|motor)\b"),
    "labor": ("Labor & public employees", set(), NO_SUBJECTS, r"\b(wage\w*|employ\w*|worker\w*|labor|pension\w*|retirement)\b"),
    "housing": ("Housing", set(), NO_SUBJECTS, r"\b(housing|landlord\w*|tenant\w*|rent|eviction\w*)\b"),
    "ag": ("Agriculture & natural resources", set(), NO_SUBJECTS, r"\b(agricultur\w*|farm\w*|livestock|fish\w*|wildlife|hunting|forestry|timber|water rights)\b"),
    "gov": ("Elections & state government", set(), NO_SUBJECTS, r"\b(election\w*|voter\w*|voting|ballot\w*|state agenc\w*|ethics|freedom of information)\b"),
    "biz": ("Business & consumers", set(), NO_SUBJECTS, r"\b(consumer\w*|business\w*|insurance|bank\w*|licens\w*|corporat\w*|economic development|gaming|casino\w*|alcohol\w*)\b"),
    "const": ("Constitutional amendments", set(), NO_SUBJECTS, ""),
}
# Standing committees (as convert.committee() names them, both houses) -> topic, for committees with one main subject.
# Joint Budget (appropriations), Rules, Management and Advanced Communications give none.
COMMITTEE_TOPICS = {
    "Agriculture, Forestry and Economic Development": "ag",
    "City, County and Local Affairs": "local",
    "Education": "edu",
    "Insurance and Commerce": "biz",
    "Judiciary": "safety",
    "Public Health, Welfare and Labor": "health",
    "Revenue and Tax": "tax", "Revenue and Taxation": "tax",
    "State Agencies and Governmental Affairs": "gov",
    "Public Transportation": "transp", "Transportation, Technology and Legislative Affairs": "transp",
    "Aging, Children and Youth, and Legislative Affairs": "human",
    "Aging, Children and Youth, Legislative and Military Affairs": "human", "Children and Youth": "human",
    "Military and Veterans Affairs": "human",
    "Public Retirement and Social Security Programs": "labor",
    "Energy": "env",
}
TOPIC_WORDS = {k: re.compile(v[3], re.I) for k, v in TOPICS.items() if v[3]}

COUNTIES = []
DISTRICTS_PATH = os.path.join(DATA, "district_counties.json")
TOWNS_PATH = os.path.join(DATA, "district_towns.json")

_NAMING = re.compile(r"\b(?:designat\w*|nam\w*|renam\w*)\b.*\b(?:bridge|interchange|highway|route|memorial|building|park)\b|\bmemorial (?:highway|bridge|interchange)\b", re.I)
NARROW_KINDS = ["", "person", "org", "naming"]


def narrow_kind(title):
    return "naming" if _NAMING.search(title) else ""


# Governors and the day each took office.
GOVERNORS = [("Hutchinson", "2015-01-13"), ("Sanders", "2023-01-10")]
GOV_SINCE = GOVERNORS[-1][1]


def governor_on(day):
    who = GOVERNORS[0][0]
    for name, start in GOVERNORS:
        if day >= start:
            who = name
    return who


TRENDS = []
WORDING = []
