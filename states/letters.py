"""Governors' letters (veto messages) as text: shared helpers for the converters that read them from PDFs
(pdftotext -layout) or plain text. A veto message becomes a record's `vetoMemo`: {"year", "signer", "text"}, the text's
paragraphs joined by "\n" (tracker.html's memoText() shows each as a paragraph)."""
import re
from collections import Counter

MAX = 3500  # characters kept of a long message (budget vetoes run to dozens of pages)


def columns(page):
    """One page of `pdftotext -layout` text in two columns -> its lines in reading order (the left column, then the
    right), each as (indent, text). A page in one column is returned as it is."""
    lines = page.split("\n")
    width = max((len(ln) for ln in lines), default=0)
    # The gutter: positions blank on (nearly) every line, with text on both sides of them on several lines. Justified
    # lines have wide gaps too, but not at the same place on every line.
    body = [ln for ln in lines if ln.strip()]
    def blank(c):
        return sum(1 for ln in body if len(ln) > c and ln[c] != " ") <= 2
    col = None
    run = [c for c in range(int(width * 0.3), int(width * 0.8)) if blank(c)]
    if run:
        # The widest stretch of blank positions; the right column starts just after it.
        spans, cur = [], [run[0]]
        for c in run[1:]:
            if c == cur[-1] + 1:
                cur.append(c)
            else:
                spans.append(cur)
                cur = [c]
        spans.append(cur)
        span = max(spans, key=len)
        right = sum(1 for ln in body if len(ln) > span[-1] + 1 and ln[span[-1] + 1:].strip())
        left = sum(1 for ln in body if ln[:span[0]].strip())
        if len(span) >= 2 and right >= 5 and left >= 5:
            col = span[-1] + 1
    if col is None:
        return [(len(ln) - len(ln.lstrip()), ln.strip()) for ln in lines]
    left, right = [], []
    for ln in lines:
        # A line split at the gutter: blanks just before the column (a word can't cross it).
        # (or further right: a signature block, "Respectfully submitted," set beside the left column's last lines).
        cut = next((c for c in range(col - 4, len(ln)) if ln[c - 2:c] == "  " and ln[c] != " "), None)
        if cut is None and len(ln) > col and ln[:col].strip() == "":
            cut = col
        if cut is None:
            left.append(ln)
            continue
        left.append(ln[:cut])
        right.append(ln[cut:])
    out = [(len(ln) - len(ln.lstrip()), ln.strip()) for ln in left]
    base = min((len(r) - len(r.lstrip()) for r in right if r.strip()), default=0)
    out += [(len(r) - len(r.lstrip()) - base, r.strip()) for r in right]
    return out


def paragraphs(lines, indent=3, blanks=True):
    """(indent, text) lines -> paragraphs: a line indented `indent` or more columns past the block's own margin starts
    one, as does a blank line after a sentence's end (unless `blanks` is False: a two-column page's left side has blank
    lines wherever only the right side has text). A word broken across lines keeps its hyphen ("well- known" ->
    "well-known": the letters are typed, not hyphenated, so a hyphen at a line's end is the word's own)."""
    body = [(i, t) for i, t in lines]
    margin = Counter(i for i, t in body if t).most_common(1)
    margin = margin[0][0] if margin else 0
    out, cur, blank = [], [], False
    for i, t in body:
        if not t:
            blank = True
            continue
        if cur and (i - margin >= indent or (blanks and blank and cur[-1][-1:] in ".:;!?”\"")):
            out.append(" ".join(cur))
            cur = []
        cur.append(t)
        blank = False
    if cur:
        out.append(" ".join(cur))
    return [re.sub(r"\s+", " ", re.sub(r"(\w)- (\w)", r"\1-\2", p)).strip() for p in out if p.strip()]


