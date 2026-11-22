#!/usr/bin/env python3
"""Utah governor's veto letters (vetoes and line-item vetoes), from two official places, both found without a table:

- The Legislature's copy of a bill's letter, le.utah.gov/~<year>/veto/<HB0003>.veto.pdf (SB0296 and SB0037 of 2025,
  HB0003 of 2024 and 2025), for each bill whose history has "Governor Vetoed" (GVETO) or "Governor Line Item Veto"
  (GOVLVETO). robots.txt allows /~<year>/ (Crawl-delay 10). Not every veto has one: the governor's last letter of a
  session often covers several bills (2025's HB 306, HB 315, SB 106, SB 197; all of 2026's), and those aren't there.
- The Legislature's copy of a letter on several bills, le.utah.gov/~<year>/veto/VetoLetter.pdf (2024's, scanned: read
  by OCR, approved by the owner 2026-11-22; 2025's).
- The governor's own copies, posted to governor.utah.gov's media library (robots.txt: only /wp-admin/ barred,
  Crawl-delay 10), found by its WordPress search, /wp-json/wp/v2/media?search=veto ("2026 Veto Letter (1)", "2026 Line
  Item Veto Letters", "2_2025 Veto Letter - Veto_No Sign_Other"). messages() picks each bill's part of such a letter.

fetch() reads each letter once (states/letters.py's scanned(): its own text, else OCR) into data/ut/<year>/vetoes/
(<HB0003>.json for the Legislature's, gov-<file name>.json for the governor's); a bill with no letter at le.utah.gov is
asked again at most weekly (misses.json), the governor's list at most daily while a vetoed bill of the window has no
letter. Ten seconds between requests to each site. Never holds the run back.
Usage: python3 states/ut/vetoes.py
"""
import glob, json, os, re, sys, time, urllib.error, urllib.request
from datetime import date, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
from states import letters as L
from states import window as W

DATA = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "ut"))
AGENT = "statebilltracker.org (a nonprofit bill tracker; contact via github.com/judithhubbard)"
GOV_MEDIA = "https://governor.utah.gov/wp-json/wp/v2/media?search=veto&per_page=100&_fields=date,source_url"
TODAY = date.today().isoformat()
KINDS = {"GVETO": "absolute", "GOVLVETO": "line-item"}


def folder(year):
    return os.path.join(DATA, str(year), "vetoes")


def _get(url):
    """Bytes, or None (404 and failures alike); ten seconds before each request (both sites' Crawl-delay)."""
    time.sleep(10)
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": AGENT}), timeout=90) as r:
            return r.read()
    except (urllib.error.URLError, OSError):
        return None


def vetoed(year):
    """{"HB0306": "absolute" | "line-item"}: the year's bills the governor vetoed, in whole or in part."""
    out = {}
    for f in glob.glob(os.path.join(DATA, str(year), "bills", "*.json")):
        try:
            b = json.load(open(f))
        except (OSError, ValueError):
            continue
        # (2024's records are older: "actionhistory", wording and no codes.)
        for a in b.get("actionHistoryList") or b.get("actionhistory") or []:
            code = a.get("actionCode") or ""
            desc = (a.get("description") or a.get("action") or "").strip().lower()
            kind = KINDS.get(code) or ("line-item" if "line item veto" in desc else "absolute" if desc == "governor vetoed" else None)
            if kind:
                out[os.path.basename(f)[:-5]] = kind
    return out


def _load(path, default):
    try:
        return json.load(open(path))
    except (OSError, ValueError):
        return default


def _save(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path + ".tmp", "w") as f:
        json.dump(obj, f)
    os.replace(path + ".tmp", path)


