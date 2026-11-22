#!/usr/bin/env python3
"""Connecticut's floor roll calls, member by member, from the House and Senate Journals (www.cga.ct.gov; robots.txt
allows /<year>/jnl/). The FTP files have no votes, and the vote sheets' only index is the bill status pages, which
robots.txt disallows; the journals print every roll call in full:

    The following is the result of the vote:
         Total Number Voting ............ 144
            Those voting Yea ............ 144
            Those voting Nay ............ 0
            Those absent and not voting . 7
        On a roll call vote House Bill No. 7083 as amended by House Amendment Schedule "A"
    was passed.
         The following is the roll call vote:
     Y       ALLIE-BRENNAN        Y       HUGHES        ...        X JACOBSON

(the House by surname, "JOHNSON, D." where two share one; the Senate by district and name, "N 21 JASON PERILLO"; X is
absent or not voting). The Senate's consent calendar is one roll call for every bill "placed on the Consent Calendar
No. 1" earlier in the day's journal ("On the roll call vote the Consent Calendar No. 1 was adopted."). Amendments'
roll calls are left out.

Each journal is one PDF a session day, its address built from the day: /2025/jnl/h/pdf/2025HJL00501-R00-JNL.PDF (House,
May 1), /2025/jnl/s/pdf/2025SJL00604-R00-JNL.PDF (Senate). No folder listing exists (403), so the days asked for are those
the bill history names for a floor vote in that house (fetch()). The PDFs are large (1-8 MB), so only their text is kept,
data/ct/<year>/journals/H0501.txt; a journal is read once. One not posted yet (404) is asked for again at most once a day,
for 60 days after the session day. The journal of a day is usually posted within a day or two (2026: May 5's on May 6;
May 6's, the last day's, on May 12: see NOTES.md).

Usage: python3 states/ct/journals.py [year ...]   (default: every year downloaded; fetch.py calls fetch() each run)
"""
import json, os, re, subprocess, sys, time
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
from states.ct import profile as P

SITE = "https://www.cga.ct.gov"
RETRY_DAYS = 60
TODAY = datetime.now(ZoneInfo(P.TIMEZONE)).date()


def folder(y):
    return os.path.join(P.DATA, str(y), "journals")


def url(h, day):
    y, mmdd = day[:4], day[5:7] + day[8:10]
    return f"{SITE}/{y}/jnl/{h.lower()}/pdf/{y}{h}JL0{mmdd}-R00-JNL.PDF"


FLOOR = re.compile(r"^(?:(HOUSE|SEN\.|SENATE) (?:PASSED|REJECTED BILL|ADOPTED,|FAILED)|(?:RE-)?ADOPTED,?\s+(HOUSE|HO\.|SENATE|SEN\.)"
                   r"|RULES SUSPENDED, ADOPTED (HOUSE|SEN)|(?:VETO OVERRIDDEN|PASSED OVER VETO)\W*(HOUSE|SEN))", re.I)


def floor_steps(y):
    """bill ("HB5141") -> {(house, day)}: the floor votes its history names."""
    from states.ct import convert as C
    out = {}
    for r in C.rows(y, "bill_history"):
        m = FLOOR.match((r.get("act_desc") or "").strip())
        day, num = (r.get("act_date") or "")[:10], r.get("bill_num") or ""
        if m and re.fullmatch(r"\d{4}-\d\d-\d\d", day) and re.fullmatch(r"[HS][BJ]\d+", num):
            word = next(g for g in m.groups() if g).upper()
            out.setdefault(num[:2] + str(int(num[2:])), set()).add(("H" if word.startswith("H") else "S", day))
    return out


def floor_days(y):
    """(house, day) for each day the bill history names a floor vote in that house."""
    return set().union(*floor_steps(y).values())


