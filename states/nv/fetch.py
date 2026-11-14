#!/usr/bin/env python3
"""Download Nevada's bills from NELIS, the Nevada Electronic Legislative Information System
(https://www.leg.state.nv.us/App/NELIS/REL/<session>/), plain server-built HTML: there is no API or bulk file, so this
reads the HTML fragments NELIS's own pages load (a bill's tabs, its vote panels, the committee list). The site's
robots.txt (checked 2026-11-08; leg.state.nv.us only redirects to www.) bars, for all user agents, */Reports/* (where
the governor's veto messages are, /Session/83rd2025/Reports/VetoMessages/...: not read), */ExhibitDocument/*,
/App/Opinions/*, /*.axd, two fiscal-note folders and a lobbyist page, none of which are read, and sets no crawl delay.
One request at a time, at most one a second (a bill's Overview takes the server about 1.7 seconds), with curl. The
site is behind Cloudflare: a challenge page, 401, 403 or 429 stops the run.

Nevada's Legislature meets in odd years only, 120 days from the first Monday of February (the 82nd session was 2023,
the 83rd 2025, the 84th 2027; bills for it are prefiled from the November before). Special sessions have their own
NELIS folders (34th2023Special, 35th2023Special, 36th2025Special) and are left out. Vetoed bills go back to the next
regular session, which may override them ("Return to 2027 Session."); a 2023 veto that the 2025 session left alone says
"No further action taken." on the 2023 bill. The lower house is the Assembly. For the next regular session (once its
bill list has bills) and the two before it, into data/nv/<year>/:
- list.json: {"session": "83rd2025", "bills": {"AB1": {"key": 11742, "summary", "title"}}, "laws": {"AB1": {"chapter":
  "60", "effective"}}, "vetoed": {"AB44": "6/5/2025"}}, from the bill lists (/HomeBill/BillsTab, one per type, every
  bill on one page: AB, SB, AJR, SJR), the list of bills that became law (/Bills/Passed/BecameLaw: the Statutes of
  Nevada chapter and effective dates; it also lists resolutions) and the vetoed list (/Bills/Vetoed). Only joint
  resolutions whose summary proposes to amend the Nevada Constitution are read further (the others are memorials:
  "Urging Congress to ..."); a joint resolution has to pass two sessions in a row, then goes to the voters.
- bills/<AB1>.html: each bill's Overview tab (/Bill/FillSelectedBillTab?selectedTab=Overview&billKey=<key>, scripts
  removed): the summary ("Voids certain regulations ... (BDR S-299)"), introduction date, fiscal note flags, primary
  sponsors and co-sponsors (members, by their legislator pages, or a committee: "Assembly Committee on Government
  Affairs"), the title and the Legislative Counsel's Digest (the plain account of existing law and what the bill
  changes: "What it does"), the most recent action, the committee hearings (committee, date, recommendation: "Do
  pass", "Amend, and do pass as amended", "Heard, No Action"), the final passage votes (house, version, date, tally),
  conference committees, the bill text versions and the full history (date, action: "Read third time. Passed. Title
  approved. (Yeas: 35, Nays: 7.) To Senate.", "Approved by the Governor.Chapter 60.", "Vetoed by the Governor.").
- votes/<AB1>.json: every recorded vote member by member: {"read": day, "types": [{"id": 3, "name": "Final
  Passage"}], "votes": [{"key", "type", "house" ("Assembly (As Introduced)"), "result" ("Passed"), "rule" ("Yes
  (Constitutional Majority)"), "date", "counts": {"All", "Yea", "Nay", "Excused", "NotVoting", "Absent"}, "members":
  [["Anderson, Natha", "Yea"], ...], "short": true when the list has fewer names than "All"}]}. From the Votes tab
  (one link per kind of vote), /Bill/GetBillVotes (each vote's house, result and counts) and
  /Bill/GetBillVoteMembers?voteResultPanel=All (every member's vote). Read only for bills whose history shows a
  recorded vote ("Yeas"), and again when those history lines change. Committee votes aren't in NELIS (only in the
  minutes, PDFs): the hearings' recommendations are all there is.
- committees.html (/HomeCommittee/LoadCommitteeListTab: the Assembly's and Senate's standing committees with their
  codes and regular meeting times, then subcommittees) and committees/<key>.html (each standing committee's Overview
  tab: members, "- Chair", "- Vice Chair", each linked to a legislator page by house and district, and staff);
  committees.json is what this script reads from them: [{"key", "house", "name", "code", "members": [{"name", "role",
  "house", "district"}]}]. Ways and Means' and Finance's budget subcommittees aren't read. The next session's
  committees are listed only once it organizes (none in November 2026; prefiled bills' committee sponsors are then
  links without a name).
- members/assembly.html and senate.html (www.leg.state.nv.us/App/Legislator/A/<Assembly|Senate>/<session>: 42 and 21
  members with party, district and county, and whether each is still serving) and members/<A01>.html, <S05>.html (each
  member's page, by house and district: post ("Speaker Pro Tempore"), party, district, county, Carson City office and
  phone, Las Vegas office, committees serving); members.json: [{"house", "district", "name" ("Monroe-Moreno,
  Daniele"), "post", "party", "county", "status" ("Currently Serving", or "Served in the Nevada Assembly 2023-2025.
  Resigned October 6, 2025."), "page" ("" for a member who left: the list links only a biography PDF, "bio"), "full"
  ("Daniele Monroe-Moreno"), "carson_office", "carson_phone", "las_vegas_office", "committees"}]. The pages' email
  addresses are hidden by Cloudflare's email obfuscation (a script decodes them in the browser): not decoded, and left
  out of the saved pages. A district's page shows its member at the end of the session. Read once for a past session,
  weekly for the newest one with members. The next session's list (members-elect, from November) has the rooms,
  Carson City phone and term in its second line ("term_ends", read into the same fields), and its new members' pages
  answer 500 until the session is set up: those are tried once a run and kept when they fail.
- state.json: each bill's Overview fingerprint ("stamps"), the day it was read ("read") and a fingerprint of its
  history's vote lines ("sigs"; "" when it has none), the fingerprint each bill's votes were read for ("votes"), when
  the lists, committees and members were read, and "finished" once a session no longer changes (two years after it,
  when its vetoes' return to the next session is over).

What's read again: while a session is live (until August 1 of its year), every bill's Overview once a day during the
session (February to mid-June) and weekly otherwise, oldest first, at most REFRESH_MAX a run (the bill lists carry no
status or date, so there is nothing cheaper that shows which bills changed); the laws and vetoed lists every run. From
August 1 until the next session's August 1, only the vetoed bills, weekly. Each run reads the lists, Overviews,
members and committees first, the newest session first, and then the votes. A first copy of three sessions (about
2,250 bills, 70 minutes; then votes for about 1,350 bills, four or five requests each, about an hour and a half)
builds up over several runs. Out of session a run reads the next session's lists and its prefiled bills weekly, and the last
session's vetoed bills weekly: a few minutes. During a session, about 1,200 Overviews a day (spread over the runs)
plus the votes of bills that had one.

Not downloaded: bill texts, amendments, fiscal notes, exhibits, committee minutes and agendas (PDFs or other pages);
the veto messages (under /Reports/, which robots.txt bars); the Histories (PDFs); members' email addresses (above).

data/nv/incomplete says "running" during the first copy, then lists what was never downloaded (a session's bill list,
a listed bill's Overview, a session's members); it is removed when nothing is missing. Votes and committees fill in on
later runs and don't hold the state back. A request that fails where a last copy exists keeps that copy and doesn't
count.
Usage: python3 states/nv/fetch.py [year]   (default: every session above; a single year leaves the marker alone)
"""
import hashlib, html, json, os, re, subprocess, sys, tempfile, time
from collections import Counter
from datetime import date, datetime, timedelta

