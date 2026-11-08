"""Tennessee: the settings and wording that are particular to this state.

build_data.py reads these as P.<name>, with the same names as states/ny/profile.py.
"""
import os, re

DATA = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "tn"))
SITE_DIR = "tn"

STATE_NAME = "Tennessee"
SITE_NAME = "Tennessee Bill Tracker"
LEGISLATURE = "Tennessee General Assembly"
TIMEZONE = "America/Chicago"
PUBLIC_URL = "https://statebilltracker.org/tn/"
SITE_URL = os.environ.get("SITE_URL", PUBLIC_URL)

# Each General Assembly runs two years from an odd year (the 114th is 2025-26) and meets each year from the second
# Tuesday of January, usually until late April. Bills stay alive through both years. Every bill is filed twice, once
# in each house with the same text (a House Bill and its Senate companion); convert.py shows the two as one bill.
YEARS = 2
LOWER = "H"
LOWER_NAME = "House"
TITLES = {"S": "Sen.", "H": "Rep."}


def session_of(year):
    return year if year % 2 else year - 1


def general_assembly(session):
    """2025 -> 114."""
    return 114 + (session - 2025) // 2


def session_label(session):
    return f"{session}–{str(session + 1)[2:]}"


CF_ANALYTICS_TOKEN = ""
GOATCOUNTER_CODE = ""

DELEGATION_NAMES = set()
# Who decides which bills reach each house's floor: the Speaker of the House, and the Speaker of the Senate, whom the
# senators elect from among themselves and who is also Lieutenant Governor (Randy McNally, who didn't run again in 2026:
# the 115th General Assembly elects a new one in January 2027; change it then). Each house's Calendar Committee (the
# House's Calendar and Rules) schedules the floor votes.
LEADERS = {"S": ("Randy McNally", "Lieutenant Governor and Speaker of the Senate", "him"),
           "H": ("Cameron Sexton", "Speaker of the House", "him")}


def delegation(session):
    return {}


# Topic: (label, committees (unused; see COMMITTEE_TOPICS), official subjects (unused; see SUBJECT_TOPICS), title words).
NO_SUBJECTS = re.compile(r"(?!)")
TOPICS = {
    "env": ("Environment & energy", set(), NO_SUBJECTS, r"\b(environment\w*|climate|emission\w*|renewable|solar|pollut\w*|energy|utilit\w*|electric\w*|solid waste|landfill\w*)\b"),
    "local": ("Local government", set(), NO_SUBJECTS, r"\b(municipal\w*|county|counties|cities|city of|town of|local government\w*|annexation|charter)\b"),
    "tax": ("Taxes", set(), NO_SUBJECTS, r"\b(tax\w*|revenue)\b"),
    "safety": ("Public safety & courts", set(), NO_SUBJECTS, r"\b(crim\w*|firearm\w*|handgun\w*|police|court\w*|sentenc\w*|prison\w*|jail\w*|felony|misdemeanor|correction\w*|expunge\w*|offense\w*)\b"),
    "human": ("Human services", set(), NO_SUBJECTS, r"\b(child care|foster|veteran\w*|senior\w*|elderly|disabilit\w*|homeless\w*|children's services)\b"),
    "health": ("Health & mental health", set(), NO_SUBJECTS, r"\b(health|medical|tenncare|medicaid|hospital\w*|mental|pharmac\w*|nurs\w*|physician\w*)\b"),
    "edu": ("Education", set(), NO_SUBJECTS, r"\b(school\w*|student\w*|teacher\w*|education|college\w*|universit\w*|tuition)\b"),
    "transp": ("Transportation", set(), NO_SUBJECTS, r"\b(vehicle\w*|highway\w*|road\w*|traffic|transit|driver\w*|driving|motor)\b"),
    "labor": ("Labor & public employees", set(), NO_SUBJECTS, r"\b(wage\w*|employ\w*|worker\w*|labor|pension\w*|retirement)\b"),
    "housing": ("Housing", set(), NO_SUBJECTS, r"\b(housing|landlord\w*|tenant\w*|rent|eviction\w*|zoning)\b"),
    "ag": ("Agriculture & natural resources", set(), NO_SUBJECTS, r"\b(agricultur\w*|farm\w*|livestock|fish\w*|wildlife|hunting|forest\w*)\b"),
    "gov": ("Elections & state government", set(), NO_SUBJECTS, r"\b(election\w*|voter\w*|voting|ballot\w*|state agenc\w*|ethics|public records|campaign\w*)\b"),
    "biz": ("Business & consumers", set(), NO_SUBJECTS, r"\b(consumer\w*|business\w*|insurance|bank\w*|licens\w*|corporat\w*|economic development|alcohol\w*|beer|wine|gaming)\b"),
    "const": ("Constitutional amendments", set(), NO_SUBJECTS, ""),
}
TOPIC_WORDS = {k: re.compile(v[3], re.I) for k, v in TOPICS.items() if v[3]}

