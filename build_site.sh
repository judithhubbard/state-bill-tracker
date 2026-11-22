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
# What build_data.py worked out from each state's data (and its issue matches and status words), kept with the pages, so a
# change to the page's code alone (tracker.html, lists_pages/, a profile.js, how.html, weighin.html, issues.py) rewrites
# the pages without working the data out again (build_data.py's data_bundle()).
BUILD_CACHE=${BUILD_CACHE:-$(cd "$BUILT" && pwd)/cache}
export BUILD_CACHE
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
  # The page's styles and scripts (build_data.py's asset_file(): the same in every state, named by their contents) go once
  # to the site's top, /assets/, where every state's pages load them; a state kept from an older build brings its own.
  # (File by file, assets/fonts/ too: a state from an older build may bring fonts the others don't have.)
  if [ -d "$OUT/$s/assets" ]; then
    (cd "$OUT/$s/assets" && find . -type f) | while read -r f; do
      if [ ! -e "$OUT/assets/$f" ]; then mkdir -p "$(dirname "$OUT/assets/$f")"; mv "$OUT/$s/assets/$f" "$OUT/assets/$f"; fi
    done
    rm -rf "$OUT/$s/assets"
  fi
done
echo "rebuilt:${REBUILT:- none}"
# The national issue pages (/issues/), from each built state's data/issues_<session>.json; issues/summary.json feeds the front page.
python3 issues_site.py "$OUT" || echo "issue pages: BUILD FAILED"
# How the states compare (/compare/), from each built state's data/compare.json; compare/summary.json feeds the front page.
python3 compare_site.py "$OUT" || echo "compare page: BUILD FAILED"
# The front page's "Find a bill" data (search/<st>.json), from each built state's live status_<session>.json.
python3 search_site.py "$OUT" || echo "search data: BUILD FAILED"
# Where each bill is, for /list/, /your-bills/, the list editor and the front page's "Your bills": /status.json names every
# state's status pieces (each state's data/status.json, from build_data.py's write_status_shards()); checked on each visit
# (the pieces it names, in data/v/, are kept for good). A state built before the pieces existed isn't in it: its pages read
# the whole status file.
python3 - "$OUT" <<'PY'
import json, os, sys
out, index = sys.argv[1], {}
for s in sorted(os.listdir(out)):
    try:
        index[s] = json.load(open(os.path.join(out, s, "data", "status.json")))
    except (OSError, ValueError):
        pass
json.dump(index, open(os.path.join(out, "status.json"), "w"), separators=(",", ":"), ensure_ascii=False)
PY
if [ -n "$FAILED" ]; then echo "build failed for:$FAILED"; fi
# The front page lists exactly the states built in this run (home.html's own list is replaced), so a state appears there
# as soon as its pages are published (New York's too, at /ny/).
python3 - "$OUT" <<'PY'
import html, importlib, json, os, re, sys
sys.path.insert(0, ".")
import balance, front_page, site_fonts, site_meta
out = sys.argv[1]
page = site_fonts.swap_google(open("home.html").read())
# Link previews and the canonical link (site_meta.py: the public address once LAUNCHED=1, else the preview's).
desc = re.search(r'<meta name="description" content="([^"]*)">\n', page)
page = page.replace(desc.group(0), desc.group(0) + site_meta.tags("State Bill Tracker", html.unescape(desc.group(1)), site_meta.root()) + site_meta.analytics(), 1)
page = page.replace("SUPPORT_URL", site_meta.SUPPORT)
# The named lists' button and menu beside each star (lists_pages/named.js), saving to the lists Worker (LISTS_API).
page = page.replace("/*named.js*/", open("lists_pages/named.js").read(), 1)
# The status words and "New" (billfacts.js), starred bills and where each bill is (status.js): the same copies as the list pages'.
page = page.replace("/*billfacts.js*/", open("lists_pages/billfacts.js").read(), 1).replace("/*status.js*/", open("lists_pages/status.js").read(), 1)
# A bill row's parts (the pips and the status label), the same styles as every other page's bill rows.
assert "/*rows.css*/" in page, "home.html's styles lost the /*rows.css*/ marker"
page = page.replace("/*rows.css*/", open("lists_pages/rows.css").read(), 1)
page = page.replace("LISTS_API_URL", os.environ.get("LISTS_API", "https://state-lists.lists-worker.workers.dev"), 1)
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
# Each state's latest finished session (compare_site.py's summary), for the map's "Bills that became law".
try:
    cmp = json.load(open(os.path.join(out, "compare", "summary.json")))
except (OSError, ValueError):
    cmp = {}
page = page.replace('<script type="application/json" id="compare">{}</script>',
                    '<script type="application/json" id="compare">' + json.dumps(cmp, ensure_ascii=False).replace("</", "<\\/") + "</script>", 1)
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
python3 -c 'import sys, site_fonts; open(sys.argv[1], "w").write(site_fonts.swap_google(open("notfound.html").read()))' "$OUT/404.html"
# The fonts (site_fonts.py), for every page (the state pages' builds put them in too).
python3 -c 'import sys, site_fonts; site_fonts.install(sys.argv[1])' "$OUT/assets/fonts"
# The About page, with its link preview tags and the visit counter (after launch).
mkdir -p "$OUT/about"
python3 - "$OUT/about/index.html" <<'PY'
import sys, site_fonts, site_meta
page = site_fonts.swap_google(open("about.html").read())
meta = site_meta.tags("About · State Bill Tracker", "Why State Bill Tracker was built, where its data comes from, and how to reach it.",
                      site_meta.root() + "about/") + site_meta.analytics()
