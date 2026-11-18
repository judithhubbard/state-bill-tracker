#!/usr/bin/env python3
"""Copies albanybilltracker.org's shared watchlists into State Bill Tracker's lists Worker, once, when New York moves.

Reads every list:, code: and views: key from the Albany lists Worker's KV namespace (LISTS) and writes them into
state-lists' namespace (STATE_LISTS), so a published New York list keeps its address (/list/#<slug>) and its owner's
browser keeps editing it with the same edit key (the stored editHash is copied as is). Lists get what
lists_worker/src/index.js expects that the Albany Worker didn't store: state "ny", hidden false, intro and notes.
Invite codes and view counts are copied unchanged. A key that already exists in STATE_LISTS is never overwritten
(it's listed as a conflict instead). The Albany namespace is only read.

Uses the owner's wrangler login: npx -y wrangler@4.152.0 kv ...

  python3 tools/copy_albany_lists.py --dry-run      what it would copy, writing nothing
  python3 tools/copy_albany_lists.py                copy (asks before writing)

For a test against wrangler's local storage instead of Cloudflare: --local --persist-to DIR, with --from/--to set to
made-up namespace ids.
"""
import argparse, json, os, re, subprocess, sys, tempfile

ALBANY_LISTS = "b642430e568b483a9a84adbd636f89a2"   # the live Albany namespace (LISTS): read only
STATE_LISTS = "180ec60d09f84eafb686aa0f0845ed67"    # state-lists' namespace
WRANGLER = ["npx", "-y", "wrangler@4.152.0"]
PREFIXES = ("list:", "code:", "views:")
BILL_RE = re.compile(r"^-?[A-Z]{1,7}\d{1,6}$")      # the lists Worker's BILL_RE
SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,60}$")


def wrangler(args, where):
    r = subprocess.run(WRANGLER + args + where, capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"wrangler {' '.join(args[:3])} failed:\n{r.stderr.strip() or r.stdout.strip()}")
    return r.stdout


def keys(ns, where):
    out = []
    for p in PREFIXES:
        text = wrangler(["kv", "key", "list", "--namespace-id", ns, "--prefix", p], where)
        out += [k["name"] for k in json.loads(text[text.index("["):])]
    return out


def get(ns, key, where):
    out = wrangler(["kv", "key", "get", key, "--namespace-id", ns, "--text"], where)
    return out[:-1] if out.endswith("\n") else out  # wrangler adds a line break


def convert(key, raw):
    """The value to store in STATE_LISTS, or (None, reason) to skip it."""
    try:
        v = json.loads(raw)
    except ValueError:
        return None, "not JSON"
    if key.startswith("list:"):
        if not isinstance(v, dict) or not SLUG_RE.match(key[5:]) or v.get("slug") != key[5:]:
            return None, "not a list"
        bills = [str(b).replace(" ", "").upper() for b in v.get("bills") or []]
        bad = [b for b in bills if not BILL_RE.match(b)]
        if bad:
            return None, f"bills the Worker would refuse: {bad[:5]}"
        if not v.get("editHash"):
            return None, "no edit hash"
        v.update(state="ny", bills=bills, hidden=bool(v.get("hidden")), intro=v.get("intro") or "",
                 notes=v.get("notes") or {}, group=v.get("group") or "", code=v.get("code") or "")
        v.setdefault("updated", v.get("created"))
    return json.dumps(v, separators=(",", ":"), ensure_ascii=False), None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true", help="print what would be copied; write nothing")
    ap.add_argument("--yes", action="store_true", help="don't ask before writing")
    ap.add_argument("--from", dest="src", default=ALBANY_LISTS)
    ap.add_argument("--to", dest="dst", default=STATE_LISTS)
    ap.add_argument("--local", action="store_true", help="wrangler's local storage, for a test")
    ap.add_argument("--persist-to", help="with --local: the local storage folder")
    a = ap.parse_args()
    if a.dst == ALBANY_LISTS:
        sys.exit("Refusing to write into the Albany namespace.")
    if a.local and (a.src == ALBANY_LISTS or a.dst == STATE_LISTS):
        sys.exit("For a local test, give made-up namespace ids with --from and --to.")
    where = ["--local"] + (["--persist-to", a.persist_to] if a.persist_to else []) if a.local else ["--remote"]

    src_keys, dst_keys = keys(a.src, where), set(keys(a.dst, where))
    writes, skipped, conflicts = [], [], []
    for k in sorted(src_keys, key=lambda k: (not k.startswith("code:"), k)):  # codes first: a list needs its code
        if k in dst_keys:
            conflicts.append(k)
            continue
        value, why = convert(k, get(a.src, k, where))
        if value is None:
            skipped.append((k, why))
        else:
            writes.append({"key": k, "value": value})

    count = lambda p: sum(1 for w in writes if w["key"].startswith(p))
    print(f"{len(src_keys)} keys in the Albany namespace: {count('list:')} lists, {count('code:')} invite codes, "
          f"{count('views:')} view counts to copy")
    for w in writes:
        if w["key"].startswith("list:"):
            l = json.loads(w["value"])
            print(f"  {w['key']}: \"{l.get('title')}\" ({l.get('group')}), session {l.get('session')}, {len(l['bills'])} bills")
    for k in conflicts:
        print(f"  CONFLICT, already in STATE_LISTS, left alone: {k}")
    for k, why in skipped:
        print(f"  SKIPPED {k}: {why}")
    if a.dry_run or not writes:
        print("Dry run: nothing written." if a.dry_run else "Nothing to write.")
        return
    if not a.yes and input(f"Write {len(writes)} keys into {a.dst}{' (local)' if a.local else ''}? [y/N] ").strip().lower() != "y":
        print("Nothing written.")
        return
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(writes, f)
    try:
        wrangler(["kv", "bulk", "put", f.name, "--namespace-id", a.dst], where)
    finally:
        os.unlink(f.name)
    # Check: every key written reads back the same.
    bad = [w["key"] for w in writes if get(a.dst, w["key"], where) != w["value"]]
    print(f"Wrote {len(writes)} keys; {len(writes) - len(bad)} read back the same." + (f" Differ: {bad}" if bad else ""))


if __name__ == "__main__":
    main()
