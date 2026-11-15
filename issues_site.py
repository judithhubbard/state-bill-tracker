#!/usr/bin/env python3
"""The national issue pages (/issues/ and /issues/<id>/), from each built state's data/issues.json (build_data.py's
write_issues(): the current session's bills that issues.py matches). Run by build_site.sh after the states are built,
so a change here rebuilds no state; it also writes issues/summary.json, which the front page's issue list reads.

Each issue page has a table of states (bills this session, laws, still moving) and every bill, by state, with its
stage, linked to the bill on its state's page. Only each state's current session counts (2025-26 in a two-year
legislature, 2026 in a yearly one): the pages say so. States whose data has titles only are marked as undercounted.

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
.stage { font-size: 13px; background: var(--chip); border-radius: 999px; padding: 1px 9px; white-space: nowrap; align-self: start; }
.stage.s5 { color: var(--law); font-weight: 600; }
.stage.s6 { color: var(--veto); font-weight: 600; }
.hidden { display: none !important; }
.vh { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; }
.tools select { font: inherit; font-size: 15px; padding: 6px 10px; border: 1px solid var(--rule); border-radius: 8px; background: var(--sheet); color: var(--ink); }
.tiles { display: grid; grid-template-columns: repeat(11, 1fr); gap: 4px; margin: 16px 0 10px; }
.tiles a, .tiles span.off { aspect-ratio: 1; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 12%;
  border-radius: 6px; font: 700 clamp(10px, 2.6vw, 15px)/1 var(--display); text-decoration: none; }
.tiles span.off { background: transparent; color: var(--tile-off-ink); box-shadow: inset 0 0 0 1px var(--rule); }
.tiles a:hover, .tiles a:focus-visible { outline: 3px solid var(--hover); outline-offset: 1px; }
.tiles a.h0 { background: var(--tile-off); color: var(--tile-off-ink); }
.tiles a.h1 { background: var(--heat-1); color: var(--heat-ink-1); }
.tiles a.h2 { background: var(--heat-2); color: var(--heat-ink-2); }
.tiles a.h3 { background: var(--heat-3); color: var(--heat-ink-3); }
.dots { display: flex; }
.law { width: clamp(5px, 1.3vw, 9px); height: clamp(5px, 1.3vw, 9px); border-radius: 50%; background: var(--law-mark);
  box-shadow: 0 0 0 1.5px var(--sheet); display: inline-block; }
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
    states = []
    for s in sorted(os.listdir(site)):
        path = os.path.join(site, s, "data", "issues.json")
        if len(s) == 2 and os.path.exists(path):
            try:
                states.append(json.load(open(path, encoding="utf-8")))
            except ValueError:
                pass
    return states


def shown(num):
    """A bill number as people write it: "HB1005" -> "HB 1005"."""
    return re.sub(r"^([A-Z]+)(\d)", r"\1 \2", num)


def link(st, num):
    page = st["page"] if st["page"] != "./" else ""
    return f"../../{st['state']}/{page}#{re.sub(r'[A-Z]$', '', num)}"


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
         "betting": "sports betting", "drugcosts": "drug costs"}


def step(n):
    return 3 if n >= 15 else 2 if n >= 5 else 1 if n else 0


def tile_map(iid, by, names):
    """The tile map, each state shaded by its number of bills on the issue (a gold mark where one became law), each
    square a link to the state's bills below."""
    out = []
    for code, (r, c) in GRID.items():
        st = code.lower()
        style = f"grid-row:{r + 1};grid-column:{c + 1}"
        if st not in names:
            out.append(f'<span class="off" style="{style}" title="Coming soon">{code}</span>')
            continue
        n, laws = by.get(st, (0, 0))
        label = (f"{names[st]}: {n} bill{'' if n == 1 else 's'}" if n else f"{names[st]}: none") + (f", {laws} became law" if laws else "")
        mark = '<span class="dots" aria-hidden="true"><i class="law"></i></span>' if laws else ""
        href = f"#{st}" if n else "#none"
        out.append(f'<a href="{href}" class="h{step(n)}" style="{style}" title="{e(label)}" aria-label="{e(code + ", " + label)}">{code}{mark}</a>')
    return '<div class="tiles">' + "".join(out) + "</div>"


