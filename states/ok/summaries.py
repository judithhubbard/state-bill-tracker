#!/usr/bin/env python3
""""What it does" for Oklahoma's laws and vetoed bills, from the House and Senate staffs' bill summaries, read through
LegiScan (approved by the owner 2026-11-22; laws first, vetoes too).

The staffs write a summary of each version of a bill ("BILL SUMMARY ... Research Analysis" from House Research Staff,
"Bill Summary ... Bill Analysis" from Senate staff). They're PDFs on oklegislature.gov under /cf_pdf/, which its
robots.txt bars, so they're never read there: LegiScan keeps copies as each bill's "supplements" (type "Fiscal
Note/Analysis", description "House: Engrossed", "Senate: Committee Substitute", ...), one getSupplement query each
(the PDF, base64). legiscan.py makes those queries (`read_supplements()`), within its daily allowance and only after
every bill's status change, major action and new bill is read; this file says which ones and reads them.

- Which: for each House or Senate bill the governor acted on (signed, let become law, vetoed, pocket vetoed, line-item
  vetoed: read from the history, so pocket vetoes LegiScan calls passed count), the staff summaries of whole versions,
  newest first: the conference committee's (CCR, CCS), the Senate staff's of a Senate bill as the House amended it
  (HASB, whose "Bill Analysis" describes the whole bill), the engrossed bill (ENGR), committee substitutes (CS), the
  bill as introduced (INT); then proposed committee substitutes and recommendations (FULLPCS, POLREC ...), which may not
  have been adopted. Summaries of amendments alone ("Floor Amendment 1", the House staff's "Senate Amendment to House
  Bill": "The Senate amendment to HB 3660 adds ...") and fiscal impact statements (impact statements/fiscal/...) are left
  out. The first is read; when its analysis is empty ("Pending", "Please see previous summary") the next, up to
  TRIES documents a bill. Traps: some House summaries' "Research Analysis" is "Pending" (HB 2236 of 2023's conference
  substitute) while the fiscal analysis describes the bill; a document can belong to another bill (HB 2110 of 2025
  carries SB 2110's engrossed summary, dated ten months after HB 2110 became law): ones dated more than 60 days after
  the governor acted are left out, and one whose header ("Bill No.:") names another bill is kept empty ("other").
- Text: the analysis section ("Research Analysis" / "Bill Analysis") up to "Prepared By", "Fiscal Analysis", "House
  Amendments", "CCR Changes" and the like; a conference report's "The Conference Committee Report for HB 1087 adopts a
  conference committee substitute." is dropped so it leads with what the bill does.
- Each document is read once and kept for good in data/ok/summaries.json ({supplement_id: {"bill", "folder", "read",
  "text": [paragraphs]}}): a version's summary doesn't change.
- Order: newest Legislature first, laws before vetoes, latest governor's action first.

Usage: python3 states/ok/summaries.py   (how many laws and vetoed bills have one, and documents still to read; no queries)
"""
import json, os, re, subprocess, sys, tempfile
from datetime import date, timedelta

HERE = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from states import legiscan_convert as L
from states.ok import profile as P

PATH = os.path.join(P.DATA, "summaries.json")
TRIES = 3
LABEL = {"House": "From the Oklahoma House staff's bill summary, via LegiScan.",
         "Senate": "From the Oklahoma Senate staff's bill summary, via LegiScan."}
GOVERNOR = re.compile(r"^(?:Approved by Governor|Becomes law without|Vetoed|Pocket veto|Line item veto)", re.I)
LAW = re.compile(r"^(?:Approved by Governor|Becomes law without|Line item veto|Veto overridden)", re.I)
DOC = re.compile(r"/BILLSUM/(House|Senate)/[HS]B\d+((?:%20.+?)?)%20BILLSUM\.PDF$", re.I)
# A version code (the file name's middle: "CCR A", "FULLPCS1", "HASB") -> its rank; adopted versions first.
ADOPTED = [(r"N?CC[RS]\d*", 6), (r"HASB\d*", 5), (r"ENGR?", 4), (r"H?CSS?|CS\d", 3), (r"INT|", 1)]
PROPOSED = [(r"(?:FULL|POL|SUB)?P[CS]S?\d*|(?:FULL|POL|SUB)P?CS?\d*|FULLCPS\d*|FULLPSC\d*|FULLPCN\d*|POLREC|SUBREC|PC", 2)]


