#!/usr/bin/env python3
"""House committee votes by member, from the House Research Organization's Daily Floor Report (2026-11-22).

The bill histories (the FTP site) give each committee vote only as totals. The House Research Organization (HRO, the
House's nonpartisan research office) analyses every bill on the House's second-reading calendars in its Daily Floor
Report, one PDF per part of each floor day: https://hro.house.texas.gov/pdf/fr<yyyy>/<yymmdd><A|B|C...>.PDF (250422B
is the second part of April 22, 2025's report). Each analysis names the bill and its House committee, and its VOTE
line names every committee member who voted:

    COMMITTEE:  Intergovernmental Affairs — favorable, without amendment
    VOTE:       11 ayes — C. Bell, Zwiener, Cole, Cortez, Garcia Hernandez, Leo
                Wilson, Lowe, Luther, Rosenthal, Spiller, Tepper
                0 nays
                2 absent — Anchía, Smithee

(also "N present not voting — ..."). hro.house.texas.gov has no robots.txt (404, checked 2026-11-22). house.texas.gov
and capitol.texas.gov are never read: house.texas.gov's robots.txt bars ClaudeBot by name, and the Texas Legislative
Council asks data users not to mine capitol.texas.gov. Nothing on hro.house.texas.gov is read but these PDFs.

There's no listing: the days come from the histories already downloaded, every day the House placed a bill on a
second-reading calendar or read one a second time (action codes 420-435, 465, 515, 522: about 41 days a session), and
each day's parts are asked in order, A, B, C ..., until one answers 404. Each part is read once (pdftotext -layout)
into data/tx/<code>/hro/<yymmdd><L>.txt; hro/state.json records the parts that answered 404, asked again only while
the day is under three days old (a report can be posted late in the morning). About 120 requests a session, two
seconds apart, 2021 on; the first copy of three sessions takes about 15 minutes, a run after that seconds.

convert.py reads `analyses(session)`: bill -> [{"day", "committee", "ayes", "nays", "absent", "pnv", "names"}] and
puts the names on the committee vote the history already has (house, committee and tally), never as a second vote.
Usage: python3 states/tx/hro.py [year]   (default: every session from 2021)
"""
import json, os, re, shutil, subprocess, sys, tempfile, time, urllib.error, urllib.request
from datetime import date, datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
from states.tx import profile as P

SITE = "https://hro.house.texas.gov/pdf"
AGENT = "statebilltracker.org (a nonprofit bill tracker; contact via github.com/judithhubbard)"
FLOOR_CODES = (420, 425, 430, 435, 465, 515, 522)  # placed on a second-reading calendar; read 2nd time; postponed business
LETTERS = "ABCDEFGH"


def folder(session):
    return os.path.join(P.DATA, P.code_of(session), "hro")


# ---- Reading ---------------------------------------------------------------------------------------------------------

BILL = re.compile(r"\b(?:CS)?([HS])(B|JR)\s+(\d+)\b")
SECTION = re.compile(r"^([A-Z][A-Z ]{2,30}):", re.M)  # "VOTE:", "SENATE VOTE:", "WITNESSES:" at the line's start
COUNT = re.compile(r"(\d+)\s+(ayes?|nays?|absent|present,?\s+not\s+voting)\b(?:\s*[—–-]+\s*(.*))?$", re.I | re.S)


def split_names(s):
    """"C. Bell, Zwiener, Garcia Hernandez, Leo\n Wilson, Gervin-\nHawkins" -> names. A line's end is a space, except
    after a hyphen ("Gervin-Hawkins")."""
    s = re.sub(r"-\s*\n\s*", "-", s)
    s = re.sub(r"\s+", " ", s).strip().rstrip(".")
    return [x.strip() for x in s.split(",") if x.strip()]


_KNOWN = []


def known_names():
    """Members' names with a comma in them, as the House writes them ("Garcia, Linda"): the analyses sometimes do too
    (CSHB 149 of 2025: "Curry, Garcia, Linda, Olcott"), which a split on commas reads as two members."""
    if not _KNOWN:
        import glob
        names = {"\x00"}
        for path in glob.glob(os.path.join(P.DATA, "contacts_*.json")):
            try:
                names |= {p.get("dataName") or "" for p in json.load(open(path))["people"].values()}
            except (OSError, ValueError, KeyError):
                pass
        _KNOWN.append({n for n in names if "," in n})
    return _KNOWN[0]


def join_known(names, n):
    """Names split one too many times ("Garcia", "Linda") put back together when the pair is a member's name."""
    out, i = [], 0
    while i < len(names):
        if i + 1 < len(names) and len(out) + (len(names) - i) > n and f"{names[i]}, {names[i + 1]}" in known_names():
            out.append(f"{names[i]}, {names[i + 1]}")
            i += 2
        else:
            out.append(names[i])
            i += 1
    return out


def vote_line(text):
    """A VOTE section's text -> {"ayes": n, "nays": n, "absent": n, "pnv": n, "names": {"ayes": [...], ...}}, or None
    when a group's names don't add up to its count."""
    out = {"ayes": 0, "nays": 0, "absent": 0, "pnv": 0, "names": {"ayes": [], "nays": [], "absent": [], "pnv": []}}
    # Groups are separated by a blank line; a group's names may run onto several lines.
    for part in re.split(r"\n\s*\n", text.strip()):
        m = COUNT.match(part.strip())
        if not m:
            continue
        kind = m.group(2).lower()
        key = "ayes" if kind.startswith("aye") else "nays" if kind.startswith("nay") else "absent" if kind == "absent" else "pnv"
        n = int(m.group(1))
        names = split_names(m.group(3) or "")
        if len(names) > n:
            names = join_known(names, n)
        if len(names) != n:
            return None
        out[key], out["names"][key] = n, names
    return out if out["ayes"] or out["nays"] else None


