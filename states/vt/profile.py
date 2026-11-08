"""Vermont: the settings and wording that are particular to this state.

build_data.py reads these as P.<name>, with the same names as states/ny/profile.py.
"""
import os, re

DATA = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "vt"))
SITE_DIR = "vt"

STATE_NAME = "Vermont"
SITE_NAME = "Vermont Bill Tracker"
LEGISLATURE = "Vermont General Assembly"
TIMEZONE = "America/New_York"
PUBLIC_URL = "https://statebilltracker.org/vt/"
SITE_URL = os.environ.get("SITE_URL", PUBLIC_URL)

# A General Assembly is elected every two years and sits for a biennium from the odd year (2025-26): bills are numbered
# once for the biennium (H.1 to about H.950, S.1 to about S.330), stay alive through both years' sessions (January to
# May or June) and die when the biennium ends; Acts are numbered through the biennium too (Act 1 of 2025 ... Act 179 of
# 2026). LegiScan keeps a biennium as one session. So a page is a biennium (decided 2026-11-08).
YEARS = 2
LOWER = "H"
LOWER_NAME = "House"
TITLES = {"S": "Sen.", "H": "Rep."}


def session_of(year):
    return year if year % 2 else year - 1


def session_label(session):
    return f"{session}–{str(session + 1)[2:]}"


CF_ANALYTICS_TOKEN = ""
GOATCOUNTER_CODE = ""

DELEGATION_NAMES = set()
# Who decides which bills reach each house's floor. In the House, the Speaker (Jill Krowinski, 2021-); in the Senate, the
# President pro tempore (Philip Baruth, 2023-), who chairs the Committee on Committees and leads the majority; the
# Lieutenant Governor presides over the Senate but isn't a senator. The General Assembly elected in November 2026 chooses
# its leaders in January 2027: change these then.
LEADERS = {"S": ("Philip Baruth", "President pro tempore of the Senate", "him"),
           "H": ("Jill Krowinski", "Speaker of the House", "her")}


def delegation(session):
    return {}


# Topic: (label, committees (unused; see COMMITTEE_TOPICS), official subjects (unused), title words).
NO_SUBJECTS = re.compile(r"(?!)")
TOPICS = {
    "env": ("Environment & energy", set(), NO_SUBJECTS, r"\b(environment\w*|climate|emission\w*|renewable|solar|pollut\w*|energy|utilit\w*|electric\w*|solid waste|landfill\w*|water quality|stormwater|wetland\w*|flood\w*|PFAS|Act 250|land use|recycl\w*|weatheriz\w*|greenhouse)\b"),
    "local": ("Local government", set(), NO_SUBJECTS, r"\b(municipal\w*|charter|cities|city of|town of|village of|towns|selectboard|local government\w*|downtown\w*)\b"),
    "tax": ("Taxes", set(), NO_SUBJECTS, r"\b(tax\w*|revenue|property valuation|grand list)\b"),
    "safety": ("Public safety & courts", set(), NO_SUBJECTS, r"\b(crim\w*|firearm\w*|gun\w*|weapon\w*|police|law enforcement|court\w*|sentenc\w*|prison\w*|correction\w*|felony|misdemeanor|expunge\w*|offense\w*|judicial|judiciary|bail|sheriff\w*)\b"),
    "human": ("Human services", set(), NO_SUBJECTS, r"\b(child care|foster|veteran\w*|older Vermonters|elder\w*|disabilit\w*|homeless\w*|Reach Up|general assistance|human services|child welfare)\b"),
    "health": ("Health & mental health", set(), NO_SUBJECTS, r"\b(health|medical|medicaid|Dr\. Dynasaur|hospital\w*|mental|pharmac\w*|nurs\w*|physician\w*|prescription\w*|opioid\w*|substance use|cannabis|tobacco)\b"),
    "edu": ("Education", set(), NO_SUBJECTS, r"\b(school\w*|student\w*|teacher\w*|education\w*|educator\w*|college\w*|universit\w*|tuition|prekindergarten)\b"),
    "transp": ("Transportation", set(), NO_SUBJECTS, r"\b(vehicle\w*|highway\w*|road\w*|traffic|transit|driver\w*|driving|motor|transportation|rail\w*|aviation)\b"),
    "labor": ("Labor & public employees", set(), NO_SUBJECTS, r"\b(wage\w*|employ\w*|worker\w*|labor|pension\w*|retirement|unemployment|collective bargaining)\b"),
    "housing": ("Housing", set(), NO_SUBJECTS, r"\b(housing|landlord\w*|tenant\w*|rent\w*|eviction\w*|zoning|mobile home\w*|homeowner\w*)\b"),
    "ag": ("Agriculture & natural resources", set(), NO_SUBJECTS, r"\b(agricultur\w*|farm\w*|livestock|dairy|maple|fish\w*|wildlife|hunting|trapping|forest\w*|timber|pesticide\w*|neonicotinoid\w*)\b"),
    "gov": ("Elections & state government", set(), NO_SUBJECTS, r"\b(election\w*|voter\w*|voting|ballot\w*|state agenc\w*|ethics|public records|campaign\w*|open meeting\w*|legislat\w*|Secretary of State|Auditor)\b"),
    "biz": ("Business & consumers", set(), NO_SUBJECTS, r"\b(consumer\w*|business\w*|insurance|insurer\w*|bank\w*|licens\w*|corporat\w*|economic development|alcohol\w*|liquor|beer|wine|spirits|gaming|sports wagering|data broker\w*|privacy)\b"),
    "const": ("Constitutional amendments", set(), NO_SUBJECTS, ""),
}
TOPIC_WORDS = {k: re.compile(v[3], re.I) for k, v in TOPICS.items() if v[3]}

