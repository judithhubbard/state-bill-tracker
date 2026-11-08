#!/usr/bin/env python3
"""Download Georgia's bills from the General Assembly's SOAP web services
(http://webservices.legis.ga.gov/GGAServices/<Service>/Service.svc, plain HTTP; each service's ?singleWsdl lists
its operations; www.legis.ga.gov's robots.txt has no rules).

- Each regular session's legislation list (GetLegislationForSession: every HB, SB, HR and SR with its caption) into
  data/ga/<year>/legislation.json (year = the session's first year: 2025 for 2025-2026).
- Each House and Senate bill's detail (GetLegislationDetail: sponsors in order, committees, status history with
  dates, the long title as Summary, footnotes, act or veto number, versions, and its floor votes' listings) into
  data/ga/<year>/bills/<HB123>.json; also the House and Senate resolutions proposing amendments to the state
  Constitution (their captions end "- CA": data/ga/<year>/bills/<HR18>.json). Other resolutions are left out. A finished session's are read once; the current
  one's every run (the service has no change feed; about 2,300 bills, a few minutes).
- Each vote the bills list (GetVote: every member's vote, by member id) into data/ga/<year>/votes/<id>.json, once.
- The members (GetMembersBySession, then GetMember for addresses, phones, emails, titles and committee roles) and
  committees (GetCommitteesBySession, then GetCommitteeForSession for members and roles) into members.json and
  committees.json; a finished session's once.
Three requests at a time. Usage: python3 states/ga/fetch.py [first_year]   (default: the session before this one)
"""
import json, os, re, sys, time, urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from xml.sax.saxutils import escape

BASE = "http://webservices.legis.ga.gov/GGAServices"
NS = "http://www.legis.ga.gov/2009/01/01/services/"
NIL = "{http://www.w3.org/2001/XMLSchema-instance}nil"
# Each service's SOAPAction prefix (Session's actions are bare names).
ACTIONS = {"Session": "", "Legislation": NS + "LegislationSearch/", "Votes": NS + "VoteFinder/",
           "Members": NS + "MemberFinder/", "Committees": NS + "CommitteeFinder/"}
# Elements that hold a list (the WSDL's ArrayOf... types). "Legislation" is a list in a range and text in a vote listing.
LISTS = {"Authors", "CommitteeAssigned", "CommitteeMemberships", "Committees", "Days", "DocumentTypes", "Images",
         "Legislation", "LegislationTypes", "Members", "Page", "SessionContexts", "SessionsInService", "Sponsors",
         "StatusConstraints", "StatusHistory", "SubCommittees", "SubcommitteeMemberships", "Subjects", "Versions",
         "Votes", "Years"}
DATA = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "ga"))
AGENT = "statebilltracker.org (a nonprofit bill tracker; contact via github.com/judithhubbard)"
YEAR = date.today().year
CURRENT = YEAR if YEAR % 2 else YEAR - 1
FIRST = int(sys.argv[1]) if len(sys.argv) > 1 else CURRENT - 2
INCOMPLETE = set()


def tag(el):
    return el.tag.rsplit("}", 1)[-1]


def plain(el, many=False):
    """An element as JSON: nil -> None, text -> str, a list element -> list, else a dict."""
    kids = list(el)
    if el.get(NIL) == "true":
        return None
    if many or (tag(el) in LISTS and (kids or not (el.text or "").strip())):
        return [plain(k) for k in kids]
    if not kids:
        return (el.text or "").strip()
    return {tag(k): plain(k) for k in kids}


def call(service, op, many=False, timeout=180, **params):
    """One SOAP call; returns the operation's result as JSON, None if the service says there's none, False on failure."""
    body = "".join(f"<{k}>{escape(str(v))}</{k}>" for k, v in params.items())
    env = (f'<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/"><s:Body>'
           f'<{op} xmlns="{NS}">{body}</{op}></s:Body></s:Envelope>').encode()
    for attempt in range(4):
        try:
            req = urllib.request.Request(f"{BASE}/{service}/Service.svc", data=env, headers={
                "User-Agent": AGENT, "Content-Type": "text/xml; charset=utf-8",
                "SOAPAction": f'"{ACTIONS[service]}{op}"'})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                root = ET.fromstring(r.read())
            res = root.find(f".//{{{NS}}}{op}Result")
            return None if res is None else plain(res, many)
        except urllib.error.HTTPError as e:
            if e.code in (403, 429):
                print(f"{service}/{op}: refused ({e.code}); stopping")
                sys.exit(1)
            time.sleep(10 * (attempt + 1))
        except Exception:
            time.sleep(10 * (attempt + 1))
    return False


def save(path, data):
    json.dump(data, open(path + ".tmp", "w"), ensure_ascii=False)
    os.replace(path + ".tmp", path)


def session_ids():
    """{2025: 1033, ...} for the regular sessions ("2025-2026 Regular Session")."""
    out = {}
    for s in call("Session", "GetSessions", many=True) or []:
        d = s.get("Description") or ""
        if d.endswith(" Regular Session") and d[:4].isdigit():
            out[int(d[:4])] = int(s["Id"])
    return out


