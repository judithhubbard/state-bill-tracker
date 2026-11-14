"""West Virginia: the settings and wording that are particular to this state.

build_data.py reads these as P.<name>, with the same names as states/ny/profile.py.
"""
import os, re

DATA = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "wv"))
SITE_DIR = "wv"

STATE_NAME = "West Virginia"
SITE_NAME = "West Virginia Bill Tracker"
LEGISLATURE = "West Virginia Legislature"
TIMEZONE = "America/New_York"
PUBLIC_URL = "https://statebilltracker.org/wv/"
SITE_URL = os.environ.get("SITE_URL", PUBLIC_URL)

# One 60-day regular session a year, from the second Wednesday of January, or of February in a year a governor is
# inaugurated (2025, 2029: the Legislature meets for one organizational day in January). Bills die when it ends. A page a
# year; special (extraordinary) sessions are left out. The lower house is the House of Delegates.
YEARS = 1
LOWER = "H"
LOWER_NAME = "House of Delegates"
TITLES = {"S": "Sen.", "H": "Del."}


def session_of(year):
    return year


def session_label(session):
    return str(session)


CF_ANALYTICS_TOKEN = ""
GOATCOUNTER_CODE = ""

DELEGATION_NAMES = set()
# Who decides which bills reach each house's floor: the Speaker of the House of Delegates (whose Rules Committee moves bills
# from the House Calendar to the Special Calendar) and the President of the Senate (a senator, elected by the Senate; also
# the Lieutenant Governor by title), who chairs the Senate Rules Committee. From the member list, 2026-11-13; the House
# elected in November 2026 and half the Senate organize in January 2027.
LEADERS = {"S": ("Randy Smith", "President of the Senate", "him"),
           "H": ("Roger Hanshaw", "Speaker of the House of Delegates", "him")}
# The Senate President each year, for "MR PRESIDENT" in the Senate's roll calls.
PRESIDENTS = {2024: "Blair", 2025: "Smith", 2026: "Smith"}


def delegation(session):
    return {}


