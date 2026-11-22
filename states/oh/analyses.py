#!/usr/bin/env python3
"""The Legislative Service Commission's bill analyses, for "What it does" (added 2026-11-22).

Each bill's documents page on www.legislature.ohio.gov (/legislation/136/hb13/documents; robots.txt: "User-agent: *",
"Disallow:") lists its analyses by version ("As Introduced", "As Passed By House", ..., "Final Analysis" for a law), each
a PDF at /download?key=<n>. fetch() reads the page and the newest analysis (the final one when there is one), keeps the
part of its text that summarizes the bill (the SUMMARY's bullets, else the DETAILED ANALYSIS's opening) in
data/oh/<session>/analyses.json, and texts.py turns it into paragraphs (read(), so a better parser needs no new reads).

Bounded: at most REQUESTS requests and MINUTES minutes a run, GAP seconds apart; laws first, then bills that moved,
the newest General Assembly first. A bill is read again only when its versions change (and every 7 days for 30 days
after, while the new version's analysis is being written), or, with none found, after 60 days. A 403 or 429 stops
the run's reading; the last copies stand. Needs pdftotext (poppler-utils). Never fails the run: fetch.py wraps it.
www.legislature.ohio.gov doesn't send Sectigo's "OV R36" intermediate certificate, so it's fetched from Sectigo and
added to the trusted ones for these requests (the connection is still fully checked).
"""
import json, os, re, ssl, subprocess, sys, time, urllib.error, urllib.request
from datetime import date, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
from states.oh import profile as P

SITE = "https://www.legislature.ohio.gov"
INTERMEDIATE = "http://crt.sectigo.com/SectigoPublicServerAuthenticationCAOVR36.crt"
SYSTEM_CAS = ["/etc/ssl/certs/ca-certificates.crt", "/etc/ssl/cert.pem", "/etc/pki/tls/certs/ca-bundle.crt"]
CA = os.path.join(P.DATA, "sectigo_r36.pem")
REQUESTS, MINUTES, GAP = 160, 8, 2
MAX_PDF = 20_000_000  # bytes; the budget bills' analyses run to hundreds of pages
PAGES = 12  # the summary is in a long analysis's first pages
RAW = 20_000  # characters of the summary kept
AGENT = "statebilltracker.org (a nonprofit bill tracker; contact via github.com/judithhubbard)"


class Refused(Exception):
    pass


def context():
    if not (os.path.exists(CA) and time.time() - os.path.getmtime(CA) < 30 * 86400):
        with urllib.request.urlopen(urllib.request.Request(INTERMEDIATE, headers={"User-Agent": AGENT}), timeout=60) as r:
            pem = ssl.DER_cert_to_PEM_cert(r.read())
        open(CA + ".tmp", "w").write(pem)
        os.replace(CA + ".tmp", CA)
    system = next((p for p in SYSTEM_CAS if os.path.exists(p)), None)
    ctx = ssl.create_default_context(cafile=system)
    ctx.load_verify_locations(cafile=CA)
    return ctx


def get(url, ctx, limit=None):
    """The body, None when it isn't there (404, too big), False when it failed, Refused on 403/429."""
    time.sleep(GAP)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": AGENT})
        with urllib.request.urlopen(req, timeout=120, context=ctx) as r:
            if limit and int(r.headers.get("Content-Length") or 0) > limit:
                return None
            return r.read()
    except urllib.error.HTTPError as e:
        if e.code in (403, 429):
            raise Refused(f"{url} answered {e.code}")
        return None if e.code in (404, 410) else False
    except Exception:
        return False  # asked again next run


def analyses(page):
    """[(label, key)] from a documents page's Analysis section, as listed (newest first)."""
    sec = re.search(r"<h2[^>]*>\s*Analysis\s*</h2>(.*?)</section>", page, re.S)
    return re.findall(r'href="[^"]*download\?key=(\d+)"[^>]*>\s*<span>([^<]+)</span>', sec.group(1)) if sec else []


def choose(found):
    """The final analysis when there is one, else the newest."""
    found = [(k, re.sub(r"\s+", " ", l).strip()) for k, l in found]
    return next((x for x in found if re.match(r"Final\b", x[1], re.I)), found[0] if found else None)


def pdf_text(body):
    r = subprocess.run(["pdftotext", "-layout", "-l", str(PAGES), "-", "-"], input=body, capture_output=True)
    return r.stdout.decode("utf-8", "replace") if r.returncode == 0 else ""