SITE = "https://www.leg.state.nv.us"
DATA = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "nv"))
AGENT = "statebilltracker.org (a nonprofit bill tracker; contact via github.com/judithhubbard)"
TODAY = date.today()
ONLY = int(sys.argv[1]) if len(sys.argv) > 1 else None
DELAY = 1.0  # seconds between the starts of two requests
TIMEOUT = 90  # seconds for a whole request
TYPES = ("AB", "SB", "AJR", "SJR")
AMENDS = re.compile(r"\bamend the (Nevada )?Constitution|Constitution of the State of Nevada", re.I)
REFRESH_MAX = 300  # bills read again per run for being stale (runs are two hours apart on GitHub)
WEEKLY = 7
MARKER = os.path.join(DATA, "incomplete")

# The run's own time limit (FETCH_MINUTES, set by the workflow): stop a few minutes early, with everything read so far
# saved and a summary printed, rather than be cut off silently mid-request.
START = time.time()
BUDGET = max(0.0, float(os.environ.get("FETCH_MINUTES") or 0) - 5) * 60
FAILS = Counter()  # why requests failed, for the summary
STATS = Counter()
LAST = [0.0]  # when the last request started


class Refused(Exception):
    """The server turned us away (401/403/429, or a Cloudflare challenge): stop the run."""


