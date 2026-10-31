#!/usr/bin/env python3
"""Download Connecticut's bill data from the General Assembly's FTP server (ftp://ftp.cga.ct.gov/pub/data/; see the
ct-data-sources memory): for each year, bill_info (titles, statements of purpose, act numbers), bill_history,
introducer (sponsors), comm_ref (committee referrals), committee, subject, actions and the legislator database, into
data/ct/<year>/. The current year's files are in the top folder, earlier years' in archive/<year>/. The files are
small (a few MB a year), so every run reads them all again.
Usage: python3 states/ct/fetch.py [first_year]   (default: two years back)
"""
import os, re, subprocess, sys
from datetime import datetime
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
from states.ct import profile as P

FTP = "ftp://ftp.cga.ct.gov/pub/data"
FILES = ["bill_info", "bill_history", "introducer", "comm_ref", "committee", "subject", "actions", "LegislatorDatabase"]
YEAR = datetime.now(ZoneInfo(P.TIMEZONE)).year
FIRST = int(sys.argv[1]) if len(sys.argv) > 1 else YEAR - 2


def curl(url):
    for attempt in range(3):
        r = subprocess.run(["curl", "-sS", "--max-time", "300", url], capture_output=True)
        if r.returncode == 0:
            return r.stdout
    return None


def year(y):
    folder = os.path.join(P.DATA, str(y))
    os.makedirs(folder, exist_ok=True)
    # The top folder holds the newest year's files; check which year that is.
    top = curl(f"{FTP}/bill_info.csv") or b""
    newest = int(re.search(rb'"\w+","\d+","(\d{4})"', top).group(1)) if re.search(rb'"\w+","\d+","(\d{4})"', top) else YEAR
    base = FTP if y == newest else f"{FTP}/archive/{y}"
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
