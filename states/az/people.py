#!/usr/bin/env python3
"""Arizona's legislators since 2023, current and retired, from Open States' public-domain people data
(https://github.com/openstates/people, data/az/legislature/*.yml and data/az/retired/*.yml), into states/az/people.json:
[{"id": Open States person id, "name", "other_names": [...], "party": [{"name", "start", "end"}],
  "roles": [{"house": "S" | "H", "district": 12, "start", "end"}]}], keeping roles that end in 2023 or later.

The 2023 session's bulk file (states/openstates_bulk.py) names sponsors and voters without person ids; convert.py ties
those names to these people (`roster()`), within the house and the session's dates. Run once by hand (2026-11-17) and
committed: 2023's members won't change. Run it again only to cover a later year whose records also lack ids. About 350
small files from raw.githubusercontent.com (no key; the Open States API's daily quota isn't touched).
Usage: python3 states/az/people.py
"""
import json, os, re, sys, time, urllib.request

REPO = "https://api.github.com/repos/openstates/people/contents/data/az/"
RAW = "https://raw.githubusercontent.com/openstates/people/main/data/az/"
AGENT = "statebilltracker.org (a nonprofit bill tracker; contact via github.com/judithhubbard)"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "people.json")
SINCE = "2023-01-01"


def get(url):
    for attempt in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": AGENT}), timeout=60) as r:
                return r.read().decode("utf-8")
        except Exception:
            time.sleep(5 * (attempt + 1))
    raise SystemExit(f"couldn't read {url}")


def scalar(v):
    v = v.strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "'\"":
        # YAML's double quotes allow "\xE9" (é), which JSON doesn't.
        v = v[1:-1].replace("''", "'") if v[0] == "'" else json.loads(re.sub(r"\\x([0-9A-Fa-f]{2})", lambda m: "\\u00" + m.group(1), v))
    return v


def parse(text):
    """The few parts of an Open States person file used here: top-level scalars and the lists of mappings
    (party, roles, other_names). Not a general YAML reader."""
    out, key, item = {}, None, None
    for line in text.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        m = re.match(r"^([a-z_]+):\s*(.*)$", line)
        if m:
            key, v = m.group(1), m.group(2)
            out[key] = scalar(v) if v else []
            item = None
            continue
        m = re.match(r"^- ([a-z_]+):\s*(.*)$", line) or re.match(r"^  - ([a-z_]+):\s*(.*)$", line)
        if m and isinstance(out.get(key), list):
            item = {m.group(1): scalar(m.group(2))}
            out[key].append(item)
            continue
        m = re.match(r"^\s+([a-z_]+):\s*(.*)$", line)
        if m and item is not None:
            item[m.group(1)] = scalar(m.group(2))
    return out


def main():
    people = []
    for folder in ("legislature", "retired"):
        names = [f["name"] for f in json.loads(get(REPO + folder)) if f["name"].endswith(".yml")]
        for n in names:
            p = parse(get(RAW + folder + "/" + n))
            roles = [{"house": "S" if r.get("type") == "upper" else "H", "district": int(r["district"]),
                      "start": r.get("start_date") or "", "end": r.get("end_date") or ""}
                     for r in p.get("roles") or [] if r.get("type") in ("upper", "lower") and str(r.get("district", "")).isdigit()]
            roles = [r for r in roles if not r["end"] or r["end"] >= SINCE]
            if not roles:
                continue
            people.append({"id": p["id"], "name": p["name"],
                           "other_names": sorted({o["name"] for o in p.get("other_names") or [] if o.get("name")}),
                           "party": [{"name": x.get("name", ""), "start": x.get("start_date") or "", "end": x.get("end_date") or ""}
                                     for x in p.get("party") or []],
                           "roles": roles})
    people.sort(key=lambda p: p["name"])
    if len(people) < 90:
        raise SystemExit(f"only {len(people)} people; kept {OUT}")
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(people, f, ensure_ascii=False, indent=0)
    print(f"{OUT}: {len(people)} people with roles since {SINCE}")


if __name__ == "__main__":
    sys.exit(main())
