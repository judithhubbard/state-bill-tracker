// Shared by /your-bills/, /list/ and the list editor (lists_pages/; build_site.sh puts it inside each page, after
// billfacts.js and status.js, which hold the starred bills in this browser and where each bill is, as on the front page).
// Shared lists live in the lists Worker (lists_worker/): a list across states writes each bill "nj:2026:A1234" ("-" in
// front: opposed).
const LISTS_API = (document.querySelector('meta[name="lists-api"]')?.content || "").replace(/\/$/, "");
const SUPPORT = document.querySelector('meta[name="support"]')?.content || "";
const NAMES = { al: "Alabama", ak: "Alaska", az: "Arizona", ar: "Arkansas", ca: "California", co: "Colorado", ct: "Connecticut",
  dc: "District of Columbia", de: "Delaware", fl: "Florida", ga: "Georgia", hi: "Hawaii", id: "Idaho", il: "Illinois", in: "Indiana", ia: "Iowa",
  ks: "Kansas", ky: "Kentucky", la: "Louisiana", me: "Maine", md: "Maryland", ma: "Massachusetts", mi: "Michigan",
  mn: "Minnesota", ms: "Mississippi", mo: "Missouri", mt: "Montana", ne: "Nebraska", nv: "Nevada", nh: "New Hampshire",
  nj: "New Jersey", nm: "New Mexico", ny: "New York", nc: "North Carolina", nd: "North Dakota", oh: "Ohio", ok: "Oklahoma",
  or: "Oregon", pa: "Pennsylvania", ri: "Rhode Island", sc: "South Carolina", sd: "South Dakota", tn: "Tennessee",
  tx: "Texas", ut: "Utah", vt: "Vermont", va: "Virginia", wa: "Washington", wv: "West Virginia", wi: "Wisconsin", wy: "Wyoming",
  us: "Congress" };
const stName = (st) => NAMES[st] || st.toUpperCase();
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const $ = (id) => document.getElementById(id);
// Visit counting (GoatCounter, once the site is launched): anonymous events by name, never which bills or lists.
function countUse(name, tries = 0) {
  if (window.goatcounter?.count) { try { window.goatcounter.count({ path: name, title: name, event: true }); } catch (e) {} return; }
  if (document.querySelector("script[data-goatcounter]") && tries < 6) setTimeout(() => countUse(name, tries + 1), 2000);
}
// An ⓘ whose explanation shows on hover or focus (a tap focuses it on a phone): common.css's .info.
const infoTip = (text) => `<span class="info" tabindex="0" role="note" aria-label="${String(text).replace(/"/g, "&quot;")}"><span aria-hidden="true">i</span><span class="info-t" aria-hidden="true">${String(text).replace(/</g, "&lt;")}</span></span>`;
// The same with links in it (html is markup; the ⓘ stays open while a link in it has focus). "wide": the explanation spans
// its positioned parent, not centred on the ⓘ, so it can't run off a phone's screen.
const infoTipHtml = (html, cls = "") => `<span class="info${cls ? ` ${cls}` : ""}" tabindex="0" role="note" aria-label="${esc(html.replace(/<[^>]+>/g, "").replace(/&rsquo;/g, "’").replace(/&ldquo;/g, "“").replace(/&rdquo;/g, "”"))}"><span aria-hidden="true">i</span><span class="info-t">${html}</span></span>`;
const COUNTED = new Set();
function countOnce(name) { if (!COUNTED.has(name)) { COUNTED.add(name); countUse(name); } }

