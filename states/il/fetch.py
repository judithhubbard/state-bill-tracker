#!/usr/bin/env python3
"""Download Illinois bill status files, members and committees from the General Assembly's public file repository
(https://ftp.ilga.gov/), the place it asks automated programs to use (www.ilga.gov turns them away).

- /Legislation/<GA>/BillStatus/XML/: one XML per bill (HB, SB) and per joint resolution proposing a constitutional
  amendment (HC = HJRCA, SC = SJRCA); other resolutions are left out. The folder listing's dates decide which changed since the last
  run, and only those are downloaded, one request every 10 seconds (robots.txt's Crawl-delay, obeyed since 2026-11-24;
  before that six at a time), the most recently changed first, until the run's time is used (12 minutes before FETCH_MINUTES):
  the rest come next run. Into data/il/<GA>/billstatus/, with listing dates in dates.json.
- /Legislation/<GA>/HB|SB/<GA>00HB2682gms.htm: the governor's message on each vetoed bill (`veto_messages()`).
- /Members/<GA>HouseMembers.xml, <GA>SenateMembers.xml and /Committees/<GA>...CommitteeMembers.xml, every run.

The servers don't send the intermediate certificate their own certificate needs (Sectigo Public Server Authentication
CA OV R40), so it's fetched from Sectigo and added to a copy of the system's certificates (data/il/ca.pem); the
connection is still fully checked.
Usage: python3 states/il/fetch.py [first_year]   (default 2021)
"""
import glob, json, os, re, subprocess, sys, time, urllib.request
from datetime import datetime
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
from listing_dates import same
from states.il import profile as P

REPO = "https://ftp.ilga.gov"
# Members' emails and the addresses of their ilga.gov pages (states/il/contacts.py), from Open States.
PEOPLE = "https://data.openstates.org/people/current/il.csv"
AGENT = "statebilltracker.org (a nonprofit bill tracker; contact via github.com/judithhubbard)"
INTERMEDIATE = "http://crt.sectigo.com/SectigoPublicServerAuthenticationCAOVR40.crt"
SYSTEM_CAS = ["/etc/ssl/certs/ca-certificates.crt", "/etc/ssl/cert.pem", "/etc/pki/tls/certs/ca-bundle.crt"]
FIRST = int(sys.argv[1]) if len(sys.argv) > 1 else 2021
CURRENT = P.session_of(datetime.now(ZoneInfo(P.TIMEZONE)).year)
CA = os.path.join(P.DATA, "ca.pem")
DELAY = 10  # robots.txt (ftp.ilga.gov and www.ilga.gov): "User-agent: *  Crawl-delay: 10", for every request to the host
STARTED = time.time()
# The bill files stop 12 minutes before the workflow step's limit (FETCH_MINUTES, from .github/states.json), leaving time
# for the member lists and Open States; what's left comes next run.
BUDGET = (float(os.environ.get("FETCH_MINUTES", "110")) - 12) * 60
_last = [0.0]


def pace():
    """Wait until DELAY seconds have passed since the last request to the repository."""
    wait = _last[0] + DELAY - time.time()
    if wait > 0:
        time.sleep(wait)
    _last[0] = time.time()


def out_of_time():
    return time.time() - STARTED > BUDGET


def ca_bundle():
    if os.path.exists(CA) and time.time() - os.path.getmtime(CA) < 30 * 86400:
        return CA
    os.makedirs(P.DATA, exist_ok=True)
    der = subprocess.run(["curl", "-sSf", "--max-time", "60", INTERMEDIATE], capture_output=True, check=True).stdout
    pem = subprocess.run(["openssl", "x509", "-inform", "DER"], input=der, capture_output=True, check=True).stdout
    system = next(p for p in SYSTEM_CAS if os.path.exists(p))
    with open(CA + ".tmp", "wb") as f:
        f.write(open(system, "rb").read() + b"\n" + pem)
    os.replace(CA + ".tmp", CA)
    return CA


def curl(args, check=True):
    for attempt in range(4):
        pace()
        r = subprocess.run(["curl", "-sS", "--cacert", CA, "--max-time", "300", "-A", AGENT, *args], capture_output=True)
        if r.returncode == 0:
            return r.stdout.decode("utf-8", "replace")
        time.sleep(5 * (attempt + 1))
    if check:
        raise SystemExit(f"failed: curl {args[-1]}: {r.stderr.decode(errors='replace').strip()}")
    return None


