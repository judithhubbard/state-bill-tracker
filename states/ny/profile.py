"""New York: the settings and wording that are particular to this state.

build_data.py reads these as P.<name>. Another state gets its own states/<code>/profile.py with
the same names.
"""
import json, os, re

# Where this state's data files are, and the folder for its pages under site/ ("" for New York,
# whose pages stay at site/<session>.html until it moves to the multi-state site).
DATA = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data"))
SITE_DIR = ""

# Names in page titles and the header line.
STATE_NAME = "New York"
SITE_NAME = "Albany Bill Tracker"
LEGISLATURE = "New York State Legislature"
# Dates and times on the site are this state's.
TIMEZONE = "America/New_York"
# The public address; analytics are added only to builds for it.
PUBLIC_URL = "https://albanybilltracker.org/"
# The GitHub Pages address, used for share links and links to single bills.
SITE_URL = os.environ.get("SITE_URL", PUBLIC_URL)


def session_of(year):
    """The session running in a calendar year. Sessions start in odd years and run two years."""
    return year if year % 2 else year - 1


def session_label(session):
    """How a session is written: 2025–26."""
    return f"{session}–{str(session + 1)[2:]}"

# Visitor counts on the public site only (both are public values that appear in the page source).
# Cloudflare Web Analytics: the token from its JS snippet. GoatCounter: the site code, as in <code>.goatcounter.com.
CF_ANALYTICS_TOKEN = "4124cfe282c84c29990753f76caa2319"
GOATCOUNTER_CODE = "albanybilltracker"


# Sponsor checkboxes: only Sen. Webb (SD 52, from 2023) and Asm. Kelles (AD 125, from 2021).
# Later sessions use the same districts, but a checkbox appears only while Webb or Kelles
# holds the seat. Sessions with neither get no checkboxes.
DELEGATION = {
    2021: {"ASSEMBLY": {125}},
}
DEFAULT_DELEGATION = {"SENATE": {52}, "ASSEMBLY": {125}}  # 2023 onward
DELEGATION_NAMES = {"Webb", "Kelles"}

# Who decides which bills reach each house's floor: name, title, and the pronoun the site uses
# for them. Check after leadership votes in January of odd years; a leader is shown only while the
# named person still holds a seat.
LEADERS = {"S": ("Andrea Stewart-Cousins", "Senate Majority Leader", "her"),
           "A": ("Carl Heastie", "Assembly Speaker", "him")}


# Senators the contacts file doesn't list get an address on nysenate.gov, made from their name.
SENATOR_URLS = True


def delegation(session):
    return DELEGATION.get(session, DEFAULT_DELEGATION if session >= 2023 else {})


