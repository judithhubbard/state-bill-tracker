#!/bin/bash
# Checks that a change to the page didn't change what visitors see: records every tab, How section,
# 25 open bills and a watchlist of 8 (test/snapshot.js) from built pages, and compares them with
# the pages built from another commit (default: HEAD).
# Usage: test/same.sh [commit] [session ...]   (default sessions: 2025 2023)
set -e
cd "$(dirname "$0")/.."
REF=${1:-HEAD}; shift || true
SESSIONS=${*:-2025 2023}
TMP=$(mktemp -d)
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

snap() {  # snap DIR: build the sessions in DIR and record each page
  for s in $SESSIONS; do
    (cd "$1" && python3 build_data.py "$s" > /dev/null)
    cat "$1/site/$s.html" test/snapshot.js > "$TMP/page.html"
    "$CHROME" --headless=new --disable-gpu --user-data-dir="$TMP/chrome-$(basename "$2")-$s" --virtual-time-budget=60000 \
      --dump-dom "file://$TMP/page.html" 2>/dev/null |
      python3 -c "import html,re,sys; m=re.search(r'<pre id=\"SNAP\">(.*?)</pre>', sys.stdin.read(), re.S); print(html.unescape(m.group(1)) if m else 'NO SNAPSHOT')" > "$2.$s"
  done
}

git worktree add -q "$TMP/old" "$REF"
cp -R data/. "$TMP/old/data/"   # untracked fresh downloads
snap "$TMP/old" "$TMP/old.snap"
snap . "$TMP/new.snap"
git worktree remove --force "$TMP/old"

status=0
for s in $SESSIONS; do
  if grep -q "NO SNAPSHOT" "$TMP/new.snap.$s"; then echo "$s: the page didn't finish loading"; status=1; continue; fi
  if cmp -s "$TMP/old.snap.$s" "$TMP/new.snap.$s"; then
    echo "$s: same ($(grep -c '^=== ' "$TMP/new.snap.$s") parts compared)"
  else
    echo "$s: DIFFERENT"; diff "$TMP/old.snap.$s" "$TMP/new.snap.$s" | head -40; status=1
  fi
done
rm -rf "$TMP"
exit $status
