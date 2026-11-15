"""Hawaii: the settings and wording that are particular to this state.

build_data.py reads these as P.<name>, with the same names as states/ny/profile.py.
"""
import os, re

DATA = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "hi"))
SITE_DIR = "hi"

STATE_NAME = "Hawaii"
SITE_NAME = "Hawaii Bill Tracker"
LEGISLATURE = "Hawaii State Legislature"
TIMEZONE = "Pacific/Honolulu"
PUBLIC_URL = "https://statebilltracker.org/hi/"
SITE_URL = os.environ.get("SITE_URL", PUBLIC_URL)

# A two-year Legislature (2025-26 is the 33rd), with a regular session each year from the third Wednesday of January
# (Constitution, Art. III, sec. 10) to early May (60 session days). Bill numbers run through both years, and a bill not
# passed in the first year carries over to the second where it stands ("Carried over to 2026 Regular Session."), so a
# page is the two-year Legislature, named by its first year (decided 2026-11-15; see CLAUDE.md). Laws (Acts) are numbered
# each year: a law's number is "250 of 2025" ("Act 250 of 2025").
YEARS = 2
LOWER = "H"
LOWER_NAME = "House"
TITLES = {"S": "Sen.", "H": "Rep."}
SEATS = {"S": 25, "H": 51}
# Each year's last day (sine die) and the governor's 35th and 45th days after it (Saturdays, Sundays and holidays left
# out: Art. III, sec. 16), from the floor votes and the governor's announcements; as in profile.js's STATE.dated.
SESSION_ENDS = {2023: "2023-05-04", 2024: "2024-05-03", 2025: "2025-05-02", 2026: "2026-05-08"}


def session_of(year):
    return year if year % 2 else year - 1


def session_label(session):
    return f"{session}–{str(session + 1)[2:]}"


def legislature_number(session):
    """2025 -> 33 (the 33rd Legislature)."""
    return (session - 1959) // 2 + 1


CF_ANALYTICS_TOKEN = ""
GOATCOUNTER_CODE = ""

DELEGATION_NAMES = set()
# The Speaker leads the House; the Senate elects its President from among the senators. Nadine Nakamura has been Speaker
# since November 2024 and Ron Kouchi President since 2015 (the Legislature's 2025 and 2026 announcements). Every House
# seat and half the Senate's were on the ballot in November 2026; the 34th Legislature organizes in January 2027: check
# these then.
LEADERS = {"S": ("Ron Kouchi", "President of the Senate", "him"),
           "H": ("Nadine Nakamura", "Speaker of the House", "her")}


def delegation(session):
    return {}


# Committees by year (the codes the histories use) -> name. From each house's announced committee lists (the House
# Speaker's of November 27, 2024 and the Senate President's of December 2025, reprinted by the press; earlier years
# from the same announcements for the 32nd Legislature). The Senate reorganized in 2025 (Energy and Intergovernmental
# Affairs, Economic Development and Tourism) and again for 2026 (Transportation; Water, Land, Culture and the Arts;
# Higher Education folded into Education); the House in 2025.
_S32 = {
    "AEN": "Agriculture and Environment", "CPN": "Commerce and Consumer Protection", "EDU": "Education",
    "EET": "Energy, Economic Development, and Tourism", "GVO": "Government Operations", "HHS": "Health and Human Services",
    "HOU": "Housing", "HRE": "Higher Education", "HWN": "Hawaiian Affairs", "JDC": "Judiciary", "LBT": "Labor and Technology",
    "PSM": "Public Safety and Intergovernmental and Military Affairs", "TCA": "Transportation and Culture and the Arts",
    "WAM": "Ways and Means", "WTL": "Water and Land",
}
_S2025 = dict(_S32, PSM="Public Safety and Military Affairs", EIG="Energy and Intergovernmental Affairs",
              EDT="Economic Development and Tourism")
