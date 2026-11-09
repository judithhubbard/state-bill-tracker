"""Kentucky: the settings and wording that are particular to this state.

build_data.py reads these as P.<name>, with the same names as states/ny/profile.py.
"""
import os, re

DATA = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "ky"))
SITE_DIR = "ky"

STATE_NAME = "Kentucky"
SITE_NAME = "Kentucky Bill Tracker"
LEGISLATURE = "Kentucky General Assembly"
TIMEZONE = "America/New_York"
PUBLIC_URL = "https://statebilltracker.org/ky/"
SITE_URL = os.environ.get("SITE_URL", PUBLIC_URL)

# A regular session a year from the first Tuesday after the first Monday of January: 60 legislative days in even years
# (to April 15 at the latest) and 30 in odd years (a few organizational days in January, then from early February to
# March 30 at the latest). Bills die when the session ends. A page a year; special sessions are left out.
YEARS = 1
LOWER = "H"
LOWER_NAME = "House"
TITLES = {"S": "Sen.", "H": "Rep."}


def session_of(year):
    return year


def session_kind(session):
    """Sessions alternate: a long session in even years (60 legislative days, with the two-year budget), a short one in
    odd years (30 days). Statistics compare a session only with past sessions of the same kind."""
    return "long" if session % 2 == 0 else "short"


def session_label(session):
    return str(session)


CF_ANALYTICS_TOKEN = ""
GOATCOUNTER_CODE = ""

DELEGATION_NAMES = set()
# Who decides which bills reach each house's floor: each house's Rules Committee and Committee on Committees, both made up
# of its leaders, under the Speaker and the President of the Senate (a senator, elected by the Senate; the Lieutenant
# Governor no longer presides). From the members list, 2026-11-08; the General Assembly elected in November 2026
# organizes in January 2027.
LEADERS = {"S": ("Robert Stivers", "President of the Senate", "him"),
           "H": ("David W. Osborne", "Speaker of the House", "him")}


def delegation(session):
    return {}


