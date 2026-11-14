#!/usr/bin/env python3
"""Download North Dakota's bills from the Legislative Council's API (https://ndlegis.gov/legislative-api-documentation):
static JSON files, one set per Legislative Assembly, no key. ndlegis.gov's robots.txt (checked 2026-11-08) is Drupal's
stock one: it bars /admin/, /search/, /user/ and the like, nothing read here, and sets no crawl delay; www.ndlegis.gov
and legis.nd.gov only redirect to it. One request at a time, a second apart (counted from the end of the last answer).

North Dakota's Legislative Assembly meets in odd years (the 69th's regular session was 2025; the 68th's, 2023), after an
organizational session the December before, and the Legislative Management can call it back for special sessions
(the 69th met in January and September 2026, the 68th in October 2023). Each assembly goes in data/nd/<first year>/
(from FIRST_YEAR, the first with member votes; the next assembly once its files exist, with prefiled bills from
December):
- sessions.json, members.json, committees.json, bills.json, roll_call.json: the API's files as served
  (/api/assembly/69-2025/data/<name>.json), read again when their Last-Modified changes (If-Modified-Since: a 304 when
  unchanged; even a finished assembly's files are regenerated now and then, 68-2023's in July 2026).
  - bills.json ({"bills": {"1012": {...}}}, keyed by number): every bill and resolution of the assembly, special
    sessions' included (session_id "202502"; their numbers follow the regular session's, HB 1621 on): HB, SB, HCR and
    SCR (concurrent resolutions; those amending the Constitution of North Dakota say so in the title, "A concurrent
    resolution to amend and reenact section 9 of article V of the Constitution of North Dakota"; the others are
    requests and memorials), HR, HMR, SMR. Telling amendments from the rest is the converter's job. Each has its
    title, its "Relating to ..." summary (the title's subject clause: there is no plain-language summary), chamber,
    status ("Governor signed", "Governor signed (Item veto)", "Veto sustained", "Failed in House", "Withdrawn"),
    passed, the requesting agency, sponsors in order (members or committees, by id, primary flag), versions (LC
    numbers: "25.0156.02000" the first engrossment) and actions with dates and a category ("Committee report",
    "Passed", "Concurred", "Filed with Secretary of State", "Vetoed by Governor", "Veto sustained") and, for a floor
    vote, its roll call (id and totals). Committee reports carry their tally in the wording ("Reported back, do pass,
    place on calendar 13 0 1") but no names: committee votes by member are only in the minutes (PDFs, not read).
    Hearings name their committee.
  - roll_call.json: every floor roll call member by member (member_votes: member id, "Last, First", Yea/Nay/Absent),
    with the bill, version, motion ("Final Passage", "Consideration of Amendments", "Reconsider") and totals. Every
    action's roll call id is in it (checked 2023 and 2025).
  - members.json: every member who served (id, name, chamber, party, district, biography page, active); committees.json:
    standing, procedural and interim committees with members (is_chair, is_vice_chair).
- chapters.json: {"HB 1012": {"chapter": "11", "veto": ""}} from the Session Laws' bill index
  (/assembly/69-2025/session-laws/bill-index.html; veto "Vetoed" or "Item Vetoed"), published some months after the
  regular session (special sessions' laws aren't in it: they are only a PDF, sl2023ss.pdf; every other bill filed
  with the Secretary of State has a chapter, 2023 and 2025). The actions say "Filed with Secretary Of State" without the
  chapter. Read when missing, and weekly while the assembly is live.
- leaders.json: the leadership page (/assembly/69-2025/regular/members/leadership): each house's leaders with their
  biography slug and positions ("Majority Leader", "Majority Caucus Leader Effective 1/7/25 - 4/29/25"). Read when
  missing, and weekly while the assembly is live.
And into data/nd/members/<slug>.json, one per member of any assembly read (the slug is the members.json url's,
/biography/bert-anderson): the biography page's contact fields (Home, Work, Cell phones; Email) and photo. Read when
missing, and weekly for the newest assembly's active members; a page that answers 404 is noted in data/nd/bios.json
and not asked again. Members who have left keep their page without contact fields (32 of 177 in November 2026). Member
ids differ between assemblies, and so can slugs and names for the same person ("Hoverson, Jeff A." jeff-a-hoverson in
2023, "Hoverson, Jeff" jeff-hoverson in 2025: both pages are served, with the same phones).

What it does: nothing plain-language in the data. The Legislative Council staff's statements of purpose of amendment
("SPA", one per amendment) and the fiscal notes are PDFs (/assembly/69-2025/regular/documents/25-0156-01018s.pdf),
not read; "What it does" can be the title's clauses.

A first copy of two assemblies is about 10 requests for the files (about 36 MB) and about 190 for the members' pages:
about 5 minutes. After that a run is about 14 requests (mostly 304s), plus the weekly members' pages: under a minute,
about 4 minutes once a week.

data/nd/incomplete says "running" during a first copy, then lists what was never downloaded (an assembly's file, its
leaders or chapters while the server has them, a member's page); it is removed when nothing is missing. A request that
fails where a last copy exists keeps that copy and doesn't count; a 404 for a page not yet published doesn't count.
Usage: python3 states/nd/fetch.py [first year]   (default: every assembly from FIRST_YEAR; one leaves the marker alone)
"""
import html, json, os, re, sys, time, urllib.error, urllib.request
from collections import Counter
from datetime import date, timedelta

