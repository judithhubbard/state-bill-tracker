#!/usr/bin/env python3
""""What it does" for Michigan bills with no fiscal agency analysis: a lead quoted from the bill's own text
(states/billtext_lead.py).

The House and Senate Fiscal Agencies analyse a bill only when a committee takes it up, so most bills have none. For
those, this reads the bill as introduced: https://www.legislature.mi.gov/documents/2025-2026/billintroduced/House/htm/
2025-HIB-4001.htm (and Senate/htm/2025-SIB-0001.htm; the folder listings give the names, the year being the year
introduced; no robots.txt, one request a second as the Legislature asks). It's Word's HTML: each "Sec. 4." of the act
it amends is a section, new wording is in `FormattedNew` spans and deleted wording in `FormattedStrike` spans. A
section whose "Sec. 4c." heading is new wording is a section the bill adds (new law); any other is amended, and only its
new whole sentences count, with the MCL number from the section's anchor ("sec_import_start_408_414" -> "MCL 408.414").
The enacting sections after the act's own (effective dates, tie-bars, repeals) are left out.

The sections are kept in data/mi/<session>-<session + 1>/leads.json by bill, with the listing's date and size (read
again only when the file changes); the lead is worked out from them each run, so a change to its rules needs no
download. At most `minutes` a run: laws first, then bills that passed a house, then the latest acted on. texts.py puts
the leads in texts_<session>.json for bills with no analysis.
Usage: python3 states/mi/billtext.py [first year] [minutes]
"""
import glob, json, os, re, sys, time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
from states import billtext_lead as L

DATA = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "mi"))
SITE = "https://www.legislature.mi.gov"
ANCHOR = re.compile(r'<a name="sec_import_start_(\d+)_(\w+?)(?:_amended|_new|_added)?"\s*>\s*</a>', re.I)
CITE = re.compile(r"^\s*\[\[(MCL [^\]]+)\]\]\s*")
SEC = re.compile(r"^\s*Sec\.\s*(\d+[a-z]*)\.\s*", re.I)


def drop(runs, n):
    """The runs without their first n characters."""
    out = []
    for t, u in runs:
        if n >= len(t):
            n -= len(t)
            continue
        out.append((t[n:], u))
        n = 0
    return out


def sections(page):
    """The bill's sections (billtext_lead's Section dicts) from its introduced text."""
    body = page[page.find("<body"):]
    m = re.search(r"class=Enactment", body)
    body = body[m.start():] if m else body
    m = re.search(r"<p class=EnactingSection", body)
    body = body[:m.start()] if m else body  # (the bill's own enacting sections: effective dates, tie-bars)
    body = re.sub(r"class=FormattedNew", "style='text-decoration:underline'", body)
    body = re.sub(r"class=FormattedStrike", "style='text-decoration:line-through'", body)
    body = ANCHOR.sub(lambda m: f"[[MCL {m.group(1)}.{m.group(2)}]]", body)
    paras = []
    for runs in L.paragraphs(body):
        raw = "".join(t for t, _ in runs).replace("\xa0", " ")
        c = CITE.match(raw)
        cite = c.group(1) if c else ""
        if c:
            runs = drop(runs, c.end())
            raw = raw[c.end():]
        s = SEC.match(raw)
        if s:
            new = next((u for t, u in runs if t.strip()), False)
            rest = drop(runs, s.end())
            if new:
                paras.append([(f"Sec. {s.group(1)}. ", True)] + rest)
            else:
                # An amended section: say so, so split() keeps only its new whole sentences.
                paras.append([(f"Sec. {s.group(1)}. Section {s.group(1)} ({cite or 'MCL'}) is amended to read as follows:", False)])
                if rest:
                    paras.append(rest)
            continue
        paras.append(runs)
    cite = lambda head: (re.search(r"\((MCL [\d.]+[a-z]*)\)", head) or [None, ""])[1]
    secs = L.split(paras, cite)
    for sec in secs:
        # New wording in an amended section that's only a list item or a definition out of its list ("(i) An individual
        # whose primary work location is not in this state.") says little on its own.
        sec["added"] = [a for a in sec["added"] if not re.match(r"^\((?:[a-z]{1,4}|\d+|[A-Z])\)", a) or
                        (L.MODAL.search(a) and not re.search(r"[\"“][^\"”]{1,80}[\"”] (?:means|includes)", a))]
    return L.compact(secs)


