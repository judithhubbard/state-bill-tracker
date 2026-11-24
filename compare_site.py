#!/usr/bin/env python3
"""How the states compare (/compare/): each built state's finished sessions side by side, from its data/compare.json
(build_data.py's write_compare(): the odds chart's numbers, one session at a time, without placeholder bills, local and
other narrow bills, or constitutional amendments). Run by build_site.sh after the states are built, so a change here
rebuilds no state.

Writes compare/index.html (one table, a row per state; the odds chart, lists_pages/sankey.js, for one state or two) with
the data in the page, and compare/summary.json for the front page's "Bills that became law" map: {st: {name, label,
session, years, kind, intro, floor, house, both, law, vetoed, overridden}} for each state's latest finished session
(Congress as "us", apart from the states).

Usage: python3 compare_site.py SITE_DIR
"""
import html, json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import issues_site, site_meta

HERE = os.path.dirname(os.path.abspath(__file__))
FIRST = 2023  # "All finished sessions": from 2023 on, as every state keeps (states/window.py)

# The odds chart's colors (tracker.html's tokens), light and dark.
TOKENS = """
:root { --move: #3b6f76; --move-2: #18464c; --refer: #b3c2c6; --law-bar: #43b072; --veto: #b3372b; --stall: #98a4a8; }
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) { --move: #8fb5b8; --move-2: #c6dedf; --refer: #4d5d60; --law-bar: #1f8a50; --veto: #ee7d70; --stall: #6f7d80; }
}
:root[data-theme="dark"] { --move: #8fb5b8; --move-2: #c6dedf; --refer: #4d5d60; --law-bar: #1f8a50; --veto: #ee7d70; --stall: #6f7d80; }
"""

# The odds chart's styles: lists_pages/sankey.css (the state pages' too).
CSS = "\n" + open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "lists_pages", "sankey.css"), encoding="utf-8").read() + """.big { font-size: 17px; color: var(--ink); margin: 0 0 18px; max-width: 760px; }
table.cmp { min-width: 640px; }
table.cmp th { vertical-align: bottom; }
table.cmp th button { font: inherit; color: inherit; background: none; border: 0; padding: 0; cursor: pointer; text-align: inherit; }
table.cmp th button:hover { color: var(--navy); }
table.cmp th[aria-sort] button { color: var(--ink); }
table.cmp th[aria-sort="ascending"] button::after { content: " ▲"; font-size: 10px; }
table.cmp th[aria-sort="descending"] button::after { content: " ▼"; font-size: 10px; }
table.cmp td.st { white-space: nowrap; font-weight: 600; }
table.cmp td.st a { text-decoration: none; }
table.cmp td.st a:hover { text-decoration: underline; }
table.cmp td small { display: block; color: var(--ink-2); font-size: 12.5px; font-weight: 400; white-space: nowrap; }
table.cmp td .bar { display: block; height: 4px; border-radius: 2px; background: var(--rule); margin-top: 3px; overflow: hidden; }
table.cmp td .bar i { display: block; height: 100%; background: var(--stall); }
table.cmp td.house .bar i { background: var(--navy); }
table.cmp td.law .bar i { background: var(--lawn); }
table.cmp tbody.all td { font-weight: 700; background: var(--paper); }
table.cmp tbody.fed td { border-top: 2px solid var(--rule); }
table.cmp button.pickc { font: inherit; font-size: 13px; color: var(--navy); background: var(--sheet); border: 1px solid var(--rule); border-radius: 6px;
  padding: 1px 8px; cursor: pointer; white-space: nowrap; }
table.cmp button.pickc[aria-pressed="true"] { background: var(--navy); color: var(--sheet); border-color: var(--navy); }
table.cmp td.dash { color: var(--ink-2); }
table.cmp th .itip { margin-left: 3px; }
table.cmp td.sess .itip { margin-left: 5px; }
.tablewrap { margin: 0 0 8px; position: relative; }
table.cmp td.st small.ph { display: none; }
/* On a phone: the share columns that matter most, the session under the state's name. */
@media (max-width: 599.98px) {
  table.cmp { min-width: 0; font-size: 14px; }
  table.cmp th, table.cmp td { padding: 6px 4px; }
  table.cmp td.st, table.cmp td small { white-space: normal; }
  table.cmp .sess, table.cmp .house, table.cmp .pickcol { display: none; }
  table.cmp td.st small.ph { display: block; }
}
.charts h3 { margin: 18px 0 2px; }
.charts h3 small { font: 400 14px/1.3 var(--body); color: var(--ink-2); }
.charts p.note { margin: 0 0 6px; }
@media (max-width: 479.98px) { table.cmp { font-size: 14px; } th, td { padding: 6px 8px; } }
"""

