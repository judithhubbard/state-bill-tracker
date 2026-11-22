#!/usr/bin/env python3
"""Arkansas's "What it does" for laws: the Bureau of Legislative Research's Summary of General Legislation.

After each regular session the BLR publishes a book summarizing every general act by subject ("ACT 28 (HB1204) limits
the recovery of damages for past necessary medical care, ..."), linked from the session's Session Documents page
(arkleg.state.ar.us/Bills/SessionDocuments?a=1&ddBienniumSession=2025%2F2025R: "Summary of General Legislation"; 2023's
"2023 Regular Session - General Legislative Summary") as /Home/FTPDocument?path=/assembly/<year>/<year>R/Documents/...pdf.
robots.txt allows everything but ChatGPT's agents. Appropriation acts are in a separate fiscal summary, as tables of
amounts (not used), and so are the fiscal sessions' (2024, 2026).

`run(request, years)` is called by fetch.py (request: fetch.py's GET, returning bytes or None): for each regular-session
year, the Session Documents page (one request), then the book when its address is new or the copy is 60 days old (3-4
MB). The book is read with pdftohtml -xml (poppler-utils), which keeps the fonts: headings are bold or italic, or
capitals; an act's text is the plain lines after its "ACT n (HB1234)" line. Kept as data/ar/<biennium>/
general_summary_<year>.json ({"url", "read", "bills": {"HB1204": [text, ...]}}) and written to data/ar/texts_<year>.json.
A failure keeps the last copy; nothing here holds the run back.
Usage (on its own, for a saved book): python3 states/ar/summaries.py <year> <book.pdf>
"""
import difflib, html, json, os, re, shutil, subprocess, sys, tempfile, urllib.parse
from datetime import date

DATA = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "ar"))
SERVER = "https://arkleg.state.ar.us/"
LABEL = "From the Bureau of Legislative Research's summary of the act."
MAX_AGE = 60
LINK = re.compile(r'href="(/Home/FTPDocument\?path=[^"]+)"[^>]*>([^<]+)<', re.I)
START = re.compile(r"ACT (\d+) \(((?:HB|SB|HJR|SJR)\d+)\)\s*(.*)")
TEXT = re.compile(r'<text top="(\d+)" left="(\d+)"[^>]*>(.*?)</text>', re.S)
PAGE = re.compile(r"<page number=")
FOOTER = re.compile(r"SUMMARY OF GENERAL LEGISLATION|^\d+$|^[ivx]+$")


def biennium(year):
    return year - (year % 2 == 0)


def lines(xml):
    """[(page, left, text, styled)] from pdftohtml's XML, one per printed line (pdftohtml splits a line where the font
    changes: "... a medical malpractice ac" + "tion. The act is"); styled when it starts bold or italic."""
    out = []
    for p, chunk in enumerate(PAGE.split(xml)):
        rows = {}
        for top, left, body in TEXT.findall(chunk):
            rows.setdefault(int(top), []).append((int(left), body))
        for top in sorted(rows):
            segs = sorted(rows[top])
            styled = bool(re.match(r"\s*<[bi]>", segs[0][1]))
            t = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", "".join(b for _, b in segs)))).strip()
            if t:
                out.append((p, segs[0][0], t, styled))
    return out


def heading(t, styled):
    letters = re.sub(r"[^A-Za-z]", "", t)
    return styled or (letters and letters.isupper() and not t.startswith("ACT ") and len(t) < 90)


def parse(xml):
    """{"HB1204": [summary, ...]}: an act listed under several subjects is summarized under each; different words
    become separate paragraphs, near-repeats are kept once."""
    out, cur = {}, None

    def close():
        if not cur:
            return
        bill, parts = cur
        t = re.sub(r"(\w)- (\w)", lambda m: m.group(0) if m.group(2)[0].isupper() else m.group(1) + "-" + m.group(2),
                   " ".join(parts))
        t = re.sub(r"\s+", " ", t).strip()
        m = START.match(t)
        if m and m.group(3):
            rest = m.group(3)
            # "ACT 1 (HB1001) and ACT 2 (SB1) are identical acts that ..." stays as written; else the verb leads.
            t = t if re.match(r"and ACT \d+", rest) else rest[0].upper() + rest[1:]
        elif m or not t:
            return
        have = out.setdefault(bill, [])
        if not any(difflib.SequenceMatcher(None, t, h).ratio() > 0.9 for h in have):
            have.append(t)

    page = left = None
    for p, lf, t, styled in lines(xml):
        if FOOTER.search(t):
            continue
        m = START.match(t)
        if m and not styled:
            close()
            cur, page, left = (m.group(2), [t]), p, lf
            continue
        # A proposed constitutional amendment: its bold title ("HJR 1018 - A CONSTITUTIONAL AMENDMENT ..."), then
        # plain lines ("If approved by voters at the 2026 general election, the amendment would provide ...").
        a = re.match(r"(HJR|SJR) ?(\d+) - ", t)
        if a and styled:
            close()
            cur, page, left = (a.group(1) + a.group(2), []), p, None
            continue
        if cur and left is None:
            if styled and not cur[1]:
                continue  # the title's later lines
            if not styled:
                cur[1].append(t)
                continue
        elif cur and not heading(t, styled) and (p != page or abs(lf - left) <= 4):
            cur[1].append(t)
            page = p
            continue
        close()
        cur = None
    close()
    # Joint entries ("ACT 1 (HB1001) and ACT 2 (SB1) are identical acts ...") name the second bill too.
    for bill, texts in list(out.items()):
        for t in texts:
            for other in re.findall(r"^ACT \d+ \(\w+\) and ACT \d+ \(((?:HB|SB)\d+)\)", t):
                if t not in out.setdefault(other, []):
                    out[other].append(t)
    return out


