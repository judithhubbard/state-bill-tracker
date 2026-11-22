#!/usr/bin/env python3
"""Download Kansas's bills from the Legislature's REST API (https://kslegislature.gov/api/docs/, JSON, under /api/v1/),
and the Kansas Legislative Research Department's supplemental notes from the Legislature's document viewer. The API
works without a key, at up to 30 requests a minute per address (300 with a free key: KANSAS_API_KEY or
~/.kansas_api_key, sent as "Authorization: Api-Key ..."; never printed). Without a key, one request every 2.1 seconds;
with one, a second apart. kslegislature.gov has no robots.txt (it answers 404, checked 2026-11-13), so nothing is
barred. The older KLISS API (/li/api/v13/rev-1/bill_status/) still answers, but says it's deprecated (a "sunset" of
2026-08-01) and names /api/v1/ as its successor, so it isn't used. A 401, 403 or 429, or a Cloudflare challenge page,
stops the run.

Kansas's Legislature meets in two-year bienniums ("b2025_26"), a session each year from the second Monday of January
(to about mid-May, veto session included). Bills carry over from the first year to the second. Every resource is
scoped to one biennium (?biennium=b2023_24); /api/v1/biennia/ lists the active one and the archived ones the site
serves (in November 2026: b2025_26 and b2023_24). The active biennium and the newest archived one go into
data/ks/<first year>/ (2025/, 2023/):
- bill_status.json: {"read", "biennium", "bills": [...]}, every bill and resolution as /api/v1/bill_status/ serves it
  (200 a page): HB, SB, HCR, SCR, HR, SR. Each has BILLNO, SHORTTITLE (the plain one-line description), LONGTITLE ("AN
  ACT concerning ..."; concurrent resolutions proposing constitutional amendments say "A PROPOSITION to amend ... the
  constitution of the state of Kansas" and their SHORTTITLE "Proposing a constitutional amendment ..."; the other HCRs
  and SCRs are requests and memorials, and HR/SR one house's resolutions: telling them apart is the converter's job),
  EFFECTIVEDATE, STATUS and measure_state ("enacted", "dead", "introduced"), ORIGINAL_SPONSOR and SPONSOR_NAMES ("Senator
  Alley", "Committee on Taxation"), versions (each with its document and, in associated_documents, the fiscal note and
  supplemental note) and HISTORY: one entry per journal action with action_code ("ref_rbc_310" referred; "cr_rsc_282"
  committee report "be passed as amended"; "fa_fabc_340"/"efa_fabc_343" final action passed; "ccac_om_832" conference
  report adopted; "gov_mg_150" approved by the governor; "gov_mg_151" law without signature; "gov_mg_154" vetoed;
  "gov_mg_378" approved with line-item vetoes; "gov_avm_885"/"gov_avm_887" veto/line-item veto overridden;
  "dead_com_301" died in committee: the full table is in the API documentation), chamber, the committee named
  (committee_names; referrals name their committee), conferee_names, floor tallies in the wording ("Final Action -
  Passed as amended;  Yea: 105 Nay: 17"), session_date and journal page.
- governor_actions.json: /api/v1/governor-actions/: each bill the governor acted on, by outcome ("signed", "vetoed",
  "veto-overridden", "line-item-veto", "partial-override", "awaiting-governor"), for checking totals.
- votes.json: {apn: record}, every roll call in /api/v1/votes/ (bill_no, chamber, rcs_num, session_day, tally, the
  journal action it belongs to: action_code, action_label, occurred, page_number; rev_date); and votes/<key>.json, one
  per roll call on an HB, SB, HCR or SCR, from the detail endpoint (/api/v1/votes/<apn>/): the same plus members
  {"yea": [{kpid, name}], "nay": [...], "present", "absent", "not_voting"}. kpids ("rep_carpenter_will_1") are the
  legislators' ids. Floor votes only: committees don't take roll calls.
- supp_notes.json: /api/v1/supplemental-notes/ (each note's bill, version "00"/"01"/"02", keywords, PDF link, pdf_only),
  and notes/<HB2001>.json: the text of each bill's latest supplemental note (the Research Department's plain summary of
  the bill as it stood: "Brief*", then its background), read from the document viewer's HTML
  (/b2025_26/documents/view-leg/?apn=..., the same page the bill's page links to), {apn, version, rev_date, text}
  with paragraphs separated by blank lines. Notes marked pdf_only aren't read.
- legislators.json (every member listed for the biennium, with status "Active" or "Inactive": kpid, chamber, names,
  party, district, seat, email, county, occupation), leadership.json (Speaker, President, leaders, by member kpid),
  committees.json (standing, joint, special and other committees: kpid, title, display_name "Committee on Health and
  Human Services" as the history writes it, chamber, type, status, meeting time and room, members, chair and vice_chair
  by kpid).
And data/ks/members/<kpid>.json: the active biennium's active members' details (/api/v1/legislators/<kpid>/: office
phone and room, email, home phone, first term, party position, committees, chaired and vice-chaired committees,
leadership roles), read when missing and weekly.
- state.json (per biennium): when each list was last read ("read") and notes that answered 404 ("absent": apn).

What changes: the active biennium's lists (bill status, votes, supplemental notes, governor actions, legislators,
leadership, committees) are read every run, about 30 requests (a minute); the archived biennium's weekly. A roll call's
detail is read when it's new or its rev_date changed; a supplemental note's text when the bill's latest note changes.
Those extras fill in over later runs and never hold the state back: a first copy (about 2,700 roll calls and 1,200
notes for two bienniums) takes about 2½ hours without a key, so GitHub's runs build it over several.

- agendas.json (the active biennium): bills on committee hearings from yesterday to three weeks ahead, from
  /api/v1/hearings/ (see agendas()), every run.

- fnotes/<HB2001>.json: the Division of the Budget's fiscal note on the bill's latest version that has one, for bills with
  no supplemental note (2026-11-22: the note's letter describes the bill before its cost; "What it does" falls back to
  it), from the same viewer (/<biennium>/documents/view-leg/?apn=<biennium>/ds_docs_li/fisc_note_hb2001_00_0000/...),
  once a version, after the roll calls (`fiscal_notes()`).
Not read: bill texts (PDFs; /api/v1/measures/<bill>/text/ has them as lines), testimony, past
hearings, committee minutes, and the website's pages, whose emails are hidden behind Cloudflare's script
(the API and the members' CSV export give them openly).

data/ks/incomplete says "running" during the first copy, then lists what was never downloaded (a biennium's bill status,
the active biennium's legislators, committees or an active member's details); it is removed when nothing is missing. A
list that fails where a last copy exists keeps that copy and doesn't count; a biennium that hasn't begun (no bills yet)
doesn't count either.
Usage: python3 states/ks/fetch.py [biennium first year]   (default: the active and the archived ones in the shared
window, states/window.py; one leaves the marker)
"""
import gzip, html, json, os, re, sys, time, urllib.error, urllib.parse, urllib.request
from collections import Counter
from datetime import date, timedelta
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
from states import window as W

