#!/usr/bin/env python3
"""Upcoming committee meetings (hearings and markups) of the current Congress, and the bills each takes up, from the
Congress.gov API (https://api.congress.gov/v3/committee-meeting/<congress>/<house|senate>; a free api.data.gov key, in
the CONGRESS_API_KEY environment variable or ~/.congress_api_key, sent as the X-Api-Key header so it's never in a
printed address; 5,000 requests an hour). Writes data/us/meetings.json, which convert.agendas() reads for the bill
pages' "On the agenda" tags, the agenda line under "In committee" and the watchlists' "Committee meets" deadlines.

Each run lists the meetings of each house updated in the last LOOKBACK days (the list's fromDateTime filters by update
time, not the meeting's day; committees give a week's notice, so a meeting still to come was updated recently) and
reads the details of each one new or changed since its last copy (updateDate), a second apart: a few dozen calls a week
while Congress meets, a handful in recess. Kept for each meeting: its day and time, kind (Hearing, Markup, Meeting),
status (Scheduled, Rescheduled, Postponed, Canceled), committees and the bills it names (relatedItems; else the bill
numbers its documents and title name). Meetings over a month past are dropped.

First, every run, the Senate's own schedule (senate.gov's hearings.xml, one request: `senate_schedule()`) into
data/us/senate_hearings.json, a second source that needs no key. No key: nothing more is fetched and the last copy is kept. The run never fails the download; it stops after --minutes
(default 4) or on the API's rate limit, and the rest is read next run.
Usage: python3 states/us/meetings.py [--minutes N]
"""
import json, os, re, sys, time, urllib.error, urllib.request
from datetime import datetime, timedelta, timezone
from itertools import zip_longest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", ".."))
from states.us import convert as C  # noqa: E402

DATA = os.path.normpath(os.path.join(HERE, "..", "..", "data", "us"))
PATH = os.path.join(DATA, "meetings.json")
API = "https://api.congress.gov/v3"
AGENT = "statebilltracker.org (a nonprofit bill tracker; contact via github.com/judithhubbard)"
LOOKBACK = 21    # days of updates listed each run
KEEP = 30        # days a past meeting is kept
NOW = datetime.now(timezone.utc)
ARGS = sys.argv[1:]
MINUTES = float(ARGS[ARGS.index("--minutes") + 1]) if "--minutes" in ARGS else 4.0


class Limited(Exception):
    pass


def key():
    k = os.environ.get("CONGRESS_API_KEY", "").strip()
    path = os.path.expanduser("~/.congress_api_key")
    if not k and os.path.exists(path):
        k = open(path).read().strip()
    return k


def get(path, k, **q):
    """The API's JSON answer for a path ("committee-meeting/119/house"); None on a 404 or after three failures."""
    q = {"format": "json", **q}
    url = f"{API}/{path}?" + "&".join(f"{a}={b}" for a, b in q.items())
    for n in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": AGENT, "X-Api-Key": k})
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 429:
                raise Limited()
            if e.code == 404:
                return None
            print(f"  {url}: HTTP {e.code}")
        except Exception as e:  # noqa: BLE001 (timeouts, resets)
            print(f"  {url}: {e}")
        time.sleep(5 * (n + 1))
    return None


# "H.R. 10307", "S. 45", "H.J.Res. 3", "S.J. Res. 4" (not "H.Res." or "S.Con.Res.", which the site doesn't have).
NUMBER = re.compile(r"(?<![.\w])(H\.\s?R\.|S\.|H\.\s?J\.\s?Res\.|S\.\s?J\.\s?Res\.)\s?(\d{1,5})\b")
KINDS = {"H.R.": "HR", "S.": "S", "H.J.Res.": "HJRES", "S.J.Res.": "SJRES"}


def bills_of(m):
    """The bill numbers ("HR10307") a meeting takes up: its related items, else the ones its documents and title name."""
    out = []
    for b in (m.get("relatedItems") or {}).get("bills") or []:
        t = str(b.get("type", "")).upper().replace(".", "")
        if t in KINDS.values() and str(b.get("number", "")).isdigit():
            out.append(f"{t}{int(b['number'])}")
    if not out:
        texts = [d.get("name") or d.get("description") or "" for d in m.get("meetingDocuments") or []
                 if d.get("documentType") == "Bills and Resolutions"] + [m.get("title") or ""]
        for t in texts:
            for kind, n in NUMBER.findall(t):
                out.append(KINDS[re.sub(r"\s", "", kind)] + str(int(n)))
    return sorted(set(out), key=out.index)


