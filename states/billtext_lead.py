#!/usr/bin/env python3
""""What it does" from a bill's own text, for bills with no official summary: quoted, not paraphrased, and no AI.

A state's reader turns a bill's text into sections (`Section` dicts, below); `lead()` picks from them
  1. its statement of intent or purpose ("It is the intent of the legislature to ...", "The purpose of this act is ...",
     or a findings section's concluding "Therefore ..." sentence), at most two sentences;
  2. the opening sentence of each section that makes new law (WA's "NEW SECTION."), skipping definitions, severability,
     effective and expiration dates, short titles, codification and other boilerplate, at most four;
  3. when the bill only amends existing law, the whole sentences it adds (underlined in WA's text), else the sections
     it amends ("Amends RCW 19.27.031 and 43.21C.035.").
`statement()` writes them as "What it does" text (the intent as a paragraph, the rest as "• " lines, as other states'
summaries write lists) with its source sentence. Only whitespace and section numbers are changed; a sentence too long
to show is cut at a clause and ends with "…". `problems()` is what test/data_check.py checks: boilerplate, too long,
or only the title's words again.

A Section is a dict: {"num": "2", "new": True/False/None (None: the text doesn't say), "paras": [paragraphs as plain
text, deleted wording left out], "added": [whole sentences an amendment adds], "cite": "RCW 46.92.010" (what an
amended section amends), "repeal": bool}.
"""
import re
from html.parser import HTMLParser

MAX_SENTENCE = 420   # a quoted sentence longer than this is cut at a clause
MAX_INTENT = 600
MAX_BULLETS = 4
MAX_TOTAL = 1200

# Abbreviations a period doesn't end a sentence after.
ABBR = re.compile(r"(?:\b(?:Sec|Secs|Sess|No|Nos|Inc|Co|Corp|Ltd|Dr|Mr|Mrs|Ms|St|Ste|Jr|Sr|vs|v|seq|etc|al|approx|Dept|Art|"
                  r"Ch|ch|Chap|Stat|Rev|Ann|Gen|Laws|Pub|Div|Subd|Para|par|cl|subsec|Mo|Tit|Supp|Fed|Reg|Ord|Res|Exec|Admin|"
                  r"Gov|Rep|Sen|Hon|Op|Atty|Ass'n|Assn|Bros|Cal|Fla|Ga|Ill|Ind|Kan|Ky|La|Mass|Md|Me|Mich|Minn|Miss|Mont|Neb|"
                  r"Nev|Okla|Or|Ore|Pa|Tenn|Tex|Va|Vt|Wash|Wis|Wyo|Ariz|Ark|Colo|Conn|Del|Haw|Ida|Ia|Alas|N\.C|S\.C|N\.D|S\.D)"
                  r"|\b[A-Z]|\b(?:U\.S|e\.g|i\.e|a\.m|p\.m|U\.S\.C|C\.F\.R))\.$")

INTENT = re.compile(
    r"\b(?:it is (?:the )?(?:intent|purpose|policy|goal) of (?:the |this )?(?:legislature|general assembly|state|act|"
    r"chapter|section|bill|people)|(?:the |this )(?:legislature|general assembly) (?:therefore )?(?:intends|declares (?:that )?"
    r"(?:it is )?(?:the|its) (?:intent|purpose|policy))|the (?:intent|purpose|purposes|goal) of this (?:act|chapter|bill|section|"
    r"subchapter|article) (?:is|are)|this (?:act|chapter|bill) is intended to)\b", re.I)
FINDINGS = re.compile(r"^(?:The (?:legislature|general assembly|people of [\w ]+) (?:further )?(?:finds|recognizes|declares)|"
                      r"(?:Legislative )?(?:findings?|intent|purpose|declaration)\b)", re.I)
LEADIN = re.compile(r"^(?:Therefore|Accordingly|Thus|Consequently|Hence|For these reasons|To that end|In addition|Further(?:more)?),\s+", re.I)