def out_of_time():
    return BUDGET and time.time() - START > BUDGET


def request(path, label, must=None, tries=3):
    """The page at SITE + path as text, or None after three tries; None at once for a 404. must is a piece of text the
    page has to contain (else it's counted as a failure: an error page served as 200)."""
    for attempt in range(tries):
        if out_of_time():
            return None
        wait = LAST[0] + DELAY - time.time()
        if wait > 0:
            time.sleep(wait)
        LAST[0] = time.time()
        STATS["requests"] += 1
        if STATS["requests"] % 100 == 0:
            print(f"  {STATS['requests']} requests, {round((time.time() - START) / 60)} min"
                  + (f"; failures {dict(FAILS)}" if FAILS else ""), flush=True)
        try:
            code, text = curl(SITE + path)
            if "cf-chl" in text or "<title>Just a moment" in text:
                raise Refused(f"{label}: a Cloudflare challenge page")
            if code in (401, 403, 429):
                FAILS[f"HTTP {code}"] += 1
                raise Refused(f"{label}: HTTP {code}")
            if code == 404:
                FAILS["HTTP 404"] += 1
                return None
            if code != 200:
                FAILS[f"HTTP {code}"] += 1
            elif must and must not in text:
                FAILS["unexpected page"] += 1
            else:
                return text
        except Refused:
            raise
        except Exception as e:
            FAILS[type(e).__name__] += 1
        if attempt + 1 < tries:
            time.sleep(5 * (attempt + 1))
    print(f"{label}: failed" + (" three times" if tries == 3 else ""), flush=True)
    return None


def curl(url):
    """(HTTP status, body text). With curl, not Python's client: a request through urllib once hung for 20 minutes
    past its socket timeout (2026-11-08), where curl's -m limits the whole transfer."""
    with tempfile.NamedTemporaryFile(dir=DATA, suffix=".part", delete=False) as tmp:
        part = tmp.name
    try:
        r = subprocess.run(["curl", "-s", "-S", "--compressed", "-m", str(TIMEOUT), "-A", AGENT, "-o", part,
                            "-w", "%{http_code}", url], capture_output=True, text=True, timeout=TIMEOUT + 30)
        if r.returncode:
            raise OSError(f"curl exit {r.returncode}")
        with open(part, encoding="utf-8", errors="replace") as f:
            return int(r.stdout.strip() or 0), f.read()
    finally:
        os.remove(part)


def strip_scripts(page):
    page = re.sub(r"<script\b.*?</script>|<style\b.*?</style>", "", page, flags=re.S)
    # Cloudflare's obfuscated email addresses: left out, not decoded.
    page = re.sub(r'<a href="/cdn-cgi/l/email-protection[^"]*">.*?</a>', "", page, flags=re.S)
    return re.sub(r"\n\s*\n+", "\n", page)


def text(fragment):
    t = re.sub(r"<br\s*/?>", "\n", fragment)
    t = html.unescape(re.sub(r"<[^>]+>", " ", t)).replace("\xa0", " ")
    return "\n".join(re.sub(r"[ \t]+", " ", line).strip() for line in t.split("\n")).strip()


def flat(fragment):
    return re.sub(r"\s+", " ", text(fragment)).strip()


def save_text(body, path):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(body)
    os.replace(tmp, path)


def save(obj, path):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=0)
    os.replace(tmp, path)


def load(path, default=None):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def session_name(year):
    """NELIS's name for a regular session: 2025 -> "83rd2025"."""
    n = 83 + (year - 2025) // 2
    suffix = "th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}{year}"


def years():
    """The next (or current) regular session and the two before it, newest first."""
    latest = TODAY.year if TODAY.year % 2 else TODAY.year + 1
    return [latest, latest - 2, latest - 4]


def live(year):
    """Bills can still change in ways the lists don't show: until August 1 of the session's year."""
    return TODAY < date(year, 8, 1)


def in_session(year):
    return date(year, 2, 1) <= TODAY <= date(year, 6, 15)


def returned_until(year):
    """Vetoed bills go back to the next regular session: they can change until its August 1."""
    return date(year + 2, 8, 1)


def ago(days):
    return (TODAY - timedelta(days=days)).isoformat()


# ---- lists ----

def parse_bill_list(page, sess):
    out = {}
    for m in re.finditer(rf'<a id="([A-Z]+\d+)" href="/App/NELIS/REL/{sess}/Bill/(\d+)/Overview">.*?</a>\s*</div>\s*'
                         r'<div class="col[^"]*">(.*?)</div>\s*</div>\s*<hr', page, re.S):
        body = m.group(3)
        title = ""
        t = re.search(r'<span class="font-weight-bold">Title:</span>(.*?)</div>', body, re.S)
        if t:
            title = flat(t.group(1))
            body = body[:t.start()]
        out[m.group(1)] = {"key": int(m.group(2)), "summary": flat(body), "title": title}
    return out


