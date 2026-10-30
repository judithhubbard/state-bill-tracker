#!/usr/bin/env python3
"""Each Texas county and the Senate and House districts that cover it, with the share of the county's people in each,
for "Where you live": data/tx/district_towns.json: [["Harris County", "", [[4, 6], [6, 21], ...], [[126, 4], ...]], ...]:
county, (unused), Senate districts and House districts, each [district, percent of the county].

From the Texas Legislative Council's "District Population Analysis with County Subtotals" for each district
(wrm.capitol.texas.gov/fyiwebdocs/PDF/<senate|house>/dist<N>/r4.pdf; needs pdftotext), whose lines read
" Harris (4%)   196,097 ...". The districts are fixed until the 2031 redistricting, so this is run once and the file
kept in git. Usage: python3 states/tx/towns.py
"""
import json, os, re, subprocess, sys, tempfile
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
from states.tx import profile as P

URL = "https://wrm.capitol.texas.gov/fyiwebdocs/PDF/{house}/dist{d}/r4.pdf"


def counties(house, d, tmp):
    pdf = os.path.join(tmp, f"{house}{d}.pdf")
    subprocess.run(["curl", "-sSfL", "--max-time", "60", "-o", pdf, URL.format(house=house, d=d)], check=True)
    text = subprocess.run(["pdftotext", "-layout", pdf, "-"], capture_output=True, text=True, check=True).stdout
    return [(name.strip(), int(pct)) for name, pct in re.findall(r"^\s{1,3}([A-Z][A-Za-z .'-]+?) \((\d+)%\)\s+[\d,]+", text, re.M)]


def main():
    out = defaultdict(lambda: {"S": [], "H": []})
    with tempfile.TemporaryDirectory() as tmp:
        for house, h, n in (("senate", "S", 31), ("house", "H", 150)):
            for d in range(1, n + 1):
                cs = counties(house, d, tmp)
                if not cs:
                    print(f"  no counties read for {house} district {d}", file=sys.stderr)
                for name, pct in cs:
                    out[name][h].append([d, pct])
    rows = [[f"{c} County", "", sorted(v["S"], key=lambda x: -x[1]), sorted(v["H"], key=lambda x: -x[1])] for c, v in sorted(out.items())]
    path = os.path.join(P.DATA, "district_towns.json")
    os.makedirs(P.DATA, exist_ok=True)
    json.dump(rows, open(path, "w"), indent=0)
    print(f"{path}: {len(rows)} counties; {sum(1 for r in rows if len(r[2]) == 1 and len(r[3]) == 1)} in one district of each")


if __name__ == "__main__":
    main()
