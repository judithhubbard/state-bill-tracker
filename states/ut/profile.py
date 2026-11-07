"""Utah: the settings and wording that are particular to this state.

build_data.py reads these as P.<name>, with the same names as states/ny/profile.py.
"""
import os, re

DATA = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "ut"))
SITE_DIR = "ut"

STATE_NAME = "Utah"
SITE_NAME = "Utah Bill Tracker"
LEGISLATURE = "Utah State Legislature"
TIMEZONE = "America/Denver"
PUBLIC_URL = "https://statebilltracker.org/ut/"
SITE_URL = os.environ.get("SITE_URL", PUBLIC_URL)

# A 45-day general session a year from the third Tuesday of January; bills die at its end.
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
# Who decides which bills reach each house's floor: the Speaker, and the President of the Senate (through each house's
# Rules Committee). The member list marks the Speaker but not the Senate's officers.
LEADERS = {"S": ("J. Stuart Adams", "President of the Senate", "him"),
           "H": ("Mike Schultz", "Speaker of the House", "him")}


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
# Committee name words -> topic (committees with one subject).
COMMITTEE_TOPICS = {"Judiciary": "safety", "Law Enforcement": "safety", "Revenue and Taxation": "tax", "Education": "edu",
                    "Natural Resources": "env", "Transportation": "transp", "Health and Human Services": "health",
                    "Political Subdivisions": "local", "Government Operations": "gov", "Business": "biz",
                    "Economic Development": "biz", "Public Utilities": "env"}
# The Legislature's subjects -> topic.
SUBJECT_TOPICS = {
    "Health and Human Services": "health", "Health Care": "health", "Department of Health and Human Services": "health",
    "Health Care Professionals": "health", "Health Insurance": "health", "Health Care Facilities": "health",
    "Mental Health": "health", "Medicaid": "health", "Substance Abuse": "health",
    "Government Operations (State Issues)": "gov", "Legislative Operations": "gov", "Election Law": "gov",
    "Election Administration": "gov", "Voting and Voter Registration": "gov", "Government Records": "gov",
    "Constitutional Officers": "gov", "Administrative Rulemaking and Procedures": "gov",
    "Law Enforcement and Criminal Justice": "safety", "Crimes": "safety", "Judicial Operations": "safety", "Courts": "safety",
    "Punishment": "safety", "Public Safety": "safety", "Controlled Substances": "safety", "Sexual Offenses": "safety",
    "Peace Officers": "safety", "Department of Corrections": "safety", "Correctional Facilities": "safety",
    "Criminal Procedure": "safety", "Sentencing": "safety", "Weapons": "safety",
    "Education": "edu", "K-12 Education": "edu", "Local Education Agencies (LEAs)": "edu", "Higher Education": "edu",
    "State Board of Education": "edu", "School Districts": "edu", "School Finance": "edu", "Colleges and Universities": "edu",
    "Standards and Curriculum": "edu", "School Personnel": "edu", "Student Health and Safety": "edu",
    "Business": "biz", "Economic Development": "biz", "Occupational and Professional Licensing": "biz", "Insurance": "biz",
    "Commerce and Trade": "biz", "Consumer Protection": "biz", "Technology": "biz",
    "Transportation": "transp", "Motor Vehicles": "transp", "Roads/Highways": "transp", "Division of Motor Vehicles": "transp",
    "Vehicle Registration": "transp", "Transportation Funding": "transp", "Driver License": "transp",
    "Traffic Violations": "transp", "Commercial Motor Vehicle Regulation": "transp", "Department of Transportation": "transp",
    "Political Subdivisions (Local Issues)": "local", "Counties": "local", "Municipalities": "local",
    "County and Municipal Finance": "local", "Limited Purpose Local Government Entities": "local", "County Officers": "local",
    "Revenue and Taxation": "tax", "State Tax Commission": "tax", "Property Tax": "tax", "Local Taxation and Fees": "tax",
    "Income Tax": "tax", "Tax Credits": "tax", "Individual Income Tax": "tax", "Sales and Use Tax": "tax",
    "Natural Resources": "ag", "Water": "ag", "Agriculture & Food": "ag", "Agriculture": "ag", "Animals": "ag",
    "Department of Natural Resources": "ag", "Department of Agriculture and Food": "ag", "Public Lands": "ag",
    "Environment": "env", "Energy": "env", "Public Utilities and Technology": "env",
    "Workforce Services": "labor", "Labor and Employment": "labor", "Public Retirement and Insurance": "labor",
    "Housing": "housing", "Affordable Housing": "housing", "Land Use": "housing", "Planning and Zoning": "housing",
    "Real Property": "housing", "Homelessness": "housing",
    "Child Welfare": "human", "Family": "human", "Veterans and Military Affairs": "human", "Department of Workforce Services": "human",
}
TOPIC_WORDS = {k: re.compile(v[3], re.I) for k, v in TOPICS.items() if v[3]}

COUNTIES = []
DISTRICTS_PATH = os.path.join(DATA, "district_counties.json")
TOWNS_PATH = os.path.join(DATA, "district_towns.json")

_NAMING = re.compile(r"\b(?:designat\w*|nam\w*)\b.*\b(?:bridge|interchange|highway|route|memorial|building|park)\b", re.I)
NARROW_KINDS = ["", "person", "org", "naming"]


def narrow_kind(title):
    return "naming" if _NAMING.search(title) else ""


# Governors and the day each took office.
GOVERNORS = [("Herbert", "2009-08-11"), ("Cox", "2021-01-04")]
GOV_SINCE = GOVERNORS[-1][1]


def governor_on(day):
    who = GOVERNORS[0][0]
    for name, start in GOVERNORS:
        if day >= start:
            who = name
    return who


TRENDS = []
WORDING = []