def parse_laws(page, sess):
    out = {}
    for row in page.split('<div class="row px-md-3">')[1:]:
        link = re.search(rf'/App/NELIS/REL/{sess}/Bill/\d+/Overview">([A-Z]+\d+)</a>', row)
        chapter = re.search(r"Chapter\s*(\d+)", row)
        if link:
            cols = re.findall(r'<div class="col-md-2[^"]*">(.*?)</div>', row, re.S)
            out[link.group(1)] = {"chapter": chapter.group(1) if chapter else "",
                                  "effective": flat(cols[-1]) if cols else ""}
    return out


def parse_vetoed(page, sess):
    out = {}
    for row in page.split('<div class="row px-md-3">')[1:]:
        link = re.search(rf'/App/NELIS/REL/{sess}/Bill/\d+/Overview">([A-Z]+\d+)</a>', row)
        when = re.search(r"Vetoed\s+(\d+/\d+/\d{4})", row)
        if link:
            out[link.group(1)] = when.group(1) if when else ""
    return out


def lists(year, folder, state):
    """The year's bill list (read every run while live, else once), laws and vetoed lists. Returns the list or None."""
    sess = session_name(year)
    path = os.path.join(folder, "list.json")
    last = load(path)
    if last and not live(year) and state.get("lists", "") >= date(year, 8, 1).isoformat():
        return last  # after the session the lists don't change
    bills, ok = {}, True
    for kind in TYPES:
        page = request(f"/App/NELIS/REL/{sess}/HomeBill/BillsTab?Page=1&Filters.DisplayTitles=True"
                       f"&Filters.PageSize=2147483647&SelectedBillTypes={kind}", f"{year} {kind} list", 'id="billTab"')
        if page is None:
            ok = False
            continue
        bills.update(parse_bill_list(page, sess))
    if not ok or not bills:
        if last:
            print(f"{year}: bill list unreadable; kept the last copy", flush=True)
            return last
        if ok:
            print(f"{year}: no bills listed yet", flush=True)
        return None
    out = {"session": sess, "bills": bills, "laws": (last or {}).get("laws", {}), "vetoed": (last or {}).get("vetoed", {})}
    page = request(f"/App/NELIS/REL/{sess}/Bills/Passed/BecameLaw", f"{year} laws", "</html>")
    if page is not None:
        out["laws"] = parse_laws(page, sess)
    page = request(f"/App/NELIS/REL/{sess}/Bills/Vetoed", f"{year} vetoed", "</html>")
    if page is not None:
        out["vetoed"] = parse_vetoed(page, sess)
    os.makedirs(os.path.join(folder, "bills"), exist_ok=True)
    save(out, path)
    state["lists"] = TODAY.isoformat()
    return out


def wanted(listing):
    """Bills and the joint resolutions proposing constitutional amendments."""
    return {k: b for k, b in listing["bills"].items()
            if k.startswith(("AB", "SB")) or AMENDS.search(b["summary"] + " " + b["title"])}


# ---- bills ----

def vote_lines(page):
    """The history's recorded votes and veto steps: when they change, the bill's votes are read again."""
    lines = re.findall(r"\(Yeas:[^)]*\)|[^.>]*[Vv]eto[^.<]*", page)
    return hashlib.sha1("|".join(re.sub(r"\s+", " ", x) for x in lines).encode()).hexdigest()[:16] \
        if any("Yeas" in x for x in lines) else ""


