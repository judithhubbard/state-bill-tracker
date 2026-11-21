#!/usr/bin/env python3
"""The site's colors are written in several pages (notes/duplication.md, item 11): each page's color tokens on :root, light
and dark (under @media (prefers-color-scheme: dark) and again under :root[data-theme="dark"]). A token two pages both
define must have the same value in both, in each mode, and a page's two dark blocks must agree with each other; so the
teal (--navy) and the rest can't drift apart between the state pages, the front page, the list pages and the others.
issues_site.py reads home.html's tokens (one copy); compare_site.py's TOKENS are checked here like a page.

Usage: python3 test/tokens_check.py    (prints each token that differs, and fails)
"""
import os, re, sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
FILES = ["tracker.html", "home.html", "lists_pages/common.css", "about.html", "notfound.html", "lists_pages/welcome-ny.html",
         "build_data.py", "compare_site.py"]
# Tokens that mean different things on different pages (the same name, not a copy): --pty-d/--pty-r are tracker.html's
# party chips (soft backgrounds under dark ink: .pty, .bp-D) and home.html's party badges and map shades (.pD, .pR).
OWN = {"--pty-d", "--pty-r"}
# The same color under another name: the legislator chooser page (build_data.py's choose_page()) calls the teal --link.
ALIASES = {"build_data.py": {"--link": "--navy"}}


def blocks(src):
    """{mode: {token: value}} from a file's :root blocks: "light" (plain :root), "dark" (inside the media query),
    "dark-attr" (:root[data-theme="dark"])."""
    out = {"light": {}, "dark": {}, "dark-attr": {}}
    media = [(m.start(), m.end() + _close(src, m.end())) for m in re.finditer(r"@media \(prefers-color-scheme: dark\)\s*\{", src)]
    for m in re.finditer(r':root(\[data-theme="dark"\]|:not\(\[data-theme="light"\]\))?\s*\{([^}]*)\}', src):
        inside = any(a <= m.start() < b for a, b in media)
        mode = "dark-attr" if m.group(1) == '[data-theme="dark"]' else "dark" if inside or m.group(1) else "light"
        for k, v in re.findall(r"(--[a-z0-9-]+)\s*:\s*([^;]+);", m.group(2)):
            out[mode][k] = v.strip()
    return out


def _close(src, i):
    """The length from i to the brace that closes the block opened just before i."""
    depth, j = 1, i
    while depth and j < len(src):
        depth += {"{": 1, "}": -1}.get(src[j], 0)
        j += 1
    return j - i


def main():
    seen = {}
    bad = 0
    for f in FILES:
        b = blocks(open(os.path.join(REPO, f), encoding="utf-8").read())
        b = {m: {ALIASES.get(f, {}).get(k, k): v for k, v in vals.items()} for m, vals in b.items()}
        # A page's two dark blocks say the same.
        for k in set(b["dark"]) | set(b["dark-attr"]):
            if b["dark"] and b["dark-attr"] and b["dark"].get(k) != b["dark-attr"].get(k):
                bad += 1
                print(f"FAIL {f}: {k} is {b['dark'].get(k)} in the dark media query, {b['dark-attr'].get(k)} under data-theme=dark")
        for mode in ("light", "dark"):
            vals = b[mode] or (b["dark-attr"] if mode == "dark" else {})
            for k, v in vals.items():
                if k in OWN:
                    continue
                seen.setdefault((mode, k), []).append((f, v))
    for (mode, k), xs in sorted(seen.items()):
        if len({v.lower() for _, v in xs}) > 1:
            bad += 1
            print(f"FAIL {k} ({mode}): " + ", ".join(f"{f} {v}" for f, v in xs))
    shared = sum(1 for xs in seen.values() if len(xs) > 1)
    print(f"tokens_check: {len(FILES)} files, {shared} tokens defined in more than one, {f'{bad} FAIL' if bad else 'all the same'}")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