def listing(url):
    """File name -> 'date time size' from the server's folder listing."""
    page = curl([url], check=False) or ""
    out = {}
    for stamp, size, name in re.findall(r"(\d+/\d+/\d{4}\s+\d+:\d+ [AP]M)\s+(\d+)\s+<A HREF=\"[^\"]*\">([^<]+)</A>", page, re.I):
        out[name] = f"{stamp} {size}"
    return out


def complete(path):
    try:
        with open(path, "rb") as f:
            f.seek(max(0, os.path.getsize(path) - 32))
            return b"</xml>" in f.read()
    except OSError:
        return False


def session(ga):
    folder = os.path.join(P.DATA, str(ga), "billstatus")
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(P.DATA, str(ga), "dates.json")
    try:
        seen = json.load(open(path))
    except (OSError, ValueError):
        seen = {}
    files = {n: s for n, s in listing(f"{REPO}/Legislation/{ga}/BillStatus/XML/").items() if re.fullmatch(r"\d{5}(HB|SB|HC|SC)\d+\.xml", n)}
    todo = sorted(n for n, s in files.items() if not same(seen.get(n), s) or not complete(os.path.join(folder, n)))

    def get(name):
        body = curl([f"{REPO}/Legislation/{ga}/BillStatus/XML/{name}"], check=False)
        if body and body.rstrip().endswith("</xml>"):
            with open(os.path.join(folder, name), "w") as f:
                f.write(body)
            return name
        return None

    def stamp(n):  # the listing's time, newest first: the bills that just moved come before the rest
        try:
            return datetime.strptime(" ".join(files[n].split()[:3]), "%m/%d/%Y %I:%M %p")
        except ValueError:
            return datetime.min
    todo.sort(key=stamp, reverse=True)
    got = 0
    for k, name in enumerate(todo):
        if out_of_time():
            break
        if get(name):
            seen[name] = files[name]
            got += 1
        if k % 25 == 24:
            json.dump(seen, open(path, "w"))
    json.dump(seen, open(path, "w"))
    left = len(todo) - got
    print(f"GA {ga}: {got} bill status files downloaded, {len(files)} listed"
          + (f"; {left} left for the next run (one request every {DELAY} seconds)" if left else ""), flush=True)


def members(ga):
    folder = os.path.join(P.DATA, str(ga))
    os.makedirs(folder, exist_ok=True)
    for name in (f"Members/{ga}HouseMembers.xml", f"Members/{ga}SenateMembers.xml",
                 f"Committees/{ga}HouseCommitteeMembers.xml", f"Committees/{ga}SenateCommitteeMembers.xml"):
        body = curl([f"{REPO}/{name}"], check=False)
        # Only a real member or committee list replaces the last copy: on 2026-11-16 the server answered GitHub's runs
        # with something else, which was saved, and Illinois's contacts came out empty (the build then stopped).
        if body and re.search(r"<(?:Member|Committee)>", body):
            open(os.path.join(folder, os.path.basename(name)), "w").write(body)
        else:
            print(f"{name}: no member list in the answer ({len(body or '')} characters); keeping the last copy")


VETO_ACTION = re.compile(r"<action>Governor (?:Vetoed|Amendatory Veto|Item/Reduction Veto)")
VETO_AGAIN = 7 * 86400  # a message not there yet is asked for again after a week