# Topic: (label, committees, laws amended, title/summary words).
# Committee and law names are matched exactly as the API spells them.
TOPICS = {
    "env": ("Environment & energy",
            {"Environmental Conservation", "Energy", "Energy And Telecommunications"},
            {"Environmental Conservation Law", "Environmental Conservation", "Navigation Law",
             "Energy Law", "Energy"},
            r"\b(climate|greenhouse|emission|renewable|solar|wind energy|pollut\w*|wetland|watershed|"
            r"drinking water|pesticide|plastic|recycl\w*|pfas|stormwater|wastewater|invasive species|"
            r"conservation easement|forest|wildlife|clean water|clean air|composting|landfill)\b"),
    "local": ("Local government",
              {"Local Government", "Local Governments", "Cities", "Cities 1", "Cities 2"},
              {"County Law", "Town Law", "Village Law", "General Municipal Law", "Municipal Home Rule Law",
               "Local Finance Law", "General City Law"},
              None),
    "tax": ("Taxes & assessment",
            {"Budget And Revenue", "Real Property Taxation"},
            {"Tax Law", "Real Property Tax Law", "Real Property Taxation", "Taxation"},
            None),
    "safety": ("Public safety & courts",
               {"Codes", "Correction", "Crime Victims, Crime And Correction", "Judiciary"},
               {"Penal Law", "Criminal Procedure Law", "Correction Law", "Family Court Act", "Judiciary Law",
                "Civil Practice Law and Rules", "Court of Claims Act"},
               None),
    "human": ("Human services",
              {"Social Services", "Children And Families", "Aging", "Disabilities", "People With Disabilities",
               "Women's Issues", "Veterans, Homeland Security And Military Affairs", "Veterans' Affairs"},
              {"Social Services Law", "Social Services", "Elder Law", "Veterans' Service Law"},
              None),
    "health": ("Health & mental health",
               {"Health", "Mental Health", "Mental Health And Developmental Disabilities", "Alcoholism And Drug Abuse",
                "Alcoholism And Substance Use Disorders", "Alcoholism And Substance Abuse"},
               {"Public Health Law", "Public Health", "Mental Hygiene Law", "Mental Hygiene"},
               None),
    "edu": ("Education",
            {"Education", "Higher Education", "Libraries", "Libraries And Education Technology",
             "New York City Education"},
            {"Education Law", "Education"},
            None),
    "transp": ("Transportation & highways",
               {"Transportation", "Infrastructure And Capital Investment"},
               {"Vehicle and Traffic Law", "Highway Law", "Transportation Law", "Transportation"},
               None),
    "labor": ("Labor & public employees",
              {"Labor", "Governmental Employees", "Civil Service And Pensions"},
              {"Labor Law", "Civil Service Law", "Civil Service", "Retirement and Social Security Law",
               "Retirement", "Workers' Compensation Law"},
              None),
    "housing": ("Housing",
                {"Housing", "Housing, Construction And Community Development"},
                {"Real Property Law", "Private Housing Finance Law", "Public Housing Law", "Multiple Dwelling Law",
                 "Real Property Actions and Proceedings Law", "Emergency Tenant Protection Act of 1974"},
                None),
    "ag": ("Agriculture",
           {"Agriculture", "Domestic Animal Welfare"},
           {"Agriculture and Markets Law"},
           None),
    "gov": ("Elections & state government",
            {"Election Law", "Elections", "Governmental Operations", "Investigations And Government Operations",
             "Ethics And Internal Governance", "Procurement And Contracts"},
            {"Election Law", "Public Officers Law", "Legislative Law", "State Finance Law"},
            None),
    "biz": ("Business & consumers",
            {"Consumer Affairs And Protection", "Consumer Protection", "Banks", "Insurance", "Economic Development",
             "Commerce, Economic Development And Small Business", "Small Business",
             "Corporations, Authorities And Commissions", "Racing And Wagering", "Racing, Gaming And Wagering",
             "Internet And Technology", "Science And Technology"},
            {"General Business Law", "Insurance Law", "Banking Law", "Financial Services Law",
             "Alcoholic Beverage Control Law", "Cannabis Law"},
            None),
    "const": ("Constitutional amendments", set(), {"Constitution, Concurrent Resolutions to Amend"}, None),
}
TOPIC_WORDS = {k: re.compile(v[3], re.I) for k, v in TOPICS.items() if v[3]}

# Laws that touch county and municipal operations, for the "local government impact" filter.
LOCAL_LAWS = TOPICS["local"][2] | {"Real Property Tax Law", "Real Property Taxation", "Social Services Law"}
LOCAL_WORDS = re.compile(r"\b(count(y|ies)|municipal\w*|local governments?|unfunded mandate)\b", re.I)

# Which counties a bill is only about, when it names specific places: a town, city, village, county,
# district or New York City body. Bills worded to reach beyond those places count as statewide.
COUNTIES = [c.replace("_", " ") for c in ("Albany Allegany Bronx Broome Cattaraugus Cayuga Chautauqua Chemung Chenango Clinton "
            "Columbia Cortland Delaware Dutchess Erie Essex Franklin Fulton Genesee Greene Hamilton Herkimer Jefferson Kings "
            "Lewis Livingston Madison Monroe Montgomery Nassau New_York Niagara Oneida Onondaga Ontario Orange Orleans Oswego "
            "Otsego Putnam Queens Rensselaer Richmond Rockland St._Lawrence Saratoga Schenectady Schoharie Schuyler Seneca "
            "Steuben Suffolk Sullivan Tioga Tompkins Ulster Warren Washington Wayne Westchester Wyoming Yates").split()]