// ---- Watchlists in this browser ----
// Every starred bill in this browser: [{st, session, num, entry}].
function allStarred() {
  const out = [];
  try {
    for (let i = 0; i < localStorage.length; i++) {
      const m = (localStorage.key(i) || "").match(/^abt:([a-z]{2}):watch$/);
      if (!m) continue;
      const st = m[1];
      if (!NAMES[st]) continue;
      for (const [k, v] of Object.entries(readWatch(st))) {
        const [session, num] = k.split(":");
        if (/^\d{4}$/.test(session) && num) out.push({ st, session: +session, num, entry: entryOf(v) });
      }
    }
  } catch (e) {}
  return out;
}
// A bill in a list across states: "nj:2026:A1234"; "-" in front means oppose.
const CROSS_RE = /^(-?)([a-z]{2}):(\d{4}):([A-Z]{1,7}\d{1,6})$/;
const crossKey = (st, session, num) => `${st}:${session}:${baseNum(num)}`;
function parseCross(code) {
  const m = CROSS_RE.exec(code);
  return m ? { st: m[2], session: +m[3], num: m[4], stance: m[1] ? "oppose" : "support", key: `${m[2]}:${m[3]}:${m[4]}` } : null;
}
// A list's bills in one shape, whether the list is one state's ({state, session, bills: ["A1234"]}) or across states.
function listBills(l) {
  if (l.state === "all") return l.bills.map(parseCross).filter(Boolean);
  return l.bills.map((b) => {
    const m = /^(-?)(.+)$/.exec(b);
    return { st: l.state, session: l.session, num: m[2], stance: m[1] ? "oppose" : "support", key: `${l.state}:${l.session}:${m[2]}` };
  });
}
// Support and oppose are shown when they tell something: on a group's list, or when the list opposes any bill.
const showStance = (l) => !!l.group || l.bills.some((b) => b.startsWith("-"));
const noteOf = (l, b) => (l.notes || {})[l.state === "all" ? b.key : b.num] || "";

