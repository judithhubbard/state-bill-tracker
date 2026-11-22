"""Who is governor (or President) on a day, and who takes over next.

Each state's profile.py lists its governors with the day each took office (GOVERNORS = [(surname, "YYYY-MM-DD"), ...]);
a governor-elect goes on that list ahead of time, dated the day they take office, so the site switches by itself on that
day. Nothing may read the list's last entry as "the governor now": ask in_office(). states/legislatures.json holds the
full name and party (`governor`), and the governor-elect's (`governorNext`: [full name, party, "YYYY-MM-DD"]) until
that day: facts_governor() picks the one in office.
"""
import datetime


def today():
    return datetime.date.today().isoformat()


def in_office(P, day=None):
    """(surname, the day they took office) for whoever holds office on the day (today by default)."""
    day = day or today()
    now = P.GOVERNORS[0]
    for name, start in P.GOVERNORS:
        if start <= day:
            now = (name, start)
    return now


def next_up(P, day=None):
    """(surname, the day they take office) for a governor-elect listed after the day, or None."""
    day = day or today()
    return next(((name, start) for name, start in P.GOVERNORS if start > day), None)


def facts_governor(facts, day=None):
    """[full name, party] of the governor in office on the day, from a states/legislatures.json entry."""
    nxt = facts.get("governorNext")
    if nxt and nxt[2] <= (day or today()):
        return [nxt[0], nxt[1]]
    return facts["governor"]


def facts_next(facts, day=None):
    """[full name, party, "YYYY-MM-DD"] of a governor-elect not yet in office, or None."""
    nxt = facts.get("governorNext")
    return nxt if nxt and nxt[2] > (day or today()) else None


def apply_leaders(P, day=None):
    """Put a profile's chosen next leaders in place from the day they take their post. LEADERS_NEXT, optional in a
    profile, is {house: (name, title, pronoun, "YYYY-MM-DD")} for leaders already chosen (a caucus's Speaker-designate),
    entered ahead of time like a governor-elect. Modifies P.LEADERS (the module is shared, so every reader sees it)."""
    day = day or today()
    for house, (name, title, pronoun, start) in getattr(P, "LEADERS_NEXT", {}).items():
        if start <= day:
            P.LEADERS = {**P.LEADERS, house: (name, title, pronoun)}


def facts_on(facts, day=None):
    """A states/legislatures.json entry as it stands on the day (today by default): its optional `next`, a list of
    {"from": "YYYY-MM-DD", field: value, ...}, replaces those fields from each one's day, so a new legislature's facts
    (a coalition that ends, a note naming the new leaders) take effect on the day it's sworn in without anyone editing
    the file then. Fields not named stay as they are."""
    day = day or today()
    out = {k: v for k, v in facts.items() if k != "next"}
    for change in sorted(facts.get("next") or [], key=lambda c: c["from"]):
        if change["from"] <= day:
            out.update({k: v for k, v in change.items() if k != "from"})
    return out
