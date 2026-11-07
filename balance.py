#!/usr/bin/env python3
"""The balance of power in a state's legislature now: each chamber's seats by party (from the latest member list,
data/<state>/contacts_<session>.json), vacancies, the majority party, whether it can override a veto on its own, and
the governor's party (states/legislatures.json). build_data.py puts it in each state's pages and build_site.sh on the
front page; test/data_check.py checks the counts add up to each chamber's seats.

Usage: python3 balance.py STATE   (prints it)
"""
import glob, json, math, os, re, sys
from collections import Counter
from fractions import Fraction

HERE = os.path.dirname(os.path.abspath(__file__))


def party_letter(party):
    """A member's party as D, R, I (independent or unaffiliated) or O (another party). New York's ballot lines count by
    their first party ("Democratic/Working Families" is D)."""
    first = re.split(r"[/,]", party or "")[0].strip().lower()
    if first.startswith("democrat"):
        return "D"
    if first.startswith("republican"):
        return "R"
    if first.startswith(("independent", "unaffiliated", "nonpartisan", "no party")):
        return "I"
    return "O" if first else "?"


def table():
    return json.load(open(os.path.join(HERE, "states", "legislatures.json")))["states"]


def contacts_path(state):
    """The newest member list: contacts_<session>.json with the highest session (New York's are at the top of data/)."""
    paths = glob.glob(os.path.join(HERE, "data", state, "contacts_*.json")) if state != "ny" else \
        glob.glob(os.path.join(HERE, "data", "contacts_*.json"))
    paths = [p for p in paths if re.search(r"contacts_\d{4}\.json$", p)]
    return max(paths, key=lambda p: int(re.search(r"(\d{4})", os.path.basename(p)).group(1))) if paths else None


def current(state):
    """{"chambers": {letter: {seats, parties {D: n, R: n, ...}, vacant, majority, share, overrideSeats, canOverride}},
    "governor": [name, party], "unified": party or None, "note": ..., "asOf": session} or None."""
    facts = table().get(state)
    path = contacts_path(state)
    if not facts or not path:
        return None
    people = json.load(open(path)).get("people", {})
    out = {"chambers": {}, "governor": facts["governor"], "note": facts.get("note", ""),
           "asOf": int(re.search(r"(\d{4})", os.path.basename(path)).group(1))}
    frac = Fraction(facts["override"])
    for chamber, seats in facts["seats"].items():
        parties = Counter(party_letter(p.get("party")) for sid, p in people.items() if sid[0] == chamber)
        filled = sum(parties.values())
        top, n = max(parties.items(), key=lambda x: x[1]) if parties else (None, 0)
        need = math.ceil(frac * seats)
        out["chambers"][chamber] = {
            "seats": seats, "parties": dict(sorted(parties.items(), key=lambda x: -x[1])), "vacant": seats - filled,
            "majority": top if n > seats / 2 else None,  # a plurality isn't a majority
            "overrideSeats": need, "override": facts["override"], "canOverride": bool(top) and n >= need,
        }
    majorities = {c["majority"] for c in out["chambers"].values()}
    out["unified"] = out["governor"][1] if majorities == {out["governor"][1]} else None
    return out


if __name__ == "__main__":
    print(json.dumps(current(sys.argv[1]), indent=1))
