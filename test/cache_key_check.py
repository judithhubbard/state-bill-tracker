#!/usr/bin/env python3
"""The build reuses what it worked out before when its key hasn't changed (build_data.py's bundle_key(), BUILD_CACHE), and
build_site.sh copies a state's last pages when state_hash.py's fingerprint hasn't changed. Both keys list the files a
state's build reads (state_hash.data_files() and page_files()); a file the build reads that isn't listed can change without
the state being rebuilt, and the site then shows stale pages with no error. This fails when that can happen:

  1. Imports, for every state (static): the Python files build_data.py, each state's profile.py and convert.py, and what
     they import (states.<st>.x, the shared modules at the top of the repo and in states/) must be in its lists.
  2. Every file opened, for one state (dynamic): builds it once (BUILD_CACHE=off, into a temporary folder) with an audit
     hook that records each file of the repository opened for reading, and each module loaded. What compute() reads (the
     data side, kept in the cache) must be in data_files(); what the rest reads (the pages) in data_files() or page_files().
     profile.js is the one page file compute() may read: the cache checks its hooks (profile_hooks()) separately.

Usage: python3 test/cache_key_check.py [STATE]     (default wy; part 2 is skipped when the state has no downloaded data)
       python3 test/cache_key_check.py --static    only part 1
"""
import ast, contextlib, glob, os, shutil, sys, tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
import state_hash  # noqa: E402

# Read but not an input of the public build: the Claude copies' addresses, which a --github build (the only one that
# caches) replaces.
NOT_INPUTS = {os.path.realpath(os.path.join(REPO, "artifact_urls.json"))}
# The build's own output and caches.
IGNORE_DIRS = ("site", "_site", "built", ".build-cache", ".git", "__pycache__", "node_modules")


def module_file(name):
    """The repository file for a module name, or None (the standard library, pip packages)."""
    base = os.path.join(REPO, *name.split("."))
    for p in (base + ".py", os.path.join(base, "__init__.py")):
        if os.path.exists(p):
            return p
    return None


_IMPORTS = {}


def imports_of(path):
    """Module names a file imports: import statements, and importlib.import_module("literal")."""
    if path not in _IMPORTS:
        _IMPORTS[path] = list(_imports_of(path))
    return _IMPORTS[path]


def _imports_of(path):
    tree = ast.parse(open(path, encoding="utf-8").read(), path)
    pkg = os.path.relpath(os.path.dirname(path), REPO).replace(os.sep, ".")
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                yield a.name
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                parts = pkg.split(".")
                base = ".".join(parts[:len(parts) - node.level + 1])
                mod = f"{base}.{node.module}" if node.module else base
            else:
                mod = node.module
            yield mod
            for a in node.names:  # "from states.wy import convert" names a module too
                yield f"{mod}.{a.name}"
        elif (isinstance(node, ast.Call) and getattr(node.func, "attr", getattr(node.func, "id", "")) == "import_module"
              and node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str)):
            yield node.args[0].value


def closure(roots):
    seen, todo = set(), [p for p in roots if p]
    while todo:
        p = todo.pop()
        if p in seen:
            continue
        seen.add(p)
        for name in imports_of(p):
            parts = name.split(".")
            # A module and its packages (importing states.wy.convert runs states/__init__.py and states/wy/__init__.py).
            for i in range(1, len(parts) + 1):
                f = module_file(".".join(parts[:i]))
                if f and f not in seen:
                    todo.append(f)
    return seen


def states():
    return sorted(os.path.basename(os.path.dirname(p)) for p in glob.glob(os.path.join(REPO, "states", "*", "profile.py")))


def static_check():
    bad = []
    for st in states():
        roots = [os.path.join(REPO, "build_data.py"), os.path.join(REPO, "states", st, "profile.py"),
                 os.path.join(REPO, "states", st, "convert.py") if os.path.exists(os.path.join(REPO, "states", st, "convert.py")) else None]
        # (Which side reads a module, the data's or the pages', is part 2's question; issues.py is the pages'.)
        covered = set(state_hash.data_files(st)) | set(state_hash.page_files(st))
        for f in sorted(closure(roots) - covered):
            bad.append(f"{st}: the build imports {os.path.relpath(f, REPO)}, which state_hash.py's lists leave out")
    return bad


