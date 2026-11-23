#!/usr/bin/env python3
"""The front page's "Find a bill" search data (home.html): search/<st>.json for each built state and Congress, from the
state's data/status_<session>.json (build_data.py's write_status()). Run by build_site.sh after the states are built, so a
change here rebuilds no state.

search/<st>.json has only the sessions still live (the current one, and next year's prefiled bills where a state lists
them), small enough to load all 51 on a phone when the box is first used (Cloudflare compresses them); a query naming a
state loads that state's first. search/<st>.past.json has every other session the state's site shows, newest first,
loaded only when the visitor asks for earlier sessions too (home.html's "Earlier sessions"). When a state's earlier
sessions are big (over PAST_GZ gzipped), that file holds the newest of them and "more": [session, ...], each in
search/<st>.past.<session>.json.

Each file: {"st", "name", "s": [{"session", "label" ("2025–26": shown beside a result when a state has two sessions in the
search, and on every earlier session's), "page" ("" for the state's index page), "live", "up" (prefiled for a session not begun), "w": [status words (as the state's page words them: build_data.py's
bill_labels())], "b": [[number, title, stage, its status words' index in "w", [other numbers]?], ...],
"t": {issue id: [indexes into b]}}], "more"?}: "t" is each national issue's bills (the state's data/issues_<session>.json), so a
search for "kratom" also finds "Prohibits the sale of 7-hydroxymitragynine products". search/topics.json gives each issue
the words that call it up: its name, short name and issues.py's "words".
Titles are cut at about 110 characters (at a word).

Usage: python3 search_site.py SITE_DIR
"""
import glob, gzip, importlib, json, os, re, sys

CUT = 110
# A state's earlier sessions are one file unless it would be bigger than this gzipped; then one file a session.
PAST_GZ = 600_000


def short(t):
    t = re.sub(r"\s+", " ", t or "").strip()
    if len(t) <= CUT:
        return t
    return t[:CUT].rsplit(" ", 1)[0].rstrip(",;:") + "…"


def session_rows(out, st, d):
    """One session's search record, from its status file (and its issues file: the label and each bill's issues)."""
    page = "" if d.get("page") in ("./", "", None) else d["page"]
    others = {}
    for a, lead in (d.get("alias") or {}).items():
        others.setdefault(lead, []).append(a)
    # Each national issue's bills in this session, by number without its amendment letter.
    on, label = {}, str(d["session"])
    try:
        iss = json.load(open(os.path.join(out, st, "data", f"issues_{d['session']}.json"), encoding="utf-8"))
        label = iss.get("label") or label
        for x in iss["bills"]:
            for n in [x[2], *(x[10] if len(x) > 10 else [])]:
                on.setdefault(re.sub(r"[A-Z]$", "", n), set()).update(x[0])
    except (OSError, ValueError, KeyError):
        pass
    rows, tags, words = [], {}, {}
    for key, b in d["bills"].items():
        # (Sorted, so the file is the same from build to build: a set's order changes with each run.)
        for i in sorted(on.get(key, set()) | on.get(re.sub(r"[A-Z]$", "", b[0]), set())):
            tags.setdefault(i, []).append(len(rows))
        row = [b[0], short(b[1]), b[2], words.setdefault(b[11] if len(b) > 11 else "", len(words))]
        if key in others:
            row.append(others[key])
        rows.append(row)
    return {"session": d["session"], "label": label, "page": page, "live": bool(d["live"]), "up": bool(d["live"] and page),
            "w": list(words), "b": rows, "t": tags}


def text_of(d):
    return json.dumps(d, separators=(",", ":"), ensure_ascii=False)


def dump(path, d):
    with open(path, "w", encoding="utf-8") as f:
        f.write(text_of(d))


def main(out):
    os.makedirs(os.path.join(out, "search"), exist_ok=True)
    total = past_total = 0
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
        for d in files:
            d["live"] = d.get("live", d["session"] == newest)
        live = [session_rows(out, st, d) for d in sorted(files, key=lambda d: d["session"]) if d["live"]]
        past = [session_rows(out, st, d) for d in sorted(files, key=lambda d: -d["session"]) if not d["live"]]
        try:
            name = "Congress" if st == "us" else importlib.import_module(f"states.{st}.profile").STATE_NAME
        except Exception:
            name = st.upper()
        if live:
            dump(os.path.join(out, "search", f"{st}.json"), {"st": st, "name": name, "s": live})
            total += sum(len(s["b"]) for s in live)
        for f in glob.glob(os.path.join(out, "search", f"{st}.past*.json")):
            os.remove(f)
        if not past:
            continue
        whole = {"st": st, "name": name, "s": past}
        if len(past) > 1 and len(gzip.compress(text_of(whole).encode("utf-8"), 6)) > PAST_GZ:
            for s in past[1:]:
                dump(os.path.join(out, "search", f"{st}.past.{s['session']}.json"), {"st": st, "name": name, "s": [s]})
            whole = {"st": st, "name": name, "s": past[:1], "more": [s["session"] for s in past[1:]]}
        dump(os.path.join(out, "search", f"{st}.past.json"), whole)
        past_total += sum(len(s["b"]) for s in past)
    import issues, issues_site
    with open(os.path.join(out, "search", "topics.json"), "w", encoding="utf-8") as f:
        json.dump({i["id"]: sorted({i["name"].lower(), issues_site.SHORT.get(i["id"], i["name"]).lower(),
                                    *(w.lower() for w in i.get("words", []))}) for i in issues.ISSUES},
                  f, separators=(",", ":"), ensure_ascii=False)
    print(f"search: {total} bills; {past_total} more in earlier sessions")


if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    main(sys.argv[1])
