#!/usr/bin/env python3
"""Turn data/bills_<session>.json files (from fetch_bills.py) into tracker pages,
site/<session>.html: tracker.html with that session's bill data embedded in it.

Pairs Senate and Assembly versions of the same bill, works out how far each pair got,
tags each pair with topics based on committees and the laws it amends, and links each
bill to its versions in earlier and later sessions (the API's "previous versions").

Usage: python3 build_data.py            builds every session found in data/
       python3 build_data.py 2025       builds just that session's page (still reads
                                        the other sessions for bill histories)
       python3 build_data.py --github _site
                                        builds the GitHub Pages version into _site/:
                                        index.html for the current session, <year>.html
                                        for the others, linked to each other
       --state nj                       builds another state's pages (default: ny), using
                                        states/<state>/; its data is in the profile's DATA
                                        folder and its pages go in site/<state>/
"""
import base64, glob, gzip, importlib, json, os, re, sys
from fetch_contacts import committee_key, name_key, senate_url
from collections import Counter, defaultdict
from stages import STAGE_LABEL, rank

ARGS = sys.argv[1:]
STATE = "ny"
if "--state" in ARGS:
    i = ARGS.index("--state")
    STATE = ARGS[i + 1]
    del ARGS[i:i + 2]
# The state's settings and wording, as P.<name>.
P = importlib.import_module(f"states.{STATE}.profile")
# The code that reads the state's own data and turns it into bill records (C.load_session).
C = importlib.import_module(f"states.{STATE}.convert")

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE = os.path.join(HERE, "tracker.html")
SITE = os.path.join(HERE, "site", P.SITE_DIR)
# Published URL of each session's page, filled in after the first publish of each.
URLS_FILE = os.path.join(HERE, "artifact_urls.json")
# Sessions whose first copy is still downloading (data/<state>/incomplete_<session>: an older year added back to the
# window, states/window.py) are left out until it's finished.
SESSIONS = importlib.import_module("states.window").shown(P.DATA, C.sessions())
# The lower house's letter ("A" for an Assembly, "H" for Virginia's House of Delegates) and members' titles.
LOW = getattr(P, "LOWER", "A")
TITLES = getattr(P, "TITLES", {"S": "Sen.", LOW: "Asm."})
# How many years a session runs (two in New York and New Jersey, one in Virginia).
YEARS = getattr(P, "YEARS", 2)
# The current session by the calendar (P.session_of), as the workflow works it out,
# or the newest one downloaded if that hasn't started yet. A later session in data/ is upcoming:
# its prefiled bills get their own page before it opens.
def _current():
    from datetime import datetime
    from zoneinfo import ZoneInfo
    by_date = P.session_of(datetime.now(ZoneInfo(P.TIMEZONE)).year)
    return max([s for s in SESSIONS if s <= by_date] or SESSIONS)
CURRENT = _current() if SESSIONS else None
GITHUB = None
if "--github" in ARGS:
    i = ARGS.index("--github")
    GITHUB = os.path.abspath(ARGS[i + 1])
    del ARGS[i:i + 2]
ONLY = [int(a) for a in ARGS] or SESSIONS


_CALENDAR = os.path.join(P.DATA, "session_calendar.json")
SESSION_END = json.load(open(_CALENDAR))["end"] if os.path.exists(_CALENDAR) else {}


def narrow_bill(r):
    """About one place, person or group, or a naming: the bills the "leave out narrow bills" switches drop."""
    return bool(r["narrow"] or r["places"])


def analytics_tags():
    """Visit counters for the public site once launched; none for the preview or local test builds."""
    import site_meta
    if not (site_meta.launched() and P.SITE_URL.startswith(P.PUBLIC_URL.rstrip("/"))):
        return ""
    tags = ""
    if P.CF_ANALYTICS_TOKEN:
        tags += ('<script defer src="https://static.cloudflareinsights.com/beacon.min.js" '
                 f'data-cf-beacon=\'{{"token": "{P.CF_ANALYTICS_TOKEN}"}}\'></script>\n')
    code = P.GOATCOUNTER_CODE or site_meta.GOATCOUNTER
    if code:
        tags += (f'<script data-goatcounter="https://{code}.goatcounter.com/count" '
                 'async src="https://gc.zgo.at/count.js"></script>\n')
    return tags


# Until launch every page asks search engines not to list it; LAUNCHED=1 (build_site.sh's setting) drops the tag.
ROBOTS_META = "" if os.environ.get("LAUNCHED", "0") == "1" else '<meta name="robots" content="noindex, nofollow">\n'


def page_meta(title, desc, path=""):
    """A public page's description, link preview tags and canonical link (site_meta.py); path is the page's address
    within the state's folder ("", "2023.html", "watchlist/")."""
    import site_meta
    return (f'<meta name="description" content="{site_meta.attr(desc)}">\n'
            + site_meta.tags(title, desc, site_meta.state_root(P.PUBLIC_URL, P.SITE_URL) + path))


def state_words():
    """"Wyoming bills" (or "Bills in Congress") for link previews' titles."""
    return "Bills in Congress" if P.STATE_NAME == "Congress" else f"{P.STATE_NAME} bills"


def github_page(html, meta=""):
    """Claude artifacts get a document skeleton added when published; GitHub Pages doesn't. meta: page_meta()'s tags."""
    import site_meta
    from urllib.parse import urljoin
    # The links to the front page and About show from the start (the page would set them once loaded: they mustn't
    # push the title down).
    nav = '<nav class="home-link" id="siteNav" aria-label="Site" hidden><a id="siteHome" href="../">&larr; State Bill Tracker</a><a id="siteAboutTop" href="../about/">About</a></nav>'
    assert nav in html, "tracker.html's site links changed: update github_page()"
    html = html.replace(nav, f'<nav class="home-link" id="siteNav" aria-label="Site"><a id="siteHome" href="{html_escape(urljoin(P.SITE_URL, "../"))}">&larr; State Bill Tracker</a>'
                        f'<a id="siteAboutTop" href="{html_escape(urljoin(P.SITE_URL, "../about/"))}">About</a></nav>', 1)
    # The named lists' button and menu (lists_pages/named.js), on the public site only: tracker.html's listButton().
    named = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "lists_pages", "named.js")).read()
    html = html.replace('<script id="state-profile">', f'<script>\n{named}</script>\n<script id="state-profile">', 1)
    split = html.index('<div class="wrap">')
    return ('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
            + ROBOTS_META + meta + site_meta.support_meta() +
            '<style>body { margin: 0; } [hidden] { display: none !important; }</style>\n'
            + analytics_tags() + html[:split] + '\n</head>\n<body>\n' + html[split:] + '\n</body>\n</html>\n')


def assembly_resolver(session):
    """Turns the Assembly's short vote names ("Kelles", "Carroll P") into district numbers."""
    path = os.path.join(P.DATA, f"contacts_{session}.json")
    seats = json.load(open(path)).get("people", {}) if os.path.exists(path) else {}
    by_last = defaultdict(list)
    for seat, p in seats.items():
        if seat[0] == "A":
            words = p["key"].split()
            by_last[words[-1]].append((words[0], int(re.match(r"\d+", seat[2:]).group())))
    cache = {}

    def resolve(short):
        if short in cache:
            return cache[short]
        parts = short.replace(".", "").split()
        last = re.sub(r"[^a-z-]", "", parts[0].lower()) if parts else ""
        # Multi-word last names ("Pheffer Amato", "De Los Santos"): try the whole name, then its end.
        full = re.sub(r"[^a-z\s-]", "", short.lower())
        initials = parts[-1] if len(parts) > 1 and parts[-1].isupper() and len(parts[-1]) <= 3 else ""
        cands = by_last.get(full.replace(" " + initials.lower(), "").split()[-1] if initials else full.split()[-1], []) if full else []
        if not cands and full:
            # The Assembly cuts long names short ("Chandler-Waterm"): match the start of a last name.
            stem = full.split()[-1]
            cands = [c for last, cs in by_last.items() if len(stem) >= 5 and last.startswith(stem) for c in cs]
        if len(cands) > 1 and initials:
            cands = [c for c in cands if c[0][0].upper() in initials] or cands
        if short.strip().lower() in ("mr. speaker", "mr speaker", "madam speaker") and "A" in P.LEADERS:
            speaker = name_key(P.LEADERS["A"][0]).split()
            cands = [c for c in by_last.get(speaker[-1], []) if c[0] == speaker[0]]
        cache[short] = cands[0][1] if len(cands) == 1 else None
        return cache[short]
    return resolve


def parties(session, recs):
    """Party ("D" or "R") for each legislator name as the bill data spells it, keyed by
    (house, name). Names are tied to parties through the seat each sponsor holds: sitting
    members from the contacts file, earlier holders from the Open States archive. A state's converter
    can supply its own (New Jersey's come from each session's roster)."""
    if hasattr(C, "parties"):
        return C.parties(session, recs)
    path = os.path.join(P.DATA, f"contacts_{session}.json")
    seats = json.load(open(path)).get("people", {}) if os.path.exists(path) else {}
    hpath = os.path.join(P.DATA, "seat_parties.json")
    history = json.load(open(hpath)) if os.path.exists(hpath) else {}
    by_last = defaultdict(set)
    for seat, holders in history.items():
        for h in holders:
            if name_key(h["last"]).split():
                by_last[(seat[0], name_key(h["last"]).split()[-1])].add(h["party"])

    def held(h):
        return (not h["start"] or h["start"] <= str(session + YEARS - 1)) and (not h["end"] or h["end"] >= str(session))

    out = {}
    for r in recs:
        for v in r["vers"]:
            if not v["sponsor"]:
                continue
            house, last = v["p"][0], name_key(v["sponsor"]).split()[-1]
            seat_id = f"{house}:{v.get('district')}"
            seat, code = seats.get(seat_id), None
            if seat and seat["key"].split()[-1] == last:
                p = seat.get("party") or ""
                code = "D" if "Democrat" in p else "R" if "Republican" in p else None
            if not code:
                code = next((h["party"] for h in history.get(seat_id, [])
                             if held(h) and name_key(h["last"]).split()[-1:] == [last]), None)
            if not code and len(by_last.get((house, last), ())) == 1:
                code = next(iter(by_last[(house, last)]))
            if code:
                out[(house, v["sponsor"])] = code
    return out


def bill_parties(r, party_of):
    """How many sponsors and co-sponsors of each party are on either version: [D, R]."""
    found = {}
    for v in r["vers"]:
        for n in [v["sponsor"]] + v.get("cosponsors", []):
            p = party_of.get((v["p"][0], n))
            if p:
                found[(v["p"][0], n)] = p
    vals = list(found.values())
    return [vals.count("D"), vals.count("R")]


def sponsor_class(r, party_of):
    """The bill's sponsors' party, for the issue pages' "Sponsor's party" menu: "D" or "R" when every prime (main)
    sponsor whose party is known is of that party, "B" (both parties) when the prime sponsors include both, or when the
    other party has at least one in five of the bill's sponsors and co-sponsors with a known party (so one Democrat among
    twenty Republicans doesn't make a bill bipartisan, but a Republican and a Democrat together do), and "" when no
    prime sponsor is a member with a known party (committee bills, bills by request, Nebraska's nonpartisan Legislature).
    Only Democrats and Republicans count: independents and third parties don't make a bill bipartisan."""
    primes, everyone = {}, {}
    for v in r["vers"]:
        house = v["p"][0]
        names = [v["sponsor"]] + v.get("cosponsors", [])
        k = max(1, v.get("primes") or 1)
        for i, n in enumerate(names):
            p = party_of.get((house, n)) if n else None
            if p not in ("D", "R"):
                continue
            everyone[(house, n)] = p
            if i < k:
                primes[(house, n)] = p
    lead = set(primes.values())
    if not lead:
        return ""
    if len(lead) == 2:
        return "B"
    x = lead.pop()
    other = sum(1 for p in everyone.values() if p != x)
    return "B" if other and other * 5 >= len(everyone) else x


def legislators(session):
    """Current legislators with a short page address each: last name, or first-last when shared."""
    path = os.path.join(P.DATA, f"contacts_{session}.json")
    if not os.path.exists(path):
        return []
    raw = json.load(open(path))
    seats = raw.get("people", {})
    since = raw.get("since", {})
    last = lambda p: p["key"].split()[-1]

    def committees_of(seat, p):
        house = seat[0]
        src = raw.get("senateCommittees" if house == "S" else "assemblyCommittees", {})
        def same(n):
            # Committee lists spell names their own way ("Patrick J. Carroll"); match on the
            # last name when it's unique in the house, else last name and first initial.
            k = name_key(n)
            if not k or k.split()[-1] != last(p):
                return False
            return k == p["key"] or house_counts[(house, last(p))] == 1 or k[0] == p["key"][0]
        found = [(c["name"], same(c.get("chair") or "")) for c in src.values() if any(same(m) for m in c.get("members", []))]
        return [{"name": n.replace(" And ", " and "), "chair": ch} for n, ch in sorted(found, key=lambda x: (not x[1], x[0]))]
    counts = Counter(last(p) for p in seats.values())
    house_counts = Counter((seat[0], last(p)) for seat, p in seats.items())
    out = []
    for seat, p in sorted(seats.items(), key=lambda kv: kv[1]["key"].split()[-1]):
        # "A:12", or "A:12a" where a district has two Assembly members.
        house, district = seat[0], re.match(r"\d+", seat[2:]).group()
        slug = last(p) if counts[last(p)] == 1 else p["key"].replace(" ", "-")
        out.append({"id": seat, "slug": slug, "name": p["name"], "title": TITLES[house],
                    "house": house, "district": int(district), "email": p.get("email"), "phone": p.get("phone"), "phones": p.get("phones"),
                    "form": p.get("form"), "url": p.get("url"), "party": p.get("party"), "image": p.get("image"),
                    "since": since.get(seat), "committees": committees_of(seat, p)})
    return out


