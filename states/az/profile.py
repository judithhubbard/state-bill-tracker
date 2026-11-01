"""Arizona: the settings and wording that are particular to this state.

build_data.py reads these as P.<name>, with the same names as states/ny/profile.py.
"""
import os, re

DATA = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "az"))
SITE_DIR = "az"

STATE_NAME = "Arizona"
SITE_NAME = "Arizona Bill Tracker"
LEGISLATURE = "Arizona Legislature"
TIMEZONE = "America/Phoenix"
PUBLIC_URL = "https://statebilltracker.org/az/"
SITE_URL = os.environ.get("SITE_URL", PUBLIC_URL)

# A regular session each year, from the second Monday of January until it adjourns sine die (spring or early summer);
# bills don't carry over from one regular session to the next. Special sessions aren't shown. Bills come from Open States
# (the owner's decision, 2026-10-31; see the az-open-states memory).
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
# Who decides which bills reach each house's floor: the Speaker and the Senate President.
LEADERS = {"S": ("Warren Petersen", "President of the Senate", "him"),
           "H": ("Steve Montenegro", "Speaker of the House", "him")}


def delegation(session):
    return {}


# Topic: (label, committee names (unused; see COMMITTEE_TOPICS), official subjects (none), title words).
NO_SUBJECTS = re.compile(r"(?!)")
TOPICS = {
    "env": ("Environment & energy", set(), NO_SUBJECTS, r"\b(groundwater|state waters|well drilling|irrigation|active management area|greenhouse|ama\b|corporation commission|environment\w*|climate|emission\w*|renewable|solar|pollut\w*|water|energy|utilit\w*)\b"),
    "local": ("Local government", set(), NO_SUBJECTS, r"\b(municipal\w*|county|counties|city of|cities|towns|local government)\b"),
    "tax": ("Taxes", set(), NO_SUBJECTS, r"\b(tpt|transaction privilege|property exemption|appropriations?|tax\w*|revenue|homestead exemption)\b"),
    "safety": ("Public safety & courts", set(), NO_SUBJECTS, r"\b(immigration|law enforcement|victims?|incarceration|silent witness|crim\w*|firearm\w*|police|court\w*|sentenc\w*|prison\w*|jail\w*|felony|misdemeanor|correction\w*|sheriff\w*)\b"),
    "human": ("Human services", set(), NO_SUBJECTS, r"\b(dcs\b|snap\b|tanf\b|child neglect|guardianship|juveniles?|parenting time|national guard|child care|foster|veteran\w*|senior\w*|aging|disabilit\w*|homeless\w*)\b"),
    "health": ("Health & mental health", set(), NO_SUBJECTS, r"\b(ahcccs|altcs|abortion|contracept\w*|dental|prescription|medical|pharmac\w*|health|medical|medicaid|hospital\w*|mental|pharmac\w*|nurs\w*|physician\w*)\b"),
    "edu": ("Education", set(), NO_SUBJECTS, r"\b(esas?\b|empowerment scholarship|charter|school\w*|student\w*|teacher\w*|education|college\w*|universit\w*)\b"),
    "transp": ("Transportation", set(), NO_SUBJECTS, r"\b(vehicle\w*|highway\w*|road\w*|traffic|transit|driver\w*|motor)\b"),
    "labor": ("Labor & public employees", set(), NO_SUBJECTS, r"\b(wage\w*|employ\w*|worker\w*|labor|pension\w*|retirement)\b"),
    "housing": ("Housing", set(), NO_SUBJECTS, r"\b(homeowners?'? associations?|condominiums?|vacation rentals?|short-term rentals?|accessory dwelling|real estate|land division|planning|housing|landlord\w*|tenant\w*|rent|eviction\w*)\b"),
    "ag": ("Agriculture & natural resources", set(), NO_SUBJECTS, r"\b(agricultur\w*|farm\w*|livestock|fish\w*|wildlife|hunting|timber)\b"),
    "gov": ("Elections & state government", set(), NO_SUBJECTS, r"\b(campaign finance|early voting|voting centers?|auditor general|continuation|governor|asrs|eorp|election\w*|voter\w*|ballot\w*|state agenc\w*|ethics|open records)\b"),
    # Concurrent resolutions proposing constitutional amendments (tagged by convert.py, not by words).
    "const": ("Constitutional amendments", set(), NO_SUBJECTS, ""),
    "biz": ("Business & consumers", set(), NO_SUBJECTS, r"\b(marijuana|pesticides|liquified petroleum|apprenticeship|consumer\w*|business\w*|insurance|bank\w*|licens\w*)\b"),
}
# Committee name words -> topic.
COMMITTEE_TOPICS = {"Natural Resources": "env", "Energy": "env", "Environment": "env", "Water": "env", "Land": "env",
                    "Finance": "tax", "Ways and Means": "tax", "Judiciary": "safety", "Public Safety": "safety",
                    "Military Affairs": "safety", "Health": "health", "Human Services": "human", "Education": "edu",
                    "Transportation": "transp", "Technology": "biz", "Commerce": "biz", "Regulatory": "biz",
                    "Government": "gov", "Elections": "gov", "Federalism": "gov", "Agriculture": "ag", "Appropriations": "tax",
                    "Housing": "housing"}
TOPIC_WORDS = {k: re.compile(v[3], re.I) for k, v in TOPICS.items() if v[3]}

COUNTIES = []
DISTRICTS_PATH = os.path.join(DATA, "district_counties.json")
TOWNS_PATH = os.path.join(DATA, "district_towns.json")

_NAMING = re.compile(r"\b(?:dedicat\w*|designat\w*|nam\w*)\b.*\b(?:bridge|interchange|highway|route|road|memorial|building|park)\b", re.I)
NARROW_KINDS = ["", "person", "org", "naming"]


def narrow_kind(title):
    return "naming" if _NAMING.search(title) else ""


# Governors and the day each took office (the first Monday of January after the election).
GOVERNORS = [("Ducey", "2015-01-05"), ("Hobbs", "2023-01-02")]
GOV_SINCE = GOVERNORS[-1][1]


def governor_on(day):
    who = GOVERNORS[0][0]
    for name, start in GOVERNORS:
        if day >= start:
            who = name
    return who


TRENDS = []
WORDING = []
