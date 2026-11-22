"""Arizona's yearly Summary of Legislation, read into "What it does" (states/az/NOTES.md, "Summaries").

Both research staffs publish one a year, about two and a half months after the session ends, as one PDF each:
www.azleg.gov/alispdfs/57leg/2R/House/SummaryComplete.pdf ("The Book", House Majority Research Staff) and
.../Senate/SummaryComplete.pdf ("The Spiel", Senate Research Staff); robots.txt allows /alispdfs/ (Crawl-delay 120).
Each has a paragraph on every measure that passed the Legislature, grouped by committee: enacted laws, vetoed bills and
measures referred to the voters. azleg.py's `books()` saves each PDF's text in data/az/azleg/books/<year>-House.txt and
-Senate.txt; `summaries()` reads them, the House's first (its paragraphs are the plainer ones), the Senate's for what the
House's leaves out or when it's missing (2024's House file at that address is the House Journal).
"""
import os, re

HEAD = re.compile(r"^((?:HB|SB|HCR|SCR|HJR|SJR|HCM|SCM)) ?(\d{4})\s*(?:/\s*(?:HB|SB) ?\d{4}\s*)?(?:\(([^)]*)\))?\s*:\s*(.*)$")
END = re.compile(r"^Click here for\b", re.I)
SKIP = re.compile(r"^(?:\(?Effective:|\(See:|\d{1,3}$)", re.I)
EFFECTIVE = re.compile(r"\s*\(?Effective:? (?:on )?[A-Z][a-z]+ \d{1,2}, \d{4}\)?\.?$")


def paragraphs(body):
    """Lines -> paragraphs: a line ending a sentence that is much shorter than the longest ends one; a word hyphenated
    at a line's end is joined."""
    if not body:
        return ""
    width = max(len(x) for x in body)
    paras, cur = [], []
    for k, ln in enumerate(body):
        if cur and re.search(r"[a-z]-$", cur[-1]):
            cur[-1] += ln
        else:
            cur.append(ln)
        if re.search(r"[.:;][\"')”’]*$", ln) and len(ln) < 0.8 * width and k + 1 < len(body):
            paras.append(" ".join(cur))
            cur = []
    if cur:
        paras.append(" ".join(cur))
    return "\n".join(re.sub(r"\s+", " ", p).strip() for p in paras if p.strip())


def house_book(text):
    """{"HB2502": "Allows an elected official ..."} from the House book's text (pdftotext without -layout). Entries:

        HB 2502 (Chapter 201): ASRS; retirement; elected officials
        Allows an elected official who is an Arizona State Retirement System (ASRS) member and
        who attains a normal retirement date to retire ...
        Effective: September 12, 2026
        Click here for bill history.

    ("HB 4155/SB 1848 (Chapter 127): ..." for a budget bill and its mirror, kept for the first; "HB 2584 (Vetoed): ...";
    resolutions "HCR 2001: ..." and "Click here for resolution history."). The body runs from the line after the heading
    (and after the title's wrapped part: a heading ending in ";" or ",", or a short lowercase line) to "Click here for",
    without the effective date (its own line in 2026, the paragraph's end in 2025) and page numbers."""
    lines = [ln.strip() for ln in text.splitlines()]
    out = {}
    i = 0
    while i < len(lines):
        m = HEAD.match(lines[i])
        if not m:
            i += 1
            continue
        bill = m[1] + str(int(m[2]))
        title = m[4]
        j = i + 1
        while j < len(lines) and lines[j] and not HEAD.match(lines[j]) and (
                re.search(r"[;,]$", title) or re.fullmatch(r"[a-z][a-z' -]{0,40}", lines[j])):
            title += " " + lines[j]
            j += 1
        body = []
        while j < len(lines) and not END.match(lines[j]) and not HEAD.match(lines[j]):
            ln = EFFECTIVE.sub("", lines[j]) if EFFECTIVE.search(lines[j]) else lines[j]
            if ln and not SKIP.match(ln):
                body.append(ln)
            j += 1
        if j < len(lines) and END.match(lines[j]) and body:
            s = paragraphs(body)
            if s:
                out[bill] = s
        i = j
    return out


SENATE_HEAD = re.compile(r"\(([HS])\.(B|C\.R|C\.M|J\.R|M|R)\. ?(\d{4})(?:\s*/[^)]*)?\)\s*(?:[–-]\s*(.*))?$")
KIND = {"B": "B", "C.R": "CR", "C.M": "CM", "J.R": "JR", "M": "M", "R": "R"}


def senate_book(text):
    """{"SB1020": "Requires the Arizona Department of Transportation ..."} from Senate Research's book (pdftotext without
    -layout). An entry's heading ends with its numbers, "special plate; Arizona space commission (S.B. 1020) – Chapter
    13", its title sometimes over two lines and the outcome on the next ("– Chapter 172"). Its body runs to the next
    heading; a committee's box at a section's start ("Senator ..., Chairperson", its staff, the section's capitals) and
    page numbers are left out, and so are entries that only point to another committee's ("SEE THE NATURAL RESOURCES
    COMMITTEE.")."""
    lines = [ln.strip() for ln in text.splitlines()]
    out, state = {}, {"bill": None, "body": [], "skipping": False}

    def close():
        body = state["body"]
        if state["bill"] and body and not re.match(r"SEE (?:THE )?[A-Z]", body[0]):
            s = paragraphs([EFFECTIVE.sub("", x) or x for x in body])
            if s and state["bill"] not in out:
                out[state["bill"]] = s

    i = 0
    while i < len(lines):
        ln = lines[i]
        m = SENATE_HEAD.search(ln)
        body = state["body"]
        if ln == "Bill Index":  # the back of the book
            break
        nxt = lines[i + 1] if i + 1 < len(lines) else ""
        if m and (m[4] or re.match(r"[–-]\s", nxt) or m.start() == 0 or not re.search(r"[.]$", ln[:m.start()].strip())):
            # The title's first line ended the last entry's body when the heading wraps.
            if body and (ln.startswith("(") or not re.search(r"[.:;)\]]$", body[-1])):
                body.pop()
            close()
            state.update(bill=m[1] + KIND[m[2]] + str(int(m[3])), body=[], skipping=False)
            if i + 1 < len(lines) and re.match(r"[–-]\s*(?:Chapter|VETOED|Transmitted|Filed)", lines[i + 1]):
                i += 1
            i += 1
            continue
        if re.search(r"Chairperson$", ln):
            # The committee's name, on the lines before, isn't the last entry's.
            while body and not re.search(r"[.)\]]$", body[-1]):
                body.pop()
            state["skipping"] = True
        elif not ln or re.fullmatch(r"\d{1,3}", ln) or (ln.isupper() and len(ln) > 3):
            pass
        elif not state["skipping"] and state["bill"]:
            body.append(ln)
        i += 1
    close()
    return out


def summaries(folder, year):
    """{bill: (summary, "House"|"Senate")} for one year, from the saved texts in <folder> (data/az/azleg/books/)."""
    out = {}
    for house, read in (("House", house_book), ("Senate", senate_book)):
        try:
            text = open(os.path.join(folder, f"{year}-{house}.txt"), encoding="utf-8").read()
        except OSError:
            continue
        if house == "House" and "SUMMARY OF LEGISLATION" not in re.sub(r"\s+", " ", text[:3000]).upper().replace("S UMMARY", "SUMMARY"):
            continue  # (2024's House file is the Journal)
        for bill, s in read(text).items():
            out.setdefault(bill, (s, house))
    return out
