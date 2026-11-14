"""Missouri: the settings and wording that are particular to this state.

build_data.py reads these as P.<name>, with the same names as states/ny/profile.py.
"""
import os, re

DATA = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "mo"))
SITE_DIR = "mo"

STATE_NAME = "Missouri"
SITE_NAME = "Missouri Bill Tracker"
LEGISLATURE = "Missouri General Assembly"
TIMEZONE = "America/Chicago"
PUBLIC_URL = "https://statebilltracker.org/mo/"
SITE_URL = os.environ.get("SITE_URL", PUBLIC_URL)

# A regular session a year, from the first Wednesday after the first Monday of January to May 30 at the latest (bills
# can't pass after 6 p.m. on the first Friday after the second Monday in May); bills die when it ends. The governor acts
# by mid-July, and the veto session is in September. A page a year; extraordinary (special) sessions are left out.
YEARS = 1
LOWER = "H"
LOWER_NAME = "House"
TITLES = {"S": "Sen.", "H": "Rep."}


def session_of(year):
    return year


def session_label(session):
    return str(session)


CF_ANALYTICS_TOKEN = ""
GOATCOUNTER_CODE = ""

DELEGATION_NAMES = set()
# Who decides which bills reach each house's floor: the Speaker (who refers House bills to committees and, through the
# Rules committees and the Majority Floor Leader, schedules them) and the President Pro Tem of the Senate (the Lieutenant
# Governor presides but rarely acts; the Majority Floor Leader sets the Senate's calendar). From the member lists,
# 2026-11-13; the General Assembly elected in November 2026 organizes in January 2027.
LEADERS = {"S": ("Cindy O'Laughlin", "President Pro Tem of the Senate", "her"),
           "H": ("Jonathan Patterson", "Speaker of the House", "him")}


def delegation(session):
    return {}


