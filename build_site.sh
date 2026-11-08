#!/bin/bash
# Builds statebilltracker.org into one folder: the front page (home.html), the icons, and each state's
# public site in its own folder (/nj/ …). Cloudflare Pages serves the folder (see .github/workflows/publish.yml).
# Until launch, every page tells search engines not to list it (_headers and robots.txt); set LAUNCHED=1 then.
# Usage: ./build_site.sh [DIR]   (default: _site)
set -e
cd "$(dirname "$0")"
OUT=${1:-_site}
STATES=${ONLY:-"ak ar az ca co ct ga il in ma md me mi nc nh nj oh ok or pa ri sd tn tx ut va vt wa wi wy"}  # ONLY="wy sd" for a quick local test
# New York from this shared code (/ny/, not linked from the front page until New York moves here; until then
# albanybilltracker.org runs from its own repo), when the current session's bills are here (the workflow
# downloads them with the Senate API key).
NY=$(python3 -c "import datetime; y = datetime.date.today().year; print(y if y % 2 else y - 1)")
if [ -f "data/bills_$NY.json" ]; then STATES="$STATES ny"; fi
rm -rf "$OUT" && mkdir -p "$OUT"
# Each state's pages from earlier builds, with the fingerprint they were built from.
BUILT=${BUILT:-built}
mkdir -p "$BUILT"
REBUILT=""
for s in $STATES; do
  # A state whose first full download is still building up over several runs (data/<state>/incomplete, written by
  # its fetch.py) waits: a partial copy would make a misleading site, or fail the build for every state.
  if [ -f "data/$s/incomplete" ]; then echo "$s: download not complete yet; not built"; continue; fi
  # SITE_BASE (the preview's address) gives each state its own: SITE_BASE/nj/, SITE_BASE/va/.
  if [ -n "$SITE_BASE" ]; then export SITE_URL="${SITE_BASE}$s/"; fi
  # A state whose data, code and settings haven't changed since the last build (state_hash.py; publish.yml keeps
  # $BUILT between runs) is copied from it rather than rebuilt; every state is rebuilt at least once a day.
  hash=$(python3 state_hash.py "$s")
  if [ -f "$BUILT/$s.hash" ] && [ "$(cat "$BUILT/$s.hash")" = "$hash" ] && [ -f "$BUILT/$s/index.html" ]; then
    echo "$s: unchanged; pages from the last build"
  else
    rm -rf "$BUILT/$s" "$BUILT/$s.hash"
    python3 build_data.py --state "$s" --github "$BUILT/$s"
    echo "$hash" > "$BUILT/$s.hash"
    REBUILT="$REBUILT $s"
  fi
  cp -R "$BUILT/$s" "$OUT/$s"
done
echo "rebuilt:${REBUILT:- none}"
# The front page lists exactly the states built in this run (home.html's own list is replaced), so a state appears there
# as soon as its pages are published (New York's too, at /ny/).
python3 - "$OUT" <<'PY'
import importlib, json, os, re, sys
sys.path.insert(0, ".")
import balance, front_page
out = sys.argv[1]
page = open("home.html").read()
items, power = [], {}
for s in sorted(os.listdir(out)):
    if len(s) == 2 and os.path.exists(os.path.join(out, s, "index.html")):
        P = importlib.import_module(f"states.{s}.profile")
        # Party control for the map's dots (balance.py), from the latest member list.
        data = front_page.map_data(s, getattr(P, "LOWER_NAME", "Assembly"))
        if data:
            power[s] = data
        items.append((P.STATE_NAME, f'    <li><a href="{s}/"><b>{P.STATE_NAME}</b></a></li>\n'))
block = "".join(i for _, i in sorted(items))
page = page.replace('<script type="application/json" id="power">{}</script>',
                    '<script type="application/json" id="power">' + json.dumps(power, ensure_ascii=False).replace("</", "<\\/") + "</script>", 1)
page = re.sub(r'(<ul id="states">\n)(?:    <li><a href="[a-z]{2}/">.*?</li>\n)*', lambda m: m.group(1) + block, page, count=1, flags=re.S)
open(os.path.join(out, "index.html"), "w").write(page)
print("front page:", ", ".join(n for n, _ in sorted(items)))
PY
# The pages ask for their icons at the top of the site.
cp "$OUT/nj/favicon.ico" "$OUT/nj/favicon-32.png" "$OUT/nj/apple-touch-icon.png" "$OUT/"
if [ "${LAUNCHED:-0}" = 1 ]; then
  printf 'User-agent: *\nAllow: /\n' > "$OUT/robots.txt"
else
  printf 'User-agent: *\nDisallow: /\n' > "$OUT/robots.txt"
  printf '/*\n  X-Robots-Tag: noindex\n' > "$OUT/_headers"
fi
echo "Built $OUT/ ($(find "$OUT" -type f | wc -l | tr -d ' ') files)"
