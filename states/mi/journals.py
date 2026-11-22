"""Michigan's House and Senate Journals: members' floor votes and committee votes by name.

The bills' status files (fetch.py) give each floor vote's roll call number and tally ("passed; given immediate effect
Roll Call #241 Yeas 104 Nays 5 Excused 0 Not Voting 1"; the Senate's lines often only "PASSED ROLL CALL # 12"), but the
members' votes are only in the journals: www.legislature.mi.gov/documents/<session>/Journal/<House|Senate>/htm/
<yyyy>-HJ-<mm>-<dd>-<nnn>.htm (-SJ- for the Senate), one Word-exported web page per session day, posted the next day
around midday and sometimes rewritten later (the folder listing's date and size say when). No robots.txt; the
Legislature's policy allows one request a second. Pages are UTF-8 or Windows-1252 (read UTF-8 first). `fetch()` keeps
each as plain text, gzipped (data/mi/<session>/journals/<name>.txt.gz; about 800 a session, 200 MB of HTML, about
12 MB kept); `listing.json` beside them has the listing entries read.

What's read (`parse()`):
- The opening roll: "Alexander—present", "Paiz—excused" for every member (the House's; the Senate's has it too). It's
  the day's roster: House roll calls name only the yeas and nays, so members not named were excused or didn't vote.
- Each roll call: "Roll Call No. 241 Yeas—104", the names (in table cells, tab-separated columns, or space-separated
  short lists; two-word names like "St. Germaine", "McDonald Rivet" and initials "Carter, B." are put back together
  with the day's roster), "Nays—5", the Senate's "Excused—1" and "Not Voting—0" (older pages break it "Not / Voting"),
  up to "In The Chair:". Numbers restart each year in each house, so a roll call is (house, year, number). The bill
  named last before it ("Senate Bill No. 579") is kept as a check.
- Committee reports with a recorded vote: "The Committee on Health Policy, by Rep. VanderWall, Chair, reported House
  Bill No. 4779 ... Favorable Roll Call To Report Out: Yeas: Reps. VanderWall, ..., Brenda Carter, ... and Foreman
  Nays: Rep. Meerman" (the Senate's "The Committee on Education reported Senate Bill No. 463 ... To Report Out: Yeas:
  Senators ... Nays: ..."), and each committee's attendance report ("Meeting held on: Wednesday, March 4, 2026",
  "Present: Reps. ...", "Absent: ...", "Excused: ..."), whose members are the committee that day.
"""
import glob, gzip, html, json, os, re
from datetime import date

MONTHS = {m: i + 1 for i, m in enumerate(["january", "february", "march", "april", "may", "june", "july", "august",
                                          "september", "october", "november", "december"])}
FILE = re.compile(r"(\d{4})-([HS])J-(\d\d)-(\d\d)-(\d{3})")


def page_text(raw):
    """A journal page (bytes) -> plain text: a line per paragraph or table row, table cells and Word's tab stops as tabs,
    runs of spaces (the Senate's short name lists) as tabs too."""
    try:
        t = raw.decode("utf-8")
    except UnicodeDecodeError:
        t = raw.decode("cp1252", "replace")
    t = re.sub(r"(?is)<(style|script|head)[^>]*>.*?</\1>", " ", t)
    t = re.sub(r"(?i)<br\s*/?>|</p>|</div>|</tr>|</h\d>|</li>", "\n", t)
    t = re.sub(r"(?i)</td>", "\t", t)
    t = re.sub(r"<[^>]+>", "", t)
    t = html.unescape(t).replace("\xa0", " ").replace("\r", "")
    t = re.sub(r" {2,}", "\t", t)
    t = re.sub(r" *\t[ \t]*", "\t", t)
    return re.sub(r"[ \t]*\n\s*", "\n", t).strip() + "\n"


def folder(data, session):
    return os.path.join(data, session, "journals")