def _get(u):
    """(status, body): 200 and the PDF, 404, or 0 on another failure."""
    from states.ct.fetch import CA
    time.sleep(2)
    r = subprocess.run(["curl", "-sS", "--cacert", CA, "--connect-timeout", "20", "--max-time", "240", "-w", "\n%{http_code}",
                        u], capture_output=True)
    if r.returncode:
        return 0, b""
    body, _, code = r.stdout.rpartition(b"\n")
    code = int(code or 0)
    if code == 200 and body[:4] == b"%PDF":
        return 200, body
    return (404 if code == 404 else 0), b""


def fetch(years, minutes=6):
    """The journals of the given years' floor days not yet read (the newest days first), for at most `minutes`."""
    from states.ct.fetch import ca_bundle
    ca_bundle()
    stop = time.time() + minutes * 60
    got = missing = 0
    for y in sorted(years, reverse=True):
        os.makedirs(folder(y), exist_ok=True)
        mpath = os.path.join(folder(y), "missing.json")
        try:
            miss = json.load(open(mpath))
        except (OSError, ValueError):
            miss = {}
        for h, day in sorted(floor_days(y), key=lambda x: x[1], reverse=True):
            name = f"{h}{day[5:7]}{day[8:10]}"
            path = os.path.join(folder(y), name + ".txt")
            if os.path.exists(path):
                continue
            if miss.get(name) == TODAY.isoformat() or date.fromisoformat(day) < TODAY - timedelta(days=RETRY_DAYS) and name in miss:
                continue
            if time.time() > stop:
                print(f"journals: out of time; the rest next run")
                return
            code, body = _get(url(h, day))
            if code == 200:
                r = subprocess.run(["pdftotext", "-layout", "-", "-"], input=body, capture_output=True)
                text = r.stdout.decode("utf-8", "replace")
                if "roll call" in text.lower() or "JOURNAL OF THE" in text:
                    with open(path + ".tmp", "w", encoding="utf-8") as f:
                        f.write(text)
                    os.replace(path + ".tmp", path)
                    miss.pop(name, None)
                    got += 1
                    continue
            if code == 404:
                miss[name] = TODAY.isoformat()
                missing += 1
        with open(mpath, "w") as f:
            json.dump(miss, f, indent=0, sort_keys=True)
    print(f"journals: {got} read, {missing} not posted (yet)")


# ---- reading them ---------------------------------------------------------------------------------------------------

HEADER = re.compile(r"^\s*(?:-\s*\d+\s*-|.*JOURNAL OF THE (?:HOUSE|SENATE).*)\s*$")
TOTAL = re.compile(r"Those (voting Yea|voting Nay|absent and not voting)\s*\.{3,}\s*(\d+)")
OUTCOME = re.compile(r"On (?:a|the) roll call vote,? (?:the )?(?:(?:Emergency Certified )?(House|Senate) (Bill|Joint Resolution)"
                     r" No\.\s*(\d+)|Consent Calendar( No\.\s*\d+)?)\b(.*?)\bwas\s+(passed|adopted|rejected|defeated|failed|not passed)",
                     re.I | re.S)
HEADING = re.compile(r"\s{0,6}[A-Z][A-Z ,&'-]+\.\s+(?:Substitute for |Emergency Certified )*([HS])\.\s?([BJ])\.\s?No\.\s?(\d{1,4})")
BILL_REF = re.compile(r"\b([HS])\.\s?([BJ])\.\s?No\.\s?(\d{1,4})\b")
VOTE_TOKEN = re.compile(r"([YNXA])\s+(\S.*)")


def grid(lines):
    """The roll call's [(vote letter, name)] from its grid lines, and the index of the first line after it (None if a
    line couldn't be read)."""
    out, i, ok, pending = [], 0, True, None
    while i < len(lines):
        line = lines[i]
        if not line.strip() or HEADER.match(line):
            i += 1
            continue
        # "VACANT" marks an empty seat (the House of 2025-02-24). A letter can stand alone on its line with its name on
        # the next ("Y" / "1 JOHN W. FONFARA", Senate Journal of 2025-03-05).
        # (A Senate seat empty at the time is its bare number, "21", in the Senate Journal of 2025-01-28.)
        toks = [t for t in re.split(r"\s{2,}", line.strip()) if t != "VACANT" and not t.isdigit()]
        if not toks:
            i += 1
            continue
        if re.search(r"[a-z]", line) or not toks or not (pending or any(
                t in ("Y", "N", "X", "A") or VOTE_TOKEN.fullmatch(t) for t in toks)):
            break
        for t in toks:
            if t in ("Y", "N", "X", "A"):
                if pending:
                    ok = False
                pending = t
            elif VOTE_TOKEN.fullmatch(t) and not pending:
                v, name = VOTE_TOKEN.fullmatch(t).groups()
                out.append((v, name.strip()))
            elif pending:
                out.append((pending, t.strip()))
                pending = None
            else:
                ok = False
        i += 1
    return out, i, ok and not pending