SITE = "https://kslegislature.gov"
API = SITE + "/api/v1"
DATA = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "ks"))
AGENT = "statebilltracker.org (a nonprofit bill tracker; contact via github.com/judithhubbard)"
TODAY = date.today()
ONLY = int(sys.argv[1]) if len(sys.argv) > 1 else None
PAGE = 200  # the API's largest page
WEEKLY = 7
WANTED = re.compile(r"^(HB|SB|HCR|SCR)\d+$")  # roll calls and notes are read for these
MEMBERS = os.path.join(DATA, "members")
MARKER = os.path.join(DATA, "incomplete")


def api_key():
    key = os.environ.get("KANSAS_API_KEY", "").strip()
    if not key:
        try:
            with open(os.path.expanduser("~/.kansas_api_key")) as f:
                key = f.read().strip()
        except OSError:
            pass
    return key


KEY = api_key()
DELAY = 1.0 if KEY else 2.1  # seconds between the starts of two requests (30 a minute without a key)

# The run's own time limit (FETCH_MINUTES, set by the workflow): stop a few minutes early, with everything read so far
# saved and a summary printed, rather than be cut off silently mid-request.
START = time.time()
BUDGET = max(0.0, float(os.environ.get("FETCH_MINUTES") or 0) - 5) * 60
FAILS = Counter()  # why requests failed, for the summary
STATS = Counter()  # requests, votes, notes read
LAST = [0.0]  # when the last request started
CODE = [0]  # the last request's HTTP status (404: not there)


class Refused(Exception):
    """The server turned us away (401/403/429 or a Cloudflare challenge): stop the run."""


def out_of_time():
    return BUDGET and time.time() - START > BUDGET


def request(url, label, kind="json"):
    """The answer (parsed JSON, or text for kind "text"), or None after three tries; None at once for a 404 (CODE[0]
    is then 404)."""
    CODE[0] = 0
    for attempt in range(3):
        if out_of_time():
            return None
        wait = LAST[0] + DELAY - time.time()
        if wait > 0:
            time.sleep(wait)
        LAST[0] = time.time()
        STATS["requests"] += 1
        if STATS["requests"] % 100 == 0:
            print(f"  {STATS['requests']} requests, {round((time.time() - START) / 60)} min"
                  + (f"; failures {dict(FAILS)}" if FAILS else ""), flush=True)
        headers = {"User-Agent": AGENT, "Accept-Encoding": "gzip"}
        if KEY and url.startswith(API):
            headers["Authorization"] = "Api-Key " + KEY
        if kind == "json":
            headers["Accept"] = "application/json"
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=90) as r:
                body = r.read()
                if r.headers.get("Content-Encoding") == "gzip":
                    body = gzip.decompress(body)
                if r.headers.get("cf-mitigated") == "challenge":
                    raise Refused(f"{label}: Cloudflare challenge")
            if kind == "bytes":
                return body
            text = body.decode("utf-8", "replace")
            if kind != "json":
                if "challenge-platform" in text and "Just a moment" in text:
                    raise Refused(f"{label}: Cloudflare challenge")
                return text
            try:
                return json.loads(text)
            except ValueError:
                if "Just a moment" in text:
                    raise Refused(f"{label}: Cloudflare challenge")
                FAILS["not JSON"] += 1
        except urllib.error.HTTPError as e:
            FAILS[f"HTTP {e.code}"] += 1
            if e.code in (401, 403, 429) or e.headers.get("cf-mitigated") == "challenge":
                raise Refused(f"{label}: HTTP {e.code}")
            if e.code == 404:
                CODE[0] = 404
                return None
        except Refused:
            raise
        except Exception as e:
            FAILS[type(e).__name__] += 1
        time.sleep(5 * (attempt + 1))
    print(f"{label}: failed three times", flush=True)
    return None


