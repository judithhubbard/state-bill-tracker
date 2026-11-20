// The same bill must read the same way in every view. Against a local build of a few states, this picks bills that
// cover the hard cases (each stage; a bill that ended mid-session; constitutional amendments on first and second passage;
// a bill sent to the voters; Nebraska's one house; Congress and the President; a past session; prefiled bills) and reads
// how each view shows them:
//   bills   the state page's Bills row (and its opened panel: the panel opens under the row and keeps its status line)
//   watch   the state page's Watchlist tab (the bill starred in this browser)
//   yours   /your-bills/
//   mine    the front page's "Your bills" panel
//   search  the front page's "Find a bill" results
//   issue   an issue page's row, and ipanel the front page's issue panel (for bills on a national issue)
// and compares the status words in all of them, the watchlist group and deadline (watch vs yours), and whether the bill
// shows as new (watch, yours, mine; every bill is starred as seen the day before its last action). /list/ isn't read: a
// shared list needs the lists Worker, which a local build doesn't have (its rows are the state page's own card, in a
// frame, or common.js's lookUp(), the same label as yours).
//
// Build and serve first (don't put ny with other states in ONLY), then run with puppeteer-core on NODE_PATH:
//   ONLY="ne co va us tn nv nd de" SITE_BASE=http://localhost:8766/ ./build_site.sh /tmp/site
//   (cd /tmp/site && python3 -m http.server 8766) &
//   NODE_PATH=<node_modules> node test/consistency.js --base http://localhost:8766/ [--states ne,co] [--verbose]
// Prints FAIL lines (and a table with --verbose) and exits 1 on any difference.
"use strict";
const fs = require("fs");
const puppeteer = require("puppeteer-core");

const arg = (name, dflt) => { const i = process.argv.indexOf("--" + name); return i > 0 ? process.argv[i + 1] : dflt; };
const BASE = arg("base", "http://localhost:8766/").replace(/\/?$/, "/");
const VERBOSE = process.argv.includes("--verbose");
const CHROME = process.env.CHROME || ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", "/usr/bin/google-chrome",
  "/usr/bin/google-chrome-stable", "/usr/bin/chromium"].find((p) => fs.existsSync(p));
const t0 = Date.now();
const log = (...a) => console.error(`[${((Date.now() - t0) / 1000).toFixed(0)}s]`, ...a);
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

// The words as compared: curly quotes straightened, spaces collapsed; an issue view's "in 2024" / "2024" after a law
// from another year than the one shown is a note about the year, not the status.
const norm = (s) => String(s ?? "").replace(/[’‘]/g, "'").replace(/\s+/g, " ").trim();
const lawYear = (s) => norm(s).replace(/ in \d{4}$/, "");

async function waitFor(page, fn, arg, ms = 30000) {
  const end = Date.now() + ms;
  while (Date.now() < end) {
    const v = await page.evaluate(fn, arg).catch(() => null);
    if (v) return v;
    await sleep(150);
  }
  return null;
}

// ---- Picking bills: on each state's pages, with the page's own reading of each bill ----
// (Runs in the state's page: BILLS, DATA and the page's functions are its globals.)
async function pickOn(page) {
  return page.evaluate(async () => {
    try { await need("rows"); } catch (e) {}
    try { await need("net"); } catch (e) {}
    try { await need("hist"); } catch (e) {}
    const has = (n) => typeof globalThis[n] === "function" || (() => { try { return typeof eval(n) === "function"; } catch (e) { return false; } })();
    const f = (n) => (has(n) ? eval(n) : () => null);
    const ended = f("endedOf"), amend = f("isAmendment"), second = f("secondPassage"), voters = f("toVoters"), carried = f("continuedTo");
    const out = [], taken = new Set();
    const add = (why, b) => { if (!b || taken.has(b.idx)) return; taken.add(b.idx); out.push({ why, idx: b.idx, full: b.nums[0], last: b.last || "", stage: b.stage }); };
    const pick = (why, test) => add(why, BILLS.find((b) => { try { return test(b); } catch (e) { return false; } }));
    const plain = (b) => !ended(b) && !(b.topics || []).includes("const") && !b.ballot;
    if (DATA.upcoming) { pick("prefiled", (b) => b.stage === 0); pick("prefiled, moved", (b) => b.stage > 0); return out; }
    for (let s = 0; s <= 6; s++) pick(`stage ${s}`, (b) => b.stage === s && plain(b));
    pick("ended mid-session", (b) => b.stage <= 2 && ended(b));
    pick("ended, passed one house", (b) => b.stage === 2 && ended(b));
    pick("amendment, first passage", (b) => b.stage === 3 && amend(b) && !second(b));
    pick("amendment, second passage", (b) => b.stage === 3 && amend(b) && second(b));
    pick("amendment topic, passed", (b) => b.stage === 3 && (b.topics || []).includes("const"));
    pick("sent to the voters", (b) => b.stage === 3 && voters(b));
    pick("carried over", (b) => b.stage <= 2 && carried(b));
    pick("passed one house (house named)", (b) => b.stage === 2 && b.passedIn && plain(b));
    pick("committee, gate", (b) => b.stage === 0 && STATE.gates && Object.values(STATE.gates).includes(b.comm));
    return out;
  });
}