def folder(start):
    return os.path.join(DATA, f"{start}-{start + 1}")


def listing(start, get):
    """Bill ("HB4001") -> (address, date and size) of its introduced text, from the two folder listings."""
    out = {}
    for house in ("House", "Senate"):
        page = (get(f"{SITE}/documents/{start}-{start + 1}/billintroduced/{house}/htm/") or b"").decode("utf-8", "replace")
        for m in re.finditer(r"(\d+/\d+/\d{4}\s+\d+:\d+ [AP]M)\s+(\d+) <A HREF=\"([^\"]*/\d{4}-([HS])IB-(\d{4})\.htm)\"", page, re.I):
            out[f"{m.group(4).upper()}B{int(m.group(5))}"] = (SITE + m.group(3), " ".join(m.group(1).split()) + " " + m.group(2))
    return out


def ranked(start):
    """The session's bills, laws first, then bills that passed a house, then the latest acted on."""
    out = []
    for f in glob.glob(os.path.join(folder(start), "*", "*-[HS]B-*.xml")):
        m = re.search(r"-([HS])B-(\d+)\.xml$", f)
        try:
            x = open(f, encoding="utf-8-sig", errors="replace").read()
        except OSError:
            continue
        acts = " ".join(re.findall(r"<historyaction>(.*?)</historyaction>", x, re.S))
        days = re.findall(r"<historydate>(\d{4}-\d\d-\d\d)", x) or re.findall(r"<date>(\d{4}-\d\d-\d\d)", x)
        rank = 2 if re.search(r"<publicact>\s*\d", x) or re.search(r"approved by governor|public act", acts, re.I) else \
            1 if re.search(r"\bpassed\b", acts, re.I) else 0
        out.append((rank, max(days, default=""), f"{m.group(1)}B{int(m.group(2))}"))
    return [b for _, _, b in sorted(out, reverse=True)]


def decode(body):
    """Word's HTML says windows-1252, but some files are UTF-8 ("employer–employee" read as "employerâ€“employee")."""
    try:
        return body.decode("utf-8")
    except UnicodeDecodeError:
        return body.decode("cp1252", "replace")


def path(start):
    return os.path.join(folder(start), "leads.json")


def load(start):
    try:
        return json.load(open(path(start)))
    except (OSError, ValueError):
        return {}


def save(start, cache):
    tmp = path(start) + ".tmp"
    json.dump(cache, open(tmp, "w"), ensure_ascii=False)
    os.replace(tmp, path(start))


def main(start, have, get, minutes=8, stop=lambda: False):
    """Reads the introduced texts of bills with no analysis (not in `have`), at most `minutes` a run, with `get` (fetch.py's,
    one request a second). Returns how many are left."""
    until = time.time() + 60 * minutes
    if not os.path.isdir(folder(start)):
        return 0
    cache = load(start)
    docs = listing(start, get)
    todo = [b for b in ranked(start) if b not in have and b in docs and cache.get(b, {}).get("stamp") != docs[b][1]]
    read = 0
    for b in todo:
        if time.time() > until or stop():
            break
        body = get(docs[b][0])
        if body is None:
            continue
        cache[b] = {"stamp": docs[b][1], "sections": sections(decode(body))}
        read += 1
        if read % 50 == 0:
            save(start, cache)
    save(start, cache)
    left = len(todo) - read
    print(f"{start}-{start + 1} leads.json: {len(cache)} bill texts ({read} read now, {left} left)", flush=True)
    return left


def entries(start):
    """Bill -> {"statement", "label"} for texts_<session>.json, from the texts read so far."""
    out = {}
    for b, v in load(start).items():
        text, label = L.statement(L.lead(v["sections"]))
        if text:
            out[b] = {"statement": text, "label": label}
    return out


if __name__ == "__main__":
    from states.mi.fetch import get, CURRENT
    from states.mi import texts
    s = int(sys.argv[1]) if len(sys.argv) > 1 else CURRENT
    main(s, texts.analysed(s), get, float(sys.argv[2]) if len(sys.argv) > 2 else 8)
    texts.write(s)
