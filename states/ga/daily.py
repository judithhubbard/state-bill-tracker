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
{"ld", "date", "next", "meetings": [[name, "YYYY-MM-DDTHH:MM:00", agenda_url or ""], ...], "summaries": {bill:
staff summary}}}, "agendas": {url: {"bills":
["HB7", ...], "read": iso time, "failed": bool}}}. convert.py's agendas() reads it.

Usage (a test): python3 states/ga/daily.py <report.pdf>   prints what a report says.
A past session's reports, once: python3 states/ga/daily.py --backfill <pdf folder> <session> <year> ... (summaries()).
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


ENTRY = re.compile(r"^ {1,8}((?:HB|SB|HR|SR)\s+\d+)\b")
SUMMARY = re.compile(r"^(\s*)Bill Summary:\s*(.*)$")
# What ends a summary: the entry's facts, the next entry, a committee's or section's heading.
STOP = re.compile(r"^\s*(?:Authored By:|Carried By:|Sponsored By:|Rule Applied:|House\s+Committee:|Committee Meeting Schedule)"
                  r"|^ {0,4}\S.*\bCommittee\s*$|^\s*(?:Today on the Floor|Next on the Floor|Committee Actions)\b")
FURNITURE = re.compile(r"^\s*(?:House of Representatives\s+Daily Report for|Page \d+ of \d+\s*$)")


def summaries(text):
    """The staff's "Bill Summary:" paragraphs: {"HB320": "HB 320 restricts ...\nThe bill ..."}. pdftotext -layout
    keeps the report's indents: a summary's first paragraph is indented like "Bill Summary:", and each later one
    further, so a line indented differently from the one before, after a line ending a sentence, starts a paragraph (a
    deeper line after one that doesn't end a sentence is the same sentence: "Board of" / "Elections and Registration.").
    The page's running head and number are skipped (a summary can run onto the next page). A bill in two sections of one
    report (reported, then on the floor) has one summary; the last is kept."""
    out = {}
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        m = ENTRY.match(lines[i])
        if not m:
            i += 1
            continue
        bill = re.sub(r"\s+", "", m[1])
        j = i + 1
        while j < len(lines) and j < i + 6 and not SUMMARY.match(lines[j]) and not ENTRY.match(lines[j]):
            j += 1
        sm = SUMMARY.match(lines[j]) if j < len(lines) else None
        if not sm:
            i = j if j > i else i + 1
            continue
        paras, cur, indent, prev = [], [sm[2].strip()], len(sm[1]), sm[2]
        k = j + 1
        while k < len(lines):
            ln = lines[k]
            if ENTRY.match(ln) or STOP.match(ln):
                break
            if FURNITURE.match(ln) or not ln.strip():
                k += 1
                continue
            ind = len(ln) - len(ln.lstrip())
            ends = bool(re.search(r"[.!?:;][\"')\u201d\u2019]*\s*$", prev))
            if ends and (ind != indent or len(prev.strip()) < 70):
                paras.append(" ".join(cur))
                cur = []
            if cur and re.search(r"[a-z]-$", cur[-1]):  # "workforce-" / "ready": the hyphen is the word's
                cur[-1] += ln.strip()
            else:
                cur.append(ln.strip())
            indent, prev = ind, ln
            k += 1
        paras.append(" ".join(cur))
        paras = [unescape(re.sub(r"\s+", " ", x)).strip() for x in paras]
        body = "\n".join(x for x in paras if x)
        if body:
            out[bill] = body
        i = k
    return out


def read_report(body, year):
    text = pdftext(body)
    nd = next_day(text, year)
    rows = [r for r in schedule(body) if house_only(r[0])]
    return {"next": [nd[0], nd[1].isoformat()] if nd else None, "meetings": rows, "summaries": summaries(text)}


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


