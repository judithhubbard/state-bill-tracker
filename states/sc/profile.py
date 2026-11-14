"""South Carolina: the settings and wording that are particular to this state.

build_data.py reads these as P.<name>, with the same names as states/ny/profile.py.
"""
import os, re

DATA = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "sc"))
SITE_DIR = "sc"

STATE_NAME = "South Carolina"
SITE_NAME = "South Carolina Bill Tracker"
LEGISLATURE = "South Carolina General Assembly"
TIMEZONE = "America/New_York"
PUBLIC_URL = "https://statebilltracker.org/sc/"
SITE_URL = os.environ.get("SITE_URL", PUBLIC_URL)

# Two-year General Assemblies (the 126th is 2025-26). Each year's session opens the second Tuesday of January and
# adjourns sine die by law on the second Thursday of May (S.C. Code 2-1-180); a sine die resolution lets the houses come
# back later for vetoes, conference reports and the budget (June, and in 2026 August). Bills not finished in the first
# year carry over to the second, with the same numbers: one page per General Assembly.
YEARS = 2
LOWER = "H"
LOWER_NAME = "House"
TITLES = {"S": "Sen.", "H": "Rep."}


def session_of(year):
    return year if year % 2 else year - 1


def assembly_of(session):
    """2025 -> 126 (the 126th General Assembly)."""
    return 126 + (session - 2025) // 2


def session_label(session):
    return f"{session}–{str(session + 1)[2:]}"


CF_ANALYTICS_TOKEN = ""
GOATCOUNTER_CODE = ""

DELEGATION_NAMES = set()
# The Speaker leads the House; the Senate elects its own President from among the senators (since 2019 the Lieutenant
# Governor no longer presides). From the members' pages (data/sc/members/), 2026-11-09; the General Assembly elected in
# November 2026 (the House, all 124 seats; the Senate's terms run to 2028) organizes in December 2026 and January 2027.
LEADERS = {"S": ("Thomas C. Alexander", "President of the Senate", "him"),
           "H": ("G. Murrell Smith, Jr.", "Speaker of the House", "him")}


def delegation(session):
    return {}


# Topic: (label, committees (unused; see COMMITTEE_TOPICS), official subjects (unused), words in the subject line and
# official title, used alongside the committees).
NO_SUBJECTS = re.compile(r"(?!)")
TOPICS = {
    "env": ("Environment & energy", set(), NO_SUBJECTS, r"\b(environment\w*|climate|emission\w*|renewable|solar|pollut\w*|energy|utilit\w*|electric\w*|natural gas|nuclear|coastal|beach\w*|recycl\w*|solid waste|landfill\w*|stormwater|DHEC|DES|conservation)\b"),
    "local": ("Local government", set(), NO_SUBJECTS, r"\b(municipal\w*|county|counties|cit(?:y|ies)|towns?|special purpose district|public service district|local government\w*|annex\w*|zoning|land use)\b"),
    "tax": ("Taxes", set(), NO_SUBJECTS, r"\b(tax\w*|revenue|homestead exemption|millage|assessment ratio)\b"),
    "safety": ("Public safety & courts", set(), NO_SUBJECTS, r"\b(crim\w*|firearm\w*|guns?|weapons?|police|courts?|judges?|judicial|sentenc\w*|prison\w*|jail\w*|felony|misdemeanor|corrections|law enforcement|offenses?|theft|assault|fentanyl|trafficking|bail|bond hearing|solicitor\w*)\b"),
    "human": ("Human services", set(), NO_SUBJECTS, r"\b(child care|foster|adoption|veteran\w*|seniors?|elderly|disabilit\w*|homeless\w*|public assistance|social services|guardians? ad litem|child support|vulnerable adults?)\b"),
    "health": ("Health & mental health", set(), NO_SUBJECTS, r"\b(health|medical|medicaid|hospital\w*|mental|pharmac\w*|nurs\w*|physician\w*|abortion|behavioral|opioid\w*|drugs?|dental|dentist\w*|insulin|vaccin\w*)\b"),
    "edu": ("Education", set(), NO_SUBJECTS, r"\b(schools?|students?|teachers?|education\w*|college\w*|universit\w*|educators?|scholarships?|tuition|school district\w*)\b"),
    "transp": ("Transportation", set(), NO_SUBJECTS, r"\b(vehicles?|highways?|roads?|traffic|transit|drivers?|driving|motor|bridges?|transportation|DOT|DMV|aviation|airports?|ports?)\b"),
    "labor": ("Labor & public employees", set(), NO_SUBJECTS, r"\b(wages?|employ\w*|workers?|labor|pensions?|retirement|workforce|unemployment|workers' compensation)\b"),
    "housing": ("Housing", set(), NO_SUBJECTS, r"\b(housing|landlords?|tenants?|rent\w*|eviction\w*|manufactured homes?|homeowners?'? associations?|mortgage\w*)\b"),
    "ag": ("Agriculture & natural resources", set(), NO_SUBJECTS, r"\b(agricultur\w*|farm\w*|livestock|fish\w*|wildlife|hunt\w*|crops?|poultry|shellfish|forest\w*|timber|game|deer|hemp|natural resources)\b"),
    "gov": ("Elections & state government", set(), NO_SUBJECTS, r"\b(elections?|voters?|voting|ballots?|primar(?:y|ies)|state agenc\w*|ethics|freedom of information|FOIA|General Assembly|regulations?|procurement|state employees?)\b"),
    "biz": ("Business & consumers", set(), NO_SUBJECTS, r"\b(consumers?|business\w*|insurance|insurers?|banks?|banking|licens\w*|corporat\w*|economic development|gaming|gambling|alcohol\w*|beer|wine|liquor|cannabis|marijuana|contractors?|real estate)\b"),
    # Joint resolutions proposing an amendment to the South Carolina Constitution (tagged by convert.py, not by words).
    "const": ("Constitutional amendments", set(), NO_SUBJECTS, ""),
}
# Committee names (either house) -> topic, for committees with one subject. The House's Ways and Means,
# Agriculture/Natural Resources/Environmental Affairs, Education and Public Works (schools and highways) and Medical,
# Military, Public and Municipal Affairs, and the Senate's Finance, take bills on several subjects: theirs get topics
# from their titles.
COMMITTEE_TOPICS = {
    "Judiciary": "safety", "Labor, Commerce and Industry": "biz", "Banking and Insurance": "biz",
    "Corrections and Penology": "safety", "Education": "edu", "Family and Veterans' Services": "human",
    "Medical Affairs": "health", "Transportation": "transp", "Agriculture and Natural Resources": "ag",
    "Fish, Game and Forestry": "ag", "Regulations and Administrative Procedures": "gov",
}
TOPIC_WORDS = {k: re.compile(v[3], re.I) for k, v in TOPICS.items() if v[3]}
# Transportation's and the environment's acronyms ("DOT", "DES") are matched in capitals only, so "dot" and "des" in
# other words' places don't count: these two are case-sensitive, with each word's first letter either way.
TOPIC_WORDS["transp"] = re.compile(r"\b(?:[Vv]ehicles?|[Hh]ighways?|[Rr]oads?|[Tt]raffic|[Tt]ransit|[Dd]rivers?|[Dd]riving|[Mm]otor|[Bb]ridges?|[Tt]ransportation|DOT|DMV|[Aa]viation|[Aa]irports?|[Pp]orts? [Aa]uthority)\b")
TOPIC_WORDS["env"] = re.compile(r"\b(?:[Ee]nvironment\w*|[Cc]limate|[Ee]mission\w*|[Rr]enewable|[Ss]olar|[Pp]ollut\w*|[Ee]nergy|[Uu]tilit\w*|[Ee]lectric\w*|[Nn]atural [Gg]as|[Nn]uclear|[Cc]oastal|[Bb]each\w*|[Rr]ecycl\w*|[Ss]olid [Ww]aste|[Ll]andfill\w*|[Ss]tormwater|DHEC|DES|[Cc]onservation)\b")