// A bill's watchlist row. Rows are keyed by the number without its letter, so Nebraska's LB525 and LB525A share a key: the
// row whose number is the bill's.
function rowFor(rows, p) {
  const all = rows.filter((x) => x.key === `${p.st}:${p.session}:${p.num}`);
  return all.find((x) => x.num.startsWith(p.full) && !/^[A-Z0-9]/.test(x.num.slice(p.full.length))) || all[0];
}

async function main() {
  const browser = await puppeteer.launch({ executablePath: CHROME, headless: true, args: ["--no-sandbox", "--disable-gpu", "--lang=en-US"] });
  const page = await browser.newPage();
  await page.setViewport({ width: 1100, height: 1400 });
  const errors = [];
  page.on("pageerror", (e) => errors.push(`${page.url()}: ${e.message}`));
  const go = async (url) => { await page.goto(BASE + url, { waitUntil: "networkidle2", timeout: 60000 }).catch((e) => log("load", url, e.message)); };

  // The states built: /status.json names their sessions ({p: page, l: live, f: {u: upcoming}}).
  await go("");
  const index = await page.evaluate(() => fetch("/status.json").then((r) => r.json()));
  const only = arg("states") ? arg("states").split(",") : null;
  const states = Object.keys(index).filter((s) => !only || only.includes(s)).sort();
  log("states:", states.join(" "));

  // Bills to read, from each state's newest past session, current session and upcoming one.
  const picks = [];
  for (const st of states) {
    const sess = Object.keys(index[st]).map(Number).sort();
    const cur = sess.filter((s) => !index[st][s].f?.u).pop(), past = sess.filter((s) => s < cur).pop(), up = sess.find((s) => index[st][s].f?.u);
    for (const s of [cur, past, up].filter((s) => s != null)) {
      const p = index[st][s].p, url = `${st}/${p && p !== "./" ? p : ""}`;
      await go(url);
      const ok = await waitFor(page, () => document.documentElement.classList.contains("ready") && typeof BILLS !== "undefined" && BILLS.length > 0);
      if (!ok) { log(st, s, "page didn't load"); continue; }
      const got = await pickOn(page);
      for (const g of got) picks.push({ ...g, st, session: s, url, num: g.full.replace(/[A-Z]$/, ""), why: `${g.why}${s === cur ? "" : s === up ? " (upcoming)" : " (past session)"}` });
      log(st, s, got.length, "bills");
    }
  }

  // Bills on a national issue, one per stage per state (each issue's bills.json: [num, title, why, stage, link, kind,
  // raw, session, last, ...]), so the issue views are read too.
  const issues = await page.evaluate(() => fetch("/issues/summary.json").then((r) => (r.ok ? r.json() : null)).catch(() => null));
  const issueOf = {};  // st|session|num -> issue id
  const ids = (issues?.issues || []).map((i) => i.id);
  for (const id of ids) {
    const bj = await page.evaluate((id) => fetch(`/issues/${id}/bills.json`).then((r) => (r.ok ? r.json() : null)).catch(() => null), id);
    if (!bj) continue;
    const seen = new Set();
    for (const [, byState] of Object.entries(bj)) for (const [st, rows] of Object.entries(byState || {})) {
      if (!states.includes(st) || !Array.isArray(rows)) continue;
      for (const r of rows) {
        const raw = r[6], session = +r[7];
        if (!raw) continue;
        const k = `${st}|${session}|${raw.replace(/[A-Z]$/, "")}`;
        if (!issueOf[k]) issueOf[k] = id;
        const sk = `${st}|${r[3]}|${r[5]}`;
        if (seen.has(sk) || picks.some((p) => `${p.st}|${p.session}|${p.num}` === k) || picks.filter((p) => p.why.startsWith("on an issue") && p.st === st).length >= 8) continue;
        seen.add(sk);
        const ix = index[st]?.[session];
        if (!ix) continue;
        picks.push({ why: `on an issue (${id}), stage ${r[3]}`, st, session, url: `${st}/${ix.p && ix.p !== "./" ? ix.p : ""}`, full: raw, num: raw.replace(/[A-Z]$/, ""), last: r[8] || "", stage: r[3] });
      }
    }
  }
  for (const p of picks) p.issue = issueOf[`${p.st}|${p.session}|${p.num}`] || null;
  log(picks.length, "bills to read");

  // Star them all, each seen the day before its last action.
  const dayBefore = (d) => { if (!d) return ""; const t = new Date(`${d}T12:00Z`); t.setUTCDate(t.getUTCDate() - 1); return t.toISOString().slice(0, 10); };
  const lists = {};
  for (const p of picks) (lists[p.st] ||= {})[`${p.session}:${p.num}`] = { seen: dayBefore(p.last), stance: null };
  await go("about/");
  await page.evaluate((lists) => { localStorage.clear(); for (const [st, w] of Object.entries(lists)) localStorage.setItem(`abt:${st}:watch`, JSON.stringify(w)); }, lists);
  const R = new Map(picks.map((p) => [p, { views: {}, group: {}, due: {}, fresh: {} }]));

  // The state pages: each bill's row and panel, and the Watchlist tab.
  const byPage = new Map();
  for (const p of picks) (byPage.get(p.url) || byPage.set(p.url, []).get(p.url)).push(p);
  let done = 0;
  for (const [url, ps] of byPage) {
    for (const p of ps) {
      if (++done % 20 === 0) log(`state pages: ${done} of ${picks.length}`);
      // (A new load each time: going from one #bill to another on the same page is only a change of address.)
      await page.goto(BASE + "robots.txt");
      await go(`${url}#${p.full}`);
      const t = await waitFor(page, (full) => {
        const b = BILLS.find((x) => x.nums[0] === full);
        const d = b && document.querySelector(`details.bill[data-idx="${b.idx}"]`);
        const st = d && d.querySelector(".status .stg");
        if (!st || !d.open || !d.querySelector(".detail").children.length) return null;
        return st.textContent;
      }, p.full, 20000);
      R.get(p).views.bills = t;
    }
    // (Re-read the watchlist: opening a bill marks it seen, so the starred lists go back as they were first.)
    await page.evaluate((lists) => { for (const [st, w] of Object.entries(lists)) localStorage.setItem(`abt:${st}:watch`, JSON.stringify(w)); }, lists);
    await page.goto(BASE + "robots.txt");
    await go(`${url}#watch`);
    await waitFor(page, () => document.querySelector("#wlList .wr-row, #wlList .wempty, #wlList p"), null, 20000);
    await sleep(500);
    const rows = await page.evaluate(() => [...document.querySelectorAll("#wlList .wr-row")].map((r) => ({
      key: r.dataset.key, label: r.querySelector(".stg")?.textContent || null, due: r.querySelector(".wr-dl")?.textContent || "",
      group: r.closest("section[data-g]")?.dataset.g || "", fresh: !!r.querySelector(".wr-new"),
      num: [...(r.querySelector(".wr-num")?.childNodes || [])].filter((n) => !n.classList?.contains("wr-st")).map((n) => n.textContent).join("").replace(/\s+/g, "") })));
    for (const p of ps) {
      const r = rowFor(rows, p);
      if (!r) continue;
      Object.assign(R.get(p), { });
      R.get(p).views.watch = r.label; R.get(p).group.watch = r.group; R.get(p).due.watch = r.due; R.get(p).fresh.watch = r.fresh;
    }
  }

  // /your-bills/
  await page.evaluate((lists) => { localStorage.removeItem("abt:yourbills:rows"); for (const [st, w] of Object.entries(lists)) localStorage.setItem(`abt:${st}:watch`, JSON.stringify(w)); }, lists);
  await go("your-bills/");
  await waitFor(page, (n) => document.querySelectorAll("#bills .wr-row").length >= n, Math.min(picks.length, 5), 30000);
  await sleep(2000);
  {
    const rows = await page.evaluate(() => [...document.querySelectorAll("#bills .wr-row")].map((r) => ({
      key: r.dataset.key, label: r.querySelector(".stg")?.textContent || null, due: r.querySelector(".wr-dl")?.textContent || "",
      group: r.closest("section[data-g]")?.dataset.g || "", fresh: !!r.querySelector(".wr-new"),
      num: [...(r.querySelector(".wr-num")?.childNodes || [])].filter((n) => !n.classList?.contains("wr-st")).map((n) => n.textContent).join("").replace(/\s+/g, "") })));
    for (const p of picks) {
      const r = rowFor(rows, p);
      if (!r) continue;
      R.get(p).views.yours = r.label; R.get(p).group.yours = r.group; R.get(p).due.yours = r.due; R.get(p).fresh.yours = r.fresh;
    }
  }

  // The front page: Your bills, the search, the issue panel.
  await page.evaluate((lists) => { for (const [st, w] of Object.entries(lists)) localStorage.setItem(`abt:${st}:watch`, JSON.stringify(w)); }, lists);
  await go("");
  await waitFor(page, () => document.querySelectorAll("#mineList li").length > 0, null, 30000);
  await sleep(1500);
  {
    const rows = await page.evaluate(() => [...document.querySelectorAll("#mineList a[data-seen]")].map((a) => ({
      seen: a.dataset.seen, label: a.querySelector(".stg")?.textContent || null, fresh: !!a.querySelector(".what, .new") })));
    for (const p of picks) {
      const r = rows.find((x) => x.seen.startsWith(`${p.st}|${p.session}:${p.num}|`));
      if (!r) continue;
      R.get(p).views.mine = r.label; R.get(p).fresh.mine = r.fresh;
    }
  }
  // ("Find a bill" has the live sessions only: this one and next year's prefiled bills.)
  for (const p of picks.filter((x) => index[x.st][x.session]?.l)) {
    const q = `${p.st.toUpperCase()} ${p.full}`;
    await page.evaluate((q) => { const el = document.getElementById("q"); el.focus(); el.value = q; el.dispatchEvent(new Event("input", { bubbles: true })); }, q);
    const label = await waitFor(page, (href) => {
      const a = [...document.querySelectorAll("#found li a")].find((x) => x.getAttribute("href") === href);
      return a ? a.querySelector(".stg").textContent : null;
    }, `${p.url}#${p.full}`, 8000);
    if (label) R.get(p).views.search = label;
  }
  // The issue panel: the issue's map with every year, the state's panel opened.
  for (const p of picks.filter((x) => x.issue)) {
    await go(`#issue=${p.issue}&year=all`);
    await sleep(300);
    await page.evaluate((st) => showPanel(st), p.st).catch(() => {});
    const label = await waitFor(page, ({ st, num }) => {
      const a = [...document.querySelectorAll("#pbody li a")].find((x) => x.getAttribute("href").startsWith(`${st}/`) && x.getAttribute("href").endsWith(`#${num}`));
      return a ? a.querySelector(".stg").textContent : null;
    }, { st: p.st, num: p.num }, 8000);
    if (label) R.get(p).views.ipanel = label;
  }
  // The issue pages (every year's page: all.html).
  const issuePages = {};
  for (const p of picks.filter((x) => x.issue)) {
    if (!issuePages[p.issue]) {
      await go(`issues/${p.issue}/all.html`);
      issuePages[p.issue] = await page.evaluate(() => [...document.querySelectorAll("li[data-k]")].map((li) => ({ k: li.dataset.k, label: li.querySelector(".stg")?.textContent || null })));
    }
    const r = issuePages[p.issue].find((x) => x.k.startsWith(`${p.session}|${p.full}|`));
    if (r) R.get(p).views.issue = r.label;
  }

  // ---- Compare ----
  const fails = [];
  let compared = 0;
  for (const p of picks) {
    const r = R.get(p), name = `${p.st.toUpperCase()} ${p.full} (${p.session}; ${p.why})`;
    const words = Object.entries(r.views).filter(([, v]) => v != null).map(([k, v]) => [k, ["issue", "ipanel"].includes(k) ? lawYear(v) : norm(v)]);
    compared += words.length;
    if (new Set(words.map(([, v]) => v)).size > 1) fails.push(`FAIL words: ${name}: ${words.map(([k, v]) => `${k} "${v}"`).join(" | ")}`);
    if ("watch" in r.group && "yours" in r.group && (r.group.watch !== r.group.yours || norm(r.due.watch) !== norm(r.due.yours)))
      fails.push(`FAIL group: ${name}: watch ${r.group.watch} "${r.due.watch}" | yours ${r.group.yours} "${r.due.yours}"`);
    const fresh = Object.entries(r.fresh);
    if (new Set(fresh.map(([, v]) => v)).size > 1) fails.push(`FAIL new: ${name}: ${fresh.map(([k, v]) => `${k} ${v ? "new" : "not new"}`).join(" | ")}`);
    if (VERBOSE) console.log(`${name}\n  ${words.map(([k, v]) => `${k}: ${v}`).join("\n  ")}\n  group: ${JSON.stringify(r.group)} due: ${JSON.stringify(r.due)} new: ${JSON.stringify(r.fresh)}`);
    // (A state's Watchlist tab is its current page's, and "Find a bill" has the live sessions only.)
    const missing = ["bills", "watch", "yours", "mine", "search"].filter((k) => !(k in r.views) && !(k === "search" && !index[p.st][p.session]?.l)
      && !(k === "watch" && !/^(?:\.\/)?$/.test(index[p.st][p.session]?.p || "")));
    if (missing.length) console.log(`(not found in ${missing.join(", ")}: ${name})`);
  }
  for (const e of errors) fails.push(`FAIL script error: ${e}`);
  for (const f of fails) console.log(f);
  console.log(`${picks.length} bills, ${compared} views read; ${fails.length} problem(s)`);
  await browser.close();
  process.exit(fails.length ? 1 : 0);
}
main().catch((e) => { console.error(e); process.exit(2); });
