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
def state(st):
    page = (get(BASE + st + "/") or b"").decode("utf-8", "replace")
    m = re.search(r'data-src="(data/[^"]+\.json)"', page)
    if not m: return st, "no data-src"
    cur = json.loads(get(BASE + st + "/" + m.group(1)))
    sessions = [s["session"] for s in cur.get("sessions", []) if not s.get("upcoming")]
    done = []
    for s in sessions:
        path = os.path.join(OUT, f"{st}_{s}.json")
        if not os.path.exists(path):
            d = cur if cur["session"] == s else json.loads(get(BASE + st + f"/data/{s}.json") or b"null")
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
