#!/usr/bin/env python3
""""What it does" for North Carolina: data/nc/texts_<session>.json, {"H4": {"statement": ..., "label": "From the
Legislative Analysis Division's summary of the bill's third edition."}}, from the bill summaries states/nc/fetch.py
saves as text (pdftotext -layout) in data/nc/<session>/summaries/.

The General Assembly's nonpartisan staff (the Legislative Analysis Division) writes a summary of a bill for each
committee meeting and floor vote, and of each session law after it's enacted: listed on
https://www.ncleg.gov/Legislation/Bills/Summaries/<session>/<H4>, each a PDF at
https://dashboard.ncleg.gov/api/Services/BillSummary/<session>/<id>. The id names the version it describes, in
parentheses: "H4-SMBP-47(e3)-v-3" (the third edition; "-v-3" is the summary's own revision), "(CSBP-8)" a proposed
committee substitute, "(CCSSVxr-9)" a conference committee's substitute, "(ABK-93)" an amendment, "(sl)" the session
law. Bills never taken up in committee have none.
Which summary: the session law's when there is one (a long law's are written part by part: "Part I: Personal Income Tax
Changes", "Sec. 5: ...": each part's opening paragraph, in order); otherwise the newest summary of the bill (not of an
amendment alone). Each is an analysis for legislators: a header (committee, sponsors, the staff member who wrote it),
OVERVIEW, CURRENT LAW, BILL ANALYSIS and EFFECTIVE DATE, and a footer (the division's director and phone, a
disclaimer). Kept: the overview (or a law summary's opening), the analysis when the overview is short, and the
effective date; current law (background) and tables (section-by-section charts) are left out.
Usage: python3 states/nc/texts.py [session ...]   (default: every downloaded session)
"""
import html, json, os, re, sys

DATA = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "nc"))
MAX = 2500  # characters of a statement, cut at a paragraph or sentence
PART_MAX = 400  # characters of each part of a law summarized part by part
MAX_PARTS = 8  # parts of a law read; a longer law's conference summary is used instead, else its first parts
BULLET = re.compile(r"^([•➢▪◦●○■□✓\-–]|o(?=\s{2,})|\(?\d{1,2}[.)]|\([ivxIVX]{1,4}\)|\(?[a-zA-Z][.)](?=\s))\s*")
LABEL = re.compile(r"^([A-Z][A-Z ,&/'-]{3,}[A-Z]S?):\s*(.*)$")  # "OVERVIEW: ...", "EFFECTIVE DATE: ..."
ABBREV = re.compile(r"(\b(G\.S|S\.L|Sec|Secs|No|Nos|U\.S|St|Mr|Mrs|Ms|Dr|Sen|Rep|Reps|Inc|Co|Corp|Jr|Sr|vs|v|"
                    r"approx|e\.g|i\.e|etc|Art|Ch|Pub|L)|\b[A-Z])\.$")
PART = re.compile(r"\s*(Parts?|Secs?\.?|Sections?)\s+[\dIVXLC]")  # a law summary's part: "Part VI: ...", "Sec. 5: ..."
ROMAN = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100}


def file_of(sid):
    """A summary id as a file name: "H4-SMBP-47(e3)-v-3" -> "H4-SMBP-47_e3_-v-3.txt"."""
    return re.sub(r"[^A-Za-z0-9-]", "_", sid) + ".txt"


# ---------------------------------------------------------------- the list page

def parse_list(page):
    """The summaries a bill's list page links: [{"id", "desc", "updated" (YYYY-MM-DD)}]."""
    out = []
    for href, sid, desc, upd in re.findall(
            r'<tr>\s*<td[^>]*><a href="([^"]*BillSummary/\d{4}/[^"]+)">(.*?)</a></td>\s*<td[^>]*>.*?</td>\s*'
            r'<td>(.*?)</td>\s*<td>(.*?)</td>', page, re.S):
        m = re.match(r"\s*(\d\d)/(\d\d)/(\d{4})", upd)
        out.append({"id": html.unescape(sid).strip(), "desc": html.unescape(re.sub(r"<[^>]+>", "", desc)).strip(),
                    "updated": f"{m.group(3)}-{m.group(1)}-{m.group(2)}" if m else ""})
    return out


