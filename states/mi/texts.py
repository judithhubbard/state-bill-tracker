#!/usr/bin/env python3
""""What it does" for Michigan: data/mi/texts_<session>.json, {"HB4001": {"statement": ..., "label": ...}}, from the
House Fiscal Agency's and Senate Fiscal Agency's bill analyses (nonpartisan staff), which states/mi/fetch.py saves as
text in data/mi/<session>-<session + 1>/analyses/ (`analyses()` there).

Where they are: https://www.legislature.mi.gov/documents/2025-2026/billanalysis/house/pdf/2025-HLA-4001-7Q3WFG05.pdf
(the House's, PDFs only) and .../billanalysis/senate/htm/2025-SFA-0006-F.htm (the Senate's, also as PDFs). The four
characters after HLA/SFA are the bill's number, the highest of a package's ("0002" for Senate Bills 1 and 2; House
analyses of Senate bills, and of resolutions, have numbers under 4000 too: "2025-HLA-0002" is House Concurrent
Resolution 2), letters for joint resolutions; the year is the session's first year or the year introduced. So which bills
a document covers, and which version, comes from its heading: "House Bill 4001 (H-2) as reported from committee",
"Senate Bills 20 through 22 (as introduced 1-22-25)", "S.B. 18 & H.B. 4750: ANALYSIS AS ENACTED".

A bill usually has several analyses as it moves (introduced, a committee substitute, reported, passed by one house,
enacted). The one used is the latest version (`RANK`), then the latest date ("Complete to 1-16-25", "Date Completed:
7-31-26"), either agency's. Kept: what the bill would do, the House's "SUMMARY:" (without its "Background" part) and the
Senate's "CONTENT"; left out: background, rationale, arguments for and against, positions, fiscal impact, the statute
citations ("MCL 408.414"), footnotes, tables and the analysts' names. Budget bills' analyses (tables) give nothing.
Joint resolutions are left out: the page keys texts by number without a final letter, so "HJRA" and "HJRB" would share one.
Usage: python3 states/mi/texts.py [session ...]   (default: every downloaded session; 2025 for 2025-2026)
"""
import glob, html, json, os, re, sys

DATA = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "mi"))
MAX = 2500  # characters of a statement, cut at a paragraph or sentence
AGENCY = {"HLA": "House Fiscal Agency", "SFA": "Senate Fiscal Agency"}

# Sections a document's text is saved without (they're never used, and the House's lists of testifiers are long).
DROP_SECTIONS = re.compile(r"^(FISCAL IMPACT|POSITIONS|ARGUMENTS|SUPPORTING ARGUMENTS?|OPPOSING ARGUMENTS?|RESPONSE|"
                           r"BRIEF DISCUSSION|RATIONALE|BRIEF RATIONALE)\b")
HEADING = re.compile(r"^[A-Z][A-Z ,/&'’()-]{3,}:?\s*$")  # "SUMMARY:", "FISCAL IMPACT:", "CONTENT", "ANALYSIS AS ENACTED"
# Where a summary ends: the next section.
END = re.compile(r"^(FISCAL IMPACT|POSITIONS|ARGUMENTS|SUPPORTING ARGUMENT|OPPOSING ARGUMENT|BRIEF DISCUSSION|RATIONALE|"
                 r"BRIEF RATIONALE|BACKGROUND|PREVIOUS LEGISLATION|INTRODUCTION|RESPONSE|FOOTNOTES?)\b")
ABBREV = re.compile(r"(\b(Rev|Stat|Sec|Secs|No|Nos|U\.S|St|Mr|Mrs|Ms|Dr|Sen|Rep|Inc|Co|Corp|Jr|Sr|vs|v|approx|e\.g|i\.e|"
                    r"etc|Art|Ch|H\.B|S\.B|P\.A)|\b[A-Z])\.$")


# ---- the downloaded document -> text (used by fetch.py before saving) ----

