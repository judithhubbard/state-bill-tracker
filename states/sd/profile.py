"""South Dakota: the settings and wording that are particular to this state.

build_data.py reads these as P.<name>, with the same names as states/ny/profile.py.
"""
import os, re

DATA = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "sd"))
SITE_DIR = "sd"

STATE_NAME = "South Dakota"
SITE_NAME = "South Dakota Bill Tracker"
LEGISLATURE = "South Dakota Legislature"
TIMEZONE = "America/Chicago"
PUBLIC_URL = "https://statebilltracker.org/sd/"
SITE_URL = os.environ.get("SITE_URL", PUBLIC_URL)

# A session a year from the second Tuesday of January: 40 legislative days in odd years, 35 in even years, then a day
# in late March to consider vetoes; bills die at its end.
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
# Who decides which bills reach each house's floor: the Speaker, and in the Senate the President pro tempore (the
# Lieutenant Governor presides but isn't a senator).
LEADERS = {"S": ("Chris Karr", "President Pro Tempore of the Senate", "him"),
           "H": ("Jon Hansen", "Speaker of the House", "him")}


def delegation(session):
    return {}


# Topic: (label, committees (unused), official subjects (unused; see SUBJECT_TOPICS), title words).
NO_SUBJECTS = re.compile(r"(?!)")
TOPICS = {
    "env": ("Environment & energy", set(), NO_SUBJECTS, r"\b(environment\w*|climate|emission\w*|renewable|solar|wind|pollut\w*|energy|utilit\w*|mineral\w*|mining|oil|gas|coal|uranium|nuclear|carbon|electric\w*)\b"),
    "local": ("Local government", set(), NO_SUBJECTS, r"\b(municipal\w*|county|counties|local government)\b"),
    "tax": ("Taxes", set(), NO_SUBJECTS, r"\b(tax\w*|revenue)\b"),
    "safety": ("Public safety & courts", set(), NO_SUBJECTS, r"\b(crim\w*|firearm\w*|police|court\w*|sentenc\w*|prison\w*|jail\w*|felony|misdemeanor|correction\w*)\b"),
    "human": ("Human services", set(), NO_SUBJECTS, r"\b(child care|foster|veteran\w*|senior\w*|elderly|disabilit\w*|homeless\w*)\b"),
    "health": ("Health & mental health", set(), NO_SUBJECTS, r"\b(health|medical|medicaid|hospital\w*|mental|pharmac\w*|nurs\w*|physician\w*)\b"),
    "edu": ("Education", set(), NO_SUBJECTS, r"\b(school\w*|student\w*|teacher\w*|education|college\w*|universit\w*)\b"),
    "transp": ("Transportation", set(), NO_SUBJECTS, r"\b(vehicle\w*|highway\w*|road\w*|traffic|transit|driver\w*|motor)\b"),
    "labor": ("Labor & public employees", set(), NO_SUBJECTS, r"\b(wage\w*|employ\w*|worker\w*|labor|pension\w*|retirement)\b"),
    "housing": ("Housing", set(), NO_SUBJECTS, r"\b(housing|landlord\w*|tenant\w*|rent|eviction\w*)\b"),
    "ag": ("Agriculture & natural resources", set(), NO_SUBJECTS, r"\b(agricultur\w*|farm\w*|livestock|fish\w*|wildlife|hunting|ranch\w*|grazing|water rights)\b"),
    "gov": ("Elections & state government", set(), NO_SUBJECTS, r"\b(election\w*|voter\w*|ballot\w*|state agenc\w*|ethics|public records)\b"),
    "biz": ("Business & consumers", set(), NO_SUBJECTS, r"\b(consumer\w*|business\w*|insurance|bank\w*|licens\w*|corporat\w*|trademark\w*|economic development|currenc\w*)\b"),
    "const": ("Constitutional amendments", set(), NO_SUBJECTS, ""),
}
# Committee name words -> topic (committees with one subject; Appropriations takes any bill that spends money).
COMMITTEE_TOPICS = {"Judiciary": "safety", "Taxation": "tax", "Education": "edu", "Agriculture": "ag",
                    "Transportation": "transp", "Health and Human Services": "health", "Local Government": "local",
                    "State Affairs": "gov", "Commerce": "biz", "Military and Veterans": "human"}
