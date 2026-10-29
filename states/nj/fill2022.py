#!/usr/bin/env python3
"""One-time fix for 2022-23, whose text download (DB2022_TEXT.zip) lacks MAINBILL, ROSTER, COMMITTEE and
SUBJHEADINGS. Run once (done 2026-10-29); the filled file is kept in git, since a finished session never changes.

- MAINBILL comes from the full Access database (DB2022.zip), read with the pure-Python access-parser
  (mdbtools would need a large install): python3 -m venv /tmp/acc && /tmp/acc/bin/pip install access-parser,
  then /tmp/acc/bin/python states/nj/fill2022.py path/to/DB2022.mdb
- access-parser can't read the database's ROSTER and COMMITTEE tables, so they're put together instead:
  committee names from the 2020-21 download (else 2024-25), subject names from 2024-25, and the roster
  from the legislators who sponsored 2022-23 bills: party from MAINBILL's prime-sponsor parties (else the
  2020 or 2024 roster), district from the 2020 roster (the same district map), else none.
"""
import csv, io, os, re, sys, zipfile
from collections import Counter, defaultdict

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "nj")
TARGET = os.path.join(DATA, "DB2022_TEXT.zip")
norm = lambda s: re.sub(r"[ _]", "", s).lower()


def rows(z, name):
    return list(csv.DictReader(io.TextIOWrapper(z.open(name), "latin-1")))


def header(z, name):
    return next(csv.reader(io.TextIOWrapper(z.open(name), "latin-1")))


def write(z, name, head, records):
    buf = io.StringIO()
    w = csv.writer(buf, quoting=csv.QUOTE_ALL, lineterminator="\r\n")
    w.writerow(head)
    w.writerows([[r.get(h, "") for h in head] for r in records])
    z.writestr(name, buf.getvalue().encode("latin-1", "replace"))
    print(f"{name}: {len(records)} rows")


def mainbill(mdb, head):
    from access_parser import AccessParser
    t = AccessParser(mdb).parse_table("MainBill")
    cols = {norm(c): c for c in t}

    def val(v):
        if v is None:
            return ""
        if isinstance(v, float) and v.is_integer():
            v = int(v)
        m = re.fullmatch(r"(\d{4})-(\d\d)-(\d\d) (\d\d):(\d\d):(\d\d)", str(v))
        if m:  # written as the text downloads write dates: 3/20/2024 0:00:00
            y, mo, d, h, mi, s = map(int, m.groups())
            return f"{mo}/{d}/{y} {h}:{mi:02d}:{s:02d}"
        return str(v)
    n = len(next(iter(t.values())))
    return [{h: val(t[cols[norm(h)]][i]) for h in head if norm(h) in cols} for i in range(n)]


def key(house, name):
    last, _, first = name.partition(",")
    return (house, re.sub(r"[^a-z]", "", last.lower()), re.sub(r"[^a-z]", "", (first.split() or [""])[0].lower()))


def main(mdb):
    z20 = zipfile.ZipFile(os.path.join(DATA, "DB2020_TEXT.zip"))
    z24 = zipfile.ZipFile(os.path.join(DATA, "DB2024_TEXT.zip"))
    z = zipfile.ZipFile(TARGET)
    have = set(z.namelist())
    add = {}
    if "MAINBILL.TXT" not in have:
        add["MAINBILL.TXT"] = (header(z24, "MAINBILL.TXT"), mainbill(mdb, header(z24, "MAINBILL.TXT")))
    main_rows = add.get("MAINBILL.TXT", (None, None))[1] or rows(z, "MAINBILL.TXT")

    if "COMMITTEE.TXT" not in have:
        comms = {r["Code"]: r for r in rows(z24, "COMMITTEE.TXT")}
        comms.update({r["Code"]: r for r in rows(z20, "COMMITTEE.TXT")})
        add["COMMITTEE.TXT"] = (header(z24, "COMMITTEE.TXT"), list(comms.values()))
    if "SUBJHEADINGS.TXT" not in have:
        add["SUBJHEADINGS.TXT"] = (header(z24, "SUBJHEADINGS.TXT"), rows(z24, "SUBJHEADINGS.TXT"))

    if "ROSTER.TXT" not in have:
        # Who sponsored 2022-23 bills, by house; party as MAINBILL gives it for prime sponsors.
        party = defaultdict(Counter)
        for r in main_rows:
            house = r["BillType"].strip()[:1]
            for i in (1, 2, 3):
                who, p = r.get(("First", "Second", "Third")[i - 1] + "Prime", ""), r.get(f"BillParty{i}", "")
                if who.strip() and p.strip() in ("D", "R"):
                    party[key(house, who)][p.strip()] += 1
        sponsors = {}
        for r in rows(z, "BILLSPON.TXT"):
            house = r["BillType"].strip()[:1]
            if house in ("A", "S"):
                sponsors.setdefault(key(house, r["Sponsor"]), r["Sponsor"].strip())
        old = {}
        for zz, year in ((z24, 2024), (z20, 2020)):  # 2020 last, so it wins (same district map)
            for r in rows(zz, "ROSTER.TXT"):
                old[key(r["House"], f'{r["LastName"]}, {r["Firstname"]}')] = (r, year)
        roster = []
        for k, name in sponsors.items():
            last, _, first = name.partition(",")
            r, year = old.get(k, ({}, None))
            # A senator can turn up on an Assembly bill (and the other way round): party from either house.
            o = ("S" if k[0] == "A" else "A",) + k[1:]
            both = party[k] + party[o]
            p = both.most_common(1)[0][0] if both else r.get("Party", "") or old.get(o, ({}, None))[0].get("Party", "")
            roster.append({"District": r.get("District", "") if year == 2020 else "", "House": k[0],
                           "LastName": last.strip(), "Firstname": first.strip(), "Sex": r.get("Sex", ""),
                           "Party": p, "LegStatus": "Active"})
        add["ROSTER.TXT"] = (header(z24, "ROSTER.TXT"), roster)

    tmp = TARGET + ".tmp"
    with zipfile.ZipFile(TARGET) as src, zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as out:
        for info in src.infolist():
            if info.filename not in add:
                out.writestr(info, src.read(info))
        for name, (head, recs) in add.items():
            write(out, name, head, recs)
    os.replace(tmp, TARGET)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)
