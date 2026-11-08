"""Alaska: the settings and wording that are particular to this state.

build_data.py reads these as P.<name>, with the same names as states/ny/profile.py.
"""
import os, re

DATA = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "ak"))
SITE_DIR = "ak"

STATE_NAME = "Alaska"
SITE_NAME = "Alaska Bill Tracker"
LEGISLATURE = "Alaska State Legislature"
TIMEZONE = "America/Anchorage"
PUBLIC_URL = "https://statebilltracker.org/ak/"
SITE_URL = os.environ.get("SITE_URL", PUBLIC_URL)

# Two-year Legislatures starting in odd years (the 34th is 2025-26), with a regular session each year from the third
# Tuesday of January. The constitution allows 121 days (Art. II, sec. 8); a 2006 statute says 90 (AS 24.05.150), but each
# session in the data ran its full 121 days (2023: to May 17; 2024: May 16; 2025 and 2026: May 20; sessions.json). Bills not passed
# in the first year carry over to the second; all die when the Legislature ends. Special sessions (called by the governor
# or by two-thirds of the members) belong to the same Legislature: their bills are numbered from HB 1001 and are shown
# here with the rest, and regular bills on the call can pass in them (SB 183 of 2025 became law in the first special
# session, "Chapter 1, FSSLA 2025").
YEARS = 2
LOWER = "H"
LOWER_NAME = "House"
TITLES = {"S": "Sen.", "H": "Rep."}


def session_of(year):
    return year if year % 2 else year - 1


def legislature_of(session):
    """2025 -> 34 (the 34th Legislature)."""
    return 34 + (session - 2025) // 2


def session_label(session):
    return f"{session}–{str(session + 1)[2:]}"


CF_ANALYTICS_TOKEN = ""
GOATCOUNTER_CODE = ""

DELEGATION_NAMES = set()
# Who decides which bills reach each house's floor: the presiding officers, each chosen by a bipartisan majority
# coalition, with each house's Rules Committee (whose chair is in the coalition). From the members file's leadership
# notes, 2026-11-08; the 35th Legislature chooses its own in January 2027.
LEADERS = {"S": ("Gary Stevens", "President of the Senate", "him"),
           "H": ("Bryce Edgmon", "Speaker of the House", "him")}


def delegation(session):
    return {}


# Committee codes (the history's "L&C RPT", the referral lists' "HL&C") -> names, for both houses. The House's Fisheries,
# Energy, Military and Veterans' Affairs, Tribal Affairs and Ways and Means are special committees that take bills too.
COMMITTEES = {"CRA": "Community and Regional Affairs", "EDC": "Education", "ENE": "Energy", "FIN": "Finance",
              "FSH": "Fisheries", "HSS": "Health and Social Services", "JUD": "Judiciary", "L&C": "Labor and Commerce",
              "MLV": "Military and Veterans' Affairs", "RES": "Resources", "RLS": "Rules", "STA": "State Affairs",
              "TRA": "Transportation", "TRB": "Tribal Affairs", "W&M": "Ways and Means",
              "AET": "Arctic Policy, Economic Development, and Tourism", "AAF": "Arctic Affairs", "WTR": "World Trade"}