def htm_text(raw):
    """A Senate analysis (Word's HTML) -> one line per paragraph."""
    s = raw.decode("utf-8-sig", "replace") if isinstance(raw, bytes) else raw
    s = re.sub(r"(?is)<(style|script|head|xml)\b.*?</\1>|<!--.*?-->", "", s)
    s = re.sub(r"(?is)<sup\b.*?</sup>|<a [^>]*href=\"?#_ftn\w*\"?[^>]*>.*?</a>", "", s)  # footnote markers
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"(?i)<br\b[^>]*>|</p>|</h\d>|</tr>|</li>|</div>|</td>", "\n", s)
    s = html.unescape(re.sub(r"<[^>]+>", "", s)).replace("\xa0", " ")
    lines = [re.sub(r"[ \t]+", " ", ln).strip() for ln in s.split("\n")]
    return "\n".join(ln for ln in lines if ln)


def trim(text):
    """A document's text without the sections that are never used (fiscal impact, positions, arguments, rationale)."""
    out, skipping = [], False
    for ln in text.split("\n"):
        s = ln.strip()
        if HEADING.match(s) and not re.match(r"(S|H)\.", s):
            skipping = bool(DROP_SECTIONS.match(s))
        if not skipping or re.fullmatch(r"\d{1,2}", ln.rstrip()):  # footnote numbers kept, to find their markers
            out.append(ln.rstrip())
    return "\n".join(out)


# ---- which bills, which version ----

WORDS = {"bill": "B", "joint resolution": "JR"}


def refs(header):
    """Bills a heading names: "House Bills 4161 to 4170", "Senate Bills 1 and 2", "S.B. 19 (S-1) - 22", "S.B. 18 & H.B.
    4750", "Seante Bills 20 through 22" -> ["HB4161", ...]. Resolutions other than joint resolutions are left out."""
    out = []
    pat = re.compile(r"\b(?:(House|Senate|Seante|Sentate)\s+(Bills?|Joint\s+Resolutions?|Concurrent\s+Resolutions?|Resolutions?)"
                     r"|([HS])\.\s?(B|J\.\s?R|C\.\s?R|R)\.)\s*((?:(?:\d{1,4}|[A-Z]{1,2})(?:\s*\([HS]-\d+\))?(?:\s*(?:,|and|&|"
                     r"to|through|-|–|—)\s*(?=\d|[A-Z]{1,2}\b))?)+)", re.I)
    for m in pat.finditer(header):
        house = (m.group(1) or m.group(3) or "")[0].upper()
        house = "S" if house == "S" else "H"
        kind = (m.group(2) or m.group(4) or "").lower().replace(" ", "").replace(".", "")
        if kind.startswith("bill") or kind == "b":
            prefix = house + "B"
        elif kind.startswith("joint") or kind == "jr":
            prefix = house + "JR"
        else:
            continue  # a concurrent or simple resolution
        body = re.sub(r"\([HS]-\d+\)", "", m.group(5))
        toks = re.findall(r"\d{1,4}|\b[A-Z]{1,2}\b|to|through|-|–|—", body)
        nums, rng = [], False
        for t in toks:
            if t in ("to", "through", "-", "–", "—"):
                rng = True
                continue
            if t.isdigit() and rng and nums and nums[-1].isdigit() and int(nums[-1]) < int(t) <= int(nums[-1]) + 60:
                nums += [str(i) for i in range(int(nums[-1]) + 1, int(t) + 1)]
            else:
                nums.append(t)
            rng = False
        for n in nums:
            if prefix.endswith("B") and n.isdigit():
                out.append(f"{prefix}{int(n)}")
            elif prefix.endswith("JR") and n.isalpha():
                out.append(f"{prefix}{n}")
    return list(dict.fromkeys(out))


# (rank, words for the label): the furthest version first.
RANK = [(r"as enacted|public acts? \d|analysis as enacted", 6, "as enacted"),
        (r"as enrolled", 5, "as passed by the Legislature"),
        (r"passed by the (house|senate)|(house|senate)-passed", 4, None),
        (r"third reading|by the committee of the whole", 3, "as it reached the floor"),
        (r"reported|as discharged|discharged bill", 2, "as reported from committee"),
        (r"substitute|\([HS]-\d+\)", 1, "as rewritten in committee"),
        (r"introduced", 0, "as introduced")]


