#!/usr/bin/env python3
""""What it does" for Minnesota bills with no House Research or Senate summary: a lead quoted from the bill's own text
(states/billtext_lead.py).

The nonpartisan staff summarize a bill once a committee takes it up, so about half of a Legislature's bills (a House
file and its Senate companion counted once) have no summary. For those, this reads the bill as introduced, the Revisor's
page for its first version (the status record's TEXT_VERSION_LIST, engrossment 0:
https://www.revisor.mn.gov/bills/94/2025/0/HF/10/versions/0/; robots.txt allows /bills/ pages, read through fetch.py's
`request()`, which checks it and waits a second between requests). Each section is a `div.bill_section`: "newstatute"
is new law ("[16A.1393] STATE-FUNDED SERVICES ..."), an amended one says "Minnesota Statutes 2024, section 136A.1465,
subdivision 1, is amended to read:" and marks new wording `<ins>` and deleted wording `<del>`, so only its new whole
sentences count. Headings, subdivision numbers, effective dates and the screen-reader words ("new text begin") are
left out.

The sections are kept in data/mn/<first year>/leads.json by bill, with the version's address (read once, ever); the
lead is worked out from them each time convert.py builds the session, so a change to its rules needs no download. At
most `minutes` a run: laws first, then bills that passed a house, then the latest acted on; one number per companion
pair (the House file, or the one that went further).
Usage: python3 states/mn/billtext.py [first year] [minutes]
"""
import json, os, re, sys, time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
from states import billtext_lead as L
from states.mn import profile as P

DROP = [
    re.compile(r'<span class="sr-only">.*?</span>', re.S),
    re.compile(r'<div class="sec_eff_date">.*?</div>', re.S),  # (no divs inside it)
    re.compile(r'<h1 class="shn">.*?</h1>', re.S),  # a new section's heading
    re.compile(r'<h3 class="headnote">.*?</h3>', re.S),
    re.compile(r'<h2 class="subd_no">.*?</h2>', re.S),
    re.compile(r'<var class="ln">.*?</var>', re.S),
    re.compile(r'<span id="pl\.[\d.]+" class="pl">\s*</span>'),  # (line numbers' anchors)
]


def cite(head):
    """"Minnesota Statutes 2024, section 136A.1465, subdivision 1, is amended" -> "Minn. Stat. § 136A.1465"."""
    m = re.search(r"Minnesota Statutes(?: \d{4})?,? sections? (\d+[A-Z]?\.\d+\w*)", head)
    return f"Minn. Stat. § {m.group(1)}" if m else ""


def sections(page):
    """The bill's sections (billtext_lead's Section dicts) from the Revisor's page."""
    m = re.search(r'<div id="document"', page)
    body = page[m.start():] if m else page
    end = body.find("<footer")
    body = body[:end] if end > 0 else body  # (the site's footer: "About the Legislature", ...)
    for r in DROP:
        body = r.sub("", body)
    body = re.sub(r"<br[^>]*>", " ", body)  # (the printed lines' ends, inside paragraphs)
    # A new statute's section: its number marked as new wording, so split() reads it as new law.
    body = re.sub(r'(<div class="bill_section newstatute"[^>]*>\s*<h2 class="section_number">)(.*?)(</h2>)',
                  r"\1<u>\2</u>\3", body, flags=re.S)
    paras, pending = [], None
    for runs in L.paragraphs(body):
        t = L.text_of(runs)
        if L.MARK.fullmatch(t.strip() + " ") or re.fullmatch(r"(?:Section|Sec\.)\s+\d+[A-Z]?\.", t.strip()):
            pending = [(t.strip() + " ", next((u for x, u in runs if x.strip()), False))]
            continue  # (the number is its own heading: joined to the section's first paragraph)
        if pending:
            runs = pending + runs
            pending = None
        paras.append(runs)
    return L.compact(L.split(paras, cite))


def path(session):
    return os.path.join(P.DATA, str(session), "leads.json")


def load(session):
    try:
        return json.load(open(path(session)))
    except (OSError, ValueError):
        return {}


def save(session, cache):
    tmp = path(session) + ".tmp"
    json.dump(cache, open(tmp, "w"), ensure_ascii=False)
    os.replace(tmp, path(session))


def first_version(rec):
    vs = rec.get("TEXT_VERSION_LIST") or []
    vs = vs if isinstance(vs, list) else [vs]
    v = next((v for v in vs if str(v.get("DOCUMENT_ENGROSSMENT")) == "0" and v.get("HTML_URI")), None)
    return v["HTML_URI"] if v else ""


def wanted(session):
    """[(bill, address)]: one number of each record with no summary, laws first, then bills that passed a house, then
    the latest acted on."""
    from states.mn import convert as C
    B, summ = C.bills(session), C.summaries(session)
    out = []
    for g in C.groups(session):
        if any(summ.get(n) for n in g):
            continue
        def rank(n):
            r = B[n]
            acts = r.get("ACTIONS") or r.get("HOUSE_ACTIONS") or []
            s = json.dumps(r)
            law = 2 if str(r.get("LAW_NUMBER") or "").strip() else 1 if re.search(r"Third reading Passed|passed", s) else 0
            day = max(re.findall(r'"(\d{4}-\d\d-\d\d)', s), default="")
            return (law, day, n[0] == "H")
        n = max(g, key=rank)
        url = first_version(B[n])
        if url:
            out.append((rank(n)[:2], n, url))
    return [(n, u) for _, n, u in sorted(out, reverse=True)]


def main(session, request, minutes=8, stop=lambda: False):
    """Reads the first versions of records with no summary, with `request` (fetch.py's), at most `minutes` a run.
    Returns how many are left."""
    until = time.time() + 60 * minutes
    cache = load(session)
    todo = [(n, u) for n, u in wanted(session) if cache.get(n, {}).get("url") != u]
    read = 0
    for n, u in todo:
        if time.time() > until or stop():
            break
        body = request(u, f"{n} text")
        if body is None:
            continue
        cache[n] = {"url": u, "sections": sections(body.decode("utf-8", "replace"))}
        read += 1
        if read % 50 == 0:
            save(session, cache)
    save(session, cache)
    left = len(todo) - read
    print(f"{session} leads.json: {len(cache)} bill texts ({read} read now, {left} left)", flush=True)
    return left


def entry(session, nums):
    """{"statement", "label"} for the first of `nums` whose text has been read, or None."""
    cache = _cache(session)
    for n in nums:
        if n in cache:
            text, label = L.statement(L.lead(cache[n]["sections"]))
            if text:
                return {"statement": text, "label": label}
    return None


_CACHED = {}


def _cache(session):
    if session not in _CACHED:
        _CACHED[session] = load(session)
    return _CACHED[session]


if __name__ == "__main__":
    from states.mn import fetch as F
    s = int(sys.argv[1]) if len(sys.argv) > 1 else max(int(f) for f in os.listdir(P.DATA) if f.isdigit())
    main(s, F.request, float(sys.argv[2]) if len(sys.argv) > 2 else 8)
