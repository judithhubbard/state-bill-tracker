#!/usr/bin/env python3
""""What it does" for Idaho: data/id/texts_<year>.json, {"H3": {"statement": ..., "label": "From the sponsor's statement
of purpose."}}, from the Statements of Purpose that states/id/fetch.py saves as text (pdftotext -layout) in
data/id/<year>/sop/H0003.txt.

A Statement of Purpose / Fiscal Note is a page (sometimes two) written for the bill's sponsor, attached to every bill:
"STATEMENT OF PURPOSE", the request number and bill ("RS31872 / H0001"), what the bill does in a few paragraphs, then
"FISCAL NOTE" (the cost), "Contact:" (the member who asked, with a phone), the stock disclaimer (Joint Rule 18: a
proponent's statement, not legislative intent) and a footer ("Bill SOP/FN REVISED: 01/14/2025, 4:41 PM"). Only the
statement of purpose is kept: not the fiscal note, the contact or the disclaimer. The sponsor's own account (it can
argue for the bill), so it's labelled as the sponsor's.
Usage: python3 states/id/texts.py [year ...]   (default: every downloaded year)
"""
import json, os, re, sys

DATA = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "id"))
LABEL = "From the sponsor's statement of purpose."
MAX = 2500  # characters, cut at a paragraph or sentence

# Where the statement of purpose ends: the fiscal note, the contact, the disclaimer.
END = re.compile(r"^(FISCAL\s+(NOTE|IMPACT)\b|Contact\s*:|DISCLAIMER\b)", re.I)
# Page furniture and the heading.
SKIP = re.compile(r"^(REVISED|AMENDED|CORRECTED|STATEMENT OF PURPOSE|Statement of Purpose\s*/\s*Fiscal Note.*|"
                  r"Bill SOP/FN\b.*|RS\s?\d+\w*\s*(/.*)?|(H|S|HJR|SJR)\s?\d+\w*|Page \d+( of \d+)?|-?\s*\d+\s*-?)$", re.I)
# A line that starts a list item, so a new paragraph.
ITEM = re.compile(r"^(•|·|▪|◦|-\s|–|—|\*\s|\(?\d{1,2}[.)]\s|\(?[a-zA-Z][.)]\s|\([ivx]+\)\s|Section \d+[.:]|Sec\. \d+)")
ABBREV = re.compile(r"(\b(No|Nos|St|Mr|Mrs|Ms|Dr|Sen|Rep|Inc|Co|Corp|Jr|Sr|vs|v|approx|e\.g|i\.e|etc|Art|Ch|U\.S|"
                    r"Sec|Secs)|\b[A-Z])\.$")


def number(key):
    """"H0003" -> "H3"; "HJR004" -> "HJR4" (states/id/convert.py's number())."""
    m = re.fullmatch(r"([A-Z]+?)0*(\d+)", key)
    return f"{m.group(1)}{int(m.group(2))}" if m else key


def clean(s):
    s = s.replace("�", "").replace("­", "").replace(" ", " ").replace("​", "")
    s = s.replace("", "•").replace("", "•")  # Symbol-font bullets
    return re.sub(r"\s+", " ", s).strip()


def paragraphs(raw):
    """The statement of purpose's paragraphs: from the heading to the fiscal note, page furniture left out. Paragraphs end
    at a blank line (pdftotext -layout keeps one between them) or before a list item; a line ending in a hyphen joins
    the next without a space ("non-" + "public")."""
    lines = raw.replace("\f", "\n\n").split("\n")
    start = next((i + 1 for i, ln in enumerate(lines) if re.match(r"\s*STATEMENT OF PURPOSE\s*$", ln, re.I)), 0)
    paras, cur = [], ""
    for ln in lines[start:]:
        s = clean(ln)
        if END.match(s):
            break
        if not s:
            if cur:
                paras.append(cur)
            cur = ""
            continue
        if SKIP.match(s):
            continue
        if cur and ITEM.match(s):
            paras.append(cur)
            cur = ""
        if cur.endswith("-") and re.search(r"[A-Za-z]-$", cur) and s[:1].islower():
            cur += s
        elif cur.endswith("/"):
            cur += s
        else:
            cur = f"{cur} {s}".strip()
    if cur:
        paras.append(cur)
    return [p for p in (clean(p) for p in paras) if p and re.search(r"[a-z]", p)]


def sentences(p):
    """A paragraph's sentences (not split after abbreviations or initials)."""
    out, cur = [], ""
    for piece in re.split(r"(?:(?<=[.!?])|(?<=[.!?][\"”’)]))\s+(?=[\"“(]?[A-Z0-9])", p):
        cur = f"{cur} {piece}".strip()
        if not ABBREV.search(cur):
            out.append(cur)
            cur = ""
    if cur:
        out.append(cur)
    return out


def split_long(paras, longest=700, chunk=350):
    """Paragraphs over `longest` characters (a statement written as one block) split into groups of sentences of about
    `chunk` characters or more, breaking before a sentence that starts a new point ("Secondly, ...") when it can."""
    out = []
    for p in paras:
        if len(p) <= longest:
            out.append(p)
            continue
        cur = ""
        for s in sentences(p):
            if len(cur) >= 60 and re.match(r"(First|Second|Third|Fourth|Fifth|Finally|Lastly|Additionally|In "
                                                  r"addition|Also|Further)", s):
                out.append(cur)  # a new point: break before it
                cur = ""
            cur = f"{cur} {s}".strip()
            if len(cur) >= chunk:
                out.append(cur)
                cur = ""
        if cur:
            if out and len(cur) < chunk / 2:
                out[-1] += " " + cur
            else:
                out.append(cur)
    return out


def capped(paras):
    """Paragraphs up to MAX characters, cut at a paragraph's or sentence's end; a last paragraph that stops mid-sentence
    (the page cut it off) is left out unless it's all there is."""
    out, n = [], 0
    for p in paras:
        if n + len(p) <= MAX:
            out.append(p)
            n += len(p) + 2
            continue
        keep = []
        for s in sentences(p):
            if n + len(s) + 1 > MAX:
                break
            keep.append(s)
            n += len(s) + 1
        if keep:
            out.append(" ".join(keep))
        break
    if len(out) > 1 and not re.search(r"[.!?:;][\"”’)]?$", out[-1]) and not ITEM.match(out[-1]):
        out.pop()
    return out


def text_of(raw):
    paras = capped(split_long(paragraphs(raw)))
    if not paras:
        return None
    statement = "\n\n".join(paras)
    if len(statement) < 20:
        return None
    return {"statement": statement, "label": LABEL}


def write(year):
    """data/id/texts_<year>.json from the saved statements; returns how many bills have a text."""
    folder = os.path.join(DATA, str(year), "sop")
    if not os.path.isdir(folder):
        return 0
    out = {}
    for name in sorted(os.listdir(folder)):
        if not name.endswith(".txt"):
            continue
        try:
            t = text_of(open(os.path.join(folder, name), encoding="utf-8").read())
        except OSError:
            continue
        if t:
            out[number(name[:-4])] = t
    path = os.path.join(DATA, f"texts_{year}.json")
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=0)
    os.replace(tmp, path)
    print(f"texts_{year}.json: {len(out)} bills", flush=True)
    return len(out)


if __name__ == "__main__":
    yrs = [int(a) for a in sys.argv[1:]] or sorted(int(f) for f in os.listdir(DATA) if re.fullmatch(r"\d{4}", f))
    for y in yrs:
        write(y)
