#!/usr/bin/env python3
"""Connecticut governor's veto messages, from his Bill Notifications (portal.ct.gov; robots.txt allows all but
/sitecore/ and beta sites). Each time the governor acts on bills his office posts a numbered notification, a PDF at a
predictable address, /governor/-/media/office-of-the-governor/bill-notifications/<year>/bill-notification-<year>-<n>.pdf
(n from 1; 19 in 2025). Its first page lists the bills signed and vetoed; a veto's entry says where its letter is ("The
veto message can be found on page 4 of this document."; a line-item veto's "The line-item veto message can be found on
page 2"), and the letter to the Secretary of the State follows on those pages, typed (2025-13) or scanned (2025-1, read
by OCR: states/letters.py, approved by the owner 2026-11-22). A missing number answers a "404 Error Page" in HTML.

fetch() reads each year's notifications from the last one read, one request a second, until two numbers in a row are
missing; a year is asked again at most once a day, and no more once it's been checked after January 15 of the next year
(the governor has acted on all of a year's bills by then). Only notifications naming a veto are kept, as text, in
data/ct/vetoes/<year>.json: {"read": {n: true|false (has a veto)}, "checked": day, "notes": {n: {"url", "pages":
[[text, ocr]]}}}. messages(year) reads them: {"HB5002": {"text", "url", "ocr", "kind"}}. Never holds the run back.

The Office of Legislative Research's yearly "Veto Package" (cga.ct.gov/olr/VetoPackages.asp) has only excerpts.

Usage: python3 states/ct/vetoes.py [year ...]   (fetch.py calls fetch() each run)
"""
import json, os, re, sys, time, urllib.error, urllib.request
from datetime import datetime
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
from states import letters as L
from states.ct import profile as P

BASE = "https://portal.ct.gov/governor/-/media/office-of-the-governor/bill-notifications"
AGENT = "statebilltracker.org (a nonprofit bill tracker; contact via github.com/judithhubbard)"
FOLDER = os.path.join(P.DATA, "vetoes")
TODAY = datetime.now(ZoneInfo(P.TIMEZONE)).date().isoformat()


def url(year, n):
    return f"{BASE}/{year}/bill-notification-{year}-{n}.pdf"


def _path(year):
    return os.path.join(FOLDER, f"{year}.json")


def _load(year):
    try:
        return json.load(open(_path(year), encoding="utf-8"))
    except (OSError, ValueError):
        return {"read": {}, "checked": "", "notes": {}}