def overviews(year, folder, state, listing):
    sess = session_name(year)
    stamps, read = state.setdefault("stamps", {}), state.setdefault("read", {})
    bills = wanted(listing)
    have = lambda k: os.path.exists(os.path.join(folder, "bills", f"{k}.html"))
    todo = [k for k in bills if not have(k) or k not in read]  # (or saved by a run cut off before its state was)
    if live(year):
        stale = ago(1 if in_session(year) else WEEKLY)
        pool = list(bills)
    elif TODAY < returned_until(year):
        stale, pool = ago(WEEKLY), [k for k in bills if k in listing.get("vetoed", {})]
    else:
        stale, pool = returned_until(year).isoformat(), [k for k in bills if k in listing.get("vetoed", {})]
        # After that, a last read of the vetoed bills, then nothing.
    old = sorted((read.get(k, ""), k) for k in pool if k not in todo and read.get(k, "") < stale)
    todo += [k for _, k in old[:REFRESH_MAX]]
    print(f"{year} ({sess}): {len(bills)} bills and amendments listed ({len(listing['laws'])} laws incl. resolutions, "
          f"{len(listing['vetoed'])} vetoed); {len(todo)} to read", flush=True)
    got = 0
    for k in todo:
        if out_of_time():
            break
        page = request(f"/App/NELIS/REL/{sess}/Bill/FillSelectedBillTab?selectedTab=Overview&billKey={bills[k]['key']}",
                       f"{year} {k}", "Bill History")
        if page is None:
            continue  # the last copy stays, and it's asked again next run
        page = strip_scripts(page)
        save_text(page, os.path.join(folder, "bills", f"{k}.html"))
        stamps[k], read[k] = hashlib.sha1(page.encode()).hexdigest()[:16], TODAY.isoformat()
        state.setdefault("sigs", {})[k] = vote_lines(page)
        got += 1
        STATS["bills"] += 1
        if got % 25 == 0:
            save(state, os.path.join(folder, "state.json"))
    print(f"{year} bills: {got} of {len(todo)} read", flush=True)


def parse_votes(page):
    """The votes on one GetBillVotes panel: [{key, house, result, rule, date, counts}]."""
    out = []
    heads = [(m.start(), flat(m.group(1))) for m in re.finditer(r'<h2 class="h4">(.*?)</h2>', page, re.S)]
    blocks = list(re.finditer(r'id="billVoteTitleForVoteKey (\d+)"', page))
    for i, m in enumerate(blocks):
        end = blocks[i + 1].start() if i + 1 < len(blocks) else len(page)
        block = page[m.start():end]
        house = next((h for at, h in reversed(heads) if at < m.start()), "")
        res = re.search(r"<li[^>]*>\s*<span>(.*?)</span>\s*<span>(.*?)</span>", block, re.S)
        when = re.search(r"Date\s*<span>(.*?)</span>", block, re.S)
        day = ""
        if when:
            try:
                day = datetime.strptime(flat(when.group(1)), "%A, %B %d, %Y").date().isoformat()
            except ValueError:
                day = flat(when.group(1))
        counts = {p: int(n) for p, n in re.findall(r'voteResultPanel=(\w+)">[^<:]*:\s*(\d+)', block)}
        out.append({"key": int(m.group(1)), "house": house, "result": flat(res.group(1)) if res else "",
                    "rule": re.sub(r"\s+", " ", flat(res.group(2))) if res else "", "date": day, "counts": counts})
    return out


def parse_members(page):
    out = []
    for m in re.finditer(r'<div class="vote-\w+ vote[^"]*">(.*?)</div>', page, re.S):
        t = flat(m.group(1))
        v = re.match(r"(.*?)\s*\(\s*([^()]*?)\s*\)\s*$", t)
        if v:
            out.append([v.group(1), v.group(2)])
        elif t:
            out.append([t, ""])
    return out


def bill_votes(year, folder, k, key):
    """All of a bill's votes, member by member, or None when a request failed (the last copy stays)."""
    sess = session_name(year)
    tab = request(f"/App/NELIS/REL/{sess}/Bill/FillSelectedBillTab?selectedTab=Votes&billKey={key}",
                  f"{year} {k} votes", "Bill.Votes.init")  # also on "No Votes Recorded"
    if tab is None:
        return None
    types = [{"id": int(t), "name": flat(n)}
             for t, n in re.findall(rf"GetBillVotes\?billKey={key}&amp;voteTypeId=(\d+)\">(.*?)</a>", tab, re.S)]
    votes = []
    for t in types:
        page = request(f"/App/NELIS/REL/{sess}/Bill/GetBillVotes?billKey={key}&voteTypeId={t['id']}",
                       f"{year} {k} {t['name']}", "billVoteWidget")
        if page is None:
            return None
        for v in parse_votes(page):
            v["type"] = t["name"]
            people = request(f"/App/NELIS/REL/{sess}/Bill/GetBillVoteMembers?voteKey={v['key']}&voteResultPanel=All",
                             f"{year} {k} vote {v['key']}")
            if people is None:
                return None
            v["members"] = parse_members(people)
            if len(v["members"]) != v["counts"].get("All", len(v["members"])):
                v["short"] = True
                FAILS["vote list not matching its count"] += 1
            votes.append(v)
            STATS["votes"] += 1
    return {"read": TODAY.isoformat(), "types": types, "votes": votes}


