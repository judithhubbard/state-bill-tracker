"""Nebraska: the settings and wording that are particular to this state.

build_data.py reads these as P.<name>, with the same names as states/ny/profile.py.

Nebraska's Legislature has one house (unicameral since 1937): 49 senators, elected without party labels. The shared code
names houses by letter; Nebraska's only house is "L" (its bills are LB 1, its resolutions LR 1, so a bill number's first
letter is its house, as elsewhere), named "Legislature", and its members are "Sen.". Seats are "L:12" (District 12).
"""
import os, re

DATA = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "ne"))
SITE_DIR = "ne"

STATE_NAME = "Nebraska"
SITE_NAME = "Nebraska Bill Tracker"
LEGISLATURE = "Nebraska Legislature"
TIMEZONE = "America/Chicago"
PUBLIC_URL = "https://statebilltracker.org/ne/"
SITE_URL = os.environ.get("SITE_URL", PUBLIC_URL)

# Two-year Legislatures (the 109th is 2025-26): a 90-legislative-day session in the odd year (January to early June) and
# a 60-day session in the even year (January to mid-April), each from the first Wednesday after the first Monday of
# January. Bills carry over from the first session to the second, and every bill not passed is indefinitely postponed
# when the second session adjourns. A page per Legislature; special sessions (the 108th's of 2024) are left out.
YEARS = 2
# One house: the "lower house" letter the shared code asks for is the only house's. (TITLES keeps an "S" entry because
# build_data.py looks it up; no seat or bill uses it.)
LOWER = "L"
LOWER_NAME = "Legislature"
TITLES = {"S": "Sen.", "L": "Sen."}


def session_of(year):
    return year if year % 2 else year - 1


def legislature_of(session):
    """2025 -> 109 (the 109th Legislature)."""
    return 109 + (session - 2025) // 2


def session_label(session):
    return f"{session}–{str(session + 1)[2:]}"


CF_ANALYTICS_TOKEN = ""
GOATCOUNTER_CODE = ""

DELEGATION_NAMES = set()
# The Speaker, elected by the senators, sets the order of business: which bills reach the floor and when. The Lieutenant
# Governor presides but isn't a senator. From the Legislature's member pages (members.json "speaker"), 2026-11-09; the
# 110th Legislature elects its own Speaker in January 2027.
LEADERS = {"L": ("John Arch", "Speaker of the Legislature", "him")}


def delegation(session):
    return {}


# The last day of each session (the Clerk's journals; the 1st session of the 108th adjourned June 1, 2023). On the second
# session's last day every bill still pending is indefinitely postponed. Add each new session's.
LAST_DAY = {2023: "2023-06-01", 2024: "2024-04-18", 2025: "2025-06-02", 2026: "2026-04-17"}

# Roll-call names that a surname alone can't tie to a seat: "Meyer" in 2023 is Fred Meyer (District 41, appointed after Tom
# Briese left in 2023: Briese votes until June 2023, "Meyer" from January 2024); "Meyer" in 2025-26, before Fred Meyer came
# back to District 41 in January 2026 (after Dan McKeon left; from then the roll calls write "Meyer, F." and "Meyer, G."),
# is Glen Meyer (District 17): 953 of the 960 lists with plain "Meyer" also list McKeon. Checked 2026-11-13.
VOTE_NAME_FIX = {(2023, "Meyer"): "L:41", (2025, "Meyer"): "L:17"}

