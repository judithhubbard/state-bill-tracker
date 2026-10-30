#!/usr/bin/env python3
"""Download Texas bill histories from the Legislature's FTP site (ftp.legis.state.tx.us), the source the Texas
Legislative Council asks data users to use instead of its website. Each bill has its own XML file
(/bills/<session>/billhistory/house_bills/HB00001_HB00099/HB 12.xml); there's no bulk file, so the folder listings'
dates decide which files changed since the last run, and only those are downloaded (one connection per folder, six at a time).

Sessions are the Legislature's codes: 89R is the regular session of 2025 (the 89th Legislature); special sessions
(891, 892 ...) aren't downloaded. Files go to data/tx/<code>/billhistory/<file>.xml, with listing dates in dates.json.

Usage: python3 states/tx/fetch.py [first_year]   (default 2021)
"""
import json, os, re, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
from states.tx import profile as P

FTP = "ftp://ftp.legis.state.tx.us/bills"
FIRST = int(sys.argv[1]) if len(sys.argv) > 1 else 2021
CURRENT = P.session_of(datetime.now(ZoneInfo(P.TIMEZONE)).year)
KINDS = ["house_bills", "senate_bills"]


def curl(args, check=True):
    for attempt in range(4):
        r = subprocess.run(["curl", "-sS", "--max-time", "600", *args], capture_output=True)
        if r.returncode == 0:
            return r.stdout.decode("utf-8", "replace")
        if not check and r.returncode in (9, 19, 78):  # no such folder or file
            return None
        time.sleep(5 * (attempt + 1))
    if check:
        raise SystemExit(f"failed: curl {' '.join(args[-1:])}: {r.stderr.decode(errors='replace').strip()}")
    return None


def listing(url):
    """Name -> 'MM-DD-YY HH:MMxM size' for each file, and the subfolders."""
    text = curl([url + "/"], check=False)
    files, dirs = {}, []
    for line in (text or "").splitlines():
        m = re.match(r"(\d\d-\d\d-\d\d\s+\d\d:\d\d[AP]M)\s+(<DIR>|\d+)\s+(.+)$", line.strip())
        if m:
            if m.group(2) == "<DIR>":
                dirs.append(m.group(3))
            else:
                files[m.group(3)] = f"{m.group(1)} {m.group(2)}"
    return files, dirs


def complete(path):
    """A downloaded file that's all there (a dropped connection can leave half a file)."""
    try:
        with open(path, "rb") as f:
            f.seek(max(0, os.path.getsize(path) - 64))
            return b"</billhistory>" in f.read()
    except OSError:
        return False


def session(code):
    folder = os.path.join(P.DATA, code, "billhistory")
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(P.DATA, code, "dates.json")
    try:
        seen = json.load(open(path))
    except (OSError, ValueError):
        seen = {}
    # Every folder's listing first, then the changed files, six folders at a time (about a second a file).
    jobs = []
    for kind in KINDS:
        _, groups = listing(f"{FTP}/{code}/billhistory/{kind}")
        for g in groups:
            files, _ = listing(f"{FTP}/{code}/billhistory/{kind}/{g}")
            todo = [f for f, stamp in files.items() if f.endswith(".xml") and (seen.get(f) != stamp or not complete(os.path.join(folder, f)))]
            if todo:
                jobs.append((f"{FTP}/{code}/billhistory/{kind}/{g}", todo, files))

    def run(job):
        url, todo, files = job
        args = []
        for f in todo:
            args += ["-o", os.path.join(folder, f), f"{url}/{f.replace(' ', '%20')}"]
        curl(args)
        return todo, files

    got = 0
    with ThreadPoolExecutor(6) as pool:
        for todo, files in pool.map(run, jobs):
            for f in todo:
                seen[f] = files[f]
            got += len(todo)
            json.dump(seen, open(path, "w"))
    print(f"{code}: {got} bill histories downloaded, {len(seen)} in all")
    # A full pass with nothing left cut off: a finished session needn't be listed again.
    if all(complete(os.path.join(folder, f)) for f in seen):
        open(os.path.join(P.DATA, code, "complete"), "w").write(datetime.now().isoformat())


def main():
    for year in sorted(range(FIRST, CURRENT + 3, 2), reverse=True):  # newest first
        code = P.code_of(year)
        done = os.path.join(P.DATA, code, "complete")
        if year < CURRENT and os.path.exists(done) and os.path.getmtime(done) > datetime(year + 2, 1, 1).timestamp():
            continue  # a finished session, downloaded in full after it ended
        if listing(f"{FTP}/{code}/billhistory")[1]:
            session(code)


def legislators():
    """The current legislators and committees, once a day (about 250 pages)."""
    from states.tx import contacts
    path = os.path.join(P.DATA, f"contacts_{CURRENT}.json")
    today = datetime.now(ZoneInfo(P.TIMEZONE)).strftime("%Y-%m-%d")
    try:
        fresh = json.load(open(path)).get("fetched", "").startswith(today)
    except (OSError, ValueError):
        fresh = False
    if fresh:
        print(f"contacts_{CURRENT}.json: already refreshed today")
        return
    try:
        contacts.main(CURRENT)
    except Exception as e:  # a site down for the day: keep yesterday's file
        print(f"contacts not refreshed: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()
    legislators()
    from states.tx import journals  # floor votes, from the House and Senate journals
    for year in range(FIRST, CURRENT + 1, 2):
        if os.path.isdir(os.path.join(P.DATA, P.code_of(year), "billhistory")):
            journals.main(year)
            journals.senate(year, journals.senate_dates(year))
    from states.tx import texts  # "What it does", from the current session's bill analyses
    if os.path.isdir(os.path.join(P.DATA, P.code_of(CURRENT), "billhistory")):
        texts.main(CURRENT)