# Committee names (as the history writes them) -> topic, for committees with one subject. Appropriations, Ways and
# Means, Finance, Rules, Judiciary (also civil law) and the Government Operations committees give none, except where
# the subject is plain.
COMMITTEE_TOPICS = {
    # House
    "Agriculture, Food Resiliency, and Forestry": "ag", "Commerce and Economic Development": "biz",
    "Corrections and Institutions": "safety", "Education": "edu", "Environment and Energy": "env", "Environment": "env",
    "Energy and Digital Infrastructure": "env", "General and Housing": "housing", "Health Care": "health",
    "Human Services": "human", "Transportation": "transp", "Ways and Means": "tax", "Judiciary": "safety",
    "Government Operations and Military Affairs": "gov",
    # Senate
    "Agriculture": "ag", "Economic Development, Housing and General Affairs": "biz", "Finance": "tax",
    "Health and Welfare": "health", "Institutions": "safety", "Natural Resources and Energy": "env",
    "Government Operations": "gov",
}

COUNTIES = []
DISTRICTS_PATH = os.path.join(DATA, "district_counties.json")
TOWNS_PATH = os.path.join(DATA, "district_towns.json")
# District names ({"S": {"4": "Chittenden Central"}, "H": {"37": "Chittenden-17"}}): Vermont's districts have names,
# not numbers; seat ids number them alphabetically (states/vt/towns.py, which writes this file).
DISTRICT_NAMES_PATH = os.path.join(DATA, "district_names.json")

_NAMING = re.compile(r"\b(?:designat\w*|nam\w*)\b.*\b(?:bridge|interchange|highway|route|memorial|building|park|road)\b|\bmemorial (?:highway|bridge|interchange)\b", re.I)
_PLACE = re.compile(r"\bcharter\b|\bmerger of the (?:City|Town|Village)|\bunified union school district of\b", re.I)
NARROW_KINDS = ["", "place", "person", "org", "naming"]


def narrow_kind(title):
    return "place" if _PLACE.search(title) else "naming" if _NAMING.search(title) else ""


# Governors and the day each took office (Vermont's governors serve two-year terms; Phil Scott since January 2017).
# If the governor elected in November 2026 is someone new, add them here (and in states/legislatures.json) in January 2027.
GOVERNORS = [("Shumlin", "2011-01-06"), ("Scott", "2017-01-05")]
GOV_SINCE = GOVERNORS[-1][1]


def governor_on(day):
    who = GOVERNORS[0][0]
    for name, start in GOVERNORS:
        if day >= start:
            who = name
    return who


TRENDS = []
WORDING = []