def version_of(sid):
    """What a summary describes, from its id: ("law",), ("conference",), ("edition", n), ("substitute",),
    ("amendment",) or ("other",)."""
    m = re.search(r"\(([^)]*)\)", sid)
    v = m.group(1) if m else ""
    if v == "sl":
        return ("law",)
    if re.fullmatch(r"e\d+", v):
        return ("edition", int(v[1:]))
    if v.startswith("CC"):
        return ("conference",)
    if v.startswith("CS") or v.startswith("PCS"):
        return ("substitute",)
    if re.match(r"S?A[A-Z]", v):
        return ("amendment",)
    return ("other",)


def seq(sid):
    """(the staff's document number, the summary's revision): "H4-SMBP-47(e3)-v-3" -> (47, 3)."""
    m = re.search(r"-SM[A-Za-z]*-(\d+)\(.*\)-v-(\d+)$", sid)
    return (int(m.group(1)), int(m.group(2))) if m else (0, 0)


def part_key(desc):
    """Order of a law's parts, numbers compared as numbers: "Part XII: ..." -> (0, 12), "Sec. 1D.10: ..." ->
    (1, 1, "D", 10)."""
    m = re.match(r"\s*Part\s+([IVXLC]+)\b", desc)
    if m:
        r, total = m.group(1), 0
        for i, ch in enumerate(r):
            v = ROMAN[ch]
            total += -v if i + 1 < len(r) and ROMAN[r[i + 1]] > v else v
        return (0, total)
    head = desc.split(":", 1)[0]
    return (1,) + tuple(int(t) if t.isdigit() else t for t in re.findall(r"\d+|[A-Z](?=[.\d])", head)) + (desc,)


def law_parts(rows):
    """A law's summaries, one per part (a revised part replaces its earlier revision), in order."""
    best = {}
    for r in rows:
        if version_of(r["id"]) == ("law",):
            k = r["desc"]
            if k not in best or seq(r["id"]) > seq(best[k]["id"]):
                best[k] = r
    return sorted(best.values(), key=lambda r: part_key(r["desc"]))


def choose(rows):
    """The summaries to read for a bill: [one id], the session law's parts in order, or []."""
    laws = law_parts(rows)
    if len(laws) == 1 and not PART.match(laws[0]["desc"]):
        return [laws[0]["id"]]
    if laws:
        # A law summarized part by part (S 382 of 2023-24 has 70 parts; H 562 of 2025-26 only its Section 5): the
        # conference committee's summary of the whole when there is one, else the parts (the first few of a long law).
        conf = [r for r in rows if version_of(r["id"]) == ("conference",)]
        if conf:
            return [max(conf, key=lambda r: (r["updated"], seq(r["id"])))["id"]]
        return [r["id"] for r in laws[:MAX_PARTS]]
    rank = {"conference": 3, "edition": 2, "substitute": 1, "other": 0}
    bills = [r for r in rows if version_of(r["id"])[0] in rank]
    if not bills:
        return []
    def key(r):
        v = version_of(r["id"])
        return (r["updated"], rank[v[0]], v[1] if len(v) > 1 else 0, seq(r["id"]))
    return [max(bills, key=key)["id"]]


# ---------------------------------------------------------------- a summary's text

def is_table(s):
    """A row of a table (columns set apart by wide gaps), after a bullet's own spacing."""
    s = BULLET.sub("", s.strip())
    return len(re.findall(r"\S\s{4,}(?=\S)", s)) >= 1


