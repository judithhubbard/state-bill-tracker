#!/usr/bin/env python3
"""Legislators' photos, for the states whose own files have none: data/<state>/photos.json.

A legislator's page shows the photo in their contacts ("image") when the state's own files give one (NJ, CA, TX ...).
For the rest this fills in a web address from:
- the states: Open States' people data (public domain), one small file a state, data.openstates.org/people/current/<st>.csv,
  whose `image` is usually the legislature's own photo. Only photos on official sites are kept (`official()`: the
  legislature's, the government's, a caucus's; and Wikimedia Commons): Open States also links news sites' photos, campaign
  sites and Google's image-search thumbnails, which aren't ours to show.
- Congress: the unitedstates/images project (public domain; the Government Publishing Office's member photos), by
  bioguide id, which Congress's contacts carry ("id"). Congress.gov's own photos answer 403 to programs.
Photos are linked, not copied (as NJ's and the other states' own are).

It runs after each state's download (download.yml's "Add photos" step, every run): the matching is quick, and the source
file is downloaded again only when the copy is a week old (kept in the state's folder, so in its cache). photos.json is
rewritten only when it changes. build_data.py's legislators() reads it (`image_of()`); test/data_check.py counts how many
current members have a photo either way.

Matching: each contacts file's members, by house, name and district (`match()`); a member the state's files give a photo
keeps it. Each address is asked once a week whether it answers with an image (`head()`, a HEAD request, two a second,
answers in photos_checked.json): a 404, a web page or a 10 MB original is left out.
Usage: python3 photos.py data/<state> ...   (folders that aren't a state's are skipped; --force downloads again)
"""
import csv, glob, io, json, os, re, sys, time, unicodedata, urllib.error, urllib.request
from collections import Counter
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
WEEK = 7 * 86400
UA = {"User-Agent": "statebilltracker.org (legislators' photos; a weekly download)"}
# Photo hosts kept besides the official-looking ones (official()): who they are.
KNOWN = {
    "upload.wikimedia.org": "Wikimedia Commons",
    "unitedstates.github.io": "the unitedstates/images project (GPO's member photos)",
    "cdn.zephyrcms.com": "the Indiana Senate Republicans' site",
    "dtj5wlj7ond0z.cloudfront.net": "the Michigan House Republicans' site (gophouse.org)",
    "lawmakerdocuments.blob.core.usgovcloudapi.net": "the South Dakota Legislature's storage",
}
# Photo addresses the legislature names by seat (whoever holds it now), preferred to Open States' when they answer with
# an image. Louisiana: 88 of 141 have none in Open States.
PATTERNS = {
    "la": lambda seat: (f"https://senate.la.gov/SenPics/Sen{digits(seat[2:])}.jpg" if seat[0] == "S"
                        else f"https://house.louisiana.gov/H_Reps/RepPics/rep{digits(seat[2:])}.jpg"),
}
OFFICIAL = re.compile(r"(?:\.gov|\.us)$|leg|senate|house|assembly|capitol|statehouse|gencourt|dems\b|democrats|gop|republicans")
# (And not campaign sites, whose names can say "senate": overture4scsenate.com.)
NOT = re.compile(r"gstatic|googleusercontent|townnews|gannett|brightspot|arcpublishing|patch\.com|ballotpedia|enview|"
                 r"(?:for|4)[a-z]{0,3}(?:senate|house|assembly|rep|delegate)|elect|vote")
BIG = 5_000_000  # bytes: a few legislatures' photos are 10 MB originals (CT, OK), too much for a 96-pixel picture


def official(url):
    if not url or not url.startswith(("http://", "https://")):
        return False
    host = url.split("/")[2].lower()
    if NOT.search(url.lower()):
        return False
    return host in KNOWN or bool(OFFICIAL.search(host))


def https(url):
    # The pages are https: an http photo would be blocked or upgraded by the browser.
    url = "https://" + url[7:] if url.startswith("http://") else url
    # Wikimedia serves thumbnails only in its standard widths (an 800px one answers 400).
    if url.startswith("https://upload.wikimedia.org/") and "/thumb/" in url:
        url = re.sub(r"/\d+px-([^/]+)$", r"/330px-\1", url)
    return url


