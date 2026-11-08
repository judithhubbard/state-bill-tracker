"""North Dakota: the settings and wording that are particular to this state.

build_data.py reads these as P.<name>, with the same names as states/ny/profile.py.
"""
import os, re

DATA = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "nd"))
SITE_DIR = "nd"

STATE_NAME = "North Dakota"
SITE_NAME = "North Dakota Bill Tracker"
LEGISLATURE = "North Dakota Legislative Assembly"
TIMEZONE = "America/Chicago"
PUBLIC_URL = "https://statebilltracker.org/nd/"
SITE_URL = os.environ.get("SITE_URL", PUBLIC_URL)

# Two-year Legislative Assemblies (the 69th is 2025-26), but the regular session meets only in the odd year: from early
# January, at most 80 legislative days, to late April or early May (2023: April 29; 2025: May 2, the last floor votes).
# Every bill not passed then dies. The Legislative Management or the governor can call the assembly back for special
# sessions (the 68th in October 2023, the 69th in January and September 2026), whose bills are numbered after the
# regular session's (HB 1621 on) in the same assembly's files: they're shown with the rest, on the assembly's page.
YEARS = 2
LOWER = "H"
LOWER_NAME = "House"
TITLES = {"S": "Sen.", "H": "Rep."}


def session_of(year):
    return year if year % 2 else year - 1


def assembly_of(session):
    """2025 -> 69 (the 69th Legislative Assembly)."""
    return 69 + (session - 2025) // 2


def session_label(session):
    return f"{session}–{str(session + 1)[2:]}"


CF_ANALYTICS_TOKEN = ""
GOATCOUNTER_CODE = ""

DELEGATION_NAMES = set()
# The Speaker presides over the House; the Lieutenant Governor presides over the Senate (not a senator), so the Senate's
# majority leader stands in. Every bill gets a floor vote in North Dakota, so neither decides whether a bill is voted
# on. From the leadership page (leaders.json), 2026-11-08; the 70th Legislative Assembly chooses its own in December 2026.
LEADERS = {"S": ("David Hogue", "Senate Majority Leader", "him"),
           "H": ("Robin Weisz", "Speaker of the House", "him")}


def delegation(session):
    return {}


# Topic: (label, committees (unused; see COMMITTEE_TOPICS), official subjects (unused), title words).
NO_SUBJECTS = re.compile(r"(?!)")
TOPICS = {
    "env": ("Environment & energy", set(), NO_SUBJECTS, r"\b(environment\w*|climate|emission\w*|renewable|solar|wind energy|pollut\w*|energy|utilit\w*|electric\w*|oil|gas|coal|carbon|pipelines?|lignite)\b"),
    "local": ("Local government", set(), NO_SUBJECTS, r"\b(municipal\w*|county|counties|cit(?:y|ies)|townships?|political subdivisions?|home rule)\b"),
    "tax": ("Taxes", set(), NO_SUBJECTS, r"\b(tax\w*|revenue)\b"),
    "safety": ("Public safety & courts", set(), NO_SUBJECTS, r"\b(crim\w*|firearm\w*|police|courts?|sentenc\w*|prison\w*|jail\w*|felony|misdemeanor|correction\w*|law enforcement|penalt(?:y|ies))\b"),
    "human": ("Human services", set(), NO_SUBJECTS, r"\b(child care|foster|veteran\w*|senior\w*|elderly|disabilit\w*|homeless\w*|human service zones?|public assistance)\b"),
    "health": ("Health & mental health", set(), NO_SUBJECTS, r"\b(health|medical|medicaid|hospital\w*|mental|pharmac\w*|nurs\w*|physician\w*|abortion)\b"),
    "edu": ("Education", set(), NO_SUBJECTS, r"\b(schools?|students?|teachers?|education|college\w*|universit\w*)\b"),
    "transp": ("Transportation", set(), NO_SUBJECTS, r"\b(vehicles?|highways?|roads?|traffic|transit|drivers?|driving|motor|aviation|airports?)\b"),
    "labor": ("Labor & public employees", set(), NO_SUBJECTS, r"\b(wages?|employ\w*|workers?|labor|pensions?|retirement|workforce)\b"),
    "housing": ("Housing", set(), NO_SUBJECTS, r"\b(housing|landlords?|tenants?|rent|eviction\w*)\b"),
    "ag": ("Agriculture & natural resources", set(), NO_SUBJECTS, r"\b(agricultur\w*|farm\w*|livestock|fish\w*|wildlife|hunting|game and fish|grain|crops?|ranch\w*|water)\b"),
    "gov": ("Elections & state government", set(), NO_SUBJECTS, r"\b(elections?|voters?|voting|ballots?|state agenc\w*|ethics|open records|legislative assembly)\b"),
    "biz": ("Business & consumers", set(), NO_SUBJECTS, r"\b(consumers?|business\w*|insurance|banks?|licens\w*|corporat\w*|economic development|gaming|alcohol\w*)\b"),
    # Concurrent resolutions proposing amendments to the Constitution of North Dakota (tagged by convert.py, not by words).
    "const": ("Constitutional amendments", set(), NO_SUBJECTS, ""),
}
# Standing committee names (either house) -> topic, for committees with one subject. Appropriations takes any bill that
# spends money, and Judiciary also takes civil law and elections; State and Local Government (the Senate's) and the
# House's Government and Veterans Affairs cover several, so their bills get topics from their titles.
COMMITTEE_TOPICS = {"Agriculture": "ag", "Agriculture and Veterans Affairs": "ag", "Education": "edu",
                    "Energy and Natural Resources": "env", "Finance and Taxation": "tax", "Human Services": "health",
                    "Industry, Business and Labor": "biz", "Industry and Business": "biz", "Judiciary": "safety",
                    "Political Subdivisions": "local", "Transportation": "transp", "Workforce Development": "labor"}
TOPIC_WORDS = {k: re.compile(v[3], re.I) for k, v in TOPICS.items() if v[3]}

COUNTIES = []
DISTRICTS_PATH = os.path.join(DATA, "district_counties.json")
TOWNS_PATH = os.path.join(DATA, "district_towns.json")

_NAMING = re.compile(r"\b(?:designat\w*|nam\w*)\b.*\b(?:bridge|highway|route|memorial|building|interchange)\b", re.I)
NARROW_KINDS = ["", "person", "org", "naming"]


def narrow_kind(title):
    return "naming" if _NAMING.search(title) else ""


# Governors and the day each took office (December 15 after the election). Kelly Armstrong took office December 15, 2024.
GOVERNORS = [("Burgum", "2016-12-15"), ("Armstrong", "2024-12-15")]
GOV_SINCE = GOVERNORS[-1][1]


def governor_on(day):
    who = GOVERNORS[0][0]
    for name, start in GOVERNORS:
        if day >= start:
            who = name
    return who


TRENDS = []
WORDING = []
