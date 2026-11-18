#!/bin/bash
# Builds statebilltracker.org into one folder: the front page (home.html), the icons, and each state's
# public site in its own folder (/nj/ …). Cloudflare Pages serves the folder (see .github/workflows/publish.yml).
# Until launch, every page tells search engines not to list it (_headers and robots.txt); set LAUNCHED=1 then.
# Usage: ./build_site.sh [DIR]   (default: _site)
set -e
cd "$(dirname "$0")"
OUT=${1:-_site}
STATES=${ONLY:-"ak al ar az ca co ct de fl ga hi ia id il in ks ky la ma md me mi mn mo ms mt nc nd ne nh nj nm nv oh ok or pa ri sc sd tn tx ut va vt wa wi wv wy us"}  # ONLY="wy sd" for a quick local test
# New York from this shared code (/ny/, not linked from the front page until New York moves here; until then
# albanybilltracker.org runs from its own repo), when the current session's bills are here (the workflow
# downloads them with the Senate API key).
NY=$(python3 -c "import datetime; y = datetime.date.today().year; print(y if y % 2 else y - 1)")
if [ -f "data/bills_$NY.json" ]; then STATES="$STATES ny"; fi
rm -rf "$OUT" && mkdir -p "$OUT"
# Each state's pages from earlier builds, with the fingerprint they were built from.
BUILT=${BUILT:-built}
mkdir -p "$BUILT"
# Each state is built on its own (build_one), several at a time (JOBS, default 4: GitHub's runners have 4 cores), the
# biggest first, so a change to the shared code rebuilds all states in about a quarter of the time. Each leaves its
# outcome in $BUILT/<state>.result (rebuilt, failed, kept, copy or skip); the pages are copied into $OUT afterwards, in order.
build_one() {
  s=$1
  rm -f "$BUILT/$s.result"
  # A state whose first full download is still building up over several runs (data/<state>/incomplete, written by
  # its fetch.py) waits: a partial copy would make a misleading site, or fail the build for every state.
  # A state already on the site whose latest run was cut off mid-refresh (many downloads mark every run until it
  # finishes) keeps its last build's pages until a run finishes.
  if [ -f "data/$s/incomplete" ]; then
    if [ -f "$BUILT/$s/index.html" ]; then echo "$s: download not finished; keeping the last build's pages"; echo copy > "$BUILT/$s.result"
    else echo "$s: download not complete yet; not built"; echo skip > "$BUILT/$s.result"; fi
    return
  fi
  # No data yet (a new state whose first download on GitHub hasn't run, so its cache is empty): nothing to build. Files
  # kept in git (data/la/district_towns.json) and the "last checked" mark don't count.
  if [ "$s" != "ny" ] && [ -z "$(ls -A "data/$s" 2>/dev/null | grep -v '^last_checked$' | while read -r f; do git ls-files --error-unmatch "data/$s/$f" >/dev/null 2>&1 || echo "$f"; done)" ]; then
    echo "$s: no data yet; not built"; echo skip > "$BUILT/$s.result"; return
  fi
  # SITE_BASE (the preview's address) gives each state its own: SITE_BASE/nj/, SITE_BASE/va/.
  if [ -n "$SITE_BASE" ]; then export SITE_URL="${SITE_BASE}$s/"; fi
  # A state whose data, code and settings haven't changed since the last build (state_hash.py; publish.yml keeps
  # $BUILT between runs) is copied from it rather than rebuilt; every state is rebuilt at least once a day.
  hash=$(python3 state_hash.py "$s")
  if [ -f "$BUILT/$s.hash" ] && [ "$(cat "$BUILT/$s.hash")" = "$hash" ] && [ -f "$BUILT/$s/index.html" ]; then
    echo "$s: unchanged; pages from the last build"; echo copy > "$BUILT/$s.result"; return
  fi
  # One state's failure mustn't stop the site: it's built into a new folder, and if the build fails the state keeps
  # the last build's pages (or is left out if it has none); the failures are listed at the end.
  rm -rf "$BUILT/$s.new"
  if python3 build_data.py --state "$s" --github "$BUILT/$s.new" > "$BUILT/$s.log" 2>&1; then
    rm -rf "$BUILT/$s" && mv "$BUILT/$s.new" "$BUILT/$s"
    echo "$hash" > "$BUILT/$s.hash"
    echo "$s: rebuilt"; echo rebuilt > "$BUILT/$s.result"
  else
    rm -rf "$BUILT/$s.new"
    echo "$s: BUILD FAILED"; sed 's/^/  /' "$BUILT/$s.log" | tail -40
    echo failed > "$BUILT/$s.result"
  fi
}
export -f build_one
export BUILT SITE_BASE
# Biggest data first, so the long builds start early.
ORDER=$(for s in $STATES; do if [ "$s" = ny ]; then echo "999999999 ny"; else echo "$(du -sk "data/$s" 2>/dev/null | cut -f1 || echo 0) $s"; fi; done | sort -rn | cut -d' ' -f2)
printf '%s\n' $ORDER | xargs -P "${JOBS:-4}" -I{} bash -c 'build_one {}'
REBUILT=""; FAILED=""
for s in $STATES; do
  r=$(cat "$BUILT/$s.result" 2>/dev/null || echo failed)
  case "$r" in
    rebuilt) REBUILT="$REBUILT $s" ;;
    failed) FAILED="$FAILED $s"
      if [ -f "$BUILT/$s/index.html" ]; then echo "$s: build failed; keeping the last build's pages"; else echo "$s: build failed; left out"; continue; fi ;;
    skip) continue ;;
  esac
  cp -R "$BUILT/$s" "$OUT/$s"
