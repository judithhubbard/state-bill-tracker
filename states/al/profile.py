"""Alabama: the settings and wording that are particular to this state.

build_data.py reads these as P.<name>, with the same names as states/ny/profile.py.
"""
import os, re

DATA = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "al"))
SITE_DIR = "al"

STATE_NAME = "Alabama"
SITE_NAME = "Alabama Bill Tracker"
LEGISLATURE = "Alabama Legislature"
TIMEZONE = "America/Chicago"
PUBLIC_URL = "https://statebilltracker.org/al/"
SITE_URL = os.environ.get("SITE_URL", PUBLIC_URL)

# Members serve four-year terms (all elected together: 2022, 2026), but the Legislature meets in a regular session each
# year: 30 legislative days within 105 calendar days, from the first Tuesday of February (the second Tuesday of January
# in an election year; the first Tuesday of March in the year after one). Bills die when the session ends. A page a year.
# Special sessions ("2026SS1") are left out.
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
# Who decides which bills reach each house's floor: each house's Rules Committee sets the special order calendars, under
# the Speaker and the Senate's President Pro Tempore (the Lieutenant Governor presides over the Senate but isn't a
# senator). From the members list, 2026-11-08 (it also gives Matt Woods the title "President Pro Tempore", apparently in
# error); the Legislature elected in November 2026 chooses its own leaders when it organizes in January 2027.
LEADERS = {"S": ("Garlan Gudger", "President Pro Tempore of the Senate", "him"),
           "H": ("Nathaniel Ledbetter", "Speaker of the House", "him")}


def delegation(session):
    return {}


# Each year's last day (sine die), as profile.js's STATE.dated (add each year's to both). The governor has 10 days after
# it to sign bills still on the desk; unsigned ones die (a pocket veto: Constitution, sec. 125).
SESSION_ENDS = {2024: "2024-05-09", 2025: "2025-05-14", 2026: "2026-04-09"}

# A member who moved from one house to the other keeps one record, under the newer house: Matt Woods represented House
# District 13 until he won Senate District 5 (a special election after Greg Reed left), so his House votes of 2024-25
# are tied to the House seat here.
MOVED = {("H", "Matt Woods"): 13}

