#!/usr/bin/env python3
"""The governor's veto proclamations that no journal prints: House bills vetoed after the session ends. (Vetoes during
the session are special messages in the House or Senate Journal, and the Senate Journal's last day prints the
post-session proclamations for Senate bills: convert.py's journal_vetoes() reads those.) The governor's site posts the
signed proclamations as scans with no text: one post per veto in 2021 ("Governor Abbott Vetoes HB 1193 (87R)", linking
/uploads/files/press/HB_1193_Veto_Statement.pdf), one PDF of all of them in 2025 (VETO_proclamations_SCANS_2025-06-22_
(2).pdf, 34 pages, linked from the special session's announcement). None found for 2023: the Legislative Reference
Library's scans (lrl.texas.gov/scanned/vetoes/88/...) are barred by its robots.txt (Disallow: /*.pdf), and the Texas
Register (sos.texas.gov) answers programs 403.

Each PDF is read once, by OCR (states/letters.py), split into proclamations by the bill each one vetoes ("do hereby
disapprove of and veto House Bill No. 305 as passed by the Eighty-Ninth Texas Legislature, Regular Session"), and kept as
data/tx/<89R>/vetoes/<HB305>.json ({url, ocr, raw, engine, read}); data/tx/veto_pdfs.json lists the PDFs read (and the
bills found in each), so none is read twice. A few minutes a run at most; never holds Texas back.

Usage: python3 states/tx/vetoes.py [minutes]
"""
import json, os, re, sys, time, urllib.error, urllib.parse, urllib.request
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
from states import letters as L
from states.tx import profile as P

SITE = "https://gov.texas.gov"
AGENT = "statebilltracker.org (a nonprofit bill tracker)"
# The legislative statements' list (eight posts a page: /P8, /P16 ...), where each 2021 veto has its post; and posts
# elsewhere that link a session's proclamations (the 2025 scans are linked only from the special session's announcement).
CATEGORY = f"{SITE}/news/category/legislative"
PAGES = 6
POSTS = [f"{SITE}/news/post/governor-abbott-announces-special-session-date-initial-agenda"]
ORDINAL = {"Eighty-Seventh": 87, "Eighty-Eighth": 88, "Eighty-Ninth": 89, "Ninetieth": 90, "Ninety-First": 91}
DONE = os.path.join(P.DATA, "veto_pdfs.json")


def get(url, binary=False):
    for attempt in range(3):
        time.sleep(2)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": AGENT})
            with urllib.request.urlopen(req, timeout=180) as r:
                body = r.read()
            return body if binary else body.decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            if e.code in (403, 404, 410):
                return None
            time.sleep(10 * (attempt + 1))
        except OSError:
            time.sleep(10 * (attempt + 1))
    return None


def pdf_links(page):
    """The press PDFs a page links whose name says veto ("HB_1193_Veto_Statement.pdf", "VETO_proclamations_SCANS_...")."""
    out = []
    for h in re.findall(r'href="([^"]*/uploads/files/press/[^"]+\.pdf)"', page or "", re.I):
        h = urllib.parse.urljoin(SITE, h.replace("&amp;", "&"))
        if re.search(r"veto", h, re.I) and h not in out:
            out.append(h)
    return out


def proclamations(raw):
    """OCR text of a PDF (pages split by "\\f") -> [(session code "89R", bill "HB305", text)], one per proclamation: a
    page naming a vetoed bill starts one; the pages after it, until the next, belong to it. Regular sessions only."""
    out = []
    for page in raw.split("\f"):
        flat = re.sub(r"\s+", " ", re.sub(r"-\s*\n\s*", "-", page))  # "Eighty-" / "Ninth" across a line
        m = re.search(r"veto\s+(House|Senate)\s+Bill\s+No\.?\s*(\d+)\s+as\s+passed\s+by\s+the\s+([A-Z][a-z]+-?[A-Za-z]*)\s+"
                      r"Texas\s+Legislature,\s+(Regular|[A-Z][a-z]+ Called)\s+Session", flat)
        if m:
            leg = ORDINAL.get(m.group(3))
            code = f"{leg}R" if leg and m.group(4) == "Regular" else None
            out.append([code, f"{m.group(1)[0]}B{int(m.group(2))}", page])
        elif out:
            out[-1][2] += "\f" + page
    return [tuple(x) for x in out if x[0]]


def main(minutes=8):
    if not L.ocr_ready():
        print("veto proclamations: pdftoppm or tesseract isn't installed")
        return
    stop_at = time.time() + minutes * 60
    try:
        done = json.load(open(DONE))
    except (OSError, ValueError):
        done = {}
    # The posts: the category's pages (the veto posts' own), then each post's PDFs.
    posts = list(POSTS)
    for k in range(PAGES):
        page = get(CATEGORY + (f"/P{8 * k}" if k else ""))
        found = re.findall(r'href="(https://gov\.texas\.gov/news/post/[^"]*veto[^"]*)"', page or "", re.I)
        if not page or not found and k:
            break
        posts += [p for p in found if p not in posts]
    pdfs = []
    for post in posts:
        for u in pdf_links(get(post)):
            if u not in pdfs and u not in done:
                pdfs.append(u)
    got = 0
    for url in pdfs:
        if time.time() > stop_at:
            break
        data = get(url, binary=True)
        if not isinstance(data, bytes) or data[:5] != b"%PDF-":
            continue
        own = L.pdf_text(data)
        ocr = len(re.sub(r"\s", "", own)) < 200
        raw = L.ocr_pdf(data, pages=200) if ocr else own
        if raw is None:
            continue
        found = proclamations(raw)
        for code, bill, text in found:
            folder = os.path.join(P.DATA, code, "vetoes")
            os.makedirs(folder, exist_ok=True)
            path = os.path.join(folder, f"{bill}.json")
            if os.path.exists(path):
                continue
            rec = {"url": url, "ocr": ocr, "raw": text, "engine": L.ocr_engine() if ocr else "",
                   "read": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
            with open(path + ".tmp", "w", encoding="utf-8") as f:
                json.dump(rec, f, ensure_ascii=False)
            os.replace(path + ".tmp", path)
        done[url] = [f"{c} {b}" for c, b, _ in found]
        with open(DONE + ".tmp", "w") as f:
            json.dump(done, f, indent=0)
        os.replace(DONE + ".tmp", DONE)
        got += 1
    print(f"veto proclamations: {got} of {len(pdfs)} new PDFs read ({sum(len(v) for v in done.values())} proclamations in all)")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 8)