def version(header):
    for pat, rank, words in RANK:
        m = re.search(pat, header, re.I)
        if m:
            if words is None:
                words = f"as passed by the {(m.group(1) or m.group(2)).capitalize()}"
            return rank, words
    return 0, ""


def doc_date(header):
    """"Complete to 1-16-25", "Revised 3-10-23", "Date Completed: 7-31-26" -> "2025-01-16", or ""."""
    m = re.search(r"(?:Complete to|Revised|Date Completed:?)\s*(\d{1,2})-(\d{1,2})-(\d{2,4})", header)
    if not m:
        return ""
    y = int(m.group(3))
    return f"{y + 2000 if y < 100 else y:04d}-{int(m.group(1)):02d}-{int(m.group(2)):02d}"


# ---- the summary ----

def house_parts(text):
    """A House analysis (pdftotext -layout): (heading, summary lines). The heading is the left column before
    "SUMMARY:"; the summary runs to the next section. Footnotes (unindented, at each page's foot), page footers ("House
    Fiscal Agency ... Page 2 of 7") and tables (columns three spaces apart) are left out."""
    lines = text.replace("\f", "\n").split("\n")
    start = next((i for i, ln in enumerate(lines) if re.match(r"\s*(BRIEF )?SUMMARY:", ln)), None)
    # Both columns: a package's heading lists bills side by side.
    head = " ".join(c for ln in lines[:start if start is not None else 25] for c in re.split(r"\s{3,}", ln.strip())
                    if not re.match(r"(Phone:|http|Analysis available)", c))
    if start is None:
        return head, [], set()
    body = []
    notes = {ln for ln in lines if re.fullmatch(r"\d{1,2}", ln.rstrip())}  # footnote numbers (each page's foot, or the end)
    in_note = False
    for ln in lines[start + 1:]:
        s = ln.strip()
        if re.fullmatch(r"\d{1,2}", ln.rstrip()):
            in_note = True  # a footnote: its number at the margin, its text (first line indented) to the next blank line
            continue
        if in_note:
            in_note = bool(s)
            continue
        if re.match(r"[A-Z][A-Z ,/&'’-]{3,}:\s*$", s) and not ln.startswith("    "):
            break  # the next section
        if re.match(r"\s*(Legislative|Fiscal) Analysts?:", ln) or s.startswith("■"):
            break
        indent = len(ln) - len(ln.lstrip())
        if s and indent < 3:
            continue  # footnote text, page footers
        if re.search(r"\S {3,}\S", s) and not re.match(r"[•o▪-]\s", s):
            continue  # a table row
        body.append(s)
    return head, body, notes


def senate_parts(text):
    """A Senate analysis (one line per paragraph): (heading, summary lines). The heading is everything before the first
    section; the summary is the CONTENT section, or (when a document has no such heading) the paragraphs from the first
    that says what the bill "would" do."""
    lines = text.split("\n")
    first = next((i for i, ln in enumerate(lines) if END.match(ln) or ln.strip() == "CONTENT"
                  or re.match(r"(The|This|These) (bill|bills|joint resolution)s? would|(Senate|House) (Bill|Joint Resolution)s?"
                              r" [\w(), -]{1,60} would\b", ln)), len(lines))
    head = " ".join(lines[:first])
    start = next((i + 1 for i, ln in enumerate(lines) if ln.strip() == "CONTENT"), None)
    if start is None:
        start = next((i for i, ln in enumerate(lines) if i >= first and re.search(r"\bwould\b", ln) and len(ln) > 60), None)
    if start is None:
        return head, [], set()
    body = []
    for ln in lines[start:]:
        s = ln.strip()
        if END.match(s) or s == "CONTENT" or re.match(r"(Legislative|Fiscal) Analysts?:", s):
            break
        body += [s, ""]
    return head, body, set()


