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
import glob, html, json, os, re, shutil, subprocess, sys, time, urllib.error, urllib.request
from datetime import date, timedelta

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


AGENDA_LIMIT = 14 * 60  # agenda PDFs read in one run: about 7 (the listing takes one request too)


def agenda_rows(listing):
    """The standing committees' agendas (/standing-committee) -> [{"day", "committee", "id", "revised", "cancelled",
    "time", "pdf"}], one row per meeting: "03 - 24 - 2026", the committee's name and id, the Revised and Cancelled
    check boxes, "2:00 P.M. or upon recess or adjournment of Floor" (or "CANCELLED"), /agendas/0324012170130.pdf."""
    out = []
    for row in re.findall(r"<tr[^>]*>(<td>\d\d - \d\d - \d{4}</td\s*>.*?)</tr>", listing, re.S):
        cells = re.findall(r"<td[^>]*>(.*?)</td\s*>", row, re.S)
        pdf = re.search(r"href=\"?(/agendas/[\w.-]+\.pdf)", row, re.I)
        if len(cells) < 7 or not pdf:
            continue
        m, d, y = re.findall(r"\d+", cells[0])[:3]
        name = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", cells[1]))).strip()
        cid = re.search(r"committeeId=(\d+)", cells[1])
        when = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", cells[4]))).strip()
        out.append({"day": f"{y}-{m}-{d}", "committee": name, "id": cid.group(1) if cid else "",
                    "revised": "Revised" in cells[2], "cancelled": "Cancelled" in cells[3] or when.upper().startswith("CANCEL"),
                    "time": when, "pdf": pdf.group(1)})
    return out


def agenda_bills(text):
    """An agenda PDF's text (pdftotext -layout) -> (house, [bill numbers]). The heading names the house ("ARIZONA HOUSE OF
    REPRESENTATIVES", "ARIZONA STATE SENATE"); each bill heads its row ("HB2313", "SCR1001")."""
    head = text[:1500].upper()
    house = "House" if "HOUSE OF REPRESENTATIVES" in head else "Senate" if "SENATE" in head else ""
    bills = []
    for kind, n in re.findall(r"(?m)^\s*(HB|SB|HCR|SCR|HJR|SJR|HCM|SCM|HR|SR)\s?(\d{4})\b", text):
        if f"{kind}{n}" not in bills:
            bills.append(f"{kind}{n}")
    return house, bills


def clock(when):
    """"2:00 P.M. or upon recess ..." -> "14:00:00"; no time -> "00:00:00"."""
    t = re.match(r"(\d+):(\d\d)\s*([AP])\.?\s*M", when or "", re.I)
    if not t:
        return "00:00:00"
    return f"{int(t.group(1)) % 12 + (12 if t.group(3).upper() == 'P' else 0):02d}:{t.group(2)}:00"


