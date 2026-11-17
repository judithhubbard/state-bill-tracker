#!/usr/bin/env python3
"""The front page's "Find a bill" search data (home.html): search/<st>.json for each built state and Congress, from the
state's data/status_<session>.json (build_data.py's write_status()). Run by build_site.sh after the states are built, so a
change here rebuilds no state.

Only the sessions still live (the current one, and next year's prefiled bills where a state lists them): past sessions
would more than double the download. Each file is small enough to load all 51 on a phone when the box is first used
(Cloudflare compresses them); a query naming a state loads that state's first.

Each file: {"st", "name", "s": [{"session", "page" ("" for the state's index page), "live", "up" (prefiled for a session
not begun), "b": [[number, title, stage, ("c" for a constitutional amendment, else 0), [other numbers]?], ...]}]}.
Titles are cut at about 110 characters (at a word).

Usage: python3 search_site.py SITE_DIR
"""
import glob, importlib, json, os, re, sys

CUT = 110


def short(t):
    t = re.sub(r"\s+", " ", t or "").strip()
    if len(t) <= CUT:
        return t
    return t[:CUT].rsplit(" ", 1)[0].rstrip(",;:") + "…"


def main(out):
    os.makedirs(os.path.join(out, "search"), exist_ok=True)
    total = 0
    for st in sorted(os.listdir(out)):
        if len(st) != 2 or not os.path.exists(os.path.join(out, st, "index.html")):
            continue
        files = []
        for f in glob.glob(os.path.join(out, st, "data", "status_*.json")):
            try:
                files.append(json.load(open(f, encoding="utf-8")))
            except (OSError, ValueError):
                pass
        if not files:
            continue
        newest = max(d["session"] for d in files)
        sessions = []
        for d in sorted(files, key=lambda d: d["session"]):
            live = d.get("live", d["session"] == newest)
            if not live:
                continue
            page = "" if d.get("page") in ("./", "", None) else d["page"]
            others = {}
            for a, lead in (d.get("alias") or {}).items():
                others.setdefault(lead, []).append(a)
            rows = []
            for key, b in d["bills"].items():
                row = [b[0], short(b[1]), b[2], "c" if b[6] == "const" else 0]
                if key in others:
                    row.append(others[key])
                rows.append(row)
            sessions.append({"session": d["session"], "page": page, "live": True, "up": bool(page), "b": rows})
            total += len(rows)
        if not sessions:
            continue
        try:
            name = "Congress" if st == "us" else importlib.import_module(f"states.{st}.profile").STATE_NAME
        except Exception:
            name = st.upper()
        with open(os.path.join(out, "search", f"{st}.json"), "w", encoding="utf-8") as f:
            json.dump({"st": st, "name": name, "s": sessions}, f, separators=(",", ":"), ensure_ascii=False)
    print(f"search: {total} bills")


if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    main(sys.argv[1])