# Sections (by their opening words) that aren't what the bill does.
BOILER = re.compile(
    r"^(?:"
    # definitions
    r"(?:The )?definitions? (?:in|set forth in) this|(?:As|When) used in this|(?:For|In) (?:the )?purposes? of this (?:act|chapter|"
    r"section|subsection|subchapter|article|part),? (?:the (?:following|term|words?)|unless|[\"“])|"
    r"(?:For|In) (?:the )?purposes? of this [a-z]+,[^.]{0,120}?\b(?:means|includes|shall mean|has the (?:same )?meaning)\b|Unless the context (?:clearly )?(?:requires|indicates) otherwise|In this (?:act|chapter|section)"
    r"(?:, unless[^:]*)?:|\"[^\"]{1,80}\" (?:means|includes|has the meaning)|“[^”]{1,80}” (?:means|includes|has the meaning)|"
    r"[A-Z][\w,'-]*(?: [\w,'-]+){0,6} (?:means|shall mean)\b|[^.]{0,120}\bDefinitions?\s*[:.]|"
    # severability, construction, application
    r"If any (?:provision|part|section|portion|clause|phrase) of this|The provisions of this act are severable|This act is severable|"
    r"(?:Captions|Part headings|Section headings|Subheadings|Headings) used in this|Nothing in this (?:act|section|chapter) (?:shall be|may be|is to be)? ?"
    r"construed|This act (?:shall|must|is to) be (?:liberally )?construed|This act applies (?:prospectively|retroactively)|"
    r"This act is remedial|This act is retroactive|This act applies (?:to|for) taxes levied|If any part of this act is found to be in conflict with federal|"
    # effective dates, expiration, emergency clauses
    r"This (?:act|section|chapter|subsection|amendatory act)(?:, except[^,]*,)? (?:takes|shall take|will take|is to take) effect|"
    r"(?:Sections?|Subsections?) [\d\w ,.()-]+ (?:of this act )?(?:takes?|shall take) effect|"
    r"This (?:act|section|chapter|subsection) (?:expires|shall expire|is repealed|terminates)|"
    r"(?:Sections?|Subsections?) [\d\w ,.()-]+ (?:of this act )?(?:expires?|shall expire)|"
    r"This act is necessary for the immediate preservation|(?:Except as (?:otherwise )?provided (?:in|by) [^,]{1,80},\s*)?this act "
    r"(?:takes|shall take) effect|If (?:this act|secs?\.[^,]{1,40}|sections?[^,]{1,40}) takes effect, it takes effect|"
    r".{0,160}?\bappl(?:y|ies) (?:only )?to .{0,120}?\b(?:on or after|before) the effective date|"
    r"[^.]{0,120}\b(?:terminates|is repealed|expires) (?:on )?(?:[A-Z][a-z]+ \d{1,2}, \d{4}|June 30|December 31)\.$|"
    r"An emergency (?:is hereby declared|exists)|Whereas an emergency|"
    r"This act (?:shall be|is) in (?:full )?force|"
    # names, codification, the code reviser
    r"This (?:act|chapter|bill|part|article|subchapter) (?:may|shall|must|will) be (?:known|cited|referred to)|This (?:act|chapter) is known as|"
    r"(?:Sections?|Chapters?) [\d\w ,.()-]+ (?:of this act )?(?:constitutes?|are each added|is added|shall be added|are added|is codified)|"
    r"The code reviser|The revisor of statutes|The legislative (?:services|counsel)|(?:RCW|Section|Sections) [\d\w .,()-]+ (?:is|are) (?:each )?(?:re|de)codified|"
    r"The following acts or parts of acts are each repealed|The following sections? (?:of|are)|"
    # appropriations boilerplate (an appropriation itself is kept)
    r"If specific funding for the purposes of|This act is null and void|"
    # tax preference paperwork (WA: "RCW 82.32.805 and 82.32.808 do not apply to this act."; performance statements)
    r"(?:RCW|Sections?) [\d.]+(?: and [\d.]+)? (?:does|do) not apply|This section is the tax preference performance statement|"
    r"This act is necessary for the support of the state government|"
    # appropriation acts' standing clauses (MS: how the money is paid, the accounts kept, ties among bids)
    r"The money appropriated (?:by|in|under) this act shall be paid|It is the intention of the Legislature,? that,? (?:of )?(?:the )?[^.]{0,80}"
    r"(?:shall maintain complete accounting|whenever two \(2\) or more bids|is hereby authorized to purchase and pay premiums|"
    r"shall be expended in compliance)|"
    r"(?:Any|All) (?:of the )?(?:money|funds) (?:remaining|not expended|unexpended|appropriated (?:by|in) this act (?:which|that) (?:are|is) "
    r"unexpended)|The State Fiscal Officer shall"
    r")", re.I)