def fetch(data, session, get, out_of_time, same, say=print):
    """One session's journals (session "2025-2026"): each listed page not read yet, or whose listing entry (date and
    size, compared with listing_dates.same()) changed. Never marks Michigan incomplete: what isn't read now is read on a
    later run. get(url) -> bytes or None."""
    out = folder(data, session)
    os.makedirs(out, exist_ok=True)
    seen_path = os.path.join(out, "listing.json")
    try:
        seen = json.load(open(seen_path))
    except (OSError, ValueError):
        seen = {}
    todo, listed = [], 0
    for house in ("House", "Senate"):
        if out_of_time():
            break
        listing = (get(f"https://www.legislature.mi.gov/documents/{session}/Journal/{house}/htm/") or b"").decode("utf-8", "replace")
        for m in re.finditer(r"(\d+/\d+/\d{4}\s+\d+:\d+ [AP]M)\s+(\d+) <A HREF=\"([^\"]*/(\d{4}-[HS]J-\d\d-\d\d-\d{3})\.htm)\"", listing, re.I):
            listed += 1
            stamp, path, name = f"{m.group(1)} {m.group(2)}", m.group(3), m.group(4)
            if os.path.exists(os.path.join(out, name + ".txt.gz")) and same(seen.get(name), stamp):
                continue
            todo.append((name, path, stamp))
    todo.sort(key=lambda t: (t[0][:4], t[0][8:13], t[0][5]), reverse=True)  # the newest days first
    got = 0
    for i, (name, path, stamp) in enumerate(todo):
        if out_of_time():
            break
        if i and i % 50 == 0:
            json.dump(seen, open(seen_path, "w"))
        body = get("https://www.legislature.mi.gov" + path)
        if not body or b"Roll" not in body and b"JOURNAL" not in body.upper():
            continue
        tmp = os.path.join(out, name + ".tmp")
        with gzip.open(tmp, "wt", encoding="utf-8") as f:
            f.write(page_text(body))
        os.replace(tmp, os.path.join(out, name + ".txt.gz"))
        seen[name] = stamp
        got += 1
    json.dump(seen, open(seen_path, "w"))
    say(f"{session} journals: {got} of {len(todo)} read ({listed} listed)")


def journal_files(data, session):
    """[(house, ISO day, path)] for a session's saved journals, in order."""
    out = []
    for p in sorted(glob.glob(os.path.join(folder(data, session), "*.txt.gz"))):
        m = FILE.match(os.path.basename(p))
        if m:
            out.append((m.group(2), f"{m.group(1)}-{m.group(3)}-{m.group(4)}", p))
    return out


def fold(s):
    return re.sub(r"[^a-z]", "", (s or "").lower().replace("’", "'"))


# "e/d/s": entered during the session (2024's House journals).
ROLL_STATUS = re.compile(r"\s*—\s*(present|excused|absent|not present|e/d/s)(?![\w/])", re.I)


def roster(text):
    """The opening roll ("Alexander—present Foreman—present ... Greene, J.—present") -> {name: status}."""
    flat = re.sub(r"\s+", " ", text[:20000])
    m = re.search(r"roll was called .{0,200}?quorum (?:was )?present\.?", flat, re.I)
    if not m:
        return {}
    bits = ROLL_STATUS.split(flat[m.end():])
    out = {}
    for i in range(0, len(bits) - 1, 2):
        name = bits[i].strip(" ,")
        if not name or len(name) > 40 or len(name.split()) > 3 or not re.match(r"[A-Z]", name):
            break
        out[name] = bits[i + 1].lower()
    return out


def split_names(chunk, known):
    """A list of surnames (tabs, newlines or spaces between them) -> names, putting back "Carter, B.", "St. Germaine" and
    the roster's other multi-word names (known: the day's roster names)."""
    toks = chunk.split()
    keys = {re.sub(r"\s+", " ", k): k for k in known}
    out, i = [], 0
    while i < len(toks):
        for k in (3, 2, 1):
            cand = " ".join(toks[i:i + k])
            if k > 1 and cand in keys:
                out.append(cand)
                i += k
                break
        else:
            t = toks[i]
            if t.endswith(",") and i + 1 < len(toks) and re.fullmatch(r"[A-Z]\.(?:[A-Z]\.)?", toks[i + 1]):
                out.append(f"{t} {toks[i + 1]}")
                i += 2
            elif t in ("St.", "Van", "Vander", "De", "La", "Le", "Mac", "Mc") and i + 1 < len(toks):
                out.append(f"{t} {toks[i + 1]}")
                i += 2
            else:
                out.append(t)
                i += 1
    return [n.strip(",") for n in out if n.strip(",")]