def read_pdf(path):
    if not shutil.which("pdftohtml"):
        print("general summary: pdftohtml not installed (poppler-utils)", flush=True)
        return None
    with tempfile.TemporaryDirectory() as d:
        subprocess.run(["pdftohtml", "-xml", "-i", "-q", path, os.path.join(d, "out")], check=True, timeout=300)
        with open(os.path.join(d, "out.xml"), encoding="utf-8", errors="replace") as f:
            return f.read()


def load(path):
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def save(path, data):
    with open(path + ".tmp", "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=0)
    os.replace(path + ".tmp", path)


def write_texts(year):
    kept = load(os.path.join(DATA, str(biennium(year)), f"general_summary_{year}.json"))
    if not kept or not kept.get("bills"):
        return 0
    save(os.path.join(DATA, f"texts_{year}.json"),
         {n: {"statement": "\n".join(p), "label": LABEL} for n, p in sorted(kept["bills"].items())})
    return len(kept["bills"])


def book_url(request, year):
    page = request(SERVER + "Bills/SessionDocuments?a=1&ddBienniumSession="
                   + urllib.parse.quote(f"{biennium(year)}/{year}R", safe=""), f"{year} session documents")
    if not page:
        return None
    for href, label in LINK.findall(page.decode("utf-8", "replace")):
        href = html.unescape(href)
        path = urllib.parse.unquote_plus(href.split("path=", 1)[1])
        if re.search(r"general legislati", label, re.I) and f"/{year}R/" in path:
            return SERVER + href.lstrip("/")
    return None


def store(year, url, xml):
    bills = parse(xml) if xml else {}
    if len(bills) < 50:
        print(f"{year}: general summary: only {len(bills)} acts read; kept the last copy", flush=True)
        return
    folder = os.path.join(DATA, str(biennium(year)))
    os.makedirs(folder, exist_ok=True)
    save(os.path.join(folder, f"general_summary_{year}.json"), {"url": url, "read": date.today().isoformat(), "bills": bills})
    print(f"{year}: general summary: {len(bills)} acts", flush=True)


def run(request, years):
    """Each regular session's book, when new or 60 days old; texts_<year>.json from what's kept. Never raises."""
    for y in years:
        if y % 2 == 0:  # fiscal sessions: appropriations only, summarized as tables
            continue
        try:
            kept = load(os.path.join(DATA, str(biennium(y)), f"general_summary_{y}.json")) or {}
            age = (date.today() - date.fromisoformat(kept.get("read") or "2000-01-01")).days
            if age >= MAX_AGE or not kept.get("bills"):
                url = book_url(request, y)
                if url and (url != kept.get("url") or age >= MAX_AGE):
                    body = request(url, f"{y} general summary")
                    if body and body[:5] == b"%PDF-":
                        with tempfile.NamedTemporaryFile(suffix=".pdf") as f:
                            f.write(body)
                            f.flush()
                            store(y, url, read_pdf(f.name))
                elif not url:
                    print(f"{y}: no Summary of General Legislation listed yet", flush=True)
            write_texts(y)
        except Exception as e:  # noqa: BLE001
            print(f"{y}: general summary: failed ({e.__class__.__name__}: {e}); kept the last copy", flush=True)
            if e.__class__.__name__ == "Refused":  # 401/403/429: stop asking
                return


if __name__ == "__main__":
    y = int(sys.argv[1])
    store(y, "", read_pdf(sys.argv[2]))
    print(write_texts(y), "written")
