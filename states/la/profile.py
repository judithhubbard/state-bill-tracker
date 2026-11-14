"""Louisiana: the settings and wording that are particular to this state.

build_data.py reads these as P.<name>, with the same names as states/ny/profile.py.
"""
import os, re

DATA = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "la"))
SITE_DIR = "la"

STATE_NAME = "Louisiana"
SITE_NAME = "Louisiana Bill Tracker"
LEGISLATURE = "Louisiana Legislature"
TIMEZONE = "America/Chicago"
PUBLIC_URL = "https://statebilltracker.org/la/"
SITE_URL = os.environ.get("SITE_URL", PUBLIC_URL)

# One regular session a year (Constitution, Art. III, sec. 2): in even years a general session (from the second Monday of
# March, 60 legislative days in 85 calendar days), in odd years a fiscal session (from the second Monday of April, 45
# legislative days in 60 calendar days), where each member may introduce only five bills that aren't about money (taxes,
# appropriations, fees, tax exemptions and the like). Bills die when the session ends. A page a year; special
# (extraordinary) sessions are left out.
YEARS = 1
LOWER = "H"
LOWER_NAME = "House"
TITLES = {"S": "Sen.", "H": "Rep."}


def session_of(year):
    return year


def session_kind(session):
    """General sessions (even years) and fiscal sessions (odd years, mostly money bills) are compared only with their own
    kind in the statistics."""
    return "fiscal" if session % 2 else "general"


def session_label(session):
    return f"{session} {session_kind(session)}"


CF_ANALYTICS_TOKEN = ""
GOATCOUNTER_CODE = ""

DELEGATION_NAMES = set()
# Who decides which bills reach each house's floor: the Speaker of the House and the President of the Senate (a senator,
# elected by the Senate). The Senate President comes from the members' pages ("Senate President"); the House's pages name
# no posts, so the Speaker is the one member listed "Ex Officio" on every House standing committee in data/la/committees.json
# (Phillip DeVillier, on all 16; Speaker Pro Tempore Mike Johnson is on 14), as the House's rules make the Speaker. Both
# were elected in January 2024 for the term ending in January 2028.
LEADERS = {"S": ("Cameron Henry", "President of the Senate", "him"),
           "H": ("Phillip DeVillier", "Speaker of the House", "him")}
# "Mr. President" and "Mr. Speaker" in the roll calls, by session.
PRESIDENTS = {2024: "Henry", 2025: "Henry", 2026: "Henry"}
SPEAKERS = {2024: "DeVillier", 2025: "DeVillier", 2026: "DeVillier"}


def delegation(session):
    return {}