// ---- Where each bill is (status.js) ----
statusIndex();  // at once: the pages preload it
// The status files cut long titles short (about 140 characters): mark the cut.
const cut = (t) => (t.length >= 120 && !/[.!?)"”']$/.test(t) ? t.replace(/[\s,;:]+$/, "") + "…" : t);
// One bill's status: {found, full, title, stage, last, action, label, href, page} (href: its card on the state's page;
// page: the session's page, where /list/ opens a bill's card from).
async function lookUp(st, session, num) {
  const s = await statusOf(st, session, num);
  const lead = s ? (s.bills[num] ? num : s.alias?.[num]) : null, b = lead && s.bills[lead];
  if (!b) return { found: false, full: num, title: `${session} session`, href: `/${st}/` };
  const { full, title, stage, last, action, label } = rowOf(b), page = s.page && s.page !== "./" ? s.page : "";
  return { found: true, full, title: cut(title), stage, last, action, label, href: `/${st}/${page}#${full}`, page: `/${st}/${page}` };
}
const THIS_YEAR = new Date().getFullYear();
// A bill its state's data doesn't have (the state's page shows the rest, embed.js): number, title, where it is, a link to
// the state's page. x: lookUp()'s answer plus {st, session, stance, note, star (the star's HTML), seen (data-seen value)}.
function billRow(x) {
  const yr = x.session < THIS_YEAR - 1 || x.session > THIS_YEAR ? ` <small>(${x.session})</small>` : "";
  return `<li${x.star ? "" : ' class="nostar"'}><a href="${esc(x.href)}"${x.seen ? ` data-seen="${esc(x.seen)}"` : ""}>`
    + `<span class="num">${esc(numText(x.st, x.full))}${yr}</span><span class="tt">${esc(x.title)}</span>`
    + (x.note ? `<span class="note">${esc(x.note)}</span>` : "")
    + `<span class="where">${x.stance ? `<span class="stance ${x.stance}">${x.stance === "oppose" ? "Oppose" : "Support"}</span>` : ""}`
    + (x.found ? `${BillFacts.pips(x.stage, BillFacts.oneHouse(x.st), "mini", x.label, x.st)}<span class="stg s${x.stage}">${esc(x.label)}</span>${x.last ? `<span>${fmtDay(x.last)}</span>` : ""}` : "")
    + `<span class="todo">Open on ${x.st === "us" ? "the Congress page" : `${esc(stName(x.st))}'s page`} ›</span></span></a>${x.star || ""}</li>`;
}

// ---- The lists Worker ----
async function api(path, opts = {}) {
  if (!LISTS_API) throw new Error("Sharing isn't available here.");
  const r = await fetch(LISTS_API + path, { ...opts, headers: { "Content-Type": "application/json", ...(opts.headers || {}) } });
  const body = await r.json().catch(() => ({}));
  if (!r.ok) { const e = new Error(body.error || `The list service answered ${r.status}.`); e.status = r.status; throw e; }
  return body;
}
// The list made from "Your bills" in this browser: {slug, editKey, title, group, intro, notes, saved (what was last saved)}.
const PUB = "abt:all:published";
function myList() { try { return JSON.parse(localStorage.getItem(PUB) || "null"); } catch (e) { return null; } }
function setMyList(v) { try { v ? localStorage.setItem(PUB, JSON.stringify(v)) : localStorage.removeItem(PUB); } catch (e) {} }
// Lists followed in this browser: {slug: {title, known: [bill keys seen so far], since}}.
const FOLLOWS = "abt:follows";
function readFollows() { try { const o = JSON.parse(localStorage.getItem(FOLLOWS) || "{}"); return o && typeof o === "object" ? o : {}; } catch (e) { return {}; } }
function writeFollows(o) { try { localStorage.setItem(FOLLOWS, JSON.stringify(o)); } catch (e) {} }
const listLink = (slug) => `${location.origin}/list/#${slug}`;
// Paragraphs from plain text (a group's introduction).
const paras = (t) => String(t || "").split(/\n\s*\n/).map((p) => p.trim()).filter(Boolean).map((p) => `<p>${esc(p).replace(/\n/g, "<br>")}</p>`).join("");

// ---- Sharing a list: the icons and the copy button (/your-bills/ and the list editor) ----
const PHONE = /Android|iPhone|iPad|iPod/i.test(navigator.userAgent);
const ICONS = {
  email: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 5h18a1 1 0 0 1 1 1v12a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1V6a1 1 0 0 1 1-1Zm1 2.4V17h16V7.4l-8 5.3-8-5.3ZM5.6 7 12 11.2 18.4 7H5.6Z"/></svg>',
  text: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 3h16a2 2 0 0 1 2 2v11a2 2 0 0 1-2 2H9l-5 4v-4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2Zm0 2v11h2v2l2.5-2H20V5H4Zm3 4h10v2H7V9Z"/></svg>',
  facebook: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M24 12.07C24 5.41 18.63 0 12 0S0 5.4 0 12.07C0 18.1 4.39 23.1 10.13 24v-8.44H7.08v-3.49h3.04V9.41c0-3.02 1.8-4.7 4.54-4.7 1.31 0 2.68.24 2.68.24v2.97h-1.5c-1.5 0-1.96.93-1.96 1.89v2.26h3.32l-.53 3.5h-2.8V24C19.62 23.1 24 18.1 24 12.07Z"/></svg>',
  x: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M18.24 2.25h3.31l-7.23 8.26 8.5 11.24h-6.65l-5.21-6.82-5.97 6.82H1.68l7.73-8.84L1.25 2.25h6.83l4.71 6.23 5.45-6.23Zm-1.16 17.52h1.83L7.08 4.13H5.12l11.96 15.64Z"/></svg>',
  bluesky: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 10.8C10.9 8.7 7.95 4.75 5.2 2.8 2.57.95 1.56 1.27.9 1.57.14 1.9 0 3.08 0 3.77c0 .69.38 5.65.62 6.48.82 2.74 3.71 3.66 6.38 3.36-3.91.58-7.39 2-2.83 7.08 5.01 5.19 6.87-1.11 7.83-4.31.95 3.2 2.05 9.27 7.73 4.31 4.27-4.31 1.17-6.5-2.74-7.08 2.67.3 5.57-.62 6.38-3.36.25-.83.63-5.79.63-6.48 0-.69-.14-1.86-.9-2.2-.66-.3-1.67-.62-4.3 1.24C16.05 4.75 13.09 8.69 12 10.8Z"/></svg>',
};
function shareIcons(url, title) {
  const u = encodeURIComponent(url), t = encodeURIComponent(title), both = encodeURIComponent(`${title}\n${url}`);
  const links = [["Email", `mailto:?subject=${t}&body=${both}`, "email"]];
  if (PHONE) links.push(["Text message", `sms:?&body=${both}`, "text"]);
  links.push(["Facebook", `https://www.facebook.com/sharer/sharer.php?u=${u}`, "facebook"],
    ["X", `https://x.com/intent/post?text=${t}&url=${u}`, "x"],
    ["Bluesky", `https://bsky.app/intent/compose?text=${encodeURIComponent(`${title} ${url}`)}`, "bluesky"]);
  return `<div class="icons">${links.map(([name, href, icon]) => `<a href="${esc(href)}"${/^https/.test(href) ? ' target="_blank" rel="noopener"' : ""} data-share="${icon}" title="${name}" aria-label="Share by ${name}">${ICONS[icon]}</a>`).join("")}</div>`;
}
// A contribution line after the first share, at most once in 90 days in this browser (the state pages' note shares the date).
function thanksOnce() {
  if (!/^https?:/.test(SUPPORT)) return "";
  try {
    const last = localStorage.getItem("abt:supportnote");
    if (last && Date.now() - +last < 90 * 864e5) return "";
    localStorage.setItem("abt:supportnote", String(Date.now()));
  } catch (e) { return ""; }
  return `Thanks for sharing! State Bill Tracker is free and run by one person. If you can, please <a href="${esc(SUPPORT)}" target="_blank" rel="noopener">chip in</a>.`;
}
// "Share ▾" in a list's summary line: a small menu with Copy link, Preview and the share icons (sharePop()); one open at a
// time, closed by Escape or a click outside it.
function sharePop(slug, title) {
  const url = listLink(slug);
  return `<span class="spop"><button type="button" class="linkish" data-sharepop aria-expanded="false" aria-haspopup="true">Share ▾</button>`
    + `<span class="spopbox" hidden><span class="row"><button type="button" class="btn" data-copylink="${esc(slug)}">Copy link</button><a href="/list/#${esc(slug)}">Preview</a></span>`
    + `${shareIcons(url, title)}</span></span>`;
}
function closePops(but) {
  for (const b of document.querySelectorAll("[data-sharepop][aria-expanded=\"true\"]")) if (b !== but) { b.setAttribute("aria-expanded", "false"); b.nextElementSibling.hidden = true; }
}
document.addEventListener("click", (e) => {
  const b = e.target.closest?.("[data-sharepop]");
  if (b) { const on = b.getAttribute("aria-expanded") !== "true"; closePops(b); b.setAttribute("aria-expanded", String(on)); b.nextElementSibling.hidden = !on; return; }
  const c = e.target.closest?.("[data-copylink]");
  if (c) { countUse("list/link copied"); return copy(c, listLink(c.dataset.copylink)); }
  if (!e.target.closest?.(".spopbox")) closePops();
});
document.addEventListener("keydown", (e) => {
  if (e.key !== "Escape") return;
  const open = document.querySelector("[data-sharepop][aria-expanded=\"true\"]");
  if (open) { closePops(); open.focus(); }
});
async function copy(btn, text) {
  try { await navigator.clipboard.writeText(text); btn.textContent = "Copied"; } catch (e) { btn.previousElementSibling?.select?.(); btn.textContent = "Select and copy it"; }
}

// Lists made in this browser with the list editor (/lists/edit/#<slug>), apart from the one "Your bills" shares:
// {slug: {slug, editKey, title, group, intro, notes, bills (codes in the list's order), saved (what was last saved), updated}}.
const NAMED = "abt:lists";
function readNamed() { try { const o = JSON.parse(localStorage.getItem(NAMED) || "{}"); return o && typeof o === "object" && !Array.isArray(o) ? o : {}; } catch (e) { return {}; } }
function writeNamed(o) { try { localStorage.setItem(NAMED, JSON.stringify(o)); } catch (e) {} }
// The edit key this browser holds for a list, if any.
const editKeyFor = (slug) => (myList()?.slug === slug ? myList().editKey : readNamed()[slug]?.editKey || "");
