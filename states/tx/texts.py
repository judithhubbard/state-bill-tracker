#!/usr/bin/env python3
"""What each bill does, from its latest bill analysis on the Legislature's FTP site: the House Research
Organization's "Background and Purpose" or the Senate Research Center's "Author's / Sponsor's Statement of Intent",
written when a committee reports a bill. Bills no committee reported have no analysis.

The current session only (each analysis is a large file, about a second to download); analyses already read are
kept in data/tx/<code>/analyses.json by address (a version's analysis doesn't change). Writes
data/tx/texts_<session>.json in the shape build_data.py's bill_texts() reads.
Usage: python3 states/tx/texts.py [session]   (fetch.py runs it for the current session)
"""
import html, json, os, re, subprocess, sys, time
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
from states.tx import profile as P
from states.tx.convert import folder, num

LABEL = {"H": "the House committee's", "S": "the Senate committee's", "E": "the engrossed bill's", "F": "the enrolled bill's"}


def analysis_urls(session):
    """Bill -> the addresses of its analyses, latest first."""
    out = {}
    for f in os.listdir(folder(session)):
        p = num(f)
        if not p:
            continue
        try:
            t = ET.parse(os.path.join(folder(session), f)).getroot()
        except ET.ParseError:
            continue
        a = t.find("billtext/docTypes/analysis")
        urls = [v.findtext("FTPHTMLURL") for v in a.iter("version")] if a is not None else []
        urls = [u for u in urls if u]
        if urls:
            out[p] = urls[::-1]  # latest first
    return out


def statement(page):
    """The analysis's summary paragraph(s), as plain text."""
    t = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", re.sub(r"(?is)<(script|style).*?</\1>", "", page))))
    m = re.search(r"(?:BACKGROUND AND PURPOSE|STATEMENT OF INTENT)\s*(.+?)\s*(?:\(Original Author's/Sponsor's Statement of Intent\)|CRIMINAL JUSTICE IMPACT|RULEMAKING AUTHORITY|ANALYSIS\b)", t)
    return clean(m.group(1).strip()) if m else ""


def clean(text):
    """A statement with what the bill does first, or "" if it says nothing. What the bill does: the statement usually
    opens with background, then "H.B. 6 seeks to ..."."""
    text = text.replace("ï¿½", "—")  # a dash read with the wrong encoding before
    # A statement that only repeats the caption ("C.S.H.B. 2 amends current law relating to ...") says nothing.
    if re.fullmatch(r"(?:C\.S\.)?[HS]\.B\. \d+ amends current law relating to [^.]*\.?", text):
        return ""
    aim = re.search(r"(?:C\.S\.)?[HS]\.B\. \d+(?:, [^,]{1,80},)? (?:seeks|would|is intended|aims|attempts|proposes)", text) or \
        re.search(r"\bFirst, (?:C\.S\.)?[HS]\.B\. \d+", text) or \
        re.search(r"(?:^|(?<=\. ))[^.]*?(?:C\.S\.)?[HS]\.B\. \d+ [a-z]", text)
    if aim and aim.start() > 0:
        text = text[aim.start():] + "\n" + text[:aim.start()].strip()
    return text


def get(url):
    for attempt in range(3):
        r = subprocess.run(["curl", "-sS", "--max-time", "120", url], capture_output=True)
        if r.returncode == 0:
            try:
                text = r.stdout.decode("utf-8")
            except UnicodeDecodeError:
                text = r.stdout.decode("cp1252", "replace")
            return text.replace("\ufffd", "—")  # the files' own unknown characters are almost always dashes
        time.sleep(3 * (attempt + 1))
    return None


def main(session):
    path = os.path.join(P.DATA, P.code_of(session), "analyses.json")
    try:
        cache = json.load(open(path))
    except (OSError, ValueError):
        cache = {}
    urls = analysis_urls(session)
    # Each bill's latest analysis; an earlier one when the latest says nothing (its statement only repeats the caption).
    todo = sorted({us[0] for us in urls.values()} - set(cache))
    todo += sorted({u for us in urls.values() if not cache.get(us[0], "x") for u in us[1:2]} - set(cache) - set(todo))
    with ThreadPoolExecutor(6) as pool:
        for k, (url, page) in enumerate(zip(todo, pool.map(get, todo))):
            if page:
                cache[url] = statement(page)
            if k % 200 == 199:
                json.dump(cache, open(path, "w"), ensure_ascii=False)
    json.dump(cache, open(path, "w"), ensure_ascii=False)
    out = {}
    for p, us in urls.items():
        url = next((u for u in us if cache.get(u)), None)
        text = cache.get(url) if url else None
        if text:
            v = re.search(r"([HSEF])\.htm$", url, re.I)
            out[p] = {"statement": text, "label": f"From {LABEL.get(v.group(1).upper() if v else '', 'the')} bill analysis."}
    json.dump(out, open(os.path.join(P.DATA, f"texts_{session}.json"), "w"), ensure_ascii=False)
    print(f"texts_{session}.json: {len(out)} bill analyses ({len(todo)} downloaded now)")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else P.session_of(datetime.now(ZoneInfo(P.TIMEZONE)).year))