# Topic: (label, committees (unused; see COMMITTEE_TOPICS), official subjects (unused; see KEYWORD_TOPICS), words in the
# title, used when neither a committee nor the title's subject keyword gives a topic).
NO_SUBJECTS = re.compile(r"(?!)")
TOPICS = {
    "env": ("Environment & energy", set(), NO_SUBJECTS, r"\b(environment\w*|pollut\w*|energy|utilit\w*|solar|carbon|oil and gas|pipeline\w*|coastal|wetland\w*|landfill\w*|recycl\w*)\b"),
    "local": ("Local government", set(), NO_SUBJECTS, r"\b(municipal\w*|parish|parishes|cities|city of|towns?|village of|police jur\w*)\b"),
    "tax": ("Taxes", set(), NO_SUBJECTS, r"\b(tax\w*|revenue)\b"),
    "safety": ("Public safety & courts", set(), NO_SUBJECTS, r"\b(crim\w*|firearm\w*|police|law enforcement|court\w*|judge\w*|sentenc\w*|prison\w*|jail\w*|felony|corrections|parole|sheriff\w*)\b"),
    "human": ("Human services", set(), NO_SUBJECTS, r"\b(child care|foster|adoption\w*|veteran\w*|senior\w*|elderly|disabilit\w*|homeless\w*|public assistance)\b"),
    "health": ("Health & mental health", set(), NO_SUBJECTS, r"\b(health|medical|medicaid|hospital\w*|mental|pharmac\w*|nurs\w*|physician\w*|abortion)\b"),
    "edu": ("Education", set(), NO_SUBJECTS, r"\b(school\w*|student\w*|teacher\w*|education|college\w*|universit\w*)\b"),
    "transp": ("Transportation", set(), NO_SUBJECTS, r"\b(vehicle\w*|highway\w*|roads?|traffic|driver\w*|transportation|airport\w*)\b"),
    "labor": ("Labor & public employees", set(), NO_SUBJECTS, r"\b(wage\w*|employee\w*|worker\w*|labor|pension\w*|retirement)\b"),
    "housing": ("Housing", set(), NO_SUBJECTS, r"\b(housing|landlord\w*|tenant\w*|eviction\w*|homeowner\w*)\b"),
    "ag": ("Agriculture & natural resources", set(), NO_SUBJECTS, r"\b(agricultur\w*|farm\w*|livestock|fish\w*|wildlife|hunting|forest\w*|timber|seafood|oyster\w*)\b"),
    "gov": ("Elections & state government", set(), NO_SUBJECTS, r"\b(election\w*|voter\w*|voting|ballot\w*|campaign\w*|ethics|open meetings|public records)\b"),
    "biz": ("Business & consumers", set(), NO_SUBJECTS, r"\b(consumer\w*|business\w*|insurance|bank\w*|licens\w*|alcohol\w*|gaming)\b"),
    "const": ("Constitutional amendments", set(), NO_SUBJECTS, ""),
}
# Standing committees (as the bill histories name them, both houses) -> topic, for those with one main subject.
# Appropriations, Finance, Judiciary (House) and Civil Law and Procedure give courts; Appropriations and Finance none.
COMMITTEE_TOPICS = {
    "Administration of Criminal Justice": "safety", "Judiciary": "safety", "Judiciary A": "safety", "Judiciary B": "safety",
    "Judiciary C": "safety", "Civil Law and Procedure": "safety",
    "Agriculture, Forestry, Aquaculture, and Rural Development": "ag",
    "Commerce": "biz", "Commerce, Consumer Protection and International Affairs": "biz", "Insurance": "biz",
    "Education": "edu", "Health and Welfare": "health",
    "House and Governmental Affairs": "gov", "Senate and Governmental Affairs": "gov",
    "Labor and Industrial Relations": "labor", "Retirement": "labor",
    "Municipal, Parochial and Cultural Affairs": "local", "Local and Municipal Affairs": "local",
    "Natural Resources and Environment": "env", "Environmental Quality": "env", "Natural Resources": "env",
    "Transportation, Highways and Public Works": "transp",
    "Ways and Means": "tax", "Revenue and Fiscal Affairs": "tax",
}
# The subject keyword that starts each bill's title ("TAX/AD VALOREM: ...", "MTR VEHICLE/LICEN PLATES: ...") -> topics,
# by the keyword's words. Keywords that say little ("FUNDS/FUNDING", "BOARDS/COMMISSIONS", "SUNSET LAW") give none.
KEYWORD_TOPICS = [
    (r"^APPROPRIATIONS|^CAPITAL OUTLAY|^BUDGET", []),
    (r"RETIRE|PEN/RELIEF|^SCHOOL EMPLOYEES RET|^LABOR|^EMPLOYMENT|^WORKERS|^UNEMPLOYMENT|^WORKFORCE|^CIVIL SERVICE|^PUBLIC EMPLOYEES|^STATE EMPLOYEES|^LOCAL EMPLOYEES|^SUPPLEMENTAL PAY|^OCCUPATIONAL SAFETY", ["labor"]),
    (r"^TAX|^REVENUE|^TOPS$", ["tax"]),
    (r"^CRIM|^CRIME|^COURTS|^JUDGES|^BAIL|^CORR|^PAROLE|^PARDON|^PROBATION|^LAW ENFORCE|^POLICE|^SHERIFFS$|^DISTRICT ATTORNEYS|^WEAPONS|^DWI|^EVIDENCE|^JUVENILE|^DOMESTIC|^CONTROLLED|^CONTROL DANGER|^DRUGS|^THEFT|^TRESPASS|^SEX OFFENSE|^HUMAN TRAFFICKING|^INDIGENT|^PUBLIC DEFENDER|^CLERKS OF COURT|^CORONERS|^JURY|^CIVIL(?! SERVICE)|^LIABILITY|^MALPRACTICE|^ATTORNEYS|^FIRE PROTECT|^EMERGENCY|^HOMELAND|^PUBLIC SFTY|^SAFETY", ["safety"]),
    (r"^HEALTH|^MEDICAID|^MEDICAL|^HOSPITALS|^NURS|^PHARMAC|^PHYSICIAN|^BEHAVIORAL|^MENTAL|^DENT|^ABORTION|^PUBLIC HEALTH|^VACCINE|^DISEASE|^PRESCRIPTION|^SUBSTANCE ABUSE|^EMERGENCY MED|^CHIROPRACT|^OPTOMETRY|^PSYCHOLOG|^SPEECH|^PHYSICAL THERAP|^OCCUPATIONAL THERAP|^DIETITIANS|^SOCIAL WORKER|^COUNSELING|^GENETICS|^NUTRITION|^SANITARY", ["health"]),
    (r"^SCHOOL|^STUDENT|^TEACHER|^EDUCATION|^HIGHER ED|^COLLEGES|^CURRICULA|^EARLY CHILDHOOD|^POSTSECONDARY|^SECONDARY|^SPECIAL EDUCATION|^LIBRARIES", ["edu"]),
    (r"^CHILDREN|^ELDERLY|^COUNCILS ON AGING|^VETERANS|^HOMELESS|^PUBLIC ASSISTANCE|^SNAP|^TANF|^WELFARE|^HUMAN DEVELOPMENT|^WOMEN|^MILITARY", ["human"]),
    (r"^MTR VEHICLE|^MOTOR|^HIGHWAYS|^ROADS|^TRAFFIC|^TRANSPORTATION|^AIRCRAFT|^BRIDGES|^RAILROADS|^PUBLIC TRANSPORT|^MULTIMODAL|^PORTS|^BOATS|^WATERWAYS", ["transp"]),
    (r"^HOUSING|^LANDLORD|^BLIGHTED|^PROPERTY/VACANT|^MORTGAGES|^REAL ESTATE|^BUILDING CODES|^PLANNING", ["housing"]),
    (r"^AGRICULTUR|^FARMING|^FORESTRY|^HORTICULTURE|^DAIRY|^FISH|^SEAFOOD|^WILDLIFE|^WILD REFUGES|^HUNT|^ANIMALS|^PESTICIDES|^CONSERVATION|^FOOD SAFETY", ["ag"]),
    (r"^ENERGY|^ENVIRONMENT|^UTILIT|^MINERALS|^PETROLEUM|^FUELS|^COASTAL|^WATER|^LEVEES|^FLOOD|^SEWERAGE|^HAZARDOUS|^NATURAL RESOURCES|^PUBLIC SERVICE COMN", ["env"]),
    (r"^ELECTION|^VOTING|^VOTERS|^CAMPAIGN|^ETHICS|^LOBBYING|^PUBLIC RECORDS|^PUBLIC MEETINGS|^LEGISLA|^GOVERNOR|^SECRETARY OF STATE|^SECY OF STATE|^STATE AGENCIES|^STATE DEPARTMENT|^ADMINISTRATIVE|^REAPPORTIONMENT|^REGISTRAR|^POLITICAL|^CONGRESS|^ATTORNEY GENERAL|^TREASURER|^STATE TREASURER|^STATE OFFICIALS|^ELECTED OFFICIALS|^PROCUREMENT|^PUBLIC CONTRACT|^PUBLIC PRINTING|^OFFICIAL JOURNALS|^SENATE$|^GOVERNMENT|^INFORMATION TECHNOLOGY", ["gov"]),
    (r"^LOCAL|^MUNICIPAL|^PARISH|^DISTRICTS/|^SPECIAL DISTRICTS|^LOCAL AGENCIES|^LOCAL GOVT|^LOCAL FINANCE|^POLICE/LOCAL|^POLICE/MUNICIPAL|^CIVIL SERVICE/FIRE", ["local"]),
    (r"^INSURANCE|^INSURERS|^BANKS|^FINANCIAL|^CREDIT|^LOANS|^LOAN|^COMMERC|^CONSUMERS|^CONTRACTORS|^CONTRACTS|^CORPORATIONS|^SMALL BUSINESS|^ALCOHOLIC|^GAMING|^GAMBLING|^LOTTER|^RACING|^HORSE RACING|^AMUSEMENT|^COSMETOLOGY|^BARBERS|^ESTHETICIANS|^PLUMBERS|^ARCHITECTS|^ACCOUNTANTS|^SURVEYORS|^INTERIOR DESIGNERS|^PRIVATE|^LICENSING|^FEES/LICENSES|^SECURITIES|^ADVERTISING|^TOBACCO|^TELECOMMUNICATIONS|^TELEVISION|^TRADEMARKS|^ECONOMIC DEVELOP|^TOURISM|^NOTARIES|^SECONDHAND|^HEARING AID|^WEIGHTS|^AUTOMOBILE INSURANCE|^PROPERTY INSURANCE|^FIRE/CASUALTY|^SELF INSURANCE|^GROUP BENEFITS", ["biz"]),
    (r"^CONSTITUTION", ["const"]),
]
KEYWORD_RULES = [(re.compile(rx), tps) for rx, tps in KEYWORD_TOPICS]
TOPIC_WORDS = {k: re.compile(v[3], re.I) for k, v in TOPICS.items() if v[3]}