def body_lines(raw):
    """The summary's lines without the header, the page headers and footers, footnotes and staff credits; and
    what it analyzes ("Third Edition", "S.L. 2025-8") and the division that wrote it."""
    pages = raw.split("\f")
    meta = {"of": "", "division": "Legislative Analysis Division"}
    if re.search(r"Fiscal\s+Research\s+Division", raw):
        meta["division"] = "Fiscal Research Division"
    out = []
    for pi, page in enumerate(pages):
        lines = page.split("\n")
        # Footer: from the summary's id ("*H4-SMBP-47(e3)-v-3*") or the disclaimer back over the director's block.
        end = len(lines)
        for i, ln in enumerate(lines):
            if re.search(r"\*[HS]\d+-SM\S*\*|This bill analysis was prepared by the nonpartisan", ln):
                end = i
                break
        while end > 0 and (not lines[end - 1].strip() or footerish(lines[end - 1])):
            end -= 1
        lines = lines[:end]
        start = 0
        if pi == 0:
            # The header ends at the first blank line after "Analysis of:".
            a = next((i for i, ln in enumerate(lines) if "Analysis of:" in ln), None)
            if a is not None:
                of = re.split(r"\s{3,}|Prepared by:|Date:", lines[a].split("Analysis of:", 1)[1].strip())[0]
                j = a + 1
                while j < len(lines) and lines[j].strip():
                    nxt = re.split(r"\s{3,}|Prepared by:|Date:", lines[j].strip())[0]
                    if nxt and not re.search(r"Attorney|Analyst|Counsel|Staff|Division|Team|Director", nxt):
                        of += " " + nxt
                    j += 1
                meta["of"] = re.sub(r"\s+", " ", of).strip()
                start = j
        else:
            # Page headers: "Senate Bill 595" / "Senate 595 CCS" and "Page 2".
            k = 0
            while k < len(lines) and k < 4 and (not lines[k].strip() or re.fullmatch(
                    r"(House|Senate)( Bill)? \d+.{0,40}|Page \d+( of \d+)?", lines[k].strip())):
                k += 1
            start = k
        out += lines[start:]
    # Footnotes ("1" alone, then its text) and staff credits ("*Name, Staff Attorney ..., contributed to this summary.").
    kept, skip = [], False
    for ln in out:
        s = ln.strip()
        if re.fullmatch(r"\d|[ivx]{1,4}", s):
            skip = True
            continue
        if skip and s and not re.match(r"^[A-Z ,&]{6,}:", s) and len(ln) - len(ln.lstrip()) <= 1:
            continue
        skip = False
        kept.append(ln)
    text = "\n".join(kept)
    text = re.sub(r"(?m)^\s*\*[^*\n]*(?:\n[^\n]+)*?contributed to this (summary|analysis)\.?\s*$", "", text)
    return meta, text.split("\n")


def footerish(ln):
    s = ln.strip()
    return bool(re.fullmatch(r"Legislative Analysis|Division|Director|Legislative\s+Analysis\s+Division|"
                             r"\d{3}-\d{3}-\d{4}|Fiscal Research|[A-Z][a-z]+( [A-Z]\.)? [A-Z][A-Za-z'-]+", s)
                or len(ln) - len(ln.lstrip()) > 60)


def caps_heading(s):
    letters = [c for c in s if c.isalpha()]
    return len(letters) >= 6 and sum(c.isupper() for c in letters) >= 0.9 * len(letters) and " " in s


def paragraphs(lines):
    """[(section, paragraph)]: wrapped lines joined; a paragraph starts at a blank line, a bullet, a section label,
    or after a line that ends a sentence well short of the margin. Tables are left out."""
    width = max([len(ln.rstrip()) for ln in lines if ln.strip() and not is_table(ln)] + [1])
    out, cur, section, in_table = [], "", "", False
    def flush():
        nonlocal cur
        if cur.strip():
            out.append((section, re.sub(r"\s+", " ", cur).strip()))
        cur = ""
    for ln in lines:
        raw = ln.rstrip().replace("�", "").replace("­", "").replace(" ", " ")
        s = raw.strip()
        if not s:
            flush()
            in_table = False
            continue
        m = LABEL.match(s)
        if m and m.group(1) not in ("NOTE",):
            flush()
            section = m.group(1)
            in_table = False
            s = m.group(2)
            if not s:
                continue
        elif caps_heading(s):
            flush()  # "PART I – DISASTER RELIEF", "SUBPART I-B. EDUCATION": headings, left out
            continue
        elif is_table(raw) or in_table and len(raw) - len(raw.lstrip()) > 12:
            flush()
            in_table = True
            out.append((section, None))  # a table: marks where it was
            continue
        b = BULLET.match(s)
        if b and (b.group(1) not in ("-", "–") or s[1:2] == " "):
            flush()
            s = "• " + s[b.end():] if b.group(1) in "•➢▪◦●○■□✓-–o" else s
        if cur and (cur.endswith("-") and not cur.endswith(" -")):
            cur += s
        else:
            cur = (cur + " " + s) if cur else s
        if len(raw) < 0.8 * width and re.search(r"[.:;?!][\"”’)]?$", s):
            flush()
    flush()
    # Lettered and numbered items inside a sentence ("... ordinances that: (i) included ...; and (ii) ...") rejoin it.
    joined = []
    for sec, p in out:
        if p and joined and joined[-1][1] and joined[-1][0] == sec and re.match(r"\(\w{1,4}\)\s", p) \
                and re.search(r"([:;,]|\band|\bor)$", joined[-1][1]):
            joined[-1] = (sec, joined[-1][1] + " " + p)
        else:
            joined.append((sec, p))
    # Endnote markers after a word ("by legislative act.i This"), from the notes left out above.
    return [(sec, p if p is None else re.sub(r"(?<=[a-z][.,;])(?:i{1,3}|iv|vi{0,3}|ix|x)(?=\s|$)", "", p))
            for sec, p in joined]