GROUP = re.compile(r"(Yeas|Nays|Excused|Not\s+Voting)\s*—\s*(\d+)")
BILL = re.compile(r"\b(House|Senate)\s+(Bill|Joint\s+Resolution)\s+No\.\s*(\d+|[A-Z]{1,2})\b")


def bill_key(m):
    return f"{m.group(1)[0]}{'B' if m.group(2) == 'Bill' else 'JR'}{int(m.group(3)) if m.group(3).isdigit() else m.group(3)}"


def rolls(text, known):
    """Each floor roll call: {"no", "groups": {"Y": [...], "N": [...], "E": [...], "A": [...]}, "counts": {...}, "bill"}.
    A group whose names don't come to its count is marked "bad"."""
    out = []
    starts = [m for m in re.finditer(r"Roll Call No\.\s*(\d+)", text)]
    prev_end = 0
    for k, m in enumerate(starts):
        nxt = starts[k + 1].start() if k + 1 < len(starts) else len(text)
        chair = re.compile(r"In\s+The\s+Chair").search(text, m.end(), nxt)
        end = chair.start() if chair else min(nxt, m.end() + 6000)
        block = text[m.end():end]
        before = text[max(prev_end, m.start() - 400000):m.start()]
        # The bill being read ("House Bill No. 4062, entitled"), else the last named (a conference report's).
        # The bill just read ("House Bill No. 4062, entitled ...", within the few thousand characters before the roll
        # call, after the one before it): a conference report's text can name other bills, so only this is a check.
        near = before[-6000:]
        bills = [b for b in BILL.finditer(near) if re.match(r",?\s+entitled", near[b.end():b.end() + 12])]
        prev_end = end
        heads = list(GROUP.finditer(block))
        if not heads or heads[0].group(1) != "Yeas":
            continue
        groups, counts, bad = {}, {}, False
        for i, h in enumerate(heads):
            code = {"Yeas": "Y", "Nays": "N", "Excused": "E"}.get(h.group(1), "A")
            chunk = block[h.end():heads[i + 1].start() if i + 1 < len(heads) else len(block)]
            chunk = re.sub(r"\bNot\s*$", "", chunk)  # "Not / Voting—0" broken across lines
            names = split_names(chunk, known)
            groups[code], counts[code] = names, int(h.group(2))
        # A column run past its heading (the Senate's Roll Call 217 of 2026: two yeas printed under "Nays—0"): names
        # past a group's count belong to the group before when it's short by exactly as many.
        order = list(groups)
        for i in range(1, len(order)):
            a, b = order[i - 1], order[i]
            short, extra = counts[a] - len(groups[a]), len(groups[b]) - counts[b]
            if short > 0 and short == extra:
                groups[a], groups[b] = groups[a] + groups[b][:short], groups[b][short:]
        bad = any(len(groups[c]) != counts[c] for c in groups)
        out.append({"no": int(m.group(1)), "groups": groups, "counts": counts, "bad": bad,
                    "bill": bill_key(bills[-1]) if bills else None})
    return out


def name_list(s):
    """"Reps. VanderWall, Thompson, St. Germaine, Brenda Carter ... and Foreman" -> names; "None" -> []."""
    s = re.sub(r"\s+", " ", s).strip(" .")
    s = re.sub(r"^(?:Reps?|Representatives?|Senators?|Sens?)\.?\s+", "", s)
    if not s or re.fullmatch(r"None", s, re.I):
        return []
    parts = re.split(r",\s*(?:and\s+)?|\s+and\s+", s)
    return [re.sub(r"\s*\((?:C|VC|MVC)\)$", "", p).strip() for p in parts if p.strip()]


def when(s):
    m = re.search(r"([A-Z][a-z]+) (\d{1,2}), (\d{4})", s)
    if m and m.group(1).lower() in MONTHS:
        try:
            return date(int(m.group(3)), MONTHS[m.group(1).lower()], int(m.group(2))).isoformat()
        except ValueError:
            return None
    return None


def committee_name(s):
    s = re.sub(r"\s+", " ", s).strip(" ,")
    return re.sub(r"^(?:the )?Committee on ", "", s)


