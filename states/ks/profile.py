"""Kansas: the settings and wording that are particular to this state.

build_data.py reads these as P.<name>, with the same names as states/ny/profile.py.
"""
import os, re

DATA = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "ks"))
SITE_DIR = "ks"

STATE_NAME = "Kansas"
SITE_NAME = "Kansas Bill Tracker"
LEGISLATURE = "Kansas Legislature"
TIMEZONE = "America/Chicago"
PUBLIC_URL = "https://statebilltracker.org/ks/"
SITE_URL = os.environ.get("SITE_URL", PUBLIC_URL)

# Two-year bienniums ("b2025_26"). Each year's session opens the second Monday of January (Constitution, Art. 2, sec. 8);
# the regular session runs to "first adjournment" in late March or early April, and the Legislature comes back for a
# few days in late April for the veto session, then adjourns sine die. Bills not finished in the first year carry over
# to the second with the same numbers: one page per biennium.
YEARS = 2
LOWER = "H"
LOWER_NAME = "House"
TITLES = {"S": "Sen.", "H": "Rep."}


def session_of(year):
    return year if year % 2 else year - 1


def session_label(session):
    return f"{session}–{str(session + 1)[2:]}"


CF_ANALYTICS_TOKEN = ""
GOATCOUNTER_CODE = ""

DELEGATION_NAMES = set()
# The Speaker leads the House; the Senate elects its President from among the senators (the Lieutenant Governor doesn't
# preside). From the API's leadership list (data/ks/2025/leadership.json), 2026-11-13. The House (all 125 seats) was
# elected in November 2026 and organizes in January 2027, with the Senate (its terms run to 2028): update these then.
LEADERS = {"S": ("Ty Masterson", "President of the Senate", "him"),
           "H": ("Daniel Hawkins", "Speaker of the House", "him")}


def delegation(session):
    return {}


