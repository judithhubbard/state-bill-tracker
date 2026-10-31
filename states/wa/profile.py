"""Washington: the settings and wording that are particular to this state.

build_data.py reads these as P.<name>, with the same names as states/ny/profile.py.
"""
import os, re

DATA = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "wa"))
SITE_DIR = "wa"

STATE_NAME = "Washington"
SITE_NAME = "Washington Bill Tracker"
LEGISLATURE = "Washington State Legislature"
TIMEZONE = "America/Los_Angeles"
PUBLIC_URL = "https://statebilltracker.org/wa/"
SITE_URL = os.environ.get("SITE_URL", PUBLIC_URL)

# Two-year bienniums from odd years (2025-26), with a 105-day session in the first year and a 60-day one in the
# second; bills stay alive through both. Bills keep their numbers through both houses (a substitute is "SHB 1003").
YEARS = 2
LOWER = "H"
LOWER_NAME = "House"
TITLES = {"S": "Sen.", "H": "Rep."}


def session_of(year):
    return year if year % 2 else year - 1


def biennium(session):
    """2025 -> "2025-26"."""
    return f"{session}-{str(session + 1)[2:]}"


def session_label(session):
    return f"{session}–{str(session + 1)[2:]}"


CF_ANALYTICS_TOKEN = ""
GOATCOUNTER_CODE = ""

DELEGATION_NAMES = set()
# Who decides which bills reach each house's floor: each house's Rules Committee, which the Speaker chairs in the House;
# in the Senate the Majority Leader runs the floor (the Lieutenant Governor presides and chairs Senate Rules).
LEADERS = {"S": ("Jamie Pedersen", "Senate Majority Leader", "him"),
           "H": ("Laurie Jinkins", "Speaker of the House", "her")}


def delegation(session):
    return {}


# Topic: (label, committees, official subjects (none), title words). Committees as the history names them, current and
# earlier bienniums' names.
NO_SUBJECTS = re.compile(r"(?!)")
TOPICS = {
    "env": ("Environment & energy", {"Environment & Energy", "Environment, Energy & Technology", "Energy, Environment & Telecommunications",
            "Environment, Energy & Water"}, NO_SUBJECTS,
            r"\b(environment\w*|climate|emission\w*|renewable|solar|wind|pollut\w*|water|energy|utilit\w*|salmon|forest\w*)\b"),
    "local": ("Local government", {"Local Government", "Local Government, Land Use & Tribal Affairs"}, NO_SUBJECTS,
              r"\b(municipal\w*|county|counties|cities|city|local government|special district\w*|growth management)\b"),
    "tax": ("Taxes", {"Finance"}, NO_SUBJECTS, r"\b(tax\w*|revenue)\b"),
    "safety": ("Public safety & courts", {"Community Safety", "Community Safety, Justice, & Reentry", "Public Safety", "Civil Rights & Judiciary",
               "Law & Justice"}, NO_SUBJECTS,
               r"\b(crim\w*|firearm\w*|police|court\w*|sentenc\w*|prison\w*|jail\w*|felony|misdemeanor|corrections)\b"),
    "human": ("Human services", {"Early Learning & Human Services", "Human Services", "Human Services, Reentry & Rehabilitation",
              "Veterans"}, NO_SUBJECTS, r"\b(child care|foster|veteran\w*|senior\w*|aging|disabilit\w*|homeless\w*)\b"),
    "health": ("Health & mental health", {"Health Care & Wellness", "Health & Long-Term Care", "Behavioral Health"}, NO_SUBJECTS,
               r"\b(health|medical|medicaid|hospital\w*|mental|pharmac\w*|nurs\w*|physician\w*)\b"),
    "edu": ("Education", {"Education", "Early Learning & K-12 Education", "Postsecondary Education & Workforce",
            "Higher Education & Workforce Development", "College & Workforce Development"}, NO_SUBJECTS,
            r"\b(school\w*|student\w*|teacher\w*|education|college\w*|universit\w*)\b"),
    "transp": ("Transportation", {"Transportation"}, NO_SUBJECTS, r"\b(vehicle\w*|highway\w*|road\w*|traffic|transit|driver\w*|toll\w*|ferr\w*)\b"),
    "labor": ("Labor & public employees", {"Labor & Workplace Standards", "Labor & Commerce", "Labor, Commerce & Tribal Affairs"}, NO_SUBJECTS,
              r"\b(wage\w*|employ\w*|worker\w*|labor|pension\w*)\b"),
    "housing": ("Housing", {"Housing"}, NO_SUBJECTS, r"\b(housing|landlord\w*|tenant\w*|rent|eviction\w*)\b"),
    "ag": ("Agriculture & natural resources", {"Agriculture & Natural Resources", "Agriculture, Water, Natural Resources & Parks"}, NO_SUBJECTS,
           r"\b(agricultur\w*|farm\w*|livestock|fish\w*|wildlife|timber)\b"),
    "gov": ("Elections & state government", {"State Government & Tribal Relations", "State Government, Tribal Affairs & Elections",
            "State Government & Elections"}, NO_SUBJECTS, r"\b(election\w*|voter\w*|ballot\w*|state agenc\w*|ethics|public records)\b"),
    # Joint resolutions proposing constitutional amendments (tagged by convert.py, not by words).
    "const": ("Constitutional amendments", set(), NO_SUBJECTS, ""),
    "biz": ("Business & consumers", {"Consumer Protection & Business", "Business, Trade & Economic Development",
            "Technology, Economic Development, & Veterans", "Business, Financial Services, Gaming & Trade"}, NO_SUBJECTS,
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


# Governors and the day each took office (the Wednesday after the second Monday of January after the election).
GOVERNORS = [("Inslee", "2013-01-16"), ("Ferguson", "2025-01-15")]
GOV_SINCE = GOVERNORS[-1][1]


def governor_on(day):
    who = GOVERNORS[0][0]
    for name, start in GOVERNORS:
        if day >= start:
            who = name
    return who


TRENDS = []
WORDING = []
