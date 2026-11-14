"""New Mexico: the settings and wording that are particular to this state.

build_data.py reads these as P.<name>, with the same names as states/ny/profile.py.
"""
import os, re

DATA = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "nm"))
SITE_DIR = "nm"

STATE_NAME = "New Mexico"
SITE_NAME = "New Mexico Bill Tracker"
LEGISLATURE = "New Mexico Legislature"
TIMEZONE = "America/Denver"
PUBLIC_URL = "https://statebilltracker.org/nm/"
SITE_URL = os.environ.get("SITE_URL", PUBLIC_URL)

# A regular session a year from the third Tuesday of January (Constitution, Art. IV, sec. 5): 60 days in odd years, 30
# in even years, when only the budget, bills the governor puts on the call and vetoed bills of the year before may be
# taken up. Bills die when the session ends. A page a year; special sessions are left out.
YEARS = 1
LOWER = "H"
LOWER_NAME = "House"
TITLES = {"S": "Sen.", "H": "Rep."}


def session_of(year):
    return year


def session_kind(session):
    """Sessions alternate: a long session in odd years (60 days), a short one in even years (30 days, for the budget and
    what the governor calls). Statistics compare a session only with past sessions of the same kind."""
    return "long" if session % 2 else "short"


def session_label(session):
    return str(session)


CF_ANALYTICS_TOKEN = ""
GOATCOUNTER_CODE = ""

DELEGATION_NAMES = set()
# Who decides which bills reach each house's floor: the Speaker (and the House Rules and Order of Business Committee) and,
# in the Senate, the President Pro Tempore and the Committees' Committee (the Lieutenant Governor presides over the Senate
# but isn't a senator). From the Legislature's leadership page, 2026-11-13; the Legislature elected in November 2026
# chooses its own in January 2027: update this then.
LEADERS = {"S": ("Mimi Stewart", "President Pro Tempore of the Senate", "her"),
           "H": ("Javier Martínez", "Speaker of the House", "him")}


def delegation(session):
    return {}


# Topic: (label, committees (unused; see COMMITTEE_TOPICS), official subjects (unused), words in the title and the
# fiscal impact report's synopsis, used when the committees give no topic).
NO_SUBJECTS = re.compile(r"(?!)")
TOPICS = {
    "env": ("Environment & energy", set(), NO_SUBJECTS, r"\b(environment\w*|pollut\w*|energy|utilit\w*|solar|nuclear|electric\w*|emission\w*|climate|oil and gas|methane|solid waste|recycl\w*)\b"),
    "local": ("Local government", set(), NO_SUBJECTS, r"\b(municipal\w*|county|counties|cities|city|towns?|villages?|annex\w*|land grants?)\b"),
    "tax": ("Taxes", set(), NO_SUBJECTS, r"\b(tax\w*|gross receipts|revenue)\b"),
    "safety": ("Public safety & courts", set(), NO_SUBJECTS, r"\b(crim\w*|firearm\w*|police|law enforcement|courts?|judge\w*|sentenc\w*|prison\w*|jail\w*|felon\w*|corrections|parole|sheriff\w*|fentanyl|dwi)\b"),
    "human": ("Human services", set(), NO_SUBJECTS, r"\b(child care|early childhood|foster|adoption\w*|veteran\w*|senior\w*|elderly|aging|disabilit\w*|homeless\w*|public assistance)\b"),
    "health": ("Health & mental health", set(), NO_SUBJECTS, r"\b(health|medical|medicaid|hospital\w*|mental|behavioral|pharmac\w*|nurs\w*|physician\w*|abortion|cannabis)\b"),
    "edu": ("Education", set(), NO_SUBJECTS, r"\b(school\w*|student\w*|teacher\w*|education\w*|college\w*|universit\w*)\b"),
    "transp": ("Transportation", set(), NO_SUBJECTS, r"\b(vehicle\w*|highway\w*|roads?|traffic|driver\w*|transportation|airport\w*|motor)\b"),
    "labor": ("Labor & public employees", set(), NO_SUBJECTS, r"\b(wage\w*|employee\w*|worker\w*|labor|pension\w*|retire\w*|unemployment)\b"),
    "housing": ("Housing", set(), NO_SUBJECTS, r"\b(housing|landlord\w*|tenant\w*|eviction\w*|homeowner\w*|mobile home\w*)\b"),
    "ag": ("Agriculture & natural resources", set(), NO_SUBJECTS, r"\b(agricultur\w*|farm\w*|livestock|acequia\w*|water rights?|wildlife|hunting|fishing|forest\w*|ranch\w*)\b"),
    "gov": ("Elections & state government", set(), NO_SUBJECTS, r"\b(election\w*|voter\w*|voting|ballot\w*|campaign\w*|ethics|open meetings|public records|legislat\w*)\b"),
    "biz": ("Business & consumers", set(), NO_SUBJECTS, r"\b(consumer\w*|business\w*|insurance|bank\w*|licens\w*|alcohol\w*|liquor|gaming|racing)\b"),
    "const": ("Constitutional amendments", set(), NO_SUBJECTS, ""),
}
# Standing committees (as convert.comm_name() names them, both houses) -> topic, for committees with one main subject.
# Appropriations and Finance, Finance, Judiciary, Rules, the Committees' Committee, Indian, Rural and Cultural Affairs and
# Rural Development, Land Grants and Cultural Affairs give none of their own.
COMMITTEE_TOPICS = {
    "Agriculture, Acequias and Water Resources": "ag", "Commerce and Economic Development": "biz",
    "Consumer and Public Affairs": "biz", "Education": "edu", "Energy, Environment and Natural Resources": "env",
    "Government, Elections and Indian Affairs": "gov", "Health and Human Services": "health",
    "Labor, Veterans' and Military Affairs": "labor", "Transportation, Public Works and Capital Improvements": "transp",
    "Taxation and Revenue": "tax", "Conservation": "env", "Health and Public Affairs": "health",
    "Tax, Business and Transportation": "tax",
}
TOPIC_WORDS = {k: re.compile(v[3], re.I) for k, v in TOPICS.items() if v[3]}

COUNTIES = []
DISTRICTS_PATH = os.path.join(DATA, "district_counties.json")
TOWNS_PATH = os.path.join(DATA, "district_towns.json")

_NAMING = re.compile(r"\b(?:designat\w*|nam\w*|renam\w*)\b.*\b(?:bridge|interchange|highway|route|memorial|building|park)\b|\bmemorial (?:highway|bridge|interchange)\b", re.I)
NARROW_KINDS = ["", "person", "org", "naming"]


def narrow_kind(title):
    return "naming" if _NAMING.search(title) else ""


# Governors and the day each took office. Michelle Lujan Grisham's second term ends January 1, 2027 (term-limited): add the
# next governor here, and in states/legislatures.json.
GOVERNORS = [("Martinez", "2011-01-01"), ("Lujan Grisham", "2019-01-01")]
GOV_SINCE = GOVERNORS[-1][1]


def governor_on(day):
    who = GOVERNORS[0][0]
    for name, start in GOVERNORS:
        if day >= start:
            who = name
    return who


TRENDS = []
WORDING = []