def sentences_cut(p, limit):
    """p cut at the last sentence end before limit (never inside "G.S." or "S.L."), or ""."""
    best = ""
    for m in re.finditer(r"[.!?][\"”’)]?(?=\s|$)", p[:limit + 1]):
        if not ABBREV.search(p[:m.start() + 1]):
            best = p[:m.end()]
    return best


def cut(paras, limit=MAX):
    """Whole paragraphs up to limit characters (a first one longer than that cut at a sentence); a last paragraph
    that doesn't end a sentence (an introduction to what didn't fit, a list item, a heading) is dropped."""
    out, n = [], 0
    for p in paras:
        if n + len(p) > limit:
            if not out or n < limit / 2 and not p.startswith("• "):
                part = sentences_cut(p, limit - n)
                if part:
                    out.append(part)
            break
        out.append(p)
        n += len(p) + 1
    while out and not re.search(r"[.!?][\"”’)]?$", out[-1]):
        out.pop()  # an introduction to a list that didn't fit, a list item ("...; and"), or a heading
    return out


def summary(raw):
    """A summary's text -> {"of": what it analyzes, "division", "paras": what it does, "effective": the effective
    date paragraph or ""}."""
    meta, lines = body_lines(raw)
    ps = paragraphs(lines)
    keep = {"": [], "OVERVIEW": [], "BILL ANALYSIS": [], "EFFECTIVE DATE": []}
    other = []
    for sec, p in ps:
        if p is None:
            # A table ends what's kept of its section (a list introduced just before it is dropped by cut()).
            keep.setdefault(sec, []).append(None)
            continue
        k = "EFFECTIVE DATE" if sec.startswith("EFFECTIVE DATE") else "BILL ANALYSIS" if "BILL ANALYSIS" in sec else sec
        if re.search(r"contributed to this (summary|analysis)|assisted (with|in) (this|the) (summary|analysis)", p):
            continue  # staff credits
        if k in keep:
            keep[k].append(p)
        elif not re.match(r"CURRENT LAW|BACKGROUND", sec):
            other.append(p)
    def upto_table(xs):
        return xs[:xs.index(None)] if None in xs else xs
    lead = upto_table(keep[""]) + upto_table(keep["OVERVIEW"])
    analysis = upto_table(keep["BILL ANALYSIS"])
    eff = " ".join(upto_table(keep["EFFECTIVE DATE"]))
    if not lead and not analysis:
        analysis = [p for p in other if p is not None]
    paras = lead + (analysis if not lead or sum(map(len, lead)) < 600 else [])
    return {**meta, "paras": paras, "effective": eff}


def lower_first(s):
    return s[:1].lower() + s[1:] if s[:2] != s[:2].upper() else s


def what_of(of):
    """What a summary analyzes, in words: "Third Edition" -> "the bill's third edition"."""
    of = of.strip().rstrip(".")
    m = re.match(r"S\.\s*L\.\s*(\d{4}-\d+)", of)
    if m:
        return f"the law (S.L. {m.group(1)})"
    if re.match(r"Conference (Committee )?(Substitute|Report)", of, re.I):
        return "the conference committee's version"
    m = re.match(r"(?:PCS|Proposed Committee Substitute) (?:to|for) (?:the )?(\w+) Edition", of, re.I)
    if m:
        return f"the committee's new version of the {m.group(1).lower()} edition"
    m = re.match(r"(\w+) Edition\b", of, re.I)
    if m:
        return f"the bill's {m.group(1).lower()} edition"
    m = re.match(r"(?:House|Senate) Committee Substitute", of, re.I)
    if m:
        return "the committee substitute"
    return ""


def words(t):
    return {w for w in re.findall(r"[a-z]{4,}", t.lower())} - {"various", "changes", "act", "acts", "bill", "laws",
                                                               "modifications", "provisions", "technical"}