# Topic: (label, committees (unused; see COMMITTEE_TOPICS), official subjects (unused; see HEADING_TOPICS), words in the
# title and summary, used when neither the committee nor the index headings give a topic).
NO_SUBJECTS = re.compile(r"(?!)")
TOPICS = {
    "env": ("Environment & energy", set(), NO_SUBJECTS, r"\b(environment\w*|pollut\w*|energy|utilit\w*|solar|nuclear|electric\w*|solid waste|landfill\w*|recycl\w*|coal)\b"),
    "local": ("Local government", set(), NO_SUBJECTS, r"\b(municipal\w*|county|counties|cities|city|towns?|annex\w*|fiscal court\w*)\b"),
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
# Standing committees (as convert.comm_name() names them, both houses) -> topic, for committees with one main subject.
# Judiciary, State Government, Appropriations and Revenue, Rules and the Committee on Committees give none of their own.
COMMITTEE_TOPICS = {
    "Agriculture": "ag", "Banking and Insurance": "biz", "Economic Development and Workforce Investment": "biz",
    "Economic Development, Tourism and Labor": "labor", "Education": "edu", "Primary and Secondary Education": "edu",
    "Postsecondary Education": "edu", "Elections, Constitutional Amendments and Intergovernmental Affairs": "gov",
    "Families and Children": "human", "Health Services": "health", "Licensing and Occupations": "biz",
    "Licensing, Occupations and Administrative Regulations": "biz", "Local Government": "local",
    "Natural Resources and Energy": "env", "Small Business and Information Technology": "biz",
    "Tourism and Outdoor Recreation": "biz", "Transportation": "transp",
    "Veterans, Military Affairs and Public Protection": "safety",
}
# The LRC's index headings (lower case; the record writes "And" and "and") -> topics. Headings that say little about the
# subject ("State Agencies", "Local Mandate", "Effective Dates, Emergency", "Reports Mandated", "Fiscal Note") give none.
# Only a bill's first six headings are read.
_HT = {
    "ag": "agriculture; animals, livestock, and poultry; dairying and milk marketing; fish and wildlife; forests and forestry; "
          "grain; hunting and fishing; horses and horse racing; veterinarians; dogs; pets and service animals",
    "biz": "accountants; advertising; alcoholic beverages; auctioneers; banks and financial institutions; barbers and cosmetologists; "
           "business entities and organizations; commerce; consumer affairs; consumer protection; corporations; distilled spirits; "
           "gambling; gaming and wagering; insurance; insurance, motor vehicle; loans and credit; loans, credit, interest, and usury; "
           "malt beverages; occupations and professions; securities; small business; trade practices and retailing; "
           "wine and wineries; wines and wineries; tourism; economic development; electricians; plumbers and plumbing; "
           "engineers and surveyors; real estate; lottery; wagering; racing; cannabis",
    "edu": "education, elementary and secondary; education, finance; education, higher; education, vocational; teachers; "
           "universities and colleges; textbooks; athletics",
    "env": "energy; environment and conservation; pollution; waste management; water supply; public utilities; coal; "
           "minerals and mining; surface mining; oil and natural gas; nuclear energy; sewer systems; waterways and dams; "
           "flood control and flooding; hazardous materials",
    "gov": "elections and voting; campaign finance; general assembly; governor; secretary of state; attorney general; "
           "auditor of public accounts; treasurer; ethics; public ethics; public meetings; public records and reports; "
           "redistricting; congressional districts; state employees; reorganization; budget and financial administration; "
           "lieutenant governor; public procurement; purchasing",
    "health": "health and medical services; health care professionals; hospitals and nursing homes; hospitals and health facilities; "
              "insurance, health; medicaid; mental health; nurses; pharmacists; physicians; physicians and practitioners; "
              "public health; drugs and medicines; diseases; emergency medical services; substance abuse; substance use; "
              "opioids; reproductive issues; dementia; alcoholism; vaping; public medical assistance; optometrists",
    "housing": "landlord and tenant; housing, building, and construction; property; deeds and conveyances; planning and zoning",
    "human": "aged persons and aging; children and minors; disabilities; disabilities and the disabled; domestic relations; "
             "public assistance; poverty; veterans; women; men; parental rights; blind or deaf persons; guardians",
    "labor": "labor and industry; personnel and employment; retirement and pensions; unemployment compensation; wages and hours; "
             "workers' compensation; workers compensation; collective bargaining; occupational safety and health; workforce; "
             "public salaries",
    "local": "cities; counties; local government; consolidated local governments; unified local governments; charter county government; "
             "counties, charter; counties, urban; county clerks; special districts; cities, first class; cities, home rule class; "
             "sheriffs; coroners; county judges/executive; annexation; interlocal cooperation; area development districts",
    "safety": "crimes and punishments; criminal procedure; courts; courts, circuit; courts, district; courts, family; "
              "court, supreme; court of appeals; corrections and correctional facilities, state; jails and jailers; "
              "peace officers and law enforcement; police, city and county; police, state; probation and parole; "
              "firearms and weapons; crime victims; prosecutors; public advocate; bail and pretrial release; civil procedure; "
              "civil actions; juries and jurors; judges and court commissioners; homeland security; disasters; "
              "fire prevention; firefighters and fire departments; public safety; circuit clerks",
    "tax": "taxation; taxation, income--corporate; taxation, income--individual; taxation, inheritance and estate; "
           "taxation, property; taxation, sales and use; taxation, severance; property valuation administrators",
    "transp": "transportation; motor vehicles; highways, streets, and bridges; driver licensing; traffic safety; motor carriers; "
              "aeronautics and aviation; railroads; boats and boating",
    "const": "constitution, ky.",
}
HEADING_TOPICS = {}
for _k, _v in _HT.items():
    for _h in _v.split(";"):
        HEADING_TOPICS.setdefault(_h.strip(), []).append(_k)
TOPIC_WORDS = {k: re.compile(v[3], re.I) for k, v in TOPICS.items() if v[3]}

COUNTIES = []
DISTRICTS_PATH = os.path.join(DATA, "district_counties.json")
TOWNS_PATH = os.path.join(DATA, "district_towns.json")

_NAMING = re.compile(r"\b(?:designat\w*|nam\w*|renam\w*)\b.*\b(?:bridge|interchange|highway|route|memorial|building|park)\b|\bmemorial (?:highway|bridge|interchange)\b", re.I)
NARROW_KINDS = ["", "person", "org", "naming"]


def narrow_kind(title):
    return "naming" if _NAMING.search(title) else ""


# Governors and the day each took office. Andy Beshear's second term ends in December 2027 (term-limited): add the next
# governor here, and in states/legislatures.json.
GOVERNORS = [("Bevin", "2015-12-08"), ("Beshear", "2019-12-10")]
GOV_SINCE = GOVERNORS[-1][1]


def governor_on(day):
    who = GOVERNORS[0][0]
    for name, start in GOVERNORS:
        if day >= start:
            who = name
    return who


TRENDS = []
WORDING = []
