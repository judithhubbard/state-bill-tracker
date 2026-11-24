"""Arizona's bills from the Legislature's own data service (apps.azleg.gov, read by states/az/fetch_azleg.py into
data/az/azleg_api/<year>/) in the shape convert.py reads from Open States' files: identifier, title, classification,
actions (each with its house and, here, the converter's own wording already decided: "_house", "_text"), sponsorships,
votes (member by member) and sources.

What the service gives that Open States' copy didn't:
- Every committee a bill was assigned to, by name, the day it was assigned, and each committee's action with its tally
  ("DP" 10-2, "DPA/SE" 4-3, Rules' "C&P"/"PFC"), so a bill held in committee says which one.
- The Committee of the Whole's action as what it is (its own line, never a passage: Open States listed its voice vote as
  "PASSED", the trap in CLAUDE.md), and the third-reading and final votes with each member's vote.
- The governor's action with its date and the chapter number.
A bill assigned to several committees in a house goes to them in order (DisplayOrder): the next one's referral is dated
when the one before reported it, so the page says which committee it's in now.
"""
import collections, json, os, re

from states.az import profile as P

ROOT = os.path.join(P.DATA, "azleg_api")
HOUSE = {"H": "House", "S": "Senate"}
ORG = {"H": "lower", "S": "upper", "G": "executive"}
# Action codes read only as their bare code (none of the cases below knew them), by kind: the data check lists them, so
# the first conference committee or veto override in this data is looked at, not quietly misread (convert.source_checks()).
UNKNOWN = collections.Counter()
FLOOR = {"COW", "THIRD", "FINAL", "CONCUR", "RECON", "OVERRIDE", "CONF", "CC", "REFUSE"}
PASS_CODE = re.compile(r"^(DP|DPA|C&P|PFC|PFCA|DPA/SE|DP/SE|DPA/SO|DPAA)\b", re.I)


def folder(year):
    return os.path.join(ROOT, str(year))


def complete(year):
    return os.path.exists(os.path.join(folder(year), "complete"))


def available(year):
    return os.path.isdir(os.path.join(folder(year), "bills"))


def day(s):
    return (s or "")[:10]


def full(s):
    return (s or "")[:19]


