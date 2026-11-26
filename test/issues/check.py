"""Check the national issues (issues.py) against every state's published bills: python3 test/issues/get.py, then
python3 test/issues/check.py, which writes .issues-cache/report.txt (counts per issue and state, 30 random matches with
the text that matched, 40 possible misses). See notes/issues-check.md."""
"""Run issues.py over the cached bills: counts per issue and state, random matches, and possible misses."""
import glob, json, os, random, re, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
import importlib; issues = importlib.import_module("issues")
HERE = os.path.dirname(os.path.abspath(__file__))
WIDE = {  # words in a title: bills with these that the issue missed are read over
    "datacenters": [r"\b(?:large|high)[- ]?(?:energy|load|use)|\bdata\b.{0,30}\b(?:facilit|infrastructure)"],
    "pfas": [r"\bchemical|\bfoam\b|\bfluor|\bcontaminant"],
    "ai": [r"\balgorithm|\bmachine learning|\bautomated|\bsynthetic|\bdigital replica|\blikeness|\bmanipulated"],
    "kidsonline": [r"\b(?:online|internet|digital|app|website|platform|social)", r"\b(?:minor|child|youth|teen|kid|age)"],
    "phones": [r"\b(?:device|phone|technology|screen)", r"\b(?:school|student|class)"],
    "housing": [r"\b(?:zoning|land use|housing|dwelling|density|lot)"],
    "minwage": [r"\bwage"], "repair": [r"\brepair"],
    "betting": [r"\b(?:wager|gaming|gambl|sweepstake|casino|bet)"],
    "drugcosts": [r"\b(?:drug|pharmac|insulin|prescription)"],
    "popularvote": [r"\b(?:popular vote|electoral (?:college|votes?)|presidential electors?|elect\w* (?:the )?president)"]}
def bills():
    for path in sorted(glob.glob(os.path.join(HERE, "..", "..", ".issues-cache", "*.json"))):
        st, s = os.path.basename(path)[:-5].split("_")
        d = json.load(open(path))
        c = d["cols"]
        if not c: continue
        for i in range(len(c[0])):
            title, summ, flags, vers = c[0][i], c[1][i] or "", c[5][i], c[17][i]
            if summ and summ[0] == "\x01": summ = title + summ[1:]
            if flags & 512 or flags & 256: continue
            num = vers[0][0] if vers else "?"
            t = d["texts"].get(re.sub(r"[A-Z]$", "", num)) or ""
            if isinstance(t, list): t = " ".join(x for x in t if isinstance(x, str))
            elif isinstance(t, dict): t = " ".join(str(v) for v in t.values() if isinstance(v, str))
            yield st, int(s), bool(d.get("current")), num, title, (f"{title}. {summ}", t), c[6][i]
random.seed(7)
counts, samples, misses, total, cur = {}, {}, {}, {}, {}
for st, s, current, num, title, text, stage in bills():
    total[st] = total.get(st, 0) + 1
    head, body = text
    found = issues.issues_of(head, body)
    for k in found:
        counts.setdefault(k, {}).setdefault(st, [0, 0])[0] += 1
        if current: counts[k][st][1] += 1
        samples.setdefault(k, []).append((st, s, num, title, issues.snippet(k, head) or issues.snippet(k, body)))
    for k, ws in WIDE.items():
        if k not in found and all(re.search(w, title, re.I) for w in ws):
            misses.setdefault(k, []).append((st, s, num, title, ""))
out = open(os.path.join(HERE, "..", "..", ".issues-cache", "report.txt"), "w")
for i in issues.ISSUES:
    k = i["id"]; c = counts.get(k, {})
    out.write(f"\n===== {i['name']}: {sum(v[0] for v in c.values())} bills, {sum(v[1] for v in c.values())} this session; states with none: {sorted(set(total) - set(c))}\n")
    out.write("  " + ", ".join(f"{st} {v[0]}/{v[1]}" for st, v in sorted(c.items(), key=lambda x: -x[1][0])) + "\n")
    out.write("  -- 30 random matches\n")
    for st, s, num, title, snip in random.sample(samples.get(k, []), min(30, len(samples.get(k, [])))):
        out.write(f"  [{st} {s} {num}] {title[:110]}\n      ...{re.sub(r'\s+', ' ', snip or '')[:260]}\n")
    out.write(f"  -- 40 of {len(misses.get(k, []))} possible misses\n")
    for st, s, num, title, hit in random.sample(misses.get(k, []), min(40, len(misses.get(k, [])))):
        out.write(f"  [{st} {s} {num}] {title[:120]}  ({hit[:60]})\n")
print("bills", sum(total.values()), "states", len(total))
