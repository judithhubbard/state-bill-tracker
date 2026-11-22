"""The Massachusetts House's roll calls by member, from the House Journal's yearly file of them
(https://malegislature.gov/Journal/House/<court>/<year>/RollCalls: one PDF a year listing every "Yea and Nay" of the
year, numbered through the General Court: 2023's are No. 1-70, 2024's No. 71-203). The API has the Senate's roll calls
but not the House's; the bills' histories give the House's tallies and cite these numbers ("Passed to be engrossed -
156 YEAS to 0 NAYS (See YEA and NAY No. 117)").

Each roll call is one page of `pdftotext -layout` text:

                          MASSACHUSETTS HOUSE OF REPRESENTATIVES
                                      H. 57 On adoption of amendment #6
    Yea and Nay                                                                   02/06/2025 02:35 PM
    No. 1                             26 YEAS           126 NAYS                7 N/V
     N       Mr. Speaker          N       Galvin                  N   McMurtry              N       Sylvia
     ...
         X   Blais                N       Hamilton           Y       Robertson         Y           --Jones--
                                  *=AFTER VOTE      P=PRESENT     X=NOT VOTING

Four columns of "<Y|N|X|P> <surname>" (the letter's indent varies); "Moran F." and "Ramos, A." where surnames repeat;
"--Jones--" marks the floor leaders of the minority and of members outside the two parties; "Tyler *" a vote recorded
after the roll closed (counted in the tally); "P", present, is counted in none of the three tallies. fetch() keeps each year's roll calls, read, as data/ma/<session>/
house_rollcalls.json: {"years": {"2025": {"read": day, "bytes": n}}, "calls": {"117": {"date", "bill", "motion",
"yeas", "nays", "nv", "votes": [[name, letter], ...]}}}; convert.py matches them to the bills' House votes by number
(checking the day and the tally) and the names to members (`names()`).
"""
import json, os, re, shutil, subprocess, time, urllib.request
from datetime import date

AGENT = "statebilltracker.org (a nonprofit bill tracker; contact via github.com/judithhubbard)"
SITE = "https://malegislature.gov/Journal/House"
ENTRY = re.compile(r"(?<!\S)([YNXP])\s+(\S+(?: \S+)*?)(?=\s{2,}|\s*$)")


def parse(text):
    """`pdftotext -layout` text of a year's file -> {number: record}. A roll call whose names don't add up to its own
    tallies is kept with "bad": true (and not used)."""
    out = {}
    for page in re.split(r"\n?\s*MASSACHUSETTS HOUSE OF REPRESENTATIVES\s*\n", text)[1:]:
        lines = page.split("\n")
        head = re.match(r"\s*([HS])\.\s*(\d+)\s+(.*)", lines[0])
        when = re.search(r"(\d\d)/(\d\d)/(\d{4})\s+(\d\d:\d\d\s*[AP]M)?", page)
        num = re.search(r"^No\.\s*(\d+)\s+(\d+)\s+YEAS\s+(\d+)\s+NAYS\s+(\d+)\s+N/V", page, re.M)
        if not num or not when:
            continue
        body = page[num.end():]
        body = body.split("*=AFTER VOTE")[0]
        votes = []
        for line in body.split("\n"):
            for letter, name in ENTRY.findall(line):
                name = re.sub(r"\s*\*$", "", name).strip("- ").strip()
                votes.append([name, letter])
        yeas, nays, nv = int(num.group(2)), int(num.group(3)), int(num.group(4))
        count = lambda *ls: sum(1 for _, x in votes if x in ls)
        rec = {"date": f"{when.group(3)}-{when.group(1)}-{when.group(2)}",
               "bill": f"{head.group(1)}{head.group(2)}" if head else "",
               "motion": " ".join((head.group(3) if head else lines[0]).split()),
               "yeas": yeas, "nays": nays, "nv": nv, "votes": votes}
        if count("Y") != yeas or count("N") != nays or count("X") != nv:
            rec["bad"] = True
        out[num.group(1)] = rec
    return out


def court_of(session):
    return (session - 1637) // 2


def download(session, year):
    """One year's file as text, or None (no file yet: the server answers with something other than a PDF)."""
    url = f"{SITE}/{court_of(session)}/{year}/RollCalls"
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": AGENT})
            with urllib.request.urlopen(req, timeout=180) as r:
                pdf = r.read()
            break
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None, 0
            time.sleep(5 * (attempt + 1))
        except Exception:
            time.sleep(5 * (attempt + 1))
    else:
        return None, 0
    if pdf[:4] != b"%PDF":
        return None, 0
    t = subprocess.run(["pdftotext", "-layout", "-enc", "UTF-8", "-", "-"], input=pdf, capture_output=True, timeout=300)
    return t.stdout.decode("utf-8", "replace"), len(pdf)


