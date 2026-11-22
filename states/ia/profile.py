"""Iowa: the settings and wording that are particular to this state.

build_data.py reads these as P.<name>, with the same names as states/ny/profile.py.
"""
import os, re

DATA = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "ia"))
SITE_DIR = "ia"

STATE_NAME = "Iowa"
SITE_NAME = "Iowa Bill Tracker"
LEGISLATURE = "Iowa General Assembly"
TIMEZONE = "America/Chicago"
PUBLIC_URL = "https://statebilltracker.org/ia/"
SITE_URL = os.environ.get("SITE_URL", PUBLIC_URL)

# A two-year General Assembly (2025-26 is the 91st), with a session each year from the second Monday of January (Iowa
# Code 2.1) to April or May. Bill numbers run through both years (the second year's House Files from HF 2000, Senate
# Files from SF 2000), and a bill not passed in the first year carries over to the second where it stands, so a page is
# the General Assembly, named by its first year (decided 2026-11-15; see CLAUDE.md). Laws are chapters of each year's
# Iowa Acts ("2025 Iowa Acts, chapter 46": "46 of 2025").
YEARS = 2
LOWER = "H"
LOWER_NAME = "House"
TITLES = {"S": "Sen.", "H": "Rep."}
SEATS = {"S": 50, "H": 100}
# Each year's last day (sine die), from the floor votes and the news; as in profile.js's STATE.dated. Add each year's.
SESSION_ENDS = {2023: "2023-05-04", 2024: "2024-04-20", 2025: "2025-05-15", 2026: "2026-05-03"}


def plus_days(iso, n):
    from datetime import date, timedelta
    return (date.fromisoformat(iso) + timedelta(days=n)).isoformat()


def session_of(year):
    return year if year % 2 else year - 1


def session_label(session):
    return f"{session}–{str(session + 1)[2:]}"


def ga_of(session):
    """2025 -> 91 (the 91st General Assembly)."""
    return (session - 1845) // 2 + 1


# Constitutional amendments whose first passage came in a General Assembly not read here: 2023's HJR 3 (the governor's
# line of succession) and SJR 9 (the qualifications of electors) passed the 89th General Assembly first (2021-22) and were
# Amendments 2 and 1 on the November 2024 ballot. Later second passages are found by linking to the General Assembly before.
SECOND_PASSAGES = {2023: {"HJR3", "SJR9"}}

CF_ANALYTICS_TOKEN = ""
GOATCOUNTER_CODE = ""

DELEGATION_NAMES = set()
# The Speaker leads the House (Pat Grassley since 2020); in the Senate the Majority Leader decides which bills reach the
# floor (Mike Klimesh, chosen by the Senate Republicans in September 2025 after Jack Whitver stepped aside; Amy Sinclair
# is President of the Senate). The 92nd General Assembly organizes in January 2027: check these then.
LEADERS = {"S": ("Mike Klimesh", "Senate Majority Leader", "him"),
           "H": ("Pat Grassley", "Speaker of the House", "him")}


def delegation(session):
    return {}