# Topic: (label, committees (unused; see COMMITTEE_TOPICS), official subjects (unused; see SUBJECT_TOPICS), title words).
NO_SUBJECTS = re.compile(r"(?!)")
TOPICS = {
    "env": ("Environment & energy", set(), NO_SUBJECTS, r"\b(environment\w*|climate|emission\w*|renewable|solar|wind|pollut\w*|energy|utilit\w*|electric\w*|PFAS|carbon)\b"),
    "local": ("Local government", set(), NO_SUBJECTS, r"\b(municipal\w*|boroughs?|city|cities|local government|unorganized)\b"),
    "tax": ("Taxes", set(), NO_SUBJECTS, r"\b(tax\w*|revenue)\b"),
    "safety": ("Public safety & courts", set(), NO_SUBJECTS, r"\b(crim\w*|firearm\w*|police|courts?|sentenc\w*|prison\w*|jail\w*|felony|misdemeanor|correction\w*|VPSO|troopers?)\b"),
    "human": ("Human services", set(), NO_SUBJECTS, r"\b(child care|foster|veteran\w*|senior\w*|elderly|disabilit\w*|homeless\w*|public assistance|SNAP)\b"),
    "health": ("Health & mental health", set(), NO_SUBJECTS, r"\b(health|medical|medicaid|hospital\w*|mental|pharmac\w*|nurs\w*|physician\w*)\b"),
    "edu": ("Education", set(), NO_SUBJECTS, r"\b(school\w*|students?|teachers?|education|college\w*|universit\w*|univ)\b"),
    "transp": ("Transportation", set(), NO_SUBJECTS, r"\b(vehicles?|highways?|roads?|traffic|transit|drivers?|driving|motor|marine highway|ferr(?:y|ies)|aviation|airports?|railroad)\b"),
    "labor": ("Labor & public employees", set(), NO_SUBJECTS, r"\b(wages?|employ\w*|workers?|labor|pensions?|retirement|PERS|TRS)\b"),
    "housing": ("Housing", set(), NO_SUBJECTS, r"\b(housing|landlords?|tenants?|rent|eviction\w*)\b"),
    "ag": ("Agriculture & natural resources", set(), NO_SUBJECTS, r"\b(agricultur\w*|farm\w*|livestock|fish\w*|wildlife|hunting|game|mining|minerals?|timber|forest\w*|subsistence)\b"),
    "gov": ("Elections & state government", set(), NO_SUBJECTS, r"\b(elections?|voters?|voting|ballots?|state agenc\w*|ethics|public records|legislat\w*)\b"),
    "biz": ("Business & consumers", set(), NO_SUBJECTS, r"\b(consumers?|business\w*|insurance|banks?|licens\w*|corporat\w*|economic development|gaming|alcohol\w*|marijuana)\b"),
    # Joint resolutions proposing amendments to the Alaska Constitution (tagged by convert.py, not by words).
    "const": ("Constitutional amendments", set(), NO_SUBJECTS, ""),
}
# Committee codes -> topic, for committees with one subject. Finance, Rules, State Affairs, Labor and Commerce (business,
# labor and more), Resources (oil, gas, land, fish, game) and Judiciary (crime, but also civil law, elections and the
# constitutional amendments) give none: their bills' subjects do.
COMMITTEE_TOPICS = {"CRA": "local", "EDC": "edu", "ENE": "env", "FSH": "ag", "HSS": "health",
                    "MLV": "human", "TRA": "transp", "W&M": "tax"}
