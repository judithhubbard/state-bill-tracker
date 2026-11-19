"""Florida: the settings and wording that are particular to this state.

build_data.py reads these as P.<name>, with the same names as states/ny/profile.py.
"""
import os, re

DATA = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "fl"))
SITE_DIR = "fl"

STATE_NAME = "Florida"
SITE_NAME = "Florida Bill Tracker"
LEGISLATURE = "Florida Legislature"
TIMEZONE = "America/New_York"
PUBLIC_URL = "https://statebilltracker.org/fl/"
SITE_URL = os.environ.get("SITE_URL", PUBLIC_URL)

# One 60-day regular session a year (Constitution, Art. III, sec. 3): from the first Tuesday after the first Monday in
# March in odd years, and in even years from the second Tuesday after the first Monday in January (set by law, s. 11.011).
# A session can be extended (2025's ran to June 16 for the budget). Bills die when it ends. A page a year; special
# sessions and the organization session after each election are left out.
YEARS = 1
# Each session's last day (sine die), as in profile.js's STATE.dated: add each year's.
SESSION_ENDS = {2024: "2024-03-08", 2025: "2025-06-16", 2026: "2026-03-13"}
LOWER = "H"
LOWER_NAME = "House"
TITLES = {"S": "Sen.", "H": "Rep."}


def session_of(year):
    return year


def session_kind(session):
    return "regular"


def session_label(session):
    return str(session)


def term_of(session):
    """The two-year term a session belongs to, by its first year (data/fl/members/<term>.json): the 2025 and 2026
    sessions are the 2024-2026 term's (members elected in November 2024)."""
    return session - 1 if session % 2 else session - 2


CF_ANALYTICS_TOKEN = ""
GOATCOUNTER_CODE = ""

DELEGATION_NAMES = set()
# Who decides which bills reach each house's floor: the Senate President (a senator, elected by the Senate) and the Speaker
# of the House, each through the Rules Committee and the special order calendar. Each two-year term's officers are chosen
# at the organization session two weeks after the November election; for 2026-2028 the majority chose Jim Boyd (President)
# and Sam Garrison (Speaker) as designates (the organization session, November 17, 2026, elects them: check then).
LEADERS = {"S": ("Jim Boyd", "President of the Senate", "him"),
           "H": ("Sam Garrison", "Speaker of the House", "him")}
# Each term's presiding officers, by the term's first year (the House member list names no posts).
OFFICERS = {
    2022: {"S": ("Passidomo", "President of the Senate"), "H": ("Renner", "Speaker of the House")},
    2024: {"S": ("Albritton", "President of the Senate"), "H": ("Perez", "Speaker of the House")},
    2026: {"S": ("Boyd", "President of the Senate"), "H": ("Garrison", "Speaker of the House")},
}


def delegation(session):
    return {}


