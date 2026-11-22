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
- The House floor calendars' staff descriptions of each bill ("This bill bans paraquat."; `calendars()`), going forward.
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


def has_bills(data):
    """Whether a bill history zip lists at least one bill (a new session's file may exist before any bill does)."""
    try:
        z = zipfile.ZipFile(io.BytesIO(data))
        return b"<bill" in z.read(z.namelist()[0])
    except (zipfile.BadZipFile, IndexError, KeyError):
        return False


def history(session):
    """The session's bill history file; returns the parsed bills (or None)."""
    path = os.path.join(DATA, f"billhistory_{session}_0.zip")
    # The session just ended is read again until February (the governor's last actions on it).
    ending = session == CURRENT - 2 and date.today() < date(CURRENT, 2, 1)
    if session >= CURRENT or ending or not os.path.exists(path):
        data = get(f"{SITE}/data/file?documentType=BillHistoryData&session={session}_0", binary=True)
        if data and data[:2] == b"PK" and has_bills(data):
            open(path + ".tmp", "wb").write(data)
            os.replace(path + ".tmp", path)
        else:
            print(f"{session}: no bill history file (or no bills in it yet); kept the last copy")
            # Only a file never downloaded holds the state off the site, and not a new session's in its first two
            # months (the file answers 404 until the session has bills; bills are introduced only once it convenes).
            if not os.path.exists(path) and not (session == CURRENT and date.today() < date(session, 3, 1)):
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


def titled(name):
    n = re.sub(r"\b([A-Za-z])([A-Za-z']*)", lambda m: m.group(1).upper() + m.group(2).lower(), name)
    return re.sub(r"(?<!^)\b(And|Of|The|On|For|To|In)\b", lambda m: m.group(1).lower(), n)


def agendas(session):
    """Bills on committee meetings from yesterday to three weeks ahead, from each chamber's committee meeting RSS feed
    (https://www.palegis.us/house/rss/committee/schedule, /senate/...): each item's <parss:Bills> lists the bills
    ("HB1964,HB2131,HR403"). Into data/pa/<session>/agendas.json: bill -> [["House Health", "2027-02-03T09:30:00"], ...].
    A feed that fails keeps the last file."""
    ns = "{https://www.legis.state.pa.us/RSS}"
    first, last = date.fromordinal(date.today().toordinal() - 1), date.fromordinal(date.today().toordinal() + 21)
    out, n = {}, 0
    for house in ("house", "senate"):
        body = get(f"{SITE}/{house}/rss/committee/schedule")
        if not body:
            print(f"agendas: no {house} feed; kept the last file")
            return
        try:
            items = ET.fromstring(body.encode("utf-8")).iter("item")
        except ET.ParseError:
            print(f"agendas: {house} feed unreadable; kept the last file")
            return
        for it in items:
            words = " ".join((it.findtext(k) or "") for k in ("title", "description"))
            if re.search(r"cancel|postpone", words, re.I):
                continue
            m = re.match(r"(\d\d)/(\d\d)/(\d{4})$", (it.findtext(ns + "MeetingDate") or "").strip())
            if not m:
                continue
            day = date(int(m.group(3)), int(m.group(1)), int(m.group(2)))
            if not first <= day <= last:
                continue
            bills = re.findall(r"\b([HS]B)\s*0*(\d+)\b", it.findtext(ns + "Bills") or "")
            if not bills:
                continue
            n += 1
            t = re.match(r"(\d{1,2}):(\d\d)\s*([AP])M", (it.findtext(ns + "MeetingTime") or "").strip(), re.I)
            clock = "00:00:00"
            if t:
                hour = int(t.group(1)) % 12 + (12 if t.group(3).upper() == "P" else 0)
                clock = f"{hour:02d}:{t.group(2)}:00"
            name = re.sub(r"\s*\((H|S)\)$", "", html.unescape(it.findtext(ns + "Committee") or "").strip())
            if not re.match(r"(HOUSE|SENATE|JOINT)\b", name, re.I):
                name = f"{house} {name}"
            entry = [titled(re.sub(r"\s+", " ", name)), f"{day.isoformat()}T{clock}"]
            for kind, num in bills:
                if entry not in out.setdefault(f"{kind}{int(num)}", []):
                    out[f"{kind}{int(num)}"].append(entry)
    os.makedirs(os.path.join(DATA, str(session)), exist_ok=True)
    save(os.path.join(DATA, str(session), "agendas.json"), out)
    print(f"agendas: {len(out)} bills on {n} meetings")


