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
