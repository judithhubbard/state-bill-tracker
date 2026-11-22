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
- Ballotpedia (approved by the owner 2026-11-22): Open States links about 400 members' photos to Ballotpedia's
  thumbnails (s3.amazonaws.com/ballotpedia-api4/files/thumbs/200/300/..., cdn.ballotpedia.org), kept only when there's
  no official one (the legislature's own address, `PATTERNS`, wins; so do the contacts' own). Ballotpedia asks that its
  person photos be reused only non-commercially, with credit: they're linked, never copied (`ballotpedia()`), and the
  page's "About this data" names them.
Photos are linked, not copied (as NJ's and the other states' own are), except heavy ones: a photo over HEAVY (500 KB;
Georgia's and the Oklahoma Senate's are 5-10 MB originals) is downloaded once, made 240 pixels wide (JPEG, `shrink()`),
and kept in data/<state>/photos/<hash>.jpg (the state's cache); photos.json's "small" names it, and build_data.py
copies it to the site's /assets/photos/, which browsers keep for good. The name is a hash of the address and the
original's size, so a changed photo gets a new name. Ballotpedia's are never copied (and are 200x300 anyway).

It runs after each state's download (download.yml's "Add photos" step, every run): the matching is quick, and the source
file is downloaded again only when the copy is a week old (kept in the state's folder, so in its cache). photos.json is
rewritten only when it changes. build_data.py's legislators() reads it (`image_of()`); test/data_check.py counts how many
current members have a photo either way.

- The legislature's own pages (2026-11-22), preferred to Open States' when they answer with an image: an address built
  from the seat or the state's own member data (`PATTERNS`: Louisiana by seat, New Hampshire's senators by district and
  House members by the picture number its CommitteeMembers.txt gives each PersonID, Florida's House by MemberId), or read
  from one roster page that lists every member with a photo (`ROSTERS`, read weekly into photos_roster.json: the Oklahoma
  House's /representatives, the Florida Senate's /Senators/).
Every request respects the host's robots.txt (`allowed()`, 2026-11-22): a photo under a path it disallows is never asked
for, checked or copied (Colorado's /rails/active_storage/, South Carolina's /images/, Tennessee's capitol.tn.gov for all
but named search engines, the Missouri House's and the Indiana House Republicans' photo folders); it stays linked only if
an answer from before showed a light photo, else it's left out. Requests to a host keep its Crawl-delay (gc.nh.gov's 11 seconds, flsenate.gov's 10); a host with a delay of 5 seconds or more is asked again
monthly instead of weekly.

- Wikidata and Wikimedia Commons (2026-11-22), the last resort for members still without a photo (`add_wikidata()`):
  the portrait (P18) of the person Wikidata says holds the member's seat (P39 of the house's member position,
  `POSITIONS`; the district (P768) where the house's districts are its seat numbers; a term reaching the session), or,
  when Wikidata has them only in the other house or no term at all, the only person of that name, if they held a seat in
  the state's legislature or their description names it. Linked as a 330-pixel Commons thumbnail; photos.json's
  "credits" keeps each one's author and license (the photo's tooltip on the legislator's page, `credit_of()`, and a line
  in How's "About this data", `uses_commons()`). Answers, "none" too, are kept a month in photos_wikidata.json.

Matching: each contacts file's members, by house, name and district (`match()`); a member the state's files give a photo
keeps it. Each address is asked once a week whether it answers with an image (`head()`, a HEAD request, two a second,
answers in photos_checked.json, with its size): a 404 or a web page is left out, and a heavy one shrunk (above).
Usage: python3 photos.py data/<state> ...   (folders that aren't a state's are skipped; --force downloads again)
"""
import csv, glob, hashlib, io, json, os, re, sys, time, unicodedata, urllib.error, urllib.parse, urllib.request
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
# Photo addresses the legislature names itself, preferred to Open States' when they answer with an image (seat, member,
# contacts session). Louisiana's by seat (whoever holds it now; 88 of 141 have none in Open States).
def nh_pictures(folder):
    """New Hampshire's House photos are /house/images/memberpics/<n>.jpg, n the number CommitteeMembers.txt gives each
    PersonID (its third and fourth columns: "H43|51|377257|902|1|V Chairman"): {PersonID: n}, from the newest file."""
    files = sorted(glob.glob(os.path.join(folder, "[0-9]" * 4, "CommitteeMembers.txt")))
    out = {}
    for line in (open(files[-1], encoding="utf-8", errors="replace").read().split("\n") if files else []):
        f = line.strip().split("|")
        if len(f) >= 4 and f[2].strip().isdigit() and f[3].strip().isdigit():
            out[f[3].strip()] = f[2].strip()
    return out


_NH = {}


def nh_photo(seat, p, session, folder):
    if seat[0] == "S":
        return f"https://gc.nh.gov/senate/images/senators/{digits(seat[2:])}.jpg"
    if folder not in _NH:
        _NH[folder] = nh_pictures(folder)
    n = _NH[folder].get(str(p.get("id") or ""))
    return f"https://gc.nh.gov/house/images/memberpics/{n}.jpg" if n else None


PATTERNS = {
    "la": lambda seat, p, session, folder: (f"https://senate.la.gov/SenPics/Sen{digits(seat[2:])}.jpg" if seat[0] == "S"
                                            else f"https://house.louisiana.gov/H_Reps/RepPics/rep{digits(seat[2:])}.jpg"),
    "nh": nh_photo,
    # Florida's House: the MemberId the contacts carry ("id"; the roster's /FileStores/Web/Imaging/Member/4864.jpg).
    "fl": lambda seat, p, session, folder: (f"https://www.flhouse.gov/FileStores/Web/Imaging/Member/{p['id']}.jpg"
                                            if seat[0] == "H" and str(p.get("id") or "").isdigit() else None),
}


def ok_house(get_):
    """The Oklahoma House's roster page (www.okhouse.gov/representatives; no robots.txt): its page data lists every
    member with district and portrait, in several sizes ("small" is 400x500, about 35 KB). {"H:97": url}."""
    page = get_("https://www.okhouse.gov/representatives").decode("utf-8", "replace")
    data = json.loads(re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', page, re.S).group(1))
    out = {}
    for m in data["props"]["pageProps"]["members"]["legislatureMembers"]:
        a = m.get("attributes") or {}
        d = ((((a.get("district") or {}).get("data") or {}).get("attributes")) or {}).get("number")
        pic = (((a.get("portrait") or {}).get("data") or {}).get("attributes")) or {}
        url = ((pic.get("formats") or {}).get("small") or {}).get("url") or pic.get("url")
        if d and url:
            out[f"H:{int(d)}"] = url
    return out


def fl_senate(get_):
    """The Florida Senate's list of senators (www.flsenate.gov/Senators/, robots.txt allows /Senators/): each one's
    thumbnail, /PublishedContent/Senators/2026-2028/Photos/S27_5342_Thumbnail.jpg; the photo is the same name without
    "_Thumbnail" (about 60 KB). {"S:27": url}."""
    page = get_("https://www.flsenate.gov/Senators/").decode("utf-8", "replace")
    out = {}
    for path, d in re.findall(r'src="(/PublishedContent/Senators/[^"]*/Photos/S(\d+)_[^"]*?)_Thumbnail\.jpg"', page):
        out[f"S:{int(d)}"] = "https://www.flsenate.gov" + path + ".jpg"
    return out


# The legislature's own roster pages, one request each, read weekly into photos_roster.json (seat -> url): for the newest
# contacts, preferred to Open States' when the photo answers.
ROSTERS = {"ok": [ok_house], "fl": [fl_senate]}


def rosters(folder, st, force=False):
    path = os.path.join(folder, "photos_roster.json")
    try:
        old = json.load(open(path))
    except (OSError, ValueError):
        old = None
    if st not in ROSTERS:
        return {}
    if old and not force and time.time() - old.get("t", 0) < WEEK:
        return old["seats"]
    seats = {}
    for fn in ROSTERS[st]:
        try:
            def get_(u):
                if not allowed(u):
                    raise RuntimeError("robots.txt disallows it")
                pace(u, 1)
                return get(u)
            seats.update(fn(get_))
        except Exception as e:  # a failed page keeps the last copy's seats
            print(f"{st}: photo roster {fn.__name__} didn't load ({str(e)[:100]})")
            seats.update({k: v for k, v in ((old or {}).get("seats") or {}).items() if k not in seats})
    if seats:
        with open(path + ".tmp", "w") as f:
            json.dump({"t": int(time.time()), "seats": seats}, f, indent=0, sort_keys=True)
        os.replace(path + ".tmp", path)
    return seats
OFFICIAL = re.compile(r"(?:\.gov|\.us)$|leg|senate|house|assembly|capitol|statehouse|gencourt|dems\b|democrats|gop|republicans")
# (And not campaign sites, whose names can say "senate": overture4scsenate.com.)
NOT = re.compile(r"gstatic|googleusercontent|townnews|gannett|brightspot|arcpublishing|patch\.com|enview|"
                 r"(?:for|4)[a-z]{0,3}(?:senate|house|assembly|rep|delegate)|elect|vote")
HEAVY = 500_000  # bytes: over this a photo is shrunk (shrink()); a few legislatures' are 5-10 MB originals (GA, OK, CT)
BIG = 40_000_000  # and over this left out (not downloaded)
LINK_MAX = 5_000_000  # a heavy photo without a copy yet is linked up to this size, and left out over it
WIDTH = 240  # pixels: the page shows 96x120 (2.5x)
MAX_SMALL = 400  # shrunk copies a state (each is a file in the deployment: Cloudflare Pages allows 20,000)
SHRINK_SECONDS = 120  # of downloading a run; the rest wait for the next run


def ballotpedia(url):
    """Ballotpedia's photo storage (linked only when there's no official photo; never copied)."""
    parts = url.split("/")
    return len(parts) > 3 and (parts[2].lower() == "cdn.ballotpedia.org" or
                               (parts[2].lower() == "s3.amazonaws.com" and parts[3].startswith("ballotpedia-api")))


def official(url):
    if not url or not url.startswith(("http://", "https://")):
        return False
    host = url.split("/")[2].lower()
    if ballotpedia(url):
        return True
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


_ROBOTS = {}


def robots(url):
    """The host's robots.txt (urllib.robotparser), read once a run; None when it can't be read (a 404: everything
    allowed, as robotparser itself takes it)."""
    import urllib.robotparser
    host = "/".join(url.split("/")[:3])
    if host not in _ROBOTS:
        rp = urllib.robotparser.RobotFileParser()
        try:
            r = urllib.request.urlopen(urllib.request.Request(host + "/robots.txt", headers=UA), timeout=20)
            body = r.read(500_000).decode("utf-8", "replace").lstrip("\ufeff")  # (flsenate.gov's starts with a BOM)
            kind = (r.headers.get("Content-Type") or "").lower()
            # (A site answering every address with its home page, as flhouse.gov's old name did, has no robots.txt.)
            rp.parse(body.splitlines() if "html" not in kind else [])
        except urllib.error.HTTPError as e:
            # (RFC 9309: a robots.txt answering 4xx means no rules (S3 and CloudFront answer 403 for a missing one);
            # 5xx means the site may be down: all disallowed for now.)
            rp.parse([] if 400 <= e.code < 500 else ["User-agent: *", "Disallow: /"])
        except Exception:
            rp = None  # (not reached: treated as no rules, as before robots.txt was read)
        _ROBOTS[host] = rp
    return _ROBOTS[host]


def allowed(url):
    rp = robots(url)
    return True if rp is None else rp.can_fetch(UA["User-Agent"], url)


def crawl_delay(url):
    rp = robots(url)
    try:
        d = rp.crawl_delay(UA["User-Agent"]) if rp else None
    except Exception:
        d = None
    return float(d or 0)


_LAST = {}


def pace(url, least=0.5):
    """Waits so requests to one host are its Crawl-delay apart (at least `least` seconds)."""
    host = url.split("/")[2]
    wait = _LAST.get(host, 0) + max(least, crawl_delay(url)) - time.time()
    if wait > 0:
        time.sleep(wait)
    _LAST[host] = time.time()


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
    """(verdict, size): "ok" when an address answers 200 with an image no heavier than HEAVY; "big" when it's heavier
    (shrunk: shrink()), "bad" when it answers otherwise (404, a web page, over BIG); "net" when it doesn't answer here (a timeout; a certificate chain Python can't complete, as
    Illinois's and the Michigan House's, which browsers do): kept, as a browser may well load it. When HEAD fails, the
    first byte is asked for instead: servers answer HEAD in their own ways (Georgia's 405; Massachusetts's 404 for photos
    a GET gets; Colorado's redirect to signed addresses that answer HEAD 403)."""
    r = None
    for method, extra in (("HEAD", {}), ("GET", {"Range": "bytes=0-0"})):
        if method == "GET":
            pace(url)  # (the second request keeps the host's Crawl-delay too)
        try:
            r = urllib.request.urlopen(urllib.request.Request(url, method=method, headers={**UA, **extra}), timeout=10)
            break
        except urllib.error.HTTPError as e:
            if method == "GET" and e.code in (400, 404, 410):
                return "bad", 0
        except Exception:
            if method == "GET":
                return "net", 0
    if r is None:
        return "net", 0
    kind = (r.headers.get("Content-Type") or "").lower()
    total = re.search(r"/(\d+)$", r.headers.get("Content-Range") or "")
    size = int(total.group(1) if total else r.headers.get("Content-Length") or 0)
    r.close()
    # (Georgia's photos say application/octet-stream; browsers show them.)
    if r.status not in (200, 206) or not (kind.startswith("image/") or "octet-stream" in kind) or size > BIG:
        return "bad", size
    return ("big" if size > HEAVY else "ok"), size


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
        if not allowed(url):
            # Never asked for (robots.txt): linked only when an answer from before robots.txt was read showed a light
            # photo (visitors' browsers load it, as from the legislature's own page); unknown or heavy ones left out,
            # since they can't be checked or copied small.
            return "ok" if old and old[0] == "ok" else "bad"
        # (Answers saved before sizes were, [verdict, time], are asked again: 5 MB originals were "bad" then.)
        if old and len(old) > 2 and time.time() - old[1] < (4 * WEEK if crawl_delay(url) >= 5 else WEEK):
            return old[0]
        if time.time() > self.until:
            return old[0] if old and len(old) > 2 else None
        pace(url)
        v, size = head(url)
        self.seen[url] = [v, int(time.time()), size]
        self.changed = True
        return v

    def size(self, url):
        old = self.seen.get(url)
        return old[2] if old and len(old) > 2 else 0

    def save(self):
        """Saved when something was asked; addresses no longer asked about (members gone) are dropped."""
        if not self.changed:
            return
        self.seen = {u: v for u, v in self.seen.items() if u in self.asked}
        with open(self.path + ".tmp", "w") as f:
            json.dump(self.seen, f, indent=0, sort_keys=True)
        os.replace(self.path + ".tmp", self.path)


# ---- heavy photos: small copies ----

def shrink(url, size=0):
    """A heavy photo as a WIDTH-pixel JPEG (bytes), or None when it doesn't load or isn't a picture Pillow reads.
    A download shorter than the size the server gave is a failure (tried again in a week); a file the server itself
    serves cut short is read as browsers show it (Georgia serves two portraits cut at exactly 1 MiB: the last rows grey)."""
    from PIL import Image, ImageFile, ImageOps
    ImageFile.LOAD_TRUNCATED_IMAGES = True
    try:
        r = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60)
        raw = r.read(BIG + 1)
        r.close()
    except Exception as e:
        print(f"   {url}: didn't load ({str(e)[:80]})")
        return None
    if len(raw) > BIG or (size and len(raw) < size):
        return None
    try:
        im = ImageOps.exif_transpose(Image.open(io.BytesIO(raw)))
        if im.mode in ("RGBA", "LA", "P", "PA"):
            im = im.convert("RGBA")
            back = Image.new("RGB", im.size, (255, 255, 255))
            back.paste(im, mask=im.split()[-1])
            im = back
        elif im.mode != "RGB":
            im = im.convert("RGB")
        if im.width > WIDTH:
            im = im.resize((WIDTH, max(1, round(im.height * WIDTH / im.width))), Image.LANCZOS)
        out = io.BytesIO()
        im.save(out, "JPEG", quality=80, optimize=True, progressive=True)
        return out.getvalue()
    except Exception as e:
        print(f"   {url}: not read as a picture ({str(e)[:80]})")
        return None