def listing(path, label, biennium, **params):
    """Every row of a paged list endpoint, or None if a page couldn't be read."""
    q = {"biennium": biennium, "limit": PAGE, **params}
    url = f"{API}/{path}/?{urllib.parse.urlencode(q)}"
    rows, offset = [], 0
    while url:
        page = request(url, f"{label} {offset}")
        if not isinstance(page, dict) or not isinstance(page.get("results"), list):
            return None
        rows += page["results"]
        offset += PAGE
        if page.get("next"):
            url = page["next"]
        elif page.get("next_offset") is not None:  # governor-actions pages by offset
            url = f"{API}/{path}/?{urllib.parse.urlencode({**q, 'offset': page['next_offset']})}"
        else:
            url = None
        if len(rows) > 50000:
            return None  # a loop
    return rows


def save(obj, path):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=0)
    os.replace(tmp, path)


def load(path, default=None):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def first_year(biennium):
    return int(biennium[1:5])


def vote_file(apn):
    """A roll call's file name: "b2025_26/year2/house/legislative_days/day054_20260410/vote_records/0437_SB430.odt" ->
    "year2_house_day054_0437_SB430"."""
    parts = apn.split("/")
    day = re.match(r"day\d+", parts[4]).group() if len(parts) > 4 and re.match(r"day\d+", parts[4]) else "day"
    return re.sub(r"[^A-Za-z0-9_]+", "_", f"{parts[1]}_{parts[2]}_{day}_{os.path.splitext(parts[-1])[0]}")


def due(state, name, live):
    """Whether a list is read this run: every run for the active biennium, weekly for an archived one."""
    last = state.get("read", {}).get(name, "")
    return live or not last or last < (TODAY - timedelta(days=WEEKLY)).isoformat()


def read_list(folder, state, name, path, biennium, live, wrap=None, **params):
    """Read one list into <folder>/<name>.json (as {"read", "biennium", key: rows}) when due; keep the last copy when
    it fails."""
    out = os.path.join(folder, f"{name}.json")
    if not due(state, name, live) and os.path.exists(out):
        return load(out)
    rows = listing(path, f"{biennium} {name}", biennium, **params)
    if rows is None:
        if not out_of_time():
            print(f"{biennium} {name}: unreadable; kept the last copy", flush=True)
        return load(out)
    data = wrap(rows) if wrap else {"read": TODAY.isoformat(), "biennium": biennium, name: rows}
    save(data, out)
    state.setdefault("read", {})[name] = TODAY.isoformat()
    return data


def note_text(page):
    """The supplemental note's text from the viewer page: its paragraphs, separated by blank lines."""
    a = page.find('<div class="document-html-body">')
    if a < 0:
        return None
    b = page.find('<div class="document-', a + 10)  # the next panel, if any
    end = page.find("</main>", a)
    body = page[a:min(x for x in (b, end, len(page)) if x > 0)]
    body = re.sub(r"<script\b.*?</script>|<style\b.*?</style>", "", body, flags=re.S)
    paras = []
    for p in re.split(r"</p>|<br\s*/?>|</li>|</h\d>|</tr>", body):
        t = html.unescape(re.sub(r"<[^>]+>", "", p)).replace("\xa0", " ")
        t = re.sub(r"\s+", " ", t).strip()
        if t:
            paras.append(t)
    return "\n\n".join(paras)


def version_key(note):
    v = note.get("version") or ""
    return (int(v) if v.isdigit() else 99, note.get("rev_date") or "")


