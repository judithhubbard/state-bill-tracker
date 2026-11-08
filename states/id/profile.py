"""Idaho: the settings and wording that are particular to this state.

build_data.py reads these as P.<name>, with the same names as states/ny/profile.py.
"""
import os, re

DATA = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "id"))
SITE_DIR = "id"

STATE_NAME = "Idaho"
SITE_NAME = "Idaho Bill Tracker"
LEGISLATURE = "Idaho Legislature"
TIMEZONE = "America/Boise"
PUBLIC_URL = "https://statebilltracker.org/id/"
SITE_URL = os.environ.get("SITE_URL", PUBLIC_URL)

# Two-year Legislatures (the 68th is 2025-26), but a session a year: from the second Monday of January to late March or
# April (no fixed length), and bills die when it adjourns sine die (none carry over to the second year, whose bills are
# numbered on from the first's: 2026's House bills start at H0501). A page a year: each year has its own laws ("Chapter
# 296" of that year's Session Laws), deadlines and governor's actions. Extraordinary sessions are left out.
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
# Who decides which bills reach each house's floor: the Speaker, and the Senate's President Pro Tempore (the Lieutenant
# Governor presides over the Senate but isn't a senator). From the Legislature's member lists, 2026-11-08; the 69th
# Legislature organizes in December 2026 and may choose others.
LEADERS = {"S": ("Kelly Arthur Anthon", "President Pro Tempore of the Senate", "him"),
           "H": ("Mike Moyle", "Speaker of the House", "him")}


def delegation(session):
    return {}


