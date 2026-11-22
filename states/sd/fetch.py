#!/usr/bin/env python3
"""Download South Dakota's bills from the Legislature's JSON API (https://sdlegislature.gov/api/, no key; the site's
own Vue pages read it; robots.txt disallows only /pdfviewer and a few logo files). An unknown path answers with the
site's HTML page (status 200), not a 404, so any answer that isn't JSON counts as a failure.

- Sessions: the session list (one regular session a year; special sessions, "2025s", are left out) into
  data/sd/sessions.json ({year: session id}).
- Each regular session's bill list (Bills/Session/<id>: every bill and resolution with its title, sponsor ids,
  keyword ids and committees) into data/sd/<year>/bills.json, and every bill's action log in one answer
  (Bills/BillStatus/<id>: dated actions with the acting and assigned committee, result and vote totals) into
  status.json.
- Each House and Senate bill and joint resolution (joint resolutions propose constitutional amendments; other
  resolutions and commemorations are left out): its detail (Bills/<id>: sponsors in order with prime/co-sponsor,
  committee sponsor, keywords by name) and versions (Bills/Versions/<id>: each printed version's document id and
  date), with its action log from status.json, into data/sd/<year>/bills/<HB1001>.json.
- Each vote in the action logs (Votes/<id>: every member's vote, committee and floor) into votes/<id>.json, once.
- The members (SessionMembers/Session/<id>: district, party, Capitol phone, state email) into members.json, and the
  committees (SessionCommittees/Session/<id>, then SessionCommittees/Detail/<id> for members with Chair and Vice-Chair,
  room and meeting days) into committees.json.
- The governor's veto letters: each "Vetoed by the Governor" action names the day's journal (DocumentId), which prints
  the letter in full; that journal (Documents/<id>.html) once, into journals/<id>.html (`veto_journals()`).
- The Legislature's own lists of bills signed, vetoed and hoghoused (BillLogs/...), for checking totals, into logs.json.
- The LRC's Title Summaries of each session's laws ("What it does"), into texts_<year>.json (states/sd/summaries.py).

A finished session (an earlier year) is read once. The session of this year or later is read every run: its bill list
and action logs (two requests) say which bills changed, and only those bills' details are read again; members,
committees and the BillLogs lists every run. One request at a time, a second apart.
A run stops five minutes before its time limit (FETCH_MINUTES, set by the workflow), with what it read saved.
Usage: python3 states/sd/fetch.py [first_year]   (default: the shared window's first year, states/window.py: this year and
the four before, not before 2023; also next year's session once listed)
"""
import hashlib, html, json, os, re, sys, time, urllib.error, urllib.request
from datetime import date, timedelta
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
from states import window as W

API = "https://sdlegislature.gov/api/"
DATA = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "sd"))
AGENT = "statebilltracker.org (a nonprofit bill tracker; contact via github.com/judithhubbard)"
YEAR = date.today().year
FIRST = int(sys.argv[1]) if len(sys.argv) > 1 else W.first_year()
START = time.time()
READ = []  # the years this run read (states/window.py's marks change only for these)
BUDGET = max(0.0, float(os.environ.get("FETCH_MINUTES") or 0) - 5) * 60


def out_of_time():
    return bool(BUDGET) and time.time() - START > BUDGET


KINDS = ("HB", "SB", "HJR", "SJR")
LOGS = ("SignedByGovernor", "VetoedByGovernor", "Hoghouse")
INCOMPLETE = set()
WHOLE = [True]  # the last run left nothing missing (set in main): votes still to read then don't hold the site
STATS = {"requests": 0}


class Refused(Exception):
    pass