class Small:
    """The shrunk copies, data/<state>/photos/<name>.jpg, and what they were made from (photos/index.json:
    {url: [name, original's size, time]}; a name of "" is a copy that failed, tried again after a week)."""
    def __init__(self, folder, budget=SHRINK_SECONDS):
        self.dir = os.path.join(folder, "photos")
        self.path = os.path.join(self.dir, "index.json")
        try:
            self.index = json.load(open(self.path))
        except (OSError, ValueError):
            self.index = {}
        self.until = time.time() + budget
        self.changed = False
        self.made = 0

    def name(self, url, size):
        """The copy's file name, made first when there's none for this address and size; None when there's none."""
        name = hashlib.sha256(f"{url} {size}".encode()).hexdigest()[:16] + ".jpg"
        old = self.index.get(url)
        if old and old[0] == name and os.path.exists(os.path.join(self.dir, name)):
            return name
        if old and old[0] == "" and old[1] == size and time.time() - old[2] < WEEK:
            return None
        if ballotpedia(url) or time.time() > self.until or not allowed(url):
            return None
        try:
            import PIL  # noqa: F401 (installed in download.yml; without it heavy photos are left out)
        except ImportError:
            return None
        pace(url, 1)
        data = shrink(url, size)
        self.changed = True
        if not data:
            self.index[url] = ["", size, int(time.time())]
            return None
        os.makedirs(self.dir, exist_ok=True)
        with open(os.path.join(self.dir, name + ".tmp"), "wb") as f:
            f.write(data)
        os.replace(os.path.join(self.dir, name + ".tmp"), os.path.join(self.dir, name))
        self.index[url] = [name, size, int(time.time())]
        self.made += 1
        return name

    def save(self, keep):
        """Copies no longer used (members gone, photos changed) are deleted with their lines."""
        index = {u: v for u, v in self.index.items() if u in keep}
        names = {v[0] for v in index.values() if v[0]}
        gone = [f for f in (os.listdir(self.dir) if os.path.isdir(self.dir) else [])
                if f.endswith(".jpg") and f not in names]
        for f in gone:
            os.remove(os.path.join(self.dir, f))
        if index != self.index or self.changed or gone:
            self.index = index
            os.makedirs(self.dir, exist_ok=True)
            with open(self.path + ".tmp", "w") as f:
                json.dump(index, f, indent=0, sort_keys=True)
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