# A section that's an intent or findings section has already given its intent sentence.
CODIFY_HEAD = re.compile(r"^(?:A |Two |Three |\w+ )?new (?:sections?|chapters?|subsections?) (?:is|are) (?:each )?(?:hereby )?added to .{0,120}?(?:to read as follows|as follows)?:?$|"
                         r"^.{0,160}\b(?:is|are) (?:each )?(?:hereby )?(?:amended|reenacted and amended|enacted) to read (?:as follows)?:?$", re.I)


def clean(t):
    t = re.sub(r"\s+", " ", t or "").strip()
    return re.sub(r"\s+([.,;:)])", r"\1", t)


def tidy(t):
    """Layout left in a paragraph: dot leaders ("Defibrillator......... $ 2,500.00") and Mississippi's "* * *" where
    wording was deleted."""
    t = re.sub(r"\s*\.{4,}\s*", " ", t)
    return clean(re.sub(r"\s*\*\s\*\s\*\s*", " ", t))


def sentences(text):
    """Sentences of a paragraph, as written."""
    out, start = [], 0
    for m in re.finditer(r"[.!?][\"”’)]*(?=\s+(?:[\"“(]?[A-Z(]))", text):
        piece = text[start:m.end()]
        if ABBR.search(piece.rstrip("\"”’)")) or re.search(r"\b\d+\.$", piece) and not re.search(r"\b(?:19|20)\d\d\.$|\$[\d,.]+\.$|percent\.$", piece):
            continue
        out.append(piece.strip())
        start = m.end()
    rest = text[start:].strip()
    if rest:
        out.append(rest)
    return out


def unnumber(t):
    """A paragraph without its subsection marks: "(1)(a) The department ..." -> "The department ..."."""
    # ("Section 2. The ..." loses its number; "Section 2 of this act takes effect ..." keeps it.)
    t = re.sub(r"^[-–\s]+", "", t.strip())  # (MA's ":- No ...")
    t = re.sub(r"^[“\"]?(?:(?:Sec\.|Section|SECTION)\s*\d+[A-Za-z-]*(?:\.\d+[A-Za-z-]*)*\s*[.:]\s*|§\s*\d+[\w.-]*\s+)", "", t)
    return re.sub(r"^(?:\((?:\d+|[a-z]{1,4}|[A-Z])\)\s*)+", "", t).strip()


def cut(s, limit=MAX_SENTENCE):
    """A sentence no longer than limit, cut at a clause when it's longer."""
    if len(s) <= limit:
        return s
    head = s[:limit]
    for sep in ("; ", ", and ", ", or ", ", "):
        k = head.rfind(sep)
        if k > limit * 0.5:
            return head[:k].rstrip(",;") + " …"
    return head[:head.rfind(" ")] + " …"


def opening(paras, limit=MAX_SENTENCE):
    """The first full sentence of a section. A sentence leading into a list ("The study must include:") takes its items
    while they fit."""
    if not paras:
        return ""
    first = unnumber(paras[0])
    if not first:
        return ""
    paras = list(paras)
    # A paragraph broken mid-sentence by the page's layout (AK's "... if the" / "permittee") goes on with the next one.
    while len(paras) > 1 and not re.search(r"[.:;!?\"”’)]$", first) and not re.match(r"^\((?:[a-z]{1,4}|\d+|[A-Z])\)", paras[1]):
        first = clean(first + " " + paras[1])
        paras = [first] + paras[2:]
    s = sentences(first)[0]
    # A lead-in to a list: "... include:", or a paragraph that stops mid-sentence ("... an opioid overdose drug if").
    if s.endswith(":") or (len(sentences(first)) == 1 and not re.search(r"[.!?\"”’)]$", s) and len(paras) > 1):
        items = []
        for p in paras[1:]:
            item = clean(p)
            if not re.match(r"^\((?:[a-z]{1,4}|\d+|[A-Z])\)", item):
                break
            if len(s) + sum(len(i) + 1 for i in items) + len(item) > limit:
                items.append("…")
                break
            items.append(item)
        if not items:
            return ""  # a lead-in with nothing after it
        return clean(s + " " + " ".join(items))
    return cut(s, limit)