def compact(m):
    return {"date": m.get("date") or "", "type": m.get("type") or "", "status": m.get("meetingStatus") or "",
            "committees": [c.get("name") or "" for c in m.get("committees") or []],
            "title": (m.get("title") or "")[:300], "bills": bills_of(m), "updateDate": m.get("updateDate") or ""}


SENATE_XML = "https://www.senate.gov/general/committee_schedules/hearings.xml"
SENATE_PATH = os.path.join(DATA, "senate_hearings.json")


def senate_meetings(body):
    """The Senate's own schedule (senate.gov's hearings.xml: every committee meeting it has posted, about a week or two
    ahead) as meetings.json's records, keyed "senate/<identifier>": the day and time (Eastern on the page, kept in UTC as
    the API's are), type ("Open Hearing", "Closed Business Meeting"), committee (and subcommittee), the matter, and the
    bills its documents name (<AssociatedDocument document_prefix="S" document_num="1234">), else the "S. 1234" numbers
    in the matter. Nominations (PN) aren't bills. The placeholder row ("No committee hearings scheduled") has no
    identifier and is left out."""
    import xml.etree.ElementTree as ET
    from zoneinfo import ZoneInfo
    out = {}
    root = ET.fromstring(body)
    for m in root.iter("meeting"):
        t = lambda tag: re.sub(r"\s+", " ", (m.findtext(tag) or "")).strip()
        ident, day = t("identifier"), t("date_iso_8601")
        if not ident or not re.fullmatch(r"\d{4}-\d\d-\d\d", day):
            continue
        clock = t("time_iso_8601") or "00:00:00"
        when = datetime.fromisoformat(f"{day}T{clock}").replace(tzinfo=ZoneInfo("America/New_York")).astimezone(timezone.utc)
        bills = []
        for d in m.iter("AssociatedDocument"):
            kind, num = (d.get("document_prefix") or "").upper().replace(".", ""), d.get("document_num") or ""
            if kind in KINDS.values() and num.isdigit():
                bills.append(f"{kind}{int(num)}")
        if not bills:
            for kind, n in NUMBER.findall(t("matter")):
                bills.append(KINDS[re.sub(r"\s", "", kind)] + str(int(n)))
        name = "Senate " + t("committee") + (f" Subcommittee on {t('subcommittee')}" if t("subcommittee") else "")
        matter = t("matter")
        out[f"senate/{ident}"] = {
            "date": when.strftime("%Y-%m-%dT%H:%M:%SZ"), "type": t("type"),
            "status": "Canceled" if re.search(r"\bcancel", matter, re.I) else "Postponed" if re.search(r"\bpostpon", matter, re.I) else "Scheduled",
            "committees": [name], "title": matter[:300], "bills": sorted(set(bills), key=bills.index),
            "updateDate": t("last_update_iso_8601"), "source": "senate.gov"}
    return out


def senate_schedule():
    """One request a run for the Senate's schedule (senate.gov has no robots.txt rule against it), into
    data/us/senate_hearings.json ({"listed", "meetings"}), keeping past meetings for KEEP days as meetings.json does (the
    schedule drops a meeting once it's held). convert.agendas() merges it with the API's meetings, without duplicates.
    A failed request keeps the last copy."""
    try:
        req = urllib.request.Request(SENATE_XML, headers={"User-Agent": AGENT})
        with urllib.request.urlopen(req, timeout=60) as r:
            body = r.read()
        now_ = senate_meetings(body)
    except Exception as e:  # noqa: BLE001 (never fails the download)
        print(f"senate schedule: {type(e).__name__}: {e}; last copy kept")
        return
    old = json.load(open(SENATE_PATH)) if os.path.exists(SENATE_PATH) else {}
    cutoff = (NOW - timedelta(days=KEEP)).strftime("%Y-%m-%d")
    meets = {i: m for i, m in {**(old.get("meetings") or {}), **now_}.items() if m["date"][:10] >= cutoff}
    stale = not old.get("listed") or (NOW - datetime.fromisoformat(old["listed"].replace("Z", "+00:00"))).total_seconds() > 12 * 3600
    if meets != old.get("meetings") or stale:
        with open(SENATE_PATH + ".tmp", "w") as f:
            json.dump({"listed": NOW.strftime("%Y-%m-%dT%H:%M:%SZ"), "meetings": meets}, f, indent=0, sort_keys=True)
        os.replace(SENATE_PATH + ".tmp", SENATE_PATH)
    soon = [m for m in now_.values() if m["bills"]]
    print(f"senate schedule: {len(now_)} meetings posted, {len(soon)} naming bills")


