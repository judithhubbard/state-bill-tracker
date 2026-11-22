#!/usr/bin/env python3
"""Download Pennsylvania's bills from the General Assembly's website (https://www.palegis.us/; see the
state-survey-2026-10-31 memory; robots.txt limits only an accessibility scanner).

- Each session's bill history file (https://www.palegis.us/data/file?documentType=BillHistoryData, a zipped XML with
  every bill's sponsors, printer's numbers and actions, refreshed hourly) into data/pa/billhistory_<year>_0.zip. A
  finished session's is read once.
- The roll calls, which the file doesn't have: each bill page with a committee report or a floor vote lists its floor
  and committee roll calls, and each roll call's page lists every member's vote (committee votes also carry a "Brief
  Description" of the bill). Into data/pa/<year>/bills/<HB17>.json (the bill's roll-call links, read again when the
  bill's lastUpdate changes) and data/pa/<year>/rollcalls/<house>_<key>.json (one per roll call; read once).
One request a second. Usage: python3 states/pa/fetch.py [first_year]   (default: the shared window's first session, states/window.py: from 2023-24 until 2029)
"""
import html, io, json, os, re, sys, time, urllib.request, zipfile
import xml.etree.ElementTree as ET
from datetime import date
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
from states import window as W

SITE = "https://www.palegis.us"
DATA = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "pa"))
AGENT = "statebilltracker.org (a nonprofit bill tracker; contact via github.com/judithhubbard)"
YEAR = date.today().year
CURRENT = YEAR if YEAR % 2 else YEAR - 1
FIRST = int(sys.argv[1]) if len(sys.argv) > 1 else W.first_session()
INCOMPLETE = set()
WHOLE = [True]  # the last run left nothing missing (set in main): roll calls still to read then don't hold the site
# Steps that come with a roll call: committee reports and floor votes.
VOTED = re.compile(r"Reported|Re-reported|final passage|concurred|Amended in .* Committee|defeated", re.I)


def get(url, binary=False):
    for attempt in range(3):
        time.sleep(1)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": AGENT})
            with urllib.request.urlopen(req, timeout=120) as r:
                data = r.read()
                return data if binary else data.decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            time.sleep(10 * (attempt + 1))
        except Exception:
            time.sleep(10 * (attempt + 1))
    return False


def save(path, data):
    json.dump(data, open(path + ".tmp", "w"), ensure_ascii=False)
    os.replace(path + ".tmp", path)


def history(session):
    """The session's bill history file; returns the parsed bills (or None)."""
    path = os.path.join(DATA, f"billhistory_{session}_0.zip")
    if session >= CURRENT or not os.path.exists(path):
        data = get(f"{SITE}/data/file?documentType=BillHistoryData&session={session}_0", binary=True)
        if data and data[:2] == b"PK":
            open(path + ".tmp", "wb").write(data)
            os.replace(path + ".tmp", path)
        else:
            print(f"{session}: no bill history file; kept the last copy")
            if not os.path.exists(path):  # only a file never downloaded holds the state off the site
                INCOMPLETE.add(session)
    if not os.path.exists(path):
        return None
    z = zipfile.ZipFile(path)
    return ET.parse(io.BytesIO(z.read(z.namelist()[0]))).getroot().iter("bill")


BIO = re.compile(r"/(house|senate)/members/bio/(\d+)/[^\"']*[\"'][^>]*>\s*([^<]+?)\s*</a>")
VOTE = re.compile(r'title="(Yea|Nay|No Vote|Leave|Excused|Not Voting|Absent)"')
ROLL = re.compile(r"""href=["'](/(?:house|senate)/(?:committees/roll-call-votes/vote-list/vote-summary|roll-calls/summary)\?[^"']+)["']""")


def plain(s):
    s = re.sub(r"(?s)<script.*?</script>|<style.*?</style>", " ", s)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s))).strip()


def rollcall(page, link):
    """One roll call page -> {house, kind, date, motion, committee, description, members: [[id, name, vote]]}."""
    t = plain(page)
    field = lambda name, stop: (re.search(rf"{name} (.+?) (?:{stop})", t) or [None, ""])[1].strip()
    members = {}
    hits = list(BIO.finditer(page))
    for a, b in zip(hits, hits[1:] + [None]):
        v = VOTE.search(page[a.end(): b.start() if b else len(page)])
        if v:
            members[int(a.group(2))] = [int(a.group(2)), html.unescape(a.group(3)), v.group(1)]
    committee = "committees" in link
    return {
        "house": "S" if link.startswith("/senate") else "H",
        "kind": "C" if committee else "F",
        "date": field("Vote Date", r"\d{1,2}:\d\d|Bill") if not committee else field("Date", "Bill/Resolution"),
        "motion": field("Action", "Short Title|Prime Sponsor") if not committee else field("Type of Motion", "Maker of Motion|Brief"),
        "committee": field("Vote Details Committee", "Date") if committee else "",
        "description": field("Brief Description", "Vote Summary") if committee else "",
        "members": list(members.values()),
    }


