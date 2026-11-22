#!/usr/bin/env python3
"""New Hampshire's veto messages, from the House and Senate Journals (gc.nh.gov; robots.txt bars only AhrefsBot and asks
every agent for an 11-second crawl delay). The governor's site (www.governor.nh.gov) answers automated requests with 403
and isn't read. Each message is printed in full when a house takes up the veto, often weeks or months after it (the fall
veto day):

    House:   GOVERNOR'S VETO MESSAGE ON HB 349-FN
             Access to quality and affordable healthcare is ...
             ... As such, I am vetoing this bill.
             Respectfully submitted, Kelly A. Ayotte, Governor
    Senate:  VETO MESSAGE
             July 2, 2026
             Governor's Veto Message Regarding Senate Bill 627
             ... For these reasons, I have vetoed Senate Bill 627.
             Respectfully Submitted, ...

Which journals: the Docket's lines for a vetoed bill name the journal and page where each step is printed, "Vetoed by
Governor Ayotte 03/27/2026  HJ 10  P. 2", "Veto Overridden ... SJ 15"; every House or Senate Journal a vetoed bill's line
names on or after its veto is read, once (its text kept in data/nh/journals/HJ-2026-10.txt). A journal's file name has
its date ("HJ 10 April 9, 2026.pdf"), so each body's list of a year's journals comes from its Calendars & Journals page
(gc.nh.gov/house/calendars_journals/, /senate/calendars_journals/): the page, then one form post choosing Journals and
the year (data/nh/journals/lists.json; asked again, at most once a day, only when a journal named isn't on it). The PDFs
answer at viewer.aspx?fileName=journals\\2026\\HJ 10 April 9, 2026.pdf (the Senate's "Journals\\2026\\SJ 15.pdf").
Requests share fetch.py's crawl delay; at most MAX_REQUESTS a run.

Usage: python3 states/nh/vetoes.py   (fetch.py calls fetch() each run; convert.py calls message())
"""
import glob, html, json, os, re, subprocess, sys, time, urllib.parse
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
from states.nh import profile as P
from states import letters as L

FOLDER = os.path.join(P.DATA, "journals")
LISTS = os.path.join(FOLDER, "lists.json")
PAGES = {"H": "/house/calendars_journals/", "S": "/senate/calendars_journals/"}
KIND = {"H": "Journal", "S": "SenateJournal"}
PREFIX = {"H": "journals", "S": "Journals"}  # the viewer's folder name, as each page writes it
MAX_REQUESTS = 12
F_SITE, AGENT = "https://gc.nh.gov", ""  # set by fetch()
REF = re.compile(r"\b([HS])J\s+(\d{1,3})\b")


def wanted():
    """{(body, year, number)}: the journals that vetoed bills' Docket lines name on or after the veto."""
    from states.nh import convert as C
    out = set()
    for path in glob.glob(os.path.join(P.DATA, "[0-9]" * 4, "Docket_*.txt")):
        by_bill = {}
        for r in C.rows(path):
            if len(r) >= 6:
                by_bill.setdefault(r[3].replace(" ", "").upper(), []).append(r)
        for bill, lines in by_bill.items():
            vetoed = [C.iso(C.text(r[5])) or C.iso(r[2]) for r in lines if re.match(r"Vetoed by", C.text(r[5]), re.I)]
            if not vetoed:
                continue
            first = min(d for d in vetoed if d) if any(vetoed) else ""
            for r in lines:
                a = C.text(r[5])
                day = C.iso(a) or C.iso(r[2]) or ""
                if day and first and day < first:
                    continue
                for body, n in REF.findall(a):
                    out.add((body, int(day[:4] or r[0]), int(n)))
    return out


def _lists():
    try:
        return json.load(open(LISTS))
    except (OSError, ValueError):
        return {}


def _hidden(page):
    fields = {}
    for name in ("__VIEWSTATE", "__VIEWSTATEGENERATOR", "__EVENTVALIDATION"):
        m = re.search(r'name="%s"[^>]*value="([^"]*)"' % name, page)
        fields[name] = html.unescape(m.group(1)) if m else ""
    return fields


