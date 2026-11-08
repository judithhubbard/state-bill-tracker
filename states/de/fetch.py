#!/usr/bin/env python3
"""Download Delaware's bills from legis.delaware.gov: the JSON endpoints its own pages call (undocumented; Kendo grid
reads, POSTed as forms, answering {"Data": [...], "Total": N}) and, for what only the pages show, the pages themselves.
legis.delaware.gov has no robots.txt (the address redirects to its "not found" page), so nothing is barred; one
request at a time, at most one a second (counted from the start of the last request). Bill texts and session laws (PDFs,
/json/BillDetail/GetPdfDocument) aren't read.

Delaware's General Assemblies run two years (the 153rd is 2025-2026); each goes in data/de/<first year>/ (from
FIRST_GA on, and the next one once it has bills: the site lists the 154th from the November election):
- list.json: every bill and every substitute bill (the bill list, POST /json/AllLegislation/GetAllLegislation with
  selectedGA and selectedLegislationTypeId 1 or 6, twenty rows a page whatever pageSize asks): id, number, display code
  ("HB 445 w/ HA 1 + SA 3": the amendments adopted; "-HA 1" one that failed or was stricken), the substituted bill
  ("HS 1 for HB 457"; substitutes for resolutions are left out), short and long titles,
  the synopsis (what the bill does, written with it), primary sponsor (SponsorPersonId), status and its date ("/Date(ms)/"),
  chamber of origin (ChamberId: 1 Senate, 2 House). Resolutions, concurrent and joint resolutions and amendments are left
  out. Delaware's constitutional amendments are bills ("AN ACT PROPOSING AN AMENDMENT TO ARTICLE V OF THE DELAWARE
  CONSTITUTION ...", then "AN ACT CONCURRING IN A PROPOSED AMENDMENT ..." in the next Assembly): they pass two General Assemblies by two-thirds, never go to the governor and
  never go to the voters; flagged "constitutional" in the bill's file. A bill replaced by a substitute stays listed
  (status "Substituted").
- bills/<HB500>.json (a substitute: <HS1-HB457>.json): the list row; the bill page (/BillDetail?LegislationId=...): the
  status line ("Signed 7/6/26 (7/6/2026 Line-Item Veto - See Governor's Advisory #46)"), primary, additional and
  co-sponsors (each with "Sen."/"Reps." house and a link: /LegislatorDetail?personId=N or a caucus page), the
  original synopsis, Volume:Chapter of the Laws of Delaware ("85:341"; a law), the governor's advisory number, fiscal
  note or fee impact ("Not Required", "Fiscal Note" ...), effective and sunset dates, text and session-law links; the
  action history (GetRecentReportsByLegislationId: "Passed By House. Votes: 39 YES 1 NO 1 ABSENT", "Signed by
  Governor", "Vetoed by Governor"; dates "6/25/26"); the committee reports (GetCommitteeReportsByLegislationId: the
  committee, members, and how many signed favorable, on its merits and unfavorable: committee votes are these counts,
  with no names); the roll call list (GetVotingReportsByLegislationId).
- votes/<RollCallId>.json: each roll call member by member (POST /json/RollCall/GetRollCallVoteByRollCallId): the
  members' short names ("K. Johnson", as the sponsor lists write them) and votes (Y, N, A absent, NV not voting, C
  conflict, V vacant) with the totals and the vote required ("3/4", "Majority"). Read once: a roll call doesn't change.
  Only floor votes have roll calls.
- members.json: every member who served in the Assembly (GetFullLegislatorList: 65 in the 153rd for 62 seats), with
  person id, chamber, district, party, short name and leadership role.
- committees.json: the Senate, House and joint committees (GetCommitteesByTypeId) with chair and vice chair, and for
  Senate and House committees their members from the committee page (/CommitteeDetail?committeeId=...; ids are per
  Assembly). Joint committees have no page.
- data/de/people.json: each member's page (/LegislatorDetail?personId=N, which redirects to the member's latest
  Assembly): heading ("Former Representative ..."), district, Legislative Hall address, phones ("Leghall Phone"), email
  and years of service; for the members of the newest two Assemblies, again weekly while one is live.
- state.json: what's been read (each bill's status and status date when last read; the day its page was read).
An Assembly is live from its first January to the January after it ends (the governor's last actions and chapter
numbers come after the last session day, June 30). A live Assembly's list (about 50 pages), members and committees
are read every run, and a bill again when its status, status date or display code changed, or every REREAD_DAYS. A
finished Assembly is read once and marked "finished".

Each bill takes four requests (page, actions, committee reports, roll call list) plus one per roll call: a first copy
of two Assemblies (about 1,950 bills and substitutes) takes several hours, so GitHub's runs build it up, each resuming
where the last stopped: every Assembly's list, members and committees and the members' pages first, then the bills,
newest Assembly first. data/de/incomplete lists what was never downloaded (a list, members,
committees, a listed bill, a roll call); it is removed once nothing is missing. A failed request where a last copy
exists keeps that copy and doesn't mark the download incomplete.
Usage: python3 states/de/fetch.py [assembly]   (default: every Assembly from FIRST_GA; one Assembly leaves the marker alone)
"""
import gzip, html, json, os, re, sys, time, urllib.error, urllib.parse, urllib.request
from collections import Counter
from datetime import date, timedelta

