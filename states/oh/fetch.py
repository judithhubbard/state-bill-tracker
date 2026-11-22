#!/usr/bin/env python3
"""Download Ohio's bills from the Legislative Service Commission's API (https://search-prod.lis.state.oh.us/api/v2/; see
the oh-data-sources memory: the legislature's, House's and Senate's websites turn automated requests away, the API
doesn't).

- Each General Assembly's legislation list (one call: every bill with its sponsors, co-sponsors and subjects); House
  and Senate bills, and the joint resolutions that propose constitutional amendments (short titles "CA: ..."; not the
  ones applying to Congress for a convention or confirming an appointment). Other resolutions are left out.
- For each bill, into data/oh/<session>/bills/<HB1>.json: its versions (as introduced, as reported, as passed, as
  enrolled: titles, dates sent to and signed by the governor) and its actions (each with its votes, member by member).
  Versions are read again when the bill's entry in the list changes, its actions change, or it waits on enrollment or
  the governor (the entry's revno doesn't change for either); the current General Assembly's actions every run
  (an action like a referral doesn't change the list); a finished one's once. Three requests at a time.
- The legislators, committees with their members, and the next three weeks' committee meetings (agendas).
- Legislators' emails aren't in the API: Open States' public-domain file (data.openstates.org, copied from the
  official sites), decided 2026-10-31.
Usage: python3 states/oh/fetch.py [first_year]   (default 2021)
"""
import json, os, re, sys, time, urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
from states.oh import profile as P

API = "https://search-prod.lis.state.oh.us/api/v2"
PEOPLE = "https://data.openstates.org/people/current/oh.csv"
FIRST = int(sys.argv[1]) if len(sys.argv) > 1 else 2021
TODAY = datetime.now(ZoneInfo(P.TIMEZONE)).date()
CURRENT = P.session_of(TODAY.year)
AGENT = "statebilltracker.org (a nonprofit bill tracker; contact via github.com/judithhubbard)"
INCOMPLETE = set()


def get(url, raw=False):
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": AGENT, "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=120) as r:
                body = r.read()
            return body if raw else json.loads(body)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            time.sleep(5 * (attempt + 1))
        except Exception:
            time.sleep(5 * (attempt + 1))
    return False  # failed


def save(path, data):
    json.dump(data, open(path + ".tmp", "w"), ensure_ascii=False)
    os.replace(path + ".tmp", path)


def wanted(i):
    """A House or Senate bill, or a joint resolution proposing a constitutional amendment ("CA: Require 60% vote ...")."""
    num = i.get("number", "")
    if num[:2] in ("hb", "sb") and num[2:].isdigit():
        return True
    return num[:3] in ("hjr", "sjr") and num[3:].isdigit() and bool(re.match(r"CA\s*:", i.get("short_title") or ""))


def waiting(versions, actions):
    """Whether a bill has passed both houses (or one house agreed to the other's changes) and the governor's decision
    isn't in yet: no signing or effective date on the enrolled version, no veto receipt."""
    acts = [a.get("action") or "" for a in actions]
    if any(re.search(r"veto receipt", a, re.I) for a in acts):
        return False
    en = next((v for v in versions if v.get("version_id") == "EN"), None)
    if en and (en.get("governor_signed_date") or en.get("effective_date")):
        return False
    houses = {a.get("chamber") for a in actions if re.match(r"Passed", a.get("action") or "")}
    return bool(en) or len(houses) == 2 or any(re.match(r"Concurred|Conference report agreed", a) for a in acts)