def build(folder, st, src, check=lambda url: None, roster=None):
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
        session = int(re.search(r"(\d{4})", os.path.basename(path)).group(1))
        for seat, p in sorted(people.items()):
            if p.get("image"):
                continue
            i = match(seat, p, recs, used, seat[0] in strict)
            url = None
            if i is not None:
                used.add(i)
                url = https(recs[i]["image"]) if official(recs[i]["image"]) else None
            # The legislature's own (only for the newest contacts: Louisiana's is whoever holds the seat now), when it
            # answers with an image.
            newest = path == contacts_files(folder)[-1]
            own = PATTERNS[st](seat, p, session, folder) if st in PATTERNS and newest else None
            own = own or ((roster or {}).get(seat) if newest else None)
            if own and check(own) in ("ok", "big"):
                url = own
            if url and check(url) != "bad":
                out[f"{seat[0]}|{p['key']}"] = url
    return out


def refresh(folder, force=False):
    began = time.time()
    st = os.path.basename(os.path.normpath(folder))
    if not re.fullmatch(r"[a-z]{2}", st) or st == "ny" or not os.path.isdir(folder) or not contacts_files(folder):
        return
    src = source(folder, st, force)
    if not src:
        return
    # (Hosts with a crawl delay get more time: New Hampshire's 400 photos at 11 seconds take a few runs.)
    check = Checks(folder, budget=600 if st in ("nh", "fl") else 150)
    images = build(folder, st, src, check, rosters(folder, st, force))
    check.save()
    # Heavy photos: their small copies, else left out (not made yet: the next run makes more; over MAX_SMALL; Ballotpedia's).
    small, heavy = Small(folder), sorted({u for u in images.values() if check(u) == "big"})
    names = {}
    for url in heavy:
        if len(names) >= MAX_SMALL:
            print(f"{st}: over {MAX_SMALL} heavy photos; the rest left out (MAX_SMALL)")
            break
        name = small.name(url, check.size(url))
        if name:
            names[url] = name
    small.save(set(heavy))
    # (Until its copy is made, a photo up to LINK_MAX is linked as before.)
    images = {k: u for k, u in images.items() if u not in heavy or u in names or check.size(u) <= LINK_MAX}
    if heavy:
        print(f"{st}: {len(heavy)} heavy photos, {len(names)} with small copies ({small.made} made this run)")
    # Members still without one: Wikidata's portrait, from Commons (light thumbnails: never shrunk).
    try:
        # (Within the step's 8 minutes: what's left of RUN_SECONDS, else only the answers already saved.)
        credits = add_wikidata(folder, st, images, max(0, min(WD_SECONDS, began + RUN_SECONDS - time.time())))
    except Exception as e:  # (the photos found so far still count)
        print(f"{st}: Wikidata fallback failed ({str(e)[:120]})")
        credits = {}
    path = os.path.join(folder, "photos.json")
    out = {"source": "unitedstates/images" if st == "us" else "Open States people", "fetched": src.get("fetched"),
           "images": dict(sorted(images.items()))}
    if names:
        out["small"] = dict(sorted(names.items()))
    if credits:
        out["credits"] = dict(sorted(credits.items()))
    try:
        same = json.load(open(path)) == out
    except (OSError, ValueError):
        same = False
    if not same:
        with open(path + ".tmp", "w") as f:
            json.dump(out, f, indent=0, sort_keys=True)
        os.replace(path + ".tmp", path)
    print(f"{st}: {len(images)} photos added{'' if not same else ' (unchanged)'}")


