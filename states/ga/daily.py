#!/usr/bin/env python3
"""When Georgia House committees meet, and the bills on their agendas, from the House Budget & Research Office's
Daily Report (states/ga/NOTES.md, "Committee agendas").

The meeting schedule itself is on www.legis.ga.gov behind a token its script makes from a hidden key: never used. The
Daily Report is a public PDF on the same server's document path (no token), one for each legislative day, posted that
afternoon or evening. Its last page, "Committee Meeting Schedule", lists the House's meetings of the next day, each with
a link to its agenda PDF (also a public document) when the committee posted one. The report's first page says when the
House meets next ("The House will reconvene for its 25th Legislative Day on Thursday, February 26"), so the next report's
address is known but for its spelling: <folder>/ld25_thu_feb_26_2026.pdf (2026; 2025 wrote "thurs", "march", "feb_3").
There's no listing to read: the office's page on www.legis.ga.gov is drawn from the gated API.

Requests a run (2 seconds apart, a plain User-Agent): during the regular session (January to mid-April), the next report's
likely spellings until one answers (at most MAX_TRIES a run; once found, the next isn't due until its own day), and
each agenda it links (again while the meeting is ahead, at most every AGAIN hours). Nothing else on the server is read.

Writes data/ga/<session>/daily.json: {"year", "folder", "style", "next": [ld, "YYYY-MM-DD"], "reports": {file:
{"ld", "date", "next", "meetings": [[name, "YYYY-MM-DDTHH:MM:00", agenda_url or ""], ...]}}, "agendas": {url: {"bills":
["HB7", ...], "read": iso time, "failed": bool}}}. convert.py's agendas() reads it.

Usage (a test): python3 states/ga/daily.py <report.pdf>   prints what a report says.
"""
import json, os, re, subprocess, sys, tempfile, time, urllib.error, urllib.request
from datetime import date, datetime, timedelta
from html import unescape
from zoneinfo import ZoneInfo

DOCS = "https://www.legis.ga.gov/api/document/docs/default-source/house-budget-and-research-office-document-library/"
AGENDAS = "https://www.legis.ga.gov/api/document/agendas/"
AGENT = "statebilltracker.org (a nonprofit bill tracker; contact via github.com/judithhubbard)"
TZ = ZoneInfo("America/New_York")
MAX_TRIES = 8   # report addresses tried a run
AGAIN = 6       # hours before an upcoming meeting's agenda is read again (agendas change)
DOW = [["mon"], ["tue", "tues"], ["wed"], ["thu", "thurs", "thur"], ["fri"], ["sat"], ["sun"]]
MON = ["jan", "feb", "mar", "apr", "may", "june", "july", "aug", "sep", "oct", "nov", "dec"]
FULL = ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november",
        "december"]
REQUESTS = [0]


class Unreachable(Exception):
    """The server didn't answer at all (on 2026-11-22 www.legis.ga.gov timed out from GitHub's runners): stop the run's
    requests rather than wait on each."""


def get(url):
    """A document's bytes, or None (the server answers a missing document with a 200 HTML page, so only a PDF counts)."""
    REQUESTS[0] += 1
    time.sleep(2)
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": AGENT}), timeout=30) as r:
            body = r.read()
    except urllib.error.HTTPError:
        return None
    except OSError as e:  # (URLError, timeouts, refused connections)
        raise Unreachable(repr(e))
    return body if body[:5] == b"%PDF-" else None


def folders(year, known=None):
    """The year's report folder: "2026-daily-report" in 2026, "daily-report-2025" before."""
    return [known] if known else [f"{year}-daily-report", f"daily-report-{year}"]


def names(ld, day, style=None):
    """A report's likely file names, the spelling last seen first: ld24_wed_feb_25_2026.pdf. style is
    {"dow": "thurs", "mon": "march" or "", "pad": True}."""
    style = style or {}
    dows = DOW[day.weekday()]
    dows = sorted(dows, key=lambda d: (d != style.get("dow"), dows.index(d)))
    mons = list(dict.fromkeys([MON[day.month - 1], FULL[day.month - 1]]))
    pads = [style.get("pad", True), not style.get("pad", True)]
    out = []
    for pad in pads:
        for dw in dows:
            for mo in mons:
                dd = f"{day.day:02d}" if pad else str(day.day)
                out.append(f"ld{ld:02d}_{dw}_{mo}_{dd}_{day.year}.pdf")
    if ld == 1:
        out.append(f"{day.year}-daily-report-ld-1.pdf")  # 2025's first two
    return list(dict.fromkeys(out))


