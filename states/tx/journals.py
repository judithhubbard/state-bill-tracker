#!/usr/bin/env python3
"""How each member voted on the House floor, from the House Journal (journals.house.texas.gov): each record vote reads
"(Record 212): 124 Yeas, 18 Nays, 1 Present, not voting. Yeas — Alders; Allen; ... Nays — Bumgarner; ... Absent — ...".
The bill histories give each bill's record vote numbers ("Record vote", "RV#92"), so convert.py can attach them.

Each legislative day's journal is a file (89RDAY45FINAL.HTM); days are read until the files run out. A finished
session's journals don't change, so they're downloaded once (data/tx/<code>/journals/); the current session's last
few days are read again each run. Writes data/tx/<code>/house_votes.json: {"212": {"Y": [...], "N": [...], "P": [...],
"A": [...]}} with members as the journal names them ("Bell, C.", "Wu").

The Senate Journal has no record numbers: senate() reads each day's journal (see below) and ties votes to bills by
the headings.
Usage: python3 states/tx/journals.py [session]   (fetch.py runs it for every session)
"""
import html, json, os, re, subprocess, sys, time
from datetime import datetime
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
from states.tx import profile as P

URL = "https://journals.house.texas.gov/hjrnl/{code}/html/{CODE}DAY{day:02d}FINAL.HTM"
CURRENT = P.session_of(datetime.now(ZoneInfo(P.TIMEZONE)).year)
LABELS = {"Yeas": "Y", "Nays": "N", "Present, not voting": "P"}


def fetch(code, day, path):
    r = subprocess.run(["curl", "-sS", "-w", "%{http_code}", "-o", path + ".tmp", "--max-time", "120",
                        URL.format(code=code.lower(), CODE=code, day=day)], capture_output=True, text=True)
    if r.stdout.strip() == "200":
        os.replace(path + ".tmp", path)
        return True
    if os.path.exists(path + ".tmp"):
        os.remove(path + ".tmp")
    return False


def votes(text):
    """Record number -> {"Y": [...], "N": [...], "P": [...], "A": [...]} for one day's journal text."""
    out = {}
    recs = list(re.finditer(r"\(Record (\d+)\):\s*(\d+) Yeas?,\s*(\d+) Nays?", text))
    for k, m in enumerate(recs):
        seg = text[m.end():recs[k + 1].start() if k + 1 < len(recs) else m.end() + 8000][:8000]
        v = {"Y": [], "N": [], "P": [], "A": []}
        for label, body in re.findall(r"(Yeas|Nays|Present, not voting|Absent(?:, Excused)?(?:, Committee Meeting)?) — (.*?)(?=\. (?:Yeas|Nays|Present|Absent)|\.\s|$)", seg):
            key = LABELS.get(label, "A")
            names = [n.strip() for n in body.split(";") if n.strip()]
            if not v[key] or key == "A":
                v[key] += [n for n in names if n not in v[key]]
        out[m.group(1)] = v
    return out


def main(session):
    code = P.code_of(session)
    folder = os.path.join(P.DATA, code, "journals")
    os.makedirs(folder, exist_ok=True)
    out_path = os.path.join(P.DATA, code, "house_votes.json")
    day, misses, got = 1, 0, 0
    while misses < 6:
        path = os.path.join(folder, f"DAY{day:02d}.HTM")
        # A day already here is kept, except the current session's latest days, which can still be corrected.
        recent = session >= CURRENT and not os.path.exists(os.path.join(folder, f"DAY{day + 3:02d}.HTM"))
        if os.path.exists(path) and not recent:
            misses = 0
        elif fetch(code, day, path):
            misses, got = 0, got + 1
            time.sleep(0.3)
        else:
            misses += 1
        day += 1
    allv = {}
    for f in sorted(os.listdir(folder)):
        if f.endswith(".HTM"):
            raw = open(os.path.join(folder, f), encoding="cp1252", errors="replace").read()
            text = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", raw)))
            allv.update(votes(text.replace("Mr. Speaker", "Speaker")))
    json.dump(allv, open(out_path, "w"), ensure_ascii=False)
    print(f"{code}: {len(allv)} House record votes ({got} journal days downloaded now)")


