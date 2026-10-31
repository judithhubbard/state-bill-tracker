#!/usr/bin/env python3
""""What it does" for Washington: the House or Senate staff's bill report for each bill of the current biennium.

The web services list every bill report (LegislativeDocumentService GetDocumentsByClass, by the first digit of the bill
number); the reports themselves are web pages at lawfilesext.leg.wa.gov. For each bill this takes the Final Bill Report
when there is one, else the latest bill report, else the latest bill analysis, and keeps its summary ("Summary:",
"Summary of Bill:", "Summary of Substitute Bill:" ...), not the background. Reports already read are kept in
data/wa/<session>/reports.json by name and date. Writes data/wa/texts_<session>.json in the shape build_data.py's
bill_texts() reads. Usage: python3 states/wa/texts.py [session]
"""
import html, json, os, re, sys, time, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
from states.wa import profile as P
from states.wa.fetch import AGENT, BILL_ID, call, rows

# The report's own name says what it is: "1003 HBR FBR 25" (Final Bill Report), "1003 HBR HOUS 25" (House Bill Report
# as reported by Housing), "1003 HBA HOUS 25" (House Bill Analysis), "5001 SBR ..." / "SBA" for the Senate's.
RANK = {"FBR": 3, "HBR": 2, "SBR": 2, "HBA": 1, "SBA": 1}
# Section headings; a heading and its first paragraph can share a line ("Summary: Service by mail is ...").
HEAD = re.compile(r"^(Summary(?: of (?:the )?(?:Engrossed |Second |Third |Proposed )*(?:Substitute |Striking Amendment |Amended )?Bill)?"
                  r"(?: \([^)]*\))?(?: as (?:Amended|Enacted|Passed)[^:]*)?|Brief Summary of (?:[\w-]+ )*?Bill(?: \([^)]*\))?)(?::\s*(.*)|\s+(?=[A-Z])(.*)|$)", re.I)
STOP = re.compile(r"^(?:(?:Votes on Final Passage|Appropriation|Fiscal Note|Effective(?: Date)?|Staff Summary of Public Testimony|"
                  r"Persons Testifying|Persons Signed In[^:]*|(?:[\w-]+ )*(?:Bill|Substitute|Amendment) Compared[^:]*|"
                  r"Partial Veto Summary|Veto Summary|Background|Rules Committee|Majority Report|Minority Report|Staff|Brief History|"
                  r"Committee Activity|Other Committees|Title|Sponsors|Brief Description)(?::|$)|Final Passage Votes|(?:HOUSE|SENATE) COMMITTEE ON)", re.I)


def get(url):
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": AGENT})
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read().decode("utf-8", "replace")
        except Exception:
            time.sleep(3 * (attempt + 1))
    return None


def lines_of(page):
    page = re.sub(r"(?s)<style.*?</style>|<script.*?</script>", "", page)
    text = html.unescape(re.sub(r"<(?:/p|br|/li|/div|/h\d|/tr)\s*/?>", "\n", page, flags=re.I))
    text = re.sub(r"<[^>]+>", " ", text)
    return [re.sub(r"\s+", " ", l).strip() for l in text.split("\n") if l.strip()]


def summary(page):
    """The report's summary paragraphs: the full summary when there is one, else the brief one."""
    lines = lines_of(page)
    for full in (True, False):
        out, on = [], False
        for l in lines:
            m = HEAD.match(l)
            if m and m.group(1).lower().startswith("brief") != full:
                on, out = True, [m.group(2) or m.group(3)] if (m.group(2) or m.group(3)) else []
                continue
            if on and (STOP.match(l) or m):
                break
            if on:
                out.append(l)
        if out:
            return "\n".join(out).strip()
    return ""