CAL_LISTS = ["/house/session/calendars", "/house/session/calendars?c=22", "/house/session/calendars?c=23"]
CAL_AGAIN = 6 * 3600  # the calendar pages listed: looked at every 6 hours (a new calendar after each session day)


def calendar_entries(page):
    """A House calendar page (/house/session/calendars/view?CalendarId=11117&ext=HTML) -> (day, session's first year,
    {"HB1135": "This bill bans paraquat."}): each bill row (its number's link, body=H&type=B&bn=1135) and the staff's
    one- or two-sentence description in the row after it (<td class="analysis">). Resolutions have none."""
    m = re.search(r"SESSION OF (\d{4})-\d{4}", page)
    year = int(m[1]) if m else None
    m = re.search(r"(JANUARY|FEBRUARY|MARCH|APRIL|MAY|JUNE|JULY|AUGUST|SEPTEMBER|OCTOBER|NOVEMBER|DECEMBER) (\d{1,2}), (\d{4})", page)
    months = ["JANUARY", "FEBRUARY", "MARCH", "APRIL", "MAY", "JUNE", "JULY", "AUGUST", "SEPTEMBER", "OCTOBER", "NOVEMBER", "DECEMBER"]
    day = date(int(m[3]), months.index(m[1]) + 1, int(m[2])).isoformat() if m else ""
    out = {}
    rows = re.split(r"(?i)<tr\b", page)
    for i, row in enumerate(rows):
        n = re.search(r"body=([HS])&(?:amp;)?type=B&(?:amp;)?bn=(\d+)", row)
        if not n:
            continue
        for nxt in rows[i + 1:i + 3]:
            a = re.search(r'(?is)<td[^>]*class="analysis"[^>]*>(.*?)</td>', nxt)
            if a:
                t = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", a[1]))).strip()
                if len(t) >= 15:
                    out[f"{n[1]}B{int(n[2])}"] = t
                break
            if re.search(r"body=[HS]&", nxt):
                break
    return day, year, out


def calendars():
    """The staff's description of each bill on the House's floor calendars (the Calendar, the Tabled Bill Calendar and the
    Uncontested Calendar: only the current ones are linked, so this works going forward), into
    data/pa/<year>/calendar_descriptions.json: {bill: [calendar day, description]}, each bill's latest. The lists are
    looked at every CAL_AGAIN seconds; each calendar is read once (a new one is printed after each session day).
    Fails quietly: the last file stays."""
    state_path = os.path.join(DATA, "calendars_read.json")
    try:
        st = json.load(open(state_path))
    except (OSError, ValueError):
        st = {}
    if time.time() - st.get("listed", 0) < CAL_AGAIN:
        return
    ids = []
    for path in CAL_LISTS:
        page = get(SITE + path)
        if not page:
            print(f"calendars: {path} didn't answer; kept the last file")
            return
        ids += [i for i in re.findall(r"calendars/view\?CalendarId=(\d+)&(?:amp;)?ext=HTML", page) if i not in ids]
    read = st.setdefault("read", {})
    got = 0
    for cid in ids:
        if cid in read:
            continue
        page = get(f"{SITE}/house/session/calendars/view?CalendarId={cid}&ext=HTML")
        if not page:
            continue
        day, year, found = calendar_entries(page)
        read[cid] = day
        if not year:
            continue
        os.makedirs(os.path.join(DATA, str(year)), exist_ok=True)
        path = os.path.join(DATA, str(year), "calendar_descriptions.json")
        try:
            have = json.load(open(path))
        except (OSError, ValueError):
            have = {}
        for bill, text in found.items():
            if bill not in have or have[bill][0] <= day:
                have[bill] = [day, text]
        save(path, have)
        got += len(found)
    st["listed"] = time.time()
    save(state_path, st)
    print(f"calendars: {len(ids)} listed, {got} descriptions read now")


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
    try:
        agendas(CURRENT)
    except Exception as e:  # never holds the run
        print(f"agendas: {e}")
    try:
        calendars()
    except Exception as e:  # never holds the run
        print(f"calendars: {e}")
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