SITE = "https://ndlegis.gov"
DATA = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "nd"))
AGENT = "statebilltracker.org (a nonprofit bill tracker; contact via github.com/judithhubbard)"
TODAY = date.today()
ONLY = int(sys.argv[1]) if len(sys.argv) > 1 else None
FIRST_YEAR = 2023  # the 68th Legislative Assembly; roll_call.json starts with it
DELAY = 1
FILES = ("sessions", "members", "committees", "bills", "roll_call")  # each file's top key is its name
WEEKLY = 7
MEMBERS = os.path.join(DATA, "members")
BIOS = os.path.join(DATA, "bios.json")
MARKER = os.path.join(DATA, "incomplete")

# The run's own time limit (FETCH_MINUTES, set by the workflow): stop a few minutes early, with everything read so far
# saved and a summary printed, rather than be cut off silently mid-request.
START = time.time()
BUDGET = max(0.0, float(os.environ.get("FETCH_MINUTES") or 0) - 5) * 60
FAILS = Counter()  # why requests failed, for the summary
STATS = {"requests": 0, "unchanged": 0}
LAST = [0.0]  # when the last answer ended
NOT_MODIFIED = object()  # a 304
GONE = object()  # a 404


class Refused(Exception):
    """The server turned us away (401/403/429, or a JSON file answered with a web page): stop the run."""


def out_of_time():
    return BUDGET and time.time() - START > BUDGET


def request(url, label, since=None, json_wanted=False):
    """GET url: (body bytes, Last-Modified); (NOT_MODIFIED, since) for a 304; (GONE, None) for a 404; (None, None) after
    three tries. Refused on 401/403/429, or when a JSON file comes back as something else (a challenge page)."""
    for attempt in range(3):
        if out_of_time():
            return None, None
        wait = LAST[0] + DELAY - time.time()
        if wait > 0:
            time.sleep(wait)
        STATS["requests"] += 1
        if STATS["requests"] % 100 == 0:
            print(f"  {STATS['requests']} requests, {round((time.time() - START) / 60)} min"
                  + (f"; failures {dict(FAILS)}" if FAILS else ""), flush=True)
        headers = {"User-Agent": AGENT}
        if since:
            headers["If-Modified-Since"] = since
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=180) as r:
                body = r.read()
                kind = r.headers.get("Content-Type") or ""
                modified = r.headers.get("Last-Modified")
                length = r.headers.get("Content-Length")
            LAST[0] = time.time()
            if json_wanted and "json" not in kind:
                raise Refused(f"{label}: answered {kind or 'no type'}, not JSON (a challenge page?)")
            if length and int(length) != len(body):
                FAILS["cut off"] += 1
            else:
                return body, modified
        except Refused:
            raise
        except urllib.error.HTTPError as e:
            LAST[0] = time.time()
            if e.code == 304:
                STATS["unchanged"] += 1
                return NOT_MODIFIED, since
            FAILS[f"HTTP {e.code}"] += 1
            if e.code in (401, 403, 429):
                raise Refused(f"{label}: HTTP {e.code}")
            if e.code == 404:
                return GONE, None
        except Exception as e:
            LAST[0] = time.time()
            FAILS[type(e).__name__] += 1
        time.sleep(10 * (attempt + 1))
    print(f"{label}: failed three times", flush=True)
    return None, None


