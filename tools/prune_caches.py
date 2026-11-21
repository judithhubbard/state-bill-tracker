#!/usr/bin/env python3
"""Deletes the older Actions caches of one family (all but the newest two) once a newer one is saved: each job restores only the newest
(restore-keys picks it), so the older copies only fill the repository's 10 GB and push other states' copies out (2026-11-21:
10.5 GB, 11 copies of most states, 13 of built-pages).

Usage: python3 tools/prune_caches.py PREFIX KEEP   (in a workflow, with GH_TOKEN and `actions: write`)
  e.g. tools/prune_caches.py wi-data-v1- wi-data-v1-44886779488
Nothing is deleted unless KEEP itself is listed (a save that failed leaves the older copies alone).
"""
import json, subprocess, sys


def main(prefix, keep):
    run = subprocess.run(["gh", "cache", "list", "--key", prefix, "--limit", "100", "--json", "id,key,createdAt"],
                         capture_output=True, text=True)
    if run.returncode:
        print(f"caches not listed: {run.stderr.strip()}")
        return 0
    caches = [c for c in json.loads(run.stdout) if c["key"].startswith(prefix)]
    if not any(c["key"] == keep for c in caches):
        print(f"{keep} isn't saved; older copies kept")
        return 0
    # The one before it stays too: a publish run may be restoring it at this moment (publish.yml restores every state's
    # newest copy while downloads go on).
    older = sorted((c for c in caches if c["key"] != keep), key=lambda c: c["createdAt"], reverse=True)
    for c in older[1:]:
        d = subprocess.run(["gh", "cache", "delete", str(c["id"])], capture_output=True, text=True)
        print(f"deleted {c['key']}" if not d.returncode else f"{c['key']} not deleted: {d.stderr.strip()}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2]))
