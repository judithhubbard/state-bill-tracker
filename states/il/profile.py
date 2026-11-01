"""Illinois: the settings and wording that are particular to this state.

build_data.py reads these as P.<name>, with the same names as states/ny/profile.py.
"""
import os, re

DATA = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "il"))
SITE_DIR = "il"

STATE_NAME = "Illinois"
SITE_NAME = "Illinois Bill Tracker"
LEGISLATURE = "Illinois General Assembly"
TIMEZONE = "America/Chicago"
PUBLIC_URL = "https://statebilltracker.org/il/"
SITE_URL = os.environ.get("SITE_URL", PUBLIC_URL)

# Each General Assembly sits two years, from the second Wednesday of January of odd years (the 104th, 2025-26).
# Bills keep their numbers through both houses.
YEARS = 2
LOWER = "H"
LOWER_NAME = "House"
TITLES = {"S": "Sen.", "H": "Rep."}


def session_of(year):
    return year if year % 2 else year - 1


def assembly_of(session):
    """2025 -> 104."""
    return (session - 1817) // 2


def session_label(session):
    return f"{session}–{str(session + 1)[2:]}"


CF_ANALYTICS_TOKEN = ""
GOATCOUNTER_CODE = ""

DELEGATION_NAMES = set()
# Who decides which bills reach each house's floor: the Speaker and the Senate President (whose Rules Committees
# assign bills to committees and hold the ones that don't move).
LEADERS = {"S": ("Don Harmon", "Senate President", "him"),
           "H": ("Emanuel \"Chris\" Welch", "Speaker of the House", "him")}


def delegation(session):
    return {}


# Topic: (label, committees, official subjects (none in Illinois's files), title words). Committees are named as in
# the actions ("Assigned to Executive Committee" -> "Executive").
NO_SUBJECTS = re.compile(r"(?!)")
TOPICS = {
    "env": ("Environment & energy", {"Energy & Environment", "Environment and Conservation", "Energy and Public Utilities", "Public Utilities"},
            NO_SUBJECTS, r"\b(environment\w*|climate|emission\w*|renewable|solar|wind|pollut\w*|water|energy|utilit\w*|conservation|epa)\b"),
    "local": ("Local government", {"Counties & Townships", "Cities & Villages", "Local Government"}, NO_SUBJECTS,
              r"\b(municipal\w*|county|counties|township\w*|local government|special district\w*)\b"),
    "tax": ("Taxes", {"Revenue & Finance", "Revenue"}, NO_SUBJECTS, r"\b(tax\w*|revenue)\b"),
    "safety": ("Public safety & courts", {"Judiciary - Criminal", "Criminal Law", "Public Safety", "Police & Fire Committee",
               "Restorative Justice", "Judiciary - Civil", "Judiciary"}, NO_SUBJECTS,
               r"\b(crim\w*|firearm\w*|police|court\w*|sentenc\w*|prison\w*|jail\w*|felony|misdemeanor|corrections)\b"),
    "human": ("Human services", {"Human Services", "Adoption & Child Welfare", "Aging", "Veterans' Affairs", "Veterans Affairs"},
              NO_SUBJECTS, r"\b(child care|foster|dcfs|veteran\w*|senior\w*|aging|disabilit\w*|homeless\w*)\b"),
    "health": ("Health & mental health", {"Health Care Availability & Accessibility", "Health Care Licenses", "Mental Health & Addiction",
               "Public Health", "Health and Human Services", "Insurance"}, NO_SUBJECTS,
               r"\b(health|medical|medicaid|hospital\w*|mental|pharmac\w*|nurs\w*|physician\w*)\b"),
    "edu": ("Education", {"Elementary & Secondary Education: School Curriculum & Policies", "Elementary & Secondary Education: Administration, Licensing & Charter Schools",
            "Higher Education", "Education"}, NO_SUBJECTS, r"\b(school\w*|student\w*|teacher\w*|education|college\w*|universit\w*)\b"),
    "transp": ("Transportation", {"Transportation: Vehicles & Safety", "Transportation: Regulation, Roads & Bridges", "Transportation"},
               NO_SUBJECTS, r"\b(vehicle\w*|highway\w*|road\w*|traffic|transit|driver\w*|toll\w*)\b"),
    "labor": ("Labor & public employees", {"Labor & Commerce", "Labor", "Personnel & Pensions", "Pensions"}, NO_SUBJECTS,
              r"\b(wage\w*|employ\w*|worker\w*|labor|pension\w*)\b"),
    "housing": ("Housing", {"Housing"}, NO_SUBJECTS, r"\b(housing|landlord\w*|tenant\w*|rent|eviction\w*)\b"),
    "ag": ("Agriculture & natural resources", {"Agriculture & Conservation", "Agriculture"}, NO_SUBJECTS, r"\b(agricultur\w*|farm\w*|livestock|animal\w*)\b"),
    # Not the Executive Committees: they get bills on every subject.
    "gov": ("Elections & state government", {"Ethics & Elections", "State Government Administration", "Elections"},
            NO_SUBJECTS, r"\b(election\w*|voter\w*|ballot\w*|state agenc\w*|ethics)\b"),
    # Joint resolutions proposing constitutional amendments (tagged by convert.py, not by words).
    "const": ("Constitutional amendments", set(), NO_SUBJECTS, ""),
    "biz": ("Business & consumers", {"Consumer Protection", "Financial Institutions and Licensing", "Financial Institutions",
            "Commerce", "Licensed Activities", "Insurance"}, NO_SUBJECTS,
            r"\b(consumer\w*|business\w*|insurance|bank\w*|licens\w*)\b"),
}
TOPIC_WORDS = {k: re.compile(v[3], re.I) for k, v in TOPICS.items() if v[3]}

COUNTIES = []
DISTRICTS_PATH = os.path.join(DATA, "district_counties.json")
TOWNS_PATH = os.path.join(DATA, "district_towns.json")

_NAMING = re.compile(r"\b(?:designat\w*|nam\w*)\b.*\b(?:bridge|interchange|highway|route|memorial|building|park)\b", re.I)
NARROW_KINDS = ["", "person", "org", "naming"]


def narrow_kind(title):
    return "naming" if _NAMING.search(title) else ""


# Governors and the day each took office (the second Monday of January after the election).
GOVERNORS = [("Rauner", "2015-01-12"), ("Pritzker", "2019-01-14")]
GOV_SINCE = GOVERNORS[-1][1]


def governor_on(day):
    who = GOVERNORS[0][0]
    for name, start in GOVERNORS:
        if day >= start:
            who = name
    return who


TRENDS = []
WORDING = []
