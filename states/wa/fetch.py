#!/usr/bin/env python3
"""Download Washington's bills from the Legislature's web services (https://wslwebservices.leg.wa.gov/), which it
offers free "to all interested parties ... for their in-house applications" (see the wa-data-sources memory).

- Each biennium's bill list (LegislationService GetLegislationByYear, both years); only bills (House 1000s-4000s,
  Senate 5000s-8000s of type "B"), not resolutions, memorials or the governor's appointments.
- For each bill, into data/wa/<session>/bills/<HB1003>.json: every version's record (GetLegislation), its history
  (GetLegislativeStatusChangesByBillNumber) and, when the history shows a vote, its roll calls (GetRollCalls).
- A finished biennium is downloaded once. The current one asks which bills changed since the last run
  (GetLegislativeStatusChangesByDateRange) and downloads only those and new ones. Three requests at a time.
- The members (SponsorService GetSponsors) and committees, every run.
Usage: python3 states/wa/fetch.py [first_year]   (default 2021)
"""
import json, os, re, sys, time, urllib.parse, urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
from states.wa import profile as P

API = "https://wslwebservices.leg.wa.gov"
NS = "{http://WSLWebServices.leg.wa.gov/}"
FIRST = int(sys.argv[1]) if len(sys.argv) > 1 else 2021
TODAY = datetime.now(ZoneInfo(P.TIMEZONE)).date()
CURRENT = P.session_of(TODAY.year)
AGENT = "statebilltracker.org (a nonprofit bill tracker; contact via github.com/judithhubbard)"


def call(service, op, **params):
    """One web service call, as parsed XML; None after four failures."""
    url = f"{API}/{service}.asmx/{op}?{urllib.parse.urlencode(params)}"
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": AGENT})
            with urllib.request.urlopen(req, timeout=120) as r:
                return ET.fromstring(r.read())
        except Exception:
            time.sleep(5 * (attempt + 1))
    return None


def plain(el):
    """XML element -> dict/list/str, without the namespace."""
    kids = list(el)
    if not kids:
        return (el.text or "").strip()
    out = {}
    for k in kids:
        name = k.tag.replace(NS, "")
        val = plain(k)
        if name in out:
            out[name] = out[name] if isinstance(out[name], list) else [out[name]]
            out[name].append(val)
        else:
            out[name] = val
    return out


def rows(el):
    return [plain(k) for k in el] if el is not None else []


def key(info):
    """A bill's key, "HB1003" or "SB5001", from its record."""
    return ("HB" if info["OriginalAgency"] == "House" else "SB") + info["BillNumber"]


def bill_list(session):
    ids = {}
    for year in (session, session + 1):
        if year > TODAY.year:
            continue
        for info in rows(call("LegislationService", "GetLegislationByYear", year=year)):
            if info.get("ShortLegislationType", {}).get("ShortLegislationType") == "B" and info.get("BillNumber", "").isdigit():
                ids[key(info)] = info["BillNumber"]
    return ids


def sponsors(session, bill):
    """A bill's sponsors in order (the prime sponsor first), with member ids; None when the service didn't answer."""
    el = call("LegislationService", "GetSponsors", biennium=P.biennium(session), billId=f"{bill[:2]} {bill[2:]}")
    return None if el is None else rows(el)


def one(session, bill, number):
    """Download one bill's versions, history, sponsors and roll calls; True when done."""
    bien = P.biennium(session)
    leg = call("LegislationService", "GetLegislation", biennium=bien, billNumber=number)
    hist = call("LegislationService", "GetLegislativeStatusChangesByBillNumber", biennium=bien, billNumber=number,
                beginDate=f"{session - 1}-11-01", endDate=f"{session + 2}-01-31")
    if leg is None or hist is None:
        return False
    history = rows(hist)
    rolls = []
    if any("yeas" in (h.get("HistoryLine") or "").lower() for h in history):
        rc = call("LegislationService", "GetRollCalls", biennium=bien, billNumber=number)
        if rc is None:
            return False
        rolls = rows(rc)
    spons = sponsors(session, bill)
    if spons is None:
        return False
    out = {"versions": rows(leg), "history": history, "sponsors": spons, "rollCalls": rolls}
    path = os.path.join(P.DATA, str(session), "bills", f"{bill}.json")
    json.dump(out, open(path + ".tmp", "w"), ensure_ascii=False)
    os.replace(path + ".tmp", path)
    return True