def style_of(name, old=None):
    """The spelling a found name shows; only a day under 10 shows the padding."""
    m = re.match(r"ld\d+_([a-z]+)_([a-z]+)_(\d+)_\d{4}\.pdf$", name)
    out = dict(old or {})
    if m:
        out["dow"] = m[1]
        if int(m[3]) < 10:
            out["pad"] = m[3].startswith("0")
    return out


def pdftext(body, layout=True):
    with tempfile.NamedTemporaryFile(suffix=".pdf") as f:
        f.write(body)
        f.flush()
        return subprocess.run(["pdftotext"] + (["-layout"] if layout else []) + [f.name, "-"],
                              capture_output=True, text=True, errors="replace").stdout


def next_day(text, year):
    """The report's "The House will reconvene for its 25th Legislative Day on Thursday, February 26" -> (25, date)."""
    m = re.search(r"reconvene for its (\d+)\s*(?:st|nd|rd|th)\s+Legislative\s+Day\s+on\s+\w+,?\s+([A-Za-z]+)\.?\s+(\d+)",
                  re.sub(r"\s+", " ", text))
    if not m:
        return None
    mon = next((i + 1 for i, f in enumerate(FULL) if f.startswith(m[2][:3].lower())), None)
    return (int(m[1]), date(year, mon, int(m[3]))) if mon else None


def schedule(body):
    """The "Committee Meeting Schedule" rows: [[name, "YYYY-MM-DDTHH:MM:00", agenda url or ""], ...]. Read with
    pdftohtml -xml, which keeps each piece of text's place on the page and its links: a row starts at a "02/26/2026 8:00"
    text; the name is the texts in the name column down to the next row; the agenda is a link into /api/document/agendas/
    on the row's line."""
    with tempfile.TemporaryDirectory() as d:
        src = os.path.join(d, "r.pdf")
        open(src, "wb").write(body)
        subprocess.run(["pdftohtml", "-xml", "-i", "-q", "-nodrm", src, os.path.join(d, "r")], capture_output=True)
        try:
            xml = open(os.path.join(d, "r.xml"), encoding="utf-8", errors="replace").read()
        except OSError:
            return []
    start = xml.find("Committee Meeting Schedule")
    if start < 0:
        return []
    out = []
    for page in re.split(r"<page ", xml[start:]):
        items = []
        for m in re.finditer(r'<text top="(\d+)" left="(\d+)"[^>]*>(.*?)</text>', page, re.S):
            top, left, inner = int(m[1]), int(m[2]), m[3]
            links = [unescape(h) for h in re.findall(r'href="([^"]+)"', inner)]
            items.append((top, left, unescape(re.sub(r"<[^>]+>", "", inner)).strip(), links))
        rows = [(t, l, s) for t, l, s, _ in items if re.match(r"\d\d/\d\d/\d{4}\s+\d", s)]
        rows.sort()
        for i, (top, left, s) in enumerate(rows):
            end = rows[i + 1][0] - 3 if i + 1 < len(rows) else 10 ** 6
            band = [x for x in items if top - 3 <= x[0] < end]
            line = [x for x in band if abs(x[0] - top) <= 3]
            # The name column starts right of the date and time; the room starts at about 3/4 of its width.
            name_left = min((x[1] for x in line if x[1] > left + 60), default=left + 160)
            room_left = min((x[1] for x in line if x[1] > name_left + 100 and x[2]), default=10 ** 6)
            name = " ".join(x[2] for x in sorted(band) if name_left - 5 <= x[1] < room_left - 5 and x[2])
            when = " ".join(x[2] for x in sorted(line, key=lambda x: x[1]) if x[1] < name_left)
            m = re.match(r"(\d\d)/(\d\d)/(\d{4})\s+(\d{1,2}):(\d\d)\s*([AP]M)?", when + " " + name)
            if not m:
                continue
            ampm = m[6] or (re.search(r"\b([AP]M)\b", name) or [None, ""])[1]
            name = re.sub(r"^\s*[AP]M\s+", "", name)
            hh = int(m[4]) % 12 + (12 if ampm == "PM" else 0)
            agenda = next((h for x in line for h in x[3] if h.startswith(AGENDAS)), "")
            name = re.sub(r"\s+", " ", re.sub(r"\bPage \d+ of \d+\b", "", name)).strip()
            if name and not re.match(r"CANCELL?ED\b", name, re.I):
                out.append([name, f"{m[3]}-{m[1]}-{m[2]}T{hh:02d}:{m[5]}:00", agenda])
    return out


