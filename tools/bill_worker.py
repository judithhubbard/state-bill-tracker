"""Writes the bill links' Pages Function into the built site (build_site.sh): DIR/_worker.js from lists_pages/bill_worker.js
with the site's address and each folder's name filled in, DIR/_routes.json giving it only /*/bill/*, and each state's
link preview card (tools/cards/<st>.png, made by tools/state_cards.sh) at DIR/cards/. Usage: python3 tools/bill_worker.py DIR"""
import json
import os
import shutil
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import site_meta  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
NAMES = {"al": "Alabama", "ak": "Alaska", "az": "Arizona", "ar": "Arkansas", "ca": "California", "co": "Colorado",
         "ct": "Connecticut", "dc": "District of Columbia", "de": "Delaware", "fl": "Florida", "ga": "Georgia", "hi": "Hawaii",
         "id": "Idaho", "il": "Illinois", "in": "Indiana", "ia": "Iowa", "ks": "Kansas", "ky": "Kentucky", "la": "Louisiana",
         "me": "Maine", "md": "Maryland", "ma": "Massachusetts", "mi": "Michigan", "mn": "Minnesota", "ms": "Mississippi",
         "mo": "Missouri", "mt": "Montana", "ne": "Nebraska", "nv": "Nevada", "nh": "New Hampshire", "nj": "New Jersey",
         "nm": "New Mexico", "ny": "New York", "nc": "North Carolina", "nd": "North Dakota", "oh": "Ohio", "ok": "Oklahoma",
         "or": "Oregon", "pa": "Pennsylvania", "ri": "Rhode Island", "sc": "South Carolina", "sd": "South Dakota",
         "tn": "Tennessee", "tx": "Texas", "ut": "Utah", "vt": "Vermont", "va": "Virginia", "wa": "Washington",
         "wv": "West Virginia", "wi": "Wisconsin", "wy": "Wyoming", "us": "Congress"}


def main(out):
    src = open(os.path.join(HERE, "..", "lists_pages", "bill_worker.js"), encoding="utf-8").read()
    src = src.replace("const ROOT = __ROOT__;", f"const ROOT = {json.dumps(site_meta.root())};", 1) \
             .replace("const NAMES = __NAMES__;", f"const NAMES = {json.dumps(NAMES)};", 1)
    assert "= __" not in src, "bill_worker.js: a placeholder wasn't filled in"
    open(os.path.join(out, "_worker.js"), "w", encoding="utf-8").write(src)
    with open(os.path.join(out, "_routes.json"), "w") as f:
        json.dump({"version": 1, "include": ["/*/bill/*"], "exclude": []}, f)
    os.makedirs(os.path.join(out, "cards"), exist_ok=True)
    for st in NAMES:
        card = os.path.join(HERE, "cards", f"{st}.png")
        if os.path.exists(card):
            shutil.copyfile(card, os.path.join(out, "cards", f"{st}.png"))


if __name__ == "__main__":
    main(sys.argv[1])