def biennium_lists(biennium, live):
    """One biennium's lists: bill status, members, leadership, committees, governor's actions, roll calls, notes."""
    year = first_year(biennium)
    folder = os.path.join(DATA, str(year))
    os.makedirs(folder, exist_ok=True)
    state_path = os.path.join(folder, "state.json")
    state = load(state_path, {})
    state["biennium"] = biennium

    bills = read_list(folder, state, "bill_status", "bill_status", biennium, live,
                      wrap=lambda rows: {"read": TODAY.isoformat(), "biennium": biennium, "bills": rows})
    save(state, state_path)
    if bills is not None:
        kinds = Counter(re.match(r"[A-Z]+", b.get("BILLNO") or "X").group() for b in bills["bills"])
        print(f"{year}: {len(bills['bills'])} measures ({', '.join(f'{k} {n}' for k, n in sorted(kinds.items()))})",
              flush=True)
    for name, path in (("legislators", "legislators"), ("leadership", "leadership"), ("committees", "committees"),
                       ("governor_actions", "governor-actions")):
        if out_of_time():
            break
        read_list(folder, state, name, path, biennium, live)
        save(state, state_path)
    if out_of_time():
        return
    read_list(folder, state, "votes", "votes", biennium, live,
              wrap=lambda rows: {"read": TODAY.isoformat(), "biennium": biennium,
                                 "votes": {r["apn"]: r for r in rows if r.get("apn")}})
    save(state, state_path)
    read_list(folder, state, "supp_notes", "supplemental-notes", biennium, live)
    save(state, state_path)


def hearing_time(t):
    """"1:30 PM" -> "13:30:00"; "00:00:00" when there's no clock time."""
    m = re.match(r"\s*(\d{1,2}):(\d\d)\s*([AP])\.?M", t or "", re.I)
    if not m:
        return "00:00:00"
    h = int(m.group(1)) % 12 + (12 if m.group(3).upper() == "P" else 0)
    return f"{h:02d}:{m.group(2)}:00"


def agendas(biennium):
    """Bills on upcoming committee hearings, from /api/v1/hearings/ (built from the journal's "Hearing: ..." lines,
    misc_he_200, which committees post a few days to a week ahead): yesterday to three weeks ahead, canceled ones left
    out, into <first year>/agendas.json as {"HB2001": [["House Education", "2027-01-20T13:30:00"], ...]}. One or two
    requests. A failure keeps the last file."""
    path = os.path.join(DATA, str(first_year(biennium)), "agendas.json")
    try:
        rows = listing("hearings", "hearings", biennium, **{"from": (TODAY - timedelta(days=1)).isoformat(),
                                                            "to": (TODAY + timedelta(days=21)).isoformat()})
    except Refused as e:
        print(f"agendas: refused ({e}); kept the last copy", flush=True)
        return
    if rows is None:
        print("agendas: unreadable; kept the last copy", flush=True)
        return
    out, meets = {}, set()
    for h in rows:
        if (h.get("status") or "").lower() in ("canceled", "cancelled") or not h.get("hearing_date"):
            continue
        title = re.sub(r"\s+", " ", h.get("committee_title") or "").strip()
        name = title if re.match(r"(House|Senate|Joint)\b", title) else f"{h.get('chamber') or ''} {title}".strip()
        when = f"{h['hearing_date']}T{hearing_time(h.get('hearing_time'))}"
        meets.add((name, when))
        for bill in h.get("bill_numbers") or []:
            bill = re.sub(r"\s+", "", bill or "").upper()
            if WANTED.match(bill) and [name, when] not in out.setdefault(bill, []):
                out[bill].append([name, when])
    for meets_of in out.values():
        meets_of.sort(key=lambda m: m[1])
    save(out, path)
    print(f"agendas: {len(out)} bills on {len(meets)} hearings", flush=True)
    # Committees' working meetings, from their weekly agendas: in session (January to May), or whenever hearings are set.
    if rows or TODAY.month <= 5:
        weekly_agendas(biennium)


# ---- Committees' weekly agendas (working meetings) ------------------------------------------------------------------
# The hearings list has only the bills set for a hearing. A committee's "final action" (working) meetings are on its
# weekly agenda, a text PDF each committee posts on its documents page: kslegislature.gov/<biennium>/committees/<code>/
# documents/, whose list of weekly agendas is the plain-HTML fragment .../documents/fragment/?type=weekly (a row per week,
# "March 29, 2026", linking /<biennium>/bills/download/?apn=<biennium>/year2/house/committees/ctte_h_ed_1/agendas/
# published/ctte_h_ed_1_20260208_wkagenda.pdf: the Sunday after the week, February 2-6, in the name). Each day reads:
#     1:30 PM                                   218-N
#     Monday, February 2
#     Discussion & action on:
#            HB2530 — Enacting the career readiness ...
#     Hearing on:
#            HB2428 — Requiring the state board of regents ...
#     Possible action on bills previously heard
# Bills under "Discussion & action on" (also "Final action on", "Action on", "Possible action on" with bills named) are
# agenda entries like a hearing's; "Possible action on bills previously heard" names no bills: the meeting is kept as
# "the committee meets", and convert.py gives it to the bills that committee has heard and still holds. Hearings are
# left to the hearings list. The PDFs have no date or version headers (a revised agenda, "Revision 4", keeps its name),
# so a week still to come or under way is read again when its copy is 6 hours old; a past week never.
WEEK_PDF = re.compile(r'href="(/b\d{4}_\d\d/bills/download/\?apn=[^"]+?_(\d{8})_wkagenda\.pdf)"')
DAY = re.compile(r"^\s*(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),?\s+(January|February|March|April|May|"
                 r"June|July|August|September|October|November|December)\s+(\d{1,2})\b", re.I)