def _save(year, d):
    os.makedirs(FOLDER, exist_ok=True)
    with open(_path(year) + ".tmp", "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False)
    os.replace(_path(year) + ".tmp", _path(year))


def _get(u):
    """A notification's bytes; b"" when the number isn't there (the site's 404 page); None when the request failed."""
    time.sleep(1)
    try:
        with urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": AGENT}), timeout=90) as r:
            data = r.read()
    except urllib.error.HTTPError as e:
        return b"" if e.code == 404 else None
    except (urllib.error.URLError, OSError):
        return None
    return data if data[:5] == b"%PDF-" else b""


# (Every notification ends "As of this date, the governor has signed 94 bills; ... and vetoed 2 bills": not that.)
VETO = re.compile(r"\bvetoed the following\b|\bveto\s+message\b", re.I)


def fetch(years, minutes=10):
    stop = time.time() + minutes * 60
    for year in sorted(years, reverse=True):
        d = _load(year)
        if d["checked"] == TODAY or d["checked"] >= f"{year + 1}-01-15":
            continue
        n, misses, got = max((int(k) for k in d["read"]), default=0) + 1, 0, 0
        while misses < 2 and time.time() < stop:
            data = _get(url(year, n))
            if data is None:
                print(f"veto messages {year}: notification {n} failed; tried again next run", flush=True)
                break
            if not data:
                misses += 1
                n += 1
                continue
            pages = L.pdf_pages(data, ocr_from=2)
            if pages is None:
                break
            # (A number found after a missing one: the miss was a gap, not the end.)
            for k in range(n - misses, n):
                d["read"].setdefault(str(k), False)
            misses = 0
            has = any(VETO.search(t) for t, o in pages if not o)
            d["read"][str(n)] = has
            if has:
                d["notes"][str(n)] = {"url": url(year, n), "pages": [[t, o] for t, o in pages]}
            got += 1
            n += 1
        else:
            if misses >= 2:
                d["checked"] = TODAY
        # (Numbers asked for and missing at the end aren't kept: they're asked again next time.)
        d["read"] = {k: v for k, v in d["read"].items() if int(k) < n - misses}
        _save(year, d)
        print(f"veto messages {year}: {got} new notifications, {sum(d['read'].values())} with vetoes", flush=True)


# A notification's first page: "HB 5002   AN ACT ...  The veto message can be found on page 4 of this document."
_ENTRY = re.compile(r"(?m)^\s{0,4}(HB|SB)\s+(\d{1,5})\b")
_WHERE = re.compile(r"veto\s+message\s+(?:for\s+this\s+bill\s+)?(?:can\s+be\s+found|is)\s+on\s+pages?\s+(\d+)", re.I)
_SALUTE = re.compile(r"^\s*Dear (?:Madam|Mr\.|Madame) Secretary\s*[:,;]", re.I)
_CLOSE = re.compile(r"^\s*(?:Sincerely|Respectfully|Very truly yours)\b", re.I)


def _typed(lines):
    """A typed letter's lines -> its reasons: from after "Dear Madam Secretary:" to the closing, as paragraphs."""
    start = next((i + 1 for i, t in enumerate(lines) if _SALUTE.match(t)), 0)
    body = []
    for t in lines[start:]:
        if _CLOSE.match(t):
            break
        if re.fullmatch(r"\s*(?:Page \d+(?: of \d+)?|\d+)\s*", t):
            continue
        body.append(t)
    return L.wrapped(body)


def messages(year):
    """{"HB5002": {"text", "url", "ocr", "kind"}}: each veto (kind "absolute") or line-item veto ("line-item") of the
    year's notifications with its letter's paragraphs."""
    out = {}
    d = _load(year)
    for n, note in sorted(d.get("notes", {}).items(), key=lambda kv: int(kv[0])):
        pages = note["pages"]
        # The listing: the first page and any after it before the first letter (a scanned page, or one with the
        # salutation), in sections: "Governor Lamont signed the following legislation ...", "... signed and line-item
        # vetoed the following ...", "... vetoed the following ...".
        first = next((i for i, (t, o) in enumerate(pages) if i and (o or re.search(r"(?m)^\s*Dear (?:Madam|Mr\.|Madame) "
                                                                                      r"Secretary", t))), len(pages))
        head = "\n".join(t for t, _ in pages[:first])
        heads = [(m.start(), "line-item" if m.group(1) else "absolute" if m.group(2) else None)
                 for m in re.finditer(r"(?i)\b(?:(signed and line-item vetoed)|(vetoed)|signed)\s+the\s+following", head)]
        where = {}
        found = list(_ENTRY.finditer(head))
        for i, m in enumerate(found):
            kind = next((k for at, k in reversed(heads) if at < m.start()), None)
            if not kind:
                continue
            bill = f"{m.group(1)}{int(m.group(2))}"
            block = re.sub(r"\s+", " ", head[m.end():found[i + 1].start() if i + 1 < len(found) else len(head)])
            w = _WHERE.search(block)
            if w:
                where[bill] = (int(w.group(1)), kind)
                continue
            # No page given (2024, 2026): the letter's first page is the first after the listing that names the bill.
            cite = re.compile(rf"\b{'House' if m.group(1) == 'HB' else 'Senate'}\s+Bill\s+(?:No\.\s*)?{int(m.group(2))}\b", re.I)
            at = next((k for k in range(max(first, 1), len(pages)) if cite.search(pages[k][0])), None)
            if at is not None:
                where[bill] = (at + 1, kind)
        starts = sorted({p for p, _ in where.values()})
        for bill, (p, kind) in where.items():
            if not 1 <= p <= len(pages):
                continue
            nxt = next((s for s in starts if s > p), len(pages) + 1)
            part = pages[p - 1:nxt - 1]
            ocr = any(o for _, o in part)
            if ocr:
                paras = L.ocr_letter("\f".join(t for t, _ in part), governor=f"Ned {P.governor_on(f'{year}-12-31')}",
                                     start=r"^Dear (?:Madam|Mr\.?|Madame) Secretary")
            else:
                paras = _typed("\n".join(t for t, _ in part).split("\n"))
            text = L.cut(paras)
            if text:
                out[bill] = {"text": text, "url": note["url"], "ocr": ocr, "kind": kind}
    return out


if __name__ == "__main__":
    ys = [int(a) for a in sys.argv[1:]] or list(range(int(TODAY[:4]) - 4, int(TODAY[:4]) + 1))
    try:
        fetch(ys, minutes=30)
    except Exception as e:  # noqa: BLE001
        print(f"veto messages: failed ({type(e).__name__}: {e})")
    for y in ys:
        for b, m in messages(y).items():
            print(y, b, m["kind"], "OCR" if m["ocr"] else "", m["text"][:150].replace("\n", " | "))
