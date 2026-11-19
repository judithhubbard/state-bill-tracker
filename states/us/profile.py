"""Congress: the settings and wording that are particular to the federal jurisdiction (/us/).

build_data.py reads these as P.<name>, with the same names as states/ny/profile.py. Congress isn't a state, but the
shared code calls each jurisdiction a state; STATE_NAME is what pages call it.
"""
import os, re

DATA = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "us"))
SITE_DIR = "us"

STATE_NAME = "Congress"
SITE_NAME = "Congress Bill Tracker"
LEGISLATURE = "U.S. Congress"
TIMEZONE = "America/New_York"
PUBLIC_URL = "https://statebilltracker.org/us/"
SITE_URL = os.environ.get("SITE_URL", PUBLIC_URL)

# A page is a two-year Congress, named by its first year: 2025 is the 119th Congress (2025-26). It convenes January 3
# of each odd year (the 20th Amendment), and its bills die when it ends on January 3 two years later.
YEARS = 2
LOWER = "H"
LOWER_NAME = "House"
TITLES = {"S": "Sen.", "H": "Rep."}


def session_of(year):
    return year if year % 2 else year - 1


def congress_of(session):
    """2025 -> 119."""
    return (session - 1789) // 2 + 1


def session_of_congress(congress):
    return 1789 + 2 * (congress - 1)


def session_label(session):
    return f"{session}–{str(session + 1)[2:]}"


CF_ANALYTICS_TOKEN = ""
GOATCOUNTER_CODE = ""

DELEGATION_NAMES = set()
# The Speaker leads the House. The Senate's presiding officer is the Vice President (and the President pro tempore),
# but the Majority Leader decides which bills reach the floor, so he's the Senate's leader here. The 119th Congress
# (2025-26): Speaker Mike Johnson, Senate Majority Leader John Thune. The 120th Congress chooses its own on January 3,
# 2027: update these then (and P.OFFICERS for the record).
LEADERS = {"S": ("John Thune", "Senate Majority Leader", "him"),
           "H": ("Mike Johnson", "Speaker of the House", "him")}
# Leaders already chosen for the next legislature, each in place from the day they take the post (governors.py's
# apply_leaders()); pronouns only where their own official biography gives them, else "them". Checked 2026-11-19.
LEADERS_NEXT = {
    "H": ("Hakeem Jeffries", "Speaker of the House", "them", "2027-01-03"),
}
# Each Congress's leaders, for the record (contacts.py names the current ones only).
OFFICERS = {117: {"S": "Chuck Schumer", "H": "Nancy Pelosi"},
            118: {"S": "Chuck Schumer", "H": "Mike Johnson"},  # Kevin McCarthy was Speaker until October 3, 2023
            119: {"S": "John Thune", "H": "Mike Johnson"}}


def delegation(session):
    return {}


# The 50 states, the District of Columbia and the five territories with a delegate or resident commissioner: postal
# code -> (name, FIPS code). Seat ids use the FIPS code: the Senate's "S:6a"/"S:6b" (California's two senators, a for
# the lower Senate class), the House's "H:612" (California's 12th district: 100 times the FIPS code plus the district;
# a state with one district at large is "H:200" for Alaska). The delegates of DC, Guam, the Virgin Islands, American
# Samoa and the Northern Mariana Islands and Puerto Rico's Resident Commissioner sit in the House but don't vote on
# bills' passage: their seats are "H:1100" and so on, they appear among the House's members, and they don't count
# for the House's party balance (contacts.py marks them "nonvoting").
STATES = {
    "AL": ("Alabama", 1), "AK": ("Alaska", 2), "AZ": ("Arizona", 4), "AR": ("Arkansas", 5), "CA": ("California", 6),
    "CO": ("Colorado", 8), "CT": ("Connecticut", 9), "DE": ("Delaware", 10), "DC": ("District of Columbia", 11),
    "FL": ("Florida", 12), "GA": ("Georgia", 13), "HI": ("Hawaii", 15), "ID": ("Idaho", 16), "IL": ("Illinois", 17),
    "IN": ("Indiana", 18), "IA": ("Iowa", 19), "KS": ("Kansas", 20), "KY": ("Kentucky", 21), "LA": ("Louisiana", 22),
    "ME": ("Maine", 23), "MD": ("Maryland", 24), "MA": ("Massachusetts", 25), "MI": ("Michigan", 26),
    "MN": ("Minnesota", 27), "MS": ("Mississippi", 28), "MO": ("Missouri", 29), "MT": ("Montana", 30),
    "NE": ("Nebraska", 31), "NV": ("Nevada", 32), "NH": ("New Hampshire", 33), "NJ": ("New Jersey", 34),
    "NM": ("New Mexico", 35), "NY": ("New York", 36), "NC": ("North Carolina", 37), "ND": ("North Dakota", 38),
    "OH": ("Ohio", 39), "OK": ("Oklahoma", 40), "OR": ("Oregon", 41), "PA": ("Pennsylvania", 42),
    "RI": ("Rhode Island", 44), "SC": ("South Carolina", 45), "SD": ("South Dakota", 46), "TN": ("Tennessee", 47),
    "TX": ("Texas", 48), "UT": ("Utah", 49), "VT": ("Vermont", 50), "VA": ("Virginia", 51), "WA": ("Washington", 53),
    "WV": ("West Virginia", 54), "WI": ("Wisconsin", 55), "WY": ("Wyoming", 56),
    "AS": ("American Samoa", 60), "GU": ("Guam", 66), "MP": ("Northern Mariana Islands", 69), "PR": ("Puerto Rico", 72),
    "VI": ("Virgin Islands", 78),
}
BY_FIPS = {f: (code, name) for code, (name, f) in STATES.items()}
NONVOTING = {"DC", "AS", "GU", "MP", "PR", "VI"}