_S2025.pop("EET")
_S2026 = dict(_S2025, TRS="Transportation", WLA="Water, Land, Culture and the Arts")
for _k in ("TCA", "WTL", "HRE"):
    _S2026.pop(_k)
_H32 = {
    "AGR": "Agriculture and Food Systems", "CAI": "Culture, Arts, and International Affairs",
    "CMV": "Corrections, Military, and Veterans", "CPC": "Consumer Protection and Commerce", "ECD": "Economic Development",
    "EDN": "Education", "EEP": "Energy and Environmental Protection", "FIN": "Finance", "HET": "Higher Education and Technology",
    "HLT": "Health and Homelessness", "HSG": "Housing", "HUS": "Human Services", "JHA": "Judiciary and Hawaiian Affairs",
    "LGO": "Labor and Government Operations", "LMG": "Legislative Management", "TOU": "Tourism", "TRN": "Transportation",
    "WAL": "Water and Land",
}
_H33 = {
    "AGR": "Agriculture and Food Systems", "CAA": "Culture and Arts", "CPC": "Consumer Protection and Commerce",
    "ECD": "Economic Development and Technology", "EDN": "Education", "EEP": "Energy and Environmental Protection",
    "FIN": "Finance", "HED": "Higher Education", "HLT": "Health", "HSG": "Housing", "HSH": "Human Services and Homelessness",
    "JHA": "Judiciary and Hawaiian Affairs", "LAB": "Labor", "LMG": "Legislative Management", "PBS": "Public Safety",
    "TOU": "Tourism", "TRN": "Transportation", "WAL": "Water and Land",
}
COMMITTEES = {2023: {"S": _S32, "H": _H32}, 2024: {"S": _S32, "H": _H32},
              2025: {"S": _S2025, "H": _H33}, 2026: {"S": _S2026, "H": _H33}}


def committee_name(code, year, house):
    """A committee code in a history line of that year -> its name (the nearest year that has the code, else the code)."""
    for y in sorted(COMMITTEES, key=lambda y: (abs(y - year), -y)):
        name = COMMITTEES[y][house].get(code)
        if name:
            return name
    return code