CLOCK = re.compile(r"^\s*(\d{1,2}:\d\d\s*[AP]\.?\s?M\.?)", re.I)
ITEM = re.compile(r"^ {0,2}((?:Possible )?(?:final )?action on (?:bills|legislation|measures) previously heard\b|Request for bill introductions?\b|"
                  r"(?:[A-Z][A-Za-z&/,'\- ]{2,60}?)\s+(?:on|of)\b:?)(.*)$", re.I)
MEASURE = re.compile(r"\b(HB|SB|HCR|SCR)\s?(\d{4})\b")
MONTHS = {m: i + 1 for i, m in enumerate("january february march april may june july august september october november "
                                         "december".split())}


def parse_weekly(text, week):
    """A weekly agenda's text -> ([(bill, "2026-02-02T13:30:00")], [meeting times with "Possible action on bills
    previously heard"]). week: the date in the file's name, "20260208" (not the week's first day: that file holds
    February 2-6, 2026), which places the days' month and day in a year."""
    start = date(int(week[:4]), int(week[4:6]), int(week[6:])) - timedelta(days=14)
    acts, meets, day, clock, kind = [], [], None, "00:00:00", None
    for line in text.splitlines():
        if re.search(r"Committee Assistant is the point of contact|may request accommodation|Requests should be made"
                     r"|Administrative Services at:", line):
            continue
        c = CLOCK.match(line)
        if c:
            clock = hearing_time(c.group(1).replace(".", "").replace(" M", "M"))
        d = DAY.match(line)
        if d:
            month, n = MONTHS[d.group(2).lower()], int(d.group(3))
            # Within two weeks of the name's date either way (a week can run into the next month or year).
            for k in range(0, 29):
                x = start + timedelta(days=k)
                if (x.month, x.day) == (month, n):
                    day = x
                    break
            else:
                day = None
            kind = None
            continue
        i = ITEM.match(line)
        rest = line
        if i:
            head = i.group(1).lower()
            if "previously heard" in head:
                if day:
                    meets.append(f"{day.isoformat()}T{clock}")
                kind = None
                continue
            kind = "action" if re.search(r"\baction on\b", head) else "other"
            rest = i.group(2)
        if kind != "action" or not day:
            continue
        # Bills at the start of a line ("HB2530 — Enacting ...") or right after the heading's colon, not ones a
        # description mentions in passing.
        lead = re.split(r"\s+[—–-]\s+", rest.strip(), maxsplit=1)[0]
        if not re.match(r"\s*(?:HB|SB|HCR|SCR)\s?\d{4}\b", lead):
            continue
        for kind_, num in MEASURE.findall(lead):
            entry = (f"{kind_}{num}", f"{day.isoformat()}T{clock}")
            if entry not in acts:
                acts.append(entry)
    return acts, sorted(set(meets))


