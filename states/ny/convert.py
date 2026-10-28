"""New York: reads the Senate API's bill data (data/bills_<session>.json, from fetch_bills.py) and the
Assembly's floor votes, and turns them into the bill records build_data.py works with.

Every state's convert.py has the same two functions: sessions() and load_session(session).
"""
import gzip, glob, json, os, re
from collections import defaultdict

from stages import rank
from . import profile as P


def sessions():
    """The sessions downloaded. Session data may be plain JSON (fresh downloads) or gzipped (past
    sessions kept in git)."""
    return sorted({int(re.search(r"bills_(\d{4})", f).group(1)) for f in glob.glob(os.path.join(P.DATA, "bills_*.json*"))})


def read_session(session):
    path = os.path.join(P.DATA, f"bills_{session}.json")
    if os.path.exists(path):
        return json.load(open(path))
    with gzip.open(path + ".gz", "rt") as f:
        return json.load(f)

# Scheduled last day of each year's session (calendar year -> date), entered each January.


def committee_fate(live):
    """For a bill still in committee: "passed" (a committee approved it; it died in the next one), "defeated"
    (a committee voted it down), "held" (put on an agenda and held for consideration or tabled, no vote),
    "amended" (the sponsor revised it, no vote), or "none"."""
    acts = [a["text"] for b in live for a in b["actions"]]
    votes = [v for b in live for v in b.get("votes") or [] if v.get("type") == "COMMITTEE"]
    aye = lambda v: sum(n for k, n in v["counts"].items() if k.startswith("AYE"))
    if any(t.startswith(("REPORTED", "COMMITTEE DISCHARGED")) for t in acts) or any(aye(v) > v["counts"].get("NAY", 0) for v in votes):
        return "passed"
    if votes or any(t.startswith("DEFEATED") for t in acts):
        return "defeated"
    if any(t.startswith(("HELD FOR CONSIDERATION", "TABLED")) for t in acts):
        return "held"
    if any(t.startswith("AMEND") for t in acts):
        return "amended"
    return "none"


def main_topic(live, topics):
    """The topic of the committee a bill was first sent to: how the Legislature itself files it. Its other
    topics come from the laws it amends and can be incidental. Falls back to its first topic."""
    for _h, name, _left in first_committees(live):
        for t in topics:
            if name in P.TOPICS[t][1]:
                return t
    return topics[0] if topics else ""


def counties_of_name(name):
    """Counties for a place name, trying shorter versions ("Johnson City Central" -> "Johnson City")."""
    name = re.sub(r"'s$", "", name.replace("’", "'").rstrip(".,")).replace("Mt. ", "Mount ")
    if name in ("New York", "NY", "N.Y."):
        return P.NYC
    words = name.split()
    # Longest leading run first ("Johnson City Central" -> "Johnson City"), then without a leading
    # direction ("East Ramapo" -> "Ramapo").
    for cand in [words[:k] for k in range(len(words), 0, -1)] + [words[1:]] * (len(words) > 1):
        if " ".join(cand) in P.COUNTIES and " ".join(cand) != "New York":
            return [" ".join(cand)]
        hit = P.PLACE_COUNTIES.get(" ".join(cand).lower())
        if hit:
            return hit
    return []


