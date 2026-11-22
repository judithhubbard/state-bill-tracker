#!/usr/bin/env python3
""""What it does" for Ohio: the Legislative Service Commission's bill analysis (its summary; the newest version's, or the
final analysis of a law), read by states/oh/analyses.py into data/oh/<session>/analyses.json; else the bill's long title,
from its purpose on. From what states/oh/fetch.py already downloaded; no requests. Writes data/oh/texts_<session>.json in the shape build_data.py's
bill_texts() reads. Usage: python3 states/oh/texts.py
"""
import glob, json, os, sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
from states.oh import analyses as A, convert as C, profile as P


def main():
    for session in C.sessions():
        out, n = {}, 0
        try:
            lsc = json.load(open(os.path.join(C.folder(session), "analyses.json")))
        except (OSError, ValueError):
            lsc = {}
        for f in glob.glob(os.path.join(C.folder(session), "bills", "*.json")):
            vers = json.load(open(f)).get("versions") or []
            key = os.path.basename(f)[:-5]
            kind = "resolution" if key[1:3] == "JR" else "bill"
            a = lsc.get(key) or {}
            paras = A.read(a, (vers[-1].get("short_title") or "") if vers else "") if a.get("raw") else []
            if paras:
                out[key] = {"statement": "\n".join(paras), "label": A.label(a, a.get("doc"), kind)}
                n += 1
            elif vers and vers[-1].get("long_title"):
                v = vers[-1]
                out[key] = {"statement": C.purpose(v["long_title"]),
                            "label": f"From the {kind}'s title ({v.get('version', '').lower()})."}
        json.dump(out, open(os.path.join(P.DATA, f"texts_{session}.json"), "w"), ensure_ascii=False)
        print(f"texts_{session}.json: {n} analyses, {len(out) - n} titles")


if __name__ == "__main__":
    main()
