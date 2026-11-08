#!/usr/bin/env python3
"""Download Alaska's bills from the Legislature's BASIS public service (https://www.akleg.gov/publicservice/basis/;
documented in https://www.akleg.gov/basis/BasisPublicServiceAPI.pdf, tried out at https://www.akleg.gov/apptester.html).
akleg.gov's robots.txt allows /publicservice/ and /basis/get_documents.asp to all user agents (it bars AI-training
crawlers, and /PDF/ — the bill texts and fiscal notes — which are not read).

Every request is a GET to /publicservice/basis/<section>?session=<N>&json=true with the header
"X-Alaska-Legislature-Basis-Version: 1.4" and the query in "X-Alaska-Legislature-Basis-Query" ("Bills;bill=HB*,Actions,
Votes"); "X-Alaska-Query-ResultRange: 0..9" pages a result (first item 0, both ends included). An error answers 200
with {"Basis":{"Error":{...},}} (not valid JSON: the trailing comma).

Alaska's Legislatures run two years (the 34th is 2025-2026); each goes in data/ak/<first year>/:
- sessions.json: the Legislature's regular and special sessions with their dates.
- list.json: every bill and resolution with its status (number, short title, status text and date). Its Vetoed and
  PartialVeto flags are always false: only a bill's own record has them.
- bills/<HB57>.json: each House and Senate bill, and each joint resolution proposing an amendment to the state
  constitution (full title "Proposing amendments to the Constitution of the State of Alaska ..."; other joint resolutions
  are left out): titles, sponsors in order with member codes, referrals, subjects, versions, fiscal notes, the action
  history (journal date, house, action code; with CommitteeActions also each committee hearing: "Heard & Held",
  "Moved CSHB 57(L&C) Out of Committee", "Scheduled but Not Heard", with the committee as its Chamber, "HL&C",
  and code T, or M for the minutes) and every floor roll call member by member (Votes). The
  service has no committee roll calls: a committee's report is an action ("DP: names", "NR: names").
- statements/<HB57>.pdf: the sponsor statement (the bill's SponsorUrl, /basis/get_documents.asp), when there is one,
  read once per document id, five seconds apart, after every Legislature's bills (the documents server answered 429 to
  requests a second apart). It is the only plain-language account of what a bill does.
- members.json (with committee memberships; leadership is the member's Comment), committees.json (members with
  positions: C0 chair, C1/C2 co-chairs, V1 vice chair), and for the current Legislature meetings.json (the next
  three weeks).

A finished Legislature is read once. In the current one, a bill is read again when its status text or date in the list
changes, when it has an action dated from two weeks before the last run on (the service's Actions;startdate=
constraint, one request), and every bill every four weeks. Each bill is its own request (about 2 seconds): a page of
several bills leaves out the full title. A first copy of two Legislatures takes about 1.5
hours. One request at a time, a second apart.
Usage: python3 states/ak/fetch.py [legislature]   (default: the current Legislature and the one before)
"""
import gzip, json, os, re, sys, time, urllib.error, urllib.request
from collections import Counter
from datetime import date, timedelta

API = "https://www.akleg.gov/publicservice/basis/"
SITE = "https://www.akleg.gov"
DATA = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "ak"))
AGENT = "statebilltracker.org (a nonprofit bill tracker; contact via github.com/judithhubbard)"
TODAY = date.today()
CURRENT = 34 + (TODAY.year - 2025) // 2  # the 34th Legislature is 2025-2026
KINDS = ("HB", "SB", "HJR", "SJR")
DETAIL = "Sponsors,Actions,CommitteeActions,Subjects,Versions;Fulltext=Urlonly,Fiscalnotes,Votes,Referrals"
AMENDMENT = re.compile(r"proposing (an )?amendments? to the constitution of the state of alaska", re.I)

# The run's own time limit (FETCH_MINUTES, set by the workflow): stop a few minutes early, with everything read so far
# saved and a summary printed, rather than be cut off silently mid-request.
START = time.time()
BUDGET = max(0.0, float(os.environ.get("FETCH_MINUTES") or 0) - 5) * 60
FAILS = Counter()  # why requests failed, for the summary
STATS = {"requests": 0}


class Refused(Exception):
    """The server turned us away (401/403/429): stop the run."""


