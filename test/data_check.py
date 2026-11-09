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
STATES = [s for s in ("ak", "al", "ar", "az", "ca", "co", "ct", "ga", "id", "il", "in", "ky", "ma", "md", "me", "mi", "nc", "nd", "nh", "nj", "oh", "ok", "or", "pa", "ri", "sd", "tn", "tx", "ut", "va", "vt", "wa", "wi", "wy") if os.path.isdir(os.path.join(HERE, "data", s))
          and not os.path.exists(os.path.join(HERE, "data", s, "incomplete"))] + \
    (["ny"] if glob.glob(os.path.join(HERE, "data", "bills_*.json*")) else [])  # New York's data is in data/ itself
fails = []
# Each legislature's seats (states/legislatures.json), to check votes against the size of their house.
LEGISLATURES = json.load(open(os.path.join(HERE, "states", "legislatures.json")))["states"]
# The topics every state uses, with the same names, so states can be compared ("Shared conventions" in CLAUDE.md).
TOPICS = {"ag": "Agriculture & natural resources", "biz": "Business & consumers", "const": "Constitutional amendments",
          "edu": "Education", "env": "Environment & energy", "gov": "Elections & state government",
          "health": "Health & mental health", "housing": "Housing", "human": "Human services",
          "labor": "Labor & public employees", "local": "Local government", "safety": "Public safety & courts",
          "tax": "Taxes", "transp": "Transportation"}


def say(state, kind, msg):
    print(f"  {kind:4} {msg}")
    if kind == "FAIL":
        fails.append(f"{state}: {msg}")