# Topic: (label, committees (unused; see COMMITTEE_TOPICS), official subjects (unused), words in the short title, long
# title and the Research Department's keywords, used alongside the committees).
NO_SUBJECTS = re.compile(r"(?!)")
TOPICS = {
    "env": ("Environment & energy", set(), NO_SUBJECTS, r"\b(environment\w*|climate|emission\w*|renewable|solar|wind energy|pollut\w*|energy|utilit\w*|electric\w*|natural gas|nuclear|recycl\w*|solid waste|landfill\w*|water quality|water rights?|groundwater|aquifer|KDHE|conservation|carbon)\b"),
    "local": ("Local government", set(), NO_SUBJECTS, r"\b(municipal\w*|count(?:y|ies)|cit(?:y|ies)|townships?|local government\w*|annex\w*|zoning|land use|fire districts?|drainage districts?|home rule)\b"),
    "tax": ("Taxes", set(), NO_SUBJECTS, r"\b(tax\w*|revenue|property valuation|appraised value|assessed valu\w*|mill levy|homestead)\b"),
    "safety": ("Public safety & courts", set(), NO_SUBJECTS, r"\b(crim\w*|firearm\w*|guns?|weapons?|police|courts?|judges?|judicial|sentenc\w*|prison\w*|jail\w*|felony|misdemeanor|corrections|law enforcement|offenses?|theft|assault|fentanyl|trafficking|bail|bond|prosecut\w*|juvenile|KBI|highway patrol)\b"),
    "human": ("Human services", set(), NO_SUBJECTS, r"\b(child care|foster|adoption|veteran\w*|seniors?|elderly|disabilit\w*|homeless\w*|public assistance|social services|child welfare|children and families|food assistance|SNAP|TANF|welfare|aging)\b"),
    "health": ("Health & mental health", set(), NO_SUBJECTS, r"\b(health|medical|medicaid|KanCare|hospital\w*|mental|pharmac\w*|nurs\w*|physician\w*|abortion|behavioral|opioid\w*|drugs?|dental|dentist\w*|insulin|vaccin\w*|healing arts)\b"),
    "edu": ("Education", set(), NO_SUBJECTS, r"\b(schools?|students?|teachers?|education\w*|college\w*|universit\w*|educators?|scholarships?|tuition|school districts?|board of regents)\b"),
    "transp": ("Transportation", set(), NO_SUBJECTS, r"\b(vehicles?|highways?|roads?|traffic|transit|drivers?|driving|motor|bridges?|transportation|KDOT|aviation|airports?|license plates?|railroads?)\b"),
    "labor": ("Labor & public employees", set(), NO_SUBJECTS, r"\b(wages?|employ\w*|workers?|labor|pensions?|retirement|KPERS|workforce|unemployment|workers compensation|workers' compensation)\b"),
    "housing": ("Housing", set(), NO_SUBJECTS, r"\b(housing|landlords?|tenants?|rent\w*|eviction\w*|manufactured homes?|homeowners?'? associations?|mortgage\w*)\b"),
    "ag": ("Agriculture & natural resources", set(), NO_SUBJECTS, r"\b(agricultur\w*|farm\w*|livestock|fish\w*|wildlife|hunt\w*|crops?|poultry|forest\w*|game|deer|hemp|natural resources|cattle|grain|irrigation|parks?)\b"),
    "gov": ("Elections & state government", set(), NO_SUBJECTS, r"\b(elections?|voters?|voting|ballots?|primar(?:y|ies)|state agenc\w*|ethics|open records|open meetings|legislature|rules and regulations|procurement|state employees?|secretary of state|campaign finance)\b"),
    "biz": ("Business & consumers", set(), NO_SUBJECTS, r"\b(consumers?|business\w*|insurance|insurers?|banks?|banking|credit unions?|licens\w*|corporat\w*|economic development|gaming|gambling|lottery|sports wagering|alcohol\w*|beer|wine|liquor|cereal malt|cannabis|marijuana|contractors?|real estate)\b"),
    # Concurrent resolutions proposing an amendment to the Kansas Constitution (tagged by convert.py, not by words).
    "const": ("Constitutional amendments", set(), NO_SUBJECTS, ""),
}
# Committee names (either house) -> topic, for committees with one subject. Federal and State Affairs, Ways and Means,
# Appropriations, Commerce, Legislative Modernization, Government Efficiency and the joint committees take bills on
# several subjects: theirs get topics from their titles.
COMMITTEE_TOPICS = {
    "Agriculture and Natural Resources": "ag", "Agriculture and Natural Resources Budget": "ag",
    "Assessment and Taxation": "tax", "Taxation": "tax",
    "Commerce, Labor and Economic Development": "labor",
    "Corrections and Juvenile Justice": "safety", "Judiciary": "safety", "Transportation and Public Safety Budget": "safety",
    "Education": "edu", "K-12 Education Budget": "edu", "Higher Education Budget": "edu",
    "Elections": "gov", "Local Government, Transparency and Ethics": "local", "Local Government": "local",
    "Energy, Utilities and Telecommunications": "env", "Utilities": "env", "Water": "env",
    "Financial Institutions and Insurance": "biz", "Insurance": "biz", "Financial Institutions and Pensions": "biz",
    "Health and Human Services": "health", "Public Health and Welfare": "health",
    "Child Welfare and Foster Care": "human", "Welfare Reform": "human", "Social Services Budget": "human",
    "Children and Seniors": "human", "Veterans and Military": "human",
    "Transportation": "transp",
}
TOPIC_WORDS = {k: re.compile(v[3], re.I) for k, v in TOPICS.items() if v[3]}
# Agency names that say nothing about a bill's subject ("the Kansas Department of Health and Environment" on a public
# assistance bill; "the United States Department of Agriculture" on food assistance): taken out before matching words.
AGENCY_NAMES = re.compile(r"\b(?:(?:Kansas )?(?:Department|Secretary) of Health and Environment|KDHE|(?:Secretary of )?(?:United States )?Department of Agriculture|USDA)\b", re.I)

COUNTIES = []
DISTRICTS_PATH = os.path.join(DATA, "district_counties.json")
TOWNS_PATH = os.path.join(DATA, "district_towns.json")

_NAMING = re.compile(r"\b(?:designat\w*|nam\w*|renam\w*)\b.*\b(?:bridge|interchange|highway|road|route|memorial|building)\b", re.I)
NARROW_KINDS = ["", "place", "person", "org", "naming"]


def narrow_kind(title):
    """"naming" for a highway or bridge naming; "person" for a claim against the state for one person."""
    t = title or ""
    if _NAMING.search(t):
        return "naming"
    return ""


# Governors and the day each took office. Laura Kelly (D) since January 14, 2019; she is term-limited. The governor
# elected in November 2026 takes office January 11, 2027 (the second Monday of January): add them here and in
# states/legislatures.json.
GOVERNORS = [("Brownback", "2011-01-10"), ("Colyer", "2018-01-31"), ("Kelly", "2019-01-14")]
GOV_SINCE = GOVERNORS[-1][1]


def governor_on(day):
    who = GOVERNORS[0][0]
    for name, start in GOVERNORS:
        if day >= start:
            who = name
    return who


TRENDS = []
WORDING = []
