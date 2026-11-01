#!/usr/bin/env python3
"""Arizona's committees and legislators' phones from www.azleg.gov, the pages its robots.txt allows, at its crawl delay of
one request every 120 seconds (apps.azleg.gov, which the site's own pages read their data from, is "Disallow: /").
Fills what Open States lacks (the owner's decision 2026-10-31): committee chairs and members, and Capitol phones.

Saves each page as it was into data/az/azleg/ (the standing committees list, each committee's page, the member rosters),
re-read weekly; states/az/contacts.py parses them. About 40 pages, so a full pass takes about 80 minutes.

Then each concurrent resolution's official title, from its text (/legtext/<57leg>/<1R>/bills/HCR2001P.htm), into
data/az/azleg/resolutions.json, to tell the ones proposing constitutional amendments ("proposing an amendment to the
Constitution of Arizona") from referred laws ("enacting and ordering the submission to the people of a measure") and
the rest; Open States has only the short titles. Each is read once, and again after a strike-everything amendment
(DPA/SE), from the version the amending house passed. About 100 a year, so the first pass builds up over several runs
(it stops after RUN_LIMIT seconds, leaving time for the next step), those that went furthest first.
Usage: python3 states/az/azleg.py
"""
import glob, html, json, os, re, sys, time, urllib.error, urllib.request

SITE = "https://www.azleg.gov"
DATA = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "az", "azleg"))
AGENT = "statebilltracker.org (a nonprofit bill tracker; contact via github.com/judithhubbard)"
DELAY = 120  # robots.txt: Crawl-delay: 120
WEEK = 7 * 86400
RUN_LIMIT = 75 * 60  # GitHub gives this step 90 minutes
START = time.time()
_last = [0.0]
# Ceremonial resolutions, plain from their short titles; their texts aren't read.
CEREMONIAL = re.compile(r"death resolution|\bsupport(ing)?\b|recogniz|\bday$|anniversary|article v|ratification; equal rights|"
                        r"\bhonoring\b|commend|congratulat|\bweek$|\bmonth$|\bdesignat(ing|ion)\b.*\bday\b", re.I)


def get(path, missing=None):
    wait = _last[0] + DELAY - time.time()
    if wait > 0:
        time.sleep(wait)
    _last[0] = time.time()
    try:
        with urllib.request.urlopen(urllib.request.Request(SITE + path, headers={"User-Agent": AGENT}), timeout=120) as r:
            return r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        if e.code == 404 and missing is not None:
            missing.append(path)
        print(f"{path}: {e}", flush=True)
        return None
    except Exception as e:
        print(f"{path}: {e}", flush=True)
        return None


def keep(name, path, fresh=WEEK):
    """The page at `path`, saved as data/az/azleg/<name>.html; read again when older than `fresh`."""
    out = os.path.join(DATA, f"{name}.html")
    if os.path.exists(out) and time.time() - os.path.getmtime(out) < fresh:
        return open(out, encoding="utf-8").read()
    body = get(path)
    if body:
        open(out + ".tmp", "w", encoding="utf-8").write(body)
        os.replace(out + ".tmp", out)
        return body
    return open(out, encoding="utf-8").read() if os.path.exists(out) else ""


def official_title(body):
    """The resolution's title sentence ("A Concurrent Resolution proposing an amendment ..."), from its text page."""
    t = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", body)))
    # A few are drafted "AN ACT proposing an amendment ..." (SCR 1016 of 2026).
    m = re.search(r"\b((?:A Concurrent Resolution|AN ACT)\b.*?)(?:\(TEXT OF BILL BEGINS|Be it resolved\b)", t, re.I)
    return m.group(1).strip() if m else ""


def kind_of(title):
    if re.search(r"proposing (an )?amendments? to the Constitution of Arizona", title, re.I):
        return "amendment"
    if re.search(r"submission to the people (of )?a measure", title, re.I):
        return "measure"
    return "other"


def resolutions():
    path = os.path.join(DATA, "resolutions.json")
    try:
        known = json.load(open(path))
    except (OSError, ValueError):
        known = {}
    todo = []
    bills = os.path.join(os.path.dirname(DATA), "[0-9]" * 4, "bills")
    for f in glob.glob(os.path.join(bills, "[HS]CR*.json")):
        year = int(f.split(os.sep)[-3])
        b = json.load(open(f))
        num = b["identifier"].replace(" ", "")
        acts = b.get("actions") or []
        ses = sum(1 for a in acts if (a.get("description") or "").startswith("DPA/SE"))
        k = known.get(str(year), {}).get(num)
        # Read again after a strike-everything amendment, and a week after a read that found no title.
        retry = k and k.get("kind") == "unread" and time.time() - k.get("checked", 0) > 7 * 86400
        if (k and k.get("se", 0) == ses and not retry) or CEREMONIAL.search(b.get("title") or ""):
            continue
        # The version to read: as filed, or after a strike-everything amendment the one the amending house passed
        # (House engrossed "H", Senate engrossed "S").
        org = next((a["organization"]["classification"] for a in reversed(acts) if (a.get("description") or "").startswith("DPA/SE")), None)
        ver = {"lower": "H", "upper": "S"}.get(org, "P") if ses else "P"
        went = 2 if any("passage" in (a.get("classification") or []) for a in acts) else 1 if len(acts) > 2 else 0
        todo.append((-went, -year, num, year, ver, ses))
    todo.sort()
    done = 0
    for _, _, num, year, ver, ses in todo:
        if time.time() - START > RUN_LIMIT:
            break
        leg, reg = (year - 1913) // 2 + 1, "1R" if year % 2 else "2R"
        missing = []
        body = get(f"/legtext/{leg}leg/{reg}/bills/{num}{ver}.htm", missing)
        if body is None and missing and ver != "P":
            ver, missing = "P", []  # an amended version not posted (or named otherwise): the one as filed
            body = get(f"/legtext/{leg}leg/{reg}/bills/{num}{ver}.htm", missing)
        if body is None and not missing:
            continue  # a failed request: try again next run
        title = official_title(body or "")
        known.setdefault(str(year), {})[num] = {"title": title, "kind": kind_of(title) if title else "unread", "version": ver, "se": ses,
                                                "checked": int(time.time())}
        json.dump(known, open(path + ".tmp", "w"), indent=0, sort_keys=True)
        os.replace(path + ".tmp", path)
        done += 1
    print(f"azleg.gov: {done} resolution titles read, {len(todo) - done} left", flush=True)


def main():
    os.makedirs(DATA, exist_ok=True)
    for body in ("H", "S"):
        keep(f"roster_{body}", f"/memberroster/?body={body}")
    listing = keep("standing_committees", "/standing-committees/")
    ids = sorted(set(re.findall(r"standing-committee/\?committeeId=(\d+)", listing)))
    for i in ids:
        keep(f"committee_{i}", f"/standing-committee/?committeeId={i}")
    print(f"azleg.gov: {len(ids)} committees, rosters saved", flush=True)
    resolutions()


if __name__ == "__main__":
    main()