def issue_page(issue, states):
    iid = issue["id"]
    rows, blocks, total, laws, moving, by = [], [], 0, 0, 0, {}
    names = {st["state"]: st["name"] for st in states}
    none = []
    for st in sorted(states, key=lambda s: s["name"]):
        mine = [b for b in st["bills"] if iid in b[0]]
        if not mine:
            none.append(st["name"])
            continue
        n_law = sum(1 for b in mine if b[4] == 5)
        n_moving = sum(1 for b in mine if 1 <= b[4] <= 4)
        by[st["state"]] = (len(mine), n_law)
        total, laws, moving = total + len(mine), laws + n_law, moving + n_moving
        flag = " *" if st["state"] in TITLES_ONLY else ""
        all_n = st.get("total")
        rows.append((len(mine), f'<tr><th scope="row"><a href="#{st["state"]}">{e(st["name"])}</a>{flag}</th>'
                                f'<td class="n">{len(mine)}</td><td class="n">{n_law}</td><td class="n">{n_moving}</td>'
                                f'<td class="n">{f"{all_n:,}" if all_n else ""}</td><td class="sess">{e(st["label"])}</td></tr>'))
        items = []
        # Laws first, then the furthest along; within a stage, the latest action first.
        for b in sorted(sorted(mine, key=lambda b: b[5], reverse=True), key=lambda b: (b[4] != 5, -b[4])):
            f = " ".join(re.sub(r"[^a-z]+", "-", x.lower()) for x in (b[1].get(iid) or []))
            items.append(f'<li data-stage="{b[4]}" data-f="{e(f)}"><a href="{e(link(st, b[2]))}">{e(shown(b[2]))}</a>'
                         f'<span class="stage s{b[4]}">{e(stage_text(st["state"], b[4], b[6]))}</span>'
                         f'<span class="t">{e(b[3])}</span></li>')
        blocks.append(f'<section class="st" data-name="{e(st["name"].lower())}"><h3 id="{st["state"]}">{e(st["name"])} '
                      f'<span class="note">({len(mine)}, {e(st["label"])}{flag})</span></h3><ul class="bills">{"".join(items)}</ul></section>')
    in_states = len(rows)
    rows.sort(key=lambda r: -r[0])
    opts = "".join(f'<option value="f:{e(re.sub(r"[^a-z]+", "-", k.lower()))}">{e(k)}</option>' for k in issue.get("filters", {}))
    body = HEAD.format(title=f"{issue['name']}: bills in every state", desc=e(DESC.get(iid, "")), css=CSS) + f"""
<p class="crumbs"><a href="../../">State Bill Tracker</a> / <a href="../">Issues</a></p>
<h1>{e(issue['name'])}</h1>
<p class="lede">{e(DESC.get(iid, ""))}</p>
<p><b>{total:,}</b> bills in <b>{in_states}</b> states this session; <b>{laws:,}</b> became law and <b>{moving:,}</b> are still moving.</p>
{tile_map(iid, by, names)}
<p class="legend">
<span class="key"><i class="sq h0"></i>None</span><span class="key"><i class="sq h1"></i>1&ndash;4 bills</span>
<span class="key"><i class="sq h2"></i>5&ndash;14</span><span class="key"><i class="sq h3"></i>15 or more</span>
<span class="key"><i class="law"></i>A bill became law</span>
<span class="key"><i class="sq" style="box-shadow:inset 0 0 0 1px var(--rule)"></i>Not on the site yet</span>
</p>
<details class="table"><summary>Show as a table</summary>
<div class="tablewrap"><table>
<thead><tr><th scope="col">State</th><th scope="col" class="n">Bills</th><th scope="col" class="n">Laws</th><th scope="col" class="n">Moving</th><th scope="col" class="n">All bills</th><th scope="col">Session</th></tr></thead>
<tbody>{"".join(r for _, r in rows)}</tbody></table></div>
<p class="note">&ldquo;Moving&rdquo;: out of committee, not yet law or vetoed. &ldquo;All bills&rdquo;: every bill in the state's session, for scale.</p>
</details>
<p class="note">Each state's current session, so the years differ: a two-year legislature's 2025&ndash;26, a yearly one's 2026. * The legislature publishes only bill titles, so some of its bills on this issue may be missed.{f' No bills: {e(", ".join(none))}.' if none else ""}</p>
<h2 id="none">The bills</h2>
<div class="tools">
<label for="filter" class="vh">Show</label>
<select id="filter"><option value="">All bills</option><option value="law">Became law</option><option value="moving">Still moving</option>{opts}</select>
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
    return body, {"id": iid, "name": issue["name"], "short": SHORT.get(iid, issue["name"]), "bills": total,
                  "states": in_states, "laws": laws, "by": {k: list(v) for k, v in by.items()}}


def main(site):
    states = load(site)
    if not states:
        print("issues: no state has data/issues.json; not built")
        return
    os.makedirs(os.path.join(site, "issues"), exist_ok=True)
    summary = []
    for issue in issues.ISSUES:
        page, info = issue_page(issue, states)
        os.makedirs(os.path.join(site, "issues", issue["id"]), exist_ok=True)
        open(os.path.join(site, "issues", issue["id"], "index.html"), "w", encoding="utf-8").write(page)
        summary.append(info)
    cards = "".join(f'<li><a href="{s["id"]}/"><b>{e(s["name"])}</b><span>{s["bills"]:,} bills in {s["states"]} states; '
                    f'{s["laws"]:,} became law</span></a></li>' for s in summary)
    index = HEAD.format(title="Issues across the states", desc="The same subjects in every state legislature: how many bills, where, and which became law.", css=CSS) + f"""
<p class="crumbs"><a href="../">State Bill Tracker</a></p>
<h1>Issues across the states</h1>
<p class="lede">The same subjects in every state legislature this session: how many bills, where, and which became law.</p>
<ul class="cards">{cards}</ul>
<footer>Counts are each state's current session ({len(states)} states). Bills are found by the words in their titles and summaries; see each issue's page for what counts.</footer>
</main>
</body>
</html>
"""
    open(os.path.join(site, "issues", "index.html"), "w", encoding="utf-8").write(index)
    json.dump(summary, open(os.path.join(site, "issues", "summary.json"), "w"), ensure_ascii=False)
    print("issues:", ", ".join(f"{s['name']} {s['bills']}" for s in summary))


if __name__ == "__main__":
    main(sys.argv[1])