def out_of_time():
    return BUDGET and time.time() - START > BUDGET


def first_year(legislature):
    return 2025 + 2 * (legislature - 34)


def request(url, headers, label, pause=1):
    """GET url; the body, or None after three tries. Refused on 401/403/429; 404 is None at once."""
    for attempt in range(3):
        if out_of_time():
            return None
        time.sleep(pause)
        STATS["requests"] += 1
        if STATS["requests"] % 100 == 0:
            print(f"  {STATS['requests']} requests, {round((time.time() - START) / 60)} min"
                  + (f"; failures {dict(FAILS)}" if FAILS else ""), flush=True)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": AGENT, "Accept-Encoding": "gzip", **headers})
            with urllib.request.urlopen(req, timeout=30) as r:
                body = r.read()
                if r.headers.get("Content-Encoding") == "gzip":
                    body = gzip.decompress(body)
                return body
        except urllib.error.HTTPError as e:
            FAILS[f"HTTP {e.code}"] += 1
            if e.code in (401, 403, 429):
                raise Refused(f"{label}: HTTP {e.code}")
            if e.code == 404:
                return None
        except Exception as e:
            FAILS[type(e).__name__] += 1
        time.sleep(5 * (attempt + 1))
    print(f"{label}: failed three times", flush=True)
    return None


def basis(section, legislature, query="", rng=None):
    """One BASIS answer's "Basis" object, or None (failed, or an Error answer)."""
    headers = {"X-Alaska-Legislature-Basis-Version": "1.4", "X-Alaska-Legislature-Basis-Query": query}
    if rng:
        headers["X-Alaska-Query-ResultRange"] = rng
    label = f"{legislature} {section} [{query[:60]}]" + (f" {rng}" if rng else "")
    body = request(f"{API}{section}?session={legislature}&json=true", headers, label)
    if body is None:
        return None
    try:
        d = json.loads(body)["Basis"]
    except (ValueError, KeyError, TypeError):
        FAILS["unreadable"] += 1
        print(f"{label}: unreadable answer: {body[:200]!r}", flush=True)
        return None
    if isinstance(d, dict) and d.get("Error"):
        FAILS["error answer"] += 1
        print(f"{label}: {d['Error']}", flush=True)
        return None
    return d


def save(obj, path):
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(obj, f, ensure_ascii=False)
    os.replace(tmp, path)


def load(path, default):
    try:
        return json.load(open(path))
    except (OSError, ValueError):
        return default


def key(number):
    """"HB  57" -> "HB57"."""
    return re.sub(r"\s+", "", number or "")


def kind(number):
    m = re.match(r"[A-Z]+", key(number))
    return m.group() if m else ""


def keep(bill, folder, state):
    """Save a bill's record (a joint resolution only when it proposes a constitutional amendment). True if saved."""
    k = key(bill.get("BillNumber"))
    path = os.path.join(folder, "bills", f"{k}.json")
    if kind(k) in ("HJR", "SJR"):
        amends = bool(AMENDMENT.search(bill.get("FullTitle") or ""))
        state["resolutions"][k] = amends
        if not amends:
            if os.path.exists(path):
                os.remove(path)
            return False
    save(bill, path)
    return True


def read_bills(legislature, folder, state, todo, listed):
    """Read the bills in todo (keys), one request each; returns how many were read. (A page of several bills,
    "Bills;bill=HB*" with a ResultRange, leaves out each bill's FullTitle and meetings.)"""
    got = 0
    for k in sorted(todo):
        if out_of_time():
            break
        number = state["numbers"].get(k) or k
        d = basis("bills", legislature, f"Bills;bill={number},{DETAIL}")
        page = (d or {}).get("Bills") or []
        b = next((x for x in page if key(x.get("BillNumber")) == k), None)
        if b:
            keep(b, folder, state)
            state["status"][k] = listed.get(k, "")
            got += 1
            if got % 25 == 0:
                save(state, os.path.join(folder, "state.json"))
    save(state, os.path.join(folder, "state.json"))
    return got


