#!/usr/bin/env python3
"""Download Montana's bills from the JSON API behind the Legislature's Bill Explorer (bills.legmt.gov). It's
undocumented: the addresses are the ones the site's own script calls (it calls https://bearbeta.legmt.gov; the same
service answers at https://api.legmt.gov, which is used here). api.legmt.gov's robots.txt is "User-agent: * /
Crawl-delay: 10" and nothing disallowed, so one request at a time, ten seconds apart (counted from the end of the last
answer). docs.legmt.gov (bill texts, fiscal notes, vote sheets: PDFs) has the same delay and isn't read.

Montana's Legislature meets in odd years only (2025 is the 69th Legislature's regular session). Sessions since the
69th are in the current system (bills/v1, legislators/v1, committees/v1; a session's id is small: 2025 is 2, 2027 is
3); earlier ones only in its archive (archive/v1; session ids like 20231), which holds less. Each session goes in
data/mt/<year>/ (from FIRST_YEAR on; the next session once it has numbered bills, prefiled from December):
- bills/<HB1>.json: each House and Senate bill and joint resolution (HB, SB, HJ, SJ; one house's resolutions, HR and
  SR, and bill drafts that were never introduced, "LC1374" without a bill type, are left out). Montana's constitutional
  amendments are bills ("An act submitting to the qualified electors ..."); joint resolutions are mostly study requests
  and letters, kept for now.
  Current system (POST bills/v1/bills/filter, a page of 100 of one bill type, sorted by number): the bill's id (the same
  as its draft's id, which the per-bill requests below take as billId), number, type, sponsorId, chapter
  (sessionLawChapterNumber), and its draft: LC number, short title, subjects (with each subject's majority needed),
  requester, fiscal and legal note flags, and the whole history (billStatuses), drafting steps included ("(LC) Draft in
  Edit"). Each step has a status code and name ("(H) 3rd Reading", "(S) Committee Executive Action", "Chapter Number
  Assigned"), a timestamp, a result ("BILL_PASSED", "BILL_CONCURRED_AS_AMENDED", "MOTION_FAILED"), the committee
  (standingCommitteeId) for hearings and committee votes, and for a floor vote its vote (id, motion "Do Pass",
  "AMD-HB0001.001.002 Caferro DO PASS"), but not how anyone voted. There is no summary of what a bill does: the short
  title is all.
  Archive (POST archive/v1/bills/search, {"sessionId": 20231, "billTypes": ["HB"], "sortBy": "billNumber"}, the page in
  "bills"): billActions newest first with plain-English descriptions ("(S) 3rd Reading Concurred"), the committee by
  code, and floor votes as tallies (yesVotes/noVotes as strings, voteSeq "S93") but no member votes; sponsors
  (primarySponsorBillRoles), co-sponsor, requesters and drafters by law-entity id (entityIdSequence, which the archive's
  legislator list uses); subjects. Each sponsor record repeats the sponsor's committee assignments, dropped here (they
  are in legislators.json).
  Both lists' "offset" parameter is a page number, not an item (offset=1&limit=100 is items 101-200).
- votes/<HB1>.json (current system only; GET bills/v1/votes/findByBillId?billId=<id>): every floor roll call on the
  bill, amendments included, each member's vote by legislator id (legislatorVotes: YES, NO, ...; no totals), with the
  history step it belongs to (billStatus.id). Read when a history step with a vote appears.
- committee/<HB1>.json (current system only; GET committees/v1/executiveActions/findByBillId?billId=<id>): every
  committee vote ("executive action": do_pass, be_concurred_in_as_amended, be_amended, reconsider_previous_action,
  tabled ...), each member's vote by legislator id (legislatorVotes[].membership.legislatorId), the meeting and
  committee, and the history step (billStatusId; none for amendment votes). Each meeting's committee member list and
  agenda are dropped (the members are in committees.json). Read when a history step "Committee Executive Action" appears.
- cosponsors.json (current system only): {"HB1": [legislator ids]}. The site asks billCosponsors/findByBillId one bill
  at a time; the bill filter also takes "cosponsorIds" (checked: legislator 99's 47 bills include HB 1, whose one
  co-sponsor is 99), so this asks once per legislator instead (about 160 requests, not 1,600), resuming where it left
  off, again weekly while the session is live.
- legislators.json: current system (POST legislators/v1/legislators/search, {"sessionIds": [2]}): every member who
  served (154 in 2025, members who left included, with start and end dates), with the id the votes and sponsors use,
  chamber, district, party, email; phoneNumber is always empty. Archive (archive/v1/legislators/findBySession): name,
  law-entity id, district number, party and committee assignments; no chamber (the committees' houseCode tells) and
  no email.
- committees.json: current system (committees/v1/standingCommittees/findBySessionId): each standing committee's id
  (the history's standingCommitteeId), code ("APH"), name ("(H) Appropriations"), meeting days, room and members with
  their position (CH chair, VC vice chair, ME member) and dates. Archive (archive/v1/committees/findBySession/<id>):
  codes and names, free conference committees included.
- state.json: what's been read (each bill's vote and committee-vote ids when last read; paging progress; the
  co-sponsor sweep). A finished session (not live, everything read) is marked "finished" and not asked again.
A session is live while the system marks it active, until it adjourns, and for LIVE_DAYS after (vetoes, override
polls by mail and chapter numbers come after adjournment). A live session's list is read again every run (about 17
pages, three minutes), and a bill's votes or committee votes again when its history shows a new one.

At ten seconds a request, a first copy of a session takes about 12 hours (1,641 bills in 2025: about 1,300 vote and
1,400 committee-vote requests, 17 list pages, about 160 co-sponsor pages), so GitHub's runs build it up over several
runs, each resuming where the last stopped. Each run reads every session's members, committees and list first, then
the per-bill requests, newest session first. data/mt/incomplete lists what was never downloaded (a session's list,
votes, committee votes, co-sponsors, members); it is removed once nothing is missing. A failed request where a last
copy exists keeps that copy and doesn't mark the download incomplete, and once a session's first copy is whole
("whole" in its state.json), votes, committee votes and co-sponsors still to read don't either.
Usage: python3 states/mt/fetch.py [year]   (default: every session from FIRST_YEAR; a single year leaves the marker alone)
"""
import gzip, json, os, sys, time, urllib.error, urllib.request
from collections import Counter
from datetime import date, timedelta