def keyword_topics(keyword):
    out = []
    for rx, tps in KEYWORD_RULES:
        if rx.search(keyword or ""):
            out += [t for t in tps if t not in out]
            if tps == [] and not out:
                return []
    return out


COUNTIES = []
DISTRICTS_PATH = os.path.join(DATA, "district_counties.json")
TOWNS_PATH = os.path.join(DATA, "district_towns.json")

_NAMING = re.compile(r"\b(?:designat\w*|nam\w*|renam\w*)\b.*\b(?:bridge|interchange|highway|route|memorial|building|park|road|portion\w*)\b|\bmemorial (?:highway|bridge|interchange|road)\b", re.I)
NARROW_KINDS = ["", "person", "org", "naming"]


def narrow_kind(title, keyword="", local=False):
    """"naming" for a road or building named for someone; "person" for paying a judgment against the state
    (APPROPRIATIONS/JUDGMENT); "place" for a local or special bill (one that needed a published notice of intent:
    Constitution, Art. III, sec. 13; retirement bills need a notice too and aren't local)."""
    if _NAMING.search(title or ""):
        return "naming"
    if re.match(r"APPROPRIATIONS/JUDGMENT", keyword or ""):
        return "person"
    if local and not re.search(r"RETIRE|PEN/RELIEF", keyword or ""):
        return "place"
    return ""


# Governors and the day each took office. Jeff Landry's term runs to January 2028.
GOVERNORS = [("Edwards", "2016-01-11"), ("Landry", "2024-01-08")]
GOV_SINCE = GOVERNORS[-1][1]


def governor_on(day):
    who = GOVERNORS[0][0]
    for name, start in GOVERNORS:
        if day >= start:
            who = name
    return who


TRENDS = []
WORDING = []
