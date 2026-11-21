#!/usr/bin/env python3
"""Download every bill in a NY legislative session from the Senate Open Legislation API
and save a slimmed copy (no full text or memos) to data/bills_<session>.json, and what each bill does (the purpose
and summary of provisions from the sponsor's memo, Senate bills only: the API has no Assembly memos) to
data/texts_<session>.json, which build_data.py shows as "What it does".

Usage: python3 fetch_bills.py [session_year] [--if-changed]   (default 2025, i.e. the 2025-26 session)
  --if-changed: when the saved copy (data/bills_<session>.json, with the Senate memos it was made with in
  data/senate_memos_<session>.json) is there and the API lists no bill updated since it was made
  (/api/3/bills/updates/<from>/<to>), the bills aren't downloaded again (publish.yml keeps the copy in its cache); "What
  it does" is still written again, with the Assembly memos as they are now. The updates list counts the governor's
  veto and approval messages too, which arrive days after the action (scope "Bill Veto", from VETOMSG files: S8432 of
  2025, vetoed 2025-12-19, its message processed 2026-01-01; checked 2026-11-21), so a message that arrives later is
  downloaded on the next run.
API key comes from the NYSENATE_API_KEY environment variable, or else ~/.nysenate_api_key.
"""
import json, os, re, sys, time, urllib.request, urllib.parse
from datetime import datetime
from zoneinfo import ZoneInfo

IF_CHANGED = "--if-changed" in sys.argv
_args = [a for a in sys.argv[1:] if not a.startswith("--")]
SESSION = int(_args[0]) if _args else 2025
KEY = os.environ.get("NYSENATE_API_KEY") or open(os.path.expanduser("~/.nysenate_api_key")).read().strip()
BASE = f"https://legislation.nysenate.gov/api/3/bills/{SESSION}"
PAGE = 200
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", f"bills_{SESSION}.json")


def get(offset):
    q = urllib.parse.urlencode({"key": KEY, "limit": PAGE, "offset": offset, "full": "true"})
    for attempt in range(5):
        try:
            with urllib.request.urlopen(f"{BASE}?{q}", timeout=180) as r:
                return json.load(r)
        except Exception as e:
            print(f"  retry {attempt + 1} at offset {offset}: {e}", file=sys.stderr)
            time.sleep(5 * (attempt + 1))
    raise SystemExit(f"failed at offset {offset}")


def items(x):
    return (x or {}).get("items") or []


TEXTS = os.path.join(os.path.dirname(OUT), f"texts_{SESSION}.json")
ASM_MEMOS = os.path.join(os.path.dirname(OUT), "ny", f"assembly_memos_{SESSION}.json")
MEMO_HEAD = re.compile(r"^\s*([A-Z][A-Z ,/&()'.-]{3,}):(?!//)\s*(.*)$")


def memo_of(b):
    """The sponsor's memo of the bill's active version, or ''."""
    am = (b.get("amendments") or {}).get("items", {}).get(b.get("activeVersion") or "") or {}
    return (am.get("memo") or "").replace("\xa0", " ")


def memo_text(memo, vocab):
    """The memo's "PURPOSE ..." and "SUMMARY OF (SPECIFIC) PROVISIONS" sections as paragraphs (not the justification,
    which argues for the bill, nor its history or fiscal note). The memo is wrapped at 72 characters with words broken
    by hyphens: "emer-\ngency" is rejoined, "non-\ncompliance" kept, by which the session's memos use elsewhere."""
    parts, keep = [], False
    para = []

    def flush():
        if para:
            s = para[0]
            for l in para[1:]:
                m, n = re.search(r"(\w+)-$", s), re.match(r"[a-z]\w*", l)
                # Rejoined unless the hyphenated form is the usual one, or the word was already hyphenated ("cost-of-").
                if m and n and not re.search(r"\w-\w+-$", s) and (
                        (m.group(1) + n.group(0)).lower() in vocab or (m.group(1) + "-" + n.group(0)).lower() not in vocab):
                    s = s[:-1] + l
                else:
                    s += ("" if m and n else " ") + l
            parts.append(s)
            para.clear()

    for line in memo.split("\n") + [""]:
        h = MEMO_HEAD.match(line)
        if h:
            flush()
            keep = h.group(1).startswith(("PURPOSE", "SUMMARY"))
            line = h.group(2)
        if not keep:
            continue
        if line.strip():
            para.append(line.strip())
        else:
            flush()
    text = "\n".join(parts)
    # A few memos (budget bills) run to pages: cut at a sentence.
    if len(text) > 5000:
        text = text[:text.rfind(". ", 0, 5000) + 1] + " …"
    return text