API = "https://api.legmt.gov"
DATA = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "mt"))
AGENT = "statebilltracker.org (a nonprofit bill tracker; contact via github.com/judithhubbard)"
TODAY = date.today()
ONLY = int(sys.argv[1]) if len(sys.argv) > 1 else None
FIRST_YEAR = 2023
DELAY = 10  # api.legmt.gov's robots.txt: Crawl-delay: 10
PAGE = 100
LIVE_DAYS = 120
COSPONSOR_DAYS = 7
TYPES = {"HB": 1, "SB": 4, "HJ": 3, "SJ": 6}  # the current system's bill type ids; HR and SR left out
MARKER = os.path.join(DATA, "incomplete")

# The run's own time limit (FETCH_MINUTES, set by the workflow): stop a few minutes early, with everything read so far
# saved and a summary printed, rather than be cut off silently mid-request.
START = time.time()
BUDGET = max(0.0, float(os.environ.get("FETCH_MINUTES") or 0) - 5) * 60
FAILS = Counter()  # why requests failed, for the summary
STATS = {"requests": 0}
LAST = [0.0]  # when the last answer ended


class Refused(Exception):
    """The server turned us away (401/403/429, or a page that isn't JSON): stop the run."""


def out_of_time():
    return BUDGET and time.time() - START > BUDGET


