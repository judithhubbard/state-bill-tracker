"""Virginia: the settings and wording that are particular to this state.

build_data.py reads these as P.<name>, with the same names as states/ny/profile.py.
"""
import os, re

# Where this state's data files are (from states/va/fetch.py), and its folder under site/.
DATA = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "va"))
SITE_DIR = "va"

# Names in page titles and the header line.
STATE_NAME = "Virginia"
SITE_NAME = "Virginia Bill Tracker"
LEGISLATURE = "Virginia General Assembly"
TIMEZONE = "America/New_York"
PUBLIC_URL = "https://statebilltracker.org/va/"
SITE_URL = os.environ.get("SITE_URL", PUBLIC_URL)

# Sessions run one year (60 days in even years, 46 in odd ones, plus the April reconvened session), and
# bill numbers start over each year. The lower house is the House of Delegates ("H"); its members are delegates.
YEARS = 1
LOWER = "H"
LOWER_NAME = "House"
TITLES = {"S": "Sen.", "H": "Del."}


def session_of(year):
    return year


def session_label(session):
    return str(session)


# The day each regular session adjourned (or is scheduled to), for the governor's deadline: 7 days for a bill
# presented while the session still has more than 7 days to run, else 30 days after adjournment.
ADJOURNED = {2024: "2024-03-09", 2025: "2025-02-22", 2026: "2026-03-14", 2027: "2027-02-27"}

# Visitor counts: none until the site is public.
CF_ANALYTICS_TOKEN = ""
GOATCOUNTER_CODE = ""

DELEGATION_NAMES = set()
# Who decides which bills reach each house's floor: name, title, and the pronoun the site uses for them.
# In the Senate that's the majority leader (the president is the lieutenant governor). Check each January.
LEADERS = {"S": ("Scott A. Surovell", "Senate Majority Leader", "him"),
           "H": ("Don Scott", "Speaker of the House", "him")}


def delegation(session):
    return {}


# Topic: (label, committees, official subjects (Virginia's files have none), title words). Committees are
# named as in Committees.csv; the keys are shared with other states.
NO_SUBJECTS = re.compile(r"(?!)")
TOPICS = {
    "env": ("Environment & energy",
            {"Agriculture, Chesapeake and Natural Resources", "Agriculture, Conservation and Natural Resources"},
            NO_SUBJECTS,
            r"\b(climate|greenhouse|emission|renewable|solar|wind energy|pollut\w*|wetland|watershed|chesapeake|"
            r"drinking water|pesticide|plastic|recycl\w*|pfas|stormwater|wastewater|forest|wildlife|energy)\b"),
    "local": ("Local government", {"Counties, Cities and Towns", "Local Government"}, NO_SUBJECTS,
              r"\b(locality|localities|county|counties|city council|town council|zoning|local government)\b"),
    "tax": ("Taxes & assessment", {"Finance"}, NO_SUBJECTS, r"\b(tax|taxes|taxation|assessment)\b"),
    "safety": ("Public safety & courts", {"Courts of Justice", "Public Safety", "Rehabilitation and Social Services"},
               NO_SUBJECTS, r"\b(crim\w*|firearm\w*|police|law-enforcement|court|sentenc\w*|prison|jail|felony|misdemeanor)\b"),
    "human": ("Human services", {"Rehabilitation and Social Services"}, NO_SUBJECTS,
              r"\b(child care|foster care|social services|veterans?|senior|aging|disabilit\w*)\b"),
    "health": ("Health & mental health", {"Health and Human Services", "Education and Health"}, NO_SUBJECTS,
               r"\b(health|medical|medicaid|hospital|mental|behavioral|pharmac\w*|nurs\w*|physician)\b"),
    "edu": ("Education", {"Education", "Education and Health"}, NO_SUBJECTS,
            r"\b(school|schools|student\w*|teacher\w*|education|college|universit\w*)\b"),
    "transp": ("Transportation & highways", {"Transportation"}, NO_SUBJECTS,
               r"\b(motor vehicle|highway|road|traffic|transit|driver\w*|toll)\b"),
    "labor": ("Labor & public employees", {"Labor and Commerce", "Commerce and Labor"}, NO_SUBJECTS,
              r"\b(wage|wages|employ\w*|worker\w*|labor|retirement system|collective bargaining)\b"),
    "housing": ("Housing", set(), NO_SUBJECTS, r"\b(housing|landlord|tenant\w*|rent|eviction\w*|mortgage)\b"),
    "ag": ("Agriculture", {"Agriculture, Chesapeake and Natural Resources", "Agriculture, Conservation and Natural Resources"},
           NO_SUBJECTS, r"\b(agricultur\w*|farm\w*|livestock|animal\w*|food)\b"),
    "gov": ("Elections & state government", {"Privileges and Elections", "Rules", "General Laws", "General Laws and Technology"},
            NO_SUBJECTS, r"\b(election\w*|voter\w*|ballot\w*|campaign finance|state agenc\w*|freedom of information)\b"),
    "biz": ("Business & consumers", {"Labor and Commerce", "Commerce and Labor", "Communications, Technology and Innovation"},
            NO_SUBJECTS, r"\b(consumer\w*|business\w*|insurance|bank\w*|license\w*|corporation\w*|commerce)\b"),
    "const": ("Constitutional amendments", set(), NO_SUBJECTS, r"\bconstitutional amendment\b"),
}
TOPIC_WORDS = {k: re.compile(v[3], re.I) for k, v in TOPICS.items() if v[3]}

# Places come later ("Where you live" by locality).
COUNTIES = []
DISTRICTS_PATH = os.path.join(DATA, "district_counties.json")
# Each locality's Senate and House districts (states/va/towns.py): "Where you live" picks a county or city.
TOWNS_PATH = os.path.join(DATA, "district_towns.json")

_NAMING = re.compile(r"\b(?:designat\w*|nam\w*)\b.*\b(?:bridge|interchange|highway|route|memorial|building|park)\b", re.I)
NARROW_KINDS = ["", "person", "org", "naming"]


def narrow_kind(title):
    return "naming" if _NAMING.search(title) else ""


# Governors and the day each took office.
GOVERNORS = [("Northam", "2018-01-13"), ("Youngkin", "2022-01-15"), ("Spanberger", "2026-01-17")]
GOV_SINCE = GOVERNORS[-1][1]


def governor_on(day):
    who = GOVERNORS[0][0]
    for name, start in GOVERNORS:
        if day >= start:
            who = name
    return who


TRENDS = []
WORDING = []
