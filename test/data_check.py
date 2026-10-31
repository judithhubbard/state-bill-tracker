#!/usr/bin/env python3
"""Runs the "Data traps found so far" list in CLAUDE.md against every state's data, so each check is made every time,
not only the newest ones. Each trap that can be checked by a program is a check here; the rest print what a person
should look at. Add a check here whenever a new trap goes on the list.

FAIL: a trap is present (exit status 1). LOOK: numbers or examples to read over (official totals, odd wording).
Usage: python3 test/data_check.py [state ...]   (default: every state with data; New York's own data isn't checked)
"""
import collections, glob, importlib, json, os, re, sys

HERE = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, HERE)
STATES = [s for s in ("ca", "ct", "il", "nj", "oh", "or", "tx", "va", "wa") if os.path.isdir(os.path.join(HERE, "data", s))
          and not os.path.exists(os.path.join(HERE, "data", s, "incomplete"))] + \
    (["ny"] if glob.glob(os.path.join(HERE, "data", "bills_*.json*")) else [])  # New York's data is in data/ itself
fails = []


def say(state, kind, msg):
    print(f"  {kind:4} {msg}")
    if kind == "FAIL":
        fails.append(f"{state}: {msg}")


def check(state):
    P = importlib.import_module(f"states.{state}.profile")
    C = importlib.import_module(f"states.{state}.convert")
    print(f"== {P.STATE_NAME}")
    loaded = {s: C.load_session(s)[0] for s in C.sessions()}

    for s, recs in loaded.items():
        stages = collections.Counter(r["stage"] for r in recs)
        # Count bills by stage against the Legislature's own totals (signed, vetoed).
        say(state, "LOOK", f"{s}: {len(recs)} bills; signed {stages[5]}, vetoed {stages[6]}, passed both houses but not "
                           f"sent {stages[3]}, on the governor's desk {stages[4]} (compare with the official totals)")
        # A bill that passed both houses passed each one (missing votes, one-house conference reports).
        missing = [r["nums"][0] for r in recs if r["stage"] >= 3 and not (r["passedS"] and r["passedA"])]
        if missing:
            say(state, "FAIL", f"{s}: {len(missing)} bills past both houses without both houses' passage, e.g. {missing[:4]}")
        # The 4th key date is New York's alone (return to committee in a new year).
        if state != "ny" and any(r["keyDates"][3] for r in recs):
            say(state, "FAIL", f"{s}: the 4th key date (New York's return to committee) is filled in")
        # Committee pass rates that look wrong (sponsors' amendments read as committee votes).
        fate = collections.Counter(r["commFate"] for r in recs)
        say(state, "LOOK", f"{s}: first committee: {fate['passed']} approved, {fate['held']} held, {fate['defeated']} voted down, "
                           f"{fate['none']} no action ({100 * fate['passed'] // max(1, len(recs))}% approved)")
        # Floor-vote wording not read as a passage.
        odd = collections.Counter()
        for r in recs:
            for _, t in r["vers"][0]["actions"]:
                if re.search(r"\bpassed\b|rescind|reconsider", t, re.I) and not t.startswith("PASSED") and \
                        not re.search(r"passed (to (engrossment|third|3rd|second|2nd)|by indefinitely|over)|Passed by|"
                                      r"to engrossment|Bill text as passed|Reported|Committee|Passed Both Houses|Motion (Filed )?to Reconsider", t, re.I):
                    odd[re.sub(r"\(.*", "", re.sub(r"\d+", "#", t))[:70]] += 1
        if odd:
            say(state, "LOOK", f"{s}: history lines mentioning passage not read as one: " +
                "; ".join(f"{n}× {k}" for k, n in odd.most_common(4)))
        # Vote lists that don't match their tallies.
        bad = sum(1 for r in recs for v in r["votes"] if sum(1 for _, c in v[6] if c == "N") > v[5])
        if bad:
            say(state, "FAIL", f"{s}: {bad} votes list more noes than their tally")

    # The current session's votes should name seats, not leftover names.
    cur = max(loaded)
    who = [m for r in loaded[cur] for v in r["votes"] for m, _ in v[6]]
    loose = [m for m in who if "?" in m]
    if who:
        share = 100 * len(loose) / len(who)
        say(state, "FAIL" if share > 10 else "LOOK", f"{cur}: {share:.1f}% of named votes aren't tied to a seat "
            f"(former members are expected), e.g. {collections.Counter(loose).most_common(3)}")

    # Summary text: encoding, characters lost in the export, paragraphs cut mid-sentence, title-only summaries.
    for path in sorted(glob.glob(os.path.join(P.DATA, "texts_*.json"))):
        texts = [t for v in json.load(open(path)).values() for t in (v.get("statement"), v.get("fiscal")) if t]
        name = os.path.basename(path)
        enc = sum(1 for t in texts if re.search("ï¿½|�|â€|Ã©", t))
        lost = sum(1 for t in texts if re.search(r"(?<=[a-z])\?(?=[a-z]+[\s.,;])|(^|\s)\?\s+\d", re.sub(r"\S*[/=]\S*", "", t)))
        cut = sum(1 for t in texts if any(len(p) > 20 and not re.search(r"[.:;?!)\"”\]]$", p.strip()) for p in t.split("\n")[:-1]))
        title = sum(1 for t in texts if re.fullmatch(r"(?:As proposed, )?(?:C\.S\.)?\S+ amends current law relating to [^.]*\.?", t.strip()))
        if enc:
            say(state, "FAIL", f"{name}: {enc} texts with wrongly decoded characters")
        if lost:
            say(state, "FAIL", f"{name}: {lost} texts with characters lost as \"?\"")
        if title:
            say(state, "FAIL", f"{name}: {title} texts that only repeat the title")
        if texts and cut / len(texts) > 0.05:
            say(state, "LOOK", f"{name}: {100 * cut // len(texts)}% of texts have a paragraph without end punctuation "
                               f"(cut mid-sentence, or real headings and lists)")

    # Laws whose "What it does" describes a placeholder: the summary of the bill as filed, when an amendment rewrote it
    # (Illinois's shell bills: "Makes a technical change"; California's spot bills).
    for s, recs in loaded.items():
        path = os.path.join(P.DATA, f"texts_{s}.json")
        if not os.path.exists(path):
            continue
        T = json.load(open(path))
        laws = [r["nums"][0] for r in recs if r["stage"] == 5]
        found = [n for n in laws if n in T]
        # Short ones only: real summaries often also mention "technical changes".
        shell = [n for n in found if len(T[n].get("statement") or "") < 300 and re.search(
            r"technical change in a section|nonsubstantive change|intent of the Legislature to enact legislation", T[n].get("statement") or "", re.I)]
        # (Not "technical changes" alone: Connecticut's technical-revisions acts are real laws, and say so.)
        if found and len(shell) > 0.01 * len(found):
            say(state, "FAIL", f"{s}: {len(shell)} of {len(found)} laws are summarized as placeholders, e.g. {shell[:3]}")
        elif laws and len(found) < 0.5 * len(laws):
            say(state, "LOOK", f"{s}: only {len(found)} of {len(laws)} laws have a summary in {os.path.basename(path)}")

    # Legislators: degrees in names, odd spacing, duplicate phones, missing parties or phones.
    for path in sorted(glob.glob(os.path.join(P.DATA, "contacts_*.json")))[-1:]:
        people = json.load(open(path))["people"]
        deg = [p["name"] for p in people.values() if re.search(r"^(Dr|Rev|Hon)\.\s|\b(M\.D\.|Ph\.D\.|Ed\.D\.|Esq\.?)$", p["name"])]
        spaces = [p["name"] for p in people.values() if re.search(r"\s{2,}|\blll\b", p["name"])]
        dup = [p["name"] for p in people.values() if len(p.get("phones") or []) != len({tuple(x) for x in p.get("phones") or []})]
        noparty = [p["name"] for p in people.values() if not p.get("party")]
        nophone = [p["name"] for p in people.values() if not p.get("phone")]
        for label, xs in (("names with a degree or title", deg), ("names with odd spacing or \"lll\"", spaces),
                          ("legislators with a phone number twice", dup)):
            if xs:
                say(state, "FAIL", f"{os.path.basename(path)}: {label}: {xs[:4]}")
        if noparty or nophone:
            say(state, "LOOK", f"{os.path.basename(path)}: no party {noparty[:3]}, no phone {nophone[:3]}")

    # A label that means a different procedure in different states. "Constitutional amendments" in New York are
    # resolutions that never go to the governor (STATE.amendments in profile.js); in Virginia they're bills that set up
    # the ballot question, which the governor signs. Where the profile says amendments skip the governor, none may reach
    # the governor's desk; elsewhere the tag is only a topic.
    skips = re.search(r"^\s*amendments:\s*true", open(os.path.join(HERE, "states", state, "profile.js")).read(), re.M)
    for s, recs in loaded.items():
        tagged = [r for r in recs if "const" in r["topics"]]
        sent = [r["nums"][0] for r in tagged if r["stage"] >= 4]
        if skips and sent:
            say(state, "FAIL", f"{s}: {len(sent)} constitutional amendments went to the governor, though they skip the governor: {sent[:4]}")
        elif sent:
            say(state, "LOOK", f"{s}: {len(sent)} bills tagged constitutional amendments went to the governor (bills, not the amendments; "
                               f"the page mustn't say they skip the governor): {sent[:3]}")

    # Other states' names and rules on this state's pages (settings that fell back to New York's).
    words = r"Albany|Hochul|Heastie|Stewart-Cousins|Kelles|Tompkins|New York State|nysenate|nyassembly"
    pages = [] if state == "ny" else sorted(glob.glob(os.path.join(HERE, "site", P.SITE_DIR, "*.html")))[-1:] + \
        glob.glob(os.path.join(HERE, "_site", P.SITE_DIR, "index.html"))  # the Claude copy, or the public build
    for page in pages:
        html = open(page).read()
        html = re.sub(r"(?s)<script[^>]*>.*?</script>", "", html)  # the code (comments mention other states)
        hits = sorted(set(re.findall(words, html)))
        if hits:
            say(state, "FAIL", f"{os.path.basename(page)}: New York's names on the page: {hits}")


def main():
    for state in (sys.argv[1:] or STATES):
        check(state)
    print(f"\n{len(fails)} problem(s)" + ("".join(f"\n- {f}" for f in fails) if fails else ""))
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