def parse(text):
    """Every bill roll call in one journal: [{"bill": "HB7083" or None, "consent": [bills] (a consent calendar's), "pass":
    bool, "yes", "no", "absent", "names": [(letter, name)], "ok": names add up to the totals}]. A consent calendar's vote
    takes every bill placed on a consent calendar since the day's last such vote: placed one at a time ("On motion of
    Senator Duff of the 25th, the bill was placed on the Consent Calendar No.1", after the bill's heading) or as a list
    ("the following bills ... were placed on the Consent Calendar No.1")."""
    lines = text.splitlines()
    out, pending, totals, collecting, heading = [], [], {}, False, None
    i = 0
    while i < len(lines):
        line = lines[i]
        hm = HEADING.match(line)
        if hm:
            heading = f"{hm.group(1)}{hm.group(2)}{int(hm.group(3))}"
        if collecting:
            indent = len(line) - len(line.lstrip())
            if line.strip() and not HEADER.match(line) and indent >= 10 and not re.search(r"[a-z]", line) \
                    and not BILL_REF.search(line):
                collecting = False  # a centered heading ends the list
            else:
                for h, k, n in BILL_REF.findall(line):
                    if f"{h}{k}{int(n)}" not in pending:
                        pending.append(f"{h}{k}{int(n)}")
        two = " ".join(x.strip() for x in lines[i:i + 2])
        if re.search(r"\bthe following (?:bills|matters)\b", line, re.I) and re.search(r"placed on the Consent", two, re.I):
            collecting = True
        elif re.search(r"\bthe bill\s+was\s+placed\s+on\s+the\s+Consent Calendar", two, re.I) \
                and heading and heading not in pending:
            pending.append(heading)
        t = TOTAL.search(line)
        if t:
            totals[t.group(1).split()[-1].lower()] = int(t.group(2))
            i += 1
            continue
        if re.search(r"On (?:a|the) roll call vote", line, re.I):
            # The sentence runs to "The following is the roll call vote:" (or a few lines).
            j, sent = i, []
            # (A page break can come between them: its blank lines, page number and running head are skipped.)
            while j < len(lines) and j < i + 16 and "following is the roll call" not in lines[j]:
                if lines[j].strip() and not HEADER.match(lines[j]):
                    sent.append(lines[j].strip())
                j += 1
            o = OUTCOME.search(" ".join(sent))
            if o and j < len(lines) and "following is the roll call" in lines[j]:
                names, k, ok = grid(lines[j + 1:])
                house, kind, num, cal, _, word = o.groups()
                yes, no, absent = totals.get("yea"), totals.get("nay"), totals.get("voting")
                counted = {v: sum(1 for x, _ in names if x == v) for v in "YNXA"}
                good = ok and yes is not None and (counted["Y"], counted["N"], counted["X"] + counted["A"]) == (yes, no, absent or 0)
                bill = f"{house[0]}{kind[0]}{int(num)}" if num else None
                # The sentence's house can be a slip ("Senate Bill No. 7004" under the heading "H.B. No. 7004" in the
                # Senate Journal of 2025-06-04): the bill heading above it, when its number is the same, wins.
                if bill and heading and heading != bill and re.sub(r"\D", "", heading) == num.lstrip("0") \
                        and heading[1] == bill[1]:
                    bill = heading
                consent = []
                if not num:
                    consent, pending, collecting = pending, [], False
                out.append({"bill": bill, "consent": consent,
                            "pass": word.lower() in ("passed", "adopted"), "yes": yes, "no": no, "absent": absent,
                            "names": names, "ok": good, "heading": heading})
                totals = {}
                i = j + 1 + k
                continue
        i += 1
    return out