# Topic: (label, committees (unused; see COMMITTEE_TOPICS), official subjects (unused; see SUBJECT_TOPICS), words in the
# title and summary, used when neither the committee nor the subjects give a topic).
NO_SUBJECTS = re.compile(r"(?!)")
TOPICS = {
    "env": ("Environment & energy", set(), NO_SUBJECTS, r"\b(environment\w*|pollut\w*|energy|utilit\w*|solar|nuclear|electric\w*|solid waste|landfill\w*|recycl\w*|coal|oil and gas|natural gas)\b"),
    "local": ("Local government", set(), NO_SUBJECTS, r"\b(municipal\w*|county|counties|cities|city|towns?|annex\w*|county commission\w*)\b"),
    "tax": ("Taxes", set(), NO_SUBJECTS, r"\b(tax\w*|revenue)\b"),
    "safety": ("Public safety & courts", set(), NO_SUBJECTS, r"\b(crim\w*|firearm\w*|police|law enforcement|court\w*|judge\w*|sentenc\w*|prison\w*|jail\w*|felony|corrections|parole|sheriff\w*|magistrate\w*)\b"),
    "human": ("Human services", set(), NO_SUBJECTS, r"\b(child care|foster|adoption\w*|veteran\w*|senior\w*|elderly|disabilit\w*|homeless\w*|public assistance)\b"),
    "health": ("Health & mental health", set(), NO_SUBJECTS, r"\b(health|medical|medicaid|hospital\w*|mental|pharmac\w*|nurs\w*|physician\w*|abortion)\b"),
    "edu": ("Education", set(), NO_SUBJECTS, r"\b(school\w*|student\w*|teacher\w*|education|college\w*|universit\w*)\b"),
    "transp": ("Transportation", set(), NO_SUBJECTS, r"\b(vehicle\w*|highway\w*|roads?|traffic|driver\w*|transportation|airport\w*)\b"),
    "labor": ("Labor & public employees", set(), NO_SUBJECTS, r"\b(wage\w*|employee\w*|worker\w*|labor|pension\w*|retirement)\b"),
    "housing": ("Housing", set(), NO_SUBJECTS, r"\b(housing|landlord\w*|tenant\w*|eviction\w*|homeowner\w*)\b"),
    "ag": ("Agriculture & natural resources", set(), NO_SUBJECTS, r"\b(agricultur\w*|farm\w*|livestock|fish\w*|wildlife|hunting|forest\w*|timber)\b"),
    "gov": ("Elections & state government", set(), NO_SUBJECTS, r"\b(election\w*|voter\w*|voting|ballot\w*|campaign\w*|ethics|open meetings|public records)\b"),
    "biz": ("Business & consumers", set(), NO_SUBJECTS, r"\b(consumer\w*|business\w*|insurance|bank\w*|licens\w*|alcohol\w*|liquor|beer|wine)\b"),
    "const": ("Constitutional amendments", set(), NO_SUBJECTS, ""),
}
# Committees and subcommittees (as convert.comm_name() names them, both houses) -> topic, for those with one main subject.
# Judiciary, Finance, Government Organization, Rules and the House's 2025 subcommittees on Courts, Legal Services,
# Government Administration, Appropriations and Investments give none of their own.
COMMITTEE_TOPICS = {
    "Agriculture": "ag", "Agriculture and Natural Resources": "ag", "Natural Resources": "ag", "Outdoor Recreation": "ag",
    "Agriculture, Commerce, and Tourism": "ag",
    "Banking and Insurance": "biz", "Economic Development": "biz", "Economic Development and Tourism": "biz",
    "Education": "edu", "Public Education": "edu", "Higher Education": "edu", "Educational Choice": "edu", "School Choice": "edu",
    "Energy and Manufacturing": "env", "Energy and Public Works": "env", "Energy, Industry, and Mining": "env",
    "Environment, Infrastructure, and Technology": "env",
    "Health and Human Resources": "health", "Health Care Regulations": "health", "Public Health": "health",
    "Prevention and Treatment of Substance Abuse": "health", "Substance Use Disorder and Mental Health": "health",
    "Human Services": "human", "Senior, Children, and Family Issues": "human",
    "Fire Departments and Emergency Medical Services": "safety", "Jails and Prisons": "safety", "Homeland Security": "safety",
    "Veterans' Affairs and Homeland Security": "safety", "Military": "safety",
    "Pensions": "labor", "Pensions and Retirement": "labor", "Workforce": "labor", "Workforce Development": "labor",
    "Political Subdivisions": "local", "Local Governments": "local",
    "Revenue": "tax", "Transportation and Infrastructure": "transp", "Technology and Infrastructure": "transp",
}
# The Legislature's bill subjects -> topics. Subjects that say little ("Legislature--Rule Making", "Governor--Bills Requested
# By", "Boards and Commissions", "Finance and Administration", "Resolutions", "Uniform Laws") give none.
_ST = {
    "ag": "Agriculture; Natural Resources",
    "biz": "Insurance; Professions and Occupations; Economic Development; Consumer Protection; Banking and Finance; Corporations; "
           "Alcoholic Liquors and Beers; Legal Gaming",
    "edu": "Education (K12); Education (Higher); Education",
    "env": "Environment; Energy; Utilities; Public Service Commission",
    "gov": "Elections; Ethics; Legislature; Constitutional Officers; State Personnel; Records and Papers; Elected Officials; Governmental Agencies",
    "health": "Health",
    "housing": "Real and Personal Property",
    "human": "Human Services; Juveniles; Domestic Relations; Military and Veterans; Senior Citizens; Human Rights",
    "labor": "Labor; Retirement; Workers Compensation; Unemployment Compensation; Salaries",
    "local": "Counties; Municipalities; County Officials; Local and Special Laws",
    "safety": "Crime; Public Safety; Courts; Corrections; Magistrates; Actions, Suits and Liens",
    "tax": "Taxation",
    "transp": "Motor Vehicles; Roads and Transportation",
    "const": "Constitutional Amendments",
}
SUBJECT_TOPICS = {}
for _k, _v in _ST.items():
    for _h in _v.split(";"):
        SUBJECT_TOPICS.setdefault(_h.strip().lower(), []).append(_k)
TOPIC_WORDS = {k: re.compile(v[3], re.I) for k, v in TOPICS.items() if v[3]}

COUNTIES = []
DISTRICTS_PATH = os.path.join(DATA, "district_counties.json")
TOWNS_PATH = os.path.join(DATA, "district_towns.json")

_NAMING = re.compile(r"\b(?:designat\w*|nam\w*|renam\w*)\b.*\b(?:bridge|interchange|highway|route|memorial|building|park|road)\b|\bmemorial (?:highway|bridge|interchange|road)\b", re.I)
NARROW_KINDS = ["", "person", "org", "naming"]


def narrow_kind(title):
    return "naming" if _NAMING.search(title) else ""


# Governors and the day each took office. Patrick Morrisey's term runs to January 2029.
GOVERNORS = [("Justice", "2017-01-16"), ("Morrisey", "2025-01-13")]
GOV_SINCE = GOVERNORS[-1][1]


def governor_on(day):
    who = GOVERNORS[0][0]
    for name, start in GOVERNORS:
        if day >= start:
            who = name
    return who


TRENDS = []
WORDING = []
