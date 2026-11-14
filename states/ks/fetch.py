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

Not read: bill texts (PDFs; /api/v1/measures/<bill>/text/ has them as lines), fiscal notes (PDFs), testimony, hearings
(/api/v1/hearings/), committee minutes, and the website's pages, whose emails are hidden behind Cloudflare's script
(the API and the members' CSV export give them openly).

data/ks/incomplete says "running" during the first copy, then lists what was never downloaded (a biennium's bill status,
the active biennium's legislators, committees or an active member's details); it is removed when nothing is missing. A
list that fails where a last copy exists keeps that copy and doesn't count; a biennium that hasn't begun (no bills yet)
doesn't count either.
Usage: python3 states/ks/fetch.py [biennium first year]   (default: the active and newest archived; one leaves the marker)
"""
import gzip, html, json, os, re, sys, time, urllib.error, urllib.parse, urllib.request
from collections import Counter
from datetime import date, timedelta

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


def never_downloaded(bienniums, active):
    """What was never downloaded: a biennium's bill status, the active biennium's legislators or committees, an active
    member's details. (A failed refresh with a last copy doesn't count; nor do roll calls and notes, which fill in.)"""
    out = []
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
            if missing:
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
    bienniums, active = [], None
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
            bienniums = [active] + archived[:1]
            if ONLY:
                bienniums = [x for x in [active] + archived if first_year(x) == ONLY]
        # What the site needs first (each biennium's lists, the active members' details), then the extras.
        for x in bienniums:
            if out_of_time():
                break
            biennium_lists(x, x == active)
            if x == active and not out_of_time():
                member_details(x)
        for x in bienniums:
            if out_of_time():
                break
            biennium_extras(x)
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