# Topic: (label, committees (unused; see COMMITTEE_TOPICS), official subjects (unused; see SUBJECT_TOPICS), words in the
# title, used when neither the subject nor the committee gives a topic).
NO_SUBJECTS = re.compile(r"(?!)")
TOPICS = {
    "env": ("Environment & energy", set(), NO_SUBJECTS, r"\b(environment\w*|pollut\w*|energy|utilit\w*|solar|nuclear|electric\w*|solid waste|landfill\w*|recycl\w*)\b"),
    "local": ("Local government", set(), NO_SUBJECTS, r"\b(municipal\w*|county|counties|cities|city|towns?|annex\w*)\b"),
    "tax": ("Taxes", set(), NO_SUBJECTS, r"\b(tax\w*|revenue)\b"),
    "safety": ("Public safety & courts", set(), NO_SUBJECTS, r"\b(crim\w*|firearm\w*|police|law enforcement|court\w*|judge\w*|sentenc\w*|prison\w*|jail\w*|felony|corrections|parole|sheriff\w*)\b"),
    "human": ("Human services", set(), NO_SUBJECTS, r"\b(child care|foster|adoption\w*|veteran\w*|senior\w*|elderly|disabilit\w*|homeless\w*|public assistance)\b"),
    "health": ("Health & mental health", set(), NO_SUBJECTS, r"\b(health|medical|medicaid|hospital\w*|mental|pharmac\w*|nurs\w*|physician\w*|abortion)\b"),
    "edu": ("Education", set(), NO_SUBJECTS, r"\b(school\w*|student\w*|teacher\w*|education|college\w*|universit\w*)\b"),
    "transp": ("Transportation", set(), NO_SUBJECTS, r"\b(vehicle\w*|highway\w*|roads?|traffic|driver\w*|transportation|airport\w*)\b"),
    "labor": ("Labor & public employees", set(), NO_SUBJECTS, r"\b(wage\w*|employee\w*|worker\w*|labor|pension\w*|retirement)\b"),
    "housing": ("Housing", set(), NO_SUBJECTS, r"\b(housing|landlord\w*|tenant\w*|eviction\w*|homeowner\w*)\b"),
    "ag": ("Agriculture & natural resources", set(), NO_SUBJECTS, r"\b(agricultur\w*|farm\w*|livestock|fish\w*|wildlife|hunting|forest\w*|timber)\b"),
    "gov": ("Elections & state government", set(), NO_SUBJECTS, r"\b(election\w*|voter\w*|voting|ballot\w*|campaign\w*|ethics|open meetings|public records)\b"),
    "biz": ("Business & consumers", set(), NO_SUBJECTS, r"\b(consumer\w*|business\w*|insurance|bank\w*|licens\w*|alcohol\w*|liquor|beer|wine)\b"),
    "const": ("Constitutional amendments", set(), NO_SUBJECTS, ""),
}
# The Legislature's subjects (bills.json's subject, "; "-separated) -> topics. A county's name ("Jefferson County") is a
# local bill: "local". "Appropriations" and "Legislature" give none of their own.
SUBJECT_TOPICS = {
    "Administrative Law and Procedures": ["gov"], "Agriculture & Forestry": ["ag"], "Alcoholic Beverages & Tobacco": ["biz"],
    "Animals": ["ag"], "Authorities, Boards, & Commissions": ["gov"], "Buildings, Construction & Infrastructure": ["biz"],
    "Businesses & Financial Institutions": ["biz"], "Children": ["human"], "Civil Procedure": ["safety"],
    "Competitive Bidding": ["gov"], "Conservation & Natural Resources": ["ag"], "Constitutional Amendments Statewide": ["const"],
    "Consumer Protection": ["biz"], "Controlled Substances": ["safety"], "Counties & Municipalities": ["local"],
    "Courts & Judges": ["safety"], "Crimes & Offenses": ["safety"], "Criminal Procedure": ["safety"],
    "Discrimination & Civil Protections": ["gov"], "Economic Development": ["biz"], "Education": ["edu"],
    "Elderly & Disabled Persons": ["human"], "Elections, Voting, & Campaigns": ["gov"], "Environmental Protection": ["env"],
    "Family Law": ["human"], "Firearms": ["safety"], "Gaming": ["biz"], "Government Administration": ["gov"],
    "Health": ["health"], "Immigration": ["safety"], "Incarceration": ["safety"], "Insurance": ["biz"],
    "Labor & Employment": ["labor"], "Mental Health": ["health"], "Military": ["human"],
    "Motor Vehicles & Traffic": ["transp"], "Occupational Licensing Boards": ["biz"], "Pharmacy Board": ["health"],
    "Property & Estates": ["housing"], "Public K-12 Schools": ["edu"], "Public Safety & Emergencies": ["safety"],
    "Reapportionment": ["gov"], "Retirement": ["labor"], "State & State Officers": ["gov"], "State Government": ["gov"],
    "Taxation & Revenue": ["tax"], "Telecommunications & Utilities": ["env"], "Transportation": ["transp"],
    "Waters & Boating": ["ag"],
}
# Standing committees (as convert.comm_name() names them, both houses) -> topic, for committees with one main subject.
# Judiciary, State Government, the money committees and the local legislation committees give none of their own.
COMMITTEE_TOPICS = {
    "Agriculture and Forestry": "ag", "Agriculture, Conservation, and Forestry": "ag", "Banking and Insurance": "biz",
    "Children and Senior Advocacy": "human", "Children and Youth Health": "health", "Commerce and Small Business": "biz",
    "Constitution, Campaigns and Elections": "gov", "County and Municipal Government": "local",
    "Economic Development and Tourism": "biz", "Education Policy": "edu", "Ethics and Campaign Finance": "gov",
    "Financial Services": "biz", "Health": "health", "Healthcare": "health", "Insurance": "biz",
    "Military and Veterans Affairs": "human", "Ports, Waterways and Intermodal Transit": "transp",
    "Public Safety and Homeland Security": "safety", "State Governmental Affairs": "gov", "Tourism": "biz",
    "Transportation and Energy": "transp", "Transportation, Utilities and Infrastructure": "transp",
    "Urban and Rural Development": "local", "Veterans, Military Affairs and Public Safety": "safety",
    "Finance and Taxation Education": "tax", "Finance and Taxation General Fund": "tax",
}
TOPIC_WORDS = {k: re.compile(v[3], re.I) for k, v in TOPICS.items() if v[3]}

COUNTIES = []
DISTRICTS_PATH = os.path.join(DATA, "district_counties.json")
TOWNS_PATH = os.path.join(DATA, "district_towns.json")

_NAMING = re.compile(r"\b(?:designat\w*|nam\w*|renam\w*)\b.*\b(?:bridge|interchange|highway|route|memorial|building|park)\b|\bmemorial (?:highway|bridge|interchange)\b", re.I)
NARROW_KINDS = ["", "person", "org", "naming"]


def narrow_kind(title):
    return "naming" if _NAMING.search(title) else ""


# Governors and the day each took office. Kay Ivey is term-limited: a new governor takes office in January 2027 (add
# them here, and in states/legislatures.json).
GOVERNORS = [("Bentley", "2011-01-17"), ("Ivey", "2017-04-10")]
GOV_SINCE = GOVERNORS[-1][1]


def governor_on(day):
    who = GOVERNORS[0][0]
    for name, start in GOVERNORS:
        if day >= start:
            who = name
    return who


TRENDS = []
WORDING = []