def norm(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
    s = re.sub(r"\([^)]*\)|\"[^\"]*\"|“[^”]*”", " ", s)  # nicknames
    return [w for w in re.sub(r"[^a-z\s-]", " ", s).replace("-", " ").split() if w not in ("jr", "sr", "ii", "iii", "iv", "v", "dr", "rev", "md", "phd", "esq")]


def digits(s):
    m = re.search(r"\d+", s or "")
    return str(int(m.group())) if m else None


def get(url, timeout=60):
    headers = dict(UA)
    if url.startswith("https://api.github.com/") and os.environ.get("GITHUB_TOKEN"):
        headers["Authorization"] = "Bearer " + os.environ["GITHUB_TOKEN"]
    return urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=timeout).read()


# ---- sources ----

def openstates(folder, st):
    """[{name, given, family, chamber, district, image}] for a state's current legislators. Several states' contacts
    download the same file each run (data/<st>/openstates_people.csv): a copy less than a week old is read instead."""
    mine = os.path.join(folder, "openstates_people.csv")
    if os.path.exists(mine) and time.time() - os.path.getmtime(mine) < WEEK:
        text = open(mine, encoding="utf-8").read()
    else:
        text = get(f"https://data.openstates.org/people/current/{st}.csv").decode("utf-8")
    rows = csv.DictReader(io.StringIO(text))
    return [{"name": r["name"], "given": r["given_name"], "family": r["family_name"], "chamber": r["current_chamber"],
             "district": r["current_district"], "image": r["image"]} for r in rows]


def congress_ids():
    """Bioguide ids with a photo in unitedstates/images (its gh-pages tree, three requests)."""
    api = "https://api.github.com/repos/unitedstates/images/git/trees/"
    tree = lambda sha: json.loads(get(api + sha))["tree"]
    sha = next(t["sha"] for t in tree("gh-pages") if t["path"] == "congress")
    sha = next(t["sha"] for t in tree(sha) if t["path"] == "225x275")
    return sorted(t["path"][:-4] for t in tree(sha) if t["path"].endswith(".jpg"))


def source(folder, st, force=False):
    """The saved source copy (photos_source.json), downloaded again when a week old. None when there's none."""
    path = os.path.join(folder, "photos_source.json")
    try:
        old = json.load(open(path))
    except (OSError, ValueError):
        old = None
    if old and not force and time.time() - old.get("t", 0) < WEEK:
        return old
    try:
        data = congress_ids() if st == "us" else openstates(folder, st)
    except Exception as e:  # a failed download keeps the last copy
        print(f"{st}: photos' source didn't load ({str(e)[:120]}); {'kept the last copy' if old else 'no photos added'}")
        return old
    if not data:
        return old
    new = {"t": int(time.time()), "fetched": datetime.now(timezone.utc).strftime("%Y-%m-%d"), "data": data}
    with open(path + ".tmp", "w") as f:
        json.dump(new, f, separators=(",", ":"))
    os.replace(path + ".tmp", path)
    return new


def head(url):
    """"ok" when an address answers 200 with an image no bigger than BIG; "bad" when it answers otherwise (404, a web
    page, a 10 MB original); "net" when it doesn't answer here (a timeout; a certificate chain Python can't complete, as
    Illinois's and the Michigan House's, which browsers do): kept, as a browser may well load it. Servers that refuse
    HEAD (Georgia's: 405; Colorado's photos redirect to signed addresses that answer HEAD 403) are asked for the first
    byte instead."""
    r = None
    for method, extra in (("HEAD", {}), ("GET", {"Range": "bytes=0-0"})):
        try:
            r = urllib.request.urlopen(urllib.request.Request(url, method=method, headers={**UA, **extra}), timeout=10)
            break
        except urllib.error.HTTPError as e:
            if e.code in (400, 404, 410):
                return "bad"
        except Exception:
            return "net"
    if r is None:
        return "net"
    kind = (r.headers.get("Content-Type") or "").lower()
    total = re.search(r"/(\d+)$", r.headers.get("Content-Range") or "")
    size = int(total.group(1) if total else r.headers.get("Content-Length") or 0)
    r.close()
    # (Georgia's photos say application/octet-stream; browsers show them.)
    return "ok" if r.status in (200, 206) and (kind.startswith("image/") or "octet-stream" in kind) and size <= BIG else "bad"