def rank(code):
    """(adopted?, rank) for a version code, or None for an amendment's summary or an unknown code."""
    c = re.sub(r"\s+", "", code.upper())
    if re.search(r"AMD|^FA|-A\d|^CAN|SAHB|^AMD", c):
        return None
    c = re.sub(r"[&AB]$", "", c) if re.match(r"N?CC[RS]", c) else c
    for pats, adopted in ((ADOPTED, True), (PROPOSED, False)):
        for rx, r in pats:
            if re.fullmatch(rx, c):
                return adopted, r
    return None


def candidates(b):
    """[(supplement_id, house)] of a bill's whole-version staff summaries, best first. A summary dated more than 60 days
    after the governor acted isn't this bill's (HB 2110 of 2025, law in May 2025, carries "House: Engrossed" of March 2026,
    which is SB 2110's: "Engrossed SB 2110 allows farm produced eggs ...")."""
    out = []
    day = acted(b)
    limit = (date.fromisoformat(day) + timedelta(days=60)).isoformat() if day else "9999"
    for s in b.get("supplements") or []:
        m = DOC.search(s.get("state_link") or "")
        if not m or (s.get("date") or "") > limit:
            continue
        r = rank(m.group(2).replace("%20", " ").strip())
        if r is None:
            continue
        out.append(((r[0], s.get("date") or "", r[1], int(s["supplement_id"])), int(s["supplement_id"]), m.group(1).title()))
    out.sort(reverse=True)
    return [(sid, house) for _, sid, house in out]


def acted(b):
    """The day of the governor's last action on a House or Senate bill, or "" (none, or another kind of measure)."""
    if not re.match(r"[HS]B\d", b.get("bill_number") or ""):
        return ""
    return max(((a.get("date") or "")[:10] for a in b.get("history") or [] if GOVERNOR.match(L.text(a.get("action")))), default="")


def read():
    return L.read_json(PATH, {}) or {}


def save(cache):
    os.makedirs(os.path.dirname(PATH), exist_ok=True)
    tmp = PATH + ".tmp"
    with open(tmp, "w") as f:
        json.dump(cache, f, indent=0, sort_keys=True, ensure_ascii=False)
    os.replace(tmp, PATH)


def what(b, cache):
    """("What it does" paragraphs joined by "\n", label) from the first of the bill's summaries read with text, or None."""
    for sid, house in candidates(b):
        x = cache.get(str(sid))
        if x and x.get("text"):
            return "\n".join(x["text"]), LABEL[house]
    return None


def wanted(cache):
    """[(order key, supplement_id, bill number, folder name)]: the next document to read for each law and vetoed bill
    that has no summary yet, in order (newest Legislature, laws, latest action first)."""
    from states.ok import convert as C
    rows = []
    for session, folder in sorted(C.RULES.session_folders().items(), reverse=True):
        for b in L.bills(folder):
            day = acted(b)
            if not day:
                continue
            tried = 0
            for sid, _ in candidates(b):
                x = cache.get(str(sid))
                if x and x.get("text"):
                    break
                if x:
                    tried += 1
                    continue
                if tried < TRIES:
                    law = any(LAW.match(L.text(a.get("action"))) for a in b.get("history") or [])
                    rows.append(((-session, not law, "".join(chr(0x10ffff - ord(c)) for c in day)),
                                 sid, b["bill_number"], os.path.basename(folder)))
                break
    rows.sort()
    return rows


# ---- Reading a summary ----

def pdf_text(data):
    with tempfile.NamedTemporaryFile(suffix=".pdf") as f:
        f.write(data)
        f.flush()
        return subprocess.run(["pdftotext", "-enc", "UTF-8", f.name, "-"], capture_output=True, text=True).stdout


START = re.compile(r"^(?:Research Analysis|Bill Analysis|Analysis|Summary)\s*:?\s*$", re.I)
END = re.compile(r"^(?:Prepared [Bb]y\b|Fiscal Analysis|Other Considerations|(?:House|Senate) Amendments?\b|"
                 r"Fiscal Impact|Statutory Reference|[A-Z][\w ]{0,40} Changes\s*$|©|Page \d+ of \d+\s*$)")
