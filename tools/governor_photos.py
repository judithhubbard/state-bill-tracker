#!/usr/bin/env python3
"""Governors' photos (and the President's): states/governor_photos.json, from Wikidata and Wikimedia Commons.

For each state in states/legislatures.json: the governor (`governor`) and a governor-elect (`governorNext`), and for
Congress ("us") the President. Each person is found on Wikidata and their image (P18) linked as a Commons thumbnail
240 pixels wide, with the file's author and license (Commons' extmetadata), for the credit.

Matching, so a namesake never gets in: people whose English label or alias is the name, humans and U.S. citizens who
held some office (P39) or are politicians (P106); of those, one who held the state's governor's office (P39 of the office
the state's item names as its head of government, P1313), or the presidency (Q11696), wins. A governor in office must be
found that way. A governor-elect not yet in office may be found by name alone, only when exactly one person fits; a name
two people fit is listed and left out until it's settled in PICK (name -> Wikidata id, checked by eye).
Run it and read the list it prints: every match, by eye. Polite: one request to query.wikidata.org and one or two to
commons.wikimedia.org, with a User-Agent naming the site.

The build (build_data.py's govNow) shows the photo of whoever is in office on the build day (governors.facts_governor()),
so the switch on inauguration day needs no edit here. A request that fails changes nothing (the file stays as it was).
Weekly, and the day legislatures.json names someone new: publish.yml's "Governors' photos" step, whose copy is kept in
its own cache (gov_photos/), not committed; the file in the repository is the fallback when Wikidata doesn't answer.
Usage: python3 tools/governor_photos.py [--dry-run]     (--names: just list the people it would look for)
"""
import json, os, re, sys, unicodedata, urllib.parse, urllib.request

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(HERE, "states", "governor_photos.json")
UA = {"User-Agent": "StateBillTracker/1.0 (https://statebilltracker.pages.dev/; governors' photos, a weekly request)"}
WIDTH = 240
PRESIDENT = "Q11696"
# Names that more than one person fits, settled by eye: name -> Wikidata id.
PICK = {"David Crowley": "Q28151883"}  # Milwaukee County Executive, born 1986 (not the Cincinnati council member, 1937)


def norm(s):
    s = unicodedata.normalize("NFD", s or "").encode("ascii", "ignore").decode().lower()
    s = re.sub(r"\b(jr|sr|ii|iii)\b\.?", "", s)
    return re.sub(r"[^a-z]", "", s)


def get(url, data=None, headers=None):
    req = urllib.request.Request(url, data=data, headers={**UA, **(headers or {})})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.load(r)


def people():
    """[(state, name, "now" or "next")] from states/legislatures.json."""
    out = []
    for st, f in json.load(open(os.path.join(HERE, "states", "legislatures.json")))["states"].items():
        if f.get("governor"):
            out.append((st, f["governor"][0], "now"))
        if f.get("governorNext"):
            out.append((st, f["governorNext"][0], "next"))
    return out


def file_of(uri):
    """"File:Name.jpg" from a Special:FilePath address."""
    return "File:" + urllib.parse.unquote(uri.rsplit("/", 1)[-1]) if uri else ""


def by_name(names):
    """{normalized name: [(qid, label, description, image file, {state codes whose governor's office they held, "us"
    for the presidency})]}."""
    # (Labels in English or "mul", the default for every language that newer items often have instead.)
    values = " ".join(json.dumps(n) + lang for n in names for lang in ("@en", "@mul"))
    q = """
SELECT ?name ?person ?desc (SAMPLE(?img) AS ?image) (GROUP_CONCAT(DISTINCT ?code; separator="|") AS ?codes) WHERE {
  VALUES ?name { %s }
  { ?person rdfs:label ?name } UNION { ?person skos:altLabel ?name }
  ?person wdt:P31 wd:Q5; wdt:P27 wd:Q30.
  FILTER EXISTS { { ?person wdt:P39 ?any } UNION { ?person wdt:P106 wd:Q82955 } }
  OPTIONAL { ?person schema:description ?desc. FILTER(LANG(?desc) = "en") }
  OPTIONAL { ?person wdt:P18 ?img }
  OPTIONAL {
    { ?person wdt:P39 ?office. ?state wdt:P31 wd:Q35657; wdt:P1313 ?office; wdt:P300 ?iso. BIND(LCASE(SUBSTR(?iso, 4)) AS ?code) }
    UNION { ?person wdt:P39 wd:%s. BIND("us" AS ?code) }
  }
} GROUP BY ?name ?person ?desc""" % (values, PRESIDENT)
    rows = get("https://query.wikidata.org/sparql", urllib.parse.urlencode({"query": q}).encode(),
               {"Accept": "application/sparql-results+json"})["results"]["bindings"]
    out = {}
    for b in rows:
        r = {k: v["value"] for k, v in b.items()}
        # (One row a label language: a person found twice is one candidate.)
        q, codes = r["person"].rsplit("/", 1)[-1], set(filter(None, (r.get("codes") or "").split("|")))
        same = out.setdefault(norm(r["name"]), {})
        if q in same:
            codes |= same[q][4]
        same[q] = (q, r["name"], r.get("desc", ""), file_of(r.get("image")) or same.get(q, ("",) * 4)[3], codes)
    return {k: list(v.values()) for k, v in out.items()}