# Topic: (label, committees (unused; see COMMITTEE_TOPICS), official subjects (unused), words in the title, used when the
# committee gives none).
NO_SUBJECTS = re.compile(r"(?!)")
TOPICS = {
    "env": ("Environment & energy", set(), NO_SUBJECTS, r"\b(environment\w*|pollut\w*|energy|utilit\w*|solar|wind|nuclear|electric\w*|waste|recycl\w*|carbon|power district\w*|pipelines?)\b"),
    "local": ("Local government", set(), NO_SUBJECTS, r"\b(municipal\w*|county|counties|cit(?:y|ies)|villages?|annex\w*|political subdivision\w*|sanitary and improvement)\b"),
    "tax": ("Taxes", set(), NO_SUBJECTS, r"\b(tax\w*|revenue)\b"),
    "safety": ("Public safety & courts", set(), NO_SUBJECTS, r"\b(crim\w*|firearm\w*|guns?|police|law enforcement|courts?|judges?|sentenc\w*|prison\w*|jail\w*|felony|correction\w*|parole|probation|sheriff\w*|offenses?)\b"),
    "human": ("Human services", set(), NO_SUBJECTS, r"\b(child care|foster|adoption\w*|veteran\w*|senior\w*|elderly|disabilit\w*|homeless\w*|public assistance|child welfare)\b"),
    "health": ("Health & mental health", set(), NO_SUBJECTS, r"\b(health|medical|medicaid|hospital\w*|mental|pharmac\w*|nurs\w*|physician\w*|abortion|cannabis)\b"),
    "edu": ("Education", set(), NO_SUBJECTS, r"\b(schools?|students?|teachers?|education\w*|college\w*|universit\w*)\b"),
    "transp": ("Transportation", set(), NO_SUBJECTS, r"\b(vehicles?|highways?|roads?|traffic|drivers?|transportation|airports?|aeronautics|railroads?|telecommunication\w*|broadband)\b"),
    "labor": ("Labor & public employees", set(), NO_SUBJECTS, r"\b(wages?|employees?|employ\w*|workers?|labor|pensions?|retirement)\b"),
    "housing": ("Housing", set(), NO_SUBJECTS, r"\b(housing|landlords?|tenants?|evictions?|homeowners?|rent)\b"),
    "ag": ("Agriculture & natural resources", set(), NO_SUBJECTS, r"\b(agricultur\w*|farm\w*|livestock|cattle|fish\w*|wildlife|hunting|grain|crops?|ranch\w*|water|irrigation|natural resources district\w*)\b"),
    "gov": ("Elections & state government", set(), NO_SUBJECTS, r"\b(elections?|voters?|voting|ballots?|campaign\w*|ethics|open meetings|public records|state agenc\w*|legislat\w*)\b"),
    "biz": ("Business & consumers", set(), NO_SUBJECTS, r"\b(consumers?|business\w*|insurance|banks?|banking|licens\w*|alcohol\w*|liquor|gaming|gambling|lottery|corporat\w*)\b"),
    # Proposed amendments to the Nebraska Constitution (the CA resolutions, tagged by convert.py).
    "const": ("Constitutional amendments", set(), NO_SUBJECTS, ""),
}
# Standing committees (convert.comm_name()) -> topic. Appropriations, Judiciary (mostly courts and crime, kept as
# "safety"), and the Executive Board (the Legislature's own business) are as noted.
COMMITTEE_TOPICS = {
    "Agriculture": "ag", "Banking, Commerce and Insurance": "biz", "Business and Labor": "labor", "Education": "edu",
    "General Affairs": "biz", "Government, Military and Veterans Affairs": "gov", "Health and Human Services": "health",
    "Judiciary": "safety", "Natural Resources": "env", "Nebraska Retirement Systems": "labor", "Revenue": "tax",
    "Transportation and Telecommunications": "transp", "Urban Affairs": "local", "Executive Board": "gov",
}
TOPIC_WORDS = {k: re.compile(v[3], re.I) for k, v in TOPICS.items() if v[3]}

COUNTIES = []
DISTRICTS_PATH = os.path.join(DATA, "district_counties.json")
TOWNS_PATH = os.path.join(DATA, "district_towns.json")

_NAMING = re.compile(r"\b(?:designat\w*|renam\w*|nam(?:es|ing))\b.*\b(?:bridge|highway|route|memorial|building|interchange|road|day|week|month)\b", re.I)
NARROW_KINDS = ["", "person", "org", "naming"]


def narrow_kind(title):
    return "naming" if _NAMING.search(title) else ""


# Governors and the day each took office. Jim Pillen (R) took office January 5, 2023; his term runs to January 2027
# (he ran again in November 2026: if a new governor takes office, add them here and in states/legislatures.json).
GOVERNORS = [("Ricketts", "2015-01-08"), ("Pillen", "2023-01-05")]
GOV_SINCE = GOVERNORS[-1][1]


def governor_on(day):
    who = GOVERNORS[0][0]
    for name, start in GOVERNORS:
        if day >= start:
            who = name
    return who


TRENDS = []
WORDING = []
