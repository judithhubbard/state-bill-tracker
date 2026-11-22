"""New Jersey: the settings and wording that are particular to this state.

build_data.py reads these as P.<name>, with the same names as states/ny/profile.py.
"""
import os, re

# Where this state's data files are (from states/nj/fetch.py), and its folder under site/.
DATA = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "nj"))
SITE_DIR = "nj"

# Names in page titles and the header line.
STATE_NAME = "New Jersey"
SITE_NAME = "New Jersey Bill Tracker"
LEGISLATURE = "New Jersey Legislature"
# Dates and times on the site are this state's.
TIMEZONE = "America/New_York"
# The public address; analytics are added only to builds for it.
PUBLIC_URL = "https://statebilltracker.org/nj/"
SITE_URL = os.environ.get("SITE_URL", PUBLIC_URL)


def session_of(year):
    """The session running in a calendar year. Sessions start in even years and run two years."""
    return year if year % 2 == 0 else year - 1


def session_label(session):
    """How a session is written: 2026–27."""
    return f"{session}–{str(session + 1)[2:]}"

# Visitor counts: none until the site is public.
CF_ANALYTICS_TOKEN = ""
GOATCOUNTER_CODE = ""

# Sponsor checkboxes for a local delegation: none.
DELEGATION_NAMES = set()
# Who decides which bills reach each house's floor: name, title, and the pronoun the site uses for
# them (from the roster's sex field). Check after leadership votes each January of an even year.
LEADERS = {"S": ("Nicholas Scutari", "Senate President", "him"),
           "A": ("Craig Coughlin", "Assembly Speaker", "him")}


def delegation(session):
    return {}


# Topic: (label, committees, official subjects, title words). Committees are named as in
# COMMITTEE.TXT; subjects are matched on the start of their names in SUBJHEADINGS.TXT
# ("ENVIRONMENT" matches "ENVIRONMENT - WATER SUPPLY"). The keys are shared with other states.
TOPICS = {
    "env": ("Environment and energy",
            {"Environment and Solid Waste", "Environment and Energy", "Telecommunications and Utilities"},
            re.compile(r"^(ENVIRONMENT|ENERGY|PUBLIC UTILITIES)"),
            r"\b(climate|greenhouse|emission|renewable|solar|offshore wind|pollut\w*|wetland|watershed|"
            r"drinking water|pesticide|plastic|recycl\w*|pfas|stormwater|wastewater|forest|wildlife)\b"),
    "local": ("Local government",
              {"State and Local Government", "Community and Urban Affairs"},
              re.compile(r"^(LOCAL GOVERNMENT|LOCAL OFFICERS|AUTHORITIES - LOCAL|PUBLIC CONTRACTS - LOCAL|LAND USE)"),
              None),
    "tax": ("Taxes", set(), re.compile(r"^TAXATION"), None),
    "safety": ("Public safety and courts",
               {"Judiciary", "Public Safety and Preparedness", "Law and Public Safety",
                "Homeland Security and State Preparedness"},
               re.compile(r"^(CRIM|PUBLIC SAFETY|JUDICIARY|CORRECTIONS|PAROLE|JUVENILE JUSTICE|DOMESTIC VIOLENCE|TERRORISM)"),
               None),
    "human": ("Social services",
              {"Aging and Human Services", "Aging and Senior Services", "Children, Families and Food Security",
               "Military and Veterans' Affairs", "Community Development and Women's Affairs"},
              re.compile(r"^(HUMAN SERVICES(?! - (MENTAL HEALTH|DRUG))|CHILDREN|SENIOR CITIZENS|VETERANS|WOMEN)"),
              None),
    "health": ("Health",
               {"Health", "Health Infrastructure", "Health, Human Services and Senior Citizens"},
               re.compile(r"^(HEALTH|INSURANCE - HEALTH|HUMAN SERVICES - (MENTAL HEALTH|DRUG|MEDICAID))"),
               None),
    "edu": ("Education", {"Education", "Higher Education"}, re.compile(r"^(EDUCATION|HIGHER EDUCATION)"), None),
    "transp": ("Transportation",
               {"Transportation and Independent Authorities", "Transportation"},
               re.compile(r"^(TRANSPORTATION|MOTOR VEHICLES|AVIATION)"),
               None),
    "labor": ("Jobs and workers", {"Labor"},
              re.compile(r"^(LABOR|PUBLIC EMPLOYEES|PENSIONS|CIVIL SERVICE)"), None),
    "housing": ("Housing", {"Housing"}, re.compile(r"^HOUSING"), None),
    "ag": ("Agriculture and natural resources", {"Agriculture and Natural Resources"}, re.compile(r"^(AGRICULTURE|ANIMALS|FOOD)"), None),
    "gov": ("Elections and government",
            {"State and Local Government", "Oversight, Reform and Federal Relations",
             "State Government, Wagering, Tourism & Historic Preservation"},
            re.compile(r"^(ELECTIONS|STATE GOVERNMENT|LEGISLATURE|GOVERNOR|ETHICS|PUBLIC RECORDS|PUBLIC CONTRACTS - STATE)"),
            None),
    "biz": ("Business and consumers",
            {"Commerce and Economic Development", "Consumer Affairs", "Financial Institutions and Insurance",
             "Regulated Professions", "Science, Innovation and Technology", "Commerce", "Economic Growth"},
            re.compile(r"^(COMMERCE|CONSUMER AFFAIRS|BANKING|INSURANCE(?! - HEALTH)|CORPORATIONS|REGULATED PROFESSIONS|ECONOMIC DEV)"),
            None),
    # Concurrent resolutions proposing constitutional amendments (tagged by convert.py, not by subjects or words).
    "const": ("Constitutional amendments", set(), re.compile(r"(?!)"), None),
}
TOPIC_WORDS = {k: re.compile(v[3], re.I) for k, v in TOPICS.items() if v[3]}

