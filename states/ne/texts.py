#!/usr/bin/env python3
""""What it does" for Nebraska: data/ne/texts_<first year>.json, {"LB7": {"statement": ..., "label": ..., "committee":
[name, "YYYY-MM-DD", text]}}, from the documents states/ne/fetch.py saves as text (pdftotext -raw) in
data/ne/<year>/docs/ (CS-LB7.txt, SI-LB7.txt).

Two documents describe a bill:
- The committee statement (/FloorDocs/109/PDF/CS/LB7.pdf), written by the committee's staff when the committee advances
  the bill to General File (about 40% of bills): a header (hearing date, committee, introducer, one-liner), the committee's
  vote and the hearing's testifiers (left out), then "Summary of purpose and/or changes:" (what the bill does, neutral),
  often "Section-by-section" (left out: statute by statute), and "Explanation of amendments:" (what the committee's
  amendment changed; for a big amendment, each bill it folded in, with that bill's testifiers and vote, left out), signed
  by the chair. This is used when there is one: the summary as the statement, the amendments' explanation as what the
  committee changed ("As the Agriculture Committee approved it"). When the amendment replaced the bill ("becomes the
  bill", "white copy"), the explanation is the statement.
- The introducer's statement of intent (/FloorDocs/109/PDF/SI/LB7.pdf), filed for the hearing on nearly every bill: one
  or a few paragraphs after "the purposes which are sought to be accomplished thereby:". The introducer's own account
  (it can argue for the bill), so used only when there's no committee statement, labelled as the introducer's.
A bills (LB 304A, an appropriation for LB 304) are left out: the page keys texts by number without a final letter.
Usage: python3 states/ne/texts.py [first year ...]   (default: every downloaded Legislature)
"""
import json, os, re, sys

DATA = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "ne"))
MAX = 2500  # characters of a statement (and of the committee's changes), cut at a paragraph or sentence

# Lines that start a list item, a new paragraph.
ITEM = re.compile(r"^(Secs?\.?\s*\d|Sections?\s+\d|SECTION\s+\d|--|–|—|•|•|\(\w{1,4}\)\s|\d{1,2}[.)]\s|"
                  r"L[BR] ?\d+\w*\s*(\(|:|–|-\s))")
# Lists of people (testifiers, committee votes on bills folded in) inside the statement's text: left out.
SKIP_START = re.compile(r"^(Testifiers on|Testimony:|Proponents:|Opponents:|Neutral:|Committee vote|Motion to (Include|"
                        r"attach|amend)|Voting (Result|Aye|Nay|Absent)|Vote Results?:|(Yes|No|Aye|Nay|Absent|Present Not "
                        r"Voting):)", re.I)
SKIP_LINE = re.compile(r"(vote of the committee|with the following testimony|testifiers?)\s*:?\s*$", re.I)
SKIP_END = re.compile(r"^(L[BR] ?\d+|AM ?\d+|The |This |It |Section |Sec\.|In addition|Additionally|Finally|Also|"
                      r"(Adds|Amends|Changes|Strikes|Provides|Clarifies|Creates|Requires|Removes|Allows|Specifies|"
                      r"Eliminates|Inserts|Harmonizes|Appropriates|Establishes|Updates|Prohibits|Authorizes)\b)")
ABBREV = re.compile(r"(\b(Neb|Rev|Stat|Stats|Sec|Secs|No|Nos|U\.S|St|Mr|Mrs|Ms|Dr|Sen|Inc|Co|Corp|Jr|Sr|vs|v|"
                    r"approx|e\.g|i\.e|etc|Art|Ch)|\b[A-Z])\.$")


def furniture(lines):
    """Lines without the page furniture: the running footer ("Committee Statement: LB7", "Agriculture Committee",
    "Page 1"), the document hash, page numbers ("- 1 -"), the statement of intent's repeated heading."""
    out, skip = [], 0
    for i, ln in enumerate(lines):
        s = ln.strip()
        if skip:
            skip -= 1
            continue
        if re.fullmatch(r"Committee Statement: L[BR]\d+\w*", s):
            # then the committee's name and "Page N"
            skip = sum(1 for x in lines[i + 1:i + 3] if x.strip().endswith("Committee") or re.fullmatch(r"Page \d+", x.strip()))
            continue
        if re.fullmatch(r"[0-9a-f]{32}|Page \d+|-\s*\d+\s*-|\d+", s) or not s:
            continue  # (blank lines are only page breaks here: pdftotext -raw writes none between paragraphs)
        out.append(s)
    return out