def statements(legislature, folder, state):
    """Each saved bill's sponsor statement (a PDF), once per document id. Returns how many are still missing."""
    out = os.path.join(folder, "statements")
    os.makedirs(out, exist_ok=True)
    have = state.setdefault("statements", {})
    todo = []
    for name in sorted(os.listdir(os.path.join(folder, "bills"))):
        b = load(os.path.join(folder, "bills", name), {})
        url = b.get("SponsorUrl") or ""
        m = re.search(r"docid=(\d+)", url)
        k = name[:-5]
        if m and (have.get(k) != m.group(1) or not os.path.exists(os.path.join(out, f"{k}.pdf"))):
            todo.append((k, m.group(1)))
    got = 0
    for k, docid in todo:
        if out_of_time():
            break
        # The documents server answered 429 after about 250 documents a second apart: five seconds apart.
        body = request(f"{SITE}/basis/get_documents.asp?session={legislature}&docid={docid}", {}, f"{legislature} statement {k}", 5)
        if body and body.startswith(b"%PDF"):
            open(os.path.join(out, f"{k}.pdf"), "wb").write(body)
            have[k] = docid
            got += 1
            if got % 25 == 0:
                save(state, os.path.join(folder, "state.json"))
        elif body is not None:
            FAILS["statement not a PDF"] += 1
    save(state, os.path.join(folder, "state.json"))
    print(f"{legislature} sponsor statements: {got} of {len(todo)} read", flush=True)
    return len(todo) - got


def roster(legislature, folder, current):
    """Members (with committee memberships) and committees (with members); for the current Legislature also the next
    three weeks' meetings. Returns problems."""
    problems = []
    for section, query, name, field in (("members", "Members,Committees", "members", "Members"),
                                        ("committees", "Committees,Members", "committees", "Committees")):
        path = os.path.join(folder, f"{name}.json")
        if not current and os.path.exists(path):
            continue
        d = basis(section, legislature, query)
        rows = (d or {}).get(field) or []
        if not rows:
            print(f"{legislature} {name}: unreadable; kept the last copy", flush=True)
            problems.append(f"{legislature}:{name}")
            continue
        save(rows, path)
        print(f"{legislature} {name}: {len(rows)}", flush=True)
    if current:
        end = TODAY + timedelta(days=21)
        d = basis("meetings", legislature, f"Meetings;startdate={TODAY:%Y-%m-%d};enddate={end:%Y-%m-%d}")
        if d is not None:
            save(d.get("Meetings") or [], os.path.join(folder, "meetings.json"))
    return problems


def legislature_run(legislature):
    """One Legislature's sessions, roster, bills and sponsor statements. Returns problems."""
    current = legislature >= CURRENT
    folder = os.path.join(DATA, str(first_year(legislature)))
    os.makedirs(os.path.join(folder, "bills"), exist_ok=True)
    state_path = os.path.join(folder, "state.json")
    state = load(state_path, {})
    for field in ("status", "resolutions", "numbers"):
        state.setdefault(field, {})
    if state.get("finished") and not current:
        print(f"{legislature}: finished and fully read; nothing to do", flush=True)
        return []
    problems = []
    d = basis("sessions", legislature)
    if d and d.get("Session"):
        save(d["Session"], os.path.join(folder, "sessions.json"))
    problems += roster(legislature, folder, current)

    d = basis("bills", legislature)
    if d is None or not d.get("Bills"):
        print(f"{legislature}: no bill list; kept the last copies", flush=True)
        return problems + [f"{legislature}:list"]
    save(d["Bills"], os.path.join(folder, "list.json"))
    listed = {}
    for b in d["Bills"]:
        k = key(b.get("BillNumber"))
        if kind(k) in KINDS:
            listed[k] = f"{b.get('StatusDate')} {b.get('StatusText')}"
            state["numbers"][k] = b["BillNumber"]
    todo = set()
    for k, stamp in listed.items():
        is_resolution = kind(k) in ("HJR", "SJR")
        if is_resolution and state["resolutions"].get(k) is False:
            have = True  # checked: not an amendment
        else:
            have = os.path.exists(os.path.join(folder, "bills", f"{k}.json"))
        if not have or state["status"].get(k) != stamp:
            todo.add(k)
    if current:
        month_ago = (TODAY - timedelta(days=28)).isoformat()
        if (state.get("full") or "") < month_ago:
            todo = set(listed)
            print(f"{legislature}: reading every bill (every four weeks)", flush=True)
        elif state.get("since"):
            since = (date.fromisoformat(state["since"]) - timedelta(days=14)).isoformat()
            d = basis("bills", legislature, f"Actions;startdate={since}")
            if d is None:
                todo = set(listed)
            else:
                acted = {key(b.get("BillNumber")) for b in d.get("Bills") or []} & set(listed)
                print(f"{legislature}: {len(acted)} bills with actions since {since}", flush=True)
                todo |= acted
    got = read_bills(legislature, folder, state, todo, listed)
    print(f"{legislature} bills: {got} of {len(todo)} read ({len(listed)} bills and joint resolutions listed)", flush=True)
    if got == len(todo):
        state["since"] = TODAY.isoformat()
        if todo == set(listed):
            state["full"] = TODAY.isoformat()
    else:
        problems.append(f"{legislature}:bills")
    save(state, state_path)
    return problems