def votes(year, folder, state, listing):
    """Votes for bills whose history shows a recorded vote, read again when those lines change."""
    done = state.setdefault("votes", {})
    os.makedirs(os.path.join(folder, "votes"), exist_ok=True)
    sigs = state.get("sigs", {})
    todo = [(k, b["key"], sigs[k]) for k, b in wanted(listing).items() if sigs.get(k) and done.get(k) != sigs[k]]
    if not todo:
        return
    print(f"{year}: votes to read for {len(todo)} bills", flush=True)
    got = 0
    for k, key, sig in todo:
        if out_of_time():
            break
        out = bill_votes(year, folder, k, key)
        if out is None:
            continue
        save(out, os.path.join(folder, "votes", f"{k}.json"))
        done[k] = sig
        got += 1
        if got % 25 == 0:
            save(state, os.path.join(folder, "state.json"))
    print(f"{year} votes: {got} of {len(todo)} bills read", flush=True)


# ---- committees ----

def parse_committee_list(page, sess):
    """The standing committees on the committee list: [{key, house, name, code}]. Each house's card lists its
    committees (a link inside a <div>), with a committee's subcommittees (bare links) after it."""
    found = []
    for card in re.split(r'<h2 class="card-header h3">', page)[1:]:
        title = flat(card.split("</h2>")[0])
        house = "Assembly" if title.startswith("Assembly") else "Senate" if title.startswith("Senate") else title
        for m in re.finditer(rf'<div>\s*<a href="/App/NELIS/REL/{sess}/Committee/(\d+)/Overview">(.*?)</a>', card, re.S):
            name = flat(m.group(2))
            code = re.search(r"\(([A-Z]+)\)$", name)
            found.append({"key": int(m.group(1)), "house": house, "name": re.sub(r"\s*\([A-Z]+\)$", "", name),
                          "code": code.group(1) if code else ""})
    return found


def parse_committee(tab):
    """A committee's members from its Overview tab: [{name, role, house, district}]; a member who left has no link."""
    members = []
    part = tab.split(">Staff<")[0]
    for li in re.findall(r"<li\b[^>]*>(.*?)</li>", part, re.S):
        t = flat(li)
        if not t:
            continue
        name, _, role = t.partition(" - ")
        link = re.search(r'/App/Legislator/A/(Assembly|Senate)/[^/"]+/(\d+)"', li)
        members.append({"name": name.strip(), "role": role.strip(), "house": link.group(1) if link else "",
                        "district": int(link.group(2)) if link else None})
    return members


def committees(year, folder, state):
    """The standing committees and their members: once for a past session, weekly while live."""
    last = state.get("committees") or ""
    if last and (not live(year) or last >= ago(WEEKLY)):
        return
    sess = session_name(year)
    page = request(f"/App/NELIS/REL/{sess}/HomeCommittee/LoadCommitteeListTab", f"{year} committee list",
                   "committee-cards")
    if page is None:
        print(f"{year} committees: no list; kept the last copies", flush=True)
        return
    page = strip_scripts(page)
    found = parse_committee_list(page, sess)
    if not found:
        print(f"{year} committees: none found in the list; kept the last copies", flush=True)
        return
    out = os.path.join(folder, "committees")
    os.makedirs(out, exist_ok=True)
    save_text(page, os.path.join(folder, "committees.html"))
    got = 0
    for c in found:
        if out_of_time():
            return
        tab = request(f"/App/NELIS/REL/{sess}/Committee/FillSelectedCommitteeTab?selectedTab=Overview"
                      f"&committeeOrSubCommitteeKey={c['key']}", f"{year} committee {c['name']}", "Members")
        if tab is None:
            continue
        tab = strip_scripts(tab)
        save_text(tab, os.path.join(out, f"{c['key']}.html"))
        members = parse_committee(tab)
        c["members"] = members
        got += 1
    save(found, os.path.join(folder, "committees.json"))
    print(f"{year} committees: {got} of {len(found)} read", flush=True)
    if got == len(found):
        state["committees"] = TODAY.isoformat()


# ---- members ----