def is_amendment(x):
    """A House or Senate resolution proposing an amendment to the state Constitution: its caption ends "- CA"
    ("Right to Register and Vote; clarify -CA"). convert.py checks its long title too (one ratifies a federal amendment)."""
    return x["Description"].split(" ")[0] in ("HR", "SR") and bool(re.search(r"\bCA\s*$", x.get("Caption") or ""))


def pool_map(fn, items):
    with ThreadPoolExecutor(3) as pool:
        return list(pool.map(fn, items))


def session(year, sid):
    folder = os.path.join(DATA, str(year))
    for sub in ("bills", "votes"):
        os.makedirs(os.path.join(folder, sub), exist_ok=True)
    live = year >= CURRENT
    # The whole list is slow the first time the server builds it (once more than two minutes).
    index = call("Legislation", "GetLegislationForSession", many=True, timeout=600, SessionId=sid)
    if not index:
        print(f"{year}: no legislation list; kept the last copy")
        # Only a list never read holds Georgia off the site; a failed refresh keeps the last copy.
        if not os.path.exists(os.path.join(folder, "legislation.json")):
            INCOMPLETE.add(f"{year}:list")
        try:
            index = json.load(open(os.path.join(folder, "legislation.json")))
        except (OSError, ValueError):
            return
    else:
        save(os.path.join(folder, "legislation.json"), index)
    bills = {x["Description"].replace(" ", ""): x["Id"] for x in index
             if x["Description"].split(" ")[0] in ("HB", "SB") or is_amendment(x)}

    def one(item):
        num, lid = item
        path = os.path.join(folder, "bills", f"{num}.json")
        if os.path.exists(path) and not live:
            return True
        d = call("Legislation", "GetLegislationDetail", LegislationId=lid)
        if not d:
            return False
        save(path, d)
        return True

    got = sum(pool_map(one, sorted(bills.items())))
    # A bill whose refresh failed keeps its last copy (2 of 2,288 failed on 2026-11-08 and took Georgia off the site):
    # only bills never read make the copy incomplete.
    if any(not os.path.exists(os.path.join(folder, "bills", f"{num}.json")) for num in bills):
        INCOMPLETE.add(f"{year}:bills")
    print(f"{year}: {got} of {len(bills)} bills read", flush=True)

    votes = set()
    for num in bills:
        try:
            d = json.load(open(os.path.join(folder, "bills", f"{num}.json")))
        except (OSError, ValueError):
            continue
        votes.update(v["VoteId"] for v in d.get("Votes") or [] if v.get("VoteId"))
    todo = sorted(v for v in votes if not os.path.exists(os.path.join(folder, "votes", f"{v}.json")))

    def vote(vid):
        d = call("Votes", "GetVote", VoteId=vid)
        if not d:
            return False
        save(os.path.join(folder, "votes", f"{vid}.json"), d)
        return True

    vgot = sum(pool_map(vote, todo))  # votes not read now are read on a later run; they don't hold the site
    print(f"{year}: {len(votes)} votes ({vgot} of {len(todo)} read now)", flush=True)

    people(year, sid, folder, live)


def people(year, sid, folder, live):
    """Members and committees, each with its details."""
    for name, lister, op, key in (("members", "GetMembersBySession", "GetMember", "MemberId"),
                                  ("committees", "GetCommitteesBySession", "GetCommitteeForSession", "CommitteeId")):
        path = os.path.join(folder, f"{name}.json")
        if os.path.exists(path) and not live:
            continue
        service = "Members" if name == "members" else "Committees"
        listing = call(service, lister, many=True, SessionId=sid)
        if not listing:
            print(f"{year}: no {name} list; kept the last copy")
            if not os.path.exists(path):
                INCOMPLETE.add(f"{year}:{name}")
            continue
        extra = {"SessionId": sid} if name == "committees" else {}
        details = pool_map(lambda x: call(service, op, **{key: x["Id"]}, **extra), listing)
        out = []
        try:
            last = {e["listing"]["Id"]: e["detail"] for e in json.load(open(path)) if e.get("detail")}
        except (OSError, ValueError, KeyError, TypeError):
            last = {}
        for x, d in zip(listing, details):
            d = d or last.get(x["Id"])  # a failed detail keeps the last copy's
            if not d:
                INCOMPLETE.add(f"{year}:{name}")
            out.append({"listing": x, "detail": d or None})
        save(path, out)
        print(f"{year}: {len(out)} {name}", flush=True)


def main():
    os.makedirs(DATA, exist_ok=True)
    ids = session_ids()
    if not ids:
        sys.exit("No session list from the Session service")
    save(os.path.join(DATA, "sessions.json"), ids)
    for y in range(FIRST, CURRENT + 1, 2):
        if y in ids:
            session(y, ids[y])
        else:
            print(f"{y}: no regular session listed")
            INCOMPLETE.add(f"{y}:session")
    sys.path.insert(0, os.path.normpath(os.path.join(DATA, "..", "..")))
    from states.ga import contacts
    try:
        contacts.main(CURRENT)
    except (SystemExit, OSError) as e:
        print(e)
    marker = os.path.join(DATA, "incomplete")
    if INCOMPLETE:
        open(marker, "w").write(" ".join(sorted(INCOMPLETE)) + "\n")
    elif os.path.exists(marker):
        os.remove(marker)


if __name__ == "__main__":
    main()