# Topic: (label, committees (unused; see COMMITTEE_TOPICS), official subjects (unused), words in the title, used when no
# committee gives a topic).
NO_SUBJECTS = re.compile(r"(?!)")
TOPICS = {
    "env": ("Environment and energy", set(), NO_SUBJECTS, r"\b(environment\w*|climate|emission\w*|renewable|solar|wind energy|pollut\w*|energy|utilit\w*|electric\w*|recycl\w*|solid waste|water quality|carbon|pipelines?|nitrates?|drainage)\b"),
    "local": ("Local government", set(), NO_SUBJECTS, r"\b(count(?:y|ies)|cit(?:y|ies)|municipal\w*|townships?|local governments?|political subdivisions?|boards? of supervisors)\b"),
    "tax": ("Taxes", set(), NO_SUBJECTS, r"\b(tax\w*|property assessments?|tax credits?)\b"),
    "safety": ("Public safety and courts", set(), NO_SUBJECTS, r"\b(crim\w*|offen[cs]\w*|firearm\w*|guns?|weapon\w*|police|peace officers?|law enforcement|courts?|judg\w*|sentenc\w*|prison\w*|jails?|felon\w*|corrections?|correctional|parole|probation|sheriff\w*)\b"),
    "human": ("Social services", set(), NO_SUBJECTS, r"\b(child care|foster|adoption\w*|elder\w*|older Iowans|veteran\w*|disabilit\w*|homeless\w*|child welfare|public assistance|food assistance|SNAP)\b"),
    "health": ("Health", set(), NO_SUBJECTS, r"\b(health|medical|medicaid|hospital\w*|mental|pharmac\w*|nurs\w*|physician\w*|abortion|reproductive|drugs?|opioid\w*|cannabis|dental)\b"),
    "edu": ("Education", set(), NO_SUBJECTS, r"\b(schools?|students?|teachers?|education\w*|colleges?|universit\w*|preschool|board of regents)\b"),
    "transp": ("Transportation", set(), NO_SUBJECTS, r"\b(vehicles?|highways?|roads?|traffic|drivers?|transportation|airports?|rail\w*|transit|bicycl\w*|motorcycl\w*)\b"),
    "labor": ("Jobs and workers", set(), NO_SUBJECTS, r"\b(wages?|employees?|employ\w*|workers?|labor|pensions?|IPERS|retirement|unions?|collective bargaining|unemployment)\b"),
    "housing": ("Housing", set(), NO_SUBJECTS, r"\b(housing|landlords?|tenants?|rent\w*|evictions?|homeowners?|manufactured homes?)\b"),
    "ag": ("Agriculture and natural resources", set(), NO_SUBJECTS, r"\b(agricultur\w*|farm\w*|livestock|crops?|fish\w*|wildlife|hunting|forest\w*|animals?|grain|soil)\b"),
    "gov": ("Elections and government", set(), NO_SUBJECTS, r"\b(elections?|voters?|voting|ballots?|campaigns?|ethics|lobby\w*|public records|open meetings|state agenc\w*|general assembly|administrative rules?)\b"),
    "biz": ("Business and consumers", set(), NO_SUBJECTS, r"\b(consumers?|business\w*|insurance|insurers?|banks?|banking|financial|licens\w*|alcohol\w*|gambling|wagering|commerce|economic development)\b"),
    "const": ("Constitutional amendments", set(), NO_SUBJECTS, ""),
}
# Committees (both houses, both General Assemblies) -> topic, for committees with one main subject. Appropriations, Ways
# and Means (taxes, below), Judiciary, State Government (elections and agencies: "gov"), Government Oversight,
# Administration and Rules and Ethics give none of their own except as listed.
COMMITTEE_TOPICS = {
    "Agriculture": "ag", "Commerce": "biz", "Economic Growth and Technology": "biz", "Technology": "biz",
    "Education": "edu", "Higher Education": "edu", "Education Reform": "edu",
    "Environmental Protection": "env", "Natural Resources": "env", "Natural Resources and Environment": "env",
    "Health and Human Services": "health", "Labor and Workforce": "labor", "Workforce": "labor",
    "Local Government": "local", "Public Safety": "safety", "State Government": "gov", "Transportation": "transp",
    "Veterans Affairs": "human", "Ways and Means": "tax",
}
TOPIC_WORDS = {k: re.compile(v[3], re.I) for k, v in TOPICS.items() if v[3]}

COUNTIES = []
DISTRICTS_PATH = os.path.join(DATA, "district_counties.json")
TOWNS_PATH = os.path.join(DATA, "district_towns.json")

_NAMING = re.compile(r"\b(?:designat\w*|nam\w*|renam\w*)\b.*\b(?:bridges?|highways?|roads?|interchanges?|memorial|buildings?|parks?)\b|"
                     r"\bofficial state (?:fish|horse|bird|flower|rock|tree|insect|song)\b", re.I)
NARROW_KINDS = ["", "naming"]


def narrow_kind(title, desc=""):
    """Bills naming a road, building or state symbol. (Iowa's Constitution bars local and special laws, Art. III, sec.
    30, so no bill is marked "place".)"""
    return "naming" if _NAMING.search(title or "") and len(title or "") < 160 else ""


# Governors and the day each took office: Kim Reynolds (R) since May 24, 2017 (Terry Branstad before her). Reynolds didn't
# run in 2026; Rob Sand (D), elected November 3, 2026, takes office in January 2027 (the inauguration day wasn't announced
# in November): add him then.
GOVERNORS = [("Branstad", "2011-01-14"), ("Reynolds", "2017-05-24"), ("Sand", "2027-01-12")]  # governor-elect: in office from that day (governors.py)
GOV_SINCE = GOVERNORS[-1][1]


def governor_on(day):
    who = GOVERNORS[0][0]
    for name, start in GOVERNORS:
        if day >= start:
            who = name
    return who


# ---- What's changing: subjects whose share of bills changed most between 2023-24 and 2025-26, picked by hand from an
# automatic phrase scan and checked against samples of the bills matched (notes/trends.md). Only two sessions are shown,
# so only the clearest shifts. Matched on title and summary.
TRENDS = [
    ("rise", "Artificial intelligence", r"(?i:artificial intelligence|automated decision|algorithmic|deepfake|deep fake|synthetic media|\bgenerative\b|chatbot)|\bAI\b", False),
    ("spike", "Gender identity", r"transgender|gender identity|gender-affirming|gender transition|biological sex|gender dysphoria", True),
    ("spike", "Cybersecurity", r"cybersecurity|cyber security|ransomware|cyberattack", True),
]
# Old wording -> new wording, for the same thing.
WORDING = [
    (("“Medicaid”", r"medicaid"), ("“medical assistance”", r"medical assistance"),
     "Iowa law calls Medicaid the medical assistance program; in 2025–26 bill titles began using that name."),
]