def journal_list(body, year, rp, request):
    """{number: file name} for one body's journals of a year, from its page and one form post."""
    url = F_SITE + PAGES[body]
    if not rp.can_fetch(AGENT, url):
        return None
    page, _ = request(url, f"{body} calendars and journals")
    if not page:
        return None
    # Two posts, as a visitor's two choices: Journals (which lists the newest year's), then the year. (Choosing both in
    # one post keeps the newest year's list.)
    got, text = page, page.decode("utf-8", "replace")
    for target, label in (("ddlCalJourn", f"{body} journals"), ("ddlYears", f"{body} journals {year}")):
        sel = re.search(r'name="ctl00\$pageBody\$ddlYears".*?<option selected="selected" value="(\d{4})"', text, re.S)
        if target == "ddlYears" and sel and sel.group(1) == str(year):
            break
        fields = _hidden(text)
        fields.update({"__EVENTTARGET": f"ctl00$pageBody${target}", "__EVENTARGUMENT": "",
                       "ctl00$pageBody$ddlCalJourn": KIND[body],
                       "ctl00$pageBody$ddlYears": sel.group(1) if target == "ddlCalJourn" and sel else str(year)})
        got, _ = request(url, label, data=urllib.parse.urlencode(fields).encode(),
                         headers={"Content-Type": "application/x-www-form-urlencoded"})
        if not got:
            return None
        text = got.decode("utf-8", "replace")
    sel = re.search(r'name="ctl00\$pageBody\$ddlYears".*?<option selected="selected" value="(\d{4})"', text, re.S)
    if not sel or sel.group(1) != str(year):
        print(f"{body} journals {year}: the page didn't switch to that year", flush=True)
        return None
    out = {}
    for v in re.findall(r'<option[^>]*value="([HS]J[^"]*\.pdf)"', text):
        m = re.match(r"[HS]J\s*0*(\d+)\b", v)
        if m and v.startswith(f"{body}J") and m.group(1) not in out:
            out[m.group(1)] = html.unescape(v)
    return out


def pdf_text(body):
    try:
        r = subprocess.run(["pdftotext", "-layout", "-", "-"], input=body, capture_output=True)
        if r.returncode == 0:
            return r.stdout.decode("utf-8", "replace")
    except OSError:
        pass
    import io
    from pypdf import PdfReader  # (fetch.py's job installs it; pdftotext keeps the layout better)
    return "\n\f".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(body)).pages)


def text_path(body, year, n):
    return os.path.join(FOLDER, f"{body}J-{year}-{n}.txt")


def fetch(rp, request, site, agent):
    """Read the journals named that aren't kept yet, at most MAX_REQUESTS requests. Any failure leaves the rest for the
    next run."""
    global F_SITE, AGENT
    F_SITE, AGENT = site, agent
    os.makedirs(FOLDER, exist_ok=True)
    lists = _lists()
    today = date.today().isoformat()
    todo = sorted((k for k in wanted() if not os.path.exists(text_path(*k))), key=lambda k: (-k[1], k[0], k[2]))
    used = got = 0
    for body, year, n in todo:
        if used >= MAX_REQUESTS:
            break
        key = f"{body}{year}"
        entry = lists.get(key) or {}
        if str(n) not in (entry.get("files") or {}):
            if entry.get("read") == today:
                continue  # asked today already: not posted yet
            files = journal_list(body, year, rp, request)
            used += 3
            if files is None:  # (not again today)
                lists[key] = {"read": today, "files": entry.get("files") or {}}
                continue
            entry = lists[key] = {"read": today, "files": files}
            with open(LISTS, "w") as f:
                json.dump(lists, f, indent=1, sort_keys=True)
            if str(n) not in files:
                continue
        name = entry["files"][str(n)]
        url = f"{site}{PAGES[body]}viewer.aspx?fileName={urllib.parse.quote(PREFIX[body] + chr(92) + str(year) + chr(92) + name, safe=',')}"
        if not rp.can_fetch(agent, url):
            continue
        pdf, _ = request(url, f"{body}J {n} of {year}")
        used += 1
        if pdf and pdf[:4] == b"%PDF":
            with open(text_path(body, year, n), "w", encoding="utf-8") as f:
                f.write(pdf_text(pdf))
            got += 1
    left = sum(1 for k in todo if not os.path.exists(text_path(*k)))
    print(f"veto messages: {got} journals read ({used} requests); {left} named journals not read yet", flush=True)


