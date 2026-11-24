"""The Council's own records (LIMS, downloaded by states/dc/fetch_lims.py into data/dc/lims/<period>/) in the shape
states/dc/convert.py reads LegiScan's in, so one converter serves both: each bill as LegiScan writes it ("bill_number",
"bill_type", "title", "description", "history" [{date, action}], "sponsors" [{name, people_id, sponsor_order}],
"state_link") plus its roll calls ("_calls": [{date, desc, yea, nay, votes: [{people_id, vote_text}]}]).

- The list (bulk.json) gives every bill's history in LIMS's own wording (LegiScan copies the same lines), its act and law
  numbers and its kind ("Permanent Bill", "Emergency Bill", "Temporary Bill", "Congressional Review Emergency Bill").
- Each permanent bill's details (details/<number>.json) give the introducers, co-introducers and co-sponsors ("Allen,
  Charles"; listed in that order, the first introducer as the sponsor), the Secretary's abstract ("BILL SUMMARY - As
  introduced, ..." in `additionalInformation`, LegiScan's `description` without the label), and each meeting action's
  vote, member by member ("Roll Call" and "Voice Vote" alike: a voice vote records who said no).
- A bill whose details haven't been read yet takes its sponsors from the list's "introducedBy" ("Councilmember R. White",
  "Chairman Mendelson at the request of the Mayor") and has no votes until they are.
People are keyed by `name_key()` ("robert white"); names are written "First Last" from the period's member list (as
LegiScan writes them: "Robert White", "Kenyan McDuffie"), so the pages read the same.
"""
import json, os, re
from datetime import datetime
from zoneinfo import ZoneInfo

from fetch_contacts import name_key
from states.dc import profile as P

ROOT = os.path.join(P.DATA, "lims")
MONTHS = {m: i for i, m in enumerate("jan feb mar apr may jun jul aug sep oct nov dec".split(), 1)}
_CACHE = {}


def available():
    """{first year: folder} for the periods whose first copy is whole (a bill list, and every permanent bill's details:
    fetch_lims.py's meta "whole"; until then the build keeps reading LegiScan's copy)."""
    out = {}
    if os.path.isdir(ROOT):
        for name in os.listdir(ROOT):
            if name.isdigit() and os.path.exists(os.path.join(ROOT, name, "bulk.json")) and \
                    (_load(os.path.join(ROOT, name, "meta.json"), {}) or {}).get("whole"):
                out[2025 + (int(name) - 26) * 2] = os.path.join(ROOT, name)
    return dict(sorted(out.items()))


def ready():
    """True when every period downloaded has its whole first copy (so the pages never mix LIMS and LegiScan)."""
    started = [n for n in (os.listdir(ROOT) if os.path.isdir(ROOT) else []) if n.isdigit() and os.path.exists(os.path.join(ROOT, n, "bulk.json"))]
    return bool(started) and len(available()) == len(started)


def _load(path, default=None):
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def iso(s):
    """"Jan 06, 2025" or "2025-01-06T00:00:00" -> "2025-01-06"."""
    s = (s or "").strip()
    if re.match(r"\d{4}-\d\d-\d\d", s):
        return s[:10]
    m = re.match(r"([A-Za-z]{3})[a-z]*\.? (\d{1,2}),? (\d{4})", s)
    return f"{m.group(3)}-{MONTHS[m.group(1).lower()]:02d}-{int(m.group(2)):02d}" if m and m.group(1).lower() in MONTHS else ""


def members(folder):
    """name_key -> "First Last", from the period's member list."""
    out = {}
    for m in _load(os.path.join(folder, "members.json"), []) or []:
        name = re.sub(r"\s+", " ", f"{(m.get('firstName') or '').strip()} {(m.get('lastName') or '').strip()}").strip()
        if name:
            out[name_key(m.get("name") or name)] = name
            out.setdefault(name_key(name), name)
    return out


def flip(name):
    """"White, Robert C. Jr." -> "Robert C. Jr. White"; "Robert C. White, Jr." stays."""
    name = re.sub(r"\s+", " ", name or "").strip()
    m = re.match(r"([^,]+),\s*(.+)$", name)
    if m and not re.fullmatch(r"(?:Jr|Sr|II|III|IV)\.?", m.group(2).strip(), re.I):
        return f"{m.group(2)} {m.group(1)}"
    return name


def person(name, mem):
    """(key, display name) for a name as LIMS writes it."""
    k = name_key(flip(name))
    return k, mem.get(k) or re.sub(r",?\s+(?:Jr|Sr)\.?$", "", flip(name)).strip()


def from_list(text, mem):
    """The list's "introducedBy" -> [(key, name)]: "Councilmember R. White", "Councilmembers Nadeau and Allen", "Chairman
    Mendelson at the request of the Mayor"."""
    t = re.sub(r"\bat the request of .*$", "", text or "", flags=re.I)
    t = re.sub(r"\b(?:Councilmembers?|Chairman|Chairperson|Chair)\b", "", t)
    out = []
    for part in re.split(r",|\band\b", t):
        part = part.strip(" .")
        if not part:
            continue
        m = re.match(r"(?:([A-Z])\.\s*)?(.+)$", part)
        initial, last = m.group(1), m.group(2).strip()
        hits = [(k, n) for k, n in mem.items() if n.split()[-1].lower() == last.split()[-1].lower()
                and (not initial or n[0] == initial) and (len(last.split()) == 1 or n.lower().endswith(last.lower()))]
        hits = list(dict.fromkeys(hits))
        if len({n for _, n in hits}) == 1:
            out.append(hits[0])
        elif part:
            out.append((name_key(part), part))
    return out