def check(state):
    P = importlib.import_module(f"states.{state}.profile")
    C = importlib.import_module(f"states.{state}.convert")
    print(f"== {P.STATE_NAME}")
    loaded = {s: C.load_session(s)[0] for s in C.sessions()}

    # The shared topics, with the shared names.
    mine = {k: v[0] for k, v in P.TOPICS.items()}
    off = {k: mine.get(k) for k in TOPICS if mine.get(k) != TOPICS[k]} | {k: v for k, v in mine.items() if k not in TOPICS}
    if off:
        say(state, "FAIL", f"topics differ from the shared list: {off}")

    for s, recs in loaded.items():
        # (Constitutional amendments stop at "passed both houses": they go to the voters, not the governor.)
        stages = collections.Counter(r["stage"] for r in recs if not (r["stage"] == 3 and "const" in r["topics"]))
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
        # Committee names carrying a motion's tail: a failed motion to refer read as a referral (IN's "Referred to
        # Committee on Ways and Means pursuant to House Rule 84; Failed, Roll Call 185: yeas 28, nays 59").
        tails = sorted({c for r in recs for c in r["comms"] if re.search(r"\b(?:failed|roll call|yeas|nays|pursuant to)\b|;", c, re.I)})
        if tails:
            say(state, "FAIL", f"{s}: {len(tails)} committee names carry a motion's wording, e.g. {tails[:3]}")
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
        # Histories out of order: some lines with a time and some with only a date (MA's S2913: sorting by the full
        # time put "Read second" after "Laid before the Governor"). Sort by day and keep the file's order within a day.
        unsorted = [r["nums"][0] for r in recs for v in r["vers"] if any(a[0] > b[0] for a, b in zip(v["actions"], v["actions"][1:]) if a[0] and b[0])]
        # (A few are the source's own order: New York's Senate lines after a substitution.)
        if unsorted:
            say(state, "FAIL" if len(unsorted) > 0.01 * len(recs) else "LOOK",
                f"{s}: {len(unsorted)} bills with history lines out of date order, e.g. {unsorted[:4]}")
        # Law numbers on bills that aren't laws: ND's Session Laws give vetoed measures chapter numbers too (HB 1273 of 2023,
        # "Measure Vetoed", chapter 586); a chapter number alone doesn't make a law.
        numbered = [r["nums"][0] for r in recs if r.get("chapter") and r["stage"] != 5]
        if numbered:
            say(state, "FAIL", f"{s}: {len(numbered)} bills that aren't laws carry a law number, e.g. {numbered[:4]}")
        # Law numbers given twice (NH's history lines: SB 62 and HB 511 of 2025 both "Chapter 39"; the LSRs file's column is
        # right). In one-year sessions a chapter, act or public law number belongs to one bill.
        if getattr(P, "YEARS", 2) == 1:
            twice = [k for k, n in collections.Counter(r["chapter"] for r in recs if r.get("chapter")).items() if n > 1]
            if twice:
                say(state, "LOOK", f"{s}: {len(twice)} law numbers given to two bills, e.g. {twice[:4]}")
        # Dates with a typo in the year (NH's HB 425 of 2025: "03/06/2035"; HB 49 of 2023: "04/13/2022"): far outside the
        # session. (Carried-over bills reach back a year or two; laws are signed and vetoes taken up a year after.)
        years = getattr(P, "YEARS", 2)
        stray = [r["nums"][0] for r in recs for v in r["vers"] for d, _ in v["actions"]
                 if d and re.match(r"\d{4}", str(d)) and not s - 3 <= int(str(d)[:4]) <= s + years + 1]
        if stray:
            say(state, "FAIL" if len(set(stray)) > 0.005 * len(recs) else "LOOK",
                f"{s}: {len(stray)} history lines dated years from the session, e.g. {sorted(set(stray))[:4]}")
        after = [r["nums"][0] for r in recs for v in r["vers"] for i, (d, t) in enumerate(v["actions"])
                 if t == "DELIVERED TO GOVERNOR" and any(d2 == d and re.match(r"PASSED|PLACED ON FLOOR|REFERRED", t2) for d2, t2 in v["actions"][i + 1:])]
        if after:
            say(state, "LOOK", f"{s}: {len(after)} bills with a passage or referral after going to the governor the same day, e.g. {after[:4]}")
        # A list carried onto the next history line (AK's "CROSS SPONSOR(S): TOBIN, ..., GRAY-JACKSON," then "KIEHL, ...";
        # its committee reports' "DP: ..." lists too): a line ending in a comma is half of one.
        cont = [r["nums"][0] for r in recs for v in r["vers"] for _, t in v["actions"] if re.search(r",\s*$", t)]
        if cont:
            say(state, "LOOK", f"{s}: {len(cont)} history lines end in a comma (a list carried onto the next line?), e.g. {sorted(set(cont))[:4]}")
        # Vote lists that don't match their tallies.
        bad = sum(1 for r in recs for v in r["votes"] if sum(1 for _, c in v[6] if c == "N") > v[5])
        if bad:
            say(state, "FAIL", f"{s}: {bad} votes list more noes than their tally")
        # Fewer: a name list split wrongly (WY's "Brown, G, Larson, JT" read as four names, then joined too eagerly).
        few = [r["nums"][0] for r in recs for v in r["votes"] if 0 < sum(1 for _, c in v[6] if c == "N") < v[5]]
        if few:
            say(state, "FAIL" if len(few) > 0.01 * sum(len(r["votes"]) for r in recs) else "LOOK",
                f"{s}: {len(few)} votes list fewer noes than their tally, e.g. {few[:4]}")
        # Votes put in the wrong house: more ayes and noes than the house has seats (ID's history lines don't name the
        # house, so the converter follows the bill from house to house; WY's roll calls sometimes name the wrong one).
        seats = LEGISLATURES.get(state, {}).get("seats", {})
        big = [r["nums"][0] for r in recs for v in r["votes"] if v[1] == "F" and seats.get(v[0]) and v[4] + v[5] > seats[v[0]]]
        if big:
            say(state, "FAIL", f"{s}: {len(big)} floor votes have more ayes and noes than their house has seats, e.g. {big[:4]}")
        # A veto read as overridden: KY's SB 70 of 2026 was vetoed after the session and "delivered to Secretary of State"
        # with no chapter, a line laws over a veto also carry. A law with a veto date should show the override.
        ovr = re.compile(r"overrid|over (?:the )?(?:governor'?s? )?veto|notwithstanding|not sustained", re.I)
        unover = [r["nums"][0] for r in recs if r["stage"] == 5 and r["keyDates"][6] and not any(ovr.search(t) for v in r["vers"] for _, t in v["actions"])]
        if unover:
            say(state, "LOOK", f"{s}: {len(unover)} laws vetoed with no override in their history (a veto read as overridden?), e.g. {unover[:4]}")
        # Procedural votes read as the bill's own: AL's "Third Reading in House of Origin" line carries the roll call on the
        # bill's Budget Isolation Resolution, taken just before the passage. Bills with two floor votes in one house on one
        # day: up to about a third in CO and VA (passage and a re-passage, a concurrence or an emergency clause the same
        # day); a BIR read as a passage would put nearly every AL bill there.
        twice = [r["nums"][0] for r in recs if r["votes"] and max(collections.Counter((v[0], v[3]) for v in r["votes"] if v[1] == "F").values() or [0]) > 1]
        voted = sum(1 for r in recs if r["votes"])
        if voted and len(twice) > 0.5 * voted:
            say(state, "LOOK", f"{s}: {len(twice)} of {voted} bills with floor votes have two in one house on one day (a procedural vote read as the bill's?), e.g. {twice[:4]}")
        # A substitute's vote written with both names ("Hill(Brown)" in ID's House: Brown sits for Hill; "Coho(Lenney)" in
        # its Senate: Coho sits for Lenney) left as a name: the vote belongs to the member's seat. (TX's "Speaker(C)", the
        # chair's mark, isn't a name.)
        subs = collections.Counter(m for r in recs for v in r["votes"] for m, _ in v[6] if isinstance(m, str) and "?" in m and re.search(r"\([A-Za-z][A-Za-z'’ -]+\)", m))
        if subs:
            say(state, "FAIL", f"{s}: {sum(subs.values())} votes by names with parentheses not tied to a seat, e.g. {subs.most_common(3)}")

    # Sponsors tied to a party, session by session: a session far below the others has a member list that failed to
    # match (AR's 2023-24 members file has one column fewer than 2025-26's, and every member was dropped at first).
    if hasattr(C, "parties"):
        share = {}
        for s, recs in loaded.items():
            named = [r for r in recs if r["vers"][0]["sponsor"] not in ("", "—") and  # members, not committees
                     not re.search(r"Committee|Management|Council|Commission|Caucus|Efficiency|Rules", r["vers"][0]["sponsor"])]
            party = C.parties(s, recs)
            if len(named) >= 20:
                share[s] = sum(1 for r in named if (r["vers"][0]["p"][0], r["vers"][0]["sponsor"]) in party) / len(named)
        low = {s: f"{100 * v:.0f}%" for s, v in share.items() if share and v < 0.5 * max(share.values())}
        if low:
            say(state, "LOOK", f"sessions whose sponsors mostly have no party (a member list that didn't match?): {low}, "
                               f"best {100 * max(share.values()):.0f}%")

    # The current session's votes should name seats, not leftover names.
    cur = max(loaded)
    who = [m for r in loaded[cur] for v in r["votes"] for m, _ in v[6]]
    loose = [m for m in who if "?" in m]
    if who:
        share = 100 * len(loose) / len(who)
        say(state, "FAIL" if share > 10 else "LOOK", f"{cur}: {share:.1f}% of named votes aren't tied to a seat "
            f"(former members are expected), e.g. {collections.Counter(loose).most_common(3)}")

    # "What it does" says where it's from, as a sentence: "From the Legislative Reference Bureau's synopsis."
    for path in sorted(glob.glob(os.path.join(P.DATA, "texts_*.json")))[-1:]:
        labels = {v.get("label") for v in json.load(open(path)).values() if v.get("label")}
        odd = sorted(l for l in labels if not re.match(r"From the .*\.$", l))
        if odd:
            say(state, "FAIL", f"{os.path.basename(path)}: source notes not written as 'From the ....': {odd[:3]}")

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
        # A district map that doesn't match the member list (New Hampshire's HouseDistricts.txt still has the 2012 map):
        # every legislator's district is one some place in "Where you live" gives.
        towns = json.load(open(P.TOWNS_PATH)) if os.path.exists(getattr(P, "TOWNS_PATH", "")) else []
        if towns and isinstance(towns[0], list) and len(towns[0]) >= 3:
            have = {"S": set(), "L": set()}
            for t in towns:
                for key, i in (("S", 2), ("L", 3 if len(t) > 3 else 2)):
                    have[key] |= {int(d[0]) for d in t[i] if isinstance(d, list) and str(d[0]).isdigit()}
            off = [sid for sid in people if re.match(r"\d+", sid[2:]) and
                   int(re.match(r"\d+", sid[2:]).group()) not in have["S" if sid[0] == "S" else "L"]]
            if off:
                say(state, "FAIL", f"{os.path.basename(P.TOWNS_PATH)}: {len(off)} legislators' districts aren't in any place's list, e.g. {off[:4]}")

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