def wrapped(lines, short=0.8):
    """Lines of a block-style letter (no indents) -> paragraphs: a paragraph ends at a blank line, or at a line well
    short of the text's usual width that ends a sentence ("Authority." before "At the request of the sponsor, ...")."""
    texts = [t.strip() for t in lines]
    lens = sorted(len(t) for t in texts if t)
    width = lens[int(len(lens) * 0.8)] if lens else 0
    out, cur = [], []
    for t in texts:
        if not t:
            if cur:
                out.append(" ".join(cur))
                cur = []
            continue
        cur.append(t)
        if len(t) < width * short and re.search(r"[.:!?\u201d\"]$", t):
            out.append(" ".join(cur))
            cur = []
    if cur:
        out.append(" ".join(cur))
    return [re.sub(r"\s+", " ", p).strip() for p in out if p.strip()]


def cut(paras, limit=MAX):
    """The first paragraphs, up to `limit` characters; a first paragraph longer than that is cut after a sentence."""
    s = ""
    for p in paras:
        if s and len(s) + len(p) > limit:
            break
        if not s and len(p) > limit:
            ends = [m.end() for m in re.finditer(r"[.!?][\"\u201d)]?(?=\s+[A-Z])", p[:limit])]
            return p[:ends[-1]] if ends else p[:limit].rsplit(" ", 1)[0] + " \u2026"
        s += ("\n" if s else "") + p
    return s


# ---------------------------------------------------------------------------------------------------------------------
# Scanned letters (OCR). Some governors' veto letters are images with no text layer (WY, MT, OR, SC, NC, AZ, KY, TX and
# a few of WI's): the owner approved reading them with text recognition (2026-11-22). Each letter is read once:
# `scanned()` keeps the result in <folder>/<key>.json ({url, ocr, raw, engine, read}) and never reads it again. The
# converters turn `raw` into paragraphs with `ocr_letter()` and store the message with "ocr": true and the letter's
# "url", so the page says it was read from a scan and links the original.
import json as _json
import os as _os
import shutil as _shutil
import subprocess as _sp
import tempfile as _tempfile
from datetime import datetime as _dt, timezone as _tz

OCR_PAGES = 6     # pages read of a long letter (a budget's line-item vetoes run to dozens; MAX keeps 3,500 characters)
OCR_DPI = 300


def ocr_ready():
    return bool(_shutil.which("pdftoppm") and _shutil.which("tesseract"))


def ocr_engine():
    try:
        out = _sp.run(["tesseract", "--version"], capture_output=True, text=True, timeout=30)
        return ((out.stdout or out.stderr).split("\n") or [""])[0].strip()
    except (OSError, _sp.SubprocessError):
        return ""


def pdf_text(data):
    """A PDF's own text layer (pdftotext -layout), "" when it has none."""
    try:
        return _sp.run(["pdftotext", "-layout", "-enc", "UTF-8", "-", "-"], input=data, capture_output=True,
                       timeout=120).stdout.decode("utf-8", "replace")
    except (OSError, _sp.SubprocessError):
        return ""


def ocr_pdf(data, pages=OCR_PAGES, dpi=OCR_DPI):
    """A scanned PDF (bytes) -> its text by OCR, pages separated by "\f"; None when the tools are missing or fail.
    Each page is rendered in grey at `dpi` (pdftoppm) and read by tesseract with fixed settings (LSTM engine, automatic
    page layout, English, one thread), so a run on another machine reads the same."""
    if not ocr_ready():
        return None
    with _tempfile.TemporaryDirectory() as tmp:
        src = _os.path.join(tmp, "in.pdf")
        with open(src, "wb") as f:
            f.write(data)
        try:
            _sp.run(["pdftoppm", "-r", str(dpi), "-gray", "-png", "-f", "1", "-l", str(pages), src,
                     _os.path.join(tmp, "p")], check=True, capture_output=True, timeout=600)
        except (OSError, _sp.SubprocessError):
            return None
        imgs = sorted((f for f in _os.listdir(tmp) if f.startswith("p") and f.endswith(".png")),
                      key=lambda f: int(re.search(r"(\d+)\.png$", f).group(1)))
        out = []
        for img in imgs:
            try:
                r = _sp.run(["tesseract", _os.path.join(tmp, img), "-", "--oem", "1", "--psm", "3", "-l", "eng"],
                            capture_output=True, timeout=300, env={**_os.environ, "OMP_THREAD_LIMIT": "1"})
            except (OSError, _sp.SubprocessError):
                return None
            if r.returncode:
                return None
            out.append(r.stdout.decode("utf-8", "replace"))
        return "\f".join(out)