def rc_key(link):
    """A roll call's file name. The House's and the Senate's floor roll calls are numbered alike (rcNum=202 in each), and
    until 2026-11-22 their files had the same name: whichever house's was saved first kept the other's out, so about 300
    Senate floor roll calls a session (and 60 House ones) were never saved, and those votes showed tallies without names.
    New files start with the house ("senate_", "house_"); older files are matched by the link they hold."""
    key = re.sub(r"\W+", "_", link.split("?", 1)[1] + ("_c" if "committees" in link else "_f"))
    return ("senate_" if link.startswith("/senate") else "house_") + key


def votes(session, bills):
    folder = os.path.join(DATA, str(session))
    for sub in ("bills", "rollcalls"):
        os.makedirs(os.path.join(folder, sub), exist_ok=True)
    have = set()  # the roll calls saved, by link
    for f in os.listdir(os.path.join(folder, "rollcalls")):
        if f.endswith(".json"):
            try:
                have.add(json.load(open(os.path.join(folder, "rollcalls", f))).get("link"))
            except ValueError:
                pass

    def read_rollcalls(links):
        """Saves the roll calls not yet saved; False if one couldn't be read (asked again next run)."""
        ok = True
        for link in links:
            if link in have:
                continue
            rpage = get(SITE + link)
            if rpage:
                save(os.path.join(folder, "rollcalls", f"{rc_key(link)}.json"), dict(rollcall(rpage, link), link=link))
                have.add(link)
            elif rpage is False:
                ok = False
                if not WHOLE[0]:
                    INCOMPLETE.add(session)
        return ok

    todo, known = [], []
    for b in bills:
        if b.findtext("type") != "B" or not any(VOTED.search(a.findtext("verb") or "") for a in b.iter("action")):
            continue
        num = f"{b.findtext('body')}B{int(b.findtext('number'))}"
        path = os.path.join(folder, "bills", f"{num}.json")
        old = json.load(open(path)) if os.path.exists(path) else None
        if not old or old.get("lastUpdate") != b.get("lastUpdate"):
            todo.append((num, b.get("lastUpdate"), path))
        else:
            known += old.get("rollcalls", [])
    # Roll calls listed on bill pages read before but never saved (the clash above): read without the bill page.
    left = sorted(set(l for l in known if l not in have))
    print(f"{session}: {len(todo)} bill pages to read; {len(left)} roll calls of pages read before", flush=True)
    read_rollcalls(left)
    done = 0
    for num, stamp, path in todo:
        page = get(f"{SITE}/legislation/bills/{session}/{num.lower()}")
        if page is False:  # asked again next run
            if not WHOLE[0]:  # roll calls still to read hold only a first copy; later they fill in run by run
                INCOMPLETE.add(session)
            continue
        links = sorted(set(html.unescape(l) for l in ROLL.findall(page or "")))
        if not read_rollcalls(links):
            stamp = None  # the bill page is read again next run, for this roll call
        save(path, {"lastUpdate": stamp, "rollcalls": links})
        done += 1
        if done % 100 == 0:
            print(f"{session}: {done} of {len(todo)} bill pages", flush=True)


def begun(session):
    """Whether a session has convened (the first Tuesday of January of its first year)."""
    return date.today() >= date(session, 1, 1 + (1 - date(session, 1, 1).weekday()) % 7)


def main():
    os.makedirs(DATA, exist_ok=True)
    WHOLE[0] = not os.path.exists(os.path.join(DATA, "incomplete"))
    sys.path.insert(0, os.path.normpath(os.path.join(DATA, "..", "..")))
    from states.pa import contacts
    try:
        contacts.main(CURRENT)
    except SystemExit as e:
        print(e)
    # Every session's bill history first (small, and enough for the pages), then the roll calls, the current session's
    # first: a first copy of the roll calls takes several runs.
    got = {}
    for s in range(FIRST, CURRENT + 1, 2):
        bills = history(s)
        if bills is not None:
            got[s] = list(bills)
    for s in sorted(got, reverse=True):
        votes(s, got[s])
    marker = os.path.join(DATA, "incomplete")
    # A session not yet begun (no bill history file yet) is read when it's there but never holds Pennsylvania back.
    undone = {s for s in INCOMPLETE if begun(s)}
    if undone:
        open(marker, "w").write(" ".join(map(str, sorted(undone))) + "\n")
    elif os.path.exists(marker):
        os.remove(marker)


if __name__ == "__main__":
    main()
