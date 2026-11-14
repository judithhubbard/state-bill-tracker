#!/usr/bin/env python3
"""Download Iowa's bills from the Legislature's website, www.legis.iowa.gov (server-built HTML pages, PDFs and the bill
texts as HTML; there is no API, bulk file or change feed). Its robots.txt (checked 2026-11-13) bars only /chambers/,
for all user agents, and sets no crawl delay: nothing under /chambers/ is read (the journals' index pages are there,
and the leadership pages, so leaders aren't downloaded; the journal PDFs themselves are under /docs/ and aren't needed,
since each floor roll call has its own PDF). One request at a time, DELAY (6) seconds apart, counted from the end of
the last answer. The site (behind a FortiWeb firewall: the "cookiesession1" cookie) answers now and then with a script
challenge instead of the page (a page that only runs JavaScript): on 2026-11-13 once during a few dozen requests by
hand, and once in the first run, after 345 requests in 10 minutes at a request a second (hence the slower pace, the
owner's choice). That challenge, a 401, 403 or 429 ends the run at once: everything read so far is saved, the page
isn't asked again in that run, and the summary says "stopped at the site's bot check after N requests"; the next run
carries on from there. It isn't worked around (same User-Agent, no browser emulation). Whether the Legislature will
allow this download hasn't been asked (webmaster@legis.iowa.gov).

Iowa's General Assembly sits for two years (the 91st is 2025-26, the 90th 2023-24), a session each year from the second
Monday of January to April or May; bills carry over from the first session to the second. Special sessions' bills are
numbered with the regular ones. For the General Assembly before this one, this one, and (from November of an even year)
the next one once its prefiled bills are listed, into data/ia/<first year>/ (2025 for the 91st):
- lists/disposition_H.html and disposition_S.html (/legislation/billTracking/billDisposition?ga=91&chamberID=H, the
  table only) and list.json, read from them: {"ga": 91, "bills": {"HF100": {"last": "Introduced, referred to
  Transportation. H.J. 109.", "date": "2025-01-22"}}}. "Disposition of Bills" lists every bill, study bill and
  resolution of each house with its last action; that is the change signal. Read every run for the current General
  Assembly (two requests), weekly for a finished one.
- bills/<HF100>.html: each bill's history (/legislation/billTracking/billHistory?billName=HF%20100&ga=91, the content
  section only): status ("Status: Signed by Governor"), floor managers, the LSB number and the study bill it came from
  ("HSB785"), companion ("(C) SF2508"), sponsors ("By Meggers", "By COMMITTEE ON WAYS AND MEANS"), title, then every
  action with its date and journal page ("Introduced, referred to Transportation. H.J. 109.", "Subcommittee: Meggers,
  Bagniewski and Young.", "Passed House, yeas 75, nays 17.", "Signed by Governor.", "Fiscal note."). The lines aren't
  always in date order (they're in journal order). Read for every House File, Senate File and House and Senate Joint
  Resolution (HF, SF, HJR, SJR: Iowa's constitutional amendments are joint resolutions, which pass two General
  Assemblies and go to the voters, never the governor; the converter tells them from the others by title). Read again
  when the bill's last action changes; during January to June also any not read for a week (subcommittee steps don't
  always change the last action), the most recently active first, at most REFRESH_MAX a run.
- study/<HSB1>.html: the same history for each House and Senate study bill (HSB, SSB): a committee's draft, which
  becomes a numbered bill when the committee approves it ("Committee report approving bill, renumbered as SF 149.";
  the new bill's history says "Formerly HSB 785"). Read after everything else, and they don't hold the state back.
  Whether the site shows them is undecided.
- texts/<HF100>.json: the Legislative Services Agency's explanation from the bill as introduced
  (/docs/publications/LGI/91/attachments/HF100.html, the text as positioned HTML; LGR is the reprinted version, LGE
  the enrolled one, which carry no explanation): {"read", "by" (the "BY MEGGERS" lines), "explanation" (paragraphs
  separated by blank lines, page headers and line numbers removed)}. Read once per bill (the introduced text doesn't
  change); a bill whose text answers 404 is asked again a week later. "What it does".
- enrolled_<year>.json: the enrolled bills of each year (/law/statutory/acts/enrolledBills?year=2025): bill, title,
  date passed, the governor's signature date, effective date. Read when missing, weekly while the General Assembly is
  current; for checking totals.
- votes/list_<year>.json and votes/<year>/<S16037>.txt: every floor vote on a bill (/legislation/findLegislation/
  floorVotes?ga=91&session=1: bill, chamber, date, tallies, the substituted bill, and the roll call's id), and each roll
  call's PDF (?action=result&calendarItemID=16037&useFile=true&chamberID=S: "RECORD ROLL CALL", the yeas, nays,
  present, absent or not voting and excused by surname, as text by pdftotext -layout), read once. These are the final
  passage votes (and votes on bills substituted for the other house's companion); amendment votes aren't read. The list
  is read every run during January to June of its year, weekly after while its General Assembly is current, and monthly
  for the one before.
- state.json: each bill's signal ("sig", its last action and date) when its history was read, the day it was read
  ("read"), bills that answer 404 ("absent"), texts read or absent, and when the lists were read.
And into data/ia/members/<first year>/: house.html and senate.html (/legislators/house?ga=91: name, district, party,
county, email; members who left show their dates of service), pages/<personID>.html (/legislators/legislator?ga=91&
personID=6174: committees with "(Chair)", "(Ranking Member)" and dates for former memberships, "Legislative Email",
"Capitol Phone" (nearly all the House's 515.281.3221 or the Senate's 515.281.3371 switchboard), home phone and address
where given), and members.json, what this script reads from them. Read weekly for the current General Assembly, once
for the one before. And data/ia/committees.json and committees/<groupID>.html: the current General Assembly's House and
Senate standing committees and the joint appropriations subcommittees (/committees, then /committees/committee?ga=91&
groupID=629: each member with party, district and "Chair", "Vice Chair" or "Ranking Member"), weekly.

A first copy (about 5,700 bill histories, 5,700 texts, 1,900 study bills and 2,400 roll calls for two General
Assemblies, plus about 450 member and committee pages) is about 16,000 requests: about 28 hours at one every 6 seconds,
so a day or two of runs (two-hour runs every two hours; fewer if the bot check cuts runs short). The histories, members
and committees come first (about 5,800 requests, 10 hours: what the marker waits for); then roll calls, texts and
study bills. After
that, out of session, a run is a few requests (the lists); during a session, the bills that moved and their votes.

Not downloaded: leaders (only under /chambers/, which robots.txt bars); fiscal notes, the governor's letters on vetoes and
item vetoes, the LSA's "Summary of Legislation" and bill versions after the first (PDFs); committee votes by member (only
in minutes); amendment votes; committee meeting agendas.

data/ia/incomplete says "running" during the first copy, then lists what was never downloaded (a General Assembly's
lists, a listed HF, SF, HJR or SJR's history, the current members or committees); it is removed when nothing is
missing. Texts, votes, study bills and the enrolled lists fill in on later runs and don't hold the state back, nor does
a General Assembly not yet begun. A request that fails where a last copy exists keeps that copy and doesn't count; a
page that answers 404 is noted and doesn't count. The roll-call PDFs need pdftotext (poppler-utils: on GitHub's Ubuntu
runner, sudo apt-get install -y poppler-utils); without it they're skipped (and asked again next run).
Usage: python3 states/ia/fetch.py [first year]   (default: every General Assembly above; one leaves the marker alone)
"""
import html, json, os, re, shutil, subprocess, sys, tempfile, time, urllib.error, urllib.parse, urllib.request
from collections import Counter
from datetime import date, datetime, timedelta, timezone