# Topic: (label, committees (unused; see COMMITTEE_TOPICS), official subjects (unused; see SUBJECT_TOPICS), words in the
# title and summary, used when neither the committees nor the House's subject index give a topic).
NO_SUBJECTS = re.compile(r"(?!)")
TOPICS = {
    "env": ("Environment & energy", set(), NO_SUBJECTS, r"\b(environment\w*|pollut\w*|energy|utilit\w*|solar|nuclear|electric\w*|solid waste|landfill\w*|recycl\w*|water quality)\b"),
    "local": ("Local government", set(), NO_SUBJECTS, r"\b(municipal\w*|county|counties|cities|city|towns?|villages?|annex\w*|political subdivisions?)\b"),
    "tax": ("Taxes", set(), NO_SUBJECTS, r"\b(tax\w*|revenue)\b"),
    "safety": ("Public safety & courts", set(), NO_SUBJECTS, r"\b(crim\w*|firearm\w*|police|law enforcement|court\w*|judge\w*|sentenc\w*|prison\w*|jail\w*|felony|corrections|parole|sheriff\w*)\b"),
    "human": ("Human services", set(), NO_SUBJECTS, r"\b(child care|foster|adoption\w*|veteran\w*|senior\w*|elderly|disabilit\w*|homeless\w*|public assistance)\b"),
    "health": ("Health & mental health", set(), NO_SUBJECTS, r"\b(health|medical|medicaid|mo healthnet|hospital\w*|mental|pharmac\w*|nurs\w*|physician\w*|abortion)\b"),
    "edu": ("Education", set(), NO_SUBJECTS, r"\b(school\w*|student\w*|teacher\w*|education|college\w*|universit\w*)\b"),
    "transp": ("Transportation", set(), NO_SUBJECTS, r"\b(vehicle\w*|highway\w*|roads?|traffic|driver\w*|transportation|airport\w*)\b"),
    "labor": ("Labor & public employees", set(), NO_SUBJECTS, r"\b(wage\w*|employee\w*|worker\w*|labor|pension\w*|retirement)\b"),
    "housing": ("Housing", set(), NO_SUBJECTS, r"\b(housing|landlord\w*|tenant\w*|eviction\w*|homeowner\w*)\b"),
    "ag": ("Agriculture & natural resources", set(), NO_SUBJECTS, r"\b(agricultur\w*|farm\w*|livestock|fish\w*|wildlife|hunting|forest\w*|timber)\b"),
    "gov": ("Elections & state government", set(), NO_SUBJECTS, r"\b(election\w*|voter\w*|voting|ballot\w*|campaign\w*|ethics|open meetings|sunshine law|public records)\b"),
    "biz": ("Business & consumers", set(), NO_SUBJECTS, r"\b(consumer\w*|business\w*|insurance|bank\w*|licens\w*|alcohol\w*|liquor|gaming|gambling)\b"),
    "const": ("Constitutional amendments", set(), NO_SUBJECTS, ""),
}
# Committees (as convert.comm_name() names them, both houses) -> topic, for committees with one main subject. Rules,
# Fiscal Review, Fiscal Oversight, General Laws, Judiciary, Emerging Issues, Government Efficiency, Legislative Review,
# Budget, Appropriations and the special committees on broad subjects give none of their own.
COMMITTEE_TOPICS = {
    "Agriculture": "ag", "Agriculture Policy": "ag", "Agriculture, Food Production and Outdoor Resources": "ag",
    "Conservation and Natural Resources": "env", "Utilities": "env",
    "Commerce, Consumer Protection, Energy and the Environment": "biz", "Commerce": "biz", "Financial Institutions": "biz",
    "Insurance": "biz", "Insurance Policy": "biz", "Insurance and Banking": "biz", "Professional Registration and Licensing": "biz",
    "Emerging Issues and Professional Registration": "biz", "Special Committee on Small Business": "biz",
    "Special Committee on Tourism": "biz", "Select Committee on Gaming": "biz",
    "Economic Development": "biz", "Economic Development and Tax Policy": "tax", "Ways and Means": "tax",
    "Special Committee on Tax Reform": "tax", "Special Committee on Property Tax Reform": "tax", "Special Committee on Property Tax": "tax",
    "Select Committee on Property Taxes and the State Tax Commission": "tax",
    "Education": "edu", "Elementary and Secondary Education": "edu", "Higher Education": "edu",
    "Higher Education and Workforce Development": "edu", "Education and Workforce Development": "edu",
    "Special Committee on Education Reform": "edu", "Select Committee on Empowering Missouri Parents and Children": "edu",
    "Elections": "gov", "Elections and Elected Officials": "gov", "Special Committee on Election Contests": "gov",
    "Local Government": "local", "Local Government and Elections": "local", "Local Government, Elections and Pensions": "local",
    "Special Committee on Intergovernmental Affairs": "local", "Special Committee on Urban Issues": "local",
    "Pensions": "labor", "Economic and Workforce Development": "labor", "Workforce and Infrastructure Development": "labor",
    "Health and Mental Health": "health", "Health and Mental Health Policy": "health", "Healthcare Reform": "health",
    "Health and Welfare": "health", "Families, Seniors and Health": "health",
    "Children and Families": "human", "Veterans": "human", "Veterans and Armed Forces": "human",
    "Veterans and Military Affairs": "human", "Veterans, Military Affairs and Pensions": "human",
    "Crime and Public Safety": "safety", "Crime Prevention and Public Safety": "safety",
    "Corrections and Public Institutions": "safety", "Special Committee on Homeland Security": "safety",
    "Judiciary and Civil and Criminal Jurisprudence": "safety",
    "Transportation": "transp", "Transportation Accountability": "transp", "Transportation Infrastructure": "transp",
    "Transportation, Infrastructure and Public Safety": "transp",
}
# The House's subject index (upper case in the exports) -> topics; only a bill's first six subjects are read. Subjects
# that say little ("STATE DEPARTMENTS", "BOARDS, COMMISSIONS, COMMITTEES, AND COUNCILS", "FEES") give none.
_ST = {
    "ag": "AGRICULTURE; AGRICULTURE, DEPARTMENT OF; ANIMALS; FOOD; FISHING AND HUNTING; CONSERVATION, DEPARTMENT OF; TREES AND OTHER PLANTS; "
          "SOIL CONSERVATION; VETERINARIANS; FENCES AND ENCLOSURES; FAIRS; HORSE RACING",
    "biz": "BUSINESS AND COMMERCE; MERCHANDISING PRACTICES; CONSUMER PROTECTION; BANKS AND FINANCIAL INSTITUTIONS; INSURANCE - GENERAL; "
           "INSURANCE - PROPERTY; INSURANCE - LIFE; INSURANCE - AUTOMOBILE; PROFESSIONAL REGISTRATION AND LICENSING; LICENSES - MISCELLANEOUS; "
           "LICENSES - LIQUOR AND BEER; ALCOHOL; GAMBLING; LOTTERIES; BINGO; CORPORATIONS; CREDIT AND BANKRUPTCY; CREDIT UNIONS; SECURITIES; "
           "COMMERCE AND INSURANCE, DEPARTMENT OF; ECONOMIC DEVELOPMENT; ECONOMIC DEVELOPMENT, DEPARTMENT OF; TOURISM; ADVERTISING AND SIGNS; "
           "COSMETOLOGY; ACCOUNTANTS; ARCHITECTS; ENGINEERS; SURVEYORS; COMMERCIAL CODE; COOPERATIVES; ENTERTAINMENT, SPORTS AND AMUSEMENTS; "
           "MOTELS AND HOTELS; TOBACCO PRODUCTS; TELECOMMUNICATIONS; INTERNET AND E-MAIL; FUNERALS AND FUNERAL DIRECTORS",
    "edu": "EDUCATION, ELEMENTARY AND SECONDARY; ELEMENTARY AND SECONDARY EDUCATION, DEPT. OF; EDUCATION, HIGHER; "
           "HIGHER EDUCATION AND WORKFORCE DEVELOPMENT, DEPARTMENT OF; TEACHERS; EDUCATION, PROPRIETARY; RETIREMENT - SCHOOLS; ATHLETICS",
    "env": "ENERGY; UTILITIES; ENVIRONMENTAL PROTECTION; NATURAL RESOURCES, DEPARTMENT OF; WATER RESOURCES AND WATER DISTRICTS; AIR QUALITY; "
           "WASTE - HAZARDOUS; WASTE - SOLID; WASTE - RADIOACTIVE; MINING AND OIL AND GAS PRODUCTION; PUBLIC SERVICE COMMISSION; "
           "LAKES, RIVERS AND WATERWAYS; SEWERS AND SEWER DISTRICTS; PARKS AND RECREATION",
    "gov": "ELECTIONS; CAMPAIGN FINANCE; POLITICAL PARTIES; ETHICS; LOBBYING; GENERAL ASSEMBLY; SECRETARY OF STATE; AUDITOR, STATE; "
           "TREASURER, STATE; GOVERNOR AND LT. GOVERNOR; ATTORNEY GENERAL; PUBLIC RECORDS, PUBLIC MEETINGS; SUNSHINE LAW; REDISTRICTING; "
           "ADMINISTRATION, OFFICE OF; ADMINISTRATIVE RULES; STATE EMPLOYEES; PUBLIC OFFICERS",
    "health": "HEALTH CARE; HEALTH CARE PROFESSIONALS; HEALTH AND SENIOR SERVICES, DEPARTMENT OF; HEALTH, PUBLIC; INSURANCE - HEALTH; "
              "MEDICAL PROCEDURES AND PERSONNEL; MENTAL HEALTH; MENTAL HEALTH, DEPARTMENT OF; HOSPITALS; PHYSICIANS; NURSES; PHARMACY; "
              "MEDICAID/MO HEALTHNET; ABORTION; DRUGS AND CONTROLLED SUBSTANCES; DENTISTS; NURSING HOMES AND LONG-TERM CARE FACILITIES; "
              "AMBULANCES AND AMBULANCE DISTRICTS; PSYCHOLOGISTS; OPTOMETRY; CHIROPRACTORS; COUNSELING; CERTIFICATE OF NEED; SUICIDE",
    "housing": "HOUSING; LANDLORDS AND TENANTS; MANUFACTURED HOUSING; CONSTRUCTION AND BUILDING CODES; MORTGAGES AND DEEDS; PLANNING AND ZONING",
    "human": "CHILDREN AND MINORS; CHILDREN'S DIVISION; SOCIAL SERVICES, DEPARTMENT OF; PUBLIC ASSISTANCE; ELDERLY; DISABILITIES; VETERANS; "
             "ADOPTION; GUARDIANS; DOMESTIC RELATIONS; FAMILY LAW; MARRIAGE AND DIVORCE; YOUTH SERVICES, DIVISION OF; CHARITIES",
    "labor": "EMPLOYEES - EMPLOYERS; LABOR AND MANAGEMENT; LABOR AND INDUSTRIAL RELATIONS, DEPARTMENT OF; WORKERS COMPENSATION; "
             "UNEMPLOYMENT COMPENSATION; EMPLOYMENT SECURITY; RETIREMENT SYSTEMS AND BENEFITS - GENERAL; RETIREMENT - STATE; "
             "RETIREMENT - LOCAL GOVERNMENT; SALARIES",
    "local": "POLITICAL SUBDIVISIONS; COUNTIES; CITIES, TOWNS, AND VILLAGES; COUNTY OFFICIALS; COUNTY GOVERNMENT; SAINT LOUIS CITY; "
             "SAINT LOUIS COUNTY; KANSAS CITY; JACKSON COUNTY; ANNEXATION; URBAN REDEVELOPMENT; FIRE PROTECTION",
    "safety": "CRIMES AND PUNISHMENT; CRIMINAL PROCEDURE; COURTS; COURTS, JUVENILE; LAW ENFORCEMENT OFFICERS AND AGENCIES; FIREARMS; WEAPONS; "
              "PUBLIC SAFETY, DEPARTMENT OF; CORRECTIONS, DEPARTMENT OF; PRISONS AND JAILS; PROBATION AND PAROLE; VICTIMS OF CRIME; "
              "SEXUAL OFFENSES; JUDGES; JURIES; EVIDENCE; CIVIL PROCEDURE; LIABILITY; ATTORNEYS; HIGHWAY PATROL; EMERGENCIES; "
              "HOMELAND SECURITY; SEARCH AND SEIZURE; TERRORISM; CIRCUIT CLERKS; NATIONAL GUARD; MILITARY AFFAIRS; IDENTITY THEFT AND PROTECTION",
    "tax": "TAXATION AND REVENUE - GENERAL; TAXATION AND REVENUE - SALES AND USE; TAXATION AND REVENUE - PROPERTY; TAXATION AND REVENUE - INCOME; "
           "TAXATION AND REVENUE - INHERITANCE; TAX CREDITS; TAX INCENTIVES; REVENUE, DEPARTMENT OF; STATE TAX COMMISSION; ENTERPRISE ZONES",
    "transp": "MOTOR VEHICLES; ROADS AND HIGHWAYS; TRANSPORTATION; TRANSPORTATION, DEPARTMENT OF; LICENSES - MOTOR VEHICLE; LICENSES - DRIVER'S; "
              "MOTOR CARRIERS; MOTOR FUEL; AIRCRAFT AND AIRPORTS; RAILROADS; BUSES; BOATS AND WATERCRAFT; DRUNK DRIVING/BOATING; WATER PATROL",
}
SUBJECT_TOPICS = {}
for _k, _v in _ST.items():
    for _h in _v.split(";"):
        SUBJECT_TOPICS.setdefault(_h.strip(), []).append(_k)
TOPIC_WORDS = {k: re.compile(v[3], re.I) for k, v in TOPICS.items() if v[3]}

COUNTIES = []
DISTRICTS_PATH = os.path.join(DATA, "district_counties.json")
TOWNS_PATH = os.path.join(DATA, "district_towns.json")

_NAMING = re.compile(r"\b(?:designat\w*|nam\w*|renam\w*)\b.*\b(?:bridge|interchange|highway|route|memorial|building|park)\b|\bmemorial (?:highway|bridge|interchange)\b", re.I)
NARROW_KINDS = ["", "person", "org", "naming"]


def narrow_kind(title):
    return "naming" if _NAMING.search(title) else ""


# Governors and the day each took office. Mike Kehoe (R) took office January 13, 2025; his term runs to January 2029.
GOVERNORS = [("Parson", "2018-06-01"), ("Kehoe", "2025-01-13")]
GOV_SINCE = GOVERNORS[-1][1]


def governor_on(day):
    who = GOVERNORS[0][0]
    for name, start in GOVERNORS:
        if day >= start:
            who = name
    return who


TRENDS = []
WORDING = []
