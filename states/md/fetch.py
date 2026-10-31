#!/usr/bin/env python3
"""Download Maryland's bills and members from the General Assembly's website (https://mgaleg.maryland.gov/; no
robots.txt; see the state-survey-2026-10-31 memory).

- Each regular session's bill list (/<year>RS/misc/billsmasterlist/legislation.json: every bill's sponsors, synopsis,
  committees, the dates and results of each reading in each house, the chapter number and the status) into
  data/md/legislation_<year>RS.json. A finished session's (after its governor's last vetoes, by June) is read once.
- The members: each house's member list and each member's page (district, county, party, committees, Annapolis phone,
  email), into data/md/members.json; then states/md/contacts.py.
Usage: python3 states/md/fetch.py
"""
import html, json, os, re, sys, time, urllib.request
from datetime import date

SITE = "https://mgaleg.maryland.gov"
DATA = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "md"))
AGENT = "statebilltracker.org (a nonprofit bill tracker; contact via github.com/judithhubbard)"
TODAY = date.today()
INCOMPLETE = []


def get(url):
    for attempt in range(3):
        time.sleep(0.5)
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": AGENT}), timeout=180) as r:
                return r.read().decode("utf-8", "replace")
        except Exception:
            time.sleep(10 * (attempt + 1))
    return None


def plain(s):
    s = re.sub(r"(?s)<script.*?</script>|<style.*?</style>", " ", s)
    t = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " | ", s)))
    return re.sub(r"(?:\|\s*)+", "| ", t)


def member(code, house):
    page = get(f"{SITE}/mgawebsite/Members/Details/{code}")
    if not page:
        return None
    t = plain(page)
    m = re.search(r"\| (Delegate|Senator) ([^|]+?) \| Main \| Legislation", t)
    if not m:
        return None
    field = lambda name: (re.search(rf"\| {name} \| ([^|]+?) \|", t) or [None, ""])[1].strip()
    comms = re.search(r"\| Committee Assignment\(s\) \| (.+?) \| Annapolis Info", t)
    phone = re.search(r"Annapolis Info .*?Phone (\d{3}-\d{3}-\d{4})", t)
    email = next((e for e in re.findall(r"mailto:([\w.+-]+@(?:senate|house)\.maryland\.gov)", page) if ".Ind@" not in e), None)
    return {"code": code, "house": house, "name": m.group(2).strip(), "district": field("District"), "county": field("County"),
            "party": field("Party"), "committees": [c.strip() for c in comms.group(1).split("|")] if comms else [],
            "phone": phone.group(1) if phone else "", "email": email,
            "url": f"{SITE}/mgawebsite/Members/Details/{code}"}


def members():
    out = []
    for house, path in (("S", "senate"), ("H", "house")):
        page = get(f"{SITE}/mgawebsite/Members/Index/{path}") or ""
        for code in sorted(set(re.findall(r"/mgawebsite/Members/Details/([\w-]+)", page))):
            m = member(code, house)
            if m:
                out.append(m)
    if len(out) < 180:
        print(f"members: only {len(out)}; kept the last copy")
        INCOMPLETE.append("members")
        return
    json.dump(out, open(os.path.join(DATA, "members.json"), "w"), indent=1, ensure_ascii=False)
    print(f"members: {len(out)}")


def sessions():
    """The current year's session and the two before; a year's session from the second Wednesday of January."""
    return [TODAY.year - 2, TODAY.year - 1, TODAY.year]


def main():
    os.makedirs(DATA, exist_ok=True)
    for y in sessions():
        path = os.path.join(DATA, f"legislation_{y}RS.json")
        # A session's file changes until the governor's last vetoes (late May); after June it's final.
        if os.path.exists(path) and (y < TODAY.year - 1 or (y < TODAY.year and TODAY.month > 6)):
            continue
        body = get(f"{SITE}/{y}RS/misc/billsmasterlist/legislation.json")
        try:
            data = json.loads(body) if body else None
        except ValueError:
            data = None
        if data:
            json.dump(data, open(path + ".tmp", "w"), ensure_ascii=False)
            os.replace(path + ".tmp", path)
            print(f"{y}: {len(data)} bills")
        elif y < TODAY.year or TODAY.month > 1:
            print(f"{y}: no bill list; kept the last copy")
    members()
    sys.path.insert(0, os.path.normpath(os.path.join(DATA, "..", "..")))
    from states.md import contacts
    try:
        contacts.main(contacts.P.session_of(TODAY.year))
    except SystemExit as e:
        print(e)
    marker = os.path.join(DATA, "incomplete")
    if INCOMPLETE:
        open(marker, "w").write(" ".join(INCOMPLETE) + "\n")
    elif os.path.exists(marker):
        os.remove(marker)


if __name__ == "__main__":
    main()