EMPTY = re.compile(r"^(?:pending|n/?a|none|tbd|to be (?:completed|determined)|please see (?:the )?previous summary.*|"
                   r"the (?:measure|bill) is (?:currently )?under review.*)\.?$", re.I)


def tidy(s):
    s = s.replace("­", "").replace("ﬁ", "fi").replace("ﬂ", "fl").replace(" ", " ").replace("ﬀ", "ff")
    s = re.sub(r"(\w)- (\w)", lambda m: m.group(1) + "-" + m.group(2) if m.group(2)[0].isupper() else m.group(1) + m.group(2), s)
    return re.sub(r"\s+", " ", s).strip()


def analysis(text):
    """The analysis section of a staff summary's text, as paragraphs ([] when it's empty or "Pending")."""
    lines = [l.rstrip() for l in text.replace("\f", "\n").splitlines()]
    start = next((i for i, l in enumerate(lines) if START.match(l.strip())), None)
    if start is None:
        return []
    body = []
    for l in lines[start + 1:]:
        if END.match(l.strip()):
            break
        body.append(l.strip())
    width = max((len(l) for l in body), default=0)
    paras, cur = [], []
    for l in body:
        if not l:
            if cur:
                paras.append(cur)
                cur = []
            continue
        if re.match(r"^[•●▪◦\-–]\s*", l) and cur:
            paras.append(cur)
            cur = []
        cur.append(re.sub(r"^[•●▪◦]\s*", "", l))
        if re.search(r"[.:;)\"”]$", l) and len(l) < 0.8 * width:
            paras.append(cur)
            cur = []
    if cur:
        paras.append(cur)
    out = [tidy(" ".join(p)) for p in paras]
    out = [p for p in out if p and not EMPTY.match(p)]
    # Lead with what the bill does: "The Conference Committee Report for HB 1087 adopts a conference committee
    # substitute." says only how it got there.
    if out:
        lead = re.sub(r"^The (?:Conference Committee Report|CCR) (?:for|on|to) [HS]B \d+ adopts? (?:a|the) "
                      r"conference committee substitute\.\s*(?=\S)", "", out[0])
        if lead != out[0]:
            lead = re.sub(r"^The conference committee substitute\b", "The bill", lead)
        out[0] = lead
    return out


def take(cache, sid, bill, folder, supplement):
    """Keep a getSupplement answer's analysis (the PDF in "doc", base64). Returns the paragraphs."""
    import base64
    paras, other = [], None
    if (supplement.get("mime") or "").lower().endswith("pdf") or supplement.get("mime_id") == 2:
        try:
            text = pdf_text(base64.b64decode(supplement.get("doc") or ""))
            # Another bill's summary filed under this one (the header's "Bill No.:" is the first number in the text):
            # kept empty, so the bill's next summary is read.
            m = re.search(r"\b([HS])\.?\s?B\.?\s?0*(\d+)\b", text)
            if m and f"{m.group(1)}B{m.group(2)}" != bill:
                other = f"{m.group(1)}B{m.group(2)}"
            else:
                paras = analysis(text)
        except Exception as e:
            print(f"  ok summaries: {bill} ({sid}): can't read it ({e.__class__.__name__})", flush=True)
    cache[str(sid)] = {"bill": bill, "folder": folder, "read": date.today().isoformat(), "text": paras}
    if other:
        cache[str(sid)]["other"] = other
    return paras


def plan(cache=None):
    """{session: documents still to read} (each law's and vetoed bill's next summary)."""
    from collections import Counter
    rows = wanted(read() if cache is None else cache)
    return Counter(-r[0][0] for r in rows)


if __name__ == "__main__":
    cache = read()
    from states.ok import convert as C
    have = {}
    for session, folder in sorted(C.RULES.session_folders().items(), reverse=True):
        bs = [b for b in L.bills(folder) if acted(b)]
        have[session] = (sum(1 for b in bs if what(b, cache)), len(bs))
    left = plan(cache)
    for s, (n, total) in have.items():
        print(f"{P.session_label(s)}: {n} of {total} laws and vetoed bills have a staff summary; {left.get(s, 0)} documents to read next")