# Topic: (label, committees (unused; see COMMITTEE_TOPICS), official subjects (unused), words in the short title and the
# description, used when no committee gives a topic).
NO_SUBJECTS = re.compile(r"(?!)")
TOPICS = {
    "env": ("Environment and energy", set(), NO_SUBJECTS, r"\b(environment\w*|pollut\w*|energy|utilit\w*|solar|electric\w*|water quality|springs|everglades|resilien\w*|conservation|recycl\w*|solid waste|beach\w*)\b"),
    "local": ("Local government", set(), NO_SUBJECTS, r"\b(municipal\w*|count(?:y|ies)|cit(?:y|ies)|special districts?|community development districts?|annex\w*)\b"),
    "tax": ("Taxes", set(), NO_SUBJECTS, r"\b(tax\w*|ad valorem|homestead exemption)\b"),
    "safety": ("Public safety and courts", set(), NO_SUBJECTS, r"\b(crim\w*|offen[cs]\w*|firearm\w*|weapon\w*|police|law enforcement|courts?|judg\w*|sentenc\w*|prison\w*|jails?|felon\w*|corrections|sheriff\w*|emergency management|fire(?:fighter)?s?)\b"),
    "human": ("Social services", set(), NO_SUBJECTS, r"\b(child care|foster|adoption\w*|veteran\w*|elder\w*|disabilit\w*|homeless\w*|child welfare|public assistance)\b"),
    "health": ("Health", set(), NO_SUBJECTS, r"\b(health|medical|medicaid|hospital\w*|mental|pharmac\w*|nurs\w*|physician\w*|abortion|drugs?)\b"),
    "edu": ("Education", set(), NO_SUBJECTS, r"\b(schools?|students?|teachers?|education\w*|colleges?|universit\w*)\b"),
    "transp": ("Transportation", set(), NO_SUBJECTS, r"\b(vehicles?|highways?|roads?|traffic|drivers?|transportation|airports?|seaports?|toll\w*)\b"),
    "labor": ("Jobs and workers", set(), NO_SUBJECTS, r"\b(wages?|employees?|employ\w*|workers?|labor|pensions?|retirement|unions?)\b"),
    "housing": ("Housing", set(), NO_SUBJECTS, r"\b(housing|landlords?|tenants?|evictions?|condominium\w*|homeowners?)\b"),
    "ag": ("Agriculture and natural resources", set(), NO_SUBJECTS, r"\b(agricultur\w*|farm\w*|livestock|fish\w*|wildlife|hunting|forest\w*|citrus|aquaculture)\b"),
    "gov": ("Elections and government", set(), NO_SUBJECTS, r"\b(elections?|voters?|voting|ballots?|campaigns?|ethics|public records|public meetings|state agenc\w*)\b"),
    "biz": ("Business and consumers", set(), NO_SUBJECTS, r"\b(consumers?|business\w*|insurance|insurers?|banks?|banking|licens\w*|alcohol\w*|beverage\w*|gaming|gambling|financial)\b"),
    "const": ("Constitutional amendments", set(), NO_SUBJECTS, ""),
}
# Committees (as convert.comm_name() names them, both houses) -> topic, for committees with one main subject. Judiciary,
# Rules, Fiscal Policy, Appropriations, Budget, State Affairs and the like give none of their own.
COMMITTEE_TOPICS = {
    # Senate
    "Agriculture": "ag", "Banking and Insurance": "biz", "Children, Families, and Elder Affairs": "human",
    "Commerce and Tourism": "biz", "Community Affairs": "local", "Criminal Justice": "safety",
    "Education Postsecondary": "edu", "Education Pre-K - 12": "edu", "Education Pre-K -12": "edu",
    "Environment and Natural Resources": "env", "Ethics and Elections": "gov", "Finance and Tax": "tax",
    "Governmental Oversight and Accountability": "gov", "Health Policy": "health", "Regulated Industries": "biz",
    "Transportation": "transp", "Military and Veterans Affairs, Space, and Domestic Security": "safety",
    "Criminal and Civil Justice Appropriations": "safety", "Health and Human Services Appropriations": "health",
    "Education Appropriations": "edu", "Higher Education Appropriations": "edu", "Pre-K - 12 Education Appropriations": "edu",
    "Agriculture, Environment, and General Government Appropriations": "env",
    "Transportation, Tourism, and Economic Development Appropriations": "transp",
    # House
    "Agriculture and Natural Resources Appropriations": "ag", "Agriculture and Natural Resources Budget": "ag",
    "Agriculture, Conservation and Resiliency": "ag", "Careers and Workforce": "labor",
    "Children, Families and Seniors": "human", "Choice and Innovation": "edu", "Civil Justice": "safety",
    "Commerce": "biz", "Education and Employment": "edu", "Education Administration": "edu", "Education Quality": "edu",
    "Energy, Communications and Cybersecurity": "env", "Ethics, Elections and Open Government": "gov",
    "Government Operations": "gov", "Health and Human Services": "health", "Health Care Appropriations": "health",
    "Health Care Budget": "health", "Health Care Facilities and Systems": "health",
    "Health Professions and Programs": "health", "Healthcare Regulation": "health",
    "Higher Education Appropriations Subcommittee": "edu", "Higher Education Budget": "edu",
    "Housing, Agriculture and Tourism": "housing", "Human Services": "human", "Insurance and Banking": "biz",
    "Industries and Professional Activities": "biz", "Infrastructure and Tourism Appropriations": "transp",
    "Intergovernmental Affairs": "local", "Justice Appropriations": "safety", "Justice Budget": "safety",
    "Local Administration, Federal Affairs and Special Districts": "local", "Natural Resources and Disasters": "env",
    "Postsecondary Education and Workforce": "edu", "PreK-12 Appropriations": "edu", "PreK-12 Budget": "edu",
    "Regulatory Reform and Economic Development": "biz", "Student Academic Success": "edu",
    "Transportation and Economic Development Budget": "transp", "Transportation and Modals": "transp",
    "Water Quality, Supply and Treatment": "env", "Ways and Means": "tax", "Property Taxes Select": "tax",
    "Health Innovation Select": "health", "Criminal Justice Subcommittee": "safety",
}
TOPIC_WORDS = {k: re.compile(v[3], re.I) for k, v in TOPICS.items() if v[3]}

COUNTIES = []
DISTRICTS_PATH = os.path.join(DATA, "district_counties.json")
TOWNS_PATH = os.path.join(DATA, "district_towns.json")

_NAMING = re.compile(r"\b(?:designat\w*|nam\w*|renam\w*)\b.*\b(?:bridges?|highways?|roads?|interchanges?|memorial|buildings?|parks?)\b|^Road Designations|^Designation of ", re.I)
NARROW_KINDS = ["", "person", "org", "naming"]


def narrow_kind(title, kind="", key=""):
    """Local bills (the bill type "LOCAL BILL", or a House bill numbered 4001-4999, where the House files them) are for one
    place; claim bills ("Relief of ...", "CLAIM") pay one person or family."""
    if re.search(r"\bLOCAL\b", kind) and not re.search(r"CLAIM", kind):
        return "place"
    if re.search(r"CLAIM", kind) or re.match(r"Relief of\b", title or ""):
        return "person"
    if not kind and re.fullmatch(r"HB4\d{3}", key or ""):
        return "place"
    return "naming" if _NAMING.search(title or "") else ""


# Governors and the day each took office. Ron DeSantis is term-limited; the governor elected in November 2026 takes office
# January 5, 2027: add them here, and in states/legislatures.json.
GOVERNORS = [("Scott", "2011-01-04"), ("DeSantis", "2019-01-08"), ("Donalds", "2027-01-05")]  # governor-elect: in office from that day (governors.py)
GOV_SINCE = GOVERNORS[-1][1]


def governor_on(day):
    who = GOVERNORS[0][0]
    for name, start in GOVERNORS:
        if day >= start:
            who = name
    return who


TRENDS = []
WORDING = []
