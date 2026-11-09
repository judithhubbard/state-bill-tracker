"""Mississippi: the settings and wording that are particular to this state.

build_data.py reads these as P.<name>, with the same names as states/ny/profile.py.
"""
import os, re

DATA = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "ms"))
SITE_DIR = "ms"

STATE_NAME = "Mississippi"
SITE_NAME = "Mississippi Bill Tracker"
LEGISLATURE = "Mississippi Legislature"
TIMEZONE = "America/Chicago"
PUBLIC_URL = "https://statebilltracker.org/ms/"
SITE_URL = os.environ.get("SITE_URL", PUBLIC_URL)

# Four-year terms (2024-2027), a regular session every year from the Tuesday after the first Monday of January: 125 days in
# a term's first year (2024, 2028), 90 days in the others. Bills die when the session adjourns, and most die earlier, at
# the deadlines for committees and floor votes. A page a year; extraordinary sessions are left out.
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
# Who decides which bills reach each house's floor: the Speaker, and in the Senate the Lieutenant Governor, who presides,
# names the committees and refers the bills, but isn't a senator. From the Legislature's member lists, 2026-11-08.
LEADERS = {"S": ("Delbert Hosemann", "Lieutenant Governor, President of the Senate", "him"),
           "H": ("Jason White", "Speaker of the House", "him")}


def delegation(session):
    return {}