SITE = "https://legis.delaware.gov"
DATA = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "de"))
AGENT = "statebilltracker.org (a nonprofit bill tracker; contact via github.com/judithhubbard)"
TODAY = date.today()
ONLY = int(sys.argv[1]) if len(sys.argv) > 1 else None
FIRST_GA = 152  # 2023-2024
DELAY = 1  # no robots.txt; a second apart
REREAD_DAYS = 28
PEOPLE_DAYS = 7
TYPES = {1: "bill", 6: "substitute"}  # the list's legislation types kept (2 resolution, 3 concurrent, 4 joint, 5 amendment)
COMMITTEE_TYPES = {1: "Senate", 2: "House", 3: "Joint"}
# "AN ACT PROPOSING AN AMENDMENT TO ARTICLE V OF THE DELAWARE CONSTITUTION ...", and in the second Assembly "AN ACT
# CONCURRING IN A PROPOSED AMENDMENT TO ..." (not an act about the procedure for amendments: HB 321 of 2025)
AMENDMENT = re.compile(r"^\W*AN ACT (PROPOSING|CONCURRING IN)\b.{0,60}\bAMENDMENTS?\b.{0,160}CONSTITUTION", re.I | re.S)
MARKER = os.path.join(DATA, "incomplete")

# The run's own time limit (FETCH_MINUTES, set by the workflow): stop a few minutes early, with everything read so far
# saved and a summary printed, rather than be cut off silently mid-request.
START = time.time()
BUDGET = max(0.0, float(os.environ.get("FETCH_MINUTES") or 0) - 5) * 60
FAILS = Counter()  # why requests failed, for the summary
STATS = {"requests": 0}
LAST = [0.0]  # when the last request started


class Refused(Exception):
    """The server turned us away (401/403/429, or a page that isn't what was asked for): stop the run."""


def out_of_time():
    return BUDGET and time.time() - START > BUDGET


def first_year(ga):
    return 2025 + 2 * (ga - 153)


def current_ga():
    """The Assembly the calendar is in; from November of an even year (the election) the next one has begun."""
    ga = 153 + (TODAY.year - 2025) // 2
    if TODAY.year % 2 == 0 and TODAY.month >= 11:
        ga += 1
    return ga


def live(ga):
    """Read again every run: from its first January to the January after its second year."""
    y = first_year(ga)
    return y <= TODAY.year <= y + 1 or (TODAY.year == y + 2 and TODAY.month == 1) or ga >= current_ga()


def request(path, label, form=None, kind="json"):
    """The answer at SITE + path (POSTing form when given): parsed JSON, or the page's text for kind "html"; None after
    three tries, and at once when the site answers with its "not found" page; "" for an empty answer. Raises Refused on 401/403/429, or when a
    JSON address answers with something else (a challenge page)."""
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
        headers = {"User-Agent": AGENT, "Accept-Encoding": "gzip",
                   "Accept": "application/json" if kind == "json" else "text/html"}
        data = None
        if form is not None:
            data = urllib.parse.urlencode(form).encode()
            headers["Content-Type"] = "application/x-www-form-urlencoded; charset=UTF-8"
            headers["X-Requested-With"] = "XMLHttpRequest"
        try:
            req = urllib.request.Request(SITE + path, data=data, headers=headers, method="POST" if data else "GET")
            with urllib.request.urlopen(req, timeout=120) as r:
                raw = r.read()
                final = r.geturl()
                type_ = r.headers.get("Content-Type") or ""
                if r.headers.get("Content-Encoding") == "gzip":
                    raw = gzip.decompress(raw)
            if "/404" in urllib.parse.urlparse(final).path:
                FAILS["not found"] += 1
                return None
            if kind == "html":
                return raw.decode("utf-8", "replace")
            if not raw.strip():
                return ""  # a grid with no rows answers an empty text/html body
            if "json" not in type_:
                raise Refused(f"{label}: answered {type_ or 'no type'}, not JSON (a challenge page?)")
            return json.loads(raw)
        except Refused:
            raise
        except urllib.error.HTTPError as e:
            FAILS[f"HTTP {e.code}"] += 1
            if e.code in (401, 403, 429):
                raise Refused(f"{label}: HTTP {e.code}")
            if e.code == 404:
                return None
        except Exception as e:
            FAILS[type(e).__name__] += 1
        time.sleep(10 * (attempt + 1))
    print(f"{label}: failed three times", flush=True)
    return None


