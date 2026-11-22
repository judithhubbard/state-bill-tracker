#!/usr/bin/env python3
""""What it does" for Vermont's bills, from the Office of Legislative Counsel's own words on legislature.vermont.gov,
kept in data/vt/texts_raw.json for states/vt/convert.py (`what()`).

- Every bill as introduced opens with Legislative Counsel's "Statement of purpose of bill as introduced: This bill
  proposes to ..." (above the title, page 1 of "H-0091 As Introduced.pdf"; committee bills too). LegiScan's record of
  each bill links that PDF (its "Introduced" text's state_link), so no status page is read.
- Each Act has Legislative Counsel's "Act Summary" ("ACT044 Act Summary.pdf", beside "ACT044 As Enacted.pdf", the
  Chaptered text LegiScan links), describing the act as passed; a vetoed bill whose veto stands has a "Vetoed Bill
  Summary" ("H-0091 Vetoed Bill Summary.pdf", in the bill's folder). These are preferred where they exist. Summaries are
  written weeks after the act: a missing one (404) is asked again a week later, for a year.

robots.txt (read 2026-11-22) asks for 30 seconds between requests ("Crawl-delay: 30") and bars only four status-page
loaders (/bill/loadBillDetailedStatus/ and the like); /Documents/ is allowed. So a run reads one PDF every 30 seconds,
for --minutes (default 8, so the LegiScan job stays in the quick lane): about 16 a run. Each PDF is read once (its
parsed text is kept, not the file). Order: act summaries, veto summaries, then the statements of laws, of bills that
passed a house, then the rest, newest session first and the latest action first. A refusal (403, 429, 503) or three
failed requests stop the run; what was read is kept, and the next run goes on.

Usage: python3 states/vt/texts.py [--minutes 8] [--limit N]
"""
import argparse, json, os, re, subprocess, sys, tempfile, time, urllib.error, urllib.request
from datetime import date, timedelta

HERE = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from states import legiscan_convert as L
from states.vt import profile as P

AGENT = "statebilltracker.org (a nonprofit bill tracker; contact via github.com/judithhubbard)"
PATH = os.path.join(P.DATA, "texts_raw.json")
GAP = 30.5
RETRY_DAYS = 7
LABEL = {
    "act": "From the Office of Legislative Counsel's summary of the act.",
    "veto": "From the Office of Legislative Counsel's summary of the vetoed bill.",
    "intro": "From the Office of Legislative Counsel's statement of purpose of the bill as introduced.",
}


def docs_for(b):
    """[(kind, url)] for a LegiScan bill record, best first: the act summary (laws), the vetoed bill summary (vetoes
    that stand), the bill as introduced."""
    from states.vt import convert as C
    out = []
    texts = b.get("texts") or []
    enacted = next((t.get("state_link") for t in texts if t.get("type") == "Chaptered"
                    and re.search(r"/ACTS/ACTM?\d+/ACTM?\d+%20As%20Enacted\.pdf$", t.get("state_link") or "")), None)
    intro = next((t.get("state_link") for t in texts if t.get("type") == "Introduced"
                  and re.search(r"/BILLS/[HS]-\d+/[HS]-\d+%20As%20Introduced\.pdf$", t.get("state_link") or "")), None)
    if enacted:
        out.append(("act", enacted.replace("%20As%20Enacted.pdf", "%20Act%20Summary.pdf")))
    elif intro:
        steps = [x for line in C.classify(b) for x in line]
        overridden = {x[0] for x in steps if x[1] == "override"} >= {"S", "H"}
        if any(x[1] == "veto" for x in steps) and not overridden:
            out.append(("veto", intro.replace("%20As%20Introduced.pdf", "%20Vetoed%20Bill%20Summary.pdf")))
    if intro:
        out.append(("intro", intro))
    return out


def read():
    return L.read_json(PATH, {}) or {}


def save(cache):
    tmp = PATH + ".tmp"
    with open(tmp, "w") as f:
        json.dump(cache, f, indent=0, sort_keys=True, ensure_ascii=False)
    os.replace(tmp, PATH)


def what(b, cache):
    """("What it does" paragraphs joined by "\n", label) for a bill, from what's been read, or None."""
    for kind, url in docs_for(b):
        x = cache.get(url)
        if x and x.get("text"):
            return "\n".join(x["text"]), LABEL[kind]
    return None


# ---- Reading the PDFs ----

def pdf_text(data, layout=False):
    with tempfile.NamedTemporaryFile(suffix=".pdf") as f:
        f.write(data)
        f.flush()
        args = ["pdftotext"] + (["-layout"] if layout else []) + ["-enc", "UTF-8", f.name, "-"]
        return subprocess.run(args, capture_output=True, text=True).stdout


def tidy(s):
    s = s.replace("­", "").replace("ﬁ", "fi").replace("ﬂ", "fl").replace(" ", " ")
    s = re.sub(r"(\w)- (\w)", lambda m: m.group(1) + "-" + m.group(2) if m.group(2)[0].isupper() else m.group(1) + m.group(2), s)
    return re.sub(r"\s+", " ", s).strip()


def statement(data):
    """The statement of purpose from a bill as introduced, as one paragraph ([] when it has none)."""
    text = pdf_text(data, layout=True)
    m = re.search(r"Statement of purpose(?: of (?:the )?bill as introduced)?\s*:\s*", text, re.I)
    if not m:
        return []
    out = []
    for line in text[m.end():].splitlines():
        line = re.sub(r"^\s*\d{1,2}(?:\s{2,}|$)", "", line).strip()   # the page's line numbers
        if not line:
            continue
        if re.match(r"(?:BILL AS INTRODUCED|VT LEG #|\d{4}\s+Page \d+ of \d+$|Page \d+ of \d+$|[HS]\.\d+$)", line):
            continue
        if re.match(r"(?:An act |It is hereby enacted|Sec\. 1\.)", line):
            break
        out.append(line)
    s = tidy(" ".join(out))
    return [s] if s else []