def parse_member_list(page, house, sess):
    """The list's rows. A member who left has no page, only a biography PDF and a line saying so ("Served in the
    Nevada Assembly 2023-2025. Resigned October 6, 2025.")."""
    out = []
    for row in re.findall(r'<tr class="thisRow listRow[^"]*">(.*?)</tr>\s*(?:<tr class="thisRow">(.*?)</tr>)?', page, re.S):
        cells = re.findall(r"<td\b[^>]*>(.*?)</td>", row[0], re.S)
        district = re.search(r"No\.\s*(\d+)", flat(cells[3])) if len(cells) >= 5 else None
        if not district:
            continue
        link = re.search(rf'href="(/App/Legislator/A/{house}/{sess}/\d+)"', row[0])
        bio = re.search(r'href="(/Session/Legislator/[^"]+\.pdf)"', row[0])
        who = text(cells[1]).split("\n")
        m = {"house": house, "district": int(district.group(1)), "name": who[0].strip(),
             "post": " ".join(x.strip() for x in who[1:] if x.strip()), "party": flat(cells[2]),
             "county": flat(cells[4]), "status": flat(row[1] or ""),
             "page": link.group(1) if link else "", "bio": bio.group(1) if bio else ""}
        # Before a session the list's second line has the contact fields instead ("Term Ends: 2028 Email: [email
        # protected] Carson City Room: 3158 Las Vegas Room: 341 Carson City Phone: (775) 684-8841").
        fields = re.findall(r"(Term Ends|Carson City Room|Las Vegas Room|Carson City Phone|Las Vegas Phone):\s*"
                            r"(.*?)(?=\s*(?:Term Ends|Email|Carson City Room|Las Vegas Room|Carson City Phone|"
                            r"Las Vegas Phone):|$)", m["status"])
        if fields:
            names = {"Term Ends": "term_ends", "Carson City Room": "carson_office", "Las Vegas Room": "las_vegas_office",
                     "Carson City Phone": "carson_phone", "Las Vegas Phone": "las_vegas_phone"}
            m.update({names[k]: v.strip() for k, v in fields})
            m["status"] = ""
        out.append(m)
    return out


def parse_member_page(page):
    info = {}
    h = re.search(r"<h3>(.*?)</h3>", page, re.S)
    if h:
        info["full"] = re.sub(r"^(Assemblymember|Assemblyman|Assemblywoman|Senator)\s+", "", flat(h.group(1)))
    contact = re.search(r'id="contactInfo".*?</div>\s*</div>', page, re.S)
    if contact:
        place = ""
        for line in text(contact.group(0)).split("\n"):
            line = line.strip()
            if line.endswith("Contact") and line != "Contact":
                place = "carson" if line.startswith("Carson") else "las_vegas" if line.startswith("Las Vegas") \
                    else re.sub(r"\W+", "_", line[:-8].strip().lower())
            elif ":" in line and place:
                label, value = (x.strip() for x in line.split(":", 1))
                key = {"Office": "office", "Phone": "phone", "Fax": "fax", "Cell": "cell"}.get(label, label.lower())
                info[f"{place}_{key}"] = value
    comms = re.search(r"<h2>Committees Serving</h2>.*?<ul[^>]*>(.*?)</ul>", page, re.S)
    if comms:
        info["committees"] = [flat(x) for x in re.findall(r"<li>(.*?)</li>", comms.group(1), re.S)]
    return info


def members(year, folder, state, newest):
    """Each house's member list and every member's page: weekly for the newest session with members, else once."""
    last = state.get("members") or ""
    if last and (not newest or last >= ago(WEEKLY)):
        return True
    sess = session_name(year)
    out_dir = os.path.join(folder, "members")
    path = os.path.join(out_dir, "members.json")
    found, ok = [], True
    for house in ("Assembly", "Senate"):
        page = request(f"/App/Legislator/A/{house}/{sess}", f"{year} {house} members", "<table")
        rows = parse_member_list(page or "", house, sess)
        if not rows:
            ok = False
            continue
        os.makedirs(out_dir, exist_ok=True)
        save_text(strip_scripts(page), os.path.join(out_dir, f"{house.lower()}.html"))
        found += rows
    if not found:
        return os.path.exists(path)
    seen, got = {}, 0
    for m in found:
        if m["page"]:
            seen.setdefault(m["page"], m)
    for page_path, m in seen.items():
        if out_of_time():
            return os.path.exists(path)
        name = f"{m['house'][0]}{m['district']:02d}"
        # Members-elect's pages answer 500 until the session's records are set up: one try, asked again next week.
        page = request(page_path, f"{year} {name}", "contactInfo", tries=1)
        if page is None:
            continue
        page = strip_scripts(page)
        save_text(page, os.path.join(out_dir, f"{name}.html"))
        got += 1
    for m in found:
        if not m["page"]:
            continue  # a member who left: only the list's line
        try:
            with open(os.path.join(out_dir, f"{m['house'][0]}{m['district']:02d}.html"), encoding="utf-8") as f:
                m.update(parse_member_page(f.read()))
        except OSError:
            pass
    save({"read": TODAY.isoformat(), "members": found}, path)
    print(f"{year} members: {sum(m['house'] == 'Assembly' for m in found)} Assembly, "
          f"{sum(m['house'] == 'Senate' for m in found)} Senate; {got} of {len(seen)} pages read", flush=True)
    if ok:
        state["members"] = TODAY.isoformat()
    return True