def save(obj, path):
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(obj, f, ensure_ascii=False)
    os.replace(tmp, path)


def save_bytes(body, path):
    with open(path + ".tmp", "wb") as f:
        f.write(body)
    os.replace(path + ".tmp", path)


def load(path, default=None):
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def text(fragment):
    """Plain text of an HTML fragment, whitespace collapsed."""
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", fragment))).strip()


def stale(day, days=WEEKLY):
    return not day or day < (TODAY - timedelta(days=days)).isoformat()


def assemblies():
    """The assemblies from FIRST_YEAR on, newest first: [{"year", "key" ("69-2025"), "number", "sessions", "live"}].
    An assembly is live until July of the year after its biennium (special sessions, session laws, members' changes)."""
    path = os.path.join(DATA, "assemblies.json")
    body, _ = request(f"{SITE}/api/data/assemblies.json", "assemblies", json_wanted=True)
    try:
        found = json.loads(body) if isinstance(body, bytes) else None
    except ValueError:
        found = None
    if isinstance(found, dict) and found:
        save(found, path)
    else:
        print("assemblies: unreadable; kept the last copy", flush=True)
        found = load(path, {})
    out = []
    for a in found.values():
        year = int(a.get("biennium_start") or 0)
        if year < FIRST_YEAR or (ONLY and year != ONLY):
            continue
        live = TODAY < date(int(a.get("biennium_end") or year + 2), 7, 1)
        out.append({"year": year, "key": a["assembly_year"], "number": a["assembly"], "live": live,
                    "sessions": a.get("sessions") or []})
    return sorted(out, key=lambda a: -a["year"])


def data_files(a, folder, state):
    """The API's five files, each when new or changed. False when the assembly has no bills file yet (nothing to read)."""
    modified = state.setdefault("modified", {})
    absent = state.setdefault("absent", {})
    for name in ("bills",) + tuple(f for f in FILES if f != "bills"):
        path = os.path.join(folder, f"{name}.json")
        have = os.path.exists(path)
        body, stamp = request(f"{SITE}/api/assembly/{a['key']}/data/{name}.json", f"{a['year']} {name}",
                              since=modified.get(name) if have else None, json_wanted=True)
        if body is NOT_MODIFIED:
            continue
        if body is GONE:
            if not have:
                absent[name] = TODAY.isoformat()  # not published (yet): not missing
                if name == "bills":
                    print(f"{a['year']}: no bills file yet", flush=True)
                    return False
            else:
                print(f"{a['year']} {name}: answered 404; kept the last copy", flush=True)
            continue
        try:
            d = json.loads(body) if body else None
        except ValueError:
            d = None
        if not isinstance(d, dict) or not d.get(name):
            print(f"{a['year']} {name}: unreadable" + ("; kept the last copy" if have else ""), flush=True)
            continue
        os.makedirs(folder, exist_ok=True)
        save_bytes(body, path)
        modified[name] = stamp
        absent.pop(name, None)
        print(f"{a['year']} {name}: {len(d[name])}", flush=True)
    return True


def leaders(a, folder, state):
    """leaders.json from the leadership page: when missing, and weekly while the assembly is live."""
    path = os.path.join(folder, "leaders.json")
    if os.path.exists(path) and not (a["live"] and stale(state.get("leaders"))):
        return
    body, _ = request(f"{SITE}/assembly/{a['key']}/regular/members/leadership", f"{a['year']} leaders")
    if body is GONE:
        state["leaders_absent"] = TODAY.isoformat()
        return
    if not isinstance(body, bytes):
        return
    page = body.decode("utf-8", "replace")
    out, house = [], None
    for m in re.finditer(r'<h3 class="title">\s*(House|Senate)\s*</h3>|<li\s+class="member-item[^"]*">(.*?)</li>', page, re.S):
        if m.group(1):
            house = m.group(1)
            continue
        item = m.group(2)
        slug = re.search(r'href="/biography/([^"]+)"', item)
        name = re.search(r'member-name">(.*?)</div>', item, re.S)
        district = re.search(r'>District (\w+)</a>', item)
        party = re.search(r'<figure class="hidden">(.*?)</figure>', item)
        pos = item.find('class="member-position"')
        out.append({"slug": slug.group(1) if slug else None, "name": text(name.group(1)) if name else "",
                    "chamber": house, "district": district.group(1) if district else None,
                    "party": text(party.group(1)) if party else None,
                    "position": text(item[pos:].split(">", 1)[1]) if pos >= 0 else "",
                    "new": "legislator-is-new" in item})
    if not out:
        print(f"{a['year']} leaders: no leaders on the page" + ("; kept the last copy" if os.path.exists(path) else ""),
              flush=True)
        return
    save(out, path)
    state["leaders"] = TODAY.isoformat()
    state.pop("leaders_absent", None)
    print(f"{a['year']} leaders: {len(out)}", flush=True)