def cited(folder):
    """The House roll-call numbers the session's bill histories cite."""
    out = set()
    for f in os.listdir(os.path.join(folder, "bills")) if os.path.isdir(os.path.join(folder, "bills")) else []:
        if f.endswith(".json"):
            try:
                acts = json.load(open(os.path.join(folder, "bills", f)))
            except (OSError, ValueError):
                continue
            for a in acts or []:
                out.update(int(n) for n in re.findall(r"YEA and NAY\b[^()]{0,20}?No\.?\s*(\d+)", a.get("Action") or "", re.I))
    return out


def fetch(session, folder, today=None):
    """Read each year's file of the General Court that's due: never read; read before its year ended plus a month (a
    later read finds the whole year); or this year's, when the histories cite a roll call not in it yet (the file
    grows through the year) and the last read is 6 hours old, or a week old in any case. A failure keeps what's
    saved."""
    today = today or date.today()
    path = os.path.join(folder, "house_rollcalls.json")
    try:
        have = json.load(open(path))
    except (OSError, ValueError):
        have = {}
    years, calls = have.get("years") or {}, have.get("calls") or {}
    if not shutil.which("pdftotext"):
        print(f"{session}: House roll calls: pdftotext isn't installed; kept the last copy", flush=True)
        return
    want = cited(folder) - {int(n) for n in calls}
    now = time.time()
    read = []
    for year in (session, session + 1):
        if year > today.year:
            continue
        y = years.get(str(year)) or {}
        age = now - y.get("at", 0)
        if year < today.year:  # a past year: read again once after its year ended (its last weeks' roll calls)
            due = not y or y.get("read", "") < f"{year + 1}-02-01" <= today.isoformat()
        else:
            due = not y or age > 7 * 86400 or bool(want) and age > 6 * 3600
        if not due:
            continue
        text, size = download(session, year)
        if text is None:
            continue
        got = parse(text)
        if not got:
            continue
        calls.update(got)
        years[str(year)] = {"read": today.isoformat(), "at": now, "bytes": size, "first": min(map(int, got)), "last": max(map(int, got))}
        read.append(f"{year}: {len(got)}")
    if read:
        tmp = path + ".tmp"
        json.dump({"years": years, "calls": calls}, open(tmp, "w"), ensure_ascii=False)
        os.replace(tmp, path)
    bad = sum(1 for c in calls.values() if c.get("bad"))
    missing = sorted(cited(folder) - {int(n) for n in calls})
    print(f"{session}: {len(calls)} House roll calls ({', '.join(read) or 'none read now'}; {bad} whose names don't add up"
          f"{f'; cited but not in the files yet: {missing[:8]}' if missing else ''})", flush=True)


def surname_key(s):
    import unicodedata
    s = unicodedata.normalize("NFKD", s)
    return re.sub(r"[^a-z]", "", "".join(c for c in s if not unicodedata.combining(c)).lower())


def matcher(members):
    """members: [{"Name", "MemberCode", "LeadershipPosition"}] (the House's) -> a function from a roll call's name
    ("Moran F.", "Ramos, A.", "Mr. Speaker", "O'Day") to a member code, or None."""
    by_last = {}
    speaker = None
    for m in members:
        name = re.sub(r",?\s+(?:Jr\.?|Sr\.?|II|III|IV)$", "", (m.get("Name") or "").strip())
        words = name.split()
        if not words:
            continue
        by_last.setdefault(surname_key(words[-1]), []).append((m, words))
        # (Two-word surnames: "Sullivan Almeida", "Lipper-Garabedian" are one word already.)
        if len(words) >= 3:
            by_last.setdefault(surname_key(" ".join(words[-2:])), []).append((m, words))
        if re.search(r"^Speaker", m.get("LeadershipPosition") or ""):
            speaker = m["MemberCode"]

    def find(written):
        if re.match(r"Mr\.? Speaker|Madam Speaker", written):
            return speaker
        m = re.match(r"(.+?),?\s+([A-Z])\.$", written)
        last, initial = (m.group(1), m.group(2)) if m else (written, None)
        hits = by_last.get(surname_key(last), [])
        if initial:
            hits = [h for h in hits if h[1][0][:1] == initial] or [h for h in hits if any(w[:1] == initial for w in h[1][:-1])]
        codes = {h[0]["MemberCode"] for h in hits}
        return codes.pop() if len(codes) == 1 else None
    return find
