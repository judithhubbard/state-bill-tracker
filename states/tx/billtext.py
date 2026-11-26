#!/usr/bin/env python3
""""What it does" for Texas bills with no bill analysis: a lead quoted from the bill's own text (states/billtext_lead.py).

A bill analysis is written only when a committee reports a bill, so about two thirds of a session's bills have none.
For those, this reads the bill as introduced from the Legislature's FTP site (the history XML's billtext/docTypes/bill
version "Introduced", e.g. /bills/89R/billtext/HTML/house_bills/HB00001_HB00099/HB00010I.HTM). The page is a table
with one row per printed line: a line indented with spaces begins a paragraph, centered lines are headings. "SECTION 2."
marks the bill's sections; in a new chapter or section ("is amended by adding Chapter 465 to read as follows:") the
code's own "Sec. 465.0051." sections are underlined (all new wording is), and each counts as a section of new law. An
amended code section ("Section 2001.0045, Government Code, is amended to read as follows:") keeps its "Sec." heading
plain, so only its underlined whole sentences count.

The sections are kept in data/tx/<code>/leads.json by bill, with the text's address (a version is read once, ever); the
lead is worked out from them each run, so a change to its rules needs no download. At most `minutes` a run, four files
at a time; laws first, then bills that passed a house, then the latest acted on. texts.py puts the leads in
texts_<session>.json for bills with no analysis.
Usage: python3 states/tx/billtext.py [session] [minutes]
"""
import json, os, re, sys, time
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
from states import billtext_lead as L
from states.tx import profile as P
from states.tx.convert import folder, num, iso

# The bill's own sections ("SECTION 2.") and, once marked new below, a new code section ("Sec. 465.0051.", "Art. 42A.5025.").
MARK = re.compile(r"^\s*(?:SECTION|SECTIONS?)\s+(\d+[A-Za-z]?(?:\.\d+)*)\.(?!\d)\s*")
CODE_SEC = re.compile(r"^\s*(?:Sec\.|Art\.)\s*(\d+[A-Za-z]*(?:\.\d+[A-Za-z]*)*)\.(?!\d)")
CELL = re.compile(r'<td width="615"([^>]*)>(.*?)</td>', re.S | re.I)


def paras(page):
    """The text's paragraphs, each a list of (text, underlined) runs (billtext_lead.paragraphs())."""
    out, cur = [], []
    for attrs, c in CELL.findall(page):
        centered = 'align="center"' in attrs.lower()
        starts = centered or re.match(r"\s*(?:&#xA0;|&nbsp;|\xa0){3}", c)
        if starts and cur:
            out.append(" ".join(cur))
            cur = []
        cur.append(c.strip())
        if centered:
            out.append(" ".join(cur))
            cur = []
    if cur:
        out.append(" ".join(cur))
    ps = L.paragraphs("".join(f"<p>{p}</p>" for p in out))
    # A new code section is underlined from its heading on: mark it as its own section of the bill. ("SECTION " keeps its
    # number; split() reads an underlined mark as new law.)
    marked = []
    for runs in ps:
        t = L.text_of(runs)
        first = next((u for x, u in runs if x.strip()), False)
        m = CODE_SEC.match(t)
        if m and first:
            runs = [("SECTION " + m.group(1) + "." + t[m.end():], True)]  # (all of it is new: one run is enough)
        marked.append(runs)
    return marked


def cite(head):
    """"Section 21.201, Education Code, is amended" -> "Education Code § 21.201"; "Article 42.01, Code of Criminal
    Procedure" -> "Code of Criminal Procedure art. 42.01"."""
    m = re.search(r"\b(Section|Article)s? (\d+[A-Z]?\.[\dA-Z]+)[^,;]{0,40},\s*((?:[A-Z][a-z]+ )+Code|Code of Criminal Procedure)", head)
    if not m:
        return ""
    return f"{m.group(3)} {'§' if m.group(1) == 'Section' else 'art.'} {m.group(2)}"


def sections(page):
    return L.compact(L.split(paras(page), cite, MARK))


def wanted(session, have):
    """Bills with no analysis (not in `have`) -> the introduced text's address, laws first, then bills that passed a
    house, then the latest acted on."""
    out = []
    for f in os.listdir(folder(session)):
        b = num(f)
        if not b or b in have:
            continue
        try:
            t = ET.parse(os.path.join(folder(session), f)).getroot()
        except ET.ParseError:
            continue
        url = ""
        for v in t.iter("version"):
            if (v.findtext("versionDescription") or "").strip() == "Introduced" and v.findtext("FTPHTMLURL") and \
                    "/billtext/" in (v.findtext("FTPHTMLURL") or ""):
                url = v.findtext("FTPHTMLURL")
                break
        if not url:
            continue
        acts = " ".join((a.findtext("description") or "") for a in t.iter("action"))
        rank = 2 if re.search(r"Effective|Signed by the Governor|without the Governor's signature", acts) else \
            1 if re.search(r"Received from the (?:House|Senate)|Reported engrossed|Passed", acts) else 0
        out.append((rank, iso((t.findtext("lastaction") or "")[:10]), b, url))
    return [(b, url) for _, _, b, url in sorted(out, reverse=True)]


def path(session):
    return os.path.join(P.DATA, P.code_of(session), "leads.json")


def load(session):
    try:
        return json.load(open(path(session)))
    except (OSError, ValueError):
        return {}


def save(session, cache):
    tmp = path(session) + ".tmp"
    json.dump(cache, open(tmp, "w"), ensure_ascii=False)
    os.replace(tmp, path(session))


def main(session, have, minutes=8):
    """Reads the introduced texts of bills with no analysis, at most `minutes` a run. Returns how many are left."""
    from states.tx.texts import get
    until = time.time() + 60 * minutes
    cache = load(session)
    todo = [(b, u) for b, u in wanted(session, have) if cache.get(b, {}).get("url") != u]
    read = 0
    with ThreadPoolExecutor(4) as pool:
        for i in range(0, len(todo), 40):
            if time.time() > until:
                break
            batch = todo[i:i + 40]
            for (b, u), page in zip(batch, pool.map(lambda x: get(x[1]), batch)):
                if page:
                    cache[b] = {"url": u, "sections": sections(page)}
                    read += 1
            save(session, cache)
    save(session, cache)
    left = len(todo) - read
    print(f"{P.code_of(session)} leads.json: {len(cache)} bill texts ({read} read now, {left} left)", flush=True)
    return left


def entries(session):
    """Bill -> {"statement", "label"} for texts_<session>.json, from the texts read so far."""
    out = {}
    for b, v in load(session).items():
        text, label = L.statement(L.lead(v["sections"]))
        if text:
            out[b] = {"statement": text, "label": label}
    return out


if __name__ == "__main__":
    from states.tx import texts
    s = int(sys.argv[1]) if len(sys.argv) > 1 else P.session_of(time.localtime().tm_year)
    main(s, texts.analysed(s), float(sys.argv[2]) if len(sys.argv) > 2 else 8)
