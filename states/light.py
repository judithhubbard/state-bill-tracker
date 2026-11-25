#!/usr/bin/env python3
"""Light history: older sessions kept as each bill's outcome, for Statistics, Trends and the state comparison (states/
LIGHT.md). For each old session a state's hook (states/<st>/light.py) downloads only what the state's own converter needs,
into a scratch folder; the converter's load_session() decides stages exactly as it does for the current sessions; and
the records, without their actions, votes and texts, go into data/<st>/light_<session>.json.gz. A session already written
is skipped (finished sessions don't change); the scratch folder is deleted.

Usage:
  python3 states/light.py ST [SESSION ...]     download and write the state's light sessions (default: the hook's SESSIONS)
  python3 states/light.py --counts [ST ...]    each light file's counts, to compare with the official totals
"""
import re, gzip, importlib, json, os, shutil, sys, tempfile
from datetime import datetime, timezone

HERE = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, HERE)
FORMAT = 1
# The converter record's fields a light record keeps (actions, votes, texts, similar-bill text and page-only fields left
# out). Each version keeps its number, sponsor, district and counts, not its history.
KEEP = ("nums", "title", "summary", "stage", "passedS", "passedA", "passedIn", "first", "last", "keyDates", "firstComms",
        "commFate", "comms", "topics", "mainTopic", "narrow", "shell", "budget", "ballot", "chapter", "local", "places", "cosp")
VERS_KEEP = ("p", "sponsor", "district", "primes", "cosp", "statusDesc")
SUMMARY_MAX = 600


def path_of(data, session):
    return os.path.join(data, f"light_{session}.json.gz")


def fix_day(d, session):
    """A date the source mistyped by a thousand years (Open States' HI HB 186 of 2017: signed "3017-06-30") back in its
    session's years; one still outside them (or in the future) dropped."""
    d = str(d or "")
    m = re.match(r"(\d{4})(-\d\d-\d\d.*)$", d)
    if not m:
        return d
    y = int(m.group(1))
    if session - 1 <= y <= session + 3:
        return d
    if session - 1 <= y - 1000 <= session + 3:
        return f"{y - 1000}{m.group(2)}"
    return "" if y > session + 3 else d


def light_record(r, session=None):
    out = {k: r[k] for k in KEEP if k in r}
    if session:
        for k in ("first", "last"):
            if out.get(k):
                out[k] = fix_day(out[k], session) or out[k][:0]
        if out.get("keyDates"):
            out["keyDates"] = [";".join(x for x in (fix_day(p, session) for p in str(kd or "").split(";")) if x)
                               for kd in out["keyDates"]]
    if out.get("summary"):
        out["summary"] = out["summary"][:SUMMARY_MAX]
    out["firstComms"] = [list(x) for x in (out.get("firstComms") or [])]
    out["vers"] = [{k: v.get(k) for k in VERS_KEEP if k in v} for v in r.get("vers") or []]
    return out


def coverage(recs):
    """Which fields the source filled in for some bill (the header's "has"), so a reader knows what's missing."""
    has = {
        "summary": any(r.get("summary") for r in recs),
        "keyDates": any(any(r.get("keyDates") or []) for r in recs),
        "firstComms": any(r.get("firstComms") for r in recs),
        "sponsor": any(v.get("sponsor") for r in recs for v in r.get("vers") or []),
        "topics": any(r.get("topics") for r in recs),
        "chapter": any(r.get("chapter") for r in recs),
    }
    return sorted(k for k, v in has.items() if v), sorted(k for k, v in has.items() if not v)


def counts(recs):
    st = [r.get("stage") for r in recs]
    return {"bills": len(recs), "passedOne": sum(1 for r in recs if bool(r.get("passedS")) != bool(r.get("passedA"))),
            "passedBoth": sum(1 for r in recs if r.get("passedS") and r.get("passedA")),
            "laws": st.count(5), "vetoed": st.count(6), "withChapter": sum(1 for r in recs if r.get("chapter"))}


def unmapped(recs, P):
    """First committees a state maps to topics by name (P.COMMITTEE_TOPICS) that its table doesn't name: committees
    renamed since, whose bills then lose that topic (topics from title words still apply)."""
    table = getattr(P, "COMMITTEE_TOPICS", None)
    if not table:
        return []
    return sorted({c for r in recs for _, c, *_ in (r.get("firstComms") or []) if c and c not in table})