def check_balance(state):
    """The balance of power (balance.py): every built state has its legislature in states/legislatures.json and a member
    list, and each chamber's party counts and vacancies add up to its seats."""
    sys.path.insert(0, HERE)
    import balance
    if state not in balance.table():
        say(state, "FAIL", "not in states/legislatures.json (seats, veto override, governor)")
        return
    b = balance.current(state)
    if not b:
        say(state, "FAIL", "no member list for the balance of power")
        return
    for c, ch in b["chambers"].items():
        if ch["vacant"] < 0:
            say(state, "FAIL", f"{c}: {sum(ch['parties'].values())} members for {ch['seats']} seats")
        elif ch["vacant"] > 0.05 * ch["seats"]:
            say(state, "LOOK", f"{c}: {ch['vacant']} of {ch['seats']} seats vacant (a stale member list?)")
        if "?" in ch["parties"]:
            say(state, "FAIL", f"{c}: {ch['parties']['?']} members with no party")
    say(state, "LOOK", "balance: " + " | ".join(f"{c} " + "-".join(f"{k}{v}" for k, v in ch["parties"].items())
                                               + (f" +{ch['vacant']} vacant" if ch["vacant"] else "")
                                               + (" (can override)" if ch["canOverride"] else "")
                                               for c, ch in b["chambers"].items()) + f" | governor {b['governor'][1]}")


def main():
    for state in (sys.argv[1:] or STATES):
        check(state)
        check_balance(state)
    print(f"\n{len(fails)} problem(s)" + ("".join(f"\n- {f}" for f in fails) if fails else ""))
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