def bills(folder):
    """The period's bills, LegiScan-shaped, with their roll calls."""
    if folder in _CACHE:
        return _CACHE[folder]
    mem = members(folder)
    out = []
    for e in _load(os.path.join(folder, "bulk.json"), []) or []:
        n = e.get("legislationNumber") or ""
        d = _load(os.path.join(folder, "details", n + ".json")) if e.get("legislationSubCategory") == "Permanent Bill" else None
        hist = [{"date": iso(h.get("actionDate")), "action": re.sub(r"\s+", " ", h.get("actionDescription") or "").strip()}
                for h in e.get("legislationHistory") or []]
        b = {"bill_number": n, "bill_type": "B" if re.match(r"B\d+-\d+$", n) else "",
             "kind": e.get("legislationSubCategory") or "", "title": re.sub(r"(\d{4})\.\s*$", r"\1", (e.get("title") or "").strip()),
             "history": [h for h in hist if h["date"]], "state_link": f"https://lims.dccouncil.gov/Legislation/{n}",
             "act": e.get("actResNumber") or "", "law": e.get("lawNumber") or "", "status": e.get("status") or "",
             "description": "", "sponsors": [], "_calls": [], "_details": bool(d)}
        people = []
        if d:
            # The committee's reports, from its mark-ups: LIMS's list writes only "Committee Mark-up of B26-0164 by the
            # Housing Committee"; the details give each mark-up's print and report and the day the report was filed, which
            # LegiScan's copies show as "Committee Report Filed" lines. A mark-up with neither print nor report (B25-0743,
            # September 17, 2024, then "Agendized; not considered") wasn't the committee's approval: `_markups`.
            b["_markups"] = {}
            # (Only reports within the bill's own history: the budget acts' details also list the committees' reports on
            # later years' budgets, B25-0785's filed in 2026.)
            span = [h["date"] for h in b["history"]]
            for mk in d.get("committeeMarkup") or []:
                day = iso(mk.get("committeeActionDate"))
                done = bool(mk.get("committeePrint") or mk.get("committeeReport") or mk.get("reportFiledDate"))
                if day:
                    b["_markups"][day] = b["_markups"].get(day, False) or done
                filed = iso(mk.get("reportFiledDate"))
                if filed and span and min(span) <= filed <= max(span) and not any(h["date"] == filed and h["action"].startswith("Committee Report Filed") for h in b["history"]):
                    b["history"].append({"date": filed, "action": "Committee Report Filed"})
            b["history"].sort(key=lambda h: h["date"])
            for group in ("introducers", "coIntroducers", "coSponsors"):
                for p in d.get(group) or []:
                    # (A voters' initiative names "Voters", with no title, as its introducer: B25-1075; LegiScan none.)
                    if p.get("memberTitle") or person(p.get("memberName"), mem)[0] in mem:
                        people.append(person(p.get("memberName"), mem))
            info = (d.get("additionalInformation") or d.get("shortDescription") or "").replace("\r", "")
            # (The summary often follows a referral note: "The Chairman is referring this legislation sequentially ...
            # BILL SUMMARY - As introduced Bill 26-58 would ...".)
            b["description"] = re.sub(r"^\s*BILL SUMMARY\s*[-:–]\s*", "", info, flags=re.M)
            for a in d.get("actions") or []:
                vd = a.get("voteDetails") or {}
                vs = vd.get("votes") or []
                if not vs:
                    continue
                votes = []
                for v in vs:
                    k, name = person(v.get("councilMember"), mem)
                    choice = (v.get("vote") or "").strip()
                    votes.append({"people_id": k, "name": name,
                                  "vote_text": "Yea" if choice == "Yes" else "Nay" if choice == "No" else choice or "Absent"})
                b["_calls"].append({"date": iso(a.get("actionDate")), "desc": re.sub(r"\s+", " ", a.get("action") or "").strip(),
                                    "yea": sum(1 for v in votes if v["vote_text"] == "Yea"),
                                    "nay": sum(1 for v in votes if v["vote_text"] == "Nay"),
                                    "type": vd.get("voteType") or "", "result": vd.get("voteResult") or "", "votes": votes})
        else:
            people = from_list(e.get("introducedBy"), mem)
        seen = set()
        for i, (k, name) in enumerate(people, 1):
            if k in seen:
                continue
            seen.add(k)
            b["sponsors"].append({"people_id": k, "name": name, "sponsor_order": i})
        out.append(b)
    _CACHE[folder] = out
    return out


def people(folder):
    """people_id (name_key) -> {"name"} for everyone named in the period's records."""
    out = {k: {"name": n} for k, n in members(folder).items()}
    for b in bills(folder):
        for s in b["sponsors"]:
            out.setdefault(s["people_id"], {"name": s["name"]})
        for c in b["_calls"]:
            for v in c["votes"]:
                out.setdefault(v["people_id"], {"name": v["name"]})
    return out


def fetched(folder, tz):
    meta = _load(os.path.join(folder, "meta.json"), {}) or {}
    t = max([meta.get("bulk") or 0] + [x[1] for x in (meta.get("details") or {}).values() if isinstance(x, list) and len(x) > 1])
    return datetime.fromtimestamp(t, ZoneInfo(tz)).strftime("%Y-%m-%d %H:%M") if t else ""