def excerpt(text):
    """The version line and the summary's lines (layout kept: read() uses the indents), else the detailed analysis's
    opening; "" when neither is there."""
    lines = text.split("\n")
    version = next((re.sub(r"\s+", " ", m.group(1)).strip() for l in lines[:40]
                    for m in [re.match(r"\s*Version:\s*(.+)", l)] if m), "")
    strip = [l.strip() for l in lines]
    start = next((i for i, l in enumerate(strip) if l in ("SUMMARY", "HIGHLIGHTS")), None)
    kind = "summary"
    if start is None:
        start, kind = next((i for i, l in enumerate(strip) if l == "DETAILED ANALYSIS"), None), "detail"
    if start is None:
        return {"version": version, "kind": "", "raw": ""}
    end = next((i for i in range(start + 1, len(strip)) if strip[i] in ("DETAILED ANALYSIS", "HISTORY", "TABLE OF CONTENTS")
                or (kind == "detail" and strip[i] in ("COMMENT", "HISTORY"))), len(strip))
    return {"version": version, "kind": kind, "raw": "\n".join(lines[start + 1:end])[:RAW]}


# ---- From the excerpt to paragraphs (no requests) ----

DATE = re.compile(r"^(January|February|March|April|May|June|July|August|September|October|November|December) \d{1,2}, \d{4}$")
FURNITURE = re.compile(r"^(Office of Research and Drafting\b.*|P a g e \|.*|LSC|Legislative Budget Office|"
                       r"[HS]\.\s?(B|J\.\s?R|C\.\s?R|R)\.\s?\d+\*?|As (Introduced|Reported|Passed|Pending|Enrolled)\b.*|"
                       r"UPDATED VERSION.?)$")
FOOTNOTE = re.compile(r"^(\*||\d{1,3} [A-Z“(]|\d{1,3}$)")
BULLET, SUB = "▪", ""
FOOT_MARK = re.compile(r"(?<=[a-z’”)])\d{1,2}(?=[\s,.;:)]|$)")


def read(ex, title=""):
    """Paragraphs from an excerpt: each summary bullet one paragraph (its sub-items joined in), the summary's
    headings left out; for an analysis with no summary, its opening paragraphs when they say what the bill does."""
    if not ex or not ex.get("raw"):
        return []
    items, cur, skip, last_end = [], None, False, True  # cur: [text, kind]

    def close():
        nonlocal cur
        if cur and cur[0].strip():
            items.append(cur)
        cur = None

    for line in ex["raw"].split("\n"):
        s = line.strip()
        if not s:
            continue
        if DATE.match(s) or FURNITURE.match(s) or re.match(r"Click here for", s):
            skip = False
            continue
        indent = len(line) - len(line.lstrip())
        if skip:
            continue
        if FOOTNOTE.match(s) and indent <= 1 and not s.startswith(BULLET):
            skip = True  # a footnote, to the page's foot
            continue
        if s.startswith(BULLET):
            close()
            cur = [s[1:].strip(), "b"]
        elif s.startswith(SUB):
            if cur is None:
                cur = ["", "b"]
            t = s[1:].strip()
            if len(cur) == 2:
                cur.append(cur[0].rstrip().endswith(":"))  # a list of sub-items continuing the bullet's sentence
            if cur[2] and t[:1].isupper() and t[1:2].islower():
                t = t[0].lower() + t[1:]
            cur[0] += " " + t
        elif indent <= 4 and len(s) < 80 and not re.search(r"[.;:,]$", s) and (cur is None or last_end):
            close()  # a heading
        elif cur is None or (ex["kind"] == "detail" and indent >= 5 and last_end):
            close()
            cur = [s, "p"]
        else:
            cur[0] += ("" if cur[0].endswith("-") and not cur[0].endswith(" -") else " ") + s
        last_end = bool(re.search(r"[.;:]['’”)]*$", s))
    close()
    out = []
    for t, kind, *_ in items:
        t = FOOT_MARK.sub("", re.sub(r"\s+", " ", t)).strip()
        t = t.replace("�", "")
        if len(t) < 12:
            continue
        out.append(t)
    if ex["kind"] == "detail":
        # Only what says what the bill does ("The bill requires ..."), not background; two paragraphs at most.
        out = [t for t in out if re.search(r"[.)”’]$", t)]
        if not out or not re.match(r"(The|This) (bill|act|resolution|joint resolution)\b", out[0]):
            return []
        out = out[:2]
    if out and title and re.sub(r"\W+", " ", out[0]).strip().lower() == re.sub(r"\W+", " ", title).strip().lower():
        return []
    return out


