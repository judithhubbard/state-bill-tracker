// A daily check of the published site (statebilltracker.pages.dev until launch), run by
// .github/workflows/site-check.yml. It looks at the live pages the way a visitor's browser does and prints one list of
// problems: FAIL lines fail the run (so GitHub emails the owner), LOOK lines are for a person to read over.
//
//   1. Freshness: every state on the front page loads; its current session's "updated" time (DATA.fetched, the same
//      stamp as the header's "updated ...", in the state's own time zone) is under 30 hours old, and under 8 for
//      states in download.yml's quick lane; its number of bills isn't more than 10% below the last day's count (kept
//      in --counts, which the workflow keeps in an Actions cache; the first run only records).
//   2. Every page works, in headless Chrome: no script errors; three bills opened at different stages (in committee,
//      passed one or both houses, signed or vetoed), each tab visited and back, and at 375px no sideways scroll with a
//      bill open.
//   3. Accessibility: axe-core on the front page, and on each state's Bills view (a bill open) and Statistics view, in
//      light and dark themes (serious and critical violations FAIL, moderate and minor are LOOK); a keyboard test on
//      the front page and one state page; the map's dots, supermajority rings and "changes in January" outlines have
//      words too.
//
// Needs puppeteer-core and axe-core (found through NODE_PATH; the workflow installs them pinned) and Chrome (CHROME,
// else the usual place on macOS or Linux). Usage:
//   node test/site_check.js [--base URL] [--states wy,nj] [--counts FILE] [--keyboard-state nj] [--no-axe] [--quick wy,sd]
// Without --quick, the quick lane is worked out as download.yml does (`gh api`; skipped, with a LOOK, if gh can't).
"use strict";
const fs = require("fs");
const path = require("path");
const { execFileSync } = require("child_process");
const puppeteer = require("puppeteer-core");
const AXE = fs.readFileSync(require.resolve("axe-core/axe.min.js"), "utf8");

const REPO = path.resolve(__dirname, "..");
const arg = (name, dflt) => { const i = process.argv.indexOf("--" + name); return i > 0 ? process.argv[i + 1] : dflt; };
const flag = (name) => process.argv.includes("--" + name);
const BASE = (arg("base", "https://statebilltracker.pages.dev/")).replace(/\/?$/, "/");
const ONLY = arg("states") ? arg("states").split(",").map((s) => s.trim()).filter(Boolean) : null;
const COUNTS = arg("counts", path.join(REPO, ".site-check", "counts.json"));
const KEY_STATE = arg("keyboard-state", "nj");
const AXE_ON = !flag("no-axe");
const PAUSE = +arg("pause", 3000);            // between states, to be polite
const DEADLINE = Date.now() + +arg("minutes", 70) * 60000;  // stop starting new states after this
const AXE_UNTIL = Date.now() + +arg("axe-minutes", 40) * 60000; // and stop running axe after this, so every state is still checked
const QUICK_HOURS = 8, ALL_HOURS = 30, DROP = 0.10;
const CHROME = process.env.CHROME || [
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", "/usr/bin/google-chrome", "/usr/bin/google-chrome-stable",
  "/usr/bin/chromium", "/usr/bin/chromium-browser"].find((p) => fs.existsSync(p));

// ---- the report ----
const fails = [], looks = [];
const FAIL = (group, msg) => fails.push([group, msg]);
const LOOK = (group, msg) => looks.push([group, msg]);
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const t0 = Date.now();
const log = (...a) => console.error(`[${((Date.now() - t0) / 1000).toFixed(0)}s]`, ...a);