def agendas():
    """Bills on standing committee agendas from yesterday to three weeks ahead, into data/az/<year>/agendas.json: bill ->
    [["House Education", "2026-02-17T14:00:00"], ...]. The list of every standing committee's agendas
    (/standing-committee, one request a run) names each meeting's day, time, Cancelled box and agenda PDF
    (/agendas/<...>.pdf, on www.azleg.gov, which robots.txt allows; apps.azleg.gov isn't read). Each PDF is read with
    pdftotext and kept as text in data/az/azleg/agendas/: once, again when the list shows it revised or with a new time,
    and again after twelve hours while the meeting is ahead (revisions keep the address). At the crawl delay only a few
    PDFs fit in a run (AGENDA_LIMIT), the soonest unread first. A failure keeps the last files."""
    started = time.time()
    folder = os.path.join(DATA, "agendas")
    os.makedirs(folder, exist_ok=True)
    seen_path = os.path.join(folder, "read.json")
    try:
        seen = json.load(open(seen_path))
    except (OSError, ValueError):
        seen = {}
    listing = get("/standing-committee")
    if not listing:
        print("azleg.gov: agenda list unreadable; kept the last agendas", flush=True)
        return
    today = date.today()
    first, last = (today - timedelta(days=1)).isoformat(), (today + timedelta(days=21)).isoformat()
    rows = [r for r in agenda_rows(listing) if first <= r["day"] <= last and not r["cancelled"]]

    def text_path(r):
        return os.path.join(folder, os.path.basename(r["pdf"]) + ".txt")

    def need(r):
        k = seen.get(r["pdf"])
        if not k or not os.path.exists(text_path(r)):
            return (0, r["day"])
        if k.get("revised") != r["revised"] or k.get("time") != r["time"]:
            return (1, r["day"])
        if r["day"] >= today.isoformat() and time.time() - k.get("read", 0) > 12 * 3600:
            return (2, str(k.get("read", 0)))
        return None

    todo = []
    if shutil.which("pdftotext"):
        todo = sorted((need(r), r["pdf"], r) for r in rows if need(r))
    else:
        print("azleg.gov: no pdftotext; agendas not read", flush=True)
    read = 0
    for _, _, r in todo:
        if time.time() - started + DELAY > AGENDA_LIMIT:
            break
        wait = _last[0] + DELAY - time.time()
        if wait > 0:
            time.sleep(wait)
        _last[0] = time.time()
        try:
            with urllib.request.urlopen(urllib.request.Request(SITE + r["pdf"], headers={"User-Agent": AGENT}), timeout=120) as resp:
                body = resp.read()
            txt = subprocess.run(["pdftotext", "-layout", "-", "-"], input=body, capture_output=True, timeout=60).stdout
            txt = txt.decode("utf-8", "replace")
        except Exception as e:
            print(f"{r['pdf']}: {e}", flush=True)
            continue
        if not txt.strip():
            continue
        open(text_path(r) + ".tmp", "w", encoding="utf-8").write(txt)
        os.replace(text_path(r) + ".tmp", text_path(r))
        seen[r["pdf"]] = {"read": int(time.time()), "revised": r["revised"], "time": r["time"]}
        read += 1
    seen = {k: v for k, v in seen.items() if time.time() - v.get("read", 0) < 60 * 86400}
    json.dump(seen, open(seen_path + ".tmp", "w"), indent=0, sort_keys=True)
    os.replace(seen_path + ".tmp", seen_path)
    for f in glob.glob(os.path.join(folder, "*.pdf.txt")):  # texts of agendas no longer listed or read
        if time.time() - os.path.getmtime(f) > 60 * 86400:
            os.remove(f)
    by_year, n = {}, 0
    for r in rows:
        if not os.path.exists(text_path(r)):
            continue
        house, bills = agenda_bills(open(text_path(r), encoding="utf-8").read())
        name = r["committee"] if r["committee"].startswith("Joint") else f"{house or 'Joint'} {r['committee']}"
        entry = [name, f"{r['day']}T{clock(r['time'])}"]
        n += 1
        out = by_year.setdefault(int(r["day"][:4]), {})
        for b in bills:
            if entry not in out.setdefault(b, []):
                out[b].append(entry)
    for y in sorted(set(by_year) | {today.year}):
        ydir = os.path.join(os.path.dirname(DATA), str(y))
        os.makedirs(ydir, exist_ok=True)
        path = os.path.join(ydir, "agendas.json")
        json.dump(by_year.get(y, {}), open(path + ".tmp", "w"), ensure_ascii=False)
        os.replace(path + ".tmp", path)
    left = len(todo) - read
    print(f"azleg.gov: agendas: {sum(len(v) for v in by_year.values())} bills on {n} of {len(rows)} meetings ahead; "
          f"{read} PDFs read now" + (f", {left} left for later runs" if left > 0 else ""), flush=True)


def main():
    os.makedirs(DATA, exist_ok=True)
    try:  # the agendas first: they change daily in session, and the weekly committee pages could use up the run
        agendas()
    except Exception as e:  # never breaks the run
        print(f"azleg.gov: agendas failed ({type(e).__name__}); kept the last files", flush=True)
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