def request(url, label, body=None):
    """The JSON at url (POSTing body when given), or None after three tries; None at once for a 404. Raises Refused
    when the server refuses us or answers with something other than JSON (a bot challenge)."""
    for attempt in range(3):
        if out_of_time():
            return None
        wait = LAST[0] + DELAY - time.time()
        if wait > 0:
            time.sleep(wait)
        STATS["requests"] += 1
        if STATS["requests"] % 100 == 0:
            print(f"  {STATS['requests']} requests, {round((time.time() - START) / 60)} min"
                  + (f"; failures {dict(FAILS)}" if FAILS else ""), flush=True)
        headers = {"User-Agent": AGENT, "Accept": "application/json", "Accept-Encoding": "gzip"}
        data = None
        if body is not None:
            data = json.dumps(body).encode()
            headers["Content-Type"] = "application/json"
        try:
            req = urllib.request.Request(url, data=data, headers=headers, method="POST" if data else "GET")
            with urllib.request.urlopen(req, timeout=180) as r:
                raw = r.read()
                kind = r.headers.get("Content-Type") or ""
                if r.headers.get("Content-Encoding") == "gzip":
                    raw = gzip.decompress(raw)
            LAST[0] = time.time()
            if "json" not in kind:
                raise Refused(f"{label}: answered {kind or 'no type'}, not JSON (a challenge page?)")
            return json.loads(raw)
        except Refused:
            raise
        except urllib.error.HTTPError as e:
            LAST[0] = time.time()
            FAILS[f"HTTP {e.code}"] += 1
            if e.code in (401, 403, 429):
                raise Refused(f"{label}: HTTP {e.code}")
            if e.code == 404:
                return None
        except Exception as e:
            LAST[0] = time.time()
            FAILS[type(e).__name__] += 1
        time.sleep(20 * (attempt + 1))
    print(f"{label}: failed three times", flush=True)
    return None


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


def strip(obj, names):
    """Drop the keys in names anywhere inside obj (in place)."""
    if isinstance(obj, dict):
        for n in names:
            obj.pop(n, None)
        for v in obj.values():
            strip(v, names)
    elif isinstance(obj, list):
        for v in obj:
            strip(v, names)
    return obj


def sessions():
    """The regular sessions from FIRST_YEAR on, newest first: [{"year", "archive", "id", "live"}]."""
    path = os.path.join(DATA, "sessions.json")
    last = load(path, {})
    new = request(f"{API}/legislators/v1/sessions", "sessions")
    old = request(f"{API}/archive/v1/sessions", "archive sessions")
    if not isinstance(new, list) or not isinstance(old, list):
        print("sessions: unreadable; kept the last copy", flush=True)
        new = new if isinstance(new, list) else last.get("current") or []
        old = old if isinstance(old, list) else last.get("archive") or []
    else:
        save({"current": new, "archive": old}, path)
    out = {}
    for s in new:
        if s.get("type") != "REGULAR":
            continue
        year = int(str(s["ordinals"])[:4])
        ends = s.get("sineDieDate")
        live = bool(s.get("active")) or not ends or date.fromisoformat(ends[:10]) + timedelta(days=LIVE_DAYS) >= TODAY
        out[year] = {"year": year, "archive": False, "id": s["id"], "live": live}
    for s in old:
        year = s.get("sessionYear") or 0
        if s.get("sessionTypeCode") == "R" and year not in out:
            out[year] = {"year": year, "archive": True, "id": s["sessionId"], "live": False}
    return [out[y] for y in sorted(out, reverse=True) if y >= FIRST_YEAR]


def roster(s, folder):
    """The session's members and committees: read when missing, and every run while the session is live."""
    if s["archive"]:
        asks = (("legislators", f"{API}/archive/v1/legislators/findBySession?sessionId={s['id']}&limit=9999", None),
                ("committees", f"{API}/archive/v1/committees/findBySession/{s['id']}", None))
    else:
        asks = (("legislators", f"{API}/legislators/v1/legislators/search?limit=9999&offset=0", {"sessionIds": [s["id"]]}),
                ("committees", f"{API}/committees/v1/standingCommittees/findBySessionId?sessionId={s['id']}", None))
    for name, url, body in asks:
        path = os.path.join(folder, f"{name}.json")
        if os.path.exists(path) and not s["live"]:
            continue
        d = request(url, f"{s['year']} {name}", body)
        rows = d.get("content") if isinstance(d, dict) else d
        if not isinstance(rows, list) or not rows:
            print(f"{s['year']} {name}: unreadable; kept the last copy", flush=True)
            continue
        save(rows, path)
        print(f"{s['year']} {name}: {len(rows)}", flush=True)


