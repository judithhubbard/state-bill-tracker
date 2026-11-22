#!/usr/bin/env python3
"""Download Oregon's legislative data from the Legislature's OData API (https://api.oregonlegislature.gov/odata/
odataservice.svc/; see the state-survey-2026-10-31 memory): for each regular session, the tables the site uses, into
data/or/<session key>/<table>.json. One request at a time; the API pages long tables (odata.nextLink).
Usage: python3 states/or/fetch.py [first_year]   (default: four years back)
"""
import json, os, re, sys, time, urllib.error, urllib.parse, urllib.request
from datetime import date

API = "https://api.oregonlegislature.gov/odata/odataservice.svc"
DATA = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "or"))
AGENT = "statebilltracker.org (a nonprofit bill tracker; contact via github.com/judithhubbard)"
TABLES = ["Measures", "MeasureHistoryActions", "MeasureSponsors", "MeasureVotes", "CommitteeVotes", "MeasureDocuments",
          "MeasureAnalysisDocuments", "Committees", "CommitteeMembers", "CommitteeMeetings", "CommitteeAgendaItems",
          "Legislators", "LegislativeSessions", "FloorSessionAgendaItems"]  # (the last: floor calendars, 2026-11-22)
# Two sessions of each kind (long in odd years, short in even ones), so each is compared with past ones like it.
FIRST = int(sys.argv[1]) if len(sys.argv) > 1 else date.today().year - 4


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
    # From November, next year's session too, once the API lists a measure for it (pre-session filed measures appear
    # in late December: 2025's on 2024-12-31); until then one small request a run, and no folder (the converter
    # would show it as a session).
    today = date.today()
    for year in list(range(FIRST, today.year + 1)) + ([today.year + 1] if today.month >= 11 else []):
        session = f"{year}R1"
        folder = os.path.join(DATA, session)
        if year > today.year and not os.path.exists(os.path.join(folder, "Measures.json")):
            probe = get(f"{API}/Measures?" + urllib.parse.urlencode(
                {"$filter": f"SessionKey eq '{session}'", "$top": "1", "$select": "MeasureNumber", "$format": "json"}))
            if not (probe or {}).get("value"):
                print(f"{session}: no measures filed yet")
                continue
        os.makedirs(folder, exist_ok=True)
        # A session two or more years back is finished: read once.
        # (A table added later, FloorSessionAgendaItems, is read once for such a session, without the others again.)
        done = year < date.today().year - 1
        if done and all(os.path.exists(os.path.join(folder, f"{t}.json")) for t in TABLES):
            continue
        for name in TABLES:
            if done and os.path.exists(os.path.join(folder, f"{name}.json")):
                continue
            rows = table(name, session)
            if rows is None:
                print(f"{session} {name}: failed")
                continue
            json.dump(rows, open(os.path.join(folder, f"{name}.json"), "w"))
            print(f"{session} {name}: {len(rows)} rows", flush=True)


# The Governor's veto letters (scans: OCR). Kotek's 2023 letters to the Secretary of State are one PDF, linked from her
# newsroom post of 2023-08-04 ("Governor Kotek Issues Final Decision on Vetoes, Signing Letters"); from 2025 each veto
# has its own, under one of two names (SB302_Veto_Letter.pdf, SB-976_Veto_Letter.pdf). 2024 had no vetoes.
GOV_DOCS = "https://www.oregon.gov/gov/Documents/"
COMPILATIONS = {"2023R1": GOV_DOCS + "2023_Bill_Letters.pdf"}


def get_pdf(url):
    """A PDF's bytes; None when it isn't there (404) or can't be read. Two seconds between requests."""
    time.sleep(2)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": AGENT})
        with urllib.request.urlopen(req, timeout=180) as r:
            body = r.read()
        return body if body[:5] == b"%PDF-" else None
    except (urllib.error.URLError, OSError):
        return None


def vetoed(folder):
    """The session's vetoed (or line-item vetoed) measures: ["SB302", ...], from the saved tables."""
    try:
        measures = json.load(open(os.path.join(folder, "Measures.json")))
        hist = json.load(open(os.path.join(folder, "MeasureHistoryActions.json")))
    except (OSError, ValueError):
        return []
    out = {f"{m['MeasurePrefix']}{m['MeasureNumber']}" for m in measures if m.get("Vetoed")}
    out |= {f"{h['MeasurePrefix']}{h['MeasureNumber']}" for h in hist
            if re.match(r"Governor (?:vetoed|signed with line-item veto)", h.get("ActionText") or "", re.I)}
    return sorted(out)


def veto_letters(minutes=8):
    """Each vetoed measure's veto letter, read once by OCR (states/letters.py) into <session>/vetoes/<SB302>.json, or a
    session's compilation into vetoes/_letters.json (convert.py picks each bill's letter by its "Re:" line). A measure
    whose letter isn't at either name is asked again a week later (vetoes/asked.json). At most `minutes` a run."""
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
    from states import letters as L
    if not L.ocr_ready():
        print("veto letters: pdftoppm or tesseract isn't installed", flush=True)
        return
    stop_at = time.time() + minutes * 60
    today = date.today().isoformat()
    week = date.fromordinal(date.today().toordinal() - 7).isoformat()
    for session in sorted(os.listdir(DATA)):
        folder = os.path.join(DATA, session)
        if not re.fullmatch(r"\d{4}R1", session) or not os.path.isdir(folder):
            continue
        out = os.path.join(folder, "vetoes")
        if session in COMPILATIONS:
            if not os.path.exists(os.path.join(out, "_letters.json")) and time.time() < stop_at:
                data = get_pdf(COMPILATIONS[session])
                raw = L.ocr_pdf(data, pages=60) if data else None
                if raw:
                    os.makedirs(out, exist_ok=True)
                    json.dump({"url": COMPILATIONS[session], "ocr": True, "raw": raw, "engine": L.ocr_engine(), "read": today},
                              open(os.path.join(out, "_letters.json"), "w"), ensure_ascii=False)
            continue
        asked_path = os.path.join(out, "asked.json")
        try:
            asked = json.load(open(asked_path))
        except (OSError, ValueError):
            asked = {}
        got = 0
        todo = [k for k in vetoed(folder) if not os.path.exists(os.path.join(out, f"{k}.json")) and asked.get(k, "") < week]
        for k in todo:
            if time.time() > stop_at:
                break
            pre, num = re.fullmatch(r"([A-Z]+)(\d+)", k).groups()
            for url in (f"{GOV_DOCS}{pre}{num}_Veto_Letter.pdf", f"{GOV_DOCS}{pre}-{num}_Veto_Letter.pdf"):
                data = get_pdf(url)
                if data:
                    break
            if not data:
                os.makedirs(out, exist_ok=True)
                asked[k] = today
                json.dump(asked, open(asked_path, "w"))
                continue
            if L.scanned(out, k, url, lambda u: data):
                got += 1
        print(f"{session}: veto letters: {got} of {len(todo)} read now", flush=True)


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
    try:
        veto_letters()
    except Exception as e:  # never holds Oregon back
        print(f"veto letters: failed ({type(e).__name__})", flush=True)
    import importlib
    importlib.import_module("states.or.contacts").main(date.today().year)