# Topic: (label, committees (unused; see COMMITTEE_TOPICS), official subjects (unused), words in the title, description
# and the bill's subject terms, used when no committee gives a topic).
NO_SUBJECTS = re.compile(r"(?!)")
TOPICS = {
    "env": ("Environment & energy", set(), NO_SUBJECTS, r"\b(environment\w*|climate|greenhouse|emission\w*|renewable|solar|pollut\w*|energy|utilit\w*|electric\w*|recycl\w*|solid waste|plastic\w*|invasive species|coral|reefs?|ocean\w*|watershed\w*|conservation|wildfire\w*|carbon)\b"),
    "local": ("Local government", set(), NO_SUBJECTS, r"\b(count(?:y|ies)|city and county|county council\w*|neighborhood boards?|home rule)\b"),
    "tax": ("Taxes", set(), NO_SUBJECTS, r"\b(tax\w*|general excise|transient accommodations?|income tax|tax credits?)\b"),
    "safety": ("Public safety & courts", set(), NO_SUBJECTS, r"\b(crim\w*|offen[cs]\w*|firearm\w*|guns?|weapon\w*|police|law enforcement|courts?|judg\w*|sentenc\w*|prison\w*|jails?|felon\w*|corrections?|correctional|parole|probation|fireworks|emergency management|sheriff\w*)\b"),
    "human": ("Human services", set(), NO_SUBJECTS, r"\b(child care|keiki|foster|adoption\w*|kupuna|elder\w*|veteran\w*|disabilit\w*|homeless\w*|child welfare|public assistance|SNAP|food security)\b"),
    "health": ("Health & mental health", set(), NO_SUBJECTS, r"\b(health|medical|medicaid|med-quest|hospital\w*|mental|pharmac\w*|nurs\w*|physician\w*|abortion|reproductive|drugs?|opioid\w*|cannabis|dental)\b"),
    "edu": ("Education", set(), NO_SUBJECTS, r"\b(schools?|students?|teachers?|education\w*|colleges?|universit\w*|preschool|early learning)\b"),
    "transp": ("Transportation", set(), NO_SUBJECTS, r"\b(vehicles?|highways?|roads?|traffic|drivers?|transportation|airports?|harbors?|rail|transit|bicycl\w*|mopeds?)\b"),
    "labor": ("Labor & public employees", set(), NO_SUBJECTS, r"\b(wages?|employees?|employ\w*|workers?|labor|pensions?|retirement|unions?|collective bargaining)\b"),
    "housing": ("Housing", set(), NO_SUBJECTS, r"\b(housing|landlords?|tenants?|rent\w*|evictions?|condominium\w*|homeowners?|accessory dwelling\w*)\b"),
    "ag": ("Agriculture & natural resources", set(), NO_SUBJECTS, r"\b(agricultur\w*|farm\w*|ranch\w*|livestock|fish\w*|aquaculture|wildlife|hunting|forest\w*|biosecurity|food systems?)\b"),
    "gov": ("Elections & state government", set(), NO_SUBJECTS, r"\b(elections?|voters?|voting|ballots?|campaigns?|ethics|lobby\w*|public records|sunshine law|procurement|state agenc\w*|legislature)\b"),
    "biz": ("Business & consumers", set(), NO_SUBJECTS, r"\b(consumers?|business\w*|insurance|insurers?|banks?|banking|financial|licens\w*|tourism|liquor|alcohol\w*|commerce|economic development)\b"),
    "const": ("Constitutional amendments", set(), NO_SUBJECTS, ""),
}
# Committee codes (both houses, all years) -> topic, for committees with one main subject. Judiciary, Ways and Means,
# Finance, Hawaiian Affairs and Legislative Management give none of their own.
COMMITTEE_TOPICS = {
    # Senate
    "AEN": "env", "CPN": "biz", "EDU": "edu", "HRE": "edu", "EIG": "env", "EDT": "biz", "GVO": "gov", "HHS": "health",
    "HOU": "housing", "LBT": "labor", "PSM": "safety", "TCA": "transp", "TRS": "transp", "WTL": "env", "WLA": "env",
    # House
    "AGR": "ag", "CMV": "safety", "CPC": "biz", "ECD": "biz", "EDN": "edu", "EEP": "env", "HET": "edu", "HED": "edu",
    "HLT": "health", "HSG": "housing", "HUS": "human", "HSH": "human", "LGO": "labor", "LAB": "labor", "PBS": "safety",
    "TOU": "biz", "TRN": "transp", "WAL": "env",
}
TOPIC_WORDS = {k: re.compile(v[3], re.I) for k, v in TOPICS.items() if v[3]}

COUNTIES = []
DISTRICTS_PATH = os.path.join(DATA, "district_counties.json")
TOWNS_PATH = os.path.join(DATA, "district_towns.json")

_NAMING = re.compile(r"\b(?:designat\w*|nam\w*|renam\w*)\b.*\b(?:bridges?|highways?|roads?|interchanges?|memorial|buildings?|parks?)\b", re.I)
NARROW_KINDS = ["", "naming"]


def narrow_kind(title, desc=""):
    """Bills naming a road or a building. (Hawaii's counties are its only local governments, and its bills for one
    county are few and general in form, so none is marked "place".)"""
    return "naming" if _NAMING.search(title or "") and len(title or "") < 120 else ""


# Governors and the day each took office: David Ige (D) 2014-2022, Josh Green (D) since December 5, 2022. Green ran
# again in November 2026; a governor elected then takes office on the first Monday of December (December 7, 2026).
GOVERNORS = [("Ige", "2014-12-01"), ("Green", "2022-12-05")]
GOV_SINCE = GOVERNORS[-1][1]


def governor_on(day):
    who = GOVERNORS[0][0]
    for name, start in GOVERNORS:
        if day >= start:
            who = name
    return who


TRENDS = []
WORDING = []
