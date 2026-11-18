"""Download every state's published bill data and bill texts from statebilltracker.pages.dev into cache/."""
import json, os, re, sys, urllib.request
from concurrent.futures import ThreadPoolExecutor
BASE = "https://statebilltracker.pages.dev/"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".issues-cache")
os.makedirs(OUT, exist_ok=True)
def get(url):
    for _ in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "statebilltracker issues check"}), timeout=120) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code == 404: return None
        except Exception: pass
    return None
def base_num(p): return re.sub(r"[A-Z]$", "", p)
def part(p):
    k = base_num(p); return f"{k[0]}{int(re.sub(r'[^0-9]', '', k) or 0) // 500}"
def page_data(url):
    """A session page's whole data, put back together from its parts (build_data.py's split_payload(): the list part,
    then the rows, search, votes, hist and cos parts and the bills' shards, each with its own strings table) into one
    record table with one strings table, or None. (Law codes other than chapter amendments' aren't published.)"""
    page = (get(url) or b"").decode("utf-8", "replace")
    tag = re.search(r'<script[^>]*id="bill-data"[^>]*>', page)
    at = lambda k: (re.search(rf'data-{k}="([^"]*)"', tag.group(0)) or [None, None])[1] if tag else None
    if not at("src"):
        return None
    base = url.rsplit("/", 1)[0] + "/"
    load = lambda path: json.loads(get(base + path) or b"null")
    d = load(at("src"))
    if not d or not d.get("cols"):
        return d
    v, session = at("v"), at("session")
    hashes = dict(x.split(":") for x in (at("parts") or "").split())
    piece = lambda kind: load(f"{v}{session}.{hashes[kind]}.{kind}.json") if kind in hashes else None
    T = d["strings"]
    index = {t: i for i, t in enumerate(T)}

    def add(t):
        if t is None:
            return -1
        if t not in index:
            index[t] = len(T)
            T.append(t)
        return index[t]
    own = lambda table: (lambda i: -1 if i is None or i < 0 else add(table[i]))
    cols = d["cols"]
    rows, search, votes, hist, cos = (piece(k) for k in ("rows", "search", "votes", "hist", "cos"))
    if rows:
        cols[0] = rows["title"]
        f = own(rows["strings"])
        for vers, acts in zip(cols[17], rows["acts"]):
            for ver, a in zip(vers, acts):
                ver[5] = [[x[0], f(x[1])] for x in a]
        # Laws, committees, co-sponsors, program, law, parties, main topic; each version's co-sponsors, status, committee;
        # the signing memo, the committee it's in. (Sponsors' districts aren't published where legislators are known.)
        for j, (laws, comms, cosp, program, law, parties, main, vm, memo, comm) in enumerate(rows.get("more") or []):
            cols[2][j], cols[3][j], cols[27][j], cols[10][j] = [f(x) for x in laws], [f(x) for x in comms], memo, f(comm)
            cols[12][j], cols[15][j], cols[16][j], cols[21][j], cols[25][j] = cosp, f(program), f(law), parties, main
            for ver, (c, sd, cm) in zip(cols[17][j], vm):
                ver[2], ver[3], ver[4] = c, f(sd), f(cm)
    if search:
        cols[1] = search["summary"]
    if votes:
        f = own(votes["strings"])
        cols[22] = [[[x[0], x[1], f(x[2])] + x[3:6] + [[[f(m), c] for m, c in x[6]]] for x in vs] for vs in votes["votes"]]
    if hist:
        cols[19] = hist["hist"]
    if cos:
        f = own(cos["strings"])
        for vers, cs in zip(cols[17], cos["cos"]):
            for ver, c in zip(vers, cs):
                ver[6] = [f(x) for x in c]
    for k, h in enumerate((at("shards") or "").split()):
        sh = load(f"{v}{session}.{h}.s{k}.json")
        if not sh:
            continue
        f = own(sh["strings"])
        for j, num, title, acts, summ, hst, vts, similar, veto, cs, *more in sh["b"]:
            cols[26][j] = similar
            cols[28][j] = veto[:2] + [f(veto[2])] + veto[3:] if veto else veto
    return d
def state(st):
    cur = page_data(BASE + st + "/")
    if not cur: return st, "no data-src"
    sessions = [s["session"] for s in cur.get("sessions", []) if not s.get("upcoming")]
    done = []
    for s in sessions:
        path = os.path.join(OUT, f"{st}_{s}.json")
        if not os.path.exists(path):
            d = cur if cur["session"] == s else page_data(BASE + st + f"/{s}.html")
            if not d: continue
            texts = {}
            if d.get("hasText"):
                parts = sorted({part(v[0]) for vers in d["cols"][17] for v in vers[:1]})
                for pt in parts:
                    t = get(BASE + st + f"/data/{s}-text/{pt}.json")
                    if t and t[:1] in (b"{", b"["):
                        try:
                            texts.update(json.loads(t))
                        except ValueError:
                            pass
            json.dump({"cols": d["cols"], "strings": d.get("strings"), "texts": texts, "session": s, "current": d.get("current")}, open(path, "w"))
        done.append(s)
    return st, done
states = sys.argv[1:] or re.findall(r'href="([a-z]{2})/"', get(BASE).decode())
with ThreadPoolExecutor(8) as ex:
    def safe(st):
        try:
            return state(st)
        except Exception as e:
            return st, f"failed: {type(e).__name__}: {e}"
    for st, r in ex.map(safe, sorted(set(states))):
        print(st, r, flush=True)
