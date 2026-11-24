"""What a Montana bill does, from its full title: the "AN ACT ..." title the Legislative Services Division's drafters
write at the top of every bill, which lists what the act does ("AN ACT CREATING A SENIOR CITIZEN CENTER GRANT PROGRAM
...; PROVIDING AN APPROPRIATION; AMENDING SECTIONS 2-15-1, MCA; AND PROVIDING AN EFFECTIVE DATE."), while the records
carry only the short title ("Provide grant funding for senior citizen centers").

Read from the bill's text, a PDF with a text layer, through the documents service the Bill Explorer uses
(api.legmt.gov and docs.legmt.gov: "User-agent: * / Crawl-delay: 10", nothing disallowed; fetch.py's request() and
get_pdf() keep the delay). Only the enrolled bill (as passed) or the introduced one: the versions in between show
amendments in place, with struck words still in the text layer.
- current system (2025 on): GET docs/v1/documents/getBillText?legislatureOrdinal=69&sessionOrdinal=20251&billType=HB&
  billNumber=182 answers the latest version's PDF itself (one request), used for a bill never amended (versionNumber 1)
  and for laws and vetoed bills (the enrolled text, without the 'A BILL FOR AN ACT ENTITLED' wrapper);
- otherwise, and for the archive (2023: getBillText answers 404), getBillVersions (same query; 2023 is
  legislatureOrdinal 68, sessionOrdinal 20231) lists the versions ("HB0002_1.pdf" ... "HB0002_x.pdf", the enrolled
  bill), and "_x", else "_1", is read (two requests).
Each bill's title goes in data/mt/<year>/titles/<HB182>.json: {"v": the bill's version when read (versionNumber, or the
archive's latestVersion), "as": "passed" or "introduced", "title": the title as printed (capitals), "case": how the
bill's own text writes the title's words that aren't lower case ("montana": "Montana", "pfas": "PFAS"), "read": day}. A bill is read again when its version changes
(a live session); bills with no text yet are asked again a week later (titles/asked.json). Laws first, then the bills
that got furthest (most versions), newest session first; at most `minutes` a run. Joint resolutions are left out (the
converter leaves them out).

texts_<year>.json is written from those files every run: the title in sentence case (each word as the bill's text
writes it), without the lists of sections it amends or repeals ("AMENDING SECTIONS 3-1-702 AND 25-1-201, MCA"),
effective and applicability dates and "providing definitions"; a title that then says no more than the short title is
left out."""
import json, os, re, time, urllib.parse
from datetime import date, timedelta

TODAY = date.today()
TEXT_MAX = 1500  # characters at most (a budget bill's title can list dozens of purposes)
LABEL = {"passed": "From the bill's full title as passed by the Legislature.",
         "introduced": "From the bill's full title as introduced."}


def save(obj, path):
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(obj, f, ensure_ascii=False)
    os.replace(tmp, path)


def load(path, default=None):
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


# ---------------------------------------------------------------- reading a bill's text

def title_of(txt):
    """(title, case, wrapped) from a bill's text (pdftotext -layout), or None; wrapped when the title is in the
    'A BILL FOR AN ACT ENTITLED: "..."' of a bill not yet enrolled. The title runs from "AN ACT" to "BE IT ENACTED"
    (or a preamble's "WHEREAS"); introduced bills wrap it in 'A BILL FOR AN ACT ENTITLED: "..."'. Line numbers, page
    headers ("69th Legislature 2025 HB0093.3") and footers ("- 1 -", "Authorized Print Version - HB 182") are dropped."""
    lines = []
    for raw in txt.replace("\f", "\n").split("\n"):
        line = re.sub(r"^\s*\d{1,3}(?=\s{2,}|\s*$)", "", raw).strip()
        if line:
            lines.append(line)
    flat = "\n".join(lines)
    m = re.search(r"\bAN ACT\b", flat)
    if not m:
        return None
    end = re.search(r"\bBE IT ENACTED\b|\bWHEREAS\b", flat[m.start():])
    if not end:
        return None
    head = flat[m.start():m.start() + end.start()]
    body = flat[m.start() + end.start():]
    kept = []
    for line in head.split("\n"):
        # Headers and footers have lower case ("69th Legislature", "Authorized Print Version") or are page marks.
        if re.search(r"[a-z]", line) or re.fullmatch(r"-.*-|(?:HB|SB|HJ|SJ) ?\d+(?:\.\d+)?|[\d\s.]+", line):
            continue
        kept.append(line)
    title = " ".join(kept)
    title = re.sub(r"(?<=\w)- (?=\w)", "-", title)  # "3-1- 702", "NON- PROFIT": the hyphen is the word's own
    title = re.sub(r"\s+", " ", title).strip()
    wrapped = bool(re.match(r"AN ACT ENTITLED:", title))  # a bill's text before enrollment
    title = re.sub(r"^AN ACT ENTITLED:\s*[“\"]?\s*", "", title).strip().strip("“”\"").strip()
    if len(title) < 15 or re.search(r"[a-z]", title):
        return None
    return title, casing(title, body), wrapped