def _actions(d):
    """The record's history as Open States-shaped actions, with the converter's wording in "_text"."""
    num = d["Number"]
    origin = num[0]
    out = []

    def add(when, h, text, desc=None, **extra):
        if when:
            out.append({"date": full(when), "_house": h, "_text": text, "description": desc or text,
                        "organization": {"classification": ORG.get(h, "executive")}, **extra})
    add(d.get("PreFileDate"), origin, "Prefiled")
    for h in ("H", "S"):
        add(d.get(f"{HOUSE[h]}1stRead"), h, f"{HOUSE[h]} first reading")
        add(d.get(f"{HOUSE[h]}2ndRead"), h, f"{HOUSE[h]} second reading")
        add(d.get(f"{HOUSE[h]}ConsentCalendarDate"), h, f"Placed on the {HOUSE[h]} consent calendar")
    acts = d.get("BillStatusAction") or []
    # Committees, in each house in order: the first referral on its assignment day, each next one when the one before
    # reported the bill.
    for h in ("H", "S"):
        comms = sorted([a for a in acts if (a.get("Committee") or {}).get("LegislativeBody") == h
                        and (a.get("Committee") or {}).get("CommitteeShortName") not in FLOOR
                        and (a.get("Committee") or {}).get("TypeName") != "Floor"],
                       key=lambda a: (a.get("ReferralNumber") or 0, a.get("DisplayOrder") or 0))
        prev_report = None
        for i, a in enumerate(comms):
            c = a["Committee"]
            name = c.get("CommitteeName") or c.get("CommitteeShortName")
            when = a.get("AssignedDate") if i == 0 or (a.get("ReferralNumber") or 0) != (comms[i - 1].get("ReferralNumber") or 0) else prev_report
            if when is None and i > 0:
                # (The committee before hasn't reported it: it's still there.)
                break
            add(when, h, f"REFERRED TO {name.upper()}", f"Assigned to {name}")
            code = (a.get("Action") or "").strip()
            done = a.get("ReportDate") or a.get("ActionDatetime")
            tally = f" ({a['Ayes']}-{a['Nays']})" if (a.get("Ayes") or a.get("Nays")) else ""
            if not code or code.lower() == "none" or not done:
                prev_report = None
                continue
            if PASS_CODE.match(code):
                add(done, h, f"REPORTED|{name}|{code}", f"{code}{tally}",
                    related_entities=[{"entity_type": "organization", "name": name}])
                prev_report = done
            elif code.upper() == "W/D":
                # Taken out of the committee's hands: on to the next committee, or the floor (convert.py's place).
                add(done, h, f"Withdrawn from {name}", "W/D")
                prev_report = done
            else:
                word = {"HELD": "Held", "FAILED": "Failed", "FAIL": "Failed",
                        "S/E": "Strike-everything amendment in"}.get(code.upper(), code)
                if word == code:
                    UNKNOWN[f"committee {code}"] += 1
                add(done, h, f"{word} {name}{tally}" if word != code else f"{name}: {code}{tally}")
                prev_report = None
    # The floor: the Committee of the Whole (no roll call), the third reading and final votes, concurrence.
    for a in acts:
        c = a.get("Committee") or {}
        short, h = c.get("CommitteeShortName"), c.get("LegislativeBody")
        if short not in FLOOR or h not in HOUSE:
            continue
        code = (a.get("Action") or "").strip()
        when = a.get("ReportDate") or a.get("ActionDatetime") or a.get("AssignedDate")
        tally = f" ({a['Ayes']}-{a['Nays']})" if (a.get("Ayes") or a.get("Nays")) else ""
        if short in ("THIRD", "FINAL", "RECON", "OVERRIDE") and re.match(r"pass", code, re.I):
            add(when, h, f"PASSED {HOUSE[h].upper()}", f"{c.get('CommitteeName')}: passed{tally}", _id=a.get("BillStatusActionID"))
        elif short in ("THIRD", "FINAL", "RECON", "OVERRIDE") and re.match(r"fail", code, re.I):
            add(when, h, "FAILED", f"{c.get('CommitteeName')}: failed{tally}")
        elif short == "COW":
            words = {"DP": "do pass", "DPA": "do pass amended", "FAILED": "failed", "RETAINED": "retained on the calendar",
                     "RET ON CAL": "retained on the calendar"}
            # (The code as the description: a floor amendment in the second house ("DPA") means the first has to agree
            # again, convert.py's amended_by_other, as Open States' "DPA" lines did.)
            if code.upper() not in words:
                UNKNOWN[f"COW {code}"] += 1
            add(when, h, f"Committee of the Whole: {words.get(code.upper(), code)}", code)
        elif short == "CONCUR":
            them = HOUSE["S" if h == "H" else "H"]
            word = f"concurred in the {them}'s amendments" if re.match(r"pass|concur", code, re.I) else \
                   f"refused to concur in the {them}'s amendments" if re.match(r"refus", code, re.I) else f"concurrence: {code}"
            if word.startswith("concurrence:"):
                UNKNOWN[f"CONCUR {code}"] += 1
            add(when, h, f"{HOUSE[h]} {word}")
        elif code and code.lower() != "none":
            UNKNOWN[f"{short} {code}"] += 1
            add(when, h, f"{c.get('CommitteeName')}: {code}{tally}")
    for t in d.get("BodyTransmittedTo") or []:
        to = t.get("LegislativeBody")
        when = t.get("TransmitDate")
        if to == "G":
            add(when, "G", "DELIVERED TO GOVERNOR", "Transmitted to the Governor")
        elif to in HOUSE:
            add(when, "H" if to == "S" else "S", f"Transmitted to the {HOUSE[to]}")
        elif to:
            add(when, "G", "Transmitted to the Secretary of State, for the next general election ballot")
    gov = (d.get("GovernorAction") or "").strip()
    chap = f" (Chapter {d['ChapterNumber']})" if d.get("ChapterNumber") else ""
    if re.match(r"sign", gov, re.I):
        add(d.get("GovernorActionDate"), "G", "SIGNED", f"Signed by the Governor{chap}")
    elif re.match(r"veto", gov, re.I):
        add(d.get("GovernorActionDate"), "G", "VETOED", "Vetoed by the Governor")
    elif gov:
        UNKNOWN[f"governor {gov}"] += 1
        add(d.get("GovernorActionDate"), "G", f"Governor: {gov}{chap}")
    out.sort(key=lambda a: a["date"])
    for i, a in enumerate(out):
        a["order"] = i
    return out


