#!/usr/bin/env python3
"""Import Open States' bulk JSON files (public domain; listed at open.pluralpolicy.com/data/session-json/, which needs
the owner's login; the files themselves are public at data.openstates.org/json/latest/<name>) as a state's first copy,
so it doesn't cost API requests (decided 2026-11-15). Each state that uses it lists its files in states/<st>/bulk.json:
{"2023": "IA_2023-2024_json_1kN9lPSj9K5DfOYX73p5dn.zip"}, by the session's first year (the folder under data/<st>/).
The file names change when Open States rebuilds a file: a finished session's stays put; for a live one, put the new name
in bulk.json and it's imported again.

Each bill goes into data/<st>/<year>/openstates/<HF100>.json in the shape the API answers (states/ia/openstates.py,
states/hi/fetch.py), so the converters read either: "sponsorships" (the bulk file's "sponsors"; no person ids),
actions and votes with an "organization" ({"name", "classification"}), "latest_action_date" and
"latest_action_description" from the last action, "session"; the bill text ("raw_text") is left out. And
data/<st>/<year>/openstates.json: {"complete": true, "bulk": file name, "done": day}. A file is downloaded (or taken from
the owner's Bulk_files_OpenStates/ folder, when it's there) only when bulk.json names one not imported yet. Hawaii's
download (states/hi/fetch.py) keeps its bills in bills/ and its place in state.json, so for "hi" the records go into
data/hi/<year>/bills/ and state.json is marked complete with "since" the file's build time: its later passes ask the API
only for bills updated after that. Only the bill
types the state keeps are saved (KEEP below). Nothing here marks a state incomplete: a failed download is tried again
next run.

Usage: python3 states/openstates_bulk.py <st>
"""
import io, json, os, re, sys, urllib.parse, urllib.request, zipfile
from datetime import date, datetime, timedelta

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
LOCAL = os.path.join(ROOT, "Bulk_files_OpenStates")
URL = "https://data.openstates.org/json/latest/"
AGENT = "statebilltracker.org (a nonprofit bill tracker; contact via github.com/judithhubbard)"
KEEP = {"ia": r"(HF|SF|HJR|SJR|HSB|SSB)", "fl": r"(HB|SB|HJR|SJR)", "hi": r"(HB|SB)"}
CHAMBER = {"House": "lower", "Senate": "upper", "Assembly": "lower", "Legislature": "legislature"}


def save(obj, path):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False)
    os.replace(tmp, path)


def load(path, default=None):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def fetch(name):
    """The zip's bytes: the owner's local copy if there is one, else Open States' public link."""
    local = os.path.join(LOCAL, name)
    if os.path.exists(local):
        return open(local, "rb").read()
    req = urllib.request.Request(URL + urllib.parse.quote(name), headers={"User-Agent": AGENT})
    with urllib.request.urlopen(req, timeout=600) as r:
        return r.read()


def api_shape(b):
    """A bulk-file bill in the API's shape."""
    actions = []
    for a in b.get("actions") or []:
        a = dict(a)
        org = a.pop("organization__name", "") or ""
        a["organization"] = {"name": org, "classification": CHAMBER.get(org, "executive" if "Governor" in org else "")}
        actions.append(a)
    votes = []
    for v in b.get("votes") or []:
        v = dict(v)
        v["organization"] = {"classification": v.pop("organization__classification", "")}
        votes.append(v)
    last = max(actions, key=lambda a: (a.get("date") or "", a.get("order") or 0)) if actions else {}
    return {
        "id": b.get("id"), "identifier": b["identifier"], "title": b.get("title"), "session": b.get("legislative_session"),
        "classification": b.get("classification"), "subject": b.get("subject") or [], "abstracts": b.get("abstracts") or [],
        "other_titles": b.get("other_titles") or [], "sponsorships": b.get("sponsors") or [], "actions": actions,
        "votes": votes, "versions": b.get("versions") or [], "documents": b.get("documents") or [],
        "related_bills": b.get("related_bills") or [], "sources": b.get("sources") or [],
        "latest_action_date": last.get("date"), "latest_action_description": last.get("description"),
        "bulk": True,
    }


def main(st):
    files = load(os.path.join(ROOT, "states", st, "bulk.json"), {})
    keep = re.compile(KEEP[st] + r" ?\d+$")
    for year, name in sorted(files.items()):
        folder = os.path.join(ROOT, "data", st, year)
        os.makedirs(folder, exist_ok=True)
        mark_path = os.path.join(folder, "openstates.json")
        mark = load(mark_path, {})
        if mark.get("bulk") == name:
            continue
        try:
            z = zipfile.ZipFile(io.BytesIO(fetch(name)))
            bills = json.loads(z.read(next(n for n in z.namelist() if n.endswith("_bills.json"))))
        except Exception as e:
            print(f"{st} {year}: {name} unreadable ({type(e).__name__}: {e}); tried again next run", flush=True)
            continue
        out = os.path.join(folder, "bills" if st == "hi" else "openstates")
        os.makedirs(out, exist_ok=True)
        n = 0
        for b in bills:
            if keep.match(b.get("identifier") or ""):
                save(api_shape(b), os.path.join(out, b["identifier"].replace(" ", "") + ".json"))
                n += 1
        save({"complete": True, "bulk": name, "done": date.today().isoformat()}, mark_path)
        if st == "hi":
            built = datetime(*z.getinfo(next(i for i in z.namelist() if i.endswith("_bills.json"))).date_time)
            state_path = os.path.join(folder, "state.json")
            state = load(state_path, {})
            for k in ("page", "began", "pass"):
                state.pop(k, None)
            state.update(complete=True, since=(built - timedelta(days=1)).isoformat(timespec="seconds"))
            save(state, state_path)
        print(f"{st} {year}: {n} bills from {name} (of {len(bills)} records)", flush=True)


if __name__ == "__main__":
    main(sys.argv[1])