def casing(title, body):
    """How the bill's text writes the title's words that aren't plain lower case: a word counts where it follows a
    lower-case word (so not at a sentence's start, in a heading or inside a name: "Rules of Civil Procedure"), and wins when it's written that way more often than
    in lower case ("Montana", "Medicaid", "PFAS", "Title 75")."""
    want = {w.lower() for w in re.findall(r"[A-Za-z][A-Za-z.']*", title)}
    forms = {}
    for m in re.finditer(r"(?<![A-Za-z.'])[a-z]+,? +([A-Za-z][A-Za-z.']*[A-Za-z]|[A-Za-z])(?![A-Za-z])", body):
        w = m.group(1)
        if w.lower() in want:
            forms.setdefault(w.lower(), {}).setdefault(w, 0)
            forms[w.lower()][w] += 1
    out = {}
    for low, seen in forms.items():
        best = max(seen, key=lambda f: (seen[f], f != low))
        if best != low and seen[best] > seen.get(low, 0):
            out[low] = best
    return out


# ---------------------------------------------------------------- the statement

DATES = re.compile(r"PROVIDING (?:AN? |FOR AN? )?(?:(?:IMMEDIATE|DELAYED|RETROACTIVE|CONTINGENT) )*"
                   r"(?:EFFECTIVE|APPLICABILITY)\b")
# (Each number is matched whole, "(?![\d.\-])": when "15-1-1012" could also be "15-1-101" then "2", a long section list
# that isn't all sections took exponential time to fail; Montana's download hung on one on 2026-11-23 and 24.)
SECTIONS = re.compile(r"(?:AMENDING|REPEALING|AND|SECTIONS?|SUBSECTIONS?|MCA|TITLES?|CHAPTERS?|PARTS?|OF|THE|LAWS|"
                      r"[\d][\d.\-]*(?![\d.\-])(?:\([\dA-Za-z]+\))*|[,()\s])+")
STOP = set("the a an of to and or for in on by with that from as at be is are its this any certain other act "
           "revise revising revises generally general provide providing provides create creating creates law laws related "
           "relating establish establishing require requiring allow allowing include including".split())


def clauses(title):
    """The title's clauses, without what says little: section lists, effective and applicability dates, definitions."""
    t = re.sub(r"^AN ACT\s+", "", title).rstrip(".").strip()
    out = []
    for c in re.split(r";\s*", t):
        c = re.sub(r"^AND\s+", "", c.strip()).strip(" ,")
        if not c:
            continue
        if re.match(r"(?:AMENDING|REPEALING)\b", c) and SECTIONS.fullmatch(c):
            continue
        if DATES.match(c):
            if "TERMINATION" in c:
                out.append("PROVIDING A TERMINATION DATE")
            continue
        if re.fullmatch(r"PROVIDING (?:FOR )?DEFINITIONS", c):
            continue
        # A section list closing a clause ("... AND AMENDING SECTION 2-4-302, MCA"): the purpose before it stays.
        c = re.sub(r",? AND (?:AMENDING|REPEALING) SECTIONS? [\d][\d\-., ANDM]*MCA$", "", c)
        c = re.sub(r",? (?:AMENDING|REPEALING) SECTIONS? [\d][\d\-., ANDM]*MCA$", "", c)
        out.append(c)
    return out


def cased(text, case):
    words = re.sub(r"[A-Za-z][A-Za-z.']*", lambda m: case.get(m.group(0).lower(), m.group(0).lower()), text)
    words = re.sub(r"\bmontana\b", "Montana", words)
    words = re.sub(r"\b(article) ([ivxl]+)\b", lambda m: m.group(1) + " " + m.group(2).upper(), words, flags=re.I)
    words = re.sub(r"\btitle (?=\d)", "Title ", words)
    words = re.sub(r"\bu\.s\.", "U.S.", words)
    return words


def content(text):
    return {w[:5] for w in re.findall(r"[a-z]+", text.lower()) if len(w) > 2 and w not in STOP}


def statement(title, case, short):
    """The title as a sentence ("An act creating ...; providing an appropriation; and providing a termination date."),
    or "" when it says no more than the short title."""
    cs = clauses(title)
    if not cs:
        return ""
    if len(cs) > 1:
        cs[-1] = "AND " + cs[-1]
    s = "AN ACT " + "; ".join(cs)
    if len(s) > TEXT_MAX:  # a budget's long list: cut at a clause
        cut = s.rfind("; ", 0, TEXT_MAX)
        s = s[:cut] if cut > 0 else s[:TEXT_MAX]
    s = cased(s, case)
    s = s[:1].upper() + s[1:] + "."
    if len(content(s) - content(short or "")) < 2:
        return ""
    return s


# ---------------------------------------------------------------- downloading