def page(s, code, offset):
    """One page of the list, starting at item offset (a multiple of PAGE): (bills, total), or (None, None). The API's
    "offset" parameter is the page number, not the item."""
    if s["archive"]:
        d = request(f"{API}/archive/v1/bills/search?limit={PAGE}&offset={offset // PAGE}",
                    f"{s['year']} {code} list at {offset}",
                    {"sessionId": s["id"], "billTypes": [code], "sortBy": "billNumber"})
        d = d.get("bills") if isinstance(d, dict) else None
    else:
        d = request(f"{API}/bills/v1/bills/filter?limit={PAGE}&offset={offset // PAGE}&sort=billNumber,asc",
                    f"{s['year']} {code} list at {offset}",
                    [{"sessionIds": [s["id"]], "billTypeIds": [TYPES[code]]}])
    if not isinstance(d, dict) or not isinstance(d.get("content"), list):
        return None, None
    return d["content"], d.get("totalElements") or 0


def read_list(s, folder, state):
    """Each listed bill into bills/<HB1>.json, a page at a time. A live session's list is read again from the start
    every run; another's resumes at the saved page until it has been read in full once. True when read in full."""
    if state.get("listed") and not s["live"]:
        return True
    progress = {} if s["live"] else state.setdefault("pages", {})  # {"HB": {"next": 300, "total": 968}}
    whole = True
    for code in TYPES:
        p = progress.setdefault(code, {"next": 0, "total": None})
        while p["total"] is None or p["next"] < p["total"]:
            if out_of_time():
                return False
            bills, total = page(s, code, p["next"])
            if bills is None:
                print(f"{s['year']} {code}: list page at {p['next']} unreadable", flush=True)
                whole = False
                break
            p["total"] = total
            if not bills:
                break
            os.makedirs(os.path.join(folder, "bills"), exist_ok=True)
            for b in bills:
                code_of = b.get("billType") if s["archive"] else (b.get("billType") or {}).get("code")
                k = f"{code_of}{b.get('billNumber')}"
                if s["archive"]:
                    strip(b, ("committeeAssignments",))
                save(b, os.path.join(folder, "bills", f"{k}.json"))
            p["next"] += len(bills)
            if not s["live"]:
                state["pages"] = progress
                save(state, os.path.join(folder, "state.json"))
        if p["total"] is None or p["next"] < p["total"]:
            whole = False  # unreadable, or the pages ran out early
        if p["total"]:
            print(f"{s['year']} {code}: {min(p['next'], p['total'])} of {p['total']} listed", flush=True)
    if whole:
        state["listed"] = TODAY.isoformat()
        state.pop("pages", None)
    return whole


def stamps(bill):
    """The ids of a bill's history steps with a floor vote, and of its committee votes (executive actions)."""
    votes, actions = set(), set()
    for st in (bill.get("draft") or {}).get("billStatuses") or []:
        name = (st.get("billStatusCode") or {}).get("name") or ""
        if st.get("vote"):
            votes.add(st["vote"]["id"])
        if st.get("executiveActionId") or "Executive Action" in name:
            actions.add(st["id"])
    return sorted(votes), sorted(actions)


def bills_on_disk(folder):
    out = {}
    for name in sorted(os.listdir(os.path.join(folder, "bills"))) if os.path.isdir(os.path.join(folder, "bills")) else []:
        if name.endswith(".json"):
            b = load(os.path.join(folder, "bills", name))
            if isinstance(b, dict):
                out[name[:-5]] = b
    return out