def label(ex, doc, kind):
    """"From the Legislative Service Commission's analysis of the bill as passed by the House." """
    if re.match(r"Final\b", doc or "", re.I):
        return "From the Legislative Service Commission's final analysis."
    v = ex.get("version") or doc or ""
    v = re.sub(r"\s+", " ", v).strip().rstrip(".")
    m = re.match(r"As (Reported|Pending|Re-referred|Re-reported) (by|in) (the )?(House|Senate) (.+?)( Committee)?$", v, re.I)
    if m and not re.match(r"Committee$", m.group(5), re.I):
        v = f"as {m.group(1).lower()} {m.group(2).lower()} the {m.group(4).title()} {m.group(5)} Committee"
    elif m:
        v = f"as {m.group(1).lower()} {m.group(2).lower()} the {m.group(4).title()} committee"
    else:
        v = re.sub(r"^As\b", "as", v)
        v = re.sub(r"\b(by|in) (the )?(House|Senate)\b", lambda x: f"{x.group(1).lower()} the {x.group(3).title()}", v, flags=re.I)
        v = re.sub(r"\b(Passed|Introduced|Enrolled|Reported)\b", lambda x: x.group(1).lower(), v)
    return f"From the Legislative Service Commission's analysis of the {kind} {v}.".replace("  ", " ")


# ---- The download ----

def sig(versions):
    return " ".join(v.get("version_id") or "" for v in versions)


def fetch(sessions, today=None):
    """Reads what's due, within the run's caps (REQUESTS, MINUTES)."""
    import glob
    if subprocess.run(["sh", "-c", "command -v pdftotext"], capture_output=True).returncode:
        print("analyses: pdftotext isn't installed; skipped")
        return
    today = today or date.today()
    t0, n = time.time(), 0
    queue, stores = [], {}
    for session in sessions:
        folder = os.path.join(P.DATA, str(session))
        path = os.path.join(folder, "analyses.json")
        try:
            store = json.load(open(path))
        except (OSError, ValueError):
            store = {}
        stores[session] = (path, store)
        for f in glob.glob(os.path.join(folder, "bills", "*.json")):
            b = os.path.basename(f)[:-5]
            try:
                vers = json.load(open(f)).get("versions") or []
            except (OSError, ValueError):
                continue
            s, old = sig(vers), store.get(b) or {}
            if old.get("sig") != s:
                due, wait = True, 0
            else:
                since = (today - date.fromisoformat(old.get("changed") or old.get("read"))).days
                ago = (today - date.fromisoformat(old["read"])).days
                due = (since <= 30 and ago >= 7) or (not old.get("key") and ago >= 60)
                wait = 1
            if due:
                ids = s.split()
                rank = 0 if "EN" in ids else 1 if len(ids) > 1 else 2
                queue.append((wait, rank, -session, -len(ids), b, session, s))
    queue.sort()
    print(f"analyses: {len(queue)} bills due")
    if not queue:
        return
    ctx = context()
    got = failed = 0
    try:
        for wait, rank, _, _, b, session, s in queue:
            if n + 2 > REQUESTS or time.time() - t0 > MINUTES * 60:
                break
            path, store = stores[session]
            old = store.get(b) or {}
            page = get(f"{SITE}/legislation/{P.assembly_of(session)}/{b.lower()}/documents", ctx)
            n += 1
            if page is False:
                failed += 1
                if failed >= 5:
                    print("analyses: five failures; stopping")
                    break
                continue
            rec = {"sig": s, "changed": old.get("changed") if old.get("sig") == s else str(today), "read": str(today)}
            pick = choose(analyses(page.decode("utf-8", "replace"))) if page else None
            if pick and pick[0] == old.get("key"):
                rec.update({k: old[k] for k in ("key", "doc", "version", "kind", "raw") if k in old})
            elif pick:
                body = get(f"{SITE}/download?key={pick[0]}", ctx, MAX_PDF)
                n += 1
                if body is False or (body and not body.startswith(b"%PDF")):
                    failed += 1
                    continue  # asked again next run
                # None: gone or too big (a budget bill's); kept as read, with no summary, until the bill changes.
                rec.update({"key": pick[0], "doc": pick[1], **(excerpt(pdf_text(body)) if body else {})})
            store[b] = rec
            got += 1
            if got % 25 == 0:
                save(path, store)
    except Refused as e:
        print(f"analyses: {e}; stopping")
    for path, store in stores.values():
        save(path, store)
    print(f"analyses: {got} bills read ({n} requests), "
          + ", ".join(f"{s}: {sum(1 for v in st.values() if v.get('raw'))} of {len(st)} with a summary" for s, (p, st) in stores.items()))


def save(path, data):
    json.dump(data, open(path + ".tmp", "w"), ensure_ascii=False)
    os.replace(path + ".tmp", path)


if __name__ == "__main__":
    from states.oh import convert as C
    fetch(sorted(C.sessions(), reverse=True))
