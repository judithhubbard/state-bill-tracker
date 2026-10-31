#!/usr/bin/env python3
"""Download Oregon's legislative data from the Legislature's OData API (https://api.oregonlegislature.gov/odata/
odataservice.svc/; see the state-survey-2026-10-31 memory): for each regular session, the tables the site uses, into
data/or/<session key>/<table>.json. One request at a time; the API pages long tables (odata.nextLink).
Usage: python3 states/or/fetch.py [first_year]   (default: two years back)
"""
import json, os, sys, time, urllib.parse, urllib.request
from datetime import date

API = "https://api.oregonlegislature.gov/odata/odataservice.svc"
DATA = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "or"))
AGENT = "statebilltracker.org (a nonprofit bill tracker; contact via github.com/judithhubbard)"
TABLES = ["Measures", "MeasureHistoryActions", "MeasureSponsors", "MeasureVotes", "CommitteeVotes", "MeasureDocuments",
          "MeasureAnalysisDocuments", "Committees", "CommitteeMembers", "CommitteeMeetings", "CommitteeAgendaItems",
          "Legislators", "LegislativeSessions"]
FIRST = int(sys.argv[1]) if len(sys.argv) > 1 else date.today().year - 2


def get(url):
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": AGENT, "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=300) as r:
                return json.loads(r.read())
        except Exception:
            time.sleep(10 * (attempt + 1))
    return None


def table(name, session):
    url = f"{API}/{name}?" + urllib.parse.urlencode({"$filter": f"SessionKey eq '{session}'", "$format": "json"})
    rows = []
    while url:
        page = get(url)
        if page is None:
            return None
        rows += page.get("value", [])
        url = page.get("odata.nextLink") or page.get("@odata.nextLink")
        if url and not url.startswith("http"):
            url = f"{API}/{url}"
    return rows


def main():
    for year in range(FIRST, date.today().year + 1):
        session = f"{year}R1"
        folder = os.path.join(DATA, session)
        os.makedirs(folder, exist_ok=True)
        for name in TABLES:
            rows = table(name, session)
            if rows is None:
                print(f"{session} {name}: failed")
                continue
            json.dump(rows, open(os.path.join(folder, f"{name}.json"), "w"))
            print(f"{session} {name}: {len(rows)} rows", flush=True)


def texts():
    """"What it does": each bill's plain-language digest, as data/or/texts_<year>.json."""
    import importlib
    C = importlib.import_module("states.or.convert")
    for y in C.sessions():
        out = {}
        for m in C.table(y, "Measures"):
            d = C.digest(m.get("MeasureSummary"))
            if C.wanted(m) and d:
                out[f"{m['MeasurePrefix']}{m['MeasureNumber']}"] = {"statement": d, "label": "From the bill's digest."}
        json.dump(out, open(os.path.join(DATA, f"texts_{y}.json"), "w"), ensure_ascii=False)
        print(f"texts_{y}.json: {len(out)} digests")


if __name__ == "__main__":
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
    main()
    texts()
    import importlib
    importlib.import_module("states.or.contacts").main(date.today().year)