def clean_lines(body, notes):
    """Summary lines -> paragraphs: wrapped lines joined (a hyphen at a line's end kept only between words that take
    one), bullets ("•", "--") as their own paragraphs, headings and the "Background" part left out, statute citations
    and footnote markers removed."""
    paras, cur, skip = [], "", False

    def flush():
        nonlocal cur
        if cur.strip():
            paras.append(cur.strip())
        cur = ""

    width = max([len(x.strip()) for x in body] + [1])
    for i, s in enumerate(body + [""]):
        s = s.replace("\ufffd", "").replace("\u00ad", "").strip()
        if not s:
            flush()
            continue
        nxt = next((x.strip() for x in body[i + 1:] if x.strip()), "")
        # A heading: a short line without a sentence's end, after a paragraph's end, followed by a capitalized line.
        if (len(s) < min(70, 0.8 * width) and not re.search(r"[.:;,?!)\]”\"]$", s) and nxt[:1].isupper()
                and (not cur or re.search(r"[.:;?!][\"”’)]?$", cur))
                and not re.match(r"[•o▪]\s|--|(House|Senate) (Bill|Joint)", s)) \
                or re.fullmatch(r"(Senate|House) (Bills?|Joint Resolutions?) [\dA-Z][\d\s,&()SH-]*(and [\d\s()SH-]+)?", s):
            flush()
            skip = bool(re.match(r"(Background|Previous legislation|History|Current law|Discussion)\b", s, re.I))
            if re.match(r"(Senate|House) (Bills?|Joint Resolutions?) [\dA-Z]", s):
                paras.append("\x00" + s)  # a bill's own part of a package's summary begins (for_bill())
            continue
        if skip:
            continue
        if re.match(r"(Proposed )?MCL \d|\d{2,3}\.\d+[a-z]*( et al\.)?( \([SH]\.B\. \d+\))?$", s):
            continue
        if re.match(r"[•o▪]\s|--\s?|–\s", s):
            flush()
            s = "• " + re.sub(r"^([•o▪]|--|–)\s*", "", s)
        if cur.endswith("-") and re.search(r"[a-z]-$", cur) and s[:1].islower():
            cur = cur + s  # "non-" + "partisan": pdftotext keeps the hyphen of a hyphenated word
        else:
            cur = (cur + " " + s) if cur else s
        # A line that ends a sentence well short of the column's width ends its paragraph (some PDFs have no blank
        # lines between paragraphs).
        if len(s) < 0.8 * width and re.search(r"[.:;?!][\"”’)]?$", s):
            flush()
    flush()
    out = []
    for p in paras:
        p = re.sub(r"\s+", " ", p)
        for n in notes:  # footnote markers: "election. 1 Then", "wage.3", "reason, 1 the act"
            p = re.sub(rf"(?:(?<=[a-z])|(?<=[.,;:)”\"’]) ?){n}(?=[\s.,;)]|$)", "", p)
        p = re.sub(r"\s*\(?https?://\S+", "", p)  # links (a footnote's, or a law's address in parentheses)
        p = re.sub(r"\s+([.,;:])", r"\1", p).strip()
        if len(p) > 1 or p.startswith("\x00"):
            out.append(p)
    # An introduction to a table or list that was left out ("the following schedule:") says nothing on its own.
    return [p for i, p in enumerate(out) if not p.endswith(":") or i + 1 < len(out) and out[i + 1].startswith("• ")]


def sentences_cut(p, limit):
    best = ""
    for m in re.finditer(r"[.!?][\"”’)]?(?=\s|$)", p[:limit + 1]):
        if not ABBREV.search(p[:m.start() + 1]):
            best = p[:m.end()]
    return best


def cut(paras, limit=MAX):
    """Whole paragraphs up to limit characters (a first paragraph longer than that cut at a sentence); a paragraph that
    introduces a list that didn't fit ("to do the following:") is dropped from the end."""
    paras = [p for p in paras if not p.startswith("\x00")]
    out, n = [], 0
    for p in paras:
        if n + len(p) > limit:
            if not out:
                part = sentences_cut(p, limit)
                if part:
                    out.append(part)
            break
        out.append(p)
        n += len(p) + 1
    while out and (out[-1].endswith(":") or not re.search(r"[.!?:;][\"”’)]?$", out[-1])):
        out.pop()
    return out


