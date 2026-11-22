#!/usr/bin/env python3
""""What it does" for Washington: the House or Senate staff's bill report for each bill of the current biennium.

The web services list every bill report (LegislativeDocumentService GetDocumentsByClass, by the first digit of the bill
number); the reports themselves are web pages at lawfilesext.leg.wa.gov. For each bill this takes the Final Bill Report
when there is one, else the latest bill report, else the latest bill analysis, and keeps its summary ("Summary:",
"Summary of Bill:", "Summary of Substitute Bill:" ...), not the background. Reports already read are kept in
data/wa/<session>/reports.json by name and date. Writes data/wa/texts_<session>.json in the shape build_data.py's
bill_texts() reads. Usage: python3 states/wa/texts.py [session]

It also reads who signed each committee report (`signatures()`, below) into data/wa/<session>/signatures.json, which
states/wa/convert.py shows beside the votes: python3 states/wa/texts.py <session> signatures [minutes].
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


_LISTED = {}


def listing(session):
    """Every bill report and analysis of a biennium (the web services' list), as (bill key, name parts, row)."""
    if session in _LISTED:
        return _LISTED[session]
    bien = P.biennium(session)
    out = []
    for digit in "124568":  # bills 1000s-2000s and 5000s-6000s; joint resolutions 4200s and 8200s
        for d in rows(call("LegislativeDocumentService", "GetDocumentsByClass", biennium=bien, documentClass="Bill Reports", namedLike=digit)):
            parts = (d.get("Name") or "").split()
            if len(parts) < 3 or not parts[0].split("-")[0].isdigit() or d.get("BillId", "").split(" ")[-1:] == []:
                continue
            num = parts[0].split("-")[0]
            jr = BILL_ID.match(d.get("BillId") or "")
            if jr and jr.group(1).endswith("JR"):
                key = jr.group(1) + jr.group(2)  # a joint resolution (a constitutional amendment): "SJR8201"
            elif num[0] in "48":
                continue  # memorials and other resolutions
            else:
                key = ("HB" if int(num) < 5000 else "SB") + num
            out.append((key, parts, d))
    _LISTED[session] = out
    return out


def reports(session):
    """Bill key ("HB1003") -> the report to use: (name, date, url)."""
    out = {}
    for key, parts, d in listing(session):
        kind = "FBR" if parts[2] == "FBR" else parts[1]
        if kind not in RANK:
            continue
        date = d.get("PdfLastModifiedDate") or d.get("HtmLastModifiedDate") or ""
        cand = (RANK[kind], date, d["Name"], (d.get("HtmUrl") or "").replace("http://", "https://"))
        if cand[3] and (key not in out or cand[:2] > out[key][:2]):
            out[key] = cand
    return out


# Committee reports' signatures. Each committee's own report ("1002 HBR LAWS 25": as reported by Labor & Workplace
# Standards; the Senate's "1796 SBR EDU OC 25") names who signed each recommendation, for that committee and the
# house's earlier ones, as of its last executive action ("Committee Activity: Ways & Means: 4/08/25 [DPA (EDU), DNP];
# 2/27/26, 3/02/26 [DPA, DNP, w/oRec]."). A committee that reports the bill again (the next year) gets a new report, so
# reading every committee's own report finds every action; the "as passed" and "TA" reports repeat them.
SIGNED_V = 2  # signed()'s version: a report read by an earlier one is read again
SECTION = re.compile(r"^(HOUSE|SENATE) COMMITTEE ON (.+)$")
RECOMMEND = re.compile(r"^(?:Majority|Minority) Report:\s*(.*?)\s*(?:Signed by (.*))?$")
SIGNED = re.compile(r"^Signed by (?:\d+ members?:\s*)?(?:Representatives?|Senators?)\s+(.*?)\.?$")
ACTIVITY = re.compile(r"^(?:Committee Activity:\s*)?([A-Z][^:\[\]]{2,90}?):\s*(\d{1,2}/\d{1,2}/\d{2}\b.*\[.*)$")
TITLE = re.compile(r"\b(?:Chair|Vice Chair|Ranking|Member)\b")


def names(text):
    """ "Wellman, Chair; Wilson, C., Vice Chair; Cortes, Hansen and McCune" -> ["Wellman", "Wilson, C.", "Cortes", ...]."""
    out = []
    for seg in text.rstrip(".").split(";"):
        toks = [t.strip() for t in re.split(r",|\band\b", seg) if t.strip()]
        merged = []
        for t in toks:
            if re.fullmatch(r"[A-Z]\.*", t) and merged:
                merged[-1] += ", " + t.rstrip(".") + "."  # an initial: "Wilson, C."
            else:
                merged.append(t)
        if any(TITLE.search(t) for t in merged):
            merged = merged[:1]  # "Stanford, Vice Chair, Operating": the name, then the title and its part
        out += merged
    return out


def wording(t):
    """A recommendation in short: "Do pass as amended and be referred to Committee on Ways & Means." -> "do pass as amended"."""
    w = re.sub(r"\.$", "", t.strip()).lower()
    if re.match(r"(?:that it be referred )?without recommendation", w):
        return "without recommendation"
    if w.startswith("do not pass"):
        return "do not pass"
    if re.search(r"substitute bill be substituted therefor", w):
        return "do pass the substitute" + (" as amended" if re.search(r"substitute bill do pass as amended", w) else "")
    m = re.match(r"(do pass(?: as amended)?)", w)
    if m:
        return m.group(1)
    return re.sub(r"\s+and be referred to .*$", "", w)


def iso(d):
    m, dd, y = d.split("/")
    return f"20{y}-{int(m):02d}-{int(dd):02d}"


def signed(page):
    """A committee report's sections: [{"house", "committee", "acted", "groups": [[wording, [names]], ...]}]."""
    lines = lines_of(page)
    # (A few reports put the recommendations before their committee's heading: 1795 HBR ED 25. They go to the next one.)
    acted, out, cur, before = {}, [], None, []
    for i, l in enumerate(lines):
        a = ACTIVITY.match(l)
        if a and not out:
            days = [re.findall(r"\d{1,2}/\d{1,2}/\d{2}", p)[-1] for p in a.group(2).split("[")[:-1] if re.search(r"\d{1,2}/\d{1,2}/\d{2}", p)]
            if days:
                acted[a.group(1).strip().upper()] = iso(days[-1])
            continue
        s = SECTION.match(l)
        if s:
            cur = {"house": s.group(1)[0], "committee": s.group(2).strip(), "acted": acted.get(s.group(2).strip().upper(), ""), "groups": before}
            out.append(cur)
            before = []
            continue
        r = RECOMMEND.match(l)
        if cur is None and not r:
            continue
        if r:
            who = r.group(2)
            if who is None and i + 1 < len(lines) and lines[i + 1].startswith("Signed by"):
                who = lines[i + 1][len("Signed by "):]
            m = SIGNED.match("Signed by " + who) if who else None
            if m and r.group(1):
                (cur["groups"] if cur else before).append([wording(r.group(1)), names(m.group(1))])
        elif re.match(r"^(?:Staff|Background|Summary|Brief Summary)\b", l):
            cur = None
    return [s for s in out if s["groups"]]


def signatures(session, until=None):
    """Reads each committee's own report of a biennium (above) into data/wa/<session>/signatures.json: name -> {date,
    bill, sections}. Reports already read are kept by name and date. until: a time.time() to stop reading at (the rest
    wait for the next run)."""
    path = os.path.join(P.DATA, str(session), "signatures.json")
    if not os.path.isdir(os.path.dirname(path)):
        return
    try:
        cache = json.load(open(path))
    except (OSError, ValueError):
        cache = {}
    try:
        comms = json.load(open(os.path.join(P.DATA, str(session), "committees.json")))
    except (OSError, ValueError):
        comms = []
    acronyms = {("H" if c.get("Agency") == "House" else "S", (c.get("Acronym") or "").upper()) for c in comms}
    todo = []
    for key, parts, d in listing(session):
        # "1002 HBR LAWS 25"; "1796 SBR EDU OC 25" (or, rarely, "... SBR EDU 25"); not "APH", "SA", "FBR", "TA"...
        house = {"HBR": "H", "SBR": "S"}.get(parts[1])
        if not house or (house, parts[2].upper()) not in acronyms or not (len(parts) == 4 or len(parts) == 5 and parts[3] == "OC"):
            continue
        date = d.get("HtmLastModifiedDate") or d.get("PdfLastModifiedDate") or ""
        url = (d.get("HtmUrl") or "").replace("http://", "https://")
        if url and (cache.get(d["Name"], {}).get("date"), cache.get(d["Name"], {}).get("v")) != (date, SIGNED_V):
            todo.append((d["Name"], date, url, key))
    got = 0

    def one(item):
        if until and time.time() > until:
            return item, None
        page = get(urllib.parse.quote(item[2], safe=":/"))
        return item, (signed(page) if page else None)

    with ThreadPoolExecutor(3) as pool:
        for k, ((name, date, _, key), sections) in enumerate(pool.map(one, todo)):
            if sections is not None:
                cache[name] = {"date": date, "v": SIGNED_V, "bill": key, "sections": sections}
                got += 1
            if k % 200 == 199:
                json.dump(cache, open(path, "w"), ensure_ascii=False)
    json.dump(cache, open(path, "w"), ensure_ascii=False)
    print(f"{session} signatures.json: {len(cache)} committee reports ({got} read now, {len(todo) - got} left)")


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


def all_signatures(current, minutes=10):
    """The committee reports' signatures: the current biennium's first, then earlier ones (read once), for at most
    `minutes` a run; what's left waits for the next run."""
    until = time.time() + 60 * minutes
    for s in sorted({int(f) for f in os.listdir(P.DATA) if f.isdigit() and int(f) <= current}, reverse=True):
        if time.time() < until:
            signatures(s, until)


if __name__ == "__main__":
    now = P.session_of(datetime.now(ZoneInfo(P.TIMEZONE)).year)
    # python3 states/wa/texts.py <session> signatures [minutes] (the session first: fetch.py reads it as FIRST)
    if sys.argv[2:3] == ["signatures"]:
        signatures(int(sys.argv[1]), time.time() + 60 * float(sys.argv[3]) if len(sys.argv) > 3 else None)
    else:
        main(int(sys.argv[1]) if len(sys.argv) > 1 else now)