def paragraphs(lines):
    """Wrapped lines -> paragraphs: a paragraph ends at a blank line, before a list item, after a short line that ends
    a sentence, or before a capital after a very short line (a heading, or a sentence ending in a quote). A line ending in a hyphen joins the next without a space (Word documents aren't hyphenated:
    "high-" + "quality" is "high-quality")."""
    lines = [ln.replace("�", "").replace("­", "").replace(" ", " ").rstrip() for ln in lines]
    width = max([len(ln) for ln in lines if ln] + [1])
    paras, cur = [], ""
    for i, ln in enumerate(lines):
        if not ln.strip():
            if cur:
                paras.append(cur)
            cur = ""
            continue
        short = i and len(lines[i - 1]) < 0.6 * width and not re.search(r"[,;(\-/]$", lines[i - 1])
        if cur and (ITEM.match(ln) or short and ln[:1].isupper()) and not re.fullmatch(r"\(\w{1,4}\)", cur.strip()):
            paras.append(cur)
            cur = ""
        cur = cur + ln if (not cur or cur.endswith("-") or cur.endswith("/")) else cur + " " + ln
        if len(ln) < 0.8 * width and re.search(r"[.:;?!][\"”’)]?$", ln):
            paras.append(cur)
            cur = ""
    if cur:
        paras.append(cur)
    return [re.sub(r"\s+", " ", p).strip() for p in paras if p.strip()]


def sentences_cut(p, limit):
    """p cut at the last sentence end before limit (never inside "Neb. Rev. Stat."), or "" when there's none."""
    best = ""
    for m in re.finditer(r"[.!?][\"”’)]?(?=\s|$)", p[:limit + 1]):
        if not ABBREV.search(p[:m.start() + 1]):
            best = p[:m.end()]
    return best


def cut(paras, limit=MAX):
    """Whole paragraphs up to limit characters (a first paragraph longer than that cut at a sentence); a last
    paragraph that introduces a list that didn't fit ("as follows:"), or a heading, is dropped."""
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
    while out and (out[-1].endswith(":") or len(out[-1]) < 40 and not re.search(r"[.!?][\"”’)]?$", out[-1])):
        out.pop()  # an introduction to a list, or a heading, that nothing follows
    return out


def drop_lists(lines):
    """Leave out the testifier lists and committee votes inside a statement (a big amendment explains each bill it
    folded in, each with its own)."""
    out, skipping = [], False
    for ln in lines:
        if SKIP_START.match(ln) or SKIP_LINE.search(ln):
            skipping = True
            continue
        if skipping:
            if not ln or not SKIP_END.match(ln) or re.match(r"^L[BR] ?\d+\w*\s*,", ln):
                continue
            skipping = False
        out.append(ln)
    return out


def committee_statement(raw):
    """A committee statement's text -> {"committee": "Agriculture Committee", "summary": [paragraphs], "changes":
    [paragraphs], "replaced": the amendment replaced the bill}."""
    lines = raw.replace("\f", "\n").split("\n")
    comm = next((re.sub(r"^Committee On:\s*", "", ln).strip() for ln in lines if ln.startswith("Committee On:")), "")
    start = next((i for i, ln in enumerate(lines) if re.match(r"\s*Summary of purpose", ln, re.I)), None)
    if start is None:
        return None
    body = furniture(lines[start + 1:])
    end = next((i for i, ln in enumerate(body) if re.search(r",\s*(Vice )?Chair(person|man|woman)?$", ln)), len(body))
    body = drop_lists(body[:end])
    amend = next((i for i, ln in enumerate(body) if re.match(r"Explanation of amendments?", ln, re.I)), len(body))
    summary, changes = body[:amend], body[amend + 1:]
    if changes and re.sub(r"^Explanation of amendments?:?\s*", "", body[amend], flags=re.I):
        changes.insert(0, re.sub(r"^Explanation of amendments?:?\s*", "", body[amend], flags=re.I))
    # The section-by-section part of the summary is left out (statute by statute); kept only when it's all there is.
    sbs = next((i for i, ln in enumerate(summary) if re.match(r"(section[- ]by[- ]section|SECTION BY SECTION)", ln, re.I)),
               None)
    if sbs is None:
        sbs = next((i for i, ln in enumerate(summary)
                    if re.match(r"(Secs?\.?\s*1\b|Section 1\b|SECTION 1\b|Section One\b)", ln)), None)
    summary = [ln for ln in summary if ln.strip() not in ("SUMMARY", "Summary:", "Summary")]
    if sbs is not None:
        sbs = min(sbs, len(summary))
        head = paragraphs(summary[:sbs])
        summary = head if head and sum(map(len, head)) > 60 else paragraphs(summary)
    else:
        summary = paragraphs(summary)
    changes = paragraphs(changes)
    if changes and re.fullmatch(r"(none|n/?a|no amendments?\.?)\.?", changes[0], re.I):
        changes = []
    whole = " ".join(changes[:2])
    replaced = bool(re.search(r"becomes the bill|white[- ]copy|strikes? (all |the )?original sections|strikes and "
                              r"replaces|replaces the (original )?bill|no provision of .{0,12} remains", whole, re.I))
    return {"committee": comm + (" Committee" if comm and not comm.endswith(("Committee", "Board")) else ""),
            "summary": cut(summary), "changes": cut(changes), "replaced": replaced}


