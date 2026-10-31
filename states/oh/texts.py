#!/usr/bin/env python3
""""What it does" for Ohio: each bill's long title, from its purpose on (the Legislative Service Commission's analyses are
on legislature.ohio.gov, which turns automated requests away; see the oh-data-sources memory). From the bills already
downloaded by states/oh/fetch.py; no requests. Writes data/oh/texts_<session>.json in the shape build_data.py's
bill_texts() reads. Usage: python3 states/oh/texts.py
"""
import glob, json, os, sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
from states.oh import convert as C, profile as P


def main():
    for session in C.sessions():
        out = {}
        for f in glob.glob(os.path.join(C.folder(session), "bills", "*.json")):
            vers = json.load(open(f)).get("versions") or []
            if vers and vers[-1].get("long_title"):
                v = vers[-1]
                out[os.path.basename(f)[:-5]] = {"statement": C.purpose(v["long_title"]),
                                                 "label": f"From the bill's title ({v.get('version', '').lower()})."}
        json.dump(out, open(os.path.join(P.DATA, f"texts_{session}.json"), "w"), ensure_ascii=False)
        print(f"texts_{session}.json: {len(out)} titles")


if __name__ == "__main__":
    main()
