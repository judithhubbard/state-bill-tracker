#!/usr/bin/env python3
""""What it does" for Massachusetts: a lead quoted from each bill's own text (states/billtext_lead.py), since the General
Court publishes no summaries.

The text is the API's document record (GET /api/GeneralCourts/194/Documents/H100, its DocumentText: plain text, the
bill as filed or, for a committee's new draft, as drafted; robots.txt bars nothing). "SECTION 1." marks begin sections;
"Chapter 6 of the General Laws is hereby amended by inserting after section 116G the following section:- ..." is new
law, "... by striking out ... and inserting in place thereof the following paragraph:- ..." replaces wording (the new
wording counts as added), and a section with no instruction ("SECTION 1. (a) The Massachusetts General Court shall
establish ...") is uncodified new law.

The sections are kept in data/ma/<session>/leads.json by bill, read once, ever (a new draft is a new number); the lead
is worked out from them each run, so a change to its rules needs no download. At most `minutes` a run, one
request at a time, the current General Court first, the bills acted on latest first. Writes data/ma/texts_<session>.json.
Usage: python3 states/ma/billtext.py [session] [minutes]
"""
import json, os, re, sys, time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
from states import billtext_lead as L
from states.ma.fetch import API, CURRENT, DATA, court_of, get, save

PAUSE = 0.5


def cite(head):
    """"Section 25A of Chapter 118E of the General Laws" -> "M.G.L. c. 118E, § 25A"."""
    if not re.search(r"General Laws", head, re.I):
        return ""  # (a special act, "chapter 400 of the acts of 2008", or a town's charter)
    m = re.search(r"[Ss]ection (\d+[A-Z]*(?:½)?) of [Cc]hapter (\d+[A-Z]*)", head) or re.search(r"[Cc]hapter (\d+[A-Z]*),? [Ss]ection (\d+[A-Z]*)", head)
    if not m:
        return ""
    sec, ch = (m.group(1), m.group(2)) if head[m.start()] in "Ss" else (m.group(2), m.group(1))
    return f"M.G.L. c. {ch}, § {sec}"


def sections(text):
    """The bill's sections from its DocumentText."""
    t = (text or "").replace("\r", "")
    # Its lines are sometimes paragraphs and sometimes wrapped lines: join them, then begin paragraphs again at each
    # "SECTION 1." and at each subsection's number after a sentence ends.
    t = re.sub(r"\s+", " ", t)
    t = re.sub(r"\s(?=SECTION\s+\d+[A-Z]?\.\s)", "\n", t)
    t = re.sub(r"(?<=[.;:])\s(?=\((?:\d+|[a-z]{1,3})\)\s)", "\n", t)
    paras = [[(p, False)] for p in t.split("\n") if p.strip()]
    if paras and not L.MARK.match(L.text_of(paras[0])):
        # A one-section bill without a mark ("Notwithstanding any general or special law to the contrary, ...").
        paras[0] = [("SECTION 1. " + L.text_of(paras[0]), False)]
    return L.compact(L.split(paras, cite))


def wanted(session):
    """The court's bills and resolves, the latest acted on first."""
    folder = os.path.join(DATA, str(session))
    try:
        docs = json.load(open(os.path.join(folder, "documents.json")))
    except (OSError, ValueError):
        return []
    out = []
    for d in docs:
        b = d.get("BillNumber") or ""
        title = d.get("Title") or ""
        if not re.fullmatch(r"[HS]\d+", b) or not re.match(r"(?:An Act|Resolve)", title):
            continue
        try:
            last = max((a.get("Date") or "" for a in json.load(open(os.path.join(folder, "bills", f"{b}.json")))), default="")
        except (OSError, ValueError):
            last = ""
        out.append((last, b))
    return [b for _, b in sorted(out, reverse=True)]


def main(session, minutes=8):
    until = time.time() + 60 * minutes
    folder = os.path.join(DATA, str(session))
    path = os.path.join(folder, "leads.json")
    try:
        cache = json.load(open(path))
    except (OSError, ValueError):
        cache = {}
    todo = [b for b in wanted(session) if b not in cache]
    read = 0
    for b in todo:
        if time.time() > until:
            break
        d = get(f"{API}/GeneralCourts/{court_of(session)}/Documents/{b}")
        time.sleep(PAUSE)
        if not d:
            continue
        cache[b] = {"sections": sections(d.get("DocumentText"))}
        read += 1
        if read % 50 == 0:
            keep(path, cache)
    keep(path, cache)
    out = {}
    for b, v in cache.items():
        text, label = L.statement(L.lead(v["sections"]), "")
        if text:
            out[b] = {"statement": text, "label": label}
    save(os.path.join(DATA, f"texts_{session}.json"), out)
    print(f"{session} leads.json: {len(cache)} bill texts ({read} read now, {max(0, len(todo) - read)} left); "
          f"texts_{session}.json: {len(out)} leads", flush=True)
    return max(0, len(todo) - read)  # bills still to read


def keep(path, cache):
    save(path, cache)


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else CURRENT, float(sys.argv[2]) if len(sys.argv) > 2 else 8)