NYC = ["New York", "Kings", "Queens", "Bronx", "Richmond"]
# Regions and bodies named without a town or county.
REGIONS = {
    "New York city": NYC, "New York City": NYC, "city of New York": NYC, "NYC": NYC, "N.Y. city": NYC, "population of one million or more": NYC,
    "Brooklyn": ["Kings"], "Manhattan": ["New York"], "Harlem": ["New York"], "Staten Island": ["Richmond"],
    "the Bronx": ["Bronx"], "Rockaway": ["Queens"], "Coney Island": ["Kings"], "NYCHA": NYC, "Port Authority": NYC,
    "metropolitan transportation authority": NYC + ["Nassau", "Suffolk", "Westchester", "Putnam", "Dutchess", "Orange", "Rockland"],
    "MTA": NYC + ["Nassau", "Suffolk", "Westchester", "Putnam", "Dutchess", "Orange", "Rockland"],
    "Long Island Rail Road": ["Kings", "Queens", "Nassau", "Suffolk"], "Long Island Power Authority": ["Nassau", "Suffolk"],
    "Long Island": ["Nassau", "Suffolk"], "Westchester": ["Westchester"],
    "Adirondack": ["Clinton", "Essex", "Franklin", "Fulton", "Hamilton", "Herkimer", "Lewis", "Oneida", "St. Lawrence", "Saratoga", "Warren", "Washington"],
    "Catskill": ["Delaware", "Greene", "Sullivan", "Ulster"],
    "Hudson Valley": ["Columbia", "Dutchess", "Greene", "Orange", "Putnam", "Rockland", "Sullivan", "Ulster", "Westchester"],
    "Mid-Hudson": ["Columbia", "Dutchess", "Greene", "Orange", "Putnam", "Sullivan", "Ulster"],
    "Hudson River": ["Albany", "Columbia", "Dutchess", "Greene", "Orange", "Putnam", "Rensselaer", "Rockland", "Saratoga", "Ulster", "Warren", "Washington", "Westchester", "New York", "Bronx"],
    "Lake George": ["Warren", "Washington", "Essex"], "Lake Champlain": ["Clinton", "Essex", "Washington"],
    "Capital District": ["Albany", "Rensselaer", "Saratoga", "Schenectady"], "Capital Region": ["Albany", "Rensselaer", "Saratoga", "Schenectady"],
    "Western New York": ["Allegany", "Cattaraugus", "Chautauqua", "Erie", "Genesee", "Niagara", "Orleans", "Wyoming"],
    "North Country": ["Clinton", "Essex", "Franklin", "Hamilton", "Jefferson", "Lewis", "St. Lawrence"],
    "Finger Lakes": ["Cayuga", "Livingston", "Monroe", "Ontario", "Schuyler", "Seneca", "Steuben", "Tompkins", "Wayne", "Yates"],
    "Cayuga Lake": ["Cayuga", "Seneca", "Tompkins"],
    "Southern Tier": ["Allegany", "Broome", "Cattaraugus", "Chautauqua", "Chemung", "Chenango", "Delaware", "Schuyler", "Steuben", "Tioga", "Tompkins"],
    "Central New York": ["Cayuga", "Cortland", "Madison", "Onondaga", "Oswego", "Tompkins"],
}
# Cities named on their own. Names that are also common words or other things (Hudson, Rome, Geneva) are left out.
CITY_NAMES = ["Buffalo", "Rochester", "Syracuse", "Yonkers", "Schenectady", "Binghamton", "Utica", "Niagara Falls", "Poughkeepsie",
              "Newburgh", "New Rochelle", "Mount Vernon", "White Plains", "Long Beach", "Glen Cove", "Saratoga Springs", "Plattsburgh",
              "Watertown", "Jamestown", "Elmira", "Kingston", "Lackawanna", "Lockport", "Olean", "Peekskill", "Glens Falls",
              "Gloversville", "Cohoes", "Watervliet", "Ogdensburg", "Oneonta", "Hornell", "Corning", "Dunkirk", "Batavia",
              "Canandaigua", "Port Jervis", "Salamanca", "North Tonawanda", "Ithaca", "Cortland", "Trumansburg", "Cayuga Heights"]