def contacts_for(session, recs, delegation_names):
    """Who to contact for the current session: committee chairs (and whether our legislators
    sit on each committee), our legislators, and email, phone and page for each person."""
    path = os.path.join(P.DATA, f"contacts_{session}.json")
    if not os.path.exists(path):
        return None
    raw = json.load(open(path))
    seats = raw.get("people", {})  # "S:52" -> {name, key, email, phone, url}
    asm_members = raw.get("assemblyMembers", {})
    people = {}

    def lookup(name, house, district=None):
        """Contact details for a legislator, by seat when known (checking it's the same person)."""
        key = name_key(name)
        if not key.split():
            return {}  # no name ("—" for a bill with no listed sponsor)
        p = seats.get(f"{house}:{district}") if district else None
        if p and p["key"].split()[-1] != key.split()[-1]:
            p = None  # someone else holds that seat now
        if not p:
            hits = [v for k, v in seats.items() if k[0] == house and v["key"] == key]
            if not hits:
                hits = [v for k, v in seats.items() if k[0] == house and v["key"].split()[-1] == key.split()[-1]]
            p = hits[0] if len(hits) == 1 else None
        if p:
            return {"url": p["url"], "email": p["email"], "phone": p["phone"], "phones": p.get("phones"), "form": p.get("form")}
        if house == "S" and getattr(P, "SENATOR_URLS", False):
            return {"url": senate_url(name)}
        m = asm_members.get(key) or {}
        return {"url": m.get("url"), "email": m.get("email")}

    def person(name, house, district=None):
        if name and name not in people:
            people[name] = lookup(name, house, district)
        return name

    ours = {"S": set(delegation_names.get("SENATE", [])), LOW: set(delegation_names.get("ASSEMBLY", []))}

    def ours_on(members, house):
        return sorted({n for n in ours[house] for m in members if name_key(m).endswith(" " + n.lower())})

    def serving(name, house):
        return bool(name) and (not seats or any(k[0] == house and v["key"].split()[-1] == name_key(name).split()[-1] for k, v in seats.items()))

    committees = {}
    for house, key in (("S", "senateCommittees"), (LOW, "assemblyCommittees")):
        for k, c in raw.get(key, {}).items():
            committees[f"{house}:{k}"] = {
                "name": c["name"],
                # A chair carried over from last session's committees counts only while still serving.
                "chair": person(c.get("chair"), house) if serving(c.get("chair"), house) else None,
                "meets": c.get("meets"),
                "url": c.get("url"),
                "ours": ours_on(c.get("members", []), house),
                # For telling when a bill's sponsors make up most of the committee it's stuck in.
                "members": c.get("members", []),
            }
    for r in recs:
        for v in r["vers"]:
            person(v["sponsor"], v["p"][0], v.get("district"))
    reps = []
    for house, title in (("S", TITLES["S"]), (LOW, TITLES[LOW])):
        for district in sorted(P.delegation(session).get("SENATE" if house == "S" else "ASSEMBLY", ())):
            seat = seats.get(f"{house}:{district}")
            if seat and seat["key"].split()[-1] in {n.lower() for n in ours[house]}:
                name = next((n for n in people if name_key(n) == seat["key"]), seat["name"])
                people.setdefault(name, lookup(name, house, district))
                reps.append({"title": title, "name": name, "house": house, "last": seat["key"].split()[-1]})
    leaders = {}
    # Leaders as the state's own sites name them (Virginia's contacts carry them), else the profile's list. A
    # leader's pronoun comes from the profile when it names the same person, else "them".
    listed = {h: (v["name"], v["role"], next((pr for n, _, pr in [P.LEADERS.get(h, ("", "", ""))] if n and name_key(n) == name_key(v["name"])), "them"))
              for h, v in raw.get("leaders", {}).items()}
    for house, (name, role, pronoun) in {**P.LEADERS, **listed}.items():
        if any(k[0] == house and v["key"] == name_key(name) for k, v in seats.items()):
            person(name, house)
            leaders[house] = {"name": name, "role": role, "pronoun": pronoun}
        elif (raw.get("leaders", {}).get(house) or {}).get("phone"):
            # A leader who isn't a member (Texas's Lieutenant Governor, who presides over the Senate): the contacts
            # file gives their own details and title.
            v = raw["leaders"][house]
            people[name] = {"url": v.get("url"), "email": v.get("email"), "phone": v["phone"], "phones": v.get("phones"),
                            "form": v.get("form"), "title": v.get("title")}
            leaders[house] = {"name": name, "role": role, "pronoun": pronoun}
    return {"fetched": raw.get("fetched"), "committees": committees, "people": people, "reps": reps, "leaders": leaders}