def committee(text):
    """Committee votes and attendance in one journal: ([{committee, bill, yeas, nays, pass}], [{committee, day,
    present, absent, excused}])."""
    flat = re.sub(r"\s+", " ", text)
    votes = []
    for m in re.finditer(r"The (?:Conference )?Committee on ([A-Z][^.]{2,120}?),?(?: by (?:Rep|Senator)\.? [^,]+, Chair(?:person)?,)? reported "
                         r"((?:House|Senate) (?:Bill|Joint Resolution) No\. (?:\d+|[A-Z]{1,2}))", flat):
        seg = flat[m.end():m.end() + 6000]
        stop = re.search(r"The (?:Conference )?Committee on |COMMITTEE ATTENDANCE REPORT", seg)
        seg = seg[:stop.start()] if stop else seg
        r = re.search(r"To (?:Report Out|Refer)\s*:\s*Yeas\s*:\s*(.*?)\s*Nays\s*:\s*(.*?)(?=\s+(?:Pass\s*:|The\b|COMMITTEE\b|With\b|Without\b|Scheduled\b)|$)", seg)
        if not r:
            continue
        nays_txt = r.group(2)
        p = re.search(r"Pass\s*:\s*(.*?)(?=\s+(?:The|COMMITTEE)\b|$)", seg[r.end():r.end() + 400])
        b = BILL.search(m.group(2))
        votes.append({"committee": committee_name(m.group(1)), "bill": bill_key(b), "yeas": name_list(r.group(1)),
                      "nays": name_list(nays_txt), "pass": name_list(p.group(1)) if p else [],
                      "refer": "Refer" in seg[r.start():r.start() + 12]})
    attend = []
    for m in re.finditer(r"COMMITTEE ATTENDANCE REPORT (.{0,400}?)Meeting held on:? ([^,]+, [A-Z][a-z]+ \d{1,2}, \d{4})(.*?)(?=COMMITTEE ATTENDANCE REPORT|$)", flat):
        head, body = m.group(1), m.group(3)[:3000]
        c = re.search(r"(?:Conference )?Committee on (.+?)(?:,? was received| submitted)", head)
        if not c or "Conference Committee" in head:
            continue
        got = {}
        for label in ("Present", "Absent", "Excused"):
            x = re.search(label + r"\s*:\s*(.*?)(?=\s*(?:Present|Absent|Excused)\s*:|\s+(?:The|Senator \w+ moved|Rep\. \w+ moved|Scheduled|Notices|Messages|Introduction|Communications|By unanimous|Announcement|Reports?)\b|$)", body)
            got[label] = name_list(x.group(1)) if x else []
        attend.append({"committee": committee_name(c.group(1)), "day": when(m.group(2)), "present": got["Present"],
                       "absent": got["Absent"], "excused": got["Excused"]})
    return votes, attend


_PARSED = {}


def parse(data, session):
    """Every saved journal of a session: {"rolls": {(house, year, number): roll with "day"}, "committee": [vote with
    "house", "day" (the meeting's), "journal" (the journal's day), "attend" (its attendance report, or None)],
    "rosters": {(house, day): roster}, "dups": n}."""
    if session in _PARSED:
        return _PARSED[session]
    out = {"rolls": {}, "committee": [], "rosters": {}, "dups": 0, "journals": 0}
    known = {"H": set(), "S": set()}
    files = journal_files(data, session)
    texts = []
    for h, day, p in files:
        try:
            t = gzip.open(p, "rt", encoding="utf-8").read()
        except (OSError, EOFError):
            continue
        r = roster(t)
        out["rosters"][(h, day)] = r
        known[h] |= set(r)
        texts.append((h, day, t))
    for h, day, t in texts:
        out["journals"] += 1
        for rc in rolls(t, known[h] | set(out["rosters"].get((h, day), {}))):
            key = (h, day[:4], rc["no"])
            rc["day"] = day
            if key in out["rolls"]:
                out["dups"] += 1
                continue
            out["rolls"][key] = rc
        votes, attend = committee(t)
        for v in votes:
            names = set(v["yeas"]) | set(v["nays"]) | set(v["pass"])
            fits = [a for a in attend if a["committee"].lower() == v["committee"].lower() and names <= set(a["present"])]
            v.update(house=h, journal=day, attend=fits[0] if len(fits) == 1 else None,
                     day=(fits[0]["day"] if len(fits) == 1 and fits[0]["day"] else day))
            out["committee"].append(v)
    _PARSED[session] = out
    return out
