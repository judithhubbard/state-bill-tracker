#!/usr/bin/env python3
"""Download Connecticut's bill data from the General Assembly's FTP server (ftp://ftp.cga.ct.gov/pub/data/; see the
ct-data-sources memory): for each year, bill_info (titles, statements of purpose, act numbers), bill_history,
introducer (sponsors), comm_ref (committee referrals), committee, subject, actions and the legislator database, into
data/ct/<year>/. The current year's files are in the top folder, earlier years' in archive/<year>/ from 2024 on; 2023
and before are only flat files at the archive's top level ("2023bill_info.csv", "2023bill_history.csv",
"2023introducer.csv", "2023subject.csv", "2023LegislatorData.xlsx": no comm_ref, committee or actions), saved here under
the usual names, the spreadsheet as LegislatorData.csv; those years are read once. The files are small (a few MB a
year), so every run reads the newer ones all again.
Usage: python3 states/ct/fetch.py [first_year]   (default: four years back, so two finished sessions of each kind, long
and short, are kept for the statistics)
"""
import csv, io, json, os, re, subprocess, sys, time, zipfile
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
from states.ct import profile as P
from states import window as W

FTP = "ftp://ftp.cga.ct.gov/pub/data"
FILES = ["bill_info", "bill_history", "introducer", "comm_ref", "committee", "subject", "actions", "LegislatorDatabase"]
YEAR = datetime.now(ZoneInfo(P.TIMEZONE)).year
FIRST = int(sys.argv[1]) if len(sys.argv) > 1 else YEAR - 4
FLAT = ["bill_info", "bill_history", "introducer", "subject"]  # an old year's flat files, besides the spreadsheet


def curl(url):
    for attempt in range(3):
        # A stuck server mustn't hold the run (one hung GitHub's 20-minute limit): give up on a slow or silent file.
        r = subprocess.run(["curl", "-sS", "--connect-timeout", "20", "--max-time", "120", "--speed-limit", "2000",
                            "--speed-time", "30", url], capture_output=True)
        if r.returncode == 0:
            return r.stdout
    return None


_NEWEST = []


def newest():
    """The year whose files are in the top folder (read once); 0 when its bill_info has a header and no bills (a new
    session before its first bill: every year is then read from the archive, so an empty top folder never overwrites
    the last session's files)."""
    if not _NEWEST:
        top = curl(f"{FTP}/bill_info.csv") or b""
        m = re.search(rb'"\w+","\d+","(\d{4})"', top)
        _NEWEST.append(int(m.group(1)) if m else 0 if b"bill_num" in top[:200] else YEAR)
    return _NEWEST[0]


_ARCHIVE = []


def archive():
    """The names at the archive's top level: year folders ("2024") and old years' flat files (read once)."""
    if not _ARCHIVE:
        listing = (curl(f"{FTP}/archive/") or b"").decode("latin-1")
        _ARCHIVE.append({line.split()[-1] for line in listing.splitlines() if line.split()})
    return _ARCHIVE[0]


_X = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"


def xlsx_rows(body):
    """The first sheet of an .xlsx file as lists of strings (no dependencies: it's a zip of XML)."""
    z = zipfile.ZipFile(io.BytesIO(body))
    shared = []
    if "xl/sharedStrings.xml" in z.namelist():
        shared = ["".join(t.text or "" for t in si.iter(_X + "t"))
                  for si in ET.fromstring(z.read("xl/sharedStrings.xml")).iter(_X + "si")]

    def col(ref):
        n = 0
        for ch in re.match(r"[A-Z]+", ref).group():
            n = n * 26 + ord(ch) - 64
        return n - 1

    out = []
    for row in ET.fromstring(z.read("xl/worksheets/sheet1.xml")).iter(_X + "row"):
        cells = {}
        for c in row.iter(_X + "c"):
            v, t = c.find(_X + "v"), c.get("t")
            if t == "s" and v is not None:
                cells[col(c.get("r"))] = shared[int(v.text)]
            elif t == "inlineStr":
                cells[col(c.get("r"))] = "".join(x.text or "" for x in c.iter(_X + "t"))
            else:
                cells[col(c.get("r"))] = v.text if v is not None else ""
        out.append([cells.get(i, "") for i in range(max(cells) + 1)] if cells else [])
    return out


