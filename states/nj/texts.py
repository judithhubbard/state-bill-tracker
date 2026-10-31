#!/usr/bin/env python3
"""What each bill does, in the Legislature's own plain words, from pub.njleg.gov: the sponsor's statement
at the end of the bill as introduced, the latest committee statement (what the committee reported and
any amendments), and the summary of the budget office's fiscal estimate. Written as
data/nj/texts_<session>.json: {"S4659": {"statement": ..., "committee": [name, "YYYY-MM-DD", text],
"fiscal": ...}}. Documents already read are kept in data/nj/docs_<session>.json, so each run reads only
new ones (fetch.py runs it for the current session).

Usage: python3 states/nj/texts.py [session]
"""
import html, json, os, re, sys, time, urllib.error, urllib.request, zipfile
from datetime import datetime
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
from states.nj import profile as P
from states.nj.convert import _rows, is_amendment

BASE = "https://pub.njleg.gov/Bills"


def paragraphs(page):
    page = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", "", page).replace("\r", " ").replace("\n", " ")
    page = re.sub(r"(?i)<br\s*/?>|</p>|</tr>|</h\d>", "\n", page)
    text = html.unescape(re.sub(r"<[^>]+>", " ", page)).replace("\xa0", " ")
    return [p for p in (re.sub(r"\s+", " ", p).strip() for p in text.split("\n")) if p]


def statement(ps):
    """The sponsor's statement: everything after the "STATEMENT" heading."""
    i = next((i for i, p in enumerate(ps) if p.upper() == "STATEMENT"), None)
    return "\n".join(ps[i + 1:]) if i is not None else ""


BOILER = re.compile(r"prefiled for introduction .* technical review|includes the changes required by technical review", re.I)


def committee(ps):
    """A committee statement: the committee's name, and its text after the "DATED:" line."""
    i = next((i for i, p in enumerate(ps) if p.startswith("DATED:")), None)
    if i is None:
        return "", ""
    name = next((m.group(1).title().replace(" And ", " and ") for p in ps[:3]
                 for m in [re.search(r"\b((?:SENATE|ASSEMBLY|JOINT) [A-Z ,'&]+COMMITTEE)\b", p)] if m), "")
    body = [p for p in ps[i + 1:] if not BOILER.search(p) and p != "None"]
    return name, "\n".join(body)


def fiscal(ps):
    """The fiscal estimate's summary: its bullet points before the bill description."""
    end = next((i for i, p in enumerate(ps) if p == "BILL DESCRIPTION"), len(ps))
    return "\n".join(p.lstrip("·• ").strip() for p in ps[:end] if p.startswith(("·", "•")))


def doc_url(path):
    # Bills are in folders of 500 ("A0500"); concurrent resolutions in "ACR" and "SCR".
    m = re.search(r"(\d{4})BILL[\\/]+([AS]\d+|[AS]CR)[\\/]+([^\\/]+)\.\w+$", path, re.I)
    return f"{BASE}/{m.group(1)}/{m.group(2)}/{m.group(3)}.HTM" if m else None


def day(md):
    m = re.match(r"(\d+)/(\d+)/(\d{4})", md or "")
    return f"{m.group(3)}-{int(m.group(1)):02d}-{int(m.group(2)):02d}" if m else ""


def main(session):
    z = zipfile.ZipFile(os.path.join(P.DATA, f"DB{session}_TEXT.zip"))
    docs_path = os.path.join(P.DATA, f"docs_{session}.json")
    docs = json.load(open(docs_path)) if os.path.exists(docs_path) else {}  # address -> the part we keep
    # Each bill's documents: its text as introduced, its committee statements, its fiscal estimates.
    wanted = {}
    # Bills, and the concurrent resolutions that propose constitutional amendments (the only resolutions shown).
    subj = {}
    for r in _rows(z, "BILLSUBJ.TXT"):
        subj.setdefault(r["BillType"] + r["BillNumber"], set()).add(r["SubjectKey"])
    amendments = {r["BillType"] + r["BillNumber"] for r in _rows(z, "MAINBILL.TXT") if is_amendment(r, subj.get(r["BillType"] + r["BillNumber"], set()))}
    for r in _rows(z, "BILLWP.TXT"):
        bill, kind, url = r["BillType"].strip() + r["BillNumber"].strip(), r["DocType"].strip(), doc_url(r["Document"])
        if not (r["BillType"].strip() in ("A", "S") or bill in amendments) or not url or kind not in ("I", "S", "FE"):
            continue
        wanted.setdefault(bill, []).append((kind, url, day(r["ModDate"])))
    # Identical bills in the two houses carry the same sponsor's statement: read the text of one of them.
    twin = {}
    for r in _rows(z, "MAINBILL.TXT"):
        bill = r["BillType"].strip() + r["BillNumber"].strip()
        other = re.match(r"[AS]\d+", r["IdenticalBillNumber"].strip())
        if other and other.group() in wanted:
            twin[bill] = other.group()
    for bill, ds in wanted.items():
        if bill in twin and twin[bill] < bill:  # keep the one that sorts first (the A bill)
            wanted[bill] = [x for x in ds if x[0] != "I"]
    kinds = {u: k for ds in wanted.values() for k, u, d in ds}
    todo = sorted(set(kinds) - set(docs))[:int(os.environ.get("TEXTS_LIMIT", 10 ** 9))]
    pick = {"I": statement, "S": committee, "FE": fiscal}
    print(f"texts {session}: {len(todo)} documents to read")
    for n, url in enumerate(todo):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "statebilltracker.org data fetch"})
            with urllib.request.urlopen(req, timeout=60) as r:
                docs[url] = pick[kinds[url]](paragraphs(r.read().decode("cp1252", "replace")))
        except urllib.error.HTTPError as e:
            docs[url] = "" if e.code == 404 else None
        except Exception:
            docs[url] = None  # tried again next run
        if docs[url] is None:
            del docs[url]
        if n % 500 == 499:  # keep what's read so far, in case the run is cut short
            json.dump(docs, open(docs_path, "w"))
        time.sleep(0.15)
    json.dump(docs, open(docs_path, "w"))

    out = {}
    for bill, ds in wanted.items():
        rec = {}
        intro = next((u for k, u, d in sorted(ds, key=lambda x: x[1]) if k == "I" and docs.get(u)), None)
        if intro:
            rec["statement"] = docs[intro]
        stmts = sorted((d, u) for k, u, d in ds if k == "S" and docs.get(u) and docs[u][1])
        if stmts:
            rec["committee"] = [docs[stmts[-1][1]][0], stmts[-1][0], docs[stmts[-1][1]][1]]
        fes = sorted((d, u) for k, u, d in ds if k == "FE" and docs.get(u))
        if fes:
            rec["fiscal"] = docs[fes[-1][1]]
        if rec:
            out[bill] = rec
    json.dump(out, open(os.path.join(P.DATA, f"texts_{session}.json"), "w"), ensure_ascii=False)
    print(f"texts_{session}.json: {len(out)} bills ({sum('statement' in r for r in out.values())} statements, "
          f"{sum('committee' in r for r in out.values())} committee statements, {sum('fiscal' in r for r in out.values())} fiscal estimates)")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else P.session_of(datetime.now(ZoneInfo(P.TIMEZONE)).year))