SITE = "https://www.legis.iowa.gov"
DATA = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "ia"))
AGENT = "statebilltracker.org (a nonprofit bill tracker; contact via github.com/judithhubbard)"
TODAY = date.today()
YEAR = TODAY.year
ONLY = int(sys.argv[1]) if len(sys.argv) > 1 else None
DELAY = 6.0  # seconds from the end of one answer to the next request (the site's bot check tripped at one a second)
BILLS = ("HF", "SF", "HJR", "SJR")  # read in full; their histories decide whether the state is complete
STUDY = ("HSB", "SSB")  # committees' drafts: histories only, last
REFRESH_MAX = 300  # histories re-read per run only because a week has passed (January to June)
WEEKLY = 7
MARKER = os.path.join(DATA, "incomplete")
PDFTOTEXT = shutil.which("pdftotext")

# The run's own time limit (FETCH_MINUTES, set by the workflow): stop a few minutes early, with everything read so far
# saved and a summary printed, rather than be cut off silently mid-request.
START = time.time()
BUDGET = max(0.0, float(os.environ.get("FETCH_MINUTES") or 0) - 5) * 60
FAILS = Counter()  # why requests failed, for the summary
STATS = Counter()  # what was read, for the summary
LAST = [0.0]  # when the last answer ended
CODE = [0]  # the last request's HTTP status (404: not there)


class Refused(Exception):
    """The server turned us away (401/403/429, or a script challenge instead of the page): stop the run."""


def out_of_time():
    return BUDGET and time.time() - START > BUDGET


def ga_of(year):
    """The General Assembly sitting in a year: 2025 and 2026 -> 91."""
    return (year - 1843) // 2


def first_year(ga):
    return 2 * ga + 1843


