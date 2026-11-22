#!/usr/bin/env python3
"""House Research's plain summaries from the Legislative Update (states/sc/NOTES.md, "Summaries").

The House Office of Research writes the Legislative Update each week of the session, plus issues on prefiled bills,
bills the House passed and each year's Acts (www.scstatehouse.gov/reports/hupdate/session-126/<name>.htm: Word pages in
Windows-1252, 1-7 MB). Its Bill Summary Index (https://legislativeupdates.scstatehouse.gov/api/BillSummaryIndex/126, the
JSON the public page hupdate.php reads) lists each bill it has summarized with the issues and dates: 1,669 bills of
2025-26 in 35 issues on 2026-11-22. (The 125th's index is empty: 2023-24 has none.)

Requests (3 seconds apart, a plain User-Agent; www.scstatehouse.gov's robots.txt bars only /images/, /jpeg/, /gif/,
/dashboard/ and /sys/; legislativeupdates.scstatehouse.gov has no robots.txt): the index once a day, then each issue it
names once, and again when the index gives it a later date than when it was read (an issue revised in place: "House
passed bills", "Acts 2026 (FINAL)"). Writes <folder>/updates/: index.json, the issues (<name>.htm), read.json ({url:
{"read", "date"}}) and summaries.json ({bill: [date, issue name, summary]}: each bill's latest issue that has a paragraph
on it, the Acts issue after a law's enactment). convert.py reads summaries.json.

Usage: python3 states/sc/updates.py <session number> <folder>   (as fetch.py calls it: 126 data/sc/2025)
"""
import html, json, os, re, sys, time, urllib.error, urllib.parse, urllib.request
from datetime import datetime, timezone

INDEX = "https://legislativeupdates.scstatehouse.gov/api/BillSummaryIndex/{}"
AGENT = "statebilltracker.org (a nonprofit bill tracker; contact via github.com/judithhubbard)"
DELAY = 3
LAST = [0.0]


def get(url):
    wait = LAST[0] + DELAY - time.time()
    if wait > 0:
        time.sleep(wait)
    LAST[0] = time.time()
    parts = urllib.parse.urlsplit(url)
    url = urllib.parse.urlunsplit(parts._replace(path=urllib.parse.quote(parts.path)))
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": AGENT}), timeout=120) as r:
            return r.read()
    except (urllib.error.URLError, OSError) as e:
        print(f"legislative update: {url}: {e}", flush=True)
        return None


def paragraphs(page):
    """A Word page's paragraphs as (class, text): inline tags dropped without a space (Word splits words into spans:
    "decedent<span>'</span>s"), the source's own line breaks collapsed, the table of contents and index left out."""
    page = re.sub(r"(?is)<(script|style|xml|head)\b.*?</\1>", "", page)
    page = re.sub(r"(?is)<!--.*?-->", "", page)
    out = []
    for m in re.finditer(r"(?is)<(p|h[1-6])\b([^>]*)>(.*?)</\1>", page):
        cls = (re.search(r"class=\"?([\w-]+)", m[2]) or [None, ""])[1]
        if re.match(r"MsoToc|MsoIndex|MsoTitle", cls):
            continue
        t = re.sub(r"\s+", " ", m[3])
        t = re.sub(r"<br[^>]*>", " ", t, flags=re.I)
        t = html.unescape(re.sub(r"<[^>]+>", "", t)).replace("\xa0", " ").replace("‑", "-")
        t = re.sub(r"\s+", " ", t).strip()
        t = re.sub(r"\s+([,.;:)])", r"\1", t)
        if t and "PAGEREF" not in t:
            out.append((cls if not m[1].lower().startswith("h") else "Heading", t))
    return out


BILL = re.compile(r"^([HS])\.\s?(\d{1,4})\b")
ACT_HEAD = re.compile(r"\(([HS])\.\s?(\d{1,4})(?:,\s*A\.\s*\d+)?\s*\)$")