# ---- Wikidata and Wikimedia Commons: the last resort ----
#
# For members still without a photo (no contacts' own, no official or Ballotpedia one robots.txt lets us use), the
# portrait Wikidata gives them (P18), linked as a Commons thumbnail, with its author and license for the credit.
# Each state's members of each house are one SPARQL query (people holding the house's member position, P39, with the
# district (P768) and dates of each term), asked monthly; members not found there are looked up by name, once a month
# each, and kept only when one person has that name and their description names the state's legislature.
# (query.wikidata.org's and commons.wikimedia.org's robots.txt disallow /sparql and /w/ for crawlers; these are the
# query service and API Wikimedia offers programs, used here as its User-Agent policy and API etiquette ask: an honest
# User-Agent, one request at a time, a second apart, maxlag. The photos themselves are on upload.wikimedia.org, which
# robots.txt allows.)

WD_UA = {"User-Agent": "StateBillTracker/1.0 (https://statebilltracker.org/; legislators' photos, a monthly request) "
                       "Python-urllib"}
MONTH = 30 * 86400
WD_SECONDS = 120  # of asking Wikidata and Commons a run; the rest waits for the next run
RUN_SECONDS = 420  # a state's whole photos run (download.yml's step stops it at 8 minutes)
WD_WIDTH = 330  # pixels: one of Wikimedia's standard thumbnail widths (https()), over WIDTH
# Each house's member position on Wikidata ("member of the Colorado House of Representatives"), by the seat's first
# letter: "S" the upper house, "L" Nebraska's Legislature, "B" the Council of the District of Columbia, any other the
# lower house ("H", "A"). Found by their "subclass of" (member of United States state lower house; state senator) and
# "applies to jurisdiction" (the state), checked by name, 2026-11-22.
POSITIONS = {
    "al": ("Q18648747", "Q20058764"), "ak": ("Q26265831", "Q21360107"), "az": ("Q17486298", "Q21360913"),
    "ar": ("Q19681513", "Q21361754"), "ca": ("Q18180908", "Q19690441"), "co": ("Q17485005", "Q20064489"),
    "ct": ("Q18763331", "Q19831739"), "de": ("Q22679266", "Q21362489"), "fl": ("Q18342844", "Q19961062"),
    "ga": ("Q17548315", "Q20065663"), "hi": ("Q19319643", "Q20058751"), "id": ("Q17546641", "Q18655026"),
    "il": ("Q17495450", "Q20058778"), "in": ("Q18190880", "Q19362907"), "ia": ("Q17486706", "Q18707052"),
    "ks": ("Q17487134", "Q19617175"), "ky": ("Q20065966", "Q20066070"), "la": ("Q17355090", "Q18091440"),
    "me": ("Q18713970", "Q18342769"), "md": ("Q20064986", "Q20064926"), "ma": ("Q17342542", "Q20058776"),
    "mi": ("Q18654736", "Q18675883"), "mn": ("Q17505193", "Q21363942"), "ms": ("Q17487661", "Q18195558"),
    "mo": ("Q18131809", "Q21364537"), "mt": ("Q17496847", "Q21365323"), "nv": ("Q18341124", "Q20064517"),
    "nh": ("Q21971205", "Q19264592"), "nj": ("Q18536527", "Q19385767"), "nm": ("Q17631457", "Q20658713"),
    "ny": ("Q20058770", "Q18691526"), "nc": ("Q18089655", "Q19727887"), "nd": ("Q19360961", "Q21366730"),
    "oh": ("Q17502533", "Q20065429"), "ok": ("Q18925362", "Q21367377"), "or": ("Q19360415", "Q19689183"),
    "pa": ("Q14616716", "Q18199902"), "ri": ("Q20058759", "Q19397347"), "sc": ("Q19754409", "Q18676729"),
    "sd": ("Q19360976", "Q6814783"), "tn": ("Q18538054", "Q18534307"), "tx": ("Q18604553", "Q18565274"),
    "ut": ("Q18810381", "Q20065565"), "vt": ("Q17484018", "Q20065418"), "va": ("Q20065408", "Q18604340"),
    "wa": ("Q17598395", "Q20065405"), "wv": ("Q19772501", "Q21368444"), "wi": ("Q18526160", "Q17602055"),
    "wy": ("Q18341783", "Q19394559"), "us": ("Q13218630", "Q4416090"),
}
ONE_HOUSE = {"ne": ("L", "Q20065395"), "dc": ("B", "Q54855275")}
STATE_NAMES = {
    "al": "Alabama", "ak": "Alaska", "az": "Arizona", "ar": "Arkansas", "ca": "California", "co": "Colorado",
    "ct": "Connecticut", "de": "Delaware", "fl": "Florida", "ga": "Georgia", "hi": "Hawaii", "id": "Idaho",
    "il": "Illinois", "in": "Indiana", "ia": "Iowa", "ks": "Kansas", "ky": "Kentucky", "la": "Louisiana", "me": "Maine",
    "md": "Maryland", "ma": "Massachusetts", "mi": "Michigan", "mn": "Minnesota", "ms": "Mississippi", "mo": "Missouri",
    "mt": "Montana", "ne": "Nebraska", "nv": "Nevada", "nh": "New Hampshire", "nj": "New Jersey", "nm": "New Mexico",
    "ny": "New York", "nc": "North Carolina", "nd": "North Dakota", "oh": "Ohio", "ok": "Oklahoma", "or": "Oregon",
    "pa": "Pennsylvania", "ri": "Rhode Island", "sc": "South Carolina", "sd": "South Dakota", "tn": "Tennessee",
    "tx": "Texas", "ut": "Utah", "vt": "Vermont", "va": "Virginia", "wa": "Washington", "wv": "West Virginia",
    "wi": "Wisconsin", "wy": "Wyoming", "dc": "District of Columbia", "us": "United States"}