def pdf_pages(data, ocr_from=1, max_ocr=OCR_PAGES * 2, dpi=OCR_DPI):
    """A PDF (bytes) -> [(text, ocr)] a page each: its own text (pdftotext -layout), or, for a page from `ocr_from` on
    with almost none (a scanned letter inside a typed document: CT's bill notifications), the page read by OCR (at most
    `max_ocr` pages). None when pdftotext fails; a page OCR can't read now (no tools) is ("", True)."""
    try:
        n = int(re.search(r"Pages:\s+(\d+)", _sp.run(["pdfinfo", "-"], input=data, capture_output=True,
                                                       timeout=60).stdout.decode("utf-8", "replace")).group(1))
    except (OSError, _sp.SubprocessError, AttributeError):
        return None
    out, ocrs = [], 0
    with _tempfile.TemporaryDirectory() as tmp:
        src = _os.path.join(tmp, "in.pdf")
        with open(src, "wb") as f:
            f.write(data)
        for p in range(1, n + 1):
            try:
                t = _sp.run(["pdftotext", "-layout", "-enc", "UTF-8", "-f", str(p), "-l", str(p), src, "-"],
                            capture_output=True, timeout=120).stdout.decode("utf-8", "replace")
            except (OSError, _sp.SubprocessError):
                return None
            if p < ocr_from or len(re.sub(r"\s", "", t)) > 100 or ocrs >= max_ocr:
                out.append((t, False))
                continue
            ocrs += 1
            got = ""
            if ocr_ready():
                try:
                    _sp.run(["pdftoppm", "-r", str(dpi), "-gray", "-png", "-f", str(p), "-l", str(p), "-singlefile", src,
                             _os.path.join(tmp, "pg")], check=True, capture_output=True, timeout=600)
                    r = _sp.run(["tesseract", _os.path.join(tmp, "pg.png"), "-", "--oem", "1", "--psm", "3", "-l", "eng"],
                                capture_output=True, timeout=300, env={**_os.environ, "OMP_THREAD_LIMIT": "1"})
                    got = r.stdout.decode("utf-8", "replace") if not r.returncode else ""
                except (OSError, _sp.SubprocessError):
                    got = ""
            out.append((got, True))
    return out