def ordinal(n):
    return f"{n}{'th' if 10 <= n % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"


def house_seat(state, district):
    """"CA", 12 -> 612; an at-large seat (district 0, or None) -> 200 for Alaska."""
    return STATES[state][1] * 100 + int(district or 0)


def seat_name(house, number):
    """What a seat is called: "California" (the Senate, by state), "California's 12th" or "Alaska at large" (the House),
    "District of Columbia (delegate)"."""
    if house == "S":
        return BY_FIPS[int(number)][1]
    code, name = BY_FIPS[int(number) // 100]
    d = int(number) % 100
    if code in NONVOTING:
        return f"{name} ({'Resident Commissioner' if code == 'PR' else 'delegate'})"
    return f"{name}'s {ordinal(d)}" if d else f"{name} at large"


def district_names(seats=None):
    """{"S": {"6": "California", ...}, "H": {"612": "California's 12th", ...}}: every state's Senate seat and the House
    seats given (towns.py passes those in its places and those any member of a downloaded Congress held), so a page can
    name any seat its votes or members use."""
    out = {"S": {str(f): name for code, (name, f) in STATES.items() if code not in NONVOTING}, "H": {}}
    for n in sorted(seats or ()):
        out["H"][str(n)] = seat_name("H", n)
    return out


# Topics: the 14 the states share, plus two only Congress needs (defense, and foreign affairs with trade and
# immigration). Each bill's policy area, chosen by the Congressional Research Service, gives its main topic
# (POLICY_TOPICS); words in its title and the CRS's subject terms add others.
NO_SUBJECTS = re.compile(r"(?!)")
TOPICS = {
    "env": ("Environment & energy", set(), NO_SUBJECTS, r"\b(environment\w*|climate|emission\w*|renewable|solar|wind energy|pollut\w*|energy|electric\w*|natural gas|nuclear|recycl\w*|hazardous waste|drinking water|water quality|clean water|PFAS|carbon|oil and gas|pipelines?)\b"),
    "local": ("Local government", set(), NO_SUBJECTS, r"\b(municipal\w*|local governments?|District of Columbia|Puerto Rico|Guam|territor(?:y|ies)|tribal|Indian tribes?|native americans?|Alaska natives?|Native Hawaiians?)\b"),
    "tax": ("Taxes", set(), NO_SUBJECTS, r"\b(tax\w*|internal revenue|tariff\w*|IRS)\b"),
    "safety": ("Public safety & courts", set(), NO_SUBJECTS, r"\b(crim\w*|firearm\w*|guns?|weapons?|police|courts?|judges?|judicial|sentenc\w*|prison\w*|felony|law enforcement|offenses?|fentanyl|trafficking|prosecut\w*|juvenile|FBI|terroris\w*|disaster\w*|FEMA|emergency management)\b"),
    "human": ("Human services", set(), NO_SUBJECTS, r"\b(child care|foster|adoption|veteran\w*|seniors?|elderly|older americans|disabilit\w*|homeless\w*|social security|supplemental security income|SNAP|food assistance|nutrition assistance|TANF|welfare|child support)\b"),
    "health": ("Health & mental health", set(), NO_SUBJECTS, r"\b(health|medical|medicaid|medicare|hospital\w*|mental|pharmac\w*|nurs\w*|physician\w*|abortion|behavioral|opioid\w*|drugs?|dental|insulin|vaccin\w*|disease\w*)\b"),
    "edu": ("Education", set(), NO_SUBJECTS, r"\b(schools?|students?|teachers?|education\w*|college\w*|universit\w*|scholarships?|student loans?|Pell)\b"),
    "transp": ("Transportation", set(), NO_SUBJECTS, r"\b(vehicles?|highways?|roads?|traffic|transit|drivers?|motor carriers?|bridges?|transportation|aviation|airports?|aircraft|railroads?|rail|FAA|ports?|maritime|shipping)\b"),
    "labor": ("Labor & public employees", set(), NO_SUBJECTS, r"\b(wages?|employ\w*|workers?|labor|pensions?|retirement|workforce|unemployment|federal employees?|civil service|unions?)\b"),
    "housing": ("Housing", set(), NO_SUBJECTS, r"\b(housing|landlords?|tenants?|rental|eviction\w*|mortgage\w*|homeowners?|HUD)\b"),
    "ag": ("Agriculture & natural resources", set(), NO_SUBJECTS, r"\b(agricultur\w*|farm\w*|livestock|fish\w*|wildlife|hunt\w*|crops?|forest\w*|national parks?|public lands?|wilderness|grazing|mining|minerals?)\b"),
    "gov": ("Elections & government", set(), NO_SUBJECTS, r"\b(elections?|voters?|voting|ballots?|federal agenc\w*|ethics|inspectors? general|freedom of information|census|postal service|regulations?|campaign finance|Congress)\b"),
    "biz": ("Business & consumers", set(), NO_SUBJECTS, r"\b(consumers?|business\w*|insurance|insurers?|banks?|banking|credit unions?|securities|corporat\w*|economic development|gaming|gambling|alcohol\w*|cannabis|marijuana|small business\w*|telecommunications?|broadband|internet|cryptocurrenc\w*|digital assets?|antitrust)\b"),
    "defense": ("Defense & national security", set(), NO_SUBJECTS, r"\b(armed forces|military|defense|army|navy|air force|marine corps|space force|national guard|service ?members?|national security|intelligence)\b"),
    "foreign": ("Foreign affairs, trade & immigration", set(), NO_SUBJECTS, r"\b(foreign|international|treaty|treaties|embassy|sanctions?|Ukraine|Israel|China|Russia|Iran|Taiwan|immigra\w*|aliens?|asylum|visas?|refugees?|border|deport\w*|exports?|imports?)\b"),
    # Joint resolutions proposing an amendment to the Constitution of the United States (tagged by convert.py).
    "const": ("Constitutional amendments", set(), NO_SUBJECTS, ""),
}
TOPIC_WORDS = {k: re.compile(v[3], re.I) for k, v in TOPICS.items() if v[3]}
# For test/data_check.py: the topics Congress adds to the states' 14, and its own name for "gov".
EXTRA_TOPICS = {"defense", "foreign"}
TOPIC_NAMES = {"gov": "Elections & government"}
# The Congressional Research Service's 32 policy areas (one a bill) -> the main topic. Those left out ("Economics and
# Public Finance": the budget, appropriations; "Arts, Culture, Religion"; "Social Sciences and History"; "Sports and
# Recreation"; "Civil Rights and Liberties, Minority Issues"; "Private Legislation") get topics from their words.
POLICY_TOPICS = {
    "Agriculture and Food": "ag", "Animals": "ag", "Public Lands and Natural Resources": "ag",
    "Water Resources Development": "env", "Environmental Protection": "env", "Energy": "env",
    "Armed Forces and National Security": "defense",
    "International Affairs": "foreign", "Foreign Trade and International Finance": "foreign", "Immigration": "foreign",
    "Commerce": "biz", "Finance and Financial Sector": "biz", "Science, Technology, Communications": "biz",
    "Congress": "gov", "Government Operations and Politics": "gov",
    "Crime and Law Enforcement": "safety", "Law": "safety", "Emergency Management": "safety",
    "Education": "edu", "Families": "human", "Social Welfare": "human", "Health": "health",
    "Housing and Community Development": "housing", "Labor and Employment": "labor", "Taxation": "tax",
    "Transportation and Public Works": "transp", "Native Americans": "local",
    "Geographic Areas, Entities, and Committees": "local",
}

COUNTIES = []
DISTRICTS_PATH = os.path.join(DATA, "district_counties.json")
TOWNS_PATH = os.path.join(DATA, "district_towns.json")
DISTRICT_NAMES_PATH = os.path.join(DATA, "district_names.json")

NARROW_KINDS = ["", "place", "person", "org", "naming"]
_NAMING = re.compile(
    r"\b(?:designate|to name|rename)\b.{0,160}\b(?:post office|postal service|facility|building|courthouse|clinic|"
    r"medical center|outpatient|station|bridge|highway|dam|lake|peak|mountain|trail|wilderness|visitor center|reserve center)\b"
    r"|\bcommemorative coins?\b|\bcongressional gold medals?\b|\bto award (?:a|three|four|five|\w+) congressional gold medals?\b", re.I)


def narrow_kind(title, policy=""):
    """"naming" for a post office, building or landmark named, a commemorative coin or a Congressional Gold Medal;
    "person" for a private bill ("For the relief of ...")."""
    t = title or ""
    if policy == "Private Legislation" or re.match(r"(?:A bill )?for the relief of\b", t, re.I):
        return "person"
    if _NAMING.search(t):
        return "naming"
    return ""


# Presidents and the day each took office. Each Congress's page compares its President's record with earlier ones.
GOVERNORS = [("Obama", "2009-01-20"), ("Trump", "2017-01-20"), ("Biden", "2021-01-20"), ("Trump", "2025-01-20")]
GOV_SINCE = GOVERNORS[-1][1]


def governor_on(day):
    who = GOVERNORS[0][0]
    for name, start in GOVERNORS:
        if day >= start:
            who = name
    return who


TRENDS = []
WORDING = []