def title_case(t):
    words = re.findall(r"[A-Za-z][A-Za-z'’-]*", t)
    small = {"a", "an", "and", "as", "at", "by", "for", "from", "in", "of", "on", "or", "the", "to", "with"}
    big = [w for w in words if w.lower() not in small]
    return bool(big) and sum(w[0].isupper() for w in big) >= 0.75 * len(big)


def heading(cls, t):
    """The bill a paragraph heads, or None: "H. 4641 No Kratom Sales To Minors ..." (a weekly issue's), "Taxation of
    Watercraft (H. 3858, A. 109)" (the Acts issue's)."""
    m = BILL.match(t)
    if m and len(t) < 250 and title_case(t[m.end():]):
        return f"{m[1]}{int(m[2])}"
    m = ACT_HEAD.search(t)
    if m and len(t) < 250 and title_case(t[:m.start()]):
        return f"{m[1]}{int(m[2])}"
    return None


def section(cls, t):
    """A section's heading ("House Floor", "Ways and Means"): it ends an entry."""
    return cls == "Heading" or (len(t) < 80 and not re.search(r"[.!?:;]$", t) and title_case(t) and not BILL.match(t))


def first_bill(t):
    """The first bill a paragraph names in its opening: "The Committee also gave H. 4755 ..." -> "H4755"."""
    m = re.search(r"\b([HS])\.\s?(\d{1,4})\b", t[:250])
    return f"{m[1]}{int(m[2])}" if m else None


def summaries_in(page):
    """{bill: summary} from one issue: each heading's following paragraphs to the next heading or section. The weekly
    issues sometimes put a heading before the end of the last bill's text (the "H. 4145 South Carolina Pray Safe Act"
    heading, then a paragraph on H. 4755's judicial hearings, then "H. 4145 the ... received a favorable report"): when a
    later paragraph under a heading names the heading's bill, the ones before it go back to the entry before. An entry
    whose paragraphs never name its bill but open naming another one (a heading's typo: "H. 5146" over a paragraph on
    "H. 5164") is left out rather than risk the wrong bill's summary."""
    entries, bill, body = [], None, None

    for cls, t in paragraphs(page):
        b = heading(cls, t)
        t = re.sub(r"(?<=[.;:])\s+\d{1,3}$", "", t)  # a page number run into the text
        if b:
            body = []
            entries.append([b, body])
        elif section(cls, t):
            body = None
            entries.append([None, []])
        elif body is not None and not re.fullmatch(r"[#*\s]+", t):
            # A paragraph Word split at a page break: "a work-based" / "learning experience ...".
            if body and not re.search(r"[.!?:;\"')\]”’]$", body[-1]) and re.match(r"[a-z(]", t):
                body[-1] += " " + t
            else:
                body.append(t)
    for k, (bill, body) in enumerate(entries):
        if not bill or not body:
            continue
        named = [first_bill(t) for t in body]
        if bill in named and named.index(bill) > 0:
            j = named.index(bill)
            if k and entries[k - 1][0]:
                entries[k - 1][1].extend(body[:j])
            del body[:j]
        elif bill not in named and named[0] and named[0] != bill:
            body.clear()
    out = {}
    for bill, body in entries:
        if bill and body:
            # The weekly issues open with what the House did ("The House amended and adopted H. 3247."): dropped when
            # the paragraph goes on to say what the bill does.
            s = PROCEDURE.sub("", "\n".join(body), count=1)
            if len(s) >= 40 and bill not in out:
                out[bill] = s
    return out


PROCEDURE = re.compile(r"^(?:The (?:House|Senate)(?: also)? (?:amended(?: and)?|adopted|passed|gave [^.]{0,40}reading to|"
                       r"received(?: from the (?:House|Senate))?|returned|concurred in)[^.]{0,120}\.|"
                       r"The Senate is receiving [^.]{0,120}\.)\s+(?=\S[^\n]{80})")