# ---- The Senate Journal: one file per day (89RSJ05-19-F.HTM). Each bill's consideration has a heading ("HOUSE BILL 12
# ON THIRD READING", "SENATE BILL 3 WITH HOUSE AMENDMENTS"), then "was passed by the following vote: Yeas 25, Nays 6."
# with the exceptions by name ("Nays: Alvarado, Cook." "Absent-excused: King."), or "(Same as previous roll call)".
SURL = "https://journals.senate.texas.gov/sjrnl/{code}/html/{CODE}SJ{md}-F.HTM"
HEAD = re.compile(r"(?:COMMITTEE SUBSTITUTE )?(SENATE|HOUSE) BILL (\d+) (ON (?:SECOND|THIRD) READING|WITH HOUSE AMENDMENTS?|WITH SENATE AMENDMENTS?|CONFERENCE COMMITTEE REPORT|ON .{0,40}?MOTION)"
                  r"|(CONFERENCE COMMITTEE REPORT) ON (?:COMMITTEE SUBSTITUTE )?(SENATE|HOUSE) BILL (\d+)")
VOTE = re.compile(r"([^.]{0,160}?) by the following vote: Yeas (\d+), Nays (\d+)\.")
# A list ends at the next label or a new sentence (not at an initial: "A. Hinojosa, J. Hinojosa").
LIST = re.compile(r"\s*(Yeas|Nays|Present-not voting|Absent-excused|Absent): ([^:]*?)\.(?=\s+(?:Yeas|Nays|Present-not voting|Absent-excused|Absent):|\s+(?:The|On|Senator|Question|Pursuant|[A-Z]{2,})\b|\s*\(|\s*$)")


def senate_day(text):
    """[(bill, kind, yes, no, {"N": [...], "P": [...], "A": [...]})] for one day's Senate Journal text. Every vote is
    read in order (motions too), since "(Same as previous roll call)" means the vote just before."""
    out, last = [], {"N": [], "P": [], "A": []}
    heads = list(HEAD.finditer(text))
    for k, h in enumerate(heads):
        house, number, what = (h.group(1), h.group(2), h.group(3)) if h.group(1) else (h.group(5), h.group(6), h.group(4))
        bill = ("SB" if house == "SENATE" else "HB") + number
        kind = "third" if "THIRD" in what else "second" if "SECOND" in what else "conference" if "CONFERENCE" in what else "concur"
        seg = text[h.end():heads[k + 1].start() if k + 1 < len(heads) else h.end() + 20000]
        for m in VOTE.finditer(seg):
            rest = seg[m.end():m.end() + 3000]
            if rest.lstrip().startswith("(Same as previous roll call)"):
                v = {x: list(y) for x, y in last.items()}
            else:
                v, pos = {"N": [], "P": [], "A": []}, 0
                while True:
                    lm = LIST.match(rest, pos)
                    if not lm:
                        break
                    if lm.group(1) != "Yeas":
                        key = "N" if lm.group(1) == "Nays" else "P" if lm.group(1).startswith("Present") else "A"
                        v[key] += [n.strip() for n in lm.group(2).split(",") if n.strip()]
                    pos = lm.end()
                last = v
            before = m.group(1)
            final = re.search(r"was (?:finally )?passed$|was passed$|finally passed$", before.strip()) and kind == "third"
            # Agreeing to the House's changes reads "moved to concur in the House amendments ... The motion prevailed".
            concur = kind == "concur" and re.search(r"concurred|adopted|motion prevailed", before) and \
                re.search(r"moved to concur|concur in the House amendment", seg[:m.start()])
            if final or (kind == "second" and "passed" in before) or concur or (kind == "conference" and re.search(r"adopted|prevailed", before)):
                out.append((bill, kind, int(m.group(2)), int(m.group(3)), v))
    return out


