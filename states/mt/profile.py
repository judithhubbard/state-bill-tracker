"""Montana: the settings and wording that are particular to this state.

build_data.py reads these as P.<name>, with the same names as states/ny/profile.py.
"""
import os, re

DATA = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "mt"))
SITE_DIR = "mt"

STATE_NAME = "Montana"
SITE_NAME = "Montana Bill Tracker"
LEGISLATURE = "Montana Legislature"
TIMEZONE = "America/Denver"
PUBLIC_URL = "https://statebilltracker.org/mt/"
SITE_URL = os.environ.get("SITE_URL", PUBLIC_URL)

# Two-year Legislatures (the 69th is 2025-26), but the Legislature meets in regular session only in the odd year: from
# the first Monday of January (January 2 when that's New Year's Day), at most 90 legislative days, to late April or early
# May (2023: May 2; 2025: April 30). Every bill not passed then dies. A page per Legislature, named by its session's year;
# special sessions are left out.
YEARS = 2
LOWER = "H"
LOWER_NAME = "House"
TITLES = {"S": "Sen.", "H": "Rep."}


def session_of(year):
    return year if year % 2 else year - 1


def legislature_of(session):
    """2025 -> 69 (the 69th Legislature)."""
    return 69 + (session - 2025) // 2


def session_label(session):
    return str(session)


CF_ANALYTICS_TOKEN = ""
GOATCOUNTER_CODE = ""

DELEGATION_NAMES = set()
# The Speaker and the Senate President preside and refer bills to committees. From the Legislature's member list
# (legislators.json "position"), 2026-11-09; the 70th Legislature chooses its own in January 2027.
LEADERS = {"S": ("Matt Regier", "President of the Senate", "him"),
           "H": ("Brandon Ler", "Speaker of the House", "him")}


def delegation(session):
    return {}


# Members whose record in the current system shows a later house or district than the one they held in the session
# (it keeps one record per member, overwritten: senators-elect of 2026 show as senators, two senators as House members).
# Checked 2026-11-09 against the roll calls (which house each one voted in) and Open States' member list.
SEAT_FIX = {2025: {24: "S:41", 59: "H:6", 60: "H:64", 67: "H:68", 77: "H:22", 79: "H:36", 97: "S:9", 99: "H:86",
                   119: "H:18", 134: "H:16", 177: "H:61", 186: "H:28", 293: "H:57"}}

