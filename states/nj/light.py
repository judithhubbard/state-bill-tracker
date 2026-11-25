"""New Jersey's light history (states/light.py, states/LIGHT.md): the 2014-15 and 2016-17 sessions, before the site's
first (2018-19), from the Legislature's own bill database, pub.njleg.gov/leg-databases/<year>data/DB<year>_TEXT.zip
(about 1.5 MB each; both answer, checked 2026-11-25; njleg.state.nj.us's robots.txt allows everything), read by the same
converter as the site's sessions. One download a session: the floor and committee vote files are left out (light
history keeps no votes). Older databases may lack tables, as 2022-23's did (states/nj/fill2022.py): the light file's
"lacks" says what came out empty."""
import importlib, os, sys

SOURCE = "pub.njleg.gov/leg-databases DB<year>_TEXT.zip (New Jersey Legislature)"
SESSIONS = [2014, 2016]


def fetch(session, data):
    saved = sys.argv
    sys.argv = [saved[0]]  # (fetch.py reads its first year from the command line when loaded)
    try:
        F = importlib.import_module("states.nj.fetch")
    finally:
        sys.argv = saved
    url, name = next(F.files(session))
    return F.get(url, os.path.join(data, name))