def intent_of(sections):
    """The bill's statement of intent or purpose: the sentence(s) saying it, from the start of the bill."""
    found = []
    for sec in sections[:4]:
        if sec.get("new") is False:
            continue  # (an amended section's "The purpose of this section is ..." is the law as it stands)
        for p in sec["paras"]:
            ss = sentences(unnumber(p))
            for j, s in enumerate(ss):
                m = INTENT.search(s)
                if m and m.start() < 120:
                    s = LEADIN.sub("", s)
                    s = s[0].upper() + s[1:]
                    # A short one that points elsewhere ("The legislature therefore intends to close this gap.") takes
                    # the sentence after it, which says how.
                    if len(s) < 80 and j + 1 < len(ss) and len(s) + len(ss[j + 1]) < MAX_INTENT:
                        s += " " + ss[j + 1]
                    if len(s) <= MAX_SENTENCE * 1.3:
                        found.append(s)
        if found:
            break
    if found:
        out = found[0]
        if len(found) > 1 and len(out) + len(found[1]) < MAX_INTENT:
            out += " " + found[1]
        return out, sections.index(sec)
    # A findings section's concluding sentence, when it draws the conclusion ("Therefore, ...").
    for k, sec in enumerate(sections[:2]):
        if sec["paras"] and FINDINGS.match(unnumber(sec["paras"][0])) and sec.get("new") is not False:
            last = sentences(unnumber(sec["paras"][-1]))[-1] if sec["paras"][-1].strip() else ""
            if LEADIN.match(last) and len(last) < MAX_SENTENCE:
                s = LEADIN.sub("", last)
                return s[0].upper() + s[1:], k
    return "", None


def findings_only(sec):
    return bool(sec["paras"]) and bool(FINDINGS.match(unnumber(sec["paras"][0])))


# What makes a sentence operative: a bill's first section without one only describes the problem ("Throughout
# Washington state, there is a growing need ..."), and an added stretch without a verb is a list item ("Other
# particularly serious violations of fundamental ethical norms.").
MODAL = re.compile(r"\b(?:shall|must|may not|this (?:act|section|chapter|subsection)|cause of action|(?:is|are) (?:hereby )?"
                   r"(?:established|created|prohibited|required|authorized|guilty|exempt|liable|entitled|subject))\b", re.I)
OPERATIVE = re.compile(r"\b(?:shall|must|may|is|are|has|have|will|does|do|means|includes?|applies|apply|constitutes?)\b", re.I)