done
echo "rebuilt:${REBUILT:- none}"
# The national issue pages (/issues/), from each built state's data/issues_<session>.json; issues/summary.json feeds the front page.
python3 issues_site.py "$OUT" || echo "issue pages: BUILD FAILED"
# The front page's "Find a bill" data (search/<st>.json), from each built state's live status_<session>.json.
python3 search_site.py "$OUT" || echo "search data: BUILD FAILED"
if [ -n "$FAILED" ]; then echo "build failed for:$FAILED"; fi
# The front page lists exactly the states built in this run (home.html's own list is replaced), so a state appears there
# as soon as its pages are published (New York's too, at /ny/).
python3 - "$OUT" <<'PY'
import html, importlib, json, os, re, sys
sys.path.insert(0, ".")
import balance, front_page, site_meta
out = sys.argv[1]
page = open("home.html").read()
# Link previews and the canonical link (site_meta.py: the public address once LAUNCHED=1, else the preview's).
desc = re.search(r'<meta name="description" content="([^"]*)">\n', page)
page = page.replace(desc.group(0), desc.group(0) + site_meta.tags("State Bill Tracker", html.unescape(desc.group(1)), site_meta.root()) + site_meta.analytics(), 1)
page = page.replace("SUPPORT_URL", site_meta.SUPPORT)
items, power, after = [], {}, {}
for s in sorted(os.listdir(out)):
    if len(s) == 2 and os.path.exists(os.path.join(out, s, "index.html")):
        P = importlib.import_module(f"states.{s}.profile")
        # Party control for the map's colors (balance.py), from the latest member list. Congress (/us/) gets its own
        # tile on the map, colored from the House, the Senate and the President.
        data = front_page.map_data(s, getattr(P, "LOWER_NAME", "Assembly"))
        if data:
            power[s] = data
        if s == "us":
            # Congress isn't a state: listed first; no "From January" colors (the 2026 congressional results aren't in
            # states/elected_2026.json).
            items.append((" Congress", f'    <li><a href="us/"><b>Congress</b> (federal bills)</a></li>\n'))
            continue
        # After the 2026 election (states/elected_2026.json), for the map's "From January" view.
        nxt = front_page.next_data(s, getattr(P, "LOWER_NAME", "Assembly"))
        if nxt:
            after[s] = nxt
        items.append((P.STATE_NAME, f'    <li><a href="{s}/"><b>{P.STATE_NAME}</b></a></li>\n'))
