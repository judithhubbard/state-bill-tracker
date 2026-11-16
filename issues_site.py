#!/usr/bin/env python3
"""The national issue pages (/issues/ and /issues/<id>/), from each built state's data/issues_<session>.json
(build_data.py's write_issues(): each session's bills that issues.py matches). Run by build_site.sh after the states are
built, so a change here rebuilds no state; it also writes issues/summary.json (each issue's counts by year and state, and
the states with a session each year), which the front page's map reads.

Counts are by calendar year (last year, this year, and next year once a state lists prefiled bills): a bill counts in
every year it was alive, from the year it was introduced (its session's first year at the earliest, so a bill prefiled
in December counts in its session's year) through the year of its last action (the owner found New York's 2026 PFAS
view showing 4 of 24 bills when only the year introduced counted: two-year legislatures file most bills in year one);
laws count in the year they became law. Each issue has a page per year (index.html for this year,
<year>.html for the others) with a tile map shaded by the bills alive that year and the number that became law, a table by state
(under "Show as a table") and every bill, by state, linked to the bill on its state's page. States whose data has titles
only are marked as undercounted.

Usage: python3 issues_site.py SITE_DIR
"""
import html, json, os, re, sys

import issues

# States whose legislatures publish titles only (no summaries or "What it does"): matched on fewer words.
TITLES_ONLY = {"ak", "ar", "ma", "me", "ms", "mt", "nd", "ne", "nh", "ok", "vt"}
STAGES = ["In committee", "On the floor", "Passed one house", "Passed both houses", "On the governor’s desk",
          "Became law", "Vetoed"]
DESC = {
    "datacenters": "Bills about data centers and other very large electricity users: siting, power and water use, rates, tax breaks.",
    "pfas": "Bills about PFAS, the “forever chemicals”: bans in products, drinking water limits, firefighting foam, cleanup.",
    "ai": "Bills about artificial intelligence: deepfakes, chatbots, AI in hiring, insurance and health care, and government use.",
    "kidsonline": "Bills about children online: social media rules for minors, age checks, app stores, design codes.",
    "phones": "Bills about students’ phones and other devices in schools: bans, policies, phone-free days.",
    "housing": "Bills about building more homes: zoning, accessory dwelling units, lot sizes, parking rules, housing plans.",
    "minwage": "Bills that set or change a minimum wage: the state rate, tipped and subminimum wages, local wages.",
    "repair": "Bills giving owners and independent shops the parts, tools and manuals to fix what they own.",
    "betting": "Bills about sports betting, online casinos, fantasy sports, sweepstakes games and prediction markets.",
    "drugcosts": "Bills about what prescription drugs cost: insulin caps, pharmacy benefit managers, affordability boards, 340B.",
    "abortion": "Bills about abortion: bans and limits, access and protections, abortion pills, and amendments for the voters.",
    "firearms": "Bills about guns: carry permits, background checks and sales, red flag orders, ghost guns, guns in schools.",
    "vouchers": "Bills about public money for private schooling: vouchers, education savings accounts, tax-credit scholarships.",
    "voting": "Bills about how people vote and how elections are run: voter ID, mail voting, registration, counting and audits.",
    "immigration": "Bills about immigration enforcement: working with federal agents, sanctuary policies, status checks, benefits and licenses.",
    "tenants": "Bills about renting a home: rent limits, evictions, leases, security deposits, fees and tenants’ rights.",
    "proptax": "Bills about property tax relief for homeowners and residents: homestead exemptions, assessment caps, freezes, credits.",
    "transgender": "Bills about transgender people: sports, health care for minors, birth certificates and IDs, bathrooms, schools, protections.",
    "dei": "Bills about diversity, equity and inclusion programs: offices, training, statements and hiring, bans and protections.",
    "cannabis": "Bills about cannabis: legal sales, medical cannabis, hemp-derived THC such as delta-8, and clearing old records.",
}