def flat_year(y, folder):
    """An old year from the archive's flat files (no year folder). Finished years don't change: each file is read once,
    and a file a run failed to get is read again by the next (a check of only two files once kept 2023 without its
    bill_history for good, and the site showed every 2023 bill with no history). Until every file is there the year is
    marked incomplete (states/window.py), so the site leaves it out rather than show it empty."""
    have = lambda name: os.path.exists(os.path.join(folder, name))
    missing = [n for n in FLAT if not have(f"{n}.csv")] + ([] if have("LegislatorData.csv") else ["LegislatorData"])
    if not missing:
        print(f"{y}: kept")
        W.mark(P.DATA, y, [])
        return
    for name in [n for n in FLAT if n in missing]:
        body = curl(f"{FTP}/archive/{y}{name}.csv")
        if body and len(body) > 100:
            open(os.path.join(folder, f"{name}.csv"), "wb").write(body)
            missing.remove(name)
    if "LegislatorData" in missing:
        body = curl(f"{FTP}/archive/{y}LegislatorData.xlsx")
        if body and body[:2] == b"PK":
            rows = xlsx_rows(body)
            with open(os.path.join(folder, "LegislatorData.csv"), "w", newline="", encoding="utf-8") as f:
                csv.writer(f).writerows(r for r in rows if r)
            missing.remove("LegislatorData")
    W.mark(P.DATA, y, [f"{y}:{m}" for m in missing])
    print(f"{y}: {len(FLAT) + 1 - len(missing)} of {len(FLAT) + 1} files (flat archive)"
          + (f"; still missing {', '.join(missing)}" if missing else ""))


def year(y):
    folder = os.path.join(P.DATA, str(y))
    newest_ = newest()
    if newest_ and y > newest_:
        # A year the server doesn't have yet (January before the top folder moves on to the new session): no folder,
        # no requests; the newest year keeps being read from the top folder until then.
        print(f"{y}: not on the server yet (its top folder is still {newest_})")
        return
    os.makedirs(folder, exist_ok=True)
    # A flat year: the archive lists its flat files, or (when the listing failed) the folder already holds them.
    flat_here = os.path.exists(os.path.join(folder, "LegislatorData.csv")) and not os.path.exists(
        os.path.join(folder, "comm_ref.csv"))
    if y != newest_ and str(y) not in archive() and (f"{y}bill_info.csv" in archive() or flat_here):
        return flat_year(y, folder)
    base = FTP if y == newest_ else f"{FTP}/archive/{y}"
    got = 0
    for name in FILES:
        body = curl(f"{base}/{name}.csv")
        if body and len(body) > 100:
            open(os.path.join(folder, f"{name}.csv"), "wb").write(body)
            got += 1
    print(f"{y}: {got} of {len(FILES)} files")


def texts():
    """"What it does": each bill's statement of purpose (bill_info's stmt_purp), as data/ct/texts_<year>.json."""
    import csv, json
    from states.ct import convert as C
    for y in C.sessions():
        out = {}
        for r in C.rows(y, "bill_info"):
            num, purp = r.get("bill_num", ""), (r.get("stmt_purp") or "").strip()
            if num[:2] in ("HB", "SB") and purp:
                out[num[:2] + str(int(num[2:]))] = {"statement": purp, "label": "From the bill's statement of purpose."}
        json.dump(out, open(os.path.join(P.DATA, f"texts_{y}.json"), "w"), ensure_ascii=False)
        print(f"texts_{y}.json: {len(out)} statements of purpose")


SITE = "https://www.cga.ct.gov"
EVENTS = f"{SITE}/basin/api/v1/calendar-events/"
# www.cga.ct.gov doesn't send the intermediate certificate its own needs (GoDaddy's G2), so it's fetched from GoDaddy
# and added to a copy of the system's certificates (data/ct/ca.pem); the connection is still fully checked.
INTERMEDIATE = "http://certificates.godaddy.com/repository/gdig2.crt"
SYSTEM_CAS = ["/etc/ssl/certs/ca-certificates.crt", "/etc/ssl/cert.pem", "/etc/pki/tls/certs/ca-bundle.crt"]
CA = os.path.join(P.DATA, "ca.pem")
AGENDA_BILL = re.compile(r"\b([HS])\.\s?([BJ])\.\s?No\.\s?(\d{1,4})\b")


def ca_bundle():
    if os.path.exists(CA) and time.time() - os.path.getmtime(CA) < 30 * 86400:
        return CA
    os.makedirs(P.DATA, exist_ok=True)
    der = subprocess.run(["curl", "-sSf", "--max-time", "60", INTERMEDIATE], capture_output=True, check=True).stdout
    pem = subprocess.run(["openssl", "x509", "-inform", "DER"], input=der, capture_output=True, check=True).stdout
    system = next(p for p in SYSTEM_CAS if os.path.exists(p))
    with open(CA + ".tmp", "wb") as f:
        f.write(open(system, "rb").read() + b"\n" + pem)
    os.replace(CA + ".tmp", CA)
    return CA


def web(url):
    """One page from www.cga.ct.gov (robots.txt allows /basin/ and the /<year>/ folders), a second apart; None on failure."""
    time.sleep(1)
    r = subprocess.run(["curl", "-sSf", "--cacert", CA, "--connect-timeout", "20", "--max-time", "120", url],
                       capture_output=True)
    return r.stdout if r.returncode == 0 else None


def pdf_text(body):
    r = subprocess.run(["pdftotext", "-layout", "-", "-"], input=body, capture_output=True)
    return r.stdout.decode("utf-8", "replace") if r.returncode == 0 else ""


