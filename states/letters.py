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
    """The first paragraphs, up to `limit` characters (at least one)."""
    s = ""
    for p in paras:
        if s and len(s) + len(p) > limit:
            break
        s += ("\n" if s else "") + p
    return s
