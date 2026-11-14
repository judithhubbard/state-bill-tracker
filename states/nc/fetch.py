#!/usr/bin/env python3
"""Download North Carolina's bills from the General Assembly's website, https://www.ncleg.gov/ (robots.txt disallows
only /WHPTest/ and /Ethics/ and asks for a crawl delay of 2 seconds), and its web services,
https://webservices.ncleg.gov/ (no robots.txt; its index redirects to www.ncleg.gov/About/Webservices, which lists the
feeds). One request at a time, at least 2 seconds apart.

For each two-year session (2023 = 2023-2024, 2025 = 2025-2026; regular session only):
- The list of every bill and resolution (the "All Bills" feed, /Legislation/Bills/LastActionByYear/<year>/All/RSS: each
  with its title and last action and date) into data/nc/<year>/list.json.
- Each bill's page (/BillLookup/<year>/H4) parsed into data/nc/<year>/bills/<H4>.json: the title, the session law (or
  resolution) number, the editions (filed, each committee substitute, ratified, session law) with their PDF links, the
  sponsors in order (the primary sponsors, then the others, with member ids), attributes (Public/Local), counties,
  statutes and keywords, the "All Votes" table (each roll call's subject, number, tallies and link), and the history
  (date, chamber, action, documents and vote links), oldest first.
  A finished session's bills are read once. The current session's are read again when the feed shows a new last action
  or date, when the last action is from the last three days (more can happen the same day), and otherwise in turn, the
  seventh of them read longest ago each run, so every bill is read at least weekly.
- Each roll call the bill pages link to (/Legislation/Votes/RollCallVoteTranscript/<year>/<H|S>/<n>), member by member
  (names as the chamber writes them, grouped by vote and party), into votes/<H273>.json, once.
- Members: each chamber's member list (/Members/MemberList/<H|S>: name, party, district, counties, office, phone,
  assistant, resigned/appointed notes, member id) and each member's biography page (addresses, phones, terms,
  occupation, leadership title) into members.json. The site only lists the current session's members, so a past
  session's members are the sponsors its bill pages name, each read from their biography page. Emails are hidden on
  the site by Cloudflare's email obfuscation and aren't taken (`emailHidden`).
- Committees: the web service's list (https://webservices.ncleg.gov/AllActiveCommittees/<year>/false, JSON: ids,
  names, chamber) for both sessions; for the current session, each House and Senate standing and select committee's
  page (/Committees/CommitteeInfo/HouseStanding/225: meeting schedule, Senior Chair/Chairs/Vice Chairs/Members by
  member id) into committees.json, once a week. Past sessions' committee pages aren't on the site.
- Bill summaries ("What it does"), last, in the time the run has left (FETCH_MINUTES, set by the workflow, less 5
  minutes): the Legislative Analysis Division's summaries listed on /Legislation/Bills/Summaries/<year>/<H4> (read for
  bills a committee has taken up: others have none; again when the bill's history changes, every two days for a week
  after, and every two weeks for a new law until its session law's summary appears), and the PDFs it links,
  https://dashboard.ncleg.gov/api/Services/BillSummary/<year>/<summary id> (no robots.txt; about 50 KB each), each
  once (a revised summary has a new id), saved as text (pdftotext -layout) in summaries/<id>.txt, with summaries.json
  saying what each bill's list held and when. states/nc/texts.py turns them into data/nc/texts_<year>.json. They fill
  in run by run and never mark the copy incomplete. `--summaries` reads only them (`--limit=N`: at most N requests).
data/nc/incomplete lists what was never downloaded (a failed refresh keeps the last copy; roll calls still to read count
only before the first clean run); it is removed when nothing is missing.
Usage: python3 states/nc/fetch.py [first_year]   (default: the session before this one, and this one)
"""
import html, json, math, os, re, shutil, subprocess, sys, time, urllib.error, urllib.request
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta

SITE = "https://www.ncleg.gov"
WS = "https://webservices.ncleg.gov"
DATA = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "nc"))
AGENT = "statebilltracker.org (a nonprofit bill tracker; contact via github.com/judithhubbard)"
YEAR = date.today().year
CURRENT = YEAR if YEAR % 2 else YEAR - 1
ARGS = [a for a in sys.argv[1:] if not a.startswith("--")]
FIRST = int(ARGS[0]) if ARGS else CURRENT - 2
SUMMARIES_ONLY = "--summaries" in sys.argv
LIMIT = next((int(a[8:]) for a in sys.argv if a.startswith("--limit=")), None)
DELAY = 2.0  # robots.txt's Crawl-delay
REFRESH_DAYS = 7  # every current-session bill (and the members' and committees' pages) is read again this often
INCOMPLETE = set()
WHOLE = [True]  # the last run left nothing missing (set in main): roll calls still to read then don't hold the site
VOTES_LEFT = set()  # sessions with roll calls still to read
MISSING = object()  # a page that answers 404
_last = [0.0]
# The run's own time limit (FETCH_MINUTES, set by the workflow): the summaries stop 5 minutes before it.
START = time.time()
BUDGET = max(0.0, float(os.environ.get("FETCH_MINUTES") or 0) - 5) * 60