def version_of(b):
    return str(b.get("versionNumber") if "versionNumber" in b else b.get("latestVersion") or "")


def clean_version(docs):
    """(ticket, "passed" or "introduced") among getBillVersions' documents: the enrolled bill ("_x"), else the
    introduced one ("_1"). Versions in between show amendments in place, struck words still in the text layer, so a
    title read from them could keep words the amendment took out. Among copies of one version ("HB0182_X(3).pdf"),
    the latest uploaded."""
    best = {}
    for d in docs if isinstance(docs, list) else []:
        m = re.match(r"[A-Z]+\d+_(1|x)(?:\(\d+\))?\.pdf$", d.get("fileName") or "", re.I)
        link = next((a.get("stringValue") for a in d.get("attributes") or [] if a.get("name") == "DocumentLink"), None)
        if not m or not link:
            continue
        kind = "passed" if m.group(1).lower() == "x" else "introduced"
        if kind not in best or (d.get("date") or "") > best[kind][1]:
            best[kind] = (link, d.get("date") or "")
    for kind in ("passed", "introduced"):
        if kind in best:
            return best[kind][0], kind
    return None, None


def fetch(s, folder, bills, api, request, get_pdf, pdf_text, minutes=15):
    """Read the titles still missing or out of date for one session, for at most `minutes`."""
    out = os.path.join(folder, "titles")
    asked_path = os.path.join(out, "asked.json")
    asked = load(asked_path, {})
    week = (TODAY - timedelta(days=7)).isoformat()
    queue = []
    for k, b in bills.items():
        if not re.fullmatch(r"(?:HB|SB)\d+", k):
            continue
        have = load(os.path.join(out, f"{k}.json"), {})
        if have.get("v") == version_of(b) or asked.get(k, "") >= week and asked.get(f"{k}:v") == version_of(b):
            continue
        law = bool(b.get("sessionLawChapterNumber"))
        steps = len((b.get("draft") or {}).get("billStatuses") or b.get("billActions") or [])
        queue.append((not law, -steps, k))
    queue.sort()
    stop_at = time.time() + minutes * 60
    got = tried = 0
    os.makedirs(out, exist_ok=True)
    for _, _, k in queue:
        if time.time() > stop_at:
            break
        tried += 1
        b = bills[k]
        m = re.fullmatch(r"([A-Z]+)(\d+)", k)
        q = urllib.parse.urlencode({"legislatureOrdinal": 69 + (s["year"] - 2025) // 2, "sessionOrdinal": f"{s['year']}1",
                                    "billType": m.group(1), "billNumber": m.group(2)})
        found, kind = None, None
        # The current system's getBillText answers the latest version: clean when it's the introduced bill (version 1)
        # or the enrolled one (a law or a vetoed bill, without the "A BILL FOR AN ACT ENTITLED" wrapper).
        if not s["archive"] and (version_of(b) == "1" or b.get("sessionLawChapterNumber")
                                 or re.search(r"veto", json.dumps(b), re.I)):
            body = get_pdf(f"{api}/docs/v1/documents/getBillText?{q}")
            found = title_of(pdf_text(body) or "") if body else None
            if found and found[2] and version_of(b) != "1":
                found = None  # not enrolled after all: an amended version
            kind = "introduced" if found and found[2] else "passed"
        if not found:
            link, kind = clean_version(request(f"{api}/docs/v1/documents/getBillVersions?{q}", f"{s['year']} {k} versions"))
            body = get_pdf(link) if link else None
            found = title_of(pdf_text(body) or "") if body else None
        if not found:
            asked[k], asked[f"{k}:v"] = TODAY.isoformat(), version_of(b)
            save(asked, asked_path)
            continue
        save({"v": version_of(b), "as": kind, "title": found[0], "case": found[1], "read": TODAY.isoformat()},
             os.path.join(out, f"{k}.json"))
        asked.pop(k, None), asked.pop(f"{k}:v", None)
        got += 1
    save(asked, asked_path)
    print(f"{s['year']}: titles: {got} read now, {len(queue) - got} still to read", flush=True)


def short_title(b):
    return (b.get("draft") or {}).get("shortTitle") or b.get("shortTitle") or ""


def write(year, folder, bills, data):
    """texts_<year>.json from the session's titles."""
    out = {}
    tdir = os.path.join(folder, "titles")
    for name in sorted(os.listdir(tdir)) if os.path.isdir(tdir) else []:
        k = name[:-5]
        if not name.endswith(".json") or k not in bills:
            continue
        t = load(os.path.join(tdir, name), {})
        s = statement(t.get("title") or "", t.get("case") or {}, short_title(bills[k]))
        if s:
            out[k] = {"statement": s, "label": LABEL.get(t.get("as"), LABEL["introduced"])}
    if out:
        save(out, os.path.join(data, f"texts_{year}.json"))
    print(f"{year} texts: {len(out)} bills", flush=True)
