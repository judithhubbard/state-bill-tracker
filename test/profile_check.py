#!/usr/bin/env python3
"""Settings each state writes twice, in profile.py (the build) and profile.js (its pages and /your-bills/), must agree:
the lower house's letter and name (LOWER, LOWER_NAME / houses), the session's length (YEARS / years), the members' titles
(TITLES / titles), the session's label (session_label() / sessionLabel(), for every year 2017-2028) and each year's last
session day (SESSION_ENDS / dated: a day, or {end}); and the state's name (STATE_NAME) as home.html's and common.js's NAMES
write it. Missing settings fall back as the build and the page fall back
(build_data.py's LOW, TITLES, YEARS; tracker.html's TITLE, YEARS). The profile.js side is read by running it
(lists_pages/profilefacts.js). Fails on any difference.

Usage: python3 test/profile_check.py [STATE ...]   (default: every state with both files)
"""
import glob, importlib, json, os, subprocess, sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
YEARS_CHECKED = list(range(2017, 2029))


def js_settings(st):
    run = subprocess.run(["node", os.path.join(REPO, "lists_pages", "profilefacts.js"), os.path.join(REPO, "states", st, "profile.js"),
                          *map(str, YEARS_CHECKED)], capture_output=True, text=True)
    if run.returncode:
        raise SystemExit(f"{st}: profilefacts.js failed: {run.stderr[-500:]}")
    return json.loads(run.stdout)


def check(st):
    P = importlib.import_module(f"states.{st}.profile")
    J = js_settings(st)
    out = []
    low = getattr(P, "LOWER", "A")
    houses = J["houses"] or {}
    want_houses = {"S": "Senate", low: getattr(P, "LOWER_NAME", "Assembly")} if low != "L" else None
    if want_houses is not None and houses != want_houses:
        out.append(f"houses: profile.js {houses}, profile.py {want_houses}")
    years = J["years"] or 2
    if years != getattr(P, "YEARS", 2):
        out.append(f"years: profile.js {years}, profile.py YEARS {getattr(P, 'YEARS', 2)}")
    # (Each house's title: Nebraska's profile.py also titles an "S" it doesn't have.)
    titles = J["titles"] or {"S": "Sen.", low: "Asm."}
    py_titles = getattr(P, "TITLES", {"S": "Sen.", low: "Asm."})
    for h in houses or {"S": 1, low: 1}:
        if titles.get(h) != py_titles.get(h):
            out.append(f"title of {h}: profile.js {titles.get(h)!r}, profile.py {py_titles.get(h)!r}")
    for y in YEARS_CHECKED:
        js_label = J["sessionLabel"][str(y)] if J["sessionLabel"][str(y)] is not None else str(y)
        if str(P.session_label(y)) != js_label:
            out.append(f"session label of {y}: profile.js {js_label!r}, profile.py {P.session_label(y)!r}")
    ends = getattr(P, "SESSION_ENDS", None)
    if ends:
        dated = {int(k): (v.get("end") if isinstance(v, dict) else v) for k, v in (J["dated"] or {}).items()}
        for y, d in ends.items():
            if dated.get(int(y)) != d:
                out.append(f"last session day of {y}: profile.js dated {dated.get(int(y))}, profile.py SESSION_ENDS {d}")
        for y in sorted(set(dated) - {int(y) for y in ends}):
            out.append(f"last session day of {y}: profile.js dated {dated[y]}, not in profile.py's SESSION_ENDS")
    # The state's name, as the front page (home.html's NAMES) and the list pages (lists_pages/common.js's NAMES) write it.
    if st != "us":
        for f, key in (("home.html", st.upper()), ("lists_pages/common.js", st)):
            got = page_names(f).get(key)
            if got != P.STATE_NAME:
                out.append(f"name: {f} {got!r}, profile.py STATE_NAME {P.STATE_NAME!r}")
    return out


_NAMES = {}


def page_names(f):
    """A page's table of state names ({code: name}, "const NAMES = {...};")."""
    if f not in _NAMES:
        import re
        src = open(os.path.join(REPO, f), encoding="utf-8").read()
        m = re.search(r"\nconst NAMES = \{(.*?)\};\n", src, re.S)
        _NAMES[f] = dict(re.findall(r'\b([A-Za-z]{2}): "([^"]+)"', m.group(1))) if m else {}
    return _NAMES[f]


def main(states):
    states = states or sorted(os.path.basename(os.path.dirname(p)) for p in glob.glob(os.path.join(REPO, "states", "*", "profile.js"))
                              if os.path.exists(os.path.join(os.path.dirname(p), "profile.py")))
    bad = 0
    for st in states:
        for line in check(st):
            bad += 1
            print(f"FAIL {st}: {line}")
    print(f"profile_check: {len(states)} states, {f'{bad} FAIL' if bad else 'profile.py and profile.js agree'}")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main(sys.argv[1:])