PLACES_PATH = os.path.join(DATA, "ny_places.json")
DISTRICTS_PATH = os.path.join(DATA, "district_counties.json")
PLACE_COUNTIES = json.load(open(PLACES_PATH)) if os.path.exists(PLACES_PATH) else {}
_NAME = r"(?:St\. )?[A-Z][A-Za-z'’.-]+(?:[ -](?:on[ -]the[ -])?[A-Z][A-Za-z'’.-]+)*"
_CTY = "|".join(re.escape(c) for c in COUNTIES)
_MUNI = re.compile(r"\b(?:[Cc]ity|[Tt]own|[Vv]illage|[Hh]amlet|[Bb]orough)s? of (?!New York State\b)(" + _NAME + ")")
_COUNTY = re.compile(r"\b(" + _CTY + r")[ -][Cc]ount(?:y|ies)\b|\b[Cc]ount(?:y|ies) of (" + _CTY + r")\b")
_ENTITY = re.compile(r"\b(" + _NAME + r") (?:[Vv]olunteer )?(?:[Ff]ire (?:[Dd]epartment|[Cc]ompany|[Dd]istrict)|[Aa]mbulance"
                     r"|(?:[Pp]ublic |[Ff]ree )?[Ll]ibrary(?: [Dd]istrict)?|(?:[Cc]entral |[Uu]nion [Ff]ree |[Cc]ity )?[Ss]chool [Dd]istrict"
                     r"|[Ww]ater [Dd]istrict|[Ss]ewer [Dd]istrict|[Hh]ousing [Aa]uthority|[Ii]ndustrial [Dd]evelopment [Aa]gency"
                     r"|[Pp]arking [Aa]uthority|Cemetery|Hospital|Rescue Squad|Community College"
                     r"|(?:(?:[Vv]olunteer|Exempt) )*(?:Fire(?:fighter|men)(?:'s|s'|’s|s)? )?Benevolent Association"
                     r"|(?:First |United |Reformed |Evangelical |Lutheran |Baptist |Methodist |Presbyterian |Episcopal |Catholic )*Church)\b")
_NAMED = re.compile(r"\b(" + "|".join(re.escape(k) for k in sorted(list(REGIONS) + CITY_NAMES, key=len, reverse=True)) + r")\b")
# Wording that makes a bill reach beyond the places it names, e.g. "counties outside the city of New York".
REACHES_BEYOND = re.compile(r"\b(statewide|each county|every county|all counties|any county|state of New York|outside|except|"
                            r"other than|excluding|limits the application|the counties and|counties and the city)\b", re.I)


# Bills for one named person or organization, and namings of roads and bridges: stock formats such as
# "Grants retroactive tier IV membership ... to Katie Adamek", "Authorizes the Congregation Atzei Chaim to
# receive retroactive real property tax exempt status", "Dedicates a portion of the state highway system to ...".
_NOT_NAME = set("""New York State County City Town Village Police Department Fire Retirement System Tier Local Employees Authority
Sheriff Correction Correctional Office Commissioner University College Court Supreme Family Civil Service Teachers Transit Metropolitan
Island Long Nassau Suffolk Westchester Erie Monroe Department's Board District School Union Free Central Volunteer Benevolent
Association Inc Corporation Church Congregation Temple Foundation Society Hospital Center Highway Bridge Memorial Route Parkway
Expressway Thruway Lake River Park Medicaid SUNY CUNY MTA Act Law Program Fund Trust Agency Development Housing Water Sewer Library
Cemetery Lodge Post Club Academy Museum Health Council Senate Assembly Governor Comptroller Attorney General Division Bureau Unit
Office's Troopers Trooper Parks Disease Syndrome Cancer Nation Indian Brook Creek United States America World Trade War Veterans
Native American NY NYS Status""".split())
_PERSON = re.compile(r"\b((?:[A-Z][a-z'’]+|[A-Z]\.)(?: (?:[A-Z]\.|[A-Z][a-z'’-]+|Mc[A-Z][a-z]+|O'[A-Z][a-z]+)){1,3})")
_BENEFIT = re.compile(r"service credit|retirement|disability|death benefit|\btier\b|pension|civil service (?:examination|exam|list)|eligib|"
                      r"sick leave|reinstat|deemed|appointed|accidental|vested|membership|annuity|survivor|widow|spouse|wife of|husband of|"
                      r"salary|back pay|seniority|probationary|age requirement|maximum age|competitive", re.I)