def bills_in(text):
    """Bill numbers on an agenda: "HB 7 - Income tax ...", "SB 220", "H.B. 12", "HR 250 ... – CA" -> ["HB7", ...]."""
    out = []
    for m in re.finditer(r"\b([HS])\.?\s?([BR])\.?\s*(\d{1,4})\b", text):
        k = f"{m[1]}{m[2]}{int(m[3])}"
        if k not in out:
            out.append(k)
    return out


def house_only(name):
    """Rows for House meetings: "WAYS AND MEANS (House)"; the floor session isn't a committee."""
    return not re.search(r"FLOOR SESSION|\(Senate\)", name, re.I)


def read_report(body, year):
    text = pdftext(body)
    nd = next_day(text, year)
    rows = [r for r in schedule(body) if house_only(r[0])]
    return {"next": [nd[0], nd[1].isoformat()] if nd else None, "meetings": rows}


def run(folder, year, today=None):
    """One run's reading of the Daily Reports and their agendas; writes <folder>/daily.json."""
    now = datetime.now(TZ)
    today = today or now.date()
    path = os.path.join(folder, "daily.json")
    try:
        st = json.load(open(path))
    except (OSError, ValueError):
        st = {}
    if st.get("year") != year:
        st = {"year": year, "reports": {}, "agendas": {}}
    # The regular session: from the second Monday of January to mid-April.
    first = date(year, 1, 1 + (0 - date(year, 1, 1).weekday()) % 7 + 7)
    if not first <= today <= date(year, 4, 15):
        return st
    try:
        reports(st, year, first, today, now)
        agenda_pdfs(st, today, now)
    except Unreachable as e:
        print(f"daily report: www.legis.ga.gov didn't answer ({e}); kept the last copy", flush=True)
    json.dump(st, open(path + ".tmp", "w"), ensure_ascii=False, indent=0)
    os.replace(path + ".tmp", path)
    print(f"daily report: {REQUESTS[0]} requests", flush=True)
    return st


def reports(st, year, first, today, now):
    """The Daily Reports due since the last one found (st["next"]), each giving the next one's day."""
    ld, due = st.get("next") or [1, first.isoformat()]
    due = date.fromisoformat(due)
    tries = 0
    # Once the folder and spelling are known, the right name is nearly always the first: fewer tries.
    budget = MAX_TRIES if not st.get("folder") else MAX_TRIES // 2
    # A day's report is posted that afternoon or evening: not looked for before noon. One the House moved (weather, a
    # changed calendar) is looked for on later days too, the newest first.
    while (due < today or (due == today and now.hour >= 12)) and tries < budget:
        days = [due] + [today - timedelta(i) for i in range(3) if today - timedelta(i) > due and (today - timedelta(i)).weekday() < 5]
        found = None
        for day in days:
            for fold in folders(year, st.get("folder")):
                for name in names(ld, day, st.get("style")):
                    if tries >= budget:
                        break
                    tries += 1
                    body = get(DOCS + fold + "/" + name)
                    if body:
                        found = (fold, name, day, body)
                        break
                if found or tries >= budget:
                    break
            if found or tries >= budget:
                break
        if not found:
            break
        fold, name, day, body = found
        rep = read_report(body, year)
        st["folder"], st["style"] = fold, style_of(name, st.get("style"))
        st["reports"][name] = {"ld": ld, "date": day.isoformat(), **rep}
        print(f"daily report: {name}: {len(rep['meetings'])} meetings", flush=True)
        if not rep["next"]:
            st["next"] = [ld + 1, (day + timedelta(1)).isoformat()]
            break
        st["next"] = rep["next"]
        ld, due = rep["next"][0], date.fromisoformat(rep["next"][1])


def agenda_pdfs(st, today, now):
    """Agendas of meetings today or later: read once, and again every AGAIN hours until the meeting."""
    ahead = {r[2] for rep in st["reports"].values() for r in rep["meetings"] if r[2] and r[1][:10] >= today.isoformat()}
    for url in sorted(ahead):
        old = st["agendas"].get(url)
        if old and not old.get("failed") and now - datetime.fromisoformat(old["read"]) < timedelta(hours=AGAIN):
            continue
        body = get(url)
        if body:
            st["agendas"][url] = {"bills": bills_in(pdftext(body)), "read": now.isoformat(timespec="seconds")}
        elif not old or old.get("failed"):
            st["agendas"][url] = {"bills": [], "read": now.isoformat(timespec="seconds"), "failed": True}


if __name__ == "__main__":
    body = open(sys.argv[1], "rb").read()
    yr = int(re.search(r"(20\d\d)", os.path.basename(sys.argv[1]))[1])
    rep = read_report(body, yr)
    print("next:", rep["next"])
    for r in rep["meetings"]:
        print(r)