def slim(b):
    ver = b.get("activeVersion") or ""
    am = (b.get("amendments") or {}).get("items", {}).get(ver) or {}
    sp = b.get("sponsor") or {}
    mem = sp.get("member") or {}
    st = b.get("status") or {}
    return {
        "printNo": b["basePrintNo"],
        "activeVersion": ver,
        "chamber": (b.get("billType") or {}).get("chamber"),
        "resolution": (b.get("billType") or {}).get("resolution"),
        "title": b.get("title"),
        "summary": b.get("summary"),
        "sponsor": mem.get("fullName"),
        "sponsorShort": mem.get("shortName"),
        "district": mem.get("districtCode"),
        "budget": sp.get("budget"),
        "rules": sp.get("rules"),
        "programInfo": b.get("programInfo"),
        "signed": b.get("signed"),
        "vetoed": b.get("vetoed"),
        # The governor's note when signing, often listing changes agreed for a later bill (a chapter amendment).
        "approvalMemo": (b.get("approvalMessage") or {}).get("text"),
        # The governor's veto message, with the reasons: {year, signer, text}.
        "vetoMemo": next(({"year": m.get("year"), "signer": m.get("signer"), "text": m.get("memoText")}
                          for m in items(b.get("vetoMessages"))), None),
        "adopted": b.get("adopted"),
        "status": {k: st.get(k) for k in ("statusType", "statusDesc", "actionDate", "committeeName", "billCalNo")},
        "milestones": [{"type": m["statusType"], "date": m["actionDate"]} for m in items(b.get("milestones"))],
        "actions": [{"date": a["date"], "chamber": a["chamber"], "text": a["text"]} for a in items(b.get("actions"))],
        "pastCommittees": [{"chamber": c["chamber"], "name": c["name"], "date": c["referenceDate"]} for c in items(b.get("pastCommittees"))],
        "sameAs": [s["basePrintNo"] for s in items(am.get("sameAs"))],
        "substitutedBy": (b.get("substitutedBy") or {}).get("basePrintNo"),
        "lawSection": am.get("lawSection"),
        "lawCode": am.get("lawCode"),
        "actClause": am.get("actClause"),
        "relatedLaws": {k: v.get("items", []) for k, v in ((am.get("relatedLaws") or {}).get("items") or {}).items()},
        "cosponsorCount": len(items(am.get("coSponsors"))),
        "coSponsors": [m["fullName"] for m in items(am.get("coSponsors"))],
        "multiSponsors": [m["fullName"] for m in items(am.get("multiSponsors"))],
        "publishDate": am.get("publishDate"),
        # Senate votes (floor and committee). The API has no Assembly votes; see fetch_assembly_votes.py.
        "votes": [{
            "type": v.get("voteType"),
            "date": v.get("voteDate"),
            "committee": (v.get("committee") or {}).get("name"),
            "printNo": (v.get("billId") or {}).get("printNo"),
            "counts": {k: g.get("size", 0) for k, g in ((v.get("memberVotes") or {}).get("items") or {}).items()},
            "notYes": [[m.get("fullName"), m.get("districtCode"), k]
                       for k, g in ((v.get("memberVotes") or {}).get("items") or {}).items()
                       if k not in ("AYE", "AYEWR") for m in (g.get("items") or [])],
        } for v in items(b.get("votes"))],
        "previousVersions": [{"session": p["session"], "printNo": p["basePrintNo"]} for p in items(b.get("previousVersions"))],
    }


SENATE_MEMOS = os.path.join(os.path.dirname(OUT), f"senate_memos_{SESSION}.json")
NY_TIME = "%Y-%m-%dT%H:%M:%S"


def updated_since(since):
    """How many bill updates the API has processed since since (New York time, NY_TIME), or None if it can't say."""
    now = datetime.now(ZoneInfo("America/New_York")).strftime(NY_TIME)
    q = urllib.parse.urlencode({"key": KEY, "limit": 1})
    try:
        with urllib.request.urlopen(f"https://legislation.nysenate.gov/api/3/bills/updates/{since}/{now}?{q}", timeout=60) as r:
            d = json.load(r)
    except Exception as e:
        print(f"  updates not read ({e}); downloading everything", file=sys.stderr)
        return None
    return d.get("total") if d.get("success") else None


