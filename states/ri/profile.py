"""Rhode Island: the settings and wording that are particular to this state.

build_data.py reads these as P.<name>, with the same names as states/ny/profile.py.
"""
import os, re

DATA = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "ri"))
SITE_DIR = "ri"

STATE_NAME = "Rhode Island"
SITE_NAME = "Rhode Island Bill Tracker"
LEGISLATURE = "Rhode Island General Assembly"
TIMEZONE = "America/New_York"
PUBLIC_URL = "https://statebilltracker.org/ri/"
SITE_URL = os.environ.get("SITE_URL", PUBLIC_URL)

# One session a year (the "January session"), from the first Tuesday of January to June. Bills don't carry over: a bill
# that hasn't become law by the session's end has to be introduced again the next year. Most bills have a companion in
# the other house with the same text; convert.py shows the two as one bill.
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
# Who decides which bills reach each house's floor: the Speaker of the House (Chris Blazejewski since May 7, 2026, when
# Joe Shekarchi stepped down as Speaker) and the President of the Senate (Val Lawson since April 2025, after Dominick
# Ruggerio's death). There's no Rules or Calendar committee in between: the leaders and the committee chairs decide which
# bills are heard, held or sent to the floor. Names as Open States writes them (contacts.py matches them). The General
# Assembly elected in November 2026 chooses its leaders in January 2027: check them then.
LEADERS = {"S": ("Val Lawson", "President of the Senate", "her"),
           "H": ("Chris Blazejewski", "Speaker of the House", "him")}


def delegation(session):
    return {}


# Topic: (label, committees (unused; see COMMITTEE_TOPICS), official subjects (unused; see TITLE_TOPICS), title words).
NO_SUBJECTS = re.compile(r"(?!)")
TOPICS = {
    "env": ("Environment & energy", set(), NO_SUBJECTS, r"\b(environment\w*|climate|emission\w*|renewable|solar|offshore wind|pollut\w*|energy|electric\w*|solid waste|recycl\w*|plastic\w*)\b"),
    "local": ("Local government", set(), NO_SUBJECTS, r"\b(municipal\w*|town council|city council|cities and towns|local government\w*|fire district\w*|town of|city of|charter)\b"),
    "tax": ("Taxes", set(), NO_SUBJECTS, r"\b(tax\w*|revenue)\b"),
    "safety": ("Public safety & courts", set(), NO_SUBJECTS, r"\b(crim\w*|firearm\w*|handgun\w*|police|court\w*|sentenc\w*|prison\w*|felony|misdemeanor|correction\w*|expunge\w*|offense\w*)\b"),
    "human": ("Human services", set(), NO_SUBJECTS, r"\b(child care|foster|veteran\w*|senior\w*|elderly|disabilit\w*|homeless\w*|public assistance)\b"),
    "health": ("Health & mental health", set(), NO_SUBJECTS, r"\b(health|medical|medicaid|hospital\w*|mental|pharmac\w*|nurs\w*|physician\w*|behavioral)\b"),
    "edu": ("Education", set(), NO_SUBJECTS, r"\b(school\w*|student\w*|teacher\w*|education|college\w*|universit\w*|tuition)\b"),
    "transp": ("Transportation", set(), NO_SUBJECTS, r"\b(vehicle\w*|highway\w*|road\w*|traffic|transit|driver\w*|driving|motor)\b"),
    "labor": ("Labor & public employees", set(), NO_SUBJECTS, r"\b(wage\w*|employ\w*|worker\w*|labor|pension\w*|retirement)\b"),
    "housing": ("Housing", set(), NO_SUBJECTS, r"\b(housing|landlord\w*|tenant\w*|rent|rental|eviction\w*|zoning)\b"),
    "ag": ("Agriculture & natural resources", set(), NO_SUBJECTS, r"\b(agricultur\w*|farm\w*|livestock|fish\w*|shellfish|wildlife|hunting|forest\w*)\b"),
    "gov": ("Elections & state government", set(), NO_SUBJECTS, r"\b(election\w*|voter\w*|voting|ballot\w*|state agenc\w*|ethics|public records|campaign\w*)\b"),
    "biz": ("Business & consumers", set(), NO_SUBJECTS, r"\b(consumer\w*|business\w*|insurance|bank\w*|licens\w*|corporat\w*|economic development|alcohol\w*|beverage\w*|gaming|cannabis)\b"),
    "const": ("Constitutional amendments", set(), NO_SUBJECTS, ""),
}
TOPIC_WORDS = {k: re.compile(v[3], re.I) for k, v in TOPICS.items() if v[3]}

