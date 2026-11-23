#!/usr/bin/env python3
""""What it does" for Washington bills with no bill report: a lead quoted from the bill's own text (states/billtext_lead.py).

Washington's staff write a bill report only once a committee hears the bill, so about a third of a biennium's bills
(HB 1810 of 2025-26) have none. For those, this reads the bill as introduced (the web services' "Bills" documents,
GetDocumentsByClass; the page at lawfilesext.leg.wa.gov, which has no robots.txt) and keeps its sections: each
"NEW SECTION." is new law; an amended section ("RCW 46.92.010 and 2021 c 193 s 1 are each amended to read as follows:")
shows deleted wording struck through in (( )) and new wording underlined, so only its underlined whole sentences count.

The sections are kept in data/wa/<session>/leads.json by bill, with the document's name and date (a version is read
once, ever); the lead is worked out from them each run, so a change to its rules needs no download. At most
five minutes a run, a page a second; the current biennium first (the bills acted on latest first), then the next
biennium's prefiled bills. texts.py puts the leads in texts_<session>.json for bills with no report.
Usage: python3 states/wa/billtext.py [session] [minutes] [HB1810 ...]
"""
import html, json, os, re, sys, time, urllib.parse, urllib.request
from html.parser import HTMLParser

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
from states import billtext_lead as L
from states.wa import profile as P
from states.wa.fetch import AGENT, BILL_ID, call, rows

PAUSE = 1.0  # seconds between pages