# Files that aren't portraits (a signature, a coat of arms), whatever P18 says.
NOT_PORTRAIT = re.compile(r"(?i)signature|autograph|logo|seal|coat of arms|flag|map\b|\.(svg|pdf|djvu|webm|ogv)$")


def position_of(st, seat):
    if st in ONE_HOUSE:
        return ONE_HOUSE[st][1]
    pair = POSITIONS.get(st)
    return pair and (pair[1] if seat[0] == "S" else pair[0])


def wd_get(url, data=None, headers=None):
    pace(url, 1)
    req = urllib.request.Request(url, data=data, headers={**WD_UA, **(headers or {})})
    with urllib.request.urlopen(req, timeout=90) as r:
        return json.load(r)


def sparql(q):
    try:
        return _sparql(q)
    except urllib.error.HTTPError as e:
        if e.code not in (500, 502, 503, 504):
            raise
        time.sleep(10)  # (the query service is busy now and then: once more, a little later)
        return _sparql(q)


def _sparql(q):
    return wd_get("https://query.wikidata.org/sparql", urllib.parse.urlencode({"query": q}).encode(),
                  {"Accept": "application/sparql-results+json",
                   "Content-Type": "application/x-www-form-urlencoded"})["results"]["bindings"]


def qid(uri):
    return (uri or "").rsplit("/", 1)[-1]


def file_name(uri):
    """"Name.jpg" from a Special:FilePath address (as SPARQL gives P18)."""
    return urllib.parse.unquote(uri.rsplit("/", 1)[-1]).replace("_", " ") if uri else ""


