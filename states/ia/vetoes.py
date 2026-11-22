"""Iowa governor's letters on vetoes and item vetoes. The Legislature posts each with the enrolled bill, at an address
built from the bill: www.legis.iowa.gov/docs/publications/LGE/<ga>/Attachments/<HF383>_GovLetter.pdf (linked from its
"Bills Vetoed by Governor" and "Bills Item Vetoed by Governor" lists; robots.txt bars only /chambers/). Most are typed;
a few are scans with an old OCR layer, kept as they are ("ofveterans affairs", HF 2782 of 2026), and a scan with no text
is read by OCR (states/letters.py, approved by the owner 2026-11-22).

fetch() is called by states/ia/fetch.py early in each run, with its own request() (so the site's bot check, about 45
requests a run on GitHub, ends it like any other request): at most LIMIT letters a run, each read once into
data/ia/<first year>/vetoes/<HF383>.json; one not posted (404) is asked again a week later. Which bills: those whose
last action in the Disposition of Bills list (list.json) is "Vetoed by Governor" or "Item vetoed, signed by Governor".
"""
import json, os, re
from datetime import date, timedelta

from states import letters as L

DATA = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "ia"))
SITE = "https://www.legis.iowa.gov"
LIMIT = 4


def folder(first):
    return os.path.join(DATA, str(first), "vetoes")


def url(ga, bill):
    return f"{SITE}/docs/publications/LGE/{ga}/Attachments/{bill}_GovLetter.pdf"


def wanted(first):
    """{"HF383": "absolute" | "line-item"} from the General Assembly's list.json."""
    try:
        bills = json.load(open(os.path.join(DATA, str(first), "list.json"))).get("bills", {})
    except (OSError, ValueError):
        return {}
    out = {}
    for b, v in bills.items():
        last = (v.get("last") or "").lower()
        if last.startswith("vetoed by governor"):
            out[b] = "absolute"
        elif last.startswith("item vetoed"):
            out[b] = "line-item"
    return out


def garbled(raw):
    """An old OCR layer that ran words together ("ofveterans affairs", "2782,an Act", "1 hereby transmit"): read the
    scan again."""
    return len(re.findall(r"\bof(?:the|this|veterans|health|human|public|state|Iowa)\b|[a-z],[a-z]"
                          r"|\b1 (?:hereby|am|have|recognize|believe)\b", raw)) >= 3


def read(first, bill, u, get):
    """L.scanned(), and once more by OCR when the PDF's own text is an old, garbled OCR layer (one download)."""
    got = {}

    def once(x):
        if x not in got:
            got[x] = get(x)
        return got[x]
    rec = L.scanned(folder(first), bill, u, once)
    if rec and not rec.get("ocr") and rec.get("raw") and garbled(rec["raw"]) and L.ocr_ready():
        os.remove(os.path.join(folder(first), f"{bill}.json"))
        rec = L.scanned(folder(first), bill, u, once, force_ocr=True)
    return rec


def fetch(ga, first, state, get, absent):
    """Read up to LIMIT letters not read yet. `get(url)` returns the PDF's bytes or None, `absent()` whether that None
    was a 404; `state` is the General Assembly's state.json dict ("vetoLetters": {bill: day last found missing})."""
    misses = state.setdefault("vetoLetters", {})
    week = (date.today() - timedelta(days=7)).isoformat()
    n = 0
    for bill in sorted(wanted(first)):
        if n >= LIMIT:
            break
        if os.path.exists(os.path.join(folder(first), f"{bill}.json")) or misses.get(bill, "") > week:
            continue
        n += 1
        if read(first, bill, url(ga, bill), get) is None:
            if absent():
                misses[bill] = date.today().isoformat()
        else:
            misses.pop(bill, None)
    return n


_SALUTE = re.compile(r"^\s*Dear (?:Mr\.|Madam|Madame|Ms\.) Secretary\s*[:,;.]", re.I)
_CLOSE = re.compile(r"^\s*(?:Sincerely|Respectfully)\b", re.I)


def _paras(rec):
    raw = rec.get("raw") or ""
    if rec.get("ocr"):
        # (A scan's bullets read as "e": "e Division XVII involves ...".)
        return [re.sub(r"^[e®°]\s+(?=Division|Section|Item|Page)", "• ", p) for p in
                L.ocr_letter(raw, governor="Kim Reynolds", start=r"^Dear (?:Mr\.|Madam|Madame|Ms\.) Secretary")]
    lines = raw.replace("\f", "\n").split("\n")
    start = next((i + 1 for i, t in enumerate(lines) if _SALUTE.match(t)), 0)
    body = []
    for t in lines[start:]:
        if _CLOSE.match(t):
            break
        # The letterhead's footer on every page: "STATE CAPITOL  DES MOINES, IOWA 50319  515.281.5211  WWW.GOVERNOR.IOWA.GOV".
        if re.search(r"WWW\.GOVERNOR\.IOWA\.GOV|^\s*FAX\b|STATE CAPITOL\s+DES MOINES", t, re.I):
            continue
        body.append(t)
    out = []
    for p in L.wrapped(body):
        # (A paragraph a page break split joins up again.)
        if out and not re.search(r"[.:!?;\"”)]$", out[-1]) and re.match(r"[a-z(]", p):
            out[-1] += " " + p
        else:
            out.append(p)
    # An old OCR layer's slips: numbers split ("House File 3 83"), "1 hereby" for "I hereby" (letters.py's fixes).
    out = [re.sub(r"\b((?:House|Senate) File) (\d) (\d{1,3})\b", r"\1 \2\3", p) for p in out]
    for pat, rep in L._OCR_FIXES:
        out = [pat.sub(rep, p) for p in out]
    return out


_CACHE = {}


def message(first, bills):
    """The letter for a bill known by any of `bills` (its numbers, a renumbered bill's last first), or None:
    {"text", "url", "ocr", "kind"}."""
    if first not in _CACHE:
        _CACHE[first] = wanted(first)
    for b in bills:
        try:
            rec = json.load(open(os.path.join(folder(first), f"{b}.json"), encoding="utf-8"))
        except (OSError, ValueError):
            continue
        text = L.cut(_paras(rec))
        if text:
            return {"text": text, "url": rec.get("url", ""), "ocr": bool(rec.get("ocr")), "kind": _CACHE[first].get(b, "absolute")}
    return None