def session(session):
    ga = P.assembly_of(session)
    base = f"{API}/general_assembly_{ga}"
    folder = os.path.join(P.DATA, str(session))
    os.makedirs(os.path.join(folder, "bills"), exist_ok=True)
    items = get(f"{base}/legislation/")
    if not items:
        print(f"{session}: no legislation list (the API didn't answer, or no bills yet); kept the last copy")
        # Only a list never read holds the state off, and not a new General Assembly's in its first two months (the
        # API answers 500 for one it hasn't set up, and bills are introduced only after it convenes).
        if not os.path.exists(os.path.join(folder, "legislation.json")) \
                and not (session == CURRENT and TODAY < TODAY.replace(year=session, month=3, day=1)):
            INCOMPLETE.add(session)
        return
    bills = {i["number"].upper(): i for i in items if wanted(i)}
    save(os.path.join(folder, "legislation.json"), list(bills.values()))
    path = os.path.join(folder, "revs.json")
    try:
        revs = json.load(open(path))
    except (OSError, ValueError):
        revs = {}
    live = session >= CURRENT
    # The General Assembly just ended, until April: its last bills reach the governor in January, and the list's revno
    # may not change for that, so bills still waiting on enrollment or the governor are read again.
    ending = session == CURRENT - 2 and TODAY < TODAY.replace(year=CURRENT, month=4, day=1)

    def one(b):
        f = os.path.join(folder, "bills", f"{b}.json")
        old = json.load(open(f)) if os.path.exists(f) else None
        rev = str(bills[b].get("revno"))
        if old and not live and revs.get(b) == rev \
                and not (ending and waiting(old["versions"], old.get("actions") or [])):
            return b, True  # a finished General Assembly's bill, unchanged
        actions = get(f"{base}/legislation/{b.lower()}/actions/")
        # The list's revno doesn't change when a bill is enrolled or sent to the governor (HB 13 of the 136th: enrolled
        # and sent 2026-11-17, revno unchanged since its Senate committee report), so versions are read again when the
        # entry changes, when the actions changed, or while the bill waits on enrollment or the governor.
        fresh = old and revs.get(b) == rev and actions is not False and actions == old.get("actions") \
            and not waiting(old["versions"], old.get("actions") or [])
        versions = old["versions"] if fresh else get(f"{base}/legislation/{b.lower()}/")
        if versions is False:
            return b, False
        if actions is False:
            # The server fails on a few bills' actions every time (HB 178 of the 134th): keep the last copy, else the
            # versions alone, marked, so one broken record doesn't hold up the whole download.
            if old and old.get("actions"):
                actions = old["actions"]
            else:
                save(f, {"versions": versions or [], "actions": [], "actionsMissing": True})
                return b, True
        save(f, {"versions": versions or [], "actions": actions or []})
        return b, True

    got = 0
    with ThreadPoolExecutor(3) as pool:
        for k, (b, ok) in enumerate(pool.map(one, sorted(bills))):
            if ok:
                revs[b] = str(bills[b].get("revno"))
                got += 1
            if k % 300 == 299:
                save(path, revs)
    save(path, revs)
    # A bill whose refresh failed keeps its last copy (and is asked again next run); only bills never read count.
    if any(not os.path.exists(os.path.join(folder, "bills", f"{b}.json")) for b in bills):
        INCOMPLETE.add(session)
    print(f"{session}: {got} of {len(bills)} bills read")

    # Legislators and committees (with members for the current General Assembly).
    for name in ("legislators", "committees"):
        data = get(f"{base}/{name}/")
        if data:
            save(os.path.join(folder, f"{name}.json"), data)
    if live and os.path.exists(os.path.join(folder, "committees.json")):  # a new General Assembly's may not be listed yet
        members = {}
        for c in json.load(open(os.path.join(folder, "committees.json"))):
            m = get(f"https://search-prod.lis.state.oh.us{c['link']}members/") if c.get("link") else None
            if m:
                members[c["lpid"]] = m
        save(os.path.join(folder, "committee_members.json"), members)


def agendas(session):
    """Bills on committee agendas from yesterday to three weeks ahead: bill -> [["House Finance", "2026-01-20T09:30"], ...].
    Each meeting's agenda summary lists its bills ("H. R. No. 14, H. B. No. 148")."""
    base = f"{API}/general_assembly_{P.assembly_of(session)}"
    try:
        names = {c["lpid"]: f"{c['chamber']} {c['name']}" for c in json.load(open(os.path.join(P.DATA, str(session), "committees.json")))}
    except (OSError, ValueError):
        names = {}
    out, n, last = {}, 0, (TODAY + timedelta(days=21)).isoformat()
    for house in ("house", "senate"):
        meets = get(f"{base}/committees/meetings/{house}/{(TODAY - timedelta(days=1)).isoformat()}") or []
        for m in meets:
            when = m.get("meeting_date") or ""
            if m.get("canceled") or not when or when > last:
                continue
            n += 1
            name = names.get(m.get("committee_lpid"), house.title())
            for kind, jr, num in re.findall(r"\b([HS])\. (B|J\. R)\. No\. (\d+)", m.get("agenda_summary") or ""):
                key = f"{kind}{'JR' if jr != 'B' else 'B'}{num}"
                entry = [name, f"{when}T{m.get('meeting_time') or '00:00'}"]
                if entry not in out.setdefault(key, []):
                    out[key].append(entry)
    save(os.path.join(P.DATA, str(session), "agendas.json"), out)
    print(f"agendas: {len(out)} bills on {n} meetings")


def people():
    body = get(PEOPLE, raw=True)
    if body and body.startswith(b"id,"):
        open(os.path.join(P.DATA, "openstates_people.csv"), "wb").write(body)


def begun(session):
    """Whether a General Assembly has convened (the first Monday of January of its first year)."""
    jan = TODAY.replace(year=session, month=1, day=1)
    return TODAY >= jan.replace(day=1 + (0 - jan.weekday()) % 7)


def main():
    os.makedirs(P.DATA, exist_ok=True)
    for s in range(FIRST, CURRENT + 1, 2):
        session(s)
    agendas(CURRENT)
    people()
    marker = os.path.join(P.DATA, "incomplete")
    # A General Assembly not yet begun (no bills listed yet) is read when it's there but never holds Ohio back.
    undone = {s for s in INCOMPLETE if begun(s)}
    if undone:
        open(marker, "w").write(" ".join(map(str, sorted(undone))) + "\n")
        print(f"not complete yet: {sorted(undone)}")
    elif os.path.exists(marker):
        os.remove(marker)


if __name__ == "__main__":
    main()
    from states.oh import contacts  # the legislators, committees and Open States' emails just downloaded
    # A new General Assembly's contacts once its legislators and committees are listed (until then the last file stands).
    if all(os.path.exists(os.path.join(P.DATA, str(CURRENT), f"{n}.json")) for n in ("legislators", "committees")):
        contacts.main(CURRENT)
    from states.oh import texts  # "What it does", from the long titles
    texts.main()