def holders(st):
    """{qid: {"names": [..], "desc", "image", "born" (year), "died", "terms": [[house letter, start, end, district
    label]]}}: everyone Wikidata says held one of the state's member positions with a term ending in 2019 or later, or
    with no end, leaving out people who died before 2019 or were born before 1930. One query a house for the terms,
    then the people's names and photos 300 at a time (one query for everything timed out for the biggest houses:
    Massachusetts's, Iowa's, the U.S. House)."""
    pos = ({ONE_HOUSE[st][0]: ONE_HOUSE[st][1]} if st in ONE_HOUSE else
           {"H": POSITIONS[st][0], "S": POSITIONS[st][1]})
    out = {}
    for house, position in pos.items():
        q = """
SELECT ?person ?start ?end ?distL WHERE {
  ?person p:P39 ?stmt. ?stmt ps:P39 wd:%s.
  OPTIONAL { ?stmt pq:P582 ?end }
  FILTER(!BOUND(?end) || ?end >= "2019-01-01T00:00:00Z"^^xsd:dateTime)
  FILTER NOT EXISTS { ?person wdt:P570 ?died. FILTER(?died < "2019-01-01T00:00:00Z"^^xsd:dateTime) }
  FILTER NOT EXISTS { ?person wdt:P569 ?born. FILTER(?born < "1930-01-01T00:00:00Z"^^xsd:dateTime) }
  OPTIONAL { ?stmt pq:P580 ?start }
  OPTIONAL { ?stmt pq:P768 ?dist. OPTIONAL { ?dist rdfs:label ?distL. FILTER(LANG(?distL) = "en") } }
}""" % position
        for b in sparql(q):
            r = {k: v["value"] for k, v in b.items()}
            p = out.setdefault(qid(r["person"]), {"names": [], "desc": "", "image": "", "born": "", "died": "", "terms": []})
            term = [house, r.get("start", "")[:10], r.get("end", "")[:10], r.get("distL", "")]
            if term not in p["terms"]:
                p["terms"].append(term)
    ids = sorted(out)
    for i in range(0, len(ids), 300):
        q = """
SELECT ?person ?desc ?img ?born ?died
       (GROUP_CONCAT(DISTINCT ?label; separator="|") AS ?labels) (GROUP_CONCAT(DISTINCT ?alias; separator="|") AS ?aliases) WHERE {
  VALUES ?person { %s }
  OPTIONAL { ?person rdfs:label ?label. FILTER(LANG(?label) = "en" || LANG(?label) = "mul") }
  OPTIONAL { ?person skos:altLabel ?alias. FILTER(LANG(?alias) = "en") }
  OPTIONAL { ?person schema:description ?desc. FILTER(LANG(?desc) = "en") }
  OPTIONAL { ?person wdt:P18 ?img }
  OPTIONAL { ?person wdt:P569 ?born }
  OPTIONAL { ?person wdt:P570 ?died }
} GROUP BY ?person ?desc ?img ?born ?died""" % " ".join("wd:" + x for x in ids[i:i + 300])
        for b in sparql(q):
            r = {k: v["value"] for k, v in b.items()}
            p = out[qid(r["person"])]
            for n in (r.get("labels") or "").split("|") + (r.get("aliases") or "").split("|"):
                if n and n not in p["names"]:
                    p["names"].append(n)
            p["desc"] = p["desc"] or r.get("desc", "")
            p["image"] = p["image"] or file_name(r.get("img"))
            p["born"] = p["born"] or r.get("born", "")[:4]
            p["died"] = p["died"] or r.get("died", "")[:10]
    return out


def by_names(names):
    """{name: [[qid, description, image file], ...]}: people (humans) with that English label or alias."""
    values = " ".join(json.dumps(n) + lang for n in names for lang in ("@en", "@mul"))
    q = """
SELECT ?name ?person ?desc ?img WHERE {
  VALUES ?name { %s }
  { ?person rdfs:label ?name } UNION { ?person skos:altLabel ?name }
  ?person wdt:P31 wd:Q5.
  OPTIONAL { ?person schema:description ?desc. FILTER(LANG(?desc) = "en") }
  OPTIONAL { ?person wdt:P18 ?img }
}""" % values
    out = {n: {} for n in names}
    for b in sparql(q):
        r = {k: v["value"] for k, v in b.items()}
        same = out.setdefault(r["name"], {})
        q_ = qid(r["person"])
        old = same.get(q_, [q_, "", ""])
        same[q_] = [q_, old[1] or r.get("desc", ""), old[2] or file_name(r.get("img"))]
    return {n: list(v.values()) for n, v in out.items()}


def commons_info(files):
    """{file: {"src", "page", "author", "license", "about"}} from Commons' imageinfo, 50 files a request."""
    out = {}
    files = sorted(set(f for f in files if f))
    for i in range(0, len(files), 50):
        part = files[i:i + 50]
        q = urllib.parse.urlencode({"action": "query", "format": "json", "formatversion": 2, "prop": "imageinfo",
                                    "iiprop": "url|extmetadata", "iiurlwidth": WD_WIDTH, "maxlag": 5,
                                    "titles": "|".join("File:" + f for f in part),
                                    "iiextmetadatafilter": "Artist|LicenseShortName|ImageDescription|ObjectName"})
        data = wd_get("https://commons.wikimedia.org/w/api.php?" + q).get("query", {})
        asked = {"File:" + f: f for f in part}
        for n in data.get("normalized", []):
            asked[n["to"]] = asked.get(n["from"], n["from"][5:])
        for p in data.get("pages", []):
            info = (p.get("imageinfo") or [{}])[0]
            f = asked.get(p["title"], p["title"][5:])
            if not info.get("thumburl"):
                out[f] = {}
                continue
            m = info.get("extmetadata", {})
            val = lambda k: re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", m.get(k, {}).get("value", "") or "")).strip()
            author = val("Artist")
            if re.match(r"(?i)unknown author", author):
                author = ""
            out[f] = {"src": https(info["thumburl"].split("?")[0]), "page": info.get("descriptionurl", ""),
                      "author": author[:120].rstrip(". "), "license": val("LicenseShortName"),
                      "about": (val("ObjectName") + " | " + val("ImageDescription"))[:240]}
    return out


def names_of(p):
    """A member's name as Wikidata may write it: "Carl L. Anderson", "Carl Anderson", the nickname in quotes."""
    name = re.sub(r"\s+", " ", (p.get("name") or "").replace(" ", " ")).strip()
    out = [name]
    plain = re.sub(r"\s*[\"“(][^\"”)]*[\"”)]\s*", " ", name).strip()
    words = [w for i, w in enumerate(plain.split()) if i == 0 or not re.fullmatch(r"[A-Z]\.?", w)]
    out += [plain, " ".join(words)]
    words = [w for w in words if not re.fullmatch(r"(?i)(jr|sr|ii|iii|iv)\.?,?", w)]
    out.append(" ".join(words).rstrip(","))
    nick = re.search(r"[\"“(]([^\"”)]+)[\"”)]", name)
    if nick and len(words) > 1:
        out.append(f"{nick.group(1)} {words[-1]}")
    return [n for i, n in enumerate(out) if n and n not in out[:i]]