def weekly_agendas(biennium):
    """Each standing committee's weekly agendas from last week to three weeks ahead, into <first year>/weekly_agendas.json:
    {"bills": {"HB2530": [["House Education", "2026-02-02T13:30:00"]]}, "meets": [["House Education",
    "2026-02-05T13:30:00"]]}; the PDFs' text is kept in <first year>/wkagendas/. One request per committee (its list)
    plus one per week's agenda new or due again: about 50-90 a run in session. A failure keeps the last copy."""
    folder = os.path.join(DATA, str(first_year(biennium)))
    comms = (load(os.path.join(folder, "committees.json")) or {}).get("committees") or []
    comms = [c for c in comms if c.get("kpid") and c.get("chamber") in ("House", "Senate")
             and (c.get("committee_type") == "Standing" or (c.get("status") == "Active" and c.get("committee_type") in ("Special", "Select")))]
    if not comms:
        print("weekly agendas: no committee list; skipped", flush=True)
        return
    cache = os.path.join(folder, "wkagendas")
    os.makedirs(cache, exist_ok=True)
    seen_path = os.path.join(cache, "read.json")
    seen = load(seen_path, {}) or {}
    lo, hi = TODAY - timedelta(days=7), TODAY + timedelta(days=21)
    bills, meets, read, failed = {}, set(), 0, 0
    for c in comms:
        if out_of_time():
            break
        title = re.sub(r"\s+", " ", c.get("title") or "").strip()
        name = title if re.match(r"(House|Senate|Joint)\b", title) else f"{c['chamber']} {title}"
        page = request(f"{SITE}/{biennium}/committees/{c['kpid']}/documents/fragment/?type=weekly", f"{c['kpid']} weekly",
                       kind="text")
        if page is None:
            failed += 1
            continue
        for href, week in dict(WEEK_PDF.findall(page)).items():
            # The name's date is the Sunday after the week it covers (..._20260208_ holds February 2-6, 2026); read
            # generously, as two weeks before it to one after.
            named = date(int(week[:4]), int(week[4:6]), int(week[6:]))
            if not (lo <= named + timedelta(days=7) and named - timedelta(days=14) <= hi):
                continue
            fname = os.path.join(cache, href.rsplit("/", 1)[-1].replace(".pdf", ".txt"))
            when = seen.get(href)
            stale = not os.path.exists(fname) or (named + timedelta(days=7) >= TODAY and (
                not when or time.time() - when > 6 * 3600))
            if stale and not out_of_time():
                body = request(SITE + html.unescape(href), f"{c['kpid']} {week}", kind="bytes")
                if body and body[:4] == b"%PDF":
                    import subprocess
                    try:
                        r = subprocess.run(["pdftotext", "-layout", "-", "-"], input=body, capture_output=True)
                    except OSError:  # no pdftotext: the hearings list alone, as before
                        print("weekly agendas: pdftotext isn't installed; skipped", flush=True)
                        return
                    if r.returncode == 0:
                        with open(fname, "w", encoding="utf-8") as f:
                            f.write(r.stdout.decode("utf-8", "replace"))
                        seen[href] = time.time()
                        read += 1
                else:
                    failed += 1
            if not os.path.exists(fname):
                continue
            acts, ms = parse_weekly(open(fname, encoding="utf-8").read(), week)
            for bill, at in acts:
                if WANTED.match(bill) and [name, at] not in bills.setdefault(bill, []):
                    bills[bill].append([name, at])
            meets.update((name, at) for at in ms)
    save(seen, seen_path)
    for v in bills.values():
        v.sort(key=lambda m: m[1])
    save({"read": TODAY.isoformat(), "bills": bills, "meets": sorted(meets)}, os.path.join(folder, "weekly_agendas.json"))
    print(f"weekly agendas: {len(bills)} bills for action, {len(meets)} meetings on bills heard; {read} agendas read, "
          f"{failed} failures, {len(comms)} committees", flush=True)


def biennium_extras(biennium):
    """One biennium's supplemental notes' texts (fewer, and they're "What it does"), then its roll calls' members."""
    year = first_year(biennium)
    folder = os.path.join(DATA, str(year))
    os.makedirs(os.path.join(folder, "votes"), exist_ok=True)
    os.makedirs(os.path.join(folder, "notes"), exist_ok=True)
    state_path = os.path.join(folder, "state.json")
    state = load(state_path, {})
    votes_list = load(os.path.join(folder, "votes.json"))
    notes_list = load(os.path.join(folder, "supp_notes.json"))
    if notes_list:
        latest = {}
        for n in notes_list["supp_notes"]:
            bill = (n.get("bill_no") or "").upper()
            if WANTED.match(bill) and (bill not in latest or version_key(n) > version_key(latest[bill])):
                latest[bill] = n
        absent = state.setdefault("absent", {})
        todo = []
        for bill, n in sorted(latest.items()):
            have = load(os.path.join(folder, "notes", f"{bill}.json")) or {}
            if n.get("pdf_only"):
                continue
            if (have.get("apn"), have.get("rev_date")) == (n["apn"], n.get("rev_date")):
                continue
            if absent.get(n["apn"]) == n.get("rev_date"):
                continue
            todo.append((bill, n))
        print(f"{year} notes: {len(latest)} bills with a supplemental note; {len(todo)} to read", flush=True)
        got = 0
        for bill, n in todo:
            if out_of_time():
                break
            url = f"{SITE}/{biennium}/documents/view-leg/?{urllib.parse.urlencode({'apn': n['apn']})}"
            page = request(url, f"{year} note {bill}", "text")
            text = note_text(page) if page else None
            if not text:
                if CODE[0] == 404 or page:
                    absent[n["apn"]] = n.get("rev_date")
                continue
            save({"bill": bill, "apn": n["apn"], "version": n.get("version"), "rev_date": n.get("rev_date"),
                  "keywords": n.get("keywords"), "text": text}, os.path.join(folder, "notes", f"{bill}.json"))
            got += 1
            STATS["notes"] += 1
            if got % 25 == 0:
                save(state, state_path)
        save(state, state_path)
        print(f"{year} notes: {got} of {len(todo)} read", flush=True)

    if votes_list and not out_of_time():
        todo = []
        for apn, v in votes_list["votes"].items():
            if not WANTED.match((v.get("bill_no") or "").upper()):
                continue
            have = load(os.path.join(folder, "votes", vote_file(apn) + ".json")) or {}
            if have.get("rev_date") != v.get("rev_date") or "members" not in have:
                todo.append(apn)
        todo.sort(key=lambda a: votes_list["votes"][a].get("occurred") or "", reverse=True)  # newest first
        print(f"{year} roll calls: {len(votes_list['votes'])} listed; {len(todo)} to read", flush=True)
        got = 0
        for apn in todo:
            if out_of_time():
                break
            v = request(f"{API}/votes/{urllib.parse.quote(apn)}/", f"{year} vote {apn}")
            if not isinstance(v, dict) or "members" not in v:
                continue  # the last copy stays, and it's asked again next run
            save(v, os.path.join(folder, "votes", vote_file(apn) + ".json"))
            got += 1
            STATS["votes"] += 1
        print(f"{year} roll calls: {got} of {len(todo)} read", flush=True)
    save(state, state_path)


