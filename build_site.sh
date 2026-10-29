#!/bin/bash
# Builds statebilltracker.org into one folder: the front page (home.html), the icons, and each state's
# public site in its own folder (/nj/ …). Cloudflare Pages serves the folder (see .github/workflows/update.yml).
# Until launch, every page tells search engines not to list it (_headers and robots.txt); set LAUNCHED=1 then.
# Usage: ./build_site.sh [DIR]   (default: _site)
set -e
cd "$(dirname "$0")"
OUT=${1:-_site}
STATES="nj"
rm -rf "$OUT" && mkdir -p "$OUT"
for s in $STATES; do
  python3 build_data.py --state "$s" --github "$OUT/$s"
done
cp home.html "$OUT/index.html"
# The pages ask for their icons at the top of the site.
cp "$OUT/nj/favicon.ico" "$OUT/nj/favicon-32.png" "$OUT/nj/apple-touch-icon.png" "$OUT/"
if [ "${LAUNCHED:-0}" = 1 ]; then
  printf 'User-agent: *\nAllow: /\n' > "$OUT/robots.txt"
else
  printf 'User-agent: *\nDisallow: /\n' > "$OUT/robots.txt"
  printf '/*\n  X-Robots-Tag: noindex\n' > "$OUT/_headers"
fi
echo "Built $OUT/ ($(find "$OUT" -type f | wc -l | tr -d ' ') files)"
