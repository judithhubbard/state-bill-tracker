#!/usr/bin/env python3
"""The District's acts and laws from the Council's own law library in XML, github.com/DCCouncil/law-xml (the source of
code.dccouncil.gov; public, no key; GitHub isn't covered by LIMS's robots.txt). LegiScan's records of a Council Period stop
a few weeks after it ends (the 25th Council's at the end of January 2025), before the last acts' Congressional review
ends, and its law lines can lag: this file is how a law's number and effective date are known.

Each Council Period's folder (us/dc/council/periods/<period>/) has laws/<period>-<n>.xml and acts/<period>-<n>.xml, one
file per law and per act, whose head names the law, act and bill numbers ("<num type="bill">25-196</num>"), the short and
long titles, the effective date (laws), whether it's temporary, and the history (readings, the day it was enacted). Two
listings a run (GitHub's contents API: each file's sha), then only files new or changed since the last run, a quarter of a
second apart (raw.githubusercontent.com): about 900 files the first time, a few a week after. Kept in data/dc/lawxml/
<period>/<kind>/<n>.xml (the head only, up to the first <section>), and data/dc/laws_<first year>.json: {"B25-0196": {"law":
"25-234", "act": "25-590", "effective": "2024-12-17", "enacted": "2024-10-24", "temporary": false, "long": "To designate
..."}}. Read at most once every 20 hours. A failed listing keeps the last copy. Usage: python3 states/dc/laws.py
"""
import json, os, re, sys, time, urllib.error, urllib.request
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
from states import window as W
from states.dc import profile as P

API = "https://api.github.com/repos/DCCouncil/law-xml/contents/us/dc/council/periods/{period}/{kind}"
RAW = "https://raw.githubusercontent.com/DCCouncil/law-xml/main/us/dc/council/periods/{period}/{kind}/{name}"
AGENT = "statebilltracker.org (a nonprofit bill tracker; contact via github.com/judithhubbard)"
FOLDER = os.path.join(P.DATA, "lawxml")
EVERY = 20 * 3600


def get(url, api=False):
    headers = {"User-Agent": AGENT}
    if api:
        # (No token: GitHub's unauthenticated limit, 60 listings an hour, is far more than the few a day this needs.)
        headers["Accept"] = "application/vnd.github+json"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def head(xml):
    """The file up to its first section: the numbers, titles and dates (the text itself isn't needed)."""
    cut = xml.find("<section")
    return xml if cut < 0 else xml[:cut] + "</document>"


def field(xml, pattern):
    m = re.search(pattern, xml, re.S)
    return re.sub(r"\s+", " ", m.group(1)).strip() if m else ""


def parse(xml):
    import html
    one = lambda p: html.unescape(field(xml, p))
    return {"law": one(r'<num type="law">([^<]+)</num>'), "act": one(r'<num type="act">([^<]+)</num>'),
            "bill": one(r'<num type="bill">([^<]+)</num>'), "short": one(r'<heading type="short">(.*?)</heading>'),
            "long": one(r'<heading type="long">(.*?)</heading>'), "effective": one(r"<effective>([^<]+)</effective>"),
            "enacted": one(r"<enacted>([^<]+)</enacted>"), "temporary": "<temporary/>" in xml,
            "emergency": "<emergency/>" in xml}


def bill_key(n):
    """"25-196" -> "B25-0196"."""
    m = re.match(r"(\d+)-0*(\d+)$", n or "")
    return f"B{m.group(1)}-{int(m.group(2)):04d}" if m else ""


def refresh(period):
    """Bring one period's files up to date. Returns the number read, or None when a listing failed."""
    folder = os.path.join(FOLDER, str(period))
    state_path = os.path.join(folder, "shas.json")
    try:
        shas = json.load(open(state_path))
    except (OSError, ValueError):
        shas = {}
    read = 0
    for kind in ("laws", "acts"):
        try:
            listing = json.loads(get(API.format(period=period, kind=kind), api=True))
        except urllib.error.HTTPError as e:
            if e.code == 404:
                continue  # (a new period has no acts yet)
            print(f"  {period} {kind}: listing failed (HTTP {e.code}); kept the last copy", flush=True)
            return None
        except (OSError, ValueError) as e:
            print(f"  {period} {kind}: listing failed ({e.__class__.__name__}); kept the last copy", flush=True)
            return None
        os.makedirs(os.path.join(folder, kind), exist_ok=True)
        for f in listing:
            name = f.get("name") or ""
            key = f"{kind}/{name}"
            if not name.endswith(".xml") or shas.get(key) == f.get("sha") and os.path.exists(os.path.join(folder, key)):
                continue
            try:
                xml = get(RAW.format(period=period, kind=kind, name=name)).decode("utf-8")
            except (OSError, ValueError) as e:
                print(f"  {key}: {e.__class__.__name__}; tried again next run", flush=True)
                continue
            with open(os.path.join(folder, key), "w", encoding="utf-8") as out:
                out.write(head(xml))
            shas[key] = f.get("sha")
            read += 1
            time.sleep(0.25)
            if read % 100 == 0:
                json.dump(shas, open(state_path, "w"), indent=0)
    json.dump(shas, open(state_path, "w"), indent=0)
    return read


def table(period):
    """{"B25-0196": {...}} from the saved files: a law's entry wins over its act's."""
    folder = os.path.join(FOLDER, str(period))
    out = {}
    for kind in ("acts", "laws"):
        d = os.path.join(folder, kind)
        for name in sorted(os.listdir(d)) if os.path.isdir(d) else []:
            if not name.endswith(".xml"):
                continue
            x = parse(open(os.path.join(d, name), encoding="utf-8").read())
            k = bill_key(x["bill"])
            if not k:
                continue
            e = out.setdefault(k, {})
            for f in ("law", "act", "effective", "enacted", "long", "short"):
                if x[f] and (kind == "laws" or not e.get(f)):
                    e[f] = x[f]
            e["temporary"] = e.get("temporary") or x["temporary"]
    return out


def main():
    stamp = os.path.join(FOLDER, "last_read")
    if os.path.exists(stamp) and time.time() - os.path.getmtime(stamp) < EVERY and "--now" not in sys.argv:
        print("DC laws: read within 20 hours; skipped")
        return
    first = W.first_session()
    sessions = list(range(first, date.today().year + 1, 2))
    ok = True
    for s in sessions:
        period = P.period_of(s)
        n = refresh(period)
        ok = ok and n is not None
        t = table(period)
        if t:
            json.dump(t, open(os.path.join(P.DATA, f"laws_{s}.json"), "w"), indent=0, ensure_ascii=False, sort_keys=True)
        print(f"DC Council Period {period}: {n if n is not None else 'no'} files read; {sum(1 for e in t.values() if e.get('law'))} laws,"
              f" {sum(1 for e in t.values() if e.get('act'))} acts", flush=True)
    if ok:
        os.makedirs(FOLDER, exist_ok=True)
        open(stamp, "w").write(date.today().isoformat() + "\n")


if __name__ == "__main__":
    main()