# New Jersey's 21 counties ("Where you live" and bills about one place come later).
COUNTIES = ["Atlantic", "Bergen", "Burlington", "Camden", "Cape May", "Cumberland", "Essex", "Gloucester", "Hudson",
            "Hunterdon", "Mercer", "Middlesex", "Monmouth", "Morris", "Ocean", "Passaic", "Salem", "Somerset", "Sussex",
            "Union", "Warren"]
DISTRICTS_PATH = os.path.join(DATA, "district_counties.json")
# Each town's legislative district (states/nj/towns.py): "Where you live" picks a town. A town's Senate
# and Assembly districts are the same, with one senator and two Assembly members.
TOWNS_PATH = os.path.join(DATA, "district_towns.json")

# Bills about one person, group or naming (their odds are compared only with their own kind).
_NAMING = re.compile(r"^(?:Designates|Names|Renames|Redesignates|Dedicates)\b.*\b(?:portion|bridge|segment|section|route|"
                     r"interchange|highway|overpass|memorial|building|facility|park|trail)\b", re.I)
NARROW_KINDS = ["", "person", "org", "naming"]


def narrow_kind(title):
    return "naming" if _NAMING.search(title) else ""


# Governors and the day each took office. Patterns in when bills are signed use only the
# current governor's record (GOV_SINCE).
GOVERNORS = [("Christie", "2010-01-19"), ("Murphy", "2018-01-16"), ("Sherrill", "2026-01-20")]
GOV_SINCE = GOVERNORS[-1][1]


def governor_on(day):
    """Who was governor on a day (YYYY-MM-DD)."""
    who = GOVERNORS[0][0]
    for name, start in GOVERNORS:
        if day >= start:
            who = name
    return who


# ---- What's changing: subjects whose share of bills changed most across the sessions shown, picked by hand from an
# automatic phrase scan and checked against samples of the bills matched (notes/trends.md). Matched on the synopsis.
# (Cannabis rose from 2018-19 but has been flat since 2022-23; its change shows as the wording pair below.)
TRENDS = [
    ("rise", "Artificial intelligence", r"(?i:artificial intelligence|automated (?:employment )?decision|algorithmic|deepfake|deep fake|\bgenerative|chatbot)|\bAI\b", False),
    ("rise", "Data centers", r"data cent(?:er|re)s?\b", True),
    ("rise", "Warehouses", r"warehouse(?!m[ae]n)", True),
    ("rise", "Menstrual products", r"menstrua|feminine hygiene", True),
    ("rise", "Reproductive health care", r"reproductive health", True),
    ("rise", "E-bikes and scooters", r"electric[- ]assist(?:ed)? bicycle|electric (?:bicycle|scooter|motorized scooter)|e-bikes?\b|low-speed electric|motorized scooter", True),
    ("rise", "Nuclear power", r"nuclear (?:energy|power|reactor|generat|facilit)|small modular|advanced reactor|microreactor|advanced nuclear", True),
    ("rise", "Batteries and energy storage", r"batter(?:y|ies)|energy storage", True),
    ("rise", "Immigration", r"immigra|migrants?\b|asylum|noncitizen|illegal alien|undocumented", True),
    ("rise", "Social media", r"social media|social networking|online platform", True),
    ("spike", "COVID-19", r"covid|coronavirus|pandemic", True),
]
# Old wording -> new wording, for the same thing.
WORDING = [
    (("“marijuana”", r"marijuana|marihuana"), ("“cannabis”", r"cannabis"),
     "New Jersey's 2021 law legalizing adult use switched the statutes from “marijuana” to “cannabis.”"),
]