def write(state, session, recs, parties, source, data, P=None):
    has, lacks = coverage(recs)
    names = {v.get("sponsor") for r in recs for v in r.get("vers") or [] if v.get("sponsor")}
    body = {"format": FORMAT, "state": state, "session": session, "source": source,
            "fetched": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "has": has, "lacks": lacks,
            # The converter's parties ({(house, name): "D"/"R"}) as [house, name, party] rows, for the sponsors named here.
            "counts": counts(recs), "parties": sorted(([k[0], k[1], p] for k, p in (parties or {}).items()
                                                       if isinstance(k, tuple) and len(k) == 2 and k[1] in names),
                                                      key=lambda x: [str(y or "") for y in x]),  # (a house or name may be None)
            "noTopic": sum(1 for r in recs if not r.get("topics")), "unmappedCommittees": unmapped(recs, P) if P else [],
            "bills": [light_record(r, session) for r in recs]}
    tmp = path_of(data, session) + ".tmp"
    with gzip.open(tmp, "wt", encoding="utf-8") as f:
        json.dump(body, f, ensure_ascii=False, separators=(",", ":"), default=list)
    os.replace(tmp, path_of(data, session))
    return body


def read(data, session):
    """A light file's contents, or None."""
    try:
        with gzip.open(path_of(data, session), "rt", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def sessions_on_disk(data):
    import glob, re
    return sorted(int(m.group(1)) for p in glob.glob(os.path.join(data, "light_*.json.gz"))
                  if (m := re.search(r"light_(\d{4})\.json\.gz$", p)))


def run(state, wanted=None):
    H = importlib.import_module(f"states.{state}.light")
    P = importlib.import_module(f"states.{state}.profile")
    real = P.DATA
    os.makedirs(real, exist_ok=True)
    wrote = []
    for session in wanted or H.SESSIONS:
        if os.path.exists(path_of(real, session)):
            print(f"{state} {session}: already written", flush=True)
            continue
        # LIGHT_KEEP (the workflow's cached folder): a session too slow for one run (Wisconsin's 2015-16 from GitHub's
        # machines, about 16 seconds a bill) keeps what it downloaded, and the next run's fetch reads only what's missing.
        keep = os.environ.get("LIGHT_KEEP")
        scratch = os.path.join(keep, f"{state}-{session}") if keep else tempfile.mkdtemp(prefix=f"light-{state}-{session}-")
        os.makedirs(scratch, exist_ok=True)
        written = False
        try:
            if not H.fetch(session, scratch):
                print(f"{state} {session}: not downloaded; nothing written"
                      + (" (what was downloaded is kept for the next run)" if keep else ""), flush=True)
                continue
            P.DATA = scratch
            if hasattr(H, "records"):
                # (A hook whose source isn't the converter's: Open States' bulk files, states/openstates_records.py.)
                recs, parties = H.records(session, scratch, P)
            else:
                C = importlib.import_module(f"states.{state}.convert")
                recs = C.load_session(session)[0]
                parties = C.parties(session, recs) if hasattr(C, "parties") else {}
            body = write(state, session, recs, parties, H.SOURCE, real, P)
            print(f"{state} {session}: {body['counts']}; lacks {body['lacks'] or 'nothing'}; no topic {body['noTopic']}"
                  + (f"; committees with no topic mapping: {body['unmappedCommittees']}" if body["unmappedCommittees"] else ""), flush=True)
            wrote.append(session)
            written = True
        finally:
            P.DATA = real
            if written or not keep:
                shutil.rmtree(scratch, ignore_errors=True)
    return wrote


def show_counts(states):
    for state in states:
        P = importlib.import_module(f"states.{state}.profile")
        for s in sessions_on_disk(P.DATA):
            b = read(P.DATA, s)
            if b:
                print(f"{state} {s}: {b['counts']}; lacks {b['lacks'] or 'nothing'}; source {b['source']}; fetched {b['fetched']}")


if __name__ == "__main__":
    args = sys.argv[1:]
    if args and args[0] == "--counts":
        show_counts(args[1:] or ["mt", "wy", "nd", "or"])
    elif args:
        run(args[0], [int(a) for a in args[1:]] or None)
    else:
        sys.exit(__doc__)