e = html.escape


def load(site):
    out = []
    for st in sorted(os.listdir(site)):
        f = os.path.join(site, st, "data", "compare.json")
        if len(st) != 2 or not os.path.exists(os.path.join(site, st, "index.html")) or not os.path.exists(f):
            continue
        try:
            d = json.load(open(f, encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if d.get("sessions"):
            out.append(d)
    return out


# What a state's numbers can't show, beside its name (and in the front page's panel).
NOTES = {
    "mn": "Most Minnesota laws pass inside a few large omnibus bills, so many bills whose text became law count here as not passing.",
    "mo": "Missouri often passes several bills' contents together as one bill, so many bills whose text became law count here as not passing.",
}


def latest(d):
    """A state's latest finished session's numbers, for the front page."""
    s = d["sessions"][-1]
    n = lambda k: (s["odds"].get(k) or [0, 0])[0]
    return {"name": d["name"], "label": s["label"], "session": s["session"], "years": d["years"], "kind": s.get("kind") or "",
            "uni": d["chart"]["uni"], "intro": n("intro"), "floor": n("floor"), "house": n("house"), "both": n("both"),
            "law": (s["odds"].get("intro") or [0, 0])[1], "vetoed": n("vetoed"), "overridden": n("overridden"),
            **({"note": NOTES[d["state"]]} if d["state"] in NOTES else {})}


SCRIPT = r"""
const DATA = JSON.parse(document.getElementById("cmp-data").textContent), FIRST = __FIRST__;
const STATES = DATA.filter((d) => d.state !== "us"), US = DATA.find((d) => d.state === "us");
const num = (n) => n.toLocaleString("en-US");
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const pctOf = (a, b) => (b ? Math.round((100 * a) / b) : 0);
const itip = (text, cls = "") => `<span class="itip${cls ? ` ${cls}` : ""}" tabindex="0" role="note" aria-label="${esc(text)}"><span aria-hidden="true">i</span><span class="itip-t" aria-hidden="true">${esc(text)}</span></span>`;
const pctText = (a, b) => (b && a && a / b < 0.005 ? "<1%" : `${pctOf(a, b)}%`);
// The sessions a choice covers: the latest finished one, every one from 2023 on, or those that began in one year.
const PERIOD = document.getElementById("period"), A = document.getElementById("chartA"), B = document.getElementById("chartB");
function sessionsOf(d, p) {
  if (p === "latest") return d.sessions.slice(-1);
  if (p === "all") return d.sessions.filter((s) => s.session >= FIRST);
  return d.sessions.filter((s) => s.session === +p);
}
// Several sessions (or states) added up: the odds chart's numbers. "fate" (reintroduced next session) only where every
// part has it.
function pool(list) {
  const odds = {}, cfate = {}, fate = {};
  let fateOk = list.length > 0;
  for (const s of list) {
    for (const [k, v] of Object.entries(s.odds)) { const o = (odds[k] ||= [0, 0]); o[0] += v[0]; o[1] += v[1]; }
    for (const [k, v] of Object.entries(s.cfate || {})) { const o = (cfate[k] ||= [0, 0, 0]); v.forEach((x, i) => { o[i] += x; }); }
    if (!s.fate) fateOk = false;
    for (const [k, v] of Object.entries(s.fate || {})) { const o = (fate[k] ||= [0, 0, 0]); v.forEach((x, i) => { o[i] += x; }); }
  }
  return { odds, cfate, fate: fateOk ? fate : null };
}
const yearsText = (d, list) => (list.length > 1 ? `${list[0].label} to ${list[list.length - 1].label}` : list[0].label);
function row(d, list) {
  if (!list.length) return null;
  const { odds } = pool(list), n = (k) => (odds[k] || [0, 0])[0];
  const intro = n("intro"), law = (odds.intro || [0, 0])[1];
  return { d, list, intro, comm: intro - n("floor"), house: d.chart.uni ? n("both") : n("house"), law, vetoes: n("vetoed") + n("overridden"), over: n("overridden") };
}
let SORT = ["name", 1];
const KEYS = { name: (r) => r.d.name, intro: (r) => r.intro, comm: (r) => r.comm / r.intro, house: (r) => r.house / r.intro, law: (r) => r.law / r.intro,
  vetoes: (r) => r.vetoes, years: (r) => r.d.years * 10 + r.list.length };
function cell(cls, a, b, sub) {
  return `<td class="n ${cls}">${pctText(a, b)}<small>${num(a)}</small><span class="bar" aria-hidden="true"><i style="width:${Math.min(100, (100 * a) / (b || 1)).toFixed(1)}%"></i></span></td>`;
}
// The session's kind, in an ⓘ beside it. A two-year legislature whose session is named by one year (Montana, Texas)
// meets every other year.
const lengthText = (d, list) => (d.years === 2 && !/–|-/.test(list[0].label) ? "Meets every other year"
  : list.length > 1 ? `${d.years === 1 ? "One-year" : "Two-year"} sessions`
  : `${d.years === 1 ? "One-year" : "Two-year"} session${list[0].kind ? ` (${list[0].kind})` : ""}`);
function tr(r, all) {
  const { d, list } = r, picked = [A.value, B.value].includes(d.state);
  const ph = `<small class="ph">${esc(all ? r.sessText : yearsText(d, list))}</small>`;
  const name = all ? `<td class="st">${esc(d.name)}${ph}</td>` : `<td class="st"><a href="../${d.state}/#stats">${esc(d.name)}</a>${d.note ? itip(d.note) : ""}${ph}${d.state === "us" ? "<small>Not counted with the states</small>" : ""}</td>`;
  return `<tr>${name}<td class="sess">${esc(all ? r.sessText : yearsText(d, list))}${all ? "" : itip(lengthText(d, list))}</td>`
    + `<td class="n">${num(r.intro)}</td>${cell("", r.comm, r.intro)}${cell("house", r.house, r.intro)}${cell("law", r.law, r.intro)}`
    + `<td class="n">${num(r.vetoes)}${r.over ? `<small>${num(r.over)} overridden</small>` : ""}</td>`
    + `<td class="pickcol">${all ? "" : `<button type="button" class="pickc" data-st="${d.state}" aria-pressed="${picked}" aria-label="${esc(`Show ${d.name}'s chart`)}">Chart</button>`}</td></tr>`;
}
function allRow(rows) {
  const states = rows.filter((r) => r.d.state !== "us");
  const sum = (k) => states.reduce((a, r) => a + r[k], 0);
  return { d: { name: `All ${states.length} states`, chart: {} }, list: [], intro: sum("intro"), comm: sum("comm"), house: sum("house"), law: sum("law"),
    vetoes: sum("vetoes"), over: sum("over"), sessText: `${states.reduce((a, r) => a + r.list.length, 0)} sessions` };
}
function draw() {
  const p = PERIOD.value;
  const rows = STATES.map((d) => row(d, sessionsOf(d, p))).filter(Boolean);
  const [k, dir] = SORT, key = KEYS[k];
  rows.sort((x, y) => { const a = key(x), b = key(y); return (typeof a === "string" ? a.localeCompare(b) : a - b) * dir || x.d.name.localeCompare(y.d.name); });
  for (const th of document.querySelectorAll("table.cmp th[data-k]")) {
    if (th.dataset.k === k) th.setAttribute("aria-sort", dir > 0 ? "ascending" : "descending"); else th.removeAttribute("aria-sort");
  }
  const us = US && row(US, sessionsOf(US, p));
  const all = allRow(rows);
  document.getElementById("rows").innerHTML = rows.map((r) => tr(r)).join("");
  document.getElementById("allrow").innerHTML = rows.length ? tr(all, true) : "";
  document.getElementById("fedrow").innerHTML = us ? tr(us) : "";
  document.getElementById("lede").textContent = all.intro ? `Across ${rows.length} states, ${pctOf(all.comm, all.intro)}% of bills never made it out of committee, and ${pctOf(all.law, all.intro)}% became law.` : "";
  drawCharts();
}
// The odds chart for one state, Congress or all states together, and a second one under it.
function chartFor(id) {
  const p = PERIOD.value;
  if (id === "all") {
    const parts = STATES.map((d) => sessionsOf(d, p)).filter((l) => l.length);
    const pooled = pool(parts.flat());
    return { name: `All ${parts.length} states`, when: PERIOD.selectedOptions[0].text, data: pooled, chart: { uni: false, passedBoth: "Passed both houses", exits: null, heldLabel: null, linked: false, exec: "the governor" } };
  }
  const d = DATA.find((x) => x.state === id), list = d && sessionsOf(d, p);
  if (!list || !list.length) return { name: d ? d.name : id, none: true };
  return { name: d.name, st: d.state, when: yearsText(d, list), data: pool(list), chart: d.chart };
}
function drawCharts() {
  const box = document.getElementById("charts");
  box.innerHTML = [A.value, B.value].filter(Boolean).map((id) => {
    const c = chartFor(id);
    if (c.none) return `<h3>${esc(c.name)}</h3><p class="note">No finished session for this choice.</p>`;
    const o = c.data.odds;
    const svg = drawSankey(o, c.data.fate, c.data.cfate, { ...c.chart, linked: () => c.chart.linked, num, esc });
    return `<h3>${esc(c.name)} <small>${esc(c.when)}</small></h3>${svg}`
      + (c.st ? `<p class="note"><a href="../${c.st}/#stats">More in ${esc(c.name)}'s statistics</a></p>` : "");
  }).join("");
  for (const b of document.querySelectorAll("button.pickc")) b.setAttribute("aria-pressed", String([A.value, B.value].includes(b.dataset.st)));
}
function remember() {
  const parts = [PERIOD.value !== "latest" ? `p=${PERIOD.value}` : "", A.value !== "all" ? `a=${A.value || "none"}` : "", B.value ? `b=${B.value}` : ""].filter(Boolean);
  try { history.replaceState(null, "", parts.length ? `#${parts.join("&")}` : location.pathname); } catch (e) {}
}
{
  const opts = DATA.map((d) => `<option value="${d.state}">${esc(d.name)}</option>`).join("");
  A.innerHTML = `<option value="all">All states</option>${opts}`;
  B.innerHTML = `<option value="">Compare with…</option><option value="all">All states</option>${opts}`;
  // (Years before FIRST: the few states with a light history of older sessions, states/LIGHT.md.)
  const years = [...new Set(DATA.flatMap((d) => d.sessions.map((s) => s.session)))].sort().reverse();
  PERIOD.innerHTML = `<option value="latest">Latest finished session</option><option value="all">All finished sessions since ${FIRST}</option>`
    + years.map((y) => `<option value="${y}">Sessions that began in ${y}</option>`).join("");
  const h = new URLSearchParams(location.hash.slice(1));
  if (h.get("p") && [...PERIOD.options].some((o) => o.value === h.get("p"))) PERIOD.value = h.get("p");
  if (h.get("a")) A.value = h.get("a") === "none" ? "all" : h.get("a");
  if (h.get("b")) B.value = h.get("b");
  if (!A.value) A.value = "all";
}
PERIOD.addEventListener("change", () => { draw(); remember(); });
A.addEventListener("change", () => { drawCharts(); remember(); });
B.addEventListener("change", () => { drawCharts(); remember(); });
document.querySelector("table.cmp thead").addEventListener("click", (ev) => {
  const th = ev.target.closest("th[data-k]");
  if (!th || ev.target.closest(".itip")) return;
  SORT = SORT[0] === th.dataset.k ? [th.dataset.k, -SORT[1]] : [th.dataset.k, th.dataset.k === "name" ? 1 : -1];
  draw();
});
document.querySelector("table.cmp").addEventListener("click", (ev) => {
  const b = ev.target.closest("button.pickc");
  if (!b) return;
  const st = b.dataset.st;
  if (A.value === st) A.value = B.value || "all", B.value = "";
  else if (B.value === st) B.value = "";
  else if (A.value === "all") A.value = st;
  else B.value = st;
  drawCharts();
  remember();
  document.getElementById("chartsHead").scrollIntoView({ behavior: "smooth", block: "start" });
});
draw();
"""


def page(states):
    lede = "Bills introduced in each legislature, and how far they got."
    data = json.dumps(states, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    th = lambda k, label, cls="n", tip="": f'<th scope="col" class="{cls}" data-k="{k}"><button type="button">{label}</button>{tip}</th>'
    meta = site_meta.tags("How the states compare · State Bill Tracker", lede, site_meta.root() + "compare/") + site_meta.analytics()
    return issues_site.HEAD.format(title="How the states compare", desc=e(lede), css=issues_site.css() + TOKENS + CSS, meta=meta) + f"""
<p class="crumbs"><a href="../">State Bill Tracker</a></p>
<h1>How the states compare</h1>
<p class="big" id="lede"></p>
<div class="tools"><select id="period" aria-label="Sessions"></select></div>
<div class="tablewrap"><table class="cmp">
<thead><tr>{th("name", "State", "")}{th("years", "Session", "sess")}{th("intro", "Bills", "n", issues_site.itip("States count bills differently: New York counts a Senate bill and its identical Assembly bill as one, while most states count each, and some, like Minnesota, put their budget in a few large bills.", "r"))}{th("comm", "Died in committee")}{th("house", "Passed a house", "n house")}{th("law", "Became law")}{th("vetoes", "Vetoed")}<th scope="col" class="pickcol"><span class="vh">Chart</span></th></tr></thead>
<tbody id="rows"></tbody><tbody class="all" id="allrow"></tbody><tbody class="fed" id="fedrow"></tbody>
</table></div>
<p class="note">Finished sessions only, without local bills, placeholder bills and constitutional amendments.</p>
<h2 id="chartsHead">How bills move</h2>
<div class="tools"><select id="chartA" aria-label="Chart"></select><select id="chartB" aria-label="Beside it"></select></div>
<div class="charts" id="charts"></div>
<footer><a href="/about/">About</a> &middot; <a href="{site_meta.SUPPORT}">Support this site</a></footer>
</main>
<script type="application/json" id="cmp-data">{data}</script>
<script>
{open(os.path.join(HERE, "lists_pages", "sankey.js"), encoding="utf-8").read()}
</script>
<script>{SCRIPT.replace("__FIRST__", str(FIRST))}</script>
</body>
</html>
"""


def main(site):
    states = load(site)
    for d in states:
        if d["state"] in NOTES:
            d["note"] = NOTES[d["state"]]
    os.makedirs(os.path.join(site, "compare"), exist_ok=True)
    with open(os.path.join(site, "compare", "index.html"), "w", encoding="utf-8") as f:
        f.write(page(states))
    summary = {d["state"]: latest(d) for d in states}
    with open(os.path.join(site, "compare", "summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, separators=(",", ":"))
    print("compare:", ", ".join(f"{d['state']} {d['sessions'][-1]['label']}" for d in states))


if __name__ == "__main__":
    main(sys.argv[1])