class _Reader(HTMLParser):
    """The bill's text as paragraphs of (text, underlined) runs, with deleted ((struck)) wording left out."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.paras, self.runs, self.stack, self.section_start = [], [], [], []

    def handle_starttag(self, tag, attrs):
        if tag == "div":
            self.flush()
        style = (dict(attrs).get("style") or "").replace(" ", "")
        if tag == "span":
            self.stack.append("u" if "underline" in style else "x" if "line-through" in style else "")

    def handle_endtag(self, tag):
        if tag == "span" and self.stack:
            self.stack.pop()
        elif tag == "div":
            self.flush()

    def handle_comment(self, data):
        if "BeginningSection" in data:
            self.flush()
            self.section_start.append(len(self.paras))

    def handle_data(self, data):
        if "x" in self.stack:
            return
        self.runs.append((data, "u" in self.stack))

    def flush(self):
        if self.runs and "".join(t for t, _ in self.runs).strip():
            self.paras.append(self.runs)
        self.runs = []


AMENDED = re.compile(r"^(?:Sec\.\s*\d+\.\s*)?((?:RCW|RCW\s)?\s*[\d.A-Za-z]+(?:\s+and\s+[\d]{4}.*?)?)\s+(?:are|is)\s+each\s+(?:amended|reenacted and amended)", re.I)


def sections(page):
    """The bill's sections (billtext_lead's Section dicts), and its title."""
    r = _Reader()
    r.feed(page)
    r.flush()
    # (A deletion leaves its brackets: "(())Except as provided ...".)
    text = lambda runs: L.clean(re.sub(r"\(\(\s*\)\)", "", "".join(t for t, _ in runs).replace("\xa0", " ")))
    title = next((text(p) for p in r.paras if text(p).startswith("AN ACT")), "")
    out = []
    bounds = r.section_start + [len(r.paras)]
    for a, b in zip(bounds, bounds[1:]):
        paras = r.paras[a:b]
        if not paras:
            continue
        first = text(paras[0])
        if first.startswith("--- END ---"):
            continue
        new = bool(re.match(r"^NEW SECTION\.", first))
        head = re.sub(r"^(?:NEW SECTION\.\s*)?Sec\.\s*(\d+)\.\s*", "", first)
        num = (re.search(r"Sec\.\s*(\d+)", first) or [None, ""])[1]
        body = [head] + [text(p) for p in paras[1:]]
        body = [re.sub(r"\s*--- END ---$", "", p) for p in body if p and p != "--- END ---"]
        sec = {"num": num, "new": new, "paras": body, "added": [], "cite": "", "repeal": False}
        if not new:
            m = re.match(r"^(RCW\s+[\d.A-Za-z]+)(?:,\s*[\d.A-Za-z ]+)*\s+(?:and\s+.+?\s+)?(?:are|is)\s+each\s+(?:amended|reenacted)", head)
            if m:
                sec["cite"] = re.sub(r"\s+", " ", m.group(1))
                # Underlined runs, each a stretch of wording the amendment adds; whole sentences only.
                for p in paras[1:]:
                    cur = ""
                    for t, u in p + [("|", False)]:
                        if u or not t.strip():
                            cur += t  # (spaces between underlined spans don't end a stretch)
                            continue
                        s = L.clean(cur)
                        if s.endswith(".") and len(s) >= 60:
                            sec["added"].append(s)
                        cur = ""
            elif re.search(r"(?:are|is) (?:each )?repealed", head):
                sec["repeal"] = True
            else:
                sec["new"] = None  # (a section that doesn't say: a few bills number new sections without the label)
        if new and re.search(r"(?:are|is) (?:each )?(?:hereby )?repealed", head):
            sec["repeal"] = True
        out.append(sec)
    return out, title


def get(url):
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": AGENT})
            with urllib.request.urlopen(req, timeout=60) as resp:
                return resp.read().decode("utf-8-sig", "replace")
        except Exception:
            time.sleep(3 * (attempt + 1))
    return None


def originals(session):
    """Bill key ("HB1810") -> (document name, date, url) of the bill as introduced (the web services' "Bills" list)."""
    bien = P.biennium(session)
    out = {}
    for digit in "124568":
        for d in rows(call("LegislativeDocumentService", "GetDocumentsByClass", biennium=bien, documentClass="Bills", namedLike=digit)):
            name = d.get("Name") or ""
            if not re.fullmatch(r"\d{4}", name):
                continue  # substitutes ("1810-S"), engrossed and session law versions
            jr = BILL_ID.match(d.get("BillId") or "")
            if jr and jr.group(1).endswith("JR"):
                key = jr.group(1) + jr.group(2)
            elif name[0] in "48":
                continue
            else:
                key = ("HB" if int(name) < 5000 else "SB") + name
            url = (d.get("HtmUrl") or "").replace("http://", "https://")
            if url:
                out[key] = (name, d.get("HtmLastModifiedDate") or "", url)
    return out


def path(session):
    return os.path.join(P.DATA, str(session), "leads.json")


def load(session):
    try:
        return json.load(open(path(session)))
    except (OSError, ValueError):
        return {}


def wanted(session, reported):
    """The biennium's bills with no bill report (`reported`: texts.reports()), the latest acted on first."""
    out = []
    for f in os.listdir(os.path.join(P.DATA, str(session), "bills")) if os.path.isdir(os.path.join(P.DATA, str(session), "bills")) else []:
        k = f[:-5]
        if not f.endswith(".json") or k in reported:
            continue
        try:
            vers = json.load(open(os.path.join(P.DATA, str(session), "bills", f))).get("versions") or []
        except (OSError, ValueError):
            continue
        last = max(((v.get("CurrentStatus") or {}).get("ActionDate") or v.get("IntroducedDate") or "" for v in vers), default="")
        out.append((last, k))
    return [k for _, k in sorted(out, reverse=True)]


def main(session, want, minutes=5):
    """Reads the texts of the bills in `want` (keys, most wanted first) not read yet, for at most `minutes` a run."""
    until = time.time() + 60 * minutes
    cache = load(session)
    docs = originals(session) if want else {}
    todo = [(k, docs[k]) for k in want if k in docs and cache.get(k, {}).get("date") != docs[k][1]]
    read = 0
    for k, (name, date, url) in todo:
        if time.time() > until:
            break
        page = get(urllib.parse.quote(url, safe=":/"))
        time.sleep(PAUSE)
        if page is None:
            continue
        secs, title = sections(page)
        cache[k] = {"name": name, "date": date, "sections": L.compact(secs)}
        read += 1
        if read % 50 == 0:
            save(session, cache)
    save(session, cache)
    print(f"{session} leads.json: {len(cache)} bill texts ({read} read now, {max(0, len(todo) - read)} left)")
    return cache


def save(session, cache):
    for v in cache.values():
        v["sections"] = L.compact(v["sections"])
        v.pop("lead", None), v.pop("v", None)
    tmp = path(session) + ".tmp"
    json.dump(cache, open(tmp, "w"), ensure_ascii=False)
    os.replace(tmp, path(session))


def entries(session):
    """Bill key -> {"statement", "label"} for texts_<session>.json, from the leads read so far."""
    out = {}
    for k, v in load(session).items():
        text, label = L.statement(L.lead(v["sections"]))  # (worked out each time: a change to the rules needs no download)
        if text:
            out[k] = {"statement": text, "label": label}
    return out


if __name__ == "__main__":
    from states.wa import texts
    s = int(sys.argv[1]) if len(sys.argv) > 1 else P.session_of(time.localtime().tm_year)
    main(s, sys.argv[3:] or wanted(s, texts.reports(s)), float(sys.argv[2]) if len(sys.argv) > 2 else 5)