class Checks:
    """Each photo address's last answer (photos_checked.json), asked again after a week; at most `budget` seconds of
    asking a run (two a second), so a first run's few hundred can spread over a few runs (unasked ones are kept)."""
    def __init__(self, folder, budget=150):
        self.path = os.path.join(folder, "photos_checked.json")
        try:
            self.seen = json.load(open(self.path))
        except (OSError, ValueError):
            self.seen = {}
        self.until = time.time() + budget
        self.changed = False
        self.asked = set()

    def __call__(self, url):
        self.asked.add(url)
        old = self.seen.get(url)
        if old and time.time() - old[1] < WEEK:
            return old[0]
        if time.time() > self.until:
            return old[0] if old else None
        v = head(url)
        time.sleep(0.5)
        self.seen[url] = [v, int(time.time())]
        self.changed = True
        return v

    def save(self):
        """Saved when something was asked; addresses no longer asked about (members gone) are dropped."""
        if not self.changed:
            return
        self.seen = {u: v for u, v in self.seen.items() if u in self.asked}
        with open(self.path + ".tmp", "w") as f:
            json.dump(self.seen, f, indent=0, sort_keys=True)
        os.replace(self.path + ".tmp", self.path)


# ---- matching ----

# Short first names the contacts and Open States write differently ("William C. Galvin", "Bill Galvin").
NICK = {"bill": "william", "billy": "william", "will": "william", "mike": "michael", "jim": "james", "jimmy": "james",
        "tom": "thomas", "tommy": "thomas", "bob": "robert", "rob": "robert", "bobby": "robert", "dick": "richard",
        "rick": "richard", "ted": "edward", "ed": "edward", "tony": "anthony", "peggy": "margaret", "peg": "margaret",
        "kathy": "kathleen", "jack": "john", "chuck": "charles", "liz": "elizabeth", "beth": "elizabeth",
        "becky": "rebecca", "pat": "patricia", "patty": "patricia", "sam": "samuel", "joe": "joseph", "don": "donald",
        "rod": "rodney", "nick": "nicholas", "andy": "andrew", "drew": "andrew", "dan": "daniel", "dave": "david",
        "jen": "jennifer", "jenn": "jennifer", "matt": "matthew", "chris": "christopher", "steve": "steven",
        "jeff": "jeffrey", "greg": "gregory", "ken": "kenneth", "ron": "ronald", "larry": "lawrence", "jerry": "gerald"}

def match(seat, p, people, used, strict=False):
    """The Open States record for a contacts member: same house, then the surname, then the district or first name.
    strict: the state's seats and Open States' districts are the same numbers (`numbered()`), so a different district
    rules a record out (a new member who shares a surname with someone the copy still lists)."""
    chamber = {"S": "upper", "L": "legislature"}.get(seat[0], "lower")
    mine = norm(p.get("name")) or norm(p.get("key"))
    if not mine:
        return None
    last, first = mine[-1], mine[0]
    dist = digits(seat[2:])
    cands = [i for i, r in enumerate(people) if i not in used and r["chamber"] == chamber]

    def surname(r):
        theirs = norm(r["family"]) or norm(r["name"])[-1:]
        return last in theirs or (theirs and theirs[-1] in mine[1:]) or last in norm(r["name"])

    def firstname(r):
        g = norm(r["given"]) + norm(r["name"])[:1]
        return first in g or any(x[:1] == first[:1] and (x.startswith(first) or first.startswith(x)) for x in g) \
            or any(NICK.get(x) == first or NICK.get(first) == x for x in g)

    def initial(r):
        return any(x[:1] == first[:1] for x in norm(r["given"]) + norm(r["name"])[:1])

    # (District numbers are compared only where both are numbers: MA's and VT's districts are names.)
    same_dist = lambda r: dist is not None and digits(r["district"]) == dist
    if strict:
        cands = [i for i in cands if same_dist(people[i])]
    for test in (lambda r: surname(r) and firstname(r) and same_dist(r),
                 lambda r: surname(r) and same_dist(r),
                 lambda r: surname(r) and firstname(r),
                 lambda r: surname(r) and initial(r)):
        hits = [i for i in cands if test(people[i])]
        if len(hits) == 1:
            return hits[0]
    return None