# Topic: (label, committees (unused; see COMMITTEE_TOPICS), official subjects (unused), words in the subject heading and
# title).
NO_SUBJECTS = re.compile(r"(?!)")
TOPICS = {
    "env": ("Environment & energy", set(), NO_SUBJECTS, r"\b(environment\w*|climate|emission\w*|renewable|solar|wind|pollut\w*|energy|utilit\w*|mining|mines|oil and gas|nuclear|carbon|electric\w*|cloud seeding|weather modification|solid waste|invasive species)\b"),
    "local": ("Local government", set(), NO_SUBJECTS, r"\b(municipal\w*|county|counties|annexation|local government|cities|city|highway district\w*|taxing district\w*|urban renewal|fire protection district\w*|recreation district\w*|abatement district\w*)\b"),
    "tax": ("Taxes", set(), NO_SUBJECTS, r"\b(tax\w*|revenue)\b"),
    "safety": ("Public safety & courts", set(), NO_SUBJECTS, r"\b(crim\w*|firearm\w*|weapons|police|peace officer\w*|court\w*|judge\w*|judicial|sentenc\w*|prison\w*|penitentiary|jail\w*|felony|misdemeanor|correction\w*|juvenile\w*|controlled substances|sex offender\w*|execution|probation|parole|public defense|lewd|trespass|riots?|immigra\w*|aliens|terroris\w*|retail theft|knives|offenses against|indecen\w*|cannibalism|critical infrastructure)\b"),
    "human": ("Human services", set(), NO_SUBJECTS, r"\b(child care|daycare|foster|adoptions?|child protect\w*|child support|child custody|veteran\w*|senior\w*|elderly|disabilit\w*|homeless\w*|public assistance|welfare|runaways|refugees|minors|child safety|parental rights|early childhood)\b"),
    "health": ("Health & mental health", set(), NO_SUBJECTS, r"\b(health|medical|medicaid|hospital\w*|mental|pharmac\w*|nurs\w*|physician\w*|abortion|immunization\w*|vaccin\w*|midwi\w*|behavioral|emergency medical|prescription|dentur\w*|dietitians|podiatry|counselors|therapists|maternal|ivermectin|kratom|blood product)\b"),
    "edu": ("Education", set(), NO_SUBJECTS, r"\b(school\w*|student\w*|teacher\w*|education|college\w*|universit\w*|tuition|charter|libraries)\b"),
    "transp": ("Transportation", set(), NO_SUBJECTS, r"\b(vehicle\w*|highway\w*|road\w*|traffic|transit|driver\w*|driving|motor|license plates?|rules of the road|aircraft|transportation)\b"),
    "labor": ("Labor & public employees", set(), NO_SUBJECTS, r"\b(wage\w*|employ\w*|worker\w*|labor|pension\w*|retirement|PERSI|collective bargaining|unions?)\b"),
    "housing": ("Housing", set(), NO_SUBJECTS, r"\b(housing|landlord\w*|tenant\w*|rental\w*|eviction\w*|homeowner\w*|manufactured homes|accessory dwelling|unlawful detainer|mortgage\w*)\b"),
    "ag": ("Agriculture & natural resources", set(), NO_SUBJECTS, r"\b(agricultur\w*|farm\w*|livestock|fish\w*|game|wildlife|hunting|forestry|timber|water rights?|water districts?|irrigation|aquifer|brands?|cervidae|estrays|depredat\w*|hemp|pesticides|beans|alfalfa|lands?|grazing)\b"),
    "gov": ("Elections & state government", set(), NO_SUBJECTS, r"\b(election\w*|voter\w*|voting|ballot\w*|campaign\w*|initiative\w*|referend\w*|state agenc\w*|ethics|public records|open meetings|administrative procedure|legislature|lobbyists|state controller|state treasurer|procurement|rules? approval|attorney general|governor|state government|state affairs|budgets?|state assets|public notices|flags|capitol|daylight saving|information technology|cybersecurity|purchasing|public funds|public money|elected officials|political candidates|public office|public servants|senators|websites|civil rights|indian affairs)\b"),
    "biz": ("Business & consumers", set(), NO_SUBJECTS, r"\b(consumer\w*|business\w*|insurance|bank\w*|credit unions|licens\w*|corporat\w*|economic development|alcohol\w*|liquor|beer|wine|commerce|contractors|barbers|cosmetolog\w*|architects|broadband|stablecoin|virtual currency|tobacco|smoking|transactions|plastic bags|legal tender|gold|silver|financial|ski area|bingo|raffles|covenants|unclaimed property)\b"),
    "const": ("Constitutional amendments", set(), NO_SUBJECTS, ""),
}
# Standing committees (as convert.comm_name() names them, both houses) -> topic, for committees with one main subject.
# State Affairs (both houses), Ways and Means, Judiciary, Rules and Administration (the House's, which also prints bills)
# and the money committees (Appropriations, Finance) give none: their bills get topics from their words.
COMMITTEE_TOPICS = {
    "Agricultural Affairs": "ag", "Business": "biz", "Commerce and Human Resources": "biz", "Education": "edu",
    "Environment, Energy and Technology": "env", "Health and Welfare": "health", "Judiciary and Rules": "safety",
    "Local Government": "local", "Local Government and Taxation": "local", "Resources and Conservation": "ag",
    "Resources and Environment": "ag", "Revenue and Taxation": "tax", "Transportation": "transp",
    "Transportation and Defense": "transp",
}
TOPIC_WORDS = {k: re.compile(v[3], re.I) for k, v in TOPICS.items() if v[3]}

COUNTIES = []
DISTRICTS_PATH = os.path.join(DATA, "district_counties.json")
TOWNS_PATH = os.path.join(DATA, "district_towns.json")

_NAMING = re.compile(r"\b(?:designat\w*|nam\w*|renam\w*)\b.*\b(?:bridge|interchange|highway|route|memorial|building|park)\b|\bmemorial (?:highway|bridge|interchange)\b", re.I)
NARROW_KINDS = ["", "person", "org", "naming"]


def narrow_kind(title):
    return "naming" if _NAMING.search(title) else ""


# Governors and the day each took office.
GOVERNORS = [("Otter", "2007-01-05"), ("Little", "2019-01-07")]
GOV_SINCE = GOVERNORS[-1][1]


def governor_on(day):
    who = GOVERNORS[0][0]
    for name, start in GOVERNORS:
        if day >= start:
            who = name
    return who


TRENDS = []
WORDING = []