def scanned(folder, key, url, fetch, force_ocr=False):
    """The letter at `url`, read once and kept in <folder>/<key>.json: its own text when the PDF has one, else OCR.
    `fetch(url)` returns the PDF's bytes (or None). Returns the saved record, or None when it can't be read now (no
    tools, the download failed): it's tried again on a later run. A file that isn't a PDF is saved as unreadable
    ({"raw": ""}) so it isn't asked for again. `force_ocr`: OCR even when the PDF has a text layer (one an earlier OCR
    made badly: NC's "State of :Nortfi Carol1na")."""
    path = _os.path.join(folder, f"{key}.json")
    try:
        with open(path, encoding="utf-8") as f:
            return _json.load(f)
    except (OSError, ValueError):
        pass
    if not ocr_ready():
        return None
    data = fetch(url)
    if not isinstance(data, bytes):
        return None
    rec = {"url": url, "ocr": False, "raw": "", "read": _dt.now(_tz.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
    if data[:5] == b"%PDF-":
        own = "" if force_ocr else pdf_text(data)
        if len(re.sub(r"\s", "", own)) > 200:
            rec["raw"] = own
        else:
            got = ocr_pdf(data)
            if got is None:
                return None
            rec.update(ocr=True, raw=got, engine=ocr_engine())
    _os.makedirs(folder, exist_ok=True)
    with open(path + ".tmp", "w", encoding="utf-8") as f:
        _json.dump(rec, f, ensure_ascii=False)
    _os.replace(path + ".tmp", path)
    return rec


# Words OCR misreads in typed letters: a capital I read as J, l or |.
_I_NEXT = (r"am|have|had|was|will|would|do|did|cannot|can|must|believe|share|support|appreciate|respectfully|hereby|"
           r"veto|vetoed|recognize|agree|understand|urge|encourage|also|remain|strongly|look|hope|want|know|thank|"
           r"commend|disagree|find|feel|object|return|signed|sign|note|made|ask|applaud|value|trust|continue|welcome|"
           r"take|stand|could|should|may|might|fully|support|herewith|therefore|firmly|cannot|must")
_OCR_FIXES = [
    (re.compile(r"(?<![\w.])(?:[J|\]\[]|I[\]|])(?= [a-z])"), "I"),  # (J, |, ] and "I]" are never words of their own)
    (re.compile(rf"(?<![\w.])[l1](?= (?:{_I_NEXT})\b)"), "I"),
    (re.compile(r"(?<![\w.])[J|l1\]\[][’'](?=(?:m|ve|ll|d)\b)"), "I’"),
    (re.compile(r"(?<=[a-z])\|(?=[a-z])"), "l"),
    (re.compile(r"[‘`](?=\w)"), "‘"),
    (re.compile(r"ﬁ"), "fi"), (re.compile(r"ﬂ"), "fl"),
    (re.compile(r"\s+([,.;:])(?=\s|$)"), r"\1"),
    (re.compile(r"(?<=\w)([’']) (?=(?:s|t|ve|re|ll|d|m)\b)"), r"\1"),  # "They’ ve"
]

_SALUTE = re.compile(r"^(?:Dear\b.{0,80}|To the (?:Honorable|Members|Clerk|President|Speaker|Chief Clerk|Secretary).{0,200}[,:;]|"
                     r"(?:Mr\.|Madam|Madame) (?:Speaker|President)\b.{0,120}[,:;]|Ladies and Gentlemen.{0,40}|"
                     r"(?:Honorable|Dear) (?:Speaker|President|Members)\b.{0,120}[,:;]|"
                     r"(?:Mr\.|Madam|Madame) (?:Speaker|President)(?: and| &) .{0,120}[,:;]?)$", re.I)
_CLOSE = re.compile(r"^(?:Sincerely|Respectfully(?: submitted| yours)?|Very truly yours|Yours truly|Best regards|"
                    r"Kind regards|With (?:kind |warm |best )?regards|Cordially|Warm regards)\b[^.]{0,40}$", re.I)
_TAIL = re.compile(r"^(?:cc|c:|ce:|bec|xc|Enclosures?|Attachments?)\b\s*[:.]?|^[A-Z]{2,3}\s*[:/]\s*\w{1,4}\b")


def _norm(t):
    return re.sub(r"[^a-z0-9]", "", t.lower())


def ocr_letter(raw, governor="", start=None, end=None):
    """OCR text of a letter (pages separated by "\f", paragraphs by blank lines, as tesseract writes them) -> its
    paragraphs, the governor's reasons only: from just after the salutation ("Dear Speaker Neiman,", "To the Honorable
    ...:"; else after the "Re:" line; `start`, a pattern, overrides: the reasons start after the paragraph it matches)
    to the closing ("Sincerely,", the governor's name alone, "cc:"; `end`, a pattern, also stops it). Dropped: lines
    repeated on two or more pages (letterhead, footers), a continuation page's heading (its lines down to "Page 2"),
    signature scribbles and short fragments. A paragraph split by a page break joins up again."""
    gov = _norm(governor) if governor else ""
    pages = raw.split("\f")
    norms = [{_norm(x) for x in p.split("\n") if len(_norm(x)) >= 6} for p in pages]
    counts = Counter(n for s in norms for n in s)
    repeated = {n for n, k in counts.items() if k >= 2} if len(pages) >= 2 else set()
    paras = []  # ([lines], page index)
    for k, page in enumerate(pages):
        lines = page.split("\n")
        if k:
            # A continuation page's heading: the addressee, the date, "Page 2" in its first lines.
            hit = next((i for i, x in enumerate(lines[:14]) if re.fullmatch(
                r"\s*(?:-\s*)?Page\s*(?:\d+|[A-Z][a-z]+)(?:\s*of\s*\d+)?\s*-?\s*|\s*-\s*\d+\s*-\s*", x, re.I)), None)
            if hit is not None:
                lines = lines[hit + 1:]
        cur = []
        for x in lines + [""]:
            x = x.strip()
            if x and _norm(x) in repeated:
                x = ""
            if not x:
                if cur:
                    paras.append((cur, k))
                    cur = []
                continue
            # The governor's name on a line of its own (a signature right under the last sentence, no blank between:
            # NC's "Therefore, I veto the bill." / "Josh Stein") is a paragraph of its own, where the reasons end.
            if gov and cur and re.search(rf"\b{re.escape(governor.split()[-1])}\b", x) \
                    and len(x) < len(governor) + 30 and not re.search(r"[.;,]$", x):
                paras.append((cur, k))
                cur = []
            cur.append(x)
    # Each paragraph's lines joined.
    joined = []
    for lines, k in paras:
        t = ""
        for x in lines:
            if t.endswith("-") and not t.endswith(" -") and re.match(r"\w", x):
                # A hyphen at a line's end is the word's own: the letters are typed, not hyphenated ("data-" "informed",
                # "well-" "being", "9-2-" "1013").
                t += x
            else:
                t = f"{t} {x}" if t else x
        joined.append((re.sub(r"\s+", " ", t).strip(), k))
    texts = [t for t, _ in joined]
    first = None
    if start:
        first = next((i + 1 for i, t in enumerate(texts) if re.search(start, t, re.I)), None)
    if first is None:
        first = next((i + 1 for i, t in enumerate(texts) if _SALUTE.match(t)), None)
    if first is None:
        first = next((i + 1 for i, t in enumerate(texts) if re.match(r"(?:Re|RE|Subject)\s*[:.]", t)), 0)
    gov = _norm(governor) if governor else ""
    out = []
    for i in range(first, len(texts)):
        t, k = joined[i]
        if end and re.search(end, t, re.I):
            break
        if out and (_CLOSE.match(t) or _TAIL.match(t) or (gov and gov in _norm(t)[:len(gov) + 12] and len(t) < len(governor) + 30)
                    or re.fullmatch(r"Governor(?: of [A-Z][a-z]+(?: [A-Z][a-z]+)?)?", t)):
            break
        # Fragments: a signature read as letters, a page number, the letterhead's leftovers.
        if len(t) < 40 and not re.search(r"[.:;!?][\"”)]?$", t):
            continue
        if not re.search(r"[a-z]{3}", t):
            continue
        # A paragraph that runs on (the last one ended mid-sentence: a page break, or a gap OCR saw as one).
        if out and (not re.search(r"[.:!?][\"”)]?$", out[-1]) and re.match(r"[a-z(]", t) or out[-1].endswith(",")):
            out[-1] += ("" if out[-1].endswith("-") else " ") + t
            continue
        out.append(t)
    for pat, rep in _OCR_FIXES:
        out = [pat.sub(rep, t) for t in out]
    return [t for t in out if t]