def backfill(year, out):
    """A past year's Daily Reports, once (states/ga/NOTES.md, "Summaries"): from LD1 on the session's first day, each
    report's "reconvene" line naming the next, the PDFs saved in <out>/<year>/ (kept: a second run reads them, not the
    server). A report not at its day's address is looked for on the next four weekdays (the House moved a day for
    weather in 2025). Stops at a report naming no next day (the last) or one that can't be found."""
    d = os.path.join(out, str(year))
    os.makedirs(d, exist_ok=True)
    first = date(year, 1, 1 + (0 - date(year, 1, 1).weekday()) % 7 + 7)
    ld, due, style, fold = 1, first, {}, None
    while ld <= 45:
        days = [due + timedelta(i) for i in range(10) if (due + timedelta(i)).weekday() < 5][:5]
        found = None
        have = [f for f in os.listdir(d) if re.match(rf"ld0?{ld}_|{year}-daily-report-ld-{ld}\.pdf$", f)]
        if have:
            name = have[0]
            body = open(os.path.join(d, name), "rb").read()
            m = re.match(r"ld\d+_[a-z]+_([a-z]+)_(\d+)_", name)
            day = date(year, next(i + 1 for i, f in enumerate(FULL) if f.startswith(m[1][:3])), int(m[2])) if m else due
            found = (fold, name, day, body)
        for day in ([] if found else days):
            for fo in folders(year, fold):
                cands = names(ld, day, style) + ([f"{year}-daily-report-ld-{ld}.pdf"] if ld <= 3 else [])
                for name in dict.fromkeys(cands):
                    body = get(DOCS + fo + "/" + name)
                    if body:
                        found = (fo, name, day, body)
                        open(os.path.join(d, name), "wb").write(body)
                        break
                if found:
                    break
            if found:
                break
        if not found:
            print(f"backfill {year}: LD{ld} (due {due}) not found after {REQUESTS[0]} requests", flush=True)
            break
        fo, name, day, body = found
        fold = fo or fold
        style = style_of(name, style)
        nd = next_day(pdftext(body), year)
        print(f"backfill {year}: LD{ld} {name}", flush=True)
        if not nd:
            break
        ld, due = nd[0], nd[1]
    return d


def summaries_of(folder):
    """{bill: [report date, report file, summary]} from the reports saved in a folder, the latest report's summary kept
    (it describes the latest version the House took up: a committee substitute, or the bill as it passed)."""
    out = {}
    for name in sorted(os.listdir(folder)):
        if not name.endswith(".pdf"):
            continue
        body = open(os.path.join(folder, name), "rb").read()
        text = pdftext(body)
        m = re.search(r"Daily Report for ([A-Z][a-z]+) (\d+), (\d{4})", text)
        if not m:  # the first days' reports have no running head (and no summaries)
            continue
        day = date(int(m[3]), FULL.index(m[1].lower()) + 1, int(m[2])).isoformat()
        for bill, s in summaries(text).items():
            if bill not in out or out[bill][0] <= day:
                out[bill] = [day, name, s]
    return out


if __name__ == "__main__" and sys.argv[1] == "--backfill":
    # python3 states/ga/daily.py --backfill <pdf folder> <session> <year> ...: saves the years' reports, then writes
    # states/ga/summaries_<session>.json from every report saved for the session.
    out, session, years = sys.argv[2], int(sys.argv[3]), [int(y) for y in sys.argv[4:]]
    got = {}
    for y in years:
        for bill, v in summaries_of(backfill(y, out)).items():
            if bill not in got or got[bill][0] <= v[0]:
                got[bill] = v
    dest = os.path.join(os.path.dirname(os.path.abspath(__file__)), f"summaries_{session}.json")
    json.dump(dict(sorted(got.items(), key=lambda kv: (kv[0][:2], int(kv[0][2:])))), open(dest, "w"),
              ensure_ascii=False, indent=0)
    print(f"{dest}: {len(got)} bills, {REQUESTS[0]} requests")
elif __name__ == "__main__":
    body = open(sys.argv[1], "rb").read()
    yr = int(re.search(r"(20\d\d)", os.path.basename(sys.argv[1]))[1])
    rep = read_report(body, yr)
    print("next:", rep["next"])
    for r in rep["meetings"]:
        print(r)
    for k, v in rep["summaries"].items():
        print(k, "|", v)
