#!/usr/bin/env python3
"""The governor's veto messages (absolute, conditional and line-item), from pub.njleg.gov, written as
data/nj/vetoes_<session>.json: {"S4514": {"kind": "absolute", "signer": "Mikie Sherrill", "year": 2026,
"text": "..."}}. Only messages not already saved are downloaded (fetch.py runs it for every session).

Which bills: the session's document list (BILLWP, type "V"), and any bill whose record shows a veto, since
2022-23's list is incomplete. A message is at /Bills/<year>/<A or S><500-number block>/<number>_V1.HTM.
Usage: python3 states/nj/vetoes.py [session ...]
"""
import html, json, os, re, sys, time, urllib.error, urllib.request, zipfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
from states.nj import profile as P
from states.nj.convert import _rows

BASE = "https://pub.njleg.gov/Bills"
KINDS = {"A": "absolute", "C": "conditional", "L": "line-item"}


def candidates(session):
    """Bill -> kind ("absolute", "conditional", "line-item") for every bill with a veto message."""
    z = zipfile.ZipFile(os.path.join(P.DATA, f"DB{session}_TEXT.zip"))
    out = {}
    for r in _rows(z, "BILLWP.TXT"):
        if r["DocType"] == "V" and r["BillType"].strip() in ("A", "S"):
            out[r["BillType"].strip() + r["BillNumber"].strip()] = KINDS.get(r["Comment"].strip()[:1].upper(), "absolute")
    if "MAINBILL.TXT" in z.namelist():
        for r in _rows(z, "MAINBILL.TXT"):
            kind = {"AV": "absolute", "CV": "conditional", "LIV": "line-item"}.get(r["GovernorAction"].strip())
            if kind and r["BillType"].strip() in ("A", "S"):
                out.setdefault(r["BillType"].strip() + r["BillNumber"].strip(), kind)
    for r in _rows(z, "BILLHIST.TXT"):  # a conditional veto stays in the history after the bill is re-passed
        if re.search(r"\bCV\b", r["Action"]) and r["BillType"].strip() in ("A", "S"):
            out.setdefault(r["BillType"].strip() + r["BillNumber"].strip(), "conditional")
    return out


def url(session, bill):
    n = int(bill[1:])
    return f"{BASE}/{session}/{bill[0]}{-(-n // 500) * 500}/{n}_V1.HTM"


def message(page):
    """The governor's reasons: the paragraphs after the opening one ("Pursuant to Article V ... I herewith
    return" or "I am returning") and before the closing one ("Accordingly"/"Therefore, I herewith return");
    a conditional veto then lists line-by-line amendments, which are left out. Returns (signer, text)."""
    page = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", "", page).replace("\r", " ").replace("\n", " ")
    page = re.sub(r"(?i)<br\s*/?>|</p>", "\n", page)
    text = html.unescape(re.sub(r"<[^>]+>", " ", page)).replace("\xa0", " ")
    paras = [p for p in (re.sub(r"\s+", " ", p).strip() for p in text.split("\n")) if p]
    signer = next((p[3:].strip() for p in paras if p.startswith("/s/")), "")  # the governor signs first
    # After the "To the Senate:" line, and after the formal opening sentence when there is one (a
    # line-item veto opens straight with its reasons).
    start = next((i + 1 for i, p in enumerate(paras) if re.match(r"To the (General Assembly|Senate|Assembly)\b", p)), 0)
    if start < len(paras) and re.search(r"Pursuant to Article V|herewith return|I am returning", paras[start]):
        start += 1
    body = []
    for p in paras[start:]:
        if re.match(r"(Accordingly|Therefore|For these reasons|For the foregoing reasons)\b.*\b(herewith return|return)", p, re.I) \
                or re.search(r"recommend that it be amended as follows", p) or p.startswith(("Respectfully", "/s/", "[seal]")):
            break
        body.append(p)
    return signer, "\n\n".join(body)


def main(session):
    path = os.path.join(P.DATA, f"vetoes_{session}.json")
    saved = json.load(open(path)) if os.path.exists(path) else {}
    todo = {b: k for b, k in candidates(session).items() if b not in saved}
    for bill, kind in sorted(todo.items()):
        try:
            req = urllib.request.Request(url(session, bill), headers={"User-Agent": "statebilltracker.org data fetch"})
            with urllib.request.urlopen(req, timeout=60) as r:
                page = r.read().decode("cp1252", "replace")
        except urllib.error.HTTPError as e:
            if e.code == 404:
                continue  # the record shows a veto but no message was published (often a pocket veto)
            print(f"  {bill}: {e}", file=sys.stderr)
            continue
        except Exception as e:
            print(f"  {bill}: {e}", file=sys.stderr)
            continue
        signer, text = message(page)
        if text:
            saved[bill] = {"kind": kind, "signer": signer, "text": text}
        time.sleep(0.3)
    with open(path, "w") as f:
        json.dump(saved, f, indent=1, ensure_ascii=False)
    print(f"vetoes_{session}.json: {len(saved)} messages ({len(todo)} looked up this time)")


if __name__ == "__main__":
    for s in (map(int, sys.argv[1:]) if len(sys.argv) > 1 else [P.session_of(time.localtime().tm_year)]):
        main(s)