def strip_html(s):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", s or "")).strip()


def commons(files):
    """{file: {"src", "page", "author", "license", "attr"}} from Commons' imageinfo, 50 files a request."""
    out = {}
    files = sorted(set(f for f in files if f))
    for i in range(0, len(files), 50):
        part = files[i:i + 50]
        q = urllib.parse.urlencode({"action": "query", "format": "json", "formatversion": 2, "prop": "imageinfo",
                                    "iiprop": "url|extmetadata", "iiurlwidth": WIDTH, "titles": "|".join(part),
                                    "iiextmetadatafilter": "Artist|LicenseShortName|AttributionRequired"})
        data = get("https://commons.wikimedia.org/w/api.php?" + q)["query"]
        # (The API writes titles its own way, e.g. underscores as spaces.)
        asked = {f: f for f in part}
        for n in data.get("normalized", []):
            asked[n["to"]] = n["from"]
        for p in data["pages"]:
            info = (p.get("imageinfo") or [{}])[0]
            if not info.get("thumburl"):
                continue
            m = info.get("extmetadata", {})
            val = lambda k: strip_html(m.get(k, {}).get("value", ""))
            author = val("Artist")
            # (Commons writes an unknown author twice over, "Unknown authorUnknown author": none.)
            if re.match(r"(?i)unknown author", author):
                author = ""
            out[asked.get(p["title"], p["title"])] = {
                "src": info["thumburl"].split("?")[0], "page": info.get("descriptionurl", ""),
                "author": author[:120].rstrip(". "), "license": val("LicenseShortName"),
                "attr": val("AttributionRequired").lower() == "true"}
    return out


def main():
    dry = "--dry-run" in sys.argv
    who = people()
    if "--names" in sys.argv:
        print("\n".join(f"{st} {name}" for st, name, _ in who))
        return
    found = by_name(sorted(set(n for _, n, _ in who)))
    chosen, report = {}, []
    for st, name, when in who:
        cands = found.get(norm(name), [])
        if name in PICK:
            cands = [c for c in cands if c[0] == PICK[name]]
        # Someone who held this state's governor's office (or the presidency) wins over namesakes.
        office = [c for c in cands if st in c[4]]
        if office:
            cands, how = office, "held the office"
        elif when == "now":
            report.append(f"{st:3} {name:26} -- NOT FOUND holding the office: " + "; ".join(f"{c[0]} {c[2]}" for c in cands))
            continue
        else:
            how = "elect, by name"
        if len(cands) != 1:
            report.append(f"{st:3} {name:26} -- {len(cands)} candidates: " + "; ".join(f"{c[0]} {c[2]}" for c in cands))
            continue
        q, label, desc, f, _ = cands[0]
        chosen[(st, name)] = (q, label, f, f"{how}; {desc}")
    info = commons([c[2] for c in chosen.values()])
    out = {}
    for (st, name), (q, label, f, how) in chosen.items():
        i = info.get(f)
        report.append(f"{st:3} {name:26} {q:10} {how[:70]:70} " + (f"{f[5:]} [{i['license']}]" if i else "(no photo)"))
        if i:
            out.setdefault(st, {})[name] = {"wikidata": q, "file": f[5:], **i}
    print("\n".join(sorted(report)))
    n = sum(len(v) for v in out.values())
    print(f"\n{n} of {len(who)} people have a photo")
    if n < len(who) / 2:
        sys.exit("Too few found: Wikidata or Commons may have answered oddly. The file is left as it was.")
    if not dry:
        text = json.dumps(dict(sorted(out.items())), indent=1, ensure_ascii=False, sort_keys=True) + "\n"
        if not os.path.exists(OUT) or open(OUT).read() != text:
            open(OUT, "w").write(text)
            print("wrote", OUT)


if __name__ == "__main__":
    main()