block = "".join(i for _, i in sorted(items))
# Past years' party control (party_history.py: NCSL's tables and Congress's members, one day mid-session each year), for
# the map's earlier years; only the states built in this run, with each year's day ("_asOf").
try:
    shown = {s for s in os.listdir(out) if len(s) == 2 and os.path.exists(os.path.join(out, s, "index.html"))}
    past = {y: {k: v for k, v in states.items() if k == "_asOf" or k in shown}
            for y, states in json.load(open(os.path.join("states", "party_history.json"))).items()}
except (OSError, ValueError):
    past = {}
# The national issues for the map's "Show" menu (issues_site.py's summary: each issue's counts by state).
try:
    summ = json.load(open(os.path.join(out, "issues", "summary.json")))
except (OSError, ValueError):
    summ = []
if summ:
    page = page.replace('<script type="application/json" id="issues">[]</script>',
                        '<script type="application/json" id="issues">' + json.dumps(summ, ensure_ascii=False).replace("</", "<\\/") + "</script>", 1)
page = page.replace('<script type="application/json" id="power">{}</script>',
                    '<script type="application/json" id="power">' + json.dumps(power, ensure_ascii=False).replace("</", "<\\/") + "</script>", 1)
page = page.replace('<script type="application/json" id="after">{}</script>',
                    '<script type="application/json" id="after">' + json.dumps(after, ensure_ascii=False).replace("</", "<\\/") + "</script>", 1)
page = page.replace('<script type="application/json" id="past">{}</script>',
                    '<script type="application/json" id="past">' + json.dumps(past, ensure_ascii=False).replace("</", "<\\/") + "</script>", 1)
page = re.sub(r'(<ul id="states">\n)(?:    <li><a href="[a-z]{2}/">.*?</li>\n)*', lambda m: m.group(1) + block, page, count=1, flags=re.S)
open(os.path.join(out, "index.html"), "w").write(page)
print("front page:", ", ".join(n.strip() for n, _ in sorted(items)))
PY
# The pages ask for their icons at the top of the site.
cp static/favicon.ico static/favicon-32.png static/apple-touch-icon.png "$OUT/"
# The link preview image every page names (og:image; made by tools/og_image.sh), and the page for addresses that aren't
# there (Cloudflare Pages serves 404.html with status 404, instead of the front page).
cp tools/og-image.png "$OUT/og-image.png"
cp notfound.html "$OUT/404.html"
# The About page, with its link preview tags and the visit counter (after launch).
mkdir -p "$OUT/about"
python3 - "$OUT/about/index.html" <<'PY'
import sys, site_meta
page = open("about.html").read()
meta = site_meta.tags("About · State Bill Tracker", "Why State Bill Tracker was built, where its data comes from, and how to reach it.",
                      site_meta.root() + "about/") + site_meta.analytics()
open(sys.argv[1], "w").write(page.replace("<!--meta-->\n", meta, 1).replace("SUPPORT_URL", site_meta.SUPPORT))
PY
# Each state's bill data (data/v/<session>.<hash>.list.json, .rows.json and .details.json: build_data.py) is named by its contents,
# so a browser can keep it for good; a new build gives the page new names. Everything else is checked on each visit.
printf '/:state/data/v/*\n  Cache-Control: public, max-age=31536000, immutable\n' > "$OUT/_headers"
if [ "${LAUNCHED:-0}" = 1 ]; then
  printf 'User-agent: *\nAllow: /\n' > "$OUT/robots.txt"
else
  printf 'User-agent: *\nDisallow: /\n' > "$OUT/robots.txt"
  printf '/*\n  X-Robots-Tag: noindex\n' >> "$OUT/_headers"
fi
echo "Built $OUT/ ($(find "$OUT" -type f | wc -l | tr -d ' ') files)"
