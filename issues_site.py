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
  --law: #18693f; --veto: #a3302a; --chip: #e9eef6;
  --display: "Archivo", "Arial Narrow", "Helvetica Neue", Arial, sans-serif;
  --body: "Public Sans", "Segoe UI", system-ui, -apple-system, sans-serif;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --paper: #0f1626; --sheet: #162036; --ink: #e6ebf5; --ink-2: #a3b0c9; --rule: #2a3754; --navy: #8fb0f0; --hover: #e0b04e;
    --law: #5cc28c; --veto: #f08a80; --chip: #1f2b45; color-scheme: dark;
  }
}
:root[data-theme="dark"] {
  --paper: #0f1626; --sheet: #162036; --ink: #e6ebf5; --ink-2: #a3b0c9; --rule: #2a3754; --navy: #8fb0f0; --hover: #e0b04e;
  --law: #5cc28c; --veto: #f08a80; --chip: #1f2b45; color-scheme: dark;
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


def issue_page(issue, states):
    iid = issue["id"]
    rows, blocks, total, laws, moving = [], [], 0, 0, 0
    filters = list(issue.get("filters", {}))
    for st in sorted(states, key=lambda s: s["name"]):
        mine = [b for b in st["bills"] if iid in b[0]]
        if not mine:
            continue
        n_law = sum(1 for b in mine if b[4] == 5)
        n_moving = sum(1 for b in mine if 1 <= b[4] <= 4)
        total, laws, moving = total + len(mine), laws + n_law, moving + n_moving
        flag = " *" if st["state"] in TITLES_ONLY else ""
        rows.append((len(mine), f'<tr><th scope="row"><a href="#{st["state"]}">{e(st["name"])}</a>{flag}</th>'
                                f'<td class="n">{len(mine)}</td><td class="n">{n_law}</td><td class="n">{n_moving}</td>'
                                f'<td class="sess">{e(st["label"])}</td></tr>'))
        items = []
        # Laws first, then the furthest along; within a stage, the latest action first.
        for b in sorted(sorted(mine, key=lambda b: b[5], reverse=True), key=lambda b: (b[4] != 5, -b[4])):
            f = " ".join(re.sub(r"\W+", "-", x.lower()) for x in (b[1].get(iid) or []))
            items.append(f'<li data-stage="{b[4]}" data-f="{e(f)}"><a href="{e(link(st, b[2]))}">{e(shown(b[2]))}</a>'
                         f'<span class="stage s{b[4]}">{e(stage_text(st["state"], b[4], b[6]))}</span>'
                         f'<span class="t">{e(b[3])}</span></li>')
        blocks.append(f'<section class="st" data-name="{e(st["name"].lower())}"><h3 id="{st["state"]}">{e(st["name"])} '
                      f'<span class="note">({len(mine)}, {e(st["label"])})</span></h3><ul class="bills">{"".join(items)}</ul></section>')
    in_states = len(rows)
    rows.sort(key=lambda r: -r[0])
    ftools = "".join(f'<button type="button" data-filter="{e(re.sub(r"[^a-z]+", "-", k.lower()))}" aria-pressed="false">{e(k)}</button>'
                     for k in filters)
    body = HEAD.format(title=f"{issue['name']}: bills in every state", desc=e(DESC.get(iid, "")), css=CSS) + f"""
<p class="crumbs"><a href="../../">State Bill Tracker</a> / <a href="../">Issues</a></p>
<h1>{e(issue['name'])}</h1>
<p class="lede">{e(DESC.get(iid, ""))}</p>
<p><b>{total:,}</b> bills in <b>{in_states}</b> states this session; <b>{laws:,}</b> became law and <b>{moving:,}</b> are still moving.</p>
<h2>By state</h2>
<div class="tablewrap"><table>
<thead><tr><th scope="col">State</th><th scope="col" class="n">Bills</th><th scope="col" class="n">Laws</th><th scope="col" class="n">Moving</th><th scope="col">Session</th></tr></thead>
<tbody>{"".join(r for _, r in rows)}</tbody></table></div>
<p class="note">Each state's current session. &ldquo;Moving&rdquo; means out of committee but not yet law or vetoed. * The legislature publishes only bill titles, no summaries, so some of its bills on this issue may be missed.</p>
<h2>The bills</h2>
<div class="tools" role="group" aria-label="Show">
<button type="button" data-only="law" aria-pressed="false">Became law</button>
<button type="button" data-only="moving" aria-pressed="false">Still moving</button>
{ftools}
<input type="search" id="find" placeholder="Find a state" aria-label="Find a state">
</div>
<p class="note" id="count" aria-live="polite"></p>
{"".join(blocks)}
<footer>Bills are found by the words in their titles and summaries, so a few are missed and a few are only partly about the issue. Bills for one city or county are left out. Open a bill for its status, votes and who to contact.</footer>
</main>
<script>
const only = new Set(), fs = new Set();
function apply() {{
  const q = document.getElementById("find").value.trim().toLowerCase();
  let shown = 0;
  for (const sec of document.querySelectorAll("section.st")) {{
    let any = 0;
    for (const li of sec.querySelectorAll("li")) {{
      const s = +li.dataset.stage, f = li.dataset.f.split(" ");
      const ok = (!only.size || (only.has("law") && s === 5) || (only.has("moving") && s >= 1 && s <= 4))
        && (!fs.size || [...fs].some((x) => f.includes(x)));
      li.classList.toggle("hidden", !ok);
      if (ok) any++;
    }}
    const vis = any && (!q || sec.dataset.name.includes(q));
    sec.classList.toggle("hidden", !vis);
    if (vis) shown += any;
  }}
  document.getElementById("count").textContent = (only.size || fs.size || q) ? `Showing ${{shown.toLocaleString()}} bills.` : "";
}}
for (const b of document.querySelectorAll(".tools button")) b.addEventListener("click", () => {{
  const set = b.dataset.only ? only : fs, key = b.dataset.only || b.dataset.filter;
  set.has(key) ? set.delete(key) : set.add(key);
  b.setAttribute("aria-pressed", set.has(key));
  apply();
}});
document.getElementById("find").addEventListener("input", apply);
</script>
</body>
</html>
"""
    return body, {"id": iid, "name": issue["name"], "bills": total, "states": in_states, "laws": laws}


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