# Topic: (label, committees (unused), official subjects (unused; see SUBJECT_TOPICS), words in the short title).
NO_SUBJECTS = re.compile(r"(?!)")
TOPICS = {
    "env": ("Environment & energy", set(), NO_SUBJECTS, r"\b(environment\w*|climate|emission\w*|renewable|solar|wind|pollut\w*|energy|utilit\w*|electric\w*|coal|carbon|pipelines?|mining|nuclear)\b"),
    "local": ("Local government", set(), NO_SUBJECTS, r"\b(municipal\w*|county|counties|cit(?:y|ies)|towns?|local government\w*|special districts?)\b"),
    "tax": ("Taxes", set(), NO_SUBJECTS, r"\b(tax\w*|revenue)\b"),
    "safety": ("Public safety & courts", set(), NO_SUBJECTS, r"\b(crim\w*|firearm\w*|guns?|police|courts?|judges?|sentenc\w*|prison\w*|jail\w*|felony|misdemeanor|correction\w*|law enforcement|penalt(?:y|ies))\b"),
    "human": ("Human services", set(), NO_SUBJECTS, r"\b(child care|foster|veteran\w*|senior\w*|elderly|disabilit\w*|homeless\w*|public assistance)\b"),
    "health": ("Health & mental health", set(), NO_SUBJECTS, r"\b(health|medical|medicaid|hospital\w*|mental|pharmac\w*|nurs\w*|physician\w*|abortion)\b"),
    "edu": ("Education", set(), NO_SUBJECTS, r"\b(schools?|students?|teachers?|education|college\w*|universit\w*)\b"),
    "transp": ("Transportation", set(), NO_SUBJECTS, r"\b(vehicles?|highways?|roads?|traffic|transit|drivers?|driving|motor|aviation|airports?)\b"),
    "labor": ("Labor & public employees", set(), NO_SUBJECTS, r"\b(wages?|employ\w*|workers?|labor|pensions?|retirement|workforce)\b"),
    "housing": ("Housing", set(), NO_SUBJECTS, r"\b(housing|landlords?|tenants?|rent|eviction\w*)\b"),
    "ag": ("Agriculture & natural resources", set(), NO_SUBJECTS, r"\b(agricultur\w*|farm\w*|livestock|fish\w*|wildlife|hunting|grain|crops?|ranch\w*|water|forest\w*|state lands?)\b"),
    "gov": ("Elections & state government", set(), NO_SUBJECTS, r"\b(elections?|voters?|voting|ballots?|state agenc\w*|ethics|legislat\w*)\b"),
    "biz": ("Business & consumers", set(), NO_SUBJECTS, r"\b(consumers?|business\w*|insurance|banks?|licens\w*|corporat\w*|economic development|gambling|alcohol\w*)\b"),
    # Bills proposing amendments to the Constitution of Montana (tagged by convert.py, from the subject CAP).
    "const": ("Constitutional amendments", set(), NO_SUBJECTS, ""),
}
# The Legislative Services Division's subject codes -> topic (codes without one topic, like Appropriations, State
# Finance or Rule Making, are left out; such bills get topics from their other subjects and title words).
SUBJECT_TOPICS = {
    **dict.fromkeys(["AGR", "LVTK", "FISH", "FOR", "STLA", "WAT", "REC"], "ag"),
    **dict.fromkeys(["ENVP", "ENER", "OIL", "MINE", "UT"], "env"),
    **dict.fromkeys(["CIT", "CITF", "CITO", "CTY", "CTYF", "CTYO", "LG", "LGF", "PLDV"], "local"),
    **dict.fromkeys(["TX", "TXAG", "TXCO", "TXCR", "TXFU", "TXIN", "TXMI", "TXPR", "TXSA", "TXTR", "REVS", "REVL"], "tax"),
    **dict.fromkeys(["CR", "CRP", "CORR", "CORT", "LEN", "GUN", "JUD", "JUR", "EMER", "FIRE", "EVID", "CIV", "REM", "TORT",
                     "LIA", "SGIS"], "safety"),
    **dict.fromkeys(["SOC", "SRC", "DEV", "MIN", "FAM"], "human"),
    **dict.fromkeys(["HLTH", "HLTC", "MENT", "ABOR", "CIG"], "health"),
    **dict.fromkeys(["SCH", "SCHF", "TEA", "COL", "UNIV", "VOED", "LIB"], "edu"),
    **dict.fromkeys(["TRAN", "HWY", "MTRV", "TRAF"], "transp"),
    **dict.fromkeys(["LAB", "WAGE", "WORK", "UNEM", "RETR", "POFF"], "labor"),
    **dict.fromkeys(["HOUS", "LT"], "housing"),
    **dict.fromkeys(["ELEC", "STGO", "LEG", "BAL"], "gov"),
    **dict.fromkeys(["CONS", "CONT", "CORP", "CRED", "FIN", "INS", "PRO", "PROA", "PROE", "PROO", "SEC", "SECT", "TRAD",
                     "ALC", "GAMB", "ECO", "MON", "COM"], "biz"),
}
TOPIC_WORDS = {k: re.compile(v[3], re.I) for k, v in TOPICS.items() if v[3]}

COUNTIES = []
DISTRICTS_PATH = os.path.join(DATA, "district_counties.json")
TOWNS_PATH = os.path.join(DATA, "district_towns.json")

_NAMING = re.compile(r"\b(?:designat\w*|nam\w*)\b.*\b(?:bridge|highway|route|memorial|building|interchange|road)\b", re.I)
NARROW_KINDS = ["", "person", "org", "naming"]


def narrow_kind(title):
    return "naming" if _NAMING.search(title) else ""


# Governors and the day each took office (the first Monday of January after the election).
GOVERNORS = [("Bullock", "2013-01-07"), ("Gianforte", "2021-01-04")]
GOV_SINCE = GOVERNORS[-1][1]


def governor_on(day):
    who = GOVERNORS[0][0]
    for name, start in GOVERNORS:
        if day >= start:
            who = name
    return who


TRENDS = []
WORDING = []
