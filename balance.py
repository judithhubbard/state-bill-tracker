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
    frac = None if facts["override"] == "majority" else Fraction(facts["override"])  # Indiana: a majority of the members
    for chamber, seats in facts["seats"].items():
        parties = Counter(party_letter(p.get("party")) for sid, p in people.items() if sid[0] == chamber)
        filled = sum(parties.values())
        top, n = max(parties.items(), key=lambda x: x[1]) if parties else (None, 0)
        need = seats // 2 + 1 if frac is None else math.ceil(frac * seats)
        out["chambers"][chamber] = {
            "seats": seats, "parties": dict(sorted(parties.items(), key=lambda x: -x[1])), "vacant": seats - filled,
            "majority": top if n > seats / 2 else None,  # a plurality isn't a majority
            "overrideSeats": need, "override": facts["override"], "canOverride": bool(top) and n >= need,
        }
    majorities = {c["majority"] for c in out["chambers"].values()}
    out["unified"] = out["governor"][1] if majorities == {out["governor"][1]} else None
    return out


PARTY_NAME = {"D": "Democrats", "R": "Republicans", "I": "independents", "O": "others"}


def badge(party):
    """A party's letter in a small colored badge (the letter carries the meaning; the color helps)."""
    name = {"D": "Democratic", "R": "Republican", "I": "Independent"}.get(party, "Other")
    return f'<abbr class="bp-pty bp-{party}" title="{name}">{party}</abbr>'


def chamber_html(name, ch):
    """"Senate R 29–2 veto-proof": the majority's badge, its seats and the next party's."""
    parties = list(ch["parties"].items())
    if not parties:
        return ""
    lead, n = parties[0]
    rest = parties[1][1] if len(parties) > 1 else 0
    tip = ", ".join(f"{v} {PARTY_NAME.get(k, k)}" for k, v in parties) + (f", {ch['vacant']} vacant" if ch["vacant"] else "")
    # Where a majority overrides (Indiana), every majority is "veto-proof": the sentence below says so instead.
    tag = (' <span class="bp-vp" title="Enough seats to override a veto (' + ch["override"].replace("2/3", "two-thirds").replace("3/5", "three-fifths")
           + ')">veto-proof</span>') if ch["canOverride"] and ch["override"] != "majority" else ""
    return f'<span class="bp-ch" title="{name}: {tip}">{name} {badge(lead)} {n}–{rest}{tag}</span>'


def summary_html(state, lower_name="House", sep=" · "):
    """A state's party control: "Senate R 29–2 · House R 56–6 · Gov. R" (the front page puts each part on its own line)."""
    b = current(state)
    if not b:
        return ""
    names = {"S": "Senate"}
    parts = [chamber_html(names.get(c, re.sub(r" of Delegates$", "", lower_name)), ch) for c, ch in
             sorted(b["chambers"].items(), key=lambda x: x[0] != "S")]
    gov = b["governor"]
    parts.append(f'<span class="bp-ch" title="Governor {gov[0]}">Governor {badge(gov[1])}</span>')
    return sep.join(p for p in parts if p)


ADJ = {"D": "Democratic", "R": "Republican"}
NOUN = {"D": "Democrats", "R": "Republicans"}


def meaning(state, lower_name="House"):
    """One plain sentence on what the balance of power means for passing bills."""
    b = current(state)
    if not b:
        return ""
    if b.get("note"):
        return b["note"]
    names = {c: ("Senate" if c == "S" else re.sub(r" of Delegates$", "", lower_name)) for c in b["chambers"]}
    chambers = b["chambers"]
    majorities = {c: ch["majority"] for c, ch in chambers.items()}
    gov = b["governor"][1]
    if None in majorities.values() or len(set(majorities.values())) > 1:
        held = ", ".join(f"{NOUN.get(m, 'no party')} hold{'s' if not m else ''} the {names[c]}" for c, m in majorities.items())
        return f"Split legislature: {held}, so a bill needs support from both parties to pass."
    party = next(iter(majorities.values()))
    noun = NOUN.get(party, party)
    over = {c: ch["canOverride"] for c, ch in chambers.items()}
    simple = all(ch["override"] == "majority" for ch in chambers.values())
    if gov == party:
        return f"{noun} hold both houses and the governor's office" + (
            ". A majority of each house can override a veto." if simple else
            ", with enough seats to override a veto." if all(over.values()) else ".")
    if simple:
        return f"Divided government: a {ADJ.get(gov, gov)} governor, but a majority of each house can override a veto, and {noun} hold both."
    if all(over.values()):
        return f"Divided government: a {ADJ.get(gov, gov)} governor, but {noun} hold enough seats in both houses to override a veto."
    short = []
    for c, ch in chambers.items():
        if not ch["canOverride"]:
            gap = ch["overrideSeats"] - ch["parties"].get(party, 0)
            short.append(f"{gap} vote{'s' if gap != 1 else ''} short in the {names[c]}")
    return (f"Divided government: a {ADJ.get(gov, gov)} governor; overriding a veto takes {noun} plus help from other members "
            f"({' and '.join(short)}).")


if __name__ == "__main__":
    print(json.dumps(current(sys.argv[1]), indent=1))
