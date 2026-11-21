#!/bin/bash
# Quick check after editing tracker.html or build_data.py:
#   1. the page's main script parses (a duplicate name or stray bracket breaks the whole page),
#   2. the current session's page builds,
#   3. headless Chrome clicks every button, tab and filter and reports script errors,
#   and every file the build reads is in the build cache's key (test/cache_key_check.py).
# Usage: test/check.sh [session]   (default: the newest session in data/)
set -e
cd "$(dirname "$0")/.."
TMP=$(mktemp -d)
SESSION=${1:-$(ls data/bills_*.json* | sed -E 's/.*bills_([0-9]{4}).*/\1/' | sort -n | tail -1)}
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

python3 -c "
import re, sys
s = open('tracker.html').read()
open(sys.argv[1], 'w').write(max(re.findall(r'<script>(.*?)</script>', s, re.S), key=len))
" "$TMP/main.js"
node --check "$TMP/main.js" && for f in states/*/profile.js; do node --check "$f"; done && echo "Scripts parse."

# Top-level functions declared twice silently replace each other (no error), so look for them.
DUPES=$(grep -oE '^(async )?function [A-Za-z0-9_]+' tracker.html | awk '{print $NF}' | sort | uniq -d)
if [ -n "$DUPES" ]; then echo "Functions declared twice: $DUPES"; exit 1; fi

# Each state's governor's deadline against its constitution's rule (test/deadlines.js; under a second).
node test/deadlines.js > "$TMP/deadlines.txt" || { grep -v '^KNOWN' "$TMP/deadlines.txt"; exit 1; }
tail -1 "$TMP/deadlines.txt"

# Every file the build reads is in the build cache's key (state_hash.py), so the cache can't go stale (about 30 s).
python3 test/cache_key_check.py wy

# Logic and settings written in both the build (Python) and the pages (JavaScript) must agree (notes/duplication.md):
# the build's ports of page logic against tracker.html
# (test/ports_check.js), on a public build of one small state (from the build cache, .build-cache/, after the first time).
PUB=${PUB_STATE:-wy}
if [ -n "$(ls "data/$PUB" 2>/dev/null | grep -v district_towns.json)" ]; then
  SITE_URL=http://localhost:8765/ python3 build_data.py --state "$PUB" --github "$TMP/pub/$PUB" > "$TMP/pub.log" 2>&1 || { tail -20 "$TMP/pub.log"; exit 1; }
  node test/ports_check.js "$TMP/pub"
else
  echo "(No data for $PUB here: test/ports_check.js skipped.)"
fi

python3 build_data.py "$SESSION" > "$TMP/build.log" 2>&1 || { tail -20 "$TMP/build.log"; exit 1; }
echo "Built site/$SESSION.html."

cat "site/$SESSION.html" test/crawl.js > "$TMP/crawl.html"
"$CHROME" --headless=new --disable-gpu --user-data-dir="$TMP/chrome" --virtual-time-budget=60000 \
  --dump-dom "file://$TMP/crawl.html" 2>/dev/null > "$TMP/dom.html"
python3 - "$TMP/dom.html" <<'PY'
import html, re, sys
d = open(sys.argv[1]).read()
m = re.search(r'<pre id="RESULT">(.*?)</pre>', d, re.S)
if not m:
    sys.exit("The click test didn't finish (the page may not have loaded).")
out = html.unescape(m.group(1))
for line in out.splitlines():
    if line.startswith("clicked") or "ERROR" in line:
        print(line)
sys.exit(1 if re.search(r"ERRORS: \S", out) or "  ERROR" in out else 0)
PY
echo "Click test passed."
rm -rf "$TMP"