def same_person(p, names):
    """Whether a contacts member and a Wikidata person's names fit: the same surname and a first name (or nickname, or
    another given name) that fits."""
    mine = norm(p.get("name")) or norm(p.get("key"))
    if not mine:
        return False
    last, first, given = mine[-1], mine[0], set(w for w in mine[:-1] if len(w) > 1)
    for n in names:
        theirs = norm(n)
        if len(theirs) < 2:
            continue
        if not (theirs[-1] == last or last in theirs[1:] or theirs[-1] in mine[1:]):
            continue
        f = theirs[0]
        if f == first or NICK.get(f) == first or NICK.get(first) == f or NICK.get(f, 1) == NICK.get(first, 2) \
                or (min(len(f), len(first)) >= 3 and (f.startswith(first) or first.startswith(f))) \
                or given & set(w for w in theirs[:-1] if len(w) > 1):
            return True
    return False


class Wiki:
    """The fallback's answers, data/<state>/photos_wikidata.json: {"t", "holders", "names": {name: [t, [candidates]]},
    "files": {file: [t, info]}}, each asked again after a month; a failed request keeps the last copy."""
    def __init__(self, folder, st, budget=WD_SECONDS):
        self.st, self.path = st, os.path.join(folder, "photos_wikidata.json")
        try:
            self.d = json.load(open(self.path))
        except (OSError, ValueError):
            self.d = {}
        self.until = time.time() + budget
        self.changed = False

    def busy(self):
        return time.time() > self.until

    def holders(self):
        if (not self.d.get("holders") or time.time() - self.d.get("t", 0) > MONTH) and not self.busy():
            try:
                h = holders(self.st)
                if h or not self.d.get("holders"):
                    self.d.update(t=int(time.time()), holders=h)
                    self.changed = True
            except Exception as e:
                print(f"{self.st}: Wikidata's members didn't load ({str(e)[:100]}); kept the last copy")
        return self.d.get("holders") or {}

    def names(self, wanted):
        cache = self.d.setdefault("names", {})
        ask = sorted(n for n in wanted if n not in cache or time.time() - cache[n][0] > MONTH)
        for i in range(0, len(ask), 20):
            if self.busy():
                break
            try:
                got = by_names(ask[i:i + 20])
            except Exception as e:
                print(f"{self.st}: Wikidata's names didn't load ({str(e)[:100]})")
                break
            for n in ask[i:i + 20]:
                cache[n] = [int(time.time()), got.get(n, [])]
            self.changed = True
        return {n: cache[n][1] for n in wanted if n in cache}

    def files(self, wanted):
        cache = self.d.setdefault("files", {})
        ask = sorted(f for f in wanted if f not in cache or time.time() - cache[f][0] > MONTH)
        for i in range(0, len(ask), 50):
            if self.busy():
                break
            try:
                got = commons_info(ask[i:i + 50])
            except Exception as e:
                print(f"{self.st}: Commons didn't answer ({str(e)[:100]})")
                break
            for f in ask[i:i + 50]:
                if f in got:
                    cache[f] = [int(time.time()), got[f]]
            self.changed = True
        return {f: cache[f][1] for f in wanted if f in cache and cache[f][1]}

    def save(self, names, files):
        """Saved when something was asked; names and files no longer wanted are dropped."""
        self.d["names"] = {n: v for n, v in self.d.get("names", {}).items() if n in names}
        self.d["files"] = {f: v for f, v in self.d.get("files", {}).items() if f in files}
        if not self.changed:
            return
        with open(self.path + ".tmp", "w") as f:
            json.dump(self.d, f, indent=0, sort_keys=True)
        os.replace(self.path + ".tmp", self.path)


def legislature_words(st, house):
    """Whether a Wikidata description names this state's legislature (and the member's house, when it says)."""
    state = STATE_NAMES.get(st, "")
    if st == "us":
        return lambda d: bool(re.search(r"(?i)\b(congress(wo)?man|u\.?s\.? (representative|senator)|united states "
                                        r"(representative|senator)|member of the u\.?s\.? house)", d))
    upper, lower = r"senat", r"house|assembly|delegate|representative"
    house_re = {"S": upper, "L": upper + "|legislat", "B": r"council"}.get(house, lower)
    return lambda d: bool(state and state.lower() in d.lower() and re.search(r"(?i)" + house_re, d)
                          and not re.search(r"(?i)\b(u\.?s\.?|united states|congress)", d))


