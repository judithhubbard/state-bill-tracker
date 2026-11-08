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
import csv, io, os, re, subprocess, sys, zipfile
import xml.etree.ElementTree as ET
from datetime import datetime
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
from states.ct import profile as P

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
    """The year whose files are in the top folder (read once)."""
    if not _NEWEST:
        top = curl(f"{FTP}/bill_info.csv") or b""
        m = re.search(rb'"\w+","\d+","(\d{4})"', top)
        _NEWEST.append(int(m.group(1)) if m else YEAR)
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
    """An old year from the archive's flat files (no year folder). Finished years don't change: read once."""
    if os.path.exists(os.path.join(folder, "bill_info.csv")) and os.path.exists(os.path.join(folder, "LegislatorData.csv")):
        print(f"{y}: kept")
        return
    got = 0
    for name in FLAT:
        body = curl(f"{FTP}/archive/{y}{name}.csv")
        if body and len(body) > 100:
            open(os.path.join(folder, f"{name}.csv"), "wb").write(body)
            got += 1
    body = curl(f"{FTP}/archive/{y}LegislatorData.xlsx")
    if body and body[:2] == b"PK":
        rows = xlsx_rows(body)
        with open(os.path.join(folder, "LegislatorData.csv"), "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerows(r for r in rows if r)
        got += 1
    print(f"{y}: {got} of {len(FLAT) + 1} files (flat archive)")


def year(y):
    folder = os.path.join(P.DATA, str(y))
    os.makedirs(folder, exist_ok=True)
    newest_ = newest()
    if y != newest_ and str(y) not in archive() and f"{y}bill_info.csv" in archive():
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


def main():
    for y in range(FIRST, YEAR + 1):
        year(y)
    texts()


if __name__ == "__main__":
    main()
    from states.ct import contacts  # the legislator database just downloaded
    contacts.main(YEAR)