COUNTY_NAMES = ["Abbeville", "Aiken", "Allendale", "Anderson", "Bamberg", "Barnwell", "Beaufort", "Berkeley", "Calhoun",
                "Charleston", "Cherokee", "Chester", "Chesterfield", "Clarendon", "Colleton", "Darlington", "Dillon",
                "Dorchester", "Edgefield", "Fairfield", "Florence", "Georgetown", "Greenville", "Greenwood", "Hampton",
                "Horry", "Jasper", "Kershaw", "Lancaster", "Laurens", "Lee", "Lexington", "McCormick", "Marion",
                "Marlboro", "Newberry", "Oconee", "Orangeburg", "Pickens", "Richland", "Saluda", "Spartanburg", "Sumter",
                "Union", "Williamsburg", "York"]
COUNTIES = []
DISTRICTS_PATH = os.path.join(DATA, "district_counties.json")
TOWNS_PATH = os.path.join(DATA, "district_towns.json")

# Local legislation: bills for one county, city, school district or special purpose district. Most go to the county's
# legislative delegation instead of a standing committee (convert.py marks those); others amend a local act ("AN ACT TO
# AMEND ACT 470 OF 2000 ... ROCK HILL SCHOOL DISTRICT 3 IN YORK COUNTY") rather than the Code of Laws.
_COUNTY = "|".join(n.upper() for n in COUNTY_NAMES)
_LOCAL_ACT = re.compile(rf"^\W*(?:A BILL|AN ACT|A JOINT RESOLUTION) TO (?:AMEND (?:SECTIONS? [\d, AND]+ OF )?ACT (?:NO\. )?\d+ OF \d{{4}}|"
                        rf"(?:PROVIDE|ESTABLISH|CREATE|ABOLISH|DISSOLVE|CONVEY|EXEMPT|REPEAL ACT)\b.*?\b(?:{_COUNTY}) COUNTY\b)", re.I)
_PLACE_NAMED = re.compile(rf"\b(?:{_COUNTY}) COUNTY\b|\b(?:CITY|TOWN) OF [A-Z]+\b|\bSCHOOL DISTRICT\b|\bPUBLIC SERVICE DISTRICT\b|\bWATER AND SEWER", re.I)
_NAMING = re.compile(r"\b(?:designat\w*|nam\w*|renam\w*)\b.*\b(?:bridge|interchange|highway|road|route|memorial|building|park)\b", re.I)
NARROW_KINDS = ["", "place", "person", "org", "naming"]


def narrow_kind(title, delegation=False):
    """"place" for a bill sent to a county delegation, or one amending a local act that names its place; "naming" for a
    road or bridge naming."""
    t = title or ""
    if delegation or ("CODE OF LAWS" not in t.upper() and _LOCAL_ACT.search(t) and _PLACE_NAMED.search(t)):
        return "place"
    return "naming" if _NAMING.search(t) else ""


# Governors and the day each took office. Henry McMaster (R) took over when Nikki Haley resigned (January 24, 2017) and
# was elected in 2018 and 2022; he is term-limited. The governor elected in November 2026 takes office in January 2027:
# add them here and in states/legislatures.json.
GOVERNORS = [("Haley", "2011-01-12"), ("McMaster", "2017-01-24")]
GOV_SINCE = GOVERNORS[-1][1]


def governor_on(day):
    who = GOVERNORS[0][0]
    for name, start in GOVERNORS:
        if day >= start:
            who = name
    return who


TRENDS = []
WORDING = []