# The Legislature's subject keywords -> topic.
KEYWORD_TOPICS = {
    "Taxation": "tax", "Property Tax": "tax", "Tax Exemptions and Refunds": "tax", "Retail Sales and Service Tax": "tax",
    "Tax Increment Financing Districts": "tax", "Property Assessment or Valuation": "tax",
    "Education": "edu", "School Districts": "edu", "State Aid to Education": "edu", "Students": "edu",
    "Higher Education": "edu", "Private Education": "edu", "Teachers": "edu", "School Curriculum": "edu", "Schools": "edu",
    "Public Health and Safety": "health", "Health Care": "health", "Medical Cannabis": "health",
    "Emergency Medical Services": "health", "Health Maintenance Organizations": "health", "Immunization": "health",
    "Organ Donation": "health", "Abortion": "health", "Therapists and Counselors": "health",
    "Elections": "gov", "State Affairs and Government": "gov", "Ballot Measures": "gov", "Election Verification": "gov",
    "Voting": "gov", "Public Records and Files": "gov", "Open Meetings": "gov", "Legislature and Statutes": "gov",
    "Boards and Commissions": "gov", "Petitions": "gov", "Conflict of Interest": "gov",
    "Motor Vehicles": "transp", "Highways and Bridges": "transp", "Aviation": "transp", "Commercial Trucking": "transp",
    "Traffic Laws": "transp", "Driver License": "transp", "License Plates": "transp", "Drones": "transp",
    "Crimes": "safety", "Controlled Substances": "safety", "Law Enforcement": "safety", "Criminal Procedure": "safety",
    "Correctional Facilities and Parole": "safety", "Courts and Judiciary": "safety", "Domestic Abuse": "safety",
    "Firearms": "safety", "Sex Offenses": "safety", "Juvenile Justice": "safety", "Firefighters": "safety",
    "Emergency Management": "safety", "Civil Forfeiture": "safety",
    "Planning, Zoning and Housing Programs": "housing",
    "Counties": "local", "Municipal Government": "local",
    "Licensure": "biz", "Professions and Occupations": "biz", "Economic Development": "biz", "Insurance": "biz",
    "Trade Regulation": "biz", "Banks and Banking": "biz", "Telecommunications": "biz", "Technology": "biz",
    "Data Centers": "biz", "Alcoholic Beverages": "biz", "Gambling": "biz", "Barbers and Cosmetology": "biz",
    "Public Officers and Employees": "labor", "Retirement System": "labor", "Reemployment Assistance": "labor",
    "State Employees": "labor", "Labor and Employment": "labor",
    "Game, Fish, Parks and Forestry": "ag", "Agriculture and Horticulture": "ag", "Animals and Livestock": "ag",
    "Hunting": "ag", "Fishing": "ag", "Water Management": "ag", "Meat and Meat Products": "ag",
    "Environmental Protection": "env", "Public Utilities and Carriers": "env", "Mining, Oil and Gas": "env",
    "Public Welfare and Assistance": "human", "Veterans Affairs": "human", "Minors": "human", "Child Abuse": "human",
    "Child Custody": "human", "Child Support": "human", "Community-Based Providers": "human", "Domestic Relations": "human",
}
TOPIC_WORDS = {k: re.compile(v[3], re.I) for k, v in TOPICS.items() if v[3]}

COUNTIES = []
DISTRICTS_PATH = os.path.join(DATA, "district_counties.json")
TOWNS_PATH = os.path.join(DATA, "district_towns.json")

_NAMING = re.compile(r"\b(?:designat\w*|nam\w*)\b.*\b(?:bridge|interchange|highway|route|memorial|building|park)\b", re.I)
NARROW_KINDS = ["", "person", "org", "naming"]


def narrow_kind(title):
    return "naming" if _NAMING.search(title) else ""


# Governors and the day each took office (Rhoden succeeded Noem when she resigned).
GOVERNORS = [("Daugaard", "2011-01-08"), ("Noem", "2019-01-05"), ("Rhoden", "2025-01-25")]
GOV_SINCE = GOVERNORS[-1][1]


def governor_on(day):
    who = GOVERNORS[0][0]
    for name, start in GOVERNORS:
        if day >= start:
            who = name
    return who


TRENDS = []
WORDING = []
