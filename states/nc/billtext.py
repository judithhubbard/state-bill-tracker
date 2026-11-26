#!/usr/bin/env python3
""""What it does" for North Carolina bills with no Legislative Analysis Division summary: a lead quoted from the bill's
own text (states/billtext_lead.py).

The staff summarize a bill only once a committee hears it, so about three quarters of a session's bills have none. For
those, this reads the bill as filed: its first edition's HTML (the bill record's "Filed" edition,
/Sessions/2025/Bills/House/PDF/H10v0.pdf, has a Word HTML twin at .../HTML/H10v0.html; robots.txt allows it, two seconds
apart as it asks, sharing fetch.py's clock). "SECTION 1." marks the sections, each often with a short caption
("SECTION 1. Establishment. (a) The Committee ..."); an amended statute says "G.S. 105-278.3(g) reads as rewritten:" and
underlines its new wording (whole sentences count), a new one "is amended by adding a new section to read:".

The sections are kept in data/nc/<session>/leads.json by bill, with the edition's address (read once, ever); the lead is
worked out from them each run, so a change to its rules needs no download. At most `minutes` a run: laws first, then
bills that passed a house, then the latest acted on. texts.py puts the leads in texts_<session>.json for bills with no
summary.
Usage: python3 states/nc/billtext.py [session] [minutes]
"""
import json, os, re, sys, time, urllib.error, urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
from states import billtext_lead as L

DATA = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "nc"))
# A section's caption: a few words, no verb ("Establishment.", "Duties.", "Study/Report.").
CAPTION = re.compile(r"^([A-Z][\w ,'&/()-]{1,70}?)\.\s*(?=[–—]|\s\S)")
VERB = re.compile(r"\b(?:shall|is|are|may|must|will|has|have|was|were)\b")


def sections(page):
    """The bill's sections (billtext_lead's Section dicts) from its HTML edition."""
    m = re.search(r"enacts:", page)
    body = page[m.start():] if m else page
    body = re.sub(r"&#8209;", "-", body)  # (non-breaking hyphens in statute numbers)
    paras = []
    for runs in L.paragraphs(body):
        t = L.text_of(runs)
        mk = L.MARK.match(t)
        if mk:
            rest = re.sub(r"^\s*[–—]\s*", "", t[mk.end():])
            c = CAPTION.match(rest)
            if c and len(c.group(1).split()) <= 8 and not VERB.search(c.group(1)):
                rest = re.sub(r"^\s*[–—]\s*", "", rest[c.end():])
            rest = re.sub(r"^((?:\(\w+\)\s*)+)[A-Z][^.–—]{1,80}\.\s*[–—]\s*", r"\1", rest)  # ("(a) Caption. – ")
            # "G.S. 105-278.3(g) reads as rewritten:" is an amendment, as other states word it.
            rest = re.sub(r"\breads? as rewritten\s*:", "is amended to read as follows:", rest)
            u = next((x for s, x in runs if s.strip()), False)
            paras.append([(t[:mk.end()] + rest, u)])
            continue
        # (Quoted new law: "“§ 143B-1. Title. ...”")
        runs = [(re.sub(r"^\s*[\"“]", "", s) if i == 0 else s, u) for i, (s, u) in enumerate(runs)]
        paras.append(runs)
    def cite(head):
        m = re.search(r"G\.S\.\s*(\d+[A-Z]?-[\d.]+[A-Z]?)", head)
        return f"G.S. {m.group(1)}" if m else ""
    secs = L.split(paras, cite)
    # A subsection's or definition's caption ("(5) Embalming fluid. – Any chemicals ...", "Prevent hazing. – A local
    # board ..."): left out; a definition (no verb of its own) says little out of its list.
    cap = re.compile(r"^((?:\(\w+\)\s*)*)[A-Z][^.–—]{1,80}\.\s*[–—]\s*")
    for sec in secs:
        sec["paras"] = [cap.sub(r"\1", re.sub(r"[\"”]$", "", p)) for p in sec["paras"]]
        sec["added"] = [cap.sub(r"\1", re.sub(r"[\"”]$", "", a)) for a in sec["added"]
                        if not cap.match(a) or L.MODAL.search(cap.sub("", a))]
    return L.compact(secs)