# Committee names (as convert.py writes them) -> topic, for committees with one subject. Finance, Ways and Means,
# Calendar and Rules, Government Operations (agency reviews) and Judiciary-type committees with many subjects give none,
# except where the subject is plain.
COMMITTEE_TOPICS = {
    "Agriculture and Natural Resources": "ag", "Agriculture and Natural Resources Subcommittee": "ag",
    "Energy, Agriculture and Natural Resources": "ag",
    "Banking and Consumer Affairs Subcommittee": "biz", "Business and Utilities Subcommittee": "biz", "Commerce": "biz",
    "Commerce and Labor": "biz", "Insurance": "biz", "Insurance Subcommittee": "biz",
    "Criminal Justice": "safety", "Criminal Justice Subcommittee": "safety", "Civil Justice": "safety",
    "Civil Justice Subcommittee": "safety", "Judiciary": "safety", "Corrections Subcommittee": "safety",
    "Education": "edu", "Education Administration": "edu", "Education Instruction": "edu", "K-12 Subcommittee": "edu",
    "Higher Education Subcommittee": "edu", "Education Administration Subcommittee": "edu",
    "Education Instruction Subcommittee": "edu",
    "Elections and Campaign Finance Subcommittee": "gov", "State Government": "gov", "Departments and Agencies Subcommittee": "gov",
    "Public Service Subcommittee": "labor",
    "Health": "health", "Health Subcommittee": "health", "Health and Welfare": "health", "Population Health Subcommittee": "health",
    "TennCare Subcommittee": "health",
    "Children and Family Affairs Subcommittee": "human", "Children and Families Subcommittee": "human",
    "Local Government": "local", "Cities and Counties Subcommittee": "local", "Private Acts": "local",
    "State and Local Government": "local", "Property and Planning Subcommittee": "housing",
    "Transportation": "transp", "Transportation Subcommittee": "transp", "Transportation and Safety": "transp",
    "Revenue Subcommittee": "tax",
}
# LegiScan's subject names for Tennessee (the General Assembly's subject index) -> topic.
SUBJECT_TOPICS = {
    "Criminal Offenses": "safety", "Criminal Procedure": "safety", "Firearms and Ammunition": "safety", "Law Enforcement": "safety",
    "Juvenile Offenders": "safety", "Sentencing": "safety", "Bail, Bail Bonds": "safety", "Correction, Dept. of": "safety",
    "Tennessee Bureau of Investigation": "safety", "Expunction": "safety", "Controlled Substances": "safety",
    "District Attorneys": "safety", "Courts": "safety", "Courts, Juvenile": "safety", "Civil Procedure": "safety",
    "Handgun Permits": "safety", "DUI Offenses": "safety", "Sexual Offenses": "safety", "Victims' Rights": "safety",
    "Tort Liability and Reform": "safety", "Remedies and Special Proceedings": "safety",
    "Education": "edu", "Local Education Agencies": "edu", "Education, Higher": "edu", "Education, Dept. of": "edu",
    "Teachers, Principals and School Personnel": "edu", "Scholarships and Financial Aid": "edu", "Education, Curriculum": "edu",
    "Schools, Charter": "edu", "School Transportation": "edu", "School Vouchers": "edu",
    "Tennessee Investment in Student Achievement (TISA)": "edu", "Lottery, Scholarships and Programs": "edu",
    "Health Care": "health", "TennCare": "health", "Health, Dept. of": "health", "Hospitals and Health Care Facilities": "health",
    "Medical Occupations": "health", "Mental Health & Substance Abuse Services, Dept. of": "health", "Mental Illness": "health",
    "Drugs, Prescription": "health", "Public Health": "health", "Abortion": "health", "Opioids": "health",
    "Pharmacy, Pharmacists": "health", "Nurses, Nursing": "health", "Insurance, Health, Accident": "health",
    "Election Laws": "gov", "State Government": "gov", "General Assembly": "gov", "Public Records": "gov",
    "Campaigns and Campaign Finance": "gov", "Open Meetings": "gov", "Boards and Commissions": "gov", "Sunset Laws": "gov",
    "Comptroller, State": "gov", "Public Officials": "gov",
    "Taxes": "tax", "Taxes, Sales": "tax", "Taxes, Real Property": "tax", "Taxes, Exemption and Credits": "tax",
    "Taxes, Privilege": "tax", "Taxes, Ad Valorem": "tax",
    "Children": "human", "Children's Services, Dept. of": "human", "Human Services, Dept. of": "human",
    "Child Custody and Support": "human", "Adoption": "human",
    "Consumer Protection": "biz", "Insurance Companies, Agents, Brokers, Policies": "biz", "Alcoholic Beverages": "biz",
    "Alcoholic Beverage Commission": "biz", "Banks and Financial Institutions": "biz", "Business and Commerce": "biz",
    "Professions and Occupations": "biz", "Commerce and Insurance, Dept. of": "biz", "Economic and Community Development": "biz",
    "Tobacco, Tobacco Products": "biz",
    "Real Property": "housing", "Housing": "housing", "Zoning": "housing", "Codes": "housing",
    "Motor Vehicles": "transp", "Motor Vehicles, Titling and Registration": "transp", "Traffic Safety": "transp",
    "Driver Licenses": "transp", "Highways, Roads and Bridges": "transp", "Transportation, Dept. of": "transp",
    "Boats, Boating": "transp",
    "Local Government, General": "local", "County Government": "local", "Municipal Government": "local",
    "Regional Authorities and Special Districts": "local",
    "Utilities, Utility Districts": "env", "Environment and Conservation, Department of": "env", "Energy": "env",
    "Solid Waste Disposal": "env", "Water Pollution": "env",
    "Employees, Employers": "labor", "Pensions and Retirement Benefits": "labor", "State Employees": "labor",
    "Workers Compensation": "labor", "Public Employees": "labor", "Salaries and Benefits": "labor",
    "Agriculture": "ag", "Agriculture, Dept. of": "ag", "Game and Fish Laws": "ag", "Tennessee Fish & Wildlife Commission": "ag",
    "Food and Food Products": "ag", "Parks, Natural Areas Preservation": "ag",
}

COUNTIES = []
DISTRICTS_PATH = os.path.join(DATA, "district_counties.json")
TOWNS_PATH = os.path.join(DATA, "district_towns.json")

_NAMING = re.compile(r"\b(?:designat\w*|nam\w*)\b.*\b(?:bridge|interchange|highway|route|memorial|building|park|road)\b|\bmemorial (?:highway|bridge|interchange)\b", re.I)
NARROW_KINDS = ["", "place", "person", "org", "naming"]


def narrow_kind(title):
    return "naming" if _NAMING.search(title) else ""


# Governors and the day each took office. Bill Lee is term-limited: the governor elected in November 2026 takes office
# in January 2027; add them here (and in states/legislatures.json) then.
GOVERNORS = [("Haslam", "2011-01-15"), ("Lee", "2019-01-19")]
GOV_SINCE = GOVERNORS[-1][1]


def governor_on(day):
    who = GOVERNORS[0][0]
    for name, start in GOVERNORS:
        if day >= start:
            who = name
    return who


TRENDS = []
WORDING = []
