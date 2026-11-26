"""District of Columbia: the settings and wording that are particular to the District.

build_data.py reads these as P.<name>, with the same names as states/ny/profile.py.

The Council of the District of Columbia has one house of 13 members: a Councilmember for each of the 8 wards and 5 elected
at large (the Chairman among them). The shared code names houses by letter; the Council's is "B" (its bills are numbered
B26-0001, shown here as "B 1" on Council Period 26's page, so a bill number's first letter is its house, as elsewhere),
named "Council", and its members are "Councilmember". Seats are "B:1" to "B:8" (the wards) and "B:9a" to "B:9e" (the
at-large members, district 9, named "At-large" in district_names.json): everyone in the District has their ward's member
and all five at-large members (tracker.html's STATE.atLarge).
"""
import os, re

DATA = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "dc"))
SITE_DIR = "dc"

STATE_NAME = "District of Columbia"
STATE_NAME_IN = "the District of Columbia"  # ("How a bill becomes law in the District of Columbia")
REPS_WORD = "Councilmembers"  # ("Find your Councilmembers")
SITE_NAME = "District of Columbia Bill Tracker"
LEGISLATURE = "Council of the District of Columbia"
TIMEZONE = "America/New_York"
PUBLIC_URL = "https://statebilltracker.org/dc/"
SITE_URL = os.environ.get("SITE_URL", PUBLIC_URL)

# Two-year Council Periods (Council Period 26 is 2025-26), from January 2 of the odd year. The Council meets all year
# (a summer recess in July and August); a bill not enacted by the end of the Council Period dies and has to be introduced
# again. A page per Council Period.
YEARS = 2
# One house: the "lower house" letter the shared code asks for is the Council's. (TITLES keeps an "S" entry because
# build_data.py looks it up; no seat or bill uses it.)
LOWER = "B"
LOWER_NAME = "Council"
TITLES = {"S": "Councilmember", "B": "Councilmember"}


def session_of(year):
    return year if year % 2 else year - 1


def period_of(session):
    """2025 -> 26 (Council Period 26)."""
    return 26 + (session - 2025) // 2


def part_of_number(text, session):
    """A bill named in a legislative note ("Bill 25-131", states/part_of.py) as the session's records write it ("B131"), or
    None when it's another Council Period's."""
    import re
    m = re.match(r"(?:Bill|B) ?(\d+)-0*(\d+)$", text.strip())
    return f"B{m.group(2)}" if m and int(m.group(1)) == period_of(session) else None


def session_label(session):
    return f"{session}–{str(session + 1)[2:]}"


CF_ANALYTICS_TOKEN = ""
GOATCOUNTER_CODE = ""

DELEGATION_NAMES = set()
# The Chairman of the Council, elected at large, presides, refers each bill to a committee and sets the agenda of the
# Council's legislative meetings, and chairs the Committee of the Whole, which takes up every bill before its first reading.
LEADERS = {"B": ("Phil Mendelson", "Chairman of the Council", "him")}


def delegation(session):
    return {}


