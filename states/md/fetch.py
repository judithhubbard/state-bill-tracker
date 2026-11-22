#!/usr/bin/env python3
"""Download Maryland's bills and members from the General Assembly's website (https://mgaleg.maryland.gov/; no
robots.txt; see the state-survey-2026-10-31 memory).

- Each regular session's bill list (/<year>RS/misc/billsmasterlist/legislation.json: every bill's sponsors, synopsis,
  committees, the dates and results of each reading in each house, the chapter number and the status) into
  data/md/legislation_<year>RS.json. A finished session's (after its governor's last vetoes, by June) is read once.
- The governor's actions and the veto overrides, which the bill list lacks: each bill the General Assembly passed, its
  page (/mgawebsite/Legislation/Details/<bill>?ys=<year>RS), whose history has the day the governor signed or vetoed it
  ("Post Passage") and any override, often months later in another session ("Overridden (111-23)", "Became law per
  Maryland Constitution, Chapter 3 of 2025 Special Session"; the bill list still says "Vetoed"). Into
  data/md/governor_<year>.json; a decided bill's page is read once, a vetoed one weekly while it can be overridden, an
  undecided one daily; at most GOV_MINUTES of a run, the rest on later runs.
- The members: each house's member list (every run) and each member's page (district, county, party, committees, Annapolis
  phone, email; once a day, and at once for a new member), into data/md/members.json; then states/md/contacts.py.
Usage: python3 states/md/fetch.py
"""
import html, json, os, re, sys, time, urllib.request
from datetime import date, datetime, timedelta
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
from states import window as W

SITE = "https://mgaleg.maryland.gov"
DATA = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "md"))
AGENT = "statebilltracker.org (a nonprofit bill tracker; contact via github.com/judithhubbard)"
TODAY = date.today()
INCOMPLETE = []
START = time.time()
GOV_MINUTES = float(os.environ.get("MD_GOV_MINUTES", 11))  # of the state's 20-minute run; the members' pages take about 2, once a day


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
    """Each house's member list is read every run; a member's own page at most once a day (the day each was last read is
    in members_read.json), and at once for a member the list names for the first time (a new member, or one who changed
    house)."""
    path, stamps_path = os.path.join(DATA, "members.json"), os.path.join(DATA, "members_read.json")
    old = {(m["house"], m["code"]): m for m in (json.load(open(path)) if os.path.exists(path) else [])}
    read = json.load(open(stamps_path)) if os.path.exists(stamps_path) else {}
    out, stamps, fetched = [], {}, 0
    for house, where in (("S", "senate"), ("H", "house")):
        page = get(f"{SITE}/mgawebsite/Members/Index/{where}") or ""
        for code in sorted(set(re.findall(r"/mgawebsite/Members/Details/([\w-]+)", page))):
            key = f"{house}:{code}"
            m = old.get((house, code)) if read.get(key) == TODAY.isoformat() else None
            if not m:
                m, fetched = member(code, house) or old.get((house, code)), fetched + 1  # (a page that fails: the last copy, read again next run)
            if m:
                out.append(m)
                stamps[key] = read.get(key) if m is old.get((house, code)) else TODAY.isoformat()
    if len(out) < 180:
        print(f"members: only {len(out)}; kept the last copy")
        if not os.path.exists(path):  # only a list never read holds the state off
            INCOMPLETE.append("members")
        return
    if out != list(old.values()):
        json.dump(out, open(path, "w"), indent=1, ensure_ascii=False)
    json.dump(stamps, open(stamps_path, "w"), indent=0, sort_keys=True)
    print(f"members: {len(out)} ({fetched} member pages read; the others were read earlier today)")