def lead(sections):
    """{"intent", "bullets", "added", "amends"} from a bill's sections, or None when there's nothing to say."""
    intent, at = intent_of(sections)
    bullets, seen = [], set()
    for k, sec in enumerate(sections):
        if k == at or sec.get("new") is False or sec.get("repeal") or not sec["paras"]:
            continue
        paras = [tidy(p) for p in sec["paras"] if p.strip()]
        while paras and (CODIFY_HEAD.match(paras[0]) or not unnumber(decaption(paras[0])).strip()):
            paras = paras[1:]  # the instruction ("A new section is added to chapter 46.92 RCW to read as follows:"), a heading
        if not paras or findings_only({"paras": paras}):
            continue
        body = unnumber(decaption(paras[0]))
        ss = sentences(body)
        if k == 0 and len(paras) == len(sec["paras"]) and len(ss) >= 3 and not MODAL.search(" ".join(ss[:2])):
            continue  # a first section that only describes the problem
        if not body or BOILER.match(body) or INTENT.search(body[:150]):
            continue
        s = opening([body] + paras[1:])
        if (not s or len(s) < 25 or len(re.findall(r"[a-z]", s)) < 0.5 * len(s) or not s[0].isupper()
                or len(s.split()) < 6 or not OPERATIVE.search(s if not s.endswith("…") else s + " " + " ".join(paras[:3]))):
            continue  # (nothing, a list of statute numbers, a heading or a list item: "Write-in or sticker candidate.")
        key = re.sub(r"\W+", " ", s.lower())[:80]
        if key in seen:
            continue
        seen.add(key)
        bullets.append(s)
        if len(bullets) == MAX_BULLETS:
            break
    added, amends = [], []
    if not bullets:
        for sec in sections:
            if sec.get("cite") and sec["cite"] not in amends:
                amends.append(sec["cite"])
            for a in sec.get("added", []):
                a = unnumber(a)
                one = cut(sentences(a)[0]) if a else ""
                key = re.sub(r"\W+", " ", one.lower())[:80]
                if (len(a) >= 60 and not BOILER.match(a) and a[0].isupper() and OPERATIVE.search(one) and key not in seen
                        and len(added) < 3):
                    seen.add(key)
                    added.append(one)
    if not (intent or bullets or added or amends):
        return None
    return {"intent": intent, "bullets": bullets, "added": added, "amends": amends}


def join_cites(cites):
    """["RCW 19.27.031", "RCW 43.21C.035"] -> "RCW 19.27.031 and 43.21C.035"."""
    groups = {}
    for c in cites:
        m = re.match(r"^(.*?)\s*([\d][\w.:-]*)$", c)
        pre, n = (m.group(1), m.group(2)) if m else ("", c)
        groups.setdefault(pre, []).append(n)
    parts = []
    for pre, ns in groups.items():
        if len(ns) > 6:
            ns = ns[:5] + [f"{len(ns) - 5} more"]
        lst = ns[0] if len(ns) == 1 else ", ".join(ns[:-1]) + " and " + ns[-1]
        parts.append(f"{pre} {lst}".strip())
    return "; ".join(parts)


def statement(found, version="as introduced", shown=""):
    """(text, label) for a texts_<session>.json entry, or ("", "") when the lead says nothing. shown: what the page
    already shows (title and summary); "Amends ..." is left out when it names the same sections (Mississippi's long
    titles: "AN ACT TO AMEND SECTION 99-19-71, MISSISSIPPI CODE OF 1972, ...")."""
    if not found:
        return "", ""
    nums = [re.sub(r"^.*?(\d)", r"\1", c) for c in found["amends"]]
    if shown and nums and all(n in shown for n in nums):
        found = {**found, "amends": []}
    lines, what = [], []
    if found["intent"]:
        lines.append(found["intent"])
        what.append("its statement of intent")
    if found["bullets"]:
        lines += [f"• {b}" for b in found["bullets"]]
        what.append("the opening of its new sections" if len(found["bullets"]) > 1 else "the opening of its new section")
    elif found["added"]:
        lines += [f"• {b}" for b in found["added"]]
        what.append("the changes it makes to existing law")
    if not found["bullets"] and found["amends"]:
        lines.append(f"Amends {join_cites(found['amends'])}.")
        if not found["added"]:
            what.append("the laws it amends")
    # Keep the whole under MAX_TOTAL: drop list items from the end.
    while len("\n".join(lines)) > MAX_TOTAL and sum(l.startswith("• ") for l in lines) > 1:
        k = max(i for i, l in enumerate(lines) if l.startswith("• "))
        lines.pop(k)
    text = "\n".join(lines)
    if not what:
        return "", ""
    said = what[0] if len(what) == 1 else ", ".join(what[:-1]) + " and " + what[-1]
    return text, f"From the bill's text{' ' + version if version else ''}: {said}."


def compact(sections, paras=6, chars=1000):
    """Sections cut to what lead() can use, for a state's cache: the first paragraphs of each (an amended section's
    first only: lead() reads its added sentences), the first added sentences."""
    # (The first sections keep more: a findings section's intent sentence is often its last paragraph.)
    return [{**s, "paras": [p[:chars] for p in s["paras"][:1 if s.get("new") is False else 16 if k < 4 else paras]],
             "added": [a[:chars] for a in s.get("added", [])[:4]]} for k, s in enumerate(sections[:40])]


