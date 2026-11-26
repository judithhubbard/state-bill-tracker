"""Bills whose contents became law inside a larger bill (2026-11-26, the owner: Minnesota's HF 642, the National Popular
Vote compact, "died in committee" while the compact became law in the 2023 omnibus HF 1830, chapter 62).

A bill's own record says so where the legislature writes it ("Incorporated into SB 2508", "Language included in
HB 5001", "Amended into HB 7"); a state's profile adds what the record doesn't say, each with its source (PART_OF:
{session: {number: [the law's number, the source]}}). Only a law (stage 5) of the same session counts, and only for a
bill that didn't reach the governor itself; constitutional amendments are left out.

build_data.py's rows carry it (the last column: [the law's number, its chapter, the day it became law]); the page's
status words say "Passed as part of HF1830" (lists_pages/billfacts.js) and the bill's panel links the law. The bill
keeps its own stage, so Statistics' odds count it as it went: a separate bill that stopped (counting it as a law would
count the omnibus's one law twice).
"""
import re

LINE = re.compile(
    r"\b(?:incorporated (?:in|into)|(?:language|provisions|contents|substance|text|parts?)(?: of (?:this|the) (?:bill|measure))?"
    r"(?: (?:was|were|is|are))? (?:included|incorporated|inserted|placed|amended) (?:in|into)|amended into|rolled into|folded into|for final disposition(?: of [a-z ]+?)?,? see|"
    # (Virginia's committees: "Incorporated by Courts of Justice (HB1912-Reaser)".)
    r"incorporated by [A-Za-z &,.'-]{3,60}? \()"
    r"\s*(?:the\s+)?(?:(?:CS|CCS|HCS|SCS|SS|HS|SA|HA)\s*/?\s*|Com\.\s*Sub\.\s*for\s+)*((?:[HSAL]\.?\s?[A-Z]{0,3}\.?|[A-Z]{1,3})\s?\d{1,5}[A-Z]?)\b", re.I)

# The same said of the bill in its own summary, about this bill ("Provisions of this bill have been incorporated into Bill
# 25-131", DC's legislative notes; "these provisions were included in SB 156, which was passed", Kansas's supplemental
# notes). "Similar provisions were included in ..." isn't this bill: left out.
SUMMARY = re.compile(
    r"(?<![Ss]imilar )(?:(?:provisions|contents|language) of this (?:bill|measure)|these provisions|its provisions|(?<=\n)provisions|this bill) "
    r"(?:have been|has been|were|was|are) (?:included|incorporated) in(?:to)? (?:enacted )?(?:\d{4} )?((?:[HS]B|[HS]F|Bill) ?[\d-]+)\b", re.I)
# A law's own summary naming the bills it took in (Nebraska's omnibus bills: "also adds LB55, LB57, ... and LB627 to LB261").
ADDS = re.compile(r"\badds ((?:LB ?\d+[A-Z]?,? (?:and )?){2,})to (LB ?\d+[A-Z]?)\b")
# Lines about something other than the bill: Alaska's fiscal notes ("FN1: (MVA) INCORPORATED INTO SB 154"), amendments.
NOT = re.compile(r"^\s*FN\s?\d|fiscal note|\bamendment\b[^.]{0,40}(?:incorporated|included)|^\s*(?:floor |committee )?amendment", re.I)
# Distinctive words, for checking a record line's law is about the same thing: Connecticut writes "INCORPORATED IN" when a
# proposed bill is drafted into a committee's bill in January, and some of those committee bills became something else
# (2025's "Sunday hunting" into HB 6277, which became law about adopting animals).
STOP = {"which", "would", "their", "there", "these", "those", "other", "about", "concerning", "relating", "requiring",
        "providing", "certain", "state", "states", "amendment", "amending", "establish", "establishing", "regarding",
        "including", "under", "within", "makes", "changes", "various", "revisions", "minor", "technical", "program",
        "programs", "department", "general", "statutes", "section", "sections"}
words = lambda t: {w for w in re.findall(r"[a-z]{5,}", (t or "").lower()) if w not in STOP}
key = lambda n: re.sub(r"[^A-Z0-9]", "", (n or "").upper())
base = lambda n: re.sub(r"(?<=\d)[A-Z]$", "", key(n))


def statements(folder, session):
    """{number: the "What it does" text kept in data/<state>/texts_<session>.json} (where the District's legislative
    notes are), or {}."""
    import json, os
    path = os.path.join(folder, f"texts_{session}.json")
    try:
        raw = json.load(open(path))
    except (OSError, ValueError):
        return {}
    return {n: v.get("statement") or "" for n, v in raw.items() if isinstance(v, dict)}


def find(recs, fixed=None, number=None, texts=None):
    """{record index: [the law's first number, its chapter, the day it became law (YYYYMMDD)]}. fixed: the profile's
    PART_OF for the session; number: the profile's part_of_number(text), a number as the session's records write it, or
    None when it's another session's (the District's "Bill 25-131")."""
    number = number or (lambda t: t)
    by = {}
    for j, r in enumerate(recs):
        for n in r["nums"]:
            by.setdefault(key(n), j)
            by.setdefault(base(n), j)
    fixed = {key(k): v for k, v in (fixed or {}).items()}
    # (The laws that name the bills they took in.)
    taken = {}
    for j, r in enumerate(recs):
        if r["stage"] != 5:
            continue
        for t in [r.get("summary")] + [(texts or {}).get(n) for n in r["nums"]]:
            for m in ADDS.finditer(t or ""):
                if by.get(key(m.group(2))) == j:
                    for n in re.findall(r"LB ?\d+[A-Z]?", m.group(1)):
                        taken.setdefault(key(n), j)
    out = {}
    for i, r in enumerate(recs):
        if r["stage"] >= 4 or "const" in (r["topics"] or []):
            continue
        target = next((by.get(key(fixed[key(n)][0])) for n in r["nums"] if key(n) in fixed), None)
        if target is None:
            target = next((taken[key(n)] for n in r["nums"] if key(n) in taken and taken[key(n)] != i), None)
        if target is None:
            m = next(filter(None, (SUMMARY.search(t or "") for t in [r.get("summary")] + [(texts or {}).get(n) for n in r["nums"]])), None)
            n = m and number(m.group(1))
            if n:
                j = by.get(key(n), by.get(base(n)))
                if j is not None and j != i:
                    target = j
        if target is None:
            # (Each history line, and the source's own status wording where a converter keeps it: West Virginia's list.)
            for v in r["vers"] + ([{"actions": [["", r["statusLine"]]]}] if r.get("statusLine") else []):
                for a in v["actions"]:
                    m = LINE.search(a[1] or "") if not NOT.search(a[1] or "") else None
                    n = m and number(m.group(1))
                    if n:
                        j = by.get(key(n), by.get(base(n)))
                        # (Only a bare "incorporated into" needs it: "its provisions were amended into", "final disposition
                        # ... see" say the contents went there.)
                        strong = re.search(r"provisions|language|contents|substance|amended into|final disposition", a[1], re.I)
                        about = j is not None and (bool(strong) or bool(words(r["title"]) & words(" ".join(
                            [recs[j]["title"], recs[j].get("summary") or ""] + [(texts or {}).get(x) or "" for x in recs[j]["nums"]]))))
                        if j is not None and j != i and about:
                            target = j
        if target is None or recs[target]["stage"] != 5:
            continue
        t = recs[target]
        signed = (t["keyDates"][5] if len(t["keyDates"]) > 5 else "") or ""
        out[i] = [t["nums"][0], t["chapter"] or 0, (signed.split(";")[-1] or t["last"] or "").replace("-", "")]
    return out