def fiscal_notes(biennium):
    """The fiscal note on each bill with no supplemental note (see the module's docstring), as the run's time allows."""
    year = first_year(biennium)
    folder = os.path.join(DATA, str(year))
    bills = (load(os.path.join(folder, "bill_status.json")) or {}).get("bills") or []
    notes_list = load(os.path.join(folder, "supp_notes.json"))
    if not notes_list:
        return  # (which bills have a supplemental note isn't known yet)
    with_note = {(n.get("bill_no") or "").upper() for n in notes_list.get("supp_notes") or []}
    state_path = os.path.join(folder, "state.json")
    state = load(state_path, {})
    absent = state.setdefault("absent", {})
    os.makedirs(os.path.join(folder, "fnotes"), exist_ok=True)
    todo = []
    for b in bills:
        bill = (b.get("BILLNO") or "").upper()
        if not WANTED.match(bill) or bill in with_note:
            continue
        docs = [v.get("associated_documents", {}).get("fiscal_note") for v in b.get("versions") or []]
        docs = [d for d in docs if d]
        if not docs:
            continue
        m = re.search(r"apn=([^&]+)", docs[-1])
        if not m:
            continue
        apn = urllib.parse.unquote(m.group(1))
        have = load(os.path.join(folder, "fnotes", f"{bill}.json")) or {}
        if have.get("apn") == apn or absent.get(apn):
            continue
        todo.append((bill, apn))
    got = 0
    for bill, apn in todo:
        if out_of_time():
            break
        url = f"{SITE}/{biennium}/documents/view-leg/?{urllib.parse.urlencode({'apn': apn})}"
        page = request(url, f"{year} fiscal note {bill}", "text")
        text = note_text(page) if page else None
        if not text:
            if CODE[0] == 404 or page:
                absent[apn] = TODAY.isoformat()
            continue
        save({"bill": bill, "apn": apn, "text": text}, os.path.join(folder, "fnotes", f"{bill}.json"))
        got += 1
        if got % 25 == 0:
            save(state, state_path)
    save(state, state_path)
    if todo:
        print(f"{year} fiscal notes: {got} of {len(todo)} read (bills with no supplemental note)", flush=True)


def member_details(biennium):
    """The active members' details, when missing or a week old. A detail that fails keeps its last copy."""
    os.makedirs(MEMBERS, exist_ok=True)
    legs = load(os.path.join(DATA, str(first_year(biennium)), "legislators.json")) or {}
    active = [m["kpid"] for m in legs.get("legislators", []) if m.get("status") == "Active" and m.get("kpid")]
    week = (TODAY - timedelta(days=WEEKLY)).isoformat()
    todo = [k for k in active if (load(os.path.join(MEMBERS, f"{k}.json")) or {}).get("_read", "") < week]
    got = 0
    for k in todo:
        if out_of_time():
            break
        d = request(f"{API}/legislators/{urllib.parse.quote(k)}/?biennium={biennium}", f"member {k}")
        if isinstance(d, dict) and d.get("kpid"):
            d["_read"] = TODAY.isoformat()
            save(d, os.path.join(MEMBERS, f"{k}.json"))
            got += 1
    if todo:
        print(f"members: {len(active)} active; {got} of {len(todo)} details read", flush=True)


def begun(b):
    """Whether a biennium's Legislature has convened (the second Monday of January of its first year). One made active
    before then, without its members yet, is read when it's there but never holds Kansas off the site."""
    y = first_year(b)
    return TODAY >= date(y, 1, 1 + (0 - date(y, 1, 1).weekday()) % 7 + 7)


def biennium_of(year):
    """The biennium a year belongs to: 2027 and 2028 -> "b2027_28"."""
    y = year if year % 2 else year - 1
    return f"b{y}_{str(y + 1)[2:]}"