def history(page):
    """A bill page's history table: [[chamber, calendar date (ISO), action]] for the governor's actions and everything
    from the first of them on (overrides), and the page's status."""
    rows, out, after = [], [], False
    for tr in re.findall(r"(?s)<tr>(.*?)</tr>", page):
        tds = [re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", td))).strip() for td in re.findall(r"(?s)<td>(.*?)</td>", tr)]
        if len(tds) >= 4 and tds[3] and re.fullmatch(r"\d{1,2}/\d{1,2}/\d{4}", tds[1]):
            m, d, y = tds[1].split("/")
            rows.append([tds[0], f"{y}-{int(m):02d}-{int(d):02d}", tds[3]])
    for r in rows:
        after = after or r[0] == "Post Passage"
        if after or re.search(r"governor|veto|overrid|became law", r[2], re.I):
            out.append(r)
    st = re.search(r'(?s)<dt class="col-sm-2">Status</dt>\s*<dd class="col-sm-10">(.*?)</dd>', page)
    return out, re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", st.group(1)))).strip() if st else ""


def governor(y, bills, vetoes_only=False):
    """The governor's actions and overrides of the bills the General Assembly passed in year y's session."""
    path = os.path.join(DATA, f"governor_{y}.json")
    try:
        have = json.load(open(path))
    except (OSError, ValueError):
        have = {}
    live = y >= TODAY.year - 1  # a veto can be overridden at the next session (or a special one before it)

    def due(b):
        n = b["BillNumber"]
        got = have.get(n)
        if not got:
            return 0
        lines = " ".join(l[2] for l in got["lines"])
        age = (TODAY - date.fromisoformat(got["read"])).days
        # Decided for good: signed, law without signature, or law over the veto (one house's override isn't enough).
        if re.search(r"Approved by the Governor|Enacted under|Became law|Assigned a chapter|Gubernatorial Veto Override", lines):
            return None
        if not live:
            return None
        if re.search(r"Vetoed by the Governor", lines):
            return 2 if age >= 7 else None
        return 1 if age >= 1 else None

    todo = []
    for b in bills:
        if not b.get("PassedByMGA") or b["BillNumber"][:2] not in ("HB", "SB"):
            continue
        if b.get("ConstitutionalAmendment") and not str(b.get("Status", "")).startswith("Approved"):
            continue  # goes to the voters, not the governor
        k = due(b)
        if k is not None:
            # Vetoes first (a vetoed bill's status may show a later motion instead, but it has no chapter, or an override's)
            vetoish = "veto" in str(b.get("Status")).lower() or not b.get("ChapterNumber")
            if vetoish or not vetoes_only:
                todo.append((k, not vetoish, b["BillNumber"]))
    todo.sort()
    done = 0
    for _, _, n in todo:
        if time.time() - START > GOV_MINUTES * 60:
            break
        # Bills of a special session held after the regular one are in its list too (HB 2101 of 2026, August 3), with
        # pages under the special session's code ("NotFound" under 2026RS).
        for code in ("RS", "S1", "S2"):
            page = get(f"{SITE}/mgawebsite/Legislation/Details/{n.lower()}?ys={y}{code}")
            if not page or "Legislation History" in page:
                break
        if not page or "Legislation History" not in page:
            continue
        lines, status = history(page)
        have[n] = {"read": TODAY.isoformat(), "status": status, "lines": lines}
        done += 1
        if done % 50 == 0:
            json.dump(have, open(path + ".tmp", "w"), ensure_ascii=False)
            os.replace(path + ".tmp", path)
    if done:
        json.dump(have, open(path + ".tmp", "w"), ensure_ascii=False)
        os.replace(path + ".tmp", path)
    if todo:
        print(f"{y}: governor's actions read for {done} bills; {len(todo) - done} left for later runs" if len(todo) > done else
              f"{y}: governor's actions read for {done} bills")


def parse_meetings(page):
    """The Meetings page (/mgawebsite/Meetings/Day/<MMDDYYYY><MMDDYYYY>?ys=2026rs) -> [(committee, "2026-02-17T13:00:00",
    [bill numbers])]. Each committee's banner (class "senate", "house" or "other") is followed by its meetings, each a
    hearsched-hearing-header ("Canceled" first when it is) with the day, "Education, Energy, and the Environment
    Committee - Bill Hearing" (or "- Voting Session"), "1:00 PM - West Miller Senate Building, ...", then its bills
    (links to /mgawebsite/Legislation/Details/SB0325; struck-through rows, class hearsched-strike, were removed) and a
    footer that may say "Withdrawn bills: HB46, HB 296, ...". Canceled meetings are left out."""
    out = []
    banners = re.split(r'<div class="hearsched-committee-banner (senate|house|other)\b[^"]*">', page)
    for i in range(1, len(banners) - 1, 2):
        kind, block = banners[i], banners[i + 1]
        # The banner's text: a committee's linked name, a subcommittee's "Pensions Subcommittee - (Budget and Taxation
        # Committee)", or (class "other") a county delegation ("Anne Arundel", "No. 4 - Baltimore County"), a caucus.
        name = re.split(r'<a class="popover-icon"|</div>', block, 1)[0]
        name = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", name))).strip()
        if not name:
            continue
        sub = re.match(r"(.+?) - \((.+?) Committee\)$", name)
        if sub:
            name = f"{sub.group(2)} {sub.group(1)}"  # "Budget and Taxation Pensions Subcommittee"
        name = re.sub(r" Committee$", "", name)
        if kind == "other":
            caucus = re.search(r"Caucus|Board|Commission|Committee|Council", name)
            name = f"Joint {name}" if caucus else f"Joint {name} Delegation"
        else:
            name = f"{'Senate' if kind == 'senate' else 'House'} {name}"
        for meet in block.split('<div class="hearsched-hearing-header">')[1:]:
            head = meet.split("hearsched-table", 1)[0]
            if re.search(r'<div class="font-weight-bold">\s*Cancel+ed\s*</div>', head):
                continue
            day = re.search(r"(?:Sunday|Monday|Tuesday|Wednesday|Thursday|Friday|Saturday), (\w+ \d+, \d{4})", head)
            if not day:
                continue
            try:
                d = datetime.strptime(day.group(1), "%B %d, %Y").date()
            except ValueError:
                continue
            t = re.search(r">\s*(\d+):(\d\d) ([AP])M\b", head)
            hour = (int(t.group(1)) % 12 + (12 if t.group(3) == "P" else 0)) if t else 0
            stamp = f"{d.isoformat()}T{hour:02d}:{int(t.group(2)) if t else 0:02d}:00"
            gone = set()
            foot = re.search(r"Withdrawn bills:([^<]*)", meet)
            if foot:
                gone = {f"{a}{int(b)}" for a, b in re.findall(r"\b([HS][BJ])\s*0*(\d+)", foot.group(1))}
            bills = []
            for strike, a, b in re.findall(r'<div class="col-sm-2( hearsched-strike)?"><a href="/mgawebsite/Legislation/Details/([HS][BJ])0*(\d+)\?', meet):
                k = f"{a}{int(b)}"
                if not strike and k not in gone and k not in bills:
                    bills.append(k)
            out.append((name, stamp, bills))
    return out


def agendas(year):
    """Bills on committee meetings (hearings and voting sessions) from yesterday to three weeks ahead, from the General
    Assembly's hearing schedule, one page for the whole range, into data/md/agendas_<year>.json: bill -> [["Senate
    Education, Energy, and the Environment", "2026-02-17T13:00:00"], ...]. A failure keeps the last file."""
    first, last = TODAY - timedelta(days=1), TODAY + timedelta(days=21)
    page = get(f"{SITE}/mgawebsite/Meetings/Day/{first:%m%d%Y}{last:%m%d%Y}?budget=show&cmte=allcommittees&updates=show&ys={year}rs")
    if not page or "hearsched" not in page:
        print(f"{year}: no hearing schedule; kept the last agendas")
        return
    out, n = {}, 0
    for name, stamp, bills in parse_meetings(page):
        if not first.isoformat() <= stamp[:10] <= last.isoformat():
            continue
        n += 1
        for b in bills:
            if [name, stamp] not in out.setdefault(b, []):
                out[b].append([name, stamp])
    path = os.path.join(DATA, f"agendas_{year}.json")
    json.dump(out, open(path + ".tmp", "w"), ensure_ascii=False)
    os.replace(path + ".tmp", path)
    print(f"{year}: agendas: {len(out)} bills on {n} meetings")


def sessions():
    """The years of the shared window (states/window.py: this year and the four before, not before 2023), the current
    one first; a year's session from the second Wednesday of January. Each is one file, so a year the window adds back
    is either there or not, and never holds the state off the site."""
    return W.years()[::-1]


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
    try:
        agendas(TODAY.year)
    except Exception as e:  # agendas never break the run
        print(f"agendas failed ({type(e).__name__}); kept the last file")
    # Every year's vetoes first (overrides), then the rest.
    for only in (True, False):
        for y in sessions():
            path = os.path.join(DATA, f"legislation_{y}RS.json")
            if os.path.exists(path):
                governor(y, json.load(open(path)), only)
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