def reports(session):
    """Bill key ("HB1003") -> the report to use: (name, date, url)."""
    bien = P.biennium(session)
    out = {}
    for digit in "124568":  # bills 1000s-2000s and 5000s-6000s; joint resolutions 4200s and 8200s
        for d in rows(call("LegislativeDocumentService", "GetDocumentsByClass", biennium=bien, documentClass="Bill Reports", namedLike=digit)):
            parts = (d.get("Name") or "").split()
            if len(parts) < 3 or not parts[0].split("-")[0].isdigit():
                continue
            num = parts[0].split("-")[0]
            kind = "FBR" if parts[2] == "FBR" else parts[1]
            if kind not in RANK or d.get("BillId", "").split(" ")[-1:] == []:
                continue
            jr = BILL_ID.match(d.get("BillId") or "")
            if jr and jr.group(1).endswith("JR"):
                key = jr.group(1) + jr.group(2)  # a joint resolution (a constitutional amendment): "SJR8201"
            elif num[0] in "48":
                continue  # memorials and other resolutions
            else:
                key = ("HB" if int(num) < 5000 else "SB") + num
            date = d.get("PdfLastModifiedDate") or d.get("HtmLastModifiedDate") or ""
            cand = (RANK[kind], date, d["Name"], (d.get("HtmUrl") or "").replace("http://", "https://"))
            if cand[3] and (key not in out or cand[:2] > out[key][:2]):
                out[key] = cand
    return out


def label(name):
    parts = name.split()
    if parts[2:3] == ["FBR"]:
        return "From the Final Bill Report."
    house = "House" if parts[1].startswith("H") else "Senate"
    return f"From the {house} bill {'analysis' if parts[1].endswith('A') else 'report'}."


def main(session):
    folder = os.path.join(P.DATA, str(session))
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, "reports.json")
    try:
        cache = json.load(open(path))
    except (OSError, ValueError):
        cache = {}
    pick = reports(session)
    todo = sorted({(n, dt, u) for _, dt, n, u in pick.values() if cache.get(n, {}).get("date") != dt or not cache[n].get("text")})

    def one(item):
        name, date, url = item
        page = get(urllib.parse.quote(url, safe=":/"))
        return name, date, (summary(page) if page else None)

    with ThreadPoolExecutor(3) as pool:
        for k, (name, date, text) in enumerate(pool.map(one, todo)):
            if text is not None:
                cache[name] = {"date": date, "text": text}
            if k % 200 == 199:
                json.dump(cache, open(path, "w"), ensure_ascii=False)
    json.dump(cache, open(path, "w"), ensure_ascii=False)
    # A few reports lost characters in the Legislature's export, written "?": a "fi", "ff" or "fl" ligature ("speci?c")
    # or a non-breaking space ("establish?rate"). Each is put back when the result is words the other reports use.
    words = {w for v in cache.values() for w in re.findall(r"[a-z]+", (v.get("text") or "").lower())}

    def mend(m):
        left, right = m.group(1), m.group(2)
        for fill in ("fi", "ff", "fl", "ffi"):
            if (left + fill + right).lower() in words:
                return left + fill + right
        if left.lower() in words and right.lower() in words:
            return f"{left} {right}"
        return m.group(0)

    out = {}
    for key, (_, _, name, _) in pick.items():
        text = (cache.get(name) or {}).get("text")
        # A bold heading leaves a space before its period ("Definitions .").
        text = re.sub(r"[ \t]+([.,;:)])", r"\1", text or "")
        text = re.sub(r"([A-Za-z]+)\?([a-z]+)", mend, text)
        # The rest were spaces: a real question mark follows a letter, not punctuation or a space.
        text = re.sub(r"(?<=[^A-Za-z0-9\n])\?+|(?<=\n)\?+|^\?+|(?<=\band)\?(?=\s)|(?<=\bor)\?(?=\s)", " ", text)
        text = "\n".join(re.sub(r"[ \t]{2,}", " ", l).strip() for l in text.split("\n"))
        # Run-in headings ("The Clemency and Pardons Board.") are paragraphs of their own: join each to what follows.
        text = re.sub(r"(?m)^([A-Z][^.\n]{0,60}\.)\n(?=[A-Z])", r"\1 ", text)
        if text:
            out[key] = {"statement": text, "label": label(name)}
    json.dump(out, open(os.path.join(P.DATA, f"texts_{session}.json"), "w"), ensure_ascii=False)
    print(f"texts_{session}.json: {len(out)} bill reports ({len(todo)} read now)")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else P.session_of(datetime.now(ZoneInfo(P.TIMEZONE)).year))