def grid(path, label, form=None):
    """Every row of a Kendo grid read, page after page (the site sends twenty rows a page): a list, or None."""
    rows, page = [], 1
    while True:
        d = request(path, f"{label} p{page}", {"sort": "", "page": page, "pageSize": 100, "group": "", "filter": "",
                                              **(form or {})})
        if d == "" and page == 1:
            return []
        if not isinstance(d, dict) or not isinstance(d.get("Data"), list) or d.get("Errors"):
            return None
        rows += d["Data"]
        if not d["Data"] or len(rows) >= (d.get("Total") or 0):
            return rows
        page += 1


def save(obj, path):
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(obj, f, ensure_ascii=False)
    os.replace(tmp, path)


def load(path, default=None):
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def text(fragment):
    """A piece of HTML as plain text, whitespace collapsed."""
    fragment = re.sub(r"<br\s*/?>", " ", fragment)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", fragment))).replace(" ,", ",").strip()


def links(fragment):
    return [{"href": html.unescape(h), "text": text(t)}
            for h, t in re.findall(r"<a\b[^>]*?href=[\"']([^\"']*)[\"'][^>]*>(.*?)</a>", fragment, re.S)]


def key_of(row):
    """"HB 445 w/ HA 1 + SA 3" -> "HB445"; "HS 1 for HB 457 -HA 1" (a substitute; "-HA 1" an amendment that failed or
    was stricken) -> "HS1-HB457"."""
    k = re.sub(r"\s+", "", row.get("LegislationNumber") or "")
    parent = row.get("SubstituteParentLegislationDisplayCode")
    return f"{k}-{re.sub(r'[^A-Z0-9]', '', parent.upper())}" if row.get("LegislationTypeId") == 6 and parent else k


def wanted(row):
    """Bills, and substitutes for bills (not "HS 1 for HR 12", a resolution's)."""
    if row.get("LegislationTypeId") == 6:
        return bool(re.match(r"\s*[HS]B\s*\d+\s*$", row.get("SubstituteParentLegislationDisplayCode") or ""))
    return row.get("LegislationTypeId") == 1


def groups(page, label_class="info-label"):
    """The page's label/value pairs (<div class="info-group"><label class="info-label">X:</label><div class="info-value">
    ...): [(label, value HTML)], the value running to the next group or the end of its section."""
    out = []
    for chunk in re.split(r'<div class="info-group">', page)[1:]:
        m = re.match(rf'\s*<label class="{label_class}">(.*?)</label>(.*)', chunk, re.S)
        if not m:
            continue
        value = re.split(r"</section>", m.group(2))[0]
        value = re.sub(r'<div class="popupWarning">.*?</div>', "", value, flags=re.S)
        label = re.sub(r"\stitle=(\"[^\"]*\"|'[^']*')", "", m.group(1))  # tooltips hold HTML ("<i>Laws of Delaware</i>")
        out.append((text(label).rstrip(":"), value))
    return out


def people_in(value):
    """A sponsor list: [{"name", "house" ("S"/"H" from the "Sen."/"Reps." before it, None for the primary sponsor),
    "personId" (when the link is /LegislatorDetail), "href"}]."""
    out, house = [], None
    for m in re.finditer(r"<span>\s*(Sen|Reps?)\.\s*</span>|<a\b[^>]*?href=[\"']([^\"']*)[\"'][^>]*>(.*?)</a>", value, re.S):
        if m.group(1):
            house = "S" if m.group(1) == "Sen" else "H"
            continue
        href = html.unescape(m.group(2))
        pid = re.search(r"personId=(\d+)", href, re.I)
        out.append({"name": text(m.group(3)), "house": house, "personId": int(pid.group(1)) if pid else None, "href": href})
    return out