_ORG_TAX = re.compile(r"real property tax(?:es)? exempt|exempt(?:ion)? from (?:real property|school) tax|tax exempt status|"
                      r"application for (?:an )?exemption|retroactive real property tax|from real property taxation", re.I)
_NAMING = re.compile(r"^(?:Dedicates|Designates|Names|Renames|Redesignates)\b.*\b(?:portion|bridge|segment|section|route|interchange|"
                     r"highway|overpass|memorial|building|facility|courthouse|post office|park|trail|exit)\b|\bMemorial (?:Highway|Bridge|Way|Parkway)\b", re.I)
NARROW_KINDS = ["", "person", "org", "naming"]
# Governors and the day each took office. Add a new governor here. Patterns in how bills are
# requested use only the current governor's record (GOV_SINCE).
GOVERNORS = [("Cuomo", "2011-01-01"), ("Hochul", "2021-08-24")]
GOV_SINCE = GOVERNORS[-1][1]


def governor_on(day):
    """Who was governor on a day (YYYY-MM-DD)."""
    who = GOVERNORS[0][0]
    for name, start in GOVERNORS:
        if day >= start:
            who = name
    return who


def narrow_kind(title):
    """"person", "org" or "naming" for the stock narrow formats; "" otherwise."""
    if _NAMING.search(title):
        return "naming"
    t = title[:1].lower() + title[1:]
    if _ORG_TAX.search(title) and any(w not in ("New", "York", "State", "NY", "NYS") for w in re.findall(r"\b[A-Z][A-Za-z'’.-]+", t)):
        return "org"
    if _BENEFIT.search(title):
        for m in _PERSON.finditer(t):
            if not any(w in _NOT_NAME for w in m.group(1).replace(".", "").split()):
                return "person"
    return ""


# ---- What's changing: subjects that rose (or spiked) across sessions, and wording that changed.
# Hand-picked from an automatic scan for phrases whose share of bills changed most, then checked,
# since the raw scan mixes real subjects with drafting habits. Matched on title and summary.
TRENDS = [
    ("rise", "Artificial intelligence", r"artificial intelligence|\bAI\b|automated (?:employment )?decision|algorithmic", False),
    ("rise", "Sports betting", r"sports wagering|mobile sports|sports betting", True),
    ("rise", "E-bikes and scooters", r"electric assist|bicycles? with electric|e-bikes?\b|electric scooter", True),
    ("rise", "Climate", r"climate|greenhouse gas|zero-emission", True),
    ("rise", "Immigration", r"immigra|migrants?\b|asylum|noncitizen", True),
    ("rise", "Batteries and energy storage", r"batter(?:y|ies)|energy storage", True),
    ("rise", "Social media", r"social media|online platform|digital platform", True),
    ("rise", "Cannabis", r"cannabis|marihuana|marijuana", True),
    ("spike", "COVID-19", r"covid|coronavirus|pandemic", True),
]
# Old wording -> new wording, for the same thing.
WORDING = [
    (("“inmates”", r"\binmates?\b"), ("“incarcerated individuals”", r"incarcerated (?:individual|person|people)")),
    (("“marihuana”", r"marihuana"), ("“cannabis”", r"cannabis"),
     "“Marihuana,” with an h, is the spelling New York law used until the 2021 law legalizing adult use switched to “cannabis.”"),
    (("“alcoholism” and “drug abuse”", r"alcoholism|drug abuse"), ("“substance use”", r"substance use")),
    (("“his or her”, “he or she”", r"\bhis or her\b|\bhe or she\b"), ("“their”, “they”", r"\btheir\b|\bthey\b"),
     "In 2025–26 bill summaries switched to gender-neutral wording: “his or her” almost vanished as “their” and “they” rose."),
]
