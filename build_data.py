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
SESSIONS = C.sessions()
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
    """Visit counters for the public site; none for local test builds."""
    if not P.SITE_URL.startswith(P.PUBLIC_URL.rstrip("/")):
        return ""
    tags = ""
    if P.CF_ANALYTICS_TOKEN:
        tags += ('<script defer src="https://static.cloudflareinsights.com/beacon.min.js" '
                 f'data-cf-beacon=\'{{"token": "{P.CF_ANALYTICS_TOKEN}"}}\'></script>\n')
    if P.GOATCOUNTER_CODE:
        tags += (f'<script data-goatcounter="https://{P.GOATCOUNTER_CODE}.goatcounter.com/count" '
                 'async src="https://gc.zgo.at/count.js"></script>\n')
    return tags


def github_page(html):
    """Claude artifacts get a document skeleton added when published; GitHub Pages doesn't."""
    split = html.index('<div class="wrap">')
    return ('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
            '<meta name="robots" content="noindex, nofollow">\n'
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
            by_last[words[-1]].append((words[0], int(seat[2:])))
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
        return (not h["start"] or h["start"] <= str(session + 1)) and (not h["end"] or h["end"] >= str(session))

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
        house, district = seat.split(":")
        slug = last(p) if counts[last(p)] == 1 else p["key"].replace(" ", "-")
        out.append({"id": seat, "slug": slug, "name": p["name"], "title": "Sen." if house == "S" else "Asm.",
                    "house": house, "district": int(district), "email": p.get("email"), "phone": p.get("phone"), "phones": p.get("phones"),
                    "url": p.get("url"), "party": p.get("party"), "image": p.get("image"),
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
        p = seats.get(f"{house}:{district}") if district else None
        if p and p["key"].split()[-1] != key.split()[-1]:
            p = None  # someone else holds that seat now
        if not p:
            hits = [v for k, v in seats.items() if k[0] == house and v["key"] == key]
            if not hits:
                hits = [v for k, v in seats.items() if k[0] == house and v["key"].split()[-1] == key.split()[-1]]
            p = hits[0] if len(hits) == 1 else None
        if p:
            return {"url": p["url"], "email": p["email"], "phone": p["phone"], "phones": p.get("phones")}
        if house == "S":
            return {"url": senate_url(name)}
        m = asm_members.get(key) or {}
        return {"url": m.get("url"), "email": m.get("email")}

    def person(name, house, district=None):
        if name and name not in people:
            people[name] = lookup(name, house, district)
        return name

    ours = {"S": set(delegation_names.get("SENATE", [])), "A": set(delegation_names.get("ASSEMBLY", []))}

    def ours_on(members, house):
        return sorted({n for n in ours[house] for m in members if name_key(m).endswith(" " + n.lower())})

    def serving(name, house):
        return bool(name) and (not seats or any(k[0] == house and v["key"].split()[-1] == name_key(name).split()[-1] for k, v in seats.items()))

    committees = {}
    for house, key in (("S", "senateCommittees"), ("A", "assemblyCommittees")):
        for k, c in raw.get(key, {}).items():
            committees[f"{house}:{k}"] = {
                "name": c["name"],
                # A chair carried over from last session's committees counts only while still serving.
                "chair": person(c.get("chair"), house) if serving(c.get("chair"), house) else None,
                "meets": c.get("meets"),
                "url": c.get("url"),
                "ours": ours_on(c.get("members", []), house),
            }
    for r in recs:
        for v in r["vers"]:
            person(v["sponsor"], v["p"][0], v.get("district"))
    reps = []
    for house, title in (("S", "Sen."), ("A", "Asm.")):
        for district in sorted(P.delegation(session).get("SENATE" if house == "S" else "ASSEMBLY", ())):
            seat = seats.get(f"{house}:{district}")
            if seat and seat["key"].split()[-1] in {n.lower() for n in ours[house]}:
                name = next((n for n in people if name_key(n) == seat["key"]), seat["name"])
                people.setdefault(name, lookup(name, house, district))
                reps.append({"title": title, "name": name, "house": house, "last": seat["key"].split()[-1]})
    leaders = {}
    for house, (name, role) in P.LEADERS.items():
        if any(k[0] == house and v["key"] == name_key(name) for k, v in seats.items()):
            person(name, house)
            leaders[house] = {"name": name, "role": role}
    return {"fetched": raw.get("fetched"), "committees": committees, "people": people, "reps": reps, "leaders": leaders}


def choose_page(legs):
    """A small page for a shared last name: pick which legislator you meant."""
    last = legs[0]["name"].split()[-1]
    items = "\n".join(
        f'<li><a href="../{l["slug"]}/">{l["title"]} {html_escape(l["name"])}</a> '
        f'<span>{"Senate" if l["house"] == "S" else "Assembly"} District {l["district"]}</span></li>' for l in legs)
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow"><link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'><rect width='64' height='64' rx='14' fill='%231d3b78'/><path d='M32 10 52 23H12z' fill='%23fff'/><rect x='14' y='25' width='36' height='4' fill='%23fff'/><rect x='17' y='31' width='6' height='16' fill='%23fff'/><rect x='29' y='31' width='6' height='16' fill='%23fff'/><rect x='41' y='31' width='6' height='16' fill='%23fff'/><rect x='11' y='49' width='42' height='5' fill='%23e3b04b'/></svg>"><title>Which {html_escape(last)}? · {P.SITE_NAME}</title>
<style>
:root {{ --bg: #f6f8fb; --fg: #14213d; --muted: #4a5878; --link: #1d3b78; color-scheme: light; }}
@media (prefers-color-scheme: dark) {{ :root {{ --bg: #0f1626; --fg: #e6ebf5; --muted: #a3b0c9; --link: #8fb0f0; color-scheme: dark; }} }}
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


def insights(loaded, hist, current):
    past = [s for s in sorted(loaded) if s != current]
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
        # Only committees that exist this session; defunct ones would only confuse.
        return {t: {k: v for k, v in d.items() if k in current_comms and (not minimum or v[0] >= (40 if t == "all" else 15))} for t, d in out.items()}

    # What usually happens next: of bills that reached each point, how many became law.
    odds = {t: defaultdict(lambda: [0, 0]) for t in topics}
    for s in past:
        for r in loaded[s][0]:
            got = reached(r)
            points = {"intro": True, "floor": got["floor"], "passS": got["passS"], "passA": got["passA"], "both": got["both"],
                      "house": got["passS"] or got["passA"], "vetoed": r["stage"] == 6}
            for t in topics:
                if has(r, t):
                    for p, ok in points.items():
                        if ok:
                            odds[t][p][0] += 1
                            odds[t][p][1] += got["law"]

    # Timing: how much floor action comes at the very end of each year's session.
    timing = []
    for s in past:
        for year in (s, s + 1):
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
            last = max(d for d, n in per_day.items() if n >= 20)
            from datetime import date, timedelta
            cut = (date.fromisoformat(last) - timedelta(days=21)).isoformat()
            timing.append({"year": year, "votes": len(regular), "lastVote": last,
                           "final3wk": sum(cut < d <= last for d in regular)})
    signed = [r["keyDates"][5] for s in past for r in loaded[s][0] if r["keyDates"][5]]
    # The governor's decisions: by month (past sessions) and by calendar year (all sessions).
    gov_months = defaultdict(lambda: [0, 0])
    gov_years = defaultdict(lambda: [0, 0])
    for s in sorted(loaded):
        for r in loaded[s][0]:
            for i, kind in ((5, 0), (6, 1)):
                d = r["keyDates"][i]
                if not d:
                    continue
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
        nxt = s + 2
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
    for s in past:
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
                    c[1] += any(e[0] == s + 2 for e in later)
                    c[2] += any(e[2] == 5 for e in later)

    # What happened to bills that died, by how far they got: [died, back next session, later law].
    fate = {t: {k: [0, 0, 0] for k in ("committee", "floor", "oneHouse", "vetoed")} for t in topics}
    for s in past[:-1]:
        nxt = s + 2
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
        out = {t: {k: [0] * 24 for k in ("intro", "comm", "passS", "passA", "signed", "vetoed")} for t in topics}
        for s in sessions:
            for r in loaded[s][0]:
                k = r["keyDates"]
                when = {"intro": r["first"] or "", "comm": k[0], "passS": k[1].split(";")[0], "passA": k[2].split(";")[0],
                        "signed": k[5] if r["stage"] == 5 else "", "vetoed": k[6] if r["stage"] == 6 else ""}
                for key, d in when.items():
                    if len(d) < 7 or d[:4] > str(s + 1):
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
        "committees": {"current": committee_table([current], minimum=False), "past": committee_table(past)},
        "odds": {t: dict(v) for t, v in odds.items()},
        "timing": timing,
        "lateSigning": [late_sign, len(signed)],
        "govMonths": dict(sorted(gov_months.items())),
        "govYears": [[k.split("|")[0], k.split("|")[1], v[0], v[1]] for k, v in sorted(gov_years.items())],
        "persistence": persist,
        "comeback": comeback,
        "stuck": stuck,
    }


def profiles(session, recs, legs, party_of):
    """Each sitting legislator's numbers this session, and the median for their party in their house."""
    if not legs:
        return {}, {}
    resolve = assembly_resolver(session)
    by_seat = {L["id"]: L for L in legs}
    last_of = {L["id"]: name_key(L["name"]).split()[-1] for L in legs}
    stats = {L["id"]: {"sponsored": 0, "floor": 0, "passedHouse": 0, "both": 0, "laws": 0, "lawsLocal": 0,
                       "otherParty": 0, "floorVotes": 0, "missed": 0, "comms": {}} for L in legs}
    first_bill, votes_seen = {}, []
    for r in recs:
        got = reached(r)
        local = narrow_bill(r) or bool(CEREMONIAL.search(r["title"] or ""))
        for v in r["vers"]:
            house = v["p"][0]
            seat = f"{house}:{v.get('district')}"
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
            seat = f"{v['p'][0]}:{v.get('district')}"
            if seat in stats and v["actions"] and name_key(v["sponsor"] or "").split()[-1:] == [last_of[seat]]:
                first_bill[seat] = min(first_bill.get(seat, "9999"), v["actions"][0][0])
        for h, kind, comm, date, y, n, ny in r["votes"]:
            if kind != "F":
                continue
            absent = set()
            for (mh, who), code in ny:
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
        carriers = {"S": set(), "A": set()}
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
            for z in carriers["A"]:
                cross[(a, z)] += 1
    return spons, w, cross


def net_views(spons, w, cross, info, minimum=3):
    """The network for the Senate, the Assembly and both houses, as the page draws it:
    {view: {"nodes": [[id, label, party, bills]], "links": [[a, b, share, kind]]}}. Each member
    keeps their strongest few ties; the same rules as the live chart on the current page."""
    out = {}
    for sel in ("S", "A", "B"):
        houses = ("S", "A") if sel == "B" else (sel,)
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
    info = {f"{h}:{n}": [f"{'Sen.' if h == 'S' else 'Asm.'} {n}", p] for (h, n), p in party_of.items()}
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
        tf = Counter(_sim_words(r["title"]) * 2 + _sim_words(r["summary"][:800]))
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
    skip = [narrow_bill(r) for r in recs]
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
        for t in ["all"] + r["topics"]:
            c = out[t]
            c[0] += 1
            c[1] += r["stage"] >= 3
            c[2] += r["stage"] == 5
            c[3] += r["stage"] == 6
            c[4] += r["stage"] == 2
    return dict(out)


def main():
    loaded = {s: C.load_session(s) for s in SESSIONS}
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

    # Current legislators for past sessions' pages (profile card and the sessions they served in).
    legs_now = legislators(current)
    served_by = {seat: sorted({row[0] for row in rows}) for seat, rows in person_history(done, current, legs_now).items()}
    keep = ("id", "slug", "name", "title", "party", "house", "district", "since", "image", "url", "email", "phone", "phones")
    _PEOPLE_NOW.update({L["slug"]: {**{k: L.get(k) for k in keep}, "served": served_by.get(L["id"], [])} for L in legs_now if L.get("slug")})

    for session in ONLY:
        recs, _, fetched, names = loaded[session]
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
        rows = []
        sims = similar_bills(recs)
        for i, r in enumerate(recs):
            flags = (r["local"] and 1) | (r["senDeleg"] and 2) | (r["budget"] and 4) | (r["asmDeleg"] and 8) | (r["passedS"] and 16) | (r["passedA"] and 32) | (P.NARROW_KINDS.index(r["narrow"]) << 6)
            vers = [[v["p"], S(v["sponsor"]), v["cosp"], S(v["statusDesc"]), S(v["committee"]),
                     [[a[0].replace("-", ""), S(a[1])] for a in v["actions"]],
                     [S(n) for n in v["cosponsors"]] if session >= current else [], v.get("district") or 0] for v in r["vers"]]
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
                         [(P.COUNTIES + ["?"]).index(c) for c in r["places"]], r["mainTopic"], sims[i], r["memo"]])

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
            "insights": insight,
            # Past pages don't carry co-sponsor names, so their network is worked out here.
            "network": session_network(session, recs) if session < current else None,
            # Date of the last floor vote in either house this session.
            "sessionEnd": {y: d for y, d in SESSION_END.items() if int(y) in (session, session + 1)},
            "lastVote": max((d for r in recs for i in (1, 2) for d in r["keyDates"][i].split(";")), default=""),
            "strings": strings,
            # Stored column by column (all titles, then all summaries, ...), which compresses
            # about a fifth smaller than bill by bill; the page turns it back into rows.
            "cols": [list(c) for c in zip(*rows)] if rows else [],
            "counties": P.COUNTIES,
            # Current Senate and Assembly districts in each county, for "Where you live".
            "districtCounties": json.load(open(P.DISTRICTS_PATH)) if session == current and os.path.exists(P.DISTRICTS_PATH) else {},
        }
        if session < current:
            # Current legislators, so a past session opened for one of them can show their profile card.
            data["peopleNow"] = people_now()
        if session == current:
            data["contacts"] = contacts_for(session, recs, names)
            data["legislators"] = legislators(session)
            data["profiles"], data["peers"] = profiles(session, recs, data["legislators"], party_of)
            data["networkSince"] = network_since(done, data["legislators"])
            # Without legislators the site would lose every legislator page and contact; stop
            # so yesterday's site stays up rather than publishing a broken one.
            if GITHUB and not data["legislators"]:
                raise SystemExit("No legislators in the contacts file; not building")
            for seat, rows in person_history(done, current, data["legislators"]).items():
                if seat in data["profiles"]:
                    data["profiles"][seat]["history"] = rows
        payload = json.dumps(data, separators=(",", ":"), ensure_ascii=False).replace("</", "<\\/")
        if GITHUB:
            # On GitHub Pages the data is a separate file the page fetches, so the
            # per-legislator pages can share it.
            os.makedirs(os.path.join(GITHUB, "data"), exist_ok=True)
            # Tab and home-screen icons, at the site's root.
            for name in os.listdir(os.path.join(HERE, "static")):
                with open(os.path.join(HERE, "static", name), "rb") as src, open(os.path.join(GITHUB, name), "wb") as dst:
                    dst.write(src.read())
            with open(os.path.join(GITHUB, "data", f"{session}.json"), "w", encoding="utf-8") as f:
                f.write(payload)
        # The template is written with New York's names (title, header and the script that updates them).
        template = open(TEMPLATE).read().replace("Albany Bill Tracker", P.SITE_NAME).replace("New York State Legislature", P.LEGISLATURE)
        template = template.replace("How a bill becomes law in New York", f"How a bill becomes law in {P.STATE_NAME}")
        # A state's own explanation (states/<code>/how.html) replaces New York's sections of the How tab.
        how = os.path.join(os.path.dirname(P.__file__), "how.html")
        if os.path.exists(how):
            start = template.index('    <div class="howsec" id="howSteps">')
            end = template.index('  </section>', start)
            template = template[:start] + open(how).read() + template[end:]
        # The state's page settings and rules, read by the main script as STATE.
        state_js = open(os.path.join(os.path.dirname(P.__file__), "profile.js")).read()
        template = template.replace('<script id="state-profile"></script>', f'<script id="state-profile">\n{state_js}</script>', 1)
        if session != current:
            template = template.replace(f"<title>{P.SITE_NAME}</title>",
                                        f"<title>{P.SITE_NAME} {P.session_label(session)}</title>", 1)
        # The header line is written in now, matching what the page sets, so it doesn't change length
        # (and push the title down) when the data arrives.
        label = f"{P.LEGISLATURE} · {P.session_label(session)} session" + (
            f" · updated {fetched}" if session == current else f" · prefiled bills · updated {fetched}" if session > current else " (final)")
        template = template.replace(f'id="sessionLabel">{P.LEGISLATURE}<', f'id="sessionLabel">{html_escape(label)}<', 1)
        marker = '<script type="application/json" id="bill-data"></script>'
        assert marker in template, "template is missing the data marker"
        # The Claude copies carry the data gzipped and base64-encoded (about a third the size), unpacked in the
        # browser; GitHub Pages pages load the shared JSON file instead, which the server compresses anyway.
        packed = base64.b64encode(gzip.compress(payload.encode("utf-8"), 9, mtime=0)).decode("ascii")
        html = template.replace(marker, f'<script type="application/octet-stream" id="bill-data" data-enc="gzip64">{packed}</script>')
        if GITHUB:
            out = os.path.join(GITHUB, "index.html" if session == current else f"{session}.html")
            html = github_page(template.replace(marker, f'<script type="application/json" id="bill-data" data-src="data/{session}.json" data-root="{P.SITE_URL}"></script>'))
            if session == current:
                for leg in data.get("legislators", []):
                    page = template.replace(marker, f'<script type="application/json" id="bill-data" data-src="../data/{session}.json" data-base="../" data-root="{P.SITE_URL}"></script>')
                    preset = json.dumps({"who": leg["id"]}).replace('"', "&quot;")
                    page = page.replace(f"<title>{P.SITE_NAME}</title>",
                                        f'<title>{leg["title"]} {leg["name"]} · {P.SITE_NAME}</title>\n<meta name="abt-preset" content="{preset}">', 1)
                    os.makedirs(os.path.join(GITHUB, leg["slug"]), exist_ok=True)
                    with open(os.path.join(GITHUB, leg["slug"], "index.html"), "w") as f:
                        f.write(github_page(page))
                # /watchlist/: the same page, opened to the visitor's own watchlist.
                page = template.replace(marker, f'<script type="application/json" id="bill-data" data-src="../data/{session}.json" data-base="../" data-root="{P.SITE_URL}"></script>')
                page = page.replace(f"<title>{P.SITE_NAME}</title>",
                                    f'<title>Watchlist · {P.SITE_NAME}</title>\n<meta name="abt-preset" content="{{&quot;watch&quot;: true}}">', 1)
                os.makedirs(os.path.join(GITHUB, "watchlist"), exist_ok=True)
                with open(os.path.join(GITHUB, "watchlist", "index.html"), "w") as f:
                    f.write(github_page(page))
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