def bill_page(page):
    """What the bill page shows beyond the list: {"heading", "assembly", "fields": {label: text}, "sponsors": {...},
    "links": {label: [links]}, "tips": {label: [tooltip texts]}}."""
    h2 = re.search(r"<h2>(.*?)</h2>\s*<h5>(.*?)</h5>", page, re.S)
    out = {"heading": text(h2.group(1)) if h2 else None, "assembly": text(h2.group(2)) if h2 else None,
           "fields": {}, "sponsors": {}, "links": {}, "tips": {}}
    names = {"Primary Sponsor": "primary", "Additional Sponsor(s)": "additional", "Co-Sponsor(s)": "cosponsors"}
    for label, value in groups(page):
        if label in names:
            out["sponsors"][names[label]] = people_in(value)
            continue
        out["fields"][label] = text(value)
        ls = [l for l in links(value) if not l["href"].startswith("#")]
        if ls:
            out["links"][label] = ls
        tips = [html.unescape(t) for t in re.findall(r"<span data-toggle='tooltip'[^>]*title='([^']*)'", value)]
        if tips:
            out["tips"][label] = tips
    return out


def bill_record(ga, row, folder):
    """A bill's page, actions, committee reports and roll call list into bills/<key>.json, and its roll calls not yet
    read into votes/; False when a part failed (the last copy, if any, stays)."""
    k, lid = key_of(row), row["LegislationId"]
    page = request(f"/BillDetail?LegislationId={lid}", f"{ga} {k} page", kind="html")
    detail = bill_page(page) if page else None
    if detail is not None and not detail["heading"]:
        FAILS["page without a heading"] += 1
        detail = None
    form = {"legislationId": lid}
    actions = grid(f"/json/BillDetail/GetRecentReportsByLegislationId?legislationId={lid}", f"{ga} {k} actions", form)
    reports = grid(f"/json/BillDetail/GetCommitteeReportsByLegislationId?legislationId={lid}", f"{ga} {k} committee reports", form)
    rolls = grid(f"/json/BillDetail/GetVotingReportsByLegislationId?legislationId={lid}", f"{ga} {k} roll calls", form)
    for r in reports or []:
        r.pop("LongTitle", None)  # the bill's own, again
        r.pop("Synopsis", None)
    if None in (detail, actions, reports, rolls):
        return False
    record = {"key": k, "id": lid, "assembly": ga, "read": TODAY.isoformat(), "list": row,
              "constitutional": bool(AMENDMENT.search(row.get("LongTitle") or "")),
              "detail": detail, "actions": actions, "committeeReports": reports, "rollCalls": rolls}
    os.makedirs(os.path.join(folder, "bills"), exist_ok=True)
    save(record, os.path.join(folder, "bills", f"{k}.json"))
    return roll_calls(ga, k, rolls, folder)


def roll_calls(ga, k, rolls, folder):
    """Each roll call not yet on disk; False when one failed."""
    ok = True
    os.makedirs(os.path.join(folder, "votes"), exist_ok=True)
    for r in rolls:
        rid = r.get("RollCallId")
        path = os.path.join(folder, "votes", f"{rid}.json")
        if not rid or os.path.exists(path):
            continue
        if out_of_time():
            return False
        d = request("/json/RollCall/GetRollCallVoteByRollCallId", f"{ga} {k} roll call {rid}", {"rollCallId": rid})
        if not isinstance(d, dict) or not d.get("Success") or not isinstance(d.get("Model"), dict):
            ok = False
            continue
        save(d["Model"], path)
    return ok


def read_list(ga, folder):
    """Every bill and substitute of the Assembly, into list.json; the last copy when a page fails."""
    rows = []
    for t in TYPES:
        got = grid("/json/AllLegislation/GetAllLegislation", f"{ga} {TYPES[t]} list",
                   {"selectedGA[0]": ga, "selectedLegislationTypeId[0]": t, "coSponsorCheck": "false"})
        if got is None:
            print(f"{ga} list: unreadable; kept the last copy", flush=True)
            return load(os.path.join(folder, "list.json"))
        rows += [r for r in got if wanted(r)]
    save(rows, os.path.join(folder, "list.json"))
    print(f"{ga} list: {sum(1 for r in rows if r.get('LegislationTypeId') == 1)} bills, "
          f"{sum(1 for r in rows if r.get('LegislationTypeId') == 6)} substitutes", flush=True)
    return rows


