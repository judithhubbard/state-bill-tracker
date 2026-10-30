#!/usr/bin/env python3
"""What each bill does, in the Legislature's own words: the Division of Legislative Services' summary
(Summaries.csv), the latest version of it (as introduced, as passed by one house, as passed, as enacted with
the governor's amendments). Written as data/va/texts_<year>.json in the shape build_data.py's bill_texts()
reads: {"HB1": {"statement": ..., "label": "From the Legislature's summary of the bill as passed."}}.

Usage: python3 states/va/texts.py [year ...]   (fetch.py runs it for every session)
"""
import html, json, os, re, sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
from states.va import profile as P
from states.va.convert import num, rows, sessions

# Later versions of the summary replace earlier ones.
ORDER = ["SUMMARY AS INTRODUCED", "SUMMARY AS PASSED HOUSE", "SUMMARY AS PASSED SENATE", "SUMMARY AS PASSED",
         "SUMMARY AS ENACTED WITH GOVERNOR'S RECOMMENDATION"]
LABEL = {"SUMMARY AS INTRODUCED": "as introduced", "SUMMARY AS PASSED HOUSE": "as passed by the House",
         "SUMMARY AS PASSED SENATE": "as passed by the Senate", "SUMMARY AS PASSED": "as passed",
         "SUMMARY AS ENACTED WITH GOVERNOR'S RECOMMENDATION": "as enacted with the governor's amendments"}


def plain(h):
    """The summary's HTML as paragraphs of text (its bold opening is the bill's short title)."""
    h = re.sub(r"\s+", " ", h)  # line breaks in the file aren't paragraph breaks
    h = re.sub(r"(?i)</p>|<br\s*/?>", "\n", h)
    t = html.unescape(re.sub(r"<[^>]+>", "", h))
    # The files turn some characters into "?": "§ 2.2-1509", "2026–2027", "don't".
    t = re.sub(r"(^|\s)\?(?=\s+\d)", r"\1§", t)
    t = re.sub(r"(?<=\b\d{4})\?(?=\d{4}\b)", "–", t)
    t = re.sub(r"(?<=[A-Za-z])\?(?=[A-Za-z])", "’", t)
    return "\n".join(p for p in (re.sub(r"\s+", " ", x).strip() for x in t.split("\n")) if p)


def main(session):
    best = {}
    for r in rows(session, "Summaries.csv"):
        kind = r["SUMMARY_TYPE"].strip()
        if kind not in ORDER or not r["SUMMARY_TEXT"].strip():
            continue
        bill = num(r["SUM_BILNO"])
        if bill not in best or ORDER.index(kind) >= ORDER.index(best[bill][0]):
            best[bill] = (kind, plain(r["SUMMARY_TEXT"]))
    out = {b: {"statement": text, "label": f"From the Legislature's summary of the bill {LABEL[kind]}."}
           for b, (kind, text) in best.items() if text}
    path = os.path.join(P.DATA, f"texts_{session}.json")
    json.dump(out, open(path, "w"), ensure_ascii=False)
    print(f"texts_{session}.json: {len(out)} summaries")


if __name__ == "__main__":
    for s in (map(int, sys.argv[1:]) if len(sys.argv) > 1 else sessions()):
        main(s)