def waiting(b):
    """A biennium with no bills on file (the next one, before or just after it convenes): skipped unless the API lists a
    bill for it (one request a run), so an empty one is never saved (the converter would show it as a session with no
    bills, and the build would take it for the current one) and never holds Kansas back. Its prefiled bills, once the
    API lists them, are read from then on."""
    if os.path.exists(os.path.join(DATA, str(first_year(b)), "bill_status.json")):
        return False
    page = request(f"{API}/bill_status/?{urllib.parse.urlencode({'biennium': b, 'limit': 1})}", f"{b} bills listed")
    if isinstance(page, dict) and page.get("count"):
        print(f"{b}: {page['count']} measures listed; reading its first copy", flush=True)
        return False
    print(f"{b}: no bills listed yet", flush=True)
    return True


def never_downloaded(bienniums, active):
    """What was never downloaded: a biennium's bill status, the active biennium's legislators or committees, an active
    member's details. (A failed refresh with a last copy doesn't count; nor do roll calls and notes, which fill in.)"""
    out = []
    bienniums = [b for b in bienniums if begun(b)]
    for b in bienniums:
        if load(os.path.join(DATA, str(first_year(b)), "bill_status.json")) is None:
            out.append(f"{first_year(b)}:bills")
    if active in bienniums:
        folder = os.path.join(DATA, str(first_year(active)))
        legs = load(os.path.join(folder, "legislators.json"))
        if legs is None:
            out.append("legislators")
        else:
            missing = [m["kpid"] for m in legs.get("legislators", []) if m.get("status") == "Active"
                       and not os.path.exists(os.path.join(MEMBERS, f"{m['kpid']}.json"))]
            # (A new Legislature's members' details, read in its first January, don't hold Kansas back.)
            if missing and not (first_year(active) == TODAY.year and TODAY.month == 1):
                out.append(f"members({len(missing)})")
        if load(os.path.join(folder, "committees.json")) is None:
            out.append("committees")
    return out


def main():
    os.makedirs(DATA, exist_ok=True)
    # Before the first copy, a run cut off without its summary leaves this, so a partial copy isn't published.
    if not ONLY and not any(name.isdigit() for name in os.listdir(DATA)):
        with open(MARKER, "w") as f:
            f.write("running\n")
    print(f"Kansas: {'with an API key' if KEY else 'no API key'}, a request every {DELAY} s", flush=True)
    refused = False
    bienniums, active, nxt = [], None, []
    try:
        b = request(f"{API}/biennia/", "biennia")
        if isinstance(b, dict) and b.get("active"):
            active = b["active"]["biennium"]
            archived = sorted((a["biennium"] for a in b.get("archived", [])), reverse=True)
            save(b, os.path.join(DATA, "biennia.json"))
        else:
            last = load(os.path.join(DATA, "biennia.json")) or {}
            if last.get("active"):
                print("biennia: unreadable; kept the last copy", flush=True)
                active = last["active"]["biennium"]
                archived = sorted((a["biennium"] for a in last.get("archived", [])), reverse=True)
            else:
                archived = []
        if active:
            # The active biennium and the archived ones in the shared window (states/window.py: from b2023_24 until
            # 2029); a biennium the site no longer lists keeps its last copy.
            # From November 1, the next biennium (prefiled bills), and in January the new one, when the API doesn't
            # list it yet; it's read like the active one once it has bills.
            nxt = [x for x in [biennium_of(TODAY.year + 1 if TODAY.month >= 11 else TODAY.year)]
                   if x != active and x not in archived and first_year(x) > first_year(active)]
            bienniums = [active] + nxt + [x for x in archived if first_year(x) >= W.first_session()]
            if ONLY:
                bienniums = [x for x in [active] + nxt + archived if first_year(x) == ONLY]
            bienniums = [x for x in bienniums if not waiting(x)]
        # What the site needs first (each biennium's lists, the active members' details), then the extras.
        for x in bienniums:
            if out_of_time():
                break
            biennium_lists(x, x == active or x in nxt)  # the next biennium's lists every run too
            if x == active and not out_of_time():
                agendas(x)
            if x == active and not out_of_time():
                member_details(x)
        for x in bienniums:
            if out_of_time():
                break
            biennium_extras(x)
        for x in bienniums:
            if out_of_time():
                break
            fiscal_notes(x)
    except Refused as e:
        print(f"Stopped: the server refused a request ({e})", flush=True)
        refused = True
    missing = never_downloaded(bienniums, active) if bienniums else ["biennia"]
    print(f"run: {STATS['requests']} requests ({STATS['votes']} roll calls, {STATS['notes']} notes), "
          f"{round((time.time() - START) / 60)} min"
          + ("; stopped at the time limit" if out_of_time() else "")
          + ("; refused" if refused else "")
          + (f"; request failures {dict(FAILS)}" if FAILS else "; no request failures")
          + (f"; never downloaded: {' '.join(missing)}" if missing else "; nothing missing"), flush=True)
    if ONLY:
        return
    # Left while data that was never downloaded is missing, so a partial first copy isn't published.
    if missing:
        with open(MARKER, "w") as f:
            f.write(" ".join(missing) + "\n")
    elif os.path.exists(MARKER):
        os.remove(MARKER)


if __name__ == "__main__":
    main()