def local_calendar(text):
    """Bills passed on the Local and Uncontested Calendar: each is listed with its caption and tallies, the last one
    final passage ("SB 292 (Schwertner) Relating to ... (viva voce vote) (29-1) "Nay" Bettencourt (29-1) "Nay"
    Bettencourt"). Members on leave are named once ("Senator King was previously granted a leave of absence")."""
    out = []
    for sec in re.finditer(r"LOCAL AND UNCONTESTED CALENDAR(.*?)(?:Local and Uncontested Calendar (?:was concluded|Session was concluded)|$)", text):
        body = sec.group(1)
        away = re.findall(r"Senators? ((?:[A-Z]\. )?[A-Z][\w'-]+(?:(?:,| and) (?:[A-Z]\. )?[A-Z][\w'-]+)*) (?:was|were) previously granted (?:a )?leaves? of absence", body)
        absent = [n.strip() for a in away for n in re.split(r",\s*|\s+and\s+", a) if n.strip()]
        items = list(re.finditer(r"(?:CS)?(SB|HB) (\d+) \(", body))
        for k, it in enumerate(items):
            entry = body[it.start():items[k + 1].start() if k + 1 < len(items) else len(body)]
            tallies = list(re.finditer(r"\((\d+)-(\d+)\)(?:\s*\"Nays?\"\s*((?:[A-Z]\. )?[A-Z][\w'-]+(?:,\s*(?:[A-Z]\. )?[A-Z][\w'-]+)*))?", entry))
            if not tallies:
                continue
            t = tallies[-1]
            nays = [n.strip() for n in (t.group(3) or "").split(",") if n.strip()]
            out.append((it.group(1) + it.group(2), "third", int(t.group(1)), int(t.group(2)), {"N": nays, "P": [], "A": list(absent)}))
    return out


def senate(session, dates):
    """Senate floor votes for the days given (from the bill histories' Senate record votes)."""
    code = P.code_of(session)
    folder = os.path.join(P.DATA, code, "journals", "senate")
    os.makedirs(folder, exist_ok=True)
    got, out = 0, {}
    for d in sorted(dates):
        # A date with two legislative days has a second journal, "...SJ04-12-F1.HTM".
        for extra in ("", "1", "2", "3"):
            md = d[5:]
            path = os.path.join(folder, f"{md}{'-' + extra if extra else ''}.HTM")
            recent = session >= CURRENT and d >= max(dates)
            if not os.path.exists(path) or recent:
                miss = path + ".none"
                if extra and os.path.exists(miss) and not recent:
                    break  # looked for before: there's no such file
                r = subprocess.run(["curl", "-sS", "-w", "%{http_code}", "-o", path + ".tmp", "--max-time", "120",
                                    SURL.format(code=code.lower(), CODE=code, md=md) .replace("-F.HTM", f"-F{extra}.HTM")],
                                   capture_output=True, text=True)
                time.sleep(0.3)
                if r.stdout.strip() == "200":
                    os.replace(path + ".tmp", path)
                    got += 1
                else:
                    if os.path.exists(path + ".tmp"):
                        os.remove(path + ".tmp")
                    if extra:
                        open(miss, "w").close()
                    break
            raw = open(path, encoding="cp1252", errors="replace").read()
            text = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", raw)))
            for bill, kind, yes, no, v in senate_day(text) + local_calendar(text):
                if [kind, yes, no, v] not in [x[1:] for x in out.get(bill, [])]:
                    out.setdefault(bill, []).append([d, kind, yes, no, v])
    json.dump(out, open(os.path.join(P.DATA, code, "senate_votes.json"), "w"), ensure_ascii=False)
    print(f"{code}: Senate floor votes on {len(out)} bills ({got} journal days downloaded now)")


def senate_dates(session):
    """Days with Senate floor votes in the bill histories, and each next day (a journal can be dated a day later)."""
    from datetime import date, timedelta
    from states.tx.convert import bills
    days = {d for b in bills(session).values() for d, h, n, desc, c in b["actions"] if h == "S" and n in (576, 577, 625, 626) and d}
    return days | {(date.fromisoformat(d) + timedelta(1)).isoformat() for d in days}


if __name__ == "__main__":
    for s in (map(int, sys.argv[1:]) if len(sys.argv) > 1 else [CURRENT]):
        main(s)
        senate(s, senate_dates(s))