# What a paragraph says when it only reports a step (a conference committee named, amendments refused).
STEP_ONLY = re.compile(r"\b(?:conference committee|did not concur|non-?concur|insisted upon|special order|carried over|"
                       r"recommitted|tabled)\b", re.I)


def best(links, parsed):
    """A bill's summary from the issues the index lists for it: the Acts issue's (the law as enacted) first, else the
    latest issue's, passing over a short paragraph that only reports a step ("The Senate did not concur ...; the House has
    named Reps. ... to this bill's Conference Committee.")."""
    acts = [l for l in links if re.match(r"Acts\b", l.get("linkText") or "")]
    rest = sorted((l for l in links if l not in acts), key=lambda l: l.get("date") or "", reverse=True)
    for link in sorted(acts, key=lambda l: l.get("date") or "", reverse=True) + rest:
        s = parsed(link.get("linkUrl") or "").get(link["bill"])
        if s and not (len(s) < 400 and STEP_ONLY.search(s)):
            return link, s
    return None, None


def safe(url):
    return re.sub(r"[^A-Za-z0-9 ().,_-]", "_", urllib.parse.unquote(url.rsplit("/", 1)[-1]))[:150]


def run(session, folder):
    d = os.path.join(folder, "updates")
    os.makedirs(d, exist_ok=True)
    ipath, rpath = os.path.join(d, "index.json"), os.path.join(d, "read.json")
    try:
        read = json.load(open(rpath))
    except (OSError, ValueError):
        read = {}
    now = datetime.now(timezone.utc)
    if not os.path.exists(ipath) or time.time() - os.path.getmtime(ipath) > 20 * 3600:
        body = get(INDEX.format(session))
        try:
            index = json.loads(body) if body else None
        except ValueError:
            index = None
        if isinstance(index, list):
            json.dump(index, open(ipath, "w"))
    try:
        index = json.load(open(ipath))
    except (OSError, ValueError):
        return
    latest = {}
    for x in index:
        for link in x.get("links") or []:
            u = link.get("linkUrl") or ""
            latest[u] = max(latest.get(u, ""), (link.get("date") or "")[:10])
    got = 0
    for url, day in sorted(latest.items(), key=lambda kv: kv[1], reverse=True):
        name = safe(url)
        was = read.get(url) or {}
        if os.path.exists(os.path.join(d, name)) and was.get("date", "") >= day:
            continue
        body = get(url)
        if body and re.search(rb"(?i)<html", body[:2000]):
            open(os.path.join(d, name), "wb").write(body)
            read[url] = {"read": now.isoformat(timespec="seconds"), "date": day}
            got += 1
    json.dump(read, open(rpath, "w"), indent=0)
    json.dump(summaries_of(index, d), open(os.path.join(d, "summaries.json"), "w"), ensure_ascii=False, indent=0)
    out = json.load(open(os.path.join(d, "summaries.json")))
    print(f"legislative update: {got} issues read, {len(out)} of {len(index)} indexed bills summarized", flush=True)


def summaries_of(index, d):
    """{bill: [date, issue, summary]} for every bill in the index, from the issues saved in d (best())."""
    parsed, out = {}, {}

    def read(u):
        if u not in parsed:
            try:
                parsed[u] = summaries_in(open(os.path.join(d, safe(u)), "rb").read().decode("cp1252", "replace"))
            except OSError:
                parsed[u] = {}
        return parsed[u]

    for x in index:
        m = re.match(r"([HS])\.\s?(\d+)", x.get("billNumber") or "")
        if not m:
            continue
        bill = f"{m[1]}{int(m[2])}"
        link, s = best([{**l, "bill": bill} for l in x.get("links") or []], read)
        if s:
            out[bill] = [(link.get("date") or "")[:10], link.get("linkText") or safe(link.get("linkUrl") or ""), s]
    return out


if __name__ == "__main__":
    run(int(sys.argv[1]), sys.argv[2])