def in_repo(path):
    try:
        p = os.path.realpath(os.fsdecode(path))
    except (TypeError, ValueError):
        return None
    if not p.startswith(REPO + os.sep):
        return None
    rel = os.path.relpath(p, REPO)
    if rel.split(os.sep)[0] in IGNORE_DIRS or "__pycache__" in rel.split(os.sep):
        return None
    return p


def dynamic_check(st):
    """Build one state with an audit hook; return the problems, or None when the state has no data here."""
    out = tempfile.mkdtemp(prefix="cache-key-")
    sys.argv = ["build_data.py", "--state", st, "--github", out]
    os.environ["BUILD_CACHE"] = "off"
    os.environ.setdefault("SITE_URL", "http://localhost:8765/")
    phase = ["load"]
    reads = {"load": set(), "compute": set(), "pages": set()}

    def hook(event, args):
        if event == "open" and args and isinstance(args[0], (str, bytes, os.PathLike)):
            mode = args[1] if len(args) > 1 and isinstance(args[1], str) else "r"
            if any(c in mode for c in "wax+"):
                return
            p = in_repo(args[0])
            if p and not p.startswith(os.path.realpath(out)) and os.path.isfile(p):
                reads[phase[0]].add(p)
    sys.addaudithook(hook)
    os.chdir(REPO)
    # Modules count as read in the phase that loaded them (their .py may not be opened when a fresh .pyc is read).
    loaded = [set(sys.modules)]

    def modules_into(where):
        now = set(sys.modules)
        for name in now - loaded[0]:
            f = getattr(sys.modules[name], "__file__", None)
            p = in_repo(f) if f else None
            if p and p.endswith(".py"):
                reads[where].add(p)
        loaded[0] = now
    import build_data as B
    modules_into("load")
    phase[0] = "pages"
    folder = getattr(B.P, "DATA", os.path.join(REPO, "data", st))
    if not B.ONLY or not (glob.glob(os.path.join(folder, "*", "*")) or glob.glob(os.path.join(folder, "bills_*"))):
        return None
    compute = B.compute

    def traced(*a, **k):
        modules_into(phase[0])
        phase[0] = "compute"
        try:
            return compute(*a, **k)
        finally:
            modules_into("compute")
            phase[0] = "pages"
    B.compute = traced
    with open(os.devnull, "w") as quiet, contextlib.redirect_stdout(quiet):
        B.main()
    shutil.rmtree(out, ignore_errors=True)
    modules_into("pages")
    data = {os.path.realpath(p) for p in state_hash.data_files(st)}
    page = {os.path.realpath(p) for p in state_hash.page_files(st)}
    profile_js = os.path.realpath(os.path.join(REPO, "states", st, "profile.js"))
    bad = []
    for p in sorted(reads["load"] | reads["compute"]):
        if p in data or p == profile_js or p in NOT_INPUTS:
            continue
        where = "is only in page_files(): a change to it rewrites the pages but reuses the old data" if p in page else \
            "isn't in state_hash.py's lists"
        bad.append(f"{st}: the build works its data out from {os.path.relpath(p, REPO)}, which {where}")
    for p in sorted(reads["pages"] - data - page - NOT_INPUTS):
        bad.append(f"{st}: the build writes its pages from {os.path.relpath(p, REPO)}, which isn't in state_hash.py's lists")
    n = len(reads["load"] | reads["compute"] | reads["pages"])
    if not bad:
        print(f"Build of {st}: {n} files of the repository read, every one in its cache key.")
    return bad


def main():
    args = sys.argv[1:]
    bad = static_check()
    print(f"Imports: {len(states())} states checked.")
    if "--static" not in args:
        st = args[0] if args else "wy"
        dyn = dynamic_check(st)
        if dyn is None:
            print(f"(No downloaded data for {st} here: the build's file reads weren't checked.)")
        else:
            bad += dyn
    for line in bad:
        print("FAIL", line)
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