def out_of_time():
    return bool(BUDGET) and time.time() - START > BUDGET


def get(url):
    """The page's text; MISSING for a 404, None when it can't be read. Stops the run if the site refuses us."""
    if url.startswith("/"):
        url = SITE + url
    for attempt in range(4):
        wait = _last[0] + DELAY - time.time()
        if wait > 0:
            time.sleep(wait)
        _last[0] = time.time()
        try:
            req = urllib.request.Request(url, headers={"User-Agent": AGENT})
            with urllib.request.urlopen(req, timeout=120) as r:
                body = r.read().decode("utf-8", "replace")
            if "cf-chl" in body[:20000] or "<title>Just a moment" in body[:2000]:
                refused(url, "Cloudflare challenge")
            return body
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return MISSING
            if e.code in (401, 403, 429):
                refused(url, e.code)
            if e.code == 500 and attempt >= 1:  # the site answers 500 for pages that don't exist
                return MISSING
            time.sleep(10 * (attempt + 1))
        except Exception:
            time.sleep(10 * (attempt + 1))
    return None


def refused(url, why):
    print(f"{url}: refused ({why}); stopping", flush=True)
    if not WHOLE[0]:  # a refusal stops a first copy; once whole, the last copies stay
        INCOMPLETE.add(f"refused:{why}".replace(" ", "_"))
    finish()
    sys.exit(1)