def summary(data):
    """The body of an Act Summary or a Vetoed Bill Summary, as paragraphs (the disclaimer, title, subjects, effective
    date and footer left out)."""
    raw = [l.rstrip() for l in pdf_text(data).splitlines()]
    lines = [l for l in raw if l.strip() and not re.match(
        r"\s*(?:Act No\. M?-?\d+|[HS]\.\d+ \(Vetoed\)|\d{4}|Page \d+ of \d+|VT LEG #.*)\s*$", l)]
    start = next((i for i, l in enumerate(lines) if l.startswith("Subjects:")), None)
    if start is None:
        start = next((i for i, l in enumerate(lines) if re.match(r"(?:Act No\. M?-?\d+ \(|[HS]\.\d+ \(Vetoed\)\.)", l)), None)
    if start is None:
        return []
    i = start + 1
    # The subjects (or title) line wraps: its continuation starts in lower case or follows a ";" or a short word.
    while i < len(lines) and (lines[i][:1].islower() or re.search(r"(?:[;,]|\b(?:for|of|and|the|to|in|on|a|an|or))$", lines[i - 1])):
        i += 1
    body = []
    for l in lines[i:]:
        if re.match(r"(?:Effective [Dd]ates?:|Multiple effective dates|Vetoed by the Governor:|Veto (?:sustained|overridden)|"
                    r"Became law without|This act summary is provided|This summary is of a bill)", l):
            break
        body.append(l)
    if not body:
        return []
    width = max(len(l) for l in body)
    paras, cur = [], []
    for l in body:
        cur.append(l)
        if re.search(r"[.:;)\"”]$", l) and len(l) < 0.85 * width:
            paras.append(tidy(" ".join(cur)))
            cur = []
    if cur:
        paras.append(tidy(" ".join(cur)))
    return [p for p in paras if p]


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": AGENT, "Accept": "application/pdf"})
    with urllib.request.urlopen(req, timeout=90) as r:
        return r.read()


# ---- The queue ----

def queue(cache, today):
    """[(kind, url)] still to read, in order."""
    from states.vt import convert as C
    from states import window as W
    rows = []
    for session, folder in sorted(C.RULES.session_folders().items(), reverse=True):
        if session + 1 < W.first_year():
            continue
        for b in L.bills(folder):
            if C.RULES.include(b) != "bill":
                continue
            last = max([(a.get("date") or "") for a in b.get("history") or []] or [""])
            docs = docs_for(b)
            kinds = [k for k, _ in docs]
            status = b.get("status") or 0
            for kind, url in docs:
                x = cache.get(url)
                if x and (x.get("text") is not None and x.get("code") == 200):
                    continue
                if x and x.get("code") != 200:
                    # Not there yet (404) or no statement in it: asked again a week later, while the bill is in the
                    # window and its last action less than a year old (the summaries come weeks after the act).
                    if x.get("read", "") > (date.fromisoformat(today) - timedelta(days=RETRY_DAYS)).isoformat():
                        continue
                    if last and last < (date.fromisoformat(today) - timedelta(days=400)).isoformat():
                        continue
                if kind == "intro" and any(cache.get(u, {}).get("text") for k, u in docs if k != "intro"):
                    continue  # a summary is in: the statement isn't needed
                rank = {"act": 0, "veto": 1}.get(kind)
                if rank is None:
                    rank = 2 if "act" in kinds else 3 if ("veto" in kinds or status >= 2) else 4
                rows.append(((rank, -session, "".join(chr(0x10ffff - ord(c)) for c in last)), kind, url))
    rows.sort(key=lambda r: r[0])
    return [(k, u) for _, k, u in rows]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--minutes", type=float, default=8)
    ap.add_argument("--limit", type=int, default=0, help="read at most this many PDFs (for testing)")
    a = ap.parse_args()
    stop = time.time() + a.minutes * 60
    today = date.today().isoformat()
    cache = read()
    todo = queue(cache, today)
    print(f"vt texts: {len(todo)} documents to read", file=sys.stderr)
    n = got = errors = 0
    last = 0.0
    for kind, url in todo:
        if time.time() + GAP > stop or (a.limit and n >= a.limit):
            break
        time.sleep(max(0.0, last + GAP - time.time()))
        last = time.time()
        try:
            data = get(url)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                cache[url] = {"code": 404, "read": today}
                n += 1
                continue
            print(f"vt texts: {url}: HTTP {e.code}", file=sys.stderr)
            errors += 1
            if e.code in (403, 429, 503) or errors >= 3:
                break
            continue
        except Exception as e:
            print(f"vt texts: {url}: {e}", file=sys.stderr)
            errors += 1
            if errors >= 3:
                break
            continue
        n += 1
        try:
            paras = statement(data) if kind == "intro" else summary(data)
        except Exception as e:
            print(f"vt texts: {url}: can't read it ({e})", file=sys.stderr)
            paras = []
        # A PDF with nothing to show is asked again later, like a missing one.
        cache[url] = {"code": 200 if paras else 204, "read": today, "text": paras}
        got += bool(paras)
        if n % 10 == 0:
            save(cache)
    save(cache)
    print(f"vt texts: read {n} documents ({got} with text); {max(0, len(todo) - n)} left for later runs", file=sys.stderr)


if __name__ == "__main__":
    main()