def choose_page(legs):
    """A small page for a shared last name: pick which legislator you meant."""
    last = legs[0]["name"].split()[-1]
    items = "\n".join(
        f'<li><a href="../{l["slug"]}/">{l["title"]} {html_escape(l["name"])}</a> '
        f'<span>{P.seat_name(l["house"], l["district"]) if hasattr(P, "seat_name") else ("Senate" if l["house"] == "S" else getattr(P, "LOWER_NAME", "Assembly")) + " District " + str(l["district"])}</span></li>' for l in legs)
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
{ROBOTS_META.strip()}<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'><rect width='64' height='64' rx='14' fill='%231d3b78'/><path d='M32 10 52 23H12z' fill='%23fff'/><rect x='14' y='25' width='36' height='4' fill='%23fff'/><rect x='17' y='31' width='6' height='16' fill='%23fff'/><rect x='29' y='31' width='6' height='16' fill='%23fff'/><rect x='41' y='31' width='6' height='16' fill='%23fff'/><rect x='11' y='49' width='42' height='5' fill='%23e3b04b'/></svg>"><title>Which {html_escape(last)}? · {P.SITE_NAME}</title>
<style>
:root {{ --bg: #f5f7f8; --fg: #132a2e; --muted: #46575c; --link: #007c83; color-scheme: light; }}
@media (prefers-color-scheme: dark) {{ :root {{ --bg: #0f1515; --fg: #e4eded; --muted: #a2b3b5; --link: #4cc3be; color-scheme: dark; }} }}
body {{ margin: 0; background: var(--bg); color: var(--fg); font: 16px/1.5 system-ui, -apple-system, "Segoe UI", sans-serif; padding: 40px max(16px, env(safe-area-inset-left, 0px)); }}
main {{ max-width: 560px; margin: 0 auto; }} h1 {{ font-size: 26px; margin: 0 0 16px; }}
ul {{ list-style: none; padding: 0; margin: 0 0 24px; display: grid; gap: 12px; }} a {{ color: var(--link); font-weight: 600; }}
li span {{ color: var(--muted); font-size: 14px; margin-left: 8px; }}
</style></head><body><main>
<h1>Which {html_escape(last)}?</h1>
<ul>
{items}
</ul>
<p><a href="../">All bills</a></p>
</main></body></html>
"""


def html_escape(x):
    return str(x).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")

# ---- Statistics people can act on ----
# Titles of laws that are local or ceremonial (naming a road, one property's tax exemption,
# one town's arrangement), counted separately from substantive laws.
CEREMONIAL = re.compile(
    r"designat|dedicat|\bnam(e|es|ing)\b.*\b(highway|bridge|road|route|interchange|building)|"
    r"(to file|to receive|retroactive).*(exemption|exempt status)|real property tax exemption|"
    r"legaliz\w*,? validat|in the (town|village|city|county) of|of the (town|village|city|county) of|"
    r"authoriz\w* (the )?(town|village|city|county|school district|fire district)", re.I)


def reached(r):
    """How far a bill ever got this session (not where it is now)."""
    k = r["keyDates"]
    passed_s, passed_a = bool(k[1]), bool(k[2])
    return {
        "floor": bool(k[0]) or passed_s or passed_a,
        "passS": passed_s,
        "passA": passed_a,
        # Each house passing its own version, or passing in different years, isn't passing both.
        "both": r["stage"] >= 3,
        "law": r["stage"] == 5,
    }


def without_shells(loaded, hist):
    """Illinois's shell bills (placeholders never rewritten into real bills) left out of the statistics, with each
    session's history renumbered to match."""
    keep = {s: [i for i, r in enumerate(loaded[s][0]) if not r.get("shell")] for s in loaded}
    return ({s: ([loaded[s][0][i] for i in keep[s]],) + tuple(loaded[s][1:]) for s in loaded},
            {s: defaultdict(dict, {k: hist[s][i] for k, i in enumerate(keep[s]) if i in hist[s]}) for s in loaded})


def insights(loaded, hist, current):
    shells = sum(1 for s in loaded for r in loaded[s][0] if r.get("shell"))
    loaded, hist = without_shells(loaded, hist)
    # The session still running never counts as past, also on a page for an earlier session of another kind.
    past = [s for s in sorted(loaded) if s != current and s != CURRENT]
    # States whose sessions alternate between long and short (Oregon, Connecticut): compare a session only with past
    # sessions of the same kind, when there is one. A 35-day session with 300 bills isn't a slow 160-day one.
    past_kind = P.session_kind(current) if hasattr(P, "session_kind") else ""
    if past_kind and any(P.session_kind(s) == past_kind for s in past):
        past = [s for s in past if P.session_kind(s) == past_kind]
    # Each topic also comes as "t|g" (general bills only: not about one place, person or group, nor a
    # naming), and "all|n" covers the narrow ones, for the Statistics switch and each bill's odds line.
    base = ["all"] + list(P.TOPICS)
    topics = base + [t + "|g" for t in base] + ["all|n"]

    def has(r, t):
        t, _, kind = t.partition("|")
        if kind and (kind == "n") != narrow_bill(r):
            return False
        return t == "all" or t in r["topics"]

    current_comms = {f"{h} · {n}" for r in loaded[current][0] for h, n, _ in r["firstComms"]}
    # A new session has few bills in its first weeks; until then, use the committees of the one before.
    if len(loaded[current][0]) < 2000 and past:
        current_comms |= {f"{h} · {n}" for r in loaded[past[-1]][0] for h, n, _ in r["firstComms"]}

    # Where bills die: share of bills each committee let out, current session and past sessions.
    def committee_table(sessions, minimum=True):
        out = {t: defaultdict(lambda: [0, 0, 0]) for t in topics}
        for s in sessions:
            for r in loaded[s][0]:
                for house, name, left in r["firstComms"]:
                    for t in topics:
                        if has(r, t):
                            c = out[t][f"{house} · {name}"]
                            c[0] += 1
                            c[1] += left
                            c[2] += r["stage"] == 5
        # Only committees that exist this session; defunct ones would only confuse. Every one of those is shown (each row
        # gives its number of bills, so a share from a handful reads as what it is).
        return {t: {k: v for k, v in d.items() if k in current_comms and (not minimum or v[0] >= (40 if t == "all" else 15))} for t, d in out.items()}

    # What usually happens next: of bills that reached each point, how many became law.
    odds = {t: defaultdict(lambda: [0, 0]) for t in topics}
    for s in past:
        for r in loaded[s][0]:
            got = reached(r)
            points = {"intro": True, "floor": got["floor"], "passS": got["passS"], "passA": got["passA"], "both": got["both"],
                      "house": got["passS"] or got["passA"], "vetoed": r["stage"] == 6,
                      # Vetoed, then the veto overridden: a law, but the governor said no.
                      "overridden": r["stage"] == 5 and bool(r["keyDates"][6])}
            for t in topics:
                if has(r, t):
                    for p, ok in points.items():
                        if ok:
                            odds[t][p][0] += 1
                            odds[t][p][1] += got["law"]

    # Timing: how much floor action comes at the very end of each year's session.
    timing = []
    for s in past:
        for year in range(s, s + YEARS):
            dates = [d for r in loaded[s][0] for i in (1, 2) for d in r["keyDates"][i].split(";") if d.startswith(str(year))]
            if not dates:
                continue
            # The regular session ends in June; later votes are special sessions.
            regular = [d for d in dates if d <= f"{year}-07-15"]
            if not regular:
                continue
            # A one-day special session (e.g. July 2022) isn't the end of the regular session:
            # use the last day with a full slate of votes.
            per_day = Counter(regular)
            # (Ohio's Legislature meets all year, and some years have no day with 20 passages: then the last one.)
            last = max((d for d, n in per_day.items() if n >= 20), default=max(regular))
            from datetime import date, timedelta
            cut = (date.fromisoformat(last) - timedelta(days=21)).isoformat()
            timing.append({"year": year, "votes": len(regular), "lastVote": last,
                           "final3wk": sum(cut < d <= last for d in regular)})
    signed = [r["keyDates"][5] for s in past for r in loaded[s][0] if r["keyDates"][5]]
    # The governor's decisions: by month (past sessions) and by calendar year (all sessions).
    gov_months = defaultdict(lambda: [0, 0])
    gov_years = defaultdict(lambda: [0, 0, 0])  # signed, vetoed (overridden or not), of those overridden
    for s in sorted(loaded):
        for r in loaded[s][0]:
            for i, kind in ((5, 0), (6, 1)):
                d = r["keyDates"][i]
                # A veto is the governor's decision even when it was overridden: the override (a "signed" date in
                # some states' records) isn't also counted as signing it.
                if not d or (kind == 0 and r["keyDates"][6]):
                    continue
                if kind == 1 and r["stage"] == 5:
                    gov_years[f"{d[:4]}|{P.governor_on(d)}"][2] += 1
                who = P.governor_on(d)
                if s != current:
                    gov_months[f"{who}|{d[5:7]}"][kind] += 1
                gov_years[f"{d[:4]}|{who}"][kind] += 1
    late_sign = sum(d[5:7] in ("10", "11", "12") for d in signed)

    # Persistence: how many earlier sessions laws took, and what happens to bills that die.
    persist = {t: [0, 0, 0, 0, 0] for t in topics}  # laws with 0, 1, 2, 3+ earlier sessions; total
    for s in past[1:]:
        for i, r in enumerate(loaded[s][0]):
            if r["stage"] != 5:
                continue
            n = len({e[0] for e in hist[s][i].values() if e[0] < s})
            for t in topics:
                if has(r, t):
                    persist[t][min(n, 3)] += 1
                    persist[t][4] += 1
    comeback = {t: [0, 0, 0] for t in topics}  # died in committee; reintroduced next session; later became law
    for s in past[:-1]:
        nxt = s + YEARS
        for i, r in enumerate(loaded[s][0]):
            if r["stage"] != 0:
                continue
            later = [e for e in hist[s][i].values() if e[0] > s]
            for t in topics:
                if has(r, t):
                    c = comeback[t]
                    c[0] += 1
                    c[1] += any(e[0] == nxt for e in later)
                    c[2] += any(e[2] == 5 for e in later)

    # Bills that sat in committee all of the first year: [bills, approved by a committee in the second year, law].
    stuck = {t: [0, 0, 0] for t in topics}
    for s in (past if YEARS > 1 else []):
        y2 = str(s + 1)
        for r in loaded[s][0]:
            kd = r["keyDates"]
            if r["first"] >= y2 or (kd[0] and kd[0] < y2):
                continue
            for t in topics:
                if has(r, t):
                    stuck[t][0] += 1
                    stuck[t][1] += bool(kd[0])
                    stuck[t][2] += r["stage"] == 5

    # Bills that died in committee, by what happened there: [died, back next session, later law].
    comm_fate = {t: {k: [0, 0, 0] for k in ("none", "amended", "held", "defeated", "passed")} for t in topics}
    for s in past[:-1]:
        for i, r in enumerate(loaded[s][0]):
            if r["stage"] != 0:
                continue
            later = [e for e in hist[s][i].values() if e[0] > s]
            for t in topics:
                if has(r, t):
                    c = comm_fate[t][r["commFate"]]
                    c[0] += 1
                    c[1] += any(e[0] == s + YEARS for e in later)
                    c[2] += any(e[2] == 5 for e in later)

    # What happened to bills that died, by how far they got: [died, back next session, later law].
    fate = {t: {k: [0, 0, 0] for k in ("committee", "floor", "oneHouse", "vetoed")} for t in topics}
    for s in past[:-1]:
        nxt = s + YEARS
        for i, r in enumerate(loaded[s][0]):
            k = {0: "committee", 1: "floor", 2: "oneHouse", 6: "vetoed"}.get(r["stage"])
            if not k:
                continue
            later = [e for e in hist[s][i].values() if e[0] > s]
            for t in topics:
                if has(r, t):
                    c = fate[t][k]
                    c[0] += 1
                    c[1] += any(e[0] == nxt for e in later)
                    c[2] += any(e[2] == 5 for e in later)

    # The current session's most persistent bills: introduced in the most earlier sessions.
    cur_recs = loaded[current][0]
    tries = []
    for i, r in enumerate(cur_recs):
        earlier = sorted({e[0] for e in hist[current][i].values() if e[0] < current})
        if len(earlier) >= 3:
            best = max((e[2] for e in hist[current][i].values() if e[0] < current), default=-1)
            tries.append((len(earlier), i, earlier[0], best))
    tries.sort(key=lambda x: (-x[0], -rank(x[3]) if x[3] >= 0 else 1, x[1]))
    persistent = {}
    for t in topics:
        if "|" in t:
            continue
        rows = [x for x in tries if has(cur_recs[x[1]], t)][:12]
        persistent[t] = [[cur_recs[i]["nums"][0], cur_recs[i]["title"], n, first, best, cur_recs[i]["stage"]] for n, i, first, best in rows]

    # Co-sponsor counts and outcomes, past sessions: [bills, passed both houses, became law] per range.
    cosp_bins = [(0, 0), (1, 4), (5, 9), (10, 19), (20, 39), (40, 10 ** 6)]
    cosp = {t: [[0, 0, 0] for _ in cosp_bins] for t in topics}
    for s in past:
        for r in loaded[s][0]:
            j = next(i for i, (lo, hi) in enumerate(cosp_bins) if lo <= r["cosp"] <= hi)
            for t in topics:
                if has(r, t):
                    c = cosp[t][j]
                    c[0] += 1
                    c[1] += r["stage"] >= 3
                    c[2] += r["stage"] == 5

    # The same by party of sponsors and co-sponsors: both parties, Democrats only, Republicans only.
    party = {}
    for s in sorted(loaded):
        party_of = parties(s, loaded[s][0])
        key = "past" if s != current else "current"
        for r in loaded[s][0]:
            d, rep = bill_parties(r, party_of)
            k = "DR" if d and rep else "D" if d else "R" if rep else None
            if not k:
                continue
            for t in topics:
                if has(r, t):
                    c = party.setdefault(key, {}).setdefault(t, {}).setdefault(k, [0, 0, 0])
                    c[0] += 1
                    c[1] += r["stage"] >= 3
                    c[2] += r["stage"] == 5

    # When things happen, by month of the two-year session (0-11 first year, 12-23 second):
    # bills introduced, first approved by a committee, first passed by each house.
    def month_counts(sessions):
        out = {t: {k: [0] * (12 * YEARS) for k in ("intro", "comm", "passS", "passA", "signed", "vetoed")} for t in topics}
        for s in sessions:
            for r in loaded[s][0]:
                k = r["keyDates"]
                when = {"intro": r["first"] or "", "comm": k[0], "passS": k[1].split(";")[0], "passA": k[2].split(";")[0],
                        # A veto counts as one even when overridden; the override isn't the governor signing it.
                        "signed": k[5] if r["stage"] == 5 and not k[6] else "", "vetoed": k[6] or ""}
                for key, d in when.items():
                    if len(d) < 7 or d[:4] > str(s + YEARS - 1):
                        continue
                    # Bills prefiled in late fall count as introduced when the session opens.
                    if d[:4] < str(s):
                        d = f"{s}-01"
                    m = (int(d[:4]) - s) * 12 + int(d[5:7]) - 1
                    for t in topics:
                        if has(r, t):
                            out[t][key][m] += 1
        return out

    # Bills that passed both houses but that the governor's office still hadn't requested on
    # today's date in the same year of past sessions: how many became law. Bills still waiting
    # late in the year are more often vetoed than bills overall.
    from datetime import date, datetime
    from zoneinfo import ZoneInfo
    today = datetime.now(ZoneInfo(P.TIMEZONE)).date()
    year = today.year - current
    waiting = None
    if year in (0, 1):
        md = today.strftime("%m-%d")
        n = law = 0
        kinds = {"g": [0, 0], "n": [0, 0]}
        for s in past:
            cut = f"{s + year}-{md}"
            for r in loaded[s][0]:
                k = r["keyDates"]
                ps, pa = k[1].split(";")[0], k[2].split(";")[0]
                decided = min(filter(None, [k[5], k[6]]), default="")
                if not (ps and pa) or max(ps, pa) > cut or (decided and decided <= cut) or (k[4] and k[4] <= cut):
                    continue
                n += 1
                law += r["stage"] == 5
                kind = "n" if narrow_bill(r) else "g"
                # By kind, and by topic within kind ("env|g"), for each bill's own odds line.
                for key in [kind] + [f"{tp}|{kind}" for tp in r["topics"]]:
                    kk = kinds.setdefault(key, [0, 0])
                    kk[0] += 1
                    kk[1] += r["stage"] == 5
        waiting = {"date": md, "year": year, "n": n, "law": law, "kinds": kinds}

    # How the governor's office has asked for bills in this month of past years: how many large
    # batches (days with 10 or more bills requested), days from request to decision, and when the
    # bills still waiting on today's date were requested later that year. Only the current governor.
    requests = None
    mm = today.strftime("%m")
    asked = defaultdict(int)   # request day -> bills
    lags, later = [], defaultdict(int)
    for s in sorted(loaded):
        for r in loaded[s][0]:
            k = r["keyDates"]
            d = k[4].split(";")[-1]
            if not d or d < P.GOV_SINCE:
                continue
            decided = min(filter(None, [k[5], k[6]]), default="")
            # Earlier requests this year count toward the time to a decision; the rest uses whole years.
            if d[5:7] == mm and decided:
                lags.append((date.fromisoformat(decided) - date.fromisoformat(d)).days)
            if d[:4] >= str(today.year):
                continue
            asked[d] += 1
            ps, pa = k[1].split(";")[0], k[2].split(";")[0]
            if ps and pa and max(ps, pa) <= f"{d[:4]}-{today:%m-%d}" < d:
                later[d[5:7]] += 1
    years = sorted({d[:4] for d in asked if d[:7] >= P.GOV_SINCE[:7] and d[5:7] == mm} |
                   {str(y) for y in range(int(P.GOV_SINCE[:4]) + (P.GOV_SINCE[5:7] > mm), today.year)})
    if len(years) >= 3 and len(lags) >= 30:
        batches = sorted(sum(1 for d, n in asked.items() if d[:7] == f"{y}-{mm}" and n >= 10) for y in years)
        total = sum(later.values())
        requests = {"month": int(mm), "batches": [batches[len(batches) // 4], batches[3 * len(batches) // 4]],
                    "days": sorted(lags)[len(lags) // 2],
                    "later": sorted([int(m), round(100 * n / total)] for m, n in later.items()) if total >= 30 else []}

    return {
        "shells": shells,
        "waiting": waiting,
        "requests": requests,
        "months": month_counts(past),
        "monthsNow": month_counts([current]),
        "cosponsors": cosp,
        "party": party,
        "fate": fate,
        "commFate": comm_fate,
        "persistent": persistent,
        "pastSessions": past,
        "pastKind": past_kind if past_kind and all(P.session_kind(s) == past_kind for s in past) else "",
        "committees": {"current": committee_table([current], minimum=False), "past": committee_table(past, minimum=False)},
        "odds": {t: dict(v) for t, v in odds.items()},
        "timing": timing,
        "lateSigning": [late_sign, len(signed)],
        "govMonths": dict(sorted(gov_months.items())),
        "govYears": [[k.split("|")[0], k.split("|")[1], v[0], v[1], v[2]] for k, v in sorted(gov_years.items())],
        "persistence": persist,
        "comeback": comeback,
        "stuck": stuck,
    }


def write_compare(done, hist, current, insight):
    """Each finished session's odds chart numbers, for /compare/ and the front page's "Bills that became law" map
    (compare_site.py), into data/compare.json. Counted as insights() counts its odds chart (reached(), the same steps),
    one session at a time, with what skews comparisons left out: placeholder bills (shell), narrow bills (local, person,
    naming: the Statistics tab's "general bills") and constitutional amendments. As a check, the same counts with the
    amendments kept, summed over the sessions the Statistics tab pools, must equal its "general bills" odds chart.
    {"state", "name", "years", "chart": {sankey settings}, "sessions": [{"session", "label", "kind", "odds": {step: [bills,
    of them law]}, "cfate": {how it died in committee: [bills]}, "fate": {where it died: [died, back next session, later
    law]} (when the next session is downloaded), "left": {"shell", "narrow", "const"}}]}."""
    loaded, hist_ = without_shells(done, hist)
    js = open(os.path.join(os.path.dirname(P.__file__), "profile.js")).read()
    pick = lambda pat: (m.group(1) if (m := re.search(pat, js)) else None)
    exits = re.search(r'\n  oddsExits: \["([^"]*)", "([^"]*)"\]', js)
    chart = {"uni": LOW == "L" or bool(pick(r'\n  passedBothText: "([^"]*)"')),
             "passedBoth": pick(r'\n  passedBothText: "([^"]*)"') or "Passed both houses",
             "exits": [exits.group(1), exits.group(2)] if exits else None,
             "heldLabel": pick(r'\n  heldLabel: "([^"]*)"'), "exec": "the President" if STATE == "us" else "the governor",
             "linked": any(e[0] < s for s in loaded for d in hist_[s].values() for e in d.values())}
    sessions, check = [], defaultdict(lambda: [0, 0])
    for s in sorted(loaded):
        if s >= current or s == CURRENT:
            continue
        recs = loaded[s][0]
        odds, cfate, fate = defaultdict(lambda: [0, 0]), {}, {}
        left = {"shell": sum(1 for r in done[s][0] if r.get("shell")), "narrow": 0, "const": 0}
        nxt = s + YEARS in loaded
        for i, r in enumerate(recs):
            if narrow_bill(r):
                left["narrow"] += 1
                continue
            got = reached(r)
            points = {"intro": True, "floor": got["floor"], "passS": got["passS"], "passA": got["passA"], "both": got["both"],
                      "house": got["passS"] or got["passA"], "vetoed": r["stage"] == 6,
                      "overridden": r["stage"] == 5 and bool(r["keyDates"][6])}
            for p, ok in points.items():
                if ok:
                    check[(s, p)][0] += 1
                    check[(s, p)][1] += got["law"]
            if "const" in (r["topics"] or []):
                left["const"] += 1
                continue
            for p, ok in points.items():
                if ok:
                    odds[p][0] += 1
                    odds[p][1] += got["law"]
            later = [e for e in hist_[s][i].values() if e[0] > s]
            back, law = any(e[0] == s + YEARS for e in later), any(e[2] == 5 for e in later)
            if r["stage"] == 0:
                c = cfate.setdefault(r["commFate"], [0, 0, 0])
                c[0] += 1
                c[1] += back
                c[2] += law
            k = {0: "committee", 1: "floor", 2: "oneHouse", 6: "vetoed"}.get(r["stage"])
            if k and nxt:
                c = fate.setdefault(k, [0, 0, 0])
                c[0] += 1
                c[1] += back
                c[2] += law
        sessions.append({"session": s, "label": P.session_label(s), "kind": P.session_kind(s) if hasattr(P, "session_kind") else "",
                         "odds": dict(odds), "cfate": cfate, "fate": fate if nxt else None, "left": left})
    # The check: the Statistics tab's general-bills odds chart is the same counts, amendments kept, over its sessions.
    stats = insight["odds"].get("all|g") or {}
    for p, v in stats.items():
        mine = [sum(check[(s, p)][j] for s in insight["pastSessions"]) for j in (0, 1)]
        if mine != list(v):
            print(f"compare: {p} is {mine}, the Statistics tab says {v}", file=sys.stderr)
    out = {"state": STATE, "name": "Congress" if STATE == "us" else P.STATE_NAME, "years": YEARS, "chart": chart, "sessions": sessions}
    with open(os.path.join(GITHUB, "data", "compare.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, separators=(",", ":"), ensure_ascii=False)


def profiles(session, recs, legs, party_of):
    """Each sitting legislator's numbers this session, and the median for their party in their house."""
    if not legs:
        return {}, {}
    resolve = assembly_resolver(session)
    by_seat = {L["id"]: L for L in legs}
    last_of = {L["id"]: name_key(L["name"]).split()[-1] for L in legs}
    match = member_matcher(legs)

    def seat_of(house, v):
        """The current seat of a version's sponsor: by district (a seat id like "S:52"), else by name
        (New Jersey's two Assembly members per district have ids like "A:12a")."""
        seat = f"{house}:{v.get('district')}"
        return seat if seat in by_seat else match(house, v["sponsor"], v.get("district"))
    stats = {L["id"]: {"sponsored": 0, "floor": 0, "passedHouse": 0, "both": 0, "laws": 0, "lawsLocal": 0,
                       "otherParty": 0, "floorVotes": 0, "missed": 0, "comms": {}} for L in legs}
    first_bill, votes_seen = {}, []
    for r in recs:
        got = reached(r)
        local = narrow_bill(r) or bool(CEREMONIAL.search(r["title"] or ""))
        for v in r["vers"]:
            house = v["p"][0]
            seat = seat_of(house, v)
            if seat not in stats or name_key(v["sponsor"] or "").split()[-1:] != [last_of[seat]]:
                continue
            st = stats[seat]
            st["sponsored"] += 1
            st["floor"] += got["floor"]
            st["passedHouse"] += got["passS"] if house == "S" else got["passA"]
            st["both"] += got["both"]
            # The committee their own house sent the bill to first: [bills, approved, became law].
            for h, name, left in r["firstComms"]:
                if h == house:
                    c = st["comms"].setdefault(name, [0, 0, 0])
                    c[0] += 1
                    c[1] += left
                    c[2] += got["law"]
                    break
            if got["law"]:
                st["lawsLocal" if local else "laws"] += 1
            mine = "D" if "Democrat" in (by_seat[seat].get("party") or "") else "R" if "Republican" in (by_seat[seat].get("party") or "") else None
            others = {party_of.get((vv["p"][0], n)) for vv in r["vers"] for n in [vv["sponsor"]] + vv.get("cosponsors", [])}
            st["otherParty"] += bool(mine and (others - {mine, None}))
        for v in r["vers"]:
            seat = seat_of(v["p"][0], v)
            if seat in stats and v["actions"] and name_key(v["sponsor"] or "").split()[-1:] == [last_of[seat]]:
                first_bill[seat] = min(first_bill.get(seat, "9999"), v["actions"][0][0])
        for h, kind, comm, date, y, n, ny in r["votes"]:
            if kind != "F":
                continue
            absent = set()
            for m, code in ny:
                if isinstance(m, str):
                    # Members named by seat already ("A:12a").
                    if code in ("E", "A") and m in stats:
                        absent.add(m)
                    continue
                mh, who = m
                if code in ("E", "A"):
                    d = who if mh == "S" else resolve(who)
                    if d:
                        absent.add(f"{mh}:{d}")
            votes_seen.append((h, date, absent))
    # Members who joined during the session: count only votes from their first bill on.
    late = f"{session}-03-01"
    for seat, d in first_bill.items():
        if d >= late:
            stats[seat]["start"] = d
    for h, date, absent in votes_seen:
        for seat in stats:
            if seat[0] == h and (first_bill.get(seat, "") < late or date >= first_bill[seat]):
                stats[seat]["floorVotes"] += 1
                stats[seat]["missed"] += seat in absent
    groups = defaultdict(list)
    for seat, st in stats.items():
        p = by_seat[seat].get("party") or ""
        code = "D" if "Democrat" in p else "R" if "Republican" in p else None
        if code and st["sponsored"]:
            groups[f"{seat[0]}:{code}"].append(st)

    def median(xs):
        xs = sorted(xs)
        return xs[len(xs) // 2] if len(xs) % 2 else (xs[len(xs) // 2 - 1] + xs[len(xs) // 2]) / 2

    peers = {}
    for g, sts in groups.items():
        peers[g] = {"members": len(sts)}
        for k in ("sponsored", "floor", "passedHouse", "both", "laws", "lawsLocal", "otherParty", "missed", "floorVotes"):
            peers[g][k] = median([x[k] for x in sts])
    for st in stats.values():
        st["comms"] = sorted(([k] + v for k, v in st["comms"].items()), key=lambda c: -c[1])
    return stats, peers


_PEOPLE_NOW = {}


def people_now():
    """Current legislators keyed by page slug, with the sessions each one served in (set by the build)."""
    return _PEOPLE_NOW


def person_history(loaded, current, legs):
    """Each sitting legislator's bills in every loaded session, by the name they sponsor under,
    with the typical (median) member of the same party and house that session:
    [[session, house, sponsored, passed both houses, laws, typical sponsored, typical both, typical laws]]."""
    def median(xs):
        xs = sorted(xs)
        return xs[len(xs) // 2] if len(xs) % 2 else (xs[len(xs) // 2 - 1] + xs[len(xs) // 2]) / 2

    match = member_matcher(legs)
    out = defaultdict(list)
    for s in sorted(loaded):
        recs = loaded[s][0]
        party_of = parties(s, recs)
        counts = defaultdict(lambda: [0, 0, 0])  # (house, sponsor) -> [bills, both, laws]
        district = {}
        for r in recs:
            got = reached(r)
            for v in r["vers"]:
                if v["sponsor"] and v.get("district"):
                    district[(v["p"][0], v["sponsor"])] = v["district"]
            for who in {(v["p"][0], v["sponsor"]) for v in r["vers"] if v["sponsor"]}:
                c = counts[who]
                c[0] += 1
                c[1] += got["both"]
                c[2] += got["law"]
        groups = defaultdict(list)
        for who, c in counts.items():
            if party_of.get(who):
                groups[(who[0], party_of[who])].append(c)
        typical = {g: [median([c[i] for c in cs]) for i in range(3)] for g, cs in groups.items()}
        for (house, name), c in counts.items():
            seat = match(house, name, district.get((house, name)))
            if seat:
                ty = typical.get((house, party_of.get((house, name))), [0, 0, 0])
                out[seat].append([s, house] + c + ty)
    return dict(out)


def member_matcher(legs):
    """Matches a name as bills or committee lists spell it ("Joseph P. Addabbo Jr.") to a
    current legislator listed under another form ("Joe Addabbo"): by seat when the district is
    known, else by last name within the house, else last name plus first initial."""
    by_seat = {L["id"]: L for L in legs}
    by_last = defaultdict(list)
    for L in legs:
        k = name_key(L["name"])
        if k:
            by_last[(L["id"][0], k.split()[-1])].append(L)

    def match(house, name, district=None):
        k = name_key(name or "")
        if not k:
            return None
        last = k.split()[-1]
        L = by_seat.get(f"{house}:{district}") if district else None
        if L and name_key(L["name"]).split()[-1:] == [last]:
            return L["id"]
        cands = by_last.get((house, last), [])
        for pick in (cands, [c for c in cands if name_key(c["name"]) == k], [c for c in cands if name_key(c["name"])[0] == k[0]]):
            if len(pick) == 1:
                return pick[0]["id"]
        return None
    return match


def net_counts(recs, key):
    """Co-sponsorship counts for the network chart. key(house, sponsor name) gives a node id or
    None. Returns bills sponsored per node, co-sponsor -> sponsor counts (same house), and
    Senate sponsor -> Assembly sponsor counts for bills both carried."""
    spons, w, cross = Counter(), Counter(), Counter()
    for r in recs:
        carriers = {"S": set(), LOW: set()}
        for v in r["vers"]:
            h = v["p"][0]
            s = key(h, v["sponsor"], v.get("district")) if v["sponsor"] else None
            if not s:
                continue
            spons[s] += 1
            carriers[h].add(s)
            for c in v.get("cosponsors", []):
                ck = key(h, c)
                if ck and ck != s:
                    w[(ck, s)] += 1
        for a in carriers["S"]:
            for z in carriers[LOW]:
                cross[(a, z)] += 1
    return spons, w, cross


def net_views(spons, w, cross, info, minimum=3):
    """The network for the Senate, the Assembly and both houses, as the page draws it:
    {view: {"nodes": [[id, label, party, bills]], "links": [[a, b, share, kind]]}}. Each member
    keeps their strongest few ties; the same rules as the live chart on the current page."""
    out = {}
    for sel in ("S", LOW, "B"):
        houses = ("S", LOW) if sel == "B" else (sel,)
        ids = [k for k in spons if info.get(k) and k[0] in houses]
        idset = set(ids)

        def pairs(m, kind, directed):
            res = {}
            for (a, s), c in m.items():
                if a not in idset or s not in idset or c < minimum:
                    continue
                share = c / spons[s] if directed else c / min(spons[a], spons[s])
                k = tuple(sorted((a, s)))
                p = res.setdefault(k, [k[0], k[1], 0.0, kind, 0])
                p[2] = max(p[2], share)
                p[4] += c
            return list(res.values())
        keep = {}
        groups = [(pairs(w, "co", True), 2 if sel == "B" else 4)]
        if sel == "B":
            groups.append((pairs(cross, "x", False), 2))
        # Rank ties by how many bills two members share, not by share of a sponsor's bills:
        # a member with few bills would otherwise be everyone's "strongest" tie.
        for lst, n in groups:
            for x in ids:
                mine = sorted((p for p in lst if x in p[:2]), key=lambda p: (-p[4], -p[2]))[:n]
                for p in mine:
                    keep[(p[0], p[1], p[3])] = p
        # Members with no strong ties are drawn too, as dots on their own.
        out[sel] = {"nodes": [[k, info[k][0], info[k][1], spons[k]] for k in ids],
                    "links": [[a, b, c, kind] for a, b, s, kind, c in keep.values()]}
    return out


def session_network(s, recs):
    """One session's network, with members named as that session's bills name them: from all
    bills, and from laws only (fewer bills, so 2 shared laws make a tie)."""
    party_of = parties(s, recs)
    key = lambda h, n, d=None: f"{h}:{n}" if party_of.get((h, n)) else None
    info = {f"{h}:{n}": [f"{TITLES.get(h, h)} {n}", p] for (h, n), p in party_of.items()}
    laws = [r for r in recs if r["stage"] == 5]
    return {"all": net_views(*net_counts(recs, key), info), "law": net_views(*net_counts(laws, key), info, minimum=2)}


def network_since(loaded, legs):
    """Today's members, with ties added up over every loaded session they served together."""
    key = member_matcher(legs)
    out = {}
    for kind in ("all", "law"):
        spons, w, cross = Counter(), Counter(), Counter()
        for s in sorted(loaded):
            recs = loaded[s][0] if kind == "all" else [r for r in loaded[s][0] if r["stage"] == 5]
            a, b2, c = net_counts(recs, key)
            spons += a
            w += b2
            cross += c
        out[kind] = (spons, w, cross)
    info = {}
    for L in legs:
        p = L.get("party") or ""
        code = "D" if "Democrat" in p else "R" if "Republican" in p else None
        if code:
            info[L["id"]] = [f"{L['title']} {L['name']}", code]
    return {kind: net_views(*counts, info) for kind, counts in out.items()}


# ---- Similar bills: same session, matched on the words of the title and summary and the law
# sections amended. Bills about one place, person or group (and road namings) are left out,
# since they'd only match each other.
SIM_STOP = set("""the a an of to and or for in on by with relates relating certain provides provide requires require establishes
establish authorizes authorize such any all from that this which shall may be are is as at its their other into under within
than law laws section sections act state new york department commissioner program programs including include includes
relation thereto amend amends amending enacts enact chapter""".split())
_SECTIONS = re.compile(r"§+\s*([\d\w.\-]+(?:\s*(?:,|&|-)\s*[\d\w.\-]+)*)")


def _law_terms(code):
    """'Amd §§2803 & 4902, Pub Health L' -> ['§Pub Health L:2803', '§Pub Health L:4902']"""
    out = []
    for seg in (code or "").split(";"):
        parts = seg.rsplit(",", 1)
        if len(parts) < 2:
            continue
        law = parts[1].strip()
        for m in _SECTIONS.finditer(parts[0]):
            out += [f"§{law}:{n}" for n in re.split(r"\s*(?:,|&)\s*", m.group(1)) if re.match(r"^\d", n)]
    return out


def _sim_words(text):
    out = []
    for w in re.findall(r"[a-z][a-z'-]+", text.lower()):
        w = w.strip("'-")
        if len(w) < 3 or w in SIM_STOP:
            continue
        if w.endswith("s") and len(w) > 4 and not w.endswith("ss"):
            w = w[:-1]
        out.append(w)
    return out


def similar_bills(recs, k=8, floor=0.35):
    """For each bill, up to k others with similarity >= floor, as [[index, percent], ...]."""
    import math
    n = len(recs)
    docs = []
    for r in recs:
        # A state can give a longer text to compare (California's digests) without putting it in the page.
        tf = Counter(_sim_words(r["title"]) * 2 + _sim_words((r.get("simText") or r["summary"])[:800]))
        for t in _law_terms(r["lawCode"]):
            tf[t] += 2
        docs.append(tf)
    df = Counter(t for d in docs for t in d)
    vecs = []
    for d in docs:
        v = {t: (1 + math.log(c)) * math.log(n / df[t]) for t, c in d.items() if df[t] > 1}
        top = dict(sorted(v.items(), key=lambda x: -x[1])[:30])
        norm = math.sqrt(sum(x * x for x in top.values())) or 1
        vecs.append({t: x / norm for t, x in top.items()})
    skip = [narrow_bill(r) or bool(r.get("shell")) for r in recs]  # (placeholder bills say nothing: Illinois's, Oklahoma's)
    index = defaultdict(list)
    for i, v in enumerate(vecs):
        if not skip[i]:
            for t, x in v.items():
                if df[t] <= 500:  # very common words don't say two bills are alike
                    index[t].append((i, x))
    out = []
    for i, v in enumerate(vecs):
        if skip[i]:
            out.append([])
            continue
        score = defaultdict(float)
        for t, x in v.items():
            for j, y in index.get(t, ()):
                if j != i:
                    score[j] += x * y
        best = sorted(((sc, j) for j, sc in score.items() if sc >= floor), reverse=True)[:k]
        out.append([[j, round(sc * 100)] for sc, j in best])
    return out


def topic_ring(loaded):
    """The order of topics around the "Who works on what" ring: the arrangement where neighbors most often
    share bills, all the way around (exact, by dynamic programming; 13 topics is small). Fixed across
    sessions so the picture doesn't shift from day to day."""
    topics = [t for t in P.TOPICS if t != "const"]
    n, co = Counter(), Counter()
    for sn in loaded:
        for r in loaded[sn][0]:
            if narrow_bill(r):
                continue
            ts = [t for t in r["topics"] if t in topics]
            n.update(ts)
            for i, a in enumerate(ts):
                for b in ts[i + 1:]:
                    co[frozenset((a, b))] += 1
    # How strongly two topics go together, not just how big they are.
    w = lambda a, b: co[frozenset((a, b))] / ((n[a] * n[b]) ** 0.5 or 1)
    start = max(topics, key=lambda t: n[t])
    rest = [t for t in topics if t != start]
    k = len(rest)
    best = {(1 << i, i): (w(start, rest[i]), [i]) for i in range(k)}
    for mask in range(1, 1 << k):
        for last in range(k):
            if (mask, last) not in best:
                continue
            score, path = best[(mask, last)]
            for nxt in range(k):
                if mask & (1 << nxt):
                    continue
                key, cand = (mask | (1 << nxt), nxt), score + w(rest[last], rest[nxt])
                if key not in best or cand > best[key][0]:
                    best[key] = (cand, path + [nxt])
    full = (1 << k) - 1
    _, path = max((best[(full, last)][0] + w(rest[last], start), best[(full, last)][1]) for last in range(k))
    return [start] + [rest[i] for i in path]


def trends(loaded):
    """Per subject: bills per 1,000 in each session, the first bill on it, who sponsors most now, laws."""
    sessions = sorted(loaded)
    def scan(pattern, nocase):
        rx = re.compile(pattern, re.I if nocase else 0)
        per, first, now, laws, total = [], None, Counter(), 0, 0
        for sn in sessions:
            recs = loaded[sn][0]
            hits = [r for r in recs if rx.search(r["title"] + " . " + r["summary"][:600])]
            per.append(round(1000 * len(hits) / max(1, len(recs)), 1))
            total += len(hits)
            laws += sum(r["stage"] == 5 for r in hits)
            for r in hits:
                for v in r["vers"]:
                    if not v["sponsor"]:
                        continue
                    key = (sn, r["first"] or "", v["p"])
                    if first is None or key < first[0]:
                        first = (key, v["p"][0], v["sponsor"])
                    if sn == sessions[-1]:
                        now[(v["p"][0], v["sponsor"])] += 1
        lead = [[h, name, c] for (h, name), c in now.most_common(3)]
        return {"per": per, "bills": total, "laws": laws, "lead": lead,
                "first": [first[1], first[2], first[0][0], first[0][2]] if first else None}
    out = {"sessions": sessions, "subjects": [], "wording": []}
    for kind, label, pattern, nocase in P.TRENDS:
        out["subjects"].append({"kind": kind, "label": label, **scan(pattern, nocase)})
    for old, new, *note in P.WORDING:
        out["wording"].append({"old": [old[0], scan(old[1], True)["per"]], "new": [new[0], scan(new[1], True)["per"]] if new else None,
                               "note": note[0] if note else ""})
    return out


def outcomes(recs):
    """Counts per topic: [bills, passed both houses or further, signed, vetoed, passed one house only]."""
    out = defaultdict(lambda: [0, 0, 0, 0, 0])
    for r in recs:
        if r.get("shell"):  # Illinois's shell bills, as in insights()
            continue
        for t in ["all"] + r["topics"]:
            c = out[t]
            c[0] += 1
            c[1] += r["stage"] >= 3
            c[2] += r["stage"] == 5
            c[3] += r["stage"] == 6
            c[4] += r["stage"] == 2
    return dict(out)


def bill_texts(session, recs):
    """Bill (base number, as the page keys it) -> [sponsor's statement, committee, date, committee statement,
    fiscal summary, and (when the state's text isn't a sponsor's statement) where it's from], from
    data/<state>/texts_<session>.json when the state has one."""
    path = os.path.join(P.DATA, f"texts_{session}.json")
    if not os.path.exists(path):
        return {}
    raw = json.load(open(path))
    out = {}
    for r in recs:
        ts = [raw[n] for n in r["nums"] if n in raw]
        if not ts:
            continue
        stmt = next((t["statement"] for t in ts if t.get("statement")), "")
        comm = max((t["committee"] for t in ts if t.get("committee")), key=lambda c: c[1], default=["", "", ""])
        fisc = next((t["fiscal"] for t in ts if t.get("fiscal")), "")
        label = next((t["label"] for t in ts if t.get("label")), "")
        out[re.sub(r"[A-Z]$", "", r["nums"][0])] = [stmt, comm[0], comm[1], comm[2], fisc] + ([label] if label else [])
    return out


def write_issues(session, recs, texts, page, current, party_of=None):
    """A session's bills on each national issue (issues.py), into data/issues_<session>.json for issues_site.py, which
    builds the issue pages from every state's files, by calendar year: {"state", "name", "session", "years" (P.YEARS),
    "upcoming", "label", "page", "total" (bills counted, for scale), "active" ({year: bills introduced or acted on}), "bills": [[issue ids, {issue: [filters]}, number,
    title, stage, last action's date, "const" or "", year introduced (the session's first year at the earliest, so a
    bill prefiled in December counts in its session's year), date it became law or "", {issue: the sentence that
    matched} for titles under eight words, the record's other numbers, the sponsors' party (sponsor_class(): "D", "R", "B"
    or "")], ...]}. Local bills for one
    place and placeholder bills are left out, as in the statistics."""
    import issues
    bills, total, active = [], 0, {}
    for r in recs:
        if r.get("narrow") == "place" or r.get("shell"):
            continue
        total += 1
        # Bills introduced or acted on in each calendar year, so the map can tell a year the legislature didn't meet
        # (Texas, Montana, Nevada and North Dakota in even years) from one with no bills on an issue.
        for y in {max(session, int((r["first"] or str(session))[:4])), int((r["last"] or "0")[:4] or 0)}:
            if y:
                active[str(y)] = active.get(str(y), 0) + 1
        key = re.sub(r"[A-Z]$", "", r["nums"][0])
        t = texts.get(key) or []
        head = f"{r['title']}. {r['summary'] or ''}"
        body = " ".join(x for i, x in enumerate(t[:5]) if i in (0, 3, 4) and isinstance(x, str))
        found = issues.issues_of(head, body)
        if not found:
            continue
        both = f"{head} {body}"
        intro = max(session, int((r["first"] or str(session))[:4]))
        law = ""
        if r["stage"] == 5:
            law = (r["keyDates"][5].split(";")[-1] if len(r["keyDates"]) > 5 else "") or r["last"] or ""
        bills.append([found, {i: issues.filters_of(i, both) for i in found if issues.BY_ID[i].get("filters")},
                      r["nums"][0], r["title"], r["stage"], r["last"] or "", "const" if "const" in (r["topics"] or []) else "",
                      intro, law,
                      # Under a bare title ("Wages"), the sentence that matched, so readers see why the bill is there.
                      {i: issues.excerpt(i, head, body) for i in found} if len(r["title"].split()) < 8 else {},
                      # The record's other numbers (New York's identical Assembly and Senate bills are one record).
                      r["nums"][1:],
                      sponsor_class(r, party_of or {})])
    out = {"state": STATE, "name": P.STATE_NAME, "session": session, "years": getattr(P, "YEARS", 2),
           "upcoming": session > current,
           "label": P.session_label(session), "page": page, "total": total, "active": active, "bills": bills}
    with open(os.path.join(GITHUB, "data", f"issues_{session}.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, separators=(",", ":"), ensure_ascii=False)


def write_status(session, recs, page, live, facts=None, agenda_of=None, later_of=None):
    """Where each bill is, for the front page's "Your bills" (home.html) and /your-bills/, which show the bills a visitor
    starred on any state's page or on the front page: data/status_<session>.json, {"page", "live" (the session isn't
    over), "bills": {number without its amendment letter: [number, title, stage, last action's date, the last action,
    committee, "const" or "", and what the watchlist's deadline rules (lists_pages/watchrules.js) read: the day it went
    to the governor (stage 4), its committee meetings to come ([[when, committee]]), flags ("b" a budget bill, "v" sent
    to the voters), its version in the newest later session ([session, number])]}, "alias": {the record's other
    numbers: its first}}; the columns after the seventh are left off from the last one that's empty. The watchlist keys
    bills as "<session>:<number without the letter>". facts: the session's facts the rules read (write_status_shards())."""
    base = lambda n: re.sub(r"[A-Z]$", "", n)
    from datetime import date, timedelta
    soon = (date.today() - timedelta(days=1)).isoformat()
    bills, alias = {}, {}
    for i, r in enumerate(recs):
        lead = base(r["nums"][0])
        acts = [a for v in r["vers"] for a in v["actions"] if a[0] == r["last"]]
        deliv = (r["keyDates"][4] or "").split(";")[-1] if r["stage"] == 4 and len(r["keyDates"]) > 4 else ""
        meets = [[w, c] for c, w in (agenda_of(r) if agenda_of else []) if w >= soon]
        flags = ("b" if r.get("budget") else "") + ("v" if r.get("ballot") else "")
        later = later_of(i) if later_of else None
        extra = [deliv, meets, flags, later or ""]
        while extra and not extra[-1]:
            extra.pop()
        bills[lead] = [r["nums"][0], r["title"][:140], r["stage"], r["last"] or "", (acts[-1][1] if acts else "")[:120],
                       r["comm"] or "", "const" if "const" in (r["topics"] or []) else "", *extra]
        for n in r["nums"][1:]:
            alias[base(n)] = lead
    with open(os.path.join(GITHUB, "data", f"status_{session}.json"), "w", encoding="utf-8") as f:
        json.dump({"session": session, "page": page, "live": live, "bills": bills, "alias": alias, **({"facts": facts} if facts else {})},
                  f, separators=(",", ":"), ensure_ascii=False)
    write_status_shards(session, bills, alias, page, live, facts)


# The status file in pieces, for the pages that show a few bills from it (/list/, /your-bills/, the list editor, the
# front page's "Your bills"): data/v/<session>.<hash>.t<k>.json, {"bills": {number: row}, "alias": {other number: its
# record's number}}, a bill (or an other number) in piece shard_of(number, n). The rows are write_status()'s; an alias's
# record can be in another piece, which the reader then fetches too. Pieces of a current or upcoming session are about
# STATUS_GZ["current"] gzipped, so a list of ten bills fetches about ten small files; a past session's are bigger, to
# keep the site's file count down (each piece is a file). data/status.json lists each session's {"p": page, "l": live,
# "h": the pieces' hashes, 8 characters each, in order}; build_site.sh gathers every state's into /status.json, which
# the pages fetch (checked on each visit; the pieces are kept for good).
STATUS_GZ = {"current": 12_000, "past": 40_000}


def write_status_shards(session, bills, alias, page, live, facts=None):
    import hashlib
    target = STATUS_GZ["current" if live else "past"]
    def make(n):
        out = [{"bills": {}, "alias": {}} for _ in range(n)]
        for k, row in bills.items():
            out[shard_of(k, n)]["bills"][k] = row
        for k, lead in alias.items():
            out[shard_of(k, n)]["alias"][k] = lead
        return [json.dumps(x, separators=(",", ":"), ensure_ascii=False) for x in out]
    # The count from the whole file's size, then once more from the pieces' (each piece compresses less well).
    n = max(1, -(-len(gzip.compress(json.dumps({"b": bills, "a": alias}, ensure_ascii=False).encode(), 6)) // target))
    texts = make(n)
    if n > 1:
        again = max(1, round(sum(len(gzip.compress(t.encode(), 6)) for t in texts) / target))
        if again != n:
            n, texts = again, make(again)
    hashes = [hashlib.sha256(t.encode("utf-8")).hexdigest()[:8] for t in texts]
    os.makedirs(os.path.join(GITHUB, "data", "v"), exist_ok=True)
    for k, (h, t) in enumerate(zip(hashes, texts)):
        with open(os.path.join(GITHUB, "data", "v", f"{session}.{h}.t{k}.json"), "w", encoding="utf-8") as f:
            f.write(t)
    path = os.path.join(GITHUB, "data", "status.json")
    try:
        index = json.load(open(path))
    except (OSError, ValueError):
        index = {}
    index[str(session)] = {"p": page, "l": live, "h": "".join(hashes), **({"f": facts} if facts else {})}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(dict(sorted(index.items())), f, separators=(",", ":"), ensure_ascii=False)


# On the public site each session's data is split so that a visitor downloads only what they look at (data/v/, each
# file named by a hash of its contents, so browsers keep them for good: build_site.sh's _headers):
#   <session>.<hash>.list.json: what the first view and the filters need: every bill's numbers, stage, topics,
#     committees, sponsors, dates, places, parties and agendas, the titles and histories of the bills the list shows
#     first (FIRST_ROWS); legislators, contacts.
#   .rows.json: every bill's title, history and what else only its row, its panel and some filters read (ROW_COLS: the
#     committees, laws and parties filters, the sort by co-sponsors, How's committees), for any other list of bills and a
#     search of the titles; fetched when something needs it, or a few seconds after the list is drawn.
#   .s<k>.json, the shards: everything an opened bill shows (summary, history, co-sponsors, votes, its versions in other
#     sessions, similar bills, the governor's veto message), with the titles and histories of the similar bills it
#     names. A bill's shard is shard_of() its number, so opening a bill (or the watchlist) fetches a few small files.
#   .stats.json (statistics and legislators' profiles: an opened bill's odds line and votes, the Statistics tab),
#     .net.json (networks, and how far each bill's versions in other sessions got: the history filter, the sort by
#     sessions, the Statistics tab), .search.json (summaries, for a text search),
#     .votes.json (the vote filter, a legislator's numbers), .hist.json (other sessions' bill numbers), .cos.json
#     (co-sponsors: legislators' pages, networks), .towns.json (Congress's 35,000 places): each fetched when needed.
# The page's data tag names every file (data-parts, data-shards), so a page that outlives a deploy finds the new names.
# Per-bill columns (index in the record row, as decode() reads them) that the list part leaves empty, for all but the
# bills the list shows first: in the rows part and the shards (laws, committees, co-sponsors' count, program, law,
# parties, the main topic, the governor's signing memo, the committee it's in; and each version's co-sponsors' count,
# status and committee)...
ROW_COLS = {2: [], 3: [], 10: -1, 12: 0, 15: -1, 16: -1, 21: "", 25: "", 27: ""}
# ... and in the shards only:
DETAIL_COLS = {1: "summary", 14: "lawCode", 22: "votes", 26: "similar", 28: "vetoNote"}
DETAIL_EMPTY = {"summary": "", "lawCode": "", "votes": [], "similar": [], "vetoNote": 0}
STATS_TOP = ("insights", "profiles", "peers")
NET_TOP = ("network", "networkSince")
# A towns list this big (Congress's 35,000 places) waits; small ones are needed for the sidebar's town picker.
BIG_TOWNS = 500_000
# The list shows 100 bills at first (tracker.html's PAGE); a few more in case its order differs at the edge.
FIRST_ROWS = 150
# About how big (gzipped) a shard is on a current (or upcoming) session's page: small enough that an opened bill, or a
# watchlist of ten, comes quickly (NY, slow 4G: a bill 0.7 s, ten 1.3 s), large enough to keep the site's files well
# under Cloudflare Pages' 20,000 (22 KB doubled NY's shards for 0.6 s less on the watchlist). Past sessions have none.
SHARD_GZ = {"current": 40_000}


def shard_of(num, n):
    """Which of n shards holds a bill: FNV-1a of its first number without the version letter (tracker.html's
    shardOf() is the same)."""
    h = 0x811C9DC5
    for c in re.sub(r"[A-Z]$", "", num).encode():
        h = ((h ^ c) * 0x01000193) & 0xFFFFFFFF
    return h % n


def _keep_none(f):
    """f for indexes into the strings table, leaving -1 (no string) as it is."""
    return lambda i: i if i is None or i < 0 else f(i)


def _map_strings(cols, f):
    """The record columns with every index into the strings table passed through f (-1, no string, stays -1)."""
    g = _keep_none(f)
    out = list(cols)
    out[2] = [[g(x) for x in v] for v in cols[2]]
    out[3] = [[g(x) for x in v] for v in cols[3]]
    for i in (10, 15, 16):
        out[i] = [g(x) for x in cols[i]]
    out[17] = [[[v[0], g(v[1]), v[2], g(v[3]), g(v[4]), [[a[0], g(a[1])] for a in v[5]], [g(x) for x in v[6]]] + v[7:9]
                + [g(x) for x in v[9:]] for v in vers] for vers in cols[17]]
    out[22] = [_map_votes(v, g) for v in cols[22]]
    out[23] = [[[g(a[0])] + a[1:] for a in v] for v in cols[23]]
    out[28] = [_map_veto(v, g) for v in cols[28]]
    return out


def _map_votes(votes, f):
    g = _keep_none(f)
    return [[x[0], x[1], g(x[2])] + x[3:6] + [[[g(m), code] for m, code in x[6]]] for x in votes or []]


def _map_veto(v, f):
    return v[:2] + [_keep_none(f)(v[2])] + v[3:] if v else v


def _own_strings(T, walk):
    """A part with its own strings table: walk(f) builds the part with every string index passed through f. Returns
    (the part, its table), the table in the old table's order (so repeated wording stays together)."""
    seen = set()

    def collect(i):
        seen.add(i)
        return i
    walk(_keep_none(collect))
    order = sorted(seen)
    at = {old: k for k, old in enumerate(order)}
    return walk(_keep_none(at.__getitem__)), [T[i] for i in order]


def _gz(obj):
    return len(gzip.compress(json.dumps(obj, separators=(",", ":"), ensure_ascii=False).encode("utf-8"), 6))


def _last_name(n):
    """tracker.html's lastName(): the last word of a name, without accents, punctuation or "Jr.", in lower case."""
    import unicodedata
    n = re.sub("[\u0300-\u036f]", "", unicodedata.normalize("NFD", n or "")).lower()
    words = [w for w in re.split(r"\s+", re.sub(r"[^a-z\s-]", "", n)) if w not in ("jr", "sr", "ii", "iii")]
    return (words or [""])[-1]


def api_names(legislators, cols, T):
    """The legislators, each with apiName: the name the bill data uses for them, as tracker.html's setupLegislators()
    works it out (the sponsor name most often on bills from their seat that shares their last name, else their name)."""
    named = defaultdict(dict)
    for vers in cols[17]:
        for v in vers:
            sponsor = T[v[1]] if v[1] is not None and v[1] >= 0 else None
            if sponsor and v[7]:
                k = f"{v[0][0]}:{v[7]}"
                named[k][sponsor] = named[k].get(sponsor, 0) + 1
    out = []
    for L in legislators:
        names = sorted(((n, c) for n, c in named.get(L["id"], {}).items() if _last_name(n) == _last_name(L["name"])),
                       key=lambda x: -x[1])
        out.append({**L, "apiName": names[0][0] if names else L["name"]})
    return out


# tracker.html's walkCommittees() and meetings(), worked out here for the public site: the days each committee approved a
# bill ("S:education": [...]), which "who decides" counts (meetingsSkipped()). In the stats part, so an opened bill doesn't
# need every bill's history (the rows part) for it. Keep the two in step.
_SENT_TO = re.compile(r"^(?:REPORTED (?:AND )?|COMMITTEE DISCHARGED AND )?(?:REFERRED|COMMITTED|RECOMMITTED|AMEND(?: \(T\))? AND RECOMMIT) TO (.+?)(?: \d+[A-Z]?)?$")
_comm_key = lambda n: re.sub(r"[^a-z]", "", (n or "").lower().replace("and", ""))


def meeting_days(cols, T):
    days = defaultdict(set)
    for vers in cols[17]:
        for v in vers:
            house, comm = v[0][:1], None
            for d, t in v[5]:
                t = T[t] if isinstance(t, int) and t >= 0 else (t if isinstance(t, str) else "")
                day = f"{d[:4]}-{d[4:6]}-{d[6:8]}"
                moved = re.match(r"^(?:DELIVERED|RETURNED) TO (SENATE|ASSEMBLY)$", t)
                if moved:
                    house, comm = moved.group(1)[0], None
                    continue
                if re.match(r"^(REPORTED|1ST REPORT CAL)", t) and comm and comm != "rules":
                    days[f"{house}:{comm}"].add(day)
                m = _SENT_TO.match(t)
                if m:
                    comm = _comm_key(m.group(1))
                elif re.match(r"^(REPORTED|1ST REPORT CAL|ADVANCED|ORDERED|PASSED|REPASSED)", t):
                    comm = None
    return {k: sorted(v) for k, v in days.items()}


def split_payload(data, current=True, hooks=None):
    """The public site's files (above): (list part, {kind: part}, [shard, ...]). Constitutional amendments keep every
    field in the list part (whether one is a second passage, shown in its row, can read its summary, votes or other
    sessions), as do lawCodes naming the bills a chapter amendment changes (its row's tag). hooks: which of the state's
    settings read a bill's history to word how far it got ({"endedNote": True, "heldAction": False})."""
    hooks = hooks or {}
    cols, T = data["cols"], data["strings"]
    lst = {k: v for k, v in data.items() if k not in STATS_TOP + NET_TOP and k not in ("cols", "strings")}
    parts = {"stats": {k: data[k] for k in STATS_TOP if k in data}, "net": {k: data[k] for k in NET_TOP if k in data}}
    if data.get("towns") and len(json.dumps(data["towns"], separators=(",", ":"))) > BIG_TOWNS:
        parts["towns"] = {"towns": lst.pop("towns")}
        lst["townsLater"] = True
    lst["split"] = True
    if not cols:
        lst.update(cols=[], strings=T, rowsIn=[])
        parts["rows"] = {"title": [], "acts": [], "strings": []}
        return lst, parts, []
    n = len(cols[0])
    if current:
        parts["stats"]["meetingDays"] = meeting_days(cols, T)
    keep = {j for j, t in enumerate(cols[4]) if "const" in (t or [])}
    # The list's first page as the page orders it (sortBills()'s "recent": latest action, then furthest along; the
    # sort keeps the records' order among equals, as Python's does).
    first = set(sorted(range(n), key=lambda j: (cols[11][j], cols[6][j]), reverse=True)[:FIRST_ROWS])
    shown = keep | first
    out = list(cols)
    out[0] = [v if j in shown else "" for j, v in enumerate(cols[0])]
    for i, name in DETAIL_COLS.items():
        col = cols[i]
        if name == "lawCode":
            # (A law code is read only to find the bills a chapter amendment changes.)
            out[i] = [v if j in keep or (v and re.search(r"as proposed in", v, re.I)) else "" for j, v in enumerate(col)]
        else:
            out[i] = [v if j in keep else DETAIL_EMPTY[name] for j, v in enumerate(col)]
    # Other sessions: in the net part, each one's year and how far the bill got there (the history filter, the sort by
    # sessions, the statistics); with their numbers in the shards and the hist part.
    out[19] = [h if j in keep else [] for j, h in enumerate(cols[19])]
    parts["net"]["hist"] = [[[e[0], e[2]] for e in h] for h in cols[19]]
    for i, empty in ROW_COLS.items():
        out[i] = [v if j in shown else empty for j, v in enumerate(cols[i])]
    # Each version's co-sponsors' count (its 3rd field), status (4th), committee (5th), history (6th), co-sponsors (7th)
    # and, where the legislators are known (the name each goes by in the bill data is worked out here: api_names()), its
    # sponsor's district (8th).
    if lst.get("legislators"):
        lst["legislators"] = api_names(lst["legislators"], cols, T)
    out[17] = [vers if j in keep else [v[:2] + ([v[2], v[3], v[4], v[5]] if j in shown else [0, -1, -1, []]) + [[]]
                                       + [0 if lst.get("legislators") else v[7]] + v[8:]
                                       for v in vers]
               for j, vers in enumerate(cols[17])]
    lst["cols"], lst["strings"] = _own_strings(T, lambda f: _map_strings(out, f))
    lst["rowsIn"] = sorted(shown)
    acts = lambda j, f: [[[a[0], f(a[1])] for a in v[5]] for v in cols[17][j]]
    cos = lambda j, f: [[f(x) for x in v[6]] for v in cols[17][j]]
    # A bill's ROW_COLS: [laws, committees, co-sponsors, program, law, parties, main topic, [[co-sponsors, status,
    # committee] for each version], signing memo, committee].
    g = _keep_none
    more = lambda j, f: [[g(f)(x) for x in cols[2][j]], [g(f)(x) for x in cols[3][j]], cols[12][j], g(f)(cols[15][j]),
                         g(f)(cols[16][j]), cols[21][j], cols[25][j], [[v[2], g(f)(v[3]), g(f)(v[4])] for v in cols[17][j]],
                         cols[27][j], g(f)(cols[10][j])]
    # A chapter amendment's panel shows the memo of the law it changes (tracker.html's amendedBills(), chapterAmendment():
    # the first bill with either number): that bill comes with its shard too.
    first_with = {}
    for j in range(n):
        for v in cols[17][j]:
            first_with.setdefault(re.sub(r"[A-Z]$", "", v[0]), j)

    def changes(j):
        m = re.search(r"as proposed in (?:legislative bills? (?:numbers? )?)?S\.?\s?(\d+)[-A-Z]*\s*(?:&|and)\s*A\.?\s?(\d+)",
                      cols[14][j] or "", re.I)
        found = [first_with[k] for k in (f"S{m[1]}", f"A{m[2]}") if k in first_with] if m else []
        return {min(found)} if found else set()
    rows, rs = _own_strings(T, lambda f: [[acts(j, f), more(j, f)] for j in range(n)])
    parts["rows"] = {"title": cols[0], "acts": [x[0] for x in rows], "more": [x[1] for x in rows], "strings": rs}
    parts["search"] = {"summary": cols[1]}
    votes, vs = _own_strings(T, lambda f: [_map_votes(v, f) for v in cols[22]])
    parts["votes"] = {"votes": votes, "strings": vs}
    parts["hist"] = {"hist": cols[19]}
    c, cs = _own_strings(T, lambda f: [cos(j, f) for j in range(n)])
    parts["cos"] = {"cos": c, "strings": cs}
    # The shards. Each bill: [index, number, title, history, summary, other sessions, votes, similar bills, veto
    # message, co-sponsors, ROW_COLS]; then the similar bills they name that are in neither the shard nor the list part:
    # [index, number, title], with its history and ROW_COLS where the panel's word for how far it got can depend on the
    # history (tracker.html's endedOf(): a state's endedNote for bills that haven't passed both houses, its heldAction for
    # bills in committee).
    num = lambda j: cols[17][j][0][0]
    entry = lambda j, f: [j, num(j), cols[0][j], acts(j, f), cols[1][j], cols[19][j], _map_votes(cols[22][j], f),
                          cols[26][j], _map_veto(cols[28][j], f), cos(j, f), more(j, f)]
    if not current:
        # A past session's page, rarely visited, has no shards: its parts and every bill's details (without the titles,
        # histories and ROW_COLS, which the rows part has) are one file, "more", and "bundle" names the parts in it.
        lite = lambda j, f: [j, num(j), None, None, cols[1][j], cols[19][j], _map_votes(cols[22][j], f), cols[26][j],
                             _map_veto(cols[28][j], f), cos(j, f), None]
        shard, strings = _own_strings(T, lambda f: {"b": [lite(j, f) for j in range(n)], "x": []})
        shard["strings"] = strings
        inside = {k: parts.pop(k) for k in ("stats", "net", "towns") if k in parts}
        for k in ("search", "votes", "hist", "cos"):
            parts.pop(k)
        parts["more"] = {"parts": inside, "shard": shard}
        lst["bundle"] = list(inside) + ["search", "votes", "hist", "cos"]
        return lst, parts, []
    with_acts = lambda j: (hooks.get("endedNote") and cols[6][j] <= 2) or (hooks.get("heldAction") and cols[6][j] == 0)
    target = SHARD_GZ["current"]

    def make(count):
        members = defaultdict(list)
        for j in range(n):
            members[shard_of(num(j), count)].append(j)
        out = []
        for k in range(count):
            mine = members.get(k, [])
            whole = set().union(*[changes(j) for j in mine]) - set(mine) - shown
            extra = sorted(({x[0] for j in mine for x in cols[26][j]} | whole) - set(mine) - shown)
            part, strings = _own_strings(T, lambda f: {"b": [entry(j, f) for j in mine],
                                                       "x": [[j, num(j), cols[0][j]] + ([acts(j, f), more(j, f)] if with_acts(j) or j in whole else [])
                                                             for j in extra]})
            part["strings"] = strings
            out.append(part)
        return out
    # As many as make them about the target size: a first guess from the bills' own data, then once more from the
    # shards' real size (each carries its own strings and its similar bills' titles).
    count = max(1, -(-_gz(_own_strings(T, lambda f: [entry(j, f) for j in range(n)])) // target))
    shards = make(count)
    size = sum(_gz(x) for x in shards)
    if count > 1 or size > target * 1.5:
        again = max(1, round(size / target))
        if again != count:
            shards = make(again)
    return lst, parts, shards


def frame_tabs(page, kind):
    """The tabs as the page will show them once its data is drawn (hydrate() sets the same), so the page's frame, shown
    while the data loads, doesn't change when it arrives. kind: "past", "upcoming", "person" (a legislator's page) or
    "watch" (/watchlist/: no tabs)."""
    tab = lambda v: f'<button class="view-tab" type="button" data-view="{v}">'
    hide = {"past": ["watch", "act"], "upcoming": ["act", "stats"], "person": ["watch", "stats"]}.get(kind, [])
    for v in hide:
        page = page.replace(tab(v), tab(v)[:-1] + " hidden>", 1)
    if kind == "person":
        page = page.replace('data-view="how"><span', 'data-view="how" hidden><span', 1)
        page = page.replace(tab("person")[:-1] + " hidden>", tab("person"), 1)
        page = page.replace(tab("act") + "Weigh in<", tab("act") + "Open for comment<", 1)
    if kind == "watch":
        page = page.replace('<nav class="views" aria-label="Page sections">', '<nav class="views" aria-label="Page sections" hidden>', 1)
    return page


def hashed_name(session, kind, text):
    import hashlib
    return f"{session}.{hashlib.sha256(text.encode('utf-8')).hexdigest()[:12]}.{kind}.json"


def state_profile_js(P):
    """The state's page settings and rules (states/<code>/profile.js), as its pages and /your-bills/ read them."""
    state_js = open(os.path.join(os.path.dirname(P.__file__), "profile.js")).read()
    # Shared watchlists go to the state-lists Worker (lists_worker/); LISTS_API names another (a local test copy), as
    # in build_site.sh.
    if os.environ.get("LISTS_API"):
        state_js = re.sub(r'listsApi: "[^"]*"', f'listsApi: "{os.environ["LISTS_API"]}"', state_js)
    return state_js


def last_checked():
    """When the state's download last succeeded (data/<state>/last_checked), in the state's time zone, or None."""
    from datetime import datetime
    from zoneinfo import ZoneInfo
    folder = getattr(P, "DATA", os.path.join(HERE, "data"))
    try:
        stamp = open(os.path.join(folder, "last_checked")).read().strip()
        t = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
    except (OSError, ValueError):
        return None
    return t.astimezone(ZoneInfo(P.TIMEZONE)).strftime("%Y-%m-%d %H:%M")


def main():
    loaded = {s: C.load_session(s) for s in SESSIONS}
    # A number with no title and no dates is a placeholder the source lists before a bill exists: left out. One with
    # dates but no title yet (OH SB 342 of 2023, IL SB 4214 of 2025) gets a stand-in title.
    for s in SESSIONS:
        recs = loaded[s][0]
        recs[:] = [r for r in recs if (r.get("title") or "").strip() or r.get("first") or r.get("stage")]
        for r in recs:
            if not (r.get("title") or "").strip():
                r["title"] = "(No title in the Legislature's records yet)"  # OH SB 342 of 2023: introduced, never titled
    # For the issue pages' "Sponsor's party": a name's party from the other sessions shown, where they all agree, for a
    # session whose own records lack it (California's and Virginia's past sessions have no member lists with parties).
    seen_party = defaultdict(set)
    for s in SESSIONS:
        for k, v in parties(s, loaded[s][0]).items():
            seen_party[k].add(v)
    other_party = {k: next(iter(v)) for k, v in seen_party.items() if len(v) == 1}
    urls = json.load(open(URLS_FILE)) if os.path.exists(URLS_FILE) else {}
    current_session = CURRENT
    if GITHUB:
        urls = {str(s): ("./" if s == current_session else f"{s}.html") for s in SESSIONS}

    # Cross-session links. Each bill lists its own earlier versions; later sessions' lists
    # give the reverse direction. Entries: [session, "S1/A2", stage, chapter, veto].
    def entry(s, i):
        r = loaded[s][0][i]
        return [s, " / ".join(r["nums"]), r["stage"], r["chapter"] or 0, r["veto"] or 0]

    old_path = os.path.join(P.DATA, "old_outcomes.json.gz")
    old = json.load(gzip.open(old_path, "rt")) if os.path.exists(old_path) else {}
    hist = {s: defaultdict(dict) for s in SESSIONS}  # session -> rec index -> {(s, idx|printNo): entry}
    for s in SESSIONS:
        recs, index = loaded[s][0], loaded[s][1]
        for i, r in enumerate(recs):
            for ps, pp in r["prev"]:
                if ps in loaded and pp in loaded[ps][1]:
                    j = loaded[ps][1][pp]
                    hist[s][i][(ps, j)] = entry(ps, j)
                    hist[ps][j][(s, i)] = entry(s, i)
                elif ps in loaded:
                    # Version exists but was withdrawn (stricken), so it isn't in that session's list.
                    e = hist[s][i].setdefault((ps, "withdrawn"), [ps, "", -2, 0, 0])
                    e[1] = " / ".join(sorted(filter(None, e[1].split(" / ") + [pp]), key=lambda n: (n[0] != "S", n)))
                else:
                    # Session not downloaded: list its bill numbers together, with the outcome
                    # from the short list of older sessions when there is one.
                    e = hist[s][i].setdefault((ps, None), [ps, "", -1, 0, 0])
                    e[1] = " / ".join(sorted(filter(None, e[1].split(" / ") + [pp]), key=lambda n: (n[0] != "S", n)))
                    codes = [old.get(str(ps), {}).get(n[:1] + re.sub(r"[A-Z]+$", "", n[1:]))
                             for n in e[1].split(" / ")]
                    codes = [c for c in codes if c is not None]
                    if codes:
                        st = max((c // 4 for c in codes), key=rank)
                        flags = 0
                        for c in codes:
                            flags |= c & 3
                        e[2] = 3 if rank(st) < rank(3) and flags == 3 else st

    current = CURRENT
    # Statistics, outcomes and histories leave out an upcoming session's prefiled bills.
    done = {s: v for s, v in loaded.items() if s <= current}
    summary = {s: outcomes(loaded[s][0]) for s in done}
    insight = insights(done, hist, current)
    insight["trends"] = trends(done)
    insight["topicRing"] = topic_ring(done)
    # Where sessions alternate in kind (Arkansas's regular and fiscal sessions, Oregon's long and short ones), a page
    # for a session of another kind than the current one compares it with past sessions of its own kind: the newest
    # finished session of each kind gets its own statistics.
    insight_of = {}
    if hasattr(P, "session_kind"):
        newest = {}
        for s_ in sorted(done):
            newest[P.session_kind(s_)] = s_
        for kind, ref in newest.items():
            if kind != P.session_kind(current):
                insight_of[kind] = {**insights(done, hist, ref), "trends": insight["trends"], "topicRing": insight["topicRing"]}
    # Each finished session's odds chart, for /compare/ (compare_site.py).
    if GITHUB:
        os.makedirs(os.path.join(GITHUB, "data"), exist_ok=True)
        write_compare(done, hist, current, insight)

    # Current legislators for past sessions' pages (profile card and the sessions they served in).
    legs_now = legislators(current)
    served_by = {seat: sorted({row[0] for row in rows}) for seat, rows in person_history(done, current, legs_now).items()}
    keep = ("id", "slug", "name", "title", "party", "house", "district", "since", "image", "url", "email", "phone", "phones", "form")
    _PEOPLE_NOW.update({L["slug"]: {**{k: L.get(k) for k in keep}, "served": served_by.get(L["id"], [])} for L in legs_now if L.get("slug")})

    for session in ONLY:
        recs, _, fetched, names = loaded[session]
        # The current session is as fresh as the last successful download (data/<state>/last_checked, written by
        # download.yml), not its newest bill file: between sessions no bill may change for weeks.
        if session == current:
            fetched = max(fetched or "", last_checked() or "")
        law_count, comm_count = Counter(), Counter()
        for r in recs:
            law_count.update(r["laws"])
            comm_count.update(r["comms"])

        # Embedded in the HTML, since the page can't fetch side files. Repeated strings go
        # in one table and records become arrays to keep the page under the 16 MB limit.
        strings, sidx = [], {}

        def S(x):
            if x is None:
                return -1
            if x not in sidx:
                sidx[x] = len(strings)
                strings.append(x)
            return sidx[x]

        party_of = parties(session, recs)
        resolve = assembly_resolver(session)
        # Senate committee agendas (current session only): when a committee takes up the bill.
        apath = os.path.join(P.DATA, f"agendas_{session}.json")
        agendas = json.load(open(apath)) if session == current and os.path.exists(apath) else {}
        if session == current and hasattr(C, "agendas"):
            agendas = C.agendas(session)

        def agenda_of(r):
            seen = []
            for v in r["vers"]:
                for c, w in agendas.get(re.sub(r"[A-Z]$", "", v["p"]), []):
                    entry = [c.replace(" And ", " and "), w]
                    if entry not in seen:
                        seen.append(entry)
            return sorted(seen, key=lambda x: x[1])

        def member_id(m):
            # A state's converter may name members by id already ("A?Name").
            if isinstance(m, str):
                return m
            house, who = m
            if house == "S":
                return f"S:{who}"
            d = resolve(who)
            return f"A:{d}" if d else f"A?{who}"

        def enc_votes(votes):
            return [[h, kind, S(comm), date.replace("-", ""), y, n, [[S(member_id(m)), code] for m, code in ny]]
                    for h, kind, comm, date, y, n, ny in votes]
        def veto_note(i, r):
            """[year, governor, reasons, bill numbers, 1 if this bill's own veto, kind] or 0. Kind is
            "conditional" for a bill sent back with the governor's changes (New Jersey), else "absolute"."""
            m = r["vetoMemo"]
            # Its own message: vetoed, or (New Jersey) sent back with changes, whatever happened next.
            if m and (r["stage"] == 6 or m.get("kind") in ("conditional", "line-item")):
                return [m["year"], m["signer"], S(m["text"]), " / ".join(r["nums"]), 1, m.get("kind") or "absolute"]
            for (ps, j) in sorted((k for k in hist[session][i] if isinstance(k[1], int) and k[0] < session), reverse=True):
                old = loaded[ps][0][j]
                if old["stage"] == 6 and old.get("vetoMemo"):
                    m = old["vetoMemo"]
                    return [m["year"], m["signer"], S(m["text"]), " / ".join(old["nums"]), 0, m.get("kind") or "absolute"]
            return 0

        rows = []
        sims = similar_bills(recs)
        for i, r in enumerate(recs):
            flags = (r["local"] and 1) | (r["senDeleg"] and 2) | (r["budget"] and 4) | (r["asmDeleg"] and 8) | (r["passedS"] and 16) | (r["passedA"] and 32) | (P.NARROW_KINDS.index(r["narrow"]) << 6 if r["narrow"] != "place" else 512) | (256 if r.get("shell") else 0) | (1024 if r.get("ballot") else 0)
            vers = [[v["p"], S(v["sponsor"]), v["cosp"], S(v["statusDesc"]), S(v["committee"]),
                     [[a[0].replace("-", ""), S(a[1])] for a in v["actions"]],
                     [S(n) for n in v["cosponsors"]] if session >= current else [], v.get("district") or 0,
                      max(0, (v.get("primes") or 1) - 1)] + ([S(v["link"])] if v.get("link") else []) for v in r["vers"]]
            h = sorted(hist[session][i].values(), key=lambda e: (e[0], e[1]))
            summ = r["summary"][:2500]
            # A summary that repeats the title is stored as the rest of it, marked with \x01.
            if summ.startswith(r["title"]) and summ != r["title"] and r["title"]:
                summ = "\x01" + summ[len(r["title"]):]
            rows.append([r["title"], summ, [S(x) for x in r["laws"]], [S(x) for x in r["comms"]],
                         r["topics"], flags, r["stage"], r["passedIn"] or "", r["chapter"] or 0, r["veto"] or 0,
                         S(r["comm"]), r["last"].replace("-", ""), r["cosp"], "", r["lawCode"],
                         S(r["program"]), S(r["law"]), vers, max(session, int((r["first"] or str(session))[:4])), h,
                         [d.replace("-", "") for d in [r["first"] or ""] + r["keyDates"]],
                         bill_parties(r, party_of), enc_votes(r["votes"]),
                         [[S(c), w] for c, w in agenda_of(r)],
                         [(P.COUNTIES + ["?"]).index(c) for c in r["places"]], r["mainTopic"], sims[i], r["memo"], veto_note(i, r)])

        data = {
            "session": session,
            # An upcoming session's page works like the current one (watchlist, filters), marked as prefiled.
            "current": session >= current,
            "upcoming": session > current,
            "fetched": fetched,
            "topics": {k: v[0] for k, v in P.TOPICS.items()},
            "lawList": sorted(law_count.items()),
            "commList": sorted(comm_count.items()),
            "delegation": names,
            "sessions": [{"session": s, "url": urls.get(str(s)), **({"upcoming": True} if s > current else {})} for s in SESSIONS],
            "outcomes": {str(s): summary[s] for s in summary},
            "insights": insight_of.get(P.session_kind(session), insight) if insight_of and session < current else insight,
            # Past pages don't carry co-sponsor names, so their network is worked out here.
            "network": session_network(session, [r for r in recs if not r.get("shell")]) if session < current else None,
            # Date of the last floor vote in either house this session.
            "sessionEnd": {y: d for y, d in SESSION_END.items() if session <= int(y) < session + YEARS},
            "lastVote": max((d for r in recs for i in (1, 2) for d in r["keyDates"][i].split(";")), default=""),
            "strings": strings,
            # Stored column by column (all titles, then all summaries, ...), which compresses
            # about a fifth smaller than bill by bill; the page turns it back into rows.
            "cols": [list(c) for c in zip(*rows)] if rows else [],
            "counties": P.COUNTIES,
            # The current governor, for telling whether an earlier veto was theirs.
            "governor": P.GOVERNORS[-1][0],
            # Current Senate and Assembly districts in each county, for "Where you live".
            "districtCounties": json.load(open(P.DISTRICTS_PATH)) if session == current and os.path.exists(P.DISTRICTS_PATH) else {},
            # States that find legislators by town: [[town, county, [[district, share of its people], ...]], ...].
            **({"towns": json.load(open(P.TOWNS_PATH))} if session == current and os.path.exists(getattr(P, "TOWNS_PATH", "")) else {}),
            # Districts with names (Massachusetts): {"S": {"3": "1st Middlesex"}, "H": {...}}, keyed by the seat number.
            **({"districtNames": json.load(open(P.DISTRICT_NAMES_PATH))} if session == current and os.path.exists(getattr(P, "DISTRICT_NAMES_PATH", "")) else {}),
        }
        if session < current:
            # Current legislators, so a past session opened for one of them can show their profile card.
            data["peopleNow"] = people_now()
        if session == current:
            data["contacts"] = contacts_for(session, recs, names)
            data["legislators"] = legislators(session)
            # Legislators' numbers leave out Illinois's shell bills, like the statistics.
            real, real_done = [r for r in recs if not r.get("shell")], without_shells(done, {s: {} for s in done})[0]
            data["profiles"], data["peers"] = profiles(session, real, data["legislators"], party_of)
            data["networkSince"] = network_since(real_done, data["legislators"])
            # Without legislators the site would lose every legislator page and contact; stop
            # so yesterday's site stays up rather than publishing a broken one.
            # (A state without legislators yet, with no contacts file at all, builds without them.)
            if GITHUB and not data["legislators"] and os.path.exists(os.path.join(P.DATA, f"contacts_{session}.json")):
                raise SystemExit("No legislators in the contacts file; not building")
            for seat, rows in person_history(real_done, current, data["legislators"]).items():
                if seat in data["profiles"]:
                    data["profiles"][seat]["history"] = rows
        # What each bill does, in the legislature's own words (states/<code>/texts.py), kept apart from the
        # bill data and loaded when someone opens a bill.
        texts = bill_texts(session, recs)
        data["hasText"] = bool(texts)
        tpayload = json.dumps(texts, separators=(",", ":"), ensure_ascii=False).replace("</", "<\\/") if texts else ""
        payload = json.dumps(data, separators=(",", ":"), ensure_ascii=False).replace("</", "<\\/")
        if GITHUB:
            # On GitHub Pages the data is a separate file the page fetches, so the
            # per-legislator pages can share it.
            os.makedirs(os.path.join(GITHUB, "data"), exist_ok=True)
            # Tab and home-screen icons, at the site's root.
            for name in os.listdir(os.path.join(HERE, "static")):
                with open(os.path.join(HERE, "static", name), "rb") as src, open(os.path.join(GITHUB, name), "wb") as dst:
                    dst.write(src.read())
            # In parts and shards (split_payload()), under names that change with their contents (data/v/), so they can
            # be cached for good; a rebuild replaces the state's whole folder, so old ones don't pile up.
            profile_js = open(os.path.join(os.path.dirname(P.__file__), "profile.js")).read()
            lst, parts_, shards_ = split_payload(data, session >= current,
                                                 {k: re.search(rf"\b{k}\b", profile_js) is not None for k in ("endedNote", "heldAction")})
            dump = lambda part_: json.dumps(part_, separators=(",", ":"), ensure_ascii=False).replace("</", "<\\/")
            texts_ = {"list": dump(lst), **{kind: dump(part_) for kind, part_ in parts_.items()},
                      **{f"s{k}": dump(part_) for k, part_ in enumerate(shards_)}}
            names_ = {kind: hashed_name(session, kind, text) for kind, text in texts_.items()}
            os.makedirs(os.path.join(GITHUB, "data", "v"), exist_ok=True)
            for kind, text in texts_.items():
                with open(os.path.join(GITHUB, "data", "v", names_[kind]), "w", encoding="utf-8") as f:
                    f.write(text)
            # The page's data tag, from a page in the state's folder (prefix "") or one level down ("../"): the list
            # part's address, and the other files' hashes (<session>.<hash>.<kind>.json in data-v: tracker.html's
            # partUrl()); and a preload hint, so the list part starts downloading while the page's script is read.
            hash_of = lambda kind: names_[kind].split(".")[1]
            part_list = " ".join(f"{kind}:{hash_of(kind)}" for kind in parts_)
            shard_list = " ".join(hash_of(f"s{k}") for k in range(len(shards_)))
            bundle = " ".join(lst.get("bundle") or [])
            def data_tag(prefix, base=""):
                return (f'<script type="application/json" id="bill-data" data-src="{prefix}data/v/{names_["list"]}" '
                        f'data-v="{prefix}data/v/" data-session="{session}" data-parts="{part_list}" data-shards="{shard_list}" data-bundle="{bundle}" '
                        f'data-texts="{prefix}data/{session}-text/"'
                        f'{base} data-root="{P.SITE_URL}"></script>')
            def preload(prefix):
                return f'<link rel="preload" href="{prefix}data/v/{names_["list"]}" as="fetch" crossorigin="anonymous">\n'
            if texts:
                # In pieces of 500 bill numbers (data/<session>-text/A10.json holds A5000-A5499), so opening
                # a bill loads only its piece.
                parts = defaultdict(dict)
                for k, v in texts.items():
                    parts[f"{k[0]}{int(re.sub(r'[^0-9]', '', k) or 0) // 500}"][k] = v
                os.makedirs(os.path.join(GITHUB, "data", f"{session}-text"), exist_ok=True)
                for name, part in parts.items():
                    with open(os.path.join(GITHUB, "data", f"{session}-text", f"{name}.json"), "w", encoding="utf-8") as f:
                        json.dump(part, f, separators=(",", ":"), ensure_ascii=False)
            write_issues(session, recs, texts, urls.get(str(session)) or "./", current, {**other_party, **party_of})
            # The session's facts the watchlist's deadline rules read (lists_pages/watchrules.js), for /your-bills/:
            # {c: current, u: upcoming, e: scheduled last days by year, v: the last floor vote, t: past sessions' last votes}.
            # The state's profile (its STATE object) as its own file, data/v/profile.<hash>.js, so /your-bills/ loads only
            # the starred states' rules; its hash is the facts' "s".
            import hashlib
            prof_js = state_profile_js(P)
            prof_hash = hashlib.sha256(prof_js.encode("utf-8")).hexdigest()[:12]
            with open(os.path.join(GITHUB, "data", "v", f"profile.{prof_hash}.js"), "w", encoding="utf-8") as f:
                f.write(prof_js)
            facts = {"s": prof_hash, "c": session >= current, "u": session > current, "e": data.get("sessionEnd") or {},
                     "v": data.get("lastVote") or "", "t": [t["lastVote"] for t in (data.get("insights") or {}).get("timing") or [] if t.get("lastVote")]}

            def later_of(i):
                newer = [e for e in hist[session][i].values() if e[0] > session and e[2] >= 0 and e[1]]
                if not newer:
                    return None
                e = max(newer, key=lambda e: e[0])
                return [e[0], re.sub(r"[A-Z]$", "", e[1].split(" / ")[0])]
            write_status(session, recs, urls.get(str(session)) or "./", session >= current, facts, agenda_of, later_of)
        # The template is written with New York's names (title, header and the script that updates them).
        template = open(TEMPLATE).read().replace("Albany Bill Tracker", P.SITE_NAME).replace("New York State Legislature", P.LEGISLATURE)
        template = template.replace("How a bill becomes law in New York", f"How a bill becomes law in {P.STATE_NAME}")
        # A state's own explanation (states/<code>/how.html) replaces New York's sections of the How tab.
        how = os.path.join(os.path.dirname(P.__file__), "how.html")
        if os.path.exists(how):
            start = template.index('    <div class="howsec" id="howSteps">')
            end = template.index('  </section>', start)
            template = template[:start] + open(how).read() + template[end:]
        # And its own Weigh in text (states/<code>/weighin.html): how to weigh in, the governor's office and
        # who decides at each stage.
        weighin = os.path.join(os.path.dirname(P.__file__), "weighin.html")
        if os.path.exists(weighin):
            start = template.index('    <div class="act-sec">\n      <h2>How to weigh in</h2>')
            end = template.index('  </section>', start)
            template = template[:start] + open(weighin).read() + template[end:]
        # The state's page settings and rules, read by the main script as STATE.
        state_js = state_profile_js(P)
        # The watchlist's deadline rules (lists_pages/watchrules.js, shared with /your-bills/), just before it.
        rules_js = open(os.path.join(HERE, "lists_pages", "watchrules.js")).read()
        # The odds chart (lists_pages/sankey.js, shared with /compare/).
        sankey_js = open(os.path.join(HERE, "lists_pages", "sankey.js")).read()
        template = template.replace('<script id="state-profile"></script>', f'<script id="watch-rules">\n{rules_js}</script>\n<script id="sankey">\n{sankey_js}</script>\n<script id="state-profile">\n{state_js}</script>', 1)
        if session != current:
            template = template.replace(f"<title>{P.SITE_NAME}</title>",
                                        f"<title>{P.SITE_NAME} {P.session_label(session)}</title>", 1)
        # The header line is written in now, matching what the page sets, so it doesn't change length
        # (and push the title down) when the data arrives.
        label = f"{P.LEGISLATURE} · {P.session_label(session)} session" + (
            f" · updated {fetched}" if session == current else f" · prefiled bills · updated {fetched}" if session > current else " (final)")
        template = template.replace(f'id="sessionLabel">{P.LEGISLATURE}<', f'id="sessionLabel">{html_escape(label)}<', 1)
        # Party control now (balance.py), on the current session's page only: written in, so nothing moves on load.
        if session == current:
            import balance
            lower = getattr(P, "LOWER_NAME", "Assembly")
            power = balance.summary_html(STATE, lower)
            if power:
                template = template.replace('<p class="power" id="power"></p>',
                                            f'<p class="power" id="power">{power}<span class="bp-why">{html_escape(balance.meaning(STATE, lower))}</span></p>', 1)
        # The frame shown while the data loads: the tabs this page will have, and how many bills are coming.
        template = frame_tabs(template, "past" if session < current else "upcoming" if session > current else "")
        template = template.replace('id="frameLoad">Loading bills…<', f'id="frameLoad">Loading {len(recs):,} bills…<', 1)
        # And the session buttons beside the title (renderSessions() draws the same), so the title's block is already
        # as tall as it will be. (A legislator's page moves them into their card: not there.)
        latest = max(s for s in SESSIONS if s <= current)

        def sessions_nav(base):
            out = []
            for s in SESSIONS:
                label = html_escape(f"{P.session_label(s)}{' (current)' if s == latest else ' (prefiled)' if s > latest else ''}")
                url = urls.get(str(s))
                if s == session:
                    out.append(f'<span class="here" aria-current="page">{label}</span>')
                elif not url:
                    out.append(f'<span class="off">{label}</span>')
                elif re.match(r"https?:", url):
                    out.append(f'<a href="{html_escape(url)}" target="_blank" rel="noopener">{label}</a>')
                else:
                    out.append(f'<a href="{html_escape(base + url)}">{label}</a>')
            return "".join(out)
        nav_marker = '<nav class="sessions" id="sessions" aria-label="Legislative sessions"></nav>'
        with_nav = lambda page, base="": page.replace(nav_marker, nav_marker.replace("></nav>", f">{sessions_nav(base)}</nav>"), 1)
        person_template = template
        template = with_nav(template)
        marker = '<script type="application/json" id="bill-data"></script>'
        assert marker in template, "template is missing the data marker"
        # The Claude copies carry the data gzipped and base64-encoded (about a third the size), unpacked in the
        # browser; GitHub Pages pages load the shared JSON file instead, which the server compresses anyway.
        packed = base64.b64encode(gzip.compress(payload.encode("utf-8"), 9, mtime=0)).decode("ascii")
        html = template.replace(marker, f'<script type="application/octet-stream" id="bill-data" data-enc="gzip64">{packed}</script>')
        if tpayload:
            tpacked = base64.b64encode(gzip.compress(tpayload.encode("utf-8"), 9, mtime=0)).decode("ascii")
            html = html.replace(f'data-enc="gzip64">{packed}</script>',
                                f'data-enc="gzip64">{packed}</script>\n<script type="application/octet-stream" id="bill-text" data-enc="gzip64">{tpacked}</script>', 1)
        if GITHUB:
            out = os.path.join(GITHUB, "index.html" if session == current else f"{session}.html")
            if session == current:
                meta = page_meta(f"{state_words()} · State Bill Tracker",
                                 f"Follow bills in the {P.LEGISLATURE}: where each one is, who decides next, and what to ask them.")
            else:
                meta = page_meta(f"{state_words()}, {P.session_label(session)} · State Bill Tracker",
                                 (f"Bills prefiled so far for the {P.LEGISLATURE}'s {P.session_label(session)} session." if session > current
                                  else f"Every bill in the {P.LEGISLATURE}'s {P.session_label(session)} session, and where it ended up."),
                                 f"{session}.html")
            html = github_page(template.replace(marker, data_tag("")), preload("") + meta)
            if session == current:
                for leg in data.get("legislators", []):
                    page = frame_tabs(person_template, "person").replace(marker, data_tag("../", ' data-base="../"'))
                    preset = json.dumps({"who": leg["id"]}).replace('"', "&quot;")
                    page = page.replace(f"<title>{P.SITE_NAME}</title>",
                                        f'<title>{leg["title"]} {leg["name"]} · {P.SITE_NAME}</title>\n<meta name="abt-preset" content="{preset}">', 1)
                    os.makedirs(os.path.join(GITHUB, leg["slug"]), exist_ok=True)
                    with open(os.path.join(GITHUB, leg["slug"], "index.html"), "w") as f:
                        f.write(github_page(page, preload("../") + page_meta(f'{leg["title"]} {leg["name"]} · {state_words()} · State Bill Tracker',
                                                            f'{leg["title"]} {leg["name"]} in the {P.LEGISLATURE}: bills, committees and how to get in touch.',
                                                            f'{leg["slug"]}/')))
                # /watchlist/: the same page, opened to the visitor's own watchlist.
                page = frame_tabs(with_nav(person_template, "../"), "watch").replace(marker, data_tag("../", ' data-base="../"'))
                page = page.replace(f"<title>{P.SITE_NAME}</title>",
                                    f'<title>Watchlist · {P.SITE_NAME}</title>\n<meta name="abt-preset" content="{{&quot;watch&quot;: true}}">', 1)
                os.makedirs(os.path.join(GITHUB, "watchlist"), exist_ok=True)
                with open(os.path.join(GITHUB, "watchlist", "index.html"), "w") as f:
                    f.write(github_page(page, preload("../") + page_meta(f"Watchlist · {state_words()} · State Bill Tracker",
                                                        f"Your own list of {P.LEGISLATURE} bills to follow.", "watchlist/")))
                # A shared last name gets a page for picking the right person, e.g. /ramos/.
                by_last = defaultdict(list)
                for leg in data.get("legislators", []):
                    by_last[name_key(leg["name"]).split()[-1]].append(leg)
                for last, legs in by_last.items():
                    if len(legs) > 1:
                        os.makedirs(os.path.join(GITHUB, last), exist_ok=True)
                        with open(os.path.join(GITHUB, last, "index.html"), "w") as f:
                            f.write(choose_page(legs))
                print(f"   {len(data.get('legislators', []))} legislator pages")
        else:
            out = os.path.join(SITE, f"{session}.html")
            # A Claude artifact page can't be larger than 16 MB.
            size = len(html.encode("utf-8"))
            if size > 16_000_000:
                raise SystemExit(f"{out} is {size / 1e6:.1f} MB, over the 16 MB page limit")
            if size > 15_300_000:
                print(f"   warning: {out} is {size / 1e6:.1f} MB, close to the 16 MB page limit")
        os.makedirs(os.path.dirname(out), exist_ok=True)
        with open(out, "w") as f:
            f.write(html)
        stages = Counter(r["stage"] for r in recs)
        reintro = sum(1 for i in range(len(recs)) if any(k[0] < session for k in hist[session][i]))
        print(f"{session}: {len(recs)} bills, {reintro} with earlier versions, "
              f"{sum(1 for r in recs if not r['topics'])} untagged, {os.path.getsize(out) / 1e6:.1f} MB -> {out}")
        print("   stages:", {STAGE_LABEL[k]: stages[k] for k in sorted(stages)}, "delegation:", names)


if __name__ == "__main__":
    main()
