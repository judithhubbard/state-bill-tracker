#!/usr/bin/env python3
"""The bill-number hash that places a bill in a shard or a status piece is written twice: build_data.py's shard_of()
(which writes the files) and lists_pages/billfacts.js's BillFacts.hash() (which every page uses to find them). If they
ever disagree, pages fetch the wrong file and bills "aren't found". This runs both over real bill numbers (each built
state's status files in SITE, up to 300 a state, plus a few made-up ones) for several shard counts, and fails on any
difference.

Usage: python3 test/hash_check.py SITE    (a folder build_site.sh or build_data.py --github wrote)
"""
import glob, json, os, random, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)


def shard_of(num, n):
    # build_data.py's, read from the file (importing build_data.py needs a state).
    src = open(os.path.join(REPO, "build_data.py")).read()
    start = src.index("def shard_of(num, n):")
    end = src.index("\ndef ", start + 10)
    ns = {"re": __import__("re")}
    exec(src[start:end], ns)
    return ns["shard_of"](num, n)


def main(site):
    nums = {"S1234", "S1234A", "HB1", "A12345B", "HLD307", "SJR9", "HFS2", "LB304A", "HR8070", "SB26-135"}
    for f in sorted(glob.glob(os.path.join(site, "*", "data", "status_*.json"))):
        d = json.load(open(f, encoding="utf-8"))
        keys = sorted(d.get("bills", {})) + sorted(d.get("alias", {}))
        random.Random(f).shuffle(keys)
        nums.update(keys[:300])
        nums.update(b[0] for b in list(d.get("bills", {}).values())[:50])
    nums = sorted(nums)
    counts = [1, 3, 7, 13, 64, 101]
    py = {n: [shard_of(n, k) for k in counts] for n in nums}
    js = subprocess.run(["node", "-e", f"""
const B = require({json.dumps(os.path.join(REPO, "lists_pages", "billfacts.js"))});
const nums = JSON.parse(require("fs").readFileSync(0, "utf8"));
process.stdout.write(JSON.stringify(Object.fromEntries(nums.map((n) => [n, {json.dumps(counts)}.map((k) => B.hash(n) % k)]))));
"""], input=json.dumps(nums), capture_output=True, text=True, check=True)
    js = json.loads(js.stdout)
    bad = [n for n in nums if py[n] != js[n]]
    for n in bad[:20]:
        print(f"FAIL {n}: Python {py[n]}, JS {js[n]}")
    print(f"{len(nums)} bill numbers, {len(bad)} difference(s)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(REPO, "_site")))