def main():
    if IF_CHANGED:
        try:
            saved = json.load(open(SENATE_MEMOS))
            bills = json.load(open(OUT))["bills"]
        except (OSError, ValueError, KeyError):
            saved = bills = None
        # (From an hour before the last download began, so an update processed while it ran isn't missed.)
        n = updated_since(saved["asOf"]) if saved and bills and saved.get("session") == SESSION else None
        if n == 0:
            print(f"No bill updated since {saved['asOf']}: kept the {len(bills)} bills downloaded then", file=sys.stderr)
            write_texts(bills, saved["memos"])
            return
        if n:
            print(f"{n} bill updates since {saved['asOf']}", file=sys.stderr)
    began = datetime.now(ZoneInfo("America/New_York"))
    first = get(1)
    total = first["total"]
    if total == 0:
        # A new session before its first bills are filed: keep the previous session as current.
        print(f"No bills yet in the {SESSION} session; nothing written.", file=sys.stderr)
        return
    out = [slim(b) for b in first["result"]["items"]]
    memos = {b["basePrintNo"] + (b.get("activeVersion") or ""): memo_of(b) for b in first["result"]["items"]}
    print(f"{total} bills in {SESSION} session", file=sys.stderr)
    offset = 1 + PAGE
    while offset <= total:
        d = get(offset)
        out += [slim(b) for b in d["result"]["items"]]
        memos.update({b["basePrintNo"] + (b.get("activeVersion") or ""): memo_of(b) for b in d["result"]["items"]})
        print(f"  {len(out)}/{total}", file=sys.stderr)
        offset += PAGE
    tmp = OUT + ".tmp"
    with open(tmp, "w") as f:
        json.dump({"session": SESSION, "fetched": datetime.now(ZoneInfo("America/New_York")).strftime("%Y-%m-%d %H:%M ET"), "bills": out}, f)
    os.replace(tmp, OUT)
    print(f"wrote {len(out)} bills to {OUT}", file=sys.stderr)
    from datetime import timedelta
    with open(SENATE_MEMOS + ".tmp", "w") as f:
        json.dump({"session": SESSION, "asOf": (began - timedelta(hours=1)).strftime(NY_TIME), "memos": memos}, f, ensure_ascii=False)
    os.replace(SENATE_MEMOS + ".tmp", SENATE_MEMOS)
    write_texts(out, memos)


def write_texts(out, memos):
    """What each bill does (data/texts_<session>.json), from the Senate sponsors' memos (memos: print number with its
    version -> memo) and the Assembly's."""
    # The Assembly sponsors' memos, downloaded from nyassembly.gov by states/ny/memos.py (on GitHub, into its own saved
    # copy): each Assembly bill's memo for its current version, else for the newest earlier one until that's read.
    asm = {}
    if os.path.exists(ASM_MEMOS):
        by_bill = {}
        for k, m in json.load(open(ASM_MEMOS)).items():
            if m:
                by_bill.setdefault(re.sub(r"[A-Z]$", "", k), []).append((k, m))
        for b in out:
            if b["chamber"] == "ASSEMBLY":
                n = b["printNo"] + (b["activeVersion"] or "")
                older = sorted((k, m) for k, m in by_bill.get(b["printNo"], []) if k <= n)
                if older:
                    asm[n] = older[-1][1]
    # Words as the memos write them, and each hyphenated pair within longer ones ("of-living" from "cost-of-living").
    vocab = {w.lower() for m in list(memos.values()) + list(asm.values()) for w in re.findall(r"[A-Za-z]+(?:-[A-Za-z]+)*", m)}
    vocab |= {f"{a}-{b}" for w in vocab if w.count("-") > 1 for a, b in zip(w.split("-"), w.split("-")[1:])}
    texts = {n: {"statement": t, "label": "From the Senate sponsor's memo."}
             for n, t in ((n, memo_text(m, vocab)) for n, m in memos.items() if m) if t}
    texts.update({n: {"statement": t, "label": "From the Assembly sponsor's memo."}
                  for n, t in ((n, memo_text(m, vocab)) for n, m in asm.items()) if t})
    with open(TEXTS + ".tmp", "w") as f:
        json.dump(texts, f, ensure_ascii=False)
    os.replace(TEXTS + ".tmp", TEXTS)
    print(f"wrote what {len(texts)} bills do to {TEXTS}", file=sys.stderr)


if __name__ == "__main__":
    main()
