#!/usr/bin/env python3
"""Indiana's floor votes member by member, from Open States' bulk files (2026-11-28).

The General Assembly's API (states/in/fetch.py) gives each roll call's tally only: its PDF link redirects to iga.in.gov,
which answers automated requests with the website's script page, not the PDF (the journals' PDFs the same). Open States
reads those PDFs; its public-domain bulk JSON files carry each vote's members, and each vote's source is the roll call's
own PDF ("https://iga.in.gov/pdf-documents/124/2025/house/bills/HB1001/rollcalls/HB1001.402_S.pdf"), so a vote joins
our roll call exactly: bill, roll-call number and the house that voted ("HB1001.402_S"; the action reads "Roll Call 402").

The bulk files cost no API requests (Open States' free API allows 250 a day, already shared by Arizona, Hawaii, Iowa
and the daily cross-check). Their names are listed at open.pluralpolicy.com/data/session-json/, which needs the owner's
login (states/openstates_bulk.py); they go in states/in/bulk.json by session year: {"2025": "IN_2025_json_<id>.zip"}.
A live session's file is rebuilt with a new name: put the new name in bulk.json and it's read again.

Writes data/in/<year>/os_votes.json: {"bulk": file name, "done": day, "votes": {"HB1001.402_S": {"yes": n, "no": n,
"names": {"no": [...], "excused": [...], "not voting": [...], "yes": [...]}}}}, read by states/in/convert.py.
Usage: python3 states/in/os_votes.py
"""
import io, json, os, re, sys, zipfile
from datetime import date

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
sys.path.insert(0, ROOT)
from states import openstates_bulk as B  # noqa: E402

SOURCE = re.compile(r"/rollcalls/([A-Z]+\d+)\.(\d+)_([HS])\.pdf", re.I)


def votes_of(bills):
    out = {}
    for b in bills:
        for v in b.get("votes") or []:
            key = None
            for s in v.get("sources") or []:
                m = SOURCE.search(s.get("url") or "")
                if m:
                    key = f"{m.group(1).upper()}.{int(m.group(2))}_{m.group(3).upper()}"
                    break
            if not key:
                continue
            names = {}
            for x in v.get("votes") or []:
                names.setdefault((x.get("option") or "").lower(), []).append(x.get("voter_name") or "")
            counts = {(c.get("option") or "").lower(): int(c.get("value") or 0) for c in v.get("counts") or []}
            out[key] = {"yes": counts.get("yes", 0), "no": counts.get("no", 0), "names": names}
    return out


def main():
    files = B.load(os.path.join(ROOT, "states", "in", "bulk.json"), {})
    if not files:
        print("Indiana: no Open States bulk files named in states/in/bulk.json; members' votes not read", flush=True)
        return
    for year, name in sorted(files.items()):
        path = os.path.join(ROOT, "data", "in", year, "os_votes.json")
        if (B.load(path, {}) or {}).get("bulk") == name:
            continue
        try:
            z = zipfile.ZipFile(io.BytesIO(B.fetch(name)))
            bills = json.loads(z.read(next(n for n in z.namelist() if n.endswith("_bills.json"))))
        except Exception as e:
            print(f"Indiana {year}: {name} unreadable ({type(e).__name__}: {e}); tried again next run", flush=True)
            continue
        got = votes_of(bills)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        B.save({"bulk": name, "done": date.today().isoformat(), "votes": got}, path)
        print(f"Indiana {year}: {len(got)} roll calls with members' votes from {name}", flush=True)


if __name__ == "__main__":
    main()
