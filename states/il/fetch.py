#!/usr/bin/env python3
"""Download Illinois bill status files, members and committees from the General Assembly's public file repository
(https://ftp.ilga.gov/), the place it asks automated programs to use (www.ilga.gov turns them away).

- /Legislation/<GA>/BillStatus/XML/: one XML per bill; the folder listing's dates decide which changed since the last
  run, and only those are downloaded (six at a time). Into data/il/<GA>/billstatus/, with listing dates in dates.json.
- /Members/<GA>HouseMembers.xml, <GA>SenateMembers.xml and /Committees/<GA>...CommitteeMembers.xml, every run.

The servers don't send the intermediate certificate their own certificate needs (Sectigo Public Server Authentication
CA OV R40), so it's fetched from Sectigo and added to a copy of the system's certificates (data/il/ca.pem); the
connection is still fully checked.
Usage: python3 states/il/fetch.py [first_year]   (default 2021)
"""
import json, os, re, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
from states.il import profile as P

REPO = "https://ftp.ilga.gov"
INTERMEDIATE = "http://crt.sectigo.com/SectigoPublicServerAuthenticationCAOVR40.crt"
SYSTEM_CAS = ["/etc/ssl/certs/ca-certificates.crt", "/etc/ssl/cert.pem", "/etc/pki/tls/certs/ca-bundle.crt"]
FIRST = int(sys.argv[1]) if len(sys.argv) > 1 else 2021
CURRENT = P.session_of(datetime.now(ZoneInfo(P.TIMEZONE)).year)
CA = os.path.join(P.DATA, "ca.pem")


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
        r = subprocess.run(["curl", "-sS", "--cacert", CA, "--max-time", "300", *args], capture_output=True)
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
    files = {n: s for n, s in listing(f"{REPO}/Legislation/{ga}/BillStatus/XML/").items() if re.fullmatch(r"\d{5}(HB|SB)\d+\.xml", n)}
    todo = sorted(n for n, s in files.items() if seen.get(n) != s or not complete(os.path.join(folder, n)))

    def get(name):
        body = curl([f"{REPO}/Legislation/{ga}/BillStatus/XML/{name}"], check=False)
        if body and body.rstrip().endswith("</xml>"):
            with open(os.path.join(folder, name), "w") as f:
                f.write(body)
            return name
        return None

    got = 0
    with ThreadPoolExecutor(6) as pool:
        for k, name in enumerate(pool.map(get, todo)):
            if name:
                seen[name] = files[name]
                got += 1
            if k % 500 == 499:
                json.dump(seen, open(path, "w"))
    json.dump(seen, open(path, "w"))
    print(f"GA {ga}: {got} bill status files downloaded, {len(files)} listed")


def members(ga):
    folder = os.path.join(P.DATA, str(ga))
    os.makedirs(folder, exist_ok=True)
    for name in (f"Members/{ga}HouseMembers.xml", f"Members/{ga}SenateMembers.xml",
                 f"Committees/{ga}HouseCommitteeMembers.xml", f"Committees/{ga}SenateCommitteeMembers.xml"):
        body = curl([f"{REPO}/{name}"], check=False)
        if body and "<" in body:
            open(os.path.join(folder, os.path.basename(name)), "w").write(body)


def main():
    ca_bundle()
    for year in sorted(range(FIRST, CURRENT + 3, 2), reverse=True):  # newest first
        ga = P.assembly_of(year)
        if listing(f"{REPO}/Legislation/{ga}/BillStatus/XML/") or os.path.isdir(os.path.join(P.DATA, str(ga))):
            session(ga)
            members(ga)  # each Assembly's members, to read its sponsor lists


def texts():
    """"What it does": each bill's synopsis by the Legislative Reference Bureau, as data/il/texts_<session>.json."""
    from states.il import convert as C
    for s in C.sessions():
        out = {p: {"statement": b["synopsis"], "label": "From the Legislative Reference Bureau's synopsis."}
               for p, b in C.bills(s).items() if b["synopsis"]}
        json.dump(out, open(os.path.join(P.DATA, f"texts_{s}.json"), "w"), ensure_ascii=False)
        print(f"texts_{s}.json: {len(out)} synopses")


if __name__ == "__main__":
    main()
    from states.il import contacts  # from the member and committee files just downloaded
    contacts.main(CURRENT)
    texts()
