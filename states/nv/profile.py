"""Nevada: the settings and wording that are particular to this state.

build_data.py reads these as P.<name>, with the same names as states/ny/profile.py.
"""
import os, re

DATA = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "nv"))
SITE_DIR = "nv"

STATE_NAME = "Nevada"
SITE_NAME = "Nevada Bill Tracker"
LEGISLATURE = "Nevada Legislature"
TIMEZONE = "America/Los_Angeles"
PUBLIC_URL = "https://statebilltracker.org/nv/"
SITE_URL = os.environ.get("SITE_URL", PUBLIC_URL)

# The Legislature meets in regular session only in odd years: 120 days from the first Monday of February (the 82nd
# session was 2023, the 83rd 2025, the 84th 2027). Bills not passed die when it adjourns; a bill vetoed after adjournment
# goes back to the next regular session, which can override the veto. One page per session, labelled with both years
# (2025–26), since nothing meets in the even year but special sessions (left out).
YEARS = 2
LOWER = "A"
LOWER_NAME = "Assembly"
TITLES = {"S": "Sen.", "A": "Asm."}


def session_of(year):
    return year if year % 2 else year - 1


def number_of(session):
    """2025 -> 83 (the 83rd session)."""
    return 83 + (session - 2025) // 2


def session_code(session):
    """2025 -> "83rd2025", NELIS's name for the session."""
    n = number_of(session)
    suffix = "th" if 10 < n % 100 < 14 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}{session}"


def session_label(session):
    return f"{session}–{str(session + 1)[2:]}"


CF_ANALYTICS_TOKEN = ""
GOATCOUNTER_CODE = ""

DELEGATION_NAMES = set()
# The Speaker leads the Assembly; the Lieutenant Governor presides over the Senate (not a senator), and the Majority
# Leader runs it. From the 83rd session's member list (members.json, "post"), 2026-11-09. The 84th session's leaders are
# chosen when it organizes (the members-elect's list still shows 2025's posts): update this then.
LEADERS = {"S": ("Nicole J. Cannizzaro", "Senate Majority Leader", "her"),
           "A": ("Steve Yeager", "Speaker of the Assembly", "him")}


def delegation(session):
    return {}