def statements_run(legislature, earlier_problems):
    """The sponsor statements, after every Legislature's bills; a finished Legislature is marked finished here."""
    current = legislature >= CURRENT
    folder = os.path.join(DATA, str(first_year(legislature)))
    state_path = os.path.join(folder, "state.json")
    state = load(state_path, {})
    if state.get("finished") or not os.path.isdir(os.path.join(folder, "bills")):
        return []
    if statements(legislature, folder, state):
        return [f"{legislature}:statements"]
    if not current and not any(p.startswith(f"{legislature}:") for p in earlier_problems):
        state["finished"] = True
        save(state, state_path)
    return []


def never_read(legislature):
    """What of a Legislature was never downloaded (its bill list, members, committees, a listed bill): what keeps the
    marker once the first copy is whole. A failed re-read keeps the last copy and doesn't count."""
    folder = os.path.join(DATA, str(first_year(legislature)))
    listed = load(os.path.join(folder, "list.json"), None)
    if listed is None:
        return [f"{legislature}:list"]
    out = [f"{legislature}:{n}" for n in ("members", "committees") if not os.path.exists(os.path.join(folder, f"{n}.json"))]
    resolutions = load(os.path.join(folder, "state.json"), {}).get("resolutions") or {}
    for b in listed:
        k = key(b.get("BillNumber"))
        if kind(k) in KINDS and resolutions.get(k) is not False and not os.path.exists(os.path.join(folder, "bills", f"{k}.json")):
            out.append(f"{legislature}:bills")
            break
    return out


def main():
    only = int(sys.argv[1]) if len(sys.argv) > 1 else None
    os.makedirs(DATA, exist_ok=True)
    marker = os.path.join(DATA, "incomplete")
    whole = not os.path.exists(marker)  # the last run left nothing missing
    # A run cut off by its time limit leaves this, so a partial copy isn't published (cleared after a clean run).
    if not only:
        open(marker, "w").write("running\n")
    problems = []
    try:
        for legislature in (CURRENT, CURRENT - 1):  # the current Legislature first
            if only and legislature != only:
                continue
            problems += legislature_run(legislature)
        for legislature in (CURRENT, CURRENT - 1):
            if only and legislature != only:
                continue
            problems += statements_run(legislature, problems)
    except Refused as e:
        print(f"Stopped: the server refused a request ({e})", flush=True)
        problems.append("refused")
    if out_of_time():
        problems.append("time")
    print(f"run: {STATS['requests']} requests, {round((time.time() - START) / 60)} min"
          + ("; stopped at the time limit" if out_of_time() else "")
          + (f"; request failures {dict(FAILS)}" if FAILS else "; no request failures"), flush=True)
    if only:
        return
    # Only data never downloaded keeps Alaska off the site; sponsor statements still to read hold it only while the
    # first copy is being built (a failed refresh keeps the last copy).
    gaps = [g for legislature in (CURRENT, CURRENT - 1) for g in never_read(legislature)]
    if not whole:
        gaps += [p for p in problems if p.endswith(":statements") or p in ("refused", "time")]
    if problems:
        print(f"problems this run: {' '.join(problems)}", flush=True)
    if gaps:
        open(marker, "w").write(" ".join(gaps) + "\n")
    elif os.path.exists(marker):
        os.remove(marker)


if __name__ == "__main__":
    main()