CSS = """
:root {
  --paper: #f6f8fb; --sheet: #ffffff; --ink: #14213d; --ink-2: #4a5878; --rule: #d9e0ec; --navy: #1d3b78; --hover: #c8901f;
  --law: #18693f; --veto: #a3302a; --chip: #e9eef6; --tile-off: #e3e8f1; --tile-off-ink: #56627c;
  --heat-1: #c5d5ef; --heat-2: #6f93d0; --heat-3: #1d3b78; --heat-ink-1: #14213d; --heat-ink-2: #0b1530; --heat-ink-3: #ffffff;
  --law-mark: #c8901f;
  --display: "Archivo", "Arial Narrow", "Helvetica Neue", Arial, sans-serif;
  --body: "Public Sans", "Segoe UI", system-ui, -apple-system, sans-serif;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --paper: #0f1626; --sheet: #162036; --ink: #e6ebf5; --ink-2: #a3b0c9; --rule: #2a3754; --navy: #8fb0f0; --hover: #e0b04e;
    --law: #5cc28c; --veto: #f08a80; --chip: #1f2b45; --tile-off: #1b2438; --tile-off-ink: #8a96ae;
    --heat-1: #2f4d85; --heat-2: #5a86d6; --heat-3: #9dbcf3; --heat-ink-1: #e6ebf5; --heat-ink-2: #ffffff; --heat-ink-3: #0f1626;
    --law-mark: #e0b04e; color-scheme: dark;
  }
}
:root[data-theme="dark"] {
  --paper: #0f1626; --sheet: #162036; --ink: #e6ebf5; --ink-2: #a3b0c9; --rule: #2a3754; --navy: #8fb0f0; --hover: #e0b04e;
  --law: #5cc28c; --veto: #f08a80; --chip: #1f2b45; --tile-off: #1b2438; --tile-off-ink: #8a96ae;
  --heat-1: #2f4d85; --heat-2: #5a86d6; --heat-3: #9dbcf3; --heat-ink-1: #e6ebf5; --heat-ink-2: #ffffff; --heat-ink-3: #0f1626;
  --law-mark: #e0b04e; color-scheme: dark;
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--paper); color: var(--ink); font: 16px/1.5 var(--body); padding: 32px 16px 64px; }
main { max-width: 760px; margin: 0 auto; }
a { color: var(--navy); }
a:focus-visible, button:focus-visible, input:focus-visible { outline: 3px solid var(--hover); outline-offset: 2px; }
.crumbs { font-size: 14px; margin: 0 0 16px; }
h1 { font: 800 clamp(30px, 7vw, 42px)/1.08 var(--display); font-stretch: 85%; margin: 0 0 10px; }
h2 { font: 700 15px/1.2 var(--display); letter-spacing: .06em; text-transform: uppercase; color: var(--ink-2); margin: 32px 0 12px; }
h3 { font: 700 19px/1.2 var(--display); margin: 24px 0 8px; color: var(--navy); }
p.lede { color: var(--ink-2); margin: 0 0 20px; font-size: 17px; }
.note { color: var(--ink-2); font-size: 14px; }
.cards { list-style: none; margin: 0; padding: 0; display: grid; gap: 10px; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); }
.cards a { display: block; background: var(--sheet); border: 1px solid var(--rule); border-radius: 8px; padding: 12px 14px;
  color: var(--ink); text-decoration: none; height: 100%; }
.cards a:hover, .cards a:focus-visible { border-color: var(--navy); }
.cards b { display: block; font: 700 18px/1.2 var(--display); color: var(--navy); margin-bottom: 4px; }
.cards span { color: var(--ink-2); font-size: 14px; }
.tablewrap { overflow-x: auto; }
table { width: 100%; border-collapse: collapse; background: var(--sheet); border: 1px solid var(--rule); border-radius: 8px; font-size: 15px; }
th, td { text-align: left; padding: 7px 10px; border-bottom: 1px solid var(--rule); }
th { font-weight: 600; color: var(--ink-2); font-size: 13px; }
td.n, th.n { text-align: right; font-variant-numeric: tabular-nums; }
td.sess { white-space: nowrap; }
tbody tr:last-child td { border-bottom: 0; }
.tools { display: flex; flex-wrap: wrap; gap: 8px; margin: 0 0 12px; align-items: center; }
.tools button { font: inherit; font-size: 14px; border: 1px solid var(--rule); background: var(--sheet); color: var(--ink); border-radius: 999px;
  padding: 4px 12px; cursor: pointer; }
.tools button[aria-pressed="true"] { background: var(--navy); color: var(--sheet); border-color: var(--navy); }
.tools input { font: inherit; padding: 6px 10px; border: 1px solid var(--rule); border-radius: 8px; background: var(--sheet); color: var(--ink);
  min-width: 0; flex: 1 1 180px; }
ul.bills { list-style: none; margin: 0; padding: 0; background: var(--sheet); border: 1px solid var(--rule); border-radius: 8px; }
ul.bills li { padding: 8px 12px; border-bottom: 1px solid var(--rule); display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 2px 12px; }
ul.bills li:last-child { border-bottom: 0; }
ul.bills a { font-weight: 600; text-decoration: none; }
ul.bills a:hover { text-decoration: underline; }
.t { grid-column: 1 / -1; overflow-wrap: anywhere; }
.why { grid-column: 1 / -1; color: var(--ink-2); font-size: 14px; overflow-wrap: anywhere; }
.stage { font-size: 13px; background: var(--chip); border-radius: 999px; padding: 1px 9px; white-space: nowrap; align-self: start; }
.stage.s5 { color: var(--law); font-weight: 600; }
.stage.s6 { color: var(--veto); font-weight: 600; }
.hidden { display: none !important; }
.vh { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; }
.tools select { font: inherit; font-size: 15px; padding: 6px 10px; border: 1px solid var(--rule); border-radius: 8px; background: var(--sheet); color: var(--ink); }
.tiles { display: grid; grid-template-columns: repeat(11, 1fr); gap: 4px; margin: 16px 0 10px; }
.tiles a, .tiles span.off { aspect-ratio: 1; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 12%;
  border-radius: 6px; font: 700 clamp(10px, 2.6vw, 15px)/1 var(--display); text-decoration: none; }
.tiles span.off { background: transparent; color: var(--ink); box-shadow: inset 0 0 0 1px var(--rule); }
.tiles a:hover, .tiles a:focus-visible { outline: 3px solid var(--hover); outline-offset: 1px; }
.tiles a.h0 { background: var(--tile-off); color: var(--tile-off-ink); }
.tiles a.h1 { background: var(--heat-1); color: var(--heat-ink-1); }
.tiles a.h2 { background: var(--heat-2); color: var(--heat-ink-2); }
.tiles a.h3 { background: var(--heat-3); color: var(--heat-ink-3); }
/* The number of bills on the issue that became law: a gold badge under the state's letters. */
.lawn { display: inline-flex; align-items: center; justify-content: center; min-width: 1.6em; height: 1.6em; padding: 0 .3em;
  border-radius: 999px; background: var(--law-mark); color: #14213d; font: 700 clamp(9px, 2vw, 12px)/1 var(--body); }
.tiles span.wait, .legend .sq.wait { background: transparent; box-shadow: inset 0 0 0 1px var(--rule); }
.tiles span.wait { border: 1px dashed var(--tile-off-ink); box-shadow: none; }
.legend .sq.wait { border: 1px dashed var(--tile-off-ink); box-shadow: none; }
.legend .sq.off { background: transparent; box-shadow: inset 0 0 0 1px var(--rule); }
.tools label { color: var(--ink-2); }
.legend { color: var(--ink-2); font-size: 14px; margin: 0 0 12px; display: flex; gap: 6px 16px; flex-wrap: wrap; align-items: center; }
.legend .key { display: inline-flex; align-items: center; gap: 6px; }
.legend .sq { display: inline-block; width: 12px; height: 12px; border-radius: 3px; }
.legend .sq.h0 { background: var(--tile-off); } .legend .sq.h1 { background: var(--heat-1); }
.legend .sq.h2 { background: var(--heat-2); } .legend .sq.h3 { background: var(--heat-3); }
details.table { margin: 0 0 8px; }
details.table summary { cursor: pointer; color: var(--navy); font-weight: 600; font-size: 15px; margin: 0 0 8px; }
footer { margin-top: 32px; color: var(--ink-2); font-size: 14px; }
"""