def get_bytes(url, F):
    """The page's bytes, paced with fetch.py's clock (F: the running fetch module); None if it can't be read."""
    if url.startswith("/"):
        url = F.SITE + url
    for attempt in range(3):
        wait = F._last[0] + F.DELAY - time.time()
        if wait > 0:
            time.sleep(wait)
        F._last[0] = time.time()
        try:
            req = urllib.request.Request(url, headers={"User-Agent": F.AGENT})
            with urllib.request.urlopen(req, timeout=120) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            if e.code in (401, 403, 429):
                F.refused(url, e.code)
            time.sleep(10 * (attempt + 1))
        except Exception:
            time.sleep(10 * (attempt + 1))
    return None


def wanted(session, have):
    """[(bill, address)]: bills (not resolutions) with no summary, laws first, then bills that passed a house, then the
    latest acted on."""
    out = []
    folder = os.path.join(DATA, str(session), "bills")
    for f in os.listdir(folder) if os.path.isdir(folder) else []:
        try:
            d = json.load(open(os.path.join(folder, f)))
        except (OSError, ValueError):
            continue
        b = d.get("number") or f[:-5]
        if b in have or d.get("kind") not in ("HB", "SB"):
            continue
        ed = next((e for e in d.get("editions") or [] if e.get("label") == "Filed" and e.get("pdf")), None)
        if not ed:
            continue
        url = re.sub(r"/PDF/(\w+)\.pdf$", r"/HTML/\1.html", ed["pdf"])
        acts = " ".join(h.get("action") or "" for h in d.get("history") or [])
        rank = 2 if d.get("law") else 1 if re.search(r"Passed 3rd Reading|Ratified", acts) else 0
        day = max((h.get("date") or "" for h in d.get("history") or []), default="")
        out.append((rank, day, b, url))
    return [(b, u) for _, _, b, u in sorted(out, reverse=True)]


def decode(body):
    """Word's HTML says windows-1252, but some files are UTF-8 ("employer–employee" read as "employerâ€“employee")."""
    try:
        return body.decode("utf-8")
    except UnicodeDecodeError:
        return body.decode("cp1252", "replace")


def path(session):
    return os.path.join(DATA, str(session), "leads.json")


def load(session):
    try:
        return json.load(open(path(session)))
    except (OSError, ValueError):
        return {}


def save(session, cache):
    tmp = path(session) + ".tmp"
    json.dump(cache, open(tmp, "w"), ensure_ascii=False)
    os.replace(tmp, path(session))


def main(session, have, minutes=8, stop=lambda: False, F=None):
    """Reads the filed editions of bills with no summary (not in `have`), at most `minutes` a run. Returns how many are
    left."""
    if F is None:
        from states.nc import fetch as F
    until = time.time() + 60 * minutes
    cache = load(session)
    todo = [(b, u) for b, u in wanted(session, have) if cache.get(b, {}).get("url") != u]
    read = 0
    try:
        for b, u in todo:
            if time.time() > until or stop():
                break
            body = get_bytes(u, F)
            if body is None:
                continue
            cache[b] = {"url": u, "sections": sections(decode(body))}
            read += 1
            if read % 50 == 0:
                save(session, cache)
    finally:
        save(session, cache)
    left = len(todo) - read
    print(f"{session} leads.json: {len(cache)} bill texts ({read} read now, {left} left)", flush=True)
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
    from states.nc import texts
    s = int(sys.argv[1]) if len(sys.argv) > 1 else max(int(f) for f in os.listdir(DATA) if re.fullmatch(r"\d{4}", f))
    main(s, texts.analysed(s), float(sys.argv[2]) if len(sys.argv) > 2 else 8)
    texts.write(s)