open(sys.argv[1], "w").write(page.replace("<!--meta-->\n", meta, 1).replace("SUPPORT_URL", site_meta.SUPPORT))
PY
# "Your bills" across states (/your-bills/), a shared list's page (/list/#<slug>) and the list editor (/lists/edit/#<slug>),
# from lists_pages/: the shared styles and script put inside each (on the first two also embed.js, bills opened in place;
# on Your bills also watchrules.js and onelist.js, its one list across states, and named.js),
# the link preview tags, the visit counter, the lists Worker's address (LISTS_API, default the state-lists Worker), the
# contributions link and, for the editor's search, the states with "Find a bill" data (search/<st>.json, written above).
python3 - "$OUT" <<'PY'
import os, sys, site_fonts, site_meta
css, js, named, embed, rules, one = (open(f"lists_pages/{f}").read() for f in ("common.css", "common.js", "named.js", "embed.js", "watchrules.js", "onelist.js"))
# The watchlist's rows (watchrows.js, rows.css: the same as each state's Watchlist tab) go with the shared script and styles,
# after the status words and "New" (billfacts.js) and the starred bills and status reader (status.js), shared with the front page.
css += "\n" + open("lists_pages/rows.css").read()
js = open("lists_pages/billfacts.js").read() + "\n" + open("lists_pages/status.js").read() + "\n" + js + "\n" + open("lists_pages/watchrows.js").read()
api = os.environ.get("LISTS_API", "https://state-lists.lists-worker.workers.dev")
searchable = " ".join(sorted(f[:-5] for f in os.listdir(os.path.join(sys.argv[1], "search")) if len(f) == 7 and f.endswith(".json"))) if os.path.isdir(os.path.join(sys.argv[1], "search")) else ""
for src, path, title, desc in (("yourbills.html", "your-bills", "Your bills · State Bill Tracker", "The bills you follow in every state and Congress."),
                               ("list.html", "list", "Shared list · State Bill Tracker", "A list of bills shared on State Bill Tracker."),
                               ("edit.html", "lists/edit", "Edit a list · State Bill Tracker", "Make a list of bills from any state or Congress and share it.")):
    page = site_fonts.swap_google(open(os.path.join("lists_pages", src)).read())
    meta = site_meta.tags(title, desc, site_meta.root() + path + "/", canonical=False) + site_meta.analytics()
    page = (page.replace("<!--meta-->\n", meta, 1).replace("/*common.css*/", css, 1).replace("/*common.js*/", js, 1).replace("/*named.js*/", named, 1)
            .replace("/*embed.js*/", embed, 1).replace("/*watchrules.js*/", rules, 1).replace("/*onelist.js*/", one, 1).replace("LISTS_API_URL", api).replace("SUPPORT_URL", site_meta.SUPPORT).replace("SEARCH_STATES", searchable))
    os.makedirs(os.path.join(sys.argv[1], path), exist_ok=True)
    open(os.path.join(sys.argv[1], path, "index.html"), "w").write(page)
PY
# Where albanybilltracker.org's forwarding pages send New York's visitors, with their saved settings in the address
# (/welcome/ny/#d=...&to=/ny/...): lists_pages/welcome-ny.html saves them here and goes on to the page.
mkdir -p "$OUT/welcome/ny" && cp lists_pages/welcome-ny.html "$OUT/welcome/ny/index.html"
# Each state's bill data (data/v/<session>.<hash>.<part>.json.gz, gzipped: the list, rows, stats ... parts and the bills' shards,
# build_data.py's split_payload()) is named by its contents, so a browser can keep it for good; a new build gives the page
# new names, and the old files go (each state's folder is replaced whole). So are the pages' styles and scripts (/assets/).
# Everything else is checked on each visit.
printf '/:state/data/v/*\n  Cache-Control: public, max-age=31536000, immutable\n' > "$OUT/_headers"
printf '/assets/*\n  Cache-Control: public, max-age=31536000, immutable\n' >> "$OUT/_headers"
if [ "${LAUNCHED:-0}" = 1 ]; then
  # (New York was kept out of search engines until it moved here from albanybilltracker.org, 2026-11-22.)
  printf 'User-agent: *\nAllow: /\n' > "$OUT/robots.txt"
else
  printf 'User-agent: *\nDisallow: /\n' > "$OUT/robots.txt"
  printf '/*\n  X-Robots-Tag: noindex\n' >> "$OUT/_headers"
fi
N=$(find "$OUT" -type f | wc -l | tr -d ' ')
echo "Built $OUT/ ($N files)"
# Cloudflare Pages takes at most 20,000 files a deployment (free plan): a warning from 18,000, and the build fails from
# 19,500, so a deploy never breaks unnoticed.
if [ "$N" -gt 19500 ]; then echo "ERROR: $N files, too close to Cloudflare Pages' limit of 20,000 a deployment"; exit 1; fi
if [ "$N" -gt 18000 ]; then echo "WARNING: $N files, near Cloudflare Pages' limit of 20,000 a deployment"; fi
# Small copies of heavy legislators' photos (photos.py; at most 400 a state): expected to be a few hundred in all.
NP=$(find "$OUT/assets/photos" -type f 2>/dev/null | wc -l | tr -d ' ')
echo "Photos' small copies: $NP"
if [ "$NP" -gt 1500 ]; then echo "WARNING: $NP small photo copies in assets/photos/ (expected a few hundred: photos.py's HEAVY)"; fi
