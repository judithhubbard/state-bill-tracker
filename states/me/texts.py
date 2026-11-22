#!/usr/bin/env python3
""""What it does" for Maine: the SUMMARY the Legislature's drafters print at the end of each bill and each amendment, read
from the printed documents on legislature.maine.gov (getPDF.asp?paper=HP0207&item=1&snum=132: item 1 is the bill as
printed, later items its amendments; LegiScan's records give each document's address and a hash of its contents). Kept
in data/me/summaries.json ({document address: {"h": LegiScan's hash, "s": the summary, "d": the day it was read}}), which
states/me/convert.py's `what()` reads (legiscan_convert.py then writes texts_<session>.json; that file is rewritten by
every conversion, so the summaries live in their own file).

Which document: the committee amendment the bill was last passed to be engrossed with (its summary describes the bill
as amended: "This amendment replaces the bill, which is a concept draft, ..."); a floor amendment the bill was engrossed
with alone, when its summary says it replaces the bill; else the bill as printed. Floor amendments to a committee
amendment are left out (their summaries describe only their own change).

robots.txt (checked 2026-11-22) bars only the search pages and LawMakerWeb, with no crawl delay. Documents are read one
at a time, at least 1.5 seconds apart, only when not read yet or when LegiScan's hash of the document changed; laws
first, then bills that passed a house, then bills reported from committee, then the rest, the newest session first. A
run stops after --minutes (default 8), and on a refusal (403, 429, 503), three failed requests or ten slow answers in a
row, keeping what it has; the next run goes on from there. Needs pdftotext (poppler-utils).

Usage: python3 states/me/texts.py [--minutes 8]
"""
import argparse, json, os, re, subprocess, sys, tempfile, time, urllib.error, urllib.request
from datetime import date

HERE = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from states import legiscan_convert as L
from states import window as W
from states.me import profile as P

AGENT = "statebilltracker.org (a nonprofit bill tracker; contact via github.com/judithhubbard)"
PATH = os.path.join(P.DATA, "summaries.json")
GAP = 1.5
AMEND = re.compile(r'\b(Committee|House|Senate) Amendment "(\w+)" \(([HS])-(\d+)\)')
REPLACES = re.compile(r"^This amendment (?:replaces|strikes out .{0,80}?and replaces|strikes and replaces) the "
                      r"(?:bill|resolve|resolution)", re.I)


def documents(b):
    """[(address, hash, what it is, "amendment" or "bill")] to try for one LD, best first: the committee amendment (or a
    floor amendment alone) named in the bill's last "PASSED TO BE ENGROSSED" line, then the bill as printed."""
    out = []
    amends = {}
    for a in b.get("amendments") or []:
        m = re.search(r"\(([HS])-(\d+)\)", a.get("title") or "")
        if m and a.get("state_link"):
            amends[f"{m.group(1)}-{m.group(2)}"] = a
    last = None
    for h in b.get("history") or []:
        t = L.text(h.get("action"))
        i = t.upper().find("ENGROSSED")
        if i >= 0 and not re.search(r"\bRECONSIDER", t, re.I):
            named = AMEND.findall(t[i:])
            last = named
    if last:
        kind, letter, house, num = last[0]
        a = amends.get(f"{house}-{num}")
        if a:
            out.append((a["state_link"], a.get("amendment_hash") or "", f'{kind} Amendment "{letter}" ({house}-{num})',
                        "committee" if kind == "Committee" else "floor"))
    for t in b.get("texts") or []:
        if t.get("type") == "Introduced" and t.get("state_link"):
            out.append((t["state_link"], t.get("text_hash") or "", "", "bill"))
            break
    return out


def noun(b):
    t = L.text(b.get("title"))
    return "resolve" if re.match(r"Resolve\b", t, re.I) else "resolution" if re.match(r"RESOLUTION\b", t) else "bill"


def summary(pdf):
    """A printed bill's or amendment's PDF -> its SUMMARY as paragraphs joined by "\n" ("" when it has none)."""
    with tempfile.NamedTemporaryFile(suffix=".pdf") as f:
        f.write(pdf)
        f.flush()
        text = subprocess.run(["pdftotext", "-layout", f.name, "-"], capture_output=True, text=True).stdout
    return summary_text(text)


def summary_text(text):
    lines = text.replace("\f", "\n").split("\n")
    heads = [i for i, s in enumerate(lines) if re.fullmatch(r"\s*(?:\d{1,2}\s+)?SUMMARY\s*", s)]
    if not heads:
        return ""
    paras, cur = [], []
    for s in lines[heads[-1] + 1:]:
        # The end: the fiscal note's stamp, or a floor amendment's sponsor block ("SPONSORED BY: ____ (Senator ...)").
        if re.fullmatch(r"\s*(?:\d{1,2}\s+)?FISCAL NOTE REQUIRED\s*", s) or re.match(r"\s*\(See attached\)", s) \
                or re.match(r"\s*(?:\d{1,2}\s+)?SPONSORED BY:", s):
            break
        # Page footers ("Page 4 - 132LR1521(02)") and headers ("COMMITTEE AMENDMENT", 'COMMITTEE AMENDMENT "A" to H.P.
        # 207, L.D. 307'), and lines holding only a line number.
        if re.match(r"\s*Page \d+ - \d+LR\d+", s) or re.match(r"\s*(?:COMMITTEE|HOUSE|SENATE) AMENDMENT\b", s) \
                or re.fullmatch(r"\s*\d{0,2}\s*", s):
            continue
        m = re.match(r"\s*\d{1,2}(\s+)(\S.*)$", s)
        if not m:
            m = re.match(r"(\s*)(\S.*)$", s)
        indent, body = len(m.group(1)), re.sub(r"\s+", " ", m.group(2)).strip()
        # A paragraph's first line is indented further than the lines after it.
        if cur and indent >= 5:
            paras.append(cur)
            cur = []
        cur.append(body)
    if cur:
        paras.append(cur)
    out = []
    for p in paras:
        t = ""
        for piece in p:
            # A line ending in a hyphen is a hyphenated word or range broken there ("2022-" "2023"): the drafters' word
            # processor doesn't hyphenate words on its own.
            if re.search(r"\w-$", t):
                t = t + piece
            else:
                t = f"{t} {piece}".strip()
        t = t.replace("�", "").strip()
        if t:
            out.append(t)
    return "\n".join(out)