HEAD = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{desc}">
<link rel="icon" type="image/png" sizes="32x32" href="/favicon-32.png">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wdth,wght@75..100,500..800&family=Public+Sans:wght@400;600;700&display=swap">
<style>{css}</style>
</head>
<body>
<main>
"""

e = html.escape


def stage_text(state, stage, kind):
    if kind == "const" and stage == 3:
        return "Sent to the voters"
    if state == "ne" and stage == 3:
        return "Passed the Legislature"
    return STAGES[stage]


def load(site):
    """{state: {"name", "files": [each session's issues file]}} for the states built."""
    out = {}
    for s in sorted(os.listdir(site)):
        folder = os.path.join(site, s, "data")
        if len(s) != 2 or not os.path.isdir(folder):
            continue
        files = []
        for name in sorted(os.listdir(folder)):
            if re.fullmatch(r"issues_\d{4}\.json", name):
                try:
                    files.append(json.load(open(os.path.join(folder, name), encoding="utf-8")))
                except ValueError:
                    pass
        if files:
            out[s] = {"name": files[0]["name"], "files": files}
    return out


def shown(num, others=()):
    """A bill number as people write it: "HB1005" -> "HB 1005"; with a record's other numbers, "A 11560 / S 8443"."""
    return " / ".join(re.sub(r"^([A-Z]+)(\d)", r"\1 \2", n) for n in [num, *others])


def link(f, num):
    page = f["page"] if f["page"] != "./" else ""
    return f"../../{f['state']}/{page}#{re.sub(r'[A-Z]$', '', num)}"


# The tile map's grid (row, column), as on the front page (home.html's GRID).
GRID = {"AK": (0, 0), "ME": (0, 10), "VT": (1, 9), "NH": (1, 10),
        "WA": (2, 0), "ID": (2, 1), "MT": (2, 2), "ND": (2, 3), "MN": (2, 4), "IL": (2, 5), "WI": (2, 6), "MI": (2, 7), "NY": (2, 8),
        "RI": (2, 9), "MA": (2, 10), "OR": (3, 0), "NV": (3, 1), "WY": (3, 2), "SD": (3, 3), "IA": (3, 4), "IN": (3, 5), "OH": (3, 6),
        "PA": (3, 7), "NJ": (3, 8), "CT": (3, 9), "CA": (4, 0), "UT": (4, 1), "CO": (4, 2), "NE": (4, 3), "MO": (4, 4), "KY": (4, 5),
        "WV": (4, 6), "VA": (4, 7), "MD": (4, 8), "DE": (4, 9), "AZ": (5, 1), "NM": (5, 2), "KS": (5, 3), "AR": (5, 4), "TN": (5, 5),
        "NC": (5, 6), "SC": (5, 7), "OK": (6, 3), "LA": (6, 4), "MS": (6, 5), "AL": (6, 6), "GA": (6, 7), "HI": (7, 0), "TX": (7, 3),
        "FL": (7, 7)}
SHORT = {"datacenters": "data centers", "pfas": "PFAS", "ai": "artificial intelligence", "kidsonline": "children online",
         "phones": "phones in schools", "housing": "housing supply", "minwage": "minimum wage", "repair": "right to repair",
         "betting": "sports betting", "drugcosts": "drug costs", "abortion": "abortion", "firearms": "firearms",
         "vouchers": "school vouchers", "voting": "voting", "immigration": "immigration enforcement",
         "tenants": "rent and tenants", "proptax": "property tax relief", "transgender": "transgender people", "dei": "DEI",
         "cannabis": "cannabis"}


def step(n):
    return 3 if n >= 15 else 2 if n >= 5 else 1 if n else 0


def covers(f, year):
    return f["session"] <= year < f["session"] + (f.get("years") or 1)


def met(f, year):
    """Whether the legislature met that year: a session file covering it, with bills introduced or acted on then (a
    two-year session's file covers an even year Texas's Legislature doesn't meet in; a few stray actions don't count)."""
    if not covers(f, year):
        return False
    if "active" not in f:
        return True
    n = f["active"].get(str(year), 0)
    return n > 0 if f.get("upcoming") else n >= max(5, 0.02 * (f.get("total") or 0))


def year_view(iid, states, year):
    """For one issue and calendar year: {state: (bills alive that year, became law that year, rows)}, the states with a
    session that year, and each state's session label and bill total. A bill is alive from the year it was introduced
    through the year of its last action."""
    by, open_, info = {}, set(), {}
    for st, d in states.items():
        rows, seen = [], set()
        for f in d["files"]:
            if covers(f, year):
                info[st] = (f["label"], f.get("total") or 0)
            if met(f, year):
                open_.add(st)
            for b in f["bills"]:
                if iid not in b[0]:
                    continue
                intro, law = (b[7] if len(b) > 7 else f["session"]), (b[8] if len(b) > 8 else "")
                last = int((b[5] or "0")[:4] or 0)
                new, passed = intro <= year <= max(intro, last), law[:4] == str(year)
                key = (f["session"], b[2])
                if (new or passed) and key not in seen:
                    seen.add(key)
                    rows.append((f, b, new, passed))
        if rows:
            by[st] = (sum(1 for r in rows if r[2]), sum(1 for r in rows if r[3]), rows)
    return by, open_, info


def badge(laws):
    return f'<span class="lawn" aria-hidden="true">{laws}</span>' if laws else ""


def tile_map(iid, by, names, open_, year, upcoming):
    """The tile map, each state shaded by its bills on the issue introduced that year, with the number that became law,
    each square a link to the state's bills below."""
    out = []
    for code, (r, c) in GRID.items():
        st = code.lower()
        style = f"grid-row:{r + 1};grid-column:{c + 1}"
        if st not in names:
            out.append(f'<span class="off" style="{style}" title="Coming soon">{code}</span>')
            continue
        n, laws = by[st][:2] if st in by else (0, 0)
        if st not in open_ and not n and not laws:
            label = f"{names[st]}: no bills filed yet for {year}" if upcoming else f"{names[st]}: no regular session in {year}"
            out.append(f'<span class="off wait" style="{style}" title="{e(label)}" aria-label="{e(code + ", " + label)}">{code}</span>')
            continue
        label = (f"{names[st]}: {n} bill{'' if n == 1 else 's'}{' prefiled' if upcoming else ''} in {year}" if n else f"{names[st]}: none in {year}")
        label += f", {laws} became law" if laws else ""
        href = f"#{st}" if st in by else "#bills"
        out.append(f'<a href="{href}" class="h{step(n)}" style="{style}" title="{e(label)}" aria-label="{e(code + ", " + label)}">{code}{badge(laws)}</a>')
    return '<div class="tiles">' + "".join(out) + "</div>"


def page_name(year, default):
    return "./" if year == default else f"{year}.html"


def issue_page(issue, states, year, years, default, upcoming):
    iid = issue["id"]
    names = {st: d["name"] for st, d in states.items()}
    by, open_, info = year_view(iid, states, year)
    rows, blocks, intro_n, laws_n, moving = [], [], 0, 0, 0
    for st in sorted(by, key=lambda s: names[s]):
        n, laws, mine = by[st]
        n_moving = sum(1 for f, b, new, _ in mine if new and 1 <= b[4] <= 4)
        intro_n, laws_n, moving = intro_n + n, laws_n + laws, moving + n_moving
        flag = " *" if st in TITLES_ONLY else ""
        label, total = info.get(st, ("", 0))
        rows.append((n, f'<tr><th scope="row"><a href="#{st}">{e(names[st])}</a>{flag}</th><td class="n">{n}</td>'
                        f'<td class="n">{laws}</td><td class="n">{n_moving}</td><td class="n">{f"{total:,}" if total else ""}</td>'
                        f'<td class="sess">{e(label)}</td></tr>'))
        items = []
        # Laws first, then the furthest along; within a stage, the latest action first.
        for f, b, new, passed in sorted(sorted(mine, key=lambda x: x[1][5], reverse=True), key=lambda x: (x[1][4] != 5, -x[1][4])):
            fl = " ".join(re.sub(r"[^a-z]+", "-", x.lower()) for x in (b[1].get(iid) or []))
            when = ""
            items.append(f'<li data-stage="{b[4]}" data-f="{e(fl)}"><a href="{e(link(f, b[2]))}">{e(shown(b[2], b[10] if len(b) > 10 else ()))}</a>'
                         f'<span class="stage s{b[4]}">{e(stage_text(st, b[4], b[6]))}</span>'
                         f'<span class="t">{e(b[3])}{when}</span>'
                         + (f'<span class="why">{e(why)}</span>' if (why := (b[9].get(iid) if len(b) > 9 else "")) and why.lower() not in b[3].lower() else "")
                         + '</li>')
        blocks.append(f'<section class="st" data-name="{e(names[st].lower())}"><h3 id="{st}">{e(names[st])} '
                      f'<span class="note">({n}{flag})</span></h3><ul class="bills">{"".join(items)}</ul></section>')
    in_states = len([1 for st in by if by[st][0]])
    rows.sort(key=lambda r: -r[0])
    none = sorted(names[st] for st in open_ if st not in by)
    waiting = sorted(names[st] for st in names if st not in open_ and st not in by)
    yopts = "".join(f'<option value="{page_name(y, default)}"{" selected" if y == year else ""}>'
                    f'{y}{" (prefiled so far)" if y > default else ""}</option>' for y in years)
    fopts = "".join(f'<option value="f:{e(re.sub(r"[^a-z]+", "-", k.lower()))}">{e(k)}</option>' for k in issue.get("filters", {}))
    verb = "prefiled" if upcoming else "with action"
    up = up_dir = "../../"
    lede_counts = (f"<b>{intro_n:,}</b> bills {verb} in <b>{in_states}</b> states in {year}"
                   + ("" if upcoming else f"; <b>{laws_n:,}</b> became law in {year}") + ".")
    body = HEAD.format(title=f"{issue['name']}: bills in every state, {year}", desc=e(DESC.get(iid, "")), css=CSS) + f"""
<p class="crumbs"><a href="{up}">State Bill Tracker</a> / <a href="../">Issues</a></p>
<h1>{e(issue['name'])}</h1>
<p class="lede">{e(DESC.get(iid, ""))}</p>
<div class="tools"><label for="year">Year</label>
<select id="year" onchange="location.href=this.value">{yopts}</select></div>
<p>{lede_counts}</p>
{tile_map(iid, by, names, open_, year, upcoming)}
<p class="legend">
<span class="key"><i class="sq h0"></i>None</span><span class="key"><i class="sq h1"></i>1&ndash;4 bills</span>
<span class="key"><i class="sq h2"></i>5&ndash;14</span><span class="key"><i class="sq h3"></i>15 or more</span>
{"" if upcoming else '<span class="key"><span class="lawn">3</span>Number that became law</span>'}
{'<span class="key"><i class="sq wait"></i>No bills filed yet</span>' if upcoming else ('<span class="key"><i class="sq wait"></i>No session that year</span>' if any(st not in open_ and st not in by for st in names) else "")}
<span class="key"><i class="sq off"></i>Not on the site yet</span>
</p>
<details class="table"><summary>Show as a table</summary>
<div class="tablewrap"><table>
<thead><tr><th scope="col">State</th><th scope="col" class="n">{"Prefiled" if upcoming else "Bills"}</th><th scope="col" class="n">Became law</th><th scope="col" class="n">Moving</th><th scope="col" class="n">All bills</th><th scope="col">Session</th></tr></thead>
<tbody>{"".join(r for _, r in rows)}</tbody></table></div>
<p class="note">A bill counts in each year from its introduction to its last action (in a two-year legislature, most are filed in the first year and keep moving in the second); &ldquo;Became law&rdquo; counts the year it did. &ldquo;Moving&rdquo;: out of committee, not yet law or vetoed. &ldquo;All bills&rdquo;: every bill in the state's session, for scale.</p>
</details>
<p class="note">{"Most legislatures start taking bills in January; these are the bills prefiled so far. " if upcoming else ""}* The legislature publishes only bill titles, so some of its bills on this issue may be missed.{f' None in {year}: {e(", ".join(none))}.' if none else ""}{f' No bills filed yet for {year}: {e(", ".join(waiting))}.' if upcoming and waiting else ""}{f' No regular session in {year} (these legislatures meet every other year): {e(", ".join(waiting))}.' if not upcoming and waiting else ""}</p>
<h2 id="bills">The bills</h2>
<div class="tools">
<label for="filter" class="vh">Show</label>
<select id="filter"><option value="">All bills</option><option value="law">Became law</option><option value="moving">Still moving</option>{fopts}</select>
<input type="search" id="find" placeholder="Find a state" aria-label="Find a state">
</div>
<p class="note" id="count" aria-live="polite"></p>
{"".join(blocks)}
<footer>Bills are found by the words in their titles and summaries, so a few are missed and a few are only partly about the issue. Bills for one city or county are left out. Open a bill for its status, votes and who to contact.</footer>
</main>
<script>
function apply() {{
  const q = document.getElementById("find").value.trim().toLowerCase(), v = document.getElementById("filter").value;
  let shown = 0;
  for (const sec of document.querySelectorAll("section.st")) {{
    let any = 0;
    for (const li of sec.querySelectorAll("li")) {{
      const s = +li.dataset.stage, f = li.dataset.f.split(" ");
      const ok = !v || (v === "law" && s === 5) || (v === "moving" && s >= 1 && s <= 4) || (v.startsWith("f:") && f.includes(v.slice(2)));
      li.classList.toggle("hidden", !ok);
      if (ok) any++;
    }}
    const vis = any && (!q || sec.dataset.name.includes(q));
    sec.classList.toggle("hidden", !vis);
    if (vis) shown += any;
  }}
  document.getElementById("count").textContent = (v || q) ? `Showing ${{shown.toLocaleString()}} bills.` : "";
}}
document.getElementById("filter").addEventListener("change", apply);
document.getElementById("find").addEventListener("input", apply);
</script>
</body>
</html>
"""
    return body, {"bills": intro_n, "states": in_states, "laws": laws_n, "by": {st: list(v[:2]) for st, v in by.items()}}, open_


def main(site):
    from datetime import date
    states = load(site)
    if not states:
        print("issues: no state has data/issues_<session>.json; not built")
        return
    default = date.today().year
    upcoming_years = {f["session"] for d in states.values() for f in d["files"] if f.get("upcoming")}
    # Every year from the first that nearly all states have data for (90%: most states' pages begin with 2023, New
    # York's with 2017), through this year, and next year once any state lists prefiled bills.
    have = lambda y: sum(1 for d in states.values() if any(covers(f, y) for f in d["files"]))
    first = default - 1
    while have(first - 1) >= 0.9 * len(states):
        first -= 1
    years = list(range(first, default + 1)) + ([default + 1] if default + 1 in upcoming_years else [])
    os.makedirs(os.path.join(site, "issues"), exist_ok=True)
    summary, opened = [], {}
    for issue in issues.ISSUES:
        os.makedirs(os.path.join(site, "issues", issue["id"]), exist_ok=True)
        per_year, panel = {}, {}
        for y in years:
            # The front page map's panel (home.html): each state's bills that year, one line each, laws first.
            by, _, _ = year_view(issue["id"], states, y)
            panel[str(y)] = {st: [[shown(b[2], b[10] if len(b) > 10 else ()), b[3], (b[9].get(issue["id"]) if len(b) > 9 else "") or "", b[4],
                                   link(f, b[2])[len("../../"):], b[6]]
                                  for f, b, new, passed in sorted(sorted(rows, key=lambda x: x[1][5], reverse=True),
                                                                  key=lambda x: (x[1][4] != 5, -x[1][4]))]
                             for st, (n, laws, rows) in by.items()}
            page, info, open_ = issue_page(issue, states, y, years, default, y > default)
            name = "index.html" if y == default else f"{y}.html"
            open(os.path.join(site, "issues", issue["id"], name), "w", encoding="utf-8").write(page)
            per_year[str(y)] = info
            opened[str(y)] = sorted(open_)
        json.dump(panel, open(os.path.join(site, "issues", issue["id"], "bills.json"), "w"), ensure_ascii=False,
                  separators=(",", ":"))
        summary.append({"id": issue["id"], "name": issue["name"], "group": issue.get("group", ""),
                        "short": SHORT.get(issue["id"], issue["name"]), "y": per_year})
    # The issues by group (issues.GROUPS), as in the front page's menu.
    card = lambda s: (f'<li><a href="{s["id"]}/"><b>{e(s["name"])}</b><span>{s["y"][str(default)]["bills"]:,} bills in '
                      f'{s["y"][str(default)]["states"]} states in {default}; {s["y"][str(default)]["laws"]:,} became law</span></a></li>')
    cards = "".join(f'<h2>{e(g)}</h2><ul class="cards">{"".join(card(s) for s in summary if s["group"] == g)}</ul>'
                    for g in issues.GROUPS if any(s["group"] == g for s in summary))
    cards += "".join(card(s) for s in summary if s["group"] not in issues.GROUPS) and \
        f'<h2>Other</h2><ul class="cards">{"".join(card(s) for s in summary if s["group"] not in issues.GROUPS)}</ul>'
    index = HEAD.format(title="Issues across the states", desc="The same subjects in every state legislature: how many bills, where, and which became law.", css=CSS) + f"""
<p class="crumbs"><a href="../">State Bill Tracker</a></p>
<h1>Issues across the states</h1>
<p class="lede">The same subjects in every state legislature: how many bills, where, and which became law.</p>
{cards}
<footer>Counts are for {default} ({len(states)} states). Bills are found by the words in their titles and summaries; see each issue's page for what counts.</footer>
</main>
</body>
</html>
"""
    open(os.path.join(site, "issues", "index.html"), "w", encoding="utf-8").write(index)
    json.dump({"years": years, "default": default, "open": opened, "groups": issues.GROUPS, "issues": summary},
              open(os.path.join(site, "issues", "summary.json"), "w"), ensure_ascii=False)
    print("issues:", ", ".join(f"{s['name']} {s['y'][str(default)]['bills']}" for s in summary), "; years", years)


if __name__ == "__main__":
    main(sys.argv[1])