def request(url, label, must=None, binary=False):
    """The page as text (bytes if binary), or None after three tries; None at once for a 404 (CODE[0] is then 404).
    must is a piece of text the page has to contain (else it's counted as a failure: an error page served as 200)."""
    CODE[0] = 0
    for attempt in range(3):
        if out_of_time():
            return None
        wait = LAST[0] + DELAY - time.time()
        if wait > 0:
            time.sleep(wait)
        STATS["requests"] += 1
        if STATS["requests"] % 100 == 0:
            print(f"  {STATS['requests']} requests, {round((time.time() - START) / 60)} min"
                  + (f"; failures {dict(FAILS)}" if FAILS else ""), flush=True)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": AGENT})
            with urllib.request.urlopen(req, timeout=120) as r:
                body = r.read()
                length = r.headers.get("Content-Length")
            LAST[0] = time.time()
            if b"eval(function(p,a,c,k,e,d)" in body[:3000] and b"<title" not in body[:3000]:
                raise Refused(f"{label}: a script challenge instead of the page")
            if length and int(length) != len(body):
                FAILS["cut off"] += 1
            elif binary:
                if must and not body.startswith(must):
                    FAILS["unexpected file"] += 1
                else:
                    return body
            else:
                text_ = body.decode("utf-8", "replace")
                if must and must not in text_:
                    FAILS["unexpected page"] += 1
                else:
                    return text_
        except Refused:
            raise
        except urllib.error.HTTPError as e:
            LAST[0] = time.time()
            FAILS[f"HTTP {e.code}"] += 1
            if e.code in (401, 403, 429):
                raise Refused(f"{label}: HTTP {e.code}")
            if e.code == 404:
                CODE[0] = 404
                return None
        except Exception as e:
            LAST[0] = time.time()
            FAILS[type(e).__name__] += 1
        time.sleep(5 * (attempt + 1))
    print(f"{label}: failed three times", flush=True)
    return None


def save_text(body, path):
    with open(path + ".tmp", "w", encoding="utf-8") as f:
        f.write(body)
    os.replace(path + ".tmp", path)