def parse(name, text):
    """One saved document -> {"bills", "rank", "words", "date", "agency", "paras"}."""
    kind = name.split("-")[1]
    head, body, notes = (house_parts if kind == "HLA" else senate_parts)(text)
    rank, words = version(head)
    paras = clean_lines(body, notes)
    # A summary that only says the bill would make changes, with nothing after it, says nothing.
    if paras and sum(map(len, cut(paras))) < 60:
        paras = []
    return {"bills": refs(head), "rank": rank, "words": words, "date": doc_date(head), "agency": AGENCY.get(kind, kind),
            "paras": paras}


def for_bill(paras, bill):
    """A package's summary for one of its bills: what comes before the first bill's own part ("Broadly speaking, the
    bills would ..."), then this bill's part ("Senate Bill 1134 would amend ...", with its list), then the rest; cut."""
    blocks, cur = [[]], None
    for p in paras:
        lead = re.split(r"\b(would|amends|amended|enacted|creates|created)\b", p)[0][:150]
        if p.startswith("\x00") or not p.startswith("• ") and re.match(r"(House|Senate) (Bills?|Joint Resolutions?) ", p) \
                and len(lead) < len(p) and refs(lead):
            cur = refs(lead)
            blocks.append([])
        blocks[-1].append((p, cur))
    own = [p for b in blocks[1:] for p, who in b if who and bill in who]
    if not own:
        return cut(paras)
    rest = [p for b in blocks[1:] for p, who in b if not (who and bill in who)]
    return cut([p for p, _ in blocks[0]] + own + rest)


def listing_day(stamp):
    """"4/17/2025 11:03 AM 228669" -> "2025-04-17"."""
    m = re.match(r"(\d+)/(\d+)/(\d{4})", stamp or "")
    return f"{m.group(3)}-{int(m.group(1)):02d}-{int(m.group(2)):02d}" if m else ""


def write(session):
    """data/mi/texts_<session>.json from the saved analyses; returns how many bills have a text."""
    folder = os.path.join(DATA, f"{session}-{session + 1}", "analyses")
    if not os.path.isdir(folder):
        return 0
    try:
        seen = json.load(open(os.path.join(folder, "listing.json")))
    except (OSError, ValueError):
        seen = {}
    best = {}
    for path in sorted(glob.glob(os.path.join(folder, "*.txt"))):
        name = os.path.basename(path)[:-4]
        d = parse(name, open(path, encoding="utf-8").read())
        if not d["paras"]:
            continue
        key = (d["rank"], d["date"] or listing_day(seen.get(name, {}).get("stamp")), listing_day(seen.get(name, {}).get("stamp")))
        for b in d["bills"]:
            if "JR" in b:
                continue  # see above
            if b not in best or key > best[b][0]:
                best[b] = (key, d)
    out = {}
    for b, (_, d) in sorted(best.items(), key=lambda kv: (kv[0][0], int(re.sub(r"\D", "", kv[0]) or 0))):
        others = len([x for x in d["bills"] if "JR" not in x]) - 1
        subject = "the bill" if others < 1 else "this bill and " + (f"{others} others" if others > 1 else "one other")
        label = f"From the {d['agency']}'s analysis of {subject}" + (f" {d['words']}" if d["words"] else "") + "."
        out[b] = {"statement": "\n".join(for_bill(d["paras"], b) if others > 0 else cut(d["paras"])), "label": label}
    path = os.path.join(DATA, f"texts_{session}.json")
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=0)
    os.replace(tmp, path)
    print(f"texts_{session}.json: {len(out)} bills", flush=True)
    return len(out)


if __name__ == "__main__":
    yrs = [int(a) for a in sys.argv[1:]] or sorted(int(os.path.basename(f)[:4]) for f in glob.glob(os.path.join(DATA, "[0-9]" * 4 + "-*")))
    for y in yrs:
        write(y)