# The Legislature's subject index (each bill's Subjects) -> topic. BOARDS & COMMISSIONS, FUNDS and the like say nothing.
SUBJECT_TOPICS = {
    "EDUCATION": "edu", "SCHOOL DISTRICTS": "edu", "SCHOOLS": "edu", "TEACHERS": "edu", "UNIVERSITIES": "edu",
    "VOCATIONAL TRAINING": "edu", "LIBRARIES": "edu",
    "HEALTH & SOCIAL SERVICES": "health", "MEDICAL CARE": "health", "MENTAL HEALTH": "health", "HOSPITALS": "health",
    "PHYSICIANS": "health", "NURSES": "health", "PHARMACISTS": "health", "DENTISTS": "health", "NURSING HOMES": "health",
    "DRUGS": "health", "IMMUNIZATION": "health", "PSYCHOLOGISTS": "health",
    "CRIMES": "safety", "CRIMINAL PROCEDURE": "safety", "COURTS": "safety", "CORRECTIONS": "safety",
    "LAW ENFORCEMENT": "safety", "PUBLIC SAFETY": "safety", "SENTENCING": "safety", "VICTIMS RIGHTS": "safety",
    "WEAPONS": "safety", "DOMESTIC VIOLENCE": "safety", "JUDGES": "safety", "PUBLIC DEFENDER": "safety",
    "FIRE PROTECTION": "safety", "CIVIL PROCEDURE": "safety",
    "TAXATION": "tax", "REVENUE SHARING": "tax",
    "MUNICIPALITIES": "local", "UNORGANIZED BOROUGH": "local", "BOUNDARIES": "local",
    "TRANSPORTATION": "transp", "MOTOR VEHICLES": "transp", "HIGHWAYS": "transp", "MARINE HIGHWAY": "transp",
    "AIRPORTS": "transp", "AVIATION": "transp", "RAILROAD": "transp",
    "EMPLOYMENT": "labor", "LABOR": "labor", "WAGES": "labor", "PUBLIC EMPLOYEES": "labor", "RETIREMENT": "labor",
    "WORKERS COMPENSATION": "labor", "COLLECTIVE BARGAINING": "labor", "LABOR UNIONS": "labor", "LABOR RELATIONS": "labor",
    "UNEMPLOYMENT": "labor",
    "HOUSING": "housing", "LANDLORD & TENANT": "housing", "CONDOMINIUMS": "housing",
    "ENVIRONMENTAL CONCERNS": "env", "ENERGY": "env", "UTILITIES": "env", "PUBLIC UTILITIES": "env",
    "HAZARDOUS SUBSTANCES": "env", "HAZARDOUS WASTE": "env", "HYDROELECTRIC PROJECTS": "env", "OIL & GAS": "env",
    "AGRICULTURE": "ag", "FISH & GAME (FISH)": "ag", "FISH & GAME (BOTH)": "ag", "FISH & GAME (GAME)": "ag",
    "ANIMALS": "ag", "MINING": "ag", "MINERALS": "ag", "FORESTRY": "ag", "SUBSISTENCE": "ag", "HATCHERIES": "ag",
    "LIMITED ENTRY": "ag", "PUBLIC LAND": "ag", "WATER": "ag",
    "ELECTIONS": "gov", "VOTING": "gov", "CAMPAIGNS": "gov", "ETHICS": "gov", "PUBLIC RECORDS": "gov",
    "EXECUTIVE BRANCH": "gov", "LEGISLATURE": "gov", "POLITICAL PARTIES": "gov", "LOBBYISTS": "gov",
    "INITIATIVES": "gov", "REFERENDA": "gov", "LEGISLATORS": "gov",
    "PUBLIC ASSISTANCE": "human", "SENIOR CITIZENS": "human", "VETERANS": "human", "DISABILITIES": "human",
    "FOSTER CARE": "human", "DAY CARE": "human", "CHILD ABUSE": "human", "CHILD SUPPORT": "human", "ADOPTION": "human",
    "PIONEERS' HOMES": "human",
    "BUSINESS": "biz", "INSURANCE": "biz", "CONSUMER AFFAIRS": "biz", "FINANCIAL INSTITUTIONS": "biz",
    "OCCUPATIONS & PROFESSIONS": "biz", "TRADE PRACTICES": "biz", "ALCOHOL": "biz", "MARIJUANA": "biz",
    "GAMBLING": "biz", "CORPORATIONS": "biz", "ECONOMIC DEVELOPMENT": "biz", "CONTRACTORS": "biz", "TOURISM": "biz",
}
TOPIC_WORDS = {k: re.compile(v[3], re.I) for k, v in TOPICS.items() if v[3]}

COUNTIES = []
DISTRICTS_PATH = os.path.join(DATA, "district_counties.json")
TOWNS_PATH = os.path.join(DATA, "district_towns.json")
# The Senate's districts are letters (A to T, each two House districts: A is House 1 and 2); seat ids and "Where you
# live" number them 1 to 20, and this file gives the page their letters (towns.py writes it).
DISTRICT_NAMES_PATH = os.path.join(DATA, "district_names.json")


def senate_number(letter):
    return ord(letter.upper()) - 64


_NAMING = re.compile(r"\b(?:designat\w*|nam\w*)\b.*\b(?:bridge|highway|route|memorial|building|park|mountain|peak)\b|\bnaming\b", re.I)
NARROW_KINDS = ["", "person", "org", "naming"]


def narrow_kind(title):
    return "naming" if _NAMING.search(title) else ""


# Governors and the day each took office (the first Monday of December after the election). Dunleavy is term-limited: the
# governor elected in November 2026 takes office December 7, 2026; add them here and in states/legislatures.json.
GOVERNORS = [("Walker", "2014-12-01"), ("Dunleavy", "2018-12-03")]
GOV_SINCE = GOVERNORS[-1][1]


def governor_on(day):
    who = GOVERNORS[0][0]
    for name, start in GOVERNORS:
        if day >= start:
            who = name
    return who


TRENDS = []
WORDING = []