# ---- the run ----

def finished(year, state, listing):
    """A session no longer changes once its vetoes' return to the next session is over: every bill read after its
    session, the vetoed ones after that, every recorded vote read, the committees and members."""
    if live(year) or TODAY < returned_until(year) or not listing:
        return False
    read, sigs, done = state.get("read", {}), state.get("sigs", {}), state.get("votes", {})
    after, returned = date(year, 8, 1).isoformat(), returned_until(year).isoformat()
    vetoed = listing.get("vetoed", {})
    return all(read.get(k, "") >= (returned if k in vetoed else after) and done.get(k, "") == sigs.get(k, "")
               for k in wanted(listing)) and bool(state.get("committees")) and bool(state.get("members"))


def begun(year):
    """Whether a session has convened (the first Monday of February). Its prefiled bills, listed from November, are read
    when they're there but never hold Nevada off the site before then."""
    return TODAY >= date(year, 2, 1 + (0 - date(year, 2, 1).weekday()) % 7)


def never_downloaded(yrs):
    """What was never downloaded: a session's bill list (once the session exists), a listed bill's Overview, a
    session's members. (A failed refresh with a last copy doesn't count.)"""
    out = []
    for year in yrs:
        if not begun(year):
            continue
        folder = os.path.join(DATA, str(year))
        listing = load(os.path.join(folder, "list.json"))
        if not listing:
            if year < TODAY.year:
                out.append(f"{year}:list")
            continue
        if any(not os.path.exists(os.path.join(folder, "bills", f"{k}.html")) for k in wanted(listing)):
            out.append(f"{year}:bills")
        if year < TODAY.year and not os.path.exists(os.path.join(folder, "members", "members.json")):
            out.append(f"{year}:members")
    return out


def main():
    os.makedirs(DATA, exist_ok=True)
    # Before the first copy, a run cut off without its summary leaves this, so a partial copy isn't published.
    if not ONLY and not any(name.isdigit() for name in os.listdir(DATA)):
        with open(MARKER, "w") as f:
            f.write("running\n")
    yrs = [ONLY] if ONLY else years()
    refused = False
    found = {}
    try:
        newest_members = True
        # Lists, bills, members and committees first, the newest session first; then votes.
        for year in yrs:
            if out_of_time():
                break
            if TODAY < date(year - 1, 11, 1):
                continue  # nothing prefiled yet
            folder = os.path.join(DATA, str(year))
            os.makedirs(folder, exist_ok=True)
            state_path = os.path.join(folder, "state.json")
            state = load(state_path, {})
            if state.get("finished"):
                print(f"{year}: finished and fully read; nothing to do", flush=True)
                continue
            listing = lists(year, folder, state)
            save(state, state_path)
            if not listing:
                continue
            found[year] = (folder, state, listing)
            overviews(year, folder, state, listing)
            save(state, state_path)
            if members(year, folder, state, newest_members) and os.path.exists(
                    os.path.join(folder, "members", "members.json")):
                newest_members = False
            save(state, state_path)
            if not out_of_time():
                committees(year, folder, state)
            save(state, state_path)
        for year, (folder, state, listing) in found.items():
            if out_of_time():
                break
            votes(year, folder, state, listing)
            if not out_of_time() and finished(year, state, listing):
                state["finished"] = True
                print(f"{year}: finished", flush=True)
            save(state, os.path.join(folder, "state.json"))
    except Refused as e:
        print(f"Stopped: the server refused a request ({e})", flush=True)
        refused = True
        for year, (folder, state, listing) in found.items():
            save(state, os.path.join(folder, "state.json"))
    missing = never_downloaded(yrs)
    print(f"run: {STATS['requests']} requests ({STATS['bills']} bills, {STATS['votes']} votes), "
          f"{round((time.time() - START) / 60)} min"
          + ("; stopped at the time limit" if out_of_time() else "")
          + ("; refused" if refused else "")
          + (f"; request failures {dict(FAILS)}" if FAILS else "; no request failures")
          + (f"; never downloaded: {' '.join(missing)}" if missing else "; nothing missing"), flush=True)
    if ONLY:
        return
    # Left while data that was never downloaded is missing, so a partial first copy isn't published.
    if missing:
        with open(MARKER, "w") as f:
            f.write(" ".join(missing) + "\n")
    elif os.path.exists(MARKER):
        os.remove(MARKER)


if __name__ == "__main__":
    main()