def fetch(years, minutes=10):
    stop = time.time() + minutes * 60
    lacking = {}
    for year in years:
        f = folder(year)
        misses = _load(os.path.join(f, "misses.json"), {})
        for bill in sorted(vetoed(year)):
            if os.path.exists(os.path.join(f, f"{bill}.json")):
                continue
            if misses.get(bill, "") > (date.today() - timedelta(days=7)).isoformat() or time.time() > stop:
                lacking.setdefault(year, []).append(bill)
                continue
            got = L.scanned(f, bill, f"https://le.utah.gov/~{year}/veto/{bill}.veto.pdf", _get)
            if got is None:
                misses[bill] = TODAY
                lacking.setdefault(year, []).append(bill)
        # The Legislature's copy of the governor's last letter of the session, on several bills (2024's, 2025's).
        if lacking.get(year) and not os.path.exists(os.path.join(f, "leg-VetoLetter.json")) and time.time() < stop \
                and misses.get("VetoLetter", "") <= (date.today() - timedelta(days=7)).isoformat():
            if L.scanned(f, "leg-VetoLetter", f"https://le.utah.gov/~{year}/veto/VetoLetter.pdf", _get) is None:
                misses["VetoLetter"] = TODAY
        if misses:
            _save(os.path.join(f, "misses.json"), misses)
    # The governor's copies: only while a veto has no letter of its own.
    state = os.path.join(DATA, "gov_vetoes.json")
    seen = _load(state, {"checked": ""})
    if not lacking or seen["checked"] == TODAY or time.time() > stop:
        print(f"veto letters: {sum(len(v) for v in lacking.values())} vetoes with no letter of their own", flush=True)
        return
    body = _get(GOV_MEDIA)
    try:
        media = json.loads(body) if body else None
    except ValueError:
        media = None
    if not isinstance(media, list):
        print("veto letters: the governor's media list failed; tried again next run", flush=True)
        return
    got = 0
    for m in media:
        url, year = m.get("source_url") or "", int((m.get("date") or "0")[:4] or 0)
        if year not in lacking or not url.lower().endswith(".pdf") or time.time() > stop:
            continue
        key = "gov-" + re.sub(r"[^A-Za-z0-9_.-]", "_", url.rsplit("/", 1)[-1][:-4])
        if os.path.exists(os.path.join(folder(year), f"{key}.json")):
            continue
        if L.scanned(folder(year), key, url, _get):
            got += 1
    seen["checked"] = TODAY
    _save(state, seen)
    print(f"veto letters: {got} of the governor's letters read now", flush=True)


# ---- reading them ---------------------------------------------------------------------------------------------------
CITE = re.compile(r"\b(?:([HS])\.\s?B\.\s?|([HS])B\s?|(House|Senate) Bill\s)(?:No\.\s*)?0*(\d+)\b")
# ("Dear Speaker Schultz, President Adams, and Members of the Legislature,"; SB 37 of 2025's has no "Dear".)
_SALUTE = re.compile(r"^\s*(?:Dear )?(?:Speaker|President|Members|Senators|Representatives)\b.*[,:]\s*$")
_CLOSE = re.compile(r"^\s*(?:Sincerely|Respectfully|Warm regards|Kind regards)\b", re.I)
# A section of a letter covering several bills ends at a turn to something else.
_TURN = re.compile(r"^(?:There (?:are|is|were)|As I mentioned|I am also|I(?:'|’)m also|Thank you|Finally|Lastly|Additionally, I"
                   r"|In addition, I|I am allowing|I have also|I also)\b")


def _paras(raw, ocr):
    """A letter's text -> its paragraphs, from after the salutation to the closing."""
    if ocr:
        # (A scanned list's bullets read as "e": "e Item 33, lines 400-405.")
        return [re.sub(r"^[e®°•]\s+(?=Item \d)", "● ", p) for p in L.ocr_letter(raw, governor="Spencer J. Cox")]
    lines = raw.replace("\f", "\n").split("\n")
    start = next((i + 1 for i, t in enumerate(lines) if _SALUTE.match(t)), 0)
    out, cur = [], []
    for t in lines[start:] + [""]:
        if _CLOSE.match(t):
            break
        if re.fullmatch(r"\s*\d{1,2}\s*", t):  # a page number
            continue
        if not t.strip():
            if cur:
                out.append(re.sub(r"\s+", " ", " ".join(cur)).strip())
                cur = []
            continue
        cur.append(t.strip())
    if cur:
        out.append(re.sub(r"\s+", " ", " ".join(cur)).strip())
    # A paragraph split by a page break joins up again.
    joined = []
    for p in out:
        if joined and not re.search(r"[.:!?;\"”)]$", joined[-1]) and re.match(r"[a-z(]", p):
            joined[-1] += " " + p
        else:
            joined.append(p)
    return joined