def veto_messages(ga):
    """The governor's message on each bill he vetoed (total, amendatory or item/reduction), from the bill's folder in the
    repository: /Legislation/104/HB/10400HB2682gms.htm ("gms": governor's message), a Word page in Windows-1252, read once
    into data/il/<GA>/vetoes/HB2682.htm. The bills are the status files whose actions include "Governor Vetoed",
    "Governor Amendatory Veto" or "Governor Item/Reduction Veto". A 404 (the message is filed a few days after the veto) is
    noted in vetoes/missing.json and asked for again a week later. One request every DELAY seconds."""
    base = os.path.join(P.DATA, str(ga))
    out = os.path.join(base, "vetoes")
    path = os.path.join(out, "missing.json")
    try:
        missing = json.load(open(path))
    except (OSError, ValueError):
        missing = {}
    todo = []
    for f in sorted(glob.glob(os.path.join(base, "billstatus", "*.xml"))):
        m = re.search(r"\d{5}(HB|SB)(\d{4})\.xml$", f)
        if not m:
            continue
        bill = f"{m[1]}{int(m[2])}"
        if os.path.exists(os.path.join(out, bill + ".htm")) or time.time() - missing.get(bill, 0) < VETO_AGAIN:
            continue
        if VETO_ACTION.search(open(f, encoding="utf-8", errors="replace").read()):
            todo.append((bill, f"{REPO}/Legislation/{ga}/{m[1]}/{ga}00{m[1]}{m[2]}gms.htm"))
    got = 0
    for bill, url in todo:
        if out_of_time():
            break
        pace()
        r = subprocess.run(["curl", "-sS", "--cacert", CA, "--max-time", "120", "-A", AGENT, "-w", "%{http_code}", url],
                           capture_output=True)
        body, code = r.stdout[:-3], r.stdout[-3:].decode(errors="replace")
        if r.returncode == 0 and code == "200" and re.search(rb"(?i)General Assembly", body):  # a letter (amendatory ones say "return", not "veto")
            os.makedirs(out, exist_ok=True)
            open(os.path.join(out, bill + ".htm"), "wb").write(body)
            missing.pop(bill, None)
            got += 1
        elif r.returncode == 0 and code == "404":
            missing[bill] = time.time()
        else:
            print(f"veto message {url}: {code or r.stderr.decode(errors='replace').strip()}", flush=True)
    if todo:
        os.makedirs(out, exist_ok=True)
        json.dump(missing, open(path, "w"))
        print(f"GA {ga}: {got} of {len(todo)} veto messages downloaded", flush=True)


def main():
    ca_bundle()
    for year in sorted(range(FIRST, CURRENT + 3, 2), reverse=True):  # newest first
        ga = P.assembly_of(year)
        if listing(f"{REPO}/Legislation/{ga}/BillStatus/XML/") or os.path.isdir(os.path.join(P.DATA, str(ga))):
            session(ga)
            members(ga)  # each Assembly's members, to read its sponsor lists
            try:
                veto_messages(ga)
            except Exception as e:  # never holds Illinois back
                print(f"GA {ga}: veto messages failed ({type(e).__name__}: {e})", flush=True)
    people()


def people():
    """Open States' file of current members; a failed or odd answer keeps the last copy."""
    try:
        req = urllib.request.Request(PEOPLE, headers={"User-Agent": AGENT})
        with urllib.request.urlopen(req, timeout=120) as r:
            body = r.read()
    except Exception as e:
        print(f"{PEOPLE}: {e}; keeping the last copy")
        return
    if body.startswith(b"id,") and body.count(b"\n") > 100:
        path = os.path.join(P.DATA, "openstates_people.csv")
        open(path + ".tmp", "wb").write(body)
        os.replace(path + ".tmp", path)


def texts():
    """"What it does": each bill's synopsis by the Legislative Reference Bureau, as data/il/texts_<session>.json."""
    from states.il import convert as C
    for s in C.sessions():
        out = {p: {"statement": b["what"], "label": b["whatLabel"]} for p, b in C.bills(s).items() if b["what"]}
        json.dump(out, open(os.path.join(P.DATA, f"texts_{s}.json"), "w"), ensure_ascii=False)
        print(f"texts_{s}.json: {len(out)} synopses")


def contacts_session():
    """The session whose contacts to build: the current one once its Assembly's member lists are on file. In January of
    an odd year the new Assembly's bills (prefiled from December) come before its member lists, and contacts.py can't
    read lists that aren't there: until they are, the last Assembly's contacts are refreshed and the new session's
    page is built without legislators (build_data.py allows that when it has no contacts file)."""
    for s in (CURRENT, CURRENT - 2):
        ga = P.assembly_of(s)
        if all(os.path.exists(os.path.join(P.DATA, str(ga), f"{ga}{h}Members.xml")) for h in ("House", "Senate")):
            return s
    return CURRENT


if __name__ == "__main__":
    main()
    from states.il import contacts  # from the member and committee files just downloaded
    contacts.main(contacts_session())
    texts()