# Topic: (label, committees (unused; see COMMITTEE_TOPICS), official subjects (unused), words in the title, used when the
# committee gives none).
NO_SUBJECTS = re.compile(r"(?!)")
TOPICS = {
    "env": ("Environment and energy", set(), NO_SUBJECTS, r"\b(environment\w*|climate|pollut\w*|energy|electric\w*|solar|utilit\w*|waste|recycl\w*|plastic\w*|tree\w*|stormwater|green)\b"),
    "local": ("Local government", set(), NO_SUBJECTS, r"\b(advisory neighborhood commission\w*|ANCs?|home rule|street and alley closing|closing of (?:a )?(?:public )?(?:street|alley)|surplus|disposition)\b"),
    "tax": ("Taxes", set(), NO_SUBJECTS, r"\b(tax\w*|revenue|abatement\w*|exemption\w*|homestead)\b"),
    "safety": ("Public safety and courts", set(), NO_SUBJECTS, r"\b(crim\w*|firearm\w*|guns?|police|courts?|sentenc\w*|prison\w*|jail\w*|felon\w*|correction\w*|parole|probation|offense\w*|juvenile\w*|curfew|public safety|fire(?:fighters?| and emergency)?|emergency medical)\b"),
    "human": ("Social services", set(), NO_SUBJECTS, r"\b(child care|foster|adoption\w*|veteran\w*|senior\w*|elderly|disabilit\w*|homeless\w*|public assistance|child welfare|family services)\b"),
    "health": ("Health", set(), NO_SUBJECTS, r"\b(health|medical|medicaid|hospital\w*|mental|pharmac\w*|nurs\w*|physician\w*|abortion|cannabis|drug\w*|opioid\w*)\b"),
    "edu": ("Education", set(), NO_SUBJECTS, r"\b(schools?|students?|teachers?|education\w*|college\w*|universit\w*|charter)\b"),
    "transp": ("Transportation", set(), NO_SUBJECTS, r"\b(vehicles?|traffic|drivers?|transportation|transit|metro|bus(?:es)?|streets?|parking|bicycl\w*|pedestrian\w*|streatery|for-hire)\b"),
    "labor": ("Jobs and workers", set(), NO_SUBJECTS, r"\b(wages?|employees?|employ\w*|workers?|labor|pensions?|retirement|collective bargaining|leave)\b"),
    "housing": ("Housing", set(), NO_SUBJECTS, r"\b(housing|landlords?|tenants?|evictions?|homeowners?|rent\w*|zoning|condominium\w*|apartment\w*)\b"),
    "ag": ("Agriculture and natural resources", set(), NO_SUBJECTS, r"\b(agricultur\w*|farm\w*|urban farm\w*|animals?|wildlife|parks?|rivers?|anacostia)\b"),
    "gov": ("Elections and government", set(), NO_SUBJECTS, r"\b(elections?|voters?|voting|ballots?|campaign\w*|ethics|open meetings|public records|agenc\w*|procurement|contract\w*|council|government)\b"),
    "biz": ("Business and consumers", set(), NO_SUBJECTS, r"\b(consumers?|business\w*|insurance|banks?|banking|licens\w*|alcohol\w*|liquor|gaming|gambling|lottery|sports wagering|corporat\w*|retail\w*|restaurant\w*|economic development)\b"),
    # The District has no constitution to amend; the tag exists because the shared list of topics has it.
    "const": ("Constitutional amendments", set(), NO_SUBJECTS, ""),
}
# The Council's committees (convert.comm_name(): "Health", "Committee of the Whole") -> topic. The Committee of the Whole
# (every member, chaired by the Chairman) takes the budget, the Council's own business and land, and many bills on other
# subjects: no topic of its own. Judiciary and Public Safety is mostly courts and crime ("safety").
COMMITTEE_TOPICS = {
    "Health": "health", "Housing": "housing", "Human Services": "human", "Judiciary and Public Safety": "safety",
    "Transportation and the Environment": "transp", "Public Works and Operations": "gov",
    "Executive Administration and Labor": "labor", "Business and Economic Development": "biz", "Facilities": "gov",
    "Youth Affairs": "edu", "Education": "edu", "Hospital and Health Equity": "health", "Recreation, Libraries and Youth Affairs": "edu",
    "Government Operations and Facilities": "gov", "Labor and Workforce Development": "labor",
    "Public Works and Operations ": "gov",
}
TOPIC_WORDS = {k: re.compile(v[3], re.I) for k, v in TOPICS.items() if v[3]}

COUNTIES = []
DISTRICTS_PATH = os.path.join(DATA, "district_counties.json")
TOWNS_PATH = os.path.join(DATA, "district_towns.json")
DISTRICT_NAMES_PATH = os.path.join(DATA, "district_names.json")
# The at-large members' district (seats B:9a-B:9e): they represent every ward (STATE.atLarge in profile.js).
AT_LARGE = 9

# Bills for one place or one group: street and alley closings, land dispositions and designations for one building or
# square, namings (of a street, a school, a day), and bills for one organization's tax exemption or real property.
_NAMING = re.compile(r"\b(?:designat\w*|renam\w*|nam(?:es|ing))\b.*\b(?:street|way|plaza|park|school|building|day|week|month|recreation center|library|field|bridge)\b|\bDesignation Act\b|\bCommemorative Works\b", re.I)
_PLACE = re.compile(r"\b(?:closing of|street and alley closing|alley closing|transfer of jurisdiction|disposition|lease approval|square\s+\d+|lots?\s+\d+|real property tax exemption|real property tax relief|tax abatement)\b", re.I)
NARROW_KINDS = ["", "person", "org", "naming"]  # ("place" is its own flag: build_data.py)


def narrow_kind(title):
    return "naming" if _NAMING.search(title) else "place" if _PLACE.search(title) else ""


# Mayors and the day each took office (the shared code's "governors": the Mayor signs or vetoes the Council's acts).
# Muriel Bowser took office January 2, 2015. Janeese Lewis George (the Ward 4 Councilmember) was elected Mayor on November 3,
# 2026 and takes office January 2, 2027 (governors.py switches that day; states/legislatures.json's governorNext).
GOVERNORS = [("Gray", "2011-01-02"), ("Bowser", "2015-01-02"), ("Lewis George", "2027-01-02")]
GOV_SINCE = GOVERNORS[-1][1]


def governor_on(day):
    who = GOVERNORS[0][0]
    for name, start in GOVERNORS:
        if day >= start:
            who = name
    return who


# ---- What's changing: none picked yet (two Council Periods only; notes/trends.md describes how they're chosen).
TRENDS = []
WORDING = []