def chapters(a, folder, state):
    """chapters.json from the Session Laws' bill index: when missing, and weekly while the assembly is live."""
    path = os.path.join(folder, "chapters.json")
    if os.path.exists(path) and not (a["live"] and stale(state.get("chapters"))):
        return
    if not os.path.exists(path) and state.get("chapters_absent") and not stale(state["chapters_absent"]):
        return  # not published when last asked, this week
    body, _ = request(f"{SITE}/assembly/{a['key']}/session-laws/bill-index.html", f"{a['year']} chapters")
    if body is GONE:
        state["chapters_absent"] = TODAY.isoformat()
        return
    if not isinstance(body, bytes):
        return
    out = {}
    for row in re.findall(r"<tr[^>]*>(.*?)</tr>", body.decode("utf-8", "replace"), re.S):
        cells = [text(c) for c in re.findall(r"<td[^>]*>(.*?)</td>", row, re.S)]
        if len(cells) >= 3 and re.fullmatch(r"[HS][A-Z]* \d+", cells[0]) and cells[2].isdigit():
            out[cells[0]] = {"chapter": cells[2], "veto": cells[1]}
    if not out:
        state["chapters_absent"] = TODAY.isoformat()  # a page without its table yet
        print(f"{a['year']} chapters: none on the page yet", flush=True)
        return
    save(out, path)
    state["chapters"] = TODAY.isoformat()
    state.pop("chapters_absent", None)
    print(f"{a['year']} chapters: {len(out)} ({sum(1 for v in out.values() if v['veto'])} with a veto)", flush=True)


def slug_of(member):
    m = re.search(r"/biography/([^/?#]+)", member.get("url") or "")
    return m.group(1) if m else None


def bio_page(page):
    """A biography page's contact fields: {"phones": {"Home": ...}, "email", "photo"}; None if it isn't one."""
    if "node--type-person" not in page:
        return None
    out = {"phones": {}, "email": None, "photo": None}
    box = page.find("biography-contact-information-wrapper")
    if box >= 0:
        end = page.find("print__wrapper", box)
        for name, label, value in re.findall(r'field--name-field-([\w-]+)[^>]*>\s*<div class="field__label">(.*?)</div>'
                                             r'\s*<div class="field__item">(.*?)</div>', page[box:end if end > 0 else None], re.S):
            value = text(value)
            if "email" in name:
                out["email"] = value
            elif value:
                out["phones"][text(label)] = value
    photo = re.search(r'src="(/sites/default/files/styles/biography_image/[^"]+)"', page)
    if photo:
        out["photo"] = SITE + html.unescape(photo.group(1)).split("?")[0]
    return out


def bios(found):
    """Each member's biography page: when missing, and weekly for the newest assembly's active members."""
    os.makedirs(MEMBERS, exist_ok=True)
    seen = load(BIOS, {})  # slug -> {"read": day} or {"gone": day}
    want, current = {}, set()
    for i, a in enumerate(found):
        for m in (load(os.path.join(DATA, str(a["year"]), "members.json"), {}) or {}).get("members") or []:
            slug = slug_of(m)
            if slug:
                want.setdefault(slug, m)
                if i == 0 and m.get("active"):
                    current.add(slug)
    todo = [s for s in want if not seen.get(s, {}).get("gone")
            and (not os.path.exists(os.path.join(MEMBERS, f"{s}.json")) or (s in current and stale(seen.get(s, {}).get("read"))))]
    got = 0
    for slug in todo:
        if out_of_time():
            break
        body, _ = request(f"{SITE}/biography/{slug}", f"member {slug}")
        if body is GONE:
            seen[slug] = {"gone": TODAY.isoformat()}
        elif isinstance(body, bytes):
            info = bio_page(body.decode("utf-8", "replace"))
            if info is None:
                print(f"member {slug}: not a biography page" + ("; kept the last copy" if os.path.exists(
                    os.path.join(MEMBERS, f"{slug}.json")) else ""), flush=True)
                continue
            m = want[slug]
            save({"slug": slug, "url": m.get("url"), "name": m.get("name"), **info}, os.path.join(MEMBERS, f"{slug}.json"))
            seen[slug] = {"read": TODAY.isoformat()}
            got += 1
            if got % 25 == 0:
                save(seen, BIOS)
    save(seen, BIOS)
    print(f"members' pages: {got} of {len(todo)} read ({len(want)} members)", flush=True)


