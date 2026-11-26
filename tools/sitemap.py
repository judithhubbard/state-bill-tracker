"""Writes sitemap.xml for the built site (build_site.sh, after every state is built; only when LAUNCHED=1).

Usage: python3 tools/sitemap.py OUT_DIR [BASE_URL]

Lists every page a search engine should find: the front page, About, Compare states, the issue pages, each state's
session pages, its legislators' pages and its governor's page. Left out: pages that are one visitor's own (watchlists,
Your bills, shared lists, the list editor, the New York welcome page) and any page marked noindex. Bills have no pages
of their own (they're #S1234 on the session page), so they aren't listed. A sitemap holds at most 50,000 addresses;
past that it is split into sitemap-1.xml, sitemap-2.xml ... with sitemap.xml as their index. No <lastmod>: unchanged
states are copied from the last build, so file times don't say when a page changed.
"""
import os
import re
import sys
from xml.sax.saxutils import escape

OUT = sys.argv[1]
BASE = (sys.argv[2] if len(sys.argv) > 2 else "https://statebilltracker.org/").rstrip("/") + "/"
SKIP_DIRS = {"assets", "data", "search", "list", "lists", "your-bills", "welcome", "watchlist", "manage", "admin",
             "status", "embed"}
MAX = 50000


def pages():
    for root, dirs, files in os.walk(OUT):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS and not d.startswith("."))
        for f in sorted(files):
            if not f.endswith(".html"):
                continue
            path = os.path.join(root, f)
            with open(path, "rb") as fh:
                head = fh.read(20000).decode("utf-8", "ignore")
            if re.search(r'<meta[^>]+name="robots"[^>]+noindex', head, re.I):
                continue
            rel = os.path.relpath(path, OUT).replace(os.sep, "/")
            if rel == "index.html":
                rel = ""
            elif rel.endswith("/index.html"):
                rel = rel[: -len("index.html")]
            elif rel in ("404.html",):
                continue
            else:  # Cloudflare Pages serves "ny/2023.html" at "ny/2023" and redirects the first (308): list the address it keeps
                rel = rel[: -len(".html")]
            yield BASE + rel


def write(path, urls):
    with open(path, "w", encoding="utf-8") as fh:
        fh.write('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n')
        for u in urls:
            fh.write(f"<url><loc>{escape(u)}</loc></url>\n")
        fh.write("</urlset>\n")


urls = list(pages())
if len(urls) <= MAX:
    write(os.path.join(OUT, "sitemap.xml"), urls)
else:
    parts = [urls[i:i + MAX] for i in range(0, len(urls), MAX)]
    with open(os.path.join(OUT, "sitemap.xml"), "w", encoding="utf-8") as fh:
        fh.write('<?xml version="1.0" encoding="UTF-8"?>\n<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n')
        for i, part in enumerate(parts, 1):
            write(os.path.join(OUT, f"sitemap-{i}.xml"), part)
            fh.write(f"<sitemap><loc>{BASE}sitemap-{i}.xml</loc></sitemap>\n")
        fh.write("</sitemapindex>\n")
print(f"sitemap: {len(urls)} pages")