def read():
    return L.read_json(PATH, {}) or {}


def save(cache):
    tmp = PATH + ".tmp"
    with open(tmp, "w") as f:
        json.dump(cache, f, indent=0, sort_keys=True, ensure_ascii=False)
    os.replace(tmp, PATH)


_CACHE = None


def what(b, cache=None):
    """("What it does", "From the ...") for one LD from the summaries read so far, or None."""
    global _CACHE
    if cache is None:
        if _CACHE is None:
            _CACHE = read()
        cache = _CACHE
    title = re.sub(r"\W+", " ", L.text(b.get("title"))).strip().lower()
    for url, h, name, kind in documents(b):
        x = cache.get(url)
        s = (x or {}).get("s") or ""
        if not s or re.sub(r"\W+", " ", s).strip().lower() == title:
            continue
        if kind == "floor" and not REPLACES.search(s):
            continue
        if kind == "bill":
            return s, f"From the drafters' summary printed with the {noun(b)} as introduced."
        return s, f"From the drafters' summary of {name}, which describes the {noun(b)} as amended."
    return None


def queue(cache):
    """[(address, hash)] to read, best first: laws, then bills that passed a house, then bills reported out of committee,
    then the rest; the newest session first; within those, the latest action first. A bill's best document comes first
    and the next one only once the best has been read and has no usable summary."""
    from states.me import convert as C
    rows = []
    for session in sorted(C.sessions(), reverse=True):
        if session + 1 < W.first_year():
            continue
        for b in L.bills(C.RULES.session_folders()[session]):
            if not C.RULES.include(b):
                continue
            if what(b, cache):
                continue
            kinds = {k for line in C.decode_bill(b, "bill", {}) for _, k, _, _ in line}
            rank = 0 if "chapter" in kinds else 1 if "pass" in kinds else 2 if "report" in kinds else 3
            for url, h, name, kind in documents(b):
                x = cache.get(url)
                if x and (x.get("h") == h or not h):
                    continue  # read already (no usable summary there): try the next document
                rows.append((rank, -session, (b.get("status_date") or b.get("last_action_date") or ""), url, h))
                break
    rows.sort(key=lambda r: r[2], reverse=True)
    rows.sort(key=lambda r: (r[0], r[1]))
    seen, out = set(), []
    for r in rows:
        if r[3] not in seen:
            seen.add(r[3])
            out.append((r[3], r[4]))
    return out


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": AGENT, "Accept": "application/pdf"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--minutes", type=float, default=8)
    a = ap.parse_args()
    stop = time.time() + a.minutes * 60
    today = date.today().isoformat()
    cache = read()
    rounds = n = found = 0
    last, wait, slow, errors = 0.0, GAP, 0, 0
    # Each round reads the best documents not read yet; a bill whose best had no summary is queued again in the next
    # round with its next document (the bill as printed).
    while time.time() < stop and errors < 3 and slow < 10 and rounds < 3:
        todo = queue(cache)
        rounds += 1
        print(f"me texts: {len(todo)} documents to read", file=sys.stderr)
        if not todo:
            break
        refused = False
        for url, h in todo:
            if time.time() > stop:
                break
            time.sleep(max(0.0, last + wait - time.time()))
            last = time.time()
            try:
                pdf = get(url)
            except urllib.error.HTTPError as e:
                print(f"me texts: {url}: HTTP {e.code}", file=sys.stderr)
                errors += 1
                if e.code in (403, 429, 503) or errors >= 3:
                    refused = True
                    break
                continue
            except Exception as e:
                print(f"me texts: {url}: {e}", file=sys.stderr)
                errors += 1
                if errors >= 3:
                    break
                continue
            took = time.time() - last
            wait = max(GAP, took)
            slow = slow + 1 if took > 10 else 0
            n += 1
            try:
                s = summary(pdf) if pdf[:4] == b"%PDF" else ""
            except Exception as e:
                print(f"me texts: {url}: {e}", file=sys.stderr)
                s = ""
            cache[url] = {"h": h, "s": s, "d": today}
            found += bool(s)
            if n % 25 == 0:
                save(cache)
            if slow >= 10:
                print("me texts: the site is answering slowly; stopping for this run", file=sys.stderr)
                break
        save(cache)
        if refused:
            break
    print(f"me texts: read {n} documents ({found} with a summary)", file=sys.stderr)


if __name__ == "__main__":
    main()