# Topic: (label, committees (unused; see COMMITTEE_TOPICS), official subjects (none), words in the short title).
NO_SUBJECTS = re.compile(r"(?!)")
TOPICS = {
    "env": ("Environment & energy", set(), NO_SUBJECTS, r"\b(environment\w*|climate|emission\w*|renewable|solar|wind|pollut\w*|energy|utilit\w*|mining|oil and gas|nuclear|carbon|electric\w*|solid waste|DEQ)\b"),
    "local": ("Local government", set(), NO_SUBJECTS, r"\b(municipal\w*|county|counties|annexation|local government|city|cities|town of|village of|board of supervisors)\b"),
    "tax": ("Taxes", set(), NO_SUBJECTS, r"\b(tax\w*|revenue|ad valorem|homestead exemption)\b"),
    "safety": ("Public safety & courts", set(), NO_SUBJECTS, r"\b(crim\w*|firearm\w*|weapons?|police|law enforcement|court\w*|judge\w*|judicial|chancell\w*|sentenc\w*|prison\w*|jail\w*|felon\w*|misdemeanor|correction\w*|MDOC|parole|probation|expunge\w*|youth court|juvenile\w*|controlled substances?|fentanyl|trafficking|offense\w*|district attorney\w*|bail|domestic (?:abuse|violence)|divorce|custody|wrongful death|lawsuits?|liabilit\w*|torts?|fire (?:department|protection)|rape|sexual)\b"),
    "human": ("Human services", set(), NO_SUBJECTS, r"\b(child care|foster|adoption\w*|child protection|CPS|child support|veteran\w*|senior\w*|elderly|aged|disabilit\w*|homeless\w*|human services|MDHS|TANF|SNAP|welfare|vulnerable person\w*)\b"),
    "health": ("Health & mental health", set(), NO_SUBJECTS, r"\b(health|medical|medicaid|hospital\w*|mental|pharmac\w*|nurs\w*|physician\w*|abortion|CON|certificate of need|vaccin\w*|immuniz\w*|dental|dentist\w*|EMS|ambulance\w*|opioid\w*|cannabis|marijuana)\b"),
    "edu": ("Education", set(), NO_SUBJECTS, r"\b(school\w*|student\w*|teacher\w*|education\w*|college\w*|universit\w*|tuition|IHL|charter|scholarship\w*|literacy)\b"),
    "transp": ("Transportation", set(), NO_SUBJECTS, r"\b(vehicle\w*|highway\w*|road\w*|bridge\w*|traffic|transit|driver\w*|driving|motor|MDOT|license tags?|airport\w*|aviation|transportation)\b"),
    "labor": ("Labor & public employees", set(), NO_SUBJECTS, r"\b(wage\w*|employ\w*|worker\w*|labor|pension\w*|retirement|PERS|workforce|unemployment)\b"),
    "housing": ("Housing", set(), NO_SUBJECTS, r"\b(housing|landlord\w*|tenant\w*|rental\w*|eviction\w*|homeowner\w*|mortgage\w*|manufactured home\w*)\b"),
    "ag": ("Agriculture & natural resources", set(), NO_SUBJECTS, r"\b(agricultur\w*|farm\w*|livestock|fish\w*|wildlife|hunting|forestry|timber|water resources?|groundwater|aquifer|seafood|oyster\w*|marine resources|catfish|poultry|hemp|deer|game|water (?:association|district|management|supply|system)s?|waterway)\b"),
    "gov": ("Elections & state government", set(), NO_SUBJECTS, r"\b(election\w*|voter\w*|voting|ballot\w*|campaign\w*|initiative\w*|state agenc\w*|ethics|public records|open meetings|legislature|legislative|state auditor|secretary of state|attorney general|governor|state flag|budget|procurement|state employees|state personnel|lobby\w*|redistrict\w*|apportionment|public purchasing|public contracts|holidays?|commemoration|cybersecurity|information technology|state flag|flag)\b"),
    "biz": ("Business & consumers", set(), NO_SUBJECTS, r"\b(consumer\w*|business\w*|insurance|bank\w*|licens\w*|corporat\w*|economic development|gaming|casino\w*|alcohol\w*|beer|wine|liquor|sports betting|lottery|contractor\w*|broadband|commerce|MDA|tobacco|vap\w*)\b"),
    "const": ("Constitutional amendments", set(), NO_SUBJECTS, ""),
}
# Standing committees (as convert.comm_name() names them, both houses) -> topic, for committees with one main subject.
# Appropriations, Ways and Means, Finance, Rules, Management and the civil-law Judiciary committees give none: their
# bills get topics from their words.
COMMITTEE_TOPICS = {
    "Agriculture": "ag", "Apportionment and Elections": "gov", "Elections": "gov",
    "Banking and Financial Services": "biz", "Business and Financial Institutions": "biz", "Business and Commerce": "biz",
    "Insurance": "biz", "Gaming": "biz", "Tourism": "biz", "Economic and Workforce Development": "biz",
    "Conservation and Water Resources": "ag", "Wildlife, Fisheries and Parks": "ag", "Marine Resources": "ag",
    "Forestry": "ag", "Ports and Marine Resources": "ag",
    "Environment Protection, Conservation and Water Resources": "env", "Energy": "env", "Public Utilities": "env",
    "Corrections": "safety", "Drug Policy": "safety",
    "County Affairs": "local", "Municipalities": "local", "Local and Private Legislation": "local",
    "Education": "edu", "Universities and Colleges": "edu",
    "Housing": "housing",
    "Medicaid": "health", "Public Health and Human Services": "health", "Public Health and Welfare": "health",
    "Youth and Family Affairs": "human", "Veterans and Military Affairs": "human", "Military Affairs": "human",
    "Transportation": "transp", "Highways and Transportation": "transp", "Ports, Harbors and Airports": "transp",
    "Workforce Development": "labor", "Labor": "labor",
    "Government Structure": "gov", "State Affairs": "gov", "Ethics": "gov", "Constitution": "gov",
    "Accountability, Efficiency, Transparency": "gov", "Technology": "gov",
    "Judiciary B": "safety", "Judiciary, Division B": "safety",  # criminal law (Judiciary A and Division A: civil law)
}
TOPIC_WORDS = {k: re.compile(v[3], re.I) for k, v in TOPICS.items() if v[3]}

COUNTIES = []
DISTRICTS_PATH = os.path.join(DATA, "district_counties.json")
TOWNS_PATH = os.path.join(DATA, "district_towns.json")

_NAMING = re.compile(r"\b(?:designat\w*|nam\w*|renam\w*)\b.*\b(?:bridge|interchange|highway|route|memorial|building|park)\b|\bmemorial (?:highway|bridge|interchange)\b", re.I)
NARROW_KINDS = ["", "place", "person", "org", "naming"]


# A bill restoring one person's right to vote ("Suffrage; restore to Tony Qualls of Humphreys County"): about 20 a year.
_PERSON = re.compile(r"^Suffrage; restore to\b", re.I)


def narrow_kind(title):
    return "person" if _PERSON.search(title) else "naming" if _NAMING.search(title) else ""


# Governors and the day each took office.
GOVERNORS = [("Bryant", "2012-01-10"), ("Reeves", "2020-01-14")]
GOV_SINCE = GOVERNORS[-1][1]


def governor_on(day):
    who = GOVERNORS[0][0]
    for name, start in GOVERNORS:
        if day >= start:
            who = name
    return who


TRENDS = []
WORDING = []