# ---- reading them -------------------------------------------------------------------------------------------------

HEAD = re.compile(r"^\s*(?:GOVERNOR[’']S VETO MESSAGE ON\s+(HB|SB|CACR)\s*(\d+)"
                  r"|Governor[’']s Veto Message Regarding\s+(House|Senate) Bill\s+(\d+))", re.I)
END = re.compile(r"^\s*(?:Respectfully submitted|The question (?:being|is)\b|GOVERNOR[’']S VETO MESSAGE|VETO MESSAGE\s*$)", re.I)
DAY = re.compile(r"^\s*(?:Date:\s*)?((?:January|February|March|April|May|June|July|August|September|October|November|"
                 r"December) \d{1,2}, \d{4})\s*$")
RUNNING = re.compile(r"^\s*(?:\d+\s+)?(?:\d{1,2} [A-Z]+ \d{4} HOUSE RECORD|SENATE JOURNAL \d{1,2} [A-Z]+ \d{4})(?:\s+\d+)?\s*$")


def parse(text):
    """[(bill "HB349", date or "", paragraphs)] for every veto message in one journal's text."""
    lines = text.replace("\f", "\n").splitlines()
    out = []
    for i, line in enumerate(lines):
        m = HEAD.match(line)
        if not m:
            continue
        bill = f"{m.group(1).upper()}{int(m.group(2))}" if m.group(1) else f"{m.group(3)[0]}B{int(m.group(4))}"
        day = ""
        for back in lines[max(0, i - 3):i]:
            d = DAY.match(back)
            if d:
                day = d.group(1)
        body = []
        for x in lines[i + 1:i + 400]:
            if END.match(x):
                break
            if RUNNING.match(x) or re.fullmatch(r"\s*\d+\s*", x):
                continue  # a page's running head or number
            body.append(x.strip())
        # Words broken at a line's end ("profession-" / "als"): joined (the journal's own hyphens are mid-line).
        joined = []
        for x in body:
            if joined and re.search(r"[a-z]-$", joined[-1]) and re.match(r"[a-z]", x):
                joined[-1] = joined[-1][:-1] + x
            else:
                joined.append(x)
        paras = L.wrapped(joined)
        if paras:
            out.append((bill, day, paras))
    return out


_ALL = {}


def messages():
    """bill -> [(journal year, date or "", paragraphs)] over every journal kept."""
    if not _ALL:
        for path in sorted(glob.glob(os.path.join(FOLDER, "[HS]J-*.txt"))):
            year = int(os.path.basename(path).split("-")[1])
            for bill, day, paras in parse(open(path, encoding="utf-8").read()):
                _ALL.setdefault(bill, []).append((year, day, paras))
        _ALL.setdefault("", [])
    return _ALL


def message(p, veto_day):
    """The record p's veto message ({year, signer, text}), for a veto on veto_day ("2026-03-27"): one printed for that
    bill number in a journal of the veto's year or the next (numbers start over each biennium), dated (the Senate's are)
    on the veto's day or near it."""
    from datetime import datetime
    if not veto_day:
        return None
    y = int(veto_day[:4])
    best = None
    for year, day, paras in messages().get(p, []):
        if not y <= year <= y + 1:
            continue
        if day:
            try:
                d = datetime.strptime(day, "%B %d, %Y").date().isoformat()
            except ValueError:
                d = ""
            if d and abs((date.fromisoformat(d) - date.fromisoformat(veto_day)).days) > 10:
                continue
        if not best or len("\n".join(paras)) > len("\n".join(best)):
            best = paras
    if not best:
        return None
    return {"year": y, "signer": P.governor_on(veto_day), "text": L.cut(best)}


if __name__ == "__main__":
    from states.nh import fetch as F
    rp = F.robots()
    if rp:
        fetch(rp, F.request, F.SITE, F.AGENT)
