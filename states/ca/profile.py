"""California: the settings and wording that are particular to this state.

build_data.py reads these as P.<name>, with the same names as states/ny/profile.py.
"""
import os, re

# Where this state's data files are (from states/ca/fetch.py), and its folder under site/.
DATA = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "ca"))
SITE_DIR = "ca"

# Names in page titles and the header line.
STATE_NAME = "California"
SITE_NAME = "California Bill Tracker"
LEGISLATURE = "California State Legislature"
TIMEZONE = "America/Los_Angeles"
PUBLIC_URL = "https://statebilltracker.org/ca/"
SITE_URL = os.environ.get("SITE_URL", PUBLIC_URL)

# Sessions run two years, starting in odd years (the first day is the first Monday of December before, when
# members are sworn in and bills can be introduced). Bills keep their numbers through both houses.
YEARS = 2
LOWER = "A"
LOWER_NAME = "Assembly"
TITLES = {"S": "Sen.", "A": "Asm."}


def session_of(year):
    """The session running in a calendar year."""
    return year if year % 2 else year - 1


def session_label(session):
    """How a session is written: 2025–26."""
    return f"{session}–{str(session + 1)[2:]}"


# Visitor counts: none until the site is public.
CF_ANALYTICS_TOKEN = ""
GOATCOUNTER_CODE = ""

DELEGATION_NAMES = set()
# Who decides which bills reach each house's floor: name, title, and the pronoun the site uses for them.
# The Senate's leader is the President pro Tempore, who chairs its Rules Committee.
LEADERS = {"S": ("Monique Limón", "Senate President pro Tempore", "her"),
           "A": ("Robert Rivas", "Assembly Speaker", "him")}


def delegation(session):
    return {}


# Topic: (label, committees, official subjects (none in California's files), title words). Committees are named
# as in LOCATION_CODE_TBL without the house ("Natural Resources"); the keys are shared with other states.
NO_SUBJECTS = re.compile(r"(?!)")
TOPICS = {
    "env": ("Environment & energy",
            {"Natural Resources", "Environmental Safety and Toxic Materials", "Utilities and Energy", "Water, Parks and Wildlife", "Environmental Quality", "Natural Resources and Water", "Energy, Utilities and Communications", "Petroleum and Gasoline Supply", "Fuel Supply and Price Spikes"}, NO_SUBJECTS,
            r"\b(climate|greenhouse|emission\w*|renewable|solar|wind energy|pollut\w*|wetland|watershed|"
            r"drinking water|pesticide|plastic|recycl\w*|pfas|stormwater|wastewater|forest\w*|wildlife|energy|"
            r"wildfire\w*|coastal|air quality|hazardous waste)\b"),
    "local": ("Local government",
            {"Local Government"}, NO_SUBJECTS,
              r"\b(city|cities|county|counties|special district\w*|zoning|local government|local agenc\w*)\b"),
    "tax": ("Taxes & assessment",
            {"Revenue and Taxation", "Governance and Finance"}, NO_SUBJECTS, r"\b(tax|taxes|taxation|property tax\w*)\b"),
    "safety": ("Public safety & courts",
            {"Public Safety", "Emergency Management"}, NO_SUBJECTS,
               r"\b(crim\w*|firearm\w*|police|peace officer\w*|court\w*|sentenc\w*|prison\w*|jail\w*|felony|misdemeanor)\b"),
    "human": ("Human services",
            {"Human Services", "Aging and Long Term Care", "Military and Veterans Affairs"}, NO_SUBJECTS,
              r"\b(child care|foster care|calfresh|calworks|social services|veterans?|seniors?|aging|disabilit\w*|homeless\w*)\b"),
    "health": ("Health & mental health",
            {"Health"}, NO_SUBJECTS,
               r"\b(health|medical|medi-cal|hospital\w*|mental|behavioral|pharmac\w*|nurs\w*|physician\w*)\b"),
    "edu": ("Education",
            {"Education", "Higher Education"}, NO_SUBJECTS,
            r"\b(school\w*|pupil\w*|student\w*|teacher\w*|education|college\w*|universit\w*)\b"),
    "transp": ("Transportation & highways",
            {"Transportation", "Transportation and Infrastructure Development"}, NO_SUBJECTS,
               r"\b(vehicle\w*|highway\w*|road\w*|traffic|transit|driver\w*|toll\w*|rail)\b"),
    "labor": ("Labor & public employees",
            {"Labor and Employment", "Public Employment and Retirement", "Labor, Public Employment and Retirement", "Labor and Industrial Relations"}, NO_SUBJECTS,
              r"\b(wage|wages|employ\w*|worker\w*|labor|retirement|collective bargaining|pers|strs)\b"),
    "housing": ("Housing",
            {"Housing and Community Development", "Housing"}, NO_SUBJECTS, r"\b(housing|landlord\w*|tenant\w*|rent|eviction\w*|mortgage\w*)\b"),
    "ag": ("Agriculture",
            {"Agriculture"}, NO_SUBJECTS, r"\b(agricultur\w*|farm\w*|livestock|animal\w*|food)\b"),
    "gov": ("Elections & state government",
            {"Elections", "Elections and Constitutional Amendments", "Governmental Organization", "Accountability and Administrative Review"}, NO_SUBJECTS,
            r"\b(election\w*|voter\w*|ballot\w*|campaign\w*|state agenc\w*|public records)\b"),
    "biz": ("Business & consumers",
            {"Banking and Finance", "Business and Professions", "Privacy and Consumer Protection", "Insurance", "Insurance, Banking and Financial Institutions", "Business, Professions and Economic Development", "Privacy, Digital Technologies, and Consumer Protection", "Banking and Financial Institutions", "Economic Development, Growth, and Household Impact"}, NO_SUBJECTS,
            r"\b(consumer\w*|business\w*|insurance|bank\w*|licens\w*|corporation\w*|privacy|data)\b"),
}
TOPIC_WORDS = {k: re.compile(v[3], re.I) for k, v in TOPICS.items() if v[3]}

COUNTIES = []
DISTRICTS_PATH = os.path.join(DATA, "district_counties.json")
TOWNS_PATH = os.path.join(DATA, "district_towns.json")

_NAMING = re.compile(r"\b(?:designat\w*|nam\w*)\b.*\b(?:bridge|interchange|highway|route|memorial|building|park)\b", re.I)
NARROW_KINDS = ["", "person", "org", "naming"]


def narrow_kind(title):
    return "naming" if _NAMING.search(title) else ""


# Governors and the day each took office. A new governor takes office on the first Monday after January 1
# following the election (next: January 4, 2027).
GOVERNORS = [("Brown", "2011-01-03"), ("Newsom", "2019-01-07")]
GOV_SINCE = GOVERNORS[-1][1]


def governor_on(day):
    who = GOVERNORS[0][0]
    for name, start in GOVERNORS:
        if day >= start:
            who = name
    return who


TRENDS = []
WORDING = []
