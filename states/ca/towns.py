#!/usr/bin/env python3
"""Each California county and the Senate and Assembly districts that cover it, for "Where you live", written as
data/ca/district_towns.json: [["Alameda County", "", [[7, 0], [9, 0], ...], [[14, 0], ...]], ...]: county,
(unused), Senate districts, Assembly districts. A district's share of the county isn't published, so it's 0.

From the Senate's "Counties Represented" list (a PDF; needs pdftotext) and the Assembly's member list (each
district's counties). The districts are fixed until the 2031 redistricting, so this is run once and the file is
kept in git; most counties are split, and the page's address lookup finds the exact districts.
Usage: python3 states/ca/towns.py
"""
import json, os, re, subprocess, sys, tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
from states.ca import profile as P
from states.ca.contacts import API, get

SENATE_PDF = "https://www.senate.ca.gov/media/4113"


def senate():
    with tempfile.TemporaryDirectory() as tmp:
        pdf = os.path.join(tmp, "counties.pdf")
        subprocess.run(["curl", "-sSfL", "--max-time", "60", "-o", pdf, SENATE_PDF], check=True)
        text = subprocess.run(["pdftotext", "-layout", pdf, "-"], capture_output=True, text=True, check=True).stdout
    out, cur = {}, None
    for line in text.splitlines():
        m = re.match(r"\S.*?\((?:D|R|I)\)\s+(\d+)\s+(.+)$", line) or re.match(r"Vacant\s+(\d+)\s+(.+)$", line.strip())
        if m:
            cur = int(m.group(1))
            out.setdefault(cur, []).extend(c.strip() for c in m.group(2).split(",") if c.strip())
        elif cur and re.match(r"\s{30,}\S", line) and not re.search(r"CAPITALS|Revised|COUNTIES", line):
            out[cur].extend(c.strip() for c in line.split(",") if c.strip())
        elif not line.strip():
            continue
        else:
            cur = None if re.search(r"CAPITALS|SENATE COUNTIES|Revised|MEMBER", line) else cur
    return {d: {c.title() for c in cs} for d, cs in out.items()}


def assembly():
    out = {}
    for d, counties in re.findall(r"data-district=\"(\d+)\"[^>]*?data-counties='([^']*)'", get(API), re.S):
        out[int(d)] = {c.strip().title() for c in counties.split(",") if c.strip()}
    return out


def main():
    s, a = senate(), assembly()
    counties = sorted({c for cs in list(s.values()) + list(a.values()) for c in cs})
    rows = [[f"{c} County", "", [[d, 0] for d in sorted(s) if c in s[d]], [[d, 0] for d in sorted(a) if c in a[d]]] for c in counties]
    path = os.path.join(P.DATA, "district_towns.json")
    json.dump(rows, open(path, "w"), indent=0)
    print(f"{path}: {len(rows)} counties, {len(s)} Senate and {len(a)} Assembly districts; "
          f"{sum(1 for r in rows if len(r[2]) == 1 and len(r[3]) == 1)} in one district of each")
    missing = [r[0] for r in rows if not r[2] or not r[3]]
    if missing:
        print("  no district for:", ", ".join(missing), file=sys.stderr)


if __name__ == "__main__":
    main()
