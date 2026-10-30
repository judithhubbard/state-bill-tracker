#!/usr/bin/env python3
"""What each bill does, in the Legislature's own words: the Legislative Counsel's Digest at the top of the bill's
latest version ("Existing law ... This bill would ..."), and the version's title, which names the code sections it
changes. Written as data/ca/texts_<session>.json in the shape build_data.py's bill_texts() reads:
{"AB1": {"statement": ..., "label": "From the Legislative Counsel's Digest of the bill as passed."}}.

The texts are inside each version's file in the pubinfo zip, numbered differently in each day's zip, so they are
read from the same zip as the tables (fetch.py calls update() right after saving them). Versions already read are
kept in data/ca/<session>/digests.json, so a day's run reads only new versions.

Usage: python3 states/ca/texts.py [session ...]   (writes texts_<session>.json from what's been read)
"""
import html, json, os, re, sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
from states.ca import profile as P
from states.ca.convert import folder, rows, sessions

LABEL = {"Introduced": "as introduced", "Amended Assembly": "as amended in the Assembly",
         "Amended Senate": "as amended in the Senate", "Enrolled": "as passed", "Chaptered": "as enacted",
         "Vetoed": "as passed"}


def plain(h):
    # Processing instructions (<?xm-replace_text ... ?>) hold markup of their own; drop them whole.
    h = re.sub(r"(?s)<\?.*?\?>", "", h)
    h = re.sub(r"\s+", " ", h)  # line breaks in the file aren't paragraph breaks
    h = re.sub(r"(?i)</(?:xhtml:)?p>|<br\s*/?>", "\n", h)
    t = html.unescape(re.sub(r"<[^>]+>", "", h))
    return "\n".join(p for p in (re.sub(r"\s+", " ", x).strip() for x in t.split("\n")) if p)


def cache_path(session):
    return os.path.join(folder(session), "digests.json")


def load(session):
    try:
        return json.load(open(cache_path(session)))
    except (OSError, ValueError):
        return {}


def latest(session):
    """Each regular-session AB and SB's latest version: version id -> (bill, its .lob file in the zip, action)."""
    want = {r[10]: f"{r[3]}{r[4]}" for r in rows(session, "BILL") if r[2] == "0" and r[3] in ("AB", "SB") and r[10]}
    out = {}
    for r in rows(session, "BILL_VERSION"):
        if r[0] in want and r[14]:
            out[r[0]] = (want[r[0]], r[14], r[4] or "")
    return out


def update(session, z):
    """Read the digests of versions not read before, from the zip the tables were just saved from."""
    cache = load(session)
    # Versions read before processing instructions were dropped (their text has markup in it) are read again.
    todo = {vid: v for vid, v in latest(session).items() if vid not in cache or "xhtml:" in cache[vid]["digest"]}
    if todo:
        got = z.read([lob for _, lob, _ in todo.values()], gap=2 << 20)
        bad = 0
        for vid, (p, lob, _) in todo.items():
            x = got.get(lob, b"").decode("utf-8", "replace")
            m = re.search(r"<caml:Id>([^<]+)</caml:Id>", x)
            # A file that isn't this version's (the zip was replaced while it was being read) waits for the next run.
            # The file writes the number padded: "20210AB__001698AMD" for 20210AB1698AMD.
            if not m or re.sub(r"([A-Z]+)_*0*(?=\d)", r"\1", m.group(1)) != vid:
                bad += 1
                continue
            digest = re.search(r"<caml:DigestText>(.*?)</caml:DigestText>", x, re.S)
            title = re.search(r"<caml:Title>(.*?)</caml:Title>", x, re.S)
            cache[vid] = {"digest": plain(digest.group(1)) if digest else "", "act": plain(title.group(1)) if title else ""}
        json.dump(cache, open(cache_path(session), "w"), ensure_ascii=False)
        print(f"{session}: read {len(todo) - bad} bill texts" + (f" ({bad} didn't match, left for next time)" if bad else ""))
    write(session)


def write(session):
    cache = load(session)
    out = {}
    for vid, (p, _, action) in latest(session).items():
        c = cache.get(vid)
        if c and c["digest"]:
            # What the bill would do first: the digest opens with existing law, so its first "This bill would"
            # paragraph moves to the top.
            # (Texts read before line breaks were handled have paragraphs split mid-sentence: join them back.)
            paras = []
            for x in c["digest"].split("\n"):
                if paras and not re.search(r"[.:;?!)\"”]$", paras[-1]):
                    paras[-1] += " " + x
                else:
                    paras.append(x)
            i = next((k for k, x in enumerate(paras) if re.match(r"(This|The) bill would", x)), 0)
            text = "\n".join([paras[i]] + paras[:i] + paras[i + 1:])
            out[p] = {"statement": text, "label": f"From the Legislative Counsel's Digest of the bill {LABEL.get(action, 'as amended')}."}
    json.dump(out, open(os.path.join(P.DATA, f"texts_{session}.json"), "w"), ensure_ascii=False)
    print(f"texts_{session}.json: {len(out)} digests")


if __name__ == "__main__":
    for s in (map(int, sys.argv[1:]) if len(sys.argv) > 1 else sessions()):
        write(s)