def _cites(p):
    return [(m.group(1) or m.group(2) or m.group(3)[0]) + "B" + m.group(4) for m in CITE.finditer(p)]


def section(paras, bill, title=""):
    """The paragraphs of a letter on several bills that are about `bill` ("HB164"): from the first that names it (not a
    bullet of a line-item list, for an absolute veto) to a paragraph turning to another bill or topic, at most five."""
    out = []
    for i, p in enumerate(paras):
        # (Or its number and short title: 2024's scanned list reads "2, Jub 239 State Employee Cybersecurity ...".)
        named = bill in _cites(p) or (len(title) > 8 and title.lower() in p.lower()
                                      and re.search(rf"\b{re.sub(r'\D', '', bill)}\b", p))
        if named and not p.startswith("●"):
            for q in paras[i:i + 5]:
                if out:
                    c = _cites(q)
                    # (Another bill, a turn to something else, or the next item of a numbered list: "3. HB 412 ...".)
                    if not q.startswith("●") and ((c and bill not in c) or _TURN.match(q) or re.match(r"\d{1,2}[.,] ", q)):
                        break
                    if out[-1].startswith("●") and not q.startswith("●"):
                        break
                out.append(q)
                last = re.split(r"(?<=[.!?])\s+", out[-1])[-1]
                if re.search(r"\bveto", last, re.I) and bill in _cites(last) and not last.endswith(":"):
                    break  # "For this reason, I have vetoed H.B. 462."
            # A numbered list's heading isn't part of the reasons: "6. HB 144 Vehicle Accident Liability Amendments".
            if title and out:
                out[0] = re.sub(rf"^\d{{1,2}}[.,]\s+\S{{1,4}}\s?\d+\s+{re.escape(title)}\s*", "", out[0], flags=re.I) or out[0]
            return out
    return out


def messages(year):
    """{"HB306": {"text", "url", "ocr", "kind"}} for the year's vetoes and line-item vetoes that have a letter."""
    out = {}
    f = folder(year)
    gov = []
    for path in sorted(glob.glob(os.path.join(f, "leg-*.json"))) + sorted(glob.glob(os.path.join(f, "gov-*.json"))):
        rec = _load(path, {})
        if rec.get("raw"):
            gov.append((rec, _paras(rec["raw"], rec.get("ocr"))))
    titles = {}
    for padded in vetoed(year):
        b = _load(os.path.join(DATA, str(year), "bills", f"{padded}.json"), {})
        titles[padded] = (b.get("shortTitle") or b.get("shorttitle") or "").strip()
    for padded, kind in vetoed(year).items():
        bill = re.sub(r"(?<=[A-Z])0+(?=\d)", "", padded)
        rec = _load(os.path.join(f, f"{padded}.json"), {})
        paras = _paras(rec["raw"], rec.get("ocr")) if rec.get("raw") else []
        if paras:
            out[bill] = {"text": L.cut(paras), "url": rec["url"], "ocr": bool(rec.get("ocr")), "kind": kind}
            continue
        # The governor's letters: the one naming the bill in its own section (a veto's, before a list of line items).
        for g, ps in gov:
            part = section(ps, bill, titles.get(padded, ""))
            if part:
                out[bill] = {"text": L.cut(part), "url": g["url"], "ocr": bool(g.get("ocr")), "kind": kind}
                break
    return out


if __name__ == "__main__":
    ys = W.years()
    try:
        fetch(ys, minutes=20)
    except Exception as e:  # noqa: BLE001
        print(f"veto letters: failed ({type(e).__name__}: {e})")
    for y in ys:
        for b, m in sorted(messages(y).items()):
            print(y, b, m["kind"], "OCR" if m["ocr"] else "", m["url"].rsplit("/", 1)[-1], "|", m["text"][:200].replace("\n", " | "))