def todo(folder, state):
    """{"votes": [(key, bill id, ids)], "committee": [...]}: the bills whose votes or committee votes are missing or
    out of date (the history shows a vote that wasn't there when they were last read)."""
    out = {"votes": [], "committee": []}
    for k, b in bills_on_disk(folder).items():
        for kind, ids in zip(("votes", "committee"), stamps(b)):
            if ids and (state.setdefault(kind, {}).get(k) != ids or not os.path.exists(os.path.join(folder, kind, f"{k}.json"))):
                out[kind].append((k, b["id"], ids))
    return out


def per_bill(s, folder, state):
    """Each bill's floor votes and committee votes, where missing or out of date."""
    work = todo(folder, state)
    for kind in ("votes", "committee"):
        os.makedirs(os.path.join(folder, kind), exist_ok=True)
        got = 0
        for k, bill_id, ids in work[kind]:
            if out_of_time():
                break
            if kind == "votes":
                d = request(f"{API}/bills/v1/votes/findByBillId?billId={bill_id}", f"{s['year']} {k} votes")
                if isinstance(d, list):
                    for v in d:
                        v.pop("bill", None)  # the bill itself, again
            else:
                d = request(f"{API}/committees/v1/executiveActions/findByBillId?billId={bill_id}", f"{s['year']} {k} committee votes")
                if isinstance(d, list):
                    strip(d, ("memberships", "staffMemberships", "agendaItems"))  # the committee's members (committees.json), staff, agenda
            if not isinstance(d, list):
                continue  # failed: the last copy stays, and it's asked again next run
            save(d, os.path.join(folder, kind, f"{k}.json"))
            state[kind][k] = ids
            got += 1
            if got % 25 == 0:
                save(state, os.path.join(folder, "state.json"))
        save(state, os.path.join(folder, "state.json"))
        print(f"{s['year']} {kind}: {got} of {len(work[kind])} bills read", flush=True)


def cosponsors(s, folder, state):
    """cosponsors.json, from the bill filter once per legislator (cosponsorIds), resuming where the last run stopped;
    again every COSPONSOR_DAYS while the session is live."""
    c = state.setdefault("cosponsors", {})
    if c.get("read") and (not s["live"] or c["read"] >= (TODAY - timedelta(days=COSPONSOR_DAYS)).isoformat()) \
            and not c.get("done"):
        return
    members = load(os.path.join(folder, "legislators.json")) or []
    if not members:
        return
    done = c.setdefault("done", {})  # legislator id -> the bills they co-sponsor, while a sweep is under way
    for m in members:
        lid = str(m["id"])
        if lid in done:
            continue
        keys, number = [], 0
        while True:
            if out_of_time():
                save(state, os.path.join(folder, "state.json"))
                return
            d = request(f"{API}/bills/v1/bills/filter?limit={PAGE}&offset={number}&sort=billNumber,asc",
                        f"{s['year']} bills co-sponsored by {lid}",
                        [{"sessionIds": [s["id"]], "billTypeIds": list(TYPES.values()), "cosponsorIds": [m["id"]]}])
            if not isinstance(d, dict) or not isinstance(d.get("content"), list):
                keys = None
                break
            keys += [f"{b['billType']['code']}{b['billNumber']}" for b in d["content"] if b.get("billType")]
            number += 1  # the API's offset is a page number
            if not d["content"] or number * PAGE >= (d.get("totalElements") or 0):
                break
        if keys is None:
            print(f"{s['year']} co-sponsors of {lid}: unreadable", flush=True)
            save(state, os.path.join(folder, "state.json"))
            return  # the sweep resumes here next run
        done[lid] = keys
        save(state, os.path.join(folder, "state.json"))
    out = {}
    for lid, keys in done.items():
        for k in keys:
            out.setdefault(k, []).append(int(lid))
    save(out, os.path.join(folder, "cosponsors.json"))
    c["read"] = TODAY.isoformat()
    c["done"] = {}
    save(state, os.path.join(folder, "state.json"))
    print(f"{s['year']} co-sponsors: {sum(map(len, out.values()))} on {len(out)} bills", flush=True)


def begun(s):
    """Whether a session has convened (the first Monday of January). One listed earlier, with bills numbered before it,
    is read when it's there but never holds Montana off the site."""
    y = s["year"]
    return TODAY >= date(y, 1, 1 + (0 - date(y, 1, 1).weekday()) % 7)


