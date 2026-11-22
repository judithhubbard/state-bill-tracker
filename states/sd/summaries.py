#!/usr/bin/env python3
"""South Dakota's "What it does" for laws: the Legislative Research Council's Title Summaries.

After each session the LRC publishes one memorandum per SDCL title summarizing the session's laws codified in it ("HB
1054 repeals provisions creating the Digital Dakota Network, ..."), all in one document: the session list
(sdlegislature.gov/api/Sessions) names it as SummaryDocumentId (2025: 285313, 2026: 306526; 0 for 2023, 2024 and the
special sessions, which have none), and the same document is served as HTML at
mylrc.sdlegislature.gov/api/Documents/<id>.html (robots.txt there bars nothing; sdlegislature.gov's only /pdfviewer).
It covers the laws that change the codified statutes (205 of 2026's 240 laws, 194 of 2025's 211); appropriations and
other uncodified acts aren't in it.

`run(get, years)` is called by fetch.py: one Sessions request, then each listed document once (about 6 MB,
mostly embedded images), again only when its id changes or the copy is 30 days old. What it reads is kept as
data/sd/<year>/title_summaries.json ({"doc": id, "read": day, "bills": {"HB1054": [text, ...]}}), and
data/sd/texts_<year>.json is written from it ({"HB1054": {"statement", "label"}}). A failure keeps the last copy.
Usage (on its own): python3 states/sd/summaries.py
"""
import difflib, html, json, os, re, sys, time, urllib.request
from datetime import date

DATA = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "sd"))
LABEL = "From the Legislative Research Council's summary of the law."
MAX_AGE = 30  # days before a document is read again
BILL = re.compile(r"(HB|SB|HJR|SJR) ?(\d+)(?!\d)\s*(.*)")


def text(s):
    """A paragraph's text: tags removed without adding spaces (LibreOffice splits words across <font> tags), entities
    decoded, the file's own line breaks collapsed."""
    s = html.unescape(re.sub(r"<[^>]+>", "", s)).replace("\xa0", " ")
    return re.sub(r"\s+", " ", s).strip()


def parse(page):
    """{"HB1054": [summary, ...]}: a law codified in several titles is summarized under each, the same words or each
    part's own; near-repeats ("five percent" / "5 percent") are kept once."""
    page = re.sub(r"(?s)<(script|style)\b.*?</\1>", " ", page)
    out = {}
    for tag, body in re.findall(r"(?s)<(p|h1|h2|h3)\b[^>]*>(.*?)</\1>", page):
        s = text(body)
        m = BILL.fullmatch(s) if tag == "p" else None
        if not m or not m.group(3):
            continue
        num, words = m.group(1) + m.group(2), m.group(3)
        words = words[0].upper() + words[1:]
        have = out.setdefault(num, [])
        if not any(difflib.SequenceMatcher(None, words, h).ratio() > 0.9 for h in have):
            have.append(words)
    return out


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
    kept = load(os.path.join(DATA, str(year), "title_summaries.json"))
    if not kept or not kept.get("bills"):
        return 0
    texts = {n: {"statement": "\n".join(parts), "label": LABEL} for n, parts in sorted(kept["bills"].items())}
    save(os.path.join(DATA, f"texts_{year}.json"), texts)
    return len(texts)


def run(get, years):
    """Read each year's Title Summaries when new or 30 days old; write texts_<year>.json. Never raises."""
    try:
        listed = {str(s.get("Year")): s.get("SummaryDocumentId") for s in get("Sessions") or []
                  if not s.get("SpecialSession")}
    except Exception as e:  # noqa: BLE001
        print(f"title summaries: no session list ({e.__class__.__name__})", flush=True)
        listed = {}
    for y in years:
        folder = os.path.join(DATA, str(y))
        path = os.path.join(folder, "title_summaries.json")
        kept = load(path) or {}
        doc = listed.get(str(y))
        try:
            old = (date.today() - date.fromisoformat(kept.get("read") or "2000-01-01")).days >= MAX_AGE
            if doc and os.path.isdir(folder) and (kept.get("doc") != doc or old):
                page = fetch_doc(doc)
                bills = parse(page) if page else {}
                if bills:
                    save(path, {"doc": doc, "read": date.today().isoformat(), "bills": bills})
                    print(f"{y}: title summaries: {len(bills)} laws (document {doc})", flush=True)
                else:
                    print(f"{y}: title summaries: document {doc} unread or empty; kept the last copy", flush=True)
            n = write_texts(y)
            if n and not (doc and kept.get("doc") != doc):
                print(f"{y}: title summaries: {n} laws", flush=True)
        except Exception as e:  # noqa: BLE001
            print(f"{y}: title summaries: failed ({e.__class__.__name__}); kept the last copy", flush=True)


def fetch_doc(doc):
    """The document as HTML from mylrc.sdlegislature.gov, or None."""
    time.sleep(1)
    try:
        req = urllib.request.Request(f"https://mylrc.sdlegislature.gov/api/Documents/{doc}.html",
                                     headers={"User-Agent": AGENT})
        with urllib.request.urlopen(req, timeout=120) as r:
            if "html" not in (r.headers.get("Content-Type") or ""):
                return None
            return r.read().decode("utf-8", "replace")
    except Exception as e:  # noqa: BLE001
        print(f"title summaries: document {doc}: {e.__class__.__name__}", flush=True)
        return None


AGENT = "statebilltracker.org (a nonprofit bill tracker; contact via github.com/judithhubbard)"

if __name__ == "__main__":
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
    from states.sd import fetch as F
    run(F.get, sorted(int(d) for d in os.listdir(DATA) if d.isdigit()))
