#!/usr/bin/env python3
"""Washington's legislators and committees, written as data/wa/contacts_<session>.json in the shape build_data.py reads.

- Who sits now: leg.wa.gov's legislator list (147 cards, each with the member id the web services and roll calls use,
  chamber, district, party, leadership positions and a photo). Each district has a senator and two representatives;
  their seat ids are "S:21", and "H:21a"/"H:21b" for the representatives in order of last name (New Jersey's scheme).
- Phones and emails: the web services' member list (data/wa/<session>/sponsors.json, from states/wa/fetch.py).
- Committees: each committee's page on leg.wa.gov (chair, vice chairs, ranking members, then the member table).
leg.wa.gov has no robots.txt; the web services' own site asks crawlers away, so its pages aren't used (see the
wa-data-sources memory). Usage: python3 states/wa/contacts.py [session]
"""
import html, json, os, re, sys, time, urllib.request
from datetime import datetime
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
from fetch_contacts import committee_key, name_key
from states.wa import profile as P

SITE = "https://leg.wa.gov"
AGENT = "statebilltracker.org (a nonprofit bill tracker; contact via github.com/judithhubbard)"
PARTY = {"D": "Democratic", "R": "Republican", "I": "Independent"}
FIND = "https://app.leg.wa.gov/districtfinder"


def get(url):
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": AGENT})
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read().decode("utf-8", "replace")
        except Exception:
            time.sleep(3 * (attempt + 1))
    return None


def attr(tag, name):
    m = re.search(rf'{name}="([^"]*)"', tag)
    return html.unescape(m.group(1)).strip() if m else ""


def roster():
    """Member id -> card fields, and page slug -> member id, from the legislator list."""
    page = get(f"{SITE}/legislators/") or ""
    cards, slugs = {}, {}
    for m in re.finditer(r'<li role="listitem"([^>]*id="legislator-legislatorList-[^"]*")>(.*?)</li>', page, re.S):
        tag, body = m.group(1), m.group(2)
        mid = attr(tag, "data-id")
        last, _, first = attr(tag, "data-name").partition(", ")
        slug = re.search(r'href="/legislators/member/([a-z0-9-]+)"', body)
        cards[mid] = {"first": first, "last": last, "house": "S" if attr(tag, "data-chamber") == "Senate" else "H",
                      "district": int(attr(tag, "data-district") or 0), "party": attr(tag, "data-party"),
                      "positions": re.findall(r"'([^']+)'", attr(tag, "data-leadership")),
                      "slug": slug.group(1) if slug else ""}
        if slug:
            slugs[slug.group(1)] = mid
    return cards, slugs


def committees(house, slugs, names, cards):
    """Committee key -> {name, chair, members}, from each committee's page."""
    folder = "senate" if house == "S" else "house-of-representatives"
    index = get(f"{SITE}/about-the-legislature/committees/") or ""
    out = {}
    for acr in sorted(set(re.findall(rf'/about-the-legislature/committees/{folder}/([a-z0-9-]+)/', index))):
        page = get(f"{SITE}/about-the-legislature/committees/{folder}/{acr}/")
        if not page:
            continue
        title = re.search(r'in the (?:House|Senate) (.+?) Committee</div>', page)
        cname = html.unescape(title.group(1)).strip() if title else acr.upper()
        ranks = re.search(r'List of ranking members of the committee</caption>(.*?)</table>', page, re.S)
        chair = None
        if ranks:
            m = re.search(r'Chair:</th>\s*<td><a href="/legislators/member/([a-z0-9-]+)"', ranks.group(1))
            chair = names.get(slugs.get(m.group(1))) if m else None
        table = re.search(r'List of legislative members of the committee</caption>(.*?)</table>', page, re.S)
        # Rows: "Peterson, Strom (D)<br>Chair", then the district; matched to the legislator list by name and district.
        by = {(c["last"], c["first"], c["district"]): mid for mid, c in cards.items() if c["house"] == house}
        members = sorted({names[by[(html.unescape(last).strip(), html.unescape(first).strip(), int(d))]]
                          for last, first, d in re.findall(r'<tr><td>([^,<]+), ([^(<]+?) \(\w\)(?:<br>[^<]*)?</td>\s*<td><a[^>]*>(\d+)</a>',
                                                         table.group(1) if table else "")
                          if (html.unescape(last).strip(), html.unescape(first).strip(), int(d)) in by})
        out[committee_key(cname)] = {"name": cname, "chair": chair, "meets": None, "members": members}
    return out


def build(session):
    cards, slugs = roster()
    if len(cards) < 140:
        raise SystemExit(f"leg.wa.gov listed {len(cards)} legislators; expected 147")
    try:
        api = {m["Id"]: m for m in json.load(open(os.path.join(P.DATA, str(session), "sponsors.json")))}
    except (OSError, ValueError):
        api = {}
    people, names, n = {}, {}, {}
    for mid, c in sorted(cards.items(), key=lambda kv: (kv[1]["house"], kv[1]["district"], kv[1]["last"], kv[1]["first"])):
        d = c["district"]
        if c["house"] == "S":
            sid = f"S:{d}"
        else:
            sid = f"H:{d}{'ab'[min(n.get(d, 0), 1)]}"
            n[d] = n.get(d, 0) + 1
        name = f"{c['first']} {c['last']}"
        a = api.get(mid, {})
        phone = a.get("Phone") or None
        names[mid] = name
        people[sid] = {
            "name": name, "key": name_key(name), "id": mid, "party": PARTY.get(c["party"][:1], ""),
            "email": (a.get("Email") or None), "form": None, "phone": phone, "phones": [["Olympia", phone]] if phone else [],
            "url": f"{SITE}/legislators/member/{c['slug']}" if c["slug"] else None,
            "image": f"{SITE}/memberthumbnail/{mid}.jpg", "office": "",
            "position": next((p for p in c["positions"] if p != "all leadership positions"), None),
            "places": "", "dataName": c["last"],
        }
    leaders = {}
    for h, (name, role, _) in P.LEADERS.items():
        hit = next((p for sid, p in people.items() if sid[0] == h and p["key"] == name_key(name)), None)
        if hit:
            hit["position"] = role
            leaders[h] = {"name": hit["name"], "role": role}
    return {"session": session, "fetched": datetime.now(ZoneInfo(P.TIMEZONE)).strftime("%Y-%m-%d %H:%M PT"),
            "people": people, "since": {}, "senateCommittees": committees("S", slugs, names, cards),
            "assemblyCommittees": committees("H", slugs, names, cards), "leaders": leaders, "assemblyMembers": {}, "kept": []}


def main(session):
    out = build(session)
    path = os.path.join(P.DATA, f"contacts_{session}.json")
    json.dump(out, open(path, "w"), indent=1, ensure_ascii=False)
    ppl = out["people"].values()
    print(f"{path}: {len(out['people'])} legislators ({sum(1 for p in ppl if p['phone'])} with a phone, "
          f"{sum(1 for p in ppl if p['email'])} with email, {sum(1 for p in ppl if p['party'])} with party), "
          f"{len(out['senateCommittees'])} Senate and {len(out['assemblyCommittees'])} House committees "
          f"({sum(1 for c in list(out['senateCommittees'].values()) + list(out['assemblyCommittees'].values()) if c['chair'])} with a chair), "
          f"leaders {sorted(out['leaders'])}")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else P.session_of(datetime.now(ZoneInfo(P.TIMEZONE)).year))