def text_of(folder, entry, title=""):
    """One bill's entry for the texts file, or None. entry: the bill's summaries.json record; title: the bill's
    title now."""
    ids = choose(entry.get("rows", []))
    rows = {r["id"]: r for r in entry.get("rows", [])}
    if len(ids) == 1 and version_of(ids[0]) != ("law",) and title:
        # The list gives the bill's title when each summary was written: one sharing no word with today's means the
        # bill was rewritten since (H 562 of 2025-26, a behavioral health bill that became budget corrections).
        if not words(rows[ids[0]]["desc"]) & words(title) and words(rows[ids[0]]["desc"]):
            return None
    docs = []
    for sid in ids:
        try:
            raw = open(os.path.join(folder, "summaries", file_of(sid)), encoding="utf-8").read()
        except OSError:
            return None  # not read yet: nothing rather than part of it
        docs.append((sid, summary(raw)))
    if not docs:
        return None
    if len(docs) == 1:
        s = docs[0][1]
        eff = s["effective"]
        body = cut(s["paras"], MAX - (len(eff) + 20 if eff else 0))
        if not body:
            return None
        if eff and not any(re.search(r"\beffective\b", p, re.I) for p in body):
            body.append(eff if re.match(r"(Effective|Except|It|This|The|Sections?|Parts?)\b", eff) else "Effective date: " + eff)
        what = what_of(s["of"])
        if PART.match(rows.get(docs[0][0], {}).get("desc", "")) and what.startswith("the law"):
            what = "one part of " + what  # H 562 of 2025-26: only its Section 5 was summarized
        label = f"From the {s['division']}'s summary" + (f" of {what}." if what else ".")
        return {"statement": "\n".join(body), "label": label}
    # A law summarized part by part: each part's opening paragraph.
    parts, law = [], ""
    for sid, s in docs:
        ps = s["paras"]
        i = next((k for k, p in enumerate(ps) if not p.startswith("• ")), None)
        if i is None or re.search(r"\b(please )?see the summary (of|for)\b", ps[i], re.I):
            continue  # a cross-reference to another law's summary
        first = ps[i]
        if first.endswith(":"):
            # "... does the following:" and its list, as far as it fits.
            items = []
            for p in ps[i + 1:]:
                if not p.startswith("• ") or len(first) + sum(len(x) + 2 for x in items) + len(p) > PART_MAX * 1.5:
                    break
                items.append(p[2:].rstrip(".;"))
            if not items:
                continue
            first = first + " " + "; ".join(lower_first(x) for x in items) + "."
        elif len(first) > PART_MAX:
            first = sentences_cut(first, PART_MAX) or sentences_cut(first, 700)
            if not first:
                continue
        desc = rows.get(sid, {}).get("desc", "")
        if not re.match(r"(Part|Sections?|Secs?\.)\s", first) and desc:
            first = f"{desc.rstrip('.')}: {lower_first(first)}"
        parts.append(first)
        law = law or (re.search(r"S\.\s*L\.\s*\d{4}-\d+", s["of"]) or [""])[0]
    body = cut(parts, MAX + 1000)
    if not body:
        return None
    more = len(law_parts(entry.get("rows", []))) - len(body)
    if more > 0:
        body.append(f"The law has {more} more part{'s' if more > 1 else ''}, each with its own summary on the General "
                    f"Assembly's website.")
    law = re.sub(r"S\.\s*L\.\s*", "S.L. ", law)
    law = f" ({law})" if law else ""
    div = docs[0][1]["division"]
    return {"statement": "\n".join(body),
            "label": f"From the {div}'s summaries of the law{law}, part by part."}


def write(session):
    """data/nc/texts_<session>.json from the saved summaries; returns how many bills have a text."""
    folder = os.path.join(DATA, str(session))
    try:
        index = json.load(open(os.path.join(folder, "summaries.json")))
    except (OSError, ValueError):
        return 0
    out = {}
    for key in sorted(index, key=lambda k: (k[0], int(re.sub(r"\D", "", k) or 0))):
        bill = {}
        try:
            bill = json.load(open(os.path.join(folder, "bills", f"{key}.json")))
        except (OSError, ValueError):
            pass
        try:
            t = text_of(folder, index[key], bill.get("title", ""))
        except Exception as e:  # one summary that fails to read mustn't stop the rest
            print(f"{session} {key}: summary not read ({type(e).__name__}: {e})", flush=True)
            t = None
        if t:
            out[key] = t
    path = os.path.join(DATA, f"texts_{session}.json")
    with open(path + ".tmp", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=0)
    os.replace(path + ".tmp", path)
    print(f"texts_{session}.json: {len(out)} bills", flush=True)
    return len(out)


if __name__ == "__main__":
    yrs = [int(a) for a in sys.argv[1:]] or sorted(int(f) for f in os.listdir(DATA) if re.fullmatch(r"\d{4}", f))
    for y in yrs:
        write(y)