def _votes(rec):
    """The roll calls, as Open States' votes: third readings and final votes, each member's vote."""
    d = rec["detail"]
    out = []
    heads = {str(h.get("BillStatusActionId")): h for h in d.get("FloorHeaders") or []}
    for aid, rows in (rec.get("votes") or {}).items():
        x = rows[0] if isinstance(rows, list) and rows else rows if isinstance(rows, dict) else None
        if not x:
            continue
        h = (heads.get(aid) or {}).get("LegislativeBody")
        if h not in HOUSE:
            continue
        passed = bool(re.match(r"pass", x.get("Action") or "", re.I))
        opt = {"Y": "yes", "N": "no", "NV": "not voting", "E": "excused", "A": "absent", "P": "present"}
        out.append({"organization": {"classification": ORG[h]}, "motion_classification": ["passage"],
                    "motion_text": "Passed" if passed else "Failed", "result": "pass" if passed else "fail",
                    "start_date": full(x.get("ReportDate") or (heads.get(aid) or {}).get("ActionDate")),
                    "counts": [{"option": "yes", "value": x.get("Ayes") or 0}, {"option": "no", "value": x.get("Nays") or 0},
                               {"option": "not voting", "value": x.get("NotVoting") or 0},
                               {"option": "excused", "value": x.get("Excused") or 0}],
                    "votes": [{"option": opt.get(v.get("Vote"), "other"), "voter_name": (v.get("Legislator") or {}).get("FullName") or "",
                               "voter": {}} for v in x.get("Votes") or []]})
    return out


def bill(rec, year):
    """One saved record -> an Open States-shaped bill."""
    d = rec["detail"]
    num = d["Number"]
    party = {"R": "Republican", "D": "Democratic", "I": "Independent"}
    spons = []
    for s in sorted(rec.get("sponsors") or [], key=lambda s: (s.get("SponsorType") != "Prime", s.get("DisplayOrder") or 0)):
        lg = s.get("Legislator") or {}
        spons.append({"name": lg.get("FullName") or "", "primary": s.get("SponsorType") == "Prime",
                      "person": {"party": party.get(lg.get("Party"), ""),
                                 "current_role": {"org_classification": ORG.get(lg.get("Body"), "")}}})
    title = (d.get("NOWTitle") or d.get("ShortTitle") or "").strip()
    return {"identifier": num, "title": title, "short_title": d.get("ShortTitle") or "",
            "classification": ["bill"] if num[:2] in ("HB", "SB") else ["concurrent resolution"],
            "actions": _actions(d), "sponsorships": spons, "votes": _votes(rec),
            "sources": [{"url": f"https://apps.azleg.gov/BillStatus/BillOverview/{d['BillId']}?SessionId={d.get('SessionId')}"}],
            "chapter": d.get("ChapterNumber"), "_azleg": True}


def bills(year):
    """Every saved record of a session, Open States-shaped."""
    out = []
    base = os.path.join(folder(year), "bills")
    for f in sorted(os.listdir(base)) if os.path.isdir(base) else []:
        if f.endswith(".json"):
            try:
                with open(os.path.join(base, f), encoding="utf-8") as fh:
                    out.append(bill(json.load(fh), year))
            except (OSError, ValueError, KeyError):
                continue
    return out


def fetched_mtime(year):
    base = os.path.join(folder(year), "bills")
    ts = [os.path.getmtime(os.path.join(base, f)) for f in os.listdir(base)] if os.path.isdir(base) else []
    return max(ts, default=None)