def begun(a):
    """Whether an assembly has convened (the first Tuesday after January 3 of its first year). One listed earlier, with
    prefiled bills, is read when it's there but never holds North Dakota off the site."""
    y = a["year"]
    return TODAY >= date(y, 1, 4 + (1 - date(y, 1, 4).weekday()) % 7)


def missing(a, seen):
    """What of this assembly was never downloaded (a failed re-read with a last copy, or a 404 for something not
    published yet, doesn't count)."""
    folder = os.path.join(DATA, str(a["year"]))
    state = load(os.path.join(folder, "state.json"), {})
    absent = state.get("absent") or {}
    if not os.path.exists(os.path.join(folder, "bills.json")):
        return [] if "bills" in absent else [f"{a['year']}:bills"]
    out = [f"{a['year']}:{f}" for f in FILES if not os.path.exists(os.path.join(folder, f"{f}.json")) and f not in absent]
    if not os.path.exists(os.path.join(folder, "leaders.json")) and not state.get("leaders_absent"):
        out.append(f"{a['year']}:leaders")
    if not os.path.exists(os.path.join(folder, "chapters.json")) and not state.get("chapters_absent"):
        out.append(f"{a['year']}:chapters")
    members = (load(os.path.join(folder, "members.json"), {}) or {}).get("members") or []
    if any(slug_of(m) and not seen.get(slug_of(m), {}).get("gone")
           and not os.path.exists(os.path.join(MEMBERS, f"{slug_of(m)}.json")) for m in members):
        out.append(f"{a['year']}:contacts")
    return out


def main():
    os.makedirs(DATA, exist_ok=True)
    # Before the first copy, a run cut off without its summary leaves this, so a partial copy isn't published.
    if not ONLY and not any(name.isdigit() for name in os.listdir(DATA)):
        with open(MARKER, "w") as f:
            f.write("running\n")
    refused = False
    found = []
    try:
        found = assemblies()
        read = []
        for a in found:  # the newest first
            if out_of_time():
                break
            folder = os.path.join(DATA, str(a["year"]))
            state = load(os.path.join(folder, "state.json"), {})
            has_bills = data_files(a, folder, state)
            if has_bills:
                leaders(a, folder, state)
                chapters(a, folder, state)
                read.append(a)
            if os.path.isdir(folder):
                save(state, os.path.join(folder, "state.json"))
        bios(read)
    except Refused as e:
        print(f"Stopped: the server refused a request ({e})", flush=True)
        refused = True
    gaps = [g for a in found if begun(a) for g in missing(a, load(BIOS, {}))]
    if not found:
        gaps.append("assemblies")
    sizes = []
    for a in found:
        folder = os.path.join(DATA, str(a["year"]))
        bills = (load(os.path.join(folder, "bills.json"), {}) or {}).get("bills") or {}
        votes = (load(os.path.join(folder, "roll_call.json"), {}) or {}).get("roll_call") or []
        if bills:
            sizes.append(f"{a['year']} {len(bills)} bills, {len(votes)} roll calls")
    print(f"run: {STATS['requests']} requests ({STATS['unchanged']} unchanged), {round((time.time() - START) / 60, 1)} min"
          + (f"; {'; '.join(sizes)}" if sizes else "")
          + ("; stopped at the time limit" if out_of_time() else "")
          + ("; refused" if refused else "")
          + (f"; request failures {dict(FAILS)}" if FAILS else "; no request failures")
          + (f"; still missing: {' '.join(gaps)}" if gaps else "; nothing missing"), flush=True)
    if ONLY:
        return
    # Left while data that was never downloaded is missing, so a partial first copy isn't published.
    if gaps:
        with open(MARKER, "w") as f:
            f.write(" ".join(gaps) + "\n")
    elif os.path.exists(MARKER):
        os.remove(MARKER)


if __name__ == "__main__":
    main()