def save(obj, path):
    with open(path + ".tmp", "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=0)
    os.replace(path + ".tmp", path)


def load(path, default=None):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def text(fragment):
    """Plain text of an HTML fragment, whitespace collapsed."""
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", fragment)).replace("\xa0", " ")).strip()


def strip(body):
    return re.sub(r"<script\b.*?</script>|<style\b.*?</style>|<input\b[^>]*>", "", body, flags=re.S)


def content(page):
    """A page's content: the #content element, without the site's menus and footer."""
    a = page.find('<div id="content">')
    b = page.find("<footer", max(a, 0))
    return strip(page[max(a, 0):b if b > 0 else len(page)])


def stale(day, days=WEEKLY):
    return not day or day < (TODAY - timedelta(days=days)).isoformat()


def iso(mdy):
    m = re.match(r"(\d\d)/(\d\d)/(\d{4})", mdy or "")
    return f"{m.group(3)}-{m.group(1)}-{m.group(2)}" if m else ""


def selected_ga(page):
    """The General Assembly a page shows (an unknown one falls back to the newest, so it has to be checked)."""
    m = re.search(r'<li class="selected nocsscolor" data-ga="(\d+)"(?: data-session="(\d+)")?', page or "")
    return (int(m.group(1)), int(m.group(2)) if m.group(2) else None) if m else (None, None)


def key_of(name):
    return re.sub(r"\s+", "", name).upper()


def pdf_text(body):
    """A PDF's text (pdftotext -layout), or None."""
    if not PDFTOTEXT or not body or not body.startswith(b"%PDF"):
        return None
    with tempfile.TemporaryDirectory() as tmp:
        src = os.path.join(tmp, "in.pdf")
        with open(src, "wb") as f:
            f.write(body)
        try:
            out = subprocess.run([PDFTOTEXT, "-layout", "-enc", "UTF-8", src, "-"], capture_output=True, timeout=120)
        except Exception:
            return None
        return out.stdout.decode("utf-8", "replace") if out.returncode == 0 else None


# ----------------------------------------------------------------------------------------------- lists and bills

def read_lists(ga, folder, state):
    """The two houses' Disposition of Bills into list.json. False when the General Assembly isn't listed yet."""
    path = os.path.join(folder, "list.json")
    live = ga >= ga_of(YEAR)
    if os.path.exists(path) and not live and not stale(state.get("listed")):
        return True
    bills = {}
    for house in ("H", "S"):
        if out_of_time():
            return os.path.exists(path)
        page = request(f"{SITE}/legislation/billTracking/billDisposition?ga={ga}&chamberID={house}",
                       f"{ga} disposition {house}", "Disposition of Bills")
        if page is None or selected_ga(page)[0] != ga:
            if page is not None and not os.path.exists(path):
                print(f"{ga}: not listed yet", flush=True)
                return False
            print(f"{ga} disposition {house}: unreadable; kept the last copy", flush=True)
            return os.path.exists(path)
        a = page.find('<table class="standard divideVert sortable"')
        b = page.find("</table>", max(a, 0))
        table = page[a:b + 8] if a >= 0 else ""
        os.makedirs(os.path.join(folder, "lists"), exist_ok=True)
        save_text(table, os.path.join(folder, "lists", f"disposition_{house}.html"))
        for m in re.finditer(r"<tr>\s*<td><a[^>]*>([^<]+)</a></td>\s*<td[^>]*>(.*?)</td>\s*<td>([^<]*)</td>", table, re.S):
            bills[key_of(m.group(1))] = {"last": text(m.group(2)), "date": iso(m.group(3).strip())}
    if not bills:
        if not os.path.exists(path):
            print(f"{ga}: no bills listed yet", flush=True)
            return False
        print(f"{ga}: the lists are empty; kept the last copy", flush=True)
        return True
    save({"ga": ga, "bills": bills}, path)
    state["listed"] = TODAY.isoformat()
    kinds = Counter(re.match(r"[A-Z]+", k).group(0) for k in bills)
    print(f"{ga}: {len(bills)} listed ({', '.join(f'{n} {k}' for k, n in sorted(kinds.items()))})", flush=True)
    return True


def history_part(page):
    """The history section of a bill history page."""
    a = page.find('<section class="grid_12 alpha omega">')
    b = page.find("</section>", max(a, 0))
    return strip(page[a:b + 10]) if a >= 0 and b > 0 else None


def histories(ga, folder, state, kinds, sub):
    """Each listed bill's history (kinds: BILLS or STUDY, into bills/ or study/): new and moved ones first."""
    listing = load(os.path.join(folder, "list.json")) or {}
    bills = {k: v for k, v in (listing.get("bills") or {}).items() if re.match(r"[A-Z]+", k).group(0) in kinds}
    if not bills:
        return
    os.makedirs(os.path.join(folder, sub), exist_ok=True)
    sigs, read, absent = state.setdefault("sig", {}), state.setdefault("read", {}), state.setdefault("absent", {})
    sig = {k: f"{v['date']} {v['last']}" for k, v in bills.items()}
    have = lambda k: os.path.exists(os.path.join(folder, sub, f"{k}.html"))
    urgent = [k for k in bills if (not have(k) and absent.get(k) != sig[k]) or (have(k) and sigs.get(k) != sig[k])]
    rest = []
    if ga == ga_of(YEAR) and TODAY.month <= 6 and kinds == BILLS:
        rest = [k for k in bills if k not in urgent and have(k) and stale(read.get(k))]
        rest.sort(key=lambda k: bills[k]["date"], reverse=True)  # most recently active first
    todo = urgent + rest[:REFRESH_MAX]
    if not todo:
        return
    print(f"{ga} {sub}: {len(bills)} listed; {len(urgent)} new or moved, {len(rest)} a week old; {len(todo)} to read",
          flush=True)
    got = 0
    for k in todo:
        if out_of_time():
            break
        name = re.sub(r"^([A-Z]+)", r"\1 ", k)
        page = request(f"{SITE}/legislation/billTracking/billHistory?billName={urllib.parse.quote(name)}&ga={ga}",
                       f"{ga} {k}", "Bill History")
        part = history_part(page) if page else None
        if not part or "Bill History for" not in part:
            if page is not None or CODE[0] == 404:
                absent[k] = sig[k]  # no such bill page: asked again when the list changes
            continue  # the last copy stays, and it's asked again next run
        save_text(part, os.path.join(folder, sub, f"{k}.html"))
        sigs[k], read[k] = sig[k], TODAY.isoformat()
        absent.pop(k, None)
        got += 1
        STATS[sub] += 1
        if got % 25 == 0:
            save(state, os.path.join(folder, "state.json"))
    save(state, os.path.join(folder, "state.json"))
    print(f"{ga} {sub}: {got} of {len(todo)} read", flush=True)


def explanation(page):
    """The sponsors line and the LSA's explanation from a bill text page (positioned HTML: one span per word)."""
    lines = []
    for m in re.finditer(r"<span class='t' style='top:(\d+)px;'>(.*?)\n</span>", page, re.S):
        words = []
        for w in re.finditer(r"<span class='t' style='([^']*)'>(.*?)</span>", m.group(2), re.S):
            if "<a name=" in w.group(2):
                continue  # a line number
            left = re.search(r"left:(\d+)px", w.group(1))
            words.append((int(left.group(1)) if left else 0, html.unescape(re.sub(r"<[^>]+>", "", w.group(2)))))
        if words:
            lines.append((int(m.group(1)), words[0][0], " ".join(w for _, w in words).strip()))
    by, i = [], 0
    for i, (_, _, line) in enumerate(lines[:40]):
        if line.startswith("BY "):
            by.append(line[3:])
            for _, _, more in lines[i + 1:i + 8]:
                if re.match(r"(A BILL FOR|A JOINT RESOLUTION|An Act|\(SUCCESSOR|\(COMPANION|\(PROPOSED)", more):
                    break
                by.append(more)
            break
    start = next((j for j, l in enumerate(lines) if l[2] == "EXPLANATION"), None)
    if start is None:
        return {"by": " ".join(by), "explanation": ""}
    paras, cur = [], ""
    for top, left, line in lines[start + 1:]:
        if top < 100 or top > 750 or re.fullmatch(r"-\d+-", line):
            continue  # page headers and footers ("H.F. 100", "-2-", "LSB 1082YH (3) 91", "th/ns 2/ 4")
        if line.startswith("The inclusion of this explanation"):
            continue
        if line.startswith("the explanation") and "substance by the members" in line:
            continue
        if left > 110 and cur:  # an indented first line starts a paragraph
            paras.append(cur)
            cur = ""
        cur = cur[:-1] + line if cur.endswith("-") and not cur.endswith(" -") else (cur + " " + line).strip()
    if cur:
        paras.append(cur)
    return {"by": " ".join(by), "explanation": "\n\n".join(paras)}


def texts(ga, folder, state):
    """The explanation from each bill's introduced text, once (a 404 is asked again a week later)."""
    listing = load(os.path.join(folder, "list.json")) or {}
    keys = [k for k in listing.get("bills") or {} if re.match(r"[A-Z]+", k).group(0) in BILLS]
    os.makedirs(os.path.join(folder, "texts"), exist_ok=True)
    gone = state.setdefault("texts_absent", {})
    todo = [k for k in keys if not os.path.exists(os.path.join(folder, "texts", f"{k}.json")) and stale(gone.get(k))]
    if not todo:
        return
    print(f"{ga} texts: {len(todo)} to read", flush=True)
    got = 0
    for k in todo:
        if out_of_time():
            break
        page = request(f"{SITE}/docs/publications/LGI/{ga}/attachments/{k}.html", f"{ga} {k} text", "<span class='t'")
        if not page:
            if CODE[0] == 404:
                gone[k] = TODAY.isoformat()
            continue
        save({"read": TODAY.isoformat(), "version": "LGI", **explanation(page)},
             os.path.join(folder, "texts", f"{k}.json"))
        gone.pop(k, None)
        got += 1
        STATS["texts"] += 1
        if got % 50 == 0:
            save(state, os.path.join(folder, "state.json"))
    save(state, os.path.join(folder, "state.json"))
    print(f"{ga} texts: {got} of {len(todo)} read", flush=True)


def enrolled(ga, folder, state):
    """Each year's enrolled bills list: when missing, and weekly while the General Assembly is current."""
    for year in (first_year(ga), first_year(ga) + 1):
        if year > YEAR or out_of_time():
            continue
        path = os.path.join(folder, f"enrolled_{year}.json")
        if os.path.exists(path) and not (ga == ga_of(YEAR) and stale(state.get(f"enrolled_{year}"))):
            continue
        page = request(f"{SITE}/law/statutory/acts/enrolledBills?year={year}", f"{year} enrolled", "enrolledBillsTable")
        if not page:
            continue
        a = page.find('<table id="enrolledBillsTable"')
        rows = []
        for row in re.findall(r"<tr[^>]*>(.*?)</tr>", page[a:page.find("</table>", a)], re.S):
            cells = [text(c) for c in re.findall(r"<td[^>]*>(.*?)</td>", row, re.S)]
            if len(cells) >= 5:
                rows.append({"bill": key_of(cells[0]), "title": cells[1], "passed": iso(cells[2]), "governor": cells[3],
                             "signed": iso(cells[3]), "effective": cells[4],
                             "applicability": cells[5] if len(cells) > 5 else ""})
        save(rows, path)
        state[f"enrolled_{year}"] = TODAY.isoformat()
        print(f"{year} enrolled: {len(rows)}", flush=True)


# ----------------------------------------------------------------------------------------------- floor votes

def vote_list(ga, session, folder, state):
    """One session's floor votes on bills into votes/list_<year>.json; False if the list can't be had."""
    year = first_year(ga) + session - 1
    path = os.path.join(folder, "votes", f"list_{year}.json")
    when = state.get(f"votes_{year}")
    if os.path.exists(path):
        if year == YEAR and TODAY.month <= 6:
            pass  # every run during the session
        elif ga == ga_of(YEAR) and not stale(when):
            return True
        elif ga < ga_of(YEAR) and not stale(when, 30):
            return True
    page = request(f"{SITE}/legislation/findLegislation/floorVotes?ga={ga}&session={session}", f"{year} floor votes",
                   "Floor Votes on Bills")
    if page is None or selected_ga(page) != (ga, session):
        if page is not None:
            print(f"{year} floor votes: not listed", flush=True)
        return os.path.exists(path)
    out = []
    for block in page.split('<div class="section bill sortable"')[1:]:
        attr = dict(re.findall(r"data-([a-z]+)=['\"]([^'\"]*)['\"]", block[:block.find(">", block.find("data-billname"))]))
        pdf = re.search(r"data-sequence='(\d+)' data-year=\"(\d+)\"[^>]*href=\"\?action=result&calendarItemID=(\d+)"
                        r"&useFile=true&chamberID=([HS])\"", block)
        tally = {k.lower(): int(v) for k, v in re.findall(r"<div class=\"srow\">(AYES|NAYS|ABSENT OR NOT VOTING): (\d+)",
                                                          block)}
        sub = re.search(r"<label>Substituted:</label><span>([^<]*)</span>", block)
        out.append({"bill": key_of(attr.get("billname", "")), "chamber": attr.get("chamber"),
                    "id": int(attr["id"]) if attr.get("id", "").lstrip("-").isdigit() else None,
                    "time": int(attr["timestamp"]) if attr.get("timestamp", "").isdigit() else None,
                    "date": datetime.fromtimestamp(int(attr["datestamp"]) / 1000 + 43200, timezone.utc).date().isoformat()
                    if attr.get("datestamp", "").isdigit() else "",
                    "sequence": int(pdf.group(1)) if pdf else None, "pdf": bool(pdf),
                    "ayes": tally.get("ayes"), "nays": tally.get("nays"), "absent": tally.get("absent or not voting"),
                    "substituted": key_of(sub.group(1)) if sub else ""})
    os.makedirs(os.path.join(folder, "votes"), exist_ok=True)
    save(out, path)
    state[f"votes_{year}"] = TODAY.isoformat()
    print(f"{year} floor votes: {len(out)} ({sum(v['pdf'] for v in out)} roll calls)", flush=True)
    return True


def roll_calls(ga, folder, state):
    """Each listed roll call's PDF as text, once."""
    for session in (1, 2):
        year = first_year(ga) + session - 1
        if year > YEAR or (year == YEAR and TODAY.month == 1 and TODAY.day < 10) or out_of_time():
            continue
        if not vote_list(ga, session, folder, state):
            continue
        votes = load(os.path.join(folder, "votes", f"list_{year}.json")) or []
        out_dir = os.path.join(folder, "votes", str(year))
        os.makedirs(out_dir, exist_ok=True)
        todo = [v for v in votes if v["pdf"] and v["id"] and not os.path.exists(os.path.join(out_dir, f"{v['chamber']}{v['id']}.txt"))]
        if not todo:
            continue
        if not PDFTOTEXT:
            STATS["roll calls skipped (no pdftotext)"] += len(todo)
            continue
        print(f"{year} roll calls: {len(todo)} to read", flush=True)
        got = 0
        for v in todo:
            if out_of_time():
                break
            body = request(f"{SITE}/legislation/findLegislation/floorVotes?action=result&calendarItemID={v['id']}"
                           f"&useFile=true&chamberID={v['chamber']}", f"{year} roll call {v['chamber']}{v['id']}",
                           must=b"%PDF", binary=True)
            words = pdf_text(body)
            if not words or "ROLL CALL" not in words:
                if body:
                    FAILS["unreadable roll call"] += 1
                continue
            save_text(words, os.path.join(out_dir, f"{v['chamber']}{v['id']}.txt"))
            got += 1
            STATS["roll calls"] += 1
        print(f"{year} roll calls: {got} of {len(todo)} read", flush=True)


# ----------------------------------------------------------------------------------------------- members, committees

def member_page(page, pid):
    """One member's page: title, party, district, committees and the "Other Information" fields."""
    head = re.search(r'<h2 style="display: inline">(.*?)</h2>', page, re.S)
    out = {"person": pid, "heading": text(head.group(1)) if head else "", "committees": [], "info": {}}
    side = re.search(r'<div style="text-align: center;">(.*?)</section>', page, re.S)
    if side:
        bits = [text(b) for b in re.findall(r"<div>(.*?)</div>", side.group(1), re.S)]
        out["role"], out["party"] = (bits + ["", ""])[:2]
        d = re.search(r"District (\d+)", side.group(1))
        out["district"] = int(d.group(1)) if d else None
    for sec in re.finditer(r"<h4>(.*?)</h4>(.*?)</ul>", page, re.S):
        kind = text(sec.group(1))
        for c in re.finditer(r'groupID=(\d+)">(.*?)</a>', sec.group(2), re.S):
            label = text(c.group(2))
            dates = re.search(r"\((\d\d/\d\d/\d{4}) - (\d\d/\d\d/\d{4})\)$", label)
            if dates:
                label = label[:dates.start()].strip()
            role = re.search(r"\(([^()]*)\)$", label)
            out["committees"].append({"kind": kind, "group": int(c.group(1)),
                                      "name": label[:role.start()].strip() if role else label,
                                      "role": role.group(1) if role else "",
                                      "from": iso(dates.group(1)) if dates else "", "to": iso(dates.group(2)) if dates else ""})
    for label, value in re.findall(r"<label>(.*?):?</label></td><td>(.*?)</td>", page, re.S):
        out["info"][text(label).rstrip(":")] = text(value)
    return out


def members(ga):
    """A General Assembly's members: both houses' lists and each member's page. Weekly for the current one, once for
    one before. A page that fails keeps its last copy."""
    folder = os.path.join(DATA, "members", str(first_year(ga)))
    path = os.path.join(folder, "members.json")
    last = load(path) or {}
    if last and not last.get("missing") and (ga < ga_of(YEAR) or not stale(last.get("read"))):
        return
    os.makedirs(os.path.join(folder, "pages"), exist_ok=True)
    rows = []
    for house in ("house", "senate"):
        page = request(f"{SITE}/legislators/{house}?ga={ga}", f"{ga} {house} members", "sortableTable")
        if page is None or selected_ga(page)[0] != ga:
            print(f"{ga} {house} members: unreadable" + ("; kept the last copy" if last else ""), flush=True)
            return
        a = page.find('<table id="sortableTable"')
        table = page[a:page.find("</table>", a) + 8]
        f = page.find("<h2>Former Members</h2>")  # members who left during the term, with their dates
        former = page[f:page.find("</table>", f) + 8] if f > 0 else ""
        save_text(table + "\n" + former, os.path.join(folder, f"{house}.html"))
        for row in re.findall(r"<tr>(.*?)</tr>", table + former, re.S):
            cells = re.findall(r"<td[^>]*>(.*?)</td>", row, re.S)
            pid = re.search(r"personID=(\d+)", row)
            if len(cells) < 5 or not pid:
                continue
            name = text(cells[1])
            served = re.search(r"\((\d\d/\d\d/\d{4}) - (\d\d/\d\d/\d{4})\)$", name)
            rows.append({"person": int(pid.group(1)), "chamber": text(cells[0]),
                         "name": name[:served.start()].strip() if served else name,
                         "served": [iso(served.group(1)), iso(served.group(2))] if served else None,
                         "district": int(text(cells[2])) if text(cells[2]).isdigit() else text(cells[2]),
                         "party": text(cells[3]), "county": text(cells[4]),
                         "email": text(cells[5]).lower() if len(cells) > 5 else ""})
    if not rows:
        print(f"{ga} members: none listed" + ("; kept the last copy" if last else ""), flush=True)
        return
    before = {m["person"]: m for m in last.get("members", [])}
    out, missing = [], []
    for m in rows:
        if out_of_time():
            return
        page = request(f"{SITE}/legislators/legislator?ga={ga}&personID={m['person']}", f"member {m['person']}",
                       "Other Information")
        if page:
            part = content(page)
            save_text(part, os.path.join(folder, "pages", f"{m['person']}.html"))
            out.append({**m, **member_page(part, m["person"])})
        elif m["person"] in before:
            out.append(before[m["person"]])
        else:
            out.append(m)
            if not m["served"]:  # a member who left needn't have a page
                missing.append(m["person"])
    save({"ga": ga, "read": TODAY.isoformat(), "members": out, "missing": missing}, path)
    print(f"{ga} members: {sum(m['chamber'] == 'House' for m in out)} House, {sum(m['chamber'] == 'Senate' for m in out)}"
          f" Senate ({sum(bool(m.get('served')) for m in out)} served part of the term), "
          f"{sum(bool(m.get('info', {}).get('Capitol Phone')) for m in out)} with phones"
          + (f"; {len(missing)} pages never read" if missing else ""), flush=True)


def committees(ga):
    """The current General Assembly's House and Senate standing committees and the appropriations subcommittees,
    weekly. A committee whose page fails keeps its last copy."""
    folder = os.path.join(DATA, "committees")
    path = os.path.join(DATA, "committees.json")
    last = load(path) or {}
    if last.get("ga") == ga and not last.get("missing") and not stale(last.get("read")):
        return
    os.makedirs(folder, exist_ok=True)
    page = request(f"{SITE}/committees", "committees", "Standing Committees")
    if not page:
        print("committees: list unreadable; kept the last copy", flush=True)
        return
    found, section = [], None
    for m in re.finditer(r"<h[2-5][^>]*>(.*?)</h[2-5]>|href=\"/committees/committee\?ga=(\d+)&(?:amp;)?groupID=(\d+)\"",
                         page, re.S):
        if m.group(1) is not None:
            section = text(m.group(1))
        elif section in ("Senate", "House", "Appropriations") and int(m.group(2)) == ga:
            found.append((int(m.group(3)), section))
    if not found:
        print("committees: none found on the list; kept the last copy", flush=True)
        return
    before = {c["group"]: c for c in last.get("committees", [])} if last.get("ga") == ga else {}
    out, missing = [], []
    for group, section in found:
        if out_of_time():
            return
        page = request(f"{SITE}/committees/committee?ga={ga}&groupID={group}", f"committee {group}", "<h1>")
        if not page:
            if group in before:
                out.append(before[group])
            else:
                missing.append(group)
            continue
        part = content(page)
        save_text(part, os.path.join(folder, f"{group}.html"))
        name = re.search(r"<h1>(.*?)</h1>", part, re.S)
        mems, house = [], None
        for m in re.finditer(r"<h5>(.*?)</h5>|<li>(.*?)</li>", part, re.S):
            if m.group(1) is not None:
                house = text(m.group(1))
                continue
            item = m.group(2)
            pid = re.search(r"personID=(\d+)", item)
            if not pid or not house or not house.endswith("Members"):
                continue
            who = re.search(r'data-pid="\d+">(.*?)</a>\s*\(([A-Z]), District\s*<a[^>]*>(\d+)</a>\)(.*)', item, re.S)
            mems.append({"person": int(pid.group(1)), "house": house.split()[0],
                         "name": text(who.group(1)) if who else text(item),
                         "party": who.group(2) if who else "", "district": int(who.group(3)) if who else None,
                         "role": text(who.group(4)).strip(", ") if who else ""})
        out.append({"group": group, "section": section, "name": text(name.group(1)) if name else "", "members": mems})
    save({"ga": ga, "read": TODAY.isoformat(), "committees": out, "missing": missing}, path)
    print(f"committees: {len(out)} ({sum(any(m['role'] == 'Chair' for m in c['members']) for c in out)} with a chair)"
          + (f"; {len(missing)} never read" if missing else ""), flush=True)


# ----------------------------------------------------------------------------------------------- the run

def assemblies():
    """The General Assemblies to read, newest first: the next one (November and December of an even year, once listed),
    the current one and the one before."""
    cur = ga_of(YEAR)
    gas = [cur, cur - 1]
    if YEAR % 2 == 0 and TODAY.month >= 11:
        gas.insert(0, cur + 1)
    return [g for g in gas if not ONLY or first_year(g) == ONLY]


def never_downloaded(gas, begun):
    """What was never downloaded: a begun General Assembly's lists, a listed HF, SF, HJR or SJR's history, the current
    members and committees. (Texts, votes, study bills and the enrolled lists don't count; nor does a failed refresh
    with a last copy, a General Assembly not yet listed, or a page that answers 404.)"""
    out = []
    cur = ga_of(YEAR)
    for ga in gas:
        folder = os.path.join(DATA, str(first_year(ga)))
        listing = load(os.path.join(folder, "list.json"))
        if not listing:
            if ga < cur or (ga == cur and (YEAR > first_year(ga) or TODAY.month > 1)) or ga in begun:
                out.append(f"{first_year(ga)}:lists")
            continue
        state = load(os.path.join(folder, "state.json")) or {}
        absent = state.get("absent", {})
        if any(re.match(r"[A-Z]+", k).group(0) in BILLS and not os.path.exists(os.path.join(folder, "bills", f"{k}.html"))
               and k not in absent for k in listing["bills"]):
            out.append(f"{first_year(ga)}:bills")
    if cur in gas:
        m = load(os.path.join(DATA, "members", str(first_year(cur)), "members.json"))
        if not m or m.get("missing"):
            out.append("members")
        c = load(os.path.join(DATA, "committees.json"))
        if not c or c.get("missing"):
            out.append("committees")
    return out


def main():
    os.makedirs(DATA, exist_ok=True)
    # Before the first copy, a run cut off without its summary leaves this, so a partial copy isn't published.
    if not ONLY and not any(name.isdigit() for name in os.listdir(DATA)):
        with open(MARKER, "w") as f:
            f.write("running\n")
    gas = assemblies()
    listed, refused = [], False
    states = {}
    try:
        for ga in gas:  # the newest first: lists, then histories
            if out_of_time():
                break
            folder = os.path.join(DATA, str(first_year(ga)))
            state = states[ga] = load(os.path.join(folder, "state.json"), {})
            exists = os.path.isdir(folder)
            os.makedirs(folder, exist_ok=True)
            if read_lists(ga, folder, state):
                listed.append(ga)
                save(state, os.path.join(folder, "state.json"))
            elif not exists and not os.listdir(folder):
                os.rmdir(folder)  # a General Assembly not listed yet leaves nothing behind
        if ga_of(YEAR) in gas and not out_of_time():
            members(ga_of(YEAR))
            committees(ga_of(YEAR))
        for ga in listed:
            if not out_of_time():
                histories(ga, os.path.join(DATA, str(first_year(ga))), states[ga], BILLS, "bills")
        for ga in gas:
            if ga < ga_of(YEAR) and not out_of_time():
                members(ga)
        for ga in listed:  # the extras
            folder = os.path.join(DATA, str(first_year(ga)))
            if not out_of_time():
                enrolled(ga, folder, states[ga])
            if not out_of_time():
                roll_calls(ga, folder, states[ga])
            save(states[ga], os.path.join(folder, "state.json"))
        for ga in listed:
            if not out_of_time():
                texts(ga, os.path.join(DATA, str(first_year(ga))), states[ga])
        for ga in listed:
            if not out_of_time():
                histories(ga, os.path.join(DATA, str(first_year(ga))), states[ga], STUDY, "study")
    except Refused as e:
        print(f"Stopped: {e}", flush=True)  # the page isn't asked again in this run
        refused = True
    for ga in listed:
        save(states[ga], os.path.join(DATA, str(first_year(ga)), "state.json"))
    missing = never_downloaded([g for g in gas if g <= ga_of(YEAR)], listed)
    sizes = []
    for ga in listed:
        folder = os.path.join(DATA, str(first_year(ga)))
        count = lambda sub: len(os.listdir(os.path.join(folder, sub))) if os.path.isdir(os.path.join(folder, sub)) else 0
        votes = sum(len(os.listdir(os.path.join(folder, "votes", d))) for d in os.listdir(os.path.join(folder, "votes"))
                    if os.path.isdir(os.path.join(folder, "votes", d))) if os.path.isdir(os.path.join(folder, "votes")) else 0
        sizes.append(f"{ga}th: {count('bills')} bills, {count('study')} study bills, {count('texts')} texts, "
                     f"{votes} roll calls")
    print(f"run: {STATS['requests']} requests, {round((time.time() - START) / 60, 1)} min"
          + (f"; read {', '.join(f'{n} {k}' for k, n in STATS.items() if k != 'requests')}" if len(STATS) > 1 else "")
          + (f"; have {'; '.join(sizes)}" if sizes else "")
          + ("; stopped at the time limit" if out_of_time() else "")
          + (f"; stopped at the site's bot check after {STATS['requests']} requests" if refused else "")
          + ("" if PDFTOTEXT else "; no pdftotext (roll calls skipped)")
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