def roster(ga, folder):
    """members.json and committees.json (with each Senate and House committee's members from its page)."""
    path = os.path.join(folder, "members.json")
    m = request("/json/Search/GetFullLegislatorList", f"{ga} members", {"selectedGAs[0]": ga})
    if isinstance(m, dict) and isinstance(m.get("Data"), list) and m["Data"]:
        save(m["Data"], path)
        print(f"{ga} members: {len(m['Data'])}", flush=True)
    else:
        print(f"{ga} members: unreadable or none yet; kept the last copy", flush=True)
    path = os.path.join(folder, "committees.json")
    last = {c.get("CommitteeId"): c for c in load(path, []) or []}
    out = []
    for t, house in COMMITTEE_TYPES.items():
        rows = grid("/json/Committees/GetCommitteesByTypeId?ga=", f"{ga} {house} committees",
                    {"assemblyId": ga, "committeeTypeId": t})
        if rows is None:
            print(f"{ga} committees: unreadable; kept the last copy", flush=True)
            return
        for c in rows:
            if t != 3:  # joint committees have no page
                page = request(f"/CommitteeDetail?committeeId={c['CommitteeId']}", f"{ga} committee {c['CommitteeId']}",
                               kind="html")
                if page:
                    c["members"] = {label: people_in(value) for label, value in groups(page, "info-label-sm")}
                elif "members" in (last.get(c["CommitteeId"]) or {}):
                    c["members"] = last[c["CommitteeId"]]["members"]
            out.append(c)
    if out:
        save(out, path)
        print(f"{ga} committees: {len(out)}", flush=True)


def person_page(page):
    h2 = re.search(r"<h2>(.*?)</h2>\s*<h5>(.*?)</h5>", page, re.S)
    block = page.split("assembly-member__contact", 1)[-1].split('<h3 class="section-head">', 1)[0]
    service = re.search(r'Legislative Service</h3>(.*?)</section>', page, re.S)
    address = re.search(r'<label class="sr-only">Address</label>(.*?)</div>\s*</div>', block, re.S)
    office = re.search(r'<h6 class="info-value">(.*?)</h6>', block, re.S)
    return {"heading": text(h2.group(1)) if h2 else None, "district": text(h2.group(2)) if h2 else None,
            "office": text(office.group(1)) if office else None,
            "address": text(address.group(1)) if address else None,
            "phones": [{"label": text(a), "number": text(b)}
                       for a, b in re.findall(r"<span>([^<]*?):\s*</span>\s*<span>([^<]*)</span>", block)],
            "emails": sorted(set(re.findall(r"mailto:([^\"'?]+)", block))),
            "service": [text(p) for p in re.findall(r"<p>(.*?)</p>", service.group(1), re.S)] if service else []}


def people(gas):
    """data/de/people.json: each member's page, for the members of the newest two Assemblies; again weekly while one is
    live. A page that fails keeps the last copy."""
    path = os.path.join(DATA, "people.json")
    have = load(path, {})
    stale = (TODAY - timedelta(days=PEOPLE_DAYS)).isoformat()
    ids = set()
    for ga in sorted(gas)[-2:]:
        for m in load(os.path.join(DATA, str(first_year(ga)), "members.json"), []) or []:
            if m.get("PersonId"):
                ids.add(m["PersonId"])
    got = 0
    for pid in sorted(ids):
        p = have.get(str(pid))
        if p and (p.get("read", "") >= stale or not any(live(g) for g in gas)):
            continue
        if out_of_time():
            break
        page = request(f"/LegislatorDetail?personId={pid}", f"person {pid}", kind="html")
        if not page or "<h2>" not in page:
            continue
        have[str(pid)] = {"personId": pid, "read": TODAY.isoformat(), **person_page(page)}
        got += 1
        if got % 20 == 0:
            save(have, path)
    save(have, path)
    print(f"people: {got} pages read, {len(have)} on file", flush=True)


def signature(row):
    return [row.get("StatusName"), row.get("LegislationStatusDateTime"), row.get("LegislationDisplayCode")]


def assembly_lists(ga):
    """An Assembly's list, members and committees (when never read, and every run while it's live)."""
    folder = os.path.join(DATA, str(first_year(ga)))
    if load(os.path.join(folder, "state.json"), {}).get("finished"):
        print(f"{ga}: finished and fully read; nothing to do", flush=True)
        return
    if out_of_time():
        return
    os.makedirs(folder, exist_ok=True)
    if not os.path.exists(os.path.join(folder, "list.json")) or live(ga):
        read_list(ga, folder)
    if not os.path.exists(os.path.join(folder, "members.json")) or live(ga):
        roster(ga, folder)