def session(session):
    folder = os.path.join(P.DATA, str(session))
    os.makedirs(os.path.join(folder, "bills"), exist_ok=True)
    state_path = os.path.join(folder, "state.json")
    try:
        state = json.load(open(state_path))
    except (OSError, ValueError):
        state = {}
    ids = bill_list(session)
    if not ids:
        print(f"{session}: no bill list (the service didn't answer); kept the last copy")
        return
    have = {f[:-5] for f in os.listdir(os.path.join(folder, "bills")) if f.endswith(".json")}
    todo = set(ids) - have
    started = TODAY.isoformat()
    if session >= CURRENT - 2 and state.get("synced"):
        # Bills whose status changed since the last run (a day's overlap), plus any new ones.
        since = (date.fromisoformat(state["synced"]) - timedelta(days=1)).isoformat()
        changes = rows(call("LegislationService", "GetLegislativeStatusChangesByDateRange", biennium=P.biennium(session),
                            beginDate=since, endDate=(TODAY + timedelta(days=1)).isoformat()))
        for c in changes:
            m = re.match(r"(?:\d?E?\d?S?)(HB|SB) (\d+)", c.get("BillId", ""))
            if m and m.group(1) + m.group(2) in ids:
                todo.add(m.group(1) + m.group(2))
    elif session >= CURRENT - 2:
        # The first copy may take several runs: only the missing bills, then the change feed from the day it began.
        state.setdefault("began", started)
        started = state["began"]
    todo = sorted(todo)
    # Files from before sponsor lists were kept: add just those.
    folder_b = os.path.join(folder, "bills")
    for b in sorted(have - set(todo)):
        path = os.path.join(folder_b, f"{b}.json")
        d = json.load(open(path))
        if "sponsors" not in d:
            spons = sponsors(session, b)
            if spons is not None:
                d["sponsors"] = spons
                json.dump(d, open(path + ".tmp", "w"), ensure_ascii=False)
                os.replace(path + ".tmp", path)
    got = 0
    with ThreadPoolExecutor(3) as pool:
        for ok in pool.map(lambda b: one(session, b, ids[b]), todo):
            got += ok
    if got == len(todo):
        state["synced"] = started
    json.dump(state, open(state_path, "w"))
    missing = len(set(ids) - {f[:-5] for f in os.listdir(os.path.join(folder, "bills")) if f.endswith(".json")})
    if missing:
        INCOMPLETE.add(session)
    print(f"{session}: {got} of {len(todo)} bills downloaded, {len(ids)} listed")


def members(session):
    folder = os.path.join(P.DATA, str(session))
    os.makedirs(folder, exist_ok=True)
    bien = P.biennium(session)
    for name, (service, op, params) in {
        "sponsors.json": ("SponsorService", "GetSponsors", {"biennium": bien}),
        "committees.json": ("CommitteeService", "GetCommittees", {"biennium": bien}),
    }.items():
        el = call(service, op, **params)
        if el is not None and len(el):
            json.dump(rows(el), open(os.path.join(folder, name), "w"), ensure_ascii=False)


def agendas(session):
    """Bills on committee agendas from yesterday to three weeks ahead, into data/wa/<session>/agendas.json:
    bill -> [["House Housing", "2026-01-20T08:00:00"], ...]."""
    meets = rows(call("CommitteeMeetingService", "GetCommitteeMeetings", beginDate=(TODAY - timedelta(days=1)).isoformat(),
                      endDate=(TODAY + timedelta(days=21)).isoformat()))
    out = {}
    for m in meets:
        if m.get("Cancelled") == "true" or not m.get("AgendaId"):
            continue
        cs = (m.get("Committees") or {}).get("Committee") or []
        c = (cs if isinstance(cs, list) else [cs])[0] if cs else {}
        name = f"{m.get('Agency', '')} {c.get('Name', '')}".strip()
        for item in rows(call("CommitteeMeetingService", "GetCommitteeMeetingItems", agendaId=m["AgendaId"])):
            b = re.match(r"(?:\d?E?\d?S?)(HB|SB) (\d+)", item.get("BillId") or "")
            if b and [name, m.get("Date")] not in out.setdefault(b.group(1) + b.group(2), []):
                out[b.group(1) + b.group(2)].append([name, m.get("Date")])
    json.dump(out, open(os.path.join(P.DATA, str(session), "agendas.json"), "w"))
    print(f"agendas: {len(out)} bills on {len(meets)} meetings' agendas")


INCOMPLETE = set()


def main():
    for s in range(FIRST, CURRENT + 1, 2):
        members(s)
        session(s)
    agendas(CURRENT)
    # Until every biennium is fully downloaded, data/wa/incomplete tells build_site.sh and the checks to wait.
    marker = os.path.join(P.DATA, "incomplete")
    if INCOMPLETE:
        open(marker, "w").write(" ".join(map(str, sorted(INCOMPLETE))) + "\n")
        print(f"not complete yet: {sorted(INCOMPLETE)}")
    elif os.path.exists(marker):
        os.remove(marker)


if __name__ == "__main__":
    main()
    from states.wa import contacts  # the legislator list and committee pages, with the member list just downloaded
    contacts.main(CURRENT)
    from states.wa import texts  # "What it does": the current biennium's bill reports
    texts.main(CURRENT)