def statement_of_intent(raw):
    """A statement of intent's text -> paragraphs (between "accomplished thereby:" and the introducer's signature)."""
    lines = raw.replace("\f", "\n").split("\n")
    start = next((i for i, ln in enumerate(lines) if re.search(r"accomplished\s+thereby:?\s*$", ln)), None)
    if start is None:
        start = next((i for i, ln in enumerate(lines) if re.search(r"Date of Hearing", ln, re.I)), None)
    if start is None:
        return []
    body = []
    for ln in lines[start + 1:]:
        if re.match(r"\s*Principal Introducer", ln):
            break
        if re.match(r"\s*(One Hundred \w+ Legislature|Introducer's Statement of Intent|L[BR]\d+\w*$)", ln, re.I):
            continue
        body.append(ln)
    return cut(paragraphs(furniture(body)))


def placed_on(year, key):
    """The day the committee last advanced the bill ("Placed on General File"), from its page, or ""."""
    try:
        s = open(os.path.join(DATA, str(year), "bills", f"{key}.html"), encoding="utf-8").read()
    except OSError:
        return ""
    from datetime import datetime
    days = [datetime.strptime(d, "%b %d, %Y").date().isoformat()
            for d in re.findall(r'<td class="py-1">([A-Z][a-z]{2} \d\d, \d{4})</td>\s*<td class="py-1">Placed on General File', s)]
    return max(days, default="")


def read(path):
    try:
        return open(path, encoding="utf-8").read()
    except OSError:
        return None


def text_of(year, key):
    """One bill's entry for the texts file, or None."""
    docs = os.path.join(DATA, str(year), "docs")
    cs = read(os.path.join(docs, f"CS-{key}.txt"))
    c = committee_statement(cs) if cs else None
    if c and (c["summary"] or c["changes"]):
        who = c["committee"] or "committee"
        if c["replaced"] and c["changes"] or not c["summary"]:
            return {"statement": "\n".join(c["changes"]),
                    "label": f"From the {who}'s statement, on the amendment it adopted"
                             + (" in place of the bill as introduced." if c["replaced"] else ".")}
        out = {"statement": "\n".join(c["summary"]), "label": f"From the {who}'s statement."}
        if c["changes"]:
            out["committee"] = [who, placed_on(year, key), "\n".join(c["changes"])]
        return out
    si = read(os.path.join(docs, f"SI-{key}.txt"))
    paras = statement_of_intent(si) if si else []
    if paras:
        return {"statement": "\n".join(paras), "label": "From the introducer's statement of intent."}
    return None


def write(year):
    """data/ne/texts_<year>.json from the saved documents; returns how many bills have a text."""
    docs = os.path.join(DATA, str(year), "docs")
    if not os.path.isdir(docs):
        return 0
    keys = sorted({f[3:-4] for f in os.listdir(docs) if f.endswith(".txt")},
                  key=lambda k: (k[:2], int(re.sub(r"\D", "", k) or 0), k))
    out = {}
    for key in keys:
        if re.fullmatch(r"LB\d+A", key):
            continue
        t = text_of(year, key)
        if t:
            out[key] = t
    path = os.path.join(DATA, f"texts_{year}.json")
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=0)
    os.replace(tmp, path)
    cs = sum(1 for v in out.values() if v["label"] != "From the introducer's statement of intent.")
    print(f"texts_{year}.json: {len(out)} bills ({cs} from committee statements, {len(out) - cs} from statements of "
          f"intent)", flush=True)
    return len(out)


if __name__ == "__main__":
    yrs = [int(a) for a in sys.argv[1:]] or sorted(int(f) for f in os.listdir(DATA) if re.fullmatch(r"\d{4}", f))
    for y in yrs:
        write(y)