// ---- time zones: "2026-11-14 01:52" in America/Denver -> a Date ----
const TZ = {};
for (const code of fs.readdirSync(path.join(REPO, "states"))) {
  const p = path.join(REPO, "states", code, "profile.py");
  if (!fs.existsSync(p)) continue;
  const m = fs.readFileSync(p, "utf8").match(/^TIMEZONE = "([^"]+)"/m);
  if (m) TZ[code] = m[1];
}
function offsetMs(ms, tz) {
  const parts = Object.fromEntries(new Intl.DateTimeFormat("en-US", { timeZone: tz, hourCycle: "h23", year: "numeric",
    month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit", second: "2-digit" })
    .formatToParts(new Date(ms)).map((p) => [p.type, p.value]));
  return Date.UTC(+parts.year, parts.month - 1, +parts.day, +parts.hour, +parts.minute, +parts.second) - ms;
}
function zoned(stamp, tz) {
  const m = String(stamp || "").match(/^(\d{4})-(\d\d)-(\d\d)[ T](\d\d):(\d\d)/);
  if (!m) return null;
  const wall = Date.UTC(+m[1], m[2] - 1, +m[3], +m[4], +m[5]);
  let t = wall - offsetMs(wall, tz);
  t = wall - offsetMs(t, tz);
  return new Date(t);
}

// ---- the quick lane, as download.yml's plan job decides it: the longest of each state's last three finished
// download jobs is 30 minutes or less ----
function quickLane() {
  if (arg("quick") != null) return { codes: new Set(arg("quick").split(",").filter(Boolean)), note: "given" };
  const states = JSON.parse(fs.readFileSync(path.join(REPO, ".github", "states.json"), "utf8")).states;
  const codesOf = {};
  for (const s of states) codesOf[s.name] = s.paths.map((p) => p.replace(/^data\//, "")).filter((c) => c !== "legiscan");
  let repo = process.env.GITHUB_REPOSITORY;
  if (!repo) try { repo = execFileSync("git", ["-C", REPO, "remote", "get-url", "origin"], { encoding: "utf8" }).trim().replace(/^.*github\.com[:/]/, "").replace(/\.git$/, ""); } catch (e) {}
  const api = (p) => JSON.parse(execFileSync("gh", ["api", p], { encoding: "utf8", stdio: ["ignore", "pipe", "ignore"] }));
  try {
    const runs = api(`repos/${repo}/actions/workflows/download.yml/runs?status=completed&per_page=8`).workflow_runs;
    const times = {};
    for (const r of runs) {
      for (const j of api(`repos/${repo}/actions/runs/${r.id}/jobs?per_page=100`).jobs) {
        if (!["success", "failure"].includes(j.conclusion) || !j.completed_at) continue;
        const list = (times[j.name] ||= []);
        if (list.length < 3) list.push((Date.parse(j.completed_at) - Date.parse(j.started_at)) / 60000);
      }
    }
    const codes = new Set();
    for (const [name, ts] of Object.entries(times)) if (codesOf[name] && Math.max(...ts) <= 30) codesOf[name].forEach((c) => codes.add(c));
    return { codes, note: "from download.yml's last runs" };
  } catch (e) {
    LOOK("Freshness", `couldn't read download.yml's runs with gh (${String(e.message).split("\n")[0]}); every state held to ${ALL_HOURS} hours`);
    return { codes: new Set(), note: "unknown" };
  }
}

// ---- the browser ----
let browser;
async function newPage(errors) {
  // A new context each time: nothing saved by one page (filters, watchlists) carries into the next.
  const context = await browser.createBrowserContext();
  const page = await context.newPage();
  page.on("close", () => context.close().catch(() => {}));
  await page.emulateMediaFeatures([{ name: "prefers-color-scheme", value: "light" }, { name: "prefers-reduced-motion", value: "reduce" }]);
  await page.setViewport({ width: 1200, height: 900 });
  page.setDefaultTimeout(30000);
  page.on("pageerror", (e) => errors.push("script error: " + String(e.message || e).split("\n")[0]));
  page.on("console", (m) => { if (m.type() === "debug" && m.text().startsWith("axe ms")) log(m.text()); if (m.type() === "error" && !/Failed to load resource/.test(m.text())) errors.push("console error: " + m.text().slice(0, 200)); });
  page.on("requestfailed", (r) => {
    const u = r.url(), why = r.failure()?.errorText || "";
    if (/ERR_ABORTED/.test(why)) return;  // navigations away and cancelled fetches
    errors.push((u.startsWith(BASE) ? "" : "(other site) ") + `request failed: ${u.slice(0, 120)} ${why}`);
  });
  page.on("response", (r) => {
    if (r.status() >= 400 && r.url().startsWith(BASE)) errors.push(`HTTP ${r.status()}: ${r.url().slice(0, 120)}`);
  });
  return page;
}
// Errors from this site's own pages fail; a font or other site that didn't answer is only worth a look.
function report(group, where, errors) {
  for (const e of [...new Set(errors)]) (e.startsWith("(other site)") ? LOOK : FAIL)(group, `${where}: ${e}`);
  errors.length = 0;
}

// ---- axe ----
const IMPACT = { critical: 4, serious: 3, moderate: 2, minor: 1 };
const axeFound = new Map();  // rule -> {impact, help, nodes, pages:Set, example}
// In dark mode only colors change, so only the contrast rule runs again.
const axeSkipped = new Set();
async function runAxe(page, where, dark) {
  if (!AXE_ON) return;
  if (Date.now() > AXE_UNTIL) { axeSkipped.add(where.split(" ")[0]); return; }
  try {
    if (!(await page.evaluate(() => !!window.axe))) await page.addScriptTag({ content: AXE });
    const res = await page.evaluate(async (dark) => {
      const t = performance.now();
      const r = await window.axe.run(document, { resultTypes: ["violations"], ...(dark ? { runOnly: { type: "rule", values: ["color-contrast"] } } : {}) });
      console.debug("axe ms", Math.round(performance.now() - t), document.getElementsByTagName("*").length);
      return r.violations.map((v) => ({ id: v.id, impact: v.impact, help: v.help, n: v.nodes.length,
        examples: v.nodes.slice(0, 3).map((n) => `${n.target.join(" ")}: ${(n.failureSummary || "").split("\n").slice(1, 2).join("").trim()}`),
        // For contrast, each color pair once: "#8a96ad on #e3e8f1 (2.42)", with an element that has it.
        pairs: v.id === "color-contrast" ? v.nodes.map((n) => { const d = (n.any[0] || {}).data || {};
          return [`${d.fgColor} on ${d.bgColor} (${d.contrastRatio})`, `${n.target.join(" ")} "${(document.querySelector(n.target[0])?.textContent || "").trim().slice(0, 40)}"`]; }) : [] }));
    }, !!dark);
    for (const v of res) {
      const k = v.id;
      const e = axeFound.get(k) || { impact: v.impact, help: v.help, nodes: 0, pages: new Set(), examples: [] };
      if ((IMPACT[v.impact] || 0) > (IMPACT[e.impact] || 0)) e.impact = v.impact;
      e.nodes += v.n;
      // Examples from different pages first: two from the first page, then one from each other page, up to four.
      for (const x of v.examples.slice(0, e.pages.size ? 1 : 2)) if (e.examples.length < 4) e.examples.push(`${where}, ${x}`.slice(0, 300));
      e.pages.add(where);
      for (const [pair, el] of v.pairs) { const c = ((e.pairs ||= {})[pair] ||= { n: 0, el: `${where}, ${el}` }); c.n++; }
      axeFound.set(k, e);
    }
  } catch (e) {
    LOOK("Accessibility", `${where}: axe didn't run (${String(e.message).split("\n")[0]})`);
  }
}
async function setTheme(page, theme) {
  await page.evaluate((t) => { document.documentElement.dataset.theme = t; }, theme);
  await sleep(150);
}

// ---- the front page ----
async function frontPage() {
  const errors = [];
  const page = await newPage(errors);
  const resp = await page.goto(BASE, { waitUntil: "networkidle2" }).catch((e) => ({ status: () => 0, err: e }));
  if (!resp || resp.status() !== 200) { FAIL("Pages load", `front page: HTTP ${resp && resp.status()}`); return { states: [] }; }
  await sleep(500);
  const states = await page.evaluate(() => [...document.querySelectorAll("#states a")].map((a) => a.getAttribute("href").replace(/\/.*$/, "")));
  if (states.length < 10) FAIL("Pages load", `front page lists only ${states.length} states`);

  // The map says in words what its dots, rings and outlines show.
  const words = { D: /Democrat/i, R: /Republican/i, N: /nonpartisan/i, C: /coalition|split/i, S: /split|tied|coalition/i, I: /independent/i };
  const mapCheck = async (view) => page.evaluate((view, wordsSrc) => {
    const words = Object.fromEntries(Object.entries(wordsSrc).map(([k, v]) => [k, new RegExp(v, "i")]));
    const out = [];
    const tiles = [...document.querySelectorAll("#tiles a")];
    if (!tiles.length) out.push(["FAIL", `${view}: the map has no state links`]);
    if (document.getElementById("tiles")?.getAttribute("aria-hidden") === "true") out.push(["FAIL", `${view}: the map is hidden from screen readers`]);
    const noName = [], noRing = [], noParty = [], noChange = [];
    for (const a of tiles) {
      const label = (a.getAttribute("aria-label") || "") + " " + (a.getAttribute("title") || "");
      const code = a.textContent.trim().slice(0, 2);
      if (!label.trim()) { noName.push(code); continue; }
      const dots = [...a.querySelectorAll(".dot")];
      const sm = dots.filter((d) => d.classList.contains("sm")).length;
      if (sm && !/supermajorit/i.test(label)) noRing.push(code);
      // Each dot's party is in the words.
      const missing = dots.map((d) => [...d.classList].find((c) => words[c])).filter((c) => c && !words[c].test(label));
      if (missing.length) noParty.push(code + " (" + [...new Set(missing)].join("") + ")");
      if (a.classList.contains("changed") && !/now:|chang|january/i.test(label)) noChange.push(code);
    }
    if (noName.length) out.push(["FAIL", `${view}: map squares with no title or aria-label: ${noName.join(", ")}`]);
    if (noRing.length) out.push(["FAIL", `${view}: a supermajority ring with no "supermajority" in the square's label: ${noRing.join(", ")}`]);
    if (noParty.length) out.push(["FAIL", `${view}: party dots whose party isn't in the square's label: ${noParty.join(", ")}`]);
    if (noChange.length) out.push(["FAIL", `${view}: "changes in January" outline with no words saying so: ${noChange.join(", ")}`]);
    const legend = document.getElementById("legend");
    if (!legend || legend.hidden || !legend.offsetParent) out.push(["FAIL", `${view}: the map's legend isn't shown`]);
    else for (const w of ["Democratic", "Republican", "Supermajority"]) if (!legend.textContent.toLowerCase().includes(w.toLowerCase())) out.push(["LOOK", `${view}: the legend doesn't say "${w}"`]);
    return out;
  }, view, Object.fromEntries(Object.entries(words).map(([k, v]) => [k, v.source])));
  for (const [kind, msg] of await mapCheck("front page map (Now)")) (kind === "FAIL" ? FAIL : LOOK)("Map text equivalents", msg);
  const hasSwitch = await page.evaluate(() => { const w = document.getElementById("when"); return !!(w && !w.hidden && w.offsetParent); });
  if (hasSwitch) {
    await page.click('#when button[data-when="after"]');
    await sleep(300);
    for (const [kind, msg] of await mapCheck("front page map (From January)")) (kind === "FAIL" ? FAIL : LOOK)("Map text equivalents", msg);
    const key = await page.evaluate(() => { const k = document.getElementById("changedKey"); return !document.querySelector("#tiles a.changed") || (k && !k.hidden); });
    if (!key) FAIL("Map text equivalents", 'From January: squares are outlined but the legend has no "Changes in January" entry');
    await page.click('#when button[data-when="now"]');
    await sleep(200);
  }

  for (const theme of ["light", "dark"]) { await setTheme(page, theme); await runAxe(page, `front page (${theme})`, theme === "dark"); }
  await setTheme(page, "light");

  // Keyboard: Tab reaches the switch, the map and the list, and Enter or Space works them.
  await page.goto(BASE, { waitUntil: "networkidle2" });
  await sleep(300);
  const reached = new Set();
  const want = hasSwitch ? ["switch", "map", "list"] : ["map", "list"];
  for (let i = 0; i < 200 && !want.every((w) => reached.has(w)); i++) {
    await page.keyboard.press("Tab");
    const k = await page.evaluate(() => {
      const a = document.activeElement;
      return a.closest("#when") ? "switch" : a.closest("#tiles") ? "map" : a.closest("#states") ? "list" : a.id === "find" ? "find" : "";
    });
    if (k) reached.add(k);
  }
  for (const w of want) if (!reached.has(w)) FAIL("Keyboard", `front page: Tab never reaches the ${{ switch: "Now/From January switch", map: "map squares", list: "state list" }[w]}`);
  if (hasSwitch) {
    await page.focus('#when button[data-when="after"]');
    await page.keyboard.press("Space");
    await sleep(200);
    if (await page.$eval('#when button[data-when="after"]', (b) => b.getAttribute("aria-pressed")) !== "true") FAIL("Keyboard", "front page: Space on \"From January\" doesn't switch the map");
    await page.focus('#when button[data-when="now"]');
    await page.keyboard.press("Enter");
    await sleep(200);
    if (await page.$eval('#when button[data-when="now"]', (b) => b.getAttribute("aria-pressed")) !== "true") FAIL("Keyboard", "front page: Enter on \"Now\" doesn't switch the map back");
  }
  for (const [what, sel] of [["a map square", "#tiles a"], ["a state in the list", "#states a"]]) {
    const href = await page.$eval(sel, (a) => a.href).catch(() => null);
    if (!href) continue;
    await page.focus(sel);
    const nav = page.waitForNavigation({ timeout: 15000 }).catch(() => null);
    await page.keyboard.press("Enter");
    await nav;
    if (page.url() !== href) FAIL("Keyboard", `front page: Enter on ${what} doesn't open it (still at ${page.url()})`);
    await page.goto(BASE, { waitUntil: "networkidle2" });
  }
  report("Front page", "front page", errors);
  await page.close();
  return { states };
}

// ---- a state's current page ----
const GROUPS = [["in committee", [0]], ["passed one or both houses", [2, 3, 4]], ["signed or vetoed", [5, 6]]];
async function statePage(code, quick, counts, today, keyboard) {
  const where = code.toUpperCase();
  const url = BASE + code + "/";
  const errors = [];
  const page = await newPage(errors);
  try {
    const resp = await page.goto(url, { waitUntil: "networkidle2", timeout: 60000 }).catch((e) => null);
    if (!resp || resp.status() !== 200) { FAIL("Pages load", `${where}: ${url} answered ${resp ? "HTTP " + resp.status() : "nothing"}`); return; }
    const ready = await page.waitForFunction(() => document.documentElement.classList.contains("ready") && typeof BILLS !== "undefined",
      { timeout: 45000 }).then(() => true).catch(() => false);
    if (!ready) { FAIL("Pages load", `${where}: the page never finished loading`); report("Script errors", where, errors); return; }

    // 1. Freshness and the count of bills.
    const info = await page.evaluate(() => ({ fetched: DATA.fetched, session: DATA.session, current: DATA.current, bills: BILLS.length,
      label: document.getElementById("sessionLabel")?.textContent || "" }));
    const tz = TZ[code];
    const when = tz && zoned(info.fetched, tz);
    if (!when) FAIL("Freshness", `${where}: no "updated" time (DATA.fetched = ${JSON.stringify(info.fetched)}${tz ? "" : ", no TIMEZONE in its profile.py"})`);
    else {
      const hours = (Date.now() - when) / 3600000;
      const limit = quick ? QUICK_HOURS : ALL_HOURS;
      if (hours > limit) FAIL("Freshness", `${where}: updated ${info.fetched} (${tz.replace(/.*\//, "").replace(/_/g, " ")} time), ${hours.toFixed(1)} hours ago; limit ${limit} hours${quick ? " (quick lane)" : ""}`);
      if (hours < -1) LOOK("Freshness", `${where}: "updated" time ${info.fetched} is in the future`);
    }
    if (!info.label.includes("updated")) LOOK("Freshness", `${where}: the header line doesn't say when it was updated ("${info.label.trim()}")`);
    // Compared with the last count from an earlier day (a second run the same day compares with the same one).
    const prev = counts[code];
    const base = prev && (prev.date < today ? prev : prev.before);
    if (base && prev.session === info.session && info.bills < base.bills * (1 - DROP))
      FAIL("Bill counts", `${where}: ${info.bills} bills in ${info.session}, down from ${base.bills} on ${base.date} (${Math.round(100 - 100 * info.bills / base.bills)}% fewer)`);
    if (!info.bills) FAIL("Bill counts", `${where}: the ${info.session} page has no bills`);
    counts[code] = !prev || prev.date < today || prev.session !== info.session
      ? { session: info.session, bills: info.bills, date: today, before: prev && prev.date < today ? { date: prev.date, bills: prev.bills } : prev?.before }
      : { ...prev, bills: info.bills };
    report("Script errors", `${where} on load`, errors);

    log(`${where}: loaded`);
    // 2. Tabs: each one shows its view, then back to Bills.
    const tabs = await page.$$eval(".view-tab", (ts) => ts.filter((t) => !t.hidden && t.offsetParent).map((t) => t.dataset.view));
    for (const v of [...tabs.filter((v) => v !== "bills"), "bills"]) {
      await page.click(`.view-tab[data-view="${v}"]`);
      await sleep(v === "stats" ? 1200 : 300);
      const shown = await page.evaluate((v) => { const el = document.getElementById("view-" + v); return !!el && !el.hidden; }, v);
      if (!shown) FAIL("Tabs", `${where}: the ${v} tab doesn't show its view`);
      report("Script errors", `${where} after the ${v} tab`, errors);
    }
    for (const v of ["bills", "watch", "act", "stats", "how"]) if (!tabs.includes(v)) LOOK("Tabs", `${where}: no ${v} tab`);

    log(`${where}: tabs done`);
    // Bills at three stages, chosen with the "Where it is now" filter as a visitor would.
    const opened = [];
    for (const [name, stages] of GROUPS) {
      const k = await page.evaluate((stages) => {
        const rows = [...document.querySelectorAll("#pipeline button.srow[data-k]")];
        const r = rows.filter((b) => stages.includes(+b.dataset.k) && +(b.querySelector(".sn")?.textContent || "0").replace(/,/g, "") > 0);
        return r.length ? r[0].dataset.k : null;
      }, stages);
      if (k == null) { opened.push(null); continue; }
      await page.click(`#pipeline button.srow[data-k="${k}"]`);
      await sleep(400);
      const bill = await page.evaluate(() => {
        const d = document.querySelector("#list details.bill");
        if (!d) return null;
        // Into the middle of the window: scrolled to the top, the sticky results bar can sit over it.
        d.scrollIntoView({ block: "center" });
        return d.dataset.idx;
      });
      if (bill == null) FAIL("Bills", `${where}: the "${name}" stage filter shows no bills though its count isn't 0`);
      else {
        await page.click(`#list details.bill[data-idx="${bill}"] > summary .nums > span`);
        // A big bill's panel (a state budget) can take a few seconds to fill on a slow machine.
        const ok = await page.waitForFunction((i) => { const d = document.querySelector(`#list details.bill[data-idx="${i}"]`); return d && d.open && d.querySelector(".detail").textContent.trim().length > 20; },
          { timeout: 10000, polling: 250 }, bill).then(() => true).catch(() => false);
        const num = await page.evaluate((i) => BILLS[i]?.nums?.join(" / "), bill);
        if (!ok) FAIL("Bills", `${where}: ${num} (${name}) doesn't open, or its panel is empty`);
        opened.push({ k, bill, num, name });
        report("Script errors", `${where} opening ${num} (${name})`, errors);
        await page.click(`#list details.bill[data-idx="${bill}"] > summary .nums > span`).catch(() => {});
      }
      await page.click(`#pipeline button.srow[data-k="${k}"]`);  // the filter off again
      await sleep(300);
    }
    if (!opened.some(Boolean)) FAIL("Bills", `${where}: no bill could be opened`);

    log(`${where}: bills done`);
    // 3. Accessibility: Bills with a bill open, and Statistics, light and dark.
    const first = opened.find(Boolean);
    const openOne = async () => {
      if (!first) return;
      await page.click(`.view-tab[data-view="bills"]`);
      await page.click(`#pipeline button.srow[data-k="${first.k}"]`);
      await sleep(300);
      await page.evaluate((i) => { const d = document.querySelector(`#list details.bill[data-idx="${i}"]`) || document.querySelector("#list details.bill"); if (d && !d.open) d.querySelector("summary").click(); }, first.bill);
      await sleep(800);
    };
    if (AXE_ON) {
      await openOne();
      // Bill rows past the tenth repeat the first ten's markup; taken out (the page is reloaded after), axe takes a
      // fraction of the time.
      await page.evaluate(() => { for (const d of [...document.querySelectorAll("#list details.bill")].slice(10)) d.remove(); });
      for (const theme of ["light", "dark"]) { await setTheme(page, theme); await runAxe(page, `${where} Bills (${theme})`, theme === "dark"); }
      if (tabs.includes("stats")) {
        await page.click(`.view-tab[data-view="stats"]`);
        await sleep(1200);
        for (const theme of ["light", "dark"]) { await setTheme(page, theme); await runAxe(page, `${where} Statistics (${theme})`, theme === "dark"); }
      }
      await setTheme(page, "light");
      report("Script errors", `${where} during the accessibility check`, errors);
      await page.goto(url, { waitUntil: "networkidle2", timeout: 60000 });
      await page.waitForFunction(() => document.documentElement.classList.contains("ready"), { timeout: 45000 });
    }

    log(`${where}: axe done`);
    // Phone width: no sideways scroll with each bill open.
    await page.setViewport({ width: 375, height: 800, isMobile: true, hasTouch: true });
    await sleep(500);
    for (const o of opened.filter(Boolean)) {
      const w = await page.evaluate(async (o) => {
        document.querySelector('.view-tab[data-view="bills"]').click();
        const row = document.querySelector(`#pipeline button.srow[data-k="${o.k}"]`);
        if (row && row.getAttribute("aria-pressed") !== "true") row.click();
        await new Promise((r) => setTimeout(r, 400));
        const d = document.querySelector(`#list details.bill[data-idx="${o.bill}"]`) || document.querySelector("#list details.bill");
        if (d && !d.open) d.querySelector("summary").click();
        await new Promise((r) => setTimeout(r, 800));
        const sw = document.documentElement.scrollWidth;
        // What sticks out: the outermost elements past the right edge (their parent fits), and the bill they're in.
        const out = (e) => e.getBoundingClientRect().right > 376;
        const wide = sw > 375 ? [...document.querySelectorAll("body *")].filter((e) => e.offsetParent && out(e) && !(e.parentElement && out(e.parentElement)))
          .slice(0, 3).map((e) => {
            const row = e.closest("details.bill");
            const num = row ? BILLS[row.dataset.idx]?.nums?.[0] + "'s " : "";
            return `${num}${e.tagName.toLowerCase()}${e.id ? "#" + e.id : ""}${e.className && typeof e.className === "string" ? "." + e.className.trim().split(/\s+/).join(".") : ""} "${e.textContent.trim().slice(0, 60)}" (${Math.round(e.getBoundingClientRect().right)}px)`;
          }) : [];
        if (d && d.open) d.querySelector("summary").click();
        const again = document.querySelector(`#pipeline button.srow[data-k="${o.k}"]`);  // the list is drawn anew on each change
        if (again && again.getAttribute("aria-pressed") === "true") again.click();
        return { sw, wide };
      }, o);
      if (w.sw > 375) { FAIL("Phone width", `${where}: with ${o.num} (${o.name}) open, the page is ${w.sw}px wide at 375px; sticking out: ${w.wide.join("; ")}`); break; }
    }
    report("Script errors", `${where} at phone width`, errors);
    await page.setViewport({ width: 1200, height: 900 });

    log(`${where}: phone width done`);
    if (keyboard) await stateKeyboard(page, url, where);
    report("Script errors", `${where} keyboard test`, errors);
  } catch (e) {
    FAIL("Checker", `${where}: the check stopped: ${String(e.message).split("\n")[0]}`);
  } finally {
    await page.close().catch(() => {});
  }
}

// Keyboard on one state page: Tab reaches the tabs, the filters and a bill row; Enter and Space work them.
async function stateKeyboard(page, url, where) {
  await page.goto(url, { waitUntil: "networkidle2", timeout: 60000 });
  await page.waitForFunction(() => document.documentElement.classList.contains("ready"), { timeout: 45000 });
  const reached = new Set();
  for (let i = 0; i < 400 && reached.size < 3; i++) {
    await page.keyboard.press("Tab");
    const k = await page.evaluate(() => {
      const a = document.activeElement;
      return a.classList.contains("view-tab") ? "tabs" : a.closest("#side, #pipeline") ? "filters" : a.closest("#list details.bill") ? "bill" : "";
    });
    if (k) reached.add(k);
  }
  for (const [k, name] of [["tabs", "the tabs"], ["filters", "the filters"], ["bill", "a bill row"]])
    if (!reached.has(k)) FAIL("Keyboard", `${where}: Tab never reaches ${name} (400 presses)`);
  const key = async (sel, k) => { await page.focus(sel); await page.keyboard.press(k); await sleep(400); };
  await key('.view-tab[data-view="stats"]', "Enter");
  if (!(await page.evaluate(() => !document.getElementById("view-stats").hidden))) FAIL("Keyboard", `${where}: Enter on the Statistics tab doesn't open it`);
  await key('.view-tab[data-view="bills"]', "Space");
  if (!(await page.evaluate(() => !document.getElementById("view-bills").hidden))) FAIL("Keyboard", `${where}: Space on the Bills tab doesn't open it`);
  const row = await page.evaluate(() => { const b = [...document.querySelectorAll("#pipeline button.srow[data-k]")].find((b) => +(b.querySelector(".sn")?.textContent || "0").replace(/,/g, "") > 0); return b ? b.dataset.k : null; });
  if (row != null) {
    const sel = `#pipeline button.srow[data-k="${row}"]`;
    await key(sel, "Space");
    if ((await page.$eval(sel, (b) => b.getAttribute("aria-pressed"))) !== "true") FAIL("Keyboard", `${where}: Space on a "Where it is now" filter doesn't turn it on`);
    await key(sel, "Enter");
    if ((await page.$eval(sel, (b) => b.getAttribute("aria-pressed"))) !== "false") FAIL("Keyboard", `${where}: Enter on a "Where it is now" filter doesn't turn it off`);
  }
  await key("#list details.bill > summary", "Enter");
  if (!(await page.$eval("#list details.bill", (d) => d.open))) FAIL("Keyboard", `${where}: Enter on a bill row doesn't open it`);
  else {
    const focusIn = await page.evaluate(() => {
      const s = document.querySelector("#list details.bill > summary");
      return document.activeElement === s;
    });
    if (!focusIn) LOOK("Keyboard", `${where}: opening a bill with Enter moves focus away from its row`);
    await key("#list details.bill > summary", "Space");
    if (await page.$eval("#list details.bill", (d) => d.open)) FAIL("Keyboard", `${where}: Space on an open bill row doesn't close it`);
  }
}

// ---- main ----
(async () => {
  if (!CHROME) { console.log("FAIL  Checker: no Chrome found (set CHROME)"); process.exit(2); }
  const quick = quickLane();
  let counts = {};
  try { counts = JSON.parse(fs.readFileSync(COUNTS, "utf8")); } catch (e) { LOOK("Bill counts", `no earlier counts (${COUNTS}): this run only records them`); }
  const today = new Date().toISOString().slice(0, 10);
  browser = await puppeteer.launch({ executablePath: CHROME, headless: true, args: ["--no-sandbox", "--disable-gpu", "--lang=en-US"] });
  const { states } = await frontPage();
  log(`front page: ${states.length} states; quick lane (${quick.note}): ${[...quick.codes].sort().join(" ") || "none"}`);
  // A different starting state each day, so if time runs short, a different set goes without axe.
  const listed = ONLY ? states.filter((s) => ONLY.includes(s)) : states;
  const day = Math.floor(Date.now() / 86400000);
  const todo = listed.map((_, i) => listed[(i + day) % listed.length]);
  if (ONLY) for (const s of ONLY) if (!states.includes(s)) FAIL("Pages load", `${s.toUpperCase()}: not on the front page`);
  const skipped = [];
  const keyState = todo.includes(KEY_STATE) ? KEY_STATE : todo[0];
  for (const code of todo) {
    if (Date.now() > DEADLINE) { skipped.push(code); continue; }
    log(`checking ${code}`);
    await statePage(code, quick.codes.has(code), counts, today, code === keyState);
    await sleep(PAUSE);
  }
  if (skipped.length) FAIL("Checker", `ran out of time; not checked: ${skipped.join(", ")}`);
  if (axeSkipped.size) LOOK("Accessibility", `axe-core ran out of time and wasn't run for: ${[...axeSkipped].join(", ")}`);
  await browser.close();
  fs.mkdirSync(path.dirname(COUNTS), { recursive: true });
  fs.writeFileSync(COUNTS, JSON.stringify(counts, null, 1));

  // Accessibility, worst first.
  const rules = [...axeFound.entries()].sort((a, b) => (IMPACT[b[1].impact] - IMPACT[a[1].impact]) || b[1].nodes - a[1].nodes);
  for (const [id, e] of rules) {
    const pages = [...e.pages];
    const line = `[${e.impact}] ${id}: ${e.help}. ${e.nodes} elements on ${pages.length} pages (${pages.slice(0, 6).join("; ")}${pages.length > 6 ? " ..." : ""})` +
      (e.pairs ? Object.entries(e.pairs).sort((a, b) => b[1].n - a[1].n).map(([pair, c]) => `\n          ${pair}: ${c.n}, e.g. ${c.el}`).join("")
        : e.examples.map((x) => `\n          e.g. ${x}`).join(""));
    (IMPACT[e.impact] >= 3 ? FAIL : LOOK)("Accessibility (axe-core)", line);
  }

  const order = ["Pages load", "Freshness", "Bill counts", "Script errors", "Front page", "Tabs", "Bills", "Phone width",
    "Accessibility (axe-core)", "Accessibility", "Keyboard", "Map text equivalents", "Checker"];
  const print = (kind, list) => {
    const groups = {};
    for (const [g, m] of list) (groups[g] ||= []).push(m);
    const out = [];
    for (const g of [...order, ...Object.keys(groups).filter((g) => !order.includes(g))]) {
      if (!groups[g]) continue;
      out.push(`${kind}  ${g} (${groups[g].length})`);
      for (const m of groups[g]) out.push(`      ${m}`);
    }
    return out;
  };
  const minutes = ((Date.now() - t0) / 60000).toFixed(1);
  const text = [`Site check of ${BASE}: ${todo.length - skipped.length} states and the front page in ${minutes} minutes.`,
    fails.length ? `${fails.length} problem${fails.length > 1 ? "s" : ""}:` : "No problems.", ...print("FAIL", fails),
    ...(looks.length ? ["", "To look at:", ...print("LOOK", looks)] : [])].join("\n");
  console.log(text);
  if (process.env.GITHUB_STEP_SUMMARY) fs.appendFileSync(process.env.GITHUB_STEP_SUMMARY, "```\n" + text + "\n```\n");
  process.exit(fails.length ? 1 : 0);
})().catch((e) => { console.log("FAIL  Checker: " + (e.stack || e)); process.exit(2); });