def save(path, data):
    with open(path + ".tmp", "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=0)
    os.replace(path + ".tmp", path)


def load(path, default=None):
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def text(fragment):
    """Plain text of an HTML fragment, whitespace collapsed."""
    fragment = re.sub(r"<br\s*/?>", " ", fragment)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", fragment))).replace(" ,", ",").replace(" ;", ";").strip()


def main_part(page):
    i, j = page.find("<main"), page.find("</main>")
    page = page[i if i >= 0 else 0: j if j >= 0 else len(page)]
    return re.sub(r"<script.*?</script>|<style.*?</style>", "", page, flags=re.S)


def iso(mdy):
    try:
        return datetime.strptime(mdy.strip(), "%m/%d/%Y").date().isoformat()
    except ValueError:
        return mdy.strip()


def cols(fragment):
    """The texts and inner HTML of a row's value cells (Bootstrap "col-7" cells; the "col-5 d-md-none" ones are the
    labels shown on phones)."""
    out = []
    for m in re.finditer(r'<div class="col-7[^"]*">(.*?)</div>\s*(?=<div|</div>|$)', fragment, re.S):
        out.append(m.group(1))
    return out


# ---------------------------------------------------------------- the bill list

def bill_list(year):
    """{"H4": {"kind": "HB", "title": "Sam's Law.", "lastAction": "...", "date": "2025-05-07"}} from the All Bills
    feed, or None."""
    body = get(f"/Legislation/Bills/LastActionByYear/{year}/All/RSS")
    if not isinstance(body, str):
        return None
    try:
        root = ET.fromstring(body.lstrip("﻿").encode("utf-8"))
    except ET.ParseError:
        return None
    out = {}
    for item in root.iter("item"):
        guid = (item.findtext("guid") or "").strip()
        m = re.search(rf"/{year}/([HS]\d+)$", guid)
        if not m:
            continue
        title = (item.findtext("title") or "").strip()
        k = re.match(r"([A-Z]+) \d+ - (.*)", title, re.S)
        desc = (item.findtext("description") or "").strip()
        try:
            d = datetime.strptime(" ".join((item.findtext("pubDate") or "").split()[1:4]), "%d %b %Y").date().isoformat()
        except ValueError:
            d = ""
        out[m.group(1)] = {"kind": k.group(1) if k else "", "title": k.group(2).strip() if k else title,
                           "lastAction": re.sub(r"^Last action:\s*", "", desc), "date": d}
    return out


# ---------------------------------------------------------------- bill pages

def members_in(fragment):
    return [{"name": text(n), "id": i, "chamber": c}
            for c, i, n in re.findall(r'<a href="/Members/Biography/([HS])/(\d+)">(.*?)</a>', fragment, re.S)]


def parse_sponsors(cell, chamber):
    """The primary sponsors (the first div, ending "(Primary)"), then the other sponsors (the second div). The current
    session links each to the member's page (with the member id); a past session's pages write names only (id None)."""
    divs = re.findall(r"<div>(.*?)</div>", cell, re.S)
    out = {"sponsorsText": text(cell), "primary": [], "sponsors": []}
    for d in divs:
        people = members_in(d)
        if not people:
            names = [x.strip() for x in text(d).replace("(Primary)", "").split(";")]
            people = [{"name": x, "id": None, "chamber": chamber} for x in names if x]
        if "(Primary)" in d and not out["primary"]:
            out["primary"] = people
        else:
            out["sponsors"] += people
    if not divs:
        out["primary"] = members_in(cell)
    return out


def parse_bill(page, num, year):
    body = main_part(page)
    out = {"number": num, "session": year}
    m = re.search(r'<div class="col-12 col-sm-6 h2 text-center order-sm-2">(.*?)</div>', body, re.S)
    out["heading"] = text(m.group(1)) if m else ""  # "House Bill 3 / SL 2025-13"
    m = re.search(r"/\s*(SL|Res\.?)\s+(\d{4}-\d+)", out["heading"])
    out["law"] = f"{m.group(1)} {m.group(2)}" if m else ""
    m = re.search(r'<div class="col-12">\s*(?:<a href="([^"]*)">)?(.*?)(?:</a>)?\s*</div>\s*<div class="col-12 titleSub">\s*(.*?)\s*</div>',
                  body, re.S)
    out["title"] = text(m.group(2)) if m else ""
    out["titleLink"] = html.unescape(m.group(1)) if m and m.group(1) else ""
    out["sessionName"] = text(m.group(3)) if m else ""
    # Editions and fiscal notes
    eds = []
    card = body[body.find('<div class="card-body">'): body.find('id="bill-misc-info"')]
    for row in re.findall(r'<div class="row">\s*<div class="col-6">(.*?)</div>\s*<div class="col-6">(.*?)</div>\s*</div>', card, re.S):
        a = re.search(r'<a href="([^"]+)">(.*?)</a>', row[0], re.S)
        if a:
            e = {"label": text(a.group(2)), "pdf": html.unescape(a.group(1))}
            f = re.search(r'<a[^>]*href="([^"]+)"[^>]*>(.*?)</a>', row[1], re.S)
            if f:
                e["fiscalNote"] = {"label": text(f.group(2)), "href": html.unescape(f.group(1))}
            eds.append(e)
    out["editions"] = eds
    out["hasSummaries"] = f"/Legislation/Bills/Summaries/{year}/{num}" in body
    # Last action, sponsors, attributes, counties, statutes, keywords
    misc = body[body.find('id="bill-misc-info"'):]
    misc = misc[: misc.find('class="col-12 bill-lookup-section"')] if 'class="col-12 bill-lookup-section"' in misc else misc
    for part in misc.split('misc-info-label">')[1:]:
        label, _, rest = part.partition("</div>")
        value = re.sub(r'^\s*<div class="col-8[^"]*"[^>]*>', "", rest)
        value = re.sub(r'\s*<div[^>]*$', "", value)
        value = re.sub(r'\s*</div>\s*$', "", value)  # the cell's own closing tag
        key = label.strip().rstrip(":")
        if key == "Sponsors":
            out.update(parse_sponsors(value, num[0]))
        elif key == "Last Action":
            out["lastAction"] = text(value)
        elif key:
            out[key[0].lower() + key[1:].replace(" ", "")] = text(re.sub(r"(\s*</div>)+\s*$", "", value))
    # The "All Votes" table
    votes = []
    i = body.find('id="vote-header"')
    if i >= 0:
        vcard = body[i: body.find("<h6", i + 10) if body.find("<h6", i + 10) > 0 else len(body)]
        vbody = vcard[vcard.find('<div class="card-body"'):]
        for row in re.split(r'<div class="row[" ]', vbody)[1:]:
            c = cols(row)
            if len(c) < 10:
                continue
            link = re.search(r'<a href="([^"]+)"', c[9])
            votes.append({"time": text(c[0]), "subject": text(c[1]), "rcs": text(c[2]), "aye": text(c[3]),
                          "no": text(c[4]), "nv": text(c[5]), "excAbs": text(c[6]), "excVote": text(c[7]),
                          "total": text(c[8]), "result": text(c[9]), "link": html.unescape(link.group(1)) if link else ""})
    out["voteTable"] = votes
    # History (the page lists it newest first; kept oldest first)
    hist = []
    j = body.find("<h6 style=\"margin-bottom:0;\">History</h6>")
    if j >= 0:
        hbody = body[j:]
        hbody = hbody[hbody.find('<div class="card-body">'):]
        for row in re.split(r'<div class="row avoid-break-inside">', hbody)[1:]:
            c = cols(row)
            if len(c) < 3:
                continue
            line = {"date": iso(text(c[0])), "chamber": text(c[1]), "action": text(c[2])}
            if len(c) > 3:
                docs = [{"label": text(a[2]), "title": html.unescape(a[1] or ""), "href": html.unescape(a[0])}
                        for a in re.findall(r'<a href="([^"]+)"(?:[^>]*title="([^"]*)")?[^>]*>(.*?)</a>', c[3], re.S)]
                if docs:
                    line["documents"] = docs
            if len(c) > 4:
                vl = [{"text": text(a[1]), "href": html.unescape(a[0])}
                      for a in re.findall(r'<a href="([^"]+)"[^>]*>(.*?)</a>', c[4], re.S)]
                if vl:
                    line["votes"] = vl
            hist.append(line)
    hist.reverse()
    out["history"] = hist
    links = set(v["link"] for v in votes if v["link"]) | set(x["href"] for h in hist for x in h.get("votes", []))
    out["voteIds"] = sorted(vid for vid in (vote_id(l) for l in links) if vid)
    out["otherVoteLinks"] = sorted(l for l in links if not vote_id(l))
    return out


def vote_id(link):
    m = re.search(r"/RollCallVoteTranscript/\d{4}/([HS])/(\d+)$", link)
    return f"{m.group(1)}{m.group(2)}" if m else None


# ---------------------------------------------------------------- roll calls

def parse_vote(page, vid, year):
    body = main_part(page)
    out = {"id": vid, "session": year, "chamber": "House" if vid[0] == "H" else "Senate", "rcs": int(vid[1:])}
    m = re.search(r'<a href="/BillLookup/\d+/([HS]\d+)">(.*?)</a>:</span>(.*?)</div>', body, re.S)
    if m:
        out["bill"], out["billLabel"], out["billTitle"] = m.group(1), text(m.group(2)), text(m.group(3))
    m = re.search(r'Vote:</span>(.*?)</div>', body, re.S)
    out["subject"] = text(m.group(1)) if m else ""
    fields = {}
    for label, value in re.findall(r'<span class="font-weight-bold">([^<]+?):?</span>:?(.*?)</div>', body, re.S):
        fields[label.strip().rstrip(":")] = text(value)
    out["outcome"] = fields.get("Outcome", "")
    out["sponsor"] = fields.get("Sponsor", "")
    out["time"] = fields.get("Time", "")
    t = re.match(r"(\d+/\d+/\d{4})", out["time"])
    out["date"] = iso(t.group(1)) if t else ""
    totals = {}
    for label, key in (("Total votes", "total"), ("Ayes", "aye"), ("Noes", "no"), ("Not Voting", "nv"),
                       ("Excused Absence", "excAbs"), ("Excused Vote", "excVote")):
        if fields.get(label, "").isdigit():
            totals[key] = int(fields[label])
    out["totals"] = totals
    members = []
    for group, names in re.findall(r'<span class="font-weight-bold">([^<]*\([^<)]*\))</span></div>\s*<div class="col-12">(.*?)</div>',
                                   body, re.S):
        g = re.match(r"(.*?)\s*\((.*)\)$", group.strip())
        vote, party = (g.group(1), g.group(2)) if g else (group.strip(), "")
        for n in text(names).split(";"):
            n = n.strip()
            if not n:
                continue
            note = re.search(r"\s*\(([^)]*)\)$", n)  # "D. Hall (Speaker)"
            members.append({"name": re.sub(r"\s*\([^)]*\)$", "", n), "vote": vote, "party": party,
                            **({"note": note.group(1)} if note else {})})
    out["members"] = members
    return out


# ---------------------------------------------------------------- members

def member_list(chamber):
    page = get(f"/Members/MemberList/{chamber}")
    if not isinstance(page, str):
        return None
    body = main_part(page)
    sess = re.search(r'<h2 class="section-sub-title[^"]*">([^<]*Session)', body)
    out = []
    for block in body.split('member-col">')[1:]:
        a = re.search(r'<p><a href="/Members/Biography/([HS])/(\d+)">(.*?)</a>&nbsp;\((\w*)\)</p>', block, re.S)
        if not a:
            continue
        p = {"chamber": a.group(1), "id": a.group(2), "name": text(a.group(3)), "party": a.group(4),
             "listSession": sess.group(1).strip() if sess else ""}
        n = re.search(r'<p style="color:#a01c1c">\((.*?)\)</p>', block)
        if n:
            p["note"] = n.group(1)  # "Resigned 10/31/25", "Appointed 11/18/25", "Deceased 3/18/26"
        d = re.search(r'DistrictPlanMap/(\w+)/(\d+)">District', block)
        if d:
            p["district"], p["plan"] = int(d.group(2)), d.group(1)
        p["counties"] = [text(c) for c in re.findall(r'/Members/CountyRepresentation/[^"]*">(.*?)</a>', block)]
        for label, value in re.findall(r"<strong>([^<]+)</strong>:\s*(?:&nbsp;)*(.*?)</p>", block, re.S):
            p[label.strip().lower()] = text(value)  # office, phone, assistant
        out.append(p)
    return out


def biography(chamber, mid):
    page = get(f"/Members/Biography/{chamber}/{mid}")
    if not isinstance(page, str):
        return None
    body = main_part(page)
    out = {}
    m = re.search(r'<h1 class="section-title">(.*?)</h1>', body, re.S)
    out["heading"] = text(m.group(1)) if m else ""  # "Representative Jay Adams (Rep)"
    m = re.search(r'<h2 class="card-header">(.*?)</h2>', body, re.S)
    out["session"] = text(m.group(1)) if m else ""
    m = re.search(r'<h6 class="text-nowrap">(.*?)</h6>', body, re.S)
    if m:
        pd = re.match(r"(.*?) - District (\d+)", text(m.group(1)))
        if pd:
            out["partyName"], out["district"] = pd.group(1), int(pd.group(2))
    m = re.search(r'<p style="color:#a01c1c; font-weight: bold;">(.*?)</p>', body, re.S)
    if m and text(m.group(1)):
        out["title"] = text(m.group(1))  # leadership
    for label, key in (("Legislative Office:", "office"), ("Mailing Address:", "mailing")):
        s = re.search(re.escape(label) + r"</h6>(.*?)(?=<h6|</div>)", body, re.S)
        if s:
            lines = [text(x) for x in re.findall(r"<p[^>]*>(.*?)</p>", s.group(1), re.S) if text(x)]
            out[key] = [l for l in lines if not re.fullmatch(r"[\d() -]{10,}", l)]
            phones = [l for l in lines if re.fullmatch(r"[\d() -]{10,}", l)]
            if phones:
                out[key + "Phones"] = phones
    for label, value in re.findall(r'font-weight-bold"><p>([^<]+):</p></div>\s*<div class="col-12[^"]*">(.*?)</div>', body, re.S):
        out[label.strip()[0].lower() + label.strip()[1:].replace(" ", "")] = text(value)  # termsInHouse, occupation, mainPhone
    out["emailHidden"] = "__cf_email__" in body
    return out


def members(year, folder, live, seen):
    """members.json: the current session from the member lists (with biographies weekly). The site has no list of a
    past session's members, and its pages name them without ids, so a past session's members.json lists the names and
    parties its roll calls use, by chamber (`fromVotes`), once its roll calls are all read."""
    mpath = os.path.join(folder, "members.json")
    old = {f"{p['chamber']}:{p.get('id')}": p for p in (load(mpath, []) or [])}
    if live:
        people = []
        for chamber in ("H", "S"):
            got = member_list(chamber)
            if not got:
                if not os.path.exists(mpath):  # only a list never read holds the state off the site
                    INCOMPLETE.add(f"{year}:members")
                print(f"{year}: no {chamber} member list; kept the last copy")
                return
            people += got
    else:
        if year not in VOTES_LEFT:
            save(mpath, [{"chamber": c, "name": n, "party": pa, "fromVotes": True} for (c, n), pa in sorted(seen.items())])
            print(f"{year}: {len(seen)} member names from the roll calls", flush=True)
        return
    stale = live and (not os.path.exists(mpath) or (time.time() - os.path.getmtime(os.path.join(folder, "members.json"))) / 86400 >= REFRESH_DAYS)
    bad = 0
    for p in people:
        key = f"{p['chamber']}:{p['id']}"
        prev = old.get(key, {}).get("bio")
        if prev and not stale:
            p["bio"] = prev
            continue
        b = biography(p["chamber"], p["id"])
        if b:
            p["bio"] = b
        elif prev:
            p["bio"] = prev
        else:
            bad += 1
    if bad:
        INCOMPLETE.add(f"{year}:members")
    save(mpath, people)
    print(f"{year}: {len(people)} members ({bad} biographies failed)", flush=True)


# ---------------------------------------------------------------- committees

def committees(year, folder, live):
    cpath = os.path.join(folder, "committees.json")
    age = (time.time() - os.path.getmtime(cpath)) / 86400 if os.path.exists(cpath) else None
    if age is not None and (not live or age < REFRESH_DAYS):
        return
    listing = get(f"{WS}/AllActiveCommittees/{year}/false")
    try:
        listed = json.loads(listing) if isinstance(listing, str) else None
    except ValueError:
        listed = None
    if listed is None:
        if not os.path.exists(cpath):  # a failed refresh keeps the last copy
            INCOMPLETE.add(f"{year}:committees")
        return
    out = {"listed": listed, "pages": []}
    if live:
        page = get("/Committees")
        if not isinstance(page, str):
            if not os.path.exists(cpath):
                INCOMPLETE.add(f"{year}:committees")
            return
        links = sorted(set(re.findall(r'href="/Committees/CommitteeInfo/((?:House|Senate)(?:Standing|Select))/(\d+)"', page)),
                       key=lambda x: (x[0], int(x[1])))
        bad = 0
        for kind, cid in links:
            p = get(f"/Committees/CommitteeInfo/{kind}/{cid}")
            if not isinstance(p, str):
                bad += 1
                continue
            body = main_part(p)
            c = {"id": int(cid), "kind": kind}
            m = re.search(r'<h1 class="section-title">(.*?)</h1>', body, re.S)
            c["name"] = text(m.group(1)) if m else ""
            m = re.search(r'<h2 class="section-sub-title[^"]*">(.*?)</h2>', body, re.S)
            c["type"] = text(m.group(1)) if m else ""
            m = re.search(r'Meeting Schedule:</div>\s*<div[^>]*>(.*?)</div>', body, re.S)
            c["schedule"] = text(m.group(1)) if m else ""
            ms = body[body.find('id="Membership"'): body.find('id="Bills"') if body.find('id="Bills"') > 0 else len(body)]
            roles = []
            for role, chunk in re.findall(r'<h5 class="mt-2">([^<]*)</h5>(.*?)(?=<h5 class="mt-2">|$)', ms, re.S):
                for ch, mid, name in re.findall(r'<a href="/Members/Biography/([HS])/(\d+)">.*?<p>(.*?)</p>', chunk, re.S):
                    roles.append({"role": role.strip(), "chamber": ch, "id": mid, "name": text(name)})
            c["members"] = roles
            out["pages"].append(c)
        if bad:
            if not os.path.exists(cpath):
                INCOMPLETE.add(f"{year}:committees")
            if os.path.exists(cpath):
                print(f"{year}: {bad} committee pages failed; kept the last copy")
                return
    save(cpath, out)
    print(f"{year}: {len(listed)} committees listed, {len(out['pages'])} pages read", flush=True)


# ---------------------------------------------------------------- one session

def session(year):
    folder = os.path.join(DATA, str(year))
    for sub in ("bills", "votes"):
        os.makedirs(os.path.join(folder, sub), exist_ok=True)
    live = year >= CURRENT

    listing = bill_list(year)
    if not listing:
        print(f"{year}: no bill list; kept the last copy")
        listing = load(os.path.join(folder, "list.json"), {}) or {}
        if not listing:  # only a list never read holds the state off the site
            INCOMPLETE.add(f"{year}:list")
    else:
        save(os.path.join(folder, "list.json"), listing)

    def path_of(num):
        return os.path.join(folder, "bills", f"{num}.json")

    recent = (date.today() - timedelta(days=3)).isoformat()
    todo, stale = [], []
    for num, entry in listing.items():
        if not os.path.exists(path_of(num)):
            todo.append(num)
            continue
        if not live:
            continue
        old = load(path_of(num)) or {}
        if (old.get("listAction") != entry["lastAction"] or old.get("listDate") != entry["date"]
                or entry["date"] >= recent or not old.get("history")):
            todo.append(num)
        else:
            stale.append((old.get("fetched", ""), num))
    if live:
        # Each bill read again once it's REFRESH_DAYS old, at most a seventh of the list a run (runs are two hours apart:
        # re-reading a seventh every run took 45 minutes and ran past the time limit).
        cutoff = (datetime.now() - timedelta(days=REFRESH_DAYS)).isoformat(timespec="seconds")
        stale.sort()
        todo += [n for f, n in stale[:math.ceil(len(listing) / REFRESH_DAYS)] if f < cutoff]
    todo = sorted(dict.fromkeys(todo), key=lambda n: (n[0], int(n[1:])))
    print(f"{year}: {len(listing)} bills listed, {len(todo)} to read", flush=True)

    got = failed = 0
    for num in todo:
        page = get(f"/BillLookup/{year}/{num}")
        if not isinstance(page, str):
            failed += 1
            continue
        try:
            bill = parse_bill(page, num, year)
        except Exception as e:
            print(f"{num}: couldn't read the page ({e})")
            failed += 1
            continue
        if not bill["history"] or not bill["title"]:
            print(f"{num}: no history or title on the page")
            failed += 1
            continue
        entry = listing.get(num, {})
        bill["kind"] = entry.get("kind", "")
        bill["listAction"], bill["listDate"] = entry.get("lastAction"), entry.get("date")
        bill["fetched"] = datetime.now().isoformat(timespec="seconds")
        save(path_of(num), bill)
        got += 1
        if got % 250 == 0:
            print(f"{year}: {got} of {len(todo)} bills read", flush=True)
    # A bill whose refresh failed keeps its last copy; only bills never read make the copy incomplete.
    if any(not os.path.exists(path_of(n)) for n in listing):
        INCOMPLETE.add(f"{year}:bills")
    print(f"{year}: {got} of {len(todo)} bills read ({failed} failed)", flush=True)

    votes = set()
    for num in listing:
        b = load(path_of(num))
        if b:
            votes.update(b.get("voteIds", []))
    vtodo = sorted((v for v in votes if not os.path.exists(os.path.join(folder, "votes", f"{v}.json"))),
                   key=lambda v: (v[0], int(v[1:])))
    print(f"{year}: {len(votes)} roll calls, {len(vtodo)} to read", flush=True)
    vgot = 0
    for vid in vtodo:
        page = get(f"/Legislation/Votes/RollCallVoteTranscript/{year}/{vid[0]}/{vid[1:]}")
        if isinstance(page, str):
            try:
                v = parse_vote(page, vid, year)
            except Exception as e:
                print(f"vote {vid}: couldn't read the page ({e})")
                continue
            if v["members"] or v["totals"].get("total") == 0:
                save(os.path.join(folder, "votes", f"{vid}.json"), v)
                vgot += 1
            if vgot and vgot % 250 == 0:
                print(f"{year}: {vgot} of {len(vtodo)} roll calls read", flush=True)
    if vgot < len(vtodo):
        VOTES_LEFT.add(year)
        if not WHOLE[0]:  # roll calls still to read hold only a first copy; later they fill in run by run
            INCOMPLETE.add(f"{year}:votes")
    print(f"{year}: {vgot} of {len(vtodo)} roll calls read", flush=True)

    seen = {}
    if not live:
        for v in votes:
            r = load(os.path.join(folder, "votes", f"{v}.json")) or {}
            for p in r.get("members", []):
                seen.setdefault((v[0], p["name"]), p.get("party", ""))
    members(year, folder, live, seen)
    committees(year, folder, live)


# ---------------------------------------------------------------- bill summaries

class Refused(Exception):
    """The summaries' server turned us away (401/403/429 or a Cloudflare challenge): no more summaries this run."""


def get_summary(url, binary=False):
    """A summary list page (text) or PDF (bytes); MISSING for a 404, None when it can't be read. Never stops the run:
    a refusal raises Refused, which ends only the summaries."""
    if url.startswith("/"):
        url = SITE + url
    for attempt in range(3):
        wait = _last[0] + DELAY - time.time()
        if wait > 0:
            time.sleep(wait)
        _last[0] = time.time()
        SUMMARY_STATS["requests"] += 1
        try:
            req = urllib.request.Request(url, headers={"User-Agent": AGENT})
            with urllib.request.urlopen(req, timeout=60) as r:
                body = r.read()
            if body[:5] != b"%PDF-":
                t = body.decode("utf-8", "replace")
                if "cf-chl" in t[:20000] or "<title>Just a moment" in t[:2000]:
                    raise Refused(f"{url}: Cloudflare challenge")
                return body if binary else t
            return body
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return MISSING
            if e.code in (401, 403, 429):
                raise Refused(f"{url}: {e.code}")
            if e.code == 500 and attempt >= 1:
                return MISSING
        except Refused:
            raise
        except Exception:
            pass
        if out_of_time():
            return None
        time.sleep(10 * (attempt + 1))
    return None


SUMMARY_STATS = {"requests": 0}
# History lines that don't mean a committee took the bill up (bills with only these have no summaries).
UNHEARD = re.compile(r"(Filed|Passed 1st Reading|Ref(?:'d)? [Tt]o|Ref to|Re-ref|Withdrawn From Com|Sequential Referral|"
                     r"Serial Referral)", re.I)


def summaries_due(bill, entry, today):
    """Whether a bill's list of summaries should be read now."""
    hist = bill.get("history") or []
    if not any(not UNHEARD.match(h.get("action", "")) for h in hist):
        return False  # never taken up in committee: no summaries (none of 12 such bills checked had any)
    if not entry:
        return True
    if entry.get("sig") != signature(bill):
        return True
    listed = entry.get("listed", "")
    last = max((h.get("date", "") for h in hist), default="")
    try:
        after = (date.fromisoformat(last) + timedelta(days=7)).isoformat()
    except ValueError:
        after = ""
    if listed < after and listed <= (today - timedelta(days=2)).isoformat():
        return True  # summaries are often posted days after the step
    law = next((h.get("date", "") for h in hist if h.get("action", "").startswith("Ch. ")), "")
    if bill.get("law", "").startswith("SL") and not any("(sl)" in r["id"] for r in entry.get("rows", [])):
        # A new law: its session law's summary comes weeks or months later.
        if law >= (today - timedelta(days=365)).isoformat() and listed <= (today - timedelta(days=14)).isoformat():
            return True
    return False


def signature(bill):
    return f"{len(bill.get('history') or [])}|{len(bill.get('editions') or [])}|{bill.get('law', '')}"


def pdf_to_text(body):
    """pdftotext -layout of a PDF's bytes, or None."""
    try:
        r = subprocess.run(["pdftotext", "-layout", "-enc", "UTF-8", "-", "-"], input=body, capture_output=True,
                           timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return r.stdout.decode("utf-8", "replace") if r.returncode == 0 and r.stdout.strip() else None


def texts_module():
    import importlib.util
    spec = importlib.util.spec_from_file_location("nc_texts", os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                                            "texts.py"))
    T = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(T)
    return T


def summaries(years):
    """Bill summaries, as the run's time allows (see the module's docstring); then texts_<year>.json. Never marks the
    copy incomplete: what isn't read now is read on a later run."""
    T = texts_module()
    today = date.today()
    week_ago = (today - timedelta(days=7)).isoformat()
    can_read = bool(shutil.which("pdftotext"))
    if not can_read:
        print("summaries: pdftotext isn't installed; no new summaries read", flush=True)
    indexes, todo = {}, []
    for year in years:
        folder = os.path.join(DATA, str(year))
        bills_dir = os.path.join(folder, "bills")
        index = load(os.path.join(folder, "summaries.json"), {})
        indexes[year] = index
        if not os.path.isdir(bills_dir):
            continue
        for name in os.listdir(bills_dir):
            if not name.endswith(".json"):
                continue
            bill = load(os.path.join(bills_dir, name)) or {}
            key = name[:-5]
            entry = index.get(key)
            if entry:  # chosen again each run, so a change in texts.choose() takes effect without reading the list
                entry["chosen"] = T.choose(entry.get("rows", []))
            listing = summaries_due(bill, entry, today)
            missing = [i for i in (entry or {}).get("chosen", [])
                       if not os.path.exists(os.path.join(folder, "summaries", T.file_of(i)))
                       and (entry.get("bad", {}).get(i, "") <= week_ago)]
            if listing or missing:
                last = max((h.get("date", "") for h in bill.get("history") or []), default="")
                # The current session first, then laws, then the bills that moved most recently.
                todo.append(((year != CURRENT, not bill.get("law"), "".join(chr(0x10FFFF - ord(c)) for c in last)),
                             year, key, bill, listing))
    todo.sort(key=lambda t: t[0])
    print(f"summaries: {len(todo)} bills to look at", flush=True)
    read = {"lists": 0, "docs": 0, "bills": 0}
    stopped = ""
    try:
        for n, (_, year, key, bill, listing) in enumerate(todo):
            if not can_read:
                stopped = "pdftotext isn't installed"
                break
            if out_of_time() or (LIMIT is not None and SUMMARY_STATS["requests"] >= LIMIT):
                stopped = "out of time" if out_of_time() else "request limit"
                break
            folder = os.path.join(DATA, str(year))
            index = indexes[year]
            entry = index.setdefault(key, {})
            if listing:
                page = get_summary(f"/Legislation/Bills/Summaries/{year}/{key}")
                if page is None:
                    continue
                rows = [] if page is MISSING else T.parse_list(page)
                entry.update({"listed": today.isoformat(), "sig": signature(bill), "rows": rows,
                              "chosen": T.choose(rows)})
                read["lists"] += 1
            for sid in entry.get("chosen", []):
                path = os.path.join(folder, "summaries", T.file_of(sid))
                if os.path.exists(path) or entry.get("bad", {}).get(sid, "") > week_ago:
                    continue
                if out_of_time() or (LIMIT is not None and SUMMARY_STATS["requests"] >= LIMIT):
                    break
                body = get_summary(f"https://dashboard.ncleg.gov/api/Services/BillSummary/{year}/{sid}", binary=True)
                t = pdf_to_text(body) if isinstance(body, bytes) and body[:5] == b"%PDF-" else None
                if t is None:
                    if body is not None:  # not a PDF, or one pdftotext can't read: tried again in a week
                        entry.setdefault("bad", {})[sid] = today.isoformat()
                    continue
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path + ".tmp", "w", encoding="utf-8") as f:
                    f.write(t)
                os.replace(path + ".tmp", path)
                entry.get("bad", {}).pop(sid, None)
                read["docs"] += 1
            read["bills"] += 1
            if n % 25 == 24:
                save(os.path.join(folder, "summaries.json"), index)
    except Refused as e:
        stopped = f"refused ({e})"
    finally:
        for year, index in indexes.items():
            if index:
                save(os.path.join(DATA, str(year), "summaries.json"), index)
    print(f"summaries: {read['lists']} lists and {read['docs']} summaries read for {read['bills']} of {len(todo)} bills"
          + (f"; stopped: {stopped}" if stopped else ""), flush=True)
    for year in years:
        try:
            T.write(year)
        except Exception as e:  # a summary that fails to read mustn't stop the run
            print(f"{year} texts: failed ({type(e).__name__}: {e})", flush=True)