def numbered(people, recs):
    """The houses whose seats ("H:12", "H:12a") carry Open States' district numbers: for 90% of their members found
    by name (not MA's or VT's named districts, AK's lettered Senate seats, MN's House seats counted 1-134)."""
    same, n = Counter(), Counter()
    for seat, p in people.items():
        i = match(seat, p, recs, set())
        if i is not None:
            n[seat[0]] += 1
            same[seat[0]] += digits(seat[2:]) == digits(recs[i]["district"])
    return {h for h in n if same[h] >= 0.9 * n[h]}


def contacts_files(folder):
    return sorted(glob.glob(os.path.join(folder, "contacts_*.json")))


def build(folder, st, src, check=lambda url: None):
    """{"<house>|<name key>": url} for members whose contacts have no photo. check(url) "bad" leaves a photo out."""
    out = {}
    for path in contacts_files(folder):
        people = json.load(open(path)).get("people", {})
        if st == "us":
            have = set(src["data"])
            for seat, p in people.items():
                url = f"https://unitedstates.github.io/images/congress/225x275/{p['id']}.jpg"
                if not p.get("image") and p.get("id") in have:  # (in the project's own file list)
                    out[f"{seat[0]}|{p['key']}"] = url
            continue
        recs = src["data"]
        used, strict = set(), numbered(people, recs)
        for seat, p in sorted(people.items()):
            if p.get("image"):
                continue
            i = match(seat, p, recs, used, seat[0] in strict)
            url = None
            if i is not None:
                used.add(i)
                url = https(recs[i]["image"]) if official(recs[i]["image"]) else None
            # The legislature's own, by seat: whoever holds it now (so only for the newest contacts), when it answers.
            if st in PATTERNS and path == contacts_files(folder)[-1] and check(PATTERNS[st](seat)) == "ok":
                url = PATTERNS[st](seat)
            if url and check(url) != "bad":
                out[f"{seat[0]}|{p['key']}"] = url
    return out


def refresh(folder, force=False):
    st = os.path.basename(os.path.normpath(folder))
    if not re.fullmatch(r"[a-z]{2}", st) or st == "ny" or not os.path.isdir(folder) or not contacts_files(folder):
        return
    src = source(folder, st, force)
    if not src:
        return
    check = Checks(folder)
    images = build(folder, st, src, check)
    check.save()
    path = os.path.join(folder, "photos.json")
    out = {"source": "unitedstates/images" if st == "us" else "Open States people", "fetched": src.get("fetched"),
           "images": dict(sorted(images.items()))}
    try:
        same = json.load(open(path)) == out
    except (OSError, ValueError):
        same = False
    if not same:
        with open(path + ".tmp", "w") as f:
            json.dump(out, f, indent=0, sort_keys=True)
        os.replace(path + ".tmp", path)
    print(f"{st}: {len(images)} photos added{'' if not same else ' (unchanged)'}")


# ---- reading (build_data.py, test/data_check.py) ----

_CACHE = {}


def load(folder):
    if folder not in _CACHE:
        try:
            _CACHE[folder] = json.load(open(os.path.join(folder, "photos.json"))).get("images", {})
        except (OSError, ValueError):
            _CACHE[folder] = {}
    return _CACHE[folder]


def image_of(folder, seat, p):
    """A member's photo: their contacts' own, else photos.json's."""
    return p.get("image") or load(folder).get(f"{seat[0]}|{p.get('key')}")


if __name__ == "__main__":
    force = "--force" in sys.argv
    for a in sys.argv[1:]:
        if not a.startswith("--"):
            try:
                refresh(a, force)
            except Exception as e:  # one state's trouble mustn't stop the others (or the download)
                print(f"{a}: photos not updated ({e})")
