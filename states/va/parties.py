#!/usr/bin/env python3
"""Party letters for Virginia members who appear in an earlier session's LIS files but in no contacts file (they've left),
written to states/va/parties.json as {"H0253": "R", ...}, keyed by the LIS member id each session's Members.csv gives (the
same id in every session). From Open States' public-domain people data for members who have left (data/va/retired/*.yml
on github.com/openstates/people), matched by house and name. convert.py's old_parties() reads it; members still sitting
take their party from the contacts files first. Run once by hand (2026-11-26) and committed: those members won't change.
Run it again only when the window adds a session with members who left before the newest contacts file.
Usage: python3 states/va/parties.py
"""
import csv, glob, json, os, re, sys, time, urllib.request
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
from states.az.people import parse, AGENT  # (the same small reader of Open States person files)
from states.va import profile as P

REPO = "https://api.github.com/repos/openstates/people/contents/data/va/retired"
RAW = "https://raw.githubusercontent.com/openstates/people/main/data/va/retired/"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "parties.json")
LETTER = {"Democratic": "D", "Republican": "R", "Independent": "I"}
# Members Open States' retired list doesn't name (2026-11-26): Emily Brewer (Delegate, R), Angelia Williams Graves
# (Delegate, then Senator, D), Ghazala Hashmi (Senator, then Lieutenant Governor, D).
KNOWN = {"H0291": "R", "H0331": "D", "S0108": "D"}


def get(url):
    for attempt in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": AGENT}), timeout=60) as r:
                return r.read().decode("utf-8")
        except Exception:
            time.sleep(5 * (attempt + 1))
    raise SystemExit(f"couldn't read {url}")


def key(name):
    """"Austin, Terry L." or "Terry L. Austin" -> ("austin", "t")."""
    name = re.sub(r",?\s+(Jr\.?|Sr\.?|II|III|IV)$", "", name.strip(), flags=re.I)
    if "," in name:
        last, first = [x.strip() for x in name.split(",", 1)]
    else:
        parts = name.split()
        last, first = parts[-1], parts[0]
    return re.sub(r"[^a-z]", "", last.lower()), (first[:1] or "").lower()


def main():
    known = set()
    for path in glob.glob(os.path.join(P.DATA, "contacts_*.json")):
        for p in json.load(open(path))["people"].values():
            if p.get("id"):
                known.add(p["id"][0] + p["id"][1:].zfill(4))
    wanted = {}
    for path in glob.glob(os.path.join(P.DATA, "*", "Members.csv")):
        for r in csv.DictReader(open(path, encoding="utf-8", errors="replace")):
            mid = r["MBR_MBRNO"].strip()
            if mid and mid not in known:
                wanted[mid] = (r["MBR_HOU"].strip(), key(r["MBR_NAME"]))
    people = {}
    for f in json.loads(get(REPO)):
        if not f["name"].endswith(".yml"):
            continue
        p = parse(get(RAW + f["name"]))
        time.sleep(0.3)
        parties = [x.get("name", "") for x in p.get("party") or []]
        letter = LETTER.get(parties[-1]) if parties else None
        if not letter:
            continue
        for r in p.get("roles") or []:
            if (r.get("end_date") or "9") < "2022-01-01" or r.get("type") not in ("upper", "lower"):
                continue
            house = "S" if r["type"] == "upper" else "H"
            for n in [p["name"]] + [o.get("name", "") for o in p.get("other_names") or []]:
                if n:
                    people.setdefault((house,) + key(n), set()).add(letter)
    # (A member who moved to the other house has a new id there: Bagby, Roem, VanValkenburg ... now senators. Their old
    # id takes the party their name has in either house: the contacts files' members, then Open States' retired list.)
    any_house = {}
    for (h, last, first), letters in people.items():
        any_house.setdefault((last, first), set()).update(letters)
    for path in glob.glob(os.path.join(P.DATA, "contacts_*.json")):
        for p in json.load(open(path))["people"].values():
            if (p.get("party") or "")[:1] in ("D", "R", "I") and p.get("name"):
                any_house.setdefault(key(re.sub(r"^(Sen|Del|Rep|Asm)\.\s+", "", p["name"])), set()).add(p["party"][:1])
    out = {m: v for m, v in KNOWN.items() if m in wanted}
    for mid, (house, k) in sorted(wanted.items()):
        got = people.get((house,) + k) or any_house.get(k)
        if got and len(got) == 1:
            out[mid] = next(iter(got))
    with open(OUT, "w") as f:
        json.dump(out, f, indent=0, sort_keys=True)
    unmatched = sorted(f"{m} {wanted[m]}" for m in wanted if m not in out)
    print(f"{OUT}: {len(out)} of {len(wanted)} members who've left; unmatched ({len(unmatched)}): {unmatched[:20]}")


if __name__ == "__main__":
    main()