STOP = {"the", "and", "for", "this", "bill", "act", "that", "with", "relating", "concerning", "regarding", "an", "to", "of",
        "in", "on", "a", "by", "or", "amends", "amending", "rcw", "section", "sections"}


def words(t):
    return set(re.findall(r"[a-z]{3,}", (t or "").lower())) - STOP


def problems(text, title):
    """What's wrong with a lead, for the data checks: [] when nothing is."""
    out = []
    if len(text) > MAX_TOTAL:
        out.append("too long")
    lines = [l[2:] if l.startswith("• ") else l for l in text.split("\n") if l.strip()]
    if lines and all(BOILER.match(unnumber(l)) for l in lines):
        out.append("boilerplate")
    body = [l for l in lines if not l.startswith("Amends ")]
    if body and words(" ".join(body)) <= words(title):
        out.append("repeats the title")
    return out


# Reading a bill's text. Most legislatures' text pages mark new wording in an amended section by underlining it and
# deleted wording by striking it through; `paragraphs()` keeps each paragraph as (text, underlined) runs with struck
# wording left out, and `split()` cuts them into sections at their "SECTION 1." marks.
class _Runs(HTMLParser):
    BREAK = {"p", "div", "br", "li", "tr", "h1", "h2", "h3", "h4", "h5", "h6", "table", "pre"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.paras, self.runs, self.stack, self.skip = [], [], [], 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "head", "title"):
            self.skip += 1
        if tag in self.BREAK:
            self.flush()
        style = (dict(attrs).get("style") or "").replace(" ", "").lower()
        if tag in ("u", "ins") or "underline" in style:
            self.stack.append((tag, "u"))
        elif tag in ("s", "strike", "del") or "line-through" in style:
            self.stack.append((tag, "x"))
        elif tag in ("span", "font", "b", "i", "em", "strong", "a"):
            self.stack.append((tag, ""))

    def handle_endtag(self, tag):
        if tag in ("script", "style", "head", "title"):
            self.skip = max(0, self.skip - 1)
        if tag in self.BREAK:
            self.flush()
        for k in range(len(self.stack) - 1, -1, -1):
            if self.stack[k][0] == tag:
                del self.stack[k:]
                break

    def handle_data(self, data):
        if self.skip or any(m == "x" for _, m in self.stack):
            return
        self.runs.append((data, any(m == "u" for _, m in self.stack)))

    def flush(self):
        if self.runs and "".join(t for t, _ in self.runs).strip():
            self.paras.append(self.runs)
        self.runs = []


def paragraphs(page):
    """A text page's paragraphs, each a list of (text, underlined) runs; struck-through wording left out."""
    r = _Runs()
    r.feed(page)
    r.flush()
    return r.paras


def text_of(runs):
    return clean("".join(t for t, _ in runs).replace("\xa0", " "))


MARK = re.compile(r"^\s*\*?\s*(?:SECTION|Section|SEC\.|Sec\.)\s+(\d+[A-Za-z]?(?:\.\d+)?)\.(?!\d)\s*")
NEW = re.compile(r"\b(?:(?:is|are) (?:hereby )?(?:further )?amended,? by (?:adding|inserting|the addition of)\b(?!.{0,60}\b(?:words?|"
                 r"definitions?|sentences?|clauses?)\b)|new (?:sections?|chapters?|articles?|subsections?|parts?) (?:is|are) "
                 r"(?:hereby )?(?:added|created|enacted)|(?:shall|will) be codified as|(?:is|are) (?:hereby )?(?:created|enacted) to read)", re.I)
AMEND = re.compile(r"\b(?:is|are) (?:hereby )?(?:further |each )?(?:amended|reenacted|revised|brought forward)\b", re.I)
REPEAL = re.compile(r"\b(?:is|are) (?:hereby )?(?:each )?repealed\b", re.I)
# Where the instruction ends and the text begins: "... to read as follows:", "... as follows:", MA's ":-".
INSTRUCTION = re.compile(r"^(.{0,600}?(?:to read(?: as follows)?|as follows|the following[^:]{0,80}?|to read in full)\s*:-?|.{0,600}?:-)\s*(.*)$", re.S)


