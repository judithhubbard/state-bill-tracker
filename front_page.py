"""The front page map's party-control dots (build_site.sh). Kept apart from balance.py, which every state's pages use (and
whose changes rebuild them all), so a change to the front page rebuilds no state."""
import re

from balance import ADJ, current


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
        dots.append([ch["majority"] or "S", ch["canOverride"]])
        counts = "–".join(str(v) for _, v in list(ch["parties"].items())[:2])
        words.append(f"{name}: {ADJ.get(ch['majority'], 'split') if ch['majority'] else 'split'} {counts}"
                     + (" (supermajority)" if ch["canOverride"] else ""))
    gov = b["governor"][1]
    dots.append([gov, False])
    words.append(f"Governor: {ADJ.get(gov, gov)}")
    return {"dots": dots, "title": "; ".join(words)}
