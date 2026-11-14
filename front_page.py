"""The front page map's party-control dots (build_site.sh). Kept apart from balance.py, which every state's pages use (and
whose changes rebuild them all), so a change to the front page rebuilds no state."""
import re

from balance import ADJ, current
WORD = {**ADJ, "C": "bipartisan coalition"}  # a chamber run by a coalition (Alaska)


def map_data(state, lower_name="House"):
    """The front page map's dots for a state: [[party, supermajority], ...] for the Senate, the lower house and the
    governor, and the words for the square's tooltip."""
    b = current(state)
    if not b:
        return None
    lower = re.sub(r" of Delegates$", "", lower_name)
    order = sorted(b["chambers"].items(), key=lambda x: x[0] != "S")
    dots, words = [], []
    for c, ch in order:
        name = "Senate" if c == "S" else lower
        if ch.get("nonpartisan"):
            # Elected without party labels (Nebraska's one house): a neutral ring, "N" (home.html's legend).
            dots.append(["N", False])
            words.append(f"{name}: nonpartisan, one house")
            continue
        # No ring where a simple majority overrides a veto (Indiana): it would mark every majority.
        sm = ch["canOverride"] and ch["override"] != "majority"
        dots.append([ch["majority"] or "S", sm])
        counts = "–".join(str(v) for _, v in list(ch["parties"].items())[:2]) if ch["majority"] != "C" else ""
        words.append(f"{name}: {WORD.get(ch['majority'], 'split') if ch['majority'] else 'split'}{' ' + counts if counts else ''}"
                     + (" (supermajority)" if sm else ""))
    gov = b["governor"][1]
    dots.append([gov, False])
    words.append(f"Governor: {ADJ.get(gov, gov)}")
    return {"dots": dots, "title": "; ".join(words)}


def next_data(state, lower_name="House"):
    """The map's dots for after the 2026 election (states/elected_2026.json: seats won, from reported results), for the
    "From January" view the front page shows between the election and the new sessions; None when the file has nothing
    for the state. Same rules as map_data: a majority is more than half the seats, a ring a supermajority that can
    override a veto on its own (not where a simple majority overrides, as in Indiana)."""
    import json, math, os
    from fractions import Fraction
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "states", "elected_2026.json")
    if not os.path.exists(path):
        return None
    e = json.load(open(path)).get("states", {}).get(state)
    facts = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "states", "legislatures.json")))["states"].get(state)
    if not e or not facts:
        return None
    lower = re.sub(r" of Delegates$", "", lower_name)
    dots, words = [], []
    for c, seats in sorted(facts["seats"].items(), key=lambda x: x[0] != "S"):
        name = "Senate" if c == "S" else lower
        ch = (e.get("chambers") or {}).get(c) or {}
        if facts.get("nonpartisan") or ch.get("nonpartisan"):
            dots.append(["N", False])
            words.append(f"{name}: nonpartisan, one house")
            continue
        counts = {k: v for k, v in ch.items() if k in ("D", "R", "I", "O") and isinstance(v, int)}
        if not counts:
            return None
        top, n = max(counts.items(), key=lambda x: x[1])
        coalition = c in (e.get("coalition") or [])
        majority = "C" if coalition else (top if n > seats / 2 else None)
        need = seats // 2 + 1 if facts["override"] == "majority" else math.ceil(Fraction(facts["override"]) * seats)
        sm = not coalition and majority == top and n >= need and facts["override"] != "majority"
        dots.append([majority or "S", sm])
        parts = sorted(counts.values(), reverse=True)[:2]
        unc = ch.get("uncalled") or 0
        words.append(f"{name}: {WORD.get(majority, 'split') if majority else 'split'} {'–'.join(map(str, parts))}"
                     + (" (supermajority)" if sm else "") + (f", {unc} uncalled" if unc else ""))
    gov = (e.get("governor") or [None, None])[1]
    if gov:
        dots.append([gov, False])
        words.append(f"Governor: {ADJ.get(gov, gov)}")
    return {"dots": dots, "title": "; ".join(words), "close": e.get("confidence") != "called"}
