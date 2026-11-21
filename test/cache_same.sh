#!/bin/bash
# Builds states twice, once working everything out (BUILD_CACHE=off) and once from the build cache (build_data.py's
# data_bundle() and cached_json()), and fails if the two differ by a byte: a cache that went stale (a file the build
# reads that isn't in its key, test/cache_key_check.py's subject) shows up here as a difference.
# The cache is a copy of CACHE_FROM (a build cache folder, such as publish.yml's built/cache, so what's compared is what
# the next publish would reuse), or, without it, made by one build first. Nothing outside a temporary folder is changed.
# Usage: test/cache_same.sh wy sd ...
#        CACHE_FROM=built/cache SITE_BASE=https://statebilltracker.pages.dev/ test/cache_same.sh wy sd   (publish.yml's cache)
set -u
cd "$(dirname "$0")/.."
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
# The address is part of the cache's key: with SITE_BASE, each state's is SITE_BASE/<state>/, as build_site.sh makes it.
status=0
for s in "$@"; do
  if [ -n "${SITE_BASE:-}" ]; then export SITE_URL="${SITE_BASE}$s/"; else export SITE_URL=${SITE_URL:-http://localhost:8765/}; fi
  mkdir -p "$TMP/cache"
  if [ -n "${CACHE_FROM:-}" ] && [ -d "$CACHE_FROM/$s" ]; then
    cp -R "$CACHE_FROM/$s" "$TMP/cache/$s"
  else
    BUILD_CACHE="$TMP/cache" python3 build_data.py --state "$s" --github "$TMP/prime/$s" > "$TMP/$s.prime.log" 2>&1 \
      || { echo "FAIL $s: the build failed"; tail -5 "$TMP/$s.prime.log"; status=1; continue; }
  fi
  BUILD_CACHE=off python3 build_data.py --state "$s" --github "$TMP/off/$s" > "$TMP/$s.off.log" 2>&1 \
    || { echo "FAIL $s: the build failed"; tail -5 "$TMP/$s.off.log"; status=1; continue; }
  BUILD_CACHE="$TMP/cache" python3 build_data.py --state "$s" --github "$TMP/cached/$s" > "$TMP/$s.cached.log" 2>&1 \
    || { echo "FAIL $s: the build from the cache failed"; tail -5 "$TMP/$s.cached.log"; status=1; continue; }
  how=$(grep -q '^data unchanged' "$TMP/$s.cached.log" && echo "its data from the cache" || echo "its data worked out again (the cache's key didn't match), the slow steps' caches reused")
  if diff -rq "$TMP/off/$s" "$TMP/cached/$s" > "$TMP/$s.diff"; then
    echo "$s: the same both ways ($(find "$TMP/off/$s" -type f | wc -l | tr -d ' ') files; the cached build took $how)."
  else
    echo "FAIL $s: the cached build ($how) differs from a build without the cache:"
    head -20 "$TMP/$s.diff"
    # The first differing text file, in brief.
    f=$(grep -m1 '^Files ' "$TMP/$s.diff" | sed -E 's/^Files (.*) and .*/\1/')
    if [ -n "$f" ]; then diff <(tr ',' '\n' < "$f") <(tr ',' '\n' < "${f/\/off\//\/cached\/}") | head -20; fi
    status=1
  fi
done
exit $status