def get(path, timeout=60):
    """One API answer as JSON; None when it fails or isn't JSON. Raises Refused on 401/403, a bot challenge, or
    429 three times running."""
    throttled = 0
    for attempt in range(4):
        time.sleep(1)
        STATS["requests"] += 1
        try:
            req = urllib.request.Request(API + path, headers={"User-Agent": AGENT, "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                body = r.read()
                kind = r.headers.get("Content-Type") or ""
            if "json" not in kind:
                low = body[:5000].lower()
                if any(w in low for w in (b"captcha", b"challenge", b"just a moment", b"access denied")) \
                        and b"chunk-vendors" not in low:
                    raise Refused(f"{path}: a bot challenge")
                print(f"{path}: not JSON (the site's page: no such endpoint)")
                return None
            return json.loads(body)
        except urllib.error.HTTPError as e:
            if e.code in (401, 403):
                raise Refused(f"{path}: refused ({e.code})")
            if e.code == 429:
                throttled += 1
                if throttled >= 3:
                    raise Refused(f"{path}: too many requests (429), three times")
                time.sleep(60 * throttled)
                continue
            if e.code == 404:
                return None
            print(f"{path}: HTTP {e.code}; trying again", flush=True)
            time.sleep(10 * (attempt + 1))
        except (OSError, ValueError) as e:
            print(f"{path}: {e.__class__.__name__} {e}; trying again", flush=True)
            time.sleep(10 * (attempt + 1))
    print(f"{path}: failed", flush=True)
    return None


def save(path, data):
    with open(path + ".tmp", "w") as f:
        json.dump(data, f, ensure_ascii=False)
    os.replace(path + ".tmp", path)


def load(path):
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def session_ids():
    """{2026: 71, ...}: the regular sessions."""
    out = {}
    for s in get("Sessions") or []:
        y = str(s.get("Year") or "")
        if y.isdigit() and not s.get("SpecialSession"):
            out[int(y)] = int(s["SessionId"])
    return out


def key(b):
    return f"{b['BillType']}{b['BillNumberOnly']}"


def fingerprint(entry, logs):
    """What the bill list and action logs say about one bill; a change means its detail is read again."""
    return hashlib.sha1(json.dumps([entry, logs], sort_keys=True).encode()).hexdigest()


def session(year, sid):
    folder = os.path.join(DATA, str(year))
    live = year >= YEAR
    paths = {n: os.path.join(folder, n + ".json") for n in ("bills", "status", "seen", "members", "committees", "logs")}
    index = status = None
    if live or not (os.path.exists(paths["bills"]) and os.path.exists(paths["status"])):
        index = get(f"Bills/Session/{sid}")
        if index == [] and (year > YEAR or not begun(year)):  # next year's, or this year's before it convenes
            print(f"{year}: no bills yet")
            return
        status = get(f"Bills/BillStatus/{sid}", timeout=600) if index else None
        if not index or status is None:
            print(f"{year}: no bill list or action logs; kept the last copy")
            if not (os.path.exists(paths["bills"]) and os.path.exists(paths["status"])):  # only lists never read count
                INCOMPLETE.add(f"{year}:list")
            index = status = None
    for sub in ("bills", "votes"):
        os.makedirs(os.path.join(folder, sub), exist_ok=True)
    if index is None:
        index, status = load(paths["bills"]), load(paths["status"])
        if index is None or status is None:
            return
    else:
        save(paths["bills"], index)
        save(paths["status"], status)
    logs = {x["BillId"]: x.get("ActionLogs") or [] for x in status}
    bills = {key(b): b for b in index if b["BillType"] in KINDS}
    seen = load(paths["seen"]) or {}  # {HB1001: fingerprint} of the details read

    todo = []
    for k, b in sorted(bills.items()):
        fp = fingerprint(b, logs.get(b["BillId"], []))
        path = os.path.join(folder, "bills", f"{k}.json")
        if not os.path.exists(path) or (live and seen.get(k) != fp):
            todo.append((k, b, fp))
        elif os.path.exists(path):  # the action log comes with the list: keep the file's copy current
            d = load(path)
            if d is not None and d.get("ActionLog") != logs.get(b["BillId"], []):
                d["ActionLog"] = logs.get(b["BillId"], [])
                save(path, d)
    got = 0
    for i, (k, b, fp) in enumerate(todo):
        if out_of_time():
            break
        detail = get(f"Bills/{b['BillId']}")
        versions = get(f"Bills/Versions/{b['BillId']}") if detail else None
        if not detail or versions is None:
            continue
        save(os.path.join(folder, "bills", f"{k}.json"),
             {"listing": b, "detail": detail, "versions": versions, "ActionLog": logs.get(b["BillId"], [])})
        seen[k] = fp
        got += 1
        if got % 100 == 0:
            save(paths["seen"], seen)
            print(f"{year}: {got} of {len(todo)} bills read", flush=True)
    save(paths["seen"], seen)
    # A bill whose refresh failed keeps its last copy; only bills never read make the copy incomplete.
    if any(not os.path.exists(os.path.join(folder, "bills", f"{k}.json")) for k in bills):
        INCOMPLETE.add(f"{year}:bills")
    print(f"{year}: {len(bills)} bills ({got} of {len(todo)} read now; {len(index)} items listed)", flush=True)

    votes = sorted({a["Vote"]["VoteId"] for b in bills.values() for a in logs.get(b["BillId"], [])
                    if a.get("Vote") and a["Vote"].get("VoteId")})
    vtodo = [v for v in votes if not os.path.exists(os.path.join(folder, "votes", f"{v}.json"))]
    vgot = 0
    for v in vtodo:
        if out_of_time():
            break
        d = get(f"Votes/{v}")
        if d and isinstance(d, dict) and "RollCalls" in d:
            save(os.path.join(folder, "votes", f"{v}.json"), d)
            vgot += 1
            if vgot % 200 == 0:
                print(f"{year}: {vgot} of {len(vtodo)} votes read", flush=True)
    if vgot < len(vtodo) and not WHOLE[0]:  # votes still to read hold only a first copy; later they fill in
        INCOMPLETE.add(f"{year}:votes")
    print(f"{year}: {len(votes)} votes ({vgot} of {len(vtodo)} read now)", flush=True)

    if live or not os.path.exists(paths["members"]):
        members = get(f"SessionMembers/Session/{sid}")
        if members:
            # After the 2026 election the API cleared every 2026 member's Capitol phone and email (2026-11-22; the 2027
            # session's list has them): a field the API has emptied keeps the last copy's value.
            old = {m.get("SessionMemberId"): m for m in load(paths["members"]) or [] if isinstance(m, dict)}
            for m in members:
                for f in ("CapitolPhone", "EmailState"):
                    if not m.get(f) and (old.get(m.get("SessionMemberId")) or {}).get(f):
                        m[f] = old[m["SessionMemberId"]][f]
            save(paths["members"], members)
            print(f"{year}: {len(members)} members", flush=True)
        elif not os.path.exists(paths["members"]):  # a failed refresh keeps the last copy
            INCOMPLETE.add(f"{year}:members")
    if live or not os.path.exists(paths["committees"]):
        listing = get(f"SessionCommittees/Session/{sid}")
        if listing:
            out = []
            last = {e["listing"]["SessionCommitteeId"]: e["detail"] for e in load(paths["committees"]) or []
                    if isinstance(e, dict) and e.get("detail") and isinstance(e.get("listing"), dict)}
            for c in listing:
                d = get(f"SessionCommittees/Detail/{c['SessionCommitteeId']}") or last.get(c["SessionCommitteeId"])
                if not d:  # never read (a failed detail keeps the last copy's)
                    INCOMPLETE.add(f"{year}:committees")
                out.append({"listing": c, "detail": d or None})
            save(paths["committees"], out)
            print(f"{year}: {len(out)} committees", flush=True)
        elif not os.path.exists(paths["committees"]):
            INCOMPLETE.add(f"{year}:committees")
    if live or not os.path.exists(paths["logs"]):
        out = {}
        last = load(paths["logs"]) or {}
        for name in LOGS:
            d = get(f"BillLogs/{name}/{sid}")
            if d is None:
                d = last.get(name)  # a failed refresh keeps the last copy
            if d is None:
                INCOMPLETE.add(f"{year}:logs")
            out[name] = d
        save(paths["logs"], out)


AGENDA_BILL = re.compile(r"\b(HB|SB|HJR|SJR|HCR|SCR|HC|SC)\s*(\d{1,4})\b")


def get_html(path):
    """One API document as text (Documents/<id>.html), or None. Never raises: agendas never hold the run back."""
    time.sleep(1)
    STATS["requests"] += 1
    try:
        req = urllib.request.Request(API + path, headers={"User-Agent": AGENT})
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.read().decode("utf-8", "replace")
    except Exception as e:
        print(f"{path}: {e.__class__.__name__}", flush=True)
        return None


def committee_name(full):
    """committees.json's "House Committee on Appropriations" -> "House Appropriations"; "Joint Committee on
    Appropriations" -> "Joint Appropriations"; "House Judiciary" as it is."""
    return re.sub(r"\s+", " ", re.sub(r"\bCommittee on ", "", full or "")).strip()


def agendas(year):
    """Bills on committee agendas from yesterday to three weeks ahead, into data/sd/<year>/agendas.json:
    {"HB1055": [["House Judiciary", "2026-01-16T10:00:00"], ...]}. For each of the session's committees in
    committees.json (not the whole House or Senate), its documents list (SessionCommittees/Documents/<id>?Type=3&Type=5,
    as the committee page's Agendas tab reads it: each agenda's DocumentId, DocumentDate with its UTC offset, and
    NoMeeting for a canceled meeting), then each upcoming agenda's text (Documents/<id>.html), whose bills read
    "HB 1055" (a line break between). About 32 requests a run plus one per agenda; any failure keeps the last copy."""
    folder = os.path.join(DATA, str(year))
    comms = load(os.path.join(folder, "committees.json")) or []
    first, last = (date.today() - timedelta(days=1)).isoformat(), (date.today() + timedelta(days=21)).isoformat()
    out, meetings, failed = {}, 0, 0
    for c in comms:
        lst = c.get("listing") or {}
        if (lst.get("Committee") or {}).get("FullBody") or not lst.get("SessionCommitteeId"):
            continue
        name = committee_name(lst.get("FullName"))
        try:
            docs = get(f"SessionCommittees/Documents/{lst['SessionCommitteeId']}?Type=3&Type=5")
        except Refused as e:
            print(f"agendas: stopped ({e})", flush=True)
            failed += 1
            break
        if docs is None:
            failed += 1
            continue
        for d in docs if isinstance(docs, list) else []:
            when = d.get("DocumentDate") or ""
            if d.get("NoMeeting") or not d.get("DocumentId") or not first <= when[:10] <= last:
                continue
            page = get_html(f"Documents/{d['DocumentId']}.html")
            if page is None:
                failed += 1
                continue
            meetings += 1
            body = html.unescape(re.sub(r"<[^>]+>", " ", re.sub(r"(?s)<(script|style)\b.*?</\1>", " ", page)))
            stamp = when[:19] if re.match(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d", when) else f"{when[:10]}T00:00:00"
            for kind, num in AGENDA_BILL.findall(body):
                entry = [name, stamp]
                if entry not in out.setdefault(f"{kind}{int(num)}", []):
                    out[f"{kind}{int(num)}"].append(entry)
    if failed and not meetings and os.path.exists(os.path.join(folder, "agendas.json")):
        print(f"agendas: {failed} requests failed; kept the last copy", flush=True)
        return
    save(os.path.join(folder, "agendas.json"), out)
    print(f"agendas: {len(out)} bills on {meetings} meetings ({failed} requests failed)", flush=True)


def veto_journals(year):
    """The House or Senate Journal each veto action names (it prints the governor's letter), once each."""
    folder = os.path.join(DATA, str(year))
    bills = os.path.join(folder, "bills")
    if not os.path.isdir(bills):
        return
    ids = set()
    for name in os.listdir(bills):
        b = load(os.path.join(bills, name)) or {}
        for a in b.get("ActionLog") or []:
            if re.match(r"Vetoed by the Governor", a.get("StatusText") or "") and a.get("DocumentId"):
                ids.add(a["DocumentId"])
    todo = sorted(i for i in ids if not os.path.exists(os.path.join(folder, "journals", f"{i}.html")))
    got = 0
    for i in todo:
        if out_of_time():
            break
        page = get_html(f"Documents/{i}.html")
        if page and "Journal" in page:
            os.makedirs(os.path.join(folder, "journals"), exist_ok=True)
            with open(os.path.join(folder, "journals", f"{i}.html"), "w", encoding="utf-8") as f:
                f.write(page)
            got += 1
    if todo:
        print(f"{year}: {got} of {len(todo)} journals with veto letters read", flush=True)


def begun(year):
    """Whether a year's session has convened (the second Tuesday of January)."""
    return date.today() >= date(year, 1, 1 + (1 - date(year, 1, 1).weekday()) % 7 + 7)


def main():
    os.makedirs(DATA, exist_ok=True)
    marker = os.path.join(DATA, "incomplete")
    WHOLE[0] = not os.path.exists(marker)
    if not os.path.exists(marker):  # until this run finishes, the copy may be partial
        with open(marker, "w") as f:
            f.write("running\n")
    began = time.time()
    refused = False
    try:
        ids = session_ids()
        if not ids:
            if WHOLE[0]:
                os.remove(marker)  # nothing read: the last copies stand as they were
            sys.exit("No session list from the API; kept the last copies")
        save(os.path.join(DATA, "sessions.json"), ids)
        for y in range(YEAR, FIRST - 1, -1):  # this year's session first
            if out_of_time():
                break
            if y in ids:
                session(y, ids[y])
                READ.append(y)
            else:
                print(f"{y}: no regular session listed")
                INCOMPLETE.add(f"{y}:session")
        for y in READ:
            if not out_of_time():
                try:  # never holds the run back
                    veto_journals(y)
                except Exception as e:  # noqa: BLE001
                    print(f"{y}: veto letters: failed ({e.__class__.__name__})", flush=True)
        if READ and not out_of_time():
            try:  # the LRC's Title Summaries ("What it does" for laws); never holds the run back
                from states.sd import summaries
                summaries.run(get, READ)
            except Exception as e:  # noqa: BLE001
                print(f"title summaries: failed ({e.__class__.__name__})", flush=True)
        if YEAR + 1 in ids:  # prefiled bills for next year's session
            session(YEAR + 1, ids[YEAR + 1])
            # Its members (those elected in November), whose list carries the emails and phones this year's list lost
            # after the election: contacts.py fills a re-elected member's from it.
            nxt = get(f"SessionMembers/Session/{ids[YEAR + 1]}")
            if nxt:
                save(os.path.join(DATA, "members_next.json"), nxt)
        if YEAR in ids and not out_of_time():
            try:
                agendas(YEAR)  # never holds South Dakota back
            except Exception as e:
                print(f"agendas: failed ({e.__class__.__name__}); kept the last copy", flush=True)
    except Refused as e:
        print(f"Stopped: {e}")
        refused = True
        if not WHOLE[0]:  # a refusal stops a first copy; once whole, the last copies stay
            INCOMPLETE.add("refused")
    print(f"{STATS['requests']} requests in {(time.time() - began) / 60:.0f} minutes")
    # Next year's session (prefiled bills from November, its members not listed yet) never holds South Dakota back.
    undone = {g for g in INCOMPLETE if not g[:4].isdigit() or begun(int(g[:4]))}
    # A year the window added back (2023) marks only itself (states/window.py).
    undone = set(W.settle(DATA, undone, READ))
    if undone:
        with open(marker, "w") as f:
            f.write(" ".join(sorted(undone)) + "\n")
    elif os.path.exists(marker):
        os.remove(marker)
    if refused:
        sys.exit(1)


if __name__ == "__main__":
    main()