def assembly(ga):
    """An Assembly's bills that are new, changed or due, after every Assembly's lists and the members' pages; a finished
    Assembly is marked so once everything is read."""
    folder = os.path.join(DATA, str(first_year(ga)))
    state_path = os.path.join(folder, "state.json")
    state = load(state_path, {})
    rows = load(os.path.join(folder, "list.json"))
    if state.get("finished") or rows is None or out_of_time():
        return
    is_live = live(ga)
    seen = state.setdefault("bills", {})  # key -> {"sig": [...], "read": day}
    due = (TODAY - timedelta(days=REREAD_DAYS)).isoformat()
    work = []
    for row in rows:
        k = key_of(row)
        s = seen.get(k)
        if not s or not os.path.exists(os.path.join(folder, "bills", f"{k}.json")):
            work.append((0, row))
        elif is_live and (s.get("sig") != signature(row) or s.get("read", "") < due):
            work.append((1 if s.get("sig") != signature(row) else 2, row))
    work.sort(key=lambda w: w[0])  # never read first, then changed, then due
    got = failed = 0
    for _, row in work:
        if out_of_time():
            break
        k = key_of(row)
        if bill_record(ga, row, folder):
            seen[k] = {"sig": signature(row), "read": TODAY.isoformat()}
            got += 1
        elif not out_of_time():  # (a bill cut off by the time limit isn't a failure)
            failed += 1
        if (got + failed) % 25 == 0:
            save(state, state_path)
    # Roll calls a bill listed but that failed to load (the bill's record was saved without them)
    for k in list(seen):
        if out_of_time():
            break
        b = load(os.path.join(folder, "bills", f"{k}.json"))
        if b and any(not os.path.exists(os.path.join(folder, "votes", f"{r.get('RollCallId')}.json")) for r in b["rollCalls"]):
            roll_calls(ga, k, b["rollCalls"], folder)
    save(state, state_path)
    print(f"{ga}: {got} of {len(work)} bills read" + (f", {failed} failed" if failed else "")
          + f"; {len(rows)} listed", flush=True)
    if not is_live and not missing(ga) and not out_of_time():
        state["finished"] = True
        save(state, state_path)
        print(f"{ga}: finished", flush=True)
    return True


def missing(ga):
    """What of an Assembly was never downloaded (a failed re-read with a last copy doesn't count)."""
    folder = os.path.join(DATA, str(first_year(ga)))
    if load(os.path.join(folder, "state.json"), {}).get("finished"):
        return []
    rows = load(os.path.join(folder, "list.json"))
    if rows is None:
        return [f"{ga}:list"]
    out = []
    if rows:
        out += [f"{ga}:{n}" for n in ("members", "committees") if not os.path.exists(os.path.join(folder, f"{n}.json"))]
    no_bill = no_vote = 0
    for row in rows:
        b = load(os.path.join(folder, "bills", f"{key_of(row)}.json"))
        if not b:
            no_bill += 1
            continue
        no_vote += sum(not os.path.exists(os.path.join(folder, "votes", f"{r.get('RollCallId')}.json")) for r in b["rollCalls"])
    if no_bill:
        out.append(f"{ga}:bills({no_bill})")
    if no_vote:
        out.append(f"{ga}:rollcalls({no_vote})")
    return out


def main():
    os.makedirs(DATA, exist_ok=True)
    # Before the first copy, a run cut off without its summary leaves this, so a partial copy isn't published.
    if not ONLY and not any(name.isdigit() for name in os.listdir(DATA)):
        with open(MARKER, "w") as f:
            f.write("running\n")
    gas = [ga for ga in range(current_ga(), FIRST_GA - 1, -1) if not ONLY or ga == ONLY]  # the newest first
    refused = False
    try:
        for ga in gas:
            assembly_lists(ga)
        people([ga for ga in gas if os.path.exists(os.path.join(DATA, str(first_year(ga)), "members.json"))])
        for ga in gas:
            assembly(ga)
    except Refused as e:
        print(f"Stopped: the server refused a request ({e})", flush=True)
        refused = True
    gaps = [g for ga in gas for g in missing(ga)]
    if not os.path.exists(os.path.join(DATA, "people.json")):
        gaps.append("people")
    print(f"run: {STATS['requests']} requests, {round((time.time() - START) / 60)} min"
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