def wikidata(folder, st, wanted, budget=WD_SECONDS):
    """{"<house>|<name key>": (file, how)} for wanted members ([(seat, person, session)]), from Wikidata: someone who
    held the member's house's position in a term reaching the session, with a fitting name (and district, where the
    house's Wikidata districts are its seat numbers), and no other such person; else one person by that exact name whose
    description names the state's legislature. Returns (found, Wiki) so the caller can save it."""
    w = Wiki(folder, st, budget)
    if not wanted or (st not in POSITIONS and st not in ONE_HOUSE):
        return {}, w
    people = w.holders()
    found, unresolved = {}, []
    cands = {}
    for seat, p, session in wanted:
        pos_house = seat[0] if st in ONE_HOUSE else ("S" if seat[0] == "S" else "H")
        begun = f"{session}-01-01"
        same, other = [], []
        for q, r in people.items():
            # (Not someone who died before the session, or was born before 1930: a namesake from long ago, whose
            # terms Wikidata often has without dates.)
            if (r.get("died") and r["died"] < begun) or (r.get("born") and r["born"] < "1930") \
                    or not same_person(p, r["names"]):
                continue
            mine = [t for t in r["terms"] if t[0] == pos_house and (not t[2] or t[2] >= begun)]
            if mine:
                same.append((q, mine))
            elif r.get("born") or any(t[1] >= "2000" or t[2] for t in r["terms"]):
                other.append((q, []))
        # Someone Wikidata has only in the other house (a representative since elected to the Senate, the statement not
        # yet added) counts when no one fits in the member's own house; districts aren't compared then. (One with only
        # undated terms there is checked by name below: the only person of that name.)
        cands[(seat, p["key"], session)] = same or other
    # Districts count where the house's Wikidata districts are its seat numbers (90% of the single matches agree).
    agree, n = Counter(), Counter()
    for (seat, key, session), c in cands.items():
        ds = {digits(t[3]) for t in (c[0][1] if len(c) == 1 else []) if digits(t[3])}
        if ds and digits(seat[2:]):
            n[seat[0]] += 1
            agree[seat[0]] += digits(seat[2:]) in ds
    numbered_ = {h for h in n if n[h] >= 3 and agree[h] >= 0.9 * n[h]}
    for seat, p, session in wanted:
        c = cands[(seat, p["key"], session)]
        if seat[0] in numbered_ and digits(seat[2:]):
            # (A term with no district recorded doesn't rule a person out.)
            c = [x for x in c if any(not digits(t[3]) or digits(t[3]) == digits(seat[2:]) for t in x[1])] or []
            if len(c) > 1:
                exact = [x for x in c if any(digits(t[3]) == digits(seat[2:]) for t in x[1])]
                c = exact if len(exact) == 1 else c
        if len(c) > 1:
            # (Someone whose term has dates beats a namesake with none, often a member from long ago.)
            dated = [x for x in c if any(t[1] for t in x[1])]
            c = dated if len(dated) == 1 else c
        k = f"{seat[0]}|{p['key']}"
        if len(c) == 1:
            r = people[c[0][0]]
            if r["image"] and not NOT_PORTRAIT.search(r["image"]):
                found[k] = (r["image"], f"held the position: {c[0][0]} {r['names'][0]} ({r['desc']})")
        elif not cands[(seat, p["key"], session)]:
            # (Not when the district ruled the only ones out.)
            unresolved.append((seat, p))
    # Not found holding the position: one person by exactly that name, described as one of the state's legislators.
    names = {}
    for seat, p in unresolved:
        names[(seat, p["key"])] = names_of(p)
    answers = w.names(sorted({n for v in names.values() for n in v})) if names else {}
    for (seat, key), ns in names.items():
        k = f"{seat[0]}|{key}"
        if k in found or not all(n in answers for n in ns):
            continue
        c = {x[0]: x for n in ns for x in answers[n]}
        if len(c) != 1:
            continue
        q, desc, img = next(iter(c.values()))
        # (The only person of that name, who held a seat in this state's legislature, or is described as a member.)
        held = people.get(q)
        if held and ((held.get("died") and held["died"] < "2019") or (held.get("born") and held["born"] < "1930")):
            continue
        if img and (held or legislature_words(st, seat[0])(desc)) and not NOT_PORTRAIT.search(img):
            found[k] = (img, f"by name{', held a seat' if held else ''}: {q} ({desc})")
    w.names_asked = {n for v in names.values() for n in v}
    return found, w


def add_wikidata(folder, st, images, budget=WD_SECONDS):
    """Adds Commons photos for members of every contacts file that have none; returns {url: credit}."""
    wanted, seen = [], set()
    for path in reversed(contacts_files(folder)):  # (a member's newest session)
        session = int(re.search(r"(\d{4})", os.path.basename(path)).group(1))
        for seat, p in sorted(json.load(open(path)).get("people", {}).items()):
            k = f"{seat[0]}|{p.get('key')}"
            if p.get("image") or k in images or k in seen or not p.get("key"):
                continue
            seen.add(k)
            wanted.append((seat, p, session))
    found, w = wikidata(folder, st, wanted, budget)
    info = w.files(sorted({f for f, _ in found.values()}))
    credits = {}
    for k, (f, how) in found.items():
        i = info.get(f)
        if i and i.get("src", "").startswith(("https://upload.wikimedia.org/", "https://thumb.wikimedia.org/")):
            images[k] = i["src"]
            credits[i["src"]] = {"file": f, "page": i["page"], "author": i["author"], "license": i["license"]}
    w.save(getattr(w, "names_asked", set()), {f for f, _ in found.values()})
    if wanted:
        print(f"{st}: {len(credits)} of {len(wanted)} members without a photo found on Wikidata")
    return credits


def credit_of(folder, url):
    """"Photo: author, license, via Wikimedia Commons" for a Commons photo the fallback added, else ""."""
    c = _read(folder).get("credits", {}).get(url)
    if not c:
        return ""
    lic = c.get("license") or ""
    by = "" if lic.lower() in ("public domain", "cc0") or not c.get("author") else c["author"]
    return "Photo: " + ", ".join(x for x in (by, lic, "via Wikimedia Commons") if x)


def uses_commons(folder):
    return bool(_read(folder).get("credits"))


# ---- reading (build_data.py, test/data_check.py) ----

_CACHE = {}


def _read(folder):
    if folder not in _CACHE:
        try:
            _CACHE[folder] = json.load(open(os.path.join(folder, "photos.json")))
        except (OSError, ValueError):
            _CACHE[folder] = {}
    return _CACHE[folder]


def load(folder):
    return _read(folder).get("images", {})


def small_copies(folder):
    """{name: path} of the shrunk copies photos.json uses (build_data.py copies them to /assets/photos/)."""
    return {n: os.path.join(folder, "photos", n) for n in _read(folder).get("small", {}).values()
            if os.path.exists(os.path.join(folder, "photos", n))}


def image_of(folder, seat, p, local=None):
    """A member's photo: their contacts' own, else photos.json's. local(name): the site's address for a shrunk copy
    (without it, as in the Claude copies, the original's address)."""
    url = p.get("image") or load(folder).get(f"{seat[0]}|{p.get('key')}")
    name = _read(folder).get("small", {}).get(url)
    return local(name) if local and name and name in small_copies(folder) else url


def uses_ballotpedia(folder):
    return any(ballotpedia(u) for u in load(folder).values())


if __name__ == "__main__":
    force = "--force" in sys.argv
    for a in sys.argv[1:]:
        if not a.startswith("--"):
            try:
                refresh(a, force)
            except Exception as e:  # one state's trouble mustn't stop the others (or the download)
                print(f"{a}: photos not updated ({e})")