# Topic: (label, committees (unused; see COMMITTEE_TOPICS), official subjects (unused), title words).
NO_SUBJECTS = re.compile(r"(?!)")
TOPICS = {
    "env": ("Environment & energy", set(), NO_SUBJECTS, r"\b(environment\w*|climate|emission\w*|renewable|solar|geothermal|pollut\w*|energy|utilit\w*|electric\w*|natural gas|carbon|recycl\w*|air quality|mining)\b"),
    "local": ("Local government", set(), NO_SUBJECTS, r"\b(municipal\w*|county|counties|cit(?:y|ies)|towns?|local government\w*|land use|zoning|redevelopment)\b"),
    "tax": ("Taxes", set(), NO_SUBJECTS, r"\b(tax\w*|revenue)\b"),
    "safety": ("Public safety & courts", set(), NO_SUBJECTS, r"\b(crim\w*|firearm\w*|guns?|police|peace officers?|courts?|sentenc\w*|prison\w*|jail\w*|felony|misdemeanor|correction\w*|offenders?|law enforcement|juvenile justice)\b"),
    "human": ("Human services", set(), NO_SUBJECTS, r"\b(child care|child welfare|foster|veteran\w*|seniors?|older persons|elderly|disabilit\w*|homeless\w*|public assistance|welfare|adoption|guardian\w*)\b"),
    "health": ("Health & mental health", set(), NO_SUBJECTS, r"\b(health|medical|medicaid|hospital\w*|mental|pharmac\w*|nurs\w*|physician\w*|abortion|behavioral|reproductive)\b"),
    "edu": ("Education", set(), NO_SUBJECTS, r"\b(schools?|students?|pupils?|teachers?|education|college\w*|universit\w*|educators?)\b"),
    "transp": ("Transportation", set(), NO_SUBJECTS, r"\b(vehicles?|highways?|roads?|traffic|transit|drivers?|driving|motor|aviation|airports?|transportation)\b"),
    "labor": ("Labor & public employees", set(), NO_SUBJECTS, r"\b(wages?|employ\w*|workers?|labor|pensions?|retirement|workforce|unemployment|collective bargaining|industrial insurance)\b"),
    "housing": ("Housing", set(), NO_SUBJECTS, r"\b(housing|landlords?|tenants?|rent\w*|eviction\w*|manufactured homes?|common-interest|homeowners?)\b"),
    "ag": ("Agriculture & natural resources", set(), NO_SUBJECTS, r"\b(agricultur\w*|farm\w*|livestock|fish\w*|wildlife|hunting|crops?|ranch\w*|water|public lands|forest\w*|animals?)\b"),
    "gov": ("Elections & state government", set(), NO_SUBJECTS, r"\b(elections?|voters?|voting|ballots?|state agenc\w*|ethics|public records|open meeting|Legislature|governmental administration)\b"),
    "biz": ("Business & consumers", set(), NO_SUBJECTS, r"\b(consumers?|business\w*|insurance|banks?|banking|licens\w*|corporat\w*|economic development|gaming|alcohol\w*|cannabis|trade practices|contractors?)\b"),
    # Joint resolutions proposing amendments to the Nevada Constitution (tagged by convert.py, not by words).
    "const": ("Constitutional amendments", set(), NO_SUBJECTS, ""),
}
# Standing committee names (either house) -> topic, for committees with one subject. Ways and Means (Assembly) and
# Finance (Senate) take any bill that spends money, Government Affairs and Legislative Operations and Elections several
# subjects; their bills get topics from the bill draft's NRS title and words.
COMMITTEE_TOPICS = {
    "Commerce and Labor": "biz", "Education": "edu", "Growth and Infrastructure": "transp",
    "Health and Human Services": "health", "Judiciary": "safety", "Legislative Operations and Elections": "gov",
    "Natural Resources": "ag", "Revenue": "tax", "Revenue and Economic Development": "tax",
}
# The bill draft request's number names the title of the Nevada Revised Statutes the bill amends: "(BDR 52-503)" is
# Title 52, Trade Regulations and Practices. Titles with one subject -> topic ("S" is a law outside the NRS, "C" a
# constitutional amendment, "R" a resolution: none).
NRS_TOPICS = {
    1: "safety", 2: "safety", 3: "safety", 4: "safety", 5: "safety", 14: "safety", 15: "safety", 16: "safety",
    36: "safety", 42: "safety",
    7: "biz", 8: "biz", 41: "biz", 52: "biz", 54: "biz", 55: "biz", 56: "biz", 57: "biz", 59: "biz",
    10: "housing", 25: "housing", 11: "human", 13: "human", 37: "human", 38: "human",
    17: "gov", 18: "gov", 19: "gov", 24: "gov", 27: "gov", 31: "gov",
    20: "local", 21: "local", 22: "local", 23: "labor", 53: "labor", 32: "tax", 34: "edu",
    35: "transp", 43: "transp", 44: "transp", 39: "health", 40: "health",
    45: "ag", 47: "ag", 48: "ag", 49: "ag", 50: "ag", 51: "ag", 26: "ag", 46: "env", 58: "env",
}
TOPIC_WORDS = {k: re.compile(v[3], re.I) for k, v in TOPICS.items() if v[3]}

COUNTIES = []
DISTRICTS_PATH = os.path.join(DATA, "district_counties.json")
TOWNS_PATH = os.path.join(DATA, "district_towns.json")

_NAMING = re.compile(r"\b(?:designat\w*|renam\w*|nam(?:es|ing))\b.*\b(?:bridge|highway|route|memorial|building|interchange|road|day|week|month)\b", re.I)
NARROW_KINDS = ["", "person", "org", "naming"]


def narrow_kind(title):
    return "naming" if _NAMING.search(title) else ""


# Governors and the day each took office (the first Monday of January after the election). Joe Lombardo (R) took office
# January 2, 2023, and ran again in November 2026: if a new governor takes office January 4, 2027, add them here and in
# states/legislatures.json.
GOVERNORS = [("Sisolak", "2019-01-07"), ("Lombardo", "2023-01-02")]
GOV_SINCE = GOVERNORS[-1][1]


def governor_on(day):
    who = GOVERNORS[0][0]
    for name, start in GOVERNORS:
        if day >= start:
            who = name
    return who


TRENDS = []
WORDING = []