def main():
    sys.stdout.reconfigure(line_buffering=True)
    senate_schedule()
    k = key()
    if not k:
        print("committee meetings: no Congress.gov API key (CONGRESS_API_KEY or ~/.congress_api_key); last copy kept")
        return
    congress = C.CONGRESSES[-1]
    old = json.load(open(PATH)) if os.path.exists(PATH) else {}
    if old.get("congress") != congress:
        old = {}
    meets = dict(old.get("meetings") or {})
    deadline = time.time() + MINUTES * 60
    since = (NOW - timedelta(days=LOOKBACK)).strftime("%Y-%m-%dT%H:%M:%SZ")
    done, read = True, 0
    try:
        listed = []
        for house in ("house", "senate"):
            offset = 0
            while True:
                page = get(f"committee-meeting/{congress}/{house}", k, limit=250, offset=offset, fromDateTime=since,
                           toDateTime=NOW.strftime("%Y-%m-%dT%H:%M:%SZ"))
                if page is None:
                    done = False
                    break
                items = page.get("committeeMeetings") or []
                listed += [(house, it) for it in items]
                if len(items) < 250:
                    break
                offset += 250
                time.sleep(1)
        # The newest meetings first (the ones still to come), each house in turn, in case a run stops early.
        by = {h: sorted((x for x in listed if x[0] == h), key=lambda x: -int(x[1].get("eventId") or 0)) for h in ("house", "senate")}
        listed = [x for pair in zip_longest(by["house"], by["senate"]) for x in pair if x]
        for house, it in listed:
            ident = f"{house}/{it['eventId']}"
            if meets.get(ident, {}).get("updateDate") == it.get("updateDate"):
                continue
            if time.time() > deadline:
                done = False
                break
            time.sleep(1)
            d = get(f"committee-meeting/{congress}/{house}/{it['eventId']}", k)
            read += 1
            if d and d.get("committeeMeeting"):
                meets[ident] = compact(d["committeeMeeting"])
            else:
                done = False
    except Limited:
        print("committee meetings: the API's rate limit was reached; the rest next run")
        done = False
    cutoff = (NOW - timedelta(days=KEEP)).strftime("%Y-%m-%d")
    meets = {i: m for i, m in meets.items() if m["date"][:10] >= cutoff}
    listed_at = NOW.strftime("%Y-%m-%dT%H:%M:%SZ") if done else old.get("listed", "")
    # Written when a meeting changed, or twice a day for the "listed" time (download.yml saves a copy when a file changed).
    stale = not old.get("listed") or (NOW - datetime.fromisoformat(old["listed"].replace("Z", "+00:00"))).total_seconds() > 12 * 3600
    if meets != old.get("meetings") or (done and stale):
        tmp = PATH + ".tmp"
        with open(tmp, "w") as f:
            json.dump({"congress": congress, "listed": listed_at, "meetings": meets}, f, indent=0, sort_keys=True)
        os.replace(tmp, PATH)
    soon = [m for m in meets.values() if m["date"] >= NOW.strftime("%Y-%m-%dT%H:%M") and m["bills"]
            and not re.search(r"cancel|postpon", m["status"], re.I)]
    print(f"committee meetings: {read} read this run, {len(meets)} kept; {len(soon)} still to come name bills"
          + ("" if done else " (more to read next run)"))


if __name__ == "__main__":
    main()