def place_counties(title, summary, law_code):
    """The counties a bill is only about, or [] if it isn't about specific places. "?" marks a named place
    whose county isn't known."""
    if P.REACHES_BEYOND.search(title):
        return []
    t = title[:1].lower() + title[1:]  # the opening verb isn't a place name
    found, unknown = set(), False
    for m in P._MUNI.finditer(t):
        hit = counties_of_name(m.group(1))
        found.update(hit); unknown |= not hit
    for m in P._ENTITY.finditer(t):
        hit = counties_of_name(m.group(1))
        found.update(hit); unknown |= not hit
    for m in P._COUNTY.finditer(t):
        found.add(m.group(1) or m.group(2))
    if re.search(r"\bcounties\b", t):  # "the counties of Dutchess, Orange and Putnam"
        found.update(c for c in P.COUNTIES if c != "New York" and re.search(r"\b" + re.escape(c) + r"\b", t))
    for m in P._NAMED.finditer(t):
        found.update(P.REGIONS.get(m.group(1)) or P.PLACE_COUNTIES.get(m.group(1).lower(), []))
    if found:
        # The summary often names the county ("town of Brookhaven, county of Suffolk").
        for m in P._COUNTY.finditer(summary):
            found.add(m.group(1) or m.group(2))
    elif unknown:
        # A place the list doesn't have; the summary may say where it is.
        for m in P._MUNI.finditer(summary):
            found.update(counties_of_name(m.group(1)))
        for m in P._COUNTY.finditer(summary):
            found.add(m.group(1) or m.group(2))
    else:
        # Summaries mention New York City in passing, so only named towns and counties count there.
        for m in P._MUNI.finditer(summary):
            if not m.group(1).rstrip(".").endswith(("New York", "NY")):
                hit = counties_of_name(m.group(1))
                found.update(hit); unknown |= not hit
        for m in P._COUNTY.finditer(summary):
            found.add(m.group(1) or m.group(2))
        if not (found or unknown) and law_code and all("NYC" in p for p in law_code.split(";") if p.strip()):
            found.update(P.NYC)
    out = sorted(c for c in found if c in P.COUNTIES)
    return out or (["?"] if unknown else [])


def memo_text(raw):
    """The governor's signing memo, as plain paragraphs: no heading, signature or line-end hyphens."""
    if not raw:
        return ""
    body = re.split(r"\n\s*APPROVED\s*\n", raw, maxsplit=1)[-1]
    body = re.sub(r"(^|\n)\s*This bill is approved\.\s*$", "", body.split("(signed)")[0].rstrip())
    paras = []
    for para in re.split(r"\n\s*\n", body):
        para = re.sub(r"(\w)-\n\s*(?=[a-z])", r"\1", para.strip())
        para = re.sub(r"\s+", " ", para).strip()
        if para:
            paras.append(para)
    return "\n".join(paras)


def veto_text(raw):
    """The governor's reasons from a veto message: the part after "NOT APPROVED", up to the signature."""
    if not raw or "NOT APPROVED" not in raw:
        return ""
    body = raw.split("NOT APPROVED", 1)[1].split("(signed)")[0]
    body = re.sub(r"\s*(These bills are|The bills are|This bill is|The bill is) disapproved\.\s*$", "", body.rstrip())
    paras = []
    for para in re.split(r"\n\s*\n", body):
        para = re.sub(r"(\w)-\n\s*(?=[a-z])", r"\1", para.strip())
        para = re.sub(r"\s+", " ", para).strip()
        if para:
            paras.append(para)
    return "\n".join(paras)


def norm_comm(name):
    return "Rules" if name.startswith("Rules") else name


def bill_stage(b):
    """How far this one version got, 0-6 (6 = vetoed)."""
    ms = {m["type"] for m in b["milestones"]}
    if b["signed"] or "SIGNED_BY_GOV" in ms:
        return 5
    if b["vetoed"] or "VETOED" in ms:
        return 6
    if "DELIVERED_TO_GOV" in ms:
        return 4
    if {"PASSED_SENATE", "PASSED_ASSEMBLY"} <= ms:
        return 3
    if ms & {"PASSED_SENATE", "PASSED_ASSEMBLY"}:
        return 2
    if ms & {"SENATE_FLOOR", "ASSEMBLY_FLOOR"}:
        return 1
    return 0


SENATE_CODES = {"NAY": "N", "EXC": "E", "ABS": "A", "ABD": "B"}
ASSEMBLY_CODES = {"No": "N", "ER": "E", "Abs": "A", "Abstain": "B", "NV": "A"}