def begun(year):
    """Whether a session has convened (the second Wednesday of January of its first year)."""
    return date.today() >= date(year, 1, 1 + (2 - date(year, 1, 1).weekday()) % 7 + 7)


def finish():
    marker = os.path.join(DATA, "incomplete")
    # A session not yet begun (no bills or members listed yet) is read when it's there but never holds the state back.
    undone = {g for g in INCOMPLETE if not g[:4].isdigit() or begun(int(g[:4]))}
    if undone:
        with open(marker, "w") as f:
            f.write(" ".join(sorted(undone)) + "\n")
    elif os.path.exists(marker):
        os.remove(marker)


def main():
    os.makedirs(DATA, exist_ok=True)
    if SUMMARIES_ONLY:
        summaries(list(range(FIRST, CURRENT + 1, 2)))
        return
    marker = os.path.join(DATA, "incomplete")
    WHOLE[0] = not os.path.exists(marker)
    if not os.path.exists(marker):  # until this run finishes, the copy may be partial
        with open(marker, "w") as f:
            f.write("running\n")
    for y in range(FIRST, CURRENT + 1, 2):
        session(y)
    sys.path.insert(0, os.path.normpath(os.path.join(DATA, "..", "..")))
    from states.nc import contacts
    try:
        contacts.main(CURRENT)
    except (SystemExit, OSError) as e:
        print(e)
    finish()
    try:  # last, in the time left; whatever happens here, the copy's completeness is already settled
        summaries(list(range(FIRST, CURRENT + 1, 2)))
    except Exception as e:
        print(f"summaries: failed ({type(e).__name__}: {e})", flush=True)


if __name__ == "__main__":
    main()
