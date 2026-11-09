"""Delaware: the settings and wording that are particular to this state.

build_data.py reads these as P.<name>, with the same names as states/ny/profile.py.
"""
import os, re

DATA = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "de"))
SITE_DIR = "de"

STATE_NAME = "Delaware"
SITE_NAME = "Delaware Bill Tracker"
LEGISLATURE = "Delaware General Assembly"
TIMEZONE = "America/New_York"
PUBLIC_URL = "https://statebilltracker.org/de/"
SITE_URL = os.environ.get("SITE_URL", PUBLIC_URL)

# Two-year General Assemblies (the 153rd is 2025-26). Each year's session opens the second Tuesday of January and runs
# to June 30, when the General Assembly recesses (it doesn't adjourn for good until its term ends, before the November
# election). Bill numbers run through both years, and a bill not passed in the first year carries over to the second:
# one page per General Assembly.
YEARS = 2
LOWER = "H"
LOWER_NAME = "House"
TITLES = {"S": "Sen.", "H": "Rep."}


def session_of(year):
    return year if year % 2 else year - 1


def assembly_of(session):
    """2025 -> 153 (the 153rd General Assembly)."""
    return 153 + (session - 2025) // 2


def session_label(session):
    return f"{session}–{str(session + 1)[2:]}"


CF_ANALYTICS_TOKEN = ""
GOATCOUNTER_CODE = ""

DELEGATION_NAMES = set()
# The Speaker leads the House; the Lieutenant Governor presides over the Senate (not a senator), and the President Pro
# Tempore leads it. From the 153rd General Assembly's member list (members.json), 2026-11-08; the 154th chooses its own
# in January 2027.
LEADERS = {"S": ("David P. Sokola", "President Pro Tempore", "him"),
           "H": ("Melissa Minor-Brown", "Speaker of the House", "her")}


def delegation(session):
    return {}


# Topic: (label, committees (unused; see COMMITTEE_TOPICS), official subjects (unused), title words).
NO_SUBJECTS = re.compile(r"(?!)")
TOPICS = {
    "env": ("Environment & energy", set(), NO_SUBJECTS, r"\b(environment\w*|climate|emission\w*|renewable|solar|wind|pollut\w*|energy|utilit\w*|electric\w*|natural gas|carbon|coastal|recycl\w*|DNREC|waste)\b"),
    "local": ("Local government", set(), NO_SUBJECTS, r"\b(municipal\w*|county|counties|cit(?:y|ies)|towns?|charter|reincorporat\w*|land use|zoning)\b"),
    "tax": ("Taxes", set(), NO_SUBJECTS, r"\b(tax\w*|revenue)\b"),
    "safety": ("Public safety & courts", set(), NO_SUBJECTS, r"\b(crim\w*|firearm\w*|guns?|police|courts?|sentenc\w*|prison\w*|jail\w*|felony|misdemeanor|correctional|law enforcement|offenses?|theft)\b"),
    "human": ("Human services", set(), NO_SUBJECTS, r"\b(child care|foster|veteran\w*|seniors?|elderly|disabilit\w*|homeless\w*|public assistance|family services)\b"),
    "health": ("Health & mental health", set(), NO_SUBJECTS, r"\b(health|medical|medicaid|hospital\w*|mental|pharmac\w*|nurs\w*|physician\w*|abortion|behavioral)\b"),
    "edu": ("Education", set(), NO_SUBJECTS, r"\b(schools?|students?|teachers?|education|college\w*|universit\w*|educators?)\b"),
    "transp": ("Transportation", set(), NO_SUBJECTS, r"\b(vehicles?|highways?|roads?|traffic|transit|drivers?|driving|motor|DelDOT|transportation)\b"),
    "labor": ("Labor & public employees", set(), NO_SUBJECTS, r"\b(wages?|employ\w*|workers?|labor|pensions?|retirement|workforce|unemployment)\b"),
    "housing": ("Housing", set(), NO_SUBJECTS, r"\b(housing|landlords?|tenants?|rent\w*|eviction\w*|manufactured homes?|common interest)\b"),
    "ag": ("Agriculture & natural resources", set(), NO_SUBJECTS, r"\b(agricultur\w*|farm\w*|livestock|fish\w*|wildlife|hunting|crops?|poultry|shellfish|forest\w*)\b"),
    "gov": ("Elections & state government", set(), NO_SUBJECTS, r"\b(elections?|voters?|voting|ballots?|state agenc\w*|ethics|FOIA|freedom of information|General Assembly|sunset)\b"),
    "biz": ("Business & consumers", set(), NO_SUBJECTS, r"\b(consumers?|business\w*|insurance|banks?|banking|licens\w*|corporat\w*|economic development|gaming|alcohol\w*|cannabis|marijuana)\b"),
    # Bills proposing or concurring in an amendment to the Delaware Constitution (tagged by convert.py, not by words).
    "const": ("Constitutional amendments", set(), NO_SUBJECTS, ""),
}
# Committee names (either house) -> topic, for committees with one subject. Appropriations, Capital Infrastructure /
# Capital Improvement and the Senate's Finance and Executive committees take bills on any subject, so theirs get topics
# from their titles.
COMMITTEE_TOPICS = {
    "Agriculture": "ag", "Banking, Business, Insurance & Technology": "biz", "Corrections & Public Safety": "safety",
    "Corrections": "safety", "Economic Development/Banking/Insurance & Commerce": "biz", "Education": "edu",
    "Elections & Government Affairs": "gov", "Environment, Energy & Transportation": "env", "Gaming & Parimutuels": "biz",
    "Health & Human Development": "health", "Health & Social Services": "health", "Housing": "housing",
    "Housing & Land Use": "housing", "Judiciary": "safety", "Labor": "labor", "Natural Resources & Energy": "env",
    "Public Safety & Homeland Security": "safety", "Revenue & Finance": "tax", "Transportation": "transp",
    "Veterans Affairs": "human", "Legislative Oversight & Sunset": "gov",
    "Sunset (Policy Analysis & Government Accountability)": "gov", "Technology & Telecommunications": "biz",
}
TOPIC_WORDS = {k: re.compile(v[3], re.I) for k, v in TOPICS.items() if v[3]}

COUNTIES = []
DISTRICTS_PATH = os.path.join(DATA, "district_counties.json")
TOWNS_PATH = os.path.join(DATA, "district_towns.json")

# Bills about one city or town: its charter ("AN ACT TO AMEND THE CHARTER OF THE TOWN OF MILLVILLE"), reincorporation,
# or one town's own matter.
_PLACE = re.compile(r"\b(?:charter of the (?:city|town|village)|reincorporat\w* the (?:city|town|village)|"
                    r"incorporat\w* (?:a|the) (?:city|town|village))\b", re.I)
_NAMING = re.compile(r"\b(?:designat\w*|nam\w*)\b.*\b(?:bridge|highway|route|memorial|building|interchange|road)\b", re.I)
NARROW_KINDS = ["", "place", "person", "org", "naming"]


def narrow_kind(title):
    return "place" if _PLACE.search(title) else "naming" if _NAMING.search(title) else ""


# Governors and the day each took office (the third Tuesday of January after the election).
GOVERNORS = [("Carney", "2017-01-17"), ("Meyer", "2025-01-21")]
GOV_SINCE = GOVERNORS[-1][1]


def governor_on(day):
    who = GOVERNORS[0][0]
    for name, start in GOVERNORS:
        if day >= start:
            who = name
    return who


TRENDS = []
WORDING = []
