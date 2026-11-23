#!/usr/bin/env python3
""""What it does" for Alaska: a lead quoted from each bill's own text (states/billtext_lead.py), since Alaska publishes no
summaries (the sponsor statement is an advocate's case; NOTES.md).

The text is BASIS's full-text page for the bill as introduced, https://www.akleg.gov/basis/Bill/Text/34?Hsid=HB0057A
(robots.txt allows /basis/; it bars /PDF/, the same texts as PDFs, which aren't read). The page shows the bill as a
line-numbered <pre>: "* Section 1." / "* Sec. 2." begin sections; "AS 14.33 is amended by adding a new section to read:"
is new law (with its statute number and catchline, "Sec. 14.33.300. Wireless telecommunications device policy."),
"AS 14.40.120 is amended to read:" an amendment whose new wording is bold and underlined and whose deleted wording is in
[CAPITALS IN BRACKETS].

The sections are kept in data/ak/<first year>/leads.json by bill and version (its first version letter), read once,
ever; the lead is worked out from them each run, so a change to its rules needs no download. At most `minutes` a
run, five seconds apart (the documents server answered 429 to requests a second apart), the current Legislature first,
the bills acted on latest first. Writes data/ak/texts_<first year>.json for build_data.py's bill_texts().
Usage: python3 states/ak/billtext.py [first year] [minutes]
"""
import html, json, os, re, sys, time, urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
from states import billtext_lead as L
from states.ak import convert as C, profile as P

AGENT = "statebilltracker.org (a nonprofit bill tracker; contact via github.com/judithhubbard)"
PAUSE = 5
MARK = re.compile(r"^\s*\*\s*(?:Section|Sec\.)\s+(\d+[A-Za-z]?)\.\s*")
U_ON, U_OFF = "\x01", "\x02"


def lines_of(page):
    """The bill's text lines, without line numbers; underlined wording between U_ON and U_OFF."""
    pre = "\n".join(re.findall(r"(?s)<pre[^>]*>(.*?)</pre>", page)).replace("\r\n", "\n").replace("\r", "\n")  # (lines end in CR)
    pre = re.sub(r"(?s)<span class=unselectable>.*?</span>", "", pre)
    pre = re.sub(r"(?i)<u>", U_ON, pre)
    pre = re.sub(r"(?i)</u>", U_OFF, pre)
    pre = re.sub(r"(?i)</p>\s*<p[^>]*>", "\n", pre)
    pre = html.unescape(re.sub(r"<[^>]+>", "", pre))
    out = []
    for line in pre.split("\n"):
        line = re.sub(r"^\d\d(?=\D|$)", "", line.rstrip())  # (the first line of each page keeps its number)
        if line.strip():
            out.append(line)
    return out


def sections(page):
    """The bill's sections (billtext_lead's Section dicts) and its title."""
    lines = lines_of(page)
    paras, cur = [], ""
    indent = lambda l: len(l) - len(l.lstrip(" " + U_ON + U_OFF))
    for k, line in enumerate(lines):
        # A paragraph starts at a section mark or a subsection's number, or indented further than the line after it
        # (its wrapped lines start at the text's margin, which differs from page to page).
        nxt = lines[k + 1] if k + 1 < len(lines) else ""
        starts = MARK.match(line) or re.match(r"^[\s\x01\x02]*\((?:\d+|[a-z]{1,4}|[A-Z])\)\s", line) or (nxt and indent(line) > indent(nxt) + 1)
        if starts and cur:
            paras.append(cur)
            cur = ""
        # (A word broken at its hyphen, "nonschool-" / "issued", is joined without a space.)
        cur += ("" if not cur or re.search(r"[a-z]-[\x01\x02]*$", cur) else " ") + line.strip()
    if cur:
        paras.append(cur)
    title = next((p.strip('"') for p in paras if p.startswith('"An Act') or p.startswith('"Proposing')), "")
    runs = []
    for p in paras:
        # Deleted wording: [IN CAPITALS, IN BRACKETS].
        p = re.sub(r"\s*\[[^\]a-z]*\]", "", p)
        pieces, on = [], False
        for bit in re.split(f"([{U_ON}{U_OFF}])", p):
            if bit == U_ON:
                on = True
            elif bit == U_OFF:
                on = False
            elif bit:
                pieces.append((bit, on))
        runs.append(pieces)

    def cite(head):
        m = re.search(r"\b(AS\s+\d+\.\d+(?:\.\d+)?)", head)
        return m.group(1) if m else ""

    return L.split(runs, cite, MARK), title


def folder(first):
    return os.path.join(P.DATA, str(first))


def get(url):
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": AGENT})
            with urllib.request.urlopen(req, timeout=60) as resp:
                return resp.read().decode("utf-8", "replace")
        except Exception:
            time.sleep(PAUSE * (attempt + 2))
    return None


def wanted(first):
    """[(bill, version, text page)] of the Legislature's bills, the latest acted on first."""
    out = []
    legis = P.legislature_of(first)  # 2025 -> 34
    bills = os.path.join(folder(first), "bills")
    for f in os.listdir(bills) if os.path.isdir(bills) else []:
        try:
            rec = json.load(open(os.path.join(bills, f)))
        except (OSError, ValueError):
            continue
        vers = sorted(rec.get("Versions") or [], key=lambda v: v.get("VersionLetter") or "")
        m = re.match(r"([HS](?:B|JR))\s*(\d+)", (rec.get("BillNumber") or "").replace(" ", ""))
        key = C.number(rec)
        if not vers or not m or not key:
            continue
        v = vers[0]["VersionLetter"]
        out.append((rec.get("StatusDate") or "", key, v,
                    f"https://www.akleg.gov/basis/Bill/Text/{legis}?Hsid={m.group(1)}{int(m.group(2)):04d}{v}"))
    return [x[1:] for x in sorted(out, reverse=True)]


def main(first, minutes=10):
    until = time.time() + 60 * minutes
    path = os.path.join(folder(first), "leads.json")
    try:
        cache = json.load(open(path))
    except (OSError, ValueError):
        cache = {}
    want = wanted(first)
    todo = [w for w in want if cache.get(w[0], {}).get("version") != w[1]]
    read = 0
    for bill, version, url in todo:
        if time.time() > until:
            break
        page = get(url)
        time.sleep(PAUSE)
        if not page or "<pre" not in page:
            continue
        secs, title = sections(page)
        cache[bill] = {"version": version, "sections": L.compact(secs)}
        read += 1
        if read % 25 == 0:
            save(path, cache)
    save(path, cache)
    out = {}
    for bill, v in cache.items():
        text, label = L.statement(L.lead(v["sections"]))
        if text:
            out[bill] = {"statement": text, "label": label}
    json.dump(out, open(os.path.join(P.DATA, f"texts_{first}.json"), "w"), ensure_ascii=False)
    print(f"{first} leads.json: {len(cache)} bill texts ({read} read now, {max(0, len(todo) - read)} left); "
          f"texts_{first}.json: {len(out)} leads", flush=True)
    return max(0, len(todo) - read)  # bills still to read


def save(path, cache):
    json.dump(cache, open(path + ".tmp", "w"), ensure_ascii=False)
    os.replace(path + ".tmp", path)


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else P.session_of(time.localtime().tm_year) if hasattr(P, "session_of") else 2025,
         float(sys.argv[2]) if len(sys.argv) > 2 else 10)