def _key(s):
    return re.sub(r"[^A-Z]", "", s.upper())


def seat_finder(session):
    """A function (house, journal name) -> seat id ("H:14", "S:21") or None, from the year's legislator list."""
    from states.ct import convert as C

    def index(members):
        by = {}
        for h, name, d, _ in members.values():
            parts = name.split()
            last = [p for p in parts if not re.fullmatch(r"(?:Jr|Sr|II|III|IV)\.?", p)]
            # The surname may be two words ("Kavros DeGraw", "McCarthy Vahey"): each tail of the name is a candidate.
            for k in range(1, min(3, len(last))):
                by.setdefault((h, _key(" ".join(last[-k:]))), set()).add((d, parts[0][:1].upper()))
        return by

    # This year's list first; a member who left mid-session (Kevin Ryan of the 139th, 2025) is only in an earlier year's
    # (the list is the year's last), looked up there when this year's has no one of that name.
    lists = [index(C.legislators(y)) for y in (session, session - 1)]

    def find(h, name):
        if h == "S":
            m = re.match(r"(\d+)\s", name)
            return f"S:{int(m.group(1))}" if m else None
        sur, _, init = name.partition(",")
        for by in lists:
            hits = by.get((h, _key(sur)), set())
            if init.strip() and len(hits) > 1:
                hits = {x for x in hits if x[1] == _key(init)[:1]}
            if hits:
                return f"H:{next(iter(hits))[0]}" if len(hits) == 1 else None
        return None
    return find


_CONTRADICTED = []


def roll_calls(session):
    """bill -> [(house, day, pass, yes, no, [[seat or "H?Name", "N" or "A"]] or None when the names don't add up)]."""
    d = folder(session)
    if not os.path.isdir(d):
        return {}
    find = seat_finder(session)
    out = {}
    for f in sorted(os.listdir(d)):
        m = re.fullmatch(r"([HS])(\d\d)(\d\d)\.txt", f)
        if not m:
            continue
        h, day = m.group(1), f"{session}-{m.group(2)}-{m.group(3)}"
        for rc in parse(open(os.path.join(d, f), encoding="utf-8").read()):
            # A "was passed" under a tally that lost is another vote's grid (the Senate Journal of 2026-04-29 prints
            # SB 148's passage over an 11-21 grid that is a rejected amendment's): left out.
            if rc["pass"] and (rc["yes"] or 0) <= (rc["no"] or 0):
                _CONTRADICTED.append((session, h, day, rc["bill"]))
                continue
            listed = None
            if rc["ok"]:
                listed = []
                for v, name in rc["names"]:
                    if v == "Y":
                        continue
                    sid = find(h, name)
                    listed.append([sid or f"{h}?{re.sub(r'^\d+ ', '', name).title()}", "N" if v == "N" else "A"])
            entry = (h, day, rc["pass"], rc["yes"] or 0, rc["no"] or 0, listed, False)
            for b in ([rc["bill"]] if rc["bill"] else rc["consent"]):
                out.setdefault(b, []).append(entry)
            # The sentence's number can be a slip ("Senate Bill No. 247" under the heading "S.B. No. 274", Senate
            # Journal of 2026-04-14): the vote is offered to the heading's bill too, marked, for convert.py to take
            # only when the sentence's bill had no floor vote that day and the heading's did.
            if rc["bill"] and rc["heading"] and rc["heading"] != rc["bill"]:
                out.setdefault(rc["heading"], []).append(entry[:6] + (rc["bill"],))
    return out


if __name__ == "__main__":
    from states.ct import convert as C
    ys = [int(a) for a in sys.argv[1:]] or C.sessions()
    fetch(ys, minutes=60)