def split(paras, cite=None, mark=MARK):
    """Sections from paragraphs (lists of runs) at their section marks. cite(head) names what an amended section amends
    ("Section 9-5-13, Mississippi Code of 1972, is amended" -> "Section 9-5-13"), or None. The text before the first mark
    (the title, the enacting clause) is left out."""
    out, cur = [], None
    for runs in paras:
        t = text_of(runs)
        m = mark.match(t)
        if m:
            # (The rest of the mark's paragraph is the section's first paragraph.)
            # An underlined mark is a new section (Mississippi's "<u>SECTION 1.</u>").
            cur = {"num": m.group(1), "runs": [[(t[m.end():], False)]], "u": next((u for x, u in runs if x.strip()), False)}
            out.append(cur)
        elif cur is not None:
            cur["runs"].append(runs)
    secs = []
    for c in out:
        first = text_of(c["runs"][0])
        instr = NEW.search(first[:400]) or AMEND.search(first[:400])
        m = INSTRUCTION.match(first) if instr else None
        head, rest = (m.group(1), m.group(2)) if m else ((first, "") if instr else ("", first))
        kind = ("repeal" if REPEAL.search(first[:300]) and not m else "new" if head and NEW.search(head) else
                "amend" if head and AMEND.search(head) else "new" if c["u"] else None)
        paras = ([rest] if rest.strip() else []) + [text_of(r) for r in c["runs"][1:]]
        sec = {"num": c["num"], "new": {"new": True, "amend": False, "repeal": False}.get(kind),
               "paras": [p for p in paras if p], "added": [], "cite": "", "repeal": kind == "repeal"}
        if kind == "amend":
            # (Mississippi "brings forward" sections it doesn't change, so they can be amended later.)
            sec["cite"] = (cite(head) if cite and not re.search(r"brought forward", head, re.I) else "") or ""
            for runs in c["runs"][1:]:
                sec["added"] += underlined(runs)
            if not sec["added"] and re.search(r"(?:inserting|substituting|replac|in place thereof)", head, re.I):
                # MA: "... striking out ... and inserting in place thereof the following paragraph:- <new wording>"
                sec["added"] = [p for p in sec["paras"] if p.endswith(".")]
            if not sec["added"] and not m and len(head) < 350 and head.endswith(".") and re.search(r"[“\"][^”\"]{2,}[”\"]", head):
                # An instruction that says the whole change: "... is hereby amended by striking out “Thanksgiving day” in line 22."
                sec["added"] = [head]
        secs.append(sec)
    return secs


def underlined(runs):
    """The whole sentences an amendment adds in one paragraph: its underlined stretches that end a sentence."""
    out, cur = [], ""
    for t, u in runs + [("|", False)]:
        if u or not t.strip():
            cur += t
            continue
        s = clean(cur)
        if s.endswith(".") and len(s) >= 60:
            out.append(s)
        cur = ""
    return out


CATCHLINE = re.compile(r"^(?:(?:Article|ARTICLE|Chapter|CHAPTER|Part|PART) [\dIVXLC]+[A-Z]?\.?\s+[^.]{2,100}\.\s*|"
                       r"(?:Sec\.|Section|§)\s*\d+[\w:-]*(?:\.\d+[\w:-]*)+\.?\s+(?:[A-Z][^.]{1,120}\.\s+)?|"
                       r"(?:(?:Section|§)\s*)?\d+-\d+-[\d.]+\.\s+(?:[A-Z][^.]{1,120}\.(?:\s+|$))?|[A-Z][A-Z ,'&;:/-]{3,90}\.(?:\s+|(?=[A-Z(“\"])|$))(?=\S|$)")


def decaption(t):
    """A new section's text without its statute number and catchline ("Sec. 14.33.300. Wireless telecommunications
    device policy. (a) The department ..." -> "(a) The department ...") or an uncodified section's capitals heading
    ("SHORT TITLE. This Act ...")."""
    for _ in range(3):
        u = CATCHLINE.sub("", t, count=1)
        if u == t:
            break
        t = u
    return t
