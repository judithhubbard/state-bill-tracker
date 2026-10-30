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
    """Bill -> the address of its latest analysis (the last listed version)."""
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
            out[p] = urls[-1]
    return out


def statement(page):
    """The analysis's summary paragraph(s), as plain text."""
    t = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", re.sub(r"(?is)<(script|style).*?</\1>", "", page))))
    m = re.search(r"(?:BACKGROUND AND PURPOSE|STATEMENT OF INTENT)\s*(.+?)\s*(?:\(Original Author's/Sponsor's Statement of Intent\)|CRIMINAL JUSTICE IMPACT|RULEMAKING AUTHORITY|ANALYSIS\b)", t)
    if not m:
        return ""
    text = m.group(1).strip()
    # What the bill does first: the statement usually opens with background, then "H.B. 6 seeks to ...".
    aim = re.search(r"(?:C\.S\.)?[HS]\.B\. \d+ (?:seeks|would|is intended|aims|attempts|proposes)", text)
    if aim and aim.start() > 0:
        text = text[aim.start():] + "\n" + text[:aim.start()].strip()
    return text


def get(url):
    for attempt in range(3):
        r = subprocess.run(["curl", "-sS", "--max-time", "120", url], capture_output=True)
        if r.returncode == 0:
            return r.stdout.decode("cp1252", "replace")
        time.sleep(3 * (attempt + 1))
    return None


def main(session):
    path = os.path.join(P.DATA, P.code_of(session), "analyses.json")
    try:
        cache = json.load(open(path))
    except (OSError, ValueError):
        cache = {}
    urls = analysis_urls(session)
    todo = sorted(set(urls.values()) - set(cache))
    with ThreadPoolExecutor(6) as pool:
        for k, (url, page) in enumerate(zip(todo, pool.map(get, todo))):
            if page:
                cache[url] = statement(page)
            if k % 200 == 199:
                json.dump(cache, open(path, "w"), ensure_ascii=False)
    json.dump(cache, open(path, "w"), ensure_ascii=False)
    out = {}
    for p, url in urls.items():
        text = cache.get(url)
        if text:
            v = re.search(r"([HSEF])\.htm$", url, re.I)
            out[p] = {"statement": text, "label": f"From {LABEL.get(v.group(1).upper() if v else '', 'the')} bill analysis."}
    json.dump(out, open(os.path.join(P.DATA, f"texts_{session}.json"), "w"), ensure_ascii=False)
    print(f"texts_{session}.json: {len(out)} bill analyses ({len(todo)} downloaded now)")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else P.session_of(datetime.now(ZoneInfo(P.TIMEZONE)).year))