def agendas(y):
    """Bills on committee agendas from yesterday to three weeks ahead, into data/ct/<year>/agendas.json:
    {"SB89": [["Joint Judiciary", "2026-03-23T10:00:00"], ...]}. The meetings come from the General Assembly's Schedule
    of Events (www.cga.ct.gov/calendarofevents.asp reads /basin/api/v1/calendar-events/: every event of about a year,
    each with its committee's code (office_code "JUD"), kind (COM a committee meeting, PHR a public hearing, PHC a hearing
    followed by a meeting), start (Eastern time, written with a "Z" the site's own script strips) and its agenda's
    address once posted, a PDF such as /2026/JUDdata/ca/pdf/2026ca-00323-R001000JUD-ca.pdf). Each upcoming agenda is
    read with pdftotext; its bills read "S.B. No. 89", "H.B. No. 5308", "H.J. No. 1". Canceled events' titles begin
    "CANCELLED". One request for the events plus one per posted agenda; any failure keeps the last copy."""
    folder = os.path.join(P.DATA, str(y))
    path = os.path.join(folder, "agendas.json")
    try:
        ca_bundle()
    except (subprocess.CalledProcessError, OSError, StopIteration) as e:
        print(f"agendas: no certificate bundle ({type(e).__name__}); kept the last copy")
        return
    body = web(EVENTS)
    try:
        events = json.loads(body) if body else None
    except ValueError:
        events = None
    if not isinstance(events, list):
        print("agendas: the schedule of events is unreadable; kept the last copy")
        return
    names = {}
    try:
        with open(os.path.join(folder, "committee.csv"), newline="", encoding="utf-8", errors="replace") as f:
            for r in csv.DictReader(f):
                names[r["comm_code"].strip()] = re.sub(r"\s+Committee$", "", re.sub(
                    r"^(?:Joint )?Committee on\s+", "", r["comm_name"].strip()))
    except (OSError, KeyError):
        pass
    today = datetime.now(ZoneInfo(P.TIMEZONE)).date()
    first, last = (today - timedelta(days=1)).isoformat(), (today + timedelta(days=21)).isoformat()
    out, meetings, failed = {}, 0, 0
    for ev in events:
        when, url, code = ev.get("start") or "", (ev.get("url") or "").strip(), (ev.get("office_code") or "").strip()
        if ev.get("mtg_type") not in ("COM", "PHR", "PHC") or not first <= when[:10] <= last \
                or re.match(r"\s*CANCEL", ev.get("title") or "", re.I) or not url.lower().endswith(".pdf"):
            continue
        pdf = web(SITE + url if url.startswith("/") else url)
        text = pdf_text(pdf) if pdf and pdf[:4] == b"%PDF" else ""
        if not text:
            failed += 1
            continue
        meetings += 1
        name = f"Joint {names.get(code) or re.sub(r' (Committee|Public Hearing).*$', '', ev.get('title') or code)}"
        stamp = f"{when[:10]}T{when[11:16] or '00:00'}:00" if re.match(r"\d{4}-\d\d-\d\dT\d\d:\d\d", when) \
            else f"{when[:10]}T00:00:00"
        for h, kind, num in AGENDA_BILL.findall(text):
            key, entry = f"{h}{kind}{int(num)}", [name, stamp]
            if entry not in out.setdefault(key, []):
                out[key].append(entry)
    if failed and not meetings and os.path.exists(path):
        print(f"agendas: {failed} agendas unreadable; kept the last copy")
        return
    os.makedirs(folder, exist_ok=True)
    with open(path + ".tmp", "w") as f:
        json.dump(out, f, ensure_ascii=False)
    os.replace(path + ".tmp", path)
    print(f"agendas: {len(out)} bills on {meetings} meetings ({failed} agendas unreadable)")


def main():
    # Through the new session's year, or the year the top folder holds when it moves on before January 1.
    for y in range(FIRST, max(YEAR, newest()) + 1):
        year(y)
    texts()
    try:
        agendas(YEAR)  # never holds Connecticut back
    except Exception as e:
        print(f"agendas: failed ({type(e).__name__}); kept the last copy")
    try:
        # Floor roll calls: each floor day's House and Senate Journal, read once (states/ct/journals.py); at most ten
        # minutes a run, newest first, so a first copy of five years (about 210 journals of 1-8 MB) takes two runs.
        from states.ct import journals
        from states.ct import convert as C
        journals.fetch([y for y in C.sessions() if y >= FIRST], minutes=10)
    except Exception as e:  # never holds Connecticut back
        print(f"journals: failed ({type(e).__name__}: {e})")
    try:
        # The governor's veto messages, from his numbered Bill Notifications (states/ct/vetoes.py).
        from states.ct import vetoes
        vetoes.fetch(range(FIRST, YEAR + 1), minutes=8)
    except Exception as e:  # never holds Connecticut back
        print(f"veto messages: failed ({type(e).__name__}: {e})")


if __name__ == "__main__":
    main()
    from states.ct import contacts  # the legislator database just downloaded
    contacts.main(YEAR)