def collect_votes(live, avotes):
    """Senate votes (API) and Assembly floor votes (nyassembly.gov) for a bill's versions.
    Each: [house, "F"/"C", committee, date, yes, no, [[member, code], ...]] listing only
    members who didn't vote yes; members are ("S", district) or ("A", short name)."""
    out, seen = [], set()
    for b in live:
        for v in b.get("votes", []):
            key = ("S", v["type"], v["date"], v.get("committee"))
            if key in seen:
                continue
            seen.add(key)
            c = v["counts"]
            out.append(["S", "F" if v["type"] == "FLOOR" else "C", v.get("committee"), v["date"],
                        c.get("AYE", 0) + c.get("AYEWR", 0), c.get("NAY", 0),
                        [[("S", d), SENATE_CODES.get(code, code)] for _, d, code in v["notYes"]]])
        for v in (avotes.get(b["printNo"]) or {}).get("votes", []):
            key = ("A", "F", v["date"], v["yea"], v["nay"])
            if key in seen:
                continue
            seen.add(key)
            out.append(["A", "F", None, v["date"], v["yea"], v["nay"],
                        [[("A", n), ASSEMBLY_CODES.get(code, code)] for n, code in v["notYes"]]])
    return sorted(out, key=lambda v: v[3])


LEFT_COMMITTEE = ("ADVANCED TO THIRD READING", "ORDERED TO THIRD READING", "REPORTED", "COMMITTEE DISCHARGED",
                  "PASSED SENATE", "PASSED ASSEMBLY")


# Committees renamed between sessions, mapped to their current names.
COMMITTEE_RENAMES = {
    "Alcoholism And Substance Abuse": "Alcoholism And Substance Use Disorders",
    "Mental Health And Developmental Disabilities": "Mental Health",
}


def first_committees(live):
    """For each version: the first committee in its own house, and whether the bill got out of it."""
    out = []
    for b in live:
        # The API lists committees by name, not date; the first referral is the earliest.
        own = sorted((c for c in b["pastCommittees"] if c["chamber"] == b["chamber"]), key=lambda c: c.get("date") or "")
        if not own:
            continue
        name = COMMITTEE_RENAMES.get(norm_comm(own[0]["name"]), norm_comm(own[0]["name"]))
        if name in ("Rules", "Calendar"):
            continue
        left = any(a["chamber"] == b["chamber"] and a["text"].startswith(LEFT_COMMITTEE) for a in b["actions"])
        out.append((b["chamber"][0], name, left))
    return out


TITLE_STOP = set("the a an of to and or for in on by with relates relating certain provides requires establishes authorizes".split())


def title_overlap(a, b):
    """Share of the shorter title's words that the other title also uses."""
    wa, wb = ({w for w in re.findall(r"[a-z]+", (x or "").lower()) if w not in TITLE_STOP and len(w) > 2} for x in (a, b))
    return len(wa & wb) / max(1, min(len(wa), len(wb)))