def parse(text, day):
    """A floor report's text -> [{"bill": "HB467", "day": "2025-04-22", "committee": "Intergovernmental Affairs",
    "ayes": 11, ..., "names": {...}}], one per bill analysis with a readable House committee vote."""
    out = []
    lines = text.splitlines()
    starts = [i for i, l in enumerate(lines) if re.match(r"\s*ORGANIZATION\s+bill analysis\b", l)]
    for k, i in enumerate(starts):
        head = " ".join(lines[max(0, i - 2):i + 1])
        m = BILL.search(head)
        if not m:
            continue
        bill = f"{m.group(1)}{m.group(2)}{int(m.group(3))}"
        body = "\n".join(lines[i + 1:starts[k + 1] - 2 if k + 1 < len(starts) else len(lines)])
        secs = {}
        found = list(SECTION.finditer(body))
        for j, s in enumerate(found):
            name = s.group(1).strip()
            if name not in secs:
                secs[name] = body[s.end():found[j + 1].start() if j + 1 < len(found) else len(body)]
        comm = re.sub(r"\s+", " ", secs.get("COMMITTEE", "")).strip()
        comm = re.split(r"\s+[—–]\s+", comm)[0].strip()
        v = vote_line(secs.get("VOTE", ""))
        if not comm or not v:
            continue
        out.append({"bill": bill, "day": day, "committee": comm, **v})
    return out


def day_of(name):
    """"250422B.txt" -> "2025-04-22"."""
    m = re.match(r"(\d\d)(\d\d)(\d\d)[A-Z]", name)
    return f"20{m.group(1)}-{m.group(2)}-{m.group(3)}" if m else ""


def analyses(session):
    """Bill -> its analyses with a House committee vote, from every saved part, oldest first, one per distinct vote."""
    out = {}
    d = folder(session)
    if not os.path.isdir(d):
        return out
    for f in sorted(os.listdir(d)):
        if not f.endswith(".txt"):
            continue
        for a in parse(open(os.path.join(d, f), encoding="utf-8", errors="replace").read(), day_of(f)):
            seen = out.setdefault(a.pop("bill"), [])
            if not any(x["committee"] == a["committee"] and x["names"] == a["names"] for x in seen):
                seen.append(a)
    return out


# ---- Downloading -----------------------------------------------------------------------------------------------------

def floor_days(session):
    """Days the House had bills on a second-reading calendar, from the saved histories."""
    from states.tx import convert as C
    return sorted({d for b in C.bills(session).values() for d, h, n, _, _ in b["actions"] if h == "H" and n in FLOOR_CODES and d})


def get(url):
    """(status, body): 200 with the PDF, 404, or None after three tries."""
    for attempt in range(3):
        time.sleep(2)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": AGENT})
            with urllib.request.urlopen(req, timeout=120) as r:
                return 200, r.read()
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return 404, None
            if e.code in (401, 403, 429):
                return e.code, None
        except Exception:
            pass
        time.sleep(10 * (attempt + 1))
    return None, None


def main(year, minutes=10):
    """Read each floor day's report parts not yet saved, at most `minutes`."""
    if not shutil.which("pdftotext"):
        print("floor reports: pdftotext isn't installed; skipped")
        return
    start = time.time()
    d = folder(year)
    os.makedirs(d, exist_ok=True)
    spath = os.path.join(d, "state.json")
    try:
        state = json.load(open(spath))
    except (OSError, ValueError):
        state = {"missing": {}}
    today = date.today()
    got = asked = 0
    for day in floor_days(year):
        if date.fromisoformat(day) > today:
            continue
        stem = day[2:4] + day[5:7] + day[8:10]
        for L in LETTERS:
            name = f"{stem}{L}"
            if os.path.exists(os.path.join(d, name + ".txt")):
                continue
            tried = state["missing"].get(name)
            # This day has no more parts: asked again (once a day) only while the day was under three days old.
            if tried and ((date.fromisoformat(tried) - date.fromisoformat(day)).days >= 3 or tried == today.isoformat()):
                break
            if time.time() - start > minutes * 60:
                print(f"floor reports {year}: {got} parts read of {asked} asked; stopped at the time limit")
                json.dump(state, open(spath, "w"))
                return
            asked += 1
            status, body = get(f"{SITE}/fr20{stem[:2]}/{name}.PDF")
            if status == 404:
                state["missing"][name] = today.isoformat()
                break
            if status != 200 or not body or not body.startswith(b"%PDF"):
                print(f"floor reports: {name} failed ({status}); stopping")
                json.dump(state, open(spath, "w"))
                return
            with tempfile.TemporaryDirectory() as tmp:
                pdf = os.path.join(tmp, "r.pdf")
                open(pdf, "wb").write(body)
                r = subprocess.run(["pdftotext", "-layout", "-enc", "UTF-8", pdf, os.path.join(d, name + ".tmp")])
            if r.returncode:
                print(f"floor reports: pdftotext failed on {name}")
                continue
            os.replace(os.path.join(d, name + ".tmp"), os.path.join(d, name + ".txt"))
            state["missing"].pop(name, None)
            got += 1
    json.dump(state, open(spath, "w"))
    print(f"floor reports {year}: {got} parts read of {asked} asked; "
          f"{len([f for f in os.listdir(d) if f.endswith('.txt')])} saved")


if __name__ == "__main__":
    years = [int(sys.argv[1])] if len(sys.argv) > 1 else range(2021, P.session_of(datetime.now().year) + 1, 2)
    for y in years:
        main(y, minutes=30)