def missing(s, folder):
    """What of this session was never downloaded (a failed re-read with a last copy doesn't count)."""
    state = load(os.path.join(folder, "state.json"), {})
    if state.get("finished"):
        return []
    out = []
    if not os.path.exists(os.path.join(folder, "legislators.json")):
        out.append(f"{s['year']}:members")
    if not state.get("listed") and not (s["live"] and os.path.isdir(os.path.join(folder, "bills"))):
        out.append(f"{s['year']}:list")
    # Votes, committee votes and co-sponsors hold the session back only until its first copy is whole: after that, ones
    # still to read (a new vote, a failed request) fill in on later runs.
    if not s["archive"] and not state.get("whole"):
        for k, b in bills_on_disk(folder).items():
            v, a = stamps(b)
            if v and not os.path.exists(os.path.join(folder, "votes", f"{k}.json")):
                out.append(f"{s['year']}:votes")
                break
        for k, b in bills_on_disk(folder).items():
            v, a = stamps(b)
            if a and not os.path.exists(os.path.join(folder, "committee", f"{k}.json")):
                out.append(f"{s['year']}:committee")
                break
        if not (state.get("cosponsors") or {}).get("read") and not os.path.exists(os.path.join(folder, "cosponsors.json")):
            out.append(f"{s['year']}:cosponsors")
    return out


def session_lists(s):
    """A session's members, committees and bill list. False when there is nothing to read (finished, or a session
    without numbered bills yet)."""
    folder = os.path.join(DATA, str(s["year"]))
    state_path = os.path.join(folder, "state.json")
    state = load(state_path, {})
    if state.get("finished"):
        print(f"{s['year']}: finished and fully read; nothing to do", flush=True)
        return False
    if out_of_time():
        return False
    if not os.path.isdir(folder) and not s["archive"]:  # a session not yet started: only once it has numbered bills
        bills, total = page(s, "HB", 0)
        bills, total_sb = page(s, "SB", 0) if not total else (None, 0)
        if not total and not total_sb:
            print(f"{s['year']}: no bills numbered yet", flush=True)
            return False
    os.makedirs(folder, exist_ok=True)
    roster(s, folder)
    read_list(s, folder, state)
    save(state, state_path)
    return True


def session_details(s):
    """A session's floor votes, committee votes and co-sponsors (current system only), after every session's list; a
    session that isn't live is marked finished once everything is read."""
    folder = os.path.join(DATA, str(s["year"]))
    state_path = os.path.join(folder, "state.json")
    state = load(state_path, {})
    if not s["archive"]:
        per_bill(s, folder, state)
        cosponsors(s, folder, state)
    if state.get("listed") and not state.get("whole") and not missing(s, folder):
        state["whole"] = True
        save(state, state_path)
    if state.get("listed") and not s["live"] and not missing(s, folder) and not any(todo(folder, state).values()) \
            and not out_of_time():
        state["finished"] = True
        save(state, state_path)
        print(f"{s['year']}: finished", flush=True)


def main():
    os.makedirs(DATA, exist_ok=True)
    # Before the first copy, a run cut off without its summary leaves this, so a partial copy isn't published.
    if not ONLY and not any(name.isdigit() for name in os.listdir(DATA)):
        with open(MARKER, "w") as f:
            f.write("running\n")
    refused = False
    found = sessions_seen = []
    try:
        found = sessions_seen = [s for s in sessions() if not ONLY or s["year"] == ONLY]
        found = [s for s in found if session_lists(s)]  # the newest first
        for s in found:
            session_details(s)
    except Refused as e:
        print(f"Stopped: the server refused a request ({e})", flush=True)
        refused = True
    gaps = [g for s in sessions_seen if begun(s) for g in missing(s, os.path.join(DATA, str(s["year"])))
            if os.path.isdir(os.path.join(DATA, str(s["year"]))) or not s["live"]]  # (a live one may have no bills yet)
    if not sessions_seen:
        gaps.append("sessions")
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