def load_session(session):
    """Read one session's bills and return (records, printNo -> record index, fetched time)."""
    raw = read_session(session)
    bills = {b["printNo"]: b for b in raw["bills"] if not b["resolution"]}
    deleg = P.delegation(session)

    # The API names some laws two ways ("Cannabis" and "Cannabis Law"); use the full name.
    law_names = {b["lawSection"] for b in bills.values() if b["lawSection"]}
    for b in bills.values():
        if b["lawSection"] and b["lawSection"] + " Law" in law_names:
            b["lawSection"] = b["lawSection"] + " Law"

    # Union-find over "same as" and substitution links.
    parent = {p: p for p in bills}

    def find(p):
        while parent[p] != p:
            parent[p] = parent[parent[p]]
            p = parent[p]
        return p

    def union(a, b):
        if a in parent and b in parent:
            parent[find(a)] = find(b)

    # The API occasionally points a bill at an unrelated "same as" (S10006 -> A11368, a
    # physical therapy bill). Skip a link when it only goes one way and the titles share
    # almost no words; one-way links between matching titles are ordinary reintroductions.
    for b in bills.values():
        for s in b["sameAs"]:
            back = bills[s]["sameAs"] if s in bills else []
            if back and b["printNo"] not in back and title_overlap(b["title"], bills[s]["title"]) < 0.25:
                continue
            union(b["printNo"], s)
        if b["substitutedBy"]:
            union(b["printNo"], b["substitutedBy"])

    groups = {}
    for p in bills:
        groups.setdefault(find(p), []).append(bills[p])

    avotes_path = os.path.join(P.DATA, f"assembly_votes_{session}.json")
    avotes = json.load(open(avotes_path)) if os.path.exists(avotes_path) else {}
    recs, index = [], {}
    for members in groups.values():
        live = [b for b in members if b["status"]["statusType"] != "STRICKEN"]
        if not live:
            continue
        for b in live:
            b["_stage"] = bill_stage(b)
        live.sort(key=lambda b: (-rank(b["_stage"]), b["chamber"] != "SENATE", b["printNo"]))
        lead = live[0]

        ms = {m["type"] for b in live for m in b["milestones"]}
        stage = max((b["_stage"] for b in live), key=rank)
        if stage < 3 and {"PASSED_SENATE", "PASSED_ASSEMBLY"} <= ms:
            stage = 3
        passed_in = None
        if stage == 2:
            passed_in = "Senate" if "PASSED_SENATE" in ms else "Assembly"

        chapter = veto = None
        for b in live:
            for a in b["actions"]:
                m = re.match(r"SIGNED CHAP\.(\d+)", a["text"])
                if m:
                    chapter = int(m.group(1))
                m = re.match(r"(?:VETOED MEMO\.|POCKET VETO - VETO\.)(\d+)", a["text"])
                if m:
                    veto = int(m.group(1))

        laws = sorted({b["lawSection"] for b in live if b["lawSection"]})
        # Each committee under its own house (a Senate bill sent to the Assembly meets Assembly committees).
        comms = sorted({f"{(c.get('chamber') or b2['chamber'])[0]} · {norm_comm(c['name'])}" for b2 in live for c in b2["pastCommittees"]})
        comm_names = {norm_comm(c["name"]) for b in live for c in b["pastCommittees"]}
        text = " ".join(filter(None, [lead["title"], lead["summary"]]))

        topics = []
        for k, (label, cset, lset, _) in P.TOPICS.items():
            if comm_names & cset or set(laws) & lset or (k in P.TOPIC_WORDS and P.TOPIC_WORDS[k].search(lead["title"] or "")):
                topics.append(k)
        if any((b["programInfo"] or {}).get("name") in ("Department of Environmental Conservation",
                                                       "Environmental Facilities Corporation") for b in live):
            if "env" not in topics:
                topics.insert(0, "env")

        dates = [a["date"] for b in live for a in b["actions"]]

        def when(pred, mode="last"):
            ds = sorted({a["date"] for b in live for a in b["actions"] if pred(a["text"])})
            if not ds:
                return ""
            return {"first": ds[0], "last": ds[-1], "all": ";".join(ds)}[mode]

        # Key dates in the bill's path, across both houses' versions ("" if it never happened).
        key_dates = [
            when(lambda t: t.startswith(("ADVANCED TO THIRD READING", "ORDERED TO THIRD READING")), "first"),
            when(lambda t: t in ("PASSED SENATE", "REPASSED SENATE"), "all"),
            when(lambda t: t in ("PASSED ASSEMBLY", "REPASSED ASSEMBLY"), "all"),
            when(lambda t: t.startswith("DIED IN")),
            when(lambda t: t == "DELIVERED TO GOVERNOR"),
            when(lambda t: t.startswith("SIGNED CHAP")),
            when(lambda t: t.startswith(("VETOED MEMO", "POCKET VETO"))),
        ]
        first = min(dates + [b["publishDate"] for b in live if b["publishDate"]], default=None)
        last = max(dates, default=lead["status"]["actionDate"])
        prog = next(((b["programInfo"] or {}).get("name") for b in live if b["programInfo"]), None)

        rec = {
            "nums": [b["printNo"] + (b["activeVersion"] or "") for b in live],
            "base": [b["printNo"] for b in members],
            "prev": {(p["session"], p["printNo"]) for b in members for p in b.get("previousVersions", [])
                     if p["session"] < session},
            "title": lead["title"],
            "summary": lead["summary"] or "",
            "act": re.sub(r"\s+", " ", lead["actClause"] or ""),
            "lawCode": lead["lawCode"] or "",
            "law": lead["lawSection"],
            "laws": laws,
            "comms": comms,
            "topics": topics,
            "places": place_counties(lead["title"] or "", lead["summary"] or "", lead["lawCode"] or ""),
            "narrow": P.narrow_kind(lead["title"] or ""),
            "commFate": committee_fate(live),
            "mainTopic": main_topic(live, topics),
            "local": "local" in topics or bool(set(laws) & P.LOCAL_LAWS) or bool(P.LOCAL_WORDS.search(text)),
            "senDeleg": any(b["chamber"] == "SENATE" and b["district"] in deleg.get("SENATE", ()) for b in live),
            "asmDeleg": any(b["chamber"] == "ASSEMBLY" and b["district"] in deleg.get("ASSEMBLY", ()) for b in live),
            "budget": any(b["budget"] for b in live),
            # Passed each house at any point in the session, even if later sent back to committee.
            "passedS": any(a["text"] in ("PASSED SENATE", "REPASSED SENATE") for b in live for a in b["actions"]),
            "passedA": any(a["text"] in ("PASSED ASSEMBLY", "REPASSED ASSEMBLY") for b in live for a in b["actions"]),
            "program": f"Program bill: {prog}" if prog else None,
            "stage": stage,
            "passedIn": passed_in,
            "chapter": chapter,
            "veto": veto,
            "memo": next((memo_text(b.get("approvalMemo")) for b in members if b.get("approvalMemo")), ""),
            # The governor's veto message: {year, signer, text} with the reasons.
            "vetoMemo": next(({"year": m["year"], "signer": (m.get("signer") or "").title(), "text": veto_text(m["text"])}
                              for b in members for m in [b.get("vetoMemo")] if m and veto_text(m.get("text"))), None),
            "comm": lead["status"]["committeeName"] if stage == 0 else None,
            "first": first,
            "last": last,
            "cosp": max(b["cosponsorCount"] for b in live),
            "keyDates": key_dates,
            "votes": collect_votes(live, avotes),
            "firstComms": first_committees(live),
            "vers": [{
                "p": b["printNo"] + (b["activeVersion"] or ""),
                "sponsor": b["sponsor"],
                "district": b["district"],
                "cosponsors": (b.get("coSponsors") or []) + (b.get("multiSponsors") or []),
                "cosp": b["cosponsorCount"],
                "statusDesc": b["status"]["statusDesc"],
                "committee": b["status"]["committeeName"],
                "actions": [[a["date"], a["text"]] for a in b["actions"]],
            } for b in live],
        }
        for p in rec["base"]:
            index[p] = len(recs)
        recs.append(rec)

    # Sponsor names for the delegation checkboxes.
    names = {"SENATE": set(), "ASSEMBLY": set()}
    for b in bills.values():
        if b["district"] in deleg.get(b["chamber"], ()) and b["sponsorShort"]:
            names[b["chamber"]].add(b["sponsor"].split()[-1] if not b["sponsor"].split()[-1].rstrip(".").isupper()
                                    else b["sponsor"].split()[-2])
    names = {k: sorted(v & P.DELEGATION_NAMES) for k, v in names.items()}
    # If someone else holds the seat, drop that checkbox's matches as well.
    for r in recs:
        if not names["SENATE"]:
            r["senDeleg"] = False
        if not names["ASSEMBLY"]:
            r["asmDeleg"] = False
    return recs, index, raw["fetched"], names
