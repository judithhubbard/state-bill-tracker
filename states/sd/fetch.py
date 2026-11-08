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
- The Legislature's own lists of bills signed, vetoed and hoghoused (BillLogs/...), for checking totals, into logs.json.

A finished session (an earlier year) is read once. The session of this year or later is read every run: its bill list
and action logs (two requests) say which bills changed, and only those bills' details are read again; members,
committees and the BillLogs lists every run. One request at a time, a second apart.
Usage: python3 states/sd/fetch.py [first_year]   (default: two years back; also next year's session once listed)
"""
import hashlib, json, os, sys, time, urllib.error, urllib.request
from datetime import date

API = "https://sdlegislature.gov/api/"
DATA = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "sd"))
AGENT = "statebilltracker.org (a nonprofit bill tracker; contact via github.com/judithhubbard)"
YEAR = date.today().year
FIRST = int(sys.argv[1]) if len(sys.argv) > 1 else YEAR - 2
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
        if index == [] and year > YEAR:
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
            if y in ids:
                session(y, ids[y])
            else:
                print(f"{y}: no regular session listed")
                INCOMPLETE.add(f"{y}:session")
        if YEAR + 1 in ids:  # prefiled bills for next year's session
            session(YEAR + 1, ids[YEAR + 1])
    except Refused as e:
        print(f"Stopped: {e}")
        refused = True
        if not WHOLE[0]:  # a refusal stops a first copy; once whole, the last copies stay
            INCOMPLETE.add("refused")
    print(f"{STATS['requests']} requests in {(time.time() - began) / 60:.0f} minutes")
    if INCOMPLETE:
        with open(marker, "w") as f:
            f.write(" ".join(sorted(INCOMPLETE)) + "\n")
    elif os.path.exists(marker):
        os.remove(marker)
    if refused:
        sys.exit(1)


if __name__ == "__main__":
    main()