# Committee names (as convert.py writes them) -> topic, for committees with one subject. Finance and Judiciary hear
# bills on many subjects and give none.
COMMITTEE_TOPICS = {
    "Corporations": "biz", "Commerce": "biz", "Small Business": "biz",
    "Municipal Government and Housing": "housing", "Housing and Municipal Government": "housing",
    "Health and Human Services": "health", "Education": "edu",
    "State Government and Elections": "gov", "Rules, Government Ethics and Oversight": "gov", "Oversight": "gov",
    "Labor": "labor", "Labor and Gaming": "labor",
    "Environment and Natural Resources": "env", "Environment and Agriculture": "env",
    "Veterans Affairs": "human",
}
# The first part of a bill's heading, the title of the General Laws it amends ("COMMERCIAL LAW -- GENERAL REGULATORY
# PROVISIONS -- ...") -> topic.
TITLE_TOPICS = {
    "EDUCATION": "edu", "TAXATION": "tax", "HEALTH AND SAFETY": "health", "INSURANCE": "biz", "TOWNS AND CITIES": "local",
    "TOWN AND CITIES": "local", "MOTOR AND OTHER VEHICLES": "transp", "MOTOR AND MOTOR VEHICLES": "transp",
    "CRIMINAL OFFENSES": "safety", "CRIMINAL PROCEDURE": "safety", "CRIMINALS": "safety", "COURTS AND CIVIL PROCEDURE": "safety",
    "BUSINESSES AND PROFESSIONS": "biz", "BUSINESS AND PROFESSIONS": "biz", "PROPERTY": "housing",
    "PUBLIC UTILITIES AND CARRIERS": "env", "LABOR AND LABOR RELATIONS": "labor", "ELECTIONS": "gov", "ELECTION": "gov",
    "HUMAN SERVICES": "human", "COMMERCIAL LAW": "biz", "FOOD AND DRUGS": "health", "PUBLIC OFFICERS AND EMPLOYEES": "labor",
    "ALCOHOLIC BEVERAGES": "biz", "WATERS AND NAVIGATION": "env", "MILITARY AFFAIRS AND DEFENSE": "human",
    "ANIMALS AND ANIMAL HUSBANDRY": "ag", "DELINQUENT AND DEPENDENT CHILDREN": "human", "HIGHWAYS": "transp",
    "GENERAL ASSEMBLY": "gov", "THE GENERAL ASSEMBLY": "gov", "FINANCIAL INSTITUTIONS": "biz", "PUBLIC RECORDS": "gov",
    "AGRICULTURE AND FORESTRY": "ag", "BEHAVIORAL HEALTHCARE, DEVELOPMENTAL DISABILITIES AND HOSPITALS": "health",
    "PUBLIC FINANCE": "tax", "DOMESTIC RELATIONS": "human", "FISH AND WILDLIFE": "ag", "CORPORATIONS, ASSOCIATIONS, AND PARTNERSHIPS": "biz",
    "CORPORATIONS, ASSOCIATIONS AND PARTNERSHIPS": "biz", "PARKS AND RECREATIONAL AREAS": "ag", "AERONAUTICS": "transp",
    "THE UNIFORM COMMERCIAL CODE": "biz", "STATE AFFAIRS AND GOVERNMENT": "gov",
}

COUNTIES = []
DISTRICTS_PATH = os.path.join(DATA, "district_counties.json")
TOWNS_PATH = os.path.join(DATA, "district_towns.json")

# Rhode Island's 39 cities and towns, for telling local acts (for one of them) from general laws.
MUNICIPALITIES = ("Barrington Bristol Burrillville Central Falls Charlestown Coventry Cranston Cumberland East Greenwich "
                  "East Providence Exeter Foster Glocester Hopkinton Jamestown Johnston Lincoln Little Compton Middletown "
                  "Narragansett Newport New Shoreham North Kingstown North Providence North Smithfield Pawtucket Portsmouth "
                  "Providence Richmond Scituate Smithfield South Kingstown Tiverton Warren Warwick Westerly West Greenwich "
                  "West Warwick Woonsocket").split(" ")
_TWO = {"Central", "East", "Little", "New", "North", "South", "West"}
TOWN_NAMES = []
for _w in MUNICIPALITIES:
    if TOWN_NAMES and TOWN_NAMES[-1] in _TWO:
        TOWN_NAMES[-1] += " " + _w
    else:
        TOWN_NAMES.append(_w)

_NAMING = re.compile(r"\b(?:designat\w*|nam\w*|renam\w*)\b.*\b(?:bridge|interchange|highway|route|memorial|building|park|road|square)\b|\bmemorial (?:highway|bridge|square)\b", re.I)
NARROW_KINDS = ["", "place", "person", "org", "naming"]


def narrow_kind(title):
    return "naming" if _NAMING.search(title) else ""


# Governors and the day each took office. Dan McKee became governor when Gina Raimondo resigned (March 2, 2021) and was
# elected in 2022; the governor elected in November 2026 takes office in January 2027: add them here (and in
# states/legislatures.json) if it's someone else.
GOVERNORS = [("Raimondo", "2015-01-06"), ("McKee", "2021-03-02")]
GOV_SINCE = GOVERNORS[-1][1]


def governor_on(day):
    who = GOVERNORS[0][0]
    for name, start in GOVERNORS:
        if day >= start:
            who = name
    return who


TRENDS = []
WORDING = []
